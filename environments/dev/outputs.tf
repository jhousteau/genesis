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
  description = "The development project ID"
  value       = local.project_id
}

output "project_number" {
  description = "The development project number"
  value       = var.create_project ? google_project.dev[0].number : data.google_project.dev[0].number
}

# Network Outputs
output "network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.dev.name
}

output "network_id" {
  description = "ID of the VPC network"
  value       = google_compute_network.dev.id
}

output "subnet_main_name" {
  description = "Name of the main subnet"
  value       = google_compute_subnetwork.dev_main.name
}

output "subnet_serverless_name" {
  description = "Name of the serverless subnet"
  value       = google_compute_subnetwork.dev_serverless.name
}

# Service Account Outputs
output "compute_service_account" {
  description = "Email of the Compute Engine service account"
  value       = google_service_account.dev_compute.email
}

output "gke_service_account" {
  description = "Email of the GKE service account"
  value       = google_service_account.dev_gke.email
}

output "cloud_run_service_account" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.dev_cloud_run.email
}

output "cloud_functions_service_account" {
  description = "Email of the Cloud Functions service account"
  value       = google_service_account.dev_cloud_functions.email
}

# Artifact Registry Outputs
output "artifact_registry_repository" {
  description = "Name of the Artifact Registry repository"
  value       = google_artifact_registry_repository.dev_containers.name
}

output "artifact_registry_url" {
  description = "URL of the Artifact Registry repository"
  value       = "${var.region}-docker.pkg.dev/${local.project_id}/${google_artifact_registry_repository.dev_containers.repository_id}"
}

# Storage Outputs
output "data_bucket_name" {
  description = "Name of the data storage bucket"
  value       = google_storage_bucket.dev_data.name
}

output "temp_bucket_name" {
  description = "Name of the temporary storage bucket"
  value       = google_storage_bucket.dev_temp.name
}

# Pub/Sub Outputs
output "events_topic_name" {
  description = "Name of the events Pub/Sub topic"
  value       = google_pubsub_topic.dev_events.name
}

output "deadletter_topic_name" {
  description = "Name of the dead letter Pub/Sub topic"
  value       = google_pubsub_topic.dev_deadletter.name
}

# Firestore Outputs
output "firestore_database" {
  description = "Name of the Firestore database"
  value       = var.enable_firestore ? google_firestore_database.dev[0].name : null
}

# Environment Info
output "environment" {
  description = "Environment name"
  value       = local.environment
}

output "region" {
  description = "Default GCP region"
  value       = var.region
}

output "activated_apis" {
  description = "List of activated Google APIs"
  value       = local.dev_apis
}
