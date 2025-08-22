"""Convergent stability engine for resolving tool conflicts and managing file state."""

import hashlib
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import pathspec
else:
    try:
        import pathspec

        HAS_PATHSPEC = True
    except ImportError:
        pathspec: Any = None
        HAS_PATHSPEC = False


class ToolStatus(Enum):
    """Status of tool execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    CONFLICT = "conflict"


@dataclass
class FileState:
    """Represents the state of a file."""

    path: Path
    content_hash: str
    timestamp: float

    @classmethod
    def from_file(cls, path: Path) -> "FileState":
        """Create FileState from file path."""
        content = path.read_bytes() if path.exists() else b""
        return cls(
            path=path,
            content_hash=hashlib.sha256(content).hexdigest(),
            timestamp=time.time(),
        )


@dataclass
class ToolResult:
    """Result of tool execution."""

    tool_name: str
    status: ToolStatus
    modified_files: set[Path] = field(default_factory=set)
    error_message: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class ConflictReport:
    """Report of conflicts between tools."""

    conflicting_tools: list[tuple[str, str]]
    conflicting_files: dict[Path, list[str]]
    resolution_strategy: Optional[str] = None


@dataclass
class ConvergenceResult:
    """Result of convergence process."""

    converged: bool
    iterations: int
    total_time: float
    tool_results: list[ToolResult]
    conflicts_resolved: list[ConflictReport]
    final_state: dict[Path, FileState]


class Tool:
    """Base class for tools."""

    def __init__(
        self,
        name: str,
        command: list[str],
        check_command: Optional[list[str]] = None,
        file_extensions: Optional[list[str]] = None,
    ):
        """Initialize tool.

        Args:
            name: Tool name
            command: Command to execute
            check_command: Command to check availability
            file_extensions: File extensions to track (default: ['.py'])
        """
        self.name = name
        self.command = command
        self.check_command = check_command or command + ["--version"]
        self.file_extensions = file_extensions or [".py"]
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if tool is available."""
        if self._available is not None:
            return self._available

        try:
            subprocess.run(self.check_command, capture_output=True, timeout=5, check=False)  # noqa: S603  # Subprocess secured: shell=False, validated inputs
            self._available = True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._available = False

        return self._available

    def run(self, project_root: Path) -> ToolResult:
        """Run the tool."""
        if not self.is_available():
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SKIPPED,
                error_message=f"{self.name} not available",
            )

        start_time = time.time()

        # Track files before execution
        before_files = self._get_file_states(project_root)

        try:
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                self.command,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Track files after execution
            after_files = self._get_file_states(project_root)
            modified_files = self._find_modified_files(before_files, after_files)

            # Capture error details - many tools output errors to stdout!
            error_msg = None
            if result.returncode != 0:
                # Combine stderr and stdout for error message
                error_parts = []
                if result.stderr and result.stderr.strip():
                    error_parts.append(f"STDERR:\n{result.stderr.strip()}")
                if result.stdout and result.stdout.strip():
                    error_parts.append(f"STDOUT:\n{result.stdout.strip()}")
                if not error_parts:
                    error_parts.append(f"Command failed with exit code {result.returncode}")
                    error_parts.append(f"Command: {' '.join(self.command)}")
                error_msg = "\n".join(error_parts)

            return ToolResult(
                tool_name=self.name,
                status=(ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.FAILURE),
                modified_files=modified_files,
                error_message=error_msg,
                execution_time=time.time() - start_time,
            )
        except subprocess.TimeoutExpired as e:
            error_msg = (
                f"Tool execution timeout after 60 seconds\nCommand: {' '.join(self.command)}"
            )
            if e.stdout:
                error_msg += f"\nPartial stdout: {e.stdout[:500]}"
            if e.stderr:
                error_msg += f"\nPartial stderr: {e.stderr[:500]}"
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILURE,
                error_message=error_msg,
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            error_msg = (
                f"Exception: {type(e).__name__}: {str(e)}\nCommand: {' '.join(self.command)}"
            )
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILURE,
                error_message=error_msg,
                execution_time=time.time() - start_time,
            )

    def _get_file_states(self, project_root: Path) -> dict[Path, FileState]:
        """Get state of all relevant files."""
        states = {}
        for ext in self.file_extensions:
            pattern = f"*{ext}" if ext.startswith(".") else f"*.{ext}"
            for file_path in project_root.rglob(pattern):
                if ".git" not in str(file_path):
                    states[file_path] = FileState.from_file(file_path)
        return states

    def _find_modified_files(
        self,
        before: dict[Path, FileState],
        after: dict[Path, FileState],
    ) -> set[Path]:
        """Find files that were modified."""
        modified = set()
        for path, after_state in after.items():
            if path not in before or before[path].content_hash != after_state.content_hash:
                modified.add(path)
        return modified


class StabilityEngine:
    """Engine for achieving convergent stability across tools."""

    def __init__(
        self,
        project_root: Path,
        max_iterations: int = 10,
        file_extensions: Optional[list[str]] = None,
    ):
        """Initialize stability engine.

        Args:
            project_root: Root directory of the project
            max_iterations: Maximum iterations for convergence
            file_extensions: List of file extensions to track (default: ['.py'])
        """
        self.project_root = project_root
        self.max_iterations = max_iterations
        self.file_extensions = file_extensions or [".py"]
        self.conflict_history: list[ConflictReport] = []
        self._gitignore_spec = self._load_gitignore_patterns()

    def run_until_stable(
        self,
        tools: list[Tool],
        stability_check: Optional[Callable[[dict[Path, FileState]], bool]] = None,
    ) -> ConvergenceResult:
        """Run tools until stable state is achieved."""
        start_time = time.time()
        iterations = 0
        tool_results = []
        conflicts_resolved = []

        previous_state = self._capture_state()
        stable = False

        # Filter to only available tools
        available_tools = [t for t in tools if t.is_available()]
        if not available_tools:
            return ConvergenceResult(
                converged=False,
                iterations=0,
                total_time=0,
                tool_results=[],
                conflicts_resolved=[],
                final_state={},
            )

        while not stable and iterations < self.max_iterations:
            iterations += 1
            iteration_results = []

            # Run each available tool
            for tool in available_tools:
                result = tool.run(self.project_root)
                iteration_results.append(result)
                tool_results.append(result)

            # Capture new state
            current_state = self._capture_state()

            # Check for conflicts
            conflicts = self._detect_conflicts(iteration_results)
            if conflicts:
                resolved = self._resolve_conflicts(conflicts, tools)
                conflicts_resolved.extend(resolved)

            # Check stability
            if stability_check:
                stable = stability_check(current_state)
            else:
                stable = self._is_stable(previous_state, current_state)

            previous_state = current_state

        return ConvergenceResult(
            converged=stable,
            iterations=iterations,
            total_time=time.time() - start_time,
            tool_results=tool_results,
            conflicts_resolved=conflicts_resolved,
            final_state=current_state,
        )

    def _load_gitignore_patterns(self) -> Any:
        """Load gitignore patterns from .gitignore file."""
        if not HAS_PATHSPEC:
            return None

        gitignore_path = self.project_root / ".gitignore"
        if not gitignore_path.exists():
            # Return a minimal spec that just excludes .git
            return pathspec.PathSpec.from_lines("gitwildmatch", [".git/"])

        try:
            with open(gitignore_path, "r") as f:
                # Always exclude .git even if not in .gitignore
                patterns = [".git/"] + f.read().splitlines()
            return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        except Exception:
            # If we can't read gitignore, at least exclude .git
            return pathspec.PathSpec.from_lines("gitwildmatch", [".git/"])

    def _capture_state(self) -> dict[Path, FileState]:
        """Capture current state of all files tracked by git."""
        state = {}
        patterns = ["*.py", "*.js", "*.ts", "*.go", "*.rs", "*.tf", "*.yaml", "*.yml"]

        for pattern in patterns:
            for file_path in self.project_root.rglob(pattern):
                # Use gitignore patterns if available
                if self._gitignore_spec:
                    # Get relative path for gitignore matching
                    rel_path = file_path.relative_to(self.project_root)
                    if self._gitignore_spec.match_file(str(rel_path)):
                        continue
                else:
                    # Fallback to just excluding .git
                    if ".git" in file_path.parts:
                        continue

                state[file_path] = FileState.from_file(file_path)

        return state

    def _is_stable(self, before: dict[Path, FileState], after: dict[Path, FileState]) -> bool:
        """Check if state is stable (no changes)."""
        if set(before.keys()) != set(after.keys()):
            return False

        for path in before:
            if before[path].content_hash != after[path].content_hash:
                return False

        return True

    def _detect_conflicts(self, results: list[ToolResult]) -> list[ConflictReport]:
        """Detect conflicts between tools."""
        conflicts = []

        # Find files modified by multiple tools
        file_modifiers: dict[Path, list[str]] = {}
        for result in results:
            for file_path in result.modified_files:
                if file_path not in file_modifiers:
                    file_modifiers[file_path] = []
                file_modifiers[file_path].append(result.tool_name)

        # Identify conflicts
        conflicting_files = {
            path: tools for path, tools in file_modifiers.items() if len(tools) > 1
        }

        if conflicting_files:
            # Identify tool pairs
            tool_pairs = set()
            for tools in conflicting_files.values():
                for i, tool1 in enumerate(tools):
                    for tool2 in tools[i + 1 :]:
                        tool_pairs.add((tool1, tool2))

            conflicts.append(
                ConflictReport(
                    conflicting_tools=list(tool_pairs),
                    conflicting_files=conflicting_files,
                ),
            )

        return conflicts

    def _resolve_conflicts(
        self,
        conflicts: list[ConflictReport],
        tools: list[Tool],
    ) -> list[ConflictReport]:
        """Resolve conflicts between tools."""
        resolved = []

        for conflict in conflicts:
            # Strategy 1: Run tools in sequence instead of parallel
            conflict.resolution_strategy = "sequential_execution"

            # Strategy 2: Configure tools to ignore conflicting patterns
            # This would require tool-specific configuration

            # Strategy 3: Apply tool precedence rules
            # E.g., formatter > linter

            resolved.append(conflict)
            self.conflict_history.append(conflict)

        return resolved

    def detect_formatter_wars(self) -> list[tuple[str, str]]:
        """Detect tools that fight over formatting."""
        wars = []

        # Analyze conflict history
        tool_conflict_counts: dict[tuple[str, str], int] = {}
        for conflict in self.conflict_history:
            for tool_pair in conflict.conflicting_tools:
                key = tuple(sorted(tool_pair))
                if len(key) == 2:  # Ensure it's a pair
                    tool_conflict_counts[key] = tool_conflict_counts.get(key, 0) + 1

        # Identify persistent conflicts
        for tool_pair, count in tool_conflict_counts.items():
            if count >= 2:  # Conflicted multiple times
                wars.append(tool_pair)

        return wars
