#!/usr/bin/env bash
# Isolation Validator - Comprehensive validation and testing framework
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Validates isolation configuration across all cloud providers and environments

set -euo pipefail

# Script metadata
ISOLATION_VALIDATOR_VERSION="2.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Test results tracking
PASSED_TESTS=0
FAILED_TESTS=0
WARNING_TESTS=0
SKIPPED_TESTS=0
TOTAL_TESTS=0

# Configuration files
VALIDATION_CONFIG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/validation-config.json"
VALIDATION_REPORT_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/validation-reports/validation_$(date +%Y%m%d_%H%M%S).json"
VALIDATION_LOG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/logs/validation.log"

# Test categories
declare -A TEST_CATEGORIES=(
    ["environment"]="Environment Configuration Tests"
    ["credentials"]="Credential Management Tests"
    ["isolation"]="Isolation Boundary Tests"
    ["security"]="Security Configuration Tests"
    ["compliance"]="Compliance Framework Tests"
    ["integration"]="Integration Tests"
    ["performance"]="Performance Tests"
)

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "══════════════════════════════════════════════════════════════"
    echo "🔍 ISOLATION VALIDATOR v${ISOLATION_VALIDATOR_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "   Comprehensive Validation & Testing Framework"
    echo "══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Test result logging
log_test_result() {
    local test_name="$1"
    local category="$2"
    local status="$3"
    local message="$4"
    local details="${5:-}"

    ((TOTAL_TESTS++))

    case "$status" in
        "PASS")
            ((PASSED_TESTS++))
            echo -e "${GREEN}✅ [$category] $test_name${NC}: $message"
            ;;
        "FAIL")
            ((FAILED_TESTS++))
            echo -e "${RED}❌ [$category] $test_name${NC}: $message"
            if [[ -n "$details" ]]; then
                echo -e "${RED}   Details: $details${NC}"
            fi
            ;;
        "WARN")
            ((WARNING_TESTS++))
            echo -e "${YELLOW}⚠️  [$category] $test_name${NC}: $message"
            ;;
        "SKIP")
            ((SKIPPED_TESTS++))
            echo -e "${BLUE}⏭️  [$category] $test_name${NC}: $message"
            ;;
    esac

    # Log to file
    local log_entry
    log_entry=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "test_name": "$test_name",
    "category": "$category",
    "status": "$status",
    "message": "$message",
    "details": "$details",
    "validator_version": "$ISOLATION_VALIDATOR_VERSION"
}
EOF
)

    mkdir -p "$(dirname "$VALIDATION_LOG_FILE")"
    echo "$log_entry" >> "$VALIDATION_LOG_FILE"
}

# Initialize validation framework
init_validation_framework() {
    log_step "Initializing validation framework..."

    mkdir -p "$(dirname "$VALIDATION_CONFIG_FILE")"
    mkdir -p "$(dirname "$VALIDATION_REPORT_FILE")"
    mkdir -p "$(dirname "$VALIDATION_LOG_FILE")"

    if [[ ! -f "$VALIDATION_CONFIG_FILE" ]]; then
        create_default_validation_config
    fi

    log_success "Validation framework initialized"
}

# Create default validation configuration
create_default_validation_config() {
    cat > "$VALIDATION_CONFIG_FILE" <<EOF
{
    "version": "$ISOLATION_VALIDATOR_VERSION",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "test_categories": {
        "environment": {
            "enabled": true,
            "critical": true,
            "tests": [
                "environment_variables",
                "directory_structure",
                "configuration_files",
                "initialization_markers"
            ]
        },
        "credentials": {
            "enabled": true,
            "critical": true,
            "tests": [
                "gcp_authentication",
                "aws_authentication",
                "azure_authentication",
                "credential_isolation",
                "workload_identity"
            ]
        },
        "isolation": {
            "enabled": true,
            "critical": true,
            "tests": [
                "path_isolation",
                "config_isolation",
                "cross_contamination",
                "guard_scripts",
                "boundary_enforcement"
            ]
        },
        "security": {
            "enabled": true,
            "critical": true,
            "tests": [
                "permission_validation",
                "encryption_settings",
                "audit_logging",
                "access_controls",
                "production_safeguards"
            ]
        },
        "compliance": {
            "enabled": true,
            "critical": false,
            "tests": [
                "policy_compliance",
                "data_classification",
                "retention_policies",
                "reporting_requirements"
            ]
        },
        "integration": {
            "enabled": true,
            "critical": false,
            "tests": [
                "cli_integration",
                "terraform_integration",
                "ci_cd_integration",
                "monitoring_integration"
            ]
        },
        "performance": {
            "enabled": false,
            "critical": false,
            "tests": [
                "command_latency",
                "resource_usage",
                "scalability"
            ]
        }
    },
    "thresholds": {
        "critical_failure_threshold": 0,
        "warning_threshold": 5,
        "performance_timeout_seconds": 30
    },
    "reporting": {
        "format": "json",
        "include_details": true,
        "generate_html_report": true,
        "send_notifications": false
    },
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

# Run environment configuration tests
test_environment_configuration() {
    log_step "Running environment configuration tests..."

    # Test environment variables
    if [[ -n "${PROJECT_ID:-}" ]]; then
        log_test_result "PROJECT_ID_SET" "environment" "PASS" "PROJECT_ID environment variable is set"
    else
        log_test_result "PROJECT_ID_SET" "environment" "FAIL" "PROJECT_ID environment variable is not set"
    fi

    if [[ -n "${ENVIRONMENT:-}" ]]; then
        log_test_result "ENVIRONMENT_SET" "environment" "PASS" "ENVIRONMENT variable is set to: ${ENVIRONMENT}"
    else
        log_test_result "ENVIRONMENT_SET" "environment" "FAIL" "ENVIRONMENT variable is not set"
    fi

    # Test directory structure
    if [[ -n "${REPO_GCLOUD_HOME:-}" && -d "$REPO_GCLOUD_HOME" ]]; then
        log_test_result "ISOLATION_DIRECTORY" "environment" "PASS" "Isolation directory exists: $REPO_GCLOUD_HOME"

        # Check directory permissions
        local perms
        perms=$(stat -c %a "$REPO_GCLOUD_HOME" 2>/dev/null || stat -f %A "$REPO_GCLOUD_HOME" 2>/dev/null || echo "unknown")
        if [[ "$perms" == "700" ]]; then
            log_test_result "DIRECTORY_PERMISSIONS" "environment" "PASS" "Isolation directory has secure permissions (700)"
        else
            log_test_result "DIRECTORY_PERMISSIONS" "environment" "WARN" "Directory permissions are $perms (recommended: 700)"
        fi
    else
        log_test_result "ISOLATION_DIRECTORY" "environment" "FAIL" "Isolation directory not found or not set"
    fi

    # Test configuration files
    local config_files=(".envrc" "terraform.tfvars" "Makefile")
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            log_test_result "CONFIG_FILE_${config_file^^}" "environment" "PASS" "Configuration file exists: $config_file"
        else
            log_test_result "CONFIG_FILE_${config_file^^}" "environment" "WARN" "Configuration file missing: $config_file"
        fi
    done

    # Test initialization markers
    if [[ -n "${REPO_GCLOUD_HOME:-}" && -f "$REPO_GCLOUD_HOME/.initialized" ]]; then
        log_test_result "INITIALIZATION_MARKER" "environment" "PASS" "Initialization marker found"

        # Check marker content
        if grep -q "SCRIPT_VERSION=" "$REPO_GCLOUD_HOME/.initialized" 2>/dev/null; then
            local version
            version=$(grep "SCRIPT_VERSION=" "$REPO_GCLOUD_HOME/.initialized" | cut -d= -f2)
            log_test_result "MARKER_VERSION" "environment" "PASS" "Initialization version: $version"
        fi
    else
        log_test_result "INITIALIZATION_MARKER" "environment" "FAIL" "Initialization marker not found"
    fi
}

# Run credential management tests
test_credential_management() {
    log_step "Running credential management tests..."

    # Test GCP authentication
    if command -v gcloud >/dev/null 2>&1; then
        if gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
            local active_account
            active_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
            log_test_result "GCP_AUTHENTICATION" "credentials" "PASS" "GCP authenticated as: $active_account"
        else
            log_test_result "GCP_AUTHENTICATION" "credentials" "FAIL" "GCP not authenticated"
        fi
    else
        log_test_result "GCP_AUTHENTICATION" "credentials" "SKIP" "gcloud CLI not available"
    fi

    # Test AWS authentication
    if command -v aws >/dev/null 2>&1; then
        if aws sts get-caller-identity >/dev/null 2>&1; then
            local aws_identity
            aws_identity=$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null || echo "unknown")
            log_test_result "AWS_AUTHENTICATION" "credentials" "PASS" "AWS authenticated as: $aws_identity"
        else
            log_test_result "AWS_AUTHENTICATION" "credentials" "FAIL" "AWS not authenticated"
        fi
    else
        log_test_result "AWS_AUTHENTICATION" "credentials" "SKIP" "AWS CLI not available"
    fi

    # Test Azure authentication
    if command -v az >/dev/null 2>&1; then
        if az account show >/dev/null 2>&1; then
            local azure_user
            azure_user=$(az account show --query 'user.name' --output tsv 2>/dev/null || echo "unknown")
            log_test_result "AZURE_AUTHENTICATION" "credentials" "PASS" "Azure authenticated as: $azure_user"
        else
            log_test_result "AZURE_AUTHENTICATION" "credentials" "FAIL" "Azure not authenticated"
        fi
    else
        log_test_result "AZURE_AUTHENTICATION" "credentials" "SKIP" "Azure CLI not available"
    fi

    # Test credential isolation
    if [[ -n "${CLOUDSDK_CONFIG:-}" ]]; then
        log_test_result "CREDENTIAL_ISOLATION" "credentials" "PASS" "Credential isolation active (CLOUDSDK_CONFIG set)"
    else
        log_test_result "CREDENTIAL_ISOLATION" "credentials" "FAIL" "Credential isolation not active"
    fi

    # Test workload identity configuration
    if [[ -f "${REPO_GCLOUD_HOME:-$HOME/.gcloud}/wif-config.json" ]]; then
        log_test_result "WORKLOAD_IDENTITY" "credentials" "PASS" "Workload Identity configuration found"
    else
        log_test_result "WORKLOAD_IDENTITY" "credentials" "WARN" "No Workload Identity configuration found"
    fi
}

# Run isolation boundary tests
test_isolation_boundaries() {
    log_step "Running isolation boundary tests..."

    # Test PATH isolation
    if echo "$PATH" | grep -q "${REPO_GCLOUD_HOME:-/nonexistent}/bin"; then
        log_test_result "PATH_ISOLATION" "isolation" "PASS" "PATH includes isolation directory"
    else
        log_test_result "PATH_ISOLATION" "isolation" "WARN" "PATH isolation not detected"
    fi

    # Test configuration isolation
    if [[ "${CLOUDSDK_CONFIG:-}" == "${REPO_GCLOUD_HOME:-}" ]]; then
        log_test_result "CONFIG_ISOLATION" "isolation" "PASS" "Configuration isolation active"
    else
        log_test_result "CONFIG_ISOLATION" "isolation" "FAIL" "Configuration isolation not properly configured"
    fi

    # Test guard scripts
    if [[ -f "${REPO_GCLOUD_HOME:-/nonexistent}/bin/gcloud" ]]; then
        log_test_result "GUARD_SCRIPTS" "isolation" "PASS" "Guard scripts installed"

        # Test guard script functionality
        if [[ -x "${REPO_GCLOUD_HOME:-/nonexistent}/bin/gcloud" ]]; then
            log_test_result "GUARD_EXECUTABLE" "isolation" "PASS" "Guard script is executable"
        else
            log_test_result "GUARD_EXECUTABLE" "isolation" "FAIL" "Guard script not executable"
        fi
    else
        log_test_result "GUARD_SCRIPTS" "isolation" "FAIL" "Guard scripts not found"
    fi

    # Test cross-contamination prevention
    local system_gcloud_config="${HOME}/.config/gcloud"
    if [[ -d "$system_gcloud_config" && "${CLOUDSDK_CONFIG:-}" != "$system_gcloud_config" ]]; then
        log_test_result "CROSS_CONTAMINATION" "isolation" "PASS" "System config separated from isolation config"
    else
        log_test_result "CROSS_CONTAMINATION" "isolation" "WARN" "Potential cross-contamination risk"
    fi
}

# Run security configuration tests
test_security_configuration() {
    log_step "Running security configuration tests..."

    # Test production mode detection
    if [[ "${PRODUCTION_MODE:-false}" == "true" ]]; then
        log_test_result "PRODUCTION_MODE" "security" "PASS" "Production mode enabled"

        # Test production confirmations
        if [[ "${CONFIRM_PROD:-}" == "I_UNDERSTAND" ]]; then
            log_test_result "PRODUCTION_CONFIRMATION" "security" "WARN" "Production confirmation is set (destructive ops allowed)"
        else
            log_test_result "PRODUCTION_CONFIRMATION" "security" "PASS" "Production confirmation not set (safe)"
        fi
    else
        log_test_result "PRODUCTION_MODE" "security" "PASS" "Development/staging mode"
    fi

    # Test audit logging
    if [[ "${AUDIT_ENABLED:-true}" == "true" ]]; then
        log_test_result "AUDIT_LOGGING" "security" "PASS" "Audit logging enabled"

        # Check for audit logs
        if [[ -d "${REPO_GCLOUD_HOME:-/nonexistent}/logs" ]]; then
            log_test_result "AUDIT_LOG_DIRECTORY" "security" "PASS" "Audit log directory exists"
        else
            log_test_result "AUDIT_LOG_DIRECTORY" "security" "WARN" "Audit log directory not found"
        fi
    else
        log_test_result "AUDIT_LOGGING" "security" "WARN" "Audit logging disabled"
    fi

    # Test encryption settings
    local isolation_level="${ISOLATION_LEVEL:-standard}"
    case "$isolation_level" in
        "strict")
            log_test_result "ISOLATION_LEVEL" "security" "PASS" "Strict isolation level configured"
            ;;
        "standard")
            log_test_result "ISOLATION_LEVEL" "security" "PASS" "Standard isolation level configured"
            ;;
        "relaxed")
            log_test_result "ISOLATION_LEVEL" "security" "WARN" "Relaxed isolation level (consider strengthening)"
            ;;
        *)
            log_test_result "ISOLATION_LEVEL" "security" "FAIL" "Unknown isolation level: $isolation_level"
            ;;
    esac
}

# Run compliance tests
test_compliance_framework() {
    log_step "Running compliance framework tests..."

    # Test compliance framework detection
    if [[ -n "${COMPLIANCE_FRAMEWORK:-}" ]]; then
        log_test_result "COMPLIANCE_FRAMEWORK" "compliance" "PASS" "Compliance framework set: ${COMPLIANCE_FRAMEWORK}"
    else
        log_test_result "COMPLIANCE_FRAMEWORK" "compliance" "WARN" "No compliance framework specified"
    fi

    # Test data classification
    if [[ -n "${DATA_CLASSIFICATION:-}" ]]; then
        log_test_result "DATA_CLASSIFICATION" "compliance" "PASS" "Data classification set: ${DATA_CLASSIFICATION}"
    else
        log_test_result "DATA_CLASSIFICATION" "compliance" "WARN" "No data classification specified"
    fi

    # Test retention policies
    if [[ -n "${LOG_RETENTION_DAYS:-}" ]]; then
        local retention_days="${LOG_RETENTION_DAYS}"
        if [[ "$retention_days" -ge 365 ]]; then
            log_test_result "LOG_RETENTION" "compliance" "PASS" "Log retention configured: $retention_days days"
        else
            log_test_result "LOG_RETENTION" "compliance" "WARN" "Short log retention period: $retention_days days"
        fi
    else
        log_test_result "LOG_RETENTION" "compliance" "WARN" "No log retention policy specified"
    fi

    # Test compliance scanner
    if [[ -f "${SCRIPT_DIR}/../policies/compliance/compliance_scanner.sh" ]]; then
        log_test_result "COMPLIANCE_SCANNER" "compliance" "PASS" "Compliance scanner available"
    else
        log_test_result "COMPLIANCE_SCANNER" "compliance" "WARN" "Compliance scanner not found"
    fi
}

# Run integration tests
test_integration() {
    log_step "Running integration tests..."

    # Test CLI integration
    if command -v gcloud >/dev/null 2>&1; then
        if timeout 10s gcloud config list >/dev/null 2>&1; then
            log_test_result "GCLOUD_CLI" "integration" "PASS" "gcloud CLI integration working"
        else
            log_test_result "GCLOUD_CLI" "integration" "FAIL" "gcloud CLI integration failed"
        fi
    else
        log_test_result "GCLOUD_CLI" "integration" "SKIP" "gcloud CLI not available"
    fi

    # Test Terraform integration
    if command -v terraform >/dev/null 2>&1; then
        if [[ -f "main.tf" || -f "terraform/main.tf" ]]; then
            log_test_result "TERRAFORM_CONFIG" "integration" "PASS" "Terraform configuration found"

            # Test Terraform variables
            if [[ -n "${TF_VAR_project_id:-}" ]]; then
                log_test_result "TERRAFORM_VARS" "integration" "PASS" "Terraform variables configured"
            else
                log_test_result "TERRAFORM_VARS" "integration" "WARN" "Terraform variables not set"
            fi
        else
            log_test_result "TERRAFORM_CONFIG" "integration" "SKIP" "No Terraform configuration found"
        fi
    else
        log_test_result "TERRAFORM_CLI" "integration" "SKIP" "Terraform CLI not available"
    fi

    # Test CI/CD integration
    local ci_configs=(".github/workflows" ".gitlab-ci.yml" "azure-pipelines.yml" "Jenkinsfile")
    local ci_found=false
    for ci_config in "${ci_configs[@]}"; do
        if [[ -f "$ci_config" || -d "$ci_config" ]]; then
            log_test_result "CI_CD_CONFIG" "integration" "PASS" "CI/CD configuration found: $ci_config"
            ci_found=true
            break
        fi
    done

    if [[ "$ci_found" == false ]]; then
        log_test_result "CI_CD_CONFIG" "integration" "WARN" "No CI/CD configuration found"
    fi
}

# Run performance tests
test_performance() {
    log_step "Running performance tests..."

    # Test command latency
    if command -v gcloud >/dev/null 2>&1; then
        local start_time end_time duration
        start_time=$(date +%s.%N)
        gcloud config list >/dev/null 2>&1 || true
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "unknown")

        if [[ "$duration" != "unknown" ]] && (( $(echo "$duration < 5.0" | bc -l 2>/dev/null || echo 0) )); then
            log_test_result "COMMAND_LATENCY" "performance" "PASS" "gcloud command latency: ${duration}s"
        else
            log_test_result "COMMAND_LATENCY" "performance" "WARN" "High command latency: ${duration}s"
        fi
    else
        log_test_result "COMMAND_LATENCY" "performance" "SKIP" "gcloud CLI not available"
    fi

    # Test resource usage
    local isolation_size
    if [[ -d "${REPO_GCLOUD_HOME:-/nonexistent}" ]]; then
        isolation_size=$(du -sh "${REPO_GCLOUD_HOME}" 2>/dev/null | cut -f1 || echo "unknown")
        log_test_result "RESOURCE_USAGE" "performance" "PASS" "Isolation directory size: $isolation_size"
    else
        log_test_result "RESOURCE_USAGE" "performance" "FAIL" "Cannot measure resource usage"
    fi
}

# Generate validation report
generate_validation_report() {
    log_step "Generating validation report..."

    local report_data
    report_data=$(cat <<EOF
{
    "metadata": {
        "validation_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "validator_version": "$ISOLATION_VALIDATOR_VERSION",
        "project_id": "${PROJECT_ID:-unknown}",
        "environment": "${ENVIRONMENT:-unknown}",
        "isolation_level": "${ISOLATION_LEVEL:-unknown}",
        "production_mode": "${PRODUCTION_MODE:-false}"
    },
    "summary": {
        "total_tests": $TOTAL_TESTS,
        "passed_tests": $PASSED_TESTS,
        "failed_tests": $FAILED_TESTS,
        "warning_tests": $WARNING_TESTS,
        "skipped_tests": $SKIPPED_TESTS,
        "success_rate": $(( TOTAL_TESTS > 0 ? (PASSED_TESTS * 100) / TOTAL_TESTS : 0 )),
        "overall_status": "$(if [[ $FAILED_TESTS -eq 0 ]]; then echo "PASS"; else echo "FAIL"; fi)"
    },
    "test_categories": $(jq -n --argjson categories '{}' '$categories'),
    "recommendations": [],
    "next_steps": []
}
EOF
)

    # Add recommendations based on results
    if [[ $FAILED_TESTS -gt 0 ]]; then
        report_data=$(echo "$report_data" | jq '.recommendations += ["Address critical test failures before proceeding"]')
    fi

    if [[ $WARNING_TESTS -gt 0 ]]; then
        report_data=$(echo "$report_data" | jq '.recommendations += ["Review warning conditions and consider improvements"]')
    fi

    # Save report
    mkdir -p "$(dirname "$VALIDATION_REPORT_FILE")"
    echo "$report_data" > "$VALIDATION_REPORT_FILE"

    log_success "Validation report generated: $VALIDATION_REPORT_FILE"
}

# Print validation summary
print_validation_summary() {
    echo ""
    echo -e "${CYAN}═══ VALIDATION SUMMARY ═══${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${WHITE}Test Results:${NC}"
    echo "• Total Tests:    $TOTAL_TESTS"
    echo -e "• Passed:         ${GREEN}$PASSED_TESTS${NC}"
    echo -e "• Failed:         ${RED}$FAILED_TESTS${NC}"
    echo -e "• Warnings:       ${YELLOW}$WARNING_TESTS${NC}"
    echo -e "• Skipped:        ${BLUE}$SKIPPED_TESTS${NC}"

    if [[ $TOTAL_TESTS -gt 0 ]]; then
        local success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
        echo "• Success Rate:   $success_rate%"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}🎉 All critical validations passed!${NC}"
        echo "Your isolation configuration is working correctly."
    else
        echo -e "${RED}⚠️  Some validations failed. Please address the issues above.${NC}"
    fi

    echo ""
    echo -e "${WHITE}Validation Report:${NC} $VALIDATION_REPORT_FILE"
}

# Run full validation suite
run_full_validation() {
    local categories="${1:-all}"

    log_step "Starting comprehensive isolation validation..."

    # Initialize
    init_validation_framework

    # Reset counters
    PASSED_TESTS=0
    FAILED_TESTS=0
    WARNING_TESTS=0
    SKIPPED_TESTS=0
    TOTAL_TESTS=0

    # Run test categories
    if [[ "$categories" == "all" || "$categories" =~ environment ]]; then
        test_environment_configuration
    fi

    if [[ "$categories" == "all" || "$categories" =~ credentials ]]; then
        test_credential_management
    fi

    if [[ "$categories" == "all" || "$categories" =~ isolation ]]; then
        test_isolation_boundaries
    fi

    if [[ "$categories" == "all" || "$categories" =~ security ]]; then
        test_security_configuration
    fi

    if [[ "$categories" == "all" || "$categories" =~ compliance ]]; then
        test_compliance_framework
    fi

    if [[ "$categories" == "all" || "$categories" =~ integration ]]; then
        test_integration
    fi

    if [[ "$categories" == "all" || "$categories" =~ performance ]]; then
        test_performance
    fi

    # Generate report and summary
    generate_validation_report
    print_validation_summary

    # Return appropriate exit code
    if [[ $FAILED_TESTS -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

# Main function
main() {
    local command="${1:-validate}"

    case "$command" in
        "init")
            init_validation_framework
            ;;
        "validate")
            local categories="${2:-all}"
            print_banner
            run_full_validation "$categories"
            ;;
        "test")
            local category="${2:-environment}"
            print_banner
            case "$category" in
                "environment") test_environment_configuration ;;
                "credentials") test_credential_management ;;
                "isolation") test_isolation_boundaries ;;
                "security") test_security_configuration ;;
                "compliance") test_compliance_framework ;;
                "integration") test_integration ;;
                "performance") test_performance ;;
                *)
                    log_error "Unknown test category: $category"
                    echo "Available categories: ${!TEST_CATEGORIES[*]}"
                    exit 1
                    ;;
            esac
            print_validation_summary
            ;;
        "report")
            if [[ -f "$VALIDATION_REPORT_FILE" ]]; then
                cat "$VALIDATION_REPORT_FILE" | jq .
            else
                log_error "No validation report found. Run validation first."
                exit 1
            fi
            ;;
        "categories")
            echo -e "${WHITE}Available Test Categories:${NC}"
            for category in "${!TEST_CATEGORIES[@]}"; do
                echo "• $category - ${TEST_CATEGORIES[$category]}"
            done
            ;;
        "help"|"--help"|"-h")
            print_banner
            echo "Isolation Validator v$ISOLATION_VALIDATOR_VERSION"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  init                     Initialize validation framework"
            echo "  validate [categories]    Run full validation suite"
            echo "  test <category>          Run specific test category"
            echo "  report                   Show latest validation report"
            echo "  categories               List available test categories"
            echo "  help                     Show this help"
            echo ""
            echo "Categories: ${!TEST_CATEGORIES[*]}"
            echo ""
            echo "Examples:"
            echo "  $0 validate              # Run all tests"
            echo "  $0 validate security     # Run only security tests"
            echo "  $0 test credentials      # Test credential management"
            ;;
        *)
            log_error "Unknown command: $command"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Execute main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
