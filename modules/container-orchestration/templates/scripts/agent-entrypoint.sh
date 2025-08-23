#!/bin/bash
# Genesis Agent Runtime Entrypoint
# Initializes and starts the agent runtime with proper configuration

set -euo pipefail

# Configuration
AGENT_TYPE="${AGENT_TYPE:-backend-developer}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
HEALTH_PORT="${HEALTH_PORT:-8080}"
METRICS_PORT="${METRICS_PORT:-9090}"

# Logging functions
log() {
    echo "[$(date -Iseconds)] [AGENT-ENTRYPOINT] $*" | tee -a /var/log/agent/entrypoint.log
}

error() {
    echo "[$(date -Iseconds)] [ERROR] [AGENT-ENTRYPOINT] $*" >&2 | tee -a /var/log/agent/entrypoint.log
    exit 1
}

# Initialize agent environment
init_agent() {
    log "Initializing Genesis Agent: $AGENT_TYPE"

    # Create log directory
    sudo mkdir -p /var/log/agent
    sudo chown agent:agent /var/log/agent

    # Initialize workspace
    if [[ ! -d "$WORKSPACE_DIR" ]]; then
        mkdir -p "$WORKSPACE_DIR"
    fi

    # Set up agent-specific environment
    case "$AGENT_TYPE" in
        "backend-developer")
            init_backend_developer
            ;;
        "frontend-developer")
            init_frontend_developer
            ;;
        "platform-engineer")
            init_platform_engineer
            ;;
        "data-engineer")
            init_data_engineer
            ;;
        "qa-automation")
            init_qa_automation
            ;;
        "security")
            init_security
            ;;
        "sre")
            init_sre
            ;;
        "devops")
            init_devops
            ;;
        "integration")
            init_integration
            ;;
        "architect")
            init_architect
            ;;
        "tech-lead")
            init_tech_lead
            ;;
        "project-manager")
            init_project_manager
            ;;
        *)
            log "Unknown agent type: $AGENT_TYPE, using default configuration"
            ;;
    esac
}

# Agent-specific initialization functions
init_backend_developer() {
    log "Setting up Backend Developer Agent environment"

    # Python environment
    if [[ -f "$WORKSPACE_DIR/pyproject.toml" ]]; then
        cd "$WORKSPACE_DIR"
        poetry install --no-dev || log "Poetry install failed, continuing..."
    fi

    # Node.js environment
    if [[ -f "$WORKSPACE_DIR/package.json" ]]; then
        cd "$WORKSPACE_DIR"
        npm ci --production || log "npm ci failed, continuing..."
    fi

    # Go environment
    if [[ -f "$WORKSPACE_DIR/go.mod" ]]; then
        cd "$WORKSPACE_DIR"
        go mod download || log "go mod download failed, continuing..."
    fi
}

init_frontend_developer() {
    log "Setting up Frontend Developer Agent environment"

    if [[ -f "$WORKSPACE_DIR/package.json" ]]; then
        cd "$WORKSPACE_DIR"
        npm ci --production || log "npm ci failed, continuing..."
    fi

    # Set up development server if needed
    export REACT_APP_API_URL="${REACT_APP_API_URL:-http://localhost:8080}"
    export VUE_APP_API_URL="${VUE_APP_API_URL:-http://localhost:8080}"
}

init_platform_engineer() {
    log "Setting up Platform Engineer Agent environment"

    # Initialize Terraform
    if [[ -d "$WORKSPACE_DIR/terraform" ]]; then
        cd "$WORKSPACE_DIR/terraform"
        terraform init -backend=false || log "Terraform init failed, continuing..."
    fi

    # Initialize kubectl context
    if [[ -f /home/agent/.kube/config ]]; then
        kubectl cluster-info || log "kubectl cluster-info failed, continuing..."
    fi
}

init_data_engineer() {
    log "Setting up Data Engineer Agent environment"

    # Python environment for data tools
    if [[ -f "$WORKSPACE_DIR/requirements.txt" ]]; then
        pip3 install --user -r "$WORKSPACE_DIR/requirements.txt" || log "pip install failed, continuing..."
    fi
}

init_qa_automation() {
    log "Setting up QA Automation Agent environment"

    # Install test dependencies
    if [[ -f "$WORKSPACE_DIR/requirements.txt" ]]; then
        pip3 install --user -r "$WORKSPACE_DIR/requirements.txt" || log "pip install failed, continuing..."
    fi

    if [[ -f "$WORKSPACE_DIR/package.json" ]]; then
        cd "$WORKSPACE_DIR"
        npm ci --production || log "npm ci failed, continuing..."
    fi

    # Set up browser drivers
    export DISPLAY=:99
    export CHROME_BIN=/usr/bin/chromium-browser
    export FIREFOX_BIN=/usr/bin/firefox
}

init_security() {
    log "Setting up Security Agent environment"

    # Initialize security scanning tools
    log "Security tools initialized"
}

init_sre() {
    log "Setting up SRE Agent environment"

    # Set up monitoring tools
    log "SRE monitoring tools initialized"
}

init_devops() {
    log "Setting up DevOps Agent environment"

    # Initialize deployment tools
    log "DevOps tools initialized"
}

init_integration() {
    log "Setting up Integration Agent environment"

    # Set up API client configurations
    log "Integration tools initialized"
}

init_architect() {
    log "Setting up Architect Agent environment"

    # Initialize architecture documentation tools
    log "Architecture tools initialized"
}

init_tech_lead() {
    log "Setting up Tech Lead Agent environment"

    # Initialize code quality tools
    log "Tech Lead tools initialized"
}

init_project_manager() {
    log "Setting up Project Manager Agent environment"

    # Initialize project management tools
    log "Project Manager tools initialized"
}

# Health check endpoint
start_health_server() {
    log "Starting health check server on port $HEALTH_PORT"

    cat > /tmp/health_server.py << 'EOF'
import http.server
import socketserver
import json
import os
import sys
from datetime import datetime

class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "agent_type": os.environ.get('AGENT_TYPE', 'unknown'),
                "workspace": os.environ.get('WORKSPACE_DIR', '/workspace'),
                "version": "1.0.0"
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
        elif self.path == '/ready':
            # Check if agent is ready to accept work
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ready": True}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default logging

if __name__ == '__main__':
    PORT = int(os.environ.get('HEALTH_PORT', 8080))
    with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
        httpd.serve_forever()
EOF

    python3 /tmp/health_server.py &
    HEALTH_PID=$!
    echo $HEALTH_PID > /tmp/health_server.pid
}

# Metrics endpoint
start_metrics_server() {
    log "Starting metrics server on port $METRICS_PORT"

    cat > /tmp/metrics_server.py << 'EOF'
import http.server
import socketserver
import os
import psutil
import json
from datetime import datetime

class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            # Prometheus-style metrics
            metrics = f"""# HELP agent_cpu_usage_percent CPU usage percentage
# TYPE agent_cpu_usage_percent gauge
agent_cpu_usage_percent {psutil.cpu_percent()}

# HELP agent_memory_usage_bytes Memory usage in bytes
# TYPE agent_memory_usage_bytes gauge
agent_memory_usage_bytes {psutil.virtual_memory().used}

# HELP agent_memory_total_bytes Total memory in bytes
# TYPE agent_memory_total_bytes gauge
agent_memory_total_bytes {psutil.virtual_memory().total}

# HELP agent_uptime_seconds Agent uptime in seconds
# TYPE agent_uptime_seconds counter
agent_uptime_seconds {psutil.boot_time()}
"""

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(metrics.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    PORT = int(os.environ.get('METRICS_PORT', 9090))
    with socketserver.TCPServer(("", PORT), MetricsHandler) as httpd:
        httpd.serve_forever()
EOF

    pip3 install --user psutil || log "Failed to install psutil for metrics"
    python3 /tmp/metrics_server.py &
    METRICS_PID=$!
    echo $METRICS_PID > /tmp/metrics_server.pid
}

# Signal handlers for graceful shutdown
cleanup() {
    log "Received shutdown signal, cleaning up..."

    if [[ -f /tmp/health_server.pid ]]; then
        kill $(cat /tmp/health_server.pid) 2>/dev/null || true
    fi

    if [[ -f /tmp/metrics_server.pid ]]; then
        kill $(cat /tmp/metrics_server.pid) 2>/dev/null || true
    fi

    log "Cleanup complete"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Main execution
main() {
    log "Starting Genesis Agent Runtime"
    log "Agent Type: $AGENT_TYPE"
    log "Workspace: $WORKSPACE_DIR"
    log "Log Level: $LOG_LEVEL"

    # Initialize agent
    init_agent

    # Start health and metrics servers
    start_health_server
    start_metrics_server

    log "Agent initialization complete"

    # Keep the container running
    if [[ $# -eq 0 ]] || [[ "$1" == "agent-runtime" ]]; then
        log "Starting agent runtime loop"
        while true; do
            sleep 30
            log "Agent runtime heartbeat - $(date -Iseconds)"
        done
    else
        log "Executing command: $*"
        exec "$@"
    fi
}

# Execute main function
main "$@"
