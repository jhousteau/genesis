"""
Comprehensive Lesson Capture and Template Evolution System for SOLVE Methodology

This module implements the requirements from Issue #80:
1. Captures lessons from multiple sources (autofix, deployments, operations)
2. Categorizes and prioritizes lessons
3. Generates template updates automatically
4. Tracks lesson application and effectiveness
5. Builds a knowledge base of patterns and anti-patterns
6. Measures improvement over time

Architecture based on Issue #80 specifications with GCP integration.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# Enhanced Data Models for Issue #80


class LessonSource(Enum):
    """Source of lesson learned."""

    AUTOFIX = "autofix"
    DEPLOYMENT = "deployment"
    OPERATIONS = "operations"
    MANUAL = "manual"
    CI_CD = "ci_cd"
    TESTING = "testing"


class ImpactLevel(Enum):
    """Impact level of a lesson."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(Enum):
    """Type of improvement action."""

    UPDATE_TEMPLATE = "update_template"
    UPDATE_GRAPH_PATTERN = "update_graph_pattern"
    UPDATE_POLICY = "update_policy"
    ADD_VALIDATION = "add_validation"
    UPDATE_DOCUMENTATION = "update_documentation"
    CREATE_ALERT = "create_alert"


class Category(Enum):
    """Lesson categories."""

    TEMPLATE = "template"
    GRAPH_PATTERN = "graph_pattern"
    POLICY = "policy"
    SECURITY = "security"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    CODE_QUALITY = "code_quality"


class Priority(Enum):
    """Priority levels for lesson processing."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AutofixResult:
    """Result from autofix operation."""

    success: bool
    phase: str
    issue_type: str
    pattern: str
    fix_applied: str
    stage: int
    files_affected: List[str] = field(default_factory=list)
    files_modified: List[str] = field(
        default_factory=list
    )  # Added for API compatibility
    time_taken: float = 0.0
    error_count: int = 0


@dataclass
class DeployResult:
    """Result from deployment operation."""

    success: bool
    error_type: Optional[str] = None
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    resolution: Optional[str] = None
    environment: str = "unknown"
    service_name: str = ""
    deployment_time: float = 0.0


@dataclass
class Incident:
    """Production incident information."""

    type: str
    root_cause: str
    prevention_measure: str
    impact_cost: float
    severity: str = "medium"
    affected_services: List[str] = field(default_factory=list)
    resolution_time: float = 0.0


@dataclass
class EnhancedLesson:
    """Enhanced lesson with additional metadata for Issue #80."""

    source: LessonSource
    phase: str
    issue_type: str
    pattern: str
    fix: str
    frequency: int
    impact: ImpactLevel
    category: Category
    priority: Priority
    timestamp: datetime = field(default_factory=datetime.now)
    lesson_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Additional metadata
    affected_template: Optional[str] = None
    pattern_id: Optional[str] = None
    validation_rule: Optional[str] = None
    prevents_deployment: bool = False
    cost_impact: float = 0.0
    effectiveness: Optional[float] = None
    applied_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "lesson_id": self.lesson_id,
            "source": self.source.value,
            "phase": self.phase,
            "issue_type": self.issue_type,
            "pattern": self.pattern,
            "fix": self.fix,
            "frequency": self.frequency,
            "impact": self.impact.value,
            "category": self.category.value,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "affected_template": self.affected_template,
            "pattern_id": self.pattern_id,
            "validation_rule": self.validation_rule,
            "prevents_deployment": self.prevents_deployment,
            "cost_impact": self.cost_impact,
            "effectiveness": self.effectiveness,
            "applied_date": (
                self.applied_date.isoformat() if self.applied_date else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnhancedLesson":
        """Create from dictionary."""
        # Convert enum fields
        data["source"] = LessonSource(data["source"])
        data["impact"] = ImpactLevel(data["impact"])
        data["category"] = Category(data["category"])
        data["priority"] = Priority(data["priority"])

        # Convert datetime fields
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if data.get("applied_date"):
            data["applied_date"] = datetime.fromisoformat(data["applied_date"])

        return cls(**data)


@dataclass
class Action:
    """Improvement action to be taken."""

    action_type: ActionType
    description: str
    lesson_id: str
    priority: Priority
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateTemplateAction:
    """Action to update a template."""

    template_id: str
    update_type: str
    description: str
    lesson_id: str
    priority: Priority
    action_type: ActionType = ActionType.UPDATE_TEMPLATE
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_rule: Optional[str] = None
    field: Optional[str] = None
    value: Optional[Any] = None
    check: Optional[str] = None


@dataclass
class UpdateGraphPatternAction:
    """Action to update a graph pattern."""

    pattern_id: str
    enhancement: str
    description: str
    lesson_id: str
    priority: Priority
    action_type: ActionType = ActionType.UPDATE_GRAPH_PATTERN
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdatePolicyAction:
    """Action to update a policy."""

    policy_type: str
    new_rule: str
    description: str
    lesson_id: str
    priority: Priority
    action_type: ActionType = ActionType.UPDATE_POLICY
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedLesson:
    """Lesson after processing."""

    lesson: EnhancedLesson
    category: Category
    actions: List[
        Union[
            Action, UpdateTemplateAction, UpdateGraphPatternAction, UpdatePolicyAction
        ]
    ]
    priority: Priority
    similar_lessons: List[str] = field(default_factory=list)
    processing_timestamp: datetime = field(default_factory=datetime.now)


class LessonCaptureSystem:
    """Captures and processes lessons from all sources."""

    def __init__(
        self,
        graph_db: Optional[Any] = None,
        template_registry: Optional[Any] = None,
        storage_path: Optional[Union[str, Path]] = None,
    ):
        """Initialize the lesson capture system.

        Args:
            graph_db: Graph database instance for pattern storage
            template_registry: Template registry for archetype management
            storage_path: Path for lesson storage (defaults to .solve/lessons)
        """
        self.graph = graph_db
        self.templates = template_registry
        self.lesson_store = LessonStore(storage_path)

        # Pattern tracking
        self.pattern_library = PatternLibrary()

        logger.info("Initialized LessonCaptureSystem with enhanced capabilities")

    async def capture_from_autofix(
        self, autofix_result: AutofixResult
    ) -> EnhancedLesson:
        """Extract lessons from autofix corrections."""
        logger.info(f"Capturing lesson from autofix: {autofix_result.issue_type}")

        # Determine impact based on stage and error count
        if autofix_result.stage == 3 or autofix_result.error_count > 10:
            impact = ImpactLevel.HIGH
        elif autofix_result.stage == 2 or autofix_result.error_count > 5:
            impact = ImpactLevel.MEDIUM
        else:
            impact = ImpactLevel.LOW

        # Extract pattern from issue type
        pattern = self.pattern_library.extract_pattern(
            autofix_result.issue_type, autofix_result.fix_applied
        )

        lesson = EnhancedLesson(
            source=LessonSource.AUTOFIX,
            phase=autofix_result.phase,
            issue_type=autofix_result.issue_type,
            pattern=pattern,
            fix=autofix_result.fix_applied,
            frequency=1,
            impact=impact,
            category=Category.CODE_QUALITY,
            priority=Priority.MEDIUM if impact == ImpactLevel.HIGH else Priority.LOW,
        )

        return await self.process_lesson(lesson)

    async def capture_from_deployment(
        self, deploy_result: DeployResult
    ) -> Optional[EnhancedLesson]:
        """Extract lessons from deployment failures."""
        if deploy_result.success:
            return None

        logger.info(
            f"Capturing lesson from deployment failure: {deploy_result.error_type}"
        )

        lesson = EnhancedLesson(
            source=LessonSource.DEPLOYMENT,
            phase="deployment",
            issue_type=deploy_result.error_type or "unknown_error",
            pattern=f"deployment_failure_{deploy_result.error_type}",
            fix=deploy_result.resolution or "Manual resolution required",
            frequency=1,
            impact=(
                ImpactLevel.CRITICAL
                if deploy_result.error_type == "security"
                else ImpactLevel.HIGH
            ),
            category=Category.RELIABILITY,
            priority=Priority.CRITICAL,
            prevents_deployment=True,
        )

        return await self.process_lesson(lesson)

    async def capture_from_operations(self, incident: Incident) -> EnhancedLesson:
        """Extract lessons from production incidents."""
        logger.info(f"Capturing lesson from incident: {incident.type}")

        # Map severity to impact
        severity_to_impact = {
            "critical": ImpactLevel.CRITICAL,
            "high": ImpactLevel.HIGH,
            "medium": ImpactLevel.MEDIUM,
            "low": ImpactLevel.LOW,
        }

        impact = severity_to_impact.get(incident.severity.lower(), ImpactLevel.MEDIUM)

        lesson = EnhancedLesson(
            source=LessonSource.OPERATIONS,
            phase="operations",
            issue_type=incident.type,
            pattern=f"incident_{incident.type}",
            fix=incident.root_cause,
            frequency=1,
            impact=impact,
            category=(
                Category.RELIABILITY
                if "reliability" in incident.type
                else Category.PERFORMANCE
            ),
            priority=(
                Priority.CRITICAL if impact == ImpactLevel.CRITICAL else Priority.HIGH
            ),
            cost_impact=incident.impact_cost,
        )

        return await self.process_lesson(lesson)

    async def process_lesson(self, lesson: EnhancedLesson) -> EnhancedLesson:
        """Process a raw lesson through the enhancement pipeline."""
        logger.info(f"Processing lesson {lesson.lesson_id}")

        # Store the lesson
        await self.lesson_store.store_lesson(lesson)

        # Update pattern frequency if similar pattern exists
        await self._update_pattern_frequency(lesson)

        return lesson

    async def _update_pattern_frequency(self, lesson: EnhancedLesson) -> None:
        """Update frequency for similar patterns."""
        similar_lessons = await self.lesson_store.find_similar_lessons(lesson)

        if similar_lessons:
            # Increase frequency for this pattern
            lesson.frequency = len(similar_lessons) + 1
            logger.info(
                f"Updated pattern frequency to {lesson.frequency} for {lesson.pattern}"
            )

    async def search_lessons(
        self,
        query: str,
        phase: Optional[str] = None,
        source: Optional[LessonSource] = None,
        days_back: int = 30,
    ) -> List[EnhancedLesson]:
        """Search lessons by query, phase, and source."""
        logger.info(
            f"Searching lessons: query='{query}', phase={phase}, source={source}"
        )

        all_lessons = await self.lesson_store.load_lessons(days_back=days_back)
        matching_lessons = []

        query_lower = query.lower()

        for lesson in all_lessons:
            # Text search across issue_type, pattern, and fix
            text_match = (
                query_lower in lesson.issue_type.lower()
                or query_lower in lesson.pattern.lower()
                or query_lower in lesson.fix.lower()
            )

            # Phase filter
            phase_match = phase is None or lesson.phase == phase

            # Source filter
            source_match = source is None or lesson.source == source

            if text_match and phase_match and source_match:
                matching_lessons.append(lesson)

        logger.info(f"Found {len(matching_lessons)} matching lessons")
        return matching_lessons

    async def get_analytics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get analytics for lessons over specified period."""
        logger.info(f"Generating analytics for {period_days} days")

        lessons = await self.lesson_store.load_lessons(days_back=period_days)

        # Basic counts
        total_lessons = len(lessons)

        # Count by source
        by_source = {}
        for source in LessonSource:
            by_source[source.value] = len(
                [lesson for lesson in lessons if lesson.source == source]
            )

        # Count by category
        by_category = {}
        for category in Category:
            by_category[category.value] = len(
                [lesson for lesson in lessons if lesson.category == category]
            )

        # Count by impact level
        by_impact = {}
        for impact in ImpactLevel:
            by_impact[impact.value] = len(
                [lesson for lesson in lessons if lesson.impact == impact]
            )

        # Top patterns
        pattern_counts = {}
        for lesson in lessons:
            pattern_counts[lesson.pattern] = pattern_counts.get(lesson.pattern, 0) + 1

        top_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        # Effectiveness metrics
        applied_lessons = [
            lesson for lesson in lessons if lesson.applied_date is not None
        ]
        effectiveness_rate = (
            len(applied_lessons) / total_lessons if total_lessons > 0 else 0.0
        )

        # Average lesson frequency (pattern repetition indicator)
        avg_frequency = (
            sum(lesson.frequency for lesson in lessons) / total_lessons
            if total_lessons > 0
            else 0.0
        )

        analytics = {
            "period_days": period_days,
            "total_lessons": total_lessons,
            "by_source": by_source,
            "by_category": by_category,
            "by_impact": by_impact,
            "top_patterns": [
                {
                    "pattern": pattern,
                    "count": count,
                    "percentage": (
                        (count / total_lessons * 100) if total_lessons > 0 else 0
                    ),
                }
                for pattern, count in top_patterns
            ],
            "effectiveness_rate": effectiveness_rate,
            "average_frequency": avg_frequency,
            "applied_lessons_count": len(applied_lessons),
        }

        logger.info(
            f"Generated analytics: {total_lessons} lessons, {effectiveness_rate:.2%} effectiveness"
        )
        return analytics

    async def capture_manual_lesson(
        self,
        issue: str,
        resolution: str,
        prevention: str,
        impact: ImpactLevel,
        phase: str,
    ) -> EnhancedLesson:
        """Capture a manually provided lesson."""
        logger.info(f"Capturing manual lesson: {issue}")

        # Extract pattern from issue and resolution
        pattern = self.pattern_library.extract_pattern(issue, resolution)

        # Determine category based on issue content
        issue_lower = issue.lower()
        if any(word in issue_lower for word in ["security", "vulnerability", "auth"]):
            category = Category.SECURITY
        elif any(word in issue_lower for word in ["performance", "slow", "timeout"]):
            category = Category.PERFORMANCE
        elif any(
            word in issue_lower for word in ["deploy", "reliability", "availability"]
        ):
            category = Category.RELIABILITY
        elif any(word in issue_lower for word in ["template", "archetype"]):
            category = Category.TEMPLATE
        else:
            category = Category.POLICY

        # Set priority based on impact
        if impact == ImpactLevel.CRITICAL:
            priority = Priority.CRITICAL
        elif impact == ImpactLevel.HIGH:
            priority = Priority.HIGH
        elif impact == ImpactLevel.MEDIUM:
            priority = Priority.MEDIUM
        else:
            priority = Priority.LOW

        lesson = EnhancedLesson(
            source=LessonSource.MANUAL,
            phase=phase,
            issue_type=issue,
            pattern=pattern,
            fix=f"{resolution} | Prevention: {prevention}",
            frequency=1,
            impact=impact,
            category=category,
            priority=priority,
            validation_rule=prevention if "check" in prevention.lower() else None,
        )

        return await self.process_lesson(lesson)


class LessonProcessor:
    """Processes lessons into actionable improvements."""

    def __init__(self, lesson_store: "LessonStore"):
        self.lesson_store = lesson_store

    async def process_lesson(self, lesson: EnhancedLesson) -> ProcessedLesson:
        """Process a lesson into actionable improvements."""
        logger.info(f"Processing lesson {lesson.lesson_id} for improvements")

        # 1. Deduplicate similar lessons
        similar = await self.find_similar_lessons(lesson)
        if similar:
            lesson = await self.merge_lessons(lesson, similar)

        # 2. Categorize by impact area
        category = self.categorize_lesson(lesson)

        # 3. Generate improvement actions
        actions = await self.generate_actions(lesson, category)

        # 4. Prioritize based on frequency and impact
        priority = self.calculate_priority(lesson)

        return ProcessedLesson(
            lesson=lesson,
            category=category,
            actions=actions,
            priority=priority,
            similar_lessons=[lesson.lesson_id for lesson in similar],
        )

    async def find_similar_lessons(
        self, lesson: EnhancedLesson
    ) -> List[EnhancedLesson]:
        """Find similar lessons based on pattern and issue type."""
        return await self.lesson_store.find_similar_lessons(lesson)

    async def merge_lessons(
        self, lesson: EnhancedLesson, similar: List[EnhancedLesson]
    ) -> EnhancedLesson:
        """Merge similar lessons to increase frequency and improve pattern."""
        logger.info(f"Merging lesson with {len(similar)} similar lessons")

        # Increase frequency
        lesson.frequency = len(similar) + 1

        # Upgrade priority if frequency is high
        if lesson.frequency >= 5:
            lesson.priority = Priority.HIGH
        elif lesson.frequency >= 3:
            lesson.priority = Priority.MEDIUM

        return lesson

    def categorize_lesson(self, lesson: EnhancedLesson) -> Category:
        """Categorize lesson by impact area."""
        # Use existing category if set, otherwise infer
        if lesson.category != Category.CODE_QUALITY:
            return lesson.category

        # Infer category from pattern and issue type
        issue_lower = lesson.issue_type.lower()
        pattern_lower = lesson.pattern.lower()

        if any(word in issue_lower for word in ["security", "vulnerability", "auth"]):
            return Category.SECURITY
        elif any(word in issue_lower for word in ["performance", "slow", "timeout"]):
            return Category.PERFORMANCE
        elif any(
            word in issue_lower for word in ["deploy", "reliability", "availability"]
        ):
            return Category.RELIABILITY
        elif any(word in pattern_lower for word in ["template", "archetype"]):
            return Category.TEMPLATE
        elif any(word in pattern_lower for word in ["graph", "pattern"]):
            return Category.GRAPH_PATTERN
        else:
            return Category.POLICY

    async def generate_actions(
        self, lesson: EnhancedLesson, category: Category
    ) -> List[
        Union[
            Action, UpdateTemplateAction, UpdateGraphPatternAction, UpdatePolicyAction
        ]
    ]:
        """Generate concrete improvement actions."""
        actions: List[
            Union[
                Action,
                UpdateTemplateAction,
                UpdateGraphPatternAction,
                UpdatePolicyAction,
            ]
        ] = []

        if category == Category.TEMPLATE:
            actions.append(
                UpdateTemplateAction(
                    template_id=lesson.affected_template or "default",
                    update_type="add_validation",
                    validation_rule=lesson.fix,
                    description=f"Add validation based on lesson: {lesson.issue_type}",
                    lesson_id=lesson.lesson_id,
                    priority=lesson.priority,
                )
            )

        if category == Category.GRAPH_PATTERN:
            actions.append(
                UpdateGraphPatternAction(
                    pattern_id=lesson.pattern_id or lesson.pattern,
                    enhancement=lesson.fix,
                    description=f"Enhance graph pattern based on lesson: {lesson.issue_type}",
                    lesson_id=lesson.lesson_id,
                    priority=lesson.priority,
                )
            )

        if category == Category.POLICY:
            actions.append(
                UpdatePolicyAction(
                    policy_type="pre_commit",
                    new_rule=lesson.validation_rule or lesson.fix,
                    description=f"Update policy based on lesson: {lesson.issue_type}",
                    lesson_id=lesson.lesson_id,
                    priority=lesson.priority,
                )
            )

        return actions

    def calculate_priority(self, lesson: EnhancedLesson) -> Priority:
        """Calculate priority based on frequency and impact."""
        base_priority = lesson.priority.value

        # Increase priority based on frequency
        if lesson.frequency >= 10:
            base_priority += 2
        elif lesson.frequency >= 5:
            base_priority += 1

        # Increase priority based on impact
        if lesson.impact == ImpactLevel.CRITICAL:
            base_priority += 2
        elif lesson.impact == ImpactLevel.HIGH:
            base_priority += 1

        # Cap at CRITICAL
        final_priority = min(base_priority, Priority.CRITICAL.value)

        return Priority(final_priority)


class LessonStore:
    """Handles storage and retrieval of lessons."""

    def __init__(self, storage_path: Optional[Union[str, Path]] = None):
        if storage_path is None:
            storage_path = Path.cwd() / ".solve" / "lessons"
        elif isinstance(storage_path, str):
            storage_path = Path(storage_path)

        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized LessonStore at {storage_path}")

    async def store_lesson(self, lesson: EnhancedLesson) -> None:
        """Store a lesson persistently."""
        date_key = lesson.timestamp.strftime("%Y-%m-%d")
        file_path = self.storage_path / f"enhanced_lessons_{date_key}.json"

        # Load existing lessons
        lessons = []
        if file_path.exists():
            content = await asyncio.to_thread(file_path.read_text)
            data = json.loads(content)
            lessons = [
                EnhancedLesson.from_dict(lesson_data)
                for lesson_data in data.get("lessons", [])
            ]

        # Add new lesson
        lessons.append(lesson)

        # Save back
        data = {
            "version": "2.0",
            "date": date_key,
            "lessons": [lesson.to_dict() for lesson in lessons],
        }

        content = json.dumps(data, indent=2)
        await asyncio.to_thread(file_path.write_text, content)

        logger.info(f"Stored lesson {lesson.lesson_id}")

    async def find_similar_lessons(
        self, lesson: EnhancedLesson, days_back: int = 30
    ) -> List[EnhancedLesson]:
        """Find lessons with similar patterns."""
        all_lessons = await self.load_lessons(days_back=days_back)

        similar = []
        for stored_lesson in all_lessons:
            if (
                stored_lesson.pattern == lesson.pattern
                and stored_lesson.issue_type == lesson.issue_type
                and stored_lesson.lesson_id != lesson.lesson_id
            ):
                similar.append(stored_lesson)

        return similar

    async def load_lessons(self, days_back: int = 30) -> List[EnhancedLesson]:
        """Load lessons from storage."""
        lessons = []
        start_date = datetime.now() - timedelta(days=days_back)

        for file_path in self.storage_path.glob("enhanced_lessons_*.json"):
            try:
                date_str = file_path.stem.replace("enhanced_lessons_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date.date() >= start_date.date():
                    content = await asyncio.to_thread(file_path.read_text)
                    data = json.loads(content)

                    for lesson_data in data.get("lessons", []):
                        lessons.append(EnhancedLesson.from_dict(lesson_data))
            except Exception as e:
                logger.warning(f"Could not load lessons from {file_path}: {e}")

        return lessons


class PatternLibrary:
    """Library of common patterns and their fixes."""

    PATTERN_LIBRARY = {
        "missing_error_handling": {
            "detection": r"except:\s*pass",
            "fix": "Add specific exception handling",
            "template_update": "Add error handling template",
        },
        "hardcoded_credentials": {
            "detection": r'password\s*=\s*["\'].*["\']',
            "fix": "Use environment variables",
            "template_update": "Add secret management",
        },
        "missing_retry": {
            "detection": "requests.get without retry",
            "fix": "Add exponential backoff retry",
            "template_update": "Include retry decorator",
        },
        "import_errors": {
            "detection": r"ImportError|ModuleNotFoundError",
            "fix": "Fix import paths and dependencies",
            "template_update": "Update dependency templates",
        },
        "formatting_issues": {
            "detection": r"formatting|whitespace|newline",
            "fix": "Apply automated code formatting",
            "template_update": "Add pre-commit formatting hooks",
        },
    }

    def extract_pattern(self, issue_type: str, fix_applied: str) -> str:
        """Extract pattern identifier from issue and fix."""
        issue_lower = issue_type.lower()

        for pattern_name, _pattern_info in self.PATTERN_LIBRARY.items():
            if any(word in issue_lower for word in pattern_name.split("_")):
                return pattern_name

        # Generate pattern from issue type
        return f"pattern_{issue_type.lower().replace(' ', '_')}"

    def get_pattern_info(self, pattern: str) -> Dict[str, str]:
        """Get pattern information."""
        return self.PATTERN_LIBRARY.get(
            pattern,
            {
                "detection": pattern,
                "fix": "Pattern-specific fix required",
                "template_update": "Update relevant templates",
            },
        )
