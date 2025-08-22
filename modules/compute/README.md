# Compute Module

This module provides comprehensive compute infrastructure for Google Cloud Platform, including virtual machines, managed instance groups, GKE clusters, Cloud Run services, and Cloud Functions.

## Features

- **Virtual Machines**: Instance templates with auto-scaling and health checks
- **Managed Instance Groups**: Regional instance groups with auto-scaling and rolling updates
- **Google Kubernetes Engine (GKE)**: Fully managed Kubernetes clusters with node pools
- **Cloud Run**: Serverless container platform with automatic scaling
- **Cloud Functions**: Event-driven serverless functions
- **Health Checks**: Comprehensive health monitoring for all compute resources
- **Auto-scaling**: Intelligent scaling based on CPU, load, and custom metrics
- **Security**: Shielded VMs, Confidential Computing, and Binary Authorization
- **Multi-region Support**: Deploy across multiple regions for high availability
- **Cost Optimization**: Preemptible and spot instances for cost savings

## Usage

### Basic VM Instance

```hcl
module "compute" {
  source = "./modules/compute"
  
  project_id   = "my-project-id"
  name_prefix  = "app"
  environment  = "production"
  
  network_id = module.networking.network_id
  subnet_id  = module.networking.subnet_ids["app-subnet"]
  
  vm_instances = [
    {
      name         = "web-server"
      machine_type = "e2-standard-2"
      source_image = "debian-cloud/debian-12"
      disk_size_gb = 50
      network_tags = ["web-server"]
      
      service_account = {
        email  = module.service_accounts.service_accounts["web"].email
        scopes = ["cloud-platform"]
      }
    }
  ]
}
```

### Managed Instance Group with Auto-scaling

```hcl
module "compute" {
  source = "./modules/compute"
  
  project_id   = "my-project-id"
  name_prefix  = "app"
  environment  = "production"
  
  # VM template
  vm_instances = [
    {
      name         = "web-template"
      machine_type = "e2-standard-2"
      source_image = "debian-cloud/debian-12"
      network_tags = ["web-server", "load-balanced"]
      
      startup_script = file("${path.module}/startup-script.sh")
      
      metadata = {
        "startup-script-url" = "gs://my-bucket/startup-script.sh"
      }
    }
  ]
  
  # Instance group
  instance_groups = [
    {
      name              = "web-group"
      instance_template = "web-template"
      target_size       = 3
      
      # Auto-scaling
      enable_autoscaling = true
      min_replicas      = 2
      max_replicas      = 10
      cpu_target        = 0.6
      
      # Health check
      health_check = "web-health-check"
      
      # Update policy
      update_policy = {
        type                = "PROACTIVE"
        minimal_action     = "REPLACE"
        max_surge_percent  = 20
        max_unavailable_percent = 10
      }
    }
  ]
  
  # Health checks
  health_checks = [
    {
      name = "web-health-check"
      http = {
        port         = 80
        request_path = "/health"
      }
    }
  ]
}
```

### GKE Cluster

```hcl
module "compute" {
  source = "./modules/compute"
  
  project_id   = "my-project-id"
  name_prefix  = "k8s"
  environment  = "production"
  
  network_id = module.networking.network_id
  subnet_id  = module.networking.subnet_ids["gke-subnet"]
  
  gke_clusters = [
    {
      name               = "primary"
      location          = "us-central1"
      kubernetes_version = "1.28"
      
      # Private cluster
      private_cluster         = true
      enable_private_endpoint = false
      master_ipv4_cidr_block = "172.16.0.0/28"
      
      # IP allocation
      enable_ip_alias     = true
      pods_range_name     = "pods"
      services_range_name = "services"
      
      # Network policy
      enable_network_policy = true
      
      # Addons
      enable_http_load_balancing = true
      enable_hpa                = true
      enable_backup_agent       = true
      
      # Workload Identity
      enable_workload_identity = true
      
      # Monitoring
      enable_monitoring     = true
      enable_logging       = true
      
      # Node pools
      node_pools = [
        {
          name         = "default-pool"
          machine_type = "e2-standard-4"
          disk_size_gb = 100
          disk_type    = "pd-ssd"
          
          enable_autoscaling = true
          min_node_count    = 1
          max_node_count    = 5
          
          labels = {
            pool = "default"
          }
          
          taints = []
        },
        {
          name         = "compute-pool"
          machine_type = "c2-standard-8"
          disk_size_gb = 200
          
          enable_autoscaling = true
          min_node_count    = 0
          max_node_count    = 10
          
          labels = {
            pool        = "compute"
            workload    = "cpu-intensive"
          }
          
          taints = [
            {
              key    = "compute"
              value  = "true"
              effect = "NO_SCHEDULE"
            }
          ]
        }
      ]
    }
  ]
}
```

### Cloud Run Services

```hcl
module "compute" {
  source = "./modules/compute"
  
  project_id   = "my-project-id"
  name_prefix  = "api"
  environment  = "production"
  
  cloud_run_services = [
    {
      name  = "api-service"
      image = "gcr.io/my-project/api:latest"
      
      # Scaling
      min_scale = 1
      max_scale = 100
      
      # Resources
      containers = [
        {
          cpu    = "1000m"
          memory = "1Gi"
          
          env = {
            "DATABASE_URL" = "postgresql://..."
            "REDIS_URL"    = "redis://..."
          }
          
          env_from_secret = {
            "API_KEY" = {
              secret  = "api-secrets"
              version = "latest"
            }
          }
          
          ports = [
            {
              container_port = 8080
            }
          ]
        }
      ]
      
      # VPC Access
      vpc_access = {
        connector = "vpc-connector"
        egress   = "PRIVATE_RANGES_ONLY"
      }
      
      # Traffic
      traffic = [
        {
          type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
          percent = 100
        }
      ]
      
      allow_unauthenticated = true
    }
  ]
}
```

### Cloud Functions

```hcl
module "compute" {
  source = "./modules/compute"
  
  project_id   = "my-project-id"
  name_prefix  = "fn"
  environment  = "production"
  
  cloud_functions = [
    {
      name        = "process-data"
      runtime     = "python311"
      entry_point = "main"
      
      source_bucket = "my-functions-bucket"
      source_object = "process-data.zip"
      
      # Configuration
      available_memory    = "512M"
      timeout_seconds    = 300
      max_instances      = 10
      
      environment_variables = {
        "ENVIRONMENT" = "production"
      }
      
      secret_environment_variables = {
        "DATABASE_PASSWORD" = {
          secret  = "db-credentials"
          version = "latest"
        }
      }
      
      # Event trigger
      event_trigger = {
        event_type   = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic = "projects/my-project/topics/data-processing"
        retry_policy = "RETRY_POLICY_RETRY"
      }
    }
  ]
}
```

## Module Structure

```
modules/compute/
├── main.tf           # VM instances, instance groups, health checks
├── gke.tf           # GKE clusters and node pools
├── serverless.tf    # Cloud Run and Cloud Functions
├── variables.tf     # Input variables
├── outputs.tf       # Output values
├── versions.tf      # Provider version constraints
└── README.md        # This file
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_id | The GCP project ID | `string` | n/a | yes |
| name_prefix | Prefix for resource names | `string` | `"compute"` | no |
| environment | Environment name | `string` | `"dev"` | no |
| network_id | The ID of the VPC network | `string` | `"default"` | no |
| subnet_id | The ID of the subnet | `string` | `null` | no |
| vm_instances | VM instance configurations | `list(object)` | `[]` | no |
| instance_groups | Instance group configurations | `list(object)` | `[]` | no |
| gke_clusters | GKE cluster configurations | `list(object)` | `[]` | no |
| cloud_run_services | Cloud Run service configurations | `list(object)` | `[]` | no |
| cloud_functions | Cloud Functions configurations | `list(object)` | `[]` | no |

## Outputs

| Name | Description |
|------|-------------|
| vm_instance_templates | VM instance template self-links |
| instance_groups | Managed instance group information |
| gke_clusters | GKE cluster information |
| gke_cluster_endpoints | GKE cluster endpoints |
| cloud_run_services | Cloud Run service information |
| cloud_run_urls | Cloud Run service URLs |
| cloud_functions | Cloud Functions information |
| service_urls | Public URLs for all services |

## Advanced Features

### Spot and Preemptible Instances

Reduce costs with spot and preemptible instances:

```hcl
vm_instances = [
  {
    name         = "batch-worker"
    machine_type = "n1-standard-4"
    
    scheduling = {
      preemptible = true
    }
  }
]

# GKE spot nodes
gke_clusters = [
  {
    name = "batch-cluster"
    node_pools = [
      {
        name = "spot-pool"
        spot = true
        machine_type = "n1-standard-4"
      }
    ]
  }
]
```

### GPU Support

Configure GPU accelerators:

```hcl
vm_instances = [
  {
    name         = "ml-training"
    machine_type = "n1-standard-4"
    zone        = "us-central1-a"
    
    guest_accelerators = [
      {
        type  = "nvidia-tesla-t4"
        count = 1
      }
    ]
  }
]
```

### Multi-Region Deployment

Deploy across multiple regions:

```hcl
# Primary region
instance_groups = [
  {
    name   = "web-primary"
    region = "us-central1"
    # ... configuration
  }
]

# Secondary region
instance_groups = [
  {
    name   = "web-secondary" 
    region = "us-east1"
    # ... configuration
  }
]
```

### Security Features

Enable advanced security features:

```hcl
vm_instances = [
  {
    name = "secure-vm"
    
    # Shielded VM
    enable_shielded_vm           = true
    enable_secure_boot          = true
    enable_integrity_monitoring = true
    
    # Confidential Computing
    enable_confidential_vm = true
  }
]

# GKE with Binary Authorization
gke_clusters = [
  {
    name = "secure-cluster"
    enable_binary_authorization = true
    enable_network_policy      = true
    enable_shielded_nodes      = true
  }
]
```

## Integration with Other Modules

### With Networking Module

```hcl
module "networking" {
  source = "./modules/networking"
  # networking configuration
}

module "compute" {
  source = "./modules/compute"
  
  network_id = module.networking.network_id
  subnet_id  = module.networking.subnet_ids["compute-subnet"]
  # compute configuration
}
```

### With Security Module

```hcl
module "security" {
  source = "./modules/security"
  # security configuration
}

module "compute" {
  source = "./modules/compute"
  
  vm_instances = [
    {
      name = "web-server"
      service_account = {
        email = module.security.service_accounts["web"].email
      }
      disk_encryption_key = module.security.kms_keys["vm-encryption"].id
    }
  ]
}
```

## Best Practices

1. **Right-sizing**: Choose appropriate machine types for workloads
2. **Auto-scaling**: Configure proper scaling policies
3. **Health Checks**: Implement comprehensive health monitoring
4. **Security**: Use Shielded VMs and proper IAM
5. **Cost Optimization**: Use preemptible/spot instances for non-critical workloads
6. **High Availability**: Deploy across multiple zones/regions
7. **Monitoring**: Enable comprehensive logging and monitoring
8. **Updates**: Use rolling updates for zero-downtime deployments

## Version Compatibility

- Terraform >= 1.3
- Google Provider >= 5.0
- Google Beta Provider >= 5.0

## Contributing

When contributing to this module:

1. Test across different machine types and regions
2. Validate security configurations
3. Update examples for new features
4. Ensure backward compatibility
5. Follow GCP best practices