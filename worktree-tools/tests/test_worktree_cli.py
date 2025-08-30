#!/usr/bin/env python3
"""Test script for Genesis worktree CLI"""

import os

# Load environment from .envrc (no hardcoded values)
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
envrc_path = project_root / ".envrc"
if envrc_path.exists():
    try:
        result = subprocess.run(
            ["bash", "-c", f"set -a; source {envrc_path}; env"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=True,
        )
        for line in result.stdout.strip().split("\n"):
            if "=" in line and not line.startswith("_"):
                key, value = line.split("=", 1)
                if key not in os.environ:
                    os.environ[key] = value
    except subprocess.CalledProcessError:
        pass

# Add genesis to path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    from genesis.cli import cli

    cli()
