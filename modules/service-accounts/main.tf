/**
 * Service Accounts Module
 * 
 * This module creates and manages GCP service accounts with customizable IAM roles.
 * It supports creating multiple service accounts with different permission sets
 * and follows the principle of least privilege.
 */

locals {
  # Flatten service accounts with their roles for easier iteration
  sa_project_roles = flatten([
    for sa_key, sa in var.service_accounts : [
      for role in sa.project_roles : {
        sa_key     = sa_key
        sa_email   = google_service_account.service_accounts[sa_key].email
        role       = role
        project_id = coalesce(sa.project_id, var.project_id)
      }
    ]
  ])

  # Flatten service accounts with their organization roles
  sa_org_roles = flatten([
    for sa_key, sa in var.service_accounts : [
      for role in sa.organization_roles : {
        sa_key   = sa_key
        sa_email = google_service_account.service_accounts[sa_key].email
        role     = role
      }
    ] if sa.organization_roles != null
  ])

  # Flatten service accounts with their folder roles
  sa_folder_roles = flatten([
    for sa_key, sa in var.service_accounts : [
      for folder_id, roles in sa.folder_roles : [
        for role in roles : {
          sa_key    = sa_key
          sa_email  = google_service_account.service_accounts[sa_key].email
          folder_id = folder_id
          role      = role
        }
      ]
    ] if sa.folder_roles != null
  ])

  # Build impersonation relationships
  impersonation_pairs = flatten([
    for sa_key, sa in var.service_accounts : [
      for impersonator in sa.impersonators : {
        sa_key       = sa_key
        sa_email     = google_service_account.service_accounts[sa_key].email
        impersonator = impersonator
      }
    ] if sa.impersonators != null
  ])

  # Service account key configurations
  sa_keys = {
    for sa_key, sa in var.service_accounts :
    sa_key => sa
    if sa.create_key == true
  }
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
    for idx, binding in local.sa_project_roles :
    "${binding.sa_key}-${binding.project_id}-${binding.role}" => binding
  }

  project = each.value.project_id
  role    = each.value.role
  member  = "serviceAccount:${each.value.sa_email}"

  depends_on = [google_service_account.service_accounts]
}

# Assign organization-level IAM roles (if applicable)
resource "google_organization_iam_member" "org_roles" {
  for_each = {
    for idx, binding in local.sa_org_roles :
    "${binding.sa_key}-org-${binding.role}" => binding
    if var.organization_id != null
  }

  org_id = var.organization_id
  role   = each.value.role
  member = "serviceAccount:${each.value.sa_email}"

  depends_on = [google_service_account.service_accounts]
}

# Assign folder-level IAM roles (if applicable)
resource "google_folder_iam_member" "folder_roles" {
  for_each = {
    for idx, binding in local.sa_folder_roles :
    "${binding.sa_key}-${binding.folder_id}-${binding.role}" => binding
  }

  folder = each.value.folder_id
  role   = each.value.role
  member = "serviceAccount:${each.value.sa_email}"

  depends_on = [google_service_account.service_accounts]
}

# Configure service account impersonation
resource "google_service_account_iam_member" "impersonation" {
  for_each = {
    for idx, pair in local.impersonation_pairs :
    "${pair.sa_key}-impersonation-${pair.impersonator}" => pair
  }

  service_account_id = google_service_account.service_accounts[each.value.sa_key].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = each.value.impersonator

  depends_on = [google_service_account.service_accounts]
}

# Create service account keys (only when explicitly requested)
resource "google_service_account_key" "keys" {
  for_each = local.sa_keys

  service_account_id = google_service_account.service_accounts[each.key].name
  key_algorithm      = "KEY_ALG_RSA_2048"
  private_key_type   = "TYPE_GOOGLE_CREDENTIALS_FILE"

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [google_service_account.service_accounts]
}

# Store service account keys in Secret Manager (optional)
resource "google_secret_manager_secret" "sa_keys" {
  for_each = {
    for sa_key, sa in local.sa_keys :
    sa_key => sa
    if var.store_keys_in_secret_manager
  }

  project   = coalesce(each.value.project_id, var.project_id)
  secret_id = "${each.value.account_id}-key"

  replication {
    auto {}
  }

  labels = merge(
    var.labels,
    {
      service_account = each.value.account_id
      managed_by      = "terraform"
    }
  )

  depends_on = [google_service_account_key.keys]
}

# Store the actual key data in Secret Manager
resource "google_secret_manager_secret_version" "sa_key_versions" {
  for_each = {
    for sa_key, sa in local.sa_keys :
    sa_key => sa
    if var.store_keys_in_secret_manager
  }

  secret      = google_secret_manager_secret.sa_keys[each.key].id
  secret_data = base64decode(google_service_account_key.keys[each.key].private_key)

  depends_on = [
    google_secret_manager_secret.sa_keys,
    google_service_account_key.keys
  ]
}

# Grant access to read the secrets (for authorized users/SAs)
resource "google_secret_manager_secret_iam_member" "secret_accessors" {
  for_each = {
    for sa_key, sa in local.sa_keys :
    sa_key => sa
    if var.store_keys_in_secret_manager && length(sa.key_secret_accessors) > 0
  }

  project   = coalesce(each.value.project_id, var.project_id)
  secret_id = google_secret_manager_secret.sa_keys[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = each.value.key_secret_accessors[0] # This would need to be expanded for multiple accessors

  depends_on = [google_secret_manager_secret.sa_keys]
}