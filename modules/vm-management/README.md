# VM Management Layer - Issue #30

This module implements comprehensive VM management capabilities for the Genesis platform, specifically designed to support the agent-cage migration. It follows the PIPES methodology for scalable, secure, and standardized VM infrastructure.

## PIPES Methodology Implementation

### **P - Provision Infrastructure**
- **Agent VM Templates**: Configurable instance templates for different agent types
- **Managed Instance Groups**: Automated scaling and lifecycle management
- **Resource Allocation**: Optimized machine types and disk configurations
- **Multi-zone Distribution**: High availability across GCP zones

### **I - Integration Systems & Services**
- **Genesis Framework**: Deep integration with existing Genesis patterns
- **Network Integration**: VPC and subnet connectivity with firewall rules
- **Service Account Integration**: Workload identity and IAM permissions
- **Health Check Integration**: Automated health monitoring and healing

### **P - Protect & Secure**
- **Shielded VMs**: Secure boot, vTPM, and integrity monitoring
- **Disk Encryption**: KMS-based encryption for all persistent disks
- **Network Security**: Firewall rules and network tag-based access control
- **Confidential Computing**: Optional confidential VM support for sensitive workloads

### **E - Evolve & Scale**
- **Autoscaling**: CPU and custom metric-based scaling policies
- **Predictive Scaling**: Optional predictive autoscaling for proactive capacity management
- **Rolling Updates**: Zero-downtime instance template updates
- **Cost Optimization**: Preemptible instances and intelligent resource sizing

### **S - Standardize & Automate**
- **Agent Types**: Standardized configurations for all 12 Genesis agent types
- **Startup Scripts**: Automated agent environment setup and configuration
- **Health Monitoring**: Standardized health check endpoints and monitoring
- **CLI Integration**: Commands for VM lifecycle management

## Supported Agent Types

The module supports all Genesis agent types with optimized configurations:

### Executive Level Agents
- **project-manager**: Resource coordination and planning workloads
- **architect**: System design and architectural analysis
- **tech-lead**: Code review and quality assessment

### Implementation Level Agents
- **platform-engineer**: Infrastructure and Terraform operations
- **backend-developer**: API development and server-side processing
- **frontend-developer**: UI/UX development and client-side operations
- **data-engineer**: Data processing and analytics pipelines
- **integration-agent**: Service integration and API orchestration

### Quality & Operations Level Agents
- **qa-automation**: Testing and quality assurance automation
- **sre-agent**: Site reliability and incident response
- **security-agent**: Security scanning and compliance validation
- **devops-agent**: Deployment and CI/CD operations

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                 VM Management Layer                     │
├─────────────────────────────────────────────────────────┤
│  Agent VM Templates                                     │
│  ├── Backend Developer VMs                             │
│  ├── Frontend Developer VMs                            │
│  ├── Platform Engineer VMs                             │
│  ├── Security Agent VMs                                │
│  └── ... (all 12 agent types)                         │
├─────────────────────────────────────────────────────────┤
│  Agent Pools (Managed Instance Groups)                 │
│  ├── Auto-scaling policies                             │
│  ├── Health checks                                     │
│  ├── Rolling updates                                   │
│  └── Load balancer integration                         │
├─────────────────────────────────────────────────────────┤
│  Security & Compliance                                  │
│  ├── Shielded VMs                                      │
│  ├── Disk encryption (KMS)                            │
│  ├── Firewall rules                                   │
│  └── Network isolation                                │
├─────────────────────────────────────────────────────────┤
│  Monitoring & Operations                                │
│  ├── Cloud Operations integration                      │
│  ├── Custom metrics                                    │
│  ├── Health endpoints                                  │
│  └── Logging aggregation                              │
└─────────────────────────────────────────────────────────┘
```

## Usage Examples

### Basic Agent Pool Deployment

```hcl
module "vm_management" {
  source = "../../modules/vm-management"

  project_id  = "genesis-project-dev"
  region      = "us-central1"
  zones       = ["us-central1-a", "us-central1-b", "us-central1-c"]
  environment = "dev"

  network_id = module.networking.vpc_id
  subnet_id  = module.networking.subnet_id

  agent_vm_templates = [
    {
      name       = "backend-dev"
      agent_type = "backend-developer"
      machine_type = "e2-standard-2"
    },
    {
      name       = "platform-eng"
      agent_type = "platform-engineer"
      machine_type = "e2-standard-4"
    }
  ]

  agent_pools = [
    {
      name          = "backend-pool"
      agent_type    = "backend-developer"
      template_name = "backend-dev"
      target_size   = 2
      enable_autoscaling = true
      min_replicas  = 1
      max_replicas  = 5
    }
  ]
}
```

### Production Deployment with Security Features

```hcl
module "vm_management_prod" {
  source = "../../modules/vm-management"

  project_id  = "genesis-project-prod"
  region      = "us-central1"
  environment = "prod"

  # Security configuration
  enable_disk_encryption = true
  disk_encryption_key   = "projects/genesis-project-prod/locations/us-central1/keyRings/genesis/cryptoKeys/vm-encryption"

  enable_secure_boot            = true
  enable_vtpm                  = true
  enable_integrity_monitoring  = true

  # High availability configuration
  agent_pools = [
    {
      name          = "prod-backend-pool"
      agent_type    = "backend-developer"
      template_name = "backend-prod"
      enable_autoscaling = true
      min_replicas  = 3
      max_replicas  = 20
      cpu_target    = 0.70
    }
  ]

  # Custom firewall rules
  firewall_rules = {
    "allow-prod-backend" = {
      description   = "Allow production backend access"
      direction     = "INGRESS"
      source_ranges = ["10.0.0.0/16"]
      target_tags   = ["agent-backend-developer"]
      allow = [{
        protocol = "tcp"
        ports    = ["8080", "9090"]
      }]
    }
  }
}
```

## Agent-Specific Configurations

### Backend Developer Agents
- **Tools**: Python, Node.js, Go development environments
- **Resources**: 2-4 vCPUs, 8-16 GB RAM
- **Storage**: 50 GB workspace disk for code repositories
- **Networking**: Internal access with optional external IP

### Platform Engineer Agents
- **Tools**: Terraform, Kubernetes, Helm, cloud SDKs
- **Resources**: 4-8 vCPUs, 16-32 GB RAM
- **Storage**: 100 GB workspace disk for infrastructure code
- **Networking**: Full cloud API access and external connectivity

### Security Agents
- **Tools**: Security scanners, compliance tools, monitoring
- **Resources**: 2-4 vCPUs, 8-16 GB RAM
- **Storage**: 50 GB for scan results and reports
- **Networking**: Restricted access with security-specific firewall rules

## Monitoring and Health Checks

### Built-in Health Endpoints
- **`/health`**: Basic health status and metadata
- **`/metrics`**: Prometheus-compatible metrics
- **`/status`**: Detailed agent runtime status

### Cloud Operations Integration
- **Logging**: Structured logs to Cloud Logging
- **Metrics**: Custom metrics to Cloud Monitoring
- **Alerting**: Automated alerts for health failures
- **Tracing**: Request tracing for troubleshooting

## Cost Optimization Features

### Preemptible Instances
- **Development**: Default preemptible for cost savings
- **Production**: Optional preemptible for non-critical workloads
- **Automatic Restart**: Handles preemption gracefully

### Autoscaling Policies
- **CPU-based**: Scale based on CPU utilization
- **Custom Metrics**: Scale based on agent-specific metrics
- **Schedule-based**: Predictive scaling for known patterns
- **Cost Controls**: Maximum instance limits and budget alerts

## Security Features

### Encryption at Rest
- **Boot Disks**: KMS encryption for all boot volumes
- **Workspace Disks**: Separate encryption for persistent workspaces
- **Key Management**: Integration with Cloud KMS

### Network Security
- **Firewall Rules**: Agent-type specific access controls
- **Network Tags**: Granular network policy enforcement
- **Private IPs**: Internal-only communication when possible

### Compliance
- **Shielded VMs**: Hardware-level security features
- **OS Login**: Google-managed SSH access
- **Audit Logging**: All VM operations logged for compliance

## CLI Integration

### VM Management Commands
```bash
# Create agent pool
g vm create-pool --type backend-developer --size 3

# Scale agent pool
g vm scale-pool backend-pool --min 2 --max 10

# Update agent pool
g vm update-pool backend-pool --template new-template

# Monitor agent health
g vm health-check --pool backend-pool

# Agent runtime management
g vm agent-start --instance agent-backend-001
g vm agent-stop --instance agent-backend-001
g vm agent-restart --instance agent-backend-001
```

## Variables Reference

### Core Configuration
- **`project_id`**: GCP project ID for resources
- **`region`**: Primary region for VM deployment
- **`zones`**: List of zones for distribution
- **`environment`**: Environment name (dev/staging/prod)

### Agent Templates
- **`agent_vm_templates`**: List of agent VM template configurations
- **`agent_pools`**: List of managed instance group configurations
- **`default_agent_machine_type`**: Default machine type for agents

### Security Settings
- **`enable_disk_encryption`**: Enable KMS disk encryption
- **`enable_secure_boot`**: Enable Shielded VM secure boot
- **`enable_vtpm`**: Enable virtual Trusted Platform Module
- **`firewall_rules`**: Custom firewall rule definitions

### Scaling Configuration
- **`default_enable_autoscaling`**: Enable autoscaling by default
- **`default_min_replicas`**: Minimum instances per pool
- **`default_max_replicas`**: Maximum instances per pool
- **`default_cpu_target`**: Target CPU utilization for scaling

## Outputs Reference

### Resource Information
- **`agent_vm_templates`**: VM template details and metadata
- **`agent_pools`**: Managed instance group information
- **`autoscalers`**: Autoscaling configuration and status
- **`health_checks`**: Health check endpoint details

### Integration Points
- **`instance_group_urls`**: URLs for load balancer backends
- **`network_tags`**: Network tags for firewall rules
- **`service_accounts`**: Service account configurations

### Monitoring Data
- **`vm_management_summary`**: Complete deployment summary
- **`cost_optimization`**: Cost settings and estimates
- **`agent_configuration`**: Agent runtime configuration

## Prerequisites

1. **GCP Project**: Configured with Compute Engine API enabled
2. **VPC Network**: Existing VPC with appropriate subnets
3. **Service Accounts**: IAM service accounts for agent workloads
4. **KMS Keys**: Encryption keys for disk encryption (if enabled)
5. **Agent-Cage**: Agent runtime binary and configuration

## Migration Path from Legacy Infrastructure

### Phase 1: Parallel Deployment
1. Deploy VM management module alongside existing infrastructure
2. Create agent pools with minimal instances
3. Validate health checks and monitoring

### Phase 2: Agent Migration
1. Configure agent-cage runtime on new VMs
2. Test agent functionality and performance
3. Gradually migrate agents from legacy to new infrastructure

### Phase 3: Legacy Decommission
1. Scale down legacy infrastructure
2. Update DNS and load balancer configurations
3. Remove deprecated resources and configurations

## Troubleshooting

### Common Issues

#### Health Check Failures
```bash
# Check health endpoint manually
curl http://VM_INTERNAL_IP:8080/health

# Review health check logs
gcloud logging read "resource.type=gce_instance AND jsonPayload.agent_type=backend-developer"
```

#### Autoscaling Not Working
```bash
# Check autoscaler status
gcloud compute region-autoscalers describe AUTOSCALER_NAME --region=REGION

# Review metrics
gcloud monitoring metrics list --filter="metric.type:compute.googleapis.com"
```

#### Agent Startup Issues
```bash
# Check startup script logs
gcloud compute instances get-serial-port-output INSTANCE_NAME --zone=ZONE

# SSH to instance and check services
gcloud compute ssh INSTANCE_NAME --zone=ZONE
sudo journalctl -u agent-runtime -f
```

### Support and Maintenance

This module is part of the Genesis platform infrastructure. For support:

1. **Documentation**: Check Genesis platform documentation
2. **Issues**: File issues in the Genesis repository
3. **Monitoring**: Use Cloud Operations for ongoing health monitoring
4. **Updates**: Follow Genesis platform release cycles for updates

## Contributing

When contributing to this module:

1. **Follow PIPES**: Ensure all changes follow the PIPES methodology
2. **Test Thoroughly**: Test with multiple agent types and configurations
3. **Update Documentation**: Keep README and inline comments current
4. **Security Review**: Ensure security features are maintained
5. **Cost Impact**: Consider cost implications of changes
