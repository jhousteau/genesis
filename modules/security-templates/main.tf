/**
 * Security Templates Module
 *
 * Comprehensive security controls for VM and container infrastructure
 * Implements PIPES Protection methodology for agent-cage and claude-talk
 */

# Terraform version constraints moved to versions.tf

locals {
  # Standard labels following Genesis patterns
  default_labels = {
    managed_by   = "terraform"
    module       = "security-templates"
    environment  = var.environment
    component    = "security"
    purpose      = "infrastructure-protection"
  }

  merged_labels = merge(local.default_labels, var.labels)

  # Agent types for RBAC
  agent_types = [
    "backend-developer", "frontend-developer", "platform-engineer",
    "data-engineer", "integration-agent", "qa-automation",
    "sre-agent", "security-agent", "devops-agent",
    "project-manager", "architect", "tech-lead"
  ]

  # Non-sensitive keys for for_each loops to avoid sensitivity exposure
  agent_secret_keys = nonsensitive(keys(var.agent_secrets))
  kubernetes_secret_keys = nonsensitive(keys(var.kubernetes_secrets))

  # Security policies by agent type
  agent_security_policies = {
    for agent_type in local.agent_types : agent_type => {
      compute_permissions = contains([
        "platform-engineer", "devops-agent", "sre-agent"
      ], agent_type) ? var.elevated_compute_permissions : var.standard_compute_permissions

      storage_permissions = contains([
        "data-engineer", "platform-engineer"
      ], agent_type) ? var.elevated_storage_permissions : var.standard_storage_permissions

      network_permissions = contains([
        "platform-engineer", "security-agent", "sre-agent"
      ], agent_type) ? var.elevated_network_permissions : var.standard_network_permissions

      security_level = contains([
        "security-agent", "platform-engineer"
      ], agent_type) ? "high" : "standard"
    }
  }
}

# Service Accounts for Agent Types
resource "google_service_account" "agent_service_accounts" {
  for_each = toset(local.agent_types)

  account_id   = "${var.name_prefix}-${each.value}"
  display_name = "Genesis ${title(replace(each.value, "-", " "))} Agent"
  description  = "Service account for ${each.value} agent workloads"
  project      = var.project_id
}

# IAM Roles for Agent Service Accounts
resource "google_project_iam_member" "agent_compute_permissions" {
  for_each = toset([
    for agent_type in local.agent_types : agent_type
    if length(local.agent_security_policies[agent_type].compute_permissions) > 0
  ])

  project = var.project_id
  member  = "serviceAccount:${google_service_account.agent_service_accounts[each.value].email}"

  # Assign appropriate compute role based on agent type
  role = contains(["platform-engineer", "devops-agent", "sre-agent"], each.value) ? "roles/compute.admin" : "roles/compute.viewer"
}

resource "google_project_iam_member" "agent_storage_permissions" {
  for_each = toset([
    for agent_type in local.agent_types : agent_type
    if length(local.agent_security_policies[agent_type].storage_permissions) > 0
  ])

  project = var.project_id
  member  = "serviceAccount:${google_service_account.agent_service_accounts[each.value].email}"

  role = contains(["data-engineer", "platform-engineer"], each.value) ? "roles/storage.admin" : "roles/storage.objectViewer"
}

# Custom IAM Roles for Specific Agent Operations
resource "google_project_iam_custom_role" "agent_custom_roles" {
  for_each = {
    for agent_type in local.agent_types : agent_type => local.agent_security_policies[agent_type]
    if local.agent_security_policies[agent_type].security_level == "high"
  }

  role_id     = "${replace(var.name_prefix, "-", "_")}_${replace(each.key, "-", "_")}_custom"
  title       = "Genesis ${title(replace(each.key, "-", " "))} Custom Role"
  description = "Custom role for ${each.key} with elevated permissions"

  permissions = concat(
    each.value.compute_permissions,
    each.value.storage_permissions,
    each.value.network_permissions
  )
}

# Workload Identity for Kubernetes
resource "google_service_account_iam_member" "workload_identity_binding" {
  for_each = var.enable_workload_identity ? toset(local.agent_types) : toset([])

  service_account_id = google_service_account.agent_service_accounts[each.value].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.kubernetes_namespace}/${each.value}-service-account]"
}

# Kubernetes Service Accounts
resource "kubernetes_service_account" "agent_k8s_service_accounts" {
  for_each = var.enable_workload_identity ? toset(local.agent_types) : toset([])

  metadata {
    name      = "${each.value}-service-account"
    namespace = var.kubernetes_namespace

    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.agent_service_accounts[each.value].email
    }

    labels = merge(
      local.merged_labels,
      {
        "agent-type" = each.value
        "security-level" = local.agent_security_policies[each.value].security_level
      }
    )
  }

  automount_service_account_token = false
}

# Network Security Policies
resource "google_compute_firewall" "agent_security_rules" {
  for_each = var.firewall_security_rules

  name    = "${var.name_prefix}-security-${each.key}"
  network = var.network_id
  project = var.project_id

  description = each.value.description
  direction   = each.value.direction
  priority    = each.value.priority

  # Source and target configuration
  source_ranges      = lookup(each.value, "source_ranges", null)
  destination_ranges = lookup(each.value, "destination_ranges", null)
  source_tags        = lookup(each.value, "source_tags", null)
  target_tags        = lookup(each.value, "target_tags", null)

  # Allow/deny rules
  dynamic "allow" {
    for_each = lookup(each.value, "allow", [])
    content {
      protocol = allow.value.protocol
      ports    = lookup(allow.value, "ports", null)
    }
  }

  dynamic "deny" {
    for_each = lookup(each.value, "deny", [])
    content {
      protocol = deny.value.protocol
      ports    = lookup(deny.value, "ports", null)
    }
  }

  # Logging for security monitoring
  log_config {
    metadata = var.enable_firewall_logging ? "INCLUDE_ALL_METADATA" : "EXCLUDE_ALL_METADATA"
  }
}

# Kubernetes Network Policies
resource "kubernetes_network_policy" "agent_network_policies" {
  for_each = var.enable_kubernetes_network_policies ? toset(local.agent_types) : toset([])

  metadata {
    name      = "${each.value}-network-policy"
    namespace = var.kubernetes_namespace

    labels = merge(
      local.merged_labels,
      {
        "agent-type" = each.value
      }
    )
  }

  spec {
    pod_selector {
      match_labels = {
        "app" = each.value
      }
    }

    policy_types = ["Ingress", "Egress"]

    # Ingress rules based on agent type
    dynamic "ingress" {
      for_each = local.agent_security_policies[each.value].security_level == "high" ? var.high_security_ingress_rules : var.standard_ingress_rules

      content {
        from {
          namespace_selector {
            match_labels = {
              name = ingress.value.namespace
            }
          }
        }

        ports {
          port     = ingress.value.port
          protocol = lookup(ingress.value, "protocol", "TCP")
        }
      }
    }

    # Egress rules based on agent type
    dynamic "egress" {
      for_each = local.agent_security_policies[each.value].security_level == "high" ? var.high_security_egress_rules : var.standard_egress_rules

      content {
        to {
          namespace_selector {
            match_labels = {
              name = egress.value.namespace
            }
          }
        }

        ports {
          port     = egress.value.port
          protocol = lookup(egress.value, "protocol", "TCP")
        }
      }
    }
  }
}

# Pod Security Standards
resource "kubernetes_manifest" "pod_security_policy" {
  count = var.enable_pod_security_standards ? 1 : 0

  manifest = {
    apiVersion = "policy/v1beta1"
    kind       = "PodSecurityPolicy"

    metadata = {
      name = "${var.name_prefix}-pod-security-policy"
      labels = local.merged_labels
    }

    spec = {
      privileged                = false
      allowPrivilegeEscalation  = false
      requiredDropCapabilities  = ["ALL"]
      volumes = [
        "configMap",
        "emptyDir",
        "projected",
        "secret",
        "downwardAPI",
        "persistentVolumeClaim"
      ]

      runAsUser = {
        rule = "MustRunAsNonRoot"
      }

      seLinux = {
        rule = "RunAsAny"
      }

      fsGroup = {
        rule = "RunAsAny"
      }

      readOnlyRootFilesystem = true
    }
  }
}

# RBAC for Agent Service Accounts
resource "kubernetes_cluster_role" "agent_cluster_roles" {
  for_each = toset(local.agent_types)

  metadata {
    name = "${each.value}-cluster-role"

    labels = merge(
      local.merged_labels,
      {
        "agent-type" = each.value
      }
    )
  }

  # Rules based on agent type
  dynamic "rule" {
    for_each = var.kubernetes_rbac_rules[each.value]

    content {
      api_groups = rule.value.api_groups
      resources  = rule.value.resources
      verbs      = rule.value.verbs
    }
  }
}

resource "kubernetes_cluster_role_binding" "agent_cluster_role_bindings" {
  for_each = toset(local.agent_types)

  metadata {
    name = "${each.value}-cluster-role-binding"

    labels = merge(
      local.merged_labels,
      {
        "agent-type" = each.value
      }
    )
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.agent_cluster_roles[each.value].metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = "${each.value}-service-account"
    namespace = var.kubernetes_namespace
  }
}

# Secret Management
resource "google_secret_manager_secret" "agent_secrets" {
  for_each = toset(local.agent_secret_keys)

  secret_id = "${var.name_prefix}-${each.key}"
  project   = var.project_id

  labels = merge(
    local.merged_labels,
    {
      "secret-type" = var.agent_secrets[each.key].type
      "agent-type"  = lookup(var.agent_secrets[each.key], "agent_type", "all")
    }
  )

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "agent_secret_versions" {
  for_each = toset(local.agent_secret_keys)

  secret      = google_secret_manager_secret.agent_secrets[each.key].id
  secret_data = var.agent_secrets[each.key].value

  lifecycle {
    ignore_changes = [secret_data]
  }
}

# Secret Manager IAM (temporarily disabled due to sensitivity constraints)
# TODO: Refactor to avoid sensitive for_each after issue #36 resolution
# resource "google_secret_manager_secret_iam_member" "agent_secret_access" {
#   for_each = {
#     for combo in flatten([
#       for secret_name, secret_config in var.agent_secrets : [
#         for agent_type in (lookup(secret_config, "agent_type", "all") == "all" ?
#           local.agent_types : [lookup(secret_config, "agent_type", "")]) : {
#           secret_name = secret_name
#           agent_type  = agent_type
#         }
#       ]
#     ]) : "${combo.secret_name}-${combo.agent_type}" => combo
#   }
#
#   secret_id = google_secret_manager_secret.agent_secrets[each.value.secret_name].secret_id
#   role      = "roles/secretmanager.secretAccessor"
#   member    = "serviceAccount:${google_service_account.agent_service_accounts[each.value.agent_type].email}"
# }

# Kubernetes Secrets from Secret Manager
resource "kubernetes_secret" "agent_kubernetes_secrets" {
  for_each = toset(local.kubernetes_secret_keys)

  metadata {
    name      = each.key
    namespace = var.kubernetes_namespace

    labels = merge(
      local.merged_labels,
      {
        "secret-type" = var.kubernetes_secrets[each.key].type
        "managed-by"  = "secret-manager"
      }
    )

    annotations = {
      "secret-manager.io/secret-name" = var.kubernetes_secrets[each.key].secret_manager_secret
    }
  }

  type = lookup(var.kubernetes_secrets[each.key], "kubernetes_type", "Opaque")

  data = {
    for key, value in var.kubernetes_secrets[each.key].data : key => base64encode(value)
  }
}

# Security Monitoring and Logging
resource "google_logging_project_sink" "security_audit_sink" {
  count = var.enable_security_audit_logging ? 1 : 0

  name        = "${var.name_prefix}-security-audit-sink"
  project     = var.project_id
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${var.security_audit_dataset}"

  filter = <<-EOT
    (protoPayload.serviceName="compute.googleapis.com" OR
     protoPayload.serviceName="container.googleapis.com" OR
     protoPayload.serviceName="iam.googleapis.com") AND
    (protoPayload.methodName:"insert" OR
     protoPayload.methodName:"delete" OR
     protoPayload.methodName:"setIamPolicy" OR
     protoPayload.methodName:"create" OR
     protoPayload.methodName:"update")
  EOT

  unique_writer_identity = true
}

# BigQuery dataset for security audit logs
resource "google_bigquery_dataset" "security_audit_dataset" {
  count = var.enable_security_audit_logging ? 1 : 0

  dataset_id    = var.security_audit_dataset
  project       = var.project_id
  friendly_name = "Genesis Security Audit Logs"
  description   = "Security audit logs for Genesis infrastructure"
  location      = var.region

  labels = local.merged_labels

  access {
    role          = "OWNER"
    user_by_email = var.security_audit_admin_email
  }

  access {
    role         = "READER"
    special_group = "projectReaders"
  }
}

# Cloud Asset Inventory for security monitoring
resource "google_cloud_asset_project_feed" "security_asset_feed" {
  count = var.enable_asset_inventory_feed ? 1 : 0

  project     = var.project_id
  feed_id     = "${var.name_prefix}-security-asset-feed"
  content_type = "RESOURCE"

  asset_types = [
    "compute.googleapis.com/Instance",
    "compute.googleapis.com/InstanceGroup",
    "container.googleapis.com/Cluster",
    "iam.googleapis.com/ServiceAccount",
    "secretmanager.googleapis.com/Secret"
  ]

  feed_output_config {
    pubsub_destination {
      topic = "projects/${var.project_id}/topics/${var.security_monitoring_topic}"
    }
  }
}

# Pub/Sub topic for security monitoring
resource "google_pubsub_topic" "security_monitoring_topic" {
  count = var.enable_asset_inventory_feed ? 1 : 0

  name    = var.security_monitoring_topic
  project = var.project_id

  labels = local.merged_labels

  message_retention_duration = "86400s"
}

# Binary Authorization Policy
resource "google_binary_authorization_policy" "genesis_binary_auth_policy" {
  count = var.enable_binary_authorization ? 1 : 0

  project = var.project_id

  admission_whitelist_patterns {
    name_pattern = "${var.container_registry}/*"
  }

  default_admission_rule {
    evaluation_mode  = "REQUIRE_ATTESTATION"
    enforcement_mode = "ENFORCED_BLOCK_AND_AUDIT_LOG"

    require_attestations_by = [
      "projects/${var.project_id}/attestors/${var.name_prefix}-attestor"
    ]
  }

  dynamic "cluster_admission_rules" {
    for_each = var.gke_clusters

    content {
      cluster                = cluster_admission_rules.value
      evaluation_mode        = "REQUIRE_ATTESTATION"
      enforcement_mode       = "ENFORCED_BLOCK_AND_AUDIT_LOG"
      require_attestations_by = [
        "projects/${var.project_id}/attestors/${var.name_prefix}-attestor"
      ]
    }
  }
}

# Container Analysis Attestor
resource "google_binary_authorization_attestor" "genesis_attestor" {
  count = var.enable_binary_authorization ? 1 : 0

  name    = "${var.name_prefix}-attestor"
  project = var.project_id

  attestation_authority_note {
    note_reference = "projects/${var.project_id}/notes/${var.name_prefix}-attestor-note"

    public_keys {
      ascii_armored_pgp_public_key = var.attestor_public_key
      id                          = "pgp-key-1"
    }
  }
}
