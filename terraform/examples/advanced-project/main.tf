/**
 * Advanced Project Setup Example
 * 
 * Creates a GCP project with additional service accounts, GitHub Actions integration,
 * and multiple APIs. Good for production setups.
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

# Advanced project setup
module "project_setup" {
  source = "../../modules/project-setup"

  project_id      = var.project_id
  project_name    = var.project_name
  billing_account = var.billing_account
  environment     = var.environment
  location        = var.region

  # More APIs for advanced use cases
  runtime_apis = [
    "compute.googleapis.com",
    "container.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "run.googleapis.com",
    "sqladmin.googleapis.com"
  ]

  budget_amount = var.budget_amount

  # Workload Identity for GitHub Actions
  workload_identity_user = var.github_repository != "" ? (
    "principalSet://iam.googleapis.com/projects/${var.workload_identity_pool_project_number}/locations/global/workloadIdentityPools/${var.workload_identity_pool_id}/attribute.repository/${var.github_repository}"
  ) : null

  # Additional service accounts for different services
  service_accounts = {
    app_service = {
      account_id   = "app-service"
      display_name = "Application Service Account"
      description  = "Service account for running the application"
      project_roles = [
        "roles/secretmanager.secretAccessor",
        "roles/cloudsql.client"
      ]
    }

    ci_cd = {
      account_id   = "ci-cd"
      display_name = "CI/CD Service Account"
      description  = "Service account for CI/CD pipeline"
      project_roles = [
        "roles/cloudbuild.builds.editor",
        "roles/run.developer",
        "roles/storage.admin"
      ]
    }
  }

  labels = {
    created_by  = "genesis"
    template    = "advanced-project"
    cost_center = var.cost_center
    team        = var.team
  }
}

# Output comprehensive information
output "project_info" {
  description = "Complete project setup information"
  value = {
    project_id         = module.project_setup.project_id
    project_number     = module.project_setup.project_number
    state_bucket       = module.project_setup.state_bucket_name
    terraform_sa_email = module.project_setup.terraform_sa_email
    service_accounts   = module.project_setup.service_account_emails
    enabled_apis       = module.project_setup.enabled_apis
  }
}