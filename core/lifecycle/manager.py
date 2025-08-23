"""
Genesis Lifecycle Manager

Central coordinator for service lifecycle management using SPIDER methodology:
- S: Symptom identification through comprehensive monitoring
- P: Problem isolation via component-level tracking
- I: Investigation through detailed logging and metrics
- D: Diagnosis with structured error handling and analysis
- E: Execution of coordinated startup/shutdown sequences
- R: Review and continuous improvement of lifecycle processes

Coordinates:
- Startup orchestration with dependency validation
- Graceful shutdown with resource cleanup
- Health check integration and monitoring
- Hook-based event system
- Cloud-native compatibility (Kubernetes, containers)
- Comprehensive metrics and observability
"""

import asyncio
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from ..errors.handler import get_error_handler
from ..logging.logger import get_logger
from .hooks import HookEvent, get_hook_manager, lifecycle_hook
from .shutdown import get_shutdown_manager
from .startup import StartupManager


class ServiceState(Enum):
    """Overall service state"""

    INITIALIZING = "initializing"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class LifecycleMetrics:
    """Comprehensive lifecycle metrics"""

    service_name: str
    state: ServiceState
    startup_duration_ms: float = 0.0
    shutdown_duration_ms: float = 0.0
    uptime_seconds: float = 0.0
    restart_count: int = 0
    health_check_failures: int = 0
    last_health_check: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "startup_duration_ms": self.startup_duration_ms,
            "shutdown_duration_ms": self.shutdown_duration_ms,
            "uptime_seconds": self.uptime_seconds,
            "restart_count": self.restart_count,
            "health_check_failures": self.health_check_failures,
            "last_health_check": (
                self.last_health_check.isoformat() if self.last_health_check else None
            ),
            "created_at": self.created_at.isoformat(),
        }


class LifecycleManager:
    """
    Central lifecycle manager for Genesis services

    Coordinates startup, shutdown, health checks, and operational state
    management with comprehensive monitoring and error handling.

    Features:
    - Coordinated startup and shutdown sequences
    - Health check integration and monitoring
    - Hook-based event system for extensibility
    - Cloud-native compatibility (Kubernetes readiness/liveness)
    - Comprehensive metrics and observability
    - Graceful degradation and recovery
    - SPIDER methodology implementation
    """

    def __init__(
        self,
        service_name: str,
        version: str = "1.0.0",
        environment: str = "development",
        enable_health_checks: bool = True,
        enable_metrics: bool = True,
        startup_timeout: int = 300,
        shutdown_timeout: int = 120,
        health_check_interval: int = 30,
        enable_auto_restart: bool = False,
    ):
        self.service_name = service_name
        self.version = version
        self.environment = environment
        self.enable_health_checks = enable_health_checks
        self.enable_metrics = enable_metrics
        self.startup_timeout = startup_timeout
        self.shutdown_timeout = shutdown_timeout
        self.health_check_interval = health_check_interval
        self.enable_auto_restart = enable_auto_restart

        # State management
        self.state = ServiceState.INITIALIZING
        self.startup_time: Optional[datetime] = None
        self.ready_time: Optional[datetime] = None
        self.shutdown_time: Optional[datetime] = None

        # Component managers
        self.startup_manager = StartupManager(
            service_name=service_name,
            startup_timeout=startup_timeout,
            enable_health_checks=enable_health_checks,
        )

        self.shutdown_manager = get_shutdown_manager()
        self.graceful_shutdown = self.shutdown_manager.register_service(
            service_name=service_name, max_shutdown_time=shutdown_timeout
        )

        self.hook_manager = get_hook_manager(service_name)

        # Health check management
        self.health_checks: Dict[str, Callable[[], bool]] = {}
        self.health_check_results: Dict[str, bool] = {}
        self.health_check_task: Optional[asyncio.Task] = None

        # Metrics and monitoring
        self.metrics = LifecycleMetrics(service_name=service_name, state=self.state)
        self.logger = get_logger(f"{__name__}.{service_name}")
        self.error_handler = get_error_handler()

        # Thread safety
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()

        # Register built-in hooks
        self._register_builtin_hooks()

        # Register health checks
        if enable_health_checks:
            self._register_builtin_health_checks()

        self.logger.info(
            f"Lifecycle manager initialized for '{service_name}' v{version} in {environment}"
        )

    def _register_builtin_hooks(self) -> None:
        """Register built-in lifecycle hooks"""

        @lifecycle_hook(HookEvent.PRE_STARTUP, manager=self.hook_manager)
        def pre_startup_hook(context: Dict[str, Any]) -> None:
            self.logger.info("Pre-startup hook: Preparing service initialization")
            self.state = ServiceState.STARTING
            self.startup_time = datetime.utcnow()

        @lifecycle_hook(HookEvent.POST_STARTUP, manager=self.hook_manager)
        def post_startup_hook(context: Dict[str, Any]) -> None:
            self.logger.info("Post-startup hook: Service initialization completed")
            self.state = ServiceState.READY
            self.ready_time = datetime.utcnow()

            # Calculate startup duration
            if self.startup_time:
                duration = (self.ready_time - self.startup_time).total_seconds() * 1000
                self.metrics.startup_duration_ms = duration

        @lifecycle_hook(HookEvent.STARTUP_FAILED, manager=self.hook_manager)
        def startup_failed_hook(context: Dict[str, Any]) -> None:
            self.logger.error("Startup failed hook: Service initialization failed")
            self.state = ServiceState.FAILED

        @lifecycle_hook(HookEvent.PRE_SHUTDOWN, manager=self.hook_manager)
        def pre_shutdown_hook(context: Dict[str, Any]) -> None:
            self.logger.info("Pre-shutdown hook: Initiating graceful shutdown")
            self.state = ServiceState.SHUTTING_DOWN
            self.shutdown_time = datetime.utcnow()

        @lifecycle_hook(HookEvent.POST_SHUTDOWN, manager=self.hook_manager)
        def post_shutdown_hook(context: Dict[str, Any]) -> None:
            self.logger.info("Post-shutdown hook: Service shutdown completed")
            self.state = ServiceState.STOPPED

            # Calculate shutdown duration
            if self.shutdown_time:
                shutdown_end = datetime.utcnow()
                duration = (shutdown_end - self.shutdown_time).total_seconds() * 1000
                self.metrics.shutdown_duration_ms = duration

        @lifecycle_hook(HookEvent.HEALTH_CHECK_FAILED, manager=self.hook_manager)
        def health_check_failed_hook(context: Dict[str, Any]) -> None:
            self.metrics.health_check_failures += 1
            self.logger.warning("Health check failed - investigating service health")

            # Implement SPIDER methodology for health check failures
            self._investigate_health_failure(
                context.get("check_name"), context.get("error")
            )

        @lifecycle_hook(HookEvent.SERVICE_DEGRADED, manager=self.hook_manager)
        def service_degraded_hook(context: Dict[str, Any]) -> None:
            self.logger.warning(
                "Service degraded - operating with limited functionality"
            )
            self.state = ServiceState.DEGRADED

        @lifecycle_hook(HookEvent.SERVICE_RECOVERING, manager=self.hook_manager)
        def service_recovering_hook(context: Dict[str, Any]) -> None:
            self.logger.info("Service recovering - restoring full functionality")
            self.state = ServiceState.READY

    def _register_builtin_health_checks(self) -> None:
        """Register built-in health checks"""

        def basic_health_check() -> bool:
            """Basic service health check"""
            return self.state in [ServiceState.READY, ServiceState.DEGRADED]

        def startup_health_check() -> bool:
            """Check if startup completed successfully"""
            return self.startup_manager.is_ready()

        def components_health_check() -> bool:
            """Check health of all registered components"""
            try:
                # Check hook manager health
                if not self.hook_manager.health_check():
                    return False

                # Check if shutdown is requested
                if self.graceful_shutdown.is_shutdown_requested():
                    return False

                return True
            except Exception:
                return False

        # Register health checks
        self.register_health_check("basic", basic_health_check)
        self.register_health_check("startup", startup_health_check)
        self.register_health_check("components", components_health_check)

    async def start(self) -> bool:
        """
        Start the service with full lifecycle management

        Returns:
            True if startup completed successfully
        """
        try:
            # Trigger pre-startup hooks
            await self.hook_manager.trigger_event(HookEvent.PRE_STARTUP)

            # Execute startup sequence
            self.logger.info("Starting service lifecycle")
            startup_success = await self.startup_manager.start()

            if startup_success:
                # Start health check monitoring
                if self.enable_health_checks:
                    self._start_health_check_monitoring()

                # Trigger post-startup hooks
                await self.hook_manager.trigger_event(HookEvent.POST_STARTUP)

                self.logger.info(f"Service '{self.service_name}' started successfully")
                return True
            else:
                # Trigger startup failed hooks
                await self.hook_manager.trigger_event(HookEvent.STARTUP_FAILED)
                self.logger.error(f"Service '{self.service_name}' startup failed")
                return False

        except Exception as e:
            self.state = ServiceState.FAILED
            self.error_handler.handle(e)
            await self.hook_manager.trigger_event(
                HookEvent.STARTUP_FAILED, {"error": str(e)}
            )
            return False

    def stop(self) -> None:
        """
        Stop the service with graceful shutdown
        """
        try:
            self.logger.info("Stopping service lifecycle")
            self._shutdown_event.set()

            # Stop health check monitoring
            if self.health_check_task:
                self.health_check_task.cancel()

            # Trigger graceful shutdown
            self.graceful_shutdown._initiate_shutdown()

        except Exception as e:
            self.logger.error(f"Error during service stop: {e}")
            self.error_handler.handle(e)

    def register_startup_hook(
        self,
        name: str,
        callback: Callable[[], None],
        phase: int,
        timeout: int = 60,
        critical: bool = True,
        description: str = "",
    ) -> None:
        """Register a startup hook"""
        self.startup_manager.register_hook(
            name=name,
            callback=callback,
            phase=phase,
            timeout=timeout,
            critical=critical,
            description=description,
        )

    def register_shutdown_hook(
        self,
        name: str,
        callback: Callable[[], None],
        phase: int,
        timeout: int = 30,
        description: str = "",
    ) -> None:
        """Register a shutdown hook"""
        self.graceful_shutdown.register_hook(
            name=name,
            callback=callback,
            phase=phase,
            timeout=timeout,
            description=description,
        )

    def register_health_check(
        self, name: str, check_function: Callable[[], bool]
    ) -> None:
        """Register a health check function"""
        with self._lock:
            self.health_checks[name] = check_function
            self.health_check_results[name] = True  # Assume healthy initially

        self.logger.debug(f"Registered health check: {name}")

    def register_dependency(
        self,
        name: str,
        check_function: Callable[[], bool],
        dependency_type: str = "required",
        timeout: int = 30,
        retry_attempts: int = 3,
        retry_delay: int = 1,
        description: str = "",
    ) -> None:
        """Register an external dependency"""
        from .startup import DependencyType

        dep_type = DependencyType.REQUIRED
        if dependency_type.lower() == "optional":
            dep_type = DependencyType.OPTIONAL
        elif dependency_type.lower() == "critical":
            dep_type = DependencyType.CRITICAL

        self.startup_manager.register_dependency(
            name=name,
            check_function=check_function,
            dependency_type=dep_type,
            timeout=timeout,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
            description=description,
        )

    def _start_health_check_monitoring(self) -> None:
        """Start health check monitoring task"""
        if self.health_check_task is None or self.health_check_task.done():
            self.health_check_task = asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self) -> None:
        """Main health check monitoring loop"""
        self.logger.debug("Started health check monitoring")

        while not self._shutdown_event.is_set():
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.health_check_interval)

        self.logger.debug("Health check monitoring stopped")

    async def _perform_health_checks(self) -> None:
        """Perform all registered health checks"""
        self.metrics.last_health_check = datetime.utcnow()

        overall_healthy = True
        failed_checks = []

        for name, check_function in self.health_checks.items():
            try:
                # Execute health check with timeout
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, check_function),
                    timeout=10,  # 10 second timeout for health checks
                )

                self.health_check_results[name] = result

                if not result:
                    overall_healthy = False
                    failed_checks.append(name)

            except asyncio.TimeoutError:
                self.health_check_results[name] = False
                overall_healthy = False
                failed_checks.append(name)
                self.logger.warning(f"Health check '{name}' timed out")

            except Exception as e:
                self.health_check_results[name] = False
                overall_healthy = False
                failed_checks.append(name)
                self.logger.error(f"Health check '{name}' failed: {e}")

        # Handle health check failures
        if not overall_healthy:
            await self.hook_manager.trigger_event(
                HookEvent.HEALTH_CHECK_FAILED, {"failed_checks": failed_checks}
            )

            # Consider service degraded if multiple checks fail
            if len(failed_checks) > 1 and self.state == ServiceState.READY:
                await self.hook_manager.trigger_event(HookEvent.SERVICE_DEGRADED)

        elif self.state == ServiceState.DEGRADED:
            # Service recovered
            await self.hook_manager.trigger_event(HookEvent.SERVICE_RECOVERING)

    def _investigate_health_failure(
        self, check_name: Optional[str], error: Optional[str]
    ) -> None:
        """
        SPIDER methodology implementation for health check failures

        S - Symptom identification: Health check failed
        P - Problem isolation: Identify which component failed
        I - Investigation: Gather diagnostic information
        D - Diagnosis: Determine root cause
        E - Execution: Apply appropriate response
        R - Review: Log for post-incident analysis
        """
        investigation_data = {
            "symptom": f"Health check '{check_name}' failed",
            "timestamp": datetime.utcnow().isoformat(),
            "service_state": self.state.value,
            "error": error,
            "recent_metrics": self.get_metrics(),
        }

        # Log investigation for later analysis
        self.logger.warning("SPIDER Investigation", **investigation_data)

        # Determine if auto-restart is needed
        if self.enable_auto_restart and self.metrics.health_check_failures > 3:
            self.logger.warning(
                "Multiple health check failures detected, considering auto-restart"
            )
            # In a real implementation, this could trigger automatic service restart

    def is_ready(self) -> bool:
        """Check if service is ready to accept requests"""
        return self.state in [ServiceState.READY, ServiceState.DEGRADED]

    def is_healthy(self) -> bool:
        """Check if service is healthy"""
        if not self.is_ready():
            return False

        # Check if majority of health checks are passing
        if not self.health_check_results:
            return True  # No health checks registered

        passing_checks = sum(
            1 for result in self.health_check_results.values() if result
        )
        total_checks = len(self.health_check_results)

        return passing_checks >= (total_checks / 2)

    def get_uptime(self) -> float:
        """Get service uptime in seconds"""
        if self.ready_time:
            return (datetime.utcnow() - self.ready_time).total_seconds()
        return 0.0

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics"""
        # Update uptime
        self.metrics.uptime_seconds = self.get_uptime()

        base_metrics = self.metrics.to_dict()

        # Add component metrics
        startup_metrics = self.startup_manager.get_status()
        shutdown_metrics = self.graceful_shutdown.get_status()
        hook_metrics = self.hook_manager.get_statistics()

        return {
            **base_metrics,
            "startup": startup_metrics,
            "shutdown": shutdown_metrics,
            "hooks": hook_metrics,
            "health_checks": {
                "registered": len(self.health_checks),
                "results": self.health_check_results,
                "overall_healthy": self.is_healthy(),
            },
        }

    def get_status(self) -> Dict[str, Any]:
        """Get complete service status"""
        return {
            "service_name": self.service_name,
            "version": self.version,
            "environment": self.environment,
            "state": self.state.value,
            "is_ready": self.is_ready(),
            "is_healthy": self.is_healthy(),
            "uptime_seconds": self.get_uptime(),
            "startup_completed": self.startup_manager.is_ready(),
            "shutdown_requested": self.graceful_shutdown.is_shutdown_requested(),
            "health_check_count": len(self.health_checks),
            "metrics": self.get_metrics(),
        }

    def wait_for_ready(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for service to become ready

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if service became ready within timeout
        """
        start_time = time.time()

        while not self.is_ready():
            if timeout and (time.time() - start_time) > timeout:
                return False
            time.sleep(0.1)

        return True

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for service shutdown

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if service shut down within timeout
        """
        return self.graceful_shutdown.wait_for_shutdown(timeout)


# Kubernetes/Container compatibility helpers
def create_kubernetes_probes(
    lifecycle_manager: LifecycleManager,
) -> Dict[str, Callable[[], bool]]:
    """
    Create Kubernetes-compatible probe functions

    Args:
        lifecycle_manager: LifecycleManager instance

    Returns:
        Dictionary with readiness and liveness probe functions
    """

    def readiness_probe() -> bool:
        """Kubernetes readiness probe - is service ready to accept traffic?"""
        return lifecycle_manager.is_ready()

    def liveness_probe() -> bool:
        """Kubernetes liveness probe - is service alive and healthy?"""
        return lifecycle_manager.is_healthy()

    def startup_probe() -> bool:
        """Kubernetes startup probe - has service completed startup?"""
        return lifecycle_manager.startup_manager.is_ready()

    return {
        "readiness": readiness_probe,
        "liveness": liveness_probe,
        "startup": startup_probe,
    }


# Global lifecycle manager instance
_lifecycle_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager(
    service_name: Optional[str] = None, **kwargs: Any
) -> LifecycleManager:
    """
    Get the global lifecycle manager instance

    Args:
        service_name: Service name for new manager
        **kwargs: Additional LifecycleManager parameters

    Returns:
        LifecycleManager instance
    """
    global _lifecycle_manager

    if _lifecycle_manager is None:
        default_service = service_name or os.environ.get("GENESIS_SERVICE", "genesis")
        _lifecycle_manager = LifecycleManager(default_service, **kwargs)

    return _lifecycle_manager


def configure_lifecycle_manager(service_name: str, **kwargs: Any) -> LifecycleManager:
    """
    Configure the global lifecycle manager

    Args:
        service_name: Service name
        **kwargs: Additional LifecycleManager parameters

    Returns:
        Configured LifecycleManager instance
    """
    global _lifecycle_manager
    _lifecycle_manager = LifecycleManager(service_name, **kwargs)
    return _lifecycle_manager
