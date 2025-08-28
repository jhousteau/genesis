"""Project type detection for autofix system."""

import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from genesis.core.logger import get_logger

logger = get_logger(__name__)


class ProjectType(Enum):
    """Supported project types."""

    PYTHON = "python"
    NODE = "node"
    UNKNOWN = "unknown"


class PythonSubtype(Enum):
    """Python project subtypes."""

    POETRY = "poetry"
    RUFF = "ruff"
    PYPROJECT = "pyproject"
    SETUPTOOLS = "setuptools"
    REQUIREMENTS = "requirements"


@dataclass
class ProjectInfo:
    """Information about detected project."""

    project_type: ProjectType
    python_subtype: Optional[PythonSubtype] = None
    has_docker: bool = False
    has_precommit: bool = False
    available_tools: dict[str, bool] = None
    project_root: Optional[Path] = None

    def __post_init__(self):
        if self.available_tools is None:
            self.available_tools = {}


class ProjectDetector:
    """Detects project type and available tools."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize project detector.

        Args:
            project_root: Root directory to analyze, defaults to current directory
        """
        self.project_root = project_root or Path.cwd()

    def detect(self) -> ProjectInfo:
        """Detect project type and available tools.

        Returns:
            ProjectInfo with detected project details
        """
        logger.debug(f"Detecting project type in {self.project_root}")

        # Detect basic project type
        project_type = self._detect_project_type()
        python_subtype = None

        if project_type == ProjectType.PYTHON:
            python_subtype = self._detect_python_subtype()

        # Detect additional features
        has_docker = self._has_docker()
        has_precommit = self._has_precommit()
        available_tools = self._detect_available_tools(project_type, python_subtype)

        info = ProjectInfo(
            project_type=project_type,
            python_subtype=python_subtype,
            has_docker=has_docker,
            has_precommit=has_precommit,
            available_tools=available_tools,
            project_root=self.project_root,
        )

        logger.info(
            f"Detected project: {project_type.value}"
            + (f" ({python_subtype.value})" if python_subtype else "")
        )

        return info

    def _detect_project_type(self) -> ProjectType:
        """Detect basic project type from files."""

        # Check for Node.js
        if (self.project_root / "package.json").exists():
            return ProjectType.NODE

        # Check for Python
        python_files = [
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "Pipfile",
            "poetry.lock",
        ]

        if any((self.project_root / f).exists() for f in python_files):
            return ProjectType.PYTHON

        # Check for .py files in common locations
        python_dirs = ["src", "lib", ".", "app"]
        for dir_name in python_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and any(dir_path.glob("*.py")):
                return ProjectType.PYTHON

        return ProjectType.UNKNOWN

    def _detect_python_subtype(self) -> PythonSubtype:
        """Detect Python project subtype."""

        # Check pyproject.toml content
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text()

                # Check for Poetry
                if "[tool.poetry]" in content:
                    return PythonSubtype.POETRY

                # Check for Ruff
                if "[tool.ruff]" in content:
                    return PythonSubtype.RUFF

                # Generic pyproject.toml
                return PythonSubtype.PYPROJECT

            except Exception as e:
                logger.warning(f"Could not read pyproject.toml: {e}")

        # Check for setup.py
        if (self.project_root / "setup.py").exists():
            return PythonSubtype.SETUPTOOLS

        # Fallback to requirements
        return PythonSubtype.REQUIREMENTS

    def _has_docker(self) -> bool:
        """Check if project has Docker files."""
        docker_files = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]
        return any((self.project_root / f).exists() for f in docker_files)

    def _has_precommit(self) -> bool:
        """Check if project has pre-commit configuration."""
        return (self.project_root / ".pre-commit-config.yaml").exists()

    def _detect_available_tools(
        self, project_type: ProjectType, python_subtype: Optional[PythonSubtype]
    ) -> dict[str, bool]:
        """Detect which autofix tools are available.

        Args:
            project_type: Detected project type
            python_subtype: Detected Python subtype

        Returns:
            Dictionary mapping tool names to availability
        """
        tools = {}

        # Universal tools
        tools["git"] = self._command_exists("git")
        tools["prettier"] = self._command_exists("prettier") or self._has_npm_bin(
            "prettier"
        )

        if project_type == ProjectType.PYTHON:
            # Python tools
            tools["black"] = self._command_exists("black")
            tools["ruff"] = self._command_exists("ruff")
            tools["isort"] = self._command_exists("isort")
            tools["autopep8"] = self._command_exists("autopep8")
            tools["yamllint"] = self._command_exists("yamllint")

            # Poetry-managed tools
            if python_subtype == PythonSubtype.POETRY:
                tools["poetry"] = self._command_exists("poetry")
                if tools["poetry"]:
                    # Check poetry-managed tools
                    poetry_tools = self._get_poetry_dev_tools()
                    for tool in ["black", "ruff", "isort"]:
                        if tool in poetry_tools:
                            tools[f"poetry-{tool}"] = True

        elif project_type == ProjectType.NODE:
            # Node.js tools
            tools["eslint"] = self._has_npm_bin("eslint")
            tools["prettier"] = tools["prettier"] or self._has_npm_bin("prettier")

        # Docker tools
        if self._has_docker():
            tools["hadolint"] = self._command_exists("hadolint")

        # Pre-commit
        if self._has_precommit():
            tools["pre-commit"] = self._command_exists("pre-commit")

        logger.debug(f"Available tools: {[k for k, v in tools.items() if v]}")
        return tools

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run(["which", command], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _has_npm_bin(self, tool: str) -> bool:
        """Check if npm binary exists in node_modules."""
        npm_bin = self.project_root / "node_modules" / ".bin" / tool
        return npm_bin.exists()

    def _get_poetry_dev_tools(self) -> list[str]:
        """Get list of tools managed by Poetry."""
        try:
            result = subprocess.run(
                ["poetry", "show", "--dev"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.project_root,
            )

            tools = []
            for line in result.stdout.split("\n"):
                if line.strip():
                    tool_name = line.split()[0]
                    tools.append(tool_name)

            return tools

        except (subprocess.CalledProcessError, FileNotFoundError):
            return []
