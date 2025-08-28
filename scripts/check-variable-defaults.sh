#!/usr/bin/env bash
# Check for variable default assignments that could be hardcoded values

set -euo pipefail

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

ISSUES_FOUND=0

log_check() {
    echo -e "${BLUE}🔍 $1${NC}"
}

log_issue() {
    echo -e "${RED}❌ $1${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_pattern() {
    local pattern="$1"
    local description="$2"
    local files="$3"
    local exclude_pattern="${4:-}"

    log_check "Checking: $description"

    # Use git ls-files to respect .gitignore, then grep the results
    # Exclude documentation, test files, and templates
    if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
        # In a git repo - use git ls-files to respect .gitignore, exclude docs/tests/templates
        if [ -n "$exclude_pattern" ]; then
            results=$(git ls-files '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' | grep -v -E '(test_|_test\.|\.test\.|/tests/|/templates/|\.md$|conftest\.py)' | xargs grep -E -H "$pattern" 2>/dev/null | grep -v -E "$exclude_pattern" || true)
        else
            results=$(git ls-files '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' | grep -v -E '(test_|_test\.|\.test\.|/tests/|/templates/|\.md$|conftest\.py)' | xargs grep -E -H "$pattern" 2>/dev/null || true)
        fi
    else
        # Fallback for non-git directories
        if [ -n "$exclude_pattern" ]; then
            results=$(grep -r -E --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" "$pattern" . 2>/dev/null | grep -v -E "$exclude_pattern" || true)
        else
            results=$(grep -r -E --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" "$pattern" . 2>/dev/null || true)
        fi
    fi

    if [ -n "$results" ]; then
        log_issue "Found variable defaults:"
        echo "$results" | head -20
        echo
    else
        log_success "No issues found"
    fi
    echo
}

echo "🔍 Checking for variable default assignments..."
echo

# PYTHON PATTERNS

# Function parameter defaults with string literals
check_pattern 'def [^(]*\([^)]*=[ \t]*"[^"]+"' \
    "Python function params with string defaults" \
    "*.py" \
    "= None|= True|= False|= \[\]|= {}"

# Function parameter defaults with numbers
check_pattern 'def [^(]*\([^)]*=[ \t]*[0-9]+[^)]*\):' \
    "Python function params with numeric defaults" \
    "*.py" \
    "= 0|= 1|= -1"

# Function parameters with URLs (always dangerous)
check_pattern 'def [^(]*\([^)]*=[ \t]*["\047](https?://|ftp://)[^"'\'']+["\047]' \
    "Python function params with URL defaults" \
    "*.py"

# Variable assignments with hardcoded strings (only flag truly dangerous URLs and connection strings)
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*[ \t]*=[ \t]*["\047](https?://[^"'\'']+|postgresql://[^"'\'']+|mongodb://[^"'\'']+|redis://[^"'\'']+)["\047]' \
    "Python variables with dangerous URLs/connection strings" \
    "*.py"

# Class attributes with dangerous defaults (only connection strings and secrets)
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*:[ \t]*[^=]*=[ \t]*["\047](https?://[^"'\'']+|postgresql://[^"'\'']+|sk-[^"'\'']+|ghp_[^"'\'']+)["\047]' \
    "Python class attributes with dangerous defaults" \
    "*.py"

# Dataclass fields with literal defaults
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*:[ \t]*[^=]*=[ \t]*[0-9]+' \
    "Python dataclass fields with numeric defaults" \
    "*.py" \
    "= 0|= 1|= -1"

# TYPESCRIPT PATTERNS

# Function parameter defaults with literals
check_pattern 'function[ \t]+[^(]*\([^)]*=[ \t]*["\047][^"'\'']*["\047][^)]*\)' \
    "TypeScript function params with string defaults" \
    "*.ts *.tsx *.js *.jsx" \
    "= \'\047\047|= \"\"|= null|= undefined"

# Function parameter defaults with numbers
check_pattern 'function[ \t]+[^(]*\([^)]*=[ \t]*[0-9]+[^)]*\)' \
    "TypeScript function params with numeric defaults" \
    "*.ts *.tsx *.js *.jsx" \
    "= 0|= 1|= -1"

# Arrow function defaults
check_pattern '\([^)]*=[ \t]*["\047][^"'\'']{3,}["\047][^)]*\)[ \t]*=>' \
    "TypeScript arrow function params with string defaults" \
    "*.ts *.tsx *.js *.jsx"

# Variable assignments with hardcoded strings
check_pattern '^[[:space:]]*(const|let|var)[ \t]+[a-zA-Z_][a-zA-Z0-9_]*[ \t]*=[ \t]*["\047][^"'\'']{3,}["\047]' \
    "TypeScript variables assigned hardcoded strings" \
    "*.ts *.tsx *.js *.jsx" \
    "= \'\047\047|= \"\""

# Object property defaults
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*:[ \t]*["\047][^"'\'']+["\047]' \
    "TypeScript object properties with string defaults" \
    "*.ts *.tsx *.js *.jsx" \
    "= \'\047\047|= \"\"|version|name|description"

# Interface/type defaults with literals
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*\?[ \t]*:[ \t]*[^=]*=[ \t]*["\047][^"'\'']+["\047]' \
    "TypeScript optional properties with string defaults" \
    "*.ts *.tsx *.js *.jsx"

# CROSS-LANGUAGE PATTERNS

# Common configuration values (ports, URLs, etc.)
check_pattern '["\047](localhost|127\.0\.0\.1|0\.0\.0\.0|https?://[^"'\'']+)["\047]' \
    "Hardcoded localhost/URLs in any language" \
    "*.py *.ts *.tsx *.js *.jsx"

# Common port numbers (only in port-like contexts)
check_pattern '(port|PORT)[^=]*=[ \t]*[0-9]{4,5}|:[0-9]{4,5}[^0-9]|localhost:[0-9]{4,5}' \
    "Hardcoded port numbers" \
    "*.py *.ts *.tsx *.js *.jsx" \
    ":22|:80|:443"

# Database connection strings
check_pattern '["\047][^"'\'']*://[^"'\'']*@[^"'\'']*["\047]' \
    "Database connection strings with credentials" \
    "*.py *.ts *.tsx *.js *.jsx"

# Hardcoded file extensions as defaults
check_pattern '=[ \t]*["\047]\.[a-zA-Z0-9]{2,4}["\047]' \
    "Hardcoded file extensions as defaults" \
    "*.py *.ts *.tsx *.js *.jsx"

# Environment variable fallback patterns (dangerous)
check_pattern 'os\.environ\.get\([^,)]*,\s*["\047][^"'\'']+["\047]\)|process\.env\[[^]]*\]\s*\|\|\s*["\047][^"'\'']+["\047]' \
    "Environment variable fallbacks with hardcoded defaults" \
    "*.py *.ts *.tsx *.js *.jsx"

echo
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}🎉 No variable default issues found!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Found $ISSUES_FOUND categories of variable default issues${NC}"
    echo -e "${YELLOW}💡 Consider making these values configurable via environment variables or configuration files${NC}"
    exit 1
fi
