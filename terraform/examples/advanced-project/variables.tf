variable "project_id" {
  description = "GCP project ID to create"
  type        = string
}

variable "project_name" {
  description = "Human-readable project name"
  type        = string
}

variable "billing_account" {
  description = "Billing account ID"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "region" {
  description = "Default GCP region"
  type        = string
  default     = "us-central1"
}

variable "budget_amount" {
  description = "Monthly budget in USD"
  type        = number
  default     = 500
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "engineering"
}

variable "team" {
  description = "Team responsible for this project"
  type        = string
  default     = "platform"
}

variable "github_repository" {
  description = "GitHub repository for Workload Identity (format: org/repo)"
  type        = string
  default     = ""
}

variable "workload_identity_pool_id" {
  description = "Workload Identity Pool ID"
  type        = string
  default     = "github-pool"
}

variable "workload_identity_pool_project_number" {
  description = "Project number where Workload Identity Pool is created"
  type        = string
  default     = ""
}
