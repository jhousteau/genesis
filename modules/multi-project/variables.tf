# Multi-Project Bootstrap Module Variables

variable "projects" {
  description = "List of projects to bootstrap"
  type = list(object({
    # Required fields
    project_id      = string
    billing_account = string
    
    # Optional fields
    project_name                = optional(string)
    org_id                     = optional(string)
    folder_id                  = optional(string)
    environment                = optional(string, "production")
    labels                     = optional(map(string), {})
    region                     = optional(string)
    
    # API configuration
    activate_apis              = optional(list(string))
    disable_services_on_destroy = optional(bool, false)
    
    # Service account configuration
    create_terraform_sa        = optional(bool, true)
    terraform_sa_name          = optional(string)
    terraform_sa_roles         = optional(list(string))
    
    # Budget configuration
    budget_amount              = optional(number)
    budget_alert_thresholds    = optional(list(number))
    grant_billing_role         = optional(bool, false)
    
    # State bucket configuration
    state_bucket_name          = optional(string)
    state_bucket_location      = optional(string)
    storage_class             = optional(string, "STANDARD")
    lifecycle_rules           = optional(list(object({
      action    = map(string)
      condition = map(string)
    })))
    force_destroy_state       = optional(bool, false)
    
    # Service accounts
    custom_service_accounts   = optional(map(object({
      account_id    = string
      display_name  = string
      description   = optional(string)
      project_roles = optional(list(string), [])
      org_roles     = optional(list(string), [])
      folder_roles  = optional(list(string), [])
    })), {})
    cicd_roles               = optional(list(string))
    app_roles                = optional(list(string))
    
    # Workload Identity Federation
    pool_id                  = optional(string)
    workload_identity_providers = optional(map(object({
      provider_id         = string
      provider_type      = string
      issuer_uri         = optional(string)
      allowed_audiences  = optional(list(string))
      attribute_mapping  = optional(map(string))
      attribute_condition = optional(string)
      
      # Provider-specific configs
      github = optional(object({
        organization = string
        repositories = optional(list(string))
        branches     = optional(list(string))
        environments = optional(list(string))
      }))
      gitlab = optional(object({
        host         = optional(string, "gitlab.com")
        namespace_id = optional(string)
        project_ids  = optional(list(string))
        ref_types    = optional(list(string))
        refs         = optional(list(string))
      }))
      azure = optional(object({
        tenant_id       = string
        subscription_id = optional(string)
        client_id       = optional(string)
      }))
      terraform_cloud = optional(object({
        organization_id = string
        workspace_id    = optional(string)
        workspace_name  = optional(string)
      }))
    })))
    wif_roles               = optional(list(string))
    
    # Networking
    create_network          = optional(bool, false)
    network_name           = optional(string)
    routing_mode           = optional(string, "REGIONAL")
    enable_flow_logs       = optional(bool, false)
    subnets = optional(list(object({
      name   = string
      cidr   = string
      region = optional(string)
    })))
    
    # Other settings
    skip_delete            = optional(bool, false)
  }))
  
  validation {
    condition = alltrue([for p in var.projects : can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", p.project_id))])
    error_message = "Project IDs must be between 6 and 30 characters, contain only lowercase letters, numbers, and hyphens."
  }
}

variable "deployment_name" {
  description = "Name for this deployment set (used for grouping projects)"
  type        = string
  default     = "bootstrap"
}

variable "project_group" {
  description = "Group name for these projects (for labeling and organization)"
  type        = string
  default     = "multi-project"
}

variable "org_id" {
  description = "Default organization ID (can be overridden per project)"
  type        = string
  default     = ""
}

variable "folder_id" {
  description = "Default folder ID (can be overridden per project)"
  type        = string
  default     = ""
}

variable "default_region" {
  description = "Default region for resources"
  type        = string
  default     = "us-central1"
}

variable "default_labels" {
  description = "Default labels to apply to all projects"
  type        = map(string)
  default = {
    managed_by  = "terraform"
    provisioner = "multi-project-bootstrap"
  }
}

# Default configurations
variable "default_settings" {
  description = "Default settings applied to all projects (can be overridden per project)"
  type        = any
  default     = {}
}

variable "default_apis" {
  description = "Default list of APIs to enable in all projects"
  type        = list(string)
  default = [
    "cloudapis.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "serviceusage.googleapis.com",
    "storage-api.googleapis.com",
    "storage.googleapis.com",
  ]
}

variable "default_terraform_roles" {
  description = "Default IAM roles for Terraform service account"
  type        = list(string)
  default = [
    "roles/resourcemanager.projectIamAdmin",
    "roles/storage.admin",
    "roles/serviceusage.serviceUsageAdmin",
  ]
}

variable "default_budget_amount" {
  description = "Default budget amount in USD"
  type        = number
  default     = 1000
}

variable "default_budget_alerts" {
  description = "Default budget alert thresholds (as percentages)"
  type        = list(number)
  default     = [50, 75, 90, 100]
}

variable "default_lifecycle_rules" {
  description = "Default lifecycle rules for state buckets"
  type = list(object({
    action    = map(string)
    condition = map(string)
  }))
  default = [
    {
      action = {
        type = "Delete"
      }
      condition = {
        age                   = "90"
        with_state            = "ARCHIVED"
        matches_storage_class = ["NEARLINE", "COLDLINE", "ARCHIVE"]
      }
    },
    {
      action = {
        type          = "SetStorageClass"
        storage_class = "NEARLINE"
      }
      condition = {
        age                   = "30"
        matches_storage_class = ["STANDARD"]
      }
    }
  ]
}

# Service Account defaults
variable "create_default_service_accounts" {
  description = "Create default service accounts (cicd, monitoring, app) for each project"
  type        = bool
  default     = true
}

variable "default_cicd_roles" {
  description = "Default roles for CI/CD service account"
  type        = list(string)
  default = [
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.builder",
    "roles/run.developer",
    "roles/storage.objectAdmin",
  ]
}

variable "default_app_roles" {
  description = "Default roles for application service account"
  type        = list(string)
  default = [
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/secretmanager.secretAccessor",
  ]
}

# Workload Identity Federation defaults
variable "default_wif_providers" {
  description = "Default Workload Identity Federation providers"
  type = map(object({
    provider_id         = string
    provider_type      = string
    issuer_uri         = optional(string)
    allowed_audiences  = optional(list(string))
    attribute_mapping  = optional(map(string))
    attribute_condition = optional(string)
    
    github = optional(object({
      organization = string
      repositories = optional(list(string))
      branches     = optional(list(string))
      environments = optional(list(string))
    }))
    gitlab = optional(object({
      host         = optional(string)
      namespace_id = optional(string)
      project_ids  = optional(list(string))
      ref_types    = optional(list(string))
      refs         = optional(list(string))
    }))
    azure = optional(object({
      tenant_id       = string
      subscription_id = optional(string)
      client_id       = optional(string)
    }))
    terraform_cloud = optional(object({
      organization_id = string
      workspace_id    = optional(string)
      workspace_name  = optional(string)
    }))
  }))
  default = {}
}

variable "default_wif_roles" {
  description = "Default roles for Workload Identity Federation service account"
  type        = list(string)
  default = [
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.builder",
    "roles/run.admin",
    "roles/storage.objectAdmin",
  ]
}

# Feature flags
variable "create_state_buckets" {
  description = "Create state storage buckets for all projects"
  type        = bool
  default     = true
}

variable "create_service_accounts" {
  description = "Create service accounts for all projects"
  type        = bool
  default     = true
}

variable "enable_workload_identity" {
  description = "Enable Workload Identity Federation for all projects"
  type        = bool
  default     = true
}

# Advanced options
variable "parallel_deployments" {
  description = "Enable parallel deployments (may cause quota issues with large lists)"
  type        = bool
  default     = true
}

variable "error_on_partial_failure" {
  description = "Fail the entire deployment if any project fails"
  type        = bool
  default     = false
}

variable "dry_run" {
  description = "Perform a dry run (plan only, no apply)"
  type        = bool
  default     = false
}