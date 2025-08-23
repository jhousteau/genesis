# Genesis VM Management Layer Example - Development Environment
# This example demonstrates how to deploy the VM Management Layer with
# agent-cage support for the development environment.

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "genesis-terraform-state-dev"
    prefix = "examples/vm-management"
  }
}

# Local values for environment configuration
locals {
  # Project configuration
  project_id = "genesis-platform-dev"
  region     = "us-central1"
  zones      = ["us-central1-a", "us-central1-b", "us-central1-c"]

  # Environment settings
  environment = "dev"

  # Common labels for all resources
  common_labels = {
    project     = "genesis"
    environment = "dev"
    managed_by  = "terraform"
    component   = "vm-management"
    cost_center = "development"
  }
}

# Data sources for existing infrastructure
data "google_compute_network" "genesis_vpc" {
  name    = "genesis-vpc-dev"
  project = local.project_id
}

data "google_compute_subnetwork" "genesis_subnet" {
  name    = "genesis-subnet-dev"
  region  = local.region
  project = local.project_id
}

data "google_service_account" "agent_sa" {
  account_id = "genesis-agent-dev"
  project    = local.project_id
}

# KMS key for disk encryption (security requirement)
resource "google_kms_key_ring" "vm_encryption" {
  name     = "genesis-vm-encryption-dev"
  location = local.region
  project  = local.project_id
}

resource "google_kms_crypto_key" "vm_disk_key" {
  name     = "vm-disk-encryption"
  key_ring = google_kms_key_ring.vm_encryption.id
  purpose  = "ENCRYPT_DECRYPT"

  lifecycle {
    prevent_destroy = true
  }
}

# VM Management Layer Deployment
module "vm_management" {
  source = "../../modules/vm-management"

  # Core configuration
  project_id  = local.project_id
  region      = local.region
  zones       = local.zones
  environment = local.environment
  labels      = local.common_labels

  # Network configuration
  network_id = data.google_compute_network.genesis_vpc.id
  subnet_id  = data.google_compute_subnetwork.genesis_subnet.id

  # Security configuration for development
  enable_disk_encryption      = true
  disk_encryption_key         = google_kms_crypto_key.vm_disk_key.id
  enable_secure_boot          = true
  enable_vtpm                 = true
  enable_integrity_monitoring = true

  # Agent service account
  default_agent_service_account = data.google_service_account.agent_sa.email

  # Development-optimized agent templates
  agent_vm_templates = [
    # Backend Developer Agents
    {
      name               = "backend-dev"
      agent_type         = "backend-developer"
      machine_type       = "e2-standard-2"
      disk_size_gb       = 30
      workspace_size_gb  = 100
      preemptible        = true # Cost optimization for dev
      enable_external_ip = true
      custom_config = jsonencode({
        tools = ["python", "node", "go", "docker"]
        ide   = "vscode-server"
      })
      additional_tags = ["backend-dev", "development"]
    },

    # Frontend Developer Agents
    {
      name               = "frontend-dev"
      agent_type         = "frontend-developer"
      machine_type       = "e2-standard-2"
      disk_size_gb       = 30
      workspace_size_gb  = 50
      preemptible        = true
      enable_external_ip = true
      custom_config = jsonencode({
        tools      = ["node", "npm", "webpack", "chrome"]
        frameworks = ["react", "vue", "angular"]
      })
      additional_tags = ["frontend-dev", "development"]
    },

    # Platform Engineer Agents
    {
      name               = "platform-dev"
      agent_type         = "platform-engineer"
      machine_type       = "e2-standard-4" # More resources for infra work
      disk_size_gb       = 50
      workspace_size_gb  = 200
      preemptible        = false # Critical for infrastructure management
      enable_external_ip = true
      custom_config = jsonencode({
        tools  = ["terraform", "kubectl", "helm", "gcloud"]
        access = ["full-gcp-apis"]
      })
      additional_tags = ["platform-eng", "infrastructure"]
    },

    # Security Agents
    {
      name               = "security-dev"
      agent_type         = "security-agent"
      machine_type       = "e2-standard-2"
      disk_size_gb       = 30
      workspace_size_gb  = 100
      preemptible        = true
      enable_external_ip = false # Security isolation
      custom_config = jsonencode({
        tools    = ["nmap", "trivy", "bandit", "semgrep"]
        scanning = ["container", "code", "infrastructure"]
      })
      additional_tags = ["security", "isolated"]
    },

    # QA Automation Agents
    {
      name               = "qa-dev"
      agent_type         = "qa-automation"
      machine_type       = "e2-standard-2"
      disk_size_gb       = 30
      workspace_size_gb  = 50
      preemptible        = true
      enable_external_ip = true
      custom_config = jsonencode({
        tools    = ["pytest", "jest", "playwright", "selenium"]
        browsers = ["chrome", "firefox"]
      })
      additional_tags = ["qa", "testing"]
    }
  ]

  # Agent pools with development-appropriate scaling
  agent_pools = [
    # Backend development pool
    {
      name               = "backend-dev-pool"
      agent_type         = "backend-developer"
      template_name      = "backend-dev"
      target_size        = 2
      enable_autoscaling = true
      min_replicas       = 1
      max_replicas       = 8
      cpu_target         = 0.75
      named_ports = [
        { name = "http", port = 8080 },
        { name = "debug", port = 5000 },
        { name = "metrics", port = 9090 }
      ]
    },

    # Frontend development pool
    {
      name               = "frontend-dev-pool"
      agent_type         = "frontend-developer"
      template_name      = "frontend-dev"
      target_size        = 2
      enable_autoscaling = true
      min_replicas       = 1
      max_replicas       = 5
      cpu_target         = 0.70
      named_ports = [
        { name = "dev-server", port = 3000 },
        { name = "storybook", port = 6006 },
        { name = "metrics", port = 9090 }
      ]
    },

    # Platform engineering pool (always-on for infrastructure)
    {
      name               = "platform-dev-pool"
      agent_type         = "platform-engineer"
      template_name      = "platform-dev"
      target_size        = 1
      enable_autoscaling = false # Stable infrastructure management
      min_replicas       = 1
      max_replicas       = 3
    },

    # Security pool (on-demand)
    {
      name               = "security-dev-pool"
      agent_type         = "security-agent"
      template_name      = "security-dev"
      target_size        = 0 # Start with no instances, scale on demand
      enable_autoscaling = true
      min_replicas       = 0
      max_replicas       = 3
      cpu_target         = 0.60
    },

    # QA automation pool
    {
      name               = "qa-dev-pool"
      agent_type         = "qa-automation"
      template_name      = "qa-dev"
      target_size        = 1
      enable_autoscaling = true
      min_replicas       = 0
      max_replicas       = 5
      cpu_target         = 0.80
    }
  ]

  # Development-specific firewall rules
  firewall_rules = {
    # Allow HTTP/HTTPS access for development servers
    "allow-dev-http" = {
      description   = "Allow HTTP access to development servers"
      direction     = "INGRESS"
      source_ranges = ["10.0.0.0/8", "0.0.0.0/0"] # Open for dev
      target_tags   = ["agent-vm", "backend-dev", "frontend-dev"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["80", "443", "3000", "8080", "5000", "6006"]
        }
      ]
    }

    # Allow SSH access for debugging
    "allow-dev-ssh" = {
      description   = "Allow SSH access for development and debugging"
      direction     = "INGRESS"
      source_ranges = ["10.0.0.0/8"]
      target_tags   = ["agent-vm"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["22"]
        }
      ]
    }

    # Allow metrics collection
    "allow-dev-metrics" = {
      description   = "Allow metrics collection from agents"
      direction     = "INGRESS"
      source_ranges = ["10.0.0.0/8"]
      target_tags   = ["agent-vm"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["9090", "9091", "9100"]
        }
      ]
    }

    # Restrict security agent access
    "restrict-security-access" = {
      description        = "Restrict security agent external access"
      direction          = "EGRESS"
      target_tags        = ["security", "isolated"]
      destination_ranges = ["0.0.0.0/0"]
      deny = [
        {
          protocol = "tcp"
          ports    = ["80", "443"]
        }
      ]
    }
  }

  # Development configuration
  default_preemptible     = true # Cost optimization
  enable_health_checks    = true
  enable_monitoring       = true
  enable_firewall_logging = false # Reduce noise in dev

  # Agent-cage configuration
  agent_cage_version       = "latest"
  agent_startup_script_url = "gs://genesis-artifacts-dev/scripts/agent-startup.sh"

  # Autoscaling configuration
  default_enable_autoscaling    = true
  enable_predictive_autoscaling = false # Not needed for dev
  scale_down_max_percent        = 50    # Faster scale-down for cost
}

# Outputs for integration with other systems
output "vm_management_summary" {
  description = "VM management deployment summary"
  value       = module.vm_management.vm_management_summary
}

output "agent_pools" {
  description = "Agent pool information"
  value       = module.vm_management.agent_pools
}

output "health_check_endpoints" {
  description = "Health check endpoints for monitoring"
  value = {
    for pool_name, pool in module.vm_management.agent_pools : pool_name => {
      health_url  = "http://{instance_ip}:8080/health"
      metrics_url = "http://{instance_ip}:9090/metrics"
    }
  }
}

output "cost_optimization" {
  description = "Cost optimization settings and estimates"
  value       = module.vm_management.cost_optimization
}

# Development-specific outputs
output "development_access" {
  description = "Development access information"
  value = {
    ssh_command = "gcloud compute ssh {instance_name} --zone={zone} --project=${local.project_id}"

    port_forwards = {
      backend_dev  = "gcloud compute ssh {instance_name} --zone={zone} --ssh-flag='-L 8080:localhost:8080' --project=${local.project_id}"
      frontend_dev = "gcloud compute ssh {instance_name} --zone={zone} --ssh-flag='-L 3000:localhost:3000' --project=${local.project_id}"
    }

    monitoring = {
      health_checks = "curl http://{external_ip}:8080/health"
      metrics       = "curl http://{external_ip}:9090/metrics"
      logs          = "gcloud logging read 'resource.type=gce_instance AND labels.agent_type={agent_type}' --project=${local.project_id}"
    }
  }
}
