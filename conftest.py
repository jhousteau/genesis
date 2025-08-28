"""Genesis Testing Infrastructure - Root conftest.py

Shared fixtures and configuration for all Genesis component tests.
Provides common testing utilities, mocks, and AI safety validation.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any
import pytest
import subprocess
from unittest.mock import Mock, patch

# Test markers
pytest_plugins = []


@pytest.fixture(scope="session")
def genesis_root() -> Path:
    """Get Genesis project root directory."""
    current = Path(__file__).parent
    return current


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_genesis_project(temp_dir: Path) -> Path:
    """Create mock Genesis project structure for testing."""
    project_dir = temp_dir / "mock-genesis"
    project_dir.mkdir()

    # Create CLAUDE.md to mark as Genesis project
    (project_dir / "CLAUDE.md").write_text("# Mock Genesis Project")

    # Create component directories
    components = [
        "bootstrap",
        "genesis-cli",
        "smart-commit",
        "worktree-tools",
        "shared-python",
    ]
    for component in components:
        comp_dir = project_dir / component
        comp_dir.mkdir()
        (comp_dir / "README.md").write_text(f"# {component}")

        # Create src and tests directories
        (comp_dir / "src").mkdir()
        (comp_dir / "tests").mkdir()

    return project_dir


@pytest.fixture
def mock_git():
    """Mock git operations to avoid actual git calls in tests."""
    with patch("subprocess.run") as mock_run:
        # Default successful git response
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def mock_shell_commands():
    """Mock shell command execution for testing scripts."""
    commands = {}

    def mock_run(cmd, **kwargs):
        """Mock subprocess.run with configurable responses."""
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd

        # Default response
        result = Mock()
        result.returncode = commands.get(cmd_str, {}).get("returncode", 0)
        result.stdout = commands.get(cmd_str, {}).get("stdout", "")
        result.stderr = commands.get(cmd_str, {}).get("stderr", "")
        return result

    with patch("subprocess.run", side_effect=mock_run):
        yield commands


@pytest.fixture
def ai_safety_validator():
    """Fixture for validating AI safety constraints."""

    class AISafetyValidator:
        def __init__(self):
            self.max_files = 100
            self.max_component_files = 30

        def validate_file_count(
            self, path: Path, max_files: int = None
        ) -> Dict[str, Any]:
            """Validate file count for AI safety."""
            if max_files is None:
                max_files = self.max_files

            files = list(path.rglob("*"))
            file_count = len([f for f in files if f.is_file()])

            return {
                "file_count": file_count,
                "max_files": max_files,
                "is_safe": file_count <= max_files,
                "files": [f.relative_to(path) for f in files if f.is_file()],
            }

        def validate_component_isolation(self, component_path: Path) -> Dict[str, Any]:
            """Validate component has proper isolation."""
            files = list(component_path.rglob("*"))
            file_count = len([f for f in files if f.is_file()])

            has_readme = (component_path / "README.md").exists()
            has_src = (component_path / "src").exists()
            has_tests = (component_path / "tests").exists()

            return {
                "file_count": file_count,
                "max_component_files": self.max_component_files,
                "is_safe": file_count <= self.max_component_files,
                "has_readme": has_readme,
                "has_src": has_src,
                "has_tests": has_tests,
                "proper_structure": has_readme and has_src and has_tests,
            }

    return AISafetyValidator()


@pytest.fixture
def sample_project_files(temp_dir: Path) -> Path:
    """Create sample project files for testing bootstrap functionality."""
    project = temp_dir / "sample-project"
    project.mkdir()

    # Python API structure
    (project / "src").mkdir()
    (project / "tests").mkdir()
    (project / "docs").mkdir()

    # Sample files
    (project / "pyproject.toml").write_text(
        """
[tool.poetry]
name = "sample-project"
version = "0.1.0"
"""
    )

    (project / "README.md").write_text("# Sample Project")
    (project / "Makefile").write_text("help:\n\techo 'Help'")
    (project / ".gitignore").write_text("*.pyc\n__pycache__/")

    return project


@pytest.fixture
def mock_worktree_environment(temp_dir: Path, mock_git):
    """Create mock environment for testing worktree operations."""
    # Main repo
    main_repo = temp_dir / "main-repo"
    main_repo.mkdir()
    (main_repo / ".git").mkdir()
    (main_repo / "CLAUDE.md").write_text("# Genesis Project")

    # Source structure
    src_dir = main_repo / "src"
    src_dir.mkdir()
    (src_dir / "auth").mkdir()
    (src_dir / "auth" / "login.py").write_text("# Login module")

    tests_dir = main_repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_auth.py").write_text("# Auth tests")

    # Worktrees directory
    worktrees_dir = temp_dir / "worktrees"
    worktrees_dir.mkdir()

    return {
        "main_repo": main_repo,
        "worktrees_dir": worktrees_dir,
        "src_dir": src_dir,
        "tests_dir": tests_dir,
    }


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean up environment variables and state between tests."""
    # Store original environment
    original_env = os.environ.copy()
    original_cwd = os.getcwd()

    yield

    # Restore environment
    os.environ.clear()
    os.environ.update(original_env)
    os.chdir(original_cwd)


@pytest.fixture
def capture_subprocess():
    """Capture subprocess calls for verification in tests."""
    captured_calls = []

    def mock_run(*args, **kwargs):
        captured_calls.append((args, kwargs))
        result = Mock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with patch("subprocess.run", side_effect=mock_run):
        yield captured_calls


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test items during collection."""
    # Add slow marker to tests that might be slow
    for item in items:
        if "integration" in item.keywords or "e2e" in item.keywords:
            item.add_marker(pytest.mark.slow)

        # Add requires_git marker for tests that use git
        if hasattr(item, "fixturenames") and "mock_git" in item.fixturenames:
            item.add_marker(pytest.mark.requires_git)


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line(
        "markers", "integration: Integration tests across components"
    )
    config.addinivalue_line("markers", "e2e: End-to-end tests for complete workflows")
    config.addinivalue_line("markers", "ai_safety: Tests for AI safety constraints")
    config.addinivalue_line("markers", "slow: Tests that take more than 2 seconds")
    config.addinivalue_line("markers", "requires_git: Tests that need git operations")
    config.addinivalue_line(
        "markers", "requires_network: Tests that need network access"
    )


def pytest_runtest_setup(item):
    """Setup before each test runs."""
    # Skip network tests unless explicitly enabled
    if "requires_network" in item.keywords and not item.config.getoption(
        "--run-network"
    ):
        pytest.skip("Network tests disabled (use --run-network to enable)")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="Run tests that require network access",
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests (integration and e2e)",
    )
