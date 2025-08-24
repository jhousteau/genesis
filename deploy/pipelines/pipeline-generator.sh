#!/usr/bin/env bash
# CI/CD Pipeline Generator
# Generates platform-specific pipeline configurations

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_error() { echo -e "${RED}❌ ERROR: $1${NC}" >&2; }
log_warning() { echo -e "${YELLOW}⚠️  WARNING: $1${NC}"; }
log_success() { echo -e "${GREEN}✅ SUCCESS: $1${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  INFO: $1${NC}"; }

# Show help
show_help() {
    cat << EOF
CI/CD Pipeline Generator

USAGE:
    $(basename "$0") [PLATFORM] [OPTIONS]

PLATFORMS:
    github-actions      Generate GitHub Actions workflow
    gitlab-ci          Generate GitLab CI configuration
    azure-devops       Generate Azure DevOps pipeline
    google-cloud-build Generate Google Cloud Build configuration
    jenkins            Generate Jenkins pipeline

OPTIONS:
    --project NAME     Project name (required)
    --type TYPE        Project type (web-app, api, cli, etc.)
    --output DIR       Output directory (default: .github/workflows or platform default)
    --template FILE    Custom template file
    --workload-identity Enable Workload Identity Federation
    --multi-env        Enable multi-environment pipeline
    --help             Show this help

PROJECT TYPES:
    web-app            Web application (React, Vue, etc.)
    api                API service (REST, GraphQL)
    cli                Command line application
    library            Shared library/package
    infrastructure     Terraform/Infrastructure
    data-pipeline      Data processing pipeline
    ml-model          Machine learning model
    microservice      Microservice application

EXAMPLES:
    # Generate GitHub Actions for web app
    $(basename "$0") github-actions --project my-app --type web-app

    # Generate GitLab CI for API with multi-environment
    $(basename "$0") gitlab-ci --project my-api --type api --multi-env

    # Generate all platforms
    $(basename "$0") all --project my-app --type web-app

EOF
}

# Parse arguments
parse_args() {
    PLATFORM=""
    PROJECT_NAME=""
    PROJECT_TYPE=""
    OUTPUT_DIR=""
    TEMPLATE_FILE=""
    WORKLOAD_IDENTITY="true"
    MULTI_ENV="false"
    GENERATE_ALL="false"

    while [[ $# -gt 0 ]]; do
        case $1 in
            github-actions|gitlab-ci|azure-devops|google-cloud-build|jenkins|all)
                PLATFORM="$1"
                if [[ "$1" == "all" ]]; then
                    GENERATE_ALL="true"
                fi
                shift
                ;;
            --project=*)
                PROJECT_NAME="${1#*=}"
                shift
                ;;
            --project)
                PROJECT_NAME="$2"
                shift 2
                ;;
            --type=*)
                PROJECT_TYPE="${1#*=}"
                shift
                ;;
            --type)
                PROJECT_TYPE="$2"
                shift 2
                ;;
            --output=*)
                OUTPUT_DIR="${1#*=}"
                shift
                ;;
            --output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --template=*)
                TEMPLATE_FILE="${1#*=}"
                shift
                ;;
            --template)
                TEMPLATE_FILE="$2"
                shift 2
                ;;
            --workload-identity)
                WORKLOAD_IDENTITY="true"
                shift
                ;;
            --no-workload-identity)
                WORKLOAD_IDENTITY="false"
                shift
                ;;
            --multi-env)
                MULTI_ENV="true"
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

# Validate arguments
validate_args() {
    if [[ -z "$PLATFORM" ]]; then
        log_error "Platform is required"
        show_help
        exit 1
    fi

    if [[ -z "$PROJECT_NAME" ]]; then
        log_error "Project name is required (--project)"
        exit 1
    fi

    if [[ -z "$PROJECT_TYPE" ]]; then
        log_warning "Project type not specified, defaulting to 'web-app'"
        PROJECT_TYPE="web-app"
    fi

    # Validate project type
    case "$PROJECT_TYPE" in
        web-app|api|cli|library|infrastructure|data-pipeline|ml-model|microservice)
            ;;
        *)
            log_error "Invalid project type: $PROJECT_TYPE"
            log_info "Valid types: web-app, api, cli, library, infrastructure, data-pipeline, ml-model, microservice"
            exit 1
            ;;
    esac
}

# Generate variables and secrets documentation
generate_variables_doc() {
    local platform="$1"
    local output_file="$2"

    cat > "$output_file" << EOF
# Required Variables and Secrets for $platform Pipeline

## Repository Variables (Settings → Secrets and variables → Actions → Variables)

### Required Variables:
- \`PROJECT_NAME\`: $PROJECT_NAME
- \`REGISTRY_REGION\`: us-central1 (or your preferred region)

### Optional Variables:
- \`WIF_PROVIDER\`: Workload Identity Federation provider
- \`WIF_SERVICE_ACCOUNT\`: Service account for WIF

## Repository Secrets (Settings → Secrets and variables → Actions → Secrets)

### For Workload Identity Federation:
- \`WIF_PROVIDER\`: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID
- \`WIF_SERVICE_ACCOUNT\`: SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com

### For Service Account Key (alternative to WIF):
- \`GCP_SA_KEY\`: Base64 encoded service account key JSON

## Environment Variables (Optional):
- \`LOG_LEVEL\`: DEBUG, INFO, WARN, ERROR
- \`DEPLOY_TIMEOUT\`: Deployment timeout in minutes (default: 30)

## Setup Instructions:

1. Enable required APIs in your GCP project:
   \`\`\`bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   \`\`\`

2. Create Artifact Registry repository:
   \`\`\`bash
   gcloud artifacts repositories create containers \\
     --repository-format=docker \\
     --location=us-central1
   \`\`\`

3. Set up Workload Identity Federation (recommended):
   \`\`\`bash
   # Create workload identity pool
   gcloud iam workload-identity-pools create github-actions \\
     --location="global" \\
     --description="GitHub Actions Pool"

   # Create provider
   gcloud iam workload-identity-pools providers create-oidc github \\
     --location="global" \\
     --workload-identity-pool="github-actions" \\
     --issuer-uri="https://token.actions.githubusercontent.com" \\
     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \\
     --attribute-condition="assertion.repository=='OWNER/REPO'"

   # Bind service account
   gcloud iam service-accounts add-iam-policy-binding \\
     SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com \\
     --role="roles/iam.workloadIdentityUser" \\
     --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/attribute.repository/OWNER/REPO"
   \`\`\`

4. Configure repository variables and secrets in GitHub

EOF
}

# Generate GitHub Actions workflow
generate_github_actions() {
    local output_dir=".github/workflows"
    [[ -n "$OUTPUT_DIR" ]] && output_dir="$OUTPUT_DIR"

    mkdir -p "$output_dir"

    local template_file
    case "$PROJECT_TYPE" in
        web-app)
            template_file="$SCRIPT_DIR/github-actions/web-app.yml"
            ;;
        api)
            template_file="$SCRIPT_DIR/github-actions/api.yml"
            ;;
        *)
            template_file="$SCRIPT_DIR/github-actions/web-app.yml"
            log_warning "Using web-app template for project type: $PROJECT_TYPE"
            ;;
    esac

    if [[ -n "$TEMPLATE_FILE" ]] && [[ -f "$TEMPLATE_FILE" ]]; then
        template_file="$TEMPLATE_FILE"
    fi

    local output_file="$output_dir/deploy.yml"

    if [[ ! -f "$template_file" ]]; then
        log_error "Template file not found: $template_file"
        exit 1
    fi

    # Copy template and customize
    cp "$template_file" "$output_file"

    # Replace placeholders
    sed -i.bak "s/\\\${{ vars.PROJECT_NAME }}/$PROJECT_NAME/g" "$output_file"
    rm -f "$output_file.bak"

    log_success "Generated GitHub Actions workflow: $output_file"

    # Generate documentation
    generate_variables_doc "GitHub Actions" "$output_dir/README-SETUP.md"
    log_info "Setup documentation: $output_dir/README-SETUP.md"
}

# Generate GitLab CI configuration
generate_gitlab_ci() {
    local output_file=".gitlab-ci.yml"
    [[ -n "$OUTPUT_DIR" ]] && output_file="$OUTPUT_DIR/.gitlab-ci.yml"

    cat > "$output_file" << EOF
# GitLab CI/CD Pipeline for $PROJECT_NAME ($PROJECT_TYPE)
# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

variables:
  PROJECT_NAME: "$PROJECT_NAME"
  REGISTRY_REGION: "us-central1"
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"

stages:
  - validate
  - build
  - test
  - security
  - deploy-dev
  - deploy-test
  - deploy-stage
  - deploy-prod

# Default image
image: google/cloud-sdk:alpine

before_script:
  - echo \$GCP_SA_KEY | base64 -d > \${HOME}/gcp-key.json
  - gcloud auth activate-service-account --key-file \${HOME}/gcp-key.json
  - gcloud config set project \$GCP_PROJECT_ID

# Validation stage
validate:
  stage: validate
  script:
    - echo "Validating configuration..."
    - |
      if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        python -m py_compile \$(find . -name "*.py")
      elif [[ -f "package.json" ]]; then
        npm ci
        npm run lint || echo "Linting issues found"
      fi
  rules:
    - if: \$CI_PIPELINE_SOURCE == "merge_request_event"
    - if: \$CI_COMMIT_BRANCH == "main"
    - if: \$CI_COMMIT_BRANCH == "develop"

# Build stage
build:
  stage: build
  services:
    - docker:20.10.16-dind
  variables:
    DOCKER_HOST: tcp://docker:2376
    DOCKER_TLS_CERTDIR: "/certs"
  script:
    - gcloud auth configure-docker \$REGISTRY_REGION-docker.pkg.dev
    - |
      IMAGE_TAG="\${CI_COMMIT_SHA}-\$(date +%Y%m%d%H%M%S)"
      IMAGE_URL="\$REGISTRY_REGION-docker.pkg.dev/\$GCP_PROJECT_ID/containers/$PROJECT_NAME"

      docker build \\
        --tag "\${IMAGE_URL}:\${IMAGE_TAG}" \\
        --tag "\${IMAGE_URL}:\$CI_ENVIRONMENT_NAME" \\
        --build-arg ENV="\$CI_ENVIRONMENT_NAME" \\
        .

      docker push "\${IMAGE_URL}:\${IMAGE_TAG}"
      docker push "\${IMAGE_URL}:\$CI_ENVIRONMENT_NAME"

      echo "IMAGE_TAG=\${IMAGE_TAG}" > build.env
      echo "IMAGE_URL=\${IMAGE_URL}" >> build.env
  artifacts:
    reports:
      dotenv: build.env
  rules:
    - if: \$CI_COMMIT_BRANCH == "main"
    - if: \$CI_COMMIT_BRANCH == "develop"

# Security scanning
security:
  stage: security
  dependencies:
    - build
  script:
    - |
      echo "Running security scans..."
      # Container scanning
      docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \\
        -v "\$PWD:/workspace" aquasec/trivy:latest \\
        image --format sarif --output trivy-report.sarif \\
        "\$IMAGE_URL:\$IMAGE_TAG"
  artifacts:
    reports:
      sast: trivy-report.sarif
  allow_failure: true
  rules:
    - if: \$CI_COMMIT_BRANCH == "main"
    - if: \$CI_COMMIT_BRANCH == "develop"

# Deploy to development
deploy-dev:
  stage: deploy-dev
  environment:
    name: development
    url: https://$PROJECT_NAME-dev.example.com
  dependencies:
    - build
  variables:
    GCP_PROJECT_ID: "$PROJECT_NAME-dev"
  script:
    - |
      gcloud run deploy "$PROJECT_NAME" \\
        --image="\$IMAGE_URL:\$IMAGE_TAG" \\
        --region="\$REGISTRY_REGION" \\
        --platform=managed \\
        --allow-unauthenticated \\
        --set-env-vars="ENV=development"
  rules:
    - if: \$CI_COMMIT_BRANCH == "develop"

# Deploy to production
deploy-prod:
  stage: deploy-prod
  environment:
    name: production
    url: https://$PROJECT_NAME.example.com
  dependencies:
    - build
  variables:
    GCP_PROJECT_ID: "$PROJECT_NAME-prod"
  script:
    - |
      gcloud run deploy "$PROJECT_NAME" \\
        --image="\$IMAGE_URL:\$IMAGE_TAG" \\
        --region="\$REGISTRY_REGION" \\
        --platform=managed \\
        --allow-unauthenticated \\
        --set-env-vars="ENV=production"
  rules:
    - if: \$CI_COMMIT_BRANCH == "main"
  when: manual
  only:
    - main
EOF

    log_success "Generated GitLab CI configuration: $output_file"

    # Generate variables documentation
    cat > "gitlab-ci-setup.md" << EOF
# GitLab CI/CD Setup for $PROJECT_NAME

## Required CI/CD Variables (Settings → CI/CD → Variables)

### Required Variables:
- \`GCP_SA_KEY\`: Base64 encoded service account key JSON
- \`GCP_PROJECT_DEV\`: Development project ID ($PROJECT_NAME-dev)
- \`GCP_PROJECT_PROD\`: Production project ID ($PROJECT_NAME-prod)

### Setup Instructions:

1. Create service account and download key:
   \`\`\`bash
   gcloud iam service-accounts create gitlab-ci
   gcloud projects add-iam-policy-binding PROJECT_ID \\
     --member="serviceAccount:gitlab-ci@PROJECT_ID.iam.gserviceaccount.com" \\
     --role="roles/run.admin"
   gcloud iam service-accounts keys create key.json \\
     --iam-account=gitlab-ci@PROJECT_ID.iam.gserviceaccount.com
   \`\`\`

2. Encode key and add to GitLab variables:
   \`\`\`bash
   base64 -w 0 key.json
   \`\`\`

EOF
    log_info "Setup documentation: gitlab-ci-setup.md"
}

# Generate Azure DevOps pipeline
generate_azure_devops() {
    local output_dir=".azure"
    [[ -n "$OUTPUT_DIR" ]] && output_dir="$OUTPUT_DIR"

    mkdir -p "$output_dir"
    local output_file="$output_dir/azure-pipelines.yml"

    cat > "$output_file" << EOF
# Azure DevOps Pipeline for $PROJECT_NAME ($PROJECT_TYPE)
# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

trigger:
  branches:
    include:
      - main
      - develop
  paths:
    exclude:
      - '**.md'
      - docs/*

pr:
  branches:
    include:
      - main

variables:
  projectName: '$PROJECT_NAME'
  registryRegion: 'us-central1'
  vmImageName: 'ubuntu-latest'

stages:
- stage: Build
  displayName: Build and Test
  jobs:
  - job: Build
    displayName: Build
    pool:
      vmImage: \$(vmImageName)

    steps:
    - task: GoogleCloudSdkTool@0
      displayName: 'Install Google Cloud SDK'

    - script: |
        echo "Building \$(projectName)"
        # Add build commands here
      displayName: 'Build Application'

    - script: |
        echo "Running tests"
        # Add test commands here
      displayName: 'Run Tests'

    - task: Docker@2
      displayName: 'Build Docker Image'
      inputs:
        containerRegistry: 'gcr-connection'
        repository: '\$(projectName)'
        command: 'build'
        Dockerfile: 'Dockerfile'
        tags: |
          \$(Build.BuildId)
          latest

- stage: Deploy
  displayName: Deploy
  dependsOn: Build
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  jobs:
  - deployment: Deploy
    displayName: Deploy to GCP
    pool:
      vmImage: \$(vmImageName)
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: GoogleCloudSdkTool@0
            displayName: 'Install Google Cloud SDK'

          - script: |
              gcloud run deploy \$(projectName) \\
                --image=gcr.io/PROJECT_ID/\$(projectName):\$(Build.BuildId) \\
                --region=\$(registryRegion) \\
                --platform=managed \\
                --allow-unauthenticated
            displayName: 'Deploy to Cloud Run'
EOF

    log_success "Generated Azure DevOps pipeline: $output_file"
}

# Generate Google Cloud Build configuration
generate_google_cloud_build() {
    local output_file="cloudbuild.yaml"
    [[ -n "$OUTPUT_DIR" ]] && output_file="$OUTPUT_DIR/cloudbuild.yaml"

    cat > "$output_file" << EOF
# Google Cloud Build Configuration for $PROJECT_NAME ($PROJECT_TYPE)
# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

steps:
  # Install dependencies and run tests
  - name: 'gcr.io/cloud-builders/docker'
    id: 'test'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        echo "Running tests for $PROJECT_NAME"
        if [[ -f "requirements.txt" ]]; then
          docker run --rm -v "\$PWD:/workspace" python:3.11 \\
            bash -c "cd /workspace && pip install -r requirements.txt && python -m pytest"
        elif [[ -f "package.json" ]]; then
          docker run --rm -v "\$PWD:/workspace" node:18 \\
            bash -c "cd /workspace && npm ci && npm test"
        fi

  # Build container image
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build'
    args:
      - 'build'
      - '-t'
      - '\$_REGION-docker.pkg.dev/\$PROJECT_ID/containers/$PROJECT_NAME:\$BUILD_ID'
      - '-t'
      - '\$_REGION-docker.pkg.dev/\$PROJECT_ID/containers/$PROJECT_NAME:latest'
      - '--build-arg'
      - 'ENV=\$_ENVIRONMENT'
      - '.'
    waitFor: ['test']

  # Push container image
  - name: 'gcr.io/cloud-builders/docker'
    id: 'push'
    args:
      - 'push'
      - '--all-tags'
      - '\$_REGION-docker.pkg.dev/\$PROJECT_ID/containers/$PROJECT_NAME'
    waitFor: ['build']

  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    id: 'deploy'
    args:
      - 'run'
      - 'deploy'
      - '$PROJECT_NAME'
      - '--image=\$_REGION-docker.pkg.dev/\$PROJECT_ID/containers/$PROJECT_NAME:\$BUILD_ID'
      - '--region=\$_REGION'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--set-env-vars=ENV=\$_ENVIRONMENT'
    waitFor: ['push']

# Substitutions
substitutions:
  _REGION: 'us-central1'
  _ENVIRONMENT: 'production'

# Build configuration
options:
  logging: CLOUD_LOGGING_ONLY
  machineType: 'E2_STANDARD_4'

# Build timeout
timeout: '1200s'

images:
  - '\$_REGION-docker.pkg.dev/\$PROJECT_ID/containers/$PROJECT_NAME:\$BUILD_ID'
  - '\$_REGION-docker.pkg.dev/\$PROJECT_ID/containers/$PROJECT_NAME:latest'
EOF

    log_success "Generated Cloud Build configuration: $output_file"
}

# Generate Jenkins pipeline
generate_jenkins() {
    local output_file="Jenkinsfile"
    [[ -n "$OUTPUT_DIR" ]] && output_file="$OUTPUT_DIR/Jenkinsfile"

    cat > "$output_file" << EOF
// Jenkins Pipeline for $PROJECT_NAME ($PROJECT_TYPE)
// Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

pipeline {
    agent any

    environment {
        PROJECT_NAME = '$PROJECT_NAME'
        REGISTRY_REGION = 'us-central1'
        GCP_PROJECT_ID = credentials('gcp-project-id')
        GOOGLE_APPLICATION_CREDENTIALS = credentials('gcp-service-account')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Validate') {
            steps {
                script {
                    echo "Validating $PROJECT_NAME"
                    if (fileExists('requirements.txt')) {
                        sh '''
                            python3 -m pip install -r requirements.txt
                            python3 -m py_compile \$(find . -name "*.py")
                        '''
                    } else if (fileExists('package.json')) {
                        sh '''
                            npm ci
                            npm run lint || echo "Linting issues found"
                        '''
                    }
                }
            }
        }

        stage('Test') {
            steps {
                script {
                    echo "Running tests"
                    if (fileExists('requirements.txt')) {
                        sh 'python3 -m pytest --junitxml=test-results.xml'
                    } else if (fileExists('package.json')) {
                        sh 'npm test'
                    }
                }
            }
            post {
                always {
                    publishTestResults testResultsPattern: 'test-results.xml'
                }
            }
        }

        stage('Build') {
            steps {
                script {
                    def imageTag = "\${env.BUILD_ID}-\$(date +%Y%m%d%H%M%S)"
                    def imageUrl = "\${REGISTRY_REGION}-docker.pkg.dev/\${GCP_PROJECT_ID}/containers/\${PROJECT_NAME}"

                    sh """
                        gcloud auth activate-service-account --key-file=\${GOOGLE_APPLICATION_CREDENTIALS}
                        gcloud config set project \${GCP_PROJECT_ID}
                        gcloud auth configure-docker \${REGISTRY_REGION}-docker.pkg.dev

                        docker build \\
                            -t "\${imageUrl}:\${imageTag}" \\
                            -t "\${imageUrl}:latest" \\
                            --build-arg ENV=production \\
                            .

                        docker push "\${imageUrl}:\${imageTag}"
                        docker push "\${imageUrl}:latest"
                    """

                    env.IMAGE_TAG = imageTag
                    env.IMAGE_URL = imageUrl
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                script {
                    sh """
                        gcloud run deploy \${PROJECT_NAME} \\
                            --image="\${IMAGE_URL}:\${IMAGE_TAG}" \\
                            --region=\${REGISTRY_REGION} \\
                            --platform=managed \\
                            --allow-unauthenticated \\
                            --set-env-vars=ENV=production
                    """
                }
            }
        }

        stage('Validate Deployment') {
            when {
                branch 'main'
            }
            steps {
                script {
                    def serviceUrl = sh(
                        script: "gcloud run services describe \${PROJECT_NAME} --region=\${REGISTRY_REGION} --format='value(status.url)'",
                        returnStdout: true
                    ).trim()

                    sh """
                        for i in {1..30}; do
                            if curl -f "\${serviceUrl}/health" --max-time 10; then
                                echo "Health check passed"
                                break
                            fi
                            sleep 10
                        done
                    """
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            echo "Pipeline succeeded for $PROJECT_NAME"
        }
        failure {
            echo "Pipeline failed for $PROJECT_NAME"
        }
    }
}
EOF

    log_success "Generated Jenkins pipeline: $output_file"
}

# Main function
main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi

    parse_args "$@"
    validate_args

    log_info "Generating CI/CD pipeline for $PROJECT_NAME ($PROJECT_TYPE)"

    if [[ "$GENERATE_ALL" == "true" ]]; then
        log_info "Generating all platform configurations..."
        generate_github_actions
        generate_gitlab_ci
        generate_azure_devops
        generate_google_cloud_build
        generate_jenkins
        log_success "Generated all platform configurations"
    else
        case "$PLATFORM" in
            github-actions)
                generate_github_actions
                ;;
            gitlab-ci)
                generate_gitlab_ci
                ;;
            azure-devops)
                generate_azure_devops
                ;;
            google-cloud-build)
                generate_google_cloud_build
                ;;
            jenkins)
                generate_jenkins
                ;;
            *)
                log_error "Unknown platform: $PLATFORM"
                exit 1
                ;;
        esac
    fi

    echo ""
    log_success "Pipeline generation completed!"
    echo ""
    echo "Next steps:"
    echo "  1. Review generated pipeline configuration"
    echo "  2. Set up required variables and secrets"
    echo "  3. Configure service accounts and permissions"
    echo "  4. Test pipeline with a sample commit"
    echo "  5. Configure environment-specific settings"
}

# Run main function
main "$@"
