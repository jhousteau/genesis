# Genesis Lifecycle Management

Comprehensive lifecycle management for Genesis services using the **SPIDER methodology** for operational excellence:

- **S**: Symptom identification through health monitoring
- **P**: Problem isolation via component tracking
- **I**: Investigation through comprehensive logging
- **D**: Diagnosis with structured error handling
- **E**: Execution of graceful startup/shutdown
- **R**: Review and continuous improvement

## Features

### 🚀 Startup Management
- **Orchestrated startup sequence** with dependency validation
- **Configuration validation** before service initialization
- **Health check registration** and monitoring setup
- **Warm-up period support** for optimal performance
- **Progressive readiness states** for safe traffic routing
- **Graceful degradation** when optional dependencies fail

### 🛑 Shutdown Management
- **Signal handling** for SIGTERM, SIGINT, and SIGHUP
- **Priority-based shutdown hooks** with configurable timeouts
- **Connection draining** and resource cleanup
- **Graceful termination** with configurable timeouts
- **Resource cleanup orchestration** across all components
- **Comprehensive metrics** for shutdown analysis

### 🔧 Hook System
- **Priority-based execution** with configurable ordering
- **Async and sync hook support** for flexibility
- **Error handling and recovery** with automatic retries
- **Context passing** between hooks for coordination
- **Plugin-style architecture** for extensibility
- **Event-driven lifecycle management** for reactive programming

### 🏥 Health Checks
- **Multiple probe types** (startup, readiness, liveness)
- **Comprehensive health monitoring** across all components
- **Integration with existing monitoring** systems
- **Kubernetes-compatible probes** for cloud-native deployment
- **Automatic degradation detection** and recovery
- **SPIDER methodology** for failure investigation

### ☁️ Cloud-Native Compatibility
- **Kubernetes readiness/liveness probes** out of the box
- **Container signal handling** with proper process management
- **Graceful shutdown** within termination grace period
- **Resource cleanup** for optimal resource utilization
- **Comprehensive metrics** for observability
- **Security-first design** with non-root execution

## Quick Start

### Basic Usage

```python
import asyncio
from core.lifecycle import LifecycleManager, StartupPhase

# Initialize lifecycle manager
lifecycle = LifecycleManager(
    service_name="my-service",
    version="1.0.0",
    environment="production"
)

# Register startup hook
lifecycle.register_startup_hook(
    name="initialize_database",
    callback=setup_database,
    phase=StartupPhase.INITIALIZE_STORAGE,
    timeout=60,
    critical=True
)

# Register shutdown hook
lifecycle.register_shutdown_hook(
    name="close_database",
    callback=cleanup_database,
    phase=400,  # Cleanup phase
    timeout=30
)

# Register health check
lifecycle.register_health_check(
    name="database",
    check_function=check_database_health
)

# Start the service
async def main():
    success = await lifecycle.start()
    if success:
        print("Service ready!")
        lifecycle.wait_for_shutdown()
    lifecycle.stop()

asyncio.run(main())
```

### Advanced Hook Usage

```python
from core.lifecycle import lifecycle_hook, HookEvent, HookPriority

@lifecycle_hook(
    event=HookEvent.PRE_STARTUP,
    priority=HookPriority.HIGH,
    timeout=30
)
def setup_logging(context):
    """Initialize logging before other components"""
    configure_structured_logging()

@lifecycle_hook(
    event=HookEvent.HEALTH_CHECK_FAILED,
    priority=HookPriority.NORMAL
)
async def investigate_health_failure(context):
    """SPIDER methodology implementation"""
    failed_checks = context.get("failed_checks", [])
    await analyze_and_recover(failed_checks)
```

### Dependency Management

```python
# Register external dependencies
lifecycle.register_dependency(
    name="database",
    check_function=lambda: test_db_connection(),
    dependency_type="critical",  # critical, required, optional
    timeout=30,
    retry_attempts=3,
    retry_delay=5
)

lifecycle.register_dependency(
    name="cache",
    check_function=lambda: test_cache_connection(),
    dependency_type="optional",  # Service can run without cache
    timeout=15,
    retry_attempts=2
)
```

## Kubernetes Integration

### Deployment Configuration

```yaml
# Kubernetes deployment with lifecycle management
apiVersion: apps/v1
kind: Deployment
metadata:
  name: genesis-service
spec:
  template:
    spec:
      containers:
      - name: genesis-service
        image: genesis/my-service:1.0.0

        # Startup probe - Genesis initialization
        startupProbe:
          httpGet:
            path: /health/startup
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          failureThreshold: 60  # 5 minutes max

        # Readiness probe - Ready for traffic
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 8080
          periodSeconds: 10
          timeoutSeconds: 3

        # Liveness probe - Process health
        livenessProbe:
          httpGet:
            path: /health/liveness
            port: 8080
          periodSeconds: 30
          timeoutSeconds: 5

        # Graceful shutdown configuration
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "kill -TERM 1; sleep 60"]

        # Environment configuration
        env:
        - name: GENESIS_SERVICE
          value: "my-service"
        - name: LIFECYCLE_STARTUP_TIMEOUT
          value: "300"
        - name: LIFECYCLE_SHUTDOWN_TIMEOUT
          value: "120"

      # Graceful termination period
      terminationGracePeriodSeconds: 180
```

### Health Check Endpoints

The lifecycle manager automatically provides Kubernetes-compatible health check endpoints:

- **`/health/startup`**: Startup probe endpoint
- **`/health/readiness`**: Readiness probe endpoint
- **`/health/liveness`**: Liveness probe endpoint
- **`/status`**: Detailed status and metrics

```python
from core.lifecycle import create_kubernetes_probes

# Create probe functions
probes = create_kubernetes_probes(lifecycle_manager)

# Use with web framework
@app.route('/health/startup')
def startup_probe():
    return jsonify({"healthy": probes["startup"]()})

@app.route('/health/readiness')
def readiness_probe():
    return jsonify({"healthy": probes["readiness"]()})

@app.route('/health/liveness')
def liveness_probe():
    return jsonify({"healthy": probes["liveness"]()})
```

## Docker Integration

### Dockerfile Example

```dockerfile
FROM python:3.11-slim

# Install signal handling utilities
RUN apt-get update && apt-get install -y dumb-init

# Application setup
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Health check script
COPY healthcheck.sh /app/
RUN chmod +x /app/healthcheck.sh

# Non-root user for security
RUN useradd -r -u 1000 genesis
USER genesis

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD /app/healthcheck.sh

# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]
CMD ["python", "-m", "my_service"]
```

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LifecycleManager                         │
│  ┌─────────────────┬─────────────────┬─────────────────────┐ │
│  │  StartupManager │ ShutdownManager │    HookManager      │ │
│  │                 │                 │                     │ │
│  │ • Dependencies  │ • Signal Handle │ • Event System     │ │
│  │ • Validation    │ • Graceful Stop │ • Priority Hooks   │ │
│  │ • Health Checks │ • Resource      │ • Context Passing  │ │
│  │ • Warm-up       │   Cleanup       │ • Error Handling   │ │
│  └─────────────────┴─────────────────┴─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Integration Layer                        │
│  ┌─────────────────┬─────────────────┬─────────────────────┐ │
│  │    Logging      │  Error Handling │     Monitoring      │ │
│  │                 │                 │                     │ │
│  │ • Structured    │ • Error Codes   │ • Health Metrics   │ │
│  │ • Context       │ • Recovery      │ • Performance      │ │
│  │ • Correlation   │ • Classification│ • Observability    │ │
│  └─────────────────┴─────────────────┴─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### SPIDER Methodology Implementation

1. **Symptom Identification**: Health checks detect issues
2. **Problem Isolation**: Component-level failure tracking
3. **Investigation**: Comprehensive logging and context collection
4. **Diagnosis**: Error classification and root cause analysis
5. **Execution**: Automated recovery and mitigation
6. **Review**: Metrics collection and improvement analysis

## Configuration

### Environment Variables

```bash
# Service identification
GENESIS_SERVICE=my-service
GENESIS_ENV=production
GENESIS_VERSION=1.0.0

# Lifecycle timeouts
LIFECYCLE_STARTUP_TIMEOUT=300
LIFECYCLE_SHUTDOWN_TIMEOUT=120
LIFECYCLE_HEALTH_CHECK_INTERVAL=30

# Feature flags
LIFECYCLE_ENABLE_METRICS=true
LIFECYCLE_ENABLE_AUTO_RESTART=false
LIFECYCLE_ENABLE_DEGRADED_MODE=true

# Health check configuration
HEALTH_CHECK_PORT=8080
HEALTH_CHECK_HOST=0.0.0.0
```

### Programmatic Configuration

```python
lifecycle = LifecycleManager(
    service_name="my-service",
    version="1.0.0",
    environment="production",

    # Timeouts
    startup_timeout=300,
    shutdown_timeout=120,
    health_check_interval=30,

    # Features
    enable_health_checks=True,
    enable_metrics=True,
    enable_auto_restart=False
)
```

## Monitoring and Observability

### Metrics

The lifecycle manager exposes comprehensive metrics:

```python
# Get service status
status = lifecycle.get_status()
print(status)

# Output:
{
    "service_name": "my-service",
    "state": "ready",
    "is_ready": true,
    "is_healthy": true,
    "uptime_seconds": 3600.5,
    "startup": {
        "duration_ms": 15000,
        "hooks_executed": 8,
        "dependencies_checked": 3
    },
    "shutdown": {
        "status": "running",
        "hooks_registered": 5
    },
    "health_checks": {
        "registered": 4,
        "overall_healthy": true,
        "results": {
            "database": true,
            "cache": true,
            "application": true
        }
    }
}
```

### Prometheus Integration

```python
from prometheus_client import Counter, Histogram, Gauge

# Lifecycle metrics
startup_duration = Histogram('genesis_startup_duration_seconds')
health_check_failures = Counter('genesis_health_check_failures_total')
service_state = Gauge('genesis_service_state')
```

## Best Practices

### 1. Startup Hooks
- Keep hooks focused and single-purpose
- Use appropriate timeouts for each hook
- Mark critical vs non-critical hooks appropriately
- Implement proper error handling and logging

### 2. Shutdown Hooks
- Order hooks by priority (high to low)
- Implement graceful resource cleanup
- Use appropriate timeouts
- Handle partial failures gracefully

### 3. Health Checks
- Implement lightweight, fast checks
- Test actual functionality, not just process existence
- Use different probe types appropriately
- Monitor health check performance

### 4. Dependencies
- Classify dependencies correctly (critical/required/optional)
- Implement retries with exponential backoff
- Provide meaningful error messages
- Test dependency failures regularly

### 5. Cloud-Native Deployment
- Use appropriate termination grace periods
- Implement proper signal handling
- Monitor resource usage during lifecycle events
- Test in realistic failure scenarios

## Troubleshooting

### Common Issues

1. **Startup Timeout**
   ```
   Check startup hooks for performance issues
   Verify dependency connectivity
   Review initialization order
   ```

2. **Health Check Failures**
   ```
   Examine health check implementation
   Check resource availability
   Review error logs and metrics
   ```

3. **Graceful Shutdown Issues**
   ```
   Verify signal handling setup
   Check hook execution order
   Review resource cleanup logic
   ```

### Debug Mode

```python
# Enable debug logging
import os
os.environ['GENESIS_LOG_LEVEL'] = 'DEBUG'

# Get detailed status
status = lifecycle.get_status()
metrics = lifecycle.get_metrics()
```

## Contributing

The lifecycle management system is designed for extensibility:

1. **Custom Hooks**: Implement `LifecycleHook` for complex logic
2. **Health Checks**: Add service-specific health validation
3. **Dependencies**: Create custom dependency checks
4. **Integrations**: Extend for new monitoring systems

See the [integration example](integration_example.py) for comprehensive usage patterns.
