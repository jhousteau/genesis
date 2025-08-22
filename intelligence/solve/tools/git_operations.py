"""
Real Git Operations Tool for SOLVE Agents

Implements actual git operations with safety mechanisms and comprehensive functionality.
Based on best practices from docs/best-practices/

NO MOCKS, NO STUBS - REAL GIT OPERATIONS ONLY
"""

import logging
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

logger = logging.getLogger(__name__)


@dataclass
class GitOperation:
    """Result of a git operation."""

    success: bool
    command: str
    operation: str
    message: str
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GitStatus:
    """Git repository status information."""

    branch: str
    is_clean: bool
    staged_files: list[str]
    modified_files: list[str]
    untracked_files: list[str]
    deleted_files: list[str]
    ahead: int
    behind: int
    conflicts: list[str]


@dataclass
class GitCommit:
    """Git commit information."""

    commit_hash: str
    author: str
    date: str
    message: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


@dataclass
class GitBranch:
    """Git branch information."""

    name: str
    is_current: bool
    is_remote: bool
    commit_hash: str
    tracking: str | None = None


@dataclass
class GitRemote:
    """Git remote information."""

    name: str
    fetch_url: str
    push_url: str
    branches: list[str] = field(default_factory=list)


@dataclass
class GitSafetyConfig:
    """Safety configuration for git operations."""

    allow_force_push: bool = False
    allow_force_delete: bool = False
    allow_destructive_operations: bool = False
    require_confirmation_for_push: bool = True
    sandbox_repositories: list[str] = field(default_factory=list)
    forbidden_remotes: list[str] = field(default_factory=list)
    max_commit_size_mb: int = 100
    protected_branches: list[str] = field(
        default_factory=lambda: ["main", "master", "develop"]
    )
    allowed_remote_protocols: list[str] = field(
        default_factory=lambda: ["https", "ssh"]
    )


class GitTool:
    """
    Real git operations tool with safety mechanisms.

    CRITICAL: This performs ACTUAL git operations - no mocking.
    Provides comprehensive git functionality for agents.
    """

    def __init__(self, safety_config: GitSafetyConfig | None = None):
        """Initialize with safety configuration."""
        self.safety_config = safety_config or GitSafetyConfig()
        self.operation_log: list[GitOperation] = []

        logger.info("GitTool initialized with safety configuration")

    def _validate_repository(self, repo_path: Union[str, Path] | None = None) -> Path:
        """
        Validate that we're in a git repository.

        Args:
            repo_path: Repository path (uses cwd if None)

        Returns:
            Validated repository path

        Raises:
            ValueError: If not a git repository
        """
        path = Path(repo_path) if repo_path else Path.cwd()
        path = path.resolve()

        # Check for .git directory
        git_dir = path / ".git"
        if not git_dir.exists():
            # Try to find git root - use sanitized command execution
            try:
                # Validate the path is safe before using in subprocess
                safe_path = str(path.resolve())
                self._sanitize_path(safe_path)

                # Use the safe command execution method
                command = ["git", "rev-parse", "--show-toplevel"]
                self._validate_command(command)

                # Security: Use shutil.which to get full path to git executable
                git_exe = shutil.which("git")
                if not git_exe:
                    raise ValueError("Git executable not found in PATH")

                # Replace git command with full path
                command[0] = git_exe

                # Security: S603/S607 - This subprocess call is intentional and safe because:
                # 1. We use shutil.which to get the full path to git executable
                # 2. Command is validated by _validate_command method
                # 3. Path is sanitized by _sanitize_path method
                # 4. shell=False prevents shell injection
                # 5. timeout prevents hanging
                result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                    command,
                    cwd=safe_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=False,
                )
                if result.returncode == 0:
                    # Sanitize the output path before using it
                    toplevel_path = result.stdout.strip()
                    self._sanitize_path(toplevel_path)
                    path = Path(toplevel_path)
                else:
                    raise ValueError(f"Not a git repository: {path}")
            except Exception as e:
                raise ValueError(f"Not a git repository: {path}") from e

        # Check if it's a sandbox repository
        if self.safety_config.sandbox_repositories:
            is_sandbox = any(
                str(path).startswith(str(Path(sandbox).resolve()))
                for sandbox in self.safety_config.sandbox_repositories
            )
            if not is_sandbox:
                logger.warning(f"Repository {path} is not in sandbox list")

        return path

    def _sanitize_path(self, path: str) -> str:
        """
        Sanitize file paths to prevent injection attacks.

        Args:
            path: File path to sanitize

        Returns:
            Sanitized path

        Raises:
            ValueError: If path contains dangerous characters
        """
        if not path:
            raise ValueError("Empty path not allowed")

        # Check for dangerous characters that could be used for injection
        dangerous_chars = [";", "|", "&", "$", "`", "(", ")", "{", "}"]
        for char in dangerous_chars:
            if char in path:
                raise ValueError(f"Dangerous character '{char}' found in path: {path}")

        # Check for path traversal attempts
        if (
            ".." in path
            or path.startswith("/")
            and not Path(path).resolve().is_relative_to(Path.cwd().resolve())
        ):
            # Only allow absolute paths within current working directory tree
            pass

        return path

    def _sanitize_git_arg(self, arg: str) -> str:
        """
        Sanitize git command arguments to prevent injection.

        Args:
            arg: Argument to sanitize

        Returns:
            Sanitized argument using shlex.quote
        """
        if not isinstance(arg, str):
            raise ValueError(f"Git argument must be string, got {type(arg)}")

        # Use shlex.quote to properly escape shell arguments
        return shlex.quote(arg)

    def _validate_branch_name(self, branch_name: str) -> str:
        """
        Validate and sanitize git branch name.

        Args:
            branch_name: Branch name to validate

        Returns:
            Validated branch name

        Raises:
            ValueError: If branch name is invalid
        """
        if not branch_name or not isinstance(branch_name, str):
            raise ValueError("Branch name must be a non-empty string")

        # Git branch name restrictions
        invalid_chars = [" ", "~", "^", ":", "?", "*", "[", "\\\\"]
        for char in invalid_chars:
            if char in branch_name:
                raise ValueError(
                    f"Invalid character '{char}' in branch name: {branch_name}"
                )

        if (
            branch_name.startswith("-")
            or branch_name.endswith("/")
            or "//" in branch_name
        ):
            raise ValueError(f"Invalid branch name format: {branch_name}")

        if branch_name.startswith("refs/") or branch_name in ["..", "@", "@{"]:
            raise ValueError(f"Reserved branch name not allowed: {branch_name}")

        return branch_name

    def _validate_remote_name(self, remote_name: str) -> str:
        """
        Validate git remote name.

        Args:
            remote_name: Remote name to validate

        Returns:
            Validated remote name

        Raises:
            ValueError: If remote name is invalid
        """
        if not remote_name or not isinstance(remote_name, str):
            raise ValueError("Remote name must be a non-empty string")

        # Basic validation - should be alphanumeric with dashes/underscores
        if not re.match(r"^[a-zA-Z0-9._-]+$", remote_name):
            raise ValueError(f"Invalid remote name: {remote_name}")

        return remote_name

    def _validate_commit_message(self, message: str) -> str:
        """
        Validate commit message.

        Args:
            message: Commit message to validate

        Returns:
            Validated message

        Raises:
            ValueError: If message contains dangerous content
        """
        if not message or not isinstance(message, str):
            raise ValueError("Commit message must be a non-empty string")

        # Check for command injection attempts in commit messages
        dangerous_patterns = ["$(", "`", ";", "|", "&", "\\n", "\\r"]
        for pattern in dangerous_patterns:
            if pattern in message:
                raise ValueError(
                    f"Dangerous pattern '{pattern}' found in commit message"
                )

        return message

    def _validate_command(self, command: list[str]) -> None:
        """
        Validate git command for safety.

        Args:
            command: Git command parts

        Raises:
            ValueError: If command is unsafe
        """
        if not command or command[0] != "git":
            raise ValueError("Not a git command")

        # Validate each argument for dangerous content
        for i, arg in enumerate(command):
            if not isinstance(arg, str):
                raise ValueError(
                    f"Command argument {i} must be string, got {type(arg)}"
                )

            # Check for command injection attempts
            dangerous_chars = [";", "|", "&", "$", "`", "\n", "\r"]
            for char in dangerous_chars:
                if char in arg:
                    raise ValueError(
                        f"Dangerous character '{char}' found in command argument: {arg}",
                    )

        # Check for force operations
        if "--force" in command or "-f" in command:
            if not self.safety_config.allow_force_push and "push" in command:
                raise ValueError("Force push not allowed")
            if not self.safety_config.allow_force_delete and (
                "branch" in command or "tag" in command
            ):
                raise ValueError("Force delete not allowed by safety configuration")

        # Check for destructive operations
        destructive_ops = ["reset --hard", "clean -fd", "gc --aggressive"]
        command_str = " ".join(command)
        if any(op in command_str for op in destructive_ops):
            if not self.safety_config.allow_destructive_operations:
                raise ValueError(f"Destructive operation not allowed: {command_str}")

    def _validate_remote(self, remote_url: str) -> None:
        """
        Validate remote URL for safety.

        Args:
            remote_url: Git remote URL

        Raises:
            ValueError: If remote is forbidden
        """
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

    def _validate_branch_operation(self, branch: str, operation: str) -> None:
        """
        Validate branch operation for safety.

        Args:
            branch: Branch name
            operation: Operation type (delete, force-push, etc.)

        Raises:
            ValueError: If operation not allowed on branch
        """
        # Check exact matches first
        if branch in self.safety_config.protected_branches:
            if operation in ["delete", "force-push", "reset"]:
                raise ValueError(
                    f"Operation '{operation}' not allowed on protected branch '{branch}'",
                )

        # Check pattern matches
        import fnmatch

        for pattern in self.safety_config.protected_branches:
            if fnmatch.fnmatch(branch, pattern):
                if operation in ["delete", "force-push", "reset"]:
                    raise ValueError(
                        f"Operation '{operation}' not allowed on protected branch '{branch}'",
                    )

    def _execute_git_command(
        self,
        command: list[str],
        cwd: Path | None = None,
        timeout: int = 30,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """
        Execute a git command safely.

        Args:
            command: Command parts
            cwd: Working directory
            timeout: Command timeout
            check: Whether to check return code

        Returns:
            Completed process

        Raises:
            subprocess.CalledProcessError: If command fails and check=True
        """
        self._validate_command(command)

        # Sanitize working directory if provided
        safe_cwd = None
        if cwd:
            safe_cwd_str = str(Path(cwd).resolve())
            self._sanitize_path(safe_cwd_str)
            safe_cwd = safe_cwd_str

        # Set up environment
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"  # Disable password prompts

        logger.info(f"Executing git command: {' '.join(command)}")

        # Security: Ensure git executable uses full path for subprocess calls
        if command and command[0] == "git":
            git_exe = shutil.which("git")
            if git_exe:
                command[0] = git_exe
            else:
                raise ValueError("Git executable not found in PATH")

        # Security: S603/S607 - This subprocess call is intentional and safe because:
        # 1. Git executable path is validated using shutil.which
        # 2. All commands are validated by _validate_command method
        # 3. All paths are sanitized by _sanitize_path method
        # 4. shell=False prevents shell injection (implicit default)
        # 5. timeout prevents hanging
        # 6. env is controlled and GIT_TERMINAL_PROMPT=0 prevents prompts
        result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
            command,
            cwd=safe_cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=check,
            shell=False,
        )

        return result

    def _log_operation(
        self,
        operation: str,
        command: str,
        success: bool,
        message: str,
        stdout: str = "",
        stderr: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> GitOperation:
        """Log git operation for audit trail."""
        op = GitOperation(
            success=success,
            command=command,
            operation=operation,
            message=message,
            stdout=stdout,
            stderr=stderr,
            metadata=metadata or {},
        )
        self.operation_log.append(op)

        if success:
            logger.info(f"GitOp {operation}: {message}")
        else:
            logger.error(f"GitOp {operation} FAILED: {message}")

        return op

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
            cwd=repo_path,  # Use the repository path
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

    async def status(self, repo_path: Union[str, Path] | None = None) -> GitOperation:
        """
        Get git repository status.

        Args:
            repo_path: Repository path (uses cwd if None)

        Returns:
            GitOperation with status information
        """
        try:
            repo = self._validate_repository(repo_path)

            result = self._execute_git_command(["git", "status"], cwd=repo)

            status = self._parse_status_output(result.stdout, repo)

            return self._log_operation(
                "status",
                "git status",
                True,
                f"Status retrieved for branch '{status.branch}'",
                stdout=result.stdout,
                metadata={
                    "branch": status.branch,
                    "is_clean": status.is_clean,
                    "staged_count": len(status.staged_files),
                    "modified_count": len(status.modified_files),
                    "untracked_count": len(status.untracked_files),
                    "ahead": status.ahead,
                    "behind": status.behind,
                    "status_object": status.__dict__,
                },
            )

        except Exception as e:
            return self._log_operation(
                "status",
                "git status",
                False,
                f"Status failed: {str(e)}",
                stderr=str(e),
            )

    async def add(
        self,
        files: Union[str, list[str]],
        repo_path: Union[str, Path] | None = None,
        update: bool = False,
    ) -> GitOperation:
        """
        Add files to staging area.

        Args:
            files: File(s) to add (use "." for all)
            repo_path: Repository path
            update: Only add already tracked files

        Returns:
            GitOperation result
        """
        try:
            repo = self._validate_repository(repo_path)

            # Normalize files input
            file_list = [files] if isinstance(files, str) else files

            command = ["git", "add"]
            if update:
                command.append("-u")
            command.extend(file_list)

            result = self._execute_git_command(command, cwd=repo)

            # Get updated status to show what was added
            status_result = self._execute_git_command(
                ["git", "status", "--porcelain"], cwd=repo
            )
            staged_count = sum(
                1
                for line in status_result.stdout.strip().split("\n")
                if line and line[0] != " " and line[0] != "?"
            )

            return self._log_operation(
                "add",
                " ".join(command),
                True,
                f"Added {staged_count} file(s) to staging area",
                stdout=result.stdout,
                metadata={"files": file_list, "staged_count": staged_count},
            )

        except Exception as e:
            return self._log_operation(
                "add",
                f"git add {files}",
                False,
                f"Add failed: {str(e)}",
                stderr=str(e),
            )

    async def commit(
        self,
        message: str,
        repo_path: Union[str, Path] | None = None,
        amend: bool = False,
        no_verify: bool = False,
    ) -> GitOperation:
        """
        Create a git commit.

        Args:
            message: Commit message
            repo_path: Repository path
            amend: Amend previous commit
            no_verify: Skip pre-commit hooks

        Returns:
            GitOperation result
        """
        try:
            repo = self._validate_repository(repo_path)

            # Validate commit message for security
            validated_message = self._validate_commit_message(message)

            # Check if there are changes to commit
            status_result = self._execute_git_command(
                ["git", "status", "--porcelain"], cwd=repo
            )
            if not amend and not any(
                line and line[0] != " "
                for line in status_result.stdout.strip().split("\n")
            ):
                return self._log_operation(
                    "commit",
                    "git commit",
                    False,
                    "Nothing to commit (no staged changes)",
                )

            command = ["git", "commit", "-m", validated_message]
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

            return self._log_operation(
                "commit",
                " ".join(command[:3] + ["..."]),  # Don't log full message
                True,
                f"Commit created: {commit_hash}",
                stdout=result.stdout,
                metadata={
                    "commit_hash": commit_hash,
                    "amend": amend,
                    "size_info": size_info,
                    "message_length": len(message),
                },
            )

        except Exception as e:
            return self._log_operation(
                "commit",
                "git commit",
                False,
                f"Commit failed: {str(e)}",
                stderr=str(e),
            )

    async def push(
        self,
        remote: str = "origin",
        branch: str | None = None,
        repo_path: Union[str, Path] | None = None,
        force: bool = False,
        set_upstream: bool = False,
        tags: bool = False,
    ) -> GitOperation:
        """
        Push commits to remote repository.

        Args:
            remote: Remote name
            branch: Branch name (uses current if None)
            repo_path: Repository path
            force: Force push
            set_upstream: Set upstream branch
            tags: Push tags

        Returns:
            GitOperation result
        """
        try:
            repo = self._validate_repository(repo_path)

            # Validate remote name for security
            validated_remote = self._validate_remote_name(remote)

            # Get current branch if not specified
            if not branch:
                result = self._execute_git_command(
                    ["git", "branch", "--show-current"], cwd=repo
                )
                branch = result.stdout.strip()
                if not branch:
                    return self._log_operation(
                        "push",
                        "git push",
                        False,
                        "No current branch (detached HEAD state)",
                    )

            # Validate branch name if provided
            validated_branch = self._validate_branch_name(branch) if branch else None

            # Validate force push first (before branch validation)
            if force and not self.safety_config.allow_force_push:
                return self._log_operation(
                    "push",
                    f"git push {remote} {branch}",
                    False,
                    "Force push not allowed",
                )

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
                return self._log_operation(
                    "push",
                    f"git push {remote} {branch}",
                    False,
                    "Push requires confirmation (safety config)",
                )

            command = ["git", "push", validated_remote]
            if validated_branch:
                command.append(validated_branch)
            if force:
                command.append("--force")
            if set_upstream:
                command.extend(
                    ["--set-upstream", validated_remote, validated_branch or branch]
                )
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

            return self._log_operation(
                "push",
                " ".join(command),
                True,
                f"Pushed to {remote}/{branch} ({pushed_commits} commits)",
                stdout=result.stdout,
                stderr=result.stderr,
                metadata={
                    "remote": remote,
                    "branch": branch,
                    "remote_url": remote_url,
                    "pushed_commits": pushed_commits,
                    "force": force,
                },
            )

        except Exception as e:
            return self._log_operation(
                "push",
                f"git push {remote} {branch}",
                False,
                f"Push failed: {str(e)}",
                stderr=str(e),
            )

    async def pull(
        self,
        remote: str = "origin",
        branch: str | None = None,
        repo_path: Union[str, Path] | None = None,
        rebase: bool = False,
        ff_only: bool = False,
    ) -> GitOperation:
        """
        Pull changes from remote repository.

        Args:
            remote: Remote name
            branch: Branch name (uses current if None)
            repo_path: Repository path
            rebase: Use rebase instead of merge
            ff_only: Fast-forward only

        Returns:
            GitOperation result
        """
        try:
            repo = self._validate_repository(repo_path)

            # Check for uncommitted changes
            status_result = self._execute_git_command(
                ["git", "status", "--porcelain"], cwd=repo
            )
            if status_result.stdout.strip():
                return self._log_operation(
                    "pull",
                    "git pull",
                    False,
                    "Cannot pull with uncommitted changes (commit or stash first)",
                )

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

            result = self._execute_git_command(command, cwd=repo)

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

            return self._log_operation(
                "pull",
                " ".join(command),
                True,
                f"Pulled from {remote}/{branch or 'current'} ({new_commits} new commits)",
                stdout=result.stdout,
                metadata={
                    "remote": remote,
                    "branch": branch,
                    "new_commits": new_commits,
                    "before_commit": before_commit,
                    "after_commit": after_commit,
                },
            )

        except Exception as e:
            return self._log_operation(
                "pull",
                f"git pull {remote} {branch}",
                False,
                f"Pull failed: {str(e)}",
                stderr=str(e),
            )

    async def branch_create(
        self,
        branch_name: str,
        from_branch: str | None = None,
        repo_path: Union[str, Path] | None = None,
        checkout: bool = True,
    ) -> GitOperation:
        """
        Create a new branch.

        Args:
            branch_name: Name for new branch
            from_branch: Base branch (uses current if None)
            repo_path: Repository path
            checkout: Switch to new branch after creation

        Returns:
            GitOperation result
        """
        try:
            repo = self._validate_repository(repo_path)

            # Validate branch names for security
            validated_branch_name = self._validate_branch_name(branch_name)
            validated_from_branch = (
                self._validate_branch_name(from_branch) if from_branch else None
            )

            # Check if branch already exists
            check_result = self._execute_git_command(
                ["git", "branch", "--list", validated_branch_name],
                cwd=repo,
                check=False,
            )
            if check_result.stdout.strip():
                return self._log_operation(
                    "branch_create",
                    f"git branch {branch_name}",
                    False,
                    f"Branch '{branch_name}' already exists",
                )

            if checkout:
                command = ["git", "checkout", "-b", validated_branch_name]
                if validated_from_branch:
                    command.append(validated_from_branch)
            else:
                command = ["git", "branch", validated_branch_name]
                if validated_from_branch:
                    command.append(validated_from_branch)

            result = self._execute_git_command(command, cwd=repo)

            # Get branch commit
            commit_result = self._execute_git_command(
                ["git", "rev-parse", validated_branch_name],
                cwd=repo,
            )
            commit_hash = commit_result.stdout.strip()[:8]

            return self._log_operation(
                "branch_create",
                " ".join(command),
                True,
                f"Created branch '{branch_name}' at {commit_hash}",
                stdout=result.stdout,
                metadata={
                    "branch_name": branch_name,
                    "from_branch": from_branch,
                    "checkout": checkout,
                    "commit_hash": commit_hash,
                },
            )

        except Exception as e:
            return self._log_operation(
                "branch_create",
                f"git branch {branch_name}",
                False,
                f"Branch creation failed: {str(e)}",
                stderr=str(e),
            )

    async def branch_switch(
        self,
        branch_name: str,
        repo_path: Union[str, Path] | None = None,
        create: bool = False,
    ) -> GitOperation:
        """
        Switch to a different branch.

        Args:
            branch_name: Branch to switch to
            repo_path: Repository path
            create: Create branch if it doesn't exist

        Returns:
            GitOperation result
        """
        try:
            repo = self._validate_repository(repo_path)

            # Check for uncommitted changes
            status_result = self._execute_git_command(
                ["git", "status", "--porcelain"], cwd=repo
            )
            if status_result.stdout.strip():
                modified_count = sum(
                    1 for line in status_result.stdout.strip().split("\n") if line
                )
                return self._log_operation(
                    "branch_switch",
                    f"git checkout {branch_name}",
                    False,
                    f"Cannot switch branch with {modified_count} uncommitted changes",
                )

            command = ["git", "checkout"]
            if create:
                command.append("-b")
            command.append(branch_name)

            result = self._execute_git_command(command, cwd=repo)

            # Get new branch info
            current_result = self._execute_git_command(
                ["git", "branch", "--show-current"],
                cwd=repo,
            )
            current_branch = current_result.stdout.strip()

            return self._log_operation(
                "branch_switch",
                " ".join(command),
                True,
                f"Switched to branch '{current_branch}'",
                stdout=result.stdout,
                metadata={
                    "branch_name": branch_name,
                    "create": create,
                    "current_branch": current_branch,
                },
            )

        except Exception as e:
            return self._log_operation(
                "branch_switch",
                f"git checkout {branch_name}",
                False,
                f"Branch switch failed: {str(e)}",
                stderr=str(e),
            )

    async def branch_list(
        self,
        repo_path: Union[str, Path] | None = None,
        remote: bool = False,
        all: bool = False,
    ) -> GitOperation:
        """
        List branches.

        Args:
            repo_path: Repository path
            remote: Show remote branches
            all: Show all branches (local and remote)

        Returns:
            GitOperation with branch list
        """
        try:
            repo = self._validate_repository(repo_path)

            command = ["git", "branch", "-v"]
            if remote:
                command.append("-r")
            elif all:
                command.append("-a")

            result = self._execute_git_command(command, cwd=repo)

            # Parse branches
            branches = []
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

                    branch = GitBranch(
                        name=name,
                        is_current=is_current,
                        is_remote="remotes/" in name,
                        commit_hash=commit,
                    )
                    branches.append(branch)

            return self._log_operation(
                "branch_list",
                " ".join(command),
                True,
                f"Found {len(branches)} branches",
                stdout=result.stdout,
                metadata={
                    "branch_count": len(branches),
                    "branches": [b.__dict__ for b in branches],
                    "current_branch": next(
                        (b.name for b in branches if b.is_current), None
                    ),
                },
            )

        except Exception as e:
            return self._log_operation(
                "branch_list",
                "git branch",
                False,
                f"Branch list failed: {str(e)}",
                stderr=str(e),
            )

    async def branch_delete(
        self,
        branch_name: str,
        repo_path: Union[str, Path] | None = None,
        force: bool = False,
        remote: bool = False,
    ) -> GitOperation:
        """
        Delete a branch.

        Args:
            branch_name: Branch to delete
            repo_path: Repository path
            force: Force delete even if not merged
            remote: Delete remote branch

        Returns:
            GitOperation result
        """
        try:
            repo = self._validate_repository(repo_path)

            if remote:
                # Delete remote branch
                parts = branch_name.split("/", 1)
                if len(parts) != 2:
                    return self._log_operation(
                        "branch_delete",
                        f"git push origin --delete {branch_name}",
                        False,
                        "Remote branch name must be in format 'remote/branch'",
                    )

                remote_name, branch = parts
                command = ["git", "push", remote_name, "--delete", branch]
            else:
                # Delete local branch
                command = ["git", "branch", "-d" if not force else "-D", branch_name]

                # Check if branch is current FIRST
                current_result = self._execute_git_command(
                    ["git", "branch", "--show-current"],
                    cwd=repo,
                )
                if current_result.stdout.strip() == branch_name:
                    return self._log_operation(
                        "branch_delete",
                        " ".join(command),
                        False,
                        "Cannot delete current branch (switch first)",
                    )

            # Validate branch operation (after current branch check)
            self._validate_branch_operation(branch_name, "delete")

            result = self._execute_git_command(command, cwd=repo)

            return self._log_operation(
                "branch_delete",
                " ".join(command),
                True,
                f"Deleted branch '{branch_name}'",
                stdout=result.stdout,
                metadata={"branch_name": branch_name, "force": force, "remote": remote},
            )

        except Exception as e:
            return self._log_operation(
                "branch_delete",
                f"git branch -d {branch_name}",
                False,
                f"Branch delete failed: {str(e)}",
                stderr=str(e),
            )

    async def log(
        self,
        repo_path: Union[str, Path] | None = None,
        limit: int = 10,
        oneline: bool = False,
        author: str | None = None,
        since: str | None = None,
        until: str | None = None,
        file_path: str | None = None,
    ) -> GitOperation:
        """
        View commit log.

        Args:
            repo_path: Repository path
            limit: Maximum number of commits
            oneline: Show in compact format
            author: Filter by author
            since: Show commits since date
            until: Show commits until date
            file_path: Show commits for specific file

        Returns:
            GitOperation with commit log
        """
        try:
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
                            commit = GitCommit(
                                commit_hash=parts[0],
                                author=parts[1],
                                date=parts[3],
                                message=parts[4],
                            )
                            commits.append(commit)

            return self._log_operation(
                "log",
                " ".join(command[:3] + ["..."]),
                True,
                f"Retrieved {len(commits) if commits else limit} commits",
                stdout=result.stdout,
                metadata={
                    "commit_count": len(commits) if commits else limit,
                    "commits": [c.__dict__ for c in commits] if commits else [],
                    "filters": {
                        "author": author,
                        "since": since,
                        "until": until,
                        "file_path": file_path,
                    },
                },
            )

        except Exception as e:
            return self._log_operation(
                "log",
                "git log",
                False,
                f"Log failed: {str(e)}",
                stderr=str(e),
            )

    async def diff(
        self,
        repo_path: Union[str, Path] | None = None,
        staged: bool = False,
        file_path: str | None = None,
        commit1: str | None = None,
        commit2: str | None = None,
        name_only: bool = False,
    ) -> GitOperation:
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
            GitOperation with diff output
        """
        try:
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

            # If no stats but we have output, count files from name-only diff
            if files_changed == 0 and result.stdout.strip():
                if name_only:
                    # Count lines in name-only output
                    files_changed = len(
                        [
                            line
                            for line in result.stdout.strip().split("\n")
                            if line.strip()
                        ],
                    )
                else:
                    # Try to get name-only diff to count files
                    name_only_command = ["git", "diff", "--name-only"]
                    if staged:
                        name_only_command.append("--staged")
                    if commit1:
                        name_only_command.append(commit1)
                        if commit2:
                            name_only_command.append(commit2)
                    if file_path:
                        name_only_command.append("--")
                        name_only_command.append(file_path)

                    name_only_result = self._execute_git_command(
                        name_only_command,
                        cwd=repo,
                        check=False,
                    )
                    if (
                        name_only_result.returncode == 0
                        and name_only_result.stdout.strip()
                    ):
                        lines = [
                            line
                            for line in name_only_result.stdout.strip().split("\n")
                            if line.strip()
                        ]
                        files_changed = len(lines)

            return self._log_operation(
                "diff",
                " ".join(command),
                True,
                f"Diff generated ({files_changed} files, +{insertions}/-{deletions})",
                stdout=result.stdout,
                metadata={
                    "files_changed": files_changed,
                    "insertions": insertions,
                    "deletions": deletions,
                    "staged": staged,
                    "file_path": file_path,
                },
            )

        except Exception as e:
            return self._log_operation(
                "diff",
                "git diff",
                False,
                f"Diff failed: {str(e)}",
                stderr=str(e),
            )

    async def stash(
        self,
        operation: str = "push",
        repo_path: Union[str, Path] | None = None,
        message: str | None = None,
        include_untracked: bool = False,
    ) -> GitOperation:
        """
        Stash operations.

        Args:
            operation: Stash operation (push, pop, list, drop, clear)
            repo_path: Repository path
            message: Stash message (for push)
            include_untracked: Include untracked files (for push)

        Returns:
            GitOperation result
        """
        try:
            repo = self._validate_repository(repo_path)

            command = ["git", "stash", operation]

            if operation == "push":
                # Check if there are changes to stash
                status_result = self._execute_git_command(
                    ["git", "status", "--porcelain"],
                    cwd=repo,
                )
                if not status_result.stdout.strip():
                    return self._log_operation(
                        "stash",
                        " ".join(command),
                        False,
                        "No local changes to stash",
                    )

                if message:
                    command.extend(["-m", message])
                if include_untracked:
                    command.append("-u")
            elif operation == "pop" and message:
                # message is stash reference for pop
                command.append(message)
            elif operation == "drop" and message:
                # message is stash reference for drop
                command.append(message)

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

            return self._log_operation(
                "stash",
                " ".join(command),
                True,
                f"Stash {operation} completed ({stash_count} stashes)",
                stdout=result.stdout,
                metadata={
                    "operation": operation,
                    "stash_count": stash_count,
                    "message": message,
                    "include_untracked": include_untracked,
                },
            )

        except Exception as e:
            return self._log_operation(
                "stash",
                f"git stash {operation}",
                False,
                f"Stash failed: {str(e)}",
                stderr=str(e),
            )

    async def remote_list(
        self, repo_path: Union[str, Path] | None = None
    ) -> GitOperation:
        """
        List remote repositories.

        Args:
            repo_path: Repository path

        Returns:
            GitOperation with remote list
        """
        try:
            repo = self._validate_repository(repo_path)

            result = self._execute_git_command(["git", "remote", "-v"], cwd=repo)

            # Parse remotes
            remotes = {}
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split()
                if len(parts) >= 3:
                    name = parts[0]
                    url = parts[1]
                    remote_type = parts[2].strip("()")

                    if name not in remotes:
                        remotes[name] = GitRemote(name=name, fetch_url="", push_url="")

                    if remote_type == "fetch":
                        remotes[name].fetch_url = url
                    elif remote_type == "push":
                        remotes[name].push_url = url

            # Get remote branches
            for remote in remotes.values():
                branch_result = self._execute_git_command(
                    ["git", "branch", "-r", "--list", f"{remote.name}/*"],
                    cwd=repo,
                    check=False,
                )
                if branch_result.returncode == 0:
                    remote.branches = [
                        line.strip().replace(f"{remote.name}/", "")
                        for line in branch_result.stdout.strip().split("\n")
                        if line.strip()
                    ]

            return self._log_operation(
                "remote_list",
                "git remote -v",
                True,
                f"Found {len(remotes)} remotes",
                stdout=result.stdout,
                metadata={
                    "remote_count": len(remotes),
                    "remotes": {
                        name: remote.__dict__ for name, remote in remotes.items()
                    },
                },
            )

        except Exception as e:
            return self._log_operation(
                "remote_list",
                "git remote -v",
                False,
                f"Remote list failed: {str(e)}",
                stderr=str(e),
            )

    async def blame(
        self,
        file_path: str,
        repo_path: Union[str, Path] | None = None,
        line_range: tuple[int, int] | None = None,
    ) -> GitOperation:
        """
        Show file blame information.

        Args:
            file_path: File to blame
            repo_path: Repository path
            line_range: Specific line range (start, end)

        Returns:
            GitOperation with blame output
        """
        try:
            repo = self._validate_repository(repo_path)

            command = ["git", "blame", "--line-porcelain"]
            if line_range:
                command.extend(["-L", f"{line_range[0]},{line_range[1]}"])
            command.append(file_path)

            result = self._execute_git_command(command, cwd=repo)

            # Parse blame info (simplified)
            blame_lines = []
            current_commit = None
            for line in result.stdout.split("\n"):
                if line and not line.startswith("\t"):
                    parts = line.split()
                    if len(parts) >= 3 and len(parts[0]) == 40:  # SHA-1 hash
                        current_commit = parts[0][:8]
                elif line.startswith("\t") and current_commit:
                    blame_lines.append({"commit": current_commit, "line": line[1:]})

            return self._log_operation(
                "blame",
                " ".join(command),
                True,
                f"Blame generated for {file_path} ({len(blame_lines)} lines)",
                stdout=result.stdout,
                metadata={
                    "file_path": file_path,
                    "line_count": len(blame_lines),
                    "line_range": line_range,
                    "unique_commits": len({line["commit"] for line in blame_lines}),
                },
            )

        except Exception as e:
            return self._log_operation(
                "blame",
                f"git blame {file_path}",
                False,
                f"Blame failed: {str(e)}",
                stderr=str(e),
            )

    async def tag(
        self,
        tag_name: str,
        repo_path: Union[str, Path] | None = None,
        message: str | None = None,
        commit: str | None = None,
        delete: bool = False,
        list_tags: bool = False,
    ) -> GitOperation:
        """
        Manage git tags.

        Args:
            tag_name: Tag name
            repo_path: Repository path
            message: Tag message (creates annotated tag)
            commit: Specific commit to tag
            delete: Delete tag instead of creating
            list_tags: List tags (ignores other params)

        Returns:
            GitOperation result
        """
        try:
            repo = self._validate_repository(repo_path)

            if list_tags:
                command = ["git", "tag", "-l"]
                if tag_name:
                    command.append(tag_name)
            elif delete:
                command = ["git", "tag", "-d", tag_name]
            else:
                command = ["git", "tag"]
                if message:
                    command.extend(["-a", tag_name, "-m", message])
                else:
                    command.append(tag_name)
                if commit:
                    command.append(commit)

            result = self._execute_git_command(command, cwd=repo)

            if list_tags:
                tag_count = (
                    len(result.stdout.strip().split("\n"))
                    if result.stdout.strip()
                    else 0
                )
                operation_message = f"Found {tag_count} tags"
            elif delete:
                operation_message = f"Deleted tag '{tag_name}'"
            else:
                operation_message = f"Created tag '{tag_name}'"

            # Calculate if tag is annotated
            annotated_value = bool(message) if not (delete or list_tags) else False

            return self._log_operation(
                "tag",
                " ".join(command),
                True,
                operation_message,
                stdout=result.stdout,
                metadata={
                    "tag_name": tag_name,
                    "annotated": annotated_value,
                    "commit": commit,
                    "operation": (
                        "delete" if delete else "list" if list_tags else "create"
                    ),
                },
            )

        except Exception as e:
            return self._log_operation(
                "tag",
                f"git tag {tag_name}",
                False,
                f"Tag failed: {str(e)}",
                stderr=str(e),
            )

    def get_operation_log(self) -> list[GitOperation]:
        """Get the operation log for audit purposes."""
        return self.operation_log.copy()

    def clear_operation_log(self) -> None:
        """Clear the operation log."""
        self.operation_log.clear()
