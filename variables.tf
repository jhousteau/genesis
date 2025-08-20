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

# Core Project Configuration
variable "org_id" {
  description = "The GCP organization ID"
  type        = string
}

variable "billing_account" {
  description = "The billing account ID to associate with projects"
  type        = string
}

variable "project_id" {
  description = "The GCP project ID for the bootstrap resources"
  type        = string
}

variable "project_name" {
  description = "The human-readable name for the project"
  type        = string
  default     = ""
}

variable "folder_id" {
  description = "The folder ID where the project will be created (optional)"
  type        = string
  default     = ""
}

# Environment Configuration
variable "environment" {
  description = "Environment name (e.g., bootstrap, dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["bootstrap", "dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: bootstrap, dev, staging, prod"
  }
}

variable "region" {
  description = "The default GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The default GCP zone for resources"
  type        = string
  default     = "us-central1-a"
}

# State Backend Configuration
variable "state_bucket_name" {
  description = "Name for the GCS bucket to store Terraform state"
  type        = string
  default     = ""
}

variable "state_bucket_location" {
  description = "Location for the state bucket"
  type        = string
  default     = "US"
}

# Service Configuration
variable "activate_apis" {
  description = "List of APIs to activate for the project"
  type        = list(string)
  default = [
    "cloudresourcemanager.googleapis.com",
    "cloudbilling.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
    "serviceusage.googleapis.com",
    "cloudkms.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com"
  ]
}

# IAM Configuration
variable "project_owners" {
  description = "List of users/groups/serviceAccounts to grant Owner role"
  type        = list(string)
  default     = []
}

variable "project_editors" {
  description = "List of users/groups/serviceAccounts to grant Editor role"
  type        = list(string)
  default     = []
}

variable "project_viewers" {
  description = "List of users/groups/serviceAccounts to grant Viewer role"
  type        = list(string)
  default     = []
}

# Service Account Configuration
variable "create_terraform_sa" {
  description = "Whether to create a Terraform service account"
  type        = bool
  default     = true
}

variable "terraform_sa_name" {
  description = "Name for the Terraform service account"
  type        = string
  default     = "terraform"
}

variable "terraform_sa_roles" {
  description = "Roles to grant to the Terraform service account"
  type        = list(string)
  default = [
    "roles/owner"
  ]
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
  description = "GitHub repository name for Workload Identity"
  type        = string
  default     = ""
}

# Network Configuration
variable "create_network" {
  description = "Whether to create a custom VPC network"
  type        = bool
  default     = false
}

variable "network_name" {
  description = "Name for the VPC network"
  type        = string
  default     = "main"
}

variable "subnet_cidr" {
  description = "CIDR range for the main subnet"
  type        = string
  default     = "10.0.0.0/24"
}

# Labels
variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    managed-by = "terraform"
  }
}

# KMS Configuration
variable "enable_kms" {
  description = "Whether to create KMS resources for encryption"
  type        = bool
  default     = false
}

variable "kms_keyring_name" {
  description = "Name for the KMS keyring"
  type        = string
  default     = "terraform-keyring"
}

variable "kms_crypto_key_name" {
  description = "Name for the KMS crypto key"
  type        = string
  default     = "terraform-state-key"
}