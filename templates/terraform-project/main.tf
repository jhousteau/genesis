terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    # Configure after running terraform init
    # bucket = "your-project-terraform-state"
    # prefix = "terraform/state"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Use Genesis modules to set up GCP project infrastructure
module "project_setup" {
  source = "../../terraform/modules/project-setup"

  project_id      = var.gcp_project_id
  project_name    = var.project_name
  billing_account = var.gcp_billing_account
  organization_id = var.gcp_organization_id
  location        = var.gcp_region

  # Service account configuration  
  service_accounts = var.service_accounts

  labels = {
    environment = "development"
    managed_by  = "terraform"
    project     = var.project_name
  }
}

# Example: Additional resources for your specific project
# Uncomment and customize as needed

# resource "google_compute_network" "main" {
#   name                    = "${var.project_name}-network"
#   auto_create_subnetworks = false
# }

# resource "google_compute_subnetwork" "main" {
#   name          = "${var.project_name}-subnet"
#   network       = google_compute_network.main.id
#   ip_cidr_range = "10.0.0.0/24"
#   region        = var.gcp_region
# }