#!/usr/bin/env bash
# Genesis Smart Commit System - Quality gates before commits
# Extracted and simplified from old Genesis (225→95 lines)

set -euo pipefail

# Load environment configuration if available
if [[ -f ".envrc" ]]; then
    source .envrc
elif [[ -f "../.envrc" ]]; then
    source ../.envrc
fi

# Colors and configuration
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
MIN_MSG_LENGTH=10; MAX_MSG_LENGTH=72

log() { echo -e "${2:-$BLUE}$1${NC}"; }
error_exit() { log "❌ $1" "$RED" >&2; exit 1; }

log "🎯 Genesis Smart Commit" "$BLUE"
log "======================"

# 1. Check for uncommitted changes
[[ -z $(git status --porcelain) ]] && error_exit "No changes to commit"

# 2. Run autofix system with convergent fixing first
log "ℹ️ Running Genesis AutoFixer..."
if command -v python &>/dev/null && python -c "from genesis.core.autofix import AutoFixer" 2>/dev/null; then
    # Use Genesis autofix system
    python -c "
from genesis.core.autofix import AutoFixer
import sys

try:
    fixer = AutoFixer()
    result = fixer.run()

    if not result.success:
        print(f'❌ AutoFixer failed: {result.error or \"Unknown error\"}')
        sys.exit(1)

    print('✅ Genesis AutoFixer completed successfully')
except Exception as e:
    print(f'❌ AutoFixer error: {e}')
    sys.exit(1)
" || error_exit "Genesis AutoFixer failed"
else
    # Fallback to basic linting
    log "⚠️ Genesis AutoFixer not available, using basic linting..." "$YELLOW"
    if command -v ruff &>/dev/null; then
        ruff check --fix . || error_exit "Ruff linting failed"
    fi
    if command -v black &>/dev/null; then
        black . &>/dev/null || true
    fi
fi
log "✅ AutoFixer completed" "$GREEN"

# 3. Run pre-commit hooks for validation
if [[ -f .pre-commit-config.yaml ]]; then
    log "ℹ️ Running pre-commit checks..."
    if ! pre-commit run --all-files; then
        echo -e "\n${YELLOW}💡 Common fixes:${NC}"
        echo "   • If main branch is protected: git checkout -b feature/your-change"
        echo "   • For formatting issues: make format"
        echo "   • For linting issues: make lint"
        echo "   • For test failures: make test"
        echo ""
        error_exit "Pre-commit checks failed"
    fi
    log "✅ Pre-commit checks passed" "$GREEN"
fi

# 4. Run tests with continue option
log "ℹ️ Running tests..."
test_cmd=""
if [[ -d tests/ ]] && command -v pytest &>/dev/null; then
    test_cmd="pytest tests/ -q"
elif [[ -f Makefile ]] && make -n test &>/dev/null; then
    test_cmd="make test"
fi

if [[ -n $test_cmd ]]; then
    if $test_cmd &>/dev/null; then
        log "✅ Tests passed" "$GREEN"
    else
        log "⚠️ Tests failed" "$YELLOW"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo; [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
fi

# 5. Basic secret detection
log "ℹ️ Scanning for secrets..."
if grep -rE "(sk-[a-zA-Z0-9]{48}|ghp_[a-zA-Z0-9]{36})" --include="*.py" --include="*.js" --include="*.ts" . 2>/dev/null | grep -v test; then
    error_exit "Potential secrets detected! Remove before committing"
fi

# 6. Interactive commit message
echo ""

# Check if commit message provided via environment variable (from CLI)
if [[ -n "${COMMIT_MESSAGE:-}" ]]; then
    commit_msg="$COMMIT_MESSAGE"
    log "Using provided commit message: $commit_msg"
# Check if commit type and message provided as arguments
elif [[ $# -ge 2 ]]; then
    type="$1"
    desc="$2"
    # Validate commit type
    if [[ ! "$type" =~ ^(feat|fix|docs|refactor|test|chore)$ ]]; then
        error_exit "Invalid commit type: $type. Must be one of: feat, fix, docs, refactor, test, chore"
    fi
    log "Using provided commit: $type: $desc"
    commit_msg="$type: $desc"
else
    error_exit "Commit message required. Use: CLI with --message or script with 'type' 'description' arguments"
fi

# Validate message length
[[ ${#commit_msg} -lt $MIN_MSG_LENGTH ]] && error_exit "Message too short (min $MIN_MSG_LENGTH chars)"
[[ ${#commit_msg} -gt $MAX_MSG_LENGTH ]] && error_exit "Message too long (max $MAX_MSG_LENGTH chars)"

# 7. Show preview and confirm
echo ""
log "📝 Changes to commit:"
git status --short
echo ""
log "💬 Message: $commit_msg"
echo ""

# Skip confirmation if message provided via environment variable (non-interactive)
if [[ -z "${COMMIT_MESSAGE:-}" ]]; then
    read -p "Proceed with commit? (Y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Nn]$ ]] && { log "Cancelled" "$YELLOW"; exit 0; }
fi

# 7. Update documentation before commit
log "ℹ️ Updating documentation..."

# Extract commit type from message for documentation updates
commit_type=$(echo "$commit_msg" | cut -d':' -f1)

# Update CHANGELOG.md if it exists and this is a meaningful change
if [[ -f "CHANGELOG.md" ]] && [[ "$commit_type" =~ ^(feat|fix|chore)$ ]]; then
    # Check if we already have an entry for this exact commit message (retry detection)
    if ! grep -q "$(echo "$commit_msg" | cut -d':' -f2- | sed 's/^ *//')" CHANGELOG.md 2>/dev/null; then
        log "📝 Adding entry to CHANGELOG.md"

        # Create a temporary changelog entry
        description=$(echo "$commit_msg" | cut -d':' -f2- | sed 's/^ *//')

        # Map commit types to changelog sections
        case "$commit_type" in
            "feat")
                section="### Added"
                ;;
            "fix")
                section="### Fixed"
                ;;
            "chore")
                section="### Changed"
                ;;
        esac

        # Create a temporary file with the changelog update
        temp_changelog=$(mktemp)

        # Process the changelog
        awk -v section="$section" -v entry="- $description" '
        /^## \[Unreleased\]/ {
            print $0
            unreleased_found = 1
            next
        }
        unreleased_found && /^### / {
            if ($0 == section) {
                print $0
                getline
                print entry
                print $0
                section_found = 1
            } else {
                print $0
            }
            next
        }
        unreleased_found && /^## \[/ && !section_found {
            print section
            print entry
            print ""
            print $0
            unreleased_found = 0
            next
        }
        { print $0 }
        END {
            if (unreleased_found && !section_found) {
                print section
                print entry
                print ""
            }
        }' CHANGELOG.md > "$temp_changelog"

        # Replace the original changelog
        mv "$temp_changelog" CHANGELOG.md

        log "✅ Updated CHANGELOG.md"
    else
        log "ℹ️ CHANGELOG.md already contains this entry (retry detected)"
    fi
else
    log "ℹ️ Skipping CHANGELOG.md update (no changelog or non-notable change)"
fi

# 8. Detect version bump needs
should_bump_version=false
if [[ -f "pyproject.toml" ]] && [[ "$commit_type" == "feat" ]]; then
    log "ℹ️ Feature detected - checking version bump..."

    # Simple version bump detection - only bump minor for feat
    current_version=$(grep -E '^version\s*=' pyproject.toml | sed -E 's/version\s*=\s*"([^"]+)"/\1/')

    if [[ -n "$current_version" ]]; then
        # Parse semantic version (major.minor.patch)
        IFS='.' read -r major minor patch <<< "$current_version"
        new_minor=$((minor + 1))
        new_version="$major.$new_minor.0"

        # Check if we already bumped to this version (retry detection)
        if [[ "$current_version" != "$new_version" ]]; then
            log "📈 Bumping version: $current_version → $new_version"

            # Update pyproject.toml
            sed -i.bak -E "s/version\s*=\s*\"[^\"]+\"/version = \"$new_version\"/" pyproject.toml
            rm pyproject.toml.bak 2>/dev/null || true

            should_bump_version=true
            log "✅ Version bumped in pyproject.toml"
        else
            log "ℹ️ Version already at expected level (retry detected)"
        fi
    fi
elif [[ "$commit_type" == "fix" ]]; then
    # For fixes, bump patch version
    current_version=$(grep -E '^version\s*=' pyproject.toml 2>/dev/null | sed -E 's/version\s*=\s*"([^"]+)"/\1/')

    if [[ -n "$current_version" ]]; then
        IFS='.' read -r major minor patch <<< "$current_version"
        new_patch=$((patch + 1))
        new_version="$major.$minor.$new_patch"

        if [[ "$current_version" != "$new_version" ]]; then
            log "🔧 Bumping patch version: $current_version → $new_version"

            sed -i.bak -E "s/version\s*=\s*\"[^\"]+\"/version = \"$new_version\"/" pyproject.toml
            rm pyproject.toml.bak 2>/dev/null || true

            should_bump_version=true
            log "✅ Patch version bumped in pyproject.toml"
        fi
    fi
fi

# 9. Create atomic commit with all changes
git add -A
git commit -m "$commit_msg"

log "✅ Commit created: $commit_msg" "$GREEN"
log "ℹ️ Next: git push to publish changes"
