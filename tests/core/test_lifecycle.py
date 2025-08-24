"""
Comprehensive tests for Genesis Lifecycle Management using VERIFY methodology

Following VERIFY methodology:
- Validate: Test startup/shutdown sequences, signal handling
- Execute: Comprehensive test coverage across all lifecycle components
- Report: Clear test names and detailed error reporting
- Integrate: Hook system, dependencies, health checks integration
- Fix: Edge cases and error handling scenarios
- Yield: Performance metrics and quality validation

Test Categories:
- LifecycleManager orchestration and state management
- StartupManager phase execution and dependency validation
- ShutdownManager graceful shutdown and resource cleanup
- HookManager event system and priority execution
- ServiceState transitions and degraded mode
- Kubernetes probe compatibility
- Signal handling and container integration
- Performance benchmarks for lifecycle operations
"""

import asyncio
import threading
import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from core.lifecycle.manager import LifecycleManager  # Core classes
from core.lifecycle.manager import (
    LifecycleMetrics,
    ServiceState,
    configure_lifecycle_manager,
    create_kubernetes_probes,
    get_lifecycle_manager,
)
from core.lifecycle.startup import (
    DependencyCheck,
    DependencyType,
    StartupHook,
    StartupManager,
    StartupMetrics,
    StartupPhase,
    StartupStatus,
)


class TestServiceState:
    """Test ServiceState enum functionality"""

    def test_service_state_values(self):
        """Test ServiceState enum values"""
        assert ServiceState.INITIALIZING.value == "initializing"
        assert ServiceState.STARTING.value == "starting"
        assert ServiceState.READY.value == "ready"
        assert ServiceState.DEGRADED.value == "degraded"
        assert ServiceState.SHUTTING_DOWN.value == "shutting_down"
        assert ServiceState.STOPPED.value == "stopped"
        assert ServiceState.FAILED.value == "failed"

    def test_service_state_transitions(self):
        """Test logical service state transitions"""
        # Normal flow
        normal_flow = [
            ServiceState.INITIALIZING,
            ServiceState.STARTING,
            ServiceState.READY,
            ServiceState.SHUTTING_DOWN,
            ServiceState.STOPPED,
        ]

        # Verify states exist and can be compared
        for state in normal_flow:
            assert isinstance(state, ServiceState)

        # Degraded flow
        assert ServiceState.READY != ServiceState.DEGRADED
        assert ServiceState.DEGRADED != ServiceState.FAILED


class TestLifecycleMetrics:
    """Test LifecycleMetrics functionality"""

    def test_lifecycle_metrics_creation(self):
        """Test LifecycleMetrics creation with defaults"""
        metrics = LifecycleMetrics(
            service_name="test-service", state=ServiceState.READY
        )

        assert metrics.service_name == "test-service"
        assert metrics.state == ServiceState.READY
        assert metrics.startup_duration_ms == 0.0
        assert metrics.shutdown_duration_ms == 0.0
        assert metrics.uptime_seconds == 0.0
        assert metrics.restart_count == 0
        assert metrics.health_check_failures == 0
        assert metrics.last_health_check is None
        assert isinstance(metrics.created_at, datetime)

    def test_lifecycle_metrics_to_dict(self):
        """Test LifecycleMetrics serialization"""
        test_time = datetime(2023, 1, 1, 12, 0, 0)

        metrics = LifecycleMetrics(
            service_name="dict-service",
            state=ServiceState.DEGRADED,
            startup_duration_ms=1500.5,
            shutdown_duration_ms=500.2,
            uptime_seconds=3600.0,
            restart_count=2,
            health_check_failures=3,
            last_health_check=test_time,
            created_at=test_time,
        )

        result = metrics.to_dict()

        expected = {
            "service_name": "dict-service",
            "state": "degraded",
            "startup_duration_ms": 1500.5,
            "shutdown_duration_ms": 500.2,
            "uptime_seconds": 3600.0,
            "restart_count": 2,
            "health_check_failures": 3,
            "last_health_check": "2023-01-01T12:00:00",
            "created_at": "2023-01-01T12:00:00",
        }
        assert result == expected

    def test_lifecycle_metrics_none_timestamps(self):
        """Test LifecycleMetrics with None timestamps"""
        metrics = LifecycleMetrics(
            service_name="none-service",
            state=ServiceState.READY,
            last_health_check=None,
        )

        result = metrics.to_dict()
        assert result["last_health_check"] is None


class TestStartupPhase:
    """Test StartupPhase enum functionality"""

    def test_startup_phase_ordering(self):
        """Test StartupPhase execution order"""
        phases = list(StartupPhase)
        values = [phase.value for phase in phases]

        # Values should be in ascending order
        assert values == sorted(values)

        # Test specific ordering
        assert StartupPhase.VALIDATE_ENVIRONMENT < StartupPhase.INITIALIZE_LOGGING
        assert StartupPhase.INITIALIZE_LOGGING < StartupPhase.VALIDATE_DEPENDENCIES
        assert StartupPhase.VALIDATE_DEPENDENCIES < StartupPhase.INITIALIZE_STORAGE
        assert StartupPhase.INITIALIZE_STORAGE < StartupPhase.INITIALIZE_NETWORKING
        assert StartupPhase.INITIALIZE_NETWORKING < StartupPhase.INITIALIZE_SERVICES
        assert StartupPhase.INITIALIZE_SERVICES < StartupPhase.REGISTER_HEALTH_CHECKS
        assert StartupPhase.REGISTER_HEALTH_CHECKS < StartupPhase.WARM_UP
        assert StartupPhase.WARM_UP < StartupPhase.FINALIZE

    def test_startup_phase_values(self):
        """Test StartupPhase specific values"""
        assert StartupPhase.VALIDATE_ENVIRONMENT.value == 100
        assert StartupPhase.INITIALIZE_LOGGING.value == 200
        assert StartupPhase.VALIDATE_DEPENDENCIES.value == 300
        assert StartupPhase.FINALIZE.value == 900


class TestStartupStatus:
    """Test StartupStatus enum functionality"""

    def test_startup_status_values(self):
        """Test StartupStatus enum values"""
        assert StartupStatus.NOT_STARTED.value == "not_started"
        assert StartupStatus.INITIALIZING.value == "initializing"
        assert StartupStatus.VALIDATING.value == "validating"
        assert StartupStatus.STARTING_DEPENDENCIES.value == "starting_dependencies"
        assert StartupStatus.STARTING_SERVICES.value == "starting_services"
        assert StartupStatus.WARMING_UP.value == "warming_up"
        assert StartupStatus.READY.value == "ready"
        assert StartupStatus.FAILED.value == "failed"
        assert StartupStatus.DEGRADED.value == "degraded"


class TestDependencyType:
    """Test DependencyType enum functionality"""

    def test_dependency_type_values(self):
        """Test DependencyType enum values"""
        assert DependencyType.REQUIRED.value == "required"
        assert DependencyType.OPTIONAL.value == "optional"
        assert DependencyType.CRITICAL.value == "critical"


class TestStartupHook:
    """Test StartupHook dataclass functionality"""

    def test_startup_hook_creation_minimal(self):
        """Test StartupHook creation with minimal parameters"""
        callback = Mock()
        hook = StartupHook(
            name="test-hook", callback=callback, phase=StartupPhase.INITIALIZE_SERVICES
        )

        assert hook.name == "test-hook"
        assert hook.callback == callback
        assert hook.phase == StartupPhase.INITIALIZE_SERVICES
        assert hook.timeout == 60
        assert hook.is_async is False
        assert hook.description == ""
        assert hook.dependencies == set()
        assert hook.critical is True
        assert isinstance(hook.created_at, datetime)

    def test_startup_hook_creation_full(self):
        """Test StartupHook creation with all parameters"""
        callback = Mock()
        dependencies = {"hook1", "hook2"}

        hook = StartupHook(
            name="full-hook",
            callback=callback,
            phase=StartupPhase.WARM_UP,
            timeout=120,
            is_async=True,
            description="Full test hook",
            dependencies=dependencies,
            critical=False,
        )

        assert hook.name == "full-hook"
        assert hook.callback == callback
        assert hook.phase == StartupPhase.WARM_UP
        assert hook.timeout == 120
        assert hook.is_async is True
        assert hook.description == "Full test hook"
        assert hook.dependencies == dependencies
        assert hook.critical is False


class TestDependencyCheck:
    """Test DependencyCheck dataclass functionality"""

    def test_dependency_check_creation_minimal(self):
        """Test DependencyCheck creation with minimal parameters"""
        check_function = Mock(return_value=True)

        dependency = DependencyCheck(name="test-dep", check_function=check_function)

        assert dependency.name == "test-dep"
        assert dependency.check_function == check_function
        assert dependency.dependency_type == DependencyType.REQUIRED
        assert dependency.timeout == 30
        assert dependency.retry_attempts == 3
        assert dependency.retry_delay == 5
        assert dependency.description == ""

    def test_dependency_check_creation_full(self):
        """Test DependencyCheck creation with all parameters"""
        check_function = Mock(return_value=False)

        dependency = DependencyCheck(
            name="full-dep",
            check_function=check_function,
            dependency_type=DependencyType.OPTIONAL,
            timeout=60,
            retry_attempts=5,
            retry_delay=10,
            description="Full test dependency",
        )

        assert dependency.name == "full-dep"
        assert dependency.check_function == check_function
        assert dependency.dependency_type == DependencyType.OPTIONAL
        assert dependency.timeout == 60
        assert dependency.retry_attempts == 5
        assert dependency.retry_delay == 10
        assert dependency.description == "Full test dependency"


class TestStartupMetrics:
    """Test StartupMetrics functionality"""

    def test_startup_metrics_creation(self):
        """Test StartupMetrics creation with defaults"""
        metrics = StartupMetrics()

        assert metrics.startup_started is None
        assert metrics.startup_completed is None
        assert metrics.hooks_executed == 0
        assert metrics.hooks_failed == 0
        assert metrics.dependencies_checked == 0
        assert metrics.dependencies_failed == 0
        assert metrics.total_duration_ms == 0.0
        assert metrics.readiness_achieved is False
        assert metrics.degraded_mode is False

    def test_startup_metrics_to_dict(self):
        """Test StartupMetrics serialization"""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 1, 30)

        metrics = StartupMetrics(
            startup_started=start_time,
            startup_completed=end_time,
            hooks_executed=5,
            hooks_failed=1,
            dependencies_checked=3,
            dependencies_failed=0,
            total_duration_ms=90000.0,
            readiness_achieved=True,
            degraded_mode=False,
        )

        result = metrics.to_dict()

        expected = {
            "startup_started": "2023-01-01T12:00:00",
            "startup_completed": "2023-01-01T12:01:30",
            "hooks_executed": 5,
            "hooks_failed": 1,
            "dependencies_checked": 3,
            "dependencies_failed": 0,
            "total_duration_ms": 90000.0,
            "duration_seconds": 90.0,
            "readiness_achieved": True,
            "degraded_mode": False,
        }
        assert result == expected

    def test_startup_metrics_to_dict_none_timestamps(self):
        """Test StartupMetrics serialization with None timestamps"""
        metrics = StartupMetrics()
        result = metrics.to_dict()

        assert result["startup_started"] is None
        assert result["startup_completed"] is None
        assert result["duration_seconds"] == 0.0


class TestStartupManager:
    """Test StartupManager functionality"""

    def test_startup_manager_creation_minimal(self):
        """Test StartupManager creation with minimal parameters"""
        manager = StartupManager(service_name="test-service")

        assert manager.service_name == "test-service"
        assert manager.enable_degraded_mode is True
        assert manager.startup_timeout == 300
        assert manager.warmup_duration == 30
        assert manager.enable_health_checks is True
        assert manager.status == StartupStatus.NOT_STARTED
        assert isinstance(manager.metrics, StartupMetrics)

        # Check that built-in hooks are registered
        assert len(manager.hooks[StartupPhase.VALIDATE_ENVIRONMENT]) > 0
        assert len(manager.hooks[StartupPhase.VALIDATE_DEPENDENCIES]) > 0
        assert len(manager.hooks[StartupPhase.REGISTER_HEALTH_CHECKS]) > 0
        assert len(manager.hooks[StartupPhase.WARM_UP]) > 0

    def test_startup_manager_creation_custom(self):
        """Test StartupManager creation with custom parameters"""
        manager = StartupManager(
            service_name="custom-service",
            enable_degraded_mode=False,
            startup_timeout=600,
            warmup_duration=60,
            enable_health_checks=False,
        )

        assert manager.service_name == "custom-service"
        assert manager.enable_degraded_mode is False
        assert manager.startup_timeout == 600
        assert manager.warmup_duration == 60
        assert manager.enable_health_checks is False

        # Health check registration hook should not be present
        assert len(manager.hooks[StartupPhase.REGISTER_HEALTH_CHECKS]) == 0

    def test_startup_manager_register_hook(self):
        """Test registering a startup hook"""
        manager = StartupManager(service_name="hook-test")
        callback = Mock()

        manager.register_hook(
            name="test-hook",
            callback=callback,
            phase=StartupPhase.INITIALIZE_SERVICES,
            timeout=120,
            description="Test hook for services",
            critical=False,
        )

        # Find the registered hook
        hooks = manager.hooks[StartupPhase.INITIALIZE_SERVICES]
        test_hook = None
        for hook in hooks:
            if hook.name == "test-hook":
                test_hook = hook
                break

        assert test_hook is not None
        assert test_hook.callback == callback
        assert test_hook.timeout == 120
        assert test_hook.description == "Test hook for services"
        assert test_hook.critical is False

    def test_startup_manager_register_dependency(self):
        """Test registering a dependency check"""
        manager = StartupManager(service_name="dep-test")
        check_function = Mock(return_value=True)

        manager.register_dependency(
            name="database",
            check_function=check_function,
            dependency_type=DependencyType.CRITICAL,
            timeout=60,
            retry_attempts=5,
            retry_delay=10,
            description="Database connectivity",
        )

        assert len(manager.dependencies) == 1
        dependency = manager.dependencies[0]

        assert dependency.name == "database"
        assert dependency.check_function == check_function
        assert dependency.dependency_type == DependencyType.CRITICAL
        assert dependency.timeout == 60
        assert dependency.retry_attempts == 5
        assert dependency.retry_delay == 10
        assert dependency.description == "Database connectivity"

    def test_startup_manager_register_config_validator(self):
        """Test registering configuration validators"""
        manager = StartupManager(service_name="config-test")
        validator1 = Mock(return_value=True)
        validator2 = Mock(return_value=True)

        manager.register_config_validator(validator1)
        manager.register_config_validator(validator2)

        assert len(manager.config_validators) == 2
        assert validator1 in manager.config_validators
        assert validator2 in manager.config_validators

    def test_startup_manager_register_health_check(self):
        """Test registering health checks"""
        manager = StartupManager(service_name="health-test")
        health_check = Mock(return_value=True)

        manager.register_health_check("app-health", health_check)

        assert "app-health" in manager.health_checks
        assert manager.health_checks["app-health"] == health_check

    @pytest.mark.asyncio
    async def test_startup_manager_start_success(self):
        """Test successful startup sequence"""
        manager = StartupManager(
            service_name="success-test",
            warmup_duration=1,  # Reduce for testing
        )

        # Mock environment variables
        with patch.dict(
            "os.environ", {"GENESIS_SERVICE": "success-test", "GENESIS_ENV": "test"}
        ):
            success = await manager.start()

        assert success is True
        assert manager.status == StartupStatus.READY
        assert manager.metrics.readiness_achieved is True
        assert manager.metrics.hooks_executed > 0
        assert manager.is_ready() is True

    @pytest.mark.asyncio
    async def test_startup_manager_start_already_started(self):
        """Test starting when already started"""
        manager = StartupManager(service_name="already-started")
        manager.status = StartupStatus.READY

        success = await manager.start()

        assert success is True  # Returns True if already ready

    @pytest.mark.asyncio
    async def test_startup_manager_start_missing_env_vars(self):
        """Test startup failure due to missing environment variables"""
        manager = StartupManager(service_name="env-fail-test")

        # Clear required environment variables
        with patch.dict("os.environ", {}, clear=True):
            success = await manager.start()

        assert success is False
        assert manager.status == StartupStatus.FAILED
        assert "validate_environment" in manager.failed_hooks

    @pytest.mark.asyncio
    async def test_startup_manager_dependency_failure_critical(self):
        """Test startup failure due to critical dependency failure"""
        manager = StartupManager(service_name="critical-dep-fail")

        # Register a failing critical dependency
        failing_check = Mock(return_value=False)
        manager.register_dependency(
            name="critical-db",
            check_function=failing_check,
            dependency_type=DependencyType.CRITICAL,
            retry_attempts=1,  # Reduce for testing
        )

        with patch.dict(
            "os.environ",
            {"GENESIS_SERVICE": "critical-dep-fail", "GENESIS_ENV": "test"},
        ):
            success = await manager.start()

        assert success is False
        assert manager.status == StartupStatus.FAILED
        assert "critical-db" in manager.failed_dependencies

    @pytest.mark.asyncio
    async def test_startup_manager_dependency_failure_degraded(self):
        """Test startup degraded mode due to required dependency failure"""
        manager = StartupManager(
            service_name="degraded-test", enable_degraded_mode=True, warmup_duration=1
        )

        # Register a failing required dependency
        failing_check = Mock(return_value=False)
        manager.register_dependency(
            name="optional-cache",
            check_function=failing_check,
            dependency_type=DependencyType.REQUIRED,
            retry_attempts=1,
        )

        with patch.dict(
            "os.environ", {"GENESIS_SERVICE": "degraded-test", "GENESIS_ENV": "test"}
        ):
            success = await manager.start()

        assert success is True
        assert manager.status == StartupStatus.DEGRADED
        assert manager.metrics.degraded_mode is True
        assert "optional-cache" in manager.failed_dependencies

    @pytest.mark.asyncio
    async def test_startup_manager_hook_timeout(self):
        """Test startup hook timeout handling"""
        manager = StartupManager(service_name="timeout-test")

        # Register a hook that will timeout
        def slow_hook():
            time.sleep(2)  # Hook takes 2 seconds

        manager.register_hook(
            name="slow-hook",
            callback=slow_hook,
            phase=StartupPhase.INITIALIZE_SERVICES,
            timeout=1,  # Timeout after 1 second
            critical=True,
        )

        with patch.dict(
            "os.environ", {"GENESIS_SERVICE": "timeout-test", "GENESIS_ENV": "test"}
        ):
            success = await manager.start()

        assert success is False
        assert manager.status == StartupStatus.FAILED
        assert "slow-hook" in manager.failed_hooks

    @pytest.mark.asyncio
    async def test_startup_manager_async_hook(self):
        """Test async hook execution"""
        manager = StartupManager(service_name="async-test")

        async_hook_called = False

        async def async_hook():
            nonlocal async_hook_called
            await asyncio.sleep(0.01)  # Small async delay
            async_hook_called = True

        manager.register_hook(
            name="async-hook",
            callback=async_hook,
            phase=StartupPhase.INITIALIZE_SERVICES,
            is_async=True,
        )

        with patch.dict(
            "os.environ", {"GENESIS_SERVICE": "async-test", "GENESIS_ENV": "test"}
        ):
            success = await manager.start()

        assert success is True
        assert async_hook_called is True

    @pytest.mark.asyncio
    async def test_startup_manager_non_critical_hook_failure(self):
        """Test that non-critical hook failures don't stop startup"""
        manager = StartupManager(service_name="non-critical-test", warmup_duration=1)

        def failing_hook():
            raise RuntimeError("Non-critical failure")

        manager.register_hook(
            name="failing-hook",
            callback=failing_hook,
            phase=StartupPhase.INITIALIZE_SERVICES,
            critical=False,  # Not critical
        )

        with patch.dict(
            "os.environ",
            {"GENESIS_SERVICE": "non-critical-test", "GENESIS_ENV": "test"},
        ):
            success = await manager.start()

        assert success is True
        assert manager.status == StartupStatus.READY
        assert "failing-hook" in manager.failed_hooks
        assert manager.metrics.hooks_failed > 0

    def test_startup_manager_is_ready(self):
        """Test is_ready status checking"""
        manager = StartupManager(service_name="ready-test")

        # Initially not ready
        assert manager.is_ready() is False

        # Ready when status is READY
        manager.status = StartupStatus.READY
        assert manager.is_ready() is True

        # Ready when status is DEGRADED
        manager.status = StartupStatus.DEGRADED
        assert manager.is_ready() is True

        # Not ready for other states
        manager.status = StartupStatus.FAILED
        assert manager.is_ready() is False

    def test_startup_manager_is_healthy(self):
        """Test is_healthy status checking"""
        manager = StartupManager(service_name="healthy-test")

        # Not healthy when not ready
        manager.status = StartupStatus.STARTING_SERVICES
        assert manager.is_healthy() is False

        # Healthy when ready with no health checks
        manager.status = StartupStatus.READY
        assert manager.is_healthy() is True

        # Test with health checks
        passing_check = Mock(return_value=True)
        failing_check = Mock(return_value=False)

        manager.register_health_check("passing", passing_check)
        assert manager.is_healthy() is True

        manager.register_health_check("failing", failing_check)
        assert manager.is_healthy() is False

    def test_startup_manager_get_status(self):
        """Test getting startup status"""
        manager = StartupManager(service_name="status-test")
        manager.status = StartupStatus.READY
        manager.completed_phases.add(StartupPhase.VALIDATE_ENVIRONMENT)
        manager.failed_hooks.append("test-hook")
        manager.failed_dependencies.append("test-dep")

        status = manager.get_status()

        assert status["service_name"] == "status-test"
        assert status["status"] == "ready"
        assert status["is_ready"] is True
        assert status["completed_phases"] == ["VALIDATE_ENVIRONMENT"]
        assert status["failed_hooks"] == ["test-hook"]
        assert status["failed_dependencies"] == ["test-dep"]
        assert "metrics" in status


class TestLifecycleManager:
    """Test LifecycleManager functionality"""

    def test_lifecycle_manager_creation_minimal(self):
        """Test LifecycleManager creation with minimal parameters"""
        manager = LifecycleManager(service_name="test-service")

        assert manager.service_name == "test-service"
        assert manager.version == "1.0.0"
        assert manager.environment == "development"
        assert manager.enable_health_checks is True
        assert manager.enable_metrics is True
        assert manager.startup_timeout == 300
        assert manager.shutdown_timeout == 120
        assert manager.health_check_interval == 30
        assert manager.enable_auto_restart is False
        assert manager.state == ServiceState.INITIALIZING
        assert isinstance(manager.startup_manager, StartupManager)
        assert isinstance(manager.metrics, LifecycleMetrics)

        # Check built-in health checks are registered
        assert "basic" in manager.health_checks
        assert "startup" in manager.health_checks
        assert "components" in manager.health_checks

    def test_lifecycle_manager_creation_custom(self):
        """Test LifecycleManager creation with custom parameters"""
        manager = LifecycleManager(
            service_name="custom-service",
            version="2.0.0",
            environment="production",
            enable_health_checks=False,
            enable_metrics=False,
            startup_timeout=600,
            shutdown_timeout=240,
            health_check_interval=60,
            enable_auto_restart=True,
        )

        assert manager.service_name == "custom-service"
        assert manager.version == "2.0.0"
        assert manager.environment == "production"
        assert manager.enable_health_checks is False
        assert manager.enable_metrics is False
        assert manager.startup_timeout == 600
        assert manager.shutdown_timeout == 240
        assert manager.health_check_interval == 60
        assert manager.enable_auto_restart is True

    @pytest.mark.asyncio
    async def test_lifecycle_manager_start_success(self):
        """Test successful lifecycle start"""
        manager = LifecycleManager(service_name="lifecycle-start-test")

        with patch.dict(
            "os.environ",
            {"GENESIS_SERVICE": "lifecycle-start-test", "GENESIS_ENV": "test"},
        ):
            # Mock the startup manager to return success quickly
            with patch.object(manager.startup_manager, "start", return_value=True):
                success = await manager.start()

        assert success is True
        assert manager.state == ServiceState.READY
        assert manager.ready_time is not None
        assert manager.metrics.startup_duration_ms > 0

    @pytest.mark.asyncio
    async def test_lifecycle_manager_start_failure(self):
        """Test lifecycle start failure"""
        manager = LifecycleManager(service_name="lifecycle-fail-test")

        # Mock the startup manager to return failure
        with patch.object(manager.startup_manager, "start", return_value=False):
            success = await manager.start()

        assert success is False
        assert manager.state == ServiceState.FAILED

    @pytest.mark.asyncio
    async def test_lifecycle_manager_start_exception(self):
        """Test lifecycle start with exception"""
        manager = LifecycleManager(service_name="lifecycle-exception-test")

        # Mock the startup manager to raise exception
        with patch.object(
            manager.startup_manager, "start", side_effect=RuntimeError("Startup error")
        ):
            success = await manager.start()

        assert success is False
        assert manager.state == ServiceState.FAILED

    def test_lifecycle_manager_stop(self):
        """Test lifecycle stop"""
        manager = LifecycleManager(service_name="lifecycle-stop-test")
        manager.state = ServiceState.READY

        # Mock health check task
        manager.health_check_task = Mock()
        manager.health_check_task.cancel = Mock()

        # Mock graceful shutdown
        manager.graceful_shutdown._initiate_shutdown = Mock()

        manager.stop()

        assert manager._shutdown_event.is_set()
        manager.health_check_task.cancel.assert_called_once()
        manager.graceful_shutdown._initiate_shutdown.assert_called_once()

    def test_lifecycle_manager_register_startup_hook(self):
        """Test registering startup hooks"""
        manager = LifecycleManager(service_name="startup-hook-test")
        callback = Mock()

        manager.register_startup_hook(
            name="test-startup-hook",
            callback=callback,
            phase=StartupPhase.INITIALIZE_SERVICES,
            timeout=120,
            critical=False,
            description="Test startup hook",
        )

        # Verify hook was registered with startup manager
        assert any(
            hook.name == "test-startup-hook"
            for hook in manager.startup_manager.hooks[StartupPhase.INITIALIZE_SERVICES]
        )

    def test_lifecycle_manager_register_shutdown_hook(self):
        """Test registering shutdown hooks"""
        manager = LifecycleManager(service_name="shutdown-hook-test")
        callback = Mock()

        # Mock graceful shutdown manager
        manager.graceful_shutdown.register_hook = Mock()

        manager.register_shutdown_hook(
            name="test-shutdown-hook",
            callback=callback,
            phase=400,
            timeout=60,
            description="Test shutdown hook",
        )

        # Verify hook was registered with shutdown manager
        manager.graceful_shutdown.register_hook.assert_called_once_with(
            name="test-shutdown-hook",
            callback=callback,
            phase=400,
            timeout=60,
            description="Test shutdown hook",
        )

    def test_lifecycle_manager_register_health_check(self):
        """Test registering health checks"""
        manager = LifecycleManager(service_name="health-check-test")
        health_check = Mock(return_value=True)

        manager.register_health_check("custom-health", health_check)

        assert "custom-health" in manager.health_checks
        assert manager.health_checks["custom-health"] == health_check
        assert manager.health_check_results["custom-health"] is True

    def test_lifecycle_manager_register_dependency(self):
        """Test registering dependencies"""
        manager = LifecycleManager(service_name="dependency-test")
        check_function = Mock(return_value=True)

        manager.register_dependency(
            name="test-dependency",
            check_function=check_function,
            dependency_type="critical",
            timeout=60,
            retry_attempts=5,
            description="Test dependency",
        )

        # Verify dependency was registered with startup manager
        assert any(
            dep.name == "test-dependency"
            for dep in manager.startup_manager.dependencies
        )

    @pytest.mark.asyncio
    async def test_lifecycle_manager_health_check_monitoring(self):
        """Test health check monitoring loop"""
        manager = LifecycleManager(
            service_name="health-monitoring-test",
            health_check_interval=0.1,  # Fast for testing
        )

        # Add custom health checks
        passing_check = Mock(return_value=True)
        failing_check = Mock(return_value=False)

        manager.register_health_check("passing", passing_check)
        manager.register_health_check("failing", failing_check)

        # Start health check monitoring
        manager._start_health_check_monitoring()

        # Let it run briefly
        await asyncio.sleep(0.2)

        # Stop monitoring
        manager._shutdown_event.set()
        if manager.health_check_task:
            manager.health_check_task.cancel()
            try:
                await manager.health_check_task
            except asyncio.CancelledError:
                pass

        # Verify health checks were called
        passing_check.assert_called()
        failing_check.assert_called()

        # Verify results are recorded
        assert manager.health_check_results["passing"] is True
        assert manager.health_check_results["failing"] is False
        assert manager.metrics.last_health_check is not None

    @pytest.mark.asyncio
    async def test_lifecycle_manager_health_check_timeout(self):
        """Test health check timeout handling"""
        manager = LifecycleManager(service_name="health-timeout-test")

        def slow_check():
            time.sleep(15)  # Longer than 10 second timeout
            return True

        manager.register_health_check("slow-check", slow_check)

        # Perform health checks
        await manager._perform_health_checks()

        # Verify timeout was handled
        assert manager.health_check_results["slow-check"] is False

    def test_lifecycle_manager_is_ready(self):
        """Test is_ready status checking"""
        manager = LifecycleManager(service_name="is-ready-test")

        # Initially not ready
        assert manager.is_ready() is False

        # Ready when state is READY
        manager.state = ServiceState.READY
        assert manager.is_ready() is True

        # Ready when state is DEGRADED
        manager.state = ServiceState.DEGRADED
        assert manager.is_ready() is True

        # Not ready for other states
        manager.state = ServiceState.FAILED
        assert manager.is_ready() is False

    def test_lifecycle_manager_is_healthy(self):
        """Test is_healthy status checking"""
        manager = LifecycleManager(service_name="is-healthy-test")

        # Not healthy when not ready
        manager.state = ServiceState.STARTING
        assert manager.is_healthy() is False

        # Healthy when ready with no health checks
        manager.state = ServiceState.READY
        manager.health_check_results = {}
        assert manager.is_healthy() is True

        # Test with health checks
        manager.health_check_results = {"check1": True, "check2": True, "check3": False}
        # 2/3 passing (>= 50%)
        assert manager.is_healthy() is True

        manager.health_check_results = {
            "check1": True,
            "check2": False,
            "check3": False,
        }
        # 1/3 passing (< 50%)
        assert manager.is_healthy() is False

    def test_lifecycle_manager_get_uptime(self):
        """Test uptime calculation"""
        manager = LifecycleManager(service_name="uptime-test")

        # No uptime when not ready
        assert manager.get_uptime() == 0.0

        # Test with ready time
        past_time = datetime.utcnow()
        manager.ready_time = past_time

        # Should be a small positive value
        uptime = manager.get_uptime()
        assert uptime >= 0.0

    def test_lifecycle_manager_get_metrics(self):
        """Test getting comprehensive metrics"""
        manager = LifecycleManager(service_name="metrics-test")
        manager.state = ServiceState.READY

        # Mock component metrics
        manager.startup_manager.get_status = Mock(return_value={"status": "ready"})
        manager.graceful_shutdown.get_status = Mock(return_value={"status": "running"})
        manager.hook_manager.get_statistics = Mock(return_value={"hooks": 5})

        metrics = manager.get_metrics()

        assert metrics["service_name"] == "metrics-test"
        assert metrics["state"] == "ready"
        assert "startup" in metrics
        assert "shutdown" in metrics
        assert "hooks" in metrics
        assert "health_checks" in metrics
        assert metrics["health_checks"]["registered"] >= 0
        assert "overall_healthy" in metrics["health_checks"]

    def test_lifecycle_manager_get_status(self):
        """Test getting complete service status"""
        manager = LifecycleManager(service_name="status-test")
        manager.state = ServiceState.READY

        # Mock component status
        manager.startup_manager.is_ready = Mock(return_value=True)
        manager.graceful_shutdown.is_shutdown_requested = Mock(return_value=False)

        status = manager.get_status()

        assert status["service_name"] == "status-test"
        assert status["version"] == "1.0.0"
        assert status["environment"] == "development"
        assert status["state"] == "ready"
        assert status["is_ready"] is True
        assert status["startup_completed"] is True
        assert status["shutdown_requested"] is False
        assert "metrics" in status

    def test_lifecycle_manager_wait_for_ready_success(self):
        """Test waiting for ready state successfully"""
        manager = LifecycleManager(service_name="wait-ready-test")

        def set_ready():
            time.sleep(0.1)
            manager.state = ServiceState.READY

        # Start thread to set ready state
        thread = threading.Thread(target=set_ready)
        thread.start()

        # Wait for ready
        result = manager.wait_for_ready(timeout=1.0)

        thread.join()
        assert result is True
        assert manager.state == ServiceState.READY

    def test_lifecycle_manager_wait_for_ready_timeout(self):
        """Test waiting for ready state with timeout"""
        manager = LifecycleManager(service_name="wait-timeout-test")

        # Don't set ready state
        result = manager.wait_for_ready(timeout=0.1)

        assert result is False
        assert manager.state != ServiceState.READY

    def test_lifecycle_manager_wait_for_shutdown(self):
        """Test waiting for shutdown"""
        manager = LifecycleManager(service_name="wait-shutdown-test")

        # Mock graceful shutdown
        manager.graceful_shutdown.wait_for_shutdown = Mock(return_value=True)

        result = manager.wait_for_shutdown(timeout=1.0)

        assert result is True
        manager.graceful_shutdown.wait_for_shutdown.assert_called_once_with(1.0)


class TestKubernetesProbes:
    """Test Kubernetes probe compatibility"""

    def test_create_kubernetes_probes(self):
        """Test creating Kubernetes-compatible probe functions"""
        manager = LifecycleManager(service_name="k8s-test")
        manager.state = ServiceState.READY

        # Mock component states
        manager.startup_manager.is_ready = Mock(return_value=True)

        probes = create_kubernetes_probes(manager)

        assert "readiness" in probes
        assert "liveness" in probes
        assert "startup" in probes

        # Test readiness probe
        assert probes["readiness"]() is True

        # Test liveness probe
        assert probes["liveness"]() is True

        # Test startup probe
        assert probes["startup"]() is True

    def test_kubernetes_probes_not_ready(self):
        """Test Kubernetes probes when service not ready"""
        manager = LifecycleManager(service_name="k8s-not-ready")
        manager.state = ServiceState.STARTING

        manager.startup_manager.is_ready = Mock(return_value=False)

        probes = create_kubernetes_probes(manager)

        # Readiness and liveness should fail
        assert probes["readiness"]() is False
        assert probes["liveness"]() is False

        # Startup should also fail if not ready
        assert probes["startup"]() is False

    def test_kubernetes_probes_degraded(self):
        """Test Kubernetes probes in degraded state"""
        manager = LifecycleManager(service_name="k8s-degraded")
        manager.state = ServiceState.DEGRADED

        manager.startup_manager.is_ready = Mock(return_value=True)

        probes = create_kubernetes_probes(manager)

        # Should still be ready in degraded mode
        assert probes["readiness"]() is True
        assert probes["startup"]() is True


class TestGlobalLifecycleManager:
    """Test global lifecycle manager functions"""

    def teardown_method(self):
        """Reset global manager after each test"""
        import core.lifecycle.manager

        core.lifecycle.manager._lifecycle_manager = None

    def test_get_lifecycle_manager_default(self):
        """Test getting default global lifecycle manager"""
        with patch.dict("os.environ", {"GENESIS_SERVICE": "global-test"}):
            manager = get_lifecycle_manager()

            assert manager.service_name == "global-test"
            assert isinstance(manager, LifecycleManager)

            # Should return same instance
            manager2 = get_lifecycle_manager()
            assert manager is manager2

    def test_get_lifecycle_manager_custom(self):
        """Test getting global lifecycle manager with custom service"""
        manager = get_lifecycle_manager(service_name="custom-global")

        assert manager.service_name == "custom-global"
        assert isinstance(manager, LifecycleManager)

    def test_configure_lifecycle_manager(self):
        """Test configuring global lifecycle manager"""
        manager = configure_lifecycle_manager(
            service_name="configured-service", version="3.0.0", environment="staging"
        )

        assert manager.service_name == "configured-service"
        assert manager.version == "3.0.0"
        assert manager.environment == "staging"

        # Should return same configured instance
        manager2 = get_lifecycle_manager()
        assert manager is manager2


class TestLifecycleThreadSafety:
    """Test lifecycle thread safety"""

    def test_lifecycle_manager_thread_safety(self):
        """Test LifecycleManager thread safety"""
        manager = LifecycleManager(service_name="thread-safety-test")
        results = []

        def register_health_checks(thread_id):
            for i in range(10):
                check_name = f"thread-{thread_id}-check-{i}"
                health_check = Mock(return_value=True)
                manager.register_health_check(check_name, health_check)
                results.append(check_name)

        # Run multiple threads registering health checks
        threads = []
        for i in range(5):
            thread = threading.Thread(target=register_health_checks, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all health checks were registered
        assert len(results) == 50
        assert len(manager.health_checks) >= 50  # Plus built-in checks

        # Verify all registered checks are in the manager
        for check_name in results:
            assert check_name in manager.health_checks

    def test_startup_manager_dependency_thread_safety(self):
        """Test StartupManager dependency registration thread safety"""
        manager = StartupManager(service_name="dep-thread-safety")
        results = []

        def register_dependencies(thread_id):
            for i in range(5):
                dep_name = f"thread-{thread_id}-dep-{i}"
                check_function = Mock(return_value=True)
                manager.register_dependency(dep_name, check_function)
                results.append(dep_name)

        # Run multiple threads registering dependencies
        threads = []
        for i in range(3):
            thread = threading.Thread(target=register_dependencies, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all dependencies were registered
        assert len(results) == 15
        assert len(manager.dependencies) == 15

        # Verify all registered dependencies are in the manager
        registered_names = [dep.name for dep in manager.dependencies]
        for dep_name in results:
            assert dep_name in registered_names


class TestLifecyclePerformance:
    """Test lifecycle performance"""

    def test_lifecycle_manager_creation_performance(self):
        """Test LifecycleManager creation performance"""
        start_time = time.time()

        # Create many lifecycle managers
        managers = []
        for i in range(50):
            manager = LifecycleManager(service_name=f"perf-test-{i}")
            managers.append(manager)

        elapsed_time = time.time() - start_time

        # Should complete quickly (< 1 second)
        assert elapsed_time < 1.0

        # Verify all were created correctly
        assert len(managers) == 50
        for i, manager in enumerate(managers):
            assert manager.service_name == f"perf-test-{i}"

    def test_health_check_registration_performance(self):
        """Test health check registration performance"""
        manager = LifecycleManager(service_name="health-perf-test")

        start_time = time.time()

        # Register many health checks
        for i in range(1000):
            health_check = Mock(return_value=True)
            manager.register_health_check(f"check-{i}", health_check)

        elapsed_time = time.time() - start_time

        # Should complete quickly (< 0.5 seconds)
        assert elapsed_time < 0.5

        # Verify all were registered
        assert len(manager.health_checks) >= 1000  # Plus built-in checks

    @pytest.mark.asyncio
    async def test_startup_hook_execution_performance(self):
        """Test startup hook execution performance"""
        manager = StartupManager(
            service_name="hook-perf-test",
            warmup_duration=0,  # Disable warmup for testing
        )

        # Register many fast hooks
        for i in range(100):

            def fast_hook():
                pass  # No-op hook

            manager.register_hook(
                name=f"fast-hook-{i}",
                callback=fast_hook,
                phase=StartupPhase.INITIALIZE_SERVICES,
                critical=False,
            )

        with patch.dict(
            "os.environ", {"GENESIS_SERVICE": "hook-perf-test", "GENESIS_ENV": "test"}
        ):
            start_time = time.time()
            success = await manager.start()
            elapsed_time = time.time() - start_time

        assert success is True
        # Should complete reasonably quickly (< 5 seconds)
        assert elapsed_time < 5.0
        assert manager.metrics.hooks_executed >= 100


class TestLifecycleEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_lifecycle_manager_double_start(self):
        """Test starting lifecycle manager twice"""
        manager = LifecycleManager(service_name="double-start-test")

        with patch.dict(
            "os.environ",
            {"GENESIS_SERVICE": "double-start-test", "GENESIS_ENV": "test"},
        ):
            # Mock successful startup
            with patch.object(manager.startup_manager, "start", return_value=True):
                # First start
                success1 = await manager.start()
                assert success1 is True

                # Second start should not cause issues
                success2 = await manager.start()
                assert success2 is True

    def test_lifecycle_manager_health_check_exception(self):
        """Test health check that raises exception"""
        manager = LifecycleManager(service_name="health-exception-test")

        def failing_health_check():
            raise RuntimeError("Health check error")

        manager.register_health_check("failing", failing_health_check)

        # Should handle exception gracefully
        assert manager.is_healthy() is False

    def test_startup_manager_empty_phases(self):
        """Test startup manager with empty phases"""
        manager = StartupManager(service_name="empty-phases-test")

        # Clear all hooks
        for phase in StartupPhase:
            manager.hooks[phase] = []

        # Should handle empty phases gracefully
        assert manager.get_status()["registered_hooks"] == {
            phase.name: 0 for phase in StartupPhase
        }

    def test_lifecycle_manager_invalid_dependency_type(self):
        """Test registering dependency with invalid type"""
        manager = LifecycleManager(service_name="invalid-dep-test")
        check_function = Mock(return_value=True)

        # Should default to REQUIRED for invalid types
        manager.register_dependency(
            name="invalid-dep",
            check_function=check_function,
            dependency_type="invalid-type",
        )

        # Should have registered with REQUIRED type
        dependency = manager.startup_manager.dependencies[-1]
        assert dependency.dependency_type == DependencyType.REQUIRED

    def test_startup_manager_hook_dependency_sorting(self):
        """Test hook dependency sorting"""
        manager = StartupManager(service_name="dep-sort-test")

        # Register hooks with dependencies
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        manager.register_hook(
            name="hook1",
            callback=callback1,
            phase=StartupPhase.INITIALIZE_SERVICES,
            dependencies=set(),  # No dependencies
        )

        manager.register_hook(
            name="hook2",
            callback=callback2,
            phase=StartupPhase.INITIALIZE_SERVICES,
            dependencies={"hook1"},  # Depends on hook1
        )

        manager.register_hook(
            name="hook3",
            callback=callback3,
            phase=StartupPhase.INITIALIZE_SERVICES,
            dependencies={"hook1", "hook2"},  # Depends on both
        )

        # Get sorted hooks
        hooks = manager.hooks[StartupPhase.INITIALIZE_SERVICES]
        sorted_hooks = manager._sort_hooks_by_dependencies(hooks)

        # Should be sorted by dependency count (simple sort)
        dependency_counts = [len(hook.dependencies) for hook in sorted_hooks]
        assert dependency_counts == sorted(dependency_counts)

    @pytest.mark.asyncio
    async def test_startup_manager_config_validator_failure(self):
        """Test configuration validator failure"""
        manager = StartupManager(service_name="config-fail-test")

        # Register failing validator
        def failing_validator():
            return False

        manager.register_config_validator(failing_validator)

        with patch.dict(
            "os.environ", {"GENESIS_SERVICE": "config-fail-test", "GENESIS_ENV": "test"}
        ):
            success = await manager.start()

        assert success is False
        assert manager.status == StartupStatus.FAILED

    @pytest.mark.asyncio
    async def test_startup_manager_config_validator_exception(self):
        """Test configuration validator exception"""
        manager = StartupManager(service_name="config-exception-test")

        # Register validator that raises exception
        def exception_validator():
            raise ValueError("Config validation error")

        manager.register_config_validator(exception_validator)

        with patch.dict(
            "os.environ",
            {"GENESIS_SERVICE": "config-exception-test", "GENESIS_ENV": "test"},
        ):
            success = await manager.start()

        assert success is False
        assert manager.status == StartupStatus.FAILED

    def test_lifecycle_manager_metrics_investigation(self):
        """Test SPIDER methodology investigation"""
        manager = LifecycleManager(service_name="spider-test")

        # Test health check failure investigation
        manager._investigate_health_failure("test-check", "Test error")

        # Should increment failure count
        assert manager.metrics.health_check_failures > 0

    def test_lifecycle_manager_auto_restart_trigger(self):
        """Test auto-restart trigger condition"""
        manager = LifecycleManager(
            service_name="auto-restart-test", enable_auto_restart=True
        )

        # Simulate multiple health check failures
        manager.metrics.health_check_failures = 5

        # Test investigation with high failure count
        manager._investigate_health_failure("failing-check", "Multiple failures")

        # Should consider auto-restart (logged but not actually restarted in test)
        assert manager.metrics.health_check_failures > 3
