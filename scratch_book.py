import urllib.request
import json
import uuid
import datetime

session_id = str(uuid.uuid4())
patient_id = str(uuid.uuid4())
expert_id = str(uuid.uuid4())

data = json.dumps({
    "session_id": session_id,
    "patient_id": patient_id,
    "expert_id": expert_id,
    "scheduled_time": datetime.datetime.now().isoformat()
}).encode("utf-8")

try:
    req = urllib.request.Request("http://localhost:8000/api/pre-consult/book", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as response:
        print(json.loads(response.read().decode()))
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code)
    print("Response:", e.read().decode())
except Exception as e:
    print("Error:", e)
