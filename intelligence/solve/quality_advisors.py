"""
Quality Advisors for SOLVE - Non-blocking quality analysis and suggestions.

Replaces blocking validators with helpful advisors that provide suggestions
rather than enforcement.
"""

import ast
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Suggestion:
    """A quality suggestion from an advisor."""

    severity: str  # "info", "warning", "opportunity"
    category: str  # "style", "performance", "security", "maintainability"
    message: str
    file: str | None = None
    line: int | None = None
    fix: str | None = None

    def __str__(self) -> str:
        location = f"{self.file}:{self.line} " if self.file and self.line else ""
        return f"[{self.severity.upper()}] {location}{self.message}"


class QualityAdvisor(ABC):
    """Base class for quality advisors."""

    name: str = "base_advisor"

    @abstractmethod
    def analyze(self, artifact: Any) -> list[Suggestion]:
        """Analyze an artifact and return suggestions."""
        pass


class CodeStructureAdvisor(QualityAdvisor):
    """Provides suggestions about code structure and organization."""

    name = "structure_advisor"

    def analyze(self, code: str, filename: str = "unknown") -> list[Suggestion]:
        """Analyze Python code structure."""
        suggestions = []

        try:
            tree = ast.parse(code)

            # Check for very long functions
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.FunctionDef)
                    and hasattr(node, "lineno")
                    and hasattr(node, "end_lineno")
                    and node.end_lineno is not None
                ):
                    func_lines = node.end_lineno - node.lineno
                    if func_lines > 50:
                        suggestions.append(
                            Suggestion(
                                severity="warning",
                                category="maintainability",
                                message=(
                                    f"Function '{node.name}' is {func_lines} lines long. "
                                    "Consider breaking it into smaller functions."
                                ),
                                file=filename,
                                line=node.lineno,
                                fix="Extract related functionality into separate functions",
                            ),
                        )
                    elif func_lines > 100:
                        suggestions.append(
                            Suggestion(
                                severity="opportunity",
                                category="maintainability",
                                message=f"Function '{node.name}' might benefit from decomposition",
                                file=filename,
                                line=node.lineno,
                            ),
                        )

            # Check for missing docstrings
            for node in ast.walk(tree):
                if isinstance(
                    node, ast.FunctionDef | ast.ClassDef
                ) and not ast.get_docstring(node):
                    suggestions.append(
                        Suggestion(
                            severity="info",
                            category="style",
                            message=f"Consider adding a docstring to '{node.name}'",
                            file=filename,
                            line=node.lineno,
                            fix=f'Add docstring: """Describe what {node.name} does."""',
                        ),
                    )

        except SyntaxError as e:
            suggestions.append(
                Suggestion(
                    severity="warning",
                    category="syntax",
                    message=f"Syntax error detected: {e}",
                    file=filename,
                    line=e.lineno if hasattr(e, "lineno") else None,
                ),
            )

        return suggestions


class ImportOrganizationAdvisor(QualityAdvisor):
    """Provides suggestions about import organization."""

    name = "import_advisor"

    def analyze(self, code: str, filename: str = "unknown") -> list[Suggestion]:
        """Analyze import organization."""
        suggestions: list[Suggestion] = []

        try:
            tree = ast.parse(code)
            imports = []

            # Collect all imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import | ast.ImportFrom):
                    imports.append(node)

            if not imports:
                return suggestions

            # Check if imports are at the top
            first_non_import_line = None
            for node in ast.walk(tree):
                if (
                    not isinstance(node, ast.Import | ast.ImportFrom | ast.Module)
                    and hasattr(node, "lineno")
                    and (
                        first_non_import_line is None
                        or node.lineno < first_non_import_line
                    )
                ):
                    first_non_import_line = node.lineno

            # Find imports that come after code
            for imp in imports:
                if first_non_import_line and imp.lineno > first_non_import_line:
                    suggestions.append(
                        Suggestion(
                            severity="info",
                            category="style",
                            message="Consider moving imports to the top of the file",
                            file=filename,
                            line=imp.lineno,
                            fix="Run 'ruff check --fix' to automatically organize imports",
                        ),
                    )
                    break

            # Check for unused imports (simple check)
            # In production, use more sophisticated analysis
            module_names = []
            for imp in imports:
                if isinstance(imp, ast.Import):
                    module_names.extend([alias.name for alias in imp.names])
                elif isinstance(imp, ast.ImportFrom) and imp.module is not None:
                    module_names.append(imp.module)

            # Group imports by type
            stdlib_imports = []
            third_party_imports = []
            local_imports = []

            for imp in imports:
                if isinstance(imp, ast.ImportFrom) and imp.level > 0:
                    local_imports.append(imp)
                # Simple heuristic - can be improved
                elif any(name in str(imp) for name in ["os", "sys", "json", "asyncio"]):
                    stdlib_imports.append(imp)
                else:
                    third_party_imports.append(imp)

            if len(imports) > 10:
                suggestions.append(
                    Suggestion(
                        severity="info",
                        category="style",
                        message=f"File has {len(imports)} imports. Consider if all are necessary.",
                        file=filename,
                        line=imports[0].lineno if imports else None,
                    ),
                )

        except Exception as e:
            # Don't fail on parse errors, just skip analysis
            # This allows us to continue analyzing other files even if one has syntax errors
            logging.debug(f"Failed to parse {filename} for style analysis: {e}")
            pass

        return suggestions


class SecurityAdvisor(QualityAdvisor):
    """Provides basic security suggestions."""

    name = "security_advisor"

    def analyze(self, code: str, filename: str = "unknown") -> list[Suggestion]:
        """Analyze code for basic security issues."""
        suggestions = []

        # Check for hardcoded secrets (basic patterns)
        secret_patterns = [
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Possible hardcoded API key"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Possible hardcoded password"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Possible hardcoded secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Possible hardcoded token"),
        ]

        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            for pattern, message in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    suggestions.append(
                        Suggestion(
                            severity="warning",
                            category="security",
                            message=message,
                            file=filename,
                            line=i,
                            fix="Use environment variables or secure configuration management",
                        ),
                    )

        # Check for use of eval/exec
        dangerous_calls = ["eval(", "exec(", "__import__("]
        for i, line in enumerate(lines, 1):
            for call in dangerous_calls:
                if call in line:
                    suggestions.append(
                        Suggestion(
                            severity="warning",
                            category="security",
                            message=f"Use of {call.rstrip('(')} can be dangerous",
                            file=filename,
                            line=i,
                            fix="Consider safer alternatives",
                        ),
                    )

        return suggestions


class AdvisorOrchestrator:
    """Orchestrates multiple advisors to provide comprehensive suggestions."""

    def __init__(self) -> None:
        self.advisors: list[QualityAdvisor] = [
            CodeStructureAdvisor(),
            ImportOrganizationAdvisor(),
            SecurityAdvisor(),
        ]

    def add_advisor(self, advisor: QualityAdvisor) -> None:
        """Add a new advisor to the orchestrator."""
        self.advisors.append(advisor)

    def analyze(self, artifact: Any, artifact_type: str = "code") -> list[Suggestion]:
        """Run all applicable advisors and collect suggestions."""
        all_suggestions = []

        for advisor in self.advisors:
            try:
                suggestions = advisor.analyze(artifact)
                all_suggestions.extend(suggestions)
            except Exception as e:
                # Log but don't fail
                all_suggestions.append(
                    Suggestion(
                        severity="info",
                        category="system",
                        message=f"Advisor {advisor.name} encountered an error: {e}",
                    ),
                )

        # Sort by severity
        severity_order = {"warning": 0, "opportunity": 1, "info": 2}
        all_suggestions.sort(key=lambda s: severity_order.get(s.severity, 3))

        return all_suggestions

    def get_summary(self, suggestions: list[Suggestion]) -> str:
        """Get a summary of suggestions."""
        if not suggestions:
            return "No suggestions - looking good!"

        by_severity: dict[str, list[Suggestion]] = {}
        for s in suggestions:
            by_severity.setdefault(s.severity, []).append(s)

        summary_parts = []
        for severity in ["warning", "opportunity", "info"]:
            if severity in by_severity:
                count = len(by_severity[severity])
                summary_parts.append(f"{count} {severity}{'s' if count != 1 else ''}")

        return f"Quality analysis: {', '.join(summary_parts)}"
