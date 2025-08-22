#!/bin/bash

# Multi-Project Bootstrap Deployment Script
# Deploys bootstrap configuration to multiple GCP projects from a list

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
MULTI_PROJECT_MODULE="$ROOT_DIR/modules/multi-project"
DEPLOYMENT_DIR="$ROOT_DIR/deployments"
LOG_FILE="/tmp/multi-project-deploy-$(date +%Y%m%d-%H%M%S).log"

# Default values
DRY_RUN=false
PARALLEL=true
FAIL_FAST=false
PROJECT_LIST=""
CONFIG_FILE=""
ENVIRONMENT="development"

# Function to print colored messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy bootstrap configuration to multiple GCP projects.

OPTIONS:
    -h, --help              Show this help message
    -l, --list FILE         Path to file containing project list (CSV or JSON)
    -c, --config FILE       Path to Terraform variables file
    -e, --environment ENV   Environment name (dev/staging/prod)
    -o, --org-id ID        Organization ID
    -b, --billing ID       Billing account ID
    -p, --prefix PREFIX    Project ID prefix
    -d, --dry-run          Perform dry run (plan only)
    -s, --sequential       Deploy sequentially (not parallel)
    -f, --fail-fast        Stop on first error
    --github-org ORG       GitHub organization for WIF
    --output-dir DIR       Output directory for configs

EXAMPLES:
    # Deploy from CSV file
    $0 --list projects.csv --org-id 123456789 --billing XXXXX-XXXXX-XXXXX

    # Deploy from JSON with custom config
    $0 --list projects.json --config custom.tfvars

    # Dry run with sequential deployment
    $0 --list projects.csv --dry-run --sequential

    # Production deployment with fail-fast
    $0 --list prod-projects.json --environment production --fail-fast

CSV FORMAT:
    project_id,billing_account,environment,budget
    my-project-1,XXXXX-XXXXX,development,1000
    my-project-2,XXXXX-XXXXX,staging,2000

JSON FORMAT:
    {
      "projects": [
        {
          "project_id": "my-project-1",
          "billing_account": "XXXXX-XXXXX",
          "environment": "development",
          "budget_amount": 1000
        }
      ]
    }
EOF
    exit 0
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                ;;
            -l|--list)
                PROJECT_LIST="$2"
                shift 2
                ;;
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -o|--org-id)
                ORG_ID="$2"
                shift 2
                ;;
            -b|--billing)
                BILLING_ACCOUNT="$2"
                shift 2
                ;;
            -p|--prefix)
                PROJECT_PREFIX="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -s|--sequential)
                PARALLEL=false
                shift
                ;;
            -f|--fail-fast)
                FAIL_FAST=true
                shift
                ;;
            --github-org)
                GITHUB_ORG="$2"
                shift 2
                ;;
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed"
        exit 1
    fi
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed"
        exit 1
    fi
    
    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        log_error "Not authenticated with GCP. Run: gcloud auth login"
        exit 1
    fi
    
    # Check project list file
    if [[ -z "$PROJECT_LIST" ]]; then
        log_error "Project list file is required (--list)"
        usage
    fi
    
    if [[ ! -f "$PROJECT_LIST" ]]; then
        log_error "Project list file not found: $PROJECT_LIST"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Parse project list file
parse_project_list() {
    local file="$1"
    local extension="${file##*.}"
    local temp_file="/tmp/projects-$(date +%s).json"
    
    log_info "Parsing project list from $file..."
    
    case "$extension" in
        csv)
            # Convert CSV to JSON
            python3 << EOF > "$temp_file"
import csv
import json
import sys

projects = []
with open('$file', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        project = {
            "project_id": row.get("project_id"),
            "billing_account": row.get("billing_account"),
            "environment": row.get("environment", "$ENVIRONMENT"),
            "budget_amount": int(row.get("budget", 1000))
        }
        # Add optional fields if present
        if "labels" in row:
            project["labels"] = json.loads(row["labels"])
        if "apis" in row:
            project["activate_apis"] = row["apis"].split(";")
        projects.append(project)

print(json.dumps({"projects": projects}, indent=2))
EOF
            ;;
        json)
            # Validate and format JSON
            python3 -m json.tool "$file" > "$temp_file"
            ;;
        txt)
            # Simple text file with project IDs
            python3 << EOF > "$temp_file"
import json

projects = []
with open('$file', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            projects.append({
                "project_id": line,
                "billing_account": "${BILLING_ACCOUNT:-}",
                "environment": "$ENVIRONMENT"
            })

print(json.dumps({"projects": projects}, indent=2))
EOF
            ;;
        *)
            log_error "Unsupported file format: $extension"
            exit 1
            ;;
    esac
    
    echo "$temp_file"
}

# Generate Terraform configuration
generate_terraform_config() {
    local projects_json="$1"
    local deployment_name="multi-project-$(date +%Y%m%d-%H%M%S)"
    local deployment_path="$DEPLOYMENT_DIR/$deployment_name"
    
    log_info "Generating Terraform configuration..."
    
    # Create deployment directory
    mkdir -p "$deployment_path"
    
    # Generate main.tf
    cat > "$deployment_path/main.tf" << 'EOF'
terraform {
  required_version = ">= 1.5"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  # Uses application default credentials
}

module "multi_project_bootstrap" {
  source = "../../modules/multi-project"
  
  deployment_name = var.deployment_name
  project_group   = var.project_group
  org_id          = var.org_id
  folder_id       = var.folder_id
  default_region  = var.default_region
  
  projects = var.projects
  
  # Feature flags
  create_state_buckets     = var.create_state_buckets
  create_service_accounts  = var.create_service_accounts
  enable_workload_identity = var.enable_workload_identity
  
  # Deployment options
  parallel_deployments     = var.parallel_deployments
  error_on_partial_failure = var.error_on_partial_failure
  dry_run                 = var.dry_run
  
  # WIF configuration
  default_wif_providers = var.github_org != "" ? {
    github = {
      provider_id   = "github-actions"
      provider_type = "github"
      github = {
        organization = var.github_org
      }
    }
  } : {}
}
EOF
    
    # Generate variables.tf
    cat > "$deployment_path/variables.tf" << 'EOF'
variable "deployment_name" {
  type    = string
  default = "multi-project-deployment"
}

variable "project_group" {
  type    = string
  default = "bootstrap-projects"
}

variable "org_id" {
  type    = string
  default = ""
}

variable "folder_id" {
  type    = string
  default = ""
}

variable "default_region" {
  type    = string
  default = "us-central1"
}

variable "projects" {
  type = list(object({
    project_id      = string
    billing_account = string
    environment     = optional(string)
    budget_amount   = optional(number)
    labels          = optional(map(string))
    activate_apis   = optional(list(string))
  }))
}

variable "create_state_buckets" {
  type    = bool
  default = true
}

variable "create_service_accounts" {
  type    = bool
  default = true
}

variable "enable_workload_identity" {
  type    = bool
  default = true
}

variable "parallel_deployments" {
  type    = bool
  default = true
}

variable "error_on_partial_failure" {
  type    = bool
  default = false
}

variable "dry_run" {
  type    = bool
  default = false
}

variable "github_org" {
  type    = string
  default = ""
}
EOF
    
    # Generate terraform.tfvars
    cat > "$deployment_path/terraform.tfvars" << EOF
deployment_name = "$deployment_name"
project_group   = "automated-deployment"
org_id          = "${ORG_ID:-}"
folder_id       = "${FOLDER_ID:-}"
default_region  = "${DEFAULT_REGION:-us-central1}"

parallel_deployments     = $PARALLEL
error_on_partial_failure = $FAIL_FAST
dry_run                 = $DRY_RUN

github_org = "${GITHUB_ORG:-}"

# Projects loaded from: $PROJECT_LIST
projects = $(jq '.projects' "$projects_json")
EOF
    
    # Generate outputs.tf
    cat > "$deployment_path/outputs.tf" << 'EOF'
output "deployed_projects" {
  value = module.multi_project_bootstrap.project_ids
}

output "state_buckets" {
  value = module.multi_project_bootstrap.state_buckets
}

output "service_accounts" {
  value = module.multi_project_bootstrap.all_service_accounts
}

output "summary" {
  value = module.multi_project_bootstrap.summary
}

output "terraform_configs" {
  value = module.multi_project_bootstrap.generated_tfvars
}
EOF
    
    # Copy custom config if provided
    if [[ -n "$CONFIG_FILE" ]] && [[ -f "$CONFIG_FILE" ]]; then
        log_info "Using custom configuration from $CONFIG_FILE"
        cp "$CONFIG_FILE" "$deployment_path/custom.tfvars"
    fi
    
    echo "$deployment_path"
}

# Deploy projects
deploy_projects() {
    local deployment_path="$1"
    
    log_info "Starting deployment from $deployment_path"
    
    cd "$deployment_path"
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init -upgrade
    
    # Format code
    terraform fmt
    
    # Validate configuration
    log_info "Validating configuration..."
    terraform validate
    
    # Plan deployment
    log_info "Planning deployment..."
    if [[ -f "custom.tfvars" ]]; then
        terraform plan -var-file="custom.tfvars" -out=tfplan
    else
        terraform plan -out=tfplan
    fi
    
    # Show summary
    terraform show -json tfplan | jq -r '
        .planned_values.root_module.child_modules[].resources[] |
        select(.type == "google_project") |
        .values.project_id
    ' | while read -r project; do
        log_info "Will deploy: $project"
    done
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "Dry run mode - not applying changes"
        return 0
    fi
    
    # Confirm deployment
    echo
    read -p "Do you want to proceed with the deployment? (yes/no): " -r
    if [[ ! "$REPLY" =~ ^[Yy]es$ ]]; then
        log_warning "Deployment cancelled by user"
        return 1
    fi
    
    # Apply configuration
    log_info "Applying configuration..."
    terraform apply tfplan
    
    # Save outputs
    if [[ -n "${OUTPUT_DIR:-}" ]]; then
        mkdir -p "$OUTPUT_DIR"
        terraform output -json > "$OUTPUT_DIR/outputs.json"
        terraform output -raw terraform_configs > "$OUTPUT_DIR/project_configs.txt"
        log_success "Outputs saved to $OUTPUT_DIR"
    fi
    
    log_success "Deployment completed successfully!"
}

# Generate summary report
generate_report() {
    local deployment_path="$1"
    
    cd "$deployment_path"
    
    log_info "Generating deployment report..."
    
    # Get deployment summary
    local summary=$(terraform output -json summary 2>/dev/null || echo "{}")
    
    cat > "$deployment_path/report.md" << EOF
# Multi-Project Deployment Report

**Date**: $(date)
**Deployment Name**: $(echo "$summary" | jq -r '.deployment_name // "N/A"')
**Total Projects**: $(echo "$summary" | jq -r '.total_projects // 0')

## Projects Deployed

$(terraform output -json deployed_projects 2>/dev/null | jq -r 'to_entries[] | "- \(.key): \(.value)"' || echo "No projects deployed")

## State Buckets Created

$(terraform output -json state_buckets 2>/dev/null | jq -r 'to_entries[] | "- \(.key): \(.value)"' || echo "No state buckets created")

## Service Accounts

$(terraform output -json service_accounts 2>/dev/null | jq -r 'to_entries[] | "### \(.key)\n\(.value.emails | to_entries[] | "- \(.key): \(.value)")"' || echo "No service accounts created")

## Configuration

- Parallel Deployment: $PARALLEL
- Fail Fast: $FAIL_FAST
- Dry Run: $DRY_RUN
- Environment: $ENVIRONMENT

## Log File

See detailed logs at: $LOG_FILE
EOF
    
    log_success "Report saved to $deployment_path/report.md"
}

# Main execution
main() {
    log_info "Multi-Project Bootstrap Deployment Script"
    log_info "Log file: $LOG_FILE"
    
    # Parse arguments
    parse_args "$@"
    
    # Check prerequisites
    check_prerequisites
    
    # Parse project list
    projects_json=$(parse_project_list "$PROJECT_LIST")
    
    # Validate parsed projects
    project_count=$(jq '.projects | length' "$projects_json")
    log_info "Found $project_count projects to deploy"
    
    if [[ "$project_count" -eq 0 ]]; then
        log_error "No projects found in the list"
        exit 1
    fi
    
    # Generate Terraform configuration
    deployment_path=$(generate_terraform_config "$projects_json")
    log_success "Generated Terraform configuration at: $deployment_path"
    
    # Deploy projects
    if deploy_projects "$deployment_path"; then
        # Generate report
        generate_report "$deployment_path"
        
        log_success "Multi-project deployment completed!"
        log_info "Deployment path: $deployment_path"
        
        # Show summary
        echo
        echo "=== Deployment Summary ==="
        terraform -chdir="$deployment_path" output summary
    else
        log_error "Deployment failed"
        exit 1
    fi
    
    # Cleanup temp files
    rm -f "$projects_json"
}

# Run main function
main "$@"