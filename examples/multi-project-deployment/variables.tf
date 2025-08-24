# Variables for Multi-Project Deployment Examples

variable "organization_id" {
  description = "The GCP organization ID"
  type        = string
}

variable "billing_account" {
  description = "The billing account ID to associate with projects"
  type        = string
}

variable "project_prefix" {
  description = "Prefix for all project IDs"
  type        = string
  default     = "bootstrap"
}

variable "github_organization" {
  description = "GitHub organization for Workload Identity Federation"
  type        = string
  default     = ""
}

variable "default_apis" {
  description = "Default APIs to enable in all projects"
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

# For environment-based deployment example
variable "dev_project_count" {
  description = "Number of development projects to create"
  type        = number
  default     = 2
}

variable "staging_project_count" {
  description = "Number of staging projects to create"
  type        = number
  default     = 1
}

variable "prod_project_count" {
  description = "Number of production projects to create"
  type        = number
  default     = 1
}
