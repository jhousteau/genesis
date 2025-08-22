"""Technology-specific tool configurations."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .detector import ProjectType
from .stability import Tool


class ToolCategory(Enum):
    """Categories of development tools."""

    FORMATTER = "formatter"
    LINTER = "linter"
    TYPE_CHECKER = "type_checker"
    TEST_RUNNER = "test_runner"
    SECURITY_SCANNER = "security_scanner"
    BUILDER = "builder"
    PACKAGE_MANAGER = "package_manager"


@dataclass
class ToolConfig:
    """Configuration for a specific tool."""

    name: str
    category: ToolCategory
    command: list[str]
    check_command: list[str]
    autofix_command: Optional[list[str]] = None
    config_files: list[str] = field(default_factory=list)
    priority: int = 0  # Higher priority tools run first


class ToolMatrix:
    """Matrix of tools for different project types."""

    TOOL_CONFIGS: dict[ProjectType, dict[ToolCategory, list[ToolConfig]]] = {
        ProjectType.PYTHON: {
            ToolCategory.FORMATTER: [
                ToolConfig(
                    name="black",
                    category=ToolCategory.FORMATTER,
                    command=["black", "."],
                    check_command=["black", "--version"],
                    autofix_command=["black", "."],
                    config_files=["pyproject.toml", ".black"],
                    priority=100,
                ),
                ToolConfig(
                    name="ruff-format",
                    category=ToolCategory.FORMATTER,
                    command=["ruff", "format", "."],
                    check_command=["ruff", "--version"],
                    autofix_command=["ruff", "format", "."],
                    config_files=["pyproject.toml", "ruff.toml"],
                    priority=90,
                ),
                ToolConfig(
                    name="isort",
                    category=ToolCategory.FORMATTER,
                    command=["isort", "."],
                    check_command=["isort", "--version"],
                    autofix_command=["isort", "."],
                    config_files=["pyproject.toml", ".isort.cfg"],
                    priority=80,
                ),
            ],
            ToolCategory.LINTER: [
                ToolConfig(
                    name="ruff",
                    category=ToolCategory.LINTER,
                    command=["ruff", "check", "."],
                    check_command=["ruff", "--version"],
                    autofix_command=["ruff", "check", "--fix", "."],
                    config_files=["pyproject.toml", "ruff.toml"],
                    priority=100,
                ),
                ToolConfig(
                    name="flake8",
                    category=ToolCategory.LINTER,
                    command=["flake8", "."],
                    check_command=["flake8", "--version"],
                    config_files=[".flake8", "setup.cfg"],
                    priority=70,
                ),
                ToolConfig(
                    name="pylint",
                    category=ToolCategory.LINTER,
                    command=["pylint", "**/*.py"],
                    check_command=["pylint", "--version"],
                    config_files=[".pylintrc", "pyproject.toml"],
                    priority=60,
                ),
            ],
            ToolCategory.TYPE_CHECKER: [
                ToolConfig(
                    name="mypy",
                    category=ToolCategory.TYPE_CHECKER,
                    command=["mypy", "."],
                    check_command=["mypy", "--version"],
                    config_files=["mypy.ini", "pyproject.toml"],
                    priority=100,
                ),
                ToolConfig(
                    name="pyright",
                    category=ToolCategory.TYPE_CHECKER,
                    command=["pyright"],
                    check_command=["pyright", "--version"],
                    config_files=["pyrightconfig.json"],
                    priority=80,
                ),
            ],
            ToolCategory.TEST_RUNNER: [
                ToolConfig(
                    name="pytest",
                    category=ToolCategory.TEST_RUNNER,
                    command=["pytest"],
                    check_command=["pytest", "--version"],
                    config_files=["pytest.ini", "pyproject.toml"],
                    priority=100,
                ),
                ToolConfig(
                    name="unittest",
                    category=ToolCategory.TEST_RUNNER,
                    command=["python", "-m", "unittest", "discover"],
                    check_command=["python", "-c", "import unittest"],
                    priority=50,
                ),
            ],
            ToolCategory.SECURITY_SCANNER: [
                ToolConfig(
                    name="bandit",
                    category=ToolCategory.SECURITY_SCANNER,
                    command=["bandit", "-r", "."],
                    check_command=["bandit", "--version"],
                    config_files=[".bandit", "pyproject.toml"],
                    priority=100,
                ),
                ToolConfig(
                    name="safety",
                    category=ToolCategory.SECURITY_SCANNER,
                    command=["safety", "check"],
                    check_command=["safety", "--version"],
                    priority=80,
                ),
            ],
        },
        ProjectType.NODEJS: {
            ToolCategory.FORMATTER: [
                ToolConfig(
                    name="prettier",
                    category=ToolCategory.FORMATTER,
                    command=["prettier", "--write", "."],
                    check_command=["prettier", "--version"],
                    autofix_command=["prettier", "--write", "."],
                    config_files=[".prettierrc", "prettier.config.js"],
                    priority=100,
                ),
            ],
            ToolCategory.LINTER: [
                ToolConfig(
                    name="eslint",
                    category=ToolCategory.LINTER,
                    command=["eslint", "."],
                    check_command=["eslint", "--version"],
                    autofix_command=["eslint", "--fix", "."],
                    config_files=[".eslintrc.js", ".eslintrc.json"],
                    priority=100,
                ),
            ],
            ToolCategory.TEST_RUNNER: [
                ToolConfig(
                    name="npm-test",
                    category=ToolCategory.TEST_RUNNER,
                    command=["npm", "test"],
                    check_command=["npm", "--version"],
                    priority=100,
                ),
                ToolConfig(
                    name="jest",
                    category=ToolCategory.TEST_RUNNER,
                    command=["jest"],
                    check_command=["jest", "--version"],
                    config_files=["jest.config.js"],
                    priority=90,
                ),
            ],
            ToolCategory.SECURITY_SCANNER: [
                ToolConfig(
                    name="npm-audit",
                    category=ToolCategory.SECURITY_SCANNER,
                    command=["npm", "audit"],
                    check_command=["npm", "--version"],
                    autofix_command=["npm", "audit", "fix"],
                    priority=100,
                ),
            ],
        },
        ProjectType.TYPESCRIPT: {
            ToolCategory.FORMATTER: [
                ToolConfig(
                    name="prettier",
                    category=ToolCategory.FORMATTER,
                    command=["prettier", "--write", "."],
                    check_command=["prettier", "--version"],
                    autofix_command=["prettier", "--write", "."],
                    config_files=[".prettierrc", "prettier.config.js"],
                    priority=100,
                ),
            ],
            ToolCategory.LINTER: [
                ToolConfig(
                    name="eslint",
                    category=ToolCategory.LINTER,
                    command=["eslint", "."],
                    check_command=["eslint", "--version"],
                    autofix_command=["eslint", "--fix", "."],
                    config_files=[".eslintrc.js", ".eslintrc.json"],
                    priority=100,
                ),
            ],
            ToolCategory.TYPE_CHECKER: [
                ToolConfig(
                    name="tsc",
                    category=ToolCategory.TYPE_CHECKER,
                    command=["tsc", "--noEmit"],
                    check_command=["tsc", "--version"],
                    config_files=["tsconfig.json"],
                    priority=100,
                ),
            ],
        },
        ProjectType.GO: {
            ToolCategory.FORMATTER: [
                ToolConfig(
                    name="gofmt",
                    category=ToolCategory.FORMATTER,
                    command=["gofmt", "-w", "."],
                    check_command=["gofmt", "-help"],
                    autofix_command=["gofmt", "-w", "."],
                    priority=100,
                ),
                ToolConfig(
                    name="goimports",
                    category=ToolCategory.FORMATTER,
                    command=["goimports", "-w", "."],
                    check_command=["goimports", "-help"],
                    autofix_command=["goimports", "-w", "."],
                    priority=90,
                ),
            ],
            ToolCategory.LINTER: [
                ToolConfig(
                    name="golangci-lint",
                    category=ToolCategory.LINTER,
                    command=["golangci-lint", "run"],
                    check_command=["golangci-lint", "--version"],
                    autofix_command=["golangci-lint", "run", "--fix"],
                    config_files=[".golangci.yml"],
                    priority=100,
                ),
            ],
            ToolCategory.TYPE_CHECKER: [
                ToolConfig(
                    name="go-vet",
                    category=ToolCategory.TYPE_CHECKER,
                    command=["go", "vet", "./..."],
                    check_command=["go", "version"],
                    priority=100,
                ),
            ],
            ToolCategory.TEST_RUNNER: [
                ToolConfig(
                    name="go-test",
                    category=ToolCategory.TEST_RUNNER,
                    command=["go", "test", "./..."],
                    check_command=["go", "version"],
                    priority=100,
                ),
            ],
            ToolCategory.SECURITY_SCANNER: [
                ToolConfig(
                    name="gosec",
                    category=ToolCategory.SECURITY_SCANNER,
                    command=["gosec", "./..."],
                    check_command=["gosec", "--version"],
                    priority=100,
                ),
            ],
        },
        ProjectType.RUST: {
            ToolCategory.FORMATTER: [
                ToolConfig(
                    name="rustfmt",
                    category=ToolCategory.FORMATTER,
                    command=["cargo", "fmt"],
                    check_command=["cargo", "fmt", "--version"],
                    autofix_command=["cargo", "fmt"],
                    config_files=["rustfmt.toml"],
                    priority=100,
                ),
            ],
            ToolCategory.LINTER: [
                ToolConfig(
                    name="clippy",
                    category=ToolCategory.LINTER,
                    command=["cargo", "clippy"],
                    check_command=["cargo", "clippy", "--version"],
                    autofix_command=["cargo", "clippy", "--fix"],
                    priority=100,
                ),
            ],
            ToolCategory.TYPE_CHECKER: [
                ToolConfig(
                    name="cargo-check",
                    category=ToolCategory.TYPE_CHECKER,
                    command=["cargo", "check"],
                    check_command=["cargo", "--version"],
                    priority=100,
                ),
            ],
            ToolCategory.TEST_RUNNER: [
                ToolConfig(
                    name="cargo-test",
                    category=ToolCategory.TEST_RUNNER,
                    command=["cargo", "test"],
                    check_command=["cargo", "--version"],
                    priority=100,
                ),
            ],
            ToolCategory.SECURITY_SCANNER: [
                ToolConfig(
                    name="cargo-audit",
                    category=ToolCategory.SECURITY_SCANNER,
                    command=["cargo", "audit"],
                    check_command=["cargo", "audit", "--version"],
                    autofix_command=["cargo", "audit", "fix"],
                    priority=100,
                ),
            ],
        },
        ProjectType.TERRAFORM: {
            ToolCategory.FORMATTER: [
                ToolConfig(
                    name="terraform-fmt",
                    category=ToolCategory.FORMATTER,
                    command=["terraform", "fmt", "-recursive"],
                    check_command=["terraform", "version"],
                    autofix_command=["terraform", "fmt", "-recursive"],
                    priority=100,
                ),
            ],
            ToolCategory.LINTER: [
                ToolConfig(
                    name="tflint",
                    category=ToolCategory.LINTER,
                    command=["tflint"],
                    check_command=["tflint", "--version"],
                    config_files=[".tflint.hcl"],
                    priority=100,
                ),
            ],
            ToolCategory.TYPE_CHECKER: [
                ToolConfig(
                    name="terraform-validate",
                    category=ToolCategory.TYPE_CHECKER,
                    command=["terraform", "validate"],
                    check_command=["terraform", "version"],
                    priority=100,
                ),
            ],
            ToolCategory.SECURITY_SCANNER: [
                ToolConfig(
                    name="tfsec",
                    category=ToolCategory.SECURITY_SCANNER,
                    command=["tfsec", "."],
                    check_command=["tfsec", "--version"],
                    priority=100,
                ),
                ToolConfig(
                    name="checkov",
                    category=ToolCategory.SECURITY_SCANNER,
                    command=["checkov", "-d", "."],
                    check_command=["checkov", "--version"],
                    priority=80,
                ),
            ],
        },
        ProjectType.DOCKER: {
            ToolCategory.LINTER: [
                ToolConfig(
                    name="hadolint",
                    category=ToolCategory.LINTER,
                    command=["hadolint", "**/Dockerfile*"],
                    check_command=["hadolint", "--version"],
                    config_files=[".hadolint.yaml"],
                    priority=100,
                ),
            ],
            ToolCategory.BUILDER: [
                ToolConfig(
                    name="docker-build",
                    category=ToolCategory.BUILDER,
                    command=["docker", "build", "--no-cache", "."],
                    check_command=["docker", "--version"],
                    priority=100,
                ),
            ],
            ToolCategory.SECURITY_SCANNER: [
                ToolConfig(
                    name="trivy",
                    category=ToolCategory.SECURITY_SCANNER,
                    command=["trivy", "image", "--severity", "HIGH,CRITICAL", "."],
                    check_command=["trivy", "--version"],
                    priority=100,
                ),
            ],
        },
    }

    @classmethod
    def get_tools_for_type(
        cls,
        project_type: ProjectType,
        categories: Optional[list[ToolCategory]] = None,
    ) -> list[ToolConfig]:
        """Get tools for a specific project type and categories."""
        if project_type not in cls.TOOL_CONFIGS:
            return []

        tools = []
        type_tools = cls.TOOL_CONFIGS[project_type]

        if categories is None:
            categories = list(ToolCategory)

        for category in categories:
            if category in type_tools:
                tools.extend(type_tools[category])

        # Sort by priority
        tools.sort(key=lambda t: t.priority, reverse=True)
        return tools

    @classmethod
    def get_autofix_tools(cls, project_type: ProjectType) -> list[ToolConfig]:
        """Get only tools that support autofix."""
        tools = cls.get_tools_for_type(project_type)
        return [t for t in tools if t.autofix_command is not None]

    @classmethod
    def create_tool_instances(cls, configs: list[ToolConfig]) -> list[Tool]:
        """Create Tool instances from configs."""
        tools = []
        for config in configs:
            command = config.autofix_command or config.command
            tool = Tool(name=config.name, command=command, check_command=config.check_command)
            tools.append(tool)
        return tools
