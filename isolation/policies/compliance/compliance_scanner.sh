#!/usr/bin/env bash
# Compliance Scanner - Automated compliance checking and reporting
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Performs automated compliance scans and generates reports

set -euo pipefail

# Script metadata
COMPLIANCE_SCANNER_VERSION="2.0.0"
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

# Configuration
COMPLIANCE_CONFIG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/compliance-config.json"
COMPLIANCE_REPORT_DIR="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/compliance-reports"
COMPLIANCE_LOG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/logs/compliance-scanner.log"

# Compliance frameworks
declare -A COMPLIANCE_FRAMEWORKS=(
    ["SOC2"]="SOC 2 Type II"
    ["HIPAA"]="Health Insurance Portability and Accountability Act"
    ["PCI-DSS"]="Payment Card Industry Data Security Standard"
    ["ISO27001"]="ISO/IEC 27001 Information Security Management"
    ["GDPR"]="General Data Protection Regulation"
    ["NIST"]="NIST Cybersecurity Framework"
    ["FedRAMP"]="Federal Risk and Authorization Management Program"
)

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "══════════════════════════════════════════════════════════"
    echo "🔍 COMPLIANCE SCANNER v${COMPLIANCE_SCANNER_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "══════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Initialize compliance configuration
init_compliance_config() {
    log_step "Initializing compliance configuration..."

    mkdir -p "$(dirname "$COMPLIANCE_CONFIG_FILE")"
    mkdir -p "$COMPLIANCE_REPORT_DIR"
    mkdir -p "$(dirname "$COMPLIANCE_LOG_FILE")"

    if [[ ! -f "$COMPLIANCE_CONFIG_FILE" ]]; then
        create_default_compliance_config
    fi

    log_success "Compliance configuration initialized"
}

# Create default compliance configuration
create_default_compliance_config() {
    cat > "$COMPLIANCE_CONFIG_FILE" <<EOF
{
    "version": "$COMPLIANCE_SCANNER_VERSION",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "frameworks": {
        "primary": "${COMPLIANCE_FRAMEWORK:-SOC2}",
        "additional": []
    },
    "scan_configuration": {
        "include_organization_policies": true,
        "include_iam_policies": true,
        "include_network_security": true,
        "include_data_encryption": true,
        "include_logging_monitoring": true,
        "include_backup_recovery": true,
        "include_access_controls": true,
        "include_vulnerability_management": true
    },
    "reporting": {
        "format": "json",
        "include_remediation": true,
        "include_evidence": true,
        "output_directory": "$COMPLIANCE_REPORT_DIR"
    },
    "thresholds": {
        "critical_finding_threshold": 0,
        "high_finding_threshold": 5,
        "medium_finding_threshold": 20
    },
    "notifications": {
        "email": "${COMPLIANCE_EMAIL:-}",
        "slack_webhook": "${SLACK_WEBHOOK:-}",
        "send_on_critical": true,
        "send_on_high": true,
        "send_summary": true
    },
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

# Load compliance configuration
load_compliance_config() {
    if [[ ! -f "$COMPLIANCE_CONFIG_FILE" ]]; then
        init_compliance_config
    fi

    PRIMARY_FRAMEWORK=$(jq -r '.frameworks.primary // "SOC2"' "$COMPLIANCE_CONFIG_FILE")
    PROJECT_ID=$(jq -r '.project_id // ""' "$COMPLIANCE_CONFIG_FILE")
    ENVIRONMENT=$(jq -r '.environment // ""' "$COMPLIANCE_CONFIG_FILE")
}

# Check organization policies compliance
check_organization_policies() {
    log_step "Checking organization policies compliance..."

    local findings=()
    local project_id="${PROJECT_ID:-}"

    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi

    # Check for required organization policies based on framework
    case "$PRIMARY_FRAMEWORK" in
        "SOC2"|"ISO27001")
            # Check encryption requirements
            check_policy_finding "constraints/storage.uniformBucketLevelAccess" "HIGH" "Storage uniform bucket level access required for SOC2/ISO27001" findings
            check_policy_finding "constraints/compute.requireShieldedVm" "MEDIUM" "Shielded VMs recommended for enhanced security" findings
            check_policy_finding "constraints/iam.disableServiceAccountKeyCreation" "HIGH" "Service account key creation should be disabled" findings
            ;;
        "HIPAA"|"PCI-DSS")
            # Check encryption and access controls
            check_policy_finding "constraints/storage.uniformBucketLevelAccess" "CRITICAL" "Storage uniform bucket level access required for HIPAA/PCI-DSS" findings
            check_policy_finding "constraints/compute.requireShieldedVm" "HIGH" "Shielded VMs required for HIPAA/PCI-DSS" findings
            check_policy_finding "constraints/iam.disableServiceAccountKeyCreation" "CRITICAL" "Service account key creation must be disabled" findings
            check_policy_finding "constraints/sql.requireSsl" "CRITICAL" "SSL required for database connections" findings
            ;;
        "GDPR")
            # Check data protection and privacy
            check_policy_finding "constraints/storage.publicAccessPrevention" "CRITICAL" "Public access prevention required for GDPR" findings
            check_policy_finding "constraints/gcp.resourceLocations" "HIGH" "Resource location restrictions required for GDPR" findings
            ;;
    esac

    echo "${findings[@]}"
}

# Check individual policy
check_policy_finding() {
    local constraint="$1"
    local severity="$2"
    local description="$3"
    local -n findings_ref="$4"

    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi

    # Check if policy exists and is enforced
    local policy_status="NOT_FOUND"
    if gcloud resource-manager org-policies describe "$constraint" \
        --project="$project_id" >/dev/null 2>&1; then

        local policy_data
        policy_data=$(gcloud resource-manager org-policies describe "$constraint" \
            --project="$project_id" --format="json" 2>/dev/null || echo '{}')

        if [[ -n "$policy_data" && "$policy_data" != "{}" ]]; then
            # Check if boolean policy is enforced
            local enforced
            enforced=$(echo "$policy_data" | jq -r '.booleanPolicy.enforced // false')

            if [[ "$enforced" == "true" ]]; then
                policy_status="COMPLIANT"
            else
                policy_status="NON_COMPLIANT"
            fi
        fi
    fi

    if [[ "$policy_status" != "COMPLIANT" ]]; then
        local finding
        finding=$(cat <<EOF
{
    "id": "$(echo "$constraint" | sed 's/[^a-zA-Z0-9]/_/g')_$(date +%s)",
    "category": "organization_policies",
    "constraint": "$constraint",
    "severity": "$severity",
    "status": "$policy_status",
    "description": "$description",
    "remediation": "Configure and enforce the organization policy constraint: $constraint",
    "framework": "$PRIMARY_FRAMEWORK",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)
        findings_ref+=("$finding")
    fi
}

# Check IAM policies compliance
check_iam_policies() {
    log_step "Checking IAM policies compliance..."

    local findings=()
    local project_id="${PROJECT_ID:-}"

    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi

    # Get IAM policy
    local iam_policy
    iam_policy=$(gcloud projects get-iam-policy "$project_id" --format="json" 2>/dev/null || echo '{}')

    # Check for overprivileged roles
    local privileged_roles=("roles/owner" "roles/editor" "roles/admin")
    for role in "${privileged_roles[@]}"; do
        local members
        members=$(echo "$iam_policy" | jq -r ".bindings[]? | select(.role == \"$role\") | .members[]?" 2>/dev/null || echo "")

        if [[ -n "$members" ]]; then
            while IFS= read -r member; do
                if [[ -n "$member" ]]; then
                    local finding
                    finding=$(cat <<EOF
{
    "id": "iam_overprivileged_$(echo "$role" | sed 's/[^a-zA-Z0-9]/_/g')_$(date +%s)",
    "category": "iam_policies",
    "role": "$role",
    "member": "$member",
    "severity": "HIGH",
    "description": "Overprivileged role assignment detected",
    "remediation": "Review and apply principle of least privilege for role: $role",
    "framework": "$PRIMARY_FRAMEWORK",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)
                    findings+=("$finding")
                fi
            done <<< "$members"
        fi
    done

    # Check for service accounts with keys
    local service_accounts
    service_accounts=$(gcloud iam service-accounts list --project="$project_id" --format="json" 2>/dev/null || echo '[]')

    while IFS= read -r sa_email; do
        if [[ -n "$sa_email" && "$sa_email" != "null" ]]; then
            local keys
            keys=$(gcloud iam service-accounts keys list --iam-account="$sa_email" \
                --project="$project_id" --format="json" 2>/dev/null || echo '[]')

            local key_count
            key_count=$(echo "$keys" | jq 'length // 0')

            if [[ "$key_count" -gt 1 ]]; then  # More than just the Google-managed key
                local finding
                finding=$(cat <<EOF
{
    "id": "iam_sa_keys_$(echo "$sa_email" | sed 's/[^a-zA-Z0-9]/_/g')_$(date +%s)",
    "category": "iam_policies",
    "service_account": "$sa_email",
    "key_count": $key_count,
    "severity": "MEDIUM",
    "description": "Service account has user-managed keys",
    "remediation": "Consider using Workload Identity Federation instead of service account keys",
    "framework": "$PRIMARY_FRAMEWORK",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)
                findings+=("$finding")
            fi
        fi
    done < <(echo "$service_accounts" | jq -r '.[].email // empty')

    echo "${findings[@]}"
}

# Check network security compliance
check_network_security() {
    log_step "Checking network security compliance..."

    local findings=()
    local project_id="${PROJECT_ID:-}"

    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi

    # Check firewall rules for overly permissive access
    local firewall_rules
    firewall_rules=$(gcloud compute firewall-rules list --project="$project_id" --format="json" 2>/dev/null || echo '[]')

    while IFS= read -r rule_data; do
        if [[ -n "$rule_data" && "$rule_data" != "null" ]]; then
            local rule_name direction source_ranges allowed
            rule_name=$(echo "$rule_data" | jq -r '.name')
            direction=$(echo "$rule_data" | jq -r '.direction // "INGRESS"')
            source_ranges=$(echo "$rule_data" | jq -r '.sourceRanges[]? // empty')
            allowed=$(echo "$rule_data" | jq -r '.allowed[]?.ports[]? // empty')

            # Check for rules allowing access from anywhere (0.0.0.0/0)
            if echo "$source_ranges" | grep -q "0.0.0.0/0" && [[ "$direction" == "INGRESS" ]]; then
                local finding
                finding=$(cat <<EOF
{
    "id": "network_overpermissive_$(echo "$rule_name" | sed 's/[^a-zA-Z0-9]/_/g')_$(date +%s)",
    "category": "network_security",
    "firewall_rule": "$rule_name",
    "direction": "$direction",
    "source_ranges": "0.0.0.0/0",
    "severity": "HIGH",
    "description": "Firewall rule allows access from anywhere",
    "remediation": "Restrict source ranges to specific IP addresses or ranges",
    "framework": "$PRIMARY_FRAMEWORK",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)
                findings+=("$finding")
            fi
        fi
    done < <(echo "$firewall_rules" | jq -c '.[]?')

    echo "${findings[@]}"
}

# Check data encryption compliance
check_data_encryption() {
    log_step "Checking data encryption compliance..."

    local findings=()
    local project_id="${PROJECT_ID:-}"

    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi

    # Check Cloud Storage buckets for encryption
    local buckets
    buckets=$(gcloud storage buckets list --project="$project_id" --format="json" 2>/dev/null || echo '[]')

    while IFS= read -r bucket_name; do
        if [[ -n "$bucket_name" && "$bucket_name" != "null" ]]; then
            # Check if bucket has public access (indicates potential data exposure)
            local bucket_iam
            bucket_iam=$(gcloud storage buckets get-iam-policy "gs://$bucket_name" --format="json" 2>/dev/null || echo '{}')

            local public_members
            public_members=$(echo "$bucket_iam" | jq -r '.bindings[]? | select(.members[]? | test("allUsers|allAuthenticatedUsers")) | .members[]?' 2>/dev/null || echo "")

            if [[ -n "$public_members" ]]; then
                local finding
                finding=$(cat <<EOF
{
    "id": "storage_public_access_$(echo "$bucket_name" | sed 's/[^a-zA-Z0-9]/_/g')_$(date +%s)",
    "category": "data_encryption",
    "bucket": "$bucket_name",
    "severity": "CRITICAL",
    "description": "Storage bucket has public access",
    "remediation": "Remove public access and enable uniform bucket-level access",
    "framework": "$PRIMARY_FRAMEWORK",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)
                findings+=("$finding")
            fi
        fi
    done < <(echo "$buckets" | jq -r '.[].name // empty')

    echo "${findings[@]}"
}

# Check logging and monitoring compliance
check_logging_monitoring() {
    log_step "Checking logging and monitoring compliance..."

    local findings=()
    local project_id="${PROJECT_ID:-}"

    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi

    # Check if audit logs are enabled
    local audit_config
    audit_config=$(gcloud logging sinks list --project="$project_id" --format="json" 2>/dev/null || echo '[]')

    local has_audit_sink=false
    while IFS= read -r sink_data; do
        if [[ -n "$sink_data" && "$sink_data" != "null" ]]; then
            local filter
            filter=$(echo "$sink_data" | jq -r '.filter // ""')

            if echo "$filter" | grep -q "protoPayload\|auditlog"; then
                has_audit_sink=true
                break
            fi
        fi
    done < <(echo "$audit_config" | jq -c '.[]?')

    if [[ "$has_audit_sink" == false ]]; then
        local finding
        finding=$(cat <<EOF
{
    "id": "logging_no_audit_sink_$(date +%s)",
    "category": "logging_monitoring",
    "severity": "HIGH",
    "description": "No audit log sink configured",
    "remediation": "Configure audit log sink for security monitoring",
    "framework": "$PRIMARY_FRAMEWORK",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)
        findings+=("$finding")
    fi

    echo "${findings[@]}"
}

# Generate compliance report
generate_compliance_report() {
    local scan_results="$1"
    local report_format="${2:-json}"

    log_step "Generating compliance report..."

    local timestamp
    timestamp=$(date -u +%Y%m%d_%H%M%S)
    local report_file="$COMPLIANCE_REPORT_DIR/compliance_report_${timestamp}.${report_format}"

    # Parse scan results
    local all_findings=()
    IFS=$'\n' read -d '' -r -a all_findings <<< "$scan_results" || true

    # Calculate statistics
    local total_findings="${#all_findings[@]}"
    local critical_count=0
    local high_count=0
    local medium_count=0
    local low_count=0

    for finding in "${all_findings[@]}"; do
        if [[ -n "$finding" ]]; then
            local severity
            severity=$(echo "$finding" | jq -r '.severity // "UNKNOWN"')

            case "$severity" in
                "CRITICAL") ((critical_count++)) ;;
                "HIGH") ((high_count++)) ;;
                "MEDIUM") ((medium_count++)) ;;
                "LOW") ((low_count++)) ;;
            esac
        fi
    done

    # Generate report
    case "$report_format" in
        "json")
            generate_json_report "$report_file" "$all_findings" "$total_findings" "$critical_count" "$high_count" "$medium_count" "$low_count"
            ;;
        "html")
            generate_html_report "$report_file" "$all_findings" "$total_findings" "$critical_count" "$high_count" "$medium_count" "$low_count"
            ;;
        "csv")
            generate_csv_report "$report_file" "$all_findings"
            ;;
    esac

    log_success "Compliance report generated: $report_file"
    echo "$report_file"
}

# Generate JSON report
generate_json_report() {
    local report_file="$1"
    local -n findings_ref="$2"
    local total="$3"
    local critical="$4"
    local high="$5"
    local medium="$6"
    local low="$7"

    local findings_json="[]"
    if [[ "${#findings_ref[@]}" -gt 0 ]]; then
        printf '%s\n' "${findings_ref[@]}" | jq -s '.' > /tmp/findings.json
        findings_json=$(cat /tmp/findings.json)
        rm -f /tmp/findings.json
    fi

    cat > "$report_file" <<EOF
{
    "metadata": {
        "scan_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "scanner_version": "$COMPLIANCE_SCANNER_VERSION",
        "project_id": "${PROJECT_ID:-}",
        "environment": "${ENVIRONMENT:-}",
        "compliance_framework": "$PRIMARY_FRAMEWORK",
        "report_id": "$(uuidgen 2>/dev/null || date +%s)"
    },
    "summary": {
        "total_findings": $total,
        "critical_findings": $critical,
        "high_findings": $high,
        "medium_findings": $medium,
        "low_findings": $low,
        "compliance_score": $(( (100 - critical * 25 - high * 10 - medium * 5 - low * 1) > 0 ? (100 - critical * 25 - high * 10 - medium * 5 - low * 1) : 0 ))
    },
    "findings": $findings_json,
    "recommendations": {
        "immediate_action_required": $(( critical > 0 ? true : false )),
        "priority_areas": [
            $(if [[ $critical -gt 0 ]]; then echo '"Critical security issues"'; fi)
            $(if [[ $high -gt 0 ]]; then echo '$(if [[ $critical -gt 0 ]]; then echo ","; fi)"High-priority compliance gaps"'; fi)
        ]
    }
}
EOF
}

# Generate HTML report
generate_html_report() {
    local report_file="$1"
    local -n findings_ref="$2"
    local total="$3"
    local critical="$4"
    local high="$5"
    local medium="$6"
    local low="$7"

    cat > "${report_file%.json}.html" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>Compliance Report - $PRIMARY_FRAMEWORK</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; }
        .summary { margin: 20px 0; }
        .finding { margin: 10px 0; padding: 10px; border-left: 4px solid #ccc; }
        .critical { border-left-color: #d32f2f; }
        .high { border-left-color: #f57c00; }
        .medium { border-left-color: #fbc02d; }
        .low { border-left-color: #388e3c; }
        .stats { display: flex; gap: 20px; }
        .stat { background: #f9f9f9; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Compliance Report: $PRIMARY_FRAMEWORK</h1>
        <p>Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)</p>
        <p>Project: ${PROJECT_ID:-}</p>
        <p>Environment: ${ENVIRONMENT:-}</p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <div class="stats">
            <div class="stat">Total Findings: $total</div>
            <div class="stat">Critical: $critical</div>
            <div class="stat">High: $high</div>
            <div class="stat">Medium: $medium</div>
            <div class="stat">Low: $low</div>
        </div>
    </div>

    <div class="findings">
        <h2>Findings</h2>
EOF

    for finding in "${findings_ref[@]}"; do
        if [[ -n "$finding" ]]; then
            local severity description remediation category
            severity=$(echo "$finding" | jq -r '.severity // "UNKNOWN"')
            description=$(echo "$finding" | jq -r '.description // "No description"')
            remediation=$(echo "$finding" | jq -r '.remediation // "No remediation provided"')
            category=$(echo "$finding" | jq -r '.category // "Unknown"')

            cat >> "${report_file%.json}.html" <<EOF
        <div class="finding ${severity,,}">
            <h3>$category - $severity</h3>
            <p><strong>Description:</strong> $description</p>
            <p><strong>Remediation:</strong> $remediation</p>
        </div>
EOF
        fi
    done

    cat >> "${report_file%.json}.html" <<EOF
    </div>
</body>
</html>
EOF
}

# Generate CSV report
generate_csv_report() {
    local report_file="$1"
    local -n findings_ref="$2"

    echo "Category,Severity,Description,Remediation,Framework,Timestamp" > "${report_file%.json}.csv"

    for finding in "${findings_ref[@]}"; do
        if [[ -n "$finding" ]]; then
            local category severity description remediation framework timestamp
            category=$(echo "$finding" | jq -r '.category // "Unknown"')
            severity=$(echo "$finding" | jq -r '.severity // "UNKNOWN"')
            description=$(echo "$finding" | jq -r '.description // "No description"' | sed 's/,/;/g')
            remediation=$(echo "$finding" | jq -r '.remediation // "No remediation"' | sed 's/,/;/g')
            framework=$(echo "$finding" | jq -r '.framework // "Unknown"')
            timestamp=$(echo "$finding" | jq -r '.timestamp // ""')

            echo "\"$category\",\"$severity\",\"$description\",\"$remediation\",\"$framework\",\"$timestamp\"" >> "${report_file%.json}.csv"
        fi
    done
}

# Run full compliance scan
run_compliance_scan() {
    local framework="${1:-$PRIMARY_FRAMEWORK}"
    local report_format="${2:-json}"

    log_step "Starting compliance scan for framework: $framework"

    # Initialize
    load_compliance_config

    # Collect all findings
    local all_findings=""

    # Run individual checks
    local org_policy_findings iam_findings network_findings encryption_findings logging_findings
    org_policy_findings=$(check_organization_policies)
    iam_findings=$(check_iam_policies)
    network_findings=$(check_network_security)
    encryption_findings=$(check_data_encryption)
    logging_findings=$(check_logging_monitoring)

    # Combine all findings
    all_findings=$(printf '%s\n%s\n%s\n%s\n%s\n' \
        "$org_policy_findings" \
        "$iam_findings" \
        "$network_findings" \
        "$encryption_findings" \
        "$logging_findings" | \
        grep -v '^$')

    # Generate report
    local report_file
    report_file=$(generate_compliance_report "$all_findings" "$report_format")

    # Log scan completion
    log_compliance_scan "$framework" "$report_file"

    log_success "Compliance scan completed: $report_file"
    echo "$report_file"
}

# Log compliance scan
log_compliance_scan() {
    local framework="$1"
    local report_file="$2"

    local log_entry
    log_entry=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "operation": "compliance_scan",
    "framework": "$framework",
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "report_file": "$report_file",
    "scanner_version": "$COMPLIANCE_SCANNER_VERSION",
    "user": "${USER:-unknown}"
}
EOF
)

    mkdir -p "$(dirname "$COMPLIANCE_LOG_FILE")"
    echo "$log_entry" >> "$COMPLIANCE_LOG_FILE"
}

# Show compliance dashboard
show_compliance_dashboard() {
    echo -e "${CYAN}═══ COMPLIANCE DASHBOARD ═══${NC}"
    echo ""

    load_compliance_config

    echo -e "${WHITE}Current Configuration:${NC}"
    echo "Framework: $PRIMARY_FRAMEWORK"
    echo "Project: ${PROJECT_ID:-unknown}"
    echo "Environment: ${ENVIRONMENT:-unknown}"
    echo ""

    echo -e "${WHITE}Available Frameworks:${NC}"
    for framework in "${!COMPLIANCE_FRAMEWORKS[@]}"; do
        echo "• $framework - ${COMPLIANCE_FRAMEWORKS[$framework]}"
    done
    echo ""

    echo -e "${WHITE}Recent Reports:${NC}"
    if [[ -d "$COMPLIANCE_REPORT_DIR" ]]; then
        find "$COMPLIANCE_REPORT_DIR" -name "*.json" -type f -exec basename {} \; | \
        sort -r | head -5 | while read -r report; do
            echo "• $report"
        done
    else
        echo "No reports found"
    fi
}

# Main function
main() {
    local command="${1:-dashboard}"

    case "$command" in
        "init")
            init_compliance_config
            ;;
        "scan")
            local framework="${2:-$PRIMARY_FRAMEWORK}"
            local format="${3:-json}"
            run_compliance_scan "$framework" "$format"
            ;;
        "dashboard"|"d")
            print_banner
            show_compliance_dashboard
            ;;
        "frameworks"|"f")
            print_banner
            echo -e "${WHITE}Supported Compliance Frameworks:${NC}"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            for framework in "${!COMPLIANCE_FRAMEWORKS[@]}"; do
                echo "• $framework - ${COMPLIANCE_FRAMEWORKS[$framework]}"
            done
            ;;
        "reports"|"r")
            local limit="${2:-10}"
            echo -e "${CYAN}Recent Compliance Reports:${NC}"
            if [[ -d "$COMPLIANCE_REPORT_DIR" ]]; then
                find "$COMPLIANCE_REPORT_DIR" -name "*.json" -type f -printf "%T@ %p\n" | \
                sort -nr | head -n "$limit" | while read -r timestamp filepath; do
                    local filename
                    filename=$(basename "$filepath")
                    local date_str
                    date_str=$(date -d "@${timestamp%.*}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "Unknown")
                    echo "• $filename ($date_str)"
                done
            else
                echo "No reports found"
            fi
            ;;
        "help"|"--help"|"-h")
            print_banner
            echo "Compliance Scanner v$COMPLIANCE_SCANNER_VERSION"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  init                     Initialize compliance configuration"
            echo "  scan [framework] [format] Run compliance scan"
            echo "  dashboard, d             Show compliance dashboard"
            echo "  frameworks, f            List supported frameworks"
            echo "  reports, r [limit]       Show recent reports"
            echo "  help                     Show this help"
            echo ""
            echo "Frameworks: ${!COMPLIANCE_FRAMEWORKS[*]}"
            echo "Formats: json, html, csv"
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
