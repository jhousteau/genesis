#!/usr/bin/env bash
# Smart Commit System
# Enforces quality gates and standards before allowing commits

set -euo pipefail

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
MAX_COMMIT_MSG_LENGTH=72
MIN_COMMIT_MSG_LENGTH=10

log_error() { echo -e "${RED}❌ $1${NC}" >&2; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

echo -e "${BLUE}🎯 Smart Commit System${NC}"
echo "================================"

# 1. Check for uncommitted changes
if [[ -z $(git status --porcelain) ]]; then
    log_error "No changes to commit"
    exit 1
fi

# 2. Run pre-commit hooks
log_info "Running pre-commit checks..."
if [[ -f .pre-commit-config.yaml ]]; then
    if ! pre-commit run --all-files; then
        log_error "Pre-commit checks failed. Fix issues and try again."
        exit 1
    fi
else
    log_warning "No pre-commit configuration found"
fi

# 3. Run tests
log_info "Running tests..."
if make test > /dev/null 2>&1; then
    log_success "Tests passed"
else
    log_warning "Tests failed or not configured"
    read -p "Tests failed. Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 4. Run linting
log_info "Running linters..."
if make lint > /dev/null 2>&1; then
    log_success "Linting passed"
else
    log_error "Linting failed. Fix issues and try again."
    exit 1
fi

# 5. Check for secrets
log_info "Scanning for secrets..."
if command -v detect-secrets &> /dev/null; then
    if detect-secrets scan --baseline .secrets.baseline 2>/dev/null | grep -q "secret"; then
        log_error "Potential secrets detected! Review and remove them."
        exit 1
    fi
fi

# 6. Get commit type
echo ""
echo "Select commit type:"
echo "  1) feat     - New feature"
echo "  2) fix      - Bug fix"
echo "  3) docs     - Documentation only"
echo "  4) style    - Code style changes"
echo "  5) refactor - Code refactoring"
echo "  6) perf     - Performance improvement"
echo "  7) test     - Adding tests"
echo "  8) chore    - Maintenance tasks"
echo "  9) build    - Build system changes"
echo "  10) ci      - CI/CD changes"

read -p "Enter choice (1-10): " TYPE_CHOICE

case $TYPE_CHOICE in
    1) TYPE="feat" ;;
    2) TYPE="fix" ;;
    3) TYPE="docs" ;;
    4) TYPE="style" ;;
    5) TYPE="refactor" ;;
    6) TYPE="perf" ;;
    7) TYPE="test" ;;
    8) TYPE="chore" ;;
    9) TYPE="build" ;;
    10) TYPE="ci" ;;
    *) log_error "Invalid choice"; exit 1 ;;
esac

# 7. Get scope (optional)
read -p "Enter scope (optional, e.g., api, frontend, auth): " SCOPE
if [[ -n "${SCOPE}" ]]; then
    SCOPE="(${SCOPE})"
fi

# 8. Check for breaking changes
read -p "Is this a breaking change? (y/N): " -n 1 -r
echo
BREAKING=""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    BREAKING="!"
fi

# 9. Get commit message
echo ""
read -p "Enter commit message (imperative mood, e.g., 'add user authentication'): " MESSAGE

# Validate message length
if [[ ${#MESSAGE} -lt ${MIN_COMMIT_MSG_LENGTH} ]]; then
    log_error "Commit message too short (minimum ${MIN_COMMIT_MSG_LENGTH} characters)"
    exit 1
fi

if [[ ${#MESSAGE} -gt ${MAX_COMMIT_MSG_LENGTH} ]]; then
    log_error "Commit message too long (maximum ${MAX_COMMIT_MSG_LENGTH} characters)"
    exit 1
fi

# 10. Get detailed description (optional)
echo ""
echo "Enter detailed description (optional, press Ctrl+D when done):"
BODY=$(cat)

# 11. Check for related issues
read -p "Related issue number (optional, e.g., 123): " ISSUE
if [[ -n "${ISSUE}" ]]; then
    FOOTER="Closes #${ISSUE}"
else
    FOOTER=""
fi

# 12. Build final commit message
COMMIT_MSG="${TYPE}${SCOPE}${BREAKING}: ${MESSAGE}"

if [[ -n "${BODY}" ]]; then
    COMMIT_MSG="${COMMIT_MSG}

${BODY}"
fi

if [[ -n "${FOOTER}" ]]; then
    COMMIT_MSG="${COMMIT_MSG}

${FOOTER}"
fi

# 13. Show preview
echo ""
echo "================================"
echo "Commit Preview:"
echo "================================"
echo "${COMMIT_MSG}"
echo "================================"
echo ""
echo "Files to be committed:"
git status --short
echo ""

# 14. Confirm commit
read -p "Proceed with commit? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    log_info "Commit cancelled"
    exit 0
fi

# 15. Stage all changes
log_info "Staging changes..."
git add -A

# 16. Create commit
log_info "Creating commit..."
git commit -m "${COMMIT_MSG}"

# 17. Run post-commit validation
log_info "Running post-commit validation..."
if [[ -f scripts/validate-compliance.sh ]]; then
    if ! ./scripts/validate-compliance.sh > /dev/null 2>&1; then
        log_warning "Post-commit validation found issues"
    fi
fi

# 18. Success
log_success "Commit created successfully!"
echo ""
echo "Next steps:"
echo "  • Review commit: git show"
echo "  • Push changes: git push"
echo "  • Create PR: make pr"

# 19. Check if push is needed
if [[ $(git rev-list --count HEAD@{upstream}..HEAD 2>/dev/null || echo "0") -gt 0 ]]; then
    echo ""
    read -p "Push changes now? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        git push
        log_success "Changes pushed!"
        
        # Offer to create PR
        if command -v gh &> /dev/null; then
            echo ""
            read -p "Create pull request? (Y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                gh pr create --fill
            fi
        fi
    fi
fi