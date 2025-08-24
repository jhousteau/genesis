/**
 * GKE (Google Kubernetes Engine) resources
 */

# GKE Clusters
resource "google_container_cluster" "clusters" {
  for_each = local.gke_clusters

  name     = each.value.full_name
  project  = var.project_id
  location = lookup(each.value, "location", var.default_region)

  description = lookup(each.value, "description", "GKE cluster ${each.value.name}")

  # Network configuration
  network    = lookup(each.value, "network", var.network_id)
  subnetwork = lookup(each.value, "subnetwork", var.subnet_id)

  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1

  # Cluster configuration
  min_master_version = lookup(each.value, "kubernetes_version", null)

  # Private cluster configuration
  dynamic "private_cluster_config" {
    for_each = lookup(each.value, "private_cluster", false) ? [1] : []
    content {
      enable_private_nodes    = true
      enable_private_endpoint = lookup(each.value, "enable_private_endpoint", false)
      master_ipv4_cidr_block  = lookup(each.value, "master_ipv4_cidr_block", "172.16.0.0/28")

      dynamic "master_global_access_config" {
        for_each = lookup(each.value, "enable_master_global_access", false) ? [1] : []
        content {
          enabled = true
        }
      }
    }
  }

  # IP allocation policy for VPC-native clusters
  dynamic "ip_allocation_policy" {
    for_each = lookup(each.value, "enable_ip_alias", true) ? [1] : []
    content {
      cluster_secondary_range_name  = lookup(each.value, "pods_range_name", null)
      services_secondary_range_name = lookup(each.value, "services_range_name", null)
      cluster_ipv4_cidr_block       = lookup(each.value, "pods_cidr_block", null)
      services_ipv4_cidr_block      = lookup(each.value, "services_cidr_block", null)
    }
  }

  # Master authorized networks
  dynamic "master_authorized_networks_config" {
    for_each = length(lookup(each.value, "authorized_networks", [])) > 0 ? [1] : []
    content {
      dynamic "cidr_blocks" {
        for_each = lookup(each.value, "authorized_networks", [])
        content {
          cidr_block   = cidr_blocks.value.cidr_block
          display_name = lookup(cidr_blocks.value, "display_name", null)
        }
      }
    }
  }

  # Network policy
  dynamic "network_policy" {
    for_each = lookup(each.value, "enable_network_policy", false) ? [1] : []
    content {
      enabled  = true
      provider = lookup(each.value, "network_policy_provider", "CALICO")
    }
  }

  # Addons configuration
  addons_config {
    http_load_balancing {
      disabled = !lookup(each.value, "enable_http_load_balancing", true)
    }

    horizontal_pod_autoscaling {
      disabled = !lookup(each.value, "enable_hpa", true)
    }

    network_policy_config {
      disabled = !lookup(each.value, "enable_network_policy", false)
    }

    dynamic "cloudrun_config" {
      for_each = lookup(each.value, "enable_cloud_run_addon", false) ? [1] : []
      content {
        disabled           = false
        load_balancer_type = lookup(each.value, "cloud_run_load_balancer_type", "LOAD_BALANCER_TYPE_EXTERNAL")
      }
    }

    dynamic "istio_config" {
      for_each = lookup(each.value, "enable_istio", false) ? [1] : []
      content {
        disabled = false
        auth     = lookup(each.value, "istio_auth", "AUTH_MUTUAL_TLS")
      }
    }

    dynamic "kalm_config" {
      for_each = lookup(each.value, "enable_kalm", false) ? [1] : []
      content {
        enabled = true
      }
    }

    dynamic "config_connector_config" {
      for_each = lookup(each.value, "enable_config_connector", false) ? [1] : []
      content {
        enabled = true
      }
    }

    dynamic "gce_persistent_disk_csi_driver_config" {
      for_each = lookup(each.value, "enable_gce_pd_csi_driver", true) ? [1] : []
      content {
        enabled = true
      }
    }

    dynamic "gcp_filestore_csi_driver_config" {
      for_each = lookup(each.value, "enable_filestore_csi_driver", false) ? [1] : []
      content {
        enabled = true
      }
    }

    dynamic "gke_backup_agent_config" {
      for_each = lookup(each.value, "enable_backup_agent", false) ? [1] : []
      content {
        enabled = true
      }
    }
  }

  # Cluster autoscaling
  dynamic "cluster_autoscaling" {
    for_each = lookup(each.value, "enable_cluster_autoscaling", false) ? [1] : []
    content {
      enabled = true

      dynamic "resource_limits" {
        for_each = lookup(each.value, "resource_limits", [])
        content {
          resource_type = resource_limits.value.resource_type
          minimum       = lookup(resource_limits.value, "minimum", 0)
          maximum       = resource_limits.value.maximum
        }
      }

      dynamic "auto_provisioning_defaults" {
        for_each = lookup(each.value, "auto_provisioning_defaults", null) != null ? [1] : []
        content {
          oauth_scopes    = lookup(each.value.auto_provisioning_defaults, "oauth_scopes", ["https://www.googleapis.com/auth/cloud-platform"])
          service_account = lookup(each.value.auto_provisioning_defaults, "service_account", null)

          dynamic "management" {
            for_each = lookup(each.value.auto_provisioning_defaults, "management", null) != null ? [1] : []
            content {
              auto_repair  = lookup(each.value.auto_provisioning_defaults.management, "auto_repair", true)
              auto_upgrade = lookup(each.value.auto_provisioning_defaults.management, "auto_upgrade", true)
            }
          }

          dynamic "upgrade_settings" {
            for_each = lookup(each.value.auto_provisioning_defaults, "upgrade_settings", null) != null ? [1] : []
            content {
              max_surge       = lookup(each.value.auto_provisioning_defaults.upgrade_settings, "max_surge", 1)
              max_unavailable = lookup(each.value.auto_provisioning_defaults.upgrade_settings, "max_unavailable", 0)

              dynamic "blue_green_settings" {
                for_each = lookup(each.value.auto_provisioning_defaults.upgrade_settings, "blue_green_settings", null) != null ? [1] : []
                content {
                  node_pool_soak_duration = lookup(each.value.auto_provisioning_defaults.upgrade_settings.blue_green_settings, "node_pool_soak_duration", "0s")

                  standard_rollout_policy {
                    batch_percentage    = lookup(each.value.auto_provisioning_defaults.upgrade_settings.blue_green_settings.standard_rollout_policy, "batch_percentage", null)
                    batch_node_count    = lookup(each.value.auto_provisioning_defaults.upgrade_settings.blue_green_settings.standard_rollout_policy, "batch_node_count", null)
                    batch_soak_duration = lookup(each.value.auto_provisioning_defaults.upgrade_settings.blue_green_settings.standard_rollout_policy, "batch_soak_duration", "0s")
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  # Workload Identity
  dynamic "workload_identity_config" {
    for_each = lookup(each.value, "enable_workload_identity", true) ? [1] : []
    content {
      workload_pool = "${var.project_id}.svc.id.goog"
    }
  }

  # Database encryption
  dynamic "database_encryption" {
    for_each = lookup(each.value, "database_encryption_key", null) != null ? [1] : []
    content {
      state    = "ENCRYPTED"
      key_name = each.value.database_encryption_key
    }
  }

  # Maintenance policy
  dynamic "maintenance_policy" {
    for_each = lookup(each.value, "maintenance_policy", null) != null ? [1] : []
    content {
      dynamic "recurring_window" {
        for_each = lookup(each.value.maintenance_policy, "recurring_window", null) != null ? [1] : []
        content {
          start_time = each.value.maintenance_policy.recurring_window.start_time
          end_time   = each.value.maintenance_policy.recurring_window.end_time
          recurrence = each.value.maintenance_policy.recurring_window.recurrence
        }
      }

      dynamic "daily_maintenance_window" {
        for_each = lookup(each.value.maintenance_policy, "daily_maintenance_window", null) != null ? [1] : []
        content {
          start_time = each.value.maintenance_policy.daily_maintenance_window.start_time
        }
      }

      dynamic "maintenance_exclusion" {
        for_each = lookup(each.value.maintenance_policy, "maintenance_exclusions", [])
        content {
          exclusion_name = maintenance_exclusion.value.exclusion_name
          start_time     = maintenance_exclusion.value.start_time
          end_time       = maintenance_exclusion.value.end_time

          dynamic "exclusion_options" {
            for_each = lookup(maintenance_exclusion.value, "exclusion_options", null) != null ? [1] : []
            content {
              scope = maintenance_exclusion.value.exclusion_options.scope
            }
          }
        }
      }
    }
  }

  # Release channel
  dynamic "release_channel" {
    for_each = lookup(each.value, "release_channel", null) != null ? [1] : []
    content {
      channel = each.value.release_channel
    }
  }

  # Resource usage export
  dynamic "resource_usage_export_config" {
    for_each = lookup(each.value, "resource_usage_export", null) != null ? [1] : []
    content {
      enable_network_egress_metering       = lookup(each.value.resource_usage_export, "enable_network_egress_metering", false)
      enable_resource_consumption_metering = lookup(each.value.resource_usage_export, "enable_resource_consumption_metering", true)

      bigquery_destination {
        dataset_id = each.value.resource_usage_export.bigquery_dataset_id
      }
    }
  }

  # Monitoring configuration
  dynamic "monitoring_config" {
    for_each = lookup(each.value, "enable_monitoring", true) ? [1] : []
    content {
      enable_components = lookup(each.value, "monitoring_components", ["SYSTEM_COMPONENTS"])

      dynamic "managed_prometheus" {
        for_each = lookup(each.value, "enable_managed_prometheus", false) ? [1] : []
        content {
          enabled = true
        }
      }
    }
  }

  # Logging configuration
  dynamic "logging_config" {
    for_each = lookup(each.value, "enable_logging", true) ? [1] : []
    content {
      enable_components = lookup(each.value, "logging_components", ["SYSTEM_COMPONENTS", "WORKLOADS"])
    }
  }

  # Binary authorization
  dynamic "binary_authorization" {
    for_each = lookup(each.value, "enable_binary_authorization", false) ? [1] : []
    content {
      evaluation_mode = lookup(each.value, "binary_authorization_evaluation_mode", "PROJECT_SINGLETON_POLICY_ENFORCE")
    }
  }

  # Cost management
  dynamic "cost_management_config" {
    for_each = lookup(each.value, "enable_cost_management", false) ? [1] : []
    content {
      enabled = true
    }
  }

  # Security posture
  dynamic "security_posture_config" {
    for_each = lookup(each.value, "enable_security_posture", false) ? [1] : []
    content {
      mode               = lookup(each.value, "security_posture_mode", "BASIC")
      vulnerability_mode = lookup(each.value, "security_posture_vulnerability_mode", "VULNERABILITY_DISABLED")
    }
  }

  # Node configuration defaults
  dynamic "node_config" {
    for_each = lookup(each.value, "default_node_config", null) != null ? [1] : []
    content {
      disk_size_gb = lookup(each.value.default_node_config, "disk_size_gb", 100)
      disk_type    = lookup(each.value.default_node_config, "disk_type", "pd-standard")
      image_type   = lookup(each.value.default_node_config, "image_type", "COS_CONTAINERD")
      machine_type = lookup(each.value.default_node_config, "machine_type", "e2-medium")

      oauth_scopes = lookup(each.value.default_node_config, "oauth_scopes", [
        "https://www.googleapis.com/auth/cloud-platform"
      ])

      service_account = lookup(each.value.default_node_config, "service_account", null)

      dynamic "shielded_instance_config" {
        for_each = lookup(each.value.default_node_config, "enable_shielded_nodes", true) ? [1] : []
        content {
          enable_secure_boot          = lookup(each.value.default_node_config, "enable_secure_boot", true)
          enable_integrity_monitoring = lookup(each.value.default_node_config, "enable_integrity_monitoring", true)
        }
      }
    }
  }

  # Enable deletion protection
  deletion_protection = lookup(each.value, "deletion_protection", true)

  # Lifecycle
  lifecycle {
    ignore_changes = [
      node_pool,
      initial_node_count,
    ]
  }
}

# GKE Node Pools
resource "google_container_node_pool" "node_pools" {
  for_each = {
    for pool in flatten([
      for cluster_name, cluster in local.gke_clusters : [
        for pool in lookup(cluster, "node_pools", []) : {
          key          = "${cluster_name}-${pool.name}"
          cluster_name = cluster_name
          pool_config  = pool
          cluster      = cluster
        }
      ]
    ]) : pool.key => pool
  }

  name     = each.value.pool_config.name
  project  = var.project_id
  location = lookup(each.value.cluster, "location", var.default_region)
  cluster  = google_container_cluster.clusters[each.value.cluster_name].name

  # Node count configuration
  initial_node_count = lookup(each.value.pool_config, "initial_node_count", 1)

  dynamic "autoscaling" {
    for_each = lookup(each.value.pool_config, "enable_autoscaling", false) ? [1] : []
    content {
      min_node_count       = lookup(each.value.pool_config, "min_node_count", 1)
      max_node_count       = lookup(each.value.pool_config, "max_node_count", 10)
      location_policy      = lookup(each.value.pool_config, "location_policy", "BALANCED")
      total_min_node_count = lookup(each.value.pool_config, "total_min_node_count", null)
      total_max_node_count = lookup(each.value.pool_config, "total_max_node_count", null)
    }
  }

  # Node configuration
  node_config {
    disk_size_gb = lookup(each.value.pool_config, "disk_size_gb", 100)
    disk_type    = lookup(each.value.pool_config, "disk_type", "pd-standard")
    image_type   = lookup(each.value.pool_config, "image_type", "COS_CONTAINERD")
    machine_type = lookup(each.value.pool_config, "machine_type", "e2-medium")
    spot         = lookup(each.value.pool_config, "spot", false)
    preemptible  = lookup(each.value.pool_config, "preemptible", false)

    # Service account
    service_account = lookup(each.value.pool_config, "service_account", null)
    oauth_scopes = lookup(each.value.pool_config, "oauth_scopes", [
      "https://www.googleapis.com/auth/cloud-platform"
    ])

    # Labels and tags
    labels = merge(
      local.merged_labels,
      lookup(each.value.pool_config, "labels", {}),
      {
        cluster   = each.value.cluster_name
        node_pool = each.value.pool_config.name
      }
    )

    tags = concat(
      lookup(each.value.pool_config, "tags", []),
      [var.environment, "gke-node"]
    )

    # Metadata
    metadata = merge(
      lookup(each.value.pool_config, "metadata", {}),
      {
        "disable-legacy-endpoints" = "true"
      }
    )

    # Shielded instance configuration
    dynamic "shielded_instance_config" {
      for_each = lookup(each.value.pool_config, "enable_shielded_nodes", true) ? [1] : []
      content {
        enable_secure_boot          = lookup(each.value.pool_config, "enable_secure_boot", true)
        enable_integrity_monitoring = lookup(each.value.pool_config, "enable_integrity_monitoring", true)
      }
    }

    # Guest accelerators (GPUs)
    dynamic "guest_accelerator" {
      for_each = lookup(each.value.pool_config, "guest_accelerators", [])
      content {
        type               = guest_accelerator.value.type
        count              = guest_accelerator.value.count
        gpu_partition_size = lookup(guest_accelerator.value, "gpu_partition_size", null)

        dynamic "gpu_sharing_config" {
          for_each = lookup(guest_accelerator.value, "gpu_sharing_config", null) != null ? [1] : []
          content {
            gpu_sharing_strategy       = guest_accelerator.value.gpu_sharing_config.gpu_sharing_strategy
            max_shared_clients_per_gpu = guest_accelerator.value.gpu_sharing_config.max_shared_clients_per_gpu
          }
        }

        dynamic "gpu_driver_installation_config" {
          for_each = lookup(guest_accelerator.value, "gpu_driver_installation_config", null) != null ? [1] : []
          content {
            gpu_driver_version = guest_accelerator.value.gpu_driver_installation_config.gpu_driver_version
          }
        }
      }
    }

    # Taints
    dynamic "taint" {
      for_each = lookup(each.value.pool_config, "taints", [])
      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }

    # Local SSD configuration
    dynamic "local_ssd_config" {
      for_each = lookup(each.value.pool_config, "local_ssd_count", 0) > 0 ? [1] : []
      content {
        local_ssd_count = each.value.pool_config.local_ssd_count
      }
    }

    # Ephemeral storage configuration
    dynamic "ephemeral_storage_local_ssd_config" {
      for_each = lookup(each.value.pool_config, "ephemeral_storage_local_ssd_count", 0) > 0 ? [1] : []
      content {
        local_ssd_count = each.value.pool_config.ephemeral_storage_local_ssd_count
      }
    }

    # GCFS configuration
    dynamic "gcfs_config" {
      for_each = lookup(each.value.pool_config, "enable_gcfs", false) ? [1] : []
      content {
        enabled = true
      }
    }

    # gVisor configuration
    dynamic "gvnic" {
      for_each = lookup(each.value.pool_config, "enable_gvnic", false) ? [1] : []
      content {
        enabled = true
      }
    }

    # Reservation affinity
    dynamic "reservation_affinity" {
      for_each = lookup(each.value.pool_config, "reservation_affinity", null) != null ? [1] : []
      content {
        consume_reservation_type = each.value.pool_config.reservation_affinity.consume_reservation_type
        key                      = lookup(each.value.pool_config.reservation_affinity, "key", null)
        values                   = lookup(each.value.pool_config.reservation_affinity, "values", [])
      }
    }

    # Workload metadata configuration
    dynamic "workload_metadata_config" {
      for_each = lookup(each.value.pool_config, "workload_metadata_mode", null) != null ? [1] : []
      content {
        mode = each.value.pool_config.workload_metadata_mode
      }
    }

    # Kubelet configuration
    dynamic "kubelet_config" {
      for_each = lookup(each.value.pool_config, "kubelet_config", null) != null ? [1] : []
      content {
        cpu_manager_policy   = lookup(each.value.pool_config.kubelet_config, "cpu_manager_policy", "static")
        cpu_cfs_quota        = lookup(each.value.pool_config.kubelet_config, "cpu_cfs_quota", null)
        cpu_cfs_quota_period = lookup(each.value.pool_config.kubelet_config, "cpu_cfs_quota_period", null)
        pod_pids_limit       = lookup(each.value.pool_config.kubelet_config, "pod_pids_limit", null)
      }
    }

    # Linux node configuration
    dynamic "linux_node_config" {
      for_each = lookup(each.value.pool_config, "linux_node_config", null) != null ? [1] : []
      content {
        sysctls     = lookup(each.value.pool_config.linux_node_config, "sysctls", {})
        cgroup_mode = lookup(each.value.pool_config.linux_node_config, "cgroup_mode", "CGROUP_MODE_UNSPECIFIED")
      }
    }

    # Advanced machine features
    dynamic "advanced_machine_features" {
      for_each = lookup(each.value.pool_config, "enable_nested_virtualization", false) ? [1] : []
      content {
        threads_per_core             = lookup(each.value.pool_config, "threads_per_core", null)
        enable_nested_virtualization = true
      }
    }

    # Sole tenant configuration
    dynamic "sole_tenant_config" {
      for_each = lookup(each.value.pool_config, "sole_tenant_config", null) != null ? [1] : []
      content {
        dynamic "node_affinity" {
          for_each = lookup(each.value.pool_config.sole_tenant_config, "node_affinities", [])
          content {
            key      = node_affinity.value.key
            operator = node_affinity.value.operator
            values   = node_affinity.value.values
          }
        }
      }
    }
  }

  # Management configuration
  dynamic "management" {
    for_each = lookup(each.value.pool_config, "management", null) != null ? [1] : []
    content {
      auto_repair  = lookup(each.value.pool_config.management, "auto_repair", true)
      auto_upgrade = lookup(each.value.pool_config.management, "auto_upgrade", true)
    }
  }

  # Upgrade settings
  dynamic "upgrade_settings" {
    for_each = lookup(each.value.pool_config, "upgrade_settings", null) != null ? [1] : []
    content {
      max_surge       = lookup(each.value.pool_config.upgrade_settings, "max_surge", 1)
      max_unavailable = lookup(each.value.pool_config.upgrade_settings, "max_unavailable", 0)
      strategy        = lookup(each.value.pool_config.upgrade_settings, "strategy", "SURGE")

      dynamic "blue_green_settings" {
        for_each = lookup(each.value.pool_config.upgrade_settings, "blue_green_settings", null) != null ? [1] : []
        content {
          node_pool_soak_duration = lookup(each.value.pool_config.upgrade_settings.blue_green_settings, "node_pool_soak_duration", "0s")

          standard_rollout_policy {
            batch_percentage    = lookup(each.value.pool_config.upgrade_settings.blue_green_settings.standard_rollout_policy, "batch_percentage", null)
            batch_node_count    = lookup(each.value.pool_config.upgrade_settings.blue_green_settings.standard_rollout_policy, "batch_node_count", null)
            batch_soak_duration = lookup(each.value.pool_config.upgrade_settings.blue_green_settings.standard_rollout_policy, "batch_soak_duration", "0s")
          }
        }
      }
    }
  }

  # Network configuration
  dynamic "network_config" {
    for_each = lookup(each.value.pool_config, "enable_private_nodes", false) ? [1] : []
    content {
      create_pod_range    = lookup(each.value.pool_config, "create_pod_range", false)
      pod_range           = lookup(each.value.pool_config, "pod_range", null)
      pod_ipv4_cidr_block = lookup(each.value.pool_config, "pod_ipv4_cidr_block", null)

      dynamic "pod_cidr_overprovision_config" {
        for_each = lookup(each.value.pool_config, "pod_cidr_overprovision_config", null) != null ? [1] : []
        content {
          disabled = !each.value.pool_config.pod_cidr_overprovision_config.enabled
        }
      }

      dynamic "network_performance_config" {
        for_each = lookup(each.value.pool_config, "network_performance_config", null) != null ? [1] : []
        content {
          total_egress_bandwidth_tier = each.value.pool_config.network_performance_config.total_egress_bandwidth_tier
        }
      }
    }
  }

  # Placement policy
  dynamic "placement_policy" {
    for_each = lookup(each.value.pool_config, "placement_policy", null) != null ? [1] : []
    content {
      type         = each.value.pool_config.placement_policy.type
      policy_name  = lookup(each.value.pool_config.placement_policy, "policy_name", null)
      tpu_topology = lookup(each.value.pool_config.placement_policy, "tpu_topology", null)
    }
  }

  # Lifecycle
  lifecycle {
    ignore_changes = [initial_node_count]
  }

  depends_on = [google_container_cluster.clusters]
}
