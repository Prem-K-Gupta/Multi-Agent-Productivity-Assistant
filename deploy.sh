#!/bin/bash
# Deploy Multi-Agent Productivity Assistant to Google Cloud Run
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated (gcloud auth login)
#   2. A Google Cloud project with billing enabled
#   3. Set your project: gcloud config set project YOUR_PROJECT_ID
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh

set -e

# Configuration - change these
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
SERVICE_NAME="nexus-assistant"
REGION="us-central1"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Deploying to Cloud Run..."
echo "  Project: $PROJECT_ID"
echo "  Service: $SERVICE_NAME"
echo "  Region:  $REGION"
echo ""

# Enable required APIs
echo "Enabling Cloud Run and Build APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com --quiet

# Build and deploy in one step (Cloud Build + Cloud Run)
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --timeout 60 \
    --set-env-vars "PORT=8080" \
    --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY:-}" \
    --quiet

# Get the service URL
URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format "value(status.url)")
echo ""
echo "Deployment complete!"
echo "Service URL: $URL"
echo ""
echo "To set Gemini API key:"
echo "  gcloud run services update $SERVICE_NAME --region $REGION --set-env-vars GEMINI_API_KEY=your_key"
