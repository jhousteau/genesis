# Smart Commit

Quality gates before commits - automated linting, testing, and validation.

## Usage

```bash
# Run smart commit (replaces git commit)
./src/smart-commit.sh "Your commit message"
```

## Features

- Pre-commit validation
- Auto-formatting (black, ruff)
- Test execution with continue option
- Secret detection
- Commit message validation

## Development

```bash
# Work on this component in isolation (AI-safe)  
git worktree add ../smart-commit-work feature/commit-work
cd ../smart-commit-work
git sparse-checkout set smart-commit/
```

## Files

- `src/smart-commit.sh` - Main script (~100 lines)
- `tests/` - Test scripts
- Target: <10 files total for AI safety