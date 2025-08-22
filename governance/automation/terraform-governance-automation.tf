# Governance Automation Infrastructure
# Policy-as-Code and automated compliance platform

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID for governance automation"
  type        = string
}

variable "region" {
  description = "Primary region for governance automation resources"
  type        = string
  default     = "us-central1"
}

variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "billing_account" {
  description = "Billing account for governance automation"
  type        = string
}

variable "governance_environment" {
  description = "Governance automation environment type"
  type        = string
  default     = "production"
  
  validation {
    condition = contains(["development", "staging", "production"], var.governance_environment)
    error_message = "Governance environment must be development, staging, or production."
  }
}

# Governance Automation Project
resource "google_project" "governance_automation_project" {
  name            = "governance-automation-${var.governance_environment}"
  project_id      = var.project_id
  billing_account = var.billing_account
  org_id         = var.organization_id
  
  labels = {
    environment = var.governance_environment
    purpose    = "governance-automation"
    automation = "policy-as-code"
    criticality = "critical"
  }
}

# Enable required APIs
resource "google_project_service" "governance_apis" {
  project = google_project.governance_automation_project.project_id
  
  for_each = toset([
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudkms.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
    "dataflow.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "orgpolicy.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "storage.googleapis.com"
  ])
  
  service = each.value
  disable_dependent_services = true
}

# Secure VPC for governance automation
resource "google_compute_network" "governance_vpc" {
  project                 = google_project.governance_automation_project.project_id
  name                    = "governance-automation-vpc-${var.governance_environment}"
  auto_create_subnetworks = false
  description             = "Secure VPC for governance automation infrastructure"
  
  depends_on = [google_project_service.governance_apis]
}

resource "google_compute_subnetwork" "governance_subnet" {
  project       = google_project.governance_automation_project.project_id
  name          = "governance-automation-subnet-${var.region}"
  ip_cidr_range = "10.30.0.0/24"
  region        = var.region
  network       = google_compute_network.governance_vpc.name
  
  private_ip_google_access = true
  
  log_config {
    aggregation_interval = "INTERVAL_1_MIN"
    flow_sampling       = 1.0
    metadata           = "INCLUDE_ALL_METADATA"
  }
  
  secondary_ip_range {
    range_name    = "governance-pods"
    ip_cidr_range = "10.31.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "governance-services"
    ip_cidr_range = "10.32.0.0/16"
  }
}

# KMS for governance data encryption
resource "google_kms_key_ring" "governance_keyring" {
  project  = google_project.governance_automation_project.project_id
  name     = "governance-automation-keyring-${var.governance_environment}"
  location = var.region
  
  depends_on = [google_project_service.governance_apis]
}

resource "google_kms_crypto_key" "governance_data_key" {
  name     = "governance-data-encryption-key"
  key_ring = google_kms_key_ring.governance_keyring.id
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

# GKE Cluster for policy engine and automation services
resource "google_container_cluster" "governance_cluster" {
  project  = google_project.governance_automation_project.project_id
  name     = "governance-automation-cluster"
  location = var.region
  
  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.governance_vpc.name
  subnetwork = google_compute_subnetwork.governance_subnet.name
  
  # Security configurations
  workload_identity_config {
    workload_pool = "${google_project.governance_automation_project.project_id}.svc.id.goog"
  }
  
  network_policy {
    enabled = true
  }
  
  database_encryption {
    state    = "ENCRYPTED"
    key_name = google_kms_crypto_key.governance_data_key.id
  }
  
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }
  
  ip_allocation_policy {
    cluster_secondary_range_name  = "governance-pods"
    services_secondary_range_name = "governance-services"
  }
  
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }
  
  enable_shielded_nodes = true
  enable_legacy_abac   = false
  
  depends_on = [google_project_service.governance_apis]
}

# Node pools for different workload types
resource "google_container_node_pool" "policy_engine_nodes" {
  project    = google_project.governance_automation_project.project_id
  name       = "policy-engine-pool"
  location   = var.region
  cluster    = google_container_cluster.governance_cluster.name
  node_count = 3
  
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
      workload-type = "policy-engine"
    }
    
    tags = ["policy-engine"]
    
    disk_encryption_key = google_kms_crypto_key.governance_data_key.id
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

resource "google_container_node_pool" "automation_nodes" {
  project    = google_project.governance_automation_project.project_id
  name       = "automation-pool"
  location   = var.region
  cluster    = google_container_cluster.governance_cluster.name
  
  autoscaling {
    min_node_count = 2
    max_node_count = 10
  }
  
  node_config {
    machine_type = "e2-standard-8"
    
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
      workload-type = "automation-workers"
    }
    
    tags = ["automation-workers"]
    
    disk_encryption_key = google_kms_crypto_key.governance_data_key.id
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Service accounts for governance automation
resource "google_service_account" "gke_nodes" {
  project      = google_project.governance_automation_project.project_id
  account_id   = "gke-governance-nodes"
  display_name = "GKE Governance Automation Nodes"
}

resource "google_service_account" "policy_engine" {
  project      = google_project.governance_automation_project.project_id
  account_id   = "policy-engine"
  display_name = "Policy Engine Service Account"
}

resource "google_service_account" "automation_orchestrator" {
  project      = google_project.governance_automation_project.project_id
  account_id   = "automation-orchestrator"
  display_name = "Automation Orchestrator Service Account"
}

resource "google_service_account" "compliance_validator" {
  project      = google_project.governance_automation_project.project_id
  account_id   = "compliance-validator"
  display_name = "Compliance Validation Service Account"
}

# BigQuery for governance analytics and policy execution data
resource "google_bigquery_dataset" "governance_dataset" {
  project    = google_project.governance_automation_project.project_id
  dataset_id = "governance_automation"
  location   = var.region
  
  description                     = "Governance automation analytics and policy execution data"
  default_table_expiration_ms     = 31536000000  # 1 year
  default_partition_expiration_ms = 2592000000   # 30 days
  
  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.governance_data_key.id
  }
  
  labels = {
    purpose = "governance-analytics"
  }
}

# BigQuery tables for governance data
resource "google_bigquery_table" "policy_executions" {
  project    = google_project.governance_automation_project.project_id
  dataset_id = google_bigquery_dataset.governance_dataset.dataset_id
  table_id   = "policy_executions"
  
  time_partitioning {
    type  = "DAY"
    field = "execution_timestamp"
  }
  
  clustering = ["policy_id", "execution_result", "target_resource"]
  
  schema = <<EOF
[
  {
    "name": "execution_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "execution_timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  },
  {
    "name": "policy_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "policy_version",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "target_resource",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "resource_type",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "execution_result",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "ALLOW, DENY, or ERROR"
  },
  {
    "name": "violation_details",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "remediation_action",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "execution_duration_ms",
    "type": "INTEGER",
    "mode": "NULLABLE"
  },
  {
    "name": "policy_engine",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "compliance_frameworks",
    "type": "STRING",
    "mode": "REPEATED"
  }
]
EOF
}

resource "google_bigquery_table" "compliance_assessments" {
  project    = google_project.governance_automation_project.project_id
  dataset_id = google_bigquery_dataset.governance_dataset.dataset_id
  table_id   = "compliance_assessments"
  
  time_partitioning {
    type  = "DAY"
    field = "assessment_timestamp"
  }
  
  clustering = ["framework", "control_category", "assessment_result"]
  
  schema = <<EOF
[
  {
    "name": "assessment_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "assessment_timestamp",
    "type": "TIMESTAMP",
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
    "name": "control_category",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "target_scope",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "assessment_result",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "COMPLIANT, NON_COMPLIANT, or MANUAL_REVIEW"
  },
  {
    "name": "risk_score",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "evidence_artifacts",
    "type": "STRING",
    "mode": "REPEATED"
  },
  {
    "name": "remediation_required",
    "type": "BOOLEAN",
    "mode": "NULLABLE"
  },
  {
    "name": "automated_remediation",
    "type": "BOOLEAN",
    "mode": "NULLABLE"
  }
]
EOF
}

resource "google_bigquery_table" "risk_assessments" {
  project    = google_project.governance_automation_project.project_id
  dataset_id = google_bigquery_dataset.governance_dataset.dataset_id
  table_id   = "risk_assessments"
  
  time_partitioning {
    type  = "DAY"
    field = "assessment_timestamp"
  }
  
  clustering = ["risk_category", "risk_level", "asset_type"]
  
  schema = <<EOF
[
  {
    "name": "assessment_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "assessment_timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  },
  {
    "name": "asset_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "asset_type",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "risk_category",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "risk_level",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "probability_score",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "impact_score",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "overall_risk_score",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "threat_vectors",
    "type": "STRING",
    "mode": "REPEATED"
  },
  {
    "name": "existing_controls",
    "type": "STRING",
    "mode": "REPEATED"
  },
  {
    "name": "recommended_controls",
    "type": "STRING",
    "mode": "REPEATED"
  },
  {
    "name": "business_impact",
    "type": "STRING",
    "mode": "NULLABLE"
  }
]
EOF
}

# Firestore for policy repository and configuration
resource "google_firestore_database" "governance_db" {
  project     = google_project.governance_automation_project.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  
  depends_on = [google_project_service.governance_apis]
}

# Cloud Storage for policy artifacts and documentation
resource "google_storage_bucket" "policy_repository" {
  project  = google_project.governance_automation_project.project_id
  name     = "${var.project_id}-policy-repository-${var.governance_environment}"
  location = var.region
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  encryption {
    default_kms_key_name = google_kms_crypto_key.governance_data_key.id
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
    purpose = "policy-repository"
  }
}

resource "google_storage_bucket" "governance_artifacts" {
  project  = google_project.governance_automation_project.project_id
  name     = "${var.project_id}-governance-artifacts-${var.governance_environment}"
  location = var.region
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  encryption {
    default_kms_key_name = google_kms_crypto_key.governance_data_key.id
  }
  
  lifecycle_rule {
    condition {
      age = 180
    }
    action {
      type = "Delete"
    }
  }
  
  labels = {
    purpose = "governance-artifacts"
  }
}

# Pub/Sub topics for governance event processing
resource "google_pubsub_topic" "policy_events" {
  project = google_project.governance_automation_project.project_id
  name    = "policy-events"
  
  kms_key_name = google_kms_crypto_key.governance_data_key.id
  
  message_retention_duration = "604800s"  # 7 days
}

resource "google_pubsub_topic" "compliance_events" {
  project = google_project.governance_automation_project.project_id
  name    = "compliance-events"
  
  kms_key_name = google_kms_crypto_key.governance_data_key.id
  
  message_retention_duration = "604800s"  # 7 days
}

resource "google_pubsub_topic" "remediation_events" {
  project = google_project.governance_automation_project.project_id
  name    = "remediation-events"
  
  kms_key_name = google_kms_crypto_key.governance_data_key.id
  
  message_retention_duration = "604800s"  # 7 days
}

resource "google_pubsub_topic" "risk_events" {
  project = google_project.governance_automation_project.project_id
  name    = "risk-events"
  
  kms_key_name = google_kms_crypto_key.governance_data_key.id
  
  message_retention_duration = "604800s"  # 7 days
}

# Pub/Sub subscriptions for processing
resource "google_pubsub_subscription" "policy_processor" {
  project = google_project.governance_automation_project.project_id
  name    = "policy-processor"
  topic   = google_pubsub_topic.policy_events.name
  
  ack_deadline_seconds = 300
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.governance_dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_subscription" "compliance_processor" {
  project = google_project.governance_automation_project.project_id
  name    = "compliance-processor"
  topic   = google_pubsub_topic.compliance_events.name
  
  ack_deadline_seconds = 600  # Longer timeout for compliance processing
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.governance_dead_letter.id
    max_delivery_attempts = 3
  }
}

resource "google_pubsub_topic" "governance_dead_letter" {
  project = google_project.governance_automation_project.project_id
  name    = "governance-dead-letter"
  
  kms_key_name = google_kms_crypto_key.governance_data_key.id
}

# Cloud Scheduler for automated governance tasks
resource "google_cloud_scheduler_job" "daily_compliance_check" {
  project     = google_project.governance_automation_project.project_id
  region      = var.region
  name        = "daily-compliance-check"
  description = "Daily automated compliance assessment"
  schedule    = "0 2 * * *"  # Daily at 2 AM
  time_zone   = "UTC"
  
  pubsub_target {
    topic_name = google_pubsub_topic.compliance_events.id
    data = base64encode(jsonencode({
      task_type = "compliance_assessment"
      scope     = "organization_wide"
      trigger   = "scheduled_daily"
    }))
  }
}

resource "google_cloud_scheduler_job" "weekly_risk_assessment" {
  project     = google_project.governance_automation_project.project_id
  region      = var.region
  name        = "weekly-risk-assessment"
  description = "Weekly automated risk assessment"
  schedule    = "0 3 * * 1"  # Weekly on Monday at 3 AM
  time_zone   = "UTC"
  
  pubsub_target {
    topic_name = google_pubsub_topic.risk_events.id
    data = base64encode(jsonencode({
      task_type = "risk_assessment"
      scope     = "all_assets"
      trigger   = "scheduled_weekly"
    }))
  }
}

resource "google_cloud_scheduler_job" "monthly_policy_review" {
  project     = google_project.governance_automation_project.project_id
  region      = var.region
  name        = "monthly-policy-review"
  description = "Monthly automated policy effectiveness review"
  schedule    = "0 4 1 * *"  # Monthly on 1st at 4 AM
  time_zone   = "UTC"
  
  pubsub_target {
    topic_name = google_pubsub_topic.policy_events.id
    data = base64encode(jsonencode({
      task_type = "policy_review"
      scope     = "all_policies"
      trigger   = "scheduled_monthly"
    }))
  }
}

# IAM bindings for governance automation
resource "google_project_iam_binding" "policy_engine_permissions" {
  project = google_project.governance_automation_project.project_id
  role    = "roles/orgpolicy.policyViewer"
  
  members = [
    "serviceAccount:${google_service_account.policy_engine.email}",
  ]
}

resource "google_project_iam_binding" "automation_orchestrator_permissions" {
  project = google_project.governance_automation_project.project_id
  role    = "roles/resourcemanager.organizationViewer"
  
  members = [
    "serviceAccount:${google_service_account.automation_orchestrator.email}",
  ]
}

resource "google_project_iam_binding" "compliance_validator_permissions" {
  project = google_project.governance_automation_project.project_id
  role    = "roles/iam.securityReviewer"
  
  members = [
    "serviceAccount:${google_service_account.compliance_validator.email}",
  ]
}

# Custom IAM roles
resource "google_project_iam_custom_role" "governance_analyst" {
  project     = google_project.governance_automation_project.project_id
  role_id     = "governance_analyst"
  title       = "Governance Analyst"
  description = "Role for governance analysts to view and analyze governance data"
  
  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.list",
    "bigquery.tables.getData",
    "storage.objects.get",
    "storage.objects.list",
    "monitoring.dashboards.get",
    "monitoring.dashboards.list",
    "pubsub.subscriptions.consume",
  ]
}

resource "google_project_iam_custom_role" "policy_administrator" {
  project     = google_project.governance_automation_project.project_id
  role_id     = "policy_administrator"
  title       = "Policy Administrator"
  description = "Role for policy administrators to manage governance policies"
  
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
    "pubsub.topics.publish",
    "cloudfunctions.functions.invoke",
    "orgpolicy.policies.list",
    "orgpolicy.policies.get",
  ]
}

# Monitoring and alerting
resource "google_monitoring_alert_policy" "policy_violation_alert" {
  project      = google_project.governance_automation_project.project_id
  display_name = "Policy Violation Alert"
  description  = "Alert when policy violations are detected"
  
  conditions {
    display_name = "Policy Violation Rate"
    
    condition_threshold {
      filter         = "resource.type=\"global\""
      duration       = "300s"
      comparison     = "COMPARISON_GREATER_THAN"
      threshold_value = 10  # More than 10 violations in 5 minutes
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_COUNT"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.governance_team_email.name,
    google_monitoring_notification_channel.governance_team_slack.name,
  ]
  
  alert_strategy {
    auto_close = "3600s"  # 1 hour
  }
}

resource "google_monitoring_alert_policy" "compliance_failure_alert" {
  project      = google_project.governance_automation_project.project_id
  display_name = "Compliance Assessment Failure"
  description  = "Alert when compliance assessments fail"
  
  conditions {
    display_name = "Compliance Failure Rate"
    
    condition_threshold {
      filter         = "resource.type=\"cloud_function\""
      duration       = "600s"
      comparison     = "COMPARISON_GREATER_THAN"
      threshold_value = 0.05  # 5% failure rate
      
      aggregations {
        alignment_period   = "600s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.governance_team_email.name,
    google_monitoring_notification_channel.governance_team_pagerduty.name,
  ]
}

resource "google_monitoring_notification_channel" "governance_team_email" {
  project      = google_project.governance_automation_project.project_id
  display_name = "Governance Team Email"
  type         = "email"
  
  labels = {
    email_address = "governance-team@company.com"
  }
}

resource "google_monitoring_notification_channel" "governance_team_slack" {
  project      = google_project.governance_automation_project.project_id
  display_name = "Governance Team Slack"
  type         = "slack"
  
  labels = {
    channel_name = "#governance-alerts"
    url          = var.slack_webhook_url
  }
  
  sensitive_labels {
    url = var.slack_webhook_url
  }
}

resource "google_monitoring_notification_channel" "governance_team_pagerduty" {
  project      = google_project.governance_automation_project.project_id
  display_name = "Governance Team PagerDuty"
  type         = "pagerduty"
  
  labels = {
    service_key = var.pagerduty_service_key
  }
  
  sensitive_labels {
    service_key = var.pagerduty_service_key
  }
}

# Firewall rules for governance automation
resource "google_compute_firewall" "governance_internal_only" {
  project = google_project.governance_automation_project.project_id
  name    = "governance-internal-only"
  network = google_compute_network.governance_vpc.name
  
  description = "Allow internal governance automation traffic"
  direction   = "INGRESS"
  priority    = 1000
  
  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8080", "9090"]
  }
  
  source_ranges = ["10.30.0.0/24"]
  target_tags   = ["governance-automation"]
}

# Outputs
output "governance_project_id" {
  description = "Governance automation project ID"
  value       = google_project.governance_automation_project.project_id
}

output "governance_cluster_name" {
  description = "Governance automation GKE cluster name"
  value       = google_container_cluster.governance_cluster.name
}

output "governance_dataset_id" {
  description = "BigQuery governance dataset ID"
  value       = google_bigquery_dataset.governance_dataset.dataset_id
}

output "governance_topics" {
  description = "Pub/Sub topics for governance events"
  value = {
    policy_events      = google_pubsub_topic.policy_events.name
    compliance_events  = google_pubsub_topic.compliance_events.name
    remediation_events = google_pubsub_topic.remediation_events.name
    risk_events       = google_pubsub_topic.risk_events.name
  }
}

output "governance_buckets" {
  description = "Storage buckets for governance automation"
  value = {
    policy_repository    = google_storage_bucket.policy_repository.name
    governance_artifacts = google_storage_bucket.governance_artifacts.name
  }
}

output "governance_service_accounts" {
  description = "Governance automation service account emails"
  value = {
    policy_engine          = google_service_account.policy_engine.email
    automation_orchestrator = google_service_account.automation_orchestrator.email
    compliance_validator   = google_service_account.compliance_validator.email
    gke_nodes             = google_service_account.gke_nodes.email
  }
}

output "governance_vpc_name" {
  description = "Governance automation VPC network name"
  value       = google_compute_network.governance_vpc.name
}

# Variables
variable "slack_webhook_url" {
  description = "Slack webhook URL for governance alerts"
  type        = string
  sensitive   = true
}

variable "pagerduty_service_key" {
  description = "PagerDuty service key for governance alerts"
  type        = string
  sensitive   = true
}