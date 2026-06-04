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
