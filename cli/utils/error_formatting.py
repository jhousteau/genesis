#!/usr/bin/env python3
"""
Genesis CLI Error Formatting Utilities

Provides standardized error message formatting for consistent user experience
across all CLI commands.
"""

from typing import Optional

import click
from rich.console import Console

console = Console()


class ErrorFormatter:
    """Standardized error formatting for CLI commands."""

    # Error type icons and colors
    ERROR_ICONS = {
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "success": "✅",
        "loading": "🔄",
        "security": "🔒",
        "network": "🌐",
        "config": "⚙️",
        "validation": "📋",
        "timeout": "⏱️",
    }

    ERROR_COLORS = {
        "error": "red",
        "warning": "yellow",
        "info": "blue",
        "success": "green",
        "loading": "cyan",
        "security": "magenta",
        "network": "blue",
        "config": "yellow",
        "validation": "yellow",
        "timeout": "red",
    }

    @classmethod
    def format_error(
        cls,
        message: str,
        error_type: str = "error",
        context: Optional[str] = None,
        suggestion: Optional[str] = None,
        use_rich: bool = False,
    ) -> str:
        """
        Format error message with consistent pattern.

        Args:
            message: The error message
            error_type: Type of error (error, warning, info, etc.)
            context: Additional context information
            suggestion: Suggested fix or next step
            use_rich: Whether to use Rich formatting or plain text

        Returns:
            Formatted error string
        """
        icon = cls.ERROR_ICONS.get(error_type, "❌")
        color = cls.ERROR_COLORS.get(error_type, "red")

        if use_rich:
            formatted_msg = f"[{color}]{icon} {message}[/{color}]"
            if context:
                formatted_msg += f"\n[dim]Context: {context}[/dim]"
            if suggestion:
                formatted_msg += f"\n[blue]💡 Suggestion: {suggestion}[/blue]"
        else:
            formatted_msg = f"{icon} {message}"
            if context:
                formatted_msg += f"\nContext: {context}"
            if suggestion:
                formatted_msg += f"\n💡 Suggestion: {suggestion}"

        return formatted_msg

    @classmethod
    def print_error(
        cls,
        message: str,
        error_type: str = "error",
        context: Optional[str] = None,
        suggestion: Optional[str] = None,
        use_rich: bool = False,
        exit_code: Optional[int] = None,
    ) -> None:
        """
        Print formatted error message and optionally exit.

        Args:
            message: The error message
            error_type: Type of error
            context: Additional context
            suggestion: Suggested fix
            use_rich: Whether to use Rich console
            exit_code: Exit code if should exit
        """
        formatted_msg = cls.format_error(
            message, error_type, context, suggestion, use_rich
        )

        if use_rich:
            console.print(formatted_msg)
        else:
            click.echo(formatted_msg, err=True)

        if exit_code is not None:
            click.get_current_context().exit(exit_code)

    @classmethod
    def standardize_exception_message(
        cls, exception: Exception, operation: str = ""
    ) -> str:
        """
        Standardize exception messages for consistency.

        Args:
            exception: The exception to format
            operation: The operation that failed

        Returns:
            Standardized error message
        """
        exc_name = exception.__class__.__name__
        exc_msg = str(exception)

        # Clean up common exception patterns
        if exc_name == "FileNotFoundError":
            return f"File not found: {exc_msg}"
        elif exc_name == "PermissionError":
            return f"Permission denied: {exc_msg}"
        elif exc_name == "ConnectionError":
            return f"Connection failed: {exc_msg}"
        elif exc_name == "TimeoutError":
            return f"Operation timed out: {exc_msg}"
        elif exc_name == "ValidationError":
            return f"Validation failed: {exc_msg}"
        elif exc_name in ["ValueError", "TypeError"]:
            return f"Invalid input: {exc_msg}"
        else:
            if operation:
                return f"{operation} failed: {exc_msg}"
            return f"{exc_name}: {exc_msg}"


# Convenience functions for common error patterns
def format_gcp_error(error: Exception, resource: str = "") -> str:
    """Format GCP-specific errors."""
    if "permission" in str(error).lower():
        context = f"Resource: {resource}" if resource else None
        suggestion = (
            "Check IAM permissions and ensure service account has required roles"
        )
        return ErrorFormatter.format_error(
            f"GCP permission denied: {error}",
            error_type="security",
            context=context,
            suggestion=suggestion,
        )
    elif "quota" in str(error).lower():
        suggestion = "Check GCP quotas and consider requesting increases"
        return ErrorFormatter.format_error(
            f"GCP quota exceeded: {error}", error_type="resource", suggestion=suggestion
        )
    else:
        return ErrorFormatter.format_error(
            f"GCP operation failed: {error}", error_type="network"
        )


def format_terraform_error(error: Exception, module: str = "") -> str:
    """Format Terraform-specific errors."""
    context = f"Module: {module}" if module else None

    if "authentication" in str(error).lower():
        suggestion = "Run 'gcloud auth application-default login' or check service account configuration"
        return ErrorFormatter.format_error(
            f"Terraform authentication failed: {error}",
            error_type="security",
            context=context,
            suggestion=suggestion,
        )
    elif "state" in str(error).lower():
        suggestion = "Check Terraform state file permissions and backend configuration"
        return ErrorFormatter.format_error(
            f"Terraform state error: {error}",
            error_type="config",
            context=context,
            suggestion=suggestion,
        )
    else:
        return ErrorFormatter.format_error(
            f"Terraform operation failed: {error}", error_type="config", context=context
        )


def format_secret_error(error: Exception, secret_name: str = "") -> str:
    """Format secret management errors."""
    context = f"Secret: {secret_name}" if secret_name else None

    if "not found" in str(error).lower():
        suggestion = "Verify secret name and ensure it exists in the target project"
        return ErrorFormatter.format_error(
            f"Secret not found: {error}",
            error_type="validation",
            context=context,
            suggestion=suggestion,
        )
    elif "permission" in str(error).lower() or "access" in str(error).lower():
        suggestion = "Check IAM permissions for Secret Manager access"
        return ErrorFormatter.format_error(
            f"Secret access denied: {error}",
            error_type="security",
            context=context,
            suggestion=suggestion,
        )
    else:
        return ErrorFormatter.format_error(
            f"Secret operation failed: {error}", error_type="security", context=context
        )
