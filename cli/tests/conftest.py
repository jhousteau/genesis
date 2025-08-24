"""
Pytest Configuration for Genesis CLI Testing
Comprehensive test configuration following VERIFY methodology.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import json
import yaml

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test markers - only include available plugins
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "skip_ci: mark test to skip in CI")


@pytest.fixture(scope="session")
def test_config():
    """Session-wide test configuration."""
    return {
        "project_id": "genesis-test-project",
        "region": "us-central1",
        "zone": "us-central1-a",
        "environment": "test",
        "performance_targets": {
            "startup_time_ms": 200,
            "response_time_ms": 2000,
            "memory_limit_mb": 50,
        },
        "security_config": {
            "service_account": "test@genesis-test-project.iam.gserviceaccount.com",
            "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
        },
    }


@pytest.fixture
def temp_genesis_root():
    """Create temporary Genesis root directory structure."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create complete directory structure
    directories = [
        "config/environments",
        "modules/vm-management",
        "modules/container-orchestration",
        "modules/networking",
        "modules/security",
        "cli/commands",
        "cli/services",
        "cli/ui",
        "core",
        "temp/reports",
    ]

    for directory in directories:
        (temp_dir / directory).mkdir(parents=True, exist_ok=True)

    # Create essential config files
    _create_test_configs(temp_dir)

    yield temp_dir

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


def _create_test_configs(temp_dir):
    """Create essential configuration files for testing."""
    config_dir = temp_dir / "config"

    # Global configuration
    global_config = {
        "terraform": {
            "backend_bucket": "test-terraform-state",
            "region": "us-central1",
        },
        "performance": {
            "target_response_time": 2.0,
            "cache_ttl": 300,
            "monitoring": {"enabled": True},
        },
    }

    with open(config_dir / "global.yaml", "w") as f:
        yaml.dump(global_config, f)

    # Test environment configuration
    test_env_config = {
        "gcp": {
            "project_id": "genesis-test-project",
            "region": "us-central1",
            "zone": "us-central1-a",
        },
        "agents": {
            "types": {
                "backend-developer": {
                    "machine_type": "e2-standard-2",
                    "disk_size_gb": 50,
                    "preemptible": False,
                },
                "frontend-developer": {
                    "machine_type": "e2-medium",
                    "disk_size_gb": 30,
                    "preemptible": True,
                },
                "platform-engineer": {
                    "machine_type": "e2-standard-4",
                    "disk_size_gb": 100,
                    "preemptible": False,
                },
                "test-agent": {
                    "machine_type": "e2-micro",
                    "disk_size_gb": 20,
                    "preemptible": True,
                },
            }
        },
        "containers": {
            "cluster_name": "test-cluster",
            "node_pool_size": 3,
            "services": {
                "agent-cage": {
                    "replicas": 2,
                    "port": 8080,
                    "image": "gcr.io/genesis/agent-cage:latest",
                },
                "claude-talk": {
                    "replicas": 3,
                    "port": 9000,
                    "image": "gcr.io/genesis/claude-talk:latest",
                },
                "test-service": {
                    "replicas": 1,
                    "port": 3000,
                    "image": "gcr.io/google-samples/hello-app:2.0",
                },
            },
        },
        "terraform": {"backend_bucket": "test-terraform-state", "state_prefix": "test"},
    }

    with open(config_dir / "environments" / "test.yaml", "w") as f:
        yaml.dump(test_env_config, f)


@pytest.fixture
def mock_cli():
    """Mock CLI object with complete configuration."""
    cli = Mock()
    cli.genesis_root = Path("/tmp/genesis-test")
    cli.environment = "test"
    cli.project_id = "genesis-test-project"
    cli.verbose = False
    cli.dry_run = False
    cli.output_format = "json"

    return cli


@pytest.fixture
def mock_services():
    """Mock all CLI services with realistic behaviors."""
    services = Mock()

    # Config Service Mock
    services.config_service = Mock()
    services.config_service.load_environment_config.return_value = {
        "gcp": {"project_id": "test-project", "region": "us-central1"},
        "agents": {"types": {"test-agent": {"machine_type": "e2-micro"}}},
    }
    services.config_service.get_agent_config.return_value = {
        "types": {"test-agent": {"machine_type": "e2-micro"}}
    }

    # Auth Service Mock
    services.auth_service = Mock()
    mock_credentials = Mock()
    mock_credentials.token = "test-token-12345"
    mock_credentials.project_id = "test-project"
    mock_credentials.provider = "gcp"
    services.auth_service.authenticate_gcp.return_value = mock_credentials

    # Cache Service Mock
    services.cache_service = Mock()
    services.cache_service.get.return_value = None
    services.cache_service.set.return_value = True
    services.cache_service.get_stats.return_value = {
        "hits": 10,
        "misses": 5,
        "hit_rate": 0.67,
    }

    # Error Service Mock
    services.error_service = Mock()
    mock_error = Mock()
    mock_error.message = "Test error"
    mock_error.category = "TEST"
    mock_error.severity = "LOW"
    services.error_service.create_error.return_value = mock_error

    # GCP Service Mock
    services.gcp_service = Mock()
    services.gcp_service.list_vm_pools.return_value = []
    services.gcp_service.create_vm_pool.return_value = {
        "pool_name": "test-pool",
        "status": "creating",
    }

    # Performance Service Mock
    services.performance_service = Mock()
    timer_mock = Mock()
    timer_mock.__enter__ = Mock(return_value=timer_mock)
    timer_mock.__exit__ = Mock(return_value=None)
    services.performance_service.time_operation.return_value = timer_mock
    services.performance_service.get_performance_summary.return_value = {
        "total_operations": 10,
        "avg_response_time": 1.5,
    }

    return services


@pytest.fixture
def performance_monitor():
    """Performance monitoring fixture for test timing."""
    import time

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def end(self):
            self.end_time = time.time()

        @property
        def duration_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return 0

    return PerformanceMonitor()


@pytest.fixture
def memory_monitor():
    """Memory monitoring fixture for memory usage testing."""
    try:
        import psutil
        import os

        class MemoryMonitor:
            def __init__(self):
                self.process = psutil.Process(os.getpid())
                self.start_memory = None
                self.end_memory = None

            def start(self):
                self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            def end(self):
                self.end_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            @property
            def memory_increase_mb(self):
                if self.start_memory and self.end_memory:
                    return self.end_memory - self.start_memory
                return 0

        return MemoryMonitor()

    except ImportError:
        # Fallback mock if psutil not available
        mock_monitor = Mock()
        mock_monitor.start = Mock()
        mock_monitor.end = Mock()
        mock_monitor.memory_increase_mb = 0
        return mock_monitor


# Pytest hooks for enhanced reporting (disabled for basic pytest compatibility)
# def pytest_html_report_title(report):
#     """Customize HTML report title."""
#     report.title = "Genesis CLI Comprehensive Test Report"


def pytest_collection_modifyitems(config, items):
    """Modify collected test items based on markers and conditions."""
    skip_integration = pytest.mark.skip(
        reason="Integration tests require environment setup"
    )
    skip_e2e = pytest.mark.skip(reason="E2E tests require explicit enablement")
    skip_slow = pytest.mark.skip(reason="Slow tests skipped by default")

    for item in items:
        # Skip integration tests unless explicitly enabled
        if "integration" in item.keywords and not os.getenv("RUN_INTEGRATION_TESTS"):
            item.add_marker(skip_integration)

        # Skip E2E tests unless explicitly enabled
        if "e2e" in item.keywords and not os.getenv("RUN_E2E_TESTS"):
            item.add_marker(skip_e2e)

        # Skip slow tests unless explicitly enabled
        if "slow" in item.keywords and not os.getenv("RUN_SLOW_TESTS"):
            item.add_marker(skip_slow)


@pytest.fixture(autouse=True)
def test_environment_setup():
    """Automatically set up test environment for all tests."""
    # Set environment variables
    original_env = {}
    test_env_vars = {
        "ENVIRONMENT": "test",
        "GENESIS_ROOT": str(Path.cwd()),
        "PYTHONPATH": str(Path.cwd()),
        "LOG_LEVEL": "WARNING",  # Reduce log noise in tests
    }

    # Save original values and set test values
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


# Custom assertions for CLI testing
class CLIAssertions:
    """Custom assertions for CLI testing."""

    @staticmethod
    def assert_command_success(result):
        """Assert command executed successfully."""
        assert result is not None
        if isinstance(result, dict):
            assert result.get("status") != "error"

    @staticmethod
    def assert_performance_within_target(duration_ms, target_ms, operation_name):
        """Assert operation performance meets target."""
        assert (
            duration_ms <= target_ms
        ), f"{operation_name} took {duration_ms}ms, exceeds target of {target_ms}ms"

    @staticmethod
    def assert_memory_within_limit(memory_mb, limit_mb, operation_name):
        """Assert memory usage within acceptable limits."""
        assert (
            memory_mb <= limit_mb
        ), f"{operation_name} used {memory_mb}MB, exceeds limit of {limit_mb}MB"

    @staticmethod
    def assert_coverage_threshold(coverage_percent, threshold):
        """Assert test coverage meets threshold."""
        assert (
            coverage_percent >= threshold
        ), f"Coverage {coverage_percent}% below threshold {threshold}%"


# Make assertions available to all tests
@pytest.fixture
def cli_assert():
    """Provide CLI-specific assertions."""
    return CLIAssertions


# Parametrization helpers
def agent_types():
    """Standard agent types for parametrized tests."""
    return [
        "backend-developer",
        "frontend-developer",
        "platform-engineer",
        "test-agent",
    ]


def environments():
    """Standard environments for parametrized tests."""
    return ["dev", "staging", "prod", "test"]


def gcp_regions():
    """Standard GCP regions for parametrized tests."""
    return ["us-central1", "us-east1", "us-west1", "europe-west1"]


# Export commonly used parametrize decorators
pytest_parametrize_agent_types = pytest.mark.parametrize("agent_type", agent_types())
pytest_parametrize_environments = pytest.mark.parametrize("environment", environments())
pytest_parametrize_regions = pytest.mark.parametrize("region", gcp_regions())
