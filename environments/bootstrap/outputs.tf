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
  description = "The bootstrap project ID"
  value       = google_project.bootstrap.project_id
}

output "project_number" {
  description = "The bootstrap project number"
  value       = google_project.bootstrap.number
}

# State Backend Outputs
output "state_bucket_name" {
  description = "The name of the GCS bucket for Terraform state"
  value       = module.terraform_state_backend.bucket_name
}

output "state_bucket_url" {
  description = "The URL of the GCS bucket for Terraform state"
  value       = module.terraform_state_backend.bucket_url
}

# Service Account Outputs
output "terraform_service_account_email" {
  description = "Email of the Terraform service account"
  value       = google_service_account.terraform.email
}

output "terraform_service_account_id" {
  description = "ID of the Terraform service account"
  value       = google_service_account.terraform.id
}

output "terraform_service_account_key" {
  description = "Base64 encoded service account key (sensitive)"
  value       = var.create_sa_key ? google_service_account_key.terraform[0].private_key : null
  sensitive   = true
}

# Workload Identity Outputs
output "workload_identity_pool_name" {
  description = "Full name of the Workload Identity Pool"
  value       = var.enable_workload_identity ? module.github_workload_identity[0].pool_name : null
}

output "workload_identity_provider_name" {
  description = "Full name of the Workload Identity Provider"
  value       = var.enable_workload_identity ? module.github_workload_identity[0].provider_name : null
}

# KMS Outputs
output "kms_keyring_id" {
  description = "ID of the KMS keyring for state encryption"
  value       = var.enable_state_encryption ? google_kms_key_ring.terraform_state[0].id : null
}

output "kms_crypto_key_id" {
  description = "ID of the KMS crypto key for state encryption"
  value       = var.enable_state_encryption ? google_kms_crypto_key.terraform_state[0].id : null
}

# Network Outputs
output "network_name" {
  description = "Name of the bootstrap VPC network"
  value       = var.create_bootstrap_network ? google_compute_network.bootstrap[0].name : null
}

output "subnet_name" {
  description = "Name of the bootstrap subnet"
  value       = var.create_bootstrap_network ? google_compute_subnetwork.bootstrap[0].name : null
}

# Backend Configuration Output
output "backend_config" {
  description = "Terraform backend configuration for other environments"
  value = {
    bucket = module.terraform_state_backend.bucket_name
    prefix = "ENVIRONMENT_NAME/terraform/state" # Replace ENVIRONMENT_NAME
  }
}

# Instructions Output
output "next_steps" {
  description = "Next steps after bootstrap"
  value       = <<-EOT
    Bootstrap complete! Next steps:

    1. Save the Terraform service account key (if created) securely
    2. Update backend.tf in other environments with:
       bucket = "${module.terraform_state_backend.bucket_name}"
    3. Configure GitHub Actions with Workload Identity (if enabled)
    4. Deploy development and production environments
  EOT
}
