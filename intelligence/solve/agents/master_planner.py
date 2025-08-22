"""
Master Planner Agent: ADR to Graph Transformation Orchestrator

This agent is the core intelligence that parses Architecture Decision Records (ADRs)
and transforms them into executable graph structures. It bridges ADR input to
graph-driven execution in the SOLVE methodology.

Based on:
- Issue #76: Build Master Planner Agent
- docs/vision/SOLVE_UNIFIED_VISION.md
- docs/IMPLEMENTATION_ORDER.md (critical path component)
"""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from solve.agents.base_agent import RealADKAgent
from solve.models import AgentTask, Goal, Result, TaskStatus
from solve.prompts.constitutional_template import AgentRole

# Graph and GCP model imports
try:
    from graph.connection import GraphConnection
    from graph.models.adr_models import ADRNode, SystemNode
    from graph.models.gcp_models import (CloudFunction, CloudRunService,
                                         CloudStorage, CloudTasks, Firestore,
                                         GCPPrimitive, PubSubTopic)
    from graph.repositories.adr_repository import ADRRepository
    from graph.repositories.gcp_repository import GCPRepository

    GRAPH_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Graph database components not available: {e}")
    # Define minimal stubs for development
    GraphConnection = None
    ADRNode = None
    SystemNode = None
    GCPPrimitive = None
    CloudFunction = None
    CloudRunService = None
    CloudStorage = None
    CloudTasks = None
    Firestore = None
    PubSubTopic = None
    ADRRepository = None
    GCPRepository = None

    GRAPH_AVAILABLE = False

logger = logging.getLogger(__name__)


class MasterPlannerAgent(RealADKAgent):
    """
    Master Planner Agent: Transforms ADRs into executable graph structures.

    This is the cornerstone of graph-driven orchestration, implementing the critical
    path component that enables all subsequent parallel agent execution.
    """

    def __init__(
        self,
        working_directory: Optional[Path] = None,
        graph_connection: Optional[GraphConnection] = None,
    ):
        """Initialize Master Planner Agent with graph database integration."""

        super().__init__(
            name="master_planner",
            role=AgentRole.STRUCTURE,  # Primary role for architectural planning
            description=(
                "Transforms ADRs into executable graph structures for parallel agent execution"
            ),
            capabilities=[
                "Parse Architecture Decision Records (ADRs)",
                "Decompose requirements into GCP primitives",
                "Create Neo4j graph structures",
                "Assign archetype templates to nodes",
                "Define relationships and contracts",
                "Validate graph completeness",
                "Trigger parallel agent execution",
                "Handle ambiguous requirements gracefully",
            ],
            working_directory=working_directory,
        )

        # Constitutional AI principles specific to Master Planner
        self.constitutional_principles = [
            "Decompose into smallest viable GCP primitives",
            "Ensure complete contract definition between services",
            "Validate all dependencies are satisfied",
            "Optimize for parallel execution",
            "Preserve system integrity and security",
            "Follow cloud-native architecture patterns",
        ]

        # Initialize graph database connection
        self.graph_connection = (
            graph_connection or self._create_default_graph_connection()
        )
        self.adr_repository = None
        self.gcp_repository = None

        # Initialize repositories if graph connection is available
        if self.graph_connection:
            try:
                self.adr_repository = ADRRepository(self.graph_connection)
                self.gcp_repository = GCPRepository(self.graph_connection)
                logger.info("✅ Master Planner connected to graph database")
            except Exception as e:
                logger.warning(f"⚠️ Graph repositories not available: {e}")

        # GCP primitive type mapping for decomposition
        if GRAPH_AVAILABLE:
            self.primitive_type_mapping = {
                "cloud_run": CloudRunService,
                "cloud_function": CloudFunction,
                "pubsub_topic": PubSubTopic,
                "firestore": Firestore,
                "cloud_tasks": CloudTasks,
                "cloud_storage": CloudStorage,
            }
        else:
            # Create mock mapping when graph models are not available
            self.primitive_type_mapping = {
                "cloud_run": dict,
                "cloud_function": dict,
                "pubsub_topic": dict,
                "firestore": dict,
                "cloud_tasks": dict,
                "cloud_storage": dict,
            }

        # Archetype registry
        self.archetype_registry = {
            "cloud_run": "templates/archetypes/cloud-run",
            "cloud_function": "templates/archetypes/cloud-function",
            "pubsub_topic": "templates/archetypes/pubsub-topic",
            "firestore": "templates/archetypes/firestore",
            "cloud_tasks": "templates/archetypes/cloud-tasks",
            "cloud_storage": "templates/archetypes/cloud-storage",
        }

        logger.info(
            "🧠 Master Planner Agent initialized with graph-driven orchestration"
        )

    def _create_default_graph_connection(self) -> Optional[GraphConnection]:
        """Create default graph database connection."""
        if GraphConnection is None:
            logger.warning(
                "GraphConnection not available, running without graph database"
            )
            return None

        try:
            connection = GraphConnection.from_env()
            connection.connect()
            return connection
        except Exception as e:
            logger.warning(f"Failed to create graph connection: {e}")
            return None

    async def parse_adr(self, adr_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Parse ADR document to extract structured requirements.

        Args:
            adr_path: Path to ADR markdown file

        Returns:
            Tuple of (ADRNode, SystemNode) with extracted data
        """
        logger.info(f"📖 Parsing ADR: {adr_path}")

        try:
            # Read ADR content
            if not adr_path.exists():
                raise FileNotFoundError(f"ADR file not found: {adr_path}")

            adr_content = adr_path.read_text(encoding="utf-8")

            # Use ADK to extract structured information
            extraction_prompt = self._build_adr_extraction_prompt(adr_content)

            # Execute via ADK for intelligent parsing
            user_id = f"adr_parser_{uuid.uuid4().hex[:8]}"
            session = await self.runner.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
            )

            from google.genai import types

            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=extraction_prompt)],
            )

            events = []
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content,
            ):
                events.append(event)

            # Extract structured data from ADK response
            adr_data, system_data = await self._process_adr_extraction_events(
                events, adr_path
            )

            # Create ADRNode and SystemNode (or dicts if models not available)
            if GRAPH_AVAILABLE and ADRNode and SystemNode:
                adr_node = ADRNode(**adr_data)
                system_node = SystemNode(**system_data)
            else:
                adr_node = adr_data
                system_node = system_data

            # Extract titles for logging (handle both objects and dicts)
            adr_title = getattr(adr_node, "title", adr_node.get("title", "Unknown"))
            system_name = getattr(
                system_node, "name", system_node.get("name", "Unknown")
            )
            logger.info(f"✅ Parsed ADR '{adr_title}' -> System '{system_name}'")
            return adr_node, system_node

        except Exception as e:
            logger.error(f"❌ Failed to parse ADR {adr_path}: {e}")
            raise RuntimeError(f"ADR parsing failed: {e}") from e

    def _build_adr_extraction_prompt(self, adr_content: str) -> str:
        """Build prompt for ADR extraction using Constitutional AI."""
        return f"""<adr_extraction>
<instruction>
You are the Master Planner Agent in the SOLVE methodology. Your role is to parse
Architecture Decision Records (ADRs) and extract structured requirements for
graph-driven orchestration.

Parse the following ADR and extract:
1. ADR metadata (title, status, date, context, decision, consequences)
2. System requirements (name, description, GCP project, region)
3. Technical requirements for GCP primitive decomposition

Follow Constitutional AI principles:
- Extract complete and accurate information
- Identify all technical requirements
- Preserve the original intent and context
- Structure data for graph database storage
</instruction>

<adr_content>
{adr_content}
</adr_content>

<output_format>
Respond with a JSON object containing two sections:
{{
  "adr": {{
    "id": "unique_adr_identifier",
    "title": "ADR title",
    "status": "proposed|accepted|deprecated",
    "date": "2025-01-01T00:00:00Z",
    "context": "extracted context and problem statement",
    "decision": "extracted decision made",
    "consequences": "extracted expected consequences",
    "tags": ["tag1", "tag2"]
  }},
  "system": {{
    "name": "system_name",
    "description": "system description",
    "gcp_project": "target_gcp_project_id",
    "region": "us-central1",
    "service_level_objectives": {{}},
    "cost_budget": null,
    "compliance_requirements": []
  }}
}}
</output_format>
</adr_extraction>"""

    async def _process_adr_extraction_events(
        self,
        events: list[Any],
        adr_path: Path,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Process ADK events to extract ADR and system data."""
        try:
            # Extract response text from events
            response_text = ""
            for event in events:
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts") and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_text += part.text.strip()

            if not response_text:
                raise ValueError("No response received from ADK")

            # Parse JSON response
            try:
                # Extract JSON from response (may have additional text)
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    parsed_data = json.loads(json_match.group())
                else:
                    # Fallback: try to parse entire response
                    parsed_data = json.loads(response_text)

            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse JSON response, using fallback extraction: {e}"
                )
                # Fallback to rule-based extraction
                return self._fallback_adr_extraction(response_text, adr_path)

            # Validate and clean extracted data
            adr_data = parsed_data.get("adr", {})
            system_data = parsed_data.get("system", {})

            # Ensure required fields with defaults
            adr_data.setdefault("id", f"adr_{uuid.uuid4().hex[:8]}")
            adr_data.setdefault("title", adr_path.stem)
            adr_data.setdefault("status", "proposed")
            adr_data.setdefault("date", datetime.utcnow().isoformat())
            adr_data.setdefault("context", "Context not specified")
            adr_data.setdefault("decision", "Decision not specified")
            adr_data.setdefault("consequences", "Consequences not specified")
            adr_data.setdefault("tags", [])

            system_data.setdefault("name", adr_data["title"].lower().replace(" ", "_"))
            system_data.setdefault("description", f"System for {adr_data['title']}")
            system_data.setdefault("gcp_project", "solve-default-project")
            system_data.setdefault("region", "us-central1")
            system_data.setdefault("service_level_objectives", {})
            system_data.setdefault("cost_budget", None)
            system_data.setdefault("compliance_requirements", [])

            return adr_data, system_data

        except Exception as e:
            logger.error(f"Failed to process ADR extraction events: {e}")
            # Return minimal valid data as fallback
            return self._fallback_adr_extraction("", adr_path)

    def _fallback_adr_extraction(
        self,
        response_text: str,
        adr_path: Path,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fallback ADR extraction using simple text processing."""
        logger.info("Using fallback ADR extraction")

        # Read ADR file for basic extraction
        try:
            adr_content = adr_path.read_text(encoding="utf-8")
        except Exception:
            adr_content = ""

        # Extract title from filename or first heading
        title_match = re.search(r"^#\s+(.+)$", adr_content, re.MULTILINE)
        title = title_match.group(1) if title_match else adr_path.stem

        # Basic data extraction
        adr_data = {
            "id": f"adr_{uuid.uuid4().hex[:8]}",
            "title": title,
            "status": "proposed",
            "date": datetime.utcnow().isoformat(),
            "context": "Context extracted from ADR file",
            "decision": "Decision extracted from ADR file",
            "consequences": "Consequences extracted from ADR file",
            "tags": ["extracted", "fallback"],
        }

        system_data = {
            "name": title.lower().replace(" ", "_"),
            "description": f"System for {title}",
            "gcp_project": "solve-default-project",
            "region": "us-central1",
            "service_level_objectives": {},
            "cost_budget": None,
            "compliance_requirements": [],
        }

        return adr_data, system_data

    async def decompose_to_primitives(
        self,
        adr_node: dict[str, Any],
        system_node: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Decompose system requirements into GCP primitives.

        Args:
            adr_node: Parsed ADR data
            system_node: System requirements

        Returns:
            List of GCP primitive instances
        """
        system_name = getattr(system_node, "name", system_node.get("name", "Unknown"))
        logger.info(f"🔧 Decomposing '{system_name}' into GCP primitives")

        try:
            # Use ADK to intelligently decompose requirements
            decomposition_prompt = self._build_decomposition_prompt(
                adr_node, system_node
            )

            user_id = f"decomposer_{uuid.uuid4().hex[:8]}"
            session = await self.runner.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
            )

            from google.genai import types

            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=decomposition_prompt)],
            )

            events = []
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content,
            ):
                events.append(event)

            # Process decomposition results
            primitives = await self._process_decomposition_events(events, system_node)

            logger.info(f"✅ Decomposed into {len(primitives)} GCP primitives")
            return primitives

        except Exception as e:
            logger.error(f"❌ Failed to decompose requirements: {e}")
            # Return minimal default primitives as fallback
            return self._create_default_primitives(system_node)

    def _build_decomposition_prompt(
        self,
        adr_node: dict[str, Any],
        system_node: dict[str, Any],
    ) -> str:
        """Build prompt for requirements decomposition."""
        return f"""<requirements_decomposition>
<instruction>
As the Master Planner Agent, decompose the following system requirements into
specific GCP primitives.

Constitutional AI Principles:
- Decompose into smallest viable GCP primitives
- Ensure complete contract definition between services
- Optimize for parallel execution
- Follow cloud-native architecture patterns

Available GCP Primitive Types:
- cloud_run: User-facing APIs and web services
- cloud_function: Background processing and event handlers
- pubsub_topic: Asynchronous communication and events
- firestore: Document database and data persistence
- cloud_tasks: Task queues and workflow orchestration
- cloud_storage: File storage and static assets
</instruction>

<adr_context>
Title: {adr_node.get("title", "Unknown")}
Decision: {adr_node.get("decision", "Not specified")}
Context: {adr_node.get("context", "Not specified")}
Consequences: {adr_node.get("consequences", "Not specified")}
</adr_context>

<system_requirements>
Name: {system_node.get("name", "Unknown")}
Description: {system_node.get("description", "Not specified")}
GCP Project: {system_node.get("gcp_project", "default-project")}
Region: {system_node.get("region", "us-central1")}
</system_requirements>

<output_format>
Respond with a JSON array of GCP primitives:
[
  {{
    "id": "unique_primitive_id",
    "name": "primitive_name",
    "type": "cloud_run|cloud_function|pubsub_topic|firestore|cloud_tasks|cloud_storage",
    "archetype_path": "templates/archetypes/[type]",
    "config": {{
      // Type-specific configuration
    }},
    "labels": {{
      "system": "{system_node.get("name", "default")}",
      "environment": "production"
    }}
  }}
]
</output_format>
</requirements_decomposition>"""

    async def _process_decomposition_events(
        self,
        events: list[Any],
        system_node: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Process decomposition events to create GCP primitive instances."""
        try:
            # Extract response text
            response_text = ""
            for event in events:
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts") and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_text += part.text.strip()

            # Parse JSON response
            try:
                json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
                if json_match:
                    primitives_data = json.loads(json_match.group())
                else:
                    primitives_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse decomposition JSON: {e}")
                return self._create_default_primitives(system_node)

            # Create GCP primitive instances
            primitives = []
            for primitive_data in primitives_data:
                try:
                    primitive_type = primitive_data.get("type")

                    # Ensure archetype path
                    primitive_data.setdefault(
                        "archetype_path",
                        self.archetype_registry.get(
                            primitive_type,
                            f"templates/archetypes/{primitive_type}",
                        ),
                    )

                    if (
                        GRAPH_AVAILABLE
                        and primitive_type in self.primitive_type_mapping
                    ):
                        primitive_class = self.primitive_type_mapping.get(
                            primitive_type, dict
                        )
                        if primitive_class is not dict:
                            # Create actual primitive instance
                            primitive = primitive_class(**primitive_data)
                        else:
                            # Use dict as fallback
                            primitive = primitive_data
                    else:
                        # Use dict when graph models not available
                        primitive = primitive_data

                    primitives.append(primitive)

                except Exception as e:
                    logger.warning(
                        f"Failed to create primitive from {primitive_data}: {e}"
                    )
                    continue

            return primitives

        except Exception as e:
            logger.error(f"Failed to process decomposition events: {e}")
            return self._create_default_primitives(system_node)

    def _create_default_primitives(self, system_node) -> list[dict[str, Any]]:
        """Create default GCP primitives as fallback."""
        logger.info("Creating default GCP primitives")

        primitives = []

        # Extract system name (handle both objects and dicts)
        system_name = getattr(
            system_node, "name", system_node.get("name", "default_system")
        )
        gcp_project = getattr(
            system_node,
            "gcp_project",
            system_node.get("gcp_project", "default-project"),
        )

        if GRAPH_AVAILABLE and CloudRunService and Firestore:
            # Default API service (Cloud Run)
            api_service = CloudRunService(
                id=f"{system_name}_api",
                name=f"{system_name}-api",
                image=f"gcr.io/{gcp_project}/{system_name}-api:latest",
                config={"port": 8080, "cpu": "1", "memory": "512Mi"},
                labels={"system": system_name, "environment": "production"},
            )
            primitives.append(api_service)

            # Default database (Firestore)
            database = Firestore(
                id=f"{system_name}_db",
                name=f"{system_name}-db",
                config={"collections": [{"name": "entities", "schema": {}}]},
                labels={"system": system_name, "environment": "production"},
            )
            primitives.append(database)
        else:
            # Create dict-based primitives when graph models are not available
            api_service = {
                "id": f"{system_name}_api",
                "name": f"{system_name}-api",
                "type": "cloud_run",
                "archetype_path": "templates/archetypes/cloud-run",
                "config": {"port": 8080, "cpu": "1", "memory": "512Mi"},
                "labels": {"system": system_name, "environment": "production"},
            }
            primitives.append(api_service)

            database = {
                "id": f"{system_name}_db",
                "name": f"{system_name}-db",
                "type": "firestore",
                "archetype_path": "templates/archetypes/firestore",
                "config": {"collections": [{"name": "entities", "schema": {}}]},
                "labels": {"system": system_name, "environment": "production"},
            }
            primitives.append(database)

        return primitives

    async def build_graph(
        self,
        adr_node: ADRNode,
        system_node: SystemNode,
        primitives: list[GCPPrimitive],
    ) -> dict[str, Any]:
        """
        Create Neo4j graph structure from parsed components.

        Args:
            adr_node: ADR metadata
            system_node: System definition
            primitives: List of GCP primitives

        Returns:
            Graph structure metadata
        """
        logger.info(f"🕸️ Building graph for system '{system_node.name}'")

        try:
            if not self.adr_repository or not self.gcp_repository:
                logger.warning(
                    "Graph repositories not available, skipping graph creation"
                )
                return {"status": "skipped", "reason": "graph_database_unavailable"}

            # Create ADR node in graph
            await self.adr_repository.create_adr(adr_node)

            # Create system node and link to ADR
            await self.adr_repository.create_system(system_node)
            await self.adr_repository.link_adr_to_system(adr_node.id, system_node.name)

            # Create GCP primitive nodes
            graph_metadata = {
                "adr_id": adr_node.id,
                "system_name": system_node.name,
                "primitives": [],
                "relationships": [],
            }

            for primitive in primitives:
                # Create primitive node
                await self.gcp_repository.create_primitive(primitive)

                # Link to system
                await self.gcp_repository.link_primitive_to_system(
                    primitive.id, system_node.name
                )

                graph_metadata["primitives"].append(
                    {
                        "id": primitive.id,
                        "name": primitive.name,
                        "type": primitive.type,
                    },
                )

            # Define relationships based on primitive types
            relationships = self._define_primitive_relationships(primitives)

            for relationship in relationships:
                await self.gcp_repository.create_relationship(
                    relationship["from_id"],
                    relationship["to_id"],
                    relationship["type"],
                    relationship["properties"],
                )
                graph_metadata["relationships"].append(relationship)

            logger.info(
                f"✅ Graph created with {len(primitives)} nodes and "
                f"{len(relationships)} relationships",
            )
            return graph_metadata

        except Exception as e:
            logger.error(f"❌ Failed to build graph: {e}")
            return {"status": "failed", "error": str(e)}

    def _define_primitive_relationships(
        self,
        primitives: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Define relationships between GCP primitives based on common patterns."""
        relationships = []

        # Find primitives by type (handle both objects and dicts)
        api_services = [
            p for p in primitives if getattr(p, "type", p.get("type")) == "cloud_run"
        ]
        functions = [
            p
            for p in primitives
            if getattr(p, "type", p.get("type")) == "cloud_function"
        ]
        topics = [
            p for p in primitives if getattr(p, "type", p.get("type")) == "pubsub_topic"
        ]
        databases = [
            p for p in primitives if getattr(p, "type", p.get("type")) == "firestore"
        ]

        # API -> Database relationships
        for api in api_services:
            for db in databases:
                relationships.append(
                    {
                        "from_id": getattr(api, "id", api.get("id")),
                        "to_id": getattr(db, "id", db.get("id")),
                        "type": "READS_WRITES",
                        "properties": {"protocol": "firestore", "operation": "crud"},
                    },
                )

        # API -> Pub/Sub relationships
        for api in api_services:
            for topic in topics:
                relationships.append(
                    {
                        "from_id": getattr(api, "id", api.get("id")),
                        "to_id": getattr(topic, "id", topic.get("id")),
                        "type": "PUBLISHES",
                        "properties": {"protocol": "pubsub", "message_type": "event"},
                    },
                )

        # Pub/Sub -> Function relationships
        for topic in topics:
            for function in functions:
                relationships.append(
                    {
                        "from_id": getattr(topic, "id", topic.get("id")),
                        "to_id": getattr(function, "id", function.get("id")),
                        "type": "TRIGGERS",
                        "properties": {
                            "protocol": "pubsub",
                            "trigger_type": "subscription",
                        },
                    },
                )

        # Function -> Database relationships
        for function in functions:
            for db in databases:
                relationships.append(
                    {
                        "from_id": getattr(function, "id", function.get("id")),
                        "to_id": getattr(db, "id", db.get("id")),
                        "type": "WRITES",
                        "properties": {"protocol": "firestore", "operation": "write"},
                    },
                )

        return relationships

    async def validate_graph(self, graph_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Validate graph completeness and integrity.

        Args:
            graph_metadata: Graph structure information

        Returns:
            Validation result with issues and recommendations
        """
        logger.info("🔍 Validating graph completeness")

        validation_result = {
            "valid": True,
            "issues": [],
            "recommendations": [],
            "metrics": {
                "total_nodes": len(graph_metadata.get("primitives", [])),
                "total_relationships": len(graph_metadata.get("relationships", [])),
                "orphaned_nodes": 0,
                "coverage_score": 0.0,
            },
        }

        try:
            primitives = graph_metadata.get("primitives", [])
            relationships = graph_metadata.get("relationships", [])

            # Check for orphaned nodes (nodes with no relationships)
            connected_nodes = set()
            for rel in relationships:
                connected_nodes.add(rel["from_id"])
                connected_nodes.add(rel["to_id"])

            orphaned_nodes = []
            for primitive in primitives:
                if primitive["id"] not in connected_nodes:
                    orphaned_nodes.append(primitive["id"])
                    validation_result["issues"].append(
                        f"Orphaned node: {primitive['name']} ({primitive['type']})",
                    )

            validation_result["metrics"]["orphaned_nodes"] = len(orphaned_nodes)

            # Calculate coverage score
            if primitives:
                connected_ratio = len(connected_nodes) / len(primitives)
                validation_result["metrics"]["coverage_score"] = connected_ratio

            # Check for missing API entry points
            api_services = [p for p in primitives if p["type"] == "cloud_run"]
            if not api_services:
                validation_result["issues"].append(
                    "No API entry points (Cloud Run services) found"
                )
                validation_result["recommendations"].append(
                    "Add at least one Cloud Run service for external access",
                )

            # Check for missing data persistence
            databases = [p for p in primitives if p["type"] == "firestore"]
            storage = [p for p in primitives if p["type"] == "cloud_storage"]
            if not databases and not storage:
                validation_result["issues"].append("No data persistence layer found")
                validation_result["recommendations"].append(
                    "Add Firestore or Cloud Storage for data persistence",
                )

            # Mark as invalid if critical issues found
            if len(validation_result["issues"]) > 0:
                validation_result["valid"] = False

            logger.info(
                f"📊 Validation complete: {len(validation_result['issues'])} issues found"
            )
            return validation_result

        except Exception as e:
            logger.error(f"❌ Graph validation failed: {e}")
            return {
                "valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "recommendations": ["Review graph structure and retry validation"],
                "metrics": {"error": str(e)},
            }

    async def assign_agents(self, graph_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Assign specialized agents to each graph node for parallel execution.

        Args:
            graph_metadata: Graph structure information

        Returns:
            Agent assignment mapping
        """
        logger.info("🎯 Assigning agents to graph nodes")

        try:
            primitives = graph_metadata.get("primitives", [])

            agent_assignments = {
                "assignments": [],
                "execution_plan": {
                    "parallel_batches": [],
                    "dependencies": [],
                },
                "estimated_duration": "15-30 minutes",
            }

            # Agent type mapping based on primitive types
            agent_type_mapping = {
                "cloud_run": "ScaffoldAgent",  # Structure creation
                "cloud_function": "LogicAgent",  # Implementation
                "pubsub_topic": "InterfaceAgent",  # Contract definition
                "firestore": "StructureAgent",  # Schema design
                "cloud_tasks": "LogicAgent",  # Queue implementation
                "cloud_storage": "StructureAgent",  # Storage setup
            }

            # Create agent assignments
            for primitive in primitives:
                agent_type = agent_type_mapping.get(primitive["type"], "GeneralAgent")

                assignment = {
                    "node_id": primitive["id"],
                    "node_name": primitive["name"],
                    "node_type": primitive["type"],
                    "assigned_agent": agent_type,
                    "task_description": (
                        f"Implement {primitive['type']} primitive: {primitive['name']}"
                    ),
                    "archetype_path": f"templates/archetypes/{primitive['type']}",
                    "estimated_duration": "5-10 minutes",
                }

                agent_assignments["assignments"].append(assignment)

            # Create execution plan with parallel batches
            # Group by dependencies (independent nodes can run in parallel)
            relationships = graph_metadata.get("relationships", [])
            dependency_graph = self._build_dependency_graph(primitives, relationships)

            parallel_batches = self._create_execution_batches(dependency_graph)
            agent_assignments["execution_plan"]["parallel_batches"] = parallel_batches

            logger.info(
                f"✅ Assigned {len(agent_assignments['assignments'])} agents in "
                f"{len(parallel_batches)} batches",
            )
            return agent_assignments

        except Exception as e:
            logger.error(f"❌ Agent assignment failed: {e}")
            return {
                "assignments": [],
                "execution_plan": {"parallel_batches": [], "dependencies": []},
                "error": str(e),
            }

    def _build_dependency_graph(
        self,
        primitives: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Build dependency graph for execution ordering."""
        dependencies = {}

        # Initialize all nodes
        for primitive in primitives:
            dependencies[primitive["id"]] = []

        # Add dependencies based on relationships
        for relationship in relationships:
            from_id = relationship["from_id"]
            to_id = relationship["to_id"]

            # 'from' depends on 'to' being available
            if from_id in dependencies:
                dependencies[from_id].append(to_id)

        return dependencies

    def _create_execution_batches(
        self, dependency_graph: dict[str, list[str]]
    ) -> list[list[str]]:
        """Create parallel execution batches respecting dependencies."""
        batches = []
        remaining_nodes = set(dependency_graph.keys())

        while remaining_nodes:
            # Find nodes with no remaining dependencies
            ready_nodes = []
            for node in remaining_nodes:
                deps = dependency_graph[node]
                if all(dep not in remaining_nodes for dep in deps):
                    ready_nodes.append(node)

            if not ready_nodes:
                # Break circular dependencies by taking first remaining node
                ready_nodes = [list(remaining_nodes)[0]]

            batches.append(ready_nodes)
            remaining_nodes -= set(ready_nodes)

        return batches

    async def execute(self, task: AgentTask) -> Result:
        """
        Execute Master Planner task: Transform ADR to executable graph.

        This is the main entry point for the Master Planner Agent.
        """
        logger.info(f"🚀 Master Planner executing: {task.goal.description}")

        try:
            # Extract ADR path from task
            adr_path_str = (
                task.goal.context.get("adr_path") if task.goal.context else None
            )
            if not adr_path_str:
                raise ValueError("ADR path not provided in task context")

            adr_path = Path(adr_path_str)

            # Step 1: Parse ADR
            adr_node, system_node = await self.parse_adr(adr_path)

            # Step 2: Decompose to primitives
            primitives = await self.decompose_to_primitives(adr_node, system_node)

            # Step 3: Build graph
            graph_metadata = await self.build_graph(adr_node, system_node, primitives)

            # Step 4: Validate graph
            validation_result = await self.validate_graph(graph_metadata)

            # Step 5: Assign agents
            agent_assignments = await self.assign_agents(graph_metadata)

            # Compile results
            artifacts = {
                "adr_node": (
                    adr_node.dict() if hasattr(adr_node, "dict") else adr_node.__dict__
                ),
                "system_node": (
                    system_node.dict()
                    if hasattr(system_node, "dict")
                    else system_node.__dict__
                ),
                "primitives": [
                    p.dict() if hasattr(p, "dict") else p.__dict__ for p in primitives
                ],
                "graph_metadata": graph_metadata,
                "validation_result": validation_result,
                "agent_assignments": agent_assignments,
            }

            success = (
                validation_result.get("valid", False)
                and len(agent_assignments.get("assignments", [])) > 0
                and graph_metadata.get("status") != "failed"
            )

            message = (
                f"Successfully transformed ADR '{adr_node.title}' into executable graph with "
                f"{len(primitives)} GCP primitives and "
                f"{len(agent_assignments.get('assignments', []))} agent assignments"
                if success
                else (
                    f"Failed to transform ADR: {validation_result.get('issues', ['Unknown error'])}"
                )
            )

            return Result(
                success=success,
                message=message,
                artifacts=artifacts,
                metadata={
                    "agent": self.name,
                    "role": self.role.value,
                    "adr_path": str(adr_path),
                    "system_name": system_node.name,
                    "primitive_count": len(primitives),
                    "validation_issues": len(validation_result.get("issues", [])),
                    "agent_assignments": len(agent_assignments.get("assignments", [])),
                },
            )

        except Exception as e:
            logger.error(f"❌ Master Planner execution failed: {e}")
            return Result(
                success=False,
                message=f"Master Planner execution failed: {str(e)}",
                artifacts={"error": str(e)},
                metadata={"agent": self.name, "role": self.role.value, "error": str(e)},
            )


# Test function for Master Planner Agent
async def test_master_planner() -> bool:
    """Test the Master Planner Agent implementation."""
    try:
        # Create test ADR content
        test_adr_content = """# ADR-001: Work Order Management System

## Status
Accepted

## Context
We need a cloud-native work order management system that can handle customer requests,
track work progress, and notify stakeholders of status changes.

## Decision
Implement a microservices architecture on Google Cloud Platform using:
- Cloud Run for API services
- Firestore for data persistence
- Pub/Sub for event-driven communication
- Cloud Functions for background processing

## Consequences
- Scalable and maintainable architecture
- Event-driven design enables loose coupling
- Cloud-native approach reduces operational overhead
"""

        # Create temporary ADR file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(test_adr_content)
            test_adr_path = Path(f.name)

        try:
            # Create Master Planner agent
            agent = MasterPlannerAgent()

            # Create test task
            goal = Goal(
                description="Transform ADR into executable graph structure",
                success_criteria=[
                    "Graph created",
                    "Primitives identified",
                    "Agents assigned",
                ],
                context={"adr_path": str(test_adr_path)},
            )

            task = AgentTask(
                goal=goal,
                assigned_agent=agent.name,
                status=TaskStatus.PENDING,
            )

            # Execute test
            result = await agent.execute(task)

            # Verify results
            success = result.success and "artifacts" in result.artifacts
            logger.info(
                f"Master Planner test {'✅ PASSED' if success else '❌ FAILED'}"
            )

            return success

        finally:
            # Cleanup
            test_adr_path.unlink(missing_ok=True)

    except Exception as e:
        logger.exception(f"Master Planner test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test
    asyncio.run(test_master_planner())
