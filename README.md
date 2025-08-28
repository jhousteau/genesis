# Genesis

Modern, AI-safe development toolkit with sparse worktree isolation.

## Quick Start

```bash
# Clone and setup
git clone <repo-url> genesis
cd genesis

# Create your first workspace
git worktree add ../genesis-cli feature/cli
cd ../genesis-cli
git sparse-checkout init --cone
git sparse-checkout set genesis_cli/ pyproject.toml

# Now you have 21 files instead of 3000+
find . -type f | wc -l  # Returns: 21
```

## What Genesis Does

**Problem**: AI tools see ALL 3000+ files → accidental modifications, security risks, slow responses

**Solution**: Sparse worktrees expose only 5-30 files per task → safe, fast, focused development

## Core Components

1. **Genesis CLI** (`genesis_cli/`) - Project management commands
2. **Smart Commit** (`shared-infra/smart-commit/`) - Quality gates before commits
3. **Bootstrap** (`shared-infra/bootstrap/`) - Automated project setup
4. **Shared Libraries** (`shared-infra/libs/`) - Reusable Python/TypeScript utilities

## Installation

```bash
# Install Genesis CLI
pip install -e .

# Verify installation
genesis --help
```

## Basic Usage

```bash
# Bootstrap new project
genesis bootstrap my-project --template python-api

# Create focused workspace
genesis worktree create feature/auth --files src/auth.py tests/test_auth.py

# Smart commit with quality gates
cd shared-infra/smart-commit
poetry run smart-commit "feat: add authentication"

# Run tests
pytest tests/ -v
```

## Project Structure

```
genesis/
├── genesis_cli/           # Command-line interface
├── shared-infra/          # Shared components
│   ├── bootstrap/         # Project setup automation
│   ├── smart-commit/      # Quality gate system
│   ├── libs/python/       # Python utilities
│   └── libs/typescript/   # TypeScript utilities
├── tests/                 # Test suite
└── templates/             # Project templates
```

## Development Workflow

1. **Create sparse worktree** for your task (5-30 files only)
2. **Make changes** in isolated environment
3. **Run tests** to verify correctness
4. **Smart commit** with quality gates
5. **Merge** to main after review

## Safety First

- **Never give AI access** to the main repository (3000+ files)
- **Always work in sparse worktrees** (5-30 files max)
- **Review all changes** before merging
- **Use smart-commit** to enforce quality

## Contributing

1. Read [GENESIS.md](GENESIS.md) for architecture details
2. Read [SAFETY.md](SAFETY.md) for AI and Git safety rules
3. Create sparse worktree for your feature
4. Follow test-driven development
5. Use smart-commit for all changes

## Links

- **Architecture & Components**: [GENESIS.md](GENESIS.md)
- **AI & Git Safety Rules**: [SAFETY.md](SAFETY.md)
- **Templates**: [templates/](templates/)
- **Old Code Analysis**: [OLD_CODE_ANALYSIS.md](OLD_CODE_ANALYSIS.md)
