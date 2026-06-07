import hashlib
import asyncio
import logging
import httpx
import asyncpg

logger = logging.getLogger("SagaOrchestrator")

def generate_idempotency_key(session_id: str, date: str, slot: str) -> str:
    """Generates a deterministic SHA-256 hash to prevent double-booking collisions."""
    payload = f"{session_id}:{date}:{slot}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

class SagaOrchestrator:
    def __init__(
        self, 
        db_pool: asyncpg.Pool, 
        http_client: httpx.AsyncClient, 
        max_retries: int = 3, 
        backoff_factor: float = 2.0
    ):
        self.db_pool = db_pool
        self.http_client = http_client
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.clinic_endpoint = "https://api.partner-clinic.com/v1/appointments"

    async def run(self, session_id: str, preferred_date: str, time_slot: str) -> str:
        """Executes the distributed booking saga."""
        idempotency_key = generate_idempotency_key(session_id, preferred_date, time_slot)
        
        async with self.db_pool.acquire() as conn:
            # 1. Local Intent Lock
            await conn.execute(
                "UPDATE pre_consultation_sessions SET status = $1 WHERE session_id = $2",
                "INITIATING_BOOKING", session_id
            )
            
            # Fetch necessary payload details (abstracted for brevity)
            payload = {
                "preferred_date": preferred_date,
                "time_slot": time_slot,
                "status": "confirmed"
            }

            # 2. External Execution with Retry Backoff
            for attempt in range(self.max_retries + 1):
                try:
                    response = await self.http_client.post(
                        self.clinic_endpoint,
                        json=payload,
                        headers={"X-Idempotency-Key": idempotency_key}
                    )
                    
                    # Success
                    if response.status_code in (200, 201):
                        ext_booking_id = response.json().get("booking_id", "unknown")
                        await conn.execute(
                            "UPDATE pre_consultation_sessions SET status = $1 WHERE session_id = $2",
                            "BOOKED", session_id
                        )
                        return "BOOKED"
                        
                    # Permanent Failure (e.g., 409 Conflict)
                    if response.status_code >= 400 and response.status_code < 500:
                        logger.warning(f"Booking rejected: {response.status_code}. Rolling back.")
                        await self._compensating_rollback(conn, session_id)
                        return "FAILED_REVIEW"

                    response.raise_for_status()

                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.HTTPStatusError) as e:
                    if attempt == self.max_retries:
                        logger.error(f"Saga failed after {self.max_retries} retries: {str(e)}")
                        await self._compensating_rollback(conn, session_id)
                        return "FAILED_REVIEW"
                    
                    delay = self.backoff_factor ** attempt
                    logger.info(f"Transient error. Retrying in {delay}s...")
                    await asyncio.sleep(delay)

    async def _compensating_rollback(self, conn: asyncpg.Connection, session_id: str):
        """Reverts the local state if the external transaction permanently fails."""
        await conn.execute(
            "UPDATE pre_consultation_sessions SET status = $1 WHERE session_id = $2",
            "FAILED_REVIEW", session_id
        )
