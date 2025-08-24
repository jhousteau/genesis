#!/bin/bash

# GCP Authentication and Isolation Module
# Provides secure authentication and project isolation for GCP operations

# Source logging utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../logging/logger.sh"

# Default configuration
GCP_CONFIG_DIR="${GCP_CONFIG_DIR:-$HOME/.gcloud-isolated}"
DEFAULT_REGION="${DEFAULT_REGION:-us-central1}"
DEFAULT_ZONE="${DEFAULT_ZONE:-us-central1-a}"
SERVICE_ACCOUNT_KEY_DIR="${SERVICE_ACCOUNT_KEY_DIR:-$HOME/.gcp-keys}"

# Authentication state
declare -A GCP_CONTEXTS=()
CURRENT_GCP_CONTEXT=""

# Initialize GCP authentication module
init_gcp_auth() {
    log_info "Initializing GCP authentication module"

    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Please install Google Cloud SDK"
        return 1
    fi

    # Create necessary directories
    mkdir -p "$GCP_CONFIG_DIR" "$SERVICE_ACCOUNT_KEY_DIR"
    chmod 700 "$GCP_CONFIG_DIR" "$SERVICE_ACCOUNT_KEY_DIR"

    # Set default gcloud configuration
    export CLOUDSDK_CONFIG="$GCP_CONFIG_DIR/default"
    mkdir -p "$CLOUDSDK_CONFIG"

    log_info "GCP authentication module initialized"
    return 0
}

# Create isolated GCP context
create_gcp_context() {
    local context_name="$1"
    local project_id="$2"
    local service_account="${3:-}"
    local region="${4:-$DEFAULT_REGION}"
    local zone="${5:-$DEFAULT_ZONE}"

    if [[ -z "$context_name" || -z "$project_id" ]]; then
        log_error "Context name and project ID are required"
        return 1
    fi

    log_info "Creating GCP context: $context_name for project: $project_id"

    local context_dir="$GCP_CONFIG_DIR/$context_name"
    mkdir -p "$context_dir"
    chmod 700 "$context_dir"

    # Store context configuration
    local context_config="$context_dir/context.json"
    cat > "$context_config" << EOF
{
    "name": "$context_name",
    "project_id": "$project_id",
    "service_account": "$service_account",
    "region": "$region",
    "zone": "$zone",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "config_dir": "$context_dir"
}
EOF

    # Store in memory
    GCP_CONTEXTS["$context_name"]="$context_config"

    # Initialize gcloud configuration for this context
    CLOUDSDK_CONFIG="$context_dir" gcloud config configurations create "$context_name" 2>/dev/null || true
    CLOUDSDK_CONFIG="$context_dir" gcloud config set project "$project_id"
    CLOUDSDK_CONFIG="$context_dir" gcloud config set compute/region "$region"
    CLOUDSDK_CONFIG="$context_dir" gcloud config set compute/zone "$zone"

    log_info "GCP context created successfully: $context_name"
    return 0
}

# Switch to GCP context
switch_gcp_context() {
    local context_name="$1"

    if [[ -z "$context_name" ]]; then
        log_error "Context name is required"
        return 1
    fi

    local context_dir="$GCP_CONFIG_DIR/$context_name"
    local context_config="$context_dir/context.json"

    if [[ ! -f "$context_config" ]]; then
        log_error "GCP context not found: $context_name"
        return 1
    fi

    log_info "Switching to GCP context: $context_name"

    # Set environment variables
    export CLOUDSDK_CONFIG="$context_dir"
    export GOOGLE_CLOUD_PROJECT=$(jq -r '.project_id' "$context_config")
    export GCP_PROJECT="$GOOGLE_CLOUD_PROJECT"
    export GCP_REGION=$(jq -r '.region' "$context_config")
    export GCP_ZONE=$(jq -r '.zone' "$context_config")

    # Set current context
    CURRENT_GCP_CONTEXT="$context_name"

    # Verify context is working
    if ! CLOUDSDK_CONFIG="$context_dir" gcloud config get-value project &>/dev/null; then
        log_error "Failed to switch to GCP context: $context_name"
        return 1
    fi

    log_info "Successfully switched to GCP context: $context_name (project: $GOOGLE_CLOUD_PROJECT)"
    return 0
}

# Authenticate with service account
authenticate_service_account() {
    local context_name="$1"
    local key_file_path="$2"

    if [[ -z "$context_name" || -z "$key_file_path" ]]; then
        log_error "Context name and key file path are required"
        return 1
    fi

    if [[ ! -f "$key_file_path" ]]; then
        log_error "Service account key file not found: $key_file_path"
        return 1
    fi

    log_info "Authenticating service account for context: $context_name"

    # Switch to context first
    if ! switch_gcp_context "$context_name"; then
        return 1
    fi

    # Authenticate with service account
    if CLOUDSDK_CONFIG="$CLOUDSDK_CONFIG" gcloud auth activate-service-account --key-file="$key_file_path"; then
        log_info "Service account authentication successful"

        # Update context configuration with service account info
        local context_config="$GCP_CONFIG_DIR/$context_name/context.json"
        local service_account_email=$(jq -r '.client_email' "$key_file_path")

        # Update context with service account email
        jq --arg sa "$service_account_email" '.service_account = $sa' "$context_config" > "$context_config.tmp" && mv "$context_config.tmp" "$context_config"

        return 0
    else
        log_error "Service account authentication failed"
        return 1
    fi
}

# Authenticate with user account (interactive)
authenticate_user_account() {
    local context_name="$1"

    if [[ -z "$context_name" ]]; then
        log_error "Context name is required"
        return 1
    fi

    log_info "Starting user authentication for context: $context_name"

    # Switch to context first
    if ! switch_gcp_context "$context_name"; then
        return 1
    fi

    # Authenticate with user account
    if CLOUDSDK_CONFIG="$CLOUDSDK_CONFIG" gcloud auth login; then
        log_info "User authentication successful"
        return 0
    else
        log_error "User authentication failed"
        return 1
    fi
}

# Check authentication status
check_auth_status() {
    local context_name="${1:-$CURRENT_GCP_CONTEXT}"

    if [[ -z "$context_name" ]]; then
        log_error "No context specified and no current context set"
        return 1
    fi

    local context_dir="$GCP_CONFIG_DIR/$context_name"

    if [[ ! -d "$context_dir" ]]; then
        log_error "Context not found: $context_name"
        return 1
    fi

    # Check if authenticated
    if CLOUDSDK_CONFIG="$context_dir" gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        local active_account=$(CLOUDSDK_CONFIG="$context_dir" gcloud auth list --filter=status:ACTIVE --format="value(account)")
        local project=$(CLOUDSDK_CONFIG="$context_dir" gcloud config get-value project)

        log_info "Authentication status for context $context_name:"
        log_info "  Active account: $active_account"
        log_info "  Project: $project"
        return 0
    else
        log_warn "No active authentication for context: $context_name"
        return 1
    fi
}

# List available contexts
list_gcp_contexts() {
    log_info "Available GCP contexts:"

    if [[ -d "$GCP_CONFIG_DIR" ]]; then
        for context_dir in "$GCP_CONFIG_DIR"/*; do
            if [[ -d "$context_dir" && -f "$context_dir/context.json" ]]; then
                local context_name=$(basename "$context_dir")
                local project_id=$(jq -r '.project_id' "$context_dir/context.json" 2>/dev/null || echo "unknown")
                local current_marker=""

                if [[ "$context_name" == "$CURRENT_GCP_CONTEXT" ]]; then
                    current_marker=" (current)"
                fi

                log_info "  $context_name -> $project_id$current_marker"
            fi
        done
    else
        log_info "  No contexts found"
    fi
}

# Remove GCP context
remove_gcp_context() {
    local context_name="$1"
    local force="${2:-false}"

    if [[ -z "$context_name" ]]; then
        log_error "Context name is required"
        return 1
    fi

    local context_dir="$GCP_CONFIG_DIR/$context_name"

    if [[ ! -d "$context_dir" ]]; then
        log_error "Context not found: $context_name"
        return 1
    fi

    if [[ "$context_name" == "$CURRENT_GCP_CONTEXT" && "$force" != "true" ]]; then
        log_error "Cannot remove current context. Switch to another context first or use --force"
        return 1
    fi

    log_info "Removing GCP context: $context_name"

    # Remove from gcloud configurations
    CLOUDSDK_CONFIG="$context_dir" gcloud config configurations delete "$context_name" --quiet 2>/dev/null || true

    # Remove directory
    rm -rf "$context_dir"

    # Remove from memory
    unset GCP_CONTEXTS["$context_name"]

    # Clear current context if it was removed
    if [[ "$context_name" == "$CURRENT_GCP_CONTEXT" ]]; then
        CURRENT_GCP_CONTEXT=""
        unset CLOUDSDK_CONFIG GOOGLE_CLOUD_PROJECT GCP_PROJECT GCP_REGION GCP_ZONE
    fi

    log_info "GCP context removed: $context_name"
    return 0
}

# Verify GCP permissions
verify_gcp_permissions() {
    local context_name="${1:-$CURRENT_GCP_CONTEXT}"
    local required_permissions=("$@")

    if [[ -z "$context_name" ]]; then
        log_error "No context specified and no current context set"
        return 1
    fi

    if ! switch_gcp_context "$context_name"; then
        return 1
    fi

    log_info "Verifying GCP permissions for context: $context_name"

    # Test basic project access
    if ! CLOUDSDK_CONFIG="$CLOUDSDK_CONFIG" gcloud projects describe "$GCP_PROJECT" &>/dev/null; then
        log_error "Cannot access project: $GCP_PROJECT"
        return 1
    fi

    # Test specific permissions if provided
    if [[ ${#required_permissions[@]} -gt 1 ]]; then
        # Skip first argument which is context_name
        for permission in "${required_permissions[@]:1}"; do
            log_debug "Testing permission: $permission"

            case "$permission" in
                "compute.instances.list")
                    if ! CLOUDSDK_CONFIG="$CLOUDSDK_CONFIG" gcloud compute instances list --limit=1 &>/dev/null; then
                        log_error "Missing permission: $permission"
                        return 1
                    fi
                    ;;
                "storage.buckets.list")
                    if ! CLOUDSDK_CONFIG="$CLOUDSDK_CONFIG" gcloud storage buckets list --limit=1 &>/dev/null; then
                        log_error "Missing permission: $permission"
                        return 1
                    fi
                    ;;
                "cloudsql.instances.list")
                    if ! CLOUDSDK_CONFIG="$CLOUDSDK_CONFIG" gcloud sql instances list --limit=1 &>/dev/null; then
                        log_error "Missing permission: $permission"
                        return 1
                    fi
                    ;;
                *)
                    log_warn "Unknown permission test: $permission"
                    ;;
            esac
        done
    fi

    log_info "GCP permissions verified successfully"
    return 0
}

# Setup Application Default Credentials
setup_adc() {
    local context_name="${1:-$CURRENT_GCP_CONTEXT}"

    if [[ -z "$context_name" ]]; then
        log_error "No context specified and no current context set"
        return 1
    fi

    if ! switch_gcp_context "$context_name"; then
        return 1
    fi

    log_info "Setting up Application Default Credentials for context: $context_name"

    if CLOUDSDK_CONFIG="$CLOUDSDK_CONFIG" gcloud auth application-default login; then
        log_info "Application Default Credentials configured successfully"
        return 0
    else
        log_error "Failed to setup Application Default Credentials"
        return 1
    fi
}

# Execute command with GCP context
with_gcp_context() {
    local context_name="$1"
    shift

    if [[ -z "$context_name" ]]; then
        log_error "Context name is required"
        return 1
    fi

    # Save current context
    local old_context="$CURRENT_GCP_CONTEXT"
    local old_cloudsdk_config="${CLOUDSDK_CONFIG:-}"
    local old_gcp_project="${GCP_PROJECT:-}"
    local old_gcp_region="${GCP_REGION:-}"
    local old_gcp_zone="${GCP_ZONE:-}"

    # Switch to new context
    if switch_gcp_context "$context_name"; then
        # Execute command
        "$@"
        local exit_code=$?

        # Restore old context
        if [[ -n "$old_context" ]]; then
            switch_gcp_context "$old_context"
        else
            CURRENT_GCP_CONTEXT=""
            export CLOUDSDK_CONFIG="$old_cloudsdk_config"
            export GCP_PROJECT="$old_gcp_project"
            export GCP_REGION="$old_gcp_region"
            export GCP_ZONE="$old_gcp_zone"
        fi

        return $exit_code
    else
        log_error "Failed to switch to context: $context_name"
        return 1
    fi
}

# Get current GCP context info
get_current_context() {
    if [[ -n "$CURRENT_GCP_CONTEXT" ]]; then
        echo "$CURRENT_GCP_CONTEXT"
        return 0
    else
        log_warn "No current GCP context set"
        return 1
    fi
}

# Refresh authentication token
refresh_auth_token() {
    local context_name="${1:-$CURRENT_GCP_CONTEXT}"

    if [[ -z "$context_name" ]]; then
        log_error "No context specified and no current context set"
        return 1
    fi

    if ! switch_gcp_context "$context_name"; then
        return 1
    fi

    log_info "Refreshing authentication token for context: $context_name"

    if CLOUDSDK_CONFIG="$CLOUDSDK_CONFIG" gcloud auth application-default print-access-token &>/dev/null; then
        log_info "Authentication token refreshed successfully"
        return 0
    else
        log_error "Failed to refresh authentication token"
        return 1
    fi
}

# Export functions for use in other scripts
export -f init_gcp_auth create_gcp_context switch_gcp_context
export -f authenticate_service_account authenticate_user_account check_auth_status
export -f list_gcp_contexts remove_gcp_context verify_gcp_permissions
export -f setup_adc with_gcp_context get_current_context refresh_auth_token

# Initialize on source
init_gcp_auth
