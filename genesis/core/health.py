"""Lightweight health check system."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class HealthStatus(Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class CheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class HealthCheck:
    """Simple health check coordinator."""
    
    def __init__(self):
        self._checks: dict[str, Callable[[], CheckResult]] = {}
    
    def add_check(self, name: str, check_func: Callable[[], CheckResult]) -> None:
        """Add a health check function.
        
        Args:
            name: Unique name for the check
            check_func: Function that returns CheckResult
        """
        self._checks[name] = check_func
    
    def remove_check(self, name: str) -> None:
        """Remove a health check by name."""
        self._checks.pop(name, None)
    
    def run_check(self, name: str) -> CheckResult:
        """Run a single health check by name."""
        if name not in self._checks:
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check '{name}' not found"
            )
        
        start_time = time.time()
        try:
            result = self._checks[name]()
            result.duration_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def run_all_checks(self) -> list[CheckResult]:
        """Run all registered health checks."""
        return [self.run_check(name) for name in self._checks.keys()]
    
    def get_overall_status(self) -> HealthStatus:
        """Get overall health status based on all checks."""
        if not self._checks:
            return HealthStatus.HEALTHY
        
        results = self.run_all_checks()
        
        # If any check is unhealthy, overall is unhealthy
        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            return HealthStatus.UNHEALTHY
        
        # If any check is degraded, overall is degraded
        if any(r.status == HealthStatus.DEGRADED for r in results):
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def get_summary(self) -> dict[str, Any]:
        """Get health check summary."""
        results = self.run_all_checks()
        overall_status = self.get_overall_status()
        
        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                    "metadata": r.metadata,
                }
                for r in results
            ],
            "summary": {
                "total_checks": len(results),
                "healthy": sum(1 for r in results if r.status == HealthStatus.HEALTHY),
                "unhealthy": sum(1 for r in results if r.status == HealthStatus.UNHEALTHY),
                "degraded": sum(1 for r in results if r.status == HealthStatus.DEGRADED),
            }
        }