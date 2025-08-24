"""
GCP Service
Google Cloud Platform service integration following CRAFT methodology.
"""

import json
import subprocess
import asyncio
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging

from .auth_service import AuthService
from .cache_service import CacheService
from .error_service import ErrorService, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


@dataclass
class GCPResource:
    """GCP resource representation."""

    name: str
    type: str
    zone: Optional[str] = None
    region: Optional[str] = None
    status: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    created_at: Optional[str] = None


class GCPService:
    """
    Google Cloud Platform service integration implementing CRAFT principles.

    Create: Robust GCP integration framework
    Refactor: Optimized for GCP best practices
    Authenticate: Secure GCP authentication
    Function: Reliable GCP operations
    Test: Comprehensive GCP validation
    """

    def __init__(
        self,
        config_service,
        auth_service: AuthService,
        cache_service: CacheService,
        error_service: ErrorService,
    ):
        self.config_service = config_service
        self.auth_service = auth_service
        self.cache_service = cache_service
        self.error_service = error_service

        self.gcp_config = config_service.get_gcp_config()
        self.project_id = self.gcp_config.get("project_id")
        self.region = self.gcp_config.get("region", "us-central1")
        self.zone = self.gcp_config.get("zone", "us-central1-a")
        self.labels = self.gcp_config.get("labels", {})

    def execute_gcloud_command(
        self,
        cmd: List[str],
        timeout: int = 120,
        use_cache: bool = True,
        cache_ttl: int = 300,
    ) -> Dict[str, Any]:
        """Execute gcloud command with authentication and error handling."""
        try:
            # Add authentication
            authenticated_cmd = self.auth_service.get_authenticated_gcloud_cmd(
                cmd, self.project_id
            )

            # Check cache first if enabled
            if use_cache:
                cache_key = f"gcloud:{':'.join(authenticated_cmd)}"
                cached_result = self.cache_service.get(cache_key)
                if cached_result is not None:
                    return cached_result

            # Execute command
            result = subprocess.run(
                authenticated_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout,
            )

            # Parse JSON output if applicable
            output_data = {}
            if result.stdout:
                try:
                    output_data = json.loads(result.stdout)
                except json.JSONDecodeError:
                    output_data = {"output": result.stdout.strip()}

            response = {
                "success": True,
                "data": output_data,
                "stderr": result.stderr.strip() if result.stderr else None,
            }

            # Cache successful results
            if use_cache:
                self.cache_service.set(
                    cache_key, response, cache_ttl, tags=["gcloud", "gcp"]
                )

            return response

        except subprocess.CalledProcessError as e:
            error = self.error_service.create_error(
                message=f"GCloud command failed: {e.stderr or e.stdout or str(e)}",
                category=ErrorCategory.SERVICE,
                severity=ErrorSeverity.HIGH,
                code="GCLOUD_COMMAND_FAILED",
                details={
                    "command": authenticated_cmd,
                    "return_code": e.returncode,
                    "stdout": e.stdout,
                    "stderr": e.stderr,
                },
            )

            return {"success": False, "error": error, "data": None}

        except Exception as e:
            error = self.error_service.handle_exception(
                e, {"command": cmd, "project_id": self.project_id}
            )

            return {"success": False, "error": error, "data": None}

    # Compute Engine Operations

    def list_instances(
        self, zone: Optional[str] = None, filter_expr: Optional[str] = None
    ) -> Dict[str, Any]:
        """List Compute Engine instances."""
        cmd = ["gcloud", "compute", "instances", "list", "--format=json"]

        if zone:
            cmd.extend([f"--zones={zone}"])

        if filter_expr:
            cmd.extend([f"--filter={filter_expr}"])
        else:
            # Default filter for Genesis-managed instances
            cmd.extend(["--filter=labels.genesis-managed=true"])

        return self.execute_gcloud_command(cmd, use_cache=True, cache_ttl=60)

    def create_instance_template(
        self, name: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create instance template."""
        cmd = [
            "gcloud",
            "compute",
            "instance-templates",
            "create",
            name,
            f"--machine-type={config.get('machine_type', 'e2-standard-2')}",
            f"--image-family={config.get('image_family', 'ubuntu-2004-lts')}",
            f"--image-project={config.get('image_project', 'ubuntu-os-cloud')}",
            f"--boot-disk-size={config.get('disk_size_gb', 50)}",
            "--boot-disk-type=pd-standard",
            "--boot-disk-device-name=root",
            "--subnet=default",
            "--no-address" if config.get("no_external_ip", False) else "",
        ]

        # Add labels
        labels = {**self.labels, **config.get("labels", {})}
        if labels:
            label_str = ",".join([f"{k}={v}" for k, v in labels.items()])
            cmd.extend([f"--labels={label_str}"])

        # Add metadata for startup script
        if config.get("startup_script"):
            cmd.extend(
                [f"--metadata-from-file=startup-script={config['startup_script']}"]
            )

        # Add service account
        if config.get("service_account"):
            cmd.extend([f"--service-account={config['service_account']}"])

        # Add scopes
        scopes = config.get(
            "scopes", ["https://www.googleapis.com/auth/cloud-platform"]
        )
        cmd.extend([f"--scopes={','.join(scopes)}"])

        # Add preemptible if specified
        if config.get("preemptible", False):
            cmd.append("--preemptible")

        # Remove empty strings from command
        cmd = [arg for arg in cmd if arg]

        return self.execute_gcloud_command(cmd, use_cache=False)

    def create_instance_group(
        self, name: str, template: str, size: int, zone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create managed instance group."""
        zone = zone or self.zone

        cmd = [
            "gcloud",
            "compute",
            "instance-groups",
            "managed",
            "create",
            name,
            f"--template={template}",
            f"--size={size}",
            f"--zone={zone}",
        ]

        return self.execute_gcloud_command(cmd, use_cache=False)

    def scale_instance_group(
        self, name: str, size: int, zone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Scale managed instance group."""
        zone = zone or self.zone

        cmd = [
            "gcloud",
            "compute",
            "instance-groups",
            "managed",
            "resize",
            name,
            f"--size={size}",
            f"--zone={zone}",
        ]

        return self.execute_gcloud_command(cmd, use_cache=False)

    def set_autoscaling(
        self,
        name: str,
        min_replicas: int,
        max_replicas: int,
        zone: Optional[str] = None,
        cpu_target: float = 0.75,
    ) -> Dict[str, Any]:
        """Configure autoscaling for instance group."""
        zone = zone or self.zone

        cmd = [
            "gcloud",
            "compute",
            "instance-groups",
            "managed",
            "set-autoscaling",
            name,
            f"--min-num-replicas={min_replicas}",
            f"--max-num-replicas={max_replicas}",
            f"--target-cpu-utilization={cpu_target}",
            f"--zone={zone}",
        ]

        return self.execute_gcloud_command(cmd, use_cache=False)

    # GKE Operations

    def list_clusters(self, region: Optional[str] = None) -> Dict[str, Any]:
        """List GKE clusters."""
        cmd = ["gcloud", "container", "clusters", "list", "--format=json"]

        if region:
            cmd.extend([f"--region={region}"])

        return self.execute_gcloud_command(cmd, use_cache=True, cache_ttl=60)

    def create_cluster(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create GKE cluster."""
        region = config.get("region", self.region)

        if config.get("autopilot", True):
            cmd = [
                "gcloud",
                "container",
                "clusters",
                "create-auto",
                name,
                f"--region={region}",
                "--release-channel=regular",
            ]
        else:
            cmd = [
                "gcloud",
                "container",
                "clusters",
                "create",
                name,
                f"--region={region}",
                f"--num-nodes={config.get('num_nodes', 3)}",
                f"--machine-type={config.get('machine_type', 'e2-medium')}",
                "--enable-autoscaling",
                f"--min-nodes={config.get('min_nodes', 1)}",
                f"--max-nodes={config.get('max_nodes', 10)}",
                "--enable-autorepair",
                "--enable-autoupgrade",
            ]

        # Add labels
        labels = {**self.labels, **config.get("labels", {})}
        if labels:
            label_str = ",".join([f"{k}={v}" for k, v in labels.items()])
            cmd.extend([f"--labels={label_str}"])

        return self.execute_gcloud_command(cmd, use_cache=False, timeout=600)

    def get_cluster_credentials(
        self, cluster_name: str, region: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get cluster credentials."""
        region = region or self.region

        cmd = [
            "gcloud",
            "container",
            "clusters",
            "get-credentials",
            cluster_name,
            f"--region={region}",
        ]

        return self.execute_gcloud_command(cmd, use_cache=False)

    # Resource Management

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage summary."""
        cache_key = "resource_usage"
        cached_usage = self.cache_service.get(cache_key)

        if cached_usage:
            return cached_usage

        usage = {}

        # Get compute instances
        instances_result = self.list_instances()
        if instances_result["success"]:
            instances = instances_result["data"]
            usage["compute_instances"] = {
                "total": len(instances) if isinstance(instances, list) else 0,
                "running": (
                    sum(1 for i in instances if i.get("status") == "RUNNING")
                    if isinstance(instances, list)
                    else 0
                ),
            }

        # Get GKE clusters
        clusters_result = self.list_clusters()
        if clusters_result["success"]:
            clusters = clusters_result["data"]
            usage["gke_clusters"] = {
                "total": len(clusters) if isinstance(clusters, list) else 0,
                "running": (
                    sum(1 for c in clusters if c.get("status") == "RUNNING")
                    if isinstance(clusters, list)
                    else 0
                ),
            }

        # Cache for 5 minutes
        self.cache_service.set(cache_key, usage, ttl=300, tags=["resource_usage"])

        return usage

    def get_project_info(self) -> Dict[str, Any]:
        """Get project information."""
        cmd = ["gcloud", "projects", "describe", self.project_id, "--format=json"]

        return self.execute_gcloud_command(cmd, use_cache=True, cache_ttl=3600)

    def validate_permissions(
        self, permissions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Validate current permissions."""
        if not permissions:
            permissions = [
                "compute.instances.list",
                "compute.instanceTemplates.create",
                "compute.instanceGroups.create",
                "container.clusters.list",
                "container.clusters.create",
            ]

        # Use auth service to validate permissions
        return {
            "success": True,
            "data": self.auth_service.validate_permissions(
                self.project_id, permissions
            ),
        }

    # Utility Methods

    def parse_resource_name(self, resource_url: str) -> Dict[str, str]:
        """Parse GCP resource URL into components."""
        parts = resource_url.split("/")

        resource_info = {}

        for i, part in enumerate(parts):
            if part == "projects":
                resource_info["project"] = parts[i + 1]
            elif part == "zones":
                resource_info["zone"] = parts[i + 1]
            elif part == "regions":
                resource_info["region"] = parts[i + 1]
            elif part in [
                "instances",
                "instanceTemplates",
                "instanceGroups",
                "clusters",
            ]:
                resource_info["type"] = part
                if i + 1 < len(parts):
                    resource_info["name"] = parts[i + 1]

        return resource_info

    def build_labels(
        self, additional_labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Build standard labels for resources."""
        labels = {
            **self.labels,
            "created-by": "genesis-cli",
            "created-at": datetime.now().strftime("%Y%m%d-%H%M%S"),
        }

        if additional_labels:
            labels.update(additional_labels)

        return labels

    def wait_for_operation(
        self,
        operation_name: str,
        operation_type: str = "compute",
        zone: Optional[str] = None,
        region: Optional[str] = None,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """Wait for GCP operation to complete."""
        if operation_type == "compute":
            if zone:
                cmd = [
                    "gcloud",
                    "compute",
                    "operations",
                    "wait",
                    operation_name,
                    f"--zone={zone}",
                ]
            elif region:
                cmd = [
                    "gcloud",
                    "compute",
                    "operations",
                    "wait",
                    operation_name,
                    f"--region={region}",
                ]
            else:
                cmd = ["gcloud", "compute", "operations", "wait", operation_name]
        elif operation_type == "container":
            region = region or self.region
            cmd = [
                "gcloud",
                "container",
                "operations",
                "wait",
                operation_name,
                f"--region={region}",
            ]
        else:
            raise ValueError(f"Unsupported operation type: {operation_type}")

        return self.execute_gcloud_command(cmd, use_cache=False, timeout=timeout)
