# Deployment Guide: Google Cloud Run

This guide details how to deploy the GarageAI Telephony Bridge to Google Cloud Run, a fully managed serverless platform perfect for handling WebSocket connections.

## 1. Prerequisites

- **Google Cloud CLI (`gcloud`)** installed and authenticated.
- **Docker** desktop installed.
- Valid **Google Cloud Project** created.

## 2. Configuration Steps

### 2.1 Set Project ID & Region
Set your variables in your terminal to avoid repetition:
```bash
export PROJECT_ID="your-google-cloud-project-id"
export REGION="europe-west4" # Recommended for Netherlands (Eemshaven) to minimize latency
export SERVICE_NAME="garageai-bridge"
```

### 2.2 Enable Required APIs
Ensure the following Google Cloud APIs are enabled:
```bash
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com
```

## 3. Deployment

We have provided a script `deployment/deploy_cloudrun.sh` to automate this, but here is the manual breakdown.

### Step 1: Build & Push Docker Image
Cloud Run deploys containers. First, build the image and push it to Google Artifact Registry (or Container Registry).

```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME
```

### Step 2: Deploy to Cloud Run
Deploy the service, exposing port 8080 and allowing unauthenticated access (required for Twilio Webhook).

**CRITICAL**: You must pass your `GOOGLE_API_KEY` as an environment variable.

```bash
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars GOOGLE_API_KEY="your_actual_gemini_api_key_here"
```

*Note: For production, consider using Google Secret Manager for the API Key.*

## 4. Post-Deployment

1. **Get Service URL**:
   After deployment, the terminal will output a Service URL ending in `.run.app`.
   Example: `https://garageai-bridge-x82la.europe-west4.run.app`

2. **Update Twilio**:
   You need to point your Twilio phone number to this new URL.
   
   - Go to your **Twilio Console** > **Phone Numbers**.
   - Select your active number.
   - Under "Voice", set "A call comes in" to **TwiML Bin**.
   - Update the TwiML Bin with the WebSocket URL.
     - **Scheme**: Change `https://` to `wss://`.
     - **Path**: Append `/ws/twilio`.
     - **Final URL Example**: `wss://garageai-bridge-x82la.europe-west4.run.app/ws/twilio`

## Troubleshooting

- **503 Service Unavailable**: Often means the application failed to start (e.g., crash on boot). Check Cloud Run logs.
- **403 Forbidden**: Ensure `--allow-unauthenticated` was used.
- **WebSocket Disconnects immediately**: Check `GOOGLE_API_KEY` validity in the Cloud Run Environment Variables.
