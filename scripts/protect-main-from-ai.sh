#!/usr/bin/env bash
# AI Protection Hook - Prevents AI from working directly in main workspace

set -euo pipefail

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

check_ai_protection() {
    # Skip if we're in a worktree (has .ai-safety-manifest)
    if [[ -f ".ai-safety-manifest" ]]; then
        return 0  # Allow - we're in a worktree
    fi

    # Detect if Claude/AI is running
    local is_ai=false

    # Check for Claude Code environment variables
    if [[ -n "${CLAUDE_CODE:-}" ]] || [[ -n "${AI_ASSISTANT:-}" ]]; then
        is_ai=true
    fi

    # Check for common AI process indicators
    if pgrep -f "claude|anthropic" >/dev/null 2>&1; then
        is_ai=true
    fi

    # Check environment variables that Claude Code sets
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]] || [[ -n "${CLAUDE_SESSION:-}" ]]; then
        is_ai=true
    fi

    # Check for AI-specific terminal patterns
    if [[ "${TERM_PROGRAM:-}" == "claude-code" ]] || [[ "${EDITOR:-}" == *"claude"* ]]; then
        is_ai=true
    fi

    # Check for tool execution patterns (Claude Code tools)
    if [[ -n "${CLAUDE_TOOL_EXECUTION:-}" ]] || [[ "${BASH_SOURCE[*]}" == *"claude"* ]]; then
        is_ai=true
    fi

    # Force AI detection for testing if requested
    if [[ "${1:-}" == "--test-ai-mode" ]]; then
        is_ai=true
    fi

    if [[ "$is_ai" == "true" ]]; then
        echo -e "${RED}🤖 AI SAFETY PROTECTION ACTIVE${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo
        echo -e "${YELLOW}❌ AI assistants cannot work directly in the main workspace${NC}"
        echo
        echo -e "${BLUE}Why this protection exists:${NC}"
        echo "  • Main workspace has $(git ls-files 2>/dev/null | wc -l | tr -d ' ') files - too many for AI context"
        echo "  • AI works better with focused, small file sets (<30 files)"
        echo "  • Prevents contamination across unrelated project areas"
        echo "  • Enforces clean separation of concerns"
        echo "  • Protects against accidental broad changes"
        echo
        echo -e "${GREEN}✅ Solution: Create a focused worktree for your specific task${NC}"
        echo
        echo -e "${YELLOW}Create new worktree:${NC}"
        echo "  ./worktree-tools/src/create-sparse-worktree.sh <name> <focus-path> --max-files 25"
        echo
        echo -e "${YELLOW}Examples:${NC}"
        echo "  ./worktree-tools/src/create-sparse-worktree.sh fix-auth src/auth/"
        echo "  ./worktree-tools/src/create-sparse-worktree.sh update-tests tests/unit/"
        echo "  ./worktree-tools/src/create-sparse-worktree.sh add-docs docs/guides/"
        echo
        echo -e "${BLUE}Existing worktrees:${NC}"
        if [[ -d "worktrees" ]] && ls worktrees/ >/dev/null 2>&1; then
            ls worktrees/ | sed 's/^/  📁 /'
            echo "  💡 cd worktrees/<name> to switch to existing worktree"
        else
            echo "  (none created yet - create your first one above!)"
        fi
        echo
        echo -e "${GREEN}Note: Humans can work in main normally - this only protects against AI context overflow${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return 1  # Block AI
    fi

    return 0  # Allow humans
}

# If called directly, run the check
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    check_ai_protection "$@"
fi
