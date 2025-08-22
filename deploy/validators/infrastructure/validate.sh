#!/usr/bin/env bash
# Infrastructure Validation Framework
# Comprehensive validation for cloud infrastructure deployment

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
log_progress() { echo -e "${CYAN}🔍 VALIDATING: $1${NC}"; }
log_infra() { echo -e "${PURPLE}🏗️  INFRASTRUCTURE: $1${NC}"; }

# Configuration
VALIDATION_TYPE="${VALIDATION_TYPE:-all}"  # all, basic, advanced, compliance, cost
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
OUTPUT_DIR="${OUTPUT_DIR:-./infrastructure-reports}"
DRY_RUN="${DRY_RUN:-false}"

# Validation thresholds
MAX_COST_THRESHOLD="${MAX_COST_THRESHOLD:-1000}"  # Monthly cost in USD
CPU_UTILIZATION_THRESHOLD="${CPU_UTILIZATION_THRESHOLD:-80}"  # Percentage
DISK_UTILIZATION_THRESHOLD="${DISK_UTILIZATION_THRESHOLD:-85}"  # Percentage
NETWORK_EGRESS_THRESHOLD="${NETWORK_EGRESS_THRESHOLD:-100}"  # GB per month

log_info "🏗️ Starting Infrastructure Validation"
log_info "Validation Type: $VALIDATION_TYPE"
log_info "Project ID: $PROJECT_ID"
log_info "Region: $REGION"
log_info "Environment: $ENVIRONMENT"
log_info "Output Directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Initialize validation tracking
declare -A validation_results
declare -A resource_counts
declare -A cost_estimates

# Function to check prerequisites
check_prerequisites() {
    log_progress "Checking prerequisites"
    
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
    
    # Install additional tools if needed
    if ! command -v jq &> /dev/null; then
        log_info "Installing jq..."
        sudo apt-get update && sudo apt-get install -y jq || {
            log_error "Failed to install jq"
            exit 1
        }
    fi
    
    log_success "Prerequisites check completed"
}

# Basic project validation
validate_project_basics() {
    if [[ "$VALIDATION_TYPE" != "all" && "$VALIDATION_TYPE" != "basic" ]]; then
        return 0
    fi
    
    log_progress "Basic project validation"
    
    # Project information
    log_infra "Validating project information..."
    local project_info
    project_info=$(gcloud projects describe "$PROJECT_ID" --format=json)
    
    local project_state=$(echo "$project_info" | jq -r '.lifecycleState')
    local project_number=$(echo "$project_info" | jq -r '.projectNumber')
    local project_name=$(echo "$project_info" | jq -r '.name')
    
    if [[ "$project_state" != "ACTIVE" ]]; then
        log_error "Project is not in ACTIVE state: $project_state"
        validation_results["project_state"]="failed"
        return 1
    else
        log_success "Project is active"
        validation_results["project_state"]="passed"
    fi
    
    # Save project info
    echo "$project_info" > "$OUTPUT_DIR/project-info.json"
    
    # Check billing
    log_infra "Checking billing account..."
    local billing_info
    if billing_info=$(gcloud billing projects describe "$PROJECT_ID" --format=json 2>/dev/null); then
        local billing_enabled=$(echo "$billing_info" | jq -r '.billingEnabled')
        if [[ "$billing_enabled" == "true" ]]; then
            log_success "Billing is enabled"
            validation_results["billing"]="passed"
        else
            log_warning "Billing is not enabled"
            validation_results["billing"]="warning"
        fi
        echo "$billing_info" > "$OUTPUT_DIR/billing-info.json"
    else
        log_warning "Cannot access billing information"
        validation_results["billing"]="warning"
    fi
    
    # Check enabled APIs
    log_infra "Validating enabled APIs..."
    local enabled_apis
    enabled_apis=$(gcloud services list --enabled --format=json)
    echo "$enabled_apis" > "$OUTPUT_DIR/enabled-apis.json"
    
    local api_count=$(echo "$enabled_apis" | jq '. | length')
    resource_counts["enabled_apis"]=$api_count
    
    # Check for essential APIs
    local essential_apis=(
        "compute.googleapis.com"
        "container.googleapis.com"
        "cloudbuild.googleapis.com"
        "storage.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
    )
    
    local missing_apis=()
    for api in "${essential_apis[@]}"; do
        if echo "$enabled_apis" | jq -e --arg api "$api" '.[] | select(.name == $api)' > /dev/null; then
            log_success "Essential API enabled: $api"
        else
            log_warning "Essential API not enabled: $api"
            missing_apis+=("$api")
        fi
    done
    
    if [[ ${#missing_apis[@]} -eq 0 ]]; then
        validation_results["essential_apis"]="passed"
    else
        validation_results["essential_apis"]="warning"
        log_warning "Missing essential APIs: ${missing_apis[*]}"
    fi
    
    log_success "Basic project validation completed"
}

# Compute resources validation
validate_compute_resources() {
    if [[ "$VALIDATION_TYPE" != "all" && "$VALIDATION_TYPE" != "basic" && "$VALIDATION_TYPE" != "advanced" ]]; then
        return 0
    fi
    
    log_progress "Compute resources validation"
    
    # Compute Engine instances
    log_infra "Checking Compute Engine instances..."
    local instances
    instances=$(gcloud compute instances list --format=json 2>/dev/null || echo "[]")
    echo "$instances" > "$OUTPUT_DIR/compute-instances.json"
    
    local instance_count=$(echo "$instances" | jq '. | length')
    resource_counts["compute_instances"]=$instance_count
    log_info "Compute instances found: $instance_count"
    
    # Analyze instance configurations
    if [[ $instance_count -gt 0 ]]; then
        # Check for public IP addresses
        local public_instances
        public_instances=$(echo "$instances" | jq '[.[] | select(.networkInterfaces[].accessConfigs != null)]')
        local public_count=$(echo "$public_instances" | jq '. | length')
        
        if [[ $public_count -gt 0 ]]; then
            log_warning "$public_count instances have public IP addresses"
            validation_results["public_instances"]="warning"
        else
            log_success "No instances with public IP addresses"
            validation_results["public_instances"]="passed"
        fi
        
        # Check for proper machine types
        local oversized_instances
        oversized_instances=$(echo "$instances" | jq '[.[] | select(.machineType | contains("n1-highmem-16") or contains("n1-highcpu-32"))]')
        local oversized_count=$(echo "$oversized_instances" | jq '. | length')
        
        if [[ $oversized_count -gt 0 ]]; then
            log_warning "$oversized_count instances using large machine types"
            validation_results["machine_types"]="warning"
        else
            validation_results["machine_types"]="passed"
        fi
    fi
    
    # GKE clusters
    log_infra "Checking GKE clusters..."
    local clusters
    clusters=$(gcloud container clusters list --format=json 2>/dev/null || echo "[]")
    echo "$clusters" > "$OUTPUT_DIR/gke-clusters.json"
    
    local cluster_count=$(echo "$clusters" | jq '. | length')
    resource_counts["gke_clusters"]=$cluster_count
    log_info "GKE clusters found: $cluster_count"
    
    if [[ $cluster_count -gt 0 ]]; then
        # Check cluster configurations
        local private_clusters
        private_clusters=$(echo "$clusters" | jq '[.[] | select(.privateClusterConfig.enablePrivateNodes == true)]')
        local private_count=$(echo "$private_clusters" | jq '. | length')
        
        if [[ $private_count -eq $cluster_count ]]; then
            log_success "All GKE clusters are private"
            validation_results["private_clusters"]="passed"
        else
            log_warning "$((cluster_count - private_count)) GKE clusters are not private"
            validation_results["private_clusters"]="warning"
        fi
        
        # Check node pool configurations
        for cluster in $(echo "$clusters" | jq -r '.[].name'); do
            local node_pools
            node_pools=$(gcloud container node-pools list --cluster="$cluster" --region="$REGION" --format=json 2>/dev/null || echo "[]")
            echo "$node_pools" > "$OUTPUT_DIR/gke-nodepools-${cluster}.json"
            
            # Check for auto-scaling
            local autoscaling_pools
            autoscaling_pools=$(echo "$node_pools" | jq '[.[] | select(.autoscaling.enabled == true)]')
            local autoscaling_count=$(echo "$autoscaling_pools" | jq '. | length')
            local total_pools=$(echo "$node_pools" | jq '. | length')
            
            if [[ $autoscaling_count -eq $total_pools ]]; then
                log_success "All node pools in $cluster have auto-scaling enabled"
            else
                log_warning "$((total_pools - autoscaling_count)) node pools in $cluster don't have auto-scaling"
            fi
        done
    fi
    
    # Cloud Run services
    log_infra "Checking Cloud Run services..."
    local cloudrun_services
    cloudrun_services=$(gcloud run services list --region="$REGION" --format=json 2>/dev/null || echo "[]")
    echo "$cloudrun_services" > "$OUTPUT_DIR/cloudrun-services.json"
    
    local cloudrun_count=$(echo "$cloudrun_services" | jq '. | length')
    resource_counts["cloudrun_services"]=$cloudrun_count
    log_info "Cloud Run services found: $cloudrun_count"
    
    # Cloud Functions
    log_infra "Checking Cloud Functions..."
    local functions
    functions=$(gcloud functions list --format=json 2>/dev/null || echo "[]")
    echo "$functions" > "$OUTPUT_DIR/cloud-functions.json"
    
    local function_count=$(echo "$functions" | jq '. | length')
    resource_counts["cloud_functions"]=$function_count
    log_info "Cloud Functions found: $function_count"
    
    validation_results["compute_resources"]="completed"
    log_success "Compute resources validation completed"
}

# Storage and database validation
validate_storage_database() {
    if [[ "$VALIDATION_TYPE" != "all" && "$VALIDATION_TYPE" != "basic" && "$VALIDATION_TYPE" != "advanced" ]]; then
        return 0
    fi
    
    log_progress "Storage and database validation"
    
    # Cloud Storage buckets
    log_infra "Checking Cloud Storage buckets..."
    local buckets
    buckets=$(gsutil ls -L -b gs://** 2>/dev/null | grep -E "gs://|Created|Location|Storage class|Bucket Policy Only" || echo "")
    echo "$buckets" > "$OUTPUT_DIR/storage-buckets-raw.txt"
    
    local bucket_list
    bucket_list=$(gsutil ls 2>/dev/null || echo "")
    local bucket_count=$(echo "$bucket_list" | wc -l)
    resource_counts["storage_buckets"]=$((bucket_count - 1))  # Subtract 1 for empty line
    
    if [[ $bucket_count -gt 1 ]]; then
        log_info "Storage buckets found: $((bucket_count - 1))"
        
        # Check bucket permissions
        local public_buckets=()
        while IFS= read -r bucket; do
            if [[ -n "$bucket" ]]; then
                if gsutil iam get "$bucket" 2>/dev/null | grep -q "allUsers\|allAuthenticatedUsers"; then
                    public_buckets+=("$bucket")
                fi
            fi
        done <<< "$bucket_list"
        
        if [[ ${#public_buckets[@]} -gt 0 ]]; then
            log_warning "Public buckets found: ${public_buckets[*]}"
            validation_results["public_buckets"]="warning"
        else
            log_success "No public buckets found"
            validation_results["public_buckets"]="passed"
        fi
    fi
    
    # Cloud SQL instances
    log_infra "Checking Cloud SQL instances..."
    local sql_instances
    sql_instances=$(gcloud sql instances list --format=json 2>/dev/null || echo "[]")
    echo "$sql_instances" > "$OUTPUT_DIR/sql-instances.json"
    
    local sql_count=$(echo "$sql_instances" | jq '. | length')
    resource_counts["sql_instances"]=$sql_count
    log_info "Cloud SQL instances found: $sql_count"
    
    if [[ $sql_count -gt 0 ]]; then
        # Check SSL requirements
        local ssl_required
        ssl_required=$(echo "$sql_instances" | jq '[.[] | select(.settings.ipConfiguration.requireSsl == true)]')
        local ssl_count=$(echo "$ssl_required" | jq '. | length')
        
        if [[ $ssl_count -eq $sql_count ]]; then
            log_success "All SQL instances require SSL"
            validation_results["sql_ssl"]="passed"
        else
            log_warning "$((sql_count - ssl_count)) SQL instances don't require SSL"
            validation_results["sql_ssl"]="warning"
        fi
        
        # Check backup configurations
        local backup_enabled
        backup_enabled=$(echo "$sql_instances" | jq '[.[] | select(.settings.backupConfiguration.enabled == true)]')
        local backup_count=$(echo "$backup_enabled" | jq '. | length')
        
        if [[ $backup_count -eq $sql_count ]]; then
            log_success "All SQL instances have backups enabled"
            validation_results["sql_backups"]="passed"
        else
            log_warning "$((sql_count - backup_count)) SQL instances don't have backups enabled"
            validation_results["sql_backups"]="warning"
        fi
    fi
    
    # Firestore databases
    log_infra "Checking Firestore databases..."
    local firestore_dbs
    firestore_dbs=$(gcloud firestore databases list --format=json 2>/dev/null || echo "[]")
    echo "$firestore_dbs" > "$OUTPUT_DIR/firestore-databases.json"
    
    local firestore_count=$(echo "$firestore_dbs" | jq '. | length')
    resource_counts["firestore_databases"]=$firestore_count
    log_info "Firestore databases found: $firestore_count"
    
    validation_results["storage_database"]="completed"
    log_success "Storage and database validation completed"
}

# Network and security validation
validate_network_security() {
    if [[ "$VALIDATION_TYPE" != "all" && "$VALIDATION_TYPE" != "advanced" && "$VALIDATION_TYPE" != "compliance" ]]; then
        return 0
    fi
    
    log_progress "Network and security validation"
    
    # VPC networks
    log_infra "Checking VPC networks..."
    local networks
    networks=$(gcloud compute networks list --format=json)
    echo "$networks" > "$OUTPUT_DIR/vpc-networks.json"
    
    local network_count=$(echo "$networks" | jq '. | length')
    resource_counts["vpc_networks"]=$network_count
    log_info "VPC networks found: $network_count"
    
    # Check for custom networks vs default
    local custom_networks
    custom_networks=$(echo "$networks" | jq '[.[] | select(.name != "default")]')
    local custom_count=$(echo "$custom_networks" | jq '. | length')
    
    if [[ $custom_count -gt 0 ]]; then
        log_success "Custom VPC networks found: $custom_count"
        validation_results["custom_networks"]="passed"
    else
        log_warning "Only default network found - consider using custom VPCs"
        validation_results["custom_networks"]="warning"
    fi
    
    # Firewall rules
    log_infra "Checking firewall rules..."
    local firewall_rules
    firewall_rules=$(gcloud compute firewall-rules list --format=json)
    echo "$firewall_rules" > "$OUTPUT_DIR/firewall-rules.json"
    
    local firewall_count=$(echo "$firewall_rules" | jq '. | length')
    resource_counts["firewall_rules"]=$firewall_count
    log_info "Firewall rules found: $firewall_count"
    
    # Check for overly permissive rules
    local permissive_rules
    permissive_rules=$(echo "$firewall_rules" | jq '[.[] | select(.sourceRanges[]? == "0.0.0.0/0" and (.allowed[]?.IPProtocol == "tcp" or .allowed[]?.IPProtocol == "udp"))]')
    local permissive_count=$(echo "$permissive_rules" | jq '. | length')
    
    if [[ $permissive_count -gt 0 ]]; then
        log_warning "Potentially permissive firewall rules found: $permissive_count"
        validation_results["permissive_firewall"]="warning"
    else
        log_success "No overly permissive firewall rules found"
        validation_results["permissive_firewall"]="passed"
    fi
    
    # Load balancers
    log_infra "Checking load balancers..."
    local load_balancers
    load_balancers=$(gcloud compute url-maps list --format=json 2>/dev/null || echo "[]")
    echo "$load_balancers" > "$OUTPUT_DIR/load-balancers.json"
    
    local lb_count=$(echo "$load_balancers" | jq '. | length')
    resource_counts["load_balancers"]=$lb_count
    log_info "Load balancers found: $lb_count"
    
    # SSL certificates
    log_infra "Checking SSL certificates..."
    local ssl_certs
    ssl_certs=$(gcloud compute ssl-certificates list --format=json 2>/dev/null || echo "[]")
    echo "$ssl_certs" > "$OUTPUT_DIR/ssl-certificates.json"
    
    local cert_count=$(echo "$ssl_certs" | jq '. | length')
    resource_counts["ssl_certificates"]=$cert_count
    log_info "SSL certificates found: $cert_count"
    
    validation_results["network_security"]="completed"
    log_success "Network and security validation completed"
}

# IAM and access control validation
validate_iam_access() {
    if [[ "$VALIDATION_TYPE" != "all" && "$VALIDATION_TYPE" != "compliance" ]]; then
        return 0
    fi
    
    log_progress "IAM and access control validation"
    
    # Project IAM policy
    log_infra "Checking project IAM policy..."
    local iam_policy
    iam_policy=$(gcloud projects get-iam-policy "$PROJECT_ID" --format=json)
    echo "$iam_policy" > "$OUTPUT_DIR/iam-policy.json"
    
    # Analyze bindings
    local binding_count=$(echo "$iam_policy" | jq '.bindings | length')
    resource_counts["iam_bindings"]=$binding_count
    log_info "IAM bindings found: $binding_count"
    
    # Check for overly privileged accounts
    local owner_bindings
    owner_bindings=$(echo "$iam_policy" | jq '[.bindings[] | select(.role == "roles/owner")]')
    local owner_members=$(echo "$owner_bindings" | jq -r '.[].members[]?' | wc -l)
    
    if [[ $owner_members -gt 3 ]]; then
        log_warning "Many accounts have Owner role: $owner_members"
        validation_results["iam_owners"]="warning"
    else
        log_success "Reasonable number of Owner accounts: $owner_members"
        validation_results["iam_owners"]="passed"
    fi
    
    # Check for primitive roles
    local primitive_roles
    primitive_roles=$(echo "$iam_policy" | jq '[.bindings[] | select(.role | startswith("roles/editor") or startswith("roles/viewer") or startswith("roles/owner"))]')
    local primitive_count=$(echo "$primitive_roles" | jq '. | length')
    
    if [[ $primitive_count -gt 5 ]]; then
        log_warning "Many primitive roles found: $primitive_count (consider using predefined roles)"
        validation_results["primitive_roles"]="warning"
    else
        validation_results["primitive_roles"]="passed"
    fi
    
    # Service accounts
    log_infra "Checking service accounts..."
    local service_accounts
    service_accounts=$(gcloud iam service-accounts list --format=json)
    echo "$service_accounts" > "$OUTPUT_DIR/service-accounts.json"
    
    local sa_count=$(echo "$service_accounts" | jq '. | length')
    resource_counts["service_accounts"]=$sa_count
    log_info "Service accounts found: $sa_count"
    
    # Check for unused service accounts
    # Note: This is a simplified check; in practice, you'd want more sophisticated analysis
    local user_managed_sa
    user_managed_sa=$(echo "$service_accounts" | jq '[.[] | select(.email | contains("@'$PROJECT_ID'.iam.gserviceaccount.com") and (.email | contains("compute@") | not) and (.email | contains("service-") | not))]')
    local user_sa_count=$(echo "$user_managed_sa" | jq '. | length')
    
    log_info "User-managed service accounts: $user_sa_count"
    
    validation_results["iam_access"]="completed"
    log_success "IAM and access control validation completed"
}

# Cost analysis and optimization
validate_cost_optimization() {
    if [[ "$VALIDATION_TYPE" != "all" && "$VALIDATION_TYPE" != "cost" ]]; then
        return 0
    fi
    
    log_progress "Cost analysis and optimization"
    
    # Note: This is a simplified cost analysis
    # In practice, you'd integrate with Cloud Billing API for detailed cost data
    
    log_infra "Analyzing resource costs..."
    
    # Estimate costs based on resource counts
    local estimated_monthly_cost=0
    
    # Compute Engine instances (rough estimate)
    local compute_cost=$((resource_counts["compute_instances"] * 50))  # $50/month per instance
    estimated_monthly_cost=$((estimated_monthly_cost + compute_cost))
    
    # GKE clusters (rough estimate)
    local gke_cost=$((resource_counts["gke_clusters"] * 100))  # $100/month per cluster
    estimated_monthly_cost=$((estimated_monthly_cost + gke_cost))
    
    # Cloud SQL instances (rough estimate)
    local sql_cost=$((resource_counts["sql_instances"] * 150))  # $150/month per instance
    estimated_monthly_cost=$((estimated_monthly_cost + sql_cost))
    
    # Storage buckets (minimal cost)
    local storage_cost=$((resource_counts["storage_buckets"] * 5))  # $5/month per bucket
    estimated_monthly_cost=$((estimated_monthly_cost + storage_cost))
    
    cost_estimates["total_monthly"]=$estimated_monthly_cost
    cost_estimates["compute"]=$compute_cost
    cost_estimates["gke"]=$gke_cost
    cost_estimates["sql"]=$sql_cost
    cost_estimates["storage"]=$storage_cost
    
    log_info "Estimated monthly cost: \$$estimated_monthly_cost"
    
    if [[ $estimated_monthly_cost -gt $MAX_COST_THRESHOLD ]]; then
        log_warning "Estimated cost exceeds threshold: \$$estimated_monthly_cost > \$$MAX_COST_THRESHOLD"
        validation_results["cost_threshold"]="warning"
    else
        log_success "Estimated cost within threshold: \$$estimated_monthly_cost <= \$$MAX_COST_THRESHOLD"
        validation_results["cost_threshold"]="passed"
    fi
    
    # Cost optimization recommendations
    cat > "$OUTPUT_DIR/cost-optimization-recommendations.txt" << EOF
Cost Optimization Recommendations:
=================================

1. Compute Instances: $compute_cost USD/month
   - Consider using preemptible instances for non-critical workloads
   - Review machine types and right-size instances
   - Implement auto-scaling where appropriate

2. GKE Clusters: $gke_cost USD/month
   - Use cluster autoscaler
   - Consider spot instances for non-critical workloads
   - Optimize node pool configurations

3. Cloud SQL: $sql_cost USD/month
   - Review instance sizes
   - Consider read replicas for read-heavy workloads
   - Implement automated backups with retention policies

4. Storage: $storage_cost USD/month
   - Implement lifecycle policies
   - Use appropriate storage classes
   - Clean up unused buckets and objects

Total Estimated Monthly Cost: $estimated_monthly_cost USD
EOF
    
    validation_results["cost_optimization"]="completed"
    log_success "Cost analysis and optimization completed"
}

# Generate comprehensive infrastructure report
generate_infrastructure_report() {
    log_progress "Generating comprehensive infrastructure report"
    
    local report_file="$OUTPUT_DIR/infrastructure-validation-report.json"
    local html_report="$OUTPUT_DIR/infrastructure-validation-report.html"
    
    # Create JSON summary
    cat > "$report_file" << EOF
{
  "validation_metadata": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "validation_type": "$VALIDATION_TYPE",
    "project_id": "$PROJECT_ID",
    "region": "$REGION",
    "environment": "$ENVIRONMENT"
  },
  "validation_results": $(printf '%s\n' "${!validation_results[@]}" | jq -R . | jq -s 'map(split(":") | {(.[0]): .[1]}) | add'),
  "resource_counts": {
EOF
    
    # Add resource counts
    local first=true
    for key in "${!resource_counts[@]}"; do
        if [[ "$first" == "false" ]]; then
            echo "," >> "$report_file"
        fi
        echo "    \"$key\": ${resource_counts[$key]}" >> "$report_file"
        first=false
    done
    
    echo "  }," >> "$report_file"
    echo "  \"cost_estimates\": {" >> "$report_file"
    
    # Add cost estimates
    first=true
    for key in "${!cost_estimates[@]}"; do
        if [[ "$first" == "false" ]]; then
            echo "," >> "$report_file"
        fi
        echo "    \"$key\": ${cost_estimates[$key]}" >> "$report_file"
        first=false
    done
    
    cat >> "$report_file" << 'EOF'
  }
}
EOF
    
    # Generate HTML report
    cat > "$html_report" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Infrastructure Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 10px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .pass { background: #e6ffe6; border-color: #99ff99; }
        .fail { background: #ffe6e6; border-color: #ff9999; }
        .warning { background: #fff0e6; border-color: #ffcc99; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏗️ Infrastructure Validation Report</h1>
        <p><strong>Timestamp:</strong> $(date -u +%Y-%m-%dT%H:%M:%SZ)</p>
        <p><strong>Project ID:</strong> $PROJECT_ID</p>
        <p><strong>Region:</strong> $REGION</p>
        <p><strong>Environment:</strong> $ENVIRONMENT</p>
    </div>
EOF
    
    # Add validation results to HTML
    echo '<div class="section">' >> "$html_report"
    echo '<h2>📊 Validation Results</h2>' >> "$html_report"
    echo '<table>' >> "$html_report"
    echo '<tr><th>Validation</th><th>Status</th></tr>' >> "$html_report"
    
    for key in "${!validation_results[@]}"; do
        local status="${validation_results[$key]}"
        local class="pass"
        if [[ "$status" == "failed" ]]; then
            class="fail"
        elif [[ "$status" == "warning" ]]; then
            class="warning"
        fi
        
        echo "<tr class=\"$class\"><td>$key</td><td>$status</td></tr>" >> "$html_report"
    done
    
    echo '</table>' >> "$html_report"
    echo '</div>' >> "$html_report"
    
    # Add resource counts
    echo '<div class="section">' >> "$html_report"
    echo '<h2>📈 Resource Summary</h2>' >> "$html_report"
    echo '<table>' >> "$html_report"
    echo '<tr><th>Resource Type</th><th>Count</th></tr>' >> "$html_report"
    
    for key in "${!resource_counts[@]}"; do
        echo "<tr><td>$key</td><td>${resource_counts[$key]}</td></tr>" >> "$html_report"
    done
    
    echo '</table>' >> "$html_report"
    echo '</div>' >> "$html_report"
    echo '</body></html>' >> "$html_report"
    
    log_success "Infrastructure report generated: $report_file"
    log_success "HTML report generated: $html_report"
}

# Evaluate validation results
evaluate_validation_results() {
    log_progress "Evaluating validation results"
    
    local exit_code=0
    local failed_validations=()
    local warning_validations=()
    
    for key in "${!validation_results[@]}"; do
        local status="${validation_results[$key]}"
        if [[ "$status" == "failed" ]]; then
            failed_validations+=("$key")
            exit_code=1
        elif [[ "$status" == "warning" ]]; then
            warning_validations+=("$key")
        fi
    done
    
    # Summary
    log_info "Validation Summary:"
    log_info "  Total validations: ${#validation_results[@]}"
    log_info "  Failed: ${#failed_validations[@]}"
    log_info "  Warnings: ${#warning_validations[@]}"
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "Infrastructure validation passed!"
        if [[ ${#warning_validations[@]} -gt 0 ]]; then
            log_warning "Warnings found: ${warning_validations[*]}"
        fi
    else
        log_error "Infrastructure validation failed!"
        log_error "Failed validations: ${failed_validations[*]}"
        if [[ ${#warning_validations[@]} -gt 0 ]]; then
            log_warning "Warnings found: ${warning_validations[*]}"
        fi
    fi
    
    return $exit_code
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --validation-type)
                VALIDATION_TYPE="$2"
                shift 2
                ;;
            --project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            --region)
                REGION="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --validation-type TYPE  Validation type: all, basic, advanced, compliance, cost"
                echo "  --project-id ID         GCP Project ID"
                echo "  --region REGION         GCP Region"
                echo "  --environment ENV       Environment name"
                echo "  --output-dir DIR        Output directory for reports"
                echo "  --dry-run              Dry run mode"
                echo "  --help                 Show this help"
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
    
    # Check prerequisites
    check_prerequisites
    
    # Run validations based on type
    validate_project_basics
    validate_compute_resources
    validate_storage_database
    validate_network_security
    validate_iam_access
    validate_cost_optimization
    
    # Generate reports
    generate_infrastructure_report
    
    # Evaluate results
    evaluate_validation_results
}

# Execute main function with all arguments
main "$@"