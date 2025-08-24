#!/usr/bin/env bash
# Multi-Platform Workload Identity Federation Setup
# Part of Universal Project Platform - Agent 5 Isolation Layer
# Supports GitHub Actions, GitLab CI, Azure DevOps, and other CI/CD platforms

set -euo pipefail

# Script metadata
MULTI_WIF_VERSION="2.0.0"
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

# Platform configurations
declare -A PLATFORM_CONFIGS=(
    ["github"]="https://token.actions.githubusercontent.com"
    ["gitlab"]="https://gitlab.com"
    ["azure"]="https://dev.azure.com"
    ["bitbucket"]="https://api.bitbucket.org"
    ["jenkins"]="custom"
    ["circleci"]="https://oidc.circleci.com/org"
)

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "══════════════════════════════════════════════════════════════"
    echo "🔐 MULTI-PLATFORM WORKLOAD IDENTITY FEDERATION v${MULTI_WIF_VERSION}"
    echo "   Universal Project Platform - Agent 5 Isolation Layer"
    echo "══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Show supported platforms
show_supported_platforms() {
    echo -e "${WHITE}Supported CI/CD Platforms:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "• GitHub Actions     - OIDC token authentication"
    echo "• GitLab CI/CD      - JWT token authentication"
    echo "• Azure DevOps      - Service connection authentication"
    echo "• Bitbucket Pipelines - OIDC token authentication"
    echo "• Jenkins           - Custom OIDC provider"
    echo "• CircleCI          - OIDC token authentication"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Validate platform-specific parameters
validate_platform_parameters() {
    local platform="$1"

    case "$platform" in
        "github")
            : "${GITHUB_REPO:?GITHUB_REPO is required (format: owner/repo)}"
            : "${GITHUB_ACTOR:=$GITHUB_REPO}"

            if [[ ! "$GITHUB_REPO" =~ ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$ ]]; then
                log_error "Invalid GITHUB_REPO format. Expected: owner/repo"
                return 1
            fi
            ;;
        "gitlab")
            : "${GITLAB_PROJECT_PATH:?GITLAB_PROJECT_PATH is required (format: group/project)}"
            : "${GITLAB_INSTANCE:=https://gitlab.com}"

            if [[ ! "$GITLAB_PROJECT_PATH" =~ ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$ ]]; then
                log_error "Invalid GITLAB_PROJECT_PATH format. Expected: group/project"
                return 1
            fi
            ;;
        "azure")
            : "${AZURE_ORGANIZATION:?AZURE_ORGANIZATION is required}"
            : "${AZURE_PROJECT:?AZURE_PROJECT is required}"
            : "${AZURE_REPO:?AZURE_REPO is required}"
            ;;
        "bitbucket")
            : "${BITBUCKET_WORKSPACE:?BITBUCKET_WORKSPACE is required}"
            : "${BITBUCKET_REPO:?BITBUCKET_REPO is required}"
            ;;
        "jenkins")
            : "${JENKINS_URL:?JENKINS_URL is required}"
            : "${OIDC_ISSUER:?OIDC_ISSUER is required for Jenkins}"
            ;;
        "circleci")
            : "${CIRCLECI_ORG_ID:?CIRCLECI_ORG_ID is required}"
            : "${CIRCLECI_PROJECT_ID:?CIRCLECI_PROJECT_ID is required}"
            ;;
        *)
            log_error "Unsupported platform: $platform"
            log_info "Supported platforms: ${!PLATFORM_CONFIGS[*]}"
            return 1
            ;;
    esac
}

# Get platform-specific OIDC issuer
get_oidc_issuer() {
    local platform="$1"

    case "$platform" in
        "github")
            echo "https://token.actions.githubusercontent.com"
            ;;
        "gitlab")
            echo "${GITLAB_INSTANCE:-https://gitlab.com}"
            ;;
        "azure")
            echo "https://vstoken.dev.azure.com/${AZURE_ORGANIZATION_ID}"
            ;;
        "bitbucket")
            echo "https://api.bitbucket.org/2.0/workspaces/${BITBUCKET_WORKSPACE}/pipelines-config/identity/oidc"
            ;;
        "jenkins")
            echo "${OIDC_ISSUER}"
            ;;
        "circleci")
            echo "https://oidc.circleci.com/org/${CIRCLECI_ORG_ID}"
            ;;
        *)
            log_error "Unknown platform: $platform"
            return 1
            ;;
    esac
}

# Get platform-specific attribute mapping
get_attribute_mapping() {
    local platform="$1"

    case "$platform" in
        "github")
            echo 'google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner,attribute.ref=assertion.ref'
            ;;
        "gitlab")
            echo 'google.subject=assertion.sub,attribute.project_path=assertion.project_path,attribute.namespace_path=assertion.namespace_path,attribute.ref=assertion.ref,attribute.user_login=assertion.user_login'
            ;;
        "azure")
            echo 'google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref,attribute.build_id=assertion.build_id'
            ;;
        "bitbucket")
            echo 'google.subject=assertion.sub,attribute.repository_full_name=assertion.repository_full_name,attribute.workspace=assertion.workspace'
            ;;
        "jenkins")
            echo 'google.subject=assertion.sub,attribute.job_name=assertion.job_name,attribute.build_number=assertion.build_number'
            ;;
        "circleci")
            echo 'google.subject=assertion.sub,attribute.project_id=assertion.project_id,attribute.org_id=assertion.org_id'
            ;;
        *)
            log_error "Unknown platform: $platform"
            return 1
            ;;
    esac
}

# Get platform-specific attribute condition
get_attribute_condition() {
    local platform="$1"

    case "$platform" in
        "github")
            echo "assertion.repository_owner == '$(echo "$GITHUB_REPO" | cut -d'/' -f1)'"
            ;;
        "gitlab")
            echo "assertion.project_path == '${GITLAB_PROJECT_PATH}'"
            ;;
        "azure")
            echo "assertion.repository == '${AZURE_REPO}'"
            ;;
        "bitbucket")
            echo "assertion.workspace == '${BITBUCKET_WORKSPACE}'"
            ;;
        "jenkins")
            echo "assertion.job_name == '${JENKINS_JOB_NAME:-}'"
            ;;
        "circleci")
            echo "assertion.org_id == '${CIRCLECI_ORG_ID}'"
            ;;
        *)
            log_error "Unknown platform: $platform"
            return 1
            ;;
    esac
}

# Setup WIF for specific platform
setup_platform_wif() {
    local platform="$1"

    log_step "Setting up Workload Identity Federation for: $platform"

    # Validate parameters
    validate_platform_parameters "$platform"

    # Common parameters
    local project_id="${PROJECT_ID:?PROJECT_ID is required}"
    local service_account_name="${SERVICE_ACCOUNT_NAME:?SERVICE_ACCOUNT_NAME is required}"
    local pool_id="${POOL_ID:-${platform}-wif-pool}"
    local provider_id="${PROVIDER_ID:-${platform}-provider}"
    local location="${LOCATION:-global}"

    # Platform-specific parameters
    local oidc_issuer attribute_mapping attribute_condition
    oidc_issuer=$(get_oidc_issuer "$platform")
    attribute_mapping=$(get_attribute_mapping "$platform")
    attribute_condition=$(get_attribute_condition "$platform")

    log_info "Platform: $platform"
    log_info "OIDC Issuer: $oidc_issuer"
    log_info "Pool ID: $pool_id"
    log_info "Provider ID: $provider_id"

    # Enable required APIs
    enable_required_apis

    # Create service account
    local sa_email
    sa_email=$(create_service_account "$service_account_name" "$platform")

    # Create workload identity pool
    create_workload_identity_pool "$pool_id" "$platform"

    # Create OIDC provider
    create_oidc_provider "$pool_id" "$provider_id" "$oidc_issuer" "$attribute_mapping" "$attribute_condition" "$platform"

    # Configure IAM bindings
    configure_platform_iam_bindings "$sa_email" "$pool_id" "$platform"

    # Generate platform-specific configuration
    generate_platform_config "$platform" "$sa_email" "$pool_id" "$provider_id"

    # Test configuration
    test_wif_setup "$platform" "$sa_email" "$pool_id" "$provider_id"

    log_success "Workload Identity Federation setup complete for $platform"
}

# Enable required APIs
enable_required_apis() {
    log_step "Enabling required APIs..."

    local apis=(
        "iamcredentials.googleapis.com"
        "cloudresourcemanager.googleapis.com"
        "sts.googleapis.com"
    )

    for api in "${apis[@]}"; do
        if gcloud services enable "$api" --project="$PROJECT_ID"; then
            log_success "Enabled $api"
        else
            log_error "Failed to enable $api"
            return 1
        fi
    done
}

# Create service account
create_service_account() {
    local sa_name="$1"
    local platform="$2"

    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"

    if gcloud iam service-accounts describe "$sa_email" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_warning "Service account already exists: $sa_email"
    else
        if gcloud iam service-accounts create "$sa_name" \
            --display-name="$platform CI/CD Service Account" \
            --description="Service account for $platform via Workload Identity Federation" \
            --project="$PROJECT_ID"; then
            log_success "Created service account: $sa_email"
        else
            log_error "Failed to create service account"
            return 1
        fi
    fi

    echo "$sa_email"
}

# Create workload identity pool
create_workload_identity_pool() {
    local pool_id="$1"
    local platform="$2"

    if gcloud iam workload-identity-pools describe "$pool_id" \
        --location="$LOCATION" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_warning "Workload Identity Pool already exists: $pool_id"
    else
        if gcloud iam workload-identity-pools create "$pool_id" \
            --location="$LOCATION" \
            --display-name="$platform Workload Identity Pool" \
            --description="Pool for $platform CI/CD authentication" \
            --project="$PROJECT_ID"; then
            log_success "Created Workload Identity Pool: $pool_id"
        else
            log_error "Failed to create Workload Identity Pool"
            return 1
        fi
    fi
}

# Create OIDC provider
create_oidc_provider() {
    local pool_id="$1"
    local provider_id="$2"
    local oidc_issuer="$3"
    local attribute_mapping="$4"
    local attribute_condition="$5"
    local platform="$6"

    if gcloud iam workload-identity-pools providers describe "$provider_id" \
        --workload-identity-pool="$pool_id" \
        --location="$LOCATION" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_warning "OIDC Provider already exists: $provider_id"
    else
        if gcloud iam workload-identity-pools providers create-oidc "$provider_id" \
            --workload-identity-pool="$pool_id" \
            --location="$LOCATION" \
            --issuer-uri="$oidc_issuer" \
            --attribute-mapping="$attribute_mapping" \
            --attribute-condition="$attribute_condition" \
            --project="$PROJECT_ID"; then
            log_success "Created OIDC Provider: $provider_id"
        else
            log_error "Failed to create OIDC Provider"
            return 1
        fi
    fi
}

# Configure platform-specific IAM bindings
configure_platform_iam_bindings() {
    local sa_email="$1"
    local pool_id="$2"
    local platform="$3"

    log_step "Configuring IAM bindings for $platform..."

    local project_number
    project_number=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

    local principal
    case "$platform" in
        "github")
            principal="principalSet://iam.googleapis.com/projects/$project_number/locations/$LOCATION/workloadIdentityPools/$pool_id/attribute.repository/$GITHUB_REPO"
            ;;
        "gitlab")
            principal="principalSet://iam.googleapis.com/projects/$project_number/locations/$LOCATION/workloadIdentityPools/$pool_id/attribute.project_path/$GITLAB_PROJECT_PATH"
            ;;
        "azure")
            principal="principalSet://iam.googleapis.com/projects/$project_number/locations/$LOCATION/workloadIdentityPools/$pool_id/attribute.repository/$AZURE_REPO"
            ;;
        "bitbucket")
            principal="principalSet://iam.googleapis.com/projects/$project_number/locations/$LOCATION/workloadIdentityPools/$pool_id/attribute.workspace/$BITBUCKET_WORKSPACE"
            ;;
        "jenkins")
            principal="principalSet://iam.googleapis.com/projects/$project_number/locations/$LOCATION/workloadIdentityPools/$pool_id/attribute.job_name/${JENKINS_JOB_NAME:-*}"
            ;;
        "circleci")
            principal="principalSet://iam.googleapis.com/projects/$project_number/locations/$LOCATION/workloadIdentityPools/$pool_id/attribute.org_id/$CIRCLECI_ORG_ID"
            ;;
        *)
            log_error "Unknown platform for IAM binding: $platform"
            return 1
            ;;
    esac

    if gcloud iam service-accounts add-iam-policy-binding "$sa_email" \
        --role="roles/iam.workloadIdentityUser" \
        --member="$principal" \
        --project="$PROJECT_ID"; then
        log_success "Added workload identity binding for $platform"
    else
        log_error "Failed to add workload identity binding"
        return 1
    fi
}

# Generate platform-specific configuration
generate_platform_config() {
    local platform="$1"
    local sa_email="$2"
    local pool_id="$3"
    local provider_id="$4"

    log_step "Generating $platform configuration..."

    local project_number
    project_number=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
    local wif_provider="projects/$project_number/locations/$LOCATION/workloadIdentityPools/$pool_id/providers/$provider_id"

    case "$platform" in
        "github")
            generate_github_config "$sa_email" "$wif_provider"
            ;;
        "gitlab")
            generate_gitlab_config "$sa_email" "$wif_provider"
            ;;
        "azure")
            generate_azure_config "$sa_email" "$wif_provider"
            ;;
        "bitbucket")
            generate_bitbucket_config "$sa_email" "$wif_provider"
            ;;
        "jenkins")
            generate_jenkins_config "$sa_email" "$wif_provider"
            ;;
        "circleci")
            generate_circleci_config "$sa_email" "$wif_provider"
            ;;
    esac
}

# Generate GitHub Actions configuration
generate_github_config() {
    local sa_email="$1"
    local wif_provider="$2"

    cat > "github-actions-wif.yml" <<EOF
# GitHub Actions Workload Identity Federation
# Add this to your .github/workflows/ directory

name: Deploy with WIF
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Authenticate to Google Cloud
      uses: google-github-actions/auth@v2
      with:
        workload_identity_provider: '$wif_provider'
        service_account: '$sa_email'

    - name: Set up Cloud SDK
      uses: google-github-actions/setup-gcloud@v2

    - name: Configure gcloud
      run: |
        gcloud config set project $PROJECT_ID
        gcloud auth list

    - name: Deploy your application
      run: |
        echo "Add your deployment commands here"
EOF

    log_success "Generated: github-actions-wif.yml"
}

# Generate GitLab CI configuration
generate_gitlab_config() {
    local sa_email="$1"
    local wif_provider="$2"

    cat > ".gitlab-ci-wif.yml" <<EOF
# GitLab CI/CD Workload Identity Federation
# Add this to your .gitlab-ci.yml

variables:
  GOOGLE_WORKLOAD_IDENTITY_PROVIDER: '$wif_provider'
  GOOGLE_SERVICE_ACCOUNT: '$sa_email'
  PROJECT_ID: '$PROJECT_ID'

before_script:
  - echo \${CI_JOB_JWT_V2} > /tmp/ci_job_jwt
  - gcloud auth login --brief --cred-file=/tmp/ci_job_jwt
  - gcloud config set project \${PROJECT_ID}

deploy:
  stage: deploy
  image: google/cloud-sdk:alpine
  id_tokens:
    GITLAB_OIDC_TOKEN:
      aud: https://gitlab.example.com
  script:
    - gcloud auth list
    - echo "Add your deployment commands here"
  only:
    - main
EOF

    log_success "Generated: .gitlab-ci-wif.yml"
}

# Generate Azure DevOps configuration
generate_azure_config() {
    local sa_email="$1"
    local wif_provider="$2"

    cat > "azure-pipelines-wif.yml" <<EOF
# Azure DevOps Workload Identity Federation
# Add this to your azure-pipelines.yml

trigger:
- main

pool:
  vmImage: 'ubuntu-latest'

variables:
  GOOGLE_WORKLOAD_IDENTITY_PROVIDER: '$wif_provider'
  GOOGLE_SERVICE_ACCOUNT: '$sa_email'
  PROJECT_ID: '$PROJECT_ID'

steps:
- task: GoogleCloudSdkTool@0
  displayName: 'Install Google Cloud SDK'

- script: |
    echo \$(System.AccessToken) > /tmp/azure_token
    gcloud auth login --brief --cred-file=/tmp/azure_token
    gcloud config set project \$(PROJECT_ID)
    gcloud auth list
  displayName: 'Authenticate to Google Cloud'

- script: |
    echo "Add your deployment commands here"
  displayName: 'Deploy application'
EOF

    log_success "Generated: azure-pipelines-wif.yml"
}

# Generate Bitbucket configuration
generate_bitbucket_config() {
    local sa_email="$1"
    local wif_provider="$2"

    cat > "bitbucket-pipelines-wif.yml" <<EOF
# Bitbucket Pipelines Workload Identity Federation
# Add this to your bitbucket-pipelines.yml

pipelines:
  default:
    - step:
        name: Deploy with WIF
        image: google/cloud-sdk:alpine
        oidc: true
        script:
          - export GOOGLE_WORKLOAD_IDENTITY_PROVIDER='$wif_provider'
          - export GOOGLE_SERVICE_ACCOUNT='$sa_email'
          - export PROJECT_ID='$PROJECT_ID'
          - echo \$BITBUCKET_STEP_OIDC_TOKEN > /tmp/oidc_token
          - gcloud auth login --brief --cred-file=/tmp/oidc_token
          - gcloud config set project \$PROJECT_ID
          - gcloud auth list
          - echo "Add your deployment commands here"
EOF

    log_success "Generated: bitbucket-pipelines-wif.yml"
}

# Generate Jenkins configuration
generate_jenkins_config() {
    local sa_email="$1"
    local wif_provider="$2"

    cat > "Jenkinsfile-wif" <<EOF
// Jenkins Workload Identity Federation
// Add this to your Jenkinsfile

pipeline {
    agent any

    environment {
        GOOGLE_WORKLOAD_IDENTITY_PROVIDER = '$wif_provider'
        GOOGLE_SERVICE_ACCOUNT = '$sa_email'
        PROJECT_ID = '$PROJECT_ID'
    }

    stages {
        stage('Authenticate') {
            steps {
                script {
                    // Assumes Jenkins OIDC plugin is configured
                    writeFile file: '/tmp/oidc_token', text: env.OIDC_TOKEN
                    sh 'gcloud auth login --brief --cred-file=/tmp/oidc_token'
                    sh 'gcloud config set project \${PROJECT_ID}'
                    sh 'gcloud auth list'
                }
            }
        }

        stage('Deploy') {
            steps {
                sh 'echo "Add your deployment commands here"'
            }
        }
    }
}
EOF

    log_success "Generated: Jenkinsfile-wif"
}

# Generate CircleCI configuration
generate_circleci_config() {
    local sa_email="$1"
    local wif_provider="$2"

    mkdir -p .circleci
    cat > ".circleci/config-wif.yml" <<EOF
# CircleCI Workload Identity Federation
# Add this to your .circleci/config.yml

version: 2.1

orbs:
  gcp-cli: circleci/gcp-cli@3.1.0

jobs:
  deploy:
    executor: gcp-cli/google
    steps:
      - checkout
      - run:
          name: Authenticate with Google Cloud
          command: |
            echo \$CIRCLE_OIDC_TOKEN > /tmp/oidc_token
            gcloud auth login --brief --cred-file=/tmp/oidc_token
            gcloud config set project $PROJECT_ID
            gcloud auth list
      - run:
          name: Deploy application
          command: |
            echo "Add your deployment commands here"

workflows:
  deploy:
    jobs:
      - deploy:
          context: gcp-wif
          filters:
            branches:
              only: main
EOF

    log_success "Generated: .circleci/config-wif.yml"
}

# Test WIF setup
test_wif_setup() {
    local platform="$1"
    local sa_email="$2"
    local pool_id="$3"
    local provider_id="$4"

    log_step "Testing Workload Identity Federation setup..."

    # Basic validation - check if resources exist
    if gcloud iam workload-identity-pools describe "$pool_id" \
        --location="$LOCATION" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_success "Workload Identity Pool accessible"
    else
        log_error "Cannot access Workload Identity Pool"
        return 1
    fi

    if gcloud iam workload-identity-pools providers describe "$provider_id" \
        --workload-identity-pool="$pool_id" \
        --location="$LOCATION" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_success "OIDC Provider accessible"
    else
        log_error "Cannot access OIDC Provider"
        return 1
    fi

    if gcloud iam service-accounts describe "$sa_email" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_success "Service account accessible"
    else
        log_error "Cannot access service account"
        return 1
    fi

    log_success "Workload Identity Federation test completed"
}

# Show setup instructions
show_setup_instructions() {
    local platform="$1"

    echo ""
    echo -e "${CYAN}═══ SETUP INSTRUCTIONS FOR $platform ═══${NC}"
    echo ""

    case "$platform" in
        "github")
            echo "1. Copy the generated github-actions-wif.yml to .github/workflows/"
            echo "2. Ensure your workflow has 'id-token: write' permission"
            echo "3. Push to trigger the workflow"
            ;;
        "gitlab")
            echo "1. Copy the generated .gitlab-ci-wif.yml content to .gitlab-ci.yml"
            echo "2. Configure GitLab OIDC settings if needed"
            echo "3. Push to trigger the pipeline"
            ;;
        "azure")
            echo "1. Copy the generated azure-pipelines-wif.yml to your repository"
            echo "2. Configure Azure DevOps service connection"
            echo "3. Update pipeline references"
            ;;
        "bitbucket")
            echo "1. Copy the generated bitbucket-pipelines-wif.yml to bitbucket-pipelines.yml"
            echo "2. Enable OIDC in Bitbucket repository settings"
            echo "3. Push to trigger the pipeline"
            ;;
        "jenkins")
            echo "1. Install and configure Jenkins OIDC plugin"
            echo "2. Copy the generated Jenkinsfile-wif to your repository"
            echo "3. Configure Jenkins job to use the Jenkinsfile"
            ;;
        "circleci")
            echo "1. Copy the generated .circleci/config-wif.yml to .circleci/config.yml"
            echo "2. Configure CircleCI OIDC context"
            echo "3. Push to trigger the workflow"
            ;;
    esac

    echo ""
    echo -e "${YELLOW}Important Notes:${NC}"
    echo "• Test the authentication in a safe environment first"
    echo "• Monitor the initial deployments for any issues"
    echo "• Review and adjust IAM permissions as needed"
    echo "• Keep the generated configuration files secure"
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        "setup")
            local platform="${2:-}"
            if [[ -z "$platform" ]]; then
                log_error "Platform required"
                echo "Usage: $0 setup <platform>"
                echo "Supported platforms: ${!PLATFORM_CONFIGS[*]}"
                exit 1
            fi

            print_banner
            show_supported_platforms
            setup_platform_wif "$platform"
            show_setup_instructions "$platform"
            ;;
        "platforms")
            print_banner
            show_supported_platforms
            ;;
        "help"|"--help"|"-h")
            print_banner
            echo "Multi-Platform Workload Identity Federation Setup"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  setup <platform>         Setup WIF for specific platform"
            echo "  platforms               Show supported platforms"
            echo "  help                    Show this help"
            echo ""
            echo "Platforms: ${!PLATFORM_CONFIGS[*]}"
            echo ""
            echo "Required Environment Variables:"
            echo "  PROJECT_ID              GCP Project ID"
            echo "  SERVICE_ACCOUNT_NAME    Service account name"
            echo ""
            echo "Platform-specific variables (see documentation):"
            echo "  GitHub: GITHUB_REPO"
            echo "  GitLab: GITLAB_PROJECT_PATH, GITLAB_INSTANCE"
            echo "  Azure: AZURE_ORGANIZATION, AZURE_PROJECT, AZURE_REPO"
            echo "  Bitbucket: BITBUCKET_WORKSPACE, BITBUCKET_REPO"
            echo "  Jenkins: JENKINS_URL, OIDC_ISSUER"
            echo "  CircleCI: CIRCLECI_ORG_ID, CIRCLECI_PROJECT_ID"
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
