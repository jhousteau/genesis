variable "project_id" {
  description = "The GCP project ID to create"
  type        = string
}

variable "project_name" {
  description = "Human-readable name for the project"
  type        = string
  default     = ""
}

variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
  default     = ""
}

variable "folder_id" {
  description = "GCP Folder ID"
  type        = string
  default     = ""
}

variable "billing_account" {
  description = "Billing account ID"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "development"
}

variable "location" {
  description = "Default location/region for resources"
  type        = string
  default     = "US"
}

variable "auto_create_network" {
  description = "Create default network automatically"
  type        = bool
  default     = false
}

variable "additional_apis" {
  description = "Additional APIs to enable during bootstrap"
  type        = list(string)
  default     = []
}

variable "runtime_apis" {
  description = "APIs to enable after project setup (e.g., compute, container)"
  type        = list(string)
  default     = []
}

variable "state_bucket_name" {
  description = "Name for the Terraform state bucket (defaults to PROJECT_ID-terraform-state)"
  type        = string
  default     = ""
}

variable "budget_amount" {
  description = "Monthly budget amount in USD"
  type        = number
  default     = 100
}

variable "workload_identity_user" {
  description = "Workload Identity user for GitHub Actions"
  type        = string
  default     = null
}

variable "service_accounts" {
  description = "Additional service accounts to create"
  type = map(object({
    account_id    = string
    display_name  = string
    description   = string
    project_roles = optional(list(string), [])
    create_key    = optional(bool, false)
    impersonators = optional(list(string), [])
  }))
  default = {}
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}