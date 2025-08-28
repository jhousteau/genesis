# Terraform Modules

Infrastructure as Code modules for complete GCP deployments.

## Available Modules

| Module | Purpose | Resources |
|--------|---------|-----------|
| `bootstrap` | Project setup and initial configuration | Project, billing, APIs |
| `project-setup` | Core project infrastructure | IAM, service accounts |
| `state-backend` | Terraform state storage | Cloud Storage, IAM |
| `service-accounts` | Service account management | Service accounts, keys, IAM |

## Usage

### Basic Project Setup

```hcl
module "bootstrap" {
  source = "./terraform/modules/bootstrap"
  
  project_id = "my-project-id"
  region     = "us-central1"
}

module "project_setup" {
  source = "./terraform/modules/project-setup"
  
  project_id = module.bootstrap.project_id
  region     = var.region
}
```

### With State Backend

```hcl
module "state_backend" {
  source = "./terraform/modules/state-backend"
  
  project_id = "my-project-id"
  region     = "us-central1"
  bucket_name = "my-project-terraform-state"
}
```

## Examples

See `terraform/examples/` for complete deployment examples:
- `basic-project/` - Simple project setup
- `advanced-project/` - Full infrastructure with networking

## Testing

```bash
# Validate all modules
cd terraform
terraform init
terraform validate

# Run integration tests
make terraform-test
```