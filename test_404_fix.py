import requests
import json
import time

# Test the weird Vapi behavior URL
URL = "http://localhost:8000/chat/chat/completions"

# Mock Vapi Payload
payload = {
    "message": {
        "role": "user",
        "content": "Testing the 404 fix override route."
    },
    "call": {
        "id": "test-call-404-fix"
    }
}

print(f"🚀 Sending request to WEIRD URL: {URL}...")
try:
    with requests.post(URL, json=payload, stream=True) as r:
        print(f"✅ Status Code: {r.status_code}")
        if r.status_code == 200:
            print("SUCCESS: Route is reachable!")
        else:
            print(f"FAILURE: Got {r.status_code}")
            
except Exception as e:
    print(f"❌ Error: {e}")
