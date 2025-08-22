# Genesis Core Integration Guide

This document provides comprehensive guidance for integrating Genesis Core components with existing services and frameworks. It follows the **MENTOR** methodology to ensure successful adoption and optimization.

## 🎯 Integration Strategy Overview

### Assessment Framework (MEASURE)

Before integrating Genesis Core, assess your existing service:

1. **Current Error Handling**: What error patterns exist?
2. **Logging Infrastructure**: Structured vs. unstructured logging
3. **Retry Mechanisms**: Existing retry logic and circuit breakers
4. **Health Monitoring**: Current health check implementations
5. **Context Management**: Request tracking and correlation

### Standards Evaluation (EVALUATE)

Genesis Core enforces these standards:
- **Structured Error Handling**: All errors categorized and contextualized
- **JSON Logging**: Cloud-native structured logging
- **Resilience Patterns**: Retry logic and circuit breakers
- **Health Monitoring**: Comprehensive health checks
- **Context Propagation**: Request correlation and tracing

## 🔌 Framework Integration Patterns

### FastAPI Integration

#### Basic Setup
```python
from fastapi import FastAPI, Request, HTTPException
from core import configure_core, get_logger, handle_error
from core.context import Context, RequestContext, context_span

app = FastAPI()

# Configure Genesis Core on startup
@app.on_event("startup")
async def startup():
    configure_core("my-api", "production", "1.0.0")

# Request context middleware
@app.middleware("http")
async def genesis_context(request: Request, call_next):
    # Create request context
    req_context = RequestContext.new_request()
    req_context.method = request.method
    req_context.path = str(request.url.path)
    req_context.remote_addr = request.client.host if request.client else None

    # Create application context
    app_context = Context.new_context("my-api", "production", "1.0.0")
    full_context = app_context.with_request(req_context)

    # Execute with context
    with context_span(full_context):
        response = await call_next(request)
        return response

# Error handling
@app.exception_handler(Exception)
async def genesis_exception_handler(request: Request, exc: Exception):
    genesis_error = handle_error(exc)
    logger = get_logger(__name__)
    logger.error("Unhandled API error", error=genesis_error)

    return HTTPException(
        status_code=500,
        detail={
            "error": genesis_error.message,
            "code": genesis_error.code,
            "correlation_id": genesis_error.context.correlation_id
        }
    )
```

#### Health Endpoints
```python
from core import get_service_health_registry, HTTPHealthCheck
from core.health import KubernetesProbeHandler

# Setup health checks
@app.on_event("startup")
async def setup_health():
    registry = get_service_health_registry()
    registry.add_check(HTTPHealthCheck("database", "http://db:5432/health"))

probe_handler = None

@app.on_event("startup")
async def setup_probes():
    global probe_handler
    probe_handler = KubernetesProbeHandler(get_service_health_registry())

@app.get("/health/liveness")
async def liveness():
    result = await probe_handler.liveness_probe()
    if result["status"] != "ok":
        raise HTTPException(status_code=503, detail=result)
    return result

@app.get("/health/readiness")
async def readiness():
    result = await probe_handler.readiness_probe()
    if result["status"] != "ok":
        raise HTTPException(status_code=503, detail=result)
    return result
```

### Flask Integration

#### Application Factory Pattern
```python
from flask import Flask, g, request, current_app
from core import configure_core, get_logger, handle_error
from core.context import Context, RequestContext, set_context, clear_context

def create_app(config_name='production'):
    app = Flask(__name__)

    # Configure Genesis Core
    with app.app_context():
        configure_core("my-flask-app", config_name, "1.0.0")

    # Request context setup
    @app.before_request
    def before_request():
        # Create Genesis context
        app_context = Context.new_context("my-flask-app", config_name, "1.0.0")
        req_context = RequestContext.new_request()
        req_context.method = request.method
        req_context.path = request.path

        full_context = app_context.with_request(req_context)
        set_context(full_context)
        g.genesis_context = full_context

    @app.teardown_request
    def teardown_request(exception):
        clear_context()

    # Error handling
    @app.errorhandler(Exception)
    def handle_exception(e):
        genesis_error = handle_error(e)
        logger = get_logger(__name__)
        logger.error("Flask application error", error=genesis_error)

        return {
            "error": genesis_error.message,
            "code": genesis_error.code,
            "correlation_id": genesis_error.context.correlation_id
        }, 500

    return app
```

### Django Integration

#### Settings Configuration
```python
# settings.py
from core import configure_core

# Configure Genesis Core
configure_core(
    service_name="my-django-app",
    environment=os.environ.get("DJANGO_ENV", "development"),
    version="1.0.0"
)

# Add Genesis middleware
MIDDLEWARE = [
    'myapp.middleware.GenesisContextMiddleware',
    # ... other middleware
]
```

#### Middleware Implementation
```python
# middleware.py
from django.utils.deprecation import MiddlewareMixin
from core.context import Context, RequestContext, context_span, get_context

class GenesisContextMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Create Genesis context
        app_context = Context.new_context("my-django-app", "production", "1.0.0")
        req_context = RequestContext.new_request()
        req_context.method = request.method
        req_context.path = request.path

        full_context = app_context.with_request(req_context)
        request.genesis_context = full_context

        # Set context for this request
        with context_span(full_context):
            return None

    def process_response(self, request, response):
        # Add correlation ID to response
        context = getattr(request, 'genesis_context', None)
        if context:
            response['X-Correlation-ID'] = context.correlation_id
        return response
```

## 🌐 Service-to-Service Integration

### HTTP Client Integration

#### With httpx
```python
import httpx
from core import retry, get_logger, get_context
from core.retry import NETWORK_POLICY

logger = get_logger(__name__)

class GenesisHTTPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.circuit_breaker = CircuitBreaker("http_client", failure_threshold=5)

    @retry(policy=NETWORK_POLICY)
    @circuit_breaker.decorator
    async def request(self, method: str, path: str, **kwargs):
        # Add correlation headers
        headers = kwargs.get('headers', {})
        current_context = get_context()

        if current_context:
            headers['X-Correlation-ID'] = current_context.correlation_id
            if current_context.trace:
                headers['X-Trace-ID'] = current_context.trace.trace_id

        kwargs['headers'] = headers

        async with httpx.AsyncClient() as client:
            response = await client.request(method, f"{self.base_url}{path}", **kwargs)
            response.raise_for_status()
            return response
```

#### With requests (sync)
```python
import requests
from core import retry, CircuitBreaker, get_logger, get_context

class GenesisRequestsClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.circuit_breaker = CircuitBreaker("requests_client")

    @retry(max_attempts=3, backoff='exponential')
    @circuit_breaker.decorator
    def request(self, method: str, path: str, **kwargs):
        # Add Genesis headers
        headers = kwargs.get('headers', {})
        current_context = get_context()

        if current_context:
            headers['X-Correlation-ID'] = current_context.correlation_id

        kwargs['headers'] = headers

        response = self.session.request(method, f"{self.base_url}{path}", **kwargs)
        response.raise_for_status()
        return response
```

### Message Queue Integration

#### With Celery
```python
from celery import Celery
from core import configure_core, get_logger, handle_error, Context, set_context
import json

# Configure Genesis for Celery
configure_core("my-celery-app", "production", "1.0.0")

app = Celery('tasks')

@app.task(bind=True)
def genesis_task(self, task_data, context_data=None):
    logger = get_logger(__name__)

    # Restore context if provided
    if context_data:
        context = Context(**context_data)
        set_context(context)

    try:
        logger.info("Processing Celery task", task_id=self.request.id)

        # Your task logic here
        result = process_task_data(task_data)

        logger.info("Task completed successfully", task_id=self.request.id)
        return result

    except Exception as e:
        genesis_error = handle_error(e)
        logger.error("Task failed", error=genesis_error, task_id=self.request.id)
        raise
```

#### With RabbitMQ/aio-pika
```python
import aio_pika
from core import get_logger, handle_error, get_context
import json

logger = get_logger(__name__)

async def publish_with_context(channel, exchange_name: str, routing_key: str, message: dict):
    """Publish message with Genesis context"""
    current_context = get_context()

    # Add context to message headers
    headers = {}
    if current_context:
        headers['x-correlation-id'] = current_context.correlation_id
        headers['x-service'] = current_context.service
        headers['x-environment'] = current_context.environment

    message_body = aio_pika.Message(
        json.dumps(message).encode(),
        headers=headers,
        content_type='application/json'
    )

    await channel.default_exchange.publish(message_body, routing_key=routing_key)
    logger.info("Message published", routing_key=routing_key, headers=headers)
```

## 🗄️ Database Integration

### SQLAlchemy Integration

#### Session Management
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from core import get_logger, retry, handle_error
from core.retry import DATABASE_POLICY

logger = get_logger(__name__)

class GenesisDatabase:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url)

    @retry(policy=DATABASE_POLICY)
    async def execute_query(self, query, params=None):
        """Execute database query with retry logic"""
        try:
            async with AsyncSession(self.engine) as session:
                result = await session.execute(query, params)
                await session.commit()
                return result
        except Exception as e:
            genesis_error = handle_error(e)
            logger.error("Database query failed", error=genesis_error, query=str(query))
            raise
```

#### Health Check Integration
```python
from core.health import HealthCheck, HealthStatus
from sqlalchemy import text

class SQLAlchemyHealthCheck(HealthCheck):
    def __init__(self, name: str, engine):
        super().__init__(name)
        self.engine = engine

    async def check_health(self):
        try:
            async with AsyncSession(self.engine) as session:
                await session.execute(text("SELECT 1"))
                return self._create_result(
                    HealthStatus.HEALTHY,
                    "Database connection healthy"
                )
        except Exception as e:
            return self._create_result(
                HealthStatus.UNHEALTHY,
                f"Database check failed: {str(e)}"
            )
```

### MongoDB Integration

#### Motor (Async MongoDB)
```python
from motor.motor_asyncio import AsyncIOMotorClient
from core import get_logger, retry, CircuitBreaker
from core.health import HealthCheck, HealthStatus

logger = get_logger(__name__)

class GenesisMongoClient:
    def __init__(self, connection_string: str):
        self.client = AsyncIOMotorClient(connection_string)
        self.circuit_breaker = CircuitBreaker("mongodb", failure_threshold=3)

    @retry(max_attempts=3, backoff='exponential')
    @circuit_breaker.decorator
    async def find_one(self, collection_name: str, filter_dict: dict):
        try:
            db = self.client.get_default_database()
            collection = db[collection_name]
            result = await collection.find_one(filter_dict)
            return result
        except Exception as e:
            logger.error("MongoDB query failed",
                        collection=collection_name,
                        filter=filter_dict,
                        error=str(e))
            raise

class MongoHealthCheck(HealthCheck):
    def __init__(self, name: str, client: AsyncIOMotorClient):
        super().__init__(name)
        self.client = client

    async def check_health(self):
        try:
            # Try to ping the server
            await self.client.admin.command('ping')
            return self._create_result(
                HealthStatus.HEALTHY,
                "MongoDB connection healthy"
            )
        except Exception as e:
            return self._create_result(
                HealthStatus.UNHEALTHY,
                f"MongoDB check failed: {str(e)}"
            )
```

## ☁️ Cloud Platform Integration

### Google Cloud Integration

#### Cloud Functions
```python
import functions_framework
from core import configure_core, get_logger, handle_error

# Configure Genesis for Cloud Functions
configure_core("my-cloud-function", "production", "1.0.0")
logger = get_logger(__name__)

@functions_framework.http
def genesis_cloud_function(request):
    try:
        logger.info("Cloud Function triggered", method=request.method, path=request.path)

        # Your function logic here
        result = process_request(request)

        logger.info("Function completed successfully")
        return result

    except Exception as e:
        genesis_error = handle_error(e)
        logger.error("Cloud Function failed", error=genesis_error)
        return {
            "error": genesis_error.message,
            "code": genesis_error.code
        }, 500
```

#### Cloud Run
```python
# Dockerfile additions for Cloud Run
FROM python:3.11-slim

# Install Genesis Core dependencies
RUN pip install aiohttp psutil httpx

COPY requirements.txt .
RUN pip install -r requirements.txt

# Set Genesis environment variables
ENV GENESIS_SERVICE=my-cloud-run-service
ENV GENESIS_ENV=production
ENV GENESIS_LOG_LEVEL=INFO

COPY . .

# Health check endpoint for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health/liveness || exit 1

CMD ["python", "main.py"]
```

### AWS Integration

#### Lambda Functions
```python
import json
from core import configure_core, get_logger, handle_error

# Configure Genesis for Lambda
configure_core("my-lambda-function", "production", "1.0.0")
logger = get_logger(__name__)

def lambda_handler(event, context):
    try:
        logger.info("Lambda function triggered",
                   request_id=context.aws_request_id,
                   function_name=context.function_name)

        # Your Lambda logic here
        result = process_lambda_event(event)

        logger.info("Lambda function completed", request_id=context.aws_request_id)
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }

    except Exception as e:
        genesis_error = handle_error(e)
        logger.error("Lambda function failed",
                    error=genesis_error,
                    request_id=context.aws_request_id)

        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': genesis_error.message,
                'code': genesis_error.code
            })
        }
```

## 🔍 Monitoring Integration

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from core import get_logger, get_context
import time

# Prometheus metrics
REQUEST_COUNT = Counter('genesis_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('genesis_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('genesis_active_connections', 'Active connections')

logger = get_logger(__name__)

class PrometheusMiddleware:
    def __init__(self):
        # Start metrics server
        start_http_server(8000)

    async def __call__(self, request, call_next):
        start_time = time.time()

        try:
            response = await call_next(request)

            # Record metrics
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()

            REQUEST_DURATION.observe(time.time() - start_time)

            return response

        except Exception as e:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=500
            ).inc()
            raise
```

### OpenTelemetry Integration

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from core import get_context

# Configure OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

def trace_with_genesis_context(operation_name: str):
    """Create OpenTelemetry span with Genesis context"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(operation_name) as span:
                # Add Genesis context to span
                genesis_context = get_context()
                if genesis_context:
                    span.set_attribute("genesis.correlation_id", genesis_context.correlation_id)
                    span.set_attribute("genesis.service", genesis_context.service)
                    span.set_attribute("genesis.environment", genesis_context.environment)

                    if genesis_context.user:
                        span.set_attribute("genesis.user_id", genesis_context.user.user_id)

                return await func(*args, **kwargs)
        return wrapper
    return decorator
```

## 📋 Migration Strategies

### Gradual Migration

#### Phase 1: Logging Migration
```python
# Before: Standard logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# After: Genesis logging
from core import get_logger
logger = get_logger(__name__)

# Migration helper for existing code
def migrate_existing_logs():
    """Helper to gradually migrate existing log statements"""
    # Replace logging.info with logger.info
    # Add structured context gradually
    pass
```

#### Phase 2: Error Handling Migration
```python
# Before: Basic error handling
try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise

# After: Genesis error handling
from core import handle_error

try:
    risky_operation()
except Exception as e:
    genesis_error = handle_error(e)
    logger.error("Operation failed", error=genesis_error)
    raise genesis_error
```

#### Phase 3: Resilience Patterns
```python
# Before: No retry logic
def external_api_call():
    return requests.get("https://api.example.com/data")

# After: With retry and circuit breaker
from core import retry, CircuitBreaker

circuit_breaker = CircuitBreaker("external_api")

@retry(max_attempts=3, backoff='exponential')
@circuit_breaker.decorator
def external_api_call():
    return requests.get("https://api.example.com/data")
```

### Testing Migration

```python
import pytest
from core import configure_core, Context, context_span

@pytest.fixture(scope="session")
def genesis_setup():
    """Setup Genesis for tests"""
    configure_core("test-service", "test", "1.0.0")

@pytest.fixture
def test_context():
    """Provide test context"""
    return Context.new_context("test-service", "test", "1.0.0")

def test_with_genesis_context(genesis_setup, test_context):
    """Test function with Genesis context"""
    with context_span(test_context):
        # Test logic here
        result = my_function()
        assert result is not None
```

## 🚀 Deployment Considerations

### Environment Configuration

```python
# config.py
import os
from core import configure_core

def setup_genesis():
    """Configure Genesis based on environment"""
    service_name = os.environ.get("SERVICE_NAME", "my-service")
    environment = os.environ.get("ENVIRONMENT", "development")
    version = os.environ.get("VERSION", "1.0.0")
    log_level = os.environ.get("LOG_LEVEL", "INFO")

    configure_core(
        service_name=service_name,
        environment=environment,
        version=version,
        log_level=log_level
    )

# Call in application startup
setup_genesis()
```

### Container Configuration

```dockerfile
# Dockerfile with Genesis optimizations
FROM python:3.11-slim

# Install Genesis dependencies
RUN pip install aiohttp psutil httpx prometheus-client

# Set Genesis environment variables
ENV GENESIS_SERVICE=my-service
ENV GENESIS_ENV=production
ENV GENESIS_VERSION=1.0.0
ENV GENESIS_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health/liveness || exit 1

COPY . .
CMD ["python", "main.py"]
```

### Kubernetes Deployment

```yaml
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
        env:
        - name: GENESIS_SERVICE
          value: "my-service"
        - name: GENESIS_ENV
          value: "production"
        - name: GENESIS_VERSION
          value: "1.0.0"
        - name: GENESIS_LOG_LEVEL
          value: "INFO"

        # Genesis health probes
        livenessProbe:
          httpGet:
            path: /health/liveness
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10

        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5

        startupProbe:
          httpGet:
            path: /health/startup
            port: 8080
          failureThreshold: 30
          periodSeconds: 10
```

## 🔧 Troubleshooting

### Common Integration Issues

#### Import Errors
```python
# Problem: Missing dependencies
ImportError: No module named 'aiohttp'

# Solution: Install optional dependencies
pip install aiohttp psutil httpx prometheus-client

# Or use requirements.txt
echo "aiohttp>=3.8.0" >> requirements.txt
echo "psutil>=5.9.0" >> requirements.txt
echo "httpx>=0.24.0" >> requirements.txt
```

#### Context Not Propagating
```python
# Problem: Context lost in async operations
async def problematic_function():
    # Context is None here
    context = get_context()  # Returns None

# Solution: Ensure context is set in async context
async def fixed_function():
    # Ensure context is available
    context = get_context()
    if not context:
        context = Context.new_context("service", "env", "1.0.0")
        set_context(context)
```

#### Performance Issues
```python
# Problem: Too much logging in production
logger.debug("Detailed debug info")  # Expensive

# Solution: Use appropriate log levels
if logger.logger.isEnabledFor(LogLevel.DEBUG.value):
    logger.debug("Expensive debug operation", data=expensive_operation())
```

### Best Practices Summary

1. **Gradual Adoption**: Migrate components incrementally
2. **Environment-Specific Configuration**: Use environment variables
3. **Health Check Coverage**: Monitor all critical dependencies
4. **Context Propagation**: Ensure context flows through all operations
5. **Error Categorization**: Use appropriate Genesis error categories
6. **Performance Monitoring**: Monitor Genesis component performance
7. **Testing**: Include Genesis components in your test suite

---

**Genesis Core Team** - Built with ❤️ for seamless service integration
