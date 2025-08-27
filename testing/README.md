# Testing Infrastructure

Shared testing utilities and fixtures for all Genesis components.

## Contents

- `fixtures/` - Common test fixtures and mocks
- `utilities/` - Test helper functions

## Usage

```python
from testing.fixtures import mock_git, temp_project
from testing.utilities import assert_file_count

def test_component(mock_git, temp_project):
    # Test code here
    assert_file_count(temp_project, max_files=30)
```

## Development

```bash
# Work on this component in isolation (AI-safe)
git worktree add ../testing-work feature/testing-work
cd ../testing-work
git sparse-checkout set testing/
```

## Files

- `fixtures/` - Test fixtures
- `utilities/` - Helper functions  
- Target: <15 files total for AI safety