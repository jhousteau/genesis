#!/usr/bin/env bash
# Universal Project Compliance Validator
# Ensures all projects follow organizational standards

set -euo pipefail

# Variables
ERRORS=0
WARNINGS=0
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_error() { 
    echo -e "${RED}❌ ERROR: $1${NC}" >&2
    ((ERRORS++))
}

log_warning() { 
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
    ((WARNINGS++))
}

log_success() { 
    echo -e "${GREEN}✅ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo "🔍 Running Compliance Check for: ${PROJECT_ROOT}"
echo "================================================"

# 1. Check Required Files
echo -e "\n📁 Checking required files..."
REQUIRED_FILES=(
    "README.md"
    "CHANGELOG.md"
    "CONTRIBUTING.md"
    "SECURITY.md"
    ".gitignore"
    ".editorconfig"
    ".envrc"
    "Makefile"
    ".project-config.yaml"
    "docs/ARCHITECTURE.md"
    "docs/DEPLOYMENT.md"
    "docs/DEVELOPMENT.md"
    "scripts/deploy.sh"
    "scripts/smart-commit.sh"
    "scripts/validate-compliance.sh"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "${PROJECT_ROOT}/${file}" ]]; then
        log_error "Missing required file: ${file}"
    else
        log_success "Found: ${file}"
    fi
done

# 2. Check README.md Structure
echo -e "\n📖 Validating README.md structure..."
if [[ -f "${PROJECT_ROOT}/README.md" ]]; then
    REQUIRED_SECTIONS=(
        "## Overview"
        "## Quick Start"
        "## Prerequisites"
        "## Installation"
        "## Usage"
        "## Development"
        "## Testing"
        "## Deployment"
        "## Configuration"
        "## Troubleshooting"
        "## Contributing"
    )
    
    for section in "${REQUIRED_SECTIONS[@]}"; do
        if ! grep -q "^${section}" "${PROJECT_ROOT}/README.md"; then
            log_error "README.md missing required section: ${section}"
        fi
    done
    
    # Check README length
    LINE_COUNT=$(wc -l < "${PROJECT_ROOT}/README.md")
    if [[ ${LINE_COUNT} -lt 50 ]]; then
        log_warning "README.md seems too short (${LINE_COUNT} lines). Consider adding more detail."
    fi
else
    log_error "README.md not found"
fi

# 3. Check for Garbage Files
echo -e "\n🗑️  Checking for garbage files..."
FORBIDDEN_PATTERNS=(
    "*.pyc"
    "__pycache__"
    ".DS_Store"
    "Thumbs.db"
    "*.swp"
    "*.swo"
    "*~"
    "*.bak"
    "*.old"
    "*.orig"
    ".env"
    "*.log"
    "debug.log"
    "error.log"
)

for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    FOUND_FILES=$(find "${PROJECT_ROOT}" \
        -path "${PROJECT_ROOT}/.git" -prune -o \
        -path "${PROJECT_ROOT}/node_modules" -prune -o \
        -path "${PROJECT_ROOT}/venv" -prune -o \
        -path "${PROJECT_ROOT}/.venv" -prune -o \
        -path "${PROJECT_ROOT}/temp" -prune -o \
        -name "${pattern}" -type f -print 2>/dev/null || true)
    
    if [[ -n "${FOUND_FILES}" ]]; then
        log_error "Found forbidden files matching pattern '${pattern}':"
        echo "${FOUND_FILES}" | while read -r file; do
            echo "    - ${file}"
        done
    fi
done

# 4. Check Temp Directory Usage
echo -e "\n📂 Validating temp directory usage..."
TEMP_FILES_OUTSIDE=$(find "${PROJECT_ROOT}" \
    -path "${PROJECT_ROOT}/.git" -prune -o \
    -path "${PROJECT_ROOT}/temp" -prune -o \
    -path "${PROJECT_ROOT}/node_modules" -prune -o \
    \( -name "*.tmp" -o -name "*.temp" -o -name "temp_*" \) -type f -print 2>/dev/null || true)

if [[ -n "${TEMP_FILES_OUTSIDE}" ]]; then
    log_warning "Found temporary files outside of temp/ directory:"
    echo "${TEMP_FILES_OUTSIDE}" | while read -r file; do
        echo "    - ${file}"
    done
fi

# Ensure temp directory exists and is in .gitignore
if [[ ! -d "${PROJECT_ROOT}/temp" ]]; then
    log_warning "temp/ directory does not exist"
fi

if [[ -f "${PROJECT_ROOT}/.gitignore" ]]; then
    if ! grep -q "^temp/" "${PROJECT_ROOT}/.gitignore"; then
        log_error ".gitignore does not exclude temp/ directory"
    fi
fi

# 5. Check for Hardcoded Secrets
echo -e "\n🔐 Scanning for potential hardcoded secrets..."
SECRET_PATTERNS=(
    "api[_-]?key.*=.*['\"][\w]+"
    "secret.*=.*['\"][\w]+"
    "password.*=.*['\"][\w]+"
    "token.*=.*['\"][\w]+"
    "bearer.*['\"][\w]+"
    "AWS[_]?ACCESS[_]?KEY"
    "AWS[_]?SECRET"
    "GITHUB[_]?TOKEN"
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    FOUND=$(grep -r -i -E "${pattern}" "${PROJECT_ROOT}" \
        --exclude-dir=.git \
        --exclude-dir=node_modules \
        --exclude-dir=venv \
        --exclude-dir=.venv \
        --exclude-dir=temp \
        --exclude="*.md" \
        --exclude="*.example" \
        --exclude="*.template" \
        2>/dev/null | grep -v "example\|template\|mock\|test\|fake" || true)
    
    if [[ -n "${FOUND}" ]]; then
        log_error "Potential hardcoded secret found (pattern: ${pattern})"
        echo "${FOUND}" | head -5
    fi
done

# 6. Check Documentation Freshness
echo -e "\n📅 Checking documentation freshness..."
OLD_DOCS=0
for doc in "${PROJECT_ROOT}"/docs/*.md; do
    if [[ -f "${doc}" ]]; then
        # Get file age in days
        if [[ "$OSTYPE" == "darwin"* ]]; then
            AGE=$(( ($(date +%s) - $(stat -f %m "${doc}")) / 86400 ))
        else
            AGE=$(( ($(date +%s) - $(stat -c %Y "${doc}")) / 86400 ))
        fi
        
        if [[ ${AGE} -gt 90 ]]; then
            log_warning "Documentation older than 90 days: $(basename ${doc}) (${AGE} days old)"
            ((OLD_DOCS++))
        fi
    fi
done

# 7. Check TODO/FIXME Comments
echo -e "\n📝 Checking for TODO/FIXME comments..."
TODO_COUNT=$(grep -r "TODO\|FIXME\|HACK\|XXX" "${PROJECT_ROOT}" \
    --exclude-dir=.git \
    --exclude-dir=node_modules \
    --exclude-dir=venv \
    --exclude="validate-compliance.sh" \
    2>/dev/null | wc -l || echo "0")

if [[ ${TODO_COUNT} -gt 10 ]]; then
    log_warning "Found ${TODO_COUNT} TODO/FIXME/HACK comments (recommended max: 10)"
elif [[ ${TODO_COUNT} -gt 0 ]]; then
    log_info "Found ${TODO_COUNT} TODO/FIXME/HACK comments"
fi

# 8. Validate .gitignore
echo -e "\n📋 Validating .gitignore..."
if [[ -f "${PROJECT_ROOT}/.gitignore" ]]; then
    REQUIRED_GITIGNORE=(
        "temp/"
        "*.tmp"
        "*.temp"
        ".env"
        "*.log"
        ".DS_Store"
        "__pycache__"
        "*.pyc"
        "node_modules/"
        ".terraform/"
        "*.tfstate"
        "*.tfstate.backup"
        ".venv/"
        "venv/"
        "dist/"
        "build/"
        "*.egg-info"
    )
    
    for pattern in "${REQUIRED_GITIGNORE[@]}"; do
        if ! grep -q "${pattern}" "${PROJECT_ROOT}/.gitignore"; then
            log_warning ".gitignore missing recommended pattern: ${pattern}"
        fi
    done
else
    log_error ".gitignore file not found"
fi

# 9. Check File Permissions
echo -e "\n🔒 Checking file permissions..."
EXECUTABLE_FILES=$(find "${PROJECT_ROOT}" \
    -path "${PROJECT_ROOT}/.git" -prune -o \
    -path "${PROJECT_ROOT}/node_modules" -prune -o \
    -path "${PROJECT_ROOT}/venv" -prune -o \
    -path "${PROJECT_ROOT}/scripts" -prune -o \
    -type f -perm +111 -print 2>/dev/null || true)

if [[ -n "${EXECUTABLE_FILES}" ]]; then
    log_warning "Found executable files outside scripts/ directory:"
    echo "${EXECUTABLE_FILES}" | while read -r file; do
        echo "    - ${file}"
    done
fi

# 10. Check for Large Files
echo -e "\n📦 Checking for large files..."
LARGE_FILES=$(find "${PROJECT_ROOT}" \
    -path "${PROJECT_ROOT}/.git" -prune -o \
    -path "${PROJECT_ROOT}/node_modules" -prune -o \
    -path "${PROJECT_ROOT}/temp" -prune -o \
    -type f -size +10M -print 2>/dev/null || true)

if [[ -n "${LARGE_FILES}" ]]; then
    log_warning "Found files larger than 10MB:"
    echo "${LARGE_FILES}" | while read -r file; do
        SIZE=$(du -h "${file}" | cut -f1)
        echo "    - ${file} (${SIZE})"
    done
fi

# 11. Check Project Structure
echo -e "\n🏗️  Validating project structure..."
EXPECTED_DIRS=(
    "src"
    "tests"
    "docs"
    "scripts"
    "temp"
)

for dir in "${EXPECTED_DIRS[@]}"; do
    if [[ ! -d "${PROJECT_ROOT}/${dir}" ]]; then
        log_warning "Missing expected directory: ${dir}/"
    fi
done

# 12. Check Branch Protection
echo -e "\n🌿 Checking Git configuration..."
if [[ -d "${PROJECT_ROOT}/.git" ]]; then
    # Check if main/master branch exists
    DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
    
    # Check for direct commits to main
    if git log --oneline -1 --format="%H" origin/${DEFAULT_BRANCH} 2>/dev/null | head -1 > /dev/null; then
        log_info "Git repository detected with default branch: ${DEFAULT_BRANCH}"
    fi
else
    log_warning "Not a Git repository"
fi

# 13. Check Pre-commit Hooks
echo -e "\n🪝 Checking pre-commit hooks..."
if [[ -f "${PROJECT_ROOT}/.pre-commit-config.yaml" ]]; then
    log_success "Pre-commit configuration found"
    
    if [[ -d "${PROJECT_ROOT}/.git/hooks" ]] && [[ -f "${PROJECT_ROOT}/.git/hooks/pre-commit" ]]; then
        log_success "Pre-commit hooks installed"
    else
        log_warning "Pre-commit hooks not installed. Run: pre-commit install"
    fi
else
    log_error "Pre-commit configuration not found (.pre-commit-config.yaml)"
fi

# 14. Check for Duplicate Code
echo -e "\n🔄 Checking for obvious code duplication..."
# This is a simple check - for real duplication detection use tools like jscpd
DUPLICATE_FUNCTIONS=$(grep -r "^function\|^def\|^func" "${PROJECT_ROOT}" \
    --include="*.py" --include="*.js" --include="*.go" \
    --exclude-dir=.git \
    --exclude-dir=node_modules \
    --exclude-dir=venv \
    2>/dev/null | \
    awk -F: '{print $2}' | \
    sort | uniq -c | \
    awk '$1 > 1 {print $2}' || true)

if [[ -n "${DUPLICATE_FUNCTIONS}" ]]; then
    log_warning "Potential duplicate function names found. Consider refactoring."
fi

# 15. Check Container Security (if Dockerfile exists)
if [[ -f "${PROJECT_ROOT}/Dockerfile" ]]; then
    echo -e "\n🐳 Checking Dockerfile..."
    
    # Check for running as root
    if ! grep -q "USER" "${PROJECT_ROOT}/Dockerfile"; then
        log_warning "Dockerfile does not specify a USER (running as root)"
    fi
    
    # Check for latest tags
    if grep -q ":latest" "${PROJECT_ROOT}/Dockerfile"; then
        log_warning "Dockerfile uses :latest tag (not recommended for production)"
    fi
fi

# Summary
echo ""
echo "========================================="
echo "📊 Compliance Check Summary"
echo "========================================="
echo -e "Errors:   ${RED}${ERRORS}${NC}"
echo -e "Warnings: ${YELLOW}${WARNINGS}${NC}"
echo "========================================="

if [[ ${ERRORS} -gt 0 ]]; then
    echo -e "${RED}❌ FAILED: ${ERRORS} error(s) must be fixed${NC}"
    echo ""
    echo "Run 'make clean' to remove garbage files"
    echo "Run 'setup-project upgrade' to add missing components"
    exit 1
elif [[ ${WARNINGS} -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  PASSED with ${WARNINGS} warning(s)${NC}"
    echo ""
    echo "Consider addressing warnings for better compliance"
    exit 0
else
    echo -e "${GREEN}✅ PASSED: Full compliance achieved!${NC}"
    exit 0
fi