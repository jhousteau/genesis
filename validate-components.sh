#!/bin/bash
# Component validation script - ensures AI safety limits

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Validating Genesis component structure for AI safety..."
echo

components=("genesis-cli" "smart-commit" "bootstrap" "shared-python" "worktree-tools" "testing")
max_files=30
total_components=0
valid_components=0

for component in "${components[@]}"; do
    if [ -d "$component" ]; then
        file_count=$(find "$component" -type f | wc -l | tr -d ' ')
        total_components=$((total_components + 1))

        echo "📁 $component: $file_count files"

        if [ "$file_count" -le "$max_files" ]; then
            echo "  ✅ SAFE for AI development"
            valid_components=$((valid_components + 1))
        else
            echo "  ❌ EXCEEDS AI safety limit ($max_files files)"
        fi

        # Check for README
        if [ -f "$component/README.md" ]; then
            echo "  📖 README.md present"
        else
            echo "  ⚠️  Missing README.md"
        fi

        echo
    fi
done

echo "📊 Summary:"
echo "  Components checked: $total_components"
echo "  AI-safe components: $valid_components"

if [ "$valid_components" -eq "$total_components" ]; then
    echo -e "${GREEN}✅ All components are AI-safe!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some components exceed AI safety limits${NC}"
    exit 1
fi
