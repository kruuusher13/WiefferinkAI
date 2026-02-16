# 📋 GarageAI: Unified Cloud Deployment & Validation Plan (BMAD)

**Version:** 1.1 (Optimized for GCP Only)  
**Status:** Ready for Client Validation  
**Owner:** Jan (Product Manager)

---

## 🎯 [B] Business: The Goal
Validate GarageAI with a pilot client using a **Unified Google Cloud infrastructure**. One provider, one dashboard, and zero local server footprint beyond the data tunnel.

---

## 📈 [M] Market & Client Context
- **Client:** Local Garage (WinCar user).
- **Setup:** Hybrid Cloud. Real-time voice inference on GCP, connecting to on-premise WinCar data via secure tunnel.

---

## 🚀 [D] Delivery: Unified Technical Implementation

### Step 1: Local Data Bridge (The Tunnel)
On the garage's WinCar server:
1. Run `ngrok tcp 1433`.
2. **Capture:** The Forwarding address (e.g., `0.tcp.eu.ngrok.io:12345`).

### Step 2: Set Environment Variables
```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="europe-west4"
export GOOGLE_API_KEY="your-gemini-key"
export WINCAR_TUNNEL="0.tcp.eu.ngrok.io:12345"
```

### Step 3: Deploy the Brain (Telephony Bridge)
```bash
# Build & Deploy Bridge
gcloud builds submit --tag gcr.io/$PROJECT_ID/garageai-bridge
gcloud run deploy garageai-bridge \
  --image gcr.io/$PROJECT_ID/garageai-bridge \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY,WINCAR_DB_CONNECTION=DRIVER={ODBC Driver 17 for SQL Server};SERVER=$WINCAR_TUNNEL;DATABASE=WinCarLive;UID=sa;PWD=StrongPassword123!"
```
**Note:** Copy the `Service URL` provided at the end (e.g., `https://bridge-xxx.a.run.app`).

### Step 4: Deploy the Eyes (Command Center)
```bash
cd garage-ai-command-center

# Build with bridge URL baked in (Next.js requires NEXT_PUBLIC_ vars at build time)
gcloud builds submit \
  --tag gcr.io/$PROJECT_ID/garageai-dashboard \
  --build-arg NEXT_PUBLIC_BRIDGE_URL=https://bridge-xxx.a.run.app

# Deploy
gcloud run deploy garageai-dashboard \
  --image gcr.io/$PROJECT_ID/garageai-dashboard \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi
```

### Step 5: Twilio Integration
Point your Twilio phone number (WebSocket) to:
`wss://bridge-xxx.a.run.app/ws/twilio`

---

## 💰 Estimated Cost (Pilot Phase)
| Component | Cost (Monthly) |
| :--- | :--- |
| **GCP Services (Bridge + Dashboard)** | **$0.00** (Within Free Tier) |
| **Twilio (Number + Minutes)** | **~$2.50** |
| **TOTAL** | **~$2.50** |

---

## ✅ Success Verification
1. Call the garage's new AI number.
2. Open the `garageai-dashboard` Cloud Run URL on your tablet.
3. Verify that Harry identifies the customer and the dashboard shows the "Live Stream" status.
