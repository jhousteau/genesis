#!/usr/bin/env bash
# Genesis Smart Commit System - Quality gates before commits
# Extracted and simplified from old Genesis (225→95 lines)

set -euo pipefail

# Colors and configuration
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
MIN_MSG_LENGTH=10; MAX_MSG_LENGTH=72

log() { echo -e "${2:-$BLUE}$1${NC}"; }
error_exit() { log "❌ $1" "$RED" >&2; exit 1; }

log "🎯 Genesis Smart Commit" "$BLUE"
log "======================"

# 1. Check for uncommitted changes
[[ -z $(git status --porcelain) ]] && error_exit "No changes to commit"

# 2. Run pre-commit hooks if available
if [[ -f .pre-commit-config.yaml ]]; then
    log "ℹ️ Running pre-commit checks..."
    pre-commit run --all-files || error_exit "Pre-commit checks failed"
    log "✅ Pre-commit checks passed" "$GREEN"
fi

# 3. Run tests with continue option
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

# 4. Run linting with auto-fix
log "ℹ️ Running linters..."
if command -v ruff &>/dev/null; then
    ruff check --fix . || error_exit "Ruff linting failed"
fi
if command -v black &>/dev/null; then
    black . &>/dev/null || true
fi
log "✅ Code quality checks passed" "$GREEN"

# 5. Basic secret detection
log "ℹ️ Scanning for secrets..."
if grep -rE "(sk-[a-zA-Z0-9]{48}|ghp_[a-zA-Z0-9]{36})" --include="*.py" --include="*.js" --include="*.ts" . 2>/dev/null | grep -v test; then
    error_exit "Potential secrets detected! Remove before committing"
fi

# 6. Interactive commit message
echo ""
PS3="Select commit type: "
select type in "feat" "fix" "docs" "refactor" "test" "chore"; do
    [[ -n $type ]] && break
done

read -p "Enter description: " desc
commit_msg="$type: $desc"

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

read -p "Proceed with commit? (Y/n): " -n 1 -r
echo
[[ $REPLY =~ ^[Nn]$ ]] && { log "Cancelled" "$YELLOW"; exit 0; }

# 8. Create commit
git add .
git commit -m "$commit_msg"

log "✅ Commit created: $commit_msg" "$GREEN"
log "ℹ️ Next: git push to publish changes"