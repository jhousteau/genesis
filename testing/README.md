# Testing Infrastructure - Comprehensive pytest Framework

Shared testing utilities, fixtures, and framework for all Genesis components. Provides comprehensive testing capabilities including AI safety validation, component integration testing, and end-to-end workflow validation.

## Features

**Core Testing Capabilities:**
- ✅ Comprehensive pytest configuration with coverage reporting
- ✅ Shared fixtures for all Genesis components
- ✅ AI safety validation and file count enforcement
- ✅ Mock utilities for git operations, filesystem, and shell commands
- ✅ Integration testing across component boundaries
- ✅ End-to-end workflow testing
- ✅ Component isolation validation

**Test Organization:**
- **Unit tests**: Individual component functionality
- **Integration tests**: Cross-component communication
- **E2E tests**: Complete Genesis workflows
- **AI Safety tests**: File count limits and isolation validation

## Contents

### `fixtures/` - Test Fixtures and Mocks
- `mock_git.py` - Git operation mocking with configurable responses
- `mock_filesystem.py` - Filesystem operations and project structure creation
- `mock_commands.py` - Shell command execution mocking
- `__init__.py` - Fixture exports and imports

### `utilities/` - Test Helper Functions
- `ai_safety.py` - AI safety validation, file counting, and reporting
- `__init__.py` - Utility exports

### `tests/` - Infrastructure Tests
- `test_ai_safety.py` - AI safety constraint validation tests
- `test_integration.py` - Cross-component integration tests

### Root Configuration
- `/pytest.ini` - Pytest configuration with coverage and markers
- `/conftest.py` - Root-level shared fixtures and configuration

## Usage Examples

### Basic Component Testing
```python
import pytest
from testing.fixtures import create_genesis_project_structure
from testing.utilities import assert_component_isolation

def test_component_structure(temp_dir):
    fs = create_genesis_project_structure(temp_dir)
    component_path = temp_dir / "bootstrap"
    assert_component_isolation(component_path, max_files=30)
```

### AI Safety Validation
```python
from testing.utilities import AISafetyChecker, print_ai_safety_report

def test_project_ai_safety(genesis_root):
    checker = AISafetyChecker(max_total_files=100, max_component_files=30)
    result = checker.check_project(genesis_root)
    assert result['is_safe']

    # Print detailed report if needed
    if not result['is_safe']:
        print_ai_safety_report(genesis_root)
```

### Mock Git Operations
```python
from testing.fixtures import patch_git_operations

def test_git_workflow():
    with patch_git_operations()[0] as mock_git_patch:
        # Git operations are now mocked
        result = subprocess.run(['git', 'init'])
        assert result.returncode == 0
```

### Integration Testing
```python
@pytest.mark.integration
def test_cli_bootstrap_integration(mock_genesis_project):
    from genesis import cli
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli, ['bootstrap', 'test-project'])
    assert result.exit_code == 0
```

## Test Markers

The framework provides several test markers for organization:

- `@pytest.mark.unit` - Unit tests for individual components
- `@pytest.mark.integration` - Integration tests across components
- `@pytest.mark.e2e` - End-to-end tests for complete workflows
- `@pytest.mark.ai_safety` - Tests for AI safety constraints
- `@pytest.mark.slow` - Tests that take more than 2 seconds
- `@pytest.mark.requires_git` - Tests that need git operations
- `@pytest.mark.requires_network` - Tests that need network access

## Running Tests

### All Tests
```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run only fast tests
pytest -m "not slow"
```

### Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# AI safety tests
pytest -m ai_safety

# End-to-end tests (slow)
pytest -m e2e --run-slow
```

### Component-Specific Tests
```bash
# Test specific component
pytest bootstrap/tests/ -v

# Test CLI component
pytest genesis-cli/tests/ -v

# Test shared utilities
pytest shared-python/tests/ -v
```

### Coverage Reporting
```bash
# Generate HTML coverage report
pytest --cov-report=html

# View coverage report
open coverage/index.html

# Fail if coverage below 80%
pytest --cov-fail-under=80
```

## AI Safety Testing

The testing infrastructure includes comprehensive AI safety validation:

### File Count Validation
```python
# Validate entire project
from testing.utilities import validate_ai_safety_limits
result = validate_ai_safety_limits(project_path, max_files=100)

# Validate component
assert_component_isolation(component_path, max_files=30)

# Check current Genesis project
pytest -m ai_safety
```

### Safety Reports
```python
from testing.utilities import print_ai_safety_report
print_ai_safety_report(genesis_root)
```

Output:
```
🤖 AI Safety Report for /path/to/genesis
==================================================
Total files: 73
✅ SAFE: Within limit of 100 files

Component breakdown:
  ✅ bootstrap: 8 files
  ✅ genesis-cli: 12 files
  ✅ smart-commit: 6 files
  ✅ worktree-tools: 7 files
  ✅ shared-python: 15 files
```

## Development (AI-Safe Sparse Worktree)

```bash
# Work on testing infrastructure in isolation
git worktree add ../testing-work feature/testing-improvements
cd ../testing-work
git sparse-checkout set testing/

# Component has <15 files for AI safety:
# testing/
# ├── README.md
# ├── fixtures/
# │   ├── __init__.py
# │   ├── mock_git.py
# │   ├── mock_filesystem.py
# │   └── mock_commands.py
# ├── utilities/
# │   ├── __init__.py
# │   └── ai_safety.py
# └── tests/
#     ├── test_ai_safety.py
#     └── test_integration.py
```

## Configuration

### pytest.ini Settings
- Test discovery across all components
- Coverage reporting (80% minimum)
- Custom markers and warnings configuration
- Async support enabled

### conftest.py Fixtures
- `genesis_root` - Genesis project root detection
- `temp_dir` - Isolated temporary directories
- `mock_genesis_project` - Complete mock Genesis structure
- `ai_safety_validator` - AI safety constraint checking
- `mock_git` - Git operation mocking
- `mock_shell_commands` - Shell command mocking

## Integration with CI/CD

The testing infrastructure integrates with Genesis CI/CD:

```yaml
# In GitHub Actions
- name: Run Tests
  run: |
    pytest --cov=. --cov-report=xml

- name: AI Safety Check
  run: |
    pytest -m ai_safety --tb=short

- name: Upload Coverage
  uses: codecov/codecov-action@v3
```

## Best Practices

1. **Use appropriate markers** for test categorization
2. **Mock external dependencies** (git, network, filesystem)
3. **Validate AI safety** in integration tests
4. **Test component isolation** and boundaries
5. **Use temp directories** for test isolation
6. **Check coverage regularly** (aim for >80%)
7. **Test error conditions** and edge cases
8. **Include integration tests** for cross-component workflows
