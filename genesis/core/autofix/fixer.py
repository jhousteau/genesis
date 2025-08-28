"""Main AutoFixer orchestrator class."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from genesis.core.logger import get_logger

from .convergence import ConvergentFixer
from .detectors import ProjectDetector, ProjectInfo
from .errors import AutoFixError
from .stages import StageOrchestrator, StageResult

logger = get_logger(__name__)


@dataclass
class AutoFixResult:
    """Result from running AutoFixer."""

    success: bool
    project_info: ProjectInfo
    stage_results: list[StageResult]
    total_runs: int
    files_staged: bool = False
    dry_run: bool = False
    error: Optional[str] = None


class AutoFixer:
    """Main autofix orchestrator class.

    Provides a high-level interface for running multi-stage autofix
    with convergent fixing across different project types.
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        max_iterations: int = 5,
        stage_all_files: bool = True,
        run_validation: bool = True,
    ):
        """Initialize AutoFixer.

        Args:
            project_root: Project root directory, defaults to current directory
            max_iterations: Maximum convergent fixing iterations per stage
            stage_all_files: Whether to stage files before and after fixing
            run_validation: Whether to run validation stage at the end
        """
        self.project_root = project_root or Path.cwd()
        self.max_iterations = max_iterations
        self.stage_all_files = stage_all_files
        self.run_validation = run_validation

        # Initialize components
        self.detector = ProjectDetector(self.project_root)
        self.orchestrator = StageOrchestrator()

    def run(self, dry_run: bool = False) -> AutoFixResult:
        """Run full autofix process.

        Args:
            dry_run: If True, show what would be done without making changes

        Returns:
            AutoFixResult with detailed execution information
        """
        logger.info("🔧 Starting Genesis AutoFixer...")

        try:
            # Detect project type and tools
            project_info = self.detector.detect()

            # Stage files before fixing (if not dry run)
            files_staged = False
            if self.stage_all_files and not dry_run:
                files_staged = self._stage_all_files()
            elif dry_run:
                logger.info("📦 Would stage all files (skipped in dry-run)")

            # Initialize convergent fixer
            convergent_fixer = ConvergentFixer(
                max_runs=self.max_iterations, dry_run=dry_run
            )

            # Run all stages
            stage_results = self.orchestrator.run_all(project_info, convergent_fixer)

            # Stage files after fixing (if not dry run)
            if self.stage_all_files and not dry_run:
                self._stage_all_files()
                logger.info("📦 Staged all formatted files")
            elif dry_run:
                logger.info("📦 Would stage all formatted files (skipped in dry-run)")

            # Calculate total runs
            total_runs = sum(
                len(result.convergence_results) for result in stage_results
            )

            # Determine overall success
            success = any(result.success for result in stage_results)

            result = AutoFixResult(
                success=success,
                project_info=project_info,
                stage_results=stage_results,
                total_runs=total_runs,
                files_staged=files_staged,
                dry_run=dry_run,
            )

            self._log_summary(result)
            return result

        except Exception as e:
            logger.error(f"AutoFixer failed: {e}")
            return AutoFixResult(
                success=False,
                project_info=ProjectInfo(
                    project_type=self.detector._detect_project_type()
                ),
                stage_results=[],
                total_runs=0,
                dry_run=dry_run,
                error=str(e),
            )

    def run_stage_only(
        self, stage_types: list[str], dry_run: bool = False
    ) -> AutoFixResult:
        """Run only specific stages.

        Args:
            stage_types: List of stage types to run ('basic', 'formatter', 'linter')
            dry_run: If True, show what would be done without making changes

        Returns:
            AutoFixResult with execution information
        """
        logger.info(f"🔧 Running Genesis AutoFixer stages: {', '.join(stage_types)}")

        try:
            project_info = self.detector.detect()

            # Filter stages
            filtered_stages = [
                stage
                for stage in self.orchestrator.stages
                if stage.stage_type.value in stage_types
            ]

            if not filtered_stages:
                raise AutoFixError(f"No stages found for types: {stage_types}")

            # Create temporary orchestrator with filtered stages
            temp_orchestrator = StageOrchestrator(filtered_stages)

            convergent_fixer = ConvergentFixer(
                max_runs=self.max_iterations, dry_run=dry_run
            )

            stage_results = temp_orchestrator.run_all(project_info, convergent_fixer)

            total_runs = sum(
                len(result.convergence_results) for result in stage_results
            )

            success = any(result.success for result in stage_results)

            result = AutoFixResult(
                success=success,
                project_info=project_info,
                stage_results=stage_results,
                total_runs=total_runs,
                dry_run=dry_run,
            )

            self._log_summary(result)
            return result

        except Exception as e:
            logger.error(f"AutoFixer stage run failed: {e}")
            return AutoFixResult(
                success=False,
                project_info=ProjectInfo(
                    project_type=self.detector._detect_project_type()
                ),
                stage_results=[],
                total_runs=0,
                dry_run=dry_run,
                error=str(e),
            )

    def _stage_all_files(self) -> bool:
        """Stage all files with git add -A.

        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to stage files: {e}")
            return False

    def _log_summary(self, result: AutoFixResult) -> None:
        """Log summary of autofix results."""
        logger.info("")

        if result.dry_run:
            logger.info("✅ Dry run complete! (no changes were made)")
        elif result.success:
            logger.info("✅ AutoFixer complete!")
        else:
            logger.error("❌ AutoFixer failed!")

        # Log stage summary
        successful_stages = [r for r in result.stage_results if r.success]
        if successful_stages:
            logger.info(
                f"📊 Executed {len(successful_stages)} stages with {result.total_runs} total runs"
            )

        # Log next steps
        logger.info("")
        logger.info("📝 Next steps:")
        if result.dry_run:
            logger.info("   - Run without --dry-run to apply changes")
        elif result.success:
            logger.info("   - Review changes: git diff --staged")
            logger.info("   - Commit: git commit -m 'your message'")

        # Log convergence details
        non_converged = [
            (stage.stage_name, conv_result)
            for stage in result.stage_results
            for conv_result in stage.convergence_results
            if not conv_result.converged
        ]

        if non_converged:
            logger.warning("")
            logger.warning("⚠️ Some tools didn't converge to stable state:")
            for stage_name, conv_result in non_converged:
                logger.warning(f"   - {stage_name}: {conv_result.final_command}")

    def get_available_tools(self) -> dict:
        """Get information about available tools for current project.

        Returns:
            Dictionary with project info and available tools
        """
        project_info = self.detector.detect()
        return {
            "project_type": project_info.project_type.value,
            "python_subtype": (
                project_info.python_subtype.value
                if project_info.python_subtype
                else None
            ),
            "has_docker": project_info.has_docker,
            "has_precommit": project_info.has_precommit,
            "available_tools": project_info.available_tools,
        }
