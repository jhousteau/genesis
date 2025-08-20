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