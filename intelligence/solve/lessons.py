"""
Lesson Capture System for SOLVE Methodology

This module captures and stores lessons learned during phase execution,
enabling continuous improvement of the development process.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from solve.autofix.models import FixResult
from solve.exceptions import LessonCaptureError
from solve.models import Lesson as ModelLesson  # Rename import to avoid conflict

logger = logging.getLogger(__name__)


# Test-expected Lesson structures


class LessonType(Enum):
    """Type of lesson learned during SOLVE execution."""

    IMPROVEMENT = "improvement"
    WARNING = "warning"
    SUCCESS = "success"


@dataclass
class Lesson:
    """Test-expected Lesson data model with different fields."""

    phase: str
    lesson_type: LessonType
    title: str
    description: str
    impact: str
    recommendation: str

    def __post_init__(self) -> None:
        """Validate lesson data."""
        if not all([self.phase, self.title, self.description]):
            raise ValueError("Lesson must have phase, title, and description")

        logger.debug(f"Created test lesson: {self.title} ({self.lesson_type.value})")


class LessonCapture:
    """Captures and stores lessons learned during execution.

    Provides functionality to record issues, resolutions, and prevention
    strategies for continuous improvement of the SOLVE methodology.
    """

    def __init__(self, lessons_dir: Path | None = None):
        """Initialize the lesson capture system.

        Args:
            lessons_dir: Directory to store lessons (defaults to .solve/lessons)
        """
        if lessons_dir is None:
            # Find project root and use .solve/lessons
            current = Path.cwd()
            while current != current.parent:
                if (current / ".solve").exists():
                    lessons_dir = current / ".solve" / "lessons"
                    break
                current = current.parent
            else:
                # Fallback to current directory
                lessons_dir = Path.cwd() / ".solve" / "lessons"

        self.lessons_dir = lessons_dir
        logger.info(f"Initialized LessonCapture with directory: {self.lessons_dir}")

    async def capture_lesson(
        self,
        issue: str,
        resolution: str,
        prevention: str,
        phase: str = "general",
        adr_number: str | None = None,
    ) -> ModelLesson:
        """Capture a new lesson learned.

        Args:
            issue: Description of the issue encountered
            resolution: How the issue was resolved
            prevention: How to prevent the issue in the future
            phase: SOLVE phase where issue occurred (default: 'general')
            adr_number: Related ADR number if applicable

        Returns:
            The captured lesson

        Raises:
            LessonCaptureError: If lesson capture fails
        """
        logger.info(f"Capturing lesson for phase {phase}")

        try:
            # Validate inputs
            if not all([issue, resolution, prevention]):
                raise LessonCaptureError(
                    "All fields (issue, resolution, prevention) are required",
                    operation="capture",
                )

            # Create lesson
            lesson_id = f"{phase}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
            lesson = ModelLesson(
                id=lesson_id,
                phase=phase,
                issue=issue,
                resolution=resolution,
                prevention=prevention,
                adr_number=adr_number,
            )

            # Save immediately
            await self.save_lessons([lesson])

            logger.info(f"Captured lesson {lesson_id}")
            return lesson

        except Exception as e:
            logger.error(f"Failed to capture lesson: {e}")
            raise LessonCaptureError(
                f"Failed to capture lesson: {e}", operation="capture"
            ) from e

    async def save_lessons(self, lessons: list[ModelLesson]) -> None:
        """Save lessons to persistent storage.

        Args:
            lessons: List of lessons to save

        Raises:
            LessonCaptureError: If saving fails
        """
        logger.info(f"Saving {len(lessons)} lessons")

        try:
            # Ensure lessons directory exists
            await asyncio.to_thread(self.lessons_dir.mkdir, parents=True, exist_ok=True)

            # Group lessons by date for organized storage
            lessons_by_date: dict[str, list[ModelLesson]] = {}
            for lesson in lessons:
                date_key = lesson.timestamp.strftime("%Y-%m-%d")
                if date_key not in lessons_by_date:
                    lessons_by_date[date_key] = []
                lessons_by_date[date_key].append(lesson)

            # Save lessons to date-specific files
            for date_key, date_lessons in lessons_by_date.items():
                file_path = self.lessons_dir / f"lessons-{date_key}.json"

                # Load existing lessons if file exists
                existing_lessons = []
                if file_path.exists():
                    try:
                        content = await asyncio.to_thread(file_path.read_text)
                        existing_data = json.loads(content)
                        existing_lessons = [
                            ModelLesson.from_dict(lesson_data)
                            for lesson_data in existing_data.get("lessons", [])
                        ]
                    except Exception as e:
                        logger.warning(
                            f"Could not load existing lessons from {file_path}: {e}"
                        )

                # Add new lessons
                all_lessons = existing_lessons + date_lessons

                # Remove duplicates based on ID
                unique_lessons = {lesson.lesson_id: lesson for lesson in all_lessons}
                all_lessons = list(unique_lessons.values())

                # Sort by timestamp
                all_lessons.sort(key=lambda lesson: lesson.timestamp)

                # Save to file
                data = {
                    "version": "1.0",
                    "date": date_key,
                    "lessons": [lesson.to_dict() for lesson in all_lessons],
                }

                content = json.dumps(data, indent=2)
                await asyncio.to_thread(file_path.write_text, content)

                logger.info(f"Saved {len(date_lessons)} lessons to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save lessons: {e}")
            raise LessonCaptureError(
                f"Failed to save lessons: {e}", operation="save"
            ) from e

    async def load_historical_lessons(
        self,
        phase: str | None = None,
        adr_number: str | None = None,
        days_back: int = 30,
    ) -> list[ModelLesson]:
        """Load historical lessons from storage.

        Args:
            phase: Filter by SOLVE phase (optional)
            adr_number: Filter by ADR number (optional)
            days_back: Number of days to look back (default: 30)

        Returns:
            List of historical lessons matching filters

        Raises:
            LessonCaptureError: If loading fails
        """
        logger.info(
            f"Loading historical lessons: phase={phase}, adr={adr_number}, days={days_back}",
        )

        try:
            all_lessons: list[ModelLesson] = []

            # Check if lessons directory exists
            if not self.lessons_dir.exists():
                logger.warning(f"Lessons directory does not exist: {self.lessons_dir}")
                return all_lessons

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Load lessons from files
            for file_path in self.lessons_dir.glob("lessons-*.json"):
                try:
                    # Extract date from filename
                    date_str = file_path.stem.replace("lessons-", "")
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    # Skip if outside date range
                    if file_date.date() < start_date.date():
                        continue

                    # Load lessons from file
                    content = await asyncio.to_thread(file_path.read_text)
                    data = json.loads(content)

                    for lesson_data in data.get("lessons", []):
                        lesson = ModelLesson.from_dict(lesson_data)

                        # Apply filters
                        if phase and lesson.phase != phase:
                            continue
                        if adr_number and lesson.adr_number != adr_number:
                            continue

                        all_lessons.append(lesson)

                except Exception as e:
                    logger.warning(f"Could not load lessons from {file_path}: {e}")

            # Sort by timestamp (newest first)
            all_lessons.sort(key=lambda lesson: lesson.timestamp, reverse=True)

            logger.info(f"Loaded {len(all_lessons)} historical lessons")
            return all_lessons

        except Exception as e:
            logger.error(f"Failed to load historical lessons: {e}")
            raise LessonCaptureError(
                f"Failed to load historical lessons: {e}",
                operation="load",
            ) from e

    async def get_lesson_summary(self, phase: str | None = None) -> dict[str, Any]:
        """Get a summary of lessons learned.

        Args:
            phase: Filter by phase (optional)

        Returns:
            Dictionary with lesson statistics and common patterns
        """
        logger.info(f"Getting lesson summary for phase: {phase}")

        try:
            lessons = await self.load_historical_lessons(phase=phase, days_back=90)

            summary = {
                "total_lessons": len(lessons),
                "by_phase": {},
                "recent_issues": [],
                "common_patterns": [],
            }

            # Count by phase
            phase_counts: dict[str, int] = {}
            for lesson in lessons:
                phase_counts[lesson.phase] = phase_counts.get(lesson.phase, 0) + 1
            summary["by_phase"] = phase_counts

            # Get recent issues (last 5)
            summary["recent_issues"] = [
                {
                    "id": lesson.lesson_id,
                    "phase": lesson.phase,
                    "issue": (
                        lesson.issue[:100] + "..."
                        if len(lesson.issue) > 100
                        else lesson.issue
                    ),
                    "date": lesson.timestamp.isoformat(),
                }
                for lesson in lessons[:5]
            ]

            # Find common patterns (simple keyword analysis)
            issue_words: dict[str, int] = {}
            for lesson in lessons:
                words = lesson.issue.lower().split()
                for word in words:
                    if len(word) > 4:  # Skip short words
                        issue_words[word] = issue_words.get(word, 0) + 1

            # Get top 5 common words
            common_words = sorted(
                issue_words.items(), key=lambda x: x[1], reverse=True
            )[:5]
            summary["common_patterns"] = [
                {"pattern": word, "frequency": count} for word, count in common_words
            ]

            return summary

        except Exception as e:
            logger.error(f"Failed to get lesson summary: {e}")
            return {
                "error": str(e),
                "total_lessons": 0,
                "by_phase": {},
                "recent_issues": [],
                "common_patterns": [],
            }

    async def capture_autofix_lessons(
        self,
        fix_results: list[FixResult],
        phase: str = "general",
        adr_number: str | None = None,
    ) -> list[ModelLesson]:
        """Convert autofix results into lessons learned.

        Each fix or batch of fixes becomes a lesson that helps prevent
        similar issues in future development.

        Args:
            fix_results: List of FixResult objects from autofix system
            phase: SOLVE phase where fixes were applied
            adr_number: Related ADR number if applicable

        Returns:
            List of lessons created from the fixes

        Raises:
            LessonCaptureError: If lesson creation fails
        """
        logger.info(f"Capturing lessons from {len(fix_results)} fix results")

        lessons_created = []

        try:
            for fix_result in fix_results:
                # Skip if no actual fixes were made
                if not fix_result.success or fix_result.errors_fixed == 0:
                    continue

                # Extract details from fix result
                fix_details = fix_result.details or {}
                iterations = fix_details.get("iterations", 1)
                fixers_used = fix_details.get("fixers_used", 0)
                is_dry_run = fix_details.get("dry_run", False)

                # Create descriptive issue summary
                issue = self._create_issue_description(fix_result, phase)

                # Create resolution description
                resolution = self._create_resolution_description(
                    fix_result,
                    iterations,
                    fixers_used,
                    is_dry_run,
                )

                # Create prevention strategy
                prevention = self._create_prevention_strategy(fix_result, fixers_used)

                # Capture the lesson
                lesson = await self.capture_lesson(
                    issue=issue,
                    resolution=resolution,
                    prevention=prevention,
                    phase=phase,
                    adr_number=adr_number,
                )

                lessons_created.append(lesson)

            logger.info(f"Created {len(lessons_created)} lessons from autofix results")
            return lessons_created

        except Exception as e:
            logger.error(f"Failed to capture autofix lessons: {e}")
            raise LessonCaptureError(
                f"Failed to capture autofix lessons: {e}",
                operation="capture_autofix",
            ) from e

    def _create_issue_description(self, fix_result: FixResult, phase: str) -> str:
        """Create a descriptive issue summary from fix result."""
        file_count = len(fix_result.files_changed)
        error_count = fix_result.errors_fixed

        file_desc = "1 file" if file_count == 1 else f"{file_count} files"

        if error_count == 1:
            error_desc = "1 code quality issue"
        else:
            error_desc = f"{error_count} code quality issues"

        issue = (
            f"During the {phase} phase, autofix detected {error_desc} "
            f"across {file_desc}. Issues included formatting violations, "
            f"missing end-of-file newlines, trailing whitespace, and import ordering problems."
        )

        # Add specific file examples if available
        if fix_result.files_changed:
            examples = fix_result.files_changed[:3]
            issue += f" Affected files included: {', '.join(examples)}"
            if len(fix_result.files_changed) > 3:
                issue += f" and {len(fix_result.files_changed) - 3} others"

        return issue

    def _create_resolution_description(
        self,
        fix_result: FixResult,
        iterations: int,
        fixers_used: int,
        is_dry_run: bool,
    ) -> str:
        """Create a resolution description from fix result."""
        if is_dry_run:
            resolution = (
                f"Autofix identified issues in {iterations} iteration(s) using "
                f"{fixers_used} different fixers (dry run mode - no changes applied)."
            )
        else:
            resolution = (
                f"Autofix successfully resolved all issues in {iterations} "
                f"iteration(s) using {fixers_used} different fixers. "
                f"The fixes were applied automatically, including: "
                f"code formatting with Ruff, import sorting, "
                f"trailing whitespace removal, and EOF newline enforcement."
            )

        # Add timing information if available
        if fix_result.time_taken:
            resolution += f" Total fix time: {fix_result.time_taken:.2f} seconds."

        return resolution

    def _create_prevention_strategy(
        self, fix_result: FixResult, fixers_used: int
    ) -> str:
        """Create a prevention strategy based on the fixes applied."""
        prevention = (
            "To prevent these issues in future development:\n"
            "1. Configure pre-commit hooks with the same tools used by autofix "
            "(ruff format, ruff check --fix)\n"
            "2. Run 'solve autofix' locally before committing changes\n"
            "3. Enable format-on-save in your IDE with Ruff configuration\n"
            "4. Add autofix as a CI/CD pipeline step to catch issues early"
        )

        # Add specific recommendations based on file count
        if len(fix_result.files_changed) > 10:
            prevention += (
                "\n5. Consider running autofix more frequently during development "
                "to prevent large batches of fixes"
            )

        return prevention

    async def search_lessons(
        self,
        query: str | None = None,
        phase: str | None = None,
        agent_role: str | None = None,
        limit: int = 10,
    ) -> list[ModelLesson]:
        """Search lessons by query, phase, or agent role.

        Args:
            query: Search query for text matching in issues/resolutions
            phase: Filter by SOLVE phase
            agent_role: Filter by agent role (maps to phase)
            limit: Maximum number of results to return

        Returns:
            List of lessons matching search criteria, sorted by relevance and recency
        """
        logger.info(
            f"Searching lessons: query={query}, phase={phase}, role={agent_role}"
        )

        # Map agent roles to phases
        role_to_phase = {
            "structure": "S",
            "interface": "O",
            "logic": "L",
            "testing": "V",
            "quality": "E",
        }

        # If agent_role provided, map to phase
        if agent_role and not phase:
            phase = role_to_phase.get(agent_role.lower())

        # Load all lessons (last 90 days for broader search)
        all_lessons = await self.load_historical_lessons(phase=phase, days_back=90)

        # Filter by query if provided
        if query:
            query_lower = query.lower()
            filtered_lessons = []

            for lesson in all_lessons:
                # Calculate relevance score
                score = 0

                # Check issue text
                if query_lower in lesson.issue.lower():
                    score += 3  # High weight for issue match

                # Check resolution text
                if query_lower in lesson.resolution.lower():
                    score += 2  # Medium weight for resolution match

                # Check prevention text
                if query_lower in lesson.prevention.lower():
                    score += 1  # Lower weight for prevention match

                if score > 0:
                    # Add lesson with score for sorting
                    filtered_lessons.append((score, lesson))

            # Sort by score (descending) then by timestamp (newest first)
            filtered_lessons.sort(key=lambda x: (-x[0], -x[1].timestamp.timestamp()))

            # Extract just the lessons
            lessons = [lesson for _, lesson in filtered_lessons[:limit]]
        else:
            # No query, just return most recent lessons
            lessons = all_lessons[:limit]

        logger.info(f"Found {len(lessons)} lessons matching search criteria")
        return lessons

    async def get_common_patterns(
        self, phase: str | None = None
    ) -> list[dict[str, Any]]:
        """Get common patterns from lessons.

        Args:
            phase: Filter by phase (optional)

        Returns:
            List of common patterns with frequency and examples
        """
        logger.info(f"Getting common patterns for phase: {phase}")

        try:
            # Load lessons from last 90 days
            lessons = await self.load_historical_lessons(phase=phase, days_back=90)

            if not lessons:
                return []

            # Pattern tracking
            pattern_map: dict[str, dict[str, Any]] = {}

            # Analyze each lesson for patterns
            for lesson in lessons:
                # Extract key patterns from issue
                issue_lower = lesson.issue.lower()

                # Common issue patterns
                patterns_to_check = [
                    ("formatting", "formatting violations", "Code formatting issues"),
                    ("import", "import", "Import ordering problems"),
                    ("whitespace", "whitespace", "Trailing whitespace issues"),
                    ("newline", "newline", "Missing EOF newlines"),
                    ("type", "type", "Type checking errors"),
                    ("test", "test", "Test failures"),
                    ("lint", "lint", "Linting violations"),
                    ("security", "security", "Security vulnerabilities"),
                ]

                for keyword, pattern_key, pattern_name in patterns_to_check:
                    if keyword in issue_lower:
                        if pattern_key not in pattern_map:
                            pattern_map[pattern_key] = {
                                "pattern": pattern_name,
                                "frequency": 0,
                                "examples": [],
                                "phases": set(),
                                "prevention_strategies": set(),
                            }

                        pattern_map[pattern_key]["frequency"] += 1
                        pattern_map[pattern_key]["phases"].add(lesson.phase)

                        # Add example if we have less than 3
                        if len(pattern_map[pattern_key]["examples"]) < 3:
                            pattern_map[pattern_key]["examples"].append(
                                {
                                    "issue": (
                                        lesson.issue[:100] + "..."
                                        if len(lesson.issue) > 100
                                        else lesson.issue
                                    ),
                                    "resolution": (
                                        lesson.resolution[:100] + "..."
                                        if len(lesson.resolution) > 100
                                        else lesson.resolution
                                    ),
                                },
                            )

                        # Extract prevention strategies
                        if lesson.prevention:
                            # Extract first line of prevention as summary
                            prevention_lines = lesson.prevention.split("\n")
                            if prevention_lines:
                                pattern_map[pattern_key]["prevention_strategies"].add(
                                    prevention_lines[0].strip(),
                                )

            # Convert to list format
            patterns = []
            for pattern_data in pattern_map.values():
                patterns.append(
                    {
                        "pattern": pattern_data["pattern"],
                        "frequency": pattern_data["frequency"],
                        "phases": list(pattern_data["phases"]),
                        "examples": pattern_data["examples"],
                        "prevention_strategies": list(
                            pattern_data["prevention_strategies"]
                        )[
                            :3
                        ],  # Top 3
                    },
                )

            # Sort by frequency
            patterns.sort(key=lambda x: x["frequency"], reverse=True)

            return patterns

        except Exception as e:
            logger.error(f"Failed to get common patterns: {e}")
            return []


# Convenience functions for synchronous usage
def search_lessons(
    query: str | None = None,
    phase: str | None = None,
    agent_role: str | None = None,
    limit: int = 10,
) -> list[ModelLesson]:
    """Synchronous wrapper for search_lessons."""
    capture = LessonCapture()
    return asyncio.run(capture.search_lessons(query, phase, agent_role, limit))


def get_common_patterns(phase: str | None = None) -> list[dict[str, Any]]:
    """Synchronous wrapper for get_common_patterns."""
    capture = LessonCapture()
    return asyncio.run(capture.get_common_patterns(phase))
