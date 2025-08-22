"""
Main entry point for solve.autofix module.

This allows running the autofix system with:
    python -m solve.autofix [args]

Instead of:
    python -m solve.autofix.runner [args]

This prevents the <frozen runpy> warning that occurs when
importing a module before executing it as a script.
"""

import logging
import sys
from pathlib import Path

from .ignore_utils import collect_python_files
from .llm_fixer import ManualFixOrchestrator
from .models import AutofixConfig, ValidationResult
from .runner import AutoFixerRunner
from .validation import ValidationRunner, run_validators

# Set up module logger
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for autofix CLI."""
    if len(sys.argv) < 2:
        sys.exit(1)

    target_path = Path(sys.argv[1])

    # Check for flags
    verbose = "--verbose" in sys.argv

    # Check for --validate flag
    if len(sys.argv) > 2 and sys.argv[2] == "--validate":
        validate_only = True
        stage = 2  # For validation
    else:
        validate_only = False
        # Parse stage, handling --verbose flag
        stage_args = [arg for arg in sys.argv[2:] if arg != "--verbose"]
        try:
            stage = int(stage_args[0]) if stage_args else 1
            if stage not in [1, 2, 3]:
                logger.error(f"Invalid stage: {stage}. Must be 1, 2, or 3.")
                sys.exit(1)
        except ValueError:
            logger.error(f"Invalid stage: {stage_args[0]}. Must be 1, 2, or 3.")
            sys.exit(1)

    if not target_path.exists():
        logger.error(f"Path not found: {target_path}")
        sys.exit(1)

    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Set up file handler that overwrites each time
    log_file = logs_dir / "autofix.log"
    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
    )

    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
    )

    # Configure root logger
    logging.basicConfig(
        level=log_level, handlers=[file_handler, console_handler], force=True
    )

    # Set autofix module to appropriate level
    logging.getLogger("solve.autofix").setLevel(log_level)

    # For non-verbose mode, only show WARNING and above for other modules
    if not verbose:
        logging.getLogger("solve").setLevel(logging.WARNING)
        # But keep autofix at INFO
        logging.getLogger("solve.autofix").setLevel(logging.INFO)

    # Configure autofix
    config = AutofixConfig(
        enable_auto_fixers=(stage >= 1),
        run_validation=(stage >= 2),
        enable_llm_fixes=(stage >= 3),
    )

    # Run autofix
    runner = AutoFixerRunner(config)

    # Prepare paths
    if target_path.is_file():
        paths = [str(target_path)]
    else:
        # Find all Python files in directory, respecting .solveignore
        paths = collect_python_files(target_path, respect_solveignore=True)

    if not paths:
        logger.error(f"No Python files found in {target_path}")
        sys.exit(1)

    import asyncio

    if validate_only:
        # Run validation only
        logger.info(f"Running validation on {len(paths)} files...")
        asyncio.run(run_validators(paths))
    else:
        # Run autofix stages
        if stage == 1:
            logger.info(f"Running autofix stage 1 on {len(paths)} files...")
        elif stage == 2:
            logger.info(f"Running autofix stages 1-2 on {len(paths)} files...")
        else:  # stage == 3
            logger.info(f"Running autofix stages 1-3 on {len(paths)} files...")

        if verbose:
            logger.debug(f"Files to process: {len(paths)}")
            logger.debug(
                f"Stage 1 (Auto-fixers): {'Enabled' if config.enable_auto_fixers else 'Disabled'}",
            )
            logger.debug(
                f"Stage 2 (Validation): {'Enabled' if config.run_validation else 'Disabled'}",
            )
            logger.debug(
                f"Stage 3 (LLM fixes): {'Enabled' if config.enable_llm_fixes else 'Disabled'}",
            )

        result = asyncio.run(runner.run_all_fixers(paths))

        # Report results
        if result.success:
            logger.info("Autofix completed successfully!")
            logger.info(f"Files changed: {len(result.files_changed)}")
            logger.info(f"Errors fixed: {result.errors_fixed}")
            logger.info(f"Time taken: {result.time_taken:.2f}s")

            if result.files_changed:
                logger.info("Modified files:")
                for file in sorted(result.files_changed):
                    logger.info(f"  - {file}")

            # Run validation if stage >= 2
            if stage >= 2:
                logger.info("Running validation...")
                # First run validation to find issues
                validation_runner = ValidationRunner(config)
                validation_result, analysis_report = asyncio.run(
                    validation_runner.run_all_validators(paths),
                )

                # Log analysis summary if available
                if analysis_report:
                    logger.info(
                        f"Analysis identified {len(analysis_report.error_groups)} error groups",
                    )
                    logger.info(
                        f"Estimated LLM cost: ${analysis_report.estimated_total_cost:.2f}"
                    )

                    # Log top recommendations
                    if analysis_report.recommended_actions:
                        logger.info("Top recommendations:")
                        for i, action in enumerate(
                            analysis_report.recommended_actions[:3], 1
                        ):
                            logger.info(f"  {i}. {action}")

                # If stage 3, run LLM fixes on found issues
                # Include both errors and warnings for LLM fixing
                all_issues = validation_result.errors + validation_result.warnings
                if stage >= 3 and all_issues:
                    logger.info(
                        f"Found {len(all_issues)} issues "
                        f"({len(validation_result.errors)} errors, "
                        f"{len(validation_result.warnings)} warnings). Running LLM fixes...",
                    )
                    if verbose:
                        logger.debug("Initializing Google Gemini for LLM fixes...")
                    llm_fixer = ManualFixOrchestrator(config)
                    # Create a modified validation result with all issues as errors
                    modified_result = ValidationResult(
                        success=validation_result.success,
                        errors=all_issues,
                        warnings=[],
                        time_taken=validation_result.time_taken,
                    )
                    llm_result = asyncio.run(
                        llm_fixer.fix_errors(modified_result, analysis_report)
                    )

                    if llm_result.success:
                        logger.info(
                            f"LLM fixes completed! Fixed {llm_result.errors_fixed} errors"
                        )
                        if llm_result.files_changed:
                            logger.info("Files modified by LLM:")
                            for file in sorted(llm_result.files_changed):
                                logger.info(f"  - {file}")

                        # Check for partial success
                        if llm_result.details and llm_result.details.get(
                            "partial_success"
                        ):
                            logger.warning(
                                "Some batches failed but partial fixes were applied."
                            )
                            batch_failures = llm_result.details.get(
                                "batch_failures", []
                            )
                            if batch_failures:
                                logger.warning(f"Failed batches: {len(batch_failures)}")
                                for failure in batch_failures[:3]:  # Show first 3
                                    logger.warning(
                                        f"  - Batch {failure['batch']}: {failure['error']}",
                                    )

                        # Run validation again to check remaining issues
                        logger.info("Running final validation...")
                        asyncio.run(run_validators(paths))
                    else:
                        logger.error("LLM fixes failed!")
                        if llm_result.details:
                            logger.error(f"Details: {llm_result.details}")
                else:
                    # Just show validation results
                    asyncio.run(run_validators(paths))
        else:
            logger.error("Autofix failed!")
            if result.details:
                logger.error(f"Details: {result.details}")
            sys.exit(1)


if __name__ == "__main__":
    main()
