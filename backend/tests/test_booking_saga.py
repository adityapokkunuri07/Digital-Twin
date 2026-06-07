import pytest
import asyncio
import httpx
import asyncpg
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Import saga components
from backend.app.services.saga_orchestrator import SagaOrchestrator, generate_idempotency_key
from backend.app.services.reconciliation import OutboxReconciliationCron

@pytest.fixture
def mock_db_pool():
    """Fixture providing a mocked asyncpg.Pool connection."""
    pool = MagicMock(spec=asyncpg.Pool)
    conn = AsyncMock(spec=asyncpg.Connection)
    
    # Mock transaction context manager
    tx = AsyncMock()
    conn.transaction.return_value = tx
    
    pool.acquire.return_value.__aenter__.return_value = conn
    return pool, conn

@pytest.fixture
def mock_http_client():
    """Fixture providing a mocked httpx.AsyncClient."""
    client = MagicMock(spec=httpx.AsyncClient)
    return client

# ─── Test Case 1: Idempotency Key Determination ───────────────────────

def test_idempotency_key_consistency():
    session_id = str(uuid4())
    date = "2026-06-08"
    slot = "09:00"
    
    key_1 = generate_idempotency_key(session_id, date, slot)
    key_2 = generate_idempotency_key(session_id, date, slot)
    key_changed = generate_idempotency_key(session_id, date, "10:00")
    
    assert key_1 == key_2, "Same inputs must generate matching idempotency keys."
    assert key_1 != key_changed, "Varying slot must generate distinct keys."

# ─── Test Case 2: External API Timeout with Success on Retry ──────────

@pytest.mark.asyncio
async def test_saga_transient_failure_retry_success(mock_db_pool, mock_http_client):
    pool, conn = mock_db_pool
    session_id = str(uuid4())
    
    # Mock DB: Lock status to INITIATING_BOOKING succeeds
    conn.execute = AsyncMock()
    
    # Mock HTTP: Timeout once, succeed on the second attempt
    mock_responses = [
        httpx.ConnectTimeout("Connection timed out"),
        MagicMock(status_code=200, json=lambda: {"status": "confirmed", "booking_id": "ext-999"})
    ]
    mock_http_client.post = AsyncMock(side_effect=mock_responses)
    
    orchestrator = SagaOrchestrator(
        db_pool=pool, 
        http_client=mock_http_client, 
        max_retries=2, 
        backoff_factor=0.01  # Fast backoff for tests
    )
    
    # Run the Saga
    result_status = await orchestrator.run(session_id, "2026-06-08", "09:00")
    
    # Assertions
    assert result_status == "BOOKED"
    # Ensure state transitioned to INITIATING_BOOKING first, then BOOKED
    assert conn.execute.call_count >= 2
    assert any("INITIATING_BOOKING" in str(arg) for arg in conn.execute.call_args_list[0][0])
    assert any("BOOKED" in str(arg) for arg in conn.execute.call_args_list[1][0])

# ─── Test Case 3: Permanent External API Failure (Compensating Rollback) ──

@pytest.mark.asyncio
async def test_saga_permanent_conflict_rollback(mock_db_pool, mock_http_client):
    pool, conn = mock_db_pool
    session_id = str(uuid4())
    
    # Mock HTTP: Return 409 Conflict immediately (slot already taken)
    conflict_response = MagicMock(
        status_code=409, 
        text="Time slot already reserved by another patient."
    )
    mock_http_client.post = AsyncMock(return_value=conflict_response)
    conn.execute = AsyncMock()
    
    orchestrator = SagaOrchestrator(db_pool=pool, http_client=mock_http_client)
    
    # Run the Saga
    result_status = await orchestrator.run(session_id, "2026-06-08", "09:00")
    
    # Assertions
    assert result_status == "FAILED_REVIEW"
    # Ensure local database rolled back state to lock release/failure state
    assert any("FAILED_REVIEW" in str(arg) or "AVAILABLE" in str(arg) for arg in conn.execute.call_args_list[-1][0])

# ─── Test Case 4: Worker Crash/OOM Recovery (Reconciliation Cron) ──────

@pytest.mark.asyncio
async def test_reconciliation_cron_resolves_hung_states(mock_db_pool, mock_http_client):
    pool, conn = mock_db_pool
    
    # Mock DB: Find one booking stuck in 'INITIATING_BOOKING' for > 5 minutes
    hung_booking = {
        "session_id": str(uuid4()),
        "preferred_date": "2026-06-08",
        "time_slot": "09:00",
        "status": "INITIATING_BOOKING"
    }
    conn.fetch = AsyncMock(return_value=[hung_booking])
    
    # Mock HTTP: External API confirms booking was actually recorded downstream
    confirm_response = MagicMock(
        status_code=200, 
        json=lambda: {"bookings": [{"id": "ext-999", "status": "active"}]}
    )
    mock_http_client.get = AsyncMock(return_value=confirm_response)
    conn.execute = AsyncMock()
    
    # Run outbox cleaner cron
    cron = OutboxReconciliationCron(db_pool=pool, http_client=mock_http_client)
    
    await cron.reconcile_hung_sessions()
    
    # Assertions
    # The cron queried the downstream API using the correct GET filters
    mock_http_client.get.assert_called_once()
    # The cron updated the database status to BOOKED because downstream confirmed it
    assert any("BOOKED" in str(arg) for arg in conn.execute.call_args_list[0][0])
