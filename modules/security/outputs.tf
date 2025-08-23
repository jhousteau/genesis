/**
 * Security Module Outputs
 *
 * Comprehensive outputs for all security infrastructure resources
 */

# KMS Outputs
output "kms_key_rings" {
  description = "KMS key rings information"
  value = {
    for ring_name, ring in google_kms_key_ring.key_rings : ring_name => {
      id        = ring.id
      name      = ring.name
      location  = ring.location
      self_link = ring.self_link
    }
  }
}

output "kms_crypto_keys" {
  description = "KMS crypto keys information"
  value = {
    for key_name, key in google_kms_crypto_key.keys : key_name => {
      id               = key.id
      name             = key.name
      key_ring         = key.key_ring
      purpose          = key.purpose
      rotation_period  = key.rotation_period
      self_link        = key.self_link
      version_template = key.version_template
    }
  }
}

output "kms_key_ring_map" {
  description = "Map of key ring names to their IDs"
  value = {
    for ring_name, ring in google_kms_key_ring.key_rings : ring_name => ring.id
  }
}

output "kms_crypto_key_map" {
  description = "Map of crypto key names to their IDs"
  value = {
    for key_name, key in google_kms_crypto_key.keys : key_name => key.id
  }
}

# Secret Manager Outputs
output "secrets" {
  description = "Secret Manager secrets information"
  value = {
    for secret_name, secret in google_secret_manager_secret.secrets : secret_name => {
      id          = secret.id
      name        = secret.name
      secret_id   = secret.secret_id
      project     = secret.project
      labels      = secret.labels
      annotations = secret.annotations
      topics      = secret.topics
      replication = secret.replication
      create_time = secret.create_time
    }
  }
  sensitive = true
}

output "secret_versions" {
  description = "Secret Manager secret versions information"
  value = {
    for secret_name, version in google_secret_manager_secret_version.secret_versions : secret_name => {
      id          = version.id
      name        = version.name
      secret      = version.secret
      enabled     = version.enabled
      version     = version.version
      create_time = version.create_time
    }
  }
  sensitive = true
}

output "secret_map" {
  description = "Map of secret names to their IDs"
  value = {
    for secret_name, secret in google_secret_manager_secret.secrets : secret_name => secret.id
  }
}

# Custom IAM Roles Outputs
output "custom_iam_roles" {
  description = "Custom IAM roles information"
  value = {
    project_roles = {
      for role_id, role in google_project_iam_custom_role.custom_roles : role_id => {
        id          = role.id
        name        = role.name
        title       = role.title
        description = role.description
        permissions = role.permissions
        stage       = role.stage
        deleted     = role.deleted
      }
    }
    organization_roles = {
      for role_id, role in google_organization_iam_custom_role.org_custom_roles : role_id => {
        id          = role.id
        name        = role.name
        title       = role.title
        description = role.description
        permissions = role.permissions
        stage       = role.stage
        deleted     = role.deleted
      }
    }
  }
}

output "custom_role_map" {
  description = "Map of custom role IDs to their names"
  value = merge(
    {
      for role_id, role in google_project_iam_custom_role.custom_roles : role_id => role.name
    },
    {
      for role_id, role in google_organization_iam_custom_role.org_custom_roles : role_id => role.name
    }
  )
}

# Conditional IAM Bindings Outputs
output "conditional_iam_bindings" {
  description = "Conditional IAM bindings information"
  value = {
    for binding_key, binding in google_project_iam_binding.conditional_bindings : binding_key => {
      id        = binding.id
      project   = binding.project
      role      = binding.role
      members   = binding.members
      condition = binding.condition
      etag      = binding.etag
    }
  }
}

# Security Command Center Outputs
output "security_center_sources" {
  description = "Security Command Center sources information"
  value = {
    for source_name, source in google_scc_source.sources : source_name => {
      id           = source.id
      name         = source.name
      display_name = source.display_name
      description  = source.description
      organization = source.organization
    }
  }
}

output "security_center_notifications" {
  description = "Security Command Center notification configurations"
  value = {
    for config_id, notification in google_scc_notification_config.notifications : config_id => {
      id               = notification.id
      name             = notification.name
      config_id        = notification.config_id
      organization     = notification.organization
      description      = notification.description
      pubsub_topic     = notification.pubsub_topic
      streaming_config = notification.streaming_config
      service_account  = notification.service_account
    }
  }
}

# Binary Authorization Outputs
output "binary_authorization_policy" {
  description = "Binary Authorization policy information"
  value = var.binary_authorization.enabled ? {
    id                            = google_binary_authorization_policy.policy[0].id
    project                       = google_binary_authorization_policy.policy[0].project
    default_admission_rule        = google_binary_authorization_policy.policy[0].default_admission_rule
    admission_whitelist_patterns  = google_binary_authorization_policy.policy[0].admission_whitelist_patterns
    global_policy_evaluation_mode = google_binary_authorization_policy.policy[0].global_policy_evaluation_mode
  } : null
}

output "binary_authorization_attestors" {
  description = "Binary Authorization attestors information"
  value = {
    for attestor_name, attestor in google_binary_authorization_attestor.attestors : attestor_name => {
      id                         = attestor.id
      name                       = attestor.name
      description                = attestor.description
      project                    = attestor.project
      attestation_authority_note = attestor.attestation_authority_note
    }
  }
}

# Security Policies (Cloud Armor) Outputs
output "security_policies" {
  description = "Cloud Armor security policies information"
  value = {
    for policy_name, policy in google_compute_security_policy.policies : policy_name => {
      id                         = policy.id
      name                       = policy.name
      description                = policy.description
      project                    = policy.project
      type                       = policy.type
      self_link                  = policy.self_link
      fingerprint                = policy.fingerprint
      adaptive_protection_config = policy.adaptive_protection_config
      advanced_options_config    = policy.advanced_options_config
      recaptcha_options_config   = policy.recaptcha_options_config
      rule                       = policy.rule
    }
  }
}

output "security_policy_map" {
  description = "Map of security policy names to their IDs"
  value = {
    for policy_name, policy in google_compute_security_policy.policies : policy_name => policy.id
  }
}

# Web Security Scanner Outputs
output "web_security_scanner_configs" {
  description = "Web Security Scanner scan configurations"
  value = var.web_security_scanner.enabled ? {
    for config_name, config in google_security_scanner_scan_config.scan_configs : config_name => {
      id                                = config.id
      name                              = config.name
      display_name                      = config.display_name
      starting_urls                     = config.starting_urls
      project                           = config.project
      max_qps                           = config.max_qps
      user_agent                        = config.user_agent
      blacklist_patterns                = config.blacklist_patterns
      schedule                          = config.schedule
      authentication                    = config.authentication
      export_to_security_command_center = config.export_to_security_command_center
    }
  } : {}
}

# VPC Security Controls Outputs
output "access_levels" {
  description = "VPC Security Controls access levels information"
  value = var.vpc_security_controls.enabled ? {
    for level_name, level in google_access_context_manager_access_level.access_levels : level_name => {
      id          = level.id
      name        = level.name
      title       = level.title
      description = level.description
      parent      = level.parent
      basic       = level.basic
      custom      = level.custom
    }
  } : {}
}

output "service_perimeters" {
  description = "VPC Security Controls service perimeters information"
  value = var.vpc_security_controls.enabled ? {
    for perimeter_name, perimeter in google_access_context_manager_service_perimeter.perimeters : perimeter_name => {
      id             = perimeter.id
      name           = perimeter.name
      title          = perimeter.title
      description    = perimeter.description
      parent         = perimeter.parent
      perimeter_type = perimeter.perimeter_type
      status         = perimeter.status
      spec           = perimeter.spec
      create_time    = perimeter.create_time
      update_time    = perimeter.update_time
    }
  } : {}
}

# Data Loss Prevention Outputs
output "dlp_inspect_templates" {
  description = "DLP inspect templates information"
  value = var.dlp_config.enabled ? {
    for template_name, template in google_data_loss_prevention_inspect_template.inspect_templates : template_name => {
      id             = template.id
      name           = template.name
      parent         = template.parent
      description    = template.description
      display_name   = template.display_name
      inspect_config = template.inspect_config
      create_time    = template.create_time
      update_time    = template.update_time
    }
  } : {}
}

output "dlp_job_triggers" {
  description = "DLP job triggers information"
  value = var.dlp_config.enabled ? {
    for trigger_name, trigger in google_data_loss_prevention_job_trigger.job_triggers : trigger_name => {
      id            = trigger.id
      name          = trigger.name
      parent        = trigger.parent
      description   = trigger.description
      display_name  = trigger.display_name
      status        = trigger.status
      triggers      = trigger.triggers
      inspect_job   = trigger.inspect_job
      create_time   = trigger.create_time
      update_time   = trigger.update_time
      last_run_time = trigger.last_run_time
    }
  } : {}
}

# Comprehensive Security Summary
output "security_summary" {
  description = "Comprehensive security infrastructure summary"
  value = {
    project_id      = var.project_id
    organization_id = var.organization_id
    name_prefix     = var.name_prefix
    environment     = var.environment

    # Component status
    components = {
      kms = {
        enabled     = length(var.kms_key_rings) > 0
        key_rings   = length(google_kms_key_ring.key_rings)
        crypto_keys = length(google_kms_crypto_key.keys)
      }

      secret_manager = {
        enabled  = length(var.secrets) > 0
        secrets  = length(google_secret_manager_secret.secrets)
        versions = length(google_secret_manager_secret_version.secret_versions)
      }

      iam = {
        custom_roles         = length(google_project_iam_custom_role.custom_roles) + length(google_organization_iam_custom_role.org_custom_roles)
        conditional_bindings = length(google_project_iam_binding.conditional_bindings)
      }

      security_center = {
        enabled       = var.organization_id != null
        sources       = length(google_scc_source.sources)
        notifications = length(google_scc_notification_config.notifications)
      }

      binary_authorization = {
        enabled           = var.binary_authorization.enabled
        attestors         = length(google_binary_authorization_attestor.attestors)
        policy_configured = var.binary_authorization.enabled
      }

      cloud_armor = {
        enabled  = length(var.security_policies) > 0
        policies = length(google_compute_security_policy.policies)
      }

      web_security_scanner = {
        enabled      = var.web_security_scanner.enabled
        scan_configs = length(google_security_scanner_scan_config.scan_configs)
      }

      vpc_security_controls = {
        enabled            = var.vpc_security_controls.enabled
        access_levels      = length(google_access_context_manager_access_level.access_levels)
        service_perimeters = length(google_access_context_manager_service_perimeter.perimeters)
      }

      dlp = {
        enabled           = var.dlp_config.enabled
        inspect_templates = length(google_data_loss_prevention_inspect_template.inspect_templates)
        job_triggers      = length(google_data_loss_prevention_job_trigger.job_triggers)
      }
    }

    # Security baseline status
    security_baseline = {
      enabled                        = var.security_baseline.enabled
      cis_benchmarks                 = var.security_baseline.cis_benchmarks
      nist_framework                 = var.security_baseline.nist_framework
      iso_27001                      = var.security_baseline.iso_27001
      encryption_at_rest_required    = var.security_baseline.encryption_at_rest_required
      encryption_in_transit_required = var.security_baseline.encryption_in_transit_required
      mfa_required                   = var.security_baseline.mfa_required
    }

    # Monitoring and alerts
    monitoring = {
      security_monitoring   = var.enable_security_monitoring
      compliance_automation = var.enable_compliance_automation
      notifications_enabled = var.security_notifications.enabled
      threat_detection      = var.threat_detection.enabled
      incident_response     = var.incident_response.enabled
    }

    # Regional deployment
    regions = {
      default_region = var.default_region
      multi_region_kms = length([
        for ring in var.kms_key_rings : ring
        if length([for key in ring.keys : key if contains(["GLOBAL", "EUROPE", "US", "ASIA"], lookup(ring, "location", var.default_region))]) > 0
      ]) > 0
      multi_region_secrets = length([
        for secret in var.secrets : secret
        if secret.replication_policy == "user_managed" && length(secret.replica_locations) > 1
      ]) > 0
    }

    # Compliance framework alignment
    compliance = {
      frameworks_enabled = compact([
        var.security_baseline.cis_benchmarks ? "CIS" : "",
        var.security_baseline.nist_framework ? "NIST" : "",
        var.security_baseline.iso_27001 ? "ISO_27001" : ""
      ])
      encryption_compliance     = var.security_baseline.encryption_at_rest_required && var.security_baseline.encryption_in_transit_required
      access_control_compliance = var.security_baseline.mfa_required
      audit_compliance          = var.enable_security_monitoring && var.enable_compliance_automation
    }

    # Resource counts
    resource_counts = {
      total_kms_resources     = length(google_kms_key_ring.key_rings) + length(google_kms_crypto_key.keys)
      total_secret_resources  = length(google_secret_manager_secret.secrets) + length(google_secret_manager_secret_version.secret_versions)
      total_iam_resources     = length(google_project_iam_custom_role.custom_roles) + length(google_organization_iam_custom_role.org_custom_roles) + length(google_project_iam_binding.conditional_bindings)
      total_security_policies = length(google_compute_security_policy.policies)
      total_dlp_resources     = length(google_data_loss_prevention_inspect_template.inspect_templates) + length(google_data_loss_prevention_job_trigger.job_triggers)
      total_vpc_controls      = length(google_access_context_manager_access_level.access_levels) + length(google_access_context_manager_service_perimeter.perimeters)
    }
  }
}

# Security Integration Outputs
output "integration_endpoints" {
  description = "Security service integration endpoints and configurations"
  value = {
    kms_integration = {
      crypto_key_ids     = [for key in google_kms_crypto_key.keys : key.id]
      key_ring_locations = distinct([for ring in google_kms_key_ring.key_rings : ring.location])
    }

    secret_manager_integration = {
      secret_ids   = [for secret in google_secret_manager_secret.secrets : secret.id]
      secret_names = [for secret in google_secret_manager_secret.secrets : secret.name]
    }

    security_center_integration = {
      source_names       = [for source in google_scc_source.sources : source.name]
      notification_names = [for notification in google_scc_notification_config.notifications : notification.name]
    }

    cloud_armor_integration = {
      policy_ids        = [for policy in google_compute_security_policy.policies : policy.id]
      policy_self_links = [for policy in google_compute_security_policy.policies : policy.self_link]
    }

    binary_authorization_integration = var.binary_authorization.enabled ? {
      policy_id      = google_binary_authorization_policy.policy[0].id
      attestor_names = [for attestor in google_binary_authorization_attestor.attestors : attestor.name]
    } : null

    dlp_integration = var.dlp_config.enabled ? {
      inspect_template_names = [for template in google_data_loss_prevention_inspect_template.inspect_templates : template.name]
      job_trigger_names      = [for trigger in google_data_loss_prevention_job_trigger.job_triggers : trigger.name]
    } : null
  }
}

# Security Monitoring Outputs
output "monitoring_configuration" {
  description = "Security monitoring and alerting configuration"
  value = {
    enabled = var.enable_security_monitoring

    notification_channels = var.security_notifications.enabled ? {
      email_recipients  = var.security_notifications.email_recipients
      severity_levels   = var.security_notifications.severity_levels
      slack_enabled     = var.security_notifications.slack_webhook_url != null
      pagerduty_enabled = var.security_notifications.pagerduty_key != null
    } : null

    threat_detection_config = var.threat_detection.enabled ? {
      anomaly_detection    = var.threat_detection.anomaly_detection
      behavioral_analysis  = var.threat_detection.behavioral_analysis
      machine_learning     = var.threat_detection.machine_learning
      threat_intelligence  = var.threat_detection.threat_intelligence
      real_time_monitoring = var.threat_detection.real_time_monitoring
      custom_rules_count   = length(var.threat_detection.custom_rules)
    } : null

    incident_response_config = var.incident_response.enabled ? {
      auto_containment    = var.incident_response.auto_containment
      auto_investigation  = var.incident_response.auto_investigation
      playbooks_enabled   = var.incident_response.playbooks_enabled
      forensics_enabled   = var.incident_response.forensics_enabled
      recovery_automation = var.incident_response.recovery_automation
      escalation_levels   = length(distinct([for contact in var.incident_response.escalation_policy.contacts : contact.level]))
    } : null
  }
}
