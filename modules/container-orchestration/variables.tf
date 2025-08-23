/**
 * Container Orchestration Variables
 *
 * Configuration variables for container orchestration infrastructure
 */

# Core Configuration
variable "project_id" {
  description = "GCP project ID for container resources"
  type        = string
}

variable "region" {
  description = "GCP region for container resources"
  type        = string
}

variable "zone" {
  description = "GCP zone for zonal cluster (if not regional)"
  type        = string
  default     = null
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "genesis"
}

variable "labels" {
  description = "Additional labels to apply to all resources"
  type        = map(string)
  default     = {}
}

# Network Configuration
variable "network_id" {
  description = "VPC network ID for GKE cluster"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for GKE cluster"
  type        = string
}

variable "pods_secondary_range_name" {
  description = "Name of secondary range for pods"
  type        = string
}

variable "services_secondary_range_name" {
  description = "Name of secondary range for services"
  type        = string
}

variable "additional_pod_ranges" {
  description = "Additional pod secondary ranges"
  type        = list(string)
  default     = []
}

variable "network_tags" {
  description = "Network tags to apply to GKE nodes"
  type        = list(string)
  default     = ["gke-node", "container-orchestration"]
}

# GKE Cluster Configuration
variable "gke_cluster_config" {
  description = "GKE cluster configuration"
  type = object({
    name        = string
    description = optional(string)
    labels      = optional(map(string), {})
  })
}

variable "regional_cluster" {
  description = "Create regional cluster (vs zonal)"
  type        = bool
  default     = true
}

variable "enable_autopilot" {
  description = "Enable GKE Autopilot mode"
  type        = bool
  default     = false
}

# Private Cluster Configuration
variable "enable_private_cluster" {
  description = "Enable private GKE cluster"
  type        = bool
  default     = true
}

variable "enable_private_endpoint" {
  description = "Enable private endpoint for GKE cluster"
  type        = bool
  default     = false
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for GKE master"
  type        = string
  default     = "172.16.0.0/28"
}

variable "enable_master_global_access" {
  description = "Enable global access to GKE master"
  type        = bool
  default     = false
}

variable "master_authorized_networks" {
  description = "List of authorized networks for GKE master access"
  type = list(object({
    cidr_block   = string
    display_name = optional(string)
  }))
  default = []
}

# Node Pools Configuration
variable "node_pools" {
  description = "GKE node pool configurations"
  type = list(object({
    name               = string
    machine_type       = optional(string, "e2-medium")
    image_type         = optional(string, "COS_CONTAINERD")
    disk_size_gb       = optional(number, 100)
    disk_type          = optional(string, "pd-ssd")
    initial_node_count = optional(number, 1)
    service_account    = optional(string)
    oauth_scopes       = optional(list(string))
    metadata           = optional(map(string), {})
    labels             = optional(map(string), {})
    node_pool_type     = optional(string, "general")
    workload_type      = optional(string, "mixed")
    preemptible        = optional(bool, false)
    spot               = optional(bool, false)
    local_ssd_count    = optional(number, 0)
    additional_tags    = optional(list(string), [])
    kubernetes_version = optional(string)

    # Taints for specialized workloads
    taints = optional(list(object({
      key    = string
      value  = string
      effect = string
    })), [])

    # GPU configuration
    guest_accelerators = optional(list(object({
      type               = string
      count              = number
      gpu_partition_size = optional(string)
      gpu_driver_version = optional(string)
      gpu_sharing_config = optional(object({
        strategy    = string
        max_clients = number
      }))
    })), [])

    # Autoscaling
    enable_autoscaling = optional(bool, true)
    min_nodes          = optional(number, 0)
    max_nodes          = optional(number, 10)
    total_min_nodes    = optional(number)
    total_max_nodes    = optional(number)
    location_policy    = optional(string, "BALANCED")

    # Node management
    auto_repair  = optional(bool, true)
    auto_upgrade = optional(bool, true)

    # Upgrade settings
    max_surge               = optional(number, 1)
    max_unavailable         = optional(number, 0)
    upgrade_strategy        = optional(string, "SURGE")
    node_pool_soak_duration = optional(string, "0s")
    batch_percentage        = optional(number, 100)
    batch_node_count        = optional(number)
    batch_soak_duration     = optional(string, "0s")

    # Network configuration
    pod_range                       = optional(string)
    pod_ipv4_cidr_block             = optional(string)
    enable_private_nodes            = optional(bool)
    pod_cidr_overprovision_disabled = optional(bool, false)

    # Security features
    enable_shielded_nodes        = optional(bool, true)
    enable_secure_boot           = optional(bool, true)
    enable_integrity_monitoring  = optional(bool, true)
    enable_nested_virtualization = optional(bool, false)
    threads_per_core             = optional(number, 0)
  }))
  default = []
}

# Service Account Configuration
variable "default_service_account" {
  description = "Default service account for GKE nodes"
  type        = string
  default     = null
}

variable "default_oauth_scopes" {
  description = "Default OAuth scopes for GKE nodes"
  type        = list(string)
  default = [
    "https://www.googleapis.com/auth/cloud-platform"
  ]
}

# Cluster Features
variable "enable_workload_identity" {
  description = "Enable Workload Identity"
  type        = bool
  default     = true
}

variable "enable_http_load_balancing" {
  description = "Enable HTTP load balancing addon"
  type        = bool
  default     = true
}

variable "enable_horizontal_pod_autoscaling" {
  description = "Enable horizontal pod autoscaling addon"
  type        = bool
  default     = true
}

variable "enable_network_policy" {
  description = "Enable network policy addon"
  type        = bool
  default     = true
}

variable "enable_istio_addon" {
  description = "Enable Istio addon (deprecated, use service mesh instead)"
  type        = bool
  default     = false
}

variable "enable_dns_cache" {
  description = "Enable DNS cache addon"
  type        = bool
  default     = true
}

variable "enable_gce_pd_csi_driver" {
  description = "Enable GCE persistent disk CSI driver"
  type        = bool
  default     = true
}

variable "enable_filestore_csi_driver" {
  description = "Enable Filestore CSI driver"
  type        = bool
  default     = false
}

variable "enable_backup_agent" {
  description = "Enable GKE backup agent"
  type        = bool
  default     = false
}

# Security Configuration
variable "enable_binary_authorization" {
  description = "Enable Binary Authorization"
  type        = bool
  default     = false
}

variable "binary_authorization_evaluation_mode" {
  description = "Binary Authorization evaluation mode"
  type        = string
  default     = "PROJECT_SINGLETON_POLICY_ENFORCE"
}

variable "enable_database_encryption" {
  description = "Enable database encryption with CMEK"
  type        = bool
  default     = false
}

variable "database_encryption_key" {
  description = "KMS key for database encryption"
  type        = string
  default     = null
}

variable "enable_pod_security_policy" {
  description = "Enable Pod Security Policy (deprecated)"
  type        = bool
  default     = false
}

variable "enable_shielded_nodes" {
  description = "Enable Shielded GKE nodes by default"
  type        = bool
  default     = true
}

# Autoscaling Configuration
variable "enable_cluster_autoscaling" {
  description = "Enable cluster autoscaling"
  type        = bool
  default     = true
}

variable "cluster_autoscaling_resource_limits" {
  description = "Resource limits for cluster autoscaling"
  type = list(object({
    resource_type = string
    minimum       = number
    maximum       = number
  }))
  default = [
    {
      resource_type = "cpu"
      minimum       = 1
      maximum       = 100
    },
    {
      resource_type = "memory"
      minimum       = 1
      maximum       = 1000
    }
  ]
}

variable "enable_node_auto_provisioning" {
  description = "Enable node auto-provisioning"
  type        = bool
  default     = false
}

variable "auto_provisioning_disk_size" {
  description = "Disk size for auto-provisioned nodes"
  type        = number
  default     = 100
}

variable "auto_provisioning_disk_type" {
  description = "Disk type for auto-provisioned nodes"
  type        = string
  default     = "pd-ssd"
}

variable "auto_provisioning_image_type" {
  description = "Image type for auto-provisioned nodes"
  type        = string
  default     = "COS_CONTAINERD"
}

variable "enable_vertical_pod_autoscaling" {
  description = "Enable Vertical Pod Autoscaling"
  type        = bool
  default     = false
}

variable "default_enable_node_autoscaling" {
  description = "Enable node autoscaling by default for node pools"
  type        = bool
  default     = true
}

variable "enable_auto_upgrade" {
  description = "Enable auto-upgrade for nodes"
  type        = bool
  default     = true
}

# Maintenance Configuration
variable "maintenance_policy" {
  description = "Cluster maintenance policy"
  type = object({
    start_time = string
    end_time   = string
    recurrence = string
    exclusions = optional(list(object({
      name       = string
      start_time = string
      end_time   = string
      scope      = string
    })), [])
  })
  default = null
}

# Monitoring and Logging
variable "monitoring_components" {
  description = "List of monitoring components to enable"
  type        = list(string)
  default = [
    "SYSTEM_COMPONENTS",
    "WORKLOADS",
    "APISERVER",
    "CONTROLLER_MANAGER",
    "SCHEDULER"
  ]
}

variable "enable_managed_prometheus" {
  description = "Enable managed Prometheus"
  type        = bool
  default     = false
}

variable "enable_advanced_datapath_observability" {
  description = "Enable advanced datapath observability"
  type        = bool
  default     = false
}

variable "enable_datapath_v2" {
  description = "Enable Datapath V2"
  type        = bool
  default     = false
}

variable "logging_components" {
  description = "List of logging components to enable"
  type        = list(string)
  default = [
    "SYSTEM_COMPONENTS",
    "WORKLOADS",
    "APISERVER"
  ]
}

# Security Posture
variable "enable_security_posture" {
  description = "Enable security posture management"
  type        = bool
  default     = false
}

variable "security_posture_mode" {
  description = "Security posture mode"
  type        = string
  default     = "BASIC"
}

variable "security_posture_vulnerability_mode" {
  description = "Security posture vulnerability mode"
  type        = string
  default     = "VULNERABILITY_BASIC"
}

# Notification Configuration
variable "notification_config" {
  description = "Notification configuration for cluster events"
  type = object({
    pubsub_topic = string
    event_types  = list(string)
  })
  default = null
}

# Resource Usage Export
variable "enable_resource_usage_export" {
  description = "Enable resource usage export to BigQuery"
  type        = bool
  default     = false
}

variable "resource_usage_bigquery_dataset" {
  description = "BigQuery dataset for resource usage export"
  type        = string
  default     = null
}

# Container Registry Configuration
variable "container_repositories" {
  description = "Container registry repository configurations"
  type = list(object({
    name           = string
    description    = optional(string)
    mode           = optional(string, "STANDARD_REPOSITORY")
    immutable_tags = optional(bool, false)
    labels         = optional(map(string), {})
    cleanup_policies = optional(list(object({
      id     = string
      action = string
      condition = object({
        tag_state             = optional(string, "TAGGED")
        tag_prefixes          = optional(list(string), [])
        version_name_prefixes = optional(list(string), [])
        package_name_prefixes = optional(list(string), [])
        older_than            = optional(string)
        newer_than            = optional(string)
      })
    })), [])
  }))
  default = []
}

variable "default_cleanup_policies" {
  description = "Default cleanup policies for container repositories"
  type = list(object({
    id     = string
    action = string
    condition = object({
      tag_state             = optional(string, "TAGGED")
      tag_prefixes          = optional(list(string), [])
      version_name_prefixes = optional(list(string), [])
      package_name_prefixes = optional(list(string), [])
      older_than            = optional(string)
      newer_than            = optional(string)
    })
  }))
  default = [
    {
      id     = "delete-old-versions"
      action = "DELETE"
      condition = {
        older_than = "2592000s" # 30 days
      }
    }
  ]
}

variable "default_immutable_tags" {
  description = "Enable immutable tags by default"
  type        = bool
  default     = false
}

# Service Mesh Configuration
variable "enable_service_mesh" {
  description = "Enable service mesh (Istio) installation"
  type        = bool
  default     = false
}

variable "use_helm_for_istio" {
  description = "Use Helm to install Istio (vs GCP managed)"
  type        = bool
  default     = true
}

variable "service_mesh_config" {
  description = "Service mesh configuration"
  type = object({
    namespace = optional(string, "istio-system")
  })
  default = {}
}

variable "istio_version" {
  description = "Istio version to install"
  type        = string
  default     = "1.19.3"
}

variable "mesh_id" {
  description = "Service mesh ID"
  type        = string
  default     = "mesh1"
}

variable "cluster_network" {
  description = "Cluster network name for service mesh"
  type        = string
  default     = "network1"
}

variable "num_trusted_proxies" {
  description = "Number of trusted proxies for gateway topology"
  type        = number
  default     = 2
}

variable "enable_workload_entry_autoregistration" {
  description = "Enable workload entry auto-registration"
  type        = bool
  default     = false
}

variable "enable_cross_cluster_workload_entry" {
  description = "Enable cross-cluster workload entry"
  type        = bool
  default     = false
}

variable "istiod_resources" {
  description = "Resource limits for istiod"
  type = object({
    requests = optional(object({
      cpu    = optional(string, "500m")
      memory = optional(string, "2Gi")
    }))
    limits = optional(object({
      cpu    = optional(string, "1000m")
      memory = optional(string, "4Gi")
    }))
  })
  default = {}
}

# Istio Ingress Gateway
variable "enable_istio_ingress" {
  description = "Enable Istio ingress gateway"
  type        = bool
  default     = false
}

variable "istio_ingress_service_config" {
  description = "Istio ingress gateway service configuration"
  type = object({
    type = optional(string, "LoadBalancer")
    annotations = optional(map(string), {
      "cloud.google.com/load-balancer-type" = "External"
    })
    ports = optional(list(object({
      name       = string
      port       = number
      protocol   = optional(string, "TCP")
      targetPort = optional(number)
      })), [
      {
        name       = "http2"
        port       = 80
        targetPort = 8080
      },
      {
        name       = "https"
        port       = 443
        targetPort = 8443
      }
    ])
  })
  default = {}
}

variable "istio_ingress_resources" {
  description = "Resource limits for Istio ingress gateway"
  type = object({
    requests = optional(object({
      cpu    = optional(string, "100m")
      memory = optional(string, "128Mi")
    }))
    limits = optional(object({
      cpu    = optional(string, "2000m")
      memory = optional(string, "1Gi")
    }))
  })
  default = {}
}

variable "istio_ingress_replicas" {
  description = "Number of Istio ingress gateway replicas"
  type        = number
  default     = 2
}

variable "istio_ingress_autoscaling" {
  description = "Istio ingress gateway autoscaling configuration"
  type = object({
    enabled                        = optional(bool, true)
    minReplicas                    = optional(number, 2)
    maxReplicas                    = optional(number, 10)
    targetCPUUtilizationPercentage = optional(number, 70)
  })
  default = {}
}

# Kubernetes Configuration
variable "kubernetes_namespaces" {
  description = "List of Kubernetes namespaces to create"
  type        = list(string)
  default = [
    "genesis-agents",
    "claude-talk",
    "monitoring",
    "istio-system"
  ]
}

variable "registry_secrets" {
  description = "Registry secrets for pulling container images"
  type = map(object({
    name               = string
    namespace          = string
    docker_config_json = string # Base64 encoded docker config JSON
  }))
  default = {}
}
