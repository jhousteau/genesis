#!/bin/bash

# Common utilities for the Universal Project Platform
# Version: 1.0.0

# Logging utilities with timestamps
log_with_timestamp() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message"
}

# Enhanced logging functions
log_debug() {
    [[ "${DEBUG:-false}" == "true" ]] && log_with_timestamp "DEBUG" "$1"
}

log_trace() {
    [[ "${TRACE:-false}" == "true" ]] && log_with_timestamp "TRACE" "$1"
}

# File utilities
ensure_directory() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        log_debug "Created directory: $dir"
    fi
}

backup_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        cp "$file" "${file}.backup.$(date +%s)"
        log_debug "Backed up file: $file"
    fi
}

# Configuration utilities
load_config() {
    local config_file="$1"
    if [[ -f "$config_file" ]]; then
        source "$config_file"
        log_debug "Loaded config: $config_file"
    else
        log_debug "Config file not found: $config_file"
        return 1
    fi
}

# Project utilities
get_project_root() {
    local current_dir="$(pwd)"
    while [[ "$current_dir" != "/" ]]; do
        if [[ -f "$current_dir/.bootstrap.yaml" ]] || [[ -f "$current_dir/bootstrap.yaml" ]]; then
            echo "$current_dir"
            return 0
        fi
        current_dir="$(dirname "$current_dir")"
    done
    return 1
}

# Validation utilities
validate_project_name() {
    local name="$1"
    if [[ ! "$name" =~ ^[a-z][a-z0-9-]*[a-z0-9]$ ]]; then
        log_error "Invalid project name: $name"
        log_info "Project names must start with a letter, contain only lowercase letters, numbers, and hyphens, and end with a letter or number"
        return 1
    fi
}

validate_environment_name() {
    local env="$1"
    case "$env" in
        dev|test|staging|prod)
            return 0
            ;;
        *)
            log_error "Invalid environment: $env"
            log_info "Valid environments: dev, test, staging, prod"
            return 1
            ;;
    esac
}

# GCP utilities
setup_gcp_isolation() {
    local project_name="$1"
    local environment="$2"
    local gcp_project="$3"

    local gcloud_home="$HOME/.gcloud/${project_name}-${environment}"

    ensure_directory "$gcloud_home"

    export CLOUDSDK_CONFIG="$gcloud_home"

    log_debug "Set up GCP isolation: $gcloud_home for $gcp_project"
}

# Network utilities
check_connectivity() {
    local host="$1"
    local port="${2:-443}"

    if command -v nc &> /dev/null; then
        if nc -z "$host" "$port" 2>/dev/null; then
            return 0
        else
            return 1
        fi
    else
        # Fallback using curl
        if curl -s --connect-timeout 5 "https://$host" &> /dev/null; then
            return 0
        else
            return 1
        fi
    fi
}

# Security utilities
mask_sensitive_data() {
    local input="$1"
    # Mask common sensitive patterns
    echo "$input" | \
        sed 's/password=[^[:space:]]*/password=****/g' | \
        sed 's/token=[^[:space:]]*/token=****/g' | \
        sed 's/key=[^[:space:]]*/key=****/g' | \
        sed 's/secret=[^[:space:]]*/secret=****/g'
}

# Performance utilities
measure_time() {
    local start_time=$(date +%s.%N)
    "$@"
    local exit_code=$?
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    log_debug "Command execution time: ${duration}s"
    return $exit_code
}

# Error handling utilities
handle_error() {
    local exit_code=$?
    local line_number=$1
    local command="$2"

    if [[ $exit_code -ne 0 ]]; then
        log_error "Command failed on line $line_number: $command"
        log_error "Exit code: $exit_code"
    fi

    return $exit_code
}

# Set up error handling
trap 'handle_error $LINENO "$BASH_COMMAND"' ERR

# Cleanup utilities
cleanup_temp_files() {
    if [[ -n "${TEMP_FILES:-}" ]]; then
        for file in $TEMP_FILES; do
            if [[ -f "$file" ]]; then
                rm -f "$file"
                log_debug "Cleaned up temp file: $file"
            fi
        done
    fi
}

# Register cleanup on exit
trap cleanup_temp_files EXIT

# Export functions that might be used by other scripts
export -f log_debug log_trace ensure_directory backup_file validate_project_name validate_environment_name
