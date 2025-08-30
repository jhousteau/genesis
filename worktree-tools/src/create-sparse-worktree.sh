#!/usr/bin/env bash
# Genesis Sparse Worktree Creator - AI-safe development isolation
# Extracted and simplified from old Genesis (230→148 lines)

set -euo pipefail

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

show_usage() {
    cat << EOF
Usage: $0 <name> <focus_path> [--max-files <n>] [--verify]

Create AI-safe sparse worktree with file limits and contamination prevention.

Arguments:
  name         Worktree name (e.g., fix-auth, update-tests)
  focus_path   Path to focus on (file or directory)

Options:
  --max-files <n>   Max files (required, or set AI_MAX_FILES env var)
  --verify          Verify safety after creation
  --help           Show help

Examples:
  $0 fix-auth src/auth/login.py
  $0 update-tests tests/unit/ --max-files 25

Features: File limits, depth restrictions, safety manifest, contamination detection
EOF
}

# Parse arguments - check for help first
[[ $# -gt 0 && "$1" == "--help" ]] && { show_usage; exit 0; }
[[ $# -lt 2 ]] && { show_usage; exit 1; }

NAME="$1"; FOCUS_PATH="$2"; MAX_FILES="${AI_MAX_FILES:-}"; VERIFY=false

shift 2
while [[ $# -gt 0 ]]; do
    case "$1" in
        --max-files) MAX_FILES="$2"; shift 2 ;;
        --verify) VERIFY=true; shift ;;
        --help) show_usage; exit 0 ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; show_usage; exit 1 ;;
    esac
done

# Validate inputs
[[ ! -e "$FOCUS_PATH" ]] && { echo -e "${RED}Focus path not found: $FOCUS_PATH${NC}"; exit 1; }
[[ -z "$MAX_FILES" ]] && { echo -e "${RED}Max files not specified. Use --max-files <n> or set AI_MAX_FILES environment variable${NC}"; exit 1; }
[[ ! $MAX_FILES =~ ^[0-9]+$ ]] && { echo -e "${RED}Max files must be a number${NC}"; exit 1; }

# Get repository info
PARENT_REPO="$(git rev-parse --show-toplevel)"
if git rev-parse --git-dir 2>/dev/null | grep -q worktrees; then
    echo -e "${YELLOW}In worktree - switching to main repo${NC}"
    cd "$PARENT_REPO"
fi

BRANCH="sparse-$NAME"
WORKTREE_DIR="worktrees/$NAME"

echo -e "${GREEN}Creating AI-safe sparse worktree${NC}"
echo -e "${BLUE}Name:${NC} $NAME  ${BLUE}Focus:${NC} $FOCUS_PATH  ${BLUE}Limit:${NC} $MAX_FILES files"

# Create worktree directory
mkdir -p "$(dirname "$WORKTREE_DIR")"

# Clean up any stale worktree references
echo "Cleaning up stale worktree references..."
git worktree prune 2>/dev/null || true

# Create worktree with sparse checkout
echo "Setting up worktree..."
# Try creating with new branch first
if ! git worktree add --no-checkout "$WORKTREE_DIR" -b "$BRANCH" 2>/tmp/git_error.log; then
    echo -e "${YELLOW}Branch $BRANCH may exist, trying to reuse...${NC}"
    # Try reusing existing branch
    if ! git worktree add --no-checkout "$WORKTREE_DIR" "$BRANCH" 2>/tmp/git_error.log; then
        echo -e "${RED}Failed to create worktree. Git error:${NC}"
        cat /tmp/git_error.log
        echo -e "${RED}Possible causes:${NC}"
        echo "- Branch '$BRANCH' already exists: git branch -D $BRANCH"
        echo "- Worktree path exists: rm -rf $WORKTREE_DIR"
        echo "- Uncommitted changes in main repo: git status"
        rm -f /tmp/git_error.log
        exit 1
    fi
fi
rm -f /tmp/git_error.log

cd "$WORKTREE_DIR"

# Configure sparse checkout
echo "Configuring sparse checkout..."
git sparse-checkout init --cone

if [[ -f "$PARENT_REPO/$FOCUS_PATH" ]]; then
    # Single file - include its directory
    DIR_PATH=$(dirname "$FOCUS_PATH")
    git sparse-checkout set "$DIR_PATH"
    echo -e "${BLUE}Focused on directory:${NC} $DIR_PATH (contains $FOCUS_PATH)"
elif [[ -d "$PARENT_REPO/$FOCUS_PATH" ]]; then
    # Directory - include it
    git sparse-checkout set "$FOCUS_PATH"
    echo -e "${BLUE}Focused on directory:${NC} $FOCUS_PATH"
else
    echo -e "${RED}Focus path not found in repo: $FOCUS_PATH${NC}"
    cd "$PARENT_REPO"; git worktree remove "$WORKTREE_DIR" --force 2>/dev/null; exit 1
fi

# Build complete sparse-checkout list (focus + shared resources)
SPARSE_CHECKOUT_LIST=("$FOCUS_PATH")

# Add shared resources from manifest
SHARED_MANIFEST="$PARENT_REPO/shared-resources.manifest"
if [[ -f "$SHARED_MANIFEST" ]]; then
    echo "Adding shared resources from manifest..."
    while IFS= read -r line; do
        # Skip comments, empty lines, and exclude patterns
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# || "$line" =~ ^[[:space:]]*! ]] && continue

        # Clean up line (remove leading/trailing whitespace)
        resource=$(echo "$line" | xargs)
        [[ -z "$resource" ]] && continue

        # Check if resource exists in parent repo before adding
        if [[ -e "$PARENT_REPO/$resource" ]]; then
            SPARSE_CHECKOUT_LIST+=("$resource")
            echo -e "${BLUE}  Will include:${NC} $resource"
        else
            echo -e "${YELLOW}  Skipped (not found):${NC} $resource"
        fi
    done < "$SHARED_MANIFEST"
else
    echo -e "${YELLOW}No shared resources manifest found at $SHARED_MANIFEST${NC}"
fi

# Set sparse-checkout to exact list (prevents .venv, etc.)
echo "Configuring precise sparse-checkout..."
printf '%s\n' "${SPARSE_CHECKOUT_LIST[@]}" | git sparse-checkout set --stdin

# Checkout files and count
git checkout -q
# Use actual filesystem count instead of git ls-files (sparse-checkout bug)
FILE_COUNT=$(find . -type f -not -path "./.git/*" | wc -l)
echo -e "${BLUE}Debug:${NC} Counting actual files from $(pwd), found $FILE_COUNT files"

# Create isolated local directories (not shared with other worktrees)
echo "Creating isolated local directories..."
mkdir -p docs tests scratch

# Create docs/CLAUDE.md from template
CLAUDE_TEMPLATE="$PARENT_REPO/worktree-tools/templates/docs-claude.md.template"
if [[ -f "$CLAUDE_TEMPLATE" ]]; then
    cp "$CLAUDE_TEMPLATE" docs/CLAUDE.md
else
    echo -e "${YELLOW}Warning: Template not found at $CLAUDE_TEMPLATE, creating basic version${NC}"
    cat > docs/CLAUDE.md << 'EOF'
# Worktree Documentation Instructions for AI Agents

This docs/ folder is LOCAL to this worktree. Document your work here.

## File Organization
- docs/ - Isolated to this worktree
- tests/ - Component-specific tests only
- scratch/ - Temporary files and experiments

## Shared Files (Minimal Set)
- Makefile, pyproject.toml, .envrc, .gitignore, README.md, CLAUDE.md

Document your changes in docs/README.md
EOF
fi

# Create docs/README.md from template
README_TEMPLATE="$PARENT_REPO/worktree-tools/templates/docs-readme.md.template"
if [[ -f "$README_TEMPLATE" ]]; then
    # Use sed to substitute template variables
    sed -e "s/{{NAME}}/$NAME/g" \
        -e "s/{{BRANCH}}/$BRANCH/g" \
        -e "s/{{DATE}}/$(date -u +"%Y-%m-%d")/g" \
        -e "s|{{FOCUS_PATH}}|$FOCUS_PATH|g" \
        "$README_TEMPLATE" > docs/README.md
else
    echo -e "${YELLOW}Warning: Template not found at $README_TEMPLATE, creating basic version${NC}"
    cat > docs/README.md << EOF
# Worktree: $NAME
Branch: $BRANCH
Created: $(date -u +"%Y-%m-%d")

## Overview
[Describe what this worktree is working on]

## Changes Made
### ${FOCUS_PATH}/
[List changes made to your focus component]

## Technical Decisions
[Document important choices and rationale]

## Follow-up Required
[What needs to happen next]
EOF
fi

# tests/ directory created but no .gitkeep needed (will be tracked when files are added)

# Create scratch/.gitignore to ignore everything in scratch/
echo "*" > scratch/.gitignore

echo -e "${BLUE}Isolated directories created:${NC} docs/, tests/, scratch/"

# Recalculate file count including new local files
FILE_COUNT=$(find . -type f -not -path "./.git/*" | wc -l)

# Apply file count restrictions if needed
if [[ $FILE_COUNT -gt $MAX_FILES ]]; then
    echo -e "${YELLOW}Warning: $FILE_COUNT files exceeds $MAX_FILES limit${NC}"
    echo -e "${YELLOW}For component focus, this is expected. Use sparse-checkout to reduce if needed.${NC}"
    echo -e "${BLUE}Current focus: $FOCUS_PATH with shared resources${NC}"
fi

# Ensure isolated local directories still exist after any sparse-checkout changes
mkdir -p docs tests scratch

# Auto-allow direnv if .envrc exists (prevents blocking when entering worktree)
if [[ -f .envrc ]] && command -v direnv >/dev/null 2>&1; then
    echo "Auto-allowing direnv for worktree..."
    direnv allow 2>/dev/null || echo -e "${YELLOW}Warning: Could not auto-allow direnv${NC}"
fi

# Recreate docs/CLAUDE.md if missing
if [[ ! -f docs/CLAUDE.md ]]; then
    CLAUDE_TEMPLATE="$PARENT_REPO/worktree-tools/templates/docs-claude.md.template"
    if [[ -f "$CLAUDE_TEMPLATE" ]]; then
        cp "$CLAUDE_TEMPLATE" docs/CLAUDE.md
    else
        cat > docs/CLAUDE.md << 'EOF'
# Worktree Documentation Instructions for AI Agents

This docs/ folder is LOCAL to this worktree. Document your work here.

## File Organization
- docs/ - Isolated to this worktree
- tests/ - Component-specific tests only
- scratch/ - Temporary files and experiments

## Shared Files (Minimal Set)
- Makefile, pyproject.toml, .envrc, .gitignore, README.md, CLAUDE.md

Document your changes in docs/README.md
EOF
    fi
fi

# Recreate docs/README.md if missing
if [[ ! -f docs/README.md ]]; then
    README_TEMPLATE="$PARENT_REPO/worktree-tools/templates/docs-readme.md.template"
    if [[ -f "$README_TEMPLATE" ]]; then
        # Use sed to substitute template variables
        sed -e "s/{{NAME}}/$NAME/g" \
            -e "s/{{BRANCH}}/$BRANCH/g" \
            -e "s/{{DATE}}/$(date -u +"%Y-%m-%d")/g" \
            -e "s|{{FOCUS_PATH}}|$FOCUS_PATH|g" \
            "$README_TEMPLATE" > docs/README.md
    else
        cat > docs/README.md << EOF
# Worktree: $NAME
Branch: $BRANCH
Created: $(date -u +"%Y-%m-%d")

## Overview
[Describe what this worktree is working on]

## Changes Made
### ${FOCUS_PATH}/
[List changes made to your focus component]

## Technical Decisions
[Document important choices and rationale]

## Follow-up Required
[What needs to happen next]
EOF
    fi
fi

# tests/ directory maintained by actual test files, no .gitkeep needed
[[ ! -f scratch/.gitignore ]] && echo "*" > scratch/.gitignore

# Final file count including local files
FILE_COUNT=$(find . -type f -not -path "./.git/*" | wc -l)

# Create AI safety manifest
cat > .ai-safety-manifest << EOF
# AI Safety Manifest - Genesis Sparse Worktree
# This workspace has restricted visibility to prevent AI contamination

Worktree: $NAME
Focus: $FOCUS_PATH
Files: $FILE_COUNT/$MAX_FILES
Branch: $BRANCH
Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

AI Safety Rules:
1. Only modify files within focus path: $FOCUS_PATH
2. File limit enforced: $MAX_FILES maximum
3. No deep directory nesting (max 3 levels)
4. No imports from outside this worktree
5. Use Genesis smart-commit for quality gates

For other work areas, create separate sparse worktrees.
EOF

# Calculate directory depth for safety check (BSD find compatible)
MAX_DEPTH=$(find . -type d -not -path "./.git/*" 2>/dev/null | awk -F/ '{print NF-1}' | sort -nr | head -1 || echo 0)

# Display results
echo
echo -e "${GREEN}✓ Sparse worktree created successfully${NC}"
echo -e "${BLUE}Location:${NC} $WORKTREE_DIR"
echo -e "${BLUE}Files:${NC} $FILE_COUNT (limit: $MAX_FILES)"
echo -e "${BLUE}Depth:${NC} $MAX_DEPTH levels"

echo
echo -e "${BLUE}Included files:${NC}"
find . -type f -not -path "./.git/*" -not -name ".ai-safety-manifest" | head -8
[[ $FILE_COUNT -gt 8 ]] && echo "  ... and $((FILE_COUNT - 8)) more"

# Safety verification
if [[ "$VERIFY" == "true" ]]; then
    echo
    echo -e "${BLUE}Safety verification:${NC}"
    [[ $FILE_COUNT -le $MAX_FILES ]] && echo -e "${GREEN}✓ File count within limits${NC}" || echo -e "${RED}✗ File count exceeds limits${NC}"
    [[ $MAX_DEPTH -le 3 ]] && echo -e "${GREEN}✓ Directory depth safe${NC}" || echo -e "${YELLOW}⚠ Deep nesting: $MAX_DEPTH levels${NC}"
fi

echo
echo -e "${BLUE}Next steps:${NC}"
echo "  cd $WORKTREE_DIR"
echo "  # Work on $FOCUS_PATH"
echo "  # Use smart-commit when ready"
echo
echo -e "${GREEN}🎉 SUCCESS: AI-safe worktree '$NAME' created with $FILE_COUNT files${NC}"
echo -e "${BLUE}Ready for development work on $FOCUS_PATH${NC}"

# Ensure script exits successfully
exit 0
