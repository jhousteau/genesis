# Container Orchestration Module - Issue #31

This module implements comprehensive container orchestration capabilities for the Genesis platform,
specifically designed to support both agent-cage and claude-talk migrations. It follows the PIPES
methodology for scalable, secure, and standardized container infrastructure.

## PIPES Methodology Implementation

### **P - Provision Infrastructure**

- **GKE Clusters**: Autopilot and Standard modes with multi-zone deployment
- **Node Pools**: Specialized node pools for different workload types
- **Container Registry**: Artifact Registry repositories with cleanup policies
- **Persistent Storage**: Dynamic provisioning with multiple storage classes

### **I - Integration Systems & Services**

- **Service Mesh**: Optional Istio integration with advanced traffic management
- **Load Balancing**: GCP Load Balancers with health checking
- **Networking**: VPC-native clusters with private cluster options
- **Secret Management**: Integration with Secret Manager and Kubernetes secrets

### **P - Protect & Secure**

- **Workload Identity**: Google Cloud IAM integration for pods
- **Binary Authorization**: Container image attestation and policy enforcement
- **Network Policies**: Microsegmentation and traffic control
- **Pod Security Standards**: Security contexts and admission control

### **E - Evolve & Scale**

- **Horizontal Pod Autoscaling**: CPU, memory, and custom metrics scaling
- **Cluster Autoscaling**: Node auto-provisioning and scaling
- **Vertical Pod Autoscaling**: Right-sizing recommendations and automation
- **Multi-zone Distribution**: High availability and fault tolerance

### **S - Standardize & Automate**

- **Helm Integration**: Standardized application packaging and deployment
- **GitOps Ready**: Configuration management and continuous deployment
- **Monitoring Integration**: Prometheus, Grafana, and Cloud Operations
- **CLI Integration**: Genesis CLI commands for container management

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────┐
│                Container Orchestration                  │
├─────────────────────────────────────────────────────────┤
│  GKE Cluster (Regional/Zonal)                         │
│  ├── Control Plane (Managed)                          │
│  ├── Node Pools                                       │
│  │   ├── Agent Runtime Pool                           │
│  │   ├── MCP Server Pool                             │
│  │   ├── General Purpose Pool                        │
│  │   └── Spot/Preemptible Pool                      │
│  └── Networking (VPC Native)                          │
├─────────────────────────────────────────────────────────┤
│  Workloads                                             │
│  ├── Agent-Cage Deployment                           │
│  │   ├── Pods: agent-cage                           │
│  │   ├── Services: LoadBalancer/ClusterIP           │
│  │   └── HPA: CPU/Memory scaling                    │
│  ├── Claude-Talk Deployment                          │
│  │   ├── Pods: claude-talk-mcp                      │
│  │   ├── Services: External/Internal                │
│  │   └── HPA: Session-based scaling                 │
│  └── Supporting Services                             │
│      ├── Redis (Session storage)                    │
│      ├── PostgreSQL (Metadata)                      │
│      └── Monitoring Stack                           │
├─────────────────────────────────────────────────────────┤
│  Service Mesh (Optional)                               │
│  ├── Istio Control Plane                             │
│  ├── Envoy Sidecars                                  │
│  ├── Traffic Management                              │
│  └── Security Policies                              │
├─────────────────────────────────────────────────────────┤
│  Container Registry                                     │
│  ├── Artifact Registry Repositories                  │
│  ├── Image Scanning                                  │
│  ├── Vulnerability Management                        │
│  └── Cleanup Policies                               │
└─────────────────────────────────────────────────────────┘
```

## Supported Deployment Modes

### GKE Autopilot Mode

- **Fully Managed**: Google manages nodes, networking, and security
- **Pay-per-Pod**: Cost optimization with per-pod pricing
- **Security by Default**: Built-in security best practices
- **Simplified Operations**: Reduced operational overhead

### GKE Standard Mode

- **Node Control**: Full control over node configuration
- **Custom Node Pools**: Specialized configurations for different workloads
- **Advanced Networking**: Custom VPC configurations and policies
- **Flexible Scaling**: Manual and automated scaling options

## Container Services

### Agent-Cage Runtime

- **Multi-Agent Support**: All 12 Genesis agent types
- **Container Isolation**: Secure agent execution environments
- **Resource Management**: CPU, memory, and storage allocation
- **Health Monitoring**: Comprehensive health checks and metrics

### Claude-Talk MCP Server

- **Session Management**: Persistent and ephemeral sessions
- **Container Scaling**: Session-based horizontal scaling
- **API Gateway**: External access with rate limiting
- **Integration**: Seamless agent-cage communication

### Supporting Infrastructure

- **Redis Cluster**: Session storage and caching
- **PostgreSQL**: Metadata and configuration storage
- **Monitoring Stack**: Prometheus, Grafana, Alertmanager
- **Log Aggregation**: Centralized logging with Cloud Logging

## Usage Examples

### Basic Autopilot Cluster

```hcl
module "container_orchestration" {
  source = "../../modules/container-orchestration"

  project_id  = "genesis-project-dev"
  region      = "us-central1"
  environment = "dev"

  gke_cluster_config = {
    name = "genesis-autopilot"
    description = "Genesis Autopilot cluster for agent workloads"
  }

  enable_autopilot = true
  regional_cluster = true

  container_repositories = [
    {
      name        = "agent-cage"
      description = "Agent-cage runtime images"
    },
    {
      name        = "claude-talk"
      description = "Claude-talk MCP server images"
    }
  ]

  kubernetes_namespaces = [
    "genesis-agents",
    "claude-talk",
    "monitoring"
  ]
}
```

### Production Standard Cluster with Service Mesh

```hcl
module "container_orchestration_prod" {
  source = "../../modules/container-orchestration"

  project_id  = "genesis-project-prod"
  region      = "us-central1"
  environment = "prod"

  gke_cluster_config = {
    name        = "genesis-prod"
    description = "Production Genesis cluster"
  }

  # Standard mode with custom node pools
  enable_autopilot = false
  regional_cluster = true

  node_pools = [
    {
      name               = "agent-runtime"
      machine_type       = "e2-standard-4"
      initial_node_count = 2
      min_nodes         = 2
      max_nodes         = 20
      enable_autoscaling = true

      node_pool_type = "agent-runtime"
      workload_type  = "compute-intensive"

      taints = [
        {
          key    = "agent-runtime"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      ]
    },
    {
      name               = "mcp-server"
      machine_type       = "e2-standard-2"
      initial_node_count = 1
      min_nodes         = 1
      max_nodes         = 10
      enable_autoscaling = true

      node_pool_type = "mcp-server"
      workload_type  = "io-intensive"
    },
    {
      name               = "general-purpose"
      machine_type       = "e2-medium"
      initial_node_count = 1
      min_nodes         = 0
      max_nodes         = 5
      enable_autoscaling = true
      preemptible       = true
    }
  ]

  # Private cluster configuration
  enable_private_cluster = true
  enable_private_endpoint = false
  master_ipv4_cidr_block = "172.16.0.0/28"

  # Service mesh
  enable_service_mesh = true
  enable_istio_ingress = true

  # Security features
  enable_workload_identity = true
  enable_binary_authorization = true
  enable_network_policy = true
  enable_shielded_nodes = true

  # Monitoring
  enable_managed_prometheus = true
  monitoring_components = [
    "SYSTEM_COMPONENTS",
    "WORKLOADS",
    "APISERVER"
  ]
}
```

### Development Cluster with Cost Optimization

```hcl
module "container_orchestration_dev" {
  source = "../../modules/container-orchestration"

  project_id  = "genesis-project-dev"
  region      = "us-central1"
  zone        = "us-central1-a"  # Zonal cluster for cost savings
  environment = "dev"

  gke_cluster_config = {
    name = "genesis-dev"
  }

  regional_cluster = false  # Zonal cluster
  enable_autopilot = false

  node_pools = [
    {
      name               = "dev-pool"
      machine_type       = "e2-micro"
      initial_node_count = 1
      min_nodes         = 0
      max_nodes         = 3
      enable_autoscaling = true
      preemptible       = true  # Cost optimization

      # Development-friendly settings
      auto_repair  = true
      auto_upgrade = false  # Manual upgrades in dev
    }
  ]

  # Minimal security for development
  enable_private_cluster = false
  enable_workload_identity = false
  enable_network_policy = false
}
```

## Container Deployment Examples

### Deploy Agent-Cage with CLI

```bash
# Deploy agent-cage to development
g container deploy --service agent-cage --environment dev --replicas 2

# Deploy with specific version
g container deploy --service agent-cage --version v1.2.3 --replicas 3 --namespace genesis-agents

# Scale existing deployment
g container scale --deployment agent-cage --replicas 5 --namespace genesis-agents
```

### Deploy Claude-Talk with Custom Configuration

```bash
# Deploy claude-talk with load balancer
g container deploy --service claude-talk --environment prod --replicas 3

# Check deployment status
g container list-deployments --namespace claude-talk

# View logs
g container logs --service claude-talk --follow --lines 100
```

### Docker Compose for Local Development

```bash
# Start local development environment
cd modules/container-orchestration/templates
export ENVIRONMENT=dev
export PROJECT_ID=genesis-local
docker-compose up -d

# Scale services
docker-compose up -d --scale backend-developer-agent=2

# View logs
docker-compose logs -f agent-cage
```

## Service Mesh Integration

### Istio Configuration

When service mesh is enabled, the module automatically configures:

- **Traffic Management**: Intelligent routing and load balancing
- **Security**: mTLS between services
- **Observability**: Distributed tracing and metrics
- **Policy Enforcement**: Rate limiting and access control

### Traffic Routing Example

```yaml
# Canary deployment with Istio
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: agent-cage-canary
spec:
  hosts:
  - agent-cage
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: agent-cage
        subset: v2
  - route:
    - destination:
        host: agent-cage
        subset: v1
      weight: 90
    - destination:
        host: agent-cage
        subset: v2
      weight: 10
```

## Security Features

### Workload Identity

- **GCP IAM Integration**: Kubernetes service accounts mapped to GCP service accounts
- **No Service Account Keys**: Eliminates the need for static credentials
- **Fine-grained Permissions**: Least privilege access for each workload

### Network Security

- **Private Clusters**: Nodes without external IP addresses
- **Authorized Networks**: Restricted API server access
- **Network Policies**: Microsegmentation between pods
- **VPC-native Networking**: Direct integration with GCP networking

### Pod Security

- **Security Contexts**: Non-root containers with read-only filesystems
- **Pod Security Standards**: Enforced security profiles
- **Resource Limits**: CPU and memory constraints
- **Image Security**: Binary Authorization and vulnerability scanning

## Monitoring and Observability

### Built-in Monitoring

- **Cloud Operations**: Native GCP monitoring integration
- **Prometheus**: Custom metrics collection and alerting
- **Grafana**: Visualization dashboards
- **Distributed Tracing**: Request flow tracking

### Key Metrics

- **Cluster Health**: Node status, resource utilization
- **Pod Metrics**: CPU, memory, network, storage usage
- **Application Metrics**: Custom business metrics
- **SLI/SLO Tracking**: Service level objective monitoring

### Alerting

- **Infrastructure Alerts**: Node failures, resource exhaustion
- **Application Alerts**: Service unavailability, high error rates
- **Security Alerts**: Policy violations, unauthorized access
- **Cost Alerts**: Budget thresholds and unexpected spend

## Cost Optimization

### Cluster Cost Optimization

- **Autopilot Mode**: Pay-per-pod pricing model
- **Spot Instances**: Up to 80% cost savings for fault-tolerant workloads
- **Cluster Autoscaling**: Automatic node provisioning and de-provisioning
- **Right-sizing**: VPA recommendations for optimal resource allocation

### Storage Cost Optimization

- **Storage Classes**: Standard, SSD, and regional persistent disks
- **Ephemeral Storage**: EmptyDir volumes for temporary data
- **Container Image Optimization**: Multi-stage builds and layer caching

### Network Cost Optimization

- **Regional Clusters**: Reduced cross-zone traffic costs
- **Private Clusters**: Eliminated internet egress costs
- **Load Balancer Optimization**: Efficient traffic distribution

## Troubleshooting Guide

### Common Issues

#### Pods Stuck in Pending State

```bash
# Check node resources
kubectl describe nodes

# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Check resource quotas
kubectl describe quota -n <namespace>
```

#### Network Connectivity Issues

```bash
# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup kubernetes.default

# Check network policies
kubectl get networkpolicies -A

# Test service connectivity
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- bash
```

#### Image Pull Issues

```bash
# Check service account permissions
kubectl get serviceaccount <sa-name> -o yaml

# Verify Workload Identity configuration
kubectl annotate serviceaccount <sa-name> iam.gke.io/gcp-service-account=<gsa-email>

# Test image access
docker pull <image-url>
```

### Performance Optimization

#### Resource Optimization

```bash
# Check resource utilization
kubectl top nodes
kubectl top pods -A

# VPA recommendations
kubectl get vpa -A

# HPA status
kubectl get hpa -A
```

#### Storage Performance

```bash
# Check PVC status
kubectl get pvc -A

# Storage class performance
kubectl describe storageclass

# Volume metrics
kubectl get volumeattachment
```

## Migration Strategies

### From VM-based to Container-based

1. **Parallel Deployment**: Run containers alongside existing VMs
2. **Gradual Migration**: Move agents one type at a time
3. **Traffic Shifting**: Use load balancers to shift traffic gradually
4. **Rollback Plan**: Maintain ability to revert to VMs

### From Legacy Container Systems

1. **Configuration Migration**: Convert existing configurations
2. **Data Migration**: Move persistent data to new storage
3. **Secret Migration**: Transfer credentials to Secret Manager
4. **DNS Updates**: Update service discovery configurations

## CLI Commands Reference

### Cluster Management

```bash
# Create cluster
g container create-cluster genesis-prod --autopilot --region us-central1

# List clusters
g container list-clusters

# Delete cluster (careful!)
g container delete-cluster genesis-dev --environment dev
```

### Deployment Management

```bash
# Deploy service
g container deploy --service agent-cage --version latest --replicas 3

# Scale deployment
g container scale --deployment claude-talk --replicas 5

# View deployment status
g container list-deployments
```

### Service Management

```bash
# List services
g container list-services

# View service details
g container describe service agent-cage-service
```

### Registry Management

```bash
# List repositories
g container registry list-repositories

# Push image
g container registry push agent-cage:latest --repository us-central1-docker.pkg.dev/project/repo

# Pull image
g container registry pull claude-talk:v1.2.3
```

### Monitoring and Debugging

```bash
# View logs
g container logs --service agent-cage --follow

# Get pod status
g container list-pods --namespace genesis-agents

# Execute into pod
g container exec --pod agent-cage-abc123 --command "/bin/bash"
```

## Contributing and Extending

### Adding New Services

1. Create Kubernetes manifests in `manifests/`
2. Add Docker configurations in `templates/`
3. Update CLI commands for service management
4. Add monitoring and alerting configurations
5. Update documentation and examples

### Custom Node Pools

1. Define node pool configuration in variables
2. Add specialized taints and tolerations
3. Configure appropriate resource limits
4. Add monitoring for new node pools

### Security Enhancements

1. Implement additional network policies
2. Add custom admission controllers
3. Integrate with external security scanners
4. Enhance secret management practices

## Best Practices

### Deployment Best Practices

- Use resource requests and limits
- Implement health checks for all containers
- Use multi-stage Docker builds for smaller images
- Tag images with specific versions, not `latest`

### Security Best Practices

- Enable Workload Identity
- Use private clusters in production
- Implement network policies
- Regularly scan container images

### Operational Best Practices

- Monitor resource utilization continuously
- Set up comprehensive alerting
- Implement automated backup strategies
- Document incident response procedures

### Cost Management Best Practices

- Use preemptible nodes for development
- Implement cluster autoscaling
- Monitor costs regularly with budgets and alerts
- Right-size resources based on actual usage

This container orchestration module provides a complete foundation for running Genesis agents and
supporting services in a scalable, secure, and cost-effective manner while supporting both
agent-cage and claude-talk migration requirements.
