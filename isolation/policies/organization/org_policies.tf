# Organization-level Security Policies
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Enforces security baselines across all projects in the organization

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0"
    }
  }
}

# Organization ID - must be provided
variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "environment" {
  description = "Environment (dev, test, staging, prod)"
  type        = string
  default     = "prod"
}

variable "enforce_policies" {
  description = "Whether to enforce policies (true) or just report violations (false)"
  type        = bool
  default     = true
}

variable "allowed_regions" {
  description = "List of allowed regions for resource creation"
  type        = list(string)
  default = [
    "us-central1",
    "us-east1",
    "us-east4",
    "us-west1",
    "us-west2",
    "europe-west1",
    "europe-west2",
    "europe-west3"
  ]
}

variable "blocked_services" {
  description = "List of services that should be blocked"
  type        = list(string)
  default = [
    "bigquerydatatransfer.googleapis.com",
    "clouddebugger.googleapis.com"
  ]
}

variable "require_os_login" {
  description = "Require OS Login for all VM instances"
  type        = bool
  default     = true
}

variable "disable_service_account_key_creation" {
  description = "Disable service account key creation"
  type        = bool
  default     = true
}

variable "disable_service_account_key_upload" {
  description = "Disable service account key upload"
  type        = bool
  default     = true
}

variable "require_shielded_vms" {
  description = "Require shielded VMs for all instances"
  type        = bool
  default     = true
}

variable "disable_vm_serial_port" {
  description = "Disable VM serial port access"
  type        = bool
  default     = true
}

variable "disable_vm_ip_forwarding" {
  description = "Disable VM IP forwarding"
  type        = bool
  default     = true
}

variable "require_ssl_certificates" {
  description = "Require SSL certificates for load balancers"
  type        = bool
  default     = true
}

variable "disable_default_service_account" {
  description = "Disable automatic creation of default service accounts"
  type        = bool
  default     = true
}

variable "allowed_policy_member_customer_ids" {
  description = "Customer IDs allowed to be granted IAM policies"
  type        = list(string)
  default     = []
}

# Local values for policy configuration
locals {
  enforcement_action = var.enforce_policies ? "enforce" : "dryRun"

  # Standard security policies that should be applied
  base_policies = {
    # Compute Engine policies
    "compute.requireShieldedVm" = {
      constraint = "constraints/compute.requireShieldedVm"
      enforce    = var.require_shielded_vms
    }
    "compute.requireOsLogin" = {
      constraint = "constraints/compute.requireOsLogin"
      enforce    = var.require_os_login
    }
    "compute.disableSerialPortAccess" = {
      constraint = "constraints/compute.disableSerialPortAccess"
      enforce    = var.disable_vm_serial_port
    }
    "compute.disableIpForwarding" = {
      constraint = "constraints/compute.vmCanIpForward"
      enforce    = var.disable_vm_ip_forwarding
    }
    "compute.disableVmExternalIpAccess" = {
      constraint = "constraints/compute.vmExternalIpAccess"
      enforce    = false # Often too restrictive, enable per project
    }

    # IAM policies
    "iam.disableServiceAccountKeyCreation" = {
      constraint = "constraints/iam.disableServiceAccountKeyCreation"
      enforce    = var.disable_service_account_key_creation
    }
    "iam.disableServiceAccountKeyUpload" = {
      constraint = "constraints/iam.disableServiceAccountKeyUpload"
      enforce    = var.disable_service_account_key_upload
    }
    "iam.automaticIamGrantsForDefaultServiceAccounts" = {
      constraint = "constraints/iam.automaticIamGrantsForDefaultServiceAccounts"
      enforce    = var.disable_default_service_account
    }

    # Storage policies
    "storage.uniformBucketLevelAccess" = {
      constraint = "constraints/storage.uniformBucketLevelAccess"
      enforce    = true
    }
    "storage.publicAccessPrevention" = {
      constraint = "constraints/storage.publicAccessPrevention"
      enforce    = true
    }

    # SQL policies
    "sql.restrictAuthorizedNetworks" = {
      constraint = "constraints/sql.restrictAuthorizedNetworks"
      enforce    = true
    }
    "sql.requireSsl" = {
      constraint = "constraints/sql.requireSsl"
      enforce    = true
    }
  }

  # Policies that require specific values
  list_constraint_policies = {
    "compute.restrictLoadBalancerCreationForTypes" = {
      constraint = "constraints/compute.restrictLoadBalancerCreationForTypes"
      deny_list = [
        "EXTERNAL"
      ]
      enforce = var.require_ssl_certificates
    }
    "serviceuser.services" = {
      constraint = "constraints/serviceuser.services"
      deny_list  = var.blocked_services
      enforce    = length(var.blocked_services) > 0
    }
  }

  # Location-based policies
  location_policies = {
    "gcp.resourceLocations" = {
      constraint = "constraints/gcp.resourceLocations"
      allow_list = var.allowed_regions
      enforce    = length(var.allowed_regions) > 0
    }
  }
}

# Boolean constraint policies
resource "google_organization_policy" "boolean_constraints" {
  for_each = {
    for k, v in local.base_policies : k => v if v.enforce
  }

  org_id     = var.organization_id
  constraint = each.value.constraint

  boolean_policy {
    enforced = true
  }
}

# List constraint policies with deny lists
resource "google_organization_policy" "list_deny_constraints" {
  for_each = {
    for k, v in local.list_constraint_policies : k => v if v.enforce && length(v.deny_list) > 0
  }

  org_id     = var.organization_id
  constraint = each.value.constraint

  list_policy {
    deny {
      values = each.value.deny_list
    }
  }
}

# List constraint policies with allow lists
resource "google_organization_policy" "list_allow_constraints" {
  for_each = {
    for k, v in local.location_policies : k => v if v.enforce && length(v.allow_list) > 0
  }

  org_id     = var.organization_id
  constraint = each.value.constraint

  list_policy {
    allow {
      values = each.value.allow_list
    }
  }
}

# IAM policy member restriction (if customer IDs provided)
resource "google_organization_policy" "iam_allowed_policy_member_domains" {
  count = length(var.allowed_policy_member_customer_ids) > 0 ? 1 : 0

  org_id     = var.organization_id
  constraint = "constraints/iam.allowedPolicyMemberDomains"

  list_policy {
    allow {
      values = formatlist("C%s", var.allowed_policy_member_customer_ids)
    }
  }
}

# Environment-specific overrides
# Development environments may need more permissive policies
resource "google_organization_policy" "dev_overrides" {
  for_each = var.environment == "dev" ? toset([
    "constraints/compute.vmExternalIpAccess",
    "constraints/iam.disableServiceAccountKeyCreation"
  ]) : toset([])

  org_id     = var.organization_id
  constraint = each.key

  # More permissive for development
  restore_policy {
    default = true
  }
}

# Outputs for monitoring and reporting
output "enforced_policies" {
  description = "List of enforced organization policies"
  value = concat(
    [for k, v in local.base_policies : v.constraint if v.enforce],
    [for k, v in local.list_constraint_policies : v.constraint if v.enforce],
    [for k, v in local.location_policies : v.constraint if v.enforce]
  )
}

output "policy_summary" {
  description = "Summary of organization policy configuration"
  value = {
    total_policies_configured = (
      length(google_organization_policy.boolean_constraints) +
      length(google_organization_policy.list_deny_constraints) +
      length(google_organization_policy.list_allow_constraints)
    )
    enforcement_mode     = local.enforcement_action
    environment          = var.environment
    allowed_regions      = var.allowed_regions
    blocked_services     = var.blocked_services
    require_shielded_vms = var.require_shielded_vms
    require_os_login     = var.require_os_login
    disable_sa_keys      = var.disable_service_account_key_creation
  }
}

# Data source for existing policies (for auditing)
data "google_organization_policy" "existing_policies" {
  for_each = toset([
    "constraints/compute.requireShieldedVm",
    "constraints/compute.requireOsLogin",
    "constraints/iam.disableServiceAccountKeyCreation",
    "constraints/storage.uniformBucketLevelAccess"
  ])

  org_id     = var.organization_id
  constraint = each.key
}

# Local file output for policy documentation
resource "local_file" "policy_documentation" {
  filename = "${path.module}/applied-policies.json"
  content = jsonencode({
    timestamp       = timestamp()
    organization_id = var.organization_id
    environment     = var.environment
    enforced_policies = concat(
      [for k, v in local.base_policies : {
        name       = k
        constraint = v.constraint
        enforced   = v.enforce
        type       = "boolean"
      } if v.enforce],
      [for k, v in local.list_constraint_policies : {
        name       = k
        constraint = v.constraint
        enforced   = v.enforce
        type       = "list_deny"
        values     = v.deny_list
      } if v.enforce],
      [for k, v in local.location_policies : {
        name       = k
        constraint = v.constraint
        enforced   = v.enforce
        type       = "list_allow"
        values     = v.allow_list
      } if v.enforce]
    )
    configuration_metadata = {
      terraform_version = ">=1.0"
      provider_version  = ">=4.0"
      applied_by        = "universal-project-platform"
      agent             = "agent-5-isolation-layer"
    }
  })
}

# Validation rules
check "policy_validation" {
  assert {
    condition     = var.organization_id != ""
    error_message = "Organization ID must be provided"
  }

  assert {
    condition     = length(var.allowed_regions) > 0
    error_message = "At least one allowed region must be specified"
  }

  assert {
    condition     = contains(["dev", "test", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, staging, prod"
  }
}
