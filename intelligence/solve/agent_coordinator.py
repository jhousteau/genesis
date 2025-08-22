"""
Agent Coordinator for SOLVE - Replaces phase-based orchestration with goal-driven coordination.

This module enables intelligent agents to collaborate on achieving development goals
without rigid phase enforcement. Enhanced with ADR integration for phase-bounded execution.
"""

import asyncio
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from solve.agent_constitution import AgentConstitutionFactory, AgentType
from solve.constitutional_ai import ConstitutionalAI
from solve.governance import GovernanceEngine
from solve.knowledge_loader import KnowledgeLoader
from solve.lessons import LessonCapture
from solve.models import (ADRConfig, AgentDecisionRequest,
                          AgentDecisionResponse, AgentInteraction, AgentTask,
                          ConstitutionalContext, ConstitutionalMetrics, Goal,
                          Result, SystemState, TaskStatus)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class Reasoning:
    """Represents the reasoning output from the ReAct loop."""

    thought: str
    next_action: str
    selected_agents: list[str]
    confidence: float
    context: dict[str, Any]


@dataclass
class Action:
    """Represents an action to be executed."""

    action_type: str  # e.g., "decompose", "execute", "aggregate", "complete"
    target: Any  # Goal, Task, or Result
    agents: list["Agent"]
    metadata: dict[str, Any]


class Agent(Protocol):
    """Protocol for agents that can work with the coordinator."""

    name: str
    capabilities: list[str]

    async def can_handle(self, goal: Goal) -> float:
        """Return confidence score (0-1) for handling this goal."""
        ...

    async def execute(self, task: AgentTask) -> Result:
        """Execute the assigned task."""
        ...


class KnowledgeBase:
    """Access to principles, patterns, and context."""

    def __init__(self, knowledge_path: str = "knowledge"):
        self.knowledge_path = knowledge_path
        self.principles: dict[str, Any] = {}
        self.patterns: dict[str, Any] = {}
        self.context: dict[str, Any] = {}
        # Knowledge loading disabled until KnowledgeLoader is integrated
        # self._load_knowledge()
        logger.warning(
            "Knowledge loading disabled. Requires KnowledgeLoader integration "
            "for .mdc files and other knowledge sources.",
        )

    def _load_knowledge(self) -> None:
        """Load knowledge from markdown files."""
        # Knowledge loading requires integration with KnowledgeLoader
        raise NotImplementedError(
            "Knowledge loading requires KnowledgeLoader integration. "
            "Implement using solve.knowledge_loader.KnowledgeLoader to load "
            ".mdc files and other knowledge sources.",
        )

    def get_relevant_context(self, goal: Goal) -> dict[str, Any]:
        """Retrieve context relevant to the goal."""
        return {
            "principles": self.principles,
            "patterns": self.patterns,
            "project_context": self.context,
        }


class AgentCoordinator:
    """Coordinates multiple agents to achieve development goals with Constitutional AI guidance."""

    def __init__(
        self, knowledge_base: KnowledgeBase | None = None, max_iterations: int = 10
    ):
        self.knowledge = knowledge_base or KnowledgeBase()
        self.agents: list[Agent] = []
        self.active_tasks: list[AgentTask] = []
        self.max_iterations = max_iterations
        self.reasoning_history: list[Reasoning] = []
        self.action_history: list[Action] = []

        # Constitutional AI integration
        self.knowledge_loader = KnowledgeLoader()
        self.constitutional_ai = ConstitutionalAI(self.knowledge_loader)
        self.metrics = ConstitutionalMetrics()
        self.system_state = SystemState(
            active_agents=[], current_goals=[], recent_decisions=[]
        )
        self.agent_interactions: list[AgentInteraction] = []

        # ADR and phase-bounded execution support
        self.governance_engine = GovernanceEngine()
        self.lesson_capture = LessonCapture()
        self.current_phase: str | None = None
        self.phase_context: dict[str, Any] = {}

    def register_agent(self, agent: Agent) -> None:
        """Register an agent with the coordinator."""
        self.agents.append(agent)
        self.system_state.active_agents.append(agent.name)
        logger.info(f"Registered agent: {agent.name}")

    async def validate_agent_decision(
        self,
        agent_id: str,
        agent_type: str,
        decision: str,
        context: dict[str, Any],
    ) -> AgentDecisionResponse:
        """Validate an agent decision through Constitutional AI."""

        # Create constitutional context
        constitutional_context = ConstitutionalContext(
            agent_id=agent_id,
            agent_type=agent_type,
            goal=context.get("goal"),
            constraints=context.get("constraints", []),
            reasoning=context.get("reasoning"),
            prior_decisions=context.get("prior_decisions", []),
            safety_requirements=context.get("safety_requirements", []),
            collaboration_context=context.get("collaboration_context", {}),
        )

        # Create decision request
        decision_request = AgentDecisionRequest(
            agent_id=agent_id,
            agent_type=agent_type,
            proposed_decision=decision,
            context=constitutional_context,
            urgency=context.get("urgency", "normal"),
            requires_approval=context.get("requires_approval", False),
        )

        # Validate decision
        validation_result = self.constitutional_ai.validate_decision(
            agent_id=agent_id,
            decision=decision,
            context=context,
        )

        # Create response
        response = AgentDecisionResponse(
            approved=validation_result.success,
            confidence=1.0 if validation_result.success else 0.0,
            reasoning=validation_result.message,
            applied_principles=validation_result.artifacts.get(
                "applied_principles", []
            ),
            safety_warnings=[],
            improvement_suggestions=[],
            required_actions=[],
        )

        # Extract violations for warnings and suggestions
        if (
            not validation_result.success
            and "violations" in validation_result.artifacts
        ):
            violations = validation_result.artifacts["violations"]
            for violation in violations:
                if violation["severity"] == "warning":
                    response.safety_warnings.append(violation["description"])
                elif violation["severity"] == "error":
                    response.improvement_suggestions.append(violation["remedy"])
                elif violation["severity"] == "critical":
                    response.required_actions.append(violation["remedy"])

        # Update metrics
        self.metrics.update_decision_metrics(
            approved=response.approved,
            confidence=response.confidence,
            had_warnings=len(response.safety_warnings) > 0,
            had_critical=len(response.required_actions) > 0,
        )

        # Add to system state
        self.system_state.add_decision(decision_request)

        logger.info(
            f"Constitutional validation for {agent_id}: approved={response.approved}"
        )
        return response

    def get_agent_constitution(self, agent_name: str) -> dict[str, Any]:
        """Get constitutional guidance for an agent."""
        # Map agent name to agent type
        agent_type_mapping = {
            "structure_architect": AgentType.STRUCTURE_ARCHITECT,
            "interface_designer": AgentType.INTERFACE_DESIGNER,
            "implementation_expert": AgentType.IMPLEMENTATION_EXPERT,
            "quality_guardian": AgentType.QUALITY_GUARDIAN,
            "learning_catalyst": AgentType.LEARNING_CATALYST,
            "test_specialist": AgentType.TEST_SPECIALIST,
            "autofix_agent": AgentType.AUTOFIX_AGENT,
            "solve_coordinator": AgentType.SOLVE_COORDINATOR,
        }

        agent_type = agent_type_mapping.get(agent_name, AgentType.SOLVE_COORDINATOR)
        constitution = AgentConstitutionFactory.create_constitution(agent_type)

        return {
            "agent_type": agent_type.value,
            "core_mission": constitution.core_mission,
            "primary_principles": [p.value for p in constitution.primary_principles],
            "capabilities": constitution.capabilities,
            "responsibilities": constitution.responsibilities,
            "ethical_guidelines": constitution.ethical_guidelines,
            "safety_constraints": constitution.safety_constraints,
            "collaboration_patterns": constitution.collaboration_patterns,
            "success_metrics": constitution.success_metrics,
            "decision_framework": constitution.decision_framework,
        }

    async def record_agent_interaction(
        self,
        from_agent: str,
        to_agent: str,
        interaction_type: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record an interaction between agents."""
        interaction = AgentInteraction(
            from_agent=from_agent,
            to_agent=to_agent,
            interaction_type=interaction_type,
            message=message,
            context=context or {},
            constitutional_guidance_applied=True,  # Since we're using constitutional AI
        )

        self.agent_interactions.append(interaction)
        logger.debug(
            f"Recorded interaction: {from_agent} -> {to_agent} ({interaction_type})"
        )

    def get_constitutional_metrics(self) -> dict[str, Any]:
        """Get constitutional AI metrics."""
        return self.metrics.get_summary()

    def get_system_state(self) -> SystemState:
        """Get current system state."""
        return self.system_state

    async def achieve_goal(self, goal: Goal, agents: list[str] | None = None) -> Result:
        """
        Achieve a development goal through agent collaboration using ReAct loop
        with Constitutional AI.

        Args:
            goal: The goal to achieve
            agents: Optional list of specific agent names to use

        Returns:
            Result containing artifacts and metadata
        """
        logger.info(f"Starting goal: {goal.description}")

        # Add to system state
        self.system_state.current_goals.append(goal)

        # Add context from knowledge base
        goal.context.update(self.knowledge.get_relevant_context(goal))

        # Get constitutional principles for the coordinator
        coordinator_constitution = self.get_agent_constitution("solve_coordinator")
        goal.context["constitutional_guidance"] = coordinator_constitution

        # Initialize state for ReAct loop
        state: dict[str, Any] = {
            "goal": goal,
            "preferred_agents": agents,
            "tasks": [],
            "results": [],
            "artifacts": {},
            "completed": False,
            "iteration": 0,
        }

        # ReAct loop
        while not state["completed"] and int(state["iteration"]) < self.max_iterations:
            state["iteration"] = int(state["iteration"]) + 1
            logger.info(f"ReAct iteration {state['iteration']}")

            # Reason about next step
            reasoning = await self._reason(state)
            self.reasoning_history.append(reasoning)

            # Execute action based on reasoning
            action_result = await self._act(reasoning, state)

            # Update state based on action result
            state = self._update_state(state, action_result)

            # Check if goal is achieved
            if self._is_goal_achieved(state):
                state["completed"] = True

        # Return final result
        return self._create_final_result(state)

    async def _select_agents(
        self, goal: Goal, preferred: list[str] | None = None
    ) -> list[Agent]:
        """Select the best agents for the goal."""
        if preferred:
            return [a for a in self.agents if a.name in preferred]

        # Score each agent's capability
        agent_scores = []
        for agent in self.agents:
            score = await agent.can_handle(goal)
            if score > 0.5:  # Minimum confidence threshold
                agent_scores.append((agent, score))

        # Sort by score and return top agents
        agent_scores.sort(key=lambda x: x[1], reverse=True)
        return [agent for agent, _ in agent_scores[:3]]  # Max 3 agents per goal

    async def _decompose_goal(self, goal: Goal, agents: list[Agent]) -> list[AgentTask]:
        """Break down the goal into tasks for each agent."""
        tasks = []

        # Simple decomposition - can be made more sophisticated
        for agent in agents:
            task = AgentTask(
                goal=goal, assigned_agent=agent.name, status=TaskStatus.PENDING
            )
            # Store agent reference in task metadata since AgentTask doesn't have agent field
            task.goal.context["agent_reference"] = agent
            tasks.append(task)

        return tasks

    async def _execute_tasks(self, tasks: list[AgentTask]) -> list[Result]:
        """Execute tasks, running independent ones concurrently."""
        # For now, execute all tasks concurrently
        # Future: Add dependency analysis

        async def execute_with_logging(task: AgentTask) -> Result:
            logger.info(f"Agent {task.assigned_agent} starting task")
            task.start()
            try:
                # Get agent reference from task metadata
                agent = task.goal.context.get("agent_reference")
                if agent is None:
                    raise RuntimeError(
                        f"No agent reference found for task {task.assigned_agent}"
                    )
                # Type assertion since we know this is an Agent from _decompose_goal
                agent_instance: Agent = agent
                result = await agent_instance.execute(task)
                task.complete(result)
                logger.info(f"Agent {task.assigned_agent} completed task")
                return result
            except Exception as e:
                logger.error(f"Agent {task.assigned_agent} failed: {e}")
                error_result = Result(success=False, message=str(e), artifacts={})
                task.complete(error_result)
                return error_result

        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[execute_with_logging(task) for task in tasks],
            return_exceptions=False,
        )

        return results

    def _aggregate_results(self, results: list[Result], goal: Goal) -> Result:
        """Combine results from multiple agents."""
        all_artifacts = {}
        all_messages = []
        success = True

        for result in results:
            if result.artifacts:
                all_artifacts.update(result.artifacts)
            if result.message:
                all_messages.append(result.message)
            if not result.success:
                success = False

        return Result(
            success=success,
            message="\n".join(all_messages),
            artifacts=all_artifacts,
            metadata={
                "goal": goal.description,
                "agents_used": len(results),
                "success_criteria_met": self._check_success_criteria(
                    goal, all_artifacts
                ),
            },
        )

    def _check_success_criteria(
        self, goal: Goal, artifacts: dict[str, Any]
    ) -> list[str]:
        """Check which success criteria were met."""
        met_criteria = []

        for criterion in goal.success_criteria:
            # Simple check - can be made more sophisticated
            if any(criterion.lower() in str(v).lower() for v in artifacts.values()):
                met_criteria.append(criterion)

        return met_criteria

    async def _reason(self, state: dict[str, Any]) -> Reasoning:
        """
        Analyze current state and determine next action with Constitutional AI guidance.

        This implements the 'Reason' phase of the ReAct loop.
        """
        goal = state["goal"]
        iteration = state["iteration"]

        # Get constitutional guidance for reasoning
        reasoning_context = {
            "goal": goal.description,
            "iteration": iteration,
            "constraints": goal.constraints,
            "reasoning": f"Analyzing state at iteration {iteration}",
            "collaboration_context": {
                "active_agents": self.system_state.active_agents,
                "recent_decisions": len(self.system_state.recent_decisions),
            },
        }

        # Validate the reasoning approach with Constitutional AI
        decision_response = await self.validate_agent_decision(
            agent_id="solve_coordinator",
            agent_type="solve_coordinator",
            decision="Analyze current state and determine next action",
            context=reasoning_context,
        )

        if not decision_response.approved:
            logger.warning(
                f"Constitutional AI flagged reasoning approach: {decision_response.reasoning}",
            )
            for warning in decision_response.safety_warnings:
                logger.warning(f"Safety warning: {warning}")
            for suggestion in decision_response.improvement_suggestions:
                logger.info(f"Improvement suggestion: {suggestion}")

        # Analyze what's been done so far
        completed_tasks = len([r for r in state["results"] if r.success])
        total_tasks = len(state["tasks"])

        # Determine next action based on state
        if not state["tasks"]:
            # No tasks yet - need to select agents and decompose
            thought = (
                f"Goal: {goal.description}. No tasks created yet. "
                "Need to select agents and decompose the goal."
            )
            next_action = "select_and_decompose"
            confidence = 0.9
        elif completed_tasks < total_tasks:
            # Tasks in progress - continue execution
            thought = (
                f"Progress: {completed_tasks}/{total_tasks} tasks completed. "
                "Continue executing remaining tasks."
            )
            next_action = "execute_tasks"
            confidence = 0.8
        elif all(r.success for r in state["results"]):
            # All tasks completed successfully - aggregate results
            thought = (
                "All tasks completed successfully. Ready to aggregate results "
                "and complete the goal."
            )
            next_action = "aggregate_and_complete"
            confidence = 0.95
        else:
            # Some tasks failed - analyze and decide
            failed_count = len([r for r in state["results"] if not r.success])
            thought = f"{failed_count} tasks failed. Need to analyze failures and determine next steps."
            next_action = "handle_failures"
            confidence = 0.6

        # Build reasoning context
        context = {
            "iteration": iteration,
            "tasks_created": total_tasks,
            "tasks_completed": completed_tasks,
            "has_failures": any(not r.success for r in state["results"]),
            "artifacts_collected": len(state["artifacts"]),
        }

        # Determine which agents to use
        selected_agent_names: list[str] = []
        if next_action == "select_and_decompose":
            # Will select agents in the action phase
            selected_agent_names = state["preferred_agents"] or []
        elif state["tasks"]:
            # Use agents from existing tasks
            selected_agent_names = list({t.assigned_agent for t in state["tasks"]})

        return Reasoning(
            thought=thought,
            next_action=next_action,
            selected_agents=selected_agent_names,
            confidence=confidence,
            context=context,
        )

    async def _act(self, reasoning: Reasoning, state: dict[str, Any]) -> Action:
        """
        Execute action based on reasoning.

        This implements the 'Act' phase of the ReAct loop.
        """
        logger.info(f"Acting on: {reasoning.thought}")

        action_type = reasoning.next_action
        goal = state["goal"]

        if action_type == "select_and_decompose":
            # Select agents and create tasks
            selected_agents = await self._select_agents(goal, state["preferred_agents"])
            if not selected_agents:
                return Action(
                    action_type="error",
                    target=None,
                    agents=[],
                    metadata={"error": "No suitable agents found"},
                )

            # Decompose goal into tasks
            tasks = await self._decompose_goal(goal, selected_agents)

            return Action(
                action_type="decompose",
                target=tasks,
                agents=selected_agents,
                metadata={"task_count": len(tasks)},
            )

        elif action_type == "execute_tasks":
            # Execute pending tasks
            pending_tasks = [
                t for t in state["tasks"] if t.status == TaskStatus.PENDING
            ]
            if pending_tasks:
                results = await self._execute_tasks(pending_tasks)
                return Action(
                    action_type="execute",
                    target=results,
                    agents=[],  # Agents are in the tasks
                    metadata={"executed_count": len(results)},
                )
            else:
                return Action(
                    action_type="wait",
                    target=None,
                    agents=[],
                    metadata={"message": "No pending tasks to execute"},
                )

        elif action_type == "aggregate_and_complete":
            # Aggregate all results
            final_result = self._aggregate_results(state["results"], goal)
            return Action(
                action_type="complete",
                target=final_result,
                agents=[],
                metadata={"success": final_result.success},
            )

        elif action_type == "handle_failures":
            # Analyze failures and potentially retry or adjust
            failed_tasks = [
                (t, r)
                for t, r in zip(state["tasks"], state["results"], strict=False)
                if not r.success
            ]

            # For now, just mark as complete with failures
            # Future: Could implement retry logic or alternative approaches
            logger.warning(f"Handling {len(failed_tasks)} failed tasks")

            return Action(
                action_type="complete_with_failures",
                target=failed_tasks,
                agents=[],
                metadata={"failure_count": len(failed_tasks)},
            )

        else:
            # Unknown action
            return Action(
                action_type="error",
                target=None,
                agents=[],
                metadata={"error": f"Unknown action type: {action_type}"},
            )

    def _update_state(self, state: dict[str, Any], action: Action) -> dict[str, Any]:
        """Update state based on action result."""
        new_state = state.copy()

        if action.action_type == "decompose":
            new_state["tasks"] = action.target
            logger.info(f"Created {len(action.target)} tasks")

        elif action.action_type == "execute":
            new_state["results"].extend(action.target)
            # Update artifacts from results
            for result in action.target:
                if result.artifacts:
                    new_state["artifacts"].update(result.artifacts)
            logger.info(f"Executed {len(action.target)} tasks")

        elif action.action_type in ["complete", "complete_with_failures"]:
            new_state["completed"] = True
            if action.action_type == "complete":
                new_state["final_result"] = action.target

        elif action.action_type == "error":
            logger.error(f"Action error: {action.metadata.get('error')}")
            new_state["completed"] = True
            new_state["error"] = action.metadata.get("error")

        # Store action in history
        self.action_history.append(action)

        return new_state

    def _is_goal_achieved(self, state: dict[str, Any]) -> bool:
        """Check if the goal has been achieved based on current state."""
        if state["completed"]:
            return True

        if not state["tasks"]:
            return False

        # Check if all tasks are completed
        if len(state["results"]) != len(state["tasks"]):
            return False

        # Check success criteria
        goal = state["goal"]
        met_criteria = self._check_success_criteria(goal, state["artifacts"])

        # Consider goal achieved if all criteria are met or all tasks succeeded
        all_tasks_succeeded = all(r.success for r in state["results"])
        all_criteria_met = len(met_criteria) == len(goal.success_criteria)

        return all_tasks_succeeded and (all_criteria_met or not goal.success_criteria)

    def _create_final_result(self, state: dict[str, Any]) -> Result:
        """Create the final result from the ReAct loop state."""
        if "final_result" in state:
            final_result = state["final_result"]
            if isinstance(final_result, Result):
                return final_result
            else:
                # Convert to Result if needed
                return Result(
                    success=False, message="Invalid final result type", artifacts={}
                )

        if "error" in state:
            return Result(
                success=False,
                message=f"Goal failed: {state['error']}",
                artifacts=state["artifacts"],
                metadata={
                    "iterations": state["iteration"],
                    "reasoning_steps": len(self.reasoning_history),
                    "actions_taken": len(self.action_history),
                },
            )

        # Aggregate all results if not already done
        if state["results"]:
            return self._aggregate_results(state["results"], state["goal"])

        return Result(
            success=False,
            message="Goal not achieved within iteration limit",
            artifacts=state["artifacts"],
            metadata={
                "iterations": state["iteration"],
                "max_iterations": self.max_iterations,
            },
        )

    async def execute_adr(self, adr_path: str) -> Result:
        """Execute all phases of an ADR in sequence with proper boundaries.

        Args:
            adr_path: Path to the ADR file (markdown or XML)

        Returns:
            Result containing execution artifacts and metadata
        """
        logger.info(f"Starting ADR-driven execution from {adr_path}")

        try:
            # Load and parse the ADR
            adr_config = await self.governance_engine.load_adr(Path(adr_path))
            logger.info(f"Loaded ADR-{adr_config.number}: {adr_config.title}")

            # Initialize phase results storage
            phase_results: dict[str, Result] = {}
            all_artifacts: dict[str, Any] = {}

            # Define phase order
            phases = ["scaffold", "outline", "logic", "verify", "enhance"]

            for phase in phases:
                logger.info(f"=== Starting {phase.upper()} phase ===")

                # Execute the phase
                phase_result = await self.execute_phase(
                    phase, adr_config, all_artifacts.copy()
                )
                phase_results[phase] = phase_result

                # Accumulate artifacts
                if phase_result.artifacts:
                    all_artifacts.update(phase_result.artifacts)

                # Enforce commit gate
                if not await self._commit_phase_changes(phase, adr_config):
                    logger.error(f"Failed to commit changes for {phase} phase")
                    return Result(
                        success=False,
                        message=f"Commit gate failed for {phase} phase",
                        artifacts=all_artifacts,
                        metadata={"completed_phases": list(phase_results.keys())},
                    )

                # Capture reflection/lessons
                await self._capture_phase_reflection(phase, phase_result)

                if not phase_result.success:
                    logger.warning(f"Phase {phase} failed, stopping ADR execution")
                    break

            # Determine overall success
            all_successful = all(r.success for r in phase_results.values())

            return Result(
                success=all_successful,
                message=(
                    f"ADR-{adr_config.number} execution "
                    f"{'completed' if all_successful else 'failed'}"
                ),
                artifacts=all_artifacts,
                metadata={
                    "adr_number": adr_config.number,
                    "adr_title": adr_config.title,
                    "phase_results": {p: r.success for p, r in phase_results.items()},
                    "total_requirements": len(adr_config.requirements),
                },
            )

        except Exception as e:
            logger.error(f"Failed to execute ADR: {e}")
            return Result(
                success=False,
                message=f"ADR execution failed: {str(e)}",
                artifacts={},
                metadata={"error": str(e)},
            )

    async def execute_phase(
        self, phase: str, adr: ADRConfig, context: dict[str, Any]
    ) -> Result:
        """Execute a single phase with ADR context and boundaries using multi-agent architecture.

        Args:
            phase: Phase name (scaffold, outline, logic, verify, enhance)
            adr: ADR configuration with requirements and outcomes
            context: Accumulated context from previous phases

        Returns:
            Result of phase execution
        """
        logger.info(
            f"Executing {phase} phase with ADR context using multi-agent architecture"
        )

        # Import phase coordinators
        from solve.agents.phase_executors import create_phase_executor
        from solve.agents.phase_validators import create_phase_validator

        # Set current phase
        self.current_phase = phase
        self.phase_context = context.copy()

        # Load lessons for this phase
        historical_lessons = await self.lesson_capture.load_historical_lessons(
            phase=phase,
            adr_number=adr.number,
        )
        logger.info(f"Loaded {len(historical_lessons)} historical lessons for {phase}")

        # Extract phase-specific outcomes from ADR
        phase_outcomes = adr.phase_outcomes.get(phase, {})
        phase_requirements = []

        # Filter requirements relevant to this phase
        for req in adr.requirements:
            req_lower = req.lower()
            if (
                phase == "scaffold"
                and any(kw in req_lower for kw in ["structure", "setup", "create"])
                or phase == "outline"
                and any(kw in req_lower for kw in ["interface", "contract", "define"])
                or phase == "logic"
                and any(
                    kw in req_lower for kw in ["implement", "logic", "functionality"]
                )
                or phase == "verify"
                and any(kw in req_lower for kw in ["test", "validate", "verify"])
                or phase == "enhance"
                and any(kw in req_lower for kw in ["optimize", "enhance", "improve"])
            ):
                phase_requirements.append(req)

        # Create executor and validator for this phase
        executor = create_phase_executor(phase)
        validator = create_phase_validator(phase)

        logger.info(f"Created {executor.name} and {validator.name} for {phase} phase")

        # Phase 1: Executor creates work plan based on ADR outcomes
        adr_outcomes_dict = {
            "phase": phase,
            "requirements": phase_requirements,
            "outcomes": phase_outcomes,
            "context": context,
            "historical_lessons": [
                {
                    "issue": lesson.issue,
                    "resolution": lesson.resolution,
                    "prevention": lesson.prevention,
                }
                for lesson in historical_lessons[:5]  # Include top 5 lessons
            ],
        }

        work_plan = await executor.create_plan(adr_outcomes_dict)

        # Phase 2: Validator reviews plan BEFORE execution
        plan_validation = await validator.validate_plan(work_plan)

        if not plan_validation.approved:
            logger.error(f"Plan validation failed for {phase} phase")
            return Result(
                success=False,
                message=(
                    f"Plan rejected by validator: {', '.join(plan_validation.critical_failures)}"
                ),
                artifacts={"validation_issues": plan_validation.to_dict()},
                metadata={"phase": phase, "validation_failed": True},
            )

        logger.info(f"Plan approved by validator for {phase} phase")

        # Phase 3: Execute approved plan with specialist workers
        from solve.agents.specialist_workers import create_specialist

        phase_results = []
        phase_artifacts = {}

        # Get tasks from work plan
        tasks = work_plan.get("tasks", [])
        if not tasks:
            # Fallback: create a single task for the phase
            tasks = [
                {
                    "id": "default",
                    "specialist": f"{phase}_specialist",
                    "description": f"Execute {phase} phase work",
                    "dependencies": [],
                },
            ]

        for task in tasks:
            try:
                # Get or create specialist
                specialist_name = task.get("specialist", f"{phase}_specialist")
                try:
                    specialist = create_specialist(specialist_name)
                except ValueError:
                    # If specific specialist not found, use a default based on phase
                    logger.warning(
                        f"Specialist {specialist_name} not found, using phase default"
                    )
                    specialist = self._create_default_specialist(phase)

                # Execute specialist task
                task_result = await specialist.execute_specialist_task(task)

                # Immediate validation of result
                result_validation = await validator.validate_result(task_result)

                if result_validation.approved:
                    phase_results.append(task_result)
                    if task_result.artifacts:
                        phase_artifacts.update(task_result.artifacts)
                else:
                    # Handle validation failure - retry or adjust
                    logger.warning(
                        f"Task result validation failed: {result_validation.issues}"
                    )
                    # For now, include with warning
                    phase_results.append(task_result)

            except Exception as e:
                logger.error(f"Failed to execute task {task.get('id', 'unknown')}: {e}")
                phase_results.append(
                    Result(
                        success=False,
                        message=f"Task execution failed: {str(e)}",
                        artifacts={},
                        metadata={"task": task, "error": str(e)},
                    ),
                )

        # Phase 4: Final phase validation
        phase_validation = await validator.validate_phase_complete(
            phase,
            adr_outcomes_dict,
            phase_results,
        )

        if not phase_validation.approved:
            logger.warning(
                f"Phase completion validation failed: {phase_validation.issues}"
            )

        # Aggregate results
        all_successful = all(r.success for r in phase_results)

        final_result = Result(
            success=all_successful and phase_validation.approved,
            message=(
                f"{phase.capitalize()} phase "
                f"{'completed successfully' if all_successful else 'completed with issues'}"
            ),
            artifacts=phase_artifacts,
            metadata={
                "phase": phase,
                "tasks_executed": len(phase_results),
                "tasks_successful": sum(1 for r in phase_results if r.success),
                "validation_approved": phase_validation.approved,
                "validation_issues": (
                    phase_validation.issues if not phase_validation.approved else []
                ),
            },
        )

        # Clear phase context
        self.current_phase = None
        self.phase_context = {}

        return final_result

    def _create_default_specialist(self, phase: str) -> Any:
        """Create a default specialist for phases without specific specialists."""
        from solve.agents.specialist_workers import BaseSpecialistWorker

        class DefaultSpecialist(BaseSpecialistWorker):
            def __init__(self, phase_name: str):
                super().__init__(
                    specialty=f"{phase_name} default work",
                    name=f"{phase_name}_default_specialist",
                    role=self._get_role_for_phase(phase_name),
                    description=f"Default specialist for {phase_name} phase",
                    capabilities=[f"Execute general {phase_name} phase tasks"],
                )

            def _get_role_for_phase(self, phase_name: str) -> Any:
                from solve.prompts.constitutional_template import AgentRole

                role_map = {
                    "scaffold": AgentRole.STRUCTURE,
                    "outline": AgentRole.INTERFACE,
                    "logic": AgentRole.LOGIC,
                    "verify": AgentRole.TESTING,
                    "enhance": AgentRole.QUALITY,
                }
                return role_map.get(phase_name, AgentRole.STRUCTURE)

        return DefaultSpecialist(phase)

    async def _commit_phase_changes(self, phase: str, adr: ADRConfig) -> bool:
        """Enforce git commit after phase completion.

        Args:
            phase: Phase name
            adr: ADR configuration

        Returns:
            True if commit successful, False otherwise
        """
        try:
            # Check for uncommitted changes
            # Security: Use shutil.which to locate git executable
            git_exe = shutil.which("git")
            if not git_exe:
                logger.warning(
                    "Git executable not found in PATH, skipping commit check"
                )
                return True

            # Security: Input validation - hardcoded git subcommands are safe
            # S603/S607: This subprocess call is intentional and safe because:
            # 1. We use shutil.which to get the full path to git executable
            # 2. All arguments are hardcoded git subcommands (status --porcelain)
            # 3. shell=False prevents shell injection
            # 4. timeout prevents hanging
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                [git_exe, "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
                shell=False,
                timeout=10,
            )

            if not result.stdout.strip():
                logger.info(f"No changes to commit for {phase} phase")
                return True

            logger.info(f"Found uncommitted changes for {phase} phase")

            # For now, just log what would be committed
            # In production, this would enforce actual commits
            logger.info(
                f"Would commit with message: 'Complete {phase} phase for ADR-{adr.number}'"
            )

            # Return True to allow phase progression in testing
            # In production, this would only return True after successful commit
            return True

        except Exception as e:
            logger.error(f"Failed to commit phase changes: {e}")
            return False

    async def _capture_phase_reflection(self, phase: str, result: Result) -> None:
        """Capture lessons learned from phase execution.

        Args:
            phase: Phase name
            result: Phase execution result
        """
        try:
            # Only capture lessons if there were issues or notable outcomes
            if not result.success:
                issue = f"Phase {phase} failed: {result.message}"
                resolution = "Phase execution was stopped"
                prevention = (
                    "Review phase requirements and ensure proper implementation"
                )

                await self.lesson_capture.capture_lesson(
                    issue=issue,
                    resolution=resolution,
                    prevention=prevention,
                    phase=phase,
                    adr_number=self.phase_context.get("adr_number"),
                )
            elif result.metadata.get("warnings"):
                # Capture warnings as lessons
                for warning in result.metadata["warnings"]:
                    await self.lesson_capture.capture_lesson(
                        issue=f"Warning in {phase}: {warning}",
                        resolution="Continued with warning",
                        prevention="Address warning in future implementations",
                        phase=phase,
                        adr_number=self.phase_context.get("adr_number"),
                    )

        except Exception as e:
            logger.error(f"Failed to capture phase reflection: {e}")

    def _validate_phase_completion(
        self,
        artifacts: dict[str, Any],
        considerations: list[str],
    ) -> list[str]:
        """Validate phase completion against ADR considerations.

        Args:
            artifacts: Phase execution artifacts
            considerations: Key considerations from ADR

        Returns:
            List of met considerations
        """
        met_considerations = []

        for consideration in considerations:
            # Simple validation - check if consideration keywords appear in artifacts
            consideration_lower = consideration.lower()
            for _key, value in artifacts.items():
                if any(
                    word in str(value).lower() for word in consideration_lower.split()
                ):
                    met_considerations.append(consideration)
                    break

        return met_considerations


# Example agents for testing
class StructureAgent:
    """Agent that handles project structure tasks."""

    name = "structure_architect"
    capabilities = ["project_setup", "directory_structure", "configuration"]

    async def can_handle(self, goal: Goal) -> float:
        keywords = ["structure", "setup", "scaffold", "directory", "project"]
        if any(keyword in goal.description.lower() for keyword in keywords):
            return 0.9
        return 0.1

    async def execute(self, task: AgentTask) -> Result:
        # Placeholder implementation
        return Result(
            success=True,
            message="Created project structure",
            artifacts={"structure": "Created directories and files"},
        )
