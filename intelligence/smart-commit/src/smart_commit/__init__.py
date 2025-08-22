"""Smart-commit workflow system.

Quality-gated commit workflow that works across all technology stacks.
"""

__version__ = "0.1.0"

from .detector import ProjectDetector
from .orchestrator import SmartCommitOrchestrator
from .stability import StabilityEngine

__all__ = ["ProjectDetector", "StabilityEngine", "SmartCommitOrchestrator"]
