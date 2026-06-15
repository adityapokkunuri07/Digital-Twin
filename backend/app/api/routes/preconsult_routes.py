"""
Pre-Consultation Routes
Thin HTTP handlers delegating to PreConsultationService.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from uuid import UUID

from backend.app.api.schemas.preconsult_schemas import (
    StartPreConsultRequest,
    ChatTurnRequest,
    DoctorReviewRequest,
    BookAppointmentRequest,
)
from backend.app.api.dependencies import get_preconsult_service
from backend.app.services.preconsult_service import PreConsultationService

router = APIRouter(prefix="/pre-consult", tags=["Pre-Consultation"])


@router.post("/start")
async def start_session(
    payload: StartPreConsultRequest,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Task 1 Init: Start a new pre-consultation session."""
    session = await service.start_session(payload.patient_id, payload.config_id)
    return session

@router.get("/session/{session_id}")
async def get_session(
    session_id: UUID,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Polling route for frontend to get session and summary state."""
    return await service.get_session_details(session_id)

@router.get("/queue")
async def get_pending_queue(
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Fetch all sessions that are waiting for doctor review."""
    return await service.get_pending_queue()


@router.post("/chat")
async def process_chat_turn(
    payload: ChatTurnRequest,
    background_tasks: BackgroundTasks,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Task 1 Loop: Gather data and execute triage/circuit-breakers."""
    response = await service.process_chat_turn(
        payload.session_id, payload.message, background_tasks
    )
    return response


@router.post("/review")
async def submit_doctor_review(
    payload: DoctorReviewRequest,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Task 3: Doctor reviews the synthesized summary."""
    response = await service.submit_doctor_review(
        payload.session_id, payload.doctor_review_notes
    )
    return response


@router.post("/session/{session_id}/align-release")
async def align_and_release_session(
    session_id: UUID,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Doctor dashboard action: Unfreeze session and advance workflow."""
    return await service.align_and_release(session_id)


@router.get("/session/{session_id}/escalation-context")
async def get_escalation_context(
    session_id: UUID,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Provide side-by-side comparison of patient data vs thresholds for the doctor."""
    return await service.get_escalation_context(session_id)


@router.post("/book")
async def book_appointment(
    payload: BookAppointmentRequest,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Task 4: AI Coordinator completes the booking."""
    response = await service.book_appointment(
        payload.session_id, payload.patient_id, payload.doctor_id, payload.scheduled_time
    )
    return response

@router.get("/appointments/patient/{patient_id}")
async def get_patient_appointments(
    patient_id: UUID,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Fetch all appointments for a given patient."""
    return await service.get_patient_appointments(patient_id)

@router.get("/appointments/all")
async def get_all_appointments(
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Fetch all appointments across the system for the Doctor Control Plane."""
    return await service.get_all_appointments()
