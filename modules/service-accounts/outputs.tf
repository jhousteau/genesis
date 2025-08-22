/**
 * Service Accounts Module - Outputs
 *
 * Export service account information for use by other modules
 */

# Service account email addresses
output "service_account_emails" {
  description = "Map of service account keys to their email addresses"
  value = {
    for sa_key, sa in google_service_account.service_accounts :
    sa_key => sa.email
  }
}

# Service account IDs
output "service_account_ids" {
  description = "Map of service account keys to their unique IDs"
  value = {
    for sa_key, sa in google_service_account.service_accounts :
    sa_key => sa.unique_id
  }
}

# Service account names (for resource references)
output "service_account_names" {
  description = "Map of service account keys to their resource names"
  value = {
    for sa_key, sa in google_service_account.service_accounts :
    sa_key => sa.name
  }
}

# IAM member strings (for use in other IAM bindings)
output "iam_members" {
  description = "Map of service account keys to their IAM member strings"
  value = {
    for sa_key, sa in google_service_account.service_accounts :
    sa_key => "serviceAccount:${sa.email}"
  }
}

# Service account details (comprehensive)
output "service_accounts" {
  description = "Complete service account details including all attributes"
  value = {
    for sa_key, sa in google_service_account.service_accounts :
    sa_key => {
      email       = sa.email
      unique_id   = sa.unique_id
      name        = sa.name
      project     = sa.project
      account_id  = sa.account_id
      member      = "serviceAccount:${sa.email}"
      disabled    = sa.disabled
    }
  }
}

# Service account keys (base64 encoded)
output "service_account_keys" {
  description = "Map of service account keys (base64 encoded) - handle with care!"
  sensitive   = true
  value = {
    for sa_key, key in google_service_account_key.keys :
    sa_key => key.private_key
  }
}

# Secret Manager secret IDs for keys
output "key_secret_ids" {
  description = "Map of Secret Manager secret IDs containing service account keys"
  value = {
    for sa_key, secret in google_secret_manager_secret.sa_keys :
    sa_key => secret.secret_id
  }
}

# Project role bindings
output "project_role_bindings" {
  description = "List of project-level IAM role bindings created"
  value = [
    for binding in google_project_iam_member.project_roles : {
      project = binding.project
      role    = binding.role
      member  = binding.member
    }
  ]
}

# Organization role bindings
output "organization_role_bindings" {
  description = "List of organization-level IAM role bindings created"
  value = [
    for binding in google_organization_iam_member.org_roles : {
      org_id = binding.org_id
      role   = binding.role
      member = binding.member
    }
  ]
}

# Folder role bindings
output "folder_role_bindings" {
  description = "List of folder-level IAM role bindings created"
  value = [
    for binding in google_folder_iam_member.folder_roles : {
      folder = binding.folder
      role   = binding.role
      member = binding.member
    }
  ]
}

# Impersonation configurations
output "impersonation_configs" {
  description = "Map of service accounts and their authorized impersonators"
  value = {
    for sa_key, sa in var.service_accounts :
    sa_key => sa.impersonators
    if length(sa.impersonators) > 0
  }
}

# Summary output for quick reference
output "summary" {
  description = "Summary of created service accounts"
  value = {
    total_service_accounts = length(google_service_account.service_accounts)
    service_accounts_with_keys = length([
      for sa_key, sa in var.service_accounts :
      sa_key if sa.create_key == true
    ])
    service_accounts_with_impersonation = length([
      for sa_key, sa in var.service_accounts :
      sa_key if length(sa.impersonators) > 0
    ])
    keys_in_secret_manager = var.store_keys_in_secret_manager ? length(google_secret_manager_secret.sa_keys) : 0
  }
}
# Enhanced Security Outputs
output "workload_identity_pools" {
  description = "Map of Workload Identity pools created"
  value = {
    for pool_id, pool in google_iam_workload_identity_pool.pools :
    pool_id => {
      name         = pool.name
      display_name = pool.display_name
      description  = pool.description
      state        = pool.state
    }
  }
}

output "workload_identity_providers" {
  description = "Map of Workload Identity providers created"
  value = {
    for key, provider in google_iam_workload_identity_pool_provider.providers :
    key => {
      name              = provider.name
      display_name      = provider.display_name
      description       = provider.description
      state             = provider.state
      attribute_mapping = provider.attribute_mapping
    }
  }
}

output "custom_iam_roles" {
  description = "Custom IAM roles created"
  value = {
    for role_id, role in google_project_iam_custom_role.custom_roles :
    role_id => {
      name        = role.name
      title       = role.title
      description = role.description
      permissions = role.permissions
      stage       = role.stage
    }
  }
}

output "cross_project_bindings" {
  description = "Cross-project IAM bindings created"
  value = [
    for binding in google_project_iam_member.cross_project_roles : {
      project = binding.project
      role    = binding.role
      member  = binding.member
    }
  ]
}

output "monitoring_metrics" {
  description = "Custom monitoring metrics for service accounts"
  value = {
    for metric_name, metric in google_monitoring_metric_descriptor.service_account_metrics :
    metric_name => {
      type        = metric.type
      metric_kind = metric.metric_kind
      value_type  = metric.value_type
      description = metric.description
    }
  }
}

output "alert_policies" {
  description = "Monitoring alert policies for service accounts"
  value = {
    for policy_name, policy in google_monitoring_alert_policy.service_account_alerts :
    policy_name => {
      name                  = policy.name
      display_name          = policy.display_name
      description           = policy.description
      notification_channels = policy.notification_channels
    }
  }
}

output "key_rotation_jobs" {
  description = "Key rotation scheduler jobs"
  value = {
    for sa_key, job in google_cloud_scheduler_job.key_rotation :
    sa_key => {
      name        = job.name
      description = job.description
      schedule    = job.schedule
      time_zone   = job.time_zone
    }
  }
}

output "backup_configuration" {
  description = "Service account backup configuration"
  value = var.backup_config.enabled ? {
    backup_bucket = google_storage_bucket.service_account_backup[0].name
    backup_url    = google_storage_bucket.service_account_backup[0].url
    schedule      = google_cloud_scheduler_job.backup_scheduler[0].schedule
    retention_days = var.backup_config.retention_days
    cross_region  = var.backup_config.cross_region_backup
  } : null
}

# Enhanced Configuration Summary
output "enhanced_summary" {
  description = "Comprehensive summary of enhanced service account features"
  value = {
    service_accounts = {
      total_count = length(google_service_account.service_accounts)
      with_keys   = length([for sa_key, sa in var.service_accounts : sa_key if sa.create_key])
      with_impersonation = length([for sa_key, sa in var.service_accounts : sa_key if length(sa.impersonators) > 0])
    }
    workload_identity = {
      enabled = var.workload_identity_config.enabled
      pools_count = length(google_iam_workload_identity_pool.pools)
      providers_count = length(google_iam_workload_identity_pool_provider.providers)
      bindings_count = length(var.workload_identity_config.service_account_bindings)
    }
    advanced_iam = {
      conditional_access = var.advanced_iam_config.enable_conditional_access
      custom_roles_count = length(google_project_iam_custom_role.custom_roles)
      conditional_bindings_count = length(var.advanced_iam_config.conditional_bindings)
    }
    security_features = {
      key_rotation_enabled = var.enhanced_security.enable_key_rotation
      automated_rotation = var.enhanced_security.automated_key_rotation
      access_logging = var.enhanced_security.enable_access_logging
      usage_monitoring = var.enhanced_security.enable_usage_monitoring
      mfa_required = var.enhanced_security.security_policies.require_mfa
    }
    cross_project_access = {
      enabled = var.cross_project_access.enabled
      target_projects_count = length(var.cross_project_access.target_projects)
      shared_vpc_projects_count = length(var.cross_project_access.shared_vpc_projects)
      folder_access_count = length(var.cross_project_access.folder_access)
    }
    cicd_integration = {
      github_actions = var.cicd_platforms.github_actions.enabled
      gitlab_ci = var.cicd_platforms.gitlab_ci.enabled
      azure_devops = var.cicd_platforms.azure_devops.enabled
      jenkins = var.cicd_platforms.jenkins.enabled
    }
    monitoring = {
      enabled = var.monitoring_config.enabled
      custom_metrics_count = length(google_monitoring_metric_descriptor.service_account_metrics)
      alert_policies_count = length(google_monitoring_alert_policy.service_account_alerts)
      anomaly_detection = var.monitoring_config.alerting.anomaly_detection
    }
    backup_and_recovery = {
      enabled = var.backup_config.enabled
      cross_region_backup = var.backup_config.cross_region_backup
      disaster_recovery = var.backup_config.disaster_recovery.enabled
      retention_days = var.backup_config.retention_days
    }
    compliance = {
      data_governance = var.enhanced_security.compliance_settings.enable_data_governance
      audit_trail = var.enhanced_security.compliance_settings.enable_audit_trail
      retention_policy_days = var.enhanced_security.compliance_settings.retention_policy_days
    }
    created_at = timestamp()
  }
}

# CI/CD Platform Integration Outputs
output "github_actions_config" {
  description = "GitHub Actions Workload Identity configuration"
  value = var.cicd_platforms.github_actions.enabled ? {
    enabled = true
    repositories = var.cicd_platforms.github_actions.repositories
    pool_name = var.workload_identity_config.enabled ? "projects/${var.project_id}/locations/global/workloadIdentityPools/github-pool" : null
  } : null
}

output "gitlab_ci_config" {
  description = "GitLab CI Workload Identity configuration"
  value = var.cicd_platforms.gitlab_ci.enabled ? {
    enabled = true
    projects = var.cicd_platforms.gitlab_ci.projects
    pool_name = var.workload_identity_config.enabled ? "projects/${var.project_id}/locations/global/workloadIdentityPools/gitlab-pool" : null
  } : null
}

output "azure_devops_config" {
  description = "Azure DevOps Workload Identity configuration"
  value = var.cicd_platforms.azure_devops.enabled ? {
    enabled = true
    organizations = var.cicd_platforms.azure_devops.organizations
    pool_name = var.workload_identity_config.enabled ? "projects/${var.project_id}/locations/global/workloadIdentityPools/azure-pool" : null
  } : null
}

output "jenkins_config" {
  description = "Jenkins Workload Identity configuration"
  value = var.cicd_platforms.jenkins.enabled ? {
    enabled = true
    instances = var.cicd_platforms.jenkins.instances
    pool_name = var.workload_identity_config.enabled ? "projects/${var.project_id}/locations/global/workloadIdentityPools/jenkins-pool" : null
  } : null
}
