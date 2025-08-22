"""
Phase Gatekeeper - Quality Gate for SOLVE Phases

Enforces autofix as a mandatory commit gate between phases, ensuring no bugs
can accumulate and all fixed issues become lessons learned.

Based on the enterprise principle: "No phase can complete with bugs."
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from solve.autofix.models import AutofixConfig
from solve.autofix.models import FixResult as AutofixResult
from solve.autofix.runner import AutoFixerRunner
from solve.autofix.validation import ValidationRunner
from solve.exceptions import PhaseValidationError
from solve.lessons import LessonCapture
from solve.models import Lesson, Result

logger = logging.getLogger(__name__)

# Contract validation imports
try:
    from solve.agents.contract_validation import ContractValidationAgent
    from solve.agents.contract_validation import \
        ValidationResult as ContractValidationResult

    CONTRACT_VALIDATION_AVAILABLE = True
except ImportError:
    logger.warning("Contract validation not available - install graph dependencies")
    ContractValidationAgent = None
    ContractValidationResult = None
    CONTRACT_VALIDATION_AVAILABLE = False


@dataclass
class PhaseGateResult:
    """Result of phase gate check with quality enforcement."""

    can_proceed: bool
    fixes_applied: list[AutofixResult]
    lessons_created: list[Lesson]
    validation_errors: list[dict[str, Any]]
    contract_validation_result: ContractValidationResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Log gate result summary."""
        logger.info(
            f"Phase gate result: can_proceed={self.can_proceed}, "
            f"fixes_applied={len(self.fixes_applied)}, "
            f"lessons_created={len(self.lessons_created)}, "
            f"validation_errors={len(self.validation_errors)}",
        )


class PhaseGatekeeper:
    """
    Enforces quality gates between SOLVE phases using autofix.

    This class implements the critical enterprise requirement that no phase
    can complete with bugs. It runs autofix tools, captures lessons from
    fixes, and blocks progression if quality standards aren't met.
    """

    def __init__(
        self,
        autofix_config: AutofixConfig | None = None,
        lessons_dir: Path | None = None,
        enable_contract_validation: bool = True,
    ):
        """Initialize the phase gatekeeper.

        Args:
            autofix_config: Configuration for autofix system
            lessons_dir: Directory for storing lessons (defaults to .solve/lessons)
            enable_contract_validation: Whether to enable graph contract validation
        """
        self.autofix_config = autofix_config or AutofixConfig()
        self.lesson_capture = LessonCapture(lessons_dir)
        self.enable_contract_validation = (
            enable_contract_validation and CONTRACT_VALIDATION_AVAILABLE
        )

        # Initialize contract validation agent if available
        self.contract_validator = None
        if self.enable_contract_validation:
            try:
                self.contract_validator = ContractValidationAgent()
                logger.info("Initialized PhaseGatekeeper with contract validation")
            except Exception as e:
                logger.warning(f"Failed to initialize contract validation: {e}")
                self.enable_contract_validation = False
        else:
            logger.info("Initialized PhaseGatekeeper without contract validation")

    async def check_phase_complete(
        self,
        phase: str,
        adr_number: str,
        workspace_path: Path,
        system_name: str | None = None,
    ) -> PhaseGateResult:
        """Check if a phase can be completed with quality enforcement.

        This method runs the full autofix pipeline and determines if the
        phase meets quality standards for completion. For phases that involve
        graph database contracts (Outline, Logic, Verify), it also runs
        contract validation.

        Args:
            phase: SOLVE phase being completed (S, O, L, V, or E)
            adr_number: ADR number for the feature
            workspace_path: Path to the workspace to validate
            system_name: Name of the system for contract validation (required for O, L, V phases)

        Returns:
            PhaseGateResult with detailed information about fixes and validation

        Raises:
            PhaseValidationError: If critical errors prevent gate checking
        """
        logger.info(f"Checking phase gate for {phase} phase of ADR {adr_number}")

        try:
            # Collect all Python files in workspace
            python_files = list(workspace_path.rglob("*.py"))
            if not python_files:
                logger.warning(f"No Python files found in {workspace_path}")
                return PhaseGateResult(
                    can_proceed=True,
                    fixes_applied=[],
                    lessons_created=[],
                    validation_errors=[],
                    metadata={"message": "No Python files to validate"},
                )

            file_paths = [str(f) for f in python_files]
            logger.info(f"Found {len(file_paths)} Python files to check")

            # Stage 1: Run automated fixes
            fixes_applied = []
            if self.autofix_config.enable_auto_fixers:
                logger.info("Running Stage 1: Automated fixes")
                fixer = AutoFixerRunner(self.autofix_config)
                fix_result = await fixer.run_all_fixers(file_paths)

                if fix_result.success and fix_result.files_changed:
                    fixes_applied.append(fix_result)
                    logger.info(
                        f"Applied fixes to {len(fix_result.files_changed)} files, "
                        f"fixed {fix_result.errors_fixed} issues",
                    )

            # Stage 2: Run validation
            validation_errors = []
            if self.autofix_config.run_validation:
                logger.info("Running Stage 2: Validation")
                validator = ValidationRunner(self.autofix_config)
                validation_result, analysis_report = await validator.run_all_validators(
                    file_paths
                )

                if not validation_result.success:
                    validation_errors = validation_result.errors
                    logger.warning(f"Found {len(validation_errors)} validation errors")

            # Convert autofix results to lessons
            lessons_created = []
            if fixes_applied:
                logger.info("Converting fixes to lessons learned")
                lessons = await self._create_lessons_from_fixes(
                    fixes_applied, phase, adr_number
                )
                lessons_created.extend(lessons)

            # Run contract validation for phases that require it
            contract_validation_result = None
            contract_validation_passed = True

            if (
                self._requires_contract_validation(phase)
                and self.enable_contract_validation
                and system_name
            ):
                logger.info(
                    f"Running contract validation for phase {phase} and system {system_name}",
                )
                contract_validation_result = (
                    await self.contract_validator.validate_system(
                        system_name,
                    )
                )
                contract_validation_passed = contract_validation_result.passed

                if not contract_validation_passed:
                    logger.error(
                        f"Contract validation failed for phase {phase}: "
                        f"{len(contract_validation_result.critical_issues)} critical issues, "
                        f"{len(contract_validation_result.error_issues)} errors found",
                    )

                    # Convert contract validation issues to lessons
                    contract_lessons = (
                        await self._create_lessons_from_contract_validation(
                            contract_validation_result,
                            phase,
                            adr_number,
                        )
                    )
                    lessons_created.extend(contract_lessons)
                else:
                    logger.info("✅ Contract validation passed")
            elif self._requires_contract_validation(phase) and system_name is None:
                logger.warning(
                    f"Phase {phase} requires contract validation but no system_name provided",
                )

            # Determine if phase can proceed
            can_proceed = len(validation_errors) == 0 and contract_validation_passed

            if not can_proceed:
                failure_reasons = []
                if (
                    len(validation_errors) > 0
                    and self.autofix_config.fail_on_validation_error
                ):
                    failure_reasons.append(
                        f"{len(validation_errors)} validation errors"
                    )
                if not contract_validation_passed:
                    failure_reasons.append("contract validation failed")

                logger.error(
                    f"Phase {phase} cannot proceed: {', '.join(failure_reasons)}"
                )

            return PhaseGateResult(
                can_proceed=can_proceed,
                fixes_applied=fixes_applied,
                lessons_created=lessons_created,
                validation_errors=validation_errors,
                contract_validation_result=contract_validation_result,
                metadata={
                    "phase": phase,
                    "adr_number": adr_number,
                    "system_name": system_name,
                    "files_checked": len(file_paths),
                    "autofix_enabled": self.autofix_config.enable_auto_fixers,
                    "validation_enabled": self.autofix_config.run_validation,
                    "contract_validation_enabled": self.enable_contract_validation,
                    "contract_validation_required": self._requires_contract_validation(
                        phase
                    ),
                    "contract_validation_passed": contract_validation_passed,
                },
            )

        except Exception as e:
            logger.error(f"Critical error during phase gate check: {e}")
            raise PhaseValidationError(
                f"Failed to check phase gate: {e}",
                phase=phase,
                details={"error": str(e)},
            ) from e

    async def _create_lessons_from_fixes(
        self,
        fix_results: list[AutofixResult],
        phase: str,
        adr_number: str,
    ) -> list[Lesson]:
        """Convert autofix results into lessons learned.

        Each fix becomes a lesson that helps prevent similar issues in future.

        Args:
            fix_results: List of fixes applied by autofix
            phase: Current SOLVE phase
            adr_number: ADR number for context

        Returns:
            List of lessons created from fixes
        """
        lessons = []

        for fix_result in fix_results:
            # Extract fix details
            fix_result.details.get("fix_type", "automated")
            fixer_count = fix_result.details.get("fixers_used", 0)

            # Create lesson for this batch of fixes
            issue = (
                f"Code quality issues found during {phase} phase: "
                f"{fix_result.errors_fixed} errors across "
                f"{len(fix_result.files_changed)} files"
            )

            resolution = (
                f"Autofix Stage 1 applied {fixer_count} fixers to resolve issues: "
                f"trailing whitespace, missing EOF newlines, import sorting, "
                f"and code formatting violations"
            )

            prevention = (
                "Configure pre-commit hooks with the same fixers used by autofix: "
                "ruff format, ruff check --fix, and custom whitespace/EOF checks. "
                "Run 'solve autofix' locally before committing changes."
            )

            # Capture the lesson
            lesson = await self.lesson_capture.capture_lesson(
                issue=issue,
                resolution=resolution,
                prevention=prevention,
                phase=phase,
                adr_number=adr_number,
            )
            lessons.append(lesson)

            # Log files that were fixed for detailed tracking
            for file_path in fix_result.files_changed[:5]:  # Log first 5
                logger.debug(f"Fixed file: {file_path}")
            if len(fix_result.files_changed) > 5:
                logger.debug(f"...and {len(fix_result.files_changed) - 5} more files")

        return lessons

    def _requires_contract_validation(self, phase: str) -> bool:
        """Determine if a phase requires contract validation.

        Contract validation is required for phases that involve graph database contracts:
        - O (Outline): Contract definition phase - critical for validation
        - L (Logic): Implementation phase - validate contracts are maintained
        - V (Verify): Verification phase - ensure all contracts are satisfied

        Args:
            phase: SOLVE phase (S, O, L, V, or E)

        Returns:
            True if contract validation is required for this phase
        """
        # Contract validation is required for phases that work with graph contracts
        contract_phases = ["O", "L", "V"]
        return phase.upper() in contract_phases

    async def _create_lessons_from_contract_validation(
        self,
        contract_result: ContractValidationResult,
        phase: str,
        adr_number: str,
    ) -> list[Lesson]:
        """Convert contract validation issues into lessons learned.

        Args:
            contract_result: Result from contract validation
            phase: Current SOLVE phase
            adr_number: ADR number for context

        Returns:
            List of lessons created from contract validation issues
        """
        lessons = []

        if not contract_result.issues:
            return lessons

        # Group issues by category
        issues_by_category = {}
        for issue in contract_result.issues:
            category = issue.category
            if category not in issues_by_category:
                issues_by_category[category] = []
            issues_by_category[category].append(issue)

        # Create lessons for each category
        for category, category_issues in issues_by_category.items():
            critical_count = len(
                [i for i in category_issues if i.severity.value == "critical"]
            )
            error_count = len(
                [i for i in category_issues if i.severity.value == "error"]
            )
            warning_count = len(
                [i for i in category_issues if i.severity.value == "warning"]
            )

            # Create issue description
            issue_desc = (
                f"Contract validation found {len(category_issues)} issues in {category}: "
                f"{critical_count} critical, {error_count} errors, {warning_count} warnings"
            )

            # Extract common resolution patterns
            resolution_desc = self._generate_contract_resolution(
                category, category_issues
            )

            # Create prevention guidance
            prevention_desc = self._generate_contract_prevention(category)

            # Capture the lesson
            lesson = await self.lesson_capture.capture_lesson(
                issue=issue_desc,
                resolution=resolution_desc,
                prevention=prevention_desc,
                phase=phase,
                adr_number=adr_number,
                lesson_type="contract_validation",
            )
            lessons.append(lesson)

            # Log specific issues for debugging
            for issue in category_issues[:3]:  # Log first 3 issues
                logger.debug(f"Contract issue: {issue.message} (Node: {issue.node_id})")

        return lessons

    def _generate_contract_resolution(self, category: str, issues: list) -> str:
        """Generate resolution guidance for contract validation issues."""
        category_resolutions = {
            "adr_validation": (
                "Review ADR documents to ensure all required properties are present: "
                "id, title, status, decision, context, and consequences. "
                "Verify ADR status is one of: proposed, accepted, deprecated."
            ),
            "system_validation": (
                "Update System nodes to include all required properties: "
                "name, description, gcp_project, and region. "
                "Ensure GCP project IDs follow naming conventions."
            ),
            "primitive_validation": (
                "Verify all GCP primitives have required base properties: "
                "id, name, type, and archetype_path. "
                "Check type-specific configurations match GCP requirements."
            ),
            "dependency_validation": (
                "Resolve circular dependencies by removing unnecessary dependency edges. "
                "Ensure all critical dependencies have valid targets. "
                "Verify dependency properties specify type and criticality."
            ),
            "communication_validation": (
                "Complete communication contracts with protocol, endpoint, and data_format. "
                "Verify protocol compatibility between node types. "
                "Review SLA requirements for realistic latency and throughput values."
            ),
            "archetype_validation": (
                "Ensure archetype paths point to existing template directories. "
                "Create missing archetype files based on node type requirements."
            ),
        }

        return category_resolutions.get(
            category,
            f"Review and fix {category} issues identified in contract validation.",
        )

    def _generate_contract_prevention(self, category: str) -> str:
        """Generate prevention guidance for contract validation issues."""
        category_prevention = {
            "adr_validation": (
                "Use ADR templates that include all required fields. "
                "Implement validation in ADR creation tools. "
                "Add pre-commit hooks to validate ADR structure."
            ),
            "system_validation": (
                "Use system creation templates with required properties. "
                "Validate GCP project names during system setup. "
                "Implement schema validation for system nodes."
            ),
            "primitive_validation": (
                "Use archetype templates for GCP primitive creation. "
                "Validate primitive configurations against GCP limits. "
                "Implement type-specific validation rules."
            ),
            "dependency_validation": (
                "Design dependency graphs before implementation. "
                "Use topological sort validation during graph creation. "
                "Implement dependency compatibility matrices."
            ),
            "communication_validation": (
                "Define communication contracts during design phase. "
                "Use protocol compatibility validation during graph creation. "
                "Set realistic SLA requirements based on GCP service limits."
            ),
            "archetype_validation": (
                "Maintain archetype template registry. "
                "Validate archetype paths during primitive creation. "
                "Use template generation tools for consistent archetypes."
            ),
        }

        base_prevention = (
            "Run contract validation regularly during development. "
            "Integrate validation into CI/CD pipelines. "
            "Use graph database constraints to prevent invalid data."
        )

        specific_prevention = category_prevention.get(category, "")
        return f"{specific_prevention} {base_prevention}"

    async def enforce_quality_standards(
        self,
        phase: str,
        workspace_path: Path,
        system_name: str | None = None,
        adr_number: str = "quality-check",
    ) -> Result:
        """Enforce quality standards as a blocking operation.

        This is a simplified interface that returns a Result object
        suitable for integration with existing SOLVE workflows.

        Args:
            phase: SOLVE phase being completed
            workspace_path: Path to validate
            system_name: Name of the system for contract validation
            adr_number: ADR number for context

        Returns:
            Result object with success status and artifacts
        """
        gate_result = await self.check_phase_complete(
            phase=phase,
            adr_number=adr_number,
            workspace_path=workspace_path,
            system_name=system_name,
        )

        result = Result(
            success=gate_result.can_proceed,
            message=(
                f"Phase {phase} quality gate: {'PASSED' if gate_result.can_proceed else 'FAILED'}"
            ),
        )

        # Add artifacts
        result.add_artifact("fixes_applied", len(gate_result.fixes_applied))
        result.add_artifact("lessons_created", len(gate_result.lessons_created))
        result.add_artifact("validation_errors", gate_result.validation_errors)
        result.add_artifact(
            "contract_validation_result", gate_result.contract_validation_result
        )

        # Add metadata
        result.add_metadata("phase", phase)
        result.add_metadata("can_proceed", gate_result.can_proceed)
        result.add_metadata(
            "contract_validation_enabled", self.enable_contract_validation
        )

        if gate_result.contract_validation_result:
            result.add_metadata(
                "contract_validation_passed",
                gate_result.contract_validation_result.passed,
            )
            result.add_metadata(
                "contract_issues_count",
                len(gate_result.contract_validation_result.issues),
            )
            result.add_metadata(
                "contract_blocking_issues",
                gate_result.contract_validation_result.has_blocking_issues,
            )

        return result
