/**
 * Security Templates Variables
 *
 * Configuration variables for security controls and access management
 */

# Core Configuration
variable "project_id" {
  description = "GCP project ID for security resources"
  type        = string
}

variable "region" {
  description = "GCP region for security resources"
  type        = string
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
  description = "VPC network ID for security rules"
  type        = string
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace for agent workloads"
  type        = string
  default     = "genesis-agents"
}

# IAM Permissions Configuration
variable "standard_compute_permissions" {
  description = "Standard compute permissions for agents"
  type        = list(string)
  default = [
    "compute.instances.get",
    "compute.instances.list",
    "compute.zones.get",
    "compute.zones.list"
  ]
}

variable "elevated_compute_permissions" {
  description = "Elevated compute permissions for infrastructure agents"
  type        = list(string)
  default = [
    "compute.instances.*",
    "compute.instanceGroups.*",
    "compute.instanceTemplates.*",
    "compute.autoscalers.*",
    "compute.zones.*",
    "compute.regions.*",
    "compute.networks.get",
    "compute.subnetworks.get",
    "compute.firewalls.get"
  ]
}

variable "standard_storage_permissions" {
  description = "Standard storage permissions for agents"
  type        = list(string)
  default = [
    "storage.objects.get",
    "storage.objects.list"
  ]
}

variable "elevated_storage_permissions" {
  description = "Elevated storage permissions for data agents"
  type        = list(string)
  default = [
    "storage.objects.*",
    "storage.buckets.get",
    "storage.buckets.list"
  ]
}

variable "standard_network_permissions" {
  description = "Standard network permissions for agents"
  type        = list(string)
  default = [
    "compute.networks.get",
    "compute.subnetworks.get"
  ]
}

variable "elevated_network_permissions" {
  description = "Elevated network permissions for platform agents"
  type        = list(string)
  default = [
    "compute.networks.*",
    "compute.subnetworks.*",
    "compute.firewalls.get",
    "compute.routes.get",
    "servicenetworking.services.get"
  ]
}

# Kubernetes RBAC Configuration
variable "kubernetes_rbac_rules" {
  description = "RBAC rules for each agent type"
  type = map(list(object({
    api_groups = list(string)
    resources  = list(string)
    verbs      = list(string)
  })))
  default = {
    # Backend Developer permissions
    "backend-developer" = [
      {
        api_groups = [""]
        resources  = ["pods", "services", "endpoints"]
        verbs      = ["get", "list", "watch"]
      },
      {
        api_groups = ["apps"]
        resources  = ["deployments", "replicasets"]
        verbs      = ["get", "list", "watch"]
      }
    ]

    # Frontend Developer permissions
    "frontend-developer" = [
      {
        api_groups = [""]
        resources  = ["services", "endpoints"]
        verbs      = ["get", "list", "watch"]
      },
      {
        api_groups = ["networking.k8s.io"]
        resources  = ["ingresses"]
        verbs      = ["get", "list", "watch"]
      }
    ]

    # Platform Engineer permissions (elevated)
    "platform-engineer" = [
      {
        api_groups = ["*"]
        resources  = ["*"]
        verbs      = ["*"]
      }
    ]

    # Data Engineer permissions
    "data-engineer" = [
      {
        api_groups = [""]
        resources  = ["pods", "services", "persistentvolumes", "persistentvolumeclaims"]
        verbs      = ["get", "list", "watch", "create", "update", "patch"]
      },
      {
        api_groups = ["batch"]
        resources  = ["jobs", "cronjobs"]
        verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
      }
    ]

    # Integration Agent permissions
    "integration-agent" = [
      {
        api_groups = [""]
        resources  = ["services", "endpoints", "configmaps"]
        verbs      = ["get", "list", "watch", "create", "update", "patch"]
      },
      {
        api_groups = ["networking.k8s.io"]
        resources  = ["networkpolicies"]
        verbs      = ["get", "list", "watch"]
      }
    ]

    # QA Automation permissions
    "qa-automation" = [
      {
        api_groups = [""]
        resources  = ["pods", "services"]
        verbs      = ["get", "list", "watch", "create", "delete"]
      },
      {
        api_groups = ["batch"]
        resources  = ["jobs"]
        verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
      }
    ]

    # SRE Agent permissions (elevated)
    "sre-agent" = [
      {
        api_groups = [""]
        resources  = ["*"]
        verbs      = ["get", "list", "watch", "create", "update", "patch"]
      },
      {
        api_groups = ["apps", "extensions"]
        resources  = ["*"]
        verbs      = ["get", "list", "watch", "create", "update", "patch"]
      },
      {
        api_groups = ["monitoring.coreos.com"]
        resources  = ["*"]
        verbs      = ["*"]
      }
    ]

    # Security Agent permissions (security-focused)
    "security-agent" = [
      {
        api_groups = [""]
        resources  = ["*"]
        verbs      = ["get", "list", "watch"]
      },
      {
        api_groups = ["policy"]
        resources  = ["*"]
        verbs      = ["*"]
      },
      {
        api_groups = ["networking.k8s.io"]
        resources  = ["networkpolicies"]
        verbs      = ["*"]
      },
      {
        api_groups = ["security.istio.io"]
        resources  = ["*"]
        verbs      = ["*"]
      }
    ]

    # DevOps Agent permissions (deployment-focused)
    "devops-agent" = [
      {
        api_groups = ["apps"]
        resources  = ["deployments", "replicasets", "daemonsets", "statefulsets"]
        verbs      = ["*"]
      },
      {
        api_groups = [""]
        resources  = ["services", "configmaps", "secrets"]
        verbs      = ["*"]
      },
      {
        api_groups = ["autoscaling"]
        resources  = ["horizontalpodautoscalers"]
        verbs      = ["*"]
      }
    ]

    # Project Manager permissions (read-only)
    "project-manager" = [
      {
        api_groups = [""]
        resources  = ["*"]
        verbs      = ["get", "list", "watch"]
      },
      {
        api_groups = ["apps", "extensions"]
        resources  = ["*"]
        verbs      = ["get", "list", "watch"]
      }
    ]

    # Architect permissions (read-only + design)
    "architect" = [
      {
        api_groups = [""]
        resources  = ["*"]
        verbs      = ["get", "list", "watch"]
      },
      {
        api_groups = ["apiextensions.k8s.io"]
        resources  = ["customresourcedefinitions"]
        verbs      = ["get", "list", "watch", "create", "update", "patch"]
      }
    ]

    # Tech Lead permissions (oversight)
    "tech-lead" = [
      {
        api_groups = [""]
        resources  = ["*"]
        verbs      = ["get", "list", "watch"]
      },
      {
        api_groups = ["apps", "extensions"]
        resources  = ["*"]
        verbs      = ["get", "list", "watch", "update", "patch"]
      }
    ]
  }
}

# Workload Identity Configuration
variable "enable_workload_identity" {
  description = "Enable Workload Identity for Kubernetes service accounts"
  type        = bool
  default     = true
}

# Firewall Security Rules
variable "firewall_security_rules" {
  description = "Security-focused firewall rules"
  type = map(object({
    description        = string
    direction          = string
    priority           = number
    source_ranges      = optional(list(string))
    destination_ranges = optional(list(string))
    source_tags        = optional(list(string))
    target_tags        = optional(list(string))
    allow = optional(list(object({
      protocol = string
      ports    = optional(list(string))
    })), [])
    deny = optional(list(object({
      protocol = string
      ports    = optional(list(string))
    })), [])
  }))
  default = {
    "deny-all-ingress" = {
      description   = "Deny all ingress traffic by default"
      direction     = "INGRESS"
      priority      = 65534
      source_ranges = ["0.0.0.0/0"]
      deny = [{
        protocol = "all"
      }]
    }

    "allow-internal-agents" = {
      description   = "Allow communication between agent VMs"
      direction     = "INGRESS"
      priority      = 1000
      source_ranges = ["10.0.0.0/8"]
      target_tags   = ["agent-vm"]
      allow = [{
        protocol = "tcp"
        ports    = ["8080", "9090", "22"]
      }]
    }

    "allow-health-checks" = {
      description   = "Allow Google Cloud health checks"
      direction     = "INGRESS"
      priority      = 1000
      source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
      target_tags   = ["agent-vm"]
      allow = [{
        protocol = "tcp"
        ports    = ["8080"]
      }]
    }

    "deny-sensitive-ports" = {
      description   = "Deny access to sensitive ports"
      direction     = "INGRESS"
      priority      = 500
      source_ranges = ["0.0.0.0/0"]
      deny = [{
        protocol = "tcp"
        ports    = ["3389", "5432", "3306", "1433", "27017"]
      }]
    }
  }
}

variable "enable_firewall_logging" {
  description = "Enable firewall rule logging"
  type        = bool
  default     = true
}

# Kubernetes Network Policies
variable "enable_kubernetes_network_policies" {
  description = "Enable Kubernetes network policies"
  type        = bool
  default     = true
}

variable "standard_ingress_rules" {
  description = "Standard ingress rules for network policies"
  type = list(object({
    namespace = string
    port      = number
    protocol  = optional(string, "TCP")
  }))
  default = [
    {
      namespace = "genesis-agents"
      port      = 8080
    },
    {
      namespace = "istio-system"
      port      = 15090
    }
  ]
}

variable "high_security_ingress_rules" {
  description = "High security ingress rules for sensitive agents"
  type = list(object({
    namespace = string
    port      = number
    protocol  = optional(string, "TCP")
  }))
  default = [
    {
      namespace = "genesis-agents"
      port      = 8080
    }
  ]
}

variable "standard_egress_rules" {
  description = "Standard egress rules for network policies"
  type = list(object({
    namespace = string
    port      = number
    protocol  = optional(string, "TCP")
  }))
  default = [
    {
      namespace = "kube-system"
      port      = 53
      protocol  = "UDP"
    },
    {
      namespace = "istio-system"
      port      = 15010
    }
  ]
}

variable "high_security_egress_rules" {
  description = "High security egress rules for sensitive agents"
  type = list(object({
    namespace = string
    port      = number
    protocol  = optional(string, "TCP")
  }))
  default = [
    {
      namespace = "kube-system"
      port      = 53
      protocol  = "UDP"
    }
  ]
}

# Pod Security Standards
variable "enable_pod_security_standards" {
  description = "Enable Pod Security Standards"
  type        = bool
  default     = true
}

# Secret Management
variable "agent_secrets" {
  description = "Secrets for agent operations"
  type = map(object({
    value      = string
    type       = string
    agent_type = optional(string, "all")
  }))
  default   = {}
  sensitive = true
}

variable "kubernetes_secrets" {
  description = "Kubernetes secrets from Secret Manager"
  type = map(object({
    type                  = string
    kubernetes_type       = optional(string, "Opaque")
    secret_manager_secret = string
    data                  = map(string)
  }))
  default   = {}
  sensitive = true
}

# Security Monitoring
variable "enable_security_audit_logging" {
  description = "Enable security audit logging to BigQuery"
  type        = bool
  default     = true
}

variable "security_audit_dataset" {
  description = "BigQuery dataset for security audit logs"
  type        = string
  default     = "genesis_security_audit"
}

variable "security_audit_admin_email" {
  description = "Email for security audit dataset admin"
  type        = string
  default     = ""
}

variable "enable_asset_inventory_feed" {
  description = "Enable Cloud Asset Inventory feed for security monitoring"
  type        = bool
  default     = false
}

variable "security_monitoring_topic" {
  description = "Pub/Sub topic for security monitoring"
  type        = string
  default     = "genesis-security-monitoring"
}

# Binary Authorization
variable "enable_binary_authorization" {
  description = "Enable Binary Authorization for container security"
  type        = bool
  default     = false
}

variable "container_registry" {
  description = "Container registry for Binary Authorization whitelist"
  type        = string
  default     = "us-central1-docker.pkg.dev"
}

variable "gke_clusters" {
  description = "List of GKE clusters for Binary Authorization"
  type        = list(string)
  default     = []
}

variable "attestor_public_key" {
  description = "PGP public key for Binary Authorization attestor"
  type        = string
  default     = ""
  sensitive   = true
}
