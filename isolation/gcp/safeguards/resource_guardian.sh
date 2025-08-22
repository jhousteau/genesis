#!/usr/bin/env bash
# Resource Guardian - Advanced resource monitoring and protection
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Monitors resource usage and prevents quota overruns

set -euo pipefail

# Script metadata
RESOURCE_GUARDIAN_VERSION="2.0.0"
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
RESOURCE_CONFIG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/resource-config.json"
RESOURCE_LOG_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/logs/resource-guardian.log"
QUOTA_CACHE_FILE="${REPO_GCLOUD_HOME:-$HOME/.gcloud}/cache/quota-cache.json"

# Resource monitoring functions
get_compute_usage() {
    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi
    
    log_step "Checking compute instance usage..."
    
    # Get instance count by region
    local instances_data
    instances_data=$(gcloud compute instances list \
        --project="$project_id" \
        --format="json" 2>/dev/null || echo "[]")
    
    local total_instances
    total_instances=$(echo "$instances_data" | jq 'length')
    
    local running_instances
    running_instances=$(echo "$instances_data" | jq '[.[] | select(.status == "RUNNING")] | length')
    
    # Get instance types summary
    local instance_types
    instance_types=$(echo "$instances_data" | jq -r '
        group_by(.machineType | split("/")[-1]) | 
        map({type: .[0].machineType | split("/")[-1], count: length}) | 
        .[]' 2>/dev/null || echo '{}')
    
    cat <<EOF
{
    "total_instances": $total_instances,
    "running_instances": $running_instances,
    "stopped_instances": $((total_instances - running_instances)),
    "instance_types": [$instance_types],
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

get_storage_usage() {
    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi
    
    log_step "Checking storage usage..."
    
    # Get bucket count and sizes
    local buckets_data
    buckets_data=$(gcloud storage buckets list \
        --project="$project_id" \
        --format="json" 2>/dev/null || echo "[]")
    
    local bucket_count
    bucket_count=$(echo "$buckets_data" | jq 'length')
    
    # Get persistent disk usage
    local disks_data
    disks_data=$(gcloud compute disks list \
        --project="$project_id" \
        --format="json" 2>/dev/null || echo "[]")
    
    local total_disk_size
    total_disk_size=$(echo "$disks_data" | jq '[.[].sizeGb | tonumber] | add // 0')
    
    local disk_count
    disk_count=$(echo "$disks_data" | jq 'length')
    
    cat <<EOF
{
    "bucket_count": $bucket_count,
    "disk_count": $disk_count,
    "total_disk_size_gb": $total_disk_size,
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

get_network_usage() {
    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi
    
    log_step "Checking network usage..."
    
    # Get VPC count
    local vpc_data
    vpc_data=$(gcloud compute networks list \
        --project="$project_id" \
        --format="json" 2>/dev/null || echo "[]")
    
    local vpc_count
    vpc_count=$(echo "$vpc_data" | jq 'length')
    
    # Get firewall rules count
    local firewall_data
    firewall_data=$(gcloud compute firewall-rules list \
        --project="$project_id" \
        --format="json" 2>/dev/null || echo "[]")
    
    local firewall_count
    firewall_count=$(echo "$firewall_data" | jq 'length')
    
    # Get load balancer count
    local lb_data
    lb_data=$(gcloud compute url-maps list \
        --project="$project_id" \
        --format="json" 2>/dev/null || echo "[]")
    
    local lb_count
    lb_count=$(echo "$lb_data" | jq 'length')
    
    cat <<EOF
{
    "vpc_count": $vpc_count,
    "firewall_rules_count": $firewall_count,
    "load_balancer_count": $lb_count,
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

get_quota_usage() {
    local project_id="${PROJECT_ID:-}"
    local region="${REGION:-us-central1}"
    
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi
    
    log_step "Checking quota usage..."
    
    # Cache quota information to avoid rate limiting
    local cache_age=0
    if [[ -f "$QUOTA_CACHE_FILE" ]]; then
        cache_age=$(( $(date +%s) - $(stat -c %Y "$QUOTA_CACHE_FILE" 2>/dev/null || stat -f %m "$QUOTA_CACHE_FILE" 2>/dev/null || echo 0) ))
    fi
    
    # Refresh cache if older than 5 minutes
    if [[ $cache_age -gt 300 ]]; then
        log_info "Refreshing quota cache..."
        mkdir -p "$(dirname "$QUOTA_CACHE_FILE")"
        
        # Get compute quotas for the region
        local quota_data
        quota_data=$(gcloud compute project-info describe \
            --project="$project_id" \
            --format="json" 2>/dev/null || echo '{"quotas":[]}')
        
        echo "$quota_data" > "$QUOTA_CACHE_FILE"
    fi
    
    # Extract relevant quotas
    local quota_summary
    quota_summary=$(jq -r '
        .quotas[] | 
        select(.metric | test("INSTANCES|CPUS|DISKS_TOTAL_GB|STATIC_ADDRESSES")) |
        {
            metric: .metric,
            limit: .limit,
            usage: .usage,
            percentage: ((.usage / .limit) * 100 | floor)
        }' "$QUOTA_CACHE_FILE" 2>/dev/null || echo '{}')
    
    echo "[$quota_summary]" | jq -c '.'
}

check_resource_thresholds() {
    log_step "Checking resource thresholds..."
    
    # Load configuration
    local warning_threshold=75
    local critical_threshold=90
    
    if [[ -f "$RESOURCE_CONFIG_FILE" ]]; then
        warning_threshold=$(jq -r '.warning_threshold // 75' "$RESOURCE_CONFIG_FILE" 2>/dev/null || echo "75")
        critical_threshold=$(jq -r '.critical_threshold // 90' "$RESOURCE_CONFIG_FILE" 2>/dev/null || echo "90")
    fi
    
    # Get resource usage
    local compute_usage storage_usage network_usage quota_usage
    compute_usage=$(get_compute_usage)
    storage_usage=$(get_storage_usage)
    network_usage=$(get_network_usage)
    quota_usage=$(get_quota_usage)
    
    # Check quota thresholds
    local alert_level="OK"
    local alerts=()
    
    while IFS= read -r quota; do
        if [[ -n "$quota" && "$quota" != "null" ]]; then
            local metric percentage limit usage
            metric=$(echo "$quota" | jq -r '.metric')
            percentage=$(echo "$quota" | jq -r '.percentage')
            limit=$(echo "$quota" | jq -r '.limit')
            usage=$(echo "$quota" | jq -r '.usage')
            
            if [[ "$percentage" -ge "$critical_threshold" ]]; then
                alert_level="CRITICAL"
                alerts+=("CRITICAL: $metric at ${percentage}% (${usage}/${limit})")
                log_error "CRITICAL: $metric at ${percentage}% (${usage}/${limit})"
            elif [[ "$percentage" -ge "$warning_threshold" ]]; then
                if [[ "$alert_level" != "CRITICAL" ]]; then
                    alert_level="WARNING"
                fi
                alerts+=("WARNING: $metric at ${percentage}% (${usage}/${limit})")
                log_warning "WARNING: $metric at ${percentage}% (${usage}/${limit})"
            else
                log_success "$metric: ${percentage}% (${usage}/${limit})"
            fi
        fi
    done < <(echo "$quota_usage" | jq -c '.[]?')
    
    # Create resource summary
    local resource_summary
    resource_summary=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "alert_level": "$alert_level",
    "alerts": $(printf '%s\n' "${alerts[@]}" | jq -R . | jq -s .),
    "compute": $compute_usage,
    "storage": $storage_usage,
    "network": $network_usage,
    "quotas": $quota_usage,
    "thresholds": {
        "warning": $warning_threshold,
        "critical": $critical_threshold
    },
    "project_id": "${PROJECT_ID:-}",
    "environment": "${ENVIRONMENT:-}",
    "guardian_version": "$RESOURCE_GUARDIAN_VERSION"
}
EOF
)
    
    # Log the check
    mkdir -p "$(dirname "$RESOURCE_LOG_FILE")"
    echo "$resource_summary" >> "$RESOURCE_LOG_FILE"
    
    # Return appropriate exit code
    case "$alert_level" in
        "CRITICAL") return 2 ;;
        "WARNING") return 1 ;;
        *) return 0 ;;
    esac
}

# Resource cleanup suggestions
suggest_cleanup() {
    log_step "Analyzing resources for cleanup opportunities..."
    
    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi
    
    echo -e "${CYAN}═══ CLEANUP SUGGESTIONS ═══${NC}"
    echo ""
    
    # Check for stopped instances
    local stopped_instances
    stopped_instances=$(gcloud compute instances list \
        --project="$project_id" \
        --filter="status:TERMINATED" \
        --format="value(name,zone)" 2>/dev/null | wc -l)
    
    if [[ "$stopped_instances" -gt 0 ]]; then
        echo -e "${YELLOW}Stopped Instances ($stopped_instances found):${NC}"
        echo "# Delete stopped instances:"
        gcloud compute instances list \
            --project="$project_id" \
            --filter="status:TERMINATED" \
            --format="table(name,zone)" 2>/dev/null | tail -n +2 | \
        while IFS=$'\t' read -r name zone; do
            echo "gcloud compute instances delete $name --zone=$zone --quiet"
        done
        echo ""
    fi
    
    # Check for unattached disks
    local unattached_disks
    unattached_disks=$(gcloud compute disks list \
        --project="$project_id" \
        --filter="-users:*" \
        --format="value(name,zone)" 2>/dev/null | wc -l)
    
    if [[ "$unattached_disks" -gt 0 ]]; then
        echo -e "${YELLOW}Unattached Disks ($unattached_disks found):${NC}"
        echo "# Delete unattached disks:"
        gcloud compute disks list \
            --project="$project_id" \
            --filter="-users:*" \
            --format="table(name,zone)" 2>/dev/null | tail -n +2 | \
        while IFS=$'\t' read -r name zone; do
            echo "gcloud compute disks delete $name --zone=$zone --quiet"
        done
        echo ""
    fi
    
    # Check for old snapshots
    echo -e "${YELLOW}Old Snapshots:${NC}"
    echo "# List snapshots older than 30 days:"
    echo "gcloud compute snapshots list --filter='creationTimestamp<$(date -d '30 days ago' -u +%Y-%m-%dT%H:%M:%SZ)' --format='table(name,creationTimestamp)'"
    echo ""
    
    # Check for unused static IPs
    echo -e "${YELLOW}Static IP Addresses:${NC}"
    echo "# List unused static IP addresses:"
    echo "gcloud compute addresses list --filter='status:RESERVED' --format='table(name,region,status)'"
    echo ""
    
    # Check for old images
    echo -e "${YELLOW}Custom Images:${NC}"
    echo "# List custom images (review for cleanup):"
    echo "gcloud compute images list --no-standard-images --format='table(name,creationTimestamp,diskSizeGb)'"
    echo ""
}

# Emergency resource shutdown
emergency_shutdown() {
    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "")
    fi
    
    echo -e "${RED}🚨 EMERGENCY RESOURCE SHUTDOWN${NC}"
    echo ""
    echo -e "${RED}WARNING: This will stop/scale down resources to minimize costs!${NC}"
    echo ""
    
    if [[ "${CONFIRM_EMERGENCY:-}" != "I_UNDERSTAND" ]]; then
        echo "To proceed, set: export CONFIRM_EMERGENCY=I_UNDERSTAND"
        return 1
    fi
    
    log_warning "Emergency shutdown initiated for project: $project_id"
    
    # Stop all running instances
    log_step "Stopping all compute instances..."
    if gcloud compute instances list --project="$project_id" --filter="status:RUNNING" --format="value(name,zone)" | \
       while IFS=$'\t' read -r name zone; do
           if [[ -n "$name" && -n "$zone" ]]; then
               echo "Stopping instance: $name in $zone"
               gcloud compute instances stop "$name" --zone="$zone" --async --quiet 2>/dev/null || true
           fi
       done; then
        log_success "Instance shutdown commands issued"
    else
        log_warning "Some instances may have failed to stop"
    fi
    
    # Scale down GKE clusters if any
    log_step "Scaling down GKE clusters..."
    if gcloud container clusters list --project="$project_id" --format="value(name,location)" 2>/dev/null | \
       while IFS=$'\t' read -r name location; do
           if [[ -n "$name" && -n "$location" ]]; then
               echo "Scaling down cluster: $name in $location"
               gcloud container clusters resize "$name" --location="$location" --num-nodes=0 --async --quiet 2>/dev/null || true
           fi
       done; then
        log_success "Cluster scaling commands issued"
    else
        log_info "No GKE clusters found or failed to scale"
    fi
    
    # Create emergency flag
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${REPO_GCLOUD_HOME:-$HOME/.gcloud}/.emergency_resource_flag"
    
    log_warning "Emergency shutdown complete. Review resources and restart as needed."
}

# Show resource dashboard
show_dashboard() {
    echo -e "${CYAN}═══ RESOURCE GUARDIAN DASHBOARD ═══${NC}"
    echo ""
    
    # Current project info
    local project_id="${PROJECT_ID:-}"
    if [[ -z "$project_id" ]]; then
        project_id=$(gcloud config get-value core/project 2>/dev/null || echo "unknown")
    fi
    
    echo -e "${WHITE}Project: $project_id${NC}"
    echo -e "${WHITE}Environment: ${ENVIRONMENT:-unknown}${NC}"
    echo -e "${WHITE}Region: ${REGION:-unknown}${NC}"
    echo ""
    
    # Check emergency flags
    if [[ -f "${REPO_GCLOUD_HOME:-$HOME/.gcloud}/.emergency_resource_flag" ]]; then
        echo -e "${RED}🚨 EMERGENCY RESOURCE FLAG ACTIVE${NC}"
        echo ""
    fi
    
    # Run resource check
    if check_resource_thresholds; then
        echo ""
        log_success "All resources within normal thresholds"
    else
        echo ""
        log_warning "Some resources require attention"
    fi
    
    echo ""
    echo -e "${WHITE}Quick Actions:${NC}"
    echo "• Run cleanup analysis: resource-guardian cleanup"
    echo "• View recent history: resource-guardian history"
    echo "• Emergency shutdown: resource-guardian emergency"
}

# Main function
main() {
    local command="${1:-check}"
    
    case "$command" in
        "check"|"c")
            check_resource_thresholds
            ;;
        "dashboard"|"d")
            show_dashboard
            ;;
        "cleanup")
            suggest_cleanup
            ;;
        "emergency")
            emergency_shutdown
            ;;
        "clear-emergency")
            rm -f "${REPO_GCLOUD_HOME:-$HOME/.gcloud}/.emergency_resource_flag"
            log_success "Emergency resource flag cleared"
            ;;
        "history"|"h")
            local limit="${2:-10}"
            if [[ -f "$RESOURCE_LOG_FILE" ]]; then
                log_info "Recent resource checks (last $limit):"
                tail -n "$limit" "$RESOURCE_LOG_FILE" | jq -r '
                    [.timestamp, .alert_level, (.alerts | length)] | 
                    @tsv' | \
                while IFS=$'\t' read -r timestamp level alert_count; do
                    case "$level" in
                        "CRITICAL") color="$RED" ;;
                        "WARNING") color="$YELLOW" ;;
                        *) color="$GREEN" ;;
                    esac
                    echo -e "${color}$timestamp - $level - $alert_count alerts${NC}"
                done
            else
                log_info "No resource check history found"
            fi
            ;;
        "help"|"--help"|"-h")
            echo "Resource Guardian v$RESOURCE_GUARDIAN_VERSION"
            echo ""
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  check, c                 Check resource usage against quotas"
            echo "  dashboard, d             Show resource dashboard"
            echo "  cleanup                  Suggest resource cleanup opportunities"
            echo "  emergency                Emergency resource shutdown (requires confirmation)"
            echo "  clear-emergency          Clear emergency resource flag"
            echo "  history, h [limit]       Show resource check history"
            echo "  help                     Show this help"
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