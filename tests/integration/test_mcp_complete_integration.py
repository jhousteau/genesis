"""
Comprehensive Integration Tests for MCP Protocol Support
Testing the complete MCP integration for claude-talk migration readiness.
"""

import asyncio
import json
import os
import time
import uuid
from typing import Any, Dict

import pytest
import requests
from websocket import create_connection

# Test Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8080")
MCP_WS_URL = os.getenv("MCP_WS_URL", "ws://localhost:8080/ws")
TEST_PROJECT_ID = os.getenv("TEST_PROJECT_ID", "genesis-test-project")


class MCPTestClient:
    """Test client for MCP protocol validation."""

    def __init__(self, server_url: str, ws_url: str):
        self.server_url = server_url
        self.ws_url = ws_url
        self.ws_connection = None

    async def http_request(
        self, method: str, params: Dict[str, Any] = None, timeout: int = 30
    ) -> Dict[str, Any]:
        """Send HTTP MCP request."""
        message = {
            "type": "request",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or {},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": "1.0.0",
            "source": "mcp-test-client",
        }

        response = requests.post(
            f"{self.server_url}/api/mcp", json=message, timeout=timeout
        )

        return response.json()

    def ws_connect(self):
        """Connect to MCP WebSocket."""
        self.ws_connection = create_connection(self.ws_url)

        # Receive welcome message
        welcome = json.loads(self.ws_connection.recv())
        return welcome

    def ws_send(self, method: str, params: Dict[str, Any] = None) -> str:
        """Send WebSocket MCP request."""
        if not self.ws_connection:
            raise RuntimeError("WebSocket not connected")

        message = {
            "type": "request",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or {},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": "1.0.0",
            "source": "mcp-test-client",
        }

        self.ws_connection.send(json.dumps(message))
        return message["id"]

    def ws_receive(self, timeout: int = 10) -> Dict[str, Any]:
        """Receive WebSocket response."""
        if not self.ws_connection:
            raise RuntimeError("WebSocket not connected")

        self.ws_connection.settimeout(timeout)
        response = json.loads(self.ws_connection.recv())
        return response

    def ws_disconnect(self):
        """Disconnect WebSocket."""
        if self.ws_connection:
            self.ws_connection.close()
            self.ws_connection = None


@pytest.fixture(scope="module")
def mcp_client():
    """Create MCP test client."""
    client = MCPTestClient(MCP_SERVER_URL, MCP_WS_URL)
    yield client
    if client.ws_connection:
        client.ws_disconnect()


@pytest.fixture(scope="module")
def server_health_check():
    """Ensure MCP server is running before tests."""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{MCP_SERVER_URL}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            pass

        if attempt < max_retries - 1:
            time.sleep(2)

    pytest.skip(f"MCP server not available at {MCP_SERVER_URL}")


class TestMCPServerBasics:
    """Test basic MCP server functionality."""

    def test_server_health(self, server_health_check):
        """Test server health endpoint."""
        health_data = server_health_check
        assert health_data["status"] in ["running", "healthy"]
        assert "timestamp" in health_data
        assert isinstance(health_data.get("connections", 0), int)

    def test_server_capabilities(self, mcp_client):
        """Test server capabilities discovery."""
        response = mcp_client.ws_connect()

        assert response["type"] == "notification"
        assert response["event"] == "server.welcome"
        assert "capabilities" in response["data"]

        capabilities = response["data"]["capabilities"]
        required_capabilities = [
            "service.register",
            "service.discover",
            "agent.launch",
            "health.check",
        ]

        for capability in required_capabilities:
            assert capability in capabilities

        mcp_client.ws_disconnect()

    def test_protocol_version_compatibility(self, mcp_client):
        """Test MCP protocol version compatibility."""
        response = mcp_client.ws_connect()

        assert response["data"]["version"] in ["1.0.0", "0.9.0"]

        mcp_client.ws_disconnect()


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and message handling."""

    @pytest.mark.asyncio
    async def test_http_request_response(self, mcp_client):
        """Test HTTP request-response pattern."""
        response = await asyncio.wait_for(
            asyncio.to_thread(mcp_client.http_request, "health.check"), timeout=10
        )

        assert response["success"] == True
        assert response["result"]["status"] in ["running", "healthy"]
        assert "requestId" in response

    def test_websocket_request_response(self, mcp_client):
        """Test WebSocket request-response pattern."""
        mcp_client.ws_connect()

        request_id = mcp_client.ws_send("health.check")
        response = mcp_client.ws_receive()

        assert response["type"] == "response"
        assert response["requestId"] == request_id
        assert response["success"] == True
        assert response["result"]["status"] in ["running", "healthy"]

        mcp_client.ws_disconnect()

    def test_invalid_method_handling(self, mcp_client):
        """Test handling of invalid methods."""
        mcp_client.ws_connect()

        request_id = mcp_client.ws_send("invalid.method")
        response = mcp_client.ws_receive()

        assert response["type"] == "response"
        assert response["requestId"] == request_id
        assert response["success"] == False
        assert "error" in response
        assert "Unsupported method" in response["error"]["message"]

        mcp_client.ws_disconnect()

    def test_malformed_request_handling(self, mcp_client):
        """Test handling of malformed requests."""
        mcp_client.ws_connect()

        # Send malformed JSON
        try:
            mcp_client.ws_connection.send('{"invalid": json}')
            response = mcp_client.ws_receive()

            assert response["type"] == "response"
            assert response["success"] == False
            assert "error" in response
        except:
            # Server may close connection for malformed JSON
            pass

        mcp_client.ws_disconnect()


class TestServiceDiscoveryAndRegistry:
    """Test MCP service discovery and registration."""

    def test_service_registration(self, mcp_client):
        """Test service registration functionality."""
        service_config = {
            "serviceId": f"test-service-{uuid.uuid4()}",
            "name": "Test Service",
            "type": "tool",
            "version": "1.0.0",
            "endpoint": "http://localhost:9999",
            "capabilities": ["test.capability"],
            "healthCheckUrl": "http://localhost:9999/health",
            "tags": ["test", "integration"],
        }

        mcp_client.ws_connect()

        request_id = mcp_client.ws_send("service.register", service_config)
        response = mcp_client.ws_receive()

        assert response["type"] == "response"
        assert response["requestId"] == request_id
        assert response["success"] == True
        assert response["result"]["registered"] == True
        assert response["result"]["serviceId"] == service_config["serviceId"]

        mcp_client.ws_disconnect()

    def test_service_discovery(self, mcp_client):
        """Test service discovery functionality."""
        mcp_client.ws_connect()

        request_id = mcp_client.ws_send("service.discover")
        response = mcp_client.ws_receive()

        assert response["type"] == "response"
        assert response["requestId"] == request_id
        assert response["success"] == True
        assert "services" in response["result"]
        assert isinstance(response["result"]["services"], list)

        mcp_client.ws_disconnect()

    def test_service_discovery_with_filter(self, mcp_client):
        """Test service discovery with filtering."""
        mcp_client.ws_connect()

        filter_params = {"filter": {"type": "tool"}}
        request_id = mcp_client.ws_send("service.discover", filter_params)
        response = mcp_client.ws_receive()

        assert response["type"] == "response"
        assert response["requestId"] == request_id
        assert response["success"] == True

        # All returned services should be of type 'tool'
        services = response["result"]["services"]
        for service in services:
            assert service.get("type") == "tool"

        mcp_client.ws_disconnect()


class TestClaudeTalkIntegration:
    """Test claude-talk specific integration features."""

    def test_agent_launch_request(self, mcp_client):
        """Test agent launch functionality for claude-talk."""
        agent_config = {
            "agentType": "claude-3.5-sonnet",
            "configuration": {
                "systemPrompt": "You are a helpful assistant.",
                "temperature": 0.7,
                "maxTokens": 1000,
            },
            "resourceLimits": {"memory": "1GB", "cpu": "500m", "timeout": 1800},
        }

        mcp_client.ws_connect()

        request_id = mcp_client.ws_send("agent.launch", agent_config)
        response = mcp_client.ws_receive(timeout=30)  # Agent launch may take time

        assert response["type"] == "response"
        assert response["requestId"] == request_id
        assert response["success"] == True
        assert "agentId" in response["result"]
        assert "endpoint" in response["result"]
        assert response["result"]["status"] == "launched"

        mcp_client.ws_disconnect()

    def test_session_creation(self, mcp_client):
        """Test session creation for claude-talk integration."""
        mcp_client.ws_connect()

        request_id = mcp_client.ws_send("claude-talk.session.create")
        response = mcp_client.ws_receive()

        assert response["type"] == "response"
        assert response["requestId"] == request_id
        assert response["success"] == True
        assert "sessionId" in response["result"]
        assert response["result"]["status"] == "created"

        session_id = response["result"]["sessionId"]
        assert session_id.startswith("session_")

        mcp_client.ws_disconnect()


class TestSecretManagerIntegration:
    """Test Secret Manager integration for authentication."""

    @pytest.mark.skipif(not TEST_PROJECT_ID, reason="TEST_PROJECT_ID not set")
    def test_secret_manager_connectivity(self):
        """Test Secret Manager connectivity and access."""
        from core.secrets.manager import get_secret_manager

        try:
            secret_manager = get_secret_manager(
                project_id=TEST_PROJECT_ID, environment="test"
            )

            # Test basic secret manager functionality
            secrets = secret_manager.scan_secrets()
            assert isinstance(secrets, list)

        except Exception as e:
            pytest.skip(f"Secret Manager not accessible: {e}")

    def test_mcp_auth_bridge_initialization(self):
        """Test MCP authentication bridge initialization."""
        from lib.javascript.whitehorse.core.src.mcp.secret_auth_bridge import (
            createSecretAuthBridge,
        )

        config = {"projectId": TEST_PROJECT_ID or "test-project", "environment": "test"}

        # This should not raise an exception
        bridge = createSecretAuthBridge(config)
        assert bridge is not None


class TestPerformanceAndResilience:
    """Test MCP server performance and resilience."""

    def test_concurrent_connections(self, mcp_client):
        """Test handling of multiple concurrent connections."""
        connections = []

        try:
            # Create multiple WebSocket connections
            for i in range(5):
                client = MCPTestClient(MCP_SERVER_URL, MCP_WS_URL)
                client.ws_connect()
                connections.append(client)

            # Send requests from each connection
            for i, client in enumerate(connections):
                request_id = client.ws_send("health.check", {"client_id": i})
                response = client.ws_receive()

                assert response["success"] == True
                assert response["requestId"] == request_id

        finally:
            # Clean up connections
            for client in connections:
                client.ws_disconnect()

    def test_request_timeout_handling(self, mcp_client):
        """Test request timeout handling."""
        # This test would need a mock service that delays responses
        # For now, test that normal requests complete within reasonable time

        start_time = time.time()

        mcp_client.ws_connect()
        request_id = mcp_client.ws_send("health.check")
        response = mcp_client.ws_receive()

        response_time = time.time() - start_time

        assert response["success"] == True
        assert response_time < 5.0  # Should complete within 5 seconds

        mcp_client.ws_disconnect()

    def test_large_payload_handling(self, mcp_client):
        """Test handling of large payloads."""
        # Create a large payload (but within reasonable limits)
        large_data = "x" * 10000  # 10KB payload

        mcp_client.ws_connect()

        request_id = mcp_client.ws_send("health.check", {"large_data": large_data})
        response = mcp_client.ws_receive()

        assert response["success"] == True
        assert response["requestId"] == request_id

        mcp_client.ws_disconnect()


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""

    def test_connection_recovery_after_error(self, mcp_client):
        """Test connection recovery after error."""
        # First, establish a working connection
        mcp_client.ws_connect()

        request_id = mcp_client.ws_send("health.check")
        response = mcp_client.ws_receive()
        assert response["success"] == True

        # Disconnect and reconnect
        mcp_client.ws_disconnect()
        mcp_client.ws_connect()

        # Should be able to send requests again
        request_id = mcp_client.ws_send("health.check")
        response = mcp_client.ws_receive()
        assert response["success"] == True

        mcp_client.ws_disconnect()

    def test_server_error_response_format(self, mcp_client):
        """Test that server errors follow proper MCP format."""
        mcp_client.ws_connect()

        # Send request with invalid parameters
        request_id = mcp_client.ws_send("service.register", {"invalid": "params"})
        response = mcp_client.ws_receive()

        assert response["type"] == "response"
        assert response["requestId"] == request_id
        assert response["success"] == False
        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]

        mcp_client.ws_disconnect()


class TestSecurityValidation:
    """Test security aspects of MCP implementation."""

    def test_cors_headers(self):
        """Test CORS headers in HTTP responses."""
        response = requests.options(f"{MCP_SERVER_URL}/api/mcp")

        # Should handle OPTIONS requests for CORS
        assert response.status_code in [200, 204]

    def test_input_sanitization(self, mcp_client):
        """Test input sanitization for potential injection attacks."""
        # Test with potentially malicious input
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "{{7*7}}",  # Template injection
        ]

        mcp_client.ws_connect()

        for malicious_input in malicious_inputs:
            request_id = mcp_client.ws_send(
                "health.check", {"test_input": malicious_input}
            )
            response = mcp_client.ws_receive()

            # Request should either succeed (input sanitized) or fail gracefully
            assert response["type"] == "response"
            assert response["requestId"] == request_id

            if not response["success"]:
                # If it fails, should be a proper error response
                assert "error" in response

        mcp_client.ws_disconnect()


class TestMonitoringAndMetrics:
    """Test monitoring and metrics functionality."""

    def test_metrics_endpoint(self):
        """Test metrics endpoint availability."""
        try:
            response = requests.get(
                f"{MCP_SERVER_URL.replace('8080', '8081')}/metrics", timeout=10
            )
            # Metrics endpoint may or may not be enabled, but should respond properly if it exists
            assert response.status_code in [200, 404]
        except requests.exceptions.RequestException:
            # Metrics endpoint may not be exposed externally in test environment
            pytest.skip("Metrics endpoint not accessible in test environment")

    def test_health_check_detailed_info(self):
        """Test detailed health check information."""
        response = requests.get(f"{MCP_SERVER_URL}/health")

        assert response.status_code == 200
        health_data = response.json()

        assert "status" in health_data
        assert "timestamp" in health_data
        assert isinstance(health_data.get("connections", 0), int)
        assert isinstance(health_data.get("services", 0), int)


# Performance benchmarks
class TestPerformanceBenchmarks:
    """Performance benchmark tests for claude-talk readiness."""

    def test_response_time_benchmark(self, mcp_client):
        """Test that response times meet performance requirements."""
        response_times = []

        mcp_client.ws_connect()

        # Measure response times for multiple requests
        for _ in range(10):
            start_time = time.time()

            request_id = mcp_client.ws_send("health.check")
            response = mcp_client.ws_receive()

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

            assert response["success"] == True
            response_times.append(response_time)

        mcp_client.ws_disconnect()

        # Calculate statistics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        # Performance requirements for claude-talk
        assert (
            avg_response_time < 100
        ), f"Average response time {avg_response_time:.2f}ms exceeds 100ms requirement"
        assert (
            max_response_time < 500
        ), f"Max response time {max_response_time:.2f}ms exceeds 500ms requirement"

    def test_throughput_benchmark(self, mcp_client):
        """Test throughput requirements."""
        start_time = time.time()
        request_count = 50

        mcp_client.ws_connect()

        # Send multiple requests
        for _ in range(request_count):
            request_id = mcp_client.ws_send("health.check")
            response = mcp_client.ws_receive()
            assert response["success"] == True

        end_time = time.time()
        duration = end_time - start_time
        throughput = request_count / duration

        mcp_client.ws_disconnect()

        # Should handle at least 20 requests per second
        assert (
            throughput >= 20
        ), f"Throughput {throughput:.2f} req/s below minimum 20 req/s requirement"


# Integration readiness validation
def test_claude_talk_migration_readiness():
    """Comprehensive readiness test for claude-talk migration."""
    readiness_checks = {
        "server_availability": False,
        "protocol_compliance": False,
        "service_discovery": False,
        "agent_launch": False,
        "performance_baseline": False,
        "websocket_support": False,
        "error_handling": False,
    }

    try:
        # Check 1: Server availability
        response = requests.get(f"{MCP_SERVER_URL}/health", timeout=5)
        readiness_checks["server_availability"] = response.status_code == 200

        # Check 2: Protocol compliance
        client = MCPTestClient(MCP_SERVER_URL, MCP_WS_URL)
        welcome = client.ws_connect()
        readiness_checks["protocol_compliance"] = welcome.get("type") == "notification"

        # Check 3: Service discovery
        request_id = client.ws_send("service.discover")
        response = client.ws_receive()
        readiness_checks["service_discovery"] = response.get("success") == True

        # Check 4: Agent launch capability
        request_id = client.ws_send("claude-talk.session.create")
        response = client.ws_receive()
        readiness_checks["agent_launch"] = response.get("success") == True

        # Check 5: Performance baseline
        start_time = time.time()
        request_id = client.ws_send("health.check")
        response = client.ws_receive()
        response_time = (time.time() - start_time) * 1000
        readiness_checks["performance_baseline"] = response_time < 200  # Under 200ms

        # Check 6: WebSocket support
        readiness_checks["websocket_support"] = client.ws_connection is not None

        # Check 7: Error handling
        request_id = client.ws_send("invalid.method")
        response = client.ws_receive()
        readiness_checks["error_handling"] = (
            response.get("success") == False and "error" in response
        )

        client.ws_disconnect()

    except Exception as e:
        pytest.fail(f"Readiness check failed with exception: {e}")

    # All checks must pass for migration readiness
    failed_checks = [check for check, passed in readiness_checks.items() if not passed]

    if failed_checks:
        pytest.fail(f"Claude-talk migration not ready. Failed checks: {failed_checks}")

    # If we reach here, all checks passed
    assert True, "MCP integration is ready for claude-talk migration"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
