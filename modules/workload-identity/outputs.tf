output "pool_name" {
  description = "Full resource name of the workload identity pool"
  value       = google_iam_workload_identity_pool.main.name
}

output "pool_id" {
  description = "The ID of the workload identity pool"
  value       = google_iam_workload_identity_pool.main.workload_identity_pool_id
}

output "pool_state" {
  description = "State of the workload identity pool"
  value       = google_iam_workload_identity_pool.main.state
}

output "providers" {
  description = "Map of provider IDs to their full resource names and details"
  value = {
    for key, provider in google_iam_workload_identity_pool_provider.providers : key => {
      name         = provider.name
      provider_id  = provider.workload_identity_pool_provider_id
      display_name = provider.display_name
      state        = provider.state
      issuer_uri   = try(provider.oidc[0].issuer_uri, null)
    }
  }
}

output "provider_names" {
  description = "Map of provider keys to their full resource names"
  value = {
    for key, provider in google_iam_workload_identity_pool_provider.providers :
    key => provider.name
  }
}

output "service_accounts" {
  description = "Map of service account details"
  value = {
    for key, email in local.service_account_emails : key => {
      email      = email
      member     = "serviceAccount:${email}"
      project_id = var.project_id
    }
  }
}

output "subject_format" {
  description = "Format for constructing the subject claim for different providers"
  value = {
    github = {
      repo_subject        = "repo:ORG/REPO:ref:refs/heads/BRANCH"
      environment_subject = "repo:ORG/REPO:environment:ENV_NAME"
      pull_request       = "repo:ORG/REPO:pull_request"
      tag                = "repo:ORG/REPO:ref:refs/tags/TAG_NAME"
    }
    gitlab = {
      project_subject     = "project_path:GROUP/PROJECT:ref_type:branch:ref:BRANCH"
      environment_subject = "project_path:GROUP/PROJECT:environment:ENV_NAME"
      group_subject      = "group_path:GROUP:ref_type:branch:ref:BRANCH"
    }
    azure_devops = {
      build_subject = "sc:ORG:projectId:PROJECT:definitionId:PIPELINE_ID"
    }
    terraform_cloud = {
      workspace_subject = "organization:ORG:project:PROJECT:workspace:WORKSPACE:run_phase:PHASE"
    }
  }
}

output "token_lifetime" {
  description = "Token lifetime configuration"
  value       = var.session_duration
}

output "authentication_config" {
  description = "Configuration details for authenticating from different CI/CD platforms"
  value = {
    for key, provider in var.providers : key => {
      project_number = data.google_project.current.number
      pool_id        = google_iam_workload_identity_pool.main.workload_identity_pool_id
      provider_id    = provider.provider_id

      # Platform-specific configuration instructions
      github_actions = provider.github != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        example_workflow = <<-EOT
          - uses: 'google-github-actions/auth@v2'
            with:
              workload_identity_provider: 'projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}'
              service_account: 'SERVICE_ACCOUNT_EMAIL'
        EOT
      } : null

      gitlab_ci = provider.gitlab != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        example_job = <<-EOT
          authenticate:
            image: google/cloud-sdk:alpine
            script:
              - echo $${CI_JOB_JWT_V2} > .ci_job_jwt_file
              - gcloud iam workload-identity-pools create-cred-config
                  projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}
                  --service-account=SERVICE_ACCOUNT_EMAIL
                  --credential-source-file=.ci_job_jwt_file
                  --output-file=.gcp_credentials.json
              - export GOOGLE_APPLICATION_CREDENTIALS=.gcp_credentials.json
        EOT
      } : null

      azure_devops = provider.azure_devops != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        example_task = <<-EOT
          - task: GoogleCloudSdkAuthentication@0
            inputs:
              authenticationType: 'workloadIdentityFederation'
              workloadIdentityProvider: 'projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}'
              serviceAccountEmail: 'SERVICE_ACCOUNT_EMAIL'
        EOT
      } : null

      terraform_cloud = provider.terraform_cloud != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        env_variables = {
          TFC_GCP_PROVIDER_AUTH                = "true"
          TFC_GCP_WORKLOAD_IDENTITY_POOL_ID    = var.pool_id
          TFC_GCP_WORKLOAD_PROVIDER_ID         = provider.provider_id
          TFC_GCP_SERVICE_ACCOUNT_EMAIL        = "SERVICE_ACCOUNT_EMAIL"
          TFC_GCP_PROJECT_NUMBER                = data.google_project.current.number
        }
      } : null

      jenkins = provider.jenkins != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        example_pipeline = <<-EOT
          pipeline {
              agent any
              environment {
                  GOOGLE_APPLICATION_CREDENTIALS = credentials('gcp-workload-identity')
              }
              stages {
                  stage('Authenticate') {
                      steps {
                          script {
                              sh '''
                                  gcloud iam workload-identity-pools create-cred-config \
                                      projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id} \
                                      --service-account=SERVICE_ACCOUNT_EMAIL \
                                      --credential-source-file=$JENKINS_JWT_FILE \
                                      --output-file=.gcp_credentials.json
                                  export GOOGLE_APPLICATION_CREDENTIALS=.gcp_credentials.json
                              '''
                          }
                      }
                  }
              }
          }
        EOT
      } : null

      circleci = provider.circleci != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        example_config = <<-EOT
          version: 2.1
          jobs:
            authenticate:
              docker:
                - image: google/cloud-sdk:alpine
              steps:
                - run:
                    name: Authenticate with Google Cloud
                    command: |
                      echo $CIRCLE_OIDC_TOKEN > .circle_token
                      gcloud iam workload-identity-pools create-cred-config \
                          projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id} \
                          --service-account=SERVICE_ACCOUNT_EMAIL \
                          --credential-source-file=.circle_token \
                          --output-file=.gcp_credentials.json
                      export GOOGLE_APPLICATION_CREDENTIALS=.gcp_credentials.json
        EOT
      } : null

      bitbucket = provider.bitbucket != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        example_pipeline = <<-EOT
          pipelines:
            default:
              - step:
                  name: Authenticate with Google Cloud
                  image: google/cloud-sdk:alpine
                  script:
                    - echo $BITBUCKET_STEP_OIDC_TOKEN > .bitbucket_token
                    - gcloud iam workload-identity-pools create-cred-config
                        projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}
                        --service-account=SERVICE_ACCOUNT_EMAIL
                        --credential-source-file=.bitbucket_token
                        --output-file=.gcp_credentials.json
                    - export GOOGLE_APPLICATION_CREDENTIALS=.gcp_credentials.json
        EOT
      } : null

      spinnaker = provider.spinnaker != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        example_stage = <<-EOT
          {
            "type": "script",
            "name": "Authenticate with GCP",
            "command": [
              "gcloud iam workload-identity-pools create-cred-config",
              "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}",
              "--service-account=SERVICE_ACCOUNT_EMAIL",
              "--credential-source-file=$SPINNAKER_JWT_FILE",
              "--output-file=.gcp_credentials.json"
            ]
          }
        EOT
      } : null

      harness = provider.harness != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        example_step = <<-EOT
          - step:
              type: Run
              name: Authenticate with GCP
              identifier: gcp_auth
              spec:
                shell: Bash
                command: |
                  echo $HARNESS_OIDC_JWT > .harness_token
                  gcloud iam workload-identity-pools create-cred-config \
                      projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id} \
                      --service-account=SERVICE_ACCOUNT_EMAIL \
                      --credential-source-file=.harness_token \
                      --output-file=.gcp_credentials.json
                  export GOOGLE_APPLICATION_CREDENTIALS=.gcp_credentials.json
        EOT
      } : null

      aws_codebuild = provider.aws_codebuild != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        example_buildspec = <<-EOT
          version: 0.2
          phases:
            pre_build:
              commands:
                - echo $AWS_WEB_IDENTITY_TOKEN > .aws_token
                - gcloud iam workload-identity-pools create-cred-config
                    projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}
                    --service-account=SERVICE_ACCOUNT_EMAIL
                    --credential-source-file=.aws_token
                    --output-file=.gcp_credentials.json
                - export GOOGLE_APPLICATION_CREDENTIALS=.gcp_credentials.json
            build:
              commands:
                - echo "Now authenticated with Google Cloud"
        EOT
      } : null

      custom_oidc = provider.custom_oidc != null ? {
        workload_identity_provider = "projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${provider.provider_id}"
        issuer_uri = provider.custom_oidc.issuer_uri
        audience = provider.custom_oidc.audience
        subject_format = provider.custom_oidc.subject_format
      } : null
    }
  }
}

# Enhanced outputs for multi-platform support
output "platform_support" {
  description = "Supported CI/CD platforms and their configuration status"
  value = {
    github_actions    = length([for k, v in var.providers : k if v.github != null]) > 0
    gitlab_ci        = length([for k, v in var.providers : k if v.gitlab != null]) > 0
    azure_devops     = length([for k, v in var.providers : k if v.azure_devops != null]) > 0
    terraform_cloud  = length([for k, v in var.providers : k if v.terraform_cloud != null]) > 0
    jenkins          = length([for k, v in var.providers : k if v.jenkins != null]) > 0
    circleci         = length([for k, v in var.providers : k if v.circleci != null]) > 0
    bitbucket        = length([for k, v in var.providers : k if v.bitbucket != null]) > 0
    spinnaker        = length([for k, v in var.providers : k if v.spinnaker != null]) > 0
    harness          = length([for k, v in var.providers : k if v.harness != null]) > 0
    aws_codebuild    = length([for k, v in var.providers : k if v.aws_codebuild != null]) > 0
    custom_oidc      = length([for k, v in var.providers : k if v.custom_oidc != null]) > 0
  }
}

output "enterprise_features" {
  description = "Enterprise features configuration status"
  value = {
    audit_logging = {
      enabled = var.enable_audit_logging
      sink_name = var.enable_audit_logging ? var.audit_log_config.log_sink_name : null
      destination_type = var.enable_audit_logging ? var.audit_log_config.destination_type : null
    }

    monitoring = {
      metrics_enabled = var.monitoring_config.enable_metrics
      alerts_enabled = var.monitoring_config.enable_alerts
      dashboard_created = var.monitoring_config.enable_metrics
      notification_channels = length(var.monitoring_config.notification_channels)
    }

    security_policies = {
      mfa_required = var.security_policies.require_mfa
      ip_restrictions = length(var.security_policies.allowed_ip_ranges) > 0 || length(var.security_policies.denied_ip_ranges) > 0
      session_duration = var.security_policies.max_session_duration
      corporate_device_required = var.security_policies.require_corporate_device
    }

    compliance = {
      sox_enabled = var.compliance_framework.enable_sox_compliance
      pci_enabled = var.compliance_framework.enable_pci_compliance
      hipaa_enabled = var.compliance_framework.enable_hipaa_compliance
      gdpr_enabled = var.compliance_framework.enable_gdpr_compliance
      iso27001_enabled = var.compliance_framework.enable_iso27001
      data_encryption = var.compliance_framework.enable_data_encryption
    }

    cost_optimization = {
      budget_alerts = var.cost_optimization.budget_alerts != null ? var.cost_optimization.budget_alerts.enabled : false
      automated_cleanup = var.cost_optimization.automated_cleanup != null ? var.cost_optimization.automated_cleanup.enabled : false
      cost_tracking = var.cost_optimization.enable_cost_tracking
    }

    federation_settings = {
      cross_project_access = var.federation_settings.enable_cross_project_access
      delegation_enabled = var.federation_settings.enable_delegation
      token_caching = var.federation_settings.enable_token_caching
      batch_operations = var.federation_settings.enable_batch_operations
    }

    backup_recovery = {
      backup_enabled = var.backup_and_recovery.enable_backup
      cross_region_backup = var.backup_and_recovery.enable_cross_region_backup
      automated_recovery = var.backup_and_recovery.enable_automated_recovery
      rpo_minutes = var.backup_and_recovery.recovery_rpo_minutes
      rto_minutes = var.backup_and_recovery.recovery_rto_minutes
    }
  }
}

output "integration_status" {
  description = "Third-party integration status"
  value = {
    vault_integration = var.integration_settings.vault_integration != null ? var.integration_settings.vault_integration.enabled : false
    okta_integration = var.integration_settings.okta_integration != null ? var.integration_settings.okta_integration.enabled : false
    active_directory_integration = var.integration_settings.active_directory_integration != null ? var.integration_settings.active_directory_integration.enabled : false
    splunk_integration = var.integration_settings.splunk_integration != null ? var.integration_settings.splunk_integration.enabled : false
    slack_integration = var.integration_settings.slack_integration != null ? var.integration_settings.slack_integration.enabled : false
    pagerduty_integration = var.integration_settings.pagerduty_integration != null ? var.integration_settings.pagerduty_integration.enabled : false
  }
}

output "network_security" {
  description = "Network security configuration"
  value = {
    vpc_native_enabled = var.advanced_networking.enable_vpc_native
    private_google_access = var.advanced_networking.enable_private_google_access
    allowed_networks = length(var.advanced_networking.allowed_vpc_networks)
    firewall_rules = length(var.advanced_networking.firewall_rules)
    custom_routes = length(var.advanced_networking.custom_routes)
  }
}

output "workload_identity_summary" {
  description = "Comprehensive summary of the workload identity configuration"
  value = {
    pool_configuration = {
      pool_id = var.pool_id
      pool_name = google_iam_workload_identity_pool.main.name
      project_id = var.project_id
      project_number = data.google_project.current.number
      disabled = var.pool_disabled
      session_duration = var.session_duration
    }

    providers_summary = {
      total_providers = length(var.providers)
      provider_types = [for k, v in var.providers : (
        v.github != null ? "github" :
        v.gitlab != null ? "gitlab" :
        v.azure_devops != null ? "azure_devops" :
        v.terraform_cloud != null ? "terraform_cloud" :
        v.jenkins != null ? "jenkins" :
        v.circleci != null ? "circleci" :
        v.bitbucket != null ? "bitbucket" :
        v.spinnaker != null ? "spinnaker" :
        v.harness != null ? "harness" :
        v.aws_codebuild != null ? "aws_codebuild" :
        v.custom_oidc != null ? "custom_oidc" : "unknown"
      )]
      attribute_conditions_enabled = var.enable_attribute_conditions
    }

    service_accounts_summary = {
      total_service_accounts = length(var.service_accounts)
      created_accounts = length([for k, v in var.service_accounts : k if v.create_new])
      existing_accounts = length([for k, v in var.service_accounts : k if !v.create_new])
      total_bindings = length(local.binding_keys)
    }

    security_summary = {
      audit_logging_enabled = var.enable_audit_logging
      monitoring_enabled = var.monitoring_config.enable_metrics
      alerts_configured = var.monitoring_config.enable_alerts
      compliance_frameworks = length([for k, v in var.compliance_framework : k if v == true])
      ip_restrictions_configured = length(var.security_policies.allowed_ip_ranges) > 0 || length(var.security_policies.denied_ip_ranges) > 0
    }

    cost_management = {
      budget_monitoring = var.cost_optimization.budget_alerts != null ? var.cost_optimization.budget_alerts.enabled : false
      automated_cleanup = var.cost_optimization.automated_cleanup != null ? var.cost_optimization.automated_cleanup.enabled : false
      resource_quotas_defined = var.cost_optimization.resource_quotas != null
    }

    integration_summary = {
      external_integrations = length([
        for k, v in var.integration_settings : k
        if v != null && try(v.enabled, false) == true
      ])
      vault_connected = var.integration_settings.vault_integration != null ? var.integration_settings.vault_integration.enabled : false
      siem_connected = var.integration_settings.splunk_integration != null ? var.integration_settings.splunk_integration.enabled : false
    }
  }
}

# Data source to get project details
data "google_project" "current" {
  project_id = var.project_id
}