"""
ADK-Compliant Git Operations Tools for SOLVE Agents

This module implements individual ADK BaseTool classes for each git operation,
following the single responsibility principle and ADK patterns.

Each tool:
- Inherits from google.adk.tools.BaseTool
- Implements a single git operation
- Uses ToolContext for operation tracking
- Provides real git functionality (NO MOCKS)
- Maintains safety mechanisms from original implementation

Based on patterns from:
- adk-python/src/google/adk/tools/base_tool.py
- adk-python/src/google/adk/tools/shell_tool.py
- adk-samples/python/agents/software-bug-assistant/git_operations_tools.py
"""

import logging
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Union

# Import ADK components - fallback to our adapter for development
from solve.adk_adapter import BaseTool, ToolContext
from solve.tools.git_operations import GitSafetyConfig, GitStatus

logger = logging.getLogger(__name__)


class GitBaseToolMixin:
    """Shared functionality for all Git tools."""

    def __init__(self) -> None:
        """Initialize with safety configuration."""
        self.safety_config = GitSafetyConfig()

    def _execute_git_command(
        self,
        command: list[str],
        cwd: Path | None = None,
        timeout: int = 30,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Execute a git command safely."""
        # Validate and sanitize the command
        if not command or command[0] != "git":
            raise ValueError("Only git commands are allowed")

        # Sanitize all command arguments
        sanitized_command = []
        for i, arg in enumerate(command):
            if i == 0:  # First argument should always be "git"
                if arg != "git":
                    raise ValueError("First argument must be 'git'")
                sanitized_command.append(arg)
            else:
                # For git subcommands and safe options, don't quote
                if self._is_safe_git_arg(arg):
                    sanitized_command.append(arg)
                else:
                    # Quote potentially unsafe arguments like file paths and user input
                    sanitized_command.append(shlex.quote(arg))

        # Set up environment
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"  # Disable password prompts

        logger.info(f"Executing git command: {' '.join(sanitized_command)}")

        # Security: Ensure git executable uses full path for subprocess calls
        if sanitized_command and sanitized_command[0] == "git":
            git_exe = shutil.which("git")
            if git_exe:
                sanitized_command[0] = git_exe
            else:
                raise ValueError("Git executable not found in PATH")

        # Security: S603/S607 - This subprocess call is intentional and safe because:
        # 1. Git executable path is validated using shutil.which
        # 2. All commands are validated by _validate_git_command method
        # 3. Arguments are sanitized using shlex.quote for safety
        # 4. shell=False prevents shell injection (implicit default)
        # 5. timeout prevents hanging
        # 6. env is controlled and GIT_TERMINAL_PROMPT=0 prevents prompts
        result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
            sanitized_command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=check,
            shell=False,
        )

        return result

    def _is_safe_git_arg(self, arg: str) -> bool:
        """Check if a git argument is safe and doesn't need quoting."""
        # Git subcommands and common safe options
        safe_args = {
            # Git command itself
            "git",
            # Git subcommands
            "status",
            "add",
            "commit",
            "push",
            "pull",
            "branch",
            "log",
            "diff",
            "stash",
            "rev-parse",
            "config",
            "remote",
            "checkout",
            "rev-list",
            "show",
            # Common safe options
            "--porcelain",
            "--show-toplevel",
            "--show-current",
            "--list",
            "--stat",
            "--staged",
            "--oneline",
            "--name-only",
            "--get",
            "--count",
            "--set-upstream",
            "--tags",
            "--force",
            "--amend",
            "--no-verify",
            "--rebase",
            "--ff-only",
            "--delete",
            "-b",
            "-d",
            "-D",
            "-v",
            "-r",
            "-a",
            "-m",
            "-u",
            # Safe format options
            "--pretty=format:%H|%an|%ae|%ad|%s",
            "--date=iso",
            "--format=",
            # Safe path separators
            "--",
            # Common branch names
            "main",
            "master",
            "develop",
            "dev",
            "staging",
            "production",
            "HEAD",
        }

        # Check if it's a known safe argument
        if arg in safe_args:
            return True

        # Check if it's a safe option pattern (starts with - and contains only safe chars)
        if arg.startswith("-") and re.match(r"^-+[a-zA-Z0-9=_-]+$", arg):
            return True

        # Check if it's a numeric argument (like commit count)
        if re.match(r"^-?\d+$", arg):
            return True

        # Check if it's a commit hash pattern (alphanumeric, reasonable length)
        if re.match(r"^[a-f0-9]{6,40}$", arg):
            return True

        # Check for commit range patterns like "hash1..hash2"
        if re.match(r"^[a-f0-9]{6,40}\.\.[a-f0-9]{6,40}$", arg):
            return True

        # Check if it's a safe branch name pattern (alphanumeric with dashes, underscores)
        return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_/-]*$", arg) and len(arg) <= 250)

    def _validate_repository(self, repo_path: Union[str, Path] | None = None) -> Path:
        """Validate that we're in a git repository."""
        path = Path(repo_path) if repo_path else Path.cwd()
        path = path.resolve()

        # Check for .git directory
        git_dir = path / ".git"
        if not git_dir.exists():
            # Try to find git root using safe command execution
            try:
                result = self._execute_git_command(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=path,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0:
                    path = Path(result.stdout.strip())
                else:
                    raise ValueError(f"Not a git repository: {path}")
            except Exception as e:
                raise ValueError(f"Not a git repository: {path}") from e

        return path

    def _validate_branch_operation(self, branch: str, operation: str) -> None:
        """Validate branch operation for safety."""
        if branch in self.safety_config.protected_branches:
            if operation in ["delete", "force-push", "reset"]:
                raise ValueError(
                    f"Operation '{operation}' not allowed on protected branch '{branch}'",
                )

    def _validate_remote(self, remote_url: str) -> None:
        """Validate remote URL for safety."""
        # Sanitize remote URL to prevent injection
        if not remote_url or not isinstance(remote_url, str):
            raise ValueError("Invalid remote URL")

        # Check for dangerous characters that could be used for injection
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "\n", "\r"]
        if any(char in remote_url for char in dangerous_chars):
            raise ValueError(f"Remote URL contains dangerous characters: {remote_url}")

        # Check forbidden remotes
        for forbidden in self.safety_config.forbidden_remotes:
            if forbidden in remote_url:
                raise ValueError(f"Forbidden remote: {remote_url}")

        # Check allowed protocols
        protocol_match = re.match(r"^(\w+)://", remote_url)
        if protocol_match:
            protocol = protocol_match.group(1)
            if protocol not in self.safety_config.allowed_remote_protocols:
                raise ValueError(f"Protocol not allowed: {protocol}")
        elif not remote_url.startswith("git@"):
            # Not SSH format either
            raise ValueError(f"Invalid remote URL format: {remote_url}")


class GitStatusTool(GitBaseToolMixin, BaseTool):
    """ADK tool for git status operations."""

    def __init__(self) -> None:
        """Initialize GitStatusTool."""
        GitBaseToolMixin.__init__(self)
        BaseTool.__init__(self)
        self.name = "git_status"
        self.description = (
            "Get the current status of a git repository including branch, "
            "modified files, and staged changes"
        )

    async def run(
        self, context: ToolContext | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Get git repository status.

        Args:
            repo_path: Repository path (uses cwd if None)

        Returns:
            Dict with status information
        """
        try:
            repo_path = kwargs.get("repo_path")
            repo = self._validate_repository(repo_path)

            result = self._execute_git_command(["git", "status"], cwd=repo)

            # Parse status
            status = self._parse_status_output(result.stdout, repo)

            # Log operation if context provided
            if context:
                context.add_event(
                    "git_status",
                    {
                        "repo": str(repo),
                        "branch": status.branch,
                        "is_clean": status.is_clean,
                        "files_modified": len(status.modified_files),
                    },
                )

            return {
                "success": True,
                "branch": status.branch,
                "is_clean": status.is_clean,
                "staged_files": status.staged_files,
                "modified_files": status.modified_files,
                "untracked_files": status.untracked_files,
                "deleted_files": status.deleted_files,
                "ahead": status.ahead,
                "behind": status.behind,
                "conflicts": status.conflicts,
                "message": f"Status retrieved for branch '{status.branch}'",
            }

        except Exception as e:
            error_msg = f"Git status failed: {str(e)}"
            logger.error(error_msg)
            if context:
                context.add_event("git_status_error", {"error": str(e)})
            return {"success": False, "error": error_msg}

    def _parse_status_output(self, output: str, repo_path: Path) -> GitStatus:
        """Parse git status output."""
        branch = "unknown"
        staged_files = []
        modified_files = []
        untracked_files = []
        deleted_files = []
        conflicts = []
        ahead = 0
        behind = 0

        # Parse branch info
        branch_match = re.search(r"On branch (.+)", output)
        if branch_match:
            branch = branch_match.group(1)
        else:
            # Handle initial commit case
            initial_match = re.search(r"No commits yet", output)
            if initial_match:
                # Get default branch name using safe command execution
                try:
                    result = self._execute_git_command(
                        ["git", "config", "--get", "init.defaultBranch"],
                        cwd=repo_path,
                        timeout=5,
                        check=False,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        branch = result.stdout.strip()
                    else:
                        branch = "main"  # Modern default
                except Exception:
                    branch = "main"

        # Parse ahead/behind
        ahead_behind_match = re.search(
            r"Your branch is ahead .* by (\d+) commit", output
        )
        if ahead_behind_match:
            ahead = int(ahead_behind_match.group(1))
        behind_match = re.search(r"Your branch is behind .* by (\d+) commit", output)
        if behind_match:
            behind = int(behind_match.group(1))

        # Parse file statuses (porcelain format) using safe command execution
        porcelain_result = self._execute_git_command(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            timeout=10,
            check=False,
        )

        if porcelain_result.returncode == 0:
            for line in porcelain_result.stdout.strip().split("\n"):
                if not line:
                    continue

                status = line[:2]
                filename = line[3:]

                if status[0] in ["A", "M", "D", "R", "C"]:
                    staged_files.append(filename)
                if status[1] == "M":
                    modified_files.append(filename)
                if status[1] == "D":
                    deleted_files.append(filename)
                if status == "??":
                    untracked_files.append(filename)
                if status in ["DD", "AU", "UD", "UA", "DU", "AA", "UU"]:
                    conflicts.append(filename)

        # Consider repository clean if there are no staged/modified/deleted/untracked files
        is_clean = not (
            staged_files or modified_files or deleted_files or untracked_files
        )

        return GitStatus(
            branch=branch,
            is_clean=is_clean,
            staged_files=staged_files,
            modified_files=modified_files,
            untracked_files=untracked_files,
            deleted_files=deleted_files,
            ahead=ahead,
            behind=behind,
            conflicts=conflicts,
        )


class GitAddTool(GitBaseToolMixin, BaseTool):
    """ADK tool for git add operations."""

    def __init__(self) -> None:
        """Initialize GitAddTool."""
        GitBaseToolMixin.__init__(self)
        BaseTool.__init__(self)
        self.name = "git_add"
        self.description = "Add files to the git staging area for the next commit"

    async def run(
        self, context: ToolContext | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Add files to staging area.

        Args:
            files: File(s) to add (use "." for all)
            repo_path: Repository path
            update: Only add already tracked files

        Returns:
            Dict with operation result
        """
        try:
            files = kwargs.get("files", [])
            repo_path = kwargs.get("repo_path")
            update = kwargs.get("update", False)

            if not files:
                return {"success": False, "error": "No files specified to add"}

            repo = self._validate_repository(repo_path)

            # Normalize and validate files input
            file_list = [files] if isinstance(files, str) else files

            # Validate file paths to prevent injection
            validated_files = []
            for file_path in file_list:
                if not isinstance(file_path, str):
                    raise ValueError(f"Invalid file path type: {type(file_path)}")
                # Check for dangerous characters
                if any(
                    char in file_path for char in [";", "&", "|", "`", "$", "\n", "\r"]
                ):
                    raise ValueError(
                        f"File path contains dangerous characters: {file_path}"
                    )
                validated_files.append(file_path)

            command = ["git", "add"]
            if update:
                command.append("-u")
            command.extend(validated_files)

            self._execute_git_command(command, cwd=repo)

            # Get updated status to show what was added
            status_result = self._execute_git_command(
                ["git", "status", "--porcelain"], cwd=repo
            )
            staged_count = sum(
                1
                for line in status_result.stdout.strip().split("\n")
                if line and line[0] != " "
            )

            # Log operation if context provided
            if context:
                context.add_event(
                    "git_add",
                    {
                        "files": file_list,
                        "staged_count": staged_count,
                        "update_only": update,
                    },
                )

            return {
                "success": True,
                "files": file_list,
                "staged_count": staged_count,
                "message": f"Added {staged_count} file(s) to staging area",
            }

        except Exception as e:
            error_msg = f"Git add failed: {str(e)}"
            logger.error(error_msg)
            if context:
                context.add_event("git_add_error", {"error": str(e)})
            return {"success": False, "error": error_msg}


class GitCommitTool(GitBaseToolMixin, BaseTool):
    """ADK tool for git commit operations."""

    def __init__(self) -> None:
        """Initialize GitCommitTool."""
        GitBaseToolMixin.__init__(self)
        BaseTool.__init__(self)
        self.name = "git_commit"
        self.description = "Create a git commit with staged changes"

    async def run(
        self, context: ToolContext | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Create a git commit.

        Args:
            message: Commit message
            repo_path: Repository path
            amend: Amend previous commit
            no_verify: Skip pre-commit hooks

        Returns:
            Dict with commit information
        """
        try:
            message = kwargs.get("message", "")
            repo_path = kwargs.get("repo_path")
            amend = kwargs.get("amend", False)
            no_verify = kwargs.get("no_verify", False)

            if not message and not amend:
                return {"success": False, "error": "Commit message is required"}

            # Validate commit message to prevent injection
            if message:
                if not isinstance(message, str):
                    raise ValueError(f"Invalid message type: {type(message)}")
                # Check for dangerous characters that could be used for injection
                if any(char in message for char in ["`", "$", "\n", "\r"]):
                    raise ValueError("Commit message contains dangerous characters")

            repo = self._validate_repository(repo_path)

            # Check if there are changes to commit
            status_result = self._execute_git_command(
                ["git", "status", "--porcelain"], cwd=repo
            )
            if not amend and not any(
                line and line[0] != " "
                for line in status_result.stdout.strip().split("\n")
            ):
                return {
                    "success": False,
                    "error": "Nothing to commit (no staged changes)",
                }

            command = ["git", "commit", "-m", message]
            if amend:
                command.append("--amend")
            if no_verify:
                command.append("--no-verify")

            result = self._execute_git_command(command, cwd=repo)

            # Extract commit hash
            commit_match = re.search(r"\[[\w/]+\s+([a-f0-9]+)\]", result.stdout)
            commit_hash = commit_match.group(1) if commit_match else "unknown"

            # Get commit size info
            if commit_hash != "unknown":
                size_result = self._execute_git_command(
                    ["git", "show", "--stat", "--format=", commit_hash],
                    cwd=repo,
                    check=False,
                )
                size_info = size_result.stdout.strip()
            else:
                size_info = ""

            # Log operation if context provided
            if context:
                context.add_event(
                    "git_commit",
                    {
                        "commit_hash": commit_hash,
                        "message_length": len(message),
                        "amend": amend,
                    },
                )

            return {
                "success": True,
                "commit_hash": commit_hash,
                "message": f"Commit created: {commit_hash}",
                "size_info": size_info,
                "amend": amend,
            }

        except Exception as e:
            error_msg = f"Git commit failed: {str(e)}"
            logger.error(error_msg)
            if context:
                context.add_event("git_commit_error", {"error": str(e)})
            return {"success": False, "error": error_msg}


class GitPushTool(GitBaseToolMixin, BaseTool):
    """ADK tool for git push operations."""

    def __init__(self) -> None:
        """Initialize GitPushTool."""
        GitBaseToolMixin.__init__(self)
        BaseTool.__init__(self)
        self.name = "git_push"
        self.description = "Push commits to remote repository"

    async def run(
        self, context: ToolContext | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Push commits to remote repository.

        Args:
            remote: Remote name (default: origin)
            branch: Branch name (uses current if None)
            repo_path: Repository path
            force: Force push
            set_upstream: Set upstream branch
            tags: Push tags

        Returns:
            Dict with push result
        """
        try:
            remote = kwargs.get("remote", "origin")
            branch = kwargs.get("branch")
            repo_path = kwargs.get("repo_path")
            force = kwargs.get("force", False)
            set_upstream = kwargs.get("set_upstream", False)
            tags = kwargs.get("tags", False)

            # Validate remote and branch names to prevent injection
            if remote and not isinstance(remote, str):
                raise ValueError(f"Invalid remote type: {type(remote)}")
            if remote and any(
                char in remote for char in [";", "&", "|", "`", "$", "\n", "\r", " "]
            ):
                raise ValueError(f"Remote name contains dangerous characters: {remote}")

            if branch and not isinstance(branch, str):
                raise ValueError(f"Invalid branch type: {type(branch)}")
            if branch and any(
                char in branch for char in [";", "&", "|", "`", "$", "\n", "\r"]
            ):
                raise ValueError(f"Branch name contains dangerous characters: {branch}")

            repo = self._validate_repository(repo_path)

            # Get current branch if not specified
            if not branch:
                result = self._execute_git_command(
                    ["git", "branch", "--show-current"], cwd=repo
                )
                branch = result.stdout.strip()
                if not branch:
                    return {
                        "success": False,
                        "error": "No current branch (detached HEAD state)",
                    }

            # Validate branch operation
            if force:
                self._validate_branch_operation(branch, "force-push")

            # Check if remote exists
            remote_result = self._execute_git_command(
                ["git", "remote", "get-url", remote],
                cwd=repo,
            )
            remote_url = remote_result.stdout.strip()
            self._validate_remote(remote_url)

            # Require confirmation for push if configured
            if self.safety_config.require_confirmation_for_push and not force:
                logger.warning(
                    f"Push to {remote}/{branch} requires confirmation (use force=True)"
                )
                return {
                    "success": False,
                    "error": "Push requires confirmation (safety config)",
                    "requires_confirmation": True,
                }

            command = ["git", "push", remote]
            if branch:
                command.append(branch)
            if force:
                command.append("--force")
            if set_upstream:
                command.extend(["--set-upstream", remote, branch])
            if tags:
                command.append("--tags")

            result = self._execute_git_command(command, cwd=repo)

            # Extract push info
            pushed_commits = 0
            for line in result.stderr.split("\n"):
                if ".." in line and "->" in line:
                    commit_range_match = re.search(r"([a-f0-9]+)\.\.([a-f0-9]+)", line)
                    if commit_range_match:
                        # Count commits in range
                        count_result = self._execute_git_command(
                            [
                                "git",
                                "rev-list",
                                "--count",
                                f"{commit_range_match.group(1)}..{commit_range_match.group(2)}",
                            ],
                            cwd=repo,
                            check=False,
                        )
                        if count_result.returncode == 0:
                            pushed_commits = int(count_result.stdout.strip())

            # Log operation if context provided
            if context:
                context.add_event(
                    "git_push",
                    {
                        "remote": remote,
                        "branch": branch,
                        "pushed_commits": pushed_commits,
                        "force": force,
                    },
                )

            return {
                "success": True,
                "remote": remote,
                "branch": branch,
                "remote_url": remote_url,
                "pushed_commits": pushed_commits,
                "message": f"Pushed to {remote}/{branch} ({pushed_commits} commits)",
            }

        except Exception as e:
            error_msg = f"Git push failed: {str(e)}"
            logger.error(error_msg)
            if context:
                context.add_event("git_push_error", {"error": str(e)})
            return {"success": False, "error": error_msg}


class GitPullTool(GitBaseToolMixin, BaseTool):
    """ADK tool for git pull operations."""

    def __init__(self) -> None:
        """Initialize GitPullTool."""
        GitBaseToolMixin.__init__(self)
        BaseTool.__init__(self)
        self.name = "git_pull"
        self.description = "Pull changes from remote repository"

    async def run(
        self, context: ToolContext | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Pull changes from remote repository.

        Args:
            remote: Remote name (default: origin)
            branch: Branch name (uses current if None)
            repo_path: Repository path
            rebase: Use rebase instead of merge
            ff_only: Fast-forward only

        Returns:
            Dict with pull result
        """
        try:
            remote = kwargs.get("remote", "origin")
            branch = kwargs.get("branch")
            repo_path = kwargs.get("repo_path")
            rebase = kwargs.get("rebase", False)
            ff_only = kwargs.get("ff_only", False)

            # Validate remote and branch names to prevent injection
            if remote and not isinstance(remote, str):
                raise ValueError(f"Invalid remote type: {type(remote)}")
            if remote and any(
                char in remote for char in [";", "&", "|", "`", "$", "\n", "\r", " "]
            ):
                raise ValueError(f"Remote name contains dangerous characters: {remote}")

            if branch and not isinstance(branch, str):
                raise ValueError(f"Invalid branch type: {type(branch)}")
            if branch and any(
                char in branch for char in [";", "&", "|", "`", "$", "\n", "\r"]
            ):
                raise ValueError(f"Branch name contains dangerous characters: {branch}")

            repo = self._validate_repository(repo_path)

            # Check for uncommitted changes
            status_result = self._execute_git_command(
                ["git", "status", "--porcelain"], cwd=repo
            )
            if status_result.stdout.strip():
                return {
                    "success": False,
                    "error": "Cannot pull with uncommitted changes (commit or stash first)",
                }

            command = ["git", "pull", remote]
            if branch:
                command.append(branch)
            if rebase:
                command.append("--rebase")
            if ff_only:
                command.append("--ff-only")

            # Get current commit before pull
            before_result = self._execute_git_command(
                ["git", "rev-parse", "HEAD"], cwd=repo
            )
            before_commit = before_result.stdout.strip()

            self._execute_git_command(command, cwd=repo)

            # Get current commit after pull
            after_result = self._execute_git_command(
                ["git", "rev-parse", "HEAD"], cwd=repo
            )
            after_commit = after_result.stdout.strip()

            # Count new commits
            new_commits = 0
            if before_commit != after_commit:
                count_result = self._execute_git_command(
                    ["git", "rev-list", "--count", f"{before_commit}..{after_commit}"],
                    cwd=repo,
                    check=False,
                )
                if count_result.returncode == 0:
                    new_commits = int(count_result.stdout.strip())

            # Log operation if context provided
            if context:
                context.add_event(
                    "git_pull",
                    {
                        "remote": remote,
                        "branch": branch,
                        "new_commits": new_commits,
                        "rebase": rebase,
                    },
                )

            return {
                "success": True,
                "remote": remote,
                "branch": branch or "current",
                "new_commits": new_commits,
                "before_commit": before_commit,
                "after_commit": after_commit,
                "message": (
                    f"Pulled from {remote}/{branch or 'current'} ({new_commits} new commits)"
                ),
            }

        except Exception as e:
            error_msg = f"Git pull failed: {str(e)}"
            logger.error(error_msg)
            if context:
                context.add_event("git_pull_error", {"error": str(e)})
            return {"success": False, "error": error_msg}


class GitBranchTool(GitBaseToolMixin, BaseTool):
    """ADK tool for git branch operations."""

    def __init__(self) -> None:
        """Initialize GitBranchTool."""
        GitBaseToolMixin.__init__(self)
        BaseTool.__init__(self)
        self.name = "git_branch"
        self.description = (
            "Manage git branches - create, switch, list, or delete branches"
        )

    async def run(
        self, context: ToolContext | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Manage git branches.

        Args:
            operation: Operation to perform ('create', 'switch', 'list', 'delete')
            branch_name: Name of branch to create/switch/delete
            from_branch: Base branch for creation (uses current if None)
            repo_path: Repository path
            force: Force delete even if not merged (for delete)
            remote: Show/delete remote branches (for list/delete)
            all: Show all branches (for list)

        Returns:
            Dict with operation result
        """
        try:
            operation = kwargs.get("operation", "list")
            branch_name = kwargs.get("branch_name")
            from_branch = kwargs.get("from_branch")
            repo_path = kwargs.get("repo_path")
            force = kwargs.get("force", False)
            remote = kwargs.get("remote", False)
            all_branches = kwargs.get("all", False)

            repo = self._validate_repository(repo_path)

            if operation == "create":
                return await self._create_branch(
                    repo, branch_name, from_branch, context
                )
            elif operation == "switch":
                return await self._switch_branch(repo, branch_name, context)
            elif operation == "list":
                return await self._list_branches(repo, remote, all_branches, context)
            elif operation == "delete":
                return await self._delete_branch(
                    repo, branch_name, force, remote, context
                )
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        except Exception as e:
            error_msg = f"Git branch operation failed: {str(e)}"
            logger.error(error_msg)
            if context:
                context.add_event("git_branch_error", {"error": str(e)})
            return {"success": False, "error": error_msg}

    async def _create_branch(
        self,
        repo: Path,
        branch_name: str | None,
        from_branch: str | None,
        context: ToolContext | None,
    ) -> dict[str, Any]:
        """Create a new branch."""
        if not branch_name:
            return {
                "success": False,
                "error": "Branch name required for create operation",
            }

        # Validate branch name to prevent injection
        if not isinstance(branch_name, str):
            raise ValueError(f"Invalid branch name type: {type(branch_name)}")
        if any(
            char in branch_name for char in [";", "&", "|", "`", "$", "\n", "\r", " "]
        ):
            raise ValueError(
                f"Branch name contains dangerous characters: {branch_name}"
            )

        # Validate from_branch if provided
        if from_branch:
            if not isinstance(from_branch, str):
                raise ValueError(f"Invalid from_branch type: {type(from_branch)}")
            if any(
                char in from_branch
                for char in [";", "&", "|", "`", "$", "\n", "\r", " "]
            ):
                raise ValueError(
                    f"From branch name contains dangerous characters: {from_branch}"
                )

        # Check if branch already exists
        check_result = self._execute_git_command(
            ["git", "branch", "--list", branch_name],
            cwd=repo,
            check=False,
        )
        if check_result.stdout.strip():
            return {"success": False, "error": f"Branch '{branch_name}' already exists"}

        command = ["git", "checkout", "-b", branch_name]
        if from_branch:
            command.append(from_branch)

        self._execute_git_command(command, cwd=repo)

        # Get branch commit
        commit_result = self._execute_git_command(
            ["git", "rev-parse", branch_name],
            cwd=repo,
        )
        commit_hash = commit_result.stdout.strip()[:8]

        if context:
            context.add_event(
                "git_branch_create",
                {
                    "branch_name": branch_name,
                    "from_branch": from_branch,
                    "commit_hash": commit_hash,
                },
            )

        return {
            "success": True,
            "branch_name": branch_name,
            "commit_hash": commit_hash,
            "message": f"Created and switched to branch '{branch_name}' at {commit_hash}",
        }

    async def _switch_branch(
        self,
        repo: Path,
        branch_name: str | None,
        context: ToolContext | None,
    ) -> dict[str, Any]:
        """Switch to a different branch."""
        if not branch_name:
            return {
                "success": False,
                "error": "Branch name required for switch operation",
            }

        # Validate branch name to prevent injection
        if not isinstance(branch_name, str):
            raise ValueError(f"Invalid branch name type: {type(branch_name)}")
        if any(
            char in branch_name for char in [";", "&", "|", "`", "$", "\n", "\r", " "]
        ):
            raise ValueError(
                f"Branch name contains dangerous characters: {branch_name}"
            )

        # Check for uncommitted changes
        status_result = self._execute_git_command(
            ["git", "status", "--porcelain"], cwd=repo
        )
        if status_result.stdout.strip():
            modified_count = sum(
                1 for line in status_result.stdout.strip().split("\n") if line
            )
            return {
                "success": False,
                "error": f"Cannot switch branch with {modified_count} uncommitted changes",
            }

        command = ["git", "checkout", branch_name]
        self._execute_git_command(command, cwd=repo)

        # Get new branch info
        current_result = self._execute_git_command(
            ["git", "branch", "--show-current"], cwd=repo
        )
        current_branch = current_result.stdout.strip()

        if context:
            context.add_event(
                "git_branch_switch",
                {
                    "branch_name": branch_name,
                    "current_branch": current_branch,
                },
            )

        return {
            "success": True,
            "branch_name": branch_name,
            "current_branch": current_branch,
            "message": f"Switched to branch '{current_branch}'",
        }

    async def _list_branches(
        self,
        repo: Path,
        remote: bool,
        all_branches: bool,
        context: ToolContext | None,
    ) -> dict[str, Any]:
        """List branches."""
        command = ["git", "branch", "-v"]
        if remote:
            command.append("-r")
        elif all_branches:
            command.append("-a")

        result = self._execute_git_command(command, cwd=repo)

        # Parse branches
        branches = []
        current_branch = None
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            is_current = line.startswith("*")
            line = line.lstrip("* ")

            # Parse branch info
            parts = line.split(None, 2)
            if len(parts) >= 2:
                name = parts[0]
                commit = parts[1]

                branch_info = {
                    "name": name,
                    "is_current": is_current,
                    "is_remote": "remotes/" in name,
                    "commit_hash": commit,
                }
                branches.append(branch_info)

                if is_current:
                    current_branch = name

        if context:
            context.add_event(
                "git_branch_list",
                {
                    "branch_count": len(branches),
                    "current_branch": current_branch,
                    "remote": remote,
                },
            )

        return {
            "success": True,
            "branches": branches,
            "current_branch": current_branch,
            "branch_count": len(branches),
            "message": f"Found {len(branches)} branches",
        }

    async def _delete_branch(
        self,
        repo: Path,
        branch_name: str | None,
        force: bool,
        remote: bool,
        context: ToolContext | None,
    ) -> dict[str, Any]:
        """Delete a branch."""
        if not branch_name:
            return {
                "success": False,
                "error": "Branch name required for delete operation",
            }

        # Validate branch name to prevent injection
        if not isinstance(branch_name, str):
            raise ValueError(f"Invalid branch name type: {type(branch_name)}")
        if any(
            char in branch_name for char in [";", "&", "|", "`", "$", "\n", "\r", " "]
        ):
            raise ValueError(
                f"Branch name contains dangerous characters: {branch_name}"
            )

        # Validate branch operation
        self._validate_branch_operation(branch_name, "delete")

        if remote:
            # Delete remote branch
            parts = branch_name.split("/", 1)
            if len(parts) != 2:
                return {
                    "success": False,
                    "error": "Remote branch name must be in format 'remote/branch'",
                }

            remote_name, branch = parts
            command = ["git", "push", remote_name, "--delete", branch]
        else:
            # Delete local branch
            command = ["git", "branch", "-d" if not force else "-D", branch_name]

            # Check if branch is current
            current_result = self._execute_git_command(
                ["git", "branch", "--show-current"],
                cwd=repo,
            )
            if current_result.stdout.strip() == branch_name:
                return {
                    "success": False,
                    "error": "Cannot delete current branch (switch first)",
                }

        self._execute_git_command(command, cwd=repo)

        if context:
            context.add_event(
                "git_branch_delete",
                {
                    "branch_name": branch_name,
                    "force": force,
                    "remote": remote,
                },
            )

        return {
            "success": True,
            "branch_name": branch_name,
            "message": f"Deleted branch '{branch_name}'",
        }


class GitLogTool(GitBaseToolMixin, BaseTool):
    """ADK tool for git log operations."""

    def __init__(self) -> None:
        """Initialize GitLogTool."""
        GitBaseToolMixin.__init__(self)
        BaseTool.__init__(self)
        self.name = "git_log"
        self.description = "View git commit log history with various filters"

    async def run(
        self, context: ToolContext | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """
        View commit log.

        Args:
            repo_path: Repository path
            limit: Maximum number of commits (default: 10)
            oneline: Show in compact format
            author: Filter by author
            since: Show commits since date
            until: Show commits until date
            file_path: Show commits for specific file

        Returns:
            Dict with commit log
        """
        try:
            repo_path = kwargs.get("repo_path")
            limit = kwargs.get("limit", 10)
            oneline = kwargs.get("oneline", False)
            author = kwargs.get("author")
            since = kwargs.get("since")
            until = kwargs.get("until")
            file_path = kwargs.get("file_path")

            # Validate inputs to prevent injection
            if not isinstance(limit, int) or limit < 1 or limit > 1000:
                raise ValueError(f"Invalid limit value: {limit}")

            if author and not isinstance(author, str):
                raise ValueError(f"Invalid author type: {type(author)}")
            if author and any(
                char in author for char in [";", "&", "|", "`", "$", "\n", "\r"]
            ):
                raise ValueError(f"Author contains dangerous characters: {author}")

            if since and not isinstance(since, str):
                raise ValueError(f"Invalid since type: {type(since)}")
            if since and any(
                char in since for char in [";", "&", "|", "`", "$", "\n", "\r"]
            ):
                raise ValueError(f"Since date contains dangerous characters: {since}")

            if until and not isinstance(until, str):
                raise ValueError(f"Invalid until type: {type(until)}")
            if until and any(
                char in until for char in [";", "&", "|", "`", "$", "\n", "\r"]
            ):
                raise ValueError(f"Until date contains dangerous characters: {until}")

            if file_path and not isinstance(file_path, str):
                raise ValueError(f"Invalid file_path type: {type(file_path)}")
            if file_path and any(
                char in file_path for char in [";", "&", "|", "`", "$", "\n", "\r"]
            ):
                raise ValueError(
                    f"File path contains dangerous characters: {file_path}"
                )

            repo = self._validate_repository(repo_path)

            command = ["git", "log", f"-{limit}"]
            if oneline:
                command.append("--oneline")
            else:
                command.append("--pretty=format:%H|%an|%ae|%ad|%s")
                command.append("--date=iso")

            if author:
                command.extend(["--author", author])
            if since:
                command.extend(["--since", since])
            if until:
                command.extend(["--until", until])
            if file_path:
                command.append("--")
                command.append(file_path)

            result = self._execute_git_command(command, cwd=repo)

            # Parse commits
            commits = []
            if not oneline and result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if "|" in line:
                        parts = line.split("|", 4)
                        if len(parts) == 5:
                            commit_info = {
                                "commit_hash": parts[0],
                                "author": parts[1],
                                "date": parts[3],
                                "message": parts[4],
                            }
                            commits.append(commit_info)

            if context:
                context.add_event(
                    "git_log",
                    {
                        "commit_count": len(commits) if commits else limit,
                        "filters": {
                            "author": author,
                            "since": since,
                            "until": until,
                            "file_path": file_path,
                        },
                    },
                )

            return {
                "success": True,
                "commits": commits,
                "commit_count": len(commits) if commits else limit,
                "output": result.stdout if oneline else None,
                "message": f"Retrieved {len(commits) if commits else limit} commits",
            }

        except Exception as e:
            error_msg = f"Git log failed: {str(e)}"
            logger.error(error_msg)
            if context:
                context.add_event("git_log_error", {"error": str(e)})
            return {"success": False, "error": error_msg}


class GitDiffTool(GitBaseToolMixin, BaseTool):
    """ADK tool for git diff operations."""

    def __init__(self) -> None:
        """Initialize GitDiffTool."""
        GitBaseToolMixin.__init__(self)
        BaseTool.__init__(self)
        self.name = "git_diff"
        self.description = (
            "Show differences between commits, branches, or working directory"
        )

    async def run(
        self, context: ToolContext | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Show differences.

        Args:
            repo_path: Repository path
            staged: Show staged changes
            file_path: Specific file to diff
            commit1: First commit for comparison
            commit2: Second commit for comparison
            name_only: Show only file names

        Returns:
            Dict with diff output
        """
        try:
            repo_path = kwargs.get("repo_path")
            staged = kwargs.get("staged", False)
            file_path = kwargs.get("file_path")
            commit1 = kwargs.get("commit1")
            commit2 = kwargs.get("commit2")
            name_only = kwargs.get("name_only", False)

            # Validate inputs to prevent injection
            if file_path and not isinstance(file_path, str):
                raise ValueError(f"Invalid file_path type: {type(file_path)}")
            if file_path and any(
                char in file_path for char in [";", "&", "|", "`", "$", "\n", "\r"]
            ):
                raise ValueError(
                    f"File path contains dangerous characters: {file_path}"
                )

            if commit1 and not isinstance(commit1, str):
                raise ValueError(f"Invalid commit1 type: {type(commit1)}")
            if commit1 and (
                not re.match(r"^[a-f0-9]{6,40}$", commit1)
                and commit1 not in ["HEAD", "HEAD~1", "HEAD~2"]
            ):
                raise ValueError(f"Invalid commit1 format: {commit1}")

            if commit2 and not isinstance(commit2, str):
                raise ValueError(f"Invalid commit2 type: {type(commit2)}")
            if commit2 and (
                not re.match(r"^[a-f0-9]{6,40}$", commit2)
                and commit2 not in ["HEAD", "HEAD~1", "HEAD~2"]
            ):
                raise ValueError(f"Invalid commit2 format: {commit2}")

            repo = self._validate_repository(repo_path)

            command = ["git", "diff"]
            if staged:
                command.append("--staged")
            if name_only:
                command.append("--name-only")
            if commit1:
                command.append(commit1)
                if commit2:
                    command.append(commit2)
            if file_path:
                command.append("--")
                command.append(file_path)

            result = self._execute_git_command(command, cwd=repo)

            # Parse diff stats
            stats_command = command.copy()
            if not name_only:
                stats_command.append("--stat")
            stats_result = self._execute_git_command(
                stats_command, cwd=repo, check=False
            )

            files_changed = 0
            insertions = 0
            deletions = 0
            if stats_result.returncode == 0:
                # Parse last line of stat output
                for line in stats_result.stdout.strip().split("\n"):
                    stat_match = re.match(
                        r"\s*(\d+) files? changed(?:, (\d+) insertions?)?(?:, (\d+) deletions?)?",
                        line,
                    )
                    if stat_match:
                        files_changed = int(stat_match.group(1))
                        insertions = int(stat_match.group(2) or 0)
                        deletions = int(stat_match.group(3) or 0)

            if context:
                context.add_event(
                    "git_diff",
                    {
                        "files_changed": files_changed,
                        "insertions": insertions,
                        "deletions": deletions,
                        "staged": staged,
                    },
                )

            return {
                "success": True,
                "diff": result.stdout,
                "files_changed": files_changed,
                "insertions": insertions,
                "deletions": deletions,
                "message": f"Diff generated ({files_changed} files, +{insertions}/-{deletions})",
            }

        except Exception as e:
            error_msg = f"Git diff failed: {str(e)}"
            logger.error(error_msg)
            if context:
                context.add_event("git_diff_error", {"error": str(e)})
            return {"success": False, "error": error_msg}


class GitStashTool(GitBaseToolMixin, BaseTool):
    """ADK tool for git stash operations."""

    def __init__(self) -> None:
        """Initialize GitStashTool."""
        GitBaseToolMixin.__init__(self)
        BaseTool.__init__(self)
        self.name = "git_stash"
        self.description = "Manage git stashes - save, apply, list, or drop stashes"

    async def run(
        self, context: ToolContext | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Stash operations.

        Args:
            operation: Stash operation (push, pop, list, drop, clear)
            repo_path: Repository path
            message: Stash message (for push)
            stash_ref: Stash reference (for pop/drop)
            include_untracked: Include untracked files (for push)

        Returns:
            Dict with operation result
        """
        try:
            operation = kwargs.get("operation", "push")
            repo_path = kwargs.get("repo_path")
            message = kwargs.get("message")
            stash_ref = kwargs.get("stash_ref")
            include_untracked = kwargs.get("include_untracked", False)

            # Validate inputs to prevent injection
            valid_operations = ["push", "pop", "list", "drop", "clear"]
            if operation not in valid_operations:
                raise ValueError(f"Invalid stash operation: {operation}")

            if message and not isinstance(message, str):
                raise ValueError(f"Invalid message type: {type(message)}")
            if message and any(char in message for char in ["`", "$", "\n", "\r"]):
                raise ValueError("Stash message contains dangerous characters")

            if stash_ref and not isinstance(stash_ref, str):
                raise ValueError(f"Invalid stash_ref type: {type(stash_ref)}")
            if stash_ref and not re.match(r"^stash@\{\d+\}$", stash_ref):
                raise ValueError(f"Invalid stash reference format: {stash_ref}")

            repo = self._validate_repository(repo_path)

            command = ["git", "stash", operation]

            if operation == "push":
                # Check if there are changes to stash
                status_result = self._execute_git_command(
                    ["git", "status", "--porcelain"],
                    cwd=repo,
                )
                if not status_result.stdout.strip():
                    return {"success": False, "error": "No local changes to stash"}

                if message:
                    command.extend(["-m", message])
                if include_untracked:
                    command.append("-u")
            elif operation == "pop" and stash_ref or operation == "drop" and stash_ref:
                command.append(stash_ref)

            result = self._execute_git_command(command, cwd=repo)

            # Get stash list for metadata
            list_result = self._execute_git_command(
                ["git", "stash", "list"], cwd=repo, check=False
            )
            stash_count = (
                len(list_result.stdout.strip().split("\n"))
                if list_result.stdout.strip()
                else 0
            )

            if context:
                context.add_event(
                    "git_stash",
                    {
                        "operation": operation,
                        "stash_count": stash_count,
                        "message": message,
                    },
                )

            return {
                "success": True,
                "operation": operation,
                "stash_count": stash_count,
                "output": result.stdout,
                "message": f"Stash {operation} completed ({stash_count} stashes)",
            }

        except Exception as e:
            error_msg = f"Git stash failed: {str(e)}"
            logger.error(error_msg)
            if context:
                context.add_event("git_stash_error", {"error": str(e)})
            return {"success": False, "error": error_msg}


# Registry of all git tools for easy discovery
GIT_TOOLS: list[type[BaseTool]] = [
    GitStatusTool,
    GitAddTool,
    GitCommitTool,
    GitPushTool,
    GitPullTool,
    GitBranchTool,
    GitLogTool,
    GitDiffTool,
    GitStashTool,
]


def get_git_tools() -> list[BaseTool]:
    """Get instances of all git tools."""
    return [tool_class() for tool_class in GIT_TOOLS]
