# Multi-Project Bootstrap Module
# Deploys bootstrap configuration to multiple GCP projects simultaneously

locals {
  # Flatten project configurations for iteration
  project_configs = { for p in var.projects : p.project_id => p }

  # Generate unique state bucket names if not provided
  state_buckets = { for k, p in local.project_configs :
    k => p.state_bucket_name != null ? p.state_bucket_name : "tf-state-${k}-${random_id.bucket_suffix[k].hex}"
  }

  # Merge default settings with project-specific overrides
  merged_projects = { for k, p in local.project_configs :
    k => merge(var.default_settings, p)
  }
}

# Random suffix for bucket names
resource "random_id" "bucket_suffix" {
  for_each = local.project_configs

  byte_length = 4
}

# Create/configure projects
module "bootstrap" {
  for_each = local.merged_projects
  source   = "../bootstrap"

  # Project configuration
  project_id      = each.value.project_id
  project_name    = try(each.value.project_name, each.value.project_id)
  billing_account = each.value.billing_account
  org_id          = try(each.value.org_id, var.org_id)
  folder_id       = try(each.value.folder_id, var.folder_id)

  # Environment and labels
  environment = try(each.value.environment, "production")
  labels = merge(
    var.default_labels,
    try(each.value.labels, {}),
    {
      managed_by    = "terraform"
      bootstrap_set = var.deployment_name
      project_group = var.project_group
    }
  )

  # APIs to enable
  activate_apis               = try(each.value.activate_apis, var.default_apis)
  disable_services_on_destroy = try(each.value.disable_services_on_destroy, false)

  # Service account configuration
  create_terraform_sa = try(each.value.create_terraform_sa, true)
  terraform_sa_name   = try(each.value.terraform_sa_name, "terraform-${each.value.project_id}")
  terraform_sa_roles  = try(each.value.terraform_sa_roles, var.default_terraform_roles)

  # Budget configuration
  budget_amount           = try(each.value.budget_amount, var.default_budget_amount)
  budget_alert_thresholds = try(each.value.budget_alert_thresholds, var.default_budget_alerts)

  # Additional settings
  default_region     = try(each.value.region, var.default_region)
  grant_billing_role = try(each.value.grant_billing_role, false)
  skip_delete        = try(each.value.skip_delete, false)
}

# Create state buckets for each project
module "state_backend" {
  for_each = var.create_state_buckets ? local.merged_projects : {}
  source   = "../state-backend"

  project_id    = each.value.project_id
  bucket_name   = local.state_buckets[each.key]
  location      = try(each.value.state_bucket_location, var.default_region)
  storage_class = try(each.value.storage_class, "STANDARD")

  # Versioning and lifecycle
  versioning      = true
  lifecycle_rules = try(each.value.lifecycle_rules, var.default_lifecycle_rules)

  # Security
  uniform_bucket_level_access = true
  force_destroy               = try(each.value.force_destroy_state, false)

  labels = {
    environment = try(each.value.environment, "production")
    project     = each.value.project_id
    managed_by  = "terraform"
  }

  depends_on = [module.bootstrap]
}

# Create service accounts for each project
module "service_accounts" {
  for_each = var.create_service_accounts ? local.merged_projects : {}
  source   = "../service-accounts"

  project_id = each.value.project_id

  service_accounts = merge(
    # Default service accounts
    var.create_default_service_accounts ? {
      cicd = {
        account_id    = "cicd-${each.value.project_id}"
        display_name  = "CI/CD Pipeline"
        description   = "Service account for CI/CD operations"
        project_roles = try(each.value.cicd_roles, var.default_cicd_roles)
      }
      monitoring = {
        account_id    = "monitoring-${each.value.project_id}"
        display_name  = "Monitoring"
        description   = "Service account for monitoring and observability"
        project_roles = ["roles/monitoring.metricWriter", "roles/logging.logWriter"]
      }
      app = {
        account_id    = "app-${each.value.project_id}"
        display_name  = "Application"
        description   = "Service account for application runtime"
        project_roles = try(each.value.app_roles, var.default_app_roles)
      }
    } : {},
    # Custom service accounts per project
    try(each.value.custom_service_accounts, {})
  )

  depends_on = [module.bootstrap]
}

# Configure Workload Identity Federation for each project
module "workload_identity" {
  for_each = var.enable_workload_identity ? local.merged_projects : {}
  source   = "../workload-identity"

  project_id = each.value.project_id
  pool_id    = try(each.value.pool_id, "cicd-pool-${each.value.project_id}")

  providers = try(each.value.workload_identity_providers, var.default_wif_providers)

  service_accounts = {
    deploy = {
      service_account_id = "wif-deploy-${each.value.project_id}"
      display_name       = "WIF Deployment Account"
      project_roles      = try(each.value.wif_roles, var.default_wif_roles)

      bindings = [for provider_id in keys(try(each.value.workload_identity_providers, var.default_wif_providers)) : {
        provider_id = provider_id
      }]
    }
  }

  depends_on = [module.bootstrap]
}

# Create networking resources if specified
resource "google_compute_network" "vpc" {
  for_each = { for k, p in local.merged_projects : k => p if try(p.create_network, false) }

  project                 = each.value.project_id
  name                    = try(each.value.network_name, "vpc-${each.value.project_id}")
  auto_create_subnetworks = false
  routing_mode            = try(each.value.routing_mode, "REGIONAL")

  depends_on = [module.bootstrap]
}

# Create subnets if networking is enabled
resource "google_compute_subnetwork" "subnets" {
  for_each = { for k, p in local.merged_projects : k => p if try(p.create_network, false) && try(p.subnets, null) != null }

  project       = each.value.project_id
  name          = each.value.subnets[0].name
  network       = google_compute_network.vpc[each.key].id
  region        = try(each.value.subnets[0].region, var.default_region)
  ip_cidr_range = each.value.subnets[0].cidr

  private_ip_google_access = true

  dynamic "log_config" {
    for_each = try(each.value.enable_flow_logs, false) ? [1] : []
    content {
      aggregation_interval = "INTERVAL_5_SEC"
      flow_sampling        = 0.5
      metadata             = "INCLUDE_ALL_METADATA"
    }
  }

  depends_on = [google_compute_network.vpc]
}
