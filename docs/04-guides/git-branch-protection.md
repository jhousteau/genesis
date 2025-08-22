# Git Branch Protection Guide

## Overview

The Genesis project implements comprehensive git branch protection to prevent accidental direct commits and pushes to the main branch. This ensures all changes go through proper review processes via pull requests.

## Protection Mechanisms

### 1. Pre-commit Hook (Commit Protection)

The pre-commit framework prevents direct commits to the main branch:
- **Location**: Managed by `.pre-commit-config.yaml`
- **Hook**: `no-commit-to-branch` 
- **Protected branches**: `main`, `master`
- **Additional checks**:
  - Secret detection (gitleaks)
  - File validation (YAML, JSON)
  - Code formatting (Black for Python)
  - Terraform validation and formatting
  - TODO/FIXME/HACK detection
  - Large file detection
  - Private key detection

### 2. Pre-push Hook (Push Protection)

A custom hook prevents direct pushes to protected branches:
- **Location**: `.git/hooks/pre-push`
- **Protected branches**: `main`, `master`
- **Provides**: Clear error messages with workflow guidance

## Setup Instructions

### Initial Installation

1. **Install pre-commit framework** (if not already installed):
   ```bash
   pip install pre-commit
   ```

2. **Install the hooks**:
   ```bash
   pre-commit install
   ```

3. **Verify installation**:
   ```bash
   ls -la .git/hooks/ | grep -E "pre-commit|pre-push"
   ```

### For New Contributors

When cloning the repository, run:
```bash
pre-commit install
```

## Workflow

### Correct Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and commit**:
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

3. **Push your feature branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create a Pull Request**:
   - Use GitHub's web interface or CLI
   - Get reviews and approval
   - Merge via GitHub

### What Happens If You Try to Commit to Main?

```bash
$ git commit -m "test commit"
Protect main branch......................................................Failed
- hook id: no-commit-to-branch
- exit code: 1
```

The commit will be blocked with a clear error message.

### What Happens If You Try to Push to Main?

```bash
$ git push origin main
❌ ERROR: Direct push to protected branch 'main' is not allowed!

To merge changes to 'main':
1. Push your feature branch: git push origin feature/your-feature-name
2. Create a pull request on GitHub
3. Get the PR reviewed and approved
4. Merge via GitHub's interface

To bypass in emergencies only: git push --no-verify
```

## Emergency Override

**⚠️ Use only in critical situations:**

### Bypass commit protection:
```bash
SKIP=no-commit-to-branch git commit -m "emergency fix"
```

### Bypass push protection:
```bash
git push --no-verify
```

**Note**: Emergency overrides should be rare and require justification.

## Integration with Smart-Commit

The smart-commit system (`setup-project/templates/plumbing/smart-commit.sh`) works seamlessly with these protections:
- Pre-commit hooks run automatically during smart-commit
- Branch protection rules are enforced
- Additional quality gates are applied

## Troubleshooting

### Pre-commit not found
```bash
pip install pre-commit
pre-commit install
```

### Hooks not running
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
```

### Update pre-commit hooks
```bash
pre-commit autoupdate
```

### Run hooks manually
```bash
# Run on all files
pre-commit run --all-files

# Run on staged files
pre-commit run
```

## Additional Resources

- [Pre-commit documentation](https://pre-commit.com/)
- [GitHub Pull Request workflow](https://docs.github.com/en/pull-requests)
- Project smart-commit guide: `setup-project/templates/plumbing/smart-commit.sh`