"""
Genesis Security Layer - Secret Management Module
SHIELD Methodology Implementation for Comprehensive Secret Management

This module provides secure secret management capabilities for the Genesis platform,
supporting both claude-talk and agent-cage migrations.
"""

from .access_patterns import SecretAccessPattern, SecretCache
from .exceptions import (SecretAccessDeniedError, SecretError,
                         SecretNotFoundError, SecretRotationError,
                         SecretValidationError)
from .manager import SecretManager, get_secret_manager
from .monitoring import SecretMonitor
from .rotation import SecretRotator

__all__ = [
    "SecretManager",
    "get_secret_manager",
    "SecretAccessPattern",
    "SecretCache",
    "SecretRotator",
    "SecretMonitor",
    "SecretError",
    "SecretNotFoundError",
    "SecretAccessDeniedError",
    "SecretRotationError",
    "SecretValidationError",
]

__version__ = "1.0.0"
