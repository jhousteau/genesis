"""
Contract Validation Agent: Tick-and-Tie System Validation

This agent implements comprehensive contract validation across the graph database,
ensuring system integrity, consistency, and completeness. It performs "tick-and-tie"
validation that verifies all contracts are properly defined and satisfied.

Based on:
- Issue #77: Contract Validation System
- docs/vision/SOLVE_UNIFIED_VISION.md (Phase 2: Outline - Contract Definition)
- docs/architecture/graph-schema.md (Contract validation patterns)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from solve.agents.base_agent import RealADKAgent
from solve.models import AgentTask, Result
from solve.prompts.constitutional_template import AgentRole

# Graph imports
try:
    from graph.connection import GraphConnection
    from graph.models.adr_models import ADRNode, SystemNode
    from graph.models.gcp_models import (
        CloudFunction,
        CloudRunService,
        CloudStorage,
        CloudTasks,
        Firestore,
        GCPPrimitive,
        PubSubTopic,
    )
    from graph.repositories.adr_repository import ADRRepository
    from graph.repositories.gcp_repository import GCPRepository

    GRAPH_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Graph database components not available: {e}")
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


class ValidationSeverity(Enum):
    """Validation issue severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Individual validation issue."""

    severity: ValidationSeverity
    category: str
    message: str
    node_id: Optional[str] = None
    relationship_id: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)
    fix_suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation result for a system or component."""

    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    validated_nodes: int = 0
    validated_relationships: int = 0
    validation_time: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_issues(self) -> list[ValidationIssue]:
        """Get critical issues that must be fixed."""
        return [i for i in self.issues if i.severity == ValidationSeverity.CRITICAL]

    @property
    def error_issues(self) -> list[ValidationIssue]:
        """Get error issues that should be fixed."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def has_blocking_issues(self) -> bool:
        """Check if there are issues that block deployment."""
        return len(self.critical_issues) > 0 or len(self.error_issues) > 0


class ContractValidationAgent(RealADKAgent):
    """
    Contract Validation Agent: Ensures system integrity through comprehensive validation.

    This agent performs "tick-and-tie" validation across the entire graph database,
    validating contracts, dependencies, SLAs, and system consistency.
    """

    def __init__(
        self,
        working_directory: Optional[Path] = None,
        graph_connection: Optional[GraphConnection] = None,
    ):
        """Initialize Contract Validation Agent."""

        super().__init__(
            name="contract_validation",
            role=AgentRole.VALIDATION,  # Validation role for contract validation tasks
            description="Performs comprehensive contract validation across graph database",
            capabilities=[
                "Tick-and-tie contract validation",
                "ADR-System-GCP relationship validation",
                "Dependency graph cycle detection",
                "SLA requirement validation",
                "Communication contract verification",
                "Archetype template consistency checks",
                "System completeness validation",
                "Critical path dependency analysis",
            ],
            working_directory=working_directory,
        )

        # Constitutional AI principles for validation
        self.constitutional_principles = [
            "Ensure all contracts are completely specified",
            "Validate dependencies are satisfied and non-circular",
            "Verify SLA requirements are realistic and measurable",
            "Check communication protocols are consistent",
            "Ensure archetype templates match node specifications",
            "Validate security and compliance requirements",
            "Preserve system integrity through rigorous validation",
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
                logger.info("✅ Contract Validation Agent connected to graph database")
            except Exception as e:
                logger.warning(f"⚠️ Graph repositories not available: {e}")

        # Validation rule registry
        self.validation_rules = self._initialize_validation_rules()

        logger.info(
            "🔍 Contract Validation Agent initialized for tick-and-tie validation"
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

    def _initialize_validation_rules(self) -> dict[str, list[dict[str, Any]]]:
        """Initialize comprehensive validation rules."""
        return {
            "adr_validation": [
                {
                    "name": "adr_required_properties",
                    "description": "ADR nodes must have all required properties",
                    "severity": ValidationSeverity.CRITICAL,
                    "query": """
                    MATCH (adr:ADR)
                    WHERE adr.id IS NULL OR adr.title IS NULL
                          OR adr.status IS NULL OR adr.decision IS NULL
                          OR adr.context IS NULL OR adr.consequences IS NULL
                    RETURN adr.id as node_id,
                           'Missing required ADR properties' as issue,
                           {
                               has_id: adr.id IS NOT NULL,
                               has_title: adr.title IS NOT NULL,
                               has_status: adr.status IS NOT NULL,
                               has_decision: adr.decision IS NOT NULL,
                               has_context: adr.context IS NOT NULL,
                               has_consequences: adr.consequences IS NOT NULL
                           } as details
                    """,
                },
                {
                    "name": "adr_valid_status",
                    "description": "ADR status must be valid",
                    "severity": ValidationSeverity.ERROR,
                    "query": """
                    MATCH (adr:ADR)
                    WHERE NOT adr.status IN ['proposed', 'accepted', 'deprecated']
                    RETURN adr.id as node_id,
                           'Invalid ADR status' as issue,
                           {status: adr.status} as details
                    """,
                },
                {
                    "name": "adr_defines_system",
                    "description": "All ADRs must define at least one system",
                    "severity": ValidationSeverity.WARNING,
                    "query": """
                    MATCH (adr:ADR)
                    WHERE NOT (adr)-[:DEFINES]->(:System)
                    RETURN adr.id as node_id,
                           'ADR does not define any system' as issue,
                           {title: adr.title} as details
                    """,
                },
            ],
            "system_validation": [
                {
                    "name": "system_required_properties",
                    "description": "System nodes must have all required properties",
                    "severity": ValidationSeverity.CRITICAL,
                    "query": """
                    MATCH (sys:System)
                    WHERE sys.name IS NULL OR sys.description IS NULL
                          OR sys.gcp_project IS NULL OR sys.region IS NULL
                    RETURN sys.name as node_id,
                           'Missing required system properties' as issue,
                           {
                               has_name: sys.name IS NOT NULL,
                               has_description: sys.description IS NOT NULL,
                               has_gcp_project: sys.gcp_project IS NOT NULL,
                               has_region: sys.region IS NOT NULL
                           } as details
                    """,
                },
                {
                    "name": "system_contains_primitives",
                    "description": "Systems must contain at least one GCP primitive",
                    "severity": ValidationSeverity.ERROR,
                    "query": """
                    MATCH (sys:System)
                    WHERE NOT (sys)-[:CONTAINS]->(:GCPPrimitive)
                    RETURN sys.name as node_id,
                           'System contains no GCP primitives' as issue,
                           {description: sys.description} as details
                    """,
                },
                {
                    "name": "system_valid_gcp_project",
                    "description": "GCP project IDs must follow naming conventions",
                    "severity": ValidationSeverity.WARNING,
                    "query": """
                    MATCH (sys:System)
                    WHERE NOT sys.gcp_project =~ '^[a-z][a-z0-9-]{4,28}[a-z0-9]$'
                    RETURN sys.name as node_id,
                           'Invalid GCP project ID format' as issue,
                           {gcp_project: sys.gcp_project} as details
                    """,
                },
            ],
            "primitive_validation": [
                {
                    "name": "primitive_required_properties",
                    "description": "GCP primitives must have all required base properties",
                    "severity": ValidationSeverity.CRITICAL,
                    "query": """
                    MATCH (prim:GCPPrimitive)
                    WHERE prim.id IS NULL OR prim.name IS NULL
                          OR prim.type IS NULL OR prim.archetype_path IS NULL
                    RETURN prim.id as node_id,
                           'Missing required primitive properties' as issue,
                           {
                               has_id: prim.id IS NOT NULL,
                               has_name: prim.name IS NOT NULL,
                               has_type: prim.type IS NOT NULL,
                               has_archetype_path: prim.archetype_path IS NOT NULL
                           } as details
                    """,
                },
                {
                    "name": "cloud_run_specific_validation",
                    "description": "Cloud Run services must have valid configuration",
                    "severity": ValidationSeverity.ERROR,
                    "query": """
                    MATCH (cr:CloudRun)
                    WHERE cr.image IS NULL OR cr.cpu IS NULL OR cr.memory IS NULL
                          OR NOT cr.cpu IN ['1', '2', '4', '8']
                          OR NOT cr.memory =~ '^(128Mi|256Mi|512Mi|1Gi|2Gi|4Gi|8Gi|16Gi)$'
                    RETURN cr.id as node_id,
                           'Invalid Cloud Run configuration' as issue,
                           {
                               image: cr.image,
                               cpu: cr.cpu,
                               memory: cr.memory
                           } as details
                    """,
                },
                {
                    "name": "cloud_function_specific_validation",
                    "description": "Cloud Functions must have valid runtime and entrypoint",
                    "severity": ValidationSeverity.ERROR,
                    "query": """
                    MATCH (cf:CloudFunction)
                    WHERE cf.runtime IS NULL OR cf.entrypoint IS NULL
                          OR NOT cf.runtime =~ \
                          '^(python3(11|12)|nodejs(18|20)|go1(19|20)|java(11|17))$'
                    RETURN cf.id as node_id,
                           'Invalid Cloud Function configuration' as issue,
                           {
                               runtime: cf.runtime,
                               entrypoint: cf.entrypoint
                           } as details
                    """,
                },
            ],
            "dependency_validation": [
                {
                    "name": "no_circular_dependencies",
                    "description": "Dependency graph must not contain cycles",
                    "severity": ValidationSeverity.CRITICAL,
                    "query": """
                    MATCH path = (start:GCPPrimitive)-[:DEPENDS_ON*1..10]->(start)
                    RETURN start.id as node_id,
                           'Circular dependency detected' as issue,
                           {
                               path_length: length(path),
                               cycle_nodes: [n in nodes(path) | n.id]
                           } as details
                    """,
                },
                {
                    "name": "critical_dependencies_satisfied",
                    "description": "All critical dependencies must be satisfied",
                    "severity": ValidationSeverity.CRITICAL,
                    "query": """
                    MATCH (source:GCPPrimitive)-[dep:DEPENDS_ON {criticality: 'critical'}]->
                          (target:GCPPrimitive)
                    WHERE NOT EXISTS {
                        MATCH (target) WHERE target.id IS NOT NULL
                    }
                    RETURN source.id as node_id,
                           'Critical dependency target not found' as issue,
                           {
                               dependency_type: dep.dependency_type,
                               target_id: target.id
                           } as details
                    """,
                },
                {
                    "name": "dependency_properties_complete",
                    "description": "Dependencies must have required properties",
                    "severity": ValidationSeverity.ERROR,
                    "query": """
                    MATCH (source:GCPPrimitive)-[dep:DEPENDS_ON]->(target:GCPPrimitive)
                    WHERE dep.dependency_type IS NULL OR dep.criticality IS NULL
                          OR NOT dep.dependency_type IN ['runtime', 'build', 'data']
                          OR NOT dep.criticality IN ['optional', 'required', 'critical']
                    RETURN source.id as node_id,
                           'Incomplete dependency properties' as issue,
                           {
                               dependency_type: dep.dependency_type,
                               criticality: dep.criticality,
                               target_id: target.id
                           } as details
                    """,
                },
            ],
            "communication_validation": [
                {
                    "name": "communication_contracts_complete",
                    "description": "Communication relationships must have complete contracts",
                    "severity": ValidationSeverity.ERROR,
                    "query": """
                    MATCH (source:GCPPrimitive)-[comm:COMMUNICATES_WITH]->(target:GCPPrimitive)
                    WHERE comm.protocol IS NULL OR comm.endpoint IS NULL
                          OR comm.data_format IS NULL
                          OR NOT comm.protocol IN ['http', 'https', 'grpc', 'pubsub', 'storage']
                          OR NOT comm.data_format IN ['json', 'protobuf', 'binary', 'xml']
                    RETURN source.id as node_id,
                           'Incomplete communication contract' as issue,
                           {
                               protocol: comm.protocol,
                               endpoint: comm.endpoint,
                               data_format: comm.data_format,
                               target_id: target.id
                           } as details
                    """,
                },
                {
                    "name": "sla_requirements_valid",
                    "description": "SLA requirements must be realistic and measurable",
                    "severity": ValidationSeverity.WARNING,
                    "query": """
                    MATCH (source:GCPPrimitive)-[comm:COMMUNICATES_WITH]->(target:GCPPrimitive)
                    WHERE comm.sla_requirements IS NOT NULL
                          AND (
                              comm.sla_requirements.latency_ms IS NULL
                              OR comm.sla_requirements.throughput_rps IS NULL
                              OR comm.sla_requirements.latency_ms < 1
                              OR comm.sla_requirements.latency_ms > 30000
                              OR comm.sla_requirements.throughput_rps < 1
                              OR comm.sla_requirements.throughput_rps > 1000000
                          )
                    RETURN source.id as node_id,
                           'Invalid SLA requirements' as issue,
                           {
                               sla_requirements: comm.sla_requirements,
                               target_id: target.id
                           } as details
                    """,
                },
            ],
            "archetype_validation": [
                {
                    "name": "archetype_paths_exist",
                    "description": "Archetype paths must point to existing templates",
                    "severity": ValidationSeverity.ERROR,
                    "query": """
                    MATCH (prim:GCPPrimitive)
                    WHERE prim.archetype_path IS NOT NULL
                    RETURN prim.id as node_id,
                           'Archetype path validation needed' as issue,
                           {archetype_path: prim.archetype_path} as details
                    """,
                },
            ],
        }

    async def validate_system(self, system_name: str) -> ValidationResult:
        """
        Perform comprehensive validation of a complete system.

        Args:
            system_name: Name of the system to validate

        Returns:
            ValidationResult with all validation findings
        """
        logger.info(f"🔍 Starting comprehensive validation for system: {system_name}")

        validation_start = datetime.utcnow()
        all_issues = []
        validated_nodes = 0
        validated_relationships = 0

        try:
            if not self.graph_connection:
                raise RuntimeError("Graph connection not available for validation")

            with self.graph_connection.session() as session:
                # Validate that system exists
                system_check = session.run(
                    "MATCH (sys:System {name: $name}) RETURN sys",
                    name=system_name,
                )
                if not system_check.single():
                    return ValidationResult(
                        passed=False,
                        issues=[
                            ValidationIssue(
                                severity=ValidationSeverity.CRITICAL,
                                category="system_existence",
                                message=f"System '{system_name}' not found in graph database",
                            ),
                        ],
                        validation_time=datetime.utcnow(),
                        metadata={"system_name": system_name},
                    )

                # Run all validation rule categories
                for category, rules in self.validation_rules.items():
                    logger.info(f"📋 Running {category} validation rules")

                    for rule in rules:
                        try:
                            # Modify query to focus on the specific system
                            system_scoped_query = self._scope_query_to_system(
                                rule["query"],
                                system_name,
                            )

                            result = session.run(system_scoped_query)
                            violations = list(result)

                            for violation in violations:
                                issue = ValidationIssue(
                                    severity=rule["severity"],
                                    category=category,
                                    message=violation.get("issue", rule["description"]),
                                    node_id=violation.get("node_id"),
                                    relationship_id=violation.get("relationship_id"),
                                    details=violation.get("details", {}),
                                    fix_suggestion=rule.get("fix_suggestion"),
                                )
                                all_issues.append(issue)

                        except Exception as e:
                            logger.error(
                                f"❌ Validation rule {rule['name']} failed: {e}"
                            )
                            all_issues.append(
                                ValidationIssue(
                                    severity=ValidationSeverity.ERROR,
                                    category="validation_error",
                                    message=f"Validation rule execution failed: {rule['name']}",
                                    details={"error": str(e), "rule": rule["name"]},
                                ),
                            )

                # Count validated components
                node_count_result = session.run(
                    """
                    MATCH (sys:System {name: $name})-[:CONTAINS]->(prim:GCPPrimitive)
                    RETURN count(prim) as node_count
                    UNION ALL
                    MATCH (adr:ADR)-[:DEFINES]->(sys:System {name: $name})
                    RETURN count(adr) as node_count
                    UNION ALL
                    MATCH (sys:System {name: $name})
                    RETURN count(sys) as node_count
                """,
                    name=system_name,
                )

                for record in node_count_result:
                    validated_nodes += record.values()[0]

                rel_count_result = session.run(
                    """
                    MATCH (sys:System {name: $name})-[:CONTAINS]->(prim:GCPPrimitive)
                    MATCH (prim)-[rel]->()
                    RETURN count(rel) as relationship_count
                """,
                    name=system_name,
                )

                rel_record = rel_count_result.single()
                if rel_record:
                    validated_relationships = rel_record["relationship_count"]

                # Perform archetype validation
                archetype_issues = await self._validate_archetype_consistency(
                    session, system_name
                )
                all_issues.extend(archetype_issues)

        except Exception as e:
            logger.error(f"❌ System validation failed for {system_name}: {e}")
            all_issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="validation_failure",
                    message=f"System validation failed: {str(e)}",
                    details={"error": str(e), "system": system_name},
                ),
            )

        # Determine overall validation result
        passed = not any(
            issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]
            for issue in all_issues
        )

        validation_result = ValidationResult(
            passed=passed,
            issues=all_issues,
            validated_nodes=validated_nodes,
            validated_relationships=validated_relationships,
            validation_time=datetime.utcnow(),
            metadata={
                "system_name": system_name,
                "validation_duration_seconds": (
                    datetime.utcnow() - validation_start
                ).total_seconds(),
                "rules_executed": sum(
                    len(rules) for rules in self.validation_rules.values()
                ),
            },
        )

        # Log validation summary
        if passed:
            logger.info(f"✅ System validation PASSED for {system_name}")
            logger.info(
                f"📊 Validated {validated_nodes} nodes, {validated_relationships} relationships",
            )
            if all_issues:
                warnings = len(
                    [i for i in all_issues if i.severity == ValidationSeverity.WARNING]
                )
                logger.info(f"⚠️ {warnings} warnings found (non-blocking)")
        else:
            critical_count = len(validation_result.critical_issues)
            error_count = len(validation_result.error_issues)
            logger.error(f"❌ System validation FAILED for {system_name}")
            logger.error(
                f"🚨 {critical_count} critical issues, {error_count} errors found"
            )

        return validation_result

    async def validate_contracts_between_nodes(
        self,
        node1_id: str,
        node2_id: str,
    ) -> ValidationResult:
        """
        Validate contracts between two specific nodes.

        Args:
            node1_id: ID of first node
            node2_id: ID of second node

        Returns:
            ValidationResult for the contract validation
        """
        logger.info(f"🔗 Validating contracts between {node1_id} and {node2_id}")

        issues = []

        try:
            if not self.graph_connection:
                raise RuntimeError("Graph connection not available for validation")

            with self.graph_connection.session() as session:
                # Check for communication contracts
                comm_result = session.run(
                    """
                    MATCH (n1 {id: $node1_id})-[comm:COMMUNICATES_WITH]->(n2 {id: $node2_id})
                    RETURN comm, n1.type as source_type, n2.type as target_type
                """,
                    node1_id=node1_id,
                    node2_id=node2_id,
                )

                for record in comm_result:
                    comm = dict(record["comm"])
                    source_type = record["source_type"]
                    target_type = record["target_type"]

                    # Validate protocol compatibility
                    if not self._is_protocol_compatible(
                        source_type,
                        target_type,
                        comm.get("protocol"),
                    ):
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                category="contract_compatibility",
                                message=(
                                    f"Protocol {comm.get('protocol')} incompatible between "
                                    f"{source_type} and {target_type}"
                                ),
                                node_id=node1_id,
                                details={
                                    "source_type": source_type,
                                    "target_type": target_type,
                                    "protocol": comm.get("protocol"),
                                    "target_node": node2_id,
                                },
                            ),
                        )

                    # Validate SLA requirements
                    sla_reqs = comm.get("sla_requirements", {})
                    if sla_reqs:
                        sla_issues = self._validate_sla_requirements(
                            sla_reqs,
                            source_type,
                            target_type,
                        )
                        issues.extend(sla_issues)

                # Check for dependency contracts
                dep_result = session.run(
                    """
                    MATCH (n1 {id: $node1_id})-[dep:DEPENDS_ON]->(n2 {id: $node2_id})
                    RETURN dep, n1.type as source_type, n2.type as target_type
                """,
                    node1_id=node1_id,
                    node2_id=node2_id,
                )

                for record in dep_result:
                    dep = dict(record["dep"])
                    source_type = record["source_type"]
                    target_type = record["target_type"]

                    # Validate dependency compatibility
                    if not self._is_dependency_valid(
                        source_type,
                        target_type,
                        dep.get("dependency_type"),
                    ):
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                category="dependency_compatibility",
                                message=(
                                    f"Invalid dependency: {source_type} cannot depend on "
                                    f"{target_type} for {dep.get('dependency_type')}"
                                ),
                                node_id=node1_id,
                                details={
                                    "source_type": source_type,
                                    "target_type": target_type,
                                    "dependency_type": dep.get("dependency_type"),
                                    "target_node": node2_id,
                                },
                            ),
                        )

        except Exception as e:
            logger.error(
                f"❌ Contract validation failed between {node1_id} and {node2_id}: {e}"
            )
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="validation_failure",
                    message=f"Contract validation failed: {str(e)}",
                    details={"error": str(e), "node1": node1_id, "node2": node2_id},
                ),
            )

        passed = not any(
            issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]
            for issue in issues
        )

        return ValidationResult(
            passed=passed,
            issues=issues,
            validated_relationships=1 if not issues else 0,
            validation_time=datetime.utcnow(),
            metadata={"node1_id": node1_id, "node2_id": node2_id},
        )

    async def validate_dependency_graph(self, system_name: str) -> ValidationResult:
        """
        Validate the complete dependency graph for a system.

        Args:
            system_name: Name of the system to validate

        Returns:
            ValidationResult for dependency graph validation
        """
        logger.info(f"🕸️ Validating dependency graph for system: {system_name}")

        issues = []

        try:
            if not self.graph_connection:
                raise RuntimeError("Graph connection not available for validation")

            with self.graph_connection.session() as session:
                # Check for circular dependencies
                cycle_result = session.run(
                    """
                    MATCH (sys:System {name: $name})-[:CONTAINS]->(start:GCPPrimitive)
                    MATCH path = (start)-[:DEPENDS_ON*1..20]->(start)
                    RETURN start.id as node_id,
                           [n in nodes(path) | n.id] as cycle_path,
                           length(path) as cycle_length
                """,
                    name=system_name,
                )

                for record in cycle_result:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.CRITICAL,
                            category="circular_dependency",
                            message=(
                                f"Circular dependency detected starting from {record['node_id']}"
                            ),
                            node_id=record["node_id"],
                            details={
                                "cycle_path": record["cycle_path"],
                                "cycle_length": record["cycle_length"],
                            },
                            fix_suggestion="Remove one of the dependencies in the cycle",
                        ),
                    )

                # Check for orphaned nodes (no incoming or outgoing dependencies)
                orphan_result = session.run(
                    """
                    MATCH (sys:System {name: $name})-[:CONTAINS]->(prim:GCPPrimitive)
                    WHERE NOT (prim)-[:DEPENDS_ON]->() AND NOT ()-[:DEPENDS_ON]->(prim)
                    RETURN prim.id as node_id, prim.type as node_type, prim.name as node_name
                """,
                    name=system_name,
                )

                for record in orphan_result:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="orphaned_node",
                            message=f"Node {record['node_id']} has no dependencies",
                            node_id=record["node_id"],
                            details={
                                "node_type": record["node_type"],
                                "node_name": record["node_name"],
                            },
                            fix_suggestion=(
                                "Consider if this node should have dependencies or "
                                "depend on other nodes"
                            ),
                        ),
                    )

                # Validate critical path can be computed
                critical_path_result = session.run(
                    """
                    MATCH (sys:System {name: $name})-[:CONTAINS]->(start:GCPPrimitive)
                    WHERE NOT ()-[:DEPENDS_ON]->(start)  // Start nodes (no incoming dependencies)
                    MATCH (sys)-[:CONTAINS]->(end:GCPPrimitive)
                    WHERE NOT (end)-[:DEPENDS_ON]->()    // End nodes (no outgoing dependencies)
                    RETURN count(start) as start_nodes, count(end) as end_nodes
                """,
                    name=system_name,
                )

                critical_record = critical_path_result.single()
                if critical_record and (
                    critical_record["start_nodes"] == 0
                    or critical_record["end_nodes"] == 0
                ):
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="critical_path",
                            message="No clear start or end nodes found for dependency graph",
                            details={
                                "start_nodes": critical_record["start_nodes"],
                                "end_nodes": critical_record["end_nodes"],
                            },
                        ),
                    )

        except Exception as e:
            logger.error(
                f"❌ Dependency graph validation failed for {system_name}: {e}"
            )
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="validation_failure",
                    message=f"Dependency graph validation failed: {str(e)}",
                    details={"error": str(e), "system": system_name},
                ),
            )

        passed = not any(
            issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]
            for issue in issues
        )

        return ValidationResult(
            passed=passed,
            issues=issues,
            validation_time=datetime.utcnow(),
            metadata={
                "system_name": system_name,
                "validation_type": "dependency_graph",
            },
        )

    def _scope_query_to_system(self, query: str, system_name: str) -> str:
        """Modify a validation query to focus on a specific system."""
        # This is a simplified implementation - in production, you'd want more
        # sophisticated query modification
        if "MATCH (adr:ADR)" in query and "DEFINES" not in query:
            return query.replace(
                "MATCH (adr:ADR)",
                f"MATCH (adr:ADR)-[:DEFINES]->(sys:System {{name: '{system_name}'}})",
            )
        elif "MATCH (sys:System)" in query and "name:" not in query:
            return query.replace(
                "MATCH (sys:System)",
                f"MATCH (sys:System {{name: '{system_name}'}})",
            )
        elif "MATCH (prim:GCPPrimitive)" in query:
            return query.replace(
                "MATCH (prim:GCPPrimitive)",
                f"MATCH (sys:System {{name: '{system_name}'}})-[:CONTAINS]->(prim:GCPPrimitive)",
            )

        return query

    async def _validate_archetype_consistency(
        self,
        session: Any,
        system_name: str,
    ) -> list[ValidationIssue]:
        """Validate that archetype templates are consistent with node specifications."""
        issues = []

        try:
            # Get all primitives with their archetype paths
            result = session.run(
                """
                MATCH (sys:System {name: $name})-[:CONTAINS]->(prim:GCPPrimitive)
                RETURN prim.id as node_id, prim.type as node_type,
                       prim.archetype_path as archetype_path, prim
            """,
                name=system_name,
            )

            for record in result:
                node_id = record["node_id"]
                node_type = record["node_type"]
                archetype_path = record["archetype_path"]

                if archetype_path:
                    # Check if archetype directory exists
                    archetype_dir = Path(archetype_path)
                    if not archetype_dir.exists():
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                category="archetype_validation",
                                message=f"Archetype path does not exist: {archetype_path}",
                                node_id=node_id,
                                details={
                                    "archetype_path": archetype_path,
                                    "node_type": node_type,
                                },
                                fix_suggestion=(
                                    f"Create archetype templates at {archetype_path} "
                                    "or update the path"
                                ),
                            ),
                        )
                    else:
                        # Validate archetype contains required files
                        required_files = self._get_required_archetype_files(node_type)
                        for required_file in required_files:
                            if not (archetype_dir / required_file).exists():
                                issues.append(
                                    ValidationIssue(
                                        severity=ValidationSeverity.WARNING,
                                        category="archetype_validation",
                                        message=f"Missing required archetype file: {required_file}",
                                        node_id=node_id,
                                        details={
                                            "archetype_path": archetype_path,
                                            "missing_file": required_file,
                                            "node_type": node_type,
                                        },
                                    ),
                                )

        except Exception as e:
            logger.error(f"Archetype validation failed: {e}")
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="archetype_validation",
                    message=f"Archetype validation failed: {str(e)}",
                    details={"error": str(e)},
                ),
            )

        return issues

    def _get_required_archetype_files(self, node_type: str) -> list[str]:
        """Get list of required files for an archetype based on node type."""
        base_files = ["main.tf", "variables.tf", "outputs.tf"]

        type_specific_files = {
            "cloud_run": ["Dockerfile", "requirements.txt"],
            "cloud_function": ["main.py", "requirements.txt"],
            "pubsub_topic": [],
            "firestore": ["security.rules"],
            "cloud_storage": ["lifecycle.json"],
            "cloud_tasks": [],
        }

        return base_files + type_specific_files.get(node_type, [])

    def _is_protocol_compatible(
        self, source_type: str, target_type: str, protocol: str
    ) -> bool:
        """Check if a protocol is compatible between two node types."""
        # Protocol compatibility matrix
        compatibility_matrix = {
            "cloud_run": {
                "cloud_run": ["http", "https", "grpc"],
                "cloud_function": ["http", "https"],
                "pubsub_topic": ["pubsub"],
                "firestore": ["http", "https"],
                "cloud_storage": ["storage"],
            },
            "cloud_function": {
                "cloud_run": ["http", "https"],
                "cloud_function": ["http", "https"],
                "pubsub_topic": ["pubsub"],
                "firestore": ["http", "https"],
                "cloud_storage": ["storage"],
            },
            "pubsub_topic": {
                "cloud_run": ["pubsub"],
                "cloud_function": ["pubsub"],
            },
            # Add more compatibility rules as needed
        }

        compatible_protocols = compatibility_matrix.get(source_type, {}).get(
            target_type, []
        )
        return protocol in compatible_protocols

    def _is_dependency_valid(
        self,
        source_type: str,
        target_type: str,
        dependency_type: str,
    ) -> bool:
        """Check if a dependency relationship is valid between two node types."""
        # Dependency validity matrix
        valid_dependencies = {
            "cloud_run": {
                "firestore": ["runtime", "data"],
                "pubsub_topic": ["runtime"],
                "cloud_storage": ["runtime", "data"],
                "cloud_function": ["runtime"],
            },
            "cloud_function": {
                "firestore": ["runtime", "data"],
                "pubsub_topic": ["runtime"],
                "cloud_storage": ["runtime", "data"],
            },
            # Add more dependency rules as needed
        }

        valid_deps = valid_dependencies.get(source_type, {}).get(target_type, [])
        return dependency_type in valid_deps

    def _validate_sla_requirements(
        self,
        sla_requirements: dict[str, Any],
        source_type: str,
        target_type: str,
    ) -> list[ValidationIssue]:
        """Validate SLA requirements for reasonableness."""
        issues = []

        # Check latency requirements
        latency_ms = sla_requirements.get("latency_ms")
        if latency_ms is not None:
            if latency_ms < 1:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="sla_validation",
                        message="Latency requirement too aggressive (< 1ms)",
                        details={
                            "latency_ms": latency_ms,
                            "source_type": source_type,
                            "target_type": target_type,
                        },
                    ),
                )
            elif latency_ms > 30000:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="sla_validation",
                        message="Latency requirement very high (> 30s)",
                        details={
                            "latency_ms": latency_ms,
                            "source_type": source_type,
                            "target_type": target_type,
                        },
                    ),
                )

        # Check throughput requirements
        throughput_rps = sla_requirements.get("throughput_rps")
        if throughput_rps is not None:
            if throughput_rps < 1:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="sla_validation",
                        message="Throughput requirement too low (< 1 RPS)",
                        details={
                            "throughput_rps": throughput_rps,
                            "source_type": source_type,
                            "target_type": target_type,
                        },
                    ),
                )
            elif throughput_rps > 100000:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="sla_validation",
                        message="Throughput requirement very high (> 100k RPS)",
                        details={
                            "throughput_rps": throughput_rps,
                            "source_type": source_type,
                            "target_type": target_type,
                        },
                    ),
                )

        return issues

    def format_validation_report(self, result: ValidationResult) -> str:
        """Format validation result into a human-readable report."""
        report = []

        # Header
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        report.append(f"Contract Validation Report - {status}")
        report.append("=" * 60)

        # Summary
        report.append(
            f"Validated Components: {result.validated_nodes} nodes, "
            f"{result.validated_relationships} relationships",
        )
        report.append(f"Validation Time: {result.validation_time}")
        report.append("")

        # Issues summary
        if result.issues:
            critical_count = len(result.critical_issues)
            error_count = len(result.error_issues)
            warning_count = len(
                [i for i in result.issues if i.severity == ValidationSeverity.WARNING],
            )
            info_count = len(
                [i for i in result.issues if i.severity == ValidationSeverity.INFO]
            )

            report.append(f"Issues Found: {len(result.issues)} total")
            report.append(f"  🚨 Critical: {critical_count}")
            report.append(f"  ❌ Errors: {error_count}")
            report.append(f"  ⚠️  Warnings: {warning_count}")
            report.append(f"  ℹ️  Info: {info_count}")
            report.append("")

            # Group issues by category
            issues_by_category = {}
            for issue in result.issues:
                if issue.category not in issues_by_category:
                    issues_by_category[issue.category] = []
                issues_by_category[issue.category].append(issue)

            # Report issues by category
            for category, issues in issues_by_category.items():
                report.append(f"{category.replace('_', ' ').title()}:")
                for issue in issues:
                    severity_icon = {
                        ValidationSeverity.CRITICAL: "🚨",
                        ValidationSeverity.ERROR: "❌",
                        ValidationSeverity.WARNING: "⚠️",
                        ValidationSeverity.INFO: "ℹ️",
                    }[issue.severity]

                    report.append(f"  {severity_icon} {issue.message}")
                    if issue.node_id:
                        report.append(f"    Node: {issue.node_id}")
                    if issue.fix_suggestion:
                        report.append(f"    Fix: {issue.fix_suggestion}")
                report.append("")
        else:
            report.append("✅ No issues found!")
            report.append("")

        # Metadata
        if result.metadata:
            report.append("Metadata:")
            for key, value in result.metadata.items():
                report.append(f"  {key}: {value}")

        return "\n".join(report)

    async def execute(self, task: AgentTask) -> Result:
        """Execute contract validation task."""
        try:
            # Parse task parameters
            system_name = task.context.get("system_name")
            validation_type = task.context.get("validation_type", "complete")

            if not system_name:
                return Result(
                    success=False,
                    message="System name required for contract validation",
                    artifacts={},
                )

            # Perform validation based on type
            if validation_type == "complete":
                validation_result = await self.validate_system(system_name)
            elif validation_type == "dependencies":
                validation_result = await self.validate_dependency_graph(system_name)
            else:
                return Result(
                    success=False,
                    message=f"Unknown validation type: {validation_type}",
                    artifacts={},
                )

            # Generate report
            report = self.format_validation_report(validation_result)

            return Result(
                success=validation_result.passed,
                message=(
                    f"Contract validation "
                    f"{'passed' if validation_result.passed else 'failed'} "
                    f"for system {system_name}"
                ),
                artifacts={
                    "validation_result": validation_result,
                    "validation_report": report,
                    "issues_count": len(validation_result.issues),
                    "blocking_issues": validation_result.has_blocking_issues,
                },
            )

        except Exception as e:
            logger.error(f"❌ Contract validation execution failed: {e}")
            return Result(
                success=False,
                message=f"Contract validation failed: {str(e)}",
                artifacts={"error": str(e)},
            )
