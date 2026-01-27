import requests
import json
import time

URL = "http://localhost:8000/chat"

# Mock Vapi Payload
payload = {
    "message": {
        "role": "user",
        "content": "I'm just checking the backtesting engine."
    },
    "call": {
        "id": "test-call-id-12345"
    }
}

print(f"🚀 Sending request to {URL}...")
print(f"📦 Payload: {json.dumps(payload, indent=2)}")

try:
    with requests.post(URL, json=payload, stream=True) as r:
        print(f"✅ Status Code: {r.status_code}")
        print("🌊 Streaming Response:")
        
        start_time = time.time()
        for line in r.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(f"[{time.time() - start_time:.2f}s] {decoded_line}")
                
except Exception as e:
    print(f"❌ Error: {e}")
