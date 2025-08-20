variable "project_id" {
  description = "GCP project ID where the workload identity pool will be created"
  type        = string
}

variable "pool_id" {
  description = "Workload identity pool ID (must be 4-32 characters)"
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{3,31}$", var.pool_id))
    error_message = "Pool ID must be 4-32 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "pool_display_name" {
  description = "Display name for the workload identity pool"
  type        = string
  default     = ""
}

variable "pool_description" {
  description = "Description of the workload identity pool"
  type        = string
  default     = "Workload Identity Pool for CI/CD authentication"
}

variable "pool_disabled" {
  description = "Whether the pool is disabled"
  type        = bool
  default     = false
}

variable "providers" {
  description = "Map of identity providers to configure"
  type = map(object({
    provider_id    = string
    display_name   = optional(string)
    description    = optional(string)
    disabled       = optional(bool, false)
    issuer_uri     = optional(string)
    jwks_json      = optional(string)
    allowed_audiences = optional(list(string), [])
    
    # Attribute mapping
    attribute_mapping = optional(map(string), {})
    
    # Attribute conditions for fine-grained access control
    attribute_condition = optional(string)
    
    # Provider-specific configurations
    github = optional(object({
      organization = optional(string)
      repositories = optional(list(string))
      environments = optional(list(string))
      branches     = optional(list(string))
    }))
    
    gitlab = optional(object({
      project_path = optional(string)
      group_path   = optional(string)
      branches     = optional(list(string))
      environments = optional(list(string))
    }))
    
    azure_devops = optional(object({
      organization = optional(string)
      project      = optional(string)
      branches     = optional(list(string))
    }))
    
    terraform_cloud = optional(object({
      organization = optional(string)
      project      = optional(string)
      workspace    = optional(string)
      run_phase    = optional(string)
    }))
  }))
  default = {}
}

variable "service_accounts" {
  description = "Map of service accounts to bind with workload identity"
  type = map(object({
    service_account_id   = string
    display_name        = optional(string)
    description         = optional(string)
    create_new          = optional(bool, true)
    existing_email      = optional(string)
    
    # IAM bindings
    project_roles = optional(list(string), [])
    
    # Workload identity bindings
    bindings = list(object({
      provider_id         = string
      attribute_condition = optional(string)
      roles              = optional(list(string), ["roles/iam.workloadIdentityUser"])
    }))
  }))
  default = {}
}

variable "enable_attribute_conditions" {
  description = "Enable attribute-based access control conditions"
  type        = bool
  default     = true
}

variable "session_duration" {
  description = "Duration for which the access token is valid (in seconds)"
  type        = string
  default     = "3600s"
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}