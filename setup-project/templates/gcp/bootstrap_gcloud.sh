#!/usr/bin/env bash
# GCP Per-Repository Isolation Bootstrap
# Creates isolated gcloud configuration for this repository

set -euo pipefail

# Required environment variables
: "${PROJECT_ID:?PROJECT_ID required}"
: "${REGION:?REGION required}"

# Optional variables
DEPLOY_SA="${DEPLOY_SA:-}"
REPO_GCLOUD_HOME="${REPO_GCLOUD_HOME:-$HOME/.gcloud/${PROJECT_ID}}"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔒 Setting up GCP isolation for repository${NC}"
echo "============================================"
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Config Directory: ${REPO_GCLOUD_HOME}"
if [[ -n "${DEPLOY_SA}" ]]; then
    echo "Service Account: ${DEPLOY_SA}"
fi
echo ""

# Ensure per-repo config folder exists
mkdir -p "${REPO_GCLOUD_HOME}"
export CLOUDSDK_CONFIG="${REPO_GCLOUD_HOME}"

echo -e "${BLUE}Creating isolated gcloud configuration...${NC}"

# Create 'default' configuration if absent
if ! gcloud config configurations list --format="value(name)" 2>/dev/null | grep -qx "default"; then
    gcloud config configurations create default >/dev/null
    echo -e "${GREEN}✅ Created new configuration 'default'${NC}"
else
    echo -e "${YELLOW}ℹ️  Using existing configuration 'default'${NC}"
fi

# Set core properties
echo -e "${BLUE}Setting project and region...${NC}"
gcloud config set core/project "${PROJECT_ID}" --configuration=default
gcloud config set compute/region "${REGION}" --configuration=default

# Optional: Set default zone if provided
if [[ -n "${ZONE:-}" ]]; then
    gcloud config set compute/zone "${ZONE}" --configuration=default
fi

# Optional: Setup service account impersonation
if [[ -n "${DEPLOY_SA}" ]]; then
    echo -e "${BLUE}Configuring service account impersonation...${NC}"
    gcloud config set auth/impersonate_service_account "${DEPLOY_SA}" --configuration=default
fi

# Set non-interactive mode for automation
gcloud config set core/disable_prompts true --configuration=default

# Set format preferences
gcloud config set core/log_http false --configuration=default
gcloud config set core/user_output_enabled true --configuration=default

# Verify authentication
echo -e "${BLUE}Verifying authentication...${NC}"
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    echo -e "${GREEN}✅ Authenticated as: ${ACTIVE_ACCOUNT}${NC}"
else
    echo -e "${YELLOW}⚠️  No active authentication found${NC}"
    echo "Run: gcloud auth login"
fi

# Test project access
echo -e "${BLUE}Testing project access...${NC}"
if gcloud projects describe "${PROJECT_ID}" --format="value(projectId)" 2>/dev/null | grep -q "${PROJECT_ID}"; then
    echo -e "${GREEN}✅ Project ${PROJECT_ID} is accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Cannot access project ${PROJECT_ID}${NC}"
    echo "Ensure you have the necessary permissions"
fi

# Show final configuration
echo ""
echo -e "${BLUE}Final Configuration:${NC}"
echo "===================================="
gcloud config list --configuration=default
echo "===================================="

# Create marker file
echo "${PROJECT_ID}" > "${REPO_GCLOUD_HOME}/.project"
echo "${REGION}" > "${REPO_GCLOUD_HOME}/.region"

echo ""
echo -e "${GREEN}✅ GCP isolation setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Source .envrc: direnv allow"
echo "  2. Verify setup: gcloud config list"
echo "  3. Deploy: make deploy"
