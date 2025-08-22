"""Version management for the Autofix package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("solve-autofix")
except PackageNotFoundError:
    # Fallback for development installations
    __version__ = "2.0.0"


def get_version() -> str:
    """Get the current version of the Autofix package."""
    return __version__
