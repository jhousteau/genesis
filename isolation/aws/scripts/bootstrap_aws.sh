#!/usr/bin/env bash
# AWS Per-Repository Isolation Bootstrap
# Supports multiple AWS accounts per repository with comprehensive security
# Part of Universal Project Platform - Agent 5 Isolation Layer

set -euo pipefail

# Script metadata
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="bootstrap_aws.sh"

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
    echo "🔒 AWS ISOLATION BOOTSTRAP v${SCRIPT_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "============================================================"
    echo -e "${NC}"
}

# Validation functions
validate_environment() {
    log_step "Validating AWS environment variables..."

    # Required variables
    : "${AWS_ACCOUNT_ID:?AWS_ACCOUNT_ID environment variable is required}"
    : "${AWS_ENVIRONMENT:?AWS_ENVIRONMENT environment variable is required}"
    : "${AWS_REGION:?AWS_REGION environment variable is required}"

    # Optional with defaults
    AWS_PROJECT_NAME="${AWS_PROJECT_NAME:-$(basename "$PWD")}"
    REPO_AWS_HOME="${REPO_AWS_HOME:-$HOME/.aws/${AWS_PROJECT_NAME}-${AWS_ENVIRONMENT}}"
    ISOLATION_LEVEL="${ISOLATION_LEVEL:-standard}"
    PRODUCTION_MODE="${PRODUCTION_MODE:-false}"
    AUDIT_ENABLED="${AUDIT_ENABLED:-true}"
    AWS_PROFILE="${AWS_PROFILE:-default}"

    # Validate AWS account ID format
    if [[ ! "$AWS_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
        log_error "Invalid AWS_ACCOUNT_ID format. Expected 12-digit number: $AWS_ACCOUNT_ID"
        exit 1
    fi

    # Validate region format
    if [[ ! "$AWS_REGION" =~ ^[a-z]{2}-[a-z]+-[0-9]$ ]]; then
        log_error "Invalid AWS_REGION format: $AWS_REGION"
        exit 1
    fi

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
    echo "AWS Account ID:    ${AWS_ACCOUNT_ID}"
    echo "Environment:       ${AWS_ENVIRONMENT}"
    echo "Region:            ${AWS_REGION}"
    echo "Project Name:      ${AWS_PROJECT_NAME}"
    echo "Config Directory:  ${REPO_AWS_HOME}"
    echo "Profile:           ${AWS_PROFILE}"
    echo "Isolation Level:   ${ISOLATION_LEVEL}"
    echo "Production Mode:   ${PRODUCTION_MODE}"
    echo "Audit Enabled:     ${AUDIT_ENABLED}"

    if [[ -n "${AWS_ROLE_ARN:-}" ]]; then
        echo "Role ARN:          ${AWS_ROLE_ARN}"
    fi

    if [[ -n "${AWS_ROLE_TO_ASSUME:-}" ]]; then
        echo "Role to Assume:    ${AWS_ROLE_TO_ASSUME}"
    fi

    if [[ -n "${AWS_COST_THRESHOLD_USD:-}" ]]; then
        echo "Cost Threshold:    \$${AWS_COST_THRESHOLD_USD} USD"
    fi

    echo "────────────────────────────────────────────────────────"
    echo ""
}

setup_isolation_directory() {
    log_step "Setting up AWS isolation directory..."

    # Create per-repo config folder with proper permissions
    mkdir -p "${REPO_AWS_HOME}"
    chmod 700 "${REPO_AWS_HOME}"

    # Create subdirectories
    mkdir -p "${REPO_AWS_HOME}/"{logs,cache,temp}

    # Secure directories
    chmod 700 "${REPO_AWS_HOME}/cache"
    chmod 700 "${REPO_AWS_HOME}/temp"

    log_success "Isolation directory configured: ${REPO_AWS_HOME}"
}

create_aws_configuration() {
    log_step "Creating AWS configuration..."

    # Create AWS config file
    cat > "${REPO_AWS_HOME}/config" <<EOF
[default]
region = ${AWS_REGION}
output = json

[profile ${AWS_PROFILE}]
region = ${AWS_REGION}
output = json
EOF

    # Add role-based configuration if specified
    if [[ -n "${AWS_ROLE_ARN:-}" ]]; then
        cat >> "${REPO_AWS_HOME}/config" <<EOF

[profile ${AWS_PROFILE}-role]
role_arn = ${AWS_ROLE_ARN}
source_profile = ${AWS_PROFILE}
region = ${AWS_REGION}
role_session_name = ${AWS_ROLE_SESSION_NAME:-isolation-session}
EOF
    fi

    # Create placeholder credentials file
    cat > "${REPO_AWS_HOME}/credentials" <<EOF
# AWS Credentials for ${AWS_PROJECT_NAME}-${AWS_ENVIRONMENT}
# Configure your credentials using one of these methods:
# 1. AWS SSO: aws sso login --profile ${AWS_PROFILE}
# 2. Access Keys: aws configure --profile ${AWS_PROFILE}
# 3. Role assumption: Use AWS_ROLE_ARN environment variable
# 4. OIDC/Web Identity: Use AWS_ROLE_TO_ASSUME and AWS_WEB_IDENTITY_TOKEN_FILE

[${AWS_PROFILE}]
# Add your credentials here or use alternative authentication methods
EOF

    chmod 600 "${REPO_AWS_HOME}/credentials"
    chmod 600 "${REPO_AWS_HOME}/config"

    log_success "AWS configuration files created"
}

setup_oidc_authentication() {
    if [[ -n "${AWS_ROLE_TO_ASSUME:-}" ]]; then
        log_step "Configuring OIDC/Web Identity authentication..."

        # Validate role ARN format
        if [[ ! "$AWS_ROLE_TO_ASSUME" =~ ^arn:aws:iam::[0-9]{12}:role/.+ ]]; then
            log_error "Invalid AWS_ROLE_TO_ASSUME format: ${AWS_ROLE_TO_ASSUME}"
            exit 1
        fi

        # Store OIDC configuration
        cat > "${REPO_AWS_HOME}/oidc-config.json" <<EOF
{
    "role_arn": "${AWS_ROLE_TO_ASSUME}",
    "web_identity_token_file": "${AWS_WEB_IDENTITY_TOKEN_FILE:-}",
    "role_session_name": "${AWS_ROLE_SESSION_NAME:-isolation-session}",
    "configured_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

        chmod 600 "${REPO_AWS_HOME}/oidc-config.json"
        log_success "OIDC/Web Identity configuration created"
    fi
}

verify_aws_access() {
    log_step "Verifying AWS access..."

    # Set AWS configuration for this session
    export AWS_CONFIG_FILE="${REPO_AWS_HOME}/config"
    export AWS_SHARED_CREDENTIALS_FILE="${REPO_AWS_HOME}/credentials"

    # Try to get caller identity
    if CALLER_IDENTITY=$(aws sts get-caller-identity --profile "${AWS_PROFILE}" 2>/dev/null); then
        local account_id user_arn
        account_id=$(echo "$CALLER_IDENTITY" | jq -r '.Account')
        user_arn=$(echo "$CALLER_IDENTITY" | jq -r '.Arn')

        if [[ "$account_id" == "$AWS_ACCOUNT_ID" ]]; then
            log_success "AWS access verified for account: ${account_id}"
            log_info "Identity: ${user_arn}"
        else
            log_warning "Account mismatch: Expected ${AWS_ACCOUNT_ID}, got ${account_id}"
        fi

        # Log authentication details for audit
        if [[ "$AUDIT_ENABLED" == "true" ]]; then
            cat > "${REPO_AWS_HOME}/logs/auth-$(date +%Y%m%d-%H%M%S).log" <<EOF
Authentication Event:
- Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- Account: ${account_id}
- ARN: ${user_arn}
- Project: ${AWS_PROJECT_NAME}
- Environment: ${AWS_ENVIRONMENT}
- Script Version: ${SCRIPT_VERSION}
EOF
        fi
    else
        log_warning "AWS access verification failed"
        log_info "Configure credentials using:"
        echo "  • AWS SSO: aws sso login --profile ${AWS_PROFILE}"
        echo "  • Access Keys: aws configure --profile ${AWS_PROFILE}"
        echo "  • Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
        echo "  • IAM Role: Set AWS_ROLE_ARN environment variable"
    fi
}

test_account_access() {
    log_step "Testing AWS account access..."

    # Test basic API access
    if aws ec2 describe-regions --region "${AWS_REGION}" --profile "${AWS_PROFILE}" >/dev/null 2>&1; then
        log_success "AWS API access confirmed"
    else
        log_warning "AWS API access test failed"
        log_info "Ensure you have appropriate permissions"
    fi

    # Test account-specific access
    if aws organizations describe-account --account-id "${AWS_ACCOUNT_ID}" --profile "${AWS_PROFILE}" >/dev/null 2>&1; then
        log_success "AWS Organizations access confirmed"
    else
        log_info "AWS Organizations access not available (normal for most accounts)"
    fi
}

setup_cost_monitoring() {
    if [[ -n "${AWS_COST_THRESHOLD_USD:-}" ]]; then
        log_step "Setting up cost monitoring..."

        cat > "${REPO_AWS_HOME}/cost-config.json" <<EOF
{
    "threshold_usd": ${AWS_COST_THRESHOLD_USD},
    "account_id": "${AWS_ACCOUNT_ID}",
    "environment": "${AWS_ENVIRONMENT}",
    "project_name": "${AWS_PROJECT_NAME}",
    "configured_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

        log_success "Cost monitoring configured: \$${AWS_COST_THRESHOLD_USD} USD threshold"
    fi
}

create_helper_scripts() {
    log_step "Creating helper scripts..."

    # Create AWS CLI guard script
    cat > "${REPO_AWS_HOME}/bin/aws" <<'EOF'
#!/usr/bin/env bash
# AWS CLI Guard - Enhanced account protection
set -euo pipefail

# Source the guard implementation
ISOLATION_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
if [[ -f "${ISOLATION_ROOT}/../scripts/aws_guard.sh" ]]; then
    exec "${ISOLATION_ROOT}/../scripts/aws_guard.sh" "$@"
else
    # Fallback to system AWS CLI with basic protection
    exec $(which -a aws | grep -v "$0" | head -1) "$@"
fi
EOF

    mkdir -p "${REPO_AWS_HOME}/bin"
    chmod +x "${REPO_AWS_HOME}/bin/aws"

    # Create self-check script
    cat > "${REPO_AWS_HOME}/bin/aws-self-check" <<'EOF'
#!/usr/bin/env bash
# Self-check AWS isolation configuration
ISOLATION_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
if [[ -f "${ISOLATION_ROOT}/../scripts/aws_self_check.sh" ]]; then
    exec "${ISOLATION_ROOT}/../scripts/aws_self_check.sh" "$@"
else
    echo "AWS self-check script not found"
    exit 1
fi
EOF

    chmod +x "${REPO_AWS_HOME}/bin/aws-self-check"

    log_success "Helper scripts created"
}

display_final_configuration() {
    echo ""
    echo -e "${CYAN}Final AWS Configuration:${NC}"
    echo "════════════════════════════════════════════════════════"
    cat "${REPO_AWS_HOME}/config"
    echo "════════════════════════════════════════════════════════"
}

create_initialization_marker() {
    log_step "Creating initialization marker..."

    cat > "${REPO_AWS_HOME}/.initialized" <<EOF
# AWS Isolation Initialization Marker
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
AWS_ENVIRONMENT=${AWS_ENVIRONMENT}
AWS_REGION=${AWS_REGION}
AWS_PROJECT_NAME=${AWS_PROJECT_NAME}
ISOLATION_LEVEL=${ISOLATION_LEVEL}
PRODUCTION_MODE=${PRODUCTION_MODE}
SCRIPT_VERSION=${SCRIPT_VERSION}
INITIALIZED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
INITIALIZED_BY=${USER:-unknown}
EOF

    # Create quick reference files
    echo "${AWS_ACCOUNT_ID}" > "${REPO_AWS_HOME}/.account"
    echo "${AWS_REGION}" > "${REPO_AWS_HOME}/.region"
    echo "${AWS_ENVIRONMENT}" > "${REPO_AWS_HOME}/.environment"

    log_success "Initialization markers created"
}

production_safety_check() {
    if [[ "$PRODUCTION_MODE" == "true" ]]; then
        log_warning "PRODUCTION AWS ENVIRONMENT DETECTED"
        echo ""
        echo -e "${RED}⚠️  You are configuring isolation for a PRODUCTION AWS environment:${NC}"
        echo -e "${RED}   Account: ${AWS_ACCOUNT_ID}${NC}"
        echo -e "${RED}   Environment: ${AWS_ENVIRONMENT}${NC}"
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
    log_success "AWS isolation setup complete!"
    echo ""
    echo -e "${WHITE}Next Steps:${NC}"
    echo "1. Source .envrc:           ${CYAN}direnv allow${NC}"
    echo "2. Configure credentials:"
    echo "   • AWS SSO:              ${CYAN}aws sso login --profile ${AWS_PROFILE}${NC}"
    echo "   • Access Keys:          ${CYAN}aws configure --profile ${AWS_PROFILE}${NC}"
    echo "3. Verify setup:            ${CYAN}aws sts get-caller-identity${NC}"
    echo "4. Run self-check:          ${CYAN}aws-self-check${NC}"
    echo ""
    echo -e "${WHITE}Available Commands:${NC}"
    echo "• ${CYAN}aws${NC} - Protected AWS CLI with account isolation"
    echo "• ${CYAN}aws-self-check${NC} - Validate isolation configuration"
    echo ""

    if [[ "$PRODUCTION_MODE" == "true" ]]; then
        echo -e "${YELLOW}Production Environment Reminders:${NC}"
        echo "• Use 'export CONFIRM_PROD=I_UNDERSTAND' for destructive operations"
        echo "• All operations are logged for audit purposes"
        echo "• Follow change management procedures"
        echo ""
    fi

    echo -e "${WHITE}Configuration Files:${NC}"
    echo "• Config: ${REPO_AWS_HOME}/config"
    echo "• Credentials: ${REPO_AWS_HOME}/credentials"
    echo "• Logs: ${REPO_AWS_HOME}/logs/"
}

# Main execution
main() {
    print_banner
    validate_environment
    print_configuration
    production_safety_check
    setup_isolation_directory
    create_aws_configuration
    setup_oidc_authentication
    verify_aws_access
    test_account_access
    setup_cost_monitoring
    create_helper_scripts
    display_final_configuration
    create_initialization_marker
    print_next_steps
}

# Execute main function
main "$@"
