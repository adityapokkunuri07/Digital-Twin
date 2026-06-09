from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
import json

class BookAppointmentRequest(BaseModel):
    session_id: UUID
    patient_id: UUID
    doctor_id: UUID
    scheduled_time: datetime

data = {
    "session_id": "9acf054d-0683-4627-a5a3-18187d4e157a",
    "patient_id": "40623c61-8cd8-413f-a65e-c7cc9f3cdcc3",
    "doctor_id": "4a8f39b6-89d1-4db8-bbbe-d9616e00b8e2",
    "scheduled_time": "2026-06-09T14:30:00.000Z"
}

try:
    req = BookAppointmentRequest(**data)
    print("Parsed successfully:", req.scheduled_time)
except Exception as e:
    print("Error parsing:", e)
