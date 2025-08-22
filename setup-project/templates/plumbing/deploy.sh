#!/usr/bin/env bash
# Universal Deployment Script
# Handles deployments across all environments with safety checks

set -euo pipefail

# Default values
ENVIRONMENT="${ENV:-dev}"
REGION="${REGION:-us-central1}"
AUTO_APPROVE="false"
CANARY_PERCENT=""
DRY_RUN="false"
ROLLBACK_ON_FAILURE="true"

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env=*)
            ENVIRONMENT="${1#*=}"
            shift
            ;;
        --region=*)
            REGION="${1#*=}"
            shift
            ;;
        --auto-approve)
            AUTO_APPROVE="true"
            shift
            ;;
        --canary=*)
            CANARY_PERCENT="${1#*=}"
            shift
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --no-rollback)
            ROLLBACK_ON_FAILURE="false"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --env=ENV              Environment (dev/test/stage/prod)"
            echo "  --region=REGION        GCP region"
            echo "  --auto-approve         Skip confirmation"
            echo "  --canary=PERCENT       Deploy as canary (e.g., --canary=10)"
            echo "  --dry-run             Show what would be deployed"
            echo "  --no-rollback         Don't rollback on failure"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Load project configuration
if [[ -f ".project-config.yaml" ]]; then
    PROJECT_NAME=$(grep "name:" .project-config.yaml | head -1 | awk '{print $2}')
    PROJECT_TYPE=$(grep "type:" .project-config.yaml | head -1 | awk '{print $2}')
else
    echo -e "${RED}❌ No .project-config.yaml found${NC}"
    exit 1
fi

# Set project ID based on environment
PROJECT_ID="${PROJECT_NAME}-${ENVIRONMENT}"

echo -e "${BLUE}🚀 Deployment Configuration${NC}"
echo "===================================="
echo "Project: ${PROJECT_NAME}"
echo "Type: ${PROJECT_TYPE}"
echo "Environment: ${ENVIRONMENT}"
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
if [[ -n "${CANARY_PERCENT}" ]]; then
    echo "Canary: ${CANARY_PERCENT}%"
fi
echo "===================================="

# Environment-specific checks
case ${ENVIRONMENT} in
    prod|production)
        echo -e "${RED}⚠️  PRODUCTION DEPLOYMENT${NC}"
        if [[ "${CONFIRM_PROD:-}" != "I_UNDERSTAND" ]]; then
            echo -e "${RED}Set CONFIRM_PROD=I_UNDERSTAND to deploy to production${NC}"
            exit 1
        fi
        if [[ "${AUTO_APPROVE}" != "true" ]]; then
            read -p "Type 'deploy-prod' to confirm: " confirm
            if [[ "${confirm}" != "deploy-prod" ]]; then
                echo -e "${RED}Deployment cancelled${NC}"
                exit 1
            fi
        fi
        ;;
    stage|staging)
        echo -e "${YELLOW}Staging deployment${NC}"
        ;;
    test)
        echo -e "${BLUE}Test deployment${NC}"
        ;;
    dev|development)
        echo -e "${GREEN}Development deployment${NC}"
        ;;
    *)
        echo -e "${RED}Unknown environment: ${ENVIRONMENT}${NC}"
        exit 1
        ;;
esac

# Pre-deployment validation
echo -e "\n${BLUE}Running pre-deployment checks...${NC}"

# 1. Run tests
if make test > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Tests passed${NC}"
else
    echo -e "${RED}❌ Tests failed${NC}"
    if [[ "${ENVIRONMENT}" == "prod" ]]; then
        exit 1
    fi
fi

# 2. Run linting
if make lint > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Linting passed${NC}"
else
    echo -e "${YELLOW}⚠️  Linting issues found${NC}"
fi

# 3. Check for uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}⚠️  Uncommitted changes detected${NC}"
    if [[ "${ENVIRONMENT}" == "prod" ]]; then
        echo -e "${RED}Cannot deploy to production with uncommitted changes${NC}"
        exit 1
    fi
fi

# 4. Security scan
echo -e "${BLUE}Running security scan...${NC}"
if command -v detect-secrets &> /dev/null; then
    if detect-secrets scan 2>/dev/null | grep -q "secret"; then
        echo -e "${RED}❌ Potential secrets detected!${NC}"
        exit 1
    fi
fi

# Get deployment ID
DEPLOYMENT_ID="${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD)"
echo -e "\n${BLUE}Deployment ID: ${DEPLOYMENT_ID}${NC}"

# Dry run check
if [[ "${DRY_RUN}" == "true" ]]; then
    echo -e "\n${YELLOW}DRY RUN MODE - No actual deployment${NC}"
    echo "Would deploy:"
    echo "  - Docker image: ${PROJECT_NAME}:${DEPLOYMENT_ID}"
    echo "  - To project: ${PROJECT_ID}"
    echo "  - In region: ${REGION}"
    exit 0
fi

# Build phase
echo -e "\n${BLUE}Building artifacts...${NC}"

# Build Docker image if Dockerfile exists
if [[ -f "Dockerfile" ]]; then
    echo "Building Docker image..."
    docker build -t "${PROJECT_NAME}:${DEPLOYMENT_ID}" \
        --build-arg ENV="${ENVIRONMENT}" \
        --build-arg VERSION="${DEPLOYMENT_ID}" \
        .
    
    # Tag for registry
    REGISTRY_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/containers/${PROJECT_NAME}"
    docker tag "${PROJECT_NAME}:${DEPLOYMENT_ID}" "${REGISTRY_URL}:${DEPLOYMENT_ID}"
    docker tag "${PROJECT_NAME}:${DEPLOYMENT_ID}" "${REGISTRY_URL}:${ENVIRONMENT}"
    
    # Push to registry
    echo "Pushing to registry..."
    docker push "${REGISTRY_URL}:${DEPLOYMENT_ID}"
    docker push "${REGISTRY_URL}:${ENVIRONMENT}"
fi

# Deploy infrastructure with Terraform if present
if [[ -d "infrastructure" ]] || [[ -f "main.tf" ]]; then
    echo -e "\n${BLUE}Deploying infrastructure...${NC}"
    
    # Initialize Terraform
    terraform init -backend-config="bucket=${PROJECT_ID}-terraform-state"
    
    # Plan
    terraform plan \
        -var="project_id=${PROJECT_ID}" \
        -var="region=${REGION}" \
        -var="environment=${ENVIRONMENT}" \
        -var="image_tag=${DEPLOYMENT_ID}" \
        -out=tfplan
    
    # Apply
    if [[ "${AUTO_APPROVE}" == "true" ]]; then
        terraform apply tfplan
    else
        terraform apply tfplan
    fi
fi

# Deploy application based on type
echo -e "\n${BLUE}Deploying application...${NC}"

case ${PROJECT_TYPE} in
    api|web-app)
        # Deploy to Cloud Run
        if [[ -n "${CANARY_PERCENT}" ]]; then
            # Canary deployment
            gcloud run deploy "${PROJECT_NAME}" \
                --image="${REGISTRY_URL}:${DEPLOYMENT_ID}" \
                --region="${REGION}" \
                --project="${PROJECT_ID}" \
                --tag="canary" \
                --no-traffic
            
            gcloud run services update-traffic "${PROJECT_NAME}" \
                --region="${REGION}" \
                --project="${PROJECT_ID}" \
                --to-tags="canary=${CANARY_PERCENT}"
        else
            # Full deployment
            gcloud run deploy "${PROJECT_NAME}" \
                --image="${REGISTRY_URL}:${DEPLOYMENT_ID}" \
                --region="${REGION}" \
                --project="${PROJECT_ID}" \
                --allow-unauthenticated
        fi
        
        # Get service URL
        SERVICE_URL=$(gcloud run services describe "${PROJECT_NAME}" \
            --region="${REGION}" \
            --project="${PROJECT_ID}" \
            --format="value(status.url)")
        
        echo -e "${GREEN}✅ Deployed to: ${SERVICE_URL}${NC}"
        ;;
        
    cli|library)
        echo "CLI/Library deployment not applicable"
        ;;
        
    infrastructure)
        echo "Infrastructure-only deployment completed"
        ;;
        
    *)
        echo -e "${YELLOW}Unknown project type: ${PROJECT_TYPE}${NC}"
        ;;
esac

# Post-deployment validation
echo -e "\n${BLUE}Running post-deployment checks...${NC}"

# Health check
if [[ -n "${SERVICE_URL:-}" ]]; then
    echo "Checking health endpoint..."
    for i in {1..30}; do
        if curl -f "${SERVICE_URL}/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Health check passed${NC}"
            break
        fi
        if [[ $i -eq 30 ]]; then
            echo -e "${RED}❌ Health check failed${NC}"
            if [[ "${ROLLBACK_ON_FAILURE}" == "true" ]]; then
                echo -e "${YELLOW}Rolling back...${NC}"
                gcloud run services update-traffic "${PROJECT_NAME}" \
                    --region="${REGION}" \
                    --project="${PROJECT_ID}" \
                    --to-revisions=LATEST=100
            fi
            exit 1
        fi
        sleep 2
    done
fi

# Create deployment record
DEPLOYMENT_RECORD="{
  \"id\": \"${DEPLOYMENT_ID}\",
  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
  \"environment\": \"${ENVIRONMENT}\",
  \"project_id\": \"${PROJECT_ID}\",
  \"region\": \"${REGION}\",
  \"git_sha\": \"$(git rev-parse HEAD)\",
  \"git_branch\": \"$(git rev-parse --abbrev-ref HEAD)\",
  \"deployed_by\": \"${USER}\",
  \"canary\": \"${CANARY_PERCENT:-0}\"
}"

# Save deployment record
mkdir -p .deployments
echo "${DEPLOYMENT_RECORD}" > ".deployments/${DEPLOYMENT_ID}.json"

# Send notifications
if command -v gh &> /dev/null && [[ "${ENVIRONMENT}" == "prod" ]]; then
    gh api repos/:owner/:repo/deployments \
        --method POST \
        -f ref="$(git rev-parse HEAD)" \
        -f environment="${ENVIRONMENT}" \
        -f description="Deployment ${DEPLOYMENT_ID}" \
        2>/dev/null || true
fi

# Summary
echo ""
echo "===================================="
echo -e "${GREEN}✅ Deployment Successful!${NC}"
echo "===================================="
echo "ID: ${DEPLOYMENT_ID}"
echo "Environment: ${ENVIRONMENT}"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
if [[ -n "${SERVICE_URL:-}" ]]; then
    echo "URL: ${SERVICE_URL}"
fi
echo "===================================="

# Show next steps
echo ""
echo "Next steps:"
echo "  • Monitor: make monitor"
echo "  • View logs: make logs"
echo "  • Rollback: make rollback ENV=${ENVIRONMENT}"
if [[ "${ENVIRONMENT}" != "prod" ]] && [[ -z "${CANARY_PERCENT}" ]]; then
    NEXT_ENV="test"
    [[ "${ENVIRONMENT}" == "test" ]] && NEXT_ENV="stage"
    [[ "${ENVIRONMENT}" == "stage" ]] && NEXT_ENV="prod"
    echo "  • Promote: make deploy ENV=${NEXT_ENV}"
fi