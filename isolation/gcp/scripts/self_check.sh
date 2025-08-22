#!/usr/bin/env bash
# Self-Check - Comprehensive isolation validation and troubleshooting
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Validates and troubleshoots GCP isolation configuration

set -euo pipefail

# Script metadata
SELF_CHECK_VERSION="2.0.0"
SCRIPT_NAME="self_check.sh"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# Test results tracking
PASSED_TESTS=0
FAILED_TESTS=0
WARNING_TESTS=0
TOTAL_TESTS=0

# Logging functions
log_test() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    ((TOTAL_TESTS++))
    
    case "$status" in
        "PASS")
            ((PASSED_TESTS++))
            echo -e "${GREEN}✅ $test_name${NC}: $message"
            ;;
        "FAIL")
            ((FAILED_TESTS++))
            echo -e "${RED}❌ $test_name${NC}: $message"
            ;;
        "WARN")
            ((WARNING_TESTS++))
            echo -e "${YELLOW}⚠️  $test_name${NC}: $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  $test_name${NC}: $message"
            ;;
    esac
}

log_section() {
    echo ""
    echo -e "${CYAN}═══ $1 ═══${NC}"
}

print_banner() {
    echo -e "${PURPLE}"
    echo "══════════════════════════════════════════════════════"
    echo "🔍 ISOLATION SELF-CHECK v${SELF_CHECK_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "══════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Test 1: Environment Variables
test_environment_variables() {
    log_section "Environment Variables"
    
    # Critical environment variables
    if [[ -n "${CLOUDSDK_CONFIG:-}" ]]; then
        log_test "CLOUDSDK_CONFIG" "PASS" "$CLOUDSDK_CONFIG"
    else
        log_test "CLOUDSDK_CONFIG" "FAIL" "Not set - isolation not active"
        return 1
    fi
    
    if [[ -n "${PROJECT_ID:-}" ]]; then
        log_test "PROJECT_ID" "PASS" "$PROJECT_ID"
    else
        log_test "PROJECT_ID" "WARN" "Not set - may cause validation issues"
    fi
    
    if [[ -n "${ENVIRONMENT:-}" ]]; then
        log_test "ENVIRONMENT" "PASS" "$ENVIRONMENT"
    else
        log_test "ENVIRONMENT" "WARN" "Not set"
    fi
    
    if [[ -n "${REGION:-}" ]]; then
        log_test "REGION" "PASS" "$REGION"
    else
        log_test "REGION" "WARN" "Not set"
    fi
    
    # Optional but recommended
    if [[ -n "${DEPLOY_SA:-}" ]]; then
        log_test "DEPLOY_SA" "PASS" "$DEPLOY_SA"
    else
        log_test "DEPLOY_SA" "INFO" "Not configured (using user credentials)"
    fi
    
    if [[ -n "${WIF_PROVIDER:-}" ]]; then
        log_test "WIF_PROVIDER" "PASS" "$WIF_PROVIDER"
    else
        log_test "WIF_PROVIDER" "INFO" "Not configured (not using Workload Identity)"
    fi
}

# Test 2: Directory Structure
test_directory_structure() {
    log_section "Directory Structure"
    
    if [[ -d "$CLOUDSDK_CONFIG" ]]; then
        log_test "Isolation Directory" "PASS" "Exists at $CLOUDSDK_CONFIG"
        
        # Check permissions
        local perms
        perms=$(stat -c %a "$CLOUDSDK_CONFIG" 2>/dev/null || stat -f %A "$CLOUDSDK_CONFIG" 2>/dev/null || echo "unknown")
        if [[ "$perms" == "700" ]]; then
            log_test "Directory Permissions" "PASS" "Secure (700)"
        else
            log_test "Directory Permissions" "WARN" "Not secure ($perms) - should be 700"
        fi
    else
        log_test "Isolation Directory" "FAIL" "Does not exist at $CLOUDSDK_CONFIG"
        return 1
    fi
    
    # Check subdirectories
    local subdirs=("bin" "logs" "cache" "credentials")
    for subdir in "${subdirs[@]}"; do
        if [[ -d "$CLOUDSDK_CONFIG/$subdir" ]]; then
            log_test "Subdirectory $subdir" "PASS" "Exists"
        else
            log_test "Subdirectory $subdir" "WARN" "Missing"
        fi
    done
    
    # Check initialization marker
    if [[ -f "$CLOUDSDK_CONFIG/.initialized" ]]; then
        log_test "Initialization Marker" "PASS" "Present"
        
        # Read initialization details
        if [[ -r "$CLOUDSDK_CONFIG/.initialized" ]]; then
            local init_version init_date
            init_version=$(grep "SCRIPT_VERSION=" "$CLOUDSDK_CONFIG/.initialized" | cut -d= -f2 || echo "unknown")
            init_date=$(grep "INITIALIZED_AT=" "$CLOUDSDK_CONFIG/.initialized" | cut -d= -f2 || echo "unknown")
            log_test "Initialization Version" "INFO" "v$init_version (${init_date})"
        fi
    else
        log_test "Initialization Marker" "FAIL" "Missing - run bootstrap script"
    fi
}

# Test 3: GCloud Configuration
test_gcloud_configuration() {
    log_section "GCloud Configuration"
    
    # Check if gcloud is available
    if command -v gcloud >/dev/null 2>&1; then
        log_test "GCloud Binary" "PASS" "$(gcloud --version | head -1)"
    else
        log_test "GCloud Binary" "FAIL" "Not found in PATH"
        return 1
    fi
    
    # Check configurations
    if gcloud config configurations list --format="value(name)" 2>/dev/null | grep -qx "default"; then
        log_test "GCloud Configuration" "PASS" "Default configuration exists"
        
        # Check project setting
        local cfg_project
        cfg_project=$(gcloud config get-value core/project 2>/dev/null || echo "")
        if [[ -n "$cfg_project" ]]; then
            log_test "Configured Project" "PASS" "$cfg_project"
            
            # Validate against environment
            if [[ -n "${PROJECT_ID:-}" && "$cfg_project" != "$PROJECT_ID" ]]; then
                log_test "Project Consistency" "FAIL" "Mismatch: env=$PROJECT_ID, config=$cfg_project"
            else
                log_test "Project Consistency" "PASS" "Environment and config match"
            fi
        else
            log_test "Configured Project" "FAIL" "No project configured"
        fi
        
        # Check region setting
        local cfg_region
        cfg_region=$(gcloud config get-value compute/region 2>/dev/null || echo "")
        if [[ -n "$cfg_region" ]]; then
            log_test "Configured Region" "PASS" "$cfg_region"
        else
            log_test "Configured Region" "WARN" "No region configured"
        fi
        
        # Check service account impersonation
        local impersonate_sa
        impersonate_sa=$(gcloud config get-value auth/impersonate_service_account 2>/dev/null || echo "")
        if [[ -n "$impersonate_sa" ]]; then
            log_test "Service Account Impersonation" "PASS" "$impersonate_sa"
        else
            log_test "Service Account Impersonation" "INFO" "Not configured"
        fi
        
    else
        log_test "GCloud Configuration" "FAIL" "Default configuration does not exist"
    fi
}

# Test 4: Authentication
test_authentication() {
    log_section "Authentication"
    
    # Check for active authentication
    local active_accounts
    active_accounts=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || echo "")
    
    if [[ -n "$active_accounts" ]]; then
        log_test "Active Authentication" "PASS" "$active_accounts"
        
        # Test authentication validity
        if gcloud auth print-identity-token >/dev/null 2>&1 || gcloud auth print-access-token >/dev/null 2>&1; then
            log_test "Token Validity" "PASS" "Valid authentication token"
        else
            log_test "Token Validity" "WARN" "Cannot generate token - may need refresh"
        fi
    else
        log_test "Active Authentication" "FAIL" "No active authentication"
        log_test "Authentication Help" "INFO" "Run: gcloud auth login"
    fi
}

# Test 5: Project Access
test_project_access() {
    log_section "Project Access"
    
    local cfg_project
    cfg_project=$(gcloud config get-value core/project 2>/dev/null || echo "")
    
    if [[ -n "$cfg_project" ]]; then
        # Test project access
        if PROJECT_INFO=$(gcloud projects describe "$cfg_project" --format="value(projectId,lifecycleState)" 2>/dev/null); then
            local project_state
            project_state=$(echo "$PROJECT_INFO" | cut -d$'\t' -f2)
            
            if [[ "$project_state" == "ACTIVE" ]]; then
                log_test "Project Access" "PASS" "$cfg_project is accessible and active"
            else
                log_test "Project Access" "WARN" "$cfg_project is in state: $project_state"
            fi
            
            # Test basic API access
            if gcloud services list --enabled --limit=1 >/dev/null 2>&1; then
                log_test "API Access" "PASS" "Can list enabled services"
            else
                log_test "API Access" "WARN" "Cannot list services - check permissions"
            fi
            
        else
            log_test "Project Access" "FAIL" "Cannot access project $cfg_project"
        fi
    else
        log_test "Project Access" "FAIL" "No project configured"
    fi
}

# Test 6: Isolation Enforcement
test_isolation_enforcement() {
    log_section "Isolation Enforcement"
    
    # Check if guard script is in place
    if [[ -x "$CLOUDSDK_CONFIG/bin/gcloud" ]]; then
        log_test "Guard Script" "PASS" "Isolation guard is active"
        
        # Verify guard script content
        if grep -q "gcloud_guard.sh" "$CLOUDSDK_CONFIG/bin/gcloud" 2>/dev/null; then
            log_test "Guard Implementation" "PASS" "Using enhanced guard"
        else
            log_test "Guard Implementation" "WARN" "Using basic guard"
        fi
    else
        log_test "Guard Script" "FAIL" "No isolation guard found"
    fi
    
    # Check PATH isolation
    local gcloud_path
    gcloud_path=$(which gcloud 2>/dev/null || echo "")
    if [[ "$gcloud_path" == "$CLOUDSDK_CONFIG/bin/gcloud" ]]; then
        log_test "PATH Isolation" "PASS" "Using isolated gcloud"
    else
        log_test "PATH Isolation" "WARN" "System gcloud in use: $gcloud_path"
    fi
    
    # Check for project markers
    if [[ -f "$CLOUDSDK_CONFIG/.project" ]]; then
        local stored_project
        stored_project=$(cat "$CLOUDSDK_CONFIG/.project" 2>/dev/null || echo "")
        log_test "Project Marker" "PASS" "Stored: $stored_project"
    else
        log_test "Project Marker" "WARN" "Missing project marker"
    fi
}

# Test 7: Security Configuration
test_security_configuration() {
    log_section "Security Configuration"
    
    # Check production mode
    if [[ "${PRODUCTION_MODE:-false}" == "true" ]]; then
        log_test "Production Mode" "PASS" "Enabled - production safeguards active"
        
        # Check for production confirmation
        if [[ "${CONFIRM_PROD:-}" == "I_UNDERSTAND" ]]; then
            log_test "Production Confirmation" "WARN" "Currently set - destructive ops allowed"
        else
            log_test "Production Confirmation" "PASS" "Not set - destructive ops blocked"
        fi
    else
        log_test "Production Mode" "INFO" "Disabled - development environment"
    fi
    
    # Check audit logging
    if [[ "${AUDIT_ENABLED:-true}" == "true" ]]; then
        log_test "Audit Logging" "PASS" "Enabled"
        
        # Check if audit log exists and is recent
        local audit_log="$CLOUDSDK_CONFIG/logs/audit.log"
        if [[ -f "$audit_log" ]]; then
            local log_age
            log_age=$(find "$audit_log" -mtime -1 2>/dev/null | wc -l)
            if [[ "$log_age" -gt 0 ]]; then
                log_test "Audit Log Activity" "PASS" "Recent activity logged"
            else
                log_test "Audit Log Activity" "INFO" "No recent activity"
            fi
        else
            log_test "Audit Log Activity" "INFO" "No audit log yet"
        fi
    else
        log_test "Audit Logging" "WARN" "Disabled"
    fi
    
    # Check cost monitoring
    if [[ -f "$CLOUDSDK_CONFIG/cost-config.json" ]]; then
        local threshold
        threshold=$(jq -r '.threshold_usd // "unknown"' "$CLOUDSDK_CONFIG/cost-config.json" 2>/dev/null || echo "invalid")
        log_test "Cost Monitoring" "PASS" "Configured: \$${threshold} USD"
    else
        log_test "Cost Monitoring" "INFO" "Not configured"
    fi
}

# Test 8: Workload Identity Federation
test_workload_identity() {
    log_section "Workload Identity Federation"
    
    if [[ -f "$CLOUDSDK_CONFIG/wif-config.json" ]]; then
        local wif_provider wif_sa
        wif_provider=$(jq -r '.provider // "unknown"' "$CLOUDSDK_CONFIG/wif-config.json" 2>/dev/null || echo "invalid")
        wif_sa=$(jq -r '.service_account // "unknown"' "$CLOUDSDK_CONFIG/wif-config.json" 2>/dev/null || echo "invalid")
        
        log_test "WIF Configuration" "PASS" "Provider: $wif_provider"
        log_test "WIF Service Account" "PASS" "SA: $wif_sa"
        
        # Test WIF token exchange (if in CI environment)
        if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" || -n "${GITLAB_CI:-}" ]]; then
            if [[ -n "${GOOGLE_SERVICE_ACCOUNT_EMAIL:-}" ]]; then
                log_test "WIF CI Integration" "PASS" "CI environment detected with WIF"
            else
                log_test "WIF CI Integration" "WARN" "CI environment but no WIF setup"
            fi
        else
            log_test "WIF CI Integration" "INFO" "Not in CI environment"
        fi
    else
        log_test "WIF Configuration" "INFO" "Not configured"
    fi
}

# Test 9: Helper Scripts
test_helper_scripts() {
    log_section "Helper Scripts"
    
    local scripts=("gcloud" "self-check")
    for script in "${scripts[@]}"; do
        if [[ -x "$CLOUDSDK_CONFIG/bin/$script" ]]; then
            log_test "Helper Script: $script" "PASS" "Executable and available"
        else
            log_test "Helper Script: $script" "WARN" "Missing or not executable"
        fi
    done
}

# Test 10: Integration Tests
test_integration() {
    log_section "Integration Tests"
    
    # Test basic gcloud command through guard
    if timeout 10s gcloud config list >/dev/null 2>&1; then
        log_test "Basic Command" "PASS" "gcloud config list works"
    else
        log_test "Basic Command" "FAIL" "gcloud config list failed or timed out"
    fi
    
    # Test project listing (requires proper authentication)
    if timeout 15s gcloud projects list --limit=1 >/dev/null 2>&1; then
        log_test "Project Listing" "PASS" "Can list projects"
    else
        log_test "Project Listing" "WARN" "Cannot list projects - check permissions"
    fi
    
    # Test service listing in current project
    local cfg_project
    cfg_project=$(gcloud config get-value core/project 2>/dev/null || echo "")
    if [[ -n "$cfg_project" ]] && timeout 15s gcloud services list --enabled --limit=1 >/dev/null 2>&1; then
        log_test "Service Listing" "PASS" "Can list services in current project"
    else
        log_test "Service Listing" "WARN" "Cannot list services - check permissions"
    fi
}

# Generate recommendations based on test results
generate_recommendations() {
    log_section "Recommendations"
    
    if [[ $FAILED_TESTS -gt 0 ]]; then
        echo -e "${RED}Critical Issues Found:${NC}"
        echo "• Run: ./scripts/bootstrap_gcloud.sh"
        echo "• Ensure .envrc is sourced: direnv allow"
        echo "• Check authentication: gcloud auth login"
        echo ""
    fi
    
    if [[ $WARNING_TESTS -gt 0 ]]; then
        echo -e "${YELLOW}Warnings Found:${NC}"
        echo "• Review security configuration"
        echo "• Consider enabling missing features"
        echo "• Update permissions if needed"
        echo ""
    fi
    
    if [[ $FAILED_TESTS -eq 0 && $WARNING_TESTS -eq 0 ]]; then
        echo -e "${GREEN}✅ Excellent! No critical issues found.${NC}"
        echo "Your isolation configuration is working properly."
        echo ""
    fi
    
    echo -e "${WHITE}General Recommendations:${NC}"
    echo "• Keep isolation configuration up to date"
    echo "• Regularly run self-checks"
    echo "• Review audit logs periodically"
    echo "• Follow principle of least privilege"
}

# Print summary
print_summary() {
    log_section "Summary"
    
    echo -e "${WHITE}Test Results:${NC}"
    echo "• Total Tests:    $TOTAL_TESTS"
    echo -e "• Passed:         ${GREEN}$PASSED_TESTS${NC}"
    echo -e "• Failed:         ${RED}$FAILED_TESTS${NC}"
    echo -e "• Warnings:       ${YELLOW}$WARNING_TESTS${NC}"
    echo ""
    
    local success_rate
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
        echo "Success Rate: $success_rate%"
    fi
    
    echo ""
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}🎉 All critical tests passed! Isolation is working correctly.${NC}"
        exit 0
    else
        echo -e "${RED}⚠️  Some tests failed. Please address the issues above.${NC}"
        exit 1
    fi
}

# Troubleshooting mode
run_troubleshooting() {
    echo -e "${PURPLE}🔧 TROUBLESHOOTING MODE${NC}"
    echo ""
    
    echo "Common Issues and Solutions:"
    echo ""
    
    echo "1. CLOUDSDK_CONFIG not set:"
    echo "   • Run: direnv allow"
    echo "   • Or: source .envrc"
    echo ""
    
    echo "2. No gcloud configuration:"
    echo "   • Run: ./scripts/bootstrap_gcloud.sh"
    echo ""
    
    echo "3. Authentication issues:"
    echo "   • Run: gcloud auth login"
    echo "   • Or: gcloud auth application-default login"
    echo ""
    
    echo "4. Permission denied:"
    echo "   • Check project permissions"
    echo "   • Verify service account roles"
    echo "   • Contact project administrator"
    echo ""
    
    echo "5. Cross-project contamination:"
    echo "   • Delete ~/.gcloud/configurations"
    echo "   • Re-run bootstrap script"
    echo "   • Verify PROJECT_ID environment variable"
    echo ""
}

# Main execution
main() {
    local mode="${1:-check}"
    
    case "$mode" in
        "troubleshoot"|"trouble"|"t")
            print_banner
            run_troubleshooting
            ;;
        "check"|"c"|*)
            print_banner
            
            # Run all tests
            test_environment_variables || true
            test_directory_structure || true
            test_gcloud_configuration || true
            test_authentication || true
            test_project_access || true
            test_isolation_enforcement || true
            test_security_configuration || true
            test_workload_identity || true
            test_helper_scripts || true
            test_integration || true
            
            # Generate recommendations and summary
            generate_recommendations
            print_summary
            ;;
    esac
}

# Handle script arguments
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi