variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "bucket_name" {
  description = "Name of the GCS bucket for Terraform state (defaults to PROJECT_ID-terraform-state)"
  type        = string
  default     = ""
}

variable "location" {
  description = "Location for the GCS bucket"
  type        = string
  default     = "US"
}

variable "storage_class" {
  description = "Storage class for the bucket"
  type        = string
  default     = "STANDARD"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "development"
}

variable "force_destroy" {
  description = "Allow Terraform to destroy the bucket even if it contains objects"
  type        = bool
  default     = false
}

variable "max_versions" {
  description = "Maximum number of state file versions to keep"
  type        = number
  default     = 5
}

variable "kms_key_name" {
  description = "Optional KMS key name for bucket encryption"
  type        = string
  default     = null
}

variable "create_terraform_sa" {
  description = "Create a service account for Terraform operations"
  type        = bool
  default     = false
}

variable "terraform_sa_name" {
  description = "Name for the Terraform service account"
  type        = string
  default     = "terraform"
}

variable "workload_identity_user" {
  description = "Workload Identity user for GitHub Actions (e.g., 'principalSet://iam.googleapis.com/projects/123/locations/global/workloadIdentityPools/pool/attribute.repository/org/repo')"
  type        = string
  default     = null
}

variable "labels" {
  description = "Additional labels to apply to resources"
  type        = map(string)
  default     = {}
}