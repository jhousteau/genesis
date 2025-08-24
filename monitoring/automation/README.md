# Monitoring Automation

Comprehensive automation system for Universal Platform monitoring that provides intelligent service discovery, dynamic configuration management, and autonomous monitoring operations.

## Features

- **Intelligent Service Discovery**: Automatically discover services across Kubernetes, Consul, Prometheus, and cloud platforms
- **Dynamic Configuration Management**: Automatically update monitoring configurations based on service changes
- **Autonomous Operations**: Self-healing monitoring stack with automated remediation
- **SLO Monitoring**: Continuous SLO compliance tracking with error budget management
- **Cost Optimization**: Automated cost analysis and optimization recommendations
- **Security Monitoring**: Real-time security event monitoring and threat detection
- **Performance Tuning**: Automatic performance analysis and optimization suggestions
- **Capacity Planning**: Predictive capacity planning with trend analysis

## Architecture

```
automation/
├── README.md                    # This documentation
├── service-discovery.py         # Multi-platform service discovery
├── config-manager.py           # Dynamic configuration management
├── orchestrator.py             # Main automation orchestrator
├── discovery-config.yaml       # Service discovery configuration
├── config-manager.yaml         # Configuration manager settings
├── orchestrator-config.yaml    # Orchestrator configuration
└── templates/                  # Configuration templates
    ├── prometheus.yml.j2        # Prometheus configuration template
    ├── alertmanager.yml.j2      # Alertmanager configuration template
    └── jaeger.yml.j2           # Jaeger configuration template
```

## Quick Start

### 1. Deploy Orchestrator

```bash
# Start the monitoring orchestrator
python orchestrator.py --config orchestrator-config.yaml --daemon

# Check status
python orchestrator.py --status
```

### 2. Manual Service Discovery

```bash
# Run single discovery cycle
python service-discovery.py --config discovery-config.yaml

# Run continuous discovery
python service-discovery.py --config discovery-config.yaml --continuous

# Output targets for Prometheus
python service-discovery.py --output-targets targets.json
```

### 3. Configuration Management

```bash
# Update all configurations based on discovered services
python config-manager.py --config config-manager.yaml --update-all

# Dry run to see what would change
python config-manager.py --config config-manager.yaml --update-all --dry-run

# Check update status
python config-manager.py --status
```

## Service Discovery

### Supported Platforms

#### Kubernetes
Discovers services and deployments with full metadata extraction:

```yaml
kubernetes:
  in_cluster: true
  namespace: "default"
  annotation_mappings:
    "monitoring.universal-platform/team": "team"
    "monitoring.universal-platform/language": "language"
    "monitoring.universal-platform/framework": "framework"
```

#### Prometheus
Discovers services from existing Prometheus targets:

```yaml
prometheus:
  url: "http://prometheus:9090"
  query_timeout: 30
```

#### Consul
Discovers services from Consul service registry:

```yaml
consul:
  host: "consul"
  port: 8500
  datacenter: "dc1"
```

#### Google Cloud Platform
Discovers compute instances with monitoring labels:

```yaml
gcp:
  project_id: "my-project"
  zones: ["us-central1-a"]
  instance_filters: ["labels.monitoring=enabled"]
```

### Service Metadata

Discovered services include comprehensive metadata:

```json
{
  "name": "user-service",
  "type": "api_service",
  "environment": "production",
  "namespace": "default",
  "host": "user-service.default.svc.cluster.local",
  "port": 8080,
  "protocol": "http",
  "health_check_path": "/health",
  "metrics_path": "/metrics",
  "team": "platform",
  "language": "python",
  "framework": "fastapi",
  "version": "1.2.3",
  "monitoring_enabled": true
}
```

## Dynamic Configuration Management

### Supported Components

- **Prometheus**: Automatic scrape configuration generation
- **Alertmanager**: Team-based alert routing configuration
- **Grafana**: Datasource and dashboard provisioning
- **Jaeger**: Tracing configuration management
- **Loki**: Log aggregation configuration

### Configuration Templates

Uses Jinja2 templates for flexible configuration generation:

```yaml
# prometheus.yml.j2
scrape_configs:
{% for service in services %}
  {% if service.monitoring_enabled %}
  - job_name: '{{ service.name }}-{{ service.environment }}'
    static_configs:
      - targets: ['{{ service.host }}:{{ service.port }}']
        labels:
          service: '{{ service.name }}'
          team: '{{ service.team }}'
  {% endif %}
{% endfor %}
```

### Automatic Updates

Configurations are automatically updated when:
- New services are discovered
- Existing services change
- Service metadata is updated
- Services are removed

## Automation Features

### SLO Monitoring

Continuous monitoring of Service Level Objectives:

- **Error Budget Tracking**: Monitor error budget consumption
- **Burn Rate Analysis**: Multi-window burn rate alerts
- **SLO Compliance**: Track compliance across all services
- **Automatic Alerting**: Alert when SLOs are at risk

```yaml
slo_monitoring:
  error_budget_alert_thresholds: [50, 75, 90]
  burn_rate_windows: ["1h", "6h", "24h", "72h"]
```

### Cost Optimization

Automated cost analysis and optimization:

- **Resource Utilization**: Identify underutilized resources
- **Cost Anomaly Detection**: Detect unusual spending patterns
- **Optimization Recommendations**: Suggest cost-saving measures
- **Trend Analysis**: Analyze cost trends and forecasts

### Security Monitoring

Real-time security event monitoring:

- **Authentication Failures**: Monitor login attempts
- **Privilege Escalation**: Detect privilege escalation attempts
- **Network Anomalies**: Identify suspicious network activity
- **Compliance Checking**: Ensure compliance with security policies

### Performance Tuning

Automatic performance analysis:

- **Response Time Analysis**: Monitor response time trends
- **Throughput Optimization**: Identify throughput bottlenecks
- **Resource Optimization**: Optimize resource allocation
- **Performance Recommendations**: Suggest performance improvements

### Capacity Planning

Predictive capacity planning:

- **Growth Forecasting**: Predict future resource needs
- **Capacity Alerts**: Alert when capacity limits are approached
- **Seasonal Analysis**: Account for seasonal usage patterns
- **Resource Planning**: Plan resource allocation

## Configuration Reference

### Service Discovery Configuration

```yaml
# discovery-config.yaml
discovery_interval: 60
service_ttl: 300
enabled_methods:
  - kubernetes
  - prometheus
  - consul

kubernetes:
  in_cluster: true
  namespace: "default"
  annotation_mappings:
    "monitoring.universal-platform/team": "team"

output:
  prometheus_file: "/etc/prometheus/targets/services.json"
  service_registry: "/var/lib/monitoring/services.json"
```

### Configuration Manager Settings

```yaml
# config-manager.yaml
backup_enabled: true
backup_retention_days: 7
dry_run: false

configurations:
  prometheus:
    config_file: "/etc/prometheus/prometheus.yml"
    reload_url: "http://prometheus:9090/-/reload"
    template: "prometheus.yml.j2"

teams:
  platform:
    slack_channel: "#platform-alerts"
    email_addresses: ["platform@company.com"]
```

### Orchestrator Configuration

```yaml
# orchestrator-config.yaml
discovery_interval: 60
config_update_interval: 300

automation_features:
  auto_scaling_alerts: true
  slo_monitoring: true
  cost_optimization: true
  security_monitoring: true

thresholds:
  service_change_threshold: 0.1
  slo_violation_threshold: 0.05
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "orchestrator.py", "--daemon"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: monitoring-orchestrator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: monitoring-orchestrator
  template:
    metadata:
      labels:
        app: monitoring-orchestrator
    spec:
      serviceAccountName: monitoring-orchestrator
      containers:
      - name: orchestrator
        image: universal-platform/monitoring-orchestrator:latest
        args: ["--daemon"]
        env:
        - name: LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: prometheus-config
          mountPath: /etc/prometheus
        - name: grafana-config
          mountPath: /etc/grafana
      volumes:
      - name: config
        configMap:
          name: orchestrator-config
      - name: prometheus-config
        persistentVolumeClaim:
          claimName: prometheus-config
      - name: grafana-config
        persistentVolumeClaim:
          claimName: grafana-config
```

### Required Permissions

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: monitoring-orchestrator
rules:
- apiGroups: [""]
  resources: ["services", "pods", "endpoints"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["extensions"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch"]
```

## API Reference

### Status Endpoint

```bash
curl http://orchestrator:8080/status
```

Response:
```json
{
  "status": "running",
  "metrics": {
    "discovery_cycles": 1440,
    "config_updates": 48,
    "services_discovered": 25,
    "uptime_seconds": 86400
  },
  "services_count": 25
}
```

### Services Endpoint

```bash
curl http://orchestrator:8080/services
```

### Metrics Endpoint

```bash
curl http://orchestrator:8080/metrics
```

## Monitoring the Monitor

### Self Metrics

The orchestrator exposes metrics about its own operation:

```
# Discovery metrics
orchestrator_discovery_cycles_total
orchestrator_services_discovered
orchestrator_discovery_duration_seconds

# Configuration metrics
orchestrator_config_updates_total
orchestrator_config_update_success_rate
orchestrator_config_update_duration_seconds

# Health metrics
orchestrator_component_health_status
orchestrator_uptime_seconds
```

### Health Checks

Health check endpoint provides component status:

```bash
curl http://orchestrator:8081/health
```

### Logging

Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2024-12-01T14:30:00Z",
  "level": "INFO",
  "component": "service_discovery",
  "message": "Discovered 25 services",
  "correlation_id": "abc-123-def",
  "services_count": 25,
  "discovery_method": "kubernetes"
}
```

## Troubleshooting

### Common Issues

1. **Service Discovery Fails**
   ```bash
   # Check Kubernetes permissions
   kubectl auth can-i list services --as=system:serviceaccount:default:monitoring-orchestrator

   # Verify Prometheus connectivity
   curl http://prometheus:9090/api/v1/targets
   ```

2. **Configuration Updates Fail**
   ```bash
   # Check file permissions
   ls -la /etc/prometheus/prometheus.yml

   # Test configuration syntax
   promtool check config /etc/prometheus/prometheus.yml
   ```

3. **Orchestrator Not Starting**
   ```bash
   # Check logs
   docker logs monitoring-orchestrator

   # Verify configuration
   python orchestrator.py --config orchestrator-config.yaml --status
   ```

### Debug Mode

Enable debug logging:

```yaml
log_level: DEBUG
```

### Validation Mode

Run in dry-run mode to validate changes:

```bash
python config-manager.py --dry-run --update-all
```

## Integration Examples

### Webhook Integration

```python
# Custom webhook handler
@app.route('/monitoring-webhook', methods=['POST'])
def handle_monitoring_webhook():
    data = request.json
    if data['type'] == 'service_discovery':
        # Handle service discovery events
        process_service_changes(data['services'])
    return {'status': 'success'}
```

### Slack Integration

```yaml
notification:
  slack_channels:
    - "#monitoring-automation"
  webhook_urls:
    - "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
```

### Custom Automation

```python
# Add custom automation features
class CustomAutomation:
    async def analyze_custom_metrics(self):
        # Custom analysis logic
        pass

    async def optimize_custom_resources(self):
        # Custom optimization logic
        pass
```

## Best Practices

1. **Service Labeling**: Use consistent labels across all services
2. **Team Ownership**: Assign clear team ownership to services
3. **Monitoring Hygiene**: Regularly review and cleanup monitoring configurations
4. **Testing**: Test configuration changes in non-production environments
5. **Documentation**: Document custom metrics and business logic
6. **Security**: Use appropriate RBAC and service account permissions
7. **Backup**: Maintain backups of monitoring configurations
8. **Monitoring**: Monitor the monitoring automation itself

## License

MIT License - see LICENSE file for details.
