"""
Error Service
Comprehensive error handling and user-friendly messaging system following CRAFT methodology.
"""

import sys
import traceback
import logging
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    RESOURCE = "resource"
    VALIDATION = "validation"
    INFRASTRUCTURE = "infrastructure"
    SERVICE = "service"
    USER = "user"
    SYSTEM = "system"


@dataclass
class GenesisError:
    """Structured error information."""

    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    code: str
    details: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ErrorService:
    """
    Comprehensive error handling service implementing CRAFT principles.

    Create: Robust error management framework
    Refactor: Optimized for maintainability
    Authenticate: Secure error information handling
    Function: Reliable error reporting and recovery
    Test: Comprehensive error scenario validation
    """

    def __init__(self, config_service):
        self.config_service = config_service
        self.error_handlers: Dict[str, Any] = {}
        self.error_history: List[GenesisError] = []
        self.max_history = 100

        # Initialize standard error handlers
        self._register_standard_handlers()

    def create_error(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        code: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> GenesisError:
        """Create a structured error."""
        error = GenesisError(
            message=message,
            category=category,
            severity=severity,
            code=code,
            details=details,
            suggestions=suggestions,
            context=context,
        )

        # Store in history
        self.error_history.append(error)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)

        return error

    def handle_exception(
        self, exc: Exception, context: Optional[Dict[str, Any]] = None
    ) -> GenesisError:
        """Handle and classify an exception."""
        exc_type = type(exc).__name__
        exc_message = str(exc)

        # Try to find a specific handler
        handler = self.error_handlers.get(exc_type)
        if handler:
            return handler(exc, context)

        # Generic exception handling
        category, severity = self._classify_exception(exc)

        error = self.create_error(
            message=f"{exc_type}: {exc_message}",
            category=category,
            severity=severity,
            code=f"GENERIC_{exc_type.upper()}",
            details={"exception_type": exc_type, "traceback": traceback.format_exc()},
            context=context,
        )

        # Log the error
        self._log_error(error)

        return error

    def format_error_message(
        self,
        error: GenesisError,
        include_details: bool = False,
        include_suggestions: bool = True,
    ) -> str:
        """Format error message for user display."""
        lines = []

        # Header with severity indicator
        severity_indicator = {
            ErrorSeverity.LOW: "ℹ️",
            ErrorSeverity.MEDIUM: "⚠️",
            ErrorSeverity.HIGH: "❌",
            ErrorSeverity.CRITICAL: "🚨",
        }.get(error.severity, "❓")

        lines.append(f"{severity_indicator} Genesis CLI Error [{error.code}]")
        lines.append("")
        lines.append(f"Message: {error.message}")
        lines.append(f"Category: {error.category.value}")
        lines.append(f"Severity: {error.severity.value}")

        if error.context:
            lines.append("")
            lines.append("Context:")
            for key, value in error.context.items():
                lines.append(f"  {key}: {value}")

        if include_details and error.details:
            lines.append("")
            lines.append("Details:")
            for key, value in error.details.items():
                if key != "traceback":  # Skip traceback in user output
                    lines.append(f"  {key}: {value}")

        if include_suggestions and error.suggestions:
            lines.append("")
            lines.append("Suggested Solutions:")
            for i, suggestion in enumerate(error.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")

        return "\n".join(lines)

    def get_exit_code(self, error: GenesisError) -> int:
        """Get appropriate exit code for error."""
        severity_codes = {
            ErrorSeverity.LOW: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.CRITICAL: 4,
        }

        category_codes = {
            ErrorCategory.AUTHENTICATION: 10,
            ErrorCategory.AUTHORIZATION: 11,
            ErrorCategory.CONFIGURATION: 12,
            ErrorCategory.NETWORK: 20,
            ErrorCategory.RESOURCE: 30,
            ErrorCategory.VALIDATION: 40,
            ErrorCategory.INFRASTRUCTURE: 50,
            ErrorCategory.SERVICE: 60,
            ErrorCategory.USER: 70,
            ErrorCategory.SYSTEM: 80,
        }

        return category_codes.get(error.category, 1)

    def _register_standard_handlers(self) -> None:
        """Register standard exception handlers."""

        # Authentication errors
        def handle_auth_error(
            exc: Exception, context: Optional[Dict[str, Any]] = None
        ) -> GenesisError:
            suggestions = [
                "Verify your GCP credentials are configured",
                "Check if the service account has the required permissions",
                "Ensure the project ID is correct",
                "Try running 'gcloud auth login' or 'gcloud auth application-default login'",
            ]

            return self.create_error(
                message=f"Authentication failed: {str(exc)}",
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                code="AUTH_FAILED",
                suggestions=suggestions,
                context=context,
            )

        # Configuration errors
        def handle_config_error(
            exc: Exception, context: Optional[Dict[str, Any]] = None
        ) -> GenesisError:
            suggestions = [
                "Check your configuration files in config/environments/",
                "Verify environment variables are set correctly",
                "Ensure PROJECT_ID environment variable is set",
                "Review config/global.yaml for required settings",
            ]

            return self.create_error(
                message=f"Configuration error: {str(exc)}",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.MEDIUM,
                code="CONFIG_ERROR",
                suggestions=suggestions,
                context=context,
            )

        # Network errors
        def handle_network_error(
            exc: Exception, context: Optional[Dict[str, Any]] = None
        ) -> GenesisError:
            suggestions = [
                "Check your internet connection",
                "Verify GCP API endpoints are accessible",
                "Check if you're behind a corporate firewall",
                "Try again in a few minutes (temporary network issue)",
            ]

            return self.create_error(
                message=f"Network error: {str(exc)}",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                code="NETWORK_ERROR",
                suggestions=suggestions,
                context=context,
            )

        # Resource errors (GCP quotas, limits, etc.)
        def handle_resource_error(
            exc: Exception, context: Optional[Dict[str, Any]] = None
        ) -> GenesisError:
            suggestions = [
                "Check GCP quotas in the console",
                "Verify the resource doesn't already exist",
                "Ensure you have sufficient permissions",
                "Try using a different region or zone",
            ]

            return self.create_error(
                message=f"Resource error: {str(exc)}",
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.HIGH,
                code="RESOURCE_ERROR",
                suggestions=suggestions,
                context=context,
            )

        # Register handlers
        self.error_handlers.update(
            {
                "AuthenticationError": handle_auth_error,
                "ConfigurationError": handle_config_error,
                "ConnectionError": handle_network_error,
                "TimeoutError": handle_network_error,
                "CalledProcessError": handle_resource_error,
                "FileNotFoundError": handle_config_error,
                "KeyError": handle_config_error,
                "ValueError": handle_config_error,
            }
        )

    def _classify_exception(
        self, exc: Exception
    ) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify exception into category and severity."""
        exc_type = type(exc).__name__
        exc_message = str(exc).lower()

        # Classification rules
        if any(
            keyword in exc_message
            for keyword in ["auth", "credential", "permission", "unauthorized"]
        ):
            return ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH

        if any(
            keyword in exc_message for keyword in ["config", "setting", "parameter"]
        ):
            return ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM

        if any(
            keyword in exc_message
            for keyword in ["network", "connection", "timeout", "dns"]
        ):
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM

        if any(
            keyword in exc_message
            for keyword in ["quota", "limit", "resource", "capacity"]
        ):
            return ErrorCategory.RESOURCE, ErrorSeverity.HIGH

        if exc_type in ["FileNotFoundError", "ValueError", "KeyError"]:
            return ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM

        # Default classification
        return ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM

    def _log_error(self, error: GenesisError) -> None:
        """Log error with appropriate level."""
        log_message = f"[{error.code}] {error.message}"

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={"error_details": error.details})
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra={"error_details": error.details})
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        if not self.error_history:
            return {"total_errors": 0, "by_category": {}, "by_severity": {}}

        by_category = {}
        by_severity = {}

        for error in self.error_history:
            # Count by category
            category_key = error.category.value
            by_category[category_key] = by_category.get(category_key, 0) + 1

            # Count by severity
            severity_key = error.severity.value
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "by_category": by_category,
            "by_severity": by_severity,
            "most_recent": {
                "message": self.error_history[-1].message,
                "category": self.error_history[-1].category.value,
                "severity": self.error_history[-1].severity.value,
                "timestamp": self.error_history[-1].timestamp.isoformat(),
            },
        }

    def clear_error_history(self) -> None:
        """Clear error history."""
        self.error_history.clear()

    def export_error_report(self) -> Dict[str, Any]:
        """Export comprehensive error report."""
        return {
            "report_timestamp": datetime.now().isoformat(),
            "genesis_config": {
                "environment": self.config_service.environment,
                "project_id": self.config_service.project_id,
            },
            "error_summary": self.get_error_summary(),
            "error_history": [
                {
                    "message": error.message,
                    "category": error.category.value,
                    "severity": error.severity.value,
                    "code": error.code,
                    "timestamp": error.timestamp.isoformat(),
                    "details": error.details,
                    "suggestions": error.suggestions,
                    "context": error.context,
                }
                for error in self.error_history
            ],
        }
