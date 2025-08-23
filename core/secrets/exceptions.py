"""
Genesis Secret Management - Custom Exceptions
SHIELD Security Implementation
"""

from typing import Any, Dict, Optional


class SecretError(Exception):
    """Base exception for all secret management errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class SecretNotFoundError(SecretError):
    """Raised when a requested secret is not found"""

    def __init__(self, secret_name: str, project_id: Optional[str] = None):
        message = f"Secret '{secret_name}' not found"
        if project_id:
            message += f" in project '{project_id}'"
        super().__init__(
            message, {"secret_name": secret_name, "project_id": project_id}
        )


class SecretAccessDeniedError(SecretError):
    """Raised when access to a secret is denied"""

    def __init__(self, secret_name: str, reason: str = "Insufficient permissions"):
        message = f"Access denied to secret '{secret_name}': {reason}"
        super().__init__(message, {"secret_name": secret_name, "reason": reason})


class SecretRotationError(SecretError):
    """Raised when secret rotation fails"""

    def __init__(
        self,
        secret_name: str,
        rotation_id: Optional[str] = None,
        reason: str = "Unknown",
    ):
        message = f"Failed to rotate secret '{secret_name}': {reason}"
        details = {"secret_name": secret_name, "reason": reason}
        if rotation_id:
            details["rotation_id"] = rotation_id
        super().__init__(message, details)


class SecretValidationError(SecretError):
    """Raised when secret validation fails"""

    def __init__(self, secret_name: str, validation_rules: Optional[list] = None):
        message = f"Secret '{secret_name}' failed validation"
        if validation_rules:
            message += f": {', '.join(validation_rules)}"
        super().__init__(
            message, {"secret_name": secret_name, "validation_rules": validation_rules}
        )


class SecretConfigurationError(SecretError):
    """Raised when secret configuration is invalid"""

    def __init__(self, config_issue: str):
        message = f"Secret configuration error: {config_issue}"
        super().__init__(message, {"config_issue": config_issue})


class SecretEncryptionError(SecretError):
    """Raised when secret encryption/decryption fails"""

    def __init__(self, operation: str, reason: str = "Unknown"):
        message = f"Secret {operation} failed: {reason}"
        super().__init__(message, {"operation": operation, "reason": reason})


class SecretAuditError(SecretError):
    """Raised when secret audit logging fails"""

    def __init__(self, audit_action: str, reason: str = "Unknown"):
        message = f"Secret audit logging failed for action '{audit_action}': {reason}"
        super().__init__(message, {"audit_action": audit_action, "reason": reason})
