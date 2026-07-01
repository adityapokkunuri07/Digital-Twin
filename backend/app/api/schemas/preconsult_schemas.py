"""
Pre-Consultation Workflow Schemas
"""
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class PreConsultStatus(str, Enum):
    GATHERING = "GATHERING"
    SYNTHESIZING = "SYNTHESIZING"
    SYNTHESIZING_PARTIAL = "SYNTHESIZING_PARTIAL"
    PENDING_REVIEW = "PENDING_REVIEW"
    ALIGNING = "ALIGNING"
    BOOKED = "BOOKED"
    CLOSED = "CLOSED"


class SenderType(str, Enum):
    PATIENT = "PATIENT"
    AI_DOCTOR = "AI_DOCTOR"
    AI_COORDINATOR = "AI_COORDINATOR"


class AppointmentStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class StartPreConsultRequest(BaseModel):
    patient_id: UUID
    config_id: UUID


class ChatTurnRequest(BaseModel):
    session_id: UUID
    message: str


class DoctorReviewRequest(BaseModel):
    session_id: UUID
    doctor_review_notes: str


class BookAppointmentRequest(BaseModel):
    session_id: UUID
    patient_id: UUID
    expert_id: UUID
    scheduled_time: datetime

class PreConsultSessionResponse(BaseModel):
    session_id: UUID
    patient_id: UUID
    config_id: UUID
    status: PreConsultStatus
    current_confidence_score: float
    turn_count: int
    current_extracted_entities: Dict[str, Any]
