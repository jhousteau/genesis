#!/usr/bin/env bash
# Automatic Rollback System
# Intelligent rollback with health monitoring and automatic triggers

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
log_progress() { echo -e "${CYAN}🔄 ROLLBACK: $1${NC}"; }
log_monitor() { echo -e "${PURPLE}📊 MONITOR: $1${NC}"; }

# Configuration
PROJECT_NAME="${PROJECT_NAME:-}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
GCP_PROJECT="${GCP_PROJECT:-}"
REGION="${REGION:-us-central1}"
SERVICE_TYPE="${SERVICE_TYPE:-cloudrun}"  # cloudrun, gke, gce, function
DEPLOYMENT_ID="${DEPLOYMENT_ID:-}"

# Rollback configuration
MONITORING_DURATION="${MONITORING_DURATION:-300}"  # 5 minutes
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-30}"  # 30 seconds
HEALTH_CHECK_PATH="${HEALTH_CHECK_PATH:-/health}"
ERROR_RATE_THRESHOLD="${ERROR_RATE_THRESHOLD:-5}"    # 5% error rate
RESPONSE_TIME_THRESHOLD="${RESPONSE_TIME_THRESHOLD:-5000}"  # 5 seconds
CONSECUTIVE_FAILURES_THRESHOLD="${CONSECUTIVE_FAILURES_THRESHOLD:-3}"

# Automatic rollback triggers
ENABLE_AUTO_ROLLBACK="${ENABLE_AUTO_ROLLBACK:-true}"
ROLLBACK_ON_HIGH_ERROR_RATE="${ROLLBACK_ON_HIGH_ERROR_RATE:-true}"
ROLLBACK_ON_HIGH_LATENCY="${ROLLBACK_ON_HIGH_LATENCY:-true}"
ROLLBACK_ON_HEALTH_CHECK_FAILURE="${ROLLBACK_ON_HEALTH_CHECK_FAILURE:-true}"
ROLLBACK_ON_LOW_AVAILABILITY="${ROLLBACK_ON_LOW_AVAILABILITY:-true}"

# State tracking
OUTPUT_DIR="${OUTPUT_DIR:-./rollback-logs}"
DRY_RUN="${DRY_RUN:-false}"

log_info "🔄 Starting Automatic Rollback System"
log_info "Service: $PROJECT_NAME ($SERVICE_TYPE)"
log_info "Environment: $ENVIRONMENT"
log_info "Monitoring Duration: ${MONITORING_DURATION}s"
log_info "Auto Rollback Enabled: $ENABLE_AUTO_ROLLBACK"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Initialize monitoring state
declare -A health_metrics
declare -A rollback_triggers
declare -A service_state

# Function to get current deployment information
get_current_deployment_info() {
    log_progress "Getting current deployment information"
    
    case "$SERVICE_TYPE" in
        cloudrun)
            if service_info=$(gcloud run services describe "$PROJECT_NAME" \
                --region="$REGION" \
                --project="$GCP_PROJECT" \
                --format=json 2>/dev/null); then
                
                service_state["current_revision"]=$(echo "$service_info" | jq -r '.status.latestReadyRevisionName // "unknown"')
                service_state["service_url"]=$(echo "$service_info" | jq -r '.status.url // ""')
                service_state["traffic_percent"]=$(echo "$service_info" | jq -r '.status.traffic[0].percent // 100')
                
                # Get revision list for rollback options
                local revisions
                revisions=$(gcloud run revisions list \
                    --service="$PROJECT_NAME" \
                    --region="$REGION" \
                    --project="$GCP_PROJECT" \
                    --format=json \
                    --limit=10 \
                    --sort-by="~metadata.creationTimestamp")
                
                # Find previous stable revision (exclude current)
                service_state["previous_revision"]=$(echo "$revisions" | jq -r --arg current "${service_state[current_revision]}" '[.[] | select(.metadata.name != $current)][0].metadata.name // "none"')
                
                log_info "Current revision: ${service_state[current_revision]}"
                log_info "Previous revision: ${service_state[previous_revision]}"
                log_info "Service URL: ${service_state[service_url]}"
            else
                log_error "Failed to get Cloud Run service information"
                return 1
            fi
            ;;
        gke)
            # GKE deployment information
            if deployment_info=$(kubectl get deployment "$PROJECT_NAME" -o json 2>/dev/null); then
                service_state["current_image"]=$(echo "$deployment_info" | jq -r '.spec.template.spec.containers[0].image // "unknown"')
                service_state["desired_replicas"]=$(echo "$deployment_info" | jq -r '.spec.replicas // 1')
                service_state["ready_replicas"]=$(echo "$deployment_info" | jq -r '.status.readyReplicas // 0')
                
                # Get service URL if available
                if service_url=$(kubectl get service "$PROJECT_NAME" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null); then
                    service_state["service_url"]="http://$service_url"
                else
                    service_state["service_url"]=""
                fi
                
                log_info "Current image: ${service_state[current_image]}"
                log_info "Ready replicas: ${service_state[ready_replicas]}/${service_state[desired_replicas]}"
            else
                log_error "Failed to get GKE deployment information"
                return 1
            fi
            ;;
        function)
            # Cloud Functions information
            if function_info=$(gcloud functions describe "$PROJECT_NAME" \
                --region="$REGION" \
                --project="$GCP_PROJECT" \
                --format=json 2>/dev/null); then
                
                service_state["function_version"]=$(echo "$function_info" | jq -r '.versionId // "unknown"')
                service_state["service_url"]=$(echo "$function_info" | jq -r '.httpsTrigger.url // ""')
                
                log_info "Function version: ${service_state[function_version]}"
                log_info "Function URL: ${service_state[service_url]}"
            else
                log_error "Failed to get Cloud Function information"
                return 1
            fi
            ;;
        *)
            log_error "Unsupported service type: $SERVICE_TYPE"
            return 1
            ;;
    esac
    
    log_success "Current deployment information retrieved"
}

# Function to perform health checks
perform_health_check() {
    local service_url="$1"
    local attempt="$2"
    
    if [[ -z "$service_url" ]]; then
        log_warning "No service URL available for health check"
        return 1
    fi
    
    log_monitor "Health check attempt $attempt"
    
    # Perform health check with timeout
    local start_time=$(date +%s.%N)
    local response_code
    local response_time
    
    if response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 \
        --connect-timeout 5 \
        "${service_url}${HEALTH_CHECK_PATH}"); then
        
        local end_time=$(date +%s.%N)
        response_time=$(echo "($end_time - $start_time) * 1000" | bc | cut -d. -f1)
        
        health_metrics["last_response_code"]="$response_code"
        health_metrics["last_response_time"]="$response_time"
        
        if [[ "$response_code" == "200" ]]; then
            log_success "Health check passed: HTTP $response_code (${response_time}ms)"
            health_metrics["consecutive_failures"]=0
            return 0
        else
            log_warning "Health check failed: HTTP $response_code (${response_time}ms)"
            health_metrics["consecutive_failures"]=$((${health_metrics[consecutive_failures]:-0} + 1))
            return 1
        fi
    else
        log_warning "Health check failed: Connection error"
        health_metrics["consecutive_failures"]=$((${health_metrics[consecutive_failures]:-0} + 1))
        health_metrics["last_response_code"]="000"
        health_metrics["last_response_time"]="999999"
        return 1
    fi
}

# Function to analyze service metrics
analyze_service_metrics() {
    log_monitor "Analyzing service metrics"
    
    local service_url="${service_state[service_url]}"
    if [[ -z "$service_url" ]]; then
        log_warning "No service URL available for metrics analysis"
        return 0
    fi
    
    # Collect metrics over a period
    local total_requests=0
    local successful_requests=0
    local failed_requests=0
    local total_response_time=0
    local samples=5
    
    log_info "Collecting metrics samples ($samples samples)..."
    
    for ((i=1; i<=samples; i++)); do
        local start_time=$(date +%s.%N)
        local response_code
        
        if response_code=$(curl -s -o /dev/null -w "%{http_code}" \
            --max-time 10 \
            "${service_url}${HEALTH_CHECK_PATH}"); then
            
            local end_time=$(date +%s.%N)
            local response_time=$(echo "($end_time - $start_time) * 1000" | bc | cut -d. -f1)
            
            total_requests=$((total_requests + 1))
            total_response_time=$((total_response_time + response_time))
            
            if [[ "$response_code" == "200" ]]; then
                successful_requests=$((successful_requests + 1))
            else
                failed_requests=$((failed_requests + 1))
            fi
        else
            total_requests=$((total_requests + 1))
            failed_requests=$((failed_requests + 1))
            total_response_time=$((total_response_time + 10000))  # Add penalty for failed requests
        fi
        
        sleep 2
    done
    
    # Calculate metrics
    local error_rate=0
    local avg_response_time=0
    
    if [[ $total_requests -gt 0 ]]; then
        error_rate=$(echo "scale=2; $failed_requests * 100 / $total_requests" | bc)
        avg_response_time=$(echo "scale=0; $total_response_time / $total_requests" | bc)
    fi
    
    health_metrics["error_rate"]="$error_rate"
    health_metrics["avg_response_time"]="$avg_response_time"
    health_metrics["total_requests"]="$total_requests"
    health_metrics["successful_requests"]="$successful_requests"
    health_metrics["failed_requests"]="$failed_requests"
    
    log_monitor "Metrics - Error Rate: ${error_rate}%, Avg Response Time: ${avg_response_time}ms"
    log_monitor "Requests - Total: $total_requests, Success: $successful_requests, Failed: $failed_requests"
    
    # Save metrics to file
    cat > "$OUTPUT_DIR/health-metrics-$(date +%Y%m%d-%H%M%S).json" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployment_id": "$DEPLOYMENT_ID",
  "service": "$PROJECT_NAME",
  "environment": "$ENVIRONMENT",
  "metrics": {
    "error_rate": $error_rate,
    "avg_response_time": $avg_response_time,
    "total_requests": $total_requests,
    "successful_requests": $successful_requests,
    "failed_requests": $failed_requests,
    "consecutive_failures": ${health_metrics[consecutive_failures]:-0}
  }
}
EOF
}

# Function to check rollback triggers
check_rollback_triggers() {
    log_monitor "Checking rollback triggers"
    
    local should_rollback=false
    local rollback_reasons=()
    
    # Check error rate threshold
    if [[ "$ROLLBACK_ON_HIGH_ERROR_RATE" == "true" ]]; then
        local error_rate="${health_metrics[error_rate]:-0}"
        if (( $(echo "$error_rate > $ERROR_RATE_THRESHOLD" | bc -l) )); then
            rollback_triggers["high_error_rate"]="true"
            rollback_reasons+=("High error rate: ${error_rate}% > ${ERROR_RATE_THRESHOLD}%")
            should_rollback=true
        fi
    fi
    
    # Check response time threshold
    if [[ "$ROLLBACK_ON_HIGH_LATENCY" == "true" ]]; then
        local avg_response_time="${health_metrics[avg_response_time]:-0}"
        if [[ $avg_response_time -gt $RESPONSE_TIME_THRESHOLD ]]; then
            rollback_triggers["high_latency"]="true"
            rollback_reasons+=("High latency: ${avg_response_time}ms > ${RESPONSE_TIME_THRESHOLD}ms")
            should_rollback=true
        fi
    fi
    
    # Check consecutive health check failures
    if [[ "$ROLLBACK_ON_HEALTH_CHECK_FAILURE" == "true" ]]; then
        local consecutive_failures="${health_metrics[consecutive_failures]:-0}"
        if [[ $consecutive_failures -ge $CONSECUTIVE_FAILURES_THRESHOLD ]]; then
            rollback_triggers["consecutive_failures"]="true"
            rollback_reasons+=("Consecutive failures: $consecutive_failures >= $CONSECUTIVE_FAILURES_THRESHOLD")
            should_rollback=true
        fi
    fi
    
    # Check availability
    if [[ "$ROLLBACK_ON_LOW_AVAILABILITY" == "true" ]]; then
        local total_requests="${health_metrics[total_requests]:-0}"
        local successful_requests="${health_metrics[successful_requests]:-0}"
        
        if [[ $total_requests -gt 0 ]]; then
            local availability=$(echo "scale=2; $successful_requests * 100 / $total_requests" | bc)
            if (( $(echo "$availability < 95" | bc -l) )); then
                rollback_triggers["low_availability"]="true"
                rollback_reasons+=("Low availability: ${availability}% < 95%")
                should_rollback=true
            fi
        fi
    fi
    
    # Log trigger status
    if [[ "$should_rollback" == "true" ]]; then
        log_warning "Rollback triggers activated:"
        for reason in "${rollback_reasons[@]}"; do
            log_warning "  - $reason"
        done
        return 0
    else
        log_success "No rollback triggers activated"
        return 1
    fi
}

# Function to execute automatic rollback
execute_automatic_rollback() {
    log_progress "Executing automatic rollback"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would execute automatic rollback"
        return 0
    fi
    
    # Create rollback record
    cat > "$OUTPUT_DIR/rollback-record-$(date +%Y%m%d-%H%M%S).json" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployment_id": "$DEPLOYMENT_ID",
  "service": "$PROJECT_NAME",
  "environment": "$ENVIRONMENT",
  "service_type": "$SERVICE_TYPE",
  "rollback_triggers": $(printf '%s\n' "${!rollback_triggers[@]}" | jq -R . | jq -s 'map(split(":") | {(.[0]): true}) | add'),
  "health_metrics": {
    "error_rate": ${health_metrics[error_rate]:-0},
    "avg_response_time": ${health_metrics[avg_response_time]:-0},
    "consecutive_failures": ${health_metrics[consecutive_failures]:-0}
  },
  "current_state": {
    "current_revision": "${service_state[current_revision]:-unknown}",
    "previous_revision": "${service_state[previous_revision]:-unknown}",
    "service_url": "${service_state[service_url]:-}"
  }
}
EOF
    
    case "$SERVICE_TYPE" in
        cloudrun)
            execute_cloudrun_rollback
            ;;
        gke)
            execute_gke_rollback
            ;;
        function)
            execute_function_rollback
            ;;
        *)
            log_error "Rollback not implemented for service type: $SERVICE_TYPE"
            return 1
            ;;
    esac
}

# Cloud Run rollback
execute_cloudrun_rollback() {
    log_progress "Executing Cloud Run rollback"
    
    local previous_revision="${service_state[previous_revision]}"
    
    if [[ "$previous_revision" == "none" || -z "$previous_revision" ]]; then
        log_error "No previous revision available for rollback"
        return 1
    fi
    
    log_info "Rolling back to revision: $previous_revision"
    
    # Update traffic to previous revision
    gcloud run services update-traffic "$PROJECT_NAME" \
        --region="$REGION" \
        --project="$GCP_PROJECT" \
        --to-revisions="$previous_revision=100"
    
    # Verify rollback
    sleep 10
    if verify_rollback_success; then
        log_success "Cloud Run rollback completed successfully"
        
        # Update service state
        service_state["current_revision"]="$previous_revision"
        
        # Send notification
        send_rollback_notification "success"
        
        return 0
    else
        log_error "Cloud Run rollback verification failed"
        send_rollback_notification "failed"
        return 1
    fi
}

# GKE rollback
execute_gke_rollback() {
    log_progress "Executing GKE rollback"
    
    # Rollback deployment
    kubectl rollout undo deployment/"$PROJECT_NAME"
    
    # Wait for rollout to complete
    kubectl rollout status deployment/"$PROJECT_NAME" --timeout=300s
    
    # Verify rollback
    if verify_rollback_success; then
        log_success "GKE rollback completed successfully"
        send_rollback_notification "success"
        return 0
    else
        log_error "GKE rollback verification failed"
        send_rollback_notification "failed"
        return 1
    fi
}

# Cloud Functions rollback
execute_function_rollback() {
    log_progress "Executing Cloud Function rollback"
    
    # Note: Cloud Functions doesn't have built-in rollback
    # This would require redeploying the previous version
    log_warning "Cloud Functions automatic rollback requires manual intervention"
    log_info "Please redeploy the previous version manually"
    
    send_rollback_notification "manual_required"
    return 1
}

# Verify rollback success
verify_rollback_success() {
    log_progress "Verifying rollback success"
    
    local service_url="${service_state[service_url]}"
    if [[ -z "$service_url" ]]; then
        log_warning "No service URL available for rollback verification"
        return 1
    fi
    
    # Wait for rollback to stabilize
    sleep 30
    
    # Perform health checks
    local success_count=0
    local total_checks=5
    
    for ((i=1; i<=total_checks; i++)); do
        if perform_health_check "$service_url" "$i"; then
            success_count=$((success_count + 1))
        fi
        sleep 10
    done
    
    local success_rate=$(echo "scale=0; $success_count * 100 / $total_checks" | bc)
    
    if [[ $success_rate -ge 80 ]]; then
        log_success "Rollback verification passed: ${success_rate}% success rate"
        return 0
    else
        log_error "Rollback verification failed: ${success_rate}% success rate"
        return 1
    fi
}

# Send rollback notification
send_rollback_notification() {
    local status="$1"
    
    log_info "Sending rollback notification: $status"
    
    # Create notification payload
    local notification_file="$OUTPUT_DIR/rollback-notification-$(date +%Y%m%d-%H%M%S).json"
    
    cat > "$notification_file" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "event": "automatic_rollback",
  "status": "$status",
  "service": "$PROJECT_NAME",
  "environment": "$ENVIRONMENT",
  "deployment_id": "$DEPLOYMENT_ID",
  "rollback_triggers": $(printf '%s\n' "${!rollback_triggers[@]}" | jq -R . | jq -s 'map(split(":") | {(.[0]): true}) | add'),
  "health_metrics": {
    "error_rate": ${health_metrics[error_rate]:-0},
    "avg_response_time": ${health_metrics[avg_response_time]:-0},
    "consecutive_failures": ${health_metrics[consecutive_failures]:-0}
  }
}
EOF
    
    # In a real implementation, you would send this to:
    # - Slack/Teams webhook
    # - Email notification system
    # - PagerDuty/OpsGenie
    # - Monitoring dashboard
    
    log_info "Notification saved to: $notification_file"
}

# Continuous monitoring loop
start_continuous_monitoring() {
    log_progress "Starting continuous monitoring"
    
    local start_time=$(date +%s)
    local end_time=$((start_time + MONITORING_DURATION))
    local check_count=0
    
    while [[ $(date +%s) -lt $end_time ]]; do
        check_count=$((check_count + 1))
        local elapsed=$(($(date +%s) - start_time))
        local remaining=$((end_time - $(date +%s)))
        
        log_monitor "Monitoring check $check_count (${elapsed}s elapsed, ${remaining}s remaining)"
        
        # Analyze current service metrics
        analyze_service_metrics
        
        # Check if rollback should be triggered
        if [[ "$ENABLE_AUTO_ROLLBACK" == "true" ]]; then
            if check_rollback_triggers; then
                log_warning "Automatic rollback triggered!"
                
                if execute_automatic_rollback; then
                    log_success "Automatic rollback completed successfully"
                    return 0
                else
                    log_error "Automatic rollback failed"
                    return 1
                fi
            fi
        else
            log_info "Auto rollback disabled - manual intervention required if issues detected"
        fi
        
        # Wait before next check
        if [[ $remaining -gt 0 ]]; then
            sleep $HEALTH_CHECK_INTERVAL
        fi
    done
    
    log_success "Monitoring completed - no rollback triggered"
    return 0
}

# Generate monitoring report
generate_monitoring_report() {
    log_progress "Generating monitoring report"
    
    local report_file="$OUTPUT_DIR/monitoring-report-$(date +%Y%m%d-%H%M%S).json"
    
    cat > "$report_file" << EOF
{
  "monitoring_session": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "deployment_id": "$DEPLOYMENT_ID",
    "service": "$PROJECT_NAME",
    "environment": "$ENVIRONMENT",
    "service_type": "$SERVICE_TYPE",
    "monitoring_duration": $MONITORING_DURATION,
    "auto_rollback_enabled": $ENABLE_AUTO_ROLLBACK
  },
  "final_health_metrics": {
    "error_rate": ${health_metrics[error_rate]:-0},
    "avg_response_time": ${health_metrics[avg_response_time]:-0},
    "consecutive_failures": ${health_metrics[consecutive_failures]:-0},
    "total_requests": ${health_metrics[total_requests]:-0},
    "successful_requests": ${health_metrics[successful_requests]:-0},
    "failed_requests": ${health_metrics[failed_requests]:-0}
  },
  "rollback_triggers": $(printf '%s\n' "${!rollback_triggers[@]}" | jq -R . | jq -s 'map(split(":") | {(.[0]): true}) | add' 2>/dev/null || echo "{}"),
  "service_state": {
    "current_revision": "${service_state[current_revision]:-unknown}",
    "previous_revision": "${service_state[previous_revision]:-unknown}",
    "service_url": "${service_state[service_url]:-}"
  }
}
EOF
    
    log_success "Monitoring report generated: $report_file"
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project-name)
                PROJECT_NAME="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --gcp-project)
                GCP_PROJECT="$2"
                shift 2
                ;;
            --region)
                REGION="$2"
                shift 2
                ;;
            --service-type)
                SERVICE_TYPE="$2"
                shift 2
                ;;
            --deployment-id)
                DEPLOYMENT_ID="$2"
                shift 2
                ;;
            --monitoring-duration)
                MONITORING_DURATION="$2"
                shift 2
                ;;
            --enable-auto-rollback)
                ENABLE_AUTO_ROLLBACK="true"
                shift
                ;;
            --disable-auto-rollback)
                ENABLE_AUTO_ROLLBACK="false"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --project-name NAME       Service/project name"
                echo "  --environment ENV         Environment (dev, stage, prod)"
                echo "  --gcp-project PROJECT     GCP project ID"
                echo "  --region REGION          GCP region"
                echo "  --service-type TYPE      Service type (cloudrun, gke, function)"
                echo "  --deployment-id ID       Deployment ID"
                echo "  --monitoring-duration SEC Monitoring duration in seconds"
                echo "  --enable-auto-rollback   Enable automatic rollback"
                echo "  --disable-auto-rollback  Disable automatic rollback"
                echo "  --dry-run               Dry run mode"
                echo "  --help                  Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$PROJECT_NAME" || -z "$GCP_PROJECT" ]]; then
        log_error "PROJECT_NAME and GCP_PROJECT are required"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "🧪 Running in DRY RUN mode"
    fi
    
    # Initialize metrics
    health_metrics["consecutive_failures"]=0
    
    # Get current deployment state
    get_current_deployment_info
    
    # Start monitoring
    start_continuous_monitoring
    
    # Generate final report
    generate_monitoring_report
    
    log_success "Automatic rollback monitoring completed"
}

# Execute main function with all arguments
main "$@"