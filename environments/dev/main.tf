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

# Development Environment Configuration

locals {
  environment = "dev"

  # Common labels for all resources
  common_labels = merge(
    var.labels,
    {
      environment = local.environment
      managed-by  = "terraform"
    }
  )

  # Development-specific APIs
  dev_apis = concat(
    var.activate_apis,
    [
      "compute.googleapis.com",
      "container.googleapis.com",
      "cloudbuild.googleapis.com",
      "artifactregistry.googleapis.com",
      "run.googleapis.com",
      "cloudfunctions.googleapis.com",
      "firebase.googleapis.com",
      "firestore.googleapis.com",
      "pubsub.googleapis.com",
      "cloudscheduler.googleapis.com",
      "cloudtasks.googleapis.com"
    ]
  )
}

# Data source for existing project or create new one
data "google_project" "dev" {
  count      = var.create_project ? 0 : 1
  project_id = var.project_id
}

resource "google_project" "dev" {
  count = var.create_project ? 1 : 0

  name            = var.project_name != "" ? var.project_name : "${var.project_prefix}-${local.environment}"
  project_id      = var.project_id
  org_id          = var.folder_id == "" ? var.org_id : null
  folder_id       = var.folder_id != "" ? var.folder_id : null
  billing_account = var.billing_account

  labels = local.common_labels
}

locals {
  project_id = var.create_project ? google_project.dev[0].project_id : data.google_project.dev[0].project_id
}

# Enable required APIs
resource "google_project_service" "dev_apis" {
  for_each = toset(local.dev_apis)

  project = local.project_id
  service = each.value

  disable_on_destroy = false
}

# Create development VPC network
resource "google_compute_network" "dev" {
  project                 = local.project_id
  name                    = "${var.network_name}-${local.environment}"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.dev_apis]
}

# Create subnets for different workloads
resource "google_compute_subnetwork" "dev_main" {
  project       = local.project_id
  name          = "${var.network_name}-${local.environment}-main-${var.region}"
  network       = google_compute_network.dev.self_link
  region        = var.region
  ip_cidr_range = var.subnet_ranges["main"]

  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.subnet_ranges["pods"]
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.subnet_ranges["services"]
  }

  log_config {
    aggregation_interval = "INTERVAL_5_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_subnetwork" "dev_serverless" {
  project       = local.project_id
  name          = "${var.network_name}-${local.environment}-serverless-${var.region}"
  network       = google_compute_network.dev.self_link
  region        = var.region
  ip_cidr_range = var.subnet_ranges["serverless"]

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_MIN"
    flow_sampling        = 0.5
    metadata             = "EXCLUDE_ALL_METADATA"
  }
}

# Cloud Router for NAT
resource "google_compute_router" "dev" {
  project = local.project_id
  name    = "${var.network_name}-${local.environment}-router"
  network = google_compute_network.dev.self_link
  region  = var.region
}

# Cloud NAT for outbound connectivity
resource "google_compute_router_nat" "dev" {
  project = local.project_id
  name    = "${var.network_name}-${local.environment}-nat"
  router  = google_compute_router.dev.name
  region  = var.region

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall rules
resource "google_compute_firewall" "dev_allow_internal" {
  project = local.project_id
  name    = "${var.network_name}-${local.environment}-allow-internal"
  network = google_compute_network.dev.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [
    var.subnet_ranges["main"],
    var.subnet_ranges["serverless"],
    var.subnet_ranges["pods"],
    var.subnet_ranges["services"]
  ]

  priority = 1000
}

resource "google_compute_firewall" "dev_allow_health_checks" {
  project = local.project_id
  name    = "${var.network_name}-${local.environment}-allow-health-checks"
  network = google_compute_network.dev.name

  allow {
    protocol = "tcp"
  }

  source_ranges = [
    "35.191.0.0/16",
    "130.211.0.0/22"
  ]

  target_tags = ["allow-health-checks"]
  priority    = 900
}

# Artifact Registry for container images
resource "google_artifact_registry_repository" "dev_containers" {
  project       = local.project_id
  location      = var.region
  repository_id = "${var.artifact_registry_name}-${local.environment}"
  description   = "Container registry for ${local.environment} environment"
  format        = "DOCKER"

  labels = local.common_labels

  depends_on = [google_project_service.dev_apis]
}

# Service accounts for different workloads
resource "google_service_account" "dev_compute" {
  project      = local.project_id
  account_id   = "compute-${local.environment}"
  display_name = "Compute Engine Service Account (${local.environment})"
  description  = "Service account for Compute Engine instances in ${local.environment}"
}

resource "google_service_account" "dev_gke" {
  project      = local.project_id
  account_id   = "gke-${local.environment}"
  display_name = "GKE Service Account (${local.environment})"
  description  = "Service account for GKE nodes in ${local.environment}"
}

resource "google_service_account" "dev_cloud_run" {
  project      = local.project_id
  account_id   = "cloud-run-${local.environment}"
  display_name = "Cloud Run Service Account (${local.environment})"
  description  = "Service account for Cloud Run services in ${local.environment}"
}

resource "google_service_account" "dev_cloud_functions" {
  project      = local.project_id
  account_id   = "cloud-functions-${local.environment}"
  display_name = "Cloud Functions Service Account (${local.environment})"
  description  = "Service account for Cloud Functions in ${local.environment}"
}

# IAM bindings for service accounts
resource "google_project_iam_member" "dev_compute_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ])

  project = local.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.dev_compute.email}"
}

resource "google_project_iam_member" "dev_gke_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/artifactregistry.reader"
  ])

  project = local.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.dev_gke.email}"
}

resource "google_project_iam_member" "dev_cloud_run_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/artifactregistry.reader",
    "roles/secretmanager.secretAccessor"
  ])

  project = local.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.dev_cloud_run.email}"
}

resource "google_project_iam_member" "dev_cloud_functions_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/artifactregistry.reader",
    "roles/secretmanager.secretAccessor",
    "roles/pubsub.publisher"
  ])

  project = local.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.dev_cloud_functions.email}"
}

# Firestore database for development
resource "google_firestore_database" "dev" {
  count = var.enable_firestore ? 1 : 0

  project     = local.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.dev_apis]
}

# Cloud Storage buckets for development
resource "google_storage_bucket" "dev_data" {
  project  = local.project_id
  name     = "${local.project_id}-data-${local.environment}"
  location = var.region

  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy_buckets

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 30
    }
  }

  labels = local.common_labels

  depends_on = [google_project_service.dev_apis]
}

resource "google_storage_bucket" "dev_temp" {
  project  = local.project_id
  name     = "${local.project_id}-temp-${local.environment}"
  location = var.region

  uniform_bucket_level_access = true
  force_destroy               = true

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 7
    }
  }

  labels = local.common_labels

  depends_on = [google_project_service.dev_apis]
}

# Pub/Sub topics for development
resource "google_pubsub_topic" "dev_events" {
  project = local.project_id
  name    = "events-${local.environment}"

  message_retention_duration = "86400s" # 1 day

  labels = local.common_labels

  depends_on = [google_project_service.dev_apis]
}

resource "google_pubsub_topic" "dev_deadletter" {
  project = local.project_id
  name    = "deadletter-${local.environment}"

  message_retention_duration = "604800s" # 7 days

  labels = local.common_labels

  depends_on = [google_project_service.dev_apis]
}

# Budget alert for development environment
resource "google_billing_budget" "dev" {
  count = var.budget_amount > 0 ? 1 : 0

  billing_account = var.billing_account
  display_name    = "Budget for ${local.environment} environment"

  budget_filter {
    projects = ["projects/${local.project_id}"]
    labels = {
      environment = local.environment
    }
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_amount)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = var.notification_channels
    disable_default_iam_recipients   = false
  }
}
