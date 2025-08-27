# Genesis CLI

The main command-line interface for Genesis toolkit.

## Commands

- `genesis bootstrap <name>` - Create new project with templates
- `genesis worktree create` - Create AI-safe sparse worktree  
- `genesis sync` - Update shared components
- `genesis status` - Check project health

## Development

```bash
# Work on this component in isolation (AI-safe)
git worktree add ../genesis-cli-work feature/cli-work
cd ../genesis-cli-work
git sparse-checkout set genesis-cli/
```

## Files

- `src/` - CLI source code
- `tests/` - Component tests
- Target: <20 files total for AI safety