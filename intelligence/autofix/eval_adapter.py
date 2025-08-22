"""Adapter for integrating autofix evaluation data with the SOLVE evaluation storage framework.

This module provides conversion between autofix's evaluation data format and the
standardized EvaluationResult format used by the eval storage system.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import EVAL_BASE_DIR, ensure_eval_directories

# Import from eval package storage module
try:
    from eval.storage import EvaluationResult, ResultStorage, StorageFormat
except ImportError:
    # Fallback for development environment
    import os
    import sys

    eval_path = os.path.join(os.path.dirname(__file__), "../../../eval/src")
    if os.path.exists(eval_path):
        sys.path.insert(0, eval_path)
        from eval.storage import EvaluationResult, ResultStorage, StorageFormat
    else:
        raise ImportError(
            "Cannot import eval.storage module. Ensure eval package is installed.",
        ) from None

logger = logging.getLogger(__name__)


class AutofixEvalAdapter:
    """Adapter for converting autofix evaluation data to the standard format."""

    def __init__(self, storage: ResultStorage | None = None):
        """Initialize the adapter.

        Args:
            storage: Optional ResultStorage instance. If not provided, creates one.
        """
        if storage is None:
            ensure_eval_directories()
            self.storage = ResultStorage(EVAL_BASE_DIR)
        else:
            self.storage = storage

        # Legacy paths for backward compatibility
        self.legacy_eval_dir = Path(".solve/eval/results/llm")
        self.legacy_master_log = self.legacy_eval_dir / "all_evals.jsonl"

    def convert_autofix_to_evaluation_result(
        self,
        autofix_data: dict[str, Any],
        run_id: str | None = None,
    ) -> EvaluationResult:
        """Convert autofix evaluation data to EvaluationResult format.

        Args:
            autofix_data: Autofix evaluation data dictionary
            run_id: Optional run ID. If not provided, generates one.

        Returns:
            EvaluationResult instance
        """
        # Generate run_id if not provided
        if run_id is None:
            run_id = str(uuid.uuid4())

        # Extract timestamp
        timestamp_str = autofix_data.get("timestamp", datetime.now().isoformat())
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = datetime.now()

        # Extract model information
        model_name = autofix_data.get("model", "unknown")
        model_params = autofix_data.get("model_params", {})

        # Build dataset name from file path
        file_path = autofix_data.get("file_path", "unknown")
        dataset_name = f"autofix_{Path(file_path).stem}"

        # Convert errors to test case results
        errors = autofix_data.get("errors", [])
        results = []
        for i, error in enumerate(errors):
            result = {
                "test_id": f"error_{i}_{error.get('code', 'unknown')}",
                "input": {
                    "line": error.get("line", 0),
                    "code": error.get("code", ""),
                    "message": error.get("message", ""),
                    "priority": error.get("priority", "MEDIUM"),
                },
                "expected": "fixed",
                "actual": "fixed" if autofix_data.get("success", False) else "unfixed",
                "success": autofix_data.get("success", False),
                "metadata": {
                    "error_type": error.get("code", ""),
                    "fix_attempted": True,
                },
            }
            results.append(result)

        # Extract changes attempted
        changes_attempted = autofix_data.get("changes_attempted", [])

        # Calculate metrics
        total_errors = len(errors)
        fixes_applied = autofix_data.get("fixes_applied", 0)
        success_rate = fixes_applied / total_errors if total_errors > 0 else 0.0

        metrics = {
            "total_errors": total_errors,
            "fixes_applied": fixes_applied,
            "success_rate": success_rate,
            "prompt_length": autofix_data.get("prompt_length", 0),
            "response_length": autofix_data.get("response_length", 0),
            "changes_attempted": len(changes_attempted),
        }

        # Build config
        config = {
            "model": model_name,
            "model_params": model_params,
            "system_prompt": autofix_data.get("system_prompt", ""),
            "context_lines": autofix_data.get("context_lines", 0),
        }

        # Build metadata
        metadata = {
            "file_path": file_path,
            "original_line_count": autofix_data.get("original_line_count", 0),
            "changes_attempted": changes_attempted,
            "error": autofix_data.get("error"),
            "autofix_eval": True,  # Mark as autofix evaluation
        }

        # Store full prompt and response in metadata if present
        if "prompt" in autofix_data:
            metadata["prompt"] = autofix_data["prompt"]
        if "response" in autofix_data:
            metadata["response"] = autofix_data["response"]

        return EvaluationResult(
            run_id=run_id,
            dataset_name=dataset_name,
            dataset_version="1.0",  # Default version for autofix
            timestamp=timestamp,
            model_name=model_name,
            model_version=None,
            results=results,
            metrics=metrics,
            config=config,
            metadata=metadata,
        )

    def save_autofix_eval(
        self,
        autofix_data: dict[str, Any],
        format: StorageFormat = StorageFormat.JSON,
    ) -> Path:
        """Save autofix evaluation data in the new storage format.

        Args:
            autofix_data: Autofix evaluation data
            format: Storage format to use

        Returns:
            Path to saved file
        """
        # Convert to EvaluationResult
        eval_result = self.convert_autofix_to_evaluation_result(autofix_data)

        # Save using ResultStorage
        return self.storage.save_result(eval_result, format)

    def load_legacy_evals(self) -> list[EvaluationResult]:
        """Load and convert legacy autofix evaluation data.

        Returns:
            List of converted EvaluationResult instances
        """
        results: list[EvaluationResult] = []

        if not self.legacy_master_log.exists():
            return results

        # Read legacy JSONL file
        with open(self.legacy_master_log) as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    eval_result = self.convert_autofix_to_evaluation_result(data)
                    results.append(eval_result)
                except Exception as e:
                    logger.debug(f"Skipping malformed line in legacy JSONL: {e}")
                    # Continue with next line

        return results

    def migrate_legacy_data(self) -> int:
        """Migrate legacy autofix evaluation data to new storage format.

        Returns:
            Number of evaluations migrated
        """
        legacy_evals = self.load_legacy_evals()

        migrated = 0
        for eval_result in legacy_evals:
            try:
                self.storage.save_result(eval_result)
                migrated += 1
            except Exception as e:
                logger.warning(f"Failed to migrate evaluation result: {e}")
                # Continue with next result

        return migrated

    def query_autofix_evals(
        self,
        file_path: str | None = None,
        model_name: str | None = None,
        error_code: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Query autofix evaluation results with autofix-specific filters.

        Args:
            file_path: Filter by file path
            model_name: Filter by model name
            error_code: Filter by error code
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of matching evaluation summaries
        """
        # Get all results using base filters
        all_results = self.storage.list_results(
            model_name=model_name,
            start_date=start_date,
            end_date=end_date,
        )

        # Apply autofix-specific filters
        filtered_results = []
        for result_summary in all_results:
            # Load full result to check metadata
            result = self.storage.load_result(result_summary["path"])

            # Check if this is an autofix evaluation
            if not result.metadata.get("autofix_eval", False):
                continue

            # Apply file path filter
            if file_path and result.metadata.get("file_path") != file_path:
                continue

            # Apply error code filter
            if error_code:
                # Check if any error in the results matches the code
                has_error_code = any(
                    r["input"].get("code") == error_code for r in result.results
                )
                if not has_error_code:
                    continue

            # Add autofix-specific fields to summary
            result_summary["file_path"] = result.metadata.get("file_path")
            result_summary["error_count"] = result.metrics.get("total_errors", 0)
            result_summary["fixes_applied"] = result.metrics.get("fixes_applied", 0)
            result_summary["success_rate"] = result.metrics.get("success_rate", 0)

            filtered_results.append(result_summary)

        return filtered_results

    def get_error_fix_statistics(self) -> dict[str, dict[str, Any]]:
        """Get statistics about error fixes across all evaluations.

        Returns:
            Dictionary mapping error codes to fix statistics
        """
        stats: dict[str, dict[str, Any]] = {}

        # Get all autofix evaluations
        autofix_evals = self.query_autofix_evals()

        for eval_summary in autofix_evals:
            # Load full result
            result = self.storage.load_result(eval_summary["path"])

            # Process each error
            for test_result in result.results:
                error_code = test_result["input"].get("code", "unknown")

                if error_code not in stats:
                    stats[error_code] = {
                        "total_occurrences": 0,
                        "successful_fixes": 0,
                        "failed_fixes": 0,
                        "fix_rate": 0.0,
                        "models_used": set(),
                    }

                total_occ = stats[error_code]["total_occurrences"]
                stats[error_code]["total_occurrences"] = total_occ + 1
                if test_result["success"]:
                    successful = stats[error_code]["successful_fixes"]
                    stats[error_code]["successful_fixes"] = successful + 1
                else:
                    failed = stats[error_code]["failed_fixes"]
                    stats[error_code]["failed_fixes"] = failed + 1

                models_set = stats[error_code]["models_used"]
                models_set.add(result.model_name)

        # Calculate fix rates and convert sets to lists
        for _error_code, error_stats in stats.items():
            total_occurrences = error_stats["total_occurrences"]
            if total_occurrences > 0:
                successful_fixes = error_stats["successful_fixes"]
                error_stats["fix_rate"] = successful_fixes / total_occurrences
            models_used_set = error_stats["models_used"]
            error_stats["models_used"] = list(models_used_set)

        return stats
