"""
Intelligent Error Analyzer for Stage 2 Validation.

This module provides smart grouping, risk assessment, and prioritization
of errors to optimize Stage 3 LLM processing.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .models import Error, ErrorPriority, ValidationResult

logger = logging.getLogger(__name__)


class ErrorRisk(Enum):
    """Risk levels for automated fixes."""

    LOW = "safe_to_autofix"  # E402, trailing commas, quotes
    MEDIUM = "review_recommended"  # Type annotations, simple refactors
    HIGH = "manual_review"  # Logic changes, API modifications
    CRITICAL = "do_not_autofix"  # Security issues, data loss risks


@dataclass
class ErrorGroup:
    """A group of related errors for batch processing."""

    group_type: str  # 'file', 'error_type', 'context', 'import_chain'
    group_key: str  # Identifier for the group
    errors: list[Error] = field(default_factory=list)
    risk_level: ErrorRisk = ErrorRisk.MEDIUM
    estimated_cost: float = 0.0
    priority_score: int = 0
    fix_confidence: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.errors)

    def add_error(self, error: Error) -> None:
        """Add an error to this group."""
        self.errors.append(error)


@dataclass
class AnalysisReport:
    """Comprehensive analysis report from Stage 2."""

    total_errors: int
    filtered_errors: int
    error_groups: list[ErrorGroup]
    summary_by_category: dict[str, int]
    summary_by_risk: dict[str, int]
    recommended_actions: list[str]
    estimated_total_cost: float
    confidence_score: float

    def to_markdown(self) -> str:
        """Generate human-readable markdown report."""
        lines = [
            "# Stage 2 Validation Report",
            "=" * 50,
            f"Total Issues: {self.total_errors} ({self.filtered_errors} after filtering)",
            "",
            "## By Category:",
        ]

        for category, count in sorted(
            self.summary_by_category.items(), key=lambda x: -x[1]
        ):
            percentage = (
                (count / self.total_errors * 100) if self.total_errors > 0 else 0
            )
            lines.append(f"- {category}: {count} issues ({percentage:.1f}%)")

        lines.extend(
            [
                "",
                "## By Risk Level:",
            ],
        )

        for risk, count in self.summary_by_risk.items():
            lines.append(f"- {risk}: {count} groups")

        lines.extend(
            [
                "",
                "## Recommended Actions:",
            ],
        )

        for i, action in enumerate(self.recommended_actions, 1):
            lines.append(f"{i}. {action}")

        lines.extend(
            [
                "",
                f"**Estimated Stage 3 Cost**: ${self.estimated_total_cost:.2f}",
                f"**Overall Confidence**: {self.confidence_score:.1%}",
            ],
        )

        return "\n".join(lines)


class ErrorAnalyzer:
    """Intelligent error analyzer for Stage 2 preprocessing."""

    # Risk assessment rules
    RISK_RULES = {
        # Low risk - safe automated fixes
        ErrorRisk.LOW: [
            "E402",  # Module level import not at top
            "E501",  # Line too long
            "F401",  # Unused import
            "E231",  # Missing whitespace
            "E302",  # Expected blank lines
            "E303",  # Too many blank lines
            "var-annotated",  # Missing variable annotations
        ],
        # Medium risk - usually safe but review recommended
        ErrorRisk.MEDIUM: [
            "arg-type",  # Argument type mismatch
            "no-untyped-def",  # Missing function type annotations
            "attr-defined",  # Attribute not defined (if isolated)
            "no-any-return",  # Returning Any
            "assignment",  # Assignment type errors
        ],
        # High risk - requires careful review
        ErrorRisk.HIGH: [
            "no-redef",  # Redefinition
            "unreachable",  # Unreachable code
            "return-value",  # Return type mismatches
            "union-attr",  # Union attribute access
            "operator",  # Operator type errors
        ],
        # Critical - do not autofix
        ErrorRisk.CRITICAL: [
            "misc",  # Miscellaneous mypy errors
            "security",  # Any security issue
            "syntax",  # Syntax errors
        ],
    }

    # Cost estimates per error type (in dollars)
    COST_ESTIMATES = {
        ErrorRisk.LOW: 0.001,  # $0.001 per error
        ErrorRisk.MEDIUM: 0.005,  # $0.005 per error
        ErrorRisk.HIGH: 0.01,  # $0.01 per error
        ErrorRisk.CRITICAL: 0.0,  # Not fixable
    }

    def __init__(self) -> None:
        self.groups: dict[str, ErrorGroup] = {}

    def analyze(self, validation_result: ValidationResult) -> AnalysisReport:
        """Analyze validation results and produce intelligent groupings."""
        logger.info(f"Analyzing {len(validation_result.errors)} errors...")

        # Convert dictionary errors to Error objects
        error_objects = []
        for error_dict in validation_result.errors:
            # Map error codes to priorities
            code = error_dict.get("code", "")
            if code in ["E402", "E501", "F401", "E231", "E302", "E303"]:
                priority = ErrorPriority.SIMPLE
            elif code.startswith("E"):
                priority = ErrorPriority.SYNTAX
            elif code == "import-error" or "import" in code:
                priority = ErrorPriority.IMPORTS
            elif "type" in code or "attr" in code:
                priority = ErrorPriority.TYPES
            else:
                priority = ErrorPriority.COMPLEX

            error_obj = Error(
                file_path=error_dict.get("file", ""),
                line=error_dict.get("line", 0),
                column=error_dict.get("column", 0),
                code=code,
                message=error_dict.get("message", ""),
                priority=priority,
                context={"tool": error_dict.get("tool", "unknown")},
            )
            error_objects.append(error_obj)

        # Group errors
        self._group_by_file(error_objects)
        self._group_by_type(error_objects)
        self._group_by_context(error_objects)

        # Assess risk and priority
        for group in self.groups.values():
            self._assess_risk(group)
            self._calculate_priority(group)
            self._estimate_cost(group)

        # Generate report
        report = self._generate_report(validation_result)

        logger.info(f"Analysis complete: {len(self.groups)} error groups identified")
        return report

    def _group_by_file(self, errors: list[Error]) -> None:
        """Group errors by file."""
        file_groups = defaultdict(list)

        for error in errors:
            file_groups[error.file_path].append(error)

        for file_path, file_errors in file_groups.items():
            if len(file_errors) >= 3:  # Only create groups with 3+ errors
                group_key = f"file:{file_path}"
                self.groups[group_key] = ErrorGroup(
                    group_type="file",
                    group_key=group_key,
                    errors=file_errors,
                    context={"file_path": file_path},
                )

    def _group_by_type(self, errors: list[Error]) -> None:
        """Group errors by error type."""
        type_groups = defaultdict(list)

        for error in errors:
            type_groups[error.code].append(error)

        for error_code, type_errors in type_groups.items():
            if len(type_errors) >= 5:  # Only create groups with 5+ errors
                group_key = f"type:{error_code}"
                self.groups[group_key] = ErrorGroup(
                    group_type="error_type",
                    group_key=group_key,
                    errors=type_errors,
                    context={"error_code": error_code},
                )

    def _group_by_context(self, errors: list[Error]) -> None:
        """Group errors by context (e.g., same class or function)."""
        # Group by proximity (within 20 lines)
        sorted_errors = sorted(errors, key=lambda e: (e.file_path, e.line))

        context_groups = []
        current_group: list[Error] = []

        for _i, error in enumerate(sorted_errors):
            if not current_group:
                current_group.append(error)
            else:
                last_error = current_group[-1]
                if (
                    error.file_path == last_error.file_path
                    and error.line - last_error.line <= 20
                ):
                    current_group.append(error)
                else:
                    if len(current_group) >= 3:
                        context_groups.append(current_group)
                    current_group = [error]

        if len(current_group) >= 3:
            context_groups.append(current_group)

        for _i, group_errors in enumerate(context_groups):
            group_key = (
                f"context:{group_errors[0].file_path}:"
                f"L{group_errors[0].line}-{group_errors[-1].line}"
            )
            self.groups[group_key] = ErrorGroup(
                group_type="context",
                group_key=group_key,
                errors=group_errors,
                context={
                    "file_path": group_errors[0].file_path,
                    "line_range": (group_errors[0].line, group_errors[-1].line),
                },
            )

    def _assess_risk(self, group: ErrorGroup) -> None:
        """Assess the risk level of a group."""
        # Determine risk based on error types in group
        risk_levels = []

        for error in group.errors:
            for risk, codes in self.RISK_RULES.items():
                if error.code in codes:
                    risk_levels.append(risk)
                    break
            else:
                risk_levels.append(ErrorRisk.MEDIUM)  # Default

        # Use highest risk level in group
        if ErrorRisk.CRITICAL in risk_levels:
            group.risk_level = ErrorRisk.CRITICAL
        elif ErrorRisk.HIGH in risk_levels:
            group.risk_level = ErrorRisk.HIGH
        elif ErrorRisk.MEDIUM in risk_levels:
            group.risk_level = ErrorRisk.MEDIUM
        else:
            group.risk_level = ErrorRisk.LOW

        # Adjust based on group characteristics
        if group.group_type == "file" and group.count > 50:
            # Large file changes are riskier
            if group.risk_level == ErrorRisk.LOW:
                group.risk_level = ErrorRisk.MEDIUM
            elif group.risk_level == ErrorRisk.MEDIUM:
                group.risk_level = ErrorRisk.HIGH

    def _calculate_priority(self, group: ErrorGroup) -> None:
        """Calculate priority score for fixing this group."""
        score = 0.0

        # Base score from error count
        score += min(group.count * 10, 100)  # Cap at 100

        # Risk adjustment
        risk_multipliers = {
            ErrorRisk.LOW: 2.0,
            ErrorRisk.MEDIUM: 1.5,
            ErrorRisk.HIGH: 0.8,
            ErrorRisk.CRITICAL: 0.0,
        }
        score = score * risk_multipliers[group.risk_level]

        # Type bonus
        if group.group_type == "error_type":
            score = score * 1.2  # Fixing same type together is efficient

        # Import priority
        if any(e.code == "E402" for e in group.errors):
            score = score * 1.5  # Import fixes should come first

        group.priority_score = round(score)

        # Calculate fix confidence
        if group.risk_level == ErrorRisk.LOW:
            group.fix_confidence = 0.95
        elif group.risk_level == ErrorRisk.MEDIUM:
            group.fix_confidence = 0.75
        elif group.risk_level == ErrorRisk.HIGH:
            group.fix_confidence = 0.50
        else:
            group.fix_confidence = 0.0

    def _estimate_cost(self, group: ErrorGroup) -> None:
        """Estimate the cost to fix this group."""
        base_cost = self.COST_ESTIMATES[group.risk_level]
        group.estimated_cost = base_cost * group.count

    def _generate_report(self, validation_result: ValidationResult) -> AnalysisReport:
        """Generate the final analysis report."""
        # Summarize by category
        category_summary: dict[str, int] = defaultdict(int)
        risk_summary: dict[str, int] = defaultdict(int)

        for group in self.groups.values():
            risk_summary[group.risk_level.name] += 1
            for error in group.errors:
                category_summary[error.priority.name.lower()] += 1

        # Generate recommendations
        recommendations = []

        # Sort groups by priority
        sorted_groups = sorted(
            self.groups.values(), key=lambda g: g.priority_score, reverse=True
        )

        for group in sorted_groups[:5]:  # Top 5 recommendations
            if group.risk_level == ErrorRisk.CRITICAL:
                continue

            action = (
                f"Fix {group.count} {group.context.get('error_code', 'mixed')} errors"
            )
            if group.group_type == "file":
                action += f" in {Path(group.context['file_path']).name}"
            action += f" - {group.risk_level.name} RISK"
            recommendations.append(action)

        # Calculate totals
        total_cost = sum(g.estimated_cost for g in self.groups.values())
        avg_confidence = (
            sum(g.fix_confidence * g.count for g in self.groups.values())
            / sum(g.count for g in self.groups.values())
            if self.groups
            else 0
        )

        return AnalysisReport(
            total_errors=len(validation_result.errors),
            filtered_errors=sum(g.count for g in self.groups.values()),
            error_groups=sorted_groups,
            summary_by_category=dict(category_summary),
            summary_by_risk=dict(risk_summary),
            recommended_actions=recommendations,
            estimated_total_cost=total_cost,
            confidence_score=avg_confidence,
        )


# Convenience function
async def analyze_validation_results(
    validation_result: ValidationResult,
) -> AnalysisReport:
    """Analyze validation results and return intelligent groupings."""
    analyzer: ErrorAnalyzer = ErrorAnalyzer()
    return analyzer.analyze(validation_result)
