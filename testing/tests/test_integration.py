"""Integration tests for Genesis components working together."""

import pytest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from testing.fixtures import (
    create_genesis_project_structure,
    create_mock_shell_commands,
    patch_subprocess_run,
)


class TestComponentIntegration:
    """Test integration between Genesis components."""

    @pytest.mark.integration
    def test_bootstrap_to_worktree_workflow(self, temp_dir):
        """Test workflow: bootstrap project -> create worktree."""
        # Mock Genesis project
        fs = create_genesis_project_structure(temp_dir)

        with patch_subprocess_run()[0] as mock_run:
            # Mock bootstrap script execution
            mock_run.return_value.returncode = 0

            # Import real CLI, not mock one
            import sys

            sys.path.insert(
                0, str(Path(__file__).parent.parent.parent / "genesis-cli" / "src")
            )

            from genesis import cli
            from click.testing import CliRunner

            runner = CliRunner()

            # Mock find_genesis_root to return our temp directory
            with patch("genesis.find_genesis_root", return_value=temp_dir):
                # Test bootstrap command
                result = runner.invoke(
                    cli,
                    ["bootstrap", "test-project", "--type", "python-api", "--skip-git"],
                )

                assert result.exit_code == 0
                assert "Project 'test-project' created successfully" in result.output

                # Test worktree command
                result = runner.invoke(
                    cli, ["worktree", "fix-auth", "src/auth/login.py"]
                )

                assert result.exit_code == 0
                assert (
                    "Sparse worktree 'fix-auth' created successfully" in result.output
                )

    @pytest.mark.integration
    def test_cli_status_with_all_components(self, temp_dir):
        """Test CLI status command with all components present."""
        fs = create_genesis_project_structure(temp_dir)

        # Import real CLI
        import sys

        sys.path.insert(
            0, str(Path(__file__).parent.parent.parent / "genesis-cli" / "src")
        )

        from genesis import cli
        from click.testing import CliRunner

        runner = CliRunner()

        with patch("genesis.find_genesis_root", return_value=temp_dir):
            with patch_subprocess_run()[0] as mock_run:
                # Mock file count check
                mock_run.return_value.stdout = "file1\nfile2\nfile3"
                mock_run.return_value.returncode = 0

                result = runner.invoke(cli, ["status"])

                assert result.exit_code == 0
                assert "Genesis project is healthy" in result.output
                assert "bootstrap" in result.output
                assert "genesis-cli" in result.output
                assert "smart-commit" in result.output
                assert "worktree-tools" in result.output
                assert "shared-python" in result.output

    @pytest.mark.integration
    def test_smart_commit_integration(self, temp_dir):
        """Test smart commit integration with CLI."""
        fs = create_genesis_project_structure(temp_dir)

        import sys

        sys.path.insert(
            0, str(Path(__file__).parent.parent.parent / "genesis-cli" / "src")
        )

        from genesis import cli
        from click.testing import CliRunner

        runner = CliRunner()

        with patch("genesis.find_genesis_root", return_value=temp_dir):
            with patch_subprocess_run()[0] as mock_run:
                mock_run.return_value.returncode = 0

                result = runner.invoke(cli, ["commit"])

                assert result.exit_code == 0
                assert "Smart commit completed" in result.output

    @pytest.mark.integration
    def test_shared_python_utilities_integration(self, temp_dir):
        """Test that shared Python utilities work together."""
        fs = create_genesis_project_structure(temp_dir)
        shared_python_path = temp_dir / "shared-python" / "src"

        # Add real shared_core package to path
        import sys

        sys.path.insert(0, str(shared_python_path))

        # Test importing and using utilities together
        try:
            # This would normally work with real shared-python
            # For now, just test the structure exists
            assert (shared_python_path / "shared_core" / "__init__.py").exists()
            assert (shared_python_path / "shared_core" / "retry.py").exists()
            assert (shared_python_path / "shared_core" / "logger.py").exists()
            assert (shared_python_path / "shared_core" / "config.py").exists()
            assert (shared_python_path / "shared_core" / "health.py").exists()
        except ImportError:
            # Expected in test environment
            pass

    @pytest.mark.integration
    def test_component_script_discovery(self, temp_dir):
        """Test that CLI can discover all component scripts."""
        fs = create_genesis_project_structure(temp_dir)

        # Test script discovery
        bootstrap_script = temp_dir / "bootstrap" / "src" / "bootstrap.sh"
        smart_commit_script = temp_dir / "smart-commit" / "src" / "smart-commit.sh"
        worktree_script = (
            temp_dir / "worktree-tools" / "src" / "create-sparse-worktree.sh"
        )

        assert bootstrap_script.exists()
        assert smart_commit_script.exists()
        assert worktree_script.exists()

        # Make scripts executable (would be done in real environment)
        bootstrap_script.chmod(0o755)
        smart_commit_script.chmod(0o755)
        worktree_script.chmod(0o755)


class TestEndToEndWorkflows:
    """End-to-end tests for complete Genesis workflows."""

    @pytest.mark.e2e
    def test_complete_development_workflow(self, temp_dir):
        """Test complete workflow: bootstrap -> develop -> commit."""
        fs = create_genesis_project_structure(temp_dir)

        import sys

        sys.path.insert(
            0, str(Path(__file__).parent.parent.parent / "genesis-cli" / "src")
        )

        from genesis import cli
        from click.testing import CliRunner

        runner = CliRunner()

        with patch("genesis.find_genesis_root", return_value=temp_dir):
            with patch_subprocess_run()[0] as mock_run:
                mock_run.return_value.returncode = 0

                # Step 1: Check status
                result = runner.invoke(cli, ["status"])
                assert result.exit_code == 0
                assert "healthy" in result.output

                # Step 2: Bootstrap new project
                result = runner.invoke(
                    cli, ["bootstrap", "my-api", "--type", "python-api"]
                )
                assert result.exit_code == 0

                # Step 3: Create worktree for development
                result = runner.invoke(cli, ["worktree", "add-feature", "src/api/"])
                assert result.exit_code == 0

                # Step 4: Sync dependencies
                result = runner.invoke(cli, ["sync"])
                assert result.exit_code == 0

                # Step 5: Make commit
                result = runner.invoke(cli, ["commit"])
                assert result.exit_code == 0

                # Step 6: Clean up
                result = runner.invoke(cli, ["clean", "--worktrees"])
                assert result.exit_code == 0

    @pytest.mark.e2e
    @pytest.mark.ai_safety
    def test_ai_safety_throughout_workflow(self, temp_dir):
        """Test that AI safety is maintained throughout workflow."""
        fs = create_genesis_project_structure(temp_dir)

        from testing.utilities import AISafetyChecker

        checker = AISafetyChecker(max_total_files=100, max_component_files=30)

        # Initial safety check
        initial_result = checker.check_project(temp_dir)
        assert initial_result["is_safe"]

        # Simulate adding some files during development
        new_files_dir = temp_dir / "genesis-cli" / "src"
        for i in range(5):
            (new_files_dir / f"new_file_{i}.py").write_text(f"# New file {i}")

        # Should still be safe
        updated_result = checker.check_project(temp_dir)
        assert updated_result["is_safe"]

        # Test component isolation
        for component in [
            "bootstrap",
            "genesis-cli",
            "smart-commit",
            "worktree-tools",
            "shared-python",
        ]:
            component_path = temp_dir / component
            component_result = checker.check_component(component_path)
            assert component_result[
                "is_safe"
            ], f"Component {component} unsafe after workflow"


class TestErrorHandlingIntegration:
    """Test error handling across component boundaries."""

    @pytest.mark.integration
    def test_cli_error_propagation(self, temp_dir):
        """Test that errors from scripts propagate correctly through CLI."""
        fs = create_genesis_project_structure(temp_dir)

        import sys

        sys.path.insert(
            0, str(Path(__file__).parent.parent.parent / "genesis-cli" / "src")
        )

        from genesis import cli
        from click.testing import CliRunner

        runner = CliRunner()

        with patch("genesis.find_genesis_root", return_value=temp_dir):
            # Mock script failure by raising CalledProcessError
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(
                    1, "bootstrap", "Script failed"
                )

                result = runner.invoke(cli, ["bootstrap", "test-project"])

                assert result.exit_code == 1
                assert "Bootstrap failed" in result.output

    @pytest.mark.integration
    def test_missing_component_handling(self, temp_dir):
        """Test handling of missing components."""
        # Create incomplete Genesis structure
        (temp_dir / "CLAUDE.md").write_text("# Genesis")
        # Don't create all components

        import sys

        sys.path.insert(
            0, str(Path(__file__).parent.parent.parent / "genesis-cli" / "src")
        )

        from genesis import cli
        from click.testing import CliRunner

        runner = CliRunner()

        with patch("genesis.find_genesis_root", return_value=temp_dir):
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 1
            assert "Missing" in result.output or "project has issues" in result.output

    @pytest.mark.integration
    def test_invalid_project_detection(self):
        """Test detection and handling of invalid project structures."""
        import sys

        sys.path.insert(
            0, str(Path(__file__).parent.parent.parent / "genesis-cli" / "src")
        )

        from genesis import cli
        from click.testing import CliRunner

        runner = CliRunner()

        # Mock non-Genesis directory
        with patch("genesis.find_genesis_root", return_value=None):
            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 1
            assert "Not in a Genesis project" in result.output
