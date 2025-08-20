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
    "secretmanager.googleapis.com"
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