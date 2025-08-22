#!/usr/bin/env python3
"""
CLI for Build Plan Management

Provides command-line interface for managing concurrent build plans,
agent assignments, and plan dependencies.
"""
# ruff: noqa: T201  # Print statements allowed in CLI module

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from solve.agent_coordinator import AgentCoordinator, KnowledgeBase
from solve.build_plan_manager import BuildPlanManager, PlanPriority, PlanStatus
from solve.models import Goal


class BuildPlanCLI:
    """Command-line interface for build plan management."""

    def __init__(self) -> None:
        self.build_manager: BuildPlanManager | None = None

    async def initialize(self) -> None:
        """Initialize the build plan manager."""
        knowledge_base = KnowledgeBase()
        agent_coordinator = AgentCoordinator(knowledge_base)
        self.build_manager = BuildPlanManager(agent_coordinator)

    def create_plan(self, args: Any) -> None:
        """Create a new build plan."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        priority = PlanPriority[args.priority.upper()]
        tags = set(args.tags.split(",")) if args.tags else set()
        workspace = Path(args.workspace) if args.workspace else None

        plan = self.build_manager.create_plan(
            name=args.name,
            description=args.description or "",
            priority=priority,
            parent_plan_id=args.parent,
            workspace_path=workspace,
            tags=tags,
        )

        print(f"✓ Created build plan: {plan.plan_id}")
        print(f"  Name: {plan.name}")
        print(f"  Priority: {plan.priority.name}")
        if plan.parent_plan_id:
            print(f"  Parent: {plan.parent_plan_id}")
        if plan.tags:
            print(f"  Tags: {', '.join(plan.tags)}")

    def add_goal(self, args: Any) -> None:
        """Add a goal to a build plan."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        # Parse success criteria
        criteria = []
        if args.criteria:
            criteria = [c.strip() for c in args.criteria.split(",")]

        # Parse constraints
        constraints = []
        if args.constraints:
            constraints = [c.strip() for c in args.constraints.split(",")]

        goal = Goal(
            description=args.description,
            success_criteria=criteria,
            constraints=constraints,
            context={},
        )

        success = self.build_manager.add_goal_to_plan(args.plan_id, goal)
        if success:
            print(f"✓ Added goal to plan {args.plan_id}")
            print(f"  Goal: {goal.description}")
            if criteria:
                print(f"  Success criteria: {', '.join(criteria)}")
        else:
            print(f"✗ Failed to add goal to plan {args.plan_id}")

    async def start_plan(self, args: Any) -> None:
        """Start executing a build plan."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        success = await self.build_manager.start_plan(args.plan_id)
        if success:
            print(f"✓ Started plan {args.plan_id}")
        else:
            print(f"✗ Failed to start plan {args.plan_id}")
            print("  Check dependencies and concurrent plan limits")

    async def suspend_plan(self, args: Any) -> None:
        """Suspend an active build plan."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        success = await self.build_manager.suspend_plan(args.plan_id)
        if success:
            print(f"✓ Suspended plan {args.plan_id}")
        else:
            print(f"✗ Failed to suspend plan {args.plan_id}")

    async def resume_plan(self, args: Any) -> None:
        """Resume a suspended build plan."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        success = await self.build_manager.resume_plan(args.plan_id)
        if success:
            print(f"✓ Resumed plan {args.plan_id}")
        else:
            print(f"✗ Failed to resume plan {args.plan_id}")

    def add_dependency(self, args: Any) -> None:
        """Add dependency between plans."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        success = self.build_manager.add_dependency(args.plan_id, args.depends_on)
        if success:
            print(f"✓ Added dependency: {args.plan_id} depends on {args.depends_on}")
        else:
            print("✗ Failed to add dependency (check for cycles)")

    async def reserve_agent(self, args: Any) -> None:
        """Reserve an agent for a plan."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        success = await self.build_manager.reserve_agent(
            args.plan_id,
            args.agent_name,
            args.exclusive,
        )
        if success:
            exclusive_text = " (exclusive)" if args.exclusive else ""
            print(
                f"✓ Reserved agent {args.agent_name} for plan {args.plan_id}{exclusive_text}"
            )
        else:
            print(f"✗ Failed to reserve agent {args.agent_name}")

    async def release_agent(self, args: Any) -> None:
        """Release an agent from a plan."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        await self.build_manager.release_agent(args.plan_id, args.agent_name)
        print(f"✓ Released agent {args.agent_name} from plan {args.plan_id}")

    def show_status(self, args: Any) -> None:
        """Show status of a specific plan or all plans."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        if args.plan_id:
            # Show specific plan
            status = self.build_manager.get_plan_status(args.plan_id)
            if not status:
                print(f"Plan {args.plan_id} not found")
                return

            self._print_plan_status(status, detailed=True)
        else:
            # Show all plans
            status_filter = None
            if args.filter_status:
                status_filter = PlanStatus[args.filter_status.upper()]

            plans = self.build_manager.list_plans(status_filter)
            if not plans:
                print("No plans found")
                return

            print(f"Found {len(plans)} plans:")
            print()

            for plan_status in plans:
                self._print_plan_status(plan_status, detailed=False)
                print()

    def _print_plan_status(
        self, status: dict[str, Any], detailed: bool = False
    ) -> None:
        """Print formatted plan status."""
        status_emoji = {
            "created": "🔵",
            "active": "🟢",
            "suspended": "🟡",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "⚫",
        }

        emoji = status_emoji.get(status["status"], "❓")
        print(f"{emoji} {status['name']} ({status['id']})")
        print(f"   Status: {status['status']} | Priority: {status['priority']}")

        if detailed:
            print(f"   Goals: {status['goals_count']}")
            print(f"   Active tasks: {status['active_tasks']}")
            print(f"   Completed tasks: {status['completed_tasks']}")

            if status["assigned_agents"]:
                print(f"   Agents: {', '.join(status['assigned_agents'])}")

            if status["dependencies"]:
                print(f"   Depends on: {', '.join(status['dependencies'])}")

            if status["child_plans"]:
                print(f"   Child plans: {', '.join(status['child_plans'])}")

            if status["tags"]:
                print(f"   Tags: {', '.join(status['tags'])}")

            # Timestamps
            import datetime

            created = datetime.datetime.fromtimestamp(status["created_at"])
            print(f"   Created: {created.strftime('%Y-%m-%d %H:%M:%S')}")

            if status["started_at"]:
                started = datetime.datetime.fromtimestamp(status["started_at"])
                print(f"   Started: {started.strftime('%Y-%m-%d %H:%M:%S')}")

            if status["completed_at"]:
                completed = datetime.datetime.fromtimestamp(status["completed_at"])
                print(f"   Completed: {completed.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            # Compact view
            info_parts = []
            if status["goals_count"]:
                info_parts.append(f"{status['goals_count']} goals")
            if status["assigned_agents"]:
                info_parts.append(f"{len(status['assigned_agents'])} agents")
            if status["dependencies"]:
                info_parts.append(f"deps: {len(status['dependencies'])}")

            if info_parts:
                print(f"   {' | '.join(info_parts)}")

    def show_agents(self, args: Any) -> None:
        """Show agent workload and assignments."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        workload = self.build_manager.get_agent_workload()

        if not workload:
            print("No agents currently assigned to plans")
            return

        print("Agent Workload:")
        print()

        for agent_name, info in workload.items():
            exclusive_count = len(info["exclusive_reservations"])
            total_count = info["total_assignments"]

            status_text = f"({total_count} assignments"
            if exclusive_count:
                status_text += f", {exclusive_count} exclusive"
            status_text += ")"

            print(f"🤖 {agent_name} {status_text}")

            for plan_info in info["active_plans"]:
                plan_name = plan_info["plan_name"]
                plan_id = plan_info["plan_id"]
                priority = plan_info["priority"]
                exclusive = " [EXCLUSIVE]" if plan_info["is_exclusive"] else ""

                print(f"   • {plan_name} ({plan_id}) - {priority}{exclusive}")

            print()

    def export_plans(self, args: Any) -> None:
        """Export plans to JSON file."""
        if not self.build_manager:
            print("Error: Build manager not initialized")
            return

        plans = self.build_manager.list_plans()

        export_data = {
            "export_timestamp": int(asyncio.get_event_loop().time()),
            "plans": plans,
            "agent_workload": self.build_manager.get_agent_workload(),
        }

        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"✓ Exported {len(plans)} plans to {output_path}")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Build Plan Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new plan
  python -m solve.cli_build_plans create "Feature X Implementation" \\
      --priority high --tags "frontend,api"

  # Add a goal to a plan
  python -m solve.cli_build_plans add-goal abc123 "Create user authentication system"

  # Start a plan
  python -m solve.cli_build_plans start abc123

  # Reserve an agent exclusively for a plan
  python -m solve.cli_build_plans reserve-agent abc123 structure_agent --exclusive

  # Show all active plans
  python -m solve.cli_build_plans status --filter active

  # Show agent workload
  python -m solve.cli_build_plans agents
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create plan
    create_parser = subparsers.add_parser("create", help="Create a new build plan")
    create_parser.add_argument("name", help="Plan name")
    create_parser.add_argument("--description", help="Plan description")
    create_parser.add_argument(
        "--priority",
        choices=["low", "medium", "high", "critical"],
        default="medium",
        help="Plan priority",
    )
    create_parser.add_argument("--parent", help="Parent plan ID")
    create_parser.add_argument("--workspace", help="Workspace directory path")
    create_parser.add_argument("--tags", help="Comma-separated tags")

    # Add goal
    goal_parser = subparsers.add_parser("add-goal", help="Add a goal to a plan")
    goal_parser.add_argument("plan_id", help="Plan ID")
    goal_parser.add_argument("description", help="Goal description")
    goal_parser.add_argument("--criteria", help="Comma-separated success criteria")
    goal_parser.add_argument("--constraints", help="Comma-separated constraints")

    # Start plan
    start_parser = subparsers.add_parser("start", help="Start executing a plan")
    start_parser.add_argument("plan_id", help="Plan ID to start")

    # Suspend plan
    suspend_parser = subparsers.add_parser("suspend", help="Suspend an active plan")
    suspend_parser.add_argument("plan_id", help="Plan ID to suspend")

    # Resume plan
    resume_parser = subparsers.add_parser("resume", help="Resume a suspended plan")
    resume_parser.add_argument("plan_id", help="Plan ID to resume")

    # Add dependency
    dep_parser = subparsers.add_parser(
        "add-dependency", help="Add dependency between plans"
    )
    dep_parser.add_argument("plan_id", help="Plan ID that depends on another")
    dep_parser.add_argument("depends_on", help="Plan ID that this plan depends on")

    # Reserve agent
    reserve_parser = subparsers.add_parser(
        "reserve-agent", help="Reserve an agent for a plan"
    )
    reserve_parser.add_argument("plan_id", help="Plan ID")
    reserve_parser.add_argument("agent_name", help="Agent name to reserve")
    reserve_parser.add_argument(
        "--exclusive",
        action="store_true",
        help="Reserve agent exclusively",
    )

    # Release agent
    release_parser = subparsers.add_parser(
        "release-agent", help="Release an agent from a plan"
    )
    release_parser.add_argument("plan_id", help="Plan ID")
    release_parser.add_argument("agent_name", help="Agent name to release")

    # Status
    status_parser = subparsers.add_parser("status", help="Show plan status")
    status_parser.add_argument("plan_id", nargs="?", help="Specific plan ID to show")
    status_parser.add_argument(
        "--filter",
        dest="filter_status",
        choices=["created", "active", "suspended", "completed", "failed"],
        help="Filter plans by status",
    )

    # Agents
    subparsers.add_parser("agents", help="Show agent workload")

    # Export
    export_parser = subparsers.add_parser("export", help="Export plans to JSON")
    export_parser.add_argument("output", help="Output file path")

    return parser


async def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = BuildPlanCLI()
    await cli.initialize()

    # Dispatch to appropriate handler
    command_handlers = {
        "create": cli.create_plan,
        "add-goal": cli.add_goal,
        "start": cli.start_plan,
        "suspend": cli.suspend_plan,
        "resume": cli.resume_plan,
        "add-dependency": cli.add_dependency,
        "reserve-agent": cli.reserve_agent,
        "release-agent": cli.release_agent,
        "status": cli.show_status,
        "agents": cli.show_agents,
        "export": cli.export_plans,
    }

    handler = command_handlers.get(args.command)
    if handler:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(args)
            else:
                handler(args)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
