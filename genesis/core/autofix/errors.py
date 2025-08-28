"""Autofix system specific errors."""

from genesis.core.errors import GenesisError


class AutoFixError(GenesisError):
    """Base error for autofix system."""

    pass


class ConvergenceError(AutoFixError):
    """Error when autofix fails to converge to stable state."""

    pass


class ToolNotFoundError(AutoFixError):
    """Error when required autofix tool is not available."""

    pass


class ProjectDetectionError(AutoFixError):
    """Error when project type cannot be detected."""

    pass
