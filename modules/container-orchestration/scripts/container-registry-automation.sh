#!/bin/bash
# Genesis Container Registry Automation
# Automated container image building, scanning, and deployment pipeline

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
REGISTRY_BASE="${CONTAINER_REGISTRY:-us-central1-docker.pkg.dev}"
PROJECT_ID="${PROJECT_ID:-}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
BUILD_ID="${BUILD_ID:-$(date +%Y%m%d-%H%M%S)}"

# Logging functions
log() {
    echo "[$(date -Iseconds)] [REGISTRY-AUTOMATION] $*" >&2
}

error() {
    echo "[$(date -Iseconds)] [ERROR] [REGISTRY-AUTOMATION] $*" >&2
    exit 1
}

warn() {
    echo "[$(date -Iseconds)] [WARN] [REGISTRY-AUTOMATION] $*" >&2
}

# Validate prerequisites
validate_prerequisites() {
    log "Validating prerequisites"

    # Check required tools
    local required_tools=("docker" "gcloud" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            error "Required tool '$tool' not found"
        fi
    done

    # Validate PROJECT_ID
    if [[ -z "$PROJECT_ID" ]]; then
        error "PROJECT_ID environment variable is required"
    fi

    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon not accessible"
    fi

    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 >/dev/null 2>&1; then
        error "gcloud authentication required"
    fi

    log "Prerequisites validated"
}

# Create Artifact Registry repositories
create_repositories() {
    log "Creating Artifact Registry repositories"

    local repositories=(
        "genesis-agent-cage:Agent-cage runtime images"
        "genesis-claude-talk:Claude-talk MCP server images"
        "genesis-backend-developer:Backend developer agent images"
        "genesis-frontend-developer:Frontend developer agent images"
        "genesis-platform-engineer:Platform engineer agent images"
        "genesis-data-engineer:Data engineer agent images"
        "genesis-qa-automation:QA automation agent images"
        "genesis-security:Security agent images"
        "genesis-sre:SRE agent images"
        "genesis-devops:DevOps agent images"
        "genesis-integration:Integration agent images"
        "genesis-architect:Architect agent images"
        "genesis-tech-lead:Tech lead agent images"
        "genesis-project-manager:Project manager agent images"
    )

    local region="${REGISTRY_REGION:-us-central1}"

    for repo_def in "${repositories[@]}"; do
        local repo_name="${repo_def%%:*}"
        local description="${repo_def##*:}"

        log "Creating repository: $repo_name"

        # Check if repository exists
        if gcloud artifacts repositories describe "$repo_name" \
           --project="$PROJECT_ID" \
           --location="$region" \
           --format="value(name)" >/dev/null 2>&1; then
            log "Repository $repo_name already exists"
        else
            # Create repository
            gcloud artifacts repositories create "$repo_name" \
                --project="$PROJECT_ID" \
                --location="$region" \
                --repository-format=docker \
                --description="$description" \
                --labels="environment=$ENVIRONMENT,managed-by=genesis"

            log "Created repository: $repo_name"
        fi
    done

    # Set up cleanup policies
    setup_cleanup_policies

    log "Repository creation complete"
}

# Set up cleanup policies
setup_cleanup_policies() {
    log "Setting up cleanup policies"

    local cleanup_policy='{
        "rules": [
            {
                "name": "delete-old-images",
                "action": {"type": "Delete"},
                "condition": {
                    "olderThan": "30d",
                    "tagState": "UNTAGGED"
                }
            },
            {
                "name": "keep-minimum-versions",
                "action": {"type": "Keep"},
                "mostRecentVersions": {
                    "keepCount": 5
                }
            },
            {
                "name": "delete-vulnerable-images",
                "action": {"type": "Delete"},
                "condition": {
                    "versionNameRegexes": [".*"],
                    "packageNameRegexes": [".*"],
                    "vulnerabilityPolicy": {
                        "minimumSeverity": "HIGH"
                    }
                }
            }
        ]
    }'

    local repositories=(
        "genesis-agent-cage"
        "genesis-claude-talk"
        "genesis-backend-developer"
        "genesis-frontend-developer"
        "genesis-platform-engineer"
    )

    for repo in "${repositories[@]}"; do
        log "Setting cleanup policy for $repo"

        # Create temporary policy file
        local policy_file=$(mktemp)
        echo "$cleanup_policy" > "$policy_file"

        # Apply cleanup policy
        if gcloud artifacts repositories set-cleanup-policy "$repo" \
           --project="$PROJECT_ID" \
           --location="${REGISTRY_REGION:-us-central1}" \
           --policy="$policy_file" \
           --quiet; then
            log "Cleanup policy applied to $repo"
        else
            warn "Failed to apply cleanup policy to $repo"
        fi

        rm -f "$policy_file"
    done
}

# Build container image
build_image() {
    local service_name="$1"
    local dockerfile_path="$2"
    local context_path="${3:-$PROJECT_ROOT}"
    local build_args="${4:-}"

    log "Building image for service: $service_name"

    local image_name="$REGISTRY_BASE/$PROJECT_ID/genesis-$service_name"
    local version_tag="${VERSION:-latest}"
    local build_tag="$BUILD_ID"

    # Build arguments
    local docker_build_args=(
        "--file" "$dockerfile_path"
        "--tag" "$image_name:$version_tag"
        "--tag" "$image_name:$build_tag"
        "--label" "org.opencontainers.image.created=$(date -Iseconds)"
        "--label" "org.opencontainers.image.source=https://github.com/genesis-platform/genesis"
        "--label" "org.opencontainers.image.revision=${GIT_COMMIT:-$(git rev-parse HEAD 2>/dev/null || echo 'unknown')}"
        "--label" "genesis.platform/service=$service_name"
        "--label" "genesis.platform/environment=$ENVIRONMENT"
        "--label" "genesis.platform/build-id=$BUILD_ID"
    )

    # Add custom build arguments
    if [[ -n "$build_args" ]]; then
        IFS=',' read -ra ARGS <<< "$build_args"
        for arg in "${ARGS[@]}"; do
            docker_build_args+=("--build-arg" "$arg")
        done
    fi

    # Multi-platform build for production
    if [[ "$ENVIRONMENT" == "prod" ]]; then
        docker_build_args+=("--platform" "linux/amd64,linux/arm64")
    fi

    # Execute build
    log "Building: docker build ${docker_build_args[*]} $context_path"
    docker build "${docker_build_args[@]}" "$context_path"

    # Scan image for vulnerabilities
    scan_image "$image_name:$version_tag" "$service_name"

    log "Image built successfully: $image_name:$version_tag"
}

# Scan container image for vulnerabilities
scan_image() {
    local image_name="$1"
    local service_name="$2"

    log "Scanning image for vulnerabilities: $image_name"

    # Use gcloud container images scan if available
    if command -v gcloud >/dev/null 2>&1; then
        log "Running gcloud container image scan"

        # Push image first for scanning
        docker push "$image_name"

        # Run vulnerability scan
        local scan_result_file=$(mktemp)
        if gcloud container images scan "$image_name" \
           --project="$PROJECT_ID" \
           --format=json > "$scan_result_file" 2>/dev/null; then

            # Parse scan results
            local critical_vulns=$(jq -r '.discovery.analysisCompleted.analysisType[] | select(.name=="VULNERABILITY") | .count' "$scan_result_file" 2>/dev/null || echo "0")

            log "Vulnerability scan completed. Critical vulnerabilities: $critical_vulns"

            # Fail build if critical vulnerabilities found in production
            if [[ "$ENVIRONMENT" == "prod" ]] && [[ "$critical_vulns" -gt 0 ]]; then
                error "Critical vulnerabilities found in production build: $critical_vulns"
            fi
        else
            warn "Vulnerability scanning failed for $image_name"
        fi

        rm -f "$scan_result_file"
    fi

    # Additional scanning with trivy if available
    if command -v trivy >/dev/null 2>&1; then
        log "Running Trivy security scan"

        local trivy_output=$(mktemp)
        if trivy image --format json --output "$trivy_output" "$image_name"; then
            local high_vulns=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$trivy_output" 2>/dev/null || echo "0")
            local critical_vulns=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$trivy_output" 2>/dev/null || echo "0")

            log "Trivy scan results - High: $high_vulns, Critical: $critical_vulns"

            # Fail build if too many critical vulnerabilities
            if [[ "$ENVIRONMENT" == "prod" ]] && [[ "$critical_vulns" -gt 3 ]]; then
                error "Too many critical vulnerabilities found: $critical_vulns"
            fi
        fi

        rm -f "$trivy_output"
    fi

    log "Image security scan completed: $image_name"
}

# Push image to registry
push_image() {
    local service_name="$1"
    local version_tag="${2:-latest}"

    log "Pushing image for service: $service_name"

    local image_name="$REGISTRY_BASE/$PROJECT_ID/genesis-$service_name"
    local build_tag="$BUILD_ID"

    # Configure Docker authentication
    configure_docker_auth

    # Push both version and build tags
    docker push "$image_name:$version_tag"
    docker push "$image_name:$build_tag"

    # Update latest tag for main branch
    if [[ "${GIT_BRANCH:-}" == "main" ]] && [[ "$version_tag" != "latest" ]]; then
        docker tag "$image_name:$version_tag" "$image_name:latest"
        docker push "$image_name:latest"
    fi

    log "Image pushed successfully: $image_name:$version_tag"
}

# Configure Docker authentication
configure_docker_auth() {
    local region="${REGISTRY_REGION:-us-central1}"

    log "Configuring Docker authentication for Artifact Registry"

    # Configure Docker credential helper
    gcloud auth configure-docker "${region}-docker.pkg.dev" --quiet

    log "Docker authentication configured"
}

# Build all Genesis container images
build_all_images() {
    log "Building all Genesis container images"

    local templates_dir="$PROJECT_ROOT/modules/container-orchestration/templates"

    # Build core services
    build_image "agent-cage" "$templates_dir/agent-cage.Dockerfile" "$PROJECT_ROOT"
    build_image "claude-talk" "$templates_dir/claude-talk.Dockerfile" "$PROJECT_ROOT"

    # Build specialized agents
    local agent_types=(
        "backend-developer"
        "frontend-developer"
        "platform-engineer"
        "data-engineer"
        "qa-automation"
        "security"
        "sre"
        "devops"
        "integration"
        "architect"
        "tech-lead"
        "project-manager"
    )

    for agent_type in "${agent_types[@]}"; do
        build_image "$agent_type" "$templates_dir/specialized-agent.Dockerfile" "$PROJECT_ROOT" "AGENT_TYPE=$agent_type"
    done

    log "All images built successfully"
}

# Push all images
push_all_images() {
    log "Pushing all Genesis container images"

    local version_tag="${VERSION:-latest}"

    # Push core services
    push_image "agent-cage" "$version_tag"
    push_image "claude-talk" "$version_tag"

    # Push specialized agents
    local agent_types=(
        "backend-developer"
        "frontend-developer"
        "platform-engineer"
        "data-engineer"
        "qa-automation"
        "security"
        "sre"
        "devops"
        "integration"
        "architect"
        "tech-lead"
        "project-manager"
    )

    for agent_type in "${agent_types[@]}"; do
        push_image "$agent_type" "$version_tag"
    done

    log "All images pushed successfully"
}

# Generate deployment manifests with updated image tags
update_deployment_manifests() {
    log "Updating deployment manifests with new image tags"

    local manifests_dir="$PROJECT_ROOT/modules/container-orchestration/manifests"
    local version_tag="${VERSION:-latest}"
    local image_base="$REGISTRY_BASE/$PROJECT_ID"

    # Update image references in manifests
    find "$manifests_dir" -name "*.yaml" -type f | while read -r manifest_file; do
        log "Updating manifest: $manifest_file"

        # Create backup
        cp "$manifest_file" "$manifest_file.bak"

        # Update image references
        sed -i.tmp "s|\${CONTAINER_REGISTRY}/\${PROJECT_ID}/|$image_base/genesis-|g" "$manifest_file"
        sed -i.tmp "s|\${[A-Z_]*_VERSION}|$version_tag|g" "$manifest_file"
        sed -i.tmp "s|\${PROJECT_ID}|$PROJECT_ID|g" "$manifest_file"
        sed -i.tmp "s|\${ENVIRONMENT}|$ENVIRONMENT|g" "$manifest_file"

        # Clean up temporary files
        rm -f "$manifest_file.tmp"
    done

    log "Deployment manifests updated"
}

# Clean up old images
cleanup_old_images() {
    log "Cleaning up old container images"

    local keep_images="${KEEP_IMAGES:-10}"
    local repositories=(
        "genesis-agent-cage"
        "genesis-claude-talk"
        "genesis-backend-developer"
        "genesis-frontend-developer"
        "genesis-platform-engineer"
    )

    for repo in "${repositories[@]}"; do
        log "Cleaning up repository: $repo"

        # List images and keep only the most recent ones
        local images_to_delete
        images_to_delete=$(gcloud artifacts docker images list \
            "$REGISTRY_BASE/$PROJECT_ID/$repo" \
            --project="$PROJECT_ID" \
            --sort-by="~createTime" \
            --format="value(imageUri)" \
            --limit=1000 | tail -n +$((keep_images + 1)))

        if [[ -n "$images_to_delete" ]]; then
            log "Deleting $(echo "$images_to_delete" | wc -l) old images from $repo"
            echo "$images_to_delete" | xargs -r gcloud artifacts docker images delete \
                --project="$PROJECT_ID" \
                --quiet
        else
            log "No old images to delete in $repo"
        fi
    done

    log "Image cleanup completed"
}

# Generate container image report
generate_image_report() {
    log "Generating container image report"

    local report_file="container-images-report-$BUILD_ID.json"
    local report_data='{"build_id": "'$BUILD_ID'", "timestamp": "'$(date -Iseconds)'", "environment": "'$ENVIRONMENT'", "images": []}'

    local repositories=(
        "genesis-agent-cage"
        "genesis-claude-talk"
        "genesis-backend-developer"
        "genesis-frontend-developer"
        "genesis-platform-engineer"
    )

    for repo in "${repositories[@]}"; do
        log "Gathering information for repository: $repo"

        local repo_info
        repo_info=$(gcloud artifacts docker images list \
            "$REGISTRY_BASE/$PROJECT_ID/$repo" \
            --project="$PROJECT_ID" \
            --format=json \
            --limit=5 2>/dev/null || echo '[]')

        # Add repository info to report
        report_data=$(echo "$report_data" | jq --argjson repo_info "$repo_info" --arg repo_name "$repo" '
            .images += [{
                "repository": $repo_name,
                "images": $repo_info
            }]')
    done

    # Write report
    echo "$report_data" | jq '.' > "$report_file"

    log "Container image report generated: $report_file"

    # Upload to Cloud Storage if configured
    if [[ -n "${REPORT_BUCKET:-}" ]]; then
        gsutil cp "$report_file" "gs://$REPORT_BUCKET/container-reports/"
        log "Report uploaded to Cloud Storage: gs://$REPORT_BUCKET/container-reports/$report_file"
    fi
}

# Main execution
main() {
    local action="${1:-help}"

    case "$action" in
        "setup")
            validate_prerequisites
            create_repositories
            configure_docker_auth
            ;;
        "build")
            validate_prerequisites
            configure_docker_auth
            local service="${2:-all}"
            if [[ "$service" == "all" ]]; then
                build_all_images
            else
                local dockerfile_path="$PROJECT_ROOT/modules/container-orchestration/templates/$service.Dockerfile"
                build_image "$service" "$dockerfile_path"
            fi
            ;;
        "push")
            validate_prerequisites
            configure_docker_auth
            local service="${2:-all}"
            if [[ "$service" == "all" ]]; then
                push_all_images
            else
                push_image "$service"
            fi
            ;;
        "build-push")
            validate_prerequisites
            configure_docker_auth
            local service="${2:-all}"
            if [[ "$service" == "all" ]]; then
                build_all_images
                push_all_images
            else
                local dockerfile_path="$PROJECT_ROOT/modules/container-orchestration/templates/$service.Dockerfile"
                build_image "$service" "$dockerfile_path"
                push_image "$service"
            fi
            update_deployment_manifests
            ;;
        "scan")
            validate_prerequisites
            local service="$2"
            local image_name="$REGISTRY_BASE/$PROJECT_ID/genesis-$service:${VERSION:-latest}"
            scan_image "$image_name" "$service"
            ;;
        "cleanup")
            validate_prerequisites
            cleanup_old_images
            ;;
        "report")
            validate_prerequisites
            generate_image_report
            ;;
        "help"|*)
            echo "Usage: $0 {setup|build|push|build-push|scan|cleanup|report} [service]"
            echo ""
            echo "Commands:"
            echo "  setup       - Create repositories and configure authentication"
            echo "  build       - Build container images (all or specific service)"
            echo "  push        - Push container images (all or specific service)"
            echo "  build-push  - Build and push container images"
            echo "  scan        - Scan specific image for vulnerabilities"
            echo "  cleanup     - Clean up old container images"
            echo "  report      - Generate container image report"
            echo ""
            echo "Environment Variables:"
            echo "  PROJECT_ID      - GCP Project ID (required)"
            echo "  ENVIRONMENT     - Environment (dev/staging/prod)"
            echo "  VERSION         - Image version tag"
            echo "  REGISTRY_REGION - Registry region (default: us-central1)"
            echo "  KEEP_IMAGES     - Number of images to keep during cleanup"
            echo "  REPORT_BUCKET   - Cloud Storage bucket for reports"
            exit 0
            ;;
    esac
}

# Execute main function with all arguments
main "$@"
