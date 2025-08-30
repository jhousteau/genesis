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

# Import version dynamically from pyproject.toml - fail fast if not available
from genesis.core.version import get_version

__version__ = get_version()
__author__ = "Genesis Team"

# Core exports for convenience
from pathlib import Path

from genesis.core.config import ConfigLoader
from genesis.core.health import HealthCheck
from genesis.core.logger import get_logger


def find_genesis_root(start_path: Path = None) -> Path | None:
    """Find Genesis repository root by looking for key indicators.

    Args:
        start_path: Path to start search from (defaults to current working directory)

    Returns:
        Path to Genesis root directory, or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()

    current = Path(start_path).resolve()

    # Look for Genesis indicators
    for parent in [current] + list(current.parents):
        # Check for Genesis-specific files
        if (parent / "genesis" / "cli.py").exists() and (
            parent / "pyproject.toml"
        ).exists():
            # Verify it's actually Genesis by checking pyproject.toml content
            try:
                pyproject_content = (parent / "pyproject.toml").read_text()
                if 'name = "genesis"' in pyproject_content:
                    return parent
            except (OSError, UnicodeDecodeError):
                continue

        # Also check for CLAUDE.md with Genesis content
        if (parent / "CLAUDE.md").exists():
            try:
                claude_content = (parent / "CLAUDE.md").read_text()
                if "GENESIS" in claude_content.upper():
                    return parent
            except (OSError, UnicodeDecodeError):
                continue

    return None


__all__ = [
    "get_logger",
    "ConfigLoader",
    "HealthCheck",
    "find_genesis_root",
    "__version__",
]
