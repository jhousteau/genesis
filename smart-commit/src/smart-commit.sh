#!/usr/bin/env bash
# Genesis Smart Commit System
# Extracted and refined from old Genesis - quality gates before commits

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

echo -e "${BLUE}🎯 Genesis Smart Commit${NC}"
echo "========================"

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
    log_success "Pre-commit checks passed"
else
    log_warning "No pre-commit configuration found"
fi

# 3. Run tests
log_info "Running tests..."
if command -v pytest &> /dev/null && [[ -d tests/ ]]; then
    if pytest tests/ -v; then
        log_success "Tests passed"
    else
        log_error "Tests failed"
        read -p "Tests failed. Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
elif make test > /dev/null 2>&1; then
    log_success "Tests passed"
else
    log_warning "No test framework detected"
fi

# 4. Run linting
log_info "Running linters..."
linting_passed=true

if command -v ruff &> /dev/null; then
    if ! ruff check .; then
        linting_passed=false
    fi
fi

if command -v black &> /dev/null; then
    if ! black --check .; then
        log_info "Running black formatter..."
        black .
    fi
fi

if ! $linting_passed; then
    log_error "Linting failed. Issues should be auto-fixed. Please review."
    exit 1
fi

log_success "Code quality checks passed"

# 5. Check for secrets (basic)
log_info "Scanning for common secrets..."
if grep -r "sk-" --include="*.py" --include="*.js" --include="*.ts" . 2>/dev/null | grep -v ".git" | grep -v "test"; then
    log_error "Potential API key detected! Remove secrets before committing."
    exit 1
fi

# 6. Get commit message
echo ""
echo "Commit types:"
echo "  feat     - New feature"
echo "  fix      - Bug fix"
echo "  docs     - Documentation"
echo "  refactor - Code refactoring"
echo "  test     - Adding tests"
echo "  chore    - Maintenance"

read -p "Enter commit type: " TYPE
read -p "Enter commit description: " DESCRIPTION

# Validate commit message
COMMIT_MSG="${TYPE}: ${DESCRIPTION}"

if [[ ${#COMMIT_MSG} -lt $MIN_COMMIT_MSG_LENGTH ]]; then
    log_error "Commit message too short (minimum $MIN_COMMIT_MSG_LENGTH characters)"
    exit 1
fi

if [[ ${#COMMIT_MSG} -gt $MAX_COMMIT_MSG_LENGTH ]]; then
    log_error "Commit message too long (maximum $MAX_COMMIT_MSG_LENGTH characters)"
    exit 1
fi

# 7. Show what will be committed
echo ""
log_info "Changes to be committed:"
git status --short
echo ""
log_info "Commit message: $COMMIT_MSG"

# 8. Confirm and commit
read -p "Proceed with commit? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    log_info "Commit cancelled"
    exit 0
fi

# Create the commit
git add .
git commit -m "$COMMIT_MSG"

log_success "Commit created successfully: $COMMIT_MSG"
log_info "Use 'git push' to push to remote repository"