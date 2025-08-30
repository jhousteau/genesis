# Shared Python Libraries

Reusable Python utilities for all Genesis components and projects.

## Modules

- `retry.py` - Exponential backoff retry decorator (~50 lines)
- `logger.py` - Structured JSON logging (~40 lines)
- `config.py` - YAML + env configuration (~50 lines)
- `health.py` - Simple health checks (~30 lines)

## Usage

```python
from shared_core import retry, logger, config, health

@retry.with_backoff()
def api_call():
    pass

log = logger.get_logger(__name__)
```

## Development

```bash
# Work on this component in isolation (AI-safe)
git worktree add ../shared-python-work feature/python-work
cd ../shared-python-work
git sparse-checkout set shared-python/
```

## Files

- `src/shared_core/` - Library modules
- `tests/` - Unit tests
- Target: <20 files total for AI safety
