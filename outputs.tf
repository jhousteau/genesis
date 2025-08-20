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
  description = "The GCP project ID"
  value       = var.project_id
}

output "project_number" {
  description = "The GCP project number"
  value       = data.google_project.project.number
}

output "project_name" {
  description = "The GCP project name"
  value       = data.google_project.project.name
}

# State Backend Outputs
output "state_bucket_name" {
  description = "The name of the GCS bucket for Terraform state"
  value       = var.state_bucket_name
}

output "state_bucket_url" {
  description = "The URL of the GCS bucket for Terraform state"
  value       = var.state_bucket_name != "" ? "gs://${var.state_bucket_name}" : ""
}

# Service Account Outputs
output "terraform_service_account_email" {
  description = "Email of the Terraform service account"
  value       = var.create_terraform_sa ? google_service_account.terraform[0].email : ""
}

output "terraform_service_account_id" {
  description = "ID of the Terraform service account"
  value       = var.create_terraform_sa ? google_service_account.terraform[0].id : ""
}

# Workload Identity Outputs
output "workload_identity_pool_id" {
  description = "ID of the Workload Identity Pool"
  value       = var.enable_workload_identity ? google_iam_workload_identity_pool.github[0].workload_identity_pool_id : ""
}

output "workload_identity_provider_id" {
  description = "ID of the Workload Identity Provider"
  value       = var.enable_workload_identity ? google_iam_workload_identity_pool_provider.github[0].workload_identity_pool_provider_id : ""
}

# Network Outputs
output "network_name" {
  description = "Name of the VPC network"
  value       = var.create_network ? google_compute_network.main[0].name : ""
}

output "network_id" {
  description = "ID of the VPC network"
  value       = var.create_network ? google_compute_network.main[0].id : ""
}

output "subnet_name" {
  description = "Name of the main subnet"
  value       = var.create_network ? google_compute_subnetwork.main[0].name : ""
}

output "subnet_cidr" {
  description = "CIDR range of the main subnet"
  value       = var.create_network ? google_compute_subnetwork.main[0].ip_cidr_range : ""
}

# KMS Outputs
output "kms_keyring_id" {
  description = "ID of the KMS keyring"
  value       = var.enable_kms ? google_kms_key_ring.terraform[0].id : ""
}

output "kms_crypto_key_id" {
  description = "ID of the KMS crypto key"
  value       = var.enable_kms ? google_kms_crypto_key.terraform[0].id : ""
}

# API Outputs
output "activated_apis" {
  description = "List of activated Google APIs"
  value       = var.activate_apis
}

# Environment Outputs
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "region" {
  description = "Default GCP region"
  value       = var.region
}

output "zone" {
  description = "Default GCP zone"
  value       = var.zone
}

output "labels" {
  description = "Labels applied to resources"
  value       = var.labels
}