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

locals {
  # Project ID construction
  project_id_suffix = var.random_project_id ? "-${random_id.project_suffix[0].hex}" : ""
  project_id        = "${var.project_prefix}${local.project_id_suffix}"
  project_name      = var.project_name != "" ? var.project_name : local.project_id

  # Parent configuration
  parent_type = var.folder_id != "" ? "folder" : "organization"
  parent_id   = var.folder_id != "" ? var.folder_id : var.org_id

  # Default labels
  default_labels = {
    environment = "bootstrap"
    managed_by  = "terraform"
    created_on  = formatdate("YYYY-MM-DD", timestamp())
  }

  merged_labels = merge(local.default_labels, var.labels)

  # API list processing
  activate_apis = distinct(concat(var.activate_apis, [
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbilling.googleapis.com",
    # Additional APIs for enhanced features
    "cloudscheduler.googleapis.com",
    "cloudfunctions.googleapis.com",
    "binaryauthorization.googleapis.com",
    "containeranalysis.googleapis.com",
    "cloudtasks.googleapis.com",
    "datacatalog.googleapis.com",
    "dlp.googleapis.com",
    "websecurityscanner.googleapis.com"
  ]))

  # Zone configuration
  default_zone = var.default_zone != "" ? var.default_zone : "${var.default_region}-a"

  # Service account email
  service_account_email = var.create_default_service_account ? google_service_account.default[0].email : ""
}

# Random suffix for project ID
resource "random_id" "project_suffix" {
  count       = var.random_project_id ? 1 : 0
  byte_length = var.random_project_id_length
}

# Create the GCP Project
resource "google_project" "project" {
  project_id          = local.project_id
  name                = local.project_name
  org_id              = local.parent_type == "organization" ? var.org_id : null
  folder_id           = local.parent_type == "folder" ? var.folder_id : null
  billing_account     = var.billing_account
  auto_create_network = var.auto_create_network
  labels              = local.merged_labels

  lifecycle {
    ignore_changes = [
      labels["created_on"]
    ]
  }
}

# Enable APIs
resource "google_project_service" "apis" {
  for_each = toset(local.activate_apis)

  project                    = google_project.project.project_id
  service                    = each.value
  disable_on_destroy         = var.disable_services_on_destroy
  disable_dependent_services = var.disable_dependent_services

  timeouts {
    create = "30m"
    update = "40m"
  }

  depends_on = [
    google_project.project
  ]
}

# Enable API service identities if specified
resource "google_project_service_identity" "api_identities" {
  for_each = { for item in var.activate_api_identities : item.api => item }

  provider = google-beta
  project  = google_project.project.project_id
  service  = each.value.api

  depends_on = [
    google_project_service.apis
  ]
}

# Grant roles to API service identities
resource "google_project_iam_member" "api_identity_roles" {
  for_each = {
    for item in flatten([
      for api_config in var.activate_api_identities : [
        for role in api_config.roles : {
          key  = "${api_config.api}-${role}"
          api  = api_config.api
          role = role
        }
      ]
    ]) : item.key => item
  }

  project = google_project.project.project_id
  role    = each.value.role
  member  = "serviceAccount:${google_project_service_identity.api_identities[each.value.api].email}"

  depends_on = [
    google_project_service_identity.api_identities
  ]
}

# Create default service account
resource "google_service_account" "default" {
  count = var.create_default_service_account ? 1 : 0

  account_id   = var.default_service_account_name
  display_name = "Bootstrap Default Service Account"
  description  = "Default service account created by bootstrap module"
  project      = google_project.project.project_id

  depends_on = [
    google_project_service.apis["iam.googleapis.com"]
  ]
}

# Grant roles to default service account
resource "google_project_iam_member" "default_service_account" {
  for_each = var.create_default_service_account ? toset(var.default_service_account_roles) : []

  project = google_project.project.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.default[0].email}"

  depends_on = [
    google_service_account.default
  ]
}

# Create service account key
resource "google_service_account_key" "default" {
  count = var.create_default_service_account ? 1 : 0

  service_account_id = google_service_account.default[0].name

  depends_on = [
    google_service_account.default
  ]
}

# Configure budget alerts
resource "google_billing_budget" "budget" {
  count = var.budget_amount != null ? 1 : 0

  billing_account = var.billing_account
  display_name    = "${local.project_name}-budget"

  budget_filter {
    projects               = ["projects/${google_project.project.number}"]
    services               = var.budget_filters.services
    subaccounts            = var.budget_filters.subaccounts
    regions                = var.budget_filters.regions
    credit_types_treatment = var.budget_filters.credit_types_treatment

    dynamic "labels" {
      for_each = var.budget_filters.labels
      content {
        key    = labels.key
        values = labels.value
      }
    }
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(floor(var.budget_amount))
      nanos         = tostring((var.budget_amount - floor(var.budget_amount)) * 1000000000)
    }
  }

  dynamic "threshold_rules" {
    for_each = var.budget_alert_percentages
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }

  all_updates_rule {
    schema_version                   = "1.0"
    pubsub_topic                     = length(var.budget_notification_channels) > 0 ? null : null
    monitoring_notification_channels = var.budget_notification_channels
  }

  # Calendar period configuration
  dynamic "budget_filter" {
    for_each = var.budget_calendar_period == "CUSTOM" && var.budget_custom_period != null ? [1] : []
    content {
      calendar_period = var.budget_calendar_period
      custom_period {
        start_date {
          year  = var.budget_custom_period.start_date.year
          month = var.budget_custom_period.start_date.month
          day   = var.budget_custom_period.start_date.day
        }
        dynamic "end_date" {
          for_each = var.budget_custom_period.end_date != null ? [1] : []
          content {
            year  = var.budget_custom_period.end_date.year
            month = var.budget_custom_period.end_date.month
            day   = var.budget_custom_period.end_date.day
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis["cloudbilling.googleapis.com"]
  ]
}

# Organization policies
resource "google_project_organization_policy" "org_policies" {
  for_each = var.org_policies

  project    = google_project.project.project_id
  constraint = each.key

  dynamic "boolean_policy" {
    for_each = each.value.enforce != null ? [1] : []
    content {
      enforced = each.value.enforce
    }
  }

  dynamic "list_policy" {
    for_each = (length(each.value.allow) > 0 || length(each.value.deny) > 0) ? [1] : []
    content {
      dynamic "allow" {
        for_each = length(each.value.allow) > 0 ? [1] : []
        content {
          values = each.value.allow
          all    = contains(each.value.allow, "all") ? true : false
        }
      }

      dynamic "deny" {
        for_each = length(each.value.deny) > 0 ? [1] : []
        content {
          values = each.value.deny
          all    = contains(each.value.deny, "all") ? true : false
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis["cloudresourcemanager.googleapis.com"]
  ]
}

# Essential Contacts
resource "google_essential_contacts_contact" "contacts" {
  for_each = var.essential_contacts

  parent                              = "projects/${google_project.project.project_id}"
  email                               = each.value.email
  language_tag                        = "en"
  notification_category_subscriptions = each.value.notification_categories

  depends_on = [
    google_project_service.apis["essentialcontacts.googleapis.com"]
  ]
}

# Grant service agents additional roles if specified
resource "google_project_iam_member" "service_agent_security" {
  count = var.grant_services_security_admin_role ? 1 : 0

  project = google_project.project.project_id
  role    = "roles/securitycenter.admin"
  member  = "serviceAccount:service-${google_project.project.number}@compute-system.iam.gserviceaccount.com"

  depends_on = [
    google_project_service.apis["compute.googleapis.com"]
  ]
}

resource "google_project_iam_member" "service_agent_network" {
  count = var.grant_services_network_role ? 1 : 0

  project = google_project.project.project_id
  role    = "roles/compute.networkAdmin"
  member  = "serviceAccount:service-${google_project.project.number}@compute-system.iam.gserviceaccount.com"

  depends_on = [
    google_project_service.apis["compute.googleapis.com"]
  ]
}

# Audit Log Configuration
resource "google_project_iam_audit_config" "audit" {
  for_each = length(var.audit_log_config.data_access) > 0 ? { "allServices" = true } : {}

  project = google_project.project.project_id
  service = "allServices"

  dynamic "audit_log_config" {
    for_each = var.audit_log_config.data_access
    content {
      log_type         = audit_log_config.value.log_type
      exempted_members = audit_log_config.value.exempted_members
    }
  }

  depends_on = [
    google_project_service.apis["cloudresourcemanager.googleapis.com"]
  ]
}

# Store project metadata in GCS bucket (optional, for bootstrapping state)
resource "google_storage_bucket" "bootstrap_state" {
  count = var.create_default_service_account ? 1 : 0

  name     = "${local.project_id}-bootstrap-state"
  project  = google_project.project.project_id
  location = var.default_region

  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 10
    }
    action {
      type = "Delete"
    }
  }

  labels = local.merged_labels

  depends_on = [
    google_project_service.apis["storage.googleapis.com"]
  ]
}

# Store bootstrap configuration
resource "google_storage_bucket_object" "bootstrap_config" {
  count = var.create_default_service_account ? 1 : 0

  name   = "bootstrap-config.json"
  bucket = google_storage_bucket.bootstrap_state[0].name

  content = jsonencode({
    project_id      = google_project.project.project_id
    project_number  = google_project.project.number
    organization_id = var.org_id
    billing_account = var.billing_account
    region          = var.default_region
    zone            = local.default_zone
    labels          = local.merged_labels
    enabled_apis    = local.activate_apis
    created_at      = timestamp()
  })

  depends_on = [
    google_storage_bucket.bootstrap_state
  ]
}

# Cloud Asset Inventory Feeds
resource "google_cloud_asset_project_feed" "feeds" {
  for_each = {
    for feed in var.asset_inventory_feeds : feed.name => feed
  }

  project      = google_project.project.project_id
  feed_id      = each.value.name
  content_type = each.value.content_type
  asset_types  = each.value.asset_types
  asset_names  = each.value.asset_names

  feed_output_config {
    pubsub_destination {
      topic = each.value.feed_output_config.pubsub_destination.topic
    }
  }

  dynamic "condition" {
    for_each = each.value.condition != null ? [each.value.condition] : []
    content {
      expression  = condition.value.expression
      title       = condition.value.title
      description = condition.value.description
    }
  }

  depends_on = [
    google_project_service.apis["cloudasset.googleapis.com"]
  ]
}

# Resource Manager Tags
resource "google_tags_tag_key" "keys" {
  for_each = var.resource_manager_tags

  parent      = each.value.parent
  short_name  = each.value.short_name
  description = each.value.description

  depends_on = [
    google_project_service.apis["cloudresourcemanager.googleapis.com"]
  ]
}

resource "google_tags_tag_value" "values" {
  for_each = {
    for tag_key, tag_config in var.resource_manager_tags :
    tag_key => tag_config
    if length(tag_config.values) > 0
  }

  dynamic "for_each" {
    for_each = each.value.values
    content {
      parent      = google_tags_tag_key.keys[each.key].id
      short_name  = for_each.value.short_name
      description = for_each.value.description
    }
  }

  depends_on = [
    google_tags_tag_key.keys
  ]
}

# Security Command Center
resource "google_scc_project_custom_module" "security_modules" {
  for_each = {
    for source in var.security_center_sources : source.display_name => source
    if var.enable_security_center
  }

  project      = google_project.project.project_id
  display_name = each.value.display_name
  description  = each.value.description

  enablement_state = "ENABLED"

  custom_config {
    predicate {
      expression = "true" # Default predicate, customize as needed
    }
    custom_output {
      properties {
        name = "security_finding"
        value_expression {
          expression = "resource.name"
        }
      }
    }
    description    = each.value.description
    recommendation = "Review and remediate the security finding"
    severity       = "MEDIUM"
  }

  depends_on = [
    google_project_service.apis["securitycenter.googleapis.com"]
  ]
}

# Cloud Monitoring Workspace
resource "google_monitoring_monitored_project" "primary" {
  count = var.enable_monitoring_workspace ? 1 : 0

  metrics_scope = google_project.project.project_id
  name          = google_project.project.project_id

  depends_on = [
    google_project_service.apis["monitoring.googleapis.com"]
  ]
}

# Logging Sinks
resource "google_logging_project_sink" "sinks" {
  for_each = {
    for sink in var.logging_sinks : sink.name => sink
  }

  name                   = each.value.name
  project                = google_project.project.project_id
  destination            = each.value.destination
  filter                 = each.value.filter
  description            = each.value.description
  disabled               = each.value.disabled
  unique_writer_identity = each.value.unique_writer_identity

  dynamic "bigquery_options" {
    for_each = each.value.bigquery_options != null ? [each.value.bigquery_options] : []
    content {
      use_partitioned_tables = bigquery_options.value.use_partitioned_tables
    }
  }

  dynamic "exclusions" {
    for_each = each.value.exclusions
    content {
      name        = exclusions.value.name
      description = exclusions.value.description
      filter      = exclusions.value.filter
      disabled    = exclusions.value.disabled
    }
  }

  depends_on = [
    google_project_service.apis["logging.googleapis.com"]
  ]
}

# Service Usage Quota Overrides
resource "google_service_usage_consumer_quota_override" "quota_overrides" {
  for_each = {
    for override in var.quota_overrides : "${override.service}-${override.metric}" => override
  }

  project        = google_project.project.project_id
  service        = each.value.service
  metric         = each.value.metric
  limit          = each.value.limit
  override_value = each.value.value
  dimensions     = each.value.dimensions
  force          = true

  depends_on = [
    google_project_service.apis["serviceusage.googleapis.com"]
  ]
}

# VPC Service Controls Perimeter (if configured)
resource "google_access_context_manager_service_perimeter" "perimeter" {
  count = var.vpc_service_controls != null ? 1 : 0

  parent = "accessPolicies/${var.access_context_manager_policy.parent}"
  name   = "accessPolicies/${var.access_context_manager_policy.parent}/servicePerimeters/${var.vpc_service_controls.perimeter_name}"
  title  = var.vpc_service_controls.perimeter_name

  status {
    resources           = concat(var.vpc_service_controls.resources, ["projects/${google_project.project.number}"])
    restricted_services = var.vpc_service_controls.restricted_services
    access_levels       = var.vpc_service_controls.access_levels

    dynamic "vpc_accessible_services" {
      for_each = var.vpc_service_controls.vpc_accessible_services != null ? [var.vpc_service_controls.vpc_accessible_services] : []
      content {
        enable_restriction = vpc_accessible_services.value.enable_restriction
        allowed_services   = vpc_accessible_services.value.allowed_services
      }
    }
  }

  depends_on = [
    google_project_service.apis["accesscontextmanager.googleapis.com"]
  ]
}

# Enhanced monitoring alerts
resource "google_monitoring_alert_policy" "budget_alerts" {
  count = var.budget_amount != null && var.enable_monitoring_alerts ? 1 : 0

  project      = google_project.project.project_id
  display_name = "${local.project_name} Budget Alert Policy"

  documentation {
    content = "Alert when project budget exceeds thresholds"
  }

  conditions {
    display_name = "Budget threshold exceeded"

    condition_threshold {
      filter          = "resource.type=\"billing_account\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = var.budget_amount * 0.8

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.monitoring_notification_channels

  alert_strategy {
    auto_close = "1800s"
  }

  depends_on = [
    google_project_service.apis["monitoring.googleapis.com"]
  ]
}

# Project-level IAM audit configuration for compliance
resource "google_project_iam_audit_config" "compliance_audit" {
  count = length(var.audit_log_config.data_access) > 0 ? 1 : 0

  project = google_project.project.project_id
  service = "allServices"

  dynamic "audit_log_config" {
    for_each = var.audit_log_config.data_access
    content {
      log_type         = audit_log_config.value.log_type
      exempted_members = audit_log_config.value.exempted_members
    }
  }

  depends_on = [
    google_project_service.apis["cloudresourcemanager.googleapis.com"]
  ]
}

# Multi-Region Storage for Critical Bootstrap Data
resource "google_storage_bucket" "bootstrap_state_replica" {
  for_each = {
    for region in var.multi_region_config.secondary_regions : region => region
    if var.multi_region_config.enabled && var.create_default_service_account
  }

  name     = "${local.project_id}-bootstrap-state-${each.value}"
  project  = google_project.project.project_id
  location = each.value

  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 10
    }
    action {
      type = "Delete"
    }
  }

  labels = merge(local.merged_labels, {
    purpose        = "bootstrap-replica"
    primary_region = var.multi_region_config.primary_region
  })

  depends_on = [
    google_project_service.apis["storage.googleapis.com"]
  ]
}

# CMEK Key Ring for Enhanced Security
resource "google_kms_key_ring" "bootstrap_keyring" {
  count = var.enhanced_security.cmek_config.enabled ? 1 : 0

  name     = "${local.project_id}-bootstrap-keyring"
  project  = google_project.project.project_id
  location = var.enhanced_security.cmek_config.key_ring_location

  depends_on = [
    google_project_service.apis["cloudkms.googleapis.com"]
  ]
}

# CMEK Keys for Different Services
resource "google_kms_crypto_key" "bootstrap_keys" {
  for_each = {
    for service in var.enhanced_security.cmek_config.services : service => service
    if var.enhanced_security.cmek_config.enabled
  }

  name     = "${local.project_id}-${replace(each.value, ".", "-")}-key"
  key_ring = google_kms_key_ring.bootstrap_keyring[0].id
  purpose  = "ENCRYPT_DECRYPT"

  rotation_period = var.enhanced_security.cmek_config.key_rotation_period

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [
    google_kms_key_ring.bootstrap_keyring
  ]
}

# Custom IAM Roles for Enhanced Security
resource "google_project_iam_custom_role" "custom_roles" {
  for_each = {
    for role in var.advanced_iam.custom_roles : role.role_id => role
    if var.advanced_iam.enable_iam_conditions
  }

  project     = google_project.project.project_id
  role_id     = each.value.role_id
  title       = each.value.title
  description = each.value.description
  permissions = each.value.permissions
  stage       = each.value.stage

  depends_on = [
    google_project_service.apis["iam.googleapis.com"]
  ]
}

# Conditional IAM Bindings
resource "google_project_iam_binding" "conditional_bindings" {
  for_each = {
    for idx, binding in var.advanced_iam.conditional_bindings : "${binding.role}-${idx}" => binding
    if var.advanced_iam.enable_iam_conditions
  }

  project = google_project.project.project_id
  role    = each.value.role
  members = each.value.members

  condition {
    title       = each.value.condition.title
    description = each.value.condition.description
    expression  = each.value.condition.expression
  }

  depends_on = [
    google_project_service.apis["iam.googleapis.com"]
  ]
}

# Cost Anomaly Detection
resource "google_billing_budget" "cost_anomaly_budget" {
  count = var.cost_optimization.cost_anomaly_detection.enabled && var.budget_amount != null ? 1 : 0

  billing_account = var.billing_account
  display_name    = "${local.project_name}-cost-anomaly-budget"

  budget_filter {
    projects = ["projects/${google_project.project.number}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(floor(var.budget_amount * (1 + var.cost_optimization.cost_anomaly_detection.threshold_percentage / 100)))
    }
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = var.cost_optimization.cost_anomaly_detection.notification_channels
    schema_version                   = "1.0"
  }

  depends_on = [
    google_project_service.apis["cloudbilling.googleapis.com"]
  ]
}

# Security Policy for Cloud Armor
resource "google_compute_security_policy" "security_policies" {
  for_each = {
    for policy in var.enhanced_security.security_policies : policy.name => policy
    if var.network_security.enable_cloud_armor
  }

  project     = google_project.project.project_id
  name        = "${var.project_prefix}-${each.value.name}"
  description = each.value.description

  dynamic "rule" {
    for_each = each.value.rules
    content {
      action   = rule.value.action
      priority = rule.value.priority

      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = rule.value.match.src_ip_ranges
        }
      }

      description = "Security rule ${rule.value.priority}"
    }
  }

  depends_on = [
    google_project_service.apis["compute.googleapis.com"]
  ]
}

# Binary Authorization Policy
resource "google_binary_authorization_policy" "policy" {
  count = var.enhanced_security.enable_binary_authorization ? 1 : 0

  project = google_project.project.project_id

  default_admission_rule {
    evaluation_mode  = "REQUIRE_ATTESTATION"
    enforcement_mode = "ENFORCED_BLOCK_AND_AUDIT_LOG"

    require_attestations_by = [
      # Add attestor references here when attestors are created
    ]
  }

  depends_on = [
    google_project_service.apis["binaryauthorization.googleapis.com"]
  ]
}

# Vulnerability Scanning Configuration
resource "google_container_analysis_note" "vulnerability_note" {
  count = var.enhanced_security.vulnerability_scanning.enabled ? 1 : 0

  project = google_project.project.project_id
  name    = "${local.project_id}-vulnerability-note"

  vulnerability_type {
    cvss_score {
      base_score = 5.0
    }
  }

  depends_on = [
    google_project_service.apis["containeranalysis.googleapis.com"]
  ]
}

# Advanced Monitoring - Custom Metrics
resource "google_monitoring_metric_descriptor" "custom_metrics" {
  for_each = {
    for metric in var.advanced_monitoring.custom_metrics : metric.name => metric
    if var.advanced_monitoring.enabled
  }

  project      = google_project.project.project_id
  type         = "custom.googleapis.com/${each.value.name}"
  metric_kind  = each.value.metric_kind
  value_type   = each.value.value_type
  description  = each.value.description
  display_name = each.value.name

  dynamic "labels" {
    for_each = each.value.labels
    content {
      key         = labels.key
      value_type  = "STRING"
      description = "Label for ${labels.key}"
    }
  }

  depends_on = [
    google_project_service.apis["monitoring.googleapis.com"]
  ]
}

# Log-based Metrics
resource "google_logging_metric" "log_based_metrics" {
  for_each = {
    for metric in var.advanced_monitoring.log_based_metrics : metric.name => metric
    if var.advanced_monitoring.enabled
  }

  project     = google_project.project.project_id
  name        = each.value.name
  filter      = each.value.filter
  description = each.value.description

  metric_descriptor {
    metric_kind  = each.value.metric_descriptor.metric_kind
    value_type   = each.value.metric_descriptor.value_type
    display_name = each.value.name
  }

  depends_on = [
    google_project_service.apis["logging.googleapis.com"]
  ]
}

# Advanced Alerting Policies
resource "google_monitoring_alert_policy" "advanced_alerts" {
  for_each = {
    for policy in var.advanced_monitoring.alerting_policies : policy.name => policy
    if var.advanced_monitoring.enabled
  }

  project      = google_project.project.project_id
  display_name = each.value.name
  description  = each.value.description
  combiner     = "OR"

  dynamic "conditions" {
    for_each = each.value.conditions
    content {
      display_name = conditions.value.display_name

      condition_threshold {
        filter          = conditions.value.filter
        duration        = conditions.value.duration
        comparison      = conditions.value.comparison
        threshold_value = conditions.value.threshold_value

        aggregations {
          alignment_period   = "300s"
          per_series_aligner = "ALIGN_RATE"
        }
      }
    }
  }

  notification_channels = each.value.notification_channels

  alert_strategy {
    auto_close = "1800s"
  }

  depends_on = [
    google_project_service.apis["monitoring.googleapis.com"]
  ]
}

# Disaster Recovery - Automated Backup Jobs
resource "google_cloud_scheduler_job" "backup_jobs" {
  for_each = {
    for region in var.multi_region_config.secondary_regions : region => region
    if var.disaster_recovery.enabled && var.multi_region_config.enabled
  }

  project     = google_project.project.project_id
  region      = each.value
  name        = "${local.project_id}-backup-job-${each.value}"
  description = "Automated backup job for ${each.value}"
  schedule    = var.disaster_recovery.backup_schedule
  time_zone   = "UTC"

  http_target {
    uri         = "https://cloudfunctions.googleapis.com/v1/projects/${google_project.project.project_id}/locations/${each.value}/functions/backup-function:call"
    http_method = "POST"
    body = base64encode(jsonencode({
      source_region = var.multi_region_config.primary_region
      target_region = each.value
      retention     = var.disaster_recovery.retention_policy
    }))

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = var.create_default_service_account ? google_service_account.default[0].email : ""
    }
  }

  depends_on = [
    google_project_service.apis["cloudscheduler.googleapis.com"],
    google_service_account.default
  ]
}

# Compliance Automation - Policy Enforcement
resource "google_project_organization_policy" "compliance_policies" {
  for_each = {
    "constraints/compute.requireShieldedVm" = {
      enforce = var.enhanced_security.enable_shielded_vms
    }
    "constraints/compute.requireOsLogin" = {
      enforce = var.enhanced_security.enable_os_login
    }
    "constraints/gcp.resourceLocations" = {
      allow = var.compliance_automation.policy_enforcement.allowed_locations
    }
  }

  project    = google_project.project.project_id
  constraint = each.key

  dynamic "boolean_policy" {
    for_each = contains(keys(each.value), "enforce") ? [1] : []
    content {
      enforced = each.value.enforce
    }
  }

  dynamic "list_policy" {
    for_each = contains(keys(each.value), "allow") ? [1] : []
    content {
      allow {
        values = each.value.allow
      }
    }
  }

  depends_on = [
    google_project_service.apis["cloudresourcemanager.googleapis.com"]
  ]
}
