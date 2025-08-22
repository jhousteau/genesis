"""Version management for the SOLVE package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("solve")
except PackageNotFoundError:
    # Fallback for development installations
    __version__ = "0.1.0"


def get_version() -> str:
    """Get the current version of the SOLVE package."""
    return __version__
