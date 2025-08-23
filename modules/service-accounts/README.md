# Service Accounts Module

This Terraform module creates and manages Google Cloud Platform (GCP) service accounts with customizable IAM roles, following the principle of least privilege.

## Features

- **Multiple Service Account Creation**: Create and manage multiple service accounts with different permission sets
- **Flexible IAM Bindings**: Support for project, organization, and folder-level role assignments
- **Service Account Impersonation**: Configure which identities can impersonate service accounts
- **Key Management**: Optional key creation with Secret Manager integration
- **Predefined Role Sets**: Common role configurations for typical use cases
- **Security Best Practices**: Implements least privilege and secure key storage

## Usage

### Basic Example

```hcl
module "service_accounts" {
  source = "./modules/service-accounts"

  project_id = "my-project-id"

  service_accounts = {
    terraform = {
      account_id   = "terraform-deployer"
      display_name = "Terraform Deployer"
      description  = "Service account for Terraform deployments"
      project_roles = [
        "roles/resourcemanager.projectIamAdmin",
        "roles/storage.admin",
        "roles/compute.admin"
      ]
    }

    cicd = {
      account_id   = "cicd-pipeline"
      display_name = "CI/CD Pipeline"
      description  = "Service account for CI/CD operations"
      project_roles = [
        "roles/cloudbuild.builds.editor",
        "roles/run.admin"
      ]
      create_key = true
    }
  }
}
```

### Advanced Example with Impersonation

```hcl
module "service_accounts" {
  source = "./modules/service-accounts"

  project_id      = "my-project-id"
  organization_id = "123456789"

  service_accounts = {
    terraform = {
      account_id   = "terraform-deployer"
      display_name = "Terraform Deployer"
      description  = "Service account for Terraform deployments"

      # Project-level roles
      project_roles = [
        "roles/resourcemanager.projectIamAdmin",
        "roles/storage.admin"
      ]

      # Organization-level roles
      organization_roles = [
        "roles/resourcemanager.organizationViewer",
        "roles/billing.viewer"
      ]

      # Folder-level roles
      folder_roles = {
        "folders/123456" = ["roles/resourcemanager.folderAdmin"]
        "folders/789012" = ["roles/compute.admin", "roles/storage.admin"]
      }

      # Allow impersonation
      impersonators = [
        "user:admin@example.com",
        "group:platform-team@example.com"
      ]
    }

    monitoring = {
      account_id   = "monitoring-agent"
      display_name = "Monitoring Agent"
      description  = "Service account for monitoring and observability"
      project_roles = [
        "roles/monitoring.metricWriter",
        "roles/logging.logWriter",
        "roles/cloudtrace.agent"
      ]
    }

    application = {
      account_id   = "app-runtime"
      display_name = "Application Runtime"
      description  = "Service account for application runtime"
      project_id   = "my-app-project"  # Different project
      project_roles = [
        "roles/storage.objectViewer",
        "roles/secretmanager.secretAccessor",
        "roles/cloudsql.client"
      ]
      create_key           = true
      key_secret_accessors = ["serviceAccount:deployer@my-project.iam.gserviceaccount.com"]
    }
  }

  store_keys_in_secret_manager = true

  labels = {
    environment = "production"
    managed_by  = "terraform"
    team        = "platform"
  }
}
```

### Using Predefined Role Sets

```hcl
module "service_accounts" {
  source = "./modules/service-accounts"

  project_id = "my-project-id"

  service_accounts = {
    terraform = {
      account_id    = "terraform-deployer"
      display_name  = "Terraform Deployer"
      project_roles = var.predefined_roles.terraform_deployer
    }

    cicd = {
      account_id    = "cicd-pipeline"
      display_name  = "CI/CD Pipeline"
      project_roles = var.predefined_roles.cicd_pipeline
    }

    monitoring = {
      account_id    = "monitoring-agent"
      display_name  = "Monitoring Agent"
      project_roles = var.predefined_roles.monitoring
    }
  }

  predefined_roles = {
    terraform_deployer = [
      "roles/resourcemanager.projectIamAdmin",
      "roles/storage.admin",
      "roles/compute.admin",
      "roles/iam.serviceAccountAdmin"
    ]
    cicd_pipeline = [
      "roles/cloudbuild.builds.editor",
      "roles/run.admin",
      "roles/artifactregistry.writer"
    ]
    monitoring = [
      "roles/monitoring.metricWriter",
      "roles/logging.logWriter"
    ]
  }
}
```

## Service Account Types

### Terraform Deployer Account

Designed for infrastructure provisioning and management:

- Project IAM administration
- Resource creation and management
- State storage access
- Secret management

### CI/CD Pipeline Account

Optimized for continuous integration and deployment:

- Build execution
- Container registry access
- Application deployment
- Artifact management

### Monitoring Account

Focused on observability and monitoring:

- Metric collection
- Log aggregation
- Trace collection
- Error reporting

### Application Runtime Account

Minimal permissions for application execution:

- Storage access (read-only)
- Secret access
- Database connections
- Message queue operations

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `project_id` | Default GCP project ID | `string` | n/a | yes |
| `organization_id` | GCP organization ID | `string` | `null` | no |
| `service_accounts` | Map of service accounts to create | `map(object)` | n/a | yes |
| `store_keys_in_secret_manager` | Store keys in Secret Manager | `bool` | `true` | no |
| `labels` | Labels for all resources | `map(string)` | `{}` | no |
| `predefined_roles` | Predefined role sets | `object` | `{}` | no |
| `enable_cross_project_impersonation` | Enable cross-project impersonation | `bool` | `false` | no |
| `impersonation_admin_members` | Admin members for impersonation | `list(string)` | `[]` | no |
| `enable_audit_logs` | Enable audit logging | `bool` | `true` | no |
| `key_rotation_days` | Key rotation period (informational) | `number` | `90` | no |

## Outputs

| Name | Description |
|------|-------------|
| `service_account_emails` | Map of service account emails |
| `service_account_ids` | Map of service account unique IDs |
| `service_account_names` | Map of service account resource names |
| `iam_members` | Map of IAM member strings |
| `service_accounts` | Complete service account details |
| `service_account_keys` | Service account keys (sensitive) |
| `key_secret_ids` | Secret Manager secret IDs |
| `project_role_bindings` | Project-level IAM bindings |
| `organization_role_bindings` | Organization-level IAM bindings |
| `folder_role_bindings` | Folder-level IAM bindings |
| `impersonation_configs` | Impersonation configurations |
| `summary` | Summary statistics |

## Security Best Practices

1. **Principle of Least Privilege**: Always assign the minimum required permissions
2. **Service Account Impersonation**: Prefer impersonation over key distribution
3. **Key Management**: Store keys in Secret Manager with restricted access
4. **Regular Rotation**: Implement key rotation policies (90 days recommended)
5. **Audit Logging**: Enable comprehensive audit logging for compliance
6. **Separate Accounts**: Use different service accounts for different purposes
7. **Project Isolation**: Consider using separate projects for sensitive workloads

## IAM Role Recommendations

### Minimal Roles by Use Case

**Terraform Deployer**:

- `roles/resourcemanager.projectIamAdmin` - Manage IAM policies
- `roles/storage.admin` - Terraform state storage
- `roles/serviceusage.serviceUsageAdmin` - Enable APIs

**CI/CD Pipeline**:

- `roles/cloudbuild.builds.editor` - Create and manage builds
- `roles/artifactregistry.writer` - Push container images
- `roles/run.developer` - Deploy to Cloud Run

**Monitoring**:

- `roles/monitoring.metricWriter` - Write metrics
- `roles/logging.logWriter` - Write logs
- `roles/cloudtrace.agent` - Send traces

**Application Runtime**:

- `roles/secretmanager.secretAccessor` - Read secrets
- `roles/cloudsql.client` - Connect to Cloud SQL
- `roles/pubsub.subscriber` - Subscribe to Pub/Sub topics

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the Terraform service account has `roles/iam.serviceAccountAdmin`
2. **Key Creation Failed**: Verify `roles/iam.serviceAccountKeyAdmin` is assigned
3. **Impersonation Not Working**: Check `roles/iam.serviceAccountTokenCreator` is granted
4. **Secret Manager Access**: Confirm Secret Manager API is enabled and proper roles assigned

### Debugging Commands

```bash
# List service accounts
gcloud iam service-accounts list --project=PROJECT_ID

# Check IAM policy for a service account
gcloud iam service-accounts get-iam-policy SA_EMAIL

# Test impersonation
gcloud auth print-access-token --impersonate-service-account=SA_EMAIL

# View service account roles
gcloud projects get-iam-policy PROJECT_ID --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:SA_EMAIL"
```

## Examples Directory Structure

For additional examples, see:

- `examples/basic/` - Simple service account creation
- `examples/multi-project/` - Cross-project service accounts
- `examples/with-impersonation/` - Impersonation setup
- `examples/cicd-setup/` - Complete CI/CD configuration

## License

Apache 2.0

## Contributing

Contributions are welcome! Please ensure:

1. Code follows Terraform best practices
2. Documentation is updated
3. Examples are provided for new features
4. Security implications are considered
