"""
SOLVE: Software Evolution and Learning
A methodology for evolving and improving software systems using AI assistance.
"""

# Import solve_core with fallback for development environment
try:
    from solve_core.config import load_config
    from solve_core.logging import get_logger
except ImportError:
    # Fallback for development environment
    import logging
    import os
    import sys

    # Try multiple possible solve_core paths
    possible_paths = [
        os.path.join(
            os.path.dirname(__file__), "../../../../shared/solve_core/solve_core"
        ),
        os.path.join(os.path.dirname(__file__), "../../../../shared/solve_core"),
        os.path.join(os.path.dirname(__file__), "../../../solve_core"),
    ]

    solve_core_path = None
    for path in possible_paths:
        if os.path.exists(os.path.join(path, "__init__.py")):
            solve_core_path = path
            break

    if solve_core_path:
        # For path like /path/to/shared/solve_core/solve_core, we need the parent
        if os.path.basename(solve_core_path) == "solve_core":
            sys.path.insert(0, os.path.dirname(solve_core_path))
        else:
            sys.path.insert(0, solve_core_path)
        try:
            from solve_core.config import load_config
            from solve_core.logging import get_logger
        except ImportError:
            # Final fallback - create basic functions
            def load_config():
                return {}

            def get_logger(name):
                return logging.getLogger(name)

    else:
        # Basic fallback implementations
        def load_config():
            return {}

        def get_logger(name):
            return logging.getLogger(name)


try:
    from importlib.metadata import version

    __version__ = version("solve")
except Exception:
    __version__ = "0.1.0"  # Development version

# Import key components for easier access
from .agents import Agent, ImplementationAgent, PlanningAgent, ReviewAgent
from .models import AgentTask, Goal, Result, TaskStatus
from .orchestrator import Orchestrator as SOLVEOrchestrator

# Import available components
_phases_available = False
_tools_available = False

try:
    from .phases import (AnalysisPhase, ImplementationPhase,  # noqa: F401
                         Phase, PlanningPhase)

    _phases_available = True
except ImportError:
    pass

try:
    from .tools import CodeAnalysisTool, FileSystemTool, GitTool  # noqa: F401
    from .tools.base import BaseTool as Tool  # noqa: F401

    _tools_available = True
except ImportError:
    pass

# Configure package logging
logger = get_logger(__name__)

# Load default configuration
try:
    config = load_config()
except FileNotFoundError:
    logger.warning("No configuration file found, using defaults")
    config = {}

__all__ = [
    "SOLVEOrchestrator",
    "Agent",
    "ReviewAgent",
    "PlanningAgent",
    "ImplementationAgent",
    "Goal",
    "TaskStatus",
    "AgentTask",
    "Result",
]

if _tools_available:
    __all__.extend(
        [
            "Tool",
            "FileSystemTool",
            "GitTool",
            "CodeAnalysisTool",
        ],
    )

if _phases_available:
    __all__.extend(
        [
            "Phase",
            "AnalysisPhase",
            "PlanningPhase",
            "ImplementationPhase",
        ],
    )
