/**
 * Cloud Storage and Firestore resources
 */

# Cloud Storage buckets
resource "google_storage_bucket" "buckets" {
  for_each = local.storage_buckets

  name     = each.value.full_name
  project  = var.project_id
  location = lookup(each.value, "location", var.default_region)

  storage_class               = lookup(each.value, "storage_class", "STANDARD")
  force_destroy               = lookup(each.value, "force_destroy", false)
  uniform_bucket_level_access = lookup(each.value, "uniform_bucket_level_access", true)
  public_access_prevention    = lookup(each.value, "public_access_prevention", "enforced")

  # Versioning
  versioning {
    enabled = lookup(each.value, "versioning_enabled", true)
  }

  # Lifecycle rules
  dynamic "lifecycle_rule" {
    for_each = lookup(each.value, "lifecycle_rules", [])
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
        custom_time_before         = lookup(lifecycle_rule.value.condition, "custom_time_before", null)
        days_since_custom_time     = lookup(lifecycle_rule.value.condition, "days_since_custom_time", null)
        days_since_noncurrent_time = lookup(lifecycle_rule.value.condition, "days_since_noncurrent_time", null)
        noncurrent_time_before     = lookup(lifecycle_rule.value.condition, "noncurrent_time_before", null)
      }
    }
  }

  # Retention policy
  dynamic "retention_policy" {
    for_each = lookup(each.value, "retention_policy", null) != null ? [1] : []
    content {
      retention_period = each.value.retention_policy.retention_period
      is_locked        = lookup(each.value.retention_policy, "is_locked", false)
    }
  }

  # Encryption
  dynamic "encryption" {
    for_each = lookup(each.value, "encryption_key", null) != null ? [1] : []
    content {
      default_kms_key_name = each.value.encryption_key
    }
  }

  # CORS configuration
  dynamic "cors" {
    for_each = lookup(each.value, "cors", [])
    content {
      origin          = cors.value.origin
      method          = cors.value.method
      response_header = cors.value.response_header
      max_age_seconds = cors.value.max_age_seconds
    }
  }

  # Website configuration
  dynamic "website" {
    for_each = lookup(each.value, "website", null) != null ? [1] : []
    content {
      main_page_suffix = lookup(each.value.website, "main_page_suffix", "index.html")
      not_found_page   = lookup(each.value.website, "not_found_page", "404.html")
    }
  }

  # Logging
  dynamic "logging" {
    for_each = lookup(each.value, "logging", null) != null ? [1] : []
    content {
      log_bucket        = each.value.logging.log_bucket
      log_object_prefix = lookup(each.value.logging, "log_object_prefix", "")
    }
  }

  # Autoclass
  dynamic "autoclass" {
    for_each = lookup(each.value, "enable_autoclass", false) ? [1] : []
    content {
      enabled                = true
      terminal_storage_class = lookup(each.value, "autoclass_terminal_storage_class", null)
    }
  }

  # Soft delete policy
  dynamic "soft_delete_policy" {
    for_each = lookup(each.value, "soft_delete_policy", null) != null ? [1] : []
    content {
      retention_duration_seconds = each.value.soft_delete_policy.retention_duration_seconds
    }
  }

  # Custom placement
  dynamic "custom_placement_config" {
    for_each = lookup(each.value, "custom_placement_config", null) != null ? [1] : []
    content {
      data_locations = each.value.custom_placement_config.data_locations
    }
  }

  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value, "labels", {}),
    {
      storage_type = "cloud-storage"
    }
  )
}

# Bucket IAM bindings
resource "google_storage_bucket_iam_binding" "bucket_bindings" {
  for_each = {
    for binding in flatten([
      for bucket_name, bucket in local.storage_buckets : [
        for binding in lookup(bucket, "iam_bindings", []) : {
          key         = "${bucket_name}-${binding.role}"
          bucket_name = bucket_name
          binding     = binding
        }
      ]
    ]) : binding.key => binding
  }

  bucket  = google_storage_bucket.buckets[each.value.bucket_name].name
  role    = each.value.binding.role
  members = each.value.binding.members

  dynamic "condition" {
    for_each = lookup(each.value.binding, "condition", null) != null ? [1] : []
    content {
      title       = each.value.binding.condition.title
      description = lookup(each.value.binding.condition, "description", null)
      expression  = each.value.binding.condition.expression
    }
  }
}

# Bucket notifications
resource "google_storage_notification" "bucket_notifications" {
  for_each = {
    for notification in flatten([
      for bucket_name, bucket in local.storage_buckets : [
        for notification in lookup(bucket, "notifications", []) : {
          key          = "${bucket_name}-${notification.topic}"
          bucket_name  = bucket_name
          notification = notification
        }
      ]
    ]) : notification.key => notification
  }

  bucket         = google_storage_bucket.buckets[each.value.bucket_name].name
  topic          = each.value.notification.topic
  payload_format = lookup(each.value.notification, "payload_format", "JSON_API_V1")

  event_types        = lookup(each.value.notification, "event_types", ["OBJECT_FINALIZE"])
  object_name_prefix = lookup(each.value.notification, "object_name_prefix", null)
  custom_attributes  = lookup(each.value.notification, "custom_attributes", {})

  depends_on = [google_storage_bucket.buckets]
}

# Firestore databases
resource "google_firestore_database" "databases" {
  for_each = local.firestore_databases

  name                        = each.value.full_name
  project                     = var.project_id
  location_id                 = lookup(each.value, "location", var.default_region)
  type                        = lookup(each.value, "type", "FIRESTORE_NATIVE")
  concurrency_mode            = lookup(each.value, "concurrency_mode", "OPTIMISTIC")
  app_engine_integration_mode = lookup(each.value, "app_engine_integration_mode", "DISABLED")

  # Point in time recovery
  point_in_time_recovery_enablement = lookup(each.value, "point_in_time_recovery", "POINT_IN_TIME_RECOVERY_ENABLED")

  # Delete protection
  delete_protection_state = lookup(each.value, "delete_protection", "DELETE_PROTECTION_ENABLED")
  deletion_policy         = lookup(each.value, "deletion_policy", "DELETE")
}

# Firestore indexes
resource "google_firestore_index" "indexes" {
  for_each = {
    for index in flatten([
      for db_name, db in local.firestore_databases : [
        for index in lookup(db, "indexes", []) : {
          key     = "${db_name}-${index.collection}-${join("-", [for field in index.fields : "${field.field_path}-${field.order}"])}"
          db_name = db_name
          index   = index
        }
      ]
    ]) : index.key => index
  }

  project    = var.project_id
  database   = google_firestore_database.databases[each.value.db_name].name
  collection = each.value.index.collection

  dynamic "fields" {
    for_each = each.value.index.fields
    content {
      field_path   = fields.value.field_path
      order        = lookup(fields.value, "order", null)
      array_config = lookup(fields.value, "array_config", null)

      dynamic "vector_config" {
        for_each = lookup(fields.value, "vector_config", null) != null ? [1] : []
        content {
          dimension = fields.value.vector_config.dimension

          dynamic "flat" {
            for_each = lookup(fields.value.vector_config, "flat", null) != null ? [1] : []
            content {}
          }
        }
      }
    }
  }

  query_scope = lookup(each.value.index, "query_scope", "COLLECTION")
  api_scope   = lookup(each.value.index, "api_scope", "ANY_API")
}

# Firestore backup schedules
resource "google_firestore_backup_schedule" "backup_schedules" {
  for_each = {
    for schedule in flatten([
      for db_name, db in local.firestore_databases : [
        for schedule in lookup(db, "backup_schedules", []) : {
          key      = "${db_name}-${schedule.retention}"
          db_name  = db_name
          schedule = schedule
        }
      ]
    ]) : schedule.key => schedule
  }

  project   = var.project_id
  database  = google_firestore_database.databases[each.value.db_name].name
  retention = each.value.schedule.retention

  dynamic "daily_recurrence" {
    for_each = lookup(each.value.schedule, "daily_recurrence", null) != null ? [1] : []
    content {}
  }

  dynamic "weekly_recurrence" {
    for_each = lookup(each.value.schedule, "weekly_recurrence", null) != null ? [1] : []
    content {
      day = each.value.schedule.weekly_recurrence.day
    }
  }
}

# Memorystore Redis instances
resource "google_redis_instance" "redis_instances" {
  for_each = {
    for instance_name, instance in local.memorystore_instances : instance_name => instance
    if lookup(instance, "engine", "redis") == "redis"
  }

  name                    = each.value.full_name
  project                 = var.project_id
  region                  = lookup(each.value, "region", var.default_region)
  location_id             = lookup(each.value, "zone", "${var.default_region}-a")
  alternative_location_id = lookup(each.value, "alternative_zone", null)

  tier           = lookup(each.value, "tier", "STANDARD_HA")
  memory_size_gb = each.value.memory_size_gb
  redis_version  = lookup(each.value, "redis_version", "REDIS_7_0")
  display_name   = lookup(each.value, "display_name", each.value.name)

  # Network
  authorized_network = lookup(each.value, "authorized_network", var.network_id)
  connect_mode       = lookup(each.value, "connect_mode", "PRIVATE_SERVICE_ACCESS")
  reserved_ip_range  = lookup(each.value, "reserved_ip_range", null)

  # Redis configuration
  redis_configs = lookup(each.value, "redis_configs", {})

  # Auth
  auth_enabled            = lookup(each.value, "auth_enabled", true)
  transit_encryption_mode = lookup(each.value, "transit_encryption_mode", "SERVER_AUTHENTICATION")

  # Persistence
  dynamic "persistence_config" {
    for_each = lookup(each.value, "persistence_config", null) != null ? [1] : []
    content {
      persistence_mode        = each.value.persistence_config.persistence_mode
      rdb_snapshot_period     = lookup(each.value.persistence_config, "rdb_snapshot_period", null)
      rdb_snapshot_start_time = lookup(each.value.persistence_config, "rdb_snapshot_start_time", null)
    }
  }

  # Maintenance policy
  dynamic "maintenance_policy" {
    for_each = lookup(each.value, "maintenance_policy", null) != null ? [1] : []
    content {
      description = lookup(each.value.maintenance_policy, "description", null)

      dynamic "weekly_maintenance_window" {
        for_each = lookup(each.value.maintenance_policy, "weekly_maintenance_window", [])
        content {
          day = weekly_maintenance_window.value.day
          start_time {
            hours   = weekly_maintenance_window.value.start_time.hours
            minutes = lookup(weekly_maintenance_window.value.start_time, "minutes", 0)
            seconds = lookup(weekly_maintenance_window.value.start_time, "seconds", 0)
            nanos   = lookup(weekly_maintenance_window.value.start_time, "nanos", 0)
          }
          duration = weekly_maintenance_window.value.duration
        }
      }
    }
  }

  # Customer-managed encryption key
  customer_managed_key = lookup(each.value, "encryption_key", null)

  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value, "labels", {}),
    {
      memorystore_type = "redis"
    }
  )

  # Replica count for read replicas
  replica_count      = lookup(each.value, "replica_count", null)
  read_replicas_mode = lookup(each.value, "read_replicas_mode", null)
}

# Memorystore Memcached instances
resource "google_memcache_instance" "memcached_instances" {
  for_each = {
    for instance_name, instance in local.memorystore_instances : instance_name => instance
    if lookup(instance, "engine", "redis") == "memcached"
  }

  name         = each.value.full_name
  project      = var.project_id
  region       = lookup(each.value, "region", var.default_region)
  display_name = lookup(each.value, "display_name", each.value.name)

  # Network
  authorized_network = lookup(each.value, "authorized_network", var.network_id)

  # Node configuration
  node_config {
    cpu_count      = lookup(each.value, "cpu_count", 1)
    memory_size_mb = each.value.memory_size_gb * 1024
  }

  node_count = lookup(each.value, "node_count", 1)
  zones      = lookup(each.value, "zones", ["${var.default_region}-a"])

  # Memcached version
  memcache_version = lookup(each.value, "memcache_version", "MEMCACHE_1_6_15")

  # Parameters
  dynamic "memcache_parameters" {
    for_each = lookup(each.value, "memcache_parameters", null) != null ? [1] : []
    content {
      id = "default"
      dynamic "params" {
        for_each = each.value.memcache_parameters
        content {
          key   = params.key
          value = params.value
        }
      }
    }
  }

  # Maintenance policy
  dynamic "maintenance_policy" {
    for_each = lookup(each.value, "maintenance_policy", null) != null ? [1] : []
    content {
      description = lookup(each.value.maintenance_policy, "description", null)

      dynamic "weekly_maintenance_window" {
        for_each = lookup(each.value.maintenance_policy, "weekly_maintenance_window", [])
        content {
          day      = weekly_maintenance_window.value.day
          duration = weekly_maintenance_window.value.duration
          start_time {
            hours   = weekly_maintenance_window.value.start_time.hours
            minutes = lookup(weekly_maintenance_window.value.start_time, "minutes", 0)
            seconds = lookup(weekly_maintenance_window.value.start_time, "seconds", 0)
            nanos   = lookup(weekly_maintenance_window.value.start_time, "nanos", 0)
          }
        }
      }
    }
  }

  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value, "labels", {}),
    {
      memorystore_type = "memcached"
    }
  )
}
