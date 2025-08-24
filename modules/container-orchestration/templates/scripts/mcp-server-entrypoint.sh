#!/bin/bash
set -euo pipefail

# Genesis MCP Server Container Entrypoint
# Handles configuration, secret loading, and graceful startup/shutdown

# Default values
MCP_CONFIG_PATH="${MCP_CONFIG_PATH:-/app/config/mcp-production.yaml}"
NODE_ENV="${NODE_ENV:-production}"
LOG_LEVEL="${LOG_LEVEL:-info}"
PORT="${PORT:-8080}"
METRICS_PORT="${METRICS_PORT:-8081}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] MCP-SERVER:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] MCP-SERVER ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] MCP-SERVER WARN:${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] MCP-SERVER:${NC} $1"
}

# Signal handlers for graceful shutdown
shutdown_handler() {
    log "Received shutdown signal, initiating graceful shutdown..."

    if [ ! -z "${MCP_SERVER_PID:-}" ]; then
        log "Stopping MCP server process (PID: $MCP_SERVER_PID)..."
        kill -TERM "$MCP_SERVER_PID" 2>/dev/null || true
        wait "$MCP_SERVER_PID" 2>/dev/null || true
    fi

    log "MCP server stopped gracefully"
    exit 0
}

trap shutdown_handler SIGTERM SIGINT

# Validate environment
validate_environment() {
    log "Validating environment configuration..."

    # Check required environment variables
    if [ -z "${PROJECT_ID:-}" ]; then
        error "PROJECT_ID environment variable is required"
        exit 1
    fi

    if [ -z "${ENVIRONMENT:-}" ]; then
        warn "ENVIRONMENT not set, defaulting to 'production'"
        export ENVIRONMENT="production"
    fi

    # Validate configuration file
    if [ ! -f "$MCP_CONFIG_PATH" ]; then
        error "MCP configuration file not found: $MCP_CONFIG_PATH"
        exit 1
    fi

    # Check if Secret Manager credentials are available
    if [ -f "/var/secrets/google/key.json" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="/var/secrets/google/key.json"
        log "Using service account credentials from mounted secret"
    elif [ ! -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
        if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
            error "Service account key file not found: $GOOGLE_APPLICATION_CREDENTIALS"
            exit 1
        fi
        log "Using service account credentials from environment"
    else
        warn "No explicit credentials found, using default authentication"
    fi

    success "Environment validation completed"
}

# Initialize secret access
initialize_secrets() {
    log "Initializing secret management..."

    # Test Secret Manager access
    if python3 -c "
import sys
sys.path.append('/app/core')
from secrets.manager import get_secret_manager
try:
    manager = get_secret_manager(project_id='$PROJECT_ID', environment='$ENVIRONMENT')
    print('Secret Manager connection successful')
except Exception as e:
    print(f'Secret Manager connection failed: {e}', file=sys.stderr)
    sys.exit(1)
"; then
        success "Secret Manager initialized successfully"
    else
        error "Failed to initialize Secret Manager"
        exit 1
    fi
}

# Prepare MCP server configuration
prepare_configuration() {
    log "Preparing MCP server configuration..."

    # Create runtime configuration directory
    mkdir -p /app/runtime/config

    # Process configuration template with environment variables
    if command -v envsubst >/dev/null 2>&1; then
        envsubst < "$MCP_CONFIG_PATH" > /app/runtime/config/mcp-runtime.yaml
        export MCP_RUNTIME_CONFIG="/app/runtime/config/mcp-runtime.yaml"
    else
        # Fallback: use original config file
        export MCP_RUNTIME_CONFIG="$MCP_CONFIG_PATH"
        warn "envsubst not available, using template configuration directly"
    fi

    # Validate configuration
    if ! node -e "
        const yaml = require('js-yaml');
        const fs = require('fs');
        try {
            const config = yaml.load(fs.readFileSync('$MCP_RUNTIME_CONFIG', 'utf8'));
            console.log('Configuration validation successful');
        } catch (error) {
            console.error('Configuration validation failed:', error.message);
            process.exit(1);
        }
    "; then
        error "MCP configuration validation failed"
        exit 1
    fi

    success "Configuration prepared successfully"
}

# Start MCP server
start_mcp_server() {
    log "Starting MCP server..."

    # Set Node.js options for production
    export NODE_OPTIONS="--max-old-space-size=2048 --unhandled-rejections=strict"

    # Create startup script
    cat > /app/runtime/start-server.js << 'EOF'
const { MCPServer, createSecretAuthBridge, setupMCPAuthWithSecrets } = require('./lib/javascript/@whitehorse/core');
const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');

async function startServer() {
    try {
        // Load configuration
        const configPath = process.env.MCP_RUNTIME_CONFIG || '/app/config/mcp-production.yaml';
        const config = yaml.load(fs.readFileSync(configPath, 'utf8'));

        // Setup Secret Manager authentication bridge
        const secretBridge = createSecretAuthBridge({
            projectId: process.env.PROJECT_ID,
            environment: process.env.ENVIRONMENT || 'production',
            pythonPath: 'python3',
            secretManagerScript: '/app/scripts/secret-shield-automation.py'
        });

        // Configure authentication strategies
        const authConfigs = [
            {
                name: 'jwt',
                config: {
                    type: 'jwt',
                    secretName: 'mcp-jwt-secret',
                    jwtConfig: {
                        issuer: 'genesis-mcp',
                        audience: 'claude-talk',
                        expiresIn: '1h'
                    }
                }
            },
            {
                name: 'api-key',
                config: {
                    type: 'api-key',
                    secretName: 'mcp-api-keys'
                }
            }
        ];

        // Setup authentication
        const strategies = await setupMCPAuthWithSecrets(secretBridge, authConfigs);

        // Create and configure MCP server
        const server = new MCPServer({
            port: parseInt(process.env.PORT || '8080'),
            host: '0.0.0.0',
            enableAuth: config.mcp?.auth?.enabled || true,
            enableWebSocket: config.mcp?.server?.enableWebSocket !== false,
            enableHttp: config.mcp?.server?.enableHttp !== false,
            maxConnections: config.mcp?.server?.maxConnections || 1000,
            requestTimeout: config.mcp?.server?.requestTimeout || 30000,
            corsOrigins: config.mcp?.server?.corsOrigins || ['*'],
            monitoring: {
                enabled: config.mcp?.monitoring?.enabled !== false,
                metricsPort: parseInt(process.env.METRICS_PORT || '8081')
            }
        });

        // Setup handlers for claude-talk integration
        server.registerHandler('claude-talk.session.create', async (request) => {
            return server.messageFactory.createResponse(request.id, {
                sessionId: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                status: 'created',
                timestamp: new Date().toISOString()
            });
        });

        server.registerHandler('claude-talk.agent.launch', async (request) => {
            const { agentType, configuration } = request.params;
            return server.messageFactory.createResponse(request.id, {
                agentId: `agent_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                agentType,
                status: 'launched',
                endpoint: `ws://localhost:${server.options.port}/ws/agent`,
                timestamp: new Date().toISOString()
            });
        });

        // Error handling
        server.on('error', (error) => {
            console.error('MCP Server error:', error);
        });

        server.on('started', () => {
            console.log(`MCP Server started successfully on port ${server.options.port}`);
            console.log(`Metrics available on port ${server.options.monitoring.metricsPort}`);
        });

        // Start the server
        await server.start();

        // Keep the process running
        process.on('SIGTERM', async () => {
            console.log('Received SIGTERM, shutting down gracefully...');
            await server.stop();
            process.exit(0);
        });

        process.on('SIGINT', async () => {
            console.log('Received SIGINT, shutting down gracefully...');
            await server.stop();
            process.exit(0);
        });

    } catch (error) {
        console.error('Failed to start MCP server:', error);
        process.exit(1);
    }
}

startServer();
EOF

    # Start the server in background
    cd /app
    node /app/runtime/start-server.js &
    MCP_SERVER_PID=$!
    export MCP_SERVER_PID

    # Wait for server to start
    log "Waiting for MCP server to be ready..."
    for i in {1..30}; do
        if curl -sf http://localhost:$PORT/health >/dev/null 2>&1; then
            success "MCP server is ready and responding"
            break
        fi

        if [ $i -eq 30 ]; then
            error "MCP server failed to start within timeout"
            exit 1
        fi

        sleep 2
    done
}

# Main execution
main() {
    log "Starting Genesis MCP Server container..."
    log "Configuration: $MCP_CONFIG_PATH"
    log "Environment: $NODE_ENV"
    log "Project ID: ${PROJECT_ID:-'not set'}"
    log "Port: $PORT"
    log "Metrics Port: $METRICS_PORT"

    validate_environment
    initialize_secrets
    prepare_configuration
    start_mcp_server

    success "MCP server initialization completed successfully"

    # Wait for server process
    wait "$MCP_SERVER_PID"
}

# Execute main function
main "$@"
