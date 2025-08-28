# AutoFix System

Multi-stage convergent code fixing with formatters, linters, and quality gates.

## Quick Start

```python
from genesis.core.autofix import AutoFixer

# Run all stages with convergent fixing
fixer = AutoFixer()
result = fixer.run()

# Run specific stage only
result = fixer.run_stage_only(['formatter'])
```

## Stages

### Stage 1: Formatters
- **Black**: Python code formatting
- **Prettier**: TypeScript/JavaScript formatting
- **isort**: Python import sorting

### Stage 2: Linters
- **Ruff**: Fast Python linter with auto-fixing
- **ESLint**: TypeScript/JavaScript linting

### Stage 3: Convergent Fixing
- Runs stages repeatedly until code stabilizes
- Maximum 10 iterations to prevent infinite loops
- Detects when no more changes are made

## Configuration

AutoFixer respects standard configuration files:
- `.ruff.toml` / `pyproject.toml` for Ruff
- `.prettierrc` for Prettier
- `.eslintrc` for ESLint
- `pyproject.toml` for Black and isort

## Integration

- Used by `genesis commit` for quality gates
- Integrated with CI/CD pipelines
- Available as standalone `genesis fix` command
- Works with `.gitignore` to avoid fixing generated files
