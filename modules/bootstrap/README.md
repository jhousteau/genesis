# GCP Bootstrap Module

## Overview

This Terraform module provides a comprehensive bootstrap solution for Google Cloud Platform projects. It handles project creation, API enablement, IAM configuration, budget alerts, and essential service setup following GCP best practices and terraform-google-modules patterns.

## Features

- **Project Management**: Create and configure GCP projects with organization/folder hierarchy
- **API Management**: Enable required Google Cloud APIs with dependency handling
- **IAM Configuration**: Set up service accounts, roles, and permissions
- **Budget Alerts**: Configure billing budgets with customizable alert thresholds
- **Security**: Implement organization policies and audit logging
- **State Management**: Optional GCS bucket for Terraform state storage
- **Monitoring**: Essential contacts and notification channels setup

## Usage

### Basic Example

```hcl
module "bootstrap" {
  source = "./modules/bootstrap"

  org_id          = "123456789012"
  billing_account = "ABCDEF-GHIJKL-MNOPQR"
  project_prefix  = "my-project"
  default_region  = "us-central1"
  
  labels = {
    team        = "platform"
    environment = "production"
  }
}
```

### Advanced Example with All Features

```hcl
module "bootstrap" {
  source = "./modules/bootstrap"

  # Organization Configuration
  org_id          = "123456789012"
  billing_account = "ABCDEF-GHIJKL-MNOPQR"
  folder_id       = "987654321098"  # Optional: place project in folder

  # Project Configuration
  project_prefix           = "platform"
  project_name            = "Platform Bootstrap Project"
  random_project_id       = true
  random_project_id_length = 4
  
  # Location Configuration
  default_region = "us-central1"
  default_zone   = "us-central1-a"
  
  # API Configuration
  activate_apis = [
    "serviceusage.googleapis.com",
    "servicenetworking.googleapis.com",
    "compute.googleapis.com",
    "logging.googleapis.com",
    "bigquery.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbilling.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
    "containerregistry.googleapis.com",
    "container.googleapis.com",
    "cloudrun.googleapis.com",
    "cloudfunctions.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "firebase.googleapis.com"
  ]
  
  # Service Identity Configuration
  activate_api_identities = [
    {
      api   = "container.googleapis.com"
      roles = ["roles/compute.networkAdmin"]
    },
    {
      api   = "cloudbuild.googleapis.com"
      roles = ["roles/storage.admin", "roles/artifactregistry.admin"]
    }
  ]
  
  # Service Account Configuration
  create_default_service_account = true
  default_service_account_name   = "bootstrap-sa"
  default_service_account_roles = [
    "roles/editor",
    "roles/resourcemanager.projectIamAdmin",
    "roles/billing.user"
  ]
  
  # Budget Configuration
  budget_amount             = 1000
  budget_alert_percentages  = [0.5, 0.75, 0.9, 1.0, 1.1]
  budget_notification_email = "billing@example.com"
  
  # Network Configuration
  auto_create_network = false
  
  # Labels
  labels = {
    environment     = "production"
    team           = "platform"
    cost_center    = "engineering"
    data_classification = "public"
  }
  
  # Organization Policies
  org_policies = {
    "compute.disableSerialPortAccess" = {
      enforce = true
    }
    "compute.requireOsLogin" = {
      enforce = true
    }
    "compute.vmExternalIpAccess" = {
      deny = ["all"]
    }
  }
  
  # Essential Contacts
  essential_contacts = {
    security = {
      email = "security@example.com"
      notification_categories = ["SECURITY", "SUSPENSION", "LEGAL"]
    }
    billing = {
      email = "billing@example.com"
      notification_categories = ["BILLING", "SUSPENSION"]
    }
  }
  
  # Audit Logging
  audit_log_config = {
    data_access = [
      {
        log_type = "DATA_READ"
        exempted_members = []
      },
      {
        log_type = "DATA_WRITE"
        exempted_members = []
      }
    ]
  }
  
  # Service Configuration
  disable_services_on_destroy = false
  disable_dependent_services = false
  grant_services_security_admin_role = true
  grant_services_network_role = true
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.5 |
| google | ~> 5.0 |
| google-beta | ~> 5.0 |
| random | ~> 3.6 |

## Providers

| Name | Version |
|------|---------|
| google | ~> 5.0 |
| google-beta | ~> 5.0 |
| random | ~> 3.6 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| org_id | GCP Organization ID | `string` | n/a | yes |
| billing_account | The ID of the billing account to associate projects with | `string` | n/a | yes |
| project_prefix | Prefix for the project ID and name | `string` | n/a | yes |
| project_name | Display name for the project | `string` | `""` | no |
| folder_id | The ID of a folder to host the project | `string` | `""` | no |
| random_project_id | Whether to add a random suffix to the project ID | `bool` | `true` | no |
| random_project_id_length | Length of the random suffix for project ID | `number` | `4` | no |
| default_region | Default region for regional resources | `string` | `"us-central1"` | no |
| default_zone | Default zone for zonal resources | `string` | `""` | no |
| activate_apis | List of APIs to enable in the project | `list(string)` | See variables.tf | no |
| activate_api_identities | Map of API services to their identity configuration | `list(object)` | `[]` | no |
| disable_services_on_destroy | Whether to disable services when destroying | `bool` | `false` | no |
| disable_dependent_services | Whether to disable dependent services | `bool` | `false` | no |
| auto_create_network | Whether to create the default network | `bool` | `false` | no |
| labels | Map of labels to apply to resources | `map(string)` | `{}` | no |
| budget_amount | Budget amount in USD | `number` | `null` | no |
| budget_alert_percentages | List of budget alert percentages | `list(number)` | `[0.5, 0.75, 0.9, 1.0]` | no |
| budget_notification_email | Email for budget notifications | `string` | `""` | no |
| create_default_service_account | Whether to create a default service account | `bool` | `true` | no |
| default_service_account_name | Name for the default service account | `string` | `"bootstrap-sa"` | no |
| default_service_account_roles | Roles for the default service account | `list(string)` | See variables.tf | no |
| org_policies | Organization policies to apply | `map(object)` | `{}` | no |
| essential_contacts | Essential contacts configuration | `map(object)` | `{}` | no |
| audit_log_config | Audit logging configuration | `object` | `{}` | no |
| grant_services_security_admin_role | Grant Security Admin role to service agents | `bool` | `false` | no |
| grant_services_network_role | Grant network roles to service agents | `bool` | `false` | no |
| monitoring_notification_channels | Notification channels for monitoring | `list(string)` | `[]` | no |
| vpc_sc_perimeter_name | VPC Service Control perimeter name | `string` | `""` | no |

## Outputs

| Name | Description |
|------|-------------|
| project_id | The ID of the created project |
| project_number | The numeric identifier of the created project |
| project_name | The display name of the created project |
| enabled_apis | List of enabled APIs in the project |
| enabled_api_identities | Map of enabled API service identities |
| service_account_email | Email of the default service account |
| service_account_id | Unique ID of the default service account |
| service_account_name | Fully qualified name of the default service account |
| service_account_key | Base64 encoded private key of the default service account |
| budget_name | The resource name of the budget |
| budget_amount | The budgeted amount in USD |
| bootstrap_bucket_name | The name of the bootstrap state bucket |
| bootstrap_bucket_url | The URL of the bootstrap state bucket |
| organization_id | The organization ID |
| billing_account | The billing account ID |
| folder_id | The folder ID (if project is in a folder) |
| default_region | The default region for resources |
| default_zone | The default zone for resources |
| labels | The labels applied to the project |
| project_iam_roles | Map of IAM roles granted on the project |
| project_services_map | Map of enabled services with their activation status |
| gcp_service_account_compute | The compute service agent service account |
| gcp_service_account_gke | The GKE service agent service account |
| gcp_service_account_cloudbuild | The Cloud Build service agent service account |
| essential_contacts | Map of configured essential contacts |
| org_policies | Map of organization policies applied to the project |
| terraform_backend_config | Terraform backend configuration for storing state in GCS |

## Default Enabled APIs

The module enables the following APIs by default:

- serviceusage.googleapis.com
- servicenetworking.googleapis.com
- compute.googleapis.com
- logging.googleapis.com
- bigquery.googleapis.com
- cloudresourcemanager.googleapis.com
- cloudbilling.googleapis.com
- iam.googleapis.com
- storage.googleapis.com
- cloudapis.googleapis.com
- iamcredentials.googleapis.com
- monitoring.googleapis.com
- securitycenter.googleapis.com
- cloudkms.googleapis.com
- secretmanager.googleapis.com

## State Storage

When `create_default_service_account` is enabled, the module creates a GCS bucket for storing Terraform state with:
- Versioning enabled
- Uniform bucket-level access
- Lifecycle rules to manage old versions
- Structured naming: `{project-id}-bootstrap-state`

## Security Best Practices

1. **Least Privilege**: Configure service account roles with minimal required permissions
2. **Organization Policies**: Enforce security policies at the project level
3. **Audit Logging**: Enable comprehensive audit logging for compliance
4. **Budget Alerts**: Set up budget monitoring to prevent cost overruns
5. **Essential Contacts**: Configure security and billing contacts for notifications

## Migration Guide

### From Manual Setup

1. Import existing project:
   ```bash
   terraform import module.bootstrap.google_project.project PROJECT_ID
   ```

2. Import enabled APIs:
   ```bash
   terraform import module.bootstrap.google_project_service.apis[\"compute.googleapis.com\"] PROJECT_ID/compute.googleapis.com
   ```

3. Review and apply changes:
   ```bash
   terraform plan
   terraform apply
   ```

## Troubleshooting

### Common Issues

1. **API Enablement Timeout**: Increase timeout in `google_project_service` resource
2. **Permission Denied**: Ensure the service account has necessary organization/billing permissions
3. **Budget Creation Fails**: Verify billing account permissions and quota

### Debug Mode

Enable debug logging:
```bash
export TF_LOG=DEBUG
terraform apply
```

## Contributing

Contributions are welcome! Please ensure:
1. Code follows terraform-google-modules style guide
2. All variables have descriptions and validation
3. Examples are provided for new features
4. Documentation is updated

## License

Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.