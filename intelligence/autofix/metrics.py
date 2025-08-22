"""
Metrics collection and reporting for autofix operations.

This module tracks performance metrics, costs, and effectiveness of the
three-stage autofix pipeline for continuous improvement.
"""

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""

    AUTOFIX_STAGE1 = "autofix_stage1"
    VALIDATION_STAGE2 = "validation_stage2"
    LLM_STAGE3 = "llm_stage3"
    BACKUP_OPERATION = "backup_operation"
    OVERALL_PIPELINE = "overall_pipeline"


@dataclass
class MetricEntry:
    """A single metric entry."""

    timestamp: datetime
    metric_type: MetricType
    operation_id: str
    data: dict[str, Any]
    success: bool
    duration_seconds: float
    error_message: str | None = None


@dataclass
class AutofixMetrics:
    """Metrics for automated fixing (Stage 1)."""

    fixes_applied: int
    files_processed: int
    tools_used: list[str]
    iterations: int
    time_per_iteration: list[float]
    errors_before: int
    errors_after: int


@dataclass
class ValidationMetrics:
    """Metrics for validation (Stage 2)."""

    validators_run: list[str]
    errors_found: int
    errors_by_type: dict[str, int]
    errors_by_file: dict[str, int]
    validation_time: float
    tools_failed: list[str]


@dataclass
class LLMMetrics:
    """Metrics for LLM-powered fixes (Stage 3)."""

    batches_processed: int
    errors_per_batch: list[int]
    tokens_used: int
    estimated_cost: float
    llm_response_time: list[float]
    fixes_applied: int
    fix_success_rate: float
    context_size_chars: list[int]


@dataclass
class PipelineMetrics:
    """Overall pipeline metrics."""

    total_time: float
    stage1_time: float
    stage2_time: float
    stage3_time: float
    initial_error_count: int
    final_error_count: int
    cost_savings: float
    backup_size_bytes: int


class MetricsCollector:
    """Collects and manages autofix metrics."""

    def __init__(self, metrics_dir: Path | None = None):
        self.metrics_dir = metrics_dir or Path.cwd() / ".solve" / "metrics"
        self.metrics_file = self.metrics_dir / "autofix_metrics.json"
        self.session_metrics: list[MetricEntry] = []

        # Create metrics directory
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        # Token cost estimates (as of 2024)
        self.token_costs = {
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},  # per 1K tokens
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        }

    def start_operation(self, operation_id: str, metric_type: MetricType) -> datetime:
        """Start tracking an operation."""
        start_time = datetime.now()
        logger.debug(f"Started tracking {metric_type.value} operation: {operation_id}")
        return start_time

    def record_autofix_stage1(
        self,
        operation_id: str,
        start_time: datetime,
        metrics: AutofixMetrics,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Record Stage 1 autofix metrics."""
        duration = (datetime.now() - start_time).total_seconds()

        entry = MetricEntry(
            timestamp=start_time,
            metric_type=MetricType.AUTOFIX_STAGE1,
            operation_id=operation_id,
            data=asdict(metrics),
            success=success,
            duration_seconds=duration,
            error_message=error_message,
        )

        self.session_metrics.append(entry)
        logger.info(
            f"Stage 1 autofix: {metrics.fixes_applied} fixes in {duration:.2f}s"
        )

    def record_validation_stage2(
        self,
        operation_id: str,
        start_time: datetime,
        metrics: ValidationMetrics,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Record Stage 2 validation metrics."""
        duration = (datetime.now() - start_time).total_seconds()

        entry = MetricEntry(
            timestamp=start_time,
            metric_type=MetricType.VALIDATION_STAGE2,
            operation_id=operation_id,
            data=asdict(metrics),
            success=success,
            duration_seconds=duration,
            error_message=error_message,
        )

        self.session_metrics.append(entry)
        logger.info(
            f"Stage 2 validation: {metrics.errors_found} errors found in {duration:.2f}s"
        )

    def record_llm_stage3(
        self,
        operation_id: str,
        start_time: datetime,
        metrics: LLMMetrics,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Record Stage 3 LLM metrics."""
        duration = (datetime.now() - start_time).total_seconds()

        entry = MetricEntry(
            timestamp=start_time,
            metric_type=MetricType.LLM_STAGE3,
            operation_id=operation_id,
            data=asdict(metrics),
            success=success,
            duration_seconds=duration,
            error_message=error_message,
        )

        self.session_metrics.append(entry)
        logger.info(
            f"Stage 3 LLM: {metrics.fixes_applied} fixes, ${metrics.estimated_cost:.4f} cost",
        )

    def record_pipeline_metrics(
        self,
        operation_id: str,
        start_time: datetime,
        metrics: PipelineMetrics,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Record overall pipeline metrics."""
        duration = (datetime.now() - start_time).total_seconds()

        entry = MetricEntry(
            timestamp=start_time,
            metric_type=MetricType.OVERALL_PIPELINE,
            operation_id=operation_id,
            data=asdict(metrics),
            success=success,
            duration_seconds=duration,
            error_message=error_message,
        )

        self.session_metrics.append(entry)

        # Calculate improvement percentage
        if metrics.initial_error_count > 0:
            improvement = (
                (metrics.initial_error_count - metrics.final_error_count)
                / metrics.initial_error_count
                * 100
            )
        else:
            improvement = 0

        logger.info(
            f"Pipeline complete: {improvement:.1f}% improvement, ${metrics.cost_savings:.2f} saved",
        )

    def record_fix(self, file_path: str, fix_type: str, time_taken: float) -> None:
        """Record a single fix operation.

        Args:
            file_path: Path to the file that was fixed
            fix_type: Type of fix applied (e.g., "whitespace", "imports")
            time_taken: Time taken to apply the fix in seconds
        """
        # Store fix in session for later aggregation
        if not hasattr(self, "_individual_fixes"):
            self._individual_fixes: list[dict[str, Any]] = []

        self._individual_fixes.append(
            {
                "file_path": file_path,
                "fix_type": fix_type,
                "time_taken": time_taken,
                "timestamp": datetime.now(),
            },
        )

        logger.debug(f"Recorded fix: {fix_type} on {file_path} ({time_taken:.3f}s)")

    def get_total_fixes(self) -> int:
        """Get the total number of fixes recorded.

        Returns:
            Total number of fixes
        """
        if hasattr(self, "_individual_fixes"):
            individual_fixes: list[dict[str, Any]] = self._individual_fixes
            return len(individual_fixes)
        return 0

    def generate_report(self) -> dict[str, Any]:
        """Generate a report of all metrics collected.

        Returns:
            A dictionary containing various metrics and statistics
        """
        report: dict[str, Any] = {
            "total_fixes": self.get_total_fixes(),
            "session_metrics": len(self.session_metrics),
            "metrics_by_type": defaultdict(int),
        }

        # Count metrics by type
        metrics_by_type = report["metrics_by_type"]
        for metric in self.session_metrics:
            metrics_by_type[metric.metric_type.value] += 1

        # Add individual fix details if available
        if hasattr(self, "_individual_fixes"):
            fix_types: dict[str, int] = defaultdict(int)
            total_time = 0.0
            individual_fixes: list[dict[str, Any]] = self._individual_fixes
            for fix in individual_fixes:
                fix_types[fix["fix_type"]] += 1
                total_time += fix["time_taken"]

            report["fix_types"] = dict(fix_types)
            report["total_fix_time"] = total_time
            report["average_fix_time"] = (
                total_time / len(individual_fixes) if individual_fixes else 0
            )

        return report

    def record_llm_fixes(
        self, fixes_applied: int, time_taken: float, backup_id: str
    ) -> None:
        """Record LLM fixes (simplified interface)."""
        metrics = LLMMetrics(
            batches_processed=1,
            errors_per_batch=[fixes_applied],
            tokens_used=0,  # Would be calculated from actual LLM response
            estimated_cost=0.0,
            llm_response_time=[time_taken],
            fixes_applied=fixes_applied,
            fix_success_rate=1.0 if fixes_applied > 0 else 0.0,
            context_size_chars=[1000],  # Placeholder
        )

        self.record_llm_stage3(
            operation_id=backup_id,
            start_time=datetime.now() - timedelta(seconds=time_taken),
            metrics=metrics,
            success=fixes_applied > 0,
        )

    def estimate_llm_cost(
        self, tokens_used: int, model: str = "claude-3-sonnet"
    ) -> float:
        """Estimate LLM cost based on token usage."""
        if model not in self.token_costs:
            logger.warning(f"Unknown model for cost estimation: {model}")
            return 0.0

        # Assume 80% input, 20% output tokens
        input_tokens = int(tokens_used * 0.8)
        output_tokens = int(tokens_used * 0.2)

        costs = self.token_costs[model]
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]

        return input_cost + output_cost

    def calculate_cost_savings(self, errors_fixed_by_stage: dict[str, int]) -> float:
        """Calculate cost savings from using free tools vs LLM."""
        # Estimate cost if all errors were sent to LLM
        total_errors = sum(errors_fixed_by_stage.values())
        llm_errors = errors_fixed_by_stage.get("llm", 0)
        free_errors = total_errors - llm_errors

        # Estimate 500 tokens per error for LLM processing
        tokens_per_error = 500
        cost_per_error = self.estimate_llm_cost(tokens_per_error)

        # Savings = cost we would have paid for free fixes
        savings = free_errors * cost_per_error

        return savings

    async def save_metrics(self) -> None:
        """Save session metrics to file."""
        try:
            existing_metrics = await self._load_metrics()
            all_metrics = existing_metrics + self.session_metrics

            # Convert to JSON-serializable format
            data = []
            for metric in all_metrics:
                item = asdict(metric)
                item["timestamp"] = metric.timestamp.isoformat()
                item["metric_type"] = metric.metric_type.value
                data.append(item)

            with open(self.metrics_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(
                f"Saved {len(self.session_metrics)} metrics to {self.metrics_file}"
            )
            self.session_metrics.clear()

        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    async def get_metrics_summary(self, days: int = 7) -> dict[str, Any]:
        """Get summary of metrics for the last N days."""
        try:
            all_metrics = await self._load_metrics()

            # Filter by date
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_metrics = [m for m in all_metrics if m.timestamp > cutoff_date]

            if not recent_metrics:
                return {"message": "No metrics found for the specified period"}

            # Aggregate metrics
            operations_by_type: dict[str, int] = defaultdict(int)
            summary: dict[str, Any] = {
                "period_days": days,
                "total_operations": len(recent_metrics),
                "operations_by_type": operations_by_type,
                "success_rate": 0.0,
                "average_duration": 0.0,
                "stage_performance": {},
                "cost_metrics": {},
                "error_reduction": {},
            }

            # Calculate aggregations
            successful_ops = 0
            total_duration = 0.0

            for metric in recent_metrics:
                operations_by_type[metric.metric_type.value] += 1
                if metric.success:
                    successful_ops += 1
                total_duration += metric.duration_seconds

            summary["success_rate"] = successful_ops / len(recent_metrics) * 100
            summary["average_duration"] = total_duration / len(recent_metrics)

            # Stage-specific metrics
            for stage in [
                MetricType.AUTOFIX_STAGE1,
                MetricType.VALIDATION_STAGE2,
                MetricType.LLM_STAGE3,
            ]:
                stage_metrics = [m for m in recent_metrics if m.metric_type == stage]
                if stage_metrics:
                    avg_duration = sum(m.duration_seconds for m in stage_metrics) / len(
                        stage_metrics,
                    )
                    success_rate = (
                        sum(1 for m in stage_metrics if m.success)
                        / len(stage_metrics)
                        * 100
                    )
                    stage_performance = summary["stage_performance"]
                    stage_performance[stage.value] = {
                        "avg_duration": avg_duration,
                        "success_rate": success_rate,
                        "operations": len(stage_metrics),
                    }

            return summary

        except Exception as e:
            logger.error(f"Failed to generate metrics summary: {e}")
            return {"error": str(e)}

    async def _load_metrics(self) -> list[MetricEntry]:
        """Load all metrics from file."""
        try:
            if not self.metrics_file.exists():
                return []

            with open(self.metrics_file) as f:
                data = json.load(f)

            metrics = []
            for item in data:
                # Convert timestamp string back to datetime
                item["timestamp"] = datetime.fromisoformat(item["timestamp"])
                item["metric_type"] = MetricType(item["metric_type"])
                metrics.append(MetricEntry(**item))

            return metrics

        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
            return []
