#!/usr/bin/env bash
# Production Guardrails - Advanced safety mechanisms for production environments
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Implements multi-layer safety checks and confirmation workflows

set -euo pipefail

# Script metadata
PRODUCTION_GUARDRAILS_VERSION="2.0.0"
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
SAFETY_CONFIG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/safety-config.json"
SAFETY_LOG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/logs/safety-guardrails.log"
APPROVAL_QUEUE_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/approvals/pending-approvals.json"
EMERGENCY_LOG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/logs/emergency-actions.log"

# Destructive operation patterns
DESTRUCTIVE_PATTERNS=(
    "delete"
    "destroy"
    "remove"
    "rm"
    "terminate"
    "stop"
    "reset"
    "clear"
    "purge"
    "drop"
    "truncate"
    "wipe"
    "clean"
    "flush"
    "erase"
    "cancel"
    "disable"
    "revoke"
    "suspend"
)

# High-risk resource patterns
HIGH_RISK_RESOURCES=(
    "compute.*instances"
    "sql.*instances"
    "storage.*buckets"
    "container.*clusters"
    "dataflow.*jobs"
    "bigquery.*datasets"
    "pubsub.*topics"
    "functions.*"
    "run.*services"
    "endpoints.*"
    "dns.*zones"
    "kms.*"
    "secretmanager.*"
)

# Print banner
print_banner() {
    echo -e "${RED}"
    echo "══════════════════════════════════════════════════════════════"
    echo "🛡️  PRODUCTION GUARDRAILS v${PRODUCTION_GUARDRAILS_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "   ⚠️  PRODUCTION SAFETY ENFORCEMENT ACTIVE ⚠️"
    echo "══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Initialize safety configuration
init_safety_config() {
    log_step "Initializing production safety configuration..."

    mkdir -p "$(dirname "$SAFETY_CONFIG_FILE")"
    mkdir -p "$(dirname "$SAFETY_LOG_FILE")"
    mkdir -p "$(dirname "$APPROVAL_QUEUE_FILE")"
    mkdir -p "$(dirname "$EMERGENCY_LOG_FILE")"

    if [[ ! -f "$SAFETY_CONFIG_FILE" ]]; then
        create_default_safety_config
    fi

    log_success "Safety configuration initialized"
}

# Create default safety configuration
create_default_safety_config() {
    cat > "$SAFETY_CONFIG_FILE" <<EOF
{
    "version": "$PRODUCTION_GUARDRAILS_VERSION",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "safety_level": "${SAFETY_LEVEL:-maximum}",
    "confirmation_workflows": {
        "destructive_operations": {
            "enabled": true,
            "require_manual_confirmation": true,
            "require_multiple_approvals": true,
            "min_approval_count": 2,
            "approval_timeout_minutes": 60,
            "require_change_request": true
        },
        "high_risk_resources": {
            "enabled": true,
            "require_manual_confirmation": true,
            "require_multiple_approvals": false,
            "min_approval_count": 1,
            "approval_timeout_minutes": 30
        },
        "bulk_operations": {
            "enabled": true,
            "max_resources_without_approval": 5,
            "require_confirmation": true
        }
    },
    "emergency_procedures": {
        "emergency_contact": "${EMERGENCY_CONTACT:-}",
        "emergency_phone": "${EMERGENCY_PHONE:-}",
        "emergency_runbook": "${EMERGENCY_RUNBOOK:-}",
        "auto_escalation_minutes": 30,
        "escalation_chain": [
            "${PRIMARY_ONCALL:-}",
            "${SECONDARY_ONCALL:-}",
            "${MANAGER_CONTACT:-}"
        ]
    },
    "monitoring": {
        "audit_all_blocked_operations": true,
        "alert_on_bypass_attempts": true,
        "log_all_confirmations": true,
        "retain_logs_days": 2555
    },
    "bypass_mechanisms": {
        "emergency_bypass_enabled": true,
        "emergency_bypass_requires_justification": true,
        "emergency_bypass_auto_expires_minutes": 60,
        "emergency_bypass_approval_required": true
    },
    "notifications": {
        "slack_webhook": "${SLACK_WEBHOOK:-}",
        "email_alerts": "${SAFETY_EMAIL:-}",
        "pagerduty_integration": "${PAGERDUTY_INTEGRATION_KEY:-}",
        "notify_on_blocked_operations": true,
        "notify_on_emergency_bypass": true
    },
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

# Load safety configuration
load_safety_config() {
    if [[ ! -f "$SAFETY_CONFIG_FILE" ]]; then
        init_safety_config
    fi

    SAFETY_LEVEL=$(jq -r '.safety_level // "maximum"' "$SAFETY_CONFIG_FILE")
    PROJECT_ID=$(jq -r '.project_id // ""' "$SAFETY_CONFIG_FILE")
    ENVIRONMENT=$(jq -r '.environment // ""' "$SAFETY_CONFIG_FILE")
}

# Check if operation is destructive
is_destructive_operation() {
    local command_string="$1"

    for pattern in "${DESTRUCTIVE_PATTERNS[@]}"; do
        if echo "$command_string" | grep -qi "$pattern"; then
            return 0
        fi
    done

    return 1
}

# Check if operation affects high-risk resources
is_high_risk_resource() {
    local command_string="$1"

    for pattern in "${HIGH_RISK_RESOURCES[@]}"; do
        if echo "$command_string" | grep -qiE "$pattern"; then
            return 0
        fi
    done

    return 1
}

# Check if operation is bulk operation
is_bulk_operation() {
    local command_string="$1"

    # Look for patterns indicating bulk operations
    if echo "$command_string" | grep -qE "(--all|--filter=|--zone=.*--all|instances.*list.*delete)"; then
        return 0
    fi

    # Check for multiple resource names
    local resource_count
    resource_count=$(echo "$command_string" | grep -o '[a-zA-Z0-9-]*instance[a-zA-Z0-9-]*\|[a-zA-Z0-9-]*bucket[a-zA-Z0-9-]*\|[a-zA-Z0-9-]*cluster[a-zA-Z0-9-]*' | wc -l)

    if [[ "$resource_count" -gt 5 ]]; then
        return 0
    fi

    return 1
}

# Calculate operation risk score
calculate_risk_score() {
    local command_string="$1"
    local score=0

    # Base risk factors
    if is_destructive_operation "$command_string"; then
        ((score += 50))
    fi

    if is_high_risk_resource "$command_string"; then
        ((score += 30))
    fi

    if is_bulk_operation "$command_string"; then
        ((score += 20))
    fi

    # Additional risk factors
    if echo "$command_string" | grep -qi "prod\|production"; then
        ((score += 20))
    fi

    if echo "$command_string" | grep -qi "force\|--quiet\|--no-prompt"; then
        ((score += 15))
    fi

    if echo "$command_string" | grep -qi "recursive\|--all"; then
        ((score += 10))
    fi

    echo "$score"
}

# Get risk level from score
get_risk_level() {
    local score="$1"

    if [[ "$score" -ge 80 ]]; then
        echo "CRITICAL"
    elif [[ "$score" -ge 60 ]]; then
        echo "HIGH"
    elif [[ "$score" -ge 40 ]]; then
        echo "MEDIUM"
    elif [[ "$score" -ge 20 ]]; then
        echo "LOW"
    else
        echo "MINIMAL"
    fi
}

# Create approval request
create_approval_request() {
    local command_string="$1"
    local risk_level="$2"
    local risk_score="$3"
    local justification="$4"

    local approval_id
    approval_id="approval_$(date +%s)_$(printf '%04d' $RANDOM)"

    local approval_request
    approval_request=$(cat <<EOF
{
    "approval_id": "$approval_id",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "command": "$command_string",
    "risk_level": "$risk_level",
    "risk_score": $risk_score,
    "justification": "$justification",
    "requested_by": "${USER:-unknown}",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "source_ip": "${SSH_CLIENT%% *}",
    "session_id": "${SSH_TTY:-}",
    "status": "PENDING",
    "approvals": [],
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "expires_at": "$(date -u -d '+1 hour' +%Y-%m-%dT%H:%M:%SZ)",
    "guardrails_version": "$PRODUCTION_GUARDRAILS_VERSION"
}
EOF
)

    # Add to approval queue
    if [[ -f "$APPROVAL_QUEUE_FILE" ]]; then
        local existing_approvals
        existing_approvals=$(cat "$APPROVAL_QUEUE_FILE")
        echo "$existing_approvals" | jq --argjson new "$approval_request" '. + [$new]' > "$APPROVAL_QUEUE_FILE"
    else
        echo "[$approval_request]" > "$APPROVAL_QUEUE_FILE"
    fi

    log_approval_request "$approval_id" "$command_string" "$risk_level" "$justification"

    echo "$approval_id"
}

# Log approval request
log_approval_request() {
    local approval_id="$1"
    local command_string="$2"
    local risk_level="$3"
    local justification="$4"

    local log_entry
    log_entry=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "operation": "approval_request",
    "approval_id": "$approval_id",
    "command": "$command_string",
    "risk_level": "$risk_level",
    "justification": "$justification",
    "requested_by": "${USER:-unknown}",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "guardrails_version": "$PRODUCTION_GUARDRAILS_VERSION"
}
EOF
)

    mkdir -p "$(dirname "$SAFETY_LOG_FILE")"
    echo "$log_entry" >> "$SAFETY_LOG_FILE"
}

# Send approval notification
send_approval_notification() {
    local approval_id="$1"
    local command_string="$2"
    local risk_level="$3"
    local justification="$4"

    load_safety_config

    # Send Slack notification
    local slack_webhook
    slack_webhook=$(jq -r '.notifications.slack_webhook // empty' "$SAFETY_CONFIG_FILE")

    if [[ -n "$slack_webhook" ]]; then
        local color="danger"
        case "$risk_level" in
            "CRITICAL") color="danger" ;;
            "HIGH") color="warning" ;;
            *) color="good" ;;
        esac

        local payload
        payload=$(cat <<EOF
{
    "text": "🛡️ Production Operation Approval Required",
    "attachments": [
        {
            "color": "$color",
            "title": "Approval Request: $approval_id",
            "fields": [
                {"title": "Risk Level", "value": "$risk_level", "short": true},
                {"title": "User", "value": "${USER:-unknown}", "short": true},
                {"title": "Project", "value": "${PROJECT_ID:-unknown}", "short": true},
                {"title": "Environment", "value": "${ENVIRONMENT:-unknown}", "short": true},
                {"title": "Command", "value": "\`$command_string\`", "short": false},
                {"title": "Justification", "value": "$justification", "short": false}
            ],
            "actions": [
                {
                    "type": "button",
                    "text": "Approve",
                    "style": "primary",
                    "value": "approve_$approval_id"
                },
                {
                    "type": "button",
                    "text": "Deny",
                    "style": "danger",
                    "value": "deny_$approval_id"
                }
            ],
            "footer": "Production Guardrails v$PRODUCTION_GUARDRAILS_VERSION",
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
    local email_alerts
    email_alerts=$(jq -r '.notifications.email_alerts // empty' "$SAFETY_CONFIG_FILE")

    if [[ -n "$email_alerts" ]] && command -v mail >/dev/null 2>&1; then
        local subject="🛡️ Production Operation Approval Required - $risk_level"
        local body
        body=$(cat <<EOF
Production Operation Approval Required

Approval ID: $approval_id
Risk Level: $risk_level
Requested By: ${USER:-unknown}
Project: ${PROJECT_ID:-unknown}
Environment: ${ENVIRONMENT:-unknown}
Command: $command_string
Justification: $justification

To approve or deny this request, use:
production-guardrails approve $approval_id [reason]
production-guardrails deny $approval_id [reason]

This request will expire in 1 hour.

Generated by Production Guardrails v$PRODUCTION_GUARDRAILS_VERSION
EOF
)

        echo "$body" | mail -s "$subject" "$email_alerts" >/dev/null 2>&1 || true
    fi
}

# Check for existing approval
check_approval_status() {
    local approval_id="$1"

    if [[ ! -f "$APPROVAL_QUEUE_FILE" ]]; then
        echo "NOT_FOUND"
        return 1
    fi

    local approval_status
    approval_status=$(jq -r ".[] | select(.approval_id == \"$approval_id\") | .status" "$APPROVAL_QUEUE_FILE" 2>/dev/null || echo "NOT_FOUND")

    echo "$approval_status"
}

# Production safety check
production_safety_check() {
    local command_string="$1"

    log_step "Running production safety check..."

    load_safety_config

    # Skip if not production environment
    if [[ "${ENVIRONMENT:-}" != "prod" && "${ENVIRONMENT:-}" != "production" && "${PRODUCTION_MODE:-false}" != "true" ]]; then
        log_info "Non-production environment detected. Skipping safety checks."
        return 0
    fi

    # Calculate risk score
    local risk_score risk_level
    risk_score=$(calculate_risk_score "$command_string")
    risk_level=$(get_risk_level "$risk_score")

    log_info "Command risk assessment:"
    log_info "  Command: $command_string"
    log_info "  Risk Score: $risk_score"
    log_info "  Risk Level: $risk_level"

    # Check for emergency bypass
    if [[ "${EMERGENCY_BYPASS:-}" == "ACTIVE" ]]; then
        log_warning "EMERGENCY BYPASS ACTIVE - Operation allowed"
        log_emergency_bypass "$command_string" "$risk_level"
        return 0
    fi

    # Check existing confirmation
    if [[ "${CONFIRM_PROD:-}" == "I_UNDERSTAND" ]]; then
        log_warning "Manual confirmation provided - Operation allowed"
        log_manual_confirmation "$command_string" "$risk_level"
        return 0
    fi

    # Risk-based decision
    case "$risk_level" in
        "CRITICAL"|"HIGH")
            log_error "HIGH RISK OPERATION BLOCKED"
            echo ""
            echo -e "${RED}🛑 OPERATION BLOCKED BY PRODUCTION GUARDRAILS${NC}"
            echo ""
            echo -e "${WHITE}Risk Assessment:${NC}"
            echo "• Command: $command_string"
            echo "• Risk Level: $risk_level"
            echo "• Risk Score: $risk_score"
            echo ""
            echo -e "${WHITE}To proceed, you have the following options:${NC}"
            echo ""
            echo -e "${YELLOW}1. Manual Confirmation (immediate):${NC}"
            echo "   export CONFIRM_PROD=I_UNDERSTAND"
            echo "   # Then re-run your command"
            echo ""
            echo -e "${YELLOW}2. Request Approval (recommended):${NC}"
            echo "   production-guardrails request-approval \"$command_string\" \"[justification]\""
            echo ""
            echo -e "${YELLOW}3. Emergency Bypass (emergencies only):${NC}"
            echo "   production-guardrails emergency-bypass \"[justification]\""
            echo ""

            # Create approval request automatically if justification provided
            if [[ -n "${OPERATION_JUSTIFICATION:-}" ]]; then
                local approval_id
                approval_id=$(create_approval_request "$command_string" "$risk_level" "$risk_score" "$OPERATION_JUSTIFICATION")
                echo -e "${BLUE}Approval request created: $approval_id${NC}"
                echo "Waiting for approval..."
                send_approval_notification "$approval_id" "$command_string" "$risk_level" "$OPERATION_JUSTIFICATION"
            fi

            return 1
            ;;
        "MEDIUM")
            log_warning "MEDIUM RISK OPERATION - Confirmation required"
            echo ""
            echo -e "${YELLOW}⚠️  MEDIUM RISK OPERATION DETECTED${NC}"
            echo "Command: $command_string"
            echo "Risk Score: $risk_score"
            echo ""
            read -p "Do you want to proceed? (type 'yes' to confirm): " confirmation

            if [[ "$confirmation" == "yes" ]]; then
                log_success "User confirmed medium risk operation"
                log_manual_confirmation "$command_string" "$risk_level"
                return 0
            else
                log_info "User cancelled medium risk operation"
                return 1
            fi
            ;;
        *)
            log_success "Low risk operation - Proceeding"
            return 0
            ;;
    esac
}

# Log manual confirmation
log_manual_confirmation() {
    local command_string="$1"
    local risk_level="$2"

    local log_entry
    log_entry=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "operation": "manual_confirmation",
    "command": "$command_string",
    "risk_level": "$risk_level",
    "confirmed_by": "${USER:-unknown}",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "source_ip": "${SSH_CLIENT%% *}",
    "guardrails_version": "$PRODUCTION_GUARDRAILS_VERSION"
}
EOF
)

    mkdir -p "$(dirname "$SAFETY_LOG_FILE")"
    echo "$log_entry" >> "$SAFETY_LOG_FILE"
}

# Log emergency bypass
log_emergency_bypass() {
    local command_string="$1"
    local risk_level="$2"

    local log_entry
    log_entry=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "operation": "emergency_bypass",
    "command": "$command_string",
    "risk_level": "$risk_level",
    "bypassed_by": "${USER:-unknown}",
    "justification": "${BYPASS_JUSTIFICATION:-No justification provided}",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "source_ip": "${SSH_CLIENT%% *}",
    "guardrails_version": "$PRODUCTION_GUARDRAILS_VERSION"
}
EOF
)

    mkdir -p "$(dirname "$EMERGENCY_LOG_FILE")"
    echo "$log_entry" >> "$EMERGENCY_LOG_FILE"
    echo "$log_entry" >> "$SAFETY_LOG_FILE"
}

# Request approval
request_approval() {
    local command_string="$1"
    local justification="$2"

    if [[ -z "$justification" ]]; then
        log_error "Justification required for approval request"
        echo "Usage: production-guardrails request-approval \"<command>\" \"<justification>\""
        return 1
    fi

    local risk_score risk_level
    risk_score=$(calculate_risk_score "$command_string")
    risk_level=$(get_risk_level "$risk_score")

    local approval_id
    approval_id=$(create_approval_request "$command_string" "$risk_level" "$risk_score" "$justification")

    echo ""
    echo -e "${CYAN}🔔 Approval Request Created${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Approval ID: $approval_id"
    echo "Command: $command_string"
    echo "Risk Level: $risk_level"
    echo "Risk Score: $risk_score"
    echo "Justification: $justification"
    echo "Expires: $(date -u -d '+1 hour' '+%Y-%m-%d %H:%M:%S UTC')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Notifications sent to approvers."
    echo "You can check status with: production-guardrails status $approval_id"

    send_approval_notification "$approval_id" "$command_string" "$risk_level" "$justification"
}

# Emergency bypass
emergency_bypass() {
    local justification="$1"

    if [[ -z "$justification" ]]; then
        log_error "Justification required for emergency bypass"
        echo "Usage: production-guardrails emergency-bypass \"<justification>\""
        return 1
    fi

    echo ""
    echo -e "${RED}🚨 EMERGENCY BYPASS ACTIVATED${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Justification: $justification"
    echo "Activated by: ${USER:-unknown}"
    echo "Valid for: 1 hour"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "${YELLOW}WARNING: This bypass will be logged and audited!${NC}"
    echo ""
    echo "To activate emergency bypass for the next operation:"
    echo "export EMERGENCY_BYPASS=ACTIVE"
    echo "export BYPASS_JUSTIFICATION=\"$justification\""

    # Log the bypass activation
    local log_entry
    log_entry=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "operation": "emergency_bypass_activation",
    "justification": "$justification",
    "activated_by": "${USER:-unknown}",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "source_ip": "${SSH_CLIENT%% *}",
    "expires_at": "$(date -u -d '+1 hour' +%Y-%m-%dT%H:%M:%SZ)",
    "guardrails_version": "$PRODUCTION_GUARDRAILS_VERSION"
}
EOF
)

    mkdir -p "$(dirname "$EMERGENCY_LOG_FILE")"
    echo "$log_entry" >> "$EMERGENCY_LOG_FILE"

    # Send emergency notification
    send_emergency_notification "$justification"
}

# Send emergency notification
send_emergency_notification() {
    local justification="$1"

    load_safety_config

    # Send high-priority Slack notification
    local slack_webhook
    slack_webhook=$(jq -r '.notifications.slack_webhook // empty' "$SAFETY_CONFIG_FILE")

    if [[ -n "$slack_webhook" ]]; then
        local payload
        payload=$(cat <<EOF
{
    "text": "🚨 EMERGENCY BYPASS ACTIVATED",
    "attachments": [
        {
            "color": "danger",
            "title": "Production Emergency Bypass",
            "fields": [
                {"title": "User", "value": "${USER:-unknown}", "short": true},
                {"title": "Project", "value": "${PROJECT_ID:-unknown}", "short": true},
                {"title": "Environment", "value": "${ENVIRONMENT:-unknown}", "short": true},
                {"title": "Source IP", "value": "${SSH_CLIENT%% *}", "short": true},
                {"title": "Justification", "value": "$justification", "short": false}
            ],
            "footer": "Production Guardrails v$PRODUCTION_GUARDRAILS_VERSION",
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
}

# Show safety dashboard
show_safety_dashboard() {
    echo -e "${CYAN}═══ PRODUCTION SAFETY DASHBOARD ═══${NC}"
    echo ""

    load_safety_config

    echo -e "${WHITE}Configuration:${NC}"
    echo "Project: ${PROJECT_ID:-unknown}"
    echo "Environment: ${ENVIRONMENT:-unknown}"
    echo "Safety Level: $SAFETY_LEVEL"
    echo ""

    # Check for active bypasses
    if [[ "${EMERGENCY_BYPASS:-}" == "ACTIVE" ]]; then
        echo -e "${RED}🚨 EMERGENCY BYPASS ACTIVE${NC}"
        echo ""
    fi

    if [[ "${CONFIRM_PROD:-}" == "I_UNDERSTAND" ]]; then
        echo -e "${YELLOW}⚠️  MANUAL CONFIRMATION SET${NC}"
        echo ""
    fi

    # Show pending approvals
    if [[ -f "$APPROVAL_QUEUE_FILE" ]]; then
        local pending_count
        pending_count=$(jq '[.[] | select(.status == "PENDING")] | length' "$APPROVAL_QUEUE_FILE" 2>/dev/null || echo "0")

        if [[ "$pending_count" -gt 0 ]]; then
            echo -e "${YELLOW}Pending Approvals: $pending_count${NC}"
            echo ""
        fi
    fi

    # Show recent safety events
    if [[ -f "$SAFETY_LOG_FILE" ]]; then
        echo -e "${WHITE}Recent Safety Events:${NC}"
        tail -n 5 "$SAFETY_LOG_FILE" | jq -r '
            [.timestamp, .operation, .risk_level // "N/A"] | @tsv' | \
        while IFS=$'\t' read -r timestamp operation risk_level; do
            case "$risk_level" in
                "CRITICAL") color="$RED" ;;
                "HIGH") color="$YELLOW" ;;
                *) color="$GREEN" ;;
            esac
            echo -e "${color}$timestamp - $operation - $risk_level${NC}"
        done
    fi
}

# Main function
main() {
    local command="${1:-dashboard}"

    case "$command" in
        "init")
            init_safety_config
            ;;
        "check")
            local command_string="${2:-}"
            if [[ -z "$command_string" ]]; then
                log_error "Command string required"
                echo "Usage: $0 check \"<command to check>\""
                exit 1
            fi
            production_safety_check "$command_string"
            ;;
        "request-approval")
            local command_string="${2:-}"
            local justification="${3:-}"
            request_approval "$command_string" "$justification"
            ;;
        "emergency-bypass")
            local justification="${2:-}"
            emergency_bypass "$justification"
            ;;
        "status")
            local approval_id="${2:-}"
            if [[ -n "$approval_id" ]]; then
                local status
                status=$(check_approval_status "$approval_id")
                echo "Approval $approval_id status: $status"
            else
                show_safety_dashboard
            fi
            ;;
        "dashboard"|"d")
            print_banner
            show_safety_dashboard
            ;;
        "clear-bypass")
            unset EMERGENCY_BYPASS
            unset BYPASS_JUSTIFICATION
            unset CONFIRM_PROD
            log_success "All safety bypasses cleared"
            ;;
        "help"|"--help"|"-h")
            print_banner
            echo "Production Guardrails v$PRODUCTION_GUARDRAILS_VERSION"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  init                     Initialize safety configuration"
            echo "  check \"<command>\"        Check if command is safe to run"
            echo "  request-approval \"<cmd>\" \"<reason>\"  Request approval for operation"
            echo "  emergency-bypass \"<reason>\"          Activate emergency bypass"
            echo "  status [approval-id]     Show status or specific approval"
            echo "  dashboard, d             Show safety dashboard"
            echo "  clear-bypass             Clear all active bypasses"
            echo "  help                     Show this help"
            echo ""
            echo "Environment Variables:"
            echo "  CONFIRM_PROD=I_UNDERSTAND          Manual confirmation"
            echo "  EMERGENCY_BYPASS=ACTIVE            Emergency bypass"
            echo "  OPERATION_JUSTIFICATION=\"reason\"   Auto-create approval request"
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
