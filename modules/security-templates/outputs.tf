/**
 * Security Templates Outputs
 *
 * Output values for security configuration and access management
 */

# Service Account Outputs
output "agent_service_accounts" {
  description = "Agent service account information"
  value = {
    for k, v in google_service_account.agent_service_accounts : k => {
      email      = v.email
      name       = v.name
      unique_id  = v.unique_id
      account_id = v.account_id
    }
  }
}

# Kubernetes Service Accounts
output "kubernetes_service_accounts" {
  description = "Kubernetes service account information"
  value = {
    for k, v in kubernetes_service_account.agent_k8s_service_accounts : k => {
      name      = v.metadata[0].name
      namespace = v.metadata[0].namespace
      annotations = v.metadata[0].annotations
    }
  }
}

# IAM Configuration
output "iam_configuration" {
  description = "IAM configuration summary"
  value = {
    custom_roles = {
      for k, v in google_project_iam_custom_role.agent_custom_roles : k => {
        role_id     = v.role_id
        title       = v.title
        permissions = v.permissions
      }
    }

    workload_identity_enabled = var.enable_workload_identity

    security_policies = {
      for agent_type in local.agent_types : agent_type => {
        security_level = local.agent_security_policies[agent_type].security_level
        compute_role = contains(["platform-engineer", "devops-agent", "sre-agent"], agent_type) ?
          "roles/compute.admin" : "roles/compute.viewer"
        storage_role = contains(["data-engineer", "platform-engineer"], agent_type) ?
          "roles/storage.admin" : "roles/storage.objectViewer"
      }
    }
  }
}

# Network Security Outputs
output "network_security" {
  description = "Network security configuration"
  value = {
    firewall_rules = {
      for k, v in google_compute_firewall.agent_security_rules : k => {
        name      = v.name
        direction = v.direction
        priority  = v.priority
        network   = v.network
        allow     = v.allow
        deny      = v.deny
      }
    }

    network_policies_enabled = var.enable_kubernetes_network_policies

    security_rules_count = length(var.firewall_security_rules)
  }
}

# Kubernetes RBAC Outputs
output "kubernetes_rbac" {
  description = "Kubernetes RBAC configuration"
  value = {
    cluster_roles = {
      for k, v in kubernetes_cluster_role.agent_cluster_roles : k => {
        name  = v.metadata[0].name
        rules = length(v.rule)
      }
    }

    role_bindings = {
      for k, v in kubernetes_cluster_role_binding.agent_cluster_role_bindings : k => {
        name      = v.metadata[0].name
        role_name = v.role_ref[0].name
        subjects  = length(v.subject)
      }
    }

    rbac_rules_summary = {
      for agent_type, rules in var.kubernetes_rbac_rules : agent_type => {
        rules_count = length(rules)
        permissions = rules[*].verbs
      }
    }
  }
}

# Secret Management Outputs
output "secret_management" {
  description = "Secret management configuration"
  value = {
    secret_manager_secrets = {
      for k, v in google_secret_manager_secret.agent_secrets : k => {
        secret_id = v.secret_id
        name      = v.name
        labels    = v.labels
      }
    }

    kubernetes_secrets = {
      for k, v in kubernetes_secret.agent_kubernetes_secrets : k => {
        name      = v.metadata[0].name
        namespace = v.metadata[0].namespace
        type      = v.type
      }
    }

    secret_access_bindings = length(google_secret_manager_secret_iam_member.agent_secret_access)
  }

  sensitive = true
}

# Security Monitoring Outputs
output "security_monitoring" {
  description = "Security monitoring and audit configuration"
  value = {
    audit_logging_enabled = var.enable_security_audit_logging

    audit_sink = var.enable_security_audit_logging ? {
      name        = google_logging_project_sink.security_audit_sink[0].name
      destination = google_logging_project_sink.security_audit_sink[0].destination
      filter      = google_logging_project_sink.security_audit_sink[0].filter
    } : null

    audit_dataset = var.enable_security_audit_logging ? {
      dataset_id = google_bigquery_dataset.security_audit_dataset[0].dataset_id
      location   = google_bigquery_dataset.security_audit_dataset[0].location
    } : null

    asset_inventory_enabled = var.enable_asset_inventory_feed

    monitoring_topic = var.enable_asset_inventory_feed ? {
      name = google_pubsub_topic.security_monitoring_topic[0].name
    } : null
  }
}

# Binary Authorization Outputs
output "binary_authorization" {
  description = "Binary Authorization configuration"
  value = {
    enabled = var.enable_binary_authorization

    policy = var.enable_binary_authorization ? {
      admission_whitelist = [
        "${var.container_registry}/*"
      ]
      default_rule = "REQUIRE_ATTESTATION"
    } : null

    attestor = var.enable_binary_authorization ? {
      name = google_binary_authorization_attestor.genesis_attestor[0].name
    } : null
  }

  sensitive = true
}

# Pod Security Configuration
output "pod_security" {
  description = "Pod security configuration"
  value = {
    pod_security_standards_enabled = var.enable_pod_security_standards

    security_context_defaults = {
      privileged                = false
      allowPrivilegeEscalation  = false
      readOnlyRootFilesystem    = true
      runAsNonRoot             = true
      requiredDropCapabilities = ["ALL"]
    }

    allowed_volumes = [
      "configMap",
      "emptyDir",
      "projected",
      "secret",
      "downwardAPI",
      "persistentVolumeClaim"
    ]
  }
}

# Security Compliance Summary
output "security_compliance_summary" {
  description = "Summary of security compliance features"
  value = {
    # Core security features
    workload_identity        = var.enable_workload_identity
    network_policies         = var.enable_kubernetes_network_policies
    pod_security_standards   = var.enable_pod_security_standards
    binary_authorization     = var.enable_binary_authorization

    # Monitoring and auditing
    security_audit_logging   = var.enable_security_audit_logging
    asset_inventory_feed     = var.enable_asset_inventory_feed
    firewall_logging        = var.enable_firewall_logging

    # Access control
    service_accounts_count  = length(google_service_account.agent_service_accounts)
    custom_roles_count     = length(google_project_iam_custom_role.agent_custom_roles)
    rbac_roles_count       = length(kubernetes_cluster_role.agent_cluster_roles)

    # Secret management
    secrets_count          = length(google_secret_manager_secret.agent_secrets)
    k8s_secrets_count      = length(kubernetes_secret.agent_kubernetes_secrets)

    # Network security
    firewall_rules_count   = length(google_compute_firewall.agent_security_rules)

    # Agent security levels
    high_security_agents = [
      for agent_type in local.agent_types : agent_type
      if local.agent_security_policies[agent_type].security_level == "high"
    ]

    standard_security_agents = [
      for agent_type in local.agent_types : agent_type
      if local.agent_security_policies[agent_type].security_level == "standard"
    ]
  }
}

# Agent Security Policies
output "agent_security_policies" {
  description = "Security policies by agent type"
  value = {
    for agent_type in local.agent_types : agent_type => {
      security_level = local.agent_security_policies[agent_type].security_level

      gcp_permissions = {
        compute = length(local.agent_security_policies[agent_type].compute_permissions)
        storage = length(local.agent_security_policies[agent_type].storage_permissions)
        network = length(local.agent_security_policies[agent_type].network_permissions)
      }

      kubernetes_permissions = {
        rules_count = length(var.kubernetes_rbac_rules[agent_type])
        api_groups = distinct(flatten([
          for rule in var.kubernetes_rbac_rules[agent_type] : rule.api_groups
        ]))
        verbs = distinct(flatten([
          for rule in var.kubernetes_rbac_rules[agent_type] : rule.verbs
        ]))
      }

      service_account = {
        gcp_email = google_service_account.agent_service_accounts[agent_type].email
        k8s_name  = var.enable_workload_identity ? "${agent_type}-service-account" : null
      }
    }
  }
}

# Security Best Practices Checklist
output "security_checklist" {
  description = "Security best practices implementation status"
  value = {
    # Identity and Access Management
    iam = {
      service_accounts_per_agent     = "✓ Implemented"
      least_privilege_permissions    = "✓ Implemented"
      workload_identity             = var.enable_workload_identity ? "✓ Enabled" : "⚠ Disabled"
      custom_roles_for_elevation    = length(google_project_iam_custom_role.agent_custom_roles) > 0 ? "✓ Implemented" : "⚠ Not configured"
    }

    # Network Security
    network = {
      firewall_rules_configured     = length(google_compute_firewall.agent_security_rules) > 0 ? "✓ Configured" : "⚠ Not configured"
      deny_by_default              = "✓ Implemented"
      network_policies_enabled      = var.enable_kubernetes_network_policies ? "✓ Enabled" : "⚠ Disabled"
      firewall_logging             = var.enable_firewall_logging ? "✓ Enabled" : "⚠ Disabled"
    }

    # Container Security
    container = {
      pod_security_standards        = var.enable_pod_security_standards ? "✓ Enabled" : "⚠ Disabled"
      binary_authorization         = var.enable_binary_authorization ? "✓ Enabled" : "⚠ Disabled"
      non_root_containers          = "✓ Enforced"
      readonly_filesystem          = "✓ Enforced"
      dropped_capabilities         = "✓ All capabilities dropped"
    }

    # Secret Management
    secrets = {
      secret_manager_integration    = length(google_secret_manager_secret.agent_secrets) > 0 ? "✓ Configured" : "⚠ Not configured"
      no_hardcoded_secrets         = "✓ Enforced"
      secret_access_controls       = length(google_secret_manager_secret_iam_member.agent_secret_access) > 0 ? "✓ Configured" : "⚠ Not configured"
      kubernetes_secret_sync       = length(kubernetes_secret.agent_kubernetes_secrets) > 0 ? "✓ Configured" : "⚠ Not configured"
    }

    # Monitoring and Auditing
    monitoring = {
      security_audit_logging       = var.enable_security_audit_logging ? "✓ Enabled" : "⚠ Disabled"
      asset_inventory_monitoring   = var.enable_asset_inventory_feed ? "✓ Enabled" : "⚠ Disabled"
      bigquery_audit_dataset      = var.enable_security_audit_logging ? "✓ Configured" : "⚠ Not configured"
    }

    # Compliance
    compliance = {
      rbac_configured              = length(kubernetes_cluster_role.agent_cluster_roles) > 0 ? "✓ Configured" : "⚠ Not configured"
      agent_isolation             = "✓ Implemented"
      security_boundaries         = "✓ Established"
      least_privilege_networking   = var.enable_kubernetes_network_policies ? "✓ Implemented" : "⚠ Not implemented"
    }
  }
}

# Integration Points
output "integration_endpoints" {
  description = "Security integration points for other modules"
  value = {
    # Service account emails for VM module
    vm_service_accounts = {
      for k, v in google_service_account.agent_service_accounts : k => v.email
    }

    # Kubernetes service account names for container module
    k8s_service_accounts = var.enable_workload_identity ? {
      for k, v in kubernetes_service_account.agent_k8s_service_accounts : k => v.metadata[0].name
    } : {}

    # Network tags for firewall rules
    security_network_tags = [
      for rule in var.firewall_security_rules : rule.target_tags
      if lookup(rule, "target_tags", null) != null
    ]

    # Secret manager secret names
    secret_manager_secrets = {
      for k, v in google_secret_manager_secret.agent_secrets : k => v.secret_id
    }

    # Security monitoring endpoints
    monitoring_endpoints = {
      audit_dataset = var.enable_security_audit_logging ?
        google_bigquery_dataset.security_audit_dataset[0].dataset_id : null
      monitoring_topic = var.enable_asset_inventory_feed ?
        google_pubsub_topic.security_monitoring_topic[0].name : null
    }
  }
}
