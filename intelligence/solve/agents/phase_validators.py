"""
Phase Validator Agents for SOLVE Methodology

These agents validate work plans and results for each SOLVE phase.
They NEVER execute work - that's the job of phase executors.

Based on:
- docs/SOLVE_MULTI_AGENT_ARCHITECTURE.md (Separation of concerns)
- docs/best-practices/8-constitutional-ai.md (Safety principles)
- docs/best-practices/5-multi-agent-coordination.md (Validation patterns)
"""

import logging
from typing import Any

from solve.agents.base_agent import RealADKAgent
from solve.models import AgentTask, Goal, Result, TaskStatus
from solve.prompts.constitutional_template import AgentRole

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation check."""

    def __init__(
        self,
        approved: bool,
        issues: list[str] | None = None,
        suggestions: list[str] | None = None,
        critical_failures: list[str] | None = None,
    ) -> None:
        self.approved = approved
        self.issues = issues or []
        self.suggestions = suggestions or []
        self.critical_failures = critical_failures or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "approved": self.approved,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "critical_failures": self.critical_failures,
        }


class BasePhaseValidator(RealADKAgent):
    """Base class for phase validators with strict validation capabilities."""

    def __init__(self, phase_name: str, **kwargs: Any) -> None:
        """Initialize phase validator."""
        self.phase_name = phase_name
        # Validators have stricter constitutional principles
        kwargs["capabilities"] = kwargs.get("capabilities", []) + [
            "Enforce safety constraints",
            "Block unsafe operations",
            "Ensure quality standards",
            "Prevent phase boundary violations",
        ]
        super().__init__(**kwargs)

    async def validate_plan(self, work_plan: dict[str, Any]) -> ValidationResult:
        """
        Validate a work plan BEFORE execution.

        Args:
            work_plan: Proposed execution plan

        Returns:
            Validation result with approval status
        """
        # Build validation prompt
        self._build_plan_validation_prompt(work_plan)

        # Create validation goal
        validation_goal = Goal(
            description=f"Validate {self.phase_name} phase execution plan",
            context={
                "work_plan": work_plan,
                "phase": self.phase_name,
                "agent_type": "validator",
            },
            constraints=[
                "Check for safety violations",
                "Ensure phase boundaries respected",
                "Verify all ADR requirements covered",
                "Identify potential risks",
            ],
            success_criteria=[
                "Safety assessment complete",
                "Phase boundaries verified",
                "Requirements coverage checked",
            ],
        )

        # Execute validation via ADK
        validation_task = AgentTask(
            goal=validation_goal,
            assigned_agent=self.name,
            status=TaskStatus.PENDING,
        )

        result = await self.execute(validation_task)

        return self._extract_validation_result(result)

    async def validate_result(self, execution_result: Result) -> ValidationResult:
        """
        Validate execution results AFTER work is done.

        Args:
            execution_result: Result from specialist execution

        Returns:
            Validation result
        """
        # Build result validation prompt
        self._build_result_validation_prompt(execution_result)

        # Create validation goal
        validation_goal = Goal(
            description=f"Validate {self.phase_name} phase execution result",
            context={
                "execution_result": {
                    "success": execution_result.success,
                    "message": execution_result.message,
                    "artifacts": execution_result.artifacts,
                    "metadata": execution_result.metadata,
                },
                "phase": self.phase_name,
                "agent_type": "validator",
            },
            constraints=[
                "Verify quality standards met",
                "Check for completeness",
                "Ensure no regressions",
                "Validate against success criteria",
            ],
            success_criteria=[
                "Quality verified",
                "Completeness confirmed",
                "No regressions found",
            ],
        )

        # Execute validation
        validation_task = AgentTask(
            goal=validation_goal,
            assigned_agent=self.name,
            status=TaskStatus.PENDING,
        )

        result = await self.execute(validation_task)

        return self._extract_validation_result(result)

    async def validate_phase_complete(
        self,
        phase_name: str,
        adr_outcomes: dict[str, Any],
        results: list[Result],
    ) -> ValidationResult:
        """
        Validate that entire phase is complete and meets ADR requirements.

        Args:
            phase_name: Name of the phase
            adr_outcomes: Expected outcomes from ADR
            results: All results from phase execution

        Returns:
            Final validation result for phase
        """
        # Build comprehensive validation prompt
        self._build_phase_completion_prompt(phase_name, adr_outcomes, results)

        # Create final validation goal
        validation_goal = Goal(
            description=f"Validate {phase_name} phase completion",
            context={
                "phase": phase_name,
                "adr_outcomes": adr_outcomes,
                "execution_results": [
                    {
                        "success": r.success,
                        "message": r.message,
                        "artifacts": r.artifacts,
                        "metadata": r.metadata,
                    }
                    for r in results
                ],
                "agent_type": "validator",
            },
            constraints=[
                "All ADR outcomes must be achieved",
                "No critical issues remaining",
                "Ready for commit and next phase",
            ],
            success_criteria=[
                "ADR compliance verified",
                "Phase outputs complete",
                "Quality standards met",
            ],
        )

        # Execute final validation
        validation_task = AgentTask(
            goal=validation_goal,
            assigned_agent=self.name,
            status=TaskStatus.PENDING,
        )

        result = await self.execute(validation_task)

        return self._extract_validation_result(result)

    def _build_plan_validation_prompt(self, work_plan: dict[str, Any]) -> str:
        """Build prompt for plan validation."""
        return f"""
        <validation_request type="plan">
        <phase>{self.phase_name}</phase>
        <work_plan>
        {work_plan}
        </work_plan>

        Validate this execution plan for the {self.phase_name} phase.

        Check for:
        1. Safety violations or risky operations
        2. Phase boundary violations (work that belongs in other phases)
        3. Missing requirements or incomplete coverage
        4. Dependency issues or ordering problems
        5. Resource conflicts or bottlenecks

        CRITICAL: You have veto power. If this plan could harm the system,
        damage existing functionality, or violate phase boundaries, you MUST
        reject it.

        Respond with:
        <validation_result>
        <approved>true/false</approved>
        <issues>
            <issue severity="critical/high/medium/low">Description</issue>
            ...
        </issues>
        <suggestions>
            <suggestion>Improvement recommendation</suggestion>
            ...
        </suggestions>
        </validation_result>
        </validation_request>
        """

    def _build_result_validation_prompt(self, execution_result: Result) -> str:
        """Build prompt for result validation."""
        return f"""
        <validation_request type="result">
        <phase>{self.phase_name}</phase>
        <execution_result>
        <success>{execution_result.success}</success>
        <message>{execution_result.message}</message>
        <artifacts>{execution_result.artifacts}</artifacts>
        </execution_result>

        Validate this execution result from the {self.phase_name} phase.

        Verify:
        1. Quality standards have been met
        2. No existing functionality was broken
        3. Output is complete and correct
        4. Success criteria were achieved
        5. No security or safety issues introduced

        Respond with validation assessment.
        </validation_request>
        """

    def _build_phase_completion_prompt(
        self,
        phase_name: str,
        adr_outcomes: dict[str, Any],
        results: list[Result],
    ) -> str:
        """Build prompt for phase completion validation."""
        return f"""
        <validation_request type="phase_completion">
        <phase>{phase_name}</phase>
        <adr_outcomes>
        {adr_outcomes}
        </adr_outcomes>
        <execution_results count="{len(results)}">
        {
            [
                {
                    "success": r.success,
                    "message": r.message,
                    "artifacts": r.artifacts,
                    "metadata": r.metadata,
                }
                for r in results
            ]
        }
        </execution_results>

        Validate that the {phase_name} phase is complete and ready for commit.

        Ensure:
        1. All ADR outcomes have been achieved
        2. No critical issues remain unresolved
        3. Phase outputs meet quality standards
        4. System is in a stable, committable state
        5. Ready to proceed to next phase

        This is the final gate before git commit. Be thorough.
        </validation_request>
        """

    def _extract_validation_result(self, result: Result) -> ValidationResult:
        """Extract structured validation result from ADK response."""
        # For now, return based on success
        # In production, parse the XML response
        if result.success:
            response_text = result.artifacts.get("response_text", "")

            # Simple parsing - enhance with proper XML parsing
            approved = "approved>true" in response_text.lower()

            return ValidationResult(
                approved=approved,
                issues=["Validation completed"],
                suggestions=[],
                critical_failures=[] if approved else ["Validation failed"],
            )
        else:
            return ValidationResult(
                approved=False,
                issues=[result.message],
                critical_failures=["Validation execution failed"],
            )


class ScaffoldValidator(BasePhaseValidator):
    """Validator for Scaffold phase - validates structure work."""

    def __init__(self) -> None:
        super().__init__(
            phase_name="scaffold",
            name="scaffold_validator",
            role=AgentRole.QUALITY,
            description="Validates structure creation plans and results",
            capabilities=[
                "Validate directory structure safety",
                "Check configuration correctness",
                "Verify Git setup appropriateness",
                "Ensure no destructive operations",
            ],
        )

    async def _extract_quality_artifacts(self, response: str) -> dict[str, Any]:
        """Extract scaffold validation artifacts."""
        return {
            "structure_validation": response,
            "safety_checks": [],
            "configuration_review": {},
        }


class OutlineValidator(BasePhaseValidator):
    """Validator for Outline phase - validates interfaces."""

    def __init__(self) -> None:
        super().__init__(
            phase_name="outline",
            name="outline_validator",
            role=AgentRole.QUALITY,
            description="Validates interface design plans and results",
            capabilities=[
                "Validate API design consistency",
                "Check schema correctness",
                "Verify contract completeness",
                "Ensure interface compatibility",
            ],
        )

    async def _extract_quality_artifacts(self, response: str) -> dict[str, Any]:
        """Extract outline validation artifacts."""
        return {
            "interface_validation": response,
            "consistency_checks": [],
            "compatibility_review": {},
        }


class LogicValidator(BasePhaseValidator):
    """Validator for Logic phase - validates implementation."""

    def __init__(self) -> None:
        super().__init__(
            phase_name="logic",
            name="logic_validator",
            role=AgentRole.QUALITY,
            description="Validates implementation plans and code quality",
            capabilities=[
                "Validate code correctness",
                "Check implementation completeness",
                "Verify error handling",
                "Ensure test coverage",
            ],
        )

    async def _extract_quality_artifacts(self, response: str) -> dict[str, Any]:
        """Extract logic validation artifacts."""
        return {
            "code_validation": response,
            "quality_metrics": {},
            "coverage_analysis": {},
        }


class VerifyValidator(BasePhaseValidator):
    """Validator for Verify phase - validates audit results."""

    def __init__(self) -> None:
        super().__init__(
            phase_name="verify",
            name="verify_validator",
            role=AgentRole.QUALITY,
            description="Validates verification and audit completeness",
            capabilities=[
                "Validate audit thoroughness",
                "Check test execution results",
                "Verify coverage adequacy",
                "Ensure compliance met",
            ],
        )

    async def _extract_quality_artifacts(self, response: str) -> dict[str, Any]:
        """Extract verify validation artifacts."""
        return {
            "audit_validation": response,
            "compliance_status": {},
            "coverage_verification": {},
        }


class EnhanceValidator(BasePhaseValidator):
    """Validator for Enhance phase - validates lessons/improvements."""

    def __init__(self) -> None:
        super().__init__(
            phase_name="enhance",
            name="enhance_validator",
            role=AgentRole.QUALITY,
            description="Validates enhancement suggestions and lesson quality",
            capabilities=[
                "Validate lesson accuracy",
                "Check pattern recognition",
                "Verify improvement feasibility",
                "Ensure knowledge capture quality",
            ],
        )

    async def _extract_quality_artifacts(self, response: str) -> dict[str, Any]:
        """Extract enhance validation artifacts."""
        return {
            "lesson_validation": response,
            "pattern_verification": {},
            "improvement_assessment": {},
        }


# Factory function for creating validators
def create_phase_validator(phase: str) -> BasePhaseValidator:
    """
    Create appropriate validator for a phase.

    Args:
        phase: Phase name

    Returns:
        Phase validator instance

    Raises:
        ValueError: If phase is unknown
    """
    validators = {
        "scaffold": ScaffoldValidator,
        "outline": OutlineValidator,
        "logic": LogicValidator,
        "verify": VerifyValidator,
        "enhance": EnhanceValidator,
    }

    validator_class = validators.get(phase.lower())
    if not validator_class:
        raise ValueError(f"Unknown phase: {phase}")

    return validator_class()


# Export all validator classes
__all__ = [
    "ValidationResult",
    "BasePhaseValidator",
    "ScaffoldValidator",
    "OutlineValidator",
    "LogicValidator",
    "VerifyValidator",
    "EnhanceValidator",
    "create_phase_validator",
]
