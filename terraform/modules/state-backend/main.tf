/**
 * Terraform State Backend Module - Simplified and Essential
 *
 * Creates a GCS bucket for Terraform state with basic security and versioning.
 * Follows Genesis principle: Simple, focused, and actually used.
 */

locals {
  bucket_name = var.bucket_name != "" ? var.bucket_name : "${var.project_id}-terraform-state"

  default_labels = {
    purpose     = "terraform-state"
    environment = var.environment
    project     = var.project_id
    managed_by  = "terraform"
  }

  labels = merge(local.default_labels, var.labels)
}

# Main Terraform state bucket
resource "google_storage_bucket" "state_bucket" {
  name                        = local.bucket_name
  project                     = var.project_id
  location                    = var.location
  storage_class               = var.storage_class
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  # Enable versioning for state file safety
  versioning {
    enabled = true
  }

  # Lifecycle rule to manage old versions
  lifecycle_rule {
    condition {
      num_newer_versions = var.max_versions
    }
    action {
      type = "Delete"
    }
  }

  # Encryption (Google-managed by default, can override with KMS key)
  dynamic "encryption" {
    for_each = var.kms_key_name != null ? [1] : []
    content {
      default_kms_key_name = var.kms_key_name
    }
  }

  labels = local.labels
}

# Optional: Create a service account for Terraform operations
resource "google_service_account" "terraform_sa" {
  count = var.create_terraform_sa ? 1 : 0

  project      = var.project_id
  account_id   = var.terraform_sa_name
  display_name = "Terraform Service Account"
  description  = "Service account for Terraform state operations"
}

# Grant the service account access to the bucket
resource "google_storage_bucket_iam_member" "terraform_sa_admin" {
  count = var.create_terraform_sa ? 1 : 0

  bucket = google_storage_bucket.state_bucket.name
  role   = "roles/storage.admin"
  member = "serviceAccount:${google_service_account.terraform_sa[0].email}"
}

# Optional: Create Workload Identity binding for GitHub Actions
resource "google_service_account_iam_member" "workload_identity" {
  count = var.workload_identity_user != null ? 1 : 0

  service_account_id = google_service_account.terraform_sa[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = var.workload_identity_user
}
