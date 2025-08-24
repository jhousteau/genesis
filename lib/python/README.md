# Whitehorse Core Library

Industrial-strength Python library providing common utilities, integrations, and patterns for cloud-native applications built on the Universal Project Platform.

## Overview

Whitehorse Core is a comprehensive Python package that eliminates code duplication across projects by providing:

- **Structured Logging** - JSON logging with GCP Cloud Logging integration and correlation IDs
- **Error Handling** - Comprehensive error management with recovery mechanisms and monitoring
- **Configuration** - Pydantic-based config management with environment and secret support
- **Health Checks** - System, database, and service health monitoring
- **Security** - Secrets management, encryption, authentication, and authorization
- **Storage** - Unified interface for GCS, S3, and local filesystem
- **Database** - Connection pooling, transactions, and query helpers
- **API Client** - HTTP client with retry, circuit breaker, and authentication
- **Metrics** - Prometheus and OpenTelemetry integration
- **Tracing** - Distributed tracing with context propagation
- **Caching** - Redis and in-memory caching abstractions
- **Queuing** - Pub/Sub and Cloud Tasks integration
- **CLI Framework** - Typer-based command-line tools

## Quick Start

### Installation

```bash
# Basic installation
pip install whitehorse-core

# With GCP support
pip install whitehorse-core[gcp]

# With all optional dependencies
pip install whitehorse-core[all]
```

### Basic Usage

```python
from whitehorse_core import get_logger, get_config
from whitehorse_core.storage import create_storage
from whitehorse_core.api_client import create_client
from whitehorse_core.health import default_health_monitor

# Structured logging
logger = get_logger(__name__)
logger.info("Application starting", component="main")

# Configuration management
config = get_config()
logger.info("Configuration loaded", environment=config.environment)

# Storage abstraction
storage = create_storage('gcs', bucket_name='my-bucket')
storage.put_text('config.json', '{"version": "1.0"}')
data = storage.get_text('config.json')

# HTTP client with retries
client = create_client(base_url="https://api.example.com")
response = client.get("/users")

# Health monitoring
default_health_monitor.add_check(HTTPHealthCheck("api", "https://api.example.com/health"))
health_report = default_health_monitor.get_health_report()
```

## Modules

### Logging (`whitehorse_core.logging`)

Structured JSON logging with GCP Cloud Logging integration:

```python
from whitehorse_core.logging import get_logger, setup_logging

# Setup logging for your service
setup_logging(
    service_name="my-service",
    level="INFO",
    enable_gcp=True
)

logger = get_logger(__name__)

# Structured logging with correlation IDs
with logger.correlation_id() as correlation_id:
    logger.info("Processing request", user_id="123", action="create")
    # All log entries will include the correlation_id
```

### Configuration (`whitehorse_core.config`)

Pydantic-based configuration with multiple sources:

```python
from whitehorse_core.config import BaseConfig, get_config
from pydantic import Field

class MyConfig(BaseConfig):
    database_url: str = Field(..., description="Database connection URL")
    redis_url: str = Field(default="redis://localhost:6379")
    api_key: str = Field(..., description="API key from secrets")

# Loads from: environment variables, GCP Secret Manager, config files, defaults
config = get_config(MyConfig)
print(config.database_url)
```

### Error Handling (`whitehorse_core.errors`)

Comprehensive error management with recovery:

```python
from whitehorse_core.errors import retry, CircuitBreaker, WhitehorseError
from whitehorse_core.errors import handle_errors, error_context

# Retry with exponential backoff
@retry(max_attempts=3, base_delay=1.0)
def unreliable_function():
    # Will retry on network errors
    pass

# Circuit breaker pattern
@CircuitBreaker(failure_threshold=5)
def external_service_call():
    pass

# Error context for debugging
with error_context("user_registration", user_id="123"):
    # Any errors will include this context
    register_user()
```

### Health Checks (`whitehorse_core.health`)

System and service health monitoring:

```python
from whitehorse_core.health import (
    HealthMonitor, SystemHealthCheck, DatabaseHealthCheck, HTTPHealthCheck
)

monitor = HealthMonitor("my-service")
monitor.add_check(SystemHealthCheck(cpu_threshold=80.0))
monitor.add_check(HTTPHealthCheck("api", "https://api.service.com/health"))
monitor.add_check(DatabaseHealthCheck("db", connection_factory=get_db_connection))

# Get health report
report = monitor.get_health_report()
print(f"Service status: {report['status']}")

# Start background monitoring
monitor.start_monitoring(interval=30.0)
```

### Security (`whitehorse_core.security`)

Secrets, encryption, and authentication:

```python
from whitehorse_core.security import get_security_manager
from whitehorse_core.security import GCPSecretStore, Encryption

# Security manager with RBAC
security = get_security_manager()

# JWT authentication
token = security.jwt_manager.create_token("user123", expires_in=3600)
user = security.authenticate_jwt(token.value)

# Secrets management
security.secret_store.set_secret("api_key", "secret-value")
api_key = security.secret_store.get_secret("api_key")

# Encryption
encryption = Encryption.from_password("my-password")
encrypted = encryption.encrypt_string("sensitive data")
decrypted = encryption.decrypt_string(encrypted)
```

### Storage (`whitehorse_core.storage`)

Unified storage interface for multiple backends:

```python
from whitehorse_core.storage import create_storage

# GCS backend
storage = create_storage('gcs', bucket_name='my-bucket', project_id='my-project')

# S3 backend
storage = create_storage('s3', bucket_name='my-bucket', region='us-east-1')

# Local filesystem
storage = create_storage('local', base_path='./data')

# Common interface
storage.put_json('config.json', {'version': '1.0'})
config = storage.get_json('config.json')
files = storage.list('logs/')

# File operations
storage.put_text('readme.txt', 'Hello World')
content = storage.get_text('readme.txt')
url = storage.generate_url('readme.txt', expiration=3600)
```

### API Client (`whitehorse_core.api_client`)

HTTP client with advanced features:

```python
from whitehorse_core.api_client import create_client, BearerTokenAuth

# Create authenticated client
client = create_client(
    base_url="https://api.example.com",
    auth_token="bearer-token"
)

# Make requests with automatic retries
response = client.get("/users", params={"limit": 100})
response.raise_for_status()
users = response.json()

# Upload files
client.upload_file("/upload", "document.pdf")

# Pagination support
responses = client.paginate("/items", page_size=50, max_pages=10)
all_items = [item for response in responses for item in response.json()['data']]

# Rate limiting and circuit breaker included automatically
```

## Advanced Features

### Custom Health Checks

```python
from whitehorse_core.health import HealthCheck, HealthCheckResult, HealthStatus

class CustomHealthCheck(HealthCheck):
    def check(self) -> HealthCheckResult:
        # Custom health check logic
        return HealthCheckResult(
            name=self.name,
            status=HealthStatus.HEALTHY,
            message="Custom check passed",
            timestamp=time.time(),
            duration_ms=10.0
        )

monitor.add_check(CustomHealthCheck("custom", timeout=5.0))
```

### Storage with Compression and Caching

```python
# Enable compression and caching
storage = create_storage(
    'gcs',
    bucket_name='my-bucket',
    enable_compression=True,
    cache_size=200
)

# Large JSON files will be compressed automatically
storage.put_json('large-data.json', large_dict)
```

### Request Interceptors

```python
from whitehorse_core.api_client import APIClient, RequestInterceptor

class CustomInterceptor(RequestInterceptor):
    def before_request(self, method, url, headers, **kwargs):
        headers['X-Custom-Header'] = 'value'
        return super().before_request(method, url, headers, **kwargs)

client = APIClient()
client.add_interceptor(CustomInterceptor())
```

## Configuration

### Environment Variables

```bash
# Service configuration
SERVICE_NAME=my-service
ENVIRONMENT=production
LOG_LEVEL=INFO

# GCP configuration
GCP_PROJECT=my-project
GCP_REGION=us-central1

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_USER=user
DB_PASSWORD=password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Configuration Files

Create `config.json` or `config.yaml`:

```json
{
  "service_name": "my-service",
  "environment": "production",
  "database": {
    "host": "db.example.com",
    "port": 5432
  },
  "features": {
    "enable_caching": true,
    "cache_ttl": 300
  }
}
```

## Testing

```python
import pytest
from whitehorse_core.config import get_config
from whitehorse_core.security import MemorySecretStore
from whitehorse_core.storage import create_storage

def test_config():
    config = get_config(environment="test")
    assert config.environment == "test"

def test_storage():
    storage = create_storage('local', base_path='./test-data')
    storage.put_text('test.txt', 'hello')
    assert storage.get_text('test.txt') == 'hello'

def test_secrets():
    store = MemorySecretStore()
    store.set_secret('test', 'value')
    assert store.get_secret('test') == 'value'
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/whitehorse/bootstrapper.git
cd bootstrapper/lib/python

# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Code formatting
black whitehorse_core/
isort whitehorse_core/

# Type checking
mypy whitehorse_core/
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## Integration Examples

### FastAPI Application

```python
from fastapi import FastAPI, Depends
from whitehorse_core import get_logger, get_config
from whitehorse_core.health import default_health_monitor

app = FastAPI()
logger = get_logger(__name__)
config = get_config()

@app.on_startup
async def startup():
    logger.info("Application starting", service=config.service_name)

@app.get("/health")
async def health():
    return default_health_monitor.get_health_report()

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"service": config.service_name, "version": config.service_version}
```

### Background Worker

```python
import asyncio
from whitehorse_core import get_logger
from whitehorse_core.storage import create_storage
from whitehorse_core.queue import PubSubQueue

logger = get_logger(__name__)
storage = create_storage('gcs', bucket_name='worker-data')
queue = PubSubQueue('work-queue')

async def process_message(message):
    logger.info("Processing message", message_id=message.id)

    # Process and store result
    result = await process_work(message.data)
    storage.put_json(f"results/{message.id}.json", result)

    logger.info("Message processed", message_id=message.id)

async def main():
    logger.info("Worker starting")
    await queue.consume(process_message)

if __name__ == "__main__":
    asyncio.run(main())
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

- Documentation: https://whitehorse-platform.readthedocs.io/
- Issues: https://github.com/whitehorse/bootstrapper/issues
- Discussions: https://github.com/whitehorse/bootstrapper/discussions
