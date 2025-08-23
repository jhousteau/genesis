"""
Template Evolution Engine for SOLVE Methodology

This module implements automated template evolution based on lessons learned,
as specified in Issue #80. It updates GCP primitive templates and archetype
patterns based on captured lessons and proven fixes.

Key Features:
- Automated template versioning and updates
- GCP primitive archetype enhancement
- Template validation and rollback
- Change tracking and effectiveness measurement
- Integration with Cloud Storage for template distribution
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from solve.lesson_capture_system import (
    ActionType,
    Priority,
    ProcessedLesson,
    UpdateTemplateAction,
)

logger = logging.getLogger(__name__)


class TemplateVersion:
    """Represents a version of a template."""

    def __init__(
        self,
        version: int,
        template_id: str,
        changes: List[Dict[str, Any]],
        lesson_ids: List[str],
        timestamp: Optional[datetime] = None,
    ):
        self.version = version
        self.template_id = template_id
        self.changes = changes
        self.lesson_ids = lesson_ids
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "version": self.version,
            "template_id": self.template_id,
            "changes": self.changes,
            "lesson_ids": self.lesson_ids,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateVersion":
        """Create from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class Template:
    """Represents a GCP primitive template."""

    def __init__(
        self,
        template_id: str,
        template_type: str,
        content: str,
        validations: Optional[List[str]] = None,
        defaults: Optional[Dict[str, Any]] = None,
        pre_deployment_checks: Optional[List[str]] = None,
        version: int = 1,
        changelog: Optional[List[Dict[str, Any]]] = None,
    ):
        self.template_id = template_id
        self.template_type = template_type  # cloud-run, cloud-function, firestore, etc.
        self.content = content
        self.validations = validations or []
        self.defaults = defaults or {}
        self.pre_deployment_checks = pre_deployment_checks or []
        self.version = version
        self.changelog = changelog or []

        # Template metadata
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.effectiveness_score: Optional[float] = None
        self.usage_count = 0

    def add_validation(self, validation: str, lesson_id: str) -> None:
        """Add a validation rule to the template."""
        if validation not in self.validations:
            self.validations.append(validation)
            self._update_version(f"Added validation: {validation}", lesson_id)

    def add_default(self, field: str, value: Any, lesson_id: str) -> None:
        """Add a default value to the template."""
        self.defaults[field] = value
        self._update_version(f"Added default {field} = {value}", lesson_id)

    def add_check(self, check: str, lesson_id: str) -> None:
        """Add a pre-deployment check."""
        if check not in self.pre_deployment_checks:
            self.pre_deployment_checks.append(check)
            self._update_version(f"Added check: {check}", lesson_id)

    def _update_version(self, change_description: str, lesson_id: str) -> None:
        """Update template version and changelog."""
        self.version += 1
        self.updated_at = datetime.now()
        self.changelog.append(
            {
                "version": self.version,
                "change": change_description,
                "lesson_id": lesson_id,
                "date": self.updated_at.isoformat(),
            }
        )

        logger.info(f"Updated template {self.template_id} to version {self.version}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "template_id": self.template_id,
            "template_type": self.template_type,
            "content": self.content,
            "validations": self.validations,
            "defaults": self.defaults,
            "pre_deployment_checks": self.pre_deployment_checks,
            "version": self.version,
            "changelog": self.changelog,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "effectiveness_score": self.effectiveness_score,
            "usage_count": self.usage_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Template":
        """Create from dictionary."""
        template = cls(
            template_id=data["template_id"],
            template_type=data["template_type"],
            content=data["content"],
            validations=data.get("validations", []),
            defaults=data.get("defaults", {}),
            pre_deployment_checks=data.get("pre_deployment_checks", []),
            version=data.get("version", 1),
            changelog=data.get("changelog", []),
        )

        if "created_at" in data:
            template.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            template.updated_at = datetime.fromisoformat(data["updated_at"])
        template.effectiveness_score = data.get("effectiveness_score")
        template.usage_count = data.get("usage_count", 0)

        return template


class TemplateRegistry:
    """Registry for managing GCP primitive templates."""

    def __init__(self, templates_path: Optional[Path] = None):
        self.templates_path = templates_path or Path.cwd() / "templates" / "archetypes"
        self.templates: Dict[str, Template] = {}
        self.versions: Dict[str, List[TemplateVersion]] = {}

        logger.info(f"Initialized TemplateRegistry at {self.templates_path}")

    async def load_templates(self) -> None:
        """Load all templates from the templates directory."""
        logger.info("Loading templates from registry")

        # Load existing templates from filesystem
        await self._load_gcp_primitives()

        # Load template metadata if exists
        metadata_path = self.templates_path / "registry.json"
        if metadata_path.exists():
            await self._load_template_metadata(metadata_path)

    async def _load_gcp_primitives(self) -> None:
        """Load GCP primitive templates from filesystem."""
        primitive_types = [
            "cloud-run",
            "cloud-function",
            "firestore",
            "pubsub",
            "cloud-storage",
            "cloudsql",
        ]

        for primitive_type in primitive_types:
            primitive_dir = self.templates_path / primitive_type
            if primitive_dir.exists():
                await self._load_primitive_template(primitive_type, primitive_dir)

    async def _load_primitive_template(
        self, primitive_type: str, primitive_dir: Path
    ) -> None:
        """Load a specific primitive template."""
        main_tf = primitive_dir / "main.tf"
        if main_tf.exists():
            content = await asyncio.to_thread(main_tf.read_text)

            template = Template(
                template_id=primitive_type,
                template_type=primitive_type,
                content=content,
            )

            self.templates[primitive_type] = template
            logger.info(f"Loaded template: {primitive_type}")

    async def _load_template_metadata(self, metadata_path: Path) -> None:
        """Load template metadata from registry file."""
        try:
            content = await asyncio.to_thread(metadata_path.read_text)
            data = json.loads(content)

            for template_id, template_data in data.get("templates", {}).items():
                if template_id in self.templates:
                    # Update template with metadata
                    template = Template.from_dict(template_data)
                    template.content = self.templates[template_id].content
                    self.templates[template_id] = template

        except Exception as e:
            logger.warning(f"Could not load template metadata: {e}")

    async def save_registry(self) -> None:
        """Save template registry to filesystem."""
        metadata_path = self.templates_path / "registry.json"

        registry_data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "templates": {
                template_id: template.to_dict()
                for template_id, template in self.templates.items()
            },
        }

        content = json.dumps(registry_data, indent=2)
        await asyncio.to_thread(metadata_path.write_text, content)

        logger.info("Saved template registry")

    def get(self, template_id: str) -> Optional[Template]:
        """Get template by ID."""
        return self.templates.get(template_id)

    def list_templates(self) -> List[str]:
        """List all template IDs."""
        return list(self.templates.keys())

    async def create_backup(self, template_id: str) -> Path:
        """Create backup of template before modification."""
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        backup_dir = self.templates_path / "backups" / template_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"v{template.version}_{timestamp}.json"

        backup_data = template.to_dict()
        content = json.dumps(backup_data, indent=2)
        await asyncio.to_thread(backup_path.write_text, content)

        logger.info(f"Created backup for template {template_id} at {backup_path}")
        return backup_path


class TemplateEvolution:
    """Evolves templates based on lessons learned."""

    def __init__(self, template_registry: TemplateRegistry):
        self.templates = template_registry
        self.effectiveness_tracker = EffectivenessTracker()

    async def apply_lessons_to_templates(
        self, lessons: List[ProcessedLesson]
    ) -> Dict[str, Any]:
        """Update templates with learned improvements."""
        logger.info(f"Applying {len(lessons)} lessons to templates")

        results: Dict[str, Any] = {
            "templates_updated": 0,
            "actions_applied": 0,
            "failed_updates": 0,
            "success": True,
            "updated_templates": [],
        }

        for lesson in lessons:
            if lesson.priority.value >= Priority.MEDIUM.value:
                try:
                    await self._apply_lesson_actions(lesson)
                    results["templates_updated"] += 1
                    results["actions_applied"] += (
                        len(lesson.actions) if hasattr(lesson, "actions") else 0
                    )
                    results["updated_templates"].append(lesson.lesson_id)

                except Exception as e:
                    logger.error(f"Failed to apply lesson {lesson.lesson_id}: {e}")
                    results["failed_updates"] += 1

        # Save updated registry
        await self.templates.save_registry()

        if results["failed_updates"] > 0:
            results["success"] = False

        return results

    async def _apply_lesson_actions(self, lesson) -> None:
        """Apply all actions from a processed lesson or generate actions for enhanced lesson."""
        # Handle both ProcessedLesson and EnhancedLesson
        if hasattr(lesson, "actions"):
            # ProcessedLesson - use existing actions
            for action in lesson.actions:
                if action.action_type == ActionType.UPDATE_TEMPLATE:
                    await self.update_template(action)
        else:
            # EnhancedLesson - generate basic template action
            from solve.lesson_capture_system import UpdateTemplateAction

            if lesson.category.value == "template" or lesson.affected_template:
                action = UpdateTemplateAction(
                    template_id=lesson.affected_template or "cloud-run",
                    update_type="add_validation",
                    validation_rule=lesson.fix,
                    description=f"Add validation based on lesson: {lesson.issue_type}",
                    lesson_id=lesson.lesson_id,
                    priority=lesson.priority,
                )
                await self.update_template(action)

    async def update_template(self, action: UpdateTemplateAction) -> None:
        """Apply specific update to template."""
        template = self.templates.get(action.template_id)
        if not template:
            # Create new template if it doesn't exist
            template = await self._create_template_from_action(action)
            self.templates.templates[action.template_id] = template

        # Create backup before modification
        await self.templates.create_backup(action.template_id)

        # Apply the update
        if action.update_type == "add_validation":
            template.add_validation(action.validation_rule, action.lesson_id)
        elif action.update_type == "add_default":
            template.add_default(action.field, action.value, action.lesson_id)
        elif action.update_type == "add_check":
            template.add_check(action.check, action.lesson_id)
        else:
            logger.warning(f"Unknown update type: {action.update_type}")

        logger.info(f"Applied update to template {action.template_id}")

    async def _create_template_from_action(
        self, action: UpdateTemplateAction
    ) -> Template:
        """Create a new template based on action requirements."""
        logger.info(f"Creating new template: {action.template_id}")

        # Basic template content based on template type
        template_content = self._generate_basic_template_content(action.template_id)

        return Template(
            template_id=action.template_id,
            template_type=action.template_id,
            content=template_content,
            validations=[],
            defaults={},
            pre_deployment_checks=[],
        )

    def _generate_basic_template_content(self, template_type: str) -> str:
        """Generate basic template content for a template type."""
        if template_type == "cloud-run":
            return """
resource "google_cloud_run_service" "default" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      containers {
        image = var.image_url

        resources {
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
        }

        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
      }
    }
  }
}
"""
        elif template_type == "cloud-function":
            return """
resource "google_cloudfunctions_function" "default" {
  name        = var.function_name
  runtime     = var.runtime
  entry_point = var.entry_point

  source_archive_bucket = var.bucket_name
  source_archive_object = var.zip_file

  trigger {
    http_trigger {}
  }

  environment_variables = var.environment_variables
}
"""
        else:
            return f"""
# Basic template for {template_type}
# Generated automatically based on lesson learned
"""

    async def validate_template_update(self, template_id: str) -> Dict[str, Any]:
        """Validate that a template update is syntactically correct."""
        template = self.templates.get(template_id)
        if not template:
            return {"valid": False, "error": "Template not found"}

        try:
            # Basic syntax validation for Terraform
            if (
                "resource" in template.content
                and "{" in template.content
                and "}" in template.content
            ):
                validation_result: Dict[str, Any] = {"valid": True, "checks_passed": []}

                # Check for required fields based on template type
                required_checks = {
                    "cloud-run": ["google_cloud_run_service", "name", "location"],
                    "cloud-function": [
                        "google_cloudfunctions_function",
                        "name",
                        "runtime",
                    ],
                    "firestore": ["google_firestore_database", "name"],
                    "pubsub": ["google_pubsub_topic", "name"],
                }

                if template.template_type in required_checks:
                    for required_field in required_checks[template.template_type]:
                        if required_field in template.content:
                            validation_result["checks_passed"].append(
                                f"Has {required_field}"
                            )
                        else:
                            validation_result["valid"] = False
                            validation_result[
                                "error"
                            ] = f"Missing required field: {required_field}"
                            break

                return validation_result
            else:
                return {"valid": False, "error": "Invalid template syntax"}

        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def rollback_template(self, template_id: str, target_version: int) -> bool:
        """Rollback template to a previous version."""
        logger.info(f"Rolling back template {template_id} to version {target_version}")

        try:
            # Find backup file
            backup_dir = self.templates.templates_path / "backups" / template_id
            if not backup_dir.exists():
                logger.error(f"No backups found for template {template_id}")
                return False

            # Find closest version backup
            backup_files = list(backup_dir.glob(f"v{target_version}_*.json"))
            if not backup_files:
                logger.error(f"No backup found for version {target_version}")
                return False

            # Load backup
            backup_file = backup_files[0]  # Take first match
            content = await asyncio.to_thread(backup_file.read_text)
            backup_data = json.loads(content)

            # Restore template
            restored_template = Template.from_dict(backup_data)
            self.templates.templates[template_id] = restored_template

            logger.info(f"Successfully rolled back template {template_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback template {template_id}: {e}")
            return False


class EffectivenessTracker:
    """Tracks effectiveness of template changes based on lessons."""

    def __init__(self) -> None:
        self.metrics: Dict[str, Dict[str, Any]] = {}

    async def track_template_effectiveness(
        self, template_id: str, lesson_ids: List[str], timeframe: int = 30
    ) -> float:
        """Measure if template changes prevented similar issues."""
        logger.info(f"Tracking effectiveness for template {template_id}")

        try:
            # This would integrate with the lesson store to check if similar issues
            # have been reduced after template updates

            # For now, return a simulated effectiveness score
            # In production, this would analyze actual incident rates
            base_effectiveness = 0.75

            # Increase effectiveness based on number of lessons incorporated
            lesson_bonus = min(len(lesson_ids) * 0.05, 0.2)

            effectiveness = base_effectiveness + lesson_bonus

            self.metrics[template_id] = {
                "effectiveness": effectiveness,
                "lessons_applied": len(lesson_ids),
                "measured_at": datetime.now().isoformat(),
                "timeframe_days": timeframe,
            }

            return effectiveness

        except Exception as e:
            logger.error(f"Failed to track effectiveness for {template_id}: {e}")
            return 0.0

    def get_effectiveness_metrics(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get effectiveness metrics for a template."""
        return self.metrics.get(template_id)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all effectiveness metrics."""
        return self.metrics.copy()


# Integration functions for Issue #80


async def create_template_evolution_system(
    templates_path: Optional[Path] = None,
) -> TemplateEvolution:
    """Create and initialize the template evolution system."""
    registry = TemplateRegistry(templates_path)
    await registry.load_templates()

    evolution = TemplateEvolution(registry)

    logger.info("Template evolution system initialized")
    return evolution


async def apply_lessons_to_archetypes(
    lessons: List[ProcessedLesson], templates_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Apply lessons to GCP primitive archetypes."""
    evolution = await create_template_evolution_system(templates_path)
    return await evolution.apply_lessons_to_templates(lessons)
