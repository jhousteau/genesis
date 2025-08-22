"""Adaptive project detection engine for multi-technology projects."""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ProjectType(Enum):
    """Supported project types."""

    PYTHON = "python"
    NODEJS = "nodejs"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    TERRAFORM = "terraform"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    JAVA = "java"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    SHELL = "shell"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


@dataclass
class DetectionPattern:
    """Pattern for detecting project types."""

    file_patterns: list[str]
    required_files: list[str] = field(default_factory=list)
    content_patterns: dict[str, str] = field(default_factory=dict)
    priority: int = 0  # Higher = more specific


class ProjectDetector:
    """Detects project types based on file patterns and content."""

    DETECTION_PATTERNS: dict[ProjectType, DetectionPattern] = {
        ProjectType.PYTHON: DetectionPattern(
            file_patterns=["*.py"],
            required_files=[
                "pyproject.toml",
                "setup.py",
                "requirements.txt",
                "Pipfile",
            ],
            priority=10,
        ),
        ProjectType.NODEJS: DetectionPattern(
            file_patterns=["*.js", "*.mjs", "*.cjs"],
            required_files=["package.json"],
            priority=10,
        ),
        ProjectType.TYPESCRIPT: DetectionPattern(
            file_patterns=["*.ts", "*.tsx"],
            required_files=["tsconfig.json"],
            priority=15,  # Higher than Node.js
        ),
        ProjectType.GO: DetectionPattern(
            file_patterns=["*.go"],
            required_files=["go.mod", "go.sum"],
            priority=10,
        ),
        ProjectType.RUST: DetectionPattern(
            file_patterns=["*.rs"],
            required_files=["Cargo.toml"],
            priority=10,
        ),
        ProjectType.TERRAFORM: DetectionPattern(
            file_patterns=["*.tf", "*.tfvars"],
            required_files=[],
            priority=20,  # Infrastructure as priority
        ),
        ProjectType.DOCKER: DetectionPattern(
            file_patterns=["Dockerfile*", "*.dockerfile"],
            required_files=["docker-compose.yml", "docker-compose.yaml"],
            priority=15,
        ),
        ProjectType.KUBERNETES: DetectionPattern(
            file_patterns=["*.yaml", "*.yml"],
            content_patterns={"*.yaml": "kind:", "*.yml": "apiVersion:"},
            priority=25,  # Very specific
        ),
        ProjectType.JAVA: DetectionPattern(
            file_patterns=["*.java"],
            required_files=["pom.xml", "build.gradle", "build.gradle.kts"],
            priority=10,
        ),
        ProjectType.CSHARP: DetectionPattern(
            file_patterns=["*.cs", "*.csproj"],
            required_files=["*.sln", "*.csproj"],
            priority=10,
        ),
        ProjectType.RUBY: DetectionPattern(
            file_patterns=["*.rb"],
            required_files=["Gemfile", "Rakefile"],
            priority=10,
        ),
        ProjectType.PHP: DetectionPattern(
            file_patterns=["*.php"],
            required_files=["composer.json"],
            priority=10,
        ),
        ProjectType.SHELL: DetectionPattern(file_patterns=["*.sh", "*.bash"], priority=5),
        ProjectType.MARKDOWN: DetectionPattern(file_patterns=["*.md", "*.markdown"], priority=1),
    }

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize detector with project root."""
        self.project_root = Path(project_root or os.getcwd())
        self._file_cache: Optional[set[str]] = None

    def _get_all_files(self) -> set[str]:
        """Get all files in project (cached)."""
        if self._file_cache is not None:
            return self._file_cache

        files = set()
        ignore_dirs = {
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "target",
            "build",
            "dist",
            ".terraform",
        }

        for root, dirs, filenames in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), self.project_root)
                files.add(rel_path)

        self._file_cache = files
        return files

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches pattern (supports wildcards)."""
        from fnmatch import fnmatch

        return fnmatch(filename, pattern)

    def _check_content_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file contains pattern."""
        try:
            full_path = self.project_root / file_path
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                return pattern in content
        except Exception:
            pass
        return False

    def detect_project_types(self) -> dict[ProjectType, float]:
        """Detect all project types with confidence scores."""
        files = self._get_all_files()
        scores: dict[ProjectType, float] = {}

        for project_type, pattern in self.DETECTION_PATTERNS.items():
            score = 0.0
            matching_files = 0

            # Check file patterns
            for file in files:
                for file_pattern in pattern.file_patterns:
                    if self._matches_pattern(file, file_pattern):
                        matching_files += 1
                        break

            if matching_files > 0:
                score = min(matching_files / 10.0, 1.0) * 0.5  # Up to 50% from file patterns

            # Check required files (adds up to 40%)
            if pattern.required_files:
                found_required = 0
                for required in pattern.required_files:
                    for file in files:
                        if self._matches_pattern(file, required):
                            found_required += 1
                            break
                if pattern.required_files:
                    score += (found_required / len(pattern.required_files)) * 0.4

            # Check content patterns (adds up to 10%)
            if pattern.content_patterns:
                content_matches = 0
                for file_pattern, content_pattern in pattern.content_patterns.items():
                    for file in files:
                        if self._matches_pattern(file, file_pattern):
                            if self._check_content_pattern(file, content_pattern):
                                content_matches += 1
                                break
                if pattern.content_patterns:
                    score += (content_matches / len(pattern.content_patterns)) * 0.1

            # Apply priority multiplier
            if score > 0:
                score *= 1 + pattern.priority / 100
                scores[project_type] = min(score, 1.0)

        return scores

    def get_primary_type(self) -> ProjectType:
        """Get the primary project type."""
        scores = self.detect_project_types()
        if not scores:
            return ProjectType.UNKNOWN
        return max(scores.items(), key=lambda x: x[1])[0]

    def get_all_types(self, threshold: float = 0.3) -> list[ProjectType]:
        """Get all detected project types above threshold."""
        scores = self.detect_project_types()
        return [ptype for ptype, score in scores.items() if score >= threshold]

    def detect_tools(self) -> dict[str, bool]:
        """Detect available tools on the system."""
        import shutil

        tools = {
            # Python tools
            "python": shutil.which("python") or shutil.which("python3"),
            "pip": shutil.which("pip") or shutil.which("pip3"),
            "black": shutil.which("black"),
            "ruff": shutil.which("ruff"),
            "mypy": shutil.which("mypy"),
            "pytest": shutil.which("pytest"),
            "bandit": shutil.which("bandit"),
            # Node.js tools
            "node": shutil.which("node"),
            "npm": shutil.which("npm"),
            "yarn": shutil.which("yarn"),
            "pnpm": shutil.which("pnpm"),
            "prettier": shutil.which("prettier"),
            "eslint": shutil.which("eslint"),
            "tsc": shutil.which("tsc"),
            # Go tools
            "go": shutil.which("go"),
            "gofmt": shutil.which("gofmt"),
            "golangci-lint": shutil.which("golangci-lint"),
            # Rust tools
            "cargo": shutil.which("cargo"),
            "rustfmt": shutil.which("rustfmt"),
            "clippy": shutil.which("clippy"),
            # Infrastructure tools
            "terraform": shutil.which("terraform"),
            "docker": shutil.which("docker"),
            "kubectl": shutil.which("kubectl"),
            "helm": shutil.which("helm"),
            # General tools
            "git": shutil.which("git"),
            "make": shutil.which("make"),
        }

        return {tool: bool(path) for tool, path in tools.items()}
