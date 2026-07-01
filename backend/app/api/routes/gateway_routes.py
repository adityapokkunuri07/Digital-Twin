"""
Gateway Routes
Generic entrypoints for initiating a session before workflow resolution.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from uuid import UUID

from backend.app.api.schemas.preconsult_schemas import (
    StartPreConsultRequest,
    ChatTurnRequest,
)
from backend.app.api.dependencies import get_preconsult_service
from backend.app.services.preconsult_service import PreConsultationService

router = APIRouter(prefix="/gateway", tags=["Gateway"])


@router.post("/start")
async def start_gateway_session(
    payload: StartPreConsultRequest,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Start a new session without assuming a specific workflow."""
    session = await service.start_session(payload.patient_id, payload.config_id)
    return session


@router.post("/chat")
async def process_gateway_chat(
    payload: ChatTurnRequest,
    background_tasks: BackgroundTasks,
    service: PreConsultationService = Depends(get_preconsult_service),
):
    """Process a chat turn starting in the probing phase."""
    response = await service.process_chat_turn(
        payload.session_id, payload.message, background_tasks
    )
    return response
