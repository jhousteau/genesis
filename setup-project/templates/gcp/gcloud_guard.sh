#!/usr/bin/env bash
# GCloud Guard - Prevents wrong-project operations
# Ensures all gcloud commands run in the correct project context

set -euo pipefail

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# Validate environment
: "${CLOUDSDK_CONFIG:?CLOUDSDK_CONFIG not set. Run 'direnv allow' or source .envrc}"

# Get configured project
CFG_PROJECT="$(gcloud config get-value core/project 2>/dev/null || true)"
if [[ -z "${CFG_PROJECT}" ]]; then
    echo -e "${RED}❌ No core/project configured in ${CLOUDSDK_CONFIG}${NC}" >&2
    echo "Run: ./scripts/bootstrap_gcloud.sh" >&2
    exit 1
fi

# Production safety check
if [[ "${CFG_PROJECT}" =~ (^|-)prod(-|$) ]]; then
    if [[ "${CONFIRM_PROD:-}" != "I_UNDERSTAND" ]]; then
        echo -e "${RED}❌ PRODUCTION SAFETY CHECK${NC}" >&2
        echo "" >&2
        echo "You are about to run a command against PRODUCTION: ${CFG_PROJECT}" >&2
        echo "" >&2
        echo "To proceed, set: export CONFIRM_PROD=I_UNDERSTAND" >&2
        echo "" >&2
        echo "This is a safety mechanism to prevent accidental production changes." >&2
        exit 1
    fi
    echo -e "${YELLOW}⚠️  Running against PRODUCTION: ${CFG_PROJECT}${NC}" >&2
fi

# Validate service account impersonation if configured
IMPERSONATE_SA="$(gcloud config get-value auth/impersonate_service_account 2>/dev/null || true)"
if [[ -n "${IMPERSONATE_SA}" ]]; then
    echo -e "${GREEN}✓ Using service account: ${IMPERSONATE_SA}${NC}" >&2
fi

# Log the command being executed
echo -e "${GREEN}→ Project: ${CFG_PROJECT}${NC}" >&2
echo -e "${GREEN}→ Command: gcloud $*${NC}" >&2

# Execute the gcloud command
exec gcloud "$@"
