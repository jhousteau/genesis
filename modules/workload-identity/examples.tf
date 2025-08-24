/**
 * Example configurations for common Workload Identity Federation use cases
 * These examples demonstrate best practices for 2025 keyless authentication
 */

# Example 1: GitHub Actions for a single repository
module "github_single_repo" {
  source = "../workload-identity"

  project_id        = "my-gcp-project"
  pool_id           = "github-pool"
  pool_display_name = "GitHub Actions WIF Pool"

  providers = {
    github = {
      provider_id  = "github-actions"
      display_name = "GitHub Actions"

      github = {
        organization = "my-org"
        repositories = ["my-app"]
        branches     = ["main", "release/*"]
        environments = ["production", "staging"]
      }
    }
  }

  service_accounts = {
    deploy = {
      service_account_id = "github-deploy"
      display_name       = "GitHub Deploy Service Account"

      project_roles = [
        "roles/run.admin",
        "roles/storage.objectAdmin",
        "roles/artifactregistry.writer"
      ]

      bindings = [{
        provider_id = "github-actions"
        # Additional condition: only from production environment
        attribute_condition = "attribute.environment == 'production'"
      }]
    }
  }
}

# Example 2: GitLab CI with group-level access
module "gitlab_group_access" {
  source = "../workload-identity"

  project_id = "my-gcp-project"
  pool_id    = "gitlab-pool"

  providers = {
    gitlab = {
      provider_id = "gitlab-ci"

      gitlab = {
        group_path = "my-company"
        # Allow all projects in the group
        branches = ["main", "master"]
        # Only from protected environments
        environments = ["production", "staging"]
      }
    }
  }

  service_accounts = {
    ci_runner = {
      service_account_id = "gitlab-ci-runner"

      project_roles = [
        "roles/cloudbuild.builds.editor",
        "roles/container.developer"
      ]

      bindings = [{
        provider_id = "gitlab-ci"
        # Ensure it's from a protected branch
        attribute_condition = "attribute.ref_protected == 'true'"
      }]
    }
  }
}

# Example 3: Multi-environment setup with different permissions
module "multi_environment" {
  source = "../workload-identity"

  project_id = "my-gcp-project"
  pool_id    = "multi-env-pool"

  providers = {
    github_prod = {
      provider_id = "github-prod"

      github = {
        organization = "my-org"
        repositories = ["app-frontend", "app-backend"]
        branches     = ["main"]
        environments = ["production"]
      }
    }

    github_dev = {
      provider_id = "github-dev"

      github = {
        organization = "my-org"
        repositories = ["app-frontend", "app-backend"]
        branches     = ["develop", "feature/*"]
        environments = ["development", "testing"]
      }
    }
  }

  service_accounts = {
    prod_deploy = {
      service_account_id = "prod-deploy"
      display_name       = "Production Deployment"

      project_roles = [
        "roles/run.admin",
        "roles/compute.loadBalancerAdmin"
      ]

      bindings = [{
        provider_id = "github-prod"
      }]
    }

    dev_deploy = {
      service_account_id = "dev-deploy"
      display_name       = "Development Deployment"

      project_roles = [
        "roles/run.developer",
        "roles/storage.objectUser"
      ]

      bindings = [{
        provider_id = "github-dev"
      }]
    }
  }
}

# Example 4: Terraform Cloud for infrastructure management
module "terraform_cloud" {
  source = "../workload-identity"

  project_id = "my-infrastructure-project"
  pool_id    = "terraform-pool"

  providers = {
    tfc_prod = {
      provider_id = "terraform-cloud-prod"

      terraform_cloud = {
        organization = "my-company"
        project      = "infrastructure"
        workspace    = "production"
        run_phase    = "apply" # Only during apply phase
      }
    }

    tfc_plan = {
      provider_id = "terraform-cloud-plan"

      terraform_cloud = {
        organization = "my-company"
        project      = "infrastructure"
        # All workspaces can plan
        run_phase = "plan"
      }
    }
  }

  service_accounts = {
    terraform_apply = {
      service_account_id = "terraform-apply"

      project_roles = [
        "roles/editor", # Full editor for infrastructure changes
        "roles/iam.securityAdmin"
      ]

      bindings = [{
        provider_id = "terraform-cloud-prod"
      }]
    }

    terraform_plan = {
      service_account_id = "terraform-plan"

      project_roles = [
        "roles/viewer", # Read-only for planning
        "roles/iam.roleViewer"
      ]

      bindings = [{
        provider_id = "terraform-cloud-plan"
      }]
    }
  }
}

# Example 5: Azure DevOps with organization-wide access
module "azure_devops" {
  source = "../workload-identity"

  project_id = "my-gcp-project"
  pool_id    = "azure-devops-pool"

  providers = {
    azure = {
      provider_id = "azure-devops"
      issuer_uri  = "https://vstoken.dev.azure.com/my-azure-org"

      azure_devops = {
        organization = "my-azure-org"
        project      = "CloudMigration"
        branches     = ["main", "release/*"]
      }
    }
  }

  service_accounts = {
    azure_deploy = {
      service_account_id = "azure-devops-deploy"

      project_roles = [
        "roles/compute.admin",
        "roles/container.clusterAdmin"
      ]

      bindings = [{
        provider_id = "azure-devops"
      }]
    }
  }
}

# Example 6: Complete CI/CD setup with multiple platforms
module "complete_cicd" {
  source = "../workload-identity"

  project_id = "company-platform"
  pool_id    = "unified-cicd-pool"

  providers = {
    # GitHub for application deployments
    github = {
      provider_id = "github"

      github = {
        organization = "company-org"
        repositories = ["web-app", "mobile-api", "admin-portal"]
        branches     = ["main", "hotfix/*"]
      }
    }

    # GitLab for data pipelines
    gitlab = {
      provider_id = "gitlab"

      gitlab = {
        group_path = "company/data-team"
        branches   = ["main"]
      }
    }

    # Terraform Cloud for infrastructure
    terraform = {
      provider_id = "terraform"

      terraform_cloud = {
        organization = "company"
        project      = "cloud-infrastructure"
        run_phase    = "apply"
      }
    }
  }

  service_accounts = {
    app_deploy = {
      service_account_id = "app-deployer"

      project_roles = [
        "roles/run.admin",
        "roles/redis.editor",
        "roles/cloudsql.client"
      ]

      bindings = [{
        provider_id = "github"
      }]
    }

    data_pipeline = {
      service_account_id = "data-pipeline"

      project_roles = [
        "roles/dataflow.admin",
        "roles/bigquery.dataEditor",
        "roles/pubsub.editor"
      ]

      bindings = [{
        provider_id = "gitlab"
      }]
    }

    infra_automation = {
      service_account_id = "infrastructure"

      project_roles = [
        "roles/resourcemanager.projectIamAdmin",
        "roles/compute.admin",
        "roles/container.admin"
      ]

      bindings = [{
        provider_id = "terraform"
      }]
    }
  }

  labels = {
    environment = "production"
    managed_by  = "terraform"
    cost_center = "platform-team"
  }
}

# Example 7: Granular repository-specific permissions
module "repo_specific_permissions" {
  source = "../workload-identity"

  project_id = "my-gcp-project"
  pool_id    = "repo-specific-pool"

  providers = {
    frontend = {
      provider_id = "github-frontend"

      github = {
        organization = "my-org"
        repositories = ["frontend-app"]
        branches     = ["main"]
      }
    }

    backend = {
      provider_id = "github-backend"

      github = {
        organization = "my-org"
        repositories = ["backend-api"]
        branches     = ["main"]
      }
    }

    database = {
      provider_id = "github-database"

      github = {
        organization = "my-org"
        repositories = ["database-migrations"]
        branches     = ["main"]
      }
    }
  }

  service_accounts = {
    frontend_sa = {
      service_account_id = "frontend-deploy"

      project_roles = [
        "roles/run.developer",
        "roles/firebase.admin"
      ]

      bindings = [{
        provider_id = "github-frontend"
      }]
    }

    backend_sa = {
      service_account_id = "backend-deploy"

      project_roles = [
        "roles/run.admin",
        "roles/cloudsql.client",
        "roles/secretmanager.secretAccessor"
      ]

      bindings = [{
        provider_id = "github-backend"
      }]
    }

    database_sa = {
      service_account_id = "database-migrate"

      project_roles = [
        "roles/cloudsql.admin"
      ]

      bindings = [{
        provider_id = "github-database"
      }]
    }
  }
}

# Example 8: Custom OIDC provider integration
module "custom_oidc" {
  source = "../workload-identity"

  project_id = "my-gcp-project"
  pool_id    = "custom-oidc-pool"

  providers = {
    jenkins = {
      provider_id       = "jenkins-ci"
      issuer_uri        = "https://jenkins.company.com"
      allowed_audiences = ["https://jenkins.company.com/oidc"]

      attribute_mapping = {
        "google.subject"         = "assertion.sub"
        "attribute.job_name"     = "assertion.job"
        "attribute.build_number" = "assertion.build_id"
        "attribute.branch"       = "assertion.branch"
        "attribute.user"         = "assertion.user_email"
      }

      # Custom condition for Jenkins
      attribute_condition = <<-EOT
        assertion.job in ['deploy-prod', 'deploy-staging'] &&
        assertion.branch == 'main'
      EOT
    }
  }

  service_accounts = {
    jenkins_deploy = {
      service_account_id = "jenkins-deploy"

      project_roles = [
        "roles/compute.instanceAdmin",
        "roles/iam.serviceAccountUser"
      ]

      bindings = [{
        provider_id = "jenkins-ci"
      }]
    }
  }
}
