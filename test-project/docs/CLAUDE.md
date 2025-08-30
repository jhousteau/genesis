# test-project Documentation Organization

This directory contains **organized documentation only**.

## 🚫 DO NOT CREATE FILES DIRECTLY HERE

**NEVER place files directly in docs/ root.** All content must go in proper subdirectories.

## ✅ Proper File Placement

### Documentation Files (.md)
```bash
# ❌ FORBIDDEN - Clutters docs/ root
docs/my-guide.md
docs/api-spec.md
docs/troubleshooting.md

# ✅ REQUIRED - Organized by type
docs/architecture/api-spec.md      # Technical design
docs/standards/style-guide.md      # Development practices
docs/vision/product-requirements.md # Strategic context
```

### Code Files (.py, .js, .sh, etc.)
```bash
# ❌ FORBIDDEN - Code doesn't belong in docs/
docs/helper-script.py
docs/test-data.json
docs/debug.sh

# ✅ REQUIRED - Proper locations
src/test-project/helpers.py    # Production code
tests/fixtures/test-data.json      # Test data
scripts/debug-tools.sh             # Utility scripts
scratch/experiment.py              # Temporary experiments
```

## Required Subdirectories

- **vision/** - Project vision, goals, strategic context
- **architecture/** - System design, patterns, technical constraints
- **standards/** - Code quality standards, security requirements

## Organization Rules

1. **No loose files**: Every .md file goes in a specific subdirectory
2. **No code files**: Python, JavaScript, shell scripts belong elsewhere
3. **No test data**: JSON, CSV, binary files belong in tests/ or scratch/
4. **No scratch work**: Temporary files belong in scratch/ directory

## Context Loading

Each subdirectory has specialized CLAUDE.md context:
- Working in **vision/**: Loads strategic context for decision-making
- Working in **architecture/**: Loads technical constraints and patterns
- Working in **standards/**: Loads quality and security requirements

---

**Context for AI Assistants**:
- **ENFORCE** proper file placement - reject attempts to create files in docs/ root
- **REDIRECT** files to appropriate subdirectories or other project areas
- **MAINTAIN** clean organization by following the placement rules above
