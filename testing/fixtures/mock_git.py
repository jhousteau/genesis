"""Git operation mocks for testing."""

from unittest.mock import Mock, patch


class MockGit:
    """Mock git operations with configurable responses."""

    def __init__(self):
        self.commands = {}
        self.call_history = []

    def configure_command(
        self, command: str, returncode: int = 0, stdout: str = "", stderr: str = ""
    ):
        """Configure response for a specific git command."""
        self.commands[command] = {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    def mock_run(self, cmd, **kwargs):
        """Mock subprocess.run for git commands."""
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        self.call_history.append((cmd_str, kwargs))

        # Check for configured responses
        for configured_cmd, response in self.commands.items():
            if configured_cmd in cmd_str:
                result = Mock()
                result.returncode = response["returncode"]
                result.stdout = response["stdout"]
                result.stderr = response["stderr"]
                return result

        # Default successful response
        result = Mock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    def get_call_history(self):
        """Get history of all git command calls."""
        return self.call_history

    def was_called_with(self, command: str) -> bool:
        """Check if a specific command was called."""
        return any(command in call[0] for call in self.call_history)


def create_mock_git() -> MockGit:
    """Create a configured mock git instance."""
    mock_git = MockGit()

    # Configure common git commands
    mock_git.configure_command("git init", returncode=0)
    mock_git.configure_command("git add", returncode=0)
    mock_git.configure_command("git commit", returncode=0)
    mock_git.configure_command("git status", returncode=0, stdout="On branch main")
    mock_git.configure_command("git log", returncode=0, stdout="commit abc123")
    mock_git.configure_command("git worktree add", returncode=0)
    mock_git.configure_command("git worktree remove", returncode=0)
    mock_git.configure_command("git sparse-checkout", returncode=0)
    mock_git.configure_command("git checkout", returncode=0)
    mock_git.configure_command(
        "git rev-parse --show-toplevel", returncode=0, stdout="/fake/repo"
    )

    return mock_git


def patch_git_operations():
    """Decorator/context manager to patch git operations."""
    mock_git = create_mock_git()
    return patch("subprocess.run", side_effect=mock_git.mock_run), mock_git
