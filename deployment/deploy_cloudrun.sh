#!/bin/bash

# Configuration
PROJECT_ID="your-gcp-project-id"
REGION="europe-west4" # E.g., Netherlands/Belgium region
SERVICE_NAME="garageai-bridge"

echo "Deploying $SERVICE_NAME to Google Cloud Run..."
echo "Ensure you have authenticated: gcloud auth login"

# 1. Build the container image using Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# 2. Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY,TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID

echo "Deployment complete."
