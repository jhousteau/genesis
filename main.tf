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

# This is an example root main.tf file
# Use the environment-specific configurations in environments/ directory

locals {
  project_name = var.project_name != "" ? var.project_name : "${var.project_id}-${var.environment}"
  state_bucket = var.state_bucket_name != "" ? var.state_bucket_name : "tf-state-${var.project_id}"
  
  common_labels = merge(
    var.labels,
    {
      environment = var.environment
      project     = var.project_id
    }
  )
}

# Data source for project information
data "google_project" "project" {
  project_id = var.project_id
}

# Example of using the bootstrap module
module "bootstrap" {
  source = "./modules/bootstrap"
  count  = var.environment == "bootstrap" ? 1 : 0

  org_id          = var.org_id
  billing_account = var.billing_account
  project_id      = var.project_id
  project_name    = local.project_name
  folder_id       = var.folder_id
  
  activate_apis = var.activate_apis
  labels        = local.common_labels
}

# Example of using the state-backend module
module "state_backend" {
  source = "./modules/state-backend"
  count  = var.state_bucket_name != "" ? 1 : 0

  project_id      = var.project_id
  bucket_name     = local.state_bucket
  bucket_location = var.state_bucket_location
  
  labels = local.common_labels
}

# Example of using the service-accounts module
module "service_accounts" {
  source = "./modules/service-accounts"
  count  = var.create_terraform_sa ? 1 : 0

  project_id        = var.project_id
  service_accounts = [{
    account_id   = var.terraform_sa_name
    display_name = "Terraform Service Account"
    description  = "Service account for Terraform automation"
    roles        = var.terraform_sa_roles
  }]
  
  labels = local.common_labels
}

# Example of using the workload-identity module
module "workload_identity" {
  source = "./modules/workload-identity"
  count  = var.enable_workload_identity ? 1 : 0

  project_id  = var.project_id
  github_org  = var.github_org
  github_repo = var.github_repo
  
  service_account_email = var.create_terraform_sa ? module.service_accounts[0].service_account_emails[var.terraform_sa_name] : ""
  
  labels = local.common_labels
}

# Conditional resource creation based on variables
resource "google_service_account" "terraform" {
  count = var.create_terraform_sa && var.environment != "bootstrap" ? 1 : 0

  project      = var.project_id
  account_id   = var.terraform_sa_name
  display_name = "Terraform Service Account"
  description  = "Service account for Terraform automation in ${var.environment}"
}

resource "google_project_iam_member" "terraform_roles" {
  for_each = var.create_terraform_sa && var.environment != "bootstrap" ? toset(var.terraform_sa_roles) : []

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.terraform[0].email}"
}

# Workload Identity Federation resources
resource "google_iam_workload_identity_pool" "github" {
  count = var.enable_workload_identity && var.environment != "bootstrap" ? 1 : 0

  project                   = var.project_id
  workload_identity_pool_id = "github-pool-${var.environment}"
  display_name              = "GitHub Actions Pool ${var.environment}"
  description               = "Workload Identity Pool for GitHub Actions in ${var.environment}"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  count = var.enable_workload_identity && var.environment != "bootstrap" ? 1 : 0

  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github[0].workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider-${var.environment}"
  display_name                        = "GitHub Provider ${var.environment}"
  
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Network resources
resource "google_compute_network" "main" {
  count = var.create_network ? 1 : 0

  project                 = var.project_id
  name                    = "${var.network_name}-${var.environment}"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "main" {
  count = var.create_network ? 1 : 0

  project       = var.project_id
  name          = "${var.network_name}-${var.environment}-${var.region}"
  network       = google_compute_network.main[0].self_link
  region        = var.region
  ip_cidr_range = var.subnet_cidr

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# KMS resources
resource "google_kms_key_ring" "terraform" {
  count = var.enable_kms ? 1 : 0

  project  = var.project_id
  name     = "${var.kms_keyring_name}-${var.environment}"
  location = var.region
}

resource "google_kms_crypto_key" "terraform" {
  count = var.enable_kms ? 1 : 0

  name     = "${var.kms_crypto_key_name}-${var.environment}"
  key_ring = google_kms_key_ring.terraform[0].id
  purpose  = "ENCRYPT_DECRYPT"

  rotation_period = "7776000s" # 90 days

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"
  }

  labels = local.common_labels
}