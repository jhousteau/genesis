# Genesis Claude-Talk MCP Server Container
# Containerized MCP server for Claude AI interaction with agent-cage integration
#
# This Dockerfile creates a lightweight, secure container for running the
# Claude-Talk MCP server with full container orchestration capabilities.

FROM node:18-alpine AS base

# Install system dependencies
RUN apk add --no-cache \
    curl \
    git \
    bash \
    docker-cli \
    jq

# Create app directory
WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Development stage
FROM base AS development

# Install all dependencies including dev dependencies
RUN npm ci

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/

# Build the application
RUN npm run build

# Production stage
FROM base AS production

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S claude-talk -u 1001

# Copy built application
COPY --from=development /app/dist ./dist
COPY --from=development /app/node_modules ./node_modules

# Create required directories
RUN mkdir -p /sessions /var/log/claude-talk && \
    chown -R claude-talk:nodejs /sessions /var/log/claude-talk /app

# Switch to non-root user
USER claude-talk

# Environment variables
ENV NODE_ENV=production
ENV MCP_SERVER_PORT=4000
ENV ADMIN_PORT=4001
ENV LOG_LEVEL=info
ENV CONTAINER_ISOLATION_ENABLED=true
ENV MAX_CONCURRENT_SESSIONS=10
ENV SESSION_TIMEOUT=3600000
ENV HEALTH_CHECK_INTERVAL=30000

# Expose ports
EXPOSE $MCP_SERVER_PORT $ADMIN_PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${ADMIN_PORT}/health || exit 1

# Entry point
COPY --chown=claude-talk:nodejs scripts/claude-talk-entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint

ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["server"]
