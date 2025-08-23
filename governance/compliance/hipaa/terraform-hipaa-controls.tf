# HIPAA Compliance Infrastructure Controls
# Terraform implementation of HIPAA technical safeguards

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID for HIPAA workloads"
  type        = string
}

variable "region" {
  description = "Primary region for HIPAA resources"
  type        = string
  default     = "us-central1"
}

variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
}

variable "billing_account" {
  description = "Billing account for HIPAA projects"
  type        = string
}

variable "hipaa_environment" {
  description = "HIPAA environment type"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.hipaa_environment)
    error_message = "HIPAA environment must be development, staging, or production."
  }
}

# HIPAA Project Configuration
resource "google_project" "hipaa_project" {
  name            = "hipaa-${var.hipaa_environment}"
  project_id      = var.project_id
  billing_account = var.billing_account
  org_id          = var.organization_id

  labels = {
    environment         = var.hipaa_environment
    compliance          = "hipaa"
    data_classification = "phi"
    criticality         = "high"
  }
}

# Enable required APIs
resource "google_project_service" "hipaa_apis" {
  project = google_project.hipaa_project.project_id

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
    "vpcaccess.googleapis.com"
  ])

  service = each.value

  disable_dependent_services = true
}

# HIPAA-Compliant VPC with Private Google Access
resource "google_compute_network" "hipaa_vpc" {
  project                 = google_project.hipaa_project.project_id
  name                    = "hipaa-vpc-${var.hipaa_environment}"
  auto_create_subnetworks = false
  description             = "HIPAA-compliant VPC for PHI workloads"

  depends_on = [google_project_service.hipaa_apis]
}

resource "google_compute_subnetwork" "hipaa_subnet" {
  project       = google_project.hipaa_project.project_id
  name          = "hipaa-subnet-${var.region}"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.hipaa_vpc.name

  # Enable Private Google Access for API access without external IPs
  private_ip_google_access = true

  # Enable flow logs for audit trails
  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }

  # Secondary ranges for GKE if needed
  secondary_ip_range {
    range_name    = "hipaa-pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "hipaa-services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

# HIPAA-Compliant Firewall Rules
resource "google_compute_firewall" "hipaa_deny_all_ingress" {
  project = google_project.hipaa_project.project_id
  name    = "hipaa-deny-all-ingress"
  network = google_compute_network.hipaa_vpc.name

  description = "Deny all ingress traffic by default for HIPAA compliance"
  direction   = "INGRESS"
  priority    = 65534

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_firewall" "hipaa_allow_internal" {
  project = google_project.hipaa_project.project_id
  name    = "hipaa-allow-internal"
  network = google_compute_network.hipaa_vpc.name

  description = "Allow internal communication within HIPAA VPC"
  direction   = "INGRESS"
  priority    = 1000

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/8"]
  target_tags   = ["hipaa-internal"]
}

resource "google_compute_firewall" "hipaa_allow_health_checks" {
  project = google_project.hipaa_project.project_id
  name    = "hipaa-allow-health-checks"
  network = google_compute_network.hipaa_vpc.name

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

  target_tags = ["hipaa-load-balanced"]
}

# Customer-Managed Encryption Keys (CMEK) for HIPAA
resource "google_kms_key_ring" "hipaa_keyring" {
  project  = google_project.hipaa_project.project_id
  name     = "hipaa-keyring-${var.hipaa_environment}"
  location = var.region

  depends_on = [google_project_service.hipaa_apis]
}

resource "google_kms_crypto_key" "hipaa_database_key" {
  name     = "hipaa-database-key"
  key_ring = google_kms_key_ring.hipaa_keyring.id
  purpose  = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "HSM"
  }

  lifecycle {
    prevent_destroy = true
  }

  rotation_period = "90d" # HIPAA recommends key rotation
}

resource "google_kms_crypto_key" "hipaa_storage_key" {
  name     = "hipaa-storage-key"
  key_ring = google_kms_key_ring.hipaa_keyring.id
  purpose  = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "HSM"
  }

  lifecycle {
    prevent_destroy = true
  }

  rotation_period = "90d"
}

resource "google_kms_crypto_key" "hipaa_compute_key" {
  name     = "hipaa-compute-key"
  key_ring = google_kms_key_ring.hipaa_keyring.id
  purpose  = "ENCRYPT_DECRYPT"

  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "HSM"
  }

  lifecycle {
    prevent_destroy = true
  }

  rotation_period = "90d"
}

# HIPAA-Compliant Cloud SQL Instance
resource "google_sql_database_instance" "hipaa_database" {
  project          = google_project.hipaa_project.project_id
  name             = "hipaa-db-${var.hipaa_environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier                        = "db-custom-4-16384"
    availability_type           = "REGIONAL" # High availability for HIPAA
    deletion_protection_enabled = true

    database_flags {
      name  = "log_statement"
      value = "all" # Log all statements for audit
    }

    database_flags {
      name  = "log_min_duration_statement"
      value = "0" # Log all query durations
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
      ipv4_enabled    = false
      private_network = google_compute_network.hipaa_vpc.id
      require_ssl     = true # Force SSL/TLS

      authorized_networks {
        name  = "internal-only"
        value = "10.0.0.0/8"
      }
    }

    disk_encryption_configuration {
      kms_key_name = google_kms_crypto_key.hipaa_database_key.id
    }
  }

  depends_on = [
    google_project_service.hipaa_apis,
    google_service_networking_connection.private_vpc_connection
  ]
}

# Private Service Networking for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  project       = google_project.hipaa_project.project_id
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.hipaa_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.hipaa_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# HIPAA-Compliant GCS Bucket for PHI Storage
resource "google_storage_bucket" "hipaa_phi_storage" {
  project  = google_project.hipaa_project.project_id
  name     = "${var.project_id}-hipaa-phi-${var.hipaa_environment}"
  location = var.region

  uniform_bucket_level_access = true # Required for HIPAA

  versioning {
    enabled = true # Version control for audit trails
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.hipaa_storage_key.id
  }

  # Lifecycle rules to manage PHI retention
  lifecycle_rule {
    condition {
      age = 2555 # 7 years retention as per HIPAA
    }
    action {
      type = "Delete"
    }
  }

  logging {
    log_bucket = google_storage_bucket.hipaa_audit_logs.name
  }

  labels = {
    environment         = var.hipaa_environment
    compliance          = "hipaa"
    data_classification = "phi"
  }
}

# Separate bucket for audit logs
resource "google_storage_bucket" "hipaa_audit_logs" {
  project  = google_project.hipaa_project.project_id
  name     = "${var.project_id}-hipaa-audit-${var.hipaa_environment}"
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.hipaa_storage_key.id
  }

  # Longer retention for audit logs
  lifecycle_rule {
    condition {
      age = 3653 # 10 years retention for audit logs
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment         = var.hipaa_environment
    compliance          = "hipaa"
    data_classification = "audit"
  }
}

# IAM Bindings for HIPAA Compliance
resource "google_project_iam_binding" "hipaa_data_protection_officer" {
  project = google_project.hipaa_project.project_id
  role    = "roles/iam.securityReviewer"

  members = [
    "group:hipaa-data-protection-officers@company.com",
  ]

  condition {
    title       = "HIPAA DPO Access"
    description = "Conditional access for HIPAA Data Protection Officers"
    expression  = "request.time.getHours() >= 8 && request.time.getHours() <= 18"
  }
}

resource "google_project_iam_binding" "hipaa_security_officer" {
  project = google_project.hipaa_project.project_id
  role    = "roles/iam.securityAdmin"

  members = [
    "group:hipaa-security-officers@company.com",
  ]

  condition {
    title       = "HIPAA Security Officer Access"
    description = "Full security administration for HIPAA environments"
    expression  = "true" # Always allow for security officers
  }
}

# Custom IAM Role for PHI Access
resource "google_project_iam_custom_role" "phi_access_role" {
  project     = google_project.hipaa_project.project_id
  role_id     = "phi_access_role"
  title       = "PHI Access Role"
  description = "Custom role for controlled PHI access"

  permissions = [
    "storage.objects.get",
    "storage.objects.list",
    "cloudsql.databases.connect",
    "cloudsql.instances.connect",
  ]
}

# Cloud Logging for HIPAA Audit Trails
resource "google_logging_project_sink" "hipaa_audit_sink" {
  project     = google_project.hipaa_project.project_id
  name        = "hipaa-audit-sink"
  destination = "storage.googleapis.com/${google_storage_bucket.hipaa_audit_logs.name}"

  # Capture all admin activity and data access logs
  filter = <<EOF
protoPayload.serviceName="cloudsql.googleapis.com" OR
protoPayload.serviceName="storage.googleapis.com" OR
protoPayload.serviceName="compute.googleapis.com" OR
logName:"cloudaudit.googleapis.com" OR
severity>=WARNING
EOF

  unique_writer_identity = true
}

# Grant the logging sink permission to write to the bucket
resource "google_storage_bucket_iam_member" "hipaa_log_writer" {
  bucket = google_storage_bucket.hipaa_audit_logs.name
  role   = "roles/storage.objectCreator"
  member = google_logging_project_sink.hipaa_audit_sink.writer_identity
}

# HIPAA Monitoring and Alerting
resource "google_monitoring_alert_policy" "phi_access_alert" {
  project      = google_project.hipaa_project.project_id
  display_name = "HIPAA PHI Access Alert"
  description  = "Alert on PHI access outside business hours"

  conditions {
    display_name = "PHI Access Condition"

    condition_threshold {
      filter          = "resource.type=\"gcs_bucket\" AND resource.labels.bucket_name=\"${google_storage_bucket.hipaa_phi_storage.name}\""
      duration        = "60s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_COUNT"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.hipaa_email.name,
    google_monitoring_notification_channel.hipaa_pagerduty.name,
  ]

  alert_strategy {
    auto_close = "1800s" # 30 minutes
  }
}

resource "google_monitoring_notification_channel" "hipaa_email" {
  project      = google_project.hipaa_project.project_id
  display_name = "HIPAA Security Team Email"
  type         = "email"

  labels = {
    email_address = "hipaa-security@company.com"
  }
}

resource "google_monitoring_notification_channel" "hipaa_pagerduty" {
  project      = google_project.hipaa_project.project_id
  display_name = "HIPAA PagerDuty"
  type         = "pagerduty"

  labels = {
    service_key = var.pagerduty_service_key
  }

  sensitive_labels {
    service_key = var.pagerduty_service_key
  }
}

# Data Loss Prevention (DLP) for PHI Detection
resource "google_data_loss_prevention_inspect_template" "phi_inspect_template" {
  parent       = "projects/${google_project.hipaa_project.project_id}"
  description  = "Template for detecting PHI in data"
  display_name = "PHI Detection Template"

  inspect_config {
    info_types {
      name = "US_HEALTHCARE_NPI"
    }
    info_types {
      name = "US_DEA_NUMBER"
    }
    info_types {
      name = "DATE_OF_BIRTH"
    }
    info_types {
      name = "US_SOCIAL_SECURITY_NUMBER"
    }
    info_types {
      name = "MEDICAL_RECORD_NUMBER"
    }
    info_types {
      name = "US_DRIVER_LICENSE_NUMBER"
    }

    min_likelihood = "POSSIBLE"

    limits {
      max_findings_per_item    = 100
      max_findings_per_request = 1000
    }
  }
}

# VPC Service Controls for Additional Security
resource "google_access_context_manager_access_policy" "hipaa_policy" {
  parent = "organizations/${var.organization_id}"
  title  = "HIPAA Access Policy"
}

resource "google_access_context_manager_service_perimeter" "hipaa_perimeter" {
  parent = "accessPolicies/${google_access_context_manager_access_policy.hipaa_policy.name}"
  name   = "accessPolicies/${google_access_context_manager_access_policy.hipaa_policy.name}/servicePerimeters/hipaa_perimeter"
  title  = "HIPAA Service Perimeter"

  status {
    restricted_services = [
      "storage.googleapis.com",
      "cloudsql.googleapis.com",
      "compute.googleapis.com"
    ]

    resources = ["projects/${google_project.hipaa_project.number}"]

    access_levels = [
      google_access_context_manager_access_level.hipaa_access_level.name,
    ]
  }
}

resource "google_access_context_manager_access_level" "hipaa_access_level" {
  parent = "accessPolicies/${google_access_context_manager_access_policy.hipaa_policy.name}"
  name   = "accessPolicies/${google_access_context_manager_access_policy.hipaa_policy.name}/accessLevels/hipaa_access_level"
  title  = "HIPAA Access Level"

  basic {
    conditions {
      ip_subnetworks = [
        "10.0.0.0/8" # Only allow access from internal networks
      ]
    }

    conditions {
      device_policy {
        require_screen_lock              = true
        require_admin_approval           = true
        require_corp_owned               = true
        allowed_encryption_statuses      = ["ENCRYPTED"]
        allowed_device_management_levels = ["COMPLETE"]
      }
    }
  }
}

# Outputs
output "hipaa_project_id" {
  description = "HIPAA project ID"
  value       = google_project.hipaa_project.project_id
}

output "hipaa_vpc_name" {
  description = "HIPAA VPC network name"
  value       = google_compute_network.hipaa_vpc.name
}

output "hipaa_database_connection_name" {
  description = "HIPAA database connection name"
  value       = google_sql_database_instance.hipaa_database.connection_name
}

output "hipaa_kms_keys" {
  description = "HIPAA CMEK key IDs"
  value = {
    database_key = google_kms_crypto_key.hipaa_database_key.id
    storage_key  = google_kms_crypto_key.hipaa_storage_key.id
    compute_key  = google_kms_crypto_key.hipaa_compute_key.id
  }
}

output "hipaa_storage_buckets" {
  description = "HIPAA storage bucket names"
  value = {
    phi_bucket   = google_storage_bucket.hipaa_phi_storage.name
    audit_bucket = google_storage_bucket.hipaa_audit_logs.name
  }
}

# Variables for PagerDuty integration
variable "pagerduty_service_key" {
  description = "PagerDuty service key for HIPAA alerts"
  type        = string
  sensitive   = true
}
