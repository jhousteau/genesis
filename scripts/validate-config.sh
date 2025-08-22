#!/usr/bin/env bash

# GCP Bootstrap Deployer - Configuration Validation Script
# This script validates the Terraform configuration and GCP setup

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
VALIDATION_REPORT="${PROJECT_ROOT}/validation-report-${TIMESTAMP}.md"

# Validation counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Functions
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNING_CHECKS++))
    ((TOTAL_CHECKS++))
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

validate_prerequisites() {
    print_header "Validating Prerequisites"
    
    check_command "gcloud"
    check_command "terraform"
    check_command "jq"
    check_command "gsutil"
    
    # Check gcloud authentication
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        local account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
        print_success "Authenticated with gcloud as: $account"
    else
        print_error "Not authenticated with gcloud"
    fi
    
    # Check Terraform version
    local tf_version=$(terraform version -json | jq -r '.terraform_version')
    if [[ "$tf_version" =~ ^1\.[5-9] ]]; then
        print_success "Terraform version $tf_version meets requirements (>= 1.5)"
    else
        print_error "Terraform version $tf_version does not meet requirements (>= 1.5)"
    fi
    
    echo ""
}

validate_gcp_project() {
    print_header "Validating GCP Project"
    
    # Get current project
    local project_id=$(gcloud config get-value project 2>/dev/null)
    
    if [ -z "$project_id" ]; then
        print_error "No GCP project configured"
        return 1
    fi
    
    print_info "Checking project: $project_id"
    
    # Check if project exists
    if gcloud projects describe "$project_id" &> /dev/null; then
        print_success "Project $project_id exists and is accessible"
    else
        print_error "Project $project_id not found or not accessible"
        return 1
    fi
    
    # Check billing
    local billing_enabled=$(gcloud billing projects describe "$project_id" --format="value(billingEnabled)" 2>/dev/null || echo "false")
    if [ "$billing_enabled" == "True" ]; then
        print_success "Billing is enabled for project"
    else
        print_warning "Billing is not enabled - some services may not work"
    fi
    
    # Check project quotas
    print_info "Checking key quotas..."
    local cpu_quota=$(gcloud compute project-info describe --format="value(quotas[name=CPUS].limit)" 2>/dev/null || echo "0")
    if [ "$cpu_quota" != "0" ]; then
        print_success "CPU quota: $cpu_quota"
    else
        print_warning "Unable to determine CPU quota"
    fi
    
    echo ""
}

validate_apis() {
    print_header "Validating Required APIs"
    
    local project_id=$(gcloud config get-value project 2>/dev/null)
    local required_apis=(
        "cloudresourcemanager.googleapis.com"
        "compute.googleapis.com"
        "iam.googleapis.com"
        "storage.googleapis.com"
        "cloudkms.googleapis.com"
        "secretmanager.googleapis.com"
        "cloudbuild.googleapis.com"
        "serviceusage.googleapis.com"
    )
    
    for api in "${required_apis[@]}"; do
        if gcloud services list --enabled --filter="name:$api" --format="value(name)" 2>/dev/null | grep -q "$api"; then
            print_success "$api is enabled"
        else
            print_error "$api is not enabled"
        fi
    done
    
    echo ""
}

validate_terraform_backend() {
    print_header "Validating Terraform Backend"
    
    local project_id=$(gcloud config get-value project 2>/dev/null)
    local bucket_name="terraform-state-${project_id}"
    
    # Check if bucket exists
    if gsutil ls -b "gs://$bucket_name" &> /dev/null; then
        print_success "Terraform state bucket exists: $bucket_name"
        
        # Check versioning
        local versioning=$(gsutil versioning get "gs://$bucket_name" | grep -oP '(?<=Enabled: )\w+')
        if [ "$versioning" == "True" ]; then
            print_success "Bucket versioning is enabled"
        else
            print_warning "Bucket versioning is not enabled"
        fi
        
        # Check lifecycle
        if gsutil lifecycle get "gs://$bucket_name" 2>/dev/null | grep -q '"action"'; then
            print_success "Bucket lifecycle policy is configured"
        else
            print_warning "No bucket lifecycle policy configured"
        fi
    else
        print_error "Terraform state bucket not found: $bucket_name"
    fi
    
    echo ""
}

validate_terraform_configuration() {
    print_header "Validating Terraform Configuration"
    
    cd "$PROJECT_ROOT"
    
    # Check if terraform is initialized
    if [ -d ".terraform" ]; then
        print_success "Terraform is initialized"
    else
        print_warning "Terraform not initialized - run 'terraform init'"
    fi
    
    # Validate format
    print_info "Checking Terraform formatting..."
    if terraform fmt -check -recursive &> /dev/null; then
        print_success "Terraform files are properly formatted"
    else
        print_warning "Some Terraform files need formatting - run 'terraform fmt -recursive'"
    fi
    
    # Validate configuration
    print_info "Validating Terraform configuration..."
    if terraform validate &> /dev/null; then
        print_success "Terraform configuration is valid"
    else
        print_error "Terraform configuration has errors - run 'terraform validate' for details"
    fi
    
    # Check for .tfvars files
    if ls environments/*.tfvars 2>/dev/null | grep -q ".tfvars$"; then
        print_success "Environment tfvars files found"
        for file in environments/*.tfvars; do
            print_info "  - $file"
        done
    else
        print_warning "No .tfvars files found in environments/ directory"
    fi
    
    echo ""
}

validate_workload_identity() {
    print_header "Validating Workload Identity Federation"
    
    local project_id=$(gcloud config get-value project 2>/dev/null)
    local project_number=$(gcloud projects describe "$project_id" --format="value(projectNumber)" 2>/dev/null)
    
    # Check for workload identity pools
    local pools=$(gcloud iam workload-identity-pools list --location=global --format="value(name)" 2>/dev/null)
    
    if [ -n "$pools" ]; then
        print_success "Workload identity pools found:"
        while IFS= read -r pool; do
            print_info "  - $pool"
            
            # Check providers for each pool
            local providers=$(gcloud iam workload-identity-pools providers list \
                --workload-identity-pool="$pool" \
                --location=global \
                --format="value(name)" 2>/dev/null)
            
            if [ -n "$providers" ]; then
                while IFS= read -r provider; do
                    print_info "    └─ Provider: $provider"
                done <<< "$providers"
            fi
        done <<< "$pools"
    else
        print_warning "No workload identity pools configured"
    fi
    
    # Check for service accounts
    local service_accounts=$(gcloud iam service-accounts list --format="value(email)" --filter="email:*-sa@${project_id}.iam.gserviceaccount.com" 2>/dev/null)
    
    if [ -n "$service_accounts" ]; then
        print_success "CI/CD service accounts found:"
        while IFS= read -r sa; do
            print_info "  - $sa"
        done <<< "$service_accounts"
    else
        print_warning "No CI/CD service accounts found"
    fi
    
    echo ""
}

validate_iam_permissions() {
    print_header "Validating IAM Permissions"
    
    local project_id=$(gcloud config get-value project 2>/dev/null)
    local current_user=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    
    print_info "Checking permissions for: $current_user"
    
    # List of required permissions
    local required_permissions=(
        "resourcemanager.projects.get"
        "storage.buckets.create"
        "storage.buckets.get"
        "iam.serviceAccounts.create"
        "iam.roles.create"
        "compute.networks.create"
    )
    
    local missing_permissions=()
    
    for permission in "${required_permissions[@]}"; do
        if gcloud projects get-iam-policy "$project_id" --flatten="bindings[].members" --filter="bindings.members:$current_user" --format="value(bindings.role)" 2>/dev/null | xargs -I {} gcloud iam roles describe {} --format="value(includedPermissions)" 2>/dev/null | grep -q "$permission"; then
            print_success "Has permission: $permission"
        else
            # Try to test the permission directly
            if gcloud alpha iam policies test-iam-policy --member="user:$current_user" --resource="projects/$project_id" --permission="$permission" &> /dev/null; then
                print_success "Has permission: $permission"
            else
                print_warning "May lack permission: $permission"
                missing_permissions+=("$permission")
            fi
        fi
    done
    
    if [ ${#missing_permissions[@]} -gt 0 ]; then
        print_warning "Some permissions may be missing. Ensure you have appropriate roles."
    fi
    
    echo ""
}

run_security_checks() {
    print_header "Running Security Checks"
    
    local project_id=$(gcloud config get-value project 2>/dev/null)
    
    # Check for default service account usage
    local default_sa_usage=$(gcloud iam service-accounts list --filter="email:*compute@developer.gserviceaccount.com" --format="value(email)" 2>/dev/null)
    if [ -n "$default_sa_usage" ]; then
        print_warning "Default compute service account is in use - consider using custom service accounts"
    else
        print_success "Not using default compute service account"
    fi
    
    # Check for overly permissive IAM bindings
    local broad_bindings=$(gcloud projects get-iam-policy "$project_id" --flatten="bindings[].members" --filter="bindings.members:allUsers OR bindings.members:allAuthenticatedUsers" --format="value(bindings.role)" 2>/dev/null)
    if [ -n "$broad_bindings" ]; then
        print_warning "Found overly permissive IAM bindings (allUsers or allAuthenticatedUsers)"
    else
        print_success "No overly permissive IAM bindings found"
    fi
    
    # Check if Cloud Security Command Center is enabled
    if gcloud services list --enabled --filter="name:securitycenter.googleapis.com" --format="value(name)" 2>/dev/null | grep -q "securitycenter"; then
        print_success "Security Command Center is enabled"
    else
        print_warning "Security Command Center is not enabled - consider enabling for security insights"
    fi
    
    # Check for encryption
    print_info "Checking encryption settings..."
    local kms_enabled=$(gcloud services list --enabled --filter="name:cloudkms.googleapis.com" --format="value(name)" 2>/dev/null)
    if [ -n "$kms_enabled" ]; then
        print_success "Cloud KMS is enabled for encryption management"
    else
        print_warning "Cloud KMS is not enabled - using default encryption"
    fi
    
    echo ""
}

generate_report() {
    print_header "Generating Validation Report"
    
    cat > "$VALIDATION_REPORT" <<EOF
# GCP Bootstrap Validation Report

**Generated**: $(date)
**Project**: $(gcloud config get-value project 2>/dev/null)

## Summary

- **Total Checks**: $TOTAL_CHECKS
- **Passed**: $PASSED_CHECKS ✓
- **Failed**: $FAILED_CHECKS ✗
- **Warnings**: $WARNING_CHECKS ⚠

## Validation Results

### Prerequisites
$([ $FAILED_CHECKS -eq 0 ] && echo "✓ All prerequisites met" || echo "✗ Some prerequisites missing")

### GCP Configuration
$([ $FAILED_CHECKS -eq 0 ] && echo "✓ GCP project properly configured" || echo "✗ GCP configuration issues found")

### Terraform Setup
$([ -d ".terraform" ] && echo "✓ Terraform initialized" || echo "⚠ Terraform not initialized")

### Security
$([ $WARNING_CHECKS -eq 0 ] && echo "✓ No security warnings" || echo "⚠ Security warnings present")

## Recommendations

EOF
    
    if [ $FAILED_CHECKS -gt 0 ]; then
        cat >> "$VALIDATION_REPORT" <<EOF
### Critical Issues to Address
- Review and fix all failed checks (marked with ✗)
- Ensure all required APIs are enabled
- Verify IAM permissions are correctly configured

EOF
    fi
    
    if [ $WARNING_CHECKS -gt 0 ]; then
        cat >> "$VALIDATION_REPORT" <<EOF
### Warnings to Review
- Consider addressing warning items for better security and reliability
- Enable additional monitoring and security services
- Review IAM bindings for least privilege

EOF
    fi
    
    cat >> "$VALIDATION_REPORT" <<EOF
## Next Steps

1. Address any critical issues identified
2. Review warnings and implement recommendations
3. Run \`terraform plan\` to preview infrastructure changes
4. Execute \`terraform apply\` when ready to deploy

---
*Report generated by validate-config.sh*
EOF
    
    print_success "Validation report saved to: $VALIDATION_REPORT"
}

# Main execution
main() {
    print_header "GCP Bootstrap Configuration Validator"
    echo ""
    
    validate_prerequisites
    validate_gcp_project
    validate_apis
    validate_terraform_backend
    validate_terraform_configuration
    validate_workload_identity
    validate_iam_permissions
    run_security_checks
    generate_report
    
    echo ""
    print_header "Validation Complete"
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        print_success "All critical checks passed!"
    else
        print_error "$FAILED_CHECKS critical issues found - review the report"
    fi
    
    if [ $WARNING_CHECKS -gt 0 ]; then
        print_warning "$WARNING_CHECKS warnings to review"
    fi
    
    print_info "Full report: $VALIDATION_REPORT"
}

# Run main function
main "$@"