# PCI-DSS Compliant Infrastructure
# Terraform implementation for PCI DSS compliance in GCP

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID for PCI workloads"
  type        = string
}

variable "region" {
  description = "Primary region for PCI resources"
  type        = string
  default     = "us-central1"
}

variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "billing_account" {
  description = "Billing account for PCI projects"
  type        = string
}

variable "pci_environment" {
  description = "PCI environment type"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.pci_environment)
    error_message = "PCI environment must be development, staging, or production."
  }
}

variable "merchant_level" {
  description = "PCI DSS merchant level (1-4)"
  type        = number
  default     = 1

  validation {
    condition     = var.merchant_level >= 1 && var.merchant_level <= 4
    error_message = "Merchant level must be between 1 and 4."
  }
}

# PCI Project with enhanced security
resource "google_project" "pci_project" {
  name            = "pci-${var.pci_environment}"
  project_id      = var.project_id
  billing_account = var.billing_account
  org_id          = var.organization_id

  labels = {
    environment    = var.pci_environment
    compliance     = "pci-dss"
    merchant_level = tostring(var.merchant_level)
    data_type      = "cardholder-data"
    criticality    = "critical"
  }
}

# Enable required APIs for PCI compliance
resource "google_project_service" "pci_apis" {
  project = google_project.pci_project.project_id

  for_each = toset([
    "cloudkms.googleapis.com",
    "cloudsql.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
    "dlp.googleapis.com",
    "dns.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "secretmanager.googleapis.com",
    "securitycenter.googleapis.com",
    "servicenetworking.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
    "vpcaccess.googleapis.com",
    "websecurityscanner.googleapis.com"
  ])

  service                    = each.value
  disable_dependent_services = true
}

# PCI-Compliant Network Architecture
resource "google_compute_network" "pci_vpc" {
  project                 = google_project.pci_project.project_id
  name                    = "pci-cde-vpc-${var.pci_environment}"
  auto_create_subnetworks = false
  description             = "PCI-DSS Cardholder Data Environment VPC"

  depends_on = [google_project_service.pci_apis]
}

# DMZ Subnet for external-facing components
resource "google_compute_subnetwork" "pci_dmz" {
  project       = google_project.pci_project.project_id
  name          = "pci-dmz-${var.region}"
  ip_cidr_range = "10.1.0.0/24"
  region        = var.region
  network       = google_compute_network.pci_vpc.name

  description = "DMZ subnet for PCI-DSS external components"

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_MIN"
    flow_sampling        = 1.0 # Full flow logging for PCI
    metadata             = "INCLUDE_ALL_METADATA"
  }

  secondary_ip_range {
    range_name    = "pci-dmz-pods"
    ip_cidr_range = "10.11.0.0/16"
  }

  secondary_ip_range {
    range_name    = "pci-dmz-services"
    ip_cidr_range = "10.12.0.0/16"
  }
}

# CDE (Cardholder Data Environment) Subnet
resource "google_compute_subnetwork" "pci_cde" {
  project       = google_project.pci_project.project_id
  name          = "pci-cde-${var.region}"
  ip_cidr_range = "10.2.0.0/24"
  region        = var.region
  network       = google_compute_network.pci_vpc.name

  description = "Cardholder Data Environment subnet"

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_1_MIN"
    flow_sampling        = 1.0 # Full flow logging
    metadata             = "INCLUDE_ALL_METADATA"
  }

  secondary_ip_range {
    range_name    = "pci-cde-pods"
    ip_cidr_range = "10.21.0.0/16"
  }

  secondary_ip_range {
    range_name    = "pci-cde-services"
    ip_cidr_range = "10.22.0.0/16"
  }
}

# Internal network for non-CDE components
resource "google_compute_subnetwork" "pci_internal" {
  project       = google_project.pci_project.project_id
  name          = "pci-internal-${var.region}"
  ip_cidr_range = "10.3.0.0/24"
  region        = var.region
  network       = google_compute_network.pci_vpc.name

  description = "Internal subnet for non-CDE components"

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# PCI-DSS Firewall Rules
resource "google_compute_firewall" "pci_default_deny_all" {
  project = google_project.pci_project.project_id
  name    = "pci-default-deny-all"
  network = google_compute_network.pci_vpc.name

  description = "Default deny all traffic for PCI compliance"
  direction   = "INGRESS"
  priority    = 65534

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_firewall" "pci_allow_internal_cde" {
  project = google_project.pci_project.project_id
  name    = "pci-allow-internal-cde"
  network = google_compute_network.pci_vpc.name

  description = "Allow internal communication within CDE"
  direction   = "INGRESS"
  priority    = 1000

  allow {
    protocol = "tcp"
    ports    = ["443", "5432", "3306"] # HTTPS, PostgreSQL, MySQL
  }

  source_ranges = [google_compute_subnetwork.pci_cde.ip_cidr_range]
  target_tags   = ["pci-cde"]

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_firewall" "pci_allow_dmz_to_cde" {
  project = google_project.pci_project.project_id
  name    = "pci-allow-dmz-to-cde"
  network = google_compute_network.pci_vpc.name

  description = "Allow DMZ to CDE communication on specific ports"
  direction   = "INGRESS"
  priority    = 1000

  allow {
    protocol = "tcp"
    ports    = ["443"] # Only HTTPS
  }

  source_ranges = [google_compute_subnetwork.pci_dmz.ip_cidr_range]
  target_tags   = ["pci-cde"]

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_firewall" "pci_allow_health_checks" {
  project = google_project.pci_project.project_id
  name    = "pci-allow-health-checks"
  network = google_compute_network.pci_vpc.name

  description = "Allow Google Cloud health checks"
  direction   = "INGRESS"
  priority    = 1000

  allow {
    protocol = "tcp"
  }

  source_ranges = [
    "130.211.0.0/22",
    "35.191.0.0/16"
  ]

  target_tags = ["pci-load-balanced"]

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

# HTTPS-only load balancer for PCI compliance
resource "google_compute_firewall" "pci_allow_https" {
  project = google_project.pci_project.project_id
  name    = "pci-allow-https"
  network = google_compute_network.pci_vpc.name

  description = "Allow HTTPS traffic from internet to DMZ"
  direction   = "INGRESS"
  priority    = 1000

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["pci-web-server"]

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

# PCI-DSS Key Management (CMEK)
resource "google_kms_key_ring" "pci_keyring" {
  project  = google_project.pci_project.project_id
  name     = "pci-keyring-${var.pci_environment}"
  location = var.region

  depends_on = [google_project_service.pci_apis]
}

resource "google_kms_crypto_key" "pci_database_key" {
  name     = "pci-database-key"
  key_ring = google_kms_key_ring.pci_keyring.id
  purpose  = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "HSM" # HSM required for PCI Level 1
  }

  lifecycle {
    prevent_destroy = true
  }

  # PCI DSS requires key rotation
  rotation_period = "7776000s" # 90 days
}

resource "google_kms_crypto_key" "pci_application_key" {
  name     = "pci-application-key"
  key_ring = google_kms_key_ring.pci_keyring.id
  purpose  = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "HSM"
  }

  lifecycle {
    prevent_destroy = true
  }

  rotation_period = "7776000s" # 90 days
}

resource "google_kms_crypto_key" "pci_storage_key" {
  name     = "pci-storage-key"
  key_ring = google_kms_key_ring.pci_keyring.id
  purpose  = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "HSM"
  }

  lifecycle {
    prevent_destroy = true
  }

  rotation_period = "7776000s" # 90 days
}

# PCI-Compliant Database (Cloud SQL)
resource "google_sql_database_instance" "pci_database" {
  project          = google_project.pci_project.project_id
  name             = "pci-db-${var.pci_environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier                        = "db-custom-8-32768" # High-performance for PCI
    availability_type           = "REGIONAL"
    deletion_protection_enabled = true

    # PCI DSS logging requirements
    database_flags {
      name  = "log_statement"
      value = "all"
    }

    database_flags {
      name  = "log_min_duration_statement"
      value = "0"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }

    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }

    # Enable auditing
    database_flags {
      name  = "shared_preload_libraries"
      value = "pgaudit"
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = false # No public IP for security
      private_network = google_compute_network.pci_vpc.id
      require_ssl     = true # Force SSL/TLS

      # Only allow CDE subnet access
      authorized_networks {
        name  = "pci-cde"
        value = google_compute_subnetwork.pci_cde.ip_cidr_range
      }
    }

    # CMEK encryption
    disk_encryption_configuration {
      kms_key_name = google_kms_crypto_key.pci_database_key.id
    }
  }

  depends_on = [
    google_project_service.pci_apis,
    google_service_networking_connection.pci_private_vpc_connection
  ]
}

# Private Service Networking for secure database access
resource "google_compute_global_address" "pci_private_ip_address" {
  project       = google_project.pci_project.project_id
  name          = "pci-private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.pci_vpc.id
}

resource "google_service_networking_connection" "pci_private_vpc_connection" {
  network                 = google_compute_network.pci_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.pci_private_ip_address.name]
}

# PCI-Compliant Storage for cardholder data
resource "google_storage_bucket" "pci_cardholder_data" {
  project  = google_project.pci_project.project_id
  name     = "${var.project_id}-pci-chd-${var.pci_environment}"
  location = var.region

  # PCI DSS requirements
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.pci_storage_key.id
  }

  # Access logging for audit trails
  logging {
    log_bucket = google_storage_bucket.pci_audit_logs.name
  }

  # Data retention policy
  lifecycle_rule {
    condition {
      age = 2555 # 7 years retention
    }
    action {
      type = "Delete"
    }
  }

  # Prevent public access
  public_access_prevention = "enforced"

  labels = {
    environment    = var.pci_environment
    compliance     = "pci-dss"
    data_type      = "cardholder-data"
    classification = "confidential"
  }
}

# Separate audit log storage
resource "google_storage_bucket" "pci_audit_logs" {
  project  = google_project.pci_project.project_id
  name     = "${var.project_id}-pci-audit-${var.pci_environment}"
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.pci_storage_key.id
  }

  # Longer retention for audit logs (10 years)
  lifecycle_rule {
    condition {
      age = 3653
    }
    action {
      type = "Delete"
    }
  }

  public_access_prevention = "enforced"

  labels = {
    environment    = var.pci_environment
    compliance     = "pci-dss"
    data_type      = "audit-logs"
    classification = "confidential"
  }
}

# PCI-DSS IAM Configuration
resource "google_project_iam_custom_role" "pci_cardholder_data_access" {
  project     = google_project.pci_project.project_id
  role_id     = "pci_cardholder_data_access"
  title       = "PCI Cardholder Data Access"
  description = "Limited access to cardholder data for authorized personnel"

  permissions = [
    "storage.objects.get",
    "storage.objects.list",
    "cloudsql.databases.connect",
    "cloudsql.instances.connect",
  ]
}

resource "google_project_iam_custom_role" "pci_security_administrator" {
  project     = google_project.pci_project.project_id
  role_id     = "pci_security_administrator"
  title       = "PCI Security Administrator"
  description = "Security administration for PCI environment"

  permissions = [
    "iam.roles.list",
    "iam.roles.get",
    "logging.logs.list",
    "logging.logEntries.list",
    "monitoring.alertPolicies.list",
    "monitoring.alertPolicies.get",
    "securitycenter.findings.list",
    "securitycenter.sources.list",
  ]
}

# Dedicated service accounts for PCI workloads
resource "google_service_account" "pci_application_sa" {
  project      = google_project.pci_project.project_id
  account_id   = "pci-application-sa"
  display_name = "PCI Application Service Account"
  description  = "Service account for PCI-compliant applications"
}

resource "google_service_account" "pci_database_sa" {
  project      = google_project.pci_project.project_id
  account_id   = "pci-database-sa"
  display_name = "PCI Database Service Account"
  description  = "Service account for PCI database operations"
}

# Comprehensive audit logging
resource "google_logging_project_sink" "pci_comprehensive_audit" {
  project     = google_project.pci_project.project_id
  name        = "pci-comprehensive-audit"
  destination = "storage.googleapis.com/${google_storage_bucket.pci_audit_logs.name}"

  # Capture all activity for PCI compliance
  filter = <<EOF
(protoPayload.serviceName="cloudsql.googleapis.com" OR
protoPayload.serviceName="storage.googleapis.com" OR
protoPayload.serviceName="compute.googleapis.com" OR
protoPayload.serviceName="iam.googleapis.com" OR
protoPayload.serviceName="cloudkms.googleapis.com" OR
logName:"cloudaudit.googleapis.com" OR
severity>=INFO)
EOF

  unique_writer_identity = true
}

# Grant audit sink write permissions
resource "google_storage_bucket_iam_member" "pci_audit_writer" {
  bucket = google_storage_bucket.pci_audit_logs.name
  role   = "roles/storage.objectCreator"
  member = google_logging_project_sink.pci_comprehensive_audit.writer_identity
}

# PCI-DSS Monitoring and Alerting
resource "google_monitoring_alert_policy" "pci_cardholder_data_access" {
  project      = google_project.pci_project.project_id
  display_name = "PCI Cardholder Data Access Alert"
  description  = "Alert on any access to cardholder data storage"

  conditions {
    display_name = "Cardholder Data Access"

    condition_threshold {
      filter          = "resource.type=\"gcs_bucket\" AND resource.labels.bucket_name=\"${google_storage_bucket.pci_cardholder_data.name}\""
      duration        = "0s" # Immediate alerting
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_COUNT"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.pci_security_team.name,
    google_monitoring_notification_channel.pci_pagerduty.name,
  ]

  alert_strategy {
    auto_close = "86400s" # 24 hours
  }
}

resource "google_monitoring_alert_policy" "pci_failed_authentication" {
  project      = google_project.pci_project.project_id
  display_name = "PCI Failed Authentication Alert"
  description  = "Alert on failed authentication attempts"

  conditions {
    display_name = "Failed Authentication Attempts"

    condition_threshold {
      filter          = "resource.type=\"gce_instance\" AND logName=\"projects/${google_project.pci_project.project_id}/logs/syslog\" AND \"authentication failure\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 5 # 5 failed attempts in 5 minutes

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_COUNT"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.pci_security_team.name,
  ]
}

resource "google_monitoring_notification_channel" "pci_security_team" {
  project      = google_project.pci_project.project_id
  display_name = "PCI Security Team"
  type         = "email"

  labels = {
    email_address = "pci-security@company.com"
  }
}

resource "google_monitoring_notification_channel" "pci_pagerduty" {
  project      = google_project.pci_project.project_id
  display_name = "PCI PagerDuty"
  type         = "pagerduty"

  labels = {
    service_key = var.pagerduty_service_key
  }

  sensitive_labels {
    service_key = var.pagerduty_service_key
  }
}

# DLP for PCI data discovery and protection
resource "google_data_loss_prevention_inspect_template" "pci_card_detection" {
  parent       = "projects/${google_project.pci_project.project_id}"
  description  = "Template for detecting payment card data"
  display_name = "PCI Card Data Detection"

  inspect_config {
    info_types {
      name = "CREDIT_CARD_NUMBER"
    }
    info_types {
      name = "CREDIT_CARD_TRACK_NUMBER"
    }
    info_types {
      name = "AMERICAN_EXPRESS_CARD_NUMBER"
    }
    info_types {
      name = "VISA_CARD_NUMBER"
    }
    info_types {
      name = "MASTERCARD_CARD_NUMBER"
    }

    min_likelihood = "POSSIBLE"

    limits {
      max_findings_per_item    = 100
      max_findings_per_request = 1000
    }

    rule_set {
      info_types {
        name = "CREDIT_CARD_NUMBER"
      }
      rules {
        exclusion_rule {
          matching_type = "MATCHING_TYPE_FULL_MATCH"
          dictionary {
            word_list {
              words = ["4111111111111111", "4000000000000002"] # Test card numbers
            }
          }
        }
      }
    }
  }
}

# Web Application Firewall (Cloud Armor) for PCI compliance
resource "google_compute_security_policy" "pci_security_policy" {
  project = google_project.pci_project.project_id
  name    = "pci-security-policy"

  description = "PCI-DSS compliant security policy for web applications"

  # Block suspicious traffic patterns
  rule {
    action   = "deny(403)"
    priority = "1000"
    match {
      expr {
        expression = "origin.region_code == 'CN' || origin.region_code == 'RU'"
      }
    }
    description = "Block traffic from high-risk countries"
  }

  # Rate limiting
  rule {
    action   = "rate_based_ban"
    priority = "2000"
    match {
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      ban_duration_sec = 600
    }
    description = "Rate limit requests"
  }

  # Default allow rule
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }
}

# Outputs
output "pci_project_id" {
  description = "PCI project ID"
  value       = google_project.pci_project.project_id
}

output "pci_vpc_name" {
  description = "PCI VPC network name"
  value       = google_compute_network.pci_vpc.name
}

output "pci_subnets" {
  description = "PCI subnet information"
  value = {
    dmz      = google_compute_subnetwork.pci_dmz.name
    cde      = google_compute_subnetwork.pci_cde.name
    internal = google_compute_subnetwork.pci_internal.name
  }
}

output "pci_database_connection" {
  description = "PCI database connection name"
  value       = google_sql_database_instance.pci_database.connection_name
}

output "pci_kms_keys" {
  description = "PCI KMS key IDs"
  value = {
    database_key    = google_kms_crypto_key.pci_database_key.id
    application_key = google_kms_crypto_key.pci_application_key.id
    storage_key     = google_kms_crypto_key.pci_storage_key.id
  }
}

output "pci_storage_buckets" {
  description = "PCI storage bucket names"
  value = {
    cardholder_data = google_storage_bucket.pci_cardholder_data.name
    audit_logs      = google_storage_bucket.pci_audit_logs.name
  }
}

output "pci_service_accounts" {
  description = "PCI service account emails"
  value = {
    application_sa = google_service_account.pci_application_sa.email
    database_sa    = google_service_account.pci_database_sa.email
  }
}

# Variables
variable "pagerduty_service_key" {
  description = "PagerDuty service key for PCI alerts"
  type        = string
  sensitive   = true
}
