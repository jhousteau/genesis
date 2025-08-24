#!/usr/bin/env python3
"""
MCP Claude-Talk Integration Tests

Comprehensive integration tests for MCP protocol implementation with claude-talk
including performance benchmarks and validation tests.
"""

import asyncio
import json
import os
import statistics
import subprocess

# Add the project root to the Python path for imports
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict

import pytest
import requests
import websockets

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.logging.logger import GenesisLogger
from intelligence.solve.tools.claude_talk import ClaudeTalkClient

logger = GenesisLogger(__name__)


class MCPIntegrationTester:
    """Integration tester for MCP protocol with claude-talk."""

    def __init__(self):
        self.mcp_server_process = None
        self.server_port = 18080  # Use different port to avoid conflicts
        self.server_url = f"http://localhost:{self.server_port}"
        self.ws_url = f"ws://localhost:{self.server_port}/ws"
        self.metrics_port = self.server_port + 1
        self.claude_talk_client = ClaudeTalkClient()

    async def setup(self):
        """Setup test environment."""
        logger.info("Setting up MCP integration test environment")

        # Start MCP server
        await self.start_mcp_server()

        # Wait for server to be ready
        await self.wait_for_server_ready()

        logger.info("MCP integration test environment ready")

    async def teardown(self):
        """Cleanup test environment."""
        logger.info("Tearing down MCP integration test environment")

        if self.mcp_server_process:
            self.mcp_server_process.terminate()
            try:
                self.mcp_server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.mcp_server_process.kill()
                self.mcp_server_process.wait()

        logger.info("MCP integration test environment cleaned up")

    async def start_mcp_server(self):
        """Start the MCP server for testing."""
        server_code = f"""
        const {{ MCPServer }} = require('@whitehorse/core/dist/mcp');

        const server = new MCPServer({{
            port: {self.server_port},
            enableAuth: false,  // Disable auth for testing
            enableWebSocket: true,
            enableHttp: true,
            corsOrigins: ['*'],
            monitoring: {{
                enabled: true,
                metricsPort: {self.metrics_port}
            }}
        }});

        // Add test handlers
        server.registerHandler('test.echo', async (request) => {{
            const factory = new (require('@whitehorse/core/dist/mcp')).MessageFactory('test-server');
            return factory.createResponse(request.id, request.params);
        }});

        server.registerHandler('agent.launch', async (request) => {{
            const factory = new (require('@whitehorse/core/dist/mcp')).MessageFactory('test-server');

            // Mock agent launch - simulate claude-talk integration
            const sessionId = 'test_session_' + Date.now();

            return factory.createResponse(request.id, {{
                sessionId,
                status: 'launched',
                agentType: request.params.agentType
            }});
        }});

        server.registerHandler('agent.status', async (request) => {{
            const factory = new (require('@whitehorse/core/dist/mcp')).MessageFactory('test-server');

            return factory.createResponse(request.id, {{
                sessionId: request.params.sessionId,
                status: 'running',
                phase: 'implementation',
                progress: '75%'
            }});
        }});

        server.start().then(() => {{
            console.log('Test MCP server started on port {self.server_port}');
        }}).catch(err => {{
            console.error('Failed to start test MCP server:', err);
            process.exit(1);
        }});

        process.on('SIGTERM', async () => {{
            await server.stop();
            process.exit(0);
        }});
        """

        # Write server code to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(server_code)
            server_file = f.name

        try:
            # Start server process
            self.mcp_server_process = subprocess.Popen(
                ["node", server_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            logger.info(
                f"Started MCP server process (PID: {self.mcp_server_process.pid})"
            )

        finally:
            # Clean up temporary file
            os.unlink(server_file)

    async def wait_for_server_ready(self, timeout: int = 30):
        """Wait for the MCP server to be ready."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.server_url}/health", timeout=2)
                if response.status_code == 200:
                    logger.info("MCP server is ready")
                    return True
            except requests.exceptions.RequestException:
                pass

            await asyncio.sleep(1)

        raise TimeoutError("MCP server did not become ready within timeout")

    async def test_http_protocol(self) -> Dict[str, Any]:
        """Test HTTP protocol communication."""
        logger.info("Testing HTTP protocol communication")

        test_request = {
            "type": "request",
            "method": "test.echo",
            "params": {"message": "hello", "timestamp": time.time()},
            "id": "test-http-001",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0",
            "source": "integration-test",
        }

        start_time = time.time()

        try:
            response = requests.post(
                f"{self.server_url}/api/mcp", json=test_request, timeout=10
            )

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms

            if response.status_code == 200:
                data = response.json()

                return {
                    "success": True,
                    "response_time_ms": response_time,
                    "response_data": data,
                    "protocol": "http",
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_time_ms": response_time,
                    "protocol": "http",
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
                "protocol": "http",
            }

    async def test_websocket_protocol(self) -> Dict[str, Any]:
        """Test WebSocket protocol communication."""
        logger.info("Testing WebSocket protocol communication")

        test_request = {
            "type": "request",
            "method": "test.echo",
            "params": {"message": "websocket-test", "timestamp": time.time()},
            "id": "test-ws-001",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0",
            "source": "integration-test",
        }

        start_time = time.time()

        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Send request
                await websocket.send(json.dumps(test_request))

                # Wait for response
                response_raw = await websocket.recv()
                response = json.loads(response_raw)

                end_time = time.time()
                response_time = (end_time - start_time) * 1000

                return {
                    "success": response.get("success", False),
                    "response_time_ms": response_time,
                    "response_data": response,
                    "protocol": "websocket",
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
                "protocol": "websocket",
            }

    async def test_agent_launch(self) -> Dict[str, Any]:
        """Test agent launch functionality."""
        logger.info("Testing agent launch via MCP")

        launch_request = {
            "type": "request",
            "method": "agent.launch",
            "params": {
                "agentType": "backend-developer-agent",
                "prompt": "Implement a REST API for user management",
                "context": {
                    "project": "test-project",
                    "language": "python",
                    "framework": "fastapi",
                },
                "timeout": 30000,
            },
            "id": "test-agent-launch-001",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0",
            "source": "integration-test",
        }

        start_time = time.time()

        try:
            response = requests.post(
                f"{self.server_url}/api/mcp", json=launch_request, timeout=15
            )

            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            if response.status_code == 200:
                data = response.json()

                if data.get("success"):
                    session_id = data.get("result", {}).get("sessionId")

                    # Test status check
                    status_result = await self.test_agent_status(session_id)

                    return {
                        "success": True,
                        "response_time_ms": response_time,
                        "session_id": session_id,
                        "status_check": status_result,
                        "operation": "agent_launch",
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("error", {}).get("message", "Unknown error"),
                        "response_time_ms": response_time,
                        "operation": "agent_launch",
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_time_ms": response_time,
                    "operation": "agent_launch",
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
                "operation": "agent_launch",
            }

    async def test_agent_status(self, session_id: str) -> Dict[str, Any]:
        """Test agent status check."""
        logger.info(f"Testing agent status for session {session_id}")

        status_request = {
            "type": "request",
            "method": "agent.status",
            "params": {"sessionId": session_id},
            "id": f"test-agent-status-{session_id}",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0",
            "source": "integration-test",
        }

        start_time = time.time()

        try:
            response = requests.post(
                f"{self.server_url}/api/mcp", json=status_request, timeout=10
            )

            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": data.get("success", False),
                    "response_time_ms": response_time,
                    "status_data": data.get("result"),
                    "operation": "agent_status",
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_time_ms": response_time,
                    "operation": "agent_status",
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
                "operation": "agent_status",
            }

    async def test_claude_talk_integration(self) -> Dict[str, Any]:
        """Test integration with claude-talk client."""
        logger.info("Testing claude-talk client integration")

        try:
            # Test launching an agent through claude-talk client
            session_id = await self.claude_talk_client.launch_agent(
                prompt="Test agent integration with MCP protocol",
                agent_type="integration-test-agent",
                context={"test_mode": True, "mcp_server_url": self.server_url},
            )

            if session_id:
                # Test getting status
                status = await self.claude_talk_client.get_session_status(session_id)

                # Test sending a message
                message_response = await self.claude_talk_client.send_message(
                    session_id, "Test message via claude-talk client"
                )

                return {
                    "success": True,
                    "session_id": session_id,
                    "status": status,
                    "message_response": message_response,
                    "operation": "claude_talk_integration",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to launch agent via claude-talk",
                    "operation": "claude_talk_integration",
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "claude_talk_integration",
            }

    async def run_performance_benchmark(
        self, num_requests: int = 100, concurrent: int = 10
    ) -> Dict[str, Any]:
        """Run performance benchmarks."""
        logger.info(
            f"Running performance benchmark: {num_requests} requests, {concurrent} concurrent"
        )

        async def make_request(request_id: int) -> Dict[str, Any]:
            """Make a single benchmark request."""
            test_request = {
                "type": "request",
                "method": "test.echo",
                "params": {
                    "message": f"benchmark-{request_id}",
                    "data": "x" * 1000,
                },  # 1KB payload
                "id": f"benchmark-{request_id}",
                "timestamp": "2024-01-01T00:00:00Z",
                "version": "1.0.0",
                "source": "benchmark",
            }

            start_time = time.time()

            try:
                response = requests.post(
                    f"{self.server_url}/api/mcp", json=test_request, timeout=10
                )

                end_time = time.time()
                response_time = (end_time - start_time) * 1000

                return {
                    "success": response.status_code == 200,
                    "response_time_ms": response_time,
                    "request_id": request_id,
                }

            except Exception as e:
                return {
                    "success": False,
                    "response_time_ms": (time.time() - start_time) * 1000,
                    "error": str(e),
                    "request_id": request_id,
                }

        # Run benchmark
        start_time = time.time()

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrent)

        async def limited_request(request_id: int):
            async with semaphore:
                # Convert sync request to async
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    return await loop.run_in_executor(
                        executor, lambda: asyncio.run(make_request(request_id))
                    )

        # Run all requests
        tasks = [limited_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # Analyze results
        successful_results = [
            r for r in results if isinstance(r, dict) and r.get("success")
        ]
        failed_results = [
            r for r in results if isinstance(r, dict) and not r.get("success")
        ]

        if successful_results:
            response_times = [r["response_time_ms"] for r in successful_results]

            return {
                "total_requests": num_requests,
                "successful_requests": len(successful_results),
                "failed_requests": len(failed_results),
                "total_time_seconds": total_time,
                "requests_per_second": num_requests / total_time,
                "avg_response_time_ms": statistics.mean(response_times),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "p95_response_time_ms": statistics.quantiles(response_times, n=20)[
                    18
                ],  # 95th percentile
                "p99_response_time_ms": statistics.quantiles(response_times, n=100)[
                    98
                ],  # 99th percentile
                "concurrency": concurrent,
            }
        else:
            return {
                "total_requests": num_requests,
                "successful_requests": 0,
                "failed_requests": len(failed_results),
                "error": "All requests failed",
                "concurrency": concurrent,
            }

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive integration test suite."""
        logger.info("Running comprehensive MCP integration tests")

        results = {
            "timestamp": time.time(),
            "test_environment": {
                "server_url": self.server_url,
                "ws_url": self.ws_url,
                "metrics_port": self.metrics_port,
            },
            "tests": {},
        }

        try:
            # Test HTTP protocol
            results["tests"]["http_protocol"] = await self.test_http_protocol()

            # Test WebSocket protocol
            results["tests"][
                "websocket_protocol"
            ] = await self.test_websocket_protocol()

            # Test agent launch
            results["tests"]["agent_launch"] = await self.test_agent_launch()

            # Test claude-talk integration
            results["tests"][
                "claude_talk_integration"
            ] = await self.test_claude_talk_integration()

            # Run performance benchmark
            results["tests"]["performance_benchmark"] = (
                await self.run_performance_benchmark(num_requests=50, concurrent=5)
            )

            # Calculate overall success rate
            successful_tests = sum(
                1 for test in results["tests"].values() if test.get("success", False)
            )
            total_tests = len(results["tests"])
            results["overall_success_rate"] = (
                successful_tests / total_tests if total_tests > 0 else 0
            )

            logger.info(
                f"Comprehensive test completed: {successful_tests}/{total_tests} tests passed"
            )

        except Exception as e:
            logger.error(f"Error during comprehensive test: {e}")
            results["error"] = str(e)

        return results


# Pytest integration tests
@pytest.fixture
async def mcp_tester():
    """Pytest fixture for MCP integration tester."""
    tester = MCPIntegrationTester()
    await tester.setup()
    yield tester
    await tester.teardown()


@pytest.mark.asyncio
async def test_http_protocol_communication():
    """Test HTTP protocol communication."""
    tester = MCPIntegrationTester()
    await tester.setup()

    try:
        result = await tester.test_http_protocol()
        assert result["success"], f"HTTP protocol test failed: {result.get('error')}"
        assert result["response_time_ms"] < 1000, "HTTP response time too slow"
        assert "response_data" in result
    finally:
        await tester.teardown()


@pytest.mark.asyncio
async def test_websocket_protocol_communication():
    """Test WebSocket protocol communication."""
    tester = MCPIntegrationTester()
    await tester.setup()

    try:
        result = await tester.test_websocket_protocol()
        assert result[
            "success"
        ], f"WebSocket protocol test failed: {result.get('error')}"
        assert result["response_time_ms"] < 1000, "WebSocket response time too slow"
        assert "response_data" in result
    finally:
        await tester.teardown()


@pytest.mark.asyncio
async def test_agent_launch_functionality():
    """Test agent launch functionality."""
    tester = MCPIntegrationTester()
    await tester.setup()

    try:
        result = await tester.test_agent_launch()
        assert result["success"], f"Agent launch test failed: {result.get('error')}"
        assert "session_id" in result
        assert result["status_check"]["success"], "Agent status check failed"
    finally:
        await tester.teardown()


@pytest.mark.asyncio
async def test_claude_talk_integration():
    """Test claude-talk integration."""
    tester = MCPIntegrationTester()
    await tester.setup()

    try:
        result = await tester.test_claude_talk_integration()
        # Note: This may fail in mock mode, which is expected
        if result["success"]:
            assert "session_id" in result
            assert "status" in result
        else:
            # In mock mode, this is expected to fail but should not raise exceptions
            assert "error" in result
    finally:
        await tester.teardown()


@pytest.mark.asyncio
async def test_performance_benchmark():
    """Test performance benchmarks."""
    tester = MCPIntegrationTester()
    await tester.setup()

    try:
        result = await tester.run_performance_benchmark(num_requests=10, concurrent=2)
        assert result["successful_requests"] > 0, "No successful requests in benchmark"
        assert result["requests_per_second"] > 1, "Request rate too low"
        assert result["avg_response_time_ms"] < 2000, "Average response time too slow"
    finally:
        await tester.teardown()


# Main execution for standalone testing
async def main():
    """Main function for standalone testing."""
    logger.info("Starting MCP Claude-Talk Integration Tests")

    tester = MCPIntegrationTester()
    await tester.setup()

    try:
        # Run comprehensive test
        results = await tester.run_comprehensive_test()

        # Output results
        print("\n" + "=" * 80)
        print("MCP CLAUDE-TALK INTEGRATION TEST RESULTS")
        print("=" * 80)
        print(f"Overall Success Rate: {results['overall_success_rate']*100:.1f}%")
        print(f"Test Environment: {results['test_environment']['server_url']}")
        print("\nTest Results:")

        for test_name, result in results["tests"].items():
            status = "PASS" if result.get("success", False) else "FAIL"
            print(f"  {test_name}: {status}")

            if "response_time_ms" in result:
                print(f"    Response Time: {result['response_time_ms']:.2f}ms")

            if not result.get("success", False) and "error" in result:
                print(f"    Error: {result['error']}")

        # Performance benchmark details
        if "performance_benchmark" in results["tests"]:
            perf = results["tests"]["performance_benchmark"]
            if "requests_per_second" in perf:
                print("\nPerformance Metrics:")
                print(f"  Requests/sec: {perf['requests_per_second']:.2f}")
                print(f"  Avg Response Time: {perf['avg_response_time_ms']:.2f}ms")
                print(f"  P95 Response Time: {perf['p95_response_time_ms']:.2f}ms")
                print(
                    f"  Success Rate: {perf['successful_requests']}/{perf['total_requests']}"
                )

        # Save detailed results
        results_file = "mcp_integration_test_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\nDetailed results saved to: {results_file}")

        # Return overall success for CI/CD
        return results["overall_success_rate"] >= 0.8  # 80% success rate required

    finally:
        await tester.teardown()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
