"""
Phase Executor Agents for SOLVE Methodology

These agents manage work planning and task assignment for each SOLVE phase.
They NEVER validate their own work - that's the job of phase validators.

Based on:
- docs/SOLVE_MULTI_AGENT_ARCHITECTURE.md (Separation of concerns)
- docs/best-practices/5-multi-agent-coordination.md (Team patterns)
- docs/best-practices/4-adk-agent-patterns.md (ADK integration)
"""

import logging
from typing import Any

from solve.agents.base_agent import RealADKAgent
from solve.models import AgentTask, Goal, Result, TaskStatus
from solve.prompts.constitutional_template import AgentRole

logger = logging.getLogger(__name__)


class BasePhaseExecutor(RealADKAgent):
    """Base class for phase executors with work planning capabilities."""

    def __init__(self, phase_name: str, **kwargs: Any) -> None:
        """Initialize phase executor."""
        self.phase_name = phase_name
        super().__init__(**kwargs)

    async def create_plan(self, adr_outcomes: dict[str, Any]) -> dict[str, Any]:
        """
        Create execution plan based on ADR outcomes.

        Args:
            adr_outcomes: Phase-specific outcomes from ADR

        Returns:
            Work plan with tasks and specialist assignments
        """
        # Build planning prompt
        self._build_planning_prompt(adr_outcomes)

        # Create planning goal
        planning_goal = Goal(
            description=f"Create execution plan for {self.phase_name} phase",
            context={
                "adr_outcomes": adr_outcomes,
                "phase": self.phase_name,
                "agent_type": "executor",
            },
            constraints=[
                "Break down work into specific tasks",
                "Assign appropriate specialists",
                "Consider dependencies between tasks",
                "Stay within phase boundaries",
            ],
            success_criteria=[
                "Clear task breakdown",
                "Specialist assignments",
                "Execution order defined",
            ],
        )

        # Execute planning via ADK
        planning_task = AgentTask(
            goal=planning_goal,
            assigned_agent=self.name,
            status=TaskStatus.PENDING,
        )

        result = await self.execute(planning_task)

        if result.success:
            return self._extract_plan_from_result(result)
        else:
            logger.error(f"Failed to create plan: {result.message}")
            return {"tasks": [], "error": result.message}

    def _build_planning_prompt(self, adr_outcomes: dict[str, Any]) -> str:
        """Build prompt for execution planning."""
        return f"""
        <planning_request>
        <phase>{self.phase_name}</phase>
        <adr_outcomes>
        {adr_outcomes}
        </adr_outcomes>

        Create a detailed execution plan for the {self.phase_name} phase.

        Requirements:
        1. Break down the ADR outcomes into specific, actionable tasks
        2. Assign each task to the appropriate specialist worker
        3. Define execution order considering dependencies
        4. Ensure all tasks stay within {self.phase_name} phase boundaries

        Format your response as:
        <execution_plan>
        <task id="1" specialist="specialist_name" dependencies="">
            <description>Task description</description>
            <success_criteria>How to verify completion</success_criteria>
        </task>
        ...
        </execution_plan>
        </planning_request>
        """

    def _extract_plan_from_result(self, result: Result) -> dict[str, Any]:
        """Extract structured plan from ADK result."""
        # For now, return a simple structure
        # In production, parse the XML response from ADK
        return {
            "tasks": [],
            "specialists": [],
            "dependencies": {},
            "raw_response": result.artifacts.get("response_text", ""),
        }

    async def assign_specialist(self, task: dict[str, Any]) -> str:
        """
        Assign a specialist worker to a task.

        Args:
            task: Task to assign

        Returns:
            Name of assigned specialist
        """
        # Logic to select appropriate specialist based on task type
        # This would be enhanced with actual specialist availability
        specialist_mapping = self._get_specialist_mapping()
        task_type = task.get("type", "general")

        return specialist_mapping.get(task_type, f"{self.phase_name}_specialist")

    def _get_specialist_mapping(self) -> dict[str, str]:
        """Get mapping of task types to specialists for this phase."""
        # Override in subclasses
        return {}


class ScaffoldExecutor(BasePhaseExecutor):
    """Executor for Scaffold phase - manages structure creation."""

    def __init__(self) -> None:
        super().__init__(
            phase_name="scaffold",
            name="scaffold_executor",
            role=AgentRole.STRUCTURE,
            description="Plans and manages project structure creation",
            capabilities=[
                "Plan directory structure creation",
                "Assign configuration generation tasks",
                "Coordinate Git initialization",
                "Manage file creation workflow",
            ],
        )

    def _get_specialist_mapping(self) -> dict[str, str]:
        """Get scaffold phase specialist mapping."""
        return {
            "directory": "DirectoryCreator",
            "config": "ConfigGenerator",
            "git": "GitInitializer",
            "template": "TemplateApplier",
        }

    async def _extract_structure_artifacts(self, response: str) -> dict[str, Any]:
        """Extract scaffold-specific planning artifacts."""
        return {
            "planned_directories": [],
            "planned_files": [],
            "git_config": {},
            "planning_response": response,
        }


class OutlineExecutor(BasePhaseExecutor):
    """Executor for Outline phase - manages interface design."""

    def __init__(self) -> None:
        super().__init__(
            phase_name="outline",
            name="outline_executor",
            role=AgentRole.INTERFACE,
            description="Plans and manages interface and contract design",
            capabilities=[
                "Plan API interface design",
                "Assign schema creation tasks",
                "Coordinate contract documentation",
                "Manage interface validation workflow",
            ],
        )

    def _get_specialist_mapping(self) -> dict[str, str]:
        """Get outline phase specialist mapping."""
        return {
            "api": "ApiDesigner",
            "schema": "SchemaCreator",
            "contract": "ContractWriter",
            "docs": "DocumentationWriter",
        }

    async def _extract_interface_artifacts(self, response: str) -> dict[str, Any]:
        """Extract outline-specific planning artifacts."""
        return {
            "planned_interfaces": [],
            "planned_schemas": [],
            "contract_templates": [],
            "planning_response": response,
        }


class LogicExecutor(BasePhaseExecutor):
    """Executor for Logic phase - manages implementation."""

    def __init__(self) -> None:
        super().__init__(
            phase_name="logic",
            name="logic_executor",
            role=AgentRole.LOGIC,
            description="Plans and manages business logic implementation",
            capabilities=[
                "Plan code implementation tasks",
                "Assign function writing work",
                "Coordinate error handling setup",
                "Manage test scaffolding alongside code",
            ],
        )

    def _get_specialist_mapping(self) -> dict[str, str]:
        """Get logic phase specialist mapping."""
        return {
            "implementation": "CodeImplementer",
            "test_scaffold": "TestScaffolder",
            "error_handling": "ErrorHandler",
            "integration": "IntegrationSpecialist",
        }

    async def _extract_logic_artifacts(self, response: str) -> dict[str, Any]:
        """Extract logic-specific planning artifacts."""
        return {
            "planned_modules": [],
            "planned_functions": [],
            "test_structure": {},
            "planning_response": response,
        }


class VerifyExecutor(BasePhaseExecutor):
    """Executor for Verify phase - manages verification/audit."""

    def __init__(self) -> None:
        super().__init__(
            phase_name="verify",
            name="verify_executor",
            role=AgentRole.TESTING,
            description="Plans and manages verification and audit processes",
            capabilities=[
                "Plan requirement audit tasks",
                "Assign test execution work",
                "Coordinate coverage analysis",
                "Manage quality verification workflow",
            ],
        )

    def _get_specialist_mapping(self) -> dict[str, str]:
        """Get verify phase specialist mapping."""
        return {
            "audit": "RequirementAuditor",
            "test_run": "TestRunner",
            "coverage": "CoverageAnalyzer",
            "security": "SecurityAuditor",
        }

    async def _extract_testing_artifacts(self, response: str) -> dict[str, Any]:
        """Extract verify-specific planning artifacts."""
        return {
            "audit_checklist": [],
            "test_plan": [],
            "coverage_targets": {},
            "planning_response": response,
        }


class EnhanceExecutor(BasePhaseExecutor):
    """Executor for Enhance phase - manages enhancement/lessons."""

    def __init__(self) -> None:
        super().__init__(
            phase_name="enhance",
            name="enhance_executor",
            role=AgentRole.QUALITY,
            description="Plans and manages enhancement and lesson capture",
            capabilities=[
                "Plan lesson extraction tasks",
                "Assign pattern recognition work",
                "Coordinate improvement suggestions",
                "Manage knowledge capture workflow",
            ],
        )

    def _get_specialist_mapping(self) -> dict[str, str]:
        """Get enhance phase specialist mapping."""
        return {
            "lessons": "LessonExtractor",
            "patterns": "PatternRecognizer",
            "improvements": "ImprovementSuggester",
            "documentation": "KnowledgeCapturer",
        }

    async def _extract_quality_artifacts(self, response: str) -> dict[str, Any]:
        """Extract enhance-specific planning artifacts."""
        return {
            "identified_lessons": [],
            "recognized_patterns": [],
            "improvement_suggestions": [],
            "planning_response": response,
        }


# Factory function for creating executors
def create_phase_executor(phase: str) -> BasePhaseExecutor:
    """
    Create appropriate executor for a phase.

    Args:
        phase: Phase name

    Returns:
        Phase executor instance

    Raises:
        ValueError: If phase is unknown
    """
    executors = {
        "scaffold": ScaffoldExecutor,
        "outline": OutlineExecutor,
        "logic": LogicExecutor,
        "verify": VerifyExecutor,
        "enhance": EnhanceExecutor,
    }

    executor_class = executors.get(phase.lower())
    if not executor_class:
        raise ValueError(f"Unknown phase: {phase}")

    return executor_class()


# Export all executor classes
__all__ = [
    "BasePhaseExecutor",
    "ScaffoldExecutor",
    "OutlineExecutor",
    "LogicExecutor",
    "VerifyExecutor",
    "EnhanceExecutor",
    "create_phase_executor",
]
