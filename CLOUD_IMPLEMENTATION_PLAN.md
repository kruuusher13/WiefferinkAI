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

## 🛡️ Security & Data Safety (GDPR Ready)
*This section ensures client trust and data integrity.*

1. **Zero Training:** We use the Google Gemini API (Enterprise Tier). Customer data is **not** used to train Google's global models.
2. **Read-Only Access:** We use a dedicated SQL user that can only *read* data. GarageAI cannot delete or modify WinCar records.
3. **Encrypted Tunnels:** All communication between the Garage and the Cloud is encrypted via ngrok's TLS tunnel.
4. **Secret Management:** Sensitive keys are stored in Google Secret Manager, never in the code or logs.

---

## 🚀 [D] Delivery: Unified Technical Implementation

### Step 1: Local Data Bridge (The Tunnel)
On the garage's WinCar server:
1. Run `ngrok tcp 1433 --request-header-add "X-Garage-Auth: [RANDOM_KEY]"`.
2. **Capture:** The Forwarding address (e.g., `0.tcp.eu.ngrok.io:12345`).

### Step 2: Set Environment Variables & Secrets
```bash
# 1. Store secrets in GCP (Run these once)
echo -n "your-gemini-key" | gcloud secrets create GEMINI_API_KEY --data-file=-
echo -n "DRIVER={ODBC Driver 17 for SQL Server};SERVER=[NGROK_URL];DATABASE=WinCarLive;UID=garageai_user;PWD=[PWD]" | gcloud secrets create WINCAR_DB_CONN --data-file=-

# 2. Set project variables
export PROJECT_ID="your-gcp-project-id"
export REGION="europe-west4"
```

### Step 3: Deploy the Brain (Telephony Bridge)
We now pull secrets directly from Secret Manager:
```bash
gcloud run deploy garageai-bridge \
  --image gcr.io/$PROJECT_ID/garageai-bridge \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-secrets "GOOGLE_API_KEY=GEMINI_API_KEY:latest,WINCAR_DB_CONNECTION=WINCAR_DB_CONN:latest"
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
