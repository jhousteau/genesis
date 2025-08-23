# Google Cloud Organization Policies
# Comprehensive policy enforcement for GCP resources

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "folder_id" {
  description = "GCP Folder ID (optional, if policies apply to folder instead of org)"
  type        = string
  default     = null
}

variable "project_id" {
  description = "GCP Project ID (optional, if policies apply to project instead of org/folder)"
  type        = string
  default     = null
}

variable "enforcement_level" {
  description = "Policy enforcement level: ENFORCED, DRYRUN"
  type        = string
  default     = "ENFORCED"

  validation {
    condition     = contains(["ENFORCED", "DRYRUN"], var.enforcement_level)
    error_message = "Enforcement level must be either ENFORCED or DRYRUN."
  }
}

# Local values for policy parent
locals {
  policy_parent = var.project_id != null ? "projects/${var.project_id}" : (
    var.folder_id != null ? "folders/${var.folder_id}" : "organizations/${var.organization_id}"
  )
}

# Compute policies
resource "google_org_policy_policy" "disable_sa_key_creation" {
  name   = "${local.policy_parent}/policies/iam.disableServiceAccountKeyCreation"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "disable_sa_key_upload" {
  name   = "${local.policy_parent}/policies/iam.disableServiceAccountKeyUpload"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "restrict_vm_external_access" {
  name   = "${local.policy_parent}/policies/compute.vmExternalIpAccess"
  parent = local.policy_parent

  spec {
    rules {
      deny_all = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "require_shielded_vm" {
  name   = "${local.policy_parent}/policies/compute.requireShieldedVm"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "disable_serial_port_access" {
  name   = "${local.policy_parent}/policies/compute.disableSerialPortAccess"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

# Storage policies
resource "google_org_policy_policy" "enforce_uniform_bucket_access" {
  name   = "${local.policy_parent}/policies/storage.uniformBucketLevelAccess"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "restrict_public_ip_cloudsql" {
  name   = "${local.policy_parent}/policies/sql.restrictPublicIp"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

# Network policies
resource "google_org_policy_policy" "skip_default_network_creation" {
  name   = "${local.policy_parent}/policies/compute.skipDefaultNetworkCreation"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "restrict_vpc_peering" {
  name   = "${local.policy_parent}/policies/compute.restrictVpcPeering"
  parent = local.policy_parent

  spec {
    rules {
      allow_all = var.enforcement_level == "ENFORCED" ? "FALSE" : "TRUE"
      values {
        allowed_values = [
          "projects/${var.project_id}/global/networks/allowed-network"
        ]
      }
    }
  }
}

# Resource location restrictions
resource "google_org_policy_policy" "resource_locations" {
  name   = "${local.policy_parent}/policies/gcp.resourceLocations"
  parent = local.policy_parent

  spec {
    rules {
      values {
        allowed_values = [
          "in:us-locations",
          "in:eu-locations"
        ]
      }
    }
  }
}

# Naming convention enforcement
resource "google_org_policy_policy" "naming_convention" {
  name   = "${local.policy_parent}/policies/gcp.resourceNaming"
  parent = local.policy_parent

  spec {
    rules {
      condition {
        expression = "resource.name.matches('^[a-z][a-z0-9-]*[a-z0-9]$')"
      }
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

# Required labels
resource "google_org_policy_policy" "required_labels" {
  name   = "${local.policy_parent}/policies/gcp.requiredLabels"
  parent = local.policy_parent

  spec {
    rules {
      values {
        required_values = [
          "environment",
          "project",
          "cost-center",
          "owner"
        ]
      }
    }
  }
}

# BigQuery policies
resource "google_org_policy_policy" "bigquery_public_access" {
  name   = "${local.policy_parent}/policies/bigquery.disablePublicAccess"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

# Cloud Functions policies
resource "google_org_policy_policy" "cloud_functions_ingress" {
  name   = "${local.policy_parent}/policies/cloudfunctions.allowedIngressSettings"
  parent = local.policy_parent

  spec {
    rules {
      values {
        allowed_values = [
          "ALLOW_INTERNAL_ONLY",
          "ALLOW_INTERNAL_AND_GCLB"
        ]
      }
    }
  }
}

# Kubernetes Engine policies
resource "google_org_policy_policy" "gke_legacy_abac" {
  name   = "${local.policy_parent}/policies/container.disableLegacyAbac"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "gke_basic_auth" {
  name   = "${local.policy_parent}/policies/container.disableBasicAuth"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

# App Engine policies
resource "google_org_policy_policy" "appengine_enforce_https" {
  name   = "${local.policy_parent}/policies/appengine.enforceHttps"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

# Advanced Security Policies
resource "google_org_policy_policy" "restrict_client_certificate_auth" {
  name   = "${local.policy_parent}/policies/sql.restrictClientCertificateAuth"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "disable_default_vpc" {
  name   = "${local.policy_parent}/policies/compute.disableDefaultVpc"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "require_os_login" {
  name   = "${local.policy_parent}/policies/compute.requireOsLogin"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "restrict_vm_ip_forwarding" {
  name   = "${local.policy_parent}/policies/compute.vmCanIpForward"
  parent = local.policy_parent

  spec {
    rules {
      deny_all = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "enforce_cloud_sql_ssl" {
  name   = "${local.policy_parent}/policies/sql.restrictSSL"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "restrict_load_balancer_creation" {
  name   = "${local.policy_parent}/policies/compute.restrictLoadBalancerCreationForTypes"
  parent = local.policy_parent

  spec {
    rules {
      values {
        allowed_values = [
          "INTERNAL",
          "INTERNAL_MANAGED"
        ]
      }
    }
  }
}

resource "google_org_policy_policy" "restrict_shared_vpc_subnetworks" {
  name   = "${local.policy_parent}/policies/compute.restrictSharedVpcSubnetworks"
  parent = local.policy_parent

  spec {
    rules {
      values {
        allowed_values = [
          "projects/${var.project_id}/regions/us-central1/subnetworks/allowed-subnet"
        ]
      }
    }
  }
}

# Data Protection Policies
resource "google_org_policy_policy" "restrict_dataset_location" {
  name   = "${local.policy_parent}/policies/bigquery.datasetLocationRestriction"
  parent = local.policy_parent

  spec {
    rules {
      values {
        allowed_values = [
          "us-central1",
          "us-east1"
        ]
      }
    }
  }
}

resource "google_org_policy_policy" "require_cmek_encryption" {
  name   = "${local.policy_parent}/policies/gcp.requireCmekEncryption"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

# Monitoring and Logging Policies
resource "google_org_policy_policy" "enforce_audit_logs" {
  name   = "${local.policy_parent}/policies/logging.auditLogRetention"
  parent = local.policy_parent

  spec {
    rules {
      values {
        required_values = [
          "DATA_READ",
          "DATA_WRITE",
          "ADMIN_READ"
        ]
      }
    }
  }
}

resource "google_org_policy_policy" "restrict_log_sink_destinations" {
  name   = "${local.policy_parent}/policies/logging.restrictLogSinkDestinations"
  parent = local.policy_parent

  spec {
    rules {
      values {
        allowed_values = [
          "projects/${var.project_id}/datasets/audit_logs",
          "projects/${var.project_id}/topics/audit_logs"
        ]
      }
    }
  }
}

# IAM and Security Policies
resource "google_org_policy_policy" "restrict_iam_primitive_roles" {
  name   = "${local.policy_parent}/policies/iam.restrictPrimitiveRoles"
  parent = local.policy_parent

  spec {
    rules {
      values {
        denied_values = [
          "roles/owner",
          "roles/editor",
          "roles/viewer"
        ]
      }
    }
  }
}

resource "google_org_policy_policy" "require_mfa_for_privileged_access" {
  name   = "${local.policy_parent}/policies/iam.requireMfaForPrivilegedAccess"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "restrict_cross_project_service_account_usage" {
  name   = "${local.policy_parent}/policies/iam.restrictCrossProjectServiceAccountUsage"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

# Container and Serverless Policies
resource "google_org_policy_policy" "gke_require_workload_identity" {
  name   = "${local.policy_parent}/policies/container.requireWorkloadIdentity"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "gke_disable_client_certificate_auth" {
  name   = "${local.policy_parent}/policies/container.disableClientCertificateAuth"
  parent = local.policy_parent

  spec {
    rules {
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

resource "google_org_policy_policy" "gke_restrict_node_metadata" {
  name   = "${local.policy_parent}/policies/container.restrictNodeMetadataAccess"
  parent = local.policy_parent

  spec {
    rules {
      values {
        allowed_values = [
          "GKE_METADATA_SERVER"
        ]
      }
    }
  }
}

resource "google_org_policy_policy" "cloud_run_restrict_ingress" {
  name   = "${local.policy_parent}/policies/run.allowedIngressSettings"
  parent = local.policy_parent

  spec {
    rules {
      values {
        allowed_values = [
          "internal",
          "internal-and-cloud-load-balancing"
        ]
      }
    }
  }
}

# Compliance and Governance Policies
resource "google_org_policy_policy" "enforce_data_residency" {
  name   = "${local.policy_parent}/policies/gcp.dataResidency"
  parent = local.policy_parent

  spec {
    rules {
      values {
        allowed_values = [
          "in:us-locations"
        ]
      }
    }
  }
}

resource "google_org_policy_policy" "require_business_justification" {
  name   = "${local.policy_parent}/policies/gcp.requireBusinessJustification"
  parent = local.policy_parent

  spec {
    rules {
      condition {
        expression = "resource.cost > 1000"
      }
      enforce = var.enforcement_level == "ENFORCED" ? "TRUE" : "FALSE"
    }
  }
}

# Outputs
output "applied_policies" {
  description = "List of applied organization policies"
  value = [
    # Basic Security Policies
    google_org_policy_policy.disable_sa_key_creation.name,
    google_org_policy_policy.disable_sa_key_upload.name,
    google_org_policy_policy.restrict_vm_external_access.name,
    google_org_policy_policy.require_shielded_vm.name,
    google_org_policy_policy.disable_serial_port_access.name,
    google_org_policy_policy.enforce_uniform_bucket_access.name,
    google_org_policy_policy.restrict_public_ip_cloudsql.name,
    google_org_policy_policy.skip_default_network_creation.name,
    google_org_policy_policy.restrict_vpc_peering.name,
    google_org_policy_policy.resource_locations.name,
    google_org_policy_policy.naming_convention.name,
    google_org_policy_policy.required_labels.name,
    google_org_policy_policy.bigquery_public_access.name,
    google_org_policy_policy.cloud_functions_ingress.name,
    google_org_policy_policy.gke_legacy_abac.name,
    google_org_policy_policy.gke_basic_auth.name,
    google_org_policy_policy.appengine_enforce_https.name,

    # Advanced Security Policies
    google_org_policy_policy.restrict_client_certificate_auth.name,
    google_org_policy_policy.disable_default_vpc.name,
    google_org_policy_policy.require_os_login.name,
    google_org_policy_policy.restrict_vm_ip_forwarding.name,
    google_org_policy_policy.enforce_cloud_sql_ssl.name,
    google_org_policy_policy.restrict_load_balancer_creation.name,
    google_org_policy_policy.restrict_shared_vpc_subnetworks.name,

    # Data Protection Policies
    google_org_policy_policy.restrict_dataset_location.name,
    google_org_policy_policy.require_cmek_encryption.name,

    # Monitoring and Logging Policies
    google_org_policy_policy.enforce_audit_logs.name,
    google_org_policy_policy.restrict_log_sink_destinations.name,

    # IAM and Security Policies
    google_org_policy_policy.restrict_iam_primitive_roles.name,
    google_org_policy_policy.require_mfa_for_privileged_access.name,
    google_org_policy_policy.restrict_cross_project_service_account_usage.name,

    # Container and Serverless Policies
    google_org_policy_policy.gke_require_workload_identity.name,
    google_org_policy_policy.gke_disable_client_certificate_auth.name,
    google_org_policy_policy.gke_restrict_node_metadata.name,
    google_org_policy_policy.cloud_run_restrict_ingress.name,

    # Compliance and Governance Policies
    google_org_policy_policy.enforce_data_residency.name,
    google_org_policy_policy.require_business_justification.name
  ]
}

output "policy_parent" {
  description = "The parent resource where policies are applied"
  value       = local.policy_parent
}
