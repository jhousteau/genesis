"""
Genesis Version Management

Single source of truth for version information, automatically read from pyproject.toml.
Provides utilities for version synchronization across project files.
"""

import tomllib
from pathlib import Path
from typing import Dict, Optional


def get_version() -> str:
    """
    Get version from pyproject.toml - single source of truth.
    
    Returns:
        Version string from pyproject.toml
        
    Raises:
        FileNotFoundError: If pyproject.toml not found
        KeyError: If version not found in pyproject.toml
    """
    # Navigate from genesis/core/version.py to project root
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")
    
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    
    try:
        return data["tool"]["poetry"]["version"]
    except KeyError:
        raise KeyError("Version not found in pyproject.toml at tool.poetry.version")


def get_project_version(project_path: Optional[Path] = None) -> str:
    """
    Get version from any project's pyproject.toml.
    
    Args:
        project_path: Path to project directory (defaults to current directory)
        
    Returns:
        Version string from project's pyproject.toml
    """
    if project_path is None:
        project_path = Path.cwd()
    
    pyproject_path = project_path / "pyproject.toml"
    
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")
    
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    
    # Try different version locations
    version_paths = [
        ["tool", "poetry", "version"],
        ["project", "version"],
        ["version"]
    ]
    
    for path in version_paths:
        try:
            current = data
            for key in path:
                current = current[key]
            return current
        except KeyError:
            continue
    
    raise KeyError("Version not found in pyproject.toml")


def sync_version_to_files(project_path: Path, version: str) -> Dict[str, bool]:
    """
    Synchronize version to common project files.
    
    Args:
        project_path: Path to project directory
        version: Version string to sync
        
    Returns:
        Dictionary mapping file paths to success status
    """
    results = {}
    
    # package.json (Node.js projects)
    package_json = project_path / "package.json"
    if package_json.exists():
        import json
        try:
            with open(package_json, "r") as f:
                data = json.load(f)
            data["version"] = version
            with open(package_json, "w") as f:
                json.dump(data, f, indent=2)
            results[str(package_json)] = True
        except Exception:
            results[str(package_json)] = False
    
    # __init__.py files (exclude virtual environments and external packages)
    for init_file in project_path.rglob("__init__.py"):
        # Skip virtual environments and external packages
        try:
            relative_path = init_file.relative_to(project_path)
            path_parts = relative_path.parts
            
            # Skip common virtual environment and package directories
            skip_dirs = {".venv", "venv", "env", ".env", "node_modules", "site-packages", ".git"}
            if any(part in skip_dirs for part in path_parts):
                continue
                
            content = init_file.read_text()
            if "__version__" in content:
                # Replace __version__ = "..." with new version
                import re
                new_content = re.sub(
                    r'__version__\s*=\s*["\'][^"\']*["\']',
                    f'__version__ = "{version}"',
                    content
                )
                if new_content != content:
                    init_file.write_text(new_content)
                    results[str(init_file)] = True
        except Exception:
            results[str(init_file)] = False
    
    return results


def bump_version(current_version: str, bump_type: str = "patch") -> str:
    """
    Bump version according to semantic versioning.
    
    Args:
        current_version: Current version string
        bump_type: Type of bump (major, minor, patch, alpha, beta, rc)
        
    Returns:
        New version string
    """
    import re
    
    # Parse current version
    version_match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-(.+))?", current_version)
    if not version_match:
        raise ValueError(f"Invalid version format: {current_version}")
    
    major, minor, patch, prerelease = version_match.groups()
    major, minor, patch = int(major), int(minor), int(patch)
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        if prerelease:
            # Remove prerelease for patch bump
            return f"{major}.{minor}.{patch}"
        else:
            return f"{major}.{minor}.{patch + 1}"
    elif bump_type == "alpha":
        if prerelease and "alpha" in prerelease:
            # Increment alpha version
            alpha_match = re.search(r"alpha\.?(\d+)?", prerelease)
            if alpha_match and alpha_match.group(1):
                alpha_num = int(alpha_match.group(1)) + 1
            else:
                alpha_num = 2
            return f"{major}.{minor}.{patch}-alpha.{alpha_num}"
        else:
            return f"{major}.{minor}.{patch}-alpha"
    elif bump_type == "beta":
        return f"{major}.{minor}.{patch}-beta"
    elif bump_type == "rc":
        return f"{major}.{minor}.{patch}-rc"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")