# Workload Identity Federation Module

This Terraform module creates and configures GCP Workload Identity Federation for keyless authentication from various CI/CD platforms including GitHub Actions, GitLab CI, Azure DevOps, and Terraform Cloud.

## Features

- **Multi-Platform Support**: Native integration with GitHub Actions, GitLab CI, Azure DevOps, and Terraform Cloud
- **Attribute-Based Access Control**: Fine-grained security using attribute conditions
- **Service Account Management**: Create or bind existing service accounts
- **Secure by Default**: Enforces branch, repository, and organization restrictions
- **Zero Secrets**: Completely keyless authentication using OIDC tokens

## Usage

### Basic Example

```hcl
module "workload_identity" {
  source = "./modules/workload-identity"

  project_id        = "my-project-id"
  pool_id          = "ci-cd-pool"
  pool_display_name = "CI/CD Workload Identity Pool"

  providers = {
    github = {
      provider_id  = "github-actions"
      display_name = "GitHub Actions Provider"
      
      github = {
        organization = "my-org"
        repositories = ["my-repo", "another-repo"]
        branches     = ["main", "develop"]
      }
    }
  }

  service_accounts = {
    deploy = {
      service_account_id = "github-deploy-sa"
      display_name      = "GitHub Actions Deploy SA"
      project_roles     = ["roles/storage.admin", "roles/run.admin"]
      
      bindings = [{
        provider_id = "github-actions"
      }]
    }
  }
}
```

### Multi-Provider Example

```hcl
module "workload_identity" {
  source = "./modules/workload-identity"

  project_id = "my-project-id"
  pool_id    = "multi-ci-pool"

  providers = {
    github = {
      provider_id = "github"
      github = {
        organization = "my-org"
        repositories = ["frontend-app"]
        branches     = ["main"]
        environments = ["production"]
      }
    }

    gitlab = {
      provider_id = "gitlab"
      gitlab = {
        group_path   = "my-group"
        project_path = "my-group/backend-app"
        branches     = ["main", "staging"]
      }
    }

    azure = {
      provider_id = "azure-devops"
      azure_devops = {
        organization = "my-azure-org"
        project      = "my-project"
        branches     = ["main"]
      }
    }

    terraform = {
      provider_id = "terraform-cloud"
      terraform_cloud = {
        organization = "my-tf-org"
        workspace    = "production"
        run_phase    = "apply"
      }
    }
  }

  service_accounts = {
    frontend = {
      service_account_id = "frontend-deploy"
      project_roles      = ["roles/run.admin"]
      
      bindings = [{
        provider_id = "github"
      }]
    }

    backend = {
      service_account_id = "backend-deploy"
      project_roles      = ["roles/cloudsql.client"]
      
      bindings = [{
        provider_id = "gitlab"
      }]
    }

    infra = {
      service_account_id = "terraform-deploy"
      project_roles      = ["roles/editor"]
      
      bindings = [
        {
          provider_id = "azure-devops"
        },
        {
          provider_id = "terraform-cloud"
        }
      ]
    }
  }
}
```

## CI/CD Platform Configuration

### GitHub Actions

```yaml
name: Deploy to GCP
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # Required for OIDC

    steps:
      - uses: actions/checkout@v4
      
      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.WI_PROVIDER }}
          service_account: ${{ vars.SERVICE_ACCOUNT }}
      
      - name: Deploy
        run: gcloud run deploy my-service --image gcr.io/my-project/my-app
```

### GitLab CI

```yaml
deploy:
  image: google/cloud-sdk:alpine
  stage: deploy
  id_tokens:
    GCP_TOKEN:
      aud: https://gitlab.com
  script:
    - echo ${GCP_TOKEN} > .ci_job_jwt_file
    - |
      gcloud iam workload-identity-pools create-cred-config \
        ${WI_PROVIDER} \
        --service-account=${SERVICE_ACCOUNT} \
        --credential-source-file=.ci_job_jwt_file \
        --output-file=.gcp_credentials.json
    - export GOOGLE_APPLICATION_CREDENTIALS=.gcp_credentials.json
    - gcloud auth login --cred-file=.gcp_credentials.json
    - gcloud run deploy my-service --image gcr.io/my-project/my-app
  only:
    - main
```

### Azure DevOps

```yaml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: GoogleCloudSdkInstaller@0
    displayName: Install Cloud SDK

  - script: |
      # Get the Azure DevOps JWT token
      echo $SYSTEM_ACCESSTOKEN > token.txt
      
      # Create credential configuration
      gcloud iam workload-identity-pools create-cred-config \
        $(WI_PROVIDER) \
        --service-account=$(SERVICE_ACCOUNT) \
        --credential-source-file=token.txt \
        --output-file=gcp-credentials.json
      
      # Authenticate
      gcloud auth login --cred-file=gcp-credentials.json
    displayName: Authenticate with GCP
    env:
      SYSTEM_ACCESSTOKEN: $(System.AccessToken)

  - script: |
      gcloud run deploy my-service --image gcr.io/my-project/my-app
    displayName: Deploy to Cloud Run
```

### Terraform Cloud

In your Terraform Cloud workspace, set these environment variables:

```hcl
TFC_GCP_PROVIDER_AUTH           = true
TFC_GCP_WORKLOAD_IDENTITY_POOL_ID = "ci-cd-pool"
TFC_GCP_WORKLOAD_PROVIDER_ID    = "terraform-cloud"
TFC_GCP_SERVICE_ACCOUNT_EMAIL   = "terraform-deploy@my-project.iam.gserviceaccount.com"
TFC_GCP_PROJECT_NUMBER          = "123456789"
```

Then in your Terraform configuration:

```hcl
terraform {
  cloud {
    organization = "my-org"
    workspaces {
      name = "production"
    }
  }
}

provider "google" {
  project = var.project_id
  # Authentication handled automatically via workload identity
}

provider "google-beta" {
  project = var.project_id
  # Authentication handled automatically via workload identity
}
```

## Security Best Practices

### 1. Attribute Conditions

Always use attribute conditions to restrict access:

```hcl
providers = {
  github = {
    provider_id = "github"
    
    # Automatic conditions based on configuration
    github = {
      organization = "my-org"        # Only from this org
      repositories = ["production"]  # Only from specific repos
      branches     = ["main"]        # Only from protected branches
      environments = ["production"]  # Only from specific environments
    }
    
    # Or custom attribute condition
    attribute_condition = <<-EOT
      assertion.repository_owner == 'my-org' &&
      assertion.repository in ['repo1', 'repo2'] &&
      assertion.ref == 'refs/heads/main' &&
      assertion.event_name != 'pull_request'
    EOT
  }
}
```

### 2. Least Privilege Access

Grant only necessary permissions:

```hcl
service_accounts = {
  deploy = {
    service_account_id = "minimal-deploy-sa"
    
    # Only required project roles
    project_roles = [
      "roles/run.developer",     # Deploy to Cloud Run
      "roles/storage.objectUser" # Read artifacts
    ]
    
    # Bind with specific conditions
    bindings = [{
      provider_id = "github"
      attribute_condition = "attribute.environment == 'production'"
    }]
  }
}
```

### 3. Environment Separation

Use different pools or providers for different environments:

```hcl
# Production pool
module "prod_workload_identity" {
  source = "./modules/workload-identity"
  
  project_id = "prod-project"
  pool_id    = "prod-ci-pool"
  
  providers = {
    github_prod = {
      provider_id = "github-prod"
      github = {
        organization = "my-org"
        repositories = ["app"]
        branches     = ["main"]
        environments = ["production"]
      }
    }
  }
}

# Development pool
module "dev_workload_identity" {
  source = "./modules/workload-identity"
  
  project_id = "dev-project"
  pool_id    = "dev-ci-pool"
  
  providers = {
    github_dev = {
      provider_id = "github-dev"
      github = {
        organization = "my-org"
        repositories = ["app"]
        branches     = ["develop", "feature/*"]
      }
    }
  }
}
```

## Advanced Configuration

### Custom Attribute Mapping

```hcl
providers = {
  custom = {
    provider_id = "custom-provider"
    issuer_uri  = "https://my-oidc-provider.com"
    
    attribute_mapping = {
      "google.subject"      = "assertion.sub"
      "attribute.user"      = "assertion.email"
      "attribute.team"      = "assertion.team"
      "attribute.env"       = "assertion.environment"
    }
    
    attribute_condition = "assertion.team in ['platform', 'devops']"
  }
}
```

### Using Existing Service Accounts

```hcl
service_accounts = {
  existing = {
    create_new     = false
    existing_email = "existing-sa@my-project.iam.gserviceaccount.com"
    
    bindings = [{
      provider_id = "github"
    }]
  }
}
```

## Troubleshooting

### Common Issues

1. **Token Exchange Failed**
   - Verify the issuer URI matches your CI/CD platform
   - Check attribute conditions are correctly formatted
   - Ensure the OIDC token includes required claims

2. **Permission Denied**
   - Verify service account has necessary roles
   - Check workload identity binding is correct
   - Ensure attribute conditions match token claims

3. **Invalid Attribute Mapping**
   - Use `gcloud` to inspect the actual token claims
   - Verify assertion paths in attribute mapping

### Debugging Commands

```bash
# List workload identity pools
gcloud iam workload-identity-pools list --location=global

# Describe a pool
gcloud iam workload-identity-pools describe POOL_ID --location=global

# List providers in a pool
gcloud iam workload-identity-pools providers list \
  --workload-identity-pool=POOL_ID --location=global

# Check service account IAM bindings
gcloud iam service-accounts get-iam-policy SA_EMAIL
```

## Module Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| project_id | GCP project ID | string | - | yes |
| pool_id | Workload identity pool ID | string | - | yes |
| pool_display_name | Display name for the pool | string | "" | no |
| pool_description | Pool description | string | "Workload Identity Pool for CI/CD authentication" | no |
| providers | Map of identity providers | map(object) | {} | no |
| service_accounts | Map of service accounts | map(object) | {} | no |
| enable_attribute_conditions | Enable attribute-based access control | bool | true | no |
| session_duration | Token validity duration | string | "3600s" | no |
| labels | Resource labels | map(string) | {} | no |

## Module Outputs

| Name | Description |
|------|-------------|
| pool_name | Full resource name of the workload identity pool |
| pool_id | The ID of the workload identity pool |
| providers | Map of provider details |
| service_accounts | Map of service account details |
| authentication_config | Platform-specific authentication configuration |
| subject_format | Subject claim format examples for each platform |

## License

Apache 2.0

## Contributing

Contributions are welcome! Please ensure all changes include appropriate tests and documentation updates.