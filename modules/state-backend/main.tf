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
  
  # Merge custom lifecycle rules with defaults
  lifecycle_rules = concat(local.default_lifecycle_rules, var.lifecycle_rules)
  
  # Determine if we need to create a logging bucket
  create_logging_bucket = var.logging_config == null
  log_bucket_name      = local.create_logging_bucket ? "${var.bucket_name}-logs" : var.logging_config.log_bucket
  log_object_prefix    = local.create_logging_bucket ? "access-logs/" : var.logging_config.log_object_prefix
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
  
  labels = var.labels
  
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
      delete_objects_unique_in_sink               = var.replication_configuration.delete_marker_status
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