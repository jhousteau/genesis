"""
Utilities for handling .solveignore file patterns.

Provides functionality to read .solveignore files and filter paths
according to the ignore patterns.
"""

import fnmatch
from pathlib import Path


def load_solveignore(root_path: Path | None = None) -> list[str]:
    """Load patterns from .solveignore file.

    Args:
        root_path: Root directory to look for .solveignore file.
                  If None, uses current directory.

    Returns:
        List of ignore patterns
    """
    if root_path is None:
        root_path = Path.cwd()

    solveignore_path = root_path / ".solveignore"

    if not solveignore_path.exists():
        return []

    patterns = []
    with open(solveignore_path) as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                patterns.append(line)

    return patterns


def should_ignore(
    path: str | Path, patterns: list[str], root_path: Path | None = None
) -> bool:
    """Check if a path should be ignored based on patterns.

    Args:
        path: Path to check
        patterns: List of ignore patterns
        root_path: Root directory for relative path calculation

    Returns:
        True if path should be ignored
    """
    if root_path is None:
        root_path = Path.cwd()

    path = Path(path)

    # Get relative path from root
    try:
        rel_path = path.relative_to(root_path)
    except ValueError:
        # Path is not relative to root, use as is
        rel_path = path

    path_str = str(rel_path)

    # Always ignore certain directories
    parts = path.parts
    for part in parts:
        if part in {
            ".git",
            "__pycache__",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
        }:
            return True

    # Check against patterns
    for pattern in patterns:
        # Handle directory patterns
        if pattern.endswith("/"):
            pattern = pattern.rstrip("/")
            # Check if any parent directory matches
            for i in range(len(parts)):
                parent = "/".join(parts[: i + 1])
                if fnmatch.fnmatch(parent, pattern):
                    return True

        # Standard file/pattern matching
        if fnmatch.fnmatch(path_str, pattern):
            return True

        # Also check against the filename alone
        if fnmatch.fnmatch(path.name, pattern):
            return True

    return False


def collect_python_files(
    root_path: str | Path = ".",
    respect_solveignore: bool = True,
) -> list[str]:
    """Collect all Python files in a directory, respecting .solveignore.

    Args:
        root_path: Root directory to search
        respect_solveignore: Whether to respect .solveignore patterns

    Returns:
        List of Python file paths
    """
    root_path = Path(root_path)
    patterns = load_solveignore(root_path) if respect_solveignore else []

    python_files = []

    # Walk the directory tree
    for file_path in root_path.rglob("*.py"):
        if respect_solveignore and should_ignore(file_path, patterns, root_path):
            continue

        python_files.append(str(file_path))

    return sorted(python_files)


def collect_autofix_files(
    root_path: str | Path = ".",
    respect_solveignore: bool = True,
    extensions: list[str] | None = None,
) -> list[str]:
    """Collect all files that can be autofixed, respecting .solveignore.

    Args:
        root_path: Root directory to search
        respect_solveignore: Whether to respect .solveignore patterns
        extensions: List of file extensions to collect. If None, uses default set.

    Returns:
        List of file paths that can be autofixed
    """
    if extensions is None:
        # Default extensions that our fixers support
        extensions = [".py", ".md", ".mdc", ".txt", ".json", ".yaml", ".yml"]

    root_path = Path(root_path)
    patterns = load_solveignore(root_path) if respect_solveignore else []

    autofix_files = []

    # Walk the directory tree
    for ext in extensions:
        for file_path in root_path.rglob(f"*{ext}"):
            if respect_solveignore and should_ignore(file_path, patterns, root_path):
                continue

            autofix_files.append(str(file_path))

    return sorted(autofix_files)
