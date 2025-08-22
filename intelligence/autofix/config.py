"""Configuration for SOLVE autofix package.

This module provides configuration constants for the autofix package,
including evaluation directory paths.
"""

import os
from pathlib import Path

# Base directory for all evaluation data
EVAL_BASE_DIR = Path(".solve/eval")

# Autofix-specific evaluation directories
AUTOFIX_EVAL_DIR = EVAL_BASE_DIR / "autofix"
AUTOFIX_RESULTS_DIR = AUTOFIX_EVAL_DIR / "results"
AUTOFIX_CACHE_DIR = AUTOFIX_EVAL_DIR / "cache"

# All autofix evaluation directories
AUTOFIX_DIRECTORIES = [
    EVAL_BASE_DIR,
    AUTOFIX_EVAL_DIR,
    AUTOFIX_RESULTS_DIR,
    AUTOFIX_CACHE_DIR,
]

# Autofix configuration constants
DEFAULT_MAX_ITERATIONS = 5
DEFAULT_TIMEOUT = 300
DEFAULT_BACKUP_ENABLED = True


def ensure_eval_directories(base_path: Path | None = None) -> None:
    """Ensure all evaluation directories exist with proper permissions.

    Args:
        base_path: Optional custom base path. If not provided, uses EVAL_BASE_DIR.
    """
    if base_path:
        # Create custom directory structure for autofix
        directories = [
            base_path,
            base_path / "autofix",
            base_path / "autofix" / "results",
            base_path / "autofix" / "cache",
        ]
    else:
        directories = AUTOFIX_DIRECTORIES

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        # Ensure directory is writable
        if not os.access(directory, os.W_OK):
            raise PermissionError(f"Cannot write to directory: {directory}")
