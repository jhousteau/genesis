# Sparse Worktrees Guide

This guide explains how to set up and use sparse worktrees in the Genesis project to maintain AI safety limits while working on specific components. The main workspace includes AI protection that blocks assistants from working directly on the full codebase.

## Overview

Sparse worktrees allow you to create isolated working directories that contain only the files you need for a specific task. This keeps each workspace under the AI safety limit of 30 files while still having access to shared resources. AI assistants are automatically blocked from working in the main workspace to prevent context overflow.

## Why Use Sparse Worktrees?

- **AI Safety**: Each worktree stays under 30 files for optimal AI tool performance
- **Focused Work**: Only see files relevant to your current task
- **Clean Separation**: Changes are isolated to specific areas
- **Shared Resources**: All worktrees have access to docs/, scripts/, and config files
- **No Contamination**: Unrelated files don't pollute your workspace
- **AI Protection**: Main workspace blocks AI assistants to prevent context overflow
- **Universal Pattern**: Works for Genesis and all client projects ("eat our own dog food")

## Prerequisites

### Main Repository Setup
**Before creating any worktrees, ensure the main repository is properly configured:**

1. **Repository health**: You must be in the main Genesis repository with a clean working state
2. **Dependencies installed**: Run `make setup` to install all dependencies
3. **Tests passing**: Run `make test` to verify all tests pass in main
4. **Quality gates working**: Run `make lint` to ensure formatting and linting work
5. **Git configuration**: Ensure git is configured with your user.name and user.email

```bash
# Verify main repository is ready
cd /path/to/genesis
git status                          # Should be clean
make setup                         # Install dependencies
make test                          # All tests should pass
make lint                          # All quality gates should pass
```

### Worktree Tool Prerequisites
1. The `worktree-tools/src/create-sparse-worktree.sh` script must be available
2. The `worktrees/` directory will be created automatically inside the project
3. Git worktree support (Git 2.5+ required)

**⚠️ Important**: Do not create worktrees from an unstable main branch. Always ensure main is in a good state first.

## AI Protection System

Genesis includes built-in AI protection to prevent context overflow:

- **Main workspace is protected**: AI assistants cannot work directly in main (211+ files)
- **Automatic detection**: `.envrc` detects AI tools and blocks them with helpful message
- **Worktree bypass**: Worktrees include `.ai-safety-manifest` that allows AI work
- **Human-friendly**: Humans can work normally in main workspace
- **Educational**: Block message explains the issue and shows worktree creation commands

When an AI assistant tries to work in main, they see:
```
🤖 AI SAFETY PROTECTION ACTIVE
❌ AI assistants cannot work directly in the main workspace
Why: Main workspace has 211 files - too many for AI context
✅ Solution: Create a focused worktree for your specific task
```

## Worktree Structure

After creation, your directory structure will look like:

```
genesis/                       # Main repository (211 files)
├── .git/                     # Git repository data
├── worktrees/                # All sparse worktrees (visible to developers, ignored by git)
│   ├── test-fixes/           # For test suite fixes (~45 files)
│   ├── core-genesis/         # For core module work (~45 files)
│   ├── component-fixes/      # For component updates (~40 files)
│   └── cli-integration/      # For CLI improvements (~35 files)
├── src/                      # Source code
├── scripts/                  # Utility scripts
└── docs/                     # Documentation
```

## Integration with Genesis CLI

While this guide focuses on the direct worktree creation script, Genesis also provides CLI integration:

```bash
# Future Genesis CLI commands (in development)
genesis worktree create test-fixes testing/ --max-files 25
genesis worktree list
genesis worktree remove test-fixes
genesis worktree status
```

For now, use the direct script as documented below.

## Creating Worktrees

### 1. Test-Fixes Worktree

**Purpose**: Fix pytest configuration, test infrastructure, and cross-component testing

```bash
./worktree-tools/src/create-sparse-worktree.sh test-fixes testing/ --max-files 25
```

**Contains**:
- `testing/` directory - Core testing utilities and fixtures
- `tests/conftest.py` - Root pytest configuration
- `tests/test_integration.py` - Cross-component integration tests
- `Makefile` - Test orchestration commands
- Shared resources (see below)

**Test Strategy**: This worktree focuses on the testing infrastructure that supports all components. Component-specific tests remain with their components for isolated development.

### 2. Core-Genesis Worktree

**Purpose**: Work on Genesis core modules and utilities

```bash
./worktree-tools/src/create-sparse-worktree.sh core-genesis genesis/core --max-files 25
```

**Contains**:
- `genesis/core/` directory
- Related test files
- Shared resources (see below)

### 3. Component-Fixes Worktree

**Purpose**: Work on individual components (bootstrap, smart-commit, worktree-tools)

```bash
./worktree-tools/src/create-sparse-worktree.sh component-fixes bootstrap/ --max-files 25
```

**Contains**:
- One component directory at a time (e.g., `bootstrap/`)
- Component's tests (`bootstrap/tests/`)
- Component's documentation (`bootstrap/README.md`)
- Shared resources (see below)

**Test Strategy**: Each component includes its own tests for isolated development. Run `pytest bootstrap/tests/` within the worktree to test only that component.

### 4. CLI-Integration Worktree

**Purpose**: Work on CLI commands and integration features

```bash
./worktree-tools/src/create-sparse-worktree.sh cli-integration genesis/cli.py --max-files 25
```

**Contains**:
- `genesis/cli.py`
- `genesis/commands/` directory
- Integration tests
- `templates/` directory (for bootstrap command)
- Shared resources (see below)

## Adding Shared Resources

After creating any worktree, add shared resources that all worktrees need:

```bash
# Navigate to the worktree
cd worktrees/<worktree-name>

# Add shared resources to sparse-checkout
git sparse-checkout add docs scripts Makefile pyproject.toml .envrc .gitignore CLAUDE.md README.md

# If you need specific additional resources
git sparse-checkout add templates  # For CLI worktree
git sparse-checkout add config     # If needed
```

### Shared Resources Included

Each worktree should include these common resources (~15-20 files):

- **`docs/`** - Documentation for reference (6 files)
- **`scripts/`** - Utility scripts like validators and checkers (10 files)
- **`scratch/`** - Temporary workspace (gitignored, won't count toward file limit)
- **`.gitignore`** - Know what to ignore
- **`.envrc`** - Environment setup
- **`Makefile`** - Common commands (test, lint, etc.)
- **`pyproject.toml`** - Project configuration
- **`README.md`** - Project overview
- **`CLAUDE.md`** - AI context

## Verification

After creating each worktree, verify it's within AI safety limits:

```bash
# Navigate to worktree
cd worktrees/<worktree-name>

# Count files (should be under 30)
echo "File count: $(git ls-files | wc -l)"

# List all files to verify contents
git ls-files | sort

# Verify worktree is registered
git worktree list
```

## Testing Strategy for Worktrees

Genesis uses a distributed testing approach aligned with the worktree structure:

### Test Organization

```
genesis/                          # Main repository
├── tests/                        # Integration & cross-component tests
│   ├── conftest.py              # Root pytest configuration
│   └── test_integration.py      # Cross-component integration tests
├── testing/                      # Shared testing utilities
│   ├── fixtures.py              # Common test fixtures
│   ├── ai_safety.py             # AI safety validation utilities
│   └── helpers.py               # Test helper functions
├── bootstrap/tests/              # Bootstrap component tests
├── smart-commit/tests/           # Smart commit component tests
├── worktree-tools/tests/         # Worktree tools component tests
├── genesis/core/tests/           # Core module tests
└── Makefile                     # Test orchestration
```

### Test Commands by Context

**In Main Repository** (orchestration):
```bash
make test           # Run all tests across all components
make test-unit      # Run only unit tests
make test-integration # Run only integration tests
make test-component bootstrap # Run specific component tests
```

**In Worktrees** (focused development):
```bash
# In test-fixes worktree
pytest testing/tests/ -v               # Test infrastructure
pytest tests/test_integration.py -v    # Cross-component tests

# In component-fixes worktree (e.g., bootstrap focus)
pytest bootstrap/tests/ -v             # Test only bootstrap component
pytest bootstrap/tests/test_bootstrap.py::TestSpecific -v # Specific test

# In core-genesis worktree
pytest genesis/core/tests/ -v          # Test core modules
```

### Test Isolation Benefits

1. **Focused Testing**: Each worktree can run only relevant tests
2. **Fast Feedback**: No need to run entire suite for component changes
3. **Parallel Development**: Different developers can test different components
4. **AI Safety**: Test files stay within the 30-file limit per worktree

## Working with Worktrees

### Switching Between Worktrees

```bash
# Go to main repo
cd /path/to/genesis

# Go to specific worktree
cd worktrees/test-fixes
cd worktrees/core-genesis
cd worktrees/component-fixes
cd worktrees/cli-integration
```

### Making Changes

Each worktree works like a normal Git repository:

```bash
# Make changes
vim some-file.py

# Stage and commit (commits to the worktree's branch)
git add .
git commit -m "Fix issue in component"

# Push to remote (creates branch if needed)
git push -u origin sparse-test-fixes
```

### Synchronizing with Main

```bash
# Pull latest changes from main
git fetch origin main
git merge origin/main

# Or rebase your changes
git rebase origin/main
```

### Creating Pull Requests

Each worktree branch can be used to create PRs:

```bash
# From within a worktree
gh pr create --title "Fix test suite configuration" --base main
```

## Management Commands

### List All Worktrees

```bash
# From main repo or any worktree
git worktree list
```

### Remove a Worktree

```bash
# From main repo
git worktree remove worktrees/<worktree-name>

# Or from within the worktree
git worktree remove .
```

### Prune Deleted Worktrees

```bash
# Clean up references to deleted worktrees
git worktree prune
```

## Best Practices

### File Count Management

- **Target**: Keep each worktree under 30 files
- **Monitor**: Run `git ls-files | wc -l` regularly
- **Adjust**: Use `git sparse-checkout set` to add/remove paths as needed

### Branch Naming

- Use descriptive branch names: `sparse-test-fixes`, `sparse-cli-integration`
- Include `sparse-` prefix to identify worktree branches

### Shared Resource Strategy

- **Always include** docs/, scripts/, config files
- **Selectively include** templates/, terraform/ based on needs
- **Never include** build artifacts, caches, or generated files

### Workflow Tips

1. **Start small**: Create worktree with minimal files, add more as needed
2. **Stay focused**: Resist adding unrelated directories
3. **Use scratch/**: For temporary files that don't count toward limits
4. **Regular cleanup**: Remove worktrees when done with tasks

## Troubleshooting

### Main Repository Setup Issues

**Dependencies not installed:**
```bash
# Install dependencies properly
make setup
# Or manually with Poetry
poetry install --with dev,test
```

**Tests failing in main:**
```bash
# Check test output
make test
# Run specific failing tests
pytest tests/test_failing.py -v
# Fix issues before creating worktrees
```

**Quality gates failing:**
```bash
# Run formatters
make format
# Run linters
make lint
# Check and fix issues before proceeding
```

### Worktree Creation Fails

```bash
# Check if worktree already exists
git worktree list

# Remove existing worktree if needed
git worktree remove worktrees/<name> --force
```

### Too Many Files

```bash
# Check what's taking up space
git ls-files | head -20

# Remove unnecessary paths
git sparse-checkout set path1 path2 path3

# Or start over with more specific focus
git sparse-checkout set specific-directory
```

### Missing Shared Resources

```bash
# Add them after creation
git sparse-checkout add docs scripts Makefile pyproject.toml .envrc
```

## Complete Workflow Example

Here's a full example of creating a worktree, making changes, and submitting a PR:

```bash
# 1. Create focused worktree for authentication work
./worktree-tools/src/create-sparse-worktree.sh auth-fixes genesis/core/auth.py --max-files 25

# 2. Navigate to the worktree
cd worktrees/auth-fixes

# 3. Verify file count and contents
echo "File count: $(git ls-files | wc -l)"
git ls-files | sort

# 4. Make your changes
vim genesis/core/auth.py

# 5. Run tests (within the worktree context)
make test

# 6. Create a quality commit
git add .
git commit -m "fix: improve authentication error handling"

# 7. Push and create PR
git push -u origin sparse-auth-fixes
gh pr create --title "Fix authentication error handling" --base main

# 8. When done, clean up
cd ../..
git worktree remove worktrees/auth-fixes
```

## Current Status (Genesis Project)

Genesis uses the worktree system for development but currently has no active worktrees:

- **Main repository**: 211 files (too large for direct AI work)
- **Available worktrees**: None currently active
- **Worktree tool**: ✅ Ready for use at `worktree-tools/src/create-sparse-worktree.sh`
- **Target file limits**: 25-30 files per worktree for optimal AI safety

## Key Learnings

### What the Tool Does Automatically

The `create-sparse-worktree.sh` tool is smarter than expected:

1. **Automatic file limiting**: When file count exceeds the limit, it automatically applies restrictions
2. **Shared resources included**: Automatically includes essential files like docs/, scripts/, Makefile, pyproject.toml, .envrc, etc.
3. **Smart focus**: For single files (like `genesis/cli.py`), it includes the entire parent directory
4. **Branch management**: Creates branches with `sparse-` prefix automatically

### No Manual Configuration Needed

**You don't need to manually add shared resources** - the tool includes them automatically. The documentation above about manually adding shared resources is only needed if you want to add additional paths later.

### Simplified Creation Commands

The actual commands that work are exactly as documented:

```bash
# These commands create complete, ready-to-use worktrees:
./worktree-tools/src/create-sparse-worktree.sh test-fixes testing/ --max-files 25
./worktree-tools/src/create-sparse-worktree.sh core-genesis genesis/core --max-files 25
./worktree-tools/src/create-sparse-worktree.sh component-fixes bootstrap/ --max-files 25
./worktree-tools/src/create-sparse-worktree.sh cli-integration genesis/cli.py --max-files 25
```

### File Count Reality

The actual file counts are:
- **Much lower than main repo**: Main has 211 files, worktrees have 21-47 files
- **Includes everything needed**: docs/, scripts/, configs, plus focused area
- **Ready to work**: No additional setup required

### Best Approach

1. **Use the tool as designed** - it handles shared resources automatically
2. **Trust the file limits** - the tool enforces them properly
3. **Start working immediately** - worktrees are ready after creation
4. **Monitor with**: `find . -type f -name ".git" -prune -o -type f -print | wc -l`
