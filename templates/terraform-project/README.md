# Terraform Project Template

A Genesis-powered Terraform project template that provides enterprise-grade GCP infrastructure setup with minimal configuration.

## Features

- **Genesis Modules**: Uses battle-tested Genesis Terraform modules (no code duplication)
- **GCP Best Practices**: Project setup, state management, service accounts, and IAM
- **Simple Workflow**: Standard `terraform.tfvars` configuration (no complex tooling)
- **Ready-to-Use**: Makefile with common operations

## Quick Start

1. **Configure your project**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

2. **Initialize and plan**:
   ```bash
   make setup
   ```

3. **Apply changes**:
   ```bash
   make apply
   ```

## What Gets Created

This template uses Genesis modules to create:

- **GCP Project** with essential APIs enabled
- **GCS State Bucket** with versioning and encryption
- **Service Accounts** with appropriate IAM roles
- **Project-level IAM** bindings

## Configuration

Edit `terraform.tfvars`:

```hcl
# Required
project_name         = "my-awesome-project"
gcp_project_id      = "my-project-id-123" 
gcp_billing_account = "012345-678901-ABCDEF"

# Optional
gcp_organization_id = ""  # Leave empty for personal projects
gcp_region         = "us-central1"
```

## Available Commands

```bash
make help      # Show all available commands
make init      # Initialize Terraform
make plan      # Show execution plan  
make apply     # Apply changes
make destroy   # Destroy resources
make validate  # Validate configuration
make fmt       # Format code
make check     # Run validation + formatting
make clean     # Remove cache files
```

## State Management

After the first `terraform apply`:

1. Note the state bucket name from outputs
2. Uncomment and configure the backend in `main.tf`:
   ```hcl
   backend "gcs" {
     bucket = "your-project-terraform-state" 
     prefix = "terraform/state"
   }
   ```
3. Run `terraform init -migrate-state`

## Extending the Template

Add your infrastructure in `main.tf` after the Genesis modules:

```hcl
# Example: Add a VPC
resource "google_compute_network" "main" {
  name                    = "${var.project_name}-network"
  auto_create_subnetworks = false
}
```

## Genesis Integration

This template uses Genesis modules via relative paths:
- `../../terraform/modules/project-setup` - Complete project setup
- Includes: bootstrap, state-backend, service-accounts modules

No code is copied - modules are referenced locally within Genesis.

## Troubleshooting

**Permission Issues**: Ensure your account has `roles/resourcemanager.projectCreator` and `roles/billing.user`

**State Backend**: Don't configure the GCS backend until after the first apply (chicken-and-egg problem)

**Organization**: Leave `gcp_organization_id` empty for personal Google Cloud accounts