"""Code validation utilities."""

from pathlib import Path
from typing import Protocol


class ValidationError:
    """Base class for validation errors."""

    def __init__(self, file_path: str, line: int, message: str):
        self.file_path = file_path
        self.line = line
        self.message = message


class Validator(Protocol):
    """Interface for code validators."""

    def validate(self, file_paths: list[Path]) -> list[ValidationError]:
        """Validate code files."""
        ...


class MypyChecker:
    """Type checker using mypy."""

    def validate(self, file_paths: list[Path]) -> list[ValidationError]:
        """Run mypy on Python files."""
        return []  # Placeholder


class RuffChecker:
    """Linter using ruff."""

    def validate(self, file_paths: list[Path]) -> list[ValidationError]:
        """Run ruff on Python files."""
        return []  # Placeholder


class SecurityChecker:
    """Security checker using bandit."""

    def validate(self, file_paths: list[Path]) -> list[ValidationError]:
        """Run bandit security checks."""
        return []  # Placeholder


class PytestRunner:
    """Test runner using pytest."""

    def validate(self, file_paths: list[Path]) -> list[ValidationError]:
        """Run pytest on Python files."""
        return []  # Placeholder
