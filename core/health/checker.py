"""
Genesis Health Check Implementation

Following CRAFT methodology:
- Create: Clean architecture with abstract base classes and implementations
- Refactor: Modular design for easy extension and maintenance
- Authenticate: Secure health check handling with proper error management
- Function: High-performance async health checks with caching
- Test: Comprehensive error handling and logging integration

Provides production-ready health monitoring for Genesis microservices.
"""

import asyncio
import json
import os
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import httpx
except ImportError:
    httpx = None

try:
    import psutil
except ImportError:
    psutil = None

from core.errors.handler import ErrorCategory, GenesisError
from core.logging.logger import get_logger


class HealthStatus(Enum):
    """Health status levels following industry standards"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ProbeType(Enum):
    """Kubernetes probe types"""

    LIVENESS = "liveness"
    READINESS = "readiness"
    STARTUP = "startup"


@dataclass
class HealthCheckResult:
    """
    Result of a health check operation

    Attributes:
        status: Health status (HEALTHY, DEGRADED, UNHEALTHY)
        message: Human-readable status message
        details: Additional context and metrics
        timestamp: When the check was performed
        duration_ms: How long the check took
        metadata: Additional metadata for the check
    """

    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization"""
        return {
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() + "Z",
            "duration_ms": round(self.duration_ms, 2),
            "metadata": self.metadata,
        }

    def is_healthy(self) -> bool:
        """Check if the status indicates health"""
        return self.status == HealthStatus.HEALTHY

    def is_degraded(self) -> bool:
        """Check if the status indicates degraded performance"""
        return self.status == HealthStatus.DEGRADED

    def is_unhealthy(self) -> bool:
        """Check if the status indicates failure"""
        return self.status == HealthStatus.UNHEALTHY


class HealthCheck(ABC):
    """
    Abstract base class for health checks

    All health checks must implement the check_health method and should
    provide appropriate metadata for monitoring and debugging.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        timeout_seconds: int = 10,
        critical: bool = True,
        tags: Optional[List[str]] = None,
    ):
        """
        Initialize health check

        Args:
            name: Unique name for this health check
            description: Human-readable description
            timeout_seconds: Maximum time to wait for check completion
            critical: Whether this check is critical for overall health
            tags: Optional tags for grouping and filtering
        """
        self.name = name
        self.description = description
        self.timeout_seconds = timeout_seconds
        self.critical = critical
        self.tags = tags or []
        self.logger = get_logger(f"HealthCheck.{name}")

    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """
        Perform the health check

        Returns:
            HealthCheckResult with status and details

        Raises:
            GenesisError: On check failure with proper categorization
        """
        pass

    async def execute_with_timeout(self) -> HealthCheckResult:
        """
        Execute the health check with timeout protection

        Returns:
            HealthCheckResult, possibly indicating timeout
        """
        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                self.check_health(), timeout=self.timeout_seconds
            )
            result.duration_ms = (time.time() - start_time) * 1000
            return result

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.warning(
                f"Health check {self.name} timed out",
                timeout_seconds=self.timeout_seconds,
                duration_ms=duration_ms,
            )
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout_seconds}s",
                duration_ms=duration_ms,
                details={"timeout_seconds": self.timeout_seconds},
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"Health check {self.name} failed",
                error=str(e),
                duration_ms=duration_ms,
            )
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms,
                details={"error": str(e), "error_type": type(e).__name__},
            )


class HTTPHealthCheck(HealthCheck):
    """
    HTTP endpoint health check

    Checks the health of HTTP services by making requests to health endpoints.
    Supports custom headers, status code validation, and response content checks.
    """

    def __init__(
        self,
        name: str,
        url: str,
        method: str = "GET",
        expected_status: Union[int, List[int]] = 200,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        verify_ssl: bool = True,
        **kwargs,
    ):
        """
        Initialize HTTP health check

        Args:
            name: Check name
            url: URL to check
            method: HTTP method (GET, POST, etc.)
            expected_status: Expected HTTP status code(s)
            headers: Optional HTTP headers
            body: Optional request body
            verify_ssl: Whether to verify SSL certificates
            **kwargs: Additional HealthCheck arguments
        """
        super().__init__(name, **kwargs)
        self.url = url
        self.method = method.upper()
        self.expected_status = (
            expected_status if isinstance(expected_status, list) else [expected_status]
        )
        self.headers = headers or {}
        self.body = body
        self.verify_ssl = verify_ssl

    async def check_health(self) -> HealthCheckResult:
        """Perform HTTP health check"""
        if aiohttp is None:
            return self._create_result(
                HealthStatus.UNHEALTHY,
                "aiohttp library not available - install with: pip install aiohttp",
                0.0,
                url=self.url,
                error="missing_dependency",
            )

        connector = aiohttp.TCPConnector(ssl=self.verify_ssl)

        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.request(
                    self.method,
                    self.url,
                    headers=self.headers,
                    data=self.body,
                ) as response:
                    status_healthy = response.status in self.expected_status
                    response_text = await response.text()

                    # Try to parse JSON response for additional context
                    response_data = None
                    try:
                        response_data = await response.json()
                    except (aiohttp.ContentTypeError, json.JSONDecodeError):
                        pass

                    details = {
                        "url": self.url,
                        "method": self.method,
                        "status_code": response.status,
                        "expected_status": self.expected_status,
                        "response_size": len(response_text),
                        "content_type": response.headers.get("content-type", "unknown"),
                    }

                    if response_data:
                        details["response_data"] = response_data

                    if status_healthy:
                        return HealthCheckResult(
                            status=HealthStatus.HEALTHY,
                            message=f"HTTP {self.method} {self.url} returned {response.status}",
                            details=details,
                        )
                    else:
                        return HealthCheckResult(
                            status=HealthStatus.UNHEALTHY,
                            message=f"HTTP {self.method} {self.url} returned {response.status}, expected {self.expected_status}",
                            details={**details, "response_body": response_text[:1000]},
                        )

        except aiohttp.ClientError as e:
            raise GenesisError(
                f"HTTP health check failed for {self.url}: {str(e)}",
                code="HTTP_HEALTH_CHECK_FAILED",
                category=ErrorCategory.NETWORK,
                details={"url": self.url, "method": self.method},
            )


class DatabaseHealthCheck(HealthCheck):
    """
    Database connectivity health check

    Checks database connectivity and optionally validates query performance.
    Supports connection pooling and query execution validation.
    """

    def __init__(
        self,
        name: str,
        connection_string: str,
        test_query: str = "SELECT 1",
        max_query_time_ms: float = 1000,
        **kwargs,
    ):
        """
        Initialize database health check

        Args:
            name: Check name
            connection_string: Database connection string
            test_query: Query to test database connectivity
            max_query_time_ms: Maximum acceptable query time
            **kwargs: Additional HealthCheck arguments
        """
        super().__init__(name, **kwargs)
        self.connection_string = connection_string
        self.test_query = test_query
        self.max_query_time_ms = max_query_time_ms

    async def check_health(self) -> HealthCheckResult:
        """Perform database health check"""
        # Note: This is a basic implementation. In production, you'd want to
        # use specific database drivers (asyncpg for PostgreSQL, aiomysql for MySQL, etc.)
        try:
            import asyncpg  # Example for PostgreSQL

            start_time = time.time()
            conn = await asyncpg.connect(self.connection_string)

            try:
                result = await conn.fetchval(self.test_query)
                query_duration_ms = (time.time() - start_time) * 1000

                status = (
                    HealthStatus.HEALTHY
                    if query_duration_ms <= self.max_query_time_ms
                    else HealthStatus.DEGRADED
                )

                return HealthCheckResult(
                    status=status,
                    message=f"Database query executed in {query_duration_ms:.2f}ms",
                    details={
                        "query": self.test_query,
                        "query_duration_ms": round(query_duration_ms, 2),
                        "max_query_time_ms": self.max_query_time_ms,
                        "result": str(result),
                    },
                )

            finally:
                await conn.close()

        except ImportError:
            # Fallback for when specific database drivers aren't available
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message="Database health check skipped - driver not available",
                details={"reason": "asyncpg not installed"},
            )

        except Exception as e:
            raise GenesisError(
                f"Database health check failed: {str(e)}",
                code="DATABASE_HEALTH_CHECK_FAILED",
                category=ErrorCategory.INFRASTRUCTURE,
                details={"query": self.test_query},
            )


class DiskHealthCheck(HealthCheck):
    """
    Disk space health check

    Monitors disk usage and alerts when space is running low.
    Supports multiple mount points and configurable thresholds.
    """

    def __init__(
        self,
        name: str = "disk",
        path: str = "/",
        warning_threshold: float = 0.8,  # 80%
        critical_threshold: float = 0.95,  # 95%
        **kwargs,
    ):
        """
        Initialize disk health check

        Args:
            name: Check name
            path: Path to check (mount point)
            warning_threshold: Warning threshold (0.0-1.0)
            critical_threshold: Critical threshold (0.0-1.0)
            **kwargs: Additional HealthCheck arguments
        """
        super().__init__(name, **kwargs)
        self.path = path
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    async def check_health(self) -> HealthCheckResult:
        """Perform disk health check"""
        try:
            total, used, free = shutil.disk_usage(self.path)
            usage_ratio = used / total

            details = {
                "path": self.path,
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "usage_ratio": round(usage_ratio, 4),
                "usage_percent": round(usage_ratio * 100, 2),
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold,
            }

            if usage_ratio >= self.critical_threshold:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Disk usage critical: {usage_ratio:.1%} of {self.path}",
                    details=details,
                )
            elif usage_ratio >= self.warning_threshold:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message=f"Disk usage high: {usage_ratio:.1%} of {self.path}",
                    details=details,
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message=f"Disk usage normal: {usage_ratio:.1%} of {self.path}",
                    details=details,
                )

        except Exception as e:
            raise GenesisError(
                f"Disk health check failed for {self.path}: {str(e)}",
                code="DISK_HEALTH_CHECK_FAILED",
                category=ErrorCategory.INFRASTRUCTURE,
                details={"path": self.path},
            )


class MemoryHealthCheck(HealthCheck):
    """
    Memory usage health check

    Monitors system memory usage and application memory consumption.
    Provides alerts for high memory usage that could affect performance.
    """

    def __init__(
        self,
        name: str = "memory",
        warning_threshold: float = 0.8,  # 80%
        critical_threshold: float = 0.95,  # 95%
        **kwargs,
    ):
        """
        Initialize memory health check

        Args:
            name: Check name
            warning_threshold: Warning threshold (0.0-1.0)
            critical_threshold: Critical threshold (0.0-1.0)
            **kwargs: Additional HealthCheck arguments
        """
        super().__init__(name, **kwargs)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    async def check_health(self) -> HealthCheckResult:
        """Perform memory health check"""
        if psutil is None:
            return self._create_result(
                HealthStatus.UNHEALTHY,
                "psutil library not available - install with: pip install psutil",
                0.0,
                error="missing_dependency",
            )

        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()

            usage_ratio = memory.percent / 100.0

            details = {
                "system_memory": {
                    "total_bytes": memory.total,
                    "available_bytes": memory.available,
                    "used_bytes": memory.used,
                    "usage_ratio": round(usage_ratio, 4),
                    "usage_percent": round(memory.percent, 2),
                },
                "process_memory": {
                    "rss_bytes": process_memory.rss,
                    "vms_bytes": process_memory.vms,
                    "rss_mb": round(process_memory.rss / (1024 * 1024), 2),
                    "vms_mb": round(process_memory.vms / (1024 * 1024), 2),
                },
                "thresholds": {
                    "warning": self.warning_threshold,
                    "critical": self.critical_threshold,
                },
            }

            if usage_ratio >= self.critical_threshold:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Memory usage critical: {memory.percent:.1f}%",
                    details=details,
                )
            elif usage_ratio >= self.warning_threshold:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message=f"Memory usage high: {memory.percent:.1f}%",
                    details=details,
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message=f"Memory usage normal: {memory.percent:.1f}%",
                    details=details,
                )

        except Exception as e:
            raise GenesisError(
                f"Memory health check failed: {str(e)}",
                code="MEMORY_HEALTH_CHECK_FAILED",
                category=ErrorCategory.INFRASTRUCTURE,
            )


@dataclass
class HealthReport:
    """
    Comprehensive health report for a service

    Aggregates results from multiple health checks and provides
    an overall health status with detailed breakdown.
    """

    overall_status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    checks: Dict[str, HealthCheckResult] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization"""
        return {
            "status": self.overall_status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() + "Z",
            "checks": {name: result.to_dict() for name, result in self.checks.items()},
            "summary": self.summary,
            "metadata": self.metadata,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert report to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)


class HealthCheckRegistry:
    """
    Registry for managing multiple health checks

    Provides centralized health check execution, caching, and reporting.
    Supports different probe types for Kubernetes integration.
    """

    def __init__(
        self,
        service_name: str = None,
        cache_ttl_seconds: int = 30,
        parallel_execution: bool = True,
    ):
        """
        Initialize health check registry

        Args:
            service_name: Name of the service
            cache_ttl_seconds: How long to cache health check results
            parallel_execution: Whether to run checks in parallel
        """
        self.service_name = service_name or os.environ.get("GENESIS_SERVICE", "genesis")
        self.cache_ttl_seconds = cache_ttl_seconds
        self.parallel_execution = parallel_execution

        self._checks: Dict[str, HealthCheck] = {}
        self._probe_mapping: Dict[ProbeType, List[str]] = {
            ProbeType.LIVENESS: [],
            ProbeType.READINESS: [],
            ProbeType.STARTUP: [],
        }

        self._cache: Dict[str, tuple] = {}  # name -> (result, timestamp)
        self.logger = get_logger(f"HealthRegistry.{self.service_name}")

    def add_check(
        self,
        health_check: HealthCheck,
        probe_types: Optional[List[ProbeType]] = None,
    ):
        """
        Add a health check to the registry

        Args:
            health_check: HealthCheck instance
            probe_types: Which probe types this check should be included in
        """
        self._checks[health_check.name] = health_check

        # Default probe mapping
        probe_types = probe_types or [ProbeType.READINESS]

        for probe_type in probe_types:
            if health_check.name not in self._probe_mapping[probe_type]:
                self._probe_mapping[probe_type].append(health_check.name)

        self.logger.info(
            f"Added health check: {health_check.name}",
            probe_types=[pt.value for pt in probe_types],
            critical=health_check.critical,
            tags=health_check.tags,
        )

    def remove_check(self, name: str):
        """Remove a health check from the registry"""
        if name in self._checks:
            del self._checks[name]

            # Remove from probe mappings
            for probe_checks in self._probe_mapping.values():
                if name in probe_checks:
                    probe_checks.remove(name)

            # Remove from cache
            if name in self._cache:
                del self._cache[name]

            self.logger.info(f"Removed health check: {name}")

    def get_check_names(self, probe_type: Optional[ProbeType] = None) -> List[str]:
        """
        Get names of health checks

        Args:
            probe_type: Optional filter by probe type

        Returns:
            List of health check names
        """
        if probe_type is None:
            return list(self._checks.keys())

        return self._probe_mapping.get(probe_type, [])

    async def run_check(
        self,
        name: str,
        use_cache: bool = True,
    ) -> HealthCheckResult:
        """
        Run a specific health check

        Args:
            name: Name of the health check
            use_cache: Whether to use cached results

        Returns:
            HealthCheckResult

        Raises:
            GenesisError: If check doesn't exist
        """
        if name not in self._checks:
            raise GenesisError(
                f"Health check '{name}' not found",
                code="HEALTH_CHECK_NOT_FOUND",
                category=ErrorCategory.CONFIGURATION,
                details={"available_checks": list(self._checks.keys())},
            )

        # Check cache first
        if use_cache and name in self._cache:
            cached_result, cached_time = self._cache[name]
            if (
                datetime.utcnow() - cached_time
            ).total_seconds() < self.cache_ttl_seconds:
                self.logger.debug(f"Using cached result for {name}")
                return cached_result

        # Execute health check
        health_check = self._checks[name]

        try:
            result = await health_check.execute_with_timeout()

            # Cache the result
            self._cache[name] = (result, datetime.utcnow())

            self.logger.debug(
                f"Health check {name} completed",
                status=result.status.value,
                duration_ms=result.duration_ms,
            )

            return result

        except Exception as e:
            self.logger.error(f"Health check {name} failed", error=str(e))
            raise

    async def check_health(
        self,
        probe_type: Optional[ProbeType] = None,
        check_names: Optional[List[str]] = None,
    ) -> HealthReport:
        """
        Run multiple health checks and generate a report

        Args:
            probe_type: Optional filter by probe type
            check_names: Specific checks to run (overrides probe_type)

        Returns:
            HealthReport with aggregated results
        """
        if check_names is None:
            check_names = self.get_check_names(probe_type)

        if not check_names:
            return HealthReport(
                overall_status=HealthStatus.UNKNOWN,
                message="No health checks configured",
                summary={"total_checks": 0},
            )

        # Execute health checks
        if self.parallel_execution:
            tasks = [self.run_check(name) for name in check_names]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
            for name in check_names:
                try:
                    result = await self.run_check(name)
                    results.append(result)
                except Exception as e:
                    results.append(e)

        # Process results
        check_results = {}
        status_counts = {status: 0 for status in HealthStatus}
        critical_failed = False

        for i, result in enumerate(results):
            name = check_names[i]
            check = self._checks[name]

            if isinstance(result, Exception):
                # Handle execution failure
                check_result = HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check execution failed: {str(result)}",
                    details={"error": str(result), "error_type": type(result).__name__},
                )
            else:
                check_result = result

            check_results[name] = check_result
            status_counts[check_result.status] += 1

            # Track critical failures
            if check.critical and not check_result.is_healthy():
                critical_failed = True

        # Determine overall status
        overall_status = self._calculate_overall_status(status_counts, critical_failed)

        # Create summary
        summary = {
            "total_checks": len(check_names),
            "status_counts": {
                status.value: count for status, count in status_counts.items()
            },
            "critical_failed": critical_failed,
            "probe_type": probe_type.value if probe_type else None,
        }

        # Generate message
        healthy_count = status_counts[HealthStatus.HEALTHY]
        total_count = len(check_names)

        if overall_status == HealthStatus.HEALTHY:
            message = f"All {total_count} health checks passed"
        elif overall_status == HealthStatus.DEGRADED:
            message = f"{healthy_count}/{total_count} health checks passed (degraded performance)"
        else:
            message = f"{healthy_count}/{total_count} health checks passed (service unhealthy)"

        return HealthReport(
            overall_status=overall_status,
            message=message,
            checks=check_results,
            summary=summary,
            metadata={
                "service": self.service_name,
                "parallel_execution": self.parallel_execution,
                "cache_ttl_seconds": self.cache_ttl_seconds,
            },
        )

    def _calculate_overall_status(
        self, status_counts: Dict[HealthStatus, int], critical_failed: bool
    ) -> HealthStatus:
        """Calculate overall health status from individual check results"""
        # Any critical check failure means unhealthy
        if critical_failed:
            return HealthStatus.UNHEALTHY

        # If any check is unhealthy, overall is unhealthy
        if status_counts[HealthStatus.UNHEALTHY] > 0:
            return HealthStatus.UNHEALTHY

        # If any check is degraded, overall is degraded
        if status_counts[HealthStatus.DEGRADED] > 0:
            return HealthStatus.DEGRADED

        # If any check is unknown, overall is degraded
        if status_counts[HealthStatus.UNKNOWN] > 0:
            return HealthStatus.DEGRADED

        # All checks are healthy
        return HealthStatus.HEALTHY

    def clear_cache(self):
        """Clear all cached health check results"""
        self._cache.clear()
        self.logger.info("Health check cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.utcnow()
        cache_stats = {
            "total_entries": len(self._cache),
            "expired_entries": 0,
            "entries": {},
        }

        for name, (result, timestamp) in self._cache.items():
            age_seconds = (now - timestamp).total_seconds()
            is_expired = age_seconds >= self.cache_ttl_seconds

            if is_expired:
                cache_stats["expired_entries"] += 1

            cache_stats["entries"][name] = {
                "status": result.status.value,
                "age_seconds": round(age_seconds, 2),
                "expired": is_expired,
            }

        return cache_stats


class KubernetesProbeHandler:
    """
    Handler for Kubernetes probe endpoints

    Provides HTTP endpoints that Kubernetes can use for liveness,
    readiness, and startup probes.
    """

    def __init__(self, registry: HealthCheckRegistry):
        """
        Initialize probe handler

        Args:
            registry: HealthCheckRegistry instance
        """
        self.registry = registry
        self.logger = get_logger("KubernetesProbes")

    async def liveness_probe(self) -> Dict[str, Any]:
        """
        Liveness probe endpoint

        Used by Kubernetes to determine if the container should be restarted.
        Should only fail if the application is in an unrecoverable state.

        Returns:
            HTTP response data
        """
        try:
            report = await self.registry.check_health(ProbeType.LIVENESS)

            if report.overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                return {
                    "status": "ok",
                    "timestamp": report.timestamp.isoformat() + "Z",
                    "checks": len(report.checks),
                }
            else:
                return {
                    "status": "error",
                    "message": report.message,
                    "timestamp": report.timestamp.isoformat() + "Z",
                }, 503

        except Exception as e:
            self.logger.error("Liveness probe failed", error=str(e))
            return {"status": "error", "message": str(e)}, 500

    async def readiness_probe(self) -> Dict[str, Any]:
        """
        Readiness probe endpoint

        Used by Kubernetes to determine if the container is ready to receive traffic.
        Should fail if dependencies are unavailable or the service can't handle requests.

        Returns:
            HTTP response data
        """
        try:
            report = await self.registry.check_health(ProbeType.READINESS)

            if report.overall_status == HealthStatus.HEALTHY:
                return {
                    "status": "ready",
                    "timestamp": report.timestamp.isoformat() + "Z",
                    "checks": report.summary.get("status_counts", {}),
                }
            else:
                return {
                    "status": "not_ready",
                    "message": report.message,
                    "timestamp": report.timestamp.isoformat() + "Z",
                    "details": report.summary,
                }, 503

        except Exception as e:
            self.logger.error("Readiness probe failed", error=str(e))
            return {"status": "error", "message": str(e)}, 500

    async def startup_probe(self) -> Dict[str, Any]:
        """
        Startup probe endpoint

        Used by Kubernetes during container startup to determine when the application
        has finished initializing. Disables liveness/readiness checks until passed.

        Returns:
            HTTP response data
        """
        try:
            report = await self.registry.check_health(ProbeType.STARTUP)

            if report.overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                return {
                    "status": "started",
                    "timestamp": report.timestamp.isoformat() + "Z",
                    "initialization_complete": True,
                }
            else:
                return {
                    "status": "starting",
                    "message": report.message,
                    "timestamp": report.timestamp.isoformat() + "Z",
                    "initialization_complete": False,
                }, 503

        except Exception as e:
            self.logger.error("Startup probe failed", error=str(e))
            return {"status": "error", "message": str(e)}, 500

    async def health_check(self) -> Dict[str, Any]:
        """
        General health check endpoint

        Provides detailed health information for monitoring and debugging.
        Not typically used by Kubernetes but useful for operational visibility.

        Returns:
            Comprehensive health report
        """
        try:
            report = await self.registry.check_health()
            return report.to_dict()

        except Exception as e:
            self.logger.error("Health check endpoint failed", error=str(e))
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Health check failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                },
            }, 500
