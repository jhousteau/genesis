#!/usr/bin/env python3
"""
Genesis CLI Main Module
Universal Infrastructure Platform Command Interface

Implements PIPES methodology through comprehensive CLI commands:
- VM Management (Issue #30)
- Container Orchestration (Issue #31)
- Infrastructure Automation
- Agent-Cage and Claude-Talk Migration Support
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .agent_commands import AgentCommands
from .container_commands import ContainerCommands
from .infrastructure_commands import InfrastructureCommands
# Genesis CLI modules
from .vm_commands import VMCommands

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GenesisCliError(Exception):
    """Base exception for Genesis CLI errors."""

    pass


class GenesisCLI:
    """
    Main CLI class for Genesis Universal Infrastructure Platform.

    Provides comprehensive commands for:
    - VM Management (agent VM pools, autoscaling, lifecycle)
    - Container Orchestration (GKE clusters, deployments, services)
    - Infrastructure Automation (Terraform, monitoring, security)
    - Agent Operations (agent-cage, claude-talk integration)
    """

    def __init__(self) -> None:
        self.genesis_root = Path(__file__).parent.parent.parent
        self.config_path = self.genesis_root / "config"
        self.environment = os.getenv("ENVIRONMENT", "dev")
        self.project_id = os.getenv("PROJECT_ID")

        # Initialize command modules
        self.vm_commands = VMCommands(self)
        self.container_commands = ContainerCommands(self)
        self.infrastructure_commands = InfrastructureCommands(self)
        self.agent_commands = AgentCommands(self)

    def load_config(self) -> Dict[str, Any]:
        """Load Genesis configuration."""
        config_file = self.config_path / f"environments/{self.environment}.yaml"
        if config_file.exists():
            import yaml

            with open(config_file, "r") as f:
                return yaml.safe_load(f)
        return {}

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser."""
        parser = argparse.ArgumentParser(
            prog="g",
            description="Genesis Universal Infrastructure Platform CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # VM Management
  g vm create-pool --type backend-developer --size 3
  g vm scale-pool backend-pool --min 1 --max 10
  g vm health-check --pool backend-pool

  # Container Orchestration
  g container deploy --service agent-cage --environment dev
  g container scale --deployment claude-talk --replicas 5
  g container logs --service agent-cage --follow

  # Infrastructure Management
  g infra plan --module vm-management --environment dev
  g infra apply --module container-orchestration --environment prod
  g infra status --all

  # Agent Operations
  g agent start --type backend-developer --count 2
  g agent migrate --from legacy --to agent-cage
  g agent status --all

For more information, see: https://github.com/genesis-platform/genesis
            """,
        )

        # Global options
        parser.add_argument(
            "--environment",
            "-e",
            default=self.environment,
            help="Environment (dev, staging, prod)",
        )
        parser.add_argument(
            "--project-id", "-p", default=self.project_id, help="GCP project ID"
        )
        parser.add_argument("--config", help="Configuration file path")
        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose logging"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without executing",
        )
        parser.add_argument(
            "--output",
            "-o",
            choices=["json", "yaml", "table", "text"],
            default="text",
            help="Output format",
        )

        # Create subparsers for main command categories
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # VM Management Commands (Issue #30)
        self._add_vm_commands(subparsers)

        # Container Orchestration Commands (Issue #31)
        self._add_container_commands(subparsers)

        # Infrastructure Commands
        self._add_infrastructure_commands(subparsers)

        # Agent Commands (agent-cage and claude-talk)
        self._add_agent_commands(subparsers)

        return parser

    def _add_vm_commands(self, subparsers: argparse._SubParsersAction) -> None:
        """Add VM management commands."""
        vm_parser = subparsers.add_parser(
            "vm",
            help="VM management commands (Issue #30)",
            description="Manage agent VMs, pools, and infrastructure",
        )

        vm_subparsers = vm_parser.add_subparsers(dest="vm_action")

        # VM Pool Management
        create_pool_parser = vm_subparsers.add_parser(
            "create-pool", help="Create agent VM pool"
        )
        create_pool_parser.add_argument("--type", required=True, help="Agent type")
        create_pool_parser.add_argument(
            "--size", type=int, default=1, help="Initial pool size"
        )
        create_pool_parser.add_argument("--machine-type", help="VM machine type")
        create_pool_parser.add_argument(
            "--preemptible", action="store_true", help="Use preemptible instances"
        )
        create_pool_parser.add_argument("--zones", nargs="+", help="Deployment zones")

        scale_pool_parser = vm_subparsers.add_parser(
            "scale-pool", help="Scale agent VM pool"
        )
        scale_pool_parser.add_argument("pool_name", help="Pool name")
        scale_pool_parser.add_argument("--size", type=int, help="Target pool size")
        scale_pool_parser.add_argument("--min", type=int, help="Minimum pool size")
        scale_pool_parser.add_argument("--max", type=int, help="Maximum pool size")
        scale_pool_parser.add_argument(
            "--enable-autoscaling", action="store_true", help="Enable autoscaling"
        )

        # VM Operations
        vm_subparsers.add_parser("list-pools", help="List all VM pools")
        vm_subparsers.add_parser("list-instances", help="List all VM instances")

        health_parser = vm_subparsers.add_parser(
            "health-check", help="Check VM health status"
        )
        health_parser.add_argument("--pool", help="Specific pool to check")
        health_parser.add_argument("--instance", help="Specific instance to check")

        # VM Lifecycle
        start_parser = vm_subparsers.add_parser("start", help="Start VM instances")
        start_parser.add_argument("--pool", help="Pool to start")
        start_parser.add_argument("--instance", help="Instance to start")

        stop_parser = vm_subparsers.add_parser("stop", help="Stop VM instances")
        stop_parser.add_argument("--pool", help="Pool to stop")
        stop_parser.add_argument("--instance", help="Instance to stop")

        restart_parser = vm_subparsers.add_parser(
            "restart", help="Restart VM instances"
        )
        restart_parser.add_argument("--pool", help="Pool to restart")
        restart_parser.add_argument("--instance", help="Instance to restart")

        # Template Management
        vm_subparsers.add_parser("list-templates", help="List VM templates")

        update_template_parser = vm_subparsers.add_parser(
            "update-template", help="Update VM template"
        )
        update_template_parser.add_argument("template_name", help="Template name")
        update_template_parser.add_argument("--image", help="New source image")
        update_template_parser.add_argument("--machine-type", help="New machine type")

    def _add_container_commands(self, subparsers: argparse._SubParsersAction) -> None:
        """Add container orchestration commands."""
        container_parser = subparsers.add_parser(
            "container",
            help="Container orchestration commands (Issue #31)",
            description="Manage GKE clusters, deployments, and services",
        )

        container_subparsers = container_parser.add_subparsers(dest="container_action")

        # Cluster Management
        create_cluster_parser = container_subparsers.add_parser(
            "create-cluster", help="Create GKE cluster"
        )
        create_cluster_parser.add_argument("cluster_name", help="Cluster name")
        create_cluster_parser.add_argument(
            "--autopilot", action="store_true", help="Use Autopilot mode"
        )
        create_cluster_parser.add_argument("--region", help="Cluster region")
        create_cluster_parser.add_argument(
            "--node-pools", nargs="+", help="Node pool configurations"
        )

        container_subparsers.add_parser("list-clusters", help="List GKE clusters")
        container_subparsers.add_parser("delete-cluster", help="Delete GKE cluster")

        # Deployment Management
        deploy_parser = container_subparsers.add_parser(
            "deploy", help="Deploy container service"
        )
        deploy_parser.add_argument(
            "--service", required=True, help="Service name (agent-cage, claude-talk)"
        )
        deploy_parser.add_argument("--version", help="Service version")
        deploy_parser.add_argument("--replicas", type=int, help="Number of replicas")
        deploy_parser.add_argument("--namespace", help="Kubernetes namespace")

        scale_parser = container_subparsers.add_parser(
            "scale", help="Scale container deployment"
        )
        scale_parser.add_argument("--deployment", required=True, help="Deployment name")
        scale_parser.add_argument(
            "--replicas", type=int, required=True, help="Target replicas"
        )
        scale_parser.add_argument("--namespace", help="Kubernetes namespace")

        # Service Operations
        container_subparsers.add_parser("list-deployments", help="List deployments")
        container_subparsers.add_parser("list-services", help="List services")
        container_subparsers.add_parser("list-pods", help="List pods")

        logs_parser = container_subparsers.add_parser(
            "logs", help="View container logs"
        )
        logs_parser.add_argument("--service", help="Service name")
        logs_parser.add_argument("--pod", help="Pod name")
        logs_parser.add_argument(
            "--follow", "-f", action="store_true", help="Follow logs"
        )
        logs_parser.add_argument("--lines", type=int, help="Number of lines to show")

        # Registry Management
        registry_parser = container_subparsers.add_parser(
            "registry", help="Container registry operations"
        )
        registry_subparsers = registry_parser.add_subparsers(dest="registry_action")

        registry_subparsers.add_parser("list-repositories", help="List repositories")

        push_parser = registry_subparsers.add_parser(
            "push", help="Push container image"
        )
        push_parser.add_argument("image", help="Image name and tag")
        push_parser.add_argument("--repository", help="Target repository")

        pull_parser = registry_subparsers.add_parser(
            "pull", help="Pull container image"
        )
        pull_parser.add_argument("image", help="Image name and tag")

    def _add_infrastructure_commands(
        self, subparsers: argparse._SubParsersAction
    ) -> None:
        """Add infrastructure management commands."""
        infra_parser = subparsers.add_parser(
            "infra",
            help="Infrastructure management commands",
            description="Manage Terraform infrastructure and resources",
        )

        infra_subparsers = infra_parser.add_subparsers(dest="infra_action")

        # Terraform Operations
        plan_parser = infra_subparsers.add_parser(
            "plan", help="Plan infrastructure changes"
        )
        plan_parser.add_argument("--module", help="Specific module to plan")
        plan_parser.add_argument("--target", help="Specific resource to target")

        apply_parser = infra_subparsers.add_parser(
            "apply", help="Apply infrastructure changes"
        )
        apply_parser.add_argument("--module", help="Specific module to apply")
        apply_parser.add_argument(
            "--auto-approve", action="store_true", help="Auto-approve changes"
        )
        apply_parser.add_argument("--target", help="Specific resource to target")

        destroy_parser = infra_subparsers.add_parser(
            "destroy", help="Destroy infrastructure"
        )
        destroy_parser.add_argument("--module", help="Specific module to destroy")
        destroy_parser.add_argument("--target", help="Specific resource to target")
        destroy_parser.add_argument(
            "--auto-approve", action="store_true", help="Auto-approve destruction"
        )

        infra_subparsers.add_parser("status", help="Show infrastructure status")
        infra_subparsers.add_parser("validate", help="Validate Terraform configuration")
        infra_subparsers.add_parser("init", help="Initialize Terraform")

        # Cost Management
        cost_parser = infra_subparsers.add_parser(
            "cost", help="Infrastructure cost analysis"
        )
        cost_subparsers = cost_parser.add_subparsers(dest="cost_action")
        cost_subparsers.add_parser("estimate", help="Estimate costs")
        cost_subparsers.add_parser("analyze", help="Analyze current costs")
        cost_subparsers.add_parser("optimize", help="Get cost optimization suggestions")

    def _add_agent_commands(self, subparsers: argparse._SubParsersAction) -> None:
        """Add agent management commands."""
        agent_parser = subparsers.add_parser(
            "agent",
            help="Agent management commands",
            description="Manage Genesis agents, agent-cage, and claude-talk",
        )

        agent_subparsers = agent_parser.add_subparsers(dest="agent_action")

        # Agent Operations
        start_parser = agent_subparsers.add_parser("start", help="Start agents")
        start_parser.add_argument("--type", required=True, help="Agent type")
        start_parser.add_argument(
            "--count", type=int, default=1, help="Number of agents"
        )
        start_parser.add_argument("--environment", help="Agent environment")

        stop_parser = agent_subparsers.add_parser("stop", help="Stop agents")
        stop_parser.add_argument("--type", help="Agent type")
        stop_parser.add_argument("--id", help="Specific agent ID")
        stop_parser.add_argument("--all", action="store_true", help="Stop all agents")

        agent_subparsers.add_parser("status", help="Show agent status")
        agent_subparsers.add_parser("list", help="List all agents")

        # Migration Commands
        migrate_parser = agent_subparsers.add_parser(
            "migrate", help="Migrate agents between systems"
        )
        migrate_parser.add_argument("--from", required=True, help="Source system")
        migrate_parser.add_argument("--to", required=True, help="Target system")
        migrate_parser.add_argument(
            "--agent-types", nargs="+", help="Specific agent types to migrate"
        )
        migrate_parser.add_argument(
            "--batch-size", type=int, default=5, help="Migration batch size"
        )

        # Agent-Cage Commands
        cage_parser = agent_subparsers.add_parser("cage", help="Agent-cage management")
        cage_subparsers = cage_parser.add_subparsers(dest="cage_action")
        cage_subparsers.add_parser("status", help="Agent-cage status")
        cage_subparsers.add_parser("restart", help="Restart agent-cage")
        cage_subparsers.add_parser("logs", help="View agent-cage logs")

        # Claude-Talk Commands
        claude_parser = agent_subparsers.add_parser(
            "claude-talk", help="Claude-talk MCP server management"
        )
        claude_subparsers = claude_parser.add_subparsers(dest="claude_action")
        claude_subparsers.add_parser("status", help="Claude-talk status")
        claude_subparsers.add_parser("sessions", help="List active sessions")
        claude_subparsers.add_parser("restart", help="Restart claude-talk")
        claude_subparsers.add_parser("logs", help="View claude-talk logs")

    def format_output(self, data: Any, format_type: str) -> str:
        """Format output according to specified format."""
        if format_type == "json":
            return json.dumps(data, indent=2)
        elif format_type == "yaml":
            import yaml

            return yaml.dump(data, default_flow_style=False)
        elif format_type == "table":
            # Simple table formatting
            if isinstance(data, list) and data and isinstance(data[0], dict):
                headers = list(data[0].keys())
                rows = [headers]
                rows.extend([list(item.values()) for item in data])

                # Calculate column widths
                col_widths = [
                    max(len(str(row[i])) for row in rows) for i in range(len(headers))
                ]

                # Format table
                result = []
                for i, row in enumerate(rows):
                    formatted_row = " | ".join(
                        str(row[j]).ljust(col_widths[j]) for j in range(len(row))
                    )
                    result.append(formatted_row)
                    if i == 0:  # Add separator after header
                        result.append("-" * len(formatted_row))

                return "\n".join(result)
            else:
                return str(data)
        else:  # text format
            return str(data)

    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI with given arguments."""
        try:
            parser = self.create_parser()
            parsed_args = parser.parse_args(args)

            # Configure logging level
            if parsed_args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)

            # Update configuration from arguments
            if parsed_args.environment:
                self.environment = parsed_args.environment
            if parsed_args.project_id:
                self.project_id = parsed_args.project_id

            # Load configuration
            config = self.load_config()

            # Route to appropriate command handler
            if not parsed_args.command:
                parser.print_help()
                return 1

            # Execute command
            result = self._execute_command(parsed_args, config)

            # Format and print output
            if result is not None:
                formatted_output = self.format_output(result, parsed_args.output)
                print(formatted_output)

            return 0

        except GenesisCliError as e:
            logger.error(f"Genesis CLI Error: {e}")
            return 1
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 130
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if parsed_args.verbose:
                raise
            return 1

    def _execute_command(self, args: argparse.Namespace, config: Dict[str, Any]) -> Any:
        """Execute the appropriate command based on arguments."""
        if args.command == "vm":
            return self.vm_commands.execute(args, config)
        elif args.command == "container":
            return self.container_commands.execute(args, config)
        elif args.command == "infra":
            return self.infrastructure_commands.execute(args, config)
        elif args.command == "agent":
            return self.agent_commands.execute(args, config)
        else:
            raise GenesisCliError(f"Unknown command: {args.command}")


def run() -> int:
    """Main entry point for the Genesis CLI."""
    cli = GenesisCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(run())
