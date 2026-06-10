"""
Session-related request/response schemas.
"""
from uuid import UUID
from pydantic import BaseModel


class InitiateSessionRequest(BaseModel):
    """Request payload for initiating a new LangGraph execution session."""
    conversation_id: UUID
    config_id: UUID


class QuerySessionRequest(BaseModel):
    """Request payload for sending a user query to an active session."""
    session_id: UUID
    query: str


class BookAppointmentRequest(BaseModel):
    """Request payload for enqueuing a clinic booking transaction."""
    session_id: UUID
    preferred_date: str
    time_slot: str


class DoctorInjectRequest(BaseModel):
    """Request payload for injecting a doctor's message into a frozen session."""
    message: str
