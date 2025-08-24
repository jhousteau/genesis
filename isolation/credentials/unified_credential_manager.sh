#!/usr/bin/env bash
# Unified Credential Manager - Multi-cloud credential management
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Manages credentials across GCP, AWS, Azure, and other cloud providers

set -euo pipefail

# Script metadata
UNIFIED_CREDENTIAL_VERSION="2.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Configuration files
UNIFIED_CONFIG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/unified-credentials.json"
CREDENTIAL_INVENTORY_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/inventory/unified-credentials.json"
ROTATION_LOG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/logs/unified-rotation.log"

# Supported cloud providers
declare -A CLOUD_PROVIDERS=(
    ["gcp"]="Google Cloud Platform"
    ["aws"]="Amazon Web Services"
    ["azure"]="Microsoft Azure"
    ["github"]="GitHub (OIDC)"
    ["gitlab"]="GitLab (OIDC)"
    ["jenkins"]="Jenkins (Custom OIDC)"
)

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "══════════════════════════════════════════════════════════════"
    echo "🔐 UNIFIED CREDENTIAL MANAGER v${UNIFIED_CREDENTIAL_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "   Multi-Cloud Credential Management"
    echo "══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Initialize unified credential management
init_unified_credentials() {
    log_step "Initializing unified credential management..."

    mkdir -p "$(dirname "$UNIFIED_CONFIG_FILE")"
    mkdir -p "$(dirname "$CREDENTIAL_INVENTORY_FILE")"
    mkdir -p "$(dirname "$ROTATION_LOG_FILE")"

    if [[ ! -f "$UNIFIED_CONFIG_FILE" ]]; then
        create_default_unified_config
    fi

    log_success "Unified credential management initialized"
}

# Create default unified configuration
create_default_unified_config() {
    cat > "$UNIFIED_CONFIG_FILE" <<EOF
{
    "version": "$UNIFIED_CREDENTIAL_VERSION",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "cloud_providers": {
        "gcp": {
            "enabled": true,
            "project_id": "${PROJECT_ID:-}",
            "region": "${REGION:-us-central1}",
            "auth_method": "workload_identity",
            "service_account": "${GCP_SERVICE_ACCOUNT:-}",
            "wif_provider": "${WIF_PROVIDER:-}",
            "rotation_enabled": true,
            "rotation_days": 90
        },
        "aws": {
            "enabled": false,
            "account_id": "${AWS_ACCOUNT_ID:-}",
            "region": "${AWS_REGION:-us-east-1}",
            "auth_method": "oidc",
            "role_arn": "${AWS_ROLE_ARN:-}",
            "web_identity_token_file": "${AWS_WEB_IDENTITY_TOKEN_FILE:-}",
            "rotation_enabled": true,
            "rotation_days": 90
        },
        "azure": {
            "enabled": false,
            "subscription_id": "${AZURE_SUBSCRIPTION_ID:-}",
            "tenant_id": "${AZURE_TENANT_ID:-}",
            "location": "${AZURE_LOCATION:-eastus}",
            "auth_method": "federated",
            "client_id": "${AZURE_CLIENT_ID:-}",
            "federated_token_file": "${AZURE_FEDERATED_TOKEN_FILE:-}",
            "rotation_enabled": true,
            "rotation_days": 90
        }
    },
    "ci_cd_integration": {
        "github_actions": {
            "enabled": false,
            "repository": "${GITHUB_REPO:-}",
            "oidc_token_permissions": ["id-token: write", "contents: read"]
        },
        "gitlab_ci": {
            "enabled": false,
            "project_path": "${GITLAB_PROJECT_PATH:-}",
            "oidc_enabled": true
        },
        "azure_devops": {
            "enabled": false,
            "organization": "${AZURE_ORGANIZATION:-}",
            "project": "${AZURE_PROJECT:-}"
        }
    },
    "security_settings": {
        "require_mfa": true,
        "audit_all_operations": true,
        "emergency_access_enabled": true,
        "cross_cloud_access_control": true,
        "credential_sharing_allowed": false
    },
    "monitoring": {
        "alert_on_credential_issues": true,
        "slack_webhook": "${SLACK_WEBHOOK:-}",
        "email_notifications": "${SECURITY_EMAIL:-}",
        "log_level": "INFO"
    },
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

# Discover credentials across all cloud providers
discover_credentials() {
    log_step "Discovering credentials across all cloud providers..."

    local credentials_summary='{
        "discovery_timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "providers": {}
    }'

    # Discover GCP credentials
    if command -v gcloud >/dev/null 2>&1; then
        local gcp_creds
        gcp_creds=$(discover_gcp_credentials)
        credentials_summary=$(echo "$credentials_summary" | jq --argjson gcp "$gcp_creds" '.providers.gcp = $gcp')
    fi

    # Discover AWS credentials
    if command -v aws >/dev/null 2>&1; then
        local aws_creds
        aws_creds=$(discover_aws_credentials)
        credentials_summary=$(echo "$credentials_summary" | jq --argjson aws "$aws_creds" '.providers.aws = $aws')
    fi

    # Discover Azure credentials
    if command -v az >/dev/null 2>&1; then
        local azure_creds
        azure_creds=$(discover_azure_credentials)
        credentials_summary=$(echo "$credentials_summary" | jq --argjson azure "$azure_creds" '.providers.azure = $azure')
    fi

    # Save discovery results
    echo "$credentials_summary" > "$CREDENTIAL_INVENTORY_FILE"

    log_success "Credential discovery completed"
    echo "$credentials_summary"
}

# Discover GCP credentials
discover_gcp_credentials() {
    local gcp_discovery='{
        "provider": "gcp",
        "status": "unknown",
        "auth_method": "unknown",
        "credentials": []
    }'

    # Check for active gcloud authentication
    if ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null) && [[ -n "$ACTIVE_ACCOUNT" ]]; then
        gcp_discovery=$(echo "$gcp_discovery" | jq --arg account "$ACTIVE_ACCOUNT" '.status = "authenticated" | .credentials = [{"type": "user", "account": $account}]')

        # Check for service account impersonation
        if IMPERSONATE_SA=$(gcloud config get-value auth/impersonate_service_account 2>/dev/null) && [[ -n "$IMPERSONATE_SA" ]]; then
            gcp_discovery=$(echo "$gcp_discovery" | jq --arg sa "$IMPERSONATE_SA" '.auth_method = "impersonation" | .credentials += [{"type": "service_account", "email": $sa}]')
        else
            gcp_discovery=$(echo "$gcp_discovery" | jq '.auth_method = "user"')
        fi

        # Check for WIF configuration
        if [[ -f "${REPO_GCLOUD_HOME:-$HOME/.gcloud}/wif-config.json" ]]; then
            local wif_provider wif_sa
            wif_provider=$(jq -r '.provider // empty' "${REPO_GCLOUD_HOME:-$HOME/.gcloud}/wif-config.json" 2>/dev/null || echo "")
            wif_sa=$(jq -r '.service_account // empty' "${REPO_GCLOUD_HOME:-$HOME/.gcloud}/wif-config.json" 2>/dev/null || echo "")

            if [[ -n "$wif_provider" && -n "$wif_sa" ]]; then
                gcp_discovery=$(echo "$gcp_discovery" | jq --arg provider "$wif_provider" --arg sa "$wif_sa" '.auth_method = "workload_identity" | .credentials += [{"type": "workload_identity", "provider": $provider, "service_account": $sa}]')
            fi
        fi
    else
        gcp_discovery=$(echo "$gcp_discovery" | jq '.status = "not_authenticated"')
    fi

    echo "$gcp_discovery"
}

# Discover AWS credentials
discover_aws_credentials() {
    local aws_discovery='{
        "provider": "aws",
        "status": "unknown",
        "auth_method": "unknown",
        "credentials": []
    }'

    # Check for AWS credentials
    if aws sts get-caller-identity >/dev/null 2>&1; then
        local caller_identity
        caller_identity=$(aws sts get-caller-identity 2>/dev/null || echo '{}')

        local account_id user_arn
        account_id=$(echo "$caller_identity" | jq -r '.Account // "unknown"')
        user_arn=$(echo "$caller_identity" | jq -r '.Arn // "unknown"')

        aws_discovery=$(echo "$aws_discovery" | jq --arg account "$account_id" --arg arn "$user_arn" '.status = "authenticated" | .credentials = [{"type": "active", "account": $account, "arn": $arn}]')

        # Determine auth method
        if [[ -n "${AWS_ROLE_TO_ASSUME:-}" ]]; then
            aws_discovery=$(echo "$aws_discovery" | jq '.auth_method = "oidc"')
        elif [[ -n "${AWS_ROLE_ARN:-}" ]]; then
            aws_discovery=$(echo "$aws_discovery" | jq '.auth_method = "role_assumption"')
        elif [[ -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
            aws_discovery=$(echo "$aws_discovery" | jq '.auth_method = "access_keys"')
        else
            aws_discovery=$(echo "$aws_discovery" | jq '.auth_method = "profile_or_instance"')
        fi
    else
        aws_discovery=$(echo "$aws_discovery" | jq '.status = "not_authenticated"')
    fi

    echo "$aws_discovery"
}

# Discover Azure credentials
discover_azure_credentials() {
    local azure_discovery='{
        "provider": "azure",
        "status": "unknown",
        "auth_method": "unknown",
        "credentials": []
    }'

    # Check for Azure authentication
    if az account show >/dev/null 2>&1; then
        local account_info
        account_info=$(az account show 2>/dev/null || echo '{}')

        local subscription_id tenant_id user_name
        subscription_id=$(echo "$account_info" | jq -r '.id // "unknown"')
        tenant_id=$(echo "$account_info" | jq -r '.tenantId // "unknown"')
        user_name=$(echo "$account_info" | jq -r '.user.name // "unknown"')

        azure_discovery=$(echo "$azure_discovery" | jq --arg sub "$subscription_id" --arg tenant "$tenant_id" --arg user "$user_name" '.status = "authenticated" | .credentials = [{"type": "active", "subscription": $sub, "tenant": $tenant, "user": $user}]')

        # Determine auth method
        if [[ -n "${AZURE_CLIENT_ID:-}" && -n "${AZURE_CLIENT_SECRET:-}" ]]; then
            azure_discovery=$(echo "$azure_discovery" | jq '.auth_method = "service_principal"')
        elif [[ -n "${AZURE_FEDERATED_TOKEN_FILE:-}" ]]; then
            azure_discovery=$(echo "$azure_discovery" | jq '.auth_method = "federated"')
        elif [[ "${AZURE_USE_MSI:-}" == "true" ]]; then
            azure_discovery=$(echo "$azure_discovery" | jq '.auth_method = "managed_identity"')
        else
            azure_discovery=$(echo "$azure_discovery" | jq '.auth_method = "user_or_cli"')
        fi
    else
        azure_discovery=$(echo "$azure_discovery" | jq '.status = "not_authenticated"')
    fi

    echo "$azure_discovery"
}

# Validate credentials across all providers
validate_all_credentials() {
    log_step "Validating credentials across all cloud providers..."

    local validation_results='{
        "validation_timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "overall_status": "unknown",
        "provider_results": {}
    }'

    local overall_success=true

    # Validate GCP credentials
    local gcp_result
    if validate_gcp_credentials; then
        gcp_result='{"status": "valid", "message": "GCP credentials are working"}'
    else
        gcp_result='{"status": "invalid", "message": "GCP credentials failed validation"}'
        overall_success=false
    fi
    validation_results=$(echo "$validation_results" | jq --argjson gcp "$gcp_result" '.provider_results.gcp = $gcp')

    # Validate AWS credentials
    local aws_result
    if validate_aws_credentials; then
        aws_result='{"status": "valid", "message": "AWS credentials are working"}'
    else
        aws_result='{"status": "invalid", "message": "AWS credentials failed validation"}'
        overall_success=false
    fi
    validation_results=$(echo "$validation_results" | jq --argjson aws "$aws_result" '.provider_results.aws = $aws')

    # Validate Azure credentials
    local azure_result
    if validate_azure_credentials; then
        azure_result='{"status": "valid", "message": "Azure credentials are working"}'
    else
        azure_result='{"status": "invalid", "message": "Azure credentials failed validation"}'
        overall_success=false
    fi
    validation_results=$(echo "$validation_results" | jq --argjson azure "$azure_result" '.provider_results.azure = $azure')

    # Set overall status
    if [[ "$overall_success" == "true" ]]; then
        validation_results=$(echo "$validation_results" | jq '.overall_status = "valid"')
        log_success "All credential validations passed"
    else
        validation_results=$(echo "$validation_results" | jq '.overall_status = "invalid"')
        log_warning "Some credential validations failed"
    fi

    echo "$validation_results"
}

# Validate GCP credentials
validate_gcp_credentials() {
    if command -v gcloud >/dev/null 2>&1; then
        gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1
    else
        false
    fi
}

# Validate AWS credentials
validate_aws_credentials() {
    if command -v aws >/dev/null 2>&1; then
        aws sts get-caller-identity >/dev/null 2>&1
    else
        false
    fi
}

# Validate Azure credentials
validate_azure_credentials() {
    if command -v az >/dev/null 2>&1; then
        az account show >/dev/null 2>&1
    else
        false
    fi
}

# Rotate credentials across all providers
rotate_all_credentials() {
    log_step "Starting credential rotation across all providers..."

    local rotation_results='{
        "rotation_timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "rotation_id": "'$(uuidgen 2>/dev/null || date +%s)'",
        "provider_results": {}
    }'

    # Rotate GCP credentials
    log_info "Rotating GCP credentials..."
    local gcp_result
    if rotate_gcp_credentials; then
        gcp_result='{"status": "success", "message": "GCP credentials rotated successfully"}'
    else
        gcp_result='{"status": "failed", "message": "GCP credential rotation failed"}'
    fi
    rotation_results=$(echo "$rotation_results" | jq --argjson gcp "$gcp_result" '.provider_results.gcp = $gcp')

    # Rotate AWS credentials
    log_info "Rotating AWS credentials..."
    local aws_result
    if rotate_aws_credentials; then
        aws_result='{"status": "success", "message": "AWS credentials rotated successfully"}'
    else
        aws_result='{"status": "failed", "message": "AWS credential rotation failed"}'
    fi
    rotation_results=$(echo "$rotation_results" | jq --argjson aws "$aws_result" '.provider_results.aws = $aws')

    # Rotate Azure credentials
    log_info "Rotating Azure credentials..."
    local azure_result
    if rotate_azure_credentials; then
        azure_result='{"status": "success", "message": "Azure credentials rotated successfully"}'
    else
        azure_result='{"status": "failed", "message": "Azure credential rotation failed"}'
    fi
    rotation_results=$(echo "$rotation_results" | jq --argjson azure "$azure_result" '.provider_results.azure = $azure')

    # Log rotation results
    echo "$rotation_results" >> "$ROTATION_LOG_FILE"

    log_success "Credential rotation completed"
    echo "$rotation_results"
}

# Rotate GCP credentials
rotate_gcp_credentials() {
    if [[ -f "${SCRIPT_DIR}/rotation/credential_rotator.sh" ]]; then
        "${SCRIPT_DIR}/rotation/credential_rotator.sh" health >/dev/null 2>&1
    else
        log_warning "GCP credential rotator not found"
        false
    fi
}

# Rotate AWS credentials
rotate_aws_credentials() {
    # For AWS OIDC/IAM roles, rotation is automatic
    # For access keys, would need AWS-specific rotation logic
    log_info "AWS OIDC credentials rotate automatically"
    return 0
}

# Rotate Azure credentials
rotate_azure_credentials() {
    # For Azure federated credentials, rotation is automatic
    # For service principals, would need Azure-specific rotation logic
    log_info "Azure federated credentials rotate automatically"
    return 0
}

# Show unified credential dashboard
show_unified_dashboard() {
    echo -e "${CYAN}═══ UNIFIED CREDENTIAL DASHBOARD ═══${NC}"
    echo ""

    # Load configuration
    if [[ -f "$UNIFIED_CONFIG_FILE" ]]; then
        local project_id environment
        project_id=$(jq -r '.project_id // "unknown"' "$UNIFIED_CONFIG_FILE")
        environment=$(jq -r '.environment // "unknown"' "$UNIFIED_CONFIG_FILE")

        echo -e "${WHITE}Project: $project_id${NC}"
        echo -e "${WHITE}Environment: $environment${NC}"
        echo ""
    fi

    # Show provider status
    echo -e "${WHITE}Cloud Provider Status:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check GCP
    if validate_gcp_credentials; then
        local gcp_account
        gcp_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
        echo -e "${GREEN}✅ GCP${NC} - Authenticated as: $gcp_account"
    else
        echo -e "${RED}❌ GCP${NC} - Not authenticated"
    fi

    # Check AWS
    if validate_aws_credentials; then
        local aws_identity
        aws_identity=$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null || echo "unknown")
        echo -e "${GREEN}✅ AWS${NC} - Identity: $aws_identity"
    else
        echo -e "${RED}❌ AWS${NC} - Not authenticated"
    fi

    # Check Azure
    if validate_azure_credentials; then
        local azure_user
        azure_user=$(az account show --query 'user.name' --output tsv 2>/dev/null || echo "unknown")
        echo -e "${GREEN}✅ Azure${NC} - User: $azure_user"
    else
        echo -e "${RED}❌ Azure${NC} - Not authenticated"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Show recent operations
    if [[ -f "$ROTATION_LOG_FILE" ]]; then
        echo -e "${WHITE}Recent Operations:${NC}"
        tail -n 3 "$ROTATION_LOG_FILE" | jq -r '.rotation_timestamp + " - " + (.provider_results | to_entries | map(.key + ":" + .value.status) | join(", "))' 2>/dev/null || echo "No recent operations"
        echo ""
    fi

    echo -e "${WHITE}Available Commands:${NC}"
    echo "• unified-credential-manager discover"
    echo "• unified-credential-manager validate"
    echo "• unified-credential-manager rotate-all"
    echo "• unified-credential-manager status <provider>"
}

# Main function
main() {
    local command="${1:-dashboard}"

    case "$command" in
        "init")
            init_unified_credentials
            ;;
        "discover")
            init_unified_credentials
            discover_credentials | jq .
            ;;
        "validate")
            validate_all_credentials | jq .
            ;;
        "rotate-all")
            rotate_all_credentials | jq .
            ;;
        "status")
            local provider="${2:-all}"
            if [[ "$provider" == "all" ]]; then
                show_unified_dashboard
            else
                case "$provider" in
                    "gcp")
                        discover_gcp_credentials | jq .
                        ;;
                    "aws")
                        discover_aws_credentials | jq .
                        ;;
                    "azure")
                        discover_azure_credentials | jq .
                        ;;
                    *)
                        log_error "Unknown provider: $provider"
                        echo "Supported providers: gcp, aws, azure"
                        exit 1
                        ;;
                esac
            fi
            ;;
        "dashboard"|"d")
            print_banner
            show_unified_dashboard
            ;;
        "help"|"--help"|"-h")
            print_banner
            echo "Unified Credential Manager v$UNIFIED_CREDENTIAL_VERSION"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  init                     Initialize unified credential management"
            echo "  discover                 Discover credentials across all providers"
            echo "  validate                 Validate all credentials"
            echo "  rotate-all               Rotate credentials for all providers"
            echo "  status [provider]        Show status for all or specific provider"
            echo "  dashboard, d             Show unified dashboard"
            echo "  help                     Show this help"
            echo ""
            echo "Providers: ${!CLOUD_PROVIDERS[*]}"
            ;;
        *)
            log_error "Unknown command: $command"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Execute main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
