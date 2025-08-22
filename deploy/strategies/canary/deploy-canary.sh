#!/usr/bin/env bash
# Canary Deployment Strategy
# Gradual traffic shifting with health monitoring and automatic rollback

set -euo pipefail

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Logging functions
log_error() { echo -e "${RED}❌ ERROR: $1${NC}" >&2; }
log_warning() { echo -e "${YELLOW}⚠️  WARNING: $1${NC}"; }
log_success() { echo -e "${GREEN}✅ SUCCESS: $1${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  INFO: $1${NC}"; }
log_progress() { echo -e "${CYAN}🚀 PROGRESS: $1${NC}"; }
log_monitor() { echo -e "${PURPLE}📊 MONITOR: $1${NC}"; }

# Required environment variables (passed from deploy-runner.sh)
: "${PROJECT_NAME:?Required environment variable PROJECT_NAME not set}"
: "${ENVIRONMENT:?Required environment variable ENVIRONMENT not set}"
: "${GCP_PROJECT:?Required environment variable GCP_PROJECT not set}"
: "${REGION:?Required environment variable REGION not set}"
: "${IMAGE_TAG:?Required environment variable IMAGE_TAG not set}"
: "${IMAGE_URL:?Required environment variable IMAGE_URL not set}"
: "${DEPLOYMENT_ID:?Required environment variable DEPLOYMENT_ID not set}"

# Canary configuration
DRY_RUN="${DRY_RUN:-false}"
ROLLBACK_ON_FAILURE="${ROLLBACK_ON_FAILURE:-true}"
CANARY_PERCENT="${CANARY_PERCENT:-10}"
HEALTH_CHECK_PATH="${HEALTH_CHECK_PATH:-/health}"

# Canary progression configuration
INITIAL_PERCENT="${CANARY_PERCENT}"
INCREMENT_PERCENT="${INCREMENT_PERCENT:-25}"
PROMOTION_INTERVAL="${PROMOTION_INTERVAL:-300}"  # 5 minutes
MAX_HEALTH_CHECK_ATTEMPTS=30
HEALTH_CHECK_INTERVAL=10

# Monitoring thresholds
ERROR_RATE_THRESHOLD="${ERROR_RATE_THRESHOLD:-5.0}"  # 5% error rate
RESPONSE_TIME_THRESHOLD="${RESPONSE_TIME_THRESHOLD:-2000}"  # 2 seconds
MONITORING_DURATION=60  # Monitor for 60 seconds at each stage

log_info "Starting Canary deployment for $PROJECT_NAME"
log_info "Deployment ID: $DEPLOYMENT_ID"
log_info "Image: ${IMAGE_URL}:${IMAGE_TAG}"
log_info "Initial canary traffic: ${INITIAL_PERCENT}%"

# Global variables for rollback
CANARY_TAG=""
CURRENT_PERCENT=0
STABLE_REVISION=""

# Step 1: Deploy Canary version with no traffic
deploy_canary_version() {
    log_progress "Deploying CANARY version (new version)"
    
    CANARY_TAG="canary-${DEPLOYMENT_ID}"
    local service_name="$PROJECT_NAME"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would deploy CANARY version with tag: $CANARY_TAG"
        return 0
    fi
    
    # Get current stable revision for rollback
    STABLE_REVISION=$(gcloud run services describe "$service_name" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.traffic[].revisionName)" \
        --filter="status.traffic[].percent=100" 2>/dev/null | head -1)
    
    log_info "Current stable revision: ${STABLE_REVISION:-none}"
    
    # Deploy new version without traffic
    gcloud run deploy "$service_name" \
        --image="${IMAGE_URL}:${IMAGE_TAG}" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --platform=managed \
        --tag="$CANARY_TAG" \
        --no-traffic \
        --memory=2Gi \
        --cpu=1 \
        --concurrency=100 \
        --max-instances=10 \
        --timeout=300 \
        --set-env-vars="ENV=$ENVIRONMENT,VERSION=$IMAGE_TAG,DEPLOYMENT_STRATEGY=canary"
    
    log_success "CANARY version deployed successfully"
}

# Step 2: Health check the Canary version
health_check_canary() {
    log_progress "Running health checks on CANARY version"
    
    local canary_url
    canary_url=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.traffic[].url)" \
        --filter="status.traffic[].tag=$CANARY_TAG" \
        2>/dev/null | head -1)
    
    if [[ -z "$canary_url" ]]; then
        log_error "Could not get CANARY version URL"
        return 1
    fi
    
    export CANARY_URL="$canary_url"
    log_info "CANARY version URL: $CANARY_URL"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would perform health checks on: ${CANARY_URL}${HEALTH_CHECK_PATH}"
        return 0
    fi
    
    # Wait for service to be ready
    local attempt=1
    while [[ $attempt -le $MAX_HEALTH_CHECK_ATTEMPTS ]]; do
        log_info "Health check attempt $attempt/$MAX_HEALTH_CHECK_ATTEMPTS"
        
        if curl -f "${CANARY_URL}${HEALTH_CHECK_PATH}" \
            --max-time 10 \
            --silent \
            --show-error \
            --connect-timeout 5; then
            log_success "CANARY version health check passed"
            return 0
        fi
        
        if [[ $attempt -eq $MAX_HEALTH_CHECK_ATTEMPTS ]]; then
            log_error "CANARY version health check failed after $MAX_HEALTH_CHECK_ATTEMPTS attempts"
            return 1
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        ((attempt++))
    done
}

# Step 3: Gradually shift traffic to canary
shift_traffic_to_canary() {
    local target_percent="$1"
    log_progress "Shifting ${target_percent}% traffic to CANARY version"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would shift ${target_percent}% traffic to CANARY"
        CURRENT_PERCENT="$target_percent"
        return 0
    fi
    
    # Calculate stable traffic percentage
    local stable_percent=$((100 - target_percent))
    
    # Update traffic allocation
    gcloud run services update-traffic "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --to-tags="${CANARY_TAG}=${target_percent}" \
        --to-revisions="${STABLE_REVISION}=${stable_percent}"
    
    CURRENT_PERCENT="$target_percent"
    log_success "Traffic shifted: ${target_percent}% CANARY, ${stable_percent}% STABLE"
}

# Step 4: Monitor canary performance
monitor_canary_performance() {
    local monitoring_duration="$1"
    log_monitor "Monitoring CANARY performance for ${monitoring_duration}s"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would monitor CANARY performance"
        return 0
    fi
    
    # Get main service URL for monitoring
    local main_url
    main_url=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.url)")
    
    local start_time=$(date +%s)
    local end_time=$((start_time + monitoring_duration))
    local check_interval=10
    
    local error_count=0
    local success_count=0
    local total_response_time=0
    local response_time_samples=0
    
    while [[ $(date +%s) -lt $end_time ]]; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        local remaining=$((end_time - current_time))
        
        echo -ne "\r${PURPLE}📊 Monitoring... ${elapsed}s/${monitoring_duration}s (${remaining}s remaining)${NC}"
        
        # Test main service URL (includes both canary and stable traffic)
        local response_time
        if response_time=$(curl -o /dev/null -s -w '%{time_total}' "$main_url$HEALTH_CHECK_PATH" --max-time 10 2>/dev/null); then
            success_count=$((success_count + 1))
            total_response_time=$(echo "$total_response_time + $response_time" | bc -l)
            response_time_samples=$((response_time_samples + 1))
        else
            error_count=$((error_count + 1))
        fi
        
        # Test canary URL directly
        if ! curl -f "$CANARY_URL$HEALTH_CHECK_PATH" --max-time 10 --silent > /dev/null 2>&1; then
            log_warning "\nDirect CANARY health check failed"
        fi
        
        sleep $check_interval
    done
    
    echo ""  # New line after progress indicator
    
    # Calculate metrics
    local total_requests=$((success_count + error_count))
    local error_rate=0
    local avg_response_time=0
    
    if [[ $total_requests -gt 0 ]]; then
        error_rate=$(echo "scale=2; $error_count * 100 / $total_requests" | bc -l)
    fi
    
    if [[ $response_time_samples -gt 0 ]]; then
        avg_response_time=$(echo "scale=3; $total_response_time / $response_time_samples" | bc -l)
        avg_response_time_ms=$(echo "$avg_response_time * 1000" | bc -l | cut -d. -f1)
    fi
    
    log_monitor "Performance metrics:"
    log_monitor "  Total requests: $total_requests"
    log_monitor "  Success: $success_count, Errors: $error_count"
    log_monitor "  Error rate: ${error_rate}%"
    log_monitor "  Average response time: ${avg_response_time}s (${avg_response_time_ms}ms)"
    
    # Check if metrics are within acceptable thresholds
    if (( $(echo "$error_rate > $ERROR_RATE_THRESHOLD" | bc -l) )); then
        log_error "Error rate ${error_rate}% exceeds threshold ${ERROR_RATE_THRESHOLD}%"
        return 1
    fi
    
    if [[ -n "$avg_response_time_ms" ]] && [[ "$avg_response_time_ms" -gt "$RESPONSE_TIME_THRESHOLD" ]]; then
        log_error "Average response time ${avg_response_time_ms}ms exceeds threshold ${RESPONSE_TIME_THRESHOLD}ms"
        return 1
    fi
    
    log_success "CANARY performance metrics within acceptable thresholds"
    return 0
}

# Step 5: Progressive canary rollout
progressive_canary_rollout() {
    log_progress "Starting progressive CANARY rollout"
    
    # Traffic progression stages
    local traffic_stages=($INITIAL_PERCENT)
    
    # Calculate additional stages
    local current=$INITIAL_PERCENT
    while [[ $current -lt 100 ]]; do
        current=$((current + INCREMENT_PERCENT))
        if [[ $current -gt 100 ]]; then
            current=100
        fi
        traffic_stages+=($current)
    done
    
    log_info "Traffic progression plan: ${traffic_stages[*]}%"
    
    # Execute each stage
    for stage_percent in "${traffic_stages[@]}"; do
        log_progress "Stage: ${stage_percent}% CANARY traffic"
        
        # Shift traffic
        if ! shift_traffic_to_canary "$stage_percent"; then
            log_error "Failed to shift traffic to ${stage_percent}%"
            return 1
        fi
        
        # Monitor performance at this stage
        if ! monitor_canary_performance "$MONITORING_DURATION"; then
            log_error "Performance monitoring failed at ${stage_percent}% traffic"
            return 1
        fi
        
        # If this is not the final stage, wait before proceeding
        if [[ $stage_percent -lt 100 ]]; then
            log_info "Stage ${stage_percent}% completed successfully"
            log_info "Waiting ${PROMOTION_INTERVAL}s before next stage..."
            
            if [[ "$DRY_RUN" != "true" ]]; then
                # Countdown with ability to abort
                for ((i=PROMOTION_INTERVAL; i>0; i--)); do
                    echo -ne "\r${CYAN}⏳ Next stage in ${i}s (Ctrl+C to abort promotion)${NC}"
                    sleep 1
                done
                echo -e "\r${CYAN}⏳ Proceeding to next stage...${NC}                    "
            fi
        else
            log_success "CANARY rollout completed - 100% traffic on new version"
        fi
    done
}

# Step 6: Final validation and promotion
finalize_canary_deployment() {
    log_progress "Finalizing CANARY deployment"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would finalize deployment"
        return 0
    fi
    
    # Final comprehensive health check
    log_info "Running final comprehensive validation..."
    
    local main_url
    main_url=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.url)")
    
    # Run multiple health checks to ensure stability
    for ((i=1; i<=5; i++)); do
        if ! curl -f "$main_url$HEALTH_CHECK_PATH" --max-time 10 --silent > /dev/null; then
            log_error "Final health check $i/5 failed"
            return 1
        fi
        sleep 2
    done
    
    # Update traffic to remove canary tag (make it the default)
    log_info "Promoting CANARY to stable version..."
    
    # Get the canary revision name
    local canary_revision
    canary_revision=$(gcloud run services describe "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --format="value(status.traffic[].revisionName)" \
        --filter="status.traffic[].tag=$CANARY_TAG" 2>/dev/null | head -1)
    
    if [[ -n "$canary_revision" ]]; then
        # Set 100% traffic to the canary revision (without tag)
        gcloud run services update-traffic "$PROJECT_NAME" \
            --region="$REGION" \
            --project="$GCP_PROJECT" \
            --to-revisions="$canary_revision=100"
        
        log_success "CANARY promoted to stable version"
    else
        log_warning "Could not find canary revision for promotion"
    fi
    
    # Clean up old stable revision (keep it available for rollback)
    if [[ -n "$STABLE_REVISION" ]]; then
        log_info "Previous stable revision $STABLE_REVISION kept for rollback capability"
    fi
    
    export MAIN_URL="$main_url"
    log_success "CANARY deployment finalized successfully"
}

# Rollback function
rollback_canary() {
    log_error "CANARY deployment failed - rolling back to stable version"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would rollback to stable version"
        return 0
    fi
    
    if [[ -n "$STABLE_REVISION" ]]; then
        log_info "Rolling back to stable revision: $STABLE_REVISION"
        log_info "Current canary traffic: ${CURRENT_PERCENT}%"
        
        # Immediately shift all traffic back to stable
        gcloud run services update-traffic "$PROJECT_NAME" \
            --region="$REGION" \
            --project="$GCP_PROJECT" \
            --to-revisions="$STABLE_REVISION=100" || {
            log_error "Failed to rollback traffic allocation"
            return 1
        }
        
        # Verify rollback
        local main_url
        main_url=$(gcloud run services describe "$PROJECT_NAME" \
            --region="$REGION" \
            --project="$GCP_PROJECT" \
            --format="value(status.url)")
        
        if curl -f "$main_url$HEALTH_CHECK_PATH" --max-time 10 --silent > /dev/null; then
            log_success "Rollback to stable version successful"
        else
            log_error "Rollback verification failed"
            return 1
        fi
        
        # Clean up failed canary version
        if [[ -n "$CANARY_TAG" ]]; then
            log_info "Failed CANARY version will be cleaned up by retention policy"
        fi
        
    else
        log_error "No stable revision information available for rollback"
        return 1
    fi
}

# Save deployment state for monitoring/debugging
save_deployment_state() {
    local status="$1"
    
    cat > ".canary-state.json" << EOF
{
  "deployment_id": "$DEPLOYMENT_ID",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "$status",
  "canary_tag": "$CANARY_TAG",
  "stable_revision": "$STABLE_REVISION",
  "current_traffic_percent": $CURRENT_PERCENT,
  "canary_url": "${CANARY_URL:-}",
  "main_url": "${MAIN_URL:-}",
  "configuration": {
    "initial_percent": $INITIAL_PERCENT,
    "increment_percent": $INCREMENT_PERCENT,
    "promotion_interval": $PROMOTION_INTERVAL,
    "error_rate_threshold": $ERROR_RATE_THRESHOLD,
    "response_time_threshold": $RESPONSE_TIME_THRESHOLD
  }
}
EOF
}

# Main execution
main() {
    local step_failed="false"
    
    # Trap to handle rollback on failure
    trap 'if [[ "$step_failed" == "true" ]] && [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then rollback_canary; fi; save_deployment_state "failed"' EXIT
    
    # Validate canary percentage
    if [[ $INITIAL_PERCENT -lt 1 ]] || [[ $INITIAL_PERCENT -gt 100 ]]; then
        log_error "Invalid canary percentage: $INITIAL_PERCENT (must be 1-100)"
        exit 1
    fi
    
    # Execute Canary deployment steps
    if ! deploy_canary_version; then
        step_failed="true"
        log_error "Failed to deploy CANARY version"
        exit 1
    fi
    
    if ! health_check_canary; then
        step_failed="true"
        log_error "CANARY version health check failed"
        exit 1
    fi
    
    if ! progressive_canary_rollout; then
        step_failed="true"
        log_error "Progressive CANARY rollout failed"
        exit 1
    fi
    
    if ! finalize_canary_deployment; then
        step_failed="true"
        log_error "CANARY deployment finalization failed"
        exit 1
    fi
    
    # Disable trap - deployment successful
    trap - EXIT
    
    save_deployment_state "successful"
    
    log_success "CANARY deployment completed successfully!"
    log_info "Service is now running 100% on the new version"
    log_info "Service URL: ${MAIN_URL:-$CANARY_URL}"
    log_info "Rollback is available using revision: $STABLE_REVISION"
    
    # Show deployment summary
    echo ""
    echo "===== CANARY DEPLOYMENT SUMMARY ====="
    echo "Deployment ID: $DEPLOYMENT_ID"
    echo "Initial Canary: ${INITIAL_PERCENT}%"
    echo "Increment: ${INCREMENT_PERCENT}%"
    echo "Monitoring Duration: ${MONITORING_DURATION}s per stage"
    echo "Promotion Interval: ${PROMOTION_INTERVAL}s"
    echo "Final Status: SUCCESS"
    echo "======================================"
}

# Execute main function
main