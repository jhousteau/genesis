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


@dataclass
class PhaseGateResult:
    """Result of phase gate check with quality enforcement."""

    can_proceed: bool
    fixes_applied: list[AutofixResult]
    lessons_created: list[Lesson]
    validation_errors: list[dict[str, Any]]
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
    ):
        """Initialize the phase gatekeeper.

        Args:
            autofix_config: Configuration for autofix system
            lessons_dir: Directory for storing lessons (defaults to .solve/lessons)
        """
        self.autofix_config = autofix_config or AutofixConfig()
        self.lesson_capture = LessonCapture(lessons_dir)
        logger.info("Initialized PhaseGatekeeper")

    async def check_phase_complete(
        self,
        phase: str,
        adr_number: str,
        workspace_path: Path,
    ) -> PhaseGateResult:
        """Check if a phase can be completed with quality enforcement.

        This method runs the full autofix pipeline and determines if the
        phase meets quality standards for completion.

        Args:
            phase: SOLVE phase being completed (S, O, L, V, or E)
            adr_number: ADR number for the feature
            workspace_path: Path to the workspace to validate

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

            # Determine if phase can proceed
            can_proceed = len(validation_errors) == 0
            if not can_proceed and self.autofix_config.fail_on_validation_error:
                logger.error(
                    f"Phase {phase} cannot proceed: {len(validation_errors)} "
                    "validation errors remain",
                )

            return PhaseGateResult(
                can_proceed=can_proceed,
                fixes_applied=fixes_applied,
                lessons_created=lessons_created,
                validation_errors=validation_errors,
                metadata={
                    "phase": phase,
                    "adr_number": adr_number,
                    "files_checked": len(file_paths),
                    "autofix_enabled": self.autofix_config.enable_auto_fixers,
                    "validation_enabled": self.autofix_config.run_validation,
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

    async def enforce_quality_standards(
        self,
        phase: str,
        workspace_path: Path,
    ) -> Result:
        """Enforce quality standards as a blocking operation.

        This is a simplified interface that returns a Result object
        suitable for integration with existing SOLVE workflows.

        Args:
            phase: SOLVE phase being completed
            workspace_path: Path to validate

        Returns:
            Result object with success status and artifacts
        """
        gate_result = await self.check_phase_complete(
            phase=phase,
            adr_number="quality-check",
            workspace_path=workspace_path,
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

        # Add metadata
        result.add_metadata("phase", phase)
        result.add_metadata("can_proceed", gate_result.can_proceed)

        return result
