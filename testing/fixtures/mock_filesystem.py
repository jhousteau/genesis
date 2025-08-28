"""Filesystem mocks and utilities for testing."""

import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import os


class MockFilesystem:
    """Mock filesystem operations for testing."""

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            self.temp_dir = tempfile.mkdtemp()
            self.base_path = Path(self.temp_dir)
        else:
            self.base_path = base_path
            self.temp_dir = None

        self.created_files = []
        self.created_dirs = []

    def create_file(self, relative_path: str, content: str = "") -> Path:
        """Create a file with given content."""
        file_path = self.base_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        self.created_files.append(file_path)
        return file_path

    def create_directory(self, relative_path: str) -> Path:
        """Create a directory."""
        dir_path = self.base_path / relative_path
        dir_path.mkdir(parents=True, exist_ok=True)
        self.created_dirs.append(dir_path)
        return dir_path

    def create_structure(self, structure: Dict[str, Any]) -> None:
        """Create filesystem structure from nested dict.

        Example:
        {
            'src': {
                'main.py': 'print("hello")',
                'utils': {
                    'helpers.py': 'def help(): pass'
                }
            },
            'README.md': '# Project'
        }
        """
        self._create_structure_recursive(structure, self.base_path)

    def _create_structure_recursive(
        self, structure: Dict[str, Any], base: Path
    ) -> None:
        """Recursively create structure."""
        for name, content in structure.items():
            path = base / name

            if isinstance(content, dict):
                # It's a directory
                self.create_directory(path.relative_to(self.base_path))
                self._create_structure_recursive(content, path)
            else:
                # It's a file
                self.create_file(path.relative_to(self.base_path), str(content))

    def count_files(self, pattern: str = "*") -> int:
        """Count files matching pattern."""
        return len(list(self.base_path.rglob(pattern)))

    def list_files(self, pattern: str = "*") -> List[Path]:
        """List files matching pattern."""
        return list(self.base_path.rglob(pattern))

    def cleanup(self) -> None:
        """Clean up temporary directory if created."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def create_genesis_project_structure(base_path: Path) -> MockFilesystem:
    """Create a mock Genesis project structure."""
    fs = MockFilesystem(base_path)

    structure = {
        "CLAUDE.md": "# Genesis Project Context",
        "README.md": "# Genesis",
        "pytest.ini": "[tool:pytest]",
        "conftest.py": '"""Shared fixtures."""',
        "bootstrap": {
            "README.md": "# Bootstrap",
            "src": {"bootstrap.sh": "#!/usr/bin/env bash"},
            "tests": {"test_bootstrap.py": '"""Bootstrap tests."""'},
        },
        "genesis-cli": {
            "README.md": "# Genesis CLI",
            "src": {
                "genesis.py": "#!/usr/bin/env python3",
                "__init__.py": '"""Genesis CLI package."""',
            },
            "tests": {"test_cli.py": '"""CLI tests."""'},
        },
        "smart-commit": {
            "README.md": "# Smart Commit",
            "src": {"smart-commit.sh": "#!/usr/bin/env bash"},
            "tests": {"test_smart_commit.py": '"""Smart commit tests."""'},
        },
        "worktree-tools": {
            "README.md": "# Worktree Tools",
            "src": {"create-sparse-worktree.sh": "#!/usr/bin/env bash"},
            "tests": {"test_sparse_worktree.py": '"""Worktree tests."""'},
        },
        "shared-python": {
            "README.md": "# Shared Python",
            "src": {
                "shared_core": {
                    "__init__.py": '"""Shared core package."""',
                    "retry.py": '"""Retry utility."""',
                    "logger.py": '"""Logger utility."""',
                    "config.py": '"""Config utility."""',
                    "health.py": '"""Health utility."""',
                }
            },
            "tests": {
                "test_retry.py": '"""Retry tests."""',
                "test_logger.py": '"""Logger tests."""',
                "test_config.py": '"""Config tests."""',
                "test_health.py": '"""Health tests."""',
            },
        },
    }

    fs.create_structure(structure)
    return fs


def create_test_project(
    name: str = "test-project", project_type: str = "python-api"
) -> MockFilesystem:
    """Create a test project structure."""
    fs = MockFilesystem()

    if project_type == "python-api":
        structure = {
            "pyproject.toml": f'[tool.poetry]\nname = "{name}"',
            "README.md": f"# {name}",
            "Makefile": 'setup:\n\techo "setup"',
            ".gitignore": "__pycache__/",
            "src": {"__init__.py": '"""API package."""'},
            "tests": {"test_api.py": '"""API tests."""'},
            "docs": {},
        }
    elif project_type == "typescript-service":
        structure = {
            "package.json": f'{{"name": "{name}"}}',
            "README.md": f"# {name}",
            "src": {"index.ts": 'console.log("service");'},
            "tests": {},
            "docs": {},
        }
    elif project_type == "cli-tool":
        structure = {
            "pyproject.toml": f'[tool.poetry]\nname = "{name}"',
            "README.md": f"# {name}",
            "src": {"cli.py": "#!/usr/bin/env python3"},
            "tests": {},
            "docs": {},
        }

    fs.create_structure(structure)
    return fs
