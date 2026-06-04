"""
Onboarding-related request/response schemas.
"""
from uuid import UUID
from pydantic import BaseModel


class InterviewRequest(BaseModel):
    """Request payload for an AI Journalist onboarding interview analysis."""
    transcript: str


class FinalizeOnboardingRequest(BaseModel):
    """Request payload for finalizing an onboarding session and extracting CoT."""
    config_id: UUID
    transcript: str
