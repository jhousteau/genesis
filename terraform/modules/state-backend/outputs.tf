output "bucket_name" {
  description = "Name of the created GCS bucket"
  value       = google_storage_bucket.state_bucket.name
}

output "bucket_url" {
  description = "URL of the created GCS bucket"
  value       = google_storage_bucket.state_bucket.url
}

output "bucket_self_link" {
  description = "Self link of the created GCS bucket"
  value       = google_storage_bucket.state_bucket.self_link
}

output "terraform_sa_email" {
  description = "Email of the Terraform service account (if created)"
  value       = var.create_terraform_sa ? google_service_account.terraform_sa[0].email : null
}

output "terraform_sa_key" {
  description = "Unique identifier of the Terraform service account (if created)"
  value       = var.create_terraform_sa ? google_service_account.terraform_sa[0].unique_id : null
}