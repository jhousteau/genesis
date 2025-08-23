# Comprehensive Audit Infrastructure
# Terraform implementation for audit logging and change tracking

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID for audit infrastructure"
  type        = string
}

variable "region" {
  description = "Primary region for audit resources"
  type        = string
  default     = "us-central1"
}

variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "billing_account" {
  description = "Billing account for audit projects"
  type        = string
}

variable "audit_environment" {
  description = "Audit environment type"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.audit_environment)
    error_message = "Audit environment must be development, staging, or production."
  }
}

variable "log_retention_days" {
  description = "Audit log retention period in days"
  type        = number
  default     = 2555 # 7 years
}

# Audit Project Setup
resource "google_project" "audit_project" {
  name            = "audit-${var.audit_environment}"
  project_id      = var.project_id
  billing_account = var.billing_account
  org_id          = var.organization_id

  labels = {
    environment = var.audit_environment
    purpose     = "audit-logging"
    compliance  = "multi-framework"
    criticality = "critical"
    data_type   = "audit-logs"
  }
}

# Enable required APIs
resource "google_project_service" "audit_apis" {
  project = google_project.audit_project.project_id

  for_each = toset([
    "bigquery.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudkms.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
    "dataflow.googleapis.com",
    "datastore.googleapis.com",
    "dlp.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com"
  ])

  service                    = each.value
  disable_dependent_services = true
}

# Audit VPC for secure processing
resource "google_compute_network" "audit_vpc" {
  project                 = google_project.audit_project.project_id
  name                    = "audit-vpc-${var.audit_environment}"
  auto_create_subnetworks = false
  description             = "Secure VPC for audit processing"

  depends_on = [google_project_service.audit_apis]
}

resource "google_compute_subnetwork" "audit_subnet" {
  project       = google_project.audit_project.project_id
  name          = "audit-subnet-${var.region}"
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
  network       = google_compute_network.audit_vpc.name

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_1_MIN"
    flow_sampling        = 1.0
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# KMS for audit log encryption
resource "google_kms_key_ring" "audit_keyring" {
  project  = google_project.audit_project.project_id
  name     = "audit-keyring-${var.audit_environment}"
  location = var.region

  depends_on = [google_project_service.audit_apis]
}

resource "google_kms_crypto_key" "audit_encryption_key" {
  name     = "audit-encryption-key"
  key_ring = google_kms_key_ring.audit_keyring.id
  purpose  = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "HSM"
  }

  lifecycle {
    prevent_destroy = true
  }

  rotation_period = "7776000s" # 90 days
}

# BigQuery for audit log analytics
resource "google_bigquery_dataset" "audit_dataset" {
  project    = google_project.audit_project.project_id
  dataset_id = "audit_logs"
  location   = var.region

  description                     = "Audit logs dataset for comprehensive analysis"
  default_table_expiration_ms     = var.log_retention_days * 24 * 60 * 60 * 1000
  default_partition_expiration_ms = 7 * 24 * 60 * 60 * 1000 # 7 days

  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.audit_encryption_key.id
  }

  labels = {
    environment = var.audit_environment
    purpose     = "audit-analytics"
  }
}

# Cloud Logging sinks for comprehensive audit capture
resource "google_logging_project_sink" "comprehensive_audit_sink" {
  project     = google_project.audit_project.project_id
  name        = "comprehensive-audit-sink"
  destination = "bigquery.googleapis.com/projects/${google_project.audit_project.project_id}/datasets/${google_bigquery_dataset.audit_dataset.dataset_id}"

  # Capture all audit-relevant logs
  filter = <<EOF
(protoPayload.serviceName!="" AND protoPayload.methodName!="") OR
(logName:"cloudaudit.googleapis.com") OR
(logName:"compute.googleapis.com") OR
(logName:"storage.googleapis.com") OR
(logName:"cloudsql.googleapis.com") OR
(logName:"container.googleapis.com") OR
(logName:"iam.googleapis.com") OR
(logName:"cloudkms.googleapis.com") OR
(severity>=WARNING) OR
(labels.audit_required="true")
EOF

  unique_writer_identity = true

  bigquery_options {
    use_partitioned_tables = true
  }
}

# Grant BigQuery write permissions to the sink
resource "google_bigquery_dataset_iam_member" "audit_sink_writer" {
  dataset_id = google_bigquery_dataset.audit_dataset.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.comprehensive_audit_sink.writer_identity
}

# Pub/Sub topics for real-time audit processing
resource "google_pubsub_topic" "audit_events" {
  project = google_project.audit_project.project_id
  name    = "audit-events"

  kms_key_name = google_kms_crypto_key.audit_encryption_key.id

  message_retention_duration = "604800s" # 7 days

  labels = {
    purpose = "real-time-audit"
  }
}

resource "google_pubsub_topic" "change_events" {
  project = google_project.audit_project.project_id
  name    = "change-events"

  kms_key_name = google_kms_crypto_key.audit_encryption_key.id

  message_retention_duration = "604800s" # 7 days

  labels = {
    purpose = "change-tracking"
  }
}

resource "google_pubsub_topic" "security_events" {
  project = google_project.audit_project.project_id
  name    = "security-events"

  kms_key_name = google_kms_crypto_key.audit_encryption_key.id

  message_retention_duration = "604800s" # 7 days

  labels = {
    purpose = "security-monitoring"
  }
}

# Pub/Sub subscriptions for processing
resource "google_pubsub_subscription" "audit_processing" {
  project = google_project.audit_project.project_id
  name    = "audit-processing"
  topic   = google_pubsub_topic.audit_events.name

  ack_deadline_seconds = 300

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.audit_dead_letter.id
    max_delivery_attempts = 5
  }

  expiration_policy {
    ttl = "" # Never expire
  }
}

resource "google_pubsub_topic" "audit_dead_letter" {
  project = google_project.audit_project.project_id
  name    = "audit-dead-letter"

  kms_key_name = google_kms_crypto_key.audit_encryption_key.id
}

# Cloud Storage for long-term audit archive
resource "google_storage_bucket" "audit_archive" {
  project  = google_project.audit_project.project_id
  name     = "${var.project_id}-audit-archive-${var.audit_environment}"
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.audit_encryption_key.id
  }

  lifecycle_rule {
    condition {
      age = var.log_retention_days
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 1095 # 3 years
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }

  labels = {
    purpose     = "audit-archive"
    environment = var.audit_environment
  }
}

# Cloud Functions for audit processing
resource "google_storage_bucket" "function_source" {
  project  = google_project.audit_project.project_id
  name     = "${var.project_id}-audit-functions-${var.audit_environment}"
  location = var.region

  uniform_bucket_level_access = true
}

# Service accounts for audit processing
resource "google_service_account" "audit_processor" {
  project      = google_project.audit_project.project_id
  account_id   = "audit-processor"
  display_name = "Audit Processing Service Account"
  description  = "Service account for audit log processing and analysis"
}

resource "google_service_account" "change_tracker" {
  project      = google_project.audit_project.project_id
  account_id   = "change-tracker"
  display_name = "Change Tracking Service Account"
  description  = "Service account for change detection and approval workflows"
}

# IAM bindings for audit service accounts
resource "google_project_iam_binding" "audit_processor_permissions" {
  project = google_project.audit_project.project_id
  role    = "roles/bigquery.dataEditor"

  members = [
    "serviceAccount:${google_service_account.audit_processor.email}",
  ]
}

resource "google_project_iam_binding" "audit_processor_pubsub" {
  project = google_project.audit_project.project_id
  role    = "roles/pubsub.editor"

  members = [
    "serviceAccount:${google_service_account.audit_processor.email}",
  ]
}

resource "google_project_iam_binding" "audit_processor_storage" {
  project = google_project.audit_project.project_id
  role    = "roles/storage.objectAdmin"

  members = [
    "serviceAccount:${google_service_account.audit_processor.email}",
  ]
}

# Custom IAM role for audit analysis
resource "google_project_iam_custom_role" "audit_analyst" {
  project     = google_project.audit_project.project_id
  role_id     = "audit_analyst"
  title       = "Audit Analyst"
  description = "Role for audit analysts with read access to audit data"

  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.list",
    "bigquery.tables.getData",
    "storage.objects.get",
    "storage.objects.list",
    "logging.logs.list",
    "logging.logEntries.list",
  ]
}

# Firewall rules for audit infrastructure
resource "google_compute_firewall" "audit_internal_only" {
  project = google_project.audit_project.project_id
  name    = "audit-internal-only"
  network = google_compute_network.audit_vpc.name

  description = "Allow internal audit processing traffic only"
  direction   = "INGRESS"
  priority    = 1000

  allow {
    protocol = "tcp"
    ports    = ["443", "80"]
  }

  source_ranges = ["10.10.0.0/24"]
  target_tags   = ["audit-processor"]
}

# Cloud SQL for audit metadata and workflows
resource "google_sql_database_instance" "audit_metadata_db" {
  project          = google_project.audit_project.project_id
  name             = "audit-metadata-${var.audit_environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier                        = "db-f1-micro" # Small instance for metadata
    availability_type           = "ZONAL"
    deletion_protection_enabled = true

    database_flags {
      name  = "log_statement"
      value = "all"
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.audit_vpc.id
      require_ssl     = true
    }

    disk_encryption_configuration {
      kms_key_name = google_kms_crypto_key.audit_encryption_key.id
    }
  }
}

# Private service connection for Cloud SQL
resource "google_compute_global_address" "audit_private_ip" {
  project       = google_project.audit_project.project_id
  name          = "audit-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.audit_vpc.id
}

resource "google_service_networking_connection" "audit_private_connection" {
  network                 = google_compute_network.audit_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.audit_private_ip.name]
}

# BigQuery views for common audit queries
resource "google_bigquery_table" "access_patterns_view" {
  project    = google_project.audit_project.project_id
  dataset_id = google_bigquery_dataset.audit_dataset.dataset_id
  table_id   = "access_patterns"

  view {
    query          = <<EOF
SELECT
  protoPayload.authenticationInfo.principalEmail as user_email,
  protoPayload.serviceName as service,
  protoPayload.methodName as method,
  protoPayload.resourceName as resource,
  timestamp,
  protoPayload.requestMetadata.callerIp as source_ip,
  protoPayload.request as request_details
FROM `${google_project.audit_project.project_id}.${google_bigquery_dataset.audit_dataset.dataset_id}.cloudaudit_googleapis_com_activity_*`
WHERE protoPayload.authenticationInfo.principalEmail IS NOT NULL
  AND DATE(_PARTITIONTIME) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY timestamp DESC
EOF
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "change_tracking_view" {
  project    = google_project.audit_project.project_id
  dataset_id = google_bigquery_dataset.audit_dataset.dataset_id
  table_id   = "change_tracking"

  view {
    query          = <<EOF
SELECT
  protoPayload.authenticationInfo.principalEmail as changed_by,
  protoPayload.serviceName as service,
  protoPayload.methodName as change_type,
  protoPayload.resourceName as resource_changed,
  timestamp,
  protoPayload.requestMetadata.callerIp as source_ip,
  protoPayload.request as change_details,
  protoPayload.response as change_result
FROM `${google_project.audit_project.project_id}.${google_bigquery_dataset.audit_dataset.dataset_id}.cloudaudit_googleapis_com_activity_*`
WHERE protoPayload.methodName LIKE '%create%'
   OR protoPayload.methodName LIKE '%update%'
   OR protoPayload.methodName LIKE '%delete%'
   OR protoPayload.methodName LIKE '%patch%'
  AND DATE(_PARTITIONTIME) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
ORDER BY timestamp DESC
EOF
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "security_events_view" {
  project    = google_project.audit_project.project_id
  dataset_id = google_bigquery_dataset.audit_dataset.dataset_id
  table_id   = "security_events"

  view {
    query          = <<EOF
SELECT
  protoPayload.authenticationInfo.principalEmail as user_email,
  protoPayload.serviceName as service,
  protoPayload.methodName as method,
  protoPayload.resourceName as resource,
  timestamp,
  protoPayload.requestMetadata.callerIp as source_ip,
  severity,
  protoPayload.status.code as status_code,
  protoPayload.status.message as status_message
FROM `${google_project.audit_project.project_id}.${google_bigquery_dataset.audit_dataset.dataset_id}.cloudaudit_googleapis_com_activity_*`
WHERE severity IN ('ERROR', 'WARNING', 'CRITICAL')
  OR protoPayload.status.code != 0
  OR protoPayload.methodName LIKE '%iam%'
  OR protoPayload.serviceName = 'iam.googleapis.com'
  AND DATE(_PARTITIONTIME) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY timestamp DESC
EOF
    use_legacy_sql = false
  }
}

# Scheduled queries for compliance reporting
resource "google_bigquery_data_transfer_config" "daily_compliance_report" {
  project        = google_project.audit_project.project_id
  display_name   = "Daily Compliance Report"
  location       = var.region
  data_source_id = "scheduled_query"

  schedule = "every day 06:00"

  params = {
    query = <<EOF
CREATE OR REPLACE TABLE `${google_project.audit_project.project_id}.${google_bigquery_dataset.audit_dataset.dataset_id}.daily_compliance_summary_${formatdate("YYYY_MM_DD", timestamp())}` AS
SELECT
  DATE(timestamp) as report_date,
  protoPayload.serviceName as service,
  COUNT(*) as total_events,
  COUNTIF(severity = 'ERROR') as error_events,
  COUNTIF(severity = 'WARNING') as warning_events,
  COUNT(DISTINCT protoPayload.authenticationInfo.principalEmail) as unique_users,
  COUNT(DISTINCT protoPayload.requestMetadata.callerIp) as unique_source_ips
FROM `${google_project.audit_project.project_id}.${google_bigquery_dataset.audit_dataset.dataset_id}.cloudaudit_googleapis_com_activity_*`
WHERE DATE(timestamp) = CURRENT_DATE() - 1
GROUP BY report_date, service
ORDER BY total_events DESC
EOF
  }

  destination_dataset_id = google_bigquery_dataset.audit_dataset.dataset_id
}

# Monitoring and alerting for audit infrastructure
resource "google_monitoring_alert_policy" "audit_log_ingestion_failure" {
  project      = google_project.audit_project.project_id
  display_name = "Audit Log Ingestion Failure"
  description  = "Alert when audit log ingestion fails"

  conditions {
    display_name = "Log Ingestion Error Rate"

    condition_threshold {
      filter          = "resource.type=\"logging_sink\" AND resource.labels.name=\"${google_logging_project_sink.comprehensive_audit_sink.name}\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.01

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.audit_team_email.name,
    google_monitoring_notification_channel.audit_team_pagerduty.name,
  ]

  alert_strategy {
    auto_close = "1800s"
  }
}

resource "google_monitoring_notification_channel" "audit_team_email" {
  project      = google_project.audit_project.project_id
  display_name = "Audit Team Email"
  type         = "email"

  labels = {
    email_address = "audit-team@company.com"
  }
}

resource "google_monitoring_notification_channel" "audit_team_pagerduty" {
  project      = google_project.audit_project.project_id
  display_name = "Audit Team PagerDuty"
  type         = "pagerduty"

  labels = {
    service_key = var.pagerduty_service_key
  }

  sensitive_labels {
    service_key = var.pagerduty_service_key
  }
}

# Outputs
output "audit_project_id" {
  description = "Audit project ID"
  value       = google_project.audit_project.project_id
}

output "audit_dataset_id" {
  description = "BigQuery audit dataset ID"
  value       = google_bigquery_dataset.audit_dataset.dataset_id
}

output "audit_topics" {
  description = "Pub/Sub topics for audit events"
  value = {
    audit_events    = google_pubsub_topic.audit_events.name
    change_events   = google_pubsub_topic.change_events.name
    security_events = google_pubsub_topic.security_events.name
  }
}

output "audit_storage_bucket" {
  description = "Audit archive storage bucket"
  value       = google_storage_bucket.audit_archive.name
}

output "audit_database_connection" {
  description = "Audit metadata database connection"
  value       = google_sql_database_instance.audit_metadata_db.connection_name
}

output "audit_service_accounts" {
  description = "Audit service account emails"
  value = {
    processor      = google_service_account.audit_processor.email
    change_tracker = google_service_account.change_tracker.email
  }
}

# Variables
variable "pagerduty_service_key" {
  description = "PagerDuty service key for audit alerts"
  type        = string
  sensitive   = true
}
