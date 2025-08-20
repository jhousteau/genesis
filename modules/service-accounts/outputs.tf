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