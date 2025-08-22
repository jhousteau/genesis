/**
 * Variables for Compute Module
 */

variable "project_id" {
  description = "The GCP project ID where resources will be created"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "compute"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "default_region" {
  description = "Default region for resources"
  type        = string
  default     = "us-central1"
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}

# Network Configuration
variable "network_id" {
  description = "The ID of the VPC network"
  type        = string
  default     = "default"
}

variable "subnet_id" {
  description = "The ID of the subnet"
  type        = string
  default     = null
}

# VM Instance Configuration
variable "vm_instances" {
  description = "Configuration for VM instances"
  type = list(object({
    name                = string
    machine_type        = string
    zone               = optional(string)
    region             = optional(string)
    description        = optional(string)
    source_image       = optional(string, "debian-cloud/debian-12")
    disk_size_gb       = optional(number, 20)
    disk_type          = optional(string, "pd-standard")
    auto_delete_disk   = optional(bool, true)
    disk_encryption_key = optional(string)
    enable_os_login    = optional(bool, true)
    startup_script     = optional(string)
    metadata          = optional(map(string), {})
    network_tags      = optional(list(string), [])
    labels            = optional(map(string), {})
    enable_shielded_vm = optional(bool, true)
    enable_secure_boot = optional(bool, true)
    enable_vtpm       = optional(bool, true)
    enable_integrity_monitoring = optional(bool, true)
    enable_confidential_vm = optional(bool, false)
    enable_nested_virtualization = optional(bool, false)
    threads_per_core  = optional(number)
    resource_policies = optional(list(string), [])
    
    additional_disks = optional(list(object({
      device_name        = string
      disk_size_gb      = number
      disk_type         = optional(string, "pd-standard")
      source            = optional(string)
      auto_delete       = optional(bool, false)
      disk_encryption_key = optional(string)
    })), [])
    
    network_interfaces = optional(list(object({
      network               = optional(string)
      subnetwork           = optional(string)
      subnetwork_project   = optional(string)
      network_ip           = optional(string)
      nic_type            = optional(string)
      stack_type          = optional(string, "IPV4_ONLY")
      queue_count         = optional(number)
      enable_external_ip  = optional(bool, false)
      external_ip         = optional(string)
      public_ptr_domain_name = optional(string)
      ipv6_public_ptr_domain_name = optional(string)
      enable_ipv6         = optional(bool, false)
      network_tier        = optional(string, "PREMIUM")
    })), [])
    
    service_account = optional(object({
      email  = string
      scopes = optional(list(string), ["cloud-platform"])
    }))
    
    scheduling = optional(object({
      automatic_restart   = optional(bool, true)
      on_host_maintenance = optional(string, "MIGRATE")
      preemptible        = optional(bool, false)
      node_affinities = optional(list(object({
        key      = string
        operator = string
        values   = list(string)
      })), [])
    }))
    
    guest_accelerators = optional(list(object({
      type  = string
      count = number
    })), [])
  }))
  default = []
}

# Instance Group Configuration
variable "instance_groups" {
  description = "Configuration for managed instance groups"
  type = list(object({
    name              = string
    instance_template = string  # References VM instance name
    region           = optional(string)
    target_size      = optional(number, 1)
    description      = optional(string)
    distribution_zones = optional(list(string))
    target_pools     = optional(list(string), [])
    
    canary_version = optional(object({
      instance_template = optional(string)
      percent           = optional(number, 10)
    }))
    
    update_policy = optional(object({
      type                    = optional(string, "PROACTIVE")
      minimal_action         = optional(string, "REPLACE")
      max_surge_fixed        = optional(number)
      max_surge_percent      = optional(number)
      max_unavailable_fixed  = optional(number)
      max_unavailable_percent = optional(number)
      min_ready_sec         = optional(number, 0)
      replacement_method    = optional(string, "SUBSTITUTE")
    }))
    
    health_check         = optional(string)
    initial_delay_sec    = optional(number, 300)
    
    named_ports = optional(list(object({
      name = string
      port = number
    })), [])
    
    stateful_disks = optional(list(object({
      device_name = string
      delete_rule = optional(string, "NEVER")
    })), [])
    
    # Auto-scaling configuration
    enable_autoscaling = optional(bool, false)
    min_replicas      = optional(number, 1)
    max_replicas      = optional(number, 10)
    cooldown_period   = optional(number, 60)
    cpu_target        = optional(number)
    cpu_predictive_method = optional(string, "NONE")
    load_balancing_target = optional(number)
    
    custom_metrics = optional(list(object({
      name   = string
      target = number
      type   = optional(string, "GAUGE")
      single_instance_assignment = optional(number)
    })), [])
    
    scale_down_control = optional(object({
      max_scaled_down_percent = optional(number)
      max_scaled_down_fixed   = optional(number)
      time_window_sec        = optional(number, 600)
    }))
    
    scale_in_control = optional(object({
      max_scaled_in_percent = optional(number)
      max_scaled_in_fixed   = optional(number)
      time_window_sec      = optional(number, 600)
    }))
  }))
  default = []
}

# Health Check Configuration
variable "health_checks" {
  description = "Health check configurations"
  type = list(object({
    name                = string
    description        = optional(string)
    check_interval_sec = optional(number, 5)
    timeout_sec       = optional(number, 5)
    healthy_threshold = optional(number, 2)
    unhealthy_threshold = optional(number, 3)
    enable_logging    = optional(bool, false)
    
    http = optional(object({
      host               = optional(string)
      request_path      = optional(string, "/")
      port              = optional(number, 80)
      port_name         = optional(string)
      proxy_header      = optional(string, "NONE")
      port_specification = optional(string, "USE_FIXED_PORT")
      response          = optional(string)
    }))
    
    https = optional(object({
      host               = optional(string)
      request_path      = optional(string, "/")
      port              = optional(number, 443)
      port_name         = optional(string)
      proxy_header      = optional(string, "NONE")
      port_specification = optional(string, "USE_FIXED_PORT")
      response          = optional(string)
    }))
    
    tcp = optional(object({
      port              = optional(number, 80)
      port_name         = optional(string)
      proxy_header      = optional(string, "NONE")
      port_specification = optional(string, "USE_FIXED_PORT")
      request           = optional(string)
      response          = optional(string)
    }))
    
    ssl = optional(object({
      port              = optional(number, 443)
      port_name         = optional(string)
      proxy_header      = optional(string, "NONE")
      port_specification = optional(string, "USE_FIXED_PORT")
      request           = optional(string)
      response          = optional(string)
    }))
    
    http2 = optional(object({
      host               = optional(string)
      request_path      = optional(string, "/")
      port              = optional(number, 443)
      port_name         = optional(string)
      proxy_header      = optional(string, "NONE")
      port_specification = optional(string, "USE_FIXED_PORT")
      response          = optional(string)
    }))
    
    grpc = optional(object({
      port              = optional(number, 443)
      port_name         = optional(string)
      port_specification = optional(string, "USE_FIXED_PORT")
      grpc_service_name = optional(string)
    }))
  }))
  default = []
}

# GKE Cluster Configuration
variable "gke_clusters" {
  description = "GKE cluster configurations"
  type = list(object({
    name               = string
    location          = optional(string)
    description       = optional(string)
    network           = optional(string)
    subnetwork        = optional(string)
    kubernetes_version = optional(string)
    deletion_protection = optional(bool, true)
    
    # Private cluster configuration
    private_cluster           = optional(bool, false)
    enable_private_endpoint   = optional(bool, false)
    master_ipv4_cidr_block   = optional(string, "172.16.0.0/28")
    enable_master_global_access = optional(bool, false)
    
    # IP allocation
    enable_ip_alias          = optional(bool, true)
    pods_range_name         = optional(string)
    services_range_name     = optional(string)
    pods_cidr_block         = optional(string)
    services_cidr_block     = optional(string)
    
    # Authorized networks
    authorized_networks = optional(list(object({
      cidr_block   = string
      display_name = optional(string)
    })), [])
    
    # Network policy
    enable_network_policy     = optional(bool, false)
    network_policy_provider   = optional(string, "CALICO")
    
    # Addons
    enable_http_load_balancing = optional(bool, true)
    enable_hpa               = optional(bool, true)
    enable_cloud_run_addon   = optional(bool, false)
    cloud_run_load_balancer_type = optional(string, "LOAD_BALANCER_TYPE_EXTERNAL")
    enable_istio             = optional(bool, false)
    istio_auth              = optional(string, "AUTH_MUTUAL_TLS")
    enable_kalm             = optional(bool, false)
    enable_config_connector  = optional(bool, false)
    enable_gce_pd_csi_driver = optional(bool, true)
    enable_filestore_csi_driver = optional(bool, false)
    enable_backup_agent      = optional(bool, false)
    
    # Cluster autoscaling
    enable_cluster_autoscaling = optional(bool, false)
    resource_limits = optional(list(object({
      resource_type = string
      minimum      = optional(number, 0)
      maximum      = number
    })), [])
    
    auto_provisioning_defaults = optional(object({
      oauth_scopes    = optional(list(string), ["https://www.googleapis.com/auth/cloud-platform"])
      service_account = optional(string)
      management = optional(object({
        auto_repair  = optional(bool, true)
        auto_upgrade = optional(bool, true)
      }))
      upgrade_settings = optional(object({
        max_surge       = optional(number, 1)
        max_unavailable = optional(number, 0)
        blue_green_settings = optional(object({
          node_pool_soak_duration = optional(string, "0s")
          standard_rollout_policy = object({
            batch_percentage    = optional(number)
            batch_node_count   = optional(number)
            batch_soak_duration = optional(string, "0s")
          })
        }))
      }))
    }))
    
    # Workload Identity
    enable_workload_identity = optional(bool, true)
    
    # Database encryption
    database_encryption_key = optional(string)
    
    # Maintenance policy
    maintenance_policy = optional(object({
      recurring_window = optional(object({
        start_time = string
        end_time   = string
        recurrence = string
      }))
      daily_maintenance_window = optional(object({
        start_time = string
      }))
      maintenance_exclusions = optional(list(object({
        exclusion_name = string
        start_time    = string
        end_time      = string
        exclusion_options = optional(object({
          scope = string
        }))
      })), [])
    }))
    
    # Release channel
    release_channel = optional(string)
    
    # Resource usage export
    resource_usage_export = optional(object({
      enable_network_egress_metering       = optional(bool, false)
      enable_resource_consumption_metering = optional(bool, true)
      bigquery_dataset_id                 = string
    }))
    
    # Monitoring and logging
    enable_monitoring     = optional(bool, true)
    monitoring_components = optional(list(string), ["SYSTEM_COMPONENTS"])
    enable_managed_prometheus = optional(bool, false)
    enable_logging       = optional(bool, true)
    logging_components   = optional(list(string), ["SYSTEM_COMPONENTS", "WORKLOADS"])
    
    # Security
    enable_binary_authorization = optional(bool, false)
    binary_authorization_evaluation_mode = optional(string, "PROJECT_SINGLETON_POLICY_ENFORCE")
    enable_cost_management = optional(bool, false)
    enable_security_posture = optional(bool, false)
    security_posture_mode = optional(string, "BASIC")
    security_posture_vulnerability_mode = optional(string, "VULNERABILITY_DISABLED")
    
    # Default node configuration
    default_node_config = optional(object({
      disk_size_gb    = optional(number, 100)
      disk_type       = optional(string, "pd-standard")
      image_type      = optional(string, "COS_CONTAINERD")
      machine_type    = optional(string, "e2-medium")
      oauth_scopes    = optional(list(string), ["https://www.googleapis.com/auth/cloud-platform"])
      service_account = optional(string)
      enable_shielded_nodes        = optional(bool, true)
      enable_secure_boot          = optional(bool, true)
      enable_integrity_monitoring = optional(bool, true)
    }))
    
    # Node pools
    node_pools = optional(list(object({
      name               = string
      initial_node_count = optional(number, 1)
      disk_size_gb      = optional(number, 100)
      disk_type         = optional(string, "pd-standard")
      image_type        = optional(string, "COS_CONTAINERD")
      machine_type      = optional(string, "e2-medium")
      spot             = optional(bool, false)
      preemptible      = optional(bool, false)
      service_account  = optional(string)
      oauth_scopes     = optional(list(string), ["https://www.googleapis.com/auth/cloud-platform"])
      labels           = optional(map(string), {})
      tags             = optional(list(string), [])
      metadata         = optional(map(string), {})
      
      enable_autoscaling = optional(bool, false)
      min_node_count    = optional(number, 1)
      max_node_count    = optional(number, 10)
      location_policy   = optional(string, "BALANCED")
      total_min_node_count = optional(number)
      total_max_node_count = optional(number)
      
      enable_shielded_nodes        = optional(bool, true)
      enable_secure_boot          = optional(bool, true)
      enable_integrity_monitoring = optional(bool, true)
      
      guest_accelerators = optional(list(object({
        type               = string
        count              = number
        gpu_partition_size = optional(string)
        gpu_sharing_config = optional(object({
          gpu_sharing_strategy       = string
          max_shared_clients_per_gpu = number
        }))
        gpu_driver_installation_config = optional(object({
          gpu_driver_version = string
        }))
      })), [])
      
      taints = optional(list(object({
        key    = string
        value  = string
        effect = string
      })), [])
      
      local_ssd_count                     = optional(number, 0)
      ephemeral_storage_local_ssd_count   = optional(number, 0)
      enable_gcfs                         = optional(bool, false)
      enable_gvnic                        = optional(bool, false)
      
      reservation_affinity = optional(object({
        consume_reservation_type = string
        key                     = optional(string)
        values                  = optional(list(string), [])
      }))
      
      workload_metadata_mode = optional(string)
      
      kubelet_config = optional(object({
        cpu_manager_policy   = optional(string, "static")
        cpu_cfs_quota       = optional(bool)
        cpu_cfs_quota_period = optional(string)
        pod_pids_limit      = optional(number)
      }))
      
      linux_node_config = optional(object({
        sysctls     = optional(map(string), {})
        cgroup_mode = optional(string, "CGROUP_MODE_UNSPECIFIED")
      }))
      
      enable_nested_virtualization = optional(bool, false)
      threads_per_core             = optional(number)
      
      sole_tenant_config = optional(object({
        node_affinities = optional(list(object({
          key      = string
          operator = string
          values   = list(string)
        })), [])
      }))
      
      management = optional(object({
        auto_repair  = optional(bool, true)
        auto_upgrade = optional(bool, true)
      }))
      
      upgrade_settings = optional(object({
        max_surge       = optional(number, 1)
        max_unavailable = optional(number, 0)
        strategy        = optional(string, "SURGE")
        blue_green_settings = optional(object({
          node_pool_soak_duration = optional(string, "0s")
          standard_rollout_policy = object({
            batch_percentage    = optional(number)
            batch_node_count   = optional(number)
            batch_soak_duration = optional(string, "0s")
          })
        }))
      }))
      
      enable_private_nodes     = optional(bool, false)
      create_pod_range        = optional(bool, false)
      pod_range              = optional(string)
      pod_ipv4_cidr_block    = optional(string)
      
      pod_cidr_overprovision_config = optional(object({
        enabled = bool
      }))
      
      network_performance_config = optional(object({
        total_egress_bandwidth_tier = string
      }))
      
      placement_policy = optional(object({
        type         = string
        policy_name  = optional(string)
        tpu_topology = optional(string)
      }))
    })), [])
  }))
  default = []
}

# Cloud Run Configuration
variable "cloud_run_services" {
  description = "Cloud Run service configurations"
  type = list(object({
    name        = string
    location   = optional(string)
    description = optional(string)
    image      = string
    ingress    = optional(string, "INGRESS_TRAFFIC_ALL")
    labels     = optional(map(string), {})
    annotations = optional(map(string), {})
    
    # Traffic configuration
    traffic = optional(list(object({
      type     = string
      percent  = optional(number)
      revision = optional(string)
      tag      = optional(string)
    })), [])
    
    # Template configuration
    template_annotations = optional(map(string), {})
    template_labels     = optional(map(string), {})
    revision_name       = optional(string)
    version            = optional(string, "v1")
    
    # Scaling
    min_scale = optional(number, 0)
    max_scale = optional(number, 100)
    
    # VPC Access
    vpc_access = optional(object({
      connector = optional(string)
      egress   = optional(string, "PRIVATE_RANGES_ONLY")
      network_interfaces = optional(list(object({
        network    = optional(string)
        subnetwork = optional(string)
        tags       = optional(list(string), [])
      })), [])
    }))
    
    # Security
    encryption_key   = optional(string)
    service_account = optional(string)
    
    # Runtime
    execution_environment          = optional(string, "EXECUTION_ENVIRONMENT_GEN2")
    session_affinity              = optional(bool, false)
    timeout                       = optional(string, "300s")
    cpu_throttling               = optional(bool, true)
    cloudsql_instances           = optional(list(string))
    network_interfaces           = optional(string)
    
    # Container configuration
    containers = optional(list(object({
      image       = optional(string)
      name        = optional(string, "main")
      command     = optional(list(string))
      args        = optional(list(string))
      working_dir = optional(string)
      
      # Environment variables
      env                    = optional(map(string), {})
      env_from_secret       = optional(map(object({
        secret  = string
        version = optional(string, "latest")
      })), {})
      env_from_config_map   = optional(map(object({
        config_map = string
        version    = optional(string, "latest")
      })), {})
      
      # Resources
      cpu              = optional(string, "1000m")
      memory           = optional(string, "512Mi")
      resource_limits  = optional(map(string), {})
      cpu_idle        = optional(bool, true)
      startup_cpu_boost = optional(bool, false)
      
      # Ports
      ports = optional(list(object({
        name           = optional(string, "http1")
        container_port = number
      })), [])
      
      # Volume mounts
      volume_mounts = optional(list(object({
        name       = string
        mount_path = string
      })), [])
      
      # Probes
      startup_probe = optional(object({
        initial_delay_seconds = optional(number, 0)
        timeout_seconds      = optional(number, 1)
        period_seconds       = optional(number, 10)
        failure_threshold    = optional(number, 3)
        http_get = optional(object({
          path         = optional(string, "/")
          port         = optional(number, 8080)
          http_headers = optional(map(string), {})
        }))
        tcp_socket = optional(object({
          port = number
        }))
        grpc = optional(object({
          port    = optional(number, 8080)
          service = optional(string)
        }))
      }))
      
      liveness_probe = optional(object({
        initial_delay_seconds = optional(number, 0)
        timeout_seconds      = optional(number, 1)
        period_seconds       = optional(number, 10)
        failure_threshold    = optional(number, 3)
        http_get = optional(object({
          path         = optional(string, "/")
          port         = optional(number, 8080)
          http_headers = optional(map(string), {})
        }))
        tcp_socket = optional(object({
          port = number
        }))
        grpc = optional(object({
          port    = optional(number, 8080)
          service = optional(string)
        }))
      }))
    })), [])
    
    # Volumes
    volumes = optional(list(object({
      name = string
      secret = optional(object({
        secret       = string
        default_mode = optional(number, 0444)
        items = optional(list(object({
          version = optional(string, "latest")
          path    = string
          mode    = optional(number, 0444)
        })), [])
      }))
      cloud_sql_instance = optional(object({
        instances = list(string)
      }))
      empty_dir = optional(object({
        medium     = optional(string, "MEMORY")
        size_limit = optional(string, "1Gi")
      }))
      nfs = optional(object({
        server    = string
        path      = string
        read_only = optional(bool, false)
      }))
    })), [])
    
    allow_unauthenticated = optional(bool, false)
  }))
  default = []
}

# Cloud Functions Configuration
variable "cloud_functions" {
  description = "Cloud Functions configurations"
  type = list(object({
    name        = string
    location   = optional(string)
    description = optional(string)
    runtime    = string
    entry_point = optional(string, "main")
    labels     = optional(map(string), {})
    
    # Source configuration
    source_bucket     = optional(string)
    source_object     = optional(string)
    source_archive_url = optional(string)
    repo_source = optional(object({
      project_id   = optional(string)
      repo_name    = string
      branch_name  = optional(string)
      tag_name     = optional(string)
      commit_sha   = optional(string)
      dir          = optional(string)
      invert_regex = optional(bool, false)
    }))
    
    # Build configuration
    build_environment_variables = optional(map(string), {})
    docker_repository          = optional(string)
    build_service_account      = optional(string)
    build_worker_pool          = optional(string)
    
    # Service configuration
    max_instances                      = optional(number, 1000)
    min_instances                      = optional(number, 0)
    available_memory                   = optional(string, "256M")
    available_cpu                      = optional(string, "1")
    timeout_seconds                    = optional(number, 60)
    max_instance_request_concurrency   = optional(number, 1000)
    environment_variables              = optional(map(string), {})
    service_account                    = optional(string)
    ingress_settings                   = optional(string, "ALLOW_ALL")
    all_traffic_on_latest_revision     = optional(bool, true)
    vpc_connector                      = optional(string)
    vpc_connector_egress_settings      = optional(string)
    
    # Secret environment variables
    secret_environment_variables = optional(map(object({
      project_id = optional(string)
      secret     = string
      version    = optional(string, "latest")
    })), {})
    
    # Secret volumes
    secret_volumes = optional(list(object({
      mount_path = string
      project_id = optional(string)
      secret     = string
      versions = optional(list(object({
        version = string
        path    = string
      })), [])
    })), [])
    
    # Event trigger
    event_trigger = optional(object({
      trigger_region        = optional(string)
      event_type           = string
      retry_policy         = optional(string, "RETRY_POLICY_RETRY")
      service_account_email = optional(string)
      pubsub_topic         = optional(string)
      event_filters = optional(list(object({
        attribute = string
        value     = string
        operator  = optional(string, "EQUALS")
      })), [])
    }))
    
    allow_unauthenticated = optional(bool, false)
  }))
  default = []
}

# Load Balancer Configuration
variable "load_balancers" {
  description = "Load balancer configurations"
  type = list(object({
    name = string
    type = optional(string, "external")  # external, internal
  }))
  default = []
}

# Cost Optimization
variable "enable_cost_optimization" {
  description = "Enable cost optimization features"
  type        = bool
  default     = true
}

variable "default_preemptible" {
  description = "Use preemptible instances by default"
  type        = bool
  default     = false
}

variable "default_spot" {
  description = "Use spot instances by default for GKE"
  type        = bool
  default     = false
}

# Security Configuration
variable "enable_shielded_vm_default" {
  description = "Enable Shielded VM by default"
  type        = bool
  default     = true
}

variable "enable_confidential_computing" {
  description = "Enable Confidential Computing where supported"
  type        = bool
  default     = false
}

variable "enable_binary_authorization" {
  description = "Enable Binary Authorization for containers"
  type        = bool
  default     = false
}

# Monitoring Configuration
variable "enable_monitoring" {
  description = "Enable monitoring and logging"
  type        = bool
  default     = true
}

variable "monitoring_config" {
  description = "Monitoring configuration"
  type = object({
    enable_ops_agent        = optional(bool, true)
    enable_detailed_monitoring = optional(bool, false)
    notification_channels   = optional(list(string), [])
  })
  default = {}
}