#!/usr/bin/env python3
"""Enhance phase implementation for SOLVE methodology.

This module processes lessons learned and generates improvements
to the SOLVE methodology, including quality gates and validation rules.

Enhanced for Issue #80 with comprehensive lesson capture and template evolution.
"""

import argparse
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from solve.improvement_metrics import ImprovementMetricsCalculator
from solve.lesson_capture_system import (EnhancedLesson, LessonCaptureSystem,
                                         LessonProcessor, LessonStore)
from solve.lessons import LessonCapture
from solve.models import Lesson
from solve.template_evolution import TemplateEvolution, TemplateRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancementEngine:
    """Main engine for enhancement phase operations with Issue #80 integration."""

    def __init__(self, project_path: Path):
        """Initialize the enhancement engine.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = project_path
        self.lesson_analyzer = LessonAnalyzer()
        self.gate_generator = QualityGateGenerator()

        # Initialize Issue #80 components
        self.lesson_store = LessonStore(project_path / ".solve" / "lessons")
        self.capture_system = LessonCaptureSystem(lesson_store=self.lesson_store)
        self.processor = LessonProcessor(self.lesson_store)

    async def enhance_project(self, adr_number: str | None = None) -> dict[str, Any]:
        """Run the comprehensive enhancement process on a project.

        Args:
            adr_number: Optional ADR number to focus on

        Returns:
            Dictionary with enhancement results including Issue #80 features
        """
        results: dict[str, Any] = {
            # Legacy results
            "patterns_found": 0,
            "gates_generated": 0,
            "validators_updated": False,
            # Issue #80 results
            "lessons_processed": 0,
            "templates_evolved": 0,
            "improvement_metrics": {},
            "effectiveness_improvements": {},
            "success": True,
        }

        try:
            # Run legacy pattern analysis
            patterns = await self.lesson_analyzer.analyze_patterns(adr_number)
            results["patterns_found"] = len(patterns)

            # Generate quality gates (legacy)
            gates = self.gate_generator.generate_gates(patterns)
            results["gates_generated"] = len(gates)

            # Run Issue #80 comprehensive enhancement
            enhancement_results = await self._run_comprehensive_enhancement(adr_number)
            results.update(enhancement_results)

            # Update validators if gates were generated (legacy)
            if gates:
                validator_path = self.project_path / "solve" / "validators.py"
                if validator_path.exists():
                    updater = ValidatorUpdater(validator_path)
                    results["validators_updated"] = updater.add_quality_gates(gates)

        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            results["success"] = False
            results["error"] = str(e)

        return results

    async def _run_comprehensive_enhancement(
        self, adr_number: str | None = None
    ) -> Dict[str, Any]:
        """Run comprehensive enhancement with lesson capture and template evolution."""
        logger.info("Running comprehensive enhancement with lesson capture system")

        results = {
            "lessons_processed": 0,
            "templates_evolved": 0,
            "improvement_metrics": {},
            "effectiveness_improvements": {},
        }

        try:
            # Load and process lessons
            lessons = await self.lesson_store.load_lessons(days_back=90)
            if adr_number:
                # Filter by ADR if specified
                lessons = [
                    lesson
                    for lesson in lessons
                    if getattr(lesson, "adr_number", None) == adr_number
                ]

            logger.info(f"Found {len(lessons)} lessons for enhancement processing")
            results["lessons_processed"] = len(lessons)

            if not lessons:
                logger.info("No lessons found for enhancement")
                return results

            # Process lessons into actionable improvements
            processed_lessons = []
            for lesson in lessons:
                processed = await self.processor.process_lesson(lesson)
                processed_lessons.append(processed)

            # Apply lessons to templates
            templates_path = self.project_path / "templates" / "archetypes"
            if templates_path.exists():
                template_registry = TemplateRegistry(templates_path)
                await template_registry.load_templates()

                evolution = TemplateEvolution(template_registry)
                evolution_result = await evolution.apply_lessons_to_templates(
                    processed_lessons
                )

                results["templates_evolved"] = evolution_result["templates_updated"]
                logger.info(
                    f"Evolved {evolution_result['templates_updated']} templates"
                )

            # Generate improvement metrics
            template_registry = (
                TemplateRegistry(templates_path) if templates_path.exists() else None
            )
            if template_registry:
                await template_registry.load_templates()

                calculator = ImprovementMetricsCalculator(
                    self.lesson_store, template_registry
                )
                metrics = await calculator.calculate_metrics("30_days")

                results["improvement_metrics"] = {
                    "lessons_captured": metrics.lessons_captured,
                    "templates_improved": metrics.templates_improved,
                    "cost_avoided": metrics.cost_avoided_dollars,
                    "time_saved": metrics.time_saved_hours,
                    "top_patterns": len(metrics.top_patterns),
                }

                logger.info(
                    f"Generated improvement metrics: {results['improvement_metrics']}"
                )

            # Track effectiveness improvements
            results[
                "effectiveness_improvements"
            ] = await self._calculate_effectiveness_improvements()

        except Exception as e:
            logger.error(f"Comprehensive enhancement failed: {e}")
            raise

        return results

    async def _calculate_effectiveness_improvements(self) -> Dict[str, Any]:
        """Calculate effectiveness improvements from lesson application."""
        try:
            # Load recent lessons and calculate improvement trends
            await self.lesson_store.load_lessons(days_back=30)
            older_lessons = await self.lesson_store.load_lessons(days_back=60)

            # Count lessons by category for trend analysis
            recent_counts = defaultdict(int)
            older_counts = defaultdict(int)

            cutoff_date = (datetime.now() - timedelta(days=30)).date()

            for lesson in older_lessons:
                category = lesson.category.value
                if lesson.timestamp.date() >= cutoff_date:
                    recent_counts[category] += 1
                else:
                    older_counts[category] += 1

            # Calculate improvement percentages
            improvements = {}
            for category in set(list(recent_counts.keys()) + list(older_counts.keys())):
                recent = recent_counts[category]
                older = older_counts[category]

                if older > 0:
                    improvement_pct = ((older - recent) / older) * 100
                    improvements[category] = {
                        "recent_count": recent,
                        "older_count": older,
                        "improvement_percentage": improvement_pct,
                    }

            return improvements

        except Exception as e:
            logger.warning(f"Failed to calculate effectiveness improvements: {e}")
            return {}

    async def capture_phase_lessons(
        self, phase_results: Dict[str, Any]
    ) -> List[EnhancedLesson]:
        """Capture lessons from all phase results for enhancement.

        This method integrates with other SOLVE phases to capture lessons
        from their execution results.
        """
        captured_lessons = []

        try:
            logger.info("Capturing lessons from phase results")

            # Capture from autofix results if available
            if "autofix_results" in phase_results:
                autofix_results = phase_results["autofix_results"]
                if not isinstance(autofix_results, list):
                    autofix_results = [autofix_results]

                for result in autofix_results:
                    if hasattr(result, "success") and result.success:
                        lesson = await self.capture_system.capture_from_autofix(result)
                        captured_lessons.append(lesson)

            # Capture from deployment results if available
            if "deployment_results" in phase_results:
                deployment_results = phase_results["deployment_results"]
                if not isinstance(deployment_results, list):
                    deployment_results = [deployment_results]

                for result in deployment_results:
                    lesson = await self.capture_system.capture_from_deployment(result)
                    if lesson:  # Only failures return lessons
                        captured_lessons.append(lesson)

            # Capture from operational incidents if available
            if "incidents" in phase_results:
                incidents = phase_results["incidents"]
                if not isinstance(incidents, list):
                    incidents = [incidents]

                for incident in incidents:
                    lesson = await self.capture_system.capture_from_operations(incident)
                    captured_lessons.append(lesson)

            logger.info(f"Captured {len(captured_lessons)} lessons from phase results")
            return captured_lessons

        except Exception as e:
            logger.error(f"Failed to capture phase lessons: {e}")
            return captured_lessons


class LessonAnalyzer:
    """Analyzes lessons to identify patterns and generate improvements."""

    def __init__(self, lessons_dir: Path | None = None):
        """Initialize the analyzer.

        Args:
            lessons_dir: Directory containing lesson files
        """
        self.capture = LessonCapture(lessons_dir)

    async def analyze_patterns(
        self, adr_number: str | None = None
    ) -> dict[str, list[Lesson]]:
        """Analyze lessons to identify recurring patterns.

        Args:
            adr_number: Optional ADR number to filter by

        Returns:
            Dictionary of issue categories to lessons
        """
        logger.info(f"Analyzing lessons for ADR-{adr_number or 'all'}")

        # Load lessons
        lessons = await self.capture.load_historical_lessons(
            adr_number=adr_number, days_back=90
        )

        # Categorize by issue type
        patterns = defaultdict(list)

        for lesson in lessons:
            category = self._categorize_issue(lesson.issue)
            patterns[category].append(lesson)

        # Log summary
        for category, category_lessons in patterns.items():
            logger.info(f"  {category}: {len(category_lessons)} occurrences")

        return dict(patterns)

    def _categorize_issue(self, issue: str) -> str:
        """Categorize an issue based on keywords.

        Args:
            issue: Issue description

        Returns:
            Category name
        """
        issue_lower = issue.lower()

        if "import" in issue_lower:
            return "import_issues"
        elif "validation" in issue_lower or "validate" in issue_lower:
            return "validation_issues"
        elif "test" in issue_lower:
            return "testing_issues"
        elif "phase" in issue_lower:
            return "phase_issues"
        elif "error" in issue_lower or "exception" in issue_lower:
            return "error_handling"
        elif "performance" in issue_lower or "slow" in issue_lower:
            return "performance_issues"
        else:
            return "other_issues"


class QualityGateGenerator:
    """Generates quality gate rules from lesson patterns."""

    def generate_gates(self, patterns: dict[str, list[Lesson]]) -> list[dict[str, Any]]:
        """Generate quality gate rules from patterns.

        Args:
            patterns: Dictionary of categorized lessons

        Returns:
            List of quality gate definitions
        """
        gates = []

        for category, lessons in patterns.items():
            if len(lessons) >= 1:  # Pattern threshold
                gate = self._create_gate(category, lessons)
                if gate:
                    gates.append(gate)

        return gates

    def _create_gate(
        self, category: str, lessons: list[Lesson]
    ) -> dict[str, Any] | None:
        """Create a quality gate from a pattern.

        Args:
            category: Issue category
            lessons: Related lessons

        Returns:
            Quality gate definition
        """
        # Map categories to gate rules
        gate_rules = {
            "import_issues": {
                "name": "import_style_check",
                "description": "Check for problematic import patterns",
                "validator_method": "check_imports",
                "severity": "warning" if len(lessons) < 5 else "error",
                "rule": "Avoid relative imports in library code",
            },
            "validation_issues": {
                "name": "validation_consistency",
                "description": "Ensure validation is consistent",
                "validator_method": "check_validation_consistency",
                "severity": "error",
                "rule": "All validation inputs must be normalized",
            },
            "testing_issues": {
                "name": "test_coverage",
                "description": "Ensure adequate test coverage",
                "validator_method": "check_test_coverage",
                "severity": "warning",
                "rule": "All modules must have corresponding tests",
            },
            "phase_issues": {
                "name": "phase_compliance",
                "description": "Check phase execution compliance",
                "validator_method": "check_phase_compliance",
                "severity": "error",
                "rule": "Phase codes must be uppercase and validated",
            },
        }

        if category in gate_rules:
            gate: dict[str, Any] = gate_rules[category].copy()
            gate["occurrences"] = len(lessons)
            gate["examples"] = [lesson.issue for lesson in lessons[:3]]
            return gate

        return None


class ValidatorUpdater:
    """Updates validator code with new quality gates."""

    def __init__(self, validator_path: Path):
        """Initialize the updater.

        Args:
            validator_path: Path to validators.py
        """
        self.validator_path = validator_path

    def add_quality_gates(self, gates: list[dict[str, Any]]) -> bool:
        """Add quality gate methods to validator.

        Args:
            gates: List of quality gate definitions

        Returns:
            True if successful
        """
        logger.info(f"Adding {len(gates)} quality gates to validator")

        # For now, just generate the code that would be added
        code_additions = []

        for gate in gates:
            method_code = self._generate_validator_method(gate)
            code_additions.append(method_code)

        # Log what would be added
        logger.info("Generated validator methods:")
        for code in code_additions:
            logger.info(f"\n{code}")

        # In a real implementation, we would parse the AST
        # and inject these methods into the PhaseValidator class

        return True

    def _generate_validator_method(self, gate: dict[str, Any]) -> str:
        """Generate validator method code for a gate.

        Args:
            gate: Quality gate definition

        Returns:
            Method code as string
        """
        template = f'''
    def {gate["validator_method"]}(self, path: Path) -> List[str]:
        """{gate["description"]}

        Rule: {gate["rule"]}
        Severity: {gate["severity"]}

        Args:
            path: Path to validate

        Returns:
            List of issues found
        """
        issues = []

        # Quality gate check for {gate["name"]}
        # Based on {gate["occurrences"]} occurrences in lessons learned

        # Implementation depends on the specific gate type
        # This is a generated template that needs customization per gate type

        return issues
'''
        return template


async def main() -> None:
    """Main entry point for enhance module."""
    parser = argparse.ArgumentParser(
        description="SOLVE Enhance Phase - Process lessons and improve methodology",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Analyze lessons command
    analyze_parser = subparsers.add_parser(
        "analyze-lessons", help="Analyze lessons for patterns"
    )
    analyze_parser.add_argument("--adr", help="ADR number to analyze (e.g., 016)")

    # Generate gates command
    gates_parser = subparsers.add_parser(
        "generate-gates",
        help="Generate quality gates from patterns",
    )
    gates_parser.add_argument("--adr", help="ADR number to process")

    # Update validators command
    subparsers.add_parser(
        "update-validators", help="Update validator code with new gates"
    )

    args = parser.parse_args()

    if args.command == "analyze-lessons":
        analyzer = LessonAnalyzer()
        patterns = await analyzer.analyze_patterns(args.adr)

        # Save patterns for next step
        project_root = Path.cwd()
        while (
            not (project_root / ".solve").exists()
            and project_root.parent != project_root
        ):
            project_root = project_root.parent

        patterns_file = project_root / ".solve" / "tmp" / "patterns.json"
        patterns_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert lessons to serializable format
        serializable_patterns = {}
        for category, lessons in patterns.items():
            serializable_patterns[category] = [lesson.to_dict() for lesson in lessons]

        patterns_file.write_text(json.dumps(serializable_patterns, indent=2))
        logger.info(f"Patterns saved to {patterns_file}")

    elif args.command == "generate-gates":
        # Load patterns
        project_root = Path.cwd()
        while (
            not (project_root / ".solve").exists()
            and project_root.parent != project_root
        ):
            project_root = project_root.parent

        patterns_file = project_root / ".solve" / "tmp" / "patterns.json"
        if not patterns_file.exists():
            logger.error("No patterns found. Run analyze-lessons first.")
            return

        patterns_data = json.loads(patterns_file.read_text())

        # Reconstruct lessons
        patterns = {}
        for category, lessons_data in patterns_data.items():
            patterns[category] = [Lesson.from_dict(data) for data in lessons_data]

        # Generate gates
        generator = QualityGateGenerator()
        gates = generator.generate_gates(patterns)

        # Save gates
        gates_file = project_root / ".solve" / "tmp" / "quality_gates.json"
        gates_file.write_text(json.dumps(gates, indent=2))
        logger.info(f"Generated {len(gates)} quality gates")
        logger.info(f"Gates saved to {gates_file}")

    elif args.command == "update-validators":
        # Load gates
        project_root = Path.cwd()
        while (
            not (project_root / ".solve").exists()
            and project_root.parent != project_root
        ):
            project_root = project_root.parent

        gates_file = project_root / ".solve" / "tmp" / "quality_gates.json"
        if not gates_file.exists():
            logger.error("No gates found. Run generate-gates first.")
            return

        gates = json.loads(gates_file.read_text())

        # Update validators
        validator_path = Path(".solve/sdk/validators.py")
        updater = ValidatorUpdater(validator_path)
        updater.add_quality_gates(gates)

    else:
        parser.print_help()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
