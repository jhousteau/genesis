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
    
    if command -v rg >/dev/null 2>&1; then
        if [ -n "$exclude_pattern" ]; then
            results=$(rg --line-number --no-heading --glob "$files" "$pattern" . 2>/dev/null | grep -v "$exclude_pattern" 2>/dev/null || true)
        else
            results=$(rg --line-number --no-heading --glob "$files" "$pattern" . 2>/dev/null || true)
        fi
    else
        # Use find to get the actual files matching the pattern, excluding common directories
        if [ -n "$exclude_pattern" ]; then
            results=$(find . -name "$files" -type f -not -path "*/.venv/*" -not -path "*/venv/*" -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/build/*" -not -path "*/dist/*" -exec grep -E -Hn "$pattern" {} \; 2>/dev/null | grep -v -E "$exclude_pattern" || true)
        else
            results=$(find . -name "$files" -type f -not -path "*/.venv/*" -not -path "*/venv/*" -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/build/*" -not -path "*/dist/*" -exec grep -E -Hn "$pattern" {} \; 2>/dev/null || true)
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

# Function parameter defaults with literals
check_pattern 'def [^(]*\([^)]*=\s*"[^"]+"' \
    "Python function params with string defaults" \
    "*.py" \
    "= None|= True|= False|= \[\]|= {}"

# Function parameter defaults with numbers  
check_pattern 'def [^(]*\([^)]*=\s*[0-9]+[^)]*\):' \
    "Python function params with numeric defaults" \
    "*.py" \
    "= 0|= 1|= -1"

# Variable assignments with hardcoded strings
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*["\047][^"'\'']{3,}["\047]' \
    "Python variables assigned hardcoded strings" \
    "*.py" \
    "__version__|__author__|__email__"

# Variable assignments with URLs/paths
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*["\047](https?://|/[^"'\'']+|.*\.com|.*\.org)["\047]' \
    "Python variables with URLs/paths" \
    "*.py"

# Class attributes with defaults
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*:\s*[^=]*=\s*["\047][^"'\'']+["\047]' \
    "Python class attributes with string defaults" \
    "*.py" \
    "= None|= \[\]|= {}"

# Dataclass fields with literal defaults
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*:\s*[^=]*=\s*[0-9]+' \
    "Python dataclass fields with numeric defaults" \
    "*.py" \
    "= 0|= 1|= -1"

# TYPESCRIPT PATTERNS

# Function parameter defaults with literals
check_pattern 'function\s+[^(]*\([^)]*=\s*["\047][^"'\'']*["\047][^)]*\)' \
    "TypeScript function params with string defaults" \
    "*.ts *.tsx *.js *.jsx" \
    "= \'\047\047|= \"\"|= null|= undefined"

# Function parameter defaults with numbers
check_pattern 'function\s+[^(]*\([^)]*=\s*[0-9]+[^)]*\)' \
    "TypeScript function params with numeric defaults" \
    "*.ts *.tsx *.js *.jsx" \
    "= 0|= 1|= -1"

# Arrow function defaults
check_pattern '\([^)]*=\s*["\047][^"'\'']{3,}["\047][^)]*\)\s*=>' \
    "TypeScript arrow function params with string defaults" \
    "*.ts *.tsx *.js *.jsx"

# Variable assignments with hardcoded strings
check_pattern '^[[:space:]]*(const|let|var)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*["\047][^"'\'']{3,}["\047]' \
    "TypeScript variables assigned hardcoded strings" \
    "*.ts *.tsx *.js *.jsx" \
    "= \'\047\047|= \"\""

# Object property defaults
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*:\s*["\047][^"'\'']+["\047]' \
    "TypeScript object properties with string defaults" \
    "*.ts *.tsx *.js *.jsx" \
    "= \'\047\047|= \"\"|version|name|description"

# Interface/type defaults with literals
check_pattern '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*\?\s*:\s*[^=]*=\s*["\047][^"'\'']+["\047]' \
    "TypeScript optional properties with string defaults" \
    "*.ts *.tsx *.js *.jsx"

# CROSS-LANGUAGE PATTERNS

# Common configuration values (ports, URLs, etc.)
check_pattern '["\047](localhost|127\.0\.0\.1|0\.0\.0\.0|https?://[^"'\'']+)["\047]' \
    "Hardcoded localhost/URLs in any language" \
    "*.py *.ts *.tsx *.js *.jsx"

# Common port numbers
check_pattern '["\047]?:?[0-9]{4,5}["\047]?' \
    "Hardcoded port numbers" \
    "*.py *.ts *.tsx *.js *.jsx" \
    ":22|:80|:443|:8080|:3000|:5432|:27017|:6379"

# Database connection strings
check_pattern '["\047][^"'\'']*://[^"'\'']*@[^"'\'']*["\047]' \
    "Database connection strings with credentials" \
    "*.py *.ts *.tsx *.js *.jsx"

# Hardcoded file extensions as defaults
check_pattern '=\s*["\047]\.[a-zA-Z0-9]{2,4}["\047]' \
    "Hardcoded file extensions as defaults" \
    "*.py *.ts *.tsx *.js *.jsx"

# Environment variable names hardcoded as strings
check_pattern '["\047][A-Z][A-Z0-9_]{3,}["\047]' \
    "Hardcoded environment variable names" \
    "*.py *.ts *.tsx *.js *.jsx" \
    "DEBUG|INFO|WARN|ERROR|SUCCESS|FAILED"

echo
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}🎉 No variable default issues found!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Found $ISSUES_FOUND categories of variable default issues${NC}"
    echo -e "${YELLOW}💡 Consider making these values configurable via environment variables or configuration files${NC}"
    exit 1
fi