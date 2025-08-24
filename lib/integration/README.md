# System Integration Framework

This directory contains the complete system integration framework for the Universal Project Platform. It provides unified interfaces and orchestration for all 8 core components with zero coupling and maximum cohesion.

## Architecture Overview

The integration framework consists of 4 core components that work together to provide seamless inter-component communication:

```
┌─────────────────────────────────────────────────────────────┐
│                   System Integrator                        │
│              (Main orchestration layer)                    │
├─────────────────────────────────────────────────────────────┤
│  Component     │  Event Bus     │  Config        │ Health   │
│  Registry      │  (Pub/Sub)     │  Manager       │ Aggreg.  │
│  (Discovery)   │  (Messaging)   │  (Unified Cfg) │ (Monitor)│
└─────────────────────────────────────────────────────────────┘
                             │
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
┌───▼───┐  ┌───▼───┐  ┌─────▼─────┐  ┌──▼──┐  ┌─────▼─────┐
│  CLI  │  │Monitor│  │Intelligence│  │Deploy│  │ 4 More... │
│       │  │       │  │           │  │      │  │           │
└───────┘  └───────┘  └───────────┘  └──────┘  └───────────┘
```

## Core Components

### 1. Component Registry (`component_registry.py`)
**Service Discovery and Registration System**

- **Purpose**: Central registry for all platform components
- **Features**:
  - Component registration and discovery
  - Health monitoring and heartbeat tracking
  - Dependency management and validation
  - Automatic service discovery
  - State management and lifecycle tracking

```python
from integration import register_component, ComponentType

# Register a new component
component_id = register_component(
    name="my_service",
    component_type=ComponentType.CUSTOM,
    version="1.0.0",
    description="My custom service",
    capabilities=["data_processing"],
    dependencies=["database"]
)
```

### 2. Event Bus (`event_bus.py`)
**Asynchronous Pub/Sub Messaging System**

- **Purpose**: Decoupled communication between components
- **Features**:
  - Priority-based event queuing
  - Sync and async event handlers
  - Request-reply patterns
  - Event filtering and pattern matching
  - Dead letter queue for failed events
  - Event history and replay

```python
from integration import publish_event, subscribe_to_events, EventType

# Publish an event
event_id = publish_event(
    event_type=EventType.DEPLOY_STARTED,
    data={"project": "my-app", "env": "prod"},
    source="deployment_engine"
)

# Subscribe to events
def handle_deployment(event):
    print(f"Deployment started: {event.data}")

subscribe_to_events(
    pattern="deploy.*",
    callback=handle_deployment,
    subscriber_id="monitor"
)
```

### 3. Configuration Manager (`config_manager.py`)
**Unified Configuration Management**

- **Purpose**: Centralized configuration for all components
- **Features**:
  - Multiple configuration sources with priority
  - Hot-reload on configuration changes
  - Environment variable substitution
  - Schema validation
  - Configuration inheritance and overrides
  - Secure handling of sensitive values

```python
from integration import get_config, set_config

# Get configuration value
debug_mode = get_config("system.debug", default=False)

# Set configuration value
set_config("components.monitor.interval", 60, persist=True)

# Listen for configuration changes
def on_config_change(key, old_value, new_value):
    print(f"Config changed: {key} = {new_value}")

config_manager.add_listener("monitor.*", on_config_change)
```

### 4. Health Aggregator (`health_aggregator.py`)
**System-wide Health Monitoring**

- **Purpose**: Aggregate health status from all components
- **Features**:
  - Multiple health check types (liveness, readiness, startup)
  - Component health scoring and aggregation
  - Health history and trend analysis
  - Configurable alerting and thresholds
  - Health report generation
  - Automated health checks

```python
from integration import add_health_check, get_system_health, HealthCheck, CheckType

# Add a health check
health_check = HealthCheck(
    name="api_responsive",
    component="api_server",
    check_type=CheckType.READINESS,
    endpoint="http://localhost:8080/health",
    critical=True
)
add_health_check(health_check)

# Get system health
health = get_system_health()
print(f"System health: {health.status} ({health.score:.1%})")
```

## Integration Points

### CLI ↔ All Components
The CLI component integrates with all other components through the integration framework:

```python
# CLI can discover and interact with any component
from integration import discover_components, ComponentType

# Find all monitoring components
monitors = discover_components(component_type=ComponentType.MONITORING)
for monitor in monitors:
    print(f"Found monitor: {monitor.metadata.name}")
```

### Registry ↔ All Components
All components automatically register themselves and can discover others:

```python
# Components automatically register on startup
component_id = integrate_component(
    name="new_service",
    component_type=ComponentType.CUSTOM,
    config={"port": 8080, "workers": 4}
)
```

### Monitoring ↔ All Components
The monitoring system automatically collects metrics from all registered components:

```python
# Health checks are automatically added for registered components
# Metrics are collected and aggregated
# Alerts are triggered based on thresholds
```

### Intelligence ↔ All Components
The intelligence layer can analyze and optimize all components:

```python
# AI can analyze component performance
# Generate optimization recommendations
# Apply auto-fixes where appropriate
```

### Deployment ↔ Infrastructure
Deployment orchestration works seamlessly with infrastructure management:

```python
# Deployment triggers infrastructure provisioning
# Infrastructure changes trigger deployment updates
# Both coordinate through the event bus
```

### Isolation ↔ Security
Environment isolation integrates with security policies:

```python
# Credential rotation triggers isolation updates
# Security policy changes affect isolation rules
# Both work together to maintain security
```

## Usage Examples

### Basic Integration
```python
from integration import get_system_integrator

# Initialize the integration system
integrator = get_system_integrator()

# Add a new component
component_id = integrator.integrate_new_component(
    name="payment_processor",
    component_type=ComponentType.CUSTOM,
    capabilities=["payment_processing", "fraud_detection"],
    dependencies=["database", "external_api"],
    config={
        "api_key": "${PAYMENT_API_KEY}",
        "timeout": 30,
        "retry_attempts": 3
    }
)

# Start monitoring
integrator.start_monitoring()

# Get integration status
status = integrator.get_integration_status()
print(f"System health: {status['overall_health']}")
print(f"Components: {status['registry']['total_components']}")
```

### Event-Driven Workflow
```python
from integration import publish_event, subscribe_to_events, EventType

# Set up event handlers
def handle_deployment_start(event):
    # Provision infrastructure
    publish_event(
        event_type="infrastructure.provision",
        data=event.data,
        source="infrastructure_manager"
    )

def handle_infrastructure_ready(event):
    # Deploy application
    publish_event(
        event_type=EventType.DEPLOY_STARTED,
        data=event.data,
        source="deployment_engine"
    )

# Subscribe to events
subscribe_to_events("deploy.requested", handle_deployment_start)
subscribe_to_events("infrastructure.ready", handle_infrastructure_ready)

# Trigger the workflow
publish_event(
    event_type="deploy.requested",
    data={"project": "my-app", "env": "production"},
    source="user"
)
```

### Configuration Management
```python
from integration import get_config_manager

config_manager = get_config_manager()

# Set up configuration hierarchy
config_manager.set("global.timeout", 30)
config_manager.set("components.api.timeout", 60)  # Override for API
config_manager.set("environments.production.timeout", 120)  # Override for prod

# Get effective configuration
api_timeout = config_manager.get("components.api.timeout")  # Returns 60
prod_timeout = config_manager.get("environments.production.timeout")  # Returns 120
```

### Health Monitoring
```python
from integration import get_health_aggregator, HealthCheck, CheckType

health_aggregator = get_health_aggregator()

# Add comprehensive health checks
checks = [
    HealthCheck(
        name="database_connection",
        component="api_server",
        check_type=CheckType.READINESS,
        function=lambda: test_database_connection(),
        critical=True
    ),
    HealthCheck(
        name="external_api_responsive",
        component="api_server",
        check_type=CheckType.LIVENESS,
        endpoint="https://api.external.com/health",
        timeout=5,
        critical=False
    )
]

for check in checks:
    health_aggregator.add_check(check)

# Start monitoring
health_aggregator.start_monitoring()

# Get detailed health report
print(health_aggregator.export_health_report())
```

## Testing

The integration framework includes comprehensive tests:

```bash
# Run all integration tests
python3 -m lib.integration.integration_test

# Run the interactive demo
./bin/integration-demo --component all

# Test specific components
./bin/integration-demo --component registry
./bin/integration-demo --component events
./bin/integration-demo --component config
./bin/integration-demo --component health
```

## Configuration

Integration behavior is controlled through configuration files:

- `config/global.yaml` - Global platform configuration including integration settings
- `lib/integration/registry.yaml` - Component registry configuration
- Environment variables for sensitive values

Key configuration sections:
```yaml
integration:
  registry:
    enabled: true
    auto_discovery: true
    health_check_interval: 30

  event_bus:
    enabled: true
    max_queue_size: 10000
    delivery_timeout: 5

  config_manager:
    enabled: true
    hot_reload: true
    validation_enabled: true

  health_aggregator:
    enabled: true
    aggregation_strategy: "weighted"
    alert_on_degraded: true
```

## Best Practices

### Component Integration
1. **Register Early**: Register components as soon as they start
2. **Provide Health Checks**: Always implement health endpoints
3. **Use Events**: Communicate through events, not direct calls
4. **Configuration**: Use the unified configuration system
5. **Dependencies**: Declare dependencies explicitly

### Event Communication
1. **Use Appropriate Priorities**: Critical events should use high priority
2. **Meaningful Event Types**: Use descriptive event types
3. **Include Context**: Provide sufficient data in event payloads
4. **Handle Failures**: Implement error handling for event processing
5. **Avoid Loops**: Be careful not to create event loops

### Configuration Management
1. **Hierarchical**: Use hierarchical configuration keys
2. **Environment Specific**: Separate configuration by environment
3. **Sensitive Data**: Use environment variables for secrets
4. **Validation**: Provide schemas for configuration validation
5. **Documentation**: Document all configuration options

### Health Monitoring
1. **Multiple Check Types**: Use different check types appropriately
2. **Meaningful Names**: Use descriptive health check names
3. **Proper Timeouts**: Set appropriate timeouts for checks
4. **Critical Classification**: Mark critical checks appropriately
5. **Regular Review**: Review and update health checks regularly

## Zero Coupling Design

The integration framework ensures zero coupling between components:

1. **No Direct Dependencies**: Components don't directly import each other
2. **Event-Driven**: All communication happens through events
3. **Configuration Isolation**: Each component has its own configuration namespace
4. **Interface Contracts**: Components interact only through well-defined interfaces
5. **Graceful Degradation**: Components continue working if others fail

## Maximum Cohesion

Each integration component has a single, well-defined responsibility:

1. **Component Registry**: Only handles service discovery and registration
2. **Event Bus**: Only handles message passing and routing
3. **Configuration Manager**: Only handles configuration management
4. **Health Aggregator**: Only handles health monitoring and aggregation
5. **System Integrator**: Only orchestrates the other components

This design ensures the system is maintainable, scalable, and robust.
