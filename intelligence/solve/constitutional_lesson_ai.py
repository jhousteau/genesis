"""
Constitutional AI for Lesson Evaluation

This module implements Constitutional AI principles for evaluating lessons
captured in the SOLVE methodology, ensuring that lessons are beneficial,
safe, and aligned with software engineering best practices.

Constitutional Principles:
1. Lessons must promote software quality and reliability
2. Lessons must not introduce security vulnerabilities
3. Lessons must be based on evidence and measurable outcomes
4. Lessons must respect user privacy and data protection
5. Lessons must promote maintainable and scalable solutions
6. Lessons must align with industry best practices
7. Lessons must be inclusive and accessible
8. Lessons must consider long-term technical debt implications

Implementation for Issue #80.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Tuple

from solve.lesson_capture_system import (
    EnhancedLesson,
    ImpactLevel,
    LessonSource,
    ProcessedLesson,
)

logger = logging.getLogger(__name__)


class ConstitutionalViolationType(Enum):
    """Types of constitutional violations in lessons."""

    SECURITY_RISK = "security_risk"
    QUALITY_DEGRADATION = "quality_degradation"
    PRIVACY_VIOLATION = "privacy_violation"
    ACCESSIBILITY_HARM = "accessibility_harm"
    MAINTAINABILITY_HARM = "maintainability_harm"
    SCALABILITY_HARM = "scalability_harm"
    EVIDENCE_LACKING = "evidence_lacking"
    BEST_PRACTICES_VIOLATION = "best_practices_violation"


@dataclass
class ConstitutionalViolation:
    """Represents a constitutional violation in a lesson."""

    violation_type: ConstitutionalViolationType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    suggested_mitigation: str
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "violation_type": self.violation_type.value,
            "severity": self.severity,
            "description": self.description,
            "suggested_mitigation": self.suggested_mitigation,
            "evidence": self.evidence,
        }


@dataclass
class ConstitutionalEvaluation:
    """Result of constitutional evaluation of a lesson."""

    lesson_id: str
    is_constitutional: bool
    violations: List[ConstitutionalViolation]
    quality_score: float  # 0.0 to 1.0
    recommendations: List[str]
    evaluation_timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "lesson_id": self.lesson_id,
            "is_constitutional": self.is_constitutional,
            "violations": [v.to_dict() for v in self.violations],
            "quality_score": self.quality_score,
            "recommendations": self.recommendations,
            "evaluation_timestamp": self.evaluation_timestamp.isoformat(),
        }


class ConstitutionalLessonEvaluator:
    """Evaluates lessons against constitutional AI principles."""

    # Security-related keywords that should be handled carefully
    SECURITY_KEYWORDS = [
        "password",
        "secret",
        "token",
        "key",
        "credential",
        "hardcode",
        "plaintext",
        "unencrypted",
        "insecure",
        "vulnerability",
        "exploit",
        "backdoor",
        "injection",
    ]

    # Quality anti-patterns to detect
    QUALITY_ANTI_PATTERNS = [
        "ignore error",
        "pass silently",
        "catch all",
        "global variable",
        "magic number",
        "copy paste",
        "god class",
        "spaghetti code",
    ]

    # Privacy-related concerns
    PRIVACY_KEYWORDS = [
        "personal data",
        "pii",
        "gdpr",
        "sensitive",
        "user data",
        "tracking",
        "analytics",
        "logging user",
        "email",
        "phone",
    ]

    def __init__(self):
        """Initialize the constitutional evaluator."""
        self.evaluation_history: Dict[str, ConstitutionalEvaluation] = {}

    async def evaluate_lesson(self, lesson: EnhancedLesson) -> ConstitutionalEvaluation:
        """Evaluate a lesson against constitutional principles."""
        logger.info(
            f"Evaluating lesson {lesson.lesson_id} against constitutional principles"
        )

        violations = []
        quality_score = 1.0
        recommendations = []

        # Evaluate against each constitutional principle
        violations.extend(await self._evaluate_security_principle(lesson))
        violations.extend(await self._evaluate_quality_principle(lesson))
        violations.extend(await self._evaluate_evidence_principle(lesson))
        violations.extend(await self._evaluate_privacy_principle(lesson))
        violations.extend(await self._evaluate_maintainability_principle(lesson))
        violations.extend(await self._evaluate_best_practices_principle(lesson))

        # Calculate quality score based on violations
        quality_score = self._calculate_quality_score(violations)

        # Generate recommendations
        recommendations = self._generate_recommendations(lesson, violations)

        # Determine if lesson is constitutional
        is_constitutional = (
            quality_score >= 0.7
            and not any(  # Minimum quality threshold
                v.severity in ["high", "critical"] for v in violations
            )
        )

        evaluation = ConstitutionalEvaluation(
            lesson_id=lesson.lesson_id,
            is_constitutional=is_constitutional,
            violations=violations,
            quality_score=quality_score,
            recommendations=recommendations,
            evaluation_timestamp=datetime.now(),
        )

        # Store evaluation for tracking
        self.evaluation_history[lesson.lesson_id] = evaluation

        logger.info(
            f"Constitutional evaluation complete: constitutional={is_constitutional}, "
            f"score={quality_score:.2f}, violations={len(violations)}"
        )

        return evaluation

    async def _evaluate_security_principle(
        self, lesson: EnhancedLesson
    ) -> List[ConstitutionalViolation]:
        """Evaluate lesson against security principle."""
        violations = []

        # Check for security-related content in issue description and fix
        issue_lower = lesson.issue_type.lower()
        fix_lower = lesson.fix.lower()

        # Check for hardcoded secrets
        if any(
            keyword in issue_lower or keyword in fix_lower
            for keyword in ["password", "secret", "token", "key"]
        ):
            if "hardcode" in issue_lower or "plaintext" in fix_lower:
                violations.append(
                    ConstitutionalViolation(
                        violation_type=ConstitutionalViolationType.SECURITY_RISK,
                        severity="high",
                        description="Lesson involves handling of hardcoded secrets or credentials",
                        suggested_mitigation="Ensure lesson promotes secure credential management practices",
                        evidence=f"Keywords found in: {lesson.issue_type}, {lesson.fix}",
                    )
                )

        # Check for security vulnerabilities being introduced
        if any(
            word in fix_lower
            for word in ["disable security", "skip validation", "ignore certificate"]
        ):
            violations.append(
                ConstitutionalViolation(
                    violation_type=ConstitutionalViolationType.SECURITY_RISK,
                    severity="critical",
                    description="Lesson fix appears to disable security measures",
                    suggested_mitigation="Review fix to ensure it doesn't compromise security",
                    evidence=f"Security-weakening language in fix: {lesson.fix}",
                )
            )

        # Positive security practices
        if any(
            word in fix_lower
            for word in ["encrypt", "validate", "sanitize", "authenticate"]
        ):
            # This is good - no violation, but note as positive
            logger.debug(f"Lesson {lesson.lesson_id} promotes good security practices")

        return violations

    async def _evaluate_quality_principle(
        self, lesson: EnhancedLesson
    ) -> List[ConstitutionalViolation]:
        """Evaluate lesson against quality principle."""
        violations = []

        fix_lower = lesson.fix.lower()
        lesson.issue_type.lower()

        # Check for quality anti-patterns
        for anti_pattern in self.QUALITY_ANTI_PATTERNS:
            if anti_pattern in fix_lower:
                violations.append(
                    ConstitutionalViolation(
                        violation_type=ConstitutionalViolationType.QUALITY_DEGRADATION,
                        severity="medium",
                        description=f"Lesson fix contains quality anti-pattern: {anti_pattern}",
                        suggested_mitigation="Consider alternative approaches that promote code quality",
                        evidence=f"Anti-pattern '{anti_pattern}' found in fix: {lesson.fix}",
                    )
                )

        # Check for quick fixes that might introduce technical debt
        quick_fix_indicators = [
            "quick fix",
            "temporary",
            "hack",
            "workaround",
            "todo",
            "fixme",
        ]
        if any(indicator in fix_lower for indicator in quick_fix_indicators):
            violations.append(
                ConstitutionalViolation(
                    violation_type=ConstitutionalViolationType.QUALITY_DEGRADATION,
                    severity="low",
                    description="Lesson appears to promote quick fixes or temporary solutions",
                    suggested_mitigation="Ensure lesson includes plan for proper long-term solution",
                    evidence=f"Quick fix indicators in: {lesson.fix}",
                )
            )

        return violations

    async def _evaluate_evidence_principle(
        self, lesson: EnhancedLesson
    ) -> List[ConstitutionalViolation]:
        """Evaluate lesson against evidence-based principle."""
        violations = []

        # Check if lesson has measurable impact
        if lesson.frequency < 2 and lesson.impact == ImpactLevel.LOW:
            violations.append(
                ConstitutionalViolation(
                    violation_type=ConstitutionalViolationType.EVIDENCE_LACKING,
                    severity="low",
                    description="Lesson has low frequency and impact, lacking strong evidence",
                    suggested_mitigation="Collect more evidence before applying this lesson widely",
                    evidence=f"Frequency: {lesson.frequency}, Impact: {lesson.impact.value}",
                )
            )

        # Check if lesson source is reliable
        if lesson.source == LessonSource.MANUAL and not hasattr(
            lesson, "validation_evidence"
        ):
            violations.append(
                ConstitutionalViolation(
                    violation_type=ConstitutionalViolationType.EVIDENCE_LACKING,
                    severity="medium",
                    description="Manual lesson lacks validation evidence",
                    suggested_mitigation="Add validation evidence or test results to support the lesson",
                    evidence=f"Manual lesson without validation: {lesson.lesson_id}",
                )
            )

        return violations

    async def _evaluate_privacy_principle(
        self, lesson: EnhancedLesson
    ) -> List[ConstitutionalViolation]:
        """Evaluate lesson against privacy principle."""
        violations = []

        issue_lower = lesson.issue_type.lower()
        fix_lower = lesson.fix.lower()

        # Check for privacy-related concerns
        for keyword in self.PRIVACY_KEYWORDS:
            if keyword in issue_lower or keyword in fix_lower:
                # Check if privacy is being handled properly
                if (
                    "log" in fix_lower
                    and "user" in fix_lower
                    and "mask" not in fix_lower
                ):
                    violations.append(
                        ConstitutionalViolation(
                            violation_type=ConstitutionalViolationType.PRIVACY_VIOLATION,
                            severity="medium",
                            description="Lesson may involve logging user data without proper privacy protection",
                            suggested_mitigation="Ensure user data is properly masked or anonymized in logs",
                            evidence=f"Privacy concern in: {lesson.fix}",
                        )
                    )

        return violations

    async def _evaluate_maintainability_principle(
        self, lesson: EnhancedLesson
    ) -> List[ConstitutionalViolation]:
        """Evaluate lesson against maintainability principle."""
        violations = []

        fix_lower = lesson.fix.lower()

        # Check for maintainability concerns
        maintainability_red_flags = [
            "duplicate code",
            "copy paste",
            "magic number",
            "hardcode",
            "comment out",
            "disable test",
            "skip validation",
        ]

        for red_flag in maintainability_red_flags:
            if red_flag in fix_lower:
                violations.append(
                    ConstitutionalViolation(
                        violation_type=ConstitutionalViolationType.MAINTAINABILITY_HARM,
                        severity="medium",
                        description=f"Lesson fix may harm maintainability: {red_flag}",
                        suggested_mitigation="Consider refactoring approach that improves maintainability",
                        evidence=f"Maintainability concern '{red_flag}' in: {lesson.fix}",
                    )
                )

        return violations

    async def _evaluate_best_practices_principle(
        self, lesson: EnhancedLesson
    ) -> List[ConstitutionalViolation]:
        """Evaluate lesson against best practices principle."""
        violations = []

        fix_lower = lesson.fix.lower()

        # Check for violations of common best practices
        best_practice_violations = [
            ("global", "Use of global variables"),
            ("singleton", "Overuse of singleton pattern"),
            ("sleep", "Use of sleep for timing control"),
            ("catch all", "Catching all exceptions without specificity"),
        ]

        for pattern, description in best_practice_violations:
            if pattern in fix_lower and "avoid" not in fix_lower:
                violations.append(
                    ConstitutionalViolation(
                        violation_type=ConstitutionalViolationType.BEST_PRACTICES_VIOLATION,
                        severity="low",
                        description=description,
                        suggested_mitigation="Follow industry best practices for this scenario",
                        evidence=f"Best practice concern '{pattern}' in: {lesson.fix}",
                    )
                )

        return violations

    def _calculate_quality_score(
        self, violations: List[ConstitutionalViolation]
    ) -> float:
        """Calculate quality score based on violations."""
        if not violations:
            return 1.0

        # Weight violations by severity
        severity_weights = {"low": 0.05, "medium": 0.15, "high": 0.3, "critical": 0.5}

        total_penalty = sum(severity_weights.get(v.severity, 0.1) for v in violations)
        quality_score = max(0.0, 1.0 - total_penalty)

        return quality_score

    def _generate_recommendations(
        self, lesson: EnhancedLesson, violations: List[ConstitutionalViolation]
    ) -> List[str]:
        """Generate recommendations for improving lesson quality."""
        recommendations = []

        if not violations:
            recommendations.append("Lesson meets constitutional standards")
            return recommendations

        # Group violations by type
        violation_types = {}
        for violation in violations:
            vtype = violation.violation_type
            if vtype not in violation_types:
                violation_types[vtype] = []
            violation_types[vtype].append(violation)

        # Generate recommendations based on violation types
        if ConstitutionalViolationType.SECURITY_RISK in violation_types:
            recommendations.append(
                "Review security implications and ensure secure practices"
            )

        if ConstitutionalViolationType.QUALITY_DEGRADATION in violation_types:
            recommendations.append(
                "Refactor approach to improve code quality and maintainability"
            )

        if ConstitutionalViolationType.EVIDENCE_LACKING in violation_types:
            recommendations.append(
                "Gather more evidence and validation data for this lesson"
            )

        if ConstitutionalViolationType.PRIVACY_VIOLATION in violation_types:
            recommendations.append("Implement proper privacy protection measures")

        if ConstitutionalViolationType.BEST_PRACTICES_VIOLATION in violation_types:
            recommendations.append("Align approach with industry best practices")

        # Add general recommendations based on severity
        critical_violations = [v for v in violations if v.severity == "critical"]
        high_violations = [v for v in violations if v.severity == "high"]

        if critical_violations:
            recommendations.append(
                "CRITICAL: This lesson requires immediate review before application"
            )
        elif high_violations:
            recommendations.append(
                "HIGH PRIORITY: Review and address violations before applying lesson"
            )

        return recommendations

    async def evaluate_processed_lesson(
        self, processed_lesson: ProcessedLesson
    ) -> ConstitutionalEvaluation:
        """Evaluate a processed lesson including its actions."""
        # Start with base lesson evaluation
        evaluation = await self.evaluate_lesson(processed_lesson.lesson)

        # Additional evaluation for processed lesson actions
        action_violations = []

        for action in processed_lesson.actions:
            # Evaluate template update actions for constitutional compliance
            if hasattr(action, "validation_rule") and action.validation_rule:
                rule_lower = action.validation_rule.lower()

                # Check for overly restrictive validations
                if any(
                    word in rule_lower
                    for word in [
                        "must never",
                        "always forbidden",
                        "strictly prohibited",
                    ]
                ):
                    action_violations.append(
                        ConstitutionalViolation(
                            violation_type=ConstitutionalViolationType.BEST_PRACTICES_VIOLATION,
                            severity="medium",
                            description="Action creates overly restrictive validation rule",
                            suggested_mitigation="Consider more flexible validation that allows legitimate use cases",
                            evidence=f"Overly restrictive rule: {action.validation_rule}",
                        )
                    )

        # Add action violations to evaluation
        evaluation.violations.extend(action_violations)

        # Recalculate quality score with action violations
        evaluation.quality_score = self._calculate_quality_score(evaluation.violations)
        evaluation.is_constitutional = evaluation.quality_score >= 0.7 and not any(
            v.severity in ["high", "critical"] for v in evaluation.violations
        )

        return evaluation

    def get_evaluation_history(self) -> Dict[str, ConstitutionalEvaluation]:
        """Get history of all evaluations."""
        return self.evaluation_history.copy()

    def get_constitutional_violations_summary(self) -> Dict[str, Any]:
        """Get summary of constitutional violations across all evaluations."""
        all_violations = []
        for evaluation in self.evaluation_history.values():
            all_violations.extend(evaluation.violations)

        # Count violations by type
        violation_counts = {}
        severity_counts = {}

        for violation in all_violations:
            vtype = violation.violation_type.value
            severity = violation.severity

            violation_counts[vtype] = violation_counts.get(vtype, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_evaluations": len(self.evaluation_history),
            "total_violations": len(all_violations),
            "violations_by_type": violation_counts,
            "violations_by_severity": severity_counts,
            "constitutional_rate": (
                len(
                    [e for e in self.evaluation_history.values() if e.is_constitutional]
                )
                / len(self.evaluation_history)
                if self.evaluation_history
                else 0.0
            ),
        }


# Integration functions for Issue #80


async def evaluate_lesson_constitutionally(
    lesson: EnhancedLesson,
) -> ConstitutionalEvaluation:
    """Evaluate a single lesson against constitutional principles."""
    evaluator = ConstitutionalLessonEvaluator()
    return await evaluator.evaluate_lesson(lesson)


async def evaluate_lessons_batch(
    lessons: List[EnhancedLesson],
) -> List[ConstitutionalEvaluation]:
    """Evaluate a batch of lessons against constitutional principles."""
    evaluator = ConstitutionalLessonEvaluator()
    evaluations = []

    for lesson in lessons:
        evaluation = await evaluator.evaluate_lesson(lesson)
        evaluations.append(evaluation)

    logger.info(f"Evaluated {len(lessons)} lessons constitutionally")
    return evaluations


async def filter_constitutional_lessons(
    lessons: List[EnhancedLesson],
) -> Tuple[List[EnhancedLesson], List[ConstitutionalEvaluation]]:
    """Filter lessons to only include those that pass constitutional evaluation."""
    evaluations = await evaluate_lessons_batch(lessons)

    constitutional_lessons = []
    all_evaluations = []

    for lesson, evaluation in zip(lessons, evaluations, strict=False):
        all_evaluations.append(evaluation)
        if evaluation.is_constitutional:
            constitutional_lessons.append(lesson)
        else:
            logger.warning(
                f"Lesson {lesson.lesson_id} failed constitutional evaluation: "
                f"{len(evaluation.violations)} violations"
            )

    logger.info(
        f"Filtered {len(constitutional_lessons)} constitutional lessons from {len(lessons)} total"
    )
    return constitutional_lessons, all_evaluations
