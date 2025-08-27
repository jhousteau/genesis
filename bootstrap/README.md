# Bootstrap

Project initialization system - creates new projects with Genesis patterns.

## Usage

```bash
# Initialize new project
./src/bootstrap.sh my-new-project --type python
./src/bootstrap.sh my-frontend --type typescript
```

## Features

- Template-based project creation
- Multi-language support (Python, TypeScript)
- Git repository initialization
- Dependency installation
- Environment setup

## Development

```bash
# Work on this component in isolation (AI-safe)
git worktree add ../bootstrap-work feature/bootstrap-work
cd ../bootstrap-work
git sparse-checkout set bootstrap/
```

## Files

- `src/bootstrap.sh` - Main script (~150 lines)
- `tests/` - Bootstrap tests
- Target: <15 files total for AI safety