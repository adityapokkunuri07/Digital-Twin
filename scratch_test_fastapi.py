import asyncio
import os
import sys
import datetime
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from backend.app.core.config import settings
from supabase import create_client
import uuid

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# 1. Create a dummy session in ALIGNING state
session_id = str(uuid.uuid4())
patient_id = "40623c61-8cd8-413f-a65e-c7cc9f3cdcc3"
doctor_id = "4a8f39b6-89d1-4db8-bbbe-d9616e00b8e2"

supabase.table("pre_consultation_sessions").insert({
    "session_id": session_id,
    "patient_id": patient_id,
    "status": "ALIGNING"
}).execute()

print("Created session:", session_id)

# 2. Call the FastAPI endpoint
url = f"http://localhost:8000/api/pre-consult/book?patient_id={patient_id}"
payload = {
    "session_id": session_id,
    "patient_id": patient_id,
    "doctor_id": doctor_id,
    "scheduled_time": "2026-06-09T14:30:00.000Z"
}

try:
    res = requests.post(url, json=payload)
    print("Status code:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Error:", e)

