"""Version management for the Smart-Commit package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("smart-commit")
except PackageNotFoundError:
    # Fallback for development installations
    __version__ = "1.0.0"


def get_version() -> str:
    """Get the current version of the Smart-Commit package."""
    return __version__
