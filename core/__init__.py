"""
Genesis Core Plumbing Library

Production-ready foundational components for cloud-native applications.
Provides structured error handling, logging, retry logic, health checks,
and context management with thread-safe implementations.

Quick Start:
    >>> from core import get_logger, handle_error, retry
    >>> from core.context import get_context, set_context

    >>> # Structured logging
    >>> logger = get_logger(__name__)
    >>> logger.info("Application starting")

    >>> # Error handling
    >>> try:
    >>>     risky_operation()
    >>> except Exception as e:
    >>>     genesis_error = handle_error(e)
    >>>     logger.error("Operation failed", error=genesis_error)

    >>> # Retry logic
    >>> @retry(max_attempts=3, backoff='exponential')
    >>> def unreliable_operation():
    >>>     return external_service_call()

    >>> # Health checks
    >>> from core.health import HealthCheckRegistry
    >>> registry = HealthCheckRegistry()
    >>> registry.add_check(HTTPHealthCheck("api", "https://api.example.com/health"))
    >>> health = await registry.check_health()

Components:
    - errors: Structured error handling with categorization and context
    - logging: JSON structured logging with context injection
    - retry: Exponential backoff retry logic with circuit breakers
    - health: Comprehensive health monitoring and Kubernetes probes
    - context: Thread-safe context management for distributed tracing
"""

# Version information
__version__ = "1.0.0"
__author__ = "Genesis Core Team"

# Context management
from .context import (
    Context,
    ContextManager,
    RequestContext,
    TraceContext,
    UserContext,
    clear_context,
    context_span,
    current_context,
    get_context,
    set_context,
)

# Core error handling
from .errors.handler import (
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    ErrorSeverity,
    GenesisError,
    InfrastructureError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    ValidationError,
    get_error_handler,
    handle_error,
)

# Health monitoring
from .health import (
    DatabaseHealthCheck,
    DiskHealthCheck,
    HealthCheck,
    HealthCheckRegistry,
    HealthCheckResult,
    HealthReport,
    HealthStatus,
    HTTPHealthCheck,
    KubernetesProbeHandler,
    MemoryHealthCheck,
    ProbeType,
)

# Structured logging
from .logging.logger import (
    GenesisLogger,
    JsonFormatter,
    LoggerFactory,
    LogLevel,
    get_logger,
)

# Retry logic and circuit breakers
from .retry import (
    AGGRESSIVE_POLICY,
    CONSERVATIVE_POLICY,
    DEFAULT_POLICY,
    BackoffStrategy,
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
    RetryExecutor,
    RetryPolicy,
    create_policy,
    retry,
    retry_async,
)

# Public API exports
__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Error handling
    "GenesisError",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorContext",
    "ErrorHandler",
    "InfrastructureError",
    "ValidationError",
    "NetworkError",
    "TimeoutError",
    "RateLimitError",
    "handle_error",
    "get_error_handler",
    # Logging
    "GenesisLogger",
    "LogLevel",
    "LoggerFactory",
    "JsonFormatter",
    "get_logger",
    # Retry and circuit breakers
    "RetryPolicy",
    "RetryExecutor",
    "BackoffStrategy",
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerError",
    "retry",
    "retry_async",
    "DEFAULT_POLICY",
    "AGGRESSIVE_POLICY",
    "CONSERVATIVE_POLICY",
    "create_policy",
    # Health monitoring
    "HealthStatus",
    "HealthCheck",
    "HealthCheckResult",
    "HealthCheckRegistry",
    "HTTPHealthCheck",
    "DatabaseHealthCheck",
    "DiskHealthCheck",
    "MemoryHealthCheck",
    "ProbeType",
    "KubernetesProbeHandler",
    "HealthReport",
    # Context management
    "Context",
    "RequestContext",
    "UserContext",
    "TraceContext",
    "ContextManager",
    "get_context",
    "set_context",
    "clear_context",
    "context_span",
    "current_context",
]


# Integration helpers
def configure_core(
    service_name: str,
    environment: str = "development",
    version: str = "1.0.0",
    log_level: str = "INFO",
) -> None:
    """
    Configure all core components with consistent settings

    Args:
        service_name: Name of the service
        environment: Environment (development, staging, production)
        version: Service version
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure logging
    LoggerFactory.configure(
        service=service_name,
        environment=environment,
        version=version,
        default_level=log_level,
    )

    # Configure error handler
    error_handler = get_error_handler()
    error_handler.service_name = service_name
    error_handler.environment = environment

    # Create base context
    base_context = Context.new_context(
        service=service_name,
        environment=environment,
        version=version,
    )
    set_context(base_context)

    # Log configuration
    logger = get_logger(__name__)
    logger.info(
        "Genesis core configured",
        service=service_name,
        environment=environment,
        version=version,
        log_level=log_level,
    )


def get_service_health_registry() -> HealthCheckRegistry:
    """
    Get or create a health registry with basic service checks

    Returns:
        HealthCheckRegistry with basic health checks configured
    """
    registry = HealthCheckRegistry()

    # Add basic system health checks if not already present
    if "disk_space" not in registry.list_checks():
        registry.add_check(DiskHealthCheck("disk_space"))

    if "memory_usage" not in registry.list_checks():
        registry.add_check(MemoryHealthCheck("memory_usage"))

    return registry


# Add to __all__
__all__.extend(
    [
        "configure_core",
        "get_service_health_registry",
    ]
)


import logging

# Initialize logging on import
import os

# Configure basic logging if not already configured
if not logging.getLogger().handlers:
    LoggerFactory.configure(
        service=os.environ.get("GENESIS_SERVICE", "genesis"),
        environment=os.environ.get("GENESIS_ENV", "development"),
        version=os.environ.get("GENESIS_VERSION", "1.0.0"),
        default_level=os.environ.get("GENESIS_LOG_LEVEL", "INFO"),
    )
