#!/usr/bin/env bash
# Check for proper file organization and detect clutter

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

echo "🗂️  Checking file organization and detecting clutter..."
echo

# Define allowed root files (case-insensitive patterns)
ALLOWED_ROOT_FILES=(
    "README\.md"
    "CLAUDE\.md"
    "Makefile"
    "LICENSE"
    "SECURITY\.md"
    "\.gitignore"
    "\.envrc"
    "\.env\.example"
    "pyproject\.toml"
    "poetry\.lock"
    "package\.json"
    "package-lock\.json"
    "tsconfig\.json"
    "jest\.config\.js"
    "pytest\.ini"
    "requirements\.txt"
    "requirements-dev\.txt"
    "Dockerfile"
    "docker-compose\.yml"
    "\.dockerignore"
    "main\.tf"
    "variables\.tf"
    "outputs\.tf"
    "terraform\.tfvars\.example"
)

# Define required directory structure for Genesis (component-based)
REQUIRED_DIRS=(
    "scripts/"
    "docs/"
    "tests/"
    "genesis/"
)

check_root_clutter() {
    log_check "Checking for files cluttering project root"
    
    local found_issues=false
    
    # Check all files in root (not directories)
    for file in *; do
        if [ -f "$file" ]; then
            local allowed=false
            
            # Check against allowed patterns
            for pattern in "${ALLOWED_ROOT_FILES[@]}"; do
                if [[ "$file" =~ ^${pattern}$ ]]; then
                    allowed=true
                    break
                fi
            done
            
            if [ "$allowed" = false ]; then
                if [ "$found_issues" = false ]; then
                    log_issue "Files in wrong location - should be moved:"
                    found_issues=true
                fi
                echo "  $file"
                
                # Suggest where it should go
                case "$file" in
                    *.md)
                        if [[ ! "$file" =~ ^(README|CLAUDE|SECURITY|LICENSE)\.md$ ]]; then
                            echo "    → Should be in docs/"
                        fi
                        ;;
                    *.sh)
                        echo "    → Should be in scripts/"
                        ;;
                    *.py)
                        if [[ "$file" =~ ^test_ ]] || [[ "$file" == *test.py ]] || [[ "$file" == conftest.py ]]; then
                            echo "    → Should be in tests/"
                        else
                            echo "    → Should be in src/"
                        fi
                        ;;
                    *.js|*.ts)
                        if [[ "$file" =~ \.test\. ]] || [[ "$file" =~ \.spec\. ]]; then
                            echo "    → Should be in tests/"
                        else
                            echo "    → Should be in src/"
                        fi
                        ;;
                    *.json)
                        if [[ ! "$file" =~ ^(package|package-lock|tsconfig|jest\.config)\.json$ ]]; then
                            echo "    → Should be in docs/ or config/"
                        fi
                        ;;
                    *.yml|*.yaml)
                        if [[ ! "$file" =~ ^(docker-compose)\.ya?ml$ ]]; then
                            echo "    → Should be in .github/workflows/ or config/"
                        fi
                        ;;
                    .*)
                        if [[ ! "$file" =~ ^\.(gitignore|envrc|env\.example|dockerignore)$ ]]; then
                            echo "    → Config file - consider consolidating"
                        fi
                        ;;
                esac
            fi
        fi
    done
    
    if [ "$found_issues" = false ]; then
        log_success "Project root is clean"
    fi
    echo
}

check_misplaced_scripts() {
    log_check "Checking for scripts outside scripts/ directory"
    
    local found_issues=false
    
    # Find .sh files outside of scripts/ directory or component src/ directories
    if command -v find >/dev/null 2>&1; then
        local misplaced_scripts=$(find . -name "*.sh" \
            -not -path "./scripts/*" \
            -not -path "./*/src/*" \
            -not -path "./*/tests/*" \
            -not -path "./.git/*" \
            -not -path "./node_modules/*" \
            -not -path "./.venv/*" \
            -not -path "./venv/*" \
            2>/dev/null || true)
        
        if [ -n "$misplaced_scripts" ]; then
            log_issue "Shell scripts in wrong location:"
            echo "$misplaced_scripts" | while read -r script; do
                echo "  $script → Should be in scripts/"
            done
            found_issues=true
        fi
    fi
    
    if [ "$found_issues" = false ]; then
        log_success "All shell scripts properly located"
    fi
    echo
}

check_documentation_organization() {
    log_check "Checking documentation organization"
    
    local found_issues=false
    
    # Find .md files in wrong places
    if command -v find >/dev/null 2>&1; then
        local misplaced_docs=$(find . -name "*.md" \
            -not -path "./docs/*" \
            -not -path "./README.md" \
            -not -path "./CLAUDE.md" \
            -not -path "./SECURITY.md" \
            -not -path "./LICENSE.md" \
            -not -path "./**/README.md" \
            -not -path "./.git/*" \
            -not -path "./node_modules/*" \
            -not -path "./.venv/*" \
            -not -path "./venv/*" \
            2>/dev/null || true)
        
        if [ -n "$misplaced_docs" ]; then
            log_issue "Documentation files in wrong location:"
            echo "$misplaced_docs" | while read -r doc; do
                if [[ ! "$doc" =~ /README\.md$ ]]; then  # Allow README.md in subdirectories
                    echo "  $doc → Should be in docs/"
                    found_issues=true
                fi
            done
        fi
    fi
    
    if [ "$found_issues" = false ]; then
        log_success "Documentation properly organized"
    fi
    echo
}

check_test_organization() {
    log_check "Checking test file organization"
    
    local found_issues=false
    
    # Find test files outside of tests/ directories
    if command -v find >/dev/null 2>&1; then
        local misplaced_tests=$(find . \( -name "*test*.py" -o -name "*test*.js" -o -name "*test*.ts" -o -name "conftest.py" \) \
            -not -path "./tests/*" \
            -not -path "./**/tests/*" \
            -not -path "./.git/*" \
            -not -path "./node_modules/*" \
            -not -path "./.venv/*" \
            -not -path "./venv/*" \
            2>/dev/null || true)
        
        if [ -n "$misplaced_tests" ]; then
            log_issue "Test files in wrong location:"
            echo "$misplaced_tests" | while read -r test; do
                echo "  $test → Should be in tests/"
            done
            found_issues=true
        fi
    fi
    
    if [ "$found_issues" = false ]; then
        log_success "Test files properly organized"
    fi
    echo
}

check_directory_structure() {
    log_check "Checking for required directory structure"
    
    local missing_dirs=()
    
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            missing_dirs+=("$dir")
        fi
    done
    
    if [ ${#missing_dirs[@]} -gt 0 ]; then
        log_issue "Missing required directories:"
        for dir in "${missing_dirs[@]}"; do
            echo "  $dir"
        done
    else
        log_success "All required directories present"
    fi
    echo
}

# Run all checks
check_root_clutter
check_misplaced_scripts  
check_documentation_organization
check_test_organization
check_directory_structure

echo
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}🎉 Project organization is excellent!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Found $ISSUES_FOUND file organization issues${NC}"
    echo -e "${YELLOW}💡 Move files to their proper locations for better project organization${NC}"
    exit 1
fi