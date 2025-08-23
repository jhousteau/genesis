/**
 * Container Orchestration Module - Issue #31
 *
 * Comprehensive container orchestration for agent-cage and claude-talk migrations
 * Implements PIPES methodology for scalable container infrastructure
 */

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
}

locals {
  # Standard labels following Genesis patterns
  default_labels = {
    managed_by  = "terraform"
    module      = "container-orchestration"
    environment = var.environment
    component   = "infrastructure"
    purpose     = "agent-claude-talk-migration"
  }

  merged_labels = merge(local.default_labels, var.labels)

  # GKE cluster configuration
  cluster_config = merge(var.gke_cluster_config, {
    full_name = "${var.name_prefix}-${var.gke_cluster_config.name}"
    labels    = merge(local.merged_labels, lookup(var.gke_cluster_config, "labels", {}))
  })

  # Node pools configuration
  node_pools = {
    for pool in var.node_pools : pool.name => merge(pool, {
      full_name = "${var.name_prefix}-${pool.name}"
      labels = merge(local.merged_labels, lookup(pool, "labels", {}), {
        node_pool_type = lookup(pool, "node_pool_type", "general")
        workload_type  = lookup(pool, "workload_type", "mixed")
      })
    })
  }

  # Container registry configuration
  registry_repositories = {
    for repo in var.container_repositories : repo.name => merge(repo, {
      full_name = "${var.name_prefix}-${repo.name}"
      labels    = merge(local.merged_labels, lookup(repo, "labels", {}))
    })
  }

  # Service mesh configuration
  service_mesh_config = var.enable_service_mesh ? merge(var.service_mesh_config, {
    namespace = lookup(var.service_mesh_config, "namespace", "istio-system")
  }) : null
}

# GKE Cluster for Container Orchestration
resource "google_container_cluster" "main" {
  name     = local.cluster_config.full_name
  project  = var.project_id
  location = var.regional_cluster ? var.region : var.zone

  description = lookup(local.cluster_config, "description", "GKE cluster for Genesis agent and claude-talk orchestration")

  # Network configuration
  network         = var.network_id
  subnetwork      = var.subnet_id
  networking_mode = "VPC_NATIVE"

  # IP allocation for pods and services
  ip_allocation_policy {
    cluster_secondary_range_name  = var.pods_secondary_range_name
    services_secondary_range_name = var.services_secondary_range_name

    dynamic "additional_pod_ranges_config" {
      for_each = var.enable_autopilot ? [] : [1]
      content {
        pod_range_names = var.additional_pod_ranges
      }
    }
  }

  # Private cluster configuration
  dynamic "private_cluster_config" {
    for_each = var.enable_private_cluster ? [1] : []
    content {
      enable_private_nodes    = true
      enable_private_endpoint = var.enable_private_endpoint
      master_ipv4_cidr_block  = var.master_ipv4_cidr_block

      master_global_access_config {
        enabled = var.enable_master_global_access
      }
    }
  }

  # Autopilot configuration
  dynamic "cluster_autoscaling" {
    for_each = var.enable_autopilot ? [] : [1]
    content {
      enabled = var.enable_cluster_autoscaling

      dynamic "resource_limits" {
        for_each = var.cluster_autoscaling_resource_limits
        content {
          resource_type = resource_limits.value.resource_type
          minimum       = resource_limits.value.minimum
          maximum       = resource_limits.value.maximum
        }
      }

      dynamic "auto_provisioning_defaults" {
        for_each = var.enable_node_auto_provisioning ? [1] : []
        content {
          service_account = var.default_service_account
          oauth_scopes    = var.default_oauth_scopes

          management {
            auto_repair  = true
            auto_upgrade = var.enable_auto_upgrade
          }

          disk_size_gb = var.auto_provisioning_disk_size
          disk_type    = var.auto_provisioning_disk_type
          image_type   = var.auto_provisioning_image_type
        }
      }
    }
  }

  # Autopilot mode
  dynamic "enable_autopilot" {
    for_each = var.enable_autopilot ? [1] : []
    content {
      enabled = true
    }
  }

  # Workload identity
  dynamic "workload_identity_config" {
    for_each = var.enable_workload_identity ? [1] : []
    content {
      workload_pool = "${var.project_id}.svc.id.goog"
    }
  }

  # Addons configuration
  addons_config {
    http_load_balancing {
      disabled = !var.enable_http_load_balancing
    }

    horizontal_pod_autoscaling {
      disabled = !var.enable_horizontal_pod_autoscaling
    }

    network_policy_config {
      disabled = !var.enable_network_policy
    }

    istio_config {
      disabled = !var.enable_istio_addon
    }

    dns_cache_config {
      enabled = var.enable_dns_cache
    }

    gce_persistent_disk_csi_driver_config {
      enabled = var.enable_gce_pd_csi_driver
    }

    gcp_filestore_csi_driver_config {
      enabled = var.enable_filestore_csi_driver
    }

    gke_backup_agent_config {
      enabled = var.enable_backup_agent
    }
  }

  # Binary authorization
  dynamic "binary_authorization" {
    for_each = var.enable_binary_authorization ? [1] : []
    content {
      evaluation_mode = var.binary_authorization_evaluation_mode
    }
  }

  # Database encryption
  dynamic "database_encryption" {
    for_each = var.enable_database_encryption ? [1] : []
    content {
      state    = "ENCRYPTED"
      key_name = var.database_encryption_key
    }
  }

  # Master authorized networks
  dynamic "master_authorized_networks_config" {
    for_each = length(var.master_authorized_networks) > 0 ? [1] : []
    content {
      dynamic "cidr_blocks" {
        for_each = var.master_authorized_networks
        content {
          cidr_block   = cidr_blocks.value.cidr_block
          display_name = lookup(cidr_blocks.value, "display_name", null)
        }
      }
    }
  }

  # Network policy
  dynamic "network_policy" {
    for_each = var.enable_network_policy ? [1] : []
    content {
      enabled  = true
      provider = "CALICO"
    }
  }

  # Pod security policy
  dynamic "pod_security_policy_config" {
    for_each = var.enable_pod_security_policy ? [1] : []
    content {
      enabled = true
    }
  }

  # Resource usage export config
  dynamic "resource_usage_export_config" {
    for_each = var.enable_resource_usage_export ? [1] : []
    content {
      enable_network_egress_metering       = true
      enable_resource_consumption_metering = true

      bigquery_destination {
        dataset_id = var.resource_usage_bigquery_dataset
      }
    }
  }

  # Vertical Pod Autoscaling
  dynamic "vertical_pod_autoscaling" {
    for_each = var.enable_vertical_pod_autoscaling ? [1] : []
    content {
      enabled = true
    }
  }

  # Maintenance policy
  dynamic "maintenance_policy" {
    for_each = var.maintenance_policy != null ? [1] : []
    content {
      recurring_window {
        start_time = var.maintenance_policy.start_time
        end_time   = var.maintenance_policy.end_time
        recurrence = var.maintenance_policy.recurrence
      }

      dynamic "maintenance_exclusion" {
        for_each = var.maintenance_policy.exclusions
        content {
          exclusion_name = maintenance_exclusion.value.name
          start_time     = maintenance_exclusion.value.start_time
          end_time       = maintenance_exclusion.value.end_time

          exclusion_options {
            scope = maintenance_exclusion.value.scope
          }
        }
      }
    }
  }

  # Notification configuration
  dynamic "notification_config" {
    for_each = var.notification_config != null ? [1] : []
    content {
      pubsub {
        enabled = true
        topic   = var.notification_config.pubsub_topic

        filter {
          event_type = var.notification_config.event_types
        }
      }
    }
  }

  # Monitoring configuration
  monitoring_config {
    enable_components = var.monitoring_components

    dynamic "managed_prometheus_config" {
      for_each = var.enable_managed_prometheus ? [1] : []
      content {
        enabled = true
      }
    }

    dynamic "advanced_datapath_observability_config" {
      for_each = var.enable_advanced_datapath_observability ? [1] : []
      content {
        enable_metrics = true
        enable_relay   = var.enable_datapath_v2
      }
    }
  }

  # Logging configuration
  logging_config {
    enable_components = var.logging_components
  }

  # Security posture
  dynamic "security_posture_config" {
    for_each = var.enable_security_posture ? [1] : []
    content {
      mode               = var.security_posture_mode
      vulnerability_mode = var.security_posture_vulnerability_mode
    }
  }

  # Resource labels
  resource_labels = local.merged_labels

  # Remove default node pool immediately
  remove_default_node_pool = !var.enable_autopilot
  initial_node_count       = var.enable_autopilot ? null : 1

  # Lifecycle management
  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      initial_node_count,
      node_config
    ]
  }

  depends_on = [
    google_project_service.container_api
  ]
}

# GKE Node Pools (only for Standard clusters)
resource "google_container_node_pool" "pools" {
  for_each = var.enable_autopilot ? {} : local.node_pools

  name     = each.value.full_name
  project  = var.project_id
  location = google_container_cluster.main.location
  cluster  = google_container_cluster.main.name

  version    = lookup(each.value, "kubernetes_version", null)
  node_count = lookup(each.value, "initial_node_count", 1)

  # Node configuration
  node_config {
    machine_type = lookup(each.value, "machine_type", "e2-medium")
    image_type   = lookup(each.value, "image_type", "COS_CONTAINERD")
    disk_size_gb = lookup(each.value, "disk_size_gb", 100)
    disk_type    = lookup(each.value, "disk_type", "pd-ssd")

    # Service account
    service_account = lookup(each.value, "service_account", var.default_service_account)
    oauth_scopes    = lookup(each.value, "oauth_scopes", var.default_oauth_scopes)

    # Metadata
    metadata = merge(
      lookup(each.value, "metadata", {}),
      {
        "disable-legacy-endpoints" = "true"
        "node-pool-type"           = lookup(each.value, "node_pool_type", "general")
        "workload-type"            = lookup(each.value, "workload_type", "mixed")
      }
    )

    # Labels
    labels = merge(
      each.value.labels,
      {
        "node-pool" = each.value.name
      }
    )

    # Taints for specialized workloads
    dynamic "taint" {
      for_each = lookup(each.value, "taints", [])
      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }

    # Tags
    tags = concat(
      var.network_tags,
      lookup(each.value, "additional_tags", []),
      ["gke-node", "container-orchestration"]
    )

    # Preemptible instances
    preemptible = lookup(each.value, "preemptible", false)
    spot        = lookup(each.value, "spot", false)

    # Local SSDs
    dynamic "local_ssd_config" {
      for_each = lookup(each.value, "local_ssd_count", 0) > 0 ? [1] : []
      content {
        count = each.value.local_ssd_count
      }
    }

    # Guest accelerators (GPUs)
    dynamic "guest_accelerator" {
      for_each = lookup(each.value, "guest_accelerators", [])
      content {
        type               = guest_accelerator.value.type
        count              = guest_accelerator.value.count
        gpu_partition_size = lookup(guest_accelerator.value, "gpu_partition_size", null)

        dynamic "gpu_sharing_config" {
          for_each = lookup(guest_accelerator.value, "gpu_sharing_config", null) != null ? [1] : []
          content {
            gpu_sharing_strategy       = guest_accelerator.value.gpu_sharing_config.strategy
            max_shared_clients_per_gpu = guest_accelerator.value.gpu_sharing_config.max_clients
          }
        }

        dynamic "gpu_driver_installation_config" {
          for_each = lookup(guest_accelerator.value, "gpu_driver_version", null) != null ? [1] : []
          content {
            gpu_driver_version = guest_accelerator.value.gpu_driver_version
          }
        }
      }
    }

    # Workload metadata config
    dynamic "workload_metadata_config" {
      for_each = var.enable_workload_identity ? [1] : []
      content {
        mode = "GKE_METADATA"
      }
    }

    # Shielded instance config
    dynamic "shielded_instance_config" {
      for_each = lookup(each.value, "enable_shielded_nodes", var.enable_shielded_nodes) ? [1] : []
      content {
        enable_secure_boot          = lookup(each.value, "enable_secure_boot", true)
        enable_integrity_monitoring = lookup(each.value, "enable_integrity_monitoring", true)
      }
    }

    # Advanced machine features
    dynamic "advanced_machine_features" {
      for_each = lookup(each.value, "enable_nested_virtualization", false) ? [1] : []
      content {
        threads_per_core = lookup(each.value, "threads_per_core", 0)
      }
    }
  }

  # Autoscaling
  dynamic "autoscaling" {
    for_each = lookup(each.value, "enable_autoscaling", var.default_enable_node_autoscaling) ? [1] : []
    content {
      min_node_count       = lookup(each.value, "min_nodes", 0)
      max_node_count       = lookup(each.value, "max_nodes", 10)
      location_policy      = lookup(each.value, "location_policy", "BALANCED")
      total_min_node_count = lookup(each.value, "total_min_nodes", null)
      total_max_node_count = lookup(each.value, "total_max_nodes", null)
    }
  }

  # Node pool management
  management {
    auto_repair  = lookup(each.value, "auto_repair", true)
    auto_upgrade = lookup(each.value, "auto_upgrade", var.enable_auto_upgrade)
  }

  # Upgrade settings
  dynamic "upgrade_settings" {
    for_each = lookup(each.value, "max_surge", null) != null || lookup(each.value, "max_unavailable", null) != null ? [1] : []
    content {
      max_surge       = lookup(each.value, "max_surge", 1)
      max_unavailable = lookup(each.value, "max_unavailable", 0)

      strategy = lookup(each.value, "upgrade_strategy", "SURGE")
      blue_green_node_pool_config {
        node_pool_soak_duration = lookup(each.value, "node_pool_soak_duration", "0s")

        standard_rollout_policy {
          batch_percentage    = lookup(each.value, "batch_percentage", 100)
          batch_node_count    = lookup(each.value, "batch_node_count", null)
          batch_soak_duration = lookup(each.value, "batch_soak_duration", "0s")
        }
      }
    }
  }

  # Network configuration
  dynamic "network_config" {
    for_each = lookup(each.value, "pod_range", null) != null ? [1] : []
    content {
      pod_range            = each.value.pod_range
      pod_ipv4_cidr_block  = lookup(each.value, "pod_ipv4_cidr_block", null)
      enable_private_nodes = lookup(each.value, "enable_private_nodes", var.enable_private_cluster)

      dynamic "pod_cidr_overprovision_config" {
        for_each = lookup(each.value, "pod_cidr_overprovision_disabled", false) ? [1] : []
        content {
          disabled = true
        }
      }
    }
  }

  depends_on = [google_container_cluster.main]
}

# Container Registry Repositories
resource "google_artifact_registry_repository" "repositories" {
  for_each = local.registry_repositories

  repository_id = each.value.full_name
  project       = var.project_id
  location      = var.region
  description   = lookup(each.value, "description", "Container registry for ${each.value.name}")
  format        = "DOCKER"

  mode = lookup(each.value, "mode", "STANDARD_REPOSITORY")

  # Cleanup policies
  dynamic "cleanup_policies" {
    for_each = lookup(each.value, "cleanup_policies", var.default_cleanup_policies)
    content {
      id     = cleanup_policies.value.id
      action = cleanup_policies.value.action

      condition {
        tag_state             = lookup(cleanup_policies.value.condition, "tag_state", "TAGGED")
        tag_prefixes          = lookup(cleanup_policies.value.condition, "tag_prefixes", [])
        version_name_prefixes = lookup(cleanup_policies.value.condition, "version_name_prefixes", [])
        package_name_prefixes = lookup(cleanup_policies.value.condition, "package_name_prefixes", [])
        older_than            = lookup(cleanup_policies.value.condition, "older_than", null)
        newer_than            = lookup(cleanup_policies.value.condition, "newer_than", null)
      }
    }
  }

  # Immutable images
  dynamic "docker_config" {
    for_each = lookup(each.value, "immutable_tags", var.default_immutable_tags) ? [1] : []
    content {
      immutable_tags = true
    }
  }

  labels = each.value.labels
}

# Service Mesh (Istio) Installation
resource "helm_release" "istio_base" {
  count = var.enable_service_mesh && var.use_helm_for_istio ? 1 : 0

  name       = "istio-base"
  repository = "https://istio-release.storage.googleapis.com/charts"
  chart      = "base"
  namespace  = local.service_mesh_config.namespace
  version    = var.istio_version

  create_namespace = true

  values = [
    yamlencode({
      global = {
        meshID  = var.mesh_id
        network = var.cluster_network

        meshConfig = {
          defaultConfig = {
            gatewayTopology = {
              numTrustedProxies = var.num_trusted_proxies
            }
          }
        }
      }
    })
  ]

  depends_on = [google_container_cluster.main]
}

resource "helm_release" "istiod" {
  count = var.enable_service_mesh && var.use_helm_for_istio ? 1 : 0

  name       = "istiod"
  repository = "https://istio-release.storage.googleapis.com/charts"
  chart      = "istiod"
  namespace  = local.service_mesh_config.namespace
  version    = var.istio_version

  values = [
    yamlencode({
      global = {
        meshID  = var.mesh_id
        network = var.cluster_network
      }

      pilot = {
        resources = var.istiod_resources

        env = {
          PILOT_ENABLE_WORKLOAD_ENTRY_AUTOREGISTRATION = var.enable_workload_entry_autoregistration
          PILOT_ENABLE_CROSS_CLUSTER_WORKLOAD_ENTRY    = var.enable_cross_cluster_workload_entry
        }
      }
    })
  ]

  depends_on = [helm_release.istio_base]
}

resource "helm_release" "istio_ingress" {
  count = var.enable_service_mesh && var.use_helm_for_istio && var.enable_istio_ingress ? 1 : 0

  name       = "istio-ingress"
  repository = "https://istio-release.storage.googleapis.com/charts"
  chart      = "gateway"
  namespace  = "istio-ingress"
  version    = var.istio_version

  create_namespace = true

  values = [
    yamlencode({
      service = var.istio_ingress_service_config

      resources = var.istio_ingress_resources

      replicaCount = var.istio_ingress_replicas

      autoscaling = var.istio_ingress_autoscaling
    })
  ]

  depends_on = [helm_release.istiod]
}

# Enable required APIs
resource "google_project_service" "container_api" {
  project = var.project_id
  service = "container.googleapis.com"

  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry_api" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"

  disable_on_destroy = false
}

# Kubernetes namespace creation
resource "kubernetes_namespace" "namespaces" {
  for_each = toset(var.kubernetes_namespaces)

  metadata {
    name = each.value

    labels = merge(
      local.merged_labels,
      {
        "name"       = each.value
        "managed-by" = "terraform"
      }
    )

    annotations = {
      "genesis.platform/created-by" = "container-orchestration-module"
      "genesis.platform/purpose"    = "agent-claude-talk-migration"
    }
  }

  depends_on = [google_container_cluster.main]
}

# Secret management for container orchestration
resource "kubernetes_secret" "registry_secrets" {
  for_each = var.registry_secrets

  metadata {
    name      = each.value.name
    namespace = each.value.namespace

    labels = local.merged_labels
  }

  type = "kubernetes.io/dockerconfigjson"

  data = {
    ".dockerconfigjson" = base64decode(each.value.docker_config_json)
  }

  depends_on = [kubernetes_namespace.namespaces]
}
