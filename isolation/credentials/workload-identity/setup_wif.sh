#!/usr/bin/env bash
# Workload Identity Federation Setup
# Configures secure authentication for CI/CD without service account keys
# Part of Universal Project Platform - Agent 5 Isolation Layer

set -euo pipefail

# Script metadata
WIF_SETUP_VERSION="2.0.0"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $*${NC}"; }
log_success() { echo -e "${GREEN}✅ $*${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $*${NC}"; }
log_error() { echo -e "${RED}❌ $*${NC}" >&2; }
log_step() { echo -e "${PURPLE}🔄 $*${NC}"; }

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "════════════════════════════════════════════════════"
    echo "🔐 WORKLOAD IDENTITY FEDERATION SETUP v${WIF_SETUP_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Validate required parameters
validate_parameters() {
    log_step "Validating parameters..."
    
    # Required parameters
    : "${PROJECT_ID:?PROJECT_ID is required}"
    : "${GITHUB_REPO:?GITHUB_REPO is required (format: owner/repo)}"
    : "${SERVICE_ACCOUNT_NAME:?SERVICE_ACCOUNT_NAME is required}"
    
    # Optional parameters with defaults
    POOL_ID="${POOL_ID:-github-actions-pool}"
    PROVIDER_ID="${PROVIDER_ID:-github-actions-provider}"
    LOCATION="${LOCATION:-global}"
    
    # Validate GitHub repo format
    if [[ ! "$GITHUB_REPO" =~ ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$ ]]; then
        log_error "Invalid GITHUB_REPO format. Expected: owner/repo"
        exit 1
    fi
    
    log_success "Parameters validated"
}

# Display configuration
show_configuration() {
    echo -e "${WHITE}Configuration:${NC}"
    echo "──────────────────────────────────────"
    echo "Project ID:         $PROJECT_ID"
    echo "GitHub Repository:  $GITHUB_REPO"
    echo "Service Account:    $SERVICE_ACCOUNT_NAME"
    echo "Pool ID:            $POOL_ID"
    echo "Provider ID:        $PROVIDER_ID"
    echo "Location:           $LOCATION"
    echo "──────────────────────────────────────"
    echo ""
}

# Check if WIF is already configured
check_existing_wif() {
    log_step "Checking existing Workload Identity Federation setup..."
    
    # Check if pool exists
    if gcloud iam workload-identity-pools describe "$POOL_ID" \
        --location="$LOCATION" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_warning "Workload Identity Pool '$POOL_ID' already exists"
        POOL_EXISTS=true
    else
        log_info "Workload Identity Pool '$POOL_ID' does not exist"
        POOL_EXISTS=false
    fi
    
    # Check if provider exists
    if gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
        --workload-identity-pool="$POOL_ID" \
        --location="$LOCATION" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_warning "Workload Identity Provider '$PROVIDER_ID' already exists"
        PROVIDER_EXISTS=true
    else
        log_info "Workload Identity Provider '$PROVIDER_ID' does not exist"
        PROVIDER_EXISTS=false
    fi
}

# Enable required APIs
enable_apis() {
    log_step "Enabling required APIs..."
    
    local apis=(
        "iamcredentials.googleapis.com"
        "cloudresourcemanager.googleapis.com"
        "sts.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        log_info "Enabling $api..."
        if gcloud services enable "$api" --project="$PROJECT_ID"; then
            log_success "Enabled $api"
        else
            log_error "Failed to enable $api"
            exit 1
        fi
    done
}

# Create service account if it doesn't exist
create_service_account() {
    log_step "Creating service account..."
    
    local sa_email="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    if gcloud iam service-accounts describe "$sa_email" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_warning "Service account already exists: $sa_email"
    else
        if gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
            --display-name="GitHub Actions Service Account" \
            --description="Service account for GitHub Actions via Workload Identity Federation" \
            --project="$PROJECT_ID"; then
            log_success "Created service account: $sa_email"
        else
            log_error "Failed to create service account"
            exit 1
        fi
    fi
    
    echo "$sa_email"
}

# Create Workload Identity Pool
create_wif_pool() {
    if [[ "$POOL_EXISTS" == "false" ]]; then
        log_step "Creating Workload Identity Pool..."
        
        if gcloud iam workload-identity-pools create "$POOL_ID" \
            --location="$LOCATION" \
            --display-name="GitHub Actions Pool" \
            --description="Pool for GitHub Actions authentication" \
            --project="$PROJECT_ID"; then
            log_success "Created Workload Identity Pool: $POOL_ID"
        else
            log_error "Failed to create Workload Identity Pool"
            exit 1
        fi
    else
        log_info "Using existing Workload Identity Pool: $POOL_ID"
    fi
}

# Create Workload Identity Provider
create_wif_provider() {
    if [[ "$PROVIDER_EXISTS" == "false" ]]; then
        log_step "Creating Workload Identity Provider..."
        
        # Create attribute mapping and conditions
        local attribute_mapping='google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner'
        local attribute_condition="assertion.repository_owner == '$(echo "$GITHUB_REPO" | cut -d'/' -f1)'"
        
        if gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
            --workload-identity-pool="$POOL_ID" \
            --location="$LOCATION" \
            --issuer-uri="https://token.actions.githubusercontent.com" \
            --attribute-mapping="$attribute_mapping" \
            --attribute-condition="$attribute_condition" \
            --project="$PROJECT_ID"; then
            log_success "Created Workload Identity Provider: $PROVIDER_ID"
        else
            log_error "Failed to create Workload Identity Provider"
            exit 1
        fi
    else
        log_info "Using existing Workload Identity Provider: $PROVIDER_ID"
    fi
}

# Configure IAM bindings
configure_iam_bindings() {
    log_step "Configuring IAM bindings..."
    
    local sa_email="$1"
    local principal_repo="principalSet://iam.googleapis.com/projects/$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")/locations/$LOCATION/workloadIdentityPools/$POOL_ID/attribute.repository/$GITHUB_REPO"
    local principal_main="principalSet://iam.googleapis.com/projects/$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")/locations/$LOCATION/workloadIdentityPools/$POOL_ID/attribute.repository_owner/$(echo "$GITHUB_REPO" | cut -d'/' -f1)"
    
    # Allow the GitHub Actions to impersonate the service account
    log_info "Binding repository-specific access..."
    if gcloud iam service-accounts add-iam-policy-binding "$sa_email" \
        --role="roles/iam.workloadIdentityUser" \
        --member="$principal_repo" \
        --project="$PROJECT_ID"; then
        log_success "Added repository-specific workload identity binding"
    else
        log_error "Failed to add repository-specific binding"
        exit 1
    fi
    
    # Optional: Allow all repositories in the organization (less secure)
    if [[ "${ALLOW_ORG_ACCESS:-false}" == "true" ]]; then
        log_info "Binding organization-wide access..."
        if gcloud iam service-accounts add-iam-policy-binding "$sa_email" \
            --role="roles/iam.workloadIdentityUser" \
            --member="$principal_main" \
            --project="$PROJECT_ID"; then
            log_success "Added organization-wide workload identity binding"
        else
            log_warning "Failed to add organization-wide binding"
        fi
    fi
}

# Grant necessary permissions to service account
grant_service_account_permissions() {
    log_step "Granting service account permissions..."
    
    local sa_email="$1"
    
    # Basic permissions needed for most operations
    local roles=(
        "roles/cloudtrace.agent"
        "roles/logging.logWriter"
        "roles/monitoring.metricWriter"
        "roles/storage.objectViewer"
    )
    
    # Additional roles based on environment variables
    if [[ "${GRANT_COMPUTE_ADMIN:-false}" == "true" ]]; then
        roles+=("roles/compute.admin")
    fi
    
    if [[ "${GRANT_STORAGE_ADMIN:-false}" == "true" ]]; then
        roles+=("roles/storage.admin")
    fi
    
    if [[ "${GRANT_CLOUDSQL_CLIENT:-false}" == "true" ]]; then
        roles+=("roles/cloudsql.client")
    fi
    
    if [[ "${GRANT_SECRETMANAGER_ACCESSOR:-false}" == "true" ]]; then
        roles+=("roles/secretmanager.secretAccessor")
    fi
    
    # Grant custom roles if specified
    if [[ -n "${CUSTOM_ROLES:-}" ]]; then
        IFS=',' read -ra CUSTOM_ROLE_ARRAY <<< "$CUSTOM_ROLES"
        for role in "${CUSTOM_ROLE_ARRAY[@]}"; do
            roles+=("$role")
        done
    fi
    
    for role in "${roles[@]}"; do
        log_info "Granting role: $role"
        if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$sa_email" \
            --role="$role"; then
            log_success "Granted $role"
        else
            log_warning "Failed to grant $role"
        fi
    done
}

# Generate GitHub Actions workflow configuration
generate_github_actions_config() {
    log_step "Generating GitHub Actions configuration..."
    
    local sa_email="$1"
    local project_number
    project_number=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
    local wif_provider="projects/$project_number/locations/$LOCATION/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID"
    
    local config_file="github-actions-wif-config.yaml"
    
    cat > "$config_file" <<EOF
# GitHub Actions Workload Identity Federation Configuration
# Generated by Universal Project Platform - Agent 5 Isolation Layer
# 
# Add this to your GitHub Actions workflow to authenticate with GCP:
#
# jobs:
#   deploy:
#     runs-on: ubuntu-latest
#     permissions:
#       contents: read
#       id-token: write
#
#     steps:
#     - name: Checkout
#       uses: actions/checkout@v4
#
#     - name: Authenticate to Google Cloud
#       uses: google-github-actions/auth@v2
#       with:
#         workload_identity_provider: '${wif_provider}'
#         service_account: '${sa_email}'
#
#     - name: Set up Cloud SDK
#       uses: google-github-actions/setup-gcloud@v2
#
#     - name: Configure gcloud for project
#       run: |
#         gcloud config set project ${PROJECT_ID}
#         gcloud auth list

# GitHub Secrets to configure (optional, for additional security):
# - GCP_PROJECT_ID: ${PROJECT_ID}
# - GCP_SERVICE_ACCOUNT: ${sa_email}
# - WIF_PROVIDER: ${wif_provider}

# Environment Variables for this configuration:
export PROJECT_ID="${PROJECT_ID}"
export WIF_PROVIDER="${wif_provider}"
export WIF_SA_EMAIL="${sa_email}"
export GITHUB_REPO="${GITHUB_REPO}"
EOF
    
    log_success "Generated GitHub Actions configuration: $config_file"
    
    # Also create environment file for local testing
    cat > ".envrc.wif" <<EOF
# Workload Identity Federation Environment Variables
# Source this file or add to your .envrc for local testing
export PROJECT_ID="${PROJECT_ID}"
export WIF_PROVIDER="${wif_provider}"
export WIF_SA_EMAIL="${sa_email}"
export GITHUB_REPO="${GITHUB_REPO}"
EOF
    
    log_success "Generated local environment file: .envrc.wif"
}

# Test WIF configuration
test_wif_configuration() {
    log_step "Testing Workload Identity Federation configuration..."
    
    local sa_email="$1"
    
    # Basic validation - check if resources exist and are accessible
    if gcloud iam workload-identity-pools describe "$POOL_ID" \
        --location="$LOCATION" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_success "Workload Identity Pool is accessible"
    else
        log_error "Cannot access Workload Identity Pool"
        return 1
    fi
    
    if gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
        --workload-identity-pool="$POOL_ID" \
        --location="$LOCATION" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_success "Workload Identity Provider is accessible"
    else
        log_error "Cannot access Workload Identity Provider"
        return 1
    fi
    
    if gcloud iam service-accounts describe "$sa_email" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_success "Service account is accessible"
    else
        log_error "Cannot access service account"
        return 1
    fi
    
    log_success "WIF configuration test completed"
}

# Create audit log
create_audit_log() {
    log_step "Creating audit log..."
    
    local sa_email="$1"
    local project_number
    project_number=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
    local wif_provider="projects/$project_number/locations/$LOCATION/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID"
    
    local audit_file="wif-setup-audit-$(date +%Y%m%d-%H%M%S).json"
    
    cat > "$audit_file" <<EOF
{
  "setup_metadata": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "script_version": "$WIF_SETUP_VERSION",
    "user": "${USER:-unknown}",
    "project_id": "$PROJECT_ID"
  },
  "configuration": {
    "github_repo": "$GITHUB_REPO",
    "service_account": "$sa_email",
    "pool_id": "$POOL_ID",
    "provider_id": "$PROVIDER_ID",
    "location": "$LOCATION",
    "wif_provider": "$wif_provider"
  },
  "resources_created": {
    "pool_created": $([[ "$POOL_EXISTS" == "false" ]] && echo "true" || echo "false"),
    "provider_created": $([[ "$PROVIDER_EXISTS" == "false" ]] && echo "true" || echo "false"),
    "service_account_email": "$sa_email"
  },
  "security_notes": {
    "attribute_condition_applied": true,
    "repository_scoped": true,
    "organization_access": ${ALLOW_ORG_ACCESS:-false}
  }
}
EOF
    
    log_success "Created audit log: $audit_file"
}

# Print next steps
print_next_steps() {
    log_section() { echo -e "${CYAN}═══ $1 ═══${NC}"; }
    
    echo ""
    log_section "Setup Complete!"
    
    echo -e "${WHITE}Next Steps:${NC}"
    echo ""
    echo "1. Add the GitHub Actions workflow configuration from:"
    echo "   ${CYAN}github-actions-wif-config.yaml${NC}"
    echo ""
    echo "2. Ensure your GitHub Actions workflow has the required permissions:"
    echo "   ${CYAN}permissions:${NC}"
    echo "     ${CYAN}contents: read${NC}"
    echo "     ${CYAN}id-token: write${NC}"
    echo ""
    echo "3. Test the configuration by running a GitHub Actions workflow"
    echo ""
    echo "4. For local testing, source the WIF environment:"
    echo "   ${CYAN}source .envrc.wif${NC}"
    echo ""
    
    if [[ "${PRODUCTION_MODE:-false}" == "true" ]]; then
        echo -e "${YELLOW}Production Environment Notes:${NC}"
        echo "• Review and approve all IAM bindings"
        echo "• Consider additional security constraints"
        echo "• Monitor service account usage"
        echo "• Set up alerting for authentication events"
        echo ""
    fi
    
    echo -e "${WHITE}Troubleshooting:${NC}"
    echo "• Verify repository name exactly matches: $GITHUB_REPO"
    echo "• Ensure GitHub Actions has 'id-token: write' permission"
    echo "• Check IAM bindings if authentication fails"
    echo "• Review audit log for configuration details"
}

# Main execution
main() {
    print_banner
    validate_parameters
    show_configuration
    
    # Confirmation for production
    if [[ "${PRODUCTION_MODE:-false}" == "true" && "${SKIP_CONFIRMATION:-false}" != "true" ]]; then
        echo -e "${YELLOW}⚠️  Production environment detected${NC}"
        read -p "Continue with WIF setup? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Setup cancelled"
            exit 0
        fi
    fi
    
    check_existing_wif
    enable_apis
    
    local sa_email
    sa_email=$(create_service_account)
    
    create_wif_pool
    create_wif_provider
    configure_iam_bindings "$sa_email"
    grant_service_account_permissions "$sa_email"
    generate_github_actions_config "$sa_email"
    test_wif_configuration "$sa_email"
    create_audit_log "$sa_email"
    print_next_steps
    
    log_success "Workload Identity Federation setup complete!"
}

# Script usage
show_usage() {
    echo "Usage: $0"
    echo ""
    echo "Required Environment Variables:"
    echo "  PROJECT_ID              - GCP Project ID"
    echo "  GITHUB_REPO            - GitHub repository (format: owner/repo)"
    echo "  SERVICE_ACCOUNT_NAME   - Service account name to create"
    echo ""
    echo "Optional Environment Variables:"
    echo "  POOL_ID                - WIF Pool ID (default: github-actions-pool)"
    echo "  PROVIDER_ID            - WIF Provider ID (default: github-actions-provider)"
    echo "  LOCATION               - Location (default: global)"
    echo "  ALLOW_ORG_ACCESS       - Allow org-wide access (default: false)"
    echo "  GRANT_COMPUTE_ADMIN    - Grant compute admin role (default: false)"
    echo "  GRANT_STORAGE_ADMIN    - Grant storage admin role (default: false)"
    echo "  GRANT_CLOUDSQL_CLIENT  - Grant Cloud SQL client role (default: false)"
    echo "  GRANT_SECRETMANAGER_ACCESSOR - Grant Secret Manager accessor (default: false)"
    echo "  CUSTOM_ROLES           - Comma-separated list of custom roles"
    echo ""
    echo "Example:"
    echo "  PROJECT_ID=my-project GITHUB_REPO=owner/repo SERVICE_ACCOUNT_NAME=github-actions $0"
}

# Handle help
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    show_usage
    exit 0
fi

# Execute main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi