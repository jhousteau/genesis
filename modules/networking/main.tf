/**
 * Networking Module
 *
 * Comprehensive networking infrastructure for GCP
 * Supports VPCs, subnets, firewalls, DNS, load balancers, and VPN connections
 */

locals {
  # Network configuration
  network_name = var.network_name != "" ? var.network_name : "${var.name_prefix}-vpc"

  # Subnet configuration
  subnets = {
    for subnet in var.subnets : subnet.name => merge(subnet, {
      full_name = "${var.name_prefix}-${subnet.name}"
      region    = subnet.region
    })
  }

  # Secondary ranges for subnets
  secondary_ranges = flatten([
    for subnet_name, subnet in local.subnets : [
      for range in lookup(subnet, "secondary_ranges", []) : {
        subnet_name = subnet_name
        range_name  = range.range_name
        ip_cidr     = range.ip_cidr_range
      }
    ]
  ])

  # Firewall rules processing
  firewall_rules = {
    for rule in var.firewall_rules : rule.name => merge(rule, {
      full_name = "${var.name_prefix}-${rule.name}"
    })
  }

  # Load balancer configurations
  load_balancers = {
    for lb in var.load_balancers : lb.name => merge(lb, {
      full_name = "${var.name_prefix}-${lb.name}"
    })
  }

  # DNS zones processing
  dns_zones = {
    for zone in var.dns_zones : zone.name => merge(zone, {
      full_name = "${var.name_prefix}-${zone.name}"
    })
  }

  # NAT gateway configurations
  nat_configs = {
    for nat in var.nat_gateways : "${nat.region}-${nat.name}" => merge(nat, {
      full_name = "${var.name_prefix}-${nat.name}"
    })
  }

  # VPN configurations
  vpn_configs = {
    for vpn in var.vpn_gateways : vpn.name => merge(vpn, {
      full_name = "${var.name_prefix}-${vpn.name}"
    })
  }

  # Default labels
  default_labels = {
    managed_by  = "terraform"
    module      = "networking"
    environment = var.environment
  }

  merged_labels = merge(local.default_labels, var.labels)
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                            = local.network_name
  project                         = var.project_id
  auto_create_subnetworks         = false
  routing_mode                    = var.routing_mode
  delete_default_routes_on_create = var.delete_default_routes
  mtu                             = var.mtu

  # Enable flow logs at network level if specified
  dynamic "enable_ula_internal_ipv6" {
    for_each = var.enable_ipv6 ? [1] : []
    content {
      enable_ula_internal_ipv6 = true
    }
  }
}

# Subnets
resource "google_compute_subnetwork" "subnets" {
  for_each = local.subnets

  name                     = each.value.full_name
  project                  = var.project_id
  network                  = google_compute_network.vpc.id
  region                   = each.value.region
  ip_cidr_range            = each.value.ip_cidr_range
  private_ip_google_access = lookup(each.value, "private_google_access", true)

  # IPv6 configuration
  stack_type       = lookup(each.value, "stack_type", "IPV4_ONLY")
  ipv6_access_type = lookup(each.value, "ipv6_access_type", null)

  # Purpose for special subnets (e.g., proxy-only, internal load balancer)
  purpose = lookup(each.value, "purpose", null)
  role    = lookup(each.value, "role", null)

  # Secondary IP ranges
  dynamic "secondary_ip_range" {
    for_each = {
      for range in local.secondary_ranges : range.range_name => range
      if range.subnet_name == each.key
    }
    content {
      range_name    = secondary_ip_range.value.range_name
      ip_cidr_range = secondary_ip_range.value.ip_cidr
    }
  }

  # Flow logs configuration
  dynamic "log_config" {
    for_each = lookup(each.value, "enable_flow_logs", var.enable_flow_logs) ? [1] : []
    content {
      aggregation_interval = lookup(each.value, "flow_logs_interval", "INTERVAL_5_SEC")
      flow_sampling        = lookup(each.value, "flow_logs_sampling", 0.5)
      metadata             = lookup(each.value, "flow_logs_metadata", "INCLUDE_ALL_METADATA")
      metadata_fields      = lookup(each.value, "flow_logs_filter_expr", null) != null ? ["srcaddr", "dstaddr"] : null
      filter_expr          = lookup(each.value, "flow_logs_filter_expr", null)
    }
  }

  depends_on = [google_compute_network.vpc]
}

# Cloud Router for NAT and VPN
resource "google_compute_router" "routers" {
  for_each = {
    for key, nat in local.nat_configs : nat.region => {
      name   = "${var.name_prefix}-router-${nat.region}"
      region = nat.region
    }...
  }

  name    = each.value[0].name
  project = var.project_id
  region  = each.key
  network = google_compute_network.vpc.id

  bgp {
    asn = var.bgp_asn

    dynamic "advertise_mode" {
      for_each = var.bgp_advertise_mode != null ? [1] : []
      content {
        advertise_mode    = var.bgp_advertise_mode
        advertised_groups = var.bgp_advertised_groups
      }
    }
  }
}

# NAT Gateways
resource "google_compute_router_nat" "nat_gateways" {
  for_each = local.nat_configs

  name   = each.value.full_name
  router = google_compute_router.routers[each.value.region].name
  region = each.value.region

  nat_ip_allocate_option             = lookup(each.value, "nat_ip_allocate_option", "AUTO_ONLY")
  source_subnetwork_ip_ranges_to_nat = lookup(each.value, "source_subnetwork_ip_ranges_to_nat", "ALL_SUBNETWORKS_ALL_IP_RANGES")

  # NAT IP addresses (if specified)
  dynamic "nat_ips" {
    for_each = lookup(each.value, "nat_ips", [])
    content {
      name = nat_ips.value
    }
  }

  # Subnetwork-specific NAT configuration
  dynamic "subnetwork" {
    for_each = lookup(each.value, "subnetworks", [])
    content {
      name                    = subnetwork.value.name
      source_ip_ranges_to_nat = subnetwork.value.source_ip_ranges_to_nat

      dynamic "secondary_ip_range_names" {
        for_each = lookup(subnetwork.value, "secondary_ip_range_names", [])
        content {
          secondary_ip_range_names = secondary_ip_range_names.value
        }
      }
    }
  }

  # Logging configuration
  log_config {
    enable = lookup(each.value, "enable_logging", true)
    filter = lookup(each.value, "log_filter", "ERRORS_ONLY")
  }

  # Timeout configurations
  min_ports_per_vm                 = lookup(each.value, "min_ports_per_vm", 64)
  max_ports_per_vm                 = lookup(each.value, "max_ports_per_vm", 65536)
  udp_idle_timeout_sec             = lookup(each.value, "udp_idle_timeout_sec", 30)
  tcp_established_idle_timeout_sec = lookup(each.value, "tcp_established_idle_timeout_sec", 1200)
  tcp_transitory_idle_timeout_sec  = lookup(each.value, "tcp_transitory_idle_timeout_sec", 30)
  icmp_idle_timeout_sec            = lookup(each.value, "icmp_idle_timeout_sec", 30)

  depends_on = [google_compute_router.routers]
}

# Firewall Rules
resource "google_compute_firewall" "rules" {
  for_each = local.firewall_rules

  name    = each.value.full_name
  project = var.project_id
  network = google_compute_network.vpc.name

  description = lookup(each.value, "description", "Firewall rule ${each.value.name}")
  direction   = lookup(each.value, "direction", "INGRESS")
  priority    = lookup(each.value, "priority", 1000)

  # Source/destination configuration
  source_ranges           = lookup(each.value, "source_ranges", null)
  destination_ranges      = lookup(each.value, "destination_ranges", null)
  source_tags             = lookup(each.value, "source_tags", null)
  target_tags             = lookup(each.value, "target_tags", null)
  source_service_accounts = lookup(each.value, "source_service_accounts", null)
  target_service_accounts = lookup(each.value, "target_service_accounts", null)

  # Action
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

  # Logging
  dynamic "log_config" {
    for_each = lookup(each.value, "enable_logging", false) ? [1] : []
    content {
      metadata = lookup(each.value, "log_metadata", "INCLUDE_ALL_METADATA")
    }
  }

  depends_on = [google_compute_network.vpc]
}

# DNS Zones
resource "google_dns_managed_zone" "zones" {
  for_each = local.dns_zones

  name        = each.value.full_name
  project     = var.project_id
  dns_name    = each.value.dns_name
  description = lookup(each.value, "description", "DNS zone for ${each.value.dns_name}")

  visibility = lookup(each.value, "visibility", "public")

  # Private zone configuration
  dynamic "private_visibility_config" {
    for_each = lookup(each.value, "visibility", "public") == "private" ? [1] : []
    content {
      dynamic "networks" {
        for_each = lookup(each.value, "private_visibility_config_networks", [google_compute_network.vpc.id])
        content {
          network_url = networks.value
        }
      }

      dynamic "gke_clusters" {
        for_each = lookup(each.value, "private_visibility_config_gke_clusters", [])
        content {
          gke_cluster_name = gke_clusters.value
        }
      }
    }
  }

  # Cloud logging configuration
  dynamic "cloud_logging_config" {
    for_each = lookup(each.value, "enable_logging", false) ? [1] : []
    content {
      enable_logging = true
    }
  }

  # DNSSEC configuration
  dynamic "dnssec_config" {
    for_each = lookup(each.value, "enable_dnssec", false) ? [1] : []
    content {
      state         = "on"
      non_existence = lookup(each.value, "dnssec_non_existence", "nsec3")

      dynamic "default_key_specs" {
        for_each = lookup(each.value, "dnssec_key_specs", [])
        content {
          algorithm  = default_key_specs.value.algorithm
          key_length = default_key_specs.value.key_length
          key_type   = default_key_specs.value.key_type
        }
      }
    }
  }

  # Forwarding configuration for private zones
  dynamic "forwarding_config" {
    for_each = lookup(each.value, "forwarding_config", null) != null ? [each.value.forwarding_config] : []
    content {
      dynamic "target_name_servers" {
        for_each = forwarding_config.value.target_name_servers
        content {
          ipv4_address    = target_name_servers.value.ipv4_address
          forwarding_path = lookup(target_name_servers.value, "forwarding_path", "default")
        }
      }
    }
  }

  # Peering configuration
  dynamic "peering_config" {
    for_each = lookup(each.value, "peering_config", null) != null ? [each.value.peering_config] : []
    content {
      target_network {
        network_url = peering_config.value.target_network_url
      }
    }
  }

  labels = local.merged_labels
}

# DNS Records
resource "google_dns_record_set" "records" {
  for_each = {
    for record in var.dns_records : "${record.zone}-${record.name}-${record.type}" => merge(record, {
      zone_name = local.dns_zones[record.zone].full_name
    })
  }

  project      = var.project_id
  managed_zone = each.value.zone_name
  name         = each.value.name
  type         = each.value.type
  ttl          = lookup(each.value, "ttl", 300)
  rrdatas      = each.value.rrdatas

  depends_on = [google_dns_managed_zone.zones]
}

# Static IP addresses for load balancers
resource "google_compute_global_address" "lb_addresses" {
  for_each = {
    for lb in var.load_balancers : lb.name => lb
    if lookup(lb, "create_static_ip", false) && lookup(lb, "type", "external") == "external"
  }

  name         = "${var.name_prefix}-${each.value.name}-ip"
  project      = var.project_id
  ip_version   = lookup(each.value, "ip_version", "IPV4")
  address_type = "EXTERNAL"
}

# Regional static IP addresses
resource "google_compute_address" "regional_lb_addresses" {
  for_each = {
    for lb in var.load_balancers : lb.name => lb
    if lookup(lb, "create_static_ip", false) && lookup(lb, "type", "external") == "internal"
  }

  name         = "${var.name_prefix}-${each.value.name}-ip"
  project      = var.project_id
  region       = each.value.region
  subnetwork   = lookup(each.value, "subnetwork", null)
  address_type = "INTERNAL"
}

# VPN Gateways
resource "google_compute_vpn_gateway" "vpn_gateways" {
  for_each = local.vpn_configs

  name    = each.value.full_name
  project = var.project_id
  network = google_compute_network.vpc.id
  region  = each.value.region
}

# VPN Tunnels
resource "google_compute_vpn_tunnel" "vpn_tunnels" {
  for_each = {
    for tunnel in flatten([
      for vpn_name, vpn in local.vpn_configs : [
        for tunnel in lookup(vpn, "tunnels", []) : {
          key         = "${vpn_name}-${tunnel.name}"
          vpn_name    = vpn_name
          tunnel_name = tunnel.name
          config      = tunnel
          vpn_config  = vpn
        }
      ]
    ]) : tunnel.key => tunnel
  }

  name          = "${each.value.vpn_config.full_name}-${each.value.config.name}"
  project       = var.project_id
  region        = each.value.vpn_config.region
  peer_ip       = each.value.config.peer_ip
  shared_secret = each.value.config.shared_secret

  target_vpn_gateway = google_compute_vpn_gateway.vpn_gateways[each.value.vpn_name].id

  local_traffic_selector  = lookup(each.value.config, "local_traffic_selector", ["0.0.0.0/0"])
  remote_traffic_selector = lookup(each.value.config, "remote_traffic_selector", ["0.0.0.0/0"])

  ike_version = lookup(each.value.config, "ike_version", 2)

  depends_on = [google_compute_vpn_gateway.vpn_gateways]
}

# Routes for VPN
resource "google_compute_route" "vpn_routes" {
  for_each = {
    for route in flatten([
      for tunnel_key, tunnel in google_compute_vpn_tunnel.vpn_tunnels : [
        for route in lookup(local.vpn_configs[split("-", tunnel_key)[0]].tunnels[tonumber(split("-", tunnel_key)[1])], "routes", []) : {
          key        = "${tunnel_key}-${route.dest_range}"
          tunnel_key = tunnel_key
          config     = route
        }
      ]
    ]) : route.key => route
  }

  name                = "${var.name_prefix}-vpn-route-${each.value.config.dest_range}"
  project             = var.project_id
  network             = google_compute_network.vpc.name
  dest_range          = each.value.config.dest_range
  priority            = lookup(each.value.config, "priority", 1000)
  next_hop_vpn_tunnel = google_compute_vpn_tunnel.vpn_tunnels[each.value.tunnel_key].id

  depends_on = [google_compute_vpn_tunnel.vpn_tunnels]
}

# Network peering connections
resource "google_compute_network_peering" "peerings" {
  for_each = {
    for peering in var.network_peerings : peering.name => peering
  }

  name         = "${var.name_prefix}-${each.value.name}"
  network      = google_compute_network.vpc.self_link
  peer_network = each.value.peer_network

  auto_create_routes                  = lookup(each.value, "auto_create_routes", true)
  import_custom_routes                = lookup(each.value, "import_custom_routes", false)
  export_custom_routes                = lookup(each.value, "export_custom_routes", false)
  import_subnet_routes_with_public_ip = lookup(each.value, "import_subnet_routes_with_public_ip", false)
  export_subnet_routes_with_public_ip = lookup(each.value, "export_subnet_routes_with_public_ip", false)

  depends_on = [google_compute_network.vpc]
}
