"""
Build Plan Management System for SOLVE

Manages concurrent build plans with agent isolation, dependency tracking,
and hierarchical plan coordination to prevent agent confusion.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from solve.agent_coordinator import AgentCoordinator
from solve.models import AgentTask, Goal, Result

logger = logging.getLogger(__name__)


class PlanStatus(Enum):
    """Status of a build plan."""

    CREATED = "created"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanPriority(Enum):
    """Priority levels for build plans."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class BuildPlan:
    """Represents a build plan with goals, status, and agent assignments."""

    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    status: PlanStatus = PlanStatus.CREATED
    priority: PlanPriority = PlanPriority.MEDIUM

    # Goals and tasks
    goals: list[Goal] = field(default_factory=list)
    active_tasks: list[AgentTask] = field(default_factory=list)
    completed_tasks: list[AgentTask] = field(default_factory=list)

    # Agent assignments
    assigned_agents: set[str] = field(default_factory=set)
    reserved_agents: set[str] = field(default_factory=set)

    # Dependency management
    parent_plan_id: str | None = None
    child_plan_ids: set[str] = field(default_factory=set)
    dependencies: set[str] = field(
        default_factory=set
    )  # Other plan IDs this depends on

    # Execution context
    workspace_path: Path | None = None
    isolation_context: dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    tags: set[str] = field(default_factory=set)

    def can_start(self, completed_plans: set[str]) -> bool:
        """Check if plan can start based on dependencies."""
        return self.dependencies.issubset(completed_plans)

    def add_child_plan(self, child_plan_id: str) -> None:
        """Add a child plan."""
        self.child_plan_ids.add(child_plan_id)

    def reserve_agent(self, agent_name: str) -> None:
        """Reserve an agent for exclusive use."""
        self.reserved_agents.add(agent_name)
        self.assigned_agents.add(agent_name)

    def release_agent(self, agent_name: str) -> None:
        """Release an agent reservation."""
        self.reserved_agents.discard(agent_name)
        self.assigned_agents.discard(agent_name)


@dataclass
class AgentAssignment:
    """Tracks agent assignment to build plans."""

    agent_name: str
    plan_id: str
    is_exclusive: bool = False  # If True, agent can't work on other plans
    assigned_at: float = field(default_factory=time.time)


class BuildPlanManager:
    """Manages concurrent build plans with agent coordination."""

    def __init__(
        self, agent_coordinator: AgentCoordinator, max_concurrent_plans: int = 5
    ):
        self.agent_coordinator = agent_coordinator
        self.max_concurrent_plans = max_concurrent_plans

        # Plan storage
        self.plans: dict[str, BuildPlan] = {}
        self.active_plans: set[str] = set()
        self.completed_plans: set[str] = set()

        # Agent management
        self.agent_assignments: dict[str, list[AgentAssignment]] = {}
        self.agent_locks = asyncio.Lock()

        # Execution coordination
        self.plan_execution_tasks: dict[str, asyncio.Task[Result]] = {}
        self.dependency_graph: dict[str, set[str]] = {}

    def create_plan(
        self,
        name: str,
        description: str = "",
        priority: PlanPriority = PlanPriority.MEDIUM,
        parent_plan_id: str | None = None,
        workspace_path: Path | None = None,
        tags: set[str] | None = None,
    ) -> BuildPlan:
        """Create a new build plan."""

        plan = BuildPlan(
            name=name,
            description=description,
            priority=priority,
            parent_plan_id=parent_plan_id,
            workspace_path=workspace_path,
            tags=tags or set(),
        )

        # Set up parent-child relationships
        if parent_plan_id and parent_plan_id in self.plans:
            self.plans[parent_plan_id].add_child_plan(plan.plan_id)

        self.plans[plan.plan_id] = plan
        logger.info(f"Created build plan {plan.plan_id}: {name}")

        return plan

    def add_goal_to_plan(self, plan_id: str, goal: Goal) -> bool:
        """Add a goal to an existing plan."""
        if plan_id not in self.plans:
            logger.error(f"Plan {plan_id} not found")
            return False

        plan = self.plans[plan_id]
        if plan.status in [
            PlanStatus.COMPLETED,
            PlanStatus.FAILED,
            PlanStatus.CANCELLED,
        ]:
            logger.error(f"Cannot add goal to {plan.status.value} plan {plan_id}")
            return False

        plan.goals.append(goal)
        logger.info(f"Added goal to plan {plan_id}: {goal.description}")
        return True

    def add_dependency(self, plan_id: str, depends_on: str) -> bool:
        """Add a dependency between plans."""
        if plan_id not in self.plans or depends_on not in self.plans:
            logger.error(f"Invalid plan IDs for dependency: {plan_id} -> {depends_on}")
            return False

        # Check for circular dependencies
        if self._would_create_cycle(plan_id, depends_on):
            logger.error(
                f"Cannot add dependency {plan_id} -> {depends_on}: would create cycle"
            )
            return False

        self.plans[plan_id].dependencies.add(depends_on)
        self.dependency_graph.setdefault(depends_on, set()).add(plan_id)
        logger.info(f"Added dependency: {plan_id} depends on {depends_on}")
        return True

    def _would_create_cycle(self, plan_id: str, depends_on: str) -> bool:
        """Check if adding dependency would create a circular dependency."""
        visited = set()

        def has_path(current: str, target: str) -> bool:
            if current == target:
                return True
            if current in visited:
                return False

            visited.add(current)
            for dependent in self.dependency_graph.get(current, set()):
                if has_path(dependent, target):
                    return True
            return False

        return has_path(depends_on, plan_id)

    async def reserve_agent(
        self, plan_id: str, agent_name: str, exclusive: bool = False
    ) -> bool:
        """Reserve an agent for a plan."""
        async with self.agent_locks:
            if plan_id not in self.plans:
                logger.error(f"Plan {plan_id} not found")
                return False

            # Check if agent is already exclusively reserved
            for assignments in self.agent_assignments.values():
                for assignment in assignments:
                    if assignment.agent_name == agent_name and assignment.is_exclusive:
                        logger.warning(
                            f"Agent {agent_name} exclusively reserved by {assignment.plan_id}",
                        )
                        return False

            # Create assignment
            assignment = AgentAssignment(
                agent_name=agent_name,
                plan_id=plan_id,
                is_exclusive=exclusive,
            )

            self.agent_assignments.setdefault(plan_id, []).append(assignment)
            self.plans[plan_id].reserve_agent(agent_name)

            logger.info(
                f"Reserved agent {agent_name} for plan {plan_id} (exclusive: {exclusive})"
            )
            return True

    async def release_agent(self, plan_id: str, agent_name: str) -> None:
        """Release an agent from a plan."""
        async with self.agent_locks:
            if plan_id in self.agent_assignments:
                self.agent_assignments[plan_id] = [
                    a
                    for a in self.agent_assignments[plan_id]
                    if a.agent_name != agent_name
                ]

            if plan_id in self.plans:
                self.plans[plan_id].release_agent(agent_name)

            logger.info(f"Released agent {agent_name} from plan {plan_id}")

    async def start_plan(self, plan_id: str) -> bool:
        """Start executing a build plan."""
        if plan_id not in self.plans:
            logger.error(f"Plan {plan_id} not found")
            return False

        plan = self.plans[plan_id]

        # Check if we can start (dependencies satisfied)
        if not plan.can_start(self.completed_plans):
            missing_deps = plan.dependencies - self.completed_plans
            logger.warning(
                f"Plan {plan_id} cannot start - missing dependencies: {missing_deps}"
            )
            return False

        # Check concurrent plan limit
        if len(self.active_plans) >= self.max_concurrent_plans:
            logger.warning(
                f"Cannot start plan {plan_id} - max concurrent limit reached"
            )
            return False

        # Update plan status
        plan.status = PlanStatus.ACTIVE
        plan.started_at = time.time()
        self.active_plans.add(plan_id)

        # Start execution task
        execution_task = asyncio.create_task(self._execute_plan(plan))
        self.plan_execution_tasks[plan_id] = execution_task

        logger.info(f"Started plan {plan_id}: {plan.name}")
        return True

    async def _execute_plan(self, plan: BuildPlan) -> Result:
        """Execute all goals in a plan."""
        logger.info(f"Executing plan {plan.plan_id} with {len(plan.goals)} goals")

        all_results = []
        plan_artifacts = {}

        try:
            for i, goal in enumerate(plan.goals):
                logger.info(
                    f"Plan {plan.plan_id}: Executing goal {i + 1}/{len(plan.goals)}"
                )

                # Add plan context to goal
                goal.context["build_plan_id"] = plan.plan_id
                goal.context["plan_workspace"] = (
                    str(plan.workspace_path) if plan.workspace_path else None
                )
                goal.context["plan_isolation"] = plan.isolation_context

                # Execute goal with assigned agents
                assigned_agent_names = (
                    list(plan.assigned_agents) if plan.assigned_agents else None
                )
                result = await self.agent_coordinator.achieve_goal(
                    goal, assigned_agent_names
                )

                all_results.append(result)
                if result.artifacts:
                    plan_artifacts.update(result.artifacts)

                if not result.success:
                    logger.error(
                        f"Goal failed in plan {plan.plan_id}: {result.message}"
                    )
                    plan.status = PlanStatus.FAILED
                    break
            else:
                # All goals completed successfully
                plan.status = PlanStatus.COMPLETED
                plan.completed_at = time.time()

        except Exception as e:
            logger.error(f"Plan execution failed for {plan.plan_id}: {e}")
            plan.status = PlanStatus.FAILED
            all_results.append(
                Result(
                    success=False,
                    message=f"Plan execution error: {str(e)}",
                    artifacts={},
                    metadata={"error": str(e)},
                ),
            )
        finally:
            # Cleanup
            self.active_plans.discard(plan.plan_id)
            if plan.status == PlanStatus.COMPLETED:
                self.completed_plans.add(plan.plan_id)

            # Release all agents
            for agent_name in list(plan.assigned_agents):
                await self.release_agent(plan.plan_id, agent_name)

            # Remove execution task
            self.plan_execution_tasks.pop(plan.plan_id, None)

            # Start dependent plans
            await self._start_ready_dependent_plans(plan.plan_id)

        # Create final result
        overall_success = all(r.success for r in all_results)
        return Result(
            success=overall_success,
            message=f"Plan {plan.plan_id} {'completed' if overall_success else 'failed'}",
            artifacts=plan_artifacts,
            metadata={
                "plan_id": plan.plan_id,
                "goals_executed": len(all_results),
                "goals_successful": sum(1 for r in all_results if r.success),
                "execution_time": time.time() - (plan.started_at or plan.created_at),
            },
        )

    async def _start_ready_dependent_plans(self, completed_plan_id: str) -> None:
        """Start any plans that were waiting for this plan to complete."""
        if completed_plan_id not in self.dependency_graph:
            return

        for dependent_plan_id in self.dependency_graph[completed_plan_id]:
            if (
                dependent_plan_id in self.plans
                and self.plans[dependent_plan_id].status == PlanStatus.CREATED
            ):
                if self.plans[dependent_plan_id].can_start(self.completed_plans):
                    await self.start_plan(dependent_plan_id)

    async def suspend_plan(self, plan_id: str) -> bool:
        """Suspend an active plan."""
        if plan_id not in self.active_plans or plan_id not in self.plans:
            return False

        plan = self.plans[plan_id]
        plan.status = PlanStatus.SUSPENDED

        # Cancel execution task
        if plan_id in self.plan_execution_tasks:
            self.plan_execution_tasks[plan_id].cancel()

        self.active_plans.discard(plan_id)
        logger.info(f"Suspended plan {plan_id}")
        return True

    async def resume_plan(self, plan_id: str) -> bool:
        """Resume a suspended plan."""
        if plan_id not in self.plans:
            return False

        plan = self.plans[plan_id]
        if plan.status != PlanStatus.SUSPENDED:
            return False

        return await self.start_plan(plan_id)

    def get_plan_status(self, plan_id: str) -> dict[str, Any] | None:
        """Get detailed status of a plan."""
        if plan_id not in self.plans:
            return None

        plan = self.plans[plan_id]

        return {
            "id": plan.plan_id,
            "name": plan.name,
            "status": plan.status.value,
            "priority": plan.priority.value,
            "goals_count": len(plan.goals),
            "active_tasks": len(plan.active_tasks),
            "completed_tasks": len(plan.completed_tasks),
            "assigned_agents": list(plan.assigned_agents),
            "dependencies": list(plan.dependencies),
            "child_plans": list(plan.child_plan_ids),
            "created_at": plan.created_at,
            "started_at": plan.started_at,
            "completed_at": plan.completed_at,
            "tags": list(plan.tags),
        }

    def list_plans(
        self, status_filter: PlanStatus | None = None
    ) -> list[dict[str, Any]]:
        """List all plans with optional status filter."""
        plans = []
        for plan_id, plan in self.plans.items():
            if status_filter is None or plan.status == status_filter:
                status_info = self.get_plan_status(plan_id)
                if status_info:
                    plans.append(status_info)

        # Sort by priority and creation time
        return sorted(plans, key=lambda p: (p["priority"], p["created_at"]))

    def get_agent_workload(self) -> dict[str, dict[str, Any]]:
        """Get current workload for all agents."""
        workload = {}

        for plan_id, assignments in self.agent_assignments.items():
            plan = self.plans.get(plan_id)
            if not plan or plan.status not in [PlanStatus.ACTIVE, PlanStatus.SUSPENDED]:
                continue

            for assignment in assignments:
                agent_name = assignment.agent_name
                if agent_name not in workload:
                    workload[agent_name] = {
                        "active_plans": [],
                        "exclusive_reservations": [],
                        "total_assignments": 0,
                    }

                # Type casting to handle mypy dict access
                workload[agent_name]["active_plans"] = [
                    *workload[agent_name]["active_plans"],  # type: ignore[misc]
                    {
                        "plan_id": plan_id,
                        "plan_name": plan.name,
                        "priority": plan.priority.value,
                        "is_exclusive": assignment.is_exclusive,
                    },
                ]

                if assignment.is_exclusive:
                    workload[agent_name]["exclusive_reservations"] = [
                        *workload[agent_name]["exclusive_reservations"],  # type: ignore[misc]
                        plan_id,
                    ]

                workload[agent_name]["total_assignments"] = (
                    workload[agent_name]["total_assignments"] + 1  # type: ignore[operator]
                )

        return workload

    async def shutdown(self) -> None:
        """Shutdown the build plan manager."""
        logger.info("Shutting down build plan manager...")

        # Cancel all active execution tasks
        for task in self.plan_execution_tasks.values():
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.plan_execution_tasks:
            await asyncio.gather(
                *self.plan_execution_tasks.values(), return_exceptions=True
            )

        logger.info("Build plan manager shutdown complete")
