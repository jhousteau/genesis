/**
 * VM Management Layer Variables
 *
 * Configuration variables for agent VM management infrastructure
 */

# Core Configuration
variable "project_id" {
  description = "GCP project ID for VM resources"
  type        = string
}

variable "region" {
  description = "GCP region for VM resources"
  type        = string
}

variable "zones" {
  description = "List of zones for VM distribution"
  type        = list(string)
  default     = []
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "genesis"
}

variable "labels" {
  description = "Additional labels to apply to all resources"
  type        = map(string)
  default     = {}
}

# Network Configuration
variable "network_id" {
  description = "VPC network ID for VM instances"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for VM instances"
  type        = string
}

variable "network_tags" {
  description = "Network tags to apply to VM instances"
  type        = list(string)
  default     = ["genesis-vm", "agent-runtime"]
}

# Agent VM Templates Configuration
variable "agent_vm_templates" {
  description = "Agent VM template configurations"
  type = list(object({
    name                        = string
    agent_type                  = string
    machine_type                = optional(string)
    source_image                = optional(string)
    disk_size_gb                = optional(number)
    disk_type                   = optional(string)
    enable_workspace_disk       = optional(bool, true)
    workspace_size_gb           = optional(number, 50)
    enable_external_ip          = optional(bool)
    service_account_email       = optional(string)
    scopes                      = optional(list(string))
    metadata                    = optional(map(string), {})
    additional_tags             = optional(list(string), [])
    labels                      = optional(map(string), {})
    preemptible                 = optional(bool)
    automatic_restart           = optional(bool)
    enable_confidential_compute = optional(bool, false)
    custom_config               = optional(string, "{}")
  }))
  default = []

  validation {
    condition = alltrue([
      for template in var.agent_vm_templates : contains([
        "backend-developer", "frontend-developer", "platform-engineer",
        "data-engineer", "integration-agent", "qa-automation",
        "sre-agent", "security-agent", "devops-agent",
        "project-manager", "architect", "tech-lead"
      ], template.agent_type)
    ])
    error_message = "Agent type must be one of the supported Genesis agent types."
  }
}

# Agent Pools Configuration
variable "agent_pools" {
  description = "Agent pool configurations for managed instance groups"
  type = list(object({
    name                       = string
    agent_type                 = string
    template_name              = string
    target_size                = optional(number)
    enable_autoscaling         = optional(bool)
    min_replicas               = optional(number)
    max_replicas               = optional(number)
    cpu_target                 = optional(number)
    max_surge                  = optional(number, 1)
    max_unavailable            = optional(number, 0)
    min_ready_sec              = optional(number, 60)
    health_check_initial_delay = optional(number, 300)
    named_ports = optional(list(object({
      name = string
      port = number
    })), [])
    custom_metrics = optional(list(object({
      name   = string
      target = number
      type   = string
    })), [])
    labels       = optional(map(string), {})
    scaling_mode = optional(string, "manual")
  }))
  default = []
}

# Default VM Configuration
variable "default_agent_machine_type" {
  description = "Default machine type for agent VMs"
  type        = string
  default     = "e2-standard-2"
}

variable "default_agent_image" {
  description = "Default source image for agent VMs"
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2204-lts"
}

variable "default_disk_size_gb" {
  description = "Default boot disk size in GB"
  type        = number
  default     = 20
}

variable "default_enable_external_ip" {
  description = "Enable external IP by default"
  type        = bool
  default     = true
}

variable "default_agent_service_account" {
  description = "Default service account email for agent VMs"
  type        = string
  default     = null
}

variable "default_agent_scopes" {
  description = "Default OAuth scopes for agent VMs"
  type        = list(string)
  default = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/compute",
    "https://www.googleapis.com/auth/monitoring",
    "https://www.googleapis.com/auth/logging.write"
  ]
}

variable "default_preemptible" {
  description = "Use preemptible instances by default"
  type        = bool
  default     = false
}

# Agent Pool Defaults
variable "default_pool_size" {
  description = "Default target size for agent pools"
  type        = number
  default     = 1
}

variable "default_enable_autoscaling" {
  description = "Enable autoscaling by default"
  type        = bool
  default     = false
}

variable "default_min_replicas" {
  description = "Default minimum replicas for autoscaling"
  type        = number
  default     = 1
}

variable "default_max_replicas" {
  description = "Default maximum replicas for autoscaling"
  type        = number
  default     = 10
}

variable "default_cpu_target" {
  description = "Default CPU utilization target for autoscaling"
  type        = number
  default     = 0.75
}

variable "default_cooldown_period" {
  description = "Default autoscaling cooldown period in seconds"
  type        = number
  default     = 60
}

variable "default_named_ports" {
  description = "Default named ports for agent VMs"
  type = list(object({
    name = string
    port = number
  }))
  default = [
    {
      name = "http"
      port = 8080
    },
    {
      name = "metrics"
      port = 9090
    }
  ]
}

variable "default_custom_metrics" {
  description = "Default custom metrics for autoscaling"
  type = list(object({
    name   = string
    target = number
    type   = string
  }))
  default = []
}

# Security Configuration
variable "enable_disk_encryption" {
  description = "Enable disk encryption with KMS"
  type        = bool
  default     = true
}

variable "disk_encryption_key" {
  description = "KMS key for disk encryption"
  type        = string
  default     = null
}

variable "enable_secure_boot" {
  description = "Enable Shielded VM secure boot"
  type        = bool
  default     = true
}

variable "enable_vtpm" {
  description = "Enable Shielded VM vTPM"
  type        = bool
  default     = true
}

variable "enable_integrity_monitoring" {
  description = "Enable Shielded VM integrity monitoring"
  type        = bool
  default     = true
}

# Health Checks
variable "enable_health_checks" {
  description = "Enable health checks for agent pools"
  type        = bool
  default     = true
}

variable "health_check_interval" {
  description = "Health check interval in seconds"
  type        = number
  default     = 5
}

variable "health_check_timeout" {
  description = "Health check timeout in seconds"
  type        = number
  default     = 5
}

variable "health_check_healthy_threshold" {
  description = "Number of consecutive successful checks for healthy"
  type        = number
  default     = 2
}

variable "health_check_unhealthy_threshold" {
  description = "Number of consecutive failed checks for unhealthy"
  type        = number
  default     = 3
}

variable "default_health_port" {
  description = "Default port for health checks"
  type        = number
  default     = 8080
}

variable "default_health_path" {
  description = "Default path for health checks"
  type        = string
  default     = "/health"
}

variable "enable_health_check_logging" {
  description = "Enable health check logging"
  type        = bool
  default     = true
}

# Scaling Configuration
variable "enable_predictive_autoscaling" {
  description = "Enable predictive autoscaling"
  type        = bool
  default     = false
}

variable "scale_down_max_percent" {
  description = "Maximum percentage of instances to scale down at once"
  type        = number
  default     = 25
}

variable "scale_down_time_window" {
  description = "Time window for scale down control in seconds"
  type        = number
  default     = 600
}

# Firewall Configuration
variable "firewall_rules" {
  description = "Firewall rules for agent VMs"
  type = map(object({
    description        = string
    direction          = string
    priority           = optional(number, 1000)
    source_ranges      = optional(list(string))
    destination_ranges = optional(list(string))
    source_tags        = optional(list(string))
    target_tags        = optional(list(string))
    allow = optional(list(object({
      protocol = string
      ports    = optional(list(string))
    })), [])
    deny = optional(list(object({
      protocol = string
      ports    = optional(list(string))
    })), [])
  }))
  default = {
    "allow-agent-http" = {
      description   = "Allow HTTP access to agent VMs"
      direction     = "INGRESS"
      source_ranges = ["10.0.0.0/8"]
      target_tags   = ["agent-vm"]
      allow = [{
        protocol = "tcp"
        ports    = ["8080", "9090"]
      }]
    }
    "allow-agent-ssh" = {
      description   = "Allow SSH access to agent VMs"
      direction     = "INGRESS"
      source_ranges = ["10.0.0.0/8"]
      target_tags   = ["agent-vm"]
      allow = [{
        protocol = "tcp"
        ports    = ["22"]
      }]
    }
  }
}

variable "enable_firewall_logging" {
  description = "Enable firewall rule logging"
  type        = bool
  default     = true
}

# Agent Configuration
variable "agent_cage_version" {
  description = "Version of agent-cage to deploy"
  type        = string
  default     = "latest"
}

variable "agent_startup_script_url" {
  description = "URL to agent startup script"
  type        = string
  default     = ""
}

variable "enable_monitoring" {
  description = "Enable monitoring for agent VMs"
  type        = bool
  default     = true
}

# Resource Policies
variable "resource_policies" {
  description = "Resource policies to apply to VMs"
  type        = list(string)
  default     = []
}
