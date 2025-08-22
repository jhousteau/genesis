"""
Genesis Lifecycle Management Integration Example

Demonstrates comprehensive integration with existing Genesis systems:
- Logging integration with structured logging
- Error handling integration
- Health check integration with monitoring
- Kubernetes/container compatibility
- Cloud-native deployment patterns

This example shows how to use the lifecycle management system
in a real Genesis service implementation.
"""

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict

# Genesis core imports
from ..errors.handler import GenesisError, get_error_handler
from ..logging.logger import get_logger
from . import StartupPhase, create_kubernetes_probes, get_lifecycle_manager


class GenesisServiceExample:
    """
    Example Genesis service with comprehensive lifecycle management

    Demonstrates integration with:
    - Structured logging
    - Error handling
    - Health checks
    - Monitoring integration
    - Cloud-native patterns
    """

    def __init__(self, service_name: str = "example-service"):
        self.service_name = service_name
        self.logger = get_logger(f"{__name__}.{service_name}")
        self.error_handler = get_error_handler()

        # Initialize lifecycle manager
        self.lifecycle = get_lifecycle_manager(
            service_name=service_name,
            version=os.environ.get("SERVICE_VERSION", "1.0.0"),
            environment=os.environ.get("GENESIS_ENV", "development"),
            enable_health_checks=True,
            enable_metrics=True,
            startup_timeout=180,
            shutdown_timeout=60,
            health_check_interval=30,
        )

        # Service state
        self.database_connection = None
        self.cache_connection = None
        self.message_queue = None
        self.background_tasks = []

        # Setup lifecycle hooks and dependencies
        self._setup_lifecycle_hooks()
        self._setup_dependencies()
        self._setup_health_checks()

        self.logger.info(
            f"Genesis service '{service_name}' initialized with lifecycle management"
        )

    def _setup_lifecycle_hooks(self):
        """Setup service-specific lifecycle hooks"""

        # Startup hooks
        self.lifecycle.register_startup_hook(
            name="initialize_database",
            callback=self._initialize_database,
            phase=StartupPhase.INITIALIZE_STORAGE,
            timeout=60,
            critical=True,
            description="Initialize database connections and schemas",
        )

        self.lifecycle.register_startup_hook(
            name="initialize_cache",
            callback=self._initialize_cache,
            phase=StartupPhase.INITIALIZE_STORAGE,
            timeout=30,
            critical=False,  # Service can run without cache
            description="Initialize Redis cache connection",
        )

        self.lifecycle.register_startup_hook(
            name="start_background_tasks",
            callback=self._start_background_tasks,
            phase=StartupPhase.INITIALIZE_SERVICES,
            timeout=30,
            critical=True,
            description="Start background processing tasks",
        )

        # Shutdown hooks
        self.lifecycle.register_shutdown_hook(
            name="stop_background_tasks",
            callback=self._stop_background_tasks,
            phase=200,  # Stop accepting new work
            timeout=30,
            description="Stop background processing tasks",
        )

        self.lifecycle.register_shutdown_hook(
            name="close_database",
            callback=self._close_database,
            phase=400,  # Cleanup resources
            timeout=15,
            description="Close database connections",
        )

        self.lifecycle.register_shutdown_hook(
            name="close_cache",
            callback=self._close_cache,
            phase=400,  # Cleanup resources
            timeout=10,
            description="Close cache connections",
        )

    def _setup_dependencies(self):
        """Setup external dependency checks"""

        # Database dependency
        self.lifecycle.register_dependency(
            name="database",
            check_function=self._check_database_dependency,
            dependency_type="critical",
            timeout=30,
            retry_attempts=3,
            retry_delay=5,
            description="PostgreSQL database connectivity",
        )

        # Cache dependency (optional)
        self.lifecycle.register_dependency(
            name="cache",
            check_function=self._check_cache_dependency,
            dependency_type="optional",
            timeout=15,
            retry_attempts=2,
            retry_delay=3,
            description="Redis cache connectivity",
        )

        # External API dependency
        self.lifecycle.register_dependency(
            name="external_api",
            check_function=self._check_external_api_dependency,
            dependency_type="required",
            timeout=20,
            retry_attempts=3,
            retry_delay=5,
            description="External service API connectivity",
        )

    def _setup_health_checks(self):
        """Setup service health checks"""

        # Application health check
        self.lifecycle.register_health_check(
            name="application", check_function=self._check_application_health
        )

        # Database health check
        self.lifecycle.register_health_check(
            name="database", check_function=self._check_database_health
        )

        # Cache health check
        self.lifecycle.register_health_check(
            name="cache", check_function=self._check_cache_health
        )

        # Background tasks health check
        self.lifecycle.register_health_check(
            name="background_tasks", check_function=self._check_background_tasks_health
        )

    # Startup hook implementations
    def _initialize_database(self):
        """Initialize database connections"""
        self.logger.info("Initializing database connections")

        try:
            # Simulate database initialization
            time.sleep(2)  # Simulate connection time

            # In real implementation:
            # self.database_connection = create_database_connection()
            # run_migrations()
            # validate_schema()

            self.database_connection = "mock_database_connection"
            self.logger.info("Database initialized successfully")

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise GenesisError(
                "Failed to initialize database", code="DATABASE_INIT_FAILED", cause=e
            )

    def _initialize_cache(self):
        """Initialize cache connections"""
        self.logger.info("Initializing cache connections")

        try:
            # Simulate cache initialization
            time.sleep(1)

            # In real implementation:
            # self.cache_connection = create_redis_connection()
            # test_cache_connectivity()

            self.cache_connection = "mock_cache_connection"
            self.logger.info("Cache initialized successfully")

        except Exception as e:
            self.logger.warning(f"Cache initialization failed (non-critical): {e}")
            # Don't raise error for non-critical cache

    def _start_background_tasks(self):
        """Start background processing tasks"""
        self.logger.info("Starting background tasks")

        try:
            # Simulate starting background tasks
            # In real implementation:
            # self.background_tasks = [
            #     start_metric_collection_task(),
            #     start_cleanup_task(),
            #     start_health_monitoring_task()
            # ]

            self.background_tasks = ["task1", "task2", "task3"]
            self.logger.info(f"Started {len(self.background_tasks)} background tasks")

        except Exception as e:
            self.logger.error(f"Background task startup failed: {e}")
            raise GenesisError(
                "Failed to start background tasks",
                code="BACKGROUND_TASKS_FAILED",
                cause=e,
            )

    # Shutdown hook implementations
    def _stop_background_tasks(self):
        """Stop background processing tasks"""
        self.logger.info("Stopping background tasks")

        try:
            # Simulate stopping tasks gracefully
            for task in self.background_tasks:
                # In real implementation: task.cancel() or task.stop()
                self.logger.debug(f"Stopping task: {task}")

            self.background_tasks = []
            self.logger.info("Background tasks stopped successfully")

        except Exception as e:
            self.logger.error(f"Error stopping background tasks: {e}")

    def _close_database(self):
        """Close database connections"""
        self.logger.info("Closing database connections")

        try:
            if self.database_connection:
                # In real implementation: self.database_connection.close()
                self.database_connection = None
                self.logger.info("Database connections closed")

        except Exception as e:
            self.logger.error(f"Error closing database: {e}")

    def _close_cache(self):
        """Close cache connections"""
        self.logger.info("Closing cache connections")

        try:
            if self.cache_connection:
                # In real implementation: self.cache_connection.close()
                self.cache_connection = None
                self.logger.info("Cache connections closed")

        except Exception as e:
            self.logger.error(f"Error closing cache: {e}")

    # Dependency check implementations
    def _check_database_dependency(self) -> bool:
        """Check database connectivity"""
        try:
            # In real implementation: test_database_connection()
            return True
        except Exception:
            return False

    def _check_cache_dependency(self) -> bool:
        """Check cache connectivity"""
        try:
            # In real implementation: test_cache_connection()
            return True
        except Exception:
            return False

    def _check_external_api_dependency(self) -> bool:
        """Check external API connectivity"""
        try:
            # In real implementation: make_test_api_call()
            return True
        except Exception:
            return False

    # Health check implementations
    def _check_application_health(self) -> bool:
        """Check overall application health"""
        return self.lifecycle.is_ready() and len(self.background_tasks) > 0

    def _check_database_health(self) -> bool:
        """Check database health"""
        try:
            # In real implementation: execute_health_check_query()
            return self.database_connection is not None
        except Exception:
            return False

    def _check_cache_health(self) -> bool:
        """Check cache health"""
        try:
            # In real implementation: execute_cache_ping()
            return self.cache_connection is not None
        except Exception:
            return False

    def _check_background_tasks_health(self) -> bool:
        """Check background tasks health"""
        # Check if expected number of tasks are running
        return len(self.background_tasks) >= 3

    async def start(self) -> bool:
        """Start the service"""
        return await self.lifecycle.start()

    def stop(self):
        """Stop the service"""
        self.lifecycle.stop()

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive service status"""
        status = self.lifecycle.get_status()

        # Add service-specific status
        status.update(
            {
                "database_connected": self.database_connection is not None,
                "cache_connected": self.cache_connection is not None,
                "background_tasks_count": len(self.background_tasks),
                "service_specific_metrics": {
                    "connections": {
                        "database": bool(self.database_connection),
                        "cache": bool(self.cache_connection),
                    },
                    "tasks": {"background_tasks": len(self.background_tasks)},
                },
            }
        )

        return status


# Kubernetes/Container Integration Example
def create_web_server_with_lifecycle():
    """
    Example of integrating lifecycle management with a web server
    for Kubernetes deployment
    """
    import json
    from http.server import BaseHTTPRequestHandler, HTTPServer

    # Initialize service
    service = GenesisServiceExample("web-service")

    # Create Kubernetes probes
    probes = create_kubernetes_probes(service.lifecycle)

    class HealthHandler(BaseHTTPRequestHandler):
        """HTTP handler for health check endpoints"""

        def do_GET(self):
            if self.path == "/health/startup":
                # Kubernetes startup probe
                healthy = probes["startup"]()
                self._send_health_response(healthy, "startup")

            elif self.path == "/health/readiness":
                # Kubernetes readiness probe
                healthy = probes["readiness"]()
                self._send_health_response(healthy, "readiness")

            elif self.path == "/health/liveness":
                # Kubernetes liveness probe
                healthy = probes["liveness"]()
                self._send_health_response(healthy, "liveness")

            elif self.path == "/status":
                # Detailed status endpoint
                status = service.get_status()
                self._send_json_response(status)

            else:
                self.send_error(404)

        def _send_health_response(self, healthy: bool, probe_type: str):
            """Send health check response"""
            status_code = 200 if healthy else 503
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = {
                "status": "healthy" if healthy else "unhealthy",
                "probe": probe_type,
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.wfile.write(json.dumps(response).encode())

        def _send_json_response(self, data: Dict[str, Any]):
            """Send JSON response"""
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode())

        def log_message(self, format, *args):
            # Suppress default logging to use Genesis logger
            pass

    return service, HTTPServer, HealthHandler


# Example usage and integration patterns
async def main():
    """Example main function showing lifecycle management usage"""

    # Initialize service with lifecycle management
    service = GenesisServiceExample("example-service")

    try:
        # Start the service
        print("Starting Genesis service with lifecycle management...")
        success = await service.start()

        if success:
            print("Service started successfully!")
            print("Service is ready:", service.lifecycle.is_ready())
            print("Service is healthy:", service.lifecycle.is_healthy())

            # Print comprehensive status
            status = service.get_status()
            print("\nService Status:")
            print(json.dumps(status, indent=2, default=str))

            # Wait for shutdown signal (in real implementation)
            print("\nService running... (send SIGTERM or SIGINT to stop)")
            service.lifecycle.wait_for_shutdown()

        else:
            print("Service startup failed!")
            return 1

    except KeyboardInterrupt:
        print("\nReceived interrupt signal, shutting down...")
    except Exception as e:
        print(f"Service error: {e}")
        return 1
    finally:
        # Graceful shutdown
        service.stop()
        print("Service stopped")

    return 0


if __name__ == "__main__":
    import json
    import sys

    # Run the example
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
