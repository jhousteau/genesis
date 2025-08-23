# VM Management Layer Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying and managing the Genesis VM Management Layer (Issue #30). The VM Management Layer is designed to support the agent-cage migration and provides scalable, secure VM infrastructure for Genesis agents following the PIPES methodology.

## Prerequisites

### 1. GCP Project Setup
```bash
# Set up GCP project and enable APIs
export PROJECT_ID="your-genesis-project"
export REGION="us-central1"

gcloud config set project $PROJECT_ID
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable cloudkms.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com
```

### 2. Terraform Configuration
```bash
# Initialize Terraform in your environment
cd environments/dev  # or prod
terraform init
terraform workspace new vm-management  # optional
```

### 3. Service Account Creation
```bash
# Create service account for agent VMs
gcloud iam service-accounts create genesis-agent-dev \
    --display-name="Genesis Agent Service Account" \
    --description="Service account for Genesis agent VMs"

# Assign necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:genesis-agent-dev@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/compute.instanceAdmin.v1"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:genesis-agent-dev@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/monitoring.metricWriter"
```

## Deployment Steps

### Step 1: Configure Network Infrastructure

Ensure you have the necessary VPC and subnet configured:

```hcl
# Example network configuration (if not already exists)
resource "google_compute_network" "genesis_vpc" {
  name                    = "genesis-vpc-${var.environment}"
  auto_create_subnetworks = false
  project                 = var.project_id
}

resource "google_compute_subnetwork" "genesis_subnet" {
  name          = "genesis-subnet-${var.environment}"
  ip_cidr_range = "10.0.0.0/16"
  region        = var.region
  network       = google_compute_network.genesis_vpc.id
  project       = var.project_id
}
```

### Step 2: Deploy Development Environment

Use the development example for initial testing:

```bash
cd environments/dev
terraform plan -var-file="vm-management-example.tf"
terraform apply -var-file="vm-management-example.tf"
```

### Step 3: Verify Deployment

```bash
# Check VM templates
gcloud compute instance-templates list --filter="labels.genesis-managed=true"

# Check managed instance groups
gcloud compute instance-groups managed list --filter="labels.genesis-managed=true"

# Check health checks
gcloud compute health-checks list --filter="labels.genesis-managed=true"
```

### Step 4: Test Agent Functionality

```bash
# Use Genesis CLI to test VM management
g vm list-pools
g vm list-instances
g vm health-check --pool backend-dev-pool

# Test agent startup
g vm create-pool --type backend-developer --size 1 --environment dev
```

## CLI Usage Examples

### Basic VM Pool Management

```bash
# Create a new agent pool
g vm create-pool \
    --type backend-developer \
    --size 3 \
    --machine-type e2-standard-2 \
    --zones us-central1-a,us-central1-b \
    --preemptible

# Scale existing pool
g vm scale-pool backend-pool \
    --min 2 \
    --max 10 \
    --enable-autoscaling

# Check pool health
g vm health-check --pool backend-pool

# List all resources
g vm list-pools
g vm list-instances
g vm list-templates
```

### Advanced Operations

```bash
# Update VM template
g vm update-template backend-dev \
    --image projects/genesis/global/images/agent-ubuntu-2204-v2 \
    --machine-type e2-standard-4

# Instance lifecycle management
g vm start --pool backend-pool
g vm stop --instance backend-001
g vm restart --pool frontend-pool

# Monitoring and troubleshooting
g vm health-check --instance backend-001 --verbose
g vm logs --pool backend-pool --follow
```

## Environment-Specific Configurations

### Development Environment

**Key Features:**
- Cost-optimized with preemptible instances
- Open firewall rules for development access
- Smaller machine types and disk sizes
- Aggressive autoscaling for cost control

```hcl
# Development configuration highlights
default_preemptible = true
enable_external_ip = true
firewall_rules = {
  "allow-dev-access" = {
    source_ranges = ["0.0.0.0/0"]  # Open for development
    target_tags   = ["agent-vm"]
  }
}
```

### Production Environment

**Key Features:**
- High availability across multiple zones
- Enhanced security with no external IPs
- Larger, high-performance machine types
- Conservative autoscaling policies
- Comprehensive monitoring and alerting

```hcl
# Production configuration highlights
default_preemptible = false
enable_external_ip = false
enable_confidential_compute = true  # For sensitive workloads
min_replicas = 3  # HA requirement
firewall_rules = {
  "allow-internal-only" = {
    source_ranges = ["10.0.0.0/8"]  # Internal VPC only
    target_tags   = ["agent-vm"]
  }
}
```

## Agent Types and Configurations

### Backend Developer Agents

**Resources:** 2-4 vCPUs, 8-16 GB RAM, 100-200 GB workspace
**Tools:** Python, Node.js, Go, Docker, development databases
**Networking:** Internal access with HTTP/HTTPS ports for development servers

```bash
# Deploy backend agents
g vm create-pool \
    --type backend-developer \
    --size 5 \
    --machine-type e2-standard-4 \
    --enable-autoscaling
```

### Platform Engineer Agents

**Resources:** 4-8 vCPUs, 16-32 GB RAM, 200-500 GB workspace
**Tools:** Terraform, Kubernetes, Helm, cloud SDKs, monitoring tools
**Networking:** Full GCP API access, internal connectivity

```bash
# Deploy platform engineering agents
g vm create-pool \
    --type platform-engineer \
    --size 2 \
    --machine-type c2-standard-8 \
    --zones us-central1-a,us-central1-b,us-central1-c
```

### Security Agents

**Resources:** 2-4 vCPUs, 8-16 GB RAM, 100-200 GB workspace
**Tools:** Security scanners, compliance tools, vulnerability assessments
**Networking:** Restricted access with specialized firewall rules

```bash
# Deploy security agents with isolation
g vm create-pool \
    --type security-agent \
    --size 1 \
    --machine-type e2-standard-4 \
    --enable-confidential-compute
```

## Monitoring and Alerting

### Health Checks

The VM Management Layer includes comprehensive health checks:

```bash
# Check individual agent health
curl http://AGENT_IP:8080/health

# Example health response
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "agent_type": "backend-developer",
  "environment": "prod",
  "uptime": 3600,
  "version": "1.2.3"
}
```

### Metrics Collection

Agents export Prometheus-compatible metrics:

```bash
# Agent metrics endpoint
curl http://AGENT_IP:9090/metrics

# Key metrics include:
# - agent_tasks_completed_total
# - agent_cpu_utilization_percent
# - agent_memory_usage_bytes
# - agent_disk_usage_percent
```

### Cloud Operations Integration

```bash
# View agent logs in Cloud Logging
gcloud logging read \
    "resource.type=gce_instance AND labels.agent_type=backend-developer" \
    --limit 50 \
    --format="value(timestamp,severity,textPayload)"

# Monitor autoscaling events
gcloud logging read \
    "resource.type=gce_autoscaler AND protoPayload.methodName=compute.autoscalers.patch"
```

## Troubleshooting

### Common Issues

#### 1. Agent Startup Failures

**Symptoms:** Instances start but agents don't become healthy
```bash
# Check startup script logs
gcloud compute instances get-serial-port-output INSTANCE_NAME \
    --zone=ZONE \
    --port=1

# SSH to instance and check logs
gcloud compute ssh INSTANCE_NAME --zone=ZONE
sudo journalctl -u agent-runtime -f
```

**Solutions:**
- Verify agent-cage binary is accessible
- Check service account permissions
- Ensure workspace disk is properly mounted

#### 2. Autoscaling Not Working

**Symptoms:** Pools don't scale despite high CPU utilization
```bash
# Check autoscaler status
gcloud compute autoscalers describe AUTOSCALER_NAME \
    --region=REGION \
    --format="value(status,recommendedSize)"

# Review autoscaling events
gcloud logging read \
    "resource.type=gce_autoscaler AND resource.labels.autoscaler_name=AUTOSCALER_NAME"
```

**Solutions:**
- Verify health checks are passing
- Check autoscaling policy configuration
- Review custom metrics (if used)

#### 3. Network Connectivity Issues

**Symptoms:** Agents cannot reach external services or APIs
```bash
# Test network connectivity from instance
gcloud compute ssh INSTANCE_NAME --zone=ZONE --command="curl -I https://api.github.com"

# Check firewall rules
gcloud compute firewall-rules list --filter="targetTags:agent-vm"
```

**Solutions:**
- Review firewall rules for egress traffic
- Check VPC routing configuration
- Verify service account has necessary API permissions

### Performance Optimization

#### 1. Right-sizing VM Instances

Monitor resource utilization and adjust machine types:

```bash
# Check CPU utilization metrics
gcloud monitoring metrics list --filter="metric.type:compute.googleapis.com/instance/cpu/utilization"

# Analyze cost vs performance
g infra cost analyze --module vm-management
```

#### 2. Autoscaling Tuning

Optimize autoscaling parameters based on workload patterns:

```hcl
# Example optimized autoscaling
cpu_target = 0.70          # 70% CPU target
cooldown_period = 300      # 5-minute cooldown
scale_down_max_percent = 25 # Conservative scale-down
```

#### 3. Storage Optimization

Use appropriate disk types for workloads:

```hcl
# High-performance workloads
disk_type = "pd-ssd"

# Cost-optimized workloads
disk_type = "pd-standard"

# Ultra-high performance
disk_type = "pd-extreme"
```

## Security Best Practices

### 1. Network Security

- Use private IP addresses only for production
- Implement restrictive firewall rules
- Enable VPC Flow Logs for monitoring

### 2. Encryption

- Enable disk encryption with customer-managed keys
- Use confidential computing for sensitive workloads
- Implement encryption in transit

### 3. Access Control

- Use workload identity for service account access
- Implement least-privilege IAM roles
- Enable OS Login for SSH access

### 4. Monitoring

- Enable audit logging for all VM operations
- Monitor for security events and anomalies
- Implement automated security scanning

## Migration from Legacy Infrastructure

### Phase 1: Parallel Deployment

1. Deploy VM Management Layer alongside existing infrastructure
2. Create small agent pools for testing
3. Validate functionality without migrating workloads

### Phase 2: Gradual Migration

1. Migrate development environments first
2. Move non-critical workloads to new infrastructure
3. Monitor performance and stability

### Phase 3: Production Migration

1. Migrate production workloads during maintenance windows
2. Update DNS and load balancer configurations
3. Decommission legacy infrastructure

## Cost Optimization

### Development Environment Strategies

- Use preemptible instances (60-80% cost reduction)
- Enable aggressive autoscaling with min replicas = 0
- Use smaller machine types and disk sizes
- Schedule instance shutdown during off-hours

### Production Environment Strategies

- Use committed use discounts for predictable workloads
- Implement custom metrics-based autoscaling
- Right-size instances based on actual usage patterns
- Use regional persistent disks for cost-effective storage

## Support and Maintenance

### Regular Maintenance Tasks

```bash
# Update agent-cage version
g vm update-template ALL --agent-cage-version v1.3.0

# Review and optimize costs
g infra cost analyze --recommendations

# Security scans
g vm security-scan --all-pools

# Health monitoring
g vm health-check --all --export-metrics
```

### Getting Help

1. **Documentation:** Check Genesis platform documentation
2. **Issues:** File issues in the Genesis repository
3. **Monitoring:** Use Cloud Operations for ongoing health monitoring
4. **Community:** Join Genesis platform community discussions

## Advanced Topics

### Custom Agent Types

Create specialized agent configurations for unique workloads:

```hcl
agent_vm_templates = [
  {
    name       = "ml-training"
    agent_type = "data-engineer"
    machine_type = "n1-standard-16"
    accelerator = {
      type  = "nvidia-tesla-t4"
      count = 1
    }
    custom_config = jsonencode({
      tools = ["tensorflow", "pytorch", "jupyter"]
      gpu_support = true
    })
  }
]
```

### Multi-Region Deployment

Deploy agents across multiple regions for global availability:

```hcl
# Primary region deployment
module "vm_management_us" {
  source = "../../modules/vm-management"
  region = "us-central1"
  # ... configuration
}

# Secondary region deployment
module "vm_management_eu" {
  source = "../../modules/vm-management"
  region = "europe-west1"
  # ... configuration
}
```

### Integration with Other Systems

Connect VM Management Layer with existing systems:

```hcl
# Load balancer integration
resource "google_compute_backend_service" "agent_backend" {
  name = "agent-backend-service"

  dynamic "backend" {
    for_each = module.vm_management.instance_group_urls
    content {
      group = backend.value.instance_group_url
    }
  }
}
```

This deployment guide provides comprehensive coverage of the VM Management Layer implementation following the PIPES methodology and supports the agent-cage migration requirements outlined in Issue #30.
