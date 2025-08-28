"""Tests for Genesis autofix system."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from genesis.core.autofix import (
    AutoFixer,
    ConvergenceError,
    ConvergentFixer,
    ProjectDetector,
    ProjectType,
    PythonSubtype,
)
from genesis.core.autofix.stages import (
    BasicFixesStage,
    NodeFormatterStage,
    PythonFormatterStage,
)


class TestProjectDetector:
    """Tests for project type detection."""

    def test_detect_python_poetry_project(self, tmp_path):
        """Test detection of Poetry Python project."""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(
            """
[tool.poetry]
name = "test-project"
version = "1.0.0"

[tool.ruff]
line-length = 88
"""
        )

        detector = ProjectDetector(tmp_path)
        info = detector.detect()

        assert info.project_type == ProjectType.PYTHON
        assert info.python_subtype == PythonSubtype.POETRY
        assert not info.has_docker
        assert not info.has_precommit

    def test_detect_node_project(self, tmp_path):
        """Test detection of Node.js project."""
        package_path = tmp_path / "package.json"
        package_path.write_text('{"name": "test-project", "version": "1.0.0"}')

        detector = ProjectDetector(tmp_path)
        info = detector.detect()

        assert info.project_type == ProjectType.NODE
        assert info.python_subtype is None

    def test_detect_docker_and_precommit(self, tmp_path):
        """Test detection of Docker and pre-commit."""
        (tmp_path / "Dockerfile").write_text("FROM python:3.11")
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")

        detector = ProjectDetector(tmp_path)
        info = detector.detect()

        assert info.has_docker
        assert info.has_precommit

    def test_detect_unknown_project(self, tmp_path):
        """Test detection of unknown project type."""
        detector = ProjectDetector(tmp_path)
        info = detector.detect()

        assert info.project_type == ProjectType.UNKNOWN


class TestConvergentFixer:
    """Tests for convergent fixing logic."""

    def test_convergent_fixing_success(self):
        """Test successful convergent fixing."""
        fixer = ConvergentFixer(max_runs=3, dry_run=False)

        # Mock git diff to show no changes after first run
        with patch("subprocess.run") as mock_run:
            # First call: git diff before (empty)
            # Second call: command execution
            # Third call: git diff after (empty - no changes)
            mock_run.side_effect = [
                Mock(stdout="", returncode=0),  # git diff before
                Mock(returncode=0),  # command execution
                Mock(stdout="", returncode=0),  # git diff after
            ]

            result = fixer.run_until_stable("test", "echo 'test'")

        assert result.converged
        assert result.runs == 1
        assert result.final_command == "echo 'test'"

    def test_convergent_fixing_multiple_runs(self):
        """Test convergent fixing that requires multiple runs."""
        fixer = ConvergentFixer(max_runs=3, dry_run=False)

        with patch("subprocess.run") as mock_run:
            # Run 1: changes detected
            mock_run.side_effect = [
                Mock(stdout="", returncode=0),  # git diff before
                Mock(returncode=0),  # command
                Mock(stdout="file1.py", returncode=0),  # git diff after (changes)
                # Run 2: no more changes
                Mock(stdout="file1.py", returncode=0),  # git diff before
                Mock(returncode=0),  # command
                Mock(stdout="file1.py", returncode=0),  # git diff after (no changes)
            ]

            result = fixer.run_until_stable("test", "echo 'test'")

        assert result.converged
        assert result.runs == 2

    def test_convergent_fixing_failure(self):
        """Test convergent fixing that doesn't converge."""
        fixer = ConvergentFixer(max_runs=2, dry_run=False)

        with patch("subprocess.run") as mock_run:
            # Always show changes
            mock_run.side_effect = [
                Mock(stdout="", returncode=0),  # git diff before
                Mock(returncode=0),  # command
                Mock(stdout="file1.py", returncode=0),  # git diff after
                Mock(stdout="file1.py", returncode=0),  # git diff before
                Mock(returncode=0),  # command
                Mock(stdout="file2.py", returncode=0),  # git diff after
            ]

            result = fixer.run_until_stable("test", "echo 'test'")

        assert not result.converged
        assert result.runs == 2

    def test_dry_run_mode(self):
        """Test dry run mode."""
        fixer = ConvergentFixer(dry_run=True)

        result = fixer.run_until_stable("test", "echo 'test'")

        assert result.converged
        assert result.runs == 0

    def test_git_command_failure(self):
        """Test handling of git command failure."""
        fixer = ConvergentFixer(dry_run=False)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            with pytest.raises(ConvergenceError):
                fixer.run_until_stable("test", "echo 'test'")


class TestStages:
    """Tests for individual stages."""

    def test_basic_fixes_stage_with_precommit(self):
        """Test basic fixes stage with pre-commit available."""
        stage = BasicFixesStage()

        # Create project info with pre-commit
        from genesis.core.autofix.detectors import ProjectInfo

        project_info = ProjectInfo(
            project_type=ProjectType.PYTHON,
            has_precommit=True,
            available_tools={"pre-commit": True},
        )

        commands = stage.get_commands(project_info)

        assert len(commands) == 2
        assert "trailing-whitespace" in commands[0][0]
        assert "end-of-file-fixer" in commands[1][0]

    def test_python_formatter_stage_poetry(self):
        """Test Python formatter stage with Poetry."""
        stage = PythonFormatterStage()

        from genesis.core.autofix.detectors import ProjectInfo

        project_info = ProjectInfo(
            project_type=ProjectType.PYTHON,
            python_subtype=PythonSubtype.POETRY,
            available_tools={
                "poetry-isort": True,
                "poetry-black": True,
                "poetry-ruff": True,
            },
        )

        commands = stage.get_commands(project_info)

        assert len(commands) == 3
        assert any("isort" in cmd[1] for cmd in commands)
        assert any("black" in cmd[1] for cmd in commands)
        assert any("ruff format" in cmd[1] for cmd in commands)

    def test_node_formatter_stage(self):
        """Test Node.js formatter stage."""
        stage = NodeFormatterStage()

        from genesis.core.autofix.detectors import ProjectInfo

        project_info = ProjectInfo(
            project_type=ProjectType.NODE, available_tools={"prettier": True}
        )
        # Set project_root after initialization
        project_info.project_root = Path("/fake/project")

        commands = stage.get_commands(project_info)

        assert len(commands) == 1
        assert "prettier" in commands[0][1]

    def test_stage_with_wrong_project_type(self):
        """Test stage with incompatible project type."""
        stage = PythonFormatterStage()

        from genesis.core.autofix.detectors import ProjectInfo

        project_info = ProjectInfo(project_type=ProjectType.NODE)

        commands = stage.get_commands(project_info)

        assert len(commands) == 0


class TestAutoFixer:
    """Tests for main AutoFixer class."""

    def test_autofixer_initialization(self, tmp_path):
        """Test AutoFixer initialization."""
        fixer = AutoFixer(project_root=tmp_path, max_iterations=3)

        assert fixer.project_root == tmp_path
        assert fixer.max_iterations == 3
        assert fixer.stage_all_files
        assert fixer.run_validation

    @patch("genesis.core.autofix.fixer.ProjectDetector")
    @patch("genesis.core.autofix.fixer.StageOrchestrator")
    def test_autofixer_run_success(self, mock_orchestrator, mock_detector, tmp_path):
        """Test successful AutoFixer run."""
        # Mock project detection
        from genesis.core.autofix.detectors import ProjectInfo

        mock_project_info = ProjectInfo(project_type=ProjectType.PYTHON)
        mock_detector.return_value.detect.return_value = mock_project_info

        # Mock stage results
        from genesis.core.autofix.stages import StageResult, StageType

        mock_stage_result = StageResult(
            stage_name="test",
            stage_type=StageType.FORMATTER,
            success=True,
            convergence_results=[],
        )
        mock_orchestrator.return_value.run_all.return_value = [mock_stage_result]

        fixer = AutoFixer(project_root=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = fixer.run(dry_run=False)

        assert result.success
        assert not result.dry_run
        assert len(result.stage_results) == 1

    def test_autofixer_dry_run(self, tmp_path):
        """Test AutoFixer dry run mode."""
        fixer = AutoFixer(project_root=tmp_path)

        with patch.object(fixer.detector, "detect") as mock_detect:
            from genesis.core.autofix.detectors import ProjectInfo

            mock_detect.return_value = ProjectInfo(project_type=ProjectType.PYTHON)

            with patch.object(fixer.orchestrator, "run_all") as mock_run_all:
                from genesis.core.autofix.stages import StageResult, StageType

                mock_run_all.return_value = [
                    StageResult(
                        stage_name="test",
                        stage_type=StageType.FORMATTER,
                        success=True,
                        convergence_results=[],
                    )
                ]

                result = fixer.run(dry_run=True)

        assert result.success
        assert result.dry_run
        assert not result.files_staged

    def test_autofixer_run_stage_only(self, tmp_path):
        """Test running only specific stages."""
        fixer = AutoFixer(project_root=tmp_path)

        with patch.object(fixer.detector, "detect") as mock_detect:
            from genesis.core.autofix.detectors import ProjectInfo

            mock_detect.return_value = ProjectInfo(project_type=ProjectType.PYTHON)

            result = fixer.run_stage_only(["formatter"], dry_run=True)

        assert result.success
        assert result.dry_run

    def test_autofixer_error_handling(self, tmp_path):
        """Test AutoFixer error handling."""
        fixer = AutoFixer(project_root=tmp_path)

        with patch.object(fixer.detector, "detect") as mock_detect:
            mock_detect.side_effect = Exception("Test error")

            result = fixer.run()

        assert not result.success
        assert result.error == "Test error"

    def test_get_available_tools(self, tmp_path):
        """Test getting available tools information."""
        fixer = AutoFixer(project_root=tmp_path)

        with patch.object(fixer.detector, "detect") as mock_detect:
            from genesis.core.autofix.detectors import ProjectInfo

            mock_info = ProjectInfo(
                project_type=ProjectType.PYTHON,
                python_subtype=PythonSubtype.POETRY,
                has_docker=True,
                available_tools={"black": True, "ruff": True},
            )
            mock_detect.return_value = mock_info

            tools = fixer.get_available_tools()

        assert tools["project_type"] == "python"
        assert tools["python_subtype"] == "poetry"
        assert tools["has_docker"]
        assert tools["available_tools"]["black"]
        assert tools["available_tools"]["ruff"]


class TestIntegration:
    """Integration tests for the complete autofix system."""

    def test_end_to_end_python_project(self, tmp_path):
        """Test end-to-end autofix on a Python project."""
        # Create a Python project structure
        (tmp_path / "pyproject.toml").write_text(
            """
[tool.poetry]
name = "test-project"
version = "1.0.0"
"""
        )

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "test.py").write_text("print('hello world')")

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        fixer = AutoFixer(project_root=tmp_path)

        # Test with dry run first
        result = fixer.run(dry_run=True)

        assert result.success
        assert result.dry_run
        assert result.project_info.project_type == ProjectType.PYTHON

    @pytest.mark.skipif(not Path("/usr/bin/git").exists(), reason="Git not available")
    def test_git_staging_functionality(self, tmp_path):
        """Test git staging functionality."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create a file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('test')")

        fixer = AutoFixer(project_root=tmp_path, stage_all_files=True)

        # Mock the detector and orchestrator to avoid running actual tools
        with patch.object(fixer.detector, "detect") as mock_detect:
            from genesis.core.autofix.detectors import ProjectInfo

            mock_detect.return_value = ProjectInfo(project_type=ProjectType.PYTHON)

            with patch.object(fixer.orchestrator, "run_all") as mock_run_all:
                from genesis.core.autofix.stages import StageResult, StageType

                mock_run_all.return_value = [
                    StageResult(
                        stage_name="test",
                        stage_type=StageType.FORMATTER,
                        success=True,
                        convergence_results=[],
                    )
                ]

                result = fixer.run(dry_run=False)

        assert result.success
        assert result.files_staged
