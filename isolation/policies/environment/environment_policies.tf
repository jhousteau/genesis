# Environment-Specific Security Policies
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Applies environment-specific security controls and compliance requirements

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0"
    }
  }
}

# Variables for environment configuration
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, test, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "test", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, staging, prod."
  }
}

variable "organization_id" {
  description = "GCP Organization ID (optional, for org-level policies)"
  type        = string
  default     = ""
}

variable "compliance_framework" {
  description = "Compliance framework to apply (SOC2, HIPAA, PCI-DSS, ISO27001, GDPR)"
  type        = string
  default     = "SOC2"
}

variable "data_classification" {
  description = "Data classification level (public, internal, confidential, restricted)"
  type        = string
  default     = "internal"
}

variable "region" {
  description = "Primary region for resources"
  type        = string
  default     = "us-central1"
}

variable "allowed_regions" {
  description = "List of allowed regions for this environment"
  type        = list(string)
  default     = ["us-central1", "us-east1"]
}

variable "enable_audit_logging" {
  description = "Enable comprehensive audit logging"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Log retention period in days"
  type        = number
  default     = 365
}

variable "enable_monitoring" {
  description = "Enable comprehensive monitoring and alerting"
  type        = bool
  default     = true
}

variable "cost_center" {
  description = "Cost center for billing allocation"
  type        = string
  default     = ""
}

variable "owner_team" {
  description = "Team responsible for this environment"
  type        = string
  default     = ""
}

# Local values for environment-specific configurations
locals {
  # Environment-specific settings
  environment_config = {
    dev = {
      require_approval          = false
      allow_public_ips          = true
      allow_sa_keys             = true
      encryption_level          = "standard"
      monitoring_level          = "basic"
      log_level                 = "INFO"
      cost_threshold_multiplier = 0.5
      backup_frequency          = "weekly"
      patch_schedule            = "flexible"
    }
    test = {
      require_approval          = false
      allow_public_ips          = true
      allow_sa_keys             = true
      encryption_level          = "standard"
      monitoring_level          = "enhanced"
      log_level                 = "INFO"
      cost_threshold_multiplier = 0.7
      backup_frequency          = "weekly"
      patch_schedule            = "weekly"
    }
    staging = {
      require_approval          = true
      allow_public_ips          = false
      allow_sa_keys             = false
      encryption_level          = "enhanced"
      monitoring_level          = "enhanced"
      log_level                 = "WARN"
      cost_threshold_multiplier = 0.8
      backup_frequency          = "daily"
      patch_schedule            = "weekly"
    }
    prod = {
      require_approval          = true
      allow_public_ips          = false
      allow_sa_keys             = false
      encryption_level          = "maximum"
      monitoring_level          = "maximum"
      log_level                 = "ERROR"
      cost_threshold_multiplier = 1.0
      backup_frequency          = "daily"
      patch_schedule            = "monthly"
    }
  }

  # Compliance framework requirements
  compliance_requirements = {
    SOC2 = {
      encryption_required        = true
      audit_logging_required     = true
      access_controls_required   = true
      backup_required            = true
      monitoring_required        = true
      incident_response_required = true
    }
    HIPAA = {
      encryption_required        = true
      audit_logging_required     = true
      access_controls_required   = true
      backup_required            = true
      monitoring_required        = true
      incident_response_required = true
      data_residency_required    = true
      anonymization_required     = true
    }
    "PCI-DSS" = {
      encryption_required             = true
      audit_logging_required          = true
      access_controls_required        = true
      backup_required                 = true
      monitoring_required             = true
      incident_response_required      = true
      network_segmentation_required   = true
      vulnerability_scanning_required = true
    }
    ISO27001 = {
      encryption_required          = true
      audit_logging_required       = true
      access_controls_required     = true
      backup_required              = true
      monitoring_required          = true
      incident_response_required   = true
      risk_assessment_required     = true
      business_continuity_required = true
    }
    GDPR = {
      encryption_required        = true
      audit_logging_required     = true
      access_controls_required   = true
      backup_required            = true
      monitoring_required        = true
      incident_response_required = true
      data_residency_required    = true
      right_to_erasure_required  = true
      privacy_by_design_required = true
    }
  }

  # Current environment configuration
  current_env_config = local.environment_config[var.environment]
  current_compliance = local.compliance_requirements[var.compliance_framework]

  # Computed values
  effective_log_retention = var.environment == "prod" ? max(var.log_retention_days, 2555) : var.log_retention_days # 7 years for prod

  # Required labels for all resources
  required_labels = {
    environment         = var.environment
    compliance          = lower(var.compliance_framework)
    data_classification = var.data_classification
    managed_by          = "universal-project-platform"
    cost_center         = var.cost_center != "" ? var.cost_center : "unknown"
    owner_team          = var.owner_team != "" ? var.owner_team : "unknown"
    terraform           = "true"
    isolation_layer     = "agent-5"
  }
}

# Project-level policies
resource "google_project_organization_policy" "compute_disable_serial_port" {
  count      = var.environment == "prod" ? 1 : 0
  project    = var.project_id
  constraint = "constraints/compute.disableSerialPortAccess"

  boolean_policy {
    enforced = true
  }
}

resource "google_project_organization_policy" "compute_require_shielded_vm" {
  count      = var.environment == "prod" || var.environment == "staging" ? 1 : 0
  project    = var.project_id
  constraint = "constraints/compute.requireShieldedVm"

  boolean_policy {
    enforced = true
  }
}

resource "google_project_organization_policy" "compute_require_os_login" {
  project    = var.project_id
  constraint = "constraints/compute.requireOsLogin"

  boolean_policy {
    enforced = var.environment == "prod" || var.environment == "staging"
  }
}

resource "google_project_organization_policy" "iam_disable_service_account_key_creation" {
  project    = var.project_id
  constraint = "constraints/iam.disableServiceAccountKeyCreation"

  boolean_policy {
    enforced = !local.current_env_config.allow_sa_keys
  }
}

resource "google_project_organization_policy" "compute_vm_external_ip_access" {
  count      = local.current_env_config.allow_public_ips ? 0 : 1
  project    = var.project_id
  constraint = "constraints/compute.vmExternalIpAccess"

  list_policy {
    deny {
      all = true
    }
  }
}

resource "google_project_organization_policy" "storage_uniform_bucket_level_access" {
  project    = var.project_id
  constraint = "constraints/storage.uniformBucketLevelAccess"

  boolean_policy {
    enforced = true
  }
}

resource "google_project_organization_policy" "storage_public_access_prevention" {
  project    = var.project_id
  constraint = "constraints/storage.publicAccessPrevention"

  boolean_policy {
    enforced = var.environment == "prod" || var.environment == "staging"
  }
}

# Resource location restrictions
resource "google_project_organization_policy" "resource_locations" {
  project    = var.project_id
  constraint = "constraints/gcp.resourceLocations"

  list_policy {
    allow {
      values = var.allowed_regions
    }
  }
}

# SQL policies for data protection
resource "google_project_organization_policy" "sql_restrict_authorized_networks" {
  count      = local.current_compliance.encryption_required ? 1 : 0
  project    = var.project_id
  constraint = "constraints/sql.restrictAuthorizedNetworks"

  boolean_policy {
    enforced = true
  }
}

resource "google_project_organization_policy" "sql_require_ssl" {
  count      = local.current_compliance.encryption_required ? 1 : 0
  project    = var.project_id
  constraint = "constraints/sql.requireSsl"

  boolean_policy {
    enforced = true
  }
}

# Enable audit logging
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
}

# Project labels
resource "google_project" "project_labels" {
  project_id = var.project_id
  name       = var.project_id

  labels = local.required_labels

  # Prevent accidental deletion of the project
  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      billing_account,
      folder_id,
      org_id,
      project_id,
      name
    ]
  }
}

# Log sink for security events
resource "google_logging_project_sink" "security_sink" {
  count       = var.enable_monitoring ? 1 : 0
  name        = "${var.environment}-security-events"
  project     = var.project_id
  destination = "storage.googleapis.com/${google_storage_bucket.security_logs[0].name}"

  filter = <<-EOT
    protoPayload.serviceName="cloudresourcemanager.googleapis.com"
    OR protoPayload.serviceName="iam.googleapis.com"
    OR protoPayload.serviceName="cloudkms.googleapis.com"
    OR protoPayload.serviceName="secretmanager.googleapis.com"
    OR (protoPayload.serviceName="compute.googleapis.com" AND protoPayload.methodName=~"^google.compute.*\.(insert|delete|update)")
    OR severity>=ERROR
  EOT

  unique_writer_identity = true
}

# Security logs bucket
resource "google_storage_bucket" "security_logs" {
  count         = var.enable_monitoring ? 1 : 0
  name          = "${var.project_id}-${var.environment}-security-logs"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  retention_policy {
    retention_period = local.effective_log_retention * 24 * 60 * 60 # Convert days to seconds
  }

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  labels = local.required_labels
}

# Grant log writer permission to the sink
resource "google_storage_bucket_iam_member" "security_logs_writer" {
  count  = var.enable_monitoring ? 1 : 0
  bucket = google_storage_bucket.security_logs[0].name
  role   = "roles/storage.objectCreator"
  member = google_logging_project_sink.security_sink[0].writer_identity
}

# Enable Security Command Center (if organization is provided)
resource "google_security_center_notification_config" "security_notifications" {
  count        = var.organization_id != "" && var.enable_monitoring ? 1 : 0
  config_id    = "${var.environment}-security-notifications"
  organization = var.organization_id
  description  = "Security notifications for ${var.environment} environment"
  pubsub_topic = google_pubsub_topic.security_notifications[0].id

  streaming_config {
    filter = "state=\"ACTIVE\""
  }
}

# Pub/Sub topic for security notifications
resource "google_pubsub_topic" "security_notifications" {
  count = var.organization_id != "" && var.enable_monitoring ? 1 : 0
  name  = "${var.environment}-security-notifications"

  labels = local.required_labels
}

# Monitoring policy for security events
resource "google_monitoring_alert_policy" "security_events" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${var.environment} Security Events"
  combiner     = "OR"

  conditions {
    display_name = "Security-related log entries"

    condition_threshold {
      filter          = "resource.type=\"gce_project\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.enable_monitoring ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "1800s"
  }
}

# Email notification channel
resource "google_monitoring_notification_channel" "email" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${var.environment} Security Alerts"
  type         = "email"

  labels = {
    email_address = "security-${var.environment}@example.com"
  }
}

# IAM recommendations (if organization is provided)
resource "google_recommender_iam_policy_insight" "iam_insights" {
  count       = var.organization_id != "" ? 1 : 0
  parent      = "projects/${var.project_id}"
  recommender = "google.iam.policy.Recommender"

  depends_on = [google_project.project_labels]
}

# Cloud Asset Inventory (if organization is provided)
resource "google_cloud_asset_project_feed" "asset_feed" {
  count        = var.organization_id != "" && var.enable_monitoring ? 1 : 0
  project      = var.project_id
  feed_id      = "${var.environment}-asset-feed"
  content_type = "RESOURCE"

  asset_types = [
    "compute.googleapis.com/Instance",
    "storage.googleapis.com/Bucket",
    "iam.googleapis.com/ServiceAccount",
    "cloudkms.googleapis.com/CryptoKey"
  ]

  feed_output_config {
    pubsub_destination {
      topic = google_pubsub_topic.asset_changes[0].id
    }
  }
}

# Pub/Sub topic for asset changes
resource "google_pubsub_topic" "asset_changes" {
  count = var.organization_id != "" && var.enable_monitoring ? 1 : 0
  name  = "${var.environment}-asset-changes"

  labels = local.required_labels
}

# Environment-specific service enablement
resource "google_project_service" "required_apis" {
  for_each = toset([
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudasset.googleapis.com",
    "securitycenter.googleapis.com",
    "cloudkms.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "storage.googleapis.com"
  ])

  project = var.project_id
  service = each.key

  disable_on_destroy = false
}

# Outputs
output "environment_config" {
  description = "Applied environment configuration"
  value = {
    environment             = var.environment
    compliance_framework    = var.compliance_framework
    data_classification     = var.data_classification
    current_config          = local.current_env_config
    compliance_requirements = local.current_compliance
    required_labels         = local.required_labels
  }
}

output "security_resources" {
  description = "Created security resources"
  value = {
    security_logs_bucket = var.enable_monitoring ? google_storage_bucket.security_logs[0].name : null
    security_sink        = var.enable_monitoring ? google_logging_project_sink.security_sink[0].name : null
    monitoring_policy    = var.enable_monitoring ? google_monitoring_alert_policy.security_events[0].name : null
    notification_channel = var.enable_monitoring ? google_monitoring_notification_channel.email[0].name : null
  }
}

output "compliance_status" {
  description = "Compliance status summary"
  value = {
    framework             = var.compliance_framework
    encryption_enabled    = local.current_compliance.encryption_required
    audit_logging_enabled = var.enable_audit_logging
    monitoring_enabled    = var.enable_monitoring
    log_retention_days    = local.effective_log_retention
    environment_hardening = var.environment == "prod" ? "maximum" : local.current_env_config.encryption_level
  }
}

# Validation checks
check "environment_validation" {
  assert {
    condition     = contains(["dev", "test", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, staging, prod"
  }

  assert {
    condition     = contains(["SOC2", "HIPAA", "PCI-DSS", "ISO27001", "GDPR"], var.compliance_framework)
    error_message = "Compliance framework must be one of: SOC2, HIPAA, PCI-DSS, ISO27001, GDPR"
  }

  assert {
    condition     = length(var.allowed_regions) > 0
    error_message = "At least one allowed region must be specified"
  }

  assert {
    condition     = var.log_retention_days >= 30
    error_message = "Log retention must be at least 30 days"
  }
}

# Compliance validation
check "compliance_validation" {
  assert {
    condition     = var.environment == "prod" ? var.enable_audit_logging == true : true
    error_message = "Audit logging must be enabled for production environments"
  }

  assert {
    condition     = var.environment == "prod" ? var.enable_monitoring == true : true
    error_message = "Monitoring must be enabled for production environments"
  }

  assert {
    condition     = var.environment == "prod" ? var.log_retention_days >= 2555 : true
    error_message = "Production environments must retain logs for at least 7 years (2555 days)"
  }
}
