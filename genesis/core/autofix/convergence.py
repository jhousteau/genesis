"""Convergent fixing implementation for autofix system."""

import subprocess
from dataclasses import dataclass
from typing import Optional

from genesis.core.logger import get_logger

from .errors import ConvergenceError

logger = get_logger(__name__)


@dataclass
class ConvergenceResult:
    """Result of convergent fixing process."""

    converged: bool
    runs: int
    max_runs: int
    final_command: str


class ConvergentFixer:
    """Implements convergent fixing - runs commands until no changes occur."""

    def __init__(self, max_runs: Optional[int] = None, dry_run: Optional[bool] = None):
        """Initialize convergent fixer.

        Args:
            max_runs: Maximum number of runs before giving up
            dry_run: If True, show what would be run without executing
        """
        import os

        if max_runs is None:
            max_runs_str = os.environ.get("AUTOFIX_MAX_RUNS")
            if not max_runs_str:
                raise ValueError("AUTOFIX_MAX_RUNS environment variable is required")
            try:
                max_runs = int(max_runs_str)
                if max_runs <= 0:
                    raise ValueError("AUTOFIX_MAX_RUNS must be positive")
            except ValueError as e:
                raise ValueError(f"Invalid AUTOFIX_MAX_RUNS '{max_runs_str}': {e}")

        self.max_runs = max_runs
        self.dry_run = dry_run if dry_run is not None else False

    def run_until_stable(self, name: str, command: str) -> ConvergenceResult:
        """Run command until git diff shows no changes.

        Args:
            name: Human-readable name for the operation
            command: Shell command to run

        Returns:
            ConvergenceResult with convergence status and metadata

        Raises:
            ConvergenceError: If command fails or doesn't converge
        """
        logger.info(f"Running {name} with convergent fixing...")

        if self.dry_run:
            logger.info(f"Would run: {command}")
            return ConvergenceResult(
                converged=True, runs=0, max_runs=self.max_runs, final_command=command
            )

        for run_count in range(1, self.max_runs + 1):
            # Capture git status before
            try:
                before = subprocess.run(
                    ["git", "diff", "--name-only"],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
            except subprocess.CalledProcessError as e:
                raise ConvergenceError(f"Failed to get git status before {name}: {e}")

            # Run the command
            logger.debug(f"Running {name} iteration {run_count}: {command}")
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False,  # Allow non-zero exit codes for some tools
                )

                # Log command output if there were issues
                if result.returncode != 0:
                    logger.warning(
                        f"{name} returned non-zero exit code {result.returncode}"
                    )
                    if result.stderr:
                        logger.debug(f"{name} stderr: {result.stderr}")

            except Exception as e:
                raise ConvergenceError(f"Failed to run {name}: {e}")

            # Capture git status after
            try:
                after = subprocess.run(
                    ["git", "diff", "--name-only"],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
            except subprocess.CalledProcessError as e:
                raise ConvergenceError(f"Failed to get git status after {name}: {e}")

            # If no changes, we've converged
            if before == after:
                logger.info(f"✅ {name} stable after {run_count} run(s)")
                return ConvergenceResult(
                    converged=True,
                    runs=run_count,
                    max_runs=self.max_runs,
                    final_command=command,
                )

            logger.debug(f"🔄 {name} made changes, running again...")

        # Didn't converge within max_runs
        logger.warning(f"⚠️ {name} didn't stabilize after {self.max_runs} runs")
        return ConvergenceResult(
            converged=False,
            runs=self.max_runs,
            max_runs=self.max_runs,
            final_command=command,
        )

    def run_multiple_until_stable(
        self, commands: list[tuple[str, str]]
    ) -> list[ConvergenceResult]:
        """Run multiple commands with convergent fixing.

        Args:
            commands: List of (name, command) tuples

        Returns:
            List of ConvergenceResult for each command
        """
        results = []

        for name, command in commands:
            result = self.run_until_stable(name, command)
            results.append(result)

            # Continue even if one command doesn't converge
            if not result.converged:
                logger.warning(f"Command '{name}' did not converge, continuing...")

        return results
