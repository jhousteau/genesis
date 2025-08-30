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

# Create worktree with sparse checkout
echo "Setting up worktree..."
git worktree add --no-checkout "$WORKTREE_DIR" -b "$BRANCH" 2>/dev/null || \
git worktree add --no-checkout "$WORKTREE_DIR" "$BRANCH" 2>/dev/null || {
    echo -e "${RED}Failed to create worktree - may already exist${NC}"; exit 1;
}

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

# Checkout files and count
git checkout -q
FILE_COUNT=$(git ls-files --cached --others --exclude-standard | wc -l)

# Apply file count restrictions if needed
if [[ $FILE_COUNT -gt $MAX_FILES ]]; then
    echo -e "${YELLOW}File count ($FILE_COUNT) exceeds limit ($MAX_FILES) - applying restrictions${NC}"

    # Create a temporary file with restricted patterns
    TEMP_PATTERNS=$(mktemp)

    # Get code files from the focus path, limited to MAX_FILES
    git ls-files --cached --others --exclude-standard | \
        grep -E '\.(py|ts|js|go|sh|md)$' | \
        grep "^$FOCUS_PATH" | \
        head -"$MAX_FILES" > "$TEMP_PATTERNS"

    # If we still don't have enough files, include some other important files
    if [[ $(wc -l < "$TEMP_PATTERNS") -lt $MAX_FILES ]]; then
        git ls-files --cached --others --exclude-standard | \
            grep "^$FOCUS_PATH" | \
            grep -E '\.(json|toml|yml|yaml|txt)$' | \
            head -$((MAX_FILES - $(wc -l < "$TEMP_PATTERNS"))) >> "$TEMP_PATTERNS"
    fi

    # Apply the sparse checkout with the filtered files
    if [[ -s "$TEMP_PATTERNS" ]]; then
        # Add the focus directory pattern to ensure directory structure
        echo "$FOCUS_PATH/*" > "$TEMP_PATTERNS.final"
        cat "$TEMP_PATTERNS" >> "$TEMP_PATTERNS.final"

        git sparse-checkout set --stdin < "$TEMP_PATTERNS.final"
        rm "$TEMP_PATTERNS" "$TEMP_PATTERNS.final"
    else
        # Fallback to just the focus path if no specific files found
        git sparse-checkout set "$FOCUS_PATH"
    fi

    FILE_COUNT=$(git ls-files | wc -l)
fi

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

# Calculate directory depth for safety check
MAX_DEPTH=$(find . -type d -not -path "./.git/*" -printf '%d\n' 2>/dev/null | sort -nr | head -1 || echo 0)

# Display results
echo
echo -e "${GREEN}✓ Sparse worktree created successfully${NC}"
echo -e "${BLUE}Location:${NC} $WORKTREE_DIR"
echo -e "${BLUE}Files:${NC} $FILE_COUNT (limit: $MAX_FILES)"
echo -e "${BLUE}Depth:${NC} $MAX_DEPTH levels"

echo
echo -e "${BLUE}Included files:${NC}"
git ls-files --cached --others --exclude-standard | grep -v ".ai-safety-manifest" | head -8
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
echo -e "${YELLOW}This is an AI-safe workspace - only $FILE_COUNT files visible to prevent contamination${NC}"
