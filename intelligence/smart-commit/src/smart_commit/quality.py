"""Quality gates for ensuring system readiness."""

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import psutil


class QualityGate(Enum):
    """Types of quality gates."""

    RESOURCE_GATES = "resource_gates"
    PERMISSION_GATES = "permission_gates"
    DEPENDENCY_GATES = "dependency_gates"
    CONFIGURATION_GATES = "configuration_gates"
    STATE_GATES = "state_gates"


@dataclass
class QualityCheckResult:
    """Result of a quality check."""

    check_name: str
    passed: bool
    message: str
    details: Optional[dict[str, Any]] = None


@dataclass
class QualityGateResult:
    """Result of running a quality gate."""

    gate_type: QualityGate
    passed: bool
    checks: list[QualityCheckResult]

    @property
    def failed_checks(self) -> list[str]:
        """Get list of failed check names."""
        return [c.check_name for c in self.checks if not c.passed]


class QualityGateRunner:
    """Runner for quality gate checks."""

    def __init__(self, project_root: Path):
        """Initialize quality gate runner."""
        self.project_root = project_root

    def run_gate(self, gate_type: QualityGate) -> QualityGateResult:
        """Run a specific quality gate."""
        if gate_type == QualityGate.RESOURCE_GATES:
            checks = self._check_resources()
        elif gate_type == QualityGate.PERMISSION_GATES:
            checks = self._check_permissions()
        elif gate_type == QualityGate.DEPENDENCY_GATES:
            checks = self._check_dependencies()
        elif gate_type == QualityGate.CONFIGURATION_GATES:
            checks = self._check_configuration()
        elif gate_type == QualityGate.STATE_GATES:
            checks = self._check_state()
        else:
            checks = []

        passed = all(c.passed for c in checks)

        return QualityGateResult(gate_type=gate_type, passed=passed, checks=checks)

    def _check_resources(self) -> list[QualityCheckResult]:
        """Check system resources."""
        checks = []

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        checks.append(
            QualityCheckResult(
                check_name="cpu_usage",
                passed=cpu_percent < 80,
                message=f"CPU usage: {cpu_percent}%",
                details={"cpu_percent": cpu_percent},
            ),
        )

        # Memory usage
        memory = psutil.virtual_memory()
        checks.append(
            QualityCheckResult(
                check_name="memory_usage",
                passed=memory.percent < 85,
                message=f"Memory usage: {memory.percent}%",
                details={"memory_percent": memory.percent},
            ),
        )

        # Disk space
        disk = psutil.disk_usage(str(self.project_root))
        checks.append(
            QualityCheckResult(
                check_name="disk_space",
                passed=disk.percent < 90,
                message=f"Disk usage: {disk.percent}%",
                details={"disk_percent": disk.percent},
            ),
        )

        return checks

    def _check_permissions(self) -> list[QualityCheckResult]:
        """Check file permissions and access control."""
        checks = []

        # Check if we can write to project directory
        test_file = self.project_root / ".smart_commit_test"
        try:
            test_file.touch()
            test_file.unlink()
            can_write = True
        except Exception:
            can_write = False

        checks.append(
            QualityCheckResult(
                check_name="write_permission",
                passed=can_write,
                message="Write permission to project directory",
                details={"project_root": str(self.project_root)},
            ),
        )

        # Check for exposed secrets
        secret_patterns = [
            "*.key",
            "*.pem",
            ".env",
            ".env.local",
            "*_rsa",
            "*_dsa",
            "*_ecdsa",
            "*_ed25519",
        ]

        exposed_secrets = []
        for pattern in secret_patterns:
            for path in self.project_root.glob(pattern):
                if not str(path).startswith(".git"):
                    exposed_secrets.append(str(path.relative_to(self.project_root)))

        checks.append(
            QualityCheckResult(
                check_name="no_exposed_secrets",
                passed=len(exposed_secrets) == 0,
                message=f"Found {len(exposed_secrets)} potentially exposed secrets",
                details={"exposed_files": exposed_secrets},
            ),
        )

        return checks

    def _check_dependencies(self) -> list[QualityCheckResult]:
        """Check external dependencies."""
        checks = []

        # Check git availability
        git_available = self._check_command_available(["git", "--version"])
        checks.append(
            QualityCheckResult(
                check_name="git_available",
                passed=git_available,
                message="Git is available",
                details={"command": "git"},
            ),
        )

        # Check if in git repository (look in current and parent directories)
        is_git_repo = False
        git_dir = None
        current = self.project_root
        for _ in range(5):  # Check up to 5 levels up
            if (current / ".git").exists():
                is_git_repo = True
                git_dir = current / ".git"
                break
            if current.parent == current:  # Reached root
                break
            current = current.parent

        checks.append(
            QualityCheckResult(
                check_name="in_git_repo",
                passed=is_git_repo,
                message=f"Project is {'in' if is_git_repo else 'not in'} a git repository",
                details={"git_dir": str(git_dir) if git_dir else None},
            ),
        )

        # Check network connectivity (optional)
        # This is disabled by default as it may not be needed
        # and could slow down execution

        return checks

    def _check_configuration(self) -> list[QualityCheckResult]:
        """Check system configuration."""
        checks = []

        # Check for configuration files
        config_files = {
            "pyproject.toml": self.project_root / "pyproject.toml",
            "package.json": self.project_root / "package.json",
            ".gitignore": self.project_root / ".gitignore",
        }

        for name, path in config_files.items():
            if path.exists():
                checks.append(
                    QualityCheckResult(
                        check_name=f"config_{name}",
                        passed=True,
                        message=f"Found {name}",
                        details={"path": str(path)},
                    ),
                )

        # Check environment variables
        important_env_vars = ["PATH", "HOME", "USER"]
        for var in important_env_vars:
            value = os.environ.get(var)
            checks.append(
                QualityCheckResult(
                    check_name=f"env_{var}",
                    passed=value is not None,
                    message=f"Environment variable {var} is set",
                    details={"value": value[:50] if value else None},  # Truncate for security
                ),
            )

        return checks

    def _check_state(self) -> list[QualityCheckResult]:
        """Check system state consistency."""
        checks = []

        # Check for uncommitted changes (look for git in parent dirs too)
        git_exists = False
        current = self.project_root
        for _ in range(5):
            if (current / ".git").exists():
                git_exists = True
                break
            if current.parent == current:
                break
            current = current.parent

        if git_exists:
            try:
                result = subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                    ["git", "status", "--porcelain"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                has_changes = bool(result.stdout.strip())
                checks.append(
                    QualityCheckResult(
                        check_name="git_working_tree",
                        passed=True,  # Having changes is OK
                        message=f"Git working tree {'has changes' if has_changes else 'is clean'}",
                        details={"has_changes": has_changes},
                    ),
                )
            except Exception:
                pass

        # Check for running processes that might interfere
        interfering_processes = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = proc.info["name"].lower()
                if any(tool in name for tool in ["pytest", "mypy", "ruff", "black"]):
                    interfering_processes.append(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        checks.append(
            QualityCheckResult(
                check_name="no_interfering_processes",
                passed=len(interfering_processes) == 0,
                message=f"Found {len(interfering_processes)} potentially interfering processes",
                details={"processes": interfering_processes},
            ),
        )

        return checks

    def _check_command_available(self, command: list[str]) -> bool:
        """Check if a command is available."""
        try:
            subprocess.run(command, capture_output=True, timeout=5, check=False)  # noqa: S603  # Subprocess secured: shell=False, validated inputs
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_available_gates(self) -> list[str]:
        """Get list of available quality gates."""
        return [gate.value for gate in QualityGate]

    def run_all_gates(self) -> dict[str, QualityGateResult]:
        """Run all quality gates."""
        results = {}
        for gate in QualityGate:
            results[gate.value] = self.run_gate(gate)
        return results
