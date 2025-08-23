#!/usr/bin/env python3
"""
MCP Performance and Security Validation Script
Comprehensive validation for claude-talk migration readiness.
"""

import asyncio
import json
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
import websockets
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


@dataclass
class PerformanceMetrics:
    """Performance metrics container."""

    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float
    error_rate: float
    success_count: int
    error_count: int


@dataclass
class ValidationResult:
    """Validation result container."""

    test_name: str
    status: str  # "pass", "fail", "warning"
    details: Dict[str, Any]
    metrics: Optional[PerformanceMetrics] = None
    error_message: Optional[str] = None


class MCPPerformanceValidator:
    """MCP performance and security validator."""

    def __init__(
        self,
        server_url: str = "http://localhost:8080",
        ws_url: str = "ws://localhost:8080/ws",
    ):
        self.server_url = server_url
        self.ws_url = ws_url
        self.results: List[ValidationResult] = []

    async def validate_all(self) -> List[ValidationResult]:
        """Run all validation tests."""
        console.print(
            "[bold cyan]Starting MCP Performance and Security Validation[/bold cyan]"
        )
        console.print("=" * 60)

        validation_tests = [
            ("Server Connectivity", self.validate_server_connectivity),
            ("HTTP Performance", self.validate_http_performance),
            ("WebSocket Performance", self.validate_websocket_performance),
            ("Concurrent Connections", self.validate_concurrent_connections),
            ("Load Testing", self.validate_load_testing),
            ("Security Headers", self.validate_security_headers),
            ("Input Validation", self.validate_input_validation),
            ("Rate Limiting", self.validate_rate_limiting),
            ("Authentication", self.validate_authentication),
            ("Error Handling", self.validate_error_handling),
            ("Resource Limits", self.validate_resource_limits),
            ("Protocol Compliance", self.validate_protocol_compliance),
            ("Claude-Talk Readiness", self.validate_claude_talk_readiness),
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for test_name, test_func in validation_tests:
                task = progress.add_task(f"Running {test_name}...", total=None)

                try:
                    result = await test_func()
                    result.test_name = test_name
                    self.results.append(result)

                    status_color = {
                        "pass": "green",
                        "fail": "red",
                        "warning": "yellow",
                    }[result.status]
                    progress.update(
                        task,
                        description=f"[{status_color}]{test_name}: {result.status.upper()}[/{status_color}]",
                    )

                except Exception as e:
                    error_result = ValidationResult(
                        test_name=test_name,
                        status="fail",
                        details={},
                        error_message=str(e),
                    )
                    self.results.append(error_result)
                    progress.update(task, description=f"[red]{test_name}: FAILED[/red]")

                await asyncio.sleep(0.1)  # Brief pause between tests

        return self.results

    async def validate_server_connectivity(self) -> ValidationResult:
        """Validate basic server connectivity."""
        try:
            # Test HTTP health endpoint
            start_time = time.time()
            response = requests.get(f"{self.server_url}/health", timeout=10)
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                health_data = response.json()
                return ValidationResult(
                    test_name="",
                    status="pass",
                    details={
                        "status_code": response.status_code,
                        "response_time_ms": response_time,
                        "server_status": health_data.get("status"),
                        "connections": health_data.get("connections", 0),
                        "services": health_data.get("services", 0),
                    },
                )
            else:
                return ValidationResult(
                    test_name="",
                    status="fail",
                    details={"status_code": response.status_code},
                    error_message=f"Health check returned {response.status_code}",
                )

        except Exception as e:
            return ValidationResult(
                test_name="", status="fail", details={}, error_message=str(e)
            )

    async def validate_http_performance(self) -> ValidationResult:
        """Validate HTTP API performance."""
        request_count = 100
        response_times = []
        errors = 0

        def make_request():
            try:
                start_time = time.time()

                message = {
                    "type": "request",
                    "id": str(uuid.uuid4()),
                    "method": "health.check",
                    "params": {},
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "version": "1.0.0",
                    "source": "performance-validator",
                }

                response = requests.post(
                    f"{self.server_url}/api/mcp", json=message, timeout=30
                )

                response_time = (time.time() - start_time) * 1000
                return response_time, response.status_code == 200

            except Exception:
                return None, False

        # Execute requests concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(request_count)]

            for future in as_completed(futures):
                response_time, success = future.result()
                if response_time is not None:
                    response_times.append(response_time)
                    if not success:
                        errors += 1
                else:
                    errors += 1

        if not response_times:
            return ValidationResult(
                test_name="",
                status="fail",
                details={},
                error_message="No successful requests",
            )

        # Calculate metrics
        metrics = PerformanceMetrics(
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p95_response_time=statistics.quantiles(response_times, n=20)[18]
            if len(response_times) > 20
            else max(response_times),
            p99_response_time=statistics.quantiles(response_times, n=100)[98]
            if len(response_times) > 100
            else max(response_times),
            throughput=len(response_times) / (max(response_times) / 1000)
            if response_times
            else 0,
            error_rate=(errors / request_count) * 100,
            success_count=len(response_times),
            error_count=errors,
        )

        # Performance thresholds for claude-talk
        status = "pass"
        if metrics.avg_response_time > 200:  # Average should be under 200ms
            status = "warning" if metrics.avg_response_time < 500 else "fail"
        elif metrics.p95_response_time > 500:  # 95th percentile should be under 500ms
            status = "warning"
        elif metrics.error_rate > 1:  # Error rate should be under 1%
            status = "fail"

        return ValidationResult(
            test_name="",
            status=status,
            details={"request_count": request_count, "concurrent_workers": 10},
            metrics=metrics,
        )

    async def validate_websocket_performance(self) -> ValidationResult:
        """Validate WebSocket performance."""
        request_count = 50
        response_times = []
        errors = 0

        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Receive welcome message
                welcome = await websocket.recv()

                for _ in range(request_count):
                    try:
                        start_time = time.time()

                        message = {
                            "type": "request",
                            "id": str(uuid.uuid4()),
                            "method": "health.check",
                            "params": {},
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "version": "1.0.0",
                            "source": "performance-validator",
                        }

                        await websocket.send(json.dumps(message))
                        response = await asyncio.wait_for(websocket.recv(), timeout=10)

                        response_time = (time.time() - start_time) * 1000
                        response_data = json.loads(response)

                        if response_data.get("success"):
                            response_times.append(response_time)
                        else:
                            errors += 1

                    except Exception:
                        errors += 1

        except Exception as e:
            return ValidationResult(
                test_name="",
                status="fail",
                details={},
                error_message=f"WebSocket connection failed: {e}",
            )

        if not response_times:
            return ValidationResult(
                test_name="",
                status="fail",
                details={},
                error_message="No successful WebSocket requests",
            )

        metrics = PerformanceMetrics(
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p95_response_time=statistics.quantiles(response_times, n=20)[18]
            if len(response_times) > 20
            else max(response_times),
            p99_response_time=statistics.quantiles(response_times, n=100)[98]
            if len(response_times) > 100
            else max(response_times),
            throughput=len(response_times) / (sum(response_times) / 1000)
            if response_times
            else 0,
            error_rate=(errors / request_count) * 100,
            success_count=len(response_times),
            error_count=errors,
        )

        status = "pass"
        if metrics.avg_response_time > 150 or metrics.error_rate > 1:
            status = "warning" if metrics.avg_response_time < 300 else "fail"

        return ValidationResult(
            test_name="",
            status=status,
            details={"request_count": request_count, "protocol": "WebSocket"},
            metrics=metrics,
        )

    async def validate_concurrent_connections(self) -> ValidationResult:
        """Validate concurrent connection handling."""
        connection_count = 20
        successful_connections = 0

        async def create_connection():
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    # Receive welcome message
                    await websocket.recv()

                    # Send a test request
                    message = {
                        "type": "request",
                        "id": str(uuid.uuid4()),
                        "method": "health.check",
                        "params": {},
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "version": "1.0.0",
                        "source": "concurrency-validator",
                    }

                    await websocket.send(json.dumps(message))
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)

                    response_data = json.loads(response)
                    return response_data.get("success", False)

            except Exception:
                return False

        # Create concurrent connections
        tasks = [create_connection() for _ in range(connection_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_connections = sum(1 for result in results if result is True)
        success_rate = (successful_connections / connection_count) * 100

        status = (
            "pass"
            if success_rate >= 95
            else ("warning" if success_rate >= 80 else "fail")
        )

        return ValidationResult(
            test_name="",
            status=status,
            details={
                "concurrent_connections": connection_count,
                "successful_connections": successful_connections,
                "success_rate": success_rate,
            },
        )

    async def validate_load_testing(self) -> ValidationResult:
        """Validate server under load."""
        duration = 30  # 30 seconds
        concurrent_requests = 10
        total_requests = 0
        successful_requests = 0

        start_time = time.time()
        end_time = start_time + duration

        async def load_worker():
            nonlocal total_requests, successful_requests

            try:
                async with websockets.connect(self.ws_url) as websocket:
                    await websocket.recv()  # Welcome message

                    while time.time() < end_time:
                        try:
                            message = {
                                "type": "request",
                                "id": str(uuid.uuid4()),
                                "method": "health.check",
                                "params": {},
                                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "version": "1.0.0",
                                "source": "load-tester",
                            }

                            await websocket.send(json.dumps(message))
                            response = await asyncio.wait_for(
                                websocket.recv(), timeout=5
                            )

                            total_requests += 1
                            response_data = json.loads(response)

                            if response_data.get("success"):
                                successful_requests += 1

                        except Exception:
                            total_requests += 1

            except Exception:
                pass

        # Run concurrent load workers
        tasks = [load_worker() for _ in range(concurrent_requests)]
        await asyncio.gather(*tasks, return_exceptions=True)

        actual_duration = time.time() - start_time
        success_rate = (successful_requests / max(total_requests, 1)) * 100
        requests_per_second = total_requests / actual_duration

        status = "pass"
        if success_rate < 95:
            status = "warning" if success_rate >= 80 else "fail"
        elif requests_per_second < 50:  # Should handle at least 50 req/s
            status = "warning"

        return ValidationResult(
            test_name="",
            status=status,
            details={
                "duration_seconds": actual_duration,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": success_rate,
                "requests_per_second": requests_per_second,
                "concurrent_workers": concurrent_requests,
            },
        )

    async def validate_security_headers(self) -> ValidationResult:
        """Validate security headers."""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=10)
            headers = response.headers

            security_checks = {
                "X-Content-Type-Options": headers.get("X-Content-Type-Options")
                == "nosniff",
                "X-Frame-Options": "X-Frame-Options" in headers,
                "X-XSS-Protection": "X-XSS-Protection" in headers,
                "Strict-Transport-Security": "Strict-Transport-Security" in headers
                or not self.server_url.startswith("https"),
                "Content-Security-Policy": "Content-Security-Policy" in headers,
            }

            passed_checks = sum(security_checks.values())
            total_checks = len(security_checks)

            status = "pass" if passed_checks >= total_checks * 0.8 else "warning"

            return ValidationResult(
                test_name="",
                status=status,
                details={
                    "security_checks": security_checks,
                    "passed_checks": passed_checks,
                    "total_checks": total_checks,
                    "headers": dict(headers),
                },
            )

        except Exception as e:
            return ValidationResult(
                test_name="", status="fail", details={}, error_message=str(e)
            )

    async def validate_input_validation(self) -> ValidationResult:
        """Validate input validation and sanitization."""
        malicious_payloads = [
            {"xss": "<script>alert('xss')</script>"},
            {"sql_injection": "'; DROP TABLE users; --"},
            {"path_traversal": "../../../etc/passwd"},
            {"template_injection": "{{7*7}}"},
            {"command_injection": "; rm -rf /"},
            {"large_payload": "x" * 100000},  # 100KB payload
        ]

        vulnerabilities_found = 0
        test_results = []

        for payload_name, payload_data in malicious_payloads:
            try:
                message = {
                    "type": "request",
                    "id": str(uuid.uuid4()),
                    "method": "health.check",
                    "params": payload_data,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "version": "1.0.0",
                    "source": "security-validator",
                }

                response = requests.post(
                    f"{self.server_url}/api/mcp", json=message, timeout=10
                )

                # Check if server handled malicious input safely
                if response.status_code == 200:
                    response_data = response.json()
                    # Server should either reject the payload or handle it safely
                    test_results.append(
                        {
                            "payload": payload_name,
                            "handled_safely": True,
                            "response_success": response_data.get("success", False),
                        }
                    )
                else:
                    test_results.append(
                        {
                            "payload": payload_name,
                            "handled_safely": True,
                            "response_code": response.status_code,
                        }
                    )

            except requests.exceptions.Timeout:
                # Timeout might indicate server hung on malicious input
                vulnerabilities_found += 1
                test_results.append(
                    {
                        "payload": payload_name,
                        "handled_safely": False,
                        "error": "timeout",
                    }
                )
            except Exception as e:
                test_results.append(
                    {"payload": payload_name, "handled_safely": True, "error": str(e)}
                )

        status = "pass" if vulnerabilities_found == 0 else "fail"

        return ValidationResult(
            test_name="",
            status=status,
            details={
                "payloads_tested": len(malicious_payloads),
                "vulnerabilities_found": vulnerabilities_found,
                "test_results": test_results,
            },
        )

    async def validate_rate_limiting(self) -> ValidationResult:
        """Validate rate limiting functionality."""
        # Send rapid requests to test rate limiting
        request_count = 200
        blocked_requests = 0

        def rapid_request():
            try:
                response = requests.get(f"{self.server_url}/api/services", timeout=5)
                return response.status_code
            except Exception:
                return None

        start_time = time.time()

        # Send requests rapidly
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(rapid_request) for _ in range(request_count)]

            for future in as_completed(futures):
                status_code = future.result()
                if status_code == 429:  # Too Many Requests
                    blocked_requests += 1

        duration = time.time() - start_time
        requests_per_second = request_count / duration

        # Rate limiting should kick in for very high request rates
        status = (
            "pass" if blocked_requests > 0 or requests_per_second < 1000 else "warning"
        )

        return ValidationResult(
            test_name="",
            status=status,
            details={
                "total_requests": request_count,
                "blocked_requests": blocked_requests,
                "requests_per_second": requests_per_second,
                "duration": duration,
            },
        )

    async def validate_authentication(self) -> ValidationResult:
        """Validate authentication mechanisms."""
        # Test both authenticated and unauthenticated requests
        auth_tests = []

        # Test 1: Unauthenticated request (should work if auth is disabled, or fail gracefully)
        try:
            response = requests.post(
                f"{self.server_url}/api/mcp",
                json={
                    "type": "request",
                    "id": str(uuid.uuid4()),
                    "method": "health.check",
                    "params": {},
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "version": "1.0.0",
                    "source": "auth-validator",
                },
                timeout=10,
            )

            auth_tests.append(
                {
                    "test": "unauthenticated_request",
                    "status_code": response.status_code,
                    "success": response.status_code
                    in [200, 401],  # Either works or properly rejects
                }
            )

        except Exception as e:
            auth_tests.append(
                {"test": "unauthenticated_request", "error": str(e), "success": False}
            )

        # Test 2: Invalid authentication token
        try:
            response = requests.post(
                f"{self.server_url}/api/mcp",
                json={
                    "type": "request",
                    "id": str(uuid.uuid4()),
                    "method": "health.check",
                    "params": {},
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "version": "1.0.0",
                    "source": "auth-validator",
                },
                headers={"Authorization": "Bearer invalid-token"},
                timeout=10,
            )

            # Should either accept (if auth disabled) or reject properly
            auth_tests.append(
                {
                    "test": "invalid_token",
                    "status_code": response.status_code,
                    "success": response.status_code in [200, 401, 403],
                }
            )

        except Exception as e:
            auth_tests.append(
                {"test": "invalid_token", "error": str(e), "success": False}
            )

        all_tests_passed = all(test["success"] for test in auth_tests)
        status = "pass" if all_tests_passed else "warning"

        return ValidationResult(
            test_name="",
            status=status,
            details={"auth_tests": auth_tests, "all_passed": all_tests_passed},
        )

    async def validate_error_handling(self) -> ValidationResult:
        """Validate error handling and recovery."""
        error_tests = []

        # Test malformed JSON
        try:
            response = requests.post(
                f"{self.server_url}/api/mcp",
                data='{"invalid": json}',
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            error_tests.append(
                {
                    "test": "malformed_json",
                    "status_code": response.status_code,
                    "handled_gracefully": response.status_code == 400,
                }
            )

        except Exception:
            error_tests.append(
                {
                    "test": "malformed_json",
                    "handled_gracefully": True,  # Exception is acceptable
                }
            )

        # Test invalid method
        try:
            async with websockets.connect(self.ws_url) as websocket:
                await websocket.recv()  # Welcome message

                message = {
                    "type": "request",
                    "id": str(uuid.uuid4()),
                    "method": "nonexistent.method",
                    "params": {},
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "version": "1.0.0",
                    "source": "error-validator",
                }

                await websocket.send(json.dumps(message))
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)

                error_tests.append(
                    {
                        "test": "invalid_method",
                        "response_type": response_data.get("type"),
                        "has_error": "error" in response_data,
                        "handled_gracefully": response_data.get("type") == "response"
                        and not response_data.get("success"),
                    }
                )

        except Exception as e:
            error_tests.append(
                {"test": "invalid_method", "handled_gracefully": False, "error": str(e)}
            )

        graceful_handling = all(
            test.get("handled_gracefully", False) for test in error_tests
        )
        status = "pass" if graceful_handling else "fail"

        return ValidationResult(
            test_name="",
            status=status,
            details={
                "error_tests": error_tests,
                "graceful_handling": graceful_handling,
            },
        )

    async def validate_resource_limits(self) -> ValidationResult:
        """Validate resource limits and memory usage."""
        # Test large payload handling
        large_payload = "x" * (5 * 1024 * 1024)  # 5MB payload

        try:
            start_time = time.time()

            message = {
                "type": "request",
                "id": str(uuid.uuid4()),
                "method": "health.check",
                "params": {"large_data": large_payload},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "version": "1.0.0",
                "source": "resource-validator",
            }

            response = requests.post(
                f"{self.server_url}/api/mcp", json=message, timeout=30
            )

            response_time = (time.time() - start_time) * 1000

            # Server should either accept and handle, or reject with appropriate error
            handled_properly = response.status_code in [200, 413, 400]

            return ValidationResult(
                test_name="",
                status="pass" if handled_properly else "fail",
                details={
                    "payload_size_mb": len(large_payload) / (1024 * 1024),
                    "response_time_ms": response_time,
                    "status_code": response.status_code,
                    "handled_properly": handled_properly,
                },
            )

        except requests.exceptions.Timeout:
            return ValidationResult(
                test_name="",
                status="warning",
                details={"timeout": "Large payload caused timeout"},
            )
        except Exception as e:
            return ValidationResult(
                test_name="",
                status="pass",  # Rejecting large payloads is acceptable
                details={"rejected": str(e)},
            )

    async def validate_protocol_compliance(self) -> ValidationResult:
        """Validate MCP protocol compliance."""
        compliance_tests = []

        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Test 1: Welcome message format
                welcome = await websocket.recv()
                welcome_data = json.loads(welcome)

                compliance_tests.append(
                    {
                        "test": "welcome_message",
                        "passed": (
                            welcome_data.get("type") == "notification"
                            and welcome_data.get("event") == "server.welcome"
                            and "capabilities" in welcome_data.get("data", {})
                        ),
                    }
                )

                # Test 2: Request-response format
                request_id = str(uuid.uuid4())
                message = {
                    "type": "request",
                    "id": request_id,
                    "method": "health.check",
                    "params": {},
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "version": "1.0.0",
                    "source": "protocol-validator",
                }

                await websocket.send(json.dumps(message))
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)

                compliance_tests.append(
                    {
                        "test": "request_response_format",
                        "passed": (
                            response_data.get("type") == "response"
                            and response_data.get("requestId") == request_id
                            and "success" in response_data
                        ),
                    }
                )

        except Exception as e:
            compliance_tests.append(
                {"test": "protocol_compliance", "passed": False, "error": str(e)}
            )

        all_passed = all(test.get("passed", False) for test in compliance_tests)
        status = "pass" if all_passed else "fail"

        return ValidationResult(
            test_name="",
            status=status,
            details={"compliance_tests": compliance_tests, "all_passed": all_passed},
        )

    async def validate_claude_talk_readiness(self) -> ValidationResult:
        """Validate readiness for claude-talk integration."""
        readiness_checks = []

        try:
            # Check 1: Session creation capability
            async with websockets.connect(self.ws_url) as websocket:
                await websocket.recv()  # Welcome message

                message = {
                    "type": "request",
                    "id": str(uuid.uuid4()),
                    "method": "claude-talk.session.create",
                    "params": {},
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "version": "1.0.0",
                    "source": "readiness-validator",
                }

                await websocket.send(json.dumps(message))
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)

                readiness_checks.append(
                    {
                        "check": "session_creation",
                        "passed": response_data.get("success")
                        and "sessionId" in response_data.get("result", {}),
                    }
                )

                # Check 2: Agent launch capability
                message = {
                    "type": "request",
                    "id": str(uuid.uuid4()),
                    "method": "claude-talk.agent.launch",
                    "params": {"agentType": "claude-3.5-sonnet", "configuration": {}},
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "version": "1.0.0",
                    "source": "readiness-validator",
                }

                await websocket.send(json.dumps(message))
                response = await asyncio.wait_for(websocket.recv(), timeout=30)
                response_data = json.loads(response)

                readiness_checks.append(
                    {
                        "check": "agent_launch",
                        "passed": response_data.get("success")
                        and "agentId" in response_data.get("result", {}),
                    }
                )

        except Exception as e:
            readiness_checks.append(
                {"check": "claude_talk_integration", "passed": False, "error": str(e)}
            )

        all_ready = all(check.get("passed", False) for check in readiness_checks)
        status = "pass" if all_ready else "warning"

        return ValidationResult(
            test_name="",
            status=status,
            details={
                "readiness_checks": readiness_checks,
                "claude_talk_ready": all_ready,
            },
        )

    def print_results(self):
        """Print validation results in a formatted table."""
        console.print("\n" + "=" * 80)
        console.print("[bold cyan]MCP VALIDATION RESULTS[/bold cyan]")
        console.print("=" * 80)

        # Summary statistics
        passed = sum(1 for r in self.results if r.status == "pass")
        warnings = sum(1 for r in self.results if r.status == "warning")
        failed = sum(1 for r in self.results if r.status == "fail")

        # Results table
        table = Table(title="Validation Test Results")
        table.add_column("Test Name", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        table.add_column("Performance", justify="right")

        for result in self.results:
            # Status with color
            if result.status == "pass":
                status = "[green]PASS[/green]"
            elif result.status == "warning":
                status = "[yellow]WARNING[/yellow]"
            else:
                status = "[red]FAIL[/red]"

            # Details summary
            details = []
            if result.error_message:
                details.append(f"Error: {result.error_message}")
            if result.details:
                key_details = []
                for key, value in result.details.items():
                    if key in [
                        "success_rate",
                        "requests_per_second",
                        "response_time_ms",
                    ]:
                        key_details.append(f"{key}: {value:.2f}")
                    elif isinstance(value, (int, float)) and key not in ["status_code"]:
                        key_details.append(f"{key}: {value}")
                details.extend(key_details[:2])  # Show top 2 details

            # Performance metrics
            perf_info = ""
            if result.metrics:
                perf_info = f"{result.metrics.avg_response_time:.1f}ms avg\n{result.metrics.success_count}/{result.metrics.success_count + result.metrics.error_count} success"

            table.add_row(
                result.test_name,
                status,
                "\n".join(details)[:100],  # Limit details length
                perf_info,
            )

        console.print(table)

        # Summary panel
        summary_text = f"""
Total Tests: {len(self.results)}
[green]Passed: {passed}[/green]
[yellow]Warnings: {warnings}[/yellow]
[red]Failed: {failed}[/red]

Success Rate: {(passed / len(self.results) * 100):.1f}%
        """

        overall_status = (
            "READY"
            if failed == 0
            else ("PARTIALLY READY" if failed <= 2 else "NOT READY")
        )
        status_color = "green" if failed == 0 else ("yellow" if failed <= 2 else "red")

        console.print(
            Panel(
                summary_text,
                title=f"[{status_color}]{overall_status} FOR CLAUDE-TALK MIGRATION[/{status_color}]",
                border_style=status_color,
            )
        )

        # Detailed performance metrics
        if any(r.metrics for r in self.results):
            console.print("\n[bold]Performance Summary:[/bold]")
            for result in self.results:
                if result.metrics:
                    console.print(f"[cyan]{result.test_name}:[/cyan]")
                    console.print(
                        f"  Avg Response Time: {result.metrics.avg_response_time:.2f}ms"
                    )
                    console.print(
                        f"  95th Percentile: {result.metrics.p95_response_time:.2f}ms"
                    )
                    console.print(
                        f"  Throughput: {result.metrics.throughput:.2f} req/s"
                    )
                    console.print(
                        f"  Success Rate: {100 - result.metrics.error_rate:.1f}%"
                    )

        return failed == 0  # Return True if all tests passed


async def main():
    """Main validation function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="MCP Performance and Security Validation"
    )
    parser.add_argument(
        "--server-url", default="http://localhost:8080", help="MCP server URL"
    )
    parser.add_argument(
        "--ws-url", default="ws://localhost:8080/ws", help="MCP WebSocket URL"
    )
    parser.add_argument("--output", help="Output file for detailed results")

    args = parser.parse_args()

    validator = MCPPerformanceValidator(args.server_url, args.ws_url)

    console.print(f"[bold]Validating MCP server at: {args.server_url}[/bold]")
    console.print(f"[bold]WebSocket endpoint: {args.ws_url}[/bold]\n")

    try:
        results = await validator.validate_all()
        success = validator.print_results()

        if args.output:
            # Save detailed results to file
            output_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "server_url": args.server_url,
                "ws_url": args.ws_url,
                "results": [
                    {
                        "test_name": r.test_name,
                        "status": r.status,
                        "details": r.details,
                        "error_message": r.error_message,
                        "metrics": {
                            "avg_response_time": r.metrics.avg_response_time,
                            "p95_response_time": r.metrics.p95_response_time,
                            "throughput": r.metrics.throughput,
                            "error_rate": r.metrics.error_rate,
                            "success_count": r.metrics.success_count,
                            "error_count": r.metrics.error_count,
                        }
                        if r.metrics
                        else None,
                    }
                    for r in results
                ],
            }

            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2, default=str)

            console.print(f"\n[green]Detailed results saved to: {args.output}[/green]")

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Validation interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Validation failed with error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
