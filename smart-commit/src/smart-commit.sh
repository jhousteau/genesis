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

# 3. Handle branch management before pre-commit checks
log "ℹ️ Checking branch status..."
current_branch=$(git branch --show-current)
main_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

# Check if we're on the main branch and need to create a feature branch
if [[ "$current_branch" == "$main_branch" ]]; then
    # We need a commit message to create a proper branch name
    # Check if commit message provided via environment variable (from CLI)
    if [[ -n "${COMMIT_MESSAGE:-}" ]]; then
        commit_msg="$COMMIT_MESSAGE"
    # Check if commit type and message provided as arguments
    elif [[ $# -ge 2 ]]; then
        type="$1"
        desc="$2"
        # Validate commit type
        if [[ ! "$type" =~ ^(feat|fix|docs|refactor|test|chore)$ ]]; then
            error_exit "Invalid commit type: $type. Must be one of: feat, fix, docs, refactor, test, chore"
        fi
        commit_msg="$type: $desc"
    else
        # Create a generic branch name with timestamp
        timestamp=$(date +"%Y%m%d-%H%M%S")
        branch_name="feature/auto-branch-$timestamp"
        log "🌿 Creating auto-branch: $branch_name" "$YELLOW"
        git checkout -b "$branch_name"
    fi

    # If we have a commit message, create a descriptive branch name
    if [[ -n "${commit_msg:-}" ]]; then
        commit_type=$(echo "$commit_msg" | cut -d':' -f1)
        case "$commit_type" in
            "feat")
                branch_name="feature/$(echo "$commit_msg" | sed -E 's/^feat: //' | sed -E 's/[^a-zA-Z0-9]+/-/g' | tr '[:upper:]' '[:lower:]' | sed -E 's/-+$//g')"
                ;;
            "fix")
                branch_name="fix/$(echo "$commit_msg" | sed -E 's/^fix: //' | sed -E 's/[^a-zA-Z0-9]+/-/g' | tr '[:upper:]' '[:lower:]' | sed -E 's/-+$//g')"
                ;;
            *)
                branch_name="chore/$(echo "$commit_msg" | sed -E 's/^[^:]+: //' | sed -E 's/[^a-zA-Z0-9]+/-/g' | tr '[:upper:]' '[:lower:]' | sed -E 's/-+$//g')"
                ;;
        esac

        log "🌿 Creating branch: $branch_name" "$GREEN"
        git checkout -b "$branch_name"
    fi
fi

# 4. Pre-commit validation handled by AutoFixer ValidationStage
# (removed duplicate pre-commit execution that caused convergence issues)

# 4. Run tests with continue option
log "ℹ️ Running tests..."
test_cmd=""
if [[ -f Makefile ]] && make -n test &>/dev/null; then
    # Prefer Makefile test target (official project test command)
    test_cmd="make test"
elif [[ -f pyproject.toml ]] && command -v poetry &>/dev/null && [[ -d tests/ ]]; then
    # Poetry project - use poetry run pytest on tests directory only
    test_cmd="poetry run pytest tests/"
elif [[ -d tests/ ]] && command -v pytest &>/dev/null; then
    # Fallback to direct pytest
    test_cmd="pytest tests/ -q"
fi

if [[ -n $test_cmd ]]; then
    echo "Running: $test_cmd"
    if eval "$test_cmd"; then
        log "✅ Tests passed" "$GREEN"
    else
        log "⚠️ Tests failed" "$YELLOW"
        echo ""
        echo "Test command that failed: $test_cmd"
        echo "Run the command above to see detailed error output."
        echo ""
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

# 8. Update documentation before commit
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

# 9. Detect version bump needs
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

# 10. Create atomic commit with all changes (with pre-commit hook handling)
git add -A

# Try commit and handle pre-commit hook modifications
max_attempts=3
attempt=1

while [ $attempt -le $max_attempts ]; do
    log "🔄 Commit attempt $attempt/$max_attempts..."

    if git commit -m "$commit_msg"; then
        log "✅ Commit successful!" "$GREEN"
        break
    else
        # Pre-commit hooks may have modified files - check and restage
        if [[ -n $(git status --porcelain) ]]; then
            log "ℹ️ Pre-commit hooks modified files, restaging..." "$YELLOW"
            git add -A
            attempt=$((attempt + 1))

            if [ $attempt -gt $max_attempts ]; then
                error_exit "Failed to commit after $max_attempts attempts. Pre-commit hooks keep modifying files."
            fi
        else
            error_exit "Commit failed for unknown reason"
        fi
    fi
done

log "✅ Commit created: $commit_msg" "$GREEN"

# 11. Push changes and create PR if needed
current_branch=$(git branch --show-current)

if [[ "$current_branch" != "$main_branch" ]]; then
    log "📤 Pushing branch to origin..."
    git push -u origin "$current_branch"

    # Create PR if gh CLI is available
    if command -v gh &> /dev/null; then
        log "🔗 Creating pull request..."

        # Generate PR description based on commit type
        pr_body=""
        case "$commit_type" in
            "feat")
                pr_body="## Summary\n- New feature: $(echo "$commit_msg" | sed -E 's/^feat: //')\n\n## Test plan\n- [ ] Manual testing completed\n- [ ] All existing tests pass"
                ;;
            "fix")
                pr_body="## Summary\n- Bug fix: $(echo "$commit_msg" | sed -E 's/^fix: //')\n\n## Test plan\n- [ ] Fix verified manually\n- [ ] All existing tests pass"
                ;;
            *)
                pr_body="## Summary\n- $(echo "$commit_msg" | sed -E 's/^[^:]+: //')\n\n## Test plan\n- [ ] Changes reviewed and tested"
                ;;
        esac

        gh pr create --title "$commit_msg" --body "$pr_body" --base "$main_branch" || {
            log "⚠️ Could not create PR automatically - create manually if needed"
        }
    else
        log "ℹ️ Install gh CLI for automatic PR creation"
    fi
else
    log "ℹ️ On main branch - changes committed locally"
fi
