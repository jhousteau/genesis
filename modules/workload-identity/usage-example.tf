/**
 * Complete usage example demonstrating Workload Identity Federation
 * for a production-ready multi-environment setup
 */

# Configure the providers
terraform {
  required_version = ">= 1.6"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0"
    }
  }
}

# Variables for the example
variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "billing_account" {
  description = "GCP Billing Account ID"
  type        = string
}

variable "github_org" {
  description = "GitHub organization name"
  type        = string
}

variable "gitlab_group" {
  description = "GitLab group path"
  type        = string
}

# Create projects for different environments
resource "google_project" "production" {
  name            = "Production Environment"
  project_id      = "prod-${random_id.project_suffix.hex}"
  org_id          = var.organization_id
  billing_account = var.billing_account
}

resource "google_project" "staging" {
  name            = "Staging Environment"
  project_id      = "staging-${random_id.project_suffix.hex}"
  org_id          = var.organization_id
  billing_account = var.billing_account
}

resource "google_project" "development" {
  name            = "Development Environment"
  project_id      = "dev-${random_id.project_suffix.hex}"
  org_id          = var.organization_id
  billing_account = var.billing_account
}

resource "random_id" "project_suffix" {
  byte_length = 4
}

# Enable required APIs
locals {
  required_apis = [
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "sts.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
  ]
}

resource "google_project_service" "production_apis" {
  for_each = toset(local.required_apis)
  
  project = google_project.production.project_id
  service = each.value
}

resource "google_project_service" "staging_apis" {
  for_each = toset(local.required_apis)
  
  project = google_project.staging.project_id
  service = each.value
}

resource "google_project_service" "development_apis" {
  for_each = toset(local.required_apis)
  
  project = google_project.development.project_id
  service = each.value
}

# Production Workload Identity Configuration
module "production_workload_identity" {
  source = "./modules/workload-identity"
  
  project_id        = google_project.production.project_id
  pool_id          = "production-cicd"
  pool_display_name = "Production CI/CD Pool"
  pool_description  = "Workload Identity Federation for production deployments"
  
  providers = {
    # GitHub Actions for production deployments
    github_prod = {
      provider_id  = "github-prod"
      display_name = "GitHub Actions Production"
      
      github = {
        organization = var.github_org
        repositories = ["backend-api", "frontend-app", "mobile-app"]
        branches     = ["main"]
        environments = ["production"]
      }
    }
    
    # GitLab for data pipeline deployments
    gitlab_prod = {
      provider_id  = "gitlab-prod"
      display_name = "GitLab CI Production"
      
      gitlab = {
        group_path = var.gitlab_group
        branches   = ["main"]
      }
    }
    
    # Terraform Cloud for infrastructure
    terraform_prod = {
      provider_id  = "terraform-prod"
      display_name = "Terraform Cloud Production"
      
      terraform_cloud = {
        organization = var.github_org
        workspace    = "production"
        run_phase    = "apply"
      }
    }
  }
  
  service_accounts = {
    # Application deployment service account
    app_deploy = {
      service_account_id = "prod-app-deploy"
      display_name      = "Production App Deployment"
      description       = "Deploys applications to production environment"
      
      project_roles = [
        "roles/run.admin",
        "roles/compute.loadBalancerAdmin",
        "roles/monitoring.metricWriter",
        "roles/cloudtrace.agent",
        "roles/errorreporting.writer",
      ]
      
      bindings = [{
        provider_id = "github-prod"
      }]
    }
    
    # Data pipeline service account
    data_pipeline = {
      service_account_id = "prod-data-pipeline"
      display_name      = "Production Data Pipeline"
      
      project_roles = [
        "roles/dataflow.admin",
        "roles/bigquery.admin",
        "roles/pubsub.admin",
        "roles/storage.admin",
      ]
      
      bindings = [{
        provider_id = "gitlab-prod"
      }]
    }
    
    # Infrastructure management service account
    infrastructure = {
      service_account_id = "prod-infrastructure"
      display_name      = "Production Infrastructure"
      
      project_roles = [
        "roles/compute.admin",
        "roles/container.admin",
        "roles/iam.securityAdmin",
        "roles/resourcemanager.projectIamAdmin",
      ]
      
      bindings = [{
        provider_id = "terraform-prod"
      }]
    }
  }
  
  labels = {
    environment = "production"
    managed_by  = "terraform"
    team        = "platform"
  }
  
  depends_on = [google_project_service.production_apis]
}

# Staging Workload Identity Configuration
module "staging_workload_identity" {
  source = "./modules/workload-identity"
  
  project_id        = google_project.staging.project_id
  pool_id          = "staging-cicd"
  pool_display_name = "Staging CI/CD Pool"
  
  providers = {
    github_staging = {
      provider_id = "github-staging"
      
      github = {
        organization = var.github_org
        repositories = ["backend-api", "frontend-app", "mobile-app"]
        branches     = ["staging", "release/*"]
        environments = ["staging"]
      }
    }
    
    gitlab_staging = {
      provider_id = "gitlab-staging"
      
      gitlab = {
        group_path = var.gitlab_group
        branches   = ["staging", "develop"]
      }
    }
  }
  
  service_accounts = {
    staging_deploy = {
      service_account_id = "staging-deploy"
      display_name      = "Staging Deployment"
      
      project_roles = [
        "roles/run.admin",
        "roles/storage.admin",
        "roles/cloudsql.client",
      ]
      
      bindings = [
        {
          provider_id = "github-staging"
        },
        {
          provider_id = "gitlab-staging"
        }
      ]
    }
  }
  
  labels = {
    environment = "staging"
    managed_by  = "terraform"
  }
  
  depends_on = [google_project_service.staging_apis]
}

# Development Workload Identity Configuration
module "development_workload_identity" {
  source = "./modules/workload-identity"
  
  project_id = google_project.development.project_id
  pool_id    = "dev-cicd"
  
  providers = {
    github_dev = {
      provider_id = "github-dev"
      
      github = {
        organization = var.github_org
        # Allow all repos for development
        branches = ["develop", "feature/*", "bugfix/*"]
      }
    }
  }
  
  service_accounts = {
    dev_deploy = {
      service_account_id = "dev-deploy"
      
      project_roles = [
        "roles/run.developer",
        "roles/storage.objectAdmin",
        "roles/cloudfunctions.developer",
        "roles/logging.viewer",
      ]
      
      bindings = [{
        provider_id = "github-dev"
        # More relaxed conditions for development
        attribute_condition = "assertion.repository_owner == '${var.github_org}'"
      }]
    }
  }
  
  enable_attribute_conditions = true
  session_duration           = "1800s"  # 30 minutes for dev
  
  labels = {
    environment = "development"
    managed_by  = "terraform"
  }
  
  depends_on = [google_project_service.development_apis]
}

# Create artifact registry for container images
resource "google_artifact_registry_repository" "images" {
  for_each = {
    production  = google_project.production.project_id
    staging     = google_project.staging.project_id
    development = google_project.development.project_id
  }
  
  project       = each.value
  location      = "us-central1"
  repository_id = "container-images"
  format        = "DOCKER"
  
  cleanup_policies {
    id     = "keep-recent-versions"
    action = "KEEP"
    
    most_recent_versions {
      keep_count = 10
    }
  }
}

# Outputs for CI/CD configuration
output "github_actions_config" {
  description = "GitHub Actions configuration"
  value = {
    production = {
      workload_identity_provider = module.production_workload_identity.authentication_config["github_prod"].github_actions.workload_identity_provider
      service_account           = module.production_workload_identity.service_accounts["app_deploy"].email
      artifact_registry         = "${google_artifact_registry_repository.images["production"].location}-docker.pkg.dev/${google_project.production.project_id}/${google_artifact_registry_repository.images["production"].repository_id}"
    }
    staging = {
      workload_identity_provider = module.staging_workload_identity.authentication_config["github_staging"].github_actions.workload_identity_provider
      service_account           = module.staging_workload_identity.service_accounts["staging_deploy"].email
      artifact_registry         = "${google_artifact_registry_repository.images["staging"].location}-docker.pkg.dev/${google_project.staging.project_id}/${google_artifact_registry_repository.images["staging"].repository_id}"
    }
    development = {
      workload_identity_provider = module.development_workload_identity.authentication_config["github_dev"].github_actions.workload_identity_provider
      service_account           = module.development_workload_identity.service_accounts["dev_deploy"].email
      artifact_registry         = "${google_artifact_registry_repository.images["development"].location}-docker.pkg.dev/${google_project.development.project_id}/${google_artifact_registry_repository.images["development"].repository_id}"
    }
  }
  sensitive = true
}

output "gitlab_ci_config" {
  description = "GitLab CI configuration"
  value = {
    production = {
      workload_identity_provider = module.production_workload_identity.authentication_config["gitlab_prod"].gitlab_ci.workload_identity_provider
      service_account           = module.production_workload_identity.service_accounts["data_pipeline"].email
    }
    staging = {
      workload_identity_provider = module.staging_workload_identity.authentication_config["gitlab_staging"].gitlab_ci.workload_identity_provider
      service_account           = module.staging_workload_identity.service_accounts["staging_deploy"].email
    }
  }
  sensitive = true
}

output "terraform_cloud_config" {
  description = "Terraform Cloud environment variables"
  value       = module.production_workload_identity.authentication_config["terraform_prod"].terraform_cloud.env_variables
  sensitive   = true
}