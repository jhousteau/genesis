/**
 * VM Management Layer - Issue #30
 *
 * Comprehensive VM management layer for agent-cage migration
 * Implements PIPES methodology for scalable VM infrastructure
 */

# Terraform version constraints moved to versions.tf

locals {
  # Standard labels following Genesis patterns
  default_labels = {
    managed_by  = "terraform"
    module      = "vm-management"
    environment = var.environment
    component   = "infrastructure"
    purpose     = "agent-cage-migration"
  }

  merged_labels = merge(local.default_labels, var.labels)

  # VM templates for different agent types
  agent_vm_templates = {
    for template in var.agent_vm_templates : template.name => merge(template, {
      full_name = "${var.name_prefix}-agent-${template.name}"
      labels = merge(local.merged_labels, lookup(template, "labels", {}), {
        agent_type = template.agent_type
        vm_role    = "agent-runtime"
      })
    })
  }

  # Instance groups for agent pools
  agent_pools = {
    for pool in var.agent_pools : pool.name => merge(pool, {
      full_name = "${var.name_prefix}-pool-${pool.name}"
      labels = merge(local.merged_labels, lookup(pool, "labels", {}), {
        pool_type    = pool.agent_type
        scaling_mode = lookup(pool, "scaling_mode", "manual")
      })
    })
  }
}

# Agent VM Instance Templates
resource "google_compute_instance_template" "agent_templates" {
  for_each = local.agent_vm_templates

  name_prefix = "${each.value.full_name}-"
  project     = var.project_id
  description = "VM template for ${each.value.agent_type} agents - Genesis agent-cage migration"

  # Machine configuration optimized for agent workloads
  machine_type = lookup(each.value, "machine_type", var.default_agent_machine_type)
  region       = var.region

  # Boot disk with agent runtime environment
  disk {
    source_image = lookup(each.value, "source_image", var.default_agent_image)
    auto_delete  = true
    boot         = true
    disk_size_gb = lookup(each.value, "disk_size_gb", var.default_disk_size_gb)
    disk_type    = lookup(each.value, "disk_type", "pd-ssd")

    # Encryption for agent environments
    dynamic "disk_encryption_key" {
      for_each = var.enable_disk_encryption ? [1] : []
      content {
        kms_key_self_link = var.disk_encryption_key
      }
    }
  }

  # Agent workspace disk
  dynamic "disk" {
    for_each = lookup(each.value, "enable_workspace_disk", true) ? [1] : []
    content {
      auto_delete  = false # Preserve agent workspaces
      boot         = false
      device_name  = "agent-workspace"
      disk_size_gb = lookup(each.value, "workspace_size_gb", 50)
      disk_type    = "pd-ssd"
      disk_name    = "${each.value.full_name}-workspace"

      dynamic "disk_encryption_key" {
        for_each = var.enable_disk_encryption ? [1] : []
        content {
          kms_key_self_link = var.disk_encryption_key
        }
      }
    }
  }

  # Network interface with agent isolation
  network_interface {
    network            = var.network_id
    subnetwork         = var.subnet_id
    subnetwork_project = var.project_id

    # External IP for agent communication (configurable)
    dynamic "access_config" {
      for_each = lookup(each.value, "enable_external_ip", var.default_enable_external_ip) ? [1] : []
      content {
        network_tier = "PREMIUM"
      }
    }
  }

  # Agent service account with workload identity
  service_account {
    email  = lookup(each.value, "service_account_email", var.default_agent_service_account)
    scopes = lookup(each.value, "scopes", var.default_agent_scopes)
  }

  # Agent metadata and configuration
  metadata = merge(
    lookup(each.value, "metadata", {}),
    {
      "enable-oslogin"     = "TRUE"
      "agent-type"         = each.value.agent_type
      "agent-environment"  = var.environment
      "agent-cage-version" = var.agent_cage_version
      "genesis-managed"    = "true"
      "startup-script-url" = var.agent_startup_script_url
    }
  )

  # Agent startup script
  metadata_startup_script = templatefile("${path.module}/scripts/agent-startup.sh", {
    agent_type         = each.value.agent_type
    environment        = var.environment
    project_id         = var.project_id
    agent_cage_version = var.agent_cage_version
    monitoring_enabled = var.enable_monitoring
    custom_config      = lookup(each.value, "custom_config", "{}")
  })

  # Network tags for firewall rules
  tags = concat(
    var.network_tags,
    lookup(each.value, "additional_tags", []),
    [
      "agent-vm",
      "agent-${each.value.agent_type}",
      "environment-${var.environment}",
      "genesis-managed"
    ]
  )

  # Labels for resource management
  labels = each.value.labels

  # Agent VM scheduling - prefer preemptible for cost optimization
  scheduling {
    automatic_restart   = lookup(each.value, "automatic_restart", !lookup(each.value, "preemptible", var.default_preemptible))
    on_host_maintenance = lookup(each.value, "preemptible", var.default_preemptible) ? "TERMINATE" : "MIGRATE"
    preemptible         = lookup(each.value, "preemptible", var.default_preemptible)
  }

  # Shielded VM for security
  shielded_instance_config {
    enable_secure_boot          = var.enable_secure_boot
    enable_vtpm                 = var.enable_vtpm
    enable_integrity_monitoring = var.enable_integrity_monitoring
  }

  # Confidential computing for sensitive agents
  dynamic "confidential_instance_config" {
    for_each = lookup(each.value, "enable_confidential_compute", false) ? [1] : []
    content {
      enable_confidential_compute = true
    }
  }

  # Resource policies
  resource_policies = var.resource_policies

  lifecycle {
    create_before_destroy = true
  }
}

# Agent Pools (Managed Instance Groups)
resource "google_compute_region_instance_group_manager" "agent_pools" {
  for_each = local.agent_pools

  name    = each.value.full_name
  project = var.project_id
  region  = var.region

  base_instance_name = "agent-${each.value.name}"
  target_size        = lookup(each.value, "target_size", var.default_pool_size)

  # Instance template
  version {
    instance_template = google_compute_instance_template.agent_templates[each.value.template_name].id
    name              = "primary"
  }

  # Distribution across zones for HA
  distribution_policy_zones = var.zones

  # Update policy for rolling updates
  update_policy {
    type                  = "PROACTIVE"
    minimal_action        = "REPLACE"
    max_surge_fixed       = lookup(each.value, "max_surge", 1)
    max_unavailable_fixed = lookup(each.value, "max_unavailable", 0)
    # min_ready_sec deprecated - use instance health checks instead
    replacement_method    = "SUBSTITUTE"
  }

  # Health check integration
  dynamic "auto_healing_policies" {
    for_each = var.enable_health_checks ? [1] : []
    content {
      health_check      = google_compute_health_check.agent_health[each.key].id
      initial_delay_sec = lookup(each.value, "health_check_initial_delay", 300)
    }
  }

  # Named ports for load balancing
  dynamic "named_port" {
    for_each = lookup(each.value, "named_ports", var.default_named_ports)
    content {
      name = named_port.value.name
      port = named_port.value.port
    }
  }

  depends_on = [google_compute_instance_template.agent_templates]
}

# Auto Scaling for Agent Pools
resource "google_compute_region_autoscaler" "agent_pool_autoscalers" {
  for_each = {
    for pool_name, pool in local.agent_pools : pool_name => pool
    if lookup(pool, "enable_autoscaling", var.default_enable_autoscaling)
  }

  name    = "${each.value.full_name}-autoscaler"
  project = var.project_id
  region  = var.region
  target  = google_compute_region_instance_group_manager.agent_pools[each.key].id

  autoscaling_policy {
    max_replicas    = lookup(each.value, "max_replicas", var.default_max_replicas)
    min_replicas    = lookup(each.value, "min_replicas", var.default_min_replicas)
    cooldown_period = lookup(each.value, "cooldown_period", var.default_cooldown_period)

    # CPU-based scaling
    cpu_utilization {
      target            = lookup(each.value, "cpu_target", var.default_cpu_target)
      predictive_method = var.enable_predictive_autoscaling ? "OPTIMIZE_AVAILABILITY" : "NONE"
    }

    # Custom metrics for agent workload scaling
    dynamic "metric" {
      for_each = lookup(each.value, "custom_metrics", var.default_custom_metrics)
      content {
        name   = metric.value.name
        target = metric.value.target
        type   = metric.value.type
      }
    }

    # Scale down control (deprecated - use scaling policy instead)
    # max_scaled_down_replicas and time_window_sec managed by autoscaling policy
  }

  depends_on = [google_compute_region_instance_group_manager.agent_pools]
}

# Health Checks for Agent VMs
resource "google_compute_health_check" "agent_health" {
  for_each = var.enable_health_checks ? local.agent_pools : {}

  name    = "${each.value.full_name}-health"
  project = var.project_id

  description         = "Health check for ${each.value.agent_type} agent pool"
  check_interval_sec  = var.health_check_interval
  timeout_sec         = var.health_check_timeout
  healthy_threshold   = var.health_check_healthy_threshold
  unhealthy_threshold = var.health_check_unhealthy_threshold

  # HTTP health check for agent status endpoint
  http_health_check {
    port         = lookup(each.value, "health_port", var.default_health_port)
    request_path = lookup(each.value, "health_path", var.default_health_path)
    host         = lookup(each.value, "health_host", "")
  }

  log_config {
    enable = var.enable_health_check_logging
  }
}

# VM Management Firewall Rules
resource "google_compute_firewall" "agent_vm_rules" {
  for_each = var.firewall_rules

  name    = "${var.name_prefix}-agent-${each.key}"
  network = var.network_id
  project = var.project_id

  description = each.value.description
  direction   = each.value.direction
  priority    = lookup(each.value, "priority", 1000)

  # Source/target configuration
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

  source_ranges      = lookup(each.value, "source_ranges", null)
  destination_ranges = lookup(each.value, "destination_ranges", null)
  source_tags        = lookup(each.value, "source_tags", null)
  target_tags        = lookup(each.value, "target_tags", null)

  log_config {
    metadata = var.enable_firewall_logging ? "INCLUDE_ALL_METADATA" : "EXCLUDE_ALL_METADATA"
  }
}
