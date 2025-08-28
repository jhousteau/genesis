/**
 * Basic Project Setup Example
 * 
 * Creates a GCP project with Terraform state backend and minimal configuration.
 * Perfect for getting started quickly.
 */

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  region = var.region
}

# Complete project setup with defaults
module "project_setup" {
  source = "../../modules/project-setup"

  project_id      = var.project_id
  project_name    = var.project_name
  billing_account = var.billing_account
  environment     = var.environment
  location        = var.region

  # Enable commonly needed APIs
  runtime_apis = [
    "compute.googleapis.com",
    "container.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com"
  ]

  budget_amount = var.budget_amount

  labels = {
    created_by = "genesis"
    template   = "basic-project"
  }
}

# Output important information
output "project_info" {
  description = "Key project information"
  value = {
    project_id         = module.project_setup.project_id
    state_bucket       = module.project_setup.state_bucket_name
    terraform_sa_email = module.project_setup.terraform_sa_email
  }
}