"""
Session Routes — Thin HTTP handlers for LangGraph session management.

Single Responsibility: Parse request → delegate to orchestrator → return response.
"""
from fastapi import APIRouter, Depends

from backend.app.api.schemas.session_schemas import (
    InitiateSessionRequest,
    QuerySessionRequest,
)
from backend.app.api.dependencies import get_orchestrator
from backend.app.orchestrator.state_machine import ZeroTrustOrchestrator

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
    state = await orch.run_step(payload.session_id, payload.query)
    return state
