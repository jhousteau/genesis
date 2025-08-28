variable "project_id" {
  description = "GCP project ID to create"
  type        = string
}

variable "project_name" {
  description = "Human-readable project name"
  type        = string
  default     = ""
}

variable "billing_account" {
  description = "Billing account ID"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "Default GCP region"
  type        = string
  default     = "us-central1"
}

variable "budget_amount" {
  description = "Monthly budget in USD"
  type        = number
  default     = 100
}