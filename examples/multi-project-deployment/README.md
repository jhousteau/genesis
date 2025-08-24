# Multi-Project Deployment Examples

This directory contains comprehensive examples of deploying the bootstrap configuration to multiple GCP projects simultaneously.

## Quick Start

1. **Copy and configure the variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

2. **Initialize Terraform:**
   ```bash
   terraform init
   ```

3. **Review the deployment plan:**
   ```bash
   terraform plan
   ```

4. **Deploy to multiple projects:**
   ```bash
   terraform apply
   ```

## Examples Included

### 1. Simple Multi-Project Deployment
Basic deployment of 3 projects with minimal configuration:
- 2 development projects
- 1 staging project
- Shared configuration across all projects

### 2. Complex Multi-Project Deployment
Production-ready deployment with different configurations per project:
- **Frontend Project**: Firebase, CDN, web hosting
- **Backend Project**: Cloud Run, Cloud SQL, Redis
- **Analytics Project**: BigQuery, Dataflow, Composer
- **Shared Services**: Artifact Registry, DNS, certificates

Each project has:
- Custom service accounts
- Specific API enablement
- Workload Identity Federation
- Optional networking
- Environment-specific settings

### 3. JSON-Based Deployment
Load project configurations from an external JSON file:
- Useful for managing large project lists
- Easy integration with other systems
- Version control friendly

### 4. Environment-Based Deployment
Dynamically create projects based on environment counts:
- Configurable number of dev/staging/prod projects
- Automatic labeling and budgeting
- Environment-specific configurations

## File Structure

```
multi-project-deployment/
├── main.tf                    # Main configuration with 4 examples
├── variables.tf               # Input variables
├── outputs.tf                 # Output definitions
├── terraform.tfvars.example   # Example variable values
├── projects.json              # Sample JSON project list
└── README.md                  # This file
```

## Configuration Options

### Required Variables
- `organization_id`: Your GCP organization ID
- `billing_account`: Billing account for projects

### Optional Variables
- `project_prefix`: Prefix for project IDs (default: "bootstrap")
- `github_organization`: GitHub org for Workload Identity
- `dev_project_count`: Number of dev projects (for environment example)
- `staging_project_count`: Number of staging projects
- `prod_project_count`: Number of production projects

## Using the JSON File

The `projects.json` file demonstrates loading projects from external data:

```json
{
  "group": "example-projects",
  "organization": "123456789",
  "projects": [
    {
      "id": "project-id",
      "billing": "billing-account",
      "env": "development",
      "budget": 1000,
      "labels": {...},
      "apis": [...],
      "needs_network": true
    }
  ]
}
```

## Customization Guide

### Adding a New Project

1. **To Simple Deployment:**
   ```hcl
   projects = [
     # ... existing projects ...
     {
       project_id      = "new-project"
       billing_account = var.billing_account
       environment     = "development"
       budget_amount   = 750
     }
   ]
   ```

2. **To Complex Deployment:**
   ```hcl
   projects = [
     # ... existing projects ...
     {
       project_id      = "custom-project"
       billing_account = var.billing_account

       # Custom APIs
       activate_apis = ["specific.googleapis.com"]

       # Custom service accounts
       custom_service_accounts = {
         my_sa = {
           account_id = "my-service-account"
           display_name = "My Service Account"
           project_roles = ["roles/viewer"]
         }
       }

       # Enable networking
       create_network = true
       subnets = [{
         name = "my-subnet"
         cidr = "10.4.0.0/24"
         region = "us-central1"
       }]
     }
   ]
   ```

### Modifying Global Defaults

Edit the module parameters:

```hcl
module "deployment" {
  source = "../../modules/multi-project"

  # Change default region
  default_region = "europe-west1"

  # Add default labels
  default_labels = {
    team        = "platform"
    cost_center = "engineering"
    managed_by  = "terraform"
  }

  # Modify default APIs
  default_apis = [
    "compute.googleapis.com",
    "storage.googleapis.com",
    # Add more...
  ]

  # Configure WIF defaults
  default_wif_providers = {
    github = {
      provider_id = "github"
      provider_type = "github"
      github = {
        organization = "my-org"
      }
    }
  }
}
```

## Deployment Strategies

### Sequential Deployment
For large numbers of projects or quota limitations:

```hcl
module "deployment" {
  source = "../../modules/multi-project"

  parallel_deployments = false  # Deploy one at a time
  projects = var.projects
}
```

### Fail-Fast Strategy
Stop on first error:

```hcl
module "deployment" {
  source = "../../modules/multi-project"

  error_on_partial_failure = true
  projects = var.projects
}
```

### Dry Run
Test without applying:

```hcl
module "deployment" {
  source = "../../modules/multi-project"

  dry_run = true
  projects = var.projects
}
```

## Outputs

The examples provide comprehensive outputs:

- `simple_projects`: List of project IDs from simple deployment
- `complex_service_accounts`: All service accounts created
- `complex_workload_identity`: WIF configuration details
- `environment_projects_by_env`: Projects grouped by environment
- `generated_project_configs`: Ready-to-use tfvars for each project

## Best Practices

1. **Start Small**: Test with 1-2 projects before scaling
2. **Use JSON/CSV**: For managing large project lists
3. **Environment Separation**: Different tfvars per environment
4. **Monitor Quotas**: Watch API and project quotas
5. **Incremental Rollout**: Deploy in batches for safety

## Troubleshooting

### Common Issues

1. **Quota Exceeded**
   - Reduce parallel deployments
   - Request quota increases
   - Deploy in smaller batches

2. **Permission Denied**
   - Verify organization/folder admin permissions
   - Check billing account permissions
   - Ensure API enablement permissions

3. **Billing Errors**
   - Verify billing account is active
   - Check billing quota
   - Ensure billing linkage permissions

### Debug Commands

```bash
# Enable debug logging
export TF_LOG=DEBUG

# Plan specific modules
terraform plan -target=module.simple_multi_project

# Apply to specific projects
terraform apply -target='module.complex_multi_project.module.bootstrap["frontend"]'

# Destroy specific deployments
terraform destroy -target=module.simple_multi_project
```

## Next Steps

After deployment:

1. **Verify Projects**: Check GCP Console for created projects
2. **Configure CI/CD**: Use the WIF outputs for pipeline setup
3. **Deploy Applications**: Use generated tfvars for app deployment
4. **Set Up Monitoring**: Configure alerts and dashboards
5. **Review Security**: Audit IAM roles and permissions

## Support

For issues or questions:
1. Check the module documentation in `/modules/multi-project/README.md`
2. Review validation warnings in Terraform output
3. Enable debug logging for detailed information
4. Consult GCP documentation for specific service configuration
