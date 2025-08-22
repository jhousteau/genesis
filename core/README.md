# Genesis Core Plumbing Library

Production-ready foundational components for cloud-native applications. The Genesis Core library provides structured error handling, logging, retry logic, health checks, and context management with thread-safe implementations following cloud-native best practices.

## 🏗️ Architecture Overview

The Genesis Core library is built on the **MENTOR** methodology principles:

- **Measure & Assess**: Comprehensive metrics and health monitoring
- **Evaluate Standards**: Consistent patterns across all components
- **Nurture Team Growth**: Clear APIs and extensive documentation
- **Teach & Guide**: Rich examples and best practices
- **Optimize Development Process**: Developer-friendly integrations
- **Review & Iterate**: Thread-safe, production-tested implementations

## 📦 Components

### 🚨 Error Handling (`core.errors`)

Structured error handling with categorization, context preservation, and automatic reporting.

**Key Features:**
- Structured error categorization (Infrastructure, Network, Validation, etc.)
- Correlation ID tracking and context preservation
- Automatic error serialization and stack trace management
- Integration with logging and monitoring systems

**Example:**
```python
from core import handle_error, GenesisError, ErrorCategory

try:
    risky_operation()
except Exception as e:
    genesis_error = handle_error(e)
    # Automatically categorized and enriched with context
    print(f"Error: {genesis_error.code} - {genesis_error.message}")
```

**Error Categories:**
- `INFRASTRUCTURE`: Infrastructure and platform errors
- `NETWORK`: Network connectivity and timeout issues
- `VALIDATION`: Data validation and format errors
- `AUTHENTICATION`/`AUTHORIZATION`: Security-related errors
- `EXTERNAL_SERVICE`: Third-party service failures
- `RATE_LIMIT`: Rate limiting and throttling
- `RESOURCE_EXHAUSTED`: Resource limitation errors

### 📝 Structured Logging (`core.logging`)

JSON structured logging with context injection, performance tracking, and Cloud Logging compatibility.

**Key Features:**
- JSON formatted output for structured parsing
- Automatic context injection (correlation IDs, trace IDs, user info)
- Performance timing with context managers
- Cloud Logging compatible metadata
- Thread-safe logger factory

**Example:**
```python
from core import get_logger

logger = get_logger(__name__)

# Basic logging with automatic context
logger.info("Processing request", user_id="123", action="create_order")

# Performance timing
with logger.timer("database_query", table="orders"):
    result = db.query("SELECT * FROM orders")

# Error logging with exception details
try:
    process_payment()
except Exception as e:
    logger.error("Payment processing failed", error=e, order_id="456")
```

**Log Levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: General application flow information
- `WARNING`: Warning conditions that should be noted
- `ERROR`: Error conditions that affect operation
- `CRITICAL`: Critical errors requiring immediate attention

### 🔄 Retry Logic (`core.retry`)

Exponential backoff retry logic with circuit breakers for resilient cloud-native applications.

**Key Features:**
- Multiple backoff strategies (fixed, linear, exponential, with jitter)
- Circuit breaker pattern implementation
- Async and sync operation support
- Intelligent retry based on error categories
- Pre-configured policies for common scenarios

**Example:**
```python
from core import retry, CircuitBreaker, AGGRESSIVE_POLICY

# Simple retry decorator
@retry(max_attempts=3, backoff='exponential')
def unreliable_operation():
    return external_api_call()

# Circuit breaker for failing services
cb = CircuitBreaker(failure_threshold=5, timeout=60)

@cb.decorator
def external_service():
    return call_external_service()

# Use pre-configured policies
@retry(policy=AGGRESSIVE_POLICY)
def critical_operation():
    return important_api_call()
```

**Backoff Strategies:**
- `FIXED`: Constant delay between retries
- `LINEAR`: Linearly increasing delays
- `EXPONENTIAL`: Exponentially increasing delays
- `EXPONENTIAL_JITTER`: Exponential with randomization

**Pre-configured Policies:**
- `DEFAULT_POLICY`: Standard retry for most operations
- `AGGRESSIVE_POLICY`: More attempts for critical operations
- `CONSERVATIVE_POLICY`: Fewer attempts for expensive operations
- `NETWORK_POLICY`: Optimized for network operations
- `DATABASE_POLICY`: Optimized for database operations

### 🏥 Health Monitoring (`core.health`)

Comprehensive health monitoring with Kubernetes probe support and built-in checks.

**Key Features:**
- Abstract health check framework
- Built-in checks for common resources (HTTP, database, disk, memory)
- Kubernetes liveness/readiness/startup probe support
- Thread-safe health check registry
- JSON serializable health reports

**Example:**
```python
from core import get_health_registry, HTTPHealthCheck, DatabaseHealthCheck

# Get global health registry
registry = get_health_registry()

# Add health checks
registry.add_check(HTTPHealthCheck("api", "https://api.example.com/health"))
registry.add_check(DatabaseHealthCheck("db", "postgresql://localhost/mydb"))

# Check overall health
health_report = await registry.check_health()
print(f"Overall status: {health_report.status}")

# Kubernetes probe handler
from core.health import KubernetesProbeHandler
probe_handler = KubernetesProbeHandler(registry)
liveness_status = await probe_handler.liveness_probe()
```

**Health Statuses:**
- `HEALTHY`: All systems operational
- `DEGRADED`: Some non-critical issues detected
- `UNHEALTHY`: Critical issues affecting operation
- `UNKNOWN`: Unable to determine health status

**Built-in Health Checks:**
- `HTTPHealthCheck`: Monitor HTTP endpoints
- `DatabaseHealthCheck`: Database connectivity
- `DiskHealthCheck`: Disk space usage monitoring
- `MemoryHealthCheck`: Memory usage monitoring

### 🔗 Context Management (`core.context`)

Thread-safe context management for distributed applications with request tracking and tracing.

**Key Features:**
- Request context tracking with correlation IDs
- User session management
- Distributed tracing context (trace_id, span_id)
- Thread-safe context storage using contextvars
- Context propagation patterns

**Example:**
```python
from core.context import Context, RequestContext, UserContext, context_span

# Create application context
app_context = Context.new_context(
    service="user-service",
    environment="production",
    version="1.2.0"
)

# Add request context
request_ctx = RequestContext.new_request()
request_ctx.method = "POST"
request_ctx.path = "/api/users"

context_with_request = app_context.with_request(request_ctx)

# Use context span for scoped execution
with context_span(context_with_request):
    # All logging and operations within this block
    # will have the request context available
    logger.info("Processing user creation")
    create_user(user_data)
```

## 🚀 Quick Start

### 1. Basic Setup

```python
from core import configure_core, get_logger

# Configure all core components
configure_core(
    service_name="my-service",
    environment="production",
    version="1.0.0",
    log_level="INFO"
)

# Get logger with automatic context
logger = get_logger(__name__)
logger.info("Service starting")
```

### 2. Error Handling Pattern

```python
from core import handle_error, get_logger

logger = get_logger(__name__)

def process_request(data):
    try:
        return business_logic(data)
    except Exception as e:
        # Automatic error categorization and context enrichment
        genesis_error = handle_error(e)

        # Log with structured error information
        logger.error(
            "Request processing failed",
            error=genesis_error,
            request_data=data
        )

        # Re-raise as Genesis error for upstream handling
        raise genesis_error
```

### 3. Resilient Service Calls

```python
from core import retry, CircuitBreaker

# Circuit breaker for external service
payment_service = CircuitBreaker(
    name="payment_service",
    failure_threshold=5,
    timeout=60
)

@retry(max_attempts=3, backoff='exponential')
@payment_service.decorator
async def process_payment(payment_data):
    async with httpx.AsyncClient() as client:
        response = await client.post("/api/payments", json=payment_data)
        response.raise_for_status()
        return response.json()
```

### 4. Health Monitoring Setup

```python
from core import get_service_health_registry, HTTPHealthCheck

# Get registry with basic system checks pre-configured
registry = get_service_health_registry()

# Add application-specific health checks
registry.add_check(HTTPHealthCheck(
    name="payment_api",
    url="https://payments.example.com/health",
    timeout=10.0
))

# Check health periodically
import asyncio

async def health_check_loop():
    while True:
        health = await registry.check_health()
        if health.status != HealthStatus.HEALTHY:
            logger.warning("Health check failed", health_report=health.to_dict())
        await asyncio.sleep(30)
```

## 🏗️ Integration Patterns

### Web Framework Integration

**FastAPI Integration:**
```python
from fastapi import FastAPI, Request
from core import configure_core, get_logger, get_context, RequestContext

app = FastAPI()

# Configure core on startup
@app.on_event("startup")
async def startup():
    configure_core("my-api", "production", "1.0.0")

# Request context middleware
@app.middleware("http")
async def context_middleware(request: Request, call_next):
    # Create request context
    req_context = RequestContext.new_request()
    req_context.method = request.method
    req_context.path = str(request.url.path)

    # Set in current context
    current = get_context()
    if current:
        updated_context = current.with_request(req_context)
        with context_span(updated_context):
            response = await call_next(request)
    else:
        response = await call_next(request)

    return response
```

**Flask Integration:**
```python
from flask import Flask, g, request
from core import configure_core, get_logger, Context, RequestContext

app = Flask(__name__)

# Configure on app startup
with app.app_context():
    configure_core("my-flask-app", "production")

@app.before_request
def before_request():
    # Create context for this request
    context = Context.new_context("my-flask-app", "production")
    req_context = RequestContext.new_request()
    req_context.method = request.method
    req_context.path = request.path

    g.context = context.with_request(req_context)
    set_context(g.context)

@app.teardown_request
def teardown_request(exception):
    clear_context()
```

### Async Application Pattern

```python
import asyncio
from core import configure_core, get_logger, retry, get_health_registry

class AsyncService:
    def __init__(self):
        configure_core("async-service", "production")
        self.logger = get_logger(__name__)
        self.health_registry = get_health_registry()

    async def start(self):
        self.logger.info("Starting async service")

        # Start health monitoring
        health_task = asyncio.create_task(self._health_monitor())

        # Start main processing
        process_task = asyncio.create_task(self._process_messages())

        # Wait for tasks
        await asyncio.gather(health_task, process_task)

    @retry(max_attempts=3, backoff='exponential')
    async def _process_message(self, message):
        # Process individual message with retry
        pass

    async def _health_monitor(self):
        while True:
            health = await self.health_registry.check_health()
            if health.status != HealthStatus.HEALTHY:
                self.logger.warning("Service unhealthy", health=health.to_dict())
            await asyncio.sleep(30)
```

## 🔧 Configuration

### Environment Variables

The core library respects the following environment variables:

```bash
# Service identification
GENESIS_SERVICE=my-service
GENESIS_ENV=production
GENESIS_VERSION=1.0.0

# Logging configuration
GENESIS_LOG_LEVEL=INFO

# Context defaults
GENESIS_CORRELATION_ID_HEADER=X-Correlation-ID
GENESIS_TRACE_ID_HEADER=X-Trace-ID
```

### Configuration File Pattern

```python
# config.py
import os
from core import configure_core

def setup_core():
    configure_core(
        service_name=os.environ.get("SERVICE_NAME", "my-service"),
        environment=os.environ.get("ENVIRONMENT", "development"),
        version=os.environ.get("VERSION", "1.0.0"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )

# Import in your main application
from config import setup_core
setup_core()
```

## 🧪 Testing Patterns

### Unit Testing with Core Components

```python
import pytest
from core import GenesisError, Context, get_logger
from core.context import context_span

class TestServiceLogic:
    def setup_method(self):
        # Create test context
        self.test_context = Context.new_context(
            service="test-service",
            environment="test"
        )

    def test_business_logic_with_context(self):
        with context_span(self.test_context):
            # Test code runs with proper context
            result = business_logic()
            assert result is not None

    def test_error_handling(self):
        with pytest.raises(GenesisError) as exc_info:
            failing_operation()

        error = exc_info.value
        assert error.category == ErrorCategory.VALIDATION
        assert "correlation_id" in error.context.to_dict()
```

### Integration Testing with Health Checks

```python
import pytest
from core import get_health_registry, HTTPHealthCheck

@pytest.mark.asyncio
async def test_health_checks():
    registry = get_health_registry()
    registry.add_check(HTTPHealthCheck("api", "http://localhost:8000/health"))

    health = await registry.check_health()
    assert health.status == HealthStatus.HEALTHY
```

## 📊 Monitoring and Observability

### Structured Logging for Monitoring

```python
from core import get_logger
import time

logger = get_logger(__name__)

def process_order(order_id):
    start_time = time.time()

    try:
        with logger.timer("order_processing", order_id=order_id):
            # Business logic
            result = process_business_logic(order_id)

        # Success metrics
        logger.info(
            "Order processed successfully",
            order_id=order_id,
            result_type=type(result).__name__,
            processing_duration_ms=(time.time() - start_time) * 1000
        )

        return result

    except Exception as e:
        # Error metrics
        logger.error(
            "Order processing failed",
            order_id=order_id,
            error=e,
            processing_duration_ms=(time.time() - start_time) * 1000
        )
        raise
```

### Health Check Monitoring

```python
from core import get_health_registry, HTTPHealthCheck, DatabaseHealthCheck

def setup_monitoring():
    registry = get_health_registry()

    # Core service dependencies
    registry.add_check(HTTPHealthCheck("payment_api", "https://payments.example.com/health"))
    registry.add_check(DatabaseHealthCheck("primary_db", "postgresql://..."))

    # Custom business logic health check
    class OrderProcessingHealthCheck(HealthCheck):
        async def check_health(self):
            try:
                # Check if order processing is working
                test_result = await simulate_order_processing()
                return self._create_result(
                    HealthStatus.HEALTHY,
                    "Order processing operational",
                    test_duration=test_result.duration
                )
            except Exception as e:
                return self._create_result(
                    HealthStatus.UNHEALTHY,
                    f"Order processing failed: {str(e)}"
                )

    registry.add_check(OrderProcessingHealthCheck("order_processing"))

    return registry
```

## 🚀 Production Deployment

### Kubernetes Health Probes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  template:
    spec:
      containers:
      - name: my-service
        image: my-service:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/liveness
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        startupProbe:
          httpGet:
            path: /health/startup
            port: 8000
          failureThreshold: 30
          periodSeconds: 10
```

### Docker Integration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Environment variables for core configuration
ENV GENESIS_SERVICE=my-service
ENV GENESIS_ENV=production
ENV GENESIS_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/liveness || exit 1

CMD ["python", "main.py"]
```

## 🤝 Best Practices

### 1. Context Management
- Always use context spans for scoped operations
- Propagate context across async boundaries
- Include correlation IDs in all external requests

### 2. Error Handling
- Use structured error handling consistently
- Include relevant context in error messages
- Log errors at appropriate levels

### 3. Retry Logic
- Use appropriate retry policies for different operation types
- Implement circuit breakers for external dependencies
- Consider jitter to avoid thundering herd problems

### 4. Health Monitoring
- Include health checks for all critical dependencies
- Use appropriate probe types for Kubernetes deployments
- Monitor health check performance and reliability

### 5. Logging
- Use structured logging consistently
- Include performance timing for critical operations
- Log at appropriate levels (avoid debug logs in production)

## 🔗 Integration with Existing Services

The Genesis Core library is designed to integrate seamlessly with existing services. See the `examples/` directory for complete integration examples and the integration documentation for specific framework patterns.

---

**Genesis Core Team** - Built with ❤️ for cloud-native applications
