#!/usr/bin/env bash
# Genesis Worktree Manager - List and manage sparse worktrees

set -euo pipefail

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

show_usage() {
    cat << EOF
Usage: $0 [COMMAND]

List and manage Genesis sparse worktrees.

Commands:
  list, ls      List all worktrees (default)
  status        Show detailed worktree status
  clean         Remove deleted worktrees
  help          Show this help

Examples:
  $0                    # List worktrees
  $0 status            # Detailed status
  $0 clean             # Clean up deleted worktrees

Note: Worktrees are stored in worktrees/ directory
EOF
}

list_worktrees() {
    echo -e "${BLUE}Genesis Sparse Worktrees${NC}"
    echo "========================"

    if [[ ! -d "worktrees" ]]; then
        echo -e "${YELLOW}No worktrees directory found${NC}"
        return 0
    fi

    local count=0
    for worktree_dir in worktrees/*/; do
        if [[ -d "$worktree_dir" ]]; then
            local name=$(basename "$worktree_dir")
            local manifest_file="$worktree_dir/.ai-safety-manifest"

            echo -e "${GREEN}$name${NC}"

            if [[ -f "$manifest_file" ]]; then
                # Extract key info from manifest
                local focus=$(grep "^Focus:" "$manifest_file" | cut -d' ' -f2- || echo "Unknown")
                local files=$(grep "^Files:" "$manifest_file" | cut -d' ' -f2 | cut -d'/' -f1 || echo "?")
                local created=$(grep "^Created:" "$manifest_file" | cut -d' ' -f2- || echo "Unknown")

                echo "  Focus: $focus"
                echo "  Files: $files"
                echo "  Created: $created"
            else
                echo "  (No manifest found)"
            fi

            echo "  Path: $worktree_dir"
            echo
            ((count++))
        fi
    done

    if [[ $count -eq 0 ]]; then
        echo -e "${YELLOW}No worktrees found${NC}"
    else
        echo -e "${BLUE}Total worktrees: $count${NC}"
    fi
}

show_status() {
    echo -e "${BLUE}Genesis Worktree Status${NC}"
    echo "======================="

    # Git worktree list
    echo
    echo -e "${BLUE}Git worktree status:${NC}"
    git worktree list

    echo
    list_worktrees
}

clean_worktrees() {
    echo -e "${BLUE}Cleaning up worktrees...${NC}"
    git worktree prune
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Parse command
COMMAND="${1:-list}"

case "$COMMAND" in
    list|ls|"")
        list_worktrees
        ;;
    status)
        show_status
        ;;
    clean)
        clean_worktrees
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        show_usage
        exit 1
        ;;
esac
