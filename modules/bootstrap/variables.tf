/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

# Organization Configuration
variable "org_id" {
  description = "GCP Organization ID"
  type        = string
  validation {
    condition     = can(regex("^[0-9]+$", var.org_id))
    error_message = "Organization ID must contain only numeric characters."
  }
}

variable "billing_account" {
  description = "The ID of the billing account to associate projects with"
  type        = string
  validation {
    condition     = can(regex("^[0-9A-F]{6}-[0-9A-F]{6}-[0-9A-F]{6}$", var.billing_account))
    error_message = "Billing account ID must be in the format XXXXXX-XXXXXX-XXXXXX."
  }
}

# Project Configuration
variable "project_prefix" {
  description = "Prefix for the project ID and name"
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,28}$", var.project_prefix))
    error_message = "Project prefix must start with a lowercase letter, contain only lowercase letters, numbers, and hyphens, and be at most 29 characters."
  }
}

variable "project_name" {
  description = "Display name for the project. If not set, defaults to project_id"
  type        = string
  default     = ""
}

variable "folder_id" {
  description = "The ID of a folder to host the project. If not set, project will be created at organization level"
  type        = string
  default     = ""
  validation {
    condition     = var.folder_id == "" || can(regex("^[0-9]+$", var.folder_id))
    error_message = "Folder ID must be empty or contain only numeric characters."
  }
}

variable "random_project_id" {
  description = "Whether to add a random suffix to the project ID"
  type        = bool
  default     = true
}

variable "random_project_id_length" {
  description = "Length of the random suffix for project ID"
  type        = number
  default     = 4
  validation {
    condition     = var.random_project_id_length >= 2 && var.random_project_id_length <= 8
    error_message = "Random project ID length must be between 2 and 8."
  }
}

# Location Configuration
variable "default_region" {
  description = "Default region for regional resources"
  type        = string
  default     = "us-central1"
  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+$", var.default_region))
    error_message = "Region must be a valid GCP region format (e.g., us-central1)."
  }
}

variable "default_zone" {
  description = "Default zone for zonal resources"
  type        = string
  default     = ""
}

# API Configuration
variable "activate_apis" {
  description = "List of APIs to enable in the project"
  type        = list(string)
  default = [
    "serviceusage.googleapis.com",
    "servicenetworking.googleapis.com",
    "compute.googleapis.com",
    "logging.googleapis.com",
    "bigquery.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbilling.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
    "cloudapis.googleapis.com",
    "iamcredentials.googleapis.com",
    "monitoring.googleapis.com",
    "securitycenter.googleapis.com",
    "cloudkms.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudasset.googleapis.com",
    "essentialcontacts.googleapis.com",
    "accesscontextmanager.googleapis.com",
    "clouddebugger.googleapis.com",
    "cloudtrace.googleapis.com",
    "cloudprofiler.googleapis.com"
  ]
}

variable "activate_api_identities" {
  description = "Map of API services to their identity configuration for service agent creation"
  type = list(object({
    api   = string
    roles = list(string)
  }))
  default = []
}

variable "disable_services_on_destroy" {
  description = "Whether to disable services when destroying the project. WARNING: Setting to true can prevent project deletion"
  type        = bool
  default     = false
}

variable "disable_dependent_services" {
  description = "Whether to disable dependent services when an API is disabled"
  type        = bool
  default     = false
}

# Resource Configuration
variable "auto_create_network" {
  description = "Whether to create the default network automatically"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Map of labels to apply to the project and resources"
  type        = map(string)
  default     = {}
  validation {
    condition = alltrue([
      for k, v in var.labels : can(regex("^[a-z][a-z0-9_-]{0,62}$", k)) && can(regex("^[a-z0-9_-]{0,63}$", v))
    ])
    error_message = "Label keys must start with lowercase letter and contain only lowercase letters, numbers, underscores, and hyphens. Values must contain only lowercase letters, numbers, underscores, and hyphens."
  }
}

variable "budget_amount" {
  description = "The amount to use for the budget in USD. Set to null to disable budget creation"
  type        = number
  default     = null
  validation {
    condition     = var.budget_amount == null || var.budget_amount > 0
    error_message = "Budget amount must be null or greater than 0."
  }
}

variable "budget_alert_percentages" {
  description = "List of percentages of budget amount to alert on"
  type        = list(number)
  default     = [0.5, 0.75, 0.9, 1.0]
  validation {
    condition     = alltrue([for p in var.budget_alert_percentages : p > 0 && p <= 1.2])
    error_message = "Budget alert percentages must be between 0 and 1.2."
  }
}

variable "budget_notification_email" {
  description = "Email address to send budget notifications to"
  type        = string
  default     = ""
  validation {
    condition     = var.budget_notification_email == "" || can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.budget_notification_email))
    error_message = "Budget notification email must be a valid email address or empty."
  }
}

# IAM Configuration
variable "grant_services_security_admin_role" {
  description = "Whether to grant service agents the Security Admin role"
  type        = bool
  default     = false
}

variable "grant_services_network_role" {
  description = "Whether to grant service agents network-related roles"
  type        = bool
  default     = false
}

# Org Policy Configuration
variable "org_policies" {
  description = "Map of organization policies to apply to the project"
  type = map(object({
    enforce = optional(bool)
    allow = optional(list(string), [])
    deny  = optional(list(string), [])
  }))
  default = {}
}

# Service Account Configuration
variable "create_default_service_account" {
  description = "Whether to create a default service account for the project"
  type        = bool
  default     = true
}

variable "default_service_account_name" {
  description = "Name for the default service account"
  type        = string
  default     = "bootstrap-sa"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.default_service_account_name))
    error_message = "Service account name must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "default_service_account_roles" {
  description = "List of roles to grant to the default service account"
  type        = list(string)
  default = [
    "roles/editor",
    "roles/resourcemanager.projectIamAdmin"
  ]
}

# Essential Services Configuration
variable "essential_contacts" {
  description = "Map of essential contacts for the project by notification category"
  type = map(object({
    email                    = string
    notification_categories = list(string)
  }))
  default = {}
  validation {
    condition = alltrue([
      for contact in var.essential_contacts : can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", contact.email))
    ])
    error_message = "Essential contact emails must be valid email addresses."
  }
}

# Monitoring Configuration
variable "enable_monitoring_alerts" {
  description = "Whether to create basic monitoring alerts for the project"
  type        = bool
  default     = false
}

variable "monitoring_notification_channels" {
  description = "List of notification channel IDs for monitoring alerts"
  type        = list(string)
  default     = []
}

# VPC-SC Configuration
variable "vpc_sc_perimeter_name" {
  description = "Name of an existing VPC Service Control perimeter to add the project to"
  type        = string
  default     = ""
}

# Audit Log Configuration
variable "audit_log_config" {
  description = "Configuration for audit logging"
  type = object({
    data_access = optional(list(object({
      log_type         = string
      exempted_members = optional(list(string), [])
    })), [])
  })
  default = {
    data_access = []
  }
}

# Advanced Budget Configuration
variable "budget_notification_channels" {
  description = "List of notification channel IDs for budget alerts"
  type        = list(string)
  default     = []
}

variable "budget_calendar_period" {
  description = "Budget calendar period (MONTH, QUARTER, YEAR, CALENDAR_YEAR, CUSTOM)"
  type        = string
  default     = "MONTH"
  validation {
    condition     = contains(["MONTH", "QUARTER", "YEAR", "CALENDAR_YEAR", "CUSTOM"], var.budget_calendar_period)
    error_message = "Budget calendar period must be one of: MONTH, QUARTER, YEAR, CALENDAR_YEAR, CUSTOM."
  }
}

variable "budget_custom_period" {
  description = "Custom budget period configuration"
  type = object({
    start_date = object({
      year  = number
      month = number
      day   = number
    })
    end_date = optional(object({
      year  = number
      month = number
      day   = number
    }))
  })
  default = null
}

variable "budget_filters" {
  description = "Budget filters for services, regions, labels, etc."
  type = object({
    services              = optional(list(string), [])
    subaccounts          = optional(list(string), [])
    regions              = optional(list(string), [])
    labels               = optional(map(list(string)), {})
    credit_types_treatment = optional(string, "INCLUDE_ALL_CREDITS")
  })
  default = {}
}

# Asset Inventory Configuration
variable "enable_asset_inventory" {
  description = "Whether to enable Cloud Asset Inventory for the project"
  type        = bool
  default     = false
}

variable "asset_inventory_feeds" {
  description = "Configuration for Cloud Asset Inventory feeds"
  type = list(object({
    name         = string
    asset_types  = optional(list(string), [])
    asset_names  = optional(list(string), [])
    content_type = optional(string, "RESOURCE")
    feed_output_config = object({
      pubsub_destination = object({
        topic = string
      })
    })
    condition = optional(object({
      expression  = string
      title       = optional(string)
      description = optional(string)
    }))
  }))
  default = []
}

# Resource Manager Tags
variable "resource_manager_tags" {
  description = "Resource Manager tags to apply to the project"
  type = map(object({
    parent      = string
    short_name  = string
    description = optional(string)
    values = optional(map(object({
      short_name  = string
      description = optional(string)
    })), {})
  }))
  default = {}
}

# Security Configuration
variable "enable_security_center" {
  description = "Whether to enable Security Command Center for the project"
  type        = bool
  default     = false
}

variable "security_center_sources" {
  description = "Security Command Center custom sources configuration"
  type = list(object({
    display_name = string
    description  = optional(string)
  }))
  default = []
}

# Advanced Monitoring Configuration
variable "enable_monitoring_workspace" {
  description = "Whether to create a Cloud Monitoring workspace"
  type        = bool
  default     = false
}

variable "monitoring_workspace_config" {
  description = "Cloud Monitoring workspace configuration"
  type = object({
    display_name = optional(string)
    description  = optional(string)
  })
  default = {}
}

# Logging Configuration
variable "logging_sinks" {
  description = "Logging sinks configuration for the project"
  type = list(object({
    name                   = string
    destination           = string
    filter                = optional(string, "")
    description           = optional(string)
    disabled              = optional(bool, false)
    unique_writer_identity = optional(bool, true)
    bigquery_options = optional(object({
      use_partitioned_tables = optional(bool, false)
    }))
    exclusions = optional(list(object({
      name        = string
      description = optional(string)
      filter      = string
      disabled    = optional(bool, false)
    })), [])
  }))
  default = []
}

# Network Security Configuration
variable "enable_private_google_access" {
  description = "Whether to enable Private Google Access for VPC-native workloads"
  type        = bool
  default     = true
}

variable "enable_private_service_connect" {
  description = "Whether to enable Private Service Connect for Google APIs"
  type        = bool
  default     = false
}

# Quotas and Limits
variable "quota_overrides" {
  description = "Service quota overrides for the project"
  type = list(object({
    service     = string
    metric      = string
    limit       = string
    value       = number
    dimensions  = optional(map(string), {})
  }))
  default = []
}

# Access Context Manager
variable "access_context_manager_policy" {
  description = "Access Context Manager policy configuration"
  type = object({
    parent = string
    title  = string
  })
  default = null
}

# Advanced IAM Configuration
variable "advanced_iam" {
  description = "Advanced IAM configuration for enterprise security"
  type = object({
    enable_iam_conditions = bool
    custom_roles = list(object({
      role_id = string
      title = string
      description = string
      permissions = list(string)
      stage = string
    }))
    conditional_bindings = list(object({
      role = string
      members = list(string)
      condition = object({
        title = string
        description = string
        expression = string
      })
    }))
    service_account_impersonation = object({
      enabled = bool
      allowed_impersonators = list(string)
      target_service_accounts = list(string)
    })
  })
  default = {
    enable_iam_conditions = false
    custom_roles = []
    conditional_bindings = []
    service_account_impersonation = {
      enabled = false
      allowed_impersonators = []
      target_service_accounts = []
    }
  }
}

# VPC Service Controls
variable "vpc_service_controls" {
  description = "VPC Service Controls configuration"
  type = object({
    perimeter_name = string
    resources      = optional(list(string), [])
    restricted_services = optional(list(string), [])
    access_levels = optional(list(string), [])
    vpc_accessible_services = optional(object({
      enable_restriction = bool
      allowed_services   = list(string)
    }))
  })
  default = null
}

# Multi-Region Configuration
variable "multi_region_config" {
  description = "Multi-region configuration for enhanced availability and disaster recovery"
  type = object({
    enabled = bool
    primary_region = string
    secondary_regions = list(string)
    replication_config = optional(object({
      storage_replication = bool
      backup_retention_days = number
      cross_region_backup = bool
    }), {
      storage_replication = true
      backup_retention_days = 30
      cross_region_backup = true
    })
  })
  default = {
    enabled = false
    primary_region = "us-central1"
    secondary_regions = ["us-east1", "us-west1"]
  }
}

# Cost Optimization Configuration
variable "cost_optimization" {
  description = "Cost optimization settings"
  type = object({
    enable_committed_use_discounts = bool
    enable_sustained_use_discounts = bool
    enable_preemptible_instances = bool
    resource_right_sizing = bool
    idle_resource_detection = bool
    cost_anomaly_detection = object({
      enabled = bool
      threshold_percentage = number
      notification_channels = list(string)
    })
    resource_quotas = map(object({
      limit = number
      metric = string
    }))
  })
  default = {
    enable_committed_use_discounts = false
    enable_sustained_use_discounts = true
    enable_preemptible_instances = false
    resource_right_sizing = true
    idle_resource_detection = true
    cost_anomaly_detection = {
      enabled = false
      threshold_percentage = 20
      notification_channels = []
    }
    resource_quotas = {}
  }
}

# Enhanced Security Configuration
variable "enhanced_security" {
  description = "Enhanced security configuration"
  type = object({
    enable_binary_authorization = bool
    enable_workload_identity = bool
    enable_shielded_vms = bool
    enable_os_login = bool
    enable_confidential_computing = bool
    vulnerability_scanning = object({
      enabled = bool
      scan_frequency = string
      notification_channels = list(string)
    })
    security_policies = list(object({
      name = string
      description = string
      rules = list(object({
        action = string
        priority = number
        match = object({
          src_ip_ranges = list(string)
          expr = optional(string)
        })
      }))
    }))
    cmek_config = object({
      enabled = bool
      key_ring_location = string
      key_rotation_period = string
      services = list(string)
    })
  })
  default = {
    enable_binary_authorization = false
    enable_workload_identity = true
    enable_shielded_vms = true
    enable_os_login = true
    enable_confidential_computing = false
    vulnerability_scanning = {
      enabled = false
      scan_frequency = "DAILY"
      notification_channels = []
    }
    security_policies = []
    cmek_config = {
      enabled = false
      key_ring_location = "global"
      key_rotation_period = "7776000s"
      services = ["storage.googleapis.com", "bigquery.googleapis.com"]
    }
  }
}

# Compliance Automation
variable "compliance_automation" {
  description = "Compliance automation configuration"
  type = object({
    enabled = bool
    frameworks = list(string)
    auto_remediation = bool
    compliance_scanning = object({
      enabled = bool
      scan_frequency = string
      remediation_config = object({
        auto_fix_low_severity = bool
        auto_fix_medium_severity = bool
        notification_channels = list(string)
      })
    })
    policy_enforcement = object({
      enforce_resource_locations = bool
      enforce_resource_naming = bool
      enforce_encryption = bool
      allowed_locations = list(string)
      naming_convention = string
    })
  })
  default = {
    enabled = false
    frameworks = ["CIS", "PCI-DSS", "SOC2"]
    auto_remediation = false
    compliance_scanning = {
      enabled = false
      scan_frequency = "DAILY"
      remediation_config = {
        auto_fix_low_severity = false
        auto_fix_medium_severity = false
        notification_channels = []
      }
    }
    policy_enforcement = {
      enforce_resource_locations = false
      enforce_resource_naming = false
      enforce_encryption = false
      allowed_locations = ["us-central1", "us-east1"]
      naming_convention = "^[a-z][a-z0-9-]*[a-z0-9]$"
    }
  }
}

# Network Security Configuration
variable "network_security" {
  description = "Advanced network security configuration"
  type = object({
    enable_private_google_access = bool
    enable_private_service_connect = bool
    enable_cloud_armor = bool
    enable_ddos_protection = bool
    firewall_rules = list(object({
      name = string
      direction = string
      priority = number
      source_ranges = list(string)
      target_tags = list(string)
      allow = list(object({
        protocol = string
        ports = list(string)
      }))
      deny = list(object({
        protocol = string
        ports = list(string)
      }))
    }))
    network_endpoints = object({
      enable_global_load_balancing = bool
      enable_regional_load_balancing = bool
      ssl_certificates = list(object({
        name = string
        domains = list(string)
        managed = bool
      }))
    })
  })
  default = {
    enable_private_google_access = true
    enable_private_service_connect = false
    enable_cloud_armor = false
    enable_ddos_protection = false
    firewall_rules = []
    network_endpoints = {
      enable_global_load_balancing = false
      enable_regional_load_balancing = false
      ssl_certificates = []
    }
  }
}

# Disaster Recovery Configuration
variable "disaster_recovery" {
  description = "Disaster recovery configuration"
  type = object({
    enabled = bool
    backup_schedule = string
    retention_policy = object({
      daily_backups = number
      weekly_backups = number
      monthly_backups = number
      yearly_backups = number
    })
    cross_region_replication = object({
      enabled = bool
      target_regions = list(string)
      replication_schedule = string
    })
    failover_config = object({
      automated_failover = bool
      failover_threshold = number
      recovery_time_objective = string
      recovery_point_objective = string
    })
  })
  default = {
    enabled = false
    backup_schedule = "0 2 * * *"
    retention_policy = {
      daily_backups = 7
      weekly_backups = 4
      monthly_backups = 12
      yearly_backups = 7
    }
    cross_region_replication = {
      enabled = false
      target_regions = []
      replication_schedule = "0 4 * * *"
    }
    failover_config = {
      automated_failover = false
      failover_threshold = 95
      recovery_time_objective = "4h"
      recovery_point_objective = "1h"
    }
  }
}

# Advanced Monitoring and Alerting
variable "advanced_monitoring" {
  description = "Advanced monitoring and alerting configuration"
  type = object({
    enabled = bool
    custom_metrics = list(object({
      name = string
      description = string
      metric_kind = string
      value_type = string
      labels = map(string)
    }))
    sli_slo_config = object({
      enabled = bool
      availability_target = number
      latency_target = number
      error_rate_target = number
    })
    alerting_policies = list(object({
      name = string
      description = string
      conditions = list(object({
        display_name = string
        filter = string
        comparison = string
        threshold_value = number
        duration = string
      }))
      notification_channels = list(string)
    }))
    log_based_metrics = list(object({
      name = string
      description = string
      filter = string
      metric_descriptor = object({
        metric_kind = string
        value_type = string
      })
    }))
  })
  default = {
    enabled = false
    custom_metrics = []
    sli_slo_config = {
      enabled = false
      availability_target = 99.9
      latency_target = 100
      error_rate_target = 1.0
    }
    alerting_policies = []
    log_based_metrics = []
  }
}