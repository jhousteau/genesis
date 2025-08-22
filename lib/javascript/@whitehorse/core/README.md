# @whitehorse/core

Industrial-strength core library for the Universal Project Platform. Provides comprehensive utilities for building cloud-native Node.js applications with TypeScript support.

## Features

- **Structured Logging**: Winston-based logging with correlation IDs and GCP Cloud Logging integration
- **Configuration Management**: Multi-source configuration with validation and GCP Secret Manager
- **Error Handling**: Comprehensive error handling with circuit breakers and retry policies
- **Type Safety**: Complete TypeScript definitions for all APIs
- **Observability**: Built-in metrics, tracing, and health checking
- **Cloud Integration**: Deep GCP integration for logging, secrets, and monitoring
- **Developer Experience**: Rich debugging tools and interactive development features

## Installation

```bash
npm install @whitehorse/core

# With optional peer dependencies for full functionality
npm install @whitehorse/core @google-cloud/logging @google-cloud/secret-manager redis
```

## Quick Start

```typescript
import { createLogger, loadConfig, ApiClient } from '@whitehorse/core';

// Initialize logger
const logger = createLogger('my-service', {
  level: 'info',
  enableGcp: true,
  gcpProjectId: 'my-gcp-project'
});

// Load configuration
const config = await loadConfig({
  configFile: 'config.yaml',
  secretsEnabled: true,
  gcpProjectId: 'my-gcp-project'
});

// Use structured logging
logger.info('Service starting', { version: '1.0.0' });

// Performance logging
const operation = logger.timing('database_query', async () => {
  // Your database operation
  return await db.query('SELECT * FROM users');
});

logger.info('Service started successfully');
```

## Configuration

### Environment Variables

```bash
# Service identification
SERVICE_NAME=my-service
SERVICE_VERSION=1.0.0
NODE_ENV=development

# GCP configuration
GCP_PROJECT=my-gcp-project
GCP_REGION=us-central1

# Logging
LOG_LEVEL=info
ENABLE_STRUCTURED_LOGGING=true
ENABLE_GCP_LOGGING=true

# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=myapp
DATABASE_USER=myuser
DATABASE_PASSWORD=mypassword

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Security
JWT_SECRET=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key
```

### Configuration Files

Support for multiple configuration formats:

**config.json**
```json
{
  "serviceName": "my-service",
  "environment": "development",
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "myapp"
  },
  "redis": {
    "host": "localhost",
    "port": 6379
  }
}
```

**config.yaml**
```yaml
serviceName: my-service
environment: development
database:
  host: localhost
  port: 5432
  name: myapp
redis:
  host: localhost
  port: 6379
```

## API Reference

### Logging

```typescript
import { createLogger, setupLogging, correlationMiddleware } from '@whitehorse/core';

// Create logger
const logger = createLogger('my-service');

// Structured logging
logger.info('User logged in', { userId: '123', ip: '192.168.1.1' });
logger.error('Database connection failed', { error: err.message });

// Performance logging
const timer = logger.timing('api_call', () => {
  return api.call();
});

// Correlation ID middleware (Express)
app.use(correlationMiddleware());

// Context logging
logger.withContext(ctx).info('Processing request');
```

### Configuration

```typescript
import { ConfigManager, getConfig, Config } from '@whitehorse/core';

// Load configuration
const config = await loadConfig({
  configFile: 'config.yaml',
  secretsEnabled: true,
  gcpProjectId: 'my-project'
});

// Access configuration
const dbHost = config.get('database.host');
const apiKey = config.get('api.key', 'default-key');

// Check configuration
if (config.has('redis.password')) {
  // Redis password is configured
}

// Environment-aware configuration
const envConfig = new EnvironmentAwareConfig(config);
const dbConfig = envConfig.getForEnvironment('database');
const featureFlag = envConfig.getFeatureFlag('new_feature', false);
```

### Error Handling

```typescript
import { 
  WhitehorseError, 
  ValidationError, 
  NetworkError,
  CircuitBreaker,
  retry
} from '@whitehorse/core';

// Create custom errors
throw new ValidationError('Invalid email format', 'email');
throw new NetworkError('Connection timeout', { url: 'https://api.example.com' });

// Wrap existing errors
try {
  await riskyOperation();
} catch (err) {
  throw new WhitehorseError('Operation failed', {
    cause: err,
    severity: ErrorSeverity.HIGH,
    recoverable: true
  });
}

// Circuit breaker
const breaker = new CircuitBreaker({
  threshold: 5,
  timeout: 60000
});

const result = await breaker.execute(async () => {
  return await externalApi.call();
});

// Retry with exponential backoff
const result = await retry(() => unreliableOperation(), {
  attempts: 3,
  delay: 1000,
  backoff: 'exponential'
});
```

### API Client

```typescript
import { ApiClient, HttpClient } from '@whitehorse/core';

// Create HTTP client
const client = new HttpClient({
  baseURL: 'https://api.example.com',
  timeout: 30000,
  retryAttempts: 3
});

// Make requests
const response = await client.get('/users', {
  params: { page: 1, limit: 10 }
});

const user = await client.post('/users', {
  name: 'John Doe',
  email: 'john@example.com'
});

// API client with authentication
const apiClient = new ApiClient({
  baseURL: 'https://api.example.com',
  auth: {
    type: 'bearer',
    token: 'your-token'
  }
});
```

### Health Checking

```typescript
import { HealthChecker } from '@whitehorse/core';

const healthChecker = new HealthChecker();

// Register health checks
healthChecker.register({
  name: 'database',
  check: async () => {
    await db.ping();
    return { status: 'healthy' };
  },
  interval: 30000
});

healthChecker.register({
  name: 'redis',
  check: async () => {
    await redis.ping();
    return { status: 'healthy' };
  },
  interval: 10000
});

// Get health status
const health = await healthChecker.getHealth();
console.log(health.overall); // 'healthy', 'degraded', or 'unhealthy'
```

### Storage

```typescript
import { StorageClient, GCSStorage } from '@whitehorse/core';

// GCS storage
const storage = new GCSStorage({
  bucketName: 'my-bucket',
  projectId: 'my-project'
});

// Upload file
await storage.upload('path/to/file.txt', Buffer.from('Hello, World!'));

// Download file
const content = await storage.download('path/to/file.txt');

// List files
const files = await storage.list('path/to/directory/');
```

### Caching

```typescript
import { CacheManager, RedisCache, MemoryCache } from '@whitehorse/core';

// Redis cache
const cache = new RedisCache({
  host: 'localhost',
  port: 6379
});

// Set value with TTL
await cache.set('user:123', { name: 'John' }, 3600);

// Get value
const user = await cache.get('user:123');

// Memory cache (for development)
const memCache = new MemoryCache({ maxSize: 1000 });
```

### Metrics

```typescript
import { MetricsCollector } from '@whitehorse/core';

const metrics = new MetricsCollector({
  serviceName: 'my-service',
  enablePrometheus: true
});

// Counter
metrics.incrementCounter('requests_total', 1, { method: 'GET', status: '200' });

// Gauge
metrics.setGauge('active_connections', 42);

// Histogram
metrics.recordDuration('request_duration', 150, { endpoint: '/api/users' });

// Custom metric
metrics.recordMetric('custom_metric', 100, { type: 'business' });
```

## Middleware

### Express Integration

```typescript
import express from 'express';
import { correlationMiddleware, errorMiddleware, metricsMiddleware } from '@whitehorse/core';

const app = express();

// Add correlation ID to all requests
app.use(correlationMiddleware());

// Add metrics collection
app.use(metricsMiddleware());

// Your routes
app.get('/api/users', (req, res) => {
  res.json({ users: [] });
});

// Error handling middleware (add last)
app.use(errorMiddleware());
```

### Custom Middleware

```typescript
import { getLogger } from '@whitehorse/core';

const logger = getLogger(__name__);

// Request logging middleware
export const requestLogger = (req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.info('HTTP request', {
      method: req.method,
      path: req.path,
      statusCode: res.statusCode,
      duration,
      userAgent: req.get('User-Agent'),
      ip: req.ip
    });
  });
  
  next();
};
```

## TypeScript Support

Full TypeScript support with comprehensive type definitions:

```typescript
import { BaseConfig, ApiResponse, HealthStatus, LogLevel } from '@whitehorse/core';

// Extend base configuration
interface AppConfig extends BaseConfig {
  database: {
    host: string;
    port: number;
    name: string;
  };
  redis: {
    host: string;
    port: number;
  };
}

// Type-safe API responses
const response: ApiResponse<User[]> = await api.get('/users');
const users = response.data; // Type: User[]

// Health check results
const health: HealthStatus = await healthChecker.getHealth();
```

## Development

### Setup

```bash
git clone <repository>
cd lib/javascript/@whitehorse/core
npm install
```

### Scripts

```bash
# Build TypeScript
npm run build

# Watch mode
npm run build:watch

# Run tests
npm test
npm run test:watch
npm run test:coverage

# Linting
npm run lint
npm run lint:fix

# Documentation
npm run docs
```

### Testing

```typescript
import { createLogger } from '@whitehorse/core';

describe('Logger', () => {
  it('should create logger with default options', () => {
    const logger = createLogger('test-service');
    expect(logger).toBeDefined();
    expect(logger.getLevel()).toBe('info');
  });

  it('should log with correlation ID', () => {
    const logger = createLogger('test-service');
    logger.withCorrelationID('test-123', () => {
      logger.info('Test message');
      // Assert log output contains correlation ID
    });
  });
});
```

## Examples

See the `examples/` directory for complete examples:

- **Express API**: RESTful API with full middleware stack
- **Worker Service**: Background job processing
- **CLI Tool**: Command-line interface with rich logging
- **Microservice**: Complete microservice with all features

## Best Practices

1. **Use structured logging** with consistent field names
2. **Include correlation IDs** for request tracing
3. **Handle errors gracefully** with proper categorization
4. **Monitor application health** with comprehensive checks
5. **Secure sensitive data** using Secret Manager
6. **Use TypeScript** for better development experience
7. **Follow naming conventions** for metrics and logs

## Performance

The library is designed for high-performance applications:

- **Async/await support** throughout
- **Connection pooling** for databases and external services
- **Efficient logging** with minimal overhead
- **Memory management** with configurable limits
- **Metrics collection** with low latency impact

## License

MIT License - see LICENSE file for details.