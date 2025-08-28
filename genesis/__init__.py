"""
Genesis Development Toolkit

A unified development toolkit providing:
- CLI commands for project management
- Core utilities (config, health, logger, retry)
- Testing infrastructure
- Project templates and bootstrapping
- Infrastructure as code patterns

Usage:
    from genesis.core import get_logger, Config
    from genesis.commands import bootstrap_project
"""

__version__ = "2.0.0-dev"
__author__ = "Genesis Team"

# Core exports for convenience
from genesis.core.logger import get_logger
from genesis.core.config import ConfigLoader
from genesis.core.health import HealthCheck

__all__ = ["get_logger", "ConfigLoader", "HealthCheck", "__version__"]
