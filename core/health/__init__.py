"""
Genesis Health Check System

Provides comprehensive health monitoring with:
- Health status enumeration (HEALTHY, DEGRADED, UNHEALTHY)
- Abstract base classes for health checks
- Built-in health checks for common services
- Health check registry management
- Kubernetes probe support
- JSON serializable health reports
- Integration with existing Genesis error and logging systems

Usage:
    from core.health import HealthCheckRegistry, HealthStatus, HTTPHealthCheck

    # Create health check registry
    registry = HealthCheckRegistry()

    # Add health checks
    registry.add_check(HTTPHealthCheck("api", "https://api.example.com/health"))

    # Get health status
    status = await registry.check_health()
    print(f"Overall health: {status.status}")
"""

from .checker import (
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

__all__ = [
    # Core classes
    "HealthStatus",
    "HealthCheck",
    "HealthCheckResult",
    "HealthCheckRegistry",
    # Built-in health checks
    "HTTPHealthCheck",
    "DatabaseHealthCheck",
    "DiskHealthCheck",
    "MemoryHealthCheck",
    # Kubernetes support
    "ProbeType",
    "KubernetesProbeHandler",
    # Health reporting
    "HealthReport",
]
