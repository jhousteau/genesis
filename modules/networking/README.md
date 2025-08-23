# Networking Module

This module provides comprehensive networking infrastructure for Google Cloud Platform, including VPCs, subnets, firewalls, DNS, load balancers, and VPN connections.

## Features

- **VPC Network Management**: Create and configure VPC networks with custom routing
- **Subnet Management**: Create subnets with flow logs, secondary ranges, and regional distribution
- **Firewall Rules**: Comprehensive firewall rule management with logging and compliance
- **DNS Management**: Public and private DNS zones with DNSSEC support
- **NAT Gateways**: Cloud NAT configuration for outbound internet access
- **Load Balancer IPs**: Static IP allocation for external and internal load balancers
- **VPN Connectivity**: Site-to-site VPN with tunnels and routing
- **Network Peering**: VPC network peering for multi-network architectures
- **Security Features**: Private Google Access, VPC Flow Logs, and security policies
- **Multi-region Support**: Cross-region networking and high availability
- **Cost Optimization**: Efficient resource allocation and usage patterns

## Usage

### Basic VPC with Subnets

```hcl
module "networking" {
  source = "./modules/networking"

  project_id   = "my-project-id"
  name_prefix  = "prod"
  environment  = "production"

  subnets = [
    {
      name              = "web-subnet"
      region           = "us-central1"
      ip_cidr_range    = "10.0.1.0/24"
      enable_flow_logs = true
    },
    {
      name              = "app-subnet"
      region           = "us-central1"
      ip_cidr_range    = "10.0.2.0/24"
      secondary_ranges = [
        {
          range_name    = "pods"
          ip_cidr_range = "10.1.0.0/16"
        },
        {
          range_name    = "services"
          ip_cidr_range = "10.2.0.0/16"
        }
      ]
    }
  ]
}
```

### Complete Network with Security

```hcl
module "networking" {
  source = "./modules/networking"

  project_id   = "my-project-id"
  name_prefix  = "secure"
  environment  = "production"

  # VPC Configuration
  routing_mode = "GLOBAL"
  enable_ipv6  = false

  # Subnets
  subnets = [
    {
      name                   = "dmz-subnet"
      region                = "us-central1"
      ip_cidr_range         = "10.0.0.0/24"
      private_google_access = true
      enable_flow_logs      = true
    },
    {
      name                   = "private-subnet"
      region                = "us-central1"
      ip_cidr_range         = "10.0.1.0/24"
      private_google_access = true
      enable_flow_logs      = true
    }
  ]

  # NAT Gateway
  nat_gateways = [
    {
      name   = "nat-gateway"
      region = "us-central1"
    }
  ]

  # Firewall Rules
  firewall_rules = [
    {
      name          = "allow-ssh"
      direction     = "INGRESS"
      priority      = 1000
      source_ranges = ["0.0.0.0/0"]
      target_tags   = ["ssh-allowed"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["22"]
        }
      ]
    },
    {
      name          = "allow-http"
      direction     = "INGRESS"
      priority      = 1000
      source_ranges = ["0.0.0.0/0"]
      target_tags   = ["http-server"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["80", "443"]
        }
      ]
    }
  ]

  # DNS
  dns_zones = [
    {
      name        = "private-zone"
      dns_name    = "internal.example.com."
      description = "Private DNS zone"
      visibility  = "private"
    }
  ]
}
```

### Multi-Region Setup

```hcl
module "networking" {
  source = "./modules/networking"

  project_id   = "my-project-id"
  name_prefix  = "global"
  environment  = "production"

  # Multi-region configuration
  multi_region_config = {
    enabled               = true
    primary_region       = "us-central1"
    secondary_region     = "us-east1"
    enable_cross_region_lb = true
  }

  # Subnets in multiple regions
  subnets = [
    {
      name          = "primary-subnet"
      region        = "us-central1"
      ip_cidr_range = "10.0.1.0/24"
    },
    {
      name          = "secondary-subnet"
      region        = "us-east1"
      ip_cidr_range = "10.0.2.0/24"
    }
  ]

  # NAT gateways in both regions
  nat_gateways = [
    {
      name   = "primary-nat"
      region = "us-central1"
    },
    {
      name   = "secondary-nat"
      region = "us-east1"
    }
  ]
}
```

### VPN Configuration

```hcl
module "networking" {
  source = "./modules/networking"

  project_id   = "my-project-id"
  name_prefix  = "vpn-connected"
  environment  = "production"

  # VPN Gateways
  vpn_gateways = [
    {
      name   = "on-premises-vpn"
      region = "us-central1"
      tunnels = [
        {
          name          = "tunnel-1"
          peer_ip       = "203.0.113.1"
          shared_secret = "your-shared-secret"
          routes = [
            {
              dest_range = "192.168.1.0/24"
            }
          ]
        }
      ]
    }
  ]
}
```

## Module Structure

```
modules/networking/
├── main.tf           # Main networking resources
├── variables.tf      # Input variables
├── outputs.tf        # Output values
├── versions.tf       # Provider version constraints
└── README.md         # This file
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_id | The GCP project ID | `string` | n/a | yes |
| name_prefix | Prefix for resource names | `string` | `"net"` | no |
| environment | Environment name | `string` | `"dev"` | no |
| subnets | List of subnets to create | `list(object)` | `[]` | no |
| firewall_rules | List of firewall rules | `list(object)` | `[]` | no |
| dns_zones | DNS zones to create | `list(object)` | `[]` | no |
| nat_gateways | NAT gateway configurations | `list(object)` | `[]` | no |
| vpn_gateways | VPN gateway configurations | `list(object)` | `[]` | no |

## Outputs

| Name | Description |
|------|-------------|
| network_id | The ID of the VPC network |
| network_name | The name of the VPC network |
| subnet_ids | Map of subnet names to IDs |
| firewall_rules | The created firewall rules |
| dns_zones | The created DNS zones |
| nat_gateways | The created NAT gateways |

## Advanced Features

### Flow Logs and Monitoring

The module automatically configures VPC Flow Logs for network monitoring and troubleshooting:

```hcl
subnets = [
  {
    name                  = "monitored-subnet"
    region               = "us-central1"
    ip_cidr_range        = "10.0.1.0/24"
    enable_flow_logs     = true
    flow_logs_sampling   = 0.1  # 10% sampling
    flow_logs_metadata   = "INCLUDE_ALL_METADATA"
    flow_logs_filter_expr = "inIpv4 in {'10.0.0.0/8'}"
  }
]
```

### Security Policies

Configure Cloud Armor security policies for additional protection:

```hcl
enable_security_policies = true
compliance_config = {
  enable_vpc_flow_logs    = true
  enable_firewall_logging = true
  require_ssl_policy      = true
  allowed_ip_ranges       = ["10.0.0.0/8"]
  blocked_ip_ranges       = ["192.168.100.0/24"]
}
```

### Cost Optimization

Enable cost optimization features:

```hcl
enable_cost_optimization = true
preemptible_instances   = true
```

## Integration with Other Modules

This networking module is designed to integrate seamlessly with other infrastructure modules:

### With Compute Module

```hcl
module "networking" {
  source = "./modules/networking"
  # networking configuration
}

module "compute" {
  source = "./modules/compute"

  network_id    = module.networking.network_id
  subnet_ids    = module.networking.subnet_ids
  # compute configuration
}
```

### With Security Module

```hcl
module "security" {
  source = "./modules/security"

  network_id     = module.networking.network_id
  firewall_rules = module.networking.firewall_rules
  # security configuration
}
```

## Best Practices

1. **Network Segmentation**: Use separate subnets for different tiers (web, app, data)
2. **Security First**: Enable flow logs and firewall logging for audit trails
3. **High Availability**: Deploy across multiple regions for critical workloads
4. **Cost Management**: Use appropriate instance types and enable cost optimization
5. **Monitoring**: Configure comprehensive monitoring and alerting
6. **Compliance**: Follow organizational security and compliance requirements

## Version Compatibility

- Terraform >= 1.3
- Google Provider >= 5.0
- Google Beta Provider >= 5.0

## Contributing

When contributing to this module:

1. Maintain backward compatibility
2. Update documentation for new features
3. Include examples for complex configurations
4. Test across multiple GCP regions
5. Follow Terraform best practices
