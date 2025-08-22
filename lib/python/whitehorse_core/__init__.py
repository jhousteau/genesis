"""
Whitehorse Core Library
Version: 1.0.0

Core integration library for the Universal Project Platform.
Provides common interfaces and utilities for all components.
"""

__version__ = "1.0.0"

from .deployment import DeploymentManager
from .intelligence import IntelligenceCoordinator
from .monitoring import MonitoringClient
from .registry import ProjectRegistry
from .security import SecurityManager

__all__ = [
    "ProjectRegistry",
    "IntelligenceCoordinator",
    "DeploymentManager",
    "MonitoringClient",
    "SecurityManager",
]
