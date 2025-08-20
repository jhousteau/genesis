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
    "cloudbilling.googleapis.com"
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
    projects = ["projects/${google_project.project.number}"]
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
    schema_version = "1.0"
    
    dynamic "monitoring_notification_channels" {
      for_each = var.monitoring_notification_channels
      content {
        monitoring_notification_channels = monitoring_notification_channels.value
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

  parent                          = "projects/${google_project.project.project_id}"
  email                          = each.value.email
  language_tag                   = "en"
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
  force_destroy              = false

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
    region         = var.default_region
    zone           = local.default_zone
    labels         = local.merged_labels
    enabled_apis   = local.activate_apis
    created_at     = timestamp()
  })

  depends_on = [
    google_storage_bucket.bootstrap_state
  ]
}