variable "project_id" {
  description = "Default project ID for service accounts"
  type        = string
}

variable "service_accounts" {
  description = "Map of service accounts to create"
  type = map(object({
    account_id    = string
    display_name  = string
    description   = string
    project_id    = optional(string) # Override default project_id
    disabled      = optional(bool, false)
    project_roles = optional(list(string), [])
    create_key    = optional(bool, false) # Not recommended for production
    impersonators = optional(list(string), [])
  }))
  default = {}
}
