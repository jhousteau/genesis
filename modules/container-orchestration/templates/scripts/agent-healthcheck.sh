#!/bin/bash
# Genesis Agent Health Check Script
# Comprehensive health check for containerized agents

set -euo pipefail

# Configuration
HEALTH_PORT="${HEALTH_PORT:-8080}"
TIMEOUT="${HEALTH_TIMEOUT:-5}"
AGENT_TYPE="${AGENT_TYPE:-backend-developer}"

# Health check function
check_health() {
    local endpoint="$1"
    local expected_status="${2:-200}"

    if command -v curl >/dev/null 2>&1; then
        response=$(curl -s -w "%{http_code}" -o /dev/null --max-time "$TIMEOUT" "http://localhost:$HEALTH_PORT$endpoint" 2>/dev/null || echo "000")
    else
        # Fallback using wget
        response=$(wget -q -O /dev/null --timeout="$TIMEOUT" "http://localhost:$HEALTH_PORT$endpoint" 2>&1 && echo "200" || echo "000")
    fi

    if [[ "$response" == "$expected_status" ]]; then
        return 0
    else
        return 1
    fi
}

# Check if required processes are running
check_processes() {
    # Check if health server is running
    if ! pgrep -f "health_server.py" >/dev/null; then
        echo "Health server not running"
        return 1
    fi

    # Check if metrics server is running
    if ! pgrep -f "metrics_server.py" >/dev/null; then
        echo "Metrics server not running"
        return 1
    fi

    return 0
}

# Check system resources
check_resources() {
    local max_cpu_usage=95
    local max_memory_usage=95

    # Check CPU usage
    if command -v top >/dev/null 2>&1; then
        cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d' ' -f1)
        if (( $(echo "$cpu_usage > $max_cpu_usage" | bc -l) )); then
            echo "High CPU usage: ${cpu_usage}%"
            return 1
        fi
    fi

    # Check memory usage
    if [[ -f /proc/meminfo ]]; then
        total_mem=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        available_mem=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
        used_mem=$((total_mem - available_mem))
        memory_usage=$((used_mem * 100 / total_mem))

        if (( memory_usage > max_memory_usage )); then
            echo "High memory usage: ${memory_usage}%"
            return 1
        fi
    fi

    return 0
}

# Check disk space
check_disk_space() {
    local max_disk_usage=90

    # Check workspace disk usage
    if [[ -d "${WORKSPACE_DIR:-/workspace}" ]]; then
        disk_usage=$(df "${WORKSPACE_DIR:-/workspace}" | tail -1 | awk '{print $(NF-1)}' | sed 's/%//')
        if (( disk_usage > max_disk_usage )); then
            echo "High disk usage in workspace: ${disk_usage}%"
            return 1
        fi
    fi

    # Check root disk usage
    root_usage=$(df / | tail -1 | awk '{print $(NF-1)}' | sed 's/%//')
    if (( root_usage > max_disk_usage )); then
        echo "High root disk usage: ${root_usage}%"
        return 1
    fi

    return 0
}

# Agent-specific health checks
check_agent_specific() {
    case "$AGENT_TYPE" in
        "backend-developer")
            # Check if Python is available
            if ! command -v python3 >/dev/null 2>&1; then
                echo "Python3 not available for backend developer agent"
                return 1
            fi

            # Check if Node.js is available
            if ! command -v node >/dev/null 2>&1; then
                echo "Node.js not available for backend developer agent"
                return 1
            fi
            ;;
        "frontend-developer")
            # Check if Node.js is available
            if ! command -v node >/dev/null 2>&1; then
                echo "Node.js not available for frontend developer agent"
                return 1
            fi
            ;;
        "platform-engineer")
            # Check if Terraform is available
            if ! command -v terraform >/dev/null 2>&1; then
                echo "Terraform not available for platform engineer agent"
                return 1
            fi

            # Check if kubectl is available
            if ! command -v kubectl >/dev/null 2>&1; then
                echo "kubectl not available for platform engineer agent"
                return 1
            fi
            ;;
        "data-engineer")
            # Check if Python is available with data libraries
            if ! python3 -c "import pandas" 2>/dev/null; then
                echo "Pandas not available for data engineer agent"
                return 1
            fi
            ;;
        *)
            # Generic checks for other agents
            ;;
    esac

    return 0
}

# Network connectivity check
check_network() {
    # Check if we can resolve DNS
    if ! nslookup google.com >/dev/null 2>&1; then
        echo "DNS resolution failed"
        return 1
    fi

    return 0
}

# Main health check function
main() {
    local exit_code=0
    local checks_failed=()

    # Run all health checks
    if ! check_health "/health" "200"; then
        checks_failed+=("health_endpoint")
        exit_code=1
    fi

    if ! check_processes; then
        checks_failed+=("processes")
        exit_code=1
    fi

    if ! check_resources; then
        checks_failed+=("resources")
        exit_code=1
    fi

    if ! check_disk_space; then
        checks_failed+=("disk_space")
        exit_code=1
    fi

    if ! check_agent_specific; then
        checks_failed+=("agent_specific")
        exit_code=1
    fi

    if ! check_network; then
        checks_failed+=("network")
        exit_code=1
    fi

    # Report results
    if [[ $exit_code -eq 0 ]]; then
        echo "All health checks passed"
    else
        echo "Health checks failed: ${checks_failed[*]}"
    fi

    exit $exit_code
}

# Execute main function
main "$@"
