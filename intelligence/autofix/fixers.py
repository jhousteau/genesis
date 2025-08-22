"""
Automated fixers for Stage 1 of the autofix system.

These fixers handle common issues that can be resolved automatically
without LLM assistance. Based on ADR-004.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from solve_core.config import get_config

from .models import FixResult


class BaseFixer(ABC):
    """Base class for all automated fixers"""

    @abstractmethod
    async def fix(self, paths: list[str]) -> FixResult:
        """Apply fixes to the given paths"""
        pass


class TrailingWhitespaceFixer(BaseFixer):
    """Removes trailing whitespace from files"""

    async def fix(self, paths: list[str]) -> FixResult:
        files_changed = []
        errors_fixed = 0

        for path_str in paths:
            path = Path(path_str)
            if not path.exists() or not path.is_file():
                continue

            if path.suffix not in [
                ".py",
                ".md",
                ".mdc",
                ".txt",
                ".json",
                ".yaml",
                ".yml",
            ]:
                continue

            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()

                original_content = content
                lines = content.splitlines(keepends=True)
                fixed_lines = []

                for line in lines:
                    stripped = (
                        line.rstrip() + "\n" if line.endswith("\n") else line.rstrip()
                    )
                    if stripped != line:
                        errors_fixed += 1
                    fixed_lines.append(stripped)

                new_content = "".join(fixed_lines)
                if new_content != original_content:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    files_changed.append(str(path))

            except Exception as e:
                logging.error(f"Error processing file {path_str}: {e}")
                continue

        return FixResult(
            success=True,
            files_changed=files_changed,
            errors_fixed=errors_fixed,
            time_taken=0,
            details={"fixer": "trailing_whitespace"},
        )


class EndOfFileFixer(BaseFixer):
    """Ensures files end with a single newline"""

    async def fix(self, paths: list[str]) -> FixResult:
        files_changed = []
        errors_fixed = 0

        for path_str in paths:
            path = Path(path_str)
            if not path.exists() or not path.is_file():
                continue

            if path.suffix not in [
                ".py",
                ".md",
                ".mdc",
                ".txt",
                ".json",
                ".yaml",
                ".yml",
            ]:
                continue

            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()

                if content and not content.endswith("\n"):
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content + "\n")
                    files_changed.append(str(path))
                    errors_fixed += 1
                elif content.endswith("\n\n"):
                    # Remove multiple trailing newlines
                    fixed_content = content.rstrip("\n") + "\n"
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)
                    files_changed.append(str(path))
                    errors_fixed += 1

            except Exception as e:
                logging.error(f"Error processing file {path_str}: {e}")
                continue

        return FixResult(
            success=True,
            files_changed=files_changed,
            errors_fixed=errors_fixed,
            time_taken=0,
            details={"fixer": "end_of_file"},
        )


class RuffAutoFixer(BaseFixer):
    """Runs ruff --fix for automated code fixes"""

    async def fix(self, paths: list[str]) -> FixResult:
        try:
            cmd = ["ruff", "check", "--fix", "--exit-zero"]

            # Add --unsafe-fixes if configured

            config = get_config()
            if config.autofix and config.autofix.enable_ruff_unsafe_fixes:
                cmd.append("--unsafe-fixes")

            cmd.extend(paths)

            # Use asyncio subprocess for async execution
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
                result_stdout = stdout.decode() if stdout else ""
                result_stderr = stderr.decode() if stderr else ""
                returncode = proc.returncode
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise

            # Parse output to count fixes
            errors_fixed = 0
            files_changed = []

            if result_stdout:
                # Ruff outputs like "Found 1 error (1 fixed, 0 remaining)."
                for line in result_stdout.splitlines():
                    if "fixed" in line.lower() and "0 remaining" not in line:
                        # Extract number of fixes from pattern like "(X fixed"
                        import re

                        match = re.search(r"(\d+)\s+fixed", line)
                        if match:
                            errors_fixed = int(match.group(1))

                    # Check if specific files are mentioned as being fixed
                    for path in paths:
                        if (
                            path in line
                            and "fixed" in line.lower()
                            and path not in files_changed
                        ):
                            files_changed.append(path)

                # If we have fixes but no specific files mentioned, ruff fixed something
                # but didn't tell us which files. In this case, we need to be conservative
                # and not report any files as changed unless we're sure.

            return FixResult(
                success=returncode == 0,
                files_changed=files_changed,
                errors_fixed=errors_fixed,
                time_taken=0,
                details={
                    "fixer": "ruff_auto",
                    "stdout": result_stdout,
                    "stderr": result_stderr,
                },
            )

        except asyncio.TimeoutError:
            logging.error("Ruff timeout")
            return FixResult(
                success=False,
                files_changed=[],
                errors_fixed=0,
                time_taken=0,
                details={"error": "Ruff timeout"},
            )
        except FileNotFoundError:
            logging.error("Ruff not found")
            return FixResult(
                success=False,
                files_changed=[],
                errors_fixed=0,
                time_taken=0,
                details={"error": "Ruff not found"},
            )


class RuffFormatter(BaseFixer):
    """Runs ruff format for code formatting"""

    async def fix(self, paths: list[str]) -> FixResult:
        try:
            cmd = ["ruff", "format"] + paths

            # Use asyncio subprocess for async execution
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
                returncode = proc.returncode
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise

            # Parse ruff format output to determine what changed
            files_changed = []
            stdout_str = stdout.decode() if stdout else ""

            # Ruff format outputs lines like "1 file reformatted" or "1 file left unchanged"
            if "reformatted" in stdout_str:
                # If files were reformatted, we need to figure out which ones
                # For now, we'll check timestamps or just trust that ruff modified them
                for path in paths:
                    if Path(path).suffix == ".py":
                        files_changed.append(path)
            # If output says "left unchanged", files_changed remains empty

            return FixResult(
                success=returncode == 0,
                files_changed=files_changed,
                errors_fixed=len(files_changed),
                time_taken=0,
                details={
                    "fixer": "ruff_format",
                    "stdout": stdout.decode() if "stdout" in locals() else "",
                    "stderr": stderr.decode() if "stderr" in locals() else "",
                },
            )

        except asyncio.TimeoutError:
            logging.error("Ruff format timeout")
            return FixResult(
                success=False,
                files_changed=[],
                errors_fixed=0,
                time_taken=0,
                details={"error": "Ruff format timeout"},
            )
        except FileNotFoundError:
            logging.error("Ruff not found")
            return FixResult(
                success=False,
                files_changed=[],
                errors_fixed=0,
                time_taken=0,
                details={"error": "Ruff not found"},
            )
