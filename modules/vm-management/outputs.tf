/**
 * VM Management Layer Outputs
 *
 * Output values for agent VM management infrastructure
 */

# Agent VM Template Outputs
output "agent_vm_templates" {
  description = "Agent VM instance template information"
  value = {
    for k, v in google_compute_instance_template.agent_templates : k => {
      id           = v.id
      name         = v.name
      self_link    = v.self_link
      machine_type = v.machine_type
      agent_type   = local.agent_vm_templates[k].agent_type
      labels       = v.labels
    }
  }
}

# Agent Pool Outputs
output "agent_pools" {
  description = "Agent pool (managed instance group) information"
  value = {
    for k, v in google_compute_region_instance_group_manager.agent_pools : k => {
      id                 = v.id
      name               = v.name
      self_link          = v.self_link
      instance_group     = v.instance_group
      target_size        = v.target_size
      agent_type         = local.agent_pools[k].agent_type
      base_instance_name = v.base_instance_name
      region             = v.region
      labels             = local.agent_pools[k].labels
    }
  }
}

# Autoscaler Outputs
output "autoscalers" {
  description = "Autoscaler information for agent pools"
  value = {
    for k, v in google_compute_region_autoscaler.agent_pool_autoscalers : k => {
      id           = v.id
      name         = v.name
      self_link    = v.self_link
      target       = v.target
      region       = v.region
      min_replicas = v.autoscaling_policy[0].min_replicas
      max_replicas = v.autoscaling_policy[0].max_replicas
    }
  }
}

# Health Check Outputs
output "health_checks" {
  description = "Health check information for agent pools"
  value = {
    for k, v in google_compute_health_check.agent_health : k => {
      id                 = v.id
      name               = v.name
      self_link          = v.self_link
      check_interval_sec = v.check_interval_sec
      timeout_sec        = v.timeout_sec
      agent_type         = local.agent_pools[k].agent_type
    }
  }
}

# Firewall Rules Outputs
output "firewall_rules" {
  description = "Firewall rule information for agent VMs"
  value = {
    for k, v in google_compute_firewall.agent_vm_rules : k => {
      id        = v.id
      name      = v.name
      self_link = v.self_link
      direction = v.direction
      priority  = v.priority
      network   = v.network
    }
  }
}

# Summary Outputs for Integration
output "vm_management_summary" {
  description = "Summary of VM management resources for integration"
  value = {
    project_id  = var.project_id
    region      = var.region
    environment = var.environment
    name_prefix = var.name_prefix

    template_count   = length(google_compute_instance_template.agent_templates)
    pool_count       = length(google_compute_region_instance_group_manager.agent_pools)
    autoscaler_count = length(google_compute_region_autoscaler.agent_pool_autoscalers)

    agent_types = distinct([
      for template in local.agent_vm_templates : template.agent_type
    ])

    total_target_instances = sum([
      for pool in google_compute_region_instance_group_manager.agent_pools : pool.target_size
    ])

    health_checks_enabled = var.enable_health_checks
    monitoring_enabled    = var.enable_monitoring
    encryption_enabled    = var.enable_disk_encryption

    network_id = var.network_id
    subnet_id  = var.subnet_id

    created_at = timestamp()
  }
}

# Instance Group URLs for Load Balancer Integration
output "instance_group_urls" {
  description = "Instance group URLs for load balancer backends"
  value = {
    for k, v in google_compute_region_instance_group_manager.agent_pools : k => {
      instance_group_url = v.instance_group
      named_ports = [
        for port in lookup(local.agent_pools[k], "named_ports", var.default_named_ports) : {
          name = port.name
          port = port.port
        }
      ]
    }
  }
}

# Service Account Information
output "service_accounts" {
  description = "Service account information for agent VMs"
  value = {
    default_service_account = var.default_agent_service_account
    scopes                  = var.default_agent_scopes
  }
}

# Network Tags for Firewall Rules
output "network_tags" {
  description = "Network tags applied to agent VMs"
  value = {
    base_tags = var.network_tags
    agent_specific_tags = {
      for k, v in local.agent_vm_templates : k => concat(
        var.network_tags,
        ["agent-${v.agent_type}"]
      )
    }
  }
}

# Resource Labels
output "resource_labels" {
  description = "Resource labels applied to VM management resources"
  value       = local.merged_labels
}

# Agent Configuration
output "agent_configuration" {
  description = "Agent configuration information"
  value = {
    agent_cage_version = var.agent_cage_version
    startup_script_url = var.agent_startup_script_url
    monitoring_enabled = var.enable_monitoring

    default_machine_type = var.default_agent_machine_type
    default_image        = var.default_agent_image
    default_disk_size    = var.default_disk_size_gb

    security_features = {
      disk_encryption      = var.enable_disk_encryption
      secure_boot          = var.enable_secure_boot
      vtpm                 = var.enable_vtpm
      integrity_monitoring = var.enable_integrity_monitoring
    }
  }
}

# Cost Optimization Information
output "cost_optimization" {
  description = "Cost optimization settings and estimates"
  value = {
    preemptible_default = var.default_preemptible
    autoscaling_enabled = var.default_enable_autoscaling

    scaling_config = {
      min_replicas    = var.default_min_replicas
      max_replicas    = var.default_max_replicas
      cpu_target      = var.default_cpu_target
      cooldown_period = var.default_cooldown_period
    }

    estimated_monthly_cost_usd = {
      # Basic cost estimation (actual costs may vary)
      per_vm_standard = 50 # Approximate for e2-standard-2
      total_minimum   = 50 * var.default_min_replicas * length(local.agent_pools)
      total_maximum   = 50 * var.default_max_replicas * length(local.agent_pools)
    }
  }
}
