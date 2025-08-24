"""
Autonomous commit debugging system for SOLVE orchestrator.

This module handles automatic retry of failed commits by parsing pre-commit
hook errors and using Claude to debug and fix them safely.
"""

import logging
import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic
from anthropic.types import TextBlock
from solve.config import SOLVEConfig, get_api_key, get_config

# Note: sdk_interface is archived - removed dependency

logger = logging.getLogger(__name__)


@dataclass
class ErrorContext:
    """Structured representation of a pre-commit error."""

    hook: str
    file: str | None
    line: int | None
    column: int | None
    code: str | None
    message: str
    raw_line: str


@dataclass
class DebugMetrics:
    """Tracks metrics for the debugging session."""

    initial_error_count: int = 0
    current_error_count: int = 0
    errors_fixed: int = 0
    new_errors_introduced: int = 0
    iterations: int = 0
    files_processed: set[str] = field(default_factory=set)
    error_history: list[dict[str, Any]] = field(default_factory=list)

    def add_iteration(self, fixed: int, remaining: int, new: int) -> None:
        """Record metrics for an iteration."""
        self.iterations += 1
        self.errors_fixed += fixed
        self.current_error_count = remaining
        self.new_errors_introduced += new
        self.error_history.append(
            {
                "iteration": self.iterations,
                "fixed": fixed,
                "remaining": remaining,
                "new": new,
                "net_progress": self.initial_error_count - remaining,
            },
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the debugging session."""
        return {
            "initial_errors": self.initial_error_count,
            "final_errors": self.current_error_count,
            "total_fixed": self.errors_fixed,
            "new_introduced": self.new_errors_introduced,
            "net_improvement": self.initial_error_count - self.current_error_count,
            "iterations": self.iterations,
            "files_touched": len(self.files_processed),
            "success": self.current_error_count == 0,
        }


class BackupManager:
    """Manages file backups for safe rollback."""

    def __init__(self) -> None:
        self.backup_dir = Path(".solve/.backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.current_session = datetime.now().isoformat().replace(":", "-")

    def backup_file(self, file_path: Path) -> Path:
        """Create timestamped backup of file."""
        backup_path = self.backup_dir / self.current_session / file_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        logger.debug(f"Backed up {file_path} to {backup_path}")
        return backup_path

    def restore_file(self, file_path: Path) -> bool:
        """Restore file from backup."""
        backup_path = self.backup_dir / self.current_session / file_path
        if backup_path.exists():
            shutil.copy2(backup_path, file_path)
            logger.info(f"Restored {file_path} from backup")
            return True
        return False

    def restore_all(self) -> int:
        """Restore all files from current session."""
        count = 0
        session_dir = self.backup_dir / self.current_session
        if session_dir.exists():
            for backup_file in session_dir.rglob("*"):
                if backup_file.is_file():
                    # Reconstruct original path
                    relative_path = backup_file.relative_to(session_dir)
                    original_path = Path(relative_path)
                    if original_path.exists():
                        shutil.copy2(backup_file, original_path)
                        count += 1
                        logger.info(f"Restored {original_path}")
        return count


class PreCommitErrorParser:
    """Parses pre-commit hook output to extract actionable errors."""

    ERROR_PATTERNS: dict[str, dict[str, str | dict[str, int]]] = {
        "ruff": {
            "pattern": r"(.*?):(\d+):(\d+): ([A-Z]+\d+) (.+)",
            "groups": {"file": 1, "line": 2, "column": 3, "code": 4, "message": 5},
        },
        "mypy": {
            "pattern": r"(.*?):(\d+): error: (.+) \[(.+)\]",
            "groups": {"file": 1, "line": 2, "message": 3, "code": 4},
        },
        "black": {"pattern": r"would reformat (.*)", "groups": {"file": 1}},
        "trailing-whitespace": {"pattern": r"Fixing (.*)", "groups": {"file": 1}},
        "end-of-file-fixer": {"pattern": r"Fixing (.*)", "groups": {"file": 1}},
        "pytest": {
            "pattern": r"FAILED (.*?) - (.+)",
            "groups": {"test": 1, "message": 2},
        },
    }

    def parse_output(self, output: str) -> list[ErrorContext]:
        """Parse pre-commit output into structured error contexts."""
        errors = []
        current_hook = None
        files_modified = set()

        for line in output.split("\n"):
            # Detect which hook is running
            if "- hook id:" in line:
                current_hook = line.split("- hook id:")[1].strip()
                logger.debug(f"Detected hook: {current_hook}")

            # Check if files were modified by hook
            if "- files were modified by this hook" in line and current_hook:
                files_modified.add(current_hook)

            # Parse errors based on current hook
            if current_hook and current_hook in self.ERROR_PATTERNS:
                pattern_info = self.ERROR_PATTERNS[current_hook]
                pattern = str(pattern_info["pattern"])
                match = re.match(pattern, line.strip())
                if match:
                    groups = pattern_info["groups"]
                    assert isinstance(groups, dict)
                    # Extract group indices safely
                    file_idx = groups.get("file")
                    line_idx = groups.get("line")
                    column_idx = groups.get("column")
                    code_idx = groups.get("code")
                    message_idx = groups.get("message")

                    error = ErrorContext(
                        hook=current_hook or "unknown",
                        file=match.group(file_idx) if file_idx is not None else None,
                        line=(
                            int(match.group(line_idx)) if line_idx is not None else None
                        ),
                        column=(
                            int(match.group(column_idx))
                            if column_idx is not None
                            else None
                        ),
                        code=match.group(code_idx) if code_idx is not None else None,
                        message=(
                            match.group(message_idx)
                            if message_idx is not None
                            else line.strip()
                        ),
                        raw_line=line,
                    )
                    errors.append(error)
                    logger.debug(f"Parsed error: {error}")

        # Handle hooks that just modified files
        for hook in files_modified:
            if not any(e.hook == hook for e in errors):
                errors.append(
                    ErrorContext(
                        hook=hook,
                        file=None,
                        line=None,
                        column=None,
                        code="files-modified",
                        message=f"{hook} modified files",
                        raw_line=f"{hook} modified files",
                    ),
                )

        return errors


class FixStrategy(ABC):
    """Base class for fix strategies."""

    @abstractmethod
    async def can_fix(self, error: ErrorContext) -> bool:
        """Check if this strategy can fix the error."""
        pass

    @abstractmethod
    async def generate_fix_prompt(self, error: ErrorContext) -> str:
        """Generate Claude prompt for fixing this error."""
        pass

    async def get_file_context(
        self, file_path: str, line_num: int | None = None
    ) -> str:
        """Get file content with optional line context."""
        try:
            with open(file_path) as f:
                lines = f.readlines()

            if line_num and 0 < line_num <= len(lines):
                # Get surrounding context
                start = max(0, line_num - 5)
                end = min(len(lines), line_num + 5)
                context_lines = []
                for i in range(start, end):
                    prefix = ">>>" if i == line_num - 1 else "   "
                    context_lines.append(f"{prefix} {i + 1}: {lines[i].rstrip()}")
                return "\n".join(context_lines)
            else:
                return "".join(lines)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return ""


class RuffFixStrategy(FixStrategy):
    """Handles Ruff linting errors."""

    # These are safe to auto-fix
    SAFE_FIXES = {
        "UP007": "Use X | Y for type annotations",
        "UP035": "Use typing.Self instead of string literal type",
        "UP040": "Use typing.TypeAlias for type aliases",
        "SIM102": "Use a single if statement",
        "SIM114": "Combine if branches using logical or",
        "SIM118": "Use key in dict instead of key in dict.keys()",
        "T201": "Remove print statements",
        "T203": "Remove pprint statements",
        "S314": "Use defusedxml for XML parsing",
        "E999": "Syntax error",
        "F401": "Remove unused import",
        "F841": "Remove unused variable",
        "I001": "Sort imports",
        "I002": "Add missing imports",
        "B008": "Do not perform function calls in argument defaults",
        "B904": "Use raise ... from error",
        "C901": "Function is too complex",
        "RUF001": "String contains ambiguous unicode character",
        "RUF002": "Docstring contains ambiguous unicode character",
        "RUF003": "Comment contains ambiguous unicode character",
        "RUF100": "Remove unused noqa directive",
    }

    async def can_fix(self, error: ErrorContext) -> bool:
        # Always try to fix ruff errors, even if not in SAFE_FIXES list
        return error.hook == "ruff"

    async def generate_fix_prompt(self, error: ErrorContext) -> str:
        if not error.file:
            return ""

        context = await self.get_file_context(error.file, error.line)

        return f"""<task>Fix this specific Ruff error</task>

<error>
File: {error.file}
Line: {error.line}
Column: {error.column}
Error Code: {error.code}
Message: {error.message}
</error>

<instructions>
- Only fix the specific error mentioned
- Do not change functionality
- Maintain existing code style
- Use minimal changes
- For {error.code}: {self.SAFE_FIXES.get(error.code or "", error.message)}
- Return ONLY the corrected line(s) of code
- Do not include explanations, markdown formatting, or anything else
- If multiple lines need to be fixed, return them exactly as they should appear in the file
</instructions>

<file_context>
{context}
</file_context>

IMPORTANT: Your response should contain ONLY the fixed Python code line(s),
no explanations or formatting."""


class MypyFixStrategy(FixStrategy):
    """Handles MyPy type checking errors."""

    async def can_fix(self, error: ErrorContext) -> bool:
        return bool(error.hook == "mypy" and error.file and error.line)

    async def generate_fix_prompt(self, error: ErrorContext) -> str:
        if not error.file:
            return ""

        context = await self.get_file_context(error.file, error.line)

        return f"""<task>Fix this MyPy type error</task>

<error>
File: {error.file}
Line: {error.line}
Error: {error.message}
Type: {error.code}
</error>

<instructions>
- Add proper type annotations to fix the error
- Do not change functionality
- Use modern Python type hints (Python 3.10+)
- Be specific with types
- Import any necessary type hints at the top of the response if needed
- Return ONLY the corrected line(s) of code
- Do not include explanations, markdown formatting, or anything else
</instructions>

<file_context>
{context}
</file_context>

IMPORTANT: Your response should contain ONLY the fixed Python code line(s), no
explanations or formatting."""


class AutoFixOnlyStrategy(FixStrategy):
    """Handles hooks that auto-fix themselves (trailing whitespace, etc)."""

    AUTO_FIX_HOOKS = {
        "trailing-whitespace",
        "end-of-file-fixer",
        "black",
        "ruff-format",
    }

    async def can_fix(self, error: ErrorContext) -> bool:
        return error.hook in self.AUTO_FIX_HOOKS and error.code == "files-modified"

    async def generate_fix_prompt(self, error: ErrorContext) -> str:
        # These hooks fix themselves, we just need to re-add the files
        return ""


class SafetyChecks:
    """Implements safety checks for autonomous fixing."""

    @staticmethod
    async def validate_fix_scope(
        original: str, fixed: str, error_lines: list[int]
    ) -> bool:
        """Ensure fix only touches relevant lines."""
        original_lines = original.split("\n")
        fixed_lines = fixed.split("\n")

        if len(original_lines) != len(fixed_lines):
            # Line count changed, need more careful validation
            return True  # For now, allow it

        # Check that only expected lines changed
        changed_lines = []
        for i, (orig, fix) in enumerate(zip(original_lines, fixed_lines, strict=False)):
            if orig != fix:
                changed_lines.append(i + 1)

        # Allow changes within 3 lines of errors
        allowed_lines: set[int] = set()
        for line in error_lines:
            allowed_lines.update(range(max(1, line - 3), line + 4))

        unexpected_changes = set(changed_lines) - allowed_lines
        if unexpected_changes:
            logger.warning(f"Fix touched unexpected lines: {unexpected_changes}")
            return False

        return True

    @staticmethod
    async def syntax_check(file_path: Path) -> bool:
        """Verify Python syntax is still valid."""
        if file_path.suffix != ".py":
            return True  # Skip non-Python files

        try:
            with open(file_path) as f:
                compile(f.read(), str(file_path), "exec")
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return False


class ErrorComplexityAnalyzer:
    """Analyzes error complexity to determine appropriate LLM model."""

    # Simple errors that can be handled by Haiku
    SIMPLE_ERROR_CODES = {
        # Basic linting
        "F401",
        "F841",
        "I001",
        "I002",  # Unused imports/variables
        "E999",  # Syntax errors
        "T201",
        "T203",  # Print statements
        # Simple formatting
        "UP007",
        "UP035",
        "UP040",  # Type annotation updates
        "SIM102",
        "SIM114",
        "SIM118",  # Simple refactoring
        # Basic rules
        "B008",
        "B904",  # Basic best practices
        "RUF100",  # Unused noqa
    }

    # Complex errors requiring Sonnet
    COMPLEX_ERROR_CODES = {
        "C901",  # Function complexity
        "mypy",  # Type checking errors (hook name)
        "S314",  # Security issues
        "RUF001",
        "RUF002",
        "RUF003",  # Unicode issues
    }

    def get_model_for_error(self, error: ErrorContext) -> str:
        """Determine which model to use based on error complexity.

        Returns:
            "haiku" for simple errors, "sonnet" for complex errors
        """
        # Check if it's a mypy error (always complex)
        if error.hook == "mypy":
            return "sonnet"

        # Check error code
        if error.code in self.SIMPLE_ERROR_CODES:
            return "haiku"
        elif error.code in self.COMPLEX_ERROR_CODES:
            return "sonnet"

        # Default to haiku for unknown errors
        return "haiku"

    def get_model_for_batch(self, errors: list[ErrorContext]) -> str:
        """Determine model for a batch of errors.

        Uses the most complex error to determine model.
        """
        for error in errors:
            if self.get_model_for_error(error) == "sonnet":
                return "sonnet"
        return "haiku"


class AutoDebugger:
    """Handles autonomous commit debugging with pre-commit hook error resolution."""

    def __init__(self, max_retries: int = 5):
        # Note: sdk_interface parameter removed - no longer needed
        self.max_retries = max_retries
        self.backup_manager: BackupManager = BackupManager()
        self.error_parser = PreCommitErrorParser()
        self.safety_checks = SafetyChecks()
        self.complexity_analyzer = ErrorComplexityAnalyzer()
        self.metrics = DebugMetrics()

        # Initialize Anthropic API client for text generation
        # Use configuration system for API key
        api_key = get_api_key()
        self.anthropic_client = (
            anthropic.Anthropic(api_key=api_key) if api_key else None
        )

        # Register fix strategies
        self.strategies = [
            AutoFixOnlyStrategy(),
            RuffFixStrategy(),
            MypyFixStrategy(),
        ]

    async def debug_commit_errors(self, error_output: str) -> bool:
        """Parse and debug pre-commit errors."""
        errors = self.error_parser.parse_output(error_output)

        if not errors:
            logger.warning("No errors could be parsed from output")
            return False

        # Initialize metrics
        self.metrics.initial_error_count = len(errors)
        self.metrics.current_error_count = len(errors)

        logger.info(f"📊 Initial error count: {len(errors)} errors to fix")

        # Group errors by file
        errors_by_file = defaultdict(list)
        auto_fix_hooks = set()

        for error in errors:
            if error.code == "files-modified":
                auto_fix_hooks.add(error.hook)
            elif error.file:
                errors_by_file[error.file].append(error)
                self.metrics.files_processed.add(error.file)

        # Handle auto-fix hooks first (they already fixed themselves)
        if auto_fix_hooks:
            logger.info(f"Auto-fix hooks ran: {auto_fix_hooks}")
            # Just need to stage the changes
            return True

        # First, run all auto-fixers to handle simple issues
        try:
            from solve.autofix.models import AutofixConfig
            from solve.autofix.runner import AutoFixerRunner

            logger.info("Running auto-fixers to handle simple issues first...")
            logger.info(
                f"Initial error count: {len(errors)} errors across {len(errors_by_file)} files",
            )

            autofix_config = AutofixConfig()
            runner = AutoFixerRunner(autofix_config)
            fix_result_obj = await runner.run_all_fixers([])

            # Convert FixResult to dict format expected by existing code
            fix_result = {
                "enabled": autofix_config.enable_auto_fixers,
                "total_changes": len(fix_result_obj.files_changed),
                "iterations": fix_result_obj.details.get("iterations", 0),
                "all_fixed": fix_result_obj.success and fix_result_obj.errors_fixed > 0,
            }

            if fix_result["enabled"] and fix_result["total_changes"] > 0:
                logger.info(
                    f"Auto-fixers made {fix_result['total_changes']} changes "
                    f"in {fix_result['iterations']} iteration(s)",
                )

                # If all issues were fixed by auto-fixers, we're done
                if fix_result["all_fixed"]:
                    # Re-run pre-commit to check if everything is clean now
                    # Safe: Fixed command with no user input
                    check_result = subprocess.run(  # noqa: S603
                        [
                            "/usr/bin/env",
                            "pre-commit",
                            "run",
                            "--config",
                            ".solve/config/pre-commit-validate.yaml",
                            "--all-files",
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if check_result.returncode == 0:
                        logger.info(
                            "✅ All issues resolved by auto-fixers! No LLM debugging needed.",
                        )
                        return True
                    else:
                        logger.info(
                            "Auto-fixers applied, but LLM debugging still needed"
                        )
                        # Re-parse the new errors
                        errors = self.error_parser.parse_output(
                            check_result.stdout + check_result.stderr,
                        )
                        logger.info(f"Remaining errors after auto-fix: {len(errors)}")
        except Exception as e:
            logger.warning(f"Could not run auto-fixers: {e}")

        # Fix file errors using LLM debugging with metrics tracking
        logger.info(
            f"Starting LLM debugging for {len(errors_by_file)} files with remaining errors"
        )

        # Track errors we've seen to detect loops
        error_history = []
        stuck_iterations = 0
        config: SOLVEConfig = get_config()
        max_stuck_iterations = (
            config.debugging.max_debug_iterations if config.debugging else 10
        )
        error_count_history = []
        files_modified_count: dict[str, int] = defaultdict(int)

        # Main debugging loop with metrics tracking
        for iteration in range(self.max_retries):
            # Count current errors before this iteration
            current_total, error_breakdown = await self._count_all_errors()

            if current_total == 0:
                logger.info("✅ All errors fixed! No more debugging needed.")
                self.metrics.current_error_count = 0
                # Print final metrics
                summary = self.metrics.get_summary()
                logger.info("📊 Final debugging metrics:")
                logger.info(f"   - Initial errors: {summary['initial_errors']}")
                logger.info(f"   - Errors fixed: {summary['total_fixed']}")
                logger.info(f"   - New errors introduced: {summary['new_introduced']}")
                logger.info(f"   - Net improvement: {summary['net_improvement']}")
                logger.info(f"   - Total iterations: {summary['iterations']}")
                return True

            # Calculate metrics for this iteration (skip first iteration)
            if iteration > 0:
                fixed_this_iteration = self.metrics.current_error_count - current_total
                # Detect new errors (current errors that weren't in the previous count)
                new_errors = 0
                if (
                    current_total
                    > self.metrics.current_error_count - fixed_this_iteration
                ):
                    new_errors = current_total - (
                        self.metrics.current_error_count - fixed_this_iteration
                    )

                self.metrics.add_iteration(
                    fixed_this_iteration, current_total, new_errors
                )

                logger.info(f"📊 Iteration {iteration} results:")
                logger.info(f"   - Fixed: {fixed_this_iteration} errors")
                logger.info(f"   - Remaining: {current_total} errors")
                logger.info(f"   - New errors: {new_errors}")

                # Check if we're stuck in a loop
                error_count_history.append(current_total)
                if len(error_count_history) >= 3:
                    # Check if the error count is oscillating or stuck
                    recent_counts = error_count_history[-3:]
                    if len(set(recent_counts)) == 1 or (
                        recent_counts[0] == recent_counts[2] != recent_counts[1]
                    ):
                        stuck_iterations += 1
                        logger.warning(
                            f"Possible loop detected - error count pattern: {recent_counts} "
                            f"(stuck count: {stuck_iterations}/{max_stuck_iterations})",
                        )
                        if stuck_iterations >= max_stuck_iterations:
                            logger.error(
                                "Auto-debugger appears stuck in a loop. "
                                "Stopping to prevent endless iterations.",
                            )
                            # Log files that keep getting modified
                            logger.info("Files repeatedly modified:")
                            for file_path, count in sorted(
                                files_modified_count.items(),
                                key=lambda x: x[1],
                                reverse=True,
                            )[:5]:
                                logger.info(f"  - {file_path}: {count} times")
                            break
                    else:
                        stuck_iterations = 0
                logger.info(
                    f"   - Net progress: {self.metrics.initial_error_count - current_total}",
                )

                if new_errors > fixed_this_iteration:
                    logger.warning(
                        "⚠️  Introducing more errors than fixing - stopping to prevent regression",
                    )
                    break

            self.metrics.current_error_count = current_total
            logger.info(
                f"📊 Iteration {iteration + 1}/{self.max_retries} - "
                f"Current errors: {current_total}",
            )
            logger.info(f"   Error breakdown: {error_breakdown}")

            # Check if we're stuck in a loop
            current_error_signature = (
                f"{current_total}:{sorted(error_breakdown.items())}"
            )
            if current_error_signature in error_history:
                stuck_iterations += 1
                logger.warning(
                    f"⚠️  Same error state seen before "
                    f"(stuck count: {stuck_iterations}/{max_stuck_iterations})",
                )
                if stuck_iterations >= max_stuck_iterations:
                    logger.error(
                        "❌ Stuck in loop - same errors keep appearing. Stopping."
                    )
                    logger.info(
                        "💡 Tip: Some errors may need manual fixes or should be "
                        "added to ignore lists",
                    )
                    break
            else:
                stuck_iterations = 0  # Reset if we made progress
                error_history.append(current_error_signature)

            # Re-parse current errors for this iteration
            # Safe: Fixed command with no user input
            result = subprocess.run(  # noqa: S603
                [
                    "/usr/bin/env",
                    "pre-commit",
                    "run",
                    "--config",
                    ".solve/config/pre-commit-validate.yaml",
                    "--all-files",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            errors = self.error_parser.parse_output(
                result.stdout + "\n" + result.stderr
            )

            # Group errors by file
            errors_by_file = defaultdict(list)
            for error in errors:
                if error.file and error.code != "files-modified":
                    errors_by_file[error.file].append(error)

            # Fix errors in each file
            fixed_count = 0
            for file_path, file_errors in errors_by_file.items():
                # Group errors by type for batch fixing
                errors_by_type = defaultdict(list)
                for error in file_errors:
                    errors_by_type[error.code].append(error)

                logger.info(
                    f"File {file_path} has {len(file_errors)} errors "
                    f"of {len(errors_by_type)} types",
                )

                # Fix similar errors together
                file_fixed = False
                for error_code, similar_errors in errors_by_type.items():
                    # Log which model will be used
                    model = self.complexity_analyzer.get_model_for_batch(similar_errors)
                    logger.info(
                        f"  - {error_code}: {len(similar_errors)} error(s) → using "
                        f"{model.upper()} model",
                    )

                    # For Haiku, fix one at a time for better success rate
                    if model == "haiku" and len(similar_errors) > 1:
                        logger.info(
                            f"Using incremental approach for {error_code} errors with Haiku",
                        )
                        fixed_any = False
                        for idx, error in enumerate(similar_errors):
                            logger.info(
                                f"Fixing {error_code} error {idx + 1}/{len(similar_errors)}",
                            )
                            if await self._fix_file_errors(Path(file_path), [error]):
                                fixed_any = True
                        if fixed_any:
                            file_fixed = True
                    else:
                        # Batch fix for Sonnet or single errors
                        if await self._fix_file_errors_batch(
                            Path(file_path), similar_errors
                        ):
                            file_fixed = True

                if file_fixed:
                    fixed_count += 1
                    files_modified_count[file_path] += 1

                    # Re-run auto-fixers after each LLM fix to clean up any simple issues
                    try:
                        logger.info("Re-running auto-fixers after LLM fix...")
                        autofix_config_2 = AutofixConfig()
                        runner = AutoFixerRunner(autofix_config_2)
                        fix_result_obj = await runner.run_all_fixers([file_path])

                        # Convert FixResult to dict format
                        fix_result = {
                            "enabled": autofix_config_2.enable_auto_fixers,
                            "total_changes": len(fix_result_obj.files_changed),
                        }

                        if fix_result["enabled"] and fix_result["total_changes"] > 0:
                            logger.info(
                                f"Auto-fixers made {fix_result['total_changes']} "
                                f"additional changes after LLM fix",
                            )
                    except Exception as e:
                        logger.warning(f"Could not re-run auto-fixers: {e}")

            # End of iteration - check if we made progress
            if fixed_count == 0:
                logger.warning("No files were fixed in this iteration - stopping")
                break

        # Print final metrics after all iterations
        summary = self.metrics.get_summary()
        logger.info("📊 Final debugging metrics:")
        logger.info(f"   - Initial errors: {summary['initial_errors']}")
        logger.info(f"   - Final errors: {summary['final_errors']}")
        logger.info(f"   - Errors fixed: {summary['total_fixed']}")
        logger.info(f"   - New errors introduced: {summary['new_introduced']}")
        logger.info(f"   - Net improvement: {summary['net_improvement']}")
        logger.info(f"   - Total iterations: {summary['iterations']}")
        logger.info(f"   - Files processed: {summary['files_touched']}")

        # Add loop detection info if stuck
        if stuck_iterations > 0:
            logger.info(
                f"   - Loop detection triggered: {stuck_iterations} stuck iterations"
            )
            early_stop = stuck_iterations >= max_stuck_iterations
            logger.info(f"   - Stopped early: {'Yes' if early_stop else 'No'}")

        return bool(summary["success"])

    async def _fix_file_errors_batch(
        self, file_path: Path, errors: list[ErrorContext]
    ) -> bool:
        """Fix multiple similar errors in a single file with one Claude request."""
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        # All errors should have the same code
        error_code = errors[0].code

        # Skip if no fix strategy
        strategy = None
        for s in self.strategies:
            if await s.can_fix(errors[0]):
                strategy = s
                break

        if not strategy:
            logger.warning(f"No strategy found for {errors[0].hook}:{error_code}")
            return False

        # For auto-fix strategies, just return success
        if isinstance(strategy, AutoFixOnlyStrategy):
            return True

        # Backup file first
        self.backup_manager.backup_file(file_path)

        # Read current content
        original_content = file_path.read_text()

        # For batch fixing, send all error locations at once
        if self.anthropic_client and len(errors) > 1:
            fixed_content = await self._apply_batch_fix_with_claude(
                file_path,
                original_content,
                errors,
                strategy,
            )

            if fixed_content and fixed_content != original_content:
                file_path.write_text(fixed_content)

                # Verify syntax
                if not await self.safety_checks.syntax_check(file_path):
                    logger.error(f"Syntax check failed, restoring {file_path}")
                    self.backup_manager.restore_file(file_path)
                    return False

                logger.info(
                    f"Applied batch fix for {len(errors)} {error_code} errors in {file_path}",
                )

                # Re-run auto-fixers on this specific file after batch LLM fix
                try:
                    from solve.autofix.models import AutofixConfig
                    from solve.autofix.runner import AutoFixerRunner

                    logger.info(
                        f"Running auto-fixers on {file_path} after batch LLM fix..."
                    )
                    config = AutofixConfig()
                    runner = AutoFixerRunner(config)
                    fix_result_obj = await runner.run_all_fixers([str(file_path)])

                    # Convert FixResult to dict format
                    fix_result = {
                        "enabled": config.enable_auto_fixers,
                        "total_changes": len(fix_result_obj.files_changed),
                    }
                    if fix_result["enabled"] and fix_result["total_changes"] > 0:
                        logger.info(
                            f"Auto-fixers made {fix_result['total_changes']} "
                            f"additional changes to {file_path}",
                        )
                except Exception as e:
                    logger.warning(f"Could not run auto-fixers on {file_path}: {e}")

                # Verify the specific errors are actually fixed
                logger.info(f"Verifying {error_code} errors are fixed in {file_path}")
                verification_passed = await self._verify_fixes(
                    file_path, error_code or "", errors
                )

                if verification_passed:
                    logger.info(
                        f"✅ Successfully fixed {len(errors)} {error_code} errors in {file_path}",
                    )
                    return True
                else:
                    # Instead of full rollback, check which errors were actually fixed
                    logger.warning(f"⚠️  Partial fix detected for {error_code} errors")

                    # Count how many were fixed vs remaining
                    # Safe: Fixed command with controlled file_path argument
                    cmd = [
                        "/usr/bin/env",
                        "ruff",
                        "check",
                        "--output-format=json",
                        str(file_path),
                    ]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, check=False
                    )  # noqa: S603

                    remaining_count = 0
                    if result.stdout:
                        try:
                            import json

                            errors_json = json.loads(result.stdout)
                            remaining_count = sum(
                                1
                                for err in errors_json
                                if err.get("code") == error_code
                            )
                        except Exception as e:
                            logger.debug(f"Error parsing JSON from ruff output: {e}")

                    fixed_count = len(errors) - remaining_count
                    if fixed_count > 0:
                        logger.info(
                            f"✅ Partially fixed {fixed_count}/{len(errors)} {error_code} errors",
                        )
                        # Keep the partial fix
                        return True
                    else:
                        logger.error(f"❌ No {error_code} errors were fixed")
                        self.backup_manager.restore_file(file_path)
                        return False
        else:
            # Fall back to individual fixes
            return await self._fix_file_errors(file_path, errors)

        return False

    async def _apply_batch_fix_with_claude(
        self,
        file_path: Path,
        content: str,
        errors: list[ErrorContext],
        strategy: FixStrategy,
    ) -> str | None:
        """Fix multiple similar errors with a single Claude request using Anthropic API."""
        if not self.anthropic_client:
            logger.warning("Anthropic API client not available")
            return None

        error_code = errors[0].code
        error_lines = [e.line for e in errors if e.line]

        # Determine which model to use based on error complexity
        model = self.complexity_analyzer.get_model_for_batch(errors)
        model_name = (
            "claude-3-haiku-20240307"
            if model == "haiku"
            else "claude-3-5-sonnet-20241022"
        )
        logger.info(f"Using {model} model for batch fix of {error_code} errors")

        # Build full-file prompt for Haiku (cheap tokens = send everything)
        prompt = f"""<task>Fix ALL {error_code} errors in this file</task>

<errors>
{len(errors)} {error_code} errors on lines: {", ".join(map(str, error_lines))}
Message: {errors[0].message}
</errors>

<rules>
1. Fix ALL {error_code} errors
2. Return ONLY the complete fixed Python code
3. Change ONLY error lines
4. Keep all indentation exact
5. NO explanations, NO markdown, NO prefixes like "Here is the fixed file:"
6. NO code blocks with ```
7. Start directly with the first line of code
</rules>

<file>
{content}
</file>

Output the complete fixed code below:
"""

        try:
            logger.info(
                f"Sending batch fix request to Anthropic API ({model}) for "
                f"{len(errors)} {error_code} errors",
            )

            # Use Anthropic API for text generation
            message = self.anthropic_client.messages.create(
                model=model_name,
                max_tokens=4096,
                temperature=0,  # Deterministic for code fixes
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract the full fixed file
            if message.content and len(message.content) > 0:
                content_block = message.content[0]
                if isinstance(content_block, TextBlock):
                    fixed_content = content_block.text.strip()
                else:
                    return None

                # Since we explicitly asked for raw code, check if Haiku still added formatting
                # Remove markdown formatting if present (just in case)
                if "```" in fixed_content:
                    # Find code between triple backticks
                    if "```python" in fixed_content:
                        start = fixed_content.find("```python") + 9
                        end = fixed_content.find("```", start)
                        if end > start:
                            fixed_content = fixed_content[start:end].strip()
                    else:
                        # Generic code block
                        lines = fixed_content.split("\n")
                        in_code = False
                        code_lines = []
                        for line in lines:
                            if line.strip().startswith("```"):
                                in_code = not in_code
                                continue
                            if in_code or not line.strip().startswith("```"):
                                code_lines.append(line)
                        if code_lines and code_lines[0].strip():  # Has content
                            fixed_content = "\n".join(code_lines)

                # Check for any remaining prefixes (shouldn't happen with new prompt)
                first_line = fixed_content.split("\n")[0] if fixed_content else ""
                if first_line and not first_line.strip().startswith(
                    ("import", "from", "#", '"""', "'''", "def", "class", "@"),
                ):
                    # Might have a prefix, try to find where code starts
                    lines = fixed_content.split("\n")
                    for i, line in enumerate(lines):
                        if line.strip() and line.strip()[0] in [
                            "i",
                            "f",
                            "#",
                            '"',
                            "'",
                            "d",
                            "c",
                            "@",
                        ]:
                            fixed_content = "\n".join(lines[i:])
                            break

                # Quick sanity check - should have roughly same number of lines
                original_line_count = len(content.split("\n"))
                fixed_line_count = len(fixed_content.split("\n"))
                if (
                    abs(original_line_count - fixed_line_count) > 50
                ):  # Allow some variance
                    logger.warning(
                        f"Line count mismatch: original={original_line_count}, "
                        f"fixed={fixed_line_count}",
                    )
                    return None

                if fixed_content and fixed_content != content:
                    logger.info(f"Claude provided batch fix for {error_code}")
                    logger.debug(f"Fixed {len(errors)} errors on lines: {error_lines}")

                    # Log the actual changes for debugging
                    logger.info("=== CLAUDE FIX PREVIEW ===")
                    original_lines_list: list[str] = content.split("\n")
                    fixed_lines_list: list[str] = fixed_content.split("\n")

                    # Show first few changed lines
                    changes_shown = 0
                    for i, (orig, fixed) in enumerate(
                        zip(original_lines_list, fixed_lines_list, strict=False),
                    ):
                        if orig != fixed and changes_shown < 3:
                            logger.info(f"Line {i + 1}:")
                            logger.info(f"  - Original: {orig[:80]}...")
                            logger.info(f"  + Fixed:    {fixed[:80]}...")
                            changes_shown += 1

                    return fixed_content
                else:
                    logger.warning("No changes detected in response")
                    return None

        except Exception as e:
            logger.error(f"Error in batch fix: {e}")

        return None

    async def _fix_file_errors(
        self, file_path: Path, errors: list[ErrorContext]
    ) -> bool:
        """Fix all errors in a single file."""
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        # Backup file first
        self.backup_manager.backup_file(file_path)

        # Read current content
        original_content = file_path.read_text()
        current_content = original_content

        # Try to fix each error
        for error in errors:
            # Find a strategy that can fix this error
            strategy = None
            for s in self.strategies:
                if await s.can_fix(error):
                    strategy = s
                    break

            if not strategy:
                logger.warning(f"No strategy found for {error.hook}:{error.code}")
                continue

            # Generate fix
            if self.anthropic_client:
                fixed_content = await self._apply_fix_with_claude(
                    file_path,
                    current_content,
                    error,
                    strategy,
                )
            else:
                # Manual fix for testing
                fixed_content = await self._apply_manual_fix(current_content, error)

            if fixed_content and fixed_content != current_content:
                # Validate the fix
                error_lines = [error.line] if error.line else []
                if await self.safety_checks.validate_fix_scope(
                    current_content,
                    fixed_content,
                    error_lines,
                ):
                    current_content = fixed_content
                    logger.info(f"Applied fix for {error.code} in {file_path}")
                else:
                    logger.warning(f"Fix validation failed for {error.code}")

        # Write back if changed
        if current_content != original_content:
            file_path.write_text(current_content)

            # Verify syntax
            if not await self.safety_checks.syntax_check(file_path):
                logger.error(f"Syntax check failed, restoring {file_path}")
                self.backup_manager.restore_file(file_path)
                return False

            # Re-run auto-fixers on this specific file after LLM fix
            try:
                from solve.autofix.models import AutofixConfig
                from solve.autofix.runner import AutoFixerRunner

                logger.info(f"Running auto-fixers on {file_path} after LLM fixes...")
                config = AutofixConfig()
                runner = AutoFixerRunner(config)
                fix_result_obj = await runner.run_all_fixers([str(file_path)])

                # Convert FixResult to dict format
                fix_result = {
                    "enabled": config.enable_auto_fixers,
                    "total_changes": len(fix_result_obj.files_changed),
                }
                if fix_result["enabled"] and fix_result["total_changes"] > 0:
                    logger.info(
                        f"Auto-fixers made {fix_result['total_changes']} "
                        f"additional changes to {file_path}",
                    )
            except Exception as e:
                logger.warning(f"Could not run auto-fixers on {file_path}: {e}")

            # Verify which errors were fixed (incremental progress)
            error_codes = {e.code for e in errors}
            fixed_codes = []
            remaining_codes = []

            for code in error_codes:
                if code:  # Only process non-None codes
                    code_errors = [e for e in errors if e.code == code]
                    if await self._verify_fixes(file_path, code, code_errors):
                        fixed_codes.append(code)
                    else:
                        remaining_codes.append(code)

            if fixed_codes:
                logger.info(
                    f"✅ Fixed {len(fixed_codes)} error types in {file_path}: "
                    f"{', '.join(fixed_codes)}",
                )

            if remaining_codes:
                logger.info(
                    f"⚠️  {len(remaining_codes)} error types remain in {file_path}: "
                    f"{', '.join(remaining_codes)}",
                )
                # Check if we should keep partial progress
                solve_config = get_config()
                keep_partial = (
                    solve_config.debugging.keep_partial_fixes
                    if solve_config.debugging
                    else True
                )
                if not keep_partial:
                    logger.warning(
                        "SOLVE_KEEP_PARTIAL_FIXES=false, restoring file due to remaining errors",
                    )
                    self.backup_manager.restore_file(file_path)
                    return False
                else:
                    logger.info("Keeping partial fixes (SOLVE_KEEP_PARTIAL_FIXES=true)")
                    return len(fixed_codes) > 0  # Return True if we made any progress
            else:
                logger.info(f"✅ All errors in {file_path} successfully fixed")
                return True

        return False

    async def _apply_fix_with_claude(
        self,
        file_path: Path,
        content: str,
        error: ErrorContext,
        strategy: FixStrategy,
    ) -> str | None:
        """Use Claude to fix the error via Anthropic API."""
        prompt = await strategy.generate_fix_prompt(error)

        if not prompt:  # Auto-fix strategy
            return content

        if not self.anthropic_client:
            logger.warning("Anthropic API client not available, cannot fix with Claude")
            return None

        # Determine which model to use based on error complexity
        model = self.complexity_analyzer.get_model_for_error(error)
        model_name = (
            "claude-3-haiku-20240307"
            if model == "haiku"
            else "claude-3-5-sonnet-20241022"
        )
        logger.info(f"Using {model} model for {error.code} error")

        try:
            # Build full-file prompt for single error (still cheaper than debugging)
            single_error_prompt = f"""<task>Fix {error.code} error at line {error.line}</task>

<error>
Line {error.line}: {error.message}
</error>

<rules>
1. Fix ONLY this error
2. Return ONLY the complete fixed Python code
3. NO explanations, NO markdown, NO prefixes
4. NO code blocks with ```
5. Start directly with the first line of code
</rules>

<file>
{content}
</file>

Output the complete fixed code below:
"""

            # Send the fix request to Anthropic API
            logger.info(
                f"Sending fix request to Anthropic API ({model}) for {error.code} in {file_path}",
            )

            message = self.anthropic_client.messages.create(
                model=model_name,
                max_tokens=4096,
                temperature=0,
                messages=[{"role": "user", "content": single_error_prompt}],
            )

            # Extract the fixed code from the response
            if message.content and len(message.content) > 0:
                content_block = message.content[0]
                if isinstance(content_block, TextBlock):
                    fixed_content = content_block.text.strip()
                else:
                    return None

                # Since we explicitly asked for raw code, check if Haiku still added formatting
                # Remove markdown formatting if present (just in case)
                if "```" in fixed_content:
                    # Find code between triple backticks
                    if "```python" in fixed_content:
                        start = fixed_content.find("```python") + 9
                        end = fixed_content.find("```", start)
                        if end > start:
                            fixed_content = fixed_content[start:end].strip()
                    else:
                        # Generic code block
                        lines = fixed_content.split("\n")
                        in_code = False
                        code_lines = []
                        for line in lines:
                            if line.strip().startswith("```"):
                                in_code = not in_code
                                continue
                            if in_code:
                                code_lines.append(line)
                        if code_lines:
                            fixed_content = "\n".join(code_lines).strip()

                # Check for any remaining prefixes (shouldn't happen with new prompt)
                first_line = fixed_content.split("\n")[0] if fixed_content else ""
                if first_line and not first_line.strip().startswith(
                    ("import", "from", "#", '"""', "'''", "def", "class", "@"),
                ):
                    # Might have a prefix, try to find where code starts
                    lines = fixed_content.split("\n")
                    for i, line in enumerate(lines):
                        if line.strip() and line.strip()[0] in [
                            "i",
                            "f",
                            "#",
                            '"',
                            "'",
                            "d",
                            "c",
                            "@",
                        ]:
                            fixed_content = "\n".join(lines[i:])
                            break

                if fixed_content:
                    logger.info(f"Claude provided fix for {error.code}")

                    # Log the actual fix for debugging
                    logger.info("=== CLAUDE FIX PREVIEW (single error) ===")
                    original_lines_single: list[str] = content.split("\n")
                    fixed_lines_single: list[str] = fixed_content.split("\n")

                    # Show the specific line that should be fixed
                    if (
                        error.line
                        and error.line <= len(original_lines_single)
                        and error.line <= len(fixed_lines_single)
                    ):
                        logger.info(f"Line {error.line}:")
                        logger.info(
                            f"  - Original: {original_lines_single[error.line - 1][:80]}...",
                        )
                        logger.info(
                            f"  + Fixed:    {fixed_lines_single[error.line - 1][:80]}..."
                        )

                    # Show any other changes
                    other_changes = 0
                    for i, (orig, fixed) in enumerate(
                        zip(original_lines_single, fixed_lines_single, strict=False),
                    ):
                        if i + 1 != error.line and orig != fixed and other_changes < 2:
                            logger.info(f"Line {i + 1} (unexpected change):")
                            logger.info(f"  - Original: {orig[:80]}...")
                            logger.info(f"  + Fixed:    {fixed[:80]}...")
                            other_changes += 1

                    return fixed_content

            logger.warning("No fix extracted from Claude response")
            return None

        except Exception as e:
            logger.error(f"Error applying fix with Claude: {e}")
            return None

    async def _count_all_errors(self) -> tuple[int, dict[str, int]]:
        """Count all current errors by running pre-commit validation.

        Returns:
            Tuple of (total_count, error_breakdown_by_code)
        """
        try:
            # Safe: Fixed command with no user input
            result = subprocess.run(  # noqa: S603
                [
                    "/usr/bin/env",
                    "pre-commit",
                    "run",
                    "--config",
                    ".solve/config/pre-commit-validate.yaml",
                    "--all-files",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            # Parse errors from output
            errors = self.error_parser.parse_output(
                result.stdout + "\n" + result.stderr
            )

            # Count by error code
            error_breakdown: dict[str, int] = defaultdict(int)
            for error in errors:
                if error.code and error.code != "files-modified":
                    error_breakdown[error.code] += 1

            total_count = sum(error_breakdown.values())
            return total_count, dict(error_breakdown)

        except Exception as e:
            logger.error(f"Error counting errors: {e}")
            return 0, {}

    async def _verify_fixes(
        self,
        file_path: Path,
        error_code: str,
        original_errors: list[ErrorContext],
    ) -> bool:
        """Verify that specific errors were actually fixed by running ruff on the file."""
        try:
            # Run ruff check on just this file to see if errors are gone
            # Safe: Fixed command with controlled file_path argument
            cmd = [
                "/usr/bin/env",
                "ruff",
                "check",
                "--output-format=json",
                str(file_path),
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False
            )  # noqa: S603

            if result.returncode == 0:
                # No errors at all - great!
                return True

            # Parse remaining errors
            remaining_errors = []
            if result.stdout:
                try:
                    import json

                    errors_json = json.loads(result.stdout)
                    for err in errors_json:
                        if err.get("code") == error_code:
                            remaining_errors.append(err)
                except Exception:
                    # Fallback to text parsing
                    for line in result.stdout.split("\n"):
                        if error_code in line and str(file_path) in line:
                            remaining_errors.append(line)

            # Check if our specific errors are fixed
            original_lines = {e.line for e in original_errors if e.line}
            if remaining_errors:
                # Check if these are the same errors or new ones
                remaining_lines = set()
                for err in remaining_errors:
                    if isinstance(err, dict):
                        line = err.get("location", {}).get("row")
                        if line:
                            remaining_lines.add(line)
                    else:
                        # Try to extract line number from text
                        import re

                        match = re.search(r":(\d+):", str(err))
                        if match:
                            remaining_lines.add(int(match.group(1)))

                if remaining_lines & original_lines:
                    logger.warning(
                        f"Original errors still present on lines: "
                        f"{remaining_lines & original_lines}",
                    )
                    return False
                else:
                    logger.info(
                        f"Original errors fixed, but new {error_code} errors on lines: "
                        f"{remaining_lines}",
                    )
                    # This is still a failure - we shouldn't create new errors
                    return False

            return True

        except Exception as e:
            logger.error(f"Error verifying fixes: {e}")
            # If we can't verify, assume it failed
            return False

    async def _apply_manual_fix(self, content: str, error: ErrorContext) -> str | None:
        """Apply simple manual fixes for testing."""
        lines = content.split("\n")

        if error.code == "UP007" and error.line:
            # Fix type annotations from Optional[X] to X | None
            if 0 < error.line <= len(lines):
                line = lines[error.line - 1]
                # Need to handle imports too
                if "from typing import" in line and "Optional" in line:
                    # Remove Optional from imports
                    fixed_line = re.sub(r",?\s*Optional\s*,?", "", line)
                    # Clean up double commas or trailing commas
                    fixed_line = re.sub(r",\s*,", ",", fixed_line)
                    fixed_line = re.sub(r",\s*\)", ")", fixed_line)
                    fixed_line = re.sub(r"\(\s*,", "(", fixed_line)
                    lines[error.line - 1] = fixed_line
                else:
                    fixed_line = re.sub(r"Optional\[([^\]]+)\]", r"\1 | None", line)
                    lines[error.line - 1] = fixed_line
                return "\n".join(lines)

        elif error.code == "F841" and error.line:
            # Remove unused variable
            if 0 < error.line <= len(lines):
                line = lines[error.line - 1]
                # Comment out the line instead of removing
                lines[error.line - 1] = "# " + line.lstrip() + "  # unused"
                return "\n".join(lines)

        elif error.code == "F401" and error.line:
            # Remove unused import
            if 0 < error.line <= len(lines):
                # Comment out instead of removing
                lines[error.line - 1] = (
                    "# " + lines[error.line - 1].lstrip() + "  # unused import"
                )
                return "\n".join(lines)

        elif error.code == "T201" and error.line:
            # Comment out print statements
            if 0 < error.line <= len(lines):
                line = lines[error.line - 1]
                if "print(" in line:
                    lines[error.line - 1] = "# " + line.lstrip()
                    return "\n".join(lines)

        elif error.code == "S314" and error.line and 0 < error.line <= len(lines):
            # Replace xml.etree.ElementTree with defusedxml
            line = lines[error.line - 1]
            if "xml.etree" in line:
                # Add defusedxml import after this line
                fixed_line = line.replace(
                    "xml.etree.ElementTree", "defusedxml.ElementTree"
                )
                lines[error.line - 1] = fixed_line
                return "\n".join(lines)

        return None
