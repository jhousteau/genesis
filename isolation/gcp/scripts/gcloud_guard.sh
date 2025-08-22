#!/usr/bin/env bash
# Enhanced GCloud Guard - Comprehensive protection against wrong-project operations
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Prevents cross-contamination and enforces safety policies

set -euo pipefail

# Script metadata
GUARD_VERSION="2.0.0"
AUDIT_LOG="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/logs/audit.log"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# Logging function
audit_log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    # Ensure log directory exists
    mkdir -p "$(dirname "$AUDIT_LOG")"
    
    # Log to file
    echo "[$timestamp] [$level] [$$] [${USER:-unknown}] $message" >> "$AUDIT_LOG"
    
    # Also log to stderr for visibility
    case "$level" in
        ERROR)
            echo -e "${RED}❌ GUARD: $message${NC}" >&2
            ;;
        WARN)
            echo -e "${YELLOW}⚠️  GUARD: $message${NC}" >&2
            ;;
        INFO)
            echo -e "${BLUE}ℹ️  GUARD: $message${NC}" >&2
            ;;
        SUCCESS)
            echo -e "${GREEN}✅ GUARD: $message${NC}" >&2
            ;;
    esac
}

# Validate isolation environment
validate_isolation() {
    audit_log "INFO" "Guard v${GUARD_VERSION} validating isolation environment"
    
    # Check for required CLOUDSDK_CONFIG
    if [[ -z "${CLOUDSDK_CONFIG:-}" ]]; then
        audit_log "ERROR" "CLOUDSDK_CONFIG not set - isolation not active"
        echo -e "${RED}❌ ISOLATION FAILURE${NC}" >&2
        echo "CLOUDSDK_CONFIG environment variable not set" >&2
        echo "This indicates the isolation environment is not properly configured" >&2
        echo "" >&2
        echo "Solutions:" >&2
        echo "  1. Run: direnv allow" >&2
        echo "  2. Source .envrc: source .envrc" >&2
        echo "  3. Run bootstrap: ./scripts/bootstrap_gcloud.sh" >&2
        exit 1
    fi
    
    # Validate isolation directory exists
    if [[ ! -d "$CLOUDSDK_CONFIG" ]]; then
        audit_log "ERROR" "Isolation directory does not exist: $CLOUDSDK_CONFIG"
        echo -e "${RED}❌ ISOLATION DIRECTORY MISSING${NC}" >&2
        echo "Expected isolation directory: $CLOUDSDK_CONFIG" >&2
        echo "Run: ./scripts/bootstrap_gcloud.sh" >&2
        exit 1
    fi
    
    # Check for initialization marker
    if [[ ! -f "$CLOUDSDK_CONFIG/.initialized" ]]; then
        audit_log "WARN" "Initialization marker missing - running bootstrap"
        echo -e "${YELLOW}⚠️  Isolation not fully initialized${NC}" >&2
        
        if [[ -f "./scripts/bootstrap_gcloud.sh" ]]; then
            echo "Running bootstrap automatically..." >&2
            ./scripts/bootstrap_gcloud.sh
        else
            echo "Run: ./scripts/bootstrap_gcloud.sh" >&2
            exit 1
        fi
    fi
    
    audit_log "SUCCESS" "Isolation environment validated"
}

# Get and validate configured project
get_configured_project() {
    local cfg_project
    cfg_project=$(gcloud config get-value core/project 2>/dev/null || true)
    
    if [[ -z "$cfg_project" ]]; then
        audit_log "ERROR" "No project configured in gcloud config"
        echo -e "${RED}❌ NO PROJECT CONFIGURED${NC}" >&2
        echo "No core/project configured in: $CLOUDSDK_CONFIG" >&2
        echo "Run: ./scripts/bootstrap_gcloud.sh" >&2
        exit 1
    fi
    
    echo "$cfg_project"
}

# Validate project matches expected environment
validate_project_environment() {
    local cfg_project="$1"
    
    # Check against PROJECT_ID environment variable if set
    if [[ -n "${PROJECT_ID:-}" && "$cfg_project" != "$PROJECT_ID" ]]; then
        audit_log "ERROR" "Project mismatch: configured=$cfg_project, expected=$PROJECT_ID"
        echo -e "${RED}❌ PROJECT MISMATCH DETECTED${NC}" >&2
        echo "Configured project: $cfg_project" >&2
        echo "Expected project:   $PROJECT_ID" >&2
        echo "" >&2
        echo "This could indicate cross-contamination or misconfiguration!" >&2
        echo "Run: ./scripts/bootstrap_gcloud.sh" >&2
        exit 1
    fi
    
    # Check against stored project marker
    if [[ -f "$CLOUDSDK_CONFIG/.project" ]]; then
        local stored_project
        stored_project=$(cat "$CLOUDSDK_CONFIG/.project" 2>/dev/null || true)
        
        if [[ -n "$stored_project" && "$cfg_project" != "$stored_project" ]]; then
            audit_log "ERROR" "Project mismatch: configured=$cfg_project, stored=$stored_project"
            echo -e "${RED}❌ PROJECT ISOLATION BREACH${NC}" >&2
            echo "Configured project: $cfg_project" >&2
            echo "Stored project:     $stored_project" >&2
            echo "" >&2
            echo "Isolation directory may be corrupted or misconfigured!" >&2
            exit 1
        fi
    fi
}

# Production safety checks
production_safety_check() {
    local cfg_project="$1"
    local command_args=("$@")
    
    # Check if this is a production project
    local is_production=false
    
    # Method 1: Check project name patterns
    if [[ "$cfg_project" =~ (^|[-_])prod([-_]|$) ]]; then
        is_production=true
    fi
    
    # Method 2: Check environment variable
    if [[ "${PRODUCTION_MODE:-false}" == "true" ]]; then
        is_production=true
    fi
    
    # Method 3: Check stored environment marker
    if [[ -f "$CLOUDSDK_CONFIG/.environment" ]]; then
        local stored_env
        stored_env=$(cat "$CLOUDSDK_CONFIG/.environment" 2>/dev/null || true)
        if [[ "$stored_env" =~ ^(prod|production)$ ]]; then
            is_production=true
        fi
    fi
    
    if [[ "$is_production" == "true" ]]; then
        audit_log "WARN" "Production operation detected: project=$cfg_project command=${command_args[*]}"
        
        # Check for destructive operations
        local is_destructive=false
        local destructive_patterns=(
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
        )
        
        for pattern in "${destructive_patterns[@]}"; do
            if printf '%s\n' "${command_args[@]}" | grep -qi "$pattern"; then
                is_destructive=true
                break
            fi
        done
        
        # Special handling for destructive operations
        if [[ "$is_destructive" == "true" ]]; then
            if [[ "${CONFIRM_PROD:-}" != "I_UNDERSTAND" ]]; then
                audit_log "ERROR" "Destructive production operation blocked: ${command_args[*]}"
                echo -e "${RED}❌ PRODUCTION SAFETY BLOCK${NC}" >&2
                echo "" >&2
                echo -e "${WHITE}DESTRUCTIVE OPERATION DETECTED IN PRODUCTION${NC}" >&2
                echo "Project:  $cfg_project" >&2
                echo "Command:  gcloud ${command_args[*]}" >&2
                echo "" >&2
                echo -e "${YELLOW}To proceed with this destructive operation:${NC}" >&2
                echo "  export CONFIRM_PROD=I_UNDERSTAND" >&2
                echo "" >&2
                echo "This safety mechanism prevents accidental data loss in production." >&2
                echo "Please review the command carefully before confirming." >&2
                exit 1
            else
                audit_log "WARN" "Destructive production operation confirmed: ${command_args[*]}"
                echo -e "${RED}⚠️  CONFIRMED DESTRUCTIVE PRODUCTION OPERATION${NC}" >&2
                echo "Project: $cfg_project" >&2
                echo "Command: gcloud ${command_args[*]}" >&2
            fi
        else
            echo -e "${YELLOW}⚠️  PRODUCTION OPERATION${NC}" >&2
            echo "Project: $cfg_project" >&2
        fi
    fi
}

# Resource quota and cost protection
resource_protection_check() {
    local command_args=("$@")
    
    # Check for resource-intensive operations
    local resource_intensive_patterns=(
        "compute.*create"
        "sql.*create"
        "container.*create"
        "gke.*create"
        "dataflow.*create"
        "dataproc.*create"
        "ml-engine.*create"
    )
    
    for pattern in "${resource_intensive_patterns[@]}"; do
        if printf '%s\n' "${command_args[@]}" | grep -qiE "$pattern"; then
            audit_log "INFO" "Resource-intensive operation detected: ${command_args[*]}"
            
            # Check cost thresholds if configured
            if [[ -f "$CLOUDSDK_CONFIG/cost-config.json" ]]; then
                local threshold
                threshold=$(jq -r '.threshold_usd // empty' "$CLOUDSDK_CONFIG/cost-config.json" 2>/dev/null || true)
                
                if [[ -n "$threshold" ]]; then
                    echo -e "${BLUE}💰 Cost threshold configured: \$${threshold} USD${NC}" >&2
                    echo "Consider resource costs before proceeding" >&2
                fi
            fi
            break
        fi
    done
}

# Service account validation
validate_service_account() {
    local impersonate_sa
    impersonate_sa=$(gcloud config get-value auth/impersonate_service_account 2>/dev/null || true)
    
    if [[ -n "$impersonate_sa" ]]; then
        audit_log "INFO" "Using service account impersonation: $impersonate_sa"
        echo -e "${GREEN}🔐 Impersonating: $impersonate_sa${NC}" >&2
        
        # Validate service account has required permissions
        # This is a basic check - more sophisticated validation could be added
        if ! gcloud iam service-accounts describe "$impersonate_sa" >/dev/null 2>&1; then
            audit_log "WARN" "Cannot describe impersonated service account: $impersonate_sa"
            echo -e "${YELLOW}⚠️  Warning: Cannot validate service account permissions${NC}" >&2
        fi
    fi
}

# Cross-project operation detection
detect_cross_project_operations() {
    local cfg_project="$1"
    shift
    local command_args=("$@")
    
    # Look for project references in command arguments
    local found_projects=()
    
    for arg in "${command_args[@]}"; do
        # Match project ID patterns in arguments
        if [[ "$arg" =~ --project=([a-z][a-z0-9-]{4,28}[a-z0-9]) ]]; then
            found_projects+=("${BASH_REMATCH[1]}")
        elif [[ "$arg" =~ projects/([a-z][a-z0-9-]{4,28}[a-z0-9]) ]]; then
            found_projects+=("${BASH_REMATCH[1]}")
        fi
    done
    
    # Check for cross-project references
    for project in "${found_projects[@]}"; do
        if [[ "$project" != "$cfg_project" ]]; then
            audit_log "ERROR" "Cross-project operation detected: configured=$cfg_project, referenced=$project"
            echo -e "${RED}❌ CROSS-PROJECT OPERATION BLOCKED${NC}" >&2
            echo "Configured project: $cfg_project" >&2
            echo "Referenced project:  $project" >&2
            echo "Command: gcloud ${command_args[*]}" >&2
            echo "" >&2
            echo "This could indicate accidental cross-contamination!" >&2
            echo "If this is intentional, use the system gcloud directly:" >&2
            echo "  $(which gcloud) ${command_args[*]}" >&2
            exit 1
        fi
    done
}

# Rate limiting and throttling
apply_rate_limiting() {
    local command_args=("$@")
    
    # Simple rate limiting based on command type
    local rate_limited_patterns=(
        "compute.*create"
        "sql.*create"
        "container.*create"
    )
    
    for pattern in "${rate_limited_patterns[@]}"; do
        if printf '%s\n' "${command_args[@]}" | grep -qiE "$pattern"; then
            # Simple rate limiting - could be enhanced with proper token bucket
            local last_command_file="$CLOUDSDK_CONFIG/.last_command"
            local current_time=$(date +%s)
            
            if [[ -f "$last_command_file" ]]; then
                local last_time
                last_time=$(cat "$last_command_file" 2>/dev/null || echo "0")
                local time_diff=$((current_time - last_time))
                
                if [[ $time_diff -lt 5 ]]; then
                    audit_log "WARN" "Rate limiting applied: too many rapid commands"
                    echo -e "${YELLOW}⚠️  Rate limiting: Please wait ${time_diff} seconds${NC}" >&2
                    sleep $((5 - time_diff))
                fi
            fi
            
            echo "$current_time" > "$last_command_file"
            break
        fi
    done
}

# Main guard logic
main() {
    local command_args=("$@")
    
    # Skip guard for certain safe operations
    case "${1:-}" in
        "help"|"--help"|"-h"|"version"|"--version"|"config"|"auth")
            audit_log "INFO" "Allowing safe operation: $1"
            exec $(which -a gcloud | grep -v "$(readlink -f "$0")" | head -1) "$@"
            ;;
    esac
    
    # Full validation for all other operations
    validate_isolation
    
    local cfg_project
    cfg_project=$(get_configured_project)
    
    validate_project_environment "$cfg_project"
    production_safety_check "$cfg_project" "$@"
    resource_protection_check "$@"
    validate_service_account
    detect_cross_project_operations "$cfg_project" "$@"
    apply_rate_limiting "$@"
    
    # Log the command execution
    audit_log "INFO" "Executing: gcloud ${command_args[*]} (project: $cfg_project)"
    echo -e "${GREEN}→ Project: $cfg_project${NC}" >&2
    echo -e "${CYAN}→ Command: gcloud ${command_args[*]}${NC}" >&2
    
    # Execute the actual gcloud command
    exec $(which -a gcloud | grep -v "$(readlink -f "$0")" | head -1) "$@"
}

# Execute main function
main "$@"