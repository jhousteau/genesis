/**
 * Variables for Networking Module
 */

variable "project_id" {
  description = "The GCP project ID where resources will be created"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "net"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}

# Network Configuration
variable "network_name" {
  description = "Name of the VPC network. If empty, will use name_prefix-vpc"
  type        = string
  default     = ""
}

variable "routing_mode" {
  description = "Network routing mode (REGIONAL or GLOBAL)"
  type        = string
  default     = "REGIONAL"
  
  validation {
    condition     = contains(["REGIONAL", "GLOBAL"], var.routing_mode)
    error_message = "Routing mode must be either REGIONAL or GLOBAL."
  }
}

variable "delete_default_routes" {
  description = "Whether to delete default routes on network creation"
  type        = bool
  default     = false
}

variable "mtu" {
  description = "Maximum Transmission Unit in bytes"
  type        = number
  default     = 1460
  
  validation {
    condition     = var.mtu >= 1460 && var.mtu <= 1500
    error_message = "MTU must be between 1460 and 1500."
  }
}

variable "enable_ipv6" {
  description = "Enable IPv6 on the network"
  type        = bool
  default     = false
}

# Subnet Configuration
variable "subnets" {
  description = "List of subnets to create"
  type = list(object({
    name                     = string
    region                   = string
    ip_cidr_range           = string
    private_google_access   = optional(bool, true)
    stack_type              = optional(string, "IPV4_ONLY")
    ipv6_access_type        = optional(string)
    purpose                 = optional(string)
    role                    = optional(string)
    enable_flow_logs        = optional(bool)
    flow_logs_interval      = optional(string, "INTERVAL_5_SEC")
    flow_logs_sampling      = optional(number, 0.5)
    flow_logs_metadata      = optional(string, "INCLUDE_ALL_METADATA")
    flow_logs_filter_expr   = optional(string)
    secondary_ranges = optional(list(object({
      range_name      = string
      ip_cidr_range   = string
    })), [])
  }))
  default = []
}

variable "enable_flow_logs" {
  description = "Enable flow logs for all subnets by default"
  type        = bool
  default     = true
}

# BGP Configuration
variable "bgp_asn" {
  description = "BGP ASN for Cloud Router"
  type        = number
  default     = 64512
  
  validation {
    condition     = var.bgp_asn >= 64512 && var.bgp_asn <= 65534
    error_message = "BGP ASN must be a private ASN between 64512 and 65534."
  }
}

variable "bgp_advertise_mode" {
  description = "BGP advertise mode (DEFAULT or CUSTOM)"
  type        = string
  default     = null
  
  validation {
    condition     = var.bgp_advertise_mode == null || contains(["DEFAULT", "CUSTOM"], var.bgp_advertise_mode)
    error_message = "BGP advertise mode must be DEFAULT or CUSTOM."
  }
}

variable "bgp_advertised_groups" {
  description = "List of BGP advertised groups"
  type        = list(string)
  default     = []
}

# NAT Gateway Configuration
variable "nat_gateways" {
  description = "NAT gateway configurations"
  type = list(object({
    name                                 = string
    region                              = string
    nat_ip_allocate_option              = optional(string, "AUTO_ONLY")
    source_subnetwork_ip_ranges_to_nat  = optional(string, "ALL_SUBNETWORKS_ALL_IP_RANGES")
    nat_ips                             = optional(list(string), [])
    min_ports_per_vm                    = optional(number, 64)
    max_ports_per_vm                    = optional(number, 65536)
    udp_idle_timeout_sec               = optional(number, 30)
    tcp_established_idle_timeout_sec    = optional(number, 1200)
    tcp_transitory_idle_timeout_sec     = optional(number, 30)
    icmp_idle_timeout_sec              = optional(number, 30)
    enable_logging                      = optional(bool, true)
    log_filter                         = optional(string, "ERRORS_ONLY")
    subnetworks = optional(list(object({
      name                    = string
      source_ip_ranges_to_nat = list(string)
      secondary_ip_range_names = optional(list(string), [])
    })), [])
  }))
  default = []
}

# Firewall Rules
variable "firewall_rules" {
  description = "List of firewall rules"
  type = list(object({
    name                    = string
    description            = optional(string)
    direction              = optional(string, "INGRESS")
    priority               = optional(number, 1000)
    source_ranges          = optional(list(string))
    destination_ranges     = optional(list(string))
    source_tags            = optional(list(string))
    target_tags            = optional(list(string))
    source_service_accounts = optional(list(string))
    target_service_accounts = optional(list(string))
    enable_logging         = optional(bool, false)
    log_metadata           = optional(string, "INCLUDE_ALL_METADATA")
    allow = optional(list(object({
      protocol = string
      ports    = optional(list(string))
    })), [])
    deny = optional(list(object({
      protocol = string
      ports    = optional(list(string))
    })), [])
  }))
  default = []
}

# DNS Configuration
variable "dns_zones" {
  description = "DNS zones to create"
  type = list(object({
    name        = string
    dns_name    = string
    description = optional(string)
    visibility  = optional(string, "public")
    enable_logging = optional(bool, false)
    enable_dnssec  = optional(bool, false)
    dnssec_non_existence = optional(string, "nsec3")
    dnssec_key_specs = optional(list(object({
      algorithm  = string
      key_length = number
      key_type   = string
    })), [])
    private_visibility_config_networks     = optional(list(string), [])
    private_visibility_config_gke_clusters = optional(list(string), [])
    forwarding_config = optional(object({
      target_name_servers = list(object({
        ipv4_address    = string
        forwarding_path = optional(string, "default")
      }))
    }))
    peering_config = optional(object({
      target_network_url = string
    }))
  }))
  default = []
}

variable "dns_records" {
  description = "DNS records to create"
  type = list(object({
    zone    = string  # References zone name from dns_zones
    name    = string
    type    = string
    ttl     = optional(number, 300)
    rrdatas = list(string)
  }))
  default = []
}

# Load Balancer Configuration
variable "load_balancers" {
  description = "Load balancer configurations"
  type = list(object({
    name             = string
    type             = optional(string, "external")  # external, internal
    region           = optional(string)              # Required for internal LBs
    subnetwork       = optional(string)              # For internal LBs
    create_static_ip = optional(bool, false)
    ip_version       = optional(string, "IPV4")
  }))
  default = []
}

# VPN Configuration
variable "vpn_gateways" {
  description = "VPN gateway configurations"
  type = list(object({
    name   = string
    region = string
    tunnels = optional(list(object({
      name                    = string
      peer_ip                 = string
      shared_secret          = string
      ike_version            = optional(number, 2)
      local_traffic_selector  = optional(list(string), ["0.0.0.0/0"])
      remote_traffic_selector = optional(list(string), ["0.0.0.0/0"])
      routes = optional(list(object({
        dest_range = string
        priority   = optional(number, 1000)
      })), [])
    })), [])
  }))
  default = []
}

# Network Peering
variable "network_peerings" {
  description = "Network peering configurations"
  type = list(object({
    name                                = string
    peer_network                        = string
    auto_create_routes                 = optional(bool, true)
    import_custom_routes               = optional(bool, false)
    export_custom_routes               = optional(bool, false)
    import_subnet_routes_with_public_ip = optional(bool, false)
    export_subnet_routes_with_public_ip = optional(bool, false)
  }))
  default = []
}

# Security Configuration
variable "enable_private_google_access" {
  description = "Enable private Google access for all subnets by default"
  type        = bool
  default     = true
}

variable "enable_security_policies" {
  description = "Enable Cloud Armor security policies"
  type        = bool
  default     = false
}

# Cost Optimization
variable "enable_cost_optimization" {
  description = "Enable cost optimization features"
  type        = bool
  default     = true
}

variable "preemptible_instances" {
  description = "Use preemptible instances where possible"
  type        = bool
  default     = false
}

# Multi-region Configuration
variable "multi_region_config" {
  description = "Multi-region configuration for high availability"
  type = object({
    enabled          = bool
    primary_region   = optional(string)
    secondary_region = optional(string)
    enable_cross_region_lb = optional(bool, false)
  })
  default = {
    enabled = false
  }
}

# Monitoring Configuration
variable "enable_monitoring" {
  description = "Enable monitoring and alerting"
  type        = bool
  default     = true
}

variable "monitoring_config" {
  description = "Monitoring configuration"
  type = object({
    enable_uptime_checks = optional(bool, true)
    enable_log_metrics   = optional(bool, true)
    notification_channels = optional(list(string), [])
  })
  default = {}
}

# Compliance Configuration
variable "compliance_config" {
  description = "Compliance and security configuration"
  type = object({
    enable_vpc_flow_logs    = optional(bool, true)
    enable_firewall_logging = optional(bool, true)
    require_ssl_policy      = optional(bool, true)
    allowed_ip_ranges       = optional(list(string), [])
    blocked_ip_ranges       = optional(list(string), [])
  })
  default = {}
}