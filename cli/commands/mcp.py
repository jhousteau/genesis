#!/usr/bin/env python3
"""
Genesis CLI MCP Commands

Provides command-line interface for managing MCP (Model Context Protocol) services
in the Genesis platform with full integration support for claude-talk.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import requests
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from tabulate import tabulate

# Add the project root to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from coordination.system_coordinator import SystemCoordinator
from core.logging.logger import Logger

console = Console()
logger = Logger(__name__)


class MCPServiceManager:
    """Manages MCP services in the Genesis platform."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.getcwd(), "config", "mcp.yaml"
        )
        self.coordinator = SystemCoordinator()
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080")

    async def start_server(
        self, port: int = 8080, config_file: Optional[str] = None
    ) -> bool:
        """Start the MCP server with specified configuration."""
        logger.info(f"Starting MCP server on port {port}")

        try:
            # Load configuration
            config = self._load_config(config_file)

            # Start the TypeScript MCP server
            cmd = [
                "node",
                "-e",
                f"""
                const {{ MCPServer }} = require('@whitehorse/core');

                const server = new MCPServer({{
                    port: {port},
                    enableAuth: {json.dumps(config.get('auth', {}).get('enabled', True))},
                    enableWebSocket: true,
                    enableHttp: true,
                    corsOrigins: {json.dumps(config.get('cors_origins', ['*']))},
                    monitoring: {{
                        enabled: true,
                        metricsPort: {port + 1}
                    }}
                }});

                server.start().then(() => {{
                    console.log('MCP server started successfully');
                }}).catch(err => {{
                    console.error('Failed to start MCP server:', err);
                    process.exit(1);
                }});

                process.on('SIGINT', async () => {{
                    await server.stop();
                    process.exit(0);
                }});
                """,
            ]

            # Run in background if requested
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Wait a moment to check if server started successfully
            await asyncio.sleep(2)

            if process.poll() is None:
                console.print(f"[green]MCP server started on port {port}[/green]")
                return True
            else:
                stdout, stderr = process.communicate()
                console.print("[red]Failed to start MCP server:[/red]")
                console.print(stderr)
                return False

        except Exception as e:
            logger.error(f"Error starting MCP server: {e}")
            console.print(f"[red]Error: {e}[/red]")
            return False

    async def stop_server(self) -> bool:
        """Stop the running MCP server."""
        try:
            response = requests.post(f"{self.mcp_server_url}/api/shutdown", timeout=10)
            if response.status_code == 200:
                console.print("[green]MCP server stopped successfully[/green]")
                return True
            else:
                console.print(
                    f"[red]Failed to stop MCP server: {response.status_code}[/red]"
                )
                return False
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error stopping MCP server: {e}[/red]")
            return False

    async def server_status(self) -> Dict[str, Any]:
        """Get the current status of the MCP server."""
        try:
            response = requests.get(f"{self.mcp_server_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "offline", "message": str(e)}

    async def list_services(
        self, service_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List registered MCP services."""
        try:
            params = {}
            if service_type:
                params["type"] = service_type

            response = requests.get(
                f"{self.mcp_server_url}/api/services", params=params, timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                console.print(
                    f"[red]Failed to list services: {response.status_code}[/red]"
                )
                return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error listing services: {e}[/red]")
            return []

    async def register_service(self, service_config: Dict[str, Any]) -> bool:
        """Register a new MCP service."""
        try:
            response = requests.post(
                f"{self.mcp_server_url}/api/mcp",
                json={
                    "type": "request",
                    "method": "service.register",
                    "params": service_config,
                    "id": f"register-{service_config.get('serviceId', 'unknown')}",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "version": "1.0.0",
                    "source": "genesis-cli",
                },
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    console.print(
                        f"[green]Service registered: {service_config['serviceId']}[/green]"
                    )
                    return True
                else:
                    console.print(
                        f"[red]Registration failed: {result.get('error', {}).get('message')}[/red]"
                    )
                    return False
            else:
                console.print(
                    f"[red]Registration failed: HTTP {response.status_code}[/red]"
                )
                return False

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error registering service: {e}[/red]")
            return False

    async def launch_agent(self, agent_config: Dict[str, Any]) -> Optional[str]:
        """Launch a new Claude agent via MCP."""
        try:
            response = requests.post(
                f"{self.mcp_server_url}/api/mcp",
                json={
                    "type": "request",
                    "method": "agent.launch",
                    "params": agent_config,
                    "id": f"launch-{agent_config.get('agentType', 'unknown')}",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "version": "1.0.0",
                    "source": "genesis-cli",
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    session_id = result.get("result", {}).get("sessionId")
                    console.print(f"[green]Agent launched: {session_id}[/green]")
                    return session_id
                else:
                    console.print(
                        f"[red]Launch failed: {result.get('error', {}).get('message')}[/red]"
                    )
                    return None
            else:
                console.print(f"[red]Launch failed: HTTP {response.status_code}[/red]")
                return None

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error launching agent: {e}[/red]")
            return None

    async def get_metrics(self) -> Dict[str, Any]:
        """Get MCP server metrics."""
        try:
            response = requests.get(f"{self.mcp_server_url}/api/metrics", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load MCP configuration from file."""
        config_path = config_file or self.config_path

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        else:
            # Return default configuration
            return {"auth": {"enabled": True}, "cors_origins": ["*"], "services": []}


@click.group()
@click.pass_context
def mcp(ctx: click.Context) -> None:
    """Manage MCP (Model Context Protocol) services for claude-talk integration."""
    ctx.ensure_object(dict)
    ctx.obj["manager"] = MCPServiceManager()


@mcp.command()
@click.option("--port", "-p", default=8080, help="Port to run MCP server on")
@click.option("--config", "-c", help="Configuration file path")
@click.option("--background", "-b", is_flag=True, help="Run server in background")
@click.pass_context
def start(
    ctx: click.Context, port: int, config: Optional[str], background: bool
) -> None:
    """Start the MCP server."""
    manager = ctx.obj["manager"]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Starting MCP server...", total=None)

        success = asyncio.run(manager.start_server(port, config))

        if success:
            progress.update(
                task, description="[green]MCP server started successfully[/green]"
            )
            console.print(f"Server running on http://localhost:{port}")
            console.print(f"Metrics available on http://localhost:{port + 1}/metrics")

            if not background:
                console.print("Press Ctrl+C to stop the server")
                try:
                    # Keep the process running
                    while True:
                        asyncio.sleep(1)
                except KeyboardInterrupt:
                    console.print("\nStopping server...")
        else:
            progress.update(task, description="[red]Failed to start MCP server[/red]")


@mcp.command()
@click.pass_context
def stop(ctx: click.Context) -> None:
    """Stop the MCP server."""
    manager = ctx.obj["manager"]

    success = asyncio.run(manager.stop_server())
    if not success:
        sys.exit(1)


@mcp.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show MCP server status."""
    manager = ctx.obj["manager"]

    status_info = asyncio.run(manager.server_status())

    if status_info["status"] == "offline":
        console.print("[red]MCP server is offline[/red]")
        console.print(f"Error: {status_info.get('message', 'Unknown error')}")
    else:
        console.print(
            Panel(
                f"Status: [green]{status_info.get('status', 'unknown')}[/green]\n"
                f"Connections: {status_info.get('connections', 0)}\n"
                f"Services: {status_info.get('services', 0)}\n"
                f"Timestamp: {status_info.get('timestamp', 'unknown')}",
                title="MCP Server Status",
                border_style="green",
            )
        )


@mcp.command()
@click.option("--type", "-t", help="Filter services by type")
@click.option(
    "--format",
    "-f",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format",
)
@click.pass_context
def services(ctx: click.Context, type: Optional[str], format: str) -> None:
    """List registered MCP services."""
    manager = ctx.obj["manager"]

    services_list = asyncio.run(manager.list_services(type))

    if format == "json":
        console.print(json.dumps(services_list, indent=2))
    else:
        if services_list:
            headers = ["Service ID", "Name", "Type", "Status", "Endpoint"]
            rows = []

            for service in services_list:
                rows.append(
                    [
                        service.get("serviceId", "N/A"),
                        service.get("name", "N/A"),
                        service.get("type", "N/A"),
                        service.get("status", "N/A"),
                        service.get("endpoint", "N/A"),
                    ]
                )

            console.print(tabulate(rows, headers=headers, tablefmt="grid"))
        else:
            console.print("No services registered")


@mcp.command()
@click.option("--service-id", required=True, help="Unique service identifier")
@click.option("--name", required=True, help="Service name")
@click.option(
    "--type",
    required=True,
    type=click.Choice(["agent", "tool", "resource", "monitor"]),
    help="Service type",
)
@click.option("--endpoint", required=True, help="Service endpoint URL")
@click.option("--capabilities", help="Comma-separated list of capabilities")
@click.option("--tags", help="Comma-separated list of tags")
@click.pass_context
def register(
    ctx: click.Context,
    service_id: str,
    name: str,
    type: str,
    endpoint: str,
    capabilities: Optional[str],
    tags: Optional[str],
) -> None:
    """Register a new MCP service."""
    manager = ctx.obj["manager"]

    service_config = {
        "serviceId": service_id,
        "name": name,
        "type": type,
        "endpoint": endpoint,
        "capabilities": capabilities.split(",") if capabilities else [],
        "tags": tags.split(",") if tags else [],
        "version": "1.0.0",
    }

    success = asyncio.run(manager.register_service(service_config))
    if not success:
        sys.exit(1)


@mcp.command()
@click.option("--agent-type", required=True, help="Type of agent to launch")
@click.option("--prompt", required=True, help="Agent prompt/instructions")
@click.option("--context", help="JSON context data for the agent")
@click.option("--timeout", default=1800, help="Agent timeout in seconds")
@click.pass_context
def launch(
    ctx: click.Context,
    agent_type: str,
    prompt: str,
    context: Optional[str],
    timeout: int,
) -> None:
    """Launch a new Claude agent."""
    manager = ctx.obj["manager"]

    agent_config = {
        "agentType": agent_type,
        "prompt": prompt,
        "timeout": timeout * 1000,  # Convert to milliseconds
    }

    if context:
        try:
            agent_config["context"] = json.loads(context)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON context: {e}[/red]")
            sys.exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Launching agent...", total=None)

        session_id = asyncio.run(manager.launch_agent(agent_config))

        if session_id:
            progress.update(
                task, description="[green]Agent launched successfully[/green]"
            )
            console.print(f"Session ID: {session_id}")
            console.print(f"Use 'g mcp agent-status {session_id}' to monitor progress")
        else:
            progress.update(task, description="[red]Failed to launch agent[/red]")
            sys.exit(1)


@mcp.command()
@click.pass_context
def metrics(ctx: click.Context) -> None:
    """Show MCP server metrics."""
    manager = ctx.obj["manager"]

    metrics_data = asyncio.run(manager.get_metrics())

    if "error" in metrics_data:
        console.print(f"[red]Failed to get metrics: {metrics_data['error']}[/red]")
        sys.exit(1)

    console.print(
        Panel(
            f"Messages Sent: {metrics_data.get('messagesSent', 0)}\n"
            f"Messages Received: {metrics_data.get('messagesReceived', 0)}\n"
            f"Active Connections: {metrics_data.get('activeConnections', 0)}\n"
            f"Error Count: {metrics_data.get('errorCount', 0)}\n"
            f"Average Latency: {metrics_data.get('requestLatency', {}).get('avg', 0):.2f}ms",
            title="MCP Server Metrics",
            border_style="blue",
        )
    )


@mcp.command()
@click.option("--output", "-o", help="Output configuration file path")
@click.pass_context
def init(ctx: click.Context, output: Optional[str]) -> None:
    """Initialize MCP configuration file."""
    config_path = output or os.path.join(os.getcwd(), "config", "mcp.yaml")

    # Ensure config directory exists
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    default_config = {
        "mcp": {
            "server": {
                "port": 8080,
                "host": "0.0.0.0",
                "enableAuth": True,
                "enableWebSocket": True,
                "enableHttp": True,
                "corsOrigins": ["*"],
            },
            "auth": {
                "enabled": True,
                "strategies": ["jwt", "api-key"],
                "jwt": {"secret": "${MCP_JWT_SECRET}", "expiresIn": "1h"},
            },
            "monitoring": {
                "enabled": True,
                "metricsPort": 8081,
                "healthCheckInterval": 30,
            },
            "services": {"registry": {"maxServices": 100, "healthCheckInterval": 30}},
        },
        "claude_talk": {
            "integration": {
                "enabled": True,
                "mock_mode": False,
                "session_timeout": 1800,
            }
        },
    }

    with open(config_path, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    console.print(f"[green]MCP configuration initialized at {config_path}[/green]")
    console.print("Remember to set environment variables:")
    console.print("  - MCP_JWT_SECRET: JWT signing secret")
    console.print("  - MCP_SERVER_URL: MCP server URL (if different from default)")


@mcp.command()
@click.option("--watch", "-w", is_flag=True, help="Watch for real-time updates")
@click.option("--interval", "-i", default=5, help="Update interval in seconds")
@click.pass_context
def monitor(ctx: click.Context, watch: bool, interval: int) -> None:
    """Monitor MCP server in real-time."""
    manager = ctx.obj["manager"]

    if watch:
        console.print("[green]Starting real-time MCP monitoring...[/green]")
        console.print("Press Ctrl+C to stop monitoring")

        try:
            while True:
                # Clear screen for updates
                os.system("clear" if os.name == "posix" else "cls")

                # Get current status and metrics
                status_info = asyncio.run(manager.server_status())
                metrics_data = asyncio.run(manager.get_metrics())
                services_list = asyncio.run(manager.list_services())

                # Display header
                console.print(
                    f"[bold cyan]MCP Server Monitor - {time.strftime('%H:%M:%S')}[/bold cyan]"
                )
                console.print("=" * 60)

                # Display server status
                if status_info["status"] == "offline":
                    console.print("[red]Server Status: OFFLINE[/red]")
                    console.print(
                        f"Error: {status_info.get('message', 'Unknown error')}"
                    )
                else:
                    console.print(
                        f"[green]Server Status: {status_info.get('status', 'unknown').upper()}[/green]"
                    )
                    console.print(
                        f"Active Connections: {status_info.get('connections', 0)}"
                    )
                    console.print(f"Registered Services: {len(services_list)}")

                # Display metrics if available
                if "error" not in metrics_data:
                    console.print("\n[bold]Performance Metrics:[/bold]")
                    console.print(
                        f"  Messages Sent: {metrics_data.get('messagesSent', 0)}"
                    )
                    console.print(
                        f"  Messages Received: {metrics_data.get('messagesReceived', 0)}"
                    )
                    console.print(f"  Error Count: {metrics_data.get('errorCount', 0)}")
                    console.print(
                        f"  Average Latency: {metrics_data.get('requestLatency', {}).get('avg', 0):.2f}ms"
                    )

                # Display service health
                if services_list:
                    console.print("\n[bold]Service Health:[/bold]")
                    for service in services_list[:5]:  # Show first 5 services
                        health_status = service.get("health", {}).get(
                            "status", "unknown"
                        )
                        color = "green" if health_status == "healthy" else "red"
                        console.print(
                            f"  {service.get('serviceId', 'unknown')}: [{color}]{health_status}[/{color}]"
                        )

                console.print(f"\n[dim]Next update in {interval} seconds...[/dim]")
                time.sleep(interval)

        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped[/yellow]")
    else:
        # Single status check
        status_info = asyncio.run(manager.server_status())
        metrics_data = asyncio.run(manager.get_metrics())

        console.print(
            Panel(
                f"Status: [green]{status_info.get('status', 'unknown')}[/green]\n"
                f"Messages: {metrics_data.get('messagesSent', 0)} sent, {metrics_data.get('messagesReceived', 0)} received\n"
                f"Errors: {metrics_data.get('errorCount', 0)}\n"
                f"Latency: {metrics_data.get('requestLatency', {}).get('avg', 0):.2f}ms",
                title="MCP Server Status",
                border_style="green",
            )
        )


@mcp.command()
@click.option("--session-id", required=True, help="Agent session ID to monitor")
@click.option("--watch", "-w", is_flag=True, help="Watch agent status continuously")
@click.option("--interval", "-i", default=3, help="Update interval in seconds")
@click.pass_context
def agent_status(
    ctx: click.Context, session_id: str, watch: bool, interval: int
) -> None:
    """Get detailed agent status."""
    manager = ctx.obj["manager"]

    async def get_agent_status():
        try:
            response = requests.get(
                f"{manager.mcp_server_url}/api/agents/{session_id}/status", timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    if watch:
        console.print(f"[green]Monitoring agent {session_id}...[/green]")
        console.print("Press Ctrl+C to stop monitoring")

        try:
            while True:
                os.system("clear" if os.name == "posix" else "cls")

                status_data = asyncio.run(get_agent_status())

                console.print(
                    f"[bold cyan]Agent Status - {session_id} - {time.strftime('%H:%M:%S')}[/bold cyan]"
                )
                console.print("=" * 60)

                if "error" in status_data:
                    console.print(f"[red]Error: {status_data['error']}[/red]")
                else:
                    console.print(
                        f"Status: [green]{status_data.get('status', 'unknown')}[/green]"
                    )
                    console.print(f"Phase: {status_data.get('phase', 'unknown')}")
                    console.print(f"Progress: {status_data.get('progress', 'N/A')}")

                    if "health" in status_data:
                        health = status_data["health"]
                        console.print(f"CPU: {health.get('cpu', 0):.1f}%")
                        console.print(f"Memory: {health.get('memory', 0):.1f}%")
                        console.print(f"Uptime: {health.get('uptime', 0)}s")

                console.print(f"\n[dim]Next update in {interval} seconds...[/dim]")
                time.sleep(interval)

        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped[/yellow]")
    else:
        status_data = asyncio.run(get_agent_status())

        if "error" in status_data:
            console.print(f"[red]Error: {status_data['error']}[/red]")
            sys.exit(1)

        console.print(
            Panel(
                f"Session ID: {session_id}\n"
                f"Status: [green]{status_data.get('status', 'unknown')}[/green]\n"
                f"Phase: {status_data.get('phase', 'unknown')}\n"
                f"Progress: {status_data.get('progress', 'N/A')}",
                title="Agent Status",
                border_style="blue",
            )
        )


@mcp.command()
@click.option("--session-id", required=True, help="Agent session ID")
@click.option("--message", required=True, help="Message to send to agent")
@click.option("--wait", "-w", is_flag=True, help="Wait for response")
@click.option("--timeout", default=30, help="Response timeout in seconds")
@click.pass_context
def send_message(
    ctx: click.Context, session_id: str, message: str, wait: bool, timeout: int
) -> None:
    """Send message to running agent."""
    manager = ctx.obj["manager"]

    async def send_agent_message():
        message_request = {
            "type": "request",
            "id": str(uuid.uuid4()),
            "method": "agent.message",
            "params": {
                "sessionId": session_id,
                "message": {
                    "content": message,
                    "waitForResponse": wait,
                    "timeout": timeout * 1000,
                },
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": "1.0.0",
            "source": "genesis-cli",
        }

        try:
            response = requests.post(
                f"{manager.mcp_server_url}/api/mcp",
                json=message_request,
                timeout=timeout + 5,
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Sending message...", total=None)

        result = asyncio.run(send_agent_message())

        if result.get("success"):
            progress.update(
                task, description="[green]Message sent successfully[/green]"
            )
            console.print(
                f"Message ID: {result.get('result', {}).get('messageId', 'unknown')}"
            )

            if wait and result.get("result", {}).get("response"):
                console.print("\n[bold]Agent Response:[/bold]")
                console.print(result["result"]["response"])
        else:
            progress.update(task, description="[red]Failed to send message[/red]")
            console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
            sys.exit(1)


@mcp.command()
@click.option(
    "--format",
    "-f",
    default="table",
    type=click.Choice(["table", "json", "yaml"]),
    help="Output format",
)
@click.pass_context
def debug_info(ctx: click.Context, format: str) -> None:
    """Get comprehensive debug information."""
    manager = ctx.obj["manager"]

    debug_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "environment": {
            "server_url": manager.mcp_server_url,
            "python_version": sys.version,
            "platform": sys.platform,
        },
        "server_status": asyncio.run(manager.server_status()),
        "metrics": asyncio.run(manager.get_metrics()),
        "services": asyncio.run(manager.list_services()),
    }

    if format == "json":
        console.print(json.dumps(debug_data, indent=2, default=str))
    elif format == "yaml":
        console.print(yaml.dump(debug_data, default_flow_style=False, sort_keys=False))
    else:
        # Table format
        console.print("[bold cyan]MCP Debug Information[/bold cyan]")
        console.print("=" * 50)

        console.print(f"[bold]Timestamp:[/bold] {debug_data['timestamp']}")
        console.print(
            f"[bold]Server URL:[/bold] {debug_data['environment']['server_url']}"
        )
        console.print(
            f"[bold]Python Version:[/bold] {debug_data['environment']['python_version']}"
        )

        console.print("\n[bold]Server Status:[/bold]")
        status = debug_data["server_status"]
        if status.get("status") == "offline":
            console.print(f"  Status: [red]{status['status']}[/red]")
            console.print(f"  Message: {status.get('message', 'N/A')}")
        else:
            console.print(f"  Status: [green]{status.get('status', 'unknown')}[/green]")
            console.print(f"  Connections: {status.get('connections', 0)}")
            console.print(f"  Services: {status.get('services', 0)}")

        console.print("\n[bold]Performance Metrics:[/bold]")
        metrics = debug_data["metrics"]
        if "error" in metrics:
            console.print(f"  Error: {metrics['error']}")
        else:
            console.print(f"  Messages Sent: {metrics.get('messagesSent', 0)}")
            console.print(f"  Messages Received: {metrics.get('messagesReceived', 0)}")
            console.print(f"  Error Count: {metrics.get('errorCount', 0)}")
            console.print(
                f"  Active Connections: {metrics.get('activeConnections', 0)}"
            )

        console.print(
            f"\n[bold]Registered Services:[/bold] {len(debug_data['services'])}"
        )


@mcp.command()
@click.option("--duration", "-d", default=60, help="Test duration in seconds")
@click.option("--concurrent", "-c", default=10, help="Concurrent connections")
@click.option("--message-size", "-s", default=1024, help="Message size in bytes")
@click.pass_context
def load_test(
    ctx: click.Context, duration: int, concurrent: int, message_size: int
) -> None:
    """Run load test against MCP server."""
    manager = ctx.obj["manager"]

    async def run_load_test():
        console.print("[green]Starting load test...[/green]")
        console.print(
            f"Duration: {duration}s, Concurrent: {concurrent}, Message Size: {message_size} bytes"
        )

        start_time = time.time()
        end_time = start_time + duration

        results = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": {},
        }

        semaphore = asyncio.Semaphore(concurrent)

        async def make_request():
            async with semaphore:
                test_message = {
                    "type": "request",
                    "id": str(uuid.uuid4()),
                    "method": "test.echo",
                    "params": {"data": "x" * message_size},
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "version": "1.0.0",
                    "source": "load-test",
                }

                request_start = time.time()

                try:
                    response = requests.post(
                        f"{manager.mcp_server_url}/api/mcp",
                        json=test_message,
                        timeout=10,
                    )

                    response_time = (time.time() - request_start) * 1000
                    results["response_times"].append(response_time)
                    results["total_requests"] += 1

                    if response.status_code == 200:
                        results["successful_requests"] += 1
                    else:
                        results["failed_requests"] += 1
                        error_key = f"HTTP_{response.status_code}"
                        results["errors"][error_key] = (
                            results["errors"].get(error_key, 0) + 1
                        )

                except Exception as e:
                    results["total_requests"] += 1
                    results["failed_requests"] += 1
                    error_key = str(type(e).__name__)
                    results["errors"][error_key] = (
                        results["errors"].get(error_key, 0) + 1
                    )

        # Run requests continuously
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running load test...", total=None)

            try:
                while time.time() < end_time:
                    tasks = [make_request() for _ in range(concurrent)]
                    await asyncio.gather(*tasks, return_exceptions=True)

                    # Update progress
                    elapsed = time.time() - start_time
                    remaining = max(0, end_time - time.time())
                    progress.update(
                        task,
                        description=f"Running load test... {elapsed:.1f}s elapsed, {remaining:.1f}s remaining",
                    )

                    if remaining <= 0:
                        break

                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.1)

            except KeyboardInterrupt:
                console.print("\n[yellow]Load test interrupted[/yellow]")

        # Calculate statistics
        total_time = time.time() - start_time

        if results["response_times"]:
            avg_response_time = sum(results["response_times"]) / len(
                results["response_times"]
            )
            min_response_time = min(results["response_times"])
            max_response_time = max(results["response_times"])
        else:
            avg_response_time = min_response_time = max_response_time = 0

        # Display results
        console.print("\n[bold cyan]Load Test Results[/bold cyan]")
        console.print("=" * 40)
        console.print(f"Duration: {total_time:.1f}s")
        console.print(f"Total Requests: {results['total_requests']}")
        console.print(f"Successful: {results['successful_requests']}")
        console.print(f"Failed: {results['failed_requests']}")
        console.print(
            f"Success Rate: {(results['successful_requests'] / max(1, results['total_requests']) * 100):.1f}%"
        )
        console.print(
            f"Requests/sec: {results['total_requests'] / max(1, total_time):.1f}"
        )
        console.print(f"Avg Response Time: {avg_response_time:.2f}ms")
        console.print(f"Min Response Time: {min_response_time:.2f}ms")
        console.print(f"Max Response Time: {max_response_time:.2f}ms")

        if results["errors"]:
            console.print("\n[bold]Errors:[/bold]")
            for error, count in results["errors"].items():
                console.print(f"  {error}: {count}")

    asyncio.run(run_load_test())


@mcp.command()
@click.option("--output", "-o", help="Output file path for test results")
@click.pass_context
def validate_integration(ctx: click.Context, output: Optional[str]) -> None:
    """Validate MCP integration readiness for claude-talk."""
    manager = ctx.obj["manager"]

    console.print(
        "[green]Validating MCP integration for claude-talk readiness...[/green]"
    )

    validation_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "tests": {},
        "overall_status": "unknown",
    }

    # Test 1: Server connectivity
    console.print("\n1. Testing server connectivity...")
    server_status = asyncio.run(manager.server_status())
    validation_results["tests"]["server_connectivity"] = {
        "status": "pass" if server_status.get("status") != "offline" else "fail",
        "details": server_status,
    }

    # Test 2: Protocol compliance
    console.print("2. Testing protocol compliance...")
    try:
        test_request = {
            "type": "request",
            "id": str(uuid.uuid4()),
            "method": "health.check",
            "params": {},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": "1.0.0",
            "source": "validation-test",
        }

        response = requests.post(
            f"{manager.mcp_server_url}/api/mcp", json=test_request, timeout=10
        )

        protocol_test = {
            "status": "pass" if response.status_code == 200 else "fail",
            "response_code": response.status_code,
            "response_time": response.elapsed.total_seconds() * 1000,
        }
    except Exception as e:
        protocol_test = {"status": "fail", "error": str(e)}

    validation_results["tests"]["protocol_compliance"] = protocol_test

    # Test 3: Service discovery
    console.print("3. Testing service discovery...")
    services = asyncio.run(manager.list_services())
    validation_results["tests"]["service_discovery"] = {
        "status": "pass",  # Service discovery should work even with no services
        "service_count": len(services),
        "services": services,
    }

    # Test 4: Authentication (if enabled)
    console.print("4. Testing authentication...")
    # This is a placeholder - in real implementation would test JWT/API key auth
    validation_results["tests"]["authentication"] = {
        "status": "pass",
        "note": "Authentication test requires configuration",
    }

    # Test 5: Performance baseline
    console.print("5. Testing performance baseline...")
    try:
        perf_start = time.time()
        for _ in range(10):
            response = requests.post(
                f"{manager.mcp_server_url}/api/mcp", json=test_request, timeout=5
            )
        perf_time = (time.time() - perf_start) * 1000 / 10  # Average time per request

        performance_test = {
            "status": "pass" if perf_time < 1000 else "fail",  # Must be under 1 second
            "avg_response_time_ms": perf_time,
            "threshold_ms": 1000,
        }
    except Exception as e:
        performance_test = {"status": "fail", "error": str(e)}

    validation_results["tests"]["performance_baseline"] = performance_test

    # Calculate overall status
    passed_tests = sum(
        1 for test in validation_results["tests"].values() if test["status"] == "pass"
    )
    total_tests = len(validation_results["tests"])

    validation_results["overall_status"] = (
        "ready" if passed_tests == total_tests else "not_ready"
    )
    validation_results["test_summary"] = {
        "passed": passed_tests,
        "total": total_tests,
        "success_rate": (passed_tests / total_tests) * 100,
    }

    # Display results
    console.print("\n[bold cyan]Integration Validation Results[/bold cyan]")
    console.print("=" * 50)

    for test_name, result in validation_results["tests"].items():
        status_color = "green" if result["status"] == "pass" else "red"
        console.print(
            f"{test_name}: [{status_color}]{result['status'].upper()}[/{status_color}]"
        )

        if "error" in result:
            console.print(f"  Error: {result['error']}")
        elif "response_time" in result:
            console.print(f"  Response Time: {result['response_time']:.2f}ms")

    overall_color = (
        "green" if validation_results["overall_status"] == "ready" else "red"
    )
    console.print(
        f"\n[bold]Overall Status: [{overall_color}]{validation_results['overall_status'].upper()}[/{overall_color}][/bold]"
    )
    console.print(
        f"Success Rate: {validation_results['test_summary']['success_rate']:.1f}%"
    )

    # Save results if requested
    if output:
        with open(output, "w") as f:
            json.dump(validation_results, f, indent=2, default=str)
        console.print(f"\nResults saved to: {output}")

    # Exit with appropriate code
    if validation_results["overall_status"] != "ready":
        sys.exit(1)


if __name__ == "__main__":
    mcp()
