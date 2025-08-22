/**
 * Data Module
 * 
 * Comprehensive data infrastructure for GCP
 * Supports Cloud SQL, BigQuery, Firestore, Cloud Storage with HA and backup
 */

locals {
  # Default labels
  default_labels = {
    managed_by  = "terraform"
    module      = "data"
    environment = var.environment
  }
  
  merged_labels = merge(local.default_labels, var.labels)
  
  # Cloud SQL instances processing
  sql_instances = {
    for instance in var.sql_instances : instance.name => merge(instance, {
      full_name = "${var.name_prefix}-${instance.name}"
    })
  }
  
  # BigQuery datasets processing
  bigquery_datasets = {
    for dataset in var.bigquery_datasets : dataset.name => merge(dataset, {
      full_name = "${var.name_prefix}_${dataset.name}"  # BigQuery uses underscores
    })
  }
  
  # Firestore databases processing
  firestore_databases = {
    for db in var.firestore_databases : db.name => merge(db, {
      full_name = "${var.name_prefix}-${db.name}"
    })
  }
  
  # Storage buckets processing
  storage_buckets = {
    for bucket in var.storage_buckets : bucket.name => merge(bucket, {
      full_name = "${var.name_prefix}-${bucket.name}"
    })
  }
  
  # Memorystore instances processing
  memorystore_instances = {
    for instance in var.memorystore_instances : instance.name => merge(instance, {
      full_name = "${var.name_prefix}-${instance.name}"
    })
  }
  
  # Dataflow jobs processing
  dataflow_jobs = {
    for job in var.dataflow_jobs : job.name => merge(job, {
      full_name = "${var.name_prefix}-${job.name}"
    })
  }
}

# Cloud SQL instances
resource "google_sql_database_instance" "instances" {
  for_each = local.sql_instances
  
  name             = each.value.full_name
  project          = var.project_id
  region           = lookup(each.value, "region", var.default_region)
  database_version = each.value.database_version
  
  deletion_protection = lookup(each.value, "deletion_protection", true)
  
  settings {
    tier                        = each.value.tier
    edition                     = lookup(each.value, "edition", "ENTERPRISE")
    availability_type          = lookup(each.value, "availability_type", "REGIONAL")
    disk_size                  = lookup(each.value, "disk_size", 20)
    disk_type                  = lookup(each.value, "disk_type", "PD_SSD")
    disk_autoresize           = lookup(each.value, "disk_autoresize", true)
    disk_autoresize_limit     = lookup(each.value, "disk_autoresize_limit", 0)
    
    # Backup configuration
    backup_configuration {
      enabled                        = lookup(each.value, "backup_enabled", true)
      start_time                     = lookup(each.value, "backup_start_time", "03:00")
      location                       = lookup(each.value, "backup_location", null)
      point_in_time_recovery_enabled = lookup(each.value, "point_in_time_recovery", true)
      transaction_log_retention_days = lookup(each.value, "transaction_log_retention_days", 7)
      backup_retention_settings {
        retained_backups = lookup(each.value, "retained_backups", 7)
        retention_unit   = lookup(each.value, "retention_unit", "COUNT")
      }
    }
    
    # IP configuration
    ip_configuration {
      ipv4_enabled                                  = lookup(each.value, "ipv4_enabled", false)
      private_network                              = lookup(each.value, "private_network", var.network_id)
      enable_private_path_for_google_cloud_services = lookup(each.value, "enable_private_path", true)
      allocated_ip_range                           = lookup(each.value, "allocated_ip_range", null)
      
      # Authorized networks
      dynamic "authorized_networks" {
        for_each = lookup(each.value, "authorized_networks", [])
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.value
        }
      }
      
      # SSL configuration
      ssl_mode                = lookup(each.value, "ssl_mode", "ENCRYPTED_ONLY")
      require_ssl            = lookup(each.value, "require_ssl", true)
    }
    
    # Maintenance window
    dynamic "maintenance_window" {
      for_each = lookup(each.value, "maintenance_window", null) != null ? [1] : []
      content {
        day          = each.value.maintenance_window.day
        hour         = each.value.maintenance_window.hour
        update_track = lookup(each.value.maintenance_window, "update_track", "stable")
      }
    }
    
    # Database flags
    dynamic "database_flags" {
      for_each = lookup(each.value, "database_flags", {})
      content {
        name  = database_flags.key
        value = database_flags.value
      }
    }
    
    # User labels
    user_labels = merge(
      local.merged_labels,
      lookup(each.value, "labels", {}),
      {
        database_type = "cloud-sql"
        instance_name = each.value.name
      }
    )
    
    # Insights configuration
    dynamic "insights_config" {
      for_each = lookup(each.value, "enable_insights", true) ? [1] : []
      content {
        query_insights_enabled  = true
        query_plans_per_minute  = lookup(each.value, "query_plans_per_minute", 5)
        query_string_length     = lookup(each.value, "query_string_length", 1024)
        record_application_tags = lookup(each.value, "record_application_tags", false)
        record_client_address   = lookup(each.value, "record_client_address", false)
      }
    }
    
    # Advanced machine configuration
    dynamic "advanced_machine_features" {
      for_each = lookup(each.value, "threads_per_core", null) != null ? [1] : []
      content {
        threads_per_core = each.value.threads_per_core
      }
    }
    
    # Data cache configuration
    dynamic "data_cache_config" {
      for_each = lookup(each.value, "enable_data_cache", false) ? [1] : []
      content {
        data_cache_enabled = true
      }
    }
    
    # Password policy
    dynamic "password_validation_policy" {
      for_each = lookup(each.value, "password_policy", null) != null ? [1] : []
      content {
        min_length                  = lookup(each.value.password_policy, "min_length", 8)
        complexity                  = lookup(each.value.password_policy, "complexity", "COMPLEXITY_DEFAULT")
        reuse_interval             = lookup(each.value.password_policy, "reuse_interval", 0)
        disallow_username_substring = lookup(each.value.password_policy, "disallow_username_substring", false)
        password_change_interval    = lookup(each.value.password_policy, "password_change_interval", null)
        enable_password_policy      = true
      }
    }
    
    # SQL Server audit configuration
    dynamic "sql_server_audit_config" {
      for_each = lookup(each.value, "sql_server_audit_config", null) != null ? [1] : []
      content {
        bucket                      = each.value.sql_server_audit_config.bucket
        retention_interval         = lookup(each.value.sql_server_audit_config, "retention_interval", null)
        upload_interval            = lookup(each.value.sql_server_audit_config, "upload_interval", null)
      }
    }
    
    # Deletion protection for settings
    deletion_protection_enabled = lookup(each.value, "deletion_protection", true)
  }
  
  # Encryption configuration
  dynamic "encryption_key_name" {
    for_each = lookup(each.value, "encryption_key", null) != null ? [1] : []
    content {
      encryption_key_name = each.value.encryption_key
    }
  }
  
  # Root password (will be generated if not provided)
  root_password = lookup(each.value, "root_password", null)
  
  # Lifecycle
  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      settings[0].disk_size  # Allow disk auto-resize
    ]
  }
  
  depends_on = [
    google_service_networking_connection.private_vpc_connection
  ]
}

# Cloud SQL databases
resource "google_sql_database" "databases" {
  for_each = {
    for db in flatten([
      for instance_name, instance in local.sql_instances : [
        for database in lookup(instance, "databases", []) : {
          key           = "${instance_name}-${database.name}"
          instance_name = instance_name
          database      = database
        }
      ]
    ]) : db.key => db
  }
  
  name     = each.value.database.name
  instance = google_sql_database_instance.instances[each.value.instance_name].name
  charset  = lookup(each.value.database, "charset", null)
  collation = lookup(each.value.database, "collation", null)
}

# Cloud SQL users
resource "google_sql_user" "users" {
  for_each = {
    for user in flatten([
      for instance_name, instance in local.sql_instances : [
        for user in lookup(instance, "users", []) : {
          key           = "${instance_name}-${user.name}"
          instance_name = instance_name
          user          = user
        }
      ]
    ]) : user.key => user
  }
  
  name     = each.value.user.name
  instance = google_sql_database_instance.instances[each.value.instance_name].name
  password = lookup(each.value.user, "password", null)
  host     = lookup(each.value.user, "host", null)
  type     = lookup(each.value.user, "type", "BUILT_IN")
  
  # Password policy for user
  dynamic "password_policy" {
    for_each = lookup(each.value.user, "password_policy", null) != null ? [1] : []
    content {
      allowed_failed_attempts      = lookup(each.value.user.password_policy, "allowed_failed_attempts", 5)
      password_expiration_duration = lookup(each.value.user.password_policy, "password_expiration_duration", null)
      enable_failed_attempts_check = lookup(each.value.user.password_policy, "enable_failed_attempts_check", false)
      enable_password_verification = lookup(each.value.user.password_policy, "enable_password_verification", false)
    }
  }
}

# Private VPC connection for Cloud SQL
resource "google_service_networking_connection" "private_vpc_connection" {
  count = var.enable_private_ip && var.network_id != null ? 1 : 0
  
  network                 = var.network_id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range[0].name]
}

# Reserved IP range for private Cloud SQL
resource "google_compute_global_address" "private_ip_range" {
  count = var.enable_private_ip && var.network_id != null ? 1 : 0
  
  name          = "${var.name_prefix}-sql-private-ip"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = var.network_id
}

# BigQuery datasets
resource "google_bigquery_dataset" "datasets" {
  for_each = local.bigquery_datasets
  
  dataset_id    = each.value.full_name
  project       = var.project_id
  location      = lookup(each.value, "location", var.default_region)
  friendly_name = lookup(each.value, "friendly_name", each.value.name)
  description   = lookup(each.value, "description", "Dataset ${each.value.name}")
  
  # Default table expiration
  default_table_expiration_ms = lookup(each.value, "default_table_expiration_ms", null)
  
  # Default partition expiration
  default_partition_expiration_ms = lookup(each.value, "default_partition_expiration_ms", null)
  
  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value, "labels", {}),
    {
      dataset_type = "bigquery"
    }
  )
  
  # Access controls
  dynamic "access" {
    for_each = lookup(each.value, "access", [])
    content {
      role           = lookup(access.value, "role", null)
      user_by_email  = lookup(access.value, "user_by_email", null)
      group_by_email = lookup(access.value, "group_by_email", null)
      domain        = lookup(access.value, "domain", null)
      special_group = lookup(access.value, "special_group", null)
      
      dynamic "dataset" {
        for_each = lookup(access.value, "dataset", null) != null ? [1] : []
        content {
          dataset {
            project_id = lookup(access.value.dataset, "project_id", var.project_id)
            dataset_id = access.value.dataset.dataset_id
          }
          target_types = access.value.dataset.target_types
        }
      }
      
      dynamic "routine" {
        for_each = lookup(access.value, "routine", null) != null ? [1] : []
        content {
          project_id = lookup(access.value.routine, "project_id", var.project_id)
          dataset_id = access.value.routine.dataset_id
          routine_id = access.value.routine.routine_id
        }
      }
      
      dynamic "view" {
        for_each = lookup(access.value, "view", null) != null ? [1] : []
        content {
          project_id = lookup(access.value.view, "project_id", var.project_id)
          dataset_id = access.value.view.dataset_id
          table_id   = access.value.view.table_id
        }
      }
    }
  }
  
  # Default encryption configuration
  dynamic "default_encryption_configuration" {
    for_each = lookup(each.value, "encryption_key", null) != null ? [1] : []
    content {
      kms_key_name = each.value.encryption_key
    }
  }
  
  # External dataset reference
  dynamic "external_dataset_reference" {
    for_each = lookup(each.value, "external_dataset_reference", null) != null ? [1] : []
    content {
      external_source = each.value.external_dataset_reference.external_source
      connection     = each.value.external_dataset_reference.connection
    }
  }
  
  delete_contents_on_destroy = lookup(each.value, "delete_contents_on_destroy", false)
}

# BigQuery tables
resource "google_bigquery_table" "tables" {
  for_each = {
    for table in flatten([
      for dataset_name, dataset in local.bigquery_datasets : [
        for table in lookup(dataset, "tables", []) : {
          key          = "${dataset_name}-${table.name}"
          dataset_name = dataset_name
          table        = table
        }
      ]
    ]) : table.key => table
  }
  
  table_id   = each.value.table.name
  dataset_id = google_bigquery_dataset.datasets[each.value.dataset_name].dataset_id
  project    = var.project_id
  
  description = lookup(each.value.table, "description", "Table ${each.value.table.name}")
  
  # Schema
  schema = lookup(each.value.table, "schema", null)
  
  # Time partitioning
  dynamic "time_partitioning" {
    for_each = lookup(each.value.table, "time_partitioning", null) != null ? [1] : []
    content {
      type                     = each.value.table.time_partitioning.type
      field                   = lookup(each.value.table.time_partitioning, "field", null)
      expiration_ms           = lookup(each.value.table.time_partitioning, "expiration_ms", null)
      require_partition_filter = lookup(each.value.table.time_partitioning, "require_partition_filter", false)
    }
  }
  
  # Range partitioning
  dynamic "range_partitioning" {
    for_each = lookup(each.value.table, "range_partitioning", null) != null ? [1] : []
    content {
      field = each.value.table.range_partitioning.field
      range {
        start    = each.value.table.range_partitioning.range.start
        end      = each.value.table.range_partitioning.range.end
        interval = each.value.table.range_partitioning.range.interval
      }
    }
  }
  
  # Clustering
  clustering = lookup(each.value.table, "clustering", [])
  
  # Table expiration
  expiration_time = lookup(each.value.table, "expiration_time", null)
  
  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value.table, "labels", {}),
    {
      table_type = "bigquery"
    }
  )
  
  # Encryption configuration
  dynamic "encryption_configuration" {
    for_each = lookup(each.value.table, "encryption_key", null) != null ? [1] : []
    content {
      kms_key_name = each.value.table.encryption_key
    }
  }
  
  # External data configuration
  dynamic "external_data_configuration" {
    for_each = lookup(each.value.table, "external_data_configuration", null) != null ? [1] : []
    content {
      source_format         = each.value.table.external_data_configuration.source_format
      source_uris          = each.value.table.external_data_configuration.source_uris
      schema               = lookup(each.value.table.external_data_configuration, "schema", null)
      max_bad_records      = lookup(each.value.table.external_data_configuration, "max_bad_records", 0)
      ignore_unknown_values = lookup(each.value.table.external_data_configuration, "ignore_unknown_values", false)
      compression          = lookup(each.value.table.external_data_configuration, "compression", null)
      
      dynamic "csv_options" {
        for_each = lookup(each.value.table.external_data_configuration, "csv_options", null) != null ? [1] : []
        content {
          quote                 = lookup(each.value.table.external_data_configuration.csv_options, "quote", "\"")
          skip_leading_rows     = lookup(each.value.table.external_data_configuration.csv_options, "skip_leading_rows", 0)
          field_delimiter       = lookup(each.value.table.external_data_configuration.csv_options, "field_delimiter", ",")
          allow_quoted_newlines = lookup(each.value.table.external_data_configuration.csv_options, "allow_quoted_newlines", false)
          allow_jagged_rows     = lookup(each.value.table.external_data_configuration.csv_options, "allow_jagged_rows", false)
        }
      }
      
      dynamic "google_sheets_options" {
        for_each = lookup(each.value.table.external_data_configuration, "google_sheets_options", null) != null ? [1] : []
        content {
          skip_leading_rows = lookup(each.value.table.external_data_configuration.google_sheets_options, "skip_leading_rows", 0)
          range            = lookup(each.value.table.external_data_configuration.google_sheets_options, "range", null)
        }
      }
      
      dynamic "hive_partitioning_options" {
        for_each = lookup(each.value.table.external_data_configuration, "hive_partitioning_options", null) != null ? [1] : []
        content {
          mode                     = lookup(each.value.table.external_data_configuration.hive_partitioning_options, "mode", "AUTO")
          source_uri_prefix        = lookup(each.value.table.external_data_configuration.hive_partitioning_options, "source_uri_prefix", null)
          require_partition_filter = lookup(each.value.table.external_data_configuration.hive_partitioning_options, "require_partition_filter", false)
        }
      }
    }
  }
  
  # Materialized view
  dynamic "materialized_view" {
    for_each = lookup(each.value.table, "materialized_view", null) != null ? [1] : []
    content {
      query                = each.value.table.materialized_view.query
      enable_refresh       = lookup(each.value.table.materialized_view, "enable_refresh", true)
      refresh_interval_ms  = lookup(each.value.table.materialized_view, "refresh_interval_ms", 1800000)  # 30 minutes
      allow_non_incremental_definition = lookup(each.value.table.materialized_view, "allow_non_incremental_definition", false)
    }
  }
  
  # View
  dynamic "view" {
    for_each = lookup(each.value.table, "view", null) != null ? [1] : []
    content {
      query          = each.value.table.view.query
      use_legacy_sql = lookup(each.value.table.view, "use_legacy_sql", false)
    }
  }
  
  deletion_protection = lookup(each.value.table, "deletion_protection", false)
}