# Monitoring Terraform Modules

Infrastructure-as-Code modules for provisioning comprehensive monitoring infrastructure on Google Cloud Platform and other cloud providers.

## Architecture

```
modules/
├── gcp-monitoring/        # Google Cloud Monitoring setup
├── prometheus/           # Prometheus and Grafana deployment
├── jaeger/              # Distributed tracing infrastructure
├── log-aggregation/     # Centralized logging setup
├── alerting/            # Alert manager and notification setup
├── dashboards/          # Dashboard provisioning automation
└── cost-monitoring/     # Cost tracking and optimization
```

## Modules Overview

### GCP Monitoring (`gcp-monitoring/`)
- Google Cloud Monitoring workspace setup
- Custom metrics and dashboards
- Alert policies and notification channels
- Log-based metrics and monitoring
- Integration with Cloud Operations suite

### Prometheus Stack (`prometheus/`)
- Prometheus server deployment (GKE or Compute Engine)
- Grafana dashboard server
- AlertManager for notification routing
- Service discovery configuration
- Persistent storage setup

### Jaeger Tracing (`jaeger/`)
- Jaeger collector and query services
- Elasticsearch backend for trace storage
- Load balancer and ingress configuration
- Auto-scaling and resource management
- Integration with OpenTelemetry

### Log Aggregation (`log-aggregation/`)
- Fluentd/Fluent Bit deployment
- Google Cloud Logging integration
- ELK stack setup (optional)
- Log parsing and enrichment
- Retention and archival policies

### Alerting Infrastructure (`alerting/`)
- PagerDuty service and integration setup
- Slack webhook and bot configuration
- Email notification services
- Alert routing and escalation rules
- Incident response automation

### Dashboard Automation (`dashboards/`)
- Grafana dashboard provisioning
- Google Cloud Console dashboard creation
- Template-based dashboard generation
- Team-specific dashboard deployment
- Access control and permissions

### Cost Monitoring (`cost-monitoring/`)
- Billing export and analysis setup
- Cost anomaly detection
- Budget alerts and notifications
- Resource optimization recommendations
- Cost allocation and chargeback

## Usage Patterns

### Basic Monitoring Setup
```hcl
module "basic_monitoring" {
  source = "./modules/gcp-monitoring"

  project_id = var.project_id
  environment = var.environment
  services = var.monitored_services

  notification_channels = {
    email = ["team@company.com"]
    slack = ["https://hooks.slack.com/..."]
  }
}
```

### Complete Observability Stack
```hcl
module "observability" {
  source = "./modules/complete-stack"

  project_id = var.project_id
  environment = var.environment
  cluster_name = var.gke_cluster_name

  enable_prometheus = true
  enable_jaeger = true
  enable_log_aggregation = true
  enable_cost_monitoring = true
}
```

### Production-Grade Setup
```hcl
module "production_monitoring" {
  source = "./modules/production-stack"

  project_id = var.project_id
  environment = "production"
  region = var.region

  high_availability = true
  backup_enabled = true
  retention_days = 90

  alert_severity_routing = {
    critical = "pagerduty"
    warning = "slack"
    info = "email"
  }
}
```

## Features

### Multi-Environment Support
- Environment-specific configurations
- Resource naming conventions
- Scaling parameters by environment
- Cost optimization per environment
- Security policies by environment

### High Availability
- Multi-zone deployments
- Automatic failover capabilities
- Data replication and backup
- Disaster recovery procedures
- Health check automation

### Auto-Scaling
- Kubernetes HPA for monitoring services
- Compute Engine instance groups
- Storage auto-expansion
- Network bandwidth scaling
- Cost-aware scaling policies

### Security Integration
- IAM roles and service accounts
- VPC and firewall configurations
- Secret management integration
- Audit logging enablement
- Compliance policy enforcement

### Cost Optimization
- Resource right-sizing
- Committed use discount utilization
- Preemptible instance usage
- Storage tier optimization
- Network cost minimization

## Integration Points

### Platform Integration
- Automatic service discovery
- Zero-configuration setup
- Template-driven deployment
- CI/CD pipeline integration
- Infrastructure as Code practices

### Existing Infrastructure
- VPC and network integration
- IAM and security alignment
- Resource sharing and optimization
- Compliance requirement alignment
- Migration path support
