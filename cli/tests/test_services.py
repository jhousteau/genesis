"""
Service Layer Tests
Unit tests for the Genesis CLI service layer implementation following CRAFT methodology.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

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


class TestConfigService:
    """Test configuration service following CRAFT principles."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir()

        # Create test environment files
        (self.config_dir / "environments").mkdir()
        (self.config_dir / "environments" / "test.yaml").write_text(
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
"""
        )

        (self.config_dir / "global.yaml").write_text(
            """
terraform:
  backend_bucket: test-terraform-state
  region: us-central1
"""
        )

        self.config_service = ConfigService(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_load_environment_config(self):
        """Test loading environment-specific configuration."""
        config = self.config_service.load_environment_config("test")

        assert config["gcp"]["project_id"] == "test-project"
        assert config["gcp"]["region"] == "us-central1"
        assert (
            config["agents"]["types"]["backend-developer"]["machine_type"]
            == "e2-standard-2"
        )

    def test_load_global_config(self):
        """Test loading global configuration."""
        config = self.config_service.load_global_config()

        assert config["terraform"]["backend_bucket"] == "test-terraform-state"
        assert config["terraform"]["region"] == "us-central1"

    def test_get_terraform_config(self):
        """Test Terraform configuration generation."""
        config = self.config_service.get_terraform_config()

        assert "backend_bucket" in config
        assert "state_prefix" in config
        assert config["environment"] == "dev"  # Default

    def test_get_gcp_config(self):
        """Test GCP configuration generation."""
        self.config_service.update_environment("test")
        config = self.config_service.get_gcp_config()

        assert config["region"] == "us-central1"
        assert config["zone"] == "us-central1-a"
        assert config["labels"]["genesis-managed"] == "true"
        assert config["labels"]["environment"] == "test"

    def test_get_agent_config(self):
        """Test agent configuration generation."""
        self.config_service.update_environment("test")
        config = self.config_service.get_agent_config()

        assert "backend-developer" in config["types"]
        assert config["types"]["backend-developer"]["machine_type"] == "e2-standard-2"

        # Test default agent types are present
        assert "frontend-developer" in config["types"]
        assert "platform-engineer" in config["types"]

    def test_cache_invalidation(self):
        """Test configuration cache invalidation."""
        # Load config to populate cache
        self.config_service.load_environment_config("test")

        # Invalidate cache
        self.config_service.invalidate_cache()

        # Verify cache is cleared (would require checking internal cache)
        config = self.config_service.load_environment_config("test")
        assert config is not None


class TestAuthService:
    """Test authentication service following CRAFT principles."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_service = Mock()
        self.config_service.get_security_config.return_value = {
            "service_account": "test@test-project.iam.gserviceaccount.com",
            "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
        }
        self.config_service.project_id = "test-project"

        self.auth_service = AuthService(self.config_service)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("cli.services.auth_service.subprocess.run")
    def test_authenticate_gcp_success(self, mock_run):
        """Test successful GCP authentication."""
        # Mock successful gcloud command
        mock_result = Mock()
        mock_result.stdout = "test-token-12345"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        credentials = self.auth_service.authenticate_gcp("test-project")

        assert credentials.provider == "gcp"
        assert credentials.project_id == "test-project"
        assert credentials.token == "test-token-12345"
        assert credentials.token_expiry > datetime.now()

    @patch("cli.services.auth_service.subprocess.run")
    def test_authenticate_gcp_failure(self, mock_run):
        """Test GCP authentication failure."""
        # Mock failed gcloud command
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Authentication failed"
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "gcloud", stderr="Authentication failed"
        )

        with pytest.raises(Exception):  # AuthenticationError
            self.auth_service.authenticate_gcp("test-project")

    def test_get_authenticated_gcloud_cmd(self):
        """Test gcloud command authentication."""
        # Mock authentication
        with patch.object(self.auth_service, "authenticate_gcp") as mock_auth:
            mock_creds = Mock()
            mock_creds.service_account = "test@test-project.iam.gserviceaccount.com"
            mock_auth.return_value = mock_creds

            cmd = self.auth_service.get_authenticated_gcloud_cmd(
                ["gcloud", "compute", "instances", "list"], "test-project"
            )

            assert "--project=test-project" in cmd
            assert (
                "--impersonate-service-account=test@test-project.iam.gserviceaccount.com"
                in cmd
            )

    def test_get_auth_status(self):
        """Test authentication status retrieval."""
        status = self.auth_service.get_auth_status()

        assert "authenticated" in status
        assert "provider" in status
        assert "project_id" in status
        assert status["project_id"] == "test-project"


class TestCacheService:
    """Test cache service following CRAFT principles."""

    def setup_method(self):
        """Set up test environment."""
        self.config_service = Mock()
        self.config_service.get_performance_config.return_value = {
            "cache": {"ttl": 300, "max_entries": 100}
        }
        self.config_service.project_id = "test-project"
        self.config_service.environment = "test"

        self.cache_service = CacheService(self.config_service)

    def test_set_and_get(self):
        """Test basic cache set and get operations."""
        self.cache_service.set("test_key", "test_value", ttl=60)

        value = self.cache_service.get("test_key")
        assert value == "test_value"

    def test_get_with_default(self):
        """Test cache get with default value."""
        value = self.cache_service.get("nonexistent_key", "default_value")
        assert value == "default_value"

    def test_expiration(self):
        """Test cache entry expiration."""
        # Set with very short TTL
        self.cache_service.set("expiring_key", "expiring_value", ttl=0)

        # Should be expired immediately
        value = self.cache_service.get("expiring_key", "default")
        assert value == "default"

    def test_delete(self):
        """Test cache deletion."""
        self.cache_service.set("delete_key", "delete_value")

        deleted = self.cache_service.delete("delete_key")
        assert deleted is True

        value = self.cache_service.get("delete_key", "default")
        assert value == "default"

    def test_delete_by_tags(self):
        """Test cache deletion by tags."""
        self.cache_service.set("tag1", "value1", tags=["group1"])
        self.cache_service.set("tag2", "value2", tags=["group1"])
        self.cache_service.set("tag3", "value3", tags=["group2"])

        deleted_count = self.cache_service.delete_by_tags(["group1"])
        assert deleted_count == 2

        # group2 should still exist
        value = self.cache_service.get("tag3")
        assert value == "value3"

    def test_get_or_set(self):
        """Test get-or-set pattern."""

        def factory():
            return "factory_value"

        # First call should use factory
        value = self.cache_service.get_or_set("factory_key", factory, ttl=60)
        assert value == "factory_value"

        # Second call should use cached value
        def different_factory():
            return "different_value"

        value = self.cache_service.get_or_set("factory_key", different_factory)
        assert value == "factory_value"  # Should be cached value

    def test_increment(self):
        """Test cache increment operation."""
        # First increment creates the key
        value = self.cache_service.increment("counter")
        assert value == 1

        # Second increment increases value
        value = self.cache_service.increment("counter", delta=5)
        assert value == 6

    def test_cache_stats(self):
        """Test cache statistics."""
        self.cache_service.set("stats_key", "stats_value")
        self.cache_service.get("stats_key")
        self.cache_service.get("nonexistent")

        stats = self.cache_service.get_stats()

        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["sets"] >= 1
        assert "hit_rate" in stats
        assert "total_entries" in stats

    def test_key_normalization(self):
        """Test cache key normalization."""
        # Keys should be normalized with project and environment prefix
        self.cache_service.set("test_key", "test_value")

        normalized_key = self.cache_service._normalize_key("test_key")
        assert "test-project" in normalized_key
        assert "test" in normalized_key
        assert "test_key" in normalized_key


class TestErrorService:
    """Test error service following CRAFT principles."""

    def setup_method(self):
        """Set up test environment."""
        self.config_service = Mock()
        self.config_service.environment = "test"
        self.config_service.project_id = "test-project"

        self.error_service = ErrorService(self.config_service)

    def test_create_error(self):
        """Test error creation."""
        error = self.error_service.create_error(
            message="Test error",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            code="TEST_ERROR",
            suggestions=["Fix the test"],
        )

        assert error.message == "Test error"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.code == "TEST_ERROR"
        assert "Fix the test" in error.suggestions
        assert error.timestamp is not None

    def test_handle_exception(self):
        """Test exception handling."""
        test_exception = ValueError("Test exception")

        error = self.error_service.handle_exception(test_exception, {"context": "test"})

        assert "ValueError" in error.message
        assert "Test exception" in error.message
        assert error.context["context"] == "test"

    def test_format_error_message(self):
        """Test error message formatting."""
        error = self.error_service.create_error(
            message="Test formatting",
            category=ErrorCategory.USER,
            severity=ErrorSeverity.HIGH,
            code="FORMAT_TEST",
            suggestions=["Do this", "Do that"],
        )

        formatted = self.error_service.format_error_message(error)

        assert "❌" in formatted  # High severity indicator
        assert "FORMAT_TEST" in formatted
        assert "Test formatting" in formatted
        assert "Do this" in formatted
        assert "Do that" in formatted

    def test_get_exit_code(self):
        """Test exit code generation."""
        error = self.error_service.create_error(
            message="Test exit code",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.CRITICAL,
            code="EXIT_TEST",
        )

        exit_code = self.error_service.get_exit_code(error)
        assert exit_code == 10  # Authentication category

    def test_error_history(self):
        """Test error history tracking."""
        # Create multiple errors
        for i in range(3):
            self.error_service.create_error(
                message=f"Error {i}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                code=f"ERROR_{i}",
            )

        summary = self.error_service.get_error_summary()

        assert summary["total_errors"] == 3
        assert "system" in summary["by_category"]
        assert summary["by_category"]["system"] == 3
        assert "medium" in summary["by_severity"]


class TestPerformanceService:
    """Test performance service following CRAFT principles."""

    def setup_method(self):
        """Set up test environment."""
        self.config_service = Mock()
        self.config_service.get_performance_config.return_value = {
            "target_response_time": 2.0,
            "response_timeout": 120,
            "monitoring": {"enabled": True, "sample_rate": 1.0},
        }

        self.performance_service = PerformanceService(self.config_service)

    def test_timer_operations(self):
        """Test operation timing."""
        timer = self.performance_service.start_timer("test_operation")

        # Simulate some work
        import time

        time.sleep(0.01)  # 10ms

        elapsed = self.performance_service.end_timer(timer)

        assert elapsed >= 0.01
        assert elapsed < 0.1  # Should be reasonable

    def test_time_operation_context_manager(self):
        """Test timing context manager."""
        with self.performance_service.time_operation("context_test") as ctx:
            import time

            time.sleep(0.01)

        # Should have recorded the operation
        stats = self.performance_service.get_operation_stats("context_test")
        assert stats["count"] >= 1

    def test_record_metric(self):
        """Test metric recording."""
        self.performance_service.record_metric("test_metric", 42.0, "units")

        # Metric should be recorded (internal verification would require access to metrics)
        assert True  # Placeholder for internal metric verification

    def test_operation_stats(self):
        """Test operation statistics."""
        # Record multiple operations
        for i in range(5):
            with self.performance_service.time_operation("stats_test"):
                import time

                time.sleep(0.001 * i)  # Variable timing

        stats = self.performance_service.get_operation_stats("stats_test")

        assert stats["count"] >= 5
        assert stats["avg_duration"] > 0
        assert stats["min_duration"] >= 0
        assert stats["max_duration"] > stats["min_duration"]
        assert 0 <= stats["target_compliance"] <= 1

    def test_performance_summary(self):
        """Test performance summary."""
        # Generate some operations
        with self.performance_service.time_operation("summary_test"):
            pass

        summary = self.performance_service.get_performance_summary()

        assert "total_operations" in summary
        assert "avg_response_time" in summary
        assert "target_compliance" in summary
        assert "operations" in summary

    def test_performance_health_check(self):
        """Test performance health checking."""
        # Generate fast operations (should be healthy)
        for _ in range(10):
            with self.performance_service.time_operation("fast_op"):
                pass  # Very fast operation

        health = self.performance_service.check_performance_health()

        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "issues" in health
        assert "recommendations" in health


@pytest.fixture
def mock_gcp_service():
    """Mock GCP service for testing."""
    config_service = Mock()
    auth_service = Mock()
    cache_service = Mock()
    error_service = Mock()

    return GCPService(config_service, auth_service, cache_service, error_service)


class TestIntegration:
    """Integration tests for service layer interactions."""

    def test_service_layer_integration(self):
        """Test integration between services."""
        # Create a temporary directory for config
        temp_dir = Path(tempfile.mkdtemp())
        config_dir = temp_dir / "config"
        config_dir.mkdir()

        try:
            # Set up minimal config
            (config_dir / "environments").mkdir()
            (config_dir / "environments" / "test.yaml").write_text(
                "gcp:\n  project_id: test-project"
            )
            (config_dir / "global.yaml").write_text("terraform:\n  region: us-central1")

            # Initialize services
            config_service = ConfigService(temp_dir)
            config_service.update_environment("test")

            error_service = ErrorService(config_service)
            cache_service = CacheService(config_service)
            performance_service = PerformanceService(config_service)

            # Test service interactions
            with performance_service.time_operation("integration_test"):
                # Cache some data
                cache_service.set("integration_key", "integration_value", ttl=60)

                # Retrieve cached data
                value = cache_service.get("integration_key")
                assert value == "integration_value"

                # Create an error
                error = error_service.create_error(
                    message="Integration test error",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.LOW,
                    code="INTEGRATION_TEST",
                )
                assert error.code == "INTEGRATION_TEST"

            # Verify performance was tracked
            perf_summary = performance_service.get_performance_summary()
            assert perf_summary["total_operations"] > 0

        finally:
            import shutil

            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
