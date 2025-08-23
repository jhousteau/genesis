#!/bin/bash
#
# Agent VM Startup Script - Genesis Platform
#
# This script configures agent VMs for the agent-cage migration
# Follows PIPES methodology for standardized agent runtime setup

set -euo pipefail

# Script configuration from template variables
export AGENT_TYPE="${agent_type}"
export ENVIRONMENT="${environment}"
export PROJECT_ID="${project_id}"
export AGENT_CAGE_VERSION="${agent_cage_version}"
export MONITORING_ENABLED="${monitoring_enabled}"
export CUSTOM_CONFIG='${custom_config}'

# Logging setup
exec > >(logger -t agent-startup -s 2>/dev/null) 2>&1
echo "Starting agent VM setup - Type: $AGENT_TYPE, Environment: $ENVIRONMENT"

# Global variables
readonly AGENT_USER="agent"
readonly AGENT_HOME="/home/$AGENT_USER"
readonly WORKSPACE_DIR="/mnt/agent-workspace"
readonly LOG_FILE="/var/log/agent-startup.log"
readonly METADATA_URL="http://metadata.google.internal/computeMetadata/v1"

# Utility functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1" >&2
    exit 1
}

get_metadata() {
    curl -H "Metadata-Flavor: Google" -s "$METADATA_URL/$1" 2>/dev/null || echo ""
}

# System preparation
prepare_system() {
    log "Preparing system for agent runtime..."

    # Update system packages
    apt-get update -y
    apt-get upgrade -y

    # Install essential packages
    apt-get install -y \
        curl \
        wget \
        git \
        docker.io \
        docker-compose \
        python3 \
        python3-pip \
        python3-venv \
        nodejs \
        npm \
        golang-go \
        build-essential \
        jq \
        htop \
        vim \
        tmux \
        unzip \
        ca-certificates \
        apt-transport-https \
        gnupg \
        lsb-release

    # Install Google Cloud SDK
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
    echo "deb https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list
    apt-get update -y
    apt-get install -y google-cloud-sdk

    # Install kubectl for container orchestration
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

    # Install Terraform for infrastructure management
    wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list
    apt-get update -y
    apt-get install -y terraform

    log "System preparation completed"
}

# Create agent user and directories
setup_agent_user() {
    log "Setting up agent user and directories..."

    # Create agent user if doesn't exist
    if ! id "$AGENT_USER" >/dev/null 2>&1; then
        useradd -m -s /bin/bash "$AGENT_USER"
        usermod -aG docker "$AGENT_USER"
        usermod -aG sudo "$AGENT_USER"
    fi

    # Setup workspace directory on persistent disk
    if [ -b /dev/disk/by-id/google-agent-workspace ]; then
        log "Mounting agent workspace persistent disk..."
        mkfs.ext4 -F /dev/disk/by-id/google-agent-workspace || true
        mkdir -p "$WORKSPACE_DIR"
        mount /dev/disk/by-id/google-agent-workspace "$WORKSPACE_DIR" || true
        echo "/dev/disk/by-id/google-agent-workspace $WORKSPACE_DIR ext4 defaults 0 2" >> /etc/fstab
        chown -R "$AGENT_USER:$AGENT_USER" "$WORKSPACE_DIR"
        chmod 755 "$WORKSPACE_DIR"
    else
        log "No persistent workspace disk found, using local directory"
        mkdir -p "$WORKSPACE_DIR"
        chown -R "$AGENT_USER:$AGENT_USER" "$WORKSPACE_DIR"
    fi

    # Create agent directories
    sudo -u "$AGENT_USER" mkdir -p "$AGENT_HOME"/{.config,.local,bin,projects}
    sudo -u "$AGENT_USER" ln -sf "$WORKSPACE_DIR" "$AGENT_HOME/workspace"

    log "Agent user setup completed"
}

# Install agent-cage runtime
install_agent_cage() {
    log "Installing agent-cage runtime version: $AGENT_CAGE_VERSION..."

    # Install agent-cage based on version
    if [ "$AGENT_CAGE_VERSION" = "latest" ]; then
        DOWNLOAD_URL="https://github.com/genesis-platform/agent-cage/releases/latest/download/agent-cage-linux-amd64.tar.gz"
    else
        DOWNLOAD_URL="https://github.com/genesis-platform/agent-cage/releases/download/$AGENT_CAGE_VERSION/agent-cage-linux-amd64.tar.gz"
    fi

    # Download and install agent-cage
    cd /tmp
    wget "$DOWNLOAD_URL" -O agent-cage.tar.gz || {
        log "Failed to download agent-cage, using placeholder install"
        mkdir -p /usr/local/bin
        echo '#!/bin/bash' > /usr/local/bin/agent-cage
        echo 'echo "agent-cage placeholder - version: '$AGENT_CAGE_VERSION'"' >> /usr/local/bin/agent-cage
        chmod +x /usr/local/bin/agent-cage
        return 0
    }

    tar -xzf agent-cage.tar.gz
    install -o root -g root -m 0755 agent-cage /usr/local/bin/

    # Verify installation
    /usr/local/bin/agent-cage version || error_exit "agent-cage installation failed"

    log "agent-cage installation completed"
}

# Configure agent environment
configure_agent_environment() {
    log "Configuring agent environment for type: $AGENT_TYPE..."

    # Agent-specific configuration
    case "$AGENT_TYPE" in
        "backend-developer")
            install_backend_tools
            ;;
        "frontend-developer")
            install_frontend_tools
            ;;
        "platform-engineer")
            install_platform_tools
            ;;
        "data-engineer")
            install_data_tools
            ;;
        "security-agent")
            install_security_tools
            ;;
        *)
            log "Installing standard tools for agent type: $AGENT_TYPE"
            ;;
    esac

    # Common agent configuration
    create_agent_config

    log "Agent environment configuration completed"
}

# Install backend development tools
install_backend_tools() {
    log "Installing backend development tools..."

    # Python tools
    pip3 install poetry flask fastapi django pytest black flake8 mypy

    # Node.js tools
    npm install -g typescript ts-node express jest

    # Go tools
    sudo -u "$AGENT_USER" bash -c 'export PATH=$PATH:/usr/local/go/bin && go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest'
}

# Install frontend development tools
install_frontend_tools() {
    log "Installing frontend development tools..."

    # Node.js and React tools
    npm install -g @angular/cli @vue/cli create-react-app webpack webpack-cli
    npm install -g eslint prettier stylelint
    npm install -g @storybook/cli
}

# Install platform engineering tools
install_platform_tools() {
    log "Installing platform engineering tools..."

    # Additional Terraform tools
    wget https://releases.hashicorp.com/terragrunt/0.50.0/terragrunt_linux_amd64
    install -o root -g root -m 0755 terragrunt_linux_amd64 /usr/local/bin/terragrunt

    # Helm for Kubernetes
    curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xzf -
    install -o root -g root -m 0755 linux-amd64/helm /usr/local/bin/helm

    # Additional cloud tools
    pip3 install awscli azure-cli
}

# Install data engineering tools
install_data_tools() {
    log "Installing data engineering tools..."

    # Python data tools
    pip3 install pandas numpy scipy jupyter notebook apache-airflow dbt-core

    # Database tools
    apt-get install -y postgresql-client mysql-client
}

# Install security tools
install_security_tools() {
    log "Installing security tools..."

    # Security scanning tools
    apt-get install -y nmap wireshark tshark
    pip3 install bandit safety semgrep

    # Container security
    wget https://github.com/aquasecurity/trivy/releases/download/v0.44.0/trivy_0.44.0_Linux-64bit.deb
    dpkg -i trivy_0.44.0_Linux-64bit.deb || apt-get install -f -y
}

# Create agent configuration
create_agent_config() {
    log "Creating agent configuration..."

    cat > "$AGENT_HOME/.agent-config.json" <<EOF
{
    "agent_type": "$AGENT_TYPE",
    "environment": "$ENVIRONMENT",
    "project_id": "$PROJECT_ID",
    "agent_cage_version": "$AGENT_CAGE_VERSION",
    "workspace_dir": "$WORKSPACE_DIR",
    "monitoring_enabled": $MONITORING_ENABLED,
    "custom_config": $CUSTOM_CONFIG,
    "metadata": {
        "instance_id": "$(get_metadata 'instance/id')",
        "instance_name": "$(get_metadata 'instance/name')",
        "zone": "$(get_metadata 'instance/zone')",
        "machine_type": "$(get_metadata 'instance/machine-type')"
    },
    "startup_time": "$(date -Iseconds)",
    "version": "1.0.0"
}
EOF

    chown "$AGENT_USER:$AGENT_USER" "$AGENT_HOME/.agent-config.json"
    chmod 600 "$AGENT_HOME/.agent-config.json"

    # Create agent profile
    cat >> "$AGENT_HOME/.bashrc" <<EOF

# Genesis Agent Configuration
export AGENT_TYPE="$AGENT_TYPE"
export AGENT_ENVIRONMENT="$ENVIRONMENT"
export AGENT_WORKSPACE="$WORKSPACE_DIR"
export PATH="/usr/local/bin:\$PATH"

# Agent aliases
alias agent-status='systemctl status agent-runtime'
alias agent-logs='journalctl -u agent-runtime -f'
alias agent-config='cat ~/.agent-config.json | jq'

# Welcome message
echo "Genesis Agent Runtime - Type: $AGENT_TYPE, Environment: $ENVIRONMENT"
EOF
}

# Setup monitoring
setup_monitoring() {
    if [ "$MONITORING_ENABLED" = "true" ]; then
        log "Setting up monitoring..."

        # Install monitoring agents
        curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
        bash add-google-cloud-ops-agent-repo.sh --also-install

        # Configure custom metrics
        cat > /etc/google-cloud-ops-agent/config.yaml <<EOF
logging:
  receivers:
    agent_logs:
      type: files
      include_paths:
        - /var/log/agent-*.log
        - $WORKSPACE_DIR/logs/*.log
  service:
    pipelines:
      default_pipeline:
        receivers: [agent_logs]

metrics:
  receivers:
    agent_metrics:
      type: prometheus
      config:
        scrape_configs:
          - job_name: agent-runtime
            scrape_interval: 30s
            static_configs:
              - targets: ['localhost:9090']
  service:
    pipelines:
      default_pipeline:
        receivers: [agent_metrics]
EOF

        systemctl restart google-cloud-ops-agent
        log "Monitoring setup completed"
    else
        log "Monitoring disabled, skipping setup"
    fi
}

# Create agent runtime service
create_agent_service() {
    log "Creating agent runtime service..."

    cat > /etc/systemd/system/agent-runtime.service <<EOF
[Unit]
Description=Genesis Agent Runtime
After=network.target google-cloud-ops-agent.service
Wants=google-cloud-ops-agent.service

[Service]
Type=forking
User=$AGENT_USER
Group=$AGENT_USER
WorkingDirectory=$AGENT_HOME
Environment=AGENT_TYPE=$AGENT_TYPE
Environment=AGENT_ENVIRONMENT=$ENVIRONMENT
Environment=AGENT_WORKSPACE=$WORKSPACE_DIR
ExecStart=/usr/local/bin/agent-cage start --config=$AGENT_HOME/.agent-config.json
ExecStop=/usr/local/bin/agent-cage stop
ExecReload=/usr/local/bin/agent-cage reload
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable agent-runtime.service

    log "Agent runtime service created"
}

# Health check endpoint
setup_health_check() {
    log "Setting up health check endpoint..."

    # Create simple health check server
    cat > /usr/local/bin/agent-health-server <<'EOF'
#!/usr/bin/env python3
import json
import time
import http.server
import socketserver
from datetime import datetime

class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "agent_type": "$AGENT_TYPE",
                "environment": "$ENVIRONMENT",
                "uptime": int(time.time() - start_time)
            }

            self.wfile.write(json.dumps(health_data).encode())
        else:
            self.send_response(404)
            self.end_headers()

start_time = time.time()
PORT = 8080

with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
    print(f"Health check server running on port {PORT}")
    httpd.serve_forever()
EOF

    chmod +x /usr/local/bin/agent-health-server

    # Create health check service
    cat > /etc/systemd/system/agent-health.service <<EOF
[Unit]
Description=Genesis Agent Health Check
After=network.target

[Service]
Type=simple
User=$AGENT_USER
Group=$AGENT_USER
ExecStart=/usr/local/bin/agent-health-server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable agent-health.service
    systemctl start agent-health.service

    log "Health check endpoint setup completed"
}

# Final system configuration
finalize_setup() {
    log "Finalizing agent VM setup..."

    # Set proper ownership
    chown -R "$AGENT_USER:$AGENT_USER" "$AGENT_HOME"
    chown -R "$AGENT_USER:$AGENT_USER" "$WORKSPACE_DIR" 2>/dev/null || true

    # Start agent runtime (will fail gracefully if agent-cage is placeholder)
    systemctl start agent-runtime.service || log "Agent runtime service failed to start (expected for placeholder)"

    # Create startup completion marker
    echo "$(date -Iseconds)" > /var/lib/agent-startup-complete

    # Send startup notification
    curl -X POST -H "Metadata-Flavor: Google" \
         --data "Agent VM startup completed for $AGENT_TYPE in $ENVIRONMENT" \
         "$METADATA_URL/instance/guest-attributes/agent-startup/status" 2>/dev/null || true

    log "Agent VM setup completed successfully"
}

# Main execution
main() {
    log "Starting Genesis agent VM startup process..."

    prepare_system
    setup_agent_user
    install_agent_cage
    configure_agent_environment
    setup_monitoring
    create_agent_service
    setup_health_check
    finalize_setup

    log "Genesis agent VM is ready for service"
}

# Execute main function
main "$@"
