# Worktree Tools

AI-safe sparse worktree creation and management tools.

## Usage

```bash
# Create AI-safe worktree with file limits
./src/create-sparse-worktree.sh fix-auth src/auth.py --max-files 30
```

## Features

- File count enforcement (<30 files per worktree)
- Safety manifest creation
- Automatic contamination detection  
- Directory depth limits
- Focus path validation

## Development

```bash
# Work on this component in isolation (AI-safe)
git worktree add ../worktree-work feature/worktree-work
cd ../worktree-work
git sparse-checkout set worktree-tools/
```

## Files

- `src/create-sparse-worktree.sh` - Main script (~150 lines)
- `tests/` - Worktree tests
- Target: <10 files total for AI safety