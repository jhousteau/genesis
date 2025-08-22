"""
Validators for Stage 2 of the autofix system.

These validators identify remaining issues after automated fixes.
Based on ADR-004: Comprehensive Autofix/Autocommit System Architecture
"""

import asyncio
import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from .models import ValidationResult


class BaseValidator(ABC):
    """Base class for all validators"""

    @abstractmethod
    async def validate(self, paths: list[str]) -> ValidationResult:
        """Validate the given paths and return results"""
        pass


class RuffChecker(BaseValidator):
    """Runs ruff check in no-fix mode to identify issues"""

    async def validate(self, paths: list[str]) -> ValidationResult:
        try:
            cmd = ["ruff", "check", "--no-fix", "--output-format=json"] + paths
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            errors = []
            warnings = []

            if stdout:
                try:
                    ruff_output = json.loads(stdout.decode())
                    for item in ruff_output:
                        if not item:  # Skip None items
                            continue
                        code = item.get("code", "") if item else ""
                        error_data = {
                            "file": item.get("filename", ""),
                            "line": item.get("location", {}).get("row", 0),
                            "column": item.get("location", {}).get("column", 0),
                            "code": code,
                            "message": item.get("message", ""),
                            "severity": (
                                "error" if code and code.startswith("E") else "warning"
                            ),
                            "tool": "ruff",
                        }

                        if error_data["severity"] == "error":
                            errors.append(error_data)
                        else:
                            warnings.append(error_data)

                except json.JSONDecodeError:
                    # Fallback to plain text parsing
                    for line in stdout.decode().splitlines():
                        if ":" in line:
                            errors.append(
                                {"message": line, "tool": "ruff", "severity": "error"}
                            )

            return ValidationResult(
                success=result.returncode == 0,
                errors=errors,
                warnings=warnings,
                time_taken=0,
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                success=False,
                errors=[{"error": "Ruff timeout", "tool": "ruff"}],
                warnings=[],
                time_taken=0,
            )
        except FileNotFoundError:
            return ValidationResult(
                success=False,
                errors=[{"error": "Ruff not found", "tool": "ruff"}],
                warnings=[],
                time_taken=0,
            )


class MypyChecker(BaseValidator):
    """Runs mypy for type checking"""

    async def validate(self, paths: list[str]) -> ValidationResult:
        try:
            # First try with JSON output if available
            cmd_json = [
                "mypy",
                "--output=json",
                "--show-error-codes",
                "--no-error-summary",
            ] + paths
            result = await asyncio.create_subprocess_exec(
                *cmd_json,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            errors = []
            warnings = []

            # Try to parse as JSON first
            try:
                import json

                for line in stdout.decode().splitlines():
                    if line.strip():
                        error_json = json.loads(line)
                        error_data = {
                            "file": error_json.get("file", ""),
                            "line": error_json.get("line", 0),
                            "column": error_json.get("column", 0),
                            "code": error_json.get("code", ""),
                            "message": error_json.get("message", ""),
                            "severity": error_json.get("severity", "error"),
                            "tool": "mypy",
                        }
                        if error_data["severity"] == "error":
                            errors.append(error_data)
                        else:
                            warnings.append(error_data)
            except (json.JSONDecodeError, KeyError):
                # Fall back to text parsing if JSON fails
                # Re-run without JSON flag
                cmd = ["mypy", "--show-error-codes", "--no-error-summary"] + paths
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await result.communicate()

                if stdout:
                    for line in stdout.decode().splitlines():
                        if ": error:" in line:
                            # Better regex parsing for mypy output
                            # Format: file.py:line: error: message [error-code]
                            import re

                            match = re.match(
                                r"(.*?):(\d+):(?:(\d+):)?\s*error:\s*(.*?)\s*\[(.+?)\]",
                                line,
                            )
                            if match:
                                error_data = {
                                    "file": match.group(1),
                                    "line": int(match.group(2)),
                                    "column": (
                                        int(match.group(3)) if match.group(3) else 0
                                    ),
                                    "message": match.group(4),
                                    "code": match.group(5),
                                    "tool": "mypy",
                                    "severity": "error",
                                }
                                errors.append(error_data)
                        elif ": warning:" in line or ": note:" in line:
                            warnings.append(
                                {
                                    "message": line,
                                    "tool": "mypy",
                                    "severity": "warning",
                                },
                            )

            return ValidationResult(
                success=result.returncode == 0,
                errors=errors,
                warnings=warnings,
                time_taken=0,
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                success=False,
                errors=[{"error": "Mypy timeout", "tool": "mypy"}],
                warnings=[],
                time_taken=0,
            )
        except FileNotFoundError:
            return ValidationResult(
                success=False,
                errors=[{"error": "Mypy not found", "tool": "mypy"}],
                warnings=[],
                time_taken=0,
            )


class SecurityChecker(BaseValidator):
    """Runs security validation using bandit"""

    async def validate(self, paths: list[str]) -> ValidationResult:
        try:
            cmd = ["bandit", "-f", "json", "-r"] + paths
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            errors = []
            warnings = []

            if stdout:
                try:
                    bandit_output = json.loads(stdout.decode())
                    for item in bandit_output.get("results", []):
                        severity = item.get("issue_severity", "MEDIUM")
                        error_data = {
                            "file": item.get("filename", ""),
                            "line": item.get("line_number", 0),
                            "message": item.get("issue_text", ""),
                            "code": item.get("test_id", ""),
                            "tool": "bandit",
                            "severity": "error" if severity == "HIGH" else "warning",
                        }

                        if error_data["severity"] == "error":
                            errors.append(error_data)
                        else:
                            warnings.append(error_data)

                except json.JSONDecodeError:
                    pass

            return ValidationResult(
                success=result.returncode == 0,
                errors=errors,
                warnings=warnings,
                time_taken=0,
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                success=False,
                errors=[{"error": "Bandit timeout", "tool": "bandit"}],
                warnings=[],
                time_taken=0,
            )
        except FileNotFoundError:
            return ValidationResult(
                success=False,
                errors=[{"error": "Bandit not found", "tool": "bandit"}],
                warnings=[],
                time_taken=0,
            )


class PytestRunner(BaseValidator):
    """Runs pytest for test validation"""

    async def validate(self, paths: list[str]) -> ValidationResult:
        try:
            # Check if pytest is configured in the project
            if not any(Path(p).name.startswith("test_") for p in paths):
                return ValidationResult(
                    success=True, errors=[], warnings=[], time_taken=0
                )

            # First try with JSON report if available
            json_report_file = Path(".pytest_report.json")
            cmd_json = [
                "pytest",
                "--json-report",
                f"--json-report-file={json_report_file}",
                "--tb=short",
                "-v",
            ] + paths
            result = await asyncio.create_subprocess_exec(
                *cmd_json,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            errors = []
            warnings = []

            # Try to parse JSON report
            if json_report_file.exists():
                try:
                    import json

                    with open(json_report_file) as f:
                        report = json.load(f)

                    # Extract test failures from JSON report
                    for test in report.get("tests", []):
                        if test.get("outcome") == "failed":
                            # Extract file and line from nodeid if possible
                            nodeid = test.get("nodeid", "")
                            file_path = ""
                            line_no = 0

                            # Parse nodeid like "tests/test_file.py::TestClass::test_method[param]"
                            if "::" in nodeid:
                                file_path = nodeid.split("::")[0]

                            error_data = {
                                "file": file_path,
                                "line": line_no,  # Would need to parse from call stack
                                "code": "test-failed",
                                "message": test.get("call", {}).get(
                                    "longrepr", "Test failed"
                                ),
                                "tool": "pytest",
                                "severity": "error",
                            }
                            errors.append(error_data)
                        elif test.get("outcome") == "error":
                            error_data = {
                                "file": (
                                    test.get("nodeid", "").split("::")[0]
                                    if "::" in test.get("nodeid", "")
                                    else ""
                                ),
                                "line": 0,
                                "code": "test-error",
                                "message": test.get("setup", {}).get(
                                    "longrepr", "Test error"
                                ),
                                "tool": "pytest",
                                "severity": "error",
                            }
                            errors.append(error_data)

                    # Clean up JSON report file
                    json_report_file.unlink(missing_ok=True)

                except (json.JSONDecodeError, KeyError, FileNotFoundError):
                    # Fall back to text parsing
                    pass

            # If no JSON report or parsing failed, use text parsing
            if not errors and stdout:
                for line in stdout.decode().splitlines():
                    if "FAILED" in line:
                        # Try to extract more info from FAILED lines
                        # Format: FAILED tests/test_file.py::test_function - AssertionError: message
                        import re

                        match = re.match(r"FAILED\s+(.*?)::(.*?)\s+-\s+(.*)", line)
                        if match:
                            error_data = {
                                "file": match.group(1),
                                "line": 0,  # Can't get line from this format
                                "code": "test-failed",
                                "message": f"{match.group(2)}: {match.group(3)}",
                                "tool": "pytest",
                                "severity": "error",
                            }
                            errors.append(error_data)
                        else:
                            errors.append(
                                {"message": line, "tool": "pytest", "severity": "error"}
                            )
                    elif "WARNING" in line:
                        warnings.append(
                            {"message": line, "tool": "pytest", "severity": "warning"}
                        )

            return ValidationResult(
                success=result.returncode == 0,
                errors=errors,
                warnings=warnings,
                time_taken=0,
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                success=False,
                errors=[{"error": "Pytest timeout", "tool": "pytest"}],
                warnings=[],
                time_taken=0,
            )
        except FileNotFoundError:
            return ValidationResult(
                success=False,
                errors=[{"error": "Pytest not found", "tool": "pytest"}],
                warnings=[],
                time_taken=0,
            )
