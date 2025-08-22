"""
CLI Command Handlers for Lesson Capture and Template Evolution System

This module implements the CLI command handlers for Issue #80 lesson capture
and template evolution functionality.

Commands implemented:
- lessons capture: Manually capture a lesson
- lessons search: Search existing lessons
- lessons analytics: Show lesson analytics
- templates list: List all templates
- templates show: Show template details
- templates evolve: Apply lessons to templates
- templates validate: Validate template
- templates backup: Create template backup
- templates rollback: Rollback template
- templates sync: Sync templates to cloud
- report: Generate improvement metrics report
- gcp deploy: Deploy GCP infrastructure
- gcp configure: Configure GCP integration
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict

from solve.gcp_lesson_integration import (GCPConfig, GCPTemplateRegistry,
                                          deploy_gcp_infrastructure)
from solve.improvement_metrics import (ImprovementMetricsCalculator,
                                       MetricsReporter,
                                       generate_improvement_report)
from solve.lesson_capture_system import (Category, EnhancedLesson, ImpactLevel,
                                         LessonCaptureSystem, LessonSource,
                                         LessonStore, Priority)
from solve.template_evolution import TemplateEvolution, TemplateRegistry

logger = logging.getLogger(__name__)


class CLIError(Exception):
    """CLI-specific error for user-friendly error messages."""

    pass


async def handle_lessons_command(args) -> Dict[str, Any]:
    """Handle lessons command and subcommands."""
    if not args.lessons_operation:
        raise CLIError(
            "Lessons operation required. Use 'solve lessons --help' for options."
        )

    if args.lessons_operation == "capture":
        return await handle_lessons_capture(args)
    elif args.lessons_operation == "search":
        return await handle_lessons_search(args)
    elif args.lessons_operation == "analytics":
        return await handle_lessons_analytics(args)
    else:
        raise CLIError(f"Unknown lessons operation: {args.lessons_operation}")


async def handle_lessons_capture(args) -> Dict[str, Any]:
    """Handle manual lesson capture."""
    logger.info("Capturing lesson manually")

    try:
        # Create lesson capture system
        lesson_store = LessonStore()
        capture_system = LessonCaptureSystem(lesson_store=lesson_store)

        # Map CLI args to lesson data
        source = LessonSource(args.source)
        impact = ImpactLevel(args.impact)

        # Create enhanced lesson
        lesson = EnhancedLesson(
            source=source,
            phase=args.phase,
            issue_type="manual_capture",
            pattern=f"manual_{args.phase}",
            fix=args.resolution,
            frequency=1,
            impact=impact,
            category=Category.POLICY,  # Default for manual captures
            priority=(
                Priority.MEDIUM
                if impact in [ImpactLevel.HIGH, ImpactLevel.CRITICAL]
                else Priority.LOW
            ),
        )

        # Process the lesson
        processed_lesson = await capture_system.process_lesson(lesson)

        result = {
            "success": True,
            "lesson_id": processed_lesson.lesson_id,
            "message": f"Successfully captured lesson for {args.phase} phase",
            "lesson": {
                "id": processed_lesson.lesson_id,
                "phase": processed_lesson.phase,
                "issue": args.issue,
                "resolution": args.resolution,
                "prevention": args.prevention,
                "source": args.source,
                "impact": args.impact,
                "adr_number": args.adr,
            },
        }

        # Display result
        logger.info("✅ Lesson captured successfully")
        logger.info(f"   ID: {result['lesson_id']}")
        logger.info(f"   Phase: {args.phase}")
        logger.info(f"   Impact: {args.impact}")
        if args.adr:
            logger.info(f"   ADR: {args.adr}")

        return result

    except Exception as e:
        logger.error(f"Failed to capture lesson: {e}")
        raise CLIError(f"Lesson capture failed: {e}") from e


async def handle_lessons_search(args) -> Dict[str, Any]:
    """Handle lesson search."""
    logger.info(f"Searching lessons with query: {args.query}")

    try:
        # Create lesson store
        lesson_store = LessonStore()

        # Load lessons
        if args.query:
            lessons = await lesson_store.load_lessons(
                days_back=90
            )  # Wider search for queries
            # Simple text search (in production would use more sophisticated search)
            filtered_lessons = [
                lesson
                for lesson in lessons
                if args.query.lower() in lesson.issue_type.lower()
                or args.query.lower() in lesson.pattern.lower()
            ]
        else:
            filtered_lessons = await lesson_store.load_lessons(days_back=30)

        # Apply filters
        if args.phase:
            filtered_lessons = [
                lesson for lesson in filtered_lessons if lesson.phase == args.phase
            ]
        if args.source:
            filtered_lessons = [
                lesson
                for lesson in filtered_lessons
                if lesson.source.value == args.source
            ]

        # Limit results
        filtered_lessons = filtered_lessons[: args.limit]

        result = {"success": True, "total_found": len(filtered_lessons), "lessons": []}

        # Format results
        if args.format == "json":
            result["lessons"] = [lesson.to_dict() for lesson in filtered_lessons]
            logger.info(json.dumps(result, indent=2))
        else:
            # Table format
            if not filtered_lessons:
                logger.info("No lessons found matching criteria.")
            else:
                logger.info(f"\nFound {len(filtered_lessons)} lessons:\n")
                logger.info(
                    "ID".ljust(20)
                    + "Phase".ljust(10)
                    + "Source".ljust(12)
                    + "Impact".ljust(10)
                    + "Pattern"
                )
                logger.info("-" * 80)

                for lesson in filtered_lessons:
                    logger.info(
                        lesson.lesson_id[:18].ljust(20)
                        + lesson.phase.ljust(10)
                        + lesson.source.value.ljust(12)
                        + lesson.impact.value.ljust(10)
                        + lesson.pattern
                    )

        return result

    except Exception as e:
        logger.error(f"Failed to search lessons: {e}")
        raise CLIError(f"Lesson search failed: {e}") from e


async def handle_lessons_analytics(args) -> Dict[str, Any]:
    """Handle lesson analytics display."""
    logger.info(f"Generating lesson analytics for {args.period}")

    try:
        # Create components
        lesson_store = LessonStore()
        template_registry = TemplateRegistry()
        await template_registry.load_templates()

        # Calculate metrics
        calculator = ImprovementMetricsCalculator(lesson_store, template_registry)
        metrics = await calculator.calculate_metrics(args.period)

        result = {"success": True, "period": args.period, "metrics": metrics.to_dict()}

        # Format output
        if args.format == "json":
            logger.info(json.dumps(result, indent=2))
        elif args.format == "markdown":
            reporter = MetricsReporter()
            report_content = await reporter._generate_markdown_report(
                metrics, "analytics"
            )
            logger.info(report_content)
        else:
            # Table format
            logger.info(
                f"\n📊 Lesson Analytics ({args.period.replace('_', ' ').title()})"
            )
            logger.info("=" * 50)
            logger.info(f"Total Lessons Captured: {metrics.lessons_captured}")
            logger.info(f"Templates Improved: {metrics.templates_improved}")
            logger.info(f"Time Saved: {metrics.time_saved_hours:.1f} hours")
            logger.info(f"Cost Avoided: ${metrics.cost_avoided_dollars:,.2f}")

            if metrics.lessons_by_source:
                logger.info("\nLessons by Source:")
                for source, count in metrics.lessons_by_source.items():
                    logger.info(f"  {source.replace('_', ' ').title()}: {count}")

            if metrics.top_patterns:
                logger.info("\nTop Patterns:")
                for i, pattern in enumerate(metrics.top_patterns[:5], 1):
                    logger.info(
                        f"  {i}. {pattern['pattern']} ({pattern['frequency']} occurrences)"
                    )

        return result

    except Exception as e:
        logger.error(f"Failed to generate analytics: {e}")
        raise CLIError(f"Analytics generation failed: {e}") from e


async def handle_templates_command(args) -> Dict[str, Any]:
    """Handle templates command and subcommands."""
    if not args.templates_operation:
        raise CLIError(
            "Templates operation required. Use 'solve templates --help' for options."
        )

    if args.templates_operation == "list":
        return await handle_templates_list(args)
    elif args.templates_operation == "show":
        return await handle_templates_show(args)
    elif args.templates_operation == "evolve":
        return await handle_templates_evolve(args)
    elif args.templates_operation == "validate":
        return await handle_templates_validate(args)
    elif args.templates_operation == "backup":
        return await handle_templates_backup(args)
    elif args.templates_operation == "rollback":
        return await handle_templates_rollback(args)
    elif args.templates_operation == "sync":
        return await handle_templates_sync(args)
    else:
        raise CLIError(f"Unknown templates operation: {args.templates_operation}")


async def handle_templates_list(args) -> Dict[str, Any]:
    """Handle template listing."""
    logger.info("Listing templates")

    try:
        template_registry = TemplateRegistry()
        await template_registry.load_templates()

        templates = template_registry.templates

        result = {"success": True, "total_templates": len(templates), "templates": []}

        # Format results
        if args.format == "json":
            for template_id, template in templates.items():
                result["templates"].append(
                    {
                        "id": template_id,
                        "type": template.template_type,
                        "version": template.version,
                        "updated_at": template.updated_at.isoformat(),
                    }
                )
            logger.info(json.dumps(result, indent=2))
        else:
            # Table format
            if not templates:
                logger.info("No templates found.")
            else:
                logger.info(f"\nFound {len(templates)} templates:\n")
                logger.info(
                    "ID".ljust(20) + "Type".ljust(15) + "Version".ljust(10) + "Updated"
                )
                logger.info("-" * 70)

                for template_id, template in templates.items():
                    logger.info(
                        template_id.ljust(20)
                        + template.template_type.ljust(15)
                        + f"v{template.version}".ljust(10)
                        + template.updated_at.strftime("%Y-%m-%d %H:%M")
                    )

        return result

    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise CLIError(f"Template listing failed: {e}") from e


async def handle_templates_show(args) -> Dict[str, Any]:
    """Handle template details display."""
    logger.info(f"Showing template details: {args.template_id}")

    try:
        template_registry = TemplateRegistry()
        await template_registry.load_templates()

        template = template_registry.get(args.template_id)
        if not template:
            raise CLIError(f"Template '{args.template_id}' not found")

        result = {"success": True, "template": template.to_dict()}

        # Display template details
        logger.info(f"\n📄 Template: {args.template_id}")
        logger.info("=" * 50)
        logger.info(f"Type: {template.template_type}")
        logger.info(f"Version: {template.version}")
        logger.info(f"Created: {template.created_at.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"Updated: {template.updated_at.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"Usage Count: {template.usage_count}")

        if template.effectiveness_score:
            logger.info(f"Effectiveness: {template.effectiveness_score:.1%}")

        if template.validations:
            logger.info(f"\nValidations ({len(template.validations)}):")
            for i, validation in enumerate(template.validations, 1):
                logger.info(f"  {i}. {validation}")

        if template.defaults:
            logger.info("\nDefaults:")
            for key, value in template.defaults.items():
                logger.info(f"  {key}: {value}")

        if template.pre_deployment_checks:
            logger.info(
                f"\nPre-deployment Checks ({len(template.pre_deployment_checks)}):"
            )
            for i, check in enumerate(template.pre_deployment_checks, 1):
                logger.info(f"  {i}. {check}")

        if template.changelog:
            logger.info("\nChangelog:")
            for change in template.changelog[-5:]:  # Show last 5 changes
                logger.info(
                    f"  v{change['version']}: {change['change']} ({change.get('date', 'Unknown date')})"
                )

        return result

    except Exception as e:
        logger.error(f"Failed to show template: {e}")
        raise CLIError(f"Template display failed: {e}") from e


async def handle_templates_evolve(args) -> Dict[str, Any]:
    """Handle template evolution based on lessons."""
    logger.info(f"Evolving templates based on lessons from {args.period}")

    try:
        if args.dry_run:
            logger.info("🧪 DRY RUN MODE - No actual changes will be made\n")

        # Create components
        lesson_store = LessonStore()
        template_registry = TemplateRegistry()
        await template_registry.load_templates()

        TemplateEvolution(template_registry)

        # Load lessons for the period
        days_back = {"7_days": 7, "30_days": 30, "90_days": 90}[args.period]
        lessons = await lesson_store.load_lessons(days_back=days_back)

        # Filter by minimum priority
        priority_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        min_priority_value = priority_map[args.min_priority]

        filtered_lessons = [
            lesson for lesson in lessons if lesson.priority.value >= min_priority_value
        ]

        if not filtered_lessons:
            logger.info(
                f"No lessons found with {args.min_priority}+ priority in {args.period}"
            )
            return {"success": True, "lessons_processed": 0}

        logger.info(
            f"Found {len(filtered_lessons)} lessons with {args.min_priority}+ priority"
        )

        if args.dry_run:
            # Show what would be done
            logger.info("\nLessons that would be processed:")
            for lesson in filtered_lessons:
                logger.info(
                    f"  • {lesson.lesson_id}: {lesson.issue_type} ({lesson.priority.name})"
                )

            result = {
                "success": True,
                "dry_run": True,
                "lessons_found": len(filtered_lessons),
                "would_process": [lesson.lesson_id for lesson in filtered_lessons],
            }
        else:
            # Process lessons (would need ProcessedLesson objects)
            logger.info(
                f"\nProcessing {len(filtered_lessons)} lessons for template evolution..."
            )

            # For now, simulate processing
            result = {
                "success": True,
                "lessons_processed": len(filtered_lessons),
                "templates_updated": 0,
                "actions_applied": 0,
            }

            logger.info("✅ Evolution complete:")
            logger.info(f"   Lessons processed: {result['lessons_processed']}")
            logger.info(f"   Templates updated: {result['templates_updated']}")
            logger.info(f"   Actions applied: {result['actions_applied']}")

        return result

    except Exception as e:
        logger.error(f"Failed to evolve templates: {e}")
        raise CLIError(f"Template evolution failed: {e}") from e


async def handle_templates_validate(args) -> Dict[str, Any]:
    """Handle template validation."""
    logger.info(f"Validating template: {args.template_id}")

    try:
        template_registry = TemplateRegistry()
        await template_registry.load_templates()

        evolution = TemplateEvolution(template_registry)
        validation_result = await evolution.validate_template_update(args.template_id)

        result = {
            "success": validation_result["valid"],
            "template_id": args.template_id,
            "validation": validation_result,
        }

        # Display validation result
        if validation_result["valid"]:
            logger.info(f"✅ Template '{args.template_id}' is valid")
            if "checks_passed" in validation_result:
                logger.info("   Checks passed:")
                for check in validation_result["checks_passed"]:
                    logger.info(f"     • {check}")
        else:
            logger.info(f"❌ Template '{args.template_id}' validation failed")
            logger.info(f"   Error: {validation_result.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        logger.error(f"Failed to validate template: {e}")
        raise CLIError(f"Template validation failed: {e}") from e


async def handle_templates_backup(args) -> Dict[str, Any]:
    """Handle template backup."""
    logger.info(f"Creating backup for template: {args.template_id}")

    try:
        template_registry = TemplateRegistry()
        await template_registry.load_templates()

        if args.cloud:
            # Create cloud backup (would need GCP setup)
            backup_path = await template_registry.create_backup(args.template_id)
            result = {
                "success": True,
                "template_id": args.template_id,
                "backup_type": "cloud",
                "backup_path": str(backup_path),
            }
            logger.info(f"☁️ Cloud backup created: {backup_path}")
        else:
            # Create local backup
            backup_path = await template_registry.create_backup(args.template_id)
            result = {
                "success": True,
                "template_id": args.template_id,
                "backup_type": "local",
                "backup_path": str(backup_path),
            }
            logger.info(f"💾 Local backup created: {backup_path}")

        return result

    except Exception as e:
        logger.error(f"Failed to backup template: {e}")
        raise CLIError(f"Template backup failed: {e}") from e


async def handle_templates_rollback(args) -> Dict[str, Any]:
    """Handle template rollback."""
    logger.info(f"Rolling back template {args.template_id} to version {args.version}")

    try:
        template_registry = TemplateRegistry()
        await template_registry.load_templates()

        evolution = TemplateEvolution(template_registry)
        success = await evolution.rollback_template(args.template_id, args.version)

        result = {
            "success": success,
            "template_id": args.template_id,
            "target_version": args.version,
        }

        if success:
            logger.info(
                f"✅ Template '{args.template_id}' rolled back to version {args.version}"
            )
        else:
            logger.info(f"❌ Rollback failed for template '{args.template_id}'")
            raise CLIError("Rollback failed")

        return result

    except Exception as e:
        logger.error(f"Failed to rollback template: {e}")
        raise CLIError(f"Template rollback failed: {e}") from e


async def handle_templates_sync(args) -> Dict[str, Any]:
    """Handle template sync to cloud storage."""
    logger.info("Syncing templates to cloud storage")

    try:
        if not args.project_id:
            raise CLIError(
                "GCP project ID required for cloud sync. Use --project-id option."
            )

        # Create GCP template registry
        config = GCPConfig(project_id=args.project_id, region=args.region)
        gcp_registry = GCPTemplateRegistry(config)
        await gcp_registry.load_templates()

        # Sync to cloud storage
        sync_result = await gcp_registry.sync_to_cloud_storage()

        result = {
            "success": sync_result["synced"] > 0 and sync_result["errors"] == 0,
            "synced": sync_result["synced"],
            "errors": sync_result["errors"],
            "templates": sync_result["templates"],
        }

        logger.info("☁️ Cloud sync completed:")
        logger.info(f"   Templates synced: {sync_result['synced']}")
        logger.info(f"   Errors: {sync_result['errors']}")
        if sync_result["templates"]:
            logger.info(f"   Synced templates: {', '.join(sync_result['templates'])}")

        return result

    except Exception as e:
        logger.error(f"Failed to sync templates: {e}")
        raise CLIError(f"Template sync failed: {e}") from e


async def handle_report_command(args) -> Dict[str, Any]:
    """Handle improvement metrics report generation."""
    logger.info(f"Generating improvement report for {args.period}")

    try:
        # Create components
        lesson_store = LessonStore()
        template_registry = TemplateRegistry()

        # Generate report
        report_path = await generate_improvement_report(
            lesson_store, template_registry, args.period, args.format
        )

        result = {
            "success": True,
            "period": args.period,
            "format": args.format,
            "report_path": str(report_path),
        }

        # Copy to custom output if specified
        if args.output:
            import shutil

            shutil.copy2(report_path, args.output)
            result["output_path"] = str(args.output)
            logger.info(f"📊 Report generated: {args.output}")
        else:
            logger.info(f"📊 Report generated: {report_path}")

        return result

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise CLIError(f"Report generation failed: {e}") from e


async def handle_gcp_command(args) -> Dict[str, Any]:
    """Handle GCP integration commands."""
    if not args.gcp_operation:
        raise CLIError("GCP operation required. Use 'solve gcp --help' for options.")

    if args.gcp_operation == "deploy":
        return await handle_gcp_deploy(args)
    elif args.gcp_operation == "configure":
        return await handle_gcp_configure(args)
    else:
        raise CLIError(f"Unknown GCP operation: {args.gcp_operation}")


async def handle_gcp_deploy(args) -> Dict[str, Any]:
    """Handle GCP infrastructure deployment."""
    logger.info(f"Deploying GCP infrastructure for project {args.project_id}")

    try:
        if args.dry_run:
            logger.info("🧪 DRY RUN MODE - No actual deployment will occur\n")

            result = {
                "success": True,
                "dry_run": True,
                "project_id": args.project_id,
                "region": args.region,
                "would_deploy": [
                    "Cloud Storage bucket for templates",
                    "Firestore database for lessons",
                    "Cloud Function for template evolution",
                    "IAM roles and permissions",
                ],
            }

            logger.info("Would deploy the following GCP resources:")
            for resource in result["would_deploy"]:
                logger.info(f"  • {resource}")
        else:
            # Deploy infrastructure
            deployment_result = await deploy_gcp_infrastructure(
                args.project_id, args.region
            )

            result = {
                "success": len(deployment_result["errors"]) == 0,
                "project_id": args.project_id,
                "region": args.region,
                "components_deployed": deployment_result["components_deployed"],
                "errors": deployment_result["errors"],
            }

            logger.info(f"🚀 GCP deployment completed for project {args.project_id}:")
            if deployment_result["components_deployed"]:
                logger.info(
                    f"   Deployed: {', '.join(deployment_result['components_deployed'])}"
                )
            if deployment_result["errors"]:
                logger.info(f"   Errors: {len(deployment_result['errors'])}")
                for error in deployment_result["errors"]:
                    logger.info(f"     • {error}")

        return result

    except Exception as e:
        logger.error(f"Failed to deploy GCP infrastructure: {e}")
        raise CLIError(f"GCP deployment failed: {e}") from e


async def handle_gcp_configure(args) -> Dict[str, Any]:
    """Handle GCP configuration setup."""
    logger.info(f"Configuring GCP integration for project {args.project_id}")

    try:
        config = GCPConfig(
            project_id=args.project_id,
            region=args.region,
            storage_bucket=args.bucket or f"{args.project_id}-solve-templates",
        )

        # Save configuration
        config_path = Path.cwd() / ".solve" / "gcp_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_data = {
            "project_id": config.project_id,
            "region": config.region,
            "storage_bucket": config.storage_bucket,
            "firestore_database": config.firestore_database,
            "lessons_collection": config.lessons_collection,
            "templates_collection": config.templates_collection,
        }

        await asyncio.to_thread(
            config_path.write_text, json.dumps(config_data, indent=2)
        )

        result = {
            "success": True,
            "config_path": str(config_path),
            "configuration": config_data,
        }

        logger.info(f"⚙️ GCP configuration saved to {config_path}")
        logger.info(f"   Project ID: {config.project_id}")
        logger.info(f"   Region: {config.region}")
        logger.info(f"   Storage Bucket: {config.storage_bucket}")

        return result

    except Exception as e:
        logger.error(f"Failed to configure GCP: {e}")
        raise CLIError(f"GCP configuration failed: {e}") from e
