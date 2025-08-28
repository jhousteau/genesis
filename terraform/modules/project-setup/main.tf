/**
 * Project Setup Module - Complete Project Initialization
 * 
 * Combines project bootstrap, state backend, and service accounts for quick setup.
 * Follows Genesis principle: One module, one complete workflow.
 */

# Create the project
module "bootstrap" {
  source = "../bootstrap"

  project_id                     = var.project_id
  project_name                   = var.project_name
  organization_id                = var.organization_id
  folder_id                      = var.folder_id
  billing_account                = var.billing_account
  environment                    = var.environment
  auto_create_network            = var.auto_create_network
  additional_apis                = var.additional_apis
  create_default_service_account = false # We'll create our own
  budget_amount                  = var.budget_amount
  labels                         = var.labels
}

# Create the Terraform state backend
module "state_backend" {
  source = "../state-backend"

  project_id             = module.bootstrap.project_id
  bucket_name            = var.state_bucket_name
  location               = var.location
  environment            = var.environment
  create_terraform_sa    = true
  terraform_sa_name      = "terraform"
  workload_identity_user = var.workload_identity_user
  labels                 = var.labels

  depends_on = [module.bootstrap]
}

# Create additional service accounts if specified
module "service_accounts" {
  count  = length(var.service_accounts) > 0 ? 1 : 0
  source = "../service-accounts"

  project_id       = module.bootstrap.project_id
  service_accounts = var.service_accounts

  depends_on = [module.bootstrap]
}

# Enable additional APIs after project creation
resource "google_project_service" "runtime_apis" {
  for_each = toset(var.runtime_apis)

  project = module.bootstrap.project_id
  service = each.value

  disable_on_destroy         = false
  disable_dependent_services = false

  depends_on = [module.bootstrap]
}