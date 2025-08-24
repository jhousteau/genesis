"""Main orchestrator for the smart-commit workflow system."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .detector import ProjectDetector, ProjectType
from .git_integration import CommitType, GitIntegration
from .quality import QualityGate, QualityGateRunner
from .stability import ConvergenceResult, StabilityEngine, Tool
from .tools import ToolCategory, ToolMatrix

logger = logging.getLogger(__name__)


def cli_print(message: str) -> None:
    """Output CLI message to stderr using logging instead of print."""
    # Use INFO level for CLI output to stderr
    logger.info(message)


class ExecutionMode(Enum):
    """Execution modes for smart-commit."""

    AUTOFIX = "autofix"
    TEST = "test"
    TYPECHECK = "typecheck"
    SECURITY = "security"
    ALL = "all"
    INTEGRATION = "integration"


@dataclass
class SmartCommitConfig:
    """Configuration for smart-commit orchestrator."""

    project_root: Path = field(default_factory=Path.cwd)
    max_iterations: int = 10
    dry_run: bool = False
    verbose: bool = False
    parallel: bool = True
    autodetect: bool = True
    project_types: list[ProjectType] = field(default_factory=list)
    skip_tools: set[str] = field(default_factory=set)
    quality_gates_enabled: bool = True
    commit_message: Optional[str] = None
    commit_type: CommitType = CommitType.CHORE


@dataclass
class ExecutionResult:
    """Result of smart-commit execution."""

    success: bool
    mode: ExecutionMode
    detected_types: list[ProjectType]
    tools_run: list[str]
    convergence_result: Optional[ConvergenceResult] = None
    quality_gate_results: dict[str, bool] = field(default_factory=dict)
    commit_sha: Optional[str] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    failed_tools: dict[str, str] = field(
        default_factory=dict
    )  # tool_name -> error message


class SmartCommitOrchestrator:
    """Main orchestrator for smart-commit workflow system."""

    def __init__(self, config: Optional[SmartCommitConfig] = None):
        """Initialize orchestrator."""
        self.config = config or SmartCommitConfig()
        self.detector = ProjectDetector(self.config.project_root)
        self.stability = StabilityEngine(
            self.config.project_root, self.config.max_iterations
        )
        self.git = GitIntegration(self.config.project_root)
        self.quality_runner = QualityGateRunner(self.config.project_root)

        # Detect project types if autodetect is enabled
        if self.config.autodetect:
            self._detect_project_types()

    def _detect_project_types(self):
        """Detect project types if not explicitly set."""
        if not self.config.project_types:
            self.config.project_types = self.detector.get_all_types(threshold=0.3)
            if not self.config.project_types:
                self.config.project_types = [ProjectType.UNKNOWN]

    def execute(self, mode: ExecutionMode) -> ExecutionResult:
        """Execute smart-commit in specified mode."""
        import time

        start_time = time.time()

        # Ensure project types are detected
        self._detect_project_types()

        # Get tools for the mode
        tools = self._get_tools_for_mode(mode)

        if not tools:
            return ExecutionResult(
                success=False,
                mode=mode,
                detected_types=self.config.project_types,
                tools_run=[],
                error_message="No tools available for detected project types",
                execution_time=time.time() - start_time,
            )

        # Filter out skipped tools
        tools = [t for t in tools if t.name not in self.config.skip_tools]

        # Run quality gates if enabled
        quality_results = {}
        if self.config.quality_gates_enabled:
            quality_results = self._run_quality_gates()
            if not all(quality_results.values()):
                return ExecutionResult(
                    success=False,
                    mode=mode,
                    detected_types=self.config.project_types,
                    tools_run=[],
                    quality_gate_results=quality_results,
                    error_message="Quality gate checks failed",
                    execution_time=time.time() - start_time,
                )

        # Execute tools with convergence
        convergence_result = None
        failed_tools = {}
        if mode == ExecutionMode.AUTOFIX:
            convergence_result = self.stability.run_until_stable(tools)
            success = convergence_result.converged
        else:
            # Run tools once for non-autofix modes
            success, failed_tools = self._run_tools_once(tools)

        # Create commit if requested and successful
        commit_sha = None
        if success and self.config.commit_message and not self.config.dry_run:
            commit_sha = self._create_commit()

        return ExecutionResult(
            success=success,
            mode=mode,
            detected_types=self.config.project_types,
            tools_run=[t.name for t in tools],
            convergence_result=convergence_result,
            quality_gate_results=quality_results,
            commit_sha=commit_sha,
            execution_time=time.time() - start_time,
            failed_tools=failed_tools,
        )

    def _get_tools_for_mode(self, mode: ExecutionMode) -> list[Tool]:
        """Get appropriate tools for execution mode."""
        tool_configs = []

        # Map modes to tool categories
        mode_categories = {
            ExecutionMode.AUTOFIX: [ToolCategory.FORMATTER, ToolCategory.LINTER],
            ExecutionMode.TEST: [ToolCategory.TEST_RUNNER],
            ExecutionMode.TYPECHECK: [ToolCategory.TYPE_CHECKER],
            ExecutionMode.SECURITY: [ToolCategory.SECURITY_SCANNER],
            ExecutionMode.ALL: list(ToolCategory),
            ExecutionMode.INTEGRATION: [ToolCategory.TEST_RUNNER, ToolCategory.BUILDER],
        }

        categories = mode_categories.get(mode, [])

        # SOLVE project specific: Only use Python tools to avoid timeouts
        effective_project_types = (
            [ProjectType.PYTHON]
            if any(pt == ProjectType.PYTHON for pt in self.config.project_types)
            else self.config.project_types
        )

        # Get tools for each detected project type
        for project_type in effective_project_types:
            if mode == ExecutionMode.AUTOFIX:
                # Only get autofix-capable tools
                configs = ToolMatrix.get_autofix_tools(project_type)
            else:
                configs = ToolMatrix.get_tools_for_type(project_type, categories)

            tool_configs.extend(configs)

        # Remove duplicates by name
        seen_names = set()
        unique_configs = []
        for config in tool_configs:
            if config.name not in seen_names:
                seen_names.add(config.name)
                unique_configs.append(config)

        # Create tool instances and filter to only available ones
        tools = ToolMatrix.create_tool_instances(unique_configs)
        tools_to_run = [t for t in tools if t.is_available()]

        # Production config: Filter tools based on execution mode
        if mode == ExecutionMode.AUTOFIX:
            # Only essential formatting tools for commits
            essential_tools = {"black", "ruff", "ruff-format"}
            tools_to_run = [t for t in tools_to_run if t.name in essential_tools]
        elif mode == ExecutionMode.TEST:
            # Only test runners for test mode
            test_tools = {
                "pytest",
                "unittest",
                "npm-test",
                "jest",
                "go-test",
                "cargo-test",
            }
            tools_to_run = [t for t in tools_to_run if t.name in test_tools]
        elif mode == ExecutionMode.TYPECHECK:
            # Only type checkers for typecheck mode
            type_tools = {
                "mypy",
                "pyright",
                "tsc",
                "go-vet",
                "cargo-check",
                "terraform-validate",
            }
            tools_to_run = [t for t in tools_to_run if t.name in type_tools]
        elif mode == ExecutionMode.SECURITY:
            # Only security scanners for security mode
            security_tools = {
                "bandit",
                "safety",
                "npm-audit",
                "gosec",
                "cargo-audit",
                "tfsec",
                "checkov",
                "trivy",
            }
            tools_to_run = [t for t in tools_to_run if t.name in security_tools]
        elif mode == ExecutionMode.ALL:
            # For ALL mode, keep all tools but skip the heaviest ones that timeout
            timeout_tools = {"bandit", "safety"}  # These often timeout in CI
            tools_to_run = [t for t in tools_to_run if t.name not in timeout_tools]
        # For INTEGRATION mode, keep all tools

        return tools_to_run

    def _run_tools_once(self, tools: list[Tool]) -> tuple[bool, dict[str, str]]:
        """Run tools once without convergence.

        Returns:
            Tuple of (success, failed_tools_dict)
        """
        all_success = True
        failed_tools = {}
        tools_to_run = []

        # Filter to only available tools
        unavailable = []
        for tool in tools:
            if tool.is_available():
                tools_to_run.append(tool)
            else:
                unavailable.append(tool.name)

        if unavailable and self.config.verbose:
            cli_print(f"Skipping unavailable tools: {', '.join(unavailable)}")

        # Show what we're doing
        if self.config.verbose:
            cli_print(f"\nRunning {len(tools_to_run)} tools...")

        for tool in tools_to_run:
            # Always show what tool is running
            cli_print(f"\nRunning {tool.name}...")
            if self.config.verbose:
                cli_print(f"  Command: {' '.join(tool.command)}")

            if self.config.dry_run:
                cli_print(f"[DRY RUN] Would run: {' '.join(tool.command)}")
                continue

            result = tool.run(self.config.project_root)

            # Always show tool status clearly
            if result.status.value == "success":
                cli_print("  ✓ SUCCESS")
            elif result.status.value == "failure":
                cli_print("  ✗ FAILED")
            elif result.status.value == "skipped":
                cli_print(f"  - SKIPPED: {result.error_message}")

            if result.status.value == "failure":
                all_success = False
                # Track failed tool
                failed_tools[tool.name] = result.error_message or "Unknown error"

                # Show error details
                if result.error_message:
                    error_lines = result.error_message.strip().split("\n")
                    # Show up to 10 lines in non-verbose, all in verbose
                    max_lines = len(error_lines) if self.config.verbose else 10

                    for i, line in enumerate(error_lines[:max_lines]):
                        if line.strip():
                            # Prefix important lines
                            if (
                                "STDERR:" in line
                                or "STDOUT:" in line
                                or "Command:" in line
                            ):
                                cli_print(f"    {line}")
                            else:
                                # Truncate very long lines in non-verbose mode
                                if self.config.verbose or len(line) <= 150:
                                    cli_print(f"      {line}")
                                else:
                                    cli_print(f"      {line[:150]}...")

                    if not self.config.verbose and len(error_lines) > max_lines:
                        cli_print(
                            f"\n    ... {len(error_lines) - max_lines} more lines (use --verbose for full output)",
                        )
                else:
                    # This shouldn't happen with our improved error capture
                    cli_print("    ERROR: No error details captured!")
                    cli_print(f"    Debug: Command was {' '.join(tool.command)}")
                    cli_print("    This is a bug in smart-commit error handling")

        return all_success, failed_tools

    def _run_quality_gates(self) -> dict[str, bool]:
        """Run quality gate checks."""
        results = {}

        gates = [
            QualityGate.RESOURCE_GATES,
            QualityGate.PERMISSION_GATES,
            QualityGate.DEPENDENCY_GATES,
            QualityGate.CONFIGURATION_GATES,
            QualityGate.STATE_GATES,
        ]

        for gate in gates:
            if self.config.verbose:
                cli_print(f"Checking quality gate: {gate.value}")

            result = self.quality_runner.run_gate(gate)
            results[gate.value] = result.passed

            if not result.passed and self.config.verbose:
                for check in result.failed_checks:
                    cli_print(f"  Failed: {check}")

        return results

    def _create_commit(self) -> Optional[str]:
        """Create a git commit with the changes."""
        if not self.git.has_changes():
            if self.config.verbose:
                cli_print("No changes to commit")
            return None

        # Generate commit message if not provided
        if not self.config.commit_message:
            self.config.commit_message = self.git.generate_commit_message(
                self.config.commit_type
            )

        # Stage all changes
        self.git.stage_all()

        # Create commit
        commit_sha = self.git.commit(self.config.commit_message)

        if self.config.verbose:
            cli_print(f"Created commit: {commit_sha}")

        return commit_sha

    def get_status(self) -> dict[str, Any]:
        """Get current status of the project."""
        return {
            "project_root": str(self.config.project_root),
            "detected_types": [t.value for t in self.config.project_types],
            "available_tools": self._get_available_tools(),
            "git_status": self.git.get_status(),
            "quality_gates": self.quality_runner.get_available_gates(),
        }

    def _get_available_tools(self) -> dict[str, list[str]]:
        """Get list of available tools by category."""
        available: dict[str, list[str]] = {}

        for project_type in self.config.project_types:
            for category in ToolCategory:
                configs = ToolMatrix.get_tools_for_type(project_type, [category])
                tools = ToolMatrix.create_tool_instances(configs)

                category_name = category.value
                if category_name not in available:
                    available[category_name] = []

                for tool in tools:
                    if (
                        tool.is_available()
                        and tool.name not in available[category_name]
                    ):
                        available[category_name].append(tool.name)

        return available
