variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "gcp_project_id" {
  description = "GCP Project ID (will be created if it doesn't exist)"
  type        = string
}

variable "gcp_billing_account" {
  description = "GCP Billing Account ID"
  type        = string
}

variable "gcp_organization_id" {
  description = "GCP Organization ID (optional - leave empty for personal projects)"
  type        = string
  default     = ""
}

variable "gcp_region" {
  description = "Default GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "service_accounts" {
  description = "Service accounts to create"
  type = map(object({
    account_id    = string
    display_name  = string
    description   = string
    project_roles = optional(list(string), [])
    create_key    = optional(bool, false)
    impersonators = optional(list(string), [])
  }))
  default = {
    terraform = {
      account_id   = "terraform"
      display_name = "Terraform Service Account"
      description  = "Service account for Terraform operations"
      project_roles = [
        "roles/editor",
        "roles/storage.admin"
      ]
    }
  }
}
