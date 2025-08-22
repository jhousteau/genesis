#!/bin/bash

# Advanced Logging Module for Whitehorse Platform
# Provides structured logging with correlation IDs, log levels, and GCP Cloud Logging integration

# Set default log level
LOG_LEVEL="${LOG_LEVEL:-INFO}"
ENABLE_STRUCTURED_LOGGING="${ENABLE_STRUCTURED_LOGGING:-true}"
ENABLE_CORRELATION_ID="${ENABLE_CORRELATION_ID:-true}"
SERVICE_NAME="${SERVICE_NAME:-whitehorse-service}"
LOG_FILE="${LOG_FILE:-}"

# Log levels (numeric for comparison)
declare -A LOG_LEVELS=(
    ["TRACE"]=0
    ["DEBUG"]=1
    ["INFO"]=2
    ["WARN"]=3
    ["ERROR"]=4
    ["FATAL"]=5
)

# ANSI color codes for pretty console output
declare -A LOG_COLORS=(
    ["TRACE"]="\033[0;37m"   # White
    ["DEBUG"]="\033[0;36m"   # Cyan
    ["INFO"]="\033[0;32m"    # Green
    ["WARN"]="\033[0;33m"    # Yellow
    ["ERROR"]="\033[0;31m"   # Red
    ["FATAL"]="\033[1;31m"   # Bold Red
    ["RESET"]="\033[0m"      # Reset
)

# Generate correlation ID if not set
generate_correlation_id() {
    if [[ -z "${CORRELATION_ID:-}" && "${ENABLE_CORRELATION_ID}" == "true" ]]; then
        CORRELATION_ID=$(uuidgen 2>/dev/null || echo "$(date +%s)-$$-$(shuf -i 1000-9999 -n 1)")
        export CORRELATION_ID
    fi
}

# Get current timestamp in ISO 8601 format
get_timestamp() {
    date -u '+%Y-%m-%dT%H:%M:%S.%3NZ'
}

# Check if log level should be output
should_log() {
    local level="$1"
    local current_level_num="${LOG_LEVELS[$LOG_LEVEL]}"
    local target_level_num="${LOG_LEVELS[$level]}"
    
    [[ $target_level_num -ge $current_level_num ]]
}

# Format structured log message
format_structured_log() {
    local level="$1"
    local message="$2"
    local metadata="$3"
    
    local timestamp=$(get_timestamp)
    local correlation_id="${CORRELATION_ID:-}"
    local pid="$$"
    local script_name="${0##*/}"
    
    if [[ "${ENABLE_STRUCTURED_LOGGING}" == "true" ]]; then
        # JSON structured logging
        local json_log="{\"timestamp\":\"$timestamp\",\"level\":\"$level\",\"service\":\"$SERVICE_NAME\",\"script\":\"$script_name\",\"pid\":$pid,\"message\":\"$message\""
        
        if [[ -n "$correlation_id" ]]; then
            json_log="${json_log},\"correlation_id\":\"$correlation_id\""
        fi
        
        if [[ -n "$metadata" ]]; then
            json_log="${json_log},\"metadata\":$metadata"
        fi
        
        json_log="${json_log}}"
        echo "$json_log"
    else
        # Plain text logging
        local log_line="[$timestamp] [$level] [$script_name:$pid]"
        if [[ -n "$correlation_id" ]]; then
            log_line="${log_line} [CID:$correlation_id]"
        fi
        log_line="${log_line} $message"
        echo "$log_line"
    fi
}

# Core logging function
_log() {
    local level="$1"
    local message="$2"
    local metadata="${3:-}"
    local output_stream="${4:-stdout}"
    
    if ! should_log "$level"; then
        return 0
    fi
    
    generate_correlation_id
    
    local formatted_log=$(format_structured_log "$level" "$message" "$metadata")
    
    # Console output with colors (if not structured)
    if [[ "${ENABLE_STRUCTURED_LOGGING}" != "true" && -t 1 ]]; then
        local color="${LOG_COLORS[$level]}"
        local reset="${LOG_COLORS[RESET]}"
        echo -e "${color}${formatted_log}${reset}" >&"$([[ $output_stream == "stderr" ]] && echo 2 || echo 1)"
    else
        echo "$formatted_log" >&"$([[ $output_stream == "stderr" ]] && echo 2 || echo 1)"
    fi
    
    # File output
    if [[ -n "$LOG_FILE" ]]; then
        echo "$formatted_log" >> "$LOG_FILE"
    fi
    
    # GCP Cloud Logging (if available and enabled)
    if [[ "${ENABLE_GCP_LOGGING:-false}" == "true" ]] && command -v gcloud &> /dev/null; then
        log_to_gcp "$level" "$message" "$metadata"
    fi
}

# Send log to GCP Cloud Logging
log_to_gcp() {
    local level="$1"
    local message="$2"
    local metadata="$3"
    
    local severity
    case "$level" in
        "TRACE"|"DEBUG") severity="DEBUG" ;;
        "INFO") severity="INFO" ;;
        "WARN") severity="WARNING" ;;
        "ERROR") severity="ERROR" ;;
        "FATAL") severity="CRITICAL" ;;
    esac
    
    local log_entry="{\"message\":\"$message\",\"severity\":\"$severity\",\"service\":\"$SERVICE_NAME\""
    
    if [[ -n "${CORRELATION_ID:-}" ]]; then
        log_entry="${log_entry},\"correlation_id\":\"$CORRELATION_ID\""
    fi
    
    if [[ -n "$metadata" ]]; then
        log_entry="${log_entry},\"metadata\":$metadata"
    fi
    
    log_entry="${log_entry}}"
    
    # Write to GCP (this would be enhanced with proper GCP logging client)
    echo "$log_entry" | gcloud logging write "$SERVICE_NAME" --payload-type=json --severity="$severity" 2>/dev/null || true
}

# Public logging functions
log_trace() {
    _log "TRACE" "$1" "$2" "stdout"
}

log_debug() {
    _log "DEBUG" "$1" "$2" "stdout"
}

log_info() {
    _log "INFO" "$1" "$2" "stdout"
}

log_warn() {
    _log "WARN" "$1" "$2" "stderr"
}

log_error() {
    _log "ERROR" "$1" "$2" "stderr"
}

log_fatal() {
    _log "FATAL" "$1" "$2" "stderr"
}

# Performance logging
log_performance() {
    local operation="$1"
    local start_time="$2"
    local end_time="${3:-$(date +%s.%N)}"
    local success="${4:-true}"
    
    local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "unknown")
    local metadata="{\"operation\":\"$operation\",\"duration_seconds\":$duration,\"success\":$success}"
    
    log_info "Performance: $operation completed" "$metadata"
}

# Timing wrapper function
time_operation() {
    local operation_name="$1"
    shift
    
    log_debug "Starting operation: $operation_name"
    local start_time=$(date +%s.%N)
    
    if "$@"; then
        local end_time=$(date +%s.%N)
        log_performance "$operation_name" "$start_time" "$end_time" "true"
        return 0
    else
        local exit_code=$?
        local end_time=$(date +%s.%N)
        log_performance "$operation_name" "$start_time" "$end_time" "false"
        log_error "Operation failed: $operation_name" "{\"exit_code\":$exit_code}"
        return $exit_code
    fi
}

# Context logging (with correlation ID)
with_correlation_id() {
    local correlation_id="$1"
    shift
    
    local old_correlation_id="${CORRELATION_ID:-}"
    export CORRELATION_ID="$correlation_id"
    
    "$@"
    local exit_code=$?
    
    if [[ -n "$old_correlation_id" ]]; then
        export CORRELATION_ID="$old_correlation_id"
    else
        unset CORRELATION_ID
    fi
    
    return $exit_code
}

# Request logging middleware
log_request_start() {
    local method="$1"
    local endpoint="$2"
    local user_id="${3:-}"
    
    generate_correlation_id
    
    local metadata="{\"method\":\"$method\",\"endpoint\":\"$endpoint\""
    if [[ -n "$user_id" ]]; then
        metadata="${metadata},\"user_id\":\"$user_id\""
    fi
    metadata="${metadata}}"
    
    export REQUEST_START_TIME=$(date +%s.%N)
    log_info "Request started: $method $endpoint" "$metadata"
}

log_request_end() {
    local status_code="$1"
    local response_size="${2:-0}"
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - ${REQUEST_START_TIME:-$end_time}" | bc -l 2>/dev/null || echo "unknown")
    
    local metadata="{\"status_code\":$status_code,\"response_size_bytes\":$response_size,\"duration_seconds\":$duration}"
    
    if [[ $status_code -ge 400 ]]; then
        log_error "Request completed with error: $status_code" "$metadata"
    else
        log_info "Request completed successfully: $status_code" "$metadata"
    fi
    
    unset REQUEST_START_TIME
}

# Health check logging
log_health_check() {
    local component="$1"
    local status="$2"
    local details="${3:-}"
    
    local metadata="{\"component\":\"$component\",\"status\":\"$status\""
    if [[ -n "$details" ]]; then
        metadata="${metadata},\"details\":\"$details\""
    fi
    metadata="${metadata}}"
    
    if [[ "$status" == "healthy" ]]; then
        log_info "Health check passed: $component" "$metadata"
    else
        log_error "Health check failed: $component" "$metadata"
    fi
}

# Security event logging
log_security_event() {
    local event_type="$1"
    local user_id="${2:-}"
    local ip_address="${3:-}"
    local details="${4:-}"
    
    local metadata="{\"event_type\":\"$event_type\""
    if [[ -n "$user_id" ]]; then
        metadata="${metadata},\"user_id\":\"$user_id\""
    fi
    if [[ -n "$ip_address" ]]; then
        metadata="${metadata},\"ip_address\":\"$ip_address\""
    fi
    if [[ -n "$details" ]]; then
        metadata="${metadata},\"details\":\"$details\""
    fi
    metadata="${metadata}}"
    
    log_warn "Security event: $event_type" "$metadata"
}

# Set log level
set_log_level() {
    local level="$1"
    if [[ -n "${LOG_LEVELS[$level]}" ]]; then
        LOG_LEVEL="$level"
        log_info "Log level set to: $level"
    else
        log_error "Invalid log level: $level. Valid levels: ${!LOG_LEVELS[*]}"
        return 1
    fi
}

# Get current log level
get_log_level() {
    echo "$LOG_LEVEL"
}

# Enable/disable structured logging
set_structured_logging() {
    local enabled="$1"
    ENABLE_STRUCTURED_LOGGING="$enabled"
    log_info "Structured logging set to: $enabled"
}

# Log startup information
log_startup() {
    local script_name="${0##*/}"
    local version="${VERSION:-unknown}"
    local metadata="{\"script\":\"$script_name\",\"version\":\"$version\",\"pid\":$$,\"log_level\":\"$LOG_LEVEL\"}"
    
    log_info "Service starting: $script_name" "$metadata"
}

# Log shutdown information
log_shutdown() {
    local script_name="${0##*/}"
    local exit_code="${1:-0}"
    local metadata="{\"script\":\"$script_name\",\"exit_code\":$exit_code,\"pid\":$$}"
    
    log_info "Service shutting down: $script_name" "$metadata"
}

# Setup logging configuration
setup_logging() {
    local config_file="${1:-}"
    
    if [[ -n "$config_file" && -f "$config_file" ]]; then
        source "$config_file"
        log_info "Logging configuration loaded from: $config_file"
    fi
    
    # Ensure log directory exists if LOG_FILE is set
    if [[ -n "$LOG_FILE" ]]; then
        local log_dir=$(dirname "$LOG_FILE")
        mkdir -p "$log_dir" 2>/dev/null || true
    fi
    
    # Set up log rotation if logrotate is available
    if command -v logrotate &> /dev/null && [[ -n "$LOG_FILE" ]]; then
        setup_log_rotation
    fi
}

# Setup log rotation
setup_log_rotation() {
    local logrotate_conf="/tmp/whitehorse-logrotate.conf"
    
    cat > "$logrotate_conf" << EOF
$LOG_FILE {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) $(id -gn)
}
EOF
    
    log_debug "Log rotation configured: $logrotate_conf"
}

# Export functions for use in other scripts
export -f log_trace log_debug log_info log_warn log_error log_fatal
export -f log_performance time_operation with_correlation_id
export -f log_request_start log_request_end log_health_check log_security_event
export -f set_log_level get_log_level set_structured_logging
export -f log_startup log_shutdown setup_logging

# Initialize logging on source
generate_correlation_id

# Register shutdown logging
trap 'log_shutdown $?' EXIT