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
    }
  }
}

# Data source to get project details
data "google_project" "current" {
  project_id = var.project_id
}