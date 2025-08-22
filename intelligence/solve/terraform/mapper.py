"""Node to Terraform resource mapping."""

from pathlib import Path
from typing import Optional

import structlog

from .models import TerraformResource

logger = structlog.get_logger(__name__)

# Comprehensive node to resource mapping
NODE_TO_RESOURCE_MAP = {
    "cloud_run": {
        "resources": [
            "google_cloud_run_service",
            "google_cloud_run_service_iam_member",
        ],
        "archetype": "cloud-run",
    },
    "cloudrun": {
        "resources": [
            "google_cloud_run_service",
            "google_cloud_run_service_iam_member",
        ],
        "archetype": "cloud-run",
    },
    "cloud_function": {
        "resources": [
            "google_cloudfunctions2_function",
            "google_cloudfunctions2_function_iam_member",
        ],
        "archetype": "cloud-function",
    },
    "cloudfunction": {
        "resources": [
            "google_cloudfunctions2_function",
            "google_cloudfunctions2_function_iam_member",
        ],
        "archetype": "cloud-function",
    },
    "pubsub": {
        "resources": ["google_pubsub_topic", "google_pubsub_subscription"],
        "archetype": "pubsub-topic",
    },
    "firestore": {
        "resources": ["google_firestore_database", "google_firestore_index"],
        "archetype": "firestore-db",
    },
    "cloud_storage": {
        "resources": ["google_storage_bucket", "google_storage_bucket_iam_member"],
        "archetype": "cloud-storage",
    },
    "cloudstorage": {
        "resources": ["google_storage_bucket", "google_storage_bucket_iam_member"],
        "archetype": "cloud-storage",
    },
    "cloud_tasks": {
        "resources": ["google_cloud_tasks_queue"],
        "archetype": "cloud-tasks",
    },
    "cloudtasks": {
        "resources": ["google_cloud_tasks_queue"],
        "archetype": "cloud-tasks",
    },
    "cloud_sql": {
        "resources": [
            "google_sql_database_instance",
            "google_sql_database",
            "google_sql_user",
        ],
        "archetype": "cloud-sql",
    },
    "cloudsql": {
        "resources": [
            "google_sql_database_instance",
            "google_sql_database",
            "google_sql_user",
        ],
        "archetype": "cloud-sql",
    },
}


class ResourceMapper:
    """Maps graph nodes to Terraform resources."""

    def __init__(self, archetype_registry=None):
        """Initialize the mapper.

        Args:
            archetype_registry: Optional registry of archetype templates
        """
        self.archetype_registry = archetype_registry
        self.archetype_cache = {}

    def node_to_resources(self, node: dict) -> list[TerraformResource]:
        """Convert a graph node to Terraform resources.

        Args:
            node: Graph node data

        Returns:
            List of Terraform resources
        """
        node_type = self._get_node_type(node)

        if node_type not in NODE_TO_RESOURCE_MAP:
            logger.warning(f"Unknown node type: {node_type}", node=node)
            return []

        resources = []

        # Generate resources based on node type
        if node_type in ["cloud_run", "cloudrun"]:
            resources.extend(self._create_cloud_run_resources(node))
        elif node_type in ["cloud_function", "cloudfunction"]:
            resources.extend(self._create_cloud_function_resources(node))
        elif node_type == "pubsub":
            resources.extend(self._create_pubsub_resources(node))
        elif node_type == "firestore":
            resources.extend(self._create_firestore_resources(node))
        elif node_type in ["cloud_storage", "cloudstorage"]:
            resources.extend(self._create_storage_resources(node))
        elif node_type in ["cloud_tasks", "cloudtasks"]:
            resources.extend(self._create_cloud_tasks_resources(node))
        elif node_type in ["cloud_sql", "cloudsql"]:
            resources.extend(self._create_cloud_sql_resources(node))

        return resources

    def get_archetype_template(self, node_type: str) -> Optional[str]:
        """Load archetype template for a node type.

        Args:
            node_type: Type of the node

        Returns:
            Template content or None
        """
        if node_type in self.archetype_cache:
            return self.archetype_cache[node_type]

        if node_type not in NODE_TO_RESOURCE_MAP:
            return None

        archetype_name = NODE_TO_RESOURCE_MAP[node_type]["archetype"]
        template_path = Path("templates/archetypes") / archetype_name / "main.tf"

        if template_path.exists():
            template = template_path.read_text()
            self.archetype_cache[node_type] = template
            return template

        return None

    def apply_node_properties(self, template: str, node: dict) -> str:
        """Apply node properties to a template.

        Args:
            template: Template string
            node: Node with properties

        Returns:
            Template with substituted values
        """
        # Simple variable substitution
        replacements = {
            "${node_name}": node.get("name", "unnamed"),
            "${project_id}": "var.project_id",
            "${region}": "var.region",
            "${environment}": "var.environment",
        }

        for key, value in replacements.items():
            template = template.replace(key, value)

        return template

    def _get_node_type(self, node: dict) -> str:
        """Extract node type from node data.

        Args:
            node: Node data

        Returns:
            Normalized node type
        """
        # Try different fields
        node_type = (
            node.get("primitive_type")
            or node.get("type", "").lower().replace(" ", "_")
            or "unknown"
        )

        # Normalize
        return node_type.lower().replace("-", "_")

    def _create_cloud_run_resources(self, node: dict) -> list[TerraformResource]:
        """Create Cloud Run resources.

        Args:
            node: Node data

        Returns:
            List of Cloud Run resources
        """
        resources = []
        name = node.get("name", "unnamed")

        # Main Cloud Run service
        service = TerraformResource(
            resource_type="google_cloud_run_service",
            resource_name=name,
            properties={
                "name": name,
                "location": "${var.region}",
                "project": "${var.project_id}",
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "image": node.get("image", "gcr.io/cloudrun/hello"),
                                "ports": [{"container_port": node.get("port", 8080)}],
                                "resources": {
                                    "limits": {
                                        "cpu": node.get("cpu", "1"),
                                        "memory": node.get("memory", "512Mi"),
                                    },
                                },
                            },
                        ],
                        "service_account_name": (
                            f"{name}-sa@${{var.project_id}}.iam.gserviceaccount.com"
                        ),
                    },
                    "metadata": {
                        "annotations": {
                            "autoscaling.knative.dev/minScale": str(
                                node.get("min_instances", 0)
                            ),
                            "autoscaling.knative.dev/maxScale": str(
                                node.get("max_instances", 100)
                            ),
                        },
                    },
                },
                "traffic": [{"percent": 100, "latest_revision": True}],
            },
        )
        resources.append(service)

        # IAM binding
        iam = TerraformResource(
            resource_type="google_cloud_run_service_iam_member",
            resource_name=f"{name}_invoker",
            properties={
                "service": f"google_cloud_run_service.{name}.name",
                "location": f"google_cloud_run_service.{name}.location",
                "project": f"google_cloud_run_service.{name}.project",
                "role": "roles/run.invoker",
                "member": "allUsers",  # Will be customized based on requirements
            },
        )
        resources.append(iam)

        return resources

    def _create_cloud_function_resources(self, node: dict) -> list[TerraformResource]:
        """Create Cloud Function resources.

        Args:
            node: Node data

        Returns:
            List of Cloud Function resources
        """
        resources = []
        name = node.get("name", "unnamed")

        # Cloud Function v2
        function = TerraformResource(
            resource_type="google_cloudfunctions2_function",
            resource_name=name,
            properties={
                "name": name,
                "location": "${var.region}",
                "project": "${var.project_id}",
                "build_config": {
                    "runtime": node.get("runtime", "python39"),
                    "entry_point": node.get("entry_point", "main"),
                    "source": {
                        "storage_source": {
                            "bucket": "${var.project_id}-functions",
                            "object": f"{name}.zip",
                        },
                    },
                },
                "service_config": {
                    "max_instance_count": node.get("max_instances", 100),
                    "min_instance_count": node.get("min_instances", 0),
                    "available_memory": node.get("memory", "256M"),
                    "timeout_seconds": node.get("timeout", 60),
                    "service_account_email": (
                        f"{name}-sa@${{var.project_id}}.iam.gserviceaccount.com"
                    ),
                },
            },
        )
        resources.append(function)

        # IAM binding
        iam = TerraformResource(
            resource_type="google_cloudfunctions2_function_iam_member",
            resource_name=f"{name}_invoker",
            properties={
                "cloud_function": f"google_cloudfunctions2_function.{name}.name",
                "location": f"google_cloudfunctions2_function.{name}.location",
                "project": f"google_cloudfunctions2_function.{name}.project",
                "role": "roles/cloudfunctions.invoker",
                "member": "allUsers",
            },
        )
        resources.append(iam)

        return resources

    def _create_pubsub_resources(self, node: dict) -> list[TerraformResource]:
        """Create Pub/Sub resources.

        Args:
            node: Node data

        Returns:
            List of Pub/Sub resources
        """
        resources = []
        name = node.get("name", "unnamed")

        # Topic
        topic = TerraformResource(
            resource_type="google_pubsub_topic",
            resource_name=name,
            properties={
                "name": name,
                "project": "${var.project_id}",
                "message_retention_duration": node.get("retention", "86400s"),
                "labels": {"environment": "${var.environment}", "managed_by": "solve"},
            },
        )
        resources.append(topic)

        # Default subscription
        subscription = TerraformResource(
            resource_type="google_pubsub_subscription",
            resource_name=f"{name}_default",
            properties={
                "name": f"{name}-default-sub",
                "topic": f"google_pubsub_topic.{name}.name",
                "project": "${var.project_id}",
                "ack_deadline_seconds": node.get("ack_deadline", 10),
                "message_retention_duration": node.get("retention", "604800s"),
                "retain_acked_messages": False,
                "enable_message_ordering": node.get("ordered", False),
            },
        )
        resources.append(subscription)

        return resources

    def _create_firestore_resources(self, node: dict) -> list[TerraformResource]:
        """Create Firestore resources.

        Args:
            node: Node data

        Returns:
            List of Firestore resources
        """
        resources = []
        name = node.get("name", "unnamed")

        # Firestore database
        database = TerraformResource(
            resource_type="google_firestore_database",
            resource_name=name,
            properties={
                "name": name,
                "location_id": node.get("location", "us-central"),
                "type": node.get("type", "FIRESTORE_NATIVE"),
                "project": "${var.project_id}",
                "concurrency_mode": node.get("concurrency", "OPTIMISTIC"),
                "app_engine_integration_mode": "DISABLED",
            },
        )
        resources.append(database)

        # Indexes
        for idx, collection in enumerate(node.get("collections", [])):
            index = TerraformResource(
                resource_type="google_firestore_index",
                resource_name=f"{name}_index_{idx}",
                properties={
                    "project": "${var.project_id}",
                    "database": f"google_firestore_database.{name}.name",
                    "collection": collection,
                    "fields": [{"field_path": "__name__", "order": "ASCENDING"}],
                },
            )
            resources.append(index)

        return resources

    def _create_storage_resources(self, node: dict) -> list[TerraformResource]:
        """Create Cloud Storage resources.

        Args:
            node: Node data

        Returns:
            List of Cloud Storage resources
        """
        resources = []
        name = node.get("name", "unnamed")

        # Storage bucket
        bucket = TerraformResource(
            resource_type="google_storage_bucket",
            resource_name=name,
            properties={
                "name": f"${{var.project_id}}-{name}",
                "location": node.get("location", "US"),
                "project": "${var.project_id}",
                "storage_class": node.get("storage_class", "STANDARD"),
                "uniform_bucket_level_access": True,
                "versioning": {"enabled": node.get("versioning", False)},
                "lifecycle_rule": node.get("lifecycle_rules", []),
            },
        )
        resources.append(bucket)

        # IAM binding
        iam = TerraformResource(
            resource_type="google_storage_bucket_iam_member",
            resource_name=f"{name}_viewer",
            properties={
                "bucket": f"google_storage_bucket.{name}.name",
                "role": "roles/storage.objectViewer",
                "member": "allUsers",
            },
        )
        resources.append(iam)

        return resources

    def _create_cloud_tasks_resources(self, node: dict) -> list[TerraformResource]:
        """Create Cloud Tasks resources.

        Args:
            node: Node data

        Returns:
            List of Cloud Tasks resources
        """
        resources = []
        name = node.get("name", "unnamed")

        # Tasks queue
        queue = TerraformResource(
            resource_type="google_cloud_tasks_queue",
            resource_name=name,
            properties={
                "name": name,
                "location": "${var.region}",
                "project": "${var.project_id}",
                "rate_limits": {
                    "max_dispatches_per_second": node.get("max_dispatches", 100),
                    "max_concurrent_dispatches": node.get("max_concurrent", 1000),
                },
                "retry_config": {
                    "max_attempts": node.get("max_retries", 10),
                    "max_retry_duration": node.get("retry_duration", "3600s"),
                },
            },
        )
        resources.append(queue)

        return resources

    def _create_cloud_sql_resources(self, node: dict) -> list[TerraformResource]:
        """Create Cloud SQL resources.

        Args:
            node: Node data

        Returns:
            List of Cloud SQL resources
        """
        resources = []
        name = node.get("name", "unnamed")

        # SQL instance
        instance = TerraformResource(
            resource_type="google_sql_database_instance",
            resource_name=name,
            properties={
                "name": name,
                "database_version": node.get("version", "MYSQL_8_0"),
                "project": "${var.project_id}",
                "region": "${var.region}",
                "settings": {
                    "tier": node.get("tier", "db-f1-micro"),
                    "disk_size": node.get("disk_size", 10),
                    "disk_type": node.get("disk_type", "PD_SSD"),
                    "ip_configuration": {
                        "ipv4_enabled": True,
                        "private_network": node.get("network", ""),
                        "authorized_networks": [],
                    },
                },
            },
        )
        resources.append(instance)

        # Database
        database = TerraformResource(
            resource_type="google_sql_database",
            resource_name=f"{name}_db",
            properties={
                "name": f"{name}_database",
                "instance": f"google_sql_database_instance.{name}.name",
                "project": "${var.project_id}",
            },
        )
        resources.append(database)

        # User
        user = TerraformResource(
            resource_type="google_sql_user",
            resource_name=f"{name}_user",
            properties={
                "name": node.get("username", "appuser"),
                "instance": f"google_sql_database_instance.{name}.name",
                "password": "${random_password.sql_password.result}",
                "project": "${var.project_id}",
            },
        )
        resources.append(user)

        return resources
