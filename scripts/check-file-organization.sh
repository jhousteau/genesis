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
    echo -e "${YELLOW}📋 $1${NC}"
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
    "CHANGELOG\.md"
    "Makefile"
    "LICENSE"
    "SECURITY\.md"
    "CONTRIBUTING\.md"
    "CODE_OF_CONDUCT\.md"
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
    "setup\.sh"
    "install\.sh"
    "Dockerfile"
    "docker-compose\.yml"
    "\.dockerignore"
    "main\.tf"
    "variables\.tf"
    "outputs\.tf"
    "terraform\.tfvars\.example"
    # Project-specific utility files
    "create_worktree\.py"
    ".*\.py"
)

# Define required directory structure (generic project)
REQUIRED_DIRS=(
    "scripts/"
    "docs/"
    "tests/"
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
    log_check "Checking and cleaning up documentation organization"

    local files_moved=0

    # Ensure scratch directory exists
    mkdir -p scratch/

    # Find loose .md files in project root and move to scratch/
    # Skip important root documentation files
    if command -v find >/dev/null 2>&1; then
        local loose_docs=$(find . -maxdepth 1 -name "*.md" \
            -not -name "README.md" \
            -not -name "CLAUDE.md" \
            -not -name "CHANGELOG.md" \
            -not -name "CONTRIBUTING.md" \
            -not -name "CODE_OF_CONDUCT.md" \
            -not -name "SECURITY.md" \
            -not -name "LICENSE.md" \
            2>/dev/null || true)

        if [ -n "$loose_docs" ]; then
            echo -e "${YELLOW}📦 Moving loose documentation files to scratch/${NC}"
            echo "$loose_docs" | while read -r doc; do
                if [ -f "$doc" ]; then
                    mv "$doc" "scratch/"
                    echo "  Moved: $doc → scratch/"
                    files_moved=$((files_moved + 1))
                fi
            done
        fi

        # Find files directly in docs/ root (except README.md and CLAUDE.md) and move to scratch/
        if [ -d "docs" ]; then
            local docs_root_files=$(find ./docs -maxdepth 1 -name "*.md" \
                -not -name "README.md" \
                -not -name "CLAUDE.md" \
                2>/dev/null || true)

            if [ -n "$docs_root_files" ]; then
                echo -e "${YELLOW}📦 Moving files from docs/ root to scratch/${NC}"
                echo "$docs_root_files" | while read -r doc; do
                    if [ -f "$doc" ]; then
                        filename=$(basename "$doc")
                        mv "$doc" "scratch/docs-${filename}"
                        echo "  Moved: $doc → scratch/docs-${filename}"
                        files_moved=$((files_moved + 1))
                    fi
                done
            fi
        fi
    fi

    if [ $files_moved -eq 0 ]; then
        log_success "Documentation properly organized"
    else
        echo -e "${GREEN}✅ Moved $files_moved files to scratch/ for reorganization${NC}"
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

check_directory_documentation() {
    log_check "Checking that directories have proper documentation"

    local found_issues=false
    local min_files=3  # Only check directories with 3+ files

    # Find all directories and check for documentation
    if command -v find >/dev/null 2>&1; then
        find . -type d \
            -not -path "./.git*" \
            -not -path "./node_modules*" \
            -not -path "./.venv*" \
            -not -path "./venv*" \
            -not -path "./htmlcov*" \
            -not -path "./.pytest_cache*" \
            -not -path "./dist*" \
            -not -path "./__pycache__*" \
            2>/dev/null | while read -r dir; do

            # Skip root directory
            if [ "$dir" = "." ]; then
                continue
            fi

            # Count files in directory (excluding subdirectories and hidden files)
            local file_count=$(find "$dir" -maxdepth 1 -type f -not -name ".*" 2>/dev/null | wc -l)

            if [ "$file_count" -ge "$min_files" ]; then
                # Check for README.md or CLAUDE.md
                if [ ! -f "$dir/README.md" ] && [ ! -f "$dir/CLAUDE.md" ]; then
                    if [ "$found_issues" = false ]; then
                        log_issue "Directories missing documentation (README.md or CLAUDE.md):"
                        found_issues=true
                    fi
                    echo "  $dir ($file_count files) - needs README.md or CLAUDE.md"
                fi
            fi
        done
    fi

    if [ "$found_issues" = false ]; then
        log_success "All significant directories have documentation"
    fi
    echo
}

# Run all checks
check_root_clutter
check_misplaced_scripts
check_documentation_organization
check_test_organization
check_directory_structure
check_directory_documentation

echo
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}🎉 Project organization is excellent!${NC}"
    exit 0
else
    echo -e "${YELLOW}📝 File organization check: Found $ISSUES_FOUND suggestions for improvement${NC}"
    echo -e "${BLUE}💡 These are recommendations, not errors - your code works fine!${NC}"
    echo -e "${BLUE}ℹ️  Consider moving files to conventional locations when convenient${NC}"
    # Exit 0 so this doesn't block development - these are just suggestions
    exit 0
fi
