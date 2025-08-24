"""
LLM-powered manual fix orchestrator for complex code issues.

This module implements Stage 3 of the autofix pipeline, handling complex issues
that require LLM assistance with smart batching and context optimization.
"""

import ast
import asyncio
import json
import logging
from collections.abc import Sized
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import EVAL_BASE_DIR, ensure_eval_directories

# Import from eval package storage module
try:
    from eval.storage import ResultStorage, StorageFormat
except ImportError:
    # Fallback for development environment
    import os
    import sys

    eval_path = os.path.join(os.path.dirname(__file__), "../../../eval/src")
    if os.path.exists(eval_path):
        sys.path.insert(0, eval_path)
        from eval.storage import ResultStorage, StorageFormat
    else:
        raise ImportError(
            "Cannot import eval.storage module. Ensure eval package is installed.",
        ) from None

# Import solve_core.config with fallback for development environment
try:
    from solve_core.config import ConfigurationError, ConfigurationManager
except ImportError:
    # Fallback for development environment
    import os
    import sys

    solve_core_path = os.path.join(
        os.path.dirname(__file__), "../../../../shared/solve_core"
    )
    if os.path.exists(solve_core_path):
        sys.path.insert(0, solve_core_path)
        from solve_core.config import ConfigurationError, ConfigurationManager
    else:
        raise ImportError(
            "Cannot import solve_core.config module. Ensure solve-core package is installed.",
        ) from None

from google.genai import Client, types

from .analyzer import AnalysisReport
from .backup import BackupManager
from .eval_adapter import AutofixEvalAdapter
from .metrics import MetricsCollector
from .models import (
    AutofixConfig,
    Error,
    ErrorPriority,
    FixResult,
    FixType,
    ValidationResult,
)
from .prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


@dataclass
class BatchContext:
    """Context for a batch of errors to be fixed."""

    errors: list[Error]
    file_path: Path
    context_lines: list[str]
    imports: list[str]
    type_definitions: list[str]


class ErrorGrouper:
    """Groups and prioritizes errors for efficient LLM processing."""

    ERROR_PRIORITY = {
        "syntax": 1,  # Must fix first
        "imports": 2,  # Dependencies for types
        "types": 3,  # After imports resolved
        "simple": 4,  # Quick wins
        "complex": 5,  # Needs deep understanding
    }

    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size

    def group_errors(
        self,
        errors: list[Error],
        analysis_report: AnalysisReport | None = None,
    ) -> list[list[Error]]:
        """Group errors by priority and file for optimal processing."""
        # If we have an analysis report, use its intelligent grouping
        if analysis_report and analysis_report.error_groups:
            return self._group_from_analysis(errors, analysis_report)

        # Otherwise, fall back to simple grouping
        # Sort by priority then by file
        sorted_errors = sorted(
            errors,
            key=lambda e: (
                self.ERROR_PRIORITY.get(e.priority.name.lower(), 5),
                e.file_path,
                e.line,
            ),
        )

        # Group into batches
        batches = []
        current_batch: list[Error] = []
        current_file = None

        for error in sorted_errors:
            # Start new batch if file changes or batch is full
            if current_file != error.file_path or len(current_batch) >= self.batch_size:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [error]
                current_file = error.file_path
            else:
                current_batch.append(error)

        if current_batch:
            batches.append(current_batch)

        return batches

    def _group_from_analysis(
        self,
        errors: list[Error],
        analysis_report: AnalysisReport,
    ) -> list[list[Error]]:
        """Use intelligent grouping from analysis report."""
        batches = []

        # Create a set of errors for fast lookup
        error_set = set()
        for error in errors:
            # Create a unique key for each error
            key = (error.file_path, error.line, error.code)
            error_set.add(key)

        # Process groups in priority order
        for group in analysis_report.error_groups:
            # Skip critical risk groups
            if group.risk_level.name == "CRITICAL":
                logger.debug(f"Skipping CRITICAL risk group: {group.group_key}")
                continue

            # Skip low confidence groups
            if group.fix_confidence < 0.5:
                logger.debug(
                    f"Skipping low confidence group: {group.group_key} "
                    f"({group.fix_confidence:.0%})",
                )
                continue

            # Filter to only enabled errors
            batch = []
            for error in group.errors:
                key = (error.file_path, error.line, error.code)
                if key in error_set:
                    batch.append(error)

            if batch:
                # Respect batch size limit
                if len(batch) > self.batch_size:
                    # Split large groups into smaller batches
                    for i in range(0, len(batch), self.batch_size):
                        batches.append(batch[i : i + self.batch_size])
                else:
                    batches.append(batch)

                logger.debug(
                    f"Added batch from {group.group_type} group: {len(batch)} errors"
                )

        return batches


class ContextBuilder:
    """Builds selective context for LLM processing."""

    def __init__(self, context_lines: int = 10):
        self.context_lines = context_lines

    def build_context(self, errors: list[Error]) -> BatchContext:
        """Extract minimal necessary context for a batch of errors."""
        if not errors:
            raise ValueError("No errors provided")

        file_path = errors[0].file_path

        # Read file content
        try:
            with open(file_path) as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return BatchContext(errors, Path(file_path), [], [], [])

        # Extract context around errors
        context_ranges: set[int] = set()
        for error in errors:
            start = max(0, error.line - self.context_lines)
            end = min(len(lines), error.line + self.context_lines)
            context_ranges.update(range(start, end))

        context_lines = [lines[i] for i in sorted(context_ranges)]

        # Extract imports and type definitions
        imports = self._extract_imports(lines)
        type_definitions = self._extract_type_definitions(lines, errors)

        return BatchContext(
            errors=errors,
            file_path=Path(file_path),
            context_lines=context_lines,
            imports=imports,
            type_definitions=type_definitions,
        )

    def _extract_imports(self, lines: list[str]) -> list[str]:
        """Extract import statements from file."""
        imports = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                imports.append(stripped)
        return imports

    def _extract_type_definitions(
        self, lines: list[str], errors: list[Error]
    ) -> list[str]:
        """Extract type definitions related to errors."""
        type_defs = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("class ", "def ", "async def ")):
                type_defs.append(stripped)
        return type_defs


class XMLPromptFormatter:
    """Formats prompts with XML structure for 30% performance improvement."""

    def format_fix_request(self, context: BatchContext) -> str:
        """Format a fix request with XML structure."""
        error_count = len(context.errors)
        error_types = list({e.code for e in context.errors})

        # Build XML prompt
        xml_prompt = f"""<fix_request>
  <context>
    <file>{context.file_path}</file>
    <errors count="{error_count}" types="{", ".join(error_types)}"/>
  </context>

  <instructions>
    IMMEDIATELY use the Edit or MultiEdit tools to fix the following code issues.
    DO NOT explain or analyze - just fix the issues directly.
    Group similar fixes together for efficiency using MultiEdit when fixing multiple
    issues in the same file.
  </instructions>

  <errors_to_fix>"""

        # Group errors by type for clearer instructions
        errors_by_type: dict[str, list[Error]] = {}
        for error in context.errors:
            if error.code not in errors_by_type:
                errors_by_type[error.code] = []
            errors_by_type[error.code].append(error)

        # Add each error group with specific fix instructions
        for error_code, errors in errors_by_type.items():
            xml_prompt += f"""
    <error_group code="{error_code}" count="{len(errors)}">"""

            # Add specific fix instructions based on error type
            if error_code == "E722":
                xml_prompt += """
      <fix_instruction>Replace bare 'except:' with 'except Exception:' to catch all
      exceptions explicitly</fix_instruction>"""
            elif error_code == "E402":
                xml_prompt += """
      <fix_instruction>CRITICAL: Move the import statement to the top of the file
      immediately after the module docstring but before any other code. DO NOT change
      the import itself - only move it to the correct location. Keep the exact same
      import statement. DO NOT replace any existing imports.</fix_instruction>
      <example>
        # WRONG: import after code
        some_variable = 42
        import os  # This should be moved up

        # CORRECT: import at top
        import os  # Moved here
        some_variable = 42
      </example>"""
            elif error_code == "F401":
                xml_prompt += """
      <fix_instruction>Remove unused import statements</fix_instruction>"""
            elif error_code == "F811":
                xml_prompt += """
      <fix_instruction>Remove or rename duplicate function/variable
      definitions</fix_instruction>"""
            elif error_code == "var-annotated":
                xml_prompt += """
      <fix_instruction>Add type annotation to variable assignment. Use proper
      type based on the assigned value.</fix_instruction>
      <example>
        # WRONG: no type annotation
        data = []

        # CORRECT: with type annotation
        data: List[Any] = []
      </example>"""
            elif error_code == "assignment":
                xml_prompt += """
      <fix_instruction>Fix type mismatch in assignment by either casting the value or
      changing the variable type.</fix_instruction>
      <example>
        # WRONG: type mismatch
        count: int = "5"

        # CORRECT: proper casting
        count: int = int("5")
      </example>"""
            elif error_code == "S110":
                xml_prompt += """
      <fix_instruction>Add logging or a comment explaining why the exception is being
      ignored. DO NOT remove the try-except block.</fix_instruction>
      <example>
        # WRONG: bare try-except-pass
        try:
            process_data()
        except Exception:
            pass

        # CORRECT: with explanation
        try:
            process_data()
        except Exception:
            # Ignore errors in optional processing
            pass

        # OR with logging:
        try:
            process_data()
        except Exception as e:
            logger.debug(f"Ignoring error in optional processing: {e}")
      </example>"""
            elif error_code == "B007":
                xml_prompt += """
      <fix_instruction>Rename unused loop variable by prefixing with underscore. KEEP
      THE ENTIRE FOR LOOP INTACT.</fix_instruction>
      <example>
        # WRONG: unused loop variable
        for item in items:
            print("Processing")

        # CORRECT: prefix with underscore
        for _item in items:
            print("Processing")

        # WRONG FIX: DO NOT DO THIS
        pass  # Never replace the loop with pass!
      </example>"""
            elif error_code.startswith("E"):
                xml_prompt += """
      <fix_instruction>Fix the style/syntax issue as described in the error
      message</fix_instruction>"""

            xml_prompt += """
      <locations>"""
            for error in errors:
                xml_prompt += f"""
        <location line="{error.line}" column="{error.column}">{error.message}</location>"""
            xml_prompt += """
      </locations>
    </error_group>"""

        xml_prompt += f"""
  </errors_to_fix>

  <action_required>
    Use Edit or MultiEdit tool NOW to fix all {error_count} errors in {context.file_path}.
    DO NOT read the file first - the errors and their locations are already provided above.
    Group all fixes into a single MultiEdit call when possible.
  </action_required>
</fix_request>"""

        return xml_prompt

    def _format_context_lines(self, lines: list[str], focus_line: int) -> str:
        """Format context lines with line numbers."""
        formatted = []
        for i, line in enumerate(lines, 1):
            prefix = ">>>" if i == focus_line else "   "
            formatted.append(f"{prefix} {i:3d}: {line.rstrip()}")
        return "\n".join(formatted)


class ManualFixOrchestrator:
    """Orchestrates LLM-powered fixes for complex code issues."""

    def __init__(self, config: AutofixConfig, sdk_interface: Any = None):
        self.config = config
        self.sdk_interface = sdk_interface  # Keep for compatibility
        self.error_grouper = ErrorGrouper(config.llm_batch_size)
        self.context_builder = ContextBuilder()
        self.prompt_formatter = XMLPromptFormatter()
        self.backup_manager = BackupManager(config)
        self.metrics = MetricsCollector()
        self.llm_fix_config = self._load_llm_fix_config()
        self.prompt_loader = PromptLoader()

        # Initialize eval storage
        ensure_eval_directories()
        self.result_storage = ResultStorage(EVAL_BASE_DIR)
        self.eval_adapter = AutofixEvalAdapter(self.result_storage)

        # Initialize Google Generative AI client
        # Require explicit API key configuration - no fallbacks
        import os

        # Ensure configuration is loaded from .env
        ConfigurationManager()

        api_key = os.getenv("GOOGLE_GENAI_API_KEY")

        if not api_key:
            raise ConfigurationError(
                "GOOGLE_GENAI_API_KEY environment variable is required. "
                "No fallback authentication will be attempted.",
            )

        self.client: Client = Client(api_key=api_key)
        self.adk_configured = True
        logger.debug("Google Generative AI configured with API key")

    async def fix_errors(
        self,
        validation_result: ValidationResult,
        analysis_report: AnalysisReport | None = None,
    ) -> FixResult:
        """Fix complex errors using LLM assistance."""
        if not validation_result.errors:
            return FixResult(
                success=True,
                files_changed=[],
                errors_fixed=0,
                time_taken=0.0,
                details={"fix_type": FixType.LLM_MANUAL},
            )

        start_time = asyncio.get_event_loop().time()

        # Filter errors based on LLM fix configuration
        original_error_count = len(validation_result.errors)
        # Convert dict errors to Error objects
        error_objects = []
        for e in validation_result.errors:
            # Create Error object from dict with proper priority
            priority = ErrorPriority.MEDIUM
            if "priority" in e and isinstance(e["priority"], ErrorPriority):
                priority = e["priority"]
            elif "priority" in e:
                # Try to convert string priority to enum
                try:
                    priority = ErrorPriority[e["priority"].upper()]
                except (KeyError, AttributeError):
                    priority = ErrorPriority.MEDIUM

            error_obj = Error(
                file_path=e.get(
                    "file_path", e.get("file", "")
                ),  # Handle both file_path and file
                line=e.get("line", 0),
                column=e.get("column", 0),
                code=e.get("code", ""),
                message=e.get("message", ""),
                priority=priority,
                context=e.get("context"),
            )
            error_objects.append(error_obj)

        enabled_errors = self._filter_enabled_errors(error_objects)
        disabled_count = original_error_count - len(enabled_errors)

        if disabled_count > 0:
            logger.info(
                f"Filtered out {disabled_count} errors based on LLM fix configuration"
            )

        if not enabled_errors:
            logger.info("No errors enabled for LLM fixing")
            return FixResult(
                success=True,
                files_changed=[],
                errors_fixed=0,
                time_taken=0.0,
                details={
                    "fix_type": FixType.LLM_MANUAL,
                    "filtered_errors": disabled_count,
                    "enabled_errors": 0,
                },
            )

        try:
            # Create backup before fixing
            # Convert validation errors to proper format
            file_paths = []
            for error in enabled_errors:
                file_path = getattr(error, "file_path", None)
                if file_path and file_path != "." and Path(file_path).exists():
                    file_paths.append(Path(file_path))

            # Only create backup if we have valid file paths
            backup_id = None
            if file_paths:
                backup_id = await self.backup_manager.create_backup(file_paths)

            # Group errors for batch processing using analysis if available
            error_batches = self.error_grouper.group_errors(
                enabled_errors, analysis_report
            )

            # Process each batch
            fixes_applied = 0
            errors_fixed = []
            batch_failures = []

            logger.info(f"Processing {len(error_batches)} error batches...")
            for i, batch in enumerate(error_batches):
                batch_error_codes = {e.code for e in batch}
                logger.debug(
                    f"Batch {i + 1}/{len(error_batches)}: {len(batch)} errors "
                    f"({', '.join(batch_error_codes)})",
                )

                try:
                    batch_result = await self._process_batch(batch)
                    fixes_applied += batch_result.errors_fixed
                    errors_fixed.extend(batch)  # Track which errors were addressed

                    if batch_result.success:
                        logger.info(
                            f"  Batch {i + 1}: Fixed {batch_result.errors_fixed} errors"
                        )
                    else:
                        logger.warning(
                            f"  Batch {i + 1}: Failed - "
                            f"{batch_result.details.get('error', 'Unknown error')}",
                        )
                except Exception as e:
                    logger.warning(
                        f"  Batch {i + 1}: Exception during processing - {e}"
                    )
                    batch_failures.append(
                        {
                            "batch": i + 1,
                            "error": str(e),
                            "errors_in_batch": len(batch),
                        },
                    )
                    # Continue with next batch instead of rolling back
                    continue

            end_time = asyncio.get_event_loop().time()

            # VALIDATE fixes after all batches processed (Constitutional AI principle #3)
            validation_passed = True
            if fixes_applied > 0 and file_paths:
                logger.info("Validating fixes...")
                try:
                    # Import validation tools at runtime to avoid circular imports
                    from .validation import validate_files

                    validation_dict = await validate_files(file_paths)
                    validation_passed = validation_dict.get("all_passed", True)

                    if not validation_passed:
                        logger.warning("Fixes failed validation - performing rollback")
                        if backup_id:
                            rollback_success = await self.backup_manager.rollback(
                                backup_id
                            )
                            if rollback_success:
                                logger.info("Rollback completed successfully")
                                # Reset fixes_applied since we rolled back
                                fixes_applied = 0
                                errors_fixed = []
                            else:
                                logger.error("Rollback failed - changes may be corrupt")

                except ImportError:
                    logger.warning(
                        "Validation module not available - skipping validation"
                    )
                except Exception as e:
                    logger.error(f"Validation failed: {e}")
                    # Continue without rollback - validation failure doesn't mean fixes are wrong

            # Record metrics
            self.metrics.record_llm_fixes(
                fixes_applied=fixes_applied,
                time_taken=end_time - start_time,
                backup_id=backup_id or "",
            )

            # Determine success based on whether we fixed anything AND validation passed
            success = fixes_applied > 0 and validation_passed

            # Get unique file paths from fixed errors
            files_changed = []
            for error in errors_fixed:
                file_path = getattr(error, "file_path", None)
                if file_path and file_path not in files_changed:
                    files_changed.append(file_path)

            return FixResult(
                success=success,
                files_changed=files_changed,
                errors_fixed=fixes_applied,
                time_taken=end_time - start_time,
                details={
                    "fix_type": FixType.LLM_MANUAL,
                    "errors_addressed": len(errors_fixed),
                    "filtered_errors": disabled_count,
                    "enabled_errors": len(enabled_errors),
                    "batch_failures": batch_failures,
                    "partial_success": len(batch_failures) > 0 and fixes_applied > 0,
                    "validation_passed": validation_passed,
                    "total_batches": len(error_batches),
                    "successful_batches": len(error_batches) - len(batch_failures),
                },
            )

        except Exception as e:
            logger.error(f"LLM fix orchestration failed: {e}")
            return FixResult(
                success=False,
                files_changed=[],
                errors_fixed=0,
                time_taken=asyncio.get_event_loop().time() - start_time,
                details={"fix_type": FixType.LLM_MANUAL, "error": str(e)},
            )

    async def _process_batch(self, errors: list[Error]) -> FixResult:
        """Process a batch of errors using Google Gemini API."""
        if not self.adk_configured or self.client is None:
            logger.warning("Google ADK not configured")
            return FixResult(
                success=False,
                files_changed=[],
                errors_fixed=0,
                time_taken=0.0,
                details={"fix_type": FixType.LLM_MANUAL, "error": "No API client"},
            )

        # Build context
        context = self.context_builder.build_context(errors)

        # Get file content
        file_path = Path(context.file_path)
        try:
            with open(file_path) as f:
                original_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return FixResult(
                success=False,
                files_changed=[],
                errors_fixed=0,
                time_taken=0.0,
                details={"fix_type": FixType.LLM_MANUAL, "error": str(e)},
            )

        # Format prompt for direct code output
        prompt = self._format_direct_fix_prompt(context, original_content)

        # Send to LLM
        start_time = asyncio.get_event_loop().time()
        fixes_applied = 0

        # Get the model and parameters to use for this error type
        model = self._get_model_for_errors(errors)
        model_params = self._get_model_params_for_errors(errors)

        # Log error details
        error_codes = [e.code for e in errors]
        logger.info(f"Sending batch of {len(errors)} errors to {model}")
        logger.debug(f"  Error codes: {', '.join(error_codes)}")
        logger.debug(f"  Prompt size: {len(prompt)} chars")
        logger.debug(
            f"  Model params: temperature={model_params.get('temperature', 0)}, "
            f"max_tokens={model_params.get('max_tokens', 4096)}",
        )

        # Create eval data structure for prompt tuning
        eval_data = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "model_params": model_params,
            "file_path": str(file_path),
            "original_content": original_content,
            "original_line_count": len(original_content.split("\n")),
            "errors": [
                {
                    "line": e.line,
                    "code": e.code,
                    "message": e.message,
                    "priority": e.priority.name,
                }
                for e in errors
            ],
            "prompt_length": len(prompt),
            "prompt": prompt,
            "context_lines": len(context.context_lines),
            "system_prompt": """CONSTITUTIONAL PRINCIPLES:
You are bound by these inviolable principles:
1. PRESERVE: Never remove existing functionality
2. MINIMAL: Make the smallest change that works
3. VALIDATE: Check before and after every operation
4. TRANSPARENT: Explain your reasoning
5. REVERSIBLE: Ensure all changes can be undone
6. HUMBLE: Admit uncertainty and ask for clarification
7. SAFE: Choose the safer option when uncertain

FORBIDDEN ACTIONS:
- Delete without explicit approval
- Modify security or authentication code
- Remove tests or validation
- Change API contracts
- Bypass safety checks

YOUR ROLE: You are an expert Python developer fixing specific code issues. Output
ONLY line numbers and complete fixed lines.

CRITICAL RULES:
1. NEVER replace a for/while loop with just 'pass' - only modify the variable names
2. NEVER replace function definitions with code that belongs inside them
3. For type annotations, ADD the type annotation to the existing line
4. For unused variables (B007), prefix with underscore but KEEP THE ENTIRE LOOP
5. For try-except-pass (S110), add a comment or logging but KEEP THE STRUCTURE
6. PRESERVE ALL CODE LOGIC - only fix the specific issue mentioned""",
        }

        try:
            # Build the request with system instruction and prompt
            contents: list[types.Content] = [
                types.Content(role="user", parts=[types.Part(text=prompt)]),
            ]

            # Configure generation parameters
            generation_config = types.GenerateContentConfig(
                temperature=float(model_params.get("temperature", 0)),
                top_p=float(model_params.get("top_p", 1.0)),
                max_output_tokens=int(model_params.get("max_tokens", 4096)),
                system_instruction=str(eval_data["system_prompt"]),
            )

            # Generate response using the client
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=generation_config,
            )

            # Handle the response from Gemini API
            response_text = response.text or ""
            eval_data["response"] = response_text
            eval_data["response_length"] = len(response_text)

            # Log the response details
            logger.debug(f"=== {model.upper()} RESPONSE ===")
            logger.debug(f"Response length: {len(response_text)} chars")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("First 500 chars of response:")
                logger.debug(response_text[:500])
                if len(response_text) > 500:
                    logger.debug("... (truncated for logging)")

            # Parse the response to get changed lines
            changed_lines = {}
            for line in response_text.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # Skip markdown formatting
                if line.startswith("```") or line == "```":
                    continue

                # Parse format: "42: fixed code here"
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        line_num_str = parts[0].strip()
                        if line_num_str.isdigit():
                            try:
                                line_num = int(line_num_str)
                                changed_lines[line_num] = parts[1].lstrip()
                            except ValueError:
                                logger.warning(
                                    f"Could not parse line number from: {line}"
                                )

            if not changed_lines:
                logger.warning("No fixes were extracted from LLM response")
                logger.debug(f"Raw response was: {response_text[:200]}...")
                return FixResult(
                    success=False,
                    files_changed=[],
                    errors_fixed=0,
                    time_taken=asyncio.get_event_loop().time() - start_time,
                    details={
                        "fix_type": FixType.LLM_MANUAL,
                        "error": "No fixes parsed from response",
                    },
                )

            # Check if this batch contains E402 errors
            has_e402 = any(e.code == "E402" for e in errors)
            imports_to_move = []

            if has_e402:
                # For E402 errors, we need to extract imports from lines being cleared
                for line_num in sorted(changed_lines.keys()):
                    # Check if this line had an E402 error
                    if any(
                        getattr(
                            e, "line", e.get("line") if isinstance(e, dict) else None
                        )
                        == line_num
                        and getattr(
                            e, "code", e.get("code") if isinstance(e, dict) else None
                        )
                        == "E402"
                        for e in errors
                    ):
                        # Get the original line content
                        original_lines_temp = original_content.split("\n")
                        if 1 <= line_num <= len(original_lines_temp):
                            import_line = original_lines_temp[line_num - 1].strip()
                            if import_line.startswith(("import ", "from ")):
                                imports_to_move.append(import_line)
                                logger.info(
                                    f"Will move import from line {line_num}: {import_line}"
                                )

            # Log what we're about to change
            logger.info(f"Applying {len(changed_lines)} line changes:")
            for line_num in sorted(changed_lines.keys()):
                logger.info(f"  Line {line_num}: will be replaced")

            # Apply the changes to the original content
            original_lines = original_content.split("\n")
            eval_data["changes_attempted"] = []

            for line_num, new_code in changed_lines.items():
                if 1 <= line_num <= len(original_lines):
                    old_code = original_lines[line_num - 1]

                    # Preserve original indentation
                    original_indent = len(old_code) - len(old_code.lstrip())
                    indent_chars = old_code[:original_indent]

                    # Apply indentation to the new code if it doesn't have any
                    if new_code and not new_code[0].isspace():
                        new_code = indent_chars + new_code

                    original_lines[line_num - 1] = new_code
                    logger.debug(f"Line {line_num} changed:")
                    logger.debug(
                        f"  OLD: {old_code[:80]}{'...' if len(old_code) > 80 else ''}"
                    )
                    logger.debug(
                        f"  NEW: {new_code[:80]}{'...' if len(new_code) > 80 else ''}"
                    )

                    # Record change for eval
                    if "changes_attempted" not in eval_data:
                        eval_data["changes_attempted"] = []
                    changes_attempted = eval_data["changes_attempted"]
                    if isinstance(changes_attempted, list):
                        changes_attempted.append(
                            {
                                "line": line_num,
                                "old": old_code,
                                "new": new_code,
                                "success": True,
                            },
                        )
                else:
                    logger.warning(
                        f"Line number {line_num} out of range "
                        f"(file has {len(original_lines)} lines)",
                    )
                    if "changes_attempted" not in eval_data:
                        eval_data["changes_attempted"] = []
                    changes_attempted = eval_data["changes_attempted"]
                    if isinstance(changes_attempted, list):
                        changes_attempted.append(
                            {
                                "line": line_num,
                                "old": None,
                                "new": new_code,
                                "success": False,
                                "error": f"Line out of range "
                                f"(file has {len(original_lines)} lines)",
                            },
                        )

            fixed_content = "\n".join(original_lines)

            # If we have E402 imports to move, handle them now
            if imports_to_move:
                logger.info(f"Moving {len(imports_to_move)} imports to top of file")
                fixed_lines = fixed_content.split("\n")

                # Find where to insert imports (after module docstring and initial comments)
                insert_pos = 0
                in_docstring = False
                docstring_delim = None

                for i, line in enumerate(fixed_lines):
                    stripped = line.strip()

                    # Handle module docstrings
                    if i == 0 and (
                        stripped.startswith('"""') or stripped.startswith("'''")
                    ):
                        docstring_delim = '"""' if stripped.startswith('"""') else "'''"
                        if stripped.count(docstring_delim) == 2:
                            # Single line docstring
                            insert_pos = i + 1
                            continue
                        else:
                            in_docstring = True
                            continue

                    if in_docstring:
                        if docstring_delim and docstring_delim in line:
                            in_docstring = False
                            insert_pos = i + 1
                        continue

                    # Skip empty lines and comments at the start
                    if not stripped or stripped.startswith("#"):
                        continue

                    # Found first non-empty, non-comment line
                    if not stripped.startswith(("import ", "from ", "__future__")):
                        insert_pos = i
                        break

                    # Keep going through imports to find the end of import block
                    insert_pos = i + 1

                # Group imports by type
                stdlib_imports = []
                third_party_imports = []
                local_imports = []

                # Common standard library modules
                stdlib_modules = {
                    "os",
                    "sys",
                    "re",
                    "json",
                    "logging",
                    "pathlib",
                    "typing",
                    "datetime",
                    "collections",
                    "itertools",
                    "functools",
                    "asyncio",
                    "threading",
                    "subprocess",
                    "io",
                    "time",
                    "random",
                    "math",
                    "statistics",
                    "decimal",
                    "fractions",
                    "abc",
                    "copy",
                    "pickle",
                    "shelve",
                    "tempfile",
                    "glob",
                    "shutil",
                    "zipfile",
                    "argparse",
                    "configparser",
                    "urllib",
                    "http",
                    "unittest",
                    "doctest",
                    "pdb",
                    "timeit",
                    "trace",
                    "traceback",
                    "warnings",
                    "contextlib",
                    "atexit",
                    "concurrent",
                    "multiprocessing",
                    "socket",
                    "ssl",
                    "select",
                    "signal",
                    "mmap",
                    "csv",
                    "hashlib",
                    "hmac",
                    "secrets",
                    "uuid",
                    "enum",
                    "dataclasses",
                }

                for imp in imports_to_move:
                    if imp.startswith("from .") or imp.startswith("from solve"):
                        local_imports.append(imp)
                    elif imp.startswith("import "):
                        module_name = imp.split()[1].split(".")[0]
                        if module_name in stdlib_modules:
                            stdlib_imports.append(imp)
                        else:
                            third_party_imports.append(imp)
                    elif imp.startswith("from "):
                        module_name = imp.split()[1].split(".")[0]
                        if module_name in stdlib_modules:
                            stdlib_imports.append(imp)
                        elif module_name == "solve":
                            local_imports.append(imp)
                        else:
                            third_party_imports.append(imp)
                    else:
                        # Default to third party for safety
                        third_party_imports.append(imp)

                # Build the import block
                import_block = []
                if stdlib_imports:
                    import_block.extend(sorted(set(stdlib_imports)))
                if third_party_imports:
                    if import_block:
                        import_block.append("")  # Empty line between groups
                    import_block.extend(sorted(set(third_party_imports)))
                if local_imports:
                    if import_block:
                        import_block.append("")  # Empty line between groups
                    import_block.extend(sorted(set(local_imports)))

                # Insert the imports
                if import_block:
                    # Add empty line after imports if the next line isn't empty
                    if (
                        insert_pos < len(fixed_lines)
                        and fixed_lines[insert_pos].strip()
                    ):
                        import_block.append("")

                    # Insert imports at the determined position
                    for imp in reversed(import_block):
                        fixed_lines.insert(insert_pos, imp)

                    fixed_content = "\n".join(fixed_lines)
                    logger.info(
                        f"Moved {len(imports_to_move)} imports to line {insert_pos}"
                    )

            # Write the fixed content
            with open(file_path, "w") as f:
                f.write(fixed_content)

            logger.info(f"Applied {len(changed_lines)} line fixes to {file_path}")
            fixes_applied = len(errors)  # Assume all errors in batch were addressed

            # Run auto-fixers after LLM fixes
            from .models import AutofixConfig
            from .runner import AutoFixerRunner

            config = AutofixConfig()
            runner = AutoFixerRunner(config)
            logger.debug(f"Running auto-fixers on {file_path} after LLM fixes...")
            fix_result = await runner.run_all_fixers([str(file_path)])
            if fix_result.success and fix_result.files_changed:
                logger.debug(
                    f"  Auto-fixers cleaned up {len(fix_result.files_changed)} files"
                )

            if config.enable_auto_fixers and len(fix_result.files_changed) > 0:
                logger.info(
                    f"Auto-fixers made changes to {len(fix_result.files_changed)} files"
                )

            # Validate Python syntax after all fixes
            logger.debug(f"Validating Python syntax for {file_path}...")
            syntax_valid = True
            syntax_error = None
            try:
                with open(file_path) as f:
                    final_content = f.read()

                # Use ast.parse to check syntax
                ast.parse(final_content)
                logger.debug(f"✓ Python syntax is valid for {file_path}")
            except SyntaxError as se:
                syntax_valid = False
                syntax_error = f"Line {se.lineno}: {se.msg}"
                logger.error(
                    f"Syntax error after fixes in {file_path}:{se.lineno}: {se.msg}"
                )
                logger.warning(
                    f"Keeping fixes despite syntax error - {fixes_applied} errors were addressed",
                )
                # Don't restore - keep the fixes even with syntax error
                # This allows us to see which fixes worked and which didn't
                eval_data["syntax_error"] = syntax_error
                eval_data["syntax_valid"] = False

            # Record syntax validation result
            eval_data["syntax_valid"] = syntax_valid
            if not syntax_valid and syntax_error:
                eval_data["partial_success"] = True
                eval_data["fixes_before_syntax_error"] = fixes_applied

            # Run validation to see final state
            if fixes_applied > 0:
                logger.debug("Running validation to check final error state...")
                try:
                    from .validation import validate_files

                    final_validation_dict = await validate_files([str(file_path)])

                    # Convert dict result to ValidationResult-like object for backward compatibility
                    class ValidationResultLike:
                        def __init__(
                            self,
                            errors: list[Any] | None = None,
                            warnings: list[Any] | None = None,
                        ) -> None:
                            self.errors = errors or []
                            self.warnings = warnings or []

                    # Extract errors and warnings from the validation dict
                    final_validation = ValidationResultLike(
                        errors=final_validation_dict.get("errors", []),
                        warnings=final_validation_dict.get("warnings", []),
                    )

                    # Capture the after state
                    eval_data["after_errors"] = [
                        {
                            "line": e.line,
                            "code": e.code,
                            "message": e.message,
                            "file": str(e.file_path),
                        }
                        for e in final_validation.errors
                    ]
                    eval_data["after_warnings"] = [
                        {
                            "line": e.line,
                            "code": e.code,
                            "message": e.message,
                            "file": str(e.file_path),
                        }
                        for e in final_validation.warnings
                    ]

                    # Analyze what changed
                    # Ensure errors are lists before iterating
                    original_errors = eval_data.get("errors", [])
                    after_errors = eval_data.get("after_errors", [])
                    if not isinstance(original_errors, list):
                        original_errors = []
                    if not isinstance(after_errors, list):
                        after_errors = []

                    original_error_codes = {
                        (e["line"], e["code"]) for e in original_errors
                    }
                    final_error_codes = {(e["line"], e["code"]) for e in after_errors}

                    eval_data["errors_fixed"] = list(
                        original_error_codes - final_error_codes
                    )
                    eval_data["errors_remaining"] = list(
                        original_error_codes & final_error_codes
                    )
                    eval_data["errors_introduced"] = list(
                        final_error_codes - original_error_codes
                    )

                    # Safely get lengths with proper type checking
                    errors_fixed = eval_data.get("errors_fixed", [])
                    errors_remaining = eval_data.get("errors_remaining", [])
                    errors_introduced = eval_data.get("errors_introduced", [])

                    errors_fixed_len = (
                        len(errors_fixed) if isinstance(errors_fixed, Sized) else 0
                    )
                    errors_remaining_len = (
                        len(errors_remaining)
                        if isinstance(errors_remaining, Sized)
                        else 0
                    )
                    errors_introduced_len = (
                        len(errors_introduced)
                        if isinstance(errors_introduced, Sized)
                        else 0
                    )

                    logger.info(
                        f"Validation summary: {errors_fixed_len} fixed, "
                        f"{errors_remaining_len} remaining, "
                        f"{errors_introduced_len} introduced",
                    )

                except Exception as e:
                    logger.warning(f"Could not run final validation: {e}")
                    eval_data["after_validation_error"] = str(e)

        except Exception as e:
            logger.error(f"LLM execution failed: {type(e).__name__}: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                import traceback

                logger.debug(f"Traceback:\n{traceback.format_exc()}")
            eval_data["error"] = str(e)
            eval_data["success"] = False
            fixes_applied = 0

        # Save eval data for analysis
        eval_data["fixes_applied"] = fixes_applied
        eval_data["success"] = fixes_applied > 0

        # Capture final content if we made changes
        if fixes_applied > 0:
            try:
                with open(file_path) as f:
                    final_content = f.read()
                    eval_data["final_content"] = final_content
                    eval_data["final_line_count"] = len(final_content.split("\n"))
            except Exception as e:
                eval_data["final_content_error"] = str(e)

        self._save_eval_data(eval_data)

        end_time = asyncio.get_event_loop().time()

        return FixResult(
            success=fixes_applied > 0,
            files_changed=[str(file_path)] if fixes_applied > 0 else [],
            errors_fixed=fixes_applied,
            time_taken=end_time - start_time,
            details={
                "fix_type": FixType.LLM_MANUAL,
                "batch_size": len(errors),
                "model": model,
            },
        )

    def _format_direct_fix_prompt(
        self, context: BatchContext, original_content: str
    ) -> str:
        """Format prompt for direct code output."""
        error_descriptions = []
        for error in context.errors:
            error_descriptions.append(
                f"- Line {error.line}: {error.code} - {error.message}"
            )

        # Format context lines with line numbers
        context_with_numbers = []
        # Parse the context lines to get their original line numbers
        lines = original_content.split("\n")

        # The context_lines are already extracted with their line numbers preserved
        # We need to reconstruct which lines they are
        # Strip newlines from context lines for matching
        line_map = {}
        for i, line in enumerate(lines, 1):
            line_map[line] = i

        # Match context lines to their line numbers
        for ctx_line in context.context_lines:
            # Strip newline for matching
            ctx_line_stripped = ctx_line.rstrip("\n")
            if ctx_line_stripped in line_map:
                line_num = line_map[ctx_line_stripped]
                context_with_numbers.append(f"{line_num:4}: {ctx_line_stripped}")

        # If we couldn't match lines, fall back to showing context without numbers
        if not context_with_numbers:
            for line in context.context_lines:
                context_with_numbers.append(f"     {line.rstrip()}")

        # Ensure all error lines are shown, even if not in context
        error_lines_shown = {
            int(line.split(":")[0].strip())
            for line in context_with_numbers
            if ":" in line
        }
        for error in context.errors:
            if error.line not in error_lines_shown and 1 <= error.line <= len(lines):
                # Add the error line to the context
                error_line_content = lines[error.line - 1]
                context_with_numbers.append(f"{error.line:4}: {error_line_content}")

        # Sort context by line number
        context_with_numbers.sort(
            key=lambda x: int(x.split(":")[0].strip()) if ":" in x else 0
        )

        # Group errors by type for better prompting
        errors_by_type: dict[str, list[Error]] = {}
        for error in context.errors:
            if error.code not in errors_by_type:
                errors_by_type[error.code] = []
            errors_by_type[error.code].append(error)

        # Build specific instructions based on error types using prompt loader
        instructions = []
        examples = []

        for error_code in errors_by_type:
            # Try to load prompt from file
            if self.prompt_loader.has_prompt(error_code):
                # Get instructions from the prompt file
                instruction = self.prompt_loader.get_instructions(error_code)
                if instruction:
                    instructions.append(f"- For {error_code} errors:")
                    for line in instruction.split("\n"):
                        instructions.append(f"  {line}")

                # Get examples from the prompt file
                prompt_examples = self.prompt_loader.get_examples(error_code)
                examples.extend(prompt_examples)
            else:
                # Fallback to hardcoded instructions for error types without prompt files
                if error_code == "F401":
                    instructions.append(
                        "- For F401 errors: Remove the unused import line"
                    )
                    examples.append("5: # Line removed (was unused import)")
                elif error_code == "arg-type":
                    instructions.append(
                        "- For arg-type errors: Fix the type mismatch or add type annotation",
                    )
                else:
                    instructions.append(
                        f"- For {error_code} errors: Fix according to the error message",
                    )

        return f"""Fix the following Python errors:

{chr(10).join(error_descriptions)}

Code context showing the error locations:
```python
{chr(10).join(context_with_numbers)}
```

ERROR-SPECIFIC INSTRUCTIONS:
{chr(10).join(instructions)}

OUTPUT FORMAT:
- For each line that needs changes, output: line_number: complete_fixed_line
- Only output lines that actually need changes
- Do not add explanations or comments
- For function definitions missing return types, add the return type before the colon

EXAMPLES:
{chr(10).join(examples)}

Output the fixes below:"""

    def _save_eval_data(self, eval_data: dict[str, Any]) -> None:
        """Save evaluation data for prompt tuning and analysis."""
        try:
            # Save using the new eval storage framework
            saved_path = self.eval_adapter.save_autofix_eval(
                eval_data, StorageFormat.JSON
            )
            logger.info(f"Saved LLM eval data to {saved_path}")

            # Also maintain backward compatibility by saving to legacy location
            # This ensures existing tools can still read the data
            legacy_dir = Path(".solve/eval/results/llm")
            if legacy_dir.exists():
                # Create filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                legacy_file = legacy_dir / f"eval_{timestamp}.json"

                # Save the eval data in legacy format
                with open(legacy_file, "w") as f:
                    json.dump(eval_data, f, indent=2)

                # Also append to master eval log
                master_log = legacy_dir / "all_evals.jsonl"
                with open(master_log, "a") as f:
                    f.write(json.dumps(eval_data) + "\n")

                logger.debug(f"Also saved to legacy location: {legacy_file}")

        except Exception as e:
            logger.warning(f"Could not save eval data: {e}")

    def _load_llm_fix_config(self) -> dict[str, Any]:
        """Load LLM fix configuration from JSON file."""
        config_path = Path(__file__).parent / "llm_fix_config.json"
        try:
            with open(config_path) as f:
                config = json.load(f)
                logger.info(
                    f"Loaded LLM fix config: {config.get('enabled_errors_count')} "
                    f"error types enabled",
                )
                return dict(config)
        except FileNotFoundError:
            logger.warning(
                f"LLM fix config not found at {config_path}, using default (all enabled)",
            )
            return {"llm_fixable_error_types": {}, "default_enabled": True}
        except Exception as e:
            logger.error(f"Error loading LLM fix config: {e}")
            return {"llm_fixable_error_types": {}, "default_enabled": True}

    def _filter_enabled_errors(self, errors: list[Error]) -> list[Error]:
        """Filter errors based on LLM fix configuration."""
        if not self.llm_fix_config:
            return errors

        error_types = self.llm_fix_config.get("llm_fixable_error_types", {})
        default_enabled = self.llm_fix_config.get("default_enabled", False)

        enabled_errors = []
        disabled_by_type: dict[str, int] = {}

        for error in errors:
            error_code = error.code

            # Check if this error type is in our config
            if error_code in error_types:
                if error_types[error_code].get("enabled", default_enabled):
                    enabled_errors.append(error)
                else:
                    disabled_by_type[error_code] = (
                        disabled_by_type.get(error_code, 0) + 1
                    )
            elif default_enabled:
                # Not in config, use default
                enabled_errors.append(error)
            else:
                # Not in config and default is disabled
                disabled_by_type[error_code] = disabled_by_type.get(error_code, 0) + 1

        # Log what we filtered out
        if disabled_by_type:
            for error_type, count in disabled_by_type.items():
                reason = error_types.get(error_type, {}).get(
                    "description", "Not in config"
                )
                logger.info(f"Filtered out {count} {error_type} errors: {reason}")

        return enabled_errors

    def _get_model_for_errors(self, errors: list[Error]) -> str:
        """Get the appropriate model for a batch of errors."""
        if not errors:
            default_model = self.llm_fix_config.get(
                "default_model", "claude-3-haiku-20240307"
            )
            return (
                str(default_model)
                if default_model is not None
                else "claude-3-haiku-20240307"
            )

        # Get all unique error codes in the batch
        error_codes = {e.code for e in errors}

        # If batch has multiple error types, use the model for the most complex one
        models = []
        for error_code in error_codes:
            error_config = self.llm_fix_config.get("llm_fixable_error_types", {}).get(
                error_code,
                {},
            )
            if "model" in error_config:
                models.append(error_config["model"])

        # Return the first model found, or default
        if models:
            model = models[0]
            return str(model) if model is not None else "claude-3-haiku-20240307"
        default_model = self.llm_fix_config.get(
            "default_model", "claude-3-haiku-20240307"
        )
        return (
            str(default_model)
            if default_model is not None
            else "claude-3-haiku-20240307"
        )

    def _get_model_params_for_errors(self, errors: list[Error]) -> dict[str, Any]:
        """Get the model parameters for a batch of errors."""
        if not errors:
            default_params = self.llm_fix_config.get(
                "default_model_params",
                {"max_tokens": 4096, "temperature": 0},
            )
            return (
                dict(default_params)
                if default_params is not None
                else {"max_tokens": 4096, "temperature": 0}
            )

        # Get the first error code's params (assuming homogeneous batch)
        error_code = errors[0].code
        error_config = self.llm_fix_config.get("llm_fixable_error_types", {}).get(
            error_code, {}
        )

        if "model_params" in error_config:
            params = error_config["model_params"]
            return (
                dict(params)
                if params is not None
                else {"max_tokens": 4096, "temperature": 0}
            )
        default_params = self.llm_fix_config.get(
            "default_model_params",
            {"max_tokens": 4096, "temperature": 0},
        )
        return (
            dict(default_params)
            if default_params is not None
            else {"max_tokens": 4096, "temperature": 0}
        )
