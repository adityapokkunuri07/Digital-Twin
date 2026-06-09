import urllib.request
import json

try:
    req = urllib.request.Request("http://localhost:8000/api/pre-consult/appointments/all")
    with urllib.request.urlopen(req) as response:
        print(json.loads(response.read().decode()))
except Exception as e:
    print("Error:", e)
