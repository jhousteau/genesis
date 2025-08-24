locals {
  # Generate a unique suffix if needed for bucket naming
  bucket_suffix = var.bucket_name

  # Default lifecycle rules for state management
  default_lifecycle_rules = var.enable_versioning ? [
    {
      action = {
        type = "Delete"
      }
      condition = {
        num_newer_versions = 10
        with_state         = "ARCHIVED"
      }
    },
    {
      action = {
        type = "Delete"
      }
      condition = {
        days_since_noncurrent_time = var.versioning_retain_days
        with_state                 = "ANY"
      }
    }
  ] : []

  # Enhanced lifecycle rules for cost optimization
  cost_optimized_lifecycle_rules = var.cost_optimization.enabled && var.cost_optimization.intelligent_tiering.enabled ? [
    {
      action = {
        type          = "SetStorageClass"
        storage_class = "COLDLINE"
      }
      condition = {
        age                   = var.cost_optimization.intelligent_tiering.coldline_threshold_days
        matches_storage_class = ["STANDARD", "NEARLINE"]
      }
    },
    {
      action = {
        type          = "SetStorageClass"
        storage_class = "ARCHIVE"
      }
      condition = {
        age                   = var.cost_optimization.intelligent_tiering.archive_threshold_days
        matches_storage_class = ["STANDARD", "NEARLINE", "COLDLINE"]
      }
    }
  ] : []

  # Merge all lifecycle rules
  lifecycle_rules = concat(
    local.default_lifecycle_rules,
    local.cost_optimized_lifecycle_rules,
    var.lifecycle_rules
  )

  # Determine if we need to create a logging bucket
  create_logging_bucket = var.logging_config == null
  log_bucket_name       = local.create_logging_bucket ? "${var.bucket_name}-logs" : var.logging_config.log_bucket
  log_object_prefix     = local.create_logging_bucket ? "access-logs/" : var.logging_config.log_object_prefix

  # Multi-region configuration
  all_regions = var.multi_region_config.enabled ? concat(
    [var.multi_region_config.primary_region],
    var.multi_region_config.secondary_regions
  ) : [var.location]

  # Enhanced security labels
  security_labels = var.enhanced_security.cmek_config.enabled ? {
    encryption_type = "cmek"
    key_rotation    = "enabled"
    security_level  = "enhanced"
    } : {
    encryption_type = "google_managed"
    security_level  = "standard"
  }

  # Compliance labels
  compliance_labels = var.compliance_config.enabled ? {
    compliance_frameworks = join(",", var.compliance_config.frameworks)
    data_classification   = var.compliance_config.data_classification
    retention_policy      = var.compliance_config.retention_compliance.deletion_policy
  } : {}

  # Merged labels
  all_labels = merge(
    var.labels,
    local.security_labels,
    local.compliance_labels,
    {
      multi_region      = var.multi_region_config.enabled
      disaster_recovery = var.disaster_recovery.enabled
      monitoring        = var.monitoring_config.enabled
      cost_optimized    = var.cost_optimization.enabled
    }
  )
}

# Random suffix for bucket naming uniqueness if needed
resource "random_id" "bucket_suffix" {
  count       = 0 # Set to 1 if you want to add random suffix
  byte_length = 4
}

# Logging bucket for access logs (if not provided)
resource "google_storage_bucket" "log_bucket" {
  count = local.create_logging_bucket ? 1 : 0

  name                        = local.log_bucket_name
  project                     = var.project_id
  location                    = var.location
  storage_class               = "STANDARD"
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90 # Delete logs after 90 days
    }
  }

  versioning {
    enabled = false
  }

  labels = merge(
    var.labels,
    {
      purpose = "access-logs"
      parent  = var.bucket_name
    }
  )
}

# Main state storage bucket
resource "google_storage_bucket" "state_bucket" {
  name                        = local.bucket_suffix
  project                     = var.project_id
  location                    = var.location
  storage_class               = var.enable_autoclass ? "STANDARD" : var.storage_class
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = var.enable_uniform_bucket_level_access
  public_access_prevention    = var.enable_public_access_prevention ? "enforced" : "inherited"

  # Versioning configuration
  versioning {
    enabled = var.enable_versioning
  }

  # Lifecycle rules
  dynamic "lifecycle_rule" {
    for_each = local.lifecycle_rules
    content {
      action {
        type          = lifecycle_rule.value.action.type
        storage_class = lookup(lifecycle_rule.value.action, "storage_class", null)
      }
      condition {
        age                        = lookup(lifecycle_rule.value.condition, "age", null)
        created_before             = lookup(lifecycle_rule.value.condition, "created_before", null)
        with_state                 = lookup(lifecycle_rule.value.condition, "with_state", null)
        matches_storage_class      = lookup(lifecycle_rule.value.condition, "matches_storage_class", null)
        matches_prefix             = lookup(lifecycle_rule.value.condition, "matches_prefix", null)
        matches_suffix             = lookup(lifecycle_rule.value.condition, "matches_suffix", null)
        num_newer_versions         = lookup(lifecycle_rule.value.condition, "num_newer_versions", null)
        days_since_noncurrent_time = lookup(lifecycle_rule.value.condition, "days_since_noncurrent_time", null)
        noncurrent_time_before     = lookup(lifecycle_rule.value.condition, "noncurrent_time_before", null)
      }
    }
  }

  # Retention policy
  dynamic "retention_policy" {
    for_each = var.retention_policy != null ? [var.retention_policy] : []
    content {
      retention_period = retention_policy.value.retention_period
      is_locked        = retention_policy.value.is_locked
    }
  }

  # CMEK encryption
  dynamic "encryption" {
    for_each = var.encryption_key_name != null ? [1] : []
    content {
      default_kms_key_name = var.encryption_key_name
    }
  }

  # CORS configuration
  dynamic "cors" {
    for_each = var.cors
    content {
      origin          = cors.value.origin
      method          = cors.value.method
      response_header = cors.value.response_header
      max_age_seconds = cors.value.max_age_seconds
    }
  }

  # Access logging
  dynamic "logging" {
    for_each = local.create_logging_bucket || var.logging_config != null ? [1] : []
    content {
      log_bucket        = local.create_logging_bucket ? google_storage_bucket.log_bucket[0].name : var.logging_config.log_bucket
      log_object_prefix = local.log_object_prefix
    }
  }

  # Autoclass configuration (2025 feature)
  dynamic "autoclass" {
    for_each = var.enable_autoclass ? [1] : []
    content {
      enabled                = true
      terminal_storage_class = var.autoclass_terminal_storage_class
    }
  }

  # Soft delete policy (2025 feature)
  dynamic "soft_delete_policy" {
    for_each = var.soft_delete_policy != null ? [var.soft_delete_policy] : []
    content {
      retention_duration_seconds = soft_delete_policy.value.retention_duration_seconds
    }
  }

  # Custom placement for dual-region buckets
  dynamic "custom_placement_config" {
    for_each = var.custom_placement_config != null ? [var.custom_placement_config] : []
    content {
      data_locations = custom_placement_config.value.data_locations
    }
  }

  labels = local.all_labels

  depends_on = [
    google_storage_bucket.log_bucket
  ]
}

# IAM binding for Terraform service account (optional, created separately)
resource "google_storage_bucket_iam_binding" "state_bucket_admin" {
  count = 0 # Enable this if you want to grant admin access to specific members

  bucket = google_storage_bucket.state_bucket.name
  role   = "roles/storage.admin"

  members = [
    # Add service account members here
    # "serviceAccount:terraform@${var.project_id}.iam.gserviceaccount.com"
  ]
}

# Create a backup bucket for state replication if configured
resource "google_storage_bucket" "replication_bucket" {
  count = var.replication_configuration != null ? 1 : 0

  name                        = var.replication_configuration.destination_bucket
  project                     = coalesce(var.replication_configuration.destination_project, var.project_id)
  location                    = var.location != "us-central1" ? "us-central1" : "us-east1" # Different region for replication
  storage_class               = var.storage_class
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = var.enable_uniform_bucket_level_access
  public_access_prevention    = var.enable_public_access_prevention ? "enforced" : "inherited"

  versioning {
    enabled = var.enable_versioning
  }

  # Apply same encryption if configured
  dynamic "encryption" {
    for_each = var.encryption_key_name != null ? [1] : []
    content {
      default_kms_key_name = var.encryption_key_name
    }
  }

  labels = merge(
    var.labels,
    {
      purpose = "terraform-state-replica"
      source  = var.bucket_name
    }
  )
}

# Transfer job for cross-region replication
resource "google_storage_transfer_job" "replication" {
  count = var.replication_configuration != null ? 1 : 0

  project     = var.project_id
  description = "Replication job for Terraform state bucket ${var.bucket_name}"

  transfer_spec {
    gcs_data_source {
      bucket_name = google_storage_bucket.state_bucket.name
    }

    gcs_data_sink {
      bucket_name = google_storage_bucket.replication_bucket[0].name
    }

    transfer_options {
      overwrite_objects_already_existing_in_sink = var.replication_configuration.rewrite_destination
      delete_objects_from_source_after_transfer  = false
      delete_objects_unique_in_sink              = var.replication_configuration.delete_marker_status
    }
  }

  schedule {
    schedule_start_date {
      year  = tonumber(formatdate("YYYY", timestamp()))
      month = tonumber(formatdate("MM", timestamp()))
      day   = tonumber(formatdate("DD", timestamp()))
    }

    start_time_of_day {
      hours   = 0
      minutes = 0
      seconds = 0
      nanos   = 0
    }

    repeat_interval = "3600s" # Run every hour
  }

  status = "ENABLED"
}

# Enhanced Multi-Region State Buckets
resource "google_storage_bucket" "multi_region_buckets" {
  for_each = {
    for region in var.multi_region_config.secondary_regions : region => region
    if var.multi_region_config.enabled
  }

  name                        = "${var.bucket_name}-${each.value}"
  project                     = var.project_id
  location                    = each.value
  storage_class               = var.enable_autoclass ? "STANDARD" : var.storage_class
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = var.enable_uniform_bucket_level_access
  public_access_prevention    = var.enable_public_access_prevention ? "enforced" : "inherited"

  # Versioning configuration
  versioning {
    enabled = var.enable_versioning
  }

  # Apply same lifecycle rules
  dynamic "lifecycle_rule" {
    for_each = local.lifecycle_rules
    content {
      action {
        type          = lifecycle_rule.value.action.type
        storage_class = lookup(lifecycle_rule.value.action, "storage_class", null)
      }
      condition {
        age                        = lookup(lifecycle_rule.value.condition, "age", null)
        created_before             = lookup(lifecycle_rule.value.condition, "created_before", null)
        with_state                 = lookup(lifecycle_rule.value.condition, "with_state", null)
        matches_storage_class      = lookup(lifecycle_rule.value.condition, "matches_storage_class", null)
        matches_prefix             = lookup(lifecycle_rule.value.condition, "matches_prefix", null)
        matches_suffix             = lookup(lifecycle_rule.value.condition, "matches_suffix", null)
        num_newer_versions         = lookup(lifecycle_rule.value.condition, "num_newer_versions", null)
        days_since_noncurrent_time = lookup(lifecycle_rule.value.condition, "days_since_noncurrent_time", null)
        noncurrent_time_before     = lookup(lifecycle_rule.value.condition, "noncurrent_time_before", null)
      }
    }
  }

  # CMEK encryption
  dynamic "encryption" {
    for_each = var.enhanced_security.cmek_config.enabled ? [1] : []
    content {
      default_kms_key_name = var.encryption_key_name
    }
  }

  labels = merge(
    var.labels,
    {
      purpose        = "terraform-state-replica"
      primary_region = var.multi_region_config.primary_region
      replica_region = each.value
    }
  )

  depends_on = [
    google_storage_bucket.state_bucket
  ]
}

# Enhanced KMS Key Ring for Multi-Region CMEK
resource "google_kms_key_ring" "state_keyring" {
  count = var.enhanced_security.cmek_config.enabled ? 1 : 0

  name     = "${var.bucket_name}-state-keyring"
  project  = var.project_id
  location = var.enhanced_security.cmek_config.key_ring_location
}

# Primary KMS Key for State Encryption
resource "google_kms_crypto_key" "state_key" {
  count = var.enhanced_security.cmek_config.enabled ? 1 : 0

  name     = "${var.bucket_name}-state-key"
  key_ring = google_kms_key_ring.state_keyring[0].id
  purpose  = "ENCRYPT_DECRYPT"

  rotation_period = var.enhanced_security.cmek_config.key_rotation_period

  lifecycle {
    prevent_destroy = true
  }
}

# Multi-Region KMS Keys for Regional Buckets
resource "google_kms_key_ring" "regional_keyrings" {
  for_each = {
    for region in var.multi_region_config.secondary_regions : region => region
    if var.multi_region_config.enabled && var.enhanced_security.cmek_config.enabled && var.enhanced_security.cmek_config.multi_region_keys
  }

  name     = "${var.bucket_name}-${each.value}-keyring"
  project  = var.project_id
  location = each.value
}

resource "google_kms_crypto_key" "regional_keys" {
  for_each = {
    for region in var.multi_region_config.secondary_regions : region => region
    if var.multi_region_config.enabled && var.enhanced_security.cmek_config.enabled && var.enhanced_security.cmek_config.multi_region_keys
  }

  name     = "${var.bucket_name}-${each.value}-key"
  key_ring = google_kms_key_ring.regional_keyrings[each.value].id
  purpose  = "ENCRYPT_DECRYPT"

  rotation_period = var.enhanced_security.cmek_config.key_rotation_period

  lifecycle {
    prevent_destroy = true
  }
}

# Backup KMS Key for Disaster Recovery
resource "google_kms_crypto_key" "backup_key" {
  count = var.enhanced_security.cmek_config.enabled && var.enhanced_security.cmek_config.backup_key_enabled ? 1 : 0

  name     = "${var.bucket_name}-backup-key"
  key_ring = google_kms_key_ring.state_keyring[0].id
  purpose  = "ENCRYPT_DECRYPT"

  rotation_period = var.enhanced_security.cmek_config.key_rotation_period

  lifecycle {
    prevent_destroy = true
  }
}

# Disaster Recovery Backup Buckets
resource "google_storage_bucket" "disaster_recovery_buckets" {
  for_each = {
    for region in var.disaster_recovery.cross_region_backup.target_regions : region => region
    if var.disaster_recovery.enabled && var.disaster_recovery.cross_region_backup.enabled
  }

  name                        = "${var.bucket_name}-dr-${each.value}"
  project                     = var.project_id
  location                    = each.value
  storage_class               = "COLDLINE" # Use coldline for cost-effective DR
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  # Extended retention for DR backups
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = var.disaster_recovery.retention_policy.yearly_backups * 365
    }
  }

  # CMEK encryption for DR backups
  dynamic "encryption" {
    for_each = var.disaster_recovery.cross_region_backup.encryption_key != null ? [1] : []
    content {
      default_kms_key_name = var.disaster_recovery.cross_region_backup.encryption_key
    }
  }

  labels = merge(
    var.labels,
    {
      purpose       = "disaster-recovery"
      backup_type   = "cross-region"
      source_bucket = var.bucket_name
      dr_region     = each.value
    }
  )
}

# Automated Disaster Recovery Transfer Jobs
resource "google_storage_transfer_job" "disaster_recovery" {
  for_each = {
    for region in var.disaster_recovery.cross_region_backup.target_regions : region => region
    if var.disaster_recovery.enabled && var.disaster_recovery.cross_region_backup.enabled
  }

  project     = var.project_id
  description = "Disaster recovery backup for ${var.bucket_name} to ${each.value}"

  transfer_spec {
    gcs_data_source {
      bucket_name = google_storage_bucket.state_bucket.name
    }

    gcs_data_sink {
      bucket_name = google_storage_bucket.disaster_recovery_buckets[each.value].name
    }

    transfer_options {
      overwrite_objects_already_existing_in_sink = true
      delete_objects_from_source_after_transfer  = false
      delete_objects_unique_in_sink              = false
    }
  }

  schedule {
    schedule_start_date {
      year  = tonumber(formatdate("YYYY", timestamp()))
      month = tonumber(formatdate("MM", timestamp()))
      day   = tonumber(formatdate("DD", timestamp()))
    }

    start_time_of_day {
      hours   = 2 # Run at 2 AM
      minutes = 0
      seconds = 0
      nanos   = 0
    }

    repeat_interval = "86400s" # Daily
  }

  status = "ENABLED"

  depends_on = [
    google_storage_bucket.disaster_recovery_buckets
  ]
}

# Cloud Scheduler for Backup Automation
resource "google_cloud_scheduler_job" "backup_scheduler" {
  count = var.disaster_recovery.enabled ? 1 : 0

  project     = var.project_id
  region      = var.location
  name        = "${var.bucket_name}-backup-scheduler"
  description = "Automated backup scheduler for ${var.bucket_name}"
  schedule    = var.disaster_recovery.backup_schedule
  time_zone   = "UTC"

  http_target {
    uri         = "https://storage.googleapis.com/storage/v1/b/${google_storage_bucket.state_bucket.name}/o"
    http_method = "GET"

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
      scope                 = "https://www.googleapis.com/auth/devstorage.read_write"
    }
  }
}

# Advanced Monitoring - Uptime Checks
resource "google_monitoring_uptime_check_config" "state_bucket_health" {
  count = var.monitoring_config.enabled && var.monitoring_config.health_checks.enabled ? 1 : 0

  project      = var.project_id
  display_name = "${var.bucket_name} Health Check"
  timeout      = "10s"
  period       = var.monitoring_config.health_checks.check_frequency

  http_check {
    path         = "/"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "storage.googleapis.com"
    }
  }

  content_matchers {
    content = google_storage_bucket.state_bucket.name
    matcher = "CONTAINS_STRING"
  }
}

# Custom Monitoring Metrics
resource "google_monitoring_metric_descriptor" "state_bucket_metrics" {
  for_each = {
    "state_operations" = {
      metric_kind = "GAUGE"
      value_type  = "INT64"
      description = "Number of state operations per minute"
    }
    "state_size" = {
      metric_kind = "GAUGE"
      value_type  = "INT64"
      description = "Total size of Terraform state in bytes"
    }
    "replication_lag" = {
      metric_kind = "GAUGE"
      value_type  = "DOUBLE"
      description = "Replication lag in seconds between regions"
    }
  }

  project      = var.project_id
  type         = "custom.googleapis.com/terraform/state/${each.key}"
  metric_kind  = each.value.metric_kind
  value_type   = each.value.value_type
  description  = each.value.description
  display_name = "Terraform State ${title(replace(each.key, "_", " "))}"

  dynamic "labels" {
    for_each = ["bucket_name", "region", "environment"]
    content {
      key         = labels.value
      value_type  = "STRING"
      description = "${title(labels.value)} label"
    }
  }
}

# Alert Policies for State Bucket Monitoring
resource "google_monitoring_alert_policy" "state_bucket_alerts" {
  for_each = {
    for policy in var.monitoring_config.alerting.alert_policies : policy.name => policy
    if var.monitoring_config.enabled && var.monitoring_config.alerting.enabled
  }

  project      = var.project_id
  display_name = "${var.bucket_name} - ${each.value.name}"
  description  = "Alert policy for Terraform state bucket monitoring"
  combiner     = "OR"

  conditions {
    display_name = each.value.name

    condition_threshold {
      filter          = each.value.condition
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = each.value.threshold

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = each.value.notification_channels

  alert_strategy {
    auto_close = "1800s"
  }
}

# Cloud Function for Advanced State Operations
resource "google_cloudfunctions_function" "state_operations" {
  count = var.disaster_recovery.enabled ? 1 : 0

  project = var.project_id
  region  = var.location
  name    = "${var.bucket_name}-state-operations"

  description         = "Advanced state operations for ${var.bucket_name}"
  available_memory_mb = 256
  timeout             = 540
  entry_point         = "handleStateOperation"
  runtime             = "python39"

  source_archive_bucket = google_storage_bucket.state_bucket.name
  source_archive_object = "state-operations.zip"

  environment_variables = {
    BUCKET_NAME        = google_storage_bucket.state_bucket.name
    PROJECT_ID         = var.project_id
    BACKUP_ENABLED     = var.disaster_recovery.cross_region_backup.enabled
    MONITORING_ENABLED = var.monitoring_config.enabled
  }

  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = google_storage_bucket.state_bucket.name
  }
}

# IAM for Enhanced Security
resource "google_storage_bucket_iam_binding" "conditional_access" {
  for_each = {
    "time_restricted" = {
      role = "roles/storage.objectViewer"
      condition = {
        title       = "Time-based access"
        description = "Access only during business hours"
        expression  = "request.time.getHours() >= 9 && request.time.getHours() <= 17"
      }
    }
  }

  bucket  = google_storage_bucket.state_bucket.name
  role    = each.value.role
  members = var.enhanced_security.access_control.service_account_restrictions

  dynamic "condition" {
    for_each = var.enhanced_security.access_control.enable_iam_conditions ? [each.value.condition] : []
    content {
      title       = condition.value.title
      description = condition.value.description
      expression  = condition.value.expression
    }
  }
}

# Budget Alert for Cost Control
resource "google_billing_budget" "state_storage_budget" {
  count = var.cost_optimization.enabled && var.cost_optimization.budget_controls.enabled ? 1 : 0

  billing_account = data.google_project.project.billing_account
  display_name    = "${var.bucket_name} Storage Budget"

  budget_filter {
    projects = ["projects/${var.project_id}"]
    services = ["services/95FF2659-5EA1-4CC2-9B71-1FE578B7C1E8"] # Cloud Storage service ID
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(floor(var.cost_optimization.budget_controls.monthly_budget))
    }
  }

  dynamic "threshold_rules" {
    for_each = var.cost_optimization.budget_controls.alert_thresholds
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }

  all_updates_rule {
    schema_version = "1.0"
  }
}

# Data source for project info
data "google_project" "project" {
  project_id = var.project_id
}
