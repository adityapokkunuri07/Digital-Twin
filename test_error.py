import urllib.request, json
import urllib.error

url = 'http://localhost:8000/api/session/0afb9d62-90b0-41cb-a3b6-0604ef6b09ab/doctor-inject'
data = json.dumps({"message": "Hello"}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as f:
        print(f.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode('utf-8'))
except Exception as e:
    print(e)
