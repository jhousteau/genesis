# Genesis Worktree Strategy

## Overview

Genesis uses focused sparse worktrees to enable AI-safe development with complete component isolation. Each worktree provides a small, focused context for AI agents while maintaining operational functionality.

## Core Principles

1. **Isolation First**: Prevent agent confusion by ensuring only one editable version of each component
2. **Growth Buffer Strategy**: Set file limits based on current size + growth buffer, not arbitrary numbers
3. **File Type Awareness**: Template/config files can handle higher limits than dense logic files
4. **Focused Context**: Small, manageable contexts are easier to understand and maintain

## Current Component Analysis (August 2025)

### File Counts and Classifications
```
Component           Files  Type        AI Complexity
testing/              8   Mixed        Medium
genesis/core/        30   Logic        High
genesis/commands/     8   Logic        High
bootstrap/            3   Mixed        Low
templates/python-api/ 34   Templates    Low (verbose config)
templates/other/     28   Templates    Low (boilerplate)
smart-commit/         3   Logic        Medium
worktree-tools/       7   Scripts      Medium
shared-python/       16   Logic        Medium
shared-typescript/   14   Logic        Medium
terraform/           40   Config       Low-Medium
```

## Approved Worktree Plan

### Genesis Core Split
```bash
# Split large genesis/ component for focused work
genesis worktree create genesis-core-branch genesis/core --max-files 35
genesis worktree create genesis-commands-branch genesis/commands --max-files 15
```

**Rationale**:
- `genesis/core` (30 files) → 35 limit: Dense logic files, minimal growth buffer
- `genesis/commands` (8 files) → 15 limit: Logic files, room to grow

### Template Split
```bash
# Split by template complexity, higher limits for config-heavy files
genesis worktree create template-python-branch templates/python-api --max-files 40
genesis worktree create template-misc-branch templates/cli-tool templates/typescript-service templates/terraform-project --max-files 35
```

**Rationale**:
- Template files are verbose config/boilerplate, not complex logic
- AI handles configuration files better than equivalent count of logic files
- Python API template is largest and most complex, gets own worktree

### Small Components (Growth Buffer Strategy)
```bash
# Current size → Growth buffer limit (reasoning)
genesis worktree create testing-branch testing/ --max-files 15                    # 8 → 15 (can almost double)
genesis worktree create bootstrap-branch bootstrap/ --max-files 10              # 3 → 10 (can triple)
genesis worktree create smart-commit-branch smart-commit/ --max-files 10       # 3 → 10 (can triple)
genesis worktree create worktree-tools-branch worktree-tools/ --max-files 15  # 7 → 15 (can double)
genesis worktree create shared-python-branch shared-python/ --max-files 25      # 16 → 25 (50% growth)
genesis worktree create shared-ts-branch shared-typescript/ --max-files 20      # 14 → 20 (40% growth)
genesis worktree create terraform-branch terraform/ --max-files 45              # 40 → 45 (config files, small buffer)
```

## File Limit Philosophy

### Growth Buffer Formula
```
Max Limit = Current Files + Growth Buffer
```

### Buffer Size Guidelines
- **Tiny components** (1-5 files): Can triple (generous growth room)
- **Small components** (5-15 files): Can double (good growth room)
- **Medium components** (15-25 files): 40-60% growth (moderate room)
- **Large components** (25+ files): 20% growth (conservative, consider splitting)

### File Type Adjustments
- **Logic files** (`.py`, `.ts`, `.js`): Use conservative limits
- **Config files** (`.json`, `.yaml`, `.toml`): Can handle +20% more
- **Template files** (boilerplate, examples): Can handle +40% more
- **Documentation** (`.md`): Very AI-friendly, high limits OK

## Isolation Benefits

### What Each Worktree Contains
- **Focus component** (e.g., `genesis/core/`)
- **Isolated docs/** (worktree-specific documentation)
- **Isolated tests/** (component-specific tests)
- **Isolated scratch/** (temporary files)
- **Minimal shared files** (7 files: Makefile, pyproject.toml, .envrc, .gitignore, .pre-commit-config.yaml, README.md, CLAUDE.md)

### What's NOT Shared
- Global docs/ (stays in main)
- Global scripts/ (stays in main)
- Global tests/ (stays in main)
- Other components (complete isolation)

## Expected Outcomes

### AI Safety
- Each worktree stays under 45 files maximum
- AI agents have clear, focused context
- No confusion about which files to edit

### Development Benefits
- Complete component isolation
- Independent documentation per worktree
- Component-specific testing
- Clean merge strategy (minimal shared surface)

### Growth Management
- Early warning when components hit limits
- Forced architectural decisions at appropriate times
- Natural evolution path (split worktrees when needed)

## Review Schedule

- **Monthly**: Check actual file counts vs limits
- **When limits hit**: Decide to split worktree or increase limit
- **Quarterly**: Review overall strategy effectiveness

## Decision Log

**August 30, 2025**: Initial worktree strategy defined
- Chose focused breakdown over single large worktrees
- Implemented growth buffer strategy
- Recognized file type differences in AI handling
- Set 11 focused worktrees as starting point

---

*This strategy can be revisited and adjusted based on actual development experience.*
