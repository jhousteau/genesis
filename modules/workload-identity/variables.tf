variable "project_id" {
  description = "GCP project ID where the workload identity pool will be created"
  type        = string
}

variable "pool_id" {
  description = "Workload identity pool ID (must be 4-32 characters)"
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{3,31}$", var.pool_id))
    error_message = "Pool ID must be 4-32 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "pool_display_name" {
  description = "Display name for the workload identity pool"
  type        = string
  default     = ""
}

variable "pool_description" {
  description = "Description of the workload identity pool"
  type        = string
  default     = "Workload Identity Pool for CI/CD authentication"
}

variable "pool_disabled" {
  description = "Whether the pool is disabled"
  type        = bool
  default     = false
}

variable "providers" {
  description = "Map of identity providers to configure"
  type = map(object({
    provider_id    = string
    display_name   = optional(string)
    description    = optional(string)
    disabled       = optional(bool, false)
    issuer_uri     = optional(string)
    jwks_json      = optional(string)
    allowed_audiences = optional(list(string), [])

    # Attribute mapping
    attribute_mapping = optional(map(string), {})

    # Attribute conditions for fine-grained access control
    attribute_condition = optional(string)

    # Provider-specific configurations
    github = optional(object({
      organization = optional(string)
      repositories = optional(list(string))
      environments = optional(list(string))
      branches     = optional(list(string))
    }))

    gitlab = optional(object({
      project_path = optional(string)
      group_path   = optional(string)
      branches     = optional(list(string))
      environments = optional(list(string))
    }))

    azure_devops = optional(object({
      organization = optional(string)
      project      = optional(string)
      branches     = optional(list(string))
    }))

    terraform_cloud = optional(object({
      organization = optional(string)
      project      = optional(string)
      workspace    = optional(string)
      run_phase    = optional(string)
    }))

    # Jenkins CI/CD platform
    jenkins = optional(object({
      jenkins_url      = optional(string)
      build_number     = optional(string)
      job_name         = optional(string)
      node_name        = optional(string)
      user_id          = optional(string)
      build_url        = optional(string)
      workspace        = optional(string)
      git_branch       = optional(string)
      git_commit       = optional(string)
    }))

    # CircleCI platform
    circleci = optional(object({
      organization = optional(string)
      project_id   = optional(string)
      branch       = optional(string)
      vcs_type     = optional(string) # github or bitbucket
      repository   = optional(string)
    }))

    # Bitbucket Pipelines
    bitbucket = optional(object({
      workspace   = optional(string)
      repository  = optional(string)
      branch      = optional(string)
      build_number = optional(string)
      pipeline_uuid = optional(string)
    }))

    # Spinnaker deployment platform
    spinnaker = optional(object({
      application   = optional(string)
      pipeline_name = optional(string)
      execution_id  = optional(string)
      stage_name    = optional(string)
      account       = optional(string)
    }))

    # Harness deployment platform
    harness = optional(object({
      account_id      = optional(string)
      organization_id = optional(string)
      project_id      = optional(string)
      pipeline_id     = optional(string)
      service_id      = optional(string)
      environment_id  = optional(string)
    }))

    # AWS CodeBuild (for hybrid cloud scenarios)
    aws_codebuild = optional(object({
      aws_account_id = optional(string)
      aws_region     = optional(string)
      project_name   = optional(string)
      build_id       = optional(string)
      source_repo    = optional(string)
      branch         = optional(string)
    }))

    # Custom OIDC provider
    custom_oidc = optional(object({
      issuer_uri       = string
      audience         = optional(list(string), [])
      subject_format   = optional(string)
      claims_mapping   = optional(map(string), {})
      allowed_claims   = optional(map(list(string)), {})
    }))
  }))
  default = {}
}

variable "service_accounts" {
  description = "Map of service accounts to bind with workload identity"
  type = map(object({
    service_account_id   = string
    display_name        = optional(string)
    description         = optional(string)
    create_new          = optional(bool, true)
    existing_email      = optional(string)

    # IAM bindings
    project_roles = optional(list(string), [])

    # Workload identity bindings
    bindings = list(object({
      provider_id         = string
      attribute_condition = optional(string)
      roles              = optional(list(string), ["roles/iam.workloadIdentityUser"])
    }))
  }))
  default = {}
}

variable "enable_attribute_conditions" {
  description = "Enable attribute-based access control conditions"
  type        = bool
  default     = true
}

variable "session_duration" {
  description = "Duration for which the access token is valid (in seconds)"
  type        = string
  default     = "3600s"
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}

# Enhanced Security and Enterprise Features
variable "enable_audit_logging" {
  description = "Enable comprehensive audit logging for workload identity operations"
  type        = bool
  default     = true
}

variable "audit_log_config" {
  description = "Audit logging configuration"
  type = object({
    log_sink_name           = optional(string, "workload-identity-audit")
    destination_type        = optional(string, "bigquery") # bigquery, cloud_logging, pubsub, cloud_storage
    bigquery_dataset        = optional(string)
    pubsub_topic           = optional(string)
    cloud_storage_bucket   = optional(string)
    include_children       = optional(bool, true)
    filter_expression      = optional(string)
  })
  default = {
    destination_type = "cloud_logging"
  }
}

variable "security_policies" {
  description = "Advanced security policies for workload identity"
  type = object({
    require_mfa                    = optional(bool, false)
    max_session_duration          = optional(string, "3600s")
    allowed_ip_ranges             = optional(list(string), [])
    denied_ip_ranges              = optional(list(string), [])
    require_verified_email        = optional(bool, false)
    require_corporate_device      = optional(bool, false)
    session_affinity_timeout      = optional(string, "300s")
    enable_access_transparency    = optional(bool, false)
    enable_privileged_access      = optional(bool, false)
  })
  default = {}
}

variable "compliance_framework" {
  description = "Compliance framework configuration"
  type = object({
    enable_sox_compliance     = optional(bool, false)
    enable_pci_compliance     = optional(bool, false)
    enable_hipaa_compliance   = optional(bool, false)
    enable_gdpr_compliance    = optional(bool, false)
    enable_iso27001          = optional(bool, false)
    data_residency_regions   = optional(list(string), [])
    retention_policy_days    = optional(number, 90)
    enable_data_encryption   = optional(bool, true)
  })
  default = {}
}

variable "monitoring_config" {
  description = "Monitoring and alerting configuration"
  type = object({
    enable_metrics           = optional(bool, true)
    enable_alerts           = optional(bool, true)
    notification_channels   = optional(list(string), [])
    alert_thresholds = optional(object({
      failed_auth_rate      = optional(number, 5)   # failures per minute
      unusual_access_count  = optional(number, 10)  # access attempts from new locations
      token_usage_spike     = optional(number, 100) # tokens issued per minute
    }), {})
    metrics_retention_days = optional(number, 30)
  })
  default = {}
}

variable "federation_settings" {
  description = "Advanced federation settings"
  type = object({
    enable_cross_project_access   = optional(bool, false)
    allowed_projects             = optional(list(string), [])
    enable_delegation            = optional(bool, false)
    delegation_timeout           = optional(string, "3600s")
    enable_token_caching         = optional(bool, true)
    cache_duration              = optional(string, "300s")
    enable_batch_operations     = optional(bool, false)
  })
  default = {}
}

variable "backup_and_recovery" {
  description = "Backup and disaster recovery configuration"
  type = object({
    enable_backup              = optional(bool, true)
    backup_frequency          = optional(string, "daily") # daily, weekly, monthly
    backup_retention_days     = optional(number, 30)
    enable_cross_region_backup = optional(bool, false)
    backup_regions            = optional(list(string), [])
    enable_automated_recovery = optional(bool, false)
    recovery_rpo_minutes      = optional(number, 60) # Recovery Point Objective
    recovery_rto_minutes      = optional(number, 30) # Recovery Time Objective
  })
  default = {}
}

variable "integration_settings" {
  description = "Third-party integration settings"
  type = object({
    # Secret management integrations
    vault_integration = optional(object({
      enabled        = bool
      vault_addr     = string
      auth_method    = optional(string, "gcp")
      role           = optional(string)
      secret_path    = optional(string)
    }))

    # External identity providers
    okta_integration = optional(object({
      enabled     = bool
      domain      = string
      client_id   = string
      api_token   = optional(string)
    }))

    active_directory_integration = optional(object({
      enabled           = bool
      domain            = string
      ldap_server       = string
      service_account   = string
    }))

    # SIEM integrations
    splunk_integration = optional(object({
      enabled      = bool
      endpoint     = string
      index        = optional(string, "main")
      source_type  = optional(string, "gcp:workload_identity")
    }))

    # Notification integrations
    slack_integration = optional(object({
      enabled      = bool
      webhook_url  = string
      channel      = optional(string, "#security")
    }))

    pagerduty_integration = optional(object({
      enabled        = bool
      service_key    = string
      escalation_policy = optional(string)
    }))
  })
  default = {}
}

variable "advanced_networking" {
  description = "Advanced networking configuration for workload identity"
  type = object({
    enable_vpc_native           = optional(bool, true)
    allowed_vpc_networks        = optional(list(string), [])
    enable_private_google_access = optional(bool, true)
    custom_routes              = optional(list(object({
      name         = string
      dest_range   = string
      next_hop_ip  = string
      priority     = optional(number, 1000)
    })), [])
    firewall_rules = optional(list(object({
      name           = string
      direction      = string # INGRESS or EGRESS
      action         = string # ALLOW or DENY
      source_ranges  = optional(list(string), [])
      target_tags    = optional(list(string), [])
      ports          = optional(list(string), [])
      protocols      = optional(list(string), ["tcp"])
    })), [])
  })
  default = {}
}

variable "cost_optimization" {
  description = "Cost optimization settings"
  type = object({
    enable_cost_tracking      = optional(bool, true)
    budget_alerts            = optional(object({
      enabled           = bool
      budget_amount     = number
      threshold_percent = optional(number, 80)
      notification_emails = optional(list(string), [])
    }))
    resource_quotas = optional(object({
      max_pools                = optional(number, 10)
      max_providers_per_pool   = optional(number, 20)
      max_service_accounts     = optional(number, 100)
      token_request_rate_limit = optional(number, 1000) # per minute
    }))
    automated_cleanup = optional(object({
      enabled                    = bool
      unused_pool_threshold_days = optional(number, 30)
      unused_sa_threshold_days   = optional(number, 60)
      cleanup_schedule           = optional(string, "0 2 * * 0") # Weekly Sunday 2 AM
    }))
  })
  default = {}
}