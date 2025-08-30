# @genesis/typescript

Genesis TypeScript shared utilities for retry, logging, config, health, errors, and context management.

## Installation

```bash
npm install @genesis/typescript
```

## Quick Start

```typescript
import {
  getLogger,
  loadConfig,
  HealthCheck,
  retry,
  getContext,
  handleError
} from '@genesis/typescript';

// Logging
const logger = getLogger('my-service');
logger.info('Service starting', { version: '1.0.0' });

// Configuration
const config = loadConfig('config.yml', 'APP_');
const dbUrl = config.database?.url || 'localhost:5432';

// Health checks
const health = new HealthCheck();
health.addCheck('database', async () => ({
  name: 'database',
  status: HealthStatus.HEALTHY,
  message: 'Connected'
}));

// Retry with circuit breaker
class ApiService {
  @resilientExternalService()
  async fetchData() {
    // This method will be retried with exponential backoff
    // and protected by a circuit breaker
    return fetch('/api/data');
  }
}

// Context management
import { contextSpan, createRequestContext } from '@genesis/typescript';

const context = createRequestContext({ userId: 'user-123' });
await contextSpan(context, async () => {
  // All operations in this scope share the same request context
  logger.info('Processing request'); // Automatically includes correlation ID
});
```

## Core Modules

### Configuration (`config`)
- YAML file loading with environment variable overrides
- Type-safe configuration classes
- Predefined configuration presets

```typescript
import { loadConfig, TypedConfig } from '@genesis/typescript';

// Simple usage
const config = loadConfig('config.yml', 'APP_');

// Type-safe configuration
class AppConfig extends TypedConfig<{ port: number; dbUrl: string }> {
  protected validate(raw: any) {
    return {
      port: Number(raw.port) || 3000,
      dbUrl: raw.database_url || 'localhost:5432'
    };
  }
}
```

### Logging (`logger`)
- Structured JSON logging
- Automatic context inclusion (correlation IDs, user IDs, etc.)
- Multiple log levels and presets

```typescript
import { getLogger, LoggerPresets } from '@genesis/typescript';

const logger = getLogger('my-service', LoggerPresets.production());
logger.info('User action', { userId: '123', action: 'login' });
```

### Health Checks (`health`)
- Simple health check coordinator
- Built-in checks for common resources (HTTP, memory, etc.)
- Overall status aggregation

```typescript
import { HealthCheck, HealthChecks } from '@genesis/typescript';

const health = new HealthCheck();
health.addCheck('api', () => HealthChecks.httpEndpoint('http://api.example.com/health'));
health.addCheck('memory', () => HealthChecks.memory(512)); // 512MB limit

const summary = await health.getSummary();
```

### Retry & Circuit Breaker (`retry`)
- Exponential backoff with jitter
- Circuit breaker pattern for failing services
- Decorator and function-based APIs
- Pre-configured patterns for external services and databases

```typescript
import { retry, resilientExternalService, retryFunction } from '@genesis/typescript';

// Decorator usage
class Service {
  @resilientExternalService()
  async callApi() {
    return fetch('/api/endpoint');
  }
}

// Function usage
const result = await retryFunction(
  () => fetch('/api/data'),
  { maxAttempts: 3, initialDelay: 1000 }
);
```

### Error Handling (`errors`)
- Structured error classes with categories and severity
- Automatic error context enrichment
- Error conversion and handling utilities

```typescript
import { ValidationError, handleError, NetworkError } from '@genesis/typescript';

// Throw structured errors
throw new ValidationError('Invalid email format', 'email');

// Handle any error
try {
  // risky operation
} catch (error) {
  const genesisError = handleError(error);
  logger.error('Operation failed', {
    error: genesisError.toJSON()
  });
}
```

### Context Management (`context`)
- Request correlation across async operations
- Distributed tracing support
- Automatic context propagation
- Express middleware integration

```typescript
import {
  contextSpan,
  createRequestContext,
  getCorrelationId,
  createContextMiddleware
} from '@genesis/typescript';

// Create and use context
const context = createRequestContext({ userId: 'user-123' });
await contextSpan(context, async () => {
  const correlationId = getCorrelationId(); // Available in all nested calls
  await someAsyncOperation();
});

// Express middleware
app.use(createContextMiddleware({
  generateCorrelationId: true,
  extractUserId: (req) => req.user?.id
}));
```

## TypeScript Support

All modules are written in TypeScript with full type definitions. The library provides:

- Complete type safety for all APIs
- Generic configuration classes
- Typed health check results
- Type-safe error handling

## Usage Patterns

### Microservice Setup

```typescript
import {
  getLogger,
  loadConfig,
  HealthCheck,
  HealthChecks,
  createContextMiddleware
} from '@genesis/typescript';

// Load configuration
const config = loadConfig('config.yml', 'SERVICE_');

// Setup logging
const logger = getLogger('my-service');

// Setup health checks
const health = new HealthCheck();
health.addCheck('database', () => HealthChecks.database(testDbConnection));
health.addCheck('memory', () => HealthChecks.memory(512));

// Express app with context middleware
app.use(createContextMiddleware({ generateCorrelationId: true }));
app.get('/health', async (req, res) => {
  const summary = await health.getSummary();
  res.json(summary);
});
```

### Resilient External API Calls

```typescript
import { resilientExternalService, getLogger } from '@genesis/typescript';

class ExternalApiClient {
  private logger = getLogger('api-client');

  @resilientExternalService(3, 5, 60000, 'PaymentAPI')
  async processPayment(data: PaymentData) {
    this.logger.info('Processing payment', { amount: data.amount });

    const response = await fetch('/api/payments', {
      method: 'POST',
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error(`Payment failed: ${response.statusText}`);
    }

    return response.json();
  }
}
```

## Environment Variables

Common environment variables used by the library:

- `SERVICE` - Service name for context and logging
- `ENV` - Environment (development, production, etc.)
- `LOG_LEVEL` - Default log level
- `APP_*` - Application configuration (when using 'APP_' prefix)

## License

MIT
