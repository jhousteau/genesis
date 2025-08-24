#!/usr/bin/env bash

# GCP Bootstrap Deployer - Initial Setup Script
# This script sets up the initial GCP infrastructure for the bootstrap deployer

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
LOG_FILE="${PROJECT_ROOT}/logs/bootstrap-${TIMESTAMP}.log"

# Default values
DEFAULT_REGION="us-central1"
DEFAULT_ZONE="us-central1-a"
REQUIRED_APIS=(
    "cloudresourcemanager.googleapis.com"
    "compute.googleapis.com"
    "iam.googleapis.com"
    "iamcredentials.googleapis.com"
    "storage.googleapis.com"
    "cloudkms.googleapis.com"
    "secretmanager.googleapis.com"
    "cloudbuild.googleapis.com"
    "artifactregistry.googleapis.com"
    "container.googleapis.com"
    "run.googleapis.com"
    "cloudfunctions.googleapis.com"
    "serviceusage.googleapis.com"
    "cloudidentity.googleapis.com"
    "sts.googleapis.com"
)

# Functions
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_message() {
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    local missing_tools=()

    # Check for required tools
    for tool in gcloud terraform jq; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
            print_error "$tool is not installed"
        else
            print_success "$tool is installed ($(command -v "$tool"))"
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo ""
        print_error "Missing required tools: ${missing_tools[*]}"
        echo ""
        echo "Installation instructions:"
        echo "  gcloud: https://cloud.google.com/sdk/docs/install"
        echo "  terraform: https://www.terraform.io/downloads"
        echo "  jq: https://stedolan.github.io/jq/download/"
        exit 1
    fi

    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        print_error "Not authenticated with gcloud"
        echo "Run: gcloud auth login"
        exit 1
    else
        local account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
        print_success "Authenticated as: $account"
    fi

    echo ""
}

select_or_create_project() {
    print_header "Project Configuration"

    echo "Choose an option:"
    echo "1) Use existing project"
    echo "2) Create new project"
    read -p "Enter choice (1 or 2): " choice

    case $choice in
        1)
            # List existing projects
            echo ""
            print_info "Available projects:"
            gcloud projects list --format="table(projectId,name,projectNumber)"
            echo ""
            read -p "Enter project ID: " PROJECT_ID

            # Verify project exists
            if ! gcloud projects describe "$PROJECT_ID" &> /dev/null; then
                print_error "Project $PROJECT_ID not found"
                exit 1
            fi
            ;;
        2)
            read -p "Enter new project ID (lowercase, numbers, hyphens only): " PROJECT_ID
            read -p "Enter project name: " PROJECT_NAME
            read -p "Enter billing account ID (or press Enter to set later): " BILLING_ACCOUNT

            print_info "Creating project $PROJECT_ID..."
            if gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME"; then
                print_success "Project created successfully"

                if [ -n "$BILLING_ACCOUNT" ]; then
                    print_info "Linking billing account..."
                    gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"
                    print_success "Billing account linked"
                else
                    print_warning "No billing account linked. Some services may not be available."
                fi
            else
                print_error "Failed to create project"
                exit 1
            fi
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac

    # Set the project
    gcloud config set project "$PROJECT_ID"
    print_success "Project set to: $PROJECT_ID"

    echo ""
}

setup_project_defaults() {
    print_header "Setting Project Defaults"

    read -p "Enter default region (default: $DEFAULT_REGION): " REGION
    REGION=${REGION:-$DEFAULT_REGION}

    read -p "Enter default zone (default: $DEFAULT_ZONE): " ZONE
    ZONE=${ZONE:-$DEFAULT_ZONE}

    gcloud config set compute/region "$REGION"
    gcloud config set compute/zone "$ZONE"

    print_success "Default region set to: $REGION"
    print_success "Default zone set to: $ZONE"

    echo ""
}

enable_apis() {
    print_header "Enabling Required APIs"

    for api in "${REQUIRED_APIS[@]}"; do
        print_info "Enabling $api..."
        if gcloud services enable "$api" --project="$PROJECT_ID" 2>&1 | tee -a "$LOG_FILE"; then
            print_success "$api enabled"
        else
            print_warning "Failed to enable $api (may already be enabled)"
        fi
    done

    echo ""
}

create_terraform_backend() {
    print_header "Creating Terraform Backend"

    local bucket_name="terraform-state-${PROJECT_ID}"

    print_info "Creating GCS bucket: $bucket_name"

    if gsutil ls -b "gs://$bucket_name" &> /dev/null; then
        print_warning "Bucket already exists: $bucket_name"
    else
        gsutil mb -p "$PROJECT_ID" -l "$REGION" -b on "gs://$bucket_name"

        # Enable versioning
        gsutil versioning set on "gs://$bucket_name"

        # Set lifecycle policy
        cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "isLive": false
        }
      }
    ]
  }
}
EOF
        gsutil lifecycle set /tmp/lifecycle.json "gs://$bucket_name"
        rm /tmp/lifecycle.json

        print_success "Terraform backend bucket created and configured"
    fi

    echo ""
}

setup_workload_identity_federation() {
    print_header "Setting up Workload Identity Federation"

    echo "Select CI/CD platform:"
    echo "1) GitHub Actions"
    echo "2) GitLab CI"
    echo "3) Both"
    echo "4) Skip"
    read -p "Enter choice (1-4): " wif_choice

    case $wif_choice in
        1|3)
            setup_github_wif
            ;;
    esac

    case $wif_choice in
        2|3)
            setup_gitlab_wif
            ;;
    esac

    if [ "$wif_choice" != "4" ]; then
        print_success "Workload Identity Federation configured"
    fi

    echo ""
}

setup_github_wif() {
    print_info "Configuring GitHub Workload Identity Federation"

    read -p "Enter GitHub organization/username: " GITHUB_ORG
    read -p "Enter GitHub repository name: " GITHUB_REPO

    local pool_id="github-pool"
    local provider_id="github-provider"
    local sa_name="github-actions-sa"
    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"

    # Create workload identity pool
    print_info "Creating workload identity pool..."
    gcloud iam workload-identity-pools create "$pool_id" \
        --location="global" \
        --display-name="GitHub Actions Pool" \
        --description="Workload Identity Pool for GitHub Actions"

    # Create workload identity provider
    print_info "Creating workload identity provider..."
    gcloud iam workload-identity-pools providers create-oidc "$provider_id" \
        --location="global" \
        --workload-identity-pool="$pool_id" \
        --display-name="GitHub Provider" \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
        --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'" \
        --issuer-uri="https://token.actions.githubusercontent.com"

    # Create service account
    print_info "Creating service account..."
    gcloud iam service-accounts create "$sa_name" \
        --display-name="GitHub Actions Service Account" \
        --description="Service account for GitHub Actions CI/CD"

    # Grant permissions
    print_info "Granting permissions..."
    for role in "roles/editor" "roles/storage.admin" "roles/resourcemanager.projectIamAdmin"; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:${sa_email}" \
            --role="$role"
    done

    # Allow impersonation
    gcloud iam service-accounts add-iam-policy-binding "$sa_email" \
        --role="roles/iam.workloadIdentityUser" \
        --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/${pool_id}/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}"

    # Output configuration
    echo ""
    print_success "GitHub WIF Configuration:"
    echo "  WIF_PROVIDER: projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/${pool_id}/providers/${provider_id}"
    echo "  WIF_SERVICE_ACCOUNT: ${sa_email}"
    echo ""
}

setup_gitlab_wif() {
    print_info "Configuring GitLab Workload Identity Federation"

    read -p "Enter GitLab instance URL (default: https://gitlab.com): " GITLAB_URL
    GITLAB_URL=${GITLAB_URL:-"https://gitlab.com"}
    read -p "Enter GitLab project path (e.g., group/project): " GITLAB_PROJECT

    local pool_id="gitlab-pool"
    local provider_id="gitlab-provider"
    local sa_name="gitlab-ci-sa"
    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"

    # Create workload identity pool
    print_info "Creating workload identity pool..."
    gcloud iam workload-identity-pools create "$pool_id" \
        --location="global" \
        --display-name="GitLab CI Pool" \
        --description="Workload Identity Pool for GitLab CI"

    # Create workload identity provider
    print_info "Creating workload identity provider..."
    gcloud iam workload-identity-pools providers create-oidc "$provider_id" \
        --location="global" \
        --workload-identity-pool="$pool_id" \
        --display-name="GitLab Provider" \
        --attribute-mapping="google.subject=assertion.sub,attribute.project_path=assertion.project_path,attribute.ref=assertion.ref,attribute.ref_type=assertion.ref_type" \
        --attribute-condition="assertion.project_path == '${GITLAB_PROJECT}'" \
        --issuer-uri="$GITLAB_URL"

    # Create service account
    print_info "Creating service account..."
    gcloud iam service-accounts create "$sa_name" \
        --display-name="GitLab CI Service Account" \
        --description="Service account for GitLab CI/CD"

    # Grant permissions
    print_info "Granting permissions..."
    for role in "roles/editor" "roles/storage.admin" "roles/resourcemanager.projectIamAdmin"; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:${sa_email}" \
            --role="$role"
    done

    # Allow impersonation
    gcloud iam service-accounts add-iam-policy-binding "$sa_email" \
        --role="roles/iam.workloadIdentityUser" \
        --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/${pool_id}/attribute.project_path/${GITLAB_PROJECT}"

    # Output configuration
    echo ""
    print_success "GitLab WIF Configuration:"
    echo "  WIF_PROVIDER_GITLAB: projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/${pool_id}/providers/${provider_id}"
    echo "  WIF_SERVICE_ACCOUNT_GITLAB: ${sa_email}"
    echo ""
}

initialize_terraform() {
    print_header "Initializing Terraform"

    cd "$PROJECT_ROOT"

    print_info "Running terraform init..."
    if terraform init \
        -backend-config="bucket=terraform-state-${PROJECT_ID}" \
        -backend-config="prefix=bootstrap"; then
        print_success "Terraform initialized successfully"
    else
        print_error "Terraform initialization failed"
        exit 1
    fi

    echo ""
}

create_example_tfvars() {
    print_header "Creating Example Configuration Files"

    mkdir -p "${PROJECT_ROOT}/environments"

    for env in dev staging prod; do
        cat > "${PROJECT_ROOT}/environments/${env}.tfvars.example" <<EOF
# ${env} environment configuration
project_id = "${PROJECT_ID}"
region     = "${REGION}"
zone       = "${ZONE}"

# Environment-specific settings
environment = "${env}"
labels = {
  environment = "${env}"
  managed_by  = "terraform"
  team        = "platform"
}

# Network configuration
network_name = "vpc-${env}"
subnet_cidr  = "10.${env == 'dev' ? '0' : env == 'staging' ? '1' : '2'}.0.0/16"

# Additional environment-specific variables
# ...
EOF
        print_success "Created environments/${env}.tfvars.example"
    done

    echo ""
}

generate_summary() {
    print_header "Bootstrap Summary"

    cat > "${PROJECT_ROOT}/bootstrap-summary.md" <<EOF
# GCP Bootstrap Deployer - Setup Summary

## Project Information
- **Project ID**: ${PROJECT_ID}
- **Region**: ${REGION}
- **Zone**: ${ZONE}
- **Timestamp**: $(date)

## Terraform Backend
- **Bucket**: terraform-state-${PROJECT_ID}
- **Prefix**: bootstrap

## Enabled APIs
$(printf '%s\n' "${REQUIRED_APIS[@]}" | sed 's/^/- /')

## Next Steps
1. Review and customize the environment configuration files in \`environments/\`
2. Copy \`.tfvars.example\` files to \`.tfvars\` and update values
3. Run \`terraform plan\` to review the infrastructure changes
4. Run \`terraform apply\` to create the infrastructure

## Useful Commands
\`\`\`bash
# Validate configuration
./scripts/validate-config.sh

# Plan changes
terraform plan -var-file="environments/dev.tfvars"

# Apply changes
terraform apply -var-file="environments/dev.tfvars"

# Clean up resources
./scripts/cleanup.sh
\`\`\`

## Logs
Bootstrap log: logs/bootstrap-${TIMESTAMP}.log
EOF

    print_success "Summary saved to bootstrap-summary.md"
    echo ""
    cat "${PROJECT_ROOT}/bootstrap-summary.md"
}

# Main execution
main() {
    print_header "GCP Bootstrap Deployer - Initial Setup"
    echo ""

    log_message "Starting bootstrap process"

    check_prerequisites
    select_or_create_project
    setup_project_defaults
    enable_apis
    create_terraform_backend
    setup_workload_identity_federation
    initialize_terraform
    create_example_tfvars
    generate_summary

    log_message "Bootstrap process completed successfully"

    print_header "Setup Complete!"
    print_success "Your GCP bootstrap environment is ready."
    print_info "Review bootstrap-summary.md for next steps."
}

# Run main function
main "$@"
