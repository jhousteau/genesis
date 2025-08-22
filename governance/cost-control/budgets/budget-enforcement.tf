# Budget Enforcement Terraform Module
# Comprehensive budget management and enforcement across cloud providers

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "billing_account" {
  description = "GCP Billing Account ID"
  type        = string
}

variable "project_budgets" {
  description = "Project-specific budget configurations"
  type = map(object({
    project_id        = string
    environment      = string
    annual_budget    = number
    currency         = string
    alert_thresholds = list(number)
    enforcement_type = string  # soft, hard, emergency
    notification_channels = list(string)
    auto_shutdown_enabled = bool
    cost_center = string
  }))
}

variable "notification_channels" {
  description = "Notification channels for budget alerts"
  type = map(object({
    type = string  # email, slack, pubsub, webhook
    endpoint = string
    severity_filter = list(string)
  }))
}

# Data sources
data "google_billing_account" "account" {
  billing_account = var.billing_account
}

data "google_project" "projects" {
  for_each   = var.project_budgets
  project_id = each.value.project_id
}

# Local calculations
locals {
  # Calculate monthly budgets from annual
  monthly_budgets = {
    for k, v in var.project_budgets : k => {
      amount = v.annual_budget / 12
      currency = v.currency
    }
  }
  
  # Standard alert thresholds
  default_thresholds = [0.5, 0.75, 0.9, 1.0, 1.1]
  
  # Budget alert rules
  budget_alerts = {
    for project_key, budget in var.project_budgets : project_key => [
      for threshold in coalesce(budget.alert_thresholds, local.default_thresholds) : {
        threshold = threshold
        severity = threshold < 0.8 ? "info" : threshold < 1.0 ? "warning" : "critical"
        enforcement_action = (
          threshold >= 1.1 && budget.enforcement_type == "emergency" ? "shutdown" :
          threshold >= 1.0 && budget.enforcement_type == "hard" ? "freeze" :
          "alert"
        )
      }
    ]
  }
}

# Google Cloud Budget Management
resource "google_billing_budget" "project_budgets" {
  for_each = var.project_budgets
  
  billing_account = var.billing_account
  display_name    = "${each.value.project_id}-${each.value.environment}-budget"
  
  # Budget amount
  amount {
    specified_amount {
      currency_code = each.value.currency
      units         = tostring(floor(local.monthly_budgets[each.key].amount))
      nanos        = floor((local.monthly_budgets[each.key].amount - floor(local.monthly_budgets[each.key].amount)) * 1000000000)
    }
  }
  
  # Budget filters
  budget_filter {
    projects = ["projects/${data.google_project.projects[each.key].number}"]
    
    # Calendar period (monthly)
    calendar_period = "MONTH"
    
    # Credit types to include
    credit_types_treatment = "INCLUDE_ALL_CREDITS"
    
    # Services filter (all services)
    services = []
    
    # Custom labels filter
    labels = {
      environment = each.value.environment
      cost_center = each.value.cost_center
    }
  }
  
  # Alert rules
  dynamic "threshold_rules" {
    for_each = local.budget_alerts[each.key]
    content {
      threshold_percent = threshold_rules.value.threshold
      spend_basis      = "CURRENT_SPEND"
      
      # Forecast-based alerts for early warning
      dynamic "threshold_rules" {
        for_each = threshold_rules.value.threshold < 1.0 ? [1] : []
        content {
          threshold_percent = threshold_rules.value.threshold * 0.8
          spend_basis      = "FORECASTED_SPEND"
        }
      }
    }
  }
  
  # All updates rule (monitors all threshold breaches)
  all_updates_rule {
    # Pub/Sub notification
    pubsub_topic = google_pubsub_topic.budget_alerts[each.key].id
    
    # Schema version
    schema_version = "1.0"
    
    # Monitoring notification channels
    monitoring_notification_channels = [
      for channel_key in each.value.notification_channels :
      google_monitoring_notification_channel.budget_channels[channel_key].id
      if contains(keys(google_monitoring_notification_channel.budget_channels), channel_key)
    ]
  }
}

# Pub/Sub topics for budget alerts
resource "google_pubsub_topic" "budget_alerts" {
  for_each = var.project_budgets
  
  name    = "${each.value.project_id}-${each.value.environment}-budget-alerts"
  project = each.value.project_id
  
  # Message retention
  message_retention_duration = "86400s"  # 24 hours
  
  # Labels
  labels = {
    environment = each.value.environment
    purpose     = "budget-monitoring"
    cost_center = each.value.cost_center
  }
}

# Pub/Sub subscriptions for budget alert processing
resource "google_pubsub_subscription" "budget_alert_processor" {
  for_each = var.project_budgets
  
  name    = "${each.value.project_id}-${each.value.environment}-budget-processor"
  topic   = google_pubsub_topic.budget_alerts[each.key].name
  project = each.value.project_id
  
  # Acknowledgment deadline
  ack_deadline_seconds = 300
  
  # Message retention
  message_retention_duration = "86400s"
  
  # Retry policy
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }
  
  # Dead letter policy
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.budget_dead_letters[each.key].id
    max_delivery_attempts = 5
  }
}

# Dead letter topics for failed budget alert processing
resource "google_pubsub_topic" "budget_dead_letters" {
  for_each = var.project_budgets
  
  name    = "${each.value.project_id}-${each.value.environment}-budget-dead-letters"
  project = each.value.project_id
  
  # Message retention
  message_retention_duration = "604800s"  # 7 days
  
  labels = {
    environment = each.value.environment
    purpose     = "budget-monitoring-dlq"
  }
}

# Monitoring notification channels
resource "google_monitoring_notification_channel" "budget_channels" {
  for_each = var.notification_channels
  
  display_name = "Budget Alert Channel - ${each.key}"
  type         = each.value.type == "email" ? "email" : each.value.type == "slack" ? "slack" : "webhook_tokenauth"
  
  labels = {
    email_address = each.value.type == "email" ? each.value.endpoint : null
    channel_name  = each.value.type == "slack" ? each.value.endpoint : null
    url          = each.value.type == "webhook" ? each.value.endpoint : null
  }
  
  # User labels
  user_labels = {
    severity_filter = join(",", each.value.severity_filter)
  }
}

# Cloud Function for budget enforcement
resource "google_cloudfunctions_function" "budget_enforcer" {
  for_each = {
    for k, v in var.project_budgets : k => v
    if v.enforcement_type != "soft" && v.auto_shutdown_enabled
  }
  
  name                  = "${each.value.project_id}-${each.value.environment}-budget-enforcer"
  project              = each.value.project_id
  region               = "us-central1"
  runtime              = "python39"
  available_memory_mb  = 256
  timeout              = 300
  
  # Event trigger
  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.budget_alerts[each.key].name
  }
  
  # Source code
  source_archive_bucket = google_storage_bucket.budget_enforcer_code.name
  source_archive_object = google_storage_bucket_object.budget_enforcer_code.name
  
  # Environment variables
  environment_variables = {
    PROJECT_ID        = each.value.project_id
    ENVIRONMENT      = each.value.environment
    ENFORCEMENT_TYPE = each.value.enforcement_type
    BUDGET_AMOUNT    = local.monthly_budgets[each.key].amount
  }
  
  # Service account
  service_account_email = google_service_account.budget_enforcer[each.key].email
}

# Service account for budget enforcer
resource "google_service_account" "budget_enforcer" {
  for_each = {
    for k, v in var.project_budgets : k => v
    if v.enforcement_type != "soft" && v.auto_shutdown_enabled
  }
  
  account_id   = "${each.value.project_id}-budget-enforcer"
  project      = each.value.project_id
  display_name = "Budget Enforcer Service Account"
  description  = "Service account for automated budget enforcement"
}

# IAM bindings for budget enforcer
resource "google_project_iam_member" "budget_enforcer_compute" {
  for_each = {
    for k, v in var.project_budgets : k => v
    if v.enforcement_type != "soft" && v.auto_shutdown_enabled
  }
  
  project = each.value.project_id
  role    = "roles/compute.instanceAdmin"
  member  = "serviceAccount:${google_service_account.budget_enforcer[each.key].email}"
}

resource "google_project_iam_member" "budget_enforcer_run" {
  for_each = {
    for k, v in var.project_budgets : k => v
    if v.enforcement_type != "soft" && v.auto_shutdown_enabled
  }
  
  project = each.value.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.budget_enforcer[each.key].email}"
}

resource "google_project_iam_member" "budget_enforcer_functions" {
  for_each = {
    for k, v in var.project_budgets : k => v
    if v.enforcement_type != "soft" && v.auto_shutdown_enabled
  }
  
  project = each.value.project_id
  role    = "roles/cloudfunctions.admin"
  member  = "serviceAccount:${google_service_account.budget_enforcer[each.key].email}"
}

# Storage for budget enforcer source code
resource "google_storage_bucket" "budget_enforcer_code" {
  name          = "${var.organization_id}-budget-enforcer-code"
  location      = "US"
  storage_class = "STANDARD"
  
  # Lifecycle management
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
  
  # Versioning
  versioning {
    enabled = true
  }
}

# Budget enforcer source code
resource "google_storage_bucket_object" "budget_enforcer_code" {
  name   = "budget-enforcer-${formatdate("YYYY-MM-DD-hhmm", timestamp())}.zip"
  bucket = google_storage_bucket.budget_enforcer_code.name
  source = "${path.module}/budget_enforcer.zip"
}

# Cost anomaly detection using BigQuery
resource "google_bigquery_dataset" "cost_analytics" {
  dataset_id    = "cost_analytics"
  friendly_name = "Cost Analytics Dataset"
  description   = "Dataset for cost monitoring and anomaly detection"
  location      = "US"
  
  # Access control
  access {
    role          = "OWNER"
    user_by_email = "finance-team@whitehorse.ai"
  }
  
  access {
    role          = "READER"
    user_by_email = "operations-team@whitehorse.ai"
  }
  
  # Default table expiration
  default_table_expiration_ms = 31536000000  # 1 year
  
  labels = {
    environment = "shared"
    purpose     = "cost-analytics"
  }
}

# Scheduled queries for cost analysis
resource "google_bigquery_data_transfer_config" "cost_analysis" {
  display_name           = "Daily Cost Analysis"
  data_source_id        = "scheduled_query"
  location              = "US"
  schedule              = "every day 06:00"
  destination_dataset_id = google_bigquery_dataset.cost_analytics.dataset_id
  
  params = {
    query = templatefile("${path.module}/queries/daily_cost_analysis.sql", {
      billing_project = var.billing_account
    })
    destination_table_name_template = "daily_cost_analysis_{run_date|%Y%m%d}"
    write_disposition              = "WRITE_TRUNCATE"
  }
}

# Cloud Monitoring alerting policies for budget anomalies
resource "google_monitoring_alert_policy" "cost_anomaly" {
  for_each = var.project_budgets
  
  display_name = "${each.value.project_id} Cost Anomaly Detection"
  combiner     = "OR"
  
  conditions {
    display_name = "Cost Spike Detection"
    
    condition_threshold {
      filter          = "resource.type=\"billing_account\""
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = local.monthly_budgets[each.key].amount * 1.5  # 50% above budget
      duration        = "300s"
      
      aggregations {
        alignment_period   = "3600s"  # 1 hour
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  # Notification channels
  notification_channels = [
    for channel_key in each.value.notification_channels :
    google_monitoring_notification_channel.budget_channels[channel_key].id
    if contains(keys(google_monitoring_notification_channel.budget_channels), channel_key)
  ]
  
  # Alert strategy
  alert_strategy {
    auto_close = "1800s"  # 30 minutes
    
    notification_rate_limit {
      period = "300s"  # 5 minutes
    }
  }
  
  # Documentation
  documentation {
    content = "Cost anomaly detected for project ${each.value.project_id} in ${each.value.environment} environment. Current spend rate exceeds budget threshold."
  }
}

# Outputs
output "budget_ids" {
  description = "IDs of created budgets"
  value = {
    for k, v in google_billing_budget.project_budgets : k => v.name
  }
}

output "pubsub_topics" {
  description = "Pub/Sub topics for budget alerts"
  value = {
    for k, v in google_pubsub_topic.budget_alerts : k => v.id
  }
}

output "notification_channels" {
  description = "Monitoring notification channels"
  value = {
    for k, v in google_monitoring_notification_channel.budget_channels : k => v.id
  }
}

output "enforcer_functions" {
  description = "Budget enforcer Cloud Functions"
  value = {
    for k, v in google_cloudfunctions_function.budget_enforcer : k => v.name
  }
}

output "cost_analytics_dataset" {
  description = "BigQuery dataset for cost analytics"
  value = google_bigquery_dataset.cost_analytics.dataset_id
}