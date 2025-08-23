#!/bin/bash
# Genesis Claude-Talk MCP Server Entrypoint
# Initializes and starts the Claude-Talk MCP server with container integration

set -euo pipefail

# Configuration
MCP_SERVER_PORT="${MCP_SERVER_PORT:-4000}"
ADMIN_PORT="${ADMIN_PORT:-4001}"
LOG_LEVEL="${LOG_LEVEL:-info}"
NODE_ENV="${NODE_ENV:-production}"
CONTAINER_ISOLATION_ENABLED="${CONTAINER_ISOLATION_ENABLED:-true}"
MAX_CONCURRENT_SESSIONS="${MAX_CONCURRENT_SESSIONS:-10}"

# Logging functions
log() {
    echo "[$(date -Iseconds)] [CLAUDE-TALK] $*" | tee -a /var/log/claude-talk/entrypoint.log
}

error() {
    echo "[$(date -Iseconds)] [ERROR] [CLAUDE-TALK] $*" >&2 | tee -a /var/log/claude-talk/entrypoint.log
    exit 1
}

# Initialize Claude-Talk environment
init_claude_talk() {
    log "Initializing Claude-Talk MCP Server"

    # Create required directories
    mkdir -p /sessions /var/log/claude-talk

    # Validate environment variables
    validate_environment

    # Initialize session storage
    init_session_storage

    # Set up container integration if enabled
    if [[ "$CONTAINER_ISOLATION_ENABLED" == "true" ]]; then
        init_container_integration
    fi
}

# Validate required environment variables
validate_environment() {
    log "Validating environment configuration"

    # Check for required environment variables
    if [[ -z "${CLAUDE_API_KEY:-}" ]]; then
        error "CLAUDE_API_KEY environment variable is required"
    fi

    if [[ -z "${PROJECT_ID:-}" ]]; then
        error "PROJECT_ID environment variable is required"
    fi

    # Validate ports
    if ! [[ "$MCP_SERVER_PORT" =~ ^[0-9]+$ ]] || (( MCP_SERVER_PORT < 1024 || MCP_SERVER_PORT > 65535 )); then
        error "Invalid MCP_SERVER_PORT: $MCP_SERVER_PORT"
    fi

    if ! [[ "$ADMIN_PORT" =~ ^[0-9]+$ ]] || (( ADMIN_PORT < 1024 || ADMIN_PORT > 65535 )); then
        error "Invalid ADMIN_PORT: $ADMIN_PORT"
    fi

    # Validate session limits
    if ! [[ "$MAX_CONCURRENT_SESSIONS" =~ ^[0-9]+$ ]] || (( MAX_CONCURRENT_SESSIONS < 1 )); then
        error "Invalid MAX_CONCURRENT_SESSIONS: $MAX_CONCURRENT_SESSIONS"
    fi

    log "Environment validation complete"
}

# Initialize session storage
init_session_storage() {
    log "Initializing session storage"

    # Create session directories
    mkdir -p /sessions/{active,archived,tmp}

    # Set proper permissions
    chmod 755 /sessions
    chmod 700 /sessions/active /sessions/archived /sessions/tmp

    # Clean up any stale sessions from previous runs
    if [[ -d /sessions/active ]]; then
        find /sessions/active -name "*.session" -mtime +1 -delete 2>/dev/null || true
    fi

    log "Session storage initialized"
}

# Initialize container integration
init_container_integration() {
    log "Initializing container integration"

    # Check if Docker is available
    if ! command -v docker >/dev/null 2>&1; then
        log "Warning: Docker not available, disabling container isolation"
        export CONTAINER_ISOLATION_ENABLED=false
        return
    fi

    # Test Docker connectivity
    if ! docker info >/dev/null 2>&1; then
        log "Warning: Cannot connect to Docker daemon, disabling container isolation"
        export CONTAINER_ISOLATION_ENABLED=false
        return
    fi

    # Verify agent-cage connectivity
    if ! check_agent_cage_connectivity; then
        log "Warning: Cannot connect to agent-cage, some features may be limited"
    fi

    log "Container integration initialized"
}

# Check agent-cage connectivity
check_agent_cage_connectivity() {
    # Try to connect to agent-cage service
    local agent_cage_host="${AGENT_CAGE_HOST:-agent-cage}"
    local agent_cage_port="${AGENT_CAGE_PORT:-8080}"

    if command -v curl >/dev/null 2>&1; then
        if curl -f -s --max-time 5 "http://$agent_cage_host:$agent_cage_port/health" >/dev/null 2>&1; then
            log "Agent-cage connectivity verified"
            return 0
        fi
    fi

    return 1
}

# Start health check server
start_health_server() {
    log "Starting admin/health server on port $ADMIN_PORT"

    cat > /tmp/admin_server.js << 'EOF'
const http = require('http');
const url = require('url');
const fs = require('fs');
const path = require('path');

const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);

    if (parsedUrl.pathname === '/health') {
        const health = {
            status: 'healthy',
            timestamp: new Date().toISOString(),
            service: 'claude-talk-mcp-server',
            version: '1.0.0',
            environment: process.env.NODE_ENV || 'production',
            container_isolation: process.env.CONTAINER_ISOLATION_ENABLED === 'true',
            max_sessions: parseInt(process.env.MAX_CONCURRENT_SESSIONS || '10'),
            active_sessions: getActiveSessionCount()
        };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(health, null, 2));
    } else if (parsedUrl.pathname === '/ready') {
        const ready = {
            ready: true,
            timestamp: new Date().toISOString()
        };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(ready));
    } else if (parsedUrl.pathname === '/sessions') {
        const sessions = {
            active: getActiveSessionCount(),
            max: parseInt(process.env.MAX_CONCURRENT_SESSIONS || '10'),
            sessions: listActiveSessions()
        };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(sessions, null, 2));
    } else {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not Found');
    }
});

function getActiveSessionCount() {
    try {
        const sessionDir = '/sessions/active';
        if (!fs.existsSync(sessionDir)) return 0;
        return fs.readdirSync(sessionDir).filter(file => file.endsWith('.session')).length;
    } catch (e) {
        return 0;
    }
}

function listActiveSessions() {
    try {
        const sessionDir = '/sessions/active';
        if (!fs.existsSync(sessionDir)) return [];
        return fs.readdirSync(sessionDir)
            .filter(file => file.endsWith('.session'))
            .map(file => {
                const filePath = path.join(sessionDir, file);
                const stat = fs.statSync(filePath);
                return {
                    id: file.replace('.session', ''),
                    created: stat.birthtime,
                    modified: stat.mtime
                };
            });
    } catch (e) {
        return [];
    }
}

const PORT = process.env.ADMIN_PORT || 4001;
server.listen(PORT, () => {
    console.log(`Admin server listening on port ${PORT}`);
});
EOF

    node /tmp/admin_server.js &
    ADMIN_PID=$!
    echo $ADMIN_PID > /tmp/admin_server.pid

    log "Admin server started with PID $ADMIN_PID"
}

# Start the main Claude-Talk MCP server
start_mcp_server() {
    log "Starting Claude-Talk MCP Server on port $MCP_SERVER_PORT"

    # Start the main application
    cd /app
    exec node dist/index.js
}

# Signal handlers for graceful shutdown
cleanup() {
    log "Received shutdown signal, performing graceful shutdown..."

    # Stop admin server
    if [[ -f /tmp/admin_server.pid ]]; then
        kill $(cat /tmp/admin_server.pid) 2>/dev/null || true
        rm -f /tmp/admin_server.pid
    fi

    # Archive active sessions
    if [[ -d /sessions/active ]] && [[ -n "$(ls -A /sessions/active)" ]]; then
        log "Archiving active sessions..."
        mv /sessions/active/* /sessions/archived/ 2>/dev/null || true
    fi

    log "Graceful shutdown complete"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Pre-flight checks
preflight_check() {
    log "Running pre-flight checks"

    # Check Node.js version
    node_version=$(node --version)
    log "Node.js version: $node_version"

    # Check if application files exist
    if [[ ! -f /app/dist/index.js ]]; then
        error "Application files not found in /app/dist/"
    fi

    # Check write permissions for session directory
    if [[ ! -w /sessions ]]; then
        error "Cannot write to sessions directory"
    fi

    # Check disk space
    available_space=$(df /sessions | tail -1 | awk '{print $(NF-1)}' | sed 's/%//')
    if (( available_space > 90 )); then
        log "Warning: Session storage disk usage is high: ${available_space}%"
    fi

    log "Pre-flight checks complete"
}

# Main execution
main() {
    log "Starting Genesis Claude-Talk MCP Server"
    log "MCP Server Port: $MCP_SERVER_PORT"
    log "Admin Port: $ADMIN_PORT"
    log "Log Level: $LOG_LEVEL"
    log "Container Isolation: $CONTAINER_ISOLATION_ENABLED"
    log "Max Concurrent Sessions: $MAX_CONCURRENT_SESSIONS"

    # Run pre-flight checks
    preflight_check

    # Initialize environment
    init_claude_talk

    # Start admin/health server
    start_health_server

    log "Claude-Talk initialization complete"

    # Handle different commands
    if [[ $# -eq 0 ]] || [[ "$1" == "server" ]]; then
        start_mcp_server
    else
        log "Executing command: $*"
        exec "$@"
    fi
}

# Execute main function
main "$@"
