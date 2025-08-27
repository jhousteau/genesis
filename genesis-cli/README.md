# Genesis CLI - Main Command-Line Interface

The unified command-line interface for the Genesis development toolkit. Provides a single entry point for all Genesis functionality.

## Features

**Core Commands:**
- ✅ Project bootstrapping with templates
- ✅ AI-safe sparse worktree creation  
- ✅ Smart commits with quality gates
- ✅ Project health monitoring
- ✅ Component synchronization
- ✅ Workspace cleanup

**Built on Existing Components:**
- Wraps `bootstrap.sh` for project creation
- Wraps `create-sparse-worktree.sh` for safe worktrees
- Wraps `smart-commit.sh` for quality-gated commits
- Integrates with all Genesis components

## Commands

### `genesis bootstrap <name>`
Create new project with Genesis patterns and tooling.

```bash
# Create Python API project
genesis bootstrap my-api --type python-api

# Create TypeScript service  
genesis bootstrap my-service --type typescript-service

# Create CLI tool without Git
genesis bootstrap my-cli --type cli-tool --skip-git

# Create in specific directory
genesis bootstrap my-project --path ~/projects/
```

### `genesis worktree <name> <path>`
Create AI-safe sparse worktree with file limits.

```bash
# Create worktree focused on specific file
genesis worktree fix-auth src/auth/login.py

# Create worktree for directory with custom limits
genesis worktree update-tests tests/ --max-files 25

# Create with safety verification
genesis worktree refactor-cli cli/ --verify
```

### `genesis commit`
Smart commit with quality gates and pre-commit hooks.

```bash
# Interactive smart commit
genesis commit

# Commit with message (still runs quality checks)
genesis commit -m "feat: add new feature"
```

### `genesis status`
Check Genesis project health and component status.

```bash
# Basic health check
genesis status

# Detailed status with component info
genesis status --verbose
```

### `genesis sync`
Update shared components and dependencies.

```bash
# Update all shared components
genesis sync
```

### `genesis clean`
Clean workspace: remove old worktrees and build artifacts.

```bash
# Clean everything
genesis clean

# Clean only worktrees
genesis clean --worktrees

# Clean only build artifacts
genesis clean --artifacts
```

## Installation

### From Source (Development)
```bash
cd genesis-cli/
pip install -e .

# Now `genesis` command is available
genesis --help
```

### Requirements
- Python 3.11+
- Click framework
- Must be run from within a Genesis project (detects via CLAUDE.md)

## Usage Requirements

The CLI automatically detects Genesis projects by looking for `CLAUDE.md` in the current directory or parent directories. All commands require being run from within a Genesis project.

```bash
# Check if you're in a Genesis project
genesis status
```

## Component Integration

The CLI integrates with all Genesis components:

- **bootstrap/**: Project initialization via `genesis bootstrap`
- **smart-commit/**: Quality gates via `genesis commit`  
- **worktree-tools/**: Sparse worktrees via `genesis worktree`
- **shared-python/**: Dependency management via `genesis sync`

## Development (AI-Safe Sparse Worktree)

```bash
# Work on CLI component in isolation
git worktree add ../genesis-cli-work feature/cli-improvements
cd ../genesis-cli-work
git sparse-checkout set genesis-cli/

# Component has <10 files for AI safety:
# genesis-cli/
# ├── README.md
# ├── setup.py
# ├── src/
# │   ├── __init__.py
# │   └── genesis.py          # ~280 lines
# └── tests/
#     └── test_cli.py
```

## Testing

```bash
# Run CLI tests
cd genesis-cli/
pytest tests/ -v

# Test CLI functionality
genesis --help
genesis status
```

## Error Handling

The CLI provides clear error messages for common issues:

- **Not in Genesis project**: `❌ Not in a Genesis project. Run from Genesis directory.`
- **Missing components**: `❌ Smart-commit script not found. Genesis may be incomplete.`
- **Command failures**: `❌ Bootstrap failed: <error details>`

All errors exit with non-zero status codes for proper script integration.

## Configuration

No additional configuration required. The CLI:
- Auto-detects Genesis project root via `CLAUDE.md`
- Locates component scripts automatically
- Uses existing Genesis configuration and patterns
- Integrates with existing quality gates and CI/CD