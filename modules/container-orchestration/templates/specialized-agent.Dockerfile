# Genesis Specialized Agent Container Template
# Flexible template for building agent-specific containers with customized toolchains
#
# This template supports all 12 Genesis agent types with build-time customization
# for optimal resource usage and security.

# Build arguments for customization
ARG BASE_IMAGE=ubuntu:22.04
ARG NODE_VERSION=18
ARG PYTHON_VERSION=3.11
ARG GO_VERSION=1.21
ARG AGENT_TYPE=backend-developer

FROM $BASE_IMAGE AS base

ARG DEBIAN_FRONTEND=noninteractive
ARG AGENT_TYPE

# Install base system packages
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    ca-certificates \
    gnupg \
    unzip \
    wget \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Conditional tool installation based on agent type
# Backend Developer Agent
FROM base AS backend-developer
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    golang \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install poetry flake8 black mypy pytest requests pyyaml && \
    npm install -g typescript ts-node @types/node eslint prettier jest

# Frontend Developer Agent
FROM base AS frontend-developer
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g \
    typescript \
    @angular/cli \
    @vue/cli \
    create-react-app \
    vite \
    webpack-cli \
    eslint \
    prettier \
    jest

# Platform Engineer Agent
FROM base AS platform-engineer
RUN apt-get update && apt-get install -y \
    docker.io \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

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

# Install Helm
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install gcloud CLI
RUN curl https://sdk.cloud.google.com | bash
ENV PATH="/root/google-cloud-sdk/bin:${PATH}"

# Data Engineer Agent
FROM base AS data-engineer
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    pandas \
    numpy \
    apache-beam \
    google-cloud-bigquery \
    google-cloud-storage \
    google-cloud-dataflow \
    dbt-bigquery \
    jupyter

# QA Automation Agent
FROM base AS qa-automation
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    nodejs \
    npm \
    chromium-browser \
    firefox \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install pytest selenium playwright requests && \
    npm install -g cypress jest puppeteer

# Security Agent
FROM base AS security
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    nmap \
    openssl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    bandit \
    safety \
    semgrep \
    checkov

# SRE Agent
FROM base AS sre
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    prometheus-client \
    grafana-api \
    pagerduty \
    google-cloud-monitoring

# DevOps Agent
FROM base AS devops
RUN apt-get update && apt-get install -y \
    docker.io \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    ansible \
    docker \
    google-cloud-build

# Integration Agent
FROM base AS integration
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    requests \
    httpx \
    pydantic \
    fastapi \
    celery

# Architect Agent
FROM base AS architect
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    diagrams \
    plantuml \
    pyyaml \
    jinja2

# Tech Lead Agent
FROM base AS tech-lead
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    nodejs \
    npm \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    flake8 \
    black \
    mypy \
    pylint \
    bandit && \
    npm install -g \
    eslint \
    prettier \
    jshint \
    tslint

# Project Manager Agent
FROM base AS project-manager
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    jira \
    github3.py \
    slack-sdk \
    pyyaml

# Select the appropriate stage based on agent type
FROM ${AGENT_TYPE} AS agent-runtime

# Create agent user
RUN useradd -m -s /bin/bash agent && \
    usermod -aG sudo agent || true

# Set up workspace
WORKDIR /workspace
RUN chown -R agent:agent /workspace

# Create directories
RUN mkdir -p /var/log/agent /home/agent/.cache /home/agent/.config && \
    chown -R agent:agent /var/log/agent /home/agent

# Switch to agent user
USER agent

# Environment variables
ENV AGENT_TYPE=${AGENT_TYPE}
ENV WORKSPACE_DIR=/workspace
ENV LOG_LEVEL=INFO
ENV METRICS_PORT=9090
ENV HEALTH_PORT=8080
ENV PYTHONPATH=/workspace:$PYTHONPATH
ENV NODE_PATH=/usr/local/lib/node_modules:$NODE_PATH

# Copy agent-specific configuration and scripts
COPY --chown=agent:agent config/${AGENT_TYPE}/ /home/agent/.config/
COPY --chown=agent:agent scripts/agent-entrypoint.sh /usr/local/bin/entrypoint
COPY --chown=agent:agent scripts/agent-healthcheck.sh /usr/local/bin/healthcheck

USER root
RUN chmod +x /usr/local/bin/entrypoint /usr/local/bin/healthcheck
USER agent

# Expose ports
EXPOSE $HEALTH_PORT $METRICS_PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/healthcheck

# Entry point
ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["agent-runtime"]
