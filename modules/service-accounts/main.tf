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
# Enhanced Locals for Advanced Features
locals {
  # Workload Identity Pool and Provider pairs
  wif_pools = {
    for pool in var.workload_identity_config.identity_pools : pool.pool_id => pool
    if var.workload_identity_config.enabled
  }

  wif_providers = flatten([
    for pool in var.workload_identity_config.identity_pools : [
      for provider in pool.providers : {
        pool_id = pool.pool_id
        provider_id = provider.provider_id
        provider = provider
      }
    ]
    if var.workload_identity_config.enabled
  ])

  # Custom roles for advanced IAM
  custom_roles = {
    for role in var.advanced_iam_config.custom_roles : role.role_id => role
    if var.advanced_iam_config.enable_custom_roles
  }

  # Cross-project IAM bindings
  cross_project_bindings = flatten([
    for sa_key, sa in var.service_accounts : [
      for project in var.cross_project_access.target_projects : [
        for role in project.roles : {
          sa_key = sa_key
          sa_email = google_service_account.service_accounts[sa_key].email
          project_id = project.project_id
          role = role
          conditions = project.conditions
        }
      ]
    ]
    if var.cross_project_access.enabled
  ])

  # CI/CD platform bindings
  cicd_bindings = flatten([
    # GitHub Actions
    for repo in var.cicd_platforms.github_actions.repositories : {
      platform = "github"
      key = "${repo.owner}/${repo.repo}"
      sa_key = repo.service_account_key
      provider_id = "github-${repo.owner}-${repo.repo}"
      attribute_mapping = {
        "google.subject" = "assertion.sub"
        "attribute.actor" = "assertion.actor"
        "attribute.repository" = "assertion.repository"
        "attribute.ref" = "assertion.ref"
      }
      attribute_condition = "assertion.repository == '${repo.owner}/${repo.repo}' && assertion.ref == 'refs/heads/${repo.ref}'"
      oidc_config = {
        issuer_uri = "https://token.actions.githubusercontent.com"
        allowed_audiences = ["https://github.com/${repo.owner}"]
      }
    }
    if var.cicd_platforms.github_actions.enabled
  ])
}

# Workload Identity Pools
resource "google_iam_workload_identity_pool" "pools" {
  for_each = local.wif_pools

  project                   = var.project_id
  workload_identity_pool_id = each.value.pool_id
  display_name              = each.value.display_name
  description               = each.value.description
  disabled                  = each.value.disabled
}

# Workload Identity Providers
resource "google_iam_workload_identity_pool_provider" "providers" {
  for_each = {
    for item in local.wif_providers : "${item.pool_id}-${item.provider_id}" => item
  }

  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.pools[each.value.pool_id].workload_identity_pool_id
  workload_identity_pool_provider_id = each.value.provider_id
  display_name                       = each.value.provider.display_name
  description                        = each.value.provider.description
  disabled                           = each.value.provider.disabled
  attribute_mapping                  = each.value.provider.attribute_mapping
  attribute_condition                = each.value.provider.attribute_condition

  # OIDC Configuration
  dynamic "oidc" {
    for_each = each.value.provider.oidc_config != null ? [each.value.provider.oidc_config] : []
    content {
      issuer_uri        = oidc.value.issuer_uri
      allowed_audiences = oidc.value.allowed_audiences
      jwks_json         = oidc.value.jwks_json
    }
  }

  # AWS Configuration
  dynamic "aws" {
    for_each = each.value.provider.aws_config != null ? [each.value.provider.aws_config] : []
    content {
      account_id = aws.value.account_id
      sts_uri    = aws.value.sts_uri
    }
  }

  # SAML Configuration
  dynamic "saml" {
    for_each = each.value.provider.saml_config != null ? [each.value.provider.saml_config] : []
    content {
      idp_metadata_xml = saml.value.idp_metadata_xml
    }
  }

  depends_on = [google_iam_workload_identity_pool.pools]
}

# Workload Identity bindings for service accounts
resource "google_service_account_iam_binding" "workload_identity" {
  for_each = {
    for binding in var.workload_identity_config.service_account_bindings :
    "${binding.service_account_key}-${binding.pool_id}-${binding.provider_id}" => binding
    if var.workload_identity_config.enabled
  }

  service_account_id = google_service_account.service_accounts[each.value.service_account_key].name
  role               = "roles/iam.workloadIdentityUser"
  members            = each.value.members

  depends_on = [
    google_service_account.service_accounts,
    google_iam_workload_identity_pool_provider.providers
  ]
}

# Custom IAM Roles
resource "google_project_iam_custom_role" "custom_roles" {
  for_each = local.custom_roles

  project     = var.project_id
  role_id     = each.value.role_id
  title       = each.value.title
  description = each.value.description
  permissions = each.value.permissions
  stage       = each.value.stage
}

# Conditional IAM Bindings
resource "google_project_iam_binding" "conditional_bindings" {
  for_each = {
    for idx, binding in var.advanced_iam_config.conditional_bindings :
    "${binding.role}-${idx}" => binding
    if var.advanced_iam_config.enable_conditional_access
  }

  project = var.project_id
  role    = each.value.role
  members = each.value.members

  condition {
    title       = each.value.condition.title
    description = each.value.condition.description
    expression  = each.value.condition.expression
  }
}

# Cross-Project IAM Bindings
resource "google_project_iam_member" "cross_project_roles" {
  for_each = {
    for idx, binding in local.cross_project_bindings :
    "${binding.sa_key}-${binding.project_id}-${binding.role}" => binding
  }

  project = each.value.project_id
  role    = each.value.role
  member  = "serviceAccount:${each.value.sa_email}"

  dynamic "condition" {
    for_each = each.value.conditions != null ? [each.value.conditions] : []
    content {
      title       = condition.value.title
      description = condition.value.description
      expression  = condition.value.expression
    }
  }

  depends_on = [google_service_account.service_accounts]
}

# Key Rotation Scheduler
resource "google_cloud_scheduler_job" "key_rotation" {
  for_each = {
    for sa_key, sa in var.service_accounts :
    sa_key => sa
    if var.enhanced_security.enable_key_rotation && sa.create_key
  }

  project     = coalesce(each.value.project_id, var.project_id)
  region      = "us-central1"  # Default region for scheduler
  name        = "${each.value.account_id}-key-rotation"
  description = "Automated key rotation for ${each.value.account_id}"
  schedule    = var.enhanced_security.key_rotation_schedule
  time_zone   = "UTC"

  http_target {
    uri         = "https://cloudfunctions.googleapis.com/v1/projects/${var.project_id}/locations/us-central1/functions/rotate-service-account-key:call"
    http_method = "POST"
    body        = base64encode(jsonencode({
      service_account = google_service_account.service_accounts[each.key].email
      project_id      = coalesce(each.value.project_id, var.project_id)
    }))

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.service_accounts[each.key].email
    }
  }

  depends_on = [google_service_account.service_accounts]
}

# Access Logging Configuration
resource "google_logging_project_sink" "service_account_access" {
  count = var.enhanced_security.enable_access_logging ? 1 : 0

  name        = "service-account-access-logs"
  project     = var.project_id
  destination = "storage.googleapis.com/${var.project_id}-sa-access-logs"
  filter      = "protoPayload.serviceName=\"iam.googleapis.com\" AND protoPayload.resourceName=~\"projects/${var.project_id}/serviceAccounts/.*\""
  description = "Export service account access logs for security monitoring"

  unique_writer_identity = true
}

# Monitoring Metrics for Service Account Usage
resource "google_monitoring_metric_descriptor" "service_account_metrics" {
  for_each = {
    "usage_count" = {
      metric_kind = "GAUGE"
      value_type  = "INT64"
      description = "Number of service account authentications"
    }
    "key_age_days" = {
      metric_kind = "GAUGE"
      value_type  = "INT64"
      description = "Age of service account keys in days"
    }
    "access_violations" = {
      metric_kind = "GAUGE"
      value_type  = "INT64"
      description = "Number of access violations detected"
    }
  }

  project      = var.project_id
  type         = "custom.googleapis.com/service_accounts/${each.key}"
  metric_kind  = each.value.metric_kind
  value_type   = each.value.value_type
  description  = each.value.description
  display_name = "Service Account ${title(replace(each.key, "_", " "))}"

  labels {
    key         = "service_account"
    value_type  = "STRING"
    description = "Service account email"
  }

  labels {
    key         = "project"
    value_type  = "STRING"
    description = "Project ID"
  }
}

# Alert Policies for Service Account Monitoring
resource "google_monitoring_alert_policy" "service_account_alerts" {
  for_each = {
    for policy in var.monitoring_config.alerting.alert_policies : policy.name => policy
    if var.monitoring_config.enabled && var.monitoring_config.alerting.enabled
  }

  project      = var.project_id
  display_name = "Service Accounts - ${each.value.name}"
  description  = "Alert policy for service account monitoring"
  combiner     = "OR"

  conditions {
    display_name = each.value.name

    condition_threshold {
      filter         = each.value.condition
      duration       = "300s"
      comparison     = "COMPARISON_GREATER_THAN"
      threshold_value = each.value.threshold

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = each.value.notification_channels

  alert_strategy {
    auto_close = "1800s"
  }
}

# Cloud Function for Key Rotation (if automated rotation is enabled)
resource "google_cloudfunctions_function" "key_rotation_function" {
  count = var.enhanced_security.automated_key_rotation ? 1 : 0

  project = var.project_id
  region  = "us-central1"
  name    = "rotate-service-account-key"

  description          = "Automated service account key rotation function"
  available_memory_mb  = 256
  timeout              = 540
  entry_point         = "rotateKey"
  runtime             = "python39"

  source_archive_bucket = "${var.project_id}-functions-source"
  source_archive_object = "key-rotation.zip"

  environment_variables = {
    PROJECT_ID = var.project_id
    NOTIFICATION_TOPIC = "service-account-notifications"
  }

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = "projects/${var.project_id}/topics/key-rotation-trigger"
  }
}

# Backup Storage for Service Account Configurations
resource "google_storage_bucket" "service_account_backup" {
  count = var.backup_config.enabled ? 1 : 0

  name                        = "${var.project_id}-sa-backup"
  project                     = var.project_id
  location                    = var.backup_config.cross_region_backup ? "US" : "us-central1"
  storage_class               = "COLDLINE"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = var.backup_config.retention_days
    }
  }

  dynamic "encryption" {
    for_each = var.backup_config.backup_encryption.enabled ? [1] : []
    content {
      default_kms_key_name = var.backup_config.backup_encryption.kms_key
    }
  }

  labels = merge(
    var.labels,
    {
      purpose = "service-account-backup"
      backup_type = var.backup_config.cross_region_backup ? "cross-region" : "regional"
    }
  )
}

# Backup Job for Service Account Configurations
resource "google_cloud_scheduler_job" "backup_scheduler" {
  count = var.backup_config.enabled ? 1 : 0

  project     = var.project_id
  region      = "us-central1"
  name        = "service-account-backup"
  description = "Automated backup of service account configurations"
  schedule    = var.backup_config.backup_schedule
  time_zone   = "UTC"

  http_target {
    uri         = "https://cloudfunctions.googleapis.com/v1/projects/${var.project_id}/locations/us-central1/functions/backup-service-accounts:call"
    http_method = "POST"
    body        = base64encode(jsonencode({
      backup_bucket = google_storage_bucket.service_account_backup[0].name
      retention_days = var.backup_config.retention_days
    }))

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
    }
  }

  depends_on = [google_storage_bucket.service_account_backup]
}
