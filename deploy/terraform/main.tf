terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

# Project Configuration
locals {
  project_id   = var.project_id
  region       = var.region
  environment  = var.environment
  
  common_labels = {
    environment = var.environment
    project     = var.project_name
    managed_by  = "terraform"
    platform    = "universal-bootstrapper"
  }
}

# GKE Cluster for Application Deployment
resource "google_container_cluster" "primary" {
  name     = "${var.project_name}-${var.environment}-cluster"
  location = var.region
  
  # Autopilot mode for managed Kubernetes
  enable_autopilot = true
  
  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name
  
  resource_labels = local.common_labels
  
  # Security settings
  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "All networks"
    }
  }
  
  # Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${var.project_name}-${var.environment}-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.project_name}-${var.environment}-subnet"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
  
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr
  }
  
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr
  }
}

# Cloud Storage Bucket for Application Assets
resource "google_storage_bucket" "assets" {
  name          = "${var.project_id}-${var.environment}-assets"
  location      = var.region
  force_destroy = var.environment != "prod"
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
  
  labels = local.common_labels
}

# Firestore Database
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

# Cloud Run Service (for serverless deployments)
resource "google_cloud_run_service" "app" {
  count    = var.enable_cloud_run ? 1 : 0
  name     = "${var.project_name}-${var.environment}"
  location = var.region
  
  template {
    spec {
      containers {
        image = var.container_image
        
        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
        
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
      }
      
      service_account_name = google_service_account.app.email
    }
    
    metadata {
      labels = local.common_labels
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Service Account for Application
resource "google_service_account" "app" {
  account_id   = "${var.project_name}-${var.environment}-sa"
  display_name = "Service Account for ${var.project_name} ${var.environment}"
  project      = var.project_id
}

# IAM Bindings
resource "google_project_iam_member" "app_permissions" {
  for_each = toset([
    "roles/datastore.user",
    "roles/storage.objectAdmin",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Outputs
output "cluster_name" {
  value = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  value     = google_container_cluster.primary.endpoint
  sensitive = true
}

output "service_account_email" {
  value = google_service_account.app.email
}

output "bucket_name" {
  value = google_storage_bucket.assets.name
}

output "cloud_run_url" {
  value = var.enable_cloud_run ? google_cloud_run_service.app[0].status[0].url : null
}