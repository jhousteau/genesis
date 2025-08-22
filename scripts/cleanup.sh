#!/usr/bin/env bash

# GCP Bootstrap Deployer - Cleanup Script
# This script safely tears down the GCP infrastructure created by the bootstrap deployer

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
CLEANUP_LOG="${PROJECT_ROOT}/logs/cleanup-${TIMESTAMP}.log"

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
    mkdir -p "$(dirname "$CLEANUP_LOG")"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$CLEANUP_LOG"
}

confirm_action() {
    local message="$1"
    local response
    
    echo -e "${YELLOW}${message}${NC}"
    read -p "Type 'yes' to confirm: " response
    
    if [ "$response" != "yes" ]; then
        print_warning "Action cancelled"
        return 1
    fi
    return 0
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check for required tools
    for tool in gcloud terraform jq gsutil; do
        if ! command -v "$tool" &> /dev/null; then
            print_error "$tool is not installed"
            exit 1
        else
            print_success "$tool is available"
        fi
    done
    
    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        print_error "Not authenticated with gcloud"
        exit 1
    else
        local account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
        print_success "Authenticated as: $account"
    fi
    
    echo ""
}

get_project_info() {
    print_header "Project Information"
    
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    
    if [ -z "$PROJECT_ID" ]; then
        print_error "No GCP project configured"
        read -p "Enter project ID to clean up: " PROJECT_ID
        
        if ! gcloud projects describe "$PROJECT_ID" &> /dev/null; then
            print_error "Project $PROJECT_ID not found"
            exit 1
        fi
        
        gcloud config set project "$PROJECT_ID"
    fi
    
    print_info "Project ID: $PROJECT_ID"
    
    # Get project details
    local project_name=$(gcloud projects describe "$PROJECT_ID" --format="value(name)")
    local project_number=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
    
    print_info "Project Name: $project_name"
    print_info "Project Number: $project_number"
    
    echo ""
}

backup_terraform_state() {
    print_header "Backing Up Terraform State"
    
    local bucket_name="terraform-state-${PROJECT_ID}"
    local backup_dir="${PROJECT_ROOT}/backups/${TIMESTAMP}"
    
    mkdir -p "$backup_dir"
    
    # Check if bucket exists
    if gsutil ls -b "gs://$bucket_name" &> /dev/null; then
        print_info "Downloading Terraform state files..."
        
        if gsutil -m cp -r "gs://$bucket_name/*" "$backup_dir/" 2>&1 | tee -a "$CLEANUP_LOG"; then
            print_success "Terraform state backed up to: $backup_dir"
        else
            print_warning "Some files may not have been backed up"
        fi
    else
        print_warning "Terraform state bucket not found"
    fi
    
    # Also backup local terraform files
    if [ -f "${PROJECT_ROOT}/terraform.tfstate" ]; then
        cp "${PROJECT_ROOT}/terraform.tfstate" "$backup_dir/"
        print_success "Local terraform.tfstate backed up"
    fi
    
    if [ -f "${PROJECT_ROOT}/terraform.tfstate.backup" ]; then
        cp "${PROJECT_ROOT}/terraform.tfstate.backup" "$backup_dir/"
        print_success "Local terraform.tfstate.backup backed up"
    fi
    
    echo ""
}

destroy_terraform_resources() {
    print_header "Destroying Terraform-Managed Resources"
    
    cd "$PROJECT_ROOT"
    
    # Check if terraform is initialized
    if [ ! -d ".terraform" ]; then
        print_warning "Terraform not initialized, attempting to initialize..."
        
        if terraform init \
            -backend-config="bucket=terraform-state-${PROJECT_ID}" \
            -backend-config="prefix=bootstrap"; then
            print_success "Terraform initialized"
        else
            print_error "Failed to initialize Terraform"
            return 1
        fi
    fi
    
    # List workspaces
    print_info "Available Terraform workspaces:"
    terraform workspace list
    
    # Destroy resources in each workspace
    local workspaces=$(terraform workspace list | grep -v default | sed 's/[* ]//g')
    
    for workspace in $workspaces; do
        print_info "Processing workspace: $workspace"
        
        terraform workspace select "$workspace"
        
        # Check if there are resources to destroy
        local resource_count=$(terraform state list 2>/dev/null | wc -l)
        
        if [ "$resource_count" -gt 0 ]; then
            print_warning "Found $resource_count resources in workspace $workspace"
            
            if confirm_action "Destroy all resources in workspace $workspace?"; then
                print_info "Running terraform destroy for workspace $workspace..."
                
                # Try to find the appropriate tfvars file
                local tfvars_file="${PROJECT_ROOT}/environments/${workspace}.tfvars"
                
                if [ -f "$tfvars_file" ]; then
                    terraform destroy -var-file="$tfvars_file" -auto-approve 2>&1 | tee -a "$CLEANUP_LOG"
                else
                    terraform destroy -auto-approve 2>&1 | tee -a "$CLEANUP_LOG"
                fi
                
                print_success "Resources destroyed in workspace $workspace"
            else
                print_warning "Skipping workspace $workspace"
            fi
        else
            print_info "No resources found in workspace $workspace"
        fi
    done
    
    # Switch back to default workspace
    terraform workspace select default
    
    echo ""
}

cleanup_workload_identity() {
    print_header "Cleaning Up Workload Identity Federation"
    
    local project_number=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
    
    # List and delete workload identity pools
    print_info "Checking for workload identity pools..."
    
    local pools=$(gcloud iam workload-identity-pools list --location=global --format="value(name)" 2>/dev/null)
    
    if [ -n "$pools" ]; then
        while IFS= read -r pool; do
            print_info "Found pool: $pool"
            
            # Delete providers first
            local providers=$(gcloud iam workload-identity-pools providers list \
                --workload-identity-pool="$pool" \
                --location=global \
                --format="value(name)" 2>/dev/null)
            
            if [ -n "$providers" ]; then
                while IFS= read -r provider; do
                    if confirm_action "Delete provider $provider?"; then
                        gcloud iam workload-identity-pools providers delete "$provider" \
                            --workload-identity-pool="$pool" \
                            --location=global \
                            --quiet
                        print_success "Deleted provider: $provider"
                    fi
                done <<< "$providers"
            fi
            
            # Delete the pool
            if confirm_action "Delete workload identity pool $pool?"; then
                gcloud iam workload-identity-pools delete "$pool" \
                    --location=global \
                    --quiet
                print_success "Deleted pool: $pool"
            fi
        done <<< "$pools"
    else
        print_info "No workload identity pools found"
    fi
    
    # Clean up service accounts
    print_info "Checking for CI/CD service accounts..."
    
    local service_accounts=$(gcloud iam service-accounts list \
        --format="value(email)" \
        --filter="email:*-sa@${PROJECT_ID}.iam.gserviceaccount.com OR email:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com OR email:gitlab-ci-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
        2>/dev/null)
    
    if [ -n "$service_accounts" ]; then
        while IFS= read -r sa; do
            if confirm_action "Delete service account $sa?"; then
                gcloud iam service-accounts delete "$sa" --quiet
                print_success "Deleted service account: $sa"
            fi
        done <<< "$service_accounts"
    else
        print_info "No CI/CD service accounts found"
    fi
    
    echo ""
}

cleanup_terraform_backend() {
    print_header "Cleaning Up Terraform Backend"
    
    local bucket_name="terraform-state-${PROJECT_ID}"
    
    if gsutil ls -b "gs://$bucket_name" &> /dev/null; then
        print_warning "Found Terraform state bucket: $bucket_name"
        
        # Check if bucket is empty
        local object_count=$(gsutil ls "gs://$bucket_name/**" 2>/dev/null | wc -l)
        
        if [ "$object_count" -gt 0 ]; then
            print_warning "Bucket contains $object_count objects"
            
            if confirm_action "Delete all objects and remove bucket $bucket_name?"; then
                print_info "Removing all objects from bucket..."
                gsutil -m rm -r "gs://$bucket_name/**" 2>&1 | tee -a "$CLEANUP_LOG"
                
                print_info "Removing bucket..."
                gsutil rb "gs://$bucket_name" 2>&1 | tee -a "$CLEANUP_LOG"
                
                print_success "Terraform backend bucket removed"
            else
                print_warning "Bucket retained: $bucket_name"
            fi
        else
            if confirm_action "Remove empty bucket $bucket_name?"; then
                gsutil rb "gs://$bucket_name"
                print_success "Empty bucket removed"
            fi
        fi
    else
        print_info "Terraform backend bucket not found"
    fi
    
    echo ""
}

disable_apis() {
    print_header "Disabling APIs (Optional)"
    
    print_warning "Disabling APIs may affect other resources in the project"
    
    if confirm_action "Do you want to disable project APIs?"; then
        local apis_to_disable=(
            "cloudfunctions.googleapis.com"
            "run.googleapis.com"
            "container.googleapis.com"
            "artifactregistry.googleapis.com"
            "cloudbuild.googleapis.com"
            "secretmanager.googleapis.com"
            "cloudkms.googleapis.com"
        )
        
        for api in "${apis_to_disable[@]}"; do
            print_info "Disabling $api..."
            if gcloud services disable "$api" --force 2>&1 | tee -a "$CLEANUP_LOG"; then
                print_success "$api disabled"
            else
                print_warning "Could not disable $api (may have dependencies)"
            fi
        done
    else
        print_info "APIs retained"
    fi
    
    echo ""
}

cleanup_local_files() {
    print_header "Cleaning Up Local Files"
    
    cd "$PROJECT_ROOT"
    
    # Remove .terraform directory
    if [ -d ".terraform" ]; then
        if confirm_action "Remove .terraform directory?"; then
            rm -rf .terraform
            print_success "Removed .terraform directory"
        fi
    fi
    
    # Remove terraform lock file
    if [ -f ".terraform.lock.hcl" ]; then
        if confirm_action "Remove .terraform.lock.hcl?"; then
            rm -f .terraform.lock.hcl
            print_success "Removed .terraform.lock.hcl"
        fi
    fi
    
    # Remove local state files
    if [ -f "terraform.tfstate" ] || [ -f "terraform.tfstate.backup" ]; then
        print_warning "Local state files found (should be backed up already)"
        if confirm_action "Remove local terraform state files?"; then
            rm -f terraform.tfstate terraform.tfstate.backup
            print_success "Removed local state files"
        fi
    fi
    
    # Remove tfplan files
    if ls tfplan* 2>/dev/null | grep -q tfplan; then
        if confirm_action "Remove terraform plan files?"; then
            rm -f tfplan*
            print_success "Removed plan files"
        fi
    fi
    
    echo ""
}

generate_cleanup_report() {
    print_header "Generating Cleanup Report"
    
    local report_file="${PROJECT_ROOT}/cleanup-report-${TIMESTAMP}.md"
    
    cat > "$report_file" <<EOF
# GCP Bootstrap Cleanup Report

## Cleanup Summary
- **Project ID**: ${PROJECT_ID}
- **Timestamp**: $(date)
- **Initiated by**: $(gcloud auth list --filter=status:ACTIVE --format="value(account)")

## Actions Performed

### Backups Created
- Location: ${PROJECT_ROOT}/backups/${TIMESTAMP}
- Terraform state files backed up

### Resources Removed
- Terraform-managed infrastructure destroyed
- Workload Identity Federation configurations removed
- Service accounts deleted
- Terraform backend bucket cleaned

### Retained Resources
- Project: ${PROJECT_ID} (not deleted)
- Core APIs (compute, storage, iam)
- Backup files in backups/ directory

## Next Steps

If you want to completely remove the project:
\`\`\`bash
gcloud projects delete ${PROJECT_ID}
\`\`\`

To rebuild the infrastructure:
\`\`\`bash
./scripts/bootstrap.sh
\`\`\`

## Logs
- Cleanup log: logs/cleanup-${TIMESTAMP}.log
- Backup location: backups/${TIMESTAMP}/

---
*Report generated by cleanup.sh*
EOF
    
    print_success "Cleanup report saved to: $report_file"
    
    echo ""
    cat "$report_file"
}

final_confirmation() {
    print_header "Final Cleanup Option"
    
    print_warning "The project itself has not been deleted: $PROJECT_ID"
    echo ""
    echo "To completely delete the project and all remaining resources:"
    echo "  gcloud projects delete $PROJECT_ID"
    echo ""
    
    if confirm_action "Do you want to DELETE THE ENTIRE PROJECT now?"; then
        print_warning "This will permanently delete ALL resources in the project"
        print_warning "This action cannot be undone!"
        
        if confirm_action "Are you absolutely sure you want to delete project $PROJECT_ID?"; then
            print_info "Deleting project $PROJECT_ID..."
            if gcloud projects delete "$PROJECT_ID" --quiet; then
                print_success "Project $PROJECT_ID has been deleted"
            else
                print_error "Failed to delete project"
            fi
        else
            print_info "Project deletion cancelled"
        fi
    else
        print_info "Project retained: $PROJECT_ID"
    fi
}

# Main execution
main() {
    print_header "GCP Bootstrap Deployer - Cleanup"
    echo ""
    
    print_warning "This script will remove infrastructure created by the bootstrap deployer"
    print_warning "Make sure you have backups of any important data!"
    echo ""
    
    if ! confirm_action "Do you want to proceed with cleanup?"; then
        print_info "Cleanup cancelled"
        exit 0
    fi
    
    log_message "Starting cleanup process"
    
    check_prerequisites
    get_project_info
    backup_terraform_state
    destroy_terraform_resources
    cleanup_workload_identity
    cleanup_terraform_backend
    disable_apis
    cleanup_local_files
    generate_cleanup_report
    final_confirmation
    
    log_message "Cleanup process completed"
    
    print_header "Cleanup Complete"
    print_success "Infrastructure cleanup finished"
    print_info "Check the cleanup report for details"
}

# Run main function
main "$@"