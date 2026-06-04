"""
Onboarding Routes — Thin HTTP handlers for AI Journalist onboarding.

Single Responsibility: Parse request → delegate to OnboardingService → return response.
"""
from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.schemas.onboarding_schemas import (
    InterviewRequest,
    FinalizeOnboardingRequest,
)
from backend.app.api.dependencies import get_onboarding_service
from backend.app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.post("/interview")
async def onboarding_interview(
    payload: InterviewRequest,
    onboarding_svc: OnboardingService = Depends(get_onboarding_service),
):
    """Analyze an onboarding transcript for knowledge saturation."""
    saturation, is_satisfied, next_prompt = await onboarding_svc.analyze_interview(
        payload.transcript,
    )
    return {
        "saturation_score": saturation,
        "is_satisfied": is_satisfied,
        "next_prompt": next_prompt,
    }


@router.post("/finalize")
async def finalize_onboarding(
    payload: FinalizeOnboardingRequest,
    onboarding_svc: OnboardingService = Depends(get_onboarding_service),
):
    """Finalize onboarding: extract CoT, persist, and project to audit plane."""
    try:
        result = await onboarding_svc.finalize_onboarding(
            payload.config_id, payload.transcript,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
