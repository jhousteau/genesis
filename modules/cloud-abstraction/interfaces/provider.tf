/**
 * Cloud Provider Interface Definitions
 * 
 * Defines the abstract interfaces that all cloud providers must implement
 * to ensure consistent behavior across GCP, AWS, and Azure providers.
 */

# Provider Interface - Core abstraction for all cloud providers
variable "provider_config" {
  description = "Cloud provider configuration"
  type = object({
    name         = string           # Provider name: "gcp", "aws", "azure"
    region       = string           # Primary region
    project_id   = optional(string) # GCP project / AWS account / Azure subscription
    credentials  = optional(object({
      type = string                 # "service-account", "role", "managed-identity"
      path = optional(string)       # Path to credentials file
    }))
    
    # Provider-specific settings
    settings = optional(map(any), {})
    
    # Multi-region configuration
    regions = optional(list(object({
      name     = string
      primary  = optional(bool, false)
      zones    = optional(list(string))
    })), [])
    
    # Cost optimization settings
    cost_optimization = optional(object({
      enable_rightsizing    = optional(bool, true)
      enable_spot_instances = optional(bool, false)
      budget_alerts        = optional(list(object({
        threshold = number
        type      = string # "actual", "forecast"
        emails    = list(string)
      })), [])
    }))
    
    # Security configuration
    security = optional(object({
      enable_encryption_at_rest     = optional(bool, true)
      enable_encryption_in_transit  = optional(bool, true)
      enable_network_security       = optional(bool, true)
      compliance_frameworks         = optional(list(string), [])
    }))
  })
}

# Compute Service Interface
variable "compute_config" {
  description = "Compute service configuration"
  type = object({
    # Virtual Machine instances
    instances = optional(list(object({
      name              = string
      type              = string           # Abstract instance type (small, medium, large, xlarge)
      image             = string           # Abstract image name (debian-12, ubuntu-22.04, etc.)
      zone              = optional(string)
      disk_size_gb      = optional(number, 20)
      disk_type         = optional(string, "standard") # "standard", "ssd", "nvme"
      
      # Networking
      subnet_name       = optional(string)
      external_ip       = optional(bool, false)
      security_groups   = optional(list(string), [])
      
      # Configuration
      user_data         = optional(string)
      ssh_keys          = optional(list(string), [])
      labels            = optional(map(string), {})
      
      # High availability
      availability_zone = optional(string)
      auto_replace      = optional(bool, true)
      
      # Performance
      cpu_credits       = optional(string, "standard") # "standard", "unlimited"
      monitoring        = optional(bool, true)
    })), [])
    
    # Container clusters (Kubernetes)
    clusters = optional(list(object({
      name               = string
      version            = optional(string, "latest")
      node_count         = optional(number, 3)
      node_type          = string           # Abstract node type
      disk_size_gb       = optional(number, 100)
      
      # Auto-scaling
      auto_scaling       = optional(bool, true)
      min_nodes          = optional(number, 1)
      max_nodes          = optional(number, 10)
      
      # Networking
      network_name       = optional(string)
      subnet_name        = optional(string)
      cluster_cidr       = optional(string, "10.1.0.0/16")
      services_cidr      = optional(string, "10.2.0.0/16")
      
      # Security
      private_cluster    = optional(bool, true)
      master_cidr        = optional(string, "10.3.0.0/28")
      authorized_networks = optional(list(object({
        cidr_block   = string
        display_name = optional(string)
      })), [])
      
      # Features
      enable_network_policy    = optional(bool, true)
      enable_pod_security      = optional(bool, true)
      enable_workload_identity = optional(bool, true)
      
      # Node pools
      node_pools = optional(list(object({
        name           = string
        node_count     = number
        node_type      = string
        disk_size_gb   = optional(number, 100)
        auto_scaling   = optional(bool, true)
        min_nodes      = optional(number, 1)
        max_nodes      = optional(number, 10)
        preemptible    = optional(bool, false)
        labels         = optional(map(string), {})
        taints = optional(list(object({
          key    = string
          value  = string
          effect = string
        })), [])
      })), [])
      
      labels = optional(map(string), {})
    })), [])
    
    # Serverless functions
    functions = optional(list(object({
      name              = string
      runtime           = string           # "python39", "nodejs18", "go119", etc.
      entry_point       = string
      source_path       = string
      
      # Resource limits
      memory_mb         = optional(number, 256)
      timeout_seconds   = optional(number, 60)
      max_instances     = optional(number, 100)
      
      # Triggers
      triggers = optional(list(object({
        type           = string    # "http", "pubsub", "storage", "timer"
        configuration  = map(any)
      })), [])
      
      # Environment
      environment_variables = optional(map(string), {})
      secrets              = optional(list(object({
        name  = string
        key   = string
      })), [])
      
      # Networking
      vpc_connector = optional(string)
      ingress       = optional(string, "all") # "all", "internal-only"
      
      labels = optional(map(string), {})
    })), [])
    
    # Load balancers
    load_balancers = optional(list(object({
      name              = string
      type              = string           # "external", "internal"
      protocol          = optional(string, "HTTP")
      port              = optional(number, 80)
      
      # Backend configuration
      backends = list(object({
        group             = string         # Instance group or service name
        port              = optional(number, 80)
        protocol          = optional(string, "HTTP")
        health_check_path = optional(string, "/health")
        
        # Load balancing
        balancing_mode    = optional(string, "UTILIZATION")
        max_utilization   = optional(number, 0.8)
        capacity_scaler   = optional(number, 1.0)
      }))
      
      # Health checks
      health_check = optional(object({
        protocol           = optional(string, "HTTP")
        port              = optional(number, 80)
        path              = optional(string, "/health")
        check_interval    = optional(number, 30)
        timeout           = optional(number, 5)
        healthy_threshold = optional(number, 2)
        unhealthy_threshold = optional(number, 3)
      }))
      
      # SSL/TLS configuration
      ssl = optional(object({
        certificate_name = string
        ssl_policy      = optional(string)
        redirect_http   = optional(bool, true)
      }))
      
      # Network configuration
      network_name = optional(string)
      subnet_name  = optional(string)
      static_ip    = optional(bool, false)
      
      labels = optional(map(string), {})
    })), [])
  })
  
  default = {}
  
  validation {
    condition = length([
      for instance in var.compute_config.instances :
      instance.type if !contains(["nano", "micro", "small", "medium", "large", "xlarge", "2xlarge", "4xlarge"], instance.type)
    ]) == 0
    error_message = "Instance type must be one of: nano, micro, small, medium, large, xlarge, 2xlarge, 4xlarge"
  }
}

# Storage Service Interface
variable "storage_config" {
  description = "Storage service configuration"
  type = object({
    # Object storage buckets
    buckets = optional(list(object({
      name                = string
      location            = optional(string)        # Region or multi-region
      storage_class       = optional(string, "STANDARD") # "STANDARD", "NEARLINE", "COLDLINE", "ARCHIVE"
      
      # Access control
      public_access       = optional(bool, false)
      uniform_access      = optional(bool, true)
      access_control = optional(list(object({
        role    = string
        members = list(string)
      })), [])
      
      # Lifecycle management
      lifecycle_rules = optional(list(object({
        action = object({
          type          = string           # "Delete", "SetStorageClass"
          storage_class = optional(string)
        })
        condition = object({
          age                   = optional(number)
          created_before        = optional(string)
          with_state           = optional(string) # "LIVE", "ARCHIVED"
          matches_storage_class = optional(list(string))
          matches_prefix       = optional(list(string))
          matches_suffix       = optional(list(string))
        })
      })), [])
      
      # Versioning and backup
      versioning_enabled  = optional(bool, false)
      
      # Encryption
      encryption_key      = optional(string)
      
      # CORS configuration
      cors = optional(list(object({
        origin          = list(string)
        method          = list(string)
        response_header = optional(list(string))
        max_age_seconds = optional(number, 3600)
      })), [])
      
      # Notifications
      notifications = optional(list(object({
        topic             = string
        event_types       = list(string)
        object_name_prefix = optional(string)
        object_name_suffix = optional(string)
      })), [])
      
      labels = optional(map(string), {})
    })), [])
    
    # Block storage (persistent disks)
    disks = optional(list(object({
      name              = string
      type              = optional(string, "standard") # "standard", "ssd", "nvme"
      size_gb           = number
      zone              = optional(string)
      
      # Snapshot configuration
      snapshot_schedule = optional(object({
        frequency = string         # "daily", "weekly", "monthly"
        retention = number         # Number of snapshots to retain
        time      = optional(string, "02:00") # Time to take snapshot
      }))
      
      # Encryption
      encryption_key    = optional(string)
      
      labels = optional(map(string), {})
    })), [])
    
    # Managed databases
    databases = optional(list(object({
      name                = string
      engine              = string           # "mysql", "postgresql", "mongodb", "redis"
      version             = string
      instance_class      = string           # Abstract instance size
      
      # Storage
      storage_gb          = number
      storage_type        = optional(string, "ssd")
      storage_encrypted   = optional(bool, true)
      storage_autoscaling = optional(object({
        enabled     = bool
        max_storage = number
      }))
      
      # Networking
      network_name        = optional(string)
      subnet_group        = optional(string)
      publicly_accessible = optional(bool, false)
      port                = optional(number)
      
      # High availability
      multi_az            = optional(bool, true)
      backup_enabled      = optional(bool, true)
      backup_retention    = optional(number, 7)   # Days
      backup_window       = optional(string, "03:00-04:00")
      maintenance_window  = optional(string, "sun:04:00-sun:05:00")
      
      # Security
      master_username     = string
      master_password     = string           # Should use secret management
      parameter_group     = optional(string)
      
      # Monitoring and logging
      monitoring_enabled  = optional(bool, true)
      log_exports        = optional(list(string), [])
      
      # Read replicas
      read_replicas = optional(list(object({
        identifier         = string
        instance_class     = optional(string)
        storage_encrypted  = optional(bool, true)
        publicly_accessible = optional(bool, false)
        availability_zone  = optional(string)
      })), [])
      
      labels = optional(map(string), {})
    })), [])
    
    # File systems (NFS/SMB)
    file_systems = optional(list(object({
      name              = string
      type              = optional(string, "nfs")    # "nfs", "smb"
      performance_mode  = optional(string, "general") # "general", "max_io"
      throughput_mode   = optional(string, "bursting") # "bursting", "provisioned"
      provisioned_throughput = optional(number)
      
      # Access control
      access_points = optional(list(object({
        name = string
        path = string
        uid  = optional(number, 1001)
        gid  = optional(number, 1001)
      })), [])
      
      # Backup
      backup_enabled    = optional(bool, true)
      
      # Encryption
      encrypted         = optional(bool, true)
      kms_key          = optional(string)
      
      labels = optional(map(string), {})
    })), [])
  })
  
  default = {}
}

# Networking Service Interface  
variable "network_config" {
  description = "Network service configuration"
  type = object({
    # Virtual Private Cloud
    vpc = optional(object({
      name                = optional(string, "main")
      cidr_block         = optional(string, "10.0.0.0/16")
      enable_dns         = optional(bool, true)
      enable_dns_hostnames = optional(bool, true)
      
      # Flow logs
      flow_logs_enabled  = optional(bool, true)
      flow_logs_retention = optional(number, 14) # Days
      
      labels = optional(map(string), {})
    }), {})
    
    # Subnets
    subnets = optional(list(object({
      name               = string
      cidr_block        = string
      availability_zone = optional(string)
      
      # Routing
      route_table       = optional(string)
      nat_gateway       = optional(bool, true)
      
      # Access
      public            = optional(bool, false)
      
      # Flow logs (subnet-level override)
      flow_logs_enabled = optional(bool)
      
      labels = optional(map(string), {})
    })), [])
    
    # Security groups (firewall rules)
    security_groups = optional(list(object({
      name        = string
      description = optional(string)
      
      ingress_rules = optional(list(object({
        description      = optional(string)
        from_port       = number
        to_port         = number  
        protocol        = string
        cidr_blocks     = optional(list(string), [])
        security_groups = optional(list(string), [])
      })), [])
      
      egress_rules = optional(list(object({
        description      = optional(string)
        from_port       = number
        to_port         = number
        protocol        = string
        cidr_blocks     = optional(list(string), [])
        security_groups = optional(list(string), [])
      })), [])
      
      labels = optional(map(string), {})
    })), [])
    
    # Network ACLs (additional security layer)
    network_acls = optional(list(object({
      name = string
      
      ingress_rules = optional(list(object({
        rule_number = number
        protocol    = string
        rule_action = string # "allow" or "deny"
        cidr_block  = string
        from_port   = optional(number)
        to_port     = optional(number)
      })), [])
      
      egress_rules = optional(list(object({
        rule_number = number
        protocol    = string
        rule_action = string
        cidr_block  = string
        from_port   = optional(number)
        to_port     = optional(number)
      })), [])
      
      subnet_associations = list(string)
    })), [])
    
    # DNS zones and records
    dns = optional(object({
      zones = optional(list(object({
        name            = string
        domain          = string
        private         = optional(bool, false)
        vpc_associations = optional(list(string), [])
        
        records = optional(list(object({
          name    = string
          type    = string
          ttl     = optional(number, 300)
          records = list(string)
        })), [])
      })), [])
    }), {})
    
    # VPN connections
    vpn = optional(object({
      gateways = optional(list(object({
        name            = string
        type            = optional(string, "policy-based") # "policy-based", "route-based"
        
        connections = list(object({
          name                = string
          remote_gateway_ip   = string
          shared_secret      = string
          local_networks     = list(string)
          remote_networks    = list(string)
          ike_version        = optional(number, 2)
        }))
      })), [])
    }), {})
    
    # Network peering
    peering = optional(object({
      connections = optional(list(object({
        name             = string
        peer_vpc_id      = string
        peer_region      = optional(string)
        peer_account_id  = optional(string)
        
        # Route table updates
        auto_accept      = optional(bool, true)
        
        # DNS resolution across peering
        allow_remote_vpc_dns_resolution = optional(bool, false)
      })), [])
    }), {})
    
    # CDN configuration
    cdn = optional(object({
      distributions = optional(list(object({
        name            = string
        origin_domain   = string
        origin_path     = optional(string)
        
        # Caching behavior
        default_ttl     = optional(number, 86400)
        max_ttl         = optional(number, 31536000)
        compress        = optional(bool, true)
        
        # Geographic restrictions
        geo_restriction = optional(object({
          restriction_type = string # "whitelist", "blacklist"
          locations       = list(string)
        }))
        
        # SSL configuration
        ssl_certificate = optional(string)
        ssl_policy     = optional(string)
        
        # Custom error pages
        error_responses = optional(list(object({
          error_code         = number
          response_code      = number
          response_page_path = string
          min_ttl           = optional(number, 300)
        })), [])
        
        labels = optional(map(string), {})
      })), [])
    }), {})
  })
  
  default = {}
}

# Security Service Interface
variable "security_config" {
  description = "Security service configuration"  
  type = object({
    # Identity and Access Management
    iam = optional(object({
      # Service accounts / roles
      service_accounts = optional(list(object({
        name         = string
        display_name = optional(string)
        description  = optional(string)
        
        # Permissions
        roles = optional(list(string), [])
        
        # Key management
        create_key   = optional(bool, false)
        key_rotation = optional(object({
          enabled           = bool
          rotation_period   = optional(string, "90d")
        }))
        
        labels = optional(map(string), {})
      })), [])
      
      # Custom roles
      custom_roles = optional(list(object({
        name         = string
        title        = string
        description  = optional(string)
        permissions  = list(string)
        stage       = optional(string, "GA") # "ALPHA", "BETA", "GA"
      })), [])
      
      # Policy bindings
      policy_bindings = optional(list(object({
        role    = string
        members = list(string)
        
        # Conditional bindings
        condition = optional(object({
          title       = string
          description = string
          expression  = string
        }))
      })), [])
    }), {})
    
    # Secret management
    secrets = optional(object({
      secrets = optional(list(object({
        name         = string
        description  = optional(string)
        
        # Secret data
        secret_data  = optional(string)
        secret_file  = optional(string)
        
        # Access control
        access_bindings = optional(list(object({
          role    = string
          members = list(string)
        })), [])
        
        # Rotation
        rotation = optional(object({
          enabled         = bool
          rotation_period = string # "30d", "90d", etc.
          next_rotation   = optional(string)
        }))
        
        # Versioning
        version_destroy_ttl = optional(string, "2160h") # 90 days
        
        labels = optional(map(string), {})
      })), [])
      
      # Secret versions
      versions = optional(list(object({
        secret_name = string
        secret_data = string
        enabled     = optional(bool, true)
      })), [])
    }), {})
    
    # Key management
    kms = optional(object({
      key_rings = optional(list(object({
        name     = string
        location = string
        
        keys = list(object({
          name            = string
          purpose         = optional(string, "ENCRYPT_DECRYPT")
          rotation_period = optional(string, "90d")
          
          # Version template
          algorithm              = optional(string, "GOOGLE_SYMMETRIC_ENCRYPTION")
          protection_level       = optional(string, "SOFTWARE") # "SOFTWARE", "HSM"
          
          # Access control
          access_bindings = optional(list(object({
            role    = string
            members = list(string)
          })), [])
          
          labels = optional(map(string), {})
        }))
      })), [])
    }), {})
    
    # Certificate management
    certificates = optional(object({
      managed_certs = optional(list(object({
        name    = string
        domains = list(string)
        
        # Validation
        validation_method = optional(string, "dns") # "dns", "http"
        
        labels = optional(map(string), {})
      })), [])
      
      self_signed_certs = optional(list(object({
        name             = string
        common_name      = string
        organization     = optional(string)
        validity_days    = optional(number, 365)
        
        # Subject Alternative Names
        dns_names        = optional(list(string), [])
        ip_addresses     = optional(list(string), [])
        
        labels = optional(map(string), {})
      })), [])
    }), {})
    
    # Security scanning
    scanning = optional(object({
      # Vulnerability scanning
      vulnerability_scanning = optional(object({
        enabled           = bool
        scan_frequency    = optional(string, "daily")
        severity_threshold = optional(string, "HIGH") # "LOW", "MEDIUM", "HIGH", "CRITICAL"
        
        # Notification configuration
        notification_channels = optional(list(string), [])
      }))
      
      # Container scanning
      container_scanning = optional(object({
        enabled              = bool
        scan_on_push        = optional(bool, true)
        continuous_scanning = optional(bool, true)
        
        # Policy configuration
        policy_name         = optional(string)
        fail_on_severity    = optional(string, "HIGH")
      }))
    }), {})
    
    # Web Application Firewall
    waf = optional(object({
      policies = optional(list(object({
        name        = string
        description = optional(string)
        
        # Rules
        rules = list(object({
          name        = string
          priority    = number
          action      = string # "ALLOW", "DENY", "LOG"
          
          # Match conditions
          conditions = list(object({
            field    = string # "uri", "query-string", "header", "body"
            operator = string # "contains", "equals", "starts-with", "regex"
            value    = string
            
            # Case sensitivity
            case_sensitive = optional(bool, false)
          }))
          
          # Rate limiting
          rate_limit = optional(object({
            limit           = number
            period_seconds  = number
            burst_limit     = optional(number)
          }))
        }))
        
        # Default action for unmatched requests
        default_action = optional(string, "ALLOW")
        
        labels = optional(map(string), {})
      })), [])
      
      # WAF associations
      associations = optional(list(object({
        policy_name     = string
        resource_arn    = string
        resource_type   = string # "load-balancer", "cloudfront", "api-gateway"
      })), [])
    }), {})
  })
  
  default = {}
}

# Monitoring Service Interface
variable "monitoring_config" {
  description = "Monitoring and observability configuration"
  type = object({
    # Metrics and monitoring
    metrics = optional(object({
      # Metric collection
      enabled               = optional(bool, true)
      collection_interval   = optional(number, 60) # seconds
      retention_days       = optional(number, 90)
      
      # Custom metrics
      custom_metrics = optional(list(object({
        name        = string
        description = optional(string)
        unit        = optional(string)
        type        = optional(string, "gauge") # "gauge", "counter", "histogram"
        
        # Labels/dimensions
        labels = optional(list(object({
          name = string
          type = optional(string, "string")
        })), [])
      })), [])
      
      # Dashboards
      dashboards = optional(list(object({
        name         = string
        description  = optional(string)
        
        # Dashboard configuration
        config_file  = optional(string)
        config_json  = optional(string)
        
        # Sharing
        public       = optional(bool, false)
        
        labels = optional(map(string), {})
      })), [])
    }), {})
    
    # Log management
    logging = optional(object({
      # Log retention
      retention_days = optional(number, 30)
      
      # Log groups/streams
      log_groups = optional(list(object({
        name           = string
        retention_days = optional(number, 30)
        
        # Log streams
        streams = optional(list(object({
          name = string
        })), [])
        
        # Subscription filters
        filters = optional(list(object({
          name            = string
          pattern         = string
          destination_arn = string
        })), [])
      })), [])
      
      # Log sinks/exports
      sinks = optional(list(object({
        name            = string
        destination     = string
        filter          = optional(string)
        include_children = optional(bool, true)
      })), [])
      
      # Structured logging configuration
      structured_logging = optional(object({
        enabled = bool
        format  = optional(string, "json") # "json", "text"
        
        # Field mapping
        field_mappings = optional(map(string), {})
      }))
    }), {})
    
    # Alerting
    alerts = optional(object({
      # Notification channels
      notification_channels = optional(list(object({
        name        = string
        type        = string # "email", "slack", "pagerduty", "webhook"
        
        # Configuration based on type
        email = optional(object({
          addresses = list(string)
        }))
        
        slack = optional(object({
          webhook_url = string
          channel     = optional(string)
        }))
        
        pagerduty = optional(object({
          service_key = string
        }))
        
        webhook = optional(object({
          url     = string
          headers = optional(map(string), {})
        }))
        
        labels = optional(map(string), {})
      })), [])
      
      # Alert policies
      policies = optional(list(object({
        name         = string
        description  = optional(string)
        enabled      = optional(bool, true)
        
        # Conditions
        conditions = list(object({
          name        = string
          description = optional(string)
          
          # Metric condition
          metric = object({
            name   = string
            filter = optional(string)
            
            # Aggregation
            aggregation = object({
              alignment_period    = optional(string, "60s")
              per_series_aligner = optional(string, "ALIGN_MEAN")
              cross_series_reducer = optional(string, "REDUCE_MEAN")
              group_by_fields     = optional(list(string), [])
            })
          })
          
          # Threshold
          threshold = object({
            comparison      = string # "COMPARISON_EQUAL", "COMPARISON_GREATER", etc.
            threshold_value = number
            duration        = optional(string, "300s")
          })
        }))
        
        # Notification configuration
        notification_channels = list(string)
        
        # Alert policy configuration
        alert_strategy = optional(object({
          auto_close           = optional(string, "1800s")
          notification_rate_limit = optional(object({
            period = optional(string, "300s")
          }))
        }))
        
        labels = optional(map(string), {})
      })), [])
      
      # Uptime checks
      uptime_checks = optional(list(object({
        name         = string
        display_name = optional(string)
        
        # Target configuration
        http_check = optional(object({
          url             = string
          port            = optional(number, 80)
          request_method  = optional(string, "GET")
          content_type    = optional(string, "text/html")
          body           = optional(string)
          headers        = optional(map(string), {})
          
          # Response validation
          response_status_code = optional(number, 200)
          response_content_match = optional(string)
        }))
        
        tcp_check = optional(object({
          host = string
          port = number
        }))
        
        # Check frequency and timeout
        period  = optional(string, "60s")
        timeout = optional(string, "10s")
        
        # Geographic distribution
        regions = optional(list(string), ["us-central1", "us-east1", "europe-west1"])
        
        labels = optional(map(string), {})
      })), [])
    }), {})
    
    # Distributed tracing
    tracing = optional(object({
      enabled = optional(bool, true)
      
      # Sampling configuration
      sampling_rate = optional(number, 0.1) # 10% of traces
      
      # Trace retention
      retention_days = optional(number, 30)
      
      # Service map
      service_map = optional(object({
        enabled = bool
      }))
    }), {})
    
    # Application Performance Monitoring
    apm = optional(object({
      enabled = optional(bool, true)
      
      # Profiling
      profiling = optional(object({
        enabled = bool
        cpu     = optional(bool, true)
        heap    = optional(bool, true)
        wall    = optional(bool, true)
      }))
      
      # Error tracking
      error_tracking = optional(object({
        enabled            = bool
        sample_rate       = optional(number, 1.0)
        ignore_errors     = optional(list(string), [])
        grouping_rules    = optional(list(string), [])
      }))
    }), {})
  })
  
  default = {}
}

# Common labels and tags
variable "labels" {
  description = "Common labels to apply to all resources"
  type        = map(string)
  default = {
    managed_by = "terraform"
    module     = "cloud-abstraction"
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  
  validation {
    condition     = can(regex("^[a-z0-9-]{1,63}$", var.project_name))
    error_message = "Project name must be 1-63 characters, lowercase letters, numbers, and hyphens only"
  }
}

# Feature flags for enabling/disabling services
variable "features" {
  description = "Feature flags for enabling/disabling services"
  type = object({
    compute       = optional(bool, true)
    storage       = optional(bool, true)
    networking    = optional(bool, true)  
    security      = optional(bool, true)
    monitoring    = optional(bool, true)
    cost_optimization = optional(bool, true)
    auto_scaling  = optional(bool, true)
  })
  default = {}
}

# Resource naming configuration
variable "naming" {
  description = "Resource naming configuration"
  type = object({
    prefix           = optional(string, "")
    suffix           = optional(string, "")
    include_environment = optional(bool, true)
    include_region   = optional(bool, false)
    separator       = optional(string, "-")
  })
  default = {}
}