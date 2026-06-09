import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from backend.app.core.config import settings
from supabase import create_client
import datetime

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

session_id = "9acf054d-0683-4627-a5a3-18187d4e157a"
patient_id = "40623c61-8cd8-413f-a65e-c7cc9f3cdcc3"
doctor_id = "4a8f39b6-89d1-4db8-bbbe-d9616e00b8e2"

record = {
    "patient_id": patient_id,
    "session_id": session_id,
    "doctor_id": doctor_id,
    "scheduled_time": datetime.datetime.now().isoformat(),
    "status": "SCHEDULED"
}

try:
    res = supabase.table("appointments").insert(record).execute()
    print("Success:", res.data)
except Exception as e:
    print("Error:", e)
