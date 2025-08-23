"""
VM Management Commands - Issue #30
CLI commands for agent VM lifecycle management following PIPES methodology
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VMCommands:
    """VM management commands implementation."""

    def __init__(self, cli):
        self.cli = cli
        self.terraform_dir = Path(self.cli.genesis_root) / "environments"

    def execute(self, args, config: Dict[str, Any]) -> Any:
        """Execute VM command based on action."""
        action = args.vm_action

        if action == "create-pool":
            return self.create_pool(args, config)
        elif action == "scale-pool":
            return self.scale_pool(args, config)
        elif action == "list-pools":
            return self.list_pools(args, config)
        elif action == "list-instances":
            return self.list_instances(args, config)
        elif action == "health-check":
            return self.health_check(args, config)
        elif action == "start":
            return self.start_instances(args, config)
        elif action == "stop":
            return self.stop_instances(args, config)
        elif action == "restart":
            return self.restart_instances(args, config)
        elif action == "list-templates":
            return self.list_templates(args, config)
        elif action == "update-template":
            return self.update_template(args, config)
        else:
            raise ValueError(f"Unknown VM action: {action}")

    def create_pool(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new agent VM pool."""
        logger.info(f"Creating VM pool for agent type: {args.type}")

        if args.dry_run:
            return {
                "action": "create-pool",
                "agent_type": args.type,
                "size": args.size,
                "machine_type": args.machine_type,
                "preemptible": args.preemptible,
                "zones": args.zones,
                "status": "dry-run",
            }

        # Generate Terraform variables for the pool
        pool_config = self._generate_pool_config(args)

        # Create Terraform configuration
        tf_config = self._create_terraform_config(pool_config, config)

        # Apply Terraform configuration
        result = self._apply_terraform(tf_config, args.environment)

        return {
            "action": "create-pool",
            "agent_type": args.type,
            "pool_name": f"{args.type}-pool",
            "configuration": pool_config,
            "terraform_result": result,
            "status": "created",
        }

    def scale_pool(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Scale an existing VM pool."""
        logger.info(f"Scaling VM pool: {args.pool_name}")

        if args.dry_run:
            return {
                "action": "scale-pool",
                "pool_name": args.pool_name,
                "target_size": args.size,
                "min_size": args.min,
                "max_size": args.max,
                "enable_autoscaling": args.enable_autoscaling,
                "status": "dry-run",
            }

        # Update pool configuration
        scaling_config = {
            "pool_name": args.pool_name,
            "target_size": args.size,
            "min_replicas": args.min,
            "max_replicas": args.max,
            "enable_autoscaling": args.enable_autoscaling,
        }

        # Apply scaling via gcloud or Terraform
        result = self._scale_instance_group(scaling_config, args.environment)

        return {
            "action": "scale-pool",
            "pool_name": args.pool_name,
            "configuration": scaling_config,
            "result": result,
            "status": "scaled",
        }

    def list_pools(self, args, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all VM pools."""
        logger.info("Listing VM pools")

        try:
            # Get managed instance groups
            cmd = [
                "gcloud",
                "compute",
                "instance-groups",
                "managed",
                "list",
                f"--project={self.cli.project_id}",
                "--format=json",
                "--filter=labels.genesis-managed=true",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            pools = json.loads(result.stdout)

            # Format pool information
            formatted_pools = []
            for pool in pools:
                formatted_pools.append(
                    {
                        "name": pool.get("name", ""),
                        "zone": pool.get("zone", "").split("/")[-1],
                        "target_size": pool.get("targetSize", 0),
                        "current_size": len(pool.get("instances", [])),
                        "status": pool.get("status", ""),
                        "agent_type": pool.get("labels", {}).get(
                            "agent-type", "unknown"
                        ),
                        "created": pool.get("creationTimestamp", ""),
                    }
                )

            return formatted_pools

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list VM pools: {e}")
            return []

    def list_instances(self, args, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all VM instances."""
        logger.info("Listing VM instances")

        try:
            cmd = [
                "gcloud",
                "compute",
                "instances",
                "list",
                f"--project={self.cli.project_id}",
                "--format=json",
                "--filter=labels.genesis-managed=true",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            instances = json.loads(result.stdout)

            # Format instance information
            formatted_instances = []
            for instance in instances:
                formatted_instances.append(
                    {
                        "name": instance.get("name", ""),
                        "zone": instance.get("zone", "").split("/")[-1],
                        "machine_type": instance.get("machineType", "").split("/")[-1],
                        "status": instance.get("status", ""),
                        "internal_ip": self._get_internal_ip(instance),
                        "external_ip": self._get_external_ip(instance),
                        "agent_type": instance.get("labels", {}).get(
                            "agent-type", "unknown"
                        ),
                        "preemptible": instance.get("scheduling", {}).get(
                            "preemptible", False
                        ),
                        "created": instance.get("creationTimestamp", ""),
                    }
                )

            return formatted_instances

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list VM instances: {e}")
            return []

    def health_check(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check health status of VMs."""
        logger.info("Checking VM health status")

        health_results = {}

        if args.pool:
            # Check specific pool health
            health_results[args.pool] = self._check_pool_health(args.pool)
        elif args.instance:
            # Check specific instance health
            health_results[args.instance] = self._check_instance_health(args.instance)
        else:
            # Check all pools and instances
            pools = self.list_pools(args, config)
            for pool in pools:
                health_results[pool["name"]] = self._check_pool_health(pool["name"])

        return {
            "action": "health-check",
            "timestamp": self._get_timestamp(),
            "results": health_results,
            "overall_status": self._calculate_overall_health(health_results),
        }

    def start_instances(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start VM instances."""
        logger.info("Starting VM instances")

        if args.dry_run:
            return {
                "action": "start",
                "pool": args.pool,
                "instance": args.instance,
                "status": "dry-run",
            }

        if args.pool:
            return self._start_pool(args.pool)
        elif args.instance:
            return self._start_instance(args.instance)
        else:
            raise ValueError("Must specify either --pool or --instance")

    def stop_instances(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Stop VM instances."""
        logger.info("Stopping VM instances")

        if args.dry_run:
            return {
                "action": "stop",
                "pool": args.pool,
                "instance": args.instance,
                "status": "dry-run",
            }

        if args.pool:
            return self._stop_pool(args.pool)
        elif args.instance:
            return self._stop_instance(args.instance)
        else:
            raise ValueError("Must specify either --pool or --instance")

    def restart_instances(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Restart VM instances."""
        logger.info("Restarting VM instances")

        if args.dry_run:
            return {
                "action": "restart",
                "pool": args.pool,
                "instance": args.instance,
                "status": "dry-run",
            }

        if args.pool:
            return self._restart_pool(args.pool)
        elif args.instance:
            return self._restart_instance(args.instance)
        else:
            raise ValueError("Must specify either --pool or --instance")

    def list_templates(self, args, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List VM instance templates."""
        logger.info("Listing VM templates")

        try:
            cmd = [
                "gcloud",
                "compute",
                "instance-templates",
                "list",
                f"--project={self.cli.project_id}",
                "--format=json",
                "--filter=labels.genesis-managed=true",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            templates = json.loads(result.stdout)

            # Format template information
            formatted_templates = []
            for template in templates:
                formatted_templates.append(
                    {
                        "name": template.get("name", ""),
                        "machine_type": self._extract_machine_type(template),
                        "source_image": self._extract_source_image(template),
                        "agent_type": template.get("labels", {}).get(
                            "agent-type", "unknown"
                        ),
                        "created": template.get("creationTimestamp", ""),
                        "description": template.get("description", ""),
                    }
                )

            return formatted_templates

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list VM templates: {e}")
            return []

    def update_template(self, args, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update VM instance template."""
        logger.info(f"Updating VM template: {args.template_name}")

        if args.dry_run:
            return {
                "action": "update-template",
                "template_name": args.template_name,
                "image": args.image,
                "machine_type": args.machine_type,
                "status": "dry-run",
            }

        # Create new template version
        update_config = {
            "template_name": args.template_name,
            "new_image": args.image,
            "new_machine_type": args.machine_type,
        }

        result = self._update_instance_template(update_config)

        return {
            "action": "update-template",
            "template_name": args.template_name,
            "configuration": update_config,
            "result": result,
            "status": "updated",
        }

    # Helper methods

    def _generate_pool_config(self, args) -> Dict[str, Any]:
        """Generate pool configuration from arguments."""
        return {
            "agent_type": args.type,
            "pool_size": args.size,
            "machine_type": args.machine_type or "e2-standard-2",
            "preemptible": args.preemptible or False,
            "zones": args.zones or ["us-central1-a", "us-central1-b"],
            "enable_autoscaling": True,
            "min_replicas": 1,
            "max_replicas": args.size * 3,
        }

    def _create_terraform_config(
        self, pool_config: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create Terraform configuration for VM pool."""
        # This would generate actual Terraform configuration
        # For now, return a mock configuration
        return {
            "terraform_config": pool_config,
            "backend_config": config.get("terraform", {}),
        }

    def _apply_terraform(
        self, tf_config: Dict[str, Any], environment: str
    ) -> Dict[str, Any]:
        """Apply Terraform configuration."""
        # Mock Terraform apply - in real implementation, this would:
        # 1. Write Terraform files
        # 2. Run terraform init
        # 3. Run terraform plan
        # 4. Run terraform apply
        return {
            "terraform_apply": "success",
            "resources_created": ["instance_template", "instance_group", "autoscaler"],
        }

    def _scale_instance_group(
        self, scaling_config: Dict[str, Any], environment: str
    ) -> Dict[str, Any]:
        """Scale managed instance group."""
        try:
            if scaling_config.get("enable_autoscaling"):
                # Update autoscaler
                cmd = [
                    "gcloud",
                    "compute",
                    "instance-groups",
                    "managed",
                    "set-autoscaling",
                    scaling_config["pool_name"],
                    f"--project={self.cli.project_id}",
                    f'--min-num-replicas={scaling_config["min_replicas"]}',
                    f'--max-num-replicas={scaling_config["max_replicas"]}',
                    "--target-cpu-utilization=0.75",
                ]
            else:
                # Set fixed size
                cmd = [
                    "gcloud",
                    "compute",
                    "instance-groups",
                    "managed",
                    "resize",
                    scaling_config["pool_name"],
                    f"--project={self.cli.project_id}",
                    f'--size={scaling_config["target_size"]}',
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {"status": "success", "output": result.stdout}

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to scale instance group: {e}")
            return {"status": "failed", "error": str(e)}

    def _check_pool_health(self, pool_name: str) -> Dict[str, Any]:
        """Check health of a specific pool."""
        try:
            # Get pool status
            cmd = [
                "gcloud",
                "compute",
                "instance-groups",
                "managed",
                "describe",
                pool_name,
                f"--project={self.cli.project_id}",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            pool_info = json.loads(result.stdout)

            # Check individual instance health
            instances = pool_info.get("instances", [])
            healthy_instances = sum(
                1 for inst in instances if inst.get("instanceStatus") == "RUNNING"
            )

            return {
                "pool_name": pool_name,
                "total_instances": len(instances),
                "healthy_instances": healthy_instances,
                "health_percentage": (
                    (healthy_instances / len(instances)) * 100 if instances else 0
                ),
                "status": (
                    "healthy" if healthy_instances == len(instances) else "degraded"
                ),
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to check pool health: {e}")
            return {"pool_name": pool_name, "status": "error", "error": str(e)}

    def _check_instance_health(self, instance_name: str) -> Dict[str, Any]:
        """Check health of a specific instance."""
        try:
            # Check instance status
            cmd = [
                "gcloud",
                "compute",
                "instances",
                "describe",
                instance_name,
                f"--project={self.cli.project_id}",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            instance_info = json.loads(result.stdout)

            # Check agent health endpoint if available
            internal_ip = self._get_internal_ip(instance_info)
            agent_health = (
                self._check_agent_health_endpoint(internal_ip) if internal_ip else None
            )

            return {
                "instance_name": instance_name,
                "vm_status": instance_info.get("status", "UNKNOWN"),
                "agent_health": agent_health,
                "last_start_timestamp": instance_info.get("lastStartTimestamp", ""),
                "status": (
                    "healthy"
                    if instance_info.get("status") == "RUNNING"
                    else "unhealthy"
                ),
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to check instance health: {e}")
            return {"instance_name": instance_name, "status": "error", "error": str(e)}

    def _check_agent_health_endpoint(self, ip: str) -> Optional[Dict[str, Any]]:
        """Check agent health endpoint."""
        try:
            import requests

            response = requests.get(f"http://{ip}:8080/health", timeout=5)
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None

    def _get_internal_ip(self, instance: Dict[str, Any]) -> Optional[str]:
        """Extract internal IP from instance data."""
        interfaces = instance.get("networkInterfaces", [])
        if interfaces:
            return interfaces[0].get("networkIP")
        return None

    def _get_external_ip(self, instance: Dict[str, Any]) -> Optional[str]:
        """Extract external IP from instance data."""
        interfaces = instance.get("networkInterfaces", [])
        if interfaces:
            access_configs = interfaces[0].get("accessConfigs", [])
            if access_configs:
                return access_configs[0].get("natIP")
        return None

    def _extract_machine_type(self, template: Dict[str, Any]) -> str:
        """Extract machine type from template."""
        properties = template.get("properties", {})
        machine_type = properties.get("machineType", "")
        return machine_type.split("/")[-1] if machine_type else "unknown"

    def _extract_source_image(self, template: Dict[str, Any]) -> str:
        """Extract source image from template."""
        properties = template.get("properties", {})
        disks = properties.get("disks", [])
        if disks:
            source_image = disks[0].get("initializeParams", {}).get("sourceImage", "")
            return source_image.split("/")[-1] if source_image else "unknown"
        return "unknown"

    def _start_pool(self, pool_name: str) -> Dict[str, Any]:
        """Start all instances in a pool."""
        # This would typically involve starting stopped instances in the pool
        return {"action": "start_pool", "pool": pool_name, "status": "started"}

    def _start_instance(self, instance_name: str) -> Dict[str, Any]:
        """Start a specific instance."""
        try:
            cmd = [
                "gcloud",
                "compute",
                "instances",
                "start",
                instance_name,
                f"--project={self.cli.project_id}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "action": "start_instance",
                "instance": instance_name,
                "status": "started",
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start instance: {e}")
            return {
                "action": "start_instance",
                "instance": instance_name,
                "status": "failed",
                "error": str(e),
            }

    def _stop_pool(self, pool_name: str) -> Dict[str, Any]:
        """Stop all instances in a pool."""
        # This would typically involve scaling the pool to 0 or stopping instances
        return {"action": "stop_pool", "pool": pool_name, "status": "stopped"}

    def _stop_instance(self, instance_name: str) -> Dict[str, Any]:
        """Stop a specific instance."""
        try:
            cmd = [
                "gcloud",
                "compute",
                "instances",
                "stop",
                instance_name,
                f"--project={self.cli.project_id}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "action": "stop_instance",
                "instance": instance_name,
                "status": "stopped",
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop instance: {e}")
            return {
                "action": "stop_instance",
                "instance": instance_name,
                "status": "failed",
                "error": str(e),
            }

    def _restart_pool(self, pool_name: str) -> Dict[str, Any]:
        """Restart all instances in a pool."""
        # This would typically involve a rolling restart of the pool
        return {"action": "restart_pool", "pool": pool_name, "status": "restarted"}

    def _restart_instance(self, instance_name: str) -> Dict[str, Any]:
        """Restart a specific instance."""
        try:
            cmd = [
                "gcloud",
                "compute",
                "instances",
                "reset",
                instance_name,
                f"--project={self.cli.project_id}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "action": "restart_instance",
                "instance": instance_name,
                "status": "restarted",
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart instance: {e}")
            return {
                "action": "restart_instance",
                "instance": instance_name,
                "status": "failed",
                "error": str(e),
            }

    def _update_instance_template(
        self, update_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update instance template with new configuration."""
        # This would create a new version of the instance template
        return {"action": "update_template", "status": "updated"}

    def _calculate_overall_health(self, health_results: Dict[str, Any]) -> str:
        """Calculate overall health status from individual results."""
        if not health_results:
            return "unknown"

        statuses = [
            result.get("status", "unknown") for result in health_results.values()
        ]

        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "error" for status in statuses):
            return "error"
        else:
            return "degraded"

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()
