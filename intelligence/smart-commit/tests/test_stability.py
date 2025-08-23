"""Tests for stability module."""

import pytest
from smart_commit.stability import StabilityEngine


@pytest.fixture
def test_project(tmp_path):
    """Create a test project with gitignore and various files."""
    # Create regular source files
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "config.yaml").write_text("name: test")

    # Create .gitignore file
    gitignore_content = """# Virtual environments
.venv/
venv/

# Python cache
__pycache__/
*.pyc

# Node modules
node_modules/

# Build directories
build/
dist/
"""
    (tmp_path / ".gitignore").write_text(gitignore_content)

    # Create files in excluded directories
    excluded_paths = []
    for excluded_dir in [".venv", "node_modules", "__pycache__"]:
        excluded_dir_path = tmp_path / excluded_dir
        excluded_dir_path.mkdir()
        excluded_file = excluded_dir_path / "file.py"
        excluded_file.write_text("# should be ignored")
        excluded_paths.append(excluded_file)

    return tmp_path, excluded_paths


def test_capture_state_respects_gitignore(test_project):
    """Test that _capture_state correctly respects gitignore patterns."""
    project_root, excluded_paths = test_project

    engine = StabilityEngine(project_root)
    state = engine._capture_state()

    # Check that state contains the main files
    assert any(p.name == "main.py" for p in state.keys())
    assert any(p.name == "config.yaml" for p in state.keys())

    # Check that no files from gitignored dirs are present
    for excluded_path in excluded_paths:
        assert excluded_path not in state.keys(), f"Found gitignored file {excluded_path} in state"


def test_capture_state_without_gitignore(tmp_path):
    """Test that _capture_state works without a .gitignore file."""
    # Create files without gitignore
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "utils.py").write_text("def helper(): pass")

    # Create .git directory (should always be excluded)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config.py").write_text("# git file")

    engine = StabilityEngine(tmp_path)
    state = engine._capture_state()

    # Check that regular files are included
    assert any(p.name == "main.py" for p in state.keys())
    assert any(p.name == "utils.py" for p in state.keys())

    # Check that .git files are excluded even without gitignore
    assert not any(
        ".git" in str(p) for p in state.keys()
    ), "Found .git file in state even though it should always be excluded"
