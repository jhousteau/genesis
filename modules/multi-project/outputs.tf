# Multi-Project Bootstrap Module Outputs

# Project information
output "project_ids" {
  description = "Map of project IDs that were bootstrapped"
  value       = { for k, v in module.bootstrap : k => v.project_id }
}

output "project_numbers" {
  description = "Map of project numbers"
  value       = { for k, v in module.bootstrap : k => v.project_number }
}

output "project_details" {
  description = "Detailed information about each bootstrapped project"
  value = { for k, v in module.bootstrap : k => {
    project_id     = v.project_id
    project_number = v.project_number
    project_name   = v.project_name
    enabled_apis   = v.enabled_apis
    environment    = try(local.merged_projects[k].environment, "production")
  }}
}

# State bucket information
output "state_buckets" {
  description = "Map of state bucket names for each project"
  value       = { for k, v in module.state_backend : k => v.bucket_name }
  sensitive   = false
}

output "state_bucket_urls" {
  description = "Map of state bucket URLs for each project"
  value       = { for k, v in module.state_backend : k => v.bucket_url }
}

output "terraform_backend_configs" {
  description = "Terraform backend configurations for each project"
  value = { for k, v in module.state_backend : k => {
    bucket = v.bucket_name
    prefix = "terraform/state"
  }}
}

# Service account information
output "terraform_service_accounts" {
  description = "Terraform service account emails for each project"
  value       = { for k, v in module.bootstrap : k => v.terraform_service_account_email if v.terraform_service_account_email != "" }
}

output "all_service_accounts" {
  description = "All service accounts created for each project"
  value = { for k, v in module.service_accounts : k => {
    emails = v.service_account_emails
    ids    = v.service_account_ids
  }}
}

output "cicd_service_accounts" {
  description = "CI/CD service account emails for each project"
  value = { for k, v in module.service_accounts : k => lookup(v.service_account_emails, "cicd", null) }
}

# Workload Identity Federation
output "workload_identity_pools" {
  description = "Workload Identity pool names for each project"
  value       = { for k, v in module.workload_identity : k => v.pool_name }
}

output "workload_identity_providers" {
  description = "Workload Identity provider information for each project"
  value = { for k, v in module.workload_identity : k => {
    pool_name     = v.pool_name
    providers     = v.provider_names
    service_accounts = v.service_account_emails
  }}
}

output "github_actions_config" {
  description = "GitHub Actions configuration for each project"
  value = { for k, v in module.workload_identity : k => v.github_actions_config if can(v.github_actions_config) }
}

# Network information
output "network_ids" {
  description = "Network IDs for projects with networking enabled"
  value       = { for k, v in google_compute_network.vpc : k => v.id }
}

output "subnet_ids" {
  description = "Subnet IDs for projects with networking enabled"
  value       = { for k, v in google_compute_subnetwork.subnets : k => v.id }
}

# Summary information
output "summary" {
  description = "Summary of the multi-project bootstrap deployment"
  value = {
    deployment_name     = var.deployment_name
    project_group      = var.project_group
    total_projects     = length(var.projects)
    projects_created   = length(module.bootstrap)
    state_buckets      = length(module.state_backend)
    service_accounts   = sum([for k, v in module.service_accounts : length(v.service_account_emails)])
    wif_pools         = length(module.workload_identity)
    networks_created   = length(google_compute_network.vpc)
    
    projects_by_environment = {
      for env in distinct([for p in local.merged_projects : try(p.environment, "production")]) :
      env => [for k, p in local.merged_projects : k if try(p.environment, "production") == env]
    }
    
    feature_flags = {
      state_buckets_enabled    = var.create_state_buckets
      service_accounts_enabled = var.create_service_accounts
      workload_identity_enabled = var.enable_workload_identity
    }
  }
}

# Validation results
output "validation_warnings" {
  description = "Any validation warnings from the deployment"
  value = concat(
    [for k, p in local.merged_projects : 
      "Project ${k} does not have org_id or folder_id set" 
      if p.org_id == "" && p.folder_id == ""],
    [for k, p in local.merged_projects : 
      "Project ${k} has a very high budget threshold: $${try(p.budget_amount, var.default_budget_amount)}" 
      if try(p.budget_amount, var.default_budget_amount) > 10000]
  )
}

# Export configurations for downstream use
output "exported_configs" {
  description = "Configurations that can be used by other Terraform modules"
  value = {
    for k, v in module.bootstrap : k => {
      project_id              = v.project_id
      terraform_backend_bucket = try(module.state_backend[k].bucket_name, null)
      terraform_sa_email      = v.terraform_service_account_email
      workload_identity_pool  = try(module.workload_identity[k].pool_name, null)
      network_id             = try(google_compute_network.vpc[k].id, null)
    }
  }
}

# Helper output for generating tfvars for each project
output "generated_tfvars" {
  description = "Generated tfvars content for each project"
  value = { for k, v in module.bootstrap : k => <<-EOT
    # Generated tfvars for project: ${k}
    project_id = "${v.project_id}"
    project_number = "${v.project_number}"
    terraform_service_account = "${v.terraform_service_account_email}"
    state_bucket = "${try(module.state_backend[k].bucket_name, "")}"
    workload_identity_pool = "${try(module.workload_identity[k].pool_name, "")}"
    network_id = "${try(google_compute_network.vpc[k].id, "")}"
    EOT
  }
}