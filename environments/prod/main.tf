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

# Production Environment Configuration

locals {
  environment = "prod"

  # Common labels for all resources
  common_labels = merge(
    var.labels,
    {
      environment = local.environment
      managed-by  = "terraform"
      compliance  = "production"
    }
  )

  # Production-specific APIs
  prod_apis = concat(
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
      "cloudtasks.googleapis.com",
      "cloudkms.googleapis.com",
      "secretmanager.googleapis.com",
      "certificatemanager.googleapis.com",
      "dns.googleapis.com",
      "monitoring.googleapis.com",
      "logging.googleapis.com",
      "cloudtrace.googleapis.com",
      "clouderrorreporting.googleapis.com"
    ]
  )
}

# Data source for existing project or create new one
data "google_project" "prod" {
  count      = var.create_project ? 0 : 1
  project_id = var.project_id
}

resource "google_project" "prod" {
  count = var.create_project ? 1 : 0

  name            = var.project_name != "" ? var.project_name : "${var.project_prefix}-${local.environment}"
  project_id      = var.project_id
  org_id          = var.folder_id == "" ? var.org_id : null
  folder_id       = var.folder_id != "" ? var.folder_id : null
  billing_account = var.billing_account

  labels = local.common_labels
}

locals {
  project_id = var.create_project ? google_project.prod[0].project_id : data.google_project.prod[0].project_id
}

# Enable required APIs
resource "google_project_service" "prod_apis" {
  for_each = toset(local.prod_apis)

  project = local.project_id
  service = each.value

  disable_on_destroy = false
}

# KMS keyring for production encryption
resource "google_kms_key_ring" "prod" {
  project  = local.project_id
  name     = "prod-keyring-${var.region}"
  location = var.region

  depends_on = [google_project_service.prod_apis]
}

# KMS keys for different services
resource "google_kms_crypto_key" "prod_gcs" {
  name            = "gcs-encryption-key"
  key_ring        = google_kms_key_ring.prod.id
  rotation_period = "2592000s" # 30 days
  purpose         = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  labels = local.common_labels
}

resource "google_kms_crypto_key" "prod_secrets" {
  name            = "secrets-encryption-key"
  key_ring        = google_kms_key_ring.prod.id
  rotation_period = "2592000s" # 30 days
  purpose         = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  labels = local.common_labels
}

# Create production VPC network with high availability
resource "google_compute_network" "prod" {
  project                 = local.project_id
  name                    = "${var.network_name}-${local.environment}"
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL" # Global routing for multi-region

  depends_on = [google_project_service.prod_apis]
}

# Create subnets in primary region
resource "google_compute_subnetwork" "prod_main" {
  project       = local.project_id
  name          = "${var.network_name}-${local.environment}-main-${var.primary_region}"
  network       = google_compute_network.prod.self_link
  region        = var.primary_region
  ip_cidr_range = var.primary_subnet_ranges["main"]

  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.primary_subnet_ranges["pods"]
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.primary_subnet_ranges["services"]
  }

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_subnetwork" "prod_serverless" {
  project       = local.project_id
  name          = "${var.network_name}-${local.environment}-serverless-${var.primary_region}"
  network       = google_compute_network.prod.self_link
  region        = var.primary_region
  ip_cidr_range = var.primary_subnet_ranges["serverless"]

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Create subnets in secondary region for DR
resource "google_compute_subnetwork" "prod_main_dr" {
  count = var.enable_dr ? 1 : 0

  project       = local.project_id
  name          = "${var.network_name}-${local.environment}-main-${var.dr_region}"
  network       = google_compute_network.prod.self_link
  region        = var.dr_region
  ip_cidr_range = var.dr_subnet_ranges["main"]

  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.dr_subnet_ranges["pods"]
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.dr_subnet_ranges["services"]
  }

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud Router and NAT for primary region
resource "google_compute_router" "prod_primary" {
  project = local.project_id
  name    = "${var.network_name}-${local.environment}-router-${var.primary_region}"
  network = google_compute_network.prod.self_link
  region  = var.primary_region

  bgp {
    asn = 64514
  }
}

resource "google_compute_router_nat" "prod_primary" {
  project = local.project_id
  name    = "${var.network_name}-${local.environment}-nat-${var.primary_region}"
  router  = google_compute_router.prod_primary.name
  region  = var.primary_region

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Cloud Router and NAT for DR region
resource "google_compute_router" "prod_dr" {
  count = var.enable_dr ? 1 : 0

  project = local.project_id
  name    = "${var.network_name}-${local.environment}-router-${var.dr_region}"
  network = google_compute_network.prod.self_link
  region  = var.dr_region

  bgp {
    asn = 64515
  }
}

resource "google_compute_router_nat" "prod_dr" {
  count = var.enable_dr ? 1 : 0

  project = local.project_id
  name    = "${var.network_name}-${local.environment}-nat-${var.dr_region}"
  router  = google_compute_router.prod_dr[0].name
  region  = var.dr_region

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall rules for production
resource "google_compute_firewall" "prod_allow_internal" {
  project = local.project_id
  name    = "${var.network_name}-${local.environment}-allow-internal"
  network = google_compute_network.prod.name

  allow {
    protocol = "tcp"
    ports    = ["443", "3306", "5432", "6379", "27017"] # HTTPS, MySQL, PostgreSQL, Redis, MongoDB
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = concat(
    [for k, v in var.primary_subnet_ranges : v],
    var.enable_dr ? [for k, v in var.dr_subnet_ranges : v] : []
  )

  priority = 1000
}

resource "google_compute_firewall" "prod_allow_health_checks" {
  project = local.project_id
  name    = "${var.network_name}-${local.environment}-allow-health-checks"
  network = google_compute_network.prod.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = [
    "35.191.0.0/16",
    "130.211.0.0/22",
    "209.85.152.0/22",
    "209.85.204.0/22"
  ]

  target_tags = ["allow-health-checks"]
  priority    = 900
}

# Artifact Registry for production container images
resource "google_artifact_registry_repository" "prod_containers" {
  project       = local.project_id
  location      = var.primary_region
  repository_id = "${var.artifact_registry_name}-${local.environment}"
  description   = "Production container registry"
  format        = "DOCKER"

  labels = local.common_labels

  depends_on = [google_project_service.prod_apis]
}

# Service accounts for production workloads
resource "google_service_account" "prod_compute" {
  project      = local.project_id
  account_id   = "compute-${local.environment}"
  display_name = "Production Compute Engine Service Account"
  description  = "Service account for production Compute Engine instances"
}

resource "google_service_account" "prod_gke" {
  project      = local.project_id
  account_id   = "gke-${local.environment}"
  display_name = "Production GKE Service Account"
  description  = "Service account for production GKE nodes"
}

resource "google_service_account" "prod_cloud_run" {
  project      = local.project_id
  account_id   = "cloud-run-${local.environment}"
  display_name = "Production Cloud Run Service Account"
  description  = "Service account for production Cloud Run services"
}

resource "google_service_account" "prod_cloud_functions" {
  project      = local.project_id
  account_id   = "cloud-functions-${local.environment}"
  display_name = "Production Cloud Functions Service Account"
  description  = "Service account for production Cloud Functions"
}

# IAM bindings for service accounts with production-specific roles
resource "google_project_iam_member" "prod_compute_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent"
  ])

  project = local.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.prod_compute.email}"
}

resource "google_project_iam_member" "prod_gke_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/artifactregistry.reader",
    "roles/cloudtrace.agent"
  ])

  project = local.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.prod_gke.email}"
}

resource "google_project_iam_member" "prod_cloud_run_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/artifactregistry.reader",
    "roles/secretmanager.secretAccessor",
    "roles/cloudtrace.agent",
    "roles/cloudsql.client"
  ])

  project = local.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.prod_cloud_run.email}"
}

resource "google_project_iam_member" "prod_cloud_functions_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/artifactregistry.reader",
    "roles/secretmanager.secretAccessor",
    "roles/pubsub.publisher",
    "roles/cloudtrace.agent",
    "roles/eventarc.eventReceiver"
  ])

  project = local.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.prod_cloud_functions.email}"
}

# Firestore database for production with backup
resource "google_firestore_database" "prod" {
  count = var.enable_firestore ? 1 : 0

  project     = local.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.prod_apis]
}

# Cloud Storage buckets for production with encryption
resource "google_storage_bucket" "prod_data" {
  project  = local.project_id
  name     = "${local.project_id}-data-${local.environment}"
  location = var.storage_location

  uniform_bucket_level_access = true
  force_destroy               = false # Never force destroy in production

  encryption {
    default_kms_key_name = google_kms_crypto_key.prod_gcs.id
  }

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 30
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
    condition {
      age = 90
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
    condition {
      age = 365
    }
  }

  labels = local.common_labels

  depends_on = [google_project_service.prod_apis]
}

resource "google_storage_bucket" "prod_backup" {
  project  = local.project_id
  name     = "${local.project_id}-backup-${local.environment}"
  location = var.storage_location

  uniform_bucket_level_access = true
  force_destroy               = false

  encryption {
    default_kms_key_name = google_kms_crypto_key.prod_gcs.id
  }

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = var.backup_retention_days
    }
  }

  labels = local.common_labels

  depends_on = [google_project_service.prod_apis]
}

# Pub/Sub topics for production with DLQ
resource "google_pubsub_topic" "prod_events" {
  project = local.project_id
  name    = "events-${local.environment}"

  message_retention_duration = "604800s" # 7 days

  labels = local.common_labels

  depends_on = [google_project_service.prod_apis]
}

resource "google_pubsub_topic" "prod_deadletter" {
  project = local.project_id
  name    = "deadletter-${local.environment}"

  message_retention_duration = "2592000s" # 30 days

  labels = local.common_labels

  depends_on = [google_project_service.prod_apis]
}

# Cloud SQL instance for production (if enabled)
resource "google_sql_database_instance" "prod" {
  count = var.enable_cloud_sql ? 1 : 0

  project          = local.project_id
  name             = "${var.project_prefix}-${local.environment}-db"
  database_version = var.cloud_sql_version
  region           = var.primary_region

  settings {
    tier              = var.cloud_sql_tier
    availability_type = "REGIONAL" # High availability

    backup_configuration {
      enabled                        = true
      start_time                     = "02:00"
      point_in_time_recovery_enabled = true
      location                       = var.storage_location

      backup_retention_settings {
        retained_backups = 30
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.prod.id
    }

    database_flags {
      name  = "slow_query_log"
      value = "on"
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }

    user_labels = local.common_labels
  }

  deletion_protection = true

  depends_on = [
    google_project_service.prod_apis,
    google_service_networking_connection.prod
  ]
}

# Private service connection for Cloud SQL
resource "google_compute_global_address" "prod_sql" {
  count = var.enable_cloud_sql ? 1 : 0

  project       = local.project_id
  name          = "sql-private-ip-${local.environment}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.prod.id
}

resource "google_service_networking_connection" "prod" {
  count = var.enable_cloud_sql ? 1 : 0

  network                 = google_compute_network.prod.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.prod_sql[0].name]
}

# Budget alert for production environment
resource "google_billing_budget" "prod" {
  billing_account = var.billing_account
  display_name    = "Production Environment Budget"

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
    threshold_percent = 0.9
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

# Monitoring workspace for production
resource "google_monitoring_workspace" "prod" {
  count = var.enable_monitoring_workspace ? 1 : 0

  provider     = google-beta
  project      = local.project_id
  display_name = "Production Monitoring Workspace"
}