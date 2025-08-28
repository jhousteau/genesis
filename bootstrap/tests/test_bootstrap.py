"""Tests for bootstrap script functionality."""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import pytest


class TestBootstrapScript:
    """Test bootstrap script functionality."""

    def test_script_exists_and_executable(self):
        """Test that bootstrap script exists and is executable."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"
        assert script_path.exists(), "Bootstrap script should exist"
        assert os.access(script_path, os.X_OK), "Script should be executable"

    def test_help_flag_works(self):
        """Test that --help flag shows usage information."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        result = subprocess.run(
            ["bash", str(script_path), "--help"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "Bootstrap project" in result.stdout
        assert "Arguments:" in result.stdout
        assert "Options:" in result.stdout

    def test_insufficient_arguments_shows_usage(self):
        """Test that insufficient arguments shows usage and exits with error."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        result = subprocess.run(
            ["bash", str(script_path)], capture_output=True, text=True
        )

        assert result.returncode == 1
        assert "Usage:" in result.stdout

    def test_python_api_project_creation(self):
        """Test Python API project creation."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_name = "test-api"

            result = subprocess.run(
                [
                    "bash",
                    str(script_path),
                    project_name,
                    "--type",
                    "python-api",
                    "--path",
                    tmpdir,
                    "--skip-git",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            project_path = Path(tmpdir) / project_name
            assert project_path.exists()
            assert (project_path / "pyproject.toml").exists()
            assert (project_path / "src").exists()
            assert (project_path / "tests").exists()
            assert (project_path / "README.md").exists()
            assert (project_path / "Makefile").exists()
            assert (project_path / ".gitignore").exists()

            # Check pyproject.toml content
            pyproject_content = (project_path / "pyproject.toml").read_text()
            assert project_name in pyproject_content
            assert "fastapi" in pyproject_content

    def test_typescript_service_project_creation(self):
        """Test TypeScript service project creation."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_name = "test-service"

            result = subprocess.run(
                [
                    "bash",
                    str(script_path),
                    project_name,
                    "--type",
                    "typescript-service",
                    "--path",
                    tmpdir,
                    "--skip-git",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            project_path = Path(tmpdir) / project_name
            assert project_path.exists()
            assert (project_path / "package.json").exists()
            assert (project_path / "src").exists()
            assert (project_path / "tests").exists()

            # Check package.json content
            package_content = (project_path / "package.json").read_text()
            assert project_name in package_content
            assert "express" in package_content

    def test_cli_tool_project_creation(self):
        """Test CLI tool project creation."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_name = "test-cli"

            result = subprocess.run(
                [
                    "bash",
                    str(script_path),
                    project_name,
                    "--type",
                    "cli-tool",
                    "--path",
                    tmpdir,
                    "--skip-git",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            project_path = Path(tmpdir) / project_name
            assert project_path.exists()
            assert (project_path / "pyproject.toml").exists()

            # Check pyproject.toml content
            pyproject_content = (project_path / "pyproject.toml").read_text()
            assert project_name in pyproject_content
            assert "click" in pyproject_content

    def test_git_initialization_works(self):
        """Test that Git initialization works when not skipped."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_name = "test-git"

            # Need git available for this test
            if shutil.which("git") is None:
                pytest.skip("Git not available")

            result = subprocess.run(
                ["bash", str(script_path), project_name, "--path", tmpdir],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            if result.returncode != 0:
                # Git config might not be set up, skip test
                if "user.name" in result.stderr or "user.email" in result.stderr:
                    pytest.skip("Git user config not set up")

            project_path = Path(tmpdir) / project_name
            assert project_path.exists()
            assert (project_path / ".git").exists()

    def test_unknown_option_fails(self):
        """Test that unknown options cause script to fail."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        result = subprocess.run(
            ["bash", str(script_path), "test-project", "--unknown-option"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Unknown option" in result.stderr

    def test_script_syntax_validation(self):
        """Test that the script has valid bash syntax."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        result = subprocess.run(
            ["bash", "-n", str(script_path)], capture_output=True, text=True
        )

        assert result.returncode == 0, f"Script has syntax errors: {result.stderr}"

    def test_line_count_meets_requirement(self):
        """Test that script meets the ~150 line requirement."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        with open(script_path, "r") as f:
            lines = len(f.readlines())

        assert lines <= 180, f"Script should be ~150 lines, got {lines}"
        assert lines >= 140, f"Script seems too short at {lines} lines"

    def test_makefile_content_valid(self):
        """Test that generated Makefile has valid content."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_name = "test-makefile"

            result = subprocess.run(
                [
                    "bash",
                    str(script_path),
                    project_name,
                    "--path",
                    tmpdir,
                    "--skip-git",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            makefile_path = Path(tmpdir) / project_name / "Makefile"
            makefile_content = makefile_path.read_text()

            # Check for essential targets
            assert "setup:" in makefile_content
            assert "test:" in makefile_content
            assert "lint:" in makefile_content
            assert "build:" in makefile_content
            assert "clean:" in makefile_content
            assert "help:" in makefile_content

    def test_gitignore_content_valid(self):
        """Test that generated .gitignore has appropriate entries."""
        script_path = Path(__file__).parent.parent / "src" / "bootstrap.sh"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_name = "test-gitignore"

            result = subprocess.run(
                [
                    "bash",
                    str(script_path),
                    project_name,
                    "--path",
                    tmpdir,
                    "--skip-git",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            gitignore_path = Path(tmpdir) / project_name / ".gitignore"
            gitignore_content = gitignore_path.read_text()

            # Check for common ignore patterns
            assert "node_modules/" in gitignore_content
            assert "__pycache__/" in gitignore_content
            assert ".venv/" in gitignore_content
            assert "dist/" in gitignore_content
            assert ".env" in gitignore_content
