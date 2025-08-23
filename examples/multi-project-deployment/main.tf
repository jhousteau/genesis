# Example: Multi-Project Deployment
# This example shows how to deploy the bootstrap configuration to multiple projects

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  # Configure your credentials
  # credentials = file("path/to/credentials.json")
  # or use application default credentials
}

# Example 1: Simple multi-project deployment
module "simple_multi_project" {
  source = "../../modules/multi-project"

  deployment_name = "simple-deployment"
  project_group   = "example-projects"

  # Set organization or folder
  org_id = var.organization_id # or use folder_id

  # Default settings for all projects
  default_region = "us-central1"
  default_labels = {
    managed_by  = "terraform"
    environment = "development"
    team        = "platform"
  }

  # List of projects to create
  projects = [
    {
      project_id      = "${var.project_prefix}-dev-app1"
      billing_account = var.billing_account
      environment     = "development"
      budget_amount   = 500
    },
    {
      project_id      = "${var.project_prefix}-dev-app2"
      billing_account = var.billing_account
      environment     = "development"
      budget_amount   = 500
    },
    {
      project_id      = "${var.project_prefix}-staging"
      billing_account = var.billing_account
      environment     = "staging"
      budget_amount   = 1000
    }
  ]
}

# Example 2: Complex multi-project with different configurations
module "complex_multi_project" {
  source = "../../modules/multi-project"

  deployment_name = "production-infrastructure"
  project_group   = "production-apps"
  org_id          = var.organization_id

  # Configure default Workload Identity Federation
  default_wif_providers = {
    github = {
      provider_id   = "github-actions"
      provider_type = "github"
      github = {
        organization = var.github_organization
      }
    }
  }

  projects = [
    # Frontend application project
    {
      project_id      = "${var.project_prefix}-frontend"
      billing_account = var.billing_account
      environment     = "production"
      budget_amount   = 2000

      labels = {
        application = "frontend"
        tier        = "web"
      }

      activate_apis = [
        "firebase.googleapis.com",
        "firebasehosting.googleapis.com",
        "firebasestorage.googleapis.com",
        "identitytoolkit.googleapis.com",
      ]

      custom_service_accounts = {
        frontend = {
          account_id   = "frontend-app"
          display_name = "Frontend Application"
          project_roles = [
            "roles/firebase.admin",
            "roles/storage.objectViewer",
          ]
        }
      }

      # Frontend-specific WIF configuration
      workload_identity_providers = {
        github = {
          provider_id   = "github-actions"
          provider_type = "github"
          github = {
            organization = var.github_organization
            repositories = ["frontend-app"]
            branches     = ["main"]
            environments = ["production"]
          }
        }
      }

      create_network = true
      network_name   = "frontend-vpc"
      subnets = [{
        name   = "frontend-subnet"
        cidr   = "10.1.0.0/24"
        region = "us-central1"
      }]
    },

    # Backend API project
    {
      project_id      = "${var.project_prefix}-backend"
      billing_account = var.billing_account
      environment     = "production"
      budget_amount   = 3000

      labels = {
        application = "backend"
        tier        = "api"
      }

      activate_apis = [
        "run.googleapis.com",
        "cloudsql.googleapis.com",
        "redis.googleapis.com",
        "secretmanager.googleapis.com",
        "cloudtasks.googleapis.com",
      ]

      custom_service_accounts = {
        api = {
          account_id   = "backend-api"
          display_name = "Backend API Service"
          project_roles = [
            "roles/run.invoker",
            "roles/cloudsql.client",
            "roles/secretmanager.secretAccessor",
          ]
        }
        worker = {
          account_id   = "backend-worker"
          display_name = "Backend Worker Service"
          project_roles = [
            "roles/cloudtasks.enqueuer",
            "roles/pubsub.publisher",
          ]
        }
      }

      workload_identity_providers = {
        github = {
          provider_id   = "github-actions"
          provider_type = "github"
          github = {
            organization = var.github_organization
            repositories = ["backend-api", "backend-services"]
            branches     = ["main", "release/*"]
            environments = ["production"]
          }
        }
      }

      create_network   = true
      network_name     = "backend-vpc"
      enable_flow_logs = true
      subnets = [
        {
          name   = "backend-subnet-us"
          cidr   = "10.2.0.0/24"
          region = "us-central1"
        },
        {
          name   = "backend-subnet-eu"
          cidr   = "10.3.0.0/24"
          region = "europe-west1"
        }
      ]
    },

    # Data analytics project
    {
      project_id      = "${var.project_prefix}-analytics"
      billing_account = var.billing_account
      environment     = "production"
      budget_amount   = 5000

      labels = {
        application = "analytics"
        tier        = "data"
      }

      activate_apis = [
        "bigquery.googleapis.com",
        "dataflow.googleapis.com",
        "composer.googleapis.com",
        "datacatalog.googleapis.com",
        "dataplex.googleapis.com",
      ]

      # Analytics needs more permissions
      terraform_sa_roles = [
        "roles/bigquery.admin",
        "roles/dataflow.admin",
        "roles/composer.admin",
        "roles/storage.admin",
      ]

      custom_service_accounts = {
        etl = {
          account_id   = "etl-pipeline"
          display_name = "ETL Pipeline"
          project_roles = [
            "roles/bigquery.dataEditor",
            "roles/dataflow.worker",
            "roles/storage.objectAdmin",
          ]
        }
        analytics = {
          account_id   = "analytics-reader"
          display_name = "Analytics Reader"
          project_roles = [
            "roles/bigquery.dataViewer",
            "roles/datacatalog.viewer",
          ]
        }
      }

      # Different state bucket settings for analytics
      state_bucket_location = "us" # Multi-region for analytics
      storage_class         = "STANDARD"
      lifecycle_rules = [
        {
          action = {
            type          = "SetStorageClass"
            storage_class = "NEARLINE"
          }
          condition = {
            age = "90"
          }
        },
        {
          action = {
            type          = "SetStorageClass"
            storage_class = "COLDLINE"
          }
          condition = {
            age = "365"
          }
        }
      ]
    },

    # Shared services project
    {
      project_id      = "${var.project_prefix}-shared"
      billing_account = var.billing_account
      environment     = "production"
      budget_amount   = 1500

      labels = {
        application = "shared"
        tier        = "infrastructure"
      }

      activate_apis = [
        "artifactregistry.googleapis.com",
        "containerscanning.googleapis.com",
        "binaryauthorization.googleapis.com",
        "certificatemanager.googleapis.com",
        "dns.googleapis.com",
      ]

      custom_service_accounts = {
        registry = {
          account_id   = "artifact-registry"
          display_name = "Artifact Registry Manager"
          project_roles = [
            "roles/artifactregistry.admin",
            "roles/containerscanning.viewer",
          ]
        }
      }

      # Shared services accessible from all repos
      workload_identity_providers = {
        github = {
          provider_id   = "github-actions"
          provider_type = "github"
          github = {
            organization = var.github_organization
            # All repositories can access shared services
            repositories = ["*"]
            branches     = ["main", "develop", "release/*"]
          }
        }
      }
    }
  ]

  # Enable all features
  create_state_buckets     = true
  create_service_accounts  = true
  enable_workload_identity = true

  # Deployment settings
  parallel_deployments     = true
  error_on_partial_failure = false
}

# Example 3: Loading projects from external data source
locals {
  # Load project list from JSON file
  project_data = jsondecode(file("${path.module}/projects.json"))

  # Transform to required format
  projects_from_json = [for p in local.project_data.projects : {
    project_id      = p.id
    billing_account = p.billing
    environment     = p.env
    budget_amount   = p.budget
    labels          = p.labels
    activate_apis   = try(p.apis, var.default_apis)
    create_network  = try(p.needs_network, false)
  }]
}

module "json_based_deployment" {
  source = "../../modules/multi-project"

  deployment_name = "json-deployment"
  project_group   = local.project_data.group
  org_id          = local.project_data.organization

  projects = local.projects_from_json
}

# Example 4: Environment-based deployment
module "environment_deployment" {
  source = "../../modules/multi-project"

  deployment_name = "environment-based"
  project_group   = "all-environments"
  org_id          = var.organization_id

  projects = concat(
    # Development projects
    [for i in range(var.dev_project_count) : {
      project_id      = "${var.project_prefix}-dev-${i + 1}"
      billing_account = var.billing_account
      environment     = "development"
      budget_amount   = 500
      labels = {
        environment = "dev"
        auto_delete = "true"
      }
    }],

    # Staging projects
    [for i in range(var.staging_project_count) : {
      project_id      = "${var.project_prefix}-staging-${i + 1}"
      billing_account = var.billing_account
      environment     = "staging"
      budget_amount   = 1000
      labels = {
        environment = "staging"
      }
    }],

    # Production projects
    [for i in range(var.prod_project_count) : {
      project_id      = "${var.project_prefix}-prod-${i + 1}"
      billing_account = var.billing_account
      environment     = "production"
      budget_amount   = 2000
      labels = {
        environment = "prod"
        critical    = "true"
      }
      # Production gets enhanced monitoring
      activate_apis = concat(
        var.default_apis,
        [
          "monitoring.googleapis.com",
          "logging.googleapis.com",
          "cloudtrace.googleapis.com",
          "cloudprofiler.googleapis.com",
        ]
      )
    }]
  )
}
