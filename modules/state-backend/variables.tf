variable "project_id" {
  description = "The GCP project ID where the state bucket will be created"
  type        = string
}

variable "bucket_name" {
  description = "The name of the GCS bucket for Terraform state storage"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-_.]*[a-z0-9]$", var.bucket_name))
    error_message = "Bucket name must start and end with a letter or number, and can contain lowercase letters, numbers, hyphens, underscores, and dots."
  }
}

variable "location" {
  description = "The location for the GCS bucket (region or multi-region)"
  type        = string
  default     = "us-central1"
}

variable "storage_class" {
  description = "The storage class of the GCS bucket"
  type        = string
  default     = "STANDARD"
  validation {
    condition     = contains(["STANDARD", "NEARLINE", "COLDLINE", "ARCHIVE"], var.storage_class)
    error_message = "Storage class must be one of: STANDARD, NEARLINE, COLDLINE, ARCHIVE."
  }
}

variable "force_destroy" {
  description = "When true, allows Terraform to destroy the bucket even if it contains objects"
  type        = bool
  default     = false
}

variable "enable_versioning" {
  description = "Enable versioning for the state bucket"
  type        = bool
  default     = true
}

variable "versioning_retain_days" {
  description = "Number of days to retain non-current versions"
  type        = number
  default     = 30
}

variable "lifecycle_rules" {
  description = "List of lifecycle rules to configure for the bucket"
  type = list(object({
    action = object({
      type          = string
      storage_class = optional(string)
    })
    condition = object({
      age                        = optional(number)
      created_before             = optional(string)
      with_state                 = optional(string)
      matches_storage_class      = optional(list(string))
      matches_prefix             = optional(list(string))
      matches_suffix             = optional(list(string))
      num_newer_versions         = optional(number)
      days_since_noncurrent_time = optional(number)
      noncurrent_time_before     = optional(string)
    })
  }))
  default = []
}

variable "retention_policy" {
  description = "Retention policy configuration for the bucket"
  type = object({
    retention_period = number
    is_locked        = optional(bool, false)
  })
  default = null
}

variable "encryption_key_name" {
  description = "The Cloud KMS key name for CMEK encryption (format: projects/PROJECT_ID/locations/LOCATION/keyRings/RING_NAME/cryptoKeys/KEY_NAME)"
  type        = string
  default     = null
}

variable "enable_uniform_bucket_level_access" {
  description = "Enable uniform bucket-level access (recommended for Terraform state)"
  type        = bool
  default     = true
}

variable "enable_public_access_prevention" {
  description = "Prevents public access to the bucket"
  type        = bool
  default     = true
}

variable "labels" {
  description = "Labels to apply to the bucket"
  type        = map(string)
  default = {
    purpose     = "terraform-state"
    managed-by  = "terraform"
    environment = "shared"
  }
}

variable "cors" {
  description = "CORS configuration for the bucket"
  type = list(object({
    origin          = list(string)
    method          = list(string)
    response_header = list(string)
    max_age_seconds = number
  }))
  default = []
}

variable "logging_config" {
  description = "Access logging configuration for the bucket"
  type = object({
    log_bucket        = string
    log_object_prefix = optional(string, "state-access-logs/")
  })
  default = null
}

variable "enable_autoclass" {
  description = "Enable Autoclass for automatic storage class management"
  type        = bool
  default     = false
}

variable "autoclass_terminal_storage_class" {
  description = "Terminal storage class for Autoclass-enabled buckets"
  type        = string
  default     = "NEARLINE"
  validation {
    condition     = contains(["NEARLINE", "ARCHIVE"], var.autoclass_terminal_storage_class)
    error_message = "Autoclass terminal storage class must be either NEARLINE or ARCHIVE."
  }
}

variable "replication_configuration" {
  description = "Cross-region replication configuration"
  type = object({
    role                 = string
    destination_bucket   = string
    destination_project  = optional(string)
    rewrite_destination  = optional(bool, false)
    delete_marker_status = optional(bool, false)
  })
  default = null
}

variable "soft_delete_policy" {
  description = "Soft delete policy configuration (2025 feature)"
  type = object({
    retention_duration_seconds = optional(number, 604800) # 7 days default
  })
  default = {
    retention_duration_seconds = 604800
  }
}

variable "custom_placement_config" {
  description = "Custom dual-region configuration for the bucket"
  type = object({
    data_locations = list(string)
  })
  default = null
}

# Enhanced Multi-Region Configuration
variable "multi_region_config" {
  description = "Advanced multi-region configuration for high availability"
  type = object({
    enabled = bool
    primary_region = string
    secondary_regions = list(string)
    replication_strategy = object({
      sync_replication = bool
      async_replication = bool
      cross_region_backup = bool
      failover_threshold_minutes = number
    })
    consistency_model = string # "eventual" or "strong"
    geo_redundancy = object({
      enabled = bool
      minimum_regions = number
      preferred_regions = list(string)
    })
  })
  default = {
    enabled = false
    primary_region = "us-central1"
    secondary_regions = ["us-east1"]
    replication_strategy = {
      sync_replication = false
      async_replication = true
      cross_region_backup = true
      failover_threshold_minutes = 5
    }
    consistency_model = "eventual"
    geo_redundancy = {
      enabled = false
      minimum_regions = 2
      preferred_regions = ["us-central1", "us-east1", "europe-west1"]
    }
  }
}

# Disaster Recovery Configuration
variable "disaster_recovery" {
  description = "Comprehensive disaster recovery configuration"
  type = object({
    enabled = bool
    backup_schedule = string
    retention_policy = object({
      daily_backups = number
      weekly_backups = number
      monthly_backups = number
      yearly_backups = number
      point_in_time_recovery_days = number
    })
    cross_region_backup = object({
      enabled = bool
      target_regions = list(string)
      encryption_key = optional(string)
      compression_enabled = bool
    })
    failover_config = object({
      automated_failover = bool
      manual_failover_only = bool
      health_check_interval = string
      recovery_time_objective = string
      recovery_point_objective = string
      notification_channels = list(string)
    })
    business_continuity = object({
      critical_data_protection = bool
      compliance_requirements = list(string)
      data_residency_requirements = list(string)
    })
  })
  default = {
    enabled = false
    backup_schedule = "0 2 * * *"
    retention_policy = {
      daily_backups = 7
      weekly_backups = 4
      monthly_backups = 12
      yearly_backups = 7
      point_in_time_recovery_days = 30
    }
    cross_region_backup = {
      enabled = false
      target_regions = []
      compression_enabled = true
    }
    failover_config = {
      automated_failover = false
      manual_failover_only = true
      health_check_interval = "60s"
      recovery_time_objective = "4h"
      recovery_point_objective = "1h"
      notification_channels = []
    }
    business_continuity = {
      critical_data_protection = true
      compliance_requirements = []
      data_residency_requirements = []
    }
  }
}

# Enhanced Security Configuration
variable "enhanced_security" {
  description = "Advanced security configuration for state storage"
  type = object({
    cmek_config = object({
      enabled = bool
      key_ring_location = string
      key_rotation_period = string
      multi_region_keys = bool
      backup_key_enabled = bool
    })
    access_control = object({
      enable_iam_conditions = bool
      time_based_access = bool
      ip_restrictions = list(string)
      service_account_restrictions = list(string)
    })
    audit_logging = object({
      enabled = bool
      log_bucket = string
      data_access_logs = bool
      admin_activity_logs = bool
      retention_days = number
    })
    vpc_security = object({
      private_endpoint_enabled = bool
      authorized_networks = list(string)
      vpc_sc_perimeter = optional(string)
    })
    threat_protection = object({
      malware_scanning = bool
      anomaly_detection = bool
      intrusion_detection = bool
      compliance_monitoring = bool
    })
  })
  default = {
    cmek_config = {
      enabled = false
      key_ring_location = "global"
      key_rotation_period = "7776000s"
      multi_region_keys = false
      backup_key_enabled = false
    }
    access_control = {
      enable_iam_conditions = false
      time_based_access = false
      ip_restrictions = []
      service_account_restrictions = []
    }
    audit_logging = {
      enabled = false
      log_bucket = ""
      data_access_logs = true
      admin_activity_logs = true
      retention_days = 365
    }
    vpc_security = {
      private_endpoint_enabled = false
      authorized_networks = []
    }
    threat_protection = {
      malware_scanning = false
      anomaly_detection = false
      intrusion_detection = false
      compliance_monitoring = false
    }
  }
}

# Performance Optimization
variable "performance_config" {
  description = "Performance optimization configuration"
  type = object({
    enable_transfer_acceleration = bool
    request_payer = string
    cdn_integration = object({
      enabled = bool
      cache_mode = string
      cache_ttl = number
    })
    bandwidth_optimization = object({
      enabled = bool
      compression = bool
      parallel_uploads = bool
      chunk_size_mb = number
    })
    regional_optimization = object({
      enabled = bool
      preferred_regions = list(string)
      latency_based_routing = bool
    })
  })
  default = {
    enable_transfer_acceleration = false
    request_payer = "BucketOwner"
    cdn_integration = {
      enabled = false
      cache_mode = "CACHE_ALL_STATIC"
      cache_ttl = 3600
    }
    bandwidth_optimization = {
      enabled = false
      compression = true
      parallel_uploads = true
      chunk_size_mb = 8
    }
    regional_optimization = {
      enabled = false
      preferred_regions = []
      latency_based_routing = false
    }
  }
}

# Compliance and Governance
variable "compliance_config" {
  description = "Compliance and governance configuration"
  type = object({
    enabled = bool
    frameworks = list(string)
    data_classification = string
    retention_compliance = object({
      legal_hold_enabled = bool
      regulatory_retention = number
      deletion_policy = string
    })
    access_governance = object({
      periodic_access_review = bool
      access_review_frequency = string
      automatic_access_removal = bool
    })
    data_governance = object({
      data_lineage_tracking = bool
      data_quality_monitoring = bool
      metadata_management = bool
      schema_validation = bool
    })
  })
  default = {
    enabled = false
    frameworks = []
    data_classification = "internal"
    retention_compliance = {
      legal_hold_enabled = false
      regulatory_retention = 2555
      deletion_policy = "automatic"
    }
    access_governance = {
      periodic_access_review = false
      access_review_frequency = "quarterly"
      automatic_access_removal = false
    }
    data_governance = {
      data_lineage_tracking = false
      data_quality_monitoring = false
      metadata_management = false
      schema_validation = false
    }
  }
}

# Monitoring and Alerting
variable "monitoring_config" {
  description = "Advanced monitoring and alerting configuration"
  type = object({
    enabled = bool
    metrics_collection = object({
      storage_metrics = bool
      access_metrics = bool
      performance_metrics = bool
      security_metrics = bool
    })
    alerting = object({
      enabled = bool
      alert_policies = list(object({
        name = string
        condition = string
        threshold = number
        notification_channels = list(string)
      }))
      slack_notifications = bool
      email_notifications = bool
      pagerduty_integration = bool
    })
    health_checks = object({
      enabled = bool
      check_frequency = string
      failure_threshold = number
      success_threshold = number
    })
    custom_dashboards = object({
      enabled = bool
      dashboard_configs = list(object({
        name = string
        description = string
        widgets = list(string)
      }))
    })
  })
  default = {
    enabled = false
    metrics_collection = {
      storage_metrics = true
      access_metrics = true
      performance_metrics = false
      security_metrics = false
    }
    alerting = {
      enabled = false
      alert_policies = []
      slack_notifications = false
      email_notifications = false
      pagerduty_integration = false
    }
    health_checks = {
      enabled = false
      check_frequency = "300s"
      failure_threshold = 3
      success_threshold = 2
    }
    custom_dashboards = {
      enabled = false
      dashboard_configs = []
    }
  }
}

# Cost Optimization
variable "cost_optimization" {
  description = "Cost optimization configuration"
  type = object({
    enabled = bool
    intelligent_tiering = object({
      enabled = bool
      archive_threshold_days = number
      coldline_threshold_days = number
    })
    lifecycle_optimization = object({
      enabled = bool
      optimize_for_cost = bool
      optimize_for_performance = bool
    })
    storage_insights = object({
      enabled = bool
      cost_analysis = bool
      usage_analytics = bool
      recommendation_engine = bool
    })
    budget_controls = object({
      enabled = bool
      monthly_budget = number
      alert_thresholds = list(number)
      automatic_cost_controls = bool
    })
  })
  default = {
    enabled = false
    intelligent_tiering = {
      enabled = false
      archive_threshold_days = 365
      coldline_threshold_days = 90
    }
    lifecycle_optimization = {
      enabled = false
      optimize_for_cost = true
      optimize_for_performance = false
    }
    storage_insights = {
      enabled = false
      cost_analysis = false
      usage_analytics = false
      recommendation_engine = false
    }
    budget_controls = {
      enabled = false
      monthly_budget = 100
      alert_thresholds = [0.8, 0.9, 1.0]
      automatic_cost_controls = false
    }
  }
}