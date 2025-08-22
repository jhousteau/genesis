"""
Data models for the autofix/autocommit system.

Based on ADR-004: Comprehensive Autofix/Autocommit System Architecture
"""

import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorPriority(Enum):
    """Priority levels for error fixing"""

    HIGH = 1  # Critical issues
    SYNTAX = 1  # Must fix first
    IMPORTS = 2  # Dependencies for types
    TYPES = 3  # After imports resolved
    SIMPLE = 4  # Quick wins
    COMPLEX = 5  # Needs deep understanding
    MEDIUM = 4  # Medium priority issues
    LOW = 5  # Low priority issues


class FixType(Enum):
    """Type of fix applied"""

    AUTO_FORMAT = "auto_format"  # Formatting only
    AUTO_FIX = "auto_fix"  # Automated code fixes
    LLM_MANUAL = "llm_manual"  # LLM-powered fixes
    AUTOMATED = "automated"  # General automated fixes


@dataclass
class AutofixConfig:
    """Configuration for the autofix system"""

    # Stage 1
    enable_auto_fixers: bool = True
    max_fix_iterations: int = 5

    # Stage 2
    run_validation: bool = True
    fail_on_validation_error: bool = True
    save_analysis_report: bool = True

    # Stage 3
    enable_llm_fixes: bool = True
    llm_batch_size: int = 10
    llm_timeout_seconds: int = 300
    max_llm_retries: int = 3

    # Safety
    create_backups: bool = True
    enable_backups: bool = True  # Alias for create_backups
    enable_dry_run: bool = False

    # Non-interactive mode
    interactive_mode: bool | None = None  # Auto-detect from TTY


@dataclass
class FixResult:
    """Result of a fix operation"""

    success: bool
    files_changed: list[str]
    errors_fixed: int
    time_taken: float
    details: dict[str, Any]


@dataclass
class ValidationResult:
    """Result of a validation operation"""

    success: bool
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    time_taken: float


@dataclass
class Error:
    """Represents a code error that needs fixing"""

    file_path: str
    line: int
    column: int
    code: str
    message: str
    priority: ErrorPriority
    context: dict[str, Any] | None = None

    # Computed properties for backward compatibility
    @property
    def line_number(self) -> int:
        """Alias for line to support legacy code."""
        return self.line

    @property
    def error_type(self) -> str:
        """Alias for code to support legacy code."""
        return self.code

    @property
    def category(self) -> str:
        """Return priority name in lowercase for legacy code."""
        return self.priority.name.lower()


@dataclass
class FixBatch:
    """A batch of errors to be fixed together"""

    errors: list[Error]
    batch_id: str
    priority: ErrorPriority
    estimated_tokens: int


def detect_interactive_mode() -> bool:
    """Auto-detect based on environment"""
    if os.environ.get("CI"):
        return False
    if not sys.stdin.isatty():
        return False
    return not os.environ.get("SOLVE_NON_INTERACTIVE")


ERROR_PRIORITY_MAP = {
    "syntax": ErrorPriority.SYNTAX,
    "imports": ErrorPriority.IMPORTS,
    "types": ErrorPriority.TYPES,
    "simple": ErrorPriority.SIMPLE,
    "complex": ErrorPriority.COMPLEX,
}
