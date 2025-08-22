# Bootstrap Environment

This is the bootstrap environment that sets up the foundational GCP infrastructure for managing all other environments.

## Purpose

The bootstrap environment creates:
- GCP Project for centralized management
- Terraform state storage bucket
- Service accounts for automation
- Workload Identity for GitHub Actions (optional)
- KMS keys for state encryption (optional)
- Base network infrastructure (optional)

## Prerequisites

1. GCP Organization ID
2. Billing Account ID
3. Permissions to create projects and assign billing
4. `gcloud` CLI installed and authenticated
5. Terraform >= 1.5

## Initial Setup

### 1. Authenticate with GCP

```bash
gcloud auth application-default login
gcloud config set project YOUR_EXISTING_PROJECT
```

### 2. Configure Variables

Copy the example variables file and update with your values:

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your organization details
```

### 3. Initialize Terraform

For the first run, initialize without a backend:

```bash
terraform init
```

### 4. Plan and Apply

Review the planned changes:

```bash
terraform plan
```

Apply the bootstrap configuration:

```bash
terraform apply
```

### 5. Configure Backend

After the initial apply, configure the backend:

1. Note the `state_bucket_name` from the output
2. Copy `backend.tf.example` to `backend.tf`
3. Update the bucket name in `backend.tf`
4. Re-initialize with the backend:

```bash
terraform init -migrate-state
```

## Configuration Options

### Required Variables

| Variable | Description |
|----------|-------------|
| `org_id` | Your GCP organization ID |
| `billing_account` | Billing account to associate with the project |
| `project_id` | Unique project ID for bootstrap resources |

### Optional Features

#### Workload Identity Federation

Enable GitHub Actions integration:

```hcl
enable_workload_identity = true
github_org = "your-org"
github_repo = "your-repo"  # Optional, for repo-specific access
```

#### State Encryption

Enable KMS encryption for Terraform state:

```hcl
enable_state_encryption = true
```

#### Bootstrap Network

Create a VPC network for bootstrap resources:

```hcl
create_bootstrap_network = true
bootstrap_subnet_cidr = "10.0.0.0/24"
```

## Outputs

After successful deployment, you'll get:

- `project_id`: The bootstrap project ID
- `state_bucket_name`: Terraform state bucket name
- `terraform_service_account_email`: Service account for Terraform
- `backend_config`: Backend configuration for other environments

## Using Bootstrap for Other Environments

After bootstrap is complete, other environments can use the created resources:

### Backend Configuration

In other environment's `backend.tf`:

```hcl
terraform {
  backend "gcs" {
    bucket = "YOUR_STATE_BUCKET_NAME"
    prefix = "dev/terraform/state"  # Change per environment
  }
}
```

### Service Account Authentication

For local development:

```bash
gcloud auth activate-service-account --key-file=PATH_TO_KEY
```

For CI/CD with Workload Identity:

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v1
  with:
    workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
    service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
```

## Security Best Practices

1. **Service Account Keys**: Avoid creating keys (`create_sa_key = false`)
2. **Workload Identity**: Use for GitHub Actions instead of keys
3. **State Encryption**: Always enable in production
4. **IAM Roles**: Grant minimum necessary permissions
5. **Network Security**: Use private IPs and Cloud NAT

## Troubleshooting

### Permission Denied

Ensure your user has these roles:
- `roles/resourcemanager.projectCreator`
- `roles/billing.admin` or `roles/billing.user`

### State Lock Issues

If state is locked:

```bash
terraform force-unlock LOCK_ID
```

### API Not Enabled

The bootstrap automatically enables required APIs. If you encounter API errors, wait a few minutes for propagation.

## Maintenance

### Updating Bootstrap

1. Always backup state before changes
2. Review plan carefully
3. Consider impact on dependent environments
4. Update in maintenance window

### Rotating Service Account Keys

If using service account keys:

```bash
# Create new key
gcloud iam service-accounts keys create NEW_KEY.json \
  --iam-account=terraform-automation@PROJECT_ID.iam.gserviceaccount.com

# Update systems using the key
# Delete old key
gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=terraform-automation@PROJECT_ID.iam.gserviceaccount.com
```

## Next Steps

After bootstrap is complete:

1. Deploy the development environment
2. Deploy the production environment
3. Set up CI/CD pipelines
4. Configure monitoring and alerting
5. Document operational procedures