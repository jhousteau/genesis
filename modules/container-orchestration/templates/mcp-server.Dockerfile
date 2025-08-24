# Genesis MCP Server Container
# Multi-stage build for optimal size and security

FROM node:18-alpine AS builder
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache python3 make g++

# Copy package files
COPY package*.json ./
COPY lib/javascript/@whitehorse/core/package*.json ./lib/javascript/@whitehorse/core/

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY lib/javascript/@whitehorse/core ./lib/javascript/@whitehorse/core
COPY scripts ./scripts

# Build TypeScript
RUN cd lib/javascript/@whitehorse/core && npm run build

# Production stage
FROM node:18-alpine AS production
WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S mcpuser && adduser -S mcpuser -u 1001

# Install runtime dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    jq \
    && rm -rf /var/cache/apk/*

# Install Python dependencies for Secret Manager integration
COPY requirements.txt ./
RUN pip3 install -r requirements.txt

# Copy built application
COPY --from=builder --chown=mcpuser:mcpuser /app/node_modules ./node_modules
COPY --from=builder --chown=mcpuser:mcpuser /app/lib ./lib
COPY --from=builder --chown=mcpuser:mcpuser /app/scripts ./scripts

# Copy configuration templates
COPY config/mcp-*.yaml ./config/
COPY core/secrets ./core/secrets

# Create necessary directories
RUN mkdir -p /app/logs /app/temp /app/data && \
    chown -R mcpuser:mcpuser /app

# Expose MCP server port and metrics port
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Switch to non-root user
USER mcpuser

# Environment variables
ENV NODE_ENV=production
ENV MCP_CONFIG_PATH=/app/config/mcp-production.yaml
ENV PYTHONPATH=/app/core:/app/scripts

# Start script
COPY --chown=mcpuser:mcpuser modules/container-orchestration/templates/scripts/mcp-server-entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
