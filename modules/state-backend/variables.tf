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