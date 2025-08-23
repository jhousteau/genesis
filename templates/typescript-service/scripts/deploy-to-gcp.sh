#!/bin/bash
# Genesis TypeScript Service GCP Deployment Script

set -euo pipefail

# Configuration
PROJECT_NAME="{{PROJECT_NAME}}"
ENVIRONMENT="${GENESIS_ENVIRONMENT:-development}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="${PROJECT_NAME}-${ENVIRONMENT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI not found. Please install Google Cloud CLI."
        exit 1
    fi

    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi

    # Check if project is set
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
    if [[ -z "$PROJECT_ID" ]]; then
        error "No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi

    success "Prerequisites check passed"
    log "Project ID: $PROJECT_ID"
    log "Region: $REGION"
    log "Service: $SERVICE_NAME"
}

# Build the application
build_application() {
    log "Building application..."

    # Install dependencies
    npm ci --production=false

    # Run build
    npm run build

    # Run tests
    npm test

    success "Application built successfully"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    log "Deploying to Cloud Run..."

    # Deploy using gcloud
    gcloud run deploy "$SERVICE_NAME" \
        --source . \
        --platform managed \
        --region "$REGION" \
        --allow-unauthenticated \
        --set-env-vars="NODE_ENV=${ENVIRONMENT}" \
        --set-env-vars="GENESIS_ENVIRONMENT=${ENVIRONMENT}" \
        --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
        --set-env-vars="GOOGLE_CLOUD_REGION=${REGION}" \
        --memory="1Gi" \
        --cpu="1" \
        --concurrency="100" \
        --timeout="300" \
        --max-instances="10" \
        --min-instances="0" \
        --port="8080"

    success "Deployed to Cloud Run"
}

# Get service URL
get_service_url() {
    log "Getting service URL..."

    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --platform managed \
        --region "$REGION" \
        --format "value(status.url)")

    success "Service URL: $SERVICE_URL"

    # Test the health endpoint
    log "Testing health endpoint..."
    if curl -f "${SERVICE_URL}/health" >/dev/null 2>&1; then
        success "Health check passed"
    else
        warning "Health check failed - service may still be starting up"
    fi
}

# Setup monitoring (if enabled)
setup_monitoring() {
    if [[ "${ENABLE_METRICS:-true}" == "true" ]]; then
        log "Setting up monitoring..."

        # This would typically set up Cloud Monitoring dashboards
        # For now, just log the metrics endpoint
        success "Metrics available at: ${SERVICE_URL}/metrics"
    fi
}

# Main deployment flow
main() {
    log "Starting deployment of $PROJECT_NAME to $ENVIRONMENT environment"

    check_prerequisites
    build_application
    deploy_to_cloud_run
    get_service_url
    setup_monitoring

    success "Deployment completed successfully!"
    log "Service is available at: $SERVICE_URL"
}

# Run main function
main "$@"
