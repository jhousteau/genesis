"""Edge to dependency translation for Terraform."""

import structlog

logger = structlog.get_logger(__name__)


class DependencyTranslator:
    """Translates graph edges to Terraform dependencies."""

    def translate_edges_to_dependencies(self, graph_data: dict) -> dict:
        """Convert graph edges to Terraform dependencies.

        Args:
            graph_data: Graph data with nodes and edges

        Returns:
            Dictionary mapping resources to their dependencies
        """
        dependencies = {}

        for edge in graph_data.get("edges", []):
            edge_type = edge.get("type", "").upper()
            source = edge.get("source")
            target = edge.get("target")

            if not source or not target:
                continue

            # Initialize dependency entry
            if source not in dependencies:
                dependencies[source] = {
                    "depends_on": [],
                    "environment_variables": {},
                    "iam_roles": [],
                    "event_triggers": [],
                    "pubsub_topics": [],
                }

            # Process based on edge type
            if edge_type == "CALLS":
                deps = self.process_api_dependency(edge)
            elif edge_type == "PUBLISHES":
                deps = self.process_pubsub_publisher(edge)
            elif edge_type == "SUBSCRIBES":
                deps = self.process_pubsub_subscriber(edge)
            elif edge_type in ["READS", "WRITES"]:
                deps = self.process_database_dependency(edge)
            elif edge_type == "STORES":
                deps = self.process_storage_dependency(edge)
            elif edge_type == "TRIGGERS":
                deps = self.process_trigger_dependency(edge)
            elif edge_type == "DEPENDS_ON":
                deps = self.process_direct_dependency(edge)
            else:
                logger.warning(f"Unknown edge type: {edge_type}", edge=edge)
                continue

            # Merge dependencies
            self._merge_dependencies(dependencies[source], deps)

        return dependencies

    def process_api_dependency(self, edge: dict) -> dict:
        """Process API call dependencies.

        Args:
            edge: Edge data

        Returns:
            Dependency configuration
        """
        target = edge.get("target")
        return {
            "depends_on": [f"module.{target}"],
            "environment_variables": {
                f"{target.upper().replace('-', '_')}_URL": f"${{module.{target}.service_url}}",
            },
        }

    def process_pubsub_publisher(self, edge: dict) -> dict:
        """Process Pub/Sub publisher dependencies.

        Args:
            edge: Edge data

        Returns:
            Dependency configuration
        """
        target = edge.get("target")
        return {
            "depends_on": [f"module.{target}"],
            "pubsub_topics": [target],
            "environment_variables": {
                f"{target.upper().replace('-', '_')}_TOPIC": f"${{module.{target}.topic_name}}",
            },
            "iam_roles": ["roles/pubsub.publisher"],
        }

    def process_pubsub_subscriber(self, edge: dict) -> dict:
        """Process Pub/Sub subscriber dependencies.

        Args:
            edge: Edge data

        Returns:
            Dependency configuration
        """
        target = edge.get("target")
        return {
            "depends_on": [f"module.{target}"],
            "event_triggers": [
                {
                    "event_type": "google.pubsub.topic.publish",
                    "resource": f"${{module.{target}.topic_id}}",
                },
            ],
            "iam_roles": ["roles/pubsub.subscriber"],
        }

    def process_database_dependency(self, edge: dict) -> dict:
        """Process database access dependencies.

        Args:
            edge: Edge data

        Returns:
            Dependency configuration
        """
        target = edge.get("target")
        edge_type = edge.get("type", "").upper()

        # Determine IAM roles based on access type
        if edge_type == "WRITES":
            roles = ["roles/datastore.user", "roles/firestore.writer"]
        else:
            roles = ["roles/datastore.viewer", "roles/firestore.reader"]

        return {
            "depends_on": [f"module.{target}"],
            "environment_variables": {
                f"{target.upper().replace('-', '_')}_DATABASE": (
                    f"${{module.{target}.database_name}}"
                ),
                f"{target.upper().replace('-', '_')}_PROJECT": "${var.project_id}",
            },
            "iam_roles": roles,
        }

    def process_storage_dependency(self, edge: dict) -> dict:
        """Process storage dependencies.

        Args:
            edge: Edge data

        Returns:
            Dependency configuration
        """
        target = edge.get("target")
        return {
            "depends_on": [f"module.{target}"],
            "environment_variables": {
                f"{target.upper().replace('-', '_')}_BUCKET": f"${{module.{target}.bucket_name}}",
            },
            "iam_roles": ["roles/storage.objectAdmin"],
        }

    def process_trigger_dependency(self, edge: dict) -> dict:
        """Process trigger dependencies.

        Args:
            edge: Edge data

        Returns:
            Dependency configuration
        """
        target = edge.get("target")
        trigger_type = edge.get("properties", {}).get("trigger_type", "http")

        if trigger_type == "http":
            return {
                "depends_on": [f"module.{target}"],
                "environment_variables": {
                    f"{target.upper().replace('-', '_')}_TRIGGER_URL": (
                        f"${{module.{target}.trigger_url}}"
                    ),
                },
            }
        elif trigger_type == "storage":
            return {
                "depends_on": [f"module.{target}"],
                "event_triggers": [
                    {
                        "event_type": "google.storage.object.finalize",
                        "resource": f"${{module.{target}.bucket_name}}",
                    },
                ],
            }
        else:
            return {"depends_on": [f"module.{target}"]}

    def process_direct_dependency(self, edge: dict) -> dict:
        """Process direct dependencies.

        Args:
            edge: Edge data

        Returns:
            Dependency configuration
        """
        target = edge.get("target")
        return {"depends_on": [f"module.{target}"]}

    def detect_circular_dependencies(self, graph_data: dict) -> list[list[str]]:
        """Detect circular dependencies in the graph.

        Args:
            graph_data: Graph data

        Returns:
            List of circular dependency cycles
        """
        # Build adjacency list
        adjacency = {}
        for edge in graph_data.get("edges", []):
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                if source not in adjacency:
                    adjacency[source] = []
                adjacency[source].append(target)

        # DFS to detect cycles
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            if node in adjacency:
                for neighbor in adjacency[node]:
                    if neighbor not in visited:
                        if dfs(neighbor, path.copy()):
                            return True
                    elif neighbor in rec_stack:
                        # Found cycle
                        cycle_start = path.index(neighbor)
                        cycles.append(path[cycle_start:] + [neighbor])

            rec_stack.remove(node)
            return False

        # Check all nodes
        for node in adjacency:
            if node not in visited:
                dfs(node, [])

        return cycles

    def get_deployment_order(self, graph_data: dict) -> list[str]:
        """Get topologically sorted deployment order.

        Args:
            graph_data: Graph data

        Returns:
            Ordered list of nodes for deployment
        """
        # Build dependency graph
        in_degree = {}
        adjacency = {}
        all_nodes = set()

        # Initialize from nodes
        for node in graph_data.get("nodes", []):
            node_name = node.get("name")
            if node_name:
                all_nodes.add(node_name)
                in_degree[node_name] = 0
                adjacency[node_name] = []

        # Build from edges
        for edge in graph_data.get("edges", []):
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                all_nodes.add(source)
                all_nodes.add(target)

                if source not in adjacency:
                    adjacency[source] = []
                adjacency[source].append(target)

                if target not in in_degree:
                    in_degree[target] = 0
                in_degree[target] += 1

                if source not in in_degree:
                    in_degree[source] = 0

        # Topological sort using Kahn's algorithm
        queue = [node for node in all_nodes if in_degree.get(node, 0) == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        if len(result) != len(all_nodes):
            logger.warning("Circular dependencies detected in graph")
            # Return partial order
            for node in all_nodes:
                if node not in result:
                    result.append(node)

        return result

    def _merge_dependencies(self, target: dict, source: dict) -> None:
        """Merge dependency configurations.

        Args:
            target: Target dependency dict to merge into
            source: Source dependency dict to merge from
        """
        # Merge depends_on
        if "depends_on" in source:
            for dep in source["depends_on"]:
                if dep not in target["depends_on"]:
                    target["depends_on"].append(dep)

        # Merge environment variables
        if "environment_variables" in source:
            target["environment_variables"].update(source["environment_variables"])

        # Merge IAM roles
        if "iam_roles" in source:
            for role in source["iam_roles"]:
                if role not in target["iam_roles"]:
                    target["iam_roles"].append(role)

        # Merge event triggers
        if "event_triggers" in source:
            target["event_triggers"].extend(source["event_triggers"])

        # Merge pubsub topics
        if "pubsub_topics" in source:
            for topic in source["pubsub_topics"]:
                if topic not in target["pubsub_topics"]:
                    target["pubsub_topics"].append(topic)
