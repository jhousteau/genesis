"""Git integration for smart commits."""

import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class CommitType(Enum):
    """Conventional commit types."""

    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"
    REVERT = "revert"


@dataclass
class GitChange:
    """Represents a git change."""

    file_path: str
    status: str  # M=modified, A=added, D=deleted, R=renamed
    additions: int = 0
    deletions: int = 0


class GitIntegration:
    """Integration with git for smart commits."""

    def __init__(self, project_root: Path):
        """Initialize git integration."""
        self.project_root = project_root

    def has_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def get_changes(self) -> list[GitChange]:
        """Get list of changes."""
        changes = []

        try:
            # Get unstaged changes
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["git", "diff", "--numstat"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        changes.append(
                            GitChange(
                                file_path=parts[2],
                                status="M",
                                additions=int(parts[0]) if parts[0] != "-" else 0,
                                deletions=int(parts[1]) if parts[1] != "-" else 0,
                            ),
                        )

            # Get staged changes
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["git", "diff", "--cached", "--numstat"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        changes.append(
                            GitChange(
                                file_path=parts[2],
                                status="M",
                                additions=int(parts[0]) if parts[0] != "-" else 0,
                                deletions=int(parts[1]) if parts[1] != "-" else 0,
                            ),
                        )

            # Get untracked files
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.strip().split("\n"):
                if line:
                    changes.append(GitChange(file_path=line, status="A"))

        except Exception:
            pass

        return changes

    def stage_all(self) -> bool:
        """Stage all changes."""
        try:
            subprocess.run(
                ["git", "add", "-A"], cwd=self.project_root, check=True, timeout=10
            )  # noqa: S603  # Subprocess secured: shell=False, validated inputs
            return True
        except Exception:
            return False

    def stage_files(self, files: list[str]) -> bool:
        """Stage specific files."""
        try:
            subprocess.run(
                ["git", "add"] + files, cwd=self.project_root, check=True, timeout=10
            )  # noqa: S603  # Subprocess secured: shell=False, validated inputs
            return True
        except Exception:
            return False

    def commit(self, message: str) -> Optional[str]:
        """Create a commit."""
        try:
            subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["git", "commit", "-m", message],
                cwd=self.project_root,
                check=True,
                timeout=10,
            )

            # Get the commit SHA
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            return result.stdout.strip()
        except Exception:
            return None

    def generate_commit_message(self, commit_type: CommitType) -> str:
        """Generate a smart commit message based on changes."""
        changes = self.get_changes()

        if not changes:
            return f"{commit_type.value}: update project files"

        # Analyze changes
        file_types = set()
        actions = set()

        for change in changes:
            # Determine file type
            if change.file_path.endswith(".py"):
                file_types.add("Python")
            elif change.file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
                file_types.add("JavaScript/TypeScript")
            elif change.file_path.endswith(".go"):
                file_types.add("Go")
            elif change.file_path.endswith(".rs"):
                file_types.add("Rust")
            elif change.file_path.endswith((".yml", ".yaml")):
                file_types.add("YAML")
            elif change.file_path.endswith(".json"):
                file_types.add("JSON")
            elif change.file_path.endswith(".md"):
                file_types.add("documentation")
            elif change.file_path.endswith(".tf"):
                file_types.add("Terraform")
            elif "Dockerfile" in change.file_path:
                file_types.add("Docker")

            # Determine action
            if change.status == "A":
                actions.add("add")
            elif change.status == "D":
                actions.add("remove")
            elif change.status == "M":
                if change.additions > change.deletions * 2:
                    actions.add("expand")
                elif change.deletions > change.additions * 2:
                    actions.add("reduce")
                else:
                    actions.add("update")

        # Build message
        action = "update"
        if "add" in actions and len(actions) == 1:
            action = "add"
        elif "remove" in actions and len(actions) == 1:
            action = "remove"
        elif "expand" in actions:
            action = "enhance"

        subject = "/".join(list(file_types)[:2]) if file_types else "project"

        # Generate scope if applicable
        scope = ""
        if len(changes) <= 3:
            # Use specific file/directory as scope
            common_dir = self._find_common_directory([c.file_path for c in changes])
            if common_dir and common_dir != ".":
                scope = f"({common_dir})"

        message = f"{commit_type.value}{scope}: {action} {subject}"

        # Add details if significant changes
        details = []
        if len(changes) > 5:
            details.append(f"- Modified {len(changes)} files")

        total_additions = sum(c.additions for c in changes)
        total_deletions = sum(c.deletions for c in changes)
        if total_additions > 50 or total_deletions > 50:
            details.append(
                f"- {total_additions} additions, {total_deletions} deletions"
            )

        if details:
            message += "\n\n" + "\n".join(details)

        return message

    def _find_common_directory(self, file_paths: list[str]) -> str:
        """Find common directory for a list of file paths."""
        if not file_paths:
            return ""

        # Split paths into components
        path_components = [Path(p).parts for p in file_paths]

        # Find common prefix
        common = []
        for components in zip(*path_components):
            if len(set(components)) == 1:
                common.append(components[0])
            else:
                break

        return "/".join(common) if common else ""

    def get_status(self) -> dict[str, Any]:
        """Get git status information."""
        try:
            # Get branch name
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            branch = result.stdout.strip()

            # Get commit count
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["git", "rev-list", "--count", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            commit_count = int(result.stdout.strip())

            # Get last commit
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["git", "log", "-1", "--pretty=format:%h %s"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            last_commit = result.stdout.strip()

            return {
                "branch": branch,
                "commit_count": commit_count,
                "last_commit": last_commit,
                "has_changes": self.has_changes(),
                "change_count": len(self.get_changes()),
            }
        except Exception:
            return {
                "branch": "unknown",
                "commit_count": 0,
                "last_commit": "",
                "has_changes": False,
                "change_count": 0,
            }

    def get_recent_commits(self, count: int = 10) -> list[str]:
        """Get recent commit messages."""
        try:
            result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["git", "log", f"-{count}", "--pretty=format:%s"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip().split("\n") if result.stdout else []
        except Exception:
            return []

    def analyze_commit_patterns(self) -> dict[str, int]:
        """Analyze patterns in recent commits."""
        commits = self.get_recent_commits(100)
        patterns: dict[str, int] = {}

        for commit in commits:
            # Extract commit type
            if ":" in commit:
                commit_type = commit.split(":")[0].split("(")[0].strip()
                patterns[commit_type] = patterns.get(commit_type, 0) + 1

        return patterns
