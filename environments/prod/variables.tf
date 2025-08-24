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
  description = "The GCP organization ID"
  type        = string
}

variable "billing_account" {
  description = "The billing account ID to associate with the project"
  type        = string
}

variable "folder_id" {
  description = "The folder ID where the project will be created (optional)"
  type        = string
  default     = ""
}

# Project Configuration
variable "create_project" {
  description = "Whether to create a new project or use existing"
  type        = bool
  default     = true
}

variable "project_id" {
  description = "The GCP project ID for production environment"
  type        = string
}

variable "project_name" {
  description = "The human-readable name for the project"
  type        = string
  default     = ""
}

variable "project_prefix" {
  description = "Prefix for auto-generated resource names"
  type        = string
  default     = "my-app"
}

# Region Configuration
variable "primary_region" {
  description = "The primary GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "dr_region" {
  description = "The disaster recovery region"
  type        = string
  default     = "us-east1"
}

variable "enable_dr" {
  description = "Enable disaster recovery configuration"
  type        = bool
  default     = true
}

# Network Configuration
variable "network_name" {
  description = "Base name for the VPC network"
  type        = string
  default     = "main"
}

variable "primary_subnet_ranges" {
  description = "CIDR ranges for primary region subnets"
  type        = map(string)
  default = {
    main       = "10.10.0.0/24"
    serverless = "10.10.1.0/24"
    pods       = "10.11.0.0/16"
    services   = "10.12.0.0/16"
  }
}

variable "dr_subnet_ranges" {
  description = "CIDR ranges for DR region subnets"
  type        = map(string)
  default = {
    main       = "10.20.0.0/24"
    serverless = "10.20.1.0/24"
    pods       = "10.21.0.0/16"
    services   = "10.22.0.0/16"
  }
}

# Storage Configuration
variable "storage_location" {
  description = "Location for multi-region storage (US, EU, ASIA)"
  type        = string
  default     = "US"
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 90
}

# Artifact Registry Configuration
variable "artifact_registry_name" {
  description = "Base name for Artifact Registry repositories"
  type        = string
  default     = "containers"
}

# Firestore Configuration
variable "enable_firestore" {
  description = "Enable Firestore database"
  type        = bool
  default     = true
}

variable "firestore_location" {
  description = "Location for Firestore database"
  type        = string
  default     = "nam5" # US multi-region
}

# Cloud SQL Configuration
variable "enable_cloud_sql" {
  description = "Enable Cloud SQL instance"
  type        = bool
  default     = false
}

variable "cloud_sql_version" {
  description = "Cloud SQL database version"
  type        = string
  default     = "POSTGRES_15"
}

variable "cloud_sql_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-g1-small"
}

# Monitoring Configuration
variable "enable_monitoring_workspace" {
  description = "Create a monitoring workspace"
  type        = bool
  default     = true
}

# Budget Configuration
variable "budget_amount" {
  description = "Monthly budget amount in USD"
  type        = number
  default     = 1000
}

variable "notification_channels" {
  description = "List of monitoring notification channel IDs for budget alerts"
  type        = list(string)
  default     = []
}

# API Configuration
variable "activate_apis" {
  description = "Additional APIs to activate for the project"
  type        = list(string)
  default     = []
}

# Labels
variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    environment = "prod"
    managed-by  = "terraform"
  }
}
