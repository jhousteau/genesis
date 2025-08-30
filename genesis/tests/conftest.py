"""Testing conftest for genesis/tests directory."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def genesis_root() -> Path:
    """Get the Genesis repository root."""
    # Go up three levels from genesis/tests/ to get to root
    return Path(__file__).parent.parent.parent


@pytest.fixture(autouse=True)
def setup_test_env():
    """Load real environment variables from .envrc for authentic testing."""
    # Store original values to restore after test
    original_env = {}

    # Get the project root
    project_root = Path(__file__).parent.parent.parent
    envrc_path = project_root / ".envrc"

    if envrc_path.exists():
        # Source .envrc using bash and capture the environment
        try:
            result = subprocess.run(
                ["bash", "-c", f"set -a; source {envrc_path}; env"],
                capture_output=True,
                text=True,
                cwd=project_root,
                check=True,
            )

            # Parse environment variables from output
            for line in result.stdout.strip().split("\n"):
                if "=" in line and not line.startswith("_"):  # Skip bash internals
                    key, value = line.split("=", 1)
                    # Only set if not already in environment (preserve existing values)
                    if key not in os.environ:
                        original_env[key] = None
                        os.environ[key] = value

        except subprocess.CalledProcessError:
            # Fall back to minimal test environment if .envrc fails
            pass

    # Ensure critical test environment variables are set
    test_overrides = {
        "ENV": "test",  # Override to test environment
        "PROJECT_MODE": "test",
    }

    for key, value in test_overrides.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value
