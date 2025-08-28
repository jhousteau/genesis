variable "project_id" {
  description = "The GCP project ID to create"
  type        = string
}

variable "project_name" {
  description = "Human-readable name for the project (defaults to project_id)"
  type        = string
  default     = ""
}

variable "organization_id" {
  description = "GCP Organization ID (leave empty if using folders)"
  type        = string
  default     = ""
}

variable "folder_id" {
  description = "GCP Folder ID (leave empty if using organization)"
  type        = string
  default     = ""
}

variable "billing_account" {
  description = "Billing account ID to associate with the project"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "development"
}

variable "auto_create_network" {
  description = "Create default network automatically"
  type        = bool
  default     = false
}

variable "additional_apis" {
  description = "Additional APIs to enable beyond the essentials"
  type        = list(string)
  default     = []
}

variable "create_default_service_account" {
  description = "Create a default service account for the project"
  type        = bool
  default     = false
}

variable "default_service_account_name" {
  description = "Name for the default service account"
  type        = string
  default     = "project-default"
}

variable "default_service_account_roles" {
  description = "IAM roles to assign to the default service account"
  type        = list(string)
  default     = ["roles/viewer"]
}

variable "budget_amount" {
  description = "Monthly budget amount in USD (0 = no budget)"
  type        = number
  default     = 0
}

variable "labels" {
  description = "Labels to apply to the project"
  type        = map(string)
  default     = {}
}