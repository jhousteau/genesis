# Project-level Security Policies
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Enforces security baselines at the project level

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "environment" {
  description = "Environment (dev, test, staging, prod)"
  type        = string
}

variable "enable_audit_logging" {
  description = "Enable audit logging for the project"
  type        = bool
  default     = true
}

variable "enable_monitoring" {
  description = "Enable monitoring APIs and default monitoring"
  type        = bool
  default     = true
}

variable "enable_security_center" {
  description = "Enable Security Command Center"
  type        = bool
  default     = true
}

variable "enable_binary_authorization" {
  description = "Enable Binary Authorization for container images"
  type        = bool
  default     = false # Enable for production
}

variable "allowed_external_ips" {
  description = "List of allowed external IP addresses"
  type        = list(string)
  default     = []
}

variable "required_labels" {
  description = "Labels that must be present on all resources"
  type        = map(string)
  default = {
    environment = ""
    team        = ""
    project     = ""
  }
}

variable "enable_private_google_access" {
  description = "Enable Private Google Access for subnets"
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "retention_days" {
  description = "Log retention period in days"
  type        = number
  default     = 90

  validation {
    condition     = var.retention_days >= 30 && var.retention_days <= 3653
    error_message = "Retention days must be between 30 and 3653."
  }
}

variable "alert_notification_channels" {
  description = "Notification channels for security alerts"
  type        = list(string)
  default     = []
}

# Local values
locals {
  is_production = var.environment == "prod"

  # Required APIs for security features
  required_apis = [
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
    "cloudsecurity.googleapis.com",
    "securitycenter.googleapis.com"
  ]

  # Security-focused APIs
  security_apis = [
    "binaryauthorization.googleapis.com",
    "cloudkms.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudasset.googleapis.com",
    "policytroubleshooter.googleapis.com"
  ]

  # Production-specific requirements
  production_policies = {
    "compute.requireShieldedVm" = {
      constraint = "constraints/compute.requireShieldedVm"
      enforce    = local.is_production
    }
    "compute.disableSerialPortAccess" = {
      constraint = "constraints/compute.disableSerialPortAccess"
      enforce    = local.is_production
    }
    "iam.disableServiceAccountKeyCreation" = {
      constraint = "constraints/iam.disableServiceAccountKeyCreation"
      enforce    = local.is_production
    }
    "storage.publicAccessPrevention" = {
      constraint = "constraints/storage.publicAccessPrevention"
      enforce    = true # Always enforce
    }
  }
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset(local.required_apis)

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

# Enable security APIs
resource "google_project_service" "security_apis" {
  for_each = var.enable_security_center ? toset(local.security_apis) : toset([])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

# Project-level organization policies (if permissions allow)
resource "google_project_organization_policy" "project_policies" {
  for_each = {
    for k, v in local.production_policies : k => v if v.enforce
  }

  project    = var.project_id
  constraint = each.value.constraint

  boolean_policy {
    enforced = true
  }

  depends_on = [google_project_service.required_apis]
}

# IAM Audit Configuration
resource "google_project_iam_audit_config" "audit_config" {
  count   = var.enable_audit_logging ? 1 : 0
  project = var.project_id
  service = "allServices"

  audit_log_config {
    log_type = "ADMIN_READ"
  }

  audit_log_config {
    log_type = "DATA_READ"
  }

  audit_log_config {
    log_type = "DATA_WRITE"
  }

  depends_on = [google_project_service.required_apis]
}

# Custom IAM role for security monitoring
resource "google_project_iam_custom_role" "security_monitor" {
  role_id     = "securityMonitor"
  title       = "Security Monitor"
  description = "Custom role for security monitoring and auditing"
  project     = var.project_id

  permissions = [
    "cloudkms.keyRings.list",
    "cloudkms.cryptoKeys.list",
    "compute.instances.list",
    "compute.firewalls.list",
    "iam.serviceAccounts.list",
    "iam.roles.list",
    "logging.logs.list",
    "monitoring.alertPolicies.list",
    "securitycenter.findings.list",
    "storage.buckets.list"
  ]

  depends_on = [google_project_service.required_apis]
}

# Log sink for security events
resource "google_logging_project_sink" "security_sink" {
  count = var.enable_audit_logging ? 1 : 0

  name        = "security-events-sink"
  project     = var.project_id
  destination = "storage.googleapis.com/${google_storage_bucket.security_logs[0].name}"

  filter = <<-EOT
    (protoPayload.methodName:"iam.googleapis.com" OR
     protoPayload.methodName:"cloudkms.googleapis.com" OR
     protoPayload.methodName:"secretmanager.googleapis.com" OR
     resource.type="gce_firewall_rule" OR
     resource.type="gce_instance" AND operation.first=true) AND
    severity>=ERROR
  EOT

  unique_writer_identity = true

  depends_on = [google_project_service.required_apis]
}

# Security logs storage bucket
resource "google_storage_bucket" "security_logs" {
  count = var.enable_audit_logging ? 1 : 0

  name     = "${var.project_id}-security-logs"
  location = "US"
  project  = var.project_id

  # Security configurations
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = var.retention_days
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age        = 30
      with_state = "NONCURRENT_VERSION"
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.required_apis]
}

# IAM binding for log sink
resource "google_storage_bucket_iam_binding" "security_logs_writer" {
  count  = var.enable_audit_logging ? 1 : 0
  bucket = google_storage_bucket.security_logs[0].name
  role   = "roles/storage.objectCreator"

  members = [
    google_logging_project_sink.security_sink[0].writer_identity
  ]
}

# Security monitoring alerts
resource "google_monitoring_alert_policy" "unauthorized_iam_changes" {
  count = var.enable_monitoring && length(var.alert_notification_channels) > 0 ? 1 : 0

  display_name = "Unauthorized IAM Changes"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "IAM policy changes by non-service accounts"

    condition_threshold {
      filter          = "resource.type=\"project\" AND protoPayload.methodName=\"SetIamPolicy\" AND NOT protoPayload.authenticationInfo.principalEmail:gserviceaccount.com"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0
      duration        = "60s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.alert_notification_channels

  alert_strategy {
    notification_rate_limit {
      period = "300s"
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Firewall rule changes alert
resource "google_monitoring_alert_policy" "firewall_changes" {
  count = var.enable_monitoring && length(var.alert_notification_channels) > 0 ? 1 : 0

  display_name = "Firewall Rule Changes"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Firewall rules created or modified"

    condition_threshold {
      filter          = "resource.type=\"gce_firewall_rule\" AND (protoPayload.methodName=\"insert\" OR protoPayload.methodName=\"patch\")"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0
      duration        = "60s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.alert_notification_channels

  depends_on = [google_project_service.required_apis]
}

# Service account key creation alert
resource "google_monitoring_alert_policy" "service_account_keys" {
  count = var.enable_monitoring && length(var.alert_notification_channels) > 0 ? 1 : 0

  display_name = "Service Account Key Creation"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Service account keys created"

    condition_threshold {
      filter          = "resource.type=\"service_account\" AND protoPayload.methodName=\"google.iam.admin.v1.IAM.CreateServiceAccountKey\""
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0
      duration        = "60s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.alert_notification_channels

  depends_on = [google_project_service.required_apis]
}

# Binary Authorization policy (for production)
resource "google_binary_authorization_policy" "policy" {
  count   = var.enable_binary_authorization ? 1 : 0
  project = var.project_id

  # Default admission rule - require attestation
  default_admission_rule {
    evaluation_mode  = "REQUIRE_ATTESTATION"
    enforcement_mode = "ENFORCED_BLOCK_AND_AUDIT_LOG"

    require_attestations_by = [
      google_binary_authorization_attestor.build_attestor[0].name
    ]
  }

  # Cluster-specific admission rules can be added here

  depends_on = [google_project_service.security_apis]
}

# Binary Authorization attestor
resource "google_binary_authorization_attestor" "build_attestor" {
  count   = var.enable_binary_authorization ? 1 : 0
  name    = "build-attestor"
  project = var.project_id

  attestation_authority_note {
    note_reference = google_container_analysis_note.build_note[0].name

    public_keys {
      ascii_armored_pgp_public_key = file("${path.module}/attestor-key.pub")
    }
  }

  depends_on = [google_project_service.security_apis]
}

# Container Analysis note for Binary Authorization
resource "google_container_analysis_note" "build_note" {
  count   = var.enable_binary_authorization ? 1 : 0
  name    = "build-note"
  project = var.project_id

  attestation_authority {
    hint {
      human_readable_name = "Build Attestor"
    }
  }

  depends_on = [google_project_service.security_apis]
}

# Security Command Center notification config
resource "google_scc_notification_config" "security_findings" {
  count        = var.enable_security_center && length(var.alert_notification_channels) > 0 ? 1 : 0
  config_id    = "security-findings-config"
  organization = data.google_project.current.number
  pubsub_topic = google_pubsub_topic.security_notifications[0].id
  streaming_config {
    filter = "state=\"ACTIVE\""
  }
}

# Pub/Sub topic for security notifications
resource "google_pubsub_topic" "security_notifications" {
  count   = var.enable_security_center ? 1 : 0
  name    = "security-notifications"
  project = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Data source for current project
data "google_project" "current" {
  project_id = var.project_id
}

# KMS key for encryption at rest
resource "google_kms_key_ring" "security" {
  name     = "security-keyring"
  location = "global"
  project  = var.project_id

  depends_on = [google_project_service.security_apis]
}

resource "google_kms_crypto_key" "security" {
  name     = "security-key"
  key_ring = google_kms_key_ring.security.id
  purpose  = "ENCRYPT_DECRYPT"

  version_template {
    algorithm = "GOOGLE_SYMMETRIC_ENCRYPTION"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# IAM bindings for security key
resource "google_kms_crypto_key_iam_binding" "security_key_users" {
  crypto_key_id = google_kms_crypto_key.security.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"

  members = [
    "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
  ]
}

# Outputs
output "security_configuration" {
  description = "Security configuration summary"
  value = {
    project_id              = var.project_id
    environment             = var.environment
    audit_logging_enabled   = var.enable_audit_logging
    monitoring_enabled      = var.enable_monitoring
    security_center_enabled = var.enable_security_center
    binary_authorization    = var.enable_binary_authorization
    kms_key_ring            = google_kms_key_ring.security.name
    security_logs_bucket    = var.enable_audit_logging ? google_storage_bucket.security_logs[0].name : null
    log_retention_days      = var.retention_days
    is_production           = local.is_production
  }
}

output "security_monitoring" {
  description = "Security monitoring resources"
  value = {
    alert_policies = [
      var.enable_monitoring && length(var.alert_notification_channels) > 0 ? google_monitoring_alert_policy.unauthorized_iam_changes[0].name : null,
      var.enable_monitoring && length(var.alert_notification_channels) > 0 ? google_monitoring_alert_policy.firewall_changes[0].name : null,
      var.enable_monitoring && length(var.alert_notification_channels) > 0 ? google_monitoring_alert_policy.service_account_keys[0].name : null
    ]
    custom_role  = google_project_iam_custom_role.security_monitor.role_id
    log_sink     = var.enable_audit_logging ? google_logging_project_sink.security_sink[0].name : null
    pubsub_topic = var.enable_security_center ? google_pubsub_topic.security_notifications[0].name : null
  }
}

output "compliance_status" {
  description = "Compliance and security status"
  value = {
    audit_logging          = var.enable_audit_logging
    encryption_at_rest     = true # KMS key created
    network_security       = var.enable_flow_logs
    access_logging         = var.enable_audit_logging
    incident_response      = length(var.alert_notification_channels) > 0
    vulnerability_scanning = var.enable_security_center
    binary_authorization   = var.enable_binary_authorization
    data_retention_policy  = "${var.retention_days} days"
  }
}
