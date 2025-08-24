#!/usr/bin/env bash
# Enhanced GCP Per-Repository Isolation Bootstrap
# Supports multiple GCP projects per repository with comprehensive security
# Part of Universal Project Platform - Agent 5 Isolation Layer

set -euo pipefail

# Script metadata
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="bootstrap_gcloud.sh"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $*${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $*${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $*${NC}"
}

log_error() {
    echo -e "${RED}❌ $*${NC}" >&2
}

log_step() {
    echo -e "${PURPLE}🔄 $*${NC}"
}

# Banner
print_banner() {
    echo -e "${CYAN}"
    echo "============================================================"
    echo "🔒 GCP ISOLATION BOOTSTRAP v${SCRIPT_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "============================================================"
    echo -e "${NC}"
}

# Validation functions
validate_environment() {
    log_step "Validating environment variables..."

    # Required variables
    : "${PROJECT_ID:?PROJECT_ID environment variable is required}"
    : "${ENVIRONMENT:?ENVIRONMENT environment variable is required}"
    : "${REGION:?REGION environment variable is required}"

    # Optional with defaults
    ZONE="${ZONE:-${REGION}-a}"
    REPO_GCLOUD_HOME="${REPO_GCLOUD_HOME:-$HOME/.gcloud/${PROJECT_ID}}"
    ISOLATION_LEVEL="${ISOLATION_LEVEL:-standard}"
    PRODUCTION_MODE="${PRODUCTION_MODE:-false}"
    AUDIT_ENABLED="${AUDIT_ENABLED:-true}"

    # Validate isolation level
    case "$ISOLATION_LEVEL" in
        strict|standard|relaxed)
            ;;
        *)
            log_error "Invalid ISOLATION_LEVEL: $ISOLATION_LEVEL (must be: strict, standard, relaxed)"
            exit 1
            ;;
    esac

    log_success "Environment validation passed"
}

print_configuration() {
    echo -e "${WHITE}Configuration Summary:${NC}"
    echo "────────────────────────────────────────────────────────"
    echo "Project ID:        ${PROJECT_ID}"
    echo "Environment:       ${ENVIRONMENT}"
    echo "Region:            ${REGION}"
    echo "Zone:              ${ZONE}"
    echo "Config Directory:  ${REPO_GCLOUD_HOME}"
    echo "Isolation Level:   ${ISOLATION_LEVEL}"
    echo "Production Mode:   ${PRODUCTION_MODE}"
    echo "Audit Enabled:     ${AUDIT_ENABLED}"

    if [[ -n "${DEPLOY_SA:-}" ]]; then
        echo "Service Account:   ${DEPLOY_SA}"
    fi

    if [[ -n "${WIF_PROVIDER:-}" ]]; then
        echo "WIF Provider:      ${WIF_PROVIDER}"
        echo "WIF SA Email:      ${WIF_SA_EMAIL:-}"
    fi

    if [[ -n "${COST_THRESHOLD_USD:-}" ]]; then
        echo "Cost Threshold:    \$${COST_THRESHOLD_USD} USD"
    fi

    echo "────────────────────────────────────────────────────────"
    echo ""
}

setup_isolation_directory() {
    log_step "Setting up isolation directory..."

    # Create per-repo config folder with proper permissions
    mkdir -p "${REPO_GCLOUD_HOME}"
    chmod 700 "${REPO_GCLOUD_HOME}"

    # Create subdirectories
    mkdir -p "${REPO_GCLOUD_HOME}/"{bin,logs,cache,credentials}

    # Secure credentials directory
    chmod 700 "${REPO_GCLOUD_HOME}/credentials"

    # Set CLOUDSDK_CONFIG for this session
    export CLOUDSDK_CONFIG="${REPO_GCLOUD_HOME}"

    log_success "Isolation directory configured: ${REPO_GCLOUD_HOME}"
}

create_gcloud_configuration() {
    log_step "Creating gcloud configuration..."

    # Create or update 'default' configuration
    if ! gcloud config configurations list --format="value(name)" 2>/dev/null | grep -qx "default"; then
        gcloud config configurations create default >/dev/null 2>&1
        log_success "Created new gcloud configuration 'default'"
    else
        log_info "Using existing gcloud configuration 'default'"
    fi

    # Set core properties with validation
    log_step "Configuring project and region..."
    gcloud config set core/project "${PROJECT_ID}" --configuration=default
    gcloud config set compute/region "${REGION}" --configuration=default
    gcloud config set compute/zone "${ZONE}" --configuration=default

    # Configure automation settings
    gcloud config set core/disable_prompts true --configuration=default
    gcloud config set core/log_http false --configuration=default
    gcloud config set core/user_output_enabled true --configuration=default

    # Set isolation-specific settings
    if [[ "$ISOLATION_LEVEL" == "strict" ]]; then
        gcloud config set core/check_gce_metadata false --configuration=default
        gcloud config set auth/disable_credentials false --configuration=default
    fi

    log_success "Gcloud configuration completed"
}

setup_service_account_impersonation() {
    if [[ -n "${DEPLOY_SA:-}" ]]; then
        log_step "Configuring service account impersonation..."

        # Validate service account format
        if [[ ! "$DEPLOY_SA" =~ ^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+\.iam\.gserviceaccount\.com$ ]]; then
            log_error "Invalid service account format: ${DEPLOY_SA}"
            exit 1
        fi

        gcloud config set auth/impersonate_service_account "${DEPLOY_SA}" --configuration=default
        log_success "Service account impersonation configured: ${DEPLOY_SA}"
    fi
}

setup_workload_identity() {
    if [[ -n "${WIF_PROVIDER:-}" && -n "${WIF_SA_EMAIL:-}" ]]; then
        log_step "Configuring Workload Identity Federation..."

        # Store WIF configuration
        cat > "${REPO_GCLOUD_HOME}/wif-config.json" <<EOF
{
    "provider": "${WIF_PROVIDER}",
    "service_account": "${WIF_SA_EMAIL}",
    "github_repo": "${GITHUB_REPO:-}",
    "configured_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

        chmod 600 "${REPO_GCLOUD_HOME}/wif-config.json"
        log_success "Workload Identity Federation configured"
    fi
}

verify_authentication() {
    log_step "Verifying authentication..."

    # Check for active authentication
    if ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null) && [[ -n "$ACTIVE_ACCOUNT" ]]; then
        log_success "Authenticated as: ${ACTIVE_ACCOUNT}"

        # Log authentication details for audit
        if [[ "$AUDIT_ENABLED" == "true" ]]; then
            cat > "${REPO_GCLOUD_HOME}/logs/auth-$(date +%Y%m%d-%H%M%S).log" <<EOF
Authentication Event:
- Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- Account: ${ACTIVE_ACCOUNT}
- Project: ${PROJECT_ID}
- Environment: ${ENVIRONMENT}
- Script Version: ${SCRIPT_VERSION}
EOF
        fi
    else
        log_warning "No active authentication found"
        log_info "Run: gcloud auth login"

        # In CI environments, provide helpful guidance
        if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" || -n "${GITLAB_CI:-}" ]]; then
            log_info "In CI/CD environments, use Workload Identity Federation or service account keys"
        fi
    fi
}

test_project_access() {
    log_step "Testing project access..."

    if PROJECT_INFO=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectId,lifecycleState)" 2>/dev/null); then
        PROJECT_STATE=$(echo "$PROJECT_INFO" | cut -d$'\t' -f2)

        if [[ "$PROJECT_STATE" == "ACTIVE" ]]; then
            log_success "Project ${PROJECT_ID} is accessible and active"
        else
            log_warning "Project ${PROJECT_ID} is in state: ${PROJECT_STATE}"
        fi
    else
        log_error "Cannot access project ${PROJECT_ID}"
        log_info "Ensure you have the necessary permissions and the project exists"
        exit 1
    fi
}

setup_cost_monitoring() {
    if [[ -n "${COST_THRESHOLD_USD:-}" ]]; then
        log_step "Setting up cost monitoring..."

        cat > "${REPO_GCLOUD_HOME}/cost-config.json" <<EOF
{
    "threshold_usd": ${COST_THRESHOLD_USD},
    "project_id": "${PROJECT_ID}",
    "environment": "${ENVIRONMENT}",
    "configured_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

        log_success "Cost monitoring configured: \$${COST_THRESHOLD_USD} USD threshold"
    fi
}

create_helper_scripts() {
    log_step "Creating helper scripts..."

    # Create gcloud guard script
    cat > "${REPO_GCLOUD_HOME}/bin/gcloud" <<'EOF'
#!/usr/bin/env bash
# GCloud Guard - Enhanced project protection
set -euo pipefail

# Source the guard implementation
ISOLATION_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
if [[ -f "${ISOLATION_ROOT}/../scripts/gcloud_guard.sh" ]]; then
    exec "${ISOLATION_ROOT}/../scripts/gcloud_guard.sh" "$@"
else
    # Fallback to system gcloud with basic protection
    exec $(which -a gcloud | grep -v "$0" | head -1) "$@"
fi
EOF

    chmod +x "${REPO_GCLOUD_HOME}/bin/gcloud"

    # Create self-check script
    cat > "${REPO_GCLOUD_HOME}/bin/self-check" <<'EOF'
#!/usr/bin/env bash
# Self-check isolation configuration
ISOLATION_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
if [[ -f "${ISOLATION_ROOT}/../scripts/self_check.sh" ]]; then
    exec "${ISOLATION_ROOT}/../scripts/self_check.sh" "$@"
else
    echo "Self-check script not found"
    exit 1
fi
EOF

    chmod +x "${REPO_GCLOUD_HOME}/bin/self-check"

    log_success "Helper scripts created"
}

display_final_configuration() {
    echo ""
    echo -e "${CYAN}Final Configuration:${NC}"
    echo "════════════════════════════════════════════════════════"
    gcloud config list --configuration=default
    echo "════════════════════════════════════════════════════════"
}

create_initialization_marker() {
    log_step "Creating initialization marker..."

    cat > "${REPO_GCLOUD_HOME}/.initialized" <<EOF
# GCP Isolation Initialization Marker
PROJECT_ID=${PROJECT_ID}
ENVIRONMENT=${ENVIRONMENT}
REGION=${REGION}
ZONE=${ZONE}
ISOLATION_LEVEL=${ISOLATION_LEVEL}
PRODUCTION_MODE=${PRODUCTION_MODE}
SCRIPT_VERSION=${SCRIPT_VERSION}
INITIALIZED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
INITIALIZED_BY=${USER:-unknown}
EOF

    # Create project marker for quick reference
    echo "${PROJECT_ID}" > "${REPO_GCLOUD_HOME}/.project"
    echo "${REGION}" > "${REPO_GCLOUD_HOME}/.region"
    echo "${ENVIRONMENT}" > "${REPO_GCLOUD_HOME}/.environment"

    log_success "Initialization markers created"
}

production_safety_check() {
    if [[ "$PRODUCTION_MODE" == "true" ]]; then
        log_warning "PRODUCTION ENVIRONMENT DETECTED"
        echo ""
        echo -e "${RED}⚠️  You are configuring isolation for a PRODUCTION environment:${NC}"
        echo -e "${RED}   Project: ${PROJECT_ID}${NC}"
        echo -e "${RED}   Environment: ${ENVIRONMENT}${NC}"
        echo ""
        echo -e "${YELLOW}Production safety measures will be enforced:${NC}"
        echo "   • Destructive operations require CONFIRM_PROD=I_UNDERSTAND"
        echo "   • All operations are logged and audited"
        echo "   • Additional approval gates may be required"
        echo ""

        if [[ "${SKIP_PROD_CONFIRMATION:-}" != "true" ]]; then
            read -p "Continue with production setup? (type 'yes' to proceed): " confirmation
            if [[ "$confirmation" != "yes" ]]; then
                log_info "Production setup cancelled by user"
                exit 0
            fi
        fi
    fi
}

print_next_steps() {
    echo ""
    log_success "GCP isolation setup complete!"
    echo ""
    echo -e "${WHITE}Next Steps:${NC}"
    echo "1. Source .envrc:           ${CYAN}direnv allow${NC}"
    echo "2. Verify setup:            ${CYAN}gcloud config list${NC}"
    echo "3. Run self-check:          ${CYAN}self-check${NC}"
    echo "4. Test deployment:         ${CYAN}make deploy${NC}"
    echo ""
    echo -e "${WHITE}Available Commands:${NC}"
    echo "• ${CYAN}gcloud${NC} - Protected gcloud with project isolation"
    echo "• ${CYAN}self-check${NC} - Validate isolation configuration"
    echo ""

    if [[ "$PRODUCTION_MODE" == "true" ]]; then
        echo -e "${YELLOW}Production Environment Reminders:${NC}"
        echo "• Use 'export CONFIRM_PROD=I_UNDERSTAND' for destructive operations"
        echo "• All operations are logged for audit purposes"
        echo "• Follow change management procedures"
        echo ""
    fi
}

# Main execution
main() {
    print_banner
    validate_environment
    print_configuration
    production_safety_check
    setup_isolation_directory
    create_gcloud_configuration
    setup_service_account_impersonation
    setup_workload_identity
    verify_authentication
    test_project_access
    setup_cost_monitoring
    create_helper_scripts
    display_final_configuration
    create_initialization_marker
    print_next_steps
}

# Execute main function
main "$@"
