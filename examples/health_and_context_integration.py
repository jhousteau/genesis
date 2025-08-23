"""
Genesis Health Check and Context Integration Example

This example demonstrates how to use the health check system and context
management together in a production microservice following CRAFT methodology.
"""

import asyncio
import time
from typing import Any, Dict

from core.context import (ContextManager, extract_headers,
                          generate_correlation_id, propagate_headers)
from core.errors.handler import GenesisError
from core.health import (DiskHealthCheck, HealthCheckRegistry, HTTPHealthCheck,
                         KubernetesProbeHandler, MemoryHealthCheck, ProbeType)
from core.logging.logger import get_logger


class ExampleMicroservice:
    """
    Example microservice demonstrating integration of health checks
    and context management with the Genesis platform.
    """

    def __init__(self):
        """Initialize the microservice with health checks and context management"""
        self.logger = get_logger("ExampleMicroservice")
        self.context_manager = ContextManager("example-service")

        # Initialize health check registry
        self.health_registry = HealthCheckRegistry(
            service_name="example-service",
            cache_ttl_seconds=30,
            parallel_execution=True,
        )

        # Set up health checks
        self._setup_health_checks()

        # Initialize Kubernetes probe handler
        self.probe_handler = KubernetesProbeHandler(self.health_registry)

        self.logger.info("Example microservice initialized")

    def _setup_health_checks(self):
        """Set up health checks for the service"""

        # HTTP health check for external API dependency
        api_check = HTTPHealthCheck(
            name="external_api",
            url="https://api.example.com/health",
            timeout_seconds=5,
            critical=True,
            description="External API dependency health check",
            tags=["external", "api", "critical"],
        )

        # Add to different probe types
        self.health_registry.add_check(
            api_check,
            probe_types=[ProbeType.READINESS],  # Only affects readiness, not liveness
        )

        # System resource checks
        disk_check = DiskHealthCheck(
            name="disk_space",
            path="/",
            warning_threshold=0.8,
            critical_threshold=0.95,
            critical=False,  # Disk space issues shouldn't kill the service
            description="System disk space monitoring",
            tags=["system", "disk", "resource"],
        )

        memory_check = MemoryHealthCheck(
            name="memory_usage",
            warning_threshold=0.85,
            critical_threshold=0.95,
            critical=False,  # Memory issues are degradation, not failure
            description="System memory usage monitoring",
            tags=["system", "memory", "resource"],
        )

        # Add resource checks to all probe types
        for check in [disk_check, memory_check]:
            self.health_registry.add_check(
                check,
                probe_types=[
                    ProbeType.LIVENESS,
                    ProbeType.READINESS,
                    ProbeType.STARTUP,
                ],
            )

        self.logger.info(
            "Health checks configured",
            total_checks=len(self.health_registry.get_check_names()),
            liveness_checks=len(
                self.health_registry.get_check_names(ProbeType.LIVENESS)
            ),
            readiness_checks=len(
                self.health_registry.get_check_names(ProbeType.READINESS)
            ),
        )

    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an incoming request with full context management

        This demonstrates the complete request lifecycle with context
        propagation and health monitoring.
        """

        # Extract context from request headers (if available)
        headers = request_data.get("headers", {})
        context_info = extract_headers(headers)

        # Set up request context
        correlation_id = context_info.get("correlation_id") or generate_correlation_id()

        async with self.context_manager.request_context(
            correlation_id=correlation_id,
            request_id=context_info.get("request_id") or correlation_id,
            user_id=request_data.get("user_id"),
            trace_id=context_info.get("trace_id"),
            span_id=context_info.get("span_id"),
            metadata={"request_type": request_data.get("type", "unknown")},
        ):
            # All logging within this context will automatically include
            # correlation_id, user_id, trace_id, etc.
            self.logger.info(
                "Processing request",
                request_type=request_data.get("type"),
                request_size=len(str(request_data)),
            )

            try:
                # Simulate business logic with trace spans
                result = await self._process_business_logic(request_data)

                self.logger.info(
                    "Request processed successfully", result_size=len(str(result))
                )

                return {
                    "success": True,
                    "result": result,
                    "correlation_id": correlation_id,
                    "headers": propagate_headers(),  # For downstream services
                }

            except Exception as e:
                self.logger.error(
                    "Request processing failed",
                    error=str(e),
                    request_type=request_data.get("type"),
                )
                raise

    async def _process_business_logic(
        self, request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process business logic with trace spans"""

        # Create trace span for validation
        with self.context_manager.trace_span("validate_request"):
            await self._validate_request(request_data)

        # Create trace span for data processing
        with self.context_manager.trace_span("process_data"):
            processed_data = await self._process_data(request_data)

        # Create trace span for external service call
        with self.context_manager.trace_span("external_service_call"):
            enriched_data = await self._call_external_service(processed_data)

        return enriched_data

    async def _validate_request(self, request_data: Dict[str, Any]):
        """Validate incoming request"""
        self.logger.debug("Validating request data")

        if not request_data.get("type"):
            raise GenesisError(
                "Request type is required",
                code="VALIDATION_ERROR",
                details={"field": "type"},
            )

        # Simulate validation time
        await asyncio.sleep(0.01)
        self.logger.debug("Request validation completed")

    async def _process_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process request data"""
        self.logger.debug("Processing request data")

        # Simulate processing time
        await asyncio.sleep(0.05)

        processed = {
            "original": request_data,
            "processed_at": time.time(),
            "processing_version": "1.0.0",
        }

        self.logger.debug("Data processing completed")
        return processed

    async def _call_external_service(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call external service with context propagation"""
        self.logger.debug("Calling external service")

        # Get headers for context propagation
        headers = propagate_headers()
        self.logger.debug("Propagating context headers", header_count=len(headers))

        # Simulate external service call
        await asyncio.sleep(0.1)

        # Simulate external service response
        enriched = {
            **data,
            "external_data": {
                "service": "external-api",
                "version": "2.1.0",
                "timestamp": time.time(),
            },
        }

        self.logger.debug("External service call completed")
        return enriched

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        try:
            report = await self.health_registry.check_health()
            return report.to_dict()
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e), "timestamp": time.time()}

    async def get_liveness_probe(self) -> tuple[Dict[str, Any], int]:
        """Kubernetes liveness probe endpoint"""
        try:
            result = await self.probe_handler.liveness_probe()
            if isinstance(result, tuple):
                return result
            return result, 200
        except Exception as e:
            self.logger.error("Liveness probe failed", error=str(e))
            return {"status": "error", "message": str(e)}, 500

    async def get_readiness_probe(self) -> tuple[Dict[str, Any], int]:
        """Kubernetes readiness probe endpoint"""
        try:
            result = await self.probe_handler.readiness_probe()
            if isinstance(result, tuple):
                return result
            return result, 200
        except Exception as e:
            self.logger.error("Readiness probe failed", error=str(e))
            return {"status": "error", "message": str(e)}, 500

    async def get_startup_probe(self) -> tuple[Dict[str, Any], int]:
        """Kubernetes startup probe endpoint"""
        try:
            result = await self.probe_handler.startup_probe()
            if isinstance(result, tuple):
                return result
            return result, 200
        except Exception as e:
            self.logger.error("Startup probe failed", error=str(e))
            return {"status": "error", "message": str(e)}, 500


async def run_example():
    """Run example demonstrating the integration"""

    # Initialize the microservice
    service = ExampleMicroservice()

    print("=== Genesis Health Check and Context Integration Example ===\n")

    # 1. Check initial health status
    print("1. Initial Health Check:")
    health_status = await service.get_health_status()
    print(f"   Overall Status: {health_status.get('status')}")
    print(f"   Total Checks: {health_status.get('summary', {}).get('total_checks', 0)}")
    print(f"   Message: {health_status.get('message', 'N/A')}")

    # 2. Test Kubernetes probes
    print("\n2. Kubernetes Probes:")

    liveness_result, liveness_code = await service.get_liveness_probe()
    print(f"   Liveness: {liveness_result.get('status')} (HTTP {liveness_code})")

    readiness_result, readiness_code = await service.get_readiness_probe()
    print(f"   Readiness: {readiness_result.get('status')} (HTTP {readiness_code})")

    startup_result, startup_code = await service.get_startup_probe()
    print(f"   Startup: {startup_result.get('status')} (HTTP {startup_code})")

    # 3. Process requests with context propagation
    print("\n3. Request Processing with Context:")

    # Simulate incoming request with headers
    incoming_request = {
        "type": "user_data_request",
        "user_id": "user_12345",
        "data": {"query": "get_profile"},
        "headers": {
            "X-Correlation-ID": "req_example_001",
            "X-User-ID": "user_12345",
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        },
    }

    try:
        result = await service.handle_request(incoming_request)
        print(f"   Request successful: {result.get('success')}")
        print(f"   Correlation ID: {result.get('correlation_id')}")
        print(f"   Response headers: {len(result.get('headers', {}))} headers")

    except Exception as e:
        print(f"   Request failed: {e}")

    # 4. Test health check caching
    print("\n4. Health Check Caching:")

    start_time = time.time()
    await service.get_health_status()  # First call - will execute checks
    first_duration = time.time() - start_time

    start_time = time.time()
    await service.get_health_status()  # Second call - should use cache
    second_duration = time.time() - start_time

    print(f"   First call: {first_duration:.3f}s")
    print(f"   Cached call: {second_duration:.3f}s")
    print(f"   Cache speedup: {first_duration / second_duration:.1f}x")

    # 5. Show cache statistics
    cache_stats = service.health_registry.get_cache_stats()
    print(f"   Cache entries: {cache_stats.get('total_entries', 0)}")

    print("\n=== Example completed successfully ===")


if __name__ == "__main__":
    asyncio.run(run_example())
