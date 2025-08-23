/**
 * Security Module
 *
 * Comprehensive security infrastructure for GCP
 * Includes KMS, Secret Manager, IAM policies, security scanning, and compliance automation
 */

locals {
  # Default labels
  default_labels = {
    managed_by  = "terraform"
    module      = "security"
    environment = var.environment
  }

  merged_labels = merge(local.default_labels, var.labels)

  # KMS key rings processing
  key_rings = {
    for ring in var.kms_key_rings : ring.name => merge(ring, {
      full_name = "${var.name_prefix}-${ring.name}"
    })
  }

  # KMS keys processing
  kms_keys = flatten([
    for ring_name, ring in local.key_rings : [
      for key in lookup(ring, "keys", []) : {
        key_name  = "${ring_name}-${key.name}"
        ring_name = ring_name
        key = merge(key, {
          full_name = "${var.name_prefix}-${key.name}"
        })
      }
    ]
  ])

  # Secret Manager secrets processing
  secrets = {
    for secret in var.secrets : secret.name => merge(secret, {
      full_name = "${var.name_prefix}-${secret.name}"
    })
  }

  # Security policies processing
  security_policies = {
    for policy in var.security_policies : policy.name => merge(policy, {
      full_name = "${var.name_prefix}-${policy.name}"
    })
  }

  # IAM custom roles processing
  custom_roles = {
    for role in var.custom_iam_roles : role.role_id => role
  }

  # Binary Authorization attestors
  attestors = {
    for attestor in var.binary_authorization.attestors : attestor.name => merge(attestor, {
      full_name = "${var.name_prefix}-${attestor.name}"
    })
  }
}

# KMS Key Rings
resource "google_kms_key_ring" "key_rings" {
  for_each = local.key_rings

  name     = each.value.full_name
  project  = var.project_id
  location = lookup(each.value, "location", var.default_region)
}

# KMS Crypto Keys
resource "google_kms_crypto_key" "keys" {
  for_each = {
    for key in local.kms_keys : key.key_name => key
  }

  name     = each.value.key.full_name
  key_ring = google_kms_key_ring.key_rings[each.value.ring_name].id
  purpose  = lookup(each.value.key, "purpose", "ENCRYPT_DECRYPT")

  # Key rotation
  rotation_period = lookup(each.value.key, "rotation_period", "7776000s") # 90 days

  # Version template
  dynamic "version_template" {
    for_each = lookup(each.value.key, "version_template", null) != null ? [1] : []
    content {
      algorithm        = each.value.key.version_template.algorithm
      protection_level = lookup(each.value.key.version_template, "protection_level", "SOFTWARE")
    }
  }

  # Lifecycle
  lifecycle {
    prevent_destroy = true
  }

  labels = merge(
    local.merged_labels,
    lookup(each.value.key, "labels", {}),
    {
      key_ring = each.value.ring_name
      purpose  = lookup(each.value.key, "purpose", "encrypt_decrypt")
    }
  )
}

# KMS Key IAM bindings
resource "google_kms_crypto_key_iam_binding" "key_bindings" {
  for_each = {
    for binding in flatten([
      for key_name, key_config in local.kms_keys : [
        for binding in lookup(key_config.key, "iam_bindings", []) : {
          key      = "${key_config.key_name}-${binding.role}"
          key_name = key_config.key_name
          binding  = binding
        }
      ]
    ]) : binding.key => binding
  }

  crypto_key_id = google_kms_crypto_key.keys[each.value.key_name].id
  role          = each.value.binding.role
  members       = each.value.binding.members

  dynamic "condition" {
    for_each = lookup(each.value.binding, "condition", null) != null ? [1] : []
    content {
      title       = each.value.binding.condition.title
      description = lookup(each.value.binding.condition, "description", null)
      expression  = each.value.binding.condition.expression
    }
  }
}

# Secret Manager Secrets
resource "google_secret_manager_secret" "secrets" {
  for_each = local.secrets

  project   = var.project_id
  secret_id = each.value.full_name

  # Replication
  dynamic "replication" {
    for_each = [1] # Always have replication block
    content {
      # Automatic replication
      dynamic "auto" {
        for_each = lookup(each.value, "replication_policy", "auto") == "auto" ? [1] : []
        content {
          dynamic "customer_managed_encryption" {
            for_each = lookup(each.value, "encryption_key", null) != null ? [1] : []
            content {
              kms_key_name = each.value.encryption_key
            }
          }
        }
      }

      # User-managed replication
      dynamic "user_managed" {
        for_each = lookup(each.value, "replication_policy", "auto") == "user_managed" ? [1] : []
        content {
          dynamic "replicas" {
            for_each = lookup(each.value, "replica_locations", [])
            content {
              location = replicas.value.location
              dynamic "customer_managed_encryption" {
                for_each = lookup(replicas.value, "encryption_key", null) != null ? [1] : []
                content {
                  kms_key_name = replicas.value.encryption_key
                }
              }
            }
          }
        }
      }
    }
  }

  # Expiry and TTL
  dynamic "expire_time" {
    for_each = lookup(each.value, "expire_time", null) != null ? [1] : []
    content {
      expire_time = each.value.expire_time
    }
  }

  dynamic "ttl" {
    for_each = lookup(each.value, "ttl", null) != null ? [1] : []
    content {
      ttl = each.value.ttl
    }
  }

  # Rotation
  dynamic "rotation" {
    for_each = lookup(each.value, "rotation", null) != null ? [1] : []
    content {
      next_rotation_time = lookup(each.value.rotation, "next_rotation_time", null)
      rotation_period    = lookup(each.value.rotation, "rotation_period", null)
    }
  }

  # Topics for notifications
  dynamic "topics" {
    for_each = lookup(each.value, "topics", [])
    content {
      name = topics.value
    }
  }

  # Annotations
  annotations = lookup(each.value, "annotations", {})

  labels = merge(
    local.merged_labels,
    lookup(each.value, "labels", {}),
    {
      secret_type = lookup(each.value, "secret_type", "application")
    }
  )
}

# Secret Manager Secret Versions
resource "google_secret_manager_secret_version" "secret_versions" {
  for_each = {
    for secret_name, secret in local.secrets :
    secret_name => secret
    if lookup(secret, "secret_data", null) != null
  }

  secret      = google_secret_manager_secret.secrets[each.key].id
  secret_data = each.value.secret_data

  # Enabled state
  enabled = lookup(each.value, "enabled", true)

  depends_on = [google_secret_manager_secret.secrets]
}

# Secret Manager IAM bindings
resource "google_secret_manager_secret_iam_binding" "secret_bindings" {
  for_each = {
    for binding in flatten([
      for secret_name, secret in local.secrets : [
        for binding in lookup(secret, "iam_bindings", []) : {
          key         = "${secret_name}-${binding.role}"
          secret_name = secret_name
          binding     = binding
        }
      ]
    ]) : binding.key => binding
  }

  project   = var.project_id
  secret_id = google_secret_manager_secret.secrets[each.value.secret_name].secret_id
  role      = each.value.binding.role
  members   = each.value.binding.members

  dynamic "condition" {
    for_each = lookup(each.value.binding, "condition", null) != null ? [1] : []
    content {
      title       = each.value.binding.condition.title
      description = lookup(each.value.binding.condition, "description", null)
      expression  = each.value.binding.condition.expression
    }
  }
}

# Custom IAM Roles
resource "google_project_iam_custom_role" "custom_roles" {
  for_each = local.custom_roles

  project     = var.project_id
  role_id     = each.value.role_id
  title       = each.value.title
  description = each.value.description
  permissions = each.value.permissions
  stage       = lookup(each.value, "stage", "GA")
}

# Organization-level custom roles
resource "google_organization_iam_custom_role" "org_custom_roles" {
  for_each = {
    for role_id, role in local.custom_roles : role_id => role
    if var.organization_id != null && lookup(role, "scope", "project") == "organization"
  }

  org_id      = var.organization_id
  role_id     = each.value.role_id
  title       = each.value.title
  description = each.value.description
  permissions = each.value.permissions
  stage       = lookup(each.value, "stage", "GA")
}

# IAM Policy Bindings with Conditions
resource "google_project_iam_binding" "conditional_bindings" {
  for_each = {
    for idx, binding in var.conditional_iam_bindings :
    "${binding.role}-${idx}" => binding
  }

  project = var.project_id
  role    = each.value.role
  members = each.value.members

  dynamic "condition" {
    for_each = lookup(each.value, "condition", null) != null ? [1] : []
    content {
      title       = each.value.condition.title
      description = lookup(each.value.condition, "description", "")
      expression  = each.value.condition.expression
    }
  }
}

# Security Command Center Sources
resource "google_scc_source" "sources" {
  for_each = {
    for source in var.security_center_sources : source.display_name => source
    if var.organization_id != null
  }

  organization = var.organization_id
  display_name = each.value.display_name
  description  = lookup(each.value, "description", "Custom security source")
}

# Security Command Center Notifications
resource "google_scc_notification_config" "notifications" {
  for_each = {
    for notification in var.security_center_notifications : notification.config_id => notification
    if var.organization_id != null
  }

  config_id    = each.value.config_id
  organization = var.organization_id
  description  = lookup(each.value, "description", "Security notification config")
  pubsub_topic = each.value.pubsub_topic

  streaming_config {
    filter = each.value.filter
  }
}

# Binary Authorization Policy
resource "google_binary_authorization_policy" "policy" {
  count = var.binary_authorization.enabled ? 1 : 0

  project = var.project_id

  # Default admission rule
  default_admission_rule {
    evaluation_mode  = var.binary_authorization.default_admission_rule.evaluation_mode
    enforcement_mode = var.binary_authorization.default_admission_rule.enforcement_mode

    require_attestations_by = [
      for attestor in google_binary_authorization_attestor.attestors :
      attestor.name
    ]
  }

  # Cluster-specific admission rules
  dynamic "admission_whitelist_patterns" {
    for_each = var.binary_authorization.admission_whitelist_patterns
    content {
      name_pattern = admission_whitelist_patterns.value
    }
  }

  # Istio service identity admission rules
  dynamic "istio_service_identity_admission_rules" {
    for_each = var.binary_authorization.istio_service_identity_admission_rules
    content {
      evaluation_mode  = istio_service_identity_admission_rules.value.evaluation_mode
      enforcement_mode = istio_service_identity_admission_rules.value.enforcement_mode

      require_attestations_by = istio_service_identity_admission_rules.value.require_attestations_by
    }
  }

  # Kubernetes namespace admission rules
  dynamic "kubernetes_namespace_admission_rules" {
    for_each = var.binary_authorization.kubernetes_namespace_admission_rules
    content {
      namespace        = kubernetes_namespace_admission_rules.value.namespace
      evaluation_mode  = kubernetes_namespace_admission_rules.value.evaluation_mode
      enforcement_mode = kubernetes_namespace_admission_rules.value.enforcement_mode

      require_attestations_by = kubernetes_namespace_admission_rules.value.require_attestations_by
    }
  }

  # Kubernetes service account admission rules
  dynamic "kubernetes_service_account_admission_rules" {
    for_each = var.binary_authorization.kubernetes_service_account_admission_rules
    content {
      service_account  = kubernetes_service_account_admission_rules.value.service_account
      namespace        = kubernetes_service_account_admission_rules.value.namespace
      evaluation_mode  = kubernetes_service_account_admission_rules.value.evaluation_mode
      enforcement_mode = kubernetes_service_account_admission_rules.value.enforcement_mode

      require_attestations_by = kubernetes_service_account_admission_rules.value.require_attestations_by
    }
  }

  # Global policy evaluation mode
  global_policy_evaluation_mode = lookup(var.binary_authorization, "global_policy_evaluation_mode", "ENABLE")
}

# Binary Authorization Attestors
resource "google_binary_authorization_attestor" "attestors" {
  for_each = local.attestors

  project = var.project_id
  name    = each.value.full_name

  attestation_authority_note {
    note_reference = each.value.note_reference

    dynamic "public_keys" {
      for_each = lookup(each.value, "public_keys", [])
      content {
        id                           = public_keys.value.id
        ascii_armored_pgp_public_key = lookup(public_keys.value, "ascii_armored_pgp_public_key", null)

        dynamic "pkix_public_key" {
          for_each = lookup(public_keys.value, "pkix_public_key", null) != null ? [1] : []
          content {
            public_key_pem      = public_keys.value.pkix_public_key.public_key_pem
            signature_algorithm = lookup(public_keys.value.pkix_public_key, "signature_algorithm", null)
          }
        }
      }
    }
  }

  description = lookup(each.value, "description", "Binary Authorization attestor")
}

# Security Policies (Cloud Armor)
resource "google_compute_security_policy" "policies" {
  for_each = local.security_policies

  project     = var.project_id
  name        = each.value.full_name
  description = lookup(each.value, "description", "Security policy ${each.value.name}")

  # Adaptive protection configuration
  dynamic "adaptive_protection_config" {
    for_each = lookup(each.value, "adaptive_protection_config", null) != null ? [1] : []
    content {
      layer_7_ddos_defense_config {
        enable          = lookup(each.value.adaptive_protection_config.layer_7_ddos_defense_config, "enable", true)
        rule_visibility = lookup(each.value.adaptive_protection_config.layer_7_ddos_defense_config, "rule_visibility", "STANDARD")
      }

      auto_deploy_config {
        load_threshold              = lookup(each.value.adaptive_protection_config.auto_deploy_config, "load_threshold", 0.1)
        confidence_threshold        = lookup(each.value.adaptive_protection_config.auto_deploy_config, "confidence_threshold", 0.5)
        impacted_baseline_threshold = lookup(each.value.adaptive_protection_config.auto_deploy_config, "impacted_baseline_threshold", 0.01)
        expiration_sec              = lookup(each.value.adaptive_protection_config.auto_deploy_config, "expiration_sec", 600)
      }
    }
  }

  # Advanced options configuration
  dynamic "advanced_options_config" {
    for_each = lookup(each.value, "advanced_options_config", null) != null ? [1] : []
    content {
      json_parsing                     = lookup(each.value.advanced_options_config, "json_parsing", "DISABLED")
      json_custom_config_content_types = lookup(each.value.advanced_options_config, "json_custom_config_content_types", [])
      log_level                        = lookup(each.value.advanced_options_config, "log_level", "NORMAL")
      user_ip_request_headers          = lookup(each.value.advanced_options_config, "user_ip_request_headers", [])
    }
  }

  # Recaptcha options configuration
  dynamic "recaptcha_options_config" {
    for_each = lookup(each.value, "recaptcha_options_config", null) != null ? [1] : []
    content {
      redirect_site_key = each.value.recaptcha_options_config.redirect_site_key
    }
  }

  # Security rules
  dynamic "rule" {
    for_each = lookup(each.value, "rules", [])
    content {
      action      = rule.value.action
      priority    = rule.value.priority
      description = lookup(rule.value, "description", "Security rule")
      preview     = lookup(rule.value, "preview", false)

      # Match configuration
      dynamic "match" {
        for_each = lookup(rule.value, "match", null) != null ? [1] : []
        content {
          versioned_expr = lookup(rule.value.match, "versioned_expr", null)

          dynamic "config" {
            for_each = lookup(rule.value.match, "config", null) != null ? [1] : []
            content {
              src_ip_ranges = lookup(rule.value.match.config, "src_ip_ranges", [])
            }
          }

          dynamic "expr" {
            for_each = lookup(rule.value.match, "expr", null) != null ? [1] : []
            content {
              expression = rule.value.match.expr.expression
            }
          }
        }
      }

      # Rate limit options
      dynamic "rate_limit_options" {
        for_each = lookup(rule.value, "rate_limit_options", null) != null ? [1] : []
        content {
          conform_action      = rule.value.rate_limit_options.conform_action
          exceed_action       = rule.value.rate_limit_options.exceed_action
          enforce_on_key      = lookup(rule.value.rate_limit_options, "enforce_on_key", null)
          enforce_on_key_name = lookup(rule.value.rate_limit_options, "enforce_on_key_name", null)

          dynamic "rate_limit_threshold" {
            for_each = lookup(rule.value.rate_limit_options, "rate_limit_threshold", null) != null ? [1] : []
            content {
              count        = rule.value.rate_limit_options.rate_limit_threshold.count
              interval_sec = rule.value.rate_limit_options.rate_limit_threshold.interval_sec
            }
          }

          dynamic "ban_threshold" {
            for_each = lookup(rule.value.rate_limit_options, "ban_threshold", null) != null ? [1] : []
            content {
              count        = rule.value.rate_limit_options.ban_threshold.count
              interval_sec = rule.value.rate_limit_options.ban_threshold.interval_sec
            }
          }

          ban_duration_sec = lookup(rule.value.rate_limit_options, "ban_duration_sec", null)
        }
      }

      # Header action
      dynamic "header_action" {
        for_each = lookup(rule.value, "header_action", null) != null ? [1] : []
        content {
          dynamic "request_headers_to_adds" {
            for_each = lookup(rule.value.header_action, "request_headers_to_adds", [])
            content {
              header_name  = request_headers_to_adds.value.header_name
              header_value = request_headers_to_adds.value.header_value
            }
          }
        }
      }

      # Redirect options
      dynamic "redirect_options" {
        for_each = lookup(rule.value, "redirect_options", null) != null ? [1] : []
        content {
          type   = rule.value.redirect_options.type
          target = lookup(rule.value.redirect_options, "target", null)
        }
      }
    }
  }

  # Type (CLOUD_ARMOR or CLOUD_ARMOR_EDGE)
  type = lookup(each.value, "type", "CLOUD_ARMOR")
}

# Web Security Scanner Scan Configs
resource "google_security_scanner_scan_config" "scan_configs" {
  for_each = {
    for scan in var.web_security_scanner.scan_configs : scan.display_name => scan
    if var.web_security_scanner.enabled
  }

  project       = var.project_id
  display_name  = each.value.display_name
  starting_urls = each.value.starting_urls

  # Authentication
  dynamic "authentication" {
    for_each = lookup(each.value, "authentication", null) != null ? [1] : []
    content {
      dynamic "google_account" {
        for_each = lookup(each.value.authentication, "google_account", null) != null ? [1] : []
        content {
          username = each.value.authentication.google_account.username
          password = each.value.authentication.google_account.password
        }
      }

      dynamic "custom_account" {
        for_each = lookup(each.value.authentication, "custom_account", null) != null ? [1] : []
        content {
          username  = each.value.authentication.custom_account.username
          password  = each.value.authentication.custom_account.password
          login_url = each.value.authentication.custom_account.login_url
        }
      }
    }
  }

  # Schedule
  dynamic "schedule" {
    for_each = lookup(each.value, "schedule", null) != null ? [1] : []
    content {
      schedule_time          = each.value.schedule.schedule_time
      interval_duration_days = lookup(each.value.schedule, "interval_duration_days", 7)
    }
  }

  # Blacklist patterns
  blacklist_patterns = lookup(each.value, "blacklist_patterns", [])

  # Max QPS
  max_qps = lookup(each.value, "max_qps", 15)

  # User agent
  user_agent = lookup(each.value, "user_agent", "CHROME_LINUX")

  # Export to Security Command Center
  export_to_security_command_center = lookup(each.value, "export_to_security_command_center", "ENABLED")
}

# VPC Security Controls (Access Levels)
resource "google_access_context_manager_access_level" "access_levels" {
  for_each = {
    for level in var.vpc_security_controls.access_levels : level.name => level
    if var.vpc_security_controls.enabled && var.access_context_manager_policy != null
  }

  parent = "accessPolicies/${var.access_context_manager_policy}"
  name   = "accessPolicies/${var.access_context_manager_policy}/accessLevels/${each.value.name}"
  title  = each.value.title

  # Basic access level conditions
  dynamic "basic" {
    for_each = lookup(each.value, "basic", null) != null ? [1] : []
    content {
      combining_function = lookup(each.value.basic, "combining_function", "AND")

      # Conditions
      dynamic "conditions" {
        for_each = lookup(each.value.basic, "conditions", [])
        content {
          # IP subnetworks
          ip_subnetworks = lookup(conditions.value, "ip_subnetworks", [])

          # Required access levels
          required_access_levels = lookup(conditions.value, "required_access_levels", [])

          # Members
          members = lookup(conditions.value, "members", [])

          # Negate
          negate = lookup(conditions.value, "negate", false)

          # Regions
          regions = lookup(conditions.value, "regions", [])

          # Device policy
          dynamic "device_policy" {
            for_each = lookup(conditions.value, "device_policy", null) != null ? [1] : []
            content {
              require_screen_lock    = lookup(conditions.value.device_policy, "require_screen_lock", false)
              require_admin_approval = lookup(conditions.value.device_policy, "require_admin_approval", false)
              require_corp_owned     = lookup(conditions.value.device_policy, "require_corp_owned", false)

              dynamic "allowed_device_management_levels" {
                for_each = lookup(conditions.value.device_policy, "allowed_device_management_levels", [])
                content {
                  allowed_device_management_levels = allowed_device_management_levels.value
                }
              }

              dynamic "allowed_encryption_statuses" {
                for_each = lookup(conditions.value.device_policy, "allowed_encryption_statuses", [])
                content {
                  allowed_encryption_statuses = allowed_encryption_statuses.value
                }
              }

              dynamic "os_constraints" {
                for_each = lookup(conditions.value.device_policy, "os_constraints", [])
                content {
                  os_type                    = os_constraints.value.os_type
                  minimum_version            = lookup(os_constraints.value, "minimum_version", null)
                  require_verified_chrome_os = lookup(os_constraints.value, "require_verified_chrome_os", false)
                }
              }
            }
          }
        }
      }
    }
  }

  # Custom access level
  dynamic "custom" {
    for_each = lookup(each.value, "custom", null) != null ? [1] : []
    content {
      expr {
        expression  = each.value.custom.expr.expression
        title       = lookup(each.value.custom.expr, "title", "Custom access level")
        description = lookup(each.value.custom.expr, "description", "Custom access level condition")
        location    = lookup(each.value.custom.expr, "location", "")
      }
    }
  }

  description = lookup(each.value, "description", "Access level for VPC Security Controls")
}

# VPC Security Controls (Service Perimeters)
resource "google_access_context_manager_service_perimeter" "perimeters" {
  for_each = {
    for perimeter in var.vpc_security_controls.service_perimeters : perimeter.name => perimeter
    if var.vpc_security_controls.enabled && var.access_context_manager_policy != null
  }

  parent = "accessPolicies/${var.access_context_manager_policy}"
  name   = "accessPolicies/${var.access_context_manager_policy}/servicePerimeters/${each.value.name}"
  title  = each.value.title

  # Status
  dynamic "status" {
    for_each = lookup(each.value, "status", null) != null ? [1] : []
    content {
      resources           = each.value.status.resources
      restricted_services = each.value.status.restricted_services
      access_levels       = each.value.status.access_levels

      # VPC accessible services
      dynamic "vpc_accessible_services" {
        for_each = lookup(each.value.status, "vpc_accessible_services", null) != null ? [1] : []
        content {
          enable_restriction = each.value.status.vpc_accessible_services.enable_restriction
          allowed_services   = each.value.status.vpc_accessible_services.allowed_services
        }
      }

      # Ingress policies
      dynamic "ingress_policies" {
        for_each = lookup(each.value.status, "ingress_policies", [])
        content {
          dynamic "ingress_from" {
            for_each = lookup(ingress_policies.value, "ingress_from", null) != null ? [1] : []
            content {
              sources {
                access_level = lookup(ingress_policies.value.ingress_from.sources, "access_level", null)
                resource     = lookup(ingress_policies.value.ingress_from.sources, "resource", null)
              }
              identity_type = lookup(ingress_policies.value.ingress_from, "identity_type", null)
              identities    = lookup(ingress_policies.value.ingress_from, "identities", [])
            }
          }

          dynamic "ingress_to" {
            for_each = lookup(ingress_policies.value, "ingress_to", null) != null ? [1] : []
            content {
              resources = ingress_policies.value.ingress_to.resources

              dynamic "operations" {
                for_each = lookup(ingress_policies.value.ingress_to, "operations", [])
                content {
                  service_name = operations.value.service_name

                  dynamic "method_selectors" {
                    for_each = lookup(operations.value, "method_selectors", [])
                    content {
                      method     = lookup(method_selectors.value, "method", null)
                      permission = lookup(method_selectors.value, "permission", null)
                    }
                  }
                }
              }
            }
          }
        }
      }

      # Egress policies
      dynamic "egress_policies" {
        for_each = lookup(each.value.status, "egress_policies", [])
        content {
          dynamic "egress_from" {
            for_each = lookup(egress_policies.value, "egress_from", null) != null ? [1] : []
            content {
              identity_type = lookup(egress_policies.value.egress_from, "identity_type", null)
              identities    = lookup(egress_policies.value.egress_from, "identities", [])
            }
          }

          dynamic "egress_to" {
            for_each = lookup(egress_policies.value, "egress_to", null) != null ? [1] : []
            content {
              resources          = lookup(egress_policies.value.egress_to, "resources", [])
              external_resources = lookup(egress_policies.value.egress_to, "external_resources", [])

              dynamic "operations" {
                for_each = lookup(egress_policies.value.egress_to, "operations", [])
                content {
                  service_name = operations.value.service_name

                  dynamic "method_selectors" {
                    for_each = lookup(operations.value, "method_selectors", [])
                    content {
                      method     = lookup(method_selectors.value, "method", null)
                      permission = lookup(method_selectors.value, "permission", null)
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  # Spec (dry-run mode)
  dynamic "spec" {
    for_each = lookup(each.value, "spec", null) != null ? [1] : []
    content {
      resources           = each.value.spec.resources
      restricted_services = each.value.spec.restricted_services
      access_levels       = each.value.spec.access_levels

      # VPC accessible services
      dynamic "vpc_accessible_services" {
        for_each = lookup(each.value.spec, "vpc_accessible_services", null) != null ? [1] : []
        content {
          enable_restriction = each.value.spec.vpc_accessible_services.enable_restriction
          allowed_services   = each.value.spec.vpc_accessible_services.allowed_services
        }
      }
    }
  }

  perimeter_type = lookup(each.value, "perimeter_type", "PERIMETER_TYPE_REGULAR")
  description    = lookup(each.value, "description", "Service perimeter for VPC Security Controls")
}

# Data Loss Prevention (DLP) Inspect Templates
resource "google_data_loss_prevention_inspect_template" "inspect_templates" {
  for_each = {
    for template in var.dlp_config.inspect_templates : template.display_name => template
    if var.dlp_config.enabled
  }

  parent       = "projects/${var.project_id}"
  description  = lookup(each.value, "description", "DLP inspect template")
  display_name = each.value.display_name

  # Inspect configuration
  inspect_config {
    # Info types
    dynamic "info_types" {
      for_each = lookup(each.value.inspect_config, "info_types", [])
      content {
        name = info_types.value.name
      }
    }

    # Min likelihood
    min_likelihood = lookup(each.value.inspect_config, "min_likelihood", "POSSIBLE")

    # Limits
    dynamic "limits" {
      for_each = lookup(each.value.inspect_config, "limits", null) != null ? [1] : []
      content {
        max_findings_per_item    = lookup(each.value.inspect_config.limits, "max_findings_per_item", 100)
        max_findings_per_request = lookup(each.value.inspect_config.limits, "max_findings_per_request", 1000)

        dynamic "max_findings_per_info_type" {
          for_each = lookup(each.value.inspect_config.limits, "max_findings_per_info_type", [])
          content {
            info_type {
              name = max_findings_per_info_type.value.info_type.name
            }
            max_findings = max_findings_per_info_type.value.max_findings
          }
        }
      }
    }

    # Include quote
    include_quote = lookup(each.value.inspect_config, "include_quote", false)

    # Exclude info types
    exclude_info_types = lookup(each.value.inspect_config, "exclude_info_types", false)

    # Custom info types
    dynamic "custom_info_types" {
      for_each = lookup(each.value.inspect_config, "custom_info_types", [])
      content {
        info_type {
          name = custom_info_types.value.info_type.name
        }

        likelihood = lookup(custom_info_types.value, "likelihood", "POSSIBLE")

        dynamic "dictionary" {
          for_each = lookup(custom_info_types.value, "dictionary", null) != null ? [1] : []
          content {
            word_list {
              words = custom_info_types.value.dictionary.word_list.words
            }
          }
        }

        dynamic "regex" {
          for_each = lookup(custom_info_types.value, "regex", null) != null ? [1] : []
          content {
            pattern = custom_info_types.value.regex.pattern
          }
        }
      }
    }

    # Rule sets
    dynamic "rule_set" {
      for_each = lookup(each.value.inspect_config, "rule_sets", [])
      content {
        info_types {
          name = rule_set.value.info_types.name
        }

        dynamic "rules" {
          for_each = lookup(rule_set.value, "rules", [])
          content {
            dynamic "hotword_rule" {
              for_each = lookup(rules.value, "hotword_rule", null) != null ? [1] : []
              content {
                hotword_regex {
                  pattern = rules.value.hotword_rule.hotword_regex.pattern
                }

                proximity {
                  window_before = lookup(rules.value.hotword_rule.proximity, "window_before", 50)
                  window_after  = lookup(rules.value.hotword_rule.proximity, "window_after", 50)
                }

                likelihood_adjustment {
                  fixed_likelihood = lookup(rules.value.hotword_rule.likelihood_adjustment, "fixed_likelihood", "VERY_LIKELY")
                }
              }
            }

            dynamic "exclusion_rule" {
              for_each = lookup(rules.value, "exclusion_rule", null) != null ? [1] : []
              content {
                matching_type = rules.value.exclusion_rule.matching_type

                dynamic "dictionary" {
                  for_each = lookup(rules.value.exclusion_rule, "dictionary", null) != null ? [1] : []
                  content {
                    word_list {
                      words = rules.value.exclusion_rule.dictionary.word_list.words
                    }
                  }
                }

                dynamic "regex" {
                  for_each = lookup(rules.value.exclusion_rule, "regex", null) != null ? [1] : []
                  content {
                    pattern = rules.value.exclusion_rule.regex.pattern
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}

# Data Loss Prevention (DLP) Job Triggers
resource "google_data_loss_prevention_job_trigger" "job_triggers" {
  for_each = {
    for trigger in var.dlp_config.job_triggers : trigger.display_name => trigger
    if var.dlp_config.enabled
  }

  parent       = "projects/${var.project_id}"
  description  = lookup(each.value, "description", "DLP job trigger")
  display_name = each.value.display_name
  status       = lookup(each.value, "status", "HEALTHY")

  # Triggers
  dynamic "triggers" {
    for_each = lookup(each.value, "triggers", [])
    content {
      dynamic "schedule" {
        for_each = lookup(triggers.value, "schedule", null) != null ? [1] : []
        content {
          recurrence_period_duration = triggers.value.schedule.recurrence_period_duration
        }
      }

      dynamic "manual" {
        for_each = lookup(triggers.value, "manual", false) ? [1] : []
        content {}
      }
    }
  }

  # Inspect job
  inspect_job {
    inspect_template_name = lookup(each.value.inspect_job, "inspect_template_name", null)

    # Storage config
    storage_config {
      dynamic "cloud_storage_options" {
        for_each = lookup(each.value.inspect_job.storage_config, "cloud_storage_options", null) != null ? [1] : []
        content {
          file_set {
            url = each.value.inspect_job.storage_config.cloud_storage_options.file_set.url
          }

          bytes_limit_per_file         = lookup(each.value.inspect_job.storage_config.cloud_storage_options, "bytes_limit_per_file", 0)
          bytes_limit_per_file_percent = lookup(each.value.inspect_job.storage_config.cloud_storage_options, "bytes_limit_per_file_percent", 0)
          file_types                   = lookup(each.value.inspect_job.storage_config.cloud_storage_options, "file_types", [])
          sample_method                = lookup(each.value.inspect_job.storage_config.cloud_storage_options, "sample_method", "TOP")
          files_limit_percent          = lookup(each.value.inspect_job.storage_config.cloud_storage_options, "files_limit_percent", 0)
        }
      }

      dynamic "big_query_options" {
        for_each = lookup(each.value.inspect_job.storage_config, "big_query_options", null) != null ? [1] : []
        content {
          table_reference {
            project_id = lookup(each.value.inspect_job.storage_config.big_query_options.table_reference, "project_id", var.project_id)
            dataset_id = each.value.inspect_job.storage_config.big_query_options.table_reference.dataset_id
            table_id   = each.value.inspect_job.storage_config.big_query_options.table_reference.table_id
          }

          rows_limit         = lookup(each.value.inspect_job.storage_config.big_query_options, "rows_limit", 0)
          rows_limit_percent = lookup(each.value.inspect_job.storage_config.big_query_options, "rows_limit_percent", 0)
          sample_method      = lookup(each.value.inspect_job.storage_config.big_query_options, "sample_method", "TOP")

          dynamic "identifying_fields" {
            for_each = lookup(each.value.inspect_job.storage_config.big_query_options, "identifying_fields", [])
            content {
              name = identifying_fields.value.name
            }
          }

          dynamic "excluded_fields" {
            for_each = lookup(each.value.inspect_job.storage_config.big_query_options, "excluded_fields", [])
            content {
              name = excluded_fields.value.name
            }
          }

          dynamic "included_fields" {
            for_each = lookup(each.value.inspect_job.storage_config.big_query_options, "included_fields", [])
            content {
              name = included_fields.value.name
            }
          }
        }
      }

      dynamic "datastore_options" {
        for_each = lookup(each.value.inspect_job.storage_config, "datastore_options", null) != null ? [1] : []
        content {
          partition_id {
            project_id   = lookup(each.value.inspect_job.storage_config.datastore_options.partition_id, "project_id", var.project_id)
            namespace_id = lookup(each.value.inspect_job.storage_config.datastore_options.partition_id, "namespace_id", null)
          }

          kind {
            name = each.value.inspect_job.storage_config.datastore_options.kind.name
          }
        }
      }

      dynamic "timespan_config" {
        for_each = lookup(each.value.inspect_job.storage_config, "timespan_config", null) != null ? [1] : []
        content {
          start_time = lookup(each.value.inspect_job.storage_config.timespan_config, "start_time", null)
          end_time   = lookup(each.value.inspect_job.storage_config.timespan_config, "end_time", null)

          dynamic "timestamp_field" {
            for_each = lookup(each.value.inspect_job.storage_config.timespan_config, "timestamp_field", null) != null ? [1] : []
            content {
              name = each.value.inspect_job.storage_config.timespan_config.timestamp_field.name
            }
          }

          enable_auto_population_of_timespan_config = lookup(each.value.inspect_job.storage_config.timespan_config, "enable_auto_population_of_timespan_config", false)
        }
      }
    }

    # Actions
    dynamic "actions" {
      for_each = lookup(each.value.inspect_job, "actions", [])
      content {
        dynamic "save_findings" {
          for_each = lookup(actions.value, "save_findings", null) != null ? [1] : []
          content {
            output_config {
              table {
                project_id = lookup(actions.value.save_findings.output_config.table, "project_id", var.project_id)
                dataset_id = actions.value.save_findings.output_config.table.dataset_id
                table_id   = lookup(actions.value.save_findings.output_config.table, "table_id", null)
              }

              output_schema = lookup(actions.value.save_findings.output_config, "output_schema", "BASIC_COLUMNS")
            }
          }
        }

        dynamic "pub_sub" {
          for_each = lookup(actions.value, "pub_sub", null) != null ? [1] : []
          content {
            topic = actions.value.pub_sub.topic
          }
        }

        dynamic "publish_summary_to_cscc" {
          for_each = lookup(actions.value, "publish_summary_to_cscc", false) ? [1] : []
          content {}
        }

        dynamic "publish_findings_to_cloud_data_catalog" {
          for_each = lookup(actions.value, "publish_findings_to_cloud_data_catalog", false) ? [1] : []
          content {}
        }
      }
    }
  }
}
