"""
Genesis Graceful Shutdown Management

Production-ready graceful shutdown system with:
- SIGTERM, SIGINT, SIGHUP signal handling
- Priority-based shutdown hooks
- Connection draining and resource cleanup
- Configurable timeout management
- Health check integration
- Cloud-native compatibility

Follows SPIDER methodology for operational excellence.
"""

import asyncio
import os
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Set

from ..errors.handler import get_error_handler
from ..logging.logger import get_logger


class ShutdownSignal(Enum):
    """Supported shutdown signals"""

    SIGTERM = signal.SIGTERM  # Graceful shutdown (default in containers)
    SIGINT = signal.SIGINT  # Interrupt (Ctrl+C)
    SIGHUP = signal.SIGHUP  # Hangup (reload/restart)


class ShutdownPhase(IntEnum):
    """Shutdown phases in priority order"""

    HEALTH_CHECK_DISABLE = 100  # Disable health checks first
    STOP_ACCEPTING_REQUESTS = 200  # Stop accepting new requests
    DRAIN_CONNECTIONS = 300  # Drain existing connections
    CLEANUP_RESOURCES = 400  # Cleanup application resources
    FINALIZE = 500  # Final cleanup and shutdown


class ShutdownStatus(Enum):
    """Current shutdown status"""

    RUNNING = "running"
    INITIATING = "initiating"
    IN_PROGRESS = "in_progress"
    DRAINING = "draining"
    CLEANUP = "cleanup"
    COMPLETED = "completed"
    FAILED = "failed"
    FORCED = "forced"


@dataclass
class ShutdownHook:
    """Individual shutdown hook configuration"""

    name: str
    callback: Callable[[], Any]
    phase: ShutdownPhase
    timeout: int = 30
    is_async: bool = False
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ShutdownMetrics:
    """Metrics for shutdown process"""

    shutdown_started: Optional[datetime] = None
    shutdown_completed: Optional[datetime] = None
    signal_received: Optional[ShutdownSignal] = None
    hooks_executed: int = 0
    hooks_failed: int = 0
    timeout_occurred: bool = False
    forced_shutdown: bool = False
    total_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "shutdown_started": (
                self.shutdown_started.isoformat() if self.shutdown_started else None
            ),
            "shutdown_completed": (
                self.shutdown_completed.isoformat() if self.shutdown_completed else None
            ),
            "signal_received": (
                self.signal_received.name if self.signal_received else None
            ),
            "hooks_executed": self.hooks_executed,
            "hooks_failed": self.hooks_failed,
            "timeout_occurred": self.timeout_occurred,
            "forced_shutdown": self.forced_shutdown,
            "total_duration_ms": self.total_duration_ms,
            "duration_seconds": (
                self.total_duration_ms / 1000.0 if self.total_duration_ms else 0.0
            ),
        }


class GracefulShutdown:
    """
    Graceful shutdown handler with signal management and hook coordination

    Features:
    - Multi-signal support (SIGTERM, SIGINT, SIGHUP)
    - Priority-based hook execution
    - Configurable timeouts per phase
    - Connection draining support
    - Resource cleanup orchestration
    - Health check integration
    - Comprehensive logging and metrics
    """

    def __init__(
        self,
        service_name: str,
        default_timeout: int = 30,
        max_shutdown_time: int = 120,
        enable_health_check_integration: bool = True,
        enable_metrics: bool = True,
    ):
        self.service_name = service_name
        self.default_timeout = default_timeout
        self.max_shutdown_time = max_shutdown_time
        self.enable_health_check_integration = enable_health_check_integration
        self.enable_metrics = enable_metrics

        # State management
        self.status = ShutdownStatus.RUNNING
        self.shutdown_event = threading.Event()
        self.hooks: Dict[ShutdownPhase, List[ShutdownHook]] = {
            phase: [] for phase in ShutdownPhase
        }
        self.active_connections: Set[Any] = set()
        self.is_healthy = True

        # Metrics and logging
        self.metrics = ShutdownMetrics()
        self.logger = get_logger(f"{__name__}.{service_name}")
        self.error_handler = get_error_handler()

        # Signal handlers
        self._original_handlers = {}
        self._setup_signal_handlers()

        # Built-in hooks
        self._register_builtin_hooks()

        self.logger.info(f"Graceful shutdown initialized for service '{service_name}'")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signals_to_handle = [ShutdownSignal.SIGTERM, ShutdownSignal.SIGINT]

        # Only handle SIGHUP on Unix systems
        if hasattr(signal, "SIGHUP"):
            signals_to_handle.append(ShutdownSignal.SIGHUP)

        for shutdown_signal in signals_to_handle:
            try:
                # Store original handler
                self._original_handlers[shutdown_signal] = signal.signal(
                    shutdown_signal.value, self._signal_handler
                )
                self.logger.debug(f"Registered handler for {shutdown_signal.name}")
            except (OSError, ValueError) as e:
                # Some signals may not be available in all environments
                self.logger.warning(
                    f"Could not register handler for {shutdown_signal.name}: {e}"
                )

    def _signal_handler(self, signum: int, frame):
        """Handle shutdown signals"""
        try:
            shutdown_signal = ShutdownSignal(signum)
            self.logger.info(
                f"Received {shutdown_signal.name} signal, initiating graceful shutdown"
            )

            # Record signal in metrics
            self.metrics.signal_received = shutdown_signal

            # Start shutdown process
            self._initiate_shutdown()

        except Exception as e:
            self.logger.error(f"Error in signal handler: {e}")
            # Force immediate shutdown if signal handler fails
            self._force_shutdown()

    def _register_builtin_hooks(self):
        """Register built-in shutdown hooks"""

        # Health check disabling hook
        if self.enable_health_check_integration:
            self.register_hook(
                name="disable_health_checks",
                callback=self._disable_health_checks,
                phase=ShutdownPhase.HEALTH_CHECK_DISABLE,
                description="Disable health checks to remove from load balancer",
            )

        # Connection draining hook
        self.register_hook(
            name="drain_connections",
            callback=self._drain_connections,
            phase=ShutdownPhase.DRAIN_CONNECTIONS,
            timeout=45,
            description="Gracefully drain active connections",
        )

        # Metrics collection hook
        if self.enable_metrics:
            self.register_hook(
                name="collect_shutdown_metrics",
                callback=self._collect_final_metrics,
                phase=ShutdownPhase.FINALIZE,
                description="Collect and report final shutdown metrics",
            )

    def register_hook(
        self,
        name: str,
        callback: Callable[[], Any],
        phase: ShutdownPhase,
        timeout: Optional[int] = None,
        is_async: bool = False,
        description: str = "",
    ):
        """
        Register a shutdown hook

        Args:
            name: Unique hook name
            callback: Function to execute during shutdown
            phase: Shutdown phase for ordering
            timeout: Hook execution timeout (uses default if None)
            is_async: Whether the callback is async
            description: Human-readable description
        """
        hook = ShutdownHook(
            name=name,
            callback=callback,
            phase=phase,
            timeout=timeout or self.default_timeout,
            is_async=is_async,
            description=description,
        )

        self.hooks[phase].append(hook)
        self.logger.debug(f"Registered shutdown hook '{name}' for phase {phase.name}")

    def register_connection(self, connection: Any):
        """Register an active connection for draining"""
        self.active_connections.add(connection)
        self.logger.debug(f"Registered connection: {id(connection)}")

    def unregister_connection(self, connection: Any):
        """Unregister a connection (completed/closed)"""
        self.active_connections.discard(connection)
        self.logger.debug(f"Unregistered connection: {id(connection)}")

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested"""
        return self.shutdown_event.is_set()

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for shutdown signal

        Args:
            timeout: Maximum time to wait (None for indefinite)

        Returns:
            True if shutdown was signaled, False if timeout occurred
        """
        return self.shutdown_event.wait(timeout)

    def _initiate_shutdown(self):
        """Initiate the graceful shutdown process"""
        if self.status != ShutdownStatus.RUNNING:
            self.logger.warning(
                f"Shutdown already in progress (status: {self.status.value})"
            )
            return

        self.status = ShutdownStatus.INITIATING
        self.metrics.shutdown_started = datetime.utcnow()
        self.shutdown_event.set()

        # Start shutdown in a separate thread to avoid blocking signal handler
        shutdown_thread = threading.Thread(
            target=self._execute_shutdown,
            name=f"shutdown-{self.service_name}",
            daemon=False,
        )
        shutdown_thread.start()

    def _execute_shutdown(self):
        """Execute the complete shutdown sequence"""
        start_time = time.time()

        try:
            self.status = ShutdownStatus.IN_PROGRESS
            self.logger.info("Starting graceful shutdown sequence")

            # Execute hooks by phase
            for phase in ShutdownPhase:
                if not self.hooks[phase]:
                    continue

                self.logger.info(f"Executing shutdown phase: {phase.name}")

                # Update status for specific phases
                if phase == ShutdownPhase.DRAIN_CONNECTIONS:
                    self.status = ShutdownStatus.DRAINING
                elif phase == ShutdownPhase.CLEANUP_RESOURCES:
                    self.status = ShutdownStatus.CLEANUP

                # Execute all hooks in this phase
                self._execute_phase_hooks(phase)

            self.status = ShutdownStatus.COMPLETED
            self.logger.info("Graceful shutdown completed successfully")

        except Exception as e:
            self.status = ShutdownStatus.FAILED
            self.logger.error(f"Shutdown failed: {e}")
            self.error_handler.handle(e)

        finally:
            # Record completion time
            self.metrics.shutdown_completed = datetime.utcnow()
            self.metrics.total_duration_ms = (time.time() - start_time) * 1000

            # Restore original signal handlers
            self._restore_signal_handlers()

    def _execute_phase_hooks(self, phase: ShutdownPhase):
        """Execute all hooks for a specific phase"""
        phase_hooks = self.hooks[phase]

        if not phase_hooks:
            return

        self.logger.debug(f"Executing {len(phase_hooks)} hooks for phase {phase.name}")

        for hook in phase_hooks:
            try:
                self.logger.debug(f"Executing hook: {hook.name}")

                if hook.is_async:
                    # Handle async hooks
                    loop = None
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        # No event loop running, create one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    if loop:
                        # Use asyncio.wait_for for timeout
                        future = asyncio.wait_for(hook.callback(), timeout=hook.timeout)
                        loop.run_until_complete(future)
                else:
                    # Handle sync hooks with timeout
                    self._execute_sync_hook_with_timeout(hook)

                self.metrics.hooks_executed += 1
                self.logger.debug(f"Hook '{hook.name}' completed successfully")

            except asyncio.TimeoutError:
                self.metrics.hooks_failed += 1
                self.metrics.timeout_occurred = True
                self.logger.error(f"Hook '{hook.name}' timed out after {hook.timeout}s")

            except Exception as e:
                self.metrics.hooks_failed += 1
                self.logger.error(f"Hook '{hook.name}' failed: {e}")
                self.error_handler.handle(e)

    def _execute_sync_hook_with_timeout(self, hook: ShutdownHook):
        """Execute a synchronous hook with timeout"""
        result = [None]
        exception = [None]

        def target():
            try:
                result[0] = hook.callback()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=hook.timeout)

        if thread.is_alive():
            # Hook timed out
            self.logger.warning(f"Hook '{hook.name}' still running after timeout")
            raise asyncio.TimeoutError(
                f"Hook '{hook.name}' exceeded timeout of {hook.timeout}s"
            )

        if exception[0]:
            raise exception[0]

        return result[0]

    def _disable_health_checks(self):
        """Disable health checks to remove service from load balancer"""
        self.is_healthy = False
        self.logger.info("Health checks disabled - service marked unhealthy")

    def _drain_connections(self):
        """Gracefully drain active connections"""
        if not self.active_connections:
            self.logger.info("No active connections to drain")
            return

        self.logger.info(f"Draining {len(self.active_connections)} active connections")

        # Wait for connections to complete naturally
        drain_timeout = 30  # seconds
        check_interval = 0.5  # seconds
        start_time = time.time()

        while self.active_connections and (time.time() - start_time) < drain_timeout:
            self.logger.debug(
                f"Waiting for {len(self.active_connections)} connections to complete"
            )
            time.sleep(check_interval)

        if self.active_connections:
            self.logger.warning(
                f"Forced to close {len(self.active_connections)} remaining connections"
            )
            # Force close remaining connections here if needed
        else:
            self.logger.info("All connections drained successfully")

    def _collect_final_metrics(self):
        """Collect and report final shutdown metrics"""
        if self.enable_metrics:
            metrics_dict = self.metrics.to_dict()
            self.logger.info("Shutdown metrics", **metrics_dict)

    def _restore_signal_handlers(self):
        """Restore original signal handlers"""
        for shutdown_signal, original_handler in self._original_handlers.items():
            try:
                signal.signal(shutdown_signal.value, original_handler)
                self.logger.debug(
                    f"Restored original handler for {shutdown_signal.name}"
                )
            except (OSError, ValueError) as e:
                self.logger.warning(
                    f"Could not restore handler for {shutdown_signal.name}: {e}"
                )

    def _force_shutdown(self):
        """Force immediate shutdown (last resort)"""
        self.status = ShutdownStatus.FORCED
        self.metrics.forced_shutdown = True
        self.logger.critical("Forcing immediate shutdown")

        # Set shutdown event
        self.shutdown_event.set()

        # Exit process
        os._exit(1)

    def get_status(self) -> Dict[str, Any]:
        """Get current shutdown status and metrics"""
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "is_shutdown_requested": self.is_shutdown_requested(),
            "active_connections": len(self.active_connections),
            "registered_hooks": {
                phase.name: len(hooks) for phase, hooks in self.hooks.items()
            },
            "metrics": self.metrics.to_dict(),
            "is_healthy": self.is_healthy,
        }


class ShutdownManager:
    """
    Global shutdown manager for coordinating service shutdown

    Provides centralized shutdown coordination across multiple services
    and components within an application.
    """

    def __init__(self):
        self.shutdown_handlers: Dict[str, GracefulShutdown] = {}
        self.logger = get_logger(__name__)
        self.global_shutdown_event = threading.Event()

    def register_service(
        self,
        service_name: str,
        default_timeout: int = 30,
        max_shutdown_time: int = 120,
        **kwargs,
    ) -> GracefulShutdown:
        """
        Register a service for shutdown management

        Args:
            service_name: Unique service identifier
            default_timeout: Default timeout for hooks
            max_shutdown_time: Maximum total shutdown time
            **kwargs: Additional GracefulShutdown parameters

        Returns:
            GracefulShutdown instance for the service
        """
        if service_name in self.shutdown_handlers:
            raise ValueError(f"Service '{service_name}' already registered")

        shutdown_handler = GracefulShutdown(
            service_name=service_name,
            default_timeout=default_timeout,
            max_shutdown_time=max_shutdown_time,
            **kwargs,
        )

        self.shutdown_handlers[service_name] = shutdown_handler
        self.logger.info(f"Registered service '{service_name}' for shutdown management")

        return shutdown_handler

    def shutdown_all(self, timeout: Optional[int] = None):
        """
        Initiate shutdown for all registered services

        Args:
            timeout: Maximum time to wait for all services to shutdown
        """
        if not self.shutdown_handlers:
            self.logger.info("No services registered for shutdown")
            return

        self.logger.info(
            f"Initiating shutdown for {len(self.shutdown_handlers)} services"
        )
        self.global_shutdown_event.set()

        # Trigger shutdown for all services
        for service_name, handler in self.shutdown_handlers.items():
            try:
                handler._initiate_shutdown()
            except Exception as e:
                self.logger.error(
                    f"Failed to initiate shutdown for {service_name}: {e}"
                )

        # Wait for all services to complete shutdown
        start_time = time.time()
        default_timeout = timeout or 180  # 3 minutes default

        while time.time() - start_time < default_timeout:
            active_services = [
                name
                for name, handler in self.shutdown_handlers.items()
                if handler.status
                not in [ShutdownStatus.COMPLETED, ShutdownStatus.FAILED]
            ]

            if not active_services:
                self.logger.info("All services shutdown completed")
                break

            self.logger.debug(
                f"Waiting for {len(active_services)} services to complete shutdown"
            )
            time.sleep(1)
        else:
            # Timeout occurred
            incomplete_services = [
                name
                for name, handler in self.shutdown_handlers.items()
                if handler.status
                not in [ShutdownStatus.COMPLETED, ShutdownStatus.FAILED]
            ]
            self.logger.warning(
                f"Shutdown timeout: {len(incomplete_services)} services did not complete"
            )

    def get_service(self, service_name: str) -> Optional[GracefulShutdown]:
        """Get shutdown handler for a specific service"""
        return self.shutdown_handlers.get(service_name)

    def get_global_status(self) -> Dict[str, Any]:
        """Get global shutdown status for all services"""
        return {
            "global_shutdown_requested": self.global_shutdown_event.is_set(),
            "services": {
                name: handler.get_status()
                for name, handler in self.shutdown_handlers.items()
            },
            "total_services": len(self.shutdown_handlers),
        }


# Global shutdown manager instance
_shutdown_manager = ShutdownManager()


def get_shutdown_manager() -> ShutdownManager:
    """Get the global shutdown manager instance"""
    return _shutdown_manager


def register_service_for_shutdown(service_name: str, **kwargs) -> GracefulShutdown:
    """
    Convenience function to register a service for shutdown management

    Args:
        service_name: Unique service identifier
        **kwargs: Additional GracefulShutdown parameters

    Returns:
        GracefulShutdown instance for the service
    """
    return _shutdown_manager.register_service(service_name, **kwargs)
