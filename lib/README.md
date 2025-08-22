# Whitehorse Core Libraries

This directory contains the shared libraries for the Whitehorse Universal Project Platform. These libraries provide consistent interfaces and utilities across all components of the platform.

## Libraries

### Python Library (`python/whitehorse_core/`)
Industrial-strength Python library with comprehensive modules for:
- **Logging**: Structured logging with GCP Cloud Logging integration
- **Configuration**: Pydantic-based configuration with Secret Manager integration
- **Registry**: Project registry management and service discovery
- **Errors**: Comprehensive error handling with recovery mechanisms
- **Security**: Authentication, authorization, and encryption utilities
- **Monitoring**: Metrics collection and health checking
- **Deployment**: Multi-strategy deployment management
- **Intelligence**: AI-powered optimization and recommendations

**Installation:**
```bash
cd python/
pip install -e .
# Or with extras
pip install -e ".[gcp,monitoring,dev]"
```

**Usage:**
```python
from whitehorse_core import get_logger, get_config, ProjectRegistry

# Structured logging
logger = get_logger(__name__)
logger.info("Application started")

# Configuration management
config = get_config()
db_url = config.database_url

# Project registry
registry = ProjectRegistry()
projects = registry.list_projects()
```

### JavaScript/TypeScript Library (`javascript/@whitehorse/core/`)
Modern Node.js/TypeScript library with:
- **Logging**: Winston-based structured logging with correlation IDs
- **Configuration**: Multi-source configuration with validation
- **Errors**: Comprehensive error handling and circuit breakers
- **Types**: Complete TypeScript definitions
- **Utilities**: Async helpers, validation, crypto, and more

**Installation:**
```bash
cd javascript/@whitehorse/core/
npm install
npm run build
```

**Usage:**
```typescript
import { createLogger, loadConfig, ApiClient } from '@whitehorse/core';

// Structured logging
const logger = createLogger('my-service');
logger.info('Service started');

// Configuration
const config = await loadConfig();

// API client
const client = new ApiClient(config.api);
```

### Bash Utilities (`bash/common/`)
Comprehensive bash utilities for shell scripting:
- **Logging**: Advanced logging with structured output and GCP integration
- **Authentication**: GCP authentication and project isolation
- **Deployment**: Multi-strategy deployment utilities
- **Validation**: Input validation and security helpers
- **Utils**: Common utilities for file operations, networking, and more

**Usage:**
```bash
# Source the libraries
source lib/bash/common/logging/logger.sh
source lib/bash/common/auth/gcp_auth.sh
source lib/bash/common/deploy/deployment_utils.sh

# Structured logging
log_info "Starting deployment"
log_error "Deployment failed" '{"error_code": "TIMEOUT"}'

# GCP authentication
create_gcp_context "my-project-dev" "my-gcp-project-dev"
switch_gcp_context "my-project-dev"

# Deployment
deploy_application "my-app" "dev" "my-gcp-project-dev" "rolling"
```

### Go Module (`go/whitehorse/`)
High-performance Go library with:
- **Logging**: Structured logging with logrus and GCP Cloud Logging
- **Errors**: Comprehensive error handling with stack traces
- **Configuration**: Viper-based configuration management
- **HTTP**: HTTP client and server utilities
- **Metrics**: Prometheus metrics integration
- **Storage**: GCS and database abstractions

**Installation:**
```bash
cd go/whitehorse/
go mod tidy
```

**Usage:**
```go
package main

import (
    "context"
    "github.com/whitehorse/bootstrapper/lib/go/whitehorse"
)

func main() {
    // Create client
    client, err := whitehorse.NewClient(&whitehorse.Options{
        ServiceName: "my-service",
        Environment: "development",
        LogLevel:    "info",
    })
    if err != nil {
        panic(err)
    }

    // Start client
    ctx := context.Background()
    if err := client.Start(ctx); err != nil {
        panic(err)
    }
    defer client.Stop(ctx)

    // Use logger
    logger := client.Logger()
    logger.Info("Service started")

    // Use metrics
    metrics := client.Metrics()
    metrics.IncrementCounter("requests_total", 1, map[string]string{"method": "GET"})
}
```

## Design Principles

### 1. **Consistency**
All libraries provide consistent APIs and behavior across languages:
- Structured logging with correlation IDs
- Configuration management with environment variables and secrets
- Error handling with categorization and recovery mechanisms
- Metrics collection with common labels and formats

### 2. **Cloud-Native**
Deep integration with Google Cloud Platform:
- GCP Cloud Logging for centralized log collection
- Secret Manager for secure configuration
- Cloud Monitoring for metrics and alerting
- IAM for authentication and authorization

### 3. **Observability**
Built-in observability features:
- Structured logging with correlation tracking
- Metrics collection with Prometheus compatibility
- Distributed tracing support
- Health checking and service discovery

### 4. **Security**
Security-first design:
- Input validation and sanitization
- Secure secret management
- Authentication and authorization helpers
- Security event logging and monitoring

### 5. **Developer Experience**
Focus on developer productivity:
- Comprehensive documentation and examples
- Type safety (TypeScript, Python type hints)
- Interactive development tools
- Extensive testing and validation

## Configuration

All libraries support common configuration patterns:

### Environment Variables
```bash
# Service identification
SERVICE_NAME=my-service
SERVICE_VERSION=1.0.0
ENVIRONMENT=development

# GCP configuration
GCP_PROJECT=my-gcp-project
GCP_REGION=us-central1

# Logging
LOG_LEVEL=info
ENABLE_STRUCTURED_LOGGING=true
ENABLE_GCP_LOGGING=true

# Security
JWT_SECRET=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key
```

### Configuration Files
Each library supports configuration files in multiple formats:
- JSON: `config.json`
- YAML: `config.yaml` or `config.yml`
- Environment-specific: `config.dev.json`, `config.prod.yaml`

### Secret Management
Integration with GCP Secret Manager for sensitive configuration:
- Database passwords
- API keys
- JWT secrets
- Encryption keys

## Development

### Requirements
- **Python**: 3.8+
- **Node.js**: 14+
- **Go**: 1.21+
- **Bash**: 4.0+

### Testing
Each library includes comprehensive test suites:

```bash
# Python
cd python/
python -m pytest tests/ --cov=whitehorse_core

# JavaScript/TypeScript
cd javascript/@whitehorse/core/
npm test
npm run test:coverage

# Go
cd go/whitehorse/
go test ./... -race -cover

# Bash
cd bash/common/
./run_tests.sh
```

### Linting and Formatting
```bash
# Python
black whitehorse_core/
isort whitehorse_core/
flake8 whitehorse_core/

# JavaScript/TypeScript
npm run lint
npm run format

# Go
gofmt -w .
golint ./...
```

## Contributing

1. **Follow the established patterns** in each library
2. **Add comprehensive tests** for new functionality
3. **Update documentation** for API changes
4. **Use consistent naming** across all libraries
5. **Ensure security** for any new features

## Support

For issues and questions:
- Check the documentation in each library's directory
- Review the examples in the `examples/` directories
- Open an issue in the project repository

## License

MIT License - see LICENSE file for details.