"""
SOLVE CLI Entry Point

This module allows the package to be run as a module:
    python -m solve

It simply delegates to the main CLI entry point.
"""

import sys

from solve.cli import main

if __name__ == "__main__":
    sys.exit(main())
