"""
Session Routes — Thin HTTP handlers for LangGraph session management.

Single Responsibility: Parse request → delegate to orchestrator → return response.
"""
from fastapi import APIRouter, Depends

from uuid import UUID

from backend.app.api.schemas.session_schemas import (
    InitiateSessionRequest,
    QuerySessionRequest,
    DoctorInjectRequest,
)
from backend.app.api.dependencies import get_orchestrator, get_preconsult_service
from backend.app.orchestrator.state_machine import ZeroTrustOrchestrator
from backend.app.services.preconsult_service import PreConsultationService

router = APIRouter(prefix="/session", tags=["Session"])


@router.post("/initiate")
async def initiate_session(
    payload: InitiateSessionRequest,
    orch: ZeroTrustOrchestrator = Depends(get_orchestrator),
):
    """Initialize a new LangGraph execution session."""
    state = await orch.initialize_session(
        payload.conversation_id, payload.config_id,
    )
    return state


@router.post("/query")
async def query_session(
    payload: QuerySessionRequest,
    orch: ZeroTrustOrchestrator = Depends(get_orchestrator),
):
    """Send a user query to an active session for state machine processing."""
    
    # --- KNOWLEDGE ENGINE INTERCEPTION ---
    if "[Document Attached:" in payload.query:
        import re
        from backend.app.services.task_assembler import TaskAssembler
        # Fallback expert ID for demo
        expert_id = "default-expert-id"
        matched_task = "Generate Briefs" # Hardcoded for demo parity
        
        try:
            assembler = TaskAssembler()
            blueprint = assembler.assemble_blueprint(matched_task, expert_id)
            print(f"[SESSION_ROUTE] Intercepted Document, Assembled Blueprint: {blueprint}")
        except Exception as e:
            print(f"[SESSION_ROUTE] Assembly failed: {e}")

    state = await orch.run_step(payload.session_id, payload.query)
    return state


@router.post("/{session_id}/doctor-inject")
async def doctor_inject_message(
    session_id: UUID,
    payload: DoctorInjectRequest,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Inject a doctor's message into a session."""
    state = await service.inject_doctor_message(session_id, payload.message)
    return state


from arq import create_pool
from arq.connections import RedisSettings
from backend.app.api.schemas.session_schemas import BookAppointmentRequest

async def get_redis_pool():
    # Points to standard Redis settings
    return await create_pool(RedisSettings(host="localhost", port=6379))

@router.post("/book", status_code=202)
async def book_appointment(
    payload: BookAppointmentRequest,
    redis_pool = Depends(get_redis_pool)
):
    """Enqueues the booking task into the Redis queue for worker execution."""
    await redis_pool.enqueue_job(
        "execute_booking_saga_task",
        session_id=str(payload.session_id),
        preferred_date=payload.preferred_date,
        time_slot=payload.time_slot
    )
    return {"status": "queued", "session_id": payload.session_id}
