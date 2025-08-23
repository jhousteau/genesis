# GCP State Backend Module

This Terraform module creates and configures a Google Cloud Storage (GCS) bucket optimized for storing Terraform state files with enterprise-grade security, reliability, and compliance features.

## Features

- **State Management**: Purpose-built for Terraform state storage with versioning and lifecycle management
- **Security**: CMEK encryption, uniform bucket-level access, and public access prevention
- **Reliability**: Cross-region replication, soft delete protection, and retention policies
- **Compliance**: Access logging, audit trails, and retention policy locks
- **Cost Optimization**: Autoclass support, lifecycle transitions, and storage class management
- **2025 Best Practices**: Implements latest GCP storage features including soft delete and Autoclass

## Usage

### Basic Usage

```hcl
module "state_backend" {
  source = "./modules/state-backend"

  project_id  = "my-project-id"
  bucket_name = "my-terraform-state-bucket"
  location    = "us-central1"
}
```

### Advanced Usage with All Features

```hcl
module "state_backend" {
  source = "./modules/state-backend"

  project_id                         = "my-project-id"
  bucket_name                        = "my-terraform-state-bucket"
  location                           = "us-central1"
  storage_class                      = "STANDARD"
  enable_versioning                  = true
  versioning_retain_days             = 30
  enable_uniform_bucket_level_access = true
  enable_public_access_prevention    = true

  # CMEK Encryption
  encryption_key_name = "projects/my-project/locations/us-central1/keyRings/terraform/cryptoKeys/state-key"

  # Retention Policy
  retention_policy = {
    retention_period = 2592000  # 30 days in seconds
    is_locked        = false
  }

  # Access Logging
  logging_config = {
    log_bucket        = "my-audit-logs-bucket"
    log_object_prefix = "terraform-state-access/"
  }

  # Autoclass for automatic storage optimization
  enable_autoclass                  = true
  autoclass_terminal_storage_class = "NEARLINE"

  # Cross-region replication
  replication_configuration = {
    role               = "roles/storage.admin"
    destination_bucket = "my-terraform-state-replica"
    destination_project = "my-backup-project"
    rewrite_destination = true
    delete_marker_status = false
  }

  # Soft delete policy (2025 feature)
  soft_delete_policy = {
    retention_duration_seconds = 604800  # 7 days
  }

  # Custom lifecycle rules
  lifecycle_rules = [
    {
      action = {
        type          = "SetStorageClass"
        storage_class = "NEARLINE"
      }
      condition = {
        age = 30
        matches_prefix = ["archive/"]
      }
    }
  ]

  labels = {
    environment = "production"
    team        = "platform"
    cost-center = "engineering"
  }
}
```

### Multi-Region Configuration

```hcl
module "state_backend" {
  source = "./modules/state-backend"

  project_id    = "my-project-id"
  bucket_name   = "my-global-terraform-state"
  location      = "us"  # Multi-region
  storage_class = "STANDARD"

  # Custom dual-region placement
  custom_placement_config = {
    data_locations = ["us-central1", "us-east1"]
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_id | The GCP project ID where the state bucket will be created | `string` | n/a | yes |
| bucket_name | The name of the GCS bucket for Terraform state storage | `string` | n/a | yes |
| location | The location for the GCS bucket (region or multi-region) | `string` | `"us-central1"` | no |
| storage_class | The storage class of the GCS bucket | `string` | `"STANDARD"` | no |
| force_destroy | Allow Terraform to destroy the bucket even if it contains objects | `bool` | `false` | no |
| enable_versioning | Enable versioning for the state bucket | `bool` | `true` | no |
| versioning_retain_days | Number of days to retain non-current versions | `number` | `30` | no |
| lifecycle_rules | List of lifecycle rules to configure for the bucket | `list(object)` | `[]` | no |
| retention_policy | Retention policy configuration for the bucket | `object` | `null` | no |
| encryption_key_name | The Cloud KMS key name for CMEK encryption | `string` | `null` | no |
| enable_uniform_bucket_level_access | Enable uniform bucket-level access | `bool` | `true` | no |
| enable_public_access_prevention | Prevents public access to the bucket | `bool` | `true` | no |
| labels | Labels to apply to the bucket | `map(string)` | See variables.tf | no |
| cors | CORS configuration for the bucket | `list(object)` | `[]` | no |
| logging_config | Access logging configuration for the bucket | `object` | `null` | no |
| enable_autoclass | Enable Autoclass for automatic storage class management | `bool` | `false` | no |
| autoclass_terminal_storage_class | Terminal storage class for Autoclass-enabled buckets | `string` | `"NEARLINE"` | no |
| replication_configuration | Cross-region replication configuration | `object` | `null` | no |
| soft_delete_policy | Soft delete policy configuration | `object` | `{retention_duration_seconds = 604800}` | no |
| custom_placement_config | Custom dual-region configuration for the bucket | `object` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| bucket_name | The name of the created GCS bucket |
| bucket_url | The URL of the created GCS bucket |
| bucket_self_link | The URI of the created GCS bucket |
| bucket_id | The ID of the created GCS bucket |
| bucket_location | The location of the created GCS bucket |
| bucket_storage_class | The storage class of the created GCS bucket |
| versioning_enabled | Whether versioning is enabled on the bucket |
| encryption_key | The KMS key used for bucket encryption (if configured) |
| uniform_bucket_level_access | Whether uniform bucket-level access is enabled |
| public_access_prevention | The public access prevention status |
| lifecycle_rules | The lifecycle rules configured for the bucket |
| retention_policy | The retention policy configured for the bucket |
| logging_config | The logging configuration for the bucket |
| log_bucket_name | The name of the logging bucket (if created) |
| autoclass_enabled | Whether Autoclass is enabled |
| soft_delete_policy | The soft delete policy configuration |
| replication_bucket_name | The name of the replication destination bucket |
| replication_bucket_url | The URL of the replication destination bucket |
| replication_job_name | The name of the replication transfer job |
| terraform_backend_config | Terraform backend configuration block |
| labels | The labels applied to the bucket |

## Backend Configuration

After creating the state bucket, configure your Terraform backend:

```hcl
terraform {
  backend "gcs" {
    bucket = "my-terraform-state-bucket"
    prefix = "terraform/state"
  }
}
```

Or use the output directly:

```hcl
# In your root module after applying this module
terraform {
  backend "gcs" {
    bucket = module.state_backend.bucket_name
    prefix = "terraform/state"
  }
}
```

## Security Considerations

1. **Encryption**: Always use CMEK for sensitive environments
2. **Access Control**: Use uniform bucket-level access and service accounts
3. **Logging**: Enable access logging for audit trails
4. **Retention**: Configure retention policies to prevent accidental deletion
5. **Replication**: Set up cross-region replication for disaster recovery
6. **Soft Delete**: Use soft delete policy for additional protection against accidental deletion

## Cost Optimization

1. **Autoclass**: Enable for automatic storage class transitions
2. **Lifecycle Rules**: Configure rules to move old versions to cheaper storage
3. **Storage Class**: Choose appropriate storage class based on access patterns
4. **Retention**: Balance retention needs with storage costs

## Migration from Existing State

To migrate existing state to this bucket:

```bash
# 1. Initialize with existing backend
terraform init

# 2. Pull current state
terraform state pull > terraform.tfstate.backup

# 3. Update backend configuration to new bucket
# Edit your terraform backend configuration

# 4. Reinitialize with new backend
terraform init -migrate-state

# 5. Verify state
terraform state list
```

## Disaster Recovery

For disaster recovery scenarios:

1. **Primary Failure**: Use replication bucket as failover
2. **Soft Delete Recovery**: Restore within retention window
3. **Version Recovery**: Restore previous versions if versioning enabled
4. **Backup Strategy**: Regular exports to alternate storage

## Compliance and Governance

- **Retention Locks**: Use locked retention policies for compliance
- **Access Logging**: Maintain audit trails for all bucket access
- **Labels**: Apply consistent labeling for cost tracking and governance
- **IAM**: Implement least-privilege access controls

## Troubleshooting

### Common Issues

1. **Bucket Name Already Exists**: Bucket names must be globally unique
2. **Insufficient Permissions**: Ensure service account has storage.admin role
3. **KMS Key Access**: Verify KMS key permissions for CMEK
4. **Replication Failures**: Check network connectivity and IAM permissions

### Debug Commands

```bash
# Check bucket configuration
gsutil ls -L -b gs://my-terraform-state-bucket

# View bucket IAM policy
gsutil iam get gs://my-terraform-state-bucket

# Check versioning status
gsutil versioning get gs://my-terraform-state-bucket

# List lifecycle rules
gsutil lifecycle get gs://my-terraform-state-bucket
```

## Requirements

- Terraform >= 1.5.0
- Google Provider >= 5.0.0
- GCP Project with Cloud Storage API enabled
- Appropriate IAM permissions (storage.admin or equivalent)

## License

This module is maintained as part of the GCP Bootstrap Deployer project.
