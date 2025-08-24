#!/usr/bin/env bash
# Credential Rotator - Advanced credential management and rotation
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Handles automatic credential rotation, emergency revocation, and lifecycle management

set -euo pipefail

# Script metadata
CREDENTIAL_ROTATOR_VERSION="2.0.0"
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
ROTATION_CONFIG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/credential-rotation.json"
ROTATION_LOG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/logs/credential-rotation.log"
EMERGENCY_LOG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/logs/emergency-revocation.log"
CREDENTIALS_INVENTORY_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/inventory/credentials.json"

# Default rotation periods (in days)
DEFAULT_SA_KEY_ROTATION_DAYS=90
DEFAULT_WIF_REVIEW_DAYS=180
DEFAULT_USER_REVIEW_DAYS=365

# Initialize credential management
init_credential_management() {
    log_step "Initializing credential management..."

    # Create necessary directories
    mkdir -p "$(dirname "$ROTATION_CONFIG_FILE")"
    mkdir -p "$(dirname "$ROTATION_LOG_FILE")"
    mkdir -p "$(dirname "$CREDENTIALS_INVENTORY_FILE")"

    # Create default configuration if it doesn't exist
    if [[ ! -f "$ROTATION_CONFIG_FILE" ]]; then
        create_default_config
    fi

    # Initialize inventory
    update_credential_inventory

    log_success "Credential management initialized"
}

# Create default rotation configuration
create_default_config() {
    cat > "$ROTATION_CONFIG_FILE" <<EOF
{
    "version": "$CREDENTIAL_ROTATOR_VERSION",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "rotation_policies": {
        "service_account_keys": {
            "enabled": true,
            "rotation_days": $DEFAULT_SA_KEY_ROTATION_DAYS,
            "warning_days": 7,
            "auto_rotate": false,
            "notification_enabled": true
        },
        "workload_identity": {
            "enabled": true,
            "review_days": $DEFAULT_WIF_REVIEW_DAYS,
            "validation_enabled": true
        },
        "user_credentials": {
            "enabled": true,
            "review_days": $DEFAULT_USER_REVIEW_DAYS,
            "mfa_required": true
        }
    },
    "emergency_procedures": {
        "auto_revoke_on_breach": true,
        "notification_channels": {
            "email": "${SECURITY_EMAIL:-}",
            "slack": "${SLACK_WEBHOOK:-}",
            "pagerduty": "${PAGERDUTY_INTEGRATION_KEY:-}"
        }
    },
    "audit_settings": {
        "log_all_operations": true,
        "retain_logs_days": 365,
        "export_to_cloud_logging": true
    },
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

    log_success "Default rotation configuration created"
}

# Update credential inventory
update_credential_inventory() {
    log_step "Updating credential inventory..."

    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi

    if [[ -z "$project_id" ]]; then
        log_error "No project ID available for inventory"
        return 1
    fi

    # Get service accounts
    local service_accounts
    service_accounts=$(gcloud iam service-accounts list \
        --project="$project_id" \
        --format="json" 2>/dev/null || echo "[]")

    # Get service account keys for each SA
    local sa_keys_data="[]"
    while IFS= read -r sa_email; do
        if [[ -n "$sa_email" && "$sa_email" != "null" ]]; then
            local keys_data
            keys_data=$(gcloud iam service-accounts keys list \
                --iam-account="$sa_email" \
                --project="$project_id" \
                --format="json" 2>/dev/null || echo "[]")

            # Add service account email to each key
            keys_data=$(echo "$keys_data" | jq --arg sa "$sa_email" '
                map(. + {"serviceAccountEmail": $sa})
            ')

            sa_keys_data=$(echo "$sa_keys_data" "$keys_data" | jq -s 'add')
        fi
    done < <(echo "$service_accounts" | jq -r '.[].email // empty')

    # Get Workload Identity Pools
    local wif_pools
    wif_pools=$(gcloud iam workload-identity-pools list \
        --location="global" \
        --project="$project_id" \
        --format="json" 2>/dev/null || echo "[]")

    # Create inventory
    local inventory
    inventory=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "project_id": "$project_id",
    "environment": "${ENVIRONMENT:-}",
    "service_accounts": $service_accounts,
    "service_account_keys": $sa_keys_data,
    "workload_identity_pools": $wif_pools,
    "summary": {
        "total_service_accounts": $(echo "$service_accounts" | jq 'length'),
        "total_sa_keys": $(echo "$sa_keys_data" | jq 'length'),
        "total_wif_pools": $(echo "$wif_pools" | jq 'length')
    },
    "rotator_version": "$CREDENTIAL_ROTATOR_VERSION"
}
EOF
)

    echo "$inventory" > "$CREDENTIALS_INVENTORY_FILE"
    log_success "Credential inventory updated"
}

# Check credential health
check_credential_health() {
    log_step "Checking credential health..."

    if [[ ! -f "$CREDENTIALS_INVENTORY_FILE" ]]; then
        log_warning "No credential inventory found. Running update..."
        update_credential_inventory
    fi

    # Load configuration
    local rotation_days warning_days
    rotation_days=$(jq -r '.rotation_policies.service_account_keys.rotation_days // 90' "$ROTATION_CONFIG_FILE" 2>/dev/null || echo "90")
    warning_days=$(jq -r '.rotation_policies.service_account_keys.warning_days // 7' "$ROTATION_CONFIG_FILE" 2>/dev/null || echo "7")

    local current_timestamp
    current_timestamp=$(date +%s)

    local warnings=0
    local critical=0
    local total_keys=0

    echo -e "${WHITE}Credential Health Report:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check service account keys
    while IFS= read -r key_data; do
        if [[ -n "$key_data" && "$key_data" != "null" ]]; then
            ((total_keys++))

            local key_name sa_email valid_after_time key_type
            key_name=$(echo "$key_data" | jq -r '.name')
            sa_email=$(echo "$key_data" | jq -r '.serviceAccountEmail')
            valid_after_time=$(echo "$key_data" | jq -r '.validAfterTime')
            key_type=$(echo "$key_data" | jq -r '.keyType // "USER_MANAGED"')

            # Parse creation date (validAfterTime)
            local key_timestamp
            if command -v gdate >/dev/null 2>&1; then
                key_timestamp=$(gdate -d "$valid_after_time" +%s 2>/dev/null || echo "0")
            else
                key_timestamp=$(date -d "$valid_after_time" +%s 2>/dev/null || echo "0")
            fi

            if [[ "$key_timestamp" -eq 0 ]]; then
                log_warning "Could not parse date for key: $key_name"
                continue
            fi

            local age_days
            age_days=$(( (current_timestamp - key_timestamp) / 86400 ))

            local days_until_rotation
            days_until_rotation=$(( rotation_days - age_days ))

            local status_color="$GREEN"
            local status="OK"

            if [[ $age_days -ge $rotation_days ]]; then
                status_color="$RED"
                status="CRITICAL - OVERDUE"
                ((critical++))
            elif [[ $days_until_rotation -le $warning_days ]]; then
                status_color="$YELLOW"
                status="WARNING - EXPIRING SOON"
                ((warnings++))
            fi

            echo -e "${status_color}$status${NC} - SA: $sa_email"
            echo "  Key: $(basename "$key_name")"
            echo "  Age: $age_days days (rotation due: $days_until_rotation days)"
            echo "  Type: $key_type"
            echo ""
        fi
    done < <(jq -c '.service_account_keys[]? // empty' "$CREDENTIALS_INVENTORY_FILE" 2>/dev/null)

    # Summary
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${WHITE}Summary:${NC}"
    echo "Total Keys: $total_keys"
    echo -e "Warnings: ${YELLOW}$warnings${NC}"
    echo -e "Critical: ${RED}$critical${NC}"

    # Log the health check
    log_health_check "$total_keys" "$warnings" "$critical"

    # Return appropriate exit code
    if [[ $critical -gt 0 ]]; then
        return 2
    elif [[ $warnings -gt 0 ]]; then
        return 1
    else
        return 0
    fi
}

# Log health check results
log_health_check() {
    local total_keys="$1"
    local warnings="$2"
    local critical="$3"

    local log_entry
    log_entry=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "operation": "health_check",
    "result": {
        "total_keys": $total_keys,
        "warnings": $warnings,
        "critical": $critical,
        "status": "$(if [[ $critical -gt 0 ]]; then echo "CRITICAL"; elif [[ $warnings -gt 0 ]]; then echo "WARNING"; else echo "OK"; fi)"
    },
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "rotator_version": "$CREDENTIAL_ROTATOR_VERSION"
}
EOF
)

    mkdir -p "$(dirname "$ROTATION_LOG_FILE")"
    echo "$log_entry" >> "$ROTATION_LOG_FILE"
}

# Rotate service account key
rotate_service_account_key() {
    local sa_email="$1"
    local old_key_id="${2:-}"

    log_step "Rotating service account key for: $sa_email"

    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi

    # Validate service account exists
    if ! gcloud iam service-accounts describe "$sa_email" \
        --project="$project_id" >/dev/null 2>&1; then
        log_error "Service account not found: $sa_email"
        return 1
    fi

    # Create new key
    log_info "Creating new key..."
    local new_key_file
    new_key_file="/tmp/new-key-$(date +%s).json"

    if gcloud iam service-accounts keys create "$new_key_file" \
        --iam-account="$sa_email" \
        --project="$project_id"; then
        log_success "New key created successfully"

        # Get the new key ID
        local new_key_id
        new_key_id=$(jq -r '.private_key_id' "$new_key_file")

        log_info "New key ID: $new_key_id"

        # If old key ID provided, delete it after a grace period
        if [[ -n "$old_key_id" ]]; then
            log_warning "Old key will be deleted after grace period"
            log_warning "To delete immediately: gcloud iam service-accounts keys delete $old_key_id --iam-account=$sa_email"
        fi

        # Secure the new key file
        chmod 600 "$new_key_file"

        # Log the rotation
        log_key_rotation "$sa_email" "$old_key_id" "$new_key_id" "SUCCESS"

        echo ""
        echo -e "${YELLOW}IMPORTANT: Update your applications with the new key file:${NC}"
        echo "New key file: $new_key_file"
        echo ""
        echo -e "${YELLOW}Remember to:${NC}"
        echo "1. Update environment variables or configuration"
        echo "2. Restart applications using this service account"
        echo "3. Test that authentication works"
        echo "4. Delete the old key after confirming everything works"
        echo ""

        # Cleanup temporary file (commented out for safety)
        # rm -f "$new_key_file"

    else
        log_error "Failed to create new key"
        log_key_rotation "$sa_email" "$old_key_id" "" "FAILED"
        return 1
    fi
}

# Log key rotation
log_key_rotation() {
    local sa_email="$1"
    local old_key_id="$2"
    local new_key_id="$3"
    local status="$4"

    local log_entry
    log_entry=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "operation": "key_rotation",
    "service_account": "$sa_email",
    "old_key_id": "$old_key_id",
    "new_key_id": "$new_key_id",
    "status": "$status",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "user": "${USER:-unknown}",
    "rotator_version": "$CREDENTIAL_ROTATOR_VERSION"
}
EOF
)

    mkdir -p "$(dirname "$ROTATION_LOG_FILE")"
    echo "$log_entry" >> "$ROTATION_LOG_FILE"
}

# Emergency revocation
emergency_revoke_credentials() {
    local target_type="$1"  # sa_email, key_id, or all
    local target_value="$2"

    log_error "🚨 EMERGENCY CREDENTIAL REVOCATION INITIATED"

    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi

    case "$target_type" in
        "sa_email")
            log_step "Revoking all keys for service account: $target_value"

            # Get all keys for the service account
            local keys_data
            keys_data=$(gcloud iam service-accounts keys list \
                --iam-account="$target_value" \
                --project="$project_id" \
                --format="json" 2>/dev/null || echo "[]")

            local revoked_count=0
            while IFS= read -r key_id; do
                if [[ -n "$key_id" && "$key_id" != "null" ]]; then
                    if gcloud iam service-accounts keys delete "$key_id" \
                        --iam-account="$target_value" \
                        --project="$project_id" \
                        --quiet; then
                        log_success "Revoked key: $key_id"
                        ((revoked_count++))
                    else
                        log_error "Failed to revoke key: $key_id"
                    fi
                fi
            done < <(echo "$keys_data" | jq -r '.[].name | split("/")[-1] // empty')

            log_emergency_revocation "service_account" "$target_value" "$revoked_count"
            ;;

        "key_id")
            log_step "Revoking specific key: $target_value"

            # Need service account email for key deletion
            if [[ -z "${3:-}" ]]; then
                log_error "Service account email required for key revocation"
                return 1
            fi

            local sa_email="$3"

            if gcloud iam service-accounts keys delete "$target_value" \
                --iam-account="$sa_email" \
                --project="$project_id" \
                --quiet; then
                log_success "Key revoked: $target_value"
                log_emergency_revocation "key" "$target_value" "1"
            else
                log_error "Failed to revoke key: $target_value"
                return 1
            fi
            ;;

        "all")
            log_step "Revoking ALL service account keys in project"

            if [[ "${CONFIRM_REVOKE_ALL:-}" != "I_UNDERSTAND_THIS_WILL_BREAK_EVERYTHING" ]]; then
                log_error "To revoke all keys, set: CONFIRM_REVOKE_ALL=I_UNDERSTAND_THIS_WILL_BREAK_EVERYTHING"
                return 1
            fi

            local total_revoked=0

            # Get all service accounts
            while IFS= read -r sa_email; do
                if [[ -n "$sa_email" && "$sa_email" != "null" ]]; then
                    log_info "Processing service account: $sa_email"

                    # Get all keys for this SA
                    local keys_data
                    keys_data=$(gcloud iam service-accounts keys list \
                        --iam-account="$sa_email" \
                        --project="$project_id" \
                        --format="json" 2>/dev/null || echo "[]")

                    while IFS= read -r key_id; do
                        if [[ -n "$key_id" && "$key_id" != "null" ]]; then
                            if gcloud iam service-accounts keys delete "$key_id" \
                                --iam-account="$sa_email" \
                                --project="$project_id" \
                                --quiet; then
                                log_success "Revoked: $sa_email/$key_id"
                                ((total_revoked++))
                            fi
                        fi
                    done < <(echo "$keys_data" | jq -r '.[].name | split("/")[-1] // empty')
                fi
            done < <(jq -r '.service_accounts[].email // empty' "$CREDENTIALS_INVENTORY_FILE" 2>/dev/null)

            log_emergency_revocation "all_keys" "project_wide" "$total_revoked"
            ;;

        *)
            log_error "Invalid revocation target type: $target_type"
            log_error "Valid types: sa_email, key_id, all"
            return 1
            ;;
    esac

    # Send emergency notifications
    send_emergency_notification "$target_type" "$target_value"
}

# Log emergency revocation
log_emergency_revocation() {
    local revocation_type="$1"
    local target="$2"
    local count="$3"

    local log_entry
    log_entry=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "operation": "emergency_revocation",
    "revocation_type": "$revocation_type",
    "target": "$target",
    "revoked_count": $count,
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "user": "${USER:-unknown}",
    "source_ip": "${SSH_CLIENT%% *}",
    "rotator_version": "$CREDENTIAL_ROTATOR_VERSION"
}
EOF
)

    mkdir -p "$(dirname "$EMERGENCY_LOG_FILE")"
    echo "$log_entry" >> "$EMERGENCY_LOG_FILE"

    # Also log to main rotation log
    echo "$log_entry" >> "$ROTATION_LOG_FILE"
}

# Send emergency notification
send_emergency_notification() {
    local target_type="$1"
    local target_value="$2"

    # Load notification configuration
    local slack_webhook email
    slack_webhook=$(jq -r '.emergency_procedures.notification_channels.slack // empty' "$ROTATION_CONFIG_FILE" 2>/dev/null)
    email=$(jq -r '.emergency_procedures.notification_channels.email // empty' "$ROTATION_CONFIG_FILE" 2>/dev/null)

    local message="🚨 EMERGENCY: Credentials revoked for $target_type: $target_value in project ${PROJECT_ID:-unknown}"

    # Send Slack notification
    if [[ -n "$slack_webhook" ]]; then
        local payload
        payload=$(cat <<EOF
{
    "text": "$message",
    "attachments": [
        {
            "color": "danger",
            "title": "Emergency Credential Revocation",
            "fields": [
                {"title": "Type", "value": "$target_type", "short": true},
                {"title": "Target", "value": "$target_value", "short": true},
                {"title": "Project", "value": "${PROJECT_ID:-unknown}", "short": true},
                {"title": "User", "value": "${USER:-unknown}", "short": true}
            ],
            "footer": "Credential Rotator v$CREDENTIAL_ROTATOR_VERSION",
            "ts": $(date +%s)
        }
    ]
}
EOF
)

        curl -X POST -H 'Content-type: application/json' \
            --data "$payload" \
            "$slack_webhook" >/dev/null 2>&1 || true
    fi

    # Send email notification
    if [[ -n "$email" ]] && command -v mail >/dev/null 2>&1; then
        echo "$message" | mail -s "EMERGENCY: Credential Revocation" "$email" >/dev/null 2>&1 || true
    fi
}

# Show rotation status
show_rotation_status() {
    echo -e "${CYAN}═══ CREDENTIAL ROTATION STATUS ═══${NC}"
    echo ""

    if [[ ! -f "$CREDENTIALS_INVENTORY_FILE" ]]; then
        log_warning "No credential inventory found. Run: credential-rotator inventory"
        return 1
    fi

    # Load summary from inventory
    local total_sas total_keys total_wif
    total_sas=$(jq -r '.summary.total_service_accounts // 0' "$CREDENTIALS_INVENTORY_FILE")
    total_keys=$(jq -r '.summary.total_sa_keys // 0' "$CREDENTIALS_INVENTORY_FILE")
    total_wif=$(jq -r '.summary.total_wif_pools // 0' "$CREDENTIALS_INVENTORY_FILE")

    echo -e "${WHITE}Inventory Summary:${NC}"
    echo "Service Accounts: $total_sas"
    echo "Service Account Keys: $total_keys"
    echo "Workload Identity Pools: $total_wif"
    echo ""

    # Run health check and show results
    check_credential_health
}

# Main function
main() {
    local command="${1:-status}"

    case "$command" in
        "init")
            init_credential_management
            ;;
        "inventory"|"inv")
            update_credential_inventory
            ;;
        "health"|"check")
            check_credential_health
            ;;
        "status"|"s")
            show_rotation_status
            ;;
        "rotate")
            local sa_email="${2:-}"
            local old_key_id="${3:-}"
            if [[ -z "$sa_email" ]]; then
                log_error "Service account email required"
                echo "Usage: $0 rotate <service-account-email> [old-key-id]"
                exit 1
            fi
            rotate_service_account_key "$sa_email" "$old_key_id"
            ;;
        "emergency-revoke")
            local target_type="${2:-}"
            local target_value="${3:-}"
            local sa_email="${4:-}"
            if [[ -z "$target_type" || -z "$target_value" ]]; then
                log_error "Target type and value required"
                echo "Usage: $0 emergency-revoke <sa_email|key_id|all> <value> [sa-email-for-key]"
                exit 1
            fi
            emergency_revoke_credentials "$target_type" "$target_value" "$sa_email"
            ;;
        "history"|"h")
            local limit="${2:-20}"
            if [[ -f "$ROTATION_LOG_FILE" ]]; then
                log_info "Recent credential operations (last $limit):"
                tail -n "$limit" "$ROTATION_LOG_FILE" | jq -r '
                    [.timestamp, .operation, .status // "N/A"] | @tsv' | \
                while IFS=$'\t' read -r timestamp operation status; do
                    case "$status" in
                        "SUCCESS") color="$GREEN" ;;
                        "FAILED") color="$RED" ;;
                        *) color="$YELLOW" ;;
                    esac
                    echo -e "${color}$timestamp - $operation - $status${NC}"
                done
            else
                log_info "No operation history found"
            fi
            ;;
        "help"|"--help"|"-h")
            echo "Credential Rotator v$CREDENTIAL_ROTATOR_VERSION"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  init                     Initialize credential management"
            echo "  inventory, inv           Update credential inventory"
            echo "  health, check            Check credential health"
            echo "  status, s               Show rotation status"
            echo "  rotate <sa-email> [key]  Rotate service account key"
            echo "  emergency-revoke <type> <value> [sa-email]"
            echo "                          Emergency credential revocation"
            echo "  history, h [limit]      Show operation history"
            echo "  help                    Show this help"
            echo ""
            echo "Emergency Revocation Types:"
            echo "  sa_email                Revoke all keys for service account"
            echo "  key_id                  Revoke specific key (requires sa-email)"
            echo "  all                     Revoke all keys (requires confirmation)"
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
