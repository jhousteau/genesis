/**
 * Project Bootstrap Module - Simplified and Essential
 *
 * Creates a GCP project with basic APIs enabled and optional service account.
 * Follows Genesis principle: Do what's needed, skip the complexity.
 */

locals {
  project_name = var.project_name != "" ? var.project_name : var.project_id

  # Essential APIs - only what's actually used
  essential_apis = [
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
  ]

  all_apis = distinct(concat(local.essential_apis, var.additional_apis))

  default_labels = {
    environment = var.environment
    managed_by  = "terraform"
    created_by  = "genesis"
  }

  labels = merge(local.default_labels, var.labels)
}

# Create the GCP Project
resource "google_project" "project" {
  project_id          = var.project_id
  name                = local.project_name
  org_id              = var.organization_id != "" ? var.organization_id : null
  folder_id           = var.folder_id != "" ? var.folder_id : null
  billing_account     = var.billing_account
  auto_create_network = var.auto_create_network
  labels              = local.labels
}

# Enable APIs
resource "google_project_service" "apis" {
  for_each = toset(local.all_apis)

  project                    = google_project.project.project_id
  service                    = each.value
  disable_on_destroy         = false # Keep APIs enabled to avoid issues
  disable_dependent_services = false

  depends_on = [google_project.project]
}

# Optional: Create a default service account
resource "google_service_account" "default" {
  count = var.create_default_service_account ? 1 : 0

  project      = google_project.project.project_id
  account_id   = var.default_service_account_name
  display_name = "Default Project Service Account"
  description  = "Default service account created during project bootstrap"

  depends_on = [google_project_service.apis]
}

# Grant roles to the default service account
resource "google_project_iam_member" "default_sa_roles" {
  for_each = var.create_default_service_account ? toset(var.default_service_account_roles) : []

  project = google_project.project.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.default[0].email}"

  depends_on = [google_service_account.default]
}

# Optional: Set up a basic budget alert
resource "google_billing_budget" "budget" {
  count = var.budget_amount > 0 ? 1 : 0

  billing_account = var.billing_account
  display_name    = "${local.project_name} Budget"

  budget_filter {
    projects = ["projects/${google_project.project.number}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_amount)
    }
  }

  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  depends_on = [google_project_service.apis]
}
