"""
Genesis Lifecycle Hooks Framework

Extensible hook system for lifecycle events with:
- Priority-based execution ordering
- Async and sync hook support
- Error handling and recovery
- Context passing between hooks
- Plugin-style architecture
- Event-driven lifecycle management

Follows SPIDER methodology for reliable hook execution.
"""

import asyncio
import inspect
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional
from weakref import WeakSet

from ..errors.handler import GenesisError, get_error_handler
from ..logging.logger import get_logger


class HookPriority(IntEnum):
    """Hook execution priorities (lower numbers execute first)"""

    CRITICAL = 0  # System-critical hooks (signal handlers, etc.)
    HIGH = 100  # High priority (security, auth)
    NORMAL = 500  # Normal application hooks
    LOW = 800  # Low priority (cleanup, logging)
    BACKGROUND = 1000  # Background tasks


class HookEvent(IntEnum):
    """Lifecycle events that can trigger hooks"""

    # Startup events
    PRE_STARTUP = 1
    POST_STARTUP = 2
    STARTUP_FAILED = 3

    # Shutdown events
    PRE_SHUTDOWN = 10
    POST_SHUTDOWN = 11
    SHUTDOWN_FAILED = 12

    # Configuration events
    CONFIG_LOADED = 20
    CONFIG_CHANGED = 21
    CONFIG_VALIDATION_FAILED = 22

    # Health check events
    HEALTH_CHECK_PASSED = 30
    HEALTH_CHECK_FAILED = 31

    # Service events
    SERVICE_READY = 40
    SERVICE_DEGRADED = 41
    SERVICE_RECOVERING = 42

    # Error events
    ERROR_OCCURRED = 50
    CRITICAL_ERROR = 51

    # Custom events (user-defined)
    CUSTOM_EVENT = 1000


@dataclass
class HookContext:
    """Context passed to hooks during execution"""

    event: HookEvent
    timestamp: datetime = field(default_factory=datetime.utcnow)
    service_name: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    previous_results: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get data from context"""
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        """Set data in context"""
        self.data[key] = value

    def add_result(self, hook_name: str, result: Any):
        """Add result from a hook execution"""
        self.previous_results[hook_name] = result


@dataclass
class HookResult:
    """Result from hook execution"""

    hook_name: str
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "hook_name": self.hook_name,
            "success": self.success,
            "result": self.result,
            "error": str(self.error) if self.error else None,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class LifecycleHook(ABC):
    """
    Abstract base class for lifecycle hooks

    Provides standard interface for lifecycle event handling
    with priority ordering and error management.
    """

    def __init__(
        self,
        name: str,
        priority: HookPriority = HookPriority.NORMAL,
        description: str = "",
        async_hook: bool = False,
        timeout: int = 30,
        critical: bool = False,
    ):
        self.name = name
        self.priority = priority
        self.description = description
        self.async_hook = async_hook
        self.timeout = timeout
        self.critical = critical  # If True, hook failure stops execution
        self.logger = get_logger(f"{__name__}.{name}")
        self.created_at = datetime.utcnow()

    @abstractmethod
    def execute(self, context: HookContext) -> Any:
        """
        Execute the hook with given context

        Args:
            context: Hook execution context

        Returns:
            Hook execution result
        """
        pass

    def can_execute(self, context: HookContext) -> bool:
        """
        Check if hook can execute in current context

        Override for conditional execution logic.

        Args:
            context: Hook execution context

        Returns:
            True if hook should execute
        """
        return True

    def on_error(self, error: Exception, context: HookContext):
        """
        Handle hook execution error

        Override for custom error handling.

        Args:
            error: Exception that occurred
            context: Hook execution context
        """
        self.logger.error(f"Hook '{self.name}' failed: {error}")

    def __lt__(self, other):
        """Support sorting by priority"""
        return self.priority < other.priority

    def __repr__(self):
        return f"LifecycleHook(name='{self.name}', priority={self.priority.name})"


class FunctionHook(LifecycleHook):
    """Hook that wraps a function or callable"""

    def __init__(
        self,
        name: str,
        func: Callable,
        priority: HookPriority = HookPriority.NORMAL,
        description: str = "",
        timeout: int = 30,
        critical: bool = False,
    ):
        # Detect if function is async
        async_hook = asyncio.iscoroutinefunction(func)

        super().__init__(
            name=name,
            priority=priority,
            description=description,
            async_hook=async_hook,
            timeout=timeout,
            critical=critical,
        )

        self.func = func

        # Analyze function signature for context support
        sig = inspect.signature(func)
        self.accepts_context = "context" in sig.parameters

    def execute(self, context: HookContext) -> Any:
        """Execute the wrapped function"""
        if self.accepts_context:
            return self.func(context)
        else:
            # Function doesn't accept context, call without it
            return self.func()


class HookManager:
    """
    Central manager for lifecycle hooks

    Coordinates hook registration, execution, and lifecycle management
    across all Genesis services and components.
    """

    def __init__(self, service_name: str = "genesis"):
        self.service_name = service_name
        self.hooks: Dict[HookEvent, List[LifecycleHook]] = {}
        self.execution_history: List[HookResult] = []
        self.active_hooks: WeakSet = WeakSet()
        self.logger = get_logger(f"{__name__}.manager")
        self.error_handler = get_error_handler()

        # Thread safety
        self._lock = threading.RLock()

        # Statistics
        self.stats = {
            "hooks_registered": 0,
            "hooks_executed": 0,
            "hooks_failed": 0,
            "events_triggered": 0,
        }

    def register_hook(self, event: HookEvent, hook: LifecycleHook):
        """
        Register a hook for a specific lifecycle event

        Args:
            event: Lifecycle event to hook into
            hook: Hook instance to register
        """
        with self._lock:
            if event not in self.hooks:
                self.hooks[event] = []

            # Check for duplicate names
            existing_names = {h.name for h in self.hooks[event]}
            if hook.name in existing_names:
                raise ValueError(
                    f"Hook with name '{hook.name}' already registered for event {event.name}"
                )

            self.hooks[event].append(hook)
            self.active_hooks.add(hook)
            self.stats["hooks_registered"] += 1

            # Sort hooks by priority
            self.hooks[event].sort()

            self.logger.debug(
                f"Registered hook '{hook.name}' for event {event.name} with priority {hook.priority.name}"
            )

    def register_function(
        self,
        event: HookEvent,
        func: Callable,
        name: Optional[str] = None,
        priority: HookPriority = HookPriority.NORMAL,
        description: str = "",
        timeout: int = 30,
        critical: bool = False,
    ) -> FunctionHook:
        """
        Register a function as a hook

        Args:
            event: Lifecycle event to hook into
            func: Function to register
            name: Hook name (defaults to function name)
            priority: Hook priority
            description: Hook description
            timeout: Execution timeout
            critical: Whether hook failure should stop execution

        Returns:
            Created FunctionHook instance
        """
        hook_name = name or getattr(func, "__name__", "anonymous_hook")

        hook = FunctionHook(
            name=hook_name,
            func=func,
            priority=priority,
            description=description,
            timeout=timeout,
            critical=critical,
        )

        self.register_hook(event, hook)
        return hook

    def unregister_hook(self, event: HookEvent, hook_name: str) -> bool:
        """
        Unregister a hook

        Args:
            event: Lifecycle event
            hook_name: Name of hook to remove

        Returns:
            True if hook was found and removed
        """
        with self._lock:
            if event not in self.hooks:
                return False

            hooks = self.hooks[event]
            for i, hook in enumerate(hooks):
                if hook.name == hook_name:
                    removed_hook = hooks.pop(i)
                    self.active_hooks.discard(removed_hook)
                    self.logger.debug(
                        f"Unregistered hook '{hook_name}' from event {event.name}"
                    )
                    return True

            return False

    async def trigger_event(
        self,
        event: HookEvent,
        data: Optional[Dict[str, Any]] = None,
        stop_on_error: bool = False,
    ) -> List[HookResult]:
        """
        Trigger all hooks for a lifecycle event

        Args:
            event: Event to trigger
            data: Data to pass to hooks
            stop_on_error: Whether to stop execution on first error

        Returns:
            List of hook execution results
        """
        with self._lock:
            hooks = self.hooks.get(event, [])

        if not hooks:
            self.logger.debug(f"No hooks registered for event {event.name}")
            return []

        self.stats["events_triggered"] += 1
        self.logger.info(f"Triggering {len(hooks)} hooks for event {event.name}")

        # Create execution context
        context = HookContext(
            event=event, service_name=self.service_name, data=data or {}
        )

        results = []

        for hook in hooks:
            # Check if hook can execute
            if not hook.can_execute(context):
                self.logger.debug(f"Skipping hook '{hook.name}' - conditions not met")
                continue

            # Execute hook
            result = await self._execute_single_hook(hook, context)
            results.append(result)

            # Add result to context for subsequent hooks
            context.add_result(hook.name, result.result)

            # Update statistics
            self.stats["hooks_executed"] += 1
            if not result.success:
                self.stats["hooks_failed"] += 1

                # Handle critical hook failure
                if hook.critical or stop_on_error:
                    self.logger.error(
                        f"Critical hook '{hook.name}' failed, stopping execution"
                    )
                    break

        self.logger.info(f"Completed event {event.name}: {len(results)} hooks executed")
        return results

    async def _execute_single_hook(
        self, hook: LifecycleHook, context: HookContext
    ) -> HookResult:
        """Execute a single hook with timeout and error handling"""
        start_time = asyncio.get_event_loop().time()

        try:
            self.logger.debug(f"Executing hook '{hook.name}'")

            if hook.async_hook:
                # Execute async hook with timeout
                result = await asyncio.wait_for(
                    hook.execute(context), timeout=hook.timeout
                )
            else:
                # Execute sync hook in executor with timeout
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, hook.execute, context),
                    timeout=hook.timeout,
                )

            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

            hook_result = HookResult(
                hook_name=hook.name,
                success=True,
                result=result,
                execution_time_ms=execution_time,
            )

            self.logger.debug(f"Hook '{hook.name}' completed in {execution_time:.2f}ms")
            return hook_result

        except asyncio.TimeoutError:
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            error = GenesisError(
                f"Hook '{hook.name}' timed out after {hook.timeout}s",
                code="HOOK_TIMEOUT",
            )

            hook.on_error(error, context)
            self.error_handler.handle(error)

            return HookResult(
                hook_name=hook.name,
                success=False,
                error=error,
                execution_time_ms=execution_time,
            )

        except Exception as error:
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

            hook.on_error(error, context)
            self.error_handler.handle(error)

            return HookResult(
                hook_name=hook.name,
                success=False,
                error=error,
                execution_time_ms=execution_time,
            )

    def get_hooks_for_event(self, event: HookEvent) -> List[LifecycleHook]:
        """Get all hooks registered for an event"""
        with self._lock:
            return list(self.hooks.get(event, []))

    def get_hook_count(self, event: Optional[HookEvent] = None) -> int:
        """Get count of registered hooks"""
        with self._lock:
            if event is None:
                return sum(len(hooks) for hooks in self.hooks.values())
            return len(self.hooks.get(event, []))

    def get_execution_history(self, limit: Optional[int] = None) -> List[HookResult]:
        """Get hook execution history"""
        history = list(self.execution_history)
        if limit:
            return history[-limit:]
        return history

    def clear_history(self):
        """Clear execution history"""
        self.execution_history.clear()
        self.logger.debug("Cleared hook execution history")

    def get_statistics(self) -> Dict[str, Any]:
        """Get hook manager statistics"""
        with self._lock:
            return {
                **self.stats,
                "active_hooks": len(self.active_hooks),
                "events_with_hooks": len(self.hooks),
                "hooks_by_event": {
                    event.name: len(hooks) for event, hooks in self.hooks.items()
                },
            }

    def health_check(self) -> bool:
        """Perform health check on hook manager"""
        try:
            # Check if we can access hooks safely
            with self._lock:
                total_hooks = sum(len(hooks) for hooks in self.hooks.values())

            # Basic sanity check
            return total_hooks >= 0

        except Exception as e:
            self.logger.error(f"Hook manager health check failed: {e}")
            return False


# Decorator for registering function hooks
def lifecycle_hook(
    event: HookEvent,
    priority: HookPriority = HookPriority.NORMAL,
    description: str = "",
    timeout: int = 30,
    critical: bool = False,
    manager: Optional[HookManager] = None,
):
    """
    Decorator to register a function as a lifecycle hook

    Args:
        event: Lifecycle event to hook into
        priority: Hook execution priority
        description: Hook description
        timeout: Execution timeout
        critical: Whether hook failure should stop execution
        manager: Hook manager instance (uses global if None)
    """

    def decorator(func: Callable):
        hook_manager = manager or get_hook_manager()
        hook_manager.register_function(
            event=event,
            func=func,
            priority=priority,
            description=description,
            timeout=timeout,
            critical=critical,
        )
        return func

    return decorator


# Global hook manager instance
_hook_manager: Optional[HookManager] = None


def get_hook_manager(service_name: Optional[str] = None) -> HookManager:
    """
    Get the global hook manager instance

    Args:
        service_name: Service name for new manager

    Returns:
        HookManager instance
    """
    global _hook_manager

    if _hook_manager is None:
        import os

        default_service = service_name or os.environ.get("GENESIS_SERVICE", "genesis")
        _hook_manager = HookManager(default_service)

    return _hook_manager


def configure_hook_manager(service_name: str) -> HookManager:
    """
    Configure the global hook manager

    Args:
        service_name: Service name

    Returns:
        Configured HookManager instance
    """
    global _hook_manager
    _hook_manager = HookManager(service_name)
    return _hook_manager


# Export the global hook manager for convenience
hook_manager = get_hook_manager()
