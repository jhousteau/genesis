# Whitehorse Bash Common Utilities

Comprehensive bash utilities for the Universal Project Platform. Provides industrial-strength shell scripting capabilities with structured logging, GCP integration, and deployment automation.

## Features

- **Advanced Logging**: Structured logging with JSON output, correlation IDs, and GCP Cloud Logging integration
- **GCP Authentication**: Secure authentication and project isolation with gcloud CLI
- **Deployment Utils**: Multi-strategy deployment automation (rolling, blue-green, canary)
- **Validation**: Input validation and security helpers
- **Error Handling**: Comprehensive error handling with recovery mechanisms
- **Performance**: Timing and performance measurement utilities

## Installation

No installation required - simply source the utilities in your bash scripts:

```bash
# Source the main utilities
source /path/to/lib/bash/common/utils.sh
source /path/to/lib/bash/common/logging/logger.sh
source /path/to/lib/bash/common/auth/gcp_auth.sh
source /path/to/lib/bash/common/deploy/deployment_utils.sh
```

## Quick Start

```bash
#!/bin/bash

# Source required utilities
source "$(dirname "$0")/lib/bash/common/logging/logger.sh"
source "$(dirname "$0")/lib/bash/common/auth/gcp_auth.sh"

# Set up logging
setup_logging
SERVICE_NAME="my-service"
LOG_LEVEL="INFO"
ENABLE_STRUCTURED_LOGGING="true"

# Log startup
log_startup

# Use structured logging
log_info "Starting application" '{"version": "1.0.0", "environment": "production"}'

# Set up GCP authentication
create_gcp_context "my-app-prod" "my-gcp-project-prod"
switch_gcp_context "my-app-prod"

# Verify authentication
if check_auth_status; then
    log_info "GCP authentication successful"
else
    log_error "GCP authentication failed"
    exit 1
fi

# Your application logic here
log_info "Application started successfully"
```

## Configuration

### Environment Variables

```bash
# Service identification
export SERVICE_NAME="my-service"
export SERVICE_VERSION="1.0.0"
export ENVIRONMENT="production"

# Logging configuration
export LOG_LEVEL="INFO"                    # TRACE, DEBUG, INFO, WARN, ERROR, FATAL
export ENABLE_STRUCTURED_LOGGING="true"    # true/false
export ENABLE_CORRELATION_ID="true"        # true/false
export ENABLE_GCP_LOGGING="true"          # true/false
export LOG_FILE="/var/log/my-service.log"  # Optional file output

# GCP configuration
export GCP_PROJECT="my-gcp-project"
export GCP_REGION="us-central1"
export GCP_CONFIG_DIR="$HOME/.gcloud-isolated"

# Deployment configuration
export DEPLOYMENT_TIMEOUT="1800"          # 30 minutes
export HEALTH_CHECK_TIMEOUT="300"         # 5 minutes
export ROLLBACK_ENABLED="true"
```

## API Reference

### Logging (`logging/logger.sh`)

#### Basic Logging

```bash
# Source the logger
source lib/bash/common/logging/logger.sh

# Basic logging functions
log_trace "Detailed debug information"
log_debug "Debug information"
log_info "General information"
log_warn "Warning message"
log_error "Error occurred"
log_fatal "Fatal error - application will exit"

# Logging with metadata
log_info "User action completed" '{"user_id": "123", "action": "login", "duration_ms": 1500}'
log_error "Database connection failed" '{"host": "db.example.com", "port": 5432, "timeout": 30}'
```

#### Structured Logging

```bash
# Enable structured (JSON) logging
ENABLE_STRUCTURED_LOGGING="true"

# Log with correlation ID
CORRELATION_ID="abc-123-def"
log_info "Processing request" '{"request_id": "req-456", "method": "POST"}'

# Performance logging
log_performance "database_query" "$start_time" "$end_time" "true"

# Time operations
time_operation "backup_database" ./backup_script.sh

# Request/response logging
log_request_start "POST" "/api/users" "user123"
# ... processing ...
log_request_end "201" "1024"
```

#### Correlation ID Management

```bash
# Generate correlation ID
correlation_id=$(generate_correlation_id)

# Execute with correlation ID
with_correlation_id "$correlation_id" some_function arg1 arg2

# Set correlation ID for current process
export CORRELATION_ID="$correlation_id"
```

#### Security and Health Logging

```bash
# Security event logging
log_security_event "login_attempt" "user123" "192.168.1.1" "success"
log_security_event "unauthorized_access" "user456" "10.0.0.1" "blocked"

# Health check logging
log_health_check "database" "healthy" "Connection successful"
log_health_check "redis" "unhealthy" "Connection timeout after 5s"
```

#### GCP Integration

```bash
# Enable GCP Cloud Logging
ENABLE_GCP_LOGGING="true"
GCP_PROJECT="my-project"

# Logs will automatically be sent to GCP Cloud Logging
log_info "Application started"  # Will appear in GCP Console
```

### GCP Authentication (`auth/gcp_auth.sh`)

#### Context Management

```bash
# Source the auth module
source lib/bash/common/auth/gcp_auth.sh

# Create isolated GCP context
create_gcp_context "my-app-dev" "my-gcp-project-dev" "" "us-central1"
create_gcp_context "my-app-prod" "my-gcp-project-prod" "" "us-central1"

# Switch between contexts
switch_gcp_context "my-app-dev"
switch_gcp_context "my-app-prod"

# List available contexts
list_gcp_contexts

# Get current context
current_context=$(get_current_context)
```

#### Authentication Methods

```bash
# Service account authentication
authenticate_service_account "my-app-prod" "/path/to/service-account-key.json"

# User account authentication (interactive)
authenticate_user_account "my-app-dev"

# Setup Application Default Credentials
setup_adc "my-app-dev"

# Check authentication status
if check_auth_status "my-app-prod"; then
    echo "Authenticated successfully"
else
    echo "Authentication required"
fi
```

#### Permission Verification

```bash
# Verify basic permissions
verify_gcp_permissions "my-app-prod"

# Verify specific permissions
verify_gcp_permissions "my-app-prod" \
    "compute.instances.list" \
    "storage.buckets.list" \
    "cloudsql.instances.list"
```

#### Context Execution

```bash
# Execute commands with specific context
with_gcp_context "my-app-prod" gcloud compute instances list
with_gcp_context "my-app-dev" kubectl get pods

# Execute script with context
with_gcp_context "my-app-prod" ./deploy_script.sh
```

### Deployment Utils (`deploy/deployment_utils.sh`)

#### Basic Deployment

```bash
# Source deployment utilities
source lib/bash/common/deploy/deployment_utils.sh

# Deploy application with rolling strategy
deploy_application "my-app" "production" "my-gcp-project" "rolling" "app.yaml"

# Deploy with blue-green strategy
deploy_application "my-app" "staging" "my-gcp-project" "blue_green"

# Deploy with canary strategy (10% traffic, 5 minutes)
deploy_application "my-app" "production" "my-gcp-project" "canary" "" "10" "300"
```

#### Deployment Monitoring

```bash
# Monitor deployment progress
deployment_id="my-app_production_20241201_143000_1234"
monitor_deployment "$deployment_id" 1800  # 30 minutes timeout

# Get deployment status
status=$(get_deployment_status "$deployment_id")
echo "$status" | jq '.status'

# List active deployments
list_active_deployments
```

#### Health Checking

```bash
# Health check service
if health_check_service "my-app-production" "my-gcp-project"; then
    log_info "Service is healthy"
else
    log_error "Service health check failed"
fi

# Custom health check with parameters
health_check_service "my-app-staging" "my-gcp-project" 60 5  # 60 attempts, 5s interval
```

#### Rollback Operations

```bash
# Rollback deployment
rollback_deployment "$deployment_id"

# Rollback to specific version
rollback_deployment "$deployment_id" "v1.2.3"

# Cleanup failed deployment
cleanup_failed_deployment "$deployment_id" "my-app-production" "my-gcp-project"
```

### Common Utils (`utils.sh`)

#### File Operations

```bash
# Source common utilities
source lib/bash/common/utils.sh

# Ensure directory exists
ensure_directory "/var/log/my-app"

# Backup file with timestamp
backup_file "/etc/my-app/config.yaml"

# Load configuration file
if load_config "/etc/my-app/config.sh"; then
    echo "Configuration loaded"
fi
```

#### Project Operations

```bash
# Get project root directory
project_root=$(get_project_root)
echo "Project root: $project_root"

# Validation
if validate_project_name "my-app-123"; then
    echo "Valid project name"
fi

if validate_environment_name "production"; then
    echo "Valid environment"
fi
```

#### GCP Operations

```bash
# Setup GCP isolation
setup_gcp_isolation "my-app" "production" "my-gcp-project"

# Check connectivity
if check_connectivity "google.com" 443; then
    echo "Internet connectivity available"
fi
```

#### Security and Performance

```bash
# Mask sensitive data in logs
safe_output=$(mask_sensitive_data "password=secret123 token=abc456")
echo "$safe_output"  # Output: password=**** token=****

# Measure execution time
measure_time some_long_running_command arg1 arg2

# Error handling (automatic with trap)
# Errors are automatically logged with line numbers and commands
```

## Advanced Usage

### Custom Logging Configuration

```bash
# Create custom log configuration
cat > /etc/my-app/logging.conf << EOF
LOG_LEVEL="DEBUG"
ENABLE_STRUCTURED_LOGGING="true"
ENABLE_GCP_LOGGING="true"
LOG_FILE="/var/log/my-app/application.log"
SERVICE_NAME="my-custom-service"
EOF

# Load configuration
setup_logging "/etc/my-app/logging.conf"
```

### Multi-Environment Deployment

```bash
#!/bin/bash
# deploy_multi_env.sh

source lib/bash/common/deploy/deployment_utils.sh

environments=("dev" "staging" "production")
strategies=("rolling" "rolling" "blue_green")

for i in "${!environments[@]}"; do
    env="${environments[$i]}"
    strategy="${strategies[$i]}"

    log_info "Deploying to $env with $strategy strategy"

    if deploy_application "my-app" "$env" "my-gcp-project-$env" "$strategy"; then
        log_info "Deployment to $env successful"
    else
        log_error "Deployment to $env failed"
        exit 1
    fi
done
```

### Error Handling and Recovery

```bash
#!/bin/bash

# Enable strict error handling
set -euo pipefail

# Source utilities
source lib/bash/common/logging/logger.sh

# Custom error handler
handle_deployment_error() {
    local exit_code=$?
    local line_number=$1

    log_error "Deployment failed at line $line_number" \
        '{"exit_code": '$exit_code', "deployment_id": "'$deployment_id'"}'

    # Attempt rollback
    if [[ "${ROLLBACK_ENABLED:-true}" == "true" ]]; then
        log_info "Attempting automatic rollback"
        rollback_deployment "$deployment_id"
    fi

    exit $exit_code
}

# Set custom error trap
trap 'handle_deployment_error $LINENO' ERR

# Your deployment logic here
```

### Performance Monitoring

```bash
#!/bin/bash

source lib/bash/common/logging/logger.sh

# Performance monitoring wrapper
monitor_performance() {
    local operation="$1"
    shift

    local start_time=$(date +%s.%N)

    log_info "Starting operation: $operation"

    if "$@"; then
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l)

        log_performance "$operation" "$start_time" "$end_time" "true"
        log_info "Operation completed successfully" \
            '{"operation": "'$operation'", "duration_seconds": '$duration'}'
        return 0
    else
        local exit_code=$?
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l)

        log_performance "$operation" "$start_time" "$end_time" "false"
        log_error "Operation failed" \
            '{"operation": "'$operation'", "duration_seconds": '$duration', "exit_code": '$exit_code'}'
        return $exit_code
    fi
}

# Usage
monitor_performance "database_backup" ./backup_database.sh
monitor_performance "deploy_application" deploy_application "my-app" "prod" "my-gcp-project"
```

## Best Practices

1. **Always source utilities at the beginning** of your scripts
2. **Use structured logging** with JSON metadata for better observability
3. **Include correlation IDs** for request tracing across services
4. **Set up proper error handling** with traps and recovery mechanisms
5. **Validate inputs** using the provided validation functions
6. **Use GCP context isolation** to prevent cross-project contamination
7. **Monitor deployment progress** and implement proper rollback procedures
8. **Log security events** for audit and compliance requirements
9. **Measure performance** of critical operations
10. **Use consistent naming** for logs and metrics

## Testing

```bash
# Run utility tests
cd lib/bash/common/
./run_tests.sh

# Test specific modules
./test_logging.sh
./test_auth.sh
./test_deployment.sh
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Make scripts executable
   chmod +x lib/bash/common/**/*.sh
   ```

2. **GCP Authentication Fails**
   ```bash
   # Check gcloud installation
   which gcloud

   # Verify authentication
   gcloud auth list

   # Re-authenticate
   gcloud auth login
   ```

3. **Logging Not Working**
   ```bash
   # Check log level
   echo "Current log level: $LOG_LEVEL"

   # Enable debug logging
   export LOG_LEVEL="DEBUG"
   export DEBUG="true"
   ```

4. **Deployment Timeouts**
   ```bash
   # Increase timeout
   export DEPLOYMENT_TIMEOUT="3600"  # 1 hour
   export HEALTH_CHECK_TIMEOUT="600"  # 10 minutes
   ```

### Debug Mode

```bash
# Enable debug output
export DEBUG="true"
export TRACE="true"
export LOG_LEVEL="DEBUG"

# Run script with verbose output
bash -x ./your_script.sh
```

## Examples

See the `examples/` directory for complete examples:

- **Simple Service Deployment**: Basic deployment with logging
- **Multi-Environment Pipeline**: Deploy across multiple environments
- **Blue-Green Deployment**: Zero-downtime deployment example
- **Monitoring Integration**: Health checking and alerting
- **Security Audit**: Security event logging and monitoring

## Contributing

1. Follow bash best practices and style guidelines
2. Add comprehensive error handling to new functions
3. Include structured logging for all operations
4. Write tests for new functionality
5. Update documentation for any API changes

## License

MIT License - see LICENSE file for details.
