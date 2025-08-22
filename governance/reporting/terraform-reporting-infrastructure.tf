# Compliance Reporting and Dashboard Infrastructure
# Automated reporting platform for multi-framework compliance

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID for compliance reporting"
  type        = string
}

variable "region" {
  description = "Primary region for reporting resources"
  type        = string
  default     = "us-central1"
}

variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "billing_account" {
  description = "Billing account for reporting projects"
  type        = string
}

variable "reporting_environment" {
  description = "Reporting environment type"
  type        = string
  default     = "production"
  
  validation {
    condition = contains(["development", "staging", "production"], var.reporting_environment)
    error_message = "Reporting environment must be development, staging, or production."
  }
}

variable "compliance_frameworks" {
  description = "List of compliance frameworks to support"
  type        = list(string)
  default     = ["SOX", "GDPR", "HIPAA", "PCI-DSS", "ISO27001", "NIST-CSF"]
}

# Compliance Reporting Project
resource "google_project" "reporting_project" {
  name            = "compliance-reporting-${var.reporting_environment}"
  project_id      = var.project_id
  billing_account = var.billing_account
  org_id         = var.organization_id
  
  labels = {
    environment = var.reporting_environment
    purpose    = "compliance-reporting"
    automation = "dashboard-reporting"
    criticality = "high"
  }
}

# Enable required APIs
resource "google_project_service" "reporting_apis" {
  project = google_project.reporting_project.project_id
  
  for_each = toset([
    "aiplatform.googleapis.com",
    "appengine.googleapis.com",
    "bigquery.googleapis.com",
    "bigquerydatatransfer.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudkms.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
    "dataflow.googleapis.com",
    "datastore.googleapis.com",
    "firebase.googleapis.com",
    "firestore.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com"
  ])
  
  service = each.value
  disable_dependent_services = true
}

# VPC for reporting infrastructure
resource "google_compute_network" "reporting_vpc" {
  project                 = google_project.reporting_project.project_id
  name                    = "compliance-reporting-vpc-${var.reporting_environment}"
  auto_create_subnetworks = false
  description             = "VPC for compliance reporting infrastructure"
  
  depends_on = [google_project_service.reporting_apis]
}

resource "google_compute_subnetwork" "reporting_subnet" {
  project       = google_project.reporting_project.project_id
  name          = "compliance-reporting-subnet-${var.region}"
  ip_cidr_range = "10.50.0.0/24"
  region        = var.region
  network       = google_compute_network.reporting_vpc.name
  
  private_ip_google_access = true
  
  log_config {
    aggregation_interval = "INTERVAL_1_MIN"
    flow_sampling       = 1.0
    metadata           = "INCLUDE_ALL_METADATA"
  }
  
  secondary_ip_range {
    range_name    = "reporting-pods"
    ip_cidr_range = "10.51.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "reporting-services"
    ip_cidr_range = "10.52.0.0/16"
  }
}

# KMS for reporting data encryption
resource "google_kms_key_ring" "reporting_keyring" {
  project  = google_project.reporting_project.project_id
  name     = "compliance-reporting-keyring-${var.reporting_environment}"
  location = var.region
  
  depends_on = [google_project_service.reporting_apis]
}

resource "google_kms_crypto_key" "reporting_data_key" {
  name     = "reporting-data-encryption-key"
  key_ring = google_kms_key_ring.reporting_keyring.id
  purpose  = "ENCRYPT_DECRYPT"
  
  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "HSM"
  }
  
  lifecycle {
    prevent_destroy = true
  }
  
  rotation_period = "7776000s"  # 90 days
}

# BigQuery for compliance analytics and reporting
resource "google_bigquery_dataset" "compliance_reporting" {
  project    = google_project.reporting_project.project_id
  dataset_id = "compliance_reporting"
  location   = var.region
  
  description = "Compliance reporting and analytics dataset"
  
  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.reporting_data_key.id
  }
  
  labels = {
    purpose = "compliance-reporting"
  }
}

resource "google_bigquery_dataset" "compliance_evidence" {
  project    = google_project.reporting_project.project_id
  dataset_id = "compliance_evidence"
  location   = var.region
  
  description = "Compliance evidence and audit trail dataset"
  
  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.reporting_data_key.id
  }
  
  labels = {
    purpose = "compliance-evidence"
  }
}

# BigQuery tables for compliance reporting
resource "google_bigquery_table" "compliance_status" {
  project    = google_project.reporting_project.project_id
  dataset_id = google_bigquery_dataset.compliance_reporting.dataset_id
  table_id   = "compliance_status"
  
  time_partitioning {
    type  = "DAY"
    field = "assessment_date"
  }
  
  clustering = ["framework", "control_category", "compliance_status"]
  
  schema = <<EOF
[
  {
    "name": "assessment_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "assessment_date",
    "type": "DATE",
    "mode": "REQUIRED"
  },
  {
    "name": "framework",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Compliance framework (SOX, GDPR, HIPAA, etc.)"
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
    "name": "compliance_status",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "COMPLIANT, NON_COMPLIANT, PARTIAL, NOT_TESTED"
  },
  {
    "name": "risk_level",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "LOW, MEDIUM, HIGH, CRITICAL"
  },
  {
    "name": "testing_method",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "AUTOMATED, MANUAL, HYBRID"
  },
  {
    "name": "evidence_count",
    "type": "INTEGER",
    "mode": "NULLABLE"
  },
  {
    "name": "deficiency_count",
    "type": "INTEGER",
    "mode": "NULLABLE"
  },
  {
    "name": "remediation_target_date",
    "type": "DATE",
    "mode": "NULLABLE"
  },
  {
    "name": "last_test_date",
    "type": "DATE",
    "mode": "NULLABLE"
  },
  {
    "name": "next_test_date",
    "type": "DATE",
    "mode": "NULLABLE"
  },
  {
    "name": "responsible_team",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "auditor_notes",
    "type": "STRING",
    "mode": "NULLABLE"
  }
]
EOF
}

resource "google_bigquery_table" "evidence_inventory" {
  project    = google_project.reporting_project.project_id
  dataset_id = google_bigquery_dataset.compliance_evidence.dataset_id
  table_id   = "evidence_inventory"
  
  time_partitioning {
    type  = "DAY"
    field = "collection_date"
  }
  
  clustering = ["framework", "evidence_type", "automation_status"]
  
  schema = <<EOF
[
  {
    "name": "evidence_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "collection_date",
    "type": "DATE",
    "mode": "REQUIRED"
  },
  {
    "name": "framework",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "control_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "evidence_type",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "DESIGN, OPERATING_EFFECTIVENESS, CORRECTIVE_ACTION"
  },
  {
    "name": "evidence_source",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "automation_status",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "AUTOMATED, MANUAL, SEMI_AUTOMATED"
  },
  {
    "name": "quality_score",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "completeness_score",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "reliability_score",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "storage_location",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "retention_date",
    "type": "DATE",
    "mode": "NULLABLE"
  },
  {
    "name": "access_restrictions",
    "type": "STRING",
    "mode": "REPEATED"
  },
  {
    "name": "validation_status",
    "type": "STRING",
    "mode": "NULLABLE"
  }
]
EOF
}

resource "google_bigquery_table" "compliance_metrics" {
  project    = google_project.reporting_project.project_id
  dataset_id = google_bigquery_dataset.compliance_reporting.dataset_id
  table_id   = "compliance_metrics"
  
  time_partitioning {
    type  = "DAY"
    field = "metric_date"
  }
  
  clustering = ["framework", "metric_type", "metric_category"]
  
  schema = <<EOF
[
  {
    "name": "metric_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "metric_date",
    "type": "DATE",
    "mode": "REQUIRED"
  },
  {
    "name": "framework",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "metric_type",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "KPI, TREND, FORECAST, BENCHMARK"
  },
  {
    "name": "metric_category",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "EFFECTIVENESS, EFFICIENCY, COST, RISK"
  },
  {
    "name": "metric_name",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "metric_value",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "target_value",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "threshold_red",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "threshold_yellow",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "threshold_green",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "trend_direction",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "IMPROVING, STABLE, DECLINING"
  },
  {
    "name": "business_unit",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "calculation_method",
    "type": "STRING",
    "mode": "NULLABLE"
  }
]
EOF
}

# GKE cluster for reporting applications
resource "google_container_cluster" "reporting_cluster" {
  project  = google_project.reporting_project.project_id
  name     = "compliance-reporting-cluster"
  location = var.region
  
  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.reporting_vpc.name
  subnetwork = google_compute_subnetwork.reporting_subnet.name
  
  workload_identity_config {
    workload_pool = "${google_project.reporting_project.project_id}.svc.id.goog"
  }
  
  network_policy {
    enabled = true
  }
  
  database_encryption {
    state    = "ENCRYPTED"
    key_name = google_kms_crypto_key.reporting_data_key.id
  }
  
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }
  
  ip_allocation_policy {
    cluster_secondary_range_name  = "reporting-pods"
    services_secondary_range_name = "reporting-services"
  }
  
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }
  
  enable_shielded_nodes = true
  enable_legacy_abac   = false
  
  depends_on = [google_project_service.reporting_apis]
}

# Node pools for different workloads
resource "google_container_node_pool" "web_frontend_nodes" {
  project    = google_project.reporting_project.project_id
  name       = "web-frontend-pool"
  location   = var.region
  cluster    = google_container_cluster.reporting_cluster.name
  
  autoscaling {
    min_node_count = 2
    max_node_count = 10
  }
  
  node_config {
    machine_type = "e2-standard-4"
    
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
      workload-type = "web-frontend"
    }
    
    tags = ["web-frontend"]
    
    disk_encryption_key = google_kms_crypto_key.reporting_data_key.id
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

resource "google_container_node_pool" "analytics_nodes" {
  project    = google_project.reporting_project.project_id
  name       = "analytics-pool"
  location   = var.region
  cluster    = google_container_cluster.reporting_cluster.name
  
  autoscaling {
    min_node_count = 1
    max_node_count = 8
  }
  
  node_config {
    machine_type = "n1-highmem-4"  # High memory for analytics workloads
    
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
      workload-type = "analytics"
    }
    
    tags = ["analytics-nodes"]
    
    disk_encryption_key = google_kms_crypto_key.reporting_data_key.id
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Service accounts
resource "google_service_account" "gke_nodes" {
  project      = google_project.reporting_project.project_id
  account_id   = "gke-reporting-nodes"
  display_name = "GKE Reporting Nodes"
}

resource "google_service_account" "reporting_engine" {
  project      = google_project.reporting_project.project_id
  account_id   = "reporting-engine"
  display_name = "Compliance Reporting Engine"
}

resource "google_service_account" "dashboard_service" {
  project      = google_project.reporting_project.project_id
  account_id   = "dashboard-service"
  display_name = "Dashboard Service Account"
}

resource "google_service_account" "evidence_collector" {
  project      = google_project.reporting_project.project_id
  account_id   = "evidence-collector"
  display_name = "Evidence Collection Service"
}

# IAM bindings
resource "google_project_iam_binding" "reporting_engine_permissions" {
  project = google_project.reporting_project.project_id
  role    = "roles/bigquery.dataEditor"
  
  members = [
    "serviceAccount:${google_service_account.reporting_engine.email}",
  ]
}

resource "google_project_iam_binding" "dashboard_permissions" {
  project = google_project.reporting_project.project_id
  role    = "roles/bigquery.dataViewer"
  
  members = [
    "serviceAccount:${google_service_account.dashboard_service.email}",
  ]
}

# Custom IAM roles
resource "google_project_iam_custom_role" "compliance_reporter" {
  project     = google_project.reporting_project.project_id
  role_id     = "compliance_reporter"
  title       = "Compliance Reporter"
  description = "Generate and manage compliance reports"
  
  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.list",
    "bigquery.tables.getData",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.create",
    "monitoring.dashboards.get",
    "monitoring.dashboards.list",
  ]
}

resource "google_project_iam_custom_role" "evidence_manager" {
  project     = google_project.reporting_project.project_id
  role_id     = "evidence_manager"
  title       = "Evidence Manager"
  description = "Collect and manage compliance evidence"
  
  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.list",
    "bigquery.tables.getData",
    "bigquery.tables.update",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.create",
    "storage.objects.update",
    "logging.logs.list",
    "logging.logEntries.list",
  ]
}

# Cloud Storage for reports and evidence
resource "google_storage_bucket" "compliance_reports" {
  project  = google_project.reporting_project.project_id
  name     = "${var.project_id}-compliance-reports-${var.reporting_environment}"
  location = var.region
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  encryption {
    default_kms_key_name = google_kms_crypto_key.reporting_data_key.id
  }
  
  lifecycle_rule {
    condition {
      age = 2555  # 7 years retention
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
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  
  labels = {
    purpose = "compliance-reports"
  }
}

resource "google_storage_bucket" "evidence_repository" {
  project  = google_project.reporting_project.project_id
  name     = "${var.project_id}-evidence-repository-${var.reporting_environment}"
  location = var.region
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  encryption {
    default_kms_key_name = google_kms_crypto_key.reporting_data_key.id
  }
  
  lifecycle_rule {
    condition {
      age = 2555  # 7 years retention for audit evidence
    }
    action {
      type = "Delete"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }
  
  labels = {
    purpose = "evidence-repository"
  }
}

# Pub/Sub for real-time reporting
resource "google_pubsub_topic" "compliance_events" {
  project = google_project.reporting_project.project_id
  name    = "compliance-events"
  
  kms_key_name = google_kms_crypto_key.reporting_data_key.id
}

resource "google_pubsub_topic" "reporting_requests" {
  project = google_project.reporting_project.project_id
  name    = "reporting-requests"
  
  kms_key_name = google_kms_crypto_key.reporting_data_key.id
}

resource "google_pubsub_topic" "evidence_updates" {
  project = google_project.reporting_project.project_id
  name    = "evidence-updates"
  
  kms_key_name = google_kms_crypto_key.reporting_data_key.id
}

# Pub/Sub subscriptions
resource "google_pubsub_subscription" "compliance_processor" {
  project = google_project.reporting_project.project_id
  name    = "compliance-processor"
  topic   = google_pubsub_topic.compliance_events.name
  
  ack_deadline_seconds = 600
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.reporting_dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_topic" "reporting_dead_letter" {
  project = google_project.reporting_project.project_id
  name    = "reporting-dead-letter"
  
  kms_key_name = google_kms_crypto_key.reporting_data_key.id
}

# Cloud Scheduler for automated reporting
resource "google_cloud_scheduler_job" "daily_compliance_summary" {
  project     = google_project.reporting_project.project_id
  region      = var.region
  name        = "daily-compliance-summary"
  description = "Generate daily compliance status summary"
  schedule    = "0 6 * * *"  # Daily at 6 AM
  time_zone   = "UTC"
  
  pubsub_target {
    topic_name = google_pubsub_topic.reporting_requests.id
    data = base64encode(jsonencode({
      report_type = "daily_summary"
      frameworks  = var.compliance_frameworks
      trigger     = "scheduled"
    }))
  }
}

resource "google_cloud_scheduler_job" "weekly_trend_analysis" {
  project     = google_project.reporting_project.project_id
  region      = var.region
  name        = "weekly-trend-analysis"
  description = "Generate weekly compliance trend analysis"
  schedule    = "0 7 * * 1"  # Weekly on Monday at 7 AM
  time_zone   = "UTC"
  
  pubsub_target {
    topic_name = google_pubsub_topic.reporting_requests.id
    data = base64encode(jsonencode({
      report_type = "trend_analysis"
      frameworks  = var.compliance_frameworks
      trigger     = "scheduled_weekly"
    }))
  }
}

resource "google_cloud_scheduler_job" "monthly_executive_report" {
  project     = google_project.reporting_project.project_id
  region      = var.region
  name        = "monthly-executive-report"
  description = "Generate monthly executive compliance report"
  schedule    = "0 8 1 * *"  # Monthly on 1st at 8 AM
  time_zone   = "UTC"
  
  pubsub_target {
    topic_name = google_pubsub_topic.reporting_requests.id
    data = base64encode(jsonencode({
      report_type = "executive_summary"
      frameworks  = var.compliance_frameworks
      trigger     = "scheduled_monthly"
    }))
  }
}

# Firebase for real-time dashboards
resource "google_firebase_project" "reporting_firebase" {
  project = google_project.reporting_project.project_id
  
  depends_on = [google_project_service.reporting_apis]
}

resource "google_firestore_database" "dashboard_state" {
  project     = google_project.reporting_project.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  
  depends_on = [google_firebase_project.reporting_firebase]
}

# Monitoring and alerting
resource "google_monitoring_alert_policy" "reporting_failure" {
  project      = google_project.reporting_project.project_id
  display_name = "Compliance Reporting Failure"
  description  = "Alert when compliance reporting fails"
  
  conditions {
    display_name = "Report Generation Failure"
    
    condition_threshold {
      filter         = "resource.type=\"cloud_function\""
      duration       = "300s"
      comparison     = "COMPARISON_GREATER_THAN"
      threshold_value = 0.1  # 10% failure rate
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.compliance_team_email.name,
    google_monitoring_notification_channel.compliance_team_pagerduty.name,
  ]
}

resource "google_monitoring_alert_policy" "evidence_collection_lag" {
  project      = google_project.reporting_project.project_id
  display_name = "Evidence Collection Lag"
  description  = "Alert when evidence collection is behind schedule"
  
  conditions {
    display_name = "Evidence Collection Delay"
    
    condition_threshold {
      filter         = "resource.type=\"global\""
      duration       = "3600s"  # 1 hour
      comparison     = "COMPARISON_GREATER_THAN"
      threshold_value = 24  # 24 hours behind
      
      aggregations {
        alignment_period   = "3600s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.compliance_team_email.name,
  ]
}

resource "google_monitoring_notification_channel" "compliance_team_email" {
  project      = google_project.reporting_project.project_id
  display_name = "Compliance Team Email"
  type         = "email"
  
  labels = {
    email_address = "compliance-team@company.com"
  }
}

resource "google_monitoring_notification_channel" "compliance_team_pagerduty" {
  project      = google_project.reporting_project.project_id
  display_name = "Compliance Team PagerDuty"
  type         = "pagerduty"
  
  labels = {
    service_key = var.pagerduty_service_key
  }
  
  sensitive_labels {
    service_key = var.pagerduty_service_key
  }
}

# Load balancer for dashboard access
resource "google_compute_global_address" "dashboard_ip" {
  project = google_project.reporting_project.project_id
  name    = "compliance-dashboard-ip"
}

# Firewall rules
resource "google_compute_firewall" "reporting_https" {
  project = google_project.reporting_project.project_id
  name    = "reporting-allow-https"
  network = google_compute_network.reporting_vpc.name
  
  description = "Allow HTTPS traffic to reporting dashboards"
  direction   = "INGRESS"
  priority    = 1000
  
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
  
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["dashboard-frontend"]
}

resource "google_compute_firewall" "reporting_internal" {
  project = google_project.reporting_project.project_id
  name    = "reporting-allow-internal"
  network = google_compute_network.reporting_vpc.name
  
  description = "Allow internal reporting traffic"
  direction   = "INGRESS"
  priority    = 1000
  
  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8080", "9090"]
  }
  
  source_ranges = ["10.50.0.0/24"]
  target_tags   = ["reporting-internal"]
}

# Outputs
output "reporting_project_id" {
  description = "Compliance reporting project ID"
  value       = google_project.reporting_project.project_id
}

output "reporting_cluster_name" {
  description = "Reporting GKE cluster name"
  value       = google_container_cluster.reporting_cluster.name
}

output "reporting_datasets" {
  description = "BigQuery datasets for compliance reporting"
  value = {
    reporting = google_bigquery_dataset.compliance_reporting.dataset_id
    evidence  = google_bigquery_dataset.compliance_evidence.dataset_id
  }
}

output "reporting_topics" {
  description = "Pub/Sub topics for compliance reporting"
  value = {
    compliance_events   = google_pubsub_topic.compliance_events.name
    reporting_requests  = google_pubsub_topic.reporting_requests.name
    evidence_updates    = google_pubsub_topic.evidence_updates.name
  }
}

output "reporting_buckets" {
  description = "Storage buckets for compliance reporting"
  value = {
    reports   = google_storage_bucket.compliance_reports.name
    evidence  = google_storage_bucket.evidence_repository.name
  }
}

output "reporting_service_accounts" {
  description = "Service accounts for compliance reporting"
  value = {
    reporting_engine   = google_service_account.reporting_engine.email
    dashboard_service  = google_service_account.dashboard_service.email
    evidence_collector = google_service_account.evidence_collector.email
    gke_nodes         = google_service_account.gke_nodes.email
  }
}

output "dashboard_ip" {
  description = "Global IP address for compliance dashboards"
  value       = google_compute_global_address.dashboard_ip.address
}

output "firebase_project_id" {
  description = "Firebase project ID for real-time dashboards"
  value       = google_firebase_project.reporting_firebase.project
}

# Variables
variable "pagerduty_service_key" {
  description = "PagerDuty service key for compliance alerts"
  type        = string
  sensitive   = true
}