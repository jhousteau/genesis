#!/usr/bin/env bash
# Deployment Strategy Runner
# Orchestrates different deployment strategies based on configuration

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
log_error() { echo -e "${RED}❌ ERROR: $1${NC}" >&2; }
log_warning() { echo -e "${YELLOW}⚠️  WARNING: $1${NC}"; }
log_success() { echo -e "${GREEN}✅ SUCCESS: $1${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  INFO: $1${NC}"; }
log_debug() { [[ "${LOG_LEVEL:-INFO}" == "DEBUG" ]] && echo -e "${PURPLE}🔍 DEBUG: $1${NC}"; }
log_progress() { echo -e "${CYAN}🚀 PROGRESS: $1${NC}"; }

# Global variables
PROJECT_NAME=""
ENVIRONMENT=""
DEPLOYMENT_STRATEGY=""
GCP_PROJECT=""
REGION="us-central1"
DRY_RUN="false"
FORCE="false"
ROLLBACK_ON_FAILURE="true"

# Configuration files
DEPLOY_CONFIG_FILE=".deploy-config.yaml"
DEPLOYMENT_RECORD_DIR=".deployments"

# Show help
show_help() {
    cat << EOF
Deployment Strategy Runner

USAGE:
    $(basename "$0") [OPTIONS]

OPTIONS:
    --project NAME          Project name
    --env ENVIRONMENT       Environment (dev/test/stage/prod)
    --strategy STRATEGY     Deployment strategy (rolling/blue-green/canary)
    --percent NUMBER        Canary deployment percentage (for canary strategy)
    --region REGION         GCP region (default: us-central1)
    --dry-run              Show what would be deployed
    --force                Force deployment even if validations fail
    --no-rollback          Disable automatic rollback on failure
    --help                 Show this help

DEPLOYMENT STRATEGIES:
    rolling                 Rolling deployment (default)
    blue-green             Blue-green deployment with instant switchover
    canary                 Canary deployment with gradual traffic shift
    recreate               Recreate deployment (downtime)

EXAMPLES:
    # Rolling deployment to dev
    $(basename "$0") --project my-app --env dev

    # Blue-green deployment to production
    $(basename "$0") --project my-app --env prod --strategy blue-green

    # Canary deployment with 10% initial traffic
    $(basename "$0") --project my-app --env prod --strategy canary --percent 10

    # Dry run to see what would be deployed
    $(basename "$0") --project my-app --env dev --dry-run

EOF
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project=*)
                PROJECT_NAME="${1#*=}"
                shift
                ;;
            --project)
                PROJECT_NAME="$2"
                shift 2
                ;;
            --env=*)
                ENVIRONMENT="${1#*=}"
                shift
                ;;
            --env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --strategy=*)
                DEPLOYMENT_STRATEGY="${1#*=}"
                shift
                ;;
            --strategy)
                DEPLOYMENT_STRATEGY="$2"
                shift 2
                ;;
            --percent=*)
                CANARY_PERCENT="${1#*=}"
                shift
                ;;
            --percent)
                CANARY_PERCENT="$2"
                shift 2
                ;;
            --region=*)
                REGION="${1#*=}"
                shift
                ;;
            --region)
                REGION="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --force)
                FORCE="true"
                shift
                ;;
            --no-rollback)
                ROLLBACK_ON_FAILURE="false"
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Load configuration
load_config() {
    if [[ ! -f "$DEPLOY_CONFIG_FILE" ]]; then
        log_error "Deployment configuration not found: $DEPLOY_CONFIG_FILE"
        log_info "Run 'deploy-orchestrator init' to create configuration"
        exit 1
    fi

    # Parse YAML configuration (using yq if available, fallback to basic parsing)
    if command -v yq &> /dev/null; then
        PROJECT_NAME="${PROJECT_NAME:-$(yq e '.project.name' "$DEPLOY_CONFIG_FILE")}"
        PROJECT_TYPE="$(yq e '.project.type' "$DEPLOY_CONFIG_FILE")"

        if [[ -n "$ENVIRONMENT" ]]; then
            GCP_PROJECT="$(yq e ".environments.$ENVIRONMENT.gcp_project" "$DEPLOY_CONFIG_FILE")"
            DEPLOYMENT_STRATEGY="${DEPLOYMENT_STRATEGY:-$(yq e ".environments.$ENVIRONMENT.deployment_strategy // .strategies.default" "$DEPLOY_CONFIG_FILE")}"
        fi
    else
        log_debug "yq not available, using basic parsing"
        PROJECT_NAME="${PROJECT_NAME:-$(grep "name:" "$DEPLOY_CONFIG_FILE" | head -1 | awk '{print $2}')}"
        PROJECT_TYPE="$(grep "type:" "$DEPLOY_CONFIG_FILE" | head -1 | awk '{print $2}')"

        # Basic environment parsing
        if [[ -n "$ENVIRONMENT" ]]; then
            GCP_PROJECT="${PROJECT_NAME}-${ENVIRONMENT}"
        fi
    fi

    # Set defaults
    DEPLOYMENT_STRATEGY="${DEPLOYMENT_STRATEGY:-rolling}"
    GCP_PROJECT="${GCP_PROJECT:-${PROJECT_NAME}-${ENVIRONMENT}}"
    CANARY_PERCENT="${CANARY_PERCENT:-10}"

    log_debug "Configuration loaded:"
    log_debug "  PROJECT_NAME: $PROJECT_NAME"
    log_debug "  PROJECT_TYPE: $PROJECT_TYPE"
    log_debug "  ENVIRONMENT: $ENVIRONMENT"
    log_debug "  GCP_PROJECT: $GCP_PROJECT"
    log_debug "  DEPLOYMENT_STRATEGY: $DEPLOYMENT_STRATEGY"
    log_debug "  REGION: $REGION"
}

# Validate deployment requirements
validate_requirements() {
    local validation_failed="false"

    log_info "Validating deployment requirements..."

    # Check required tools
    for tool in gcloud docker; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            validation_failed="true"
        fi
    done

    # Check GCP authentication
    if ! gcloud auth list --filter="status:ACTIVE" --format="value(account)" | grep -q "."; then
        log_error "No active GCP authentication found"
        log_info "Run: gcloud auth login"
        validation_failed="true"
    fi

    # Check project access
    if ! gcloud projects describe "$GCP_PROJECT" &> /dev/null; then
        log_error "Cannot access GCP project: $GCP_PROJECT"
        validation_failed="true"
    fi

    # Check required APIs
    local required_apis=(
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
        "artifactregistry.googleapis.com"
    )

    for api in "${required_apis[@]}"; do
        if ! gcloud services list --enabled --project="$GCP_PROJECT" --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            log_warning "Required API not enabled: $api"
            if [[ "$FORCE" != "true" ]]; then
                log_info "Enable with: gcloud services enable $api --project=$GCP_PROJECT"
                validation_failed="true"
            fi
        fi
    done

    # Check Dockerfile exists for containerized deployments
    if [[ ! -f "Dockerfile" ]] && [[ "$PROJECT_TYPE" != "infrastructure" ]]; then
        log_error "Dockerfile not found"
        validation_failed="true"
    fi

    if [[ "$validation_failed" == "true" ]] && [[ "$FORCE" != "true" ]]; then
        log_error "Validation failed. Use --force to override."
        exit 1
    fi

    log_success "Requirements validation completed"
}

# Run pre-deployment validation
run_pre_deployment_validation() {
    log_info "Running pre-deployment validation..."

    # Run validators if not forcing
    if [[ "$FORCE" != "true" ]]; then
        log_progress "Running security validation..."
        if ! "$SCRIPT_DIR/../validators/security/run-security-validation.sh" \
            --project "$PROJECT_NAME" \
            --env "$ENVIRONMENT" \
            --quiet; then
            log_error "Security validation failed"
            return 1
        fi

        log_progress "Running infrastructure validation..."
        if ! "$SCRIPT_DIR/../validators/infrastructure/run-infrastructure-validation.sh" \
            --project "$PROJECT_NAME" \
            --env "$ENVIRONMENT" \
            --quiet; then
            log_error "Infrastructure validation failed"
            return 1
        fi

        log_progress "Running cost validation..."
        if ! "$SCRIPT_DIR/../validators/cost/run-cost-validation.sh" \
            --project "$PROJECT_NAME" \
            --env "$ENVIRONMENT" \
            --quiet; then
            log_warning "Cost validation failed (non-blocking)"
        fi
    fi

    log_success "Pre-deployment validation completed"
}

# Build and push container image
build_and_push_image() {
    if [[ "$PROJECT_TYPE" == "infrastructure" ]]; then
        log_info "Skipping image build for infrastructure project"
        return 0
    fi

    log_info "Building and pushing container image..."

    local deployment_id="${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    local image_tag="$deployment_id"
    local image_url="${REGION}-docker.pkg.dev/${GCP_PROJECT}/containers/${PROJECT_NAME}"

    # Configure Docker for GCR
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

    # Build image
    log_progress "Building Docker image..."
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would build image: ${image_url}:${image_tag}"
    else
        docker build \
            --tag "${image_url}:${image_tag}" \
            --tag "${image_url}:${ENVIRONMENT}" \
            --tag "${image_url}:latest" \
            --build-arg ENV="$ENVIRONMENT" \
            --build-arg VERSION="$image_tag" \
            --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
            --build-arg VCS_REF="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
            .

        # Push image
        log_progress "Pushing Docker image..."
        docker push "${image_url}:${image_tag}"
        docker push "${image_url}:${ENVIRONMENT}"
        docker push "${image_url}:latest"
    fi

    # Export variables for strategy scripts
    export IMAGE_TAG="$image_tag"
    export IMAGE_URL="$image_url"
    export DEPLOYMENT_ID="$deployment_id"

    log_success "Image build and push completed"
}

# Execute deployment strategy
execute_deployment_strategy() {
    log_info "Executing deployment strategy: $DEPLOYMENT_STRATEGY"

    local strategy_script=""
    case "$DEPLOYMENT_STRATEGY" in
        rolling)
            strategy_script="$SCRIPT_DIR/rolling/deploy-rolling.sh"
            ;;
        blue-green)
            strategy_script="$SCRIPT_DIR/blue-green/deploy-blue-green.sh"
            ;;
        canary)
            strategy_script="$SCRIPT_DIR/canary/deploy-canary.sh"
            ;;
        recreate)
            strategy_script="$SCRIPT_DIR/rolling/deploy-rolling.sh"  # Use rolling with recreate flag
            export DEPLOYMENT_MODE="recreate"
            ;;
        *)
            log_error "Unknown deployment strategy: $DEPLOYMENT_STRATEGY"
            exit 1
            ;;
    esac

    if [[ ! -f "$strategy_script" ]]; then
        log_error "Strategy script not found: $strategy_script"
        exit 1
    fi

    # Export common variables
    export PROJECT_NAME
    export ENVIRONMENT
    export GCP_PROJECT
    export REGION
    export DRY_RUN
    export ROLLBACK_ON_FAILURE
    export CANARY_PERCENT

    # Execute strategy
    log_progress "Running deployment strategy script..."
    if ! "$strategy_script"; then
        log_error "Deployment strategy failed: $DEPLOYMENT_STRATEGY"

        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]] && [[ "$DRY_RUN" != "true" ]]; then
            log_warning "Initiating automatic rollback..."
            "$SCRIPT_DIR/../rollback/rollback-runner.sh" \
                --project "$PROJECT_NAME" \
                --env "$ENVIRONMENT" \
                --automatic
        fi

        exit 1
    fi

    log_success "Deployment strategy completed successfully"
}

# Run post-deployment validation
run_post_deployment_validation() {
    log_info "Running post-deployment validation..."

    local service_url=""

    # Get service URL based on project type
    case "$PROJECT_TYPE" in
        web-app|api|microservice)
            service_url=$(gcloud run services describe "$PROJECT_NAME" \
                --region="$REGION" \
                --project="$GCP_PROJECT" \
                --format="value(status.url)" 2>/dev/null || echo "")
            ;;
        infrastructure)
            log_info "Skipping service health check for infrastructure project"
            return 0
            ;;
    esac

    if [[ -n "$service_url" ]]; then
        log_progress "Running health checks..."

        # Wait for service to be ready
        local max_attempts=30
        local attempt=1

        while [[ $attempt -le $max_attempts ]]; do
            log_debug "Health check attempt $attempt/$max_attempts"

            if curl -f "${service_url}/health" --max-time 10 --silent > /dev/null 2>&1; then
                log_success "Health check passed"
                break
            fi

            if [[ $attempt -eq $max_attempts ]]; then
                log_error "Health check failed after $max_attempts attempts"

                if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
                    log_warning "Health check failed, initiating rollback..."
                    "$SCRIPT_DIR/../rollback/rollback-runner.sh" \
                        --project "$PROJECT_NAME" \
                        --env "$ENVIRONMENT" \
                        --reason "health_check_failure" \
                        --automatic
                fi

                return 1
            fi

            sleep 10
            ((attempt++))
        done

        # Run performance validation
        log_progress "Running performance validation..."
        local response_time=$(curl -o /dev/null -s -w '%{time_total}' "${service_url}/health" 2>/dev/null || echo "999")

        log_info "Response time: ${response_time}s"

        # Check if response time is acceptable (configurable threshold)
        local max_response_time="5.0"
        if (( $(echo "${response_time} > ${max_response_time}" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "Response time ${response_time}s exceeds threshold ${max_response_time}s"

            if [[ "$ENVIRONMENT" == "prod" ]] && [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
                log_warning "Performance degradation in production, considering rollback..."
            fi
        fi
    fi

    log_success "Post-deployment validation completed"
}

# Create deployment record
create_deployment_record() {
    log_info "Creating deployment record..."

    mkdir -p "$DEPLOYMENT_RECORD_DIR"

    local record_file="$DEPLOYMENT_RECORD_DIR/${DEPLOYMENT_ID}.json"
    local git_sha=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    local git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

    cat > "$record_file" << EOF
{
  "id": "$DEPLOYMENT_ID",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_name": "$PROJECT_NAME",
  "project_type": "$PROJECT_TYPE",
  "environment": "$ENVIRONMENT",
  "gcp_project": "$GCP_PROJECT",
  "region": "$REGION",
  "deployment_strategy": "$DEPLOYMENT_STRATEGY",
  "image_tag": "${IMAGE_TAG:-}",
  "image_url": "${IMAGE_URL:-}",
  "git_sha": "$git_sha",
  "git_branch": "$git_branch",
  "deployed_by": "${USER:-unknown}",
  "status": "successful",
  "validation_results": {
    "pre_deployment": "passed",
    "post_deployment": "passed"
  },
  "rollback_available": true
}
EOF

    log_success "Deployment record created: $record_file"
}

# Send deployment notifications
send_notifications() {
    log_info "Sending deployment notifications..."

    # GitHub deployment status (if in GitHub Actions)
    if [[ -n "${GITHUB_REPOSITORY:-}" ]] && command -v gh &> /dev/null; then
        gh api repos/:owner/:repo/deployments \
            --method POST \
            -f ref="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
            -f environment="$ENVIRONMENT" \
            -f description="Deployment $DEPLOYMENT_ID successful" \
            2>/dev/null || log_debug "GitHub deployment notification failed"
    fi

    # Slack notification (if webhook configured)
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local service_url=""
        if [[ "$PROJECT_TYPE" != "infrastructure" ]]; then
            service_url=$(gcloud run services describe "$PROJECT_NAME" \
                --region="$REGION" \
                --project="$GCP_PROJECT" \
                --format="value(status.url)" 2>/dev/null || echo "")
        fi

        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"text\": \"🚀 Deployment Successful\",
                \"blocks\": [
                    {
                        \"type\": \"section\",
                        \"text\": {
                            \"type\": \"mrkdwn\",
                            \"text\": \"*$PROJECT_NAME* deployed to *$ENVIRONMENT*\"
                        }
                    },
                    {
                        \"type\": \"section\",
                        \"fields\": [
                            {
                                \"type\": \"mrkdwn\",
                                \"text\": \"*Strategy:*\\n$DEPLOYMENT_STRATEGY\"
                            },
                            {
                                \"type\": \"mrkdwn\",
                                \"text\": \"*Environment:*\\n$ENVIRONMENT\"
                            }
                        ]
                    }
                ]
            }" \
            "$SLACK_WEBHOOK_URL" || log_debug "Slack notification failed"
    fi

    log_success "Deployment notifications sent"
}

# Show deployment summary
show_deployment_summary() {
    local service_url=""
    if [[ "$PROJECT_TYPE" != "infrastructure" ]]; then
        service_url=$(gcloud run services describe "$PROJECT_NAME" \
            --region="$REGION" \
            --project="$GCP_PROJECT" \
            --format="value(status.url)" 2>/dev/null || echo "Not available")
    fi

    echo ""
    echo "======================================"
    log_success "Deployment Completed Successfully!"
    echo "======================================"
    echo "Project: $PROJECT_NAME"
    echo "Environment: $ENVIRONMENT"
    echo "Strategy: $DEPLOYMENT_STRATEGY"
    echo "GCP Project: $GCP_PROJECT"
    echo "Region: $REGION"
    echo "Deployment ID: $DEPLOYMENT_ID"
    if [[ -n "$service_url" ]] && [[ "$service_url" != "Not available" ]]; then
        echo "Service URL: $service_url"
    fi
    echo "======================================"
    echo ""
    echo "Next steps:"
    echo "  • Monitor deployment: deploy-orchestrator monitor --project $PROJECT_NAME --env $ENVIRONMENT"
    echo "  • View logs: deploy-orchestrator logs --project $PROJECT_NAME --env $ENVIRONMENT"
    echo "  • Rollback if needed: deploy-orchestrator rollback --project $PROJECT_NAME --env $ENVIRONMENT"

    if [[ "$ENVIRONMENT" == "dev" ]]; then
        echo "  • Promote to test: deploy-orchestrator deploy --project $PROJECT_NAME --env test"
    elif [[ "$ENVIRONMENT" == "test" ]]; then
        echo "  • Promote to stage: deploy-orchestrator deploy --project $PROJECT_NAME --env stage"
    elif [[ "$ENVIRONMENT" == "stage" ]]; then
        echo "  • Promote to prod: deploy-orchestrator deploy --project $PROJECT_NAME --env prod"
    fi
    echo ""
}

# Main function
main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi

    parse_args "$@"

    # Validate required parameters
    if [[ -z "$PROJECT_NAME" ]]; then
        log_error "Project name is required (--project)"
        exit 1
    fi

    if [[ -z "$ENVIRONMENT" ]]; then
        log_error "Environment is required (--env)"
        exit 1
    fi

    # Load configuration
    load_config

    # Show deployment info
    log_info "Starting deployment of $PROJECT_NAME to $ENVIRONMENT"
    log_info "Strategy: $DEPLOYMENT_STRATEGY"
    log_info "GCP Project: $GCP_PROJECT"
    log_info "Region: $REGION"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN MODE - No actual deployment will occur"
    fi

    # Execute deployment pipeline
    validate_requirements
    run_pre_deployment_validation
    build_and_push_image
    execute_deployment_strategy

    if [[ "$DRY_RUN" != "true" ]]; then
        run_post_deployment_validation
        create_deployment_record
        send_notifications
        show_deployment_summary
    else
        log_info "DRY RUN completed - no actual deployment performed"
    fi
}

# Run main function
main "$@"
