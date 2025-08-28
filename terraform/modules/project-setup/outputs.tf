output "project_id" {
  description = "The created project ID"
  value       = module.bootstrap.project_id
}

output "project_number" {
  description = "The project number"
  value       = module.bootstrap.project_number
}

output "project_name" {
  description = "The project name"
  value       = module.bootstrap.project_name
}

output "state_bucket_name" {
  description = "Name of the Terraform state bucket"
  value       = module.state_backend.bucket_name
}

output "terraform_sa_email" {
  description = "Email of the Terraform service account"
  value       = module.state_backend.terraform_sa_email
}

output "service_account_emails" {
  description = "Map of additional service account emails"
  value       = length(var.service_accounts) > 0 ? module.service_accounts[0].service_account_emails : {}
}

output "enabled_apis" {
  description = "List of enabled APIs"
  value       = concat(module.bootstrap.enabled_apis, [for api in google_project_service.runtime_apis : api.service])
}
