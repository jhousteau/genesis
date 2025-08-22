"""
SOLVE CLI Interface - Graph-Driven Cloud-Native Development Platform

This module provides a comprehensive command-line interface for the SOLVE methodology.
Implements real agent execution with graph database integration for ADR-to-GCP workflows.

Features:
- Phase execution (scaffold, outline, logic, verify, enhance) with real agents
- Graph operations (init, visualize, validate, query)
- ADR parsing and processing
- Constitutional AI safety validation
- Progress tracking and comprehensive error handling
- Dry-run mode for safe testing

Based on Issue #72: Complete CLI Integration
Follows implementation order from docs/IMPLEMENTATION_ORDER.md
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Imports with fallbacks for missing dependencies
try:
    from solve.agents import create_phase_executor

    PHASE_EXECUTORS_AVAILABLE = True
except ImportError:
    PHASE_EXECUTORS_AVAILABLE = False

try:
    from solve.cli_lesson_handlers import CLIError as LessonCLIError
    from solve.cli_lesson_handlers import (handle_gcp_command,
                                           handle_lessons_command,
                                           handle_report_command,
                                           handle_templates_command)

    LESSON_HANDLERS_AVAILABLE = True
except ImportError:
    LESSON_HANDLERS_AVAILABLE = False

try:
    from solve.agents.master_planner import MasterPlannerAgent

    MASTER_PLANNER_AVAILABLE = True
except ImportError:
    MASTER_PLANNER_AVAILABLE = False

try:
    from solve.constitutional_ai import ConstitutionalAI

    CONSTITUTIONAL_AI_AVAILABLE = True
except ImportError:
    CONSTITUTIONAL_AI_AVAILABLE = False

try:
    from solve.terraform import TerraformGenerator
    from solve.terraform.environment_manager import EnvironmentManager
    from solve.terraform.validator import TerraformValidator

    TERRAFORM_AVAILABLE = True
except ImportError:
    TERRAFORM_AVAILABLE = False

try:
    from solve.feature_flags import log_feature_status

    FEATURE_FLAGS_AVAILABLE = True
except ImportError:
    FEATURE_FLAGS_AVAILABLE = False

    def log_feature_status():
        logger.info("Feature flags not available")


try:
    from solve.knowledge_loader import KnowledgeLoader

    KNOWLEDGE_LOADER_AVAILABLE = True
except ImportError:
    KNOWLEDGE_LOADER_AVAILABLE = False

try:
    from solve.models import ADRConfig, AgentTask, Goal, Result, TaskStatus

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    # Simple fallback models
    from dataclasses import dataclass, field
    from enum import Enum
    from typing import Dict, List

    class TaskStatus(Enum):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"

    @dataclass
    class Goal:
        description: str
        context: Dict[str, Any] = field(default_factory=dict)
        constraints: List[str] = field(default_factory=list)
        success_criteria: List[str] = field(default_factory=list)

    @dataclass
    class Result:
        success: bool
        message: str
        artifacts: Dict[str, Any] = field(default_factory=dict)
        metadata: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class AgentTask:
        goal: Goal
        assigned_agent: str
        status: TaskStatus = TaskStatus.PENDING

    @dataclass
    class ADRConfig:
        number: str
        title: str
        status: str
        requirements: List[str] = field(default_factory=list)
        phase_outcomes: Dict[str, List[str]] = field(default_factory=dict)


try:
    from solve.tools.graph_operations import GraphTool

    GRAPH_TOOL_AVAILABLE = True
except ImportError:
    GRAPH_TOOL_AVAILABLE = False

try:
    # from solve.tools.terraform_operations import TerraformTool  # Used conditionally

    TERRAFORM_TOOL_AVAILABLE = True
except ImportError:
    TERRAFORM_TOOL_AVAILABLE = False

try:
    # from solve.tools.gcp_operations import GCPTool  # Used conditionally

    GCP_TOOL_AVAILABLE = True
except ImportError:
    GCP_TOOL_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Progress indicators for better UX
def print_progress(step: str, current: int, total: int) -> None:
    """Log progress indicator."""
    percentage = (current / total) * 100
    progress_bar = "█" * int(percentage // 5) + "░" * (20 - int(percentage // 5))
    # Use info level for progress updates
    logger.info(f"{step}: [{progress_bar}] {percentage:.1f}% ({current}/{total})")
    if current == total:
        logger.info("Progress complete")


class CLIError(Exception):
    """Custom CLI error for better error handling."""

    pass


# ADR parsing functionality
def parse_adr_file(adr_path: Path) -> ADRConfig:
    """Parse ADR file and extract configuration."""
    if not adr_path.exists():
        raise CLIError(f"ADR file not found: {adr_path}")

    try:
        content = adr_path.read_text(encoding="utf-8")

        # Extract ADR number from filename or content
        number = adr_path.stem.split("-")[0] if "-" in adr_path.stem else "000"

        # Extract title (first # heading)
        title = "Untitled ADR"
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Extract status (look for status line)
        status = "proposed"
        for line in content.split("\n"):
            line_lower = line.lower()
            if "status:" in line_lower:
                if "accepted" in line_lower:
                    status = "accepted"
                elif "deprecated" in line_lower:
                    status = "deprecated"
                break

        # Parse phase outcomes and requirements from content
        phase_outcomes = {}
        requirements = []

        # Simple parsing - look for phase headers and collect following content
        current_phase = None
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("## ") and any(
                phase in line.lower()
                for phase in ["scaffold", "outline", "logic", "verify", "enhance"]
            ):
                current_phase = line[3:].lower().split()[0]
                phase_outcomes[current_phase] = []
            elif current_phase and line.startswith("- "):
                phase_outcomes[current_phase].append(line[2:])
            elif line.startswith("- ") and "requirement" in line.lower():
                requirements.append(line[2:])

        return ADRConfig(
            number=number,
            title=title,
            status=status,
            requirements=requirements,
            phase_outcomes=phase_outcomes,
        )

    except Exception as e:
        raise CLIError(f"Failed to parse ADR file {adr_path}: {e}") from e


async def execute_phase(
    phase: str,
    adr_config: Optional[ADRConfig] = None,
    graph_id: Optional[str] = None,
    dry_run: bool = False,
    constitutional_ai: Optional["ConstitutionalAI"] = None,
) -> Result:
    """Execute a SOLVE phase using real agents."""
    try:
        # Check if phase executors are available
        if not PHASE_EXECUTORS_AVAILABLE:
            if dry_run:
                return Result(
                    success=True,
                    message=(
                        f"DRY RUN: {phase} phase would execute with real agents "
                        "(dependencies missing in actual mode)"
                    ),
                    metadata={
                        "phase": phase,
                        "dry_run": dry_run,
                        "note": "Install Google ADK and configure credentials for real execution",
                    },
                )
            else:
                return Result(
                    success=False,
                    message=(
                        f"Phase execution not available - install Google ADK and configure "
                        f"credentials for {phase} phase"
                    ),
                    metadata={
                        "phase": phase,
                        "dry_run": dry_run,
                        "installation_help": (
                            "pip install google-adk and set SOLVE_ADK_PROJECT_ID"
                        ),
                    },
                )

        # Handle dry-run mode with simulated execution
        if dry_run:
            logger.info(f"🧪 DRY RUN: Simulating {phase} phase execution")
            # Create a comprehensive dry-run response without creating real agents

            phase_descriptions = {
                "scaffold": "Would create project structure and development environment",
                "outline": "Would define API interfaces, data schemas, and system contracts",
                "logic": "Would implement core business logic and functionality",
                "verify": "Would add comprehensive tests and validation procedures",
                "enhance": "Would apply optimizations and capture lessons learned",
            }

            artifacts = {
                "phase": phase,
                "would_execute": phase_descriptions.get(
                    phase, f"Would execute {phase} phase"
                ),
                "planned_activities": [
                    f"Parse ADR requirements for {phase} phase",
                    "Create execution plan with specialist assignments",
                    f"Execute {phase}-specific tasks using real ADK agents",
                    "Validate outputs and apply constitutional AI principles",
                    "Generate artifacts and update project state",
                ],
                "required_for_real_execution": [
                    "Set SOLVE_ADK_PROJECT_ID environment variable",
                    "Configure Google Cloud credentials",
                    "Install Google ADK package",
                    "Provide ADR file with --adr flag (optional)",
                ],
            }

            if adr_config:
                artifacts["adr_context"] = {
                    "number": adr_config.number,
                    "title": adr_config.title,
                    "status": adr_config.status,
                    "phase_outcomes": adr_config.phase_outcomes.get(phase, []),
                }

            return Result(
                success=True,
                message=f"DRY RUN: {phase} phase simulation completed successfully",
                artifacts=artifacts,
                metadata={
                    "phase": phase,
                    "dry_run": True,
                    "simulation": "complete",
                    "next_steps": (
                        "Configure credentials and run without --dry-run for real execution"
                    ),
                },
            )

        # Create phase executor for real execution
        try:
            executor = create_phase_executor(phase)
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to create {phase} phase executor: {str(e)}",
                metadata={
                    "phase": phase,
                    "error": str(e),
                    "installation_help": "Install Google ADK and configure credentials",
                },
            )

        # Prepare phase context
        context = {}
        if adr_config:
            context["adr"] = {
                "number": adr_config.number,
                "title": adr_config.title,
                "status": adr_config.status,
                "phase_outcomes": adr_config.phase_outcomes.get(phase, []),
            }

        if graph_id:
            context["graph_id"] = graph_id

        context["dry_run"] = dry_run

        # Create goal for phase execution
        phase_descriptions = {
            "scaffold": "Set up project structure and development environment",
            "outline": "Define API interfaces, data models, and contracts",
            "logic": "Implement core business logic and functionality",
            "verify": "Add comprehensive tests and validation",
            "enhance": "Apply optimizations and capture lessons learned",
        }

        phase_desc = phase_descriptions.get(phase, f"Execute {phase} phase")
        goal = Goal(
            description=f"{phase.title()}: {phase_desc}",
            context=context,
            constraints=[
                f"Stay within {phase} phase boundaries",
                "Follow SOLVE methodology best practices",
                "Ensure all outputs are production-ready",
                "Apply constitutional AI principles",
            ],
            success_criteria=[
                f"{phase.title()} phase objectives completed",
                "All artifacts created and validated",
                "Quality gates passed",
                "Documentation updated",
            ],
        )

        # Create and execute task
        task = AgentTask(
            goal=goal, assigned_agent=executor.name, status=TaskStatus.PENDING
        )

        logger.info(
            f"🚀 Starting {phase} phase execution" + (" (DRY RUN)" if dry_run else "")
        )

        # Execute via phase executor
        result = await executor.execute(task)

        # Constitutional AI validation if available
        if constitutional_ai and not dry_run:
            validation_result = constitutional_ai.validate_decision(
                agent_id=executor.name,
                decision=f"{phase} phase execution completed",
                context={
                    "phase": phase,
                    "result": result.message,
                    "artifacts": result.artifacts,
                },
            )

            if not validation_result.success:
                logger.warning(
                    f"⚠️ Constitutional AI warning: {validation_result.message}"
                )
                result.metadata["constitutional_warnings"] = validation_result.message

        return result

    except Exception as e:
        logger.error(f"❌ Phase {phase} execution failed: {e}")
        return Result(
            success=False,
            message=f"Phase {phase} execution failed: {str(e)}",
            metadata={"phase": phase, "error_type": type(e).__name__},
        )


# Graph operations functionality
async def execute_graph_init(dry_run: bool = False) -> Result:
    """Initialize graph database and create initial schema."""
    try:
        logger.info(
            "🔧 Initializing graph database" + (" (DRY RUN)" if dry_run else "")
        )

        if dry_run:
            return Result(
                success=True,
                message="Graph DB initialization would create schema",
                metadata={"operation": "graph_init", "dry_run": True},
            )

        if not GRAPH_TOOL_AVAILABLE:
            return Result(
                success=False,
                message="Graph operations not available - install neo4j package",
                metadata={
                    "operation": "graph_init",
                    "error": "GraphTool not available",
                    "installation_help": "pip install neo4j",
                },
            )

        # Create graph tool with init-specific safety configuration
        from solve.tools.graph_operations import GraphSafetyConfig

        init_safety_config = GraphSafetyConfig(
            allow_schema_changes=True,  # Allow schema changes during initialization
            max_query_complexity=2000,  # Higher limit for init operations
        )
        graph_tool = GraphTool(safety_config=init_safety_config)

        # Create initial constraints and indexes
        init_queries = [
            "CREATE CONSTRAINT adr_id IF NOT EXISTS FOR (a:ADR) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT system_name IF NOT EXISTS FOR (s:System) REQUIRE s.name IS UNIQUE",
            "CREATE INDEX adr_status IF NOT EXISTS FOR (a:ADR) ON (a.status)",
            "CREATE INDEX system_gcp_project IF NOT EXISTS FOR (s:System) ON (s.gcp_project)",
        ]

        results = []
        for i, query in enumerate(init_queries, 1):
            print_progress("Initializing graph schema", i, len(init_queries))
            result = await graph_tool.query(query)
            results.append(result)

        success = all(r.success for r in results)

        return Result(
            success=success,
            message=(
                "Graph database initialized successfully"
                if success
                else "Graph initialization had errors"
            ),
            artifacts={"init_results": [r.message for r in results]},
            metadata={
                "operation": "graph_init",
                "constraints_created": len(init_queries),
            },
        )

    except Exception as e:
        logger.error(f"❌ Graph initialization failed: {e}")
        return Result(
            success=False,
            message=f"Graph initialization failed: {str(e)}",
            metadata={"operation": "graph_init", "error_type": type(e).__name__},
        )


async def execute_graph_query(
    cypher_query: str,
    parameters: Optional[dict[str, Any]] = None,
    dry_run: bool = False,
) -> Result:
    """Execute a custom Cypher query against the graph database."""
    try:
        logger.info("📊 Executing graph query" + (" (DRY RUN)" if dry_run else ""))

        if dry_run:
            return Result(
                success=True,
                message=f"Would execute query: {cypher_query[:100]}...",
                metadata={"operation": "graph_query", "dry_run": True},
            )

        graph_tool = GraphTool()
        result = await graph_tool.query(cypher_query, parameters)

        return Result(
            success=result.success,
            message=result.message,
            artifacts={"query_results": result.metadata.get("results", [])},
            metadata={
                "operation": "graph_query",
                "result_count": result.result_count,
                "query": cypher_query,
            },
        )

    except Exception as e:
        logger.error(f"❌ Graph query failed: {e}")
        return Result(
            success=False,
            message=f"Graph query failed: {str(e)}",
            metadata={"operation": "graph_query", "error_type": type(e).__name__},
        )


async def execute_graph_validate(
    node_type: Optional[str] = None, dry_run: bool = False
) -> Result:
    """Validate graph contracts and data integrity."""
    try:
        logger.info("✅ Validating graph contracts" + (" (DRY RUN)" if dry_run else ""))

        if dry_run:
            return Result(
                success=True,
                message=f"Would validate contracts for node type: {node_type or 'all'}",
                metadata={"operation": "graph_validate", "dry_run": True},
            )

        graph_tool = GraphTool()

        # Validate specific node type or all major types
        node_types = (
            [node_type] if node_type else ["ADR", "System", "CloudRun", "PubSub"]
        )

        all_results = []
        for i, ntype in enumerate(node_types, 1):
            print_progress("Validating graph contracts", i, len(node_types))
            result = await graph_tool.validate_contracts(ntype)
            all_results.append(result)

        # Aggregate results
        total_issues = sum(r.metadata.get("issues_count", 0) for r in all_results)
        overall_success = all(r.success for r in all_results) and total_issues == 0

        validation_summary = []
        for result in all_results:
            if result.metadata.get("validation_results"):
                validation_summary.extend(result.metadata["validation_results"])

        return Result(
            success=overall_success,
            message=f"Graph validation completed: {total_issues} issues found",
            artifacts={"validation_results": validation_summary},
            metadata={
                "operation": "graph_validate",
                "node_types_checked": len(node_types),
                "total_issues": total_issues,
            },
        )

    except Exception as e:
        logger.error(f"❌ Graph validation failed: {e}")
        return Result(
            success=False,
            message=f"Graph validation failed: {str(e)}",
            metadata={"operation": "graph_validate", "error_type": type(e).__name__},
        )


async def execute_graph_visualize(
    graph_id: Optional[str] = None,
    output_format: str = "ascii",
    dry_run: bool = False,
) -> Result:
    """Visualize graph structure and relationships."""
    try:
        logger.info(
            "🎨 Visualizing graph structure" + (" (DRY RUN)" if dry_run else "")
        )

        if dry_run:
            return Result(
                success=True,
                message=f"Would visualize graph {graph_id or 'entire database'}",
                metadata={"operation": "graph_visualize", "dry_run": True},
            )

        graph_tool = GraphTool()

        # Build visualization query
        if graph_id:
            query = f"""
            MATCH (start {{id: '{graph_id}'}})-[*1..3]-(connected)
            RETURN start, connected, count(*) as connections
            ORDER BY connections DESC
            LIMIT 50
            """
        else:
            query = """
            MATCH (n)-[r]->(m)
            RETURN labels(n) as source_labels, type(r) as relationship,
                   labels(m) as target_labels, count(*) as count
            ORDER BY count DESC
            LIMIT 20
            """

        result = await graph_tool.query(query)

        if result.success:
            # Simple ASCII visualization
            visualization = []
            results = result.metadata.get("results", [])

            if graph_id:
                visualization.append(f"Graph centered on {graph_id}:")
                for item in results[:10]:
                    visualization.append(f"  {item}")
            else:
                visualization.append("Graph overview:")
                for item in results:
                    source = ":".join(item.get("source_labels", []))
                    rel = item.get("relationship", "UNKNOWN")
                    target = ":".join(item.get("target_labels", []))
                    count = item.get("count", 0)
                    visualization.append(f"  ({source})-[{rel}]->({target}) x{count}")

            visualization_text = "\n".join(visualization)
            logger.info(f"Graph visualization:\n{visualization_text}")

            return Result(
                success=True,
                message="Graph visualization completed",
                artifacts={"visualization": visualization_text},
                metadata={
                    "operation": "graph_visualize",
                    "format": output_format,
                    "node_count": len(results),
                },
            )
        else:
            return result

    except Exception as e:
        logger.error(f"❌ Graph visualization failed: {e}")
        return Result(
            success=False,
            message=f"Graph visualization failed: {str(e)}",
            metadata={"operation": "graph_visualize", "error_type": type(e).__name__},
        )


async def execute_terraform_generation(
    graph_id: str,
    output_dir: Path,
    environments: list,
    validate: bool,
    dry_run: bool,
) -> Result:
    """Execute Terraform generation from graph."""
    if dry_run:
        return Result(
            success=True,
            message=f"DRY RUN: Would generate Terraform for graph {graph_id}",
            artifacts={
                "graph_id": graph_id,
                "output_dir": str(output_dir),
                "environments": environments,
                "would_generate": [
                    "main.tf - Root module configuration",
                    "variables.tf - Input variables",
                    "outputs.tf - Output values",
                    "backend.tf - State management",
                    "versions.tf - Provider versions",
                    f"modules/ - {graph_id} service modules",
                    f"environments/ - {', '.join(environments)} tfvars files",
                ],
                "validation": (
                    "Would validate with terraform init and validate"
                    if validate
                    else "Skipped"
                ),
            },
            metadata={"operation": "generate-terraform", "dry_run": True},
        )

    if not TERRAFORM_AVAILABLE:
        return Result(
            success=False,
            message="Terraform generation not available - missing dependencies",
            metadata={"operation": "generate-terraform"},
        )

    try:
        # Import graph connection
        from graph.connection import GraphConnection

        # Initialize generator
        graph_conn = GraphConnection.from_env()
        generator = TerraformGenerator(graph_conn)
        env_manager = EnvironmentManager()

        # Generate Terraform project
        logger.info(f"🔧 Generating Terraform for graph: {graph_id}")
        project = generator.generate_infrastructure(graph_id)

        # Generate environment configs
        logger.info(f"🌍 Generating configs for environments: {environments}")
        graph_data = generator._fetch_graph_data(graph_id)
        env_configs = env_manager.generate_environment_configs(graph_data, environments)
        project.environments = env_configs

        # Write to filesystem
        logger.info(f"📝 Writing Terraform to: {output_dir}")
        project.write_to_filesystem(output_dir)

        # Validate if requested
        validation_results = {}
        if validate:
            logger.info("✓ Validating generated Terraform...")
            validator = TerraformValidator()
            success, errors = validator.validate_project(output_dir)
            validation_results = {
                "validation_success": success,
                "validation_errors": errors if not success else [],
            }

        return Result(
            success=True,
            message=f"Successfully generated Terraform for {graph_id}",
            artifacts={
                "output_directory": str(output_dir),
                "modules_generated": len(project.modules),
                "environments": environments,
                **validation_results,
            },
            metadata={"operation": "generate-terraform", "graph_id": graph_id},
        )

    except Exception as e:
        logger.error(f"Failed to generate Terraform: {e}")
        return Result(
            success=False,
            message=f"Terraform generation failed: {str(e)}",
            metadata={"operation": "generate-terraform", "error": str(e)},
        )


# Main CLI execution logic
async def execute_command(args: argparse.Namespace) -> int:
    """Execute the CLI command based on parsed arguments."""
    try:
        # Initialize Constitutional AI if available
        constitutional_ai = None
        if CONSTITUTIONAL_AI_AVAILABLE and KNOWLEDGE_LOADER_AVAILABLE:
            try:
                knowledge_loader = KnowledgeLoader()
                constitutional_ai = ConstitutionalAI(knowledge_loader)
                logger.info("✅ Constitutional AI initialized")
            except Exception as e:
                logger.warning(f"⚠️ Constitutional AI initialization failed: {e}")
                constitutional_ai = None
        else:
            logger.info("ℹ️ Constitutional AI not available - missing dependencies")

        # Parse ADR file if provided
        adr_config = None
        if hasattr(args, "adr") and args.adr:
            adr_config = parse_adr_file(args.adr)
            logger.info(f"📄 Loaded ADR-{adr_config.number}: {adr_config.title}")

        # Execute based on command
        result = None

        if args.command == "scaffold":
            result = await execute_phase(
                "scaffold",
                adr_config,
                getattr(args, "graph_id", None),
                args.dry_run,
                constitutional_ai,
            )
        elif args.command == "outline":
            result = await execute_phase(
                "outline",
                adr_config,
                getattr(args, "graph_id", None),
                args.dry_run,
                constitutional_ai,
            )
        elif args.command == "logic":
            result = await execute_phase(
                "logic",
                adr_config,
                getattr(args, "graph_id", None),
                args.dry_run,
                constitutional_ai,
            )
        elif args.command == "verify":
            result = await execute_phase(
                "verify",
                adr_config,
                getattr(args, "graph_id", None),
                args.dry_run,
                constitutional_ai,
            )
        elif args.command == "enhance":
            result = await execute_phase(
                "enhance",
                adr_config,
                getattr(args, "graph_id", None),
                args.dry_run,
                constitutional_ai,
            )

        elif args.command == "graph":
            if args.graph_operation == "init":
                result = await execute_graph_init(args.dry_run)
            elif args.graph_operation == "query":
                result = await execute_graph_query(
                    args.cypher,
                    getattr(args, "parameters", None),
                    args.dry_run,
                )
            elif args.graph_operation == "validate":
                result = await execute_graph_validate(
                    getattr(args, "node_type", None),
                    args.dry_run,
                )
            elif args.graph_operation == "visualize":
                result = await execute_graph_visualize(
                    getattr(args, "graph_id", None),
                    getattr(args, "format", "ascii"),
                    args.dry_run,
                )
            elif args.graph_operation == "generate-terraform":
                result = await execute_terraform_generation(
                    args.graph_id,
                    args.output_dir,
                    args.environments,
                    args.validate,
                    args.dry_run,
                )

        elif args.command == "master-plan":
            # Execute master planner for ADR parsing
            if not adr_config:
                raise CLIError("Master planner requires --adr argument")

            # Handle dry-run mode for master planner
            is_master_plan_dry_run = getattr(args, "dry_run", False)
            if is_master_plan_dry_run:
                result = Result(
                    success=True,
                    message=f"DRY RUN: Master planner would parse ADR-{adr_config.number}",
                    artifacts={
                        "adr_number": adr_config.number,
                        "adr_title": adr_config.title,
                        "adr_status": adr_config.status,
                        "would_create": [
                            "Graph nodes for each phase outcome",
                            "Relationships between system components",
                            "GCP primitive mappings",
                            "Dependency graph structure",
                        ],
                        "planned_phases": list(adr_config.phase_outcomes.keys()),
                        "requirements": adr_config.requirements,
                    },
                    metadata={"command": "master-plan", "dry_run": True},
                )
            elif not MASTER_PLANNER_AVAILABLE:
                result = Result(
                    success=False,
                    message="Master planner not available - missing agent dependencies",
                    metadata={"command": "master-plan"},
                )
            else:
                master_planner = MasterPlannerAgent()
                goal = Goal(
                    description=f"Parse ADR-{adr_config.number} and create graph structure",
                    context={
                        "adr": adr_config.__dict__,
                        "adr_path": str(args.adr) if args.adr else None,
                    },
                    success_criteria=[
                        "Graph structure created",
                        "All phases mapped",
                        "Dependencies identified",
                    ],
                )

                task = AgentTask(goal=goal, assigned_agent=master_planner.name)
                result = await master_planner.execute(task)

        # Lesson Capture and Template Evolution Commands (Issue #80)
        elif args.command == "lessons":
            if not LESSON_HANDLERS_AVAILABLE:
                result = Result(
                    success=False,
                    message="Lesson capture system not available - missing dependencies",
                    metadata={"command": "lessons"},
                )
            else:
                try:
                    lesson_result = await handle_lessons_command(args)
                    result = Result(
                        success=lesson_result["success"],
                        message=lesson_result.get(
                            "message", f"Lessons {args.lessons_operation} completed"
                        ),
                        artifacts={"result": lesson_result},
                        metadata={
                            "command": "lessons",
                            "operation": args.lessons_operation,
                        },
                    )
                except LessonCLIError as e:
                    result = Result(
                        success=False,
                        message=str(e),
                        metadata={
                            "command": "lessons",
                            "operation": getattr(args, "lessons_operation", None),
                        },
                    )

        elif args.command == "templates":
            if not LESSON_HANDLERS_AVAILABLE:
                result = Result(
                    success=False,
                    message="Template evolution system not available - missing dependencies",
                    metadata={"command": "templates"},
                )
            else:
                try:
                    template_result = await handle_templates_command(args)
                    result = Result(
                        success=template_result["success"],
                        message=template_result.get(
                            "message", f"Templates {args.templates_operation} completed"
                        ),
                        artifacts={"result": template_result},
                        metadata={
                            "command": "templates",
                            "operation": args.templates_operation,
                        },
                    )
                except LessonCLIError as e:
                    result = Result(
                        success=False,
                        message=str(e),
                        metadata={
                            "command": "templates",
                            "operation": getattr(args, "templates_operation", None),
                        },
                    )

        elif args.command == "report":
            if not LESSON_HANDLERS_AVAILABLE:
                result = Result(
                    success=False,
                    message="Improvement metrics system not available - missing dependencies",
                    metadata={"command": "report"},
                )
            else:
                try:
                    report_result = await handle_report_command(args)
                    result = Result(
                        success=report_result["success"],
                        message=f"Improvement report generated: {report_result.get('report_path')}",
                        artifacts={"result": report_result},
                        metadata={
                            "command": "report",
                            "period": args.period,
                            "format": args.format,
                        },
                    )
                except LessonCLIError as e:
                    result = Result(
                        success=False,
                        message=str(e),
                        metadata={"command": "report"},
                    )

        elif args.command == "gcp":
            if not LESSON_HANDLERS_AVAILABLE:
                result = Result(
                    success=False,
                    message="GCP integration not available - missing dependencies",
                    metadata={"command": "gcp"},
                )
            else:
                try:
                    gcp_result = await handle_gcp_command(args)
                    result = Result(
                        success=gcp_result["success"],
                        message=gcp_result.get(
                            "message", f"GCP {args.gcp_operation} completed"
                        ),
                        artifacts={"result": gcp_result},
                        metadata={"command": "gcp", "operation": args.gcp_operation},
                    )
                except LessonCLIError as e:
                    result = Result(
                        success=False,
                        message=str(e),
                        metadata={
                            "command": "gcp",
                            "operation": getattr(args, "gcp_operation", None),
                        },
                    )

        # Handle results
        if result:
            if result.success:
                logger.info(f"✅ {args.command.title()} completed successfully!")

                # Display artifacts if any
                if result.artifacts:
                    logger.info(f"📦 Generated {len(result.artifacts)} artifacts:")
                    for key, value in result.artifacts.items():
                        if isinstance(value, str) and len(value) > 100:
                            logger.info(f"   • {key}: {value[:100]}...")
                        else:
                            logger.info(f"   • {key}: {value}")

                # Show warnings if any
                if result.metadata.get("constitutional_warnings"):
                    warnings = result.metadata["constitutional_warnings"]
                    logger.warning(f"⚠️ Constitutional AI warnings: {warnings}")

                return 0
            else:
                logger.error(f"❌ {args.command.title()} failed: {result.message}")
                return 1
        else:
            logger.error(f"❌ Unknown command: {args.command}")
            return 1

    except CLIError as e:
        logger.error(f"❌ CLI Error: {e}")
        return 1
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}", exc_info=True)
        return 2


def create_parser() -> argparse.ArgumentParser:
    """Create the comprehensive argument parser for the SOLVE CLI."""
    parser = argparse.ArgumentParser(
        prog="solve",
        description="SOLVE - Graph-Driven Cloud-Native Development Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SOLVE Methodology - Graph-Driven ADR-to-GCP Development Platform

Examples:
  # SOLVE Phase Execution
  solve scaffold --adr ADR-001.md --graph-id my-system
  solve outline --adr ADR-001.md --graph-id my-system
  solve logic --adr ADR-001.md --graph-id my-system
  solve verify --adr ADR-001.md --graph-id my-system
  solve enhance --adr ADR-001.md --graph-id my-system

  # Graph Operations
  solve graph init                                    # Initialize graph database
  solve graph visualize --graph-id my-system          # Visualize graph structure
  solve graph validate --node-type ADR               # Validate graph contracts
  solve graph query "MATCH (n:ADR) RETURN n LIMIT 5" # Custom Cypher query

  # Master Planning
  solve master-plan --adr ADR-001.md                 # Parse ADR to graph

  # Dry Run Mode (Test without changes)
  solve scaffold --adr ADR-001.md --dry-run

The graph database IS the system. All ADRs become graph structures deployed to GCP.
""",
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # SOLVE Phase Commands
    phase_commands = ["scaffold", "outline", "logic", "verify", "enhance"]
    for phase in phase_commands:
        phase_parser = subparsers.add_parser(
            phase,
            help=f"Execute {phase} phase of SOLVE methodology",
        )
        phase_parser.add_argument(
            "--adr",
            type=Path,
            help="ADR file to process (required for phase execution)",
        )
        phase_parser.add_argument(
            "--graph-id", help="Graph ID for existing system (optional)"
        )
        phase_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    # Graph Operations Command
    graph_parser = subparsers.add_parser("graph", help="Graph database operations")
    graph_subparsers = graph_parser.add_subparsers(
        dest="graph_operation", help="Graph operations"
    )

    # Graph init
    init_parser = graph_subparsers.add_parser("init", help="Initialize graph database")
    init_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )

    # Graph query
    query_parser = graph_subparsers.add_parser("query", help="Execute Cypher query")
    query_parser.add_argument("cypher", help="Cypher query to execute")
    query_parser.add_argument("--parameters", help="JSON parameters for query")
    query_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )

    # Graph validate
    validate_parser = graph_subparsers.add_parser(
        "validate", help="Validate graph contracts"
    )
    validate_parser.add_argument("--node-type", help="Specific node type to validate")
    validate_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )

    # Graph visualize
    visualize_parser = graph_subparsers.add_parser(
        "visualize", help="Visualize graph structure"
    )
    visualize_parser.add_argument("--graph-id", help="Focus on specific graph/system")
    visualize_parser.add_argument(
        "--format",
        choices=["ascii", "json"],
        default="ascii",
        help="Output format",
    )
    visualize_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )

    # Graph generate-terraform
    terraform_parser = graph_subparsers.add_parser(
        "generate-terraform",
        help="Generate Terraform from graph",
    )
    terraform_parser.add_argument(
        "--graph-id", required=True, help="Graph ID to generate from"
    )
    terraform_parser.add_argument(
        "--output-dir",
        type=Path,
        default="terraform",
        help="Output directory",
    )
    terraform_parser.add_argument(
        "--environments",
        nargs="+",
        default=["dev", "staging", "prod"],
        help="Environments to generate configs for",
    )
    terraform_parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate generated Terraform",
    )
    terraform_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )

    # Master Planner Command
    master_parser = subparsers.add_parser(
        "master-plan", help="Execute master planner on ADR"
    )
    master_parser.add_argument(
        "--adr", type=Path, required=True, help="ADR file to parse"
    )
    master_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )

    # Lesson Capture and Template Evolution Commands (Issue #80)
    lessons_parser = subparsers.add_parser(
        "lessons", help="Lesson capture and template evolution operations"
    )
    lessons_subparsers = lessons_parser.add_subparsers(
        dest="lessons_operation", help="Lessons operations"
    )

    # Capture lesson manually
    capture_parser = lessons_subparsers.add_parser(
        "capture", help="Capture a lesson manually"
    )
    capture_parser.add_argument("--issue", required=True, help="Issue description")
    capture_parser.add_argument(
        "--resolution", required=True, help="Resolution description"
    )
    capture_parser.add_argument(
        "--prevention", required=True, help="Prevention strategy"
    )
    capture_parser.add_argument(
        "--phase", default="general", help="SOLVE phase (default: general)"
    )
    capture_parser.add_argument("--adr", help="Related ADR number")
    capture_parser.add_argument(
        "--source",
        choices=["autofix", "deployment", "operations", "manual"],
        default="manual",
        help="Lesson source",
    )
    capture_parser.add_argument(
        "--impact",
        choices=["low", "medium", "high", "critical"],
        default="medium",
        help="Impact level",
    )

    # Search lessons
    search_parser = lessons_subparsers.add_parser("search", help="Search lessons")
    search_parser.add_argument("query", nargs="?", help="Search query")
    search_parser.add_argument("--phase", help="Filter by phase")
    search_parser.add_argument("--source", help="Filter by source")
    search_parser.add_argument("--limit", type=int, default=10, help="Limit results")
    search_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Show lesson analytics
    analytics_parser = lessons_subparsers.add_parser(
        "analytics", help="Show lesson analytics"
    )
    analytics_parser.add_argument(
        "--period",
        choices=["7_days", "30_days", "90_days"],
        default="30_days",
        help="Reporting period",
    )
    analytics_parser.add_argument(
        "--format",
        choices=["table", "json", "markdown"],
        default="table",
        help="Output format",
    )

    # Template evolution commands
    templates_parser = subparsers.add_parser(
        "templates", help="Template evolution operations"
    )
    templates_subparsers = templates_parser.add_subparsers(
        dest="templates_operation", help="Templates operations"
    )

    # List templates
    list_templates_parser = templates_subparsers.add_parser(
        "list", help="List all templates"
    )
    list_templates_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Show template details
    show_template_parser = templates_subparsers.add_parser(
        "show", help="Show template details"
    )
    show_template_parser.add_argument("template_id", help="Template ID to show")

    # Apply lessons to templates
    evolve_parser = templates_subparsers.add_parser(
        "evolve", help="Evolve templates based on lessons"
    )
    evolve_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )
    evolve_parser.add_argument(
        "--period",
        choices=["7_days", "30_days", "90_days"],
        default="30_days",
        help="Lesson period to consider",
    )
    evolve_parser.add_argument(
        "--min-priority",
        choices=["low", "medium", "high", "critical"],
        default="medium",
        help="Minimum lesson priority",
    )

    # Validate template
    validate_template_parser = templates_subparsers.add_parser(
        "validate", help="Validate template"
    )
    validate_template_parser.add_argument("template_id", help="Template ID to validate")

    # Backup template
    backup_template_parser = templates_subparsers.add_parser(
        "backup", help="Create template backup"
    )
    backup_template_parser.add_argument("template_id", help="Template ID to backup")
    backup_template_parser.add_argument(
        "--cloud", action="store_true", help="Create cloud backup"
    )

    # Rollback template
    rollback_parser = templates_subparsers.add_parser(
        "rollback", help="Rollback template to previous version"
    )
    rollback_parser.add_argument("template_id", help="Template ID to rollback")
    rollback_parser.add_argument(
        "--version", type=int, required=True, help="Target version"
    )

    # Sync templates to cloud
    sync_parser = templates_subparsers.add_parser(
        "sync", help="Sync templates to cloud storage"
    )
    sync_parser.add_argument(
        "--project-id", help="GCP project ID (required for cloud sync)"
    )
    sync_parser.add_argument("--region", default="us-central1", help="GCP region")

    # Generate improvement report
    report_parser = subparsers.add_parser(
        "report", help="Generate improvement metrics report"
    )
    report_parser.add_argument(
        "--period",
        choices=["7_days", "30_days", "60_days", "90_days"],
        default="30_days",
        help="Reporting period",
    )
    report_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format",
    )
    report_parser.add_argument("--output", type=Path, help="Output file path")

    # GCP integration commands
    gcp_parser = subparsers.add_parser("gcp", help="GCP integration operations")
    gcp_subparsers = gcp_parser.add_subparsers(
        dest="gcp_operation", help="GCP operations"
    )

    # Deploy GCP infrastructure
    deploy_gcp_parser = gcp_subparsers.add_parser(
        "deploy", help="Deploy GCP infrastructure"
    )
    deploy_gcp_parser.add_argument("--project-id", required=True, help="GCP project ID")
    deploy_gcp_parser.add_argument("--region", default="us-central1", help="GCP region")
    deploy_gcp_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )

    # Configure GCP integration
    configure_gcp_parser = gcp_subparsers.add_parser(
        "configure", help="Configure GCP integration"
    )
    configure_gcp_parser.add_argument(
        "--project-id", required=True, help="GCP project ID"
    )
    configure_gcp_parser.add_argument(
        "--region", default="us-central1", help="GCP region"
    )
    configure_gcp_parser.add_argument("--bucket", help="Cloud Storage bucket name")

    # Global options
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", action="store_true", help="Minimize output")
    parser.add_argument(
        "--version",
        action="version",
        version="SOLVE Graph-Driven Platform v0.5.1 - Issue #72 CLI Integration",
        help="Show version and exit",
    )

    return parser


def main() -> int:
    """Main entry point for the SOLVE CLI."""
    try:
        # Parse arguments
        parser = create_parser()
        args = parser.parse_args()

        # Show help if no command provided
        if not args.command:
            parser.print_help()
            return 0

        # Configure logging level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        elif args.quiet:
            logging.getLogger().setLevel(logging.WARNING)

        # Log feature status only if configuration is available
        is_dry_run = getattr(args, "dry_run", False)
        if is_dry_run:
            logger.info("🧪 DRY RUN MODE - Configuration validation bypassed")
        else:
            try:
                log_feature_status()
            except Exception as e:
                logger.warning(f"⚠️ Feature status logging failed: {e}")
                logger.info(
                    "📋 Some dependencies may be missing - continuing with available features"
                )

        # Show system banner (skip in dry-run mode to avoid hangs)
        if not is_dry_run:
            logger.info("🚀 SOLVE Graph-Driven Cloud-Native Development Platform")
            logger.info("📊 Graph Database: Neo4j integration for ADR-to-GCP workflows")
            logger.info(
                "🤖 Real Agent Execution: Phase executors with constitutional AI"
            )
            logger.info("☁️ GCP Deployment: Terraform generation from graph structures")

        # Validate ADR file if provided
        if getattr(args, "adr", None) and not is_dry_run:
            if not args.adr.exists():
                logger.error(f"❌ ADR file not found: {args.adr}")
                return 1

        # Execute the command
        return asyncio.run(execute_command(args))

    except KeyboardInterrupt:
        logger.info("🛑 Execution interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"💥 CLI error: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
