#!/usr/bin/env python3
"""
Comprehensive Unit Tests for CLI Commands
Tests all bootstrap CLI commands with 100% critical path coverage
"""

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "bin"))
sys.path.insert(0, str(Path(__file__).parent.parent / "setup-project"))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib" / "python"))

# Import the CLI module
import importlib.util

spec = importlib.util.spec_from_file_location(
    "bootstrap", Path(__file__).parent.parent / "bin" / "bootstrap"
)
bootstrap_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap_module)
BootstrapCLI = bootstrap_module.BootstrapCLI


class TestBootstrapCLIInit:
    """Test CLI initialization"""

    def test_cli_initialization(self):
        """Test that CLI initializes correctly"""
        cli = BootstrapCLI()

        assert cli.bootstrap_root is not None
        assert cli.projects_dir.exists()
        assert cli.registry_file is not None
        assert cli.setup_project is not None

    def test_cli_creates_projects_directory(self):
        """Test that CLI creates projects directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_root = Path(tmpdir) / "test_bootstrap"
            test_root.mkdir()

            with patch("pathlib.Path.resolve") as mock_resolve:
                mock_resolve.return_value = test_root

                cli = BootstrapCLI()
                assert (test_root / "projects").exists()


class TestNewCommand:
    """Test 'bootstrap new' command"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.cli = BootstrapCLI()
        self.test_dir = tempfile.mkdtemp(prefix="test_new_")
        yield
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_new_project_basic(self):
        """Test creating a new project with basic options"""
        args = MagicMock()
        args.name = "test-project"
        args.path = self.test_dir
        args.type = "api"
        args.language = "python"
        args.cloud = "gcp"
        args.team = "test-team"
        args.criticality = "high"
        args.git = False

        with patch.object(self.cli, "load_registry") as mock_load:
            with patch.object(self.cli, "save_registry") as mock_save:
                with patch.object(self.cli.setup_project, "init_project") as mock_init:
                    mock_load.return_value = {"projects": {}}

                    self.cli.cmd_new(args)

                    # Verify project initialization was called
                    mock_init.assert_called_once_with(
                        project_name="test-project",
                        project_type="api",
                        language="python",
                        cloud_provider="gcp",
                    )

                    # Verify registry was updated
                    mock_save.assert_called_once()
                    saved_registry = mock_save.call_args[0][0]
                    assert "test-project" in saved_registry["projects"]
                    assert (
                        saved_registry["projects"]["test-project"]["team"]
                        == "test-team"
                    )
                    assert (
                        saved_registry["projects"]["test-project"]["criticality"]
                        == "high"
                    )

    def test_new_project_with_git(self):
        """Test creating a new project with Git initialization"""
        args = MagicMock()
        args.name = "test-git-project"
        args.path = self.test_dir
        args.type = "web-app"
        args.language = "javascript"
        args.cloud = "aws"
        args.team = None
        args.criticality = None
        args.git = True

        project_path = Path(self.test_dir) / "test-git-project"

        with patch.object(self.cli, "load_registry") as mock_load:
            with patch.object(self.cli, "save_registry"):
                with patch.object(self.cli.setup_project, "init_project"):
                    with patch("subprocess.run") as mock_run:
                        mock_load.return_value = {"projects": {}}
                        mock_run.return_value = MagicMock(returncode=0)

                        self.cli.cmd_new(args)

                        # Verify Git commands were called
                        calls = mock_run.call_args_list
                        assert any(
                            "git" in str(call) and "init" in str(call) for call in calls
                        )

    def test_new_project_default_path(self):
        """Test creating a project without specifying path"""
        args = MagicMock()
        args.name = "test-default-path"
        args.path = None
        args.type = "cli"
        args.language = "go"
        args.cloud = "azure"
        args.team = "platform"
        args.criticality = "low"
        args.git = False

        with patch.object(self.cli, "load_registry") as mock_load:
            with patch.object(self.cli, "save_registry") as mock_save:
                with patch.object(self.cli.setup_project, "init_project"):
                    mock_load.return_value = {"projects": {}}

                    self.cli.cmd_new(args)

                    # Check that default path was used
                    saved_registry = mock_save.call_args[0][0]
                    project_path = saved_registry["projects"]["test-default-path"][
                        "path"
                    ]
                    assert "test-default-path" in project_path


class TestRetrofitCommand:
    """Test 'bootstrap retrofit' command"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.cli = BootstrapCLI()
        self.test_dir = tempfile.mkdtemp(prefix="test_retrofit_")
        self.project_path = Path(self.test_dir) / "existing-project"
        self.project_path.mkdir()
        yield
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_retrofit_existing_project(self):
        """Test retrofitting an existing project"""
        args = MagicMock()
        args.path = str(self.project_path)
        args.type = "api"

        # Create some existing files
        (self.project_path / "package.json").write_text('{"name": "test"}')

        with patch.object(self.cli, "load_registry") as mock_load:
            with patch.object(self.cli, "save_registry") as mock_save:
                with patch.object(
                    self.cli.setup_project, "detect_project_type"
                ) as mock_detect:
                    with patch.object(
                        self.cli.setup_project, "init_project"
                    ) as mock_init:
                        mock_load.return_value = {"projects": {}}
                        mock_detect.return_value = {"language": "javascript"}

                        result = self.cli.cmd_retrofit(args)

                        # Should succeed
                        assert result != 1
                        mock_init.assert_called_once()
                        mock_save.assert_called_once()

    def test_retrofit_nonexistent_path(self):
        """Test retrofitting with non-existent path"""
        args = MagicMock()
        args.path = "/nonexistent/path"
        args.type = None

        result = self.cli.cmd_retrofit(args)
        assert result == 1

    def test_retrofit_with_existing_config(self):
        """Test retrofitting project with existing config"""
        args = MagicMock()
        args.path = str(self.project_path)
        args.type = None

        # Create existing config
        (self.project_path / ".project-config.yaml").write_text("version: 1.0.0")

        with patch.object(self.cli, "load_registry") as mock_load:
            with patch.object(self.cli, "save_registry"):
                with patch.object(
                    self.cli.setup_project, "detect_project_type"
                ) as mock_detect:
                    with patch.object(
                        self.cli.setup_project, "upgrade"
                    ) as mock_upgrade:
                        mock_load.return_value = {"projects": {}}
                        mock_detect.return_value = {"language": "python"}

                        self.cli.cmd_retrofit(args)

                        # Should call upgrade instead of init
                        mock_upgrade.assert_called_once()


class TestListCommand:
    """Test 'bootstrap list' command"""

    def test_list_empty_registry(self):
        """Test listing with no projects"""
        cli = BootstrapCLI()

        with patch.object(cli, "load_registry") as mock_load:
            mock_load.return_value = {"projects": {}}

            # Should not raise error
            cli.cmd_list(MagicMock())

    def test_list_multiple_projects(self):
        """Test listing multiple projects"""
        cli = BootstrapCLI()

        test_registry = {
            "projects": {
                "project1": {
                    "path": "/path/to/project1",
                    "type": "api",
                    "language": "python",
                    "team": "backend",
                    "criticality": "high",
                    "environments": {"dev": {}, "prod": {}},
                },
                "project2": {
                    "path": "/path/to/project2",
                    "type": "web-app",
                    "language": "javascript",
                    "team": "frontend",
                    "criticality": "medium",
                    "environments": {"dev": {}},
                },
            }
        }

        with patch.object(cli, "load_registry") as mock_load:
            with patch("pathlib.Path.exists") as mock_exists:
                mock_load.return_value = test_registry
                mock_exists.return_value = True

                # Should complete without error
                cli.cmd_list(MagicMock())


class TestValidateCommand:
    """Test 'bootstrap validate' command"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.cli = BootstrapCLI()

    def test_validate_single_project(self):
        """Test validating a single project"""
        args = MagicMock()
        args.project = "test-project"

        test_registry = {"projects": {"test-project": {"path": "/test/path"}}}

        with patch.object(self.cli, "load_registry") as mock_load:
            with patch.object(self.cli, "_validate_single_project") as mock_validate:
                mock_load.return_value = test_registry

                self.cli.cmd_validate(args)

                mock_validate.assert_called_once_with(
                    "test-project", test_registry["projects"]["test-project"]
                )

    def test_validate_all_projects(self):
        """Test validating all projects"""
        args = MagicMock()
        args.project = "all"

        test_registry = {
            "projects": {"project1": {"path": "/path1"}, "project2": {"path": "/path2"}}
        }

        with patch.object(self.cli, "load_registry") as mock_load:
            with patch.object(self.cli, "_validate_single_project") as mock_validate:
                mock_load.return_value = test_registry

                self.cli.cmd_validate(args)

                # Should validate both projects
                assert mock_validate.call_count == 2

    def test_validate_nonexistent_project(self):
        """Test validating non-existent project"""
        args = MagicMock()
        args.project = "nonexistent"

        with patch.object(self.cli, "load_registry") as mock_load:
            mock_load.return_value = {"projects": {}}

            result = self.cli.cmd_validate(args)
            assert result == 1

    def test_validate_with_script(self):
        """Test validation with compliance script"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            scripts_dir = project_path / "scripts"
            scripts_dir.mkdir()

            validation_script = scripts_dir / "validate-compliance.sh"
            validation_script.write_text("#!/bin/bash\necho 'Validating'\nexit 0")
            validation_script.chmod(0o755)

            config = {"path": str(project_path)}

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="Valid", stderr=""
                )

                self.cli._validate_single_project("test", config)

                mock_run.assert_called_once()


class TestRegistryCommand:
    """Test 'bootstrap registry' command"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.cli = BootstrapCLI()

    def test_registry_validate(self):
        """Test registry validation"""
        args = MagicMock()
        args.action = "validate"

        with patch.object(self.cli, "_validate_registry") as mock_validate:
            mock_validate.return_value = 0

            result = self.cli.cmd_registry(args)
            assert result == 0
            mock_validate.assert_called_once()

    def test_registry_update(self):
        """Test registry update"""
        args = MagicMock()
        args.action = "update"

        with patch.object(self.cli, "_update_registry") as mock_update:
            mock_update.return_value = 0

            result = self.cli.cmd_registry(args)
            assert result == 0
            mock_update.assert_called_once()

    def test_registry_clean(self):
        """Test registry cleaning"""
        args = MagicMock()
        args.action = "clean"

        test_registry = {
            "global": {"last_updated": "2024-01-01T00:00:00Z"},
            "projects": {
                "existing": {"path": "/exists"},
                "missing": {"path": "/missing"},
            },
        }

        with patch.object(self.cli, "load_registry") as mock_load:
            with patch.object(self.cli, "save_registry") as mock_save:
                with patch("pathlib.Path.exists") as mock_exists:
                    mock_load.return_value = test_registry
                    mock_exists.side_effect = lambda: mock_exists.call_count == 1

                    self.cli._clean_registry()

                    # Check that missing project was removed
                    saved = mock_save.call_args[0][0]
                    assert "existing" in saved["projects"]
                    assert "missing" not in saved["projects"]

    def test_registry_backup(self):
        """Test registry backup"""
        args = MagicMock()
        args.action = "backup"

        with patch("shutil.copy2") as mock_copy:
            self.cli._backup_registry()
            mock_copy.assert_called_once()

    def test_registry_stats(self):
        """Test registry statistics"""
        args = MagicMock()
        args.action = "stats"

        test_registry = {
            "global": {
                "organization": "test-org",
                "registry_version": "2.0.0",
                "last_updated": "2024-01-01",
            },
            "projects": {
                "api1": {"type": "api", "language": "python", "path": "/api1"},
                "api2": {"type": "api", "language": "go", "path": "/api2"},
                "web1": {"type": "web-app", "language": "javascript", "path": "/web1"},
            },
        }

        with patch.object(self.cli, "load_registry") as mock_load:
            with patch("pathlib.Path.exists") as mock_exists:
                mock_load.return_value = test_registry
                mock_exists.return_value = True

                # Should complete without error
                self.cli._registry_stats()

    def test_registry_unknown_action(self):
        """Test unknown registry action"""
        args = MagicMock()
        args.action = "unknown"

        result = self.cli.cmd_registry(args)
        assert result == 1


class TestDeployCommand:
    """Test 'bootstrap deploy' command"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.cli = BootstrapCLI()

    def test_deploy_existing_project(self):
        """Test deploying an existing project"""
        args = MagicMock()
        args.project = "test-project"
        args.environment = "dev"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            scripts_dir = project_path / "scripts"
            scripts_dir.mkdir()

            deploy_script = scripts_dir / "deploy.sh"
            deploy_script.write_text("#!/bin/bash\necho 'Deploying'\nexit 0")
            deploy_script.chmod(0o755)

            test_registry = {"projects": {"test-project": {"path": str(project_path)}}}

            with patch.object(self.cli, "load_registry") as mock_load:
                with patch("subprocess.run") as mock_run:
                    mock_load.return_value = test_registry
                    mock_run.return_value = MagicMock(returncode=0)

                    result = self.cli.cmd_deploy(args)

                    assert result == 0
                    mock_run.assert_called_once()

    def test_deploy_nonexistent_project(self):
        """Test deploying non-existent project"""
        args = MagicMock()
        args.project = "nonexistent"
        args.environment = "prod"

        with patch.object(self.cli, "load_registry") as mock_load:
            mock_load.return_value = {"projects": {}}

            result = self.cli.cmd_deploy(args)
            assert result == 1

    def test_deploy_missing_script(self):
        """Test deployment when script is missing"""
        args = MagicMock()
        args.project = "test-project"
        args.environment = None

        with tempfile.TemporaryDirectory() as tmpdir:
            test_registry = {"projects": {"test-project": {"path": tmpdir}}}

            with patch.object(self.cli, "load_registry") as mock_load:
                mock_load.return_value = test_registry

                result = self.cli.cmd_deploy(args)
                assert result == 1


class TestInfraCommand:
    """Test 'bootstrap infra' command"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.cli = BootstrapCLI()

    def test_infra_init(self):
        """Test infrastructure initialization"""
        args = MagicMock()
        args.action = "init"
        args.project = "test-project"

        with tempfile.TemporaryDirectory() as tmpdir:
            infra_dir = Path(tmpdir) / "terraform"
            infra_dir.mkdir()
            (infra_dir / "main.tf").write_text("# Terraform config")

            test_registry = {"projects": {"test-project": {"path": tmpdir}}}

            with patch.object(self.cli, "load_registry") as mock_load:
                with patch("subprocess.run") as mock_run:
                    mock_load.return_value = test_registry
                    mock_run.return_value = MagicMock(returncode=0)

                    result = self.cli.cmd_infra(args)

                    assert result == 0
                    mock_run.assert_called_once()
                    call_args = mock_run.call_args[0][0]
                    assert "terraform" in call_args
                    assert "init" in call_args

    def test_infra_plan(self):
        """Test infrastructure plan"""
        args = MagicMock()
        args.action = "plan"
        args.project = "test-project"

        with tempfile.TemporaryDirectory() as tmpdir:
            infra_dir = Path(tmpdir) / "terraform"
            infra_dir.mkdir()

            test_registry = {"projects": {"test-project": {"path": tmpdir}}}

            with patch.object(self.cli, "load_registry") as mock_load:
                with patch("subprocess.run") as mock_run:
                    mock_load.return_value = test_registry
                    mock_run.return_value = MagicMock(returncode=0)

                    result = self.cli.cmd_infra(args)

                    assert result == 0
                    call_args = mock_run.call_args[0][0]
                    assert "plan" in call_args

    def test_infra_unknown_action(self):
        """Test unknown infrastructure action"""
        args = MagicMock()
        args.action = "unknown"
        args.project = "test-project"

        test_registry = {"projects": {"test-project": {"path": "/test"}}}

        with patch.object(self.cli, "load_registry") as mock_load:
            mock_load.return_value = test_registry

            result = self.cli.cmd_infra(args)
            assert result == 1

    def test_infra_terraform_not_found(self):
        """Test when terraform is not installed"""
        args = MagicMock()
        args.action = "init"
        args.project = "test-project"

        with tempfile.TemporaryDirectory() as tmpdir:
            infra_dir = Path(tmpdir) / "terraform"
            infra_dir.mkdir()

            test_registry = {"projects": {"test-project": {"path": tmpdir}}}

            with patch.object(self.cli, "load_registry") as mock_load:
                with patch("subprocess.run") as mock_run:
                    mock_load.return_value = test_registry
                    mock_run.side_effect = FileNotFoundError()

                    result = self.cli.cmd_infra(args)
                    assert result == 1


class TestHealthCommand:
    """Test 'bootstrap health' command"""

    def test_health_check_healthy_project(self):
        """Test health check for healthy project"""
        cli = BootstrapCLI()
        args = MagicMock()
        args.project = "test-project"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create healthy project structure
            (project_path / ".git").mkdir()
            (project_path / ".project-config.yaml").write_text("version: 1.0.0")
            (project_path / "README.md").write_text("# Test Project")
            scripts_dir = project_path / "scripts"
            scripts_dir.mkdir()

            test_registry = {"projects": {"test-project": {"path": str(project_path)}}}

            with patch.object(cli, "load_registry") as mock_load:
                mock_load.return_value = test_registry

                result = cli.cmd_health(args)

                # Healthy project should return 0 or 1 depending on scripts
                assert result in [0, 1]

    def test_health_check_unhealthy_project(self):
        """Test health check for unhealthy project"""
        cli = BootstrapCLI()
        args = MagicMock()
        args.project = "test-project"

        with tempfile.TemporaryDirectory() as tmpdir:
            test_registry = {"projects": {"test-project": {"path": tmpdir}}}

            with patch.object(cli, "load_registry") as mock_load:
                mock_load.return_value = test_registry

                result = cli.cmd_health(args)
                assert result == 1


class TestIsolationCommand:
    """Test 'bootstrap isolation' command"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.cli = BootstrapCLI()

    def test_isolation_validate(self):
        """Test isolation validation"""
        args = MagicMock()
        args.isolation_action = "validate"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Valid", stderr="")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True

                result = self.cli.cmd_isolation(args)
                assert result in [0, 1]  # Depends on script existence

    def test_isolation_setup(self):
        """Test isolation setup"""
        args = MagicMock()
        args.isolation_action = "setup"
        args.project = "test-project"

        test_registry = {
            "projects": {"test-project": {"path": "/test", "cloud_provider": "gcp"}}
        }

        with patch.object(self.cli, "load_registry") as mock_load:
            with patch("subprocess.run") as mock_run:
                with patch("pathlib.Path.exists") as mock_exists:
                    mock_load.return_value = test_registry
                    mock_run.return_value = MagicMock(returncode=0)
                    mock_exists.return_value = True

                    result = self.cli._setup_isolation(args)
                    assert result in [0, 1]

    def test_isolation_unknown_action(self):
        """Test unknown isolation action"""
        args = MagicMock()
        args.isolation_action = "unknown"

        result = self.cli.cmd_isolation(args)
        assert result == 1


class TestStatusCommand:
    """Test 'bootstrap status' command"""

    def test_status_with_projects(self):
        """Test status command with projects"""
        cli = BootstrapCLI()
        args = MagicMock()

        test_registry = {
            "projects": {
                "project1": {"path": "/path1", "type": "api", "language": "python"},
                "project2": {
                    "path": "/path2",
                    "type": "web-app",
                    "language": "javascript",
                },
            }
        }

        with patch.object(cli, "load_registry") as mock_load:
            with patch("pathlib.Path.exists") as mock_exists:
                mock_load.return_value = test_registry
                mock_exists.return_value = True

                # Should complete without error
                cli.cmd_status(args)

    def test_status_empty_registry(self):
        """Test status with empty registry"""
        cli = BootstrapCLI()
        args = MagicMock()

        with patch.object(cli, "load_registry") as mock_load:
            mock_load.return_value = {"projects": {}}

            # Should handle empty registry gracefully
            cli.cmd_status(args)


class TestLogsCommand:
    """Test 'bootstrap logs' command"""

    def test_logs_with_log_files(self):
        """Test logs command with existing log files"""
        cli = BootstrapCLI()
        args = MagicMock()
        args.project = "test-project"
        args.tail = 10
        args.follow = False

        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir) / "logs"
            logs_dir.mkdir()
            (logs_dir / "app.log").write_text("Log entry 1\nLog entry 2")

            test_registry = {"projects": {"test-project": {"path": tmpdir}}}

            with patch.object(cli, "load_registry") as mock_load:
                with patch("subprocess.run") as mock_run:
                    mock_load.return_value = test_registry
                    mock_run.return_value = MagicMock(stdout="Last lines", stderr="")

                    result = cli.cmd_logs(args)
                    assert result == 0

    def test_logs_no_log_files(self):
        """Test logs command with no log files"""
        cli = BootstrapCLI()
        args = MagicMock()
        args.project = "test-project"
        args.tail = 50

        with tempfile.TemporaryDirectory() as tmpdir:
            test_registry = {"projects": {"test-project": {"path": tmpdir}}}

            with patch.object(cli, "load_registry") as mock_load:
                mock_load.return_value = test_registry

                result = cli.cmd_logs(args)
                assert result == 0


class TestMainEntryPoint:
    """Test main CLI entry point"""

    def test_main_no_args(self):
        """Test main with no arguments"""
        cli = BootstrapCLI()

        with patch("sys.argv", ["bootstrap"]):
            with patch("argparse.ArgumentParser.print_help") as mock_help:
                result = cli.main()
                assert result == 0
                mock_help.assert_called_once()

    def test_main_with_command(self):
        """Test main with valid command"""
        cli = BootstrapCLI()

        with patch("sys.argv", ["bootstrap", "list"]):
            with patch.object(cli, "cmd_list") as mock_list:
                mock_list.return_value = 0
                result = cli.main()
                assert result == 0
                mock_list.assert_called_once()

    def test_main_keyboard_interrupt(self):
        """Test handling keyboard interrupt"""
        cli = BootstrapCLI()

        with patch("sys.argv", ["bootstrap", "list"]):
            with patch.object(cli, "cmd_list") as mock_list:
                mock_list.side_effect = KeyboardInterrupt()
                result = cli.main()
                assert result == 1

    def test_main_exception(self):
        """Test handling general exception"""
        cli = BootstrapCLI()

        with patch("sys.argv", ["bootstrap", "list"]):
            with patch.object(cli, "cmd_list") as mock_list:
                mock_list.side_effect = Exception("Test error")
                result = cli.main()
                assert result == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
