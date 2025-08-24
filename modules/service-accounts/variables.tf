/**
 * Service Accounts Module - Variables
 *
 * Define input variables for service account creation and management
 */

variable "project_id" {
  description = "The default GCP project ID where service accounts will be created"
  type        = string
}

variable "organization_id" {
  description = "The GCP organization ID (required for organization-level role bindings)"
  type        = string
  default     = null
}

variable "service_accounts" {
  description = "Map of service accounts to create with their configurations"
  type = map(object({
    # Basic configuration
    account_id   = string                # The service account ID (must be unique within project)
    display_name = string                # Display name for the service account
    description  = optional(string)      # Description of the service account's purpose
    project_id   = optional(string)      # Override project ID for this specific SA
    disabled     = optional(bool, false) # Whether the service account is disabled

    # IAM role bindings
    project_roles      = optional(list(string), [])      # List of project-level IAM roles
    organization_roles = optional(list(string), [])      # List of organization-level IAM roles
    folder_roles       = optional(map(list(string)), {}) # Map of folder IDs to list of roles

    # Impersonation configuration
    impersonators = optional(list(string), []) # List of identities that can impersonate this SA

    # Key management
    create_key           = optional(bool, false)      # Whether to create a key for this SA
    key_secret_accessors = optional(list(string), []) # Who can access the key in Secret Manager
  }))

  validation {
    condition = alltrue([
      for sa_key, sa in var.service_accounts :
      can(regex("^[a-z]([a-z0-9-]*[a-z0-9])?$", sa.account_id)) &&
      length(sa.account_id) >= 6 &&
      length(sa.account_id) <= 30
    ])
    error_message = "Service account IDs must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "store_keys_in_secret_manager" {
  description = "Whether to store service account keys in Secret Manager"
  type        = bool
  default     = true
}

variable "labels" {
  description = "Labels to apply to all resources created by this module"
  type        = map(string)
  default     = {}
}

# Predefined role sets for common use cases
variable "predefined_roles" {
  description = "Predefined role sets for common service account types"
  type = object({
    terraform_deployer = optional(list(string), [
      "roles/resourcemanager.projectIamAdmin",
      "roles/storage.admin",
      "roles/compute.admin",
      "roles/iam.serviceAccountAdmin",
      "roles/iam.serviceAccountKeyAdmin",
      "roles/secretmanager.admin",
      "roles/servicenetworking.networksAdmin",
      "roles/dns.admin",
      "roles/cloudkms.admin"
    ])
    cicd_pipeline = optional(list(string), [
      "roles/cloudbuild.builds.editor",
      "roles/storage.objectAdmin",
      "roles/artifactregistry.writer",
      "roles/run.admin",
      "roles/cloudfunction.admin",
      "roles/appengine.deployer",
      "roles/iam.serviceAccountUser"
    ])
    monitoring = optional(list(string), [
      "roles/monitoring.metricWriter",
      "roles/logging.logWriter",
      "roles/cloudtrace.agent",
      "roles/cloudprofiler.agent",
      "roles/errorreporting.writer"
    ])
    application_runtime = optional(list(string), [
      "roles/storage.objectViewer",
      "roles/secretmanager.secretAccessor",
      "roles/cloudsql.client",
      "roles/datastore.user",
      "roles/pubsub.publisher",
      "roles/pubsub.subscriber",
      "roles/cloudtasks.enqueuer"
    ])
    data_pipeline = optional(list(string), [
      "roles/bigquery.dataEditor",
      "roles/bigquery.jobUser",
      "roles/storage.objectAdmin",
      "roles/dataflow.worker",
      "roles/pubsub.editor",
      "roles/cloudfunctions.invoker"
    ])
    security_scanner = optional(list(string), [
      "roles/securitycenter.findingsViewer",
      "roles/cloudkms.viewer",
      "roles/iam.securityReviewer",
      "roles/compute.viewer",
      "roles/storage.objectViewer"
    ])
  })
  default = {}
}

# Common impersonation configurations
variable "enable_cross_project_impersonation" {
  description = "Enable service accounts to be impersonated from other projects"
  type        = bool
  default     = false
}

variable "impersonation_admin_members" {
  description = "List of identities that can manage impersonation for all service accounts"
  type        = list(string)
  default     = []
}

# Audit and compliance settings
variable "enable_audit_logs" {
  description = "Enable detailed audit logging for service account activities"
  type        = bool
  default     = true
}

variable "key_rotation_days" {
  description = "Number of days before service account keys should be rotated (informational)"
  type        = number
  default     = 90
}
# Advanced IAM Configuration
variable "advanced_iam_config" {
  description = "Advanced IAM configuration for service accounts"
  type = object({
    enable_conditional_access  = bool
    enable_custom_roles        = bool
    enable_just_in_time_access = bool
    access_boundary_policy     = optional(string)
    conditional_bindings = optional(list(object({
      role    = string
      members = list(string)
      condition = object({
        title       = string
        description = string
        expression  = string
      })
    })), [])
    custom_roles = optional(list(object({
      role_id     = string
      title       = string
      description = string
      permissions = list(string)
      stage       = string
    })), [])
  })
  default = {
    enable_conditional_access  = false
    enable_custom_roles        = false
    enable_just_in_time_access = false
    conditional_bindings       = []
    custom_roles               = []
  }
}

# Workload Identity Federation Configuration
variable "workload_identity_config" {
  description = "Workload Identity Federation configuration"
  type = object({
    enabled = bool
    identity_pools = list(object({
      pool_id      = string
      display_name = string
      description  = string
      disabled     = optional(bool, false)
      providers = list(object({
        provider_id         = string
        display_name        = string
        description         = string
        disabled            = optional(bool, false)
        attribute_mapping   = map(string)
        attribute_condition = optional(string)
        oidc_config = optional(object({
          issuer_uri        = string
          allowed_audiences = list(string)
          jwks_json         = optional(string)
        }))
        aws_config = optional(object({
          account_id = string
          sts_uri    = optional(string)
        }))
        saml_config = optional(object({
          idp_metadata_xml = string
        }))
      }))
    }))
    service_account_bindings = list(object({
      service_account_key = string
      pool_id             = string
      provider_id         = string
      members             = list(string)
    }))
  })
  default = {
    enabled                  = false
    identity_pools           = []
    service_account_bindings = []
  }
}

# Enhanced Security Configuration
variable "enhanced_security" {
  description = "Enhanced security configuration for service accounts"
  type = object({
    enable_key_rotation     = bool
    key_rotation_schedule   = string
    automated_key_rotation  = bool
    enable_access_logging   = bool
    enable_usage_monitoring = bool
    security_policies = object({
      require_mfa           = bool
      allowed_key_types     = list(string)
      max_key_age_days      = number
      require_justification = bool
    })
    access_controls = object({
      enable_ip_restrictions       = bool
      allowed_ip_ranges            = list(string)
      enable_device_trust          = bool
      enable_location_restrictions = bool
      allowed_regions              = list(string)
    })
    compliance_settings = object({
      enable_data_governance     = bool
      data_classification_labels = list(string)
      retention_policy_days      = number
      enable_audit_trail         = bool
    })
  })
  default = {
    enable_key_rotation     = false
    key_rotation_schedule   = "0 2 * * 0"
    automated_key_rotation  = false
    enable_access_logging   = true
    enable_usage_monitoring = false
    security_policies = {
      require_mfa           = false
      allowed_key_types     = ["TYPE_GOOGLE_CREDENTIALS_FILE"]
      max_key_age_days      = 90
      require_justification = false
    }
    access_controls = {
      enable_ip_restrictions       = false
      allowed_ip_ranges            = []
      enable_device_trust          = false
      enable_location_restrictions = false
      allowed_regions              = []
    }
    compliance_settings = {
      enable_data_governance     = false
      data_classification_labels = []
      retention_policy_days      = 2555
      enable_audit_trail         = true
    }
  }
}

# Cross-Project Access Configuration
variable "cross_project_access" {
  description = "Cross-project access configuration"
  type = object({
    enabled = bool
    target_projects = list(object({
      project_id = string
      roles      = list(string)
      conditions = optional(object({
        title       = string
        description = string
        expression  = string
      }))
    }))
    shared_vpc_projects = list(object({
      host_project_id     = string
      service_project_ids = list(string)
      network_roles       = list(string)
    }))
    folder_access = list(object({
      folder_id           = string
      roles               = list(string)
      inherit_from_parent = bool
    }))
  })
  default = {
    enabled             = false
    target_projects     = []
    shared_vpc_projects = []
    folder_access       = []
  }
}

# Multi-Platform CI/CD Configuration
variable "cicd_platforms" {
  description = "Multi-platform CI/CD integration configuration"
  type = object({
    github_actions = object({
      enabled = bool
      repositories = list(object({
        owner               = string
        repo                = string
        ref                 = optional(string, "main")
        service_account_key = string
      }))
    })
    gitlab_ci = object({
      enabled = bool
      projects = list(object({
        project_id          = string
        ref                 = optional(string, "main")
        service_account_key = string
      }))
    })
    azure_devops = object({
      enabled = bool
      organizations = list(object({
        organization        = string
        project             = string
        service_account_key = string
      }))
    })
    jenkins = object({
      enabled = bool
      instances = list(object({
        url                 = string
        service_account_key = string
      }))
    })
  })
  default = {
    github_actions = {
      enabled      = false
      repositories = []
    }
    gitlab_ci = {
      enabled  = false
      projects = []
    }
    azure_devops = {
      enabled       = false
      organizations = []
    }
    jenkins = {
      enabled   = false
      instances = []
    }
  }
}
