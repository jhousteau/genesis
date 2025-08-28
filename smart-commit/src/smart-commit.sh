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
    pre-commit run --all-files || error_exit "Pre-commit checks failed"
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

# 8. Create commit
git add .
git commit -m "$commit_msg"

log "✅ Commit created: $commit_msg" "$GREEN"
log "ℹ️ Next: git push to publish changes"
