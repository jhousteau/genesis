"""
Genesis CLI User Interface Module
Implements REACT methodology for responsive, efficient, accessible CLI experience.
"""

from .terminal import TerminalAdapter
from .progress import ProgressIndicator
from .formatter import OutputFormatter
from .help import HelpSystem
from .colors import ColorScheme
from .interactive import InteractivePrompt

__all__ = [
    "TerminalAdapter",
    "ProgressIndicator",
    "OutputFormatter",
    "HelpSystem",
    "ColorScheme",
    "InteractivePrompt",
]
