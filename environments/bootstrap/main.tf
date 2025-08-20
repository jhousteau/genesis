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

# Bootstrap Environment Configuration
# This configuration sets up the initial GCP infrastructure

locals {
  environment = "bootstrap"
  
  # Generate unique bucket name if not provided
  state_bucket_name = var.state_bucket_name != "" ? var.state_bucket_name : "tf-state-${var.org_id}-${local.environment}"
  
  # Common labels for all resources
  common_labels = merge(
    var.labels,
    {
      environment = local.environment
      managed-by  = "terraform"
      purpose     = "bootstrap"
    }
  )
  
  # Essential APIs for bootstrap
  bootstrap_apis = concat(
    var.activate_apis,
    [
      "cloudresourcemanager.googleapis.com",
      "cloudbilling.googleapis.com",
      "iam.googleapis.com",
      "storage-api.googleapis.com",
      "storage-component.googleapis.com",
      "serviceusage.googleapis.com",
      "cloudkms.googleapis.com",
      "secretmanager.googleapis.com",
      "logging.googleapis.com",
      "monitoring.googleapis.com"
    ]
  )
}

# Create the bootstrap project
resource "google_project" "bootstrap" {
  name            = var.project_name != "" ? var.project_name : "Bootstrap Project"
  project_id      = var.project_id
  org_id          = var.folder_id == "" ? var.org_id : null
  folder_id       = var.folder_id != "" ? var.folder_id : null
  billing_account = var.billing_account
  
  labels = local.common_labels
}

# Enable required APIs
resource "google_project_service" "bootstrap_apis" {
  for_each = toset(local.bootstrap_apis)
  
  project = google_project.bootstrap.project_id
  service = each.value
  
  disable_on_destroy = false
}

# Create the state bucket for Terraform
module "terraform_state_backend" {
  source = "../../modules/state-backend"
  
  project_id      = google_project.bootstrap.project_id
  bucket_name     = local.state_bucket_name
  bucket_location = var.state_bucket_location
  
  enable_versioning = true
  force_destroy     = false
  
  lifecycle_rules = [
    {
      action = {
        type = "Delete"
      }
      condition = {
        age        = 365
        with_state = "ARCHIVED"
      }
    }
  ]
  
  labels = local.common_labels
  
  depends_on = [google_project_service.bootstrap_apis]
}

# Create Terraform service account
resource "google_service_account" "terraform" {
  project      = google_project.bootstrap.project_id
  account_id   = var.terraform_sa_name
  display_name = "Terraform Automation"
  description  = "Service account for Terraform automation across all environments"
}

# Grant necessary roles to Terraform service account
resource "google_organization_iam_member" "terraform_org_admin" {
  count = var.grant_org_admin ? 1 : 0
  
  org_id = var.org_id
  role   = "roles/resourcemanager.organizationAdmin"
  member = "serviceAccount:${google_service_account.terraform.email}"
}

resource "google_organization_iam_member" "terraform_billing_admin" {
  org_id = var.org_id
  role   = "roles/billing.admin"
  member = "serviceAccount:${google_service_account.terraform.email}"
}

resource "google_organization_iam_member" "terraform_project_creator" {
  org_id = var.org_id
  role   = "roles/resourcemanager.projectCreator"
  member = "serviceAccount:${google_service_account.terraform.email}"
}

resource "google_organization_iam_member" "terraform_folder_admin" {
  count = var.folder_id != "" ? 1 : 0
  
  org_id = var.org_id
  role   = "roles/resourcemanager.folderAdmin"
  member = "serviceAccount:${google_service_account.terraform.email}"
}

# Create service account key for local development (optional)
resource "google_service_account_key" "terraform" {
  count = var.create_sa_key ? 1 : 0
  
  service_account_id = google_service_account.terraform.name
  key_algorithm      = "KEY_ALG_RSA_2048"
}

# Set up Workload Identity for GitHub Actions
module "github_workload_identity" {
  source = "../../modules/workload-identity"
  count  = var.enable_workload_identity ? 1 : 0
  
  project_id    = google_project.bootstrap.project_id
  pool_id       = "github-pool"
  provider_id   = "github-provider"
  github_org    = var.github_org
  github_repo   = var.github_repo
  
  service_account_email = google_service_account.terraform.email
  
  attribute_condition = "assertion.repository_owner=='${var.github_org}'"
  
  labels = local.common_labels
  
  depends_on = [google_project_service.bootstrap_apis]
}

# Create KMS keyring and key for state encryption
resource "google_kms_key_ring" "terraform_state" {
  count = var.enable_state_encryption ? 1 : 0
  
  project  = google_project.bootstrap.project_id
  name     = "terraform-state-keyring"
  location = var.state_bucket_location
  
  depends_on = [google_project_service.bootstrap_apis]
}

resource "google_kms_crypto_key" "terraform_state" {
  count = var.enable_state_encryption ? 1 : 0
  
  name            = "terraform-state-key"
  key_ring        = google_kms_key_ring.terraform_state[0].id
  rotation_period = "7776000s" # 90 days
  purpose         = "ENCRYPT_DECRYPT"
  
  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }
  
  labels = local.common_labels
}

# Grant KMS permissions to the state bucket
resource "google_storage_bucket_iam_member" "terraform_state_kms" {
  count = var.enable_state_encryption ? 1 : 0
  
  bucket = module.terraform_state_backend.bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.terraform.email}"
}

# Create bootstrap network (optional)
resource "google_compute_network" "bootstrap" {
  count = var.create_bootstrap_network ? 1 : 0
  
  project                 = google_project.bootstrap.project_id
  name                    = "bootstrap-network"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  
  depends_on = [google_project_service.bootstrap_apis]
}

resource "google_compute_subnetwork" "bootstrap" {
  count = var.create_bootstrap_network ? 1 : 0
  
  project       = google_project.bootstrap.project_id
  name          = "bootstrap-subnet-${var.region}"
  network       = google_compute_network.bootstrap[0].self_link
  region        = var.region
  ip_cidr_range = var.bootstrap_subnet_cidr
  
  private_ip_google_access = true
  
  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.1
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Create Cloud NAT for outbound connectivity (optional)
resource "google_compute_router" "bootstrap" {
  count = var.create_bootstrap_network ? 1 : 0
  
  project = google_project.bootstrap.project_id
  name    = "bootstrap-router"
  network = google_compute_network.bootstrap[0].self_link
  region  = var.region
}

resource "google_compute_router_nat" "bootstrap" {
  count = var.create_bootstrap_network ? 1 : 0
  
  project = google_project.bootstrap.project_id
  name    = "bootstrap-nat"
  router  = google_compute_router.bootstrap[0].name
  region  = var.region
  
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}