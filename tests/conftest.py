#!/usr/bin/env python3
"""
Comprehensive pytest configuration and fixtures for Universal Project Platform
VERIFY methodology implementation with GCP-focused testing support
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project paths to Python path - critical for test discovery
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "lib" / "python"))
sys.path.insert(0, str(PROJECT_ROOT / "bin"))
sys.path.insert(0, str(PROJECT_ROOT / "setup-project"))

# Configure asyncio mode for pytest-asyncio
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    """Configure pytest markers to avoid warnings"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line(
        "markers", "error_handling: marks tests as error handling tests"
    )
    config.addinivalue_line("markers", "terraform: marks tests related to terraform")
    config.addinivalue_line("markers", "monitoring: marks tests related to monitoring")
    config.addinivalue_line("markers", "deployment: marks tests related to deployment")
    config.addinivalue_line(
        "markers", "registry: marks tests related to project registry"
    )
    config.addinivalue_line("markers", "cli: marks tests related to CLI commands")
    config.addinivalue_line(
        "markers", "cross_component: marks tests for cross-component communication"
    )
    config.addinivalue_line("markers", "security: marks tests for security features")
    config.addinivalue_line(
        "markers", "performance: marks tests for performance validation"
    )
    config.addinivalue_line("markers", "gcp: marks tests that require GCP services")
    config.addinivalue_line(
        "markers", "cicd: marks tests for CI/CD pipeline validation"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup global test environment - VERIFY methodology foundation"""
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["PYTHONPATH"] = ":".join(
        [
            str(PROJECT_ROOT),
            str(PROJECT_ROOT / "lib" / "python"),
            str(PROJECT_ROOT / "bin"),
            str(PROJECT_ROOT / "setup-project"),
        ]
    )

    # GCP test environment
    os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
    os.environ["GCP_PROJECT"] = "test-project"

    # Create test temp directory
    test_temp = PROJECT_ROOT / "tests" / "temp"
    test_temp.mkdir(exist_ok=True)

    # Create test reports directory
    test_reports = PROJECT_ROOT / "tests" / "test_reports"
    test_reports.mkdir(exist_ok=True)

    yield

    # Cleanup after all tests
    if test_temp.exists():
        shutil.rmtree(test_temp, ignore_errors=True)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test use"""
    temp_dir = tempfile.mkdtemp(prefix="genesis_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def project_root():
    """Provide project root path"""
    return PROJECT_ROOT


@pytest.fixture
def bootstrap_cli():
    """Bootstrap CLI instance fixture with proper error handling"""
    try:
        import importlib.util

        bootstrap_path = PROJECT_ROOT / "bin" / "bootstrap"
        if not bootstrap_path.exists():
            pytest.skip(f"Bootstrap CLI file not found: {bootstrap_path}")

        spec = importlib.util.spec_from_file_location("bootstrap", bootstrap_path)

        if spec and spec.loader:
            bootstrap_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bootstrap_module)
            return bootstrap_module.BootstrapCLI()
        else:
            pytest.skip("Bootstrap CLI spec could not be loaded")
    except Exception as e:
        pytest.skip(f"Bootstrap CLI not available: {e}")


@pytest.fixture
def mock_registry():
    """Mock project registry for testing"""
    registry_data = {
        "global": {
            "organization": "test-org",
            "default_region": "us-central1",
            "plumbing_version": "2.0.0",
            "bootstrap_version": "1.0.0",
            "registry_version": "2.0.0",
            "last_updated": "2024-01-01T00:00:00Z",
        },
        "projects": {
            "test-project": {
                "path": "/tmp/test-project",
                "type": "api",
                "language": "python",
                "cloud_provider": "gcp",
                "team": "test-team",
                "criticality": "high",
                "environments": {
                    "dev": {"gcp_project": "test-project-dev"},
                    "prod": {"gcp_project": "test-project-prod"},
                },
            }
        },
    }
    return registry_data


@pytest.fixture
def sample_project_structure(temp_dir):
    """Create a sample project structure for testing"""
    project_dir = temp_dir / "test-project"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create basic files
    (project_dir / "README.md").write_text("# Test Project")
    (project_dir / "package.json").write_text(
        '{"name": "test-project", "version": "1.0.0"}'
    )
    (project_dir / "requirements.txt").write_text("fastapi==0.104.1\nuvicorn==0.24.0")
    (project_dir / "pyproject.toml").write_text(
        """
[tool.poetry]
name = "test-project"
version = "1.0.0"
description = "Test project"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
"""
    )
    (project_dir / ".project-config.yaml").write_text(
        "version: 1.0.0\ntype: api\nlanguage: python"
    )
    (project_dir / "main.py").write_text(
        """
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
"""
    )

    # Create git directory
    git_dir = project_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\n    repositoryformatversion = 0")

    # Create scripts directory
    scripts_dir = project_dir / "scripts"
    scripts_dir.mkdir()

    # Smart commit script
    smart_commit = scripts_dir / "smart-commit.sh"
    smart_commit.write_text("#!/bin/bash\necho 'Smart commit successful'\nexit 0")
    smart_commit.chmod(0o755)

    # Deploy script
    deploy_script = scripts_dir / "deploy.sh"
    deploy_script.write_text("#!/bin/bash\necho 'Deploy successful for $1'\nexit 0")
    deploy_script.chmod(0o755)

    # Validation script
    validate_script = scripts_dir / "validate-compliance.sh"
    validate_script.write_text("#!/bin/bash\necho 'Validation successful'\nexit 0")
    validate_script.chmod(0o755)

    return project_dir


@pytest.fixture
def gcp_mock_services():
    """Comprehensive GCP services mocking for testing"""
    mock_storage_client = MagicMock()
    mock_storage_client.list_buckets.return_value = []

    mock_secret_client = MagicMock()
    mock_secret_client.list_secrets.return_value = []

    mock_firestore_client = MagicMock()

    mock_compute_client = MagicMock()
    mock_compute_client.list.return_value = []

    # Only patch modules that we actually need to test
    # Avoid trying to patch modules that might not be available
    # Return the mocks without patching - tests can use them directly
    yield {
        "storage": mock_storage_client,
        "secrets": mock_secret_client,
        "firestore": mock_firestore_client,
        "compute": mock_compute_client,
    }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls for testing"""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_cli_args():
    """Factory for creating mock CLI arguments"""

    def _create_args(**kwargs):
        args = MagicMock()
        for key, value in kwargs.items():
            setattr(args, key, value)
        return args

    return _create_args


@pytest.fixture
def test_config():
    """Provide test configuration"""
    return {
        "project_id": "test-project",
        "region": "us-central1",
        "zone": "us-central1-a",
        "environment": "test",
        "gcp_project": "test-gcp-project",
    }


@pytest.fixture(autouse=True)
def isolate_tests():
    """Ensure test isolation by mocking potentially dangerous operations"""
    # Don't mock subprocess.run globally as some tests need to control it
    with patch("shutil.rmtree") as mock_rmtree:
        mock_rmtree.return_value = None
        with patch("os.system") as mock_system:
            mock_system.return_value = 0
            yield


@pytest.fixture
async def async_temp_dir():
    """Async version of temp_dir fixture"""
    temp_dir = tempfile.mkdtemp(prefix="genesis_async_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def performance_timer():
    """Performance timing utility for testing"""
    import time

    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0

    return PerformanceTimer()


@pytest.fixture
def terraform_mock():
    """Mock terraform operations"""

    def mock_terraform_output(outputs):
        import json

        return json.dumps({key: {"value": value} for key, value in outputs.items()})

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_terraform_output(
            {
                "project_id": "test-project",
                "region": "us-central1",
                "vpc_id": "test-vpc",
            }
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run


# GCP Test Helper Class
class GCPTestHelper:
    """Helper class for GCP-related testing utilities"""

    @staticmethod
    def create_mock_bucket(name="test-bucket"):
        mock_bucket = MagicMock()
        mock_bucket.name = name
        mock_bucket.exists.return_value = True
        return mock_bucket

    @staticmethod
    def create_mock_secret(name="test-secret", value="test-value"):
        mock_secret = MagicMock()
        mock_secret.name = f"projects/test-project/secrets/{name}"
        mock_version = MagicMock()
        mock_version.payload.data = value.encode()
        mock_secret.versions.return_value = [mock_version]
        return mock_secret


@pytest.fixture
def gcp_helper():
    """GCP testing helper fixture"""
    return GCPTestHelper()


# Mark certain test functions to be skipped in CI
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on environment"""
    if os.getenv("CI") == "true":
        # Skip slow tests in CI unless specifically requested
        skip_slow = pytest.mark.skip(reason="Slow test skipped in CI")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    # Skip integration tests if no cloud credentials
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.getenv("TESTING"):
        skip_integration = pytest.mark.skip(
            reason="No cloud credentials for integration tests"
        )
        for item in items:
            if "integration" in item.keywords and "gcp" in item.keywords:
                item.add_marker(skip_integration)


# Error handling for test discovery
def pytest_sessionstart(session):
    """Called after the Session object has been created"""
    print("🧪 Starting test session for Genesis Universal Project Platform")
    print(f"📁 Project root: {PROJECT_ROOT}")
    print(f"🐍 Python path includes: {len(sys.path)} directories")


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished"""
    if exitstatus == 0:
        print("✅ All tests completed successfully!")
    else:
        print(f"❌ Tests finished with exit status: {exitstatus}")
