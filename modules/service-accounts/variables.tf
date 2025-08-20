/**
 * Service Accounts Module - Variables
 * 
 * Define input variables for service account creation and management
 */

variable "project_id" {
  description = "The default GCP project ID where service accounts will be created"
  type        = string
}

variable "organization_id" {
  description = "The GCP organization ID (required for organization-level role bindings)"
  type        = string
  default     = null
}

variable "service_accounts" {
  description = "Map of service accounts to create with their configurations"
  type = map(object({
    # Basic configuration
    account_id   = string                # The service account ID (must be unique within project)
    display_name = string                # Display name for the service account
    description  = optional(string)      # Description of the service account's purpose
    project_id   = optional(string)      # Override project ID for this specific SA
    disabled     = optional(bool, false) # Whether the service account is disabled

    # IAM role bindings
    project_roles      = optional(list(string), [])         # List of project-level IAM roles
    organization_roles = optional(list(string), [])         # List of organization-level IAM roles
    folder_roles       = optional(map(list(string)), {})    # Map of folder IDs to list of roles

    # Impersonation configuration
    impersonators = optional(list(string), []) # List of identities that can impersonate this SA

    # Key management
    create_key           = optional(bool, false)     # Whether to create a key for this SA
    key_secret_accessors = optional(list(string), []) # Who can access the key in Secret Manager
  }))

  validation {
    condition = alltrue([
      for sa_key, sa in var.service_accounts :
      can(regex("^[a-z]([a-z0-9-]*[a-z0-9])?$", sa.account_id)) &&
      length(sa.account_id) >= 6 &&
      length(sa.account_id) <= 30
    ])
    error_message = "Service account IDs must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "store_keys_in_secret_manager" {
  description = "Whether to store service account keys in Secret Manager"
  type        = bool
  default     = true
}

variable "labels" {
  description = "Labels to apply to all resources created by this module"
  type        = map(string)
  default     = {}
}

# Predefined role sets for common use cases
variable "predefined_roles" {
  description = "Predefined role sets for common service account types"
  type = object({
    terraform_deployer = optional(list(string), [
      "roles/resourcemanager.projectIamAdmin",
      "roles/storage.admin",
      "roles/compute.admin",
      "roles/iam.serviceAccountAdmin",
      "roles/iam.serviceAccountKeyAdmin",
      "roles/secretmanager.admin",
      "roles/servicenetworking.networksAdmin",
      "roles/dns.admin",
      "roles/cloudkms.admin"
    ])
    cicd_pipeline = optional(list(string), [
      "roles/cloudbuild.builds.editor",
      "roles/storage.objectAdmin",
      "roles/artifactregistry.writer",
      "roles/run.admin",
      "roles/cloudfunction.admin",
      "roles/appengine.deployer",
      "roles/iam.serviceAccountUser"
    ])
    monitoring = optional(list(string), [
      "roles/monitoring.metricWriter",
      "roles/logging.logWriter",
      "roles/cloudtrace.agent",
      "roles/cloudprofiler.agent",
      "roles/errorreporting.writer"
    ])
    application_runtime = optional(list(string), [
      "roles/storage.objectViewer",
      "roles/secretmanager.secretAccessor",
      "roles/cloudsql.client",
      "roles/datastore.user",
      "roles/pubsub.publisher",
      "roles/pubsub.subscriber",
      "roles/cloudtasks.enqueuer"
    ])
    data_pipeline = optional(list(string), [
      "roles/bigquery.dataEditor",
      "roles/bigquery.jobUser",
      "roles/storage.objectAdmin",
      "roles/dataflow.worker",
      "roles/pubsub.editor",
      "roles/cloudfunctions.invoker"
    ])
    security_scanner = optional(list(string), [
      "roles/securitycenter.findingsViewer",
      "roles/cloudkms.viewer",
      "roles/iam.securityReviewer",
      "roles/compute.viewer",
      "roles/storage.objectViewer"
    ])
  })
  default = {}
}

# Common impersonation configurations
variable "enable_cross_project_impersonation" {
  description = "Enable service accounts to be impersonated from other projects"
  type        = bool
  default     = false
}

variable "impersonation_admin_members" {
  description = "List of identities that can manage impersonation for all service accounts"
  type        = list(string)
  default     = []
}

# Audit and compliance settings
variable "enable_audit_logs" {
  description = "Enable detailed audit logging for service account activities"
  type        = bool
  default     = true
}

variable "key_rotation_days" {
  description = "Number of days before service account keys should be rotated (informational)"
  type        = number
  default     = 90
}