# Worktree Tools - AI-Safe Development Isolation

Extracted and simplified sparse worktree creator from old Genesis codebase. Creates AI-safe development environments with file count limits and contamination prevention.

## Features

**Core AI Safety Features:**
- ✅ File count enforcement (<30 files default, configurable)
- ✅ Safety manifest creation (.ai-safety-manifest)
- ✅ Automatic contamination detection
- ✅ Directory depth limits validation
- ✅ Focus path isolation

**Simplifications from Original (230→159 lines):**
- Streamlined argument parsing and validation
- Simplified file count restrictions logic
- Focused error handling and user feedback
- Reduced verbose logging while maintaining safety
- Preserved all essential AI safety features

## Usage

```bash
# Create AI-safe sparse worktree focused on specific file
./src/create-sparse-worktree.sh fix-auth src/auth/login.py

# Focus on directory with custom file limit
./src/create-sparse-worktree.sh update-tests tests/unit/ --max-files 25

# Create with safety verification
./src/create-sparse-worktree.sh refactor-cli cli/commands/ --verify

# Get help
./src/create-sparse-worktree.sh --help
```

## AI Safety Workflow

The script enforces Genesis AI safety principles:

1. **File Count Limits**: Restricts visibility to prevent AI contamination
2. **Focus Isolation**: Only shows files related to your specific task
3. **Safety Manifest**: Documents workspace rules and restrictions
4. **Depth Limits**: Prevents deep directory nesting (≤3 levels)
5. **Contamination Prevention**: Blocks access to unrelated code areas

```bash
# After creation, your worktree will contain:
../worktrees/fix-auth/
├── .ai-safety-manifest     # Safety rules and restrictions
├── src/auth/              # Your focus area only
│   └── login.py
└── # Only essential files visible (limit: 30)
```

## Integration with Genesis Workflow

**Works with Genesis development patterns:**
- Integrates with smart-commit system
- Compatible with Genesis CI/CD workflows
- Respects component isolation (<30 files)
- Follows sparse checkout best practices

**AI Safety Validation:**
- File count checked during creation
- Directory depth verified (--verify flag)
- Safety manifest enforces workspace rules
- Focus path validation prevents contamination

## Development (AI-Safe Sparse Worktree)

```bash
# Work on worktree-tools in isolation
git worktree add ../worktree-tools-work feature/worktree-fixes
cd ../worktree-tools-work
git sparse-checkout set worktree-tools/

# Component has <5 files for AI safety:
# worktree-tools/
# ├── README.md
# ├── src/create-sparse-worktree.sh    # 159 lines
# └── tests/test_sparse_worktree.py
```

## Testing

```bash
# Run component tests
pytest worktree-tools/tests/ -v

# Test script functionality
cd worktree-tools/
./src/create-sparse-worktree.sh test-run src/auth.py --verify
```

## Safety Manifest Example

Each worktree includes an AI safety manifest:

```
# AI Safety Manifest - Genesis Sparse Worktree
Worktree: fix-auth
Focus: src/auth/login.py
Files: 8/30
Branch: sparse-fix-auth
Created: 2025-01-27T10:30:00Z

AI Safety Rules:
1. Only modify files within focus path: src/auth/login.py
2. File limit enforced: 30 maximum
3. No deep directory nesting (max 3 levels)
4. No imports from outside this worktree
5. Use Genesis smart-commit for quality gates
```

## Configuration

The script automatically:
- Detects repository structure and creates appropriate isolation
- Applies file count restrictions based on focus area size
- Validates focus paths exist before creation
- Creates safety manifests with workspace rules
- Integrates with Git sparse checkout for performance

No additional configuration required - works out of the box with Genesis patterns.
