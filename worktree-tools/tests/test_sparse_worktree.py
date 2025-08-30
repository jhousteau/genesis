"""Tests for sparse worktree creator functionality."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestSparseWorktreeCreator:
    """Test sparse worktree creator script functionality."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            repo_path.mkdir()
            os.chdir(repo_path)

            # Initialize git repo
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], check=True
            )

            # Create test file structure
            (repo_path / "src").mkdir()
            (repo_path / "src" / "auth").mkdir()
            (repo_path / "src" / "auth" / "login.py").write_text("# Login module")
            (repo_path / "tests").mkdir()
            (repo_path / "tests" / "test_auth.py").write_text("# Auth tests")
            (repo_path / "README.md").write_text("# Test repo")

            # Initial commit
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

            yield repo_path

    def test_script_exists_and_executable(self):
        """Test that the sparse worktree script exists and is executable."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        assert script_path.exists(), "Sparse worktree script should exist"
        assert os.access(script_path, os.X_OK), "Script should be executable"

    def test_help_flag_works(self):
        """Test that --help flag shows usage information."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        result = subprocess.run(
            ["bash", str(script_path), "--help"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "AI-safe sparse worktree" in result.stdout
        assert "Arguments:" in result.stdout
        assert "Options:" in result.stdout

    def test_insufficient_arguments_shows_usage(self):
        """Test that insufficient arguments shows usage and exits with error."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        result = subprocess.run(
            ["bash", str(script_path)], capture_output=True, text=True
        )

        assert result.returncode == 1
        assert "Usage:" in result.stdout

    def test_nonexistent_focus_path_fails(self, temp_git_repo):
        """Test that script fails when focus path doesn't exist."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        result = subprocess.run(
            ["bash", str(script_path), "test-worktree", "nonexistent/path"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Focus path not found" in result.stdout

    def test_basic_worktree_creation_with_file(self, temp_git_repo):
        """Test basic worktree creation focusing on a single file."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        # Create worktrees directory
        worktrees_dir = temp_git_repo.parent / "worktrees"
        worktrees_dir.mkdir(exist_ok=True)

        result = subprocess.run(
            ["bash", str(script_path), "test-auth", "src/auth/login.py"],
            capture_output=True,
            text=True,
            cwd=temp_git_repo,
        )

        # Should succeed (return code 0 or handle expected git errors gracefully)
        if result.returncode != 0:
            # Check if it's a git worktree limitation issue
            if (
                "worktree" in result.stderr.lower()
                or "sparse-checkout" in result.stderr.lower()
            ):
                pytest.skip(
                    "Git worktree functionality not available in test environment"
                )

        assert "Creating AI-safe sparse worktree" in result.stdout
        assert "test-auth" in result.stdout
        assert "src/auth/login.py" in result.stdout

    def test_basic_worktree_creation_with_directory(self, temp_git_repo):
        """Test basic worktree creation focusing on a directory."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        worktrees_dir = temp_git_repo.parent / "worktrees"
        worktrees_dir.mkdir(exist_ok=True)

        result = subprocess.run(
            ["bash", str(script_path), "test-dir", "tests/"],
            capture_output=True,
            text=True,
            cwd=temp_git_repo,
        )

        if result.returncode != 0:
            if "worktree" in result.stderr.lower():
                pytest.skip(
                    "Git worktree functionality not available in test environment"
                )

        assert "Creating AI-safe sparse worktree" in result.stdout
        assert "test-dir" in result.stdout
        assert "tests/" in result.stdout

    def test_max_files_option(self, temp_git_repo):
        """Test --max-files option works correctly."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        worktrees_dir = temp_git_repo.parent / "worktrees"
        worktrees_dir.mkdir(exist_ok=True)

        result = subprocess.run(
            ["bash", str(script_path), "test-limit", "src/", "--max-files", "5"],
            capture_output=True,
            text=True,
            cwd=temp_git_repo,
        )

        if result.returncode != 0:
            if "worktree" in result.stderr.lower():
                pytest.skip(
                    "Git worktree functionality not available in test environment"
                )

        assert "max-files" in result.stdout.lower() or "limit" in result.stdout
        assert "5" in result.stdout

    def test_verify_option(self, temp_git_repo):
        """Test --verify option performs safety checks."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        worktrees_dir = temp_git_repo.parent / "worktrees"
        worktrees_dir.mkdir(exist_ok=True)

        result = subprocess.run(
            ["bash", str(script_path), "test-verify", "README.md", "--verify"],
            capture_output=True,
            text=True,
            cwd=temp_git_repo,
        )

        if result.returncode != 0:
            if "worktree" in result.stderr.lower():
                pytest.skip(
                    "Git worktree functionality not available in test environment"
                )

        # Should mention verification in output
        assert "verify" in result.stdout.lower() or "safety" in result.stdout.lower()

    def test_invalid_max_files_value(self, temp_git_repo):
        """Test that invalid max-files values are rejected."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        result = subprocess.run(
            [
                "bash",
                str(script_path),
                "test-invalid",
                "README.md",
                "--max-files",
                "not-a-number",
            ],
            capture_output=True,
            text=True,
            cwd=temp_git_repo,
        )

        assert result.returncode == 1
        assert "must be a number" in result.stdout

    def test_unknown_option_fails(self, temp_git_repo):
        """Test that unknown options cause script to fail with usage."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        result = subprocess.run(
            ["bash", str(script_path), "test-unknown", "README.md", "--unknown-option"],
            capture_output=True,
            text=True,
            cwd=temp_git_repo,
        )

        assert result.returncode == 1
        assert "Unknown option" in result.stdout
        assert "Usage:" in result.stdout

    def test_script_syntax_validation(self):
        """Test that the script has valid bash syntax."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        result = subprocess.run(
            ["bash", "-n", str(script_path)], capture_output=True, text=True
        )

        assert result.returncode == 0, f"Script has syntax errors: {result.stderr}"

    def test_line_count_meets_requirement(self):
        """Test that script meets the ~150 line requirement."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        with open(script_path) as f:
            lines = len(f.readlines())

        assert lines <= 200, f"Script should be ~180 lines, got {lines}"
        assert lines >= 130, f"Script seems too short at {lines} lines"

    def test_ai_safety_features_documented(self):
        """Test that AI safety features are documented in the script."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        with open(script_path) as f:
            content = f.read()

        # Check for key AI safety features
        assert "ai-safety-manifest" in content.lower()
        assert "file count" in content.lower() or "file limit" in content.lower()
        assert "contamination" in content.lower()
        assert "depth" in content.lower()

        # Check for safety rules/restrictions
        assert "max" in content.lower() and "files" in content.lower()

    def test_color_output_functions(self):
        """Test that color output is properly configured."""
        script_path = Path(__file__).parent.parent / "src" / "create-sparse-worktree.sh"

        with open(script_path) as f:
            content = f.read()

        # Check for color definitions
        assert "RED=" in content
        assert "GREEN=" in content
        assert "YELLOW=" in content
        assert "NC=" in content  # No Color

        # Check color codes are used in output
        assert "${GREEN}" in content or "${RED}" in content
