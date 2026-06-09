import requests
import datetime

url = "http://localhost:8000/api/pre-consult/book?patient_id=40623c61-8cd8-413f-a65e-c7cc9f3cdcc3"
payload = {
    "session_id": "4f3ece5d-edcf-4048-b40a-694a71c8b734",
    "patient_id": "40623c61-8cd8-413f-a65e-c7cc9f3cdcc3",
    "doctor_id": "4a8f39b6-89d1-4db8-bbbe-d9616e00b8e2",
    "scheduled_time": "2026-06-09T14:30:00.000Z"
}

try:
    res = requests.post(url, json=payload)
    print("Status code:", res.status_code)
    print("Response:", res.json())
except Exception as e:
    print("Error:", e)
