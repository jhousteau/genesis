output "bucket_name" {
  description = "The name of the created GCS bucket for Terraform state"
  value       = google_storage_bucket.state_bucket.name
}

output "bucket_url" {
  description = "The URL of the created GCS bucket"
  value       = google_storage_bucket.state_bucket.url
}

output "bucket_self_link" {
  description = "The URI of the created GCS bucket"
  value       = google_storage_bucket.state_bucket.self_link
}

output "bucket_id" {
  description = "The ID of the created GCS bucket"
  value       = google_storage_bucket.state_bucket.id
}

output "bucket_location" {
  description = "The location of the created GCS bucket"
  value       = google_storage_bucket.state_bucket.location
}

output "bucket_storage_class" {
  description = "The storage class of the created GCS bucket"
  value       = google_storage_bucket.state_bucket.storage_class
}

output "versioning_enabled" {
  description = "Whether versioning is enabled on the bucket"
  value       = var.enable_versioning
}

output "encryption_key" {
  description = "The KMS key used for bucket encryption (if configured)"
  value       = var.encryption_key_name
  sensitive   = true
}

output "uniform_bucket_level_access" {
  description = "Whether uniform bucket-level access is enabled"
  value       = var.enable_uniform_bucket_level_access
}

output "public_access_prevention" {
  description = "The public access prevention status of the bucket"
  value       = google_storage_bucket.state_bucket.public_access_prevention
}

output "lifecycle_rules" {
  description = "The lifecycle rules configured for the bucket"
  value       = google_storage_bucket.state_bucket.lifecycle_rule
}

output "retention_policy" {
  description = "The retention policy configured for the bucket"
  value       = google_storage_bucket.state_bucket.retention_policy
}

output "logging_config" {
  description = "The logging configuration for the bucket"
  value = google_storage_bucket.state_bucket.logging != null ? {
    log_bucket        = google_storage_bucket.state_bucket.logging[0].log_bucket
    log_object_prefix = google_storage_bucket.state_bucket.logging[0].log_object_prefix
  } : null
}

output "log_bucket_name" {
  description = "The name of the logging bucket (if created)"
  value       = local.create_logging_bucket ? google_storage_bucket.log_bucket[0].name : null
}

output "autoclass_enabled" {
  description = "Whether Autoclass is enabled on the bucket"
  value       = var.enable_autoclass
}

output "soft_delete_policy" {
  description = "The soft delete policy configuration"
  value       = var.soft_delete_policy
}

output "replication_bucket_name" {
  description = "The name of the replication destination bucket (if configured)"
  value       = var.replication_configuration != null ? google_storage_bucket.replication_bucket[0].name : null
}

output "replication_bucket_url" {
  description = "The URL of the replication destination bucket (if configured)"
  value       = var.replication_configuration != null ? google_storage_bucket.replication_bucket[0].url : null
}

output "replication_job_name" {
  description = "The name of the replication transfer job (if configured)"
  value       = var.replication_configuration != null ? google_storage_transfer_job.replication[0].name : null
}

output "terraform_backend_config" {
  description = "Terraform backend configuration block for using this bucket"
  value = <<-EOT
    backend "gcs" {
      bucket = "${google_storage_bucket.state_bucket.name}"
      prefix = "terraform/state"
    }
  EOT
}

output "labels" {
  description = "The labels applied to the bucket"
  value       = google_storage_bucket.state_bucket.labels
}
# Enhanced Multi-Region Outputs
output "multi_region_buckets" {
  description = "Map of multi-region replica buckets"
  value = {
    for region, bucket in google_storage_bucket.multi_region_buckets :
    region => {
      name      = bucket.name
      url       = bucket.url
      location  = bucket.location
      self_link = bucket.self_link
    }
  }
}

output "multi_region_config" {
  description = "Multi-region configuration summary"
  value = var.multi_region_config.enabled ? {
    enabled           = var.multi_region_config.enabled
    primary_region    = var.multi_region_config.primary_region
    secondary_regions = var.multi_region_config.secondary_regions
    replication_strategy = var.multi_region_config.replication_strategy
    consistency_model = var.multi_region_config.consistency_model
    geo_redundancy   = var.multi_region_config.geo_redundancy
  } : null
}

# Enhanced Security Outputs
output "cmek_keys" {
  description = "Customer-managed encryption keys"
  value = var.enhanced_security.cmek_config.enabled ? {
    primary_key = {
      name     = google_kms_crypto_key.state_key[0].name
      id       = google_kms_crypto_key.state_key[0].id
      key_ring = google_kms_key_ring.state_keyring[0].name
    }
    regional_keys = {
      for region, key in google_kms_crypto_key.regional_keys :
      region => {
        name     = key.name
        id       = key.id
        key_ring = google_kms_key_ring.regional_keyrings[region].name
      }
    }
    backup_key = var.enhanced_security.cmek_config.backup_key_enabled ? {
      name = google_kms_crypto_key.backup_key[0].name
      id   = google_kms_crypto_key.backup_key[0].id
    } : null
  } : null
  sensitive = false
}

# Comprehensive State Backend Summary
output "state_backend_summary" {
  description = "Comprehensive summary of the enhanced state backend configuration"
  value = {
    primary_bucket = {
      name         = google_storage_bucket.state_bucket.name
      url          = google_storage_bucket.state_bucket.url
      location     = google_storage_bucket.state_bucket.location
      storage_class = google_storage_bucket.state_bucket.storage_class
    }
    multi_region = {
      enabled = var.multi_region_config.enabled
      regions = var.multi_region_config.enabled ? local.all_regions : [var.location]
      replica_count = var.multi_region_config.enabled ? length(var.multi_region_config.secondary_regions) : 0
    }
    security = {
      encryption_type = var.enhanced_security.cmek_config.enabled ? "CMEK" : "Google-managed"
      access_control  = var.enhanced_security.access_control.enable_iam_conditions ? "Advanced" : "Standard"
      audit_logging   = var.enhanced_security.audit_logging.enabled
    }
    disaster_recovery = {
      enabled              = var.disaster_recovery.enabled
      cross_region_backup  = var.disaster_recovery.cross_region_backup.enabled
      automated_failover   = var.disaster_recovery.failover_config.automated_failover
      rto                 = var.disaster_recovery.failover_config.recovery_time_objective
      rpo                 = var.disaster_recovery.failover_config.recovery_point_objective
    }
    monitoring = {
      enabled       = var.monitoring_config.enabled
      health_checks = var.monitoring_config.health_checks.enabled
      alerting      = var.monitoring_config.alerting.enabled
    }
    cost_optimization = {
      enabled             = var.cost_optimization.enabled
      intelligent_tiering = var.cost_optimization.intelligent_tiering.enabled
      budget_controls     = var.cost_optimization.budget_controls.enabled
      lifecycle_rules     = length(local.lifecycle_rules)
    }
    compliance = {
      enabled     = var.compliance_config.enabled
      frameworks  = var.compliance_config.frameworks
      classification = var.compliance_config.data_classification
    }
    performance = {
      transfer_acceleration = var.performance_config.enable_transfer_acceleration
      cdn_integration      = var.performance_config.cdn_integration.enabled
      bandwidth_optimization = var.performance_config.bandwidth_optimization.enabled
    }
    created_at = timestamp()
  }
}
