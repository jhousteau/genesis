"""Tests for smart-commit system functionality."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestSmartCommit:
    """Test smart-commit system behavior."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            os.chdir(repo_path)

            # Initialize git repo
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], check=True
            )

            yield repo_path

    def test_no_changes_to_commit(self, temp_git_repo):
        """Test that script exits when no changes exist."""
        smart_commit_path = Path(__file__).parent.parent / "src" / "smart-commit.sh"

        # Run smart-commit with no changes
        result = subprocess.run(
            ["bash", str(smart_commit_path)], capture_output=True, text=True
        )

        assert result.returncode == 1
        assert "No changes to commit" in result.stderr

    def test_with_changes_but_no_precommit(self, temp_git_repo):
        """Test smart-commit with changes but no pre-commit config."""
        # Create a test file
        test_file = temp_git_repo / "test.py"
        test_file.write_text("print('hello world')")

        smart_commit_path = Path(__file__).parent.parent / "src" / "smart-commit.sh"

        # Mock user input for commit type and description
        with patch("builtins.input", side_effect=["1", "add test file", "y"]):
            result = subprocess.run(
                ["bash", str(smart_commit_path)],
                capture_output=True,
                text=True,
                input="1\nadd test file\ny\n",
            )

            # Should succeed even without pre-commit config
            # Check git log to see if commit was created
            log_result = subprocess.run(
                ["git", "log", "--oneline"], capture_output=True, text=True
            )

            # If script ran successfully, there should be a commit
            assert log_result.returncode == 0

    def test_secret_detection(self, temp_git_repo):
        """Test that script detects potential secrets."""
        # Create file with potential secret
        secret_file = temp_git_repo / "config.py"
        secret_file.write_text("API_KEY = 'sk-' + '0' * 48")

        smart_commit_path = Path(__file__).parent.parent / "src" / "smart-commit.sh"

        result = subprocess.run(
            ["bash", str(smart_commit_path)], capture_output=True, text=True
        )

        assert result.returncode == 1
        assert "secrets detected" in result.stderr

    def test_with_precommit_config(self, temp_git_repo):
        """Test smart-commit with pre-commit configuration."""
        # Create a simple pre-commit config
        precommit_config = temp_git_repo / ".pre-commit-config.yaml"
        precommit_config.write_text(
            """
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
"""
        )

        # Create a test file with trailing whitespace
        test_file = temp_git_repo / "test.py"
        test_file.write_text("print('hello')   \n")  # trailing spaces

        smart_commit_path = Path(__file__).parent.parent / "src" / "smart-commit.sh"

        # This test requires pre-commit to be installed
        try:
            subprocess.run(["pre-commit", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("pre-commit not available for testing")

        # Install pre-commit hooks
        subprocess.run(["pre-commit", "install"], capture_output=True)

        result = subprocess.run(
            ["bash", str(smart_commit_path)], capture_output=True, text=True
        )

        # Pre-commit should detect and potentially fix trailing whitespace
        assert (
            "pre-commit" in result.stdout.lower()
            or "pre-commit" in result.stderr.lower()
        )

    def test_commit_message_validation(self, temp_git_repo):
        """Test commit message length validation."""
        # Create a test file
        test_file = temp_git_repo / "test.py"
        test_file.write_text("print('hello')")

        smart_commit_path = Path(__file__).parent.parent / "src" / "smart-commit.sh"

        # Test message too short
        result = subprocess.run(
            ["bash", str(smart_commit_path)],
            capture_output=True,
            text=True,
            input="1\nhi\n",  # Very short description
        )

        # Should fail due to short message
        assert result.returncode == 1
        assert "too short" in result.stderr

    def test_makefile_test_detection(self, temp_git_repo):
        """Test that script can detect and run Makefile tests."""
        # Create a simple Makefile with test target
        makefile = temp_git_repo / "Makefile"
        makefile.write_text(
            """
test:
\t@echo "Running tests..."
\t@echo "All tests passed"
"""
        )

        # Create a test file
        test_file = temp_git_repo / "test.py"
        test_file.write_text("print('hello')")

        smart_commit_path = Path(__file__).parent.parent / "src" / "smart-commit.sh"

        # Mock user input
        with patch("builtins.input", side_effect=["1", "add makefile test", "y"]):
            result = subprocess.run(
                ["bash", str(smart_commit_path)],
                capture_output=True,
                text=True,
                input="1\nadd makefile test\ny\n",
            )

            # Should detect and run make test
            assert "test" in result.stdout.lower()

    def test_script_permissions(self):
        """Test that smart-commit script has execute permissions."""
        smart_commit_path = Path(__file__).parent.parent / "src" / "smart-commit.sh"

        # Check if file exists and has execute permission
        assert smart_commit_path.exists()

        # Check file permissions
        file_stat = smart_commit_path.stat()
        # Check if owner has execute permission (mode & 0o100)
        assert (
            file_stat.st_mode & 0o100
        ), "smart-commit.sh should have execute permissions"

    def test_linting_tools_detection(self, temp_git_repo):
        """Test detection of linting tools."""
        # Create a Python file with linting issues
        test_file = temp_git_repo / "test.py"
        test_file.write_text("import os\nprint( 'hello' )  # Spacing issues")

        smart_commit_path = Path(__file__).parent.parent / "src" / "smart-commit.sh"

        # Check if ruff/black are available
        ruff_available = (
            subprocess.run(["which", "ruff"], capture_output=True).returncode == 0
        )
        black_available = (
            subprocess.run(["which", "black"], capture_output=True).returncode == 0
        )

        if not (ruff_available or black_available):
            pytest.skip("Neither ruff nor black available for testing")

        result = subprocess.run(
            ["bash", str(smart_commit_path)], capture_output=True, text=True
        )

        # Should mention linting in output
        assert "lint" in result.stdout.lower() or "lint" in result.stderr.lower()
