"""
AutoFixerRunner - Stage 1 of the autofix system.

Orchestrates all automated fixing tools for free, fast fixes.
Based on ADR-004: Comprehensive Autofix/Autocommit System Architecture
"""

import asyncio
import logging
import time

from .fixers import (
    EndOfFileFixer,
    RuffAutoFixer,
    RuffFormatter,
    TrailingWhitespaceFixer,
)
from .models import AutofixConfig, FixResult
from .typescript_fixer import TypeScriptLintFixer

logger = logging.getLogger(__name__)


class AutoFixerRunner:
    """Orchestrates all automated fixing tools"""

    def __init__(self, config: AutofixConfig):
        self.config = config
        self.fixers = [
            TrailingWhitespaceFixer(),
            EndOfFileFixer(),
            RuffAutoFixer(),  # --fix mode
            RuffFormatter(),  # format mode
            TypeScriptLintFixer(),  # ESLint --fix for TypeScript/JavaScript
        ]
        self.max_iterations = config.max_fix_iterations

    async def run_all_fixers(self, paths: list[str]) -> FixResult:
        """Run fixers iteratively until no changes"""
        start_time = time.time()
        total_files_changed = []
        total_errors_fixed = 0
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            changes_made = False
            logger.debug(f"Starting iteration {iteration}")

            for fixer in self.fixers:
                if not self.config.enable_auto_fixers:
                    break

                fixer_name = fixer.__class__.__name__
                logger.debug(f"Running {fixer_name}...")
                result = await fixer.fix(paths)

                if result.success and result.files_changed:
                    changes_made = True
                    total_files_changed.extend(result.files_changed)
                    total_errors_fixed += result.errors_fixed
                    logger.debug(
                        f"  {fixer_name} fixed {result.errors_fixed} errors "
                        f"in {len(result.files_changed)} files",
                    )
                    # Log which files were changed in verbose mode
                    if (
                        logger.isEnabledFor(logging.DEBUG)
                        and len(result.files_changed) <= 10
                    ):
                        for file in sorted(result.files_changed)[:5]:
                            logger.debug(f"    - {file}")
                        if len(result.files_changed) > 5:
                            logger.debug(
                                f"    ... and {len(result.files_changed) - 5} more files"
                            )
                else:
                    logger.debug(f"  {fixer_name} made no changes")

            if not changes_made:
                logger.debug(f"No changes in iteration {iteration}, stopping")
                break

        end_time = time.time()

        return FixResult(
            success=True,
            files_changed=list(set(total_files_changed)),
            errors_fixed=total_errors_fixed,
            time_taken=end_time - start_time,
            details={
                "iterations": iteration,
                "fixers_used": len(self.fixers),
                "dry_run": self.config.enable_dry_run,
            },
        )

    def run_single_fixer(self, fixer_name: str, paths: list[str]) -> FixResult:
        """Run a specific fixer by name"""
        fixer_map = {
            "trailing_whitespace": TrailingWhitespaceFixer(),
            "end_of_file": EndOfFileFixer(),
            "ruff_auto": RuffAutoFixer(),
            "ruff_format": RuffFormatter(),
            "typescript_lint": TypeScriptLintFixer(),
        }

        if fixer_name not in fixer_map:
            return FixResult(
                success=False,
                files_changed=[],
                errors_fixed=0,
                time_taken=0,
                details={"error": f"Unknown fixer: {fixer_name}"},
            )

        start_time = time.time()
        result = asyncio.run(fixer_map[fixer_name].fix(paths))
        end_time = time.time()

        result.time_taken = end_time - start_time
        return result

    def get_available_fixers(self) -> list[str]:
        """Get list of available fixer names"""
        return [
            "trailing_whitespace",
            "end_of_file",
            "ruff_auto",
            "ruff_format",
            "typescript_lint",
        ]
