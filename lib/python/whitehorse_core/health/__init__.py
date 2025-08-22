"""
Health Check Module

Comprehensive health monitoring and status reporting for services,
dependencies, and infrastructure components.
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import psutil

from ..errors import DatabaseError, NetworkError, SystemError
from ..logging import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    message: str
    timestamp: float
    duration_ms: float
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["status"] = self.status.value
        return result


class HealthCheck(ABC):
    """Abstract base class for health checks."""

    def __init__(self, name: str, timeout: float = 10.0, critical: bool = True):
        self.name = name
        self.timeout = timeout
        self.critical = critical  # Whether failure should mark service as unhealthy

    @abstractmethod
    def check(self) -> HealthCheckResult:
        """Perform the health check."""
        pass

    def check_with_timeout(self) -> HealthCheckResult:
        """Perform health check with timeout."""
        start_time = time.time()

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.check)
                result = future.result(timeout=self.timeout)
                return result
        except TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(f"Health check {self.name} timed out after {self.timeout}s")
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s",
                timestamp=time.time(),
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Health check {self.name} failed: {e}")
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=time.time(),
                duration_ms=duration_ms,
            )


class SystemHealthCheck(HealthCheck):
    """System resource health check."""

    def __init__(
        self,
        name: str = "system",
        cpu_threshold: float = 90.0,
        memory_threshold: float = 90.0,
        disk_threshold: float = 90.0,
        **kwargs,
    ):
        super().__init__(name, **kwargs)
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

    def check(self) -> HealthCheckResult:
        """Check system resources."""
        start_time = time.time()

        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            # Determine status
            status = HealthStatus.HEALTHY
            issues = []

            if cpu_percent > self.cpu_threshold:
                status = (
                    HealthStatus.DEGRADED
                    if status == HealthStatus.HEALTHY
                    else HealthStatus.UNHEALTHY
                )
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")

            if memory_percent > self.memory_threshold:
                status = (
                    HealthStatus.DEGRADED
                    if status == HealthStatus.HEALTHY
                    else HealthStatus.UNHEALTHY
                )
                issues.append(f"High memory usage: {memory_percent:.1f}%")

            if disk_percent > self.disk_threshold:
                status = (
                    HealthStatus.DEGRADED
                    if status == HealthStatus.HEALTHY
                    else HealthStatus.UNHEALTHY
                )
                issues.append(f"High disk usage: {disk_percent:.1f}%")

            message = "System resources healthy" if not issues else "; ".join(issues)

            duration_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                timestamp=time.time(),
                duration_ms=duration_ms,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "available_memory_gb": memory.available / (1024**3),
                    "available_disk_gb": disk.free / (1024**3),
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check system resources: {str(e)}",
                timestamp=time.time(),
                duration_ms=duration_ms,
            )


class DatabaseHealthCheck(HealthCheck):
    """Database connectivity health check."""

    def __init__(
        self, name: str = "database", connection_factory: Callable = None, **kwargs
    ):
        super().__init__(name, **kwargs)
        self.connection_factory = connection_factory

    def check(self) -> HealthCheckResult:
        """Check database connectivity."""
        start_time = time.time()

        try:
            if not self.connection_factory:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNKNOWN,
                    message="No database connection factory provided",
                    timestamp=time.time(),
                    duration_ms=0,
                )

            # Test database connection
            with self.connection_factory() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

                if result and result[0] == 1:
                    status = HealthStatus.HEALTHY
                    message = "Database connection successful"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = "Database query returned unexpected result"

            duration_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                timestamp=time.time(),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database health check failed: {str(e)}",
                timestamp=time.time(),
                duration_ms=duration_ms,
            )


class RedisHealthCheck(HealthCheck):
    """Redis connectivity health check."""

    def __init__(self, name: str = "redis", redis_client=None, **kwargs):
        super().__init__(name, **kwargs)
        self.redis_client = redis_client

    def check(self) -> HealthCheckResult:
        """Check Redis connectivity."""
        start_time = time.time()

        try:
            if not self.redis_client:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNKNOWN,
                    message="No Redis client provided",
                    timestamp=time.time(),
                    duration_ms=0,
                )

            # Test Redis connection
            result = self.redis_client.ping()

            if result:
                status = HealthStatus.HEALTHY
                message = "Redis connection successful"

                # Get additional info
                info = self.redis_client.info()
                details = {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "redis_version": info.get("redis_version", "unknown"),
                }
            else:
                status = HealthStatus.UNHEALTHY
                message = "Redis ping failed"
                details = None

            duration_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                timestamp=time.time(),
                duration_ms=duration_ms,
                details=details,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis health check failed: {str(e)}",
                timestamp=time.time(),
                duration_ms=duration_ms,
            )


class HTTPHealthCheck(HealthCheck):
    """HTTP endpoint health check."""

    def __init__(
        self,
        name: str,
        url: str,
        expected_status: int = 200,
        expected_content: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(name, **kwargs)
        self.url = url
        self.expected_status = expected_status
        self.expected_content = expected_content
        self.headers = headers or {}

    def check(self) -> HealthCheckResult:
        """Check HTTP endpoint."""
        start_time = time.time()

        try:
            import requests

            response = requests.get(
                self.url, headers=self.headers, timeout=self.timeout
            )

            duration_ms = (time.time() - start_time) * 1000

            # Check status code
            if response.status_code != self.expected_status:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Unexpected status code: {response.status_code} (expected: {self.expected_status})",
                    timestamp=time.time(),
                    duration_ms=duration_ms,
                    details={
                        "status_code": response.status_code,
                        "response_time_ms": duration_ms,
                    },
                )

            # Check content if specified
            if self.expected_content and self.expected_content not in response.text:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Expected content not found in response",
                    timestamp=time.time(),
                    duration_ms=duration_ms,
                    details={
                        "status_code": response.status_code,
                        "response_time_ms": duration_ms,
                    },
                )

            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="HTTP endpoint responding correctly",
                timestamp=time.time(),
                duration_ms=duration_ms,
                details={
                    "status_code": response.status_code,
                    "response_time_ms": duration_ms,
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"HTTP health check failed: {str(e)}",
                timestamp=time.time(),
                duration_ms=duration_ms,
            )


class CustomHealthCheck(HealthCheck):
    """Custom health check with user-defined check function."""

    def __init__(self, name: str, check_function: Callable[[], bool], **kwargs):
        super().__init__(name, **kwargs)
        self.check_function = check_function

    def check(self) -> HealthCheckResult:
        """Perform custom health check."""
        start_time = time.time()

        try:
            result = self.check_function()
            duration_ms = (time.time() - start_time) * 1000

            if result:
                status = HealthStatus.HEALTHY
                message = "Custom health check passed"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Custom health check failed"

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                timestamp=time.time(),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Custom health check error: {str(e)}",
                timestamp=time.time(),
                duration_ms=duration_ms,
            )


class HealthMonitor:
    """
    Health monitoring service that aggregates multiple health checks.
    """

    def __init__(self, service_name: str = "whitehorse-service"):
        self.service_name = service_name
        self.health_checks: List[HealthCheck] = []
        self.last_results: Dict[str, HealthCheckResult] = {}
        self._lock = threading.Lock()

    def add_check(self, health_check: HealthCheck) -> None:
        """Add a health check to the monitor."""
        with self._lock:
            self.health_checks.append(health_check)
            logger.info(f"Added health check: {health_check.name}")

    def remove_check(self, name: str) -> None:
        """Remove a health check by name."""
        with self._lock:
            self.health_checks = [hc for hc in self.health_checks if hc.name != name]
            if name in self.last_results:
                del self.last_results[name]
            logger.info(f"Removed health check: {name}")

    def run_checks(self, parallel: bool = True) -> Dict[str, HealthCheckResult]:
        """
        Run all health checks.

        Args:
            parallel: Whether to run checks in parallel

        Returns:
            Dictionary of health check results
        """
        if not self.health_checks:
            return {}

        if parallel:
            return self._run_checks_parallel()
        else:
            return self._run_checks_sequential()

    def _run_checks_parallel(self) -> Dict[str, HealthCheckResult]:
        """Run health checks in parallel."""
        results = {}

        with ThreadPoolExecutor(max_workers=len(self.health_checks)) as executor:
            future_to_check = {
                executor.submit(check.check_with_timeout): check
                for check in self.health_checks
            }

            for future in future_to_check:
                check = future_to_check[future]
                try:
                    result = future.result()
                    results[check.name] = result
                except Exception as e:
                    logger.error(
                        f"Health check {check.name} failed with exception: {e}"
                    )
                    results[check.name] = HealthCheckResult(
                        name=check.name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check failed with exception: {str(e)}",
                        timestamp=time.time(),
                        duration_ms=0,
                    )

        with self._lock:
            self.last_results.update(results)

        return results

    def _run_checks_sequential(self) -> Dict[str, HealthCheckResult]:
        """Run health checks sequentially."""
        results = {}

        for check in self.health_checks:
            try:
                result = check.check_with_timeout()
                results[check.name] = result
            except Exception as e:
                logger.error(f"Health check {check.name} failed with exception: {e}")
                results[check.name] = HealthCheckResult(
                    name=check.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed with exception: {str(e)}",
                    timestamp=time.time(),
                    duration_ms=0,
                )

        with self._lock:
            self.last_results.update(results)

        return results

    def get_overall_status(
        self, results: Optional[Dict[str, HealthCheckResult]] = None
    ) -> HealthStatus:
        """
        Get overall service health status.

        Args:
            results: Health check results (uses last results if not provided)

        Returns:
            Overall health status
        """
        if results is None:
            results = self.last_results

        if not results:
            return HealthStatus.UNKNOWN

        # Check critical health checks first
        critical_checks = [hc for hc in self.health_checks if hc.critical]
        for check in critical_checks:
            if check.name in results:
                result = results[check.name]
                if result.status == HealthStatus.UNHEALTHY:
                    return HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED:
                    return HealthStatus.DEGRADED

        # Check all other health checks
        statuses = [result.status for result in results.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.DEGRADED  # Non-critical failures degrade service
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report."""
        results = self.run_checks()
        overall_status = self.get_overall_status(results)

        return {
            "service": self.service_name,
            "status": overall_status.value,
            "timestamp": time.time(),
            "checks": {name: result.to_dict() for name, result in results.items()},
            "summary": {
                "total_checks": len(results),
                "healthy": sum(
                    1 for r in results.values() if r.status == HealthStatus.HEALTHY
                ),
                "degraded": sum(
                    1 for r in results.values() if r.status == HealthStatus.DEGRADED
                ),
                "unhealthy": sum(
                    1 for r in results.values() if r.status == HealthStatus.UNHEALTHY
                ),
                "unknown": sum(
                    1 for r in results.values() if r.status == HealthStatus.UNKNOWN
                ),
            },
        }

    def start_monitoring(self, interval: float = 30.0) -> None:
        """
        Start background health monitoring.

        Args:
            interval: Check interval in seconds
        """

        def monitor_loop():
            while True:
                try:
                    results = self.run_checks()
                    overall_status = self.get_overall_status(results)

                    logger.info(
                        "Health check completed",
                        service=self.service_name,
                        overall_status=overall_status.value,
                        check_count=len(results),
                    )

                    # Log unhealthy checks
                    for name, result in results.items():
                        if result.status == HealthStatus.UNHEALTHY:
                            logger.warning(
                                f"Health check unhealthy: {name}",
                                check=name,
                                message=result.message,
                                duration_ms=result.duration_ms,
                            )

                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")

                time.sleep(interval)

        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

        logger.info(f"Started health monitoring with {interval}s interval")


# Default health monitor instance
default_health_monitor = HealthMonitor()
