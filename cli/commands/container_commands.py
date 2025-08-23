"""
Container Orchestration Commands - Issue #31
CLI commands for GKE cluster and container management following PIPES methodology
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContainerCommands:
    """Container orchestration commands implementation."""

    def __init__(self, cli):
        self.cli = cli
        self.manifests_dir = (
            Path(self.cli.genesis_root) / "modules/container-orchestration/manifests"
        )
        self.templates_dir = (
            Path(self.cli.genesis_root) / "modules/container-orchestration/templates"
        )

    def execute(self, args, config: Dict[str, Any]) -> Any:
        """Execute container command based on action."""
        action = args.container_action

        if action == "create-cluster":
            return self.create_cluster(args, config)
        elif action == "list-clusters":
            return self.list_clusters(args, config)
        elif action == "delete-cluster":
            return self.delete_cluster(args, config)
        elif action == "deploy":
            return self.deploy_service(args, config)
        elif action == "scale":
            return self.scale_deployment(args, config)
        elif action == "list-deployments":
            return self.list_deployments(args, config)
        elif action == "list-services":
            return self.list_services(args, config)
        elif action == "list-pods":
            return self.list_pods(args, config)
        elif action == "logs":
            return self.get_logs(args, config)
        elif action == "registry":
            return self.registry_operations(args, config)
        else:
            raise ValueError(f"Unknown container action: {action}")

    def create_cluster(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create GKE cluster."""
        logger.info(f"Creating GKE cluster: {args.cluster_name}")

        if args.dry_run:
            return {
                "action": "create-cluster",
                "cluster_name": args.cluster_name,
                "autopilot": args.autopilot,
                "region": args.region,
                "node_pools": args.node_pools,
                "status": "dry-run",
            }

        # Generate cluster configuration
        cluster_config = self._generate_cluster_config(args, config)

        # Create cluster via Terraform or gcloud
        result = self._create_gke_cluster(cluster_config)

        return {
            "action": "create-cluster",
            "cluster_name": args.cluster_name,
            "configuration": cluster_config,
            "result": result,
            "status": "created",
        }

    def list_clusters(self, args, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List GKE clusters."""
        logger.info("Listing GKE clusters")

        try:
            cmd = [
                "gcloud",
                "container",
                "clusters",
                "list",
                f"--project={self.cli.project_id}",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            clusters = json.loads(result.stdout)

            # Format cluster information
            formatted_clusters = []
            for cluster in clusters:
                formatted_clusters.append(
                    {
                        "name": cluster.get("name", ""),
                        "location": cluster.get("location", ""),
                        "status": cluster.get("status", ""),
                        "node_count": cluster.get("currentNodeCount", 0),
                        "master_version": cluster.get("currentMasterVersion", ""),
                        "endpoint": cluster.get("endpoint", ""),
                        "autopilot": cluster.get("autopilot", {}).get("enabled", False),
                        "created": cluster.get("createTime", ""),
                    }
                )

            return formatted_clusters

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list clusters: {e}")
            return []

    def delete_cluster(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Delete GKE cluster."""
        logger.info(f"Deleting GKE cluster: {args.cluster_name}")

        if args.dry_run:
            return {
                "action": "delete-cluster",
                "cluster_name": args.cluster_name,
                "status": "dry-run",
            }

        try:
            cmd = [
                "gcloud",
                "container",
                "clusters",
                "delete",
                args.cluster_name,
                f"--project={self.cli.project_id}",
                "--quiet",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "action": "delete-cluster",
                "cluster_name": args.cluster_name,
                "status": "deleted",
                "output": result.stdout,
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete cluster: {e}")
            return {
                "action": "delete-cluster",
                "cluster_name": args.cluster_name,
                "status": "failed",
                "error": str(e),
            }

    def deploy_service(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy container service."""
        logger.info(f"Deploying service: {args.service}")

        if args.dry_run:
            return {
                "action": "deploy",
                "service": args.service,
                "version": args.version,
                "replicas": args.replicas,
                "namespace": args.namespace,
                "status": "dry-run",
            }

        # Load appropriate manifest
        manifest_path = self._get_service_manifest(args.service)
        if not manifest_path.exists():
            raise ValueError(f"Service manifest not found for: {args.service}")

        # Process manifest template
        processed_manifest = self._process_manifest_template(
            manifest_path, args, config
        )

        # Apply manifest to cluster
        result = self._apply_kubernetes_manifest(processed_manifest, args.namespace)

        return {
            "action": "deploy",
            "service": args.service,
            "version": args.version or "latest",
            "namespace": args.namespace or "default",
            "result": result,
            "status": "deployed",
        }

    def scale_deployment(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Scale container deployment."""
        logger.info(f"Scaling deployment: {args.deployment}")

        if args.dry_run:
            return {
                "action": "scale",
                "deployment": args.deployment,
                "replicas": args.replicas,
                "namespace": args.namespace,
                "status": "dry-run",
            }

        try:
            cmd = [
                "kubectl",
                "scale",
                "deployment",
                args.deployment,
                f"--replicas={args.replicas}",
            ]

            if args.namespace:
                cmd.extend(["-n", args.namespace])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "action": "scale",
                "deployment": args.deployment,
                "replicas": args.replicas,
                "namespace": args.namespace or "default",
                "status": "scaled",
                "output": result.stdout.strip(),
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to scale deployment: {e}")
            return {
                "action": "scale",
                "deployment": args.deployment,
                "status": "failed",
                "error": str(e),
            }

    def list_deployments(self, args, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List Kubernetes deployments."""
        logger.info("Listing deployments")

        try:
            cmd = ["kubectl", "get", "deployments", "-o", "json"]
            if hasattr(args, "namespace") and args.namespace:
                cmd.extend(["-n", args.namespace])
            else:
                cmd.append("--all-namespaces")

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            deployments_data = json.loads(result.stdout)

            # Format deployment information
            formatted_deployments = []
            for deployment in deployments_data.get("items", []):
                metadata = deployment.get("metadata", {})
                spec = deployment.get("spec", {})
                status = deployment.get("status", {})

                formatted_deployments.append(
                    {
                        "name": metadata.get("name", ""),
                        "namespace": metadata.get("namespace", ""),
                        "replicas": {
                            "desired": spec.get("replicas", 0),
                            "ready": status.get("readyReplicas", 0),
                            "available": status.get("availableReplicas", 0),
                            "updated": status.get("updatedReplicas", 0),
                        },
                        "images": self._extract_images(spec),
                        "age": self._calculate_age(
                            metadata.get("creationTimestamp", "")
                        ),
                        "labels": metadata.get("labels", {}),
                        "annotations": metadata.get("annotations", {}),
                    }
                )

            return formatted_deployments

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list deployments: {e}")
            return []

    def list_services(self, args, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List Kubernetes services."""
        logger.info("Listing services")

        try:
            cmd = ["kubectl", "get", "services", "-o", "json"]
            if hasattr(args, "namespace") and args.namespace:
                cmd.extend(["-n", args.namespace])
            else:
                cmd.append("--all-namespaces")

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            services_data = json.loads(result.stdout)

            # Format service information
            formatted_services = []
            for service in services_data.get("items", []):
                metadata = service.get("metadata", {})
                spec = service.get("spec", {})
                status = service.get("status", {})

                formatted_services.append(
                    {
                        "name": metadata.get("name", ""),
                        "namespace": metadata.get("namespace", ""),
                        "type": spec.get("type", ""),
                        "cluster_ip": spec.get("clusterIP", ""),
                        "external_ip": self._get_external_ip_from_service(spec, status),
                        "ports": spec.get("ports", []),
                        "selector": spec.get("selector", {}),
                        "age": self._calculate_age(
                            metadata.get("creationTimestamp", "")
                        ),
                        "labels": metadata.get("labels", {}),
                    }
                )

            return formatted_services

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list services: {e}")
            return []

    def list_pods(self, args, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List Kubernetes pods."""
        logger.info("Listing pods")

        try:
            cmd = ["kubectl", "get", "pods", "-o", "json"]
            if hasattr(args, "namespace") and args.namespace:
                cmd.extend(["-n", args.namespace])
            else:
                cmd.append("--all-namespaces")

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            pods_data = json.loads(result.stdout)

            # Format pod information
            formatted_pods = []
            for pod in pods_data.get("items", []):
                metadata = pod.get("metadata", {})
                spec = pod.get("spec", {})
                status = pod.get("status", {})

                formatted_pods.append(
                    {
                        "name": metadata.get("name", ""),
                        "namespace": metadata.get("namespace", ""),
                        "status": status.get("phase", ""),
                        "ready": self._get_ready_status(status),
                        "restarts": self._count_restarts(status),
                        "node": spec.get("nodeName", ""),
                        "ip": status.get("podIP", ""),
                        "age": self._calculate_age(
                            metadata.get("creationTimestamp", "")
                        ),
                        "labels": metadata.get("labels", {}),
                        "containers": [
                            c.get("name", "") for c in spec.get("containers", [])
                        ],
                    }
                )

            return formatted_pods

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list pods: {e}")
            return []

    def get_logs(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get container logs."""
        logger.info("Getting container logs")

        try:
            cmd = ["kubectl", "logs"]

            if args.service:
                # Get logs from service (first pod)
                cmd.extend(["-l", f"app={args.service}"])
            elif args.pod:
                cmd.append(args.pod)
            else:
                raise ValueError("Must specify either --service or --pod")

            if hasattr(args, "namespace") and args.namespace:
                cmd.extend(["-n", args.namespace])

            if args.follow:
                cmd.append("-f")

            if args.lines:
                cmd.extend(["--tail", str(args.lines)])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "action": "logs",
                "service": args.service,
                "pod": args.pod,
                "namespace": getattr(args, "namespace", "default"),
                "logs": result.stdout,
                "status": "success",
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get logs: {e}")
            return {"action": "logs", "status": "failed", "error": str(e)}

    def registry_operations(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Handle container registry operations."""
        registry_action = args.registry_action

        if registry_action == "list-repositories":
            return self.list_repositories(args, config)
        elif registry_action == "push":
            return self.push_image(args, config)
        elif registry_action == "pull":
            return self.pull_image(args, config)
        else:
            raise ValueError(f"Unknown registry action: {registry_action}")

    def list_repositories(self, args, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List container registry repositories."""
        logger.info("Listing container repositories")

        try:
            cmd = [
                "gcloud",
                "artifacts",
                "repositories",
                "list",
                f"--project={self.cli.project_id}",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            repositories = json.loads(result.stdout)

            # Format repository information
            formatted_repos = []
            for repo in repositories:
                formatted_repos.append(
                    {
                        "name": repo.get("name", "").split("/")[-1],
                        "format": repo.get("format", ""),
                        "location": (
                            repo.get("name", "").split("/")[3]
                            if "/" in repo.get("name", "")
                            else ""
                        ),
                        "description": repo.get("description", ""),
                        "created": repo.get("createTime", ""),
                        "size_bytes": repo.get("sizeBytes", 0),
                        "labels": repo.get("labels", {}),
                    }
                )

            return formatted_repos

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list repositories: {e}")
            return []

    def push_image(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Push container image to registry."""
        logger.info(f"Pushing image: {args.image}")

        if args.dry_run:
            return {
                "action": "push",
                "image": args.image,
                "repository": args.repository,
                "status": "dry-run",
            }

        try:
            # Tag image for repository if specified
            if args.repository:
                target_image = f"{args.repository}/{args.image}"
                tag_cmd = ["docker", "tag", args.image, target_image]
                subprocess.run(tag_cmd, check=True)
                push_image = target_image
            else:
                push_image = args.image

            # Push image
            push_cmd = ["docker", "push", push_image]
            result = subprocess.run(
                push_cmd, capture_output=True, text=True, check=True
            )

            return {
                "action": "push",
                "image": args.image,
                "target": push_image,
                "status": "pushed",
                "output": result.stdout,
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to push image: {e}")
            return {
                "action": "push",
                "image": args.image,
                "status": "failed",
                "error": str(e),
            }

    def pull_image(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Pull container image from registry."""
        logger.info(f"Pulling image: {args.image}")

        if args.dry_run:
            return {"action": "pull", "image": args.image, "status": "dry-run"}

        try:
            cmd = ["docker", "pull", args.image]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "action": "pull",
                "image": args.image,
                "status": "pulled",
                "output": result.stdout,
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to pull image: {e}")
            return {
                "action": "pull",
                "image": args.image,
                "status": "failed",
                "error": str(e),
            }

    # Helper methods

    def _generate_cluster_config(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate cluster configuration from arguments."""
        cluster_config = {
            "name": args.cluster_name,
            "autopilot": args.autopilot or False,
            "region": args.region or config.get("default_region", "us-central1"),
            "node_pools": [],
        }

        if not args.autopilot and args.node_pools:
            for pool_config in args.node_pools:
                # Parse node pool configuration
                cluster_config["node_pools"].append(
                    {
                        "name": pool_config,
                        "machine_type": "e2-medium",
                        "initial_node_count": 1,
                    }
                )

        return cluster_config

    def _create_gke_cluster(self, cluster_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create GKE cluster via gcloud."""
        try:
            cmd = [
                "gcloud",
                "container",
                "clusters",
                "create",
                cluster_config["name"],
                f"--project={self.cli.project_id}",
                f'--region={cluster_config["region"]}',
            ]

            if cluster_config["autopilot"]:
                cmd.append("--enable-autopilot")
            else:
                cmd.extend(
                    [
                        "--num-nodes=1",
                        "--enable-autoscaling",
                        "--min-nodes=0",
                        "--max-nodes=10",
                    ]
                )

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "status": "success",
                "output": result.stdout,
                "cluster_name": cluster_config["name"],
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create cluster: {e}")
            return {"status": "failed", "error": str(e)}

    def _get_service_manifest(self, service_name: str) -> Path:
        """Get manifest path for service."""
        manifest_files = {
            "agent-cage": "agent-cage-deployment.yaml",
            "claude-talk": "claude-talk-deployment.yaml",
        }

        manifest_file = manifest_files.get(
            service_name, f"{service_name}-deployment.yaml"
        )
        return self.manifests_dir / manifest_file

    def _process_manifest_template(
        self, manifest_path: Path, args, config: Dict[str, Any]
    ) -> str:
        """Process manifest template with variables."""
        with open(manifest_path, "r") as f:
            template = f.read()

        # Template variables
        variables = {
            "ENVIRONMENT": self.cli.environment,
            "PROJECT_ID": self.cli.project_id,
            "CONTAINER_REGISTRY": config.get(
                "container_registry", "us-central1-docker.pkg.dev"
            ),
            f"{args.service.upper().replace('-', '_')}_VERSION": args.version
            or "latest",
            f"{args.service.upper().replace('-', '_')}_REPLICAS": str(
                args.replicas or 1
            ),
            "LOG_LEVEL": config.get("log_level", "INFO"),
            "STORAGE_CLASS": config.get("storage_class", "standard"),
        }

        # Replace template variables
        processed = template
        for key, value in variables.items():
            processed = processed.replace(f"${{{key}}}", value)

        return processed

    def _apply_kubernetes_manifest(
        self, manifest_content: str, namespace: Optional[str]
    ) -> Dict[str, Any]:
        """Apply Kubernetes manifest."""
        try:
            # Write manifest to temp file
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                f.write(manifest_content)
                temp_path = f.name

            cmd = ["kubectl", "apply", "-f", temp_path]
            if namespace:
                cmd.extend(["-n", namespace])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Clean up temp file
            Path(temp_path).unlink()

            return {
                "status": "success",
                "output": result.stdout,
                "applied_resources": result.stdout.split("\n"),
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply manifest: {e}")
            return {"status": "failed", "error": str(e)}

    def _extract_images(self, spec: Dict[str, Any]) -> List[str]:
        """Extract container images from deployment spec."""
        images = []
        containers = spec.get("template", {}).get("spec", {}).get("containers", [])
        for container in containers:
            if "image" in container:
                images.append(container["image"])
        return images

    def _get_external_ip_from_service(
        self, spec: Dict[str, Any], status: Dict[str, Any]
    ) -> str:
        """Get external IP from service."""
        if spec.get("type") == "LoadBalancer":
            ingress = status.get("loadBalancer", {}).get("ingress", [])
            if ingress:
                return ingress[0].get("ip", "pending")
        return "none"

    def _get_ready_status(self, status: Dict[str, Any]) -> str:
        """Get pod ready status."""
        conditions = status.get("conditions", [])
        ready_condition = next(
            (c for c in conditions if c.get("type") == "Ready"), None
        )
        if ready_condition:
            return "1/1" if ready_condition.get("status") == "True" else "0/1"
        return "unknown"

    def _count_restarts(self, status: Dict[str, Any]) -> int:
        """Count container restarts."""
        container_statuses = status.get("containerStatuses", [])
        return sum(cs.get("restartCount", 0) for cs in container_statuses)

    def _calculate_age(self, created_timestamp: str) -> str:
        """Calculate age from creation timestamp."""
        if not created_timestamp:
            return "unknown"

        try:
            from datetime import datetime, timezone

            created = datetime.fromisoformat(created_timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age = now - created

            days = age.days
            hours = age.seconds // 3600
            minutes = (age.seconds // 60) % 60

            if days > 0:
                return f"{days}d{hours}h"
            elif hours > 0:
                return f"{hours}h{minutes}m"
            else:
                return f"{minutes}m"

        except Exception:
            return "unknown"
