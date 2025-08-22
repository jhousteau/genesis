/**
 * Outputs for Networking Module
 */

# Network outputs
output "network" {
  description = "The VPC network"
  value = {
    id            = google_compute_network.vpc.id
    name          = google_compute_network.vpc.name
    self_link     = google_compute_network.vpc.self_link
    routing_mode  = google_compute_network.vpc.routing_mode
    mtu          = google_compute_network.vpc.mtu
  }
}

output "network_id" {
  description = "The ID of the VPC network"
  value       = google_compute_network.vpc.id
}

output "network_name" {
  description = "The name of the VPC network"
  value       = google_compute_network.vpc.name
}

output "network_self_link" {
  description = "The URI of the VPC network"
  value       = google_compute_network.vpc.self_link
}

# Subnet outputs
output "subnets" {
  description = "The created subnets"
  value = {
    for k, v in google_compute_subnetwork.subnets : k => {
      id                = v.id
      name              = v.name
      self_link         = v.self_link
      ip_cidr_range     = v.ip_cidr_range
      region            = v.region
      gateway_address   = v.gateway_address
      secondary_ip_range = v.secondary_ip_range
    }
  }
}

output "subnet_ids" {
  description = "Map of subnet names to IDs"
  value       = { for k, v in google_compute_subnetwork.subnets : k => v.id }
}

output "subnet_self_links" {
  description = "Map of subnet names to self-links"
  value       = { for k, v in google_compute_subnetwork.subnets : k => v.self_link }
}

output "subnet_regions" {
  description = "Map of subnet names to regions"
  value       = { for k, v in google_compute_subnetwork.subnets : k => v.region }
}

output "subnet_cidr_ranges" {
  description = "Map of subnet names to CIDR ranges"
  value       = { for k, v in google_compute_subnetwork.subnets : k => v.ip_cidr_range }
}

# Router outputs
output "routers" {
  description = "The created Cloud Routers"
  value = {
    for k, v in google_compute_router.routers : k => {
      id        = v.id
      name      = v.name
      self_link = v.self_link
      region    = v.region
    }
  }
}

# NAT outputs
output "nat_gateways" {
  description = "The created NAT gateways"
  value = {
    for k, v in google_compute_router_nat.nat_gateways : k => {
      id     = v.id
      name   = v.name
      region = v.region
      router = v.router
    }
  }
}

# Firewall outputs
output "firewall_rules" {
  description = "The created firewall rules"
  value = {
    for k, v in google_compute_firewall.rules : k => {
      id        = v.id
      name      = v.name
      self_link = v.self_link
      direction = v.direction
      priority  = v.priority
    }
  }
}

# DNS outputs
output "dns_zones" {
  description = "The created DNS zones"
  value = {
    for k, v in google_dns_managed_zone.zones : k => {
      id           = v.id
      name         = v.name
      dns_name     = v.dns_name
      name_servers = v.name_servers
      visibility   = v.visibility
    }
  }
}

output "dns_zone_name_servers" {
  description = "Map of DNS zone names to their name servers"
  value       = { for k, v in google_dns_managed_zone.zones : k => v.name_servers }
}

# Load balancer IP outputs
output "load_balancer_ips" {
  description = "Static IP addresses for load balancers"
  value = merge(
    { for k, v in google_compute_global_address.lb_addresses : k => {
      address    = v.address
      id        = v.id
      self_link = v.self_link
      type      = "global"
    }},
    { for k, v in google_compute_address.regional_lb_addresses : k => {
      address    = v.address
      id        = v.id
      self_link = v.self_link
      type      = "regional"
      region    = v.region
    }}
  )
}

# VPN outputs
output "vpn_gateways" {
  description = "The created VPN gateways"
  value = {
    for k, v in google_compute_vpn_gateway.vpn_gateways : k => {
      id        = v.id
      name      = v.name
      self_link = v.self_link
      region    = v.region
    }
  }
}

output "vpn_tunnels" {
  description = "The created VPN tunnels"
  value = {
    for k, v in google_compute_vpn_tunnel.vpn_tunnels : k => {
      id                = v.id
      name              = v.name
      self_link         = v.self_link
      peer_ip           = v.peer_ip
      target_vpn_gateway = v.target_vpn_gateway
    }
  }
}

# Network peering outputs
output "network_peerings" {
  description = "The created network peerings"
  value = {
    for k, v in google_compute_network_peering.peerings : k => {
      id           = v.id
      name         = v.name
      network      = v.network
      peer_network = v.peer_network
      state        = v.state
      state_details = v.state_details
    }
  }
}

# Comprehensive network information
output "network_info" {
  description = "Comprehensive network information for reference by other modules"
  value = {
    network = {
      id        = google_compute_network.vpc.id
      name      = google_compute_network.vpc.name
      self_link = google_compute_network.vpc.self_link
    }
    subnets = { for k, v in google_compute_subnetwork.subnets : k => {
      id            = v.id
      name          = v.name
      self_link     = v.self_link
      ip_cidr_range = v.ip_cidr_range
      region        = v.region
    }}
    firewall_rules = { for k, v in google_compute_firewall.rules : k => {
      id   = v.id
      name = v.name
    }}
    dns_zones = { for k, v in google_dns_managed_zone.zones : k => {
      id           = v.id
      name         = v.name
      dns_name     = v.dns_name
      name_servers = v.name_servers
    }}
    nat_gateways = { for k, v in google_compute_router_nat.nat_gateways : k => {
      id     = v.id
      name   = v.name
      region = v.region
    }}
    vpn_gateways = { for k, v in google_compute_vpn_gateway.vpn_gateways : k => {
      id     = v.id
      name   = v.name
      region = v.region
    }}
  }
}

# Terraform state information for cross-module reference
output "terraform_state" {
  description = "Terraform state information for other modules"
  value = {
    module_version = "1.0.0"
    created_at     = timestamp()
    network_id     = google_compute_network.vpc.id
    project_id     = var.project_id
  }
}