#!/usr/bin/env bash
# Infrastructure Rollback System
# Terraform-based infrastructure rollback with state management

set -euo pipefail

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Logging functions
log_error() { echo -e "${RED}❌ ERROR: $1${NC}" >&2; }
log_warning() { echo -e "${YELLOW}⚠️  WARNING: $1${NC}"; }
log_success() { echo -e "${GREEN}✅ SUCCESS: $1${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  INFO: $1${NC}"; }
log_progress() { echo -e "${CYAN}🔄 ROLLBACK: $1${NC}"; }
log_infra() { echo -e "${PURPLE}🏗️  INFRASTRUCTURE: $1${NC}"; }

# Configuration
PROJECT_ID="${PROJECT_ID:-}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
WORKING_DIR="${WORKING_DIR:-terraform}"
ROLLBACK_TYPE="${ROLLBACK_TYPE:-terraform}"  # terraform, state, snapshot
TARGET_VERSION="${TARGET_VERSION:-}"
TARGET_STATE="${TARGET_STATE:-}"

# Terraform configuration
TF_VERSION="${TF_VERSION:-1.6.0}"
TF_STATE_BUCKET="${TF_STATE_BUCKET:-}"
TF_STATE_KEY="${TF_STATE_KEY:-terraform/state}"
TF_WORKSPACE="${TF_WORKSPACE:-$ENVIRONMENT}"

# Rollback configuration
BACKUP_STATE="${BACKUP_STATE:-true}"
VERIFY_ROLLBACK="${VERIFY_ROLLBACK:-true}"
OUTPUT_DIR="${OUTPUT_DIR:-./infra-rollback-logs}"
DRY_RUN="${DRY_RUN:-false}"
AUTO_APPROVE="${AUTO_APPROVE:-false}"

# Safety settings
REQUIRE_CONFIRMATION="${REQUIRE_CONFIRMATION:-true}"
ALLOW_DESTRUCTIVE_CHANGES="${ALLOW_DESTRUCTIVE_CHANGES:-false}"
MAX_ROLLBACK_DAYS="${MAX_ROLLBACK_DAYS:-7}"

log_info "🏗️ Starting Infrastructure Rollback System"
log_info "Project: $PROJECT_ID"
log_info "Environment: $ENVIRONMENT"
log_info "Rollback Type: $ROLLBACK_TYPE"
log_info "Working Directory: $WORKING_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Initialize rollback state
declare -A rollback_state
declare -A backup_info
declare -A validation_results

# Function to validate prerequisites
validate_prerequisites() {
    log_progress "Validating prerequisites"
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is required but not installed"
        exit 1
    fi
    
    local tf_version
    tf_version=$(terraform version -json | jq -r '.terraform_version')
    log_info "Terraform version: $tf_version"
    
    # Check gcloud CLI
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is required but not installed"
        exit 1
    fi
    
    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 > /dev/null; then
        log_error "No active gcloud authentication found"
        exit 1
    fi
    
    # Check project access
    if [[ -n "$PROJECT_ID" ]]; then
        if ! gcloud projects describe "$PROJECT_ID" &> /dev/null; then
            log_error "Cannot access project: $PROJECT_ID"
            exit 1
        fi
    else
        log_error "PROJECT_ID is required"
        exit 1
    fi
    
    # Check working directory
    if [[ ! -d "$WORKING_DIR" ]]; then
        log_error "Working directory does not exist: $WORKING_DIR"
        exit 1
    fi
    
    # Check for Terraform files
    if [[ ! -f "$WORKING_DIR/main.tf" ]]; then
        log_error "No main.tf found in working directory: $WORKING_DIR"
        exit 1
    fi
    
    log_success "Prerequisites validation completed"
}

# Function to initialize Terraform
initialize_terraform() {
    log_progress "Initializing Terraform"
    
    cd "$WORKING_DIR"
    
    # Configure backend if state bucket is provided
    if [[ -n "$TF_STATE_BUCKET" ]]; then
        cat > backend.conf << EOF
bucket = "$TF_STATE_BUCKET"
prefix = "$TF_STATE_KEY"
EOF
        
        if [[ "$DRY_RUN" == "false" ]]; then
            terraform init -backend-config=backend.conf -reconfigure
        else
            log_info "[DRY RUN] Would initialize Terraform with backend config"
        fi
    else
        if [[ "$DRY_RUN" == "false" ]]; then
            terraform init
        else
            log_info "[DRY RUN] Would initialize Terraform"
        fi
    fi
    
    # Select or create workspace
    if [[ "$DRY_RUN" == "false" ]]; then
        terraform workspace select "$TF_WORKSPACE" || terraform workspace new "$TF_WORKSPACE"
        log_info "Using Terraform workspace: $TF_WORKSPACE"
    else
        log_info "[DRY RUN] Would use workspace: $TF_WORKSPACE"
    fi
    
    cd - > /dev/null
    log_success "Terraform initialization completed"
}

# Function to get current infrastructure state
get_current_state() {
    log_progress "Getting current infrastructure state"
    
    cd "$WORKING_DIR"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Get current state info
        if terraform show -json > "$OUTPUT_DIR/current-state.json" 2>/dev/null; then
            rollback_state["current_state_size"]=$(wc -c < "$OUTPUT_DIR/current-state.json")
            
            # Extract resource count
            local resource_count
            resource_count=$(jq '.values.root_module.resources | length' "$OUTPUT_DIR/current-state.json" 2>/dev/null || echo "0")
            rollback_state["current_resource_count"]="$resource_count"
            
            log_info "Current resources: $resource_count"
        else
            log_warning "Could not retrieve current state"
            rollback_state["current_state_size"]="0"
            rollback_state["current_resource_count"]="0"
        fi
        
        # Get state metadata
        if terraform state list > "$OUTPUT_DIR/current-resources.txt" 2>/dev/null; then
            rollback_state["current_state_file"]="$OUTPUT_DIR/current-resources.txt"
        fi
        
        # Get outputs
        if terraform output -json > "$OUTPUT_DIR/current-outputs.json" 2>/dev/null; then
            rollback_state["current_outputs_file"]="$OUTPUT_DIR/current-outputs.json"
        fi
    else
        log_info "[DRY RUN] Would retrieve current infrastructure state"
        rollback_state["current_resource_count"]="dry_run"
    fi
    
    cd - > /dev/null
    log_success "Current state captured"
}

# Function to backup current state
backup_current_state() {
    if [[ "$BACKUP_STATE" != "true" ]]; then
        log_info "State backup disabled"
        return 0
    fi
    
    log_progress "Backing up current state"
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$OUTPUT_DIR/state-backup-$backup_timestamp"
    mkdir -p "$backup_dir"
    
    cd "$WORKING_DIR"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Pull current state
        terraform state pull > "$backup_dir/terraform.tfstate"
        
        # Copy current working directory
        cp -r . "$backup_dir/terraform-config/"
        
        # Create backup metadata
        cat > "$backup_dir/backup-metadata.json" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "backup_type": "pre_rollback",
  "project_id": "$PROJECT_ID",
  "environment": "$ENVIRONMENT",
  "workspace": "$TF_WORKSPACE",
  "resource_count": ${rollback_state[current_resource_count]},
  "state_size": ${rollback_state[current_state_size]:-0}
}
EOF
        
        backup_info["backup_dir"]="$backup_dir"
        backup_info["backup_timestamp"]="$backup_timestamp"
        backup_info["state_file"]="$backup_dir/terraform.tfstate"
        
        log_success "State backup created: $backup_dir"
    else
        backup_info["backup_dir"]="$backup_dir (dry run)"
        log_info "[DRY RUN] Would create state backup: $backup_dir"
    fi
    
    cd - > /dev/null
}

# Function to validate rollback target
validate_rollback_target() {
    log_progress "Validating rollback target"
    
    case "$ROLLBACK_TYPE" in
        terraform)
            if [[ -z "$TARGET_VERSION" ]]; then
                log_error "TARGET_VERSION is required for Terraform rollback"
                return 1
            fi
            
            # Check if target version is a Git commit, tag, or state backup
            if [[ "$TARGET_VERSION" =~ ^[a-f0-9]{7,40}$ ]]; then
                log_info "Target appears to be a Git commit: $TARGET_VERSION"
            elif [[ -d "$TARGET_VERSION" ]]; then
                log_info "Target appears to be a backup directory: $TARGET_VERSION"
            else
                log_info "Target version: $TARGET_VERSION"
            fi
            ;;
        state)
            if [[ -z "$TARGET_STATE" ]]; then
                log_error "TARGET_STATE is required for state rollback"
                return 1
            fi
            
            if [[ ! -f "$TARGET_STATE" ]]; then
                log_error "Target state file does not exist: $TARGET_STATE"
                return 1
            fi
            
            log_info "Target state file: $TARGET_STATE"
            ;;
        snapshot)
            log_info "Snapshot rollback validation"
            # Additional validation for snapshot rollback
            ;;
        *)
            log_error "Unknown rollback type: $ROLLBACK_TYPE"
            return 1
            ;;
    esac
    
    # Check rollback age
    if [[ -n "${backup_info[backup_timestamp]:-}" ]]; then
        local current_time=$(date +%s)
        local backup_time=$(date -d "${backup_info[backup_timestamp]}" +%s 2>/dev/null || echo "$current_time")
        local age_days=$(( (current_time - backup_time) / 86400 ))
        
        if [[ $age_days -gt $MAX_ROLLBACK_DAYS ]]; then
            log_warning "Rollback target is $age_days days old (max: $MAX_ROLLBACK_DAYS days)"
            if [[ "$REQUIRE_CONFIRMATION" == "true" && "$DRY_RUN" == "false" ]]; then
                echo -n "Continue with old rollback target? (yes/no): "
                read -r confirmation
                if [[ "$confirmation" != "yes" ]]; then
                    log_info "Rollback cancelled by user"
                    exit 0
                fi
            fi
        fi
    fi
    
    log_success "Rollback target validation completed"
}

# Function to generate rollback plan
generate_rollback_plan() {
    log_progress "Generating rollback plan"
    
    cd "$WORKING_DIR"
    
    local plan_file="$OUTPUT_DIR/rollback-plan-$(date +%Y%m%d_%H%M%S).tfplan"
    local plan_output="$OUTPUT_DIR/rollback-plan-output.txt"
    
    case "$ROLLBACK_TYPE" in
        terraform)
            if [[ "$DRY_RUN" == "false" ]]; then
                # Checkout target version if it's a Git reference
                if [[ "$TARGET_VERSION" =~ ^[a-f0-9]{7,40}$ ]] && git rev-parse --git-dir > /dev/null 2>&1; then
                    log_info "Checking out Git commit: $TARGET_VERSION"
                    git checkout "$TARGET_VERSION"
                elif [[ -d "$TARGET_VERSION" ]]; then
                    log_info "Restoring from backup directory: $TARGET_VERSION"
                    cp -r "$TARGET_VERSION/terraform-config/"* .
                fi
                
                # Generate plan
                terraform plan -out="$plan_file" -detailed-exitcode > "$plan_output" 2>&1
                local plan_exit_code=$?
                
                rollback_state["plan_file"]="$plan_file"
                rollback_state["plan_output"]="$plan_output"
                
                if [[ $plan_exit_code -eq 2 ]]; then
                    log_info "Rollback plan generated with changes"
                    rollback_state["has_changes"]="true"
                elif [[ $plan_exit_code -eq 0 ]]; then
                    log_info "No changes needed for rollback"
                    rollback_state["has_changes"]="false"
                else
                    log_error "Failed to generate rollback plan"
                    return 1
                fi
                
                # Analyze plan for destructive changes
                if grep -q "will be destroyed" "$plan_output"; then
                    rollback_state["has_destructive_changes"]="true"
                    log_warning "Rollback plan includes destructive changes"
                    
                    if [[ "$ALLOW_DESTRUCTIVE_CHANGES" != "true" ]]; then
                        log_error "Destructive changes not allowed"
                        return 1
                    fi
                else
                    rollback_state["has_destructive_changes"]="false"
                fi
            else
                log_info "[DRY RUN] Would generate rollback plan"
                rollback_state["has_changes"]="true"
                rollback_state["has_destructive_changes"]="false"
            fi
            ;;
        state)
            # For state rollback, we replace the state file
            log_info "State rollback plan: replace current state with $TARGET_STATE"
            rollback_state["has_changes"]="true"
            rollback_state["has_destructive_changes"]="true"
            ;;
    esac
    
    cd - > /dev/null
    log_success "Rollback plan generated"
}

# Function to execute rollback
execute_rollback() {
    log_progress "Executing infrastructure rollback"
    
    if [[ "${rollback_state[has_changes]}" != "true" ]]; then
        log_info "No changes to apply - rollback not needed"
        return 0
    fi
    
    # Confirmation check
    if [[ "$REQUIRE_CONFIRMATION" == "true" && "$DRY_RUN" == "false" && "$AUTO_APPROVE" != "true" ]]; then
        echo ""
        log_warning "About to execute infrastructure rollback:"
        log_warning "  - Project: $PROJECT_ID"
        log_warning "  - Environment: $ENVIRONMENT"
        log_warning "  - Rollback Type: $ROLLBACK_TYPE"
        log_warning "  - Target: ${TARGET_VERSION:-$TARGET_STATE}"
        log_warning "  - Destructive Changes: ${rollback_state[has_destructive_changes]}"
        echo ""
        echo -n "Do you want to proceed? (yes/no): "
        read -r confirmation
        if [[ "$confirmation" != "yes" ]]; then
            log_info "Rollback cancelled by user"
            exit 0
        fi
    fi
    
    cd "$WORKING_DIR"
    
    case "$ROLLBACK_TYPE" in
        terraform)
            if [[ "$DRY_RUN" == "false" ]]; then
                local plan_file="${rollback_state[plan_file]}"
                
                if [[ "$AUTO_APPROVE" == "true" ]]; then
                    terraform apply -auto-approve "$plan_file"
                else
                    terraform apply "$plan_file"
                fi
                
                log_success "Terraform rollback applied"
            else
                log_info "[DRY RUN] Would apply Terraform rollback plan"
            fi
            ;;
        state)
            if [[ "$DRY_RUN" == "false" ]]; then
                # Replace current state with target state
                terraform state push "$TARGET_STATE"
                log_success "State rollback completed"
            else
                log_info "[DRY RUN] Would replace state with: $TARGET_STATE"
            fi
            ;;
    esac
    
    cd - > /dev/null
    rollback_state["rollback_executed"]="true"
}

# Function to verify rollback
verify_rollback() {
    if [[ "$VERIFY_ROLLBACK" != "true" ]]; then
        log_info "Rollback verification disabled"
        return 0
    fi
    
    log_progress "Verifying rollback"
    
    cd "$WORKING_DIR"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Refresh state
        terraform refresh > /dev/null 2>&1
        
        # Get new state
        terraform show -json > "$OUTPUT_DIR/post-rollback-state.json" 2>/dev/null
        
        # Compare resource counts
        local new_resource_count
        new_resource_count=$(jq '.values.root_module.resources | length' "$OUTPUT_DIR/post-rollback-state.json" 2>/dev/null || echo "0")
        
        rollback_state["final_resource_count"]="$new_resource_count"
        
        log_info "Resources after rollback: $new_resource_count"
        log_info "Resources before rollback: ${rollback_state[current_resource_count]}"
        
        # Validate infrastructure health
        if validate_infrastructure_health; then
            validation_results["health_check"]="passed"
            log_success "Infrastructure health check passed"
        else
            validation_results["health_check"]="failed"
            log_warning "Infrastructure health check failed"
        fi
        
        # Test essential services
        if test_essential_services; then
            validation_results["service_test"]="passed"
            log_success "Essential services test passed"
        else
            validation_results["service_test"]="failed"
            log_warning "Essential services test failed"
        fi
    else
        log_info "[DRY RUN] Would verify rollback"
        validation_results["health_check"]="dry_run"
        validation_results["service_test"]="dry_run"
    fi
    
    cd - > /dev/null
    log_success "Rollback verification completed"
}

# Function to validate infrastructure health
validate_infrastructure_health() {
    log_infra "Validating infrastructure health"
    
    # Check project status
    if ! gcloud projects describe "$PROJECT_ID" --format="value(lifecycleState)" | grep -q "ACTIVE"; then
        log_error "Project is not in ACTIVE state"
        return 1
    fi
    
    # Check essential APIs
    local essential_apis=(
        "compute.googleapis.com"
        "container.googleapis.com"
        "storage.googleapis.com"
    )
    
    for api in "${essential_apis[@]}"; do
        if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            log_warning "Essential API not enabled: $api"
        fi
    done
    
    # Check for compute instances
    local instance_count
    instance_count=$(gcloud compute instances list --format="value(name)" | wc -l)
    if [[ $instance_count -gt 0 ]]; then
        log_info "Compute instances: $instance_count"
        
        # Check instance health
        local running_instances
        running_instances=$(gcloud compute instances list --filter="status:RUNNING" --format="value(name)" | wc -l)
        log_info "Running instances: $running_instances"
    fi
    
    return 0
}

# Function to test essential services
test_essential_services() {
    log_infra "Testing essential services"
    
    # Test Cloud Run services
    local cloudrun_services
    cloudrun_services=$(gcloud run services list --format="value(name)" 2>/dev/null | wc -l)
    if [[ $cloudrun_services -gt 0 ]]; then
        log_info "Cloud Run services: $cloudrun_services"
    fi
    
    # Test Cloud Functions
    local functions
    functions=$(gcloud functions list --format="value(name)" 2>/dev/null | wc -l)
    if [[ $functions -gt 0 ]]; then
        log_info "Cloud Functions: $functions"
    fi
    
    # Test storage buckets
    local buckets
    buckets=$(gsutil ls 2>/dev/null | wc -l)
    if [[ $buckets -gt 0 ]]; then
        log_info "Storage buckets: $buckets"
    fi
    
    return 0
}

# Function to generate rollback report
generate_rollback_report() {
    log_progress "Generating rollback report"
    
    local report_file="$OUTPUT_DIR/rollback-report-$(date +%Y%m%d_%H%M%S).json"
    
    cat > "$report_file" << EOF
{
  "rollback_session": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "project_id": "$PROJECT_ID",
    "environment": "$ENVIRONMENT",
    "rollback_type": "$ROLLBACK_TYPE",
    "target_version": "${TARGET_VERSION:-$TARGET_STATE}",
    "dry_run": $DRY_RUN
  },
  "initial_state": {
    "resource_count": ${rollback_state[current_resource_count]:-0},
    "state_size": ${rollback_state[current_state_size]:-0}
  },
  "backup_info": {
    "backup_created": $BACKUP_STATE,
    "backup_dir": "${backup_info[backup_dir]:-none}",
    "backup_timestamp": "${backup_info[backup_timestamp]:-none}"
  },
  "rollback_execution": {
    "executed": "${rollback_state[rollback_executed]:-false}",
    "had_changes": "${rollback_state[has_changes]:-false}",
    "had_destructive_changes": "${rollback_state[has_destructive_changes]:-false}",
    "plan_file": "${rollback_state[plan_file]:-none}"
  },
  "validation_results": $(printf '%s\n' "${!validation_results[@]}" | jq -R . | jq -s 'map(split(":") | {(.[0]): .[1]}) | add' 2>/dev/null || echo "{}"),
  "final_state": {
    "resource_count": ${rollback_state[final_resource_count]:-0}
  }
}
EOF
    
    log_success "Rollback report generated: $report_file"
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --working-dir)
                WORKING_DIR="$2"
                shift 2
                ;;
            --rollback-type)
                ROLLBACK_TYPE="$2"
                shift 2
                ;;
            --target-version)
                TARGET_VERSION="$2"
                shift 2
                ;;
            --target-state)
                TARGET_STATE="$2"
                shift 2
                ;;
            --tf-state-bucket)
                TF_STATE_BUCKET="$2"
                shift 2
                ;;
            --tf-workspace)
                TF_WORKSPACE="$2"
                shift 2
                ;;
            --no-backup)
                BACKUP_STATE="false"
                shift
                ;;
            --allow-destructive)
                ALLOW_DESTRUCTIVE_CHANGES="true"
                shift
                ;;
            --auto-approve)
                AUTO_APPROVE="true"
                shift
                ;;
            --no-confirmation)
                REQUIRE_CONFIRMATION="false"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --project-id ID             GCP project ID"
                echo "  --environment ENV           Environment name"
                echo "  --working-dir DIR           Terraform working directory"
                echo "  --rollback-type TYPE        Rollback type (terraform, state, snapshot)"
                echo "  --target-version VERSION    Target version (commit, tag, backup dir)"
                echo "  --target-state FILE         Target state file"
                echo "  --tf-state-bucket BUCKET    Terraform state bucket"
                echo "  --tf-workspace WORKSPACE    Terraform workspace"
                echo "  --no-backup                 Skip state backup"
                echo "  --allow-destructive         Allow destructive changes"
                echo "  --auto-approve             Auto-approve Terraform apply"
                echo "  --no-confirmation           Skip confirmation prompts"
                echo "  --dry-run                   Dry run mode"
                echo "  --help                      Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$PROJECT_ID" ]]; then
        log_error "PROJECT_ID is required"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "🧪 Running in DRY RUN mode"
    fi
    
    # Execute rollback process
    validate_prerequisites
    initialize_terraform
    get_current_state
    backup_current_state
    validate_rollback_target
    generate_rollback_plan
    execute_rollback
    verify_rollback
    generate_rollback_report
    
    log_success "Infrastructure rollback process completed"
}

# Execute main function with all arguments
main "$@"