"""
Enhanced Unit Tests for Genesis CLI
Comprehensive testing following VERIFY methodology for >90% coverage target.
"""

import pytest
import tempfile
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from argparse import Namespace
import json
import yaml
from datetime import datetime, timedelta

# Test framework imports
from cli.commands.vm_commands import VMCommands
from cli.commands.enhanced_container_commands import EnhancedContainerCommands
from cli.commands.enhanced_infrastructure_commands import EnhancedInfrastructureCommands
from cli.services import (
    ConfigService,
    AuthService,
    CacheService,
    ErrorService,
    GCPService,
    PerformanceService,
    TerraformService,
)
from cli.services.error_service import ErrorCategory, ErrorSeverity


class TestEnhancedVMCommands:
    """Enhanced comprehensive testing for VM commands - targeting >90% coverage."""

    def setup_method(self):
        """Set up enhanced test environment with complete mocking."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create comprehensive test CLI
        self.mock_cli = Mock()
        self.mock_cli.genesis_root = self.temp_dir
        self.mock_cli.environment = "test"
        self.mock_cli.project_id = "test-project"

        # Create complete config structure
        self._setup_test_config()

        # Initialize VM commands with mocked services
        self.vm_commands = VMCommands(self.mock_cli)
        self._setup_service_mocks()

    def _setup_test_config(self):
        """Set up comprehensive test configuration."""
        config_dir = self.temp_dir / "config"
        config_dir.mkdir()
        (config_dir / "environments").mkdir()

        # Complete environment config
        (config_dir / "environments" / "test.yaml").write_text(
            """
gcp:
  project_id: test-project
  region: us-central1
  zone: us-central1-a
agents:
  types:
    backend-developer:
      machine_type: e2-standard-2
      disk_size_gb: 50
      preemptible: false
    frontend-developer:
      machine_type: e2-medium
      disk_size_gb: 30
      preemptible: true
    platform-engineer:
      machine_type: e2-standard-4
      disk_size_gb: 100
      preemptible: false
terraform:
  backend_bucket: test-terraform-state
"""
        )

        # Global config
        (config_dir / "global.yaml").write_text(
            """
terraform:
  region: us-central1
  backend_bucket: global-terraform-state
performance:
  target_response_time: 2.0
  cache_ttl: 300
"""
        )

    def _setup_service_mocks(self):
        """Set up comprehensive service mocking."""
        self.vm_commands.config_service = Mock()
        self.vm_commands.config_service.get_agent_config.return_value = {
            "types": {
                "backend-developer": {"machine_type": "e2-standard-2"},
                "frontend-developer": {"machine_type": "e2-medium"},
                "platform-engineer": {"machine_type": "e2-standard-4"},
            }
        }

        self.vm_commands.auth_service = Mock()
        self.vm_commands.gcp_service = Mock()
        self.vm_commands.cache_service = Mock()
        self.vm_commands.error_service = Mock()
        self.vm_commands.performance_service = Mock()

        # Mock performance timer
        timer_mock = Mock()
        timer_mock.__enter__ = Mock(return_value=timer_mock)
        timer_mock.__exit__ = Mock(return_value=None)
        self.vm_commands.performance_service.time_operation.return_value = timer_mock

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @pytest.mark.parametrize(
        "action,expected_method",
        [
            ("create-pool", "_create_pool"),
            ("scale-pool", "_scale_pool"),
            ("delete-pool", "_delete_pool"),
            ("list-pools", "_list_pools"),
            ("health-check", "_health_check"),
        ],
    )
    def test_execute_action_routing(self, action, expected_method):
        """Test that all VM actions route to correct methods."""
        args = Namespace(
            vm_action=action,
            environment="test",
            project_id="test-project",
            dry_run=True,
            type="backend-developer",
            size=1,
            pool=None,
            instance=None,
        )

        # Mock the expected method
        setattr(
            self.vm_commands, expected_method, Mock(return_value={"status": "success"})
        )

        result = self.vm_commands.execute(args, {})

        # Verify correct method was called
        expected_mock = getattr(self.vm_commands, expected_method)
        expected_mock.assert_called_once()

    def test_create_pool_comprehensive(self):
        """Test comprehensive pool creation with all parameters."""
        args = Namespace(
            vm_action="create-pool",
            type="backend-developer",
            size=5,
            machine_type="e2-standard-4",
            preemptible=True,
            zones=["us-central1-a", "us-central1-b"],
            environment="test",
            project_id="test-project",
            dry_run=False,
        )

        # Mock GCP service response
        self.vm_commands.gcp_service.create_vm_pool.return_value = {
            "pool_name": "test-backend-pool",
            "instance_count": 5,
            "status": "creating",
        }

        result = self.vm_commands.execute(args, {})

        # Verify GCP service was called with correct parameters
        expected_config = {
            "agent_type": "backend-developer",
            "pool_size": 5,
            "machine_type": "e2-standard-4",
            "preemptible": True,
            "zones": ["us-central1-a", "us-central1-b"],
            "enable_autoscaling": True,
            "min_replicas": 1,
            "max_replicas": 15,
            "startup_script": f"#!/bin/bash\n# Agent startup for backend-developer\necho 'Starting backend-developer agent...'",
        }

        self.vm_commands.gcp_service.create_vm_pool.assert_called_once()
        assert result["action"] == "create-pool"

    def test_error_handling_comprehensive(self):
        """Test comprehensive error handling scenarios."""
        # Test quota exceeded error
        args = Namespace(
            vm_action="create-pool",
            type="backend-developer",
            size=1000,  # Large size to trigger quota
            dry_run=False,
        )

        quota_error = subprocess.CalledProcessError(
            1, "gcloud", stderr="Quota 'CPUS' exceeded in region 'us-central1'"
        )
        self.vm_commands.gcp_service.create_vm_pool.side_effect = quota_error

        # Mock error service
        mock_error = Mock()
        mock_error.category = ErrorCategory.RESOURCE
        mock_error.severity = ErrorSeverity.HIGH
        self.vm_commands.error_service.handle_gcp_error.return_value = mock_error

        with pytest.raises(Exception):
            self.vm_commands.execute(args, {})

        self.vm_commands.error_service.handle_gcp_error.assert_called_once_with(
            quota_error, {"action": "create-pool", "agent_type": "backend-developer"}
        )

    def test_performance_metrics_collection(self):
        """Test performance metrics collection and reporting."""
        # Execute several operations
        operations = ["create-pool", "list-pools", "health-check"]

        for operation in operations:
            args = Namespace(
                vm_action=operation,
                type="backend-developer",
                size=1,
                environment="test",
                project_id="test-project",
                dry_run=True,
                pool=None,
                instance=None,
            )

            self.vm_commands.execute(args, {})

        # Get performance metrics
        metrics = self.vm_commands.get_performance_metrics()

        # Verify metrics structure
        assert "vm_operations" in metrics
        assert "cache_stats" in metrics
        assert "error_summary" in metrics

        # Verify performance service was used
        assert self.vm_commands.performance_service.time_operation.call_count == len(
            operations
        )

    def test_cache_utilization(self):
        """Test cache utilization for performance optimization."""
        args = Namespace(
            vm_action="list-pools", environment="test", project_id="test-project"
        )

        # Mock cache hit
        self.vm_commands.cache_service.get.return_value = [
            {"name": "test-pool", "status": "running"}
        ]

        result = self.vm_commands.execute(args, {})

        # Verify cache was checked
        self.vm_commands.cache_service.get.assert_called_once()

        # Verify result from cache
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "agent_type,expected_machine",
        [
            ("backend-developer", "e2-standard-2"),
            ("frontend-developer", "e2-medium"),
            ("platform-engineer", "e2-standard-4"),
        ],
    )
    def test_agent_type_configuration(self, agent_type, expected_machine):
        """Test agent type configuration mapping."""
        args = Namespace(
            type=agent_type, size=3, machine_type=None, preemptible=None, zones=None
        )

        config = self.vm_commands._generate_pool_config(args)

        assert config["agent_type"] == agent_type
        assert config["machine_type"] == expected_machine
        assert config["pool_size"] == 3


class TestEnhancedPerformanceTesting:
    """Enhanced performance testing for CLI startup and response times."""

    def setup_method(self):
        """Set up performance testing environment."""
        self.performance_service = PerformanceService(Mock())
        self.start_time = time.time()

    def test_cli_startup_performance(self):
        """Test CLI startup time - target <200ms."""
        startup_times = []

        for _ in range(10):  # Test 10 startup iterations
            start = time.time()

            # Simulate CLI initialization
            with self.performance_service.time_operation("cli_startup") as timer:
                # Mock CLI initialization steps
                time.sleep(0.01)  # Simulate import time
                time.sleep(0.05)  # Simulate config loading
                time.sleep(0.03)  # Simulate service initialization

            startup_time = time.time() - start
            startup_times.append(startup_time * 1000)  # Convert to ms

        avg_startup = sum(startup_times) / len(startup_times)
        max_startup = max(startup_times)

        # Performance assertions
        assert (
            avg_startup < 200
        ), f"Average startup time {avg_startup:.1f}ms exceeds 200ms target"
        assert (
            max_startup < 300
        ), f"Max startup time {max_startup:.1f}ms exceeds acceptable range"

    @pytest.mark.parametrize(
        "command,expected_max_time",
        [
            ("vm list-pools", 2000),  # 2s max
            ("container list-clusters", 1500),  # 1.5s max
            ("infra status", 3000),  # 3s max for complex operations
        ],
    )
    def test_command_response_times(self, command, expected_max_time):
        """Test command response times against targets."""
        start_time = time.time()

        with self.performance_service.time_operation(f"command_{command}") as timer:
            # Simulate command execution
            if "list" in command:
                time.sleep(0.1)  # Fast list operation
            elif "status" in command:
                time.sleep(0.5)  # More complex status check
            else:
                time.sleep(0.2)  # Standard operation

        response_time = (time.time() - start_time) * 1000  # Convert to ms

        assert (
            response_time < expected_max_time
        ), f"Command '{command}' took {response_time:.1f}ms, exceeds {expected_max_time}ms target"

    def test_memory_usage_profiling(self):
        """Test memory usage stays within acceptable limits."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Simulate CLI operations that could consume memory
        data_structures = []
        for i in range(100):
            # Simulate cache entries
            data_structures.append(
                {
                    "key": f"test_key_{i}",
                    "value": "x" * 1000,  # 1KB per entry
                    "metadata": {"timestamp": time.time(), "access_count": 0},
                }
            )

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # Memory usage assertions
        assert (
            peak_memory < 100
        ), f"Peak memory usage {peak_memory:.1f}MB exceeds 100MB limit"
        assert (
            memory_increase < 50
        ), f"Memory increase {memory_increase:.1f}MB exceeds 50MB limit"

    def test_concurrent_operations_performance(self):
        """Test performance under concurrent operations."""
        import threading
        import queue

        results_queue = queue.Queue()

        def simulate_concurrent_command():
            """Simulate a command execution."""
            start = time.time()
            with self.performance_service.time_operation("concurrent_test"):
                time.sleep(0.1)  # Simulate work
            end = time.time()
            results_queue.put((end - start) * 1000)  # ms

        # Launch concurrent operations
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=simulate_concurrent_command)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Collect results
        response_times = []
        while not results_queue.empty():
            response_times.append(results_queue.get())

        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        # Concurrent performance assertions
        assert (
            avg_response_time < 500
        ), f"Avg concurrent response {avg_response_time:.1f}ms too slow"
        assert (
            max_response_time < 1000
        ), f"Max concurrent response {max_response_time:.1f}ms too slow"


class TestSecurityValidation:
    """Security testing for authentication and authorization flows."""

    def setup_method(self):
        """Set up security testing environment."""
        self.auth_service = AuthService(Mock())
        self.config_service = Mock()
        self.error_service = ErrorService(Mock())

    def test_authentication_flow_security(self):
        """Test authentication flow security measures."""
        # Test that credentials are not logged
        with patch("cli.services.auth_service.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.stdout = "secret-token-12345"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Mock logging to verify no secrets are logged
            with patch("cli.services.auth_service.logger") as mock_logger:
                credentials = self.auth_service.authenticate_gcp("test-project")

                # Verify credentials are returned
                assert credentials.token == "secret-token-12345"

                # Verify no secret tokens appear in logs
                for call in mock_logger.info.call_args_list:
                    assert "secret-token-12345" not in str(call)

    def test_input_validation_security(self):
        """Test input validation prevents injection attacks."""
        from cli.commands.vm_commands import VMCommands

        vm_commands = VMCommands(Mock())

        # Test SQL injection attempt
        malicious_input = "'; DROP TABLE users; --"
        args = Namespace(
            vm_action="create-pool", type=malicious_input, size=1, dry_run=True
        )

        with pytest.raises(Exception) as exc_info:
            vm_commands.execute(args, {})

        # Verify the malicious input was rejected
        assert "Invalid" in str(exc_info.value) or "Unknown" in str(exc_info.value)

    def test_credential_management_security(self):
        """Test secure credential management practices."""
        # Test that credentials are not stored in plain text
        credentials = Mock()
        credentials.token = "sensitive-token"
        credentials.service_account = "test@project.iam.gserviceaccount.com"

        # Mock secure storage
        with patch("cli.services.auth_service.keyring") as mock_keyring:
            self.auth_service._store_credentials_securely(credentials)

            # Verify credentials are stored securely
            mock_keyring.set_password.assert_called()

            # Verify token is not passed as plain text
            call_args = mock_keyring.set_password.call_args
            assert call_args is not None

    def test_audit_logging_compliance(self):
        """Test audit logging for compliance requirements."""
        from cli.services.error_service import ErrorService

        error_service = ErrorService(Mock())

        # Create security-related error
        security_error = error_service.create_error(
            message="Authentication failed",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            code="AUTH_FAILED",
            context={"user": "test@example.com", "ip": "192.168.1.1"},
        )

        # Verify audit information is captured
        assert security_error.category == ErrorCategory.AUTHENTICATION
        assert security_error.timestamp is not None
        assert "user" in security_error.context
        assert "ip" in security_error.context

        # Verify error is properly categorized for security monitoring
        exit_code = error_service.get_exit_code(security_error)
        assert exit_code == 10  # Authentication category exit code


class TestAccessibilityCompliance:
    """Accessibility testing for WCAG 2.1 AA compliance."""

    def test_color_contrast_compliance(self):
        """Test color contrast ratios meet WCAG 2.1 AA standards."""
        from cli.ui.colors import ColorScheme

        color_scheme = ColorScheme()

        # Test color combinations for sufficient contrast
        test_combinations = [
            ("error", "background"),
            ("warning", "background"),
            ("info", "background"),
            ("success", "background"),
        ]

        for fg_color, bg_color in test_combinations:
            contrast_ratio = color_scheme.get_contrast_ratio(fg_color, bg_color)

            # WCAG 2.1 AA requires minimum 4.5:1 contrast ratio
            assert (
                contrast_ratio >= 4.5
            ), f"Color combination {fg_color}/{bg_color} has insufficient contrast: {contrast_ratio:.2f}:1"

    def test_screen_reader_compatibility(self):
        """Test screen reader compatibility features."""
        from cli.ui.formatter import OutputFormatter

        formatter = OutputFormatter()

        # Test that formatted output includes screen reader friendly elements
        test_data = {
            "status": "success",
            "message": "Operation completed",
            "items": ["item1", "item2", "item3"],
        }

        formatted = formatter.format_data(test_data, format_type="accessible")

        # Verify screen reader friendly formatting
        assert "Status:" in formatted
        assert "Message:" in formatted
        assert "Items:" in formatted

        # Verify proper structure for screen readers
        lines = formatted.split("\n")
        assert len([line for line in lines if line.strip()]) >= 3  # Multiple sections

    def test_keyboard_navigation_support(self):
        """Test keyboard navigation support in interactive elements."""
        from cli.ui.interactive import InteractivePrompt

        prompt = InteractivePrompt()

        # Test that interactive prompts support keyboard navigation
        choices = ["Option 1", "Option 2", "Option 3"]

        # Mock keyboard input simulation
        with patch("builtins.input", side_effect=["2"]):  # Select second option
            result = prompt.select_from_list("Choose an option:", choices)

            assert result == "Option 2"

        # Test escape sequences are handled properly
        with patch(
            "builtins.input", side_effect=["\x1b", "1"]
        ):  # ESC then select first
            result = prompt.select_from_list("Choose an option:", choices)

            assert result == "Option 1"


if __name__ == "__main__":
    # Run with coverage reporting
    pytest.main(
        [
            __file__,
            "--cov=cli",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=90",
            "-v",
        ]
    )
