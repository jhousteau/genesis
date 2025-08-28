"""Mock command execution for testing scripts and CLI operations."""

from typing import Any
from unittest.mock import Mock, patch


class MockCommandRunner:
    """Mock command execution with configurable responses."""

    def __init__(self):
        self.commands = {}
        self.call_history = []
        self.default_response = {"returncode": 0, "stdout": "", "stderr": ""}

    def configure_command(
        self,
        command: str,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        side_effect: Exception | None = None,
    ):
        """Configure response for a specific command."""
        self.commands[command] = {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "side_effect": side_effect,
        }

    def mock_run(self, cmd: str | list[str], **kwargs):
        """Mock subprocess.run with configurable responses."""
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        self.call_history.append(
            {
                "command": cmd_str,
                "args": cmd if isinstance(cmd, list) else cmd.split(),
                "kwargs": kwargs,
            }
        )

        # Check for configured responses
        for pattern, response in self.commands.items():
            if pattern in cmd_str:
                if response.get("side_effect"):
                    raise response["side_effect"]

                result = Mock()
                result.returncode = response["returncode"]
                result.stdout = response["stdout"]
                result.stderr = response["stderr"]
                return result

        # Default response
        result = Mock()
        result.returncode = self.default_response["returncode"]
        result.stdout = self.default_response["stdout"]
        result.stderr = self.default_response["stderr"]
        return result

    def was_called(self, command_pattern: str) -> bool:
        """Check if a command matching pattern was called."""
        return any(command_pattern in call["command"] for call in self.call_history)

    def get_calls_matching(self, command_pattern: str) -> list[dict[str, Any]]:
        """Get all calls matching a command pattern."""
        return [
            call for call in self.call_history if command_pattern in call["command"]
        ]

    def get_call_count(self, command_pattern: str) -> int:
        """Get count of calls matching pattern."""
        return len(self.get_calls_matching(command_pattern))

    def clear_history(self):
        """Clear call history."""
        self.call_history = []


def create_mock_shell_commands() -> MockCommandRunner:
    """Create mock command runner with common shell commands configured."""
    runner = MockCommandRunner()

    # Common shell commands
    runner.configure_command("echo", returncode=0, stdout="echo output")
    runner.configure_command("ls", returncode=0, stdout="file1\nfile2")
    runner.configure_command("mkdir", returncode=0)
    runner.configure_command("rm", returncode=0)
    runner.configure_command("find", returncode=0, stdout="found_file")
    runner.configure_command("wc -l", returncode=0, stdout="10")

    # Poetry commands
    runner.configure_command("poetry install", returncode=0)
    runner.configure_command("poetry build", returncode=0)

    # npm commands
    runner.configure_command("npm install", returncode=0)
    runner.configure_command("npm test", returncode=0)
    runner.configure_command("npm run", returncode=0)

    # pytest commands
    runner.configure_command("pytest", returncode=0, stdout="All tests passed")

    # Linting commands
    runner.configure_command("black", returncode=0)
    runner.configure_command("ruff", returncode=0)
    runner.configure_command("mypy", returncode=0)

    return runner


def create_genesis_script_mocks() -> MockCommandRunner:
    """Create mock command runner configured for Genesis scripts."""
    runner = MockCommandRunner()

    # Bootstrap script
    runner.configure_command(
        "bootstrap.sh",
        returncode=0,
        stdout="🚀 Project Bootstrap\n✅ Bootstrap complete!",
    )

    # Smart commit script
    runner.configure_command(
        "smart-commit.sh",
        returncode=0,
        stdout="🔍 Running quality checks\n✅ Commit successful!",
    )

    # Worktree script
    runner.configure_command(
        "create-sparse-worktree.sh",
        returncode=0,
        stdout="✅ Sparse worktree created successfully",
    )

    # Git commands (common in Genesis scripts)
    runner.configure_command("git init", returncode=0)
    runner.configure_command("git add", returncode=0)
    runner.configure_command("git commit", returncode=0)
    runner.configure_command("git status", returncode=0, stdout="On branch main")
    runner.configure_command("git worktree", returncode=0)
    runner.configure_command("git sparse-checkout", returncode=0)

    return runner


class MockScriptEnvironment:
    """Mock environment for testing shell scripts."""

    def __init__(self):
        self.env_vars = {}
        self.working_dir = "/fake/working/dir"
        self.command_runner = create_genesis_script_mocks()

    def set_env_var(self, name: str, value: str):
        """Set environment variable."""
        self.env_vars[name] = value

    def set_working_dir(self, path: str):
        """Set working directory."""
        self.working_dir = path

    def run_script(self, script_path: str, args: list[str] = None):
        """Mock running a script."""
        args = args or []
        cmd = f"{script_path} {' '.join(args)}"
        return self.command_runner.mock_run(cmd.strip())

    def patch_all(self):
        """Return context manager that patches subprocess and environment."""
        return patch.multiple("subprocess", run=self.command_runner.mock_run)


def patch_subprocess_run():
    """Simple patch for subprocess.run with default success."""
    mock_runner = create_mock_shell_commands()
    return patch("subprocess.run", side_effect=mock_runner.mock_run), mock_runner
