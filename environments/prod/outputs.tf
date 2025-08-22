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
  description = "The production project ID"
  value       = local.project_id
}

output "project_number" {
  description = "The production project number"
  value       = var.create_project ? google_project.prod[0].number : data.google_project.prod[0].number
}

# Network Outputs
output "network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.prod.name
}

output "network_id" {
  description = "ID of the VPC network"
  value       = google_compute_network.prod.id
}

output "primary_subnet_main" {
  description = "Name of the main subnet in primary region"
  value       = google_compute_subnetwork.prod_main.name
}

output "primary_subnet_serverless" {
  description = "Name of the serverless subnet in primary region"
  value       = google_compute_subnetwork.prod_serverless.name
}

output "dr_subnet_main" {
  description = "Name of the main subnet in DR region"
  value       = var.enable_dr ? google_compute_subnetwork.prod_main_dr[0].name : null
}

# Service Account Outputs
output "compute_service_account" {
  description = "Email of the Compute Engine service account"
  value       = google_service_account.prod_compute.email
}

output "gke_service_account" {
  description = "Email of the GKE service account"
  value       = google_service_account.prod_gke.email
}

output "cloud_run_service_account" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.prod_cloud_run.email
}

output "cloud_functions_service_account" {
  description = "Email of the Cloud Functions service account"
  value       = google_service_account.prod_cloud_functions.email
}

# KMS Outputs
output "kms_keyring_id" {
  description = "ID of the KMS keyring"
  value       = google_kms_key_ring.prod.id
}

output "kms_gcs_key_id" {
  description = "ID of the GCS encryption key"
  value       = google_kms_crypto_key.prod_gcs.id
}

output "kms_secrets_key_id" {
  description = "ID of the secrets encryption key"
  value       = google_kms_crypto_key.prod_secrets.id
}

# Artifact Registry Outputs
output "artifact_registry_repository" {
  description = "Name of the Artifact Registry repository"
  value       = google_artifact_registry_repository.prod_containers.name
}

output "artifact_registry_url" {
  description = "URL of the Artifact Registry repository"
  value       = "${var.primary_region}-docker.pkg.dev/${local.project_id}/${google_artifact_registry_repository.prod_containers.repository_id}"
}

# Storage Outputs
output "data_bucket_name" {
  description = "Name of the data storage bucket"
  value       = google_storage_bucket.prod_data.name
}

output "backup_bucket_name" {
  description = "Name of the backup storage bucket"
  value       = google_storage_bucket.prod_backup.name
}

# Pub/Sub Outputs
output "events_topic_name" {
  description = "Name of the events Pub/Sub topic"
  value       = google_pubsub_topic.prod_events.name
}

output "deadletter_topic_name" {
  description = "Name of the dead letter Pub/Sub topic"
  value       = google_pubsub_topic.prod_deadletter.name
}

# Firestore Outputs
output "firestore_database" {
  description = "Name of the Firestore database"
  value       = var.enable_firestore ? google_firestore_database.prod[0].name : null
}

# Cloud SQL Outputs
output "cloud_sql_instance_name" {
  description = "Name of the Cloud SQL instance"
  value       = var.enable_cloud_sql ? google_sql_database_instance.prod[0].name : null
}

output "cloud_sql_connection_name" {
  description = "Connection name for Cloud SQL instance"
  value       = var.enable_cloud_sql ? google_sql_database_instance.prod[0].connection_name : null
}

output "cloud_sql_private_ip" {
  description = "Private IP address of Cloud SQL instance"
  value       = var.enable_cloud_sql ? google_sql_database_instance.prod[0].private_ip_address : null
}

# Monitoring Outputs
output "monitoring_workspace_id" {
  description = "ID of the monitoring workspace"
  value       = var.enable_monitoring_workspace ? google_monitoring_workspace.prod[0].id : null
}

# Environment Info
output "environment" {
  description = "Environment name"
  value       = local.environment
}

output "primary_region" {
  description = "Primary GCP region"
  value       = var.primary_region
}

output "dr_region" {
  description = "Disaster recovery region"
  value       = var.enable_dr ? var.dr_region : null
}

output "activated_apis" {
  description = "List of activated Google APIs"
  value       = local.prod_apis
}