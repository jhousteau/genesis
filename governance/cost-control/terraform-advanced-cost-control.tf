# Advanced Cost Control Infrastructure
# AI-driven cost optimization and automated enforcement platform

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID for advanced cost control"
  type        = string
}

variable "region" {
  description = "Primary region for cost control resources"
  type        = string
  default     = "us-central1"
}

variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "billing_account" {
  description = "Billing account for cost control projects"
  type        = string
}

variable "cost_environment" {
  description = "Cost control environment type"
  type        = string
  default     = "production"
  
  validation {
    condition = contains(["development", "staging", "production"], var.cost_environment)
    error_message = "Cost environment must be development, staging, or production."
  }
}

variable "optimization_target" {
  description = "Target cost reduction percentage"
  type        = number
  default     = 30
  
  validation {
    condition = var.optimization_target >= 10 && var.optimization_target <= 70
    error_message = "Optimization target must be between 10% and 70%."
  }
}

# Advanced Cost Control Project
resource "google_project" "cost_control_project" {
  name            = "cost-control-${var.cost_environment}"
  project_id      = var.project_id
  billing_account = var.billing_account
  org_id         = var.organization_id
  
  labels = {
    environment = var.cost_environment
    purpose    = "cost-optimization"
    automation = "ai-driven"
    criticality = "high"
  }
}

# Enable required APIs
resource "google_project_service" "cost_control_apis" {
  project = google_project.cost_control_project.project_id
  
  for_each = toset([
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "bigquerydatatransfer.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudkms.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
    "dataflow.googleapis.com",
    "datastore.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "pubsub.googleapis.com",
    "recommendationengine.googleapis.com",
    "recommender.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com"
  ])
  
  service = each.value
  disable_dependent_services = true
}

# VPC for cost control infrastructure
resource "google_compute_network" "cost_control_vpc" {
  project                 = google_project.cost_control_project.project_id
  name                    = "cost-control-vpc-${var.cost_environment}"
  auto_create_subnetworks = false
  description             = "VPC for advanced cost control infrastructure"
  
  depends_on = [google_project_service.cost_control_apis]
}

resource "google_compute_subnetwork" "cost_control_subnet" {
  project       = google_project.cost_control_project.project_id
  name          = "cost-control-subnet-${var.region}"
  ip_cidr_range = "10.40.0.0/24"
  region        = var.region
  network       = google_compute_network.cost_control_vpc.name
  
  private_ip_google_access = true
  
  log_config {
    aggregation_interval = "INTERVAL_1_MIN"
    flow_sampling       = 1.0
    metadata           = "INCLUDE_ALL_METADATA"
  }
  
  secondary_ip_range {
    range_name    = "cost-control-pods"
    ip_cidr_range = "10.41.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "cost-control-services"
    ip_cidr_range = "10.42.0.0/16"
  }
}

# KMS for cost control data encryption
resource "google_kms_key_ring" "cost_control_keyring" {
  project  = google_project.cost_control_project.project_id
  name     = "cost-control-keyring-${var.cost_environment}"
  location = var.region
  
  depends_on = [google_project_service.cost_control_apis]
}

resource "google_kms_crypto_key" "cost_data_key" {
  name     = "cost-data-encryption-key"
  key_ring = google_kms_key_ring.cost_control_keyring.id
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

# BigQuery for cost analytics and AI/ML
resource "google_bigquery_dataset" "cost_analytics" {
  project    = google_project.cost_control_project.project_id
  dataset_id = "cost_analytics"
  location   = var.region
  
  description = "Advanced cost analytics and AI/ML dataset"
  
  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.cost_data_key.id
  }
  
  labels = {
    purpose = "cost-analytics"
  }
}

resource "google_bigquery_dataset" "cost_ml" {
  project    = google_project.cost_control_project.project_id
  dataset_id = "cost_ml_models"
  location   = var.region
  
  description = "Cost optimization ML models and predictions"
  
  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.cost_data_key.id
  }
  
  labels = {
    purpose = "ml-models"
  }
}

# BigQuery tables for advanced cost analytics
resource "google_bigquery_table" "cost_forecasts" {
  project    = google_project.cost_control_project.project_id
  dataset_id = google_bigquery_dataset.cost_analytics.dataset_id
  table_id   = "cost_forecasts"
  
  time_partitioning {
    type  = "DAY"
    field = "forecast_date"
  }
  
  clustering = ["forecast_horizon", "resource_type", "forecast_accuracy"]
  
  schema = <<EOF
[
  {
    "name": "forecast_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "forecast_date",
    "type": "DATE",
    "mode": "REQUIRED"
  },
  {
    "name": "forecast_horizon",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "HOURLY, DAILY, WEEKLY, MONTHLY, QUARTERLY"
  },
  {
    "name": "resource_type",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "resource_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "predicted_cost",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "confidence_interval_lower",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "confidence_interval_upper",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "model_used",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "model_version",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "forecast_accuracy",
    "type": "FLOAT",
    "mode": "NULLABLE"
  },
  {
    "name": "contributing_factors",
    "type": "STRING",
    "mode": "REPEATED"
  }
]
EOF
}

resource "google_bigquery_table" "cost_anomalies" {
  project    = google_project.cost_control_project.project_id
  dataset_id = google_bigquery_dataset.cost_analytics.dataset_id
  table_id   = "cost_anomalies"
  
  time_partitioning {
    type  = "DAY"
    field = "detection_timestamp"
  }
  
  clustering = ["anomaly_type", "severity", "resolution_status"]
  
  schema = <<EOF
[
  {
    "name": "anomaly_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "detection_timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  },
  {
    "name": "anomaly_type",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "COST_SPIKE, USAGE_ANOMALY, BILLING_IRREGULARITY"
  },
  {
    "name": "affected_resource",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "resource_type",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "severity",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "LOW, MEDIUM, HIGH, CRITICAL"
  },
  {
    "name": "anomaly_score",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "expected_cost",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "actual_cost",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "cost_deviation_percent",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "root_cause_analysis",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "resolution_status",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "DETECTED, INVESTIGATING, RESOLVED, FALSE_POSITIVE"
  },
  {
    "name": "automated_action_taken",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "resolution_timestamp",
    "type": "TIMESTAMP",
    "mode": "NULLABLE"
  }
]
EOF
}

resource "google_bigquery_table" "optimization_recommendations" {
  project    = google_project.cost_control_project.project_id
  dataset_id = google_bigquery_dataset.cost_analytics.dataset_id
  table_id   = "optimization_recommendations"
  
  time_partitioning {
    type  = "DAY"
    field = "recommendation_date"
  }
  
  clustering = ["recommendation_type", "priority", "implementation_status"]
  
  schema = <<EOF
[
  {
    "name": "recommendation_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "recommendation_date",
    "type": "DATE",
    "mode": "REQUIRED"
  },
  {
    "name": "recommendation_type",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "RIGHT_SIZE, COMMITMENT, WASTE_ELIMINATION, WORKLOAD_PLACEMENT"
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
    "name": "current_cost",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "optimized_cost",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "potential_savings",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "savings_percentage",
    "type": "FLOAT",
    "mode": "REQUIRED"
  },
  {
    "name": "priority",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "LOW, MEDIUM, HIGH, CRITICAL"
  },
  {
    "name": "implementation_complexity",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "LOW, MEDIUM, HIGH"
  },
  {
    "name": "risk_assessment",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "LOW, MEDIUM, HIGH"
  },
  {
    "name": "implementation_status",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "PENDING, IN_PROGRESS, COMPLETED, REJECTED"
  },
  {
    "name": "automated_implementation",
    "type": "BOOLEAN",
    "mode": "REQUIRED"
  },
  {
    "name": "implementation_timeline",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "business_impact_assessment",
    "type": "STRING",
    "mode": "NULLABLE"
  }
]
EOF
}

# GKE cluster for ML and optimization workloads
resource "google_container_cluster" "cost_optimization_cluster" {
  project  = google_project.cost_control_project.project_id
  name     = "cost-optimization-cluster"
  location = var.region
  
  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.cost_control_vpc.name
  subnetwork = google_compute_subnetwork.cost_control_subnet.name
  
  workload_identity_config {
    workload_pool = "${google_project.cost_control_project.project_id}.svc.id.goog"
  }
  
  network_policy {
    enabled = true
  }
  
  database_encryption {
    state    = "ENCRYPTED"
    key_name = google_kms_crypto_key.cost_data_key.id
  }
  
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }
  
  ip_allocation_policy {
    cluster_secondary_range_name  = "cost-control-pods"
    services_secondary_range_name = "cost-control-services"
  }
  
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }
  
  enable_shielded_nodes = true
  enable_legacy_abac   = false
  
  depends_on = [google_project_service.cost_control_apis]
}

# ML-optimized node pool
resource "google_container_node_pool" "ml_nodes" {
  project    = google_project.cost_control_project.project_id
  name       = "ml-node-pool"
  location   = var.region
  cluster    = google_container_cluster.cost_optimization_cluster.name
  
  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }
  
  node_config {
    machine_type = "n1-highmem-8"  # Optimized for ML workloads
    
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
      workload-type = "ml-optimization"
    }
    
    tags = ["ml-nodes"]
    
    # Attach GPUs for ML training
    guest_accelerator {
      type  = "nvidia-tesla-t4"
      count = 1
    }
    
    disk_encryption_key = google_kms_crypto_key.cost_data_key.id
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Cost optimization node pool
resource "google_container_node_pool" "optimization_nodes" {
  project    = google_project.cost_control_project.project_id
  name       = "optimization-node-pool"
  location   = var.region
  cluster    = google_container_cluster.cost_optimization_cluster.name
  
  autoscaling {
    min_node_count = 2
    max_node_count = 20
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
      workload-type = "cost-optimization"
    }
    
    tags = ["optimization-nodes"]
    
    disk_encryption_key = google_kms_crypto_key.cost_data_key.id
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Service accounts
resource "google_service_account" "gke_nodes" {
  project      = google_project.cost_control_project.project_id
  account_id   = "gke-cost-control-nodes"
  display_name = "GKE Cost Control Nodes"
}

resource "google_service_account" "cost_optimizer" {
  project      = google_project.cost_control_project.project_id
  account_id   = "cost-optimizer"
  display_name = "Cost Optimization Service Account"
}

resource "google_service_account" "ml_training" {
  project      = google_project.cost_control_project.project_id
  account_id   = "ml-training"
  display_name = "ML Training Service Account"
}

resource "google_service_account" "budget_enforcer" {
  project      = google_project.cost_control_project.project_id
  account_id   = "budget-enforcer"
  display_name = "Budget Enforcement Service Account"
}

# IAM bindings for cost control
resource "google_project_iam_binding" "cost_optimizer_permissions" {
  project = google_project.cost_control_project.project_id
  role    = "roles/compute.instanceAdmin"
  
  members = [
    "serviceAccount:${google_service_account.cost_optimizer.email}",
  ]
}

resource "google_project_iam_binding" "billing_permissions" {
  project = google_project.cost_control_project.project_id
  role    = "roles/billing.viewer"
  
  members = [
    "serviceAccount:${google_service_account.cost_optimizer.email}",
    "serviceAccount:${google_service_account.budget_enforcer.email}",
  ]
}

resource "google_project_iam_binding" "ml_training_permissions" {
  project = google_project.cost_control_project.project_id
  role    = "roles/aiplatform.user"
  
  members = [
    "serviceAccount:${google_service_account.ml_training.email}",
  ]
}

# Custom IAM roles
resource "google_project_iam_custom_role" "cost_optimization_admin" {
  project     = google_project.cost_control_project.project_id
  role_id     = "cost_optimization_admin"
  title       = "Cost Optimization Administrator"
  description = "Full access to cost optimization systems and data"
  
  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.list",
    "bigquery.tables.getData",
    "bigquery.tables.update",
    "bigquery.tables.create",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.create",
    "storage.objects.update",
    "compute.instances.get",
    "compute.instances.list",
    "compute.instances.start",
    "compute.instances.stop",
    "compute.instances.setMachineType",
    "recommender.computeInstanceMachineTypeRecommendations.get",
    "recommender.computeInstanceMachineTypeRecommendations.list",
    "billing.budgets.get",
    "billing.budgets.list",
    "monitoring.alertPolicies.get",
    "monitoring.alertPolicies.list",
    "monitoring.alertPolicies.create",
    "monitoring.alertPolicies.update",
  ]
}

resource "google_project_iam_custom_role" "cost_analyst" {
  project     = google_project.cost_control_project.project_id
  role_id     = "cost_analyst"
  title       = "Cost Analyst"
  description = "Read-only access to cost optimization data and analytics"
  
  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.list",
    "bigquery.tables.getData",
    "storage.objects.get",
    "storage.objects.list",
    "monitoring.dashboards.get",
    "monitoring.dashboards.list",
    "billing.budgets.get",
    "billing.budgets.list",
  ]
}

# Pub/Sub topics for cost optimization events
resource "google_pubsub_topic" "cost_anomalies" {
  project = google_project.cost_control_project.project_id
  name    = "cost-anomalies"
  
  kms_key_name = google_kms_crypto_key.cost_data_key.id
}

resource "google_pubsub_topic" "optimization_recommendations" {
  project = google_project.cost_control_project.project_id
  name    = "optimization-recommendations"
  
  kms_key_name = google_kms_crypto_key.cost_data_key.id
}

resource "google_pubsub_topic" "budget_alerts" {
  project = google_project.cost_control_project.project_id
  name    = "budget-alerts"
  
  kms_key_name = google_kms_crypto_key.cost_data_key.id
}

# Pub/Sub subscriptions
resource "google_pubsub_subscription" "anomaly_processor" {
  project = google_project.cost_control_project.project_id
  name    = "anomaly-processor"
  topic   = google_pubsub_topic.cost_anomalies.name
  
  ack_deadline_seconds = 300
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.cost_dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_subscription" "optimization_executor" {
  project = google_project.cost_control_project.project_id
  name    = "optimization-executor"
  topic   = google_pubsub_topic.optimization_recommendations.name
  
  ack_deadline_seconds = 600  # Longer timeout for optimization actions
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.cost_dead_letter.id
    max_delivery_attempts = 3
  }
}

resource "google_pubsub_topic" "cost_dead_letter" {
  project = google_project.cost_control_project.project_id
  name    = "cost-dead-letter"
  
  kms_key_name = google_kms_crypto_key.cost_data_key.id
}

# Cloud Storage for ML models and optimization data
resource "google_storage_bucket" "ml_models" {
  project  = google_project.cost_control_project.project_id
  name     = "${var.project_id}-cost-ml-models-${var.cost_environment}"
  location = var.region
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  encryption {
    default_kms_key_name = google_kms_crypto_key.cost_data_key.id
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
  
  labels = {
    purpose = "ml-models"
  }
}

resource "google_storage_bucket" "optimization_data" {
  project  = google_project.cost_control_project.project_id
  name     = "${var.project_id}-optimization-data-${var.cost_environment}"
  location = var.region
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  encryption {
    default_kms_key_name = google_kms_crypto_key.cost_data_key.id
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
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  
  labels = {
    purpose = "optimization-data"
  }
}

# Cloud Scheduler for automated cost optimization tasks
resource "google_cloud_scheduler_job" "hourly_cost_analysis" {
  project     = google_project.cost_control_project.project_id
  region      = var.region
  name        = "hourly-cost-analysis"
  description = "Hourly cost analysis and anomaly detection"
  schedule    = "0 * * * *"  # Every hour
  time_zone   = "UTC"
  
  pubsub_target {
    topic_name = google_pubsub_topic.cost_anomalies.id
    data = base64encode(jsonencode({
      analysis_type = "anomaly_detection"
      scope         = "organization"
      trigger       = "scheduled_hourly"
    }))
  }
}

resource "google_cloud_scheduler_job" "daily_optimization" {
  project     = google_project.cost_control_project.project_id
  region      = var.region
  name        = "daily-optimization-analysis"
  description = "Daily optimization recommendation generation"
  schedule    = "0 1 * * *"  # Daily at 1 AM
  time_zone   = "UTC"
  
  pubsub_target {
    topic_name = google_pubsub_topic.optimization_recommendations.id
    data = base64encode(jsonencode({
      analysis_type = "optimization_recommendations"
      scope         = "all_resources"
      trigger       = "scheduled_daily"
      target_reduction = var.optimization_target
    }))
  }
}

resource "google_cloud_scheduler_job" "weekly_ml_training" {
  project     = google_project.cost_control_project.project_id
  region      = var.region
  name        = "weekly-ml-model-training"
  description = "Weekly ML model retraining for cost optimization"
  schedule    = "0 2 * * 1"  # Weekly on Monday at 2 AM
  time_zone   = "UTC"
  
  pubsub_target {
    topic_name = google_pubsub_topic.optimization_recommendations.id
    data = base64encode(jsonencode({
      analysis_type = "ml_model_training"
      models        = ["forecasting", "anomaly_detection", "optimization"]
      trigger       = "scheduled_weekly"
    }))
  }
}

# Cloud Functions for cost optimization automation
resource "google_storage_bucket" "function_source" {
  project  = google_project.cost_control_project.project_id
  name     = "${var.project_id}-cost-functions-${var.cost_environment}"
  location = var.region
  
  uniform_bucket_level_access = true
}

# Monitoring and alerting for cost optimization
resource "google_monitoring_alert_policy" "high_cost_anomaly" {
  project      = google_project.cost_control_project.project_id
  display_name = "High Cost Anomaly Detected"
  description  = "Alert when high-severity cost anomalies are detected"
  
  conditions {
    display_name = "High Cost Anomaly"
    
    condition_threshold {
      filter         = "resource.type=\"global\""
      duration       = "300s"
      comparison     = "COMPARISON_GREATER_THAN"
      threshold_value = 1000  # $1000 anomaly
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.cost_team_email.name,
    google_monitoring_notification_channel.cost_team_pagerduty.name,
  ]
  
  alert_strategy {
    auto_close = "3600s"  # 1 hour
  }
}

resource "google_monitoring_alert_policy" "budget_threshold_alert" {
  project      = google_project.cost_control_project.project_id
  display_name = "Budget Threshold Exceeded"
  description  = "Alert when budget thresholds are exceeded"
  
  conditions {
    display_name = "Budget Threshold"
    
    condition_threshold {
      filter         = "resource.type=\"billing_account\""
      duration       = "60s"
      comparison     = "COMPARISON_GREATER_THAN"
      threshold_value = 0.8  # 80% of budget
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.cost_team_email.name,
    google_monitoring_notification_channel.finance_team_email.name,
  ]
}

resource "google_monitoring_alert_policy" "optimization_failure" {
  project      = google_project.cost_control_project.project_id
  display_name = "Cost Optimization Failure"
  description  = "Alert when cost optimization processes fail"
  
  conditions {
    display_name = "Optimization Process Failure"
    
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
    google_monitoring_notification_channel.cost_team_email.name,
  ]
}

resource "google_monitoring_notification_channel" "cost_team_email" {
  project      = google_project.cost_control_project.project_id
  display_name = "Cost Team Email"
  type         = "email"
  
  labels = {
    email_address = "cost-team@company.com"
  }
}

resource "google_monitoring_notification_channel" "finance_team_email" {
  project      = google_project.cost_control_project.project_id
  display_name = "Finance Team Email"
  type         = "email"
  
  labels = {
    email_address = "finance-team@company.com"
  }
}

resource "google_monitoring_notification_channel" "cost_team_pagerduty" {
  project      = google_project.cost_control_project.project_id
  display_name = "Cost Team PagerDuty"
  type         = "pagerduty"
  
  labels = {
    service_key = var.pagerduty_service_key
  }
  
  sensitive_labels {
    service_key = var.pagerduty_service_key
  }
}

# Firewall rules
resource "google_compute_firewall" "cost_control_internal" {
  project = google_project.cost_control_project.project_id
  name    = "cost-control-internal"
  network = google_compute_network.cost_control_vpc.name
  
  description = "Allow internal cost control traffic"
  direction   = "INGRESS"
  priority    = 1000
  
  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8080", "9090", "9100"]
  }
  
  source_ranges = ["10.40.0.0/24"]
  target_tags   = ["cost-control"]
}

# Outputs
output "cost_control_project_id" {
  description = "Cost control project ID"
  value       = google_project.cost_control_project.project_id
}

output "cost_optimization_cluster_name" {
  description = "Cost optimization GKE cluster name"
  value       = google_container_cluster.cost_optimization_cluster.name
}

output "cost_analytics_dataset_id" {
  description = "BigQuery cost analytics dataset ID"
  value       = google_bigquery_dataset.cost_analytics.dataset_id
}

output "cost_ml_dataset_id" {
  description = "BigQuery ML models dataset ID"
  value       = google_bigquery_dataset.cost_ml.dataset_id
}

output "cost_topics" {
  description = "Pub/Sub topics for cost control events"
  value = {
    anomalies       = google_pubsub_topic.cost_anomalies.name
    recommendations = google_pubsub_topic.optimization_recommendations.name
    budget_alerts   = google_pubsub_topic.budget_alerts.name
  }
}

output "cost_buckets" {
  description = "Storage buckets for cost control"
  value = {
    ml_models        = google_storage_bucket.ml_models.name
    optimization_data = google_storage_bucket.optimization_data.name
  }
}

output "cost_service_accounts" {
  description = "Cost control service account emails"
  value = {
    optimizer       = google_service_account.cost_optimizer.email
    ml_training     = google_service_account.ml_training.email
    budget_enforcer = google_service_account.budget_enforcer.email
    gke_nodes      = google_service_account.gke_nodes.email
  }
}

# Variables
variable "pagerduty_service_key" {
  description = "PagerDuty service key for cost control alerts"
  type        = string
  sensitive   = true
}