"""
ValidationRunner - Stage 2 of the autofix system.

Runs all validation tools to identify remaining issues after automated fixes.
Now includes intelligent error analysis for optimized Stage 3 processing.
Based on ADR-004: Comprehensive Autofix/Autocommit System Architecture
"""

import logging
import time
from typing import Any

from .analyzer import AnalysisReport, analyze_validation_results
from .models import AutofixConfig, ValidationResult
from .validators import MypyChecker, RuffChecker, SecurityChecker

logger = logging.getLogger(__name__)


async def validate_files(file_paths: list[Any]) -> dict[str, Any]:
    """
    Validate files after fixes have been applied.

    Constitutional AI validation ensuring fixes didn't break functionality.

    Args:
        file_paths: List of file paths to validate

    Returns:
        Dict with validation results including all_passed flag
    """
    from pathlib import Path

    # Convert to Path objects and filter existing files
    valid_paths = []
    for fp in file_paths:
        path = Path(fp) if not isinstance(fp, Path) else fp
        if path.exists() and path.suffix == ".py":
            valid_paths.append(str(path))

    if not valid_paths:
        return {"all_passed": True, "message": "No Python files to validate"}

    # Create a temporary config for validation
    config = AutofixConfig(run_validation=True)
    runner = ValidationRunner(config)

    try:
        validation_result, _ = await runner.run_all_validators(valid_paths)

        # Consider validation passed if no critical errors
        # (warnings and minor issues are acceptable)
        critical_errors = []
        for error in validation_result.errors:
            # Filter out non-critical validation issues
            error_code = getattr(error, "code", "")
            if error_code in ["F821", "F822", "E999"]:  # Undefined name, syntax errors
                critical_errors.append(error)

        all_passed = len(critical_errors) == 0

        return {
            "all_passed": all_passed,
            "total_errors": len(validation_result.errors),
            "critical_errors": len(critical_errors),
            "warnings": len(validation_result.warnings),
            "files_validated": len(valid_paths),
            "validation_time": validation_result.time_taken,
        }

    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        # Fail safe - if validation crashes, assume changes are bad
        return {
            "all_passed": False,
            "error": str(e),
            "files_validated": len(valid_paths),
        }


class ValidationRunner:
    """Runs all validation tools to identify remaining issues"""

    def __init__(self, config: AutofixConfig):
        self.config = config
        self.validators = [
            RuffChecker(),  # --no-fix mode
            MypyChecker(),  # type validation
            SecurityChecker(),  # security issues
            # PytestRunner removed - was causing timeouts and should be separate
        ]

    async def run_all_validators(
        self,
        paths: list[str],
    ) -> tuple[ValidationResult, AnalysisReport | None]:
        """Run all validators and collect results with intelligent analysis"""
        start_time = time.time()
        all_errors = []
        all_warnings = []
        overall_success = True

        for validator in self.validators:
            if not self.config.run_validation:
                break

            validator_name = validator.__class__.__name__
            logger.debug(f"Running {validator_name}...")
            result = await validator.validate(paths)

            if not result.success:
                overall_success = False
                logger.debug(
                    f"  {validator_name} found {len(result.errors)} errors, "
                    f"{len(result.warnings)} warnings",
                )
            else:
                logger.debug(
                    f"  {validator_name} passed with {len(result.warnings)} warnings"
                )

            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        end_time = time.time()

        validation_result = ValidationResult(
            success=overall_success,
            errors=all_errors,
            warnings=all_warnings,
            time_taken=end_time - start_time,
        )

        # Perform intelligent analysis if errors were found
        analysis_report = None
        if all_errors:
            logger.info("Performing intelligent error analysis...")
            analysis_report = await analyze_validation_results(validation_result)

            # Log summary
            logger.info(
                f"Analysis identified {len(analysis_report.error_groups)} error groups"
            )
            logger.info(
                f"Estimated Stage 3 cost: ${analysis_report.estimated_total_cost:.2f}"
            )

            # Save analysis report if configured
            if self.config.save_analysis_report:
                self._save_analysis_report(analysis_report)

        return validation_result, analysis_report

    async def run_single_validator(
        self, validator_name: str, paths: list[str]
    ) -> ValidationResult:
        """Run a specific validator by name"""
        validator_map = {
            "ruff": RuffChecker(),
            "mypy": MypyChecker(),
            "security": SecurityChecker(),
            # "pytest": PytestRunner(),  # Removed - use separate test commands
        }

        if validator_name not in validator_map:
            return ValidationResult(
                success=False,
                errors=[{"error": f"Unknown validator: {validator_name}"}],
                warnings=[],
                time_taken=0,
            )

        start_time = time.time()
        result = await validator_map[validator_name].validate(paths)
        end_time = time.time()

        result.time_taken = end_time - start_time
        return result

    def get_available_validators(self) -> list[str]:
        """Get list of available validator names"""
        return ["ruff", "mypy", "security", "pytest"]

    def _save_analysis_report(self, report: AnalysisReport) -> None:
        """Save the analysis report to a file."""
        from datetime import datetime

        from .config import EVAL_BASE_DIR, ensure_eval_directories

        # Create reports directory under the new eval structure
        ensure_eval_directories()
        reports_dir = EVAL_BASE_DIR / "reports" / "analysis"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"analysis_{timestamp}.md"

        with open(report_path, "w") as f:
            f.write(report.to_markdown())

        logger.info(f"Analysis report saved to {report_path}")

    def filter_errors_by_severity(
        self,
        errors: list[dict[str, Any]],
        min_severity: str = "error",
    ) -> list[dict[str, Any]]:
        """Filter errors by minimum severity level"""
        severity_levels = {
            "error": 3,
            "warning": 2,
            "info": 1,
        }

        min_level = severity_levels.get(min_severity, 3)

        return [
            error
            for error in errors
            if severity_levels.get(error.get("severity", "error"), 3) >= min_level
        ]


async def run_validators(paths: list[str]) -> None:
    """Run all validators on the given paths and print results.

    This is a convenience function for CLI usage.
    """
    config = AutofixConfig(run_validation=True)
    runner = ValidationRunner(config)

    result, analysis_report = await runner.run_all_validators(paths)

    # Log results
    if result.errors:
        logger.info(f"Found {len(result.errors)} errors:")

        # Group errors by tool for better readability
        errors_by_tool: dict[str, list[dict[str, Any]]] = {}
        for error in result.errors:
            tool = error.get("tool", "unknown")
            if tool not in errors_by_tool:
                errors_by_tool[tool] = []
            errors_by_tool[tool].append(error)

        # Show errors grouped by tool
        for tool, tool_errors in errors_by_tool.items():
            logger.info(f"  {tool} ({len(tool_errors)} errors):")
            for error in tool_errors[:5]:  # Show first 5 per tool
                file_info = f"{error.get('file', 'unknown')}:{error.get('line', 0)}"
                code = error.get("code", "")
                message = error.get("message", "No message")
                logger.info(f"    {file_info} {code}: {message}")
            if len(tool_errors) > 5:
                logger.info(f"    ... and {len(tool_errors) - 5} more {tool} errors")

    if result.warnings:
        logger.info(f"Found {len(result.warnings)} warnings:")
        for warning in result.warnings[:5]:  # Show first 5
            file_info = f"{warning.get('file', 'unknown')}:{warning.get('line', 0)}"
            message = warning.get("message", "No message")
            tool = warning.get("tool", "unknown")
            logger.info(f"  [{tool}] {file_info}: {message}")
        if len(result.warnings) > 5:
            logger.info(f"  ... and {len(result.warnings) - 5} more warnings")

    if not result.errors and not result.warnings:
        logger.info("No issues found!")

    logger.info(f"Validation completed in {result.time_taken:.2f}s")

    # Log analysis report if available
    if analysis_report:
        logger.info("")
        logger.info("=" * 50)
        logger.info("Stage 2 Analysis Report")
        logger.info("=" * 50)
        logger.info(f"Identified {len(analysis_report.error_groups)} error groups")
        logger.info(
            f"Estimated Stage 3 cost: ${analysis_report.estimated_total_cost:.2f}"
        )
        logger.info(f"Overall confidence: {analysis_report.confidence_score:.1%}")

        if analysis_report.recommended_actions:
            logger.info("")
            logger.info("Top recommendations:")
            for i, action in enumerate(analysis_report.recommended_actions[:3], 1):
                logger.info(f"  {i}. {action}")
