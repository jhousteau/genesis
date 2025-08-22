"""
Service Dependency Mapping and Analysis
Analyzes trace data to build service dependency graphs and detect issues.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

import networkx as nx

try:
    from google.cloud import trace_v1
    from google.cloud.trace_v1.types import Trace, TraceSpan

    GCP_TRACE_AVAILABLE = True
except ImportError:
    GCP_TRACE_AVAILABLE = False

try:
    import jaeger_client

    JAEGER_AVAILABLE = True
except ImportError:
    JAEGER_AVAILABLE = False


@dataclass
class ServiceNode:
    """Represents a service in the dependency graph."""

    name: str
    version: str = "unknown"
    environment: str = "unknown"
    call_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class ServiceEdge:
    """Represents a dependency relationship between services."""

    caller: str
    callee: str
    call_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    success_rate: float = 100.0
    last_seen: datetime = field(default_factory=datetime.now)
    operation_patterns: Dict[str, int] = field(default_factory=dict)
    error_patterns: Dict[str, int] = field(default_factory=dict)


@dataclass
class TraceSpan:
    """Simplified trace span for analysis."""

    span_id: str
    trace_id: str
    parent_span_id: str
    service_name: str
    operation_name: str
    start_time: datetime
    duration_ms: float
    status: str  # 'OK', 'ERROR', 'TIMEOUT'
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)


class ServiceDependencyMapper:
    """Analyzes traces to build and maintain service dependency graphs."""

    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self.service_graph = nx.DiGraph()
        self.services: Dict[str, ServiceNode] = {}
        self.edges: Dict[Tuple[str, str], ServiceEdge] = {}
        self.traces: List[List[TraceSpan]] = []

        # Initialize clients
        if GCP_TRACE_AVAILABLE and project_id:
            self.trace_client = trace_v1.TraceServiceClient()

    def add_trace(self, spans: List[TraceSpan]):
        """Add a trace (collection of spans) for analysis."""
        if not spans:
            return

        self.traces.append(spans)

        # Sort spans by start time to build proper call chains
        sorted_spans = sorted(spans, key=lambda s: s.start_time)

        # Build service nodes
        for span in sorted_spans:
            self._update_service_node(span)

        # Build service edges (dependencies)
        self._analyze_dependencies(sorted_spans)

        # Update the NetworkX graph
        self._update_graph()

    def _update_service_node(self, span: TraceSpan):
        """Update or create a service node from span data."""
        service_name = span.service_name

        if service_name not in self.services:
            self.services[service_name] = ServiceNode(
                name=service_name,
                version=span.tags.get("service.version", "unknown"),
                environment=span.tags.get("deployment.environment", "unknown"),
            )

        service = self.services[service_name]
        service.call_count += 1
        service.last_seen = max(service.last_seen, span.start_time)

        # Update error count
        if span.status == "ERROR":
            service.error_count += 1

        # Update latency metrics (simplified - should use proper percentile calculation)
        if service.call_count == 1:
            service.avg_latency_ms = span.duration_ms
            service.p95_latency_ms = span.duration_ms
            service.p99_latency_ms = span.duration_ms
        else:
            # Running average (simplified)
            service.avg_latency_ms = (
                service.avg_latency_ms * (service.call_count - 1) + span.duration_ms
            ) / service.call_count
            # For proper percentiles, we'd need to maintain a histogram
            service.p95_latency_ms = max(service.p95_latency_ms, span.duration_ms)
            service.p99_latency_ms = max(service.p99_latency_ms, span.duration_ms)

    def _analyze_dependencies(self, spans: List[TraceSpan]):
        """Analyze spans to determine service dependencies."""
        # Create a mapping of span_id to span for quick lookup
        span_map = {span.span_id: span for span in spans}

        # Find parent-child relationships
        for span in spans:
            if span.parent_span_id and span.parent_span_id in span_map:
                parent_span = span_map[span.parent_span_id]

                # If parent and child are different services, there's a dependency
                if parent_span.service_name != span.service_name:
                    caller = parent_span.service_name
                    callee = span.service_name

                    # Update service dependencies
                    self.services[caller].dependencies.add(callee)
                    self.services[callee].dependents.add(caller)

                    # Update or create edge
                    self._update_service_edge(parent_span, span)

    def _update_service_edge(self, parent_span: TraceSpan, child_span: TraceSpan):
        """Update or create a service dependency edge."""
        edge_key = (parent_span.service_name, child_span.service_name)

        if edge_key not in self.edges:
            self.edges[edge_key] = ServiceEdge(
                caller=parent_span.service_name, callee=child_span.service_name
            )

        edge = self.edges[edge_key]
        edge.call_count += 1
        edge.last_seen = max(edge.last_seen, child_span.start_time)

        # Update error count
        if child_span.status == "ERROR":
            edge.error_count += 1

        # Update latency metrics
        if edge.call_count == 1:
            edge.avg_latency_ms = child_span.duration_ms
            edge.p95_latency_ms = child_span.duration_ms
        else:
            edge.avg_latency_ms = (
                edge.avg_latency_ms * (edge.call_count - 1) + child_span.duration_ms
            ) / edge.call_count
            edge.p95_latency_ms = max(edge.p95_latency_ms, child_span.duration_ms)

        # Update success rate
        edge.success_rate = (
            (edge.call_count - edge.error_count) / edge.call_count
        ) * 100

        # Track operation patterns
        operation = child_span.operation_name
        edge.operation_patterns[operation] = (
            edge.operation_patterns.get(operation, 0) + 1
        )

        # Track error patterns
        if child_span.status == "ERROR":
            error_type = child_span.tags.get("error.type", "unknown")
            edge.error_patterns[error_type] = edge.error_patterns.get(error_type, 0) + 1

    def _update_graph(self):
        """Update the NetworkX graph with current service data."""
        self.service_graph.clear()

        # Add nodes
        for service_name, service in self.services.items():
            self.service_graph.add_node(
                service_name,
                version=service.version,
                environment=service.environment,
                call_count=service.call_count,
                error_count=service.error_count,
                avg_latency_ms=service.avg_latency_ms,
                error_rate=(
                    (service.error_count / service.call_count) * 100
                    if service.call_count > 0
                    else 0
                ),
            )

        # Add edges
        for (caller, callee), edge in self.edges.items():
            self.service_graph.add_edge(
                caller,
                callee,
                call_count=edge.call_count,
                error_count=edge.error_count,
                avg_latency_ms=edge.avg_latency_ms,
                success_rate=edge.success_rate,
                weight=edge.call_count,  # For graph algorithms
            )

    def get_service_dependencies(self, service_name: str) -> Dict[str, Any]:
        """Get detailed dependency information for a service."""
        if service_name not in self.services:
            return {}

        service = self.services[service_name]

        # Get direct dependencies
        dependencies = []
        for dep_name in service.dependencies:
            edge_key = (service_name, dep_name)
            if edge_key in self.edges:
                edge = self.edges[edge_key]
                dependencies.append(
                    {
                        "service": dep_name,
                        "call_count": edge.call_count,
                        "error_count": edge.error_count,
                        "success_rate": edge.success_rate,
                        "avg_latency_ms": edge.avg_latency_ms,
                        "top_operations": sorted(
                            edge.operation_patterns.items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:5],
                    }
                )

        # Get services that depend on this service
        dependents = []
        for dep_name in service.dependents:
            edge_key = (dep_name, service_name)
            if edge_key in self.edges:
                edge = self.edges[edge_key]
                dependents.append(
                    {
                        "service": dep_name,
                        "call_count": edge.call_count,
                        "error_count": edge.error_count,
                        "success_rate": edge.success_rate,
                        "avg_latency_ms": edge.avg_latency_ms,
                    }
                )

        return {
            "service_name": service_name,
            "service_info": {
                "version": service.version,
                "environment": service.environment,
                "total_calls": service.call_count,
                "error_count": service.error_count,
                "error_rate": (
                    (service.error_count / service.call_count) * 100
                    if service.call_count > 0
                    else 0
                ),
                "avg_latency_ms": service.avg_latency_ms,
                "last_seen": service.last_seen.isoformat(),
            },
            "dependencies": sorted(
                dependencies, key=lambda x: x["call_count"], reverse=True
            ),
            "dependents": sorted(
                dependents, key=lambda x: x["call_count"], reverse=True
            ),
            "dependency_count": len(service.dependencies),
            "dependent_count": len(service.dependents),
        }

    def find_critical_path(
        self, start_service: str, end_service: str
    ) -> List[Dict[str, Any]]:
        """Find the critical path between two services."""
        try:
            # Find shortest path by latency (inverse of weight)
            path = nx.shortest_path(
                self.service_graph,
                start_service,
                end_service,
                weight=lambda u, v, d: 1
                / d.get("weight", 1),  # Inverse weight for shortest path
            )

            critical_path = []
            for i in range(len(path) - 1):
                caller, callee = path[i], path[i + 1]
                edge_data = self.service_graph[caller][callee]
                critical_path.append(
                    {
                        "from": caller,
                        "to": callee,
                        "call_count": edge_data.get("call_count", 0),
                        "avg_latency_ms": edge_data.get("avg_latency_ms", 0),
                        "success_rate": edge_data.get("success_rate", 100),
                    }
                )

            return critical_path
        except nx.NetworkXNoPath:
            return []

    def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in the service graph."""
        try:
            cycles = list(nx.simple_cycles(self.service_graph))
            return cycles
        except nx.NetworkXNoCycle:
            return []

    def find_bottlenecks(
        self, threshold_latency_ms: float = 1000
    ) -> List[Dict[str, Any]]:
        """Find potential bottlenecks in the service graph."""
        bottlenecks = []

        for service_name, service in self.services.items():
            # High latency services
            if service.avg_latency_ms > threshold_latency_ms:
                bottlenecks.append(
                    {
                        "type": "high_latency",
                        "service": service_name,
                        "avg_latency_ms": service.avg_latency_ms,
                        "call_count": service.call_count,
                        "impact_score": service.call_count * service.avg_latency_ms,
                    }
                )

            # High error rate services
            error_rate = (
                (service.error_count / service.call_count) * 100
                if service.call_count > 0
                else 0
            )
            if error_rate > 5:  # 5% error rate threshold
                bottlenecks.append(
                    {
                        "type": "high_error_rate",
                        "service": service_name,
                        "error_rate": error_rate,
                        "error_count": service.error_count,
                        "call_count": service.call_count,
                    }
                )

        # Find services with many dependencies (potential single points of failure)
        for service_name, service in self.services.items():
            if len(service.dependents) > 5:  # Threshold for high fan-in
                bottlenecks.append(
                    {
                        "type": "high_dependency",
                        "service": service_name,
                        "dependent_count": len(service.dependents),
                        "dependents": list(service.dependents),
                    }
                )

        return sorted(bottlenecks, key=lambda x: x.get("impact_score", 0), reverse=True)

    def analyze_blast_radius(self, service_name: str) -> Dict[str, Any]:
        """Analyze the blast radius if a service fails."""
        if service_name not in self.service_graph:
            return {}

        # Find all services that would be affected if this service fails
        affected_services = set()

        def find_downstream(node):
            for successor in self.service_graph.successors(node):
                if successor not in affected_services:
                    affected_services.add(successor)
                    find_downstream(successor)

        find_downstream(service_name)

        # Calculate impact metrics
        total_calls_affected = 0
        critical_services = []

        for affected_service in affected_services:
            service = self.services[affected_service]
            total_calls_affected += service.call_count

            # Consider services with many dependents as critical
            if len(service.dependents) > 3:
                critical_services.append(
                    {
                        "service": affected_service,
                        "dependent_count": len(service.dependents),
                        "call_count": service.call_count,
                    }
                )

        return {
            "failing_service": service_name,
            "affected_service_count": len(affected_services),
            "affected_services": list(affected_services),
            "total_calls_affected": total_calls_affected,
            "critical_services_affected": critical_services,
            "blast_radius_score": len(affected_services) * total_calls_affected,
        }

    def get_service_mesh_topology(self) -> Dict[str, Any]:
        """Get the complete service mesh topology."""
        topology = {
            "services": [],
            "connections": [],
            "metrics": {
                "total_services": len(self.services),
                "total_connections": len(self.edges),
                "total_calls": sum(s.call_count for s in self.services.values()),
                "total_errors": sum(s.error_count for s in self.services.values()),
            },
        }

        # Add service information
        for service_name, service in self.services.items():
            topology["services"].append(
                {
                    "name": service_name,
                    "version": service.version,
                    "environment": service.environment,
                    "call_count": service.call_count,
                    "error_count": service.error_count,
                    "error_rate": (
                        (service.error_count / service.call_count) * 100
                        if service.call_count > 0
                        else 0
                    ),
                    "avg_latency_ms": service.avg_latency_ms,
                    "dependency_count": len(service.dependencies),
                    "dependent_count": len(service.dependents),
                    "last_seen": service.last_seen.isoformat(),
                }
            )

        # Add connection information
        for (caller, callee), edge in self.edges.items():
            topology["connections"].append(
                {
                    "from": caller,
                    "to": callee,
                    "call_count": edge.call_count,
                    "error_count": edge.error_count,
                    "success_rate": edge.success_rate,
                    "avg_latency_ms": edge.avg_latency_ms,
                    "p95_latency_ms": edge.p95_latency_ms,
                    "top_operations": sorted(
                        edge.operation_patterns.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:3],
                    "error_patterns": (
                        dict(edge.error_patterns) if edge.error_patterns else {}
                    ),
                }
            )

        return topology

    def export_for_visualization(self, format: str = "graphviz") -> str:
        """Export the service graph for visualization tools."""
        if format == "graphviz":
            return self._export_graphviz()
        elif format == "cytoscape":
            return self._export_cytoscape()
        elif format == "mermaid":
            return self._export_mermaid()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_graphviz(self) -> str:
        """Export as Graphviz DOT format."""
        lines = ["digraph ServiceDependencies {"]
        lines.append("  rankdir=TB;")
        lines.append("  node [shape=box, style=filled];")

        # Add nodes
        for service_name, service in self.services.items():
            error_rate = (
                (service.error_count / service.call_count) * 100
                if service.call_count > 0
                else 0
            )
            color = (
                "red"
                if error_rate > 5
                else "yellow"
                if error_rate > 1
                else "lightgreen"
            )

            lines.append(
                f'  "{service_name}" [fillcolor="{color}", label="{service_name}\\nCalls: {service.call_count}\\nErrors: {error_rate:.1f}%"];'
            )

        # Add edges
        for (caller, callee), edge in self.edges.items():
            thickness = min(max(edge.call_count / 100, 1), 5)  # Scale thickness
            color = "red" if edge.success_rate < 95 else "black"

            lines.append(
                f'  "{caller}" -> "{callee}" [penwidth={thickness}, color="{color}", label="{edge.call_count}"];'
            )

        lines.append("}")
        return "\n".join(lines)

    def _export_cytoscape(self) -> str:
        """Export as Cytoscape JSON format."""
        elements = []

        # Add nodes
        for service_name, service in self.services.items():
            error_rate = (
                (service.error_count / service.call_count) * 100
                if service.call_count > 0
                else 0
            )
            elements.append(
                {
                    "data": {
                        "id": service_name,
                        "label": service_name,
                        "call_count": service.call_count,
                        "error_rate": error_rate,
                        "avg_latency": service.avg_latency_ms,
                    }
                }
            )

        # Add edges
        for (caller, callee), edge in self.edges.items():
            elements.append(
                {
                    "data": {
                        "source": caller,
                        "target": callee,
                        "call_count": edge.call_count,
                        "success_rate": edge.success_rate,
                        "avg_latency": edge.avg_latency_ms,
                    }
                }
            )

        return json.dumps({"elements": elements}, indent=2)

    def _export_mermaid(self) -> str:
        """Export as Mermaid diagram format."""
        lines = ["graph TB"]

        # Add edges (nodes will be inferred)
        for (caller, callee), edge in self.edges.items():
            # Clean service names for Mermaid
            caller_clean = caller.replace("-", "_").replace(".", "_")
            callee_clean = callee.replace("-", "_").replace(".", "_")

            lines.append(
                f"  {caller_clean}[{caller}] -->|{edge.call_count}| {callee_clean}[{callee}]"
            )

        return "\n".join(lines)


# Convenience functions
def create_dependency_mapper(project_id: str = None) -> ServiceDependencyMapper:
    """Create a service dependency mapper with default configuration."""
    return ServiceDependencyMapper(project_id)


def analyze_trace_file(file_path: str, project_id: str = None) -> Dict[str, Any]:
    """Analyze traces from a JSON file and return dependency analysis."""
    mapper = ServiceDependencyMapper(project_id)

    with open(file_path, "r") as f:
        trace_data = json.load(f)

    # Convert JSON trace data to TraceSpan objects
    for trace in trace_data.get("traces", []):
        spans = []
        for span_data in trace.get("spans", []):
            span = TraceSpan(
                span_id=span_data.get("spanId", ""),
                trace_id=span_data.get("traceId", ""),
                parent_span_id=span_data.get("parentSpanId", ""),
                service_name=span_data.get("serviceName", "unknown"),
                operation_name=span_data.get("operationName", ""),
                start_time=datetime.fromtimestamp(span_data.get("startTime", 0) / 1000),
                duration_ms=span_data.get("duration", 0) / 1000,
                status=(
                    "ERROR" if span_data.get("status", {}).get("code") != 0 else "OK"
                ),
                tags=span_data.get("tags", {}),
                logs=span_data.get("logs", []),
            )
            spans.append(span)

        if spans:
            mapper.add_trace(spans)

    return mapper.get_service_mesh_topology()


def find_service_issues(
    mapper: ServiceDependencyMapper,
) -> Dict[str, List[Dict[str, Any]]]:
    """Find common issues in the service dependency graph."""
    issues = {
        "bottlenecks": mapper.find_bottlenecks(),
        "circular_dependencies": mapper.detect_circular_dependencies(),
        "high_blast_radius": [],
    }

    # Find services with high blast radius
    for service_name in mapper.services.keys():
        blast_radius = mapper.analyze_blast_radius(service_name)
        if blast_radius.get("affected_service_count", 0) > 5:
            issues["high_blast_radius"].append(blast_radius)

    # Sort by impact
    issues["high_blast_radius"] = sorted(
        issues["high_blast_radius"],
        key=lambda x: x.get("blast_radius_score", 0),
        reverse=True,
    )

    return issues
