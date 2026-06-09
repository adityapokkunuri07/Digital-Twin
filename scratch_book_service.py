import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from backend.app.core.config import settings
from backend.app.api.dependencies import provider
import datetime
from uuid import UUID

async def test_book():
    provider.initialize()
    service = provider.preconsult_service
    
    session_id = UUID("9acf054d-0683-4627-a5a3-18187d4e157a")
    patient_id = UUID("40623c61-8cd8-413f-a65e-c7cc9f3cdcc3")
    doctor_id = UUID("4a8f39b6-89d1-4db8-bbbe-d9616e00b8e2")
    scheduled_time = datetime.datetime.now()
    
    try:
        res = await service.book_appointment(session_id, patient_id, doctor_id, scheduled_time)
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test_book())
