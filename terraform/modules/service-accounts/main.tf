/**
 * Service Accounts Module - Simplified and Essential
 *
 * Creates service accounts with IAM roles. No over-engineering.
 * Follows Genesis principle: Simple, focused functionality.
 */

locals {
  # Flatten service accounts with their project roles for easier iteration
  project_role_bindings = flatten([
    for sa_name, sa_config in var.service_accounts : [
      for role in sa_config.project_roles : {
        sa_name    = sa_name
        sa_email   = google_service_account.service_accounts[sa_name].email
        role       = role
        project_id = coalesce(sa_config.project_id, var.project_id)
      }
    ]
  ])
}

# Create service accounts
resource "google_service_account" "service_accounts" {
  for_each = var.service_accounts

  project      = coalesce(each.value.project_id, var.project_id)
  account_id   = each.value.account_id
  display_name = each.value.display_name
  description  = each.value.description
  disabled     = each.value.disabled
}

# Assign project-level IAM roles
resource "google_project_iam_member" "project_roles" {
  for_each = {
    for binding in local.project_role_bindings :
    "${binding.sa_name}-${binding.project_id}-${binding.role}" => binding
  }

  project = each.value.project_id
  role    = each.value.role
  member  = "serviceAccount:${each.value.sa_email}"

  depends_on = [google_service_account.service_accounts]
}

# Optional: Create service account keys (not recommended for production)
resource "google_service_account_key" "keys" {
  for_each = {
    for sa_name, sa_config in var.service_accounts :
    sa_name => sa_config
    if sa_config.create_key
  }

  service_account_id = google_service_account.service_accounts[each.key].name

  # Store keys securely in outputs - consider using secret management instead
  depends_on = [google_service_account.service_accounts]
}

# Optional: Set up impersonation relationships
resource "google_service_account_iam_member" "impersonation" {
  for_each = {
    for sa_name, sa_config in var.service_accounts :
    sa_name => sa_config
    if length(sa_config.impersonators) > 0
  }

  service_account_id = google_service_account.service_accounts[each.key].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = each.value.impersonators[0] # Simplified: only first impersonator

  depends_on = [google_service_account.service_accounts]
}
