output "project_id" {
  description = "The project ID"
  value       = google_project.project.project_id
}

output "project_number" {
  description = "The project number"
  value       = google_project.project.number
}

output "project_name" {
  description = "The project name"
  value       = google_project.project.name
}

output "enabled_apis" {
  description = "List of enabled APIs"
  value       = [for api in google_project_service.apis : api.service]
}

output "default_service_account_email" {
  description = "Email of the default service account (if created)"
  value       = var.create_default_service_account ? google_service_account.default[0].email : null
}

output "default_service_account_key" {
  description = "Unique identifier of the default service account (if created)"
  value       = var.create_default_service_account ? google_service_account.default[0].unique_id : null
}