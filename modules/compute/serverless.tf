/**
 * Serverless compute resources - Cloud Run and Cloud Functions
 */

# Cloud Run Services
resource "google_cloud_run_v2_service" "services" {
  for_each = local.cloud_run_services
  
  name     = each.value.full_name
  project  = var.project_id
  location = lookup(each.value, "location", var.default_region)
  
  description = lookup(each.value, "description", "Cloud Run service ${each.value.name}")
  
  # Ingress settings
  ingress = lookup(each.value, "ingress", "INGRESS_TRAFFIC_ALL")
  
  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value, "labels", {}),
    {
      service_type = "cloud-run"
    }
  )
  
  # Annotations
  annotations = merge(
    lookup(each.value, "annotations", {}),
    {
      "run.googleapis.com/operation-id" = uuidv4()
    }
  )
  
  # Traffic configuration
  dynamic "traffic" {
    for_each = lookup(each.value, "traffic", [
      {
        type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
        percent = 100
      }
    ])
    content {
      type     = traffic.value.type
      percent  = lookup(traffic.value, "percent", null)
      revision = lookup(traffic.value, "revision", null)
      tag      = lookup(traffic.value, "tag", null)
    }
  }
  
  # Service template
  template {
    # Annotations
    annotations = merge(
      lookup(each.value, "template_annotations", {}),
      {
        "autoscaling.knative.dev/minScale" = tostring(lookup(each.value, "min_scale", 0))
        "autoscaling.knative.dev/maxScale" = tostring(lookup(each.value, "max_scale", 100))
        "run.googleapis.com/cloudsql-instances" = lookup(each.value, "cloudsql_instances", null) != null ? join(",", each.value.cloudsql_instances) : null
        "run.googleapis.com/cpu-throttling" = tostring(lookup(each.value, "cpu_throttling", true))
        "run.googleapis.com/execution-environment" = lookup(each.value, "execution_environment", "gen2")
        "run.googleapis.com/network-interfaces" = lookup(each.value, "network_interfaces", null)
      }
    )
    
    # Labels
    labels = merge(
      local.merged_labels,
      lookup(each.value, "template_labels", {}),
      {
        version = lookup(each.value, "version", "v1")
      }
    )
    
    # Revision naming
    revision = lookup(each.value, "revision_name", null)
    
    # Scaling
    scaling {
      min_instance_count = lookup(each.value, "min_scale", 0)
      max_instance_count = lookup(each.value, "max_scale", 100)
    }
    
    # VPC Access
    dynamic "vpc_access" {
      for_each = lookup(each.value, "vpc_access", null) != null ? [1] : []
      content {
        connector = lookup(each.value.vpc_access, "connector", null)
        egress    = lookup(each.value.vpc_access, "egress", "PRIVATE_RANGES_ONLY")
        
        dynamic "network_interfaces" {
          for_each = lookup(each.value.vpc_access, "network_interfaces", [])
          content {
            network    = lookup(network_interfaces.value, "network", var.network_id)
            subnetwork = lookup(network_interfaces.value, "subnetwork", var.subnet_id)
            tags       = lookup(network_interfaces.value, "tags", [])
          }
        }
      }
    }
    
    # Encryption
    dynamic "encryption_key" {
      for_each = lookup(each.value, "encryption_key", null) != null ? [1] : []
      content {
        kms_key_name = each.value.encryption_key
      }
    }
    
    # Service account
    service_account = lookup(each.value, "service_account", null)
    
    # Execution environment
    execution_environment = lookup(each.value, "execution_environment", "EXECUTION_ENVIRONMENT_GEN2")
    
    # Session affinity
    session_affinity = lookup(each.value, "session_affinity", false)
    
    # Timeout
    timeout = lookup(each.value, "timeout", "300s")
    
    # Containers
    dynamic "containers" {
      for_each = lookup(each.value, "containers", [
        {
          image = each.value.image
        }
      ])
      content {
        image = containers.value.image
        name  = lookup(containers.value, "name", "main")
        
        # Commands and arguments
        command = lookup(containers.value, "command", null)
        args    = lookup(containers.value, "args", null)
        
        # Working directory
        working_dir = lookup(containers.value, "working_dir", null)
        
        # Environment variables
        dynamic "env" {
          for_each = lookup(containers.value, "env", {})
          content {
            name  = env.key
            value = env.value
          }
        }
        
        # Environment from secrets
        dynamic "env" {
          for_each = lookup(containers.value, "env_from_secret", {})
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value.secret
                version = lookup(env.value, "version", "latest")
              }
            }
          }
        }
        
        # Environment from config maps
        dynamic "env" {
          for_each = lookup(containers.value, "env_from_config_map", {})
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value.config_map
                version = lookup(env.value, "version", "latest")
              }
            }
          }
        }
        
        # Resources
        resources {
          limits = merge(
            {
              "cpu"    = lookup(containers.value, "cpu", "1000m")
              "memory" = lookup(containers.value, "memory", "512Mi")
            },
            lookup(containers.value, "resource_limits", {})
          )
          
          cpu_idle = lookup(containers.value, "cpu_idle", true)
          
          startup_cpu_boost = lookup(containers.value, "startup_cpu_boost", false)
        }
        
        # Ports
        dynamic "ports" {
          for_each = lookup(containers.value, "ports", [
            {
              container_port = 8080
              name          = "http1"
            }
          ])
          content {
            name           = lookup(ports.value, "name", "http1")
            container_port = ports.value.container_port
          }
        }
        
        # Volume mounts
        dynamic "volume_mounts" {
          for_each = lookup(containers.value, "volume_mounts", [])
          content {
            name       = volume_mounts.value.name
            mount_path = volume_mounts.value.mount_path
          }
        }
        
        # Startup probe
        dynamic "startup_probe" {
          for_each = lookup(containers.value, "startup_probe", null) != null ? [1] : []
          content {
            initial_delay_seconds = lookup(containers.value.startup_probe, "initial_delay_seconds", 0)
            timeout_seconds      = lookup(containers.value.startup_probe, "timeout_seconds", 1)
            period_seconds       = lookup(containers.value.startup_probe, "period_seconds", 10)
            failure_threshold    = lookup(containers.value.startup_probe, "failure_threshold", 3)
            
            dynamic "http_get" {
              for_each = lookup(containers.value.startup_probe, "http_get", null) != null ? [1] : []
              content {
                path = lookup(containers.value.startup_probe.http_get, "path", "/")
                port = lookup(containers.value.startup_probe.http_get, "port", 8080)
                
                dynamic "http_headers" {
                  for_each = lookup(containers.value.startup_probe.http_get, "http_headers", {})
                  content {
                    name  = http_headers.key
                    value = http_headers.value
                  }
                }
              }
            }
            
            dynamic "tcp_socket" {
              for_each = lookup(containers.value.startup_probe, "tcp_socket", null) != null ? [1] : []
              content {
                port = containers.value.startup_probe.tcp_socket.port
              }
            }
            
            dynamic "grpc" {
              for_each = lookup(containers.value.startup_probe, "grpc", null) != null ? [1] : []
              content {
                port    = lookup(containers.value.startup_probe.grpc, "port", 8080)
                service = lookup(containers.value.startup_probe.grpc, "service", null)
              }
            }
          }
        }
        
        # Liveness probe
        dynamic "liveness_probe" {
          for_each = lookup(containers.value, "liveness_probe", null) != null ? [1] : []
          content {
            initial_delay_seconds = lookup(containers.value.liveness_probe, "initial_delay_seconds", 0)
            timeout_seconds      = lookup(containers.value.liveness_probe, "timeout_seconds", 1)
            period_seconds       = lookup(containers.value.liveness_probe, "period_seconds", 10)
            failure_threshold    = lookup(containers.value.liveness_probe, "failure_threshold", 3)
            
            dynamic "http_get" {
              for_each = lookup(containers.value.liveness_probe, "http_get", null) != null ? [1] : []
              content {
                path = lookup(containers.value.liveness_probe.http_get, "path", "/")
                port = lookup(containers.value.liveness_probe.http_get, "port", 8080)
                
                dynamic "http_headers" {
                  for_each = lookup(containers.value.liveness_probe.http_get, "http_headers", {})
                  content {
                    name  = http_headers.key
                    value = http_headers.value
                  }
                }
              }
            }
            
            dynamic "tcp_socket" {
              for_each = lookup(containers.value.liveness_probe, "tcp_socket", null) != null ? [1] : []
              content {
                port = containers.value.liveness_probe.tcp_socket.port
              }
            }
            
            dynamic "grpc" {
              for_each = lookup(containers.value.liveness_probe, "grpc", null) != null ? [1] : []
              content {
                port    = lookup(containers.value.liveness_probe.grpc, "port", 8080)
                service = lookup(containers.value.liveness_probe.grpc, "service", null)
              }
            }
          }
        }
      }
    }
    
    # Volumes
    dynamic "volumes" {
      for_each = lookup(each.value, "volumes", [])
      content {
        name = volumes.value.name
        
        dynamic "secret" {
          for_each = lookup(volumes.value, "secret", null) != null ? [1] : []
          content {
            secret       = volumes.value.secret.secret
            default_mode = lookup(volumes.value.secret, "default_mode", 0444)
            
            dynamic "items" {
              for_each = lookup(volumes.value.secret, "items", [])
              content {
                version = lookup(items.value, "version", "latest")
                path    = items.value.path
                mode    = lookup(items.value, "mode", 0444)
              }
            }
          }
        }
        
        dynamic "cloud_sql_instance" {
          for_each = lookup(volumes.value, "cloud_sql_instance", null) != null ? [1] : []
          content {
            instances = volumes.value.cloud_sql_instance.instances
          }
        }
        
        dynamic "empty_dir" {
          for_each = lookup(volumes.value, "empty_dir", null) != null ? [1] : []
          content {
            medium     = lookup(volumes.value.empty_dir, "medium", "MEMORY")
            size_limit = lookup(volumes.value.empty_dir, "size_limit", "1Gi")
          }
        }
        
        dynamic "nfs" {
          for_each = lookup(volumes.value, "nfs", null) != null ? [1] : []
          content {
            server    = volumes.value.nfs.server
            path      = volumes.value.nfs.path
            read_only = lookup(volumes.value.nfs, "read_only", false)
          }
        }
      }
    }
  }
  
  # Lifecycle
  lifecycle {
    ignore_changes = [
      template[0].annotations["run.googleapis.com/operation-id"],
    ]
  }
}

# Cloud Functions (2nd Gen)
resource "google_cloudfunctions2_function" "functions" {
  for_each = local.cloud_functions
  
  name     = each.value.full_name
  project  = var.project_id
  location = lookup(each.value, "location", var.default_region)
  
  description = lookup(each.value, "description", "Cloud Function ${each.value.name}")
  
  # Labels
  labels = merge(
    local.merged_labels,
    lookup(each.value, "labels", {}),
    {
      function_type = "cloud-function"
    }
  )
  
  # Build configuration
  build_config {
    runtime     = each.value.runtime
    entry_point = lookup(each.value, "entry_point", "main")
    
    # Source configuration
    dynamic "source" {
      for_each = lookup(each.value, "source_archive_url", null) != null ? [] : [1]
      content {
        dynamic "storage_source" {
          for_each = lookup(each.value, "source_bucket", null) != null ? [1] : []
          content {
            bucket = each.value.source_bucket
            object = lookup(each.value, "source_object", "${each.value.name}.zip")
          }
        }
        
        dynamic "repo_source" {
          for_each = lookup(each.value, "repo_source", null) != null ? [1] : []
          content {
            project_id   = lookup(each.value.repo_source, "project_id", var.project_id)
            repo_name    = each.value.repo_source.repo_name
            branch_name  = lookup(each.value.repo_source, "branch_name", null)
            tag_name     = lookup(each.value.repo_source, "tag_name", null)
            commit_sha   = lookup(each.value.repo_source, "commit_sha", null)
            dir          = lookup(each.value.repo_source, "dir", null)
            invert_regex = lookup(each.value.repo_source, "invert_regex", false)
          }
        }
      }
    }
    
    # Environment variables for build
    environment_variables = lookup(each.value, "build_environment_variables", {})
    
    # Docker repository
    docker_repository = lookup(each.value, "docker_repository", null)
    
    # Service account for builds
    service_account = lookup(each.value, "build_service_account", null)
    
    # Worker pool
    worker_pool = lookup(each.value, "build_worker_pool", null)
  }
  
  # Service configuration
  service_config {
    # Scaling
    max_instance_count               = lookup(each.value, "max_instances", 1000)
    min_instance_count               = lookup(each.value, "min_instances", 0)
    available_memory                = lookup(each.value, "available_memory", "256M")
    timeout_seconds                 = lookup(each.value, "timeout_seconds", 60)
    max_instance_request_concurrency = lookup(each.value, "max_instance_request_concurrency", 1000)
    
    # CPU
    available_cpu = lookup(each.value, "available_cpu", "1")
    
    # Environment variables
    environment_variables = lookup(each.value, "environment_variables", {})
    
    # Service account
    service_account_email = lookup(each.value, "service_account", null)
    
    # Ingress settings
    ingress_settings               = lookup(each.value, "ingress_settings", "ALLOW_ALL")
    all_traffic_on_latest_revision = lookup(each.value, "all_traffic_on_latest_revision", true)
    
    # VPC connector
    vpc_connector                 = lookup(each.value, "vpc_connector", null)
    vpc_connector_egress_settings = lookup(each.value, "vpc_connector_egress_settings", null)
    
    # Secret environment variables
    dynamic "secret_environment_variables" {
      for_each = lookup(each.value, "secret_environment_variables", {})
      content {
        key        = secret_environment_variables.key
        project_id = lookup(secret_environment_variables.value, "project_id", var.project_id)
        secret     = secret_environment_variables.value.secret
        version    = lookup(secret_environment_variables.value, "version", "latest")
      }
    }
    
    # Secret volumes
    dynamic "secret_volumes" {
      for_each = lookup(each.value, "secret_volumes", [])
      content {
        mount_path = secret_volumes.value.mount_path
        project_id = lookup(secret_volumes.value, "project_id", var.project_id)
        secret     = secret_volumes.value.secret
        
        dynamic "versions" {
          for_each = lookup(secret_volumes.value, "versions", [])
          content {
            version = versions.value.version
            path    = versions.value.path
          }
        }
      }
    }
  }
  
  # Event trigger
  dynamic "event_trigger" {
    for_each = lookup(each.value, "event_trigger", null) != null ? [1] : []
    content {
      trigger_region        = lookup(each.value.event_trigger, "trigger_region", var.default_region)
      event_type           = each.value.event_trigger.event_type
      retry_policy         = lookup(each.value.event_trigger, "retry_policy", "RETRY_POLICY_RETRY")
      service_account_email = lookup(each.value.event_trigger, "service_account_email", null)
      
      dynamic "event_filters" {
        for_each = lookup(each.value.event_trigger, "event_filters", [])
        content {
          attribute = event_filters.value.attribute
          value     = event_filters.value.value
          operator  = lookup(event_filters.value, "operator", "EQUALS")
        }
      }
      
      dynamic "pubsub_topic" {
        for_each = lookup(each.value.event_trigger, "pubsub_topic", null) != null ? [1] : []
        content {
          topic = each.value.event_trigger.pubsub_topic
        }
      }
    }
  }
  
  depends_on = [
    google_project_service.cloud_functions_api
  ]
}

# Enable Cloud Functions API
resource "google_project_service" "cloud_functions_api" {
  count = length(local.cloud_functions) > 0 ? 1 : 0
  
  project = var.project_id
  service = "cloudfunctions.googleapis.com"
  
  disable_on_destroy = false
}

# Enable Cloud Run API
resource "google_project_service" "cloud_run_api" {
  count = length(local.cloud_run_services) > 0 ? 1 : 0
  
  project = var.project_id
  service = "run.googleapis.com"
  
  disable_on_destroy = false
}

# Cloud Run IAM policies
resource "google_cloud_run_service_iam_policy" "noauth" {
  for_each = {
    for service_name, service in local.cloud_run_services : service_name => service
    if lookup(service, "allow_unauthenticated", false)
  }
  
  location = lookup(each.value, "location", var.default_region)
  project  = var.project_id
  service  = google_cloud_run_v2_service.services[each.key].name
  
  policy_data = data.google_iam_policy.noauth.policy_data
}

# IAM policy for unauthenticated access
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

# Cloud Function IAM policies
resource "google_cloudfunctions2_function_iam_policy" "function_noauth" {
  for_each = {
    for function_name, function in local.cloud_functions : function_name => function
    if lookup(function, "allow_unauthenticated", false)
  }
  
  location     = lookup(each.value, "location", var.default_region)
  project      = var.project_id
  cloud_function = google_cloudfunctions2_function.functions[each.key].name
  
  policy_data = data.google_iam_policy.noauth.policy_data
}