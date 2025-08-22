/**
 * Data Module - Variables
 * 
 * Comprehensive data infrastructure configuration variables
 */

# Project and Environment Configuration
variable "project_id" {
  description = "The GCP project ID where data resources will be created"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for naming all data resources"
  type        = string
  default     = "data"
}

variable "environment" {
  description = "Environment name (dev, staging, prod, etc.)"
  type        = string
  default     = "dev"
}

variable "default_region" {
  description = "Default region for data resources"
  type        = string
  default     = "us-central1"
}

# Network Configuration
variable "network_id" {
  description = "VPC network ID for private connectivity"
  type        = string
  default     = null
}

variable "subnet_id" {
  description = "Subnet ID for regional resources"
  type        = string
  default     = null
}

variable "enable_private_ip" {
  description = "Whether to enable private IP for Cloud SQL"
  type        = bool
  default     = true
}

# Labels
variable "labels" {
  description = "Labels to apply to all data resources"
  type        = map(string)
  default     = {}
}

# Cloud SQL Configuration
variable "sql_instances" {
  description = "List of Cloud SQL instances to create"
  type = list(object({
    name             = string
    database_version = string
    tier            = string
    region          = optional(string)
    edition         = optional(string, "ENTERPRISE")
    availability_type = optional(string, "REGIONAL")
    disk_size       = optional(number, 20)
    disk_type       = optional(string, "PD_SSD")
    disk_autoresize = optional(bool, true)
    disk_autoresize_limit = optional(number, 0)
    deletion_protection = optional(bool, true)
    
    # Backup configuration
    backup_enabled = optional(bool, true)
    backup_start_time = optional(string, "03:00")
    backup_location = optional(string)
    point_in_time_recovery = optional(bool, true)
    transaction_log_retention_days = optional(number, 7)
    retained_backups = optional(number, 7)
    retention_unit = optional(string, "COUNT")
    
    # Network configuration
    ipv4_enabled = optional(bool, false)
    private_network = optional(string)
    enable_private_path = optional(bool, true)
    allocated_ip_range = optional(string)
    authorized_networks = optional(list(object({
      name  = string
      value = string
    })), [])
    ssl_mode = optional(string, "ENCRYPTED_ONLY")
    require_ssl = optional(bool, true)
    
    # Maintenance window
    maintenance_window = optional(object({
      day = number
      hour = number
      update_track = optional(string, "stable")
    }))
    
    # Database flags
    database_flags = optional(map(string), {})
    
    # Insights and performance
    enable_insights = optional(bool, true)
    query_plans_per_minute = optional(number, 5)
    query_string_length = optional(number, 1024)
    record_application_tags = optional(bool, false)
    record_client_address = optional(bool, false)
    
    # Advanced features
    threads_per_core = optional(number)
    enable_data_cache = optional(bool, false)
    
    # Password policy
    password_policy = optional(object({
      min_length = optional(number, 8)
      complexity = optional(string, "COMPLEXITY_DEFAULT")
      reuse_interval = optional(number, 0)
      disallow_username_substring = optional(bool, false)
      password_change_interval = optional(string)
    }))
    
    # SQL Server audit configuration
    sql_server_audit_config = optional(object({
      bucket = string
      retention_interval = optional(string)
      upload_interval = optional(string)
    }))
    
    # Encryption
    encryption_key = optional(string)
    
    # Root password
    root_password = optional(string)
    
    # Databases to create
    databases = optional(list(object({
      name = string
      charset = optional(string)
      collation = optional(string)
    })), [])
    
    # Users to create
    users = optional(list(object({
      name = string
      password = optional(string)
      host = optional(string)
      type = optional(string, "BUILT_IN")
      password_policy = optional(object({
        allowed_failed_attempts = optional(number, 5)
        password_expiration_duration = optional(string)
        enable_failed_attempts_check = optional(bool, false)
        enable_password_verification = optional(bool, false)
      }))
    })), [])
    
    labels = optional(map(string), {})
  }))
  default = []
}

# BigQuery Configuration
variable "bigquery_datasets" {
  description = "List of BigQuery datasets to create"
  type = list(object({
    name = string
    location = optional(string)
    friendly_name = optional(string)
    description = optional(string)
    default_table_expiration_ms = optional(number)
    default_partition_expiration_ms = optional(number)
    delete_contents_on_destroy = optional(bool, false)
    
    # Access controls
    access = optional(list(object({
      role = optional(string)
      user_by_email = optional(string)
      group_by_email = optional(string)
      domain = optional(string)
      special_group = optional(string)
      dataset = optional(object({
        project_id = optional(string)
        dataset_id = string
        target_types = list(string)
      }))
      routine = optional(object({
        project_id = optional(string)
        dataset_id = string
        routine_id = string
      }))
      view = optional(object({
        project_id = optional(string)
        dataset_id = string
        table_id = string
      }))
    })), [])
    
    # Encryption
    encryption_key = optional(string)
    
    # External dataset reference
    external_dataset_reference = optional(object({
      external_source = string
      connection = string
    }))
    
    # Tables to create
    tables = optional(list(object({
      name = string
      description = optional(string)
      schema = optional(string)
      clustering = optional(list(string), [])
      expiration_time = optional(number)
      
      # Time partitioning
      time_partitioning = optional(object({
        type = string
        field = optional(string)
        expiration_ms = optional(number)
        require_partition_filter = optional(bool, false)
      }))
      
      # Range partitioning
      range_partitioning = optional(object({
        field = string
        range = object({
          start = number
          end = number
          interval = number
        })
      }))
      
      # Encryption
      encryption_key = optional(string)
      
      # External data configuration
      external_data_configuration = optional(object({
        source_format = string
        source_uris = list(string)
        schema = optional(string)
        max_bad_records = optional(number, 0)
        ignore_unknown_values = optional(bool, false)
        compression = optional(string)
        csv_options = optional(object({
          quote = optional(string, "\"")
          skip_leading_rows = optional(number, 0)
          field_delimiter = optional(string, ",")
          allow_quoted_newlines = optional(bool, false)
          allow_jagged_rows = optional(bool, false)
        }))
        google_sheets_options = optional(object({
          skip_leading_rows = optional(number, 0)
          range = optional(string)
        }))
        hive_partitioning_options = optional(object({
          mode = optional(string, "AUTO")
          source_uri_prefix = optional(string)
          require_partition_filter = optional(bool, false)
        }))
      }))
      
      # Materialized view
      materialized_view = optional(object({
        query = string
        enable_refresh = optional(bool, true)
        refresh_interval_ms = optional(number, 1800000)
        allow_non_incremental_definition = optional(bool, false)
      }))
      
      # View
      view = optional(object({
        query = string
        use_legacy_sql = optional(bool, false)
      }))
      
      deletion_protection = optional(bool, false)
      labels = optional(map(string), {})
    })), [])
    
    labels = optional(map(string), {})
  }))
  default = []
}

# BigQuery Data Transfer Configuration
variable "bigquery_transfers" {
  description = "List of BigQuery Data Transfer configurations"
  type = list(object({
    name = string
    display_name = string
    data_source_id = string
    destination_dataset_id = string
    location = optional(string)
    params = map(string)
    sensitive_params = optional(map(string), {})
    schedule = optional(string)
    data_refresh_window_days = optional(number, 0)
    disabled = optional(bool, false)
    service_account_name = optional(string)
    notification_pubsub_topic = optional(string)
    email_preferences = optional(object({
      enable_failure_email = optional(bool, false)
    }))
    schedule_options = optional(object({
      disable_auto_scheduling = optional(bool, false)
      start_time = optional(string)
      end_time = optional(string)
    }))
  }))
  default = []
}

# Firestore Configuration
variable "firestore_databases" {
  description = "List of Firestore databases to create"
  type = list(object({
    name = string
    location = optional(string)
    type = optional(string, "FIRESTORE_NATIVE")
    concurrency_mode = optional(string, "OPTIMISTIC")
    app_engine_integration_mode = optional(string, "DISABLED")
    point_in_time_recovery = optional(string, "POINT_IN_TIME_RECOVERY_ENABLED")
    delete_protection = optional(string, "DELETE_PROTECTION_ENABLED")
    deletion_policy = optional(string, "DELETE")
    
    # Indexes
    indexes = optional(list(object({
      collection = string
      query_scope = optional(string, "COLLECTION")
      api_scope = optional(string, "ANY_API")
      fields = list(object({
        field_path = string
        order = optional(string)
        array_config = optional(string)
        vector_config = optional(object({
          dimension = number
          flat = optional(object({}))
        }))
      }))
    })), [])
    
    # Backup schedules
    backup_schedules = optional(list(object({
      retention = string
      daily_recurrence = optional(object({}))
      weekly_recurrence = optional(object({
        day = string
      }))
    })), [])
  }))
  default = []
}

# Cloud Storage Configuration
variable "storage_buckets" {
  description = "List of Cloud Storage buckets to create"
  type = list(object({
    name = string
    location = optional(string)
    storage_class = optional(string, "STANDARD")
    force_destroy = optional(bool, false)
    uniform_bucket_level_access = optional(bool, true)
    public_access_prevention = optional(string, "enforced")
    versioning_enabled = optional(bool, true)
    
    # Lifecycle rules
    lifecycle_rules = optional(list(object({
      action = object({
        type = string
        storage_class = optional(string)
      })
      condition = object({
        age = optional(number)
        created_before = optional(string)
        with_state = optional(string)
        matches_storage_class = optional(list(string))
        matches_prefix = optional(list(string))
        matches_suffix = optional(list(string))
        num_newer_versions = optional(number)
        custom_time_before = optional(string)
        days_since_custom_time = optional(number)
        days_since_noncurrent_time = optional(number)
        noncurrent_time_before = optional(string)
      })
    })), [])
    
    # Retention policy
    retention_policy = optional(object({
      retention_period = number
      is_locked = optional(bool, false)
    }))
    
    # Encryption
    encryption_key = optional(string)
    
    # CORS configuration
    cors = optional(list(object({
      origin = list(string)
      method = list(string)
      response_header = list(string)
      max_age_seconds = number
    })), [])
    
    # Website configuration
    website = optional(object({
      main_page_suffix = optional(string, "index.html")
      not_found_page = optional(string, "404.html")
    }))
    
    # Logging
    logging = optional(object({
      log_bucket = string
      log_object_prefix = optional(string, "")
    }))
    
    # Autoclass
    enable_autoclass = optional(bool, false)
    autoclass_terminal_storage_class = optional(string)
    
    # Soft delete policy
    soft_delete_policy = optional(object({
      retention_duration_seconds = number
    }))
    
    # Custom placement
    custom_placement_config = optional(object({
      data_locations = list(string)
    }))
    
    # IAM bindings
    iam_bindings = optional(list(object({
      role = string
      members = list(string)
      condition = optional(object({
        title = string
        description = optional(string)
        expression = string
      }))
    })), [])
    
    # Notifications
    notifications = optional(list(object({
      topic = string
      payload_format = optional(string, "JSON_API_V1")
      event_types = optional(list(string), ["OBJECT_FINALIZE"])
      object_name_prefix = optional(string)
      custom_attributes = optional(map(string), {})
    })), [])
    
    labels = optional(map(string), {})
  }))
  default = []
}

# Memorystore Configuration
variable "memorystore_instances" {
  description = "List of Memorystore instances to create (Redis and Memcached)"
  type = list(object({
    name = string
    engine = optional(string, "redis") # "redis" or "memcached"
    memory_size_gb = number
    region = optional(string)
    zone = optional(string)
    alternative_zone = optional(string)
    tier = optional(string, "STANDARD_HA")
    display_name = optional(string)
    
    # Network configuration
    authorized_network = optional(string)
    connect_mode = optional(string, "PRIVATE_SERVICE_ACCESS")
    reserved_ip_range = optional(string)
    
    # Redis-specific configuration
    redis_version = optional(string, "REDIS_7_0")
    redis_configs = optional(map(string), {})
    auth_enabled = optional(bool, true)
    transit_encryption_mode = optional(string, "SERVER_AUTHENTICATION")
    replica_count = optional(number)
    read_replicas_mode = optional(string)
    
    # Memcached-specific configuration
    cpu_count = optional(number, 1)
    node_count = optional(number, 1)
    zones = optional(list(string))
    memcache_version = optional(string, "MEMCACHE_1_6_15")
    memcache_parameters = optional(map(string), {})
    
    # Persistence configuration (Redis only)
    persistence_config = optional(object({
      persistence_mode = string
      rdb_snapshot_period = optional(string)
      rdb_snapshot_start_time = optional(string)
    }))
    
    # Maintenance policy
    maintenance_policy = optional(object({
      description = optional(string)
      weekly_maintenance_window = optional(list(object({
        day = string
        duration = string
        start_time = object({
          hours = number
          minutes = optional(number, 0)
          seconds = optional(number, 0)
          nanos = optional(number, 0)
        })
      })), [])
    }))
    
    # Encryption
    encryption_key = optional(string)
    
    labels = optional(map(string), {})
  }))
  default = []
}

# Dataflow Configuration
variable "dataflow_jobs" {
  description = "List of Dataflow jobs to create"
  type = list(object({
    name = string
    template_gcs_path = string
    region = optional(string)
    parameters = optional(map(string), {})
    additional_experiments = optional(list(string), [])
    autoscaling_algorithm = optional(string)
    enable_streaming_engine = optional(bool, false)
    ip_configuration = optional(string)
    kms_key_name = optional(string)
    launcher_machine_type = optional(string)
    machine_type = optional(string, "n1-standard-1")
    max_workers = optional(number, 10)
    network = optional(string)
    subnetwork = optional(string)
    num_workers = optional(number, 1)
    sdk_container_image = optional(string)
    service_account_email = optional(string)
    skip_wait_on_job_termination = optional(bool, false)
    staging_location = optional(string)
    temp_location = optional(string)
    transform_name_mappings = optional(map(string), {})
    labels = optional(map(string), {})
  }))
  default = []
}

# Pub/Sub Configuration
variable "pubsub_topics" {
  description = "List of Pub/Sub topics to create"
  type = list(object({
    name = string
    kms_key_name = optional(string)
    message_retention_duration = optional(string, "604800s")
    message_storage_policy = optional(object({
      allowed_persistence_regions = list(string)
    }))
    schema_settings = optional(object({
      schema = string
      encoding = optional(string, "JSON")
    }))
    ingestion_data_source_settings = optional(object({
      aws_kinesis = optional(object({
        stream_name = string
        consumer_arn = string
        aws_role_arn = string
        gcp_service_account = string
      }))
    }))
    
    # Subscriptions
    subscriptions = optional(list(object({
      name = string
      ack_deadline_seconds = optional(number, 20)
      message_retention_duration = optional(string, "604800s")
      retain_acked_messages = optional(bool, false)
      enable_message_ordering = optional(bool, false)
      filter = optional(string)
      
      expiration_policy = optional(object({
        ttl = string
      }))
      
      dead_letter_policy = optional(object({
        dead_letter_topic = string
        max_delivery_attempts = optional(number, 5)
      }))
      
      retry_policy = optional(object({
        minimum_backoff = optional(string, "10s")
        maximum_backoff = optional(string, "600s")
      }))
      
      push_config = optional(object({
        push_endpoint = string
        attributes = optional(map(string), {})
        oidc_token = optional(object({
          service_account_email = string
          audience = optional(string)
        }))
        no_wrapper = optional(object({
          write_metadata = bool
        }))
      }))
      
      bigquery_config = optional(object({
        table = string
        use_topic_schema = optional(bool, false)
        write_metadata = optional(bool, false)
        drop_unknown_fields = optional(bool, false)
        use_table_schema = optional(bool, false)
      }))
      
      cloud_storage_config = optional(object({
        bucket = string
        filename_prefix = optional(string)
        filename_suffix = optional(string)
        max_duration = optional(string, "300s")
        max_bytes = optional(number, 1000000)
        avro_config = optional(object({
          write_metadata = optional(bool, false)
        }))
      }))
      
      labels = optional(map(string), {})
    })), [])
    
    labels = optional(map(string), {})
  }))
  default = []
}

# Data Catalog Configuration
variable "data_catalog_entry_groups" {
  description = "List of Data Catalog entry groups to create"
  type = list(object({
    name = string
    region = optional(string)
    display_name = optional(string)
    description = optional(string)
  }))
  default = []
}

# Cloud Scheduler Configuration
variable "scheduler_jobs" {
  description = "List of Cloud Scheduler jobs for data processing"
  type = list(object({
    name = string
    region = optional(string)
    description = optional(string)
    schedule = string
    time_zone = optional(string, "UTC")
    
    retry_config = optional(object({
      retry_count = optional(number, 3)
      max_retry_duration = optional(string, "3600s")
      min_backoff_duration = optional(string, "5s")
      max_backoff_duration = optional(string, "3600s")
      max_doublings = optional(number, 16)
    }))
    
    http_target = optional(object({
      uri = string
      http_method = optional(string, "GET")
      body = optional(string)
      headers = optional(map(string), {})
      oauth_token = optional(object({
        service_account_email = string
        scope = optional(string)
      }))
      oidc_token = optional(object({
        service_account_email = string
        audience = optional(string)
      }))
    }))
    
    pubsub_target = optional(object({
      topic_name = string
      data = optional(string)
      attributes = optional(map(string), {})
    }))
    
    app_engine_target = optional(object({
      http_method = optional(string, "GET")
      relative_uri = optional(string, "/")
      body = optional(string)
      headers = optional(map(string), {})
      routing = optional(object({
        service = optional(string)
        version = optional(string)
        instance = optional(string)
      }))
    }))
  }))
  default = []
}