"""Testing fixtures for Genesis components."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from .mock_commands import (
    MockCommandRunner,
    MockScriptEnvironment,
    create_genesis_script_mocks,
    create_mock_shell_commands,
    patch_subprocess_run,
)
from .mock_filesystem import (
    MockFilesystem,
    create_genesis_project_structure,
    create_test_project,
)
from .mock_git import MockGit, create_mock_git, patch_git_operations


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


__all__ = [
    "temp_dir",
    "MockGit",
    "create_mock_git",
    "patch_git_operations",
    "MockFilesystem",
    "create_genesis_project_structure",
    "create_test_project",
    "MockCommandRunner",
    "create_mock_shell_commands",
    "create_genesis_script_mocks",
    "MockScriptEnvironment",
    "patch_subprocess_run",
]
