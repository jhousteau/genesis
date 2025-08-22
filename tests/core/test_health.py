"""
Comprehensive tests for Genesis health monitoring using VERIFY methodology.

Test Coverage:
- HealthStatus enumeration and score conversion
- CheckType classification and validation
- HealthCheck configuration and execution
- HealthMetric data point tracking
- ComponentHealth status management
- SystemHealth aggregation and reporting
- HealthAggregator monitoring and alerting
- Thread safety and concurrent health checks
- Performance benchmarks and edge cases
- K8s probe compatibility and integration
"""

import statistics
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from lib.integration.health_aggregator import (
    CheckType,
    ComponentHealth,
    HealthAggregator,
    HealthCheck,
    HealthMetric,
    HealthStatus,
    SystemHealth,
    add_health_check,
    get_health_aggregator,
    get_system_health,
)


class TestHealthStatus:
    """Test HealthStatus enumeration and score conversion."""

    def test_health_status_values(self):
        """Test all health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_health_status_from_score_healthy(self):
        """Test score to status conversion for healthy range."""
        assert HealthStatus.from_score(1.0) == HealthStatus.HEALTHY
        assert HealthStatus.from_score(0.95) == HealthStatus.HEALTHY
        assert HealthStatus.from_score(0.9) == HealthStatus.HEALTHY

    def test_health_status_from_score_degraded(self):
        """Test score to status conversion for degraded range."""
        assert HealthStatus.from_score(0.89) == HealthStatus.DEGRADED
        assert HealthStatus.from_score(0.7) == HealthStatus.DEGRADED
        assert HealthStatus.from_score(0.5) == HealthStatus.DEGRADED

    def test_health_status_from_score_unhealthy(self):
        """Test score to status conversion for unhealthy range."""
        assert HealthStatus.from_score(0.49) == HealthStatus.UNHEALTHY
        assert HealthStatus.from_score(0.25) == HealthStatus.UNHEALTHY
        assert HealthStatus.from_score(0.01) == HealthStatus.UNHEALTHY

    def test_health_status_from_score_unknown(self):
        """Test score to status conversion for unknown/zero range."""
        assert HealthStatus.from_score(0.0) == HealthStatus.UNKNOWN
        assert HealthStatus.from_score(-0.1) == HealthStatus.UNKNOWN
        assert HealthStatus.from_score(-1.0) == HealthStatus.UNKNOWN

    def test_health_status_boundary_values(self):
        """Test boundary values for status conversion."""
        # Exact boundaries
        assert HealthStatus.from_score(0.9) == HealthStatus.HEALTHY
        assert HealthStatus.from_score(0.5) == HealthStatus.DEGRADED
        assert HealthStatus.from_score(0.0) == HealthStatus.UNKNOWN

        # Just above/below boundaries
        assert HealthStatus.from_score(0.900001) == HealthStatus.HEALTHY
        assert HealthStatus.from_score(0.899999) == HealthStatus.DEGRADED
        assert HealthStatus.from_score(0.500001) == HealthStatus.DEGRADED
        assert HealthStatus.from_score(0.499999) == HealthStatus.UNHEALTHY


class TestCheckType:
    """Test CheckType enumeration."""

    def test_check_type_values(self):
        """Test all check type enum values."""
        assert CheckType.LIVENESS.value == "liveness"
        assert CheckType.READINESS.value == "readiness"
        assert CheckType.STARTUP.value == "startup"
        assert CheckType.CUSTOM.value == "custom"

    def test_check_type_kubernetes_compatibility(self):
        """Test that check types align with Kubernetes probe types."""
        # Kubernetes uses these probe types
        k8s_probes = ["liveness", "readiness", "startup"]

        for probe_type in k8s_probes:
            # Should be able to create CheckType from K8s probe name
            check_type = CheckType(probe_type)
            assert check_type.value == probe_type


class TestHealthCheck:
    """Test HealthCheck configuration and validation."""

    def test_health_check_creation_minimal(self):
        """Test creating health check with minimal required fields."""
        check = HealthCheck(
            name="test_check", component="test_component", check_type=CheckType.LIVENESS
        )

        assert check.name == "test_check"
        assert check.component == "test_component"
        assert check.check_type == CheckType.LIVENESS
        assert check.endpoint is None
        assert check.command is None
        assert check.function is None
        assert check.interval == 30
        assert check.timeout == 5
        assert check.retries == 3
        assert check.critical is False
        assert check.enabled is True

    def test_health_check_creation_full(self):
        """Test creating health check with all fields."""
        test_function = lambda: True

        check = HealthCheck(
            name="comprehensive_check",
            component="api_service",
            check_type=CheckType.READINESS,
            endpoint="http://localhost:8080/health",
            command="curl -f http://localhost:8080/ping",
            function=test_function,
            interval=60,
            timeout=10,
            retries=5,
            critical=True,
            enabled=False,
        )

        assert check.name == "comprehensive_check"
        assert check.component == "api_service"
        assert check.check_type == CheckType.READINESS
        assert check.endpoint == "http://localhost:8080/health"
        assert check.command == "curl -f http://localhost:8080/ping"
        assert check.function == test_function
        assert check.interval == 60
        assert check.timeout == 10
        assert check.retries == 5
        assert check.critical is True
        assert check.enabled is False

    def test_health_check_hash_consistency(self):
        """Test health check hash for set operations."""
        check1 = HealthCheck("test", "comp1", CheckType.LIVENESS)
        check2 = HealthCheck("test", "comp1", CheckType.READINESS)  # Different type
        check3 = HealthCheck("test", "comp1", CheckType.LIVENESS)  # Same as check1

        # Hash should be based on component and name
        assert hash(check1) == hash(check3)
        assert hash(check1) == hash(check2)  # Same component:name

        # Different component should have different hash
        check4 = HealthCheck("test", "comp2", CheckType.LIVENESS)
        assert hash(check1) != hash(check4)

    def test_health_check_in_set(self):
        """Test health check behavior in sets."""
        check1 = HealthCheck("check1", "comp1", CheckType.LIVENESS)
        check2 = HealthCheck("check2", "comp1", CheckType.READINESS)
        check3 = HealthCheck("check1", "comp1", CheckType.STARTUP)  # Same name/comp

        check_set = {check1, check2, check3}

        # Should have only 2 unique checks (check1 and check3 are considered same)
        assert len(check_set) == 2


class TestHealthMetric:
    """Test HealthMetric data point structure."""

    def test_health_metric_creation(self):
        """Test creating health metric with default values."""
        timestamp = datetime.now().isoformat()
        metric = HealthMetric(timestamp=timestamp, value=85.5)

        assert metric.timestamp == timestamp
        assert metric.value == 85.5
        assert metric.unit == "percent"
        assert metric.metadata == {}

    def test_health_metric_with_metadata(self):
        """Test creating health metric with custom metadata."""
        timestamp = datetime.now().isoformat()
        metadata = {"source": "cpu_monitor", "host": "worker-01", "region": "us-west-2"}

        metric = HealthMetric(
            timestamp=timestamp, value=42.3, unit="ms", metadata=metadata
        )

        assert metric.value == 42.3
        assert metric.unit == "ms"
        assert metric.metadata == metadata
        assert metric.metadata["source"] == "cpu_monitor"


class TestComponentHealth:
    """Test ComponentHealth status tracking."""

    def test_component_health_creation(self):
        """Test creating component health status."""
        checks = {"check1": True, "check2": False}
        metrics = {"response_time": 150.5, "cpu_usage": 65.2}
        timestamp = datetime.now().isoformat()

        health = ComponentHealth(
            component="api_service",
            status=HealthStatus.DEGRADED,
            score=0.75,
            checks=checks,
            metrics=metrics,
            last_check=timestamp,
            consecutive_failures=2,
            error_message="Some checks failing",
            dependencies_healthy=False,
        )

        assert health.component == "api_service"
        assert health.status == HealthStatus.DEGRADED
        assert health.score == 0.75
        assert health.checks == checks
        assert health.metrics == metrics
        assert health.last_check == timestamp
        assert health.consecutive_failures == 2
        assert health.error_message == "Some checks failing"
        assert health.dependencies_healthy is False

    def test_component_health_is_healthy(self):
        """Test is_healthy method."""
        healthy = ComponentHealth(
            component="test",
            status=HealthStatus.HEALTHY,
            score=0.95,
            checks={},
            metrics={},
            last_check=datetime.now().isoformat(),
        )

        degraded = ComponentHealth(
            component="test",
            status=HealthStatus.DEGRADED,
            score=0.65,
            checks={},
            metrics={},
            last_check=datetime.now().isoformat(),
        )

        assert healthy.is_healthy() is True
        assert degraded.is_healthy() is False

    def test_component_health_is_critical_failure(self):
        """Test is_critical_failure method."""
        critical = ComponentHealth(
            component="test",
            status=HealthStatus.UNHEALTHY,
            score=0.1,
            checks={},
            metrics={},
            last_check=datetime.now().isoformat(),
            consecutive_failures=5,
        )

        not_critical = ComponentHealth(
            component="test",
            status=HealthStatus.UNHEALTHY,
            score=0.1,
            checks={},
            metrics={},
            last_check=datetime.now().isoformat(),
            consecutive_failures=2,  # <= 3
        )

        also_not_critical = ComponentHealth(
            component="test",
            status=HealthStatus.DEGRADED,  # Not UNHEALTHY
            score=0.6,
            checks={},
            metrics={},
            last_check=datetime.now().isoformat(),
            consecutive_failures=5,
        )

        assert critical.is_critical_failure() is True
        assert not_critical.is_critical_failure() is False
        assert also_not_critical.is_critical_failure() is False


class TestSystemHealth:
    """Test SystemHealth aggregation."""

    def test_system_health_creation(self):
        """Test creating system health summary."""
        timestamp = datetime.now().isoformat()
        component_health = {
            "api": ComponentHealth(
                "api", HealthStatus.HEALTHY, 0.95, {}, {}, timestamp
            ),
            "db": ComponentHealth("db", HealthStatus.DEGRADED, 0.65, {}, {}, timestamp),
        }

        system_health = SystemHealth(
            status=HealthStatus.DEGRADED,
            score=0.8,
            component_health=component_health,
            timestamp=timestamp,
            healthy_components=1,
            total_components=2,
            critical_issues=["Database connection unstable"],
            warnings=["API response time elevated"],
        )

        assert system_health.status == HealthStatus.DEGRADED
        assert system_health.score == 0.8
        assert len(system_health.component_health) == 2
        assert system_health.healthy_components == 1
        assert system_health.total_components == 2
        assert len(system_health.critical_issues) == 1
        assert len(system_health.warnings) == 1

    def test_system_health_get_summary(self):
        """Test get_summary method."""
        timestamp = datetime.now().isoformat()

        system_health = SystemHealth(
            status=HealthStatus.HEALTHY,
            score=0.92,
            component_health={},
            timestamp=timestamp,
            healthy_components=5,
            total_components=5,
            critical_issues=[],
            warnings=[],
        )

        summary = system_health.get_summary()

        assert "System Health: healthy" in summary
        assert "(5/5 healthy)" in summary
        assert "Score: 92.00%" in summary


class TestHealthAggregator:
    """Test HealthAggregator core functionality."""

    @pytest.fixture
    def aggregator(self):
        """Create health aggregator for testing."""
        # Use custom config to avoid file system dependencies
        config = {
            "health": {
                "enabled": True,
                "default_interval": 10,
                "default_timeout": 2,
                "history_size": 50,
                "alert_on_degraded": True,
                "alert_on_unhealthy": True,
                "aggregation_strategy": "weighted",
                "component_weights": {
                    "api": 1.0,
                    "database": 1.5,
                    "cache": 0.5,
                },
            }
        }

        # Mock the file system dependencies in default checks
        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)
            # Clear default checks for clean testing
            aggregator.health_checks.clear()
            aggregator.component_health.clear()
            aggregator.health_history.clear()
            return aggregator

    def test_aggregator_initialization(self, aggregator):
        """Test aggregator initialization."""
        assert aggregator.config["health"]["enabled"] is True
        assert aggregator.config["health"]["default_interval"] == 10
        assert len(aggregator.health_checks) == 0  # Cleared for testing
        assert len(aggregator.component_health) == 0
        assert aggregator.monitoring_active is False
        assert len(aggregator.check_threads) == 0

    def test_add_health_check(self, aggregator):
        """Test adding health checks."""
        check = HealthCheck(
            name="api_health",
            component="api",
            check_type=CheckType.LIVENESS,
            function=lambda: True,
        )

        aggregator.add_check(check)

        assert len(aggregator.health_checks) == 1
        assert check in aggregator.health_checks
        assert "api" in aggregator.component_health
        assert "api" in aggregator.health_history

        # Component health should be initialized
        api_health = aggregator.component_health["api"]
        assert api_health.component == "api"
        assert api_health.status == HealthStatus.UNKNOWN
        assert api_health.score == 0.0

    def test_remove_health_check(self, aggregator):
        """Test removing health checks."""
        check = HealthCheck("test_check", "test_comp", CheckType.LIVENESS)
        aggregator.add_check(check)

        assert len(aggregator.health_checks) == 1

        # Remove existing check
        result = aggregator.remove_check("test_check", "test_comp")
        assert result is True
        assert len(aggregator.health_checks) == 0

        # Remove non-existing check
        result = aggregator.remove_check("nonexistent", "test_comp")
        assert result is False

    def test_execute_check_function(self, aggregator):
        """Test executing function-based health checks."""
        success_check = HealthCheck(
            "success_check", "test_comp", CheckType.LIVENESS, function=lambda: True
        )

        failure_check = HealthCheck(
            "failure_check", "test_comp", CheckType.LIVENESS, function=lambda: False
        )

        exception_check = HealthCheck(
            "exception_check",
            "test_comp",
            CheckType.LIVENESS,
            function=lambda: exec('raise Exception("check failed")'),
        )

        assert aggregator._execute_check(success_check) is True
        assert aggregator._execute_check(failure_check) is False

        with pytest.raises(Exception):
            aggregator._execute_check(exception_check)

    def test_execute_check_retries(self, aggregator):
        """Test check execution with retries."""
        call_count = 0

        def flaky_check():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"failure {call_count}")
            return True

        check = HealthCheck(
            "flaky_check",
            "test_comp",
            CheckType.LIVENESS,
            function=flaky_check,
            retries=3,
        )

        result = aggregator._execute_check(check)

        assert result is True
        assert call_count == 3

    @patch("requests.get")
    def test_execute_check_http_endpoint(self, mock_get, aggregator):
        """Test executing HTTP endpoint checks."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        success_check = HealthCheck(
            "http_check",
            "api",
            CheckType.READINESS,
            endpoint="http://localhost:8080/health",
            timeout=5,
        )

        result = aggregator._execute_check(success_check)

        assert result is True
        mock_get.assert_called_once_with("http://localhost:8080/health", timeout=5)

        # Mock failed response
        mock_response.status_code = 500
        result = aggregator._execute_check(success_check)
        assert result is False

        # Mock connection error
        mock_get.side_effect = Exception("Connection failed")
        result = aggregator._execute_check(success_check)
        assert result is False

    @patch("subprocess.run")
    def test_execute_check_command(self, mock_run, aggregator):
        """Test executing command-based checks."""
        # Mock successful command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        command_check = HealthCheck(
            "command_check",
            "system",
            CheckType.LIVENESS,
            command="echo 'health check'",
            timeout=5,
        )

        result = aggregator._execute_check(command_check)

        assert result is True
        mock_run.assert_called_once_with(
            "echo 'health check'", shell=True, capture_output=True, timeout=5
        )

        # Mock failed command
        mock_result.returncode = 1
        result = aggregator._execute_check(command_check)
        assert result is False

        # Mock command timeout
        mock_run.side_effect = Exception("Command timeout")
        result = aggregator._execute_check(command_check)
        assert result is False

    def test_calculate_component_score(self, aggregator):
        """Test component score calculation."""
        checks = [
            HealthCheck("check1", "comp", CheckType.LIVENESS, critical=False),
            HealthCheck("check2", "comp", CheckType.READINESS, critical=True),
            HealthCheck("check3", "comp", CheckType.STARTUP, critical=False),
        ]

        # All pass
        results = {"check1": True, "check2": True, "check3": True}
        score = aggregator._calculate_component_score(results, checks)
        assert score == 1.0

        # Critical check fails
        results = {"check1": True, "check2": False, "check3": True}
        score = aggregator._calculate_component_score(results, checks)
        # Score should be (1 + 0*2 + 1) / (1 + 2 + 1) = 2/4 = 0.5
        assert score == 0.5

        # Non-critical checks fail
        results = {"check1": False, "check2": True, "check3": False}
        score = aggregator._calculate_component_score(results, checks)
        # Score should be (0 + 2 + 0) / (1 + 2 + 1) = 2/4 = 0.5
        assert score == 0.5

        # All fail
        results = {"check1": False, "check2": False, "check3": False}
        score = aggregator._calculate_component_score(results, checks)
        assert score == 0.0

        # No results
        score = aggregator._calculate_component_score({}, checks)
        assert score == 0.0

    def test_perform_component_checks(self, aggregator):
        """Test performing checks for a component."""
        # Add checks for a component
        checks = [
            HealthCheck("check1", "api", CheckType.LIVENESS, function=lambda: True),
            HealthCheck("check2", "api", CheckType.READINESS, function=lambda: False),
        ]

        for check in checks:
            aggregator.add_check(check)

        # Perform checks
        aggregator._perform_component_checks("api", checks)

        # Verify component health was updated
        api_health = aggregator.component_health["api"]
        assert api_health.component == "api"
        assert api_health.checks["check1"] is True
        assert api_health.checks["check2"] is False
        assert 0 < api_health.score < 1  # Partial success
        assert api_health.status == HealthStatus.DEGRADED

    def test_get_system_health_weighted_strategy(self, aggregator):
        """Test system health calculation with weighted strategy."""
        # Add components with different weights
        aggregator.component_health["api"] = ComponentHealth(
            "api", HealthStatus.HEALTHY, 0.9, {}, {}, datetime.now().isoformat()
        )
        aggregator.component_health["database"] = ComponentHealth(
            "database", HealthStatus.DEGRADED, 0.6, {}, {}, datetime.now().isoformat()
        )
        aggregator.component_health["cache"] = ComponentHealth(
            "cache", HealthStatus.HEALTHY, 1.0, {}, {}, datetime.now().isoformat()
        )

        system_health = aggregator.get_system_health()

        # Weighted score: (0.9*1.0 + 0.6*1.5 + 1.0*0.5) / (1.0 + 1.5 + 0.5) = 2.3 / 3.0 = 0.767
        expected_score = (0.9 * 1.0 + 0.6 * 1.5 + 1.0 * 0.5) / (1.0 + 1.5 + 0.5)

        assert abs(system_health.score - expected_score) < 0.01
        assert system_health.status == HealthStatus.DEGRADED  # Score < 0.9
        assert system_health.healthy_components == 2  # api and cache
        assert system_health.total_components == 3

    def test_get_system_health_minimum_strategy(self, aggregator):
        """Test system health calculation with minimum strategy."""
        aggregator.config["health"]["aggregation_strategy"] = "minimum"

        aggregator.component_health["comp1"] = ComponentHealth(
            "comp1", HealthStatus.HEALTHY, 0.95, {}, {}, datetime.now().isoformat()
        )
        aggregator.component_health["comp2"] = ComponentHealth(
            "comp2", HealthStatus.DEGRADED, 0.6, {}, {}, datetime.now().isoformat()
        )
        aggregator.component_health["comp3"] = ComponentHealth(
            "comp3", HealthStatus.HEALTHY, 0.9, {}, {}, datetime.now().isoformat()
        )

        system_health = aggregator.get_system_health()

        # Minimum score should be 0.6
        assert system_health.score == 0.6
        assert system_health.status == HealthStatus.DEGRADED

    def test_get_system_health_average_strategy(self, aggregator):
        """Test system health calculation with average strategy."""
        aggregator.config["health"]["aggregation_strategy"] = "average"

        aggregator.component_health["comp1"] = ComponentHealth(
            "comp1", HealthStatus.HEALTHY, 0.8, {}, {}, datetime.now().isoformat()
        )
        aggregator.component_health["comp2"] = ComponentHealth(
            "comp2", HealthStatus.HEALTHY, 1.0, {}, {}, datetime.now().isoformat()
        )

        system_health = aggregator.get_system_health()

        # Average score should be (0.8 + 1.0) / 2 = 0.9
        assert system_health.score == 0.9
        assert system_health.status == HealthStatus.HEALTHY

    def test_add_alert_handler(self, aggregator):
        """Test adding and removing alert handlers."""
        alert_calls = []

        def test_alert_handler(alert_data):
            alert_calls.append(alert_data)

        aggregator.add_alert_handler(test_alert_handler)
        assert len(aggregator.alert_handlers) == 1

        # Trigger an alert
        aggregator._trigger_alert("warning", "test_component", "Test alert")

        assert len(alert_calls) == 1
        alert = alert_calls[0]
        assert alert["level"] == "warning"
        assert alert["component"] == "test_component"
        assert alert["message"] == "Test alert"

        # Remove handler
        aggregator.remove_alert_handler(test_alert_handler)
        assert len(aggregator.alert_handlers) == 0

    def test_status_change_handling(self, aggregator):
        """Test handling of component status changes."""
        alert_calls = []

        def capture_alerts(alert_data):
            alert_calls.append(alert_data)

        aggregator.add_alert_handler(capture_alerts)

        # Test transition to unhealthy
        aggregator._handle_status_change(
            "test_comp", HealthStatus.HEALTHY, HealthStatus.UNHEALTHY
        )

        assert len(alert_calls) == 1
        assert alert_calls[0]["level"] == "critical"
        assert "unhealthy" in alert_calls[0]["message"]

        # Test transition to degraded
        aggregator._handle_status_change(
            "test_comp", HealthStatus.HEALTHY, HealthStatus.DEGRADED
        )

        assert len(alert_calls) == 2
        assert alert_calls[1]["level"] == "warning"
        assert "degraded" in alert_calls[1]["message"]

        # Test recovery
        aggregator._handle_status_change(
            "test_comp", HealthStatus.UNHEALTHY, HealthStatus.HEALTHY
        )

        assert len(alert_calls) == 3
        assert alert_calls[2]["level"] == "info"
        assert "recovered" in alert_calls[2]["message"]

    def test_get_health_history(self, aggregator):
        """Test getting health history for components."""
        # Add some history manually
        timestamp = datetime.now().isoformat()
        aggregator.health_history["test_comp"] = deque(
            [
                {"timestamp": timestamp, "status": "healthy", "score": 0.95},
                {"timestamp": timestamp, "status": "degraded", "score": 0.65},
                {"timestamp": timestamp, "status": "healthy", "score": 0.9},
            ],
            maxlen=50,
        )

        history = aggregator.get_health_history("test_comp")

        assert len(history) == 3
        assert history[0]["status"] == "healthy"
        assert history[1]["status"] == "degraded"
        assert history[2]["status"] == "healthy"

        # Test with limit
        limited_history = aggregator.get_health_history("test_comp", limit=2)
        assert len(limited_history) == 2
        # Should get last 2 entries
        assert limited_history[0]["status"] == "degraded"
        assert limited_history[1]["status"] == "healthy"

        # Test non-existent component
        empty_history = aggregator.get_health_history("nonexistent")
        assert len(empty_history) == 0

    def test_get_health_metrics(self, aggregator):
        """Test getting health metrics summary."""
        # Set up test data
        timestamp = datetime.now().isoformat()
        aggregator.component_health["comp1"] = ComponentHealth(
            "comp1",
            HealthStatus.HEALTHY,
            0.95,
            {},
            {"response_time": 100},
            timestamp,
            0,
        )
        aggregator.component_health["comp2"] = ComponentHealth(
            "comp2", HealthStatus.DEGRADED, 0.65, {}, {"cpu_usage": 80}, timestamp, 2
        )

        aggregator.health_checks.add(HealthCheck("check1", "comp1", CheckType.LIVENESS))
        aggregator.health_checks.add(
            HealthCheck("check2", "comp2", CheckType.READINESS, critical=True)
        )

        metrics = aggregator.get_health_metrics()

        assert "timestamp" in metrics
        assert "system" in metrics
        assert "components" in metrics
        assert "checks" in metrics

        # System metrics
        system = metrics["system"]
        assert system["healthy_components"] == 1
        assert system["total_components"] == 2
        assert 0 <= system["score"] <= 1

        # Component metrics
        components = metrics["components"]
        assert "comp1" in components
        assert "comp2" in components
        assert components["comp1"]["status"] == "healthy"
        assert components["comp2"]["status"] == "degraded"
        assert components["comp2"]["consecutive_failures"] == 2

        # Check metrics
        checks = metrics["checks"]
        assert checks["total"] == 2
        assert checks["enabled"] == 2
        assert checks["critical"] == 1

    def test_export_health_report(self, aggregator):
        """Test exporting detailed health report."""
        # Set up test data
        timestamp = datetime.now().isoformat()
        aggregator.component_health["api"] = ComponentHealth(
            "api",
            HealthStatus.HEALTHY,
            0.95,
            {"liveness": True, "readiness": True},
            {"response_time": 120},
            timestamp,
        )
        aggregator.component_health["database"] = ComponentHealth(
            "database",
            HealthStatus.UNHEALTHY,
            0.2,
            {"connection": False},
            {"connection_pool": 0},
            timestamp,
            consecutive_failures=5,
            error_message="Connection timeout",
        )

        report = aggregator.export_health_report()

        assert "SYSTEM HEALTH REPORT" in report
        assert "Generated:" in report
        assert "CRITICAL ISSUES:" in report
        assert "database: Connection timeout" in report
        assert "API:" in report
        assert "DATABASE:" in report
        assert "Status: healthy" in report
        assert "Status: unhealthy" in report
        assert "✓ liveness" in report
        assert "✗ connection" in report


class TestHealthAggregatorMonitoring:
    """Test health aggregator monitoring functionality."""

    @pytest.fixture
    def monitoring_aggregator(self):
        """Create aggregator configured for monitoring tests."""
        config = {
            "health": {
                "enabled": True,
                "default_interval": 0.05,  # 50ms for fast testing
                "default_timeout": 0.02,
                "history_size": 10,
            }
        }

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)
            aggregator.health_checks.clear()
            aggregator.component_health.clear()
            aggregator.health_history.clear()
            return aggregator

    def test_start_stop_monitoring(self, monitoring_aggregator):
        """Test starting and stopping monitoring."""
        aggregator = monitoring_aggregator

        # Add a test check
        check = HealthCheck(
            "test_check",
            "test_comp",
            CheckType.LIVENESS,
            function=lambda: True,
            interval=1,  # 1 second interval
        )
        aggregator.add_check(check)

        assert aggregator.monitoring_active is False
        assert len(aggregator.check_threads) == 0

        # Start monitoring
        aggregator.start_monitoring()

        assert aggregator.monitoring_active is True
        assert len(aggregator.check_threads) == 1
        assert "test_comp" in aggregator.check_threads

        # Let it run briefly
        time.sleep(0.1)

        # Stop monitoring
        aggregator.stop_monitoring()

        assert aggregator.monitoring_active is False
        assert len(aggregator.check_threads) == 0

    def test_monitoring_component_checks(self, monitoring_aggregator):
        """Test that monitoring performs component checks."""
        aggregator = monitoring_aggregator
        call_count = 0

        def counting_check():
            nonlocal call_count
            call_count += 1
            return True

        check = HealthCheck(
            "counting_check",
            "test_comp",
            CheckType.LIVENESS,
            function=counting_check,
            interval=0.05,  # 50ms interval
        )
        aggregator.add_check(check)

        # Start monitoring
        aggregator.start_monitoring()

        # Wait for multiple check cycles
        time.sleep(0.15)  # Should allow ~3 checks

        # Stop monitoring
        aggregator.stop_monitoring()

        # Verify checks were performed
        assert call_count >= 2  # At least 2 checks should have run

        # Verify component health was updated
        assert "test_comp" in aggregator.component_health
        comp_health = aggregator.component_health["test_comp"]
        assert comp_health.status == HealthStatus.HEALTHY
        assert comp_health.score == 1.0

    def test_monitoring_multiple_components(self, monitoring_aggregator):
        """Test monitoring multiple components simultaneously."""
        aggregator = monitoring_aggregator
        call_counts = {"comp1": 0, "comp2": 0}

        def make_check_function(comp_name):
            def check_func():
                call_counts[comp_name] += 1
                return comp_name == "comp1"  # comp1 succeeds, comp2 fails

            return check_func

        checks = [
            HealthCheck(
                "check1",
                "comp1",
                CheckType.LIVENESS,
                function=make_check_function("comp1"),
                interval=0.05,
            ),
            HealthCheck(
                "check2",
                "comp2",
                CheckType.READINESS,
                function=make_check_function("comp2"),
                interval=0.05,
            ),
        ]

        for check in checks:
            aggregator.add_check(check)

        # Start monitoring
        aggregator.start_monitoring()
        time.sleep(0.12)  # Allow multiple check cycles
        aggregator.stop_monitoring()

        # Verify both components were checked
        assert call_counts["comp1"] >= 1
        assert call_counts["comp2"] >= 1

        # Verify different health states
        comp1_health = aggregator.component_health["comp1"]
        comp2_health = aggregator.component_health["comp2"]

        assert comp1_health.status == HealthStatus.HEALTHY
        assert comp2_health.status == HealthStatus.UNHEALTHY


class TestHealthAggregatorThreadSafety:
    """Test health aggregator thread safety."""

    def test_concurrent_check_execution(self):
        """Test concurrent health check execution."""
        config = {"health": {"enabled": True, "default_interval": 0.01}}

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)
            aggregator.health_checks.clear()
            aggregator.component_health.clear()

        call_counts = {}
        lock = threading.Lock()

        def make_thread_safe_check(comp_name):
            def check_func():
                with lock:
                    if comp_name not in call_counts:
                        call_counts[comp_name] = 0
                    call_counts[comp_name] += 1
                return True

            return check_func

        # Add multiple checks
        for i in range(5):
            check = HealthCheck(
                f"check_{i}",
                f"comp_{i}",
                CheckType.LIVENESS,
                function=make_thread_safe_check(f"comp_{i}"),
            )
            aggregator.add_check(check)

        # Execute checks concurrently
        def execute_checks():
            checks = list(aggregator.health_checks)
            for check in checks:
                try:
                    aggregator._execute_check(check)
                except:
                    pass

        threads = [threading.Thread(target=execute_checks) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify thread safety - all components should have been called
        assert len(call_counts) == 5
        for comp_name, count in call_counts.items():
            assert count == 10  # Each thread executed each check once

    def test_concurrent_status_updates(self):
        """Test concurrent component status updates."""
        config = {"health": {"enabled": True}}

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)
            aggregator.health_checks.clear()
            aggregator.component_health.clear()

        def update_component_status(comp_name, iteration):
            # Simulate component checks with different results
            checks = [
                HealthCheck(
                    f"check_{iteration}",
                    comp_name,
                    CheckType.LIVENESS,
                    function=lambda: iteration % 2 == 0,
                )
            ]
            aggregator._perform_component_checks(comp_name, checks)

        # Concurrent updates to the same component
        threads = []
        for i in range(20):
            thread = threading.Thread(
                target=update_component_status, args=("shared_component", i)
            )
            threads.append(thread)

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify component health exists and is consistent
        assert "shared_component" in aggregator.component_health
        health = aggregator.component_health["shared_component"]
        assert health.component == "shared_component"
        assert isinstance(health.score, float)
        assert 0 <= health.score <= 1


class TestHealthAggregatorPerformance:
    """Test health aggregator performance characteristics."""

    def test_check_execution_performance(self):
        """Test performance of health check execution."""
        config = {"health": {"enabled": True}}

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)
            aggregator.health_checks.clear()

        # Create many simple checks
        checks = []
        for i in range(100):
            check = HealthCheck(
                f"perf_check_{i}",
                f"comp_{i % 10}",
                CheckType.LIVENESS,
                function=lambda: True,
            )
            checks.append(check)

        # Measure execution time
        start_time = time.time()
        for check in checks:
            aggregator._execute_check(check)
        duration = time.time() - start_time

        # Should execute quickly
        assert duration < 1.0  # Less than 1 second for 100 checks
        assert duration / 100 < 0.01  # Less than 10ms per check on average

    def test_metrics_calculation_performance(self):
        """Test performance of metrics calculations."""
        config = {"health": {"enabled": True}}

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)
            aggregator.health_checks.clear()
            aggregator.component_health.clear()

        # Create many components
        timestamp = datetime.now().isoformat()
        for i in range(50):
            aggregator.component_health[f"comp_{i}"] = ComponentHealth(
                f"comp_{i}",
                HealthStatus.HEALTHY,
                0.85 + (i % 10) * 0.01,
                {f"check_{j}": j % 2 == 0 for j in range(5)},
                {f"metric_{j}": i * 10 + j for j in range(3)},
                timestamp,
            )

        # Measure metrics calculation time
        start_time = time.time()
        for _ in range(100):
            system_health = aggregator.get_system_health()
            metrics = aggregator.get_health_metrics()
        duration = time.time() - start_time

        # Should calculate quickly
        assert duration < 1.0  # Less than 1 second for 100 calculations

    def test_large_history_performance(self):
        """Test performance with large health history."""
        config = {"health": {"enabled": True, "history_size": 1000}}

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)

        # Fill history for multiple components
        timestamp = datetime.now().isoformat()
        for comp_name in ["comp1", "comp2", "comp3"]:
            history = deque(maxlen=1000)
            for i in range(1000):
                history.append(
                    {
                        "timestamp": timestamp,
                        "status": "healthy" if i % 2 == 0 else "degraded",
                        "score": 0.5 + (i % 50) * 0.01,
                    }
                )
            aggregator.health_history[comp_name] = history

        # Measure history retrieval performance
        start_time = time.time()
        for _ in range(100):
            for comp_name in ["comp1", "comp2", "comp3"]:
                history = aggregator.get_health_history(comp_name, limit=100)
        duration = time.time() - start_time

        # Should retrieve quickly
        assert duration < 0.5  # Less than 500ms for 300 retrievals


class TestHealthAggregatorEdgeCases:
    """Test health aggregator edge cases."""

    def test_empty_aggregator_behavior(self):
        """Test behavior with no components or checks."""
        config = {"health": {"enabled": True}}

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)
            aggregator.health_checks.clear()
            aggregator.component_health.clear()

        # Should handle empty state gracefully
        system_health = aggregator.get_system_health()

        assert system_health.score == 0.0
        assert system_health.status == HealthStatus.UNKNOWN
        assert system_health.healthy_components == 0
        assert system_health.total_components == 0
        assert len(system_health.critical_issues) == 0
        assert len(system_health.warnings) == 0

        metrics = aggregator.get_health_metrics()
        assert metrics["system"]["total_components"] == 0
        assert len(metrics["components"]) == 0

    def test_invalid_check_configurations(self):
        """Test handling of invalid check configurations."""
        config = {"health": {"enabled": True}}

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)
            aggregator.health_checks.clear()

        # Check with no execution method
        invalid_check = HealthCheck(
            "invalid_check",
            "test_comp",
            CheckType.LIVENESS,
            # No function, endpoint, or command
        )

        # Should return False and not crash
        result = aggregator._execute_check(invalid_check)
        assert result is False

    def test_exception_handling_in_alert_handlers(self):
        """Test exception handling in alert handlers."""
        config = {"health": {"enabled": True}}

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)

        def failing_alert_handler(alert_data):
            raise Exception("Alert handler failed")

        def working_alert_handler(alert_data):
            working_alert_handler.called = True

        working_alert_handler.called = False

        aggregator.add_alert_handler(failing_alert_handler)
        aggregator.add_alert_handler(working_alert_handler)

        # Trigger alert - should not crash despite failing handler
        aggregator._trigger_alert("info", "test_comp", "Test message")

        # Working handler should still be called
        assert working_alert_handler.called is True


@pytest.mark.integration
class TestHealthAggregatorIntegration:
    """Integration tests for health aggregator."""

    def test_kubernetes_probe_compatibility(self):
        """Test compatibility with Kubernetes health probe patterns."""
        config = {"health": {"enabled": True}}

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)
            aggregator.health_checks.clear()

        # Simulate K8s probes
        k8s_checks = [
            HealthCheck(
                "liveness",
                "pod",
                CheckType.LIVENESS,
                endpoint="http://localhost:8080/health/live",
                timeout=1,
                interval=10,
            ),
            HealthCheck(
                "readiness",
                "pod",
                CheckType.READINESS,
                endpoint="http://localhost:8080/health/ready",
                timeout=1,
                interval=5,
            ),
            HealthCheck(
                "startup",
                "pod",
                CheckType.STARTUP,
                endpoint="http://localhost:8080/health/startup",
                timeout=1,
                interval=30,
            ),
        ]

        for check in k8s_checks:
            aggregator.add_check(check)

        # Mock HTTP responses
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Execute checks
            for check in k8s_checks:
                result = aggregator._execute_check(check)
                assert result is True

        # Verify component health
        pod_health = aggregator.component_health["pod"]
        assert pod_health.status == HealthStatus.HEALTHY
        assert pod_health.checks["liveness"] is True
        assert pod_health.checks["readiness"] is True
        assert pod_health.checks["startup"] is True

    def test_real_world_monitoring_scenario(self):
        """Test realistic monitoring scenario with multiple components."""
        config = {
            "health": {
                "enabled": True,
                "aggregation_strategy": "weighted",
                "component_weights": {
                    "api": 2.0,  # Critical
                    "database": 2.0,  # Critical
                    "cache": 1.0,  # Important
                    "metrics": 0.5,  # Nice to have
                },
            }
        }

        with patch("os.path.exists", return_value=True):
            aggregator = HealthAggregator(config)
            aggregator.health_checks.clear()
            aggregator.component_health.clear()

        # Simulate real-world component states
        timestamp = datetime.now().isoformat()

        # API: Healthy
        aggregator.component_health["api"] = ComponentHealth(
            "api",
            HealthStatus.HEALTHY,
            0.95,
            {"liveness": True, "readiness": True, "dependency_check": True},
            {"response_time_ms": 120, "error_rate": 0.001},
            timestamp,
        )

        # Database: Degraded
        aggregator.component_health["database"] = ComponentHealth(
            "database",
            HealthStatus.DEGRADED,
            0.7,
            {"connection": True, "replication": False, "backup": True},
            {"connection_pool_usage": 85, "query_time_ms": 350},
            timestamp,
            consecutive_failures=1,
        )

        # Cache: Healthy
        aggregator.component_health["cache"] = ComponentHealth(
            "cache",
            HealthStatus.HEALTHY,
            0.9,
            {"connection": True, "memory": True},
            {"hit_rate": 92, "memory_usage": 65},
            timestamp,
        )

        # Metrics: Unhealthy (but low weight)
        aggregator.component_health["metrics"] = ComponentHealth(
            "metrics",
            HealthStatus.UNHEALTHY,
            0.2,
            {"collector": False, "storage": True},
            {"collection_rate": 0.1},
            timestamp,
            consecutive_failures=3,
        )

        system_health = aggregator.get_system_health()

        # Weighted calculation:
        # (0.95*2 + 0.7*2 + 0.9*1 + 0.2*0.5) / (2+2+1+0.5) = 4.2 / 5.5 ≈ 0.76
        expected_score = (0.95 * 2 + 0.7 * 2 + 0.9 * 1 + 0.2 * 0.5) / (2 + 2 + 1 + 0.5)

        assert abs(system_health.score - expected_score) < 0.02
        assert system_health.status == HealthStatus.DEGRADED
        assert system_health.healthy_components == 2  # api, cache
        assert system_health.total_components == 4

        # Should have issues and warnings
        assert len(system_health.critical_issues) > 0
        assert any("metrics" in issue for issue in system_health.critical_issues)


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_health_aggregator_singleton(self):
        """Test global health aggregator singleton."""
        # Clear any existing instance
        import lib.integration.health_aggregator as ha_module

        ha_module._health_aggregator = None

        # Get aggregator instances
        agg1 = get_health_aggregator()
        agg2 = get_health_aggregator()

        # Should be the same instance
        assert agg1 is agg2
        assert isinstance(agg1, HealthAggregator)

    def test_get_system_health_convenience(self):
        """Test convenience function for getting system health."""
        # Use the global aggregator
        system_health = get_system_health()

        assert isinstance(system_health, SystemHealth)
        assert hasattr(system_health, "status")
        assert hasattr(system_health, "score")

    def test_add_health_check_convenience(self):
        """Test convenience function for adding health checks."""
        check = HealthCheck(
            "global_check", "global_comp", CheckType.LIVENESS, function=lambda: True
        )

        # Should not raise exception
        add_health_check(check)

        # Verify it was added to global aggregator
        aggregator = get_health_aggregator()
        assert check in aggregator.health_checks
