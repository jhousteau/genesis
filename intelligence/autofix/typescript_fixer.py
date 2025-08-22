"""TypeScript linting fixer for Stage 1 of the autofix system."""

import asyncio
import logging
from pathlib import Path

from .fixers import BaseFixer
from .models import FixResult


class TypeScriptLintFixer(BaseFixer):
    """Runs ESLint with --fix for TypeScript/JavaScript files"""

    async def fix(self, paths: list[str]) -> FixResult:
        # Filter for TypeScript/JavaScript files
        ts_js_paths = []
        for path_str in paths:
            path = Path(path_str)
            if (
                path.exists()
                and path.is_file()
                and path.suffix in [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]
            ):
                ts_js_paths.append(path_str)

        if not ts_js_paths:
            return FixResult(
                success=True,
                files_changed=[],
                errors_fixed=0,
                time_taken=0,
                details={
                    "fixer": "typescript_lint",
                    "message": "No TypeScript/JavaScript files to fix",
                },
            )

        try:
            # First, try to find eslint in common locations
            eslint_cmd = None
            possible_commands = [
                ["npx", "eslint"],  # Use npx (most common)
                ["eslint"],  # Global install
                ["./node_modules/.bin/eslint"],  # Local install
            ]

            for cmd in possible_commands:
                try:
                    # Test if command exists
                    test_proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        "--version",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await test_proc.wait()
                    if test_proc.returncode == 0:
                        eslint_cmd = cmd
                        break
                except (FileNotFoundError, OSError):
                    continue

            if not eslint_cmd:
                logging.info("ESLint not found, skipping TypeScript linting")
                return FixResult(
                    success=True,
                    files_changed=[],
                    errors_fixed=0,
                    time_taken=0,
                    details={"fixer": "typescript_lint", "message": "ESLint not found"},
                )

            # Run ESLint with --fix
            cmd = eslint_cmd + ["--fix", "--quiet"] + ts_js_paths

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=(
                    Path(ts_js_paths[0]).parent if ts_js_paths else None
                ),  # Run from project directory
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
                returncode = proc.returncode
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                logging.error("ESLint timed out after 120 seconds")
                return FixResult(
                    success=False,
                    files_changed=[],
                    errors_fixed=0,
                    time_taken=0,
                    details={"error": "ESLint timed out"},
                )

            # ESLint returns 0 if no errors (warnings ok), 1 if errors found (even after fixing)
            # We consider it successful if it ran without crashing (returncode 0 or 1)
            success = returncode in [0, 1]

            # Check which files were actually modified by comparing timestamps
            # or parsing ESLint output (ESLint doesn't clearly report which files it fixed)
            files_changed = []
            if success:
                # For simplicity, assume all files passed were potentially changed
                # In practice, you might want to check file modification times
                files_changed = ts_js_paths

            return FixResult(
                success=success,
                files_changed=files_changed,
                errors_fixed=len(files_changed),
                time_taken=0,
                details={
                    "fixer": "typescript_lint",
                    "command": " ".join(cmd),
                    "returncode": returncode,
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                },
            )

        except Exception as e:
            logging.error(f"TypeScript lint fixer error: {e}")
            return FixResult(
                success=False,
                files_changed=[],
                errors_fixed=0,
                time_taken=0,
                details={"error": str(e)},
            )
