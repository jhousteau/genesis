# Outputs for Multi-Project Deployment Examples

# Simple deployment outputs
output "simple_projects" {
  description = "Project IDs from simple deployment"
  value       = try(module.simple_multi_project.project_ids, {})
}

output "simple_state_buckets" {
  description = "State buckets from simple deployment"
  value       = try(module.simple_multi_project.state_buckets, {})
}

# Complex deployment outputs
output "complex_projects" {
  description = "Detailed project information from complex deployment"
  value       = try(module.complex_multi_project.project_details, {})
}

output "complex_service_accounts" {
  description = "All service accounts from complex deployment"
  value       = try(module.complex_multi_project.all_service_accounts, {})
}

output "complex_workload_identity" {
  description = "Workload Identity configuration from complex deployment"
  value       = try(module.complex_multi_project.workload_identity_providers, {})
}

output "complex_networks" {
  description = "Network IDs from complex deployment"
  value       = try(module.complex_multi_project.network_ids, {})
}

# JSON-based deployment outputs
output "json_deployment_summary" {
  description = "Summary of JSON-based deployment"
  value       = try(module.json_based_deployment.summary, {})
}

# Environment deployment outputs
output "environment_projects_by_env" {
  description = "Projects grouped by environment"
  value       = try(module.environment_deployment.summary.projects_by_environment, {})
}

# Combined summary
output "total_deployment_summary" {
  description = "Summary of all deployments"
  value = {
    total_projects = sum([
      try(length(module.simple_multi_project.project_ids), 0),
      try(length(module.complex_multi_project.project_ids), 0),
      try(length(module.json_based_deployment.project_ids), 0),
      try(length(module.environment_deployment.project_ids), 0),
    ])

    deployments = {
      simple      = try(module.simple_multi_project.summary, null)
      complex     = try(module.complex_multi_project.summary, null)
      json_based  = try(module.json_based_deployment.summary, null)
      environment = try(module.environment_deployment.summary, null)
    }
  }
}

# Export configurations for use in other modules
output "exported_configurations" {
  description = "Configurations that can be used by downstream modules"
  value = {
    simple  = try(module.simple_multi_project.exported_configs, {})
    complex = try(module.complex_multi_project.exported_configs, {})
  }
  sensitive = false
}

# Generated tfvars for each project (useful for individual project management)
output "generated_project_configs" {
  description = "Generated terraform.tfvars content for each project"
  value = merge(
    try(module.simple_multi_project.generated_tfvars, {}),
    try(module.complex_multi_project.generated_tfvars, {}),
    try(module.json_based_deployment.generated_tfvars, {}),
    try(module.environment_deployment.generated_tfvars, {})
  )
}

# Validation warnings from all deployments
output "all_warnings" {
  description = "Compilation of all validation warnings"
  value = concat(
    try(module.simple_multi_project.validation_warnings, []),
    try(module.complex_multi_project.validation_warnings, []),
    try(module.json_based_deployment.validation_warnings, []),
    try(module.environment_deployment.validation_warnings, [])
  )
}
