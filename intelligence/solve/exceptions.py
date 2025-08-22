"""
Custom Exceptions for SOLVE SDK Integration

This module defines specific exceptions for different error scenarios
in the SDK integration.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SOLVESDKError(Exception):
    """Base exception for all SOLVE SDK errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """Initialize the error with message and optional details.

        Args:
            message: Human-readable error message
            details: Additional error context as dict
        """
        super().__init__(message)
        self.details = details or {}
        logger.error(f"{self.__class__.__name__}: {message}", extra=self.details)


class SDKInitializationError(SOLVESDKError):
    """Raised when SDK initialization fails.

    This can occur due to missing API keys, invalid configuration,
    or Claude Code SDK import failures.
    """

    def __init__(self, message: str, missing_component: str | None = None):
        """Initialize SDK initialization error.

        Args:
            message: Error description
            missing_component: Name of missing component (e.g., 'API_KEY', 'claude_code_sdk')
        """
        details = {}
        if missing_component:
            details["missing_component"] = missing_component
        super().__init__(message, details)


class GovernanceLoadError(SOLVESDKError):
    """Raised when governance file loading or parsing fails.

    This includes XML parsing errors, missing files, or invalid
    governance file structure.
    """

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        parse_error: str | None = None,
    ):
        """Initialize governance load error.

        Args:
            message: Error description
            file_path: Path to the problematic file
            parse_error: Specific parsing error message
        """
        details = {}
        if file_path:
            details["file_path"] = file_path
        if parse_error:
            details["parse_error"] = parse_error
        super().__init__(message, details)


class ValidationError(SOLVESDKError):
    """Raised when phase validation fails.

    Contains detailed information about what validation checks failed
    and which files were involved.
    """

    def __init__(
        self,
        message: str,
        phase: str,
        errors: list[str] | None = None,
        failed_files: list[str] | None = None,
    ):
        """Initialize validation error.

        Args:
            message: Error summary
            phase: SOLVE phase that failed validation
            errors: List of specific validation errors
            failed_files: List of files that failed validation
        """
        details = {
            "phase": phase,
            "errors": errors or [],
            "failed_files": failed_files or [],
        }
        super().__init__(message, details)

        # Log specific validation failures
        if errors:
            for error in errors[:3]:  # Log first 3 errors
                logger.error(f"  - {error}")
            if len(errors) > 3:
                logger.error(f"  ... and {len(errors) - 3} more errors")


class PhaseExecutionError(SOLVESDKError):
    """Raised when phase execution fails.

    This can include Claude Code SDK errors, file operation failures,
    or unexpected execution problems.
    """

    def __init__(
        self,
        message: str,
        phase: str,
        step: str | None = None,
        root_cause: Exception | None = None,
    ):
        """Initialize phase execution error.

        Args:
            message: Error description
            phase: SOLVE phase that failed
            step: Specific step within phase (e.g., 'load_context', 'execute')
            root_cause: Original exception that caused the failure
        """
        details = {
            "phase": phase,
        }
        if step:
            details["step"] = step
        if root_cause:
            details["root_cause"] = str(root_cause)
            details["root_cause_type"] = type(root_cause).__name__

        super().__init__(message, details)
        self.__cause__ = root_cause


class ConfigurationError(SOLVESDKError):
    """Raised when configuration is invalid or missing.

    This includes missing required configuration values or
    invalid configuration formats.
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        expected_type: str | None = None,
    ):
        """Initialize configuration error.

        Args:
            message: Error description
            config_key: The configuration key that has issues
            expected_type: Expected type/format of the configuration
        """
        details = {}
        if config_key:
            details["config_key"] = config_key
        if expected_type:
            details["expected_type"] = expected_type
        super().__init__(message, details)


class LessonCaptureError(SOLVESDKError):
    """Raised when lesson capture operations fail.

    This includes failures in saving lessons, loading historical
    lessons, or lesson format issues.
    """

    def __init__(self, message: str, operation: str, lesson_id: str | None = None):
        """Initialize lesson capture error.

        Args:
            message: Error description
            operation: The operation that failed (e.g., 'save', 'load')
            lesson_id: ID of the lesson involved
        """
        details = {"operation": operation}
        if lesson_id:
            details["lesson_id"] = lesson_id
        super().__init__(message, details)


class PhaseValidationError(SOLVESDKError):
    """Raised when phase validation or quality gate checks fail.

    This error is used by the PhaseGatekeeper when critical
    quality issues prevent phase completion.
    """

    def __init__(
        self,
        message: str,
        phase: str,
        validation_errors: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ):
        """Initialize phase validation error.

        Args:
            message: Error description
            phase: SOLVE phase that failed validation
            validation_errors: List of specific validation errors found
            **kwargs: Additional details to pass to parent
        """
        details = kwargs.get("details", {})
        details["phase"] = phase
        if validation_errors:
            details["validation_errors"] = validation_errors
            details["error_count"] = len(validation_errors)
        super().__init__(message, details)
