# Genesis Agent-Cage Runtime Container
# Multi-stage build for optimized agent execution environment
#
# This Dockerfile creates a containerized runtime environment for Genesis agents,
# supporting all 12 agent types with their specific toolchains and dependencies.

FROM node:18-bullseye-slim AS node-base

# Install Node.js dependencies and tools
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

FROM python:3.11-bullseye AS python-base

# Install Python dependencies and system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    jq \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry for Python dependency management
RUN pip install --no-cache-dir poetry

FROM golang:1.21-bullseye AS go-base

# Install Go dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Multi-language runtime base
FROM ubuntu:22.04 AS runtime-base

ARG DEBIAN_FRONTEND=noninteractive

# Install base system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    jq \
    ca-certificates \
    gnupg \
    lsb-release \
    unzip \
    wget \
    vim \
    htop \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Install Terraform
ARG TERRAFORM_VERSION=1.6.6
RUN wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    mv terraform /usr/local/bin/ && \
    rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip

# Install kubectl
ARG KUBECTL_VERSION=v1.28.4
RUN curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

# Install gcloud CLI
RUN curl https://sdk.cloud.google.com | bash
ENV PATH="/root/google-cloud-sdk/bin:${PATH}"

# Copy language runtimes
COPY --from=node-base /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-base /usr/local/bin/node /usr/local/bin/
COPY --from=node-base /usr/local/bin/npm /usr/local/bin/
COPY --from=node-base /usr/local/bin/npx /usr/local/bin/

COPY --from=python-base /usr/local/bin/python3 /usr/local/bin/
COPY --from=python-base /usr/local/bin/pip3 /usr/local/bin/
COPY --from=python-base /usr/local/bin/poetry /usr/local/bin/
COPY --from=python-base /usr/local/lib/python3.11 /usr/local/lib/python3.11

COPY --from=go-base /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:${PATH}"

# Create agent user
RUN useradd -m -s /bin/bash agent && \
    usermod -aG docker agent

# Set up workspace
WORKDIR /workspace
RUN chown -R agent:agent /workspace

# Create directories
RUN mkdir -p /var/log/agent-cage /home/agent/.cache /home/agent/.config && \
    chown -R agent:agent /var/log/agent-cage /home/agent

USER agent

# Install common development tools
RUN npm install -g typescript ts-node @types/node eslint prettier jest && \
    pip3 install --user flake8 black mypy pytest requests pyyaml

# Environment variables
ENV AGENT_TYPE=backend-developer
ENV WORKSPACE_DIR=/workspace
ENV LOG_LEVEL=INFO
ENV METRICS_PORT=9090
ENV HEALTH_PORT=8080
ENV AGENT_POOL_SIZE=1
ENV PYTHONPATH=/workspace:$PYTHONPATH
ENV NODE_PATH=/usr/local/lib/node_modules:$NODE_PATH

# Health check script
COPY --chown=agent:agent scripts/agent-healthcheck.sh /usr/local/bin/healthcheck
RUN chmod +x /usr/local/bin/healthcheck

# Agent runtime entry point
COPY --chown=agent:agent scripts/agent-entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint

# Expose ports
EXPOSE $HEALTH_PORT $METRICS_PORT 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/healthcheck

# Entry point
ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["agent-runtime"]
