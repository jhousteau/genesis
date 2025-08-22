#!/usr/bin/env bash
# Rolling Deployment Strategy
# Standard Cloud Run deployment with health monitoring

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
DEPLOYMENT_MODE="${DEPLOYMENT_MODE:-rolling}"  # rolling or recreate
HEALTH_CHECK_PATH="${HEALTH_CHECK_PATH:-/health}"
MAX_HEALTH_CHECK_ATTEMPTS=30
HEALTH_CHECK_INTERVAL=10

# Rolling deployment configuration
MAX_UNAVAILABLE="${MAX_UNAVAILABLE:-25}"  # Percentage
MAX_SURGE="${MAX_SURGE:-25}"             # Percentage

log_info "Starting Rolling deployment for $PROJECT_NAME"
log_info "Deployment ID: $DEPLOYMENT_ID"
log_info "Image: ${IMAGE_URL}:${IMAGE_TAG}"
log_info "Mode: $DEPLOYMENT_MODE"

# Global variables
PREVIOUS_REVISION=""
SERVICE_URL=""

# Step 1: Capture current state for rollback
capture_current_state() {
    log_progress "Capturing current deployment state"
    
    # Get current revision for rollback capability
    PREVIOUS_REVISION=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.traffic[].revisionName)" \
        --filter="status.traffic[].percent=100" 2>/dev/null | head -1 || echo "")
    
    if [[ -n "$PREVIOUS_REVISION" ]]; then
        log_info "Current revision: $PREVIOUS_REVISION"
    else
        log_info "No existing revision found (first deployment)"
    fi
    
    # Get current service URL if exists
    SERVICE_URL=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [[ -n "$SERVICE_URL" ]]; then
        log_info "Current service URL: $SERVICE_URL"
    fi
}

# Step 2: Deploy new revision
deploy_new_revision() {
    log_progress "Deploying new revision"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would deploy new revision with image: ${IMAGE_URL}:${IMAGE_TAG}"
        return 0
    fi
    
    local deploy_args=(
        "run" "deploy" "$PROJECT_NAME"
        "--image=${IMAGE_URL}:${IMAGE_TAG}"
        "--region=$REGION"
        "--project=$GCP_PROJECT"
        "--platform=managed"
        "--memory=2Gi"
        "--cpu=1"
        "--concurrency=100"
        "--max-instances=10"
        "--timeout=300"
        "--set-env-vars=ENV=$ENVIRONMENT,VERSION=$IMAGE_TAG,DEPLOYMENT_STRATEGY=rolling"
    )
    
    # Add deployment-specific configurations
    case "$DEPLOYMENT_MODE" in
        recreate)
            # For recreate mode, we might want to temporarily reduce instances
            deploy_args+=("--min-instances=0")
            ;;
        rolling)
            # Standard rolling deployment
            if [[ "$ENVIRONMENT" == "prod" ]]; then
                deploy_args+=("--min-instances=1")
            else
                deploy_args+=("--min-instances=0")
            fi
            ;;
    esac
    
    # Set traffic allocation
    if [[ "$DEPLOYMENT_MODE" == "recreate" ]] && [[ -n "$PREVIOUS_REVISION" ]]; then
        # For recreate mode, initially deploy with no traffic
        deploy_args+=("--no-traffic")
        deploy_args+=("--tag=new-${DEPLOYMENT_ID}")
    else
        # For rolling deployment, allow traffic to flow to new revision
        deploy_args+=("--allow-unauthenticated")
    fi
    
    # Execute deployment
    log_info "Executing Cloud Run deployment..."
    gcloud "${deploy_args[@]}"
    
    # Get the new revision name
    local new_revision
    new_revision=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.latestReadyRevisionName)" 2>/dev/null)
    
    export NEW_REVISION="$new_revision"
    log_success "New revision deployed: $NEW_REVISION"
    
    # Update service URL
    SERVICE_URL=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.url)")
    
    export SERVICE_URL
}

# Step 3: Handle recreate mode traffic switching
handle_recreate_mode() {
    if [[ "$DEPLOYMENT_MODE" != "recreate" ]]; then
        return 0
    fi
    
    log_progress "Handling recreate mode traffic switching"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would switch traffic for recreate mode"
        return 0
    fi
    
    # Wait a moment for the new revision to stabilize
    log_info "Waiting for new revision to stabilize..."
    sleep 30
    
    # Switch all traffic to the new revision
    gcloud run services update-traffic "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --to-revisions="$NEW_REVISION=100"
    
    log_success "Traffic switched to new revision in recreate mode"
}

# Step 4: Wait for deployment to stabilize
wait_for_stabilization() {
    log_progress "Waiting for deployment to stabilize"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would wait for deployment stabilization"
        return 0
    fi
    
    # Check if service is ready
    local attempt=1
    while [[ $attempt -le 10 ]]; do
        local ready_conditions
        ready_conditions=$(gcloud run services describe "$PROJECT_NAME" \
            --region="$REGION" \
            --project="$GCP_PROJECT" \
            --format="value(status.conditions[].status)" \
            --filter="status.conditions[].type=Ready" 2>/dev/null)
        
        if [[ "$ready_conditions" == "True" ]]; then
            log_success "Service is ready"
            break
        fi
        
        if [[ $attempt -eq 10 ]]; then
            log_error "Service failed to become ready after 10 attempts"
            return 1
        fi
        
        log_info "Waiting for service to be ready... (attempt $attempt/10)"
        sleep 15
        ((attempt++))
    done
    
    # Additional stabilization wait
    log_info "Allowing additional time for deployment to stabilize..."
    sleep 30
}

# Step 5: Comprehensive health checks
run_health_checks() {
    log_progress "Running comprehensive health checks"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run health checks on: ${SERVICE_URL}${HEALTH_CHECK_PATH}"
        return 0
    fi
    
    if [[ -z "$SERVICE_URL" ]]; then
        log_error "Service URL not available for health checks"
        return 1
    fi
    
    local attempt=1
    local consecutive_successes=0
    local required_successes=3
    
    while [[ $attempt -le $MAX_HEALTH_CHECK_ATTEMPTS ]]; do
        log_info "Health check attempt $attempt/$MAX_HEALTH_CHECK_ATTEMPTS (need $required_successes consecutive successes)"
        
        if curl -f "${SERVICE_URL}${HEALTH_CHECK_PATH}" \
            --max-time 10 \
            --silent \
            --show-error \
            --connect-timeout 5; then
            
            consecutive_successes=$((consecutive_successes + 1))
            log_success "Health check passed ($consecutive_successes/$required_successes)"
            
            if [[ $consecutive_successes -ge $required_successes ]]; then
                log_success "All health checks passed!"
                return 0
            fi
        else
            consecutive_successes=0
            log_warning "Health check failed, resetting success counter"
        fi
        
        if [[ $attempt -eq $MAX_HEALTH_CHECK_ATTEMPTS ]]; then
            log_error "Health checks failed after $MAX_HEALTH_CHECK_ATTEMPTS attempts"
            return 1
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        ((attempt++))
    done
}

# Step 6: Performance validation
validate_performance() {
    log_progress "Running performance validation"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run performance validation"
        return 0
    fi
    
    # Response time test
    local response_times=()
    local failed_requests=0
    local total_requests=5
    
    log_info "Testing response times ($total_requests samples)..."
    
    for ((i=1; i<=total_requests; i++)); do
        local response_time
        if response_time=$(curl -o /dev/null -s -w '%{time_total}' "${SERVICE_URL}${HEALTH_CHECK_PATH}" --max-time 10 2>/dev/null); then
            response_times+=("$response_time")
            log_info "Request $i: ${response_time}s"
        else
            failed_requests=$((failed_requests + 1))
            log_warning "Request $i: FAILED"
        fi
        sleep 1
    done
    
    # Calculate average response time
    if [[ ${#response_times[@]} -gt 0 ]]; then
        local total_time=0
        for time in "${response_times[@]}"; do
            total_time=$(echo "$total_time + $time" | bc -l)
        done
        local avg_time=$(echo "scale=3; $total_time / ${#response_times[@]}" | bc -l)
        local avg_time_ms=$(echo "$avg_time * 1000" | bc -l | cut -d. -f1)
        
        log_info "Average response time: ${avg_time}s (${avg_time_ms}ms)"
        
        # Check if response time is acceptable
        if (( $(echo "$avg_time > 5.0" | bc -l) )); then
            log_warning "Average response time exceeds 5s threshold"
            if [[ "$ENVIRONMENT" == "prod" ]]; then
                log_error "Unacceptable response time for production"
                return 1
            fi
        fi
    fi
    
    # Check failure rate
    local failure_rate=$(echo "scale=2; $failed_requests * 100 / $total_requests" | bc -l)
    log_info "Request failure rate: ${failure_rate}%"
    
    if (( $(echo "$failure_rate > 20" | bc -l) )); then
        log_error "Request failure rate ${failure_rate}% exceeds 20% threshold"
        return 1
    fi
    
    log_success "Performance validation completed successfully"
}

# Step 7: Test critical endpoints
test_critical_endpoints() {
    log_progress "Testing critical endpoints"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would test critical endpoints"
        return 0
    fi
    
    # Define critical endpoints to test
    local endpoints=(
        "$HEALTH_CHECK_PATH"
        "/version"
        "/ready"
    )
    
    local failed_endpoints=()
    
    for endpoint in "${endpoints[@]}"; do
        log_info "Testing endpoint: $endpoint"
        
        if curl -f "${SERVICE_URL}${endpoint}" --max-time 10 --silent > /dev/null 2>&1; then
            log_success "Endpoint $endpoint is accessible"
        else
            log_warning "Endpoint $endpoint is not accessible"
            failed_endpoints+=("$endpoint")
        fi
    done
    
    # Only fail if critical endpoints are not accessible
    if [[ "${#failed_endpoints[@]}" -gt 0 ]]; then
        log_warning "Some endpoints are not accessible: ${failed_endpoints[*]}"
        
        # Only fail if health endpoint is not accessible
        for failed in "${failed_endpoints[@]}"; do
            if [[ "$failed" == "$HEALTH_CHECK_PATH" ]]; then
                log_error "Critical health endpoint is not accessible"
                return 1
            fi
        done
        
        log_warning "Non-critical endpoints failed, but deployment can continue"
    fi
    
    log_success "Critical endpoint testing completed"
}

# Step 8: Clean up old revisions (keep retention policy)
cleanup_old_revisions() {
    log_progress "Cleaning up old revisions"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would clean up old revisions"
        return 0
    fi
    
    # Keep the last 5 revisions for rollback capability
    local revisions_to_keep=5
    
    local old_revisions
    old_revisions=$(gcloud run revisions list \
        --service="$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(metadata.name)" \
        --limit=50 \
        --sort-by="~metadata.creationTimestamp" | tail -n +$((revisions_to_keep + 1)))
    
    if [[ -n "$old_revisions" ]]; then
        log_info "Cleaning up old revisions (keeping $revisions_to_keep most recent)..."
        
        echo "$old_revisions" | while read -r revision; do
            if [[ -n "$revision" ]]; then
                log_info "Deleting old revision: $revision"
                gcloud run revisions delete "$revision" \
                    --region="$REGION" \
                    --project="$GCP_PROJECT" \
                    --quiet || log_warning "Failed to delete revision: $revision"
            fi
        done
        
        log_success "Old revision cleanup completed"
    else
        log_info "No old revisions to clean up"
    fi
}

# Rollback function
rollback_deployment() {
    log_error "Rolling deployment failed - initiating rollback"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would rollback to previous revision"
        return 0
    fi
    
    if [[ -n "$PREVIOUS_REVISION" ]]; then
        log_info "Rolling back to previous revision: $PREVIOUS_REVISION"
        
        # Restore 100% traffic to previous revision
        gcloud run services update-traffic "$PROJECT_NAME" \
            --region="$REGION" \
            --project="$GCP_PROJECT" \
            --to-revisions="$PREVIOUS_REVISION=100" || {
            log_error "Failed to rollback traffic allocation"
            return 1
        }
        
        # Verify rollback
        local rollback_url
        rollback_url=$(gcloud run services describe "$PROJECT_NAME" \
            --region="$REGION" \
            --project="$GCP_PROJECT" \
            --format="value(status.url)")
        
        if curl -f "${rollback_url}${HEALTH_CHECK_PATH}" --max-time 10 --silent > /dev/null; then
            log_success "Rollback successful - service restored"
        else
            log_error "Rollback verification failed"
            return 1
        fi
        
        # Clean up failed revision if it exists
        if [[ -n "${NEW_REVISION:-}" ]]; then
            log_info "Failed revision will be cleaned up by retention policy"
        fi
        
    else
        log_warning "No previous revision available for rollback"
        log_info "This might be the first deployment"
    fi
}

# Save deployment state
save_deployment_state() {
    local status="$1"
    
    cat > ".rolling-deployment-state.json" << EOF
{
  "deployment_id": "$DEPLOYMENT_ID",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "$status",
  "deployment_mode": "$DEPLOYMENT_MODE",
  "previous_revision": "$PREVIOUS_REVISION",
  "new_revision": "${NEW_REVISION:-}",
  "service_url": "$SERVICE_URL",
  "image_tag": "$IMAGE_TAG",
  "image_url": "$IMAGE_URL",
  "rollback_available": $([ -n "$PREVIOUS_REVISION" ] && echo "true" || echo "false")
}
EOF
}

# Main execution
main() {
    local step_failed="false"
    
    # Trap to handle rollback on failure
    trap 'if [[ "$step_failed" == "true" ]] && [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then rollback_deployment; fi; save_deployment_state "failed"' EXIT
    
    # Execute rolling deployment steps
    capture_current_state
    
    if ! deploy_new_revision; then
        step_failed="true"
        log_error "Failed to deploy new revision"
        exit 1
    fi
    
    if ! handle_recreate_mode; then
        step_failed="true"
        log_error "Failed to handle recreate mode"
        exit 1
    fi
    
    if ! wait_for_stabilization; then
        step_failed="true"
        log_error "Deployment failed to stabilize"
        exit 1
    fi
    
    if ! run_health_checks; then
        step_failed="true"
        log_error "Health checks failed"
        exit 1
    fi
    
    if ! validate_performance; then
        step_failed="true"
        log_error "Performance validation failed"
        exit 1
    fi
    
    if ! test_critical_endpoints; then
        step_failed="true"
        log_error "Critical endpoint testing failed"
        exit 1
    fi
    
    cleanup_old_revisions
    
    # Disable trap - deployment successful
    trap - EXIT
    
    save_deployment_state "successful"
    
    log_success "Rolling deployment completed successfully!"
    log_info "Service URL: $SERVICE_URL"
    if [[ -n "$PREVIOUS_REVISION" ]]; then
        log_info "Previous revision available for rollback: $PREVIOUS_REVISION"
    fi
    
    # Show deployment summary
    echo ""
    echo "===== ROLLING DEPLOYMENT SUMMARY ====="
    echo "Deployment ID: $DEPLOYMENT_ID"
    echo "Mode: $DEPLOYMENT_MODE"
    echo "Previous Revision: ${PREVIOUS_REVISION:-none}"
    echo "New Revision: $NEW_REVISION"
    echo "Service URL: $SERVICE_URL"
    echo "Status: SUCCESS"
    echo "======================================"
}

# Execute main function
main