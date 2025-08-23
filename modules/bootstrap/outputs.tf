/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

# Project Outputs
output "project_id" {
  description = "The ID of the created project"
  value       = google_project.project.project_id
}

output "project_number" {
  description = "The numeric identifier of the created project"
  value       = google_project.project.number
}

output "project_name" {
  description = "The display name of the created project"
  value       = google_project.project.name
}

# API Outputs
output "enabled_apis" {
  description = "List of enabled APIs in the project"
  value       = keys(google_project_service.apis)
}

output "enabled_api_identities" {
  description = "Map of enabled API service identities"
  value = {
    for k, v in google_project_service_identity.api_identities :
    k => v.email
  }
}

# Service Account Outputs
output "service_account_email" {
  description = "Email of the default service account"
  value       = local.service_account_email
  sensitive   = false
}

output "service_account_id" {
  description = "Unique ID of the default service account"
  value       = var.create_default_service_account ? google_service_account.default[0].unique_id : ""
}

output "service_account_name" {
  description = "Fully qualified name of the default service account"
  value       = var.create_default_service_account ? google_service_account.default[0].name : ""
}

output "service_account_key" {
  description = "Base64 encoded private key of the default service account"
  value       = var.create_default_service_account ? google_service_account_key.default[0].private_key : ""
  sensitive   = true
}

# Budget Outputs
output "budget_name" {
  description = "The resource name of the budget, if created"
  value       = var.budget_amount != null ? google_billing_budget.budget[0].name : ""
}

output "budget_amount" {
  description = "The budgeted amount in USD"
  value       = var.budget_amount
}

# Storage Outputs
output "bootstrap_bucket_name" {
  description = "The name of the bootstrap state bucket"
  value       = var.create_default_service_account ? google_storage_bucket.bootstrap_state[0].name : ""
}

output "bootstrap_bucket_url" {
  description = "The URL of the bootstrap state bucket"
  value       = var.create_default_service_account ? google_storage_bucket.bootstrap_state[0].url : ""
}

# Configuration Outputs
output "organization_id" {
  description = "The organization ID"
  value       = var.org_id
}

output "billing_account" {
  description = "The billing account ID"
  value       = var.billing_account
}

output "folder_id" {
  description = "The folder ID (if project is in a folder)"
  value       = var.folder_id
}

output "default_region" {
  description = "The default region for resources"
  value       = var.default_region
}

output "default_zone" {
  description = "The default zone for resources"
  value       = local.default_zone
}

output "labels" {
  description = "The labels applied to the project"
  value       = local.merged_labels
}

# IAM Outputs
output "project_iam_roles" {
  description = "Map of IAM roles granted on the project"
  value = merge(
    {
      for member in google_project_iam_member.default_service_account :
      "${member.role}_${replace(member.member, "/[^a-zA-Z0-9]/", "_")}" => {
        role   = member.role
        member = member.member
      }
    },
    {
      for member in google_project_iam_member.api_identity_roles :
      "${member.role}_${replace(member.member, "/[^a-zA-Z0-9]/", "_")}" => {
        role   = member.role
        member = member.member
      }
    }
  )
}

# Computed Outputs
output "project_services_map" {
  description = "Map of enabled services with their activation status"
  value = {
    for api in local.activate_apis :
    api => {
      enabled = true
      project = google_project.project.project_id
    }
  }
}

output "gcp_service_account_compute" {
  description = "The compute service agent service account"
  value       = "service-${google_project.project.number}@compute-system.iam.gserviceaccount.com"
}

output "gcp_service_account_gke" {
  description = "The GKE service agent service account"
  value       = "service-${google_project.project.number}@container-engine-robot.iam.gserviceaccount.com"
}

output "gcp_service_account_cloudbuild" {
  description = "The Cloud Build service agent service account"
  value       = "${google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# Essential Contacts Outputs
output "essential_contacts" {
  description = "Map of configured essential contacts"
  value = {
    for k, v in google_essential_contacts_contact.contacts :
    k => {
      email                   = v.email
      notification_categories = v.notification_category_subscriptions
    }
  }
}

# Organization Policy Outputs
output "org_policies" {
  description = "Map of organization policies applied to the project"
  value = {
    for k, v in google_project_organization_policy.org_policies :
    k => {
      constraint = v.constraint
      project    = v.project
    }
  }
}

# Terraform State Configuration Output
output "terraform_backend_config" {
  description = "Terraform backend configuration for storing state in GCS"
  value = var.create_default_service_account ? {
    backend = "gcs"
    config = {
      bucket = google_storage_bucket.bootstrap_state[0].name
      prefix = "terraform/state"
    }
  } : null
}

# Enhanced Budget Outputs
output "budget_details" {
  description = "Detailed budget configuration and status"
  value = var.budget_amount != null ? {
    name                  = google_billing_budget.budget[0].name
    amount                = var.budget_amount
    calendar_period       = var.budget_calendar_period
    alert_percentages     = var.budget_alert_percentages
    notification_channels = var.budget_notification_channels
  } : null
}

# Asset Inventory Outputs
output "asset_feeds" {
  description = "Cloud Asset Inventory feeds configuration"
  value = {
    for feed_name, feed in google_cloud_asset_project_feed.feeds :
    feed_name => {
      name         = feed.feed_id
      content_type = feed.content_type
      asset_types  = feed.asset_types
    }
  }
}

# Resource Manager Tags Outputs
output "resource_tags" {
  description = "Resource Manager tags created for the project"
  value = {
    tag_keys = {
      for key_name, key in google_tags_tag_key.keys :
      key_name => {
        id         = key.id
        short_name = key.short_name
        parent     = key.parent
      }
    }
  }
}

# Security Outputs
output "security_center_modules" {
  description = "Security Command Center custom modules"
  value = {
    for module_name, module in google_scc_project_custom_module.security_modules :
    module_name => {
      name             = module.name
      display_name     = module.display_name
      enablement_state = module.enablement_state
    }
  }
}

# Monitoring Outputs
output "monitoring_workspace" {
  description = "Cloud Monitoring workspace configuration"
  value = var.enable_monitoring_workspace ? {
    metrics_scope = google_monitoring_monitored_project.primary[0].metrics_scope
    name          = google_monitoring_monitored_project.primary[0].name
  } : null
}

output "monitoring_alerts" {
  description = "Monitoring alert policies created"
  value = var.budget_amount != null && var.enable_monitoring_alerts ? {
    budget_alert = {
      name         = google_monitoring_alert_policy.budget_alerts[0].name
      display_name = google_monitoring_alert_policy.budget_alerts[0].display_name
    }
  } : {}
}

# Logging Outputs
output "logging_sinks" {
  description = "Logging sinks configuration"
  value = {
    for sink_name, sink in google_logging_project_sink.sinks :
    sink_name => {
      name                   = sink.name
      destination            = sink.destination
      filter                 = sink.filter
      unique_writer_identity = sink.unique_writer_identity
      writer_identity        = sink.writer_identity
    }
  }
}

# Quota Outputs
output "quota_overrides" {
  description = "Service quota overrides applied"
  value = {
    for override_key, override in google_service_usage_consumer_quota_override.quota_overrides :
    override_key => {
      service        = override.service
      metric         = override.metric
      limit          = override.limit
      override_value = override.override_value
    }
  }
}

# VPC Service Controls Outputs
output "vpc_service_controls" {
  description = "VPC Service Controls perimeter configuration"
  value = var.vpc_service_controls != null ? {
    perimeter_name      = google_access_context_manager_service_perimeter.perimeter[0].title
    resources           = google_access_context_manager_service_perimeter.perimeter[0].status[0].resources
    restricted_services = google_access_context_manager_service_perimeter.perimeter[0].status[0].restricted_services
  } : null
}

# Compliance and Audit Outputs
output "audit_config" {
  description = "Project audit logging configuration"
  value = length(var.audit_log_config.data_access) > 0 ? {
    enabled          = true
    data_access_logs = var.audit_log_config.data_access
    } : {
    enabled = false
  }
}

# Enhanced Features Outputs

# Multi-Region Configuration Outputs
output "multi_region_buckets" {
  description = "Multi-region bootstrap state bucket replicas"
  value = {
    for region, bucket in google_storage_bucket.bootstrap_state_replica :
    region => {
      name     = bucket.name
      url      = bucket.url
      location = bucket.location
    }
  }
}

# CMEK Configuration Outputs
output "cmek_keys" {
  description = "Customer-managed encryption keys created"
  value = var.enhanced_security.cmek_config.enabled ? {
    key_ring = google_kms_key_ring.bootstrap_keyring[0].name
    keys = {
      for service, key in google_kms_crypto_key.bootstrap_keys :
      service => {
        name    = key.name
        id      = key.id
        purpose = key.purpose
      }
    }
  } : null
  sensitive = false
}

# Custom IAM Roles Outputs
output "custom_iam_roles" {
  description = "Custom IAM roles created for the project"
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

# Security Policies Outputs
output "security_policies" {
  description = "Cloud Armor security policies created"
  value = {
    for policy_name, policy in google_compute_security_policy.security_policies :
    policy_name => {
      name        = policy.name
      description = policy.description
      self_link   = policy.self_link
    }
  }
}

# Advanced Monitoring Outputs
output "custom_metrics" {
  description = "Custom monitoring metrics created"
  value = {
    for metric_name, metric in google_monitoring_metric_descriptor.custom_metrics :
    metric_name => {
      type        = metric.type
      metric_kind = metric.metric_kind
      value_type  = metric.value_type
      description = metric.description
    }
  }
}

output "log_based_metrics" {
  description = "Log-based metrics created for monitoring"
  value = {
    for metric_name, metric in google_logging_metric.log_based_metrics :
    metric_name => {
      name        = metric.name
      filter      = metric.filter
      description = metric.description
    }
  }
}

output "advanced_alert_policies" {
  description = "Advanced monitoring alert policies"
  value = {
    for policy_name, policy in google_monitoring_alert_policy.advanced_alerts :
    policy_name => {
      name                  = policy.name
      display_name          = policy.display_name
      description           = policy.description
      notification_channels = policy.notification_channels
    }
  }
}

# Disaster Recovery Outputs
output "backup_jobs" {
  description = "Automated backup jobs for disaster recovery"
  value = {
    for region, job in google_cloud_scheduler_job.backup_jobs :
    region => {
      name        = job.name
      description = job.description
      schedule    = job.schedule
      region      = job.region
    }
  }
}

# Cost Optimization Outputs
output "cost_anomaly_budget" {
  description = "Cost anomaly detection budget configuration"
  value = var.cost_optimization.cost_anomaly_detection.enabled && var.budget_amount != null ? {
    name          = google_billing_budget.cost_anomaly_budget[0].name
    display_name  = google_billing_budget.cost_anomaly_budget[0].display_name
    threshold     = var.cost_optimization.cost_anomaly_detection.threshold_percentage
    notifications = var.cost_optimization.cost_anomaly_detection.notification_channels
  } : null
}

# Compliance Outputs
output "compliance_policies" {
  description = "Compliance organization policies enforced"
  value = {
    for constraint, policy in google_project_organization_policy.compliance_policies :
    constraint => {
      constraint = policy.constraint
      project    = policy.project
    }
  }
}

# Binary Authorization Outputs
output "binary_authorization" {
  description = "Binary Authorization policy configuration"
  value = var.enhanced_security.enable_binary_authorization ? {
    policy_name = google_binary_authorization_policy.policy[0].name
    project     = google_binary_authorization_policy.policy[0].project
    default_admission_rule = {
      evaluation_mode  = "REQUIRE_ATTESTATION"
      enforcement_mode = "ENFORCED_BLOCK_AND_AUDIT_LOG"
    }
  } : null
}

# Vulnerability Scanning Outputs
output "vulnerability_scanning" {
  description = "Container vulnerability scanning configuration"
  value = var.enhanced_security.vulnerability_scanning.enabled ? {
    note_name = google_container_analysis_note.vulnerability_note[0].name
    project   = google_container_analysis_note.vulnerability_note[0].project
    frequency = var.enhanced_security.vulnerability_scanning.scan_frequency
  } : null
}

# Enhanced Configuration Summary
output "enhanced_project_summary" {
  description = "Comprehensive summary including all enhanced features"
  value = {
    project = {
      id     = google_project.project.project_id
      number = google_project.project.number
      name   = google_project.project.name
    }
    organization = {
      id     = var.org_id
      folder = var.folder_id
    }
    billing = {
      account = var.billing_account
      budget  = var.budget_amount
    }
    location = {
      region = var.default_region
      zone   = local.default_zone
    }
    multi_region = {
      enabled           = var.multi_region_config.enabled
      primary_region    = var.multi_region_config.primary_region
      secondary_regions = var.multi_region_config.secondary_regions
    }
    security = {
      enhanced_features = {
        binary_authorization   = var.enhanced_security.enable_binary_authorization
        workload_identity      = var.enhanced_security.enable_workload_identity
        shielded_vms           = var.enhanced_security.enable_shielded_vms
        os_login               = var.enhanced_security.enable_os_login
        confidential_computing = var.enhanced_security.enable_confidential_computing
        vulnerability_scanning = var.enhanced_security.vulnerability_scanning.enabled
        cmek_enabled           = var.enhanced_security.cmek_config.enabled
      }
      security_center_enabled = var.enable_security_center
      vpc_service_controls    = var.vpc_service_controls != null
      audit_logging_enabled   = length(var.audit_log_config.data_access) > 0
      cloud_armor_enabled     = var.network_security.enable_cloud_armor
    }
    compliance = {
      automation_enabled = var.compliance_automation.enabled
      frameworks         = var.compliance_automation.frameworks
      auto_remediation   = var.compliance_automation.auto_remediation
      policy_enforcement = var.compliance_automation.policy_enforcement
    }
    cost_optimization = {
      committed_use_discounts = var.cost_optimization.enable_committed_use_discounts
      sustained_use_discounts = var.cost_optimization.enable_sustained_use_discounts
      preemptible_instances   = var.cost_optimization.enable_preemptible_instances
      anomaly_detection       = var.cost_optimization.cost_anomaly_detection.enabled
      resource_right_sizing   = var.cost_optimization.resource_right_sizing
      idle_detection          = var.cost_optimization.idle_resource_detection
    }
    monitoring = {
      workspace_enabled    = var.enable_monitoring_workspace
      alerts_enabled       = var.enable_monitoring_alerts
      advanced_monitoring  = var.advanced_monitoring.enabled
      custom_metrics_count = length(var.advanced_monitoring.custom_metrics)
      log_metrics_count    = length(var.advanced_monitoring.log_based_metrics)
      alert_policies_count = length(var.advanced_monitoring.alerting_policies)
      logging_sinks        = length(var.logging_sinks)
    }
    disaster_recovery = {
      enabled                  = var.disaster_recovery.enabled
      cross_region_replication = var.disaster_recovery.cross_region_replication.enabled
      automated_failover       = var.disaster_recovery.failover_config.automated_failover
      rto                      = var.disaster_recovery.failover_config.recovery_time_objective
      rpo                      = var.disaster_recovery.failover_config.recovery_point_objective
    }
    network_security = {
      private_google_access   = var.network_security.enable_private_google_access
      private_service_connect = var.network_security.enable_private_service_connect
      cloud_armor             = var.network_security.enable_cloud_armor
      ddos_protection         = var.network_security.enable_ddos_protection
      firewall_rules_count    = length(var.network_security.firewall_rules)
    }
    advanced_iam = {
      conditions_enabled    = var.advanced_iam.enable_iam_conditions
      custom_roles_count    = length(var.advanced_iam.custom_roles)
      conditional_bindings  = length(var.advanced_iam.conditional_bindings)
      impersonation_enabled = var.advanced_iam.service_account_impersonation.enabled
    }
    apis_enabled   = length(local.activate_apis)
    labels_applied = local.merged_labels
    created_at     = timestamp()
  }
}

# Comprehensive Project Configuration Summary (Legacy - for backward compatibility)
output "project_summary" {
  description = "Comprehensive summary of all project configurations"
  value = {
    project = {
      id     = google_project.project.project_id
      number = google_project.project.number
      name   = google_project.project.name
    }
    organization = {
      id     = var.org_id
      folder = var.folder_id
    }
    billing = {
      account = var.billing_account
      budget  = var.budget_amount
    }
    location = {
      region = var.default_region
      zone   = local.default_zone
    }
    security = {
      security_center_enabled = var.enable_security_center
      vpc_service_controls    = var.vpc_service_controls != null
      audit_logging_enabled   = length(var.audit_log_config.data_access) > 0
    }
    monitoring = {
      workspace_enabled = var.enable_monitoring_workspace
      alerts_enabled    = var.enable_monitoring_alerts
      logging_sinks     = length(var.logging_sinks)
    }
    apis_enabled   = length(local.activate_apis)
    labels_applied = local.merged_labels
    created_at     = timestamp()
  }
}
