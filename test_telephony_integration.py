
import asyncio
import websockets
import json
import base64
import subprocess
import time
import numpy as np
import scipy.io.wavfile
import os
import signal
import sys
from bridge.audio import AudioResampler

# Configuration
BRIDGE_URL = "ws://localhost:8000/ws/twilio"
MOCK_GEMINI_PORT = 9000
MOCK_GEMINI_URL = f"ws://localhost:{MOCK_GEMINI_PORT}"
TEST_TEXT = "Ik wil een afspraak maken voor een grote beurt"
AUDIO_FILE = "test_input.wav"
REPORT_FILE = "test_report.md"

# --- MOCK GEMINI SERVER ---
async def mock_gemini_handler(websocket):
    print("Mock Gemini: Connected")
    try:
        async for message in websocket:
            data = json.loads(message)
            
            # 1. Handle Setup
            if "setup" in data:
                print("Mock Gemini: Received Setup")
                # Confirm setup? Protocol doesn't strict require immediate response but usually sends empty toolInit or similar.
                pass
                
            # 2. Handle Audio (Realtime Input)
            if "realtime_input" in data:
                # We received audio. We should respond with a Tool Call after a bit.
                # Simulate 'thinking' then 'interrupting' with a tool call.
                
                # Check if we should trigger the tool call
                # Just trigger it immediately for the test
                print("Mock Gemini: Received Audio, sending Tool Call")
                
                tool_call_msg = {
                    "toolCall": {
                        "functionCalls": [{
                            "name": "book_appointment",
                            "args": {"type": "grote beurt", "date": "tomorrow"},
                            "id": "call_123"
                        }]
                    }
                }
                await websocket.send(json.dumps(tool_call_msg))
                
                # Also send some audio back?
                # "serverContent": {"modelTurn": {"parts": [{"inlineData": ...}]}}
                # Generate silence or noise as dummy audio
                dummy_pcm = np.zeros(1600, dtype=np.int16).tobytes() # 100ms silence
                b64_audio = base64.b64encode(dummy_pcm).decode("utf-8")
                
                audio_msg = {
                    "serverContent": {
                        "modelTurn": {
                            "parts": [{
                                "inlineData": {
                                    "mimeType": "audio/pcm",
                                    "data": b64_audio
                                }
                            }]
                        }
                    }
                }
                await websocket.send(json.dumps(audio_msg))
                
            # 3. Handle Tool Response
            if "tool_response" in data:
                 print("Mock Gemini: Received Tool Response")
                 # Test complete?

    except Exception as e:
        print(f"Mock Gemini Error: {e}")

async def start_mock_gemini():
    async with websockets.serve(mock_gemini_handler, "localhost", MOCK_GEMINI_PORT):
        print(f"Mock Gemini Server started on port {MOCK_GEMINI_PORT}")
        await asyncio.Future() # run forever

# --- TEST CLIENT Helpers ---
def generate_audio(text, filename):
    print(f"Generating audio for: '{text}'")
    cmd = ["say", "-o", filename, "--data-format=LEI16@16000", text] 
    subprocess.run(cmd, check=True)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"{filename} was not created")

def load_audio_as_pcm16(filename):
    try:
        rate, data = scipy.io.wavfile.read(filename)
        if rate != 16000:
            print(f"Warning: Audio rate is {rate}")
        if data.dtype != np.int16:
            data = (data * 32767).astype(np.int16)
        return data
    except ValueError:
        with open(filename, "rb") as f:
            data = np.frombuffer(f.read(), dtype=np.int16)
        return data

def add_noise(pcm_data, noise_level=0.0):
    if noise_level == 0:
        return pcm_data
    noise = np.random.normal(0, noise_level * 32768, len(pcm_data))
    noisy_signal = pcm_data + noise
    return np.clip(noisy_signal, -32768, 32767).astype(np.int16)

async def run_client(pcm_data, resampler):
    """Simulate Twilio Client."""
    # Retries for connection
    connected = False
    for i in range(5):
        try:
            async with websockets.connect(BRIDGE_URL) as ws:
                connected = True
                print("Client Connected to Bridge.")
                
                # 1. Send Start
                stream_sid = "test_stream_123"
                await ws.send(json.dumps({
                    "event": "start",
                    "start": {"streamSid": stream_sid}
                }))
                
                # 2. Stream Audio
                chunk_len = 320 # 20ms of 16k? No wait. 
                # 8k standard packet is 20ms = 160 samples.
                # 16k source -> 320 samples per 20ms chunk?
                # The bridge takes 8k mu-law.
                # So we must convert output first.
                
                # Real logic: Twilio gives 8k mu-law.
                # Our client must SIMULATE Twilio.
                # So we take our 16k PCM, convert to 8k mu-law, then send.
                
                # Convert whole buffer first
                full_mulaw = resampler.pcm_to_mulaw(pcm_data.tobytes())
                
                # Chunk into 160 bytes (20ms of 8kHz)
                chunk_size = 160
                total_chunks = len(full_mulaw) // chunk_size
                
                print(f"Streaming {total_chunks} chunks...")
                
                start_time = time.time()
                for i in range(0, len(full_mulaw), chunk_size):
                    chunk = full_mulaw[i:i+chunk_size]
                    payload = base64.b64encode(chunk).decode("utf-8")
                    
                    await ws.send(json.dumps({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": payload}
                    }))
                    await asyncio.sleep(0.01) # fast stream

                streaming_end_time = time.time()
                
                # 3. Wait for response
                first_audio_received = False
                latency = 0
                
                try:
                    while True:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)
                        
                        if data.get("event") == "media":
                            if not first_audio_received:
                                first_audio_received = True
                                latency = (time.time() - streaming_end_time) * 1000
                                print(f"First audio response received! Latency: {latency:.2f}ms")
                                return latency, True
                except asyncio.TimeoutError:
                    return 0, False
                    
        except ConnectionRefusedError:
            print("Connection refused, retrying...")
            await asyncio.sleep(1)
            continue
        except Exception as e:
            print(f"Client Error: {e}")
            return 0, False
            
    return 0, False

async def main():
    # 0. Setup
    resampler = AudioResampler()
    if os.path.exists(AUDIO_FILE): os.remove(AUDIO_FILE)
    generate_audio(TEST_TEXT, AUDIO_FILE)
    pcm_data = load_audio_as_pcm16(AUDIO_FILE)
    
    # 1. Start Mock Gemini (in background task)
    mock_task = asyncio.create_task(start_mock_gemini())
    await asyncio.sleep(1) # wait for mock start
    
    # 2. Start Bridge Server
    print("Starting Telephony Bridge...")
    env = os.environ.copy()
    env["GEMINI_URL_OVERRIDE"] = MOCK_GEMINI_URL
    
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn",  "bridge.telephony:app", "--port", "8000", "--env-file", ".env"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    # Wait for server to start
    await asyncio.sleep(3)
    
    report_lines = ["# Telephony Bridge Test Report", "", "## Test Run Results"]
    
    try:
        # 3. Run Tests
        print("\n--- Running Happy Path Test ---")
        latency, success = await run_client(pcm_data, resampler)
        status = "PASS" if success else "FAIL"
        report_lines.append(f"- **Happy Path**: {status}")
        report_lines.append(f"  - Latency: {latency:.2f}ms")
        
        print("\n--- Running Noise Test ---")
        noisy_pcm = add_noise(pcm_data, 0.1)
        latency_noise, success_noise = await run_client(noisy_pcm, resampler)
        status_noise = "PASS" if success_noise else "FAIL" 
        report_lines.append(f"- **Noise Test (10%)**: {status_noise}")
        report_lines.append(f"  - Latency: {latency_noise:.2f}ms")
        
    finally:
        server_process.terminate()
        mock_task.cancel()
        try:
            stdout, stderr = server_process.communicate(timeout=2)
        except:
             server_process.kill()
             stdout, stderr = server_process.communicate()

    # Tool Call Verification
    if "Tool Call: book_appointment" in stderr:
        tool_status = "PASS"
    else:
        tool_status = "FAIL (See logs)"
    report_lines.append(f"- **Tool Call Verification**: {tool_status}")
    
    report_lines.append("\n## Server Logs")
    report_lines.append("```")
    report_lines.append(stderr[-2000:] if stderr else "No stderr")
    report_lines.append("```")

    with open(REPORT_FILE, "w") as f:
        f.write("\n".join(report_lines))
    print(f"\nReport written to {REPORT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
