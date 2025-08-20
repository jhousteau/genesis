/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

# Project Outputs
output "project_id" {
  description = "The ID of the created project"
  value       = google_project.project.project_id
}

output "project_number" {
  description = "The numeric identifier of the created project"
  value       = google_project.project.number
}

output "project_name" {
  description = "The display name of the created project"
  value       = google_project.project.name
}

# API Outputs
output "enabled_apis" {
  description = "List of enabled APIs in the project"
  value       = keys(google_project_service.apis)
}

output "enabled_api_identities" {
  description = "Map of enabled API service identities"
  value = {
    for k, v in google_project_service_identity.api_identities :
    k => v.email
  }
}

# Service Account Outputs
output "service_account_email" {
  description = "Email of the default service account"
  value       = local.service_account_email
  sensitive   = false
}

output "service_account_id" {
  description = "Unique ID of the default service account"
  value       = var.create_default_service_account ? google_service_account.default[0].unique_id : ""
}

output "service_account_name" {
  description = "Fully qualified name of the default service account"
  value       = var.create_default_service_account ? google_service_account.default[0].name : ""
}

output "service_account_key" {
  description = "Base64 encoded private key of the default service account"
  value       = var.create_default_service_account ? google_service_account_key.default[0].private_key : ""
  sensitive   = true
}

# Budget Outputs
output "budget_name" {
  description = "The resource name of the budget, if created"
  value       = var.budget_amount != null ? google_billing_budget.budget[0].name : ""
}

output "budget_amount" {
  description = "The budgeted amount in USD"
  value       = var.budget_amount
}

# Storage Outputs
output "bootstrap_bucket_name" {
  description = "The name of the bootstrap state bucket"
  value       = var.create_default_service_account ? google_storage_bucket.bootstrap_state[0].name : ""
}

output "bootstrap_bucket_url" {
  description = "The URL of the bootstrap state bucket"
  value       = var.create_default_service_account ? google_storage_bucket.bootstrap_state[0].url : ""
}

# Configuration Outputs
output "organization_id" {
  description = "The organization ID"
  value       = var.org_id
}

output "billing_account" {
  description = "The billing account ID"
  value       = var.billing_account
}

output "folder_id" {
  description = "The folder ID (if project is in a folder)"
  value       = var.folder_id
}

output "default_region" {
  description = "The default region for resources"
  value       = var.default_region
}

output "default_zone" {
  description = "The default zone for resources"
  value       = local.default_zone
}

output "labels" {
  description = "The labels applied to the project"
  value       = local.merged_labels
}

# IAM Outputs
output "project_iam_roles" {
  description = "Map of IAM roles granted on the project"
  value = merge(
    {
      for member in google_project_iam_member.default_service_account :
      "${member.role}_${replace(member.member, "/[^a-zA-Z0-9]/", "_")}" => {
        role   = member.role
        member = member.member
      }
    },
    {
      for member in google_project_iam_member.api_identity_roles :
      "${member.role}_${replace(member.member, "/[^a-zA-Z0-9]/", "_")}" => {
        role   = member.role
        member = member.member
      }
    }
  )
}

# Computed Outputs
output "project_services_map" {
  description = "Map of enabled services with their activation status"
  value = {
    for api in local.activate_apis :
    api => {
      enabled = true
      project = google_project.project.project_id
    }
  }
}

output "gcp_service_account_compute" {
  description = "The compute service agent service account"
  value       = "service-${google_project.project.number}@compute-system.iam.gserviceaccount.com"
}

output "gcp_service_account_gke" {
  description = "The GKE service agent service account"
  value       = "service-${google_project.project.number}@container-engine-robot.iam.gserviceaccount.com"
}

output "gcp_service_account_cloudbuild" {
  description = "The Cloud Build service agent service account"
  value       = "${google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# Essential Contacts Outputs
output "essential_contacts" {
  description = "Map of configured essential contacts"
  value = {
    for k, v in google_essential_contacts_contact.contacts :
    k => {
      email                = v.email
      notification_categories = v.notification_category_subscriptions
    }
  }
}

# Organization Policy Outputs
output "org_policies" {
  description = "Map of organization policies applied to the project"
  value = {
    for k, v in google_project_organization_policy.org_policies :
    k => {
      constraint = v.constraint
      project   = v.project
    }
  }
}

# Terraform State Configuration Output
output "terraform_backend_config" {
  description = "Terraform backend configuration for storing state in GCS"
  value = var.create_default_service_account ? {
    backend = "gcs"
    config = {
      bucket = google_storage_bucket.bootstrap_state[0].name
      prefix = "terraform/state"
    }
  } : null
}