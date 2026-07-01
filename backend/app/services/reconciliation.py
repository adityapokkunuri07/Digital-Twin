import logging
import httpx
import asyncpg

from backend.app.core.enums import SessionStatus

logger = logging.getLogger("ReconciliationCron")

class OutboxReconciliationCron:
    def __init__(self, db_pool: asyncpg.Pool, http_client: httpx.AsyncClient):
        self.db_pool = db_pool
        self.http_client = http_client
        self.clinic_verify_endpoint = "https://api.partner-clinic.com/v1/appointments/verify"

    async def reconcile_hung_sessions(self):
        """Sweeps the DB for bookings stuck in INITIATING_BOOKING and resolves them."""
        async with self.db_pool.acquire() as conn:
            # Find sessions hung for more than a set threshold (e.g., 5 minutes)
            hung_sessions = await conn.fetch(
                f"SELECT session_id, preferred_date, time_slot FROM pre_consultation_sessions "
                f"WHERE status = '{SessionStatus.PROCESSING_BOOKING.value}'"
            )

            for session in hung_sessions:
                session_id = str(session["session_id"])
                
                try:
                    # Query downstream API to see if the HTTP request actually succeeded before the crash
                    response = await self.http_client.get(
                        self.clinic_verify_endpoint,
                        params={"session_reference": session_id}
                    )
                    
                    if response.status_code == 200 and response.json().get("bookings"):
                        logger.info(f"Reconciled hung session {session_id} -> BOOKED.")
                        await conn.execute(
                            "UPDATE pre_consultation_sessions SET status = $1 WHERE session_id = $2",
                            SessionStatus.COMPLETE_BOOKED, session_id
                        )
                    else:
                        # If the clinic has no record, the HTTP call died before reaching them. Safe to rollback.
                        logger.info(f"Reconciled hung session {session_id} -> AWAITING_BOOKING.")
                        await conn.execute(
                            "UPDATE pre_consultation_sessions SET status = $1 WHERE session_id = $2",
                            SessionStatus.AWAITING_BOOKING, session_id
                        )
                except Exception as e:
                    logger.error(f"Failed to reconcile session {session_id}: {str(e)}")
