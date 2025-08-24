#!/usr/bin/env bash
# Credential Rotation System - Automated credential lifecycle management
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Handles automatic rotation of service account keys and other credentials

set -euo pipefail

# Script metadata
ROTATION_VERSION="2.0.0"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# Default rotation policies (in days)
readonly DEFAULT_KEY_MAX_AGE=90
readonly DEFAULT_WARNING_THRESHOLD=75
readonly DEFAULT_CRITICAL_THRESHOLD=85

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $*${NC}"; }
log_success() { echo -e "${GREEN}✅ $*${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $*${NC}"; }
log_error() { echo -e "${RED}❌ $*${NC}" >&2; }
log_step() { echo -e "${PURPLE}🔄 $*${NC}"; }
log_critical() { echo -e "${RED}🚨 CRITICAL: $*${NC}" >&2; }

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "════════════════════════════════════════════════════════"
    echo "🔄 CREDENTIAL ROTATION SYSTEM v${ROTATION_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Show usage
show_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  check                   - Check credential age and status"
    echo "  rotate <sa-name>        - Rotate specific service account"
    echo "  rotate-all              - Rotate all eligible credentials"
    echo "  schedule                - Set up automatic rotation schedule"
    echo "  policies                - Show/update rotation policies"
    echo "  emergency-rotate        - Emergency rotation (immediate)"
    echo ""
    echo "Options:"
    echo "  --project <project-id>  - GCP project ID (required)"
    echo "  --dry-run              - Show what would be done"
    echo "  --force                - Skip safety checks"
    echo "  --max-age <days>       - Maximum credential age (default: $DEFAULT_KEY_MAX_AGE)"
    echo "  --warn-threshold <days> - Warning threshold (default: $DEFAULT_WARNING_THRESHOLD)"
    echo "  --critical-threshold <days> - Critical threshold (default: $DEFAULT_CRITICAL_THRESHOLD)"
    echo "  --notification-email <email> - Email for rotation notifications"
    echo ""
    echo "Environment Variables:"
    echo "  PROJECT_ID             - GCP project ID"
    echo "  ENVIRONMENT            - Environment (dev/test/staging/prod)"
    echo "  ROTATION_POLICY        - Rotation policy file path"
    echo "  NOTIFICATION_WEBHOOK   - Slack/Teams webhook for notifications"
    echo ""
    echo "Examples:"
    echo "  $0 check --project my-project"
    echo "  $0 rotate deploy-sa --project my-project"
    echo "  $0 rotate-all --dry-run"
    echo "  $0 schedule --max-age 60"
}

# Parse command line arguments
parse_arguments() {
    COMMAND=""
    SA_NAME=""
    PROJECT_ID="${PROJECT_ID:-}"
    DRY_RUN=false
    FORCE=false
    MAX_AGE="$DEFAULT_KEY_MAX_AGE"
    WARN_THRESHOLD="$DEFAULT_WARNING_THRESHOLD"
    CRITICAL_THRESHOLD="$DEFAULT_CRITICAL_THRESHOLD"
    NOTIFICATION_EMAIL=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --project)
                PROJECT_ID="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --max-age)
                MAX_AGE="$2"
                shift 2
                ;;
            --warn-threshold)
                WARN_THRESHOLD="$2"
                shift 2
                ;;
            --critical-threshold)
                CRITICAL_THRESHOLD="$2"
                shift 2
                ;;
            --notification-email)
                NOTIFICATION_EMAIL="$2"
                shift 2
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            check|rotate|rotate-all|schedule|policies|emergency-rotate)
                COMMAND="$1"
                shift
                ;;
            *)
                if [[ -z "$SA_NAME" && "$COMMAND" == "rotate" ]]; then
                    SA_NAME="$1"
                    shift
                else
                    log_error "Unknown argument: $1"
                    show_usage
                    exit 1
                fi
                ;;
        esac
    done

    # Validation
    if [[ -z "$COMMAND" ]]; then
        log_error "Command is required"
        show_usage
        exit 1
    fi

    if [[ -z "$PROJECT_ID" ]]; then
        log_error "PROJECT_ID is required"
        exit 1
    fi

    if [[ "$COMMAND" == "rotate" && -z "$SA_NAME" ]]; then
        log_error "Service account name is required for rotate command"
        exit 1
    fi
}

# Calculate days since date
days_since() {
    local date_str="$1"
    local date_epoch

    # Handle different date formats
    if date -d "$date_str" >/dev/null 2>&1; then
        # GNU date (Linux)
        date_epoch=$(date -d "$date_str" +%s)
    elif date -j -f "%Y-%m-%dT%H:%M:%SZ" "$date_str" >/dev/null 2>&1; then
        # BSD date (macOS) - ISO format
        date_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$date_str" +%s)
    else
        # Try other formats
        date_epoch=$(date -d "$date_str" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$date_str" +%s 2>/dev/null || echo "0")
    fi

    local current_epoch
    current_epoch=$(date +%s)

    local diff_seconds=$((current_epoch - date_epoch))
    local diff_days=$((diff_seconds / 86400))

    echo "$diff_days"
}

# Send notification
send_notification() {
    local subject="$1"
    local message="$2"
    local severity="${3:-INFO}"

    # Create notification payload
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    local notification="{
        \"timestamp\": \"$timestamp\",
        \"project\": \"$PROJECT_ID\",
        \"environment\": \"${ENVIRONMENT:-unknown}\",
        \"severity\": \"$severity\",
        \"subject\": \"$subject\",
        \"message\": \"$message\",
        \"source\": \"credential-rotation-system\"
    }"

    # Log to audit file
    local audit_dir="${CLOUDSDK_CONFIG:-$HOME/.gcloud}/logs"
    local audit_file="$audit_dir/credential-rotation-$(date +%Y%m%d).log"
    mkdir -p "$audit_dir"
    echo "$notification" >> "$audit_file"

    # Send webhook notification if configured
    if [[ -n "${NOTIFICATION_WEBHOOK:-}" ]]; then
        local webhook_payload
        case "$severity" in
            "CRITICAL"|"ERROR")
                webhook_payload="{\"text\":\"🚨 $subject\", \"attachments\":[{\"color\":\"danger\",\"text\":\"$message\"}]}"
                ;;
            "WARNING")
                webhook_payload="{\"text\":\"⚠️ $subject\", \"attachments\":[{\"color\":\"warning\",\"text\":\"$message\"}]}"
                ;;
            *)
                webhook_payload="{\"text\":\"ℹ️ $subject\", \"attachments\":[{\"color\":\"good\",\"text\":\"$message\"}]}"
                ;;
        esac

        if command -v curl >/dev/null 2>&1; then
            curl -s -X POST -H "Content-type: application/json" \
                --data "$webhook_payload" \
                "$NOTIFICATION_WEBHOOK" >/dev/null || true
        fi
    fi

    # Send email if configured
    if [[ -n "$NOTIFICATION_EMAIL" ]] && command -v mail >/dev/null 2>&1; then
        echo "$message" | mail -s "$subject" "$NOTIFICATION_EMAIL" 2>/dev/null || true
    fi

    log_info "Notification sent: $subject"
}

# Check credential status
check_credentials() {
    log_step "Checking credential status for project: $PROJECT_ID"

    echo -e "${WHITE}Credential Status Report${NC}"
    echo "════════════════════════════════════════════════════════"
    echo "Project: $PROJECT_ID"
    echo "Environment: ${ENVIRONMENT:-unknown}"
    echo "Check Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "────────────────────────────────────────────────────────"
    echo ""

    # Get all service accounts
    local sa_list
    mapfile -t sa_list < <(gcloud iam service-accounts list \
        --project="$PROJECT_ID" \
        --format="value(email)")

    local total_sas=${#sa_list[@]}
    local keys_checked=0
    local warnings=0
    local criticals=0
    local expired=0

    echo -e "${CYAN}Service Account Analysis:${NC}"
    printf "%-50s %-15s %-15s %-10s\n" "SERVICE ACCOUNT" "KEY COUNT" "OLDEST KEY" "STATUS"
    echo "────────────────────────────────────────────────────────────────────────────"

    for sa_email in "${sa_list[@]}"; do
        # Skip default service accounts
        if [[ "$sa_email" =~ -compute@developer.gserviceaccount.com$ ]] || \
           [[ "$sa_email" =~ @appspot.gserviceaccount.com$ ]] || \
           [[ "$sa_email" =~ @cloudbuild.gserviceaccount.com$ ]]; then
            continue
        fi

        # Get keys for this service account
        local key_info
        key_info=$(gcloud iam service-accounts keys list \
            --iam-account="$sa_email" \
            --project="$PROJECT_ID" \
            --format="value(validAfterTime)" 2>/dev/null || echo "")

        if [[ -z "$key_info" ]]; then
            printf "%-50s %-15s %-15s %-10s\n" "${sa_email:0:47}..." "0" "N/A" "NO_KEYS"
            continue
        fi

        # Count keys and find oldest
        local key_count
        key_count=$(echo "$key_info" | wc -l)
        local oldest_key
        oldest_key=$(echo "$key_info" | sort | head -1)

        ((keys_checked++))

        # Calculate age of oldest key
        local key_age
        key_age=$(days_since "$oldest_key")

        # Determine status
        local status color
        if [[ $key_age -gt $MAX_AGE ]]; then
            status="EXPIRED"
            color="${RED}"
            ((expired++))
        elif [[ $key_age -gt $CRITICAL_THRESHOLD ]]; then
            status="CRITICAL"
            color="${RED}"
            ((criticals++))
        elif [[ $key_age -gt $WARN_THRESHOLD ]]; then
            status="WARNING"
            color="${YELLOW}"
            ((warnings++))
        else
            status="OK"
            color="${GREEN}"
        fi

        printf "%-50s %-15s %-15s " "${sa_email:0:47}..." "$key_count" "${key_age}d"
        echo -e "${color}${status}${NC}"

        # Generate notifications for problematic keys
        if [[ "$status" == "EXPIRED" ]]; then
            send_notification \
                "EXPIRED: Service Account Key" \
                "Service account $sa_email has expired key ($key_age days old). Immediate rotation required." \
                "CRITICAL"
        elif [[ "$status" == "CRITICAL" ]]; then
            send_notification \
                "CRITICAL: Service Account Key Near Expiry" \
                "Service account $sa_email has key nearing expiry ($key_age days old). Rotation recommended." \
                "CRITICAL"
        elif [[ "$status" == "WARNING" ]]; then
            send_notification \
                "WARNING: Service Account Key Aging" \
                "Service account $sa_email has aging key ($key_age days old). Schedule rotation soon." \
                "WARNING"
        fi
    done

    echo ""
    echo -e "${WHITE}Summary:${NC}"
    echo "• Total Service Accounts: $total_sas"
    echo "• Accounts with Keys: $keys_checked"
    echo -e "• ${GREEN}OK:${NC} $((keys_checked - warnings - criticals - expired))"
    echo -e "• ${YELLOW}Warnings:${NC} $warnings"
    echo -e "• ${RED}Critical:${NC} $criticals"
    echo -e "• ${RED}Expired:${NC} $expired"

    echo ""
    echo -e "${CYAN}Recommendations:${NC}"
    if [[ $expired -gt 0 ]]; then
        echo "• IMMEDIATE ACTION: Rotate expired keys"
    fi
    if [[ $criticals -gt 0 ]]; then
        echo "• URGENT: Schedule rotation for critical keys"
    fi
    if [[ $warnings -gt 0 ]]; then
        echo "• Plan rotation for aging keys"
    fi
    echo "• Consider using Workload Identity Federation instead of keys"
    echo "• Set up automated rotation schedule"

    # Exit with appropriate code
    if [[ $expired -gt 0 ]]; then
        exit 2  # Critical issues
    elif [[ $criticals -gt 0 ]]; then
        exit 1  # Warning issues
    else
        exit 0  # All good
    fi
}

# Rotate specific service account
rotate_service_account() {
    log_step "Rotating service account: $SA_NAME"

    local sa_email="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

    # Verify service account exists
    if ! gcloud iam service-accounts describe "$sa_email" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_error "Service account does not exist: $sa_email"
        exit 1
    fi

    # Get current keys
    local current_keys
    mapfile -t current_keys < <(gcloud iam service-accounts keys list \
        --iam-account="$sa_email" \
        --project="$PROJECT_ID" \
        --format="value(name)" 2>/dev/null || echo "")

    local key_count=${#current_keys[@]}

    echo "Current keys for $sa_email: $key_count"

    if [[ $key_count -eq 0 ]]; then
        log_info "No keys to rotate for $sa_email"
        return 0
    fi

    # Safety check for production
    if [[ "${PRODUCTION_MODE:-false}" == "true" && "$FORCE" != "true" ]]; then
        log_warning "PRODUCTION ENVIRONMENT - Key rotation"
        echo "This will create new keys and may affect running applications"
        read -p "Continue with rotation? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Rotation cancelled"
            return 0
        fi
    fi

    # Create rotation plan
    local rotation_timestamp
    rotation_timestamp=$(date +%Y%m%d-%H%M%S)
    local new_key_file="${SA_NAME}-key-${rotation_timestamp}.json"

    log_info "Rotation plan:"
    echo "  • Service Account: $sa_email"
    echo "  • Current Keys: $key_count"
    echo "  • New Key File: $new_key_file"
    echo "  • Rotation Time: $(date)"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would create new key and rotate credentials"
        return 0
    fi

    # Step 1: Create new key
    log_step "Creating new key..."
    if gcloud iam service-accounts keys create "$new_key_file" \
        --iam-account="$sa_email" \
        --project="$PROJECT_ID"; then
        log_success "Created new key: $new_key_file"

        # Secure the key file
        chmod 600 "$new_key_file"
    else
        log_error "Failed to create new key"
        return 1
    fi

    # Step 2: Validation period
    log_info "New key created successfully"
    log_warning "IMPORTANT: Update applications to use the new key before old keys are deleted"

    # Step 3: Schedule old key cleanup (optional)
    if [[ "${AUTO_CLEANUP_OLD_KEYS:-false}" == "true" ]]; then
        log_info "Scheduling old key cleanup in ${KEY_CLEANUP_DELAY:-24} hours"
        # This would typically be handled by a separate cleanup process
        create_cleanup_schedule "$sa_email" "$rotation_timestamp"
    else
        log_warning "Manual cleanup required for old keys"
        echo "To clean up old keys after verification:"
        for key_name in "${current_keys[@]}"; do
            if [[ "$key_name" != "projects/$PROJECT_ID/serviceAccounts/$sa_email/keys/"* ]]; then
                continue
            fi
            echo "  gcloud iam service-accounts keys delete '$key_name' --iam-account='$sa_email'"
        done
    fi

    # Step 4: Create rotation record
    create_rotation_record "$sa_email" "$rotation_timestamp" "$new_key_file"

    # Step 5: Send notification
    send_notification \
        "Service Account Key Rotated" \
        "Successfully rotated keys for $sa_email. New key: $new_key_file. Update applications and clean up old keys." \
        "INFO"

    log_success "Rotation completed for $sa_email"
}

# Rotate all eligible credentials
rotate_all_credentials() {
    log_step "Starting batch rotation for project: $PROJECT_ID"

    # Get all service accounts with aging keys
    local sa_list
    mapfile -t sa_list < <(gcloud iam service-accounts list \
        --project="$PROJECT_ID" \
        --format="value(email)")

    local rotation_candidates=()

    echo "Analyzing service accounts for rotation eligibility..."

    for sa_email in "${sa_list[@]}"; do
        # Skip system service accounts
        if [[ "$sa_email" =~ -compute@developer.gserviceaccount.com$ ]] || \
           [[ "$sa_email" =~ @appspot.gserviceaccount.com$ ]] || \
           [[ "$sa_email" =~ @cloudbuild.gserviceaccount.com$ ]]; then
            continue
        fi

        # Get oldest key age
        local oldest_key
        oldest_key=$(gcloud iam service-accounts keys list \
            --iam-account="$sa_email" \
            --project="$PROJECT_ID" \
            --format="value(validAfterTime)" 2>/dev/null | sort | head -1)

        if [[ -n "$oldest_key" ]]; then
            local key_age
            key_age=$(days_since "$oldest_key")

            if [[ $key_age -gt $WARN_THRESHOLD ]]; then
                rotation_candidates+=("$sa_email:$key_age")
            fi
        fi
    done

    if [[ ${#rotation_candidates[@]} -eq 0 ]]; then
        log_success "No service accounts require rotation at this time"
        return 0
    fi

    echo ""
    echo "Rotation candidates:"
    for candidate in "${rotation_candidates[@]}"; do
        local sa_email="${candidate%%:*}"
        local age="${candidate##*:}"
        echo "  • $sa_email (${age}d old)"
    done

    echo ""
    if [[ "$FORCE" != "true" ]]; then
        read -p "Proceed with batch rotation of ${#rotation_candidates[@]} service accounts? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Batch rotation cancelled"
            return 0
        fi
    fi

    # Perform rotations
    local success_count=0
    local failure_count=0

    for candidate in "${rotation_candidates[@]}"; do
        local sa_email="${candidate%%:*}"
        local sa_name="${sa_email%%@*}"

        echo ""
        log_step "Rotating $sa_email..."

        # Set SA_NAME for rotation function
        SA_NAME="$sa_name"

        if rotate_service_account; then
            ((success_count++))
            log_success "Successfully rotated $sa_email"
        else
            ((failure_count++))
            log_error "Failed to rotate $sa_email"
        fi
    done

    echo ""
    echo "Batch rotation complete:"
    echo "  • Successful: $success_count"
    echo "  • Failed: $failure_count"

    # Send summary notification
    send_notification \
        "Batch Credential Rotation Complete" \
        "Rotated credentials for $success_count service accounts. $failure_count failures." \
        "$([[ $failure_count -gt 0 ]] && echo "WARNING" || echo "INFO")"
}

# Create rotation schedule
create_rotation_schedule() {
    log_step "Creating rotation schedule..."

    local schedule_file="${CLOUDSDK_CONFIG:-$HOME/.gcloud}/rotation-schedule.json"
    local schedule_dir
    schedule_dir=$(dirname "$schedule_file")
    mkdir -p "$schedule_dir"

    cat > "$schedule_file" <<EOF
{
  "rotation_policy": {
    "max_key_age_days": $MAX_AGE,
    "warning_threshold_days": $WARN_THRESHOLD,
    "critical_threshold_days": $CRITICAL_THRESHOLD,
    "auto_rotate_enabled": false,
    "auto_cleanup_enabled": false,
    "cleanup_delay_hours": 24
  },
  "notification_settings": {
    "email": "$NOTIFICATION_EMAIL",
    "webhook": "${NOTIFICATION_WEBHOOK:-}",
    "notify_on_warning": true,
    "notify_on_critical": true,
    "notify_on_rotation": true
  },
  "schedule_metadata": {
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "created_by": "${USER:-unknown}",
    "project_id": "$PROJECT_ID",
    "environment": "${ENVIRONMENT:-unknown}"
  }
}
EOF

    log_success "Created rotation schedule: $schedule_file"

    echo ""
    echo "To enable automatic rotation, consider setting up a cron job:"
    echo "  # Daily credential check at 2 AM"
    echo "  0 2 * * * $0 check --project $PROJECT_ID"
    echo ""
    echo "  # Weekly rotation check on Sundays"
    echo "  0 3 * * 0 $0 rotate-all --project $PROJECT_ID --dry-run"
    echo ""
    echo "For production environments, use CI/CD pipelines instead of cron jobs."
}

# Emergency rotation
emergency_rotate() {
    log_critical "EMERGENCY ROTATION INITIATED"

    echo -e "${RED}⚠️  EMERGENCY CREDENTIAL ROTATION${NC}"
    echo "This will immediately rotate all service account credentials"
    echo "in project: $PROJECT_ID"
    echo ""

    # Force immediate rotation without normal safeguards
    WARN_THRESHOLD=0
    FORCE=true

    if [[ "${SKIP_EMERGENCY_CONFIRMATION:-false}" != "true" ]]; then
        echo "Type 'EMERGENCY_ROTATE' to confirm:"
        read -r confirmation
        if [[ "$confirmation" != "EMERGENCY_ROTATE" ]]; then
            log_info "Emergency rotation cancelled"
            exit 1
        fi
    fi

    log_warning "Proceeding with emergency rotation..."

    # Send emergency notification
    send_notification \
        "EMERGENCY: Credential Rotation Initiated" \
        "Emergency credential rotation started for project $PROJECT_ID. All service account keys will be rotated immediately." \
        "CRITICAL"

    # Perform emergency rotation
    rotate_all_credentials

    # Post-rotation notification
    send_notification \
        "EMERGENCY: Credential Rotation Complete" \
        "Emergency credential rotation completed for project $PROJECT_ID. Review and update all applications immediately." \
        "CRITICAL"

    log_critical "EMERGENCY ROTATION COMPLETE - UPDATE ALL APPLICATIONS"
}

# Show/update rotation policies
manage_policies() {
    log_step "Managing rotation policies"

    local policy_file="${ROTATION_POLICY:-${CLOUDSDK_CONFIG:-$HOME/.gcloud}/rotation-schedule.json}"

    if [[ -f "$policy_file" ]]; then
        echo -e "${WHITE}Current Rotation Policy:${NC}"
        echo "────────────────────────────────────────"

        if command -v jq >/dev/null 2>&1; then
            jq '.rotation_policy' "$policy_file" 2>/dev/null || cat "$policy_file"
        else
            cat "$policy_file"
        fi
    else
        log_info "No rotation policy found. Creating default policy..."
        create_rotation_schedule
    fi
}

# Create rotation record
create_rotation_record() {
    local sa_email="$1"
    local timestamp="$2"
    local key_file="$3"

    local records_dir="${CLOUDSDK_CONFIG:-$HOME/.gcloud}/rotation-records"
    mkdir -p "$records_dir"

    local record_file="$records_dir/rotation-${timestamp}.json"

    cat > "$record_file" <<EOF
{
  "rotation_event": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "service_account": "$sa_email",
    "project_id": "$PROJECT_ID",
    "environment": "${ENVIRONMENT:-unknown}",
    "rotation_id": "$timestamp",
    "new_key_file": "$key_file",
    "rotated_by": "${USER:-unknown}",
    "rotation_type": "manual",
    "script_version": "$ROTATION_VERSION"
  },
  "metadata": {
    "dry_run": $DRY_RUN,
    "forced": $FORCE,
    "max_age_policy": $MAX_AGE,
    "warning_threshold": $WARN_THRESHOLD,
    "critical_threshold": $CRITICAL_THRESHOLD
  }
}
EOF

    log_info "Created rotation record: $record_file"
}

# Create cleanup schedule
create_cleanup_schedule() {
    local sa_email="$1"
    local timestamp="$2"

    local cleanup_dir="${CLOUDSDK_CONFIG:-$HOME/.gcloud}/pending-cleanup"
    mkdir -p "$cleanup_dir"

    local cleanup_file="$cleanup_dir/cleanup-${timestamp}.json"

    cat > "$cleanup_file" <<EOF
{
  "cleanup_task": {
    "service_account": "$sa_email",
    "project_id": "$PROJECT_ID",
    "rotation_timestamp": "$timestamp",
    "scheduled_cleanup": "$(date -d "+${KEY_CLEANUP_DELAY:-24} hours" -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -v+24H -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "manual")",
    "status": "pending"
  }
}
EOF

    log_info "Scheduled cleanup task: $cleanup_file"
}

# Main execution
main() {
    print_banner
    parse_arguments "$@"

    # Validate project access
    if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
        log_error "Cannot access project: $PROJECT_ID"
        exit 1
    fi

    case "$COMMAND" in
        check)
            check_credentials
            ;;
        rotate)
            rotate_service_account
            ;;
        rotate-all)
            rotate_all_credentials
            ;;
        schedule)
            create_rotation_schedule
            ;;
        policies)
            manage_policies
            ;;
        emergency-rotate)
            emergency_rotate
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
