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
      "google.subject"                  = "assertion.sub"
      "attribute.actor"                 = "assertion.actor"
      "attribute.repository"            = "assertion.repository"
      "attribute.repository_owner"      = "assertion.repository_owner"
      "attribute.repository_visibility" = "assertion.repository_visibility"
      "attribute.event_name"            = "assertion.event_name"
      "attribute.ref"                   = "assertion.ref"
      "attribute.ref_type"              = "assertion.ref_type"
      "attribute.workflow"              = "assertion.workflow"
      "attribute.job_workflow_ref"      = "assertion.job_workflow_ref"
      "attribute.environment"           = "assertion.environment"
      "attribute.runner_environment"    = "assertion.runner_environment"
    }

    gitlab = {
      "google.subject"                  = "assertion.sub"
      "attribute.namespace_id"          = "assertion.namespace_id"
      "attribute.namespace_path"        = "assertion.namespace_path"
      "attribute.project_id"            = "assertion.project_id"
      "attribute.project_path"          = "assertion.project_path"
      "attribute.user_email"            = "assertion.user_email"
      "attribute.user_login"            = "assertion.user_login"
      "attribute.ref"                   = "assertion.ref"
      "attribute.ref_type"              = "assertion.ref_type"
      "attribute.ref_protected"         = "assertion.ref_protected"
      "attribute.environment"           = "assertion.environment"
      "attribute.environment_protected" = "assertion.environment_protected"
      "attribute.deployment_tier"       = "assertion.deployment_tier"
      "attribute.pipeline_source"       = "assertion.pipeline_source"
      "attribute.ci_config_ref_uri"     = "assertion.ci_config_ref_uri"
    }

    azure_devops = {
      "google.subject"          = "assertion.sub"
      "attribute.sc"            = "assertion.sc"
      "attribute.project_id"    = "assertion.teamProjectId"
      "attribute.organization"  = "assertion.organizationId"
      "attribute.definition_id" = "assertion.pipelineId"
      "attribute.build_id"      = "assertion.runId"
      "attribute.branch"        = "assertion.ref"
    }

    terraform_cloud = {
      "google.subject"                        = "assertion.sub"
      "attribute.terraform_run_phase"         = "assertion.terraform_run_phase"
      "attribute.terraform_run_id"            = "assertion.terraform_run_id"
      "attribute.terraform_workspace_id"      = "assertion.terraform_workspace_id"
      "attribute.terraform_workspace_name"    = "assertion.terraform_workspace_name"
      "attribute.terraform_organization_id"   = "assertion.terraform_organization_id"
      "attribute.terraform_organization_name" = "assertion.terraform_organization_name"
      "attribute.terraform_project_id"        = "assertion.terraform_project_id"
      "attribute.terraform_project_name"      = "assertion.terraform_project_name"
    }

    jenkins = {
      "google.subject"         = "assertion.sub"
      "attribute.jenkins_url"  = "assertion.jenkins_url"
      "attribute.build_number" = "assertion.build_number"
      "attribute.job_name"     = "assertion.job_name"
      "attribute.node_name"    = "assertion.node_name"
      "attribute.user_id"      = "assertion.user_id"
      "attribute.build_url"    = "assertion.build_url"
      "attribute.workspace"    = "assertion.workspace"
      "attribute.git_branch"   = "assertion.git_branch"
      "attribute.git_commit"   = "assertion.git_commit"
    }

    circleci = {
      "google.subject"               = "assertion.sub"
      "attribute.project_id"         = "assertion.oidc.circleci.project-id"
      "attribute.context_id"         = "assertion.oidc.circleci.context-id"
      "attribute.job_id"             = "assertion.oidc.circleci.job-id"
      "attribute.vcs_origin"         = "assertion.oidc.circleci.vcs.origin"
      "attribute.vcs_ref"            = "assertion.oidc.circleci.vcs.ref"
      "attribute.vcs_repository_url" = "assertion.oidc.circleci.vcs.repository-url"
      "attribute.vcs_type"           = "assertion.oidc.circleci.vcs.type"
    }

    bitbucket = {
      "google.subject"          = "assertion.sub"
      "attribute.workspace"     = "assertion.workspaceUuid"
      "attribute.repository"    = "assertion.repositoryUuid"
      "attribute.branch"        = "assertion.branchName"
      "attribute.build_number"  = "assertion.buildNumber"
      "attribute.pipeline_uuid" = "assertion.pipelineUuid"
      "attribute.step_uuid"     = "assertion.stepUuid"
    }

    spinnaker = {
      "google.subject"          = "assertion.sub"
      "attribute.application"   = "assertion.application"
      "attribute.pipeline_name" = "assertion.pipeline_name"
      "attribute.execution_id"  = "assertion.execution_id"
      "attribute.stage_name"    = "assertion.stage_name"
      "attribute.account"       = "assertion.account"
      "attribute.user"          = "assertion.user"
    }

    harness = {
      "google.subject"            = "assertion.sub"
      "attribute.account_id"      = "assertion.harness.accountId"
      "attribute.organization_id" = "assertion.harness.orgId"
      "attribute.project_id"      = "assertion.harness.projectId"
      "attribute.pipeline_id"     = "assertion.harness.pipelineId"
      "attribute.service_id"      = "assertion.harness.serviceId"
      "attribute.environment_id"  = "assertion.harness.envId"
    }

    aws_codebuild = {
      "google.subject"         = "assertion.sub"
      "attribute.aws_account"  = "assertion.aws:account-id"
      "attribute.aws_region"   = "assertion.aws:region"
      "attribute.project_name" = "assertion.aws:codebuild:project-name"
      "attribute.build_id"     = "assertion.aws:codebuild:build-id"
      "attribute.source_repo"  = "assertion.aws:codebuild:source-repo"
      "attribute.branch"       = "assertion.aws:codebuild:resolved-source-version"
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
      provider.jenkins != null ? local.jenkins_conditions[key] :
      provider.circleci != null ? local.circleci_conditions[key] :
      provider.bitbucket != null ? local.bitbucket_conditions[key] :
      provider.spinnaker != null ? local.spinnaker_conditions[key] :
      provider.harness != null ? local.harness_conditions[key] :
      provider.aws_codebuild != null ? local.aws_codebuild_conditions[key] :
      provider.custom_oidc != null ? local.custom_oidc_conditions[key] :
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

  # Jenkins conditions
  jenkins_conditions = {
    for key, provider in var.providers : key => (
      provider.jenkins != null ? join(" && ", compact([
        provider.jenkins.jenkins_url != null ?
        "assertion.jenkins_url == '${provider.jenkins.jenkins_url}'" : null,
        provider.jenkins.job_name != null ?
        "assertion.job_name == '${provider.jenkins.job_name}'" : null,
        provider.jenkins.user_id != null ?
        "assertion.user_id == '${provider.jenkins.user_id}'" : null,
        provider.jenkins.git_branch != null ?
        "assertion.git_branch == '${provider.jenkins.git_branch}'" : null,
      ])) : null
    )
  }

  # CircleCI conditions
  circleci_conditions = {
    for key, provider in var.providers : key => (
      provider.circleci != null ? join(" && ", compact([
        provider.circleci.organization != null ?
        "assertion.oidc.circleci.project-id.startsWith('${provider.circleci.organization}/')" : null,
        provider.circleci.project_id != null ?
        "assertion.oidc.circleci.project-id == '${provider.circleci.project_id}'" : null,
        provider.circleci.vcs_type != null ?
        "assertion.oidc.circleci.vcs.type == '${provider.circleci.vcs_type}'" : null,
        provider.circleci.repository != null ?
        "assertion.oidc.circleci.vcs.repository-url.contains('${provider.circleci.repository}')" : null,
      ])) : null
    )
  }

  # Bitbucket conditions
  bitbucket_conditions = {
    for key, provider in var.providers : key => (
      provider.bitbucket != null ? join(" && ", compact([
        provider.bitbucket.workspace != null ?
        "assertion.workspaceUuid == '${provider.bitbucket.workspace}'" : null,
        provider.bitbucket.repository != null ?
        "assertion.repositoryUuid == '${provider.bitbucket.repository}'" : null,
        provider.bitbucket.branch != null ?
        "assertion.branchName == '${provider.bitbucket.branch}'" : null,
      ])) : null
    )
  }

  # Spinnaker conditions
  spinnaker_conditions = {
    for key, provider in var.providers : key => (
      provider.spinnaker != null ? join(" && ", compact([
        provider.spinnaker.application != null ?
        "assertion.application == '${provider.spinnaker.application}'" : null,
        provider.spinnaker.pipeline_name != null ?
        "assertion.pipeline_name == '${provider.spinnaker.pipeline_name}'" : null,
        provider.spinnaker.account != null ?
        "assertion.account == '${provider.spinnaker.account}'" : null,
      ])) : null
    )
  }

  # Harness conditions
  harness_conditions = {
    for key, provider in var.providers : key => (
      provider.harness != null ? join(" && ", compact([
        provider.harness.account_id != null ?
        "assertion.harness.accountId == '${provider.harness.account_id}'" : null,
        provider.harness.organization_id != null ?
        "assertion.harness.orgId == '${provider.harness.organization_id}'" : null,
        provider.harness.project_id != null ?
        "assertion.harness.projectId == '${provider.harness.project_id}'" : null,
        provider.harness.pipeline_id != null ?
        "assertion.harness.pipelineId == '${provider.harness.pipeline_id}'" : null,
      ])) : null
    )
  }

  # AWS CodeBuild conditions
  aws_codebuild_conditions = {
    for key, provider in var.providers : key => (
      provider.aws_codebuild != null ? join(" && ", compact([
        provider.aws_codebuild.aws_account_id != null ?
        "assertion['aws:account-id'] == '${provider.aws_codebuild.aws_account_id}'" : null,
        provider.aws_codebuild.aws_region != null ?
        "assertion['aws:region'] == '${provider.aws_codebuild.aws_region}'" : null,
        provider.aws_codebuild.project_name != null ?
        "assertion['aws:codebuild:project-name'] == '${provider.aws_codebuild.project_name}'" : null,
      ])) : null
    )
  }

  # Custom OIDC conditions
  custom_oidc_conditions = {
    for key, provider in var.providers : key => (
      provider.custom_oidc != null && length(provider.custom_oidc.allowed_claims) > 0 ?
      join(" && ", flatten([
        for claim, allowed_values in provider.custom_oidc.allowed_claims : [
          for value in allowed_values : "assertion.${claim} == '${value}'"
        ]
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
        provider.jenkins != null ? "jenkins" :
        provider.circleci != null ? "circleci" :
        provider.bitbucket != null ? "bitbucket" :
        provider.spinnaker != null ? "spinnaker" :
        provider.harness != null ? "harness" :
        provider.aws_codebuild != null ? "aws_codebuild" :
        provider.custom_oidc != null ? "custom_oidc" :
        "custom"
      )

      issuer_uri = coalesce(
        provider.issuer_uri,
        provider.github != null ? "https://token.actions.githubusercontent.com" : null,
        provider.gitlab != null ? "https://gitlab.com" : null,
        provider.azure_devops != null ? "https://vstoken.dev.azure.com/${provider.azure_devops.organization}" : null,
        provider.terraform_cloud != null ? "https://app.terraform.io" : null,
        provider.jenkins != null ? provider.jenkins.jenkins_url : null,
        provider.circleci != null ? "https://oidc.circleci.com/org/${provider.circleci.organization}" : null,
        provider.bitbucket != null ? "https://api.bitbucket.org/2.0/workspaces/${provider.bitbucket.workspace}/pipelines-config/identity/oidc" : null,
        provider.spinnaker != null ? "https://spinnaker.io" : null,
        provider.harness != null ? "https://app.harness.io/gateway/oidc/account/${provider.harness.account_id}" : null,
        provider.aws_codebuild != null ? "https://codebuild.${provider.aws_codebuild.aws_region}.amazonaws.com" : null,
        provider.custom_oidc != null ? provider.custom_oidc.issuer_uri : null,
        ""
      )

      allowed_audiences = length(provider.allowed_audiences) > 0 ? provider.allowed_audiences : (
        provider.github != null ? [] :
        provider.gitlab != null ? ["https://gitlab.com"] :
        provider.azure_devops != null ? ["api://AzureADTokenExchange"] :
        provider.terraform_cloud != null ? ["terraform.io"] :
        provider.jenkins != null ? [provider.jenkins.jenkins_url] :
        provider.circleci != null ? ["${provider.circleci.organization}"] :
        provider.bitbucket != null ? ["ari:cloud:bitbucket::workspace/${provider.bitbucket.workspace}"] :
        provider.spinnaker != null ? ["spinnaker"] :
        provider.harness != null ? ["harness.io"] :
        provider.aws_codebuild != null ? ["sts.amazonaws.com"] :
        provider.custom_oidc != null ? provider.custom_oidc.audience :
        []
      )

      attribute_mapping = merge(
        lookup(local.default_attribute_mappings, local.provider_configs[key].type, {}),
        provider.custom_oidc != null ? provider.custom_oidc.claims_mapping : {},
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
  description = coalesce(
    each.value.description,
    "Workload Identity Provider for ${local.provider_configs[each.key].type}"
  )
  disabled = each.value.disabled

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
      jwks_json         = each.value.jwks_json
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
  description = coalesce(
    each.value.description,
    "Service account for workload identity federation"
  )
  project = var.project_id
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
        roles               = binding.roles
        sa_email            = local.service_account_emails[sa_key]
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
  role               = "roles/iam.workloadIdentityUser"

  member = var.enable_attribute_conditions && each.value.attribute_condition != null ? "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.main.name}/attribute.${each.value.attribute_condition}" : "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.main.name}/*"

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
          key   = "${sa_key}-${role}"
          role  = role
          email = local.service_account_emails[sa_key]
        }
      ]
    ]) : item.key => item
  }

  project = var.project_id
  role    = each.value.role
  member  = "serviceAccount:${each.value.email}"
}
# Data source to get project details
data "google_project" "current" {
  project_id = var.project_id
}

# Audit Log Sink for Workload Identity operations
resource "google_logging_project_sink" "workload_identity_audit" {
  count = var.enable_audit_logging ? 1 : 0

  name    = var.audit_log_config.log_sink_name
  project = var.project_id

  # Destination configuration
  destination = (
    var.audit_log_config.destination_type == "bigquery" && var.audit_log_config.bigquery_dataset != null ?
    "bigquery.googleapis.com/projects/${var.project_id}/datasets/${var.audit_log_config.bigquery_dataset}" :
    var.audit_log_config.destination_type == "pubsub" && var.audit_log_config.pubsub_topic != null ?
    "pubsub.googleapis.com/projects/${var.project_id}/topics/${var.audit_log_config.pubsub_topic}" :
    var.audit_log_config.destination_type == "cloud_storage" && var.audit_log_config.cloud_storage_bucket != null ?
    "storage.googleapis.com/${var.audit_log_config.cloud_storage_bucket}" :
    "logging.googleapis.com/projects/${var.project_id}/logs/${var.audit_log_config.log_sink_name}"
  )

  # Filter for workload identity operations
  filter = coalesce(
    var.audit_log_config.filter_expression,
    <<-EOT
      protoPayload.serviceName="iam.googleapis.com" AND
      (
        protoPayload.methodName="google.iam.v1.IAMPolicy.GetIamPolicy" OR
        protoPayload.methodName="google.iam.v1.IAMPolicy.SetIamPolicy" OR
        protoPayload.methodName="GenerateAccessToken" OR
        protoPayload.methodName="GenerateIdToken"
      ) AND
      protoPayload.resourceName:"workloadIdentityPools"
    EOT
  )

  unique_writer_identity = true
  include_children       = var.audit_log_config.include_children
}

# Monitoring Dashboard for Workload Identity
resource "google_monitoring_dashboard" "workload_identity" {
  count = var.monitoring_config.enable_metrics ? 1 : 0

  project = var.project_id
  dashboard_json = jsonencode({
    displayName = "Workload Identity Federation Dashboard"
    mosaicLayout = {
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Authentication Requests"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"iam_workload_identity_pool\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
              }]
            }
          }
        },
        {
          width  = 6
          height = 4
          xPos   = 6
          widget = {
            title = "Authentication Failures"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"iam_workload_identity_pool\" AND severity=\"ERROR\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
              }]
            }
          }
        }
      ]
    }
  })
}

# Alert Policy for Authentication Failures
resource "google_monitoring_alert_policy" "auth_failures" {
  count = var.monitoring_config.enable_alerts ? 1 : 0

  project      = var.project_id
  display_name = "Workload Identity Authentication Failures"
  combiner     = "OR"

  conditions {
    display_name = "High Authentication Failure Rate"

    condition_threshold {
      filter          = "resource.type=\"iam_workload_identity_pool\" AND severity=\"ERROR\""
      duration        = "60s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = var.monitoring_config.alert_thresholds.failed_auth_rate

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.monitoring_config.notification_channels

  alert_strategy {
    auto_close = "86400s" # 24 hours
  }
}

# Budget Alert for Cost Monitoring
resource "google_billing_budget" "workload_identity" {
  count = var.cost_optimization.budget_alerts != null && var.cost_optimization.budget_alerts.enabled ? 1 : 0

  billing_account = var.billing_account_id
  display_name    = "Workload Identity Budget - ${var.pool_id}"

  budget_filter {
    projects = ["projects/${var.project_id}"]
    services = ["services/iam.googleapis.com"]

    labels = {
      "workload-identity-pool" = var.pool_id
    }
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(floor(var.cost_optimization.budget_alerts.budget_amount))
      nanos         = floor((var.cost_optimization.budget_alerts.budget_amount - floor(var.cost_optimization.budget_alerts.budget_amount)) * 1000000000)
    }
  }

  threshold_rules {
    threshold_percent = var.cost_optimization.budget_alerts.threshold_percent / 100
    spend_basis       = "CURRENT_SPEND"
  }

  dynamic "all_updates_rule" {
    for_each = length(var.cost_optimization.budget_alerts.notification_emails) > 0 ? [1] : []
    content {
      monitoring_notification_channels = var.monitoring_config.notification_channels
      disable_default_iam_recipients   = false
    }
  }
}

# Cloud Scheduler for Automated Cleanup
resource "google_cloud_scheduler_job" "cleanup" {
  count = var.cost_optimization.automated_cleanup != null && var.cost_optimization.automated_cleanup.enabled ? 1 : 0

  project     = var.project_id
  region      = "us-central1"
  name        = "workload-identity-cleanup-${var.pool_id}"
  description = "Automated cleanup for unused workload identity resources"
  schedule    = var.cost_optimization.automated_cleanup.cleanup_schedule
  time_zone   = "UTC"

  http_target {
    http_method = "POST"
    uri         = "https://cloudfunctions.googleapis.com/v1/projects/${var.project_id}/locations/us-central1/functions/workload-identity-cleanup"

    body = base64encode(jsonencode({
      pool_id                    = var.pool_id
      unused_pool_threshold_days = var.cost_optimization.automated_cleanup.unused_pool_threshold_days
      unused_sa_threshold_days   = var.cost_optimization.automated_cleanup.unused_sa_threshold_days
    }))

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.cleanup[0].email
    }
  }
}

# Service Account for Cleanup Operations
resource "google_service_account" "cleanup" {
  count = var.cost_optimization.automated_cleanup != null && var.cost_optimization.automated_cleanup.enabled ? 1 : 0

  project      = var.project_id
  account_id   = "workload-identity-cleanup"
  display_name = "Workload Identity Cleanup Service Account"
  description  = "Service account for automated cleanup operations"
}

# IAM binding for cleanup service account
resource "google_project_iam_member" "cleanup_permissions" {
  for_each = var.cost_optimization.automated_cleanup != null && var.cost_optimization.automated_cleanup.enabled ? toset([
    "roles/iam.workloadIdentityPoolAdmin",
    "roles/iam.serviceAccountAdmin",
    "roles/monitoring.metricWriter"
  ]) : toset([])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cleanup[0].email}"
}

# Network Security Rules (if VPC native is enabled)
resource "google_compute_firewall" "workload_identity" {
  for_each = {
    for idx, rule in var.advanced_networking.firewall_rules :
    rule.name => rule
    if var.advanced_networking.enable_vpc_native
  }

  project = var.project_id
  name    = "workload-identity-${each.value.name}"
  network = "default"

  direction     = each.value.direction
  source_ranges = each.value.direction == "INGRESS" ? each.value.source_ranges : null
  target_tags   = each.value.target_tags

  dynamic "allow" {
    for_each = each.value.action == "ALLOW" ? [1] : []
    content {
      protocol = "tcp"
      ports    = each.value.ports
    }
  }

  dynamic "deny" {
    for_each = each.value.action == "DENY" ? [1] : []
    content {
      protocol = "tcp"
      ports    = each.value.ports
    }
  }
}

# Additional variables for enterprise features
variable "billing_account_id" {
  description = "Billing account ID for cost monitoring"
  type        = string
  default     = null
}
