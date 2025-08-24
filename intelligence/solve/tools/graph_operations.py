"""
Real Graph Operations Tool for SOLVE Agents

Implements actual graph database operations with safety mechanisms and comprehensive functionality.
Based on existing graph infrastructure and patterns from GitTool.

NO MOCKS, NO STUBS - REAL GRAPH OPERATIONS ONLY
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import structlog

try:
    from neo4j import Driver, Record, Session

    NEO4J_AVAILABLE = True
except ImportError:
    structlog.get_logger(__name__).warning(
        "Neo4j driver not available - install neo4j package"
    )
    Driver = Record = Session = None  # type: ignore[assignment]
    NEO4J_AVAILABLE = False

logger = structlog.get_logger(__name__)

# Import existing graph infrastructure
try:
    from graph.connection import GraphConnection
    from graph.models.adr_models import ADRNode, SystemNode
    from graph.models.gcp_models import CloudRunService, GCPPrimitive, PubSubTopic
    from graph.repositories.adr_repository import ADRRepository
    from graph.repositories.gcp_repository import GCPRepository

    GRAPH_MODULES_AVAILABLE = True
except ImportError:
    logger.warning("Graph modules not found. Using basic graph operations only.")
    GraphConnection = None
    ADRNode = SystemNode = CloudRunService = GCPPrimitive = PubSubTopic = None
    ADRRepository = GCPRepository = None
    GRAPH_MODULES_AVAILABLE = False


@dataclass
class GraphOperation:
    """Result of a graph operation."""

    success: bool
    operation: str
    message: str
    node_id: str = ""
    relationship_id: str = ""
    query: str = ""
    result_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""


@dataclass
class GraphNode:
    """Generic graph node representation."""

    id: str
    labels: list[str]
    properties: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GraphRelationship:
    """Graph relationship representation."""

    id: str
    type: str
    start_node_id: str
    end_node_id: str
    properties: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GraphSafetyConfig:
    """Safety configuration for graph operations."""

    max_query_complexity: int = 1000
    max_results_per_query: int = 10000
    allow_delete_operations: bool = False
    allow_schema_changes: bool = False
    transaction_timeout_seconds: int = 30
    protected_node_types: list[str] = field(
        default_factory=lambda: ["System", "Production"]
    )
    require_transaction_for_writes: bool = True
    max_batch_size: int = 1000


class GraphTool:
    """
    Real graph database operations tool with safety mechanisms.

    CRITICAL: This performs ACTUAL graph operations - no mocking.
    Provides comprehensive graph functionality for SOLVE architecture.
    """

    def __init__(
        self,
        connection: Optional[GraphConnection] = None,
        safety_config: Optional[GraphSafetyConfig] = None,
    ):
        """Initialize graph tool with safety configuration."""
        self.safety_config = safety_config or GraphSafetyConfig()
        self.operation_log: list[GraphOperation] = []

        # Initialize connection
        if GRAPH_MODULES_AVAILABLE:
            self.connection = connection or GraphConnection.from_env()
        else:
            self.connection = None
            logger.warning(
                "Graph connection not available - install neo4j and ensure "
                "graph modules are accessible",
            )

        # Initialize repositories
        self._adr_repository = None
        self._gcp_repository = None

        logger.info("GraphTool initialized with safety configuration")

    def _get_adr_repository(self, session: Session) -> ADRRepository:
        """Get ADR repository instance."""
        return ADRRepository(session)

    def _get_gcp_repository(self, session: Session) -> GCPRepository:
        """Get GCP repository instance."""
        return GCPRepository(session)

    def _validate_node_type(self, node_type: str) -> str:
        """
        Validate node type for safety.

        Args:
            node_type: Node type to validate

        Returns:
            Validated node type

        Raises:
            ValueError: If node type is protected
        """
        if node_type in self.safety_config.protected_node_types:
            raise ValueError(f"Cannot operate on protected node type: {node_type}")

        return node_type

    def _validate_query_complexity(self, query: str) -> None:
        """
        Validate Cypher query for safety.

        Args:
            query: Cypher query to validate

        Raises:
            ValueError: If query is too complex or dangerous
        """
        query_lower = query.lower()

        # Check for dangerous operations
        if not self.safety_config.allow_delete_operations:
            if "delete" in query_lower or "remove" in query_lower:
                raise ValueError(
                    "Delete operations not allowed by safety configuration"
                )

        if not self.safety_config.allow_schema_changes:
            dangerous_ops = [
                "drop",
                "create constraint",
                "create index",
                "drop constraint",
                "drop index",
            ]
            if any(op in query_lower for op in dangerous_ops):
                raise ValueError("Schema changes not allowed by safety configuration")

        # Simple complexity check based on query length and patterns
        complexity_score = len(query)
        complexity_score += query_lower.count("match") * 10
        complexity_score += query_lower.count("optional match") * 15
        complexity_score += query_lower.count("unwind") * 20

        if complexity_score > self.safety_config.max_query_complexity:
            raise ValueError(
                f"Query complexity ({complexity_score}) exceeds safety limit"
            )

    def _sanitize_properties(self, properties: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize node/relationship properties.

        Args:
            properties: Properties to sanitize

        Returns:
            Sanitized properties
        """
        sanitized: dict[str, Any] = {}

        for key, value in properties.items():
            # Validate key
            if not key or not isinstance(key, str):
                continue

            # Sanitize value based on type
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                # Only allow simple lists
                if all(isinstance(item, (str, int, float, bool)) for item in value):
                    sanitized[key] = value
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = self._sanitize_properties(value)
            elif isinstance(value, datetime):
                sanitized[key] = value.isoformat()
            else:
                # Convert other types to string
                sanitized[key] = str(value)

        return sanitized

    def _log_operation(
        self,
        operation: str,
        success: bool,
        message: str,
        node_id: str = "",
        relationship_id: str = "",
        query: str = "",
        result_count: int = 0,
        metadata: dict[str, Any] | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> GraphOperation:
        """Log graph operation for audit trail."""
        op = GraphOperation(
            success=success,
            operation=operation,
            message=message,
            node_id=node_id,
            relationship_id=relationship_id,
            query=query,
            result_count=result_count,
            metadata=metadata or {},
            stdout=stdout,
            stderr=stderr,
        )
        self.operation_log.append(op)

        if success:
            logger.info(f"GraphOp {operation}: {message}")
        else:
            logger.error(f"GraphOp {operation} FAILED: {message}")

        return op

    async def create_node(
        self,
        labels: list[str],
        properties: dict[str, Any],
        node_id: Optional[str] = None,
    ) -> GraphOperation:
        """
        Create a new node in the graph.

        Args:
            labels: Node labels
            properties: Node properties
            node_id: Optional specific node ID

        Returns:
            GraphOperation result
        """
        try:
            # Validate labels
            for label in labels:
                self._validate_node_type(label)

            # Generate ID if not provided
            if not node_id:
                node_id = str(uuid.uuid4())

            # Sanitize properties
            sanitized_props = self._sanitize_properties(properties)
            sanitized_props["id"] = node_id
            sanitized_props["created_at"] = datetime.utcnow().isoformat()
            sanitized_props["updated_at"] = datetime.utcnow().isoformat()

            # Build Cypher query
            labels_str = ":".join(labels)
            props_str = ", ".join([f"{key}: ${key}" for key in sanitized_props.keys()])
            query = f"CREATE (n:{labels_str} {{{props_str}}}) RETURN n"

            self._validate_query_complexity(query)

            if not self.connection:
                raise RuntimeError(
                    "Graph connection not available - ensure graph modules are properly configured",
                )

            with self.connection.session() as session:
                result = session.run(query, **sanitized_props)
                record = result.single()

                if record:
                    return self._log_operation(
                        "create_node",
                        True,
                        f"Created node with labels {labels}",
                        node_id=node_id,
                        query=query,
                        result_count=1,
                        metadata={
                            "labels": labels,
                            "properties": sanitized_props,
                            "node_id": node_id,
                        },
                    )
                else:
                    return self._log_operation(
                        "create_node",
                        False,
                        "Failed to create node - no result returned",
                        query=query,
                    )

        except Exception as e:
            return self._log_operation(
                "create_node",
                False,
                f"Node creation failed: {str(e)}",
                stderr=str(e),
            )

    async def create_edge(
        self,
        start_node_id: str,
        end_node_id: str,
        relationship_type: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphOperation:
        """
        Create a relationship between two nodes.

        Args:
            start_node_id: ID of the start node
            end_node_id: ID of the end node
            relationship_type: Type of relationship
            properties: Optional relationship properties

        Returns:
            GraphOperation result
        """
        try:
            # Sanitize properties
            rel_props = self._sanitize_properties(properties or {})
            rel_props["created_at"] = datetime.utcnow().isoformat()

            # Build Cypher query
            props_str = ""
            if rel_props:
                props_items = ", ".join([f"{key}: ${key}" for key in rel_props.keys()])
                props_str = f" {{{props_items}}}"

            query = f"""
            MATCH (start {{id: $start_node_id}})
            MATCH (end {{id: $end_node_id}})
            CREATE (start)-[r:{relationship_type}{props_str}]->(end)
            RETURN r
            """

            self._validate_query_complexity(query)

            params = {
                "start_node_id": start_node_id,
                "end_node_id": end_node_id,
                **rel_props,
            }

            if not self.connection:
                raise RuntimeError(
                    "Graph connection not available - ensure graph modules are properly configured",
                )

            with self.connection.session() as session:
                result = session.run(query, **params)
                record = result.single()

                if record:
                    relationship = record["r"]
                    rel_id = str(relationship.id)

                    return self._log_operation(
                        "create_edge",
                        True,
                        f"Created relationship {relationship_type} between "
                        f"{start_node_id} and {end_node_id}",
                        relationship_id=rel_id,
                        query=query,
                        result_count=1,
                        metadata={
                            "start_node_id": start_node_id,
                            "end_node_id": end_node_id,
                            "relationship_type": relationship_type,
                            "properties": rel_props,
                        },
                    )
                else:
                    return self._log_operation(
                        "create_edge",
                        False,
                        "Failed to create relationship - nodes may not exist",
                        query=query,
                    )

        except Exception as e:
            return self._log_operation(
                "create_edge",
                False,
                f"Relationship creation failed: {str(e)}",
                stderr=str(e),
            )

    async def query(
        self,
        cypher_query: str,
        parameters: dict[str, Any] | None = None,
        limit: Optional[int] = None,
    ) -> GraphOperation:
        """
        Execute a Cypher query.

        Args:
            cypher_query: Cypher query to execute
            parameters: Query parameters
            limit: Optional result limit

        Returns:
            GraphOperation result with query results
        """
        try:
            self._validate_query_complexity(cypher_query)

            # Apply limit if specified or enforce safety limit (but not for DDL statements)
            final_limit = limit or self.safety_config.max_results_per_query
            query_lower = cypher_query.lower()
            is_ddl = any(
                keyword in query_lower
                for keyword in [
                    "create constraint",
                    "create index",
                    "drop constraint",
                    "drop index",
                ]
            )

            if not is_ddl and "limit" not in query_lower:
                cypher_query += f" LIMIT {final_limit}"

            params = parameters or {}

            if not self.connection:
                raise RuntimeError(
                    "Graph connection not available - ensure graph modules are properly configured",
                )

            with self.connection.session() as session:
                result = session.run(cypher_query, **params)
                records = list(result)

                # Convert records to serializable format
                results = []
                for record in records:
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        if hasattr(value, "items"):  # Node or Relationship
                            record_dict[key] = dict(value)
                        else:
                            record_dict[key] = value
                    results.append(record_dict)

                return self._log_operation(
                    "query",
                    True,
                    f"Query executed successfully, returned {len(results)} records",
                    query=cypher_query,
                    result_count=len(results),
                    metadata={
                        "parameters": params,
                        "results": results[:10],  # Store first 10 results in metadata
                        "total_count": len(results),
                    },
                    stdout=str(results),
                )

        except Exception as e:
            return self._log_operation(
                "query",
                False,
                f"Query execution failed: {str(e)}",
                query=cypher_query,
                stderr=str(e),
            )

    async def validate_contracts(
        self,
        node_type: str,
        validation_rules: list[dict[str, Any]] | None = None,
    ) -> GraphOperation:
        """
        Validate graph contracts for specific node types.

        Args:
            node_type: Type of nodes to validate
            validation_rules: Optional custom validation rules

        Returns:
            GraphOperation result with validation results
        """
        try:
            validation_results = []
            issues_found = 0

            # Default validation rules based on node type
            if not validation_rules:
                validation_rules = self._get_default_validation_rules(node_type)

            # Execute validation queries
            if not self.connection:
                raise RuntimeError(
                    "Graph connection not available - ensure graph modules are properly configured",
                )

            with self.connection.session() as session:
                for rule in validation_rules:
                    rule_name = rule.get("name", "Unknown rule")
                    rule_query = rule.get("query", "")
                    rule_description = rule.get("description", "")

                    if not rule_query:
                        continue

                    try:
                        result = session.run(rule_query)
                        violations = list(result)

                        rule_result = {
                            "rule_name": rule_name,
                            "description": rule_description,
                            "violations_count": len(violations),
                            "violations": violations[:5],  # First 5 violations
                            "passed": len(violations) == 0,
                        }

                        validation_results.append(rule_result)

                        if len(violations) > 0:
                            issues_found += len(violations)

                    except Exception as e:
                        rule_result = {
                            "rule_name": rule_name,
                            "description": rule_description,
                            "error": str(e),
                            "passed": False,
                        }
                        validation_results.append(rule_result)

            # Overall validation result
            overall_passed = issues_found == 0

            return self._log_operation(
                "validate_contracts",
                True,
                f"Contract validation completed: {len(validation_rules)} rules "
                f"checked, {issues_found} issues found",
                result_count=len(validation_results),
                metadata={
                    "node_type": node_type,
                    "validation_results": validation_results,
                    "overall_passed": overall_passed,
                    "issues_count": issues_found,
                    "rules_count": len(validation_rules),
                },
            )

        except Exception as e:
            return self._log_operation(
                "validate_contracts",
                False,
                f"Contract validation failed: {str(e)}",
                stderr=str(e),
            )

    async def traverse_path(
        self,
        start_node_id: str,
        end_node_id: str,
        relationship_types: list[str] | None = None,
        max_depth: int = 5,
    ) -> GraphOperation:
        """
        Find paths between two nodes.

        Args:
            start_node_id: ID of start node
            end_node_id: ID of end node
            relationship_types: Optional relationship types to follow
            max_depth: Maximum path depth

        Returns:
            GraphOperation result with paths found
        """
        try:
            # Build relationship pattern
            rel_pattern = ""
            if relationship_types:
                rel_types = "|".join(relationship_types)
                rel_pattern = f"[:{rel_types}]"
            else:
                rel_pattern = "[]"

            # Build path query
            query = (
                f"MATCH path = (start {{id: $start_node_id}})-{rel_pattern}*1..{max_depth}-"
                f"(end {{id: $end_node_id}}) "
                f"RETURN path, length(path) as path_length "
                f"ORDER BY path_length LIMIT 100"
            )

            self._validate_query_complexity(query)

            params = {
                "start_node_id": start_node_id,
                "end_node_id": end_node_id,
            }

            if not self.connection:
                raise RuntimeError(
                    "Graph connection not available - ensure graph modules are properly configured",
                )

            with self.connection.session() as session:
                result = session.run(query, **params)
                records = list(result)

                paths = []
                for record in records:
                    path = record["path"]
                    path_length = record["path_length"]

                    # Extract path information
                    path_info = {
                        "length": path_length,
                        "nodes": [dict(node) for node in path.nodes],
                        "relationships": [
                            {"type": rel.type, "properties": dict(rel)}
                            for rel in path.relationships
                        ],
                    }
                    paths.append(path_info)

                return self._log_operation(
                    "traverse_path",
                    True,
                    f"Found {len(paths)} paths between {start_node_id} and {end_node_id}",
                    result_count=len(paths),
                    metadata={
                        "start_node_id": start_node_id,
                        "end_node_id": end_node_id,
                        "relationship_types": relationship_types,
                        "max_depth": max_depth,
                        "paths": paths[:5],  # First 5 paths
                        "paths_count": len(paths),
                    },
                )

        except Exception as e:
            return self._log_operation(
                "traverse_path",
                False,
                f"Path traversal failed: {str(e)}",
                stderr=str(e),
            )

    def _get_default_validation_rules(self, node_type: str) -> list[dict[str, Any]]:
        """Get default validation rules for a node type."""
        rules = []

        if node_type == "ADR":
            rules = [
                {
                    "name": "ADR has required properties",
                    "description": "All ADR nodes must have id, title, status, and decision",
                    "query": """
                    MATCH (adr:ADR)
                    WHERE adr.id IS NULL OR adr.title IS NULL
                          OR adr.status IS NULL OR adr.decision IS NULL
                    RETURN adr.id as node_id, 'Missing required properties' as issue
                    """,
                },
                {
                    "name": "ADR status is valid",
                    "description": "ADR status must be one of: proposed, accepted, deprecated",
                    "query": """
                    MATCH (adr:ADR)
                    WHERE NOT adr.status IN ['proposed', 'accepted', 'deprecated']
                    RETURN adr.id as node_id, adr.status as invalid_status
                    """,
                },
            ]
        elif node_type == "System":
            rules = [
                {
                    "name": "System has required properties",
                    "description": "All System nodes must have name and gcp_project",
                    "query": """
                    MATCH (sys:System)
                    WHERE sys.name IS NULL OR sys.gcp_project IS NULL
                    RETURN sys.name as node_name, 'Missing required properties' as issue
                    """,
                },
            ]

        return rules

    def get_operation_log(self) -> list[GraphOperation]:
        """Get the operation log for audit purposes."""
        return self.operation_log.copy()

    def clear_operation_log(self) -> None:
        """Clear the operation log."""
        self.operation_log.clear()
