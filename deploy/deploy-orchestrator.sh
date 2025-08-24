#!/usr/bin/env bash
# Universal Deployment Orchestrator
# Main entry point for all deployment operations

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
DEPLOY_CONFIG_FILE=".deploy-config.yaml"
DEPLOYMENT_RECORD_DIR=".deployments"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

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
log_debug() { [[ "$LOG_LEVEL" == "DEBUG" ]] && echo -e "${PURPLE}🔍 DEBUG: $1${NC}"; }

# Help function
show_help() {
    cat << EOF
Universal Deployment Orchestrator

USAGE:
    $(basename "$0") [COMMAND] [OPTIONS]

COMMANDS:
    init            Initialize deployment configuration
    validate        Run pre-deployment validation
    deploy          Execute deployment
    rollback        Rollback deployment
    status          Check deployment status
    history         Show deployment history
    pipeline        Generate CI/CD pipeline
    strategy        Configure deployment strategy
    monitor         Monitor deployment health
    logs            View deployment logs

GLOBAL OPTIONS:
    --project NAME      Project name
    --env ENV          Environment (dev/test/stage/prod)
    --config FILE      Configuration file (default: .deploy-config.yaml)
    --dry-run          Show what would be done
    --verbose          Enable verbose logging
    --help             Show this help

EXAMPLES:
    # Initialize new project deployment
    $(basename "$0") init --project my-app --type web-app

    # Deploy to development
    $(basename "$0") deploy --project my-app --env dev

    # Deploy with canary strategy
    $(basename "$0") deploy --project my-app --env prod --strategy canary --percent 10

    # Rollback to previous version
    $(basename "$0") rollback --project my-app --env prod --previous

    # Generate GitHub Actions pipeline
    $(basename "$0") pipeline github-actions --project my-app

    # Monitor deployment
    $(basename "$0") monitor --project my-app --env prod

EOF
}

# Parse global arguments
parse_global_args() {
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
            --config=*)
                DEPLOY_CONFIG_FILE="${1#*=}"
                shift
                ;;
            --config)
                DEPLOY_CONFIG_FILE="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --verbose)
                LOG_LEVEL="DEBUG"
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                # Pass through to command handler
                break
                ;;
        esac
    done
}

# Load configuration
load_config() {
    if [[ ! -f "$DEPLOY_CONFIG_FILE" ]]; then
        if [[ "$1" != "init" ]]; then
            log_error "Deployment configuration not found: $DEPLOY_CONFIG_FILE"
            log_info "Run 'deploy-orchestrator init' to create configuration"
            exit 1
        fi
        return
    fi

    # Parse YAML configuration (simplified - in production use yq)
    if command -v yq &> /dev/null; then
        PROJECT_NAME="${PROJECT_NAME:-$(yq e '.project.name' "$DEPLOY_CONFIG_FILE")}"
        PROJECT_TYPE="$(yq e '.project.type' "$DEPLOY_CONFIG_FILE")"
    else
        log_debug "yq not available, using basic parsing"
        PROJECT_NAME="${PROJECT_NAME:-$(grep "name:" "$DEPLOY_CONFIG_FILE" | head -1 | awk '{print $2}')}"
        PROJECT_TYPE="$(grep "type:" "$DEPLOY_CONFIG_FILE" | head -1 | awk '{print $2}')"
    fi

    log_debug "Loaded config: PROJECT_NAME=$PROJECT_NAME, PROJECT_TYPE=$PROJECT_TYPE"
}

# Validate environment
validate_environment() {
    local env="${1:-$ENVIRONMENT}"
    case "$env" in
        dev|development|test|stage|staging|prod|production)
            return 0
            ;;
        *)
            log_error "Invalid environment: $env"
            log_info "Valid environments: dev, test, stage, prod"
            return 1
            ;;
    esac
}

# Initialize deployment configuration
cmd_init() {
    local project_name=""
    local project_type=""
    local template_type=""

    # Parse init arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project=*)
                project_name="${1#*=}"
                shift
                ;;
            --project)
                project_name="$2"
                shift 2
                ;;
            --type=*)
                project_type="${1#*=}"
                shift
                ;;
            --type)
                project_type="$2"
                shift 2
                ;;
            --template=*)
                template_type="${1#*=}"
                shift
                ;;
            --template)
                template_type="$2"
                shift 2
                ;;
            *)
                log_error "Unknown init option: $1"
                exit 1
                ;;
        esac
    done

    # Interactive prompts if not provided
    if [[ -z "$project_name" ]]; then
        read -p "Project name: " project_name
    fi

    if [[ -z "$project_type" ]]; then
        echo "Select project type:"
        echo "  1) web-app      - Web application (Cloud Run/App Engine)"
        echo "  2) api          - API service (Cloud Run/Functions)"
        echo "  3) cli          - Command line tool"
        echo "  4) library      - Shared library"
        echo "  5) infrastructure - Terraform/Infrastructure"
        echo "  6) data-pipeline - Data processing pipeline"
        echo "  7) ml-model     - Machine learning model"
        echo "  8) microservice - Microservice (GKE/Cloud Run)"
        read -p "Choose type (1-8): " type_choice

        case $type_choice in
            1) project_type="web-app" ;;
            2) project_type="api" ;;
            3) project_type="cli" ;;
            4) project_type="library" ;;
            5) project_type="infrastructure" ;;
            6) project_type="data-pipeline" ;;
            7) project_type="ml-model" ;;
            8) project_type="microservice" ;;
            *) log_error "Invalid choice"; exit 1 ;;
        esac
    fi

    # Generate configuration
    log_info "Creating deployment configuration for $project_name ($project_type)"

    cat > "$DEPLOY_CONFIG_FILE" << EOF
# Universal Deployment Configuration
# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

project:
  name: $project_name
  type: $project_type
  version: "1.0.0"

# Environment configuration
environments:
  dev:
    gcp_project: ${project_name}-dev
    region: us-central1
    auto_deploy: true
    validation_level: basic
    rollback_strategy: manual

  test:
    gcp_project: ${project_name}-test
    region: us-central1
    auto_deploy: true
    validation_level: standard
    rollback_strategy: automatic

  stage:
    gcp_project: ${project_name}-stage
    region: us-central1
    auto_deploy: false
    validation_level: comprehensive
    require_approval: true
    rollback_strategy: automatic

  prod:
    gcp_project: ${project_name}-prod
    region: us-central1
    multi_region: false
    auto_deploy: false
    validation_level: maximum
    require_approval: true
    rollback_strategy: automatic
    monitoring_enabled: true

# Deployment strategies
strategies:
  default: rolling
  canary:
    enabled: true
    initial_percent: 10
    increment_percent: 25
    promotion_interval: "5m"
  blue_green:
    enabled: true
    health_check_path: "/health"
    cutover_delay: "2m"
  rolling:
    enabled: true
    max_unavailable: "25%"
    max_surge: "25%"

# Validation configuration
validation:
  security:
    enabled: true
    secret_scanning: true
    container_scanning: true
    policy_validation: true
  performance:
    enabled: true
    load_testing: false
    benchmark_testing: true
  compliance:
    enabled: false
    standards: []
  cost:
    enabled: true
    budget_threshold: 1000

# Rollback configuration
rollback:
  automatic:
    enabled: true
    triggers:
      - health_check_failure
      - error_rate_threshold
      - performance_degradation
    error_rate_threshold: 5.0
    response_time_threshold: 2000
  retention:
    deployment_history: 10
    backup_retention: "30d"

# Pipeline configuration
pipeline:
  platform: github-actions
  triggers:
    - push
    - pull_request
  notifications:
    slack:
      enabled: false
      webhook_url: ""
    email:
      enabled: false
      recipients: []

# Monitoring configuration
monitoring:
  enabled: true
  metrics:
    - deployment_frequency
    - lead_time
    - mttr
    - change_failure_rate
  alerts:
    deployment_failure: true
    rollback_executed: true
    validation_failure: true

# Security configuration
security:
  workload_identity: true
  secret_manager: true
  binary_authorization: false
  vulnerability_scanning: true
EOF

    log_success "Configuration created: $DEPLOY_CONFIG_FILE"

    # Create deployment directory
    mkdir -p "$DEPLOYMENT_RECORD_DIR"
    log_info "Created deployment record directory: $DEPLOYMENT_RECORD_DIR"

    # Initialize git hooks if git repo exists
    if [[ -d ".git" ]]; then
        log_info "Setting up git hooks for deployment validation"
        mkdir -p ".git/hooks"

        # Pre-commit hook
        cat > ".git/hooks/pre-commit" << 'EOF'
#!/bin/bash
# Auto-generated pre-commit hook for deployment validation
exec ./deploy/deploy-orchestrator.sh validate --env dev --pre-commit
EOF
        chmod +x ".git/hooks/pre-commit"
    fi

    log_success "Deployment system initialized for $project_name"
    echo ""
    echo "Next steps:"
    echo "  1. Review configuration: cat $DEPLOY_CONFIG_FILE"
    echo "  2. Generate CI/CD pipeline: ./deploy/deploy-orchestrator.sh pipeline github-actions"
    echo "  3. Deploy to dev: ./deploy/deploy-orchestrator.sh deploy --env dev"
}

# Validate deployment
cmd_validate() {
    local env="${ENVIRONMENT:-dev}"
    local pre_commit="false"
    local skip_validations=()

    # Parse validate arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --pre-commit)
                pre_commit="true"
                shift
                ;;
            --skip-validation)
                IFS=',' read -ra skip_validations <<< "$2"
                shift 2
                ;;
            *)
                log_error "Unknown validate option: $1"
                exit 1
                ;;
        esac
    done

    validate_environment "$env"

    log_info "Running deployment validation for $PROJECT_NAME ($env)"

    # Run validators
    local validation_failed="false"

    # Security validation
    if [[ ! " ${skip_validations[@]} " =~ " security " ]]; then
        log_info "Running security validation..."
        if ! "$SCRIPT_DIR/validators/security/run-security-validation.sh" --env "$env" --project "$PROJECT_NAME"; then
            validation_failed="true"
        fi
    fi

    # Performance validation
    if [[ ! " ${skip_validations[@]} " =~ " performance " ]]; then
        log_info "Running performance validation..."
        if ! "$SCRIPT_DIR/validators/performance/run-performance-validation.sh" --env "$env" --project "$PROJECT_NAME"; then
            validation_failed="true"
        fi
    fi

    # Infrastructure validation
    if [[ ! " ${skip_validations[@]} " =~ " infrastructure " ]]; then
        log_info "Running infrastructure validation..."
        if ! "$SCRIPT_DIR/validators/infrastructure/run-infrastructure-validation.sh" --env "$env" --project "$PROJECT_NAME"; then
            validation_failed="true"
        fi
    fi

    # Cost validation
    if [[ ! " ${skip_validations[@]} " =~ " cost " ]]; then
        log_info "Running cost validation..."
        if ! "$SCRIPT_DIR/validators/cost/run-cost-validation.sh" --env "$env" --project "$PROJECT_NAME"; then
            validation_failed="true"
        fi
    fi

    if [[ "$validation_failed" == "true" ]]; then
        log_error "Validation failed for $PROJECT_NAME ($env)"
        exit 1
    fi

    log_success "All validations passed for $PROJECT_NAME ($env)"
}

# Main command handler
main() {
    # Default values
    PROJECT_NAME=""
    ENVIRONMENT="dev"
    DRY_RUN="false"

    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi

    # Parse global arguments first
    local args=("$@")
    parse_global_args "${args[@]}"

    # Get command
    local command="$1"
    shift

    # Load configuration (except for init command)
    load_config "$command"

    # Execute command
    case "$command" in
        init)
            cmd_init "$@"
            ;;
        validate)
            cmd_validate "$@"
            ;;
        deploy)
            "$SCRIPT_DIR/strategies/deploy-runner.sh" "$@"
            ;;
        rollback)
            "$SCRIPT_DIR/rollback/rollback-runner.sh" "$@"
            ;;
        pipeline)
            "$SCRIPT_DIR/pipelines/pipeline-generator.sh" "$@"
            ;;
        strategy)
            "$SCRIPT_DIR/strategies/strategy-configurator.sh" "$@"
            ;;
        status|history|monitor|logs)
            "$SCRIPT_DIR/monitoring/deployment-monitor.sh" "$command" "$@"
            ;;
        help|--help)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
