output "project_id" {
  description = "The GCP project ID"
  value       = module.project_setup.project_id
}

output "project_number" {
  description = "The GCP project number"
  value       = module.project_setup.project_number
}

output "state_bucket_name" {
  description = "Name of the Terraform state bucket"
  value       = module.project_setup.state_bucket_name
}

output "terraform_sa_email" {
  description = "Email of the Terraform service account"
  value       = module.project_setup.terraform_sa_email
}

output "service_account_emails" {
  description = "Email addresses of created service accounts"
  value       = module.project_setup.service_account_emails
}