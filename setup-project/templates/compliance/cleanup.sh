#!/usr/bin/env bash
# Project Cleanup Script
# Removes garbage files and maintains project hygiene

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🧹 Running project cleanup...${NC}"

# Counter for cleaned items
CLEANED=0

# Clean Python artifacts
if find . -name "*.pyc" -o -name "*.pyo" 2>/dev/null | grep -q .; then
    find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
    echo "✓ Removed Python bytecode files"
    ((CLEANED++))
fi

if find . -name "__pycache__" 2>/dev/null | grep -q .; then
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo "✓ Removed __pycache__ directories"
    ((CLEANED++))
fi

# Clean temp files
if find . -name "*.tmp" -o -name "*.temp" 2>/dev/null | grep -q .; then
    find . -type f \( -name "*.tmp" -o -name "*.temp" \) -delete
    echo "✓ Removed temporary files"
    ((CLEANED++))
fi

# Clean temp directory (keep directory, remove old files)
if [[ -d "temp" ]]; then
    find temp -type f -mtime +1 -delete 2>/dev/null || true
    echo "✓ Cleaned old files from temp/"
    ((CLEANED++))
fi

# Clean OS-specific files
if find . -name ".DS_Store" -o -name "Thumbs.db" 2>/dev/null | grep -q .; then
    find . -type f \( -name ".DS_Store" -o -name "Thumbs.db" \) -delete
    echo "✓ Removed OS-specific files"
    ((CLEANED++))
fi

# Clean editor backup files
if find . -name "*~" -o -name "*.swp" -o -name "*.swo" 2>/dev/null | grep -q .; then
    find . -type f \( -name "*~" -o -name "*.swp" -o -name "*.swo" \) -delete
    echo "✓ Removed editor backup files"
    ((CLEANED++))
fi

# Clean backup files
if find . -name "*.bak" -o -name "*.old" -o -name "*.orig" 2>/dev/null | grep -q .; then
    find . -type f \( -name "*.bak" -o -name "*.old" -o -name "*.orig" \) -delete
    echo "✓ Removed backup files"
    ((CLEANED++))
fi

# Clean log files older than 7 days
if find . -name "*.log" -mtime +7 2>/dev/null | grep -q .; then
    find . -name "*.log" -mtime +7 -delete
    echo "✓ Removed old log files"
    ((CLEANED++))
fi

# Clean build artifacts
DIRS_TO_CLEAN=(
    "build"
    "dist"
    ".pytest_cache"
    ".tox"
    ".mypy_cache"
    ".ruff_cache"
    "htmlcov"
    ".coverage"
    "*.egg-info"
)

for dir in "${DIRS_TO_CLEAN[@]}"; do
    if [[ -d "$dir" ]] || find . -name "$dir" 2>/dev/null | grep -q .; then
        find . -name "$dir" -type d -exec rm -rf {} + 2>/dev/null || true
        echo "✓ Removed $dir"
        ((CLEANED++))
    fi
done

# Clean empty directories
if find . -type d -empty 2>/dev/null | grep -q .; then
    find . -type d -empty -delete 2>/dev/null || true
    echo "✓ Removed empty directories"
    ((CLEANED++))
fi

# Summary
echo ""
if [[ $CLEANED -eq 0 ]]; then
    echo -e "${GREEN}✨ Project is already clean!${NC}"
else
    echo -e "${GREEN}✅ Cleanup complete! Removed $CLEANED type(s) of files${NC}"
fi

# Optional: Show disk usage
echo ""
echo "Disk usage:"
du -sh . 2>/dev/null || true