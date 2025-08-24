#!/usr/bin/env bash
# Comprehensive Security Validation Framework
# Multi-layered security scanning for containers, infrastructure, and applications

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
log_progress() { echo -e "${CYAN}🔍 SCANNING: $1${NC}"; }
log_security() { echo -e "${PURPLE}🔒 SECURITY: $1${NC}"; }

# Configuration
SCAN_TYPE="${SCAN_TYPE:-all}"  # all, container, infrastructure, application, secrets
SEVERITY_THRESHOLD="${SEVERITY_THRESHOLD:-MEDIUM}"  # LOW, MEDIUM, HIGH, CRITICAL
FAIL_ON_HIGH="${FAIL_ON_HIGH:-true}"
FAIL_ON_CRITICAL="${FAIL_ON_CRITICAL:-true}"
OUTPUT_FORMAT="${OUTPUT_FORMAT:-json}"  # json, table, sarif
OUTPUT_DIR="${OUTPUT_DIR:-./security-reports}"
DRY_RUN="${DRY_RUN:-false}"

# GCP Configuration
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
IMAGE_URL="${IMAGE_URL:-}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Security tools configuration
TRIVY_VERSION="0.48.0"
GRYPE_VERSION="0.74.0"
SYFT_VERSION="0.95.0"
CHECKOV_VERSION="3.1.0"
SEMGREP_VERSION="1.45.0"

log_info "🔒 Starting Comprehensive Security Validation"
log_info "Scan Type: $SCAN_TYPE"
log_info "Severity Threshold: $SEVERITY_THRESHOLD"
log_info "Output Directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Initialize results tracking
declare -A scan_results
declare -A vulnerability_counts

# Function to install security tools
install_security_tools() {
    log_progress "Installing security scanning tools"

    # Install Trivy
    if ! command -v trivy &> /dev/null; then
        log_info "Installing Trivy..."
        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin v${TRIVY_VERSION}
    fi

    # Install Grype
    if ! command -v grype &> /dev/null; then
        log_info "Installing Grype..."
        curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin v${GRYPE_VERSION}
    fi

    # Install Syft
    if ! command -v syft &> /dev/null; then
        log_info "Installing Syft..."
        curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin v${SYFT_VERSION}
    fi

    # Install Checkov
    if ! command -v checkov &> /dev/null; then
        log_info "Installing Checkov..."
        pip3 install checkov==${CHECKOV_VERSION}
    fi

    # Install Semgrep
    if ! command -v semgrep &> /dev/null; then
        log_info "Installing Semgrep..."
        pip3 install semgrep==${SEMGREP_VERSION}
    fi

    # Install additional tools
    if ! command -v gitleaks &> /dev/null; then
        log_info "Installing Gitleaks..."
        curl -sSfL https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz | tar -xz -C /usr/local/bin
    fi

    log_success "Security tools installation completed"
}

# Container Image Security Scanning
scan_container_image() {
    if [[ "$SCAN_TYPE" != "all" && "$SCAN_TYPE" != "container" ]]; then
        return 0
    fi

    log_progress "Container image security scanning"

    if [[ -z "$IMAGE_URL" ]]; then
        log_warning "No image URL provided, skipping container scanning"
        return 0
    fi

    local full_image="${IMAGE_URL}:${IMAGE_TAG}"
    log_info "Scanning image: $full_image"

    # Trivy Container Scan
    log_security "Running Trivy container scan..."
    if [[ "$DRY_RUN" == "false" ]]; then
        trivy image \
            --format "$OUTPUT_FORMAT" \
            --output "$OUTPUT_DIR/trivy-container-report.json" \
            --severity "$SEVERITY_THRESHOLD,HIGH,CRITICAL" \
            --ignore-unfixed \
            "$full_image" || true

        # Parse Trivy results
        if [[ -f "$OUTPUT_DIR/trivy-container-report.json" ]]; then
            local critical_count=$(jq -r '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "$OUTPUT_DIR/trivy-container-report.json" 2>/dev/null || echo "0")
            local high_count=$(jq -r '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "$OUTPUT_DIR/trivy-container-report.json" 2>/dev/null || echo "0")
            local medium_count=$(jq -r '[.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM")] | length' "$OUTPUT_DIR/trivy-container-report.json" 2>/dev/null || echo "0")

            vulnerability_counts["trivy_critical"]=$critical_count
            vulnerability_counts["trivy_high"]=$high_count
            vulnerability_counts["trivy_medium"]=$medium_count

            log_info "Trivy results - Critical: $critical_count, High: $high_count, Medium: $medium_count"
        fi
    fi

    # Grype Container Scan
    log_security "Running Grype container scan..."
    if [[ "$DRY_RUN" == "false" ]]; then
        grype "$full_image" \
            -o json \
            --file "$OUTPUT_DIR/grype-container-report.json" || true

        # Parse Grype results
        if [[ -f "$OUTPUT_DIR/grype-container-report.json" ]]; then
            local critical_count=$(jq -r '[.matches[] | select(.vulnerability.severity == "Critical")] | length' "$OUTPUT_DIR/grype-container-report.json" 2>/dev/null || echo "0")
            local high_count=$(jq -r '[.matches[] | select(.vulnerability.severity == "High")] | length' "$OUTPUT_DIR/grype-container-report.json" 2>/dev/null || echo "0")

            vulnerability_counts["grype_critical"]=$critical_count
            vulnerability_counts["grype_high"]=$high_count

            log_info "Grype results - Critical: $critical_count, High: $high_count"
        fi
    fi

    # Container Configuration Analysis
    log_security "Analyzing container configuration..."
    if [[ "$DRY_RUN" == "false" ]] && [[ -f "Dockerfile" ]]; then
        # Dockerfile security best practices check
        cat > "$OUTPUT_DIR/dockerfile-security-check.txt" << 'EOF'
Dockerfile Security Analysis:
============================
EOF

        # Check for common security issues
        if grep -q "^USER root" Dockerfile 2>/dev/null; then
            echo "❌ Running as root user detected" >> "$OUTPUT_DIR/dockerfile-security-check.txt"
        fi

        if grep -q "ADD.*http" Dockerfile 2>/dev/null; then
            echo "⚠️ Using ADD with URLs detected" >> "$OUTPUT_DIR/dockerfile-security-check.txt"
        fi

        if ! grep -q "^USER " Dockerfile 2>/dev/null; then
            echo "⚠️ No explicit USER directive found" >> "$OUTPUT_DIR/dockerfile-security-check.txt"
        fi

        if grep -q "COPY.*--chown=root" Dockerfile 2>/dev/null; then
            echo "⚠️ Files copied with root ownership" >> "$OUTPUT_DIR/dockerfile-security-check.txt"
        fi

        log_info "Dockerfile security analysis completed"
    fi

    scan_results["container"]="completed"
    log_success "Container image security scanning completed"
}

# Infrastructure Security Scanning
scan_infrastructure() {
    if [[ "$SCAN_TYPE" != "all" && "$SCAN_TYPE" != "infrastructure" ]]; then
        return 0
    fi

    log_progress "Infrastructure security scanning"

    # Terraform Security with Checkov
    if [[ -d "terraform" ]] || find . -name "*.tf" -type f | head -1 > /dev/null; then
        log_security "Running Checkov on Terraform files..."
        if [[ "$DRY_RUN" == "false" ]]; then
            checkov -d . \
                --framework terraform \
                --output json \
                --output-file-path "$OUTPUT_DIR/checkov-terraform-report.json" \
                --soft-fail || true

            # Parse Checkov results
            if [[ -f "$OUTPUT_DIR/checkov-terraform-report.json" ]]; then
                local failed_checks=$(jq -r '.results.failed_checks | length' "$OUTPUT_DIR/checkov-terraform-report.json" 2>/dev/null || echo "0")
                local passed_checks=$(jq -r '.results.passed_checks | length' "$OUTPUT_DIR/checkov-terraform-report.json" 2>/dev/null || echo "0")

                vulnerability_counts["checkov_failed"]=$failed_checks
                vulnerability_counts["checkov_passed"]=$passed_checks

                log_info "Checkov results - Failed: $failed_checks, Passed: $passed_checks"
            fi
        fi
    fi

    # Trivy Infrastructure Scan
    log_security "Running Trivy on infrastructure files..."
    if [[ "$DRY_RUN" == "false" ]]; then
        trivy config . \
            --format "$OUTPUT_FORMAT" \
            --output "$OUTPUT_DIR/trivy-infrastructure-report.json" \
            --severity "$SEVERITY_THRESHOLD,HIGH,CRITICAL" || true

        # Parse Trivy config results
        if [[ -f "$OUTPUT_DIR/trivy-infrastructure-report.json" ]]; then
            local critical_count=$(jq -r '[.Results[]?.Misconfigurations[]? | select(.Severity == "CRITICAL")] | length' "$OUTPUT_DIR/trivy-infrastructure-report.json" 2>/dev/null || echo "0")
            local high_count=$(jq -r '[.Results[]?.Misconfigurations[]? | select(.Severity == "HIGH")] | length' "$OUTPUT_DIR/trivy-infrastructure-report.json" 2>/dev/null || echo "0")

            vulnerability_counts["trivy_config_critical"]=$critical_count
            vulnerability_counts["trivy_config_high"]=$high_count

            log_info "Trivy config results - Critical: $critical_count, High: $high_count"
        fi
    fi

    # GCP Security Analysis
    if [[ -n "$PROJECT_ID" ]]; then
        log_security "Analyzing GCP security configuration..."
        if [[ "$DRY_RUN" == "false" ]]; then
            # Check IAM policies
            gcloud projects get-iam-policy "$PROJECT_ID" --format=json > "$OUTPUT_DIR/gcp-iam-policy.json" 2>/dev/null || true

            # Check organization policies
            gcloud resource-manager org-policies list --project="$PROJECT_ID" --format=json > "$OUTPUT_DIR/gcp-org-policies.json" 2>/dev/null || true

            # Check for public resources
            cat > "$OUTPUT_DIR/gcp-security-analysis.txt" << 'EOF'
GCP Security Analysis:
=====================
EOF

            # Check for public storage buckets
            if gsutil ls -p "$PROJECT_ID" 2>/dev/null | while read -r bucket; do
                if gsutil iam get "$bucket" 2>/dev/null | grep -q "allUsers"; then
                    echo "⚠️ Public bucket found: $bucket" >> "$OUTPUT_DIR/gcp-security-analysis.txt"
                fi
            done; then
                echo "Storage bucket analysis completed" >> "$OUTPUT_DIR/gcp-security-analysis.txt"
            fi

            # Check for instances with public IPs
            gcloud compute instances list --project="$PROJECT_ID" \
                --format="json" > "$OUTPUT_DIR/gcp-compute-instances.json" 2>/dev/null || true

            log_info "GCP security analysis completed"
        fi
    fi

    scan_results["infrastructure"]="completed"
    log_success "Infrastructure security scanning completed"
}

# Application Security Scanning
scan_application() {
    if [[ "$SCAN_TYPE" != "all" && "$SCAN_TYPE" != "application" ]]; then
        return 0
    fi

    log_progress "Application security scanning"

    # Semgrep SAST Scan
    log_security "Running Semgrep SAST analysis..."
    if [[ "$DRY_RUN" == "false" ]]; then
        semgrep \
            --config=auto \
            --json \
            --output="$OUTPUT_DIR/semgrep-sast-report.json" \
            . || true

        # Parse Semgrep results
        if [[ -f "$OUTPUT_DIR/semgrep-sast-report.json" ]]; then
            local error_count=$(jq -r '[.results[] | select(.extra.severity == "ERROR")] | length' "$OUTPUT_DIR/semgrep-sast-report.json" 2>/dev/null || echo "0")
            local warning_count=$(jq -r '[.results[] | select(.extra.severity == "WARNING")] | length' "$OUTPUT_DIR/semgrep-sast-report.json" 2>/dev/null || echo "0")

            vulnerability_counts["semgrep_error"]=$error_count
            vulnerability_counts["semgrep_warning"]=$warning_count

            log_info "Semgrep results - Errors: $error_count, Warnings: $warning_count"
        fi
    fi

    # Language-specific dependency scanning
    if [[ -f "package.json" ]]; then
        log_security "Scanning Node.js dependencies..."
        if [[ "$DRY_RUN" == "false" ]]; then
            # NPM Audit
            npm audit --json > "$OUTPUT_DIR/npm-audit-report.json" 2>/dev/null || true

            # Parse npm audit results
            if [[ -f "$OUTPUT_DIR/npm-audit-report.json" ]]; then
                local critical_count=$(jq -r '.metadata.vulnerabilities.critical // 0' "$OUTPUT_DIR/npm-audit-report.json" 2>/dev/null || echo "0")
                local high_count=$(jq -r '.metadata.vulnerabilities.high // 0' "$OUTPUT_DIR/npm-audit-report.json" 2>/dev/null || echo "0")

                vulnerability_counts["npm_critical"]=$critical_count
                vulnerability_counts["npm_high"]=$high_count

                log_info "NPM audit results - Critical: $critical_count, High: $high_count"
            fi
        fi
    fi

    if [[ -f "requirements.txt" ]] || [[ -f "pyproject.toml" ]]; then
        log_security "Scanning Python dependencies..."
        if [[ "$DRY_RUN" == "false" ]]; then
            # Safety check
            if command -v safety &> /dev/null; then
                safety check --json --output "$OUTPUT_DIR/safety-report.json" || true
            else
                pip3 install safety
                safety check --json --output "$OUTPUT_DIR/safety-report.json" || true
            fi

            # Bandit SAST for Python
            if command -v bandit &> /dev/null; then
                bandit -r . -f json -o "$OUTPUT_DIR/bandit-report.json" || true
            else
                pip3 install bandit
                bandit -r . -f json -o "$OUTPUT_DIR/bandit-report.json" || true
            fi
        fi
    fi

    if [[ -f "go.mod" ]]; then
        log_security "Scanning Go dependencies..."
        if [[ "$DRY_RUN" == "false" ]]; then
            # Gosec for Go security
            if command -v gosec &> /dev/null; then
                gosec -fmt json -out "$OUTPUT_DIR/gosec-report.json" ./... || true
            fi

            # Go vulnerability check
            if command -v govulncheck &> /dev/null; then
                govulncheck -json ./... > "$OUTPUT_DIR/govulncheck-report.json" || true
            fi
        fi
    fi

    scan_results["application"]="completed"
    log_success "Application security scanning completed"
}

# Secrets Scanning
scan_secrets() {
    if [[ "$SCAN_TYPE" != "all" && "$SCAN_TYPE" != "secrets" ]]; then
        return 0
    fi

    log_progress "Secrets and sensitive data scanning"

    # Gitleaks Scan
    log_security "Running Gitleaks secrets scan..."
    if [[ "$DRY_RUN" == "false" ]]; then
        gitleaks detect \
            --source . \
            --report-format json \
            --report-path "$OUTPUT_DIR/gitleaks-report.json" \
            --verbose || true

        # Parse Gitleaks results
        if [[ -f "$OUTPUT_DIR/gitleaks-report.json" ]]; then
            local secrets_count=$(jq '. | length' "$OUTPUT_DIR/gitleaks-report.json" 2>/dev/null || echo "0")
            vulnerability_counts["secrets_found"]=$secrets_count

            log_info "Gitleaks results - Secrets found: $secrets_count"
        fi
    fi

    # Trivy Secrets Scan
    log_security "Running Trivy secrets scan..."
    if [[ "$DRY_RUN" == "false" ]]; then
        trivy fs \
            --scanners secret \
            --format "$OUTPUT_FORMAT" \
            --output "$OUTPUT_DIR/trivy-secrets-report.json" \
            . || true

        # Parse Trivy secrets results
        if [[ -f "$OUTPUT_DIR/trivy-secrets-report.json" ]]; then
            local secrets_count=$(jq -r '[.Results[]?.Secrets[]?] | length' "$OUTPUT_DIR/trivy-secrets-report.json" 2>/dev/null || echo "0")
            vulnerability_counts["trivy_secrets"]=$secrets_count

            log_info "Trivy secrets results - Secrets found: $secrets_count"
        fi
    fi

    # Custom secrets patterns
    log_security "Checking for custom secrets patterns..."
    if [[ "$DRY_RUN" == "false" ]]; then
        cat > "$OUTPUT_DIR/custom-secrets-check.txt" << 'EOF'
Custom Secrets Analysis:
=======================
EOF

        # Check for common secret patterns
        if grep -r "password\s*=" . --include="*.env" --include="*.conf" --include="*.config" 2>/dev/null; then
            echo "⚠️ Password configuration found in files" >> "$OUTPUT_DIR/custom-secrets-check.txt"
        fi

        if grep -r "api[_-]key" . --include="*.js" --include="*.py" --include="*.go" 2>/dev/null; then
            echo "⚠️ API key references found in code" >> "$OUTPUT_DIR/custom-secrets-check.txt"
        fi

        if find . -name "*.pem" -o -name "*.key" -o -name "*.p12" -o -name "*.jks" 2>/dev/null | head -5; then
            echo "⚠️ Certificate/key files found in repository" >> "$OUTPUT_DIR/custom-secrets-check.txt"
        fi

        log_info "Custom secrets analysis completed"
    fi

    scan_results["secrets"]="completed"
    log_success "Secrets scanning completed"
}

# License and Compliance Scanning
scan_compliance() {
    log_progress "License and compliance scanning"

    # Syft SBOM Generation
    if [[ -n "$IMAGE_URL" ]]; then
        log_security "Generating Software Bill of Materials (SBOM)..."
        if [[ "$DRY_RUN" == "false" ]]; then
            syft "${IMAGE_URL}:${IMAGE_TAG}" \
                -o spdx-json \
                --file "$OUTPUT_DIR/sbom-spdx.json" || true

            syft "${IMAGE_URL}:${IMAGE_TAG}" \
                -o cyclonedx-json \
                --file "$OUTPUT_DIR/sbom-cyclonedx.json" || true

            log_info "SBOM generation completed"
        fi
    fi

    # License analysis
    if [[ -f "package.json" ]]; then
        log_security "Analyzing Node.js licenses..."
        if [[ "$DRY_RUN" == "false" ]] && command -v license-checker &> /dev/null; then
            license-checker --json --out "$OUTPUT_DIR/nodejs-licenses.json" || true
        fi
    fi

    log_success "Compliance scanning completed"
}

# Generate comprehensive security report
generate_security_report() {
    log_progress "Generating comprehensive security report"

    local report_file="$OUTPUT_DIR/security-summary-report.json"
    local html_report="$OUTPUT_DIR/security-summary-report.html"

    # Create JSON summary
    cat > "$report_file" << EOF
{
  "scan_metadata": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "scan_type": "$SCAN_TYPE",
    "severity_threshold": "$SEVERITY_THRESHOLD",
    "project_id": "$PROJECT_ID",
    "image_url": "$IMAGE_URL",
    "image_tag": "$IMAGE_TAG"
  },
  "scan_results": $(printf '%s\n' "${!scan_results[@]}" | jq -R . | jq -s 'map(split(":") | {(.[0]): .[1]}) | add'),
  "vulnerability_counts": {
EOF

    # Add vulnerability counts
    local first=true
    for key in "${!vulnerability_counts[@]}"; do
        if [[ "$first" == "false" ]]; then
            echo "," >> "$report_file"
        fi
        echo "    \"$key\": ${vulnerability_counts[$key]}" >> "$report_file"
        first=false
    done

    cat >> "$report_file" << 'EOF'
  },
  "security_score": {
    "overall": "CALCULATING",
    "container": "CALCULATING",
    "infrastructure": "CALCULATING",
    "application": "CALCULATING",
    "secrets": "CALCULATING"
  }
}
EOF

    # Generate HTML report
    cat > "$html_report" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Security Scan Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 10px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .critical { background: #ffe6e6; border-color: #ff9999; }
        .high { background: #fff0e6; border-color: #ffcc99; }
        .medium { background: #fffce6; border-color: #ffeb99; }
        .low { background: #f0fff0; border-color: #ccffcc; }
        .success { background: #e6ffe6; border-color: #99ff99; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔒 Security Scan Report</h1>
        <p><strong>Timestamp:</strong> $(date -u +%Y-%m-%dT%H:%M:%SZ)</p>
        <p><strong>Scan Type:</strong> $SCAN_TYPE</p>
        <p><strong>Severity Threshold:</strong> $SEVERITY_THRESHOLD</p>
    </div>
EOF

    # Add vulnerability summary to HTML
    echo '<div class="section">' >> "$html_report"
    echo '<h2>📊 Vulnerability Summary</h2>' >> "$html_report"
    echo '<table>' >> "$html_report"
    echo '<tr><th>Tool/Category</th><th>Count</th><th>Type</th></tr>' >> "$html_report"

    for key in "${!vulnerability_counts[@]}"; do
        local severity_class="medium"
        if [[ "$key" == *"critical"* ]]; then
            severity_class="critical"
        elif [[ "$key" == *"high"* ]]; then
            severity_class="high"
        elif [[ "$key" == *"low"* ]]; then
            severity_class="low"
        fi

        echo "<tr class=\"$severity_class\"><td>$key</td><td>${vulnerability_counts[$key]}</td><td>${key##*_}</td></tr>" >> "$html_report"
    done

    echo '</table>' >> "$html_report"
    echo '</div>' >> "$html_report"
    echo '</body></html>' >> "$html_report"

    log_success "Security report generated: $report_file"
    log_success "HTML report generated: $html_report"
}

# Evaluate security findings and determine pass/fail
evaluate_security_findings() {
    log_progress "Evaluating security findings"

    local exit_code=0
    local critical_issues=0
    local high_issues=0

    # Count total critical and high severity issues
    for key in "${!vulnerability_counts[@]}"; do
        if [[ "$key" == *"critical"* ]]; then
            critical_issues=$((critical_issues + vulnerability_counts[$key]))
        elif [[ "$key" == *"high"* ]]; then
            high_issues=$((high_issues + vulnerability_counts[$key]))
        fi
    done

    log_info "Total Critical Issues: $critical_issues"
    log_info "Total High Issues: $high_issues"

    # Evaluate based on thresholds
    if [[ "$FAIL_ON_CRITICAL" == "true" && $critical_issues -gt 0 ]]; then
        log_error "Critical security issues found: $critical_issues"
        exit_code=1
    fi

    if [[ "$FAIL_ON_HIGH" == "true" && $high_issues -gt 5 ]]; then
        log_error "Too many high severity issues found: $high_issues (threshold: 5)"
        exit_code=1
    fi

    # Check for secrets
    local secrets_found=0
    if [[ -n "${vulnerability_counts[secrets_found]:-}" ]]; then
        secrets_found=${vulnerability_counts[secrets_found]}
    fi
    if [[ -n "${vulnerability_counts[trivy_secrets]:-}" ]]; then
        secrets_found=$((secrets_found + vulnerability_counts[trivy_secrets]))
    fi

    if [[ $secrets_found -gt 0 ]]; then
        log_error "Secrets detected in repository: $secrets_found"
        exit_code=1
    fi

    # Summary
    if [[ $exit_code -eq 0 ]]; then
        log_success "Security validation passed!"
        log_info "Summary: $critical_issues critical, $high_issues high, $secrets_found secrets"
    else
        log_error "Security validation failed!"
        log_error "Summary: $critical_issues critical, $high_issues high, $secrets_found secrets"
    fi

    return $exit_code
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --scan-type)
                SCAN_TYPE="$2"
                shift 2
                ;;
            --severity)
                SEVERITY_THRESHOLD="$2"
                shift 2
                ;;
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            --image-url)
                IMAGE_URL="$2"
                shift 2
                ;;
            --image-tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --scan-type TYPE     Scan type: all, container, infrastructure, application, secrets"
                echo "  --severity LEVEL     Severity threshold: LOW, MEDIUM, HIGH, CRITICAL"
                echo "  --output-dir DIR     Output directory for reports"
                echo "  --project-id ID      GCP Project ID"
                echo "  --image-url URL      Container image URL"
                echo "  --image-tag TAG      Container image tag"
                echo "  --dry-run           Dry run mode"
                echo "  --help              Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "🧪 Running in DRY RUN mode"
    fi

    # Install tools if not in dry run mode
    if [[ "$DRY_RUN" == "false" ]]; then
        install_security_tools
    fi

    # Execute scans based on type
    scan_container_image
    scan_infrastructure
    scan_application
    scan_secrets
    scan_compliance

    # Generate reports
    generate_security_report

    # Evaluate findings
    evaluate_security_findings
}

# Execute main function with all arguments
main "$@"
