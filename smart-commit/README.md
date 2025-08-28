# Smart Commit System

Extracted and simplified quality gates system from old Genesis codebase. Provides automated validation before commits with essential quality gates.

## Features

**Core Quality Gates:**
- ✅ Pre-commit hook validation (if .pre-commit-config.yaml exists)
- ✅ Test execution with continue option (pytest or make test)
- ✅ Linting with auto-fix (ruff, black)
- ✅ Basic secret detection (API keys, tokens)
- ✅ Commit message validation (length, format)
- ✅ Interactive commit type selection

**Simplifications from Original (225→93 lines):**
- Removed over-complex user interaction
- Streamlined error handling
- Simplified command detection
- Focused on core functionality
- Maintained all essential quality gates

## Usage

```bash
# Run smart commit (interactive)
./src/smart-commit.sh

# The script will guide you through:
# 1. Pre-commit checks (if configured)
# 2. Running tests (with continue option)
# 3. Code linting and auto-formatting
# 4. Secret scanning
# 5. Commit type selection
# 6. Message validation
# 7. Final confirmation and commit
```

## Integration with Genesis Workflow

Works seamlessly with Genesis development patterns:
- Integrates with `.pre-commit-config.yaml` (branch protection)
- Respects Makefile test targets
- Compatible with sparse worktree usage (<30 files)
- Follows conventional commit format

## Development (AI-Safe Sparse Worktree)

```bash
# Work on smart-commit in isolation
git worktree add ../smart-commit-work feature/smart-commit-fixes
cd ../smart-commit-work
git sparse-checkout set smart-commit/

# Component has <10 files for AI safety:
# smart-commit/
# ├── README.md
# ├── src/smart-commit.sh      # 93 lines
# └── tests/test_smart_commit.py
```

## Testing

```bash
# Run component tests
pytest smart-commit/tests/ -v

# Test smart-commit functionality
cd smart-commit/
./src/smart-commit.sh  # Interactive test
```

## Configuration

The script automatically detects and uses:
- `.pre-commit-config.yaml` - Pre-commit hooks
- `pytest` or `make test` - Test runners
- `ruff`, `black` - Code linters/formatters
- Git configuration - For commit creation

No additional configuration required - works out of the box with Genesis patterns.
