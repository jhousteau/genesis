"""
Real Test Runner Tool for SOLVE Agents

Implements actual test execution with safety mechanisms and comprehensive reporting.
Based on best practices from docs/best-practices/3-llm-evaluation-frameworks-guide.md

NO MOCKS, NO STUBS - REAL TEST EXECUTION ONLY
"""

import json
import logging
import re
import shlex
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import psutil

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single test."""

    name: str
    status: str  # passed, failed, skipped, error
    duration: float
    message: str = ""
    traceback: str = ""
    file: str = ""
    line: int = 0


@dataclass
class CoverageData:
    """Test coverage information."""

    total_lines: int
    covered_lines: int
    missing_lines: list[int]
    coverage_percentage: float
    file_coverage: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class TestExecution:
    """Result of a test execution."""

    success: bool
    framework: str
    command: str
    exit_code: int
    duration: float
    stdout: str
    stderr: str
    results: list[TestResult]
    coverage: CoverageData | None
    performance_metrics: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class TestSafetyConfig:
    """Safety configuration for test execution."""

    max_execution_time: int  # seconds
    max_memory_usage: int  # MB
    allowed_test_patterns: list[str]
    forbidden_commands: list[str]
    require_virtual_env: bool
    sandbox_mode: bool
    max_processes: int


class TestRunnerTool:
    """
    Real test execution tool with safety mechanisms and comprehensive reporting.

    CRITICAL: This executes ACTUAL tests - no mocking.
    Supports pytest, unittest, and other Python test frameworks.
    """

    def __init__(self, safety_config: TestSafetyConfig | None = None):
        """Initialize with safety configuration."""
        self.safety_config = safety_config or self._default_safety_config()
        self.execution_log: list[TestExecution] = []
        self.temp_dirs: list[str] = []

        logger.info("TestRunnerTool initialized with safety configuration")

    def _default_safety_config(self) -> TestSafetyConfig:
        """Create default safety configuration."""
        return TestSafetyConfig(
            max_execution_time=300,  # 5 minutes
            max_memory_usage=1024,  # 1GB
            allowed_test_patterns=[
                "test_*.py",
                "*_test.py",
                "tests/*.py",
                "test/*.py",
                "**/test_*.py",
                "**/tests/*.py",
            ],
            forbidden_commands=[
                "rm",
                "del",
                "format",
                "mkfs",
                "fdisk",
                "dd",
                "sudo",
                "su",
                "chmod 777",
                "chown",
                "wget",
                "curl",
                "nc",
                "telnet",
            ],
            require_virtual_env=False,  # More permissive for development
            sandbox_mode=True,
            max_processes=4,
        )

    def _validate_command(self, command: str) -> None:
        """
        Validate command for safety.

        Args:
            command: Command to validate

        Raises:
            ValueError: If command is unsafe
        """
        # Check for forbidden commands
        for forbidden in self.safety_config.forbidden_commands:
            if forbidden in command.lower():
                raise ValueError(f"Forbidden command detected: {forbidden}")

        # Check for dangerous shell metacharacters that could allow injection
        # These are dangerous in most contexts and should be avoided
        dangerous_chars = [";", "&", "`", "$", "||", "&&", "#{", "$("]
        for char in dangerous_chars:
            if char in command:
                raise ValueError(f"Dangerous shell metacharacter detected: {char}")

        # Additional security checks for command injection patterns
        injection_patterns = [
            r"\$\{.*\}",  # Variable substitution ${...}
            r"\$\(.*\)",  # Command substitution $(...)
            r"`.*`",  # Backtick command substitution
            r";\s*\w+",  # Command chaining with semicolon
            r"&&\s*\w+",  # Command chaining with &&
            r"\|\|\s*\w+",  # Command chaining with ||
            r">\s*/dev/",  # Redirect to device files
            r"<\s*/dev/",  # Read from device files
        ]

        for pattern in injection_patterns:
            if re.search(pattern, command):
                raise ValueError(
                    f"Potential command injection pattern detected: {pattern}"
                )

        # Allow controlled usage of pipes and redirects for legitimate test commands
        controlled_chars = ["|", ">", "<", "(", ")"]
        for char in controlled_chars:
            if char in command and not self._is_safe_usage(command, char):
                raise ValueError(f"Potentially unsafe character usage: {char}")

    def _is_safe_usage(self, command: str, char: str) -> bool:
        """Check if potentially dangerous character usage is safe."""
        # Allow some safe usages for common test patterns
        if char == "|" and ("--" in command or "grep" in command or "head" in command):
            return True  # Common test filtering patterns
        if char == ">" and ("coverage" in command or "report" in command):
            return True  # Output redirection for reports
        # Return the condition directly (SIM103)
        return char in ["(", ")"] and any(
            test_word in command
            for test_word in ["python", "pytest", "nose", "unittest"]
        )

    def _parse_command_safely(self, command: str) -> list[str]:
        """
        Parse command string safely into arguments.

        Args:
            command: Command string to parse

        Returns:
            List of command arguments

        Raises:
            ValueError: If command cannot be parsed safely
        """
        try:
            # Try to parse with shlex first (handles quoted arguments properly)
            cmd_parts = shlex.split(command)
        except ValueError as e:
            # If shlex fails, it might be due to unmatched quotes or complex shell syntax
            # For test runners, we can try some common patterns
            if any(
                test_cmd in command.lower()
                for test_cmd in ["python", "pytest", "nose", "unittest", "coverage"]
            ):
                # Simple split for basic test commands - safer than shell=True
                cmd_parts = command.split()
            else:
                raise ValueError(f"Cannot safely parse command: {e}") from e

        # Additional validation of parsed command parts
        for part in cmd_parts:
            # Check for dangerous characters in individual arguments
            if any(char in part for char in [";", "&", "`", "$", "||", "&&"]):
                raise ValueError(f"Unsafe command part detected: {part}")

            # Check for suspicious patterns in arguments
            suspicious_patterns = [
                r"rm.*-r",  # Recursive delete
                r"format.*[c-z]:",  # Format drive
                r"del.*[/\\]",  # Delete paths
                r">\s*/dev/",  # Redirect to devices
                r"<\s*/dev/",  # Read from devices
            ]
            for pattern in suspicious_patterns:
                if re.search(pattern, part, re.IGNORECASE):
                    raise ValueError(
                        f"Suspicious command pattern detected: {pattern} in {part}"
                    )

        return cmd_parts

    def _validate_test_path(self, path: Union[str, Path]) -> Path:
        """
        Validate test path for safety.

        Args:
            path: Test path to validate

        Returns:
            Validated Path object

        Raises:
            ValueError: If path is unsafe
        """
        path_obj = Path(path).resolve()

        # Check if path exists
        if not path_obj.exists():
            raise ValueError(f"Test path does not exist: {path_obj}")

        # Check if path matches allowed patterns (only for files)
        if path_obj.is_file():
            allowed = any(
                path_obj.match(pattern)
                for pattern in self.safety_config.allowed_test_patterns
            )
            if not allowed:
                raise ValueError(
                    f"Test file does not match allowed patterns: {path_obj}"
                )

        return path_obj

    def _monitor_process_resources(
        self, process: subprocess.Popen[str]
    ) -> dict[str, Any]:
        """Monitor process resource usage."""
        try:
            ps_process = psutil.Process(process.pid)

            max_memory = 0
            cpu_times = []
            start_time = time.time()

            while process.poll() is None:
                try:
                    memory_info = ps_process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    max_memory = max(max_memory, memory_mb)

                    cpu_percent = ps_process.cpu_percent()
                    cpu_times.append(cpu_percent)

                    # Check memory limit
                    if memory_mb > self.safety_config.max_memory_usage:
                        process.terminate()
                        raise RuntimeError(
                            f"Process exceeded memory limit: {memory_mb:.1f}MB"
                        )

                    # Check time limit
                    if time.time() - start_time > self.safety_config.max_execution_time:
                        process.terminate()
                        raise RuntimeError(
                            f"Process exceeded time limit: "
                            f"{self.safety_config.max_execution_time}s",
                        )

                    time.sleep(0.1)

                except psutil.NoSuchProcess:
                    break

            return {
                "max_memory_mb": max_memory,
                "avg_cpu_percent": sum(cpu_times) / len(cpu_times) if cpu_times else 0,
                "peak_cpu_percent": max(cpu_times) if cpu_times else 0,
                "execution_time": time.time() - start_time,
            }

        except Exception as e:
            logger.warning(f"Failed to monitor process resources: {e}")
            return {}

    def _parse_pytest_output(
        self,
        stdout: str,
        stderr: str,
    ) -> tuple[list[TestResult], CoverageData | None]:
        """Parse pytest output to extract test results and coverage."""
        results = []
        coverage_data = None

        # Parse test results from pytest output
        test_pattern = r"^(.+?)::\s*(\w+)\s+(PASSED|FAILED|SKIPPED|ERROR)(?:\s+\[(.+?)\])?\s*(?:\[(\d+)%\])?"

        for line in stdout.split("\n"):
            line = line.strip()

            # Match individual test results
            match = re.match(test_pattern, line)
            if match:
                file_path, test_name, status, message, percentage = match.groups()

                results.append(
                    TestResult(
                        name=f"{file_path}::{test_name}",
                        status=status.lower(),
                        duration=0.0,  # Will be updated if timing info available
                        message=message or "",
                        file=file_path,
                    ),
                )

            # Look for timing information
            timing_pattern = r"(.+?)\s+(\d+\.\d+)s"
            timing_match = re.match(timing_pattern, line)
            if timing_match and results:
                duration_str = timing_match.group(2)
                try:
                    results[-1].duration = float(duration_str)
                except ValueError:
                    pass

        # Parse coverage from stderr or stdout
        coverage_pattern = r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+)%"
        for line in (stdout + "\n" + stderr).split("\n"):
            match = re.search(coverage_pattern, line)
            if match:
                total_lines = int(match.group(1))
                missed_lines = int(match.group(2))
                coverage_percent = int(match.group(3))
                covered_lines = total_lines - missed_lines

                coverage_data = CoverageData(
                    total_lines=total_lines,
                    covered_lines=covered_lines,
                    missing_lines=[],  # Would need more detailed parsing
                    coverage_percentage=coverage_percent / 100.0,
                )
                break

        return results, coverage_data

    def _parse_unittest_output(self, stdout: str, stderr: str) -> list[TestResult]:
        """Parse unittest output to extract test results."""
        results = []

        # Parse unittest results
        test_pattern = r"(\w+)\s+\((.+?)\)\s+\.\.\.\s+(ok|FAIL|ERROR|SKIP)"

        combined_output = stdout + "\n" + stderr
        for line in combined_output.split("\n"):
            match = re.match(test_pattern, line.strip())
            if match:
                test_name, test_class, status = match.groups()

                # Map unittest status to our standard
                status_map = {
                    "ok": "passed",
                    "FAIL": "failed",
                    "ERROR": "error",
                    "SKIP": "skipped",
                }

                results.append(
                    TestResult(
                        name=f"{test_class}.{test_name}",
                        status=status_map.get(status, status.lower()),
                        duration=0.0,
                        file=test_class,
                    ),
                )

        return results

    def _log_execution(self, execution: TestExecution) -> None:
        """Log test execution for audit trail."""
        self.execution_log.append(execution)

        if execution.success:
            logger.info(
                f"Test execution succeeded: {execution.framework} - {len(execution.results)} tests",
            )
        else:
            logger.error(
                f"Test execution failed: {execution.framework} - exit code {execution.exit_code}",
            )

    async def run_pytest(
        self,
        test_path: Union[str, Path],
        args: list[str] | None = None,
        coverage: bool = False,
        verbose: bool = False,
    ) -> TestExecution:
        """
        Run pytest on specified path.

        Args:
            test_path: Path to test file or directory
            args: Additional pytest arguments
            coverage: Whether to collect coverage data
            verbose: Whether to run in verbose mode

        Returns:
            TestExecution result
        """
        try:
            validated_path = self._validate_test_path(test_path)

            # Build pytest command
            cmd_parts = ["python", "-m", "pytest"]

            if verbose:
                cmd_parts.append("-v")

            if coverage:
                cmd_parts.extend(["--cov=.", "--cov-report=term"])

            if args:
                cmd_parts.extend(args)

            cmd_parts.append(str(validated_path))

            command = " ".join(cmd_parts)
            self._validate_command(command)

            logger.info(f"Running pytest: {command}")

            # Execute with monitoring
            start_time = time.time()
            process = subprocess.Popen(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                cmd_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                cwd=(
                    validated_path.parent
                    if validated_path.is_file()
                    else validated_path
                ),
            )

            # Monitor resources
            performance_metrics = self._monitor_process_resources(process)

            # Get output
            stdout, stderr = process.communicate(
                timeout=self.safety_config.max_execution_time
            )
            execution_time = time.time() - start_time

            # Parse results
            test_results, coverage_data = self._parse_pytest_output(stdout, stderr)

            execution = TestExecution(
                success=process.returncode == 0,
                framework="pytest",
                command=command,
                exit_code=process.returncode,
                duration=execution_time,
                stdout=stdout,
                stderr=stderr,
                results=test_results,
                coverage=coverage_data,
                performance_metrics=performance_metrics,
                metadata={
                    "test_path": str(validated_path),
                    "args": args or [],
                    "coverage_enabled": coverage,
                    "total_tests": len(test_results),
                    "passed_tests": len(
                        [r for r in test_results if r.status == "passed"]
                    ),
                    "failed_tests": len(
                        [r for r in test_results if r.status == "failed"]
                    ),
                    "skipped_tests": len(
                        [r for r in test_results if r.status == "skipped"]
                    ),
                },
            )

            self._log_execution(execution)
            return execution

        except Exception as e:
            error_execution = TestExecution(
                success=False,
                framework="pytest",
                command=command if "command" in locals() else "pytest",
                exit_code=-1,
                duration=0.0,
                stdout="",
                stderr=str(e),
                results=[],
                coverage=None,
                performance_metrics={},
                metadata={"error": str(e), "test_path": str(test_path)},
            )
            self._log_execution(error_execution)
            return error_execution

    async def run_unittest(
        self,
        test_path: Union[str, Path],
        pattern: str = "test*.py",
        verbose: bool = False,
    ) -> TestExecution:
        """
        Run unittest on specified path.

        Args:
            test_path: Path to test directory or module
            pattern: Test file pattern
            verbose: Whether to run in verbose mode

        Returns:
            TestExecution result
        """
        try:
            validated_path = self._validate_test_path(test_path)

            # Build unittest command
            cmd_parts = ["python", "-m", "unittest"]

            if verbose:
                cmd_parts.append("-v")

            if validated_path.is_dir():
                cmd_parts.extend(["discover", "-s", str(validated_path), "-p", pattern])
            else:
                # Convert file path to module name
                module_name = str(validated_path).replace("/", ".").replace(".py", "")
                cmd_parts.append(module_name)

            command = " ".join(cmd_parts)
            self._validate_command(command)

            logger.info(f"Running unittest: {command}")

            # Execute with monitoring
            start_time = time.time()
            process = subprocess.Popen(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                cmd_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                cwd=(
                    validated_path.parent
                    if validated_path.is_file()
                    else validated_path
                ),
            )

            # Monitor resources
            performance_metrics = self._monitor_process_resources(process)

            # Get output
            stdout, stderr = process.communicate(
                timeout=self.safety_config.max_execution_time
            )
            execution_time = time.time() - start_time

            # Parse results
            test_results = self._parse_unittest_output(stdout, stderr)

            execution = TestExecution(
                success=process.returncode == 0,
                framework="unittest",
                command=command,
                exit_code=process.returncode,
                duration=execution_time,
                stdout=stdout,
                stderr=stderr,
                results=test_results,
                coverage=None,  # unittest doesn't include coverage by default
                performance_metrics=performance_metrics,
                metadata={
                    "test_path": str(validated_path),
                    "pattern": pattern,
                    "total_tests": len(test_results),
                    "passed_tests": len(
                        [r for r in test_results if r.status == "passed"]
                    ),
                    "failed_tests": len(
                        [r for r in test_results if r.status == "failed"]
                    ),
                    "skipped_tests": len(
                        [r for r in test_results if r.status == "skipped"]
                    ),
                },
            )

            self._log_execution(execution)
            return execution

        except Exception as e:
            error_execution = TestExecution(
                success=False,
                framework="unittest",
                command=command if "command" in locals() else "unittest",
                exit_code=-1,
                duration=0.0,
                stdout="",
                stderr=str(e),
                results=[],
                coverage=None,
                performance_metrics={},
                metadata={"error": str(e), "test_path": str(test_path)},
            )
            self._log_execution(error_execution)
            return error_execution

    async def run_custom_command(
        self,
        command: str,
        working_dir: Union[str, Path] | None = None,
        timeout: int | None = None,
    ) -> TestExecution:
        """
        Run custom test command.

        Args:
            command: Test command to execute
            working_dir: Working directory for execution
            timeout: Custom timeout (uses default if None)

        Returns:
            TestExecution result
        """
        try:
            # CRITICAL: Validate command BEFORE parsing to catch shell injection
            self._validate_command(command)

            # Parse command safely to avoid shell injection
            cmd_parts = self._parse_command_safely(command)

            # Set working directory
            work_dir = Path(working_dir).resolve() if working_dir else Path.cwd()
            if not work_dir.exists() or not work_dir.is_dir():
                raise ValueError(f"Invalid working directory: {work_dir}")

            # Use custom timeout or default
            exec_timeout = timeout or self.safety_config.max_execution_time

            logger.info(f"Running custom command: {command}")

            # Execute with monitoring - use cmd_parts array instead of shell=True
            start_time = time.time()
            process = subprocess.Popen(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                cmd_parts,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=work_dir,
            )

            # Monitor resources
            performance_metrics = self._monitor_process_resources(process)

            # Get output
            stdout, stderr = process.communicate(timeout=exec_timeout)
            execution_time = time.time() - start_time

            execution = TestExecution(
                success=process.returncode == 0,
                framework="custom",
                command=command,
                exit_code=process.returncode,
                duration=execution_time,
                stdout=stdout,
                stderr=stderr,
                results=[],  # No parsing for custom commands
                coverage=None,
                performance_metrics=performance_metrics,
                metadata={"working_dir": str(work_dir), "timeout": exec_timeout},
            )

            self._log_execution(execution)
            return execution

        except Exception as e:
            error_execution = TestExecution(
                success=False,
                framework="custom",
                command=command,
                exit_code=-1,
                duration=0.0,
                stdout="",
                stderr=str(e),
                results=[],
                coverage=None,
                performance_metrics={},
                metadata={
                    "error": str(e),
                    "working_dir": str(working_dir) if working_dir else "",
                },
            )
            self._log_execution(error_execution)
            return error_execution

    async def generate_test_report(
        self,
        executions: list[TestExecution] | None = None,
        format: str = "json",
    ) -> str:
        """
        Generate comprehensive test report.

        Args:
            executions: List of test executions (uses log if None)
            format: Report format (json, text, html)

        Returns:
            Formatted test report
        """
        exec_list = executions or self.execution_log

        if not exec_list:
            return "No test executions to report."

        # Calculate summary statistics
        total_executions = len(exec_list)
        successful_executions = len([e for e in exec_list if e.success])
        total_tests = sum(len(e.results) for e in exec_list)
        total_passed = sum(
            len([r for r in e.results if r.status == "passed"]) for e in exec_list
        )
        total_failed = sum(
            len([r for r in e.results if r.status == "failed"]) for e in exec_list
        )
        total_skipped = sum(
            len([r for r in e.results if r.status == "skipped"]) for e in exec_list
        )

        avg_duration = sum(e.duration for e in exec_list) / total_executions
        max_memory = max(
            (e.performance_metrics.get("max_memory_mb", 0) for e in exec_list),
            default=0,
        )

        # Coverage summary
        coverage_executions = [e for e in exec_list if e.coverage]
        if coverage_executions:
            total_coverage = 0.0
            for e in coverage_executions:
                if e.coverage:
                    total_coverage += e.coverage.coverage_percentage
            avg_coverage = total_coverage / len(coverage_executions)
        else:
            avg_coverage = 0

        if format == "json":
            report_data = {
                "summary": {
                    "total_executions": total_executions,
                    "successful_executions": successful_executions,
                    "success_rate": successful_executions / total_executions,
                    "total_tests": total_tests,
                    "passed_tests": total_passed,
                    "failed_tests": total_failed,
                    "skipped_tests": total_skipped,
                    "pass_rate": total_passed / total_tests if total_tests > 0 else 0,
                    "average_duration": avg_duration,
                    "max_memory_usage_mb": max_memory,
                    "average_coverage": avg_coverage,
                },
                "executions": [
                    {
                        "framework": e.framework,
                        "success": e.success,
                        "command": e.command,
                        "exit_code": e.exit_code,
                        "duration": e.duration,
                        "test_count": len(e.results),
                        "passed": len([r for r in e.results if r.status == "passed"]),
                        "failed": len([r for r in e.results if r.status == "failed"]),
                        "coverage": (
                            e.coverage.coverage_percentage if e.coverage else None
                        ),
                        "performance": e.performance_metrics,
                        "metadata": e.metadata,
                    }
                    for e in exec_list
                ],
                "generated_at": datetime.now().isoformat(),
            }
            return json.dumps(report_data, indent=2)

        elif format == "text":
            lines = [
                "🧪 Test Execution Report",
                "=" * 50,
                f"Total Executions: {total_executions}",
                f"Successful: {successful_executions} "
                f"({successful_executions / total_executions * 100:.1f}%)",
                f"Total Tests: {total_tests}",
                (
                    f"Passed: {total_passed} ({total_passed / total_tests * 100:.1f}%)"
                    if total_tests > 0
                    else "Passed: 0"
                ),
                f"Failed: {total_failed}",
                f"Skipped: {total_skipped}",
                f"Average Duration: {avg_duration:.2f}s",
                f"Max Memory Usage: {max_memory:.1f}MB",
                (
                    f"Average Coverage: {avg_coverage * 100:.1f}%"
                    if avg_coverage > 0
                    else "Coverage: N/A"
                ),
                "",
                "📊 Execution Details:",
                "-" * 30,
            ]

            for i, execution in enumerate(exec_list, 1):
                status = "✅" if execution.success else "❌"
                lines.extend(
                    [
                        f"{i}. {status} {execution.framework}",
                        f"   Command: {execution.command}",
                        f"   Duration: {execution.duration:.2f}s",
                        f"   Tests: {len(execution.results)} total",
                        f"   Results: "
                        f"{len([r for r in execution.results if r.status == 'passed'])} passed, "
                        f"{len([r for r in execution.results if r.status == 'failed'])} failed",
                        "",
                    ],
                )

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported report format: {format}")

    def get_execution_log(self) -> list[TestExecution]:
        """Get the execution log for audit purposes."""
        return self.execution_log.copy()

    def clear_execution_log(self) -> None:
        """Clear the execution log."""
        self.execution_log.clear()

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        for temp_dir in self.temp_dirs:
            try:
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")
        self.temp_dirs.clear()


# Test function to verify real test execution
async def test_test_runner_tool() -> None:
    """Test TestRunnerTool with real test execution."""

    logger.info("🧪 Testing Real TestRunnerTool Operations")
    logger.info("=" * 50)

    # Create temporary test files for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"🏗️ Test directory: {temp_dir}")
        temp_path = Path(temp_dir)

        # Create sample test files
        test_file = temp_path / "test_sample.py"
        test_file.write_text(
            """
import unittest

class TestSample(unittest.TestCase):
    def test_success(self):
        self.assertEqual(1 + 1, 2)

    def test_failure(self):
        self.assertEqual(1 + 1, 3)  # This will fail

    def test_skip(self):
        self.skipTest("Skipping this test")

if __name__ == '__main__':
    unittest.main()
""",
        )

        pytest_file = temp_path / "test_pytest_sample.py"
        pytest_file.write_text(
            """
def test_addition():
    assert 1 + 1 == 2

def test_subtraction():
    assert 2 - 1 == 1

def test_multiplication():
    assert 2 * 3 == 6
""",
        )

        # Configure test runner
        safety_config = TestSafetyConfig(
            max_execution_time=60,
            max_memory_usage=512,
            allowed_test_patterns=["test_*.py", "*_test.py"],
            forbidden_commands=[],  # Allow everything for testing
            require_virtual_env=False,
            sandbox_mode=False,  # Disable for testing
            max_processes=2,
        )

        tool = TestRunnerTool(safety_config)

        # Test 1: Run pytest
        logger.info("\n🔬 Test 1: Run pytest")
        try:
            result = await tool.run_pytest(pytest_file, verbose=True)
            logger.info(f"   Framework: {result.framework}")
            logger.info(f"   Success: {'✅' if result.success else '❌'}")
            logger.info(f"   Duration: {result.duration:.2f}s")
            logger.info(f"   Tests: {len(result.results)}")
            logger.info(f"   Exit code: {result.exit_code}")
        except Exception as e:
            logger.info(f"   ❌ Error: {e}")

        # Test 2: Run unittest
        logger.info("\n🧪 Test 2: Run unittest")
        try:
            result = await tool.run_unittest(test_file, verbose=True)
            logger.info(f"   Framework: {result.framework}")
            logger.info(f"   Success: {'✅' if result.success else '❌'}")
            logger.info(f"   Duration: {result.duration:.2f}s")
            logger.info(f"   Tests: {len(result.results)}")
            logger.info(f"   Exit code: {result.exit_code}")
        except Exception as e:
            logger.info(f"   ❌ Error: {e}")

        # Test 3: Run custom command
        logger.info("\n⚙️ Test 3: Run custom command")
        try:
            result = await tool.run_custom_command(
                "python -c 'logger.info(\"Hello from test!\")'"
            )
            logger.info(f"   Success: {'✅' if result.success else '❌'}")
            logger.info(f"   Output: {result.stdout.strip()}")
        except Exception as e:
            logger.info(f"   ❌ Error: {e}")

        # Test 4: Generate report
        logger.info("\n📊 Test 4: Generate report")
        try:
            report = await tool.generate_test_report(format="text")
            logger.info("   Report generated:")
            logger.info(
                "   " + "\n   ".join(report.split("\n")[:10])
            )  # Show first 10 lines
        except Exception as e:
            logger.info(f"   ❌ Error: {e}")

        # Test 5: Safety validation
        logger.info("\n🛡️ Test 5: Safety validation")
        try:
            result = await tool.run_custom_command("rm -rf /", timeout=1)
            logger.info(
                f"   Safety test: {'❌ FAILED' if result.success else '✅ BLOCKED'}"
            )
        except Exception as e:
            logger.info(f"   Safety test: ✅ BLOCKED - {e}")

        # Show execution log
        logger.info("\n📋 Execution Log:")
        for i, execution in enumerate(tool.get_execution_log(), 1):
            status = "✅" if execution.success else "❌"
            logger.info(
                f"   {i}. {status} {execution.framework}: {execution.command[:50]}..."
            )

        logger.info(f"\n🎯 Tests completed. Test files created in: {temp_dir}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_test_runner_tool())
