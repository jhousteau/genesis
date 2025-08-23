# Genesis VM Management Layer - Production Environment
# Production-ready deployment with high availability, security, and monitoring
# Implements full PIPES methodology for production agent-cage infrastructure

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "genesis-terraform-state-prod"
    prefix = "vm-management/production"
  }
}

# Production configuration
locals {
  # Core project settings
  project_id = "genesis-platform-prod"
  region     = "us-central1"
  zones      = ["us-central1-a", "us-central1-b", "us-central1-c", "us-central1-f"]

  # Multi-region backup zones
  backup_region = "us-east1"
  backup_zones  = ["us-east1-b", "us-east1-c", "us-east1-d"]

  environment = "prod"

  # Production labels for resource management
  production_labels = {
    project         = "genesis"
    environment     = "production"
    managed_by      = "terraform"
    component       = "vm-management"
    cost_center     = "platform"
    security_level  = "high"
    backup_required = "true"
    monitoring      = "enabled"
  }
}

# Data sources for existing production infrastructure
data "google_compute_network" "genesis_vpc_prod" {
  name    = "genesis-vpc-prod"
  project = local.project_id
}

data "google_compute_subnetwork" "genesis_subnet_prod" {
  name    = "genesis-subnet-prod"
  region  = local.region
  project = local.project_id
}

data "google_service_account" "agent_sa_prod" {
  account_id = "genesis-agent-prod"
  project    = local.project_id
}

# Production-grade KMS encryption
resource "google_kms_key_ring" "vm_encryption_prod" {
  name     = "genesis-vm-encryption-prod"
  location = local.region
  project  = local.project_id
}

resource "google_kms_crypto_key" "vm_disk_key_prod" {
  name            = "vm-disk-encryption-prod"
  key_ring        = google_kms_key_ring.vm_encryption_prod.id
  purpose         = "ENCRYPT_DECRYPT"
  rotation_period = "7776000s" # 90 days

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# VM Management Layer - Production Deployment
module "vm_management_prod" {
  source = "../../modules/vm-management"

  # Core configuration
  project_id  = local.project_id
  region      = local.region
  zones       = local.zones
  environment = local.environment
  name_prefix = "genesis-prod"
  labels      = local.production_labels

  # Network configuration with security
  network_id   = data.google_compute_network.genesis_vpc_prod.id
  subnet_id    = data.google_compute_subnetwork.genesis_subnet_prod.id
  network_tags = ["genesis-prod", "agent-runtime", "high-security"]

  # Production security configuration
  enable_disk_encryption      = true
  disk_encryption_key         = google_kms_crypto_key.vm_disk_key_prod.id
  enable_secure_boot          = true
  enable_vtpm                 = true
  enable_integrity_monitoring = true

  # Service account with minimal permissions
  default_agent_service_account = data.google_service_account.agent_sa_prod.email
  default_agent_scopes = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/compute.readonly",
    "https://www.googleapis.com/auth/monitoring.write",
    "https://www.googleapis.com/auth/logging.write",
    "https://www.googleapis.com/auth/trace.append"
  ]

  # Production agent templates with optimized configurations
  agent_vm_templates = [
    # Backend Developer Agents - Production Scale
    {
      name                        = "backend-prod"
      agent_type                  = "backend-developer"
      machine_type                = "c2-standard-4" # High-performance
      source_image                = "projects/genesis-platform-prod/global/images/genesis-agent-ubuntu-2204"
      disk_size_gb                = 50
      workspace_size_gb           = 200
      preemptible                 = false # No preemptible in production
      automatic_restart           = true
      enable_external_ip          = false # Internal only for security
      enable_confidential_compute = false
      custom_config = jsonencode({
        production = true
        tools      = ["python", "node", "go", "docker"]
        monitoring = ["prometheus", "jaeger", "opencensus"]
        security   = ["vault", "tls", "rbac"]
      })
      additional_tags = ["backend-prod", "high-performance", "internal-only"]
      labels = {
        tier        = "backend"
        criticality = "high"
      }
    },

    # Frontend Developer Agents - CDN Optimized
    {
      name               = "frontend-prod"
      agent_type         = "frontend-developer"
      machine_type       = "n2-standard-2"
      disk_size_gb       = 30
      workspace_size_gb  = 100
      preemptible        = false
      automatic_restart  = true
      enable_external_ip = false
      custom_config = jsonencode({
        production = true
        tools      = ["node", "webpack", "chrome-headless"]
        cdn        = ["cloudflare", "cloud-cdn"]
        frameworks = ["react", "vue", "angular"]
      })
      additional_tags = ["frontend-prod", "cdn-optimized"]
      labels = {
        tier        = "frontend"
        criticality = "medium"
      }
    },

    # Platform Engineer Agents - Infrastructure Critical
    {
      name                        = "platform-prod"
      agent_type                  = "platform-engineer"
      machine_type                = "c2-standard-8" # Maximum performance
      disk_size_gb                = 100
      workspace_size_gb           = 500
      preemptible                 = false
      automatic_restart           = true
      enable_external_ip          = false
      enable_confidential_compute = true # Sensitive infrastructure operations
      custom_config = jsonencode({
        production = true
        tools      = ["terraform", "kubectl", "helm", "vault"]
        access     = ["full-gcp-apis", "kubernetes-admin"]
        backup     = ["automated", "cross-region"]
      })
      additional_tags = ["platform-prod", "infrastructure-critical", "confidential"]
      labels = {
        tier        = "platform"
        criticality = "critical"
      }
    },

    # Security Agents - Isolated and Hardened
    {
      name                        = "security-prod"
      agent_type                  = "security-agent"
      machine_type                = "c2-standard-4"
      disk_size_gb                = 50
      workspace_size_gb           = 200
      preemptible                 = false
      automatic_restart           = true
      enable_external_ip          = false
      enable_confidential_compute = true
      custom_config = jsonencode({
        production = true
        tools      = ["nmap", "trivy", "vault", "gcp-scanner"]
        scanning   = ["continuous", "compliance", "vulnerability"]
        isolation  = ["network", "compute", "data"]
      })
      additional_tags = ["security-prod", "isolated", "hardened"]
      labels = {
        tier        = "security"
        criticality = "critical"
      }
    },

    # SRE Agents - Monitoring and Response
    {
      name               = "sre-prod"
      agent_type         = "sre-agent"
      machine_type       = "n2-standard-4"
      disk_size_gb       = 50
      workspace_size_gb  = 300
      preemptible        = false
      automatic_restart  = true
      enable_external_ip = false
      custom_config = jsonencode({
        production = true
        tools      = ["prometheus", "grafana", "pagerduty", "kubectl"]
        monitoring = ["sli", "slo", "error-budget"]
        automation = ["incident-response", "capacity-planning"]
      })
      additional_tags = ["sre-prod", "monitoring", "incident-response"]
      labels = {
        tier        = "operations"
        criticality = "high"
      }
    },

    # QA Automation - Continuous Testing
    {
      name               = "qa-prod"
      agent_type         = "qa-automation"
      machine_type       = "n2-standard-2"
      disk_size_gb       = 30
      workspace_size_gb  = 100
      preemptible        = false
      automatic_restart  = true
      enable_external_ip = false
      custom_config = jsonencode({
        production = true
        tools      = ["pytest", "selenium", "k6", "lighthouse"]
        testing    = ["e2e", "performance", "security", "accessibility"]
        reporting  = ["junit", "allure", "slack"]
      })
      additional_tags = ["qa-prod", "testing", "continuous"]
      labels = {
        tier        = "testing"
        criticality = "medium"
      }
    }
  ]

  # Production agent pools with high availability
  agent_pools = [
    # Backend production pool - High availability
    {
      name                       = "backend-prod-pool"
      agent_type                 = "backend-developer"
      template_name              = "backend-prod"
      target_size                = 6 # Minimum for HA across 3 zones
      enable_autoscaling         = true
      min_replicas               = 6
      max_replicas               = 30
      cpu_target                 = 0.65
      max_surge                  = 3
      max_unavailable            = 1
      min_ready_sec              = 120
      health_check_initial_delay = 300
      named_ports = [
        { name = "http", port = 8080 },
        { name = "grpc", port = 9000 },
        { name = "metrics", port = 9090 },
        { name = "health", port = 8086 }
      ]
      custom_metrics = [
        {
          name   = "custom.googleapis.com/agent/queue_length"
          target = 10
          type   = "GAUGE"
        }
      ]
      labels = {
        tier           = "backend"
        scaling_policy = "cpu-and-queue"
      }
    },

    # Frontend production pool
    {
      name               = "frontend-prod-pool"
      agent_type         = "frontend-developer"
      template_name      = "frontend-prod"
      target_size        = 3
      enable_autoscaling = true
      min_replicas       = 3
      max_replicas       = 15
      cpu_target         = 0.70
      max_surge          = 2
      max_unavailable    = 0 # No downtime tolerance
      min_ready_sec      = 90
      named_ports = [
        { name = "http", port = 3000 },
        { name = "metrics", port = 9090 }
      ]
    },

    # Platform engineering pool - Always available
    {
      name               = "platform-prod-pool"
      agent_type         = "platform-engineer"
      template_name      = "platform-prod"
      target_size        = 3 # One per zone minimum
      enable_autoscaling = true
      min_replicas       = 3
      max_replicas       = 9
      cpu_target         = 0.80 # Higher threshold for infra work
      max_unavailable    = 0    # Critical infrastructure
      min_ready_sec      = 180
    },

    # Security pool - Dedicated and isolated
    {
      name               = "security-prod-pool"
      agent_type         = "security-agent"
      template_name      = "security-prod"
      target_size        = 2
      enable_autoscaling = true
      min_replicas       = 2
      max_replicas       = 6
      cpu_target         = 0.60 # Security scans are bursty
      max_unavailable    = 0
    },

    # SRE pool - Monitoring and incident response
    {
      name               = "sre-prod-pool"
      agent_type         = "sre-agent"
      template_name      = "sre-prod"
      target_size        = 2
      enable_autoscaling = true
      min_replicas       = 2
      max_replicas       = 8
      cpu_target         = 0.75
      custom_metrics = [
        {
          name   = "custom.googleapis.com/incidents/active_count"
          target = 5
          type   = "GAUGE"
        }
      ]
    },

    # QA automation pool
    {
      name               = "qa-prod-pool"
      agent_type         = "qa-automation"
      template_name      = "qa-prod"
      target_size        = 2
      enable_autoscaling = true
      min_replicas       = 1
      max_replicas       = 10
      cpu_target         = 0.70
    }
  ]

  # Production firewall rules - Restrictive security
  firewall_rules = {
    # Internal communication only
    "allow-internal-agent-communication" = {
      description   = "Allow internal communication between agents"
      direction     = "INGRESS"
      priority      = 1000
      source_ranges = ["10.0.0.0/8"]
      target_tags   = ["agent-vm", "genesis-prod"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["8080", "8086", "9000", "9090"]
        }
      ]
    }

    # Load balancer health checks
    "allow-lb-health-checks" = {
      description   = "Allow Google load balancer health checks"
      direction     = "INGRESS"
      priority      = 1000
      source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
      target_tags   = ["agent-vm"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["8080", "8086"]
        }
      ]
    }

    # SSH access via bastion (Identity-Aware Proxy)
    "allow-iap-ssh" = {
      description   = "Allow SSH via Identity-Aware Proxy"
      direction     = "INGRESS"
      priority      = 1000
      source_ranges = ["35.235.240.0/20"]
      target_tags   = ["agent-vm"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["22"]
        }
      ]
    }

    # Restrict security agent egress
    "restrict-security-egress" = {
      description        = "Restrict security agent external access"
      direction          = "EGRESS"
      priority           = 500
      destination_ranges = ["0.0.0.0/0"]
      target_tags        = ["security-prod", "isolated"]
      deny = [
        {
          protocol = "tcp"
          ports    = ["80", "443"]
        }
      ]
    }

    # Allow monitoring egress
    "allow-monitoring-egress" = {
      description        = "Allow monitoring and logging egress"
      direction          = "EGRESS"
      priority           = 1000
      destination_ranges = ["0.0.0.0/0"]
      target_tags        = ["agent-vm"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["443"] # HTTPS only
        }
      ]
    }
  }

  # Production defaults
  default_preemptible        = false # No preemptible in production
  default_enable_external_ip = false # Security requirement

  # Health and monitoring
  enable_health_checks        = true
  enable_monitoring           = true
  enable_firewall_logging     = true
  enable_health_check_logging = true

  # Optimized health check settings for production
  health_check_interval            = 10
  health_check_timeout             = 5
  health_check_healthy_threshold   = 2
  health_check_unhealthy_threshold = 3

  # Production autoscaling
  default_enable_autoscaling    = true
  enable_predictive_autoscaling = true # Production optimization
  default_cooldown_period       = 120  # Longer cooldown for stability
  scale_down_max_percent        = 25   # Conservative scale-down
  scale_down_time_window        = 900  # 15-minute scale-down window

  # Agent-cage production configuration
  agent_cage_version       = "v1.2.3" # Pinned version for stability
  agent_startup_script_url = "gs://genesis-artifacts-prod/scripts/agent-startup.sh"
}

# Production monitoring and alerting
resource "google_monitoring_alert_policy" "agent_pool_health" {
  for_each = module.vm_management_prod.agent_pools

  display_name = "Agent Pool Health - ${each.key}"
  project      = local.project_id

  conditions {
    display_name = "Instance group unhealthy"

    condition_threshold {
      filter          = "resource.type=\"gce_instance_group\" AND resource.labels.instance_group_name=\"${each.value.name}\""
      comparison      = "COMPARISON_LESS_THAN"
      threshold_value = each.value.target_size * 0.8 # Alert if less than 80% healthy
      duration        = "300s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = [
    # Add your notification channels here
  ]

  alert_strategy {
    auto_close = "1800s" # Auto-close after 30 minutes
  }
}

# Backup configuration for critical data
resource "google_compute_resource_policy" "agent_workspace_backup" {
  name    = "agent-workspace-backup-prod"
  project = local.project_id
  region  = local.region

  snapshot_schedule_policy {
    schedule {
      daily_schedule {
        days_in_cycle = 1
        start_time    = "04:00" # 4 AM UTC
      }
    }

    retention_policy {
      max_retention_days    = 30
      on_source_disk_delete = "KEEP_AUTO_SNAPSHOTS"
    }

    snapshot_properties {
      labels = merge(local.production_labels, {
        backup_type = "workspace"
        automated   = "true"
      })
    }
  }
}

# Outputs for production monitoring and operations
output "production_vm_summary" {
  description = "Production VM management deployment summary"
  value       = module.vm_management_prod.vm_management_summary
}

output "production_endpoints" {
  description = "Production operational endpoints"
  value       = module.vm_management_prod.operational_endpoints
}

output "security_configuration" {
  description = "Production security configuration"
  value       = module.vm_management_prod.security_summary
}

output "production_cost_estimate" {
  description = "Production cost estimates and optimization"
  value       = module.vm_management_prod.cost_optimization
}

output "monitoring_integration" {
  description = "Monitoring and alerting integration points"
  value = {
    alert_policies = {
      for policy in google_monitoring_alert_policy.agent_pool_health :
      policy.display_name => {
        name         = policy.name
        display_name = policy.display_name
        enabled      = policy.enabled
      }
    }

    health_checks = module.vm_management_prod.health_checks

    log_filters = {
      agent_errors       = "resource.type=gce_instance AND severity>=ERROR AND labels.agent_type=*"
      security_events    = "resource.type=gce_instance AND jsonPayload.event_type=security"
      performance_issues = "resource.type=gce_instance AND jsonPayload.cpu_utilization>0.9"
    }
  }
}

output "disaster_recovery" {
  description = "Disaster recovery configuration"
  value = {
    backup_policy = {
      name           = google_compute_resource_policy.agent_workspace_backup.name
      retention_days = 30
      schedule       = "daily-4am-utc"
    }

    multi_zone_deployment = {
      primary_zones = local.zones
      backup_region = local.backup_region
      backup_zones  = local.backup_zones
    }

    encryption = {
      kms_key_ring    = google_kms_key_ring.vm_encryption_prod.name
      crypto_key      = google_kms_crypto_key.vm_disk_key_prod.name
      rotation_period = "90-days"
    }
  }
}
