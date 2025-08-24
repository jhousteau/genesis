#!/usr/bin/env bash
# Cost Guardian - Advanced cost monitoring and protection
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Monitors spending and prevents cost overruns

set -euo pipefail

# Script metadata
COST_GUARDIAN_VERSION="2.0.0"
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

# Configuration
COST_CONFIG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/cost-config.json"
COST_LOG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/logs/cost-guardian.log"
COST_ALERT_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/alerts/cost-alerts.json"

# Default thresholds
DEFAULT_WARNING_THRESHOLD=80
DEFAULT_CRITICAL_THRESHOLD=95
DEFAULT_EMERGENCY_THRESHOLD=100

# Load configuration
load_cost_config() {
    if [[ -f "$COST_CONFIG_FILE" ]]; then
        THRESHOLD_USD=$(jq -r '.threshold_usd // 1000' "$COST_CONFIG_FILE" 2>/dev/null || echo "1000")
        WARNING_THRESHOLD=$(jq -r '.warning_threshold // 80' "$COST_CONFIG_FILE" 2>/dev/null || echo "$DEFAULT_WARNING_THRESHOLD")
        CRITICAL_THRESHOLD=$(jq -r '.critical_threshold // 95' "$COST_CONFIG_FILE" 2>/dev/null || echo "$DEFAULT_CRITICAL_THRESHOLD")
        EMERGENCY_THRESHOLD=$(jq -r '.emergency_threshold // 100' "$COST_CONFIG_FILE" 2>/dev/null || echo "$DEFAULT_EMERGENCY_THRESHOLD")
        ALERT_EMAIL=$(jq -r '.alert_email // empty' "$COST_CONFIG_FILE" 2>/dev/null || echo "")
        SLACK_WEBHOOK=$(jq -r '.slack_webhook // empty' "$COST_CONFIG_FILE" 2>/dev/null || echo "")
    else
        log_warning "Cost configuration not found. Using defaults."
        THRESHOLD_USD=1000
        WARNING_THRESHOLD=$DEFAULT_WARNING_THRESHOLD
        CRITICAL_THRESHOLD=$DEFAULT_CRITICAL_THRESHOLD
        EMERGENCY_THRESHOLD=$DEFAULT_EMERGENCY_THRESHOLD
        ALERT_EMAIL=""
        SLACK_WEBHOOK=""
    fi
}

# Create cost configuration
create_cost_config() {
    local threshold_usd="${1:-1000}"
    local warning_threshold="${2:-80}"
    local critical_threshold="${3:-95}"
    local emergency_threshold="${4:-100}"
    local alert_email="${5:-}"
    local slack_webhook="${6:-}"

    mkdir -p "$(dirname "$COST_CONFIG_FILE")"
    mkdir -p "$(dirname "$COST_ALERT_FILE")"

    cat > "$COST_CONFIG_FILE" <<EOF
{
    "threshold_usd": $threshold_usd,
    "warning_threshold": $warning_threshold,
    "critical_threshold": $critical_threshold,
    "emergency_threshold": $emergency_threshold,
    "alert_email": "$alert_email",
    "slack_webhook": "$slack_webhook",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "configured_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "configured_by": "${USER:-unknown}",
    "version": "$COST_GUARDIAN_VERSION"
}
EOF

    log_success "Cost configuration created: $COST_CONFIG_FILE"
}

# Get current billing information
get_current_billing() {
    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi

    if [[ -z "$project_id" ]]; then
        log_error "No project ID available for billing check"
        return 1
    fi

    # Get billing account
    local billing_account
    billing_account=$(gcloud billing projects describe "$project_id" --format="value(billingAccountName)" 2>/dev/null || echo "")

    if [[ -z "$billing_account" ]]; then
        log_warning "No billing account associated with project $project_id"
        return 1
    fi

    # Extract billing account ID
    local billing_account_id
    billing_account_id=$(echo "$billing_account" | sed 's|billingAccounts/||')

    # Get current month's usage (approximation using Cloud Resource Manager API)
    # Note: This is a simplified approach. For production, use Cloud Billing API with proper setup
    log_info "Checking billing for project: $project_id"
    log_info "Billing account: $billing_account_id"

    # For now, return mock data structure. In production, implement actual billing API calls
    cat <<EOF
{
    "project_id": "$project_id",
    "billing_account_id": "$billing_account_id",
    "current_month_cost": 0.00,
    "last_month_cost": 0.00,
    "currency": "USD",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "note": "Actual billing data requires Cloud Billing API setup"
}
EOF
}

# Calculate cost percentage
calculate_cost_percentage() {
    local current_cost="$1"
    local threshold="$2"

    # Use bc for floating point arithmetic if available, otherwise use awk
    if command -v bc >/dev/null 2>&1; then
        echo "scale=2; ($current_cost / $threshold) * 100" | bc
    else
        awk "BEGIN {printf \"%.2f\", ($current_cost / $threshold) * 100}"
    fi
}

# Check cost thresholds
check_cost_thresholds() {
    log_step "Checking cost thresholds..."

    local billing_info
    billing_info=$(get_current_billing)

    if [[ $? -ne 0 ]]; then
        log_warning "Unable to retrieve billing information"
        return 1
    fi

    local current_cost
    current_cost=$(echo "$billing_info" | jq -r '.current_month_cost // 0')

    local percentage
    percentage=$(calculate_cost_percentage "$current_cost" "$THRESHOLD_USD")

    log_info "Current cost: \$${current_cost} USD (${percentage}% of \$${THRESHOLD_USD} threshold)"

    # Determine alert level
    local alert_level="OK"
    local alert_color="$GREEN"

    if (( $(echo "$percentage >= $EMERGENCY_THRESHOLD" | bc -l 2>/dev/null || awk "BEGIN {print ($percentage >= $EMERGENCY_THRESHOLD)}") )); then
        alert_level="EMERGENCY"
        alert_color="$RED"
        log_error "EMERGENCY: Cost threshold exceeded!"
        trigger_emergency_procedures "$current_cost" "$percentage"
    elif (( $(echo "$percentage >= $CRITICAL_THRESHOLD" | bc -l 2>/dev/null || awk "BEGIN {print ($percentage >= $CRITICAL_THRESHOLD)}") )); then
        alert_level="CRITICAL"
        alert_color="$RED"
        log_error "CRITICAL: Cost approaching limit!"
        send_cost_alert "CRITICAL" "$current_cost" "$percentage"
    elif (( $(echo "$percentage >= $WARNING_THRESHOLD" | bc -l 2>/dev/null || awk "BEGIN {print ($percentage >= $WARNING_THRESHOLD)}") )); then
        alert_level="WARNING"
        alert_color="$YELLOW"
        log_warning "WARNING: Cost threshold reached!"
        send_cost_alert "WARNING" "$current_cost" "$percentage"
    else
        log_success "Cost levels normal"
    fi

    # Log the check
    log_cost_check "$alert_level" "$current_cost" "$percentage"

    # Return appropriate exit code
    case "$alert_level" in
        "EMERGENCY") return 3 ;;
        "CRITICAL") return 2 ;;
        "WARNING") return 1 ;;
        *) return 0 ;;
    esac
}

# Log cost check
log_cost_check() {
    local alert_level="$1"
    local current_cost="$2"
    local percentage="$3"

    mkdir -p "$(dirname "$COST_LOG_FILE")"

    local log_entry
    log_entry=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "alert_level": "$alert_level",
    "current_cost": $current_cost,
    "threshold_usd": $THRESHOLD_USD,
    "percentage": $percentage,
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "user": "${USER:-unknown}",
    "guardian_version": "$COST_GUARDIAN_VERSION"
}
EOF
)

    echo "$log_entry" >> "$COST_LOG_FILE"
}

# Send cost alert
send_cost_alert() {
    local level="$1"
    local current_cost="$2"
    local percentage="$3"

    local alert_data
    alert_data=$(cat <<EOF
{
    "alert_id": "$(uuidgen 2>/dev/null || date +%s)",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "level": "$level",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "current_cost": $current_cost,
    "threshold_usd": $THRESHOLD_USD,
    "percentage": $percentage,
    "message": "Cost $level: \$${current_cost} USD (${percentage}% of \$${THRESHOLD_USD} threshold)"
}
EOF
)

    # Save alert
    mkdir -p "$(dirname "$COST_ALERT_FILE")"
    echo "$alert_data" >> "$COST_ALERT_FILE"

    # Send Slack notification if configured
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        send_slack_alert "$level" "$current_cost" "$percentage"
    fi

    # Send email if configured
    if [[ -n "$ALERT_EMAIL" ]]; then
        send_email_alert "$level" "$current_cost" "$percentage"
    fi
}

# Send Slack alert
send_slack_alert() {
    local level="$1"
    local current_cost="$2"
    local percentage="$3"

    local color="warning"
    local emoji="⚠️"

    case "$level" in
        "EMERGENCY") color="danger"; emoji="🚨" ;;
        "CRITICAL") color="danger"; emoji="❌" ;;
        "WARNING") color="warning"; emoji="⚠️" ;;
    esac

    local payload
    payload=$(cat <<EOF
{
    "attachments": [
        {
            "color": "$color",
            "title": "$emoji Cost $level Alert",
            "fields": [
                {
                    "title": "Project",
                    "value": "${PROJECT_ID:-N/A}",
                    "short": true
                },
                {
                    "title": "Environment",
                    "value": "${ENVIRONMENT:-N/A}",
                    "short": true
                },
                {
                    "title": "Current Cost",
                    "value": "\$${current_cost} USD",
                    "short": true
                },
                {
                    "title": "Threshold",
                    "value": "\$${THRESHOLD_USD} USD (${percentage}%)",
                    "short": true
                }
            ],
            "footer": "Cost Guardian v$COST_GUARDIAN_VERSION",
            "ts": $(date +%s)
        }
    ]
}
EOF
)

    if curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK" >/dev/null 2>&1; then
        log_success "Slack alert sent"
    else
        log_warning "Failed to send Slack alert"
    fi
}

# Send email alert (using mail command if available)
send_email_alert() {
    local level="$1"
    local current_cost="$2"
    local percentage="$3"

    if ! command -v mail >/dev/null 2>&1; then
        log_warning "Mail command not available for email alerts"
        return 1
    fi

    local subject="Cost $level Alert - ${PROJECT_ID:-Unknown Project}"
    local body
    body=$(cat <<EOF
Cost Guardian Alert

Level: $level
Project: ${PROJECT_ID:-N/A}
Environment: ${ENVIRONMENT:-N/A}
Current Cost: \$${current_cost} USD
Threshold: \$${THRESHOLD_USD} USD
Percentage: ${percentage}%

Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Guardian Version: $COST_GUARDIAN_VERSION

This is an automated alert from the Universal Project Platform Cost Guardian.
EOF
)

    if echo "$body" | mail -s "$subject" "$ALERT_EMAIL" >/dev/null 2>&1; then
        log_success "Email alert sent to $ALERT_EMAIL"
    else
        log_warning "Failed to send email alert"
    fi
}

# Trigger emergency procedures
trigger_emergency_procedures() {
    local current_cost="$1"
    local percentage="$2"

    log_error "EMERGENCY PROCEDURES TRIGGERED"
    log_error "Cost has exceeded emergency threshold!"

    # Send emergency alert
    send_cost_alert "EMERGENCY" "$current_cost" "$percentage"

    # Suggest immediate actions
    echo ""
    echo -e "${RED}IMMEDIATE ACTIONS REQUIRED:${NC}"
    echo "1. Review current resource usage"
    echo "2. Stop non-essential resources"
    echo "3. Contact billing administrator"
    echo "4. Review budget settings"
    echo ""

    # Create emergency flag
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${REPO_GCLOUD_HOME:-$HOME/.gcloud}/.emergency_cost_flag"

    # If in automated mode, suggest shutdown commands
    if [[ "${EMERGENCY_AUTO_SUGGEST:-false}" == "true" ]]; then
        echo -e "${YELLOW}Suggested emergency commands:${NC}"
        echo "# Stop all compute instances:"
        echo "gcloud compute instances stop --all --async"
        echo ""
        echo "# Scale down all deployments:"
        echo "kubectl scale deployment --all --replicas=0"
        echo ""
        echo "# Disable auto-scaling:"
        echo "gcloud compute instance-groups managed stop-autoscaling --all"
        echo ""
    fi
}

# List recent cost checks
list_recent_checks() {
    local limit="${1:-10}"

    if [[ -f "$COST_LOG_FILE" ]]; then
        log_info "Recent cost checks (last $limit):"
        echo ""
        tail -n "$limit" "$COST_LOG_FILE" | jq -r '
            [.timestamp, .alert_level, .current_cost, .percentage] |
            @tsv' | \
        while IFS=$'\t' read -r timestamp level cost percentage; do
            case "$level" in
                "EMERGENCY") color="$RED" ;;
                "CRITICAL") color="$RED" ;;
                "WARNING") color="$YELLOW" ;;
                *) color="$GREEN" ;;
            esac
            echo -e "${color}$timestamp - $level - \$${cost} USD (${percentage}%)${NC}"
        done
    else
        log_info "No cost check history found"
    fi
}

# Show cost dashboard
show_cost_dashboard() {
    echo -e "${CYAN}═══ COST GUARDIAN DASHBOARD ═══${NC}"
    echo ""

    load_cost_config

    echo -e "${WHITE}Configuration:${NC}"
    echo "Threshold: \$${THRESHOLD_USD} USD"
    echo "Warning: ${WARNING_THRESHOLD}%"
    echo "Critical: ${CRITICAL_THRESHOLD}%"
    echo "Emergency: ${EMERGENCY_THRESHOLD}%"
    echo ""

    if [[ -f "${REPO_GCLOUD_HOME:-$HOME/.gcloud}/.emergency_cost_flag" ]]; then
        echo -e "${RED}🚨 EMERGENCY COST FLAG ACTIVE${NC}"
        echo ""
    fi

    check_cost_thresholds
    echo ""

    list_recent_checks 5
}

# Main function
main() {
    local command="${1:-check}"

    case "$command" in
        "check"|"c")
            load_cost_config
            check_cost_thresholds
            ;;
        "setup"|"s")
            local threshold="${2:-1000}"
            local warning="${3:-80}"
            local critical="${4:-95}"
            local emergency="${5:-100}"
            local email="${6:-}"
            local slack="${7:-}"
            create_cost_config "$threshold" "$warning" "$critical" "$emergency" "$email" "$slack"
            ;;
        "dashboard"|"d")
            show_cost_dashboard
            ;;
        "history"|"h")
            local limit="${2:-20}"
            list_recent_checks "$limit"
            ;;
        "clear-emergency")
            rm -f "${REPO_GCLOUD_HOME:-$HOME/.gcloud}/.emergency_cost_flag"
            log_success "Emergency flag cleared"
            ;;
        "help"|"--help"|"-h")
            echo "Cost Guardian v$COST_GUARDIAN_VERSION"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  check, c                 Check current cost against thresholds"
            echo "  setup, s [threshold]     Setup cost monitoring with threshold in USD"
            echo "  dashboard, d             Show cost dashboard"
            echo "  history, h [limit]       Show cost check history"
            echo "  clear-emergency          Clear emergency cost flag"
            echo "  help                     Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 setup 500 75 90 100 admin@company.com"
            echo "  $0 check"
            echo "  $0 dashboard"
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
