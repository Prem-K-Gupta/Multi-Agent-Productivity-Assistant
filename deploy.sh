#!/bin/bash
# deploy.sh — One-command Cloud Run deployment for Nexus AI
# Usage: ./deploy.sh <YOUR_GCP_PROJECT_ID>

set -e

PROJECT_ID=${1:-"genai-academy-track-3"}
REGION="us-central1"
SERVICE_NAME="nexus-assistant"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying Nexus to Cloud Run..."
echo "   Project: $PROJECT_ID"
echo "   Region:  $REGION"
echo "   Service: $SERVICE_NAME"

# 1. Build & push Docker image
echo ""
echo "📦 Building and pushing Docker image..."
gcloud builds submit --tag "$IMAGE" .

# 2. Deploy to Cloud Run
echo ""
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}" \
  --set-env-vars "BASE_URL=PLACEHOLDER"

# 3. Get the deployed URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
  --format "value(status.url)")

echo ""
echo "✅ Deployed! Service URL: $SERVICE_URL"

# 4. Set BASE_URL to the real Cloud Run URL
echo ""
echo "🔗 Setting BASE_URL to $SERVICE_URL ..."
gcloud run services update "$SERVICE_NAME" \
  --region "$REGION" \
  --set-env-vars "BASE_URL=${SERVICE_URL},GEMINI_API_KEY=${GEMINI_API_KEY}"

echo ""
echo "🎉 DONE! Your app is live at: $SERVICE_URL"
echo ""
echo "⚠️  NEXT STEP: Add this Authorized Redirect URI to Google Cloud Console:"
echo "   ${SERVICE_URL}/api/auth/google/callback"
