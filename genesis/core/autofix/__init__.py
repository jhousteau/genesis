"""Genesis Core Autofix System.

Multi-stage autofix system with convergent fixing capabilities.
Supports formatters, linters, and iterative stabilization.
"""

from .convergence import ConvergenceResult, ConvergentFixer
from .detectors import ProjectDetector, ProjectInfo, ProjectType, PythonSubtype
from .errors import (
    AutoFixError,
    ConvergenceError,
    ProjectDetectionError,
    ToolNotFoundError,
)
from .fixer import AutoFixer, AutoFixResult
from .stages import FormatterStage, LinterStage, Stage, StageOrchestrator, StageResult

__all__ = [
    "AutoFixer",
    "AutoFixResult",
    "Stage",
    "FormatterStage",
    "LinterStage",
    "StageOrchestrator",
    "StageResult",
    "ProjectDetector",
    "ProjectType",
    "PythonSubtype",
    "ProjectInfo",
    "ConvergentFixer",
    "ConvergenceResult",
    "AutoFixError",
    "ConvergenceError",
    "ToolNotFoundError",
    "ProjectDetectionError",
]
