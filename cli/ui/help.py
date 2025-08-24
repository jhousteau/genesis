"""
Help System - Accessible Interactive Help
Provides comprehensive help with tutorials and contextual guidance.
"""

import argparse
import textwrap
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HelpExample:
    """Structure for help examples."""

    command: str
    description: str
    output_sample: Optional[str] = None


@dataclass
class HelpTopic:
    """Structure for help topics."""

    title: str
    description: str
    content: str
    examples: List[HelpExample]
    related_topics: List[str]
    see_also: List[str]


class HelpSystem:
    """
    Accessible help system following REACT methodology.

    R - Responsive: Help adapts to terminal width and user skill level
    E - Efficient: Fast help lookup with contextual suggestions
    A - Accessible: Clear structure with progressive disclosure
    C - Connected: Integrates with Genesis commands and ecosystem
    T - Tested: Comprehensive help coverage with examples
    """

    def __init__(self, terminal_adapter=None, color_scheme=None):
        self.terminal_adapter = terminal_adapter
        self.color_scheme = color_scheme
        self._help_database: Dict[str, HelpTopic] = {}
        self._command_hierarchy: Dict[str, List[str]] = {}
        self._initialize_help_database()

    def _initialize_help_database(self) -> None:
        """Initialize comprehensive help database."""

        # VM Management Help
        self._help_database["vm"] = HelpTopic(
            title="VM Management",
            description="Manage Genesis agent VM pools and infrastructure",
            content="""
Genesis VM management provides comprehensive agent VM pool operations including:

• VM Pool Management: Create, scale, and manage agent VM pools
• Lifecycle Operations: Start, stop, restart VMs and pools
• Health Monitoring: Check VM health and performance metrics
• Template Management: Manage VM templates and configurations
• Autoscaling: Configure automatic scaling based on demand

VM pools are organized by agent types (backend-developer, frontend-developer, etc.)
and provide isolated environments for different types of development work.
            """.strip(),
            examples=[
                HelpExample(
                    "g vm create-pool --type backend-developer --size 3",
                    "Create a pool of 3 backend developer VMs",
                ),
                HelpExample(
                    "g vm scale-pool backend-pool --min 1 --max 10 --enable-autoscaling",
                    "Configure autoscaling for backend pool",
                ),
                HelpExample(
                    "g vm health-check --pool backend-pool",
                    "Check health status of backend pool",
                ),
                HelpExample(
                    "g vm list-instances", "List all VM instances across pools"
                ),
            ],
            related_topics=["container", "agent", "infrastructure"],
            see_also=["g container", "g agent", "g infra"],
        )

        # Container Management Help
        self._help_database["container"] = HelpTopic(
            title="Container Orchestration",
            description="Manage GKE clusters, deployments, and services",
            content="""
Genesis container orchestration provides comprehensive Kubernetes management:

• Cluster Management: Create and manage GKE clusters
• Service Deployment: Deploy agent-cage, claude-talk, and custom services
• Scaling Operations: Scale deployments and manage resources
• Registry Operations: Manage container images and repositories
• Monitoring: View logs, status, and performance metrics

Container services run in GKE clusters with automatic load balancing,
health checks, and integration with Genesis monitoring systems.
            """.strip(),
            examples=[
                HelpExample(
                    "g container create-cluster genesis-dev --autopilot",
                    "Create a new Autopilot GKE cluster",
                ),
                HelpExample(
                    "g container deploy --service agent-cage --replicas 3",
                    "Deploy agent-cage service with 3 replicas",
                ),
                HelpExample(
                    "g container scale --deployment claude-talk --replicas 5",
                    "Scale claude-talk deployment to 5 replicas",
                ),
                HelpExample(
                    "g container logs --service agent-cage --follow",
                    "Follow logs from agent-cage service",
                ),
            ],
            related_topics=["vm", "agent", "infrastructure"],
            see_also=["g vm", "g agent", "g infra"],
        )

        # Infrastructure Management Help
        self._help_database["infra"] = HelpTopic(
            title="Infrastructure Management",
            description="Manage Terraform infrastructure and resources",
            content="""
Genesis infrastructure management provides Terraform-based operations:

• Terraform Operations: Plan, apply, and destroy infrastructure
• Module Management: Work with modular infrastructure components
• Cost Management: Analyze and optimize infrastructure costs
• State Management: Handle Terraform state and backend configuration
• Validation: Validate infrastructure configurations and dependencies

Infrastructure is organized into modules (vm-management, container-orchestration,
networking, security) that can be managed independently or together.
            """.strip(),
            examples=[
                HelpExample(
                    "g infra plan --module vm-management --environment dev",
                    "Plan VM infrastructure changes for dev environment",
                ),
                HelpExample(
                    "g infra apply --module container-orchestration",
                    "Apply container infrastructure changes",
                ),
                HelpExample("g infra cost estimate", "Estimate infrastructure costs"),
                HelpExample(
                    "g infra status --all", "Show status of all infrastructure modules"
                ),
            ],
            related_topics=["vm", "container", "cost"],
            see_also=["g vm", "g container", "terraform"],
        )

        # Agent Management Help
        self._help_database["agent"] = HelpTopic(
            title="Agent Management",
            description="Manage Genesis agents, agent-cage, and claude-talk",
            content="""
Genesis agent management provides comprehensive agent operations:

• Agent Operations: Start, stop, and manage specialized agents
• Migration Support: Migrate agents between systems and platforms
• Agent-Cage Management: Manage the agent containerization system
• Claude-Talk Integration: Manage MCP server for agent communication
• Session Management: Handle agent sessions and workload distribution

Agents are specialized for different roles (backend-developer, frontend-developer,
platform-engineer, etc.) and can run on VMs or in containers.
            """.strip(),
            examples=[
                HelpExample(
                    "g agent start --type backend-developer --count 2",
                    "Start 2 backend developer agents",
                ),
                HelpExample(
                    "g agent migrate --from legacy --to agent-cage",
                    "Migrate agents from legacy system to agent-cage",
                ),
                HelpExample(
                    "g agent status --all", "Show status of all agents and systems"
                ),
                HelpExample(
                    "g agent claude-talk sessions", "List active claude-talk sessions"
                ),
            ],
            related_topics=["vm", "container", "migration"],
            see_also=["g vm", "g container"],
        )

        # Quick Start Help
        self._help_database["quickstart"] = HelpTopic(
            title="Quick Start Guide",
            description="Get started with Genesis CLI quickly",
            content="""
Genesis CLI Quick Start:

1. SETUP ENVIRONMENT
   Set your GCP project and environment variables:
   export PROJECT_ID=your-project-id
   export ENVIRONMENT=dev

2. INITIALIZE INFRASTRUCTURE
   Bootstrap your Genesis infrastructure:
   g infra plan --module bootstrap
   g infra apply --module bootstrap

3. CREATE VM POOL
   Create your first agent VM pool:
   g vm create-pool --type backend-developer --size 2

4. DEPLOY CONTAINERS
   Set up container orchestration:
   g container create-cluster genesis-dev --autopilot
   g container deploy --service agent-cage

5. START AGENTS
   Launch your first agents:
   g agent start --type backend-developer --count 2

6. VERIFY SETUP
   Check system status:
   g vm health-check
   g container list-pods
   g agent status
            """.strip(),
            examples=[
                HelpExample("g --help", "Show main help menu"),
                HelpExample("g vm --help", "Show VM management help"),
                HelpExample("g infra status --all", "Check infrastructure status"),
            ],
            related_topics=["vm", "container", "agent", "infrastructure"],
            see_also=["g vm", "g container", "g agent", "g infra"],
        )

        # Troubleshooting Help
        self._help_database["troubleshooting"] = HelpTopic(
            title="Troubleshooting Guide",
            description="Common issues and solutions",
            content="""
Common Genesis CLI issues and solutions:

AUTHENTICATION ISSUES:
• Ensure gcloud is authenticated: gcloud auth login
• Check service account: gcloud auth list
• Verify project access: gcloud projects list

VM ISSUES:
• Check quotas: gcloud compute project-info describe
• Verify zones: gcloud compute zones list
• Check instance status: g vm health-check

CONTAINER ISSUES:
• Check cluster status: g container list-clusters
• Verify kubectl config: kubectl config current-context
• Check pod logs: g container logs --service <service>

PERMISSION ISSUES:
• Verify IAM roles: gcloud projects get-iam-policy PROJECT_ID
• Check service accounts: gcloud iam service-accounts list
• Review organization policies

PERFORMANCE ISSUES:
• Check resource usage: g vm health-check
• Monitor container metrics: g container list-pods
• Review cost analysis: g infra cost analyze
            """.strip(),
            examples=[
                HelpExample(
                    "g vm health-check --verbose", "Detailed VM health diagnostic"
                ),
                HelpExample(
                    "g container logs --service agent-cage --lines 100",
                    "Check recent container logs",
                ),
                HelpExample(
                    "g infra status --all --verbose", "Detailed infrastructure status"
                ),
            ],
            related_topics=["vm", "container", "infrastructure", "debugging"],
            see_also=["g vm health-check", "g container logs", "g infra status"],
        )

        # Set up command hierarchy
        self._command_hierarchy = {
            "vm": [
                "create-pool",
                "scale-pool",
                "health-check",
                "list-pools",
                "start",
                "stop",
                "restart",
            ],
            "container": [
                "create-cluster",
                "deploy",
                "scale",
                "logs",
                "list-deployments",
                "list-services",
            ],
            "infra": ["plan", "apply", "destroy", "status", "validate", "cost"],
            "agent": ["start", "stop", "status", "migrate", "cage", "claude-talk"],
        }

    def get_command_help(
        self, command_path: List[str], parser: Optional[argparse.ArgumentParser] = None
    ) -> str:
        """Get help for specific command path."""

        if not command_path:
            return self.get_main_help()

        main_command = command_path[0]

        # Check if we have dedicated help for this command
        if main_command in self._help_database:
            help_topic = self._help_database[main_command]
            return self._format_help_topic(help_topic)

        # Fall back to parser help if available
        if parser:
            return parser.format_help()

        # Generate basic help
        return self._generate_basic_help(command_path)

    def get_main_help(self) -> str:
        """Get main help overview."""
        help_text = []

        if self.color_scheme:
            title = self.color_scheme.colorize(
                "Genesis Universal Infrastructure Platform CLI", "primary", "bold"
            )
            help_text.append(title)
        else:
            help_text.append("Genesis Universal Infrastructure Platform CLI")

        help_text.append("")
        help_text.append("DESCRIPTION")
        help_text.append(
            "  Comprehensive infrastructure management platform providing VM pools,"
        )
        help_text.append(
            "  container orchestration, agent management, and infrastructure automation."
        )
        help_text.append("")

        help_text.append("MAIN COMMANDS")
        main_commands = [
            ("vm", "Manage agent VM pools and infrastructure"),
            ("container", "Manage GKE clusters and container services"),
            ("infra", "Manage Terraform infrastructure and resources"),
            ("agent", "Manage Genesis agents and communication systems"),
        ]

        for cmd, desc in main_commands:
            if self.color_scheme:
                formatted_cmd = self.color_scheme.format_command(f"g {cmd}")
                help_text.append(f"  {formatted_cmd:<20} {desc}")
            else:
                help_text.append(f"  g {cmd:<18} {desc}")

        help_text.append("")
        help_text.append("GETTING STARTED")
        help_text.append(f"  g help quickstart    Quick start guide")
        help_text.append(f"  g help troubleshooting    Common issues and solutions")
        help_text.append(f"  g <command> --help    Detailed command help")

        help_text.append("")
        help_text.append("EXAMPLES")
        examples = [
            "g vm create-pool --type backend-developer --size 3",
            "g container deploy --service agent-cage",
            "g infra plan --module vm-management",
            "g agent start --type backend-developer",
        ]

        for i, example in enumerate(examples, 1):
            if self.color_scheme:
                formatted_example = self.color_scheme.format_command(example)
                help_text.append(f"  {i}. {formatted_example}")
            else:
                help_text.append(f"  {i}. {example}")

        return "\n".join(help_text)

    def get_topic_help(self, topic: str) -> str:
        """Get help for specific topic."""
        if topic in self._help_database:
            help_topic = self._help_database[topic]
            return self._format_help_topic(help_topic)
        else:
            available_topics = list(self._help_database.keys())
            return f"Help topic '{topic}' not found. Available topics: {', '.join(available_topics)}"

    def suggest_commands(
        self, partial_command: str, context: Optional[str] = None
    ) -> List[str]:
        """Suggest commands based on partial input."""
        suggestions = []

        # Check main commands
        main_commands = ["vm", "container", "infra", "agent"]
        for cmd in main_commands:
            if cmd.startswith(partial_command.lower()):
                suggestions.append(f"g {cmd}")

        # Check subcommands if context is provided
        if context and context in self._command_hierarchy:
            for subcmd in self._command_hierarchy[context]:
                if subcmd.startswith(partial_command.lower()):
                    suggestions.append(f"g {context} {subcmd}")

        # Check help topics
        for topic in self._help_database.keys():
            if topic.startswith(partial_command.lower()):
                suggestions.append(f"g help {topic}")

        return suggestions[:10]  # Limit to top 10 suggestions

    def get_contextual_help(
        self, error_message: str, command_context: Optional[List[str]] = None
    ) -> str:
        """Get contextual help based on error message."""
        help_suggestions = []

        # Analyze error message for common patterns
        if "permission" in error_message.lower() or "access" in error_message.lower():
            help_suggestions.extend(
                [
                    "Check your GCP authentication: gcloud auth list",
                    "Verify project permissions: gcloud projects get-iam-policy PROJECT_ID",
                    "See troubleshooting guide: g help troubleshooting",
                ]
            )

        elif "quota" in error_message.lower():
            help_suggestions.extend(
                [
                    "Check compute quotas: gcloud compute project-info describe",
                    "Request quota increase: https://cloud.google.com/compute/quotas",
                    "Consider using different zones: g vm create-pool --zones us-central1-b",
                ]
            )

        elif "not found" in error_message.lower():
            if command_context and len(command_context) > 0:
                suggestions = self.suggest_commands(command_context[-1])
                if suggestions:
                    help_suggestions.append(
                        f"Did you mean: {', '.join(suggestions[:3])}"
                    )

        # Add general help
        help_suggestions.extend(
            [
                f"Get command help: g {' '.join(command_context or [])} --help",
                "View troubleshooting guide: g help troubleshooting",
            ]
        )

        return "\n".join(f"  • {suggestion}" for suggestion in help_suggestions[:5])

    def _format_help_topic(self, topic: HelpTopic) -> str:
        """Format help topic with responsive design."""
        lines = []

        # Title
        if self.color_scheme:
            title = self.color_scheme.colorize(topic.title, "primary", "bold")
            lines.append(title)
        else:
            lines.append(topic.title)

        lines.append("=" * len(topic.title))
        lines.append("")

        # Description
        if self.color_scheme:
            description = self.color_scheme.colorize(topic.description, "info")
            lines.append(description)
        else:
            lines.append(topic.description)
        lines.append("")

        # Content
        content = self._wrap_text(topic.content)
        lines.extend(content.split("\n"))
        lines.append("")

        # Examples
        if topic.examples:
            if self.color_scheme:
                examples_title = self.color_scheme.colorize(
                    "EXAMPLES", "primary", "bold"
                )
                lines.append(examples_title)
            else:
                lines.append("EXAMPLES")
            lines.append("")

            for i, example in enumerate(topic.examples, 1):
                if self.color_scheme:
                    cmd = self.color_scheme.format_command(example.command)
                    lines.append(f"  {i}. {cmd}")
                    lines.append(f"     {example.description}")
                else:
                    lines.append(f"  {i}. {example.command}")
                    lines.append(f"     {example.description}")

                if example.output_sample:
                    lines.append(f"     Output: {example.output_sample}")
                lines.append("")

        # Related topics
        if topic.related_topics:
            if self.color_scheme:
                related_title = self.color_scheme.colorize(
                    "RELATED TOPICS", "primary", "bold"
                )
                lines.append(related_title)
            else:
                lines.append("RELATED TOPICS")
            lines.append(f"  {', '.join(topic.related_topics)}")
            lines.append("")

        # See also
        if topic.see_also:
            if self.color_scheme:
                see_also_title = self.color_scheme.colorize(
                    "SEE ALSO", "primary", "bold"
                )
                lines.append(see_also_title)
            else:
                lines.append("SEE ALSO")
            lines.append(f"  {', '.join(topic.see_also)}")

        return "\n".join(lines)

    def _generate_basic_help(self, command_path: List[str]) -> str:
        """Generate basic help for unknown commands."""
        cmd = " ".join(command_path)

        lines = [
            f"Command: g {cmd}",
            "",
            "No detailed help available for this command.",
            "",
            "Try:",
            f"  g {cmd} --help      (if the command supports --help)",
            f"  g --help           (for main menu)",
            f"  g help quickstart  (for getting started guide)",
        ]

        # Add suggestions if available
        if command_path:
            suggestions = self.suggest_commands(command_path[-1])
            if suggestions:
                lines.extend(
                    [
                        "",
                        "Similar commands:",
                        *[f"  {suggestion}" for suggestion in suggestions[:5]],
                    ]
                )

        return "\n".join(lines)

    def _wrap_text(self, text: str) -> str:
        """Wrap text to terminal width."""
        if self.terminal_adapter:
            width = min(80, self.terminal_adapter.width - 4)  # Leave margin
        else:
            width = 76

        paragraphs = text.split("\n\n")
        wrapped_paragraphs = []

        for paragraph in paragraphs:
            if paragraph.strip().startswith("•"):
                # Handle bullet points specially
                lines = paragraph.split("\n")
                wrapped_lines = []
                for line in lines:
                    if line.strip().startswith("•"):
                        wrapped = textwrap.fill(line, width, subsequent_indent="  ")
                        wrapped_lines.append(wrapped)
                    else:
                        wrapped = textwrap.fill(line, width)
                        wrapped_lines.append(wrapped)
                wrapped_paragraphs.append("\n".join(wrapped_lines))
            else:
                wrapped = textwrap.fill(paragraph, width)
                wrapped_paragraphs.append(wrapped)

        return "\n\n".join(wrapped_paragraphs)
