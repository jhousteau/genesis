/**
 * Container Orchestration Outputs
 *
 * Output values for container orchestration infrastructure
 */

# GKE Cluster Outputs
output "cluster" {
  description = "GKE cluster information"
  value = {
    id                     = google_container_cluster.main.id
    name                   = google_container_cluster.main.name
    location               = google_container_cluster.main.location
    zone                   = google_container_cluster.main.location
    region                 = var.region
    endpoint               = google_container_cluster.main.endpoint
    master_version         = google_container_cluster.main.master_version
    node_version           = google_container_cluster.main.node_version
    cluster_ca_certificate = base64decode(google_container_cluster.main.master_auth.0.cluster_ca_certificate)

    # Network configuration
    network                       = google_container_cluster.main.network
    subnetwork                    = google_container_cluster.main.subnetwork
    cluster_secondary_range_name  = google_container_cluster.main.ip_allocation_policy.0.cluster_secondary_range_name
    services_secondary_range_name = google_container_cluster.main.ip_allocation_policy.0.services_secondary_range_name

    # Private cluster configuration
    private_cluster_config = var.enable_private_cluster ? {
      enable_private_nodes    = google_container_cluster.main.private_cluster_config.0.enable_private_nodes
      enable_private_endpoint = google_container_cluster.main.private_cluster_config.0.enable_private_endpoint
      master_ipv4_cidr_block  = google_container_cluster.main.private_cluster_config.0.master_ipv4_cidr_block
    } : null

    # Workload identity
    workload_identity_config = var.enable_workload_identity ? {
      workload_pool = google_container_cluster.main.workload_identity_config.0.workload_pool
    } : null

    # Labels and metadata
    resource_labels = google_container_cluster.main.resource_labels
    self_link       = google_container_cluster.main.self_link
  }

  sensitive = true
}

# Node Pools Outputs
output "node_pools" {
  description = "GKE node pool information"
  value = {
    for k, v in google_container_node_pool.pools : k => {
      id                          = v.id
      name                        = v.name
      location                    = v.location
      cluster                     = v.cluster
      initial_node_count          = v.initial_node_count
      node_count                  = v.node_count
      version                     = v.version
      instance_group_urls         = v.instance_group_urls
      managed_instance_group_urls = v.managed_instance_group_urls

      # Node configuration
      node_config = {
        machine_type    = v.node_config.0.machine_type
        disk_size_gb    = v.node_config.0.disk_size_gb
        disk_type       = v.node_config.0.disk_type
        image_type      = v.node_config.0.image_type
        labels          = v.node_config.0.labels
        tags            = v.node_config.0.tags
        service_account = v.node_config.0.service_account
        oauth_scopes    = v.node_config.0.oauth_scopes
        preemptible     = v.node_config.0.preemptible
        spot            = v.node_config.0.spot
      }

      # Autoscaling configuration
      autoscaling = length(v.autoscaling) > 0 ? {
        min_node_count  = v.autoscaling.0.min_node_count
        max_node_count  = v.autoscaling.0.max_node_count
        location_policy = v.autoscaling.0.location_policy
      } : null

      # Management configuration
      management = {
        auto_repair  = v.management.0.auto_repair
        auto_upgrade = v.management.0.auto_upgrade
      }

      # Network configuration
      node_pool_type = local.node_pools[k].node_pool_type
      workload_type  = local.node_pools[k].workload_type
    }
  }
}

# Container Registry Outputs
output "container_repositories" {
  description = "Container registry repository information"
  value = {
    for k, v in google_artifact_registry_repository.repositories : k => {
      id            = v.id
      name          = v.name
      repository_id = v.repository_id
      location      = v.location
      format        = v.format
      description   = v.description

      # Repository URLs
      repository_url = "${v.location}-docker.pkg.dev/${var.project_id}/${v.repository_id}"
      docker_config = {
        registry   = "${v.location}-docker.pkg.dev"
        repository = "${var.project_id}/${v.repository_id}"
      }

      labels = v.labels
    }
  }
}

# Service Mesh Outputs
output "service_mesh" {
  description = "Service mesh (Istio) configuration and status"
  value = var.enable_service_mesh ? {
    enabled             = true
    installation_method = var.use_helm_for_istio ? "helm" : "gcp-managed"
    namespace           = local.service_mesh_config.namespace
    istio_version       = var.istio_version
    mesh_id             = var.mesh_id
    cluster_network     = var.cluster_network

    # Helm release information
    istio_base = var.use_helm_for_istio ? {
      name      = helm_release.istio_base[0].name
      namespace = helm_release.istio_base[0].namespace
      version   = helm_release.istio_base[0].version
      status    = helm_release.istio_base[0].status
    } : null

    istiod = var.use_helm_for_istio ? {
      name      = helm_release.istiod[0].name
      namespace = helm_release.istiod[0].namespace
      version   = helm_release.istiod[0].version
      status    = helm_release.istiod[0].status
    } : null

    istio_ingress = var.use_helm_for_istio && var.enable_istio_ingress ? {
      name      = helm_release.istio_ingress[0].name
      namespace = helm_release.istio_ingress[0].namespace
      version   = helm_release.istio_ingress[0].version
      status    = helm_release.istio_ingress[0].status
    } : null
    } : {
    enabled             = false
    installation_method = null
    namespace           = null
    istio_version       = null
    mesh_id             = null
    cluster_network     = null
    istio_base          = null
    istiod              = null
    istio_ingress       = null
  }
}

# Kubernetes Configuration Outputs
output "kubernetes_config" {
  description = "Kubernetes cluster connection configuration"
  value = {
    # Connection details
    host = "https://${google_container_cluster.main.endpoint}"
    # Note: username/password authentication deprecated - use service accounts and tokens instead

    # Certificate data
    cluster_ca_certificate = google_container_cluster.main.master_auth.0.cluster_ca_certificate
    client_certificate     = google_container_cluster.main.master_auth.0.client_certificate
    client_key             = google_container_cluster.main.master_auth.0.client_key

    # kubectl configuration command
    kubectl_config_command = var.regional_cluster ? "gcloud container clusters get-credentials ${google_container_cluster.main.name} --region ${var.region} --project ${var.project_id}" : "gcloud container clusters get-credentials ${google_container_cluster.main.name} --zone ${var.zone} --project ${var.project_id}"
  }

  sensitive = true
}

# Namespaces Outputs
output "kubernetes_namespaces" {
  description = "Created Kubernetes namespaces"
  value = {
    for k, v in kubernetes_namespace.namespaces : k => {
      name        = v.metadata.0.name
      uid         = v.metadata.0.uid
      labels      = v.metadata.0.labels
      annotations = v.metadata.0.annotations
    }
  }
}

# Security Configuration Outputs
output "security_config" {
  description = "Security configuration summary"
  value = {
    private_cluster      = var.enable_private_cluster
    private_endpoint     = var.enable_private_endpoint
    workload_identity    = var.enable_workload_identity
    binary_authorization = var.enable_binary_authorization
    database_encryption  = var.enable_database_encryption
    shielded_nodes       = var.enable_shielded_nodes
    network_policy       = var.enable_network_policy
    pod_security_policy  = var.enable_pod_security_policy
    security_posture     = var.enable_security_posture

    master_authorized_networks = var.master_authorized_networks

    # Encryption details
    database_encryption_key = var.enable_database_encryption ? var.database_encryption_key : null
  }
}

# Monitoring and Logging Outputs
output "observability_config" {
  description = "Monitoring and logging configuration"
  value = {
    monitoring_components = var.monitoring_components
    logging_components    = var.logging_components

    managed_prometheus              = var.enable_managed_prometheus
    advanced_datapath_observability = var.enable_advanced_datapath_observability
    resource_usage_export           = var.enable_resource_usage_export

    # BigQuery export configuration
    resource_usage_bigquery_dataset = var.enable_resource_usage_export ? var.resource_usage_bigquery_dataset : null
  }
}

# Cost Optimization Outputs
output "cost_optimization" {
  description = "Cost optimization settings and estimates"
  value = {
    autopilot_enabled      = var.enable_autopilot
    cluster_autoscaling    = var.enable_cluster_autoscaling
    node_auto_provisioning = var.enable_node_auto_provisioning

    # Node pool cost settings
    node_pool_settings = {
      for k, v in local.node_pools : k => {
        preemptible  = lookup(v, "preemptible", false)
        spot         = lookup(v, "spot", false)
        machine_type = lookup(v, "machine_type", "e2-medium")
        autoscaling = {
          enabled   = lookup(v, "enable_autoscaling", var.default_enable_node_autoscaling)
          min_nodes = lookup(v, "min_nodes", 0)
          max_nodes = lookup(v, "max_nodes", 10)
        }
      }
    }

    # Estimated monthly costs (approximations)
    estimated_monthly_cost_usd = {
      cluster_management = var.enable_autopilot ? 0 : 73.00 # Standard cluster management fee

      # Basic node cost estimation per node pool
      node_pools = {
        for k, v in local.node_pools : k => {
          machine_type = lookup(v, "machine_type", "e2-medium")
          min_nodes    = lookup(v, "min_nodes", 0)
          max_nodes    = lookup(v, "max_nodes", 10)
          preemptible  = lookup(v, "preemptible", false)
          # Rough cost estimation - actual costs may vary significantly
          estimated_per_node_monthly = lookup(v, "preemptible", false) ? 15.0 : 50.0
          estimated_min_monthly      = (lookup(v, "min_nodes", 0) * (lookup(v, "preemptible", false) ? 15.0 : 50.0))
          estimated_max_monthly      = (lookup(v, "max_nodes", 10) * (lookup(v, "preemptible", false) ? 15.0 : 50.0))
        }
      }
    }
  }
}

# Integration Points Outputs
output "integration_endpoints" {
  description = "Integration endpoints for other services"
  value = {
    # Container registry endpoints
    container_registries = {
      for k, v in google_artifact_registry_repository.repositories : k => {
        endpoint   = "${v.location}-docker.pkg.dev"
        repository = "${var.project_id}/${v.repository_id}"
        full_url   = "${v.location}-docker.pkg.dev/${var.project_id}/${v.repository_id}"
      }
    }

    # Kubernetes API endpoint
    kubernetes_api = {
      endpoint     = "https://${google_container_cluster.main.endpoint}"
      cluster_name = google_container_cluster.main.name
      location     = google_container_cluster.main.location
    }

    # Service mesh endpoints
    service_mesh_endpoints = var.enable_service_mesh ? {
      istio_system_namespace = local.service_mesh_config.namespace
      mesh_id                = var.mesh_id
      cluster_network        = var.cluster_network
    } : null

    # Load balancer integration points
    load_balancer_backends = {
      for k, v in google_container_node_pool.pools : k => {
        instance_group_urls         = v.instance_group_urls
        managed_instance_group_urls = v.managed_instance_group_urls
      }
    }
  }
}

# Operational Information
output "operational_info" {
  description = "Operational information for cluster management"
  value = {
    project_id  = var.project_id
    environment = var.environment
    name_prefix = var.name_prefix

    cluster_info = {
      name         = google_container_cluster.main.name
      location     = google_container_cluster.main.location
      network      = google_container_cluster.main.network
      subnetwork   = google_container_cluster.main.subnetwork
      is_regional  = var.regional_cluster
      is_autopilot = var.enable_autopilot
    }

    node_pools_count   = length(google_container_node_pool.pools)
    repositories_count = length(google_artifact_registry_repository.repositories)
    namespaces_count   = length(kubernetes_namespace.namespaces)

    maintenance_policy = var.maintenance_policy

    resource_labels = local.merged_labels

    created_at = timestamp()
  }
}

# CLI Integration Commands
output "cli_commands" {
  description = "Useful CLI commands for cluster management"
  value = {
    # kubectl configuration
    configure_kubectl = var.regional_cluster ? "gcloud container clusters get-credentials ${google_container_cluster.main.name} --region ${var.region} --project ${var.project_id}" : "gcloud container clusters get-credentials ${google_container_cluster.main.name} --zone ${var.zone} --project ${var.project_id}"

    # Container registry authentication
    configure_docker = "gcloud auth configure-docker ${var.region}-docker.pkg.dev"

    # Cluster information
    cluster_info = "kubectl cluster-info"

    # Node information
    get_nodes = "kubectl get nodes -o wide"

    # Service mesh commands (if enabled)
    istio_commands = var.enable_service_mesh ? {
      check_installation = "kubectl get pods -n ${local.service_mesh_config.namespace}"
      istio_version      = "kubectl get pods -n ${local.service_mesh_config.namespace} -o jsonpath='{.items[0].spec.containers[0].image}'"
    } : null

    # Monitoring commands
    monitoring_commands = {
      check_system_pods = "kubectl get pods -n kube-system"
      check_monitoring  = "kubectl get pods -n gmp-system" # For managed Prometheus
      view_logs         = "kubectl logs -n kube-system -l component=kube-apiserver"
    }
  }
}

# Summary Output
output "container_orchestration_summary" {
  description = "Complete summary of container orchestration deployment"
  value = {
    cluster = {
      name      = google_container_cluster.main.name
      location  = google_container_cluster.main.location
      endpoint  = google_container_cluster.main.endpoint
      version   = google_container_cluster.main.master_version
      autopilot = var.enable_autopilot
    }

    node_pools   = length(google_container_node_pool.pools)
    repositories = length(google_artifact_registry_repository.repositories)
    namespaces   = length(kubernetes_namespace.namespaces)

    features = {
      private_cluster   = var.enable_private_cluster
      workload_identity = var.enable_workload_identity
      service_mesh      = var.enable_service_mesh
      binary_auth       = var.enable_binary_authorization
      network_policy    = var.enable_network_policy
    }

    cost_optimization = {
      autoscaling = var.enable_cluster_autoscaling
      preemptible_nodes = length([
        for k, v in local.node_pools : k
        if lookup(v, "preemptible", false) || lookup(v, "spot", false)
      ])
    }

    security = {
      shielded_nodes   = var.enable_shielded_nodes
      encryption       = var.enable_database_encryption
      private_endpoint = var.enable_private_endpoint
    }

    created_at      = timestamp()
    resource_labels = local.merged_labels
  }
}
