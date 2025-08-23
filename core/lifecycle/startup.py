"""
Genesis Startup Management System

Orchestrated startup sequence with:
- Dependency verification and validation
- Configuration validation
- Health check registration
- Warm-up period support
- Progressive readiness states
- Component initialization ordering

Follows SPIDER methodology for reliable service initialization.
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Set

from ..errors.handler import GenesisError, get_error_handler
from ..logging.logger import get_logger


class StartupPhase(IntEnum):
    """Startup phases in execution order"""

    VALIDATE_ENVIRONMENT = 100  # Validate environment and config
    INITIALIZE_LOGGING = 200  # Setup logging infrastructure
    VALIDATE_DEPENDENCIES = 300  # Check external dependencies
    INITIALIZE_STORAGE = 400  # Initialize databases and storage
    INITIALIZE_NETWORKING = 500  # Setup network components
    INITIALIZE_SERVICES = 600  # Initialize application services
    REGISTER_HEALTH_CHECKS = 700  # Register health check endpoints
    WARM_UP = 800  # Perform warm-up operations
    FINALIZE = 900  # Final initialization steps


class StartupStatus(Enum):
    """Current startup status"""

    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    STARTING_DEPENDENCIES = "starting_dependencies"
    STARTING_SERVICES = "starting_services"
    WARMING_UP = "warming_up"
    READY = "ready"
    FAILED = "failed"
    DEGRADED = "degraded"


class DependencyType(Enum):
    """Types of dependencies"""

    REQUIRED = "required"  # Must be available to start
    OPTIONAL = "optional"  # Service can start without it
    CRITICAL = "critical"  # Failure blocks all startup


@dataclass
class StartupHook:
    """Individual startup hook configuration"""

    name: str
    callback: Callable[[], Any]
    phase: StartupPhase
    timeout: int = 60
    is_async: bool = False
    description: str = ""
    dependencies: Set[str] = field(default_factory=set)
    critical: bool = True  # If False, failure won't stop startup
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DependencyCheck:
    """External dependency validation"""

    name: str
    check_function: Callable[[], bool]
    dependency_type: DependencyType = DependencyType.REQUIRED
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5
    description: str = ""


@dataclass
class StartupMetrics:
    """Metrics for startup process"""

    startup_started: Optional[datetime] = None
    startup_completed: Optional[datetime] = None
    hooks_executed: int = 0
    hooks_failed: int = 0
    dependencies_checked: int = 0
    dependencies_failed: int = 0
    total_duration_ms: float = 0.0
    readiness_achieved: bool = False
    degraded_mode: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "startup_started": (
                self.startup_started.isoformat() if self.startup_started else None
            ),
            "startup_completed": (
                self.startup_completed.isoformat() if self.startup_completed else None
            ),
            "hooks_executed": self.hooks_executed,
            "hooks_failed": self.hooks_failed,
            "dependencies_checked": self.dependencies_checked,
            "dependencies_failed": self.dependencies_failed,
            "total_duration_ms": self.total_duration_ms,
            "duration_seconds": (
                self.total_duration_ms / 1000.0 if self.total_duration_ms else 0.0
            ),
            "readiness_achieved": self.readiness_achieved,
            "degraded_mode": self.degraded_mode,
        }


class StartupManager:
    """
    Orchestrated startup sequence manager

    Features:
    - Phase-based initialization
    - Dependency validation
    - Configuration verification
    - Health check registration
    - Progressive readiness
    - Graceful degradation
    - Comprehensive logging and metrics
    """

    def __init__(
        self,
        service_name: str,
        enable_degraded_mode: bool = True,
        startup_timeout: int = 300,  # 5 minutes
        warmup_duration: int = 30,
        enable_health_checks: bool = True,
    ):
        self.service_name = service_name
        self.enable_degraded_mode = enable_degraded_mode
        self.startup_timeout = startup_timeout
        self.warmup_duration = warmup_duration
        self.enable_health_checks = enable_health_checks

        # State management
        self.status = StartupStatus.NOT_STARTED
        self.hooks: Dict[StartupPhase, List[StartupHook]] = {
            phase: [] for phase in StartupPhase
        }
        self.dependencies: List[DependencyCheck] = []
        self.config_validators: List[Callable[[], bool]] = []
        self.health_checks: Dict[str, Callable[[], bool]] = {}

        # Tracking
        self.completed_phases: Set[StartupPhase] = set()
        self.failed_hooks: List[str] = []
        self.failed_dependencies: List[str] = []

        # Metrics and logging
        self.metrics = StartupMetrics()
        self.logger = get_logger(f"{__name__}.{service_name}")
        self.error_handler = get_error_handler()

        # Built-in hooks
        self._register_builtin_hooks()

        self.logger.info(f"Startup manager initialized for service '{service_name}'")

    def _register_builtin_hooks(self) -> None:
        """Register built-in startup hooks"""

        # Environment validation
        self.register_hook(
            name="validate_environment",
            callback=self._validate_environment,
            phase=StartupPhase.VALIDATE_ENVIRONMENT,
            description="Validate environment variables and basic configuration",
        )

        # Configuration validation
        self.register_hook(
            name="validate_configuration",
            callback=self._validate_configuration,
            phase=StartupPhase.VALIDATE_ENVIRONMENT,
            description="Validate service configuration",
        )

        # Dependency checks
        self.register_hook(
            name="check_dependencies",
            callback=self._check_all_dependencies,
            phase=StartupPhase.VALIDATE_DEPENDENCIES,
            timeout=90,
            description="Validate external dependencies",
        )

        # Health check registration
        if self.enable_health_checks:
            self.register_hook(
                name="register_health_checks",
                callback=self._register_health_checks,
                phase=StartupPhase.REGISTER_HEALTH_CHECKS,
                description="Register health check endpoints",
            )

        # Warmup operations
        self.register_hook(
            name="warmup_service",
            callback=self._warmup_service,
            phase=StartupPhase.WARM_UP,
            timeout=self.warmup_duration + 30,
            description="Perform service warm-up operations",
        )

    def register_hook(
        self,
        name: str,
        callback: Callable[[], Any],
        phase: StartupPhase,
        timeout: Optional[int] = None,
        is_async: bool = False,
        description: str = "",
        dependencies: Optional[Set[str]] = None,
        critical: bool = True,
    ):
        """
        Register a startup hook

        Args:
            name: Unique hook name
            callback: Function to execute during startup
            phase: Startup phase for ordering
            timeout: Hook execution timeout
            is_async: Whether the callback is async
            description: Human-readable description
            dependencies: Set of hook names this depends on
            critical: Whether failure should stop startup
        """
        hook = StartupHook(
            name=name,
            callback=callback,
            phase=phase,
            timeout=timeout or 60,
            is_async=is_async,
            description=description,
            dependencies=dependencies or set(),
            critical=critical,
        )

        self.hooks[phase].append(hook)
        self.logger.debug(f"Registered startup hook '{name}' for phase {phase.name}")

    def register_dependency(
        self,
        name: str,
        check_function: Callable[[], bool],
        dependency_type: DependencyType = DependencyType.REQUIRED,
        timeout: int = 30,
        retry_attempts: int = 3,
        retry_delay: int = 5,
        description: str = "",
    ):
        """
        Register an external dependency check

        Args:
            name: Dependency name
            check_function: Function that returns True if dependency is available
            dependency_type: Type of dependency (required, optional, critical)
            timeout: Timeout for individual check
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries in seconds
            description: Human-readable description
        """
        dependency = DependencyCheck(
            name=name,
            check_function=check_function,
            dependency_type=dependency_type,
            timeout=timeout,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
            description=description,
        )

        self.dependencies.append(dependency)
        self.logger.debug(f"Registered dependency '{name}' ({dependency_type.value})")

    def register_config_validator(self, validator: Callable[[], bool]) -> None:
        """Register a configuration validator function"""
        self.config_validators.append(validator)
        self.logger.debug("Registered configuration validator")

    def register_health_check(
        self, name: str, check_function: Callable[[], bool]
    ) -> None:
        """Register a health check function"""
        self.health_checks[name] = check_function
        self.logger.debug(f"Registered health check '{name}'")

    async def start(self) -> bool:
        """
        Execute the complete startup sequence

        Returns:
            True if startup completed successfully, False otherwise
        """
        if self.status != StartupStatus.NOT_STARTED:
            self.logger.warning(
                f"Startup already in progress or completed (status: {self.status.value})"
            )
            return self.status == StartupStatus.READY

        start_time = time.time()
        self.metrics.startup_started = datetime.utcnow()

        try:
            self.status = StartupStatus.INITIALIZING
            self.logger.info("Starting service initialization sequence")

            # Execute startup phases
            for phase in StartupPhase:
                if not self.hooks[phase]:
                    continue

                self.logger.info(f"Executing startup phase: {phase.name}")

                # Update status for specific phases
                if phase == StartupPhase.VALIDATE_DEPENDENCIES:
                    self.status = StartupStatus.VALIDATING
                elif phase == StartupPhase.INITIALIZE_SERVICES:
                    self.status = StartupStatus.STARTING_SERVICES
                elif phase == StartupPhase.WARM_UP:
                    self.status = StartupStatus.WARMING_UP

                # Execute phase hooks
                success = await self._execute_phase_hooks(phase)

                if not success:
                    if self.enable_degraded_mode and self._can_run_degraded():
                        self.logger.warning(
                            f"Phase {phase.name} failed, continuing in degraded mode"
                        )
                        self.status = StartupStatus.DEGRADED
                        self.metrics.degraded_mode = True
                    else:
                        self.status = StartupStatus.FAILED
                        self.logger.error(
                            f"Critical phase {phase.name} failed, startup aborted"
                        )
                        return False

                self.completed_phases.add(phase)

            # Startup completed successfully
            self.status = StartupStatus.READY
            self.metrics.readiness_achieved = True
            self.logger.info("Service startup completed successfully")
            return True

        except Exception as e:
            self.status = StartupStatus.FAILED
            self.logger.error(f"Startup failed with exception: {e}")
            self.error_handler.handle(e)
            return False

        finally:
            # Record completion metrics
            self.metrics.startup_completed = datetime.utcnow()
            self.metrics.total_duration_ms = (time.time() - start_time) * 1000

    async def _execute_phase_hooks(self, phase: StartupPhase) -> bool:
        """Execute all hooks for a specific phase"""
        phase_hooks = self.hooks[phase]

        if not phase_hooks:
            return True

        self.logger.debug(f"Executing {len(phase_hooks)} hooks for phase {phase.name}")

        # Sort hooks by dependencies (simple topological sort)
        sorted_hooks = self._sort_hooks_by_dependencies(phase_hooks)

        all_success = True

        for hook in sorted_hooks:
            try:
                self.logger.debug(f"Executing hook: {hook.name}")

                if hook.is_async:
                    # Handle async hooks with timeout
                    await asyncio.wait_for(hook.callback(), timeout=hook.timeout)
                else:
                    # Handle sync hooks
                    await self._execute_sync_hook_with_timeout(hook)

                self.metrics.hooks_executed += 1
                self.logger.debug(f"Hook '{hook.name}' completed successfully")

            except asyncio.TimeoutError:
                self.metrics.hooks_failed += 1
                self.failed_hooks.append(hook.name)
                self.logger.error(f"Hook '{hook.name}' timed out after {hook.timeout}s")

                if hook.critical:
                    all_success = False

            except Exception as e:
                self.metrics.hooks_failed += 1
                self.failed_hooks.append(hook.name)
                self.logger.error(f"Hook '{hook.name}' failed: {e}")
                self.error_handler.handle(e)

                if hook.critical:
                    all_success = False

        return all_success

    def _sort_hooks_by_dependencies(
        self, hooks: List[StartupHook]
    ) -> List[StartupHook]:
        """Simple topological sort for hook dependencies"""
        # For now, just return hooks as-is. In a full implementation,
        # this would perform dependency resolution
        return sorted(hooks, key=lambda h: len(h.dependencies))

    async def _execute_sync_hook_with_timeout(self, hook: StartupHook) -> Any:
        """Execute a synchronous hook with timeout in event loop"""
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, hook.callback), timeout=hook.timeout
        )

    def _validate_environment(self) -> None:
        """Validate basic environment setup"""
        self.logger.debug("Validating environment variables")

        # Check for required environment variables
        required_vars = ["GENESIS_SERVICE", "GENESIS_ENV"]

        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)

        if missing_vars:
            raise GenesisError(
                f"Missing required environment variables: {', '.join(missing_vars)}",
                code="MISSING_ENV_VARS",
            )

        self.logger.debug("Environment validation completed")

    def _validate_configuration(self) -> None:
        """Run all registered configuration validators"""
        self.logger.debug("Validating service configuration")

        for i, validator in enumerate(self.config_validators):
            try:
                if not validator():
                    raise GenesisError(
                        f"Configuration validator {i + 1} failed",
                        code="CONFIG_VALIDATION_FAILED",
                    )
            except Exception as e:
                raise GenesisError(
                    f"Configuration validator {i + 1} error: {e}",
                    code="CONFIG_VALIDATION_ERROR",
                    cause=e,
                )

        self.logger.debug(
            f"Configuration validation completed ({len(self.config_validators)} validators)"
        )

    def _check_all_dependencies(self) -> None:
        """Check all registered dependencies"""
        self.logger.debug(f"Checking {len(self.dependencies)} dependencies")

        failed_critical = []
        failed_required = []

        for dependency in self.dependencies:
            self.metrics.dependencies_checked += 1

            success = self._check_single_dependency(dependency)

            if not success:
                self.metrics.dependencies_failed += 1
                self.failed_dependencies.append(dependency.name)

                if dependency.dependency_type == DependencyType.CRITICAL:
                    failed_critical.append(dependency.name)
                elif dependency.dependency_type == DependencyType.REQUIRED:
                    failed_required.append(dependency.name)
                # Optional dependencies don't cause failures

        # Handle failures
        if failed_critical:
            raise GenesisError(
                f"Critical dependencies failed: {', '.join(failed_critical)}",
                code="CRITICAL_DEPENDENCY_FAILED",
            )

        if failed_required and not self.enable_degraded_mode:
            raise GenesisError(
                f"Required dependencies failed: {', '.join(failed_required)}",
                code="REQUIRED_DEPENDENCY_FAILED",
            )

        self.logger.info(
            f"Dependency validation completed: {len(self.dependencies) - len(self.failed_dependencies)}/{len(self.dependencies)} successful"
        )

    def _check_single_dependency(self, dependency: DependencyCheck) -> bool:
        """Check a single dependency with retries"""
        self.logger.debug(f"Checking dependency: {dependency.name}")

        for attempt in range(dependency.retry_attempts):
            try:
                if dependency.check_function():
                    self.logger.debug(f"Dependency '{dependency.name}' check passed")
                    return True

            except Exception as e:
                self.logger.warning(f"Dependency '{dependency.name}' check error: {e}")

            if attempt < dependency.retry_attempts - 1:
                self.logger.debug(
                    f"Retrying dependency '{dependency.name}' in {dependency.retry_delay}s"
                )
                time.sleep(dependency.retry_delay)

        self.logger.error(
            f"Dependency '{dependency.name}' failed after {dependency.retry_attempts} attempts"
        )
        return False

    def _register_health_checks(self) -> None:
        """Register all health check endpoints"""
        self.logger.debug(f"Registering {len(self.health_checks)} health checks")

        # In a real implementation, this would register endpoints with a web framework
        # For now, just log the registration
        for name, check_function in self.health_checks.items():
            self.logger.debug(f"Registered health check endpoint: {name}")

        self.logger.info("Health check endpoints registered")

    def _warmup_service(self) -> None:
        """Perform service warm-up operations"""
        self.logger.info(f"Starting {self.warmup_duration}s warm-up period")

        # Simulate warm-up operations
        # In real implementation, this might:
        # - Prime caches
        # - Establish connection pools
        # - Load configuration
        # - Perform initial data loads

        time.sleep(self.warmup_duration)
        self.logger.info("Service warm-up completed")

    def _can_run_degraded(self) -> bool:
        """Check if service can run in degraded mode"""
        # Only run degraded if no critical dependencies failed
        critical_failures = [
            dep
            for dep in self.failed_dependencies
            if any(
                d.dependency_type == DependencyType.CRITICAL
                for d in self.dependencies
                if d.name == dep
            )
        ]

        return len(critical_failures) == 0

    def is_ready(self) -> bool:
        """Check if service is ready to accept requests"""
        return self.status in [StartupStatus.READY, StartupStatus.DEGRADED]

    def is_healthy(self) -> bool:
        """Check if service is healthy (runs all health checks)"""
        if not self.is_ready():
            return False

        try:
            for name, check_function in self.health_checks.items():
                if not check_function():
                    self.logger.warning(f"Health check '{name}' failed")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get current startup status and metrics"""
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "is_ready": self.is_ready(),
            "is_healthy": self.is_healthy(),
            "completed_phases": [phase.name for phase in self.completed_phases],
            "failed_hooks": self.failed_hooks,
            "failed_dependencies": self.failed_dependencies,
            "registered_hooks": {
                phase.name: len(hooks) for phase, hooks in self.hooks.items()
            },
            "dependencies_count": len(self.dependencies),
            "health_checks_count": len(self.health_checks),
            "metrics": self.metrics.to_dict(),
        }
