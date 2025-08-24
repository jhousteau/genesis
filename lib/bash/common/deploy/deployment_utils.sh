#!/bin/bash

# Deployment Utilities Module
# Provides comprehensive deployment functionality with multiple strategies and rollback support

# Source required modules
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../logging/logger.sh"
source "$SCRIPT_DIR/../auth/gcp_auth.sh"

# Configuration
DEPLOYMENT_TIMEOUT="${DEPLOYMENT_TIMEOUT:-1800}"  # 30 minutes
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-300}"  # 5 minutes
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-10}"  # 10 seconds
ROLLBACK_ENABLED="${ROLLBACK_ENABLED:-true}"
DEPLOYMENT_LOCK_DIR="${DEPLOYMENT_LOCK_DIR:-/tmp/whitehorse-deployments}"

# Deployment state
declare -A ACTIVE_DEPLOYMENTS=()
declare -A DEPLOYMENT_HISTORY=()

# Initialize deployment module
init_deployment_utils() {
    log_info "Initializing deployment utilities module"

    # Create lock directory
    mkdir -p "$DEPLOYMENT_LOCK_DIR"
    chmod 755 "$DEPLOYMENT_LOCK_DIR"

    # Check required tools
    local required_tools=("gcloud" "kubectl" "curl" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_warn "Recommended tool not found: $tool"
        fi
    done

    log_info "Deployment utilities module initialized"
    return 0
}

# Generate deployment ID
generate_deployment_id() {
    local project_name="$1"
    local environment="$2"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    echo "${project_name}_${environment}_${timestamp}_$(shuf -i 1000-9999 -n 1)"
}

# Create deployment lock
create_deployment_lock() {
    local deployment_id="$1"
    local lock_file="$DEPLOYMENT_LOCK_DIR/$deployment_id.lock"

    if [[ -f "$lock_file" ]]; then
        log_error "Deployment already in progress: $deployment_id"
        return 1
    fi

    cat > "$lock_file" << EOF
{
    "deployment_id": "$deployment_id",
    "pid": $$,
    "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "running"
}
EOF

    log_debug "Created deployment lock: $lock_file"
    return 0
}

# Remove deployment lock
remove_deployment_lock() {
    local deployment_id="$1"
    local lock_file="$DEPLOYMENT_LOCK_DIR/$deployment_id.lock"

    if [[ -f "$lock_file" ]]; then
        rm -f "$lock_file"
        log_debug "Removed deployment lock: $lock_file"
    fi
}

# Check deployment prerequisites
check_deployment_prerequisites() {
    local project_name="$1"
    local environment="$2"
    local gcp_project="$3"

    log_info "Checking deployment prerequisites"

    # Validate inputs
    if [[ -z "$project_name" || -z "$environment" || -z "$gcp_project" ]]; then
        log_error "Missing required parameters: project_name, environment, gcp_project"
        return 1
    fi

    # Check GCP authentication
    if ! check_auth_status; then
        log_error "GCP authentication required"
        return 1
    fi

    # Verify project access
    if ! verify_gcp_permissions "compute.instances.list" "storage.buckets.list"; then
        log_error "Insufficient GCP permissions"
        return 1
    fi

    # Check if project exists in registry
    local project_root
    if project_root=$(get_project_root); then
        local registry_file="$project_root/projects/registry.yaml"
        if [[ -f "$registry_file" ]]; then
            if ! yq eval ".projects | has(\"$project_name\")" "$registry_file" 2>/dev/null | grep -q "true"; then
                log_error "Project not found in registry: $project_name"
                return 1
            fi
        else
            log_warn "Project registry not found, skipping registry check"
        fi
    fi

    log_info "Deployment prerequisites verified"
    return 0
}

# Rolling deployment strategy
deploy_rolling() {
    local deployment_id="$1"
    local project_name="$2"
    local environment="$3"
    local gcp_project="$4"
    local app_yaml="${5:-app.yaml}"

    log_info "Starting rolling deployment: $deployment_id"

    local start_time=$(date +%s.%N)

    # Deploy using App Engine or Cloud Run
    if [[ -f "$app_yaml" ]]; then
        log_info "Deploying to App Engine"

        if time_operation "app_engine_deploy" gcloud app deploy "$app_yaml" \
            --project="$gcp_project" \
            --version="$deployment_id" \
            --no-promote \
            --quiet; then

            log_info "App Engine deployment successful"

            # Promote new version gradually
            promote_app_engine_version "$gcp_project" "$deployment_id"

        else
            log_error "App Engine deployment failed"
            return 1
        fi
    else
        log_info "Deploying to Cloud Run"

        local service_name="$project_name-$environment"
        local image_name="gcr.io/$gcp_project/$project_name:$deployment_id"

        if time_operation "cloud_run_deploy" gcloud run deploy "$service_name" \
            --image="$image_name" \
            --platform=managed \
            --region="$GCP_REGION" \
            --project="$gcp_project" \
            --allow-unauthenticated \
            --quiet; then

            log_info "Cloud Run deployment successful"
        else
            log_error "Cloud Run deployment failed"
            return 1
        fi
    fi

    local end_time=$(date +%s.%N)
    log_performance "rolling_deployment" "$start_time" "$end_time" "true"

    return 0
}

# Blue-green deployment strategy
deploy_blue_green() {
    local deployment_id="$1"
    local project_name="$2"
    local environment="$3"
    local gcp_project="$4"
    local app_yaml="${5:-app.yaml}"

    log_info "Starting blue-green deployment: $deployment_id"

    local start_time=$(date +%s.%N)
    local service_name="$project_name-$environment"
    local blue_version="${service_name}-blue"
    local green_version="${service_name}-green"

    # Determine current and new versions
    local current_version
    if gcloud run services describe "$blue_version" --region="$GCP_REGION" --project="$gcp_project" &>/dev/null; then
        current_version="blue"
        new_version="green"
    else
        current_version="green"
        new_version="blue"
    fi

    log_info "Deploying to $new_version version"

    local new_service_name="$service_name-$new_version"
    local image_name="gcr.io/$gcp_project/$project_name:$deployment_id"

    # Deploy new version
    if time_operation "blue_green_deploy" gcloud run deploy "$new_service_name" \
        --image="$image_name" \
        --platform=managed \
        --region="$GCP_REGION" \
        --project="$gcp_project" \
        --allow-unauthenticated \
        --quiet; then

        log_info "New version deployed successfully: $new_service_name"

        # Health check new version
        if health_check_service "$new_service_name" "$gcp_project"; then
            # Switch traffic to new version
            switch_blue_green_traffic "$service_name" "$new_service_name" "$gcp_project"

            # Store rollback information
            store_rollback_info "$deployment_id" "blue_green" "$current_version" "$new_version"

            log_info "Blue-green deployment completed successfully"
        else
            log_error "Health check failed for new version, rolling back"
            cleanup_failed_blue_green "$new_service_name" "$gcp_project"
            return 1
        fi
    else
        log_error "Blue-green deployment failed"
        return 1
    fi

    local end_time=$(date +%s.%N)
    log_performance "blue_green_deployment" "$start_time" "$end_time" "true"

    return 0
}

# Canary deployment strategy
deploy_canary() {
    local deployment_id="$1"
    local project_name="$2"
    local environment="$3"
    local gcp_project="$4"
    local canary_percentage="${5:-10}"
    local canary_duration="${6:-300}"

    log_info "Starting canary deployment: $deployment_id (${canary_percentage}% traffic)"

    local start_time=$(date +%s.%N)
    local service_name="$project_name-$environment"
    local canary_service_name="$service_name-canary"
    local image_name="gcr.io/$gcp_project/$project_name:$deployment_id"

    # Deploy canary version
    if time_operation "canary_deploy" gcloud run deploy "$canary_service_name" \
        --image="$image_name" \
        --platform=managed \
        --region="$GCP_REGION" \
        --project="$gcp_project" \
        --allow-unauthenticated \
        --quiet; then

        log_info "Canary version deployed successfully"

        # Configure traffic split
        if configure_canary_traffic "$service_name" "$canary_service_name" "$canary_percentage" "$gcp_project"; then
            log_info "Canary traffic configured: ${canary_percentage}%"

            # Monitor canary for specified duration
            if monitor_canary_deployment "$canary_service_name" "$canary_duration"; then
                # Promote canary to full traffic
                promote_canary_deployment "$service_name" "$canary_service_name" "$gcp_project"

                # Store rollback information
                store_rollback_info "$deployment_id" "canary" "main" "promoted"

                log_info "Canary deployment promoted successfully"
            else
                log_error "Canary monitoring failed, rolling back"
                rollback_canary_deployment "$service_name" "$canary_service_name" "$gcp_project"
                return 1
            fi
        else
            log_error "Failed to configure canary traffic"
            cleanup_failed_canary "$canary_service_name" "$gcp_project"
            return 1
        fi
    else
        log_error "Canary deployment failed"
        return 1
    fi

    local end_time=$(date +%s.%N)
    log_performance "canary_deployment" "$start_time" "$end_time" "true"

    return 0
}

# Health check service
health_check_service() {
    local service_name="$1"
    local gcp_project="$2"
    local max_attempts="${3:-30}"
    local interval="${4:-10}"

    log_info "Health checking service: $service_name"

    # Get service URL
    local service_url
    service_url=$(gcloud run services describe "$service_name" \
        --region="$GCP_REGION" \
        --project="$gcp_project" \
        --format="value(status.url)" 2>/dev/null)

    if [[ -z "$service_url" ]]; then
        log_error "Could not get service URL for: $service_name"
        return 1
    fi

    log_info "Health checking URL: $service_url"

    local attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        log_debug "Health check attempt $attempt/$max_attempts"

        if curl -sf --max-time 30 "$service_url/health" &>/dev/null; then
            log_info "Health check passed for: $service_name"
            return 0
        fi

        if curl -sf --max-time 30 "$service_url" &>/dev/null; then
            log_info "Basic connectivity check passed for: $service_name"
            return 0
        fi

        log_debug "Health check failed, retrying in ${interval}s"
        sleep "$interval"
        ((attempt++))
    done

    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Store rollback information
store_rollback_info() {
    local deployment_id="$1"
    local strategy="$2"
    local from_version="$3"
    local to_version="$4"

    local rollback_file="$DEPLOYMENT_LOCK_DIR/$deployment_id.rollback"

    cat > "$rollback_file" << EOF
{
    "deployment_id": "$deployment_id",
    "strategy": "$strategy",
    "from_version": "$from_version",
    "to_version": "$to_version",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "project": "$GCP_PROJECT",
    "region": "$GCP_REGION"
}
EOF

    log_debug "Stored rollback information: $rollback_file"
}

# Rollback deployment
rollback_deployment() {
    local deployment_id="$1"
    local rollback_file="$DEPLOYMENT_LOCK_DIR/$deployment_id.rollback"

    if [[ ! -f "$rollback_file" ]]; then
        log_error "Rollback information not found for deployment: $deployment_id"
        return 1
    fi

    log_info "Starting rollback for deployment: $deployment_id"

    local strategy=$(jq -r '.strategy' "$rollback_file")
    local from_version=$(jq -r '.from_version' "$rollback_file")
    local to_version=$(jq -r '.to_version' "$rollback_file")

    case "$strategy" in
        "rolling")
            rollback_rolling_deployment "$deployment_id"
            ;;
        "blue_green")
            rollback_blue_green_deployment "$deployment_id" "$to_version" "$from_version"
            ;;
        "canary")
            rollback_canary_deployment_by_id "$deployment_id"
            ;;
        *)
            log_error "Unknown deployment strategy for rollback: $strategy"
            return 1
            ;;
    esac
}

# Monitor deployment progress
monitor_deployment() {
    local deployment_id="$1"
    local max_duration="${2:-$DEPLOYMENT_TIMEOUT}"

    log_info "Monitoring deployment: $deployment_id"

    local start_time=$(date +%s)
    local lock_file="$DEPLOYMENT_LOCK_DIR/$deployment_id.lock"

    while [[ -f "$lock_file" ]]; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ $elapsed -gt $max_duration ]]; then
            log_error "Deployment timeout after ${max_duration}s"
            return 1
        fi

        local status=$(jq -r '.status' "$lock_file" 2>/dev/null || echo "unknown")
        log_debug "Deployment status: $status (${elapsed}s elapsed)"

        case "$status" in
            "completed")
                log_info "Deployment completed successfully"
                return 0
                ;;
            "failed")
                log_error "Deployment failed"
                return 1
                ;;
            "running")
                sleep 10
                ;;
            *)
                log_warn "Unknown deployment status: $status"
                sleep 10
                ;;
        esac
    done

    log_error "Deployment lock file disappeared unexpectedly"
    return 1
}

# Cleanup failed deployment
cleanup_failed_deployment() {
    local deployment_id="$1"
    local service_name="$2"
    local gcp_project="$3"

    log_info "Cleaning up failed deployment: $deployment_id"

    # Remove failed Cloud Run services
    if gcloud run services describe "$service_name" --region="$GCP_REGION" --project="$gcp_project" &>/dev/null; then
        log_info "Removing failed Cloud Run service: $service_name"
        gcloud run services delete "$service_name" \
            --region="$GCP_REGION" \
            --project="$gcp_project" \
            --quiet
    fi

    # Remove deployment artifacts
    remove_deployment_lock "$deployment_id"

    local rollback_file="$DEPLOYMENT_LOCK_DIR/$deployment_id.rollback"
    if [[ -f "$rollback_file" ]]; then
        rm -f "$rollback_file"
    fi

    log_info "Cleanup completed for failed deployment: $deployment_id"
}

# Get deployment status
get_deployment_status() {
    local deployment_id="$1"
    local lock_file="$DEPLOYMENT_LOCK_DIR/$deployment_id.lock"

    if [[ -f "$lock_file" ]]; then
        cat "$lock_file"
        return 0
    else
        echo '{"status": "not_found"}'
        return 1
    fi
}

# List active deployments
list_active_deployments() {
    log_info "Active deployments:"

    if [[ -d "$DEPLOYMENT_LOCK_DIR" ]]; then
        for lock_file in "$DEPLOYMENT_LOCK_DIR"/*.lock; do
            if [[ -f "$lock_file" ]]; then
                local deployment_id=$(basename "$lock_file" .lock)
                local status=$(jq -r '.status' "$lock_file" 2>/dev/null || echo "unknown")
                local started_at=$(jq -r '.started_at' "$lock_file" 2>/dev/null || echo "unknown")

                log_info "  $deployment_id: $status (started: $started_at)"
            fi
        done
    else
        log_info "  No active deployments"
    fi
}

# Update deployment status
update_deployment_status() {
    local deployment_id="$1"
    local new_status="$2"
    local lock_file="$DEPLOYMENT_LOCK_DIR/$deployment_id.lock"

    if [[ -f "$lock_file" ]]; then
        jq --arg status "$new_status" '.status = $status' "$lock_file" > "$lock_file.tmp" && mv "$lock_file.tmp" "$lock_file"
        log_debug "Updated deployment status: $deployment_id -> $new_status"
    fi
}

# Main deployment function
deploy_application() {
    local project_name="$1"
    local environment="$2"
    local gcp_project="$3"
    local strategy="${4:-rolling}"
    local app_yaml="${5:-app.yaml}"

    log_startup

    # Generate deployment ID
    local deployment_id=$(generate_deployment_id "$project_name" "$environment")
    log_info "Starting deployment: $deployment_id"

    # Check prerequisites
    if ! check_deployment_prerequisites "$project_name" "$environment" "$gcp_project"; then
        log_error "Deployment prerequisites not met"
        return 1
    fi

    # Create deployment lock
    if ! create_deployment_lock "$deployment_id"; then
        return 1
    fi

    # Set up cleanup on exit
    trap "cleanup_failed_deployment '$deployment_id' '$project_name-$environment' '$gcp_project'" EXIT

    local deployment_result=0

    # Execute deployment strategy
    case "$strategy" in
        "rolling")
            deploy_rolling "$deployment_id" "$project_name" "$environment" "$gcp_project" "$app_yaml"
            deployment_result=$?
            ;;
        "blue_green")
            deploy_blue_green "$deployment_id" "$project_name" "$environment" "$gcp_project" "$app_yaml"
            deployment_result=$?
            ;;
        "canary")
            deploy_canary "$deployment_id" "$project_name" "$environment" "$gcp_project"
            deployment_result=$?
            ;;
        *)
            log_error "Unknown deployment strategy: $strategy"
            deployment_result=1
            ;;
    esac

    # Update final status
    if [[ $deployment_result -eq 0 ]]; then
        update_deployment_status "$deployment_id" "completed"
        log_info "Deployment completed successfully: $deployment_id"
    else
        update_deployment_status "$deployment_id" "failed"
        log_error "Deployment failed: $deployment_id"
    fi

    # Remove lock
    remove_deployment_lock "$deployment_id"

    # Clear trap
    trap - EXIT

    return $deployment_result
}

# Export functions for use in other scripts
export -f init_deployment_utils deploy_application rollback_deployment
export -f health_check_service monitor_deployment get_deployment_status
export -f list_active_deployments cleanup_failed_deployment

# Initialize on source
init_deployment_utils
