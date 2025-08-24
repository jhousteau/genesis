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
  description = "The billing account ID to associate with the bootstrap project"
  type        = string
}

variable "folder_id" {
  description = "The folder ID where the bootstrap project will be created (optional)"
  type        = string
  default     = ""
}

# Project Configuration
variable "project_id" {
  description = "The GCP project ID for bootstrap resources"
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Project ID must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "project_name" {
  description = "The human-readable name for the bootstrap project"
  type        = string
  default     = ""
}

# Region Configuration
variable "region" {
  description = "The default GCP region for resources"
  type        = string
  default     = "us-central1"
}

# State Backend Configuration
variable "state_bucket_name" {
  description = "Name for the GCS bucket to store Terraform state (will be auto-generated if not provided)"
  type        = string
  default     = ""
}

variable "state_bucket_location" {
  description = "Location for the state bucket (US, EU, ASIA, or specific region)"
  type        = string
  default     = "US"
}

variable "enable_state_encryption" {
  description = "Enable KMS encryption for Terraform state"
  type        = bool
  default     = true
}

# Service Account Configuration
variable "terraform_sa_name" {
  description = "Name for the Terraform service account"
  type        = string
  default     = "terraform-automation"
}

variable "create_sa_key" {
  description = "Create a service account key for local development (not recommended for production)"
  type        = bool
  default     = false
}

variable "grant_org_admin" {
  description = "Grant Organization Admin role to Terraform SA (required for org-level operations)"
  type        = bool
  default     = false
}

# Workload Identity Configuration
variable "enable_workload_identity" {
  description = "Enable Workload Identity Federation for GitHub Actions"
  type        = bool
  default     = false
}

variable "github_org" {
  description = "GitHub organization name for Workload Identity"
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository name for Workload Identity (leave empty for org-wide access)"
  type        = string
  default     = ""
}

# Network Configuration
variable "create_bootstrap_network" {
  description = "Create a VPC network for bootstrap resources"
  type        = bool
  default     = false
}

variable "bootstrap_subnet_cidr" {
  description = "CIDR range for the bootstrap subnet"
  type        = string
  default     = "10.0.0.0/24"
}

# API Configuration
variable "activate_apis" {
  description = "Additional APIs to activate for the bootstrap project"
  type        = list(string)
  default     = []
}

# Labels
variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    managed-by = "terraform"
    purpose    = "bootstrap"
  }
}
