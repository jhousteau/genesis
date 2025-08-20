/**
 * Workload Identity Federation Module
 * 
 * Provides keyless authentication for CI/CD platforms using
 * Workload Identity Federation with attribute-based access control.
 */

locals {
  # Standard attribute mappings for different providers
  default_attribute_mappings = {
    github = {
      "google.subject"                    = "assertion.sub"
      "attribute.actor"                   = "assertion.actor"
      "attribute.repository"              = "assertion.repository"
      "attribute.repository_owner"        = "assertion.repository_owner"
      "attribute.repository_visibility"   = "assertion.repository_visibility"
      "attribute.event_name"              = "assertion.event_name"
      "attribute.ref"                     = "assertion.ref"
      "attribute.ref_type"                = "assertion.ref_type"
      "attribute.workflow"                = "assertion.workflow"
      "attribute.job_workflow_ref"        = "assertion.job_workflow_ref"
      "attribute.environment"              = "assertion.environment"
      "attribute.runner_environment"      = "assertion.runner_environment"
    }
    
    gitlab = {
      "google.subject"                    = "assertion.sub"
      "attribute.namespace_id"            = "assertion.namespace_id"
      "attribute.namespace_path"          = "assertion.namespace_path"
      "attribute.project_id"              = "assertion.project_id"
      "attribute.project_path"            = "assertion.project_path"
      "attribute.user_email"              = "assertion.user_email"
      "attribute.user_login"              = "assertion.user_login"
      "attribute.ref"                     = "assertion.ref"
      "attribute.ref_type"                = "assertion.ref_type"
      "attribute.ref_protected"           = "assertion.ref_protected"
      "attribute.environment"             = "assertion.environment"
      "attribute.environment_protected"   = "assertion.environment_protected"
      "attribute.deployment_tier"         = "assertion.deployment_tier"
      "attribute.pipeline_source"         = "assertion.pipeline_source"
      "attribute.ci_config_ref_uri"       = "assertion.ci_config_ref_uri"
    }
    
    azure_devops = {
      "google.subject"                    = "assertion.sub"
      "attribute.sc"                      = "assertion.sc"
      "attribute.project_id"              = "assertion.teamProjectId"
      "attribute.organization"            = "assertion.organizationId"
      "attribute.definition_id"           = "assertion.pipelineId"
      "attribute.build_id"                = "assertion.runId"
      "attribute.branch"                  = "assertion.ref"
    }
    
    terraform_cloud = {
      "google.subject"                    = "assertion.sub"
      "attribute.terraform_run_phase"     = "assertion.terraform_run_phase"
      "attribute.terraform_run_id"        = "assertion.terraform_run_id"
      "attribute.terraform_workspace_id"  = "assertion.terraform_workspace_id"
      "attribute.terraform_workspace_name" = "assertion.terraform_workspace_name"
      "attribute.terraform_organization_id" = "assertion.terraform_organization_id"
      "attribute.terraform_organization_name" = "assertion.terraform_organization_name"
      "attribute.terraform_project_id"    = "assertion.terraform_project_id"
      "attribute.terraform_project_name"  = "assertion.terraform_project_name"
    }
  }
  
  # Build attribute conditions for each provider
  provider_conditions = {
    for key, provider in var.providers : key => (
      provider.attribute_condition != null ? provider.attribute_condition :
      provider.github != null ? local.github_conditions[key] :
      provider.gitlab != null ? local.gitlab_conditions[key] :
      provider.azure_devops != null ? local.azure_conditions[key] :
      provider.terraform_cloud != null ? local.terraform_conditions[key] :
      null
    )
  }
  
  # GitHub-specific conditions
  github_conditions = {
    for key, provider in var.providers : key => (
      provider.github != null ? join(" && ", compact([
        provider.github.organization != null ? 
          "assertion.repository_owner == '${provider.github.organization}'" : null,
        provider.github.repositories != null && length(provider.github.repositories) > 0 ? 
          "assertion.repository in ${jsonencode(provider.github.repositories)}" : null,
        provider.github.branches != null && length(provider.github.branches) > 0 ? 
          "assertion.ref in ${jsonencode([for b in provider.github.branches : "refs/heads/${b}"])}" : null,
        provider.github.environments != null && length(provider.github.environments) > 0 ? 
          "assertion.environment in ${jsonencode(provider.github.environments)}" : null,
      ])) : null
    )
  }
  
  # GitLab-specific conditions
  gitlab_conditions = {
    for key, provider in var.providers : key => (
      provider.gitlab != null ? join(" && ", compact([
        provider.gitlab.group_path != null ? 
          "assertion.namespace_path == '${provider.gitlab.group_path}'" : null,
        provider.gitlab.project_path != null ? 
          "assertion.project_path == '${provider.gitlab.project_path}'" : null,
        provider.gitlab.branches != null && length(provider.gitlab.branches) > 0 ? 
          "assertion.ref in ${jsonencode([for b in provider.gitlab.branches : "refs/heads/${b}"])}" : null,
        provider.gitlab.environments != null && length(provider.gitlab.environments) > 0 ? 
          "assertion.environment in ${jsonencode(provider.gitlab.environments)}" : null,
        "assertion.ref_protected == 'true'", # Require protected branches
      ])) : null
    )
  }
  
  # Azure DevOps conditions
  azure_conditions = {
    for key, provider in var.providers : key => (
      provider.azure_devops != null ? join(" && ", compact([
        provider.azure_devops.organization != null ? 
          "assertion.organizationId == '${provider.azure_devops.organization}'" : null,
        provider.azure_devops.project != null ? 
          "assertion.teamProjectId == '${provider.azure_devops.project}'" : null,
        provider.azure_devops.branches != null && length(provider.azure_devops.branches) > 0 ? 
          "assertion.ref in ${jsonencode([for b in provider.azure_devops.branches : "refs/heads/${b}"])}" : null,
      ])) : null
    )
  }
  
  # Terraform Cloud conditions
  terraform_conditions = {
    for key, provider in var.providers : key => (
      provider.terraform_cloud != null ? join(" && ", compact([
        provider.terraform_cloud.organization != null ? 
          "assertion.terraform_organization_name == '${provider.terraform_cloud.organization}'" : null,
        provider.terraform_cloud.project != null ? 
          "assertion.terraform_project_name == '${provider.terraform_cloud.project}'" : null,
        provider.terraform_cloud.workspace != null ? 
          "assertion.terraform_workspace_name == '${provider.terraform_cloud.workspace}'" : null,
        provider.terraform_cloud.run_phase != null ? 
          "assertion.terraform_run_phase == '${provider.terraform_cloud.run_phase}'" : null,
      ])) : null
    )
  }
  
  # Determine provider type and settings
  provider_configs = {
    for key, provider in var.providers : key => {
      type = (
        provider.github != null ? "github" :
        provider.gitlab != null ? "gitlab" :
        provider.azure_devops != null ? "azure_devops" :
        provider.terraform_cloud != null ? "terraform_cloud" :
        "custom"
      )
      
      issuer_uri = coalesce(
        provider.issuer_uri,
        provider.github != null ? "https://token.actions.githubusercontent.com" : null,
        provider.gitlab != null ? "https://gitlab.com" : null,
        provider.azure_devops != null ? "https://vstoken.dev.azure.com/${provider.azure_devops.organization}" : null,
        provider.terraform_cloud != null ? "https://app.terraform.io" : null,
        ""
      )
      
      allowed_audiences = length(provider.allowed_audiences) > 0 ? provider.allowed_audiences : (
        provider.github != null ? [] :
        provider.gitlab != null ? ["https://gitlab.com"] :
        provider.azure_devops != null ? ["api://AzureADTokenExchange"] :
        provider.terraform_cloud != null ? ["terraform.io"] :
        []
      )
      
      attribute_mapping = merge(
        local.default_attribute_mappings[local.provider_configs[key].type] != null ? 
          local.default_attribute_mappings[local.provider_configs[key].type] : {},
        provider.attribute_mapping
      )
    }
  }
}

# Create the Workload Identity Pool
resource "google_iam_workload_identity_pool" "main" {
  provider = google-beta
  
  workload_identity_pool_id = var.pool_id
  project                   = var.project_id
  display_name              = coalesce(var.pool_display_name, var.pool_id)
  description               = var.pool_description
  disabled                  = var.pool_disabled
}

# Create Workload Identity Pool Providers
resource "google_iam_workload_identity_pool_provider" "providers" {
  provider = google-beta
  
  for_each = var.providers
  
  workload_identity_pool_id          = google_iam_workload_identity_pool.main.workload_identity_pool_id
  workload_identity_pool_provider_id = each.value.provider_id
  project                            = var.project_id
  
  display_name = coalesce(each.value.display_name, each.value.provider_id)
  description  = coalesce(
    each.value.description,
    "Workload Identity Provider for ${local.provider_configs[each.key].type}"
  )
  disabled     = each.value.disabled
  
  attribute_mapping = local.provider_configs[each.key].attribute_mapping
  
  dynamic "attribute_condition" {
    for_each = var.enable_attribute_conditions && local.provider_conditions[each.key] != null ? [1] : []
    content {
      expression = local.provider_conditions[each.key]
      title      = "Access control for ${each.value.provider_id}"
    }
  }
  
  dynamic "oidc" {
    for_each = local.provider_configs[each.key].issuer_uri != "" ? [1] : []
    content {
      issuer_uri        = local.provider_configs[each.key].issuer_uri
      allowed_audiences = local.provider_configs[each.key].allowed_audiences
      jwks_json        = each.value.jwks_json
    }
  }
}

# Create or reference service accounts
resource "google_service_account" "accounts" {
  for_each = {
    for key, sa in var.service_accounts : key => sa
    if sa.create_new
  }
  
  account_id   = each.value.service_account_id
  display_name = coalesce(each.value.display_name, each.value.service_account_id)
  description  = coalesce(
    each.value.description,
    "Service account for workload identity federation"
  )
  project      = var.project_id
}

# Get existing service accounts
data "google_service_account" "existing" {
  for_each = {
    for key, sa in var.service_accounts : key => sa
    if !sa.create_new && sa.existing_email != null
  }
  
  account_id = each.value.existing_email
  project    = var.project_id
}

# Local to get all service account emails
locals {
  service_account_emails = merge(
    {
      for key, sa in google_service_account.accounts : 
      key => sa.email
    },
    {
      for key, sa in data.google_service_account.existing : 
      key => sa.email
    }
  )
  
  # Flatten bindings for easier iteration
  sa_bindings = flatten([
    for sa_key, sa in var.service_accounts : [
      for binding in sa.bindings : {
        sa_key              = sa_key
        provider_id         = binding.provider_id
        attribute_condition = binding.attribute_condition
        roles              = binding.roles
        sa_email           = local.service_account_emails[sa_key]
      }
    ]
  ])
  
  # Create unique binding keys
  binding_keys = {
    for binding in local.sa_bindings :
    "${binding.sa_key}-${binding.provider_id}-${md5(join("-", binding.roles))}" => binding
  }
}

# Bind service accounts to workload identity pool
resource "google_service_account_iam_member" "workload_identity_binding" {
  for_each = local.binding_keys
  
  service_account_id = each.value.sa_email
  role              = "roles/iam.workloadIdentityUser"
  
  member = var.enable_attribute_conditions && each.value.attribute_condition != null ? 
    "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.main.name}/attribute.${each.value.attribute_condition}" :
    "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.main.name}/*"
  
  depends_on = [
    google_iam_workload_identity_pool_provider.providers
  ]
}

# Grant project-level roles to service accounts
resource "google_project_iam_member" "sa_project_roles" {
  for_each = {
    for item in flatten([
      for sa_key, sa in var.service_accounts : [
        for role in sa.project_roles : {
          key  = "${sa_key}-${role}"
          role = role
          email = local.service_account_emails[sa_key]
        }
      ]
    ]) : item.key => item
  }
  
  project = var.project_id
  role    = each.value.role
  member  = "serviceAccount:${each.value.email}"
}