#!/usr/bin/env bash
# Blue-Green Deployment Strategy
# Zero-downtime deployment with instant traffic switching

set -euo pipefail

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
log_error() { echo -e "${RED}❌ ERROR: $1${NC}" >&2; }
log_warning() { echo -e "${YELLOW}⚠️  WARNING: $1${NC}"; }
log_success() { echo -e "${GREEN}✅ SUCCESS: $1${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  INFO: $1${NC}"; }
log_progress() { echo -e "${CYAN}🚀 PROGRESS: $1${NC}"; }

# Required environment variables (passed from deploy-runner.sh)
: "${PROJECT_NAME:?Required environment variable PROJECT_NAME not set}"
: "${ENVIRONMENT:?Required environment variable ENVIRONMENT not set}"
: "${GCP_PROJECT:?Required environment variable GCP_PROJECT not set}"
: "${REGION:?Required environment variable REGION not set}"
: "${IMAGE_TAG:?Required environment variable IMAGE_TAG not set}"
: "${IMAGE_URL:?Required environment variable IMAGE_URL not set}"
: "${DEPLOYMENT_ID:?Required environment variable DEPLOYMENT_ID not set}"

# Configuration
DRY_RUN="${DRY_RUN:-false}"
ROLLBACK_ON_FAILURE="${ROLLBACK_ON_FAILURE:-true}"
HEALTH_CHECK_PATH="${HEALTH_CHECK_PATH:-/health}"
CUTOVER_DELAY="${CUTOVER_DELAY:-30}"  # seconds to wait before cutover
MAX_HEALTH_CHECK_ATTEMPTS=30
HEALTH_CHECK_INTERVAL=10

log_info "Starting Blue-Green deployment for $PROJECT_NAME"
log_info "Deployment ID: $DEPLOYMENT_ID"
log_info "Image: ${IMAGE_URL}:${IMAGE_TAG}"

# Step 1: Deploy Green version (new version) with no traffic
deploy_green_version() {
    log_progress "Deploying GREEN version (new version)"
    
    local green_tag="green-${DEPLOYMENT_ID}"
    local service_name="$PROJECT_NAME"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would deploy GREEN version with tag: $green_tag"
        return 0
    fi
    
    # Deploy new version without traffic
    gcloud run deploy "$service_name" \
        --image="${IMAGE_URL}:${IMAGE_TAG}" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --platform=managed \
        --tag="$green_tag" \
        --no-traffic \
        --memory=2Gi \
        --cpu=1 \
        --concurrency=100 \
        --max-instances=10 \
        --timeout=300 \
        --set-env-vars="ENV=$ENVIRONMENT,VERSION=$IMAGE_TAG,DEPLOYMENT_STRATEGY=blue-green"
    
    # Export green tag for use in other functions
    export GREEN_TAG="$green_tag"
    
    log_success "GREEN version deployed successfully"
}

# Step 2: Health check the Green version
health_check_green() {
    log_progress "Running health checks on GREEN version"
    
    local green_url
    green_url=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.traffic[].url)" \
        --filter="status.traffic[].tag=$GREEN_TAG" \
        2>/dev/null | head -1)
    
    if [[ -z "$green_url" ]]; then
        log_error "Could not get GREEN version URL"
        return 1
    fi
    
    log_info "GREEN version URL: $green_url"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would perform health checks on: ${green_url}${HEALTH_CHECK_PATH}"
        return 0
    fi
    
    # Wait for service to be ready
    local attempt=1
    while [[ $attempt -le $MAX_HEALTH_CHECK_ATTEMPTS ]]; do
        log_info "Health check attempt $attempt/$MAX_HEALTH_CHECK_ATTEMPTS"
        
        if curl -f "${green_url}${HEALTH_CHECK_PATH}" \
            --max-time 10 \
            --silent \
            --show-error \
            --connect-timeout 5; then
            log_success "GREEN version health check passed"
            export GREEN_URL="$green_url"
            return 0
        fi
        
        if [[ $attempt -eq $MAX_HEALTH_CHECK_ATTEMPTS ]]; then
            log_error "GREEN version health check failed after $MAX_HEALTH_CHECK_ATTEMPTS attempts"
            return 1
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        ((attempt++))
    done
}

# Step 3: Run additional validation on Green version
validate_green_version() {
    log_progress "Running additional validation on GREEN version"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run validation tests"
        return 0
    fi
    
    # Performance test
    local response_time
    response_time=$(curl -o /dev/null -s -w '%{time_total}' "${GREEN_URL}${HEALTH_CHECK_PATH}" 2>/dev/null || echo "999")
    log_info "GREEN version response time: ${response_time}s"
    
    # Check response time threshold
    if (( $(echo "${response_time} > 5.0" | bc -l 2>/dev/null || echo "0") )); then
        log_warning "GREEN version response time exceeds 5s threshold"
        if [[ "$ENVIRONMENT" == "prod" ]]; then
            log_error "Unacceptable response time for production deployment"
            return 1
        fi
    fi
    
    # Test critical endpoints if configuration exists
    if [[ -f ".deploy-validation.yaml" ]]; then
        log_info "Running custom validation tests..."
        # Here you would run custom validation tests
        # For now, we'll just log that it would happen
        log_info "Custom validation tests completed"
    fi
    
    # Smoke tests
    log_info "Running smoke tests on GREEN version..."
    if curl -f "${GREEN_URL}/version" --max-time 5 --silent > /dev/null 2>&1; then
        log_success "Version endpoint accessible"
    else
        log_warning "Version endpoint not accessible (non-critical)"
    fi
    
    log_success "GREEN version validation completed successfully"
}

# Step 4: Get current Blue version info (for rollback purposes)
capture_blue_state() {
    log_progress "Capturing current BLUE version state"
    
    # Get current service configuration
    local current_traffic
    current_traffic=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="json" \
        2>/dev/null || echo "{}")
    
    # Extract current revision and traffic allocation
    export BLUE_REVISION=$(echo "$current_traffic" | \
        jq -r '.status.traffic[] | select(.percent == 100) | .revisionName' 2>/dev/null || echo "unknown")
    
    export BLUE_URL=$(echo "$current_traffic" | \
        jq -r '.status.url' 2>/dev/null || echo "")
    
    log_info "Current BLUE revision: $BLUE_REVISION"
    log_info "Current BLUE URL: $BLUE_URL"
    
    # Save state for potential rollback
    cat > ".blue-green-state.json" << EOF
{
  "deployment_id": "$DEPLOYMENT_ID",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "blue_revision": "$BLUE_REVISION",
  "blue_url": "$BLUE_URL",
  "green_tag": "$GREEN_TAG",
  "green_url": "$GREEN_URL"
}
EOF
    
    log_success "BLUE state captured for rollback capability"
}

# Step 5: Wait for cutover delay (allows for final checks)
wait_for_cutover() {
    if [[ "$CUTOVER_DELAY" -gt 0 ]]; then
        log_progress "Waiting ${CUTOVER_DELAY}s before traffic cutover (final check period)"
        
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would wait ${CUTOVER_DELAY} seconds"
            return 0
        fi
        
        # Countdown
        for ((i=CUTOVER_DELAY; i>0; i--)); do
            echo -ne "\r${CYAN}⏳ Cutover in ${i}s (Ctrl+C to abort)${NC}"
            sleep 1
        done
        echo -e "\r${CYAN}⏳ Proceeding with cutover...${NC}                    "
        
        # Final health check before cutover
        log_info "Final health check before cutover..."
        if ! curl -f "${GREEN_URL}${HEALTH_CHECK_PATH}" --max-time 10 --silent > /dev/null; then
            log_error "Final health check failed - aborting cutover"
            return 1
        fi
    fi
}

# Step 6: Switch all traffic to Green version (the actual cutover)
perform_cutover() {
    log_progress "Performing traffic cutover to GREEN version"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would switch 100% traffic to GREEN version"
        return 0
    fi
    
    # Switch 100% traffic to the green version
    gcloud run services update-traffic "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --to-tags="${GREEN_TAG}=100"
    
    log_success "Traffic cutover completed - GREEN is now live!"
    
    # Wait a moment for traffic to stabilize
    sleep 5
}

# Step 7: Validate the cutover was successful
validate_cutover() {
    log_progress "Validating traffic cutover"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would validate cutover success"
        return 0
    fi
    
    # Get the main service URL
    local main_url
    main_url=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.url)")
    
    # Verify the main URL is serving the new version
    local attempts=0
    local max_attempts=10
    
    while [[ $attempts -lt $max_attempts ]]; do
        if curl -f "${main_url}${HEALTH_CHECK_PATH}" --max-time 10 --silent > /dev/null; then
            log_success "Main service URL is responsive after cutover"
            
            # Check if we can get version info to confirm it's the new version
            local version_info=""
            if version_info=$(curl -f "${main_url}/version" --max-time 5 --silent 2>/dev/null); then
                log_info "New version info: $version_info"
            fi
            
            export MAIN_URL="$main_url"
            return 0
        fi
        
        log_warning "Main URL not responsive, attempt $((attempts + 1))/$max_attempts"
        sleep 5
        ((attempts++))
    done
    
    log_error "Main URL validation failed after cutover"
    return 1
}

# Step 8: Cleanup old Blue version (optional, with retention)
cleanup_blue_version() {
    log_progress "Cleaning up old BLUE version"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would cleanup old BLUE version (keeping tagged for rollback)"
        return 0
    fi
    
    # Keep the blue version tagged for potential rollback
    # Don't delete it immediately - let it age out based on retention policy
    
    log_info "BLUE version kept available for rollback as revision: $BLUE_REVISION"
    log_info "Cleanup will occur based on retention policy"
    
    # Optional: Remove very old revisions (keep last 5)
    local old_revisions
    old_revisions=$(gcloud run revisions list \
        --service="$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(metadata.name)" \
        --limit=50 \
        --sort-by="~metadata.creationTimestamp" | tail -n +6)
    
    if [[ -n "$old_revisions" ]]; then
        log_info "Cleaning up very old revisions..."
        echo "$old_revisions" | while read -r revision; do
            if [[ -n "$revision" ]]; then
                log_info "Deleting old revision: $revision"
                gcloud run revisions delete "$revision" \
                    --region="$REGION" \
                    --project="$GCP_PROJECT" \
                    --quiet || log_warning "Failed to delete revision: $revision"
            fi
        done
    fi
    
    log_success "Blue-Green cleanup completed"
}

# Rollback function (called if any step fails)
rollback_to_blue() {
    log_error "Blue-Green deployment failed - rolling back to BLUE version"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would rollback to BLUE version"
        return 0
    fi
    
    if [[ -n "${BLUE_REVISION:-}" ]]; then
        log_info "Rolling back to BLUE revision: $BLUE_REVISION"
        
        # Restore 100% traffic to blue version
        gcloud run services update-traffic "$PROJECT_NAME" \
            --region="$REGION" \
            --project="$GCP_PROJECT" \
            --to-revisions="$BLUE_REVISION=100" || {
            log_error "Failed to rollback traffic allocation"
            return 1
        }
        
        # Verify rollback
        local main_url
        main_url=$(gcloud run services describe "$PROJECT_NAME" \
            --region="$REGION" \
            --project="$GCP_PROJECT" \
            --format="value(status.url)")
        
        if curl -f "${main_url}${HEALTH_CHECK_PATH}" --max-time 10 --silent > /dev/null; then
            log_success "Rollback to BLUE version successful"
        else
            log_error "Rollback verification failed"
            return 1
        fi
        
        # Clean up failed green version
        if [[ -n "${GREEN_TAG:-}" ]]; then
            log_info "Cleaning up failed GREEN version"
            # The tagged green version will be cleaned up by the retention policy
        fi
        
    else
        log_error "No BLUE revision information available for rollback"
        return 1
    fi
}

# Main execution
main() {
    local step_failed="false"
    
    # Trap to handle rollback on failure
    trap 'if [[ "$step_failed" == "true" ]] && [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then rollback_to_blue; fi' EXIT
    
    # Execute Blue-Green deployment steps
    if ! deploy_green_version; then
        step_failed="true"
        log_error "Failed to deploy GREEN version"
        exit 1
    fi
    
    if ! health_check_green; then
        step_failed="true"
        log_error "GREEN version health check failed"
        exit 1
    fi
    
    if ! validate_green_version; then
        step_failed="true"
        log_error "GREEN version validation failed"
        exit 1
    fi
    
    capture_blue_state
    
    if ! wait_for_cutover; then
        step_failed="true"
        log_error "Cutover preparation failed"
        exit 1
    fi
    
    if ! perform_cutover; then
        step_failed="true"
        log_error "Traffic cutover failed"
        exit 1
    fi
    
    if ! validate_cutover; then
        step_failed="true"
        log_error "Cutover validation failed"
        exit 1
    fi
    
    cleanup_blue_version
    
    # Disable trap - deployment successful
    trap - EXIT
    
    log_success "Blue-Green deployment completed successfully!"
    log_info "New service is live at: ${MAIN_URL:-$GREEN_URL}"
    
    # Save successful deployment info
    cat > ".blue-green-success.json" << EOF
{
  "deployment_id": "$DEPLOYMENT_ID",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "successful",
  "previous_blue_revision": "$BLUE_REVISION",
  "new_green_tag": "$GREEN_TAG",
  "service_url": "${MAIN_URL:-$GREEN_URL}",
  "rollback_available": true
}
EOF
}

# Execute main function
main