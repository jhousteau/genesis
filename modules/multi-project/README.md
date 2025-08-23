# Multi-Project Bootstrap Module

Deploy bootstrap configuration to multiple GCP projects simultaneously with a single module call.

## Features

- **Batch Deployment**: Bootstrap multiple projects from a single configuration
- **Flexible Configuration**: Global defaults with per-project overrides
- **Complete Setup**: Projects, APIs, service accounts, state buckets, and WIF
- **Parallel Execution**: Deploy to multiple projects concurrently
- **Error Handling**: Continue on failure or stop on first error
- **Environment Support**: Group projects by environment
- **Network Creation**: Optional VPC and subnet creation per project

## Usage

### Basic Example - Multiple Projects with Same Config

```hcl
module "multi_project_bootstrap" {
  source = "./modules/multi-project"

  org_id          = "123456789"
  default_region  = "us-central1"

  projects = [
    {
      project_id      = "dev-project-1"
      billing_account = "01234-56789-ABCDEF"
    },
    {
      project_id      = "dev-project-2"
      billing_account = "01234-56789-ABCDEF"
    },
    {
      project_id      = "staging-project"
      billing_account = "01234-56789-ABCDEF"
      environment     = "staging"
    }
  ]
}
```

### Advanced Example - Different Configs per Project

```hcl
module "multi_project_bootstrap" {
  source = "./modules/multi-project"

  deployment_name = "company-infrastructure"
  project_group   = "web-applications"
  org_id          = "123456789"

  # Global defaults
  default_labels = {
    team        = "platform"
    cost_center = "engineering"
  }

  default_apis = [
    "compute.googleapis.com",
    "storage.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
  ]

  # Configure Workload Identity Federation defaults
  default_wif_providers = {
    github = {
      provider_id   = "github"
      provider_type = "github"
      github = {
        organization = "my-company"
      }
    }
  }

  projects = [
    {
      project_id      = "frontend-dev"
      billing_account = "01234-56789-ABCDEF"
      environment     = "development"
      budget_amount   = 500

      # Project-specific APIs
      activate_apis = [
        "firebase.googleapis.com",
        "firebasehosting.googleapis.com",
      ]

      # Custom service accounts
      custom_service_accounts = {
        frontend = {
          account_id   = "frontend-app"
          display_name = "Frontend Application"
          project_roles = ["roles/firebase.viewer"]
        }
      }

      # Enable networking
      create_network = true
      subnets = [{
        name   = "frontend-subnet"
        cidr   = "10.0.0.0/24"
        region = "us-central1"
      }]
    },
    {
      project_id      = "backend-dev"
      billing_account = "01234-56789-ABCDEF"
      environment     = "development"
      budget_amount   = 1000

      activate_apis = [
        "cloudsql.googleapis.com",
        "redis.googleapis.com",
      ]

      # Override WIF provider for this project
      workload_identity_providers = {
        github = {
          provider_id   = "github"
          provider_type = "github"
          github = {
            organization = "my-company"
            repositories = ["backend-api"]
            branches     = ["main", "develop"]
          }
        }
      }

      create_network = true
      enable_flow_logs = true
    },
    {
      project_id      = "data-warehouse"
      billing_account = "01234-56789-ABCDEF"
      environment     = "production"
      budget_amount   = 5000

      activate_apis = [
        "bigquery.googleapis.com",
        "dataflow.googleapis.com",
        "composer.googleapis.com",
      ]

      # Different storage class for data archival
      storage_class = "NEARLINE"

      # Custom lifecycle rules for data retention
      lifecycle_rules = [{
        action = {
          type = "Delete"
        }
        condition = {
          age = "365"
        }
      }]

      # Larger SA roles for data processing
      terraform_sa_roles = [
        "roles/bigquery.admin",
        "roles/dataflow.admin",
        "roles/composer.admin",
      ]
    }
  ]

  # Feature flags
  create_state_buckets     = true
  create_service_accounts  = true
  enable_workload_identity = true

  # Deployment options
  parallel_deployments     = true
  error_on_partial_failure = false
}
```

### Using a CSV/JSON File for Project List

```hcl
# Load projects from CSV
locals {
  csv_data = csvdecode(file("${path.module}/projects.csv"))

  projects_from_csv = [for row in local.csv_data : {
    project_id      = row.project_id
    billing_account = row.billing_account
    environment     = row.environment
    budget_amount   = tonumber(row.budget)
    region          = row.region
  }]
}

module "multi_project_bootstrap" {
  source = "./modules/multi-project"

  projects = local.projects_from_csv
}
```

### Using with Different Organizations/Folders

```hcl
module "multi_project_bootstrap" {
  source = "./modules/multi-project"

  projects = [
    {
      project_id      = "org1-project"
      billing_account = "01234-56789-ABCDEF"
      org_id          = "123456789"  # Organization 1
    },
    {
      project_id      = "org2-project"
      billing_account = "98765-43210-FEDCBA"
      org_id          = "987654321"  # Organization 2
    },
    {
      project_id      = "folder-project"
      billing_account = "01234-56789-ABCDEF"
      folder_id       = "folders/123456"  # Under a folder
    }
  ]
}
```

## Input Variables

### Required Variables

- `projects` - List of project configurations (see structure below)

### Project Configuration Structure

Each project in the list can have:

**Required:**

- `project_id` - The GCP project ID
- `billing_account` - Billing account ID

**Optional:**

- `project_name` - Display name (defaults to project_id)
- `org_id` - Organization ID (overrides global)
- `folder_id` - Folder ID (overrides global)
- `environment` - Environment name (dev/staging/prod)
- `labels` - Project-specific labels
- `region` - Default region for resources
- `activate_apis` - APIs to enable
- `budget_amount` - Budget in USD
- `create_network` - Enable VPC creation
- `subnets` - List of subnets to create
- Plus many more (see variables.tf)

### Global Configuration

- `deployment_name` - Name for this deployment set
- `project_group` - Group name for projects
- `default_region` - Default region for all projects
- `default_labels` - Labels applied to all projects
- `default_apis` - APIs to enable in all projects
- `default_budget_amount` - Default budget for projects

## Outputs

The module provides comprehensive outputs:

- `project_ids` - Map of all project IDs
- `state_buckets` - Map of state bucket names
- `terraform_service_accounts` - Service account emails
- `workload_identity_pools` - WIF pool information
- `summary` - Deployment summary with statistics
- `generated_tfvars` - Pre-generated tfvars for each project

## Advanced Features

### Parallel Deployments

Enable parallel processing for faster deployment:

```hcl
parallel_deployments = true  # Default
```

Note: May hit API quotas with very large project lists.

### Error Handling

Control behavior on failures:

```hcl
error_on_partial_failure = false  # Continue on error (default)
# or
error_on_partial_failure = true   # Stop on first error
```

### Dry Run Mode

Test configuration without applying:

```hcl
dry_run = true
```

### Environment Grouping

Projects are automatically grouped by environment in outputs:

```hcl
output "dev_projects" {
  value = module.multi_project_bootstrap.summary.projects_by_environment["development"]
}
```

## Best Practices

1. **Start Small**: Test with 1-2 projects first
2. **Use Defaults**: Define sensible defaults to reduce repetition
3. **Environment Separation**: Use different tfvars files per environment
4. **Monitor Quotas**: Watch API quotas when deploying many projects
5. **Version Control**: Store project lists in version control
6. **Incremental Rollout**: Deploy in batches for large organizations

## Troubleshooting

### Common Issues

1. **Quota Errors**: Reduce `parallel_deployments` or deploy in batches
2. **Permission Errors**: Ensure executing account has org/folder admin rights
3. **Billing Issues**: Verify billing account is active and linked
4. **API Errors**: Some APIs may need to be enabled manually first

### Debug Mode

Enable detailed logging:

```bash
export TF_LOG=DEBUG
terraform apply
```

## Migration from Single Projects

To migrate existing single-project deployments:

1. Export current state
2. Update configuration to use multi-project module
3. Import existing resources
4. Verify with `terraform plan`

## Security Considerations

- Service account keys are never created by default
- Workload Identity Federation is preferred
- Each project gets its own service accounts
- IAM roles follow least privilege principle
- State buckets are encrypted and versioned

## Cost Optimization

- Set appropriate budget alerts per project
- Use lifecycle rules for state bucket management
- Enable autoclass for automatic storage optimization
- Review and adjust quotas regularly
