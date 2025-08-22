#!/usr/bin/env bash
# Service Account Management - Comprehensive SA lifecycle management
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Handles creation, rotation, scoping, and lifecycle of service accounts

set -euo pipefail

# Script metadata
SA_MANAGER_VERSION="2.0.0"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $*${NC}"; }
log_success() { echo -e "${GREEN}✅ $*${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $*${NC}"; }
log_error() { echo -e "${RED}❌ $*${NC}" >&2; }
log_step() { echo -e "${PURPLE}🔄 $*${NC}"; }

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "════════════════════════════════════════════════════════════"
    echo "🔑 SERVICE ACCOUNT MANAGER v${SA_MANAGER_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Show usage
show_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  create <sa-name>        - Create new service account"
    echo "  delete <sa-name>        - Delete service account"
    echo "  list                    - List all service accounts"
    echo "  rotate <sa-name>        - Rotate service account keys"
    echo "  scope <sa-name> <roles> - Update service account roles"
    echo "  audit <sa-name>         - Audit service account usage"
    echo "  cleanup                 - Clean up unused service accounts"
    echo ""
    echo "Options:"
    echo "  --project <project-id>  - GCP project ID (required)"
    echo "  --dry-run              - Show what would be done without executing"
    echo "  --force                - Skip confirmations (use with caution)"
    echo "  --description <desc>   - Service account description"
    echo "  --display-name <name>  - Service account display name"
    echo ""
    echo "Environment Variables:"
    echo "  PROJECT_ID             - GCP project ID"
    echo "  ENVIRONMENT            - Environment (dev/test/staging/prod)"
    echo "  AUDIT_ENABLED          - Enable audit logging (default: true)"
    echo ""
    echo "Examples:"
    echo "  $0 create deploy-sa --project my-project"
    echo "  $0 scope deploy-sa roles/compute.admin,roles/storage.admin"
    echo "  $0 rotate deploy-sa"
    echo "  $0 audit deploy-sa"
}

# Parse command line arguments
parse_arguments() {
    COMMAND=""
    SA_NAME=""
    ROLES=""
    PROJECT_ID="${PROJECT_ID:-}"
    DRY_RUN=false
    FORCE=false
    DESCRIPTION=""
    DISPLAY_NAME=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project)
                PROJECT_ID="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
            ;;
            --description)
                DESCRIPTION="$2"
                shift 2
                ;;
            --display-name)
                DISPLAY_NAME="$2"
                shift 2
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            create|delete|list|rotate|scope|audit|cleanup)
                COMMAND="$1"
                shift
                ;;
            *)
                if [[ -z "$SA_NAME" && "$COMMAND" != "list" && "$COMMAND" != "cleanup" ]]; then
                    SA_NAME="$1"
                    shift
                elif [[ -z "$ROLES" && "$COMMAND" == "scope" ]]; then
                    ROLES="$1"
                    shift
                else
                    log_error "Unknown argument: $1"
                    show_usage
                    exit 1
                fi
                ;;
        esac
    done
    
    # Validation
    if [[ -z "$COMMAND" ]]; then
        log_error "Command is required"
        show_usage
        exit 1
    fi
    
    if [[ -z "$PROJECT_ID" ]]; then
        log_error "PROJECT_ID is required (use --project or environment variable)"
        exit 1
    fi
    
    if [[ "$COMMAND" != "list" && "$COMMAND" != "cleanup" && -z "$SA_NAME" ]]; then
        log_error "Service account name is required for $COMMAND"
        exit 1
    fi
    
    if [[ "$COMMAND" == "scope" && -z "$ROLES" ]]; then
        log_error "Roles are required for scope command"
        exit 1
    fi
}

# Validate GCP project access
validate_project() {
    log_step "Validating GCP project access..."
    
    if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
        log_error "Cannot access project: $PROJECT_ID"
        log_error "Ensure you have the necessary permissions and the project exists"
        exit 1
    fi
    
    log_success "Project access validated: $PROJECT_ID"
}

# Check if service account exists
sa_exists() {
    local sa_name="$1"
    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    gcloud iam service-accounts describe "$sa_email" \
        --project="$PROJECT_ID" >/dev/null 2>&1
}

# Execute or show command (for dry-run)
execute_command() {
    local cmd="$*"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would execute: $cmd"
        return 0
    else
        log_info "Executing: $cmd"
        eval "$cmd"
    fi
}

# Create audit log entry
audit_log_entry() {
    if [[ "${AUDIT_ENABLED:-true}" != "true" ]]; then
        return 0
    fi
    
    local action="$1"
    local sa_name="${2:-}"
    local details="${3:-}"
    
    local audit_dir="${CLOUDSDK_CONFIG:-$HOME/.gcloud}/logs"
    local audit_file="$audit_dir/sa-management-$(date +%Y%m%d).log"
    
    mkdir -p "$audit_dir"
    
    cat >> "$audit_file" <<EOF
$(date -u +%Y-%m-%dT%H:%M:%SZ) [SA_MANAGER] [$action] [${USER:-unknown}] [$PROJECT_ID] [$sa_name] $details
EOF
    
    log_info "Audit logged: $action"
}

# Create service account
create_service_account() {
    log_step "Creating service account: $SA_NAME"
    
    local sa_email="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Check if already exists
    if sa_exists "$SA_NAME"; then
        log_warning "Service account already exists: $sa_email"
        return 0
    fi
    
    # Set defaults
    local display_name="${DISPLAY_NAME:-$SA_NAME}"
    local description="${DESCRIPTION:-Service account for $SA_NAME}"
    
    # Add environment context
    if [[ -n "${ENVIRONMENT:-}" ]]; then
        description="$description (Environment: ${ENVIRONMENT})"
    fi
    
    # Create service account
    local create_cmd="gcloud iam service-accounts create '$SA_NAME'"
    create_cmd="$create_cmd --display-name='$display_name'"
    create_cmd="$create_cmd --description='$description'"
    create_cmd="$create_cmd --project='$PROJECT_ID'"
    
    if execute_command "$create_cmd"; then
        log_success "Created service account: $sa_email"
        audit_log_entry "CREATE" "$SA_NAME" "display_name=$display_name"
    else
        log_error "Failed to create service account"
        exit 1
    fi
    
    # Create initial configuration file
    if [[ "$DRY_RUN" != "true" ]]; then
        create_sa_config_file "$SA_NAME"
    fi
}

# Delete service account
delete_service_account() {
    log_step "Deleting service account: $SA_NAME"
    
    local sa_email="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Check if exists
    if ! sa_exists "$SA_NAME"; then
        log_error "Service account does not exist: $sa_email"
        exit 1
    fi
    
    # Safety check for production
    if [[ "${PRODUCTION_MODE:-false}" == "true" && "$FORCE" != "true" ]]; then
        log_warning "PRODUCTION ENVIRONMENT - Service account deletion"
        echo "Service account: $sa_email"
        echo ""
        read -p "Type the service account name to confirm deletion: " confirmation
        if [[ "$confirmation" != "$SA_NAME" ]]; then
            log_error "Confirmation failed. Service account not deleted."
            exit 1
        fi
    fi
    
    # List current IAM bindings
    log_info "Current IAM bindings for $sa_email:"
    if ! gcloud projects get-iam-policy "$PROJECT_ID" \
        --flatten="bindings[].members" \
        --format="table(bindings.role)" \
        --filter="bindings.members:serviceAccount:$sa_email" 2>/dev/null; then
        log_info "No IAM bindings found or unable to retrieve"
    fi
    
    # Delete service account
    local delete_cmd="gcloud iam service-accounts delete '$sa_email' --project='$PROJECT_ID'"
    if [[ "$FORCE" == "true" ]]; then
        delete_cmd="$delete_cmd --quiet"
    fi
    
    if execute_command "$delete_cmd"; then
        log_success "Deleted service account: $sa_email"
        audit_log_entry "DELETE" "$SA_NAME" "forced=$FORCE"
    else
        log_error "Failed to delete service account"
        exit 1
    fi
    
    # Clean up configuration file
    local config_file="${CLOUDSDK_CONFIG:-$HOME/.gcloud}/sa-configs/${SA_NAME}.json"
    if [[ -f "$config_file" && "$DRY_RUN" != "true" ]]; then
        rm -f "$config_file"
        log_info "Cleaned up configuration file"
    fi
}

# List service accounts
list_service_accounts() {
    log_step "Listing service accounts in project: $PROJECT_ID"
    
    echo -e "${WHITE}Service Accounts:${NC}"
    echo "────────────────────────────────────────────────────────────────"
    
    gcloud iam service-accounts list \
        --project="$PROJECT_ID" \
        --format="table(
            email:label='EMAIL',
            displayName:label='DISPLAY_NAME',
            description:label='DESCRIPTION',
            disabled:label='DISABLED'
        )"
    
    echo ""
    
    # Show additional statistics
    local total_count
    total_count=$(gcloud iam service-accounts list --project="$PROJECT_ID" --format="value(email)" | wc -l)
    local disabled_count
    disabled_count=$(gcloud iam service-accounts list --project="$PROJECT_ID" --format="value(disabled)" --filter="disabled=true" | wc -l)
    
    echo "Total Service Accounts: $total_count"
    echo "Disabled Service Accounts: $disabled_count"
}

# Rotate service account keys
rotate_service_account_keys() {
    log_step "Rotating keys for service account: $SA_NAME"
    
    local sa_email="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Check if exists
    if ! sa_exists "$SA_NAME"; then
        log_error "Service account does not exist: $sa_email"
        exit 1
    fi
    
    # List current keys
    log_info "Current keys for $sa_email:"
    gcloud iam service-accounts keys list \
        --iam-account="$sa_email" \
        --project="$PROJECT_ID"
    
    echo ""
    
    # WARNING: Key rotation requires careful coordination
    log_warning "KEY ROTATION WARNING:"
    echo "• This will create a new key and potentially invalidate existing keys"
    echo "• Ensure all applications can be updated with the new key"
    echo "• Consider using Workload Identity Federation instead of keys"
    echo ""
    
    if [[ "$FORCE" != "true" ]]; then
        read -p "Continue with key rotation? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Key rotation cancelled"
            return 0
        fi
    fi
    
    # Create new key
    local key_file="$SA_NAME-key-$(date +%Y%m%d-%H%M%S).json"
    local create_key_cmd="gcloud iam service-accounts keys create '$key_file' --iam-account='$sa_email' --project='$PROJECT_ID'"
    
    if execute_command "$create_key_cmd"; then
        log_success "Created new key: $key_file"
        audit_log_entry "ROTATE_KEY" "$SA_NAME" "new_key_file=$key_file"
        
        if [[ "$DRY_RUN" != "true" ]]; then
            # Secure the key file
            chmod 600 "$key_file"
            log_warning "New key created: $key_file"
            log_warning "• Update applications to use this key"
            log_warning "• Delete old keys after verification"
            log_warning "• Consider using Workload Identity Federation"
        fi
    else
        log_error "Failed to create new key"
        exit 1
    fi
}

# Update service account roles
update_service_account_roles() {
    log_step "Updating roles for service account: $SA_NAME"
    
    local sa_email="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Check if exists
    if ! sa_exists "$SA_NAME"; then
        log_error "Service account does not exist: $sa_email"
        exit 1
    fi
    
    # Parse roles
    IFS=',' read -ra ROLE_ARRAY <<< "$ROLES"
    
    log_info "Roles to assign:"
    for role in "${ROLE_ARRAY[@]}"; do
        echo "  • $role"
    done
    echo ""
    
    # Show current roles
    log_info "Current roles for $sa_email:"
    gcloud projects get-iam-policy "$PROJECT_ID" \
        --flatten="bindings[].members" \
        --format="table(bindings.role)" \
        --filter="bindings.members:serviceAccount:$sa_email" 2>/dev/null || log_info "No current roles found"
    
    echo ""
    
    # Confirmation for production
    if [[ "${PRODUCTION_MODE:-false}" == "true" && "$FORCE" != "true" ]]; then
        log_warning "PRODUCTION ENVIRONMENT - Role assignment"
        read -p "Continue with role assignment? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Role assignment cancelled"
            return 0
        fi
    fi
    
    # Assign roles
    for role in "${ROLE_ARRAY[@]}"; do
        # Validate role format
        if [[ ! "$role" =~ ^roles/ && ! "$role" =~ ^projects/.*/roles/ ]]; then
            log_error "Invalid role format: $role"
            log_error "Roles must start with 'roles/' or 'projects/PROJECT_ID/roles/'"
            continue
        fi
        
        log_info "Assigning role: $role"
        local assign_cmd="gcloud projects add-iam-policy-binding '$PROJECT_ID' --member='serviceAccount:$sa_email' --role='$role'"
        
        if execute_command "$assign_cmd"; then
            log_success "Assigned role: $role"
        else
            log_error "Failed to assign role: $role"
        fi
    done
    
    audit_log_entry "SCOPE_UPDATE" "$SA_NAME" "roles=$ROLES"
}

# Audit service account
audit_service_account() {
    log_step "Auditing service account: $SA_NAME"
    
    local sa_email="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Check if exists
    if ! sa_exists "$SA_NAME"; then
        log_error "Service account does not exist: $sa_email"
        exit 1
    fi
    
    echo -e "${WHITE}Service Account Audit Report${NC}"
    echo "══════════════════════════════════════════════════════════════"
    echo ""
    
    # Basic information
    echo -e "${CYAN}Basic Information:${NC}"
    gcloud iam service-accounts describe "$sa_email" \
        --project="$PROJECT_ID" \
        --format="yaml"
    echo ""
    
    # Keys information
    echo -e "${CYAN}Keys:${NC}"
    local keys_info
    keys_info=$(gcloud iam service-accounts keys list \
        --iam-account="$sa_email" \
        --project="$PROJECT_ID" \
        --format="table(name.scope(keys):label='KEY_ID',validAfterTime:label='CREATED',validBeforeTime:label='EXPIRES',keyType:label='TYPE')")
    
    echo "$keys_info"
    
    # Check for old keys
    local key_count
    key_count=$(gcloud iam service-accounts keys list --iam-account="$sa_email" --project="$PROJECT_ID" --format="value(name)" | wc -l)
    
    if [[ $key_count -gt 2 ]]; then
        log_warning "Service account has $key_count keys - consider key rotation"
    fi
    
    echo ""
    
    # IAM roles
    echo -e "${CYAN}Assigned Roles:${NC}"
    gcloud projects get-iam-policy "$PROJECT_ID" \
        --flatten="bindings[].members" \
        --format="table(bindings.role:label='ROLE')" \
        --filter="bindings.members:serviceAccount:$sa_email" 2>/dev/null || echo "No roles assigned"
    
    echo ""
    
    # Usage recommendations
    echo -e "${CYAN}Recommendations:${NC}"
    
    # Check key age
    local old_keys
    old_keys=$(gcloud iam service-accounts keys list \
        --iam-account="$sa_email" \
        --project="$PROJECT_ID" \
        --filter="validAfterTime<-P90D" \
        --format="value(name)" 2>/dev/null | wc -l || echo "0")
    
    if [[ $old_keys -gt 0 ]]; then
        echo "• Rotate keys older than 90 days ($old_keys found)"
    fi
    
    echo "• Consider using Workload Identity Federation instead of keys"
    echo "• Follow principle of least privilege for role assignments"
    echo "• Regularly audit service account usage"
    
    audit_log_entry "AUDIT" "$SA_NAME" "key_count=$key_count,old_keys=$old_keys"
}

# Cleanup unused service accounts
cleanup_service_accounts() {
    log_step "Cleaning up unused service accounts in project: $PROJECT_ID"
    
    echo -e "${YELLOW}This will identify potentially unused service accounts.${NC}"
    echo "Please review carefully before deletion."
    echo ""
    
    # Get all service accounts
    local all_sas
    mapfile -t all_sas < <(gcloud iam service-accounts list \
        --project="$PROJECT_ID" \
        --format="value(email)")
    
    echo "Analyzing ${#all_sas[@]} service accounts..."
    echo ""
    
    local unused_count=0
    
    for sa_email in "${all_sas[@]}"; do
        # Skip default service accounts
        if [[ "$sa_email" =~ -compute@developer.gserviceaccount.com$ ]] || \
           [[ "$sa_email" =~ @appspot.gserviceaccount.com$ ]] || \
           [[ "$sa_email" =~ @cloudbuild.gserviceaccount.com$ ]]; then
            continue
        fi
        
        # Check if service account has any keys
        local key_count
        key_count=$(gcloud iam service-accounts keys list \
            --iam-account="$sa_email" \
            --project="$PROJECT_ID" \
            --format="value(name)" 2>/dev/null | wc -l || echo "0")
        
        # Check if service account has any IAM bindings
        local role_count
        role_count=$(gcloud projects get-iam-policy "$PROJECT_ID" \
            --flatten="bindings[].members" \
            --format="value(bindings.role)" \
            --filter="bindings.members:serviceAccount:$sa_email" 2>/dev/null | wc -l || echo "0")
        
        # Consider unused if no keys and no roles (or only basic roles)
        if [[ $key_count -le 1 && $role_count -eq 0 ]]; then
            echo -e "${YELLOW}Potentially unused:${NC} $sa_email"
            echo "  Keys: $key_count, Roles: $role_count"
            ((unused_count++))
        fi
    done
    
    echo ""
    echo "Found $unused_count potentially unused service accounts"
    
    if [[ $unused_count -gt 0 ]]; then
        echo ""
        log_warning "Manual review required before deletion"
        echo "Use: $0 delete <sa-name> to delete specific service accounts"
    fi
    
    audit_log_entry "CLEANUP_SCAN" "" "total_sas=${#all_sas[@]},unused_count=$unused_count"
}

# Create service account configuration file
create_sa_config_file() {
    local sa_name="$1"
    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    local config_dir="${CLOUDSDK_CONFIG:-$HOME/.gcloud}/sa-configs"
    mkdir -p "$config_dir"
    
    local config_file="$config_dir/${sa_name}.json"
    
    cat > "$config_file" <<EOF
{
  "service_account": {
    "name": "$sa_name",
    "email": "$sa_email",
    "project_id": "$PROJECT_ID",
    "environment": "${ENVIRONMENT:-unknown}",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "created_by": "${USER:-unknown}",
    "manager_version": "$SA_MANAGER_VERSION"
  },
  "security": {
    "key_rotation_recommended": true,
    "workload_identity_preferred": true,
    "audit_enabled": ${AUDIT_ENABLED:-true}
  },
  "usage": {
    "description": "${DESCRIPTION:-}",
    "intended_use": "Please document the intended use of this service account"
  }
}
EOF
    
    log_info "Created configuration file: $config_file"
}

# Main execution
main() {
    print_banner
    parse_arguments "$@"
    validate_project
    
    case "$COMMAND" in
        create)
            create_service_account
            ;;
        delete)
            delete_service_account
            ;;
        list)
            list_service_accounts
            ;;
        rotate)
            rotate_service_account_keys
            ;;
        scope)
            update_service_account_roles
            ;;
        audit)
            audit_service_account
            ;;
        cleanup)
            cleanup_service_accounts
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi