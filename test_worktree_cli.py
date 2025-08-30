#!/usr/bin/env python3
"""Test script for Genesis worktree CLI"""

import os
import sys
from pathlib import Path

# Set up environment
os.environ["MAX_WORKTREE_FILES"] = "30"
os.environ["MAX_PROJECT_FILES"] = "1000"
os.environ["MAX_COMPONENT_FILES"] = "30"

# Add genesis to path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    from genesis.cli import cli

    cli()
