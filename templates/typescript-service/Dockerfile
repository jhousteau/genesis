# Genesis TypeScript Service Dockerfile
# Multi-stage build for optimized production container

# Build stage
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    git

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies (including dev dependencies for build)
RUN npm ci --include=dev

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/

# Build the application
RUN npm run build

# Remove dev dependencies and clean up
RUN npm prune --production && npm cache clean --force

# Production stage
FROM node:18-alpine AS production

# Create app user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Set working directory
WORKDIR /app

# Install production dependencies only
RUN apk add --no-cache \
    dumb-init \
    curl \
    && rm -rf /var/cache/apk/*

# Copy package files
COPY package*.json ./

# Install production dependencies only
RUN npm ci --production --ignore-scripts && \
    npm cache clean --force

# Copy built application from builder stage
COPY --from=builder /app/dist ./dist/

# Copy configuration files
COPY --chown=nodejs:nodejs src/config ./config/

# Create necessary directories
RUN mkdir -p /app/logs /app/temp && \
    chown -R nodejs:nodejs /app

# Switch to non-root user
USER nodejs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Set environment
ENV NODE_ENV=production
ENV PORT=8080
ENV GENESIS_ENVIRONMENT=production

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the application
CMD ["node", "dist/index.js"]

# Labels for metadata
LABEL maintainer="Genesis Platform Team"
LABEL description="Genesis TypeScript Service - {{PROJECT_DESCRIPTION}}"
LABEL version="1.0.0"
LABEL org.opencontainers.image.title="{{PROJECT_NAME}}"
LABEL org.opencontainers.image.description="{{PROJECT_DESCRIPTION}}"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.vendor="Genesis Platform"
LABEL org.opencontainers.image.source="{{REPOSITORY_URL}}"
