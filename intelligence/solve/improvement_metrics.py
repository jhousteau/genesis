"""
Improvement Metrics and Reporting System for SOLVE Methodology

This module implements comprehensive metrics tracking for the lesson capture
and template evolution system as specified in Issue #80.

Features:
- Lesson capture metrics and trends
- Template evolution effectiveness tracking
- Cost impact analysis
- Pattern detection and frequency analysis
- Performance improvement measurement
- Dashboard-ready reporting
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from solve.lesson_capture_system import (EnhancedLesson, ImpactLevel,
                                         LessonSource, LessonStore)
from solve.template_evolution import TemplateRegistry

logger = logging.getLogger(__name__)


@dataclass
class MetricsTrend:
    """Represents a trend in metrics over time."""

    period: str  # daily, weekly, monthly
    current_value: float
    previous_value: float
    change_percentage: float
    direction: str  # up, down, stable

    def __post_init__(self):
        if self.previous_value == 0:
            self.change_percentage = 100.0 if self.current_value > 0 else 0.0
        else:
            self.change_percentage = (
                (self.current_value - self.previous_value) / self.previous_value
            ) * 100

        if abs(self.change_percentage) < 5:
            self.direction = "stable"
        elif self.change_percentage > 0:
            self.direction = "up"
        else:
            self.direction = "down"


@dataclass
class ImprovementMetrics:
    """Comprehensive improvement metrics."""

    # Lesson metrics
    lessons_captured: int = 0
    lessons_by_source: Dict[str, int] = field(default_factory=dict)
    lessons_by_category: Dict[str, int] = field(default_factory=dict)
    lessons_by_impact: Dict[str, int] = field(default_factory=dict)

    # Template metrics
    templates_improved: int = 0
    template_versions_created: int = 0
    templates_by_type: Dict[str, int] = field(default_factory=dict)

    # Issue reduction metrics
    issue_reduction: Dict[str, float] = field(default_factory=dict)

    # Performance metrics
    time_saved_hours: float = 0.0
    cost_avoided_dollars: float = 0.0

    # Pattern metrics
    top_patterns: List[Dict[str, Any]] = field(default_factory=list)
    most_effective_lessons: List[Dict[str, Any]] = field(default_factory=list)

    # Trends
    trends: Dict[str, MetricsTrend] = field(default_factory=dict)

    # Metadata
    reporting_period: str = ""
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/JSON serialization."""
        return {
            "lessons_captured": self.lessons_captured,
            "lessons_by_source": self.lessons_by_source,
            "lessons_by_category": self.lessons_by_category,
            "lessons_by_impact": self.lessons_by_impact,
            "templates_improved": self.templates_improved,
            "template_versions_created": self.template_versions_created,
            "templates_by_type": self.templates_by_type,
            "issue_reduction": self.issue_reduction,
            "time_saved_hours": self.time_saved_hours,
            "cost_avoided_dollars": self.cost_avoided_dollars,
            "top_patterns": self.top_patterns,
            "most_effective_lessons": self.most_effective_lessons,
            "trends": {
                k: {
                    "period": v.period,
                    "current_value": v.current_value,
                    "previous_value": v.previous_value,
                    "change_percentage": v.change_percentage,
                    "direction": v.direction,
                }
                for k, v in self.trends.items()
            },
            "reporting_period": self.reporting_period,
            "generated_at": self.generated_at.isoformat(),
        }


class ImprovementMetricsCalculator:
    """Calculates improvement metrics from lessons and templates."""

    def __init__(self, lesson_store: LessonStore, template_registry: TemplateRegistry):
        self.lesson_store = lesson_store
        self.template_registry = template_registry

        # Cost calculation constants (rough estimates)
        self.COST_PER_AUTOFIX_INCIDENT = 50.0  # Developer time
        self.COST_PER_DEPLOYMENT_FAILURE = 500.0  # Downtime + recovery
        self.COST_PER_PRODUCTION_INCIDENT = 2000.0  # Business impact

        # Time calculation constants (hours)
        self.TIME_PER_AUTOFIX_INCIDENT = 0.5
        self.TIME_PER_DEPLOYMENT_FAILURE = 2.0
        self.TIME_PER_PRODUCTION_INCIDENT = 8.0

    async def calculate_metrics(
        self, reporting_period: str = "30_days"
    ) -> ImprovementMetrics:
        """Calculate comprehensive improvement metrics."""
        logger.info(f"Calculating improvement metrics for period: {reporting_period}")

        # Parse reporting period
        days_back = self._parse_reporting_period(reporting_period)

        # Load data
        lessons = await self.lesson_store.load_lessons(days_back=days_back)
        await self.template_registry.load_templates()

        # Calculate metrics
        metrics = ImprovementMetrics(reporting_period=reporting_period)

        await self._calculate_lesson_metrics(metrics, lessons)
        await self._calculate_template_metrics(metrics)
        await self._calculate_reduction_metrics(metrics, lessons, days_back)
        await self._calculate_pattern_metrics(metrics, lessons)
        await self._calculate_trends(metrics, days_back)

        logger.info("Improvement metrics calculation completed")
        return metrics

    def _parse_reporting_period(self, period: str) -> int:
        """Parse reporting period string to days."""
        period_map = {
            "7_days": 7,
            "14_days": 14,
            "30_days": 30,
            "60_days": 60,
            "90_days": 90,
        }
        return period_map.get(period, 30)

    async def _calculate_lesson_metrics(
        self, metrics: ImprovementMetrics, lessons: List[EnhancedLesson]
    ) -> None:
        """Calculate lesson-related metrics."""
        metrics.lessons_captured = len(lessons)

        # Group by source
        by_source = defaultdict(int)
        by_category = defaultdict(int)
        by_impact = defaultdict(int)

        for lesson in lessons:
            by_source[lesson.source.value] += 1
            by_category[lesson.category.value] += 1
            by_impact[lesson.impact.value] += 1

        metrics.lessons_by_source = dict(by_source)
        metrics.lessons_by_category = dict(by_category)
        metrics.lessons_by_impact = dict(by_impact)

    async def _calculate_template_metrics(self, metrics: ImprovementMetrics) -> None:
        """Calculate template-related metrics."""
        templates = self.template_registry.templates

        metrics.templates_improved = len(
            [t for t in templates.values() if t.version > 1]
        )
        metrics.template_versions_created = sum(
            t.version - 1 for t in templates.values()
        )

        # Group by template type
        by_type = defaultdict(int)
        for template in templates.values():
            if template.version > 1:  # Only count improved templates
                by_type[template.template_type] += 1

        metrics.templates_by_type = dict(by_type)

    async def _calculate_reduction_metrics(
        self, metrics: ImprovementMetrics, lessons: List[EnhancedLesson], days_back: int
    ) -> None:
        """Calculate issue reduction metrics."""
        # Compare current period with previous period
        current_period_start = datetime.now() - timedelta(days=days_back)
        previous_period_start = current_period_start - timedelta(days=days_back)
        previous_period_end = current_period_start

        # Load lessons from previous period for comparison
        all_lessons = await self.lesson_store.load_lessons(days_back=days_back * 2)

        current_lessons = [
            lesson for lesson in all_lessons if lesson.timestamp >= current_period_start
        ]
        previous_lessons = [
            lesson
            for lesson in all_lessons
            if previous_period_start <= lesson.timestamp < previous_period_end
        ]

        # Calculate reductions by source
        reductions = {}

        for source in LessonSource:
            current_count = len(
                [lesson for lesson in current_lessons if lesson.source == source]
            )
            previous_count = len(
                [lesson for lesson in previous_lessons if lesson.source == source]
            )

            if previous_count > 0:
                reduction = ((previous_count - current_count) / previous_count) * 100
                reductions[source.value] = round(reduction, 1)
            else:
                reductions[source.value] = 0.0

        metrics.issue_reduction = reductions

        # Calculate cost and time savings
        await self._calculate_cost_time_savings(
            metrics, current_lessons, previous_lessons
        )

    async def _calculate_cost_time_savings(
        self,
        metrics: ImprovementMetrics,
        current_lessons: List[EnhancedLesson],
        previous_lessons: List[EnhancedLesson],
    ) -> None:
        """Calculate cost and time savings from issue reduction."""

        def calculate_period_costs(
            lessons: List[EnhancedLesson],
        ) -> Tuple[float, float]:
            cost = 0.0
            time = 0.0

            for lesson in lessons:
                if lesson.source == LessonSource.AUTOFIX:
                    cost += self.COST_PER_AUTOFIX_INCIDENT
                    time += self.TIME_PER_AUTOFIX_INCIDENT
                elif lesson.source == LessonSource.DEPLOYMENT:
                    cost += self.COST_PER_DEPLOYMENT_FAILURE
                    time += self.TIME_PER_DEPLOYMENT_FAILURE
                elif lesson.source == LessonSource.OPERATIONS:
                    cost += self.COST_PER_PRODUCTION_INCIDENT
                    time += self.TIME_PER_PRODUCTION_INCIDENT

                # Add actual cost impact if available
                if lesson.cost_impact:
                    cost += lesson.cost_impact

            return cost, time

        current_cost, current_time = calculate_period_costs(current_lessons)
        previous_cost, previous_time = calculate_period_costs(previous_lessons)

        metrics.cost_avoided_dollars = max(0, previous_cost - current_cost)
        metrics.time_saved_hours = max(0, previous_time - current_time)

    async def _calculate_pattern_metrics(
        self, metrics: ImprovementMetrics, lessons: List[EnhancedLesson]
    ) -> None:
        """Calculate pattern-related metrics."""
        # Count pattern frequencies
        pattern_counts = defaultdict(int)
        pattern_lessons = defaultdict(list)

        for lesson in lessons:
            pattern_counts[lesson.pattern] += 1
            pattern_lessons[lesson.pattern].append(lesson)

        # Top patterns by frequency
        top_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]

        metrics.top_patterns = []
        for pattern, count in top_patterns:
            pattern_info = {
                "pattern": pattern,
                "frequency": count,
                "impact_levels": {},
                "sources": {},
                "latest_lesson": None,
            }

            # Analyze pattern details
            pattern_lesson_list = pattern_lessons[pattern]

            # Count by impact
            impact_counts = defaultdict(int)
            source_counts = defaultdict(int)
            latest_lesson = None
            latest_timestamp = datetime.min

            for lesson in pattern_lesson_list:
                impact_counts[lesson.impact.value] += 1
                source_counts[lesson.source.value] += 1

                if lesson.timestamp > latest_timestamp:
                    latest_timestamp = lesson.timestamp
                    latest_lesson = {
                        "lesson_id": lesson.lesson_id,
                        "issue_type": lesson.issue_type,
                        "timestamp": lesson.timestamp.isoformat(),
                    }

            pattern_info["impact_levels"] = dict(impact_counts)
            pattern_info["sources"] = dict(source_counts)
            pattern_info["latest_lesson"] = latest_lesson

            metrics.top_patterns.append(pattern_info)

        # Most effective lessons (high frequency + high impact)
        effectiveness_scores = []

        for lesson in lessons:
            if lesson.effectiveness is not None:
                effectiveness_scores.append((lesson.effectiveness, lesson))

        # Sort by effectiveness and take top 10
        effectiveness_scores.sort(reverse=True)

        metrics.most_effective_lessons = []
        for effectiveness, lesson in effectiveness_scores[:10]:
            metrics.most_effective_lessons.append(
                {
                    "lesson_id": lesson.lesson_id,
                    "pattern": lesson.pattern,
                    "issue_type": lesson.issue_type,
                    "effectiveness": effectiveness,
                    "frequency": lesson.frequency,
                    "impact": lesson.impact.value,
                    "timestamp": lesson.timestamp.isoformat(),
                }
            )

    async def _calculate_trends(
        self, metrics: ImprovementMetrics, days_back: int
    ) -> None:
        """Calculate trend metrics comparing current vs previous period."""
        # Load data for trend comparison
        all_lessons = await self.lesson_store.load_lessons(days_back=days_back * 2)

        current_period_start = datetime.now() - timedelta(days=days_back)

        current_lessons = [
            lesson for lesson in all_lessons if lesson.timestamp >= current_period_start
        ]
        previous_lessons = [
            lesson for lesson in all_lessons if lesson.timestamp < current_period_start
        ]

        # Calculate trends
        trends = {}

        # Lessons captured trend
        trends["lessons_captured"] = MetricsTrend(
            period=f"{days_back}_days",
            current_value=len(current_lessons),
            previous_value=len(previous_lessons),
        )

        # High impact lessons trend
        current_high_impact = len(
            [lesson for lesson in current_lessons if lesson.impact == ImpactLevel.HIGH]
        )
        previous_high_impact = len(
            [lesson for lesson in previous_lessons if lesson.impact == ImpactLevel.HIGH]
        )

        trends["high_impact_lessons"] = MetricsTrend(
            period=f"{days_back}_days",
            current_value=current_high_impact,
            previous_value=previous_high_impact,
        )

        # Template improvements trend
        current_template_updates = len(
            [
                t
                for t in self.template_registry.templates.values()
                if t.updated_at >= current_period_start
            ]
        )

        # Rough estimate for previous period (would need better tracking in production)
        previous_template_updates = max(
            0, len(self.template_registry.templates) - current_template_updates
        )

        trends["template_updates"] = MetricsTrend(
            period=f"{days_back}_days",
            current_value=current_template_updates,
            previous_value=previous_template_updates,
        )

        metrics.trends = trends


class MetricsReporter:
    """Generates reports and dashboards from improvement metrics."""

    def __init__(self, output_path: Optional[Path] = None):
        self.output_path = output_path or Path.cwd() / ".solve" / "metrics"
        self.output_path.mkdir(parents=True, exist_ok=True)

    async def generate_report(
        self, metrics: ImprovementMetrics, format_type: str = "json"
    ) -> Path:
        """Generate a metrics report in specified format."""
        logger.info(f"Generating metrics report in {format_type} format")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format_type == "json":
            return await self._generate_json_report(metrics, timestamp)
        elif format_type == "markdown":
            return await self._generate_markdown_report(metrics, timestamp)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    async def _generate_json_report(
        self, metrics: ImprovementMetrics, timestamp: str
    ) -> Path:
        """Generate JSON report."""
        file_path = self.output_path / f"improvement_metrics_{timestamp}.json"

        report_data = {
            "report_type": "improvement_metrics",
            "generated_at": metrics.generated_at.isoformat(),
            "reporting_period": metrics.reporting_period,
            "metrics": metrics.to_dict(),
        }

        content = json.dumps(report_data, indent=2)
        await asyncio.to_thread(file_path.write_text, content)

        logger.info(f"JSON report saved to {file_path}")
        return file_path

    async def _generate_markdown_report(
        self, metrics: ImprovementMetrics, timestamp: str
    ) -> Path:
        """Generate Markdown report."""
        file_path = self.output_path / f"improvement_metrics_{timestamp}.md"

        report_content = f"""# SOLVE Improvement Metrics Report

**Generated:** {metrics.generated_at.strftime("%Y-%m-%d %H:%M:%S")}
**Reporting Period:** {metrics.reporting_period.replace("_", " ").title()}

## Executive Summary

- **Lessons Captured:** {metrics.lessons_captured}
- **Templates Improved:** {metrics.templates_improved}
- **Cost Avoided:** ${metrics.cost_avoided_dollars:,.2f}
- **Time Saved:** {metrics.time_saved_hours:.1f} hours

## Lesson Capture Metrics

### By Source
{self._format_dict_table(metrics.lessons_by_source)}

### By Category
{self._format_dict_table(metrics.lessons_by_category)}

### By Impact Level
{self._format_dict_table(metrics.lessons_by_impact)}

## Template Evolution Metrics

- **Templates Improved:** {metrics.templates_improved}
- **Template Versions Created:** {metrics.template_versions_created}

### By Template Type
{self._format_dict_table(metrics.templates_by_type)}

## Issue Reduction

{self._format_reduction_table(metrics.issue_reduction)}

## Top Patterns

{self._format_patterns_table(metrics.top_patterns)}

## Most Effective Lessons

{self._format_effective_lessons_table(metrics.most_effective_lessons)}

## Trends

{self._format_trends_table(metrics.trends)}

---
*Report generated by SOLVE Improvement Metrics System*
"""

        await asyncio.to_thread(file_path.write_text, report_content)

        logger.info(f"Markdown report saved to {file_path}")
        return file_path

    def _format_dict_table(self, data: Dict[str, Any]) -> str:
        """Format dictionary as markdown table."""
        if not data:
            return "_No data available_"

        table = "| Category | Count |\n|----------|-------|\n"
        for key, value in data.items():
            table += f"| {key.replace('_', ' ').title()} | {value} |\n"

        return table

    def _format_reduction_table(self, data: Dict[str, float]) -> str:
        """Format reduction metrics as table."""
        if not data:
            return "_No reduction data available_"

        table = "| Source | Reduction % |\n|--------|------------|\n"
        for source, reduction in data.items():
            direction = "📈" if reduction > 0 else "📉" if reduction < 0 else "➖"
            table += f"| {source.replace('_', ' ').title()} | {direction} {reduction:+.1f}% |\n"

        return table

    def _format_patterns_table(self, patterns: List[Dict[str, Any]]) -> str:
        """Format top patterns as table."""
        if not patterns:
            return "_No patterns identified_"

        table = "| Pattern | Frequency | Primary Impact |\n|---------|-----------|----------------|\n"
        for pattern in patterns[:5]:  # Top 5
            primary_impact = (
                max(pattern["impact_levels"], key=pattern["impact_levels"].get)
                if pattern["impact_levels"]
                else "unknown"
            )
            table += f"| {pattern['pattern']} | {pattern['frequency']} | {primary_impact.title()} |\n"

        return table

    def _format_effective_lessons_table(self, lessons: List[Dict[str, Any]]) -> str:
        """Format most effective lessons as table."""
        if not lessons:
            return "_No effectiveness data available_"

        table = "| Pattern | Effectiveness | Frequency | Impact |\n|---------|---------------|-----------|--------|\n"
        for lesson in lessons[:5]:  # Top 5
            effectiveness = (
                f"{lesson['effectiveness']:.1%}"
                if lesson.get("effectiveness")
                else "N/A"
            )
            table += f"| {lesson['pattern']} | {effectiveness} | {lesson['frequency']} | {lesson['impact'].title()} |\n"

        return table

    def _format_trends_table(self, trends: Dict[str, MetricsTrend]) -> str:
        """Format trends as table."""
        if not trends:
            return "_No trend data available_"

        table = "| Metric | Current | Previous | Change | Trend |\n|--------|---------|----------|-----------|-------|\n"
        for name, trend in trends.items():
            direction_emoji = {"up": "📈", "down": "📉", "stable": "➖"}[
                trend.direction
            ]
            table += f"| {name.replace('_', ' ').title()} | {trend.current_value} | {trend.previous_value} | {trend.change_percentage:+.1f}% | {direction_emoji} |\n"

        return table


# Integration functions


async def generate_improvement_report(
    lesson_store: LessonStore,
    template_registry: TemplateRegistry,
    reporting_period: str = "30_days",
    format_type: str = "json",
) -> Path:
    """Generate comprehensive improvement metrics report."""
    calculator = ImprovementMetricsCalculator(lesson_store, template_registry)
    reporter = MetricsReporter()

    metrics = await calculator.calculate_metrics(reporting_period)
    report_path = await reporter.generate_report(metrics, format_type)

    return report_path
