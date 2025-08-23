# Security Scanning Infrastructure
# Comprehensive security scanning and vulnerability management platform

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID for security scanning infrastructure"
  type        = string
}

variable "region" {
  description = "Primary region for security scanning resources"
  type        = string
  default     = "us-central1"
}

variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "billing_account" {
  description = "Billing account for security scanning projects"
  type        = string
}

variable "security_environment" {
  description = "Security scanning environment type"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.security_environment)
    error_message = "Security environment must be development, staging, or production."
  }
}

variable "scanning_schedule" {
  description = "Cron schedule for automated security scans"
  type        = string
  default     = "0 2 * * *" # Daily at 2 AM
}

# Security Scanning Project
resource "google_project" "security_scanning_project" {
  name            = "security-scanning-${var.security_environment}"
  project_id      = var.project_id
  billing_account = var.billing_account
  org_id          = var.organization_id

  labels = {
    environment = var.security_environment
    purpose     = "security-scanning"
    automation  = "enabled"
    criticality = "high"
  }
}

# Enable required APIs
resource "google_project_service" "security_apis" {
  project = google_project.security_scanning_project.project_id

  for_each = toset([
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudkms.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
    "containeranalysis.googleapis.com",
    "containerscanning.googleapis.com",
    "dataflow.googleapis.com",
    "dlp.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "securitycenter.googleapis.com",
    "storage.googleapis.com",
    "websecurityscanner.googleapis.com"
  ])

  service                    = each.value
  disable_dependent_services = true
}

# Secure VPC for security scanning infrastructure
resource "google_compute_network" "security_vpc" {
  project                 = google_project.security_scanning_project.project_id
  name                    = "security-scanning-vpc-${var.security_environment}"
  auto_create_subnetworks = false
  description             = "Secure VPC for security scanning infrastructure"

  depends_on = [google_project_service.security_apis]
}

resource "google_compute_subnetwork" "security_subnet" {
  project       = google_project.security_scanning_project.project_id
  name          = "security-scanning-subnet-${var.region}"
  ip_cidr_range = "10.20.0.0/24"
  region        = var.region
  network       = google_compute_network.security_vpc.name

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_1_MIN"
    flow_sampling        = 1.0
    metadata             = "INCLUDE_ALL_METADATA"
  }

  secondary_ip_range {
    range_name    = "security-pods"
    ip_cidr_range = "10.21.0.0/16"
  }

  secondary_ip_range {
    range_name    = "security-services"
    ip_cidr_range = "10.22.0.0/16"
  }
}

# KMS for security scanning data encryption
resource "google_kms_key_ring" "security_keyring" {
  project  = google_project.security_scanning_project.project_id
  name     = "security-scanning-keyring-${var.security_environment}"
  location = var.region

  depends_on = [google_project_service.security_apis]
}

resource "google_kms_crypto_key" "security_data_key" {
  name     = "security-data-encryption-key"
  key_ring = google_kms_key_ring.security_keyring.id
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

# GKE Cluster for container-based security scanning
resource "google_container_cluster" "security_cluster" {
  project  = google_project.security_scanning_project.project_id
  name     = "security-scanning-cluster"
  location = var.region

  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.security_vpc.name
  subnetwork = google_compute_subnetwork.security_subnet.name

  # Security configurations
  workload_identity_config {
    workload_pool = "${google_project.security_scanning_project.project_id}.svc.id.goog"
  }

  network_policy {
    enabled = true
  }

  database_encryption {
    state    = "ENCRYPTED"
    key_name = google_kms_crypto_key.security_data_key.id
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "security-pods"
    services_secondary_range_name = "security-services"
  }

  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }

  # Enable security features
  enable_shielded_nodes = true
  enable_legacy_abac    = false

  depends_on = [google_project_service.security_apis]
}

# Security scanning node pool
resource "google_container_node_pool" "security_nodes" {
  project    = google_project.security_scanning_project.project_id
  name       = "security-node-pool"
  location   = var.region
  cluster    = google_container_cluster.security_cluster.name
  node_count = 3

  node_config {
    machine_type = "e2-standard-4"

    # Security configurations
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    service_account = google_service_account.gke_nodes.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      purpose = "security-scanning"
    }

    tags = ["security-scanner"]

    disk_encryption_key = google_kms_crypto_key.security_data_key.id
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
}

# Service accounts for security scanning
resource "google_service_account" "gke_nodes" {
  project      = google_project.security_scanning_project.project_id
  account_id   = "gke-security-nodes"
  display_name = "GKE Security Scanning Nodes"
}

resource "google_service_account" "security_scanner" {
  project      = google_project.security_scanning_project.project_id
  account_id   = "security-scanner"
  display_name = "Security Scanner Service Account"
}

resource "google_service_account" "vulnerability_manager" {
  project      = google_project.security_scanning_project.project_id
  account_id   = "vulnerability-manager"
  display_name = "Vulnerability Management Service Account"
}

# IAM bindings for security scanning
resource "google_project_iam_binding" "security_scanner_permissions" {
  project = google_project.security_scanning_project.project_id
  role    = "roles/securitycenter.admin"

  members = [
    "serviceAccount:${google_service_account.security_scanner.email}",
  ]
}

resource "google_project_iam_binding" "vulnerability_scanner_permissions" {
  project = google_project.security_scanning_project.project_id
  role    = "roles/containeranalysis.admin"

  members = [
    "serviceAccount:${google_service_account.vulnerability_manager.email}",
  ]
}

resource "google_project_iam_binding" "web_scanner_permissions" {
  project = google_project.security_scanning_project.project_id
  role    = "roles/websecurityscanner.editor"

  members = [
    "serviceAccount:${google_service_account.security_scanner.email}",
  ]
}

# BigQuery for security scan results
resource "google_bigquery_dataset" "security_dataset" {
  project    = google_project.security_scanning_project.project_id
  dataset_id = "security_scanning_results"
  location   = var.region

  description                     = "Security scanning results and vulnerability data"
  default_table_expiration_ms     = 31536000000 # 1 year
  default_partition_expiration_ms = 2592000000  # 30 days

  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.security_data_key.id
  }

  labels = {
    purpose = "security-analytics"
  }
}

# BigQuery tables for different scan types
resource "google_bigquery_table" "vulnerability_scans" {
  project    = google_project.security_scanning_project.project_id
  dataset_id = google_bigquery_dataset.security_dataset.dataset_id
  table_id   = "vulnerability_scans"

  time_partitioning {
    type  = "DAY"
    field = "scan_timestamp"
  }

  clustering = ["severity", "scan_type", "target_type"]

  schema = <<EOF
[
  {
    "name": "scan_id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Unique identifier for the scan"
  },
  {
    "name": "scan_timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "When the scan was performed"
  },
  {
    "name": "scan_type",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Type of security scan (SAST, DAST, SCA, etc.)"
  },
  {
    "name": "target_type",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Type of target scanned (application, infrastructure, container)"
  },
  {
    "name": "target_identifier",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Identifier of the scanned target"
  },
  {
    "name": "vulnerability_id",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Vulnerability identifier (CVE, CWE, etc.)"
  },
  {
    "name": "severity",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Vulnerability severity (CRITICAL, HIGH, MEDIUM, LOW)"
  },
  {
    "name": "title",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Vulnerability title or name"
  },
  {
    "name": "description",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Detailed vulnerability description"
  },
  {
    "name": "cvss_score",
    "type": "FLOAT",
    "mode": "NULLABLE",
    "description": "CVSS vulnerability score"
  },
  {
    "name": "remediation",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Remediation guidance"
  },
  {
    "name": "status",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Vulnerability status (OPEN, IN_PROGRESS, RESOLVED, FALSE_POSITIVE)"
  },
  {
    "name": "false_positive",
    "type": "BOOLEAN",
    "mode": "NULLABLE",
    "description": "Whether this is marked as a false positive"
  },
  {
    "name": "scanner_tool",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Tool that detected the vulnerability"
  },
  {
    "name": "file_path",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "File path where vulnerability was found"
  },
  {
    "name": "line_number",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "Line number where vulnerability was found"
  },
  {
    "name": "confidence",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Scanner confidence level"
  }
]
EOF
}

resource "google_bigquery_table" "compliance_scans" {
  project    = google_project.security_scanning_project.project_id
  dataset_id = google_bigquery_dataset.security_dataset.dataset_id
  table_id   = "compliance_scans"

  time_partitioning {
    type  = "DAY"
    field = "scan_timestamp"
  }

  clustering = ["compliance_framework", "control_category", "status"]

  schema = <<EOF
[
  {
    "name": "scan_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "scan_timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  },
  {
    "name": "compliance_framework",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Compliance framework (CIS, NIST, SOX, etc.)"
  },
  {
    "name": "control_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "control_category",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "control_description",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "target_resource",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "status",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "PASS, FAIL, or MANUAL_REVIEW_REQUIRED"
  },
  {
    "name": "risk_level",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "finding_details",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "remediation_steps",
    "type": "STRING",
    "mode": "NULLABLE"
  }
]
EOF
}

# Pub/Sub topics for security event processing
resource "google_pubsub_topic" "vulnerability_events" {
  project = google_project.security_scanning_project.project_id
  name    = "vulnerability-events"

  kms_key_name = google_kms_crypto_key.security_data_key.id

  message_retention_duration = "604800s" # 7 days
}

resource "google_pubsub_topic" "scan_results" {
  project = google_project.security_scanning_project.project_id
  name    = "scan-results"

  kms_key_name = google_kms_crypto_key.security_data_key.id

  message_retention_duration = "604800s" # 7 days
}

resource "google_pubsub_topic" "compliance_events" {
  project = google_project.security_scanning_project.project_id
  name    = "compliance-events"

  kms_key_name = google_kms_crypto_key.security_data_key.id

  message_retention_duration = "604800s" # 7 days
}

# Pub/Sub subscriptions
resource "google_pubsub_subscription" "vulnerability_processing" {
  project = google_project.security_scanning_project.project_id
  name    = "vulnerability-processing"
  topic   = google_pubsub_topic.vulnerability_events.name

  ack_deadline_seconds = 300

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.security_dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_topic" "security_dead_letter" {
  project = google_project.security_scanning_project.project_id
  name    = "security-dead-letter"

  kms_key_name = google_kms_crypto_key.security_data_key.id
}

# Cloud Storage for scan artifacts and reports
resource "google_storage_bucket" "security_artifacts" {
  project  = google_project.security_scanning_project.project_id
  name     = "${var.project_id}-security-artifacts-${var.security_environment}"
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.security_data_key.id
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  labels = {
    purpose = "security-artifacts"
  }
}

resource "google_storage_bucket" "security_reports" {
  project  = google_project.security_scanning_project.project_id
  name     = "${var.project_id}-security-reports-${var.security_environment}"
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.security_data_key.id
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  labels = {
    purpose = "security-reports"
  }
}

# Cloud Scheduler for automated scans
resource "google_cloud_scheduler_job" "vulnerability_scan" {
  project     = google_project.security_scanning_project.project_id
  region      = var.region
  name        = "automated-vulnerability-scan"
  description = "Automated daily vulnerability scan"
  schedule    = var.scanning_schedule
  time_zone   = "UTC"

  pubsub_target {
    topic_name = google_pubsub_topic.scan_results.id
    data = base64encode(jsonencode({
      scan_type = "vulnerability"
      trigger   = "scheduled"
      scope     = "all_targets"
    }))
  }
}

resource "google_cloud_scheduler_job" "compliance_scan" {
  project     = google_project.security_scanning_project.project_id
  region      = var.region
  name        = "automated-compliance-scan"
  description = "Automated daily compliance scan"
  schedule    = "0 3 * * *" # Daily at 3 AM
  time_zone   = "UTC"

  pubsub_target {
    topic_name = google_pubsub_topic.compliance_events.id
    data = base64encode(jsonencode({
      scan_type  = "compliance"
      trigger    = "scheduled"
      frameworks = ["CIS", "NIST", "SOC2"]
    }))
  }
}

# Security Command Center configuration
resource "google_security_center_source" "vulnerability_source" {
  project      = google_project.security_scanning_project.project_id
  display_name = "Custom Vulnerability Scanner"
  description  = "Custom vulnerability scanning source"
}

# Web Security Scanner configuration
resource "google_project_service" "web_security_scanner" {
  project = google_project.security_scanning_project.project_id
  service = "websecurityscanner.googleapis.com"
}

# Monitoring and alerting for security scanning
resource "google_monitoring_alert_policy" "critical_vulnerability_detected" {
  project      = google_project.security_scanning_project.project_id
  display_name = "Critical Vulnerability Detected"
  description  = "Alert when critical vulnerabilities are detected"

  conditions {
    display_name = "Critical Vulnerability Count"

    condition_threshold {
      filter          = "resource.type=\"global\""
      duration        = "60s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_COUNT"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.security_team_email.name,
    google_monitoring_notification_channel.security_team_pagerduty.name,
  ]

  alert_strategy {
    auto_close = "86400s" # 24 hours
  }
}

resource "google_monitoring_alert_policy" "scan_failure" {
  project      = google_project.security_scanning_project.project_id
  display_name = "Security Scan Failure"
  description  = "Alert when security scans fail"

  conditions {
    display_name = "Scan Failure Rate"

    condition_threshold {
      filter          = "resource.type=\"cloud_function\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.1

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.security_team_email.name,
  ]
}

resource "google_monitoring_notification_channel" "security_team_email" {
  project      = google_project.security_scanning_project.project_id
  display_name = "Security Team Email"
  type         = "email"

  labels = {
    email_address = "security-team@company.com"
  }
}

resource "google_monitoring_notification_channel" "security_team_pagerduty" {
  project      = google_project.security_scanning_project.project_id
  display_name = "Security Team PagerDuty"
  type         = "pagerduty"

  labels = {
    service_key = var.pagerduty_service_key
  }

  sensitive_labels {
    service_key = var.pagerduty_service_key
  }
}

# Firewall rules for security scanning
resource "google_compute_firewall" "security_internal_only" {
  project = google_project.security_scanning_project.project_id
  name    = "security-internal-only"
  network = google_compute_network.security_vpc.name

  description = "Allow internal security scanning traffic only"
  direction   = "INGRESS"
  priority    = 1000

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8080", "9000"]
  }

  source_ranges = ["10.20.0.0/24"]
  target_tags   = ["security-scanner"]
}

resource "google_compute_firewall" "security_egress_scanning" {
  project = google_project.security_scanning_project.project_id
  name    = "security-egress-scanning"
  network = google_compute_network.security_vpc.name

  description = "Allow egress for security scanning activities"
  direction   = "EGRESS"
  priority    = 1000

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  destination_ranges = ["0.0.0.0/0"]
  source_tags        = ["security-scanner"]
}

# IAM custom roles for security scanning
resource "google_project_iam_custom_role" "security_analyst" {
  project     = google_project.security_scanning_project.project_id
  role_id     = "security_analyst"
  title       = "Security Analyst"
  description = "Role for security analysts to view and analyze scan results"

  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.list",
    "bigquery.tables.getData",
    "storage.objects.get",
    "storage.objects.list",
    "securitycenter.findings.list",
    "securitycenter.sources.list",
    "monitoring.dashboards.get",
    "monitoring.dashboards.list",
  ]
}

resource "google_project_iam_custom_role" "vulnerability_manager_role" {
  project     = google_project.security_scanning_project.project_id
  role_id     = "vulnerability_manager_role"
  title       = "Vulnerability Manager"
  description = "Role for managing vulnerability assessments and remediation"

  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.list",
    "bigquery.tables.getData",
    "bigquery.tables.update",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.create",
    "securitycenter.findings.list",
    "securitycenter.findings.update",
    "containeranalysis.occurrences.get",
    "containeranalysis.occurrences.list",
    "containeranalysis.occurrences.create",
    "pubsub.topics.publish",
    "cloudbuild.builds.create",
  ]
}

# Outputs
output "security_project_id" {
  description = "Security scanning project ID"
  value       = google_project.security_scanning_project.project_id
}

output "security_cluster_name" {
  description = "Security scanning GKE cluster name"
  value       = google_container_cluster.security_cluster.name
}

output "security_dataset_id" {
  description = "BigQuery security scanning dataset ID"
  value       = google_bigquery_dataset.security_dataset.dataset_id
}

output "security_topics" {
  description = "Pub/Sub topics for security events"
  value = {
    vulnerability_events = google_pubsub_topic.vulnerability_events.name
    scan_results         = google_pubsub_topic.scan_results.name
    compliance_events    = google_pubsub_topic.compliance_events.name
  }
}

output "security_buckets" {
  description = "Storage buckets for security artifacts and reports"
  value = {
    artifacts = google_storage_bucket.security_artifacts.name
    reports   = google_storage_bucket.security_reports.name
  }
}

output "security_service_accounts" {
  description = "Security scanning service account emails"
  value = {
    scanner           = google_service_account.security_scanner.email
    vulnerability_mgr = google_service_account.vulnerability_manager.email
    gke_nodes         = google_service_account.gke_nodes.email
  }
}

output "security_vpc_name" {
  description = "Security scanning VPC network name"
  value       = google_compute_network.security_vpc.name
}

# Variables
variable "pagerduty_service_key" {
  description = "PagerDuty service key for security alerts"
  type        = string
  sensitive   = true
}
