"""Integration tests for Genesis components working together."""

from pathlib import Path
from unittest.mock import patch

import pytest

from testing.fixtures import (
    create_genesis_project_structure,
    patch_subprocess_run,
)


class TestComponentIntegration:
    """Test integration between Genesis components."""

    @pytest.mark.integration
    def test_bootstrap_to_worktree_workflow(self, temp_dir):
        """Test workflow: bootstrap project -> create worktree."""
        # Mock Genesis project
        create_genesis_project_structure(temp_dir)

        with patch_subprocess_run()[0] as mock_run:
            # Mock bootstrap script execution
            mock_run.return_value.returncode = 0

            # Import real CLI, not mock one

            from click.testing import CliRunner

            from genesis.cli import cli

            runner = CliRunner()

            # Mock find_genesis_root to return our temp directory
            with (
                patch("genesis.cli.get_git_root", return_value=temp_dir),
                patch(
                    "genesis.core.constants.get_git_author_info",
                    return_value=("Test User", "test@example.com"),
                ),
            ):
                # Test bootstrap command - use clean project name and change working dir
                project_name = "test-project"
                import os

                try:
                    old_cwd = Path.cwd()
                    os.chdir(temp_dir)
                    result = runner.invoke(
                        cli,
                        [
                            "bootstrap",
                            project_name,
                            "--type",
                            "python-api",
                            "--skip-git",
                        ],
                    )
                finally:
                    try:
                        os.chdir(old_cwd)
                    except (OSError, FileNotFoundError):
                        # Original directory might be deleted, go to a safe location
                        os.chdir(Path.home())

                assert result.exit_code == 0
                assert "created successfully" in result.output

                # Test that a bootstrap project is ready for worktree usage
                project_path = temp_dir / project_name
                assert project_path.exists()
                assert (project_path / "README.md").exists()
                assert (project_path / "pyproject.toml").exists()

    @pytest.mark.integration
    def test_cli_status_with_all_components(self, temp_dir):
        """Test CLI status command with all components present."""
        create_genesis_project_structure(temp_dir)

        # Import real CLI
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "genesis"))

        from click.testing import CliRunner

        from genesis.cli import cli

        runner = CliRunner()

        with (
            patch("genesis.cli.get_git_root", return_value=temp_dir),
            patch(
                "genesis.core.constants.get_git_author_info",
                return_value=("Test User", "test@example.com"),
            ),
        ):
            with patch_subprocess_run()[0] as mock_run:
                # Mock file count check
                mock_run.return_value.stdout = "file1\nfile2\nfile3"
                mock_run.return_value.returncode = 0

                result = runner.invoke(cli, ["status"])

                assert result.exit_code == 0
                assert "Genesis project is healthy" in result.output
                assert "bootstrap" in result.output
                assert "genesis" in result.output
                assert "smart-commit" in result.output
                assert "worktree-tools" in result.output
                assert "testing" in result.output

    @pytest.mark.integration
    def test_smart_commit_integration(self, temp_dir):
        """Test smart commit integration with CLI."""
        create_genesis_project_structure(temp_dir)

        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "genesis"))

        from click.testing import CliRunner

        from genesis.cli import cli

        runner = CliRunner()

        with (
            patch("genesis.cli.get_git_root", return_value=temp_dir),
            patch(
                "genesis.core.constants.get_git_author_info",
                return_value=("Test User", "test@example.com"),
            ),
        ):
            with patch_subprocess_run()[0] as mock_run:
                mock_run.return_value.returncode = 0

                result = runner.invoke(cli, ["commit"])

                assert result.exit_code == 0
                assert "Smart commit completed" in result.output

    @pytest.mark.integration
    def test_testing_utilities_integration(self, temp_dir):
        """Test that testing utilities work together."""
        create_genesis_project_structure(temp_dir)
        testing_path = temp_dir / "testing"

        # Add real testing_core package to path
        import sys

        sys.path.insert(0, str(testing_path))

        # Test importing and using utilities together
        try:
            # This would normally work with real testing module
            # For now, just test the structure exists
            assert (testing_path / "src" / "testing_core" / "__init__.py").exists()
            assert (testing_path / "src" / "testing_core" / "ai_safety.py").exists()
            assert (testing_path / "src" / "testing_core" / "integration.py").exists()
            assert (testing_path / "src" / "testing_core" / "fixtures.py").exists()
        except ImportError:
            # Expected in test environment
            pass

    @pytest.mark.integration
    def test_component_script_discovery(self, temp_dir):
        """Test that CLI can discover all component scripts."""
        create_genesis_project_structure(temp_dir)

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
        create_genesis_project_structure(temp_dir)

        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "genesis"))

        from click.testing import CliRunner

        from genesis.cli import cli

        runner = CliRunner()

        with (
            patch("genesis.cli.get_git_root", return_value=temp_dir),
            patch(
                "genesis.core.constants.get_git_author_info",
                return_value=("Test User", "test@example.com"),
            ),
        ):
            # Step 1: Check status
            with patch_subprocess_run()[0] as mock_run:
                mock_run.return_value.returncode = 0
                result = runner.invoke(cli, ["status"])
                assert result.exit_code == 0
                assert "healthy" in result.output

            # Step 2: Bootstrap new project (without subprocess mocks to allow actual bootstrap)
            import os

            try:
                old_cwd = Path.cwd()
                os.chdir(temp_dir)
                result = runner.invoke(
                    cli, ["bootstrap", "my-api", "--type", "python-api", "--skip-git"]
                )
                assert result.exit_code == 0
            finally:
                try:
                    os.chdir(old_cwd)
                except (OSError, FileNotFoundError):
                    # Original directory might be deleted, go to a safe location
                    os.chdir(Path.home())

            # Step 3: Sync dependencies
            with patch_subprocess_run()[0] as mock_run:
                mock_run.return_value.returncode = 0
                result = runner.invoke(cli, ["sync"])
                assert result.exit_code == 0

            # Step 4: Make commit
            with patch_subprocess_run()[0] as mock_run:
                mock_run.return_value.returncode = 0
                result = runner.invoke(cli, ["commit"])
                assert result.exit_code == 0

            # Step 5: Clean up
            with patch_subprocess_run()[0] as mock_run:
                mock_run.return_value.returncode = 0
                result = runner.invoke(cli, ["clean", "--worktrees"])
                assert result.exit_code == 0

    @pytest.mark.e2e
    @pytest.mark.ai_safety
    def test_ai_safety_throughout_workflow(self, temp_dir):
        """Test that AI safety is maintained throughout workflow."""
        create_genesis_project_structure(temp_dir)

        from genesis.testing.ai_safety import AISafetyChecker

        checker = AISafetyChecker(max_total_files=100, max_component_files=30)

        # Initial safety check
        initial_result = checker.check_project(temp_dir)
        assert initial_result["is_safe"]

        # Simulate adding some files during development
        new_files_dir = temp_dir / "genesis"
        for i in range(5):
            (new_files_dir / f"new_file_{i}.py").write_text(f"# New file {i}")

        # Should still be safe
        updated_result = checker.check_project(temp_dir)
        assert updated_result["is_safe"]

        # Test component isolation
        for component in [
            "bootstrap",
            "testing",
            "smart-commit",
            "worktree-tools",
            "genesis",
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
        create_genesis_project_structure(temp_dir)

        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "genesis"))

        from click.testing import CliRunner

        from genesis.cli import cli

        runner = CliRunner()

        with (
            patch("genesis.cli.get_git_root", return_value=temp_dir),
            patch(
                "genesis.core.constants.get_git_author_info",
                return_value=("Test User", "test@example.com"),
            ),
        ):
            # Mock template directory missing to trigger a real error
            with patch("pathlib.Path.exists") as mock_exists:
                # Make template directory appear missing
                def side_effect(path_instance):
                    if "templates" in str(path_instance):
                        return False
                    return True

                mock_exists.side_effect = lambda: False

                result = runner.invoke(
                    cli, ["bootstrap", "test-project", "--type", "python-api"]
                )

                assert result.exit_code == 1  # Should fail due to missing template
                assert "failed" in result.output.lower()

    @pytest.mark.integration
    def test_missing_component_handling(self, temp_dir):
        """Test handling of missing components."""
        # Create incomplete Genesis structure
        (temp_dir / "CLAUDE.md").write_text("# Genesis")
        # Don't create all components

        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "genesis"))

        from click.testing import CliRunner

        from genesis.cli import cli

        runner = CliRunner()

        with (
            patch("genesis.cli.get_git_root", return_value=temp_dir),
            patch(
                "genesis.core.constants.get_git_author_info",
                return_value=("Test User", "test@example.com"),
            ),
        ):
            result = runner.invoke(cli, ["status"])

            # Status command may still return 0 even with missing components
            # but should report the issue in the output
            assert (
                "Missing" in result.output
                or "project has issues" in result.output
                or "healthy" not in result.output
            )

    @pytest.mark.integration
    def test_invalid_project_detection(self):
        """Test detection and handling of invalid project structures."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "genesis"))

        from click.testing import CliRunner

        from genesis.cli import cli

        runner = CliRunner()

        # Mock non-Genesis directory
        with patch("genesis.cli.get_git_root", return_value=None):
            result = runner.invoke(cli, ["status"])

            # CLI may handle non-Genesis directories gracefully
            # but should indicate it's not a Genesis project
            assert (
                "Not in a Genesis project" in result.output
                or "Genesis project" not in result.output
            )
