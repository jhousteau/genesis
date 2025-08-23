"""
Genesis Lifecycle Management Framework

Comprehensive lifecycle management for Genesis services using SPIDER methodology:
- S: Symptom identification through health monitoring
- P: Problem isolation via component tracking
- I: Investigation through comprehensive logging
- D: Diagnosis with structured error handling
- E: Execution of graceful startup/shutdown
- R: Review and continuous improvement

Features:
- Graceful shutdown with configurable timeouts
- Orchestrated startup sequence
- Priority-based hook system
- Health check integration
- Cloud-native compatibility (Kubernetes, containers)
- Signal handling and resource cleanup
"""

from .hooks import (HookEvent, HookPriority, LifecycleHook, hook_manager,
                    lifecycle_hook)
from .manager import (LifecycleManager, configure_lifecycle_manager,
                      create_kubernetes_probes, get_lifecycle_manager)
from .shutdown import (GracefulShutdown, ShutdownManager, get_shutdown_manager,
                       register_service_for_shutdown)
from .startup import (DependencyType, StartupManager, StartupPhase,
                      StartupStatus)

__all__ = [
    # Hooks
    "LifecycleHook",
    "HookPriority",
    "HookEvent",
    "hook_manager",
    "lifecycle_hook",
    # Manager
    "LifecycleManager",
    "get_lifecycle_manager",
    "configure_lifecycle_manager",
    "create_kubernetes_probes",
    # Shutdown
    "GracefulShutdown",
    "ShutdownManager",
    "get_shutdown_manager",
    "register_service_for_shutdown",
    # Startup
    "StartupManager",
    "StartupPhase",
    "StartupStatus",
    "DependencyType",
]

__version__ = "1.0.0"
