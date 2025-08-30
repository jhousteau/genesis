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

- **Main workspace is protected**: AI assistants cannot work directly in main (259 files)
- **Automatic detection**: `.envrc` detects AI tools and blocks them with helpful message
- **Worktree bypass**: Worktrees include `.ai-safety-manifest` that allows AI work
- **Human-friendly**: Humans can work normally in main workspace
- **Educational**: Block message explains the issue and shows worktree creation commands

When an AI assistant tries to work in main, they see:
```
🤖 AI SAFETY PROTECTION ACTIVE
❌ AI assistants cannot work directly in the main workspace
Why: Main workspace has 259 files - too many for AI context
✅ Solution: Create a focused worktree for your specific task
```

## Worktree Structure

After creation, your directory structure will look like:

```
genesis/                       # Main repository (259 files)
├── .git/                     # Git repository data
├── worktrees/                # All sparse worktrees (empty, ready for creation)
├── genesis/                  # Core Python package with CLI and utilities
├── templates/                # 4 complete project templates
├── bootstrap/                # Project initialization system
├── smart-commit/             # Quality gates and pre-commit automation
├── worktree-tools/           # AI-safe sparse worktree creation tools
├── shared-python/            # Reusable Python utilities
├── shared-typescript/        # TypeScript utilities
├── terraform/                # Infrastructure modules
├── scripts/                  # Validation and automation utilities
├── testing/                  # Testing infrastructure
└── docs/                     # Documentation
```

## Genesis CLI Worktree Commands

Genesis provides a unified CLI interface for all worktree operations:

```bash
# Create AI-safe worktree
genesis worktree create test-fixes testing/ --max-files 25

# List all worktrees
genesis worktree list

# Remove worktree
genesis worktree remove test-fixes

# Show worktree information
genesis worktree info test-fixes
```

The Genesis CLI handles all the complexity of sparse worktrees, file limits, and AI safety automatically.

## Creating Worktrees

### 1. Testing Infrastructure Worktree

**Purpose**: Work on pytest configuration, test infrastructure, and cross-component testing

```bash
genesis worktree create test-infra testing/ --max-files 25
```

**Contains**:
- `testing/` directory - Core testing utilities and fixtures
- `tests/conftest.py` - Root pytest configuration
- `tests/test_integration.py` - Cross-component integration tests
- `Makefile` - Test orchestration commands
- Shared resources (see below)

**Test Strategy**: This worktree focuses on the testing infrastructure that supports all components. Component-specific tests remain with their components for isolated development.

### 2. Genesis Core Worktree

**Purpose**: Work on Genesis core modules and utilities (autofix, errors, config, etc.)

```bash
genesis worktree create genesis-core genesis/core --max-files 25
```

**Contains**:
- `genesis/core/` directory
- Related test files
- Shared resources (see below)

### 3. Bootstrap Component Worktree

**Purpose**: Work on the bootstrap project initialization system

```bash
genesis worktree create bootstrap-work bootstrap/ --max-files 25
```

**Contains**:
- One component directory at a time (e.g., `bootstrap/`)
- Component's tests (`bootstrap/tests/`)
- Component's documentation (`bootstrap/README.md`)
- Shared resources (see below)

**Test Strategy**: Each component includes its own tests for isolated development. Run `pytest bootstrap/tests/` within the worktree to test only that component.

### 4. Templates Worktree

**Purpose**: Work on project templates (Python API, CLI tool, TypeScript service, Terraform)

```bash
genesis worktree create template-work templates/ --max-files 25
```

**Contains**:
- `templates/` directory with all 4 project templates
- Template-specific tests and validation
- Bootstrap integration files
- Shared resources (see below)

## Adding Shared Resources

After creating any worktree, add shared resources that all worktrees need:

```bash
# Navigate to the worktree
cd worktrees/<worktree-name>

# Add shared resources to sparse-checkout (if needed)
git sparse-checkout add docs scripts Makefile pyproject.toml .envrc .gitignore CLAUDE.md README.md

# Add specific additional resources as needed
git sparse-checkout add config     # Configuration files
git sparse-checkout add terraform  # For infrastructure work
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
# In test-infra worktree
pytest testing/tests/ -v               # Test infrastructure
pytest testing/tests/test_integration.py -v    # Cross-component tests

# In bootstrap-work worktree
pytest bootstrap/tests/ -v             # Test only bootstrap component
pytest bootstrap/tests/test_bootstrap.py::TestSpecific -v # Specific test

# In genesis-core worktree
pytest genesis/tests/ -v          # Test core modules
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
cd worktrees/test-infra
cd worktrees/genesis-core
cd worktrees/bootstrap-work
cd worktrees/template-work
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
# List Genesis worktrees
genesis worktree list

# List all worktrees (including non-Genesis)
genesis worktree list --all
```

### Remove a Worktree

```bash
# Remove worktree by name
genesis worktree remove <worktree-name>

# Force removal even with uncommitted changes
genesis worktree remove <worktree-name> --force
```

### Get Worktree Information

```bash
# Show detailed information about a worktree
genesis worktree info <worktree-name>
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
genesis worktree list

# Remove existing worktree if needed
genesis worktree remove <name> --force
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
# 1. Create focused worktree for bootstrap component work
genesis worktree create bootstrap-fixes bootstrap/ --max-files 25

# 2. Navigate to the worktree
cd worktrees/bootstrap-fixes

# 3. Verify file count and contents
echo "File count: $(git ls-files | wc -l)"
git ls-files | sort

# 4. Make your changes
vim bootstrap/src/bootstrap.sh

# 5. Run tests (within the worktree context)
make test-component COMPONENT=bootstrap

# 6. Create a quality commit
git add .
git commit -m "fix: improve bootstrap template generation"

# 7. Push and create PR
git push -u origin sparse-bootstrap-fixes
gh pr create --title "Fix bootstrap template generation" --base main

# 8. When done, clean up
cd ../..
git worktree remove worktrees/bootstrap-fixes
```

## Current Status (Genesis Project)

Genesis uses the worktree system for development but currently has no active worktrees:

- **Main repository**: 259 files (too large for direct AI work)
- **Available worktrees**: None currently active
- **Worktree tools**: ✅ Ready for use
  - Genesis CLI: `genesis worktree create <name> <path> --max-files 25`
  - Direct script: `worktree-tools/src/create-sparse-worktree.sh`
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
genesis worktree create test-infra testing/ --max-files 25
genesis worktree create genesis-core genesis/core --max-files 25
genesis worktree create bootstrap-work bootstrap/ --max-files 25
genesis worktree create template-work templates/ --max-files 25
```

### File Count Reality

The actual file counts are:
- **Much lower than main repo**: Main has 259 files, worktrees have 21-47 files
- **Includes everything needed**: docs/, scripts/, configs, plus focused area
- **Ready to work**: No additional setup required

### Best Approach

1. **Use the tool as designed** - it handles shared resources automatically
2. **Trust the file limits** - the tool enforces them properly
3. **Start working immediately** - worktrees are ready after creation
4. **Monitor with**: `find . -type f -name ".git" -prune -o -type f -print | wc -l`

## AI Safety Enforcement

Genesis implements strict AI safety measures to prevent context overflow and ensure secure development:

### Environment-Based Detection
The `.envrc` file automatically detects AI assistants and applies appropriate restrictions:

```bash
# AI Safety configuration in .envrc
export AI_MAX_FILES=30
export AI_SAFETY_MODE="enforced"
export MAX_PROJECT_FILES=1000
```

### Automatic File Limits
- **Main workspace**: 259 files (blocked for AI assistants)
- **Worktrees**: Auto-limited to 25-30 files
- **Components**: Each kept under 30 files for AI safety

### Safety Validation Scripts
Genesis includes validation utilities:

```bash
# Check AI safety compliance
scripts/validate-components.sh

# Verify file counts
make file-check

# Generate AI safety report
make ai-safety-report
```

### Genesis CLI Integration

The Genesis CLI provides comprehensive worktree management:

```bash
# Create AI-safe worktree
genesis worktree create my-feature src/feature.py --max-files 25

# List all worktrees
genesis worktree list

# Check worktree status
genesis worktree status

# Clean up old worktrees
genesis clean --worktrees

# View project health
genesis status --verbose
```
