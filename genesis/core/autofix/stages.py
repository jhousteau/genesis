"""Multi-stage processing definitions for autofix system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from genesis.core.logger import get_logger

from .convergence import ConvergenceResult, ConvergentFixer
from .detectors import ProjectInfo, ProjectType, PythonSubtype

logger = get_logger(__name__)


class StageType(Enum):
    """Types of autofix stages."""

    BASIC = "basic"
    FORMATTER = "formatter"
    LINTER = "linter"
    VALIDATION = "validation"


@dataclass
class StageResult:
    """Result from running a stage."""

    stage_name: str
    stage_type: StageType
    success: bool
    convergence_results: list[ConvergenceResult]
    error: str | None = None


class Stage(ABC):
    """Abstract base class for autofix stages."""

    def __init__(self, name: str, stage_type: StageType):
        self.name = name
        self.stage_type = stage_type

    @abstractmethod
    def get_commands(self, project_info: ProjectInfo) -> list[tuple[str, str]]:
        """Get commands to run for this stage.

        Args:
            project_info: Information about the project

        Returns:
            List of (description, command) tuples
        """
        pass

    def run(
        self, project_info: ProjectInfo, convergent_fixer: ConvergentFixer
    ) -> StageResult:
        """Run this stage with convergent fixing.

        Args:
            project_info: Information about the project
            convergent_fixer: Convergent fixer instance

        Returns:
            StageResult with execution details
        """
        logger.info(f"Running stage: {self.name}")

        try:
            commands = self.get_commands(project_info)

            if not commands:
                logger.debug(f"No commands for stage {self.name}")
                return StageResult(
                    stage_name=self.name,
                    stage_type=self.stage_type,
                    success=True,
                    convergence_results=[],
                )

            convergence_results = convergent_fixer.run_multiple_until_stable(commands)

            # Consider stage successful if any commands ran (even if didn't converge)
            success = len(convergence_results) > 0

            return StageResult(
                stage_name=self.name,
                stage_type=self.stage_type,
                success=success,
                convergence_results=convergence_results,
            )

        except Exception as e:
            logger.error(f"Stage {self.name} failed: {e}")
            return StageResult(
                stage_name=self.name,
                stage_type=self.stage_type,
                success=False,
                convergence_results=[],
                error=str(e),
            )


class BasicFixesStage(Stage):
    """Stage for basic fixes like whitespace and EOF."""

    def __init__(self):
        super().__init__("Basic fixes", StageType.BASIC)

    def get_commands(self, project_info: ProjectInfo) -> list[tuple[str, str]]:
        commands = []

        if project_info.has_precommit and project_info.available_tools.get(
            "pre-commit"
        ):
            commands.extend(
                [
                    (
                        "trailing-whitespace",
                        "pre-commit run trailing-whitespace --all-files",
                    ),
                    (
                        "end-of-file-fixer",
                        "pre-commit run end-of-file-fixer --all-files",
                    ),
                ]
            )

        return commands


class FormatterStage(Stage):
    """Base class for formatter stages."""

    def __init__(self, name: str):
        super().__init__(name, StageType.FORMATTER)


class PythonFormatterStage(FormatterStage):
    """Python formatting stage."""

    def __init__(self):
        super().__init__("Python formatting")

    def get_commands(self, project_info: ProjectInfo) -> list[tuple[str, str]]:
        if project_info.project_type != ProjectType.PYTHON:
            return []

        commands = []

        # Import sorting
        if project_info.python_subtype == PythonSubtype.POETRY:
            if project_info.available_tools.get("poetry-isort"):
                commands.append(("isort", "poetry run isort ."))
        elif project_info.available_tools.get("isort"):
            commands.append(("isort", "isort ."))

        # Black formatting
        if project_info.python_subtype == PythonSubtype.POETRY:
            if project_info.available_tools.get("poetry-black"):
                commands.append(("Black", "poetry run black ."))
        elif project_info.available_tools.get("black"):
            commands.append(("Black", "black ."))
        elif project_info.available_tools.get("autopep8"):
            commands.append(("autopep8", "autopep8 --in-place --recursive ."))

        # Ruff formatting
        if project_info.python_subtype == PythonSubtype.POETRY:
            if project_info.available_tools.get("poetry-ruff"):
                commands.append(("Ruff format", "poetry run ruff format ."))
        elif project_info.available_tools.get("ruff"):
            commands.append(("Ruff format", "ruff format ."))

        return commands


class NodeFormatterStage(FormatterStage):
    """Node.js/TypeScript formatting stage."""

    def __init__(self):
        super().__init__("Node.js formatting")

    def get_commands(self, project_info: ProjectInfo) -> list[tuple[str, str]]:
        if project_info.project_type != ProjectType.NODE:
            return []

        commands = []

        # Prettier
        if project_info.available_tools.get("prettier"):
            if (
                project_info.project_root / "node_modules" / ".bin" / "prettier"
            ).exists():
                commands.append(
                    ("Prettier", "npx prettier --write . --log-level=error")
                )
            else:
                commands.append(("Prettier", "prettier --write . --log-level=error"))

        return commands


class ConfigFormatterStage(FormatterStage):
    """Configuration files formatting stage."""

    def __init__(self):
        super().__init__("Config formatting")

    def get_commands(self, project_info: ProjectInfo) -> list[tuple[str, str]]:
        commands = []

        # Use Prettier for config files if available
        if project_info.available_tools.get("prettier"):
            if (
                project_info.project_root / "node_modules" / ".bin" / "prettier"
            ).exists():
                commands.append(
                    (
                        "Prettier config files",
                        "npx prettier --write '**/*.{json,yaml,yml,md}' --ignore-path .gitignore",
                    )
                )
            else:
                commands.append(
                    (
                        "Prettier config files",
                        "prettier --write '**/*.{json,yaml,yml,md}' --ignore-path .gitignore",
                    )
                )
        elif (
            project_info.project_type == ProjectType.PYTHON
            and project_info.available_tools.get("yamllint")
        ):
            commands.append(("yamllint", "yamllint -d relaxed ."))

        return commands


class LinterStage(Stage):
    """Base class for linter stages."""

    def __init__(self, name: str):
        super().__init__(name, StageType.LINTER)


class PythonLinterStage(LinterStage):
    """Python linting stage."""

    def __init__(self):
        super().__init__("Python linting")

    def get_commands(self, project_info: ProjectInfo) -> list[tuple[str, str]]:
        if project_info.project_type != ProjectType.PYTHON:
            return []

        commands = []

        # Ruff linting
        if project_info.python_subtype == PythonSubtype.POETRY:
            if project_info.available_tools.get("poetry-ruff"):
                commands.append(("Ruff fix", "poetry run ruff check --fix ."))
        elif project_info.available_tools.get("ruff"):
            commands.append(("Ruff fix", "ruff check --fix ."))

        return commands


class NodeLinterStage(LinterStage):
    """Node.js/TypeScript linting stage."""

    def __init__(self):
        super().__init__("Node.js linting")

    def get_commands(self, project_info: ProjectInfo) -> list[tuple[str, str]]:
        if project_info.project_type != ProjectType.NODE:
            return []

        commands = []

        # ESLint
        if project_info.available_tools.get("eslint"):
            commands.append(("ESLint", "npx eslint . --fix --quiet"))

        return commands


class ValidationStage(Stage):
    """Final validation stage."""

    def __init__(self):
        super().__init__("Validation", StageType.VALIDATION)

    def get_commands(self, project_info: ProjectInfo) -> list[tuple[str, str]]:
        commands = []

        if project_info.has_precommit and project_info.available_tools.get(
            "pre-commit"
        ):
            commands.append(("pre-commit validation", "pre-commit run --all-files"))

        return commands


class StageOrchestrator:
    """Orchestrates running multiple stages."""

    def __init__(self, stages: list[Stage] | None = None):
        """Initialize stage orchestrator.

        Args:
            stages: List of stages to run, uses default if None
        """
        self.stages = stages or self._get_default_stages()

    def _get_default_stages(self) -> list[Stage]:
        """Get default stages for multi-stage processing."""
        return [
            BasicFixesStage(),
            PythonFormatterStage(),
            NodeFormatterStage(),
            ConfigFormatterStage(),
            PythonLinterStage(),
            NodeLinterStage(),
            ValidationStage(),
        ]

    def run_all(
        self, project_info: ProjectInfo, convergent_fixer: ConvergentFixer
    ) -> list[StageResult]:
        """Run all stages in sequence.

        Args:
            project_info: Information about the project
            convergent_fixer: Convergent fixer instance

        Returns:
            List of StageResult for each stage
        """
        results = []

        for stage in self.stages:
            result = stage.run(project_info, convergent_fixer)
            results.append(result)

            # Log stage completion
            if result.success:
                logger.info(f"✅ Stage '{stage.name}' completed successfully")
            else:
                logger.warning(f"⚠️ Stage '{stage.name}' failed: {result.error}")

        return results
