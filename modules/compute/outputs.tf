/**
 * Outputs for Compute Module
 */

# VM Instance outputs
output "vm_instances" {
  description = "VM instance information"
  value = {
    templates = { for k, v in google_compute_instance_template.templates : k => {
      id        = v.id
      name      = v.name
      self_link = v.self_link
    } }
  }
}

output "vm_instance_templates" {
  description = "VM instance templates"
  value       = { for k, v in google_compute_instance_template.templates : k => v.self_link }
}

# Instance Group outputs
output "instance_groups" {
  description = "Managed instance groups"
  value = {
    for k, v in google_compute_region_instance_group_manager.managed_groups : k => {
      id                 = v.id
      name               = v.name
      self_link          = v.self_link
      instance_group     = v.instance_group
      target_size        = v.target_size
      base_instance_name = v.base_instance_name
    }
  }
}

output "instance_group_managers" {
  description = "Instance group manager self-links"
  value       = { for k, v in google_compute_region_instance_group_manager.managed_groups : k => v.self_link }
}

# Auto-scaler outputs
output "autoscalers" {
  description = "Auto-scaler information"
  value = {
    for k, v in google_compute_region_autoscaler.autoscalers : k => {
      id     = v.id
      name   = v.name
      target = v.target
    }
  }
}

# Health Check outputs
output "health_checks" {
  description = "Health check information"
  value = {
    for k, v in google_compute_health_check.health_checks : k => {
      id        = v.id
      name      = v.name
      self_link = v.self_link
      type      = v.type
    }
  }
}

output "health_check_self_links" {
  description = "Health check self-links"
  value       = { for k, v in google_compute_health_check.health_checks : k => v.self_link }
}

# GKE Cluster outputs
output "gke_clusters" {
  description = "GKE cluster information"
  value = {
    for k, v in google_container_cluster.clusters : k => {
      id                 = v.id
      name               = v.name
      location           = v.location
      cluster_ipv4_cidr  = v.cluster_ipv4_cidr
      services_ipv4_cidr = v.services_ipv4_cidr
      master_version     = v.master_version
      endpoint           = v.endpoint
      master_auth = {
        cluster_ca_certificate = v.master_auth[0].cluster_ca_certificate
      }
      network    = v.network
      subnetwork = v.subnetwork
    }
  }
  sensitive = true
}

output "gke_cluster_endpoints" {
  description = "GKE cluster endpoints"
  value       = { for k, v in google_container_cluster.clusters : k => v.endpoint }
  sensitive   = true
}

output "gke_cluster_ca_certificates" {
  description = "GKE cluster CA certificates"
  value       = { for k, v in google_container_cluster.clusters : k => v.master_auth[0].cluster_ca_certificate }
  sensitive   = true
}

# GKE Node Pool outputs
output "gke_node_pools" {
  description = "GKE node pool information"
  value = {
    for k, v in google_container_node_pool.node_pools : k => {
      id                  = v.id
      name                = v.name
      location            = v.location
      cluster             = v.cluster
      node_count          = v.node_count
      instance_group_urls = v.instance_group_urls
    }
  }
}

# Cloud Run outputs
output "cloud_run_services" {
  description = "Cloud Run service information"
  value = {
    for k, v in google_cloud_run_v2_service.services : k => {
      id       = v.id
      name     = v.name
      location = v.location
      uri      = v.uri
      status = {
        url        = v.uri
        conditions = v.conditions
      }
      traffic = v.traffic
    }
  }
}

output "cloud_run_urls" {
  description = "Cloud Run service URLs"
  value       = { for k, v in google_cloud_run_v2_service.services : k => v.uri }
}

# Cloud Functions outputs
output "cloud_functions" {
  description = "Cloud Functions information"
  value = {
    for k, v in google_cloudfunctions2_function.functions : k => {
      id       = v.id
      name     = v.name
      location = v.location
      url      = v.url
      state    = v.state
      build_config = {
        runtime     = v.build_config[0].runtime
        entry_point = v.build_config[0].entry_point
      }
      service_config = {
        uri                = v.service_config[0].uri
        available_memory   = v.service_config[0].available_memory
        timeout_seconds    = v.service_config[0].timeout_seconds
        available_cpu      = v.service_config[0].available_cpu
        max_instance_count = v.service_config[0].max_instance_count
        min_instance_count = v.service_config[0].min_instance_count
      }
    }
  }
}

output "cloud_function_urls" {
  description = "Cloud Function URLs"
  value       = { for k, v in google_cloudfunctions2_function.functions : k => v.url }
}

# Comprehensive compute information
output "compute_info" {
  description = "Comprehensive compute information for reference by other modules"
  value = {
    vm_instances = {
      templates = { for k, v in google_compute_instance_template.templates : k => {
        id        = v.id
        name      = v.name
        self_link = v.self_link
      } }
    }
    instance_groups = { for k, v in google_compute_region_instance_group_manager.managed_groups : k => {
      id          = v.id
      name        = v.name
      self_link   = v.self_link
      target_size = v.target_size
    } }
    health_checks = { for k, v in google_compute_health_check.health_checks : k => {
      id        = v.id
      name      = v.name
      self_link = v.self_link
    } }
    gke_clusters = { for k, v in google_container_cluster.clusters : k => {
      id       = v.id
      name     = v.name
      location = v.location
      endpoint = v.endpoint
      network  = v.network
    } }
    cloud_run_services = { for k, v in google_cloud_run_v2_service.services : k => {
      id       = v.id
      name     = v.name
      location = v.location
      uri      = v.uri
    } }
    cloud_functions = { for k, v in google_cloudfunctions2_function.functions : k => {
      id       = v.id
      name     = v.name
      location = v.location
      url      = v.url
    } }
  }
  sensitive = true
}

# Terraform state information
output "terraform_state" {
  description = "Terraform state information for other modules"
  value = {
    module_version = "1.0.0"
    created_at     = timestamp()
    project_id     = var.project_id
    resource_counts = {
      vm_templates       = length(google_compute_instance_template.templates)
      instance_groups    = length(google_compute_region_instance_group_manager.managed_groups)
      health_checks      = length(google_compute_health_check.health_checks)
      gke_clusters       = length(google_container_cluster.clusters)
      gke_node_pools     = length(google_container_node_pool.node_pools)
      cloud_run_services = length(google_cloud_run_v2_service.services)
      cloud_functions    = length(google_cloudfunctions2_function.functions)
    }
  }
}

# Kubeconfig for GKE clusters (use carefully)
output "gke_kubeconfigs" {
  description = "Kubeconfig data for GKE clusters (sensitive)"
  value = {
    for k, v in google_container_cluster.clusters : k => {
      cluster_name           = v.name
      cluster_endpoint       = v.endpoint
      cluster_ca_certificate = v.master_auth[0].cluster_ca_certificate
      cluster_location       = v.location
      project_id             = var.project_id
    }
  }
  sensitive = true
}

# Service URLs for external access
output "service_urls" {
  description = "Public URLs for services"
  value = merge(
    { for k, v in google_cloud_run_v2_service.services : "cloud_run_${k}" => v.uri },
    { for k, v in google_cloudfunctions2_function.functions : "function_${k}" => v.url }
  )
}

# Resource naming patterns
output "resource_naming" {
  description = "Resource naming patterns for consistency"
  value = {
    prefix      = var.name_prefix
    environment = var.environment
    patterns = {
      vm_template    = "${var.name_prefix}-{name}-template"
      instance_group = "${var.name_prefix}-{name}"
      health_check   = "${var.name_prefix}-{name}"
      gke_cluster    = "${var.name_prefix}-{name}"
      cloud_run      = "${var.name_prefix}-{name}"
      cloud_function = "${var.name_prefix}-{name}"
    }
  }
}
