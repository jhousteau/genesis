/**
 * Compute Module
 *
 * Comprehensive compute infrastructure for GCP
 * Supports VMs, containers (GKE), serverless (Cloud Run, Cloud Functions), auto-scaling
 */

locals {
  # Default labels
  default_labels = {
    managed_by  = "terraform"
    module      = "compute"
    environment = var.environment
  }

  merged_labels = merge(local.default_labels, var.labels)

  # VM instances processing
  vm_instances = {
    for instance in var.vm_instances : instance.name => merge(instance, {
      full_name = "${var.name_prefix}-${instance.name}"
    })
  }

  # Instance groups processing
  instance_groups = {
    for group in var.instance_groups : group.name => merge(group, {
      full_name = "${var.name_prefix}-${group.name}"
    })
  }

  # GKE clusters processing
  gke_clusters = {
    for cluster in var.gke_clusters : cluster.name => merge(cluster, {
      full_name = "${var.name_prefix}-${cluster.name}"
    })
  }

  # Cloud Run services processing
  cloud_run_services = {
    for service in var.cloud_run_services : service.name => merge(service, {
      full_name = "${var.name_prefix}-${service.name}"
    })
  }

  # Cloud Functions processing
  cloud_functions = {
    for function in var.cloud_functions : function.name => merge(function, {
      full_name = "${var.name_prefix}-${function.name}"
    })
  }

  # Load balancers processing
  load_balancers = {
    for lb in var.load_balancers : lb.name => merge(lb, {
      full_name = "${var.name_prefix}-${lb.name}"
    })
  }
}

# VM Instance Templates
resource "google_compute_instance_template" "templates" {
  for_each = local.vm_instances

  name        = "${each.value.full_name}-template"
  project     = var.project_id
  description = lookup(each.value, "description", "Instance template for ${each.value.name}")

  # Machine configuration
  machine_type = each.value.machine_type
  region       = lookup(each.value, "region", var.default_region)

  # Boot disk
  disk {
    source_image = lookup(each.value, "source_image", "debian-cloud/debian-12")
    auto_delete  = lookup(each.value, "auto_delete_disk", true)
    boot         = true
    disk_size_gb = lookup(each.value, "disk_size_gb", 20)
    disk_type    = lookup(each.value, "disk_type", "pd-standard")

    # Disk encryption
    dynamic "disk_encryption_key" {
      for_each = lookup(each.value, "disk_encryption_key", null) != null ? [1] : []
      content {
        kms_key_self_link = each.value.disk_encryption_key
      }
    }
  }

  # Additional disks
  dynamic "disk" {
    for_each = lookup(each.value, "additional_disks", [])
    content {
      auto_delete  = lookup(disk.value, "auto_delete", false)
      boot         = false
      device_name  = disk.value.device_name
      disk_size_gb = disk.value.disk_size_gb
      disk_type    = lookup(disk.value, "disk_type", "pd-standard")
      source       = lookup(disk.value, "source", null)

      dynamic "disk_encryption_key" {
        for_each = lookup(disk.value, "disk_encryption_key", null) != null ? [1] : []
        content {
          kms_key_self_link = disk.value.disk_encryption_key
        }
      }
    }
  }

  # Network interfaces
  dynamic "network_interface" {
    for_each = lookup(each.value, "network_interfaces", [
      {
        network    = var.network_id
        subnetwork = var.subnet_id
      }
    ])
    content {
      network            = lookup(network_interface.value, "network", var.network_id)
      subnetwork         = lookup(network_interface.value, "subnetwork", var.subnet_id)
      subnetwork_project = lookup(network_interface.value, "subnetwork_project", var.project_id)
      network_ip         = lookup(network_interface.value, "network_ip", null)
      nic_type           = lookup(network_interface.value, "nic_type", null)
      stack_type         = lookup(network_interface.value, "stack_type", "IPV4_ONLY")
      queue_count        = lookup(network_interface.value, "queue_count", null)

      dynamic "access_config" {
        for_each = lookup(network_interface.value, "enable_external_ip", false) ? [1] : []
        content {
          nat_ip                 = lookup(network_interface.value, "external_ip", null)
          public_ptr_domain_name = lookup(network_interface.value, "public_ptr_domain_name", null)
          network_tier           = lookup(network_interface.value, "network_tier", "PREMIUM")
        }
      }

      dynamic "ipv6_access_config" {
        for_each = lookup(network_interface.value, "enable_ipv6", false) ? [1] : []
        content {
          public_ptr_domain_name = lookup(network_interface.value, "ipv6_public_ptr_domain_name", null)
          network_tier           = lookup(network_interface.value, "network_tier", "PREMIUM")
        }
      }
    }
  }

  # Service account
  dynamic "service_account" {
    for_each = lookup(each.value, "service_account", null) != null ? [1] : []
    content {
      email  = each.value.service_account.email
      scopes = lookup(each.value.service_account, "scopes", ["cloud-platform"])
    }
  }

  # Metadata
  metadata = merge(
    lookup(each.value, "metadata", {}),
    {
      "enable-oslogin" = lookup(each.value, "enable_os_login", "TRUE")
    }
  )

  # Startup script
  metadata_startup_script = lookup(each.value, "startup_script", null)

  # Tags
  tags = concat(
    lookup(each.value, "network_tags", []),
    [var.environment, "managed-by-terraform"]
  )

  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value, "labels", {}),
    {
      instance_type = "vm"
      template_name = each.value.name
    }
  )

  # Scheduling
  dynamic "scheduling" {
    for_each = lookup(each.value, "scheduling", null) != null ? [1] : []
    content {
      automatic_restart   = lookup(each.value.scheduling, "automatic_restart", true)
      on_host_maintenance = lookup(each.value.scheduling, "on_host_maintenance", "MIGRATE")
      preemptible         = lookup(each.value.scheduling, "preemptible", false)

      dynamic "node_affinities" {
        for_each = lookup(each.value.scheduling, "node_affinities", [])
        content {
          key      = node_affinities.value.key
          operator = node_affinities.value.operator
          values   = node_affinities.value.values
        }
      }
    }
  }

  # Shielded VM
  dynamic "shielded_instance_config" {
    for_each = lookup(each.value, "enable_shielded_vm", true) ? [1] : []
    content {
      enable_secure_boot          = lookup(each.value, "enable_secure_boot", true)
      enable_vtpm                 = lookup(each.value, "enable_vtpm", true)
      enable_integrity_monitoring = lookup(each.value, "enable_integrity_monitoring", true)
    }
  }

  # Guest accelerators (GPUs)
  dynamic "guest_accelerator" {
    for_each = lookup(each.value, "guest_accelerators", [])
    content {
      type  = guest_accelerator.value.type
      count = guest_accelerator.value.count
    }
  }

  # Advanced machine features
  dynamic "advanced_machine_features" {
    for_each = lookup(each.value, "enable_nested_virtualization", false) ? [1] : []
    content {
      enable_nested_virtualization = true
      threads_per_core             = lookup(each.value, "threads_per_core", null)
    }
  }

  # Confidential computing
  dynamic "confidential_instance_config" {
    for_each = lookup(each.value, "enable_confidential_vm", false) ? [1] : []
    content {
      enable_confidential_compute = true
    }
  }

  # Resource policies
  resource_policies = lookup(each.value, "resource_policies", [])

  # Lifecycle
  lifecycle {
    create_before_destroy = true
  }
}

# Managed Instance Groups
resource "google_compute_region_instance_group_manager" "managed_groups" {
  for_each = local.instance_groups

  name    = each.value.full_name
  project = var.project_id
  region  = lookup(each.value, "region", var.default_region)

  base_instance_name = each.value.name
  target_size        = lookup(each.value, "target_size", 1)

  # Instance template
  version {
    instance_template = google_compute_instance_template.templates[each.value.instance_template].id
    name              = "primary"
  }

  # Additional versions for canary deployments
  dynamic "version" {
    for_each = lookup(each.value, "canary_version", null) != null ? [1] : []
    content {
      instance_template = lookup(each.value.canary_version, "instance_template",
      google_compute_instance_template.templates[each.value.instance_template].id)
      name = "canary"
      target_size {
        percent = lookup(each.value.canary_version, "percent", 10)
      }
    }
  }

  # Target pools for load balancing
  target_pools = lookup(each.value, "target_pools", [])

  # Distribution policy
  dynamic "distribution_policy" {
    for_each = lookup(each.value, "distribution_zones", null) != null ? [1] : []
    content {
      zones = each.value.distribution_zones
    }
  }

  # Update policy
  dynamic "update_policy" {
    for_each = lookup(each.value, "update_policy", null) != null ? [1] : []
    content {
      type                    = lookup(each.value.update_policy, "type", "PROACTIVE")
      minimal_action          = lookup(each.value.update_policy, "minimal_action", "REPLACE")
      max_surge_fixed         = lookup(each.value.update_policy, "max_surge_fixed", null)
      max_surge_percent       = lookup(each.value.update_policy, "max_surge_percent", null)
      max_unavailable_fixed   = lookup(each.value.update_policy, "max_unavailable_fixed", null)
      max_unavailable_percent = lookup(each.value.update_policy, "max_unavailable_percent", null)
      min_ready_sec           = lookup(each.value.update_policy, "min_ready_sec", 0)
      replacement_method      = lookup(each.value.update_policy, "replacement_method", "SUBSTITUTE")
    }
  }

  # Auto healing
  dynamic "auto_healing_policies" {
    for_each = lookup(each.value, "health_check", null) != null ? [1] : []
    content {
      health_check      = each.value.health_check
      initial_delay_sec = lookup(each.value, "initial_delay_sec", 300)
    }
  }

  # Named ports
  dynamic "named_port" {
    for_each = lookup(each.value, "named_ports", [])
    content {
      name = named_port.value.name
      port = named_port.value.port
    }
  }

  # Stateful configuration
  dynamic "stateful_disk" {
    for_each = lookup(each.value, "stateful_disks", [])
    content {
      device_name = stateful_disk.value.device_name
      delete_rule = lookup(stateful_disk.value, "delete_rule", "NEVER")
    }
  }

  depends_on = [google_compute_instance_template.templates]
}

# Auto Scaling
resource "google_compute_region_autoscaler" "autoscalers" {
  for_each = {
    for group_name, group in local.instance_groups : group_name => group
    if lookup(group, "enable_autoscaling", false)
  }

  name    = "${each.value.full_name}-autoscaler"
  project = var.project_id
  region  = lookup(each.value, "region", var.default_region)
  target  = google_compute_region_instance_group_manager.managed_groups[each.key].id

  autoscaling_policy {
    max_replicas    = lookup(each.value, "max_replicas", 10)
    min_replicas    = lookup(each.value, "min_replicas", 1)
    cooldown_period = lookup(each.value, "cooldown_period", 60)

    # CPU utilization
    dynamic "cpu_utilization" {
      for_each = lookup(each.value, "cpu_target", null) != null ? [1] : []
      content {
        target            = each.value.cpu_target
        predictive_method = lookup(each.value, "cpu_predictive_method", "NONE")
      }
    }

    # Load balancing utilization
    dynamic "load_balancing_utilization" {
      for_each = lookup(each.value, "load_balancing_target", null) != null ? [1] : []
      content {
        target = each.value.load_balancing_target
      }
    }

    # Custom metrics
    dynamic "metric" {
      for_each = lookup(each.value, "custom_metrics", [])
      content {
        name   = metric.value.name
        target = metric.value.target
        type   = lookup(metric.value, "type", "GAUGE")

        dynamic "single_instance_assignment" {
          for_each = lookup(metric.value, "single_instance_assignment", null) != null ? [1] : []
          content {
            single_instance_assignment = metric.value.single_instance_assignment
          }
        }
      }
    }

    # Scaling schedules
    dynamic "scale_down_control" {
      for_each = lookup(each.value, "scale_down_control", null) != null ? [1] : []
      content {
        max_scaled_down_replicas {
          percent = lookup(each.value.scale_down_control, "max_scaled_down_percent", null)
          fixed   = lookup(each.value.scale_down_control, "max_scaled_down_fixed", null)
        }
        time_window_sec = lookup(each.value.scale_down_control, "time_window_sec", 600)
      }
    }

    dynamic "scale_in_control" {
      for_each = lookup(each.value, "scale_in_control", null) != null ? [1] : []
      content {
        max_scaled_in_replicas {
          percent = lookup(each.value.scale_in_control, "max_scaled_in_percent", null)
          fixed   = lookup(each.value.scale_in_control, "max_scaled_in_fixed", null)
        }
        time_window_sec = lookup(each.value.scale_in_control, "time_window_sec", 600)
      }
    }
  }

  depends_on = [google_compute_region_instance_group_manager.managed_groups]
}

# Health Checks
resource "google_compute_health_check" "health_checks" {
  for_each = {
    for check in var.health_checks : check.name => check
  }

  name    = "${var.name_prefix}-${each.value.name}"
  project = var.project_id

  description         = lookup(each.value, "description", "Health check for ${each.value.name}")
  check_interval_sec  = lookup(each.value, "check_interval_sec", 5)
  timeout_sec         = lookup(each.value, "timeout_sec", 5)
  healthy_threshold   = lookup(each.value, "healthy_threshold", 2)
  unhealthy_threshold = lookup(each.value, "unhealthy_threshold", 3)

  # HTTP health check
  dynamic "http_health_check" {
    for_each = lookup(each.value, "http", null) != null ? [1] : []
    content {
      host               = lookup(each.value.http, "host", null)
      request_path       = lookup(each.value.http, "request_path", "/")
      port               = lookup(each.value.http, "port", 80)
      port_name          = lookup(each.value.http, "port_name", null)
      proxy_header       = lookup(each.value.http, "proxy_header", "NONE")
      port_specification = lookup(each.value.http, "port_specification", "USE_FIXED_PORT")
      response           = lookup(each.value.http, "response", null)
    }
  }

  # HTTPS health check
  dynamic "https_health_check" {
    for_each = lookup(each.value, "https", null) != null ? [1] : []
    content {
      host               = lookup(each.value.https, "host", null)
      request_path       = lookup(each.value.https, "request_path", "/")
      port               = lookup(each.value.https, "port", 443)
      port_name          = lookup(each.value.https, "port_name", null)
      proxy_header       = lookup(each.value.https, "proxy_header", "NONE")
      port_specification = lookup(each.value.https, "port_specification", "USE_FIXED_PORT")
      response           = lookup(each.value.https, "response", null)
    }
  }

  # TCP health check
  dynamic "tcp_health_check" {
    for_each = lookup(each.value, "tcp", null) != null ? [1] : []
    content {
      port               = lookup(each.value.tcp, "port", 80)
      port_name          = lookup(each.value.tcp, "port_name", null)
      proxy_header       = lookup(each.value.tcp, "proxy_header", "NONE")
      port_specification = lookup(each.value.tcp, "port_specification", "USE_FIXED_PORT")
      request            = lookup(each.value.tcp, "request", null)
      response           = lookup(each.value.tcp, "response", null)
    }
  }

  # SSL health check
  dynamic "ssl_health_check" {
    for_each = lookup(each.value, "ssl", null) != null ? [1] : []
    content {
      port               = lookup(each.value.ssl, "port", 443)
      port_name          = lookup(each.value.ssl, "port_name", null)
      proxy_header       = lookup(each.value.ssl, "proxy_header", "NONE")
      port_specification = lookup(each.value.ssl, "port_specification", "USE_FIXED_PORT")
      request            = lookup(each.value.ssl, "request", null)
      response           = lookup(each.value.ssl, "response", null)
    }
  }

  # HTTP2 health check
  dynamic "http2_health_check" {
    for_each = lookup(each.value, "http2", null) != null ? [1] : []
    content {
      host               = lookup(each.value.http2, "host", null)
      request_path       = lookup(each.value.http2, "request_path", "/")
      port               = lookup(each.value.http2, "port", 443)
      port_name          = lookup(each.value.http2, "port_name", null)
      proxy_header       = lookup(each.value.http2, "proxy_header", "NONE")
      port_specification = lookup(each.value.http2, "port_specification", "USE_FIXED_PORT")
      response           = lookup(each.value.http2, "response", null)
    }
  }

  # gRPC health check
  dynamic "grpc_health_check" {
    for_each = lookup(each.value, "grpc", null) != null ? [1] : []
    content {
      port               = lookup(each.value.grpc, "port", 443)
      port_name          = lookup(each.value.grpc, "port_name", null)
      port_specification = lookup(each.value.grpc, "port_specification", "USE_FIXED_PORT")
      grpc_service_name  = lookup(each.value.grpc, "grpc_service_name", null)
    }
  }

  # Logging
  dynamic "log_config" {
    for_each = lookup(each.value, "enable_logging", false) ? [1] : []
    content {
      enable = true
    }
  }
}
