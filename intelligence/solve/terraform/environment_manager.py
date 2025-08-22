"""Multi-environment configuration management for Terraform."""

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class EnvironmentManager:
    """Manages multi-environment Terraform configurations."""

    # Default environment configurations
    DEFAULT_CONFIGS = {
        "dev": {
            "instance_count": 1,
            "machine_type": "e2-micro",
            "disk_size": 10,
            "enable_cdn": False,
            "enable_monitoring": True,
            "log_level": "DEBUG",
            "min_instances": 0,
            "max_instances": 2,
            "memory": "256Mi",
            "cpu": "0.5",
        },
        "staging": {
            "instance_count": 2,
            "machine_type": "e2-small",
            "disk_size": 20,
            "enable_cdn": True,
            "enable_monitoring": True,
            "log_level": "INFO",
            "min_instances": 1,
            "max_instances": 5,
            "memory": "512Mi",
            "cpu": "1",
        },
        "prod": {
            "instance_count": 3,
            "machine_type": "e2-standard-2",
            "disk_size": 50,
            "enable_cdn": True,
            "enable_monitoring": True,
            "log_level": "WARNING",
            "min_instances": 2,
            "max_instances": 100,
            "memory": "2Gi",
            "cpu": "2",
        },
    }

    def __init__(self):
        """Initialize the environment manager."""
        self.environments = {}

    def generate_environment_configs(
        self,
        graph_data: dict,
        environments: list[str] = None,
    ) -> dict[str, dict[str, Any]]:
        """Generate environment-specific configurations.

        Args:
            graph_data: Graph data with nodes and edges
            environments: List of environments (default: dev, staging, prod)

        Returns:
            Dictionary of environment configurations
        """
        if environments is None:
            environments = ["dev", "staging", "prod"]

        configs = {}

        for env in environments:
            logger.info(f"Generating config for environment: {env}")
            configs[env] = self.adapt_for_environment(graph_data, env)

        return configs

    def adapt_for_environment(
        self, graph_data: dict, environment: str
    ) -> dict[str, Any]:
        """Adapt graph configuration for a specific environment.

        Args:
            graph_data: Graph data
            environment: Target environment

        Returns:
            Environment-specific configuration
        """
        base_config = self.DEFAULT_CONFIGS.get(environment, self.DEFAULT_CONFIGS["dev"])

        config = {
            "environment": environment,
            "gcp_project": "solve-build",  # Use the actual SOLVE project ID
            "gcp_region": "us-central1" if environment == "dev" else "us-east1",
            **base_config,
        }

        # Add node-specific configurations
        for node in graph_data.get("nodes", []):
            node_name = node.get("name", "")
            node_type = node.get("primitive_type", node.get("type", "")).lower()

            if node_type in ["cloud_run", "cloudrun"]:
                config[f"{node_name}_min_instances"] = base_config["min_instances"]
                config[f"{node_name}_max_instances"] = base_config["max_instances"]
                config[f"{node_name}_memory"] = base_config["memory"]
                config[f"{node_name}_cpu"] = base_config["cpu"]

            elif node_type in ["cloud_function", "cloudfunction"]:
                config[f"{node_name}_memory"] = base_config["memory"]
                config[f"{node_name}_timeout"] = 60 if environment == "dev" else 300
                config[f"{node_name}_max_instances"] = base_config["max_instances"]

            elif node_type == "firestore":
                config[f"{node_name}_location"] = (
                    "us-central" if environment == "dev" else "nam5"
                )

            elif node_type in ["cloud_storage", "cloudstorage"]:
                config[f"{node_name}_location"] = (
                    "US" if environment == "dev" else "MULTI-REGION"
                )
                config[f"{node_name}_storage_class"] = (
                    "STANDARD" if environment != "dev" else "NEARLINE"
                )

        # Add environment-specific labels
        config["labels"] = {
            "environment": environment,
            "managed_by": "solve",
            "cost_center": "engineering" if environment == "dev" else "operations",
        }

        # Add monitoring and alerting configs
        if environment == "prod":
            config["enable_alerting"] = True
            config["alert_email"] = "ops-team@example.com"
            config["sla_target"] = "99.9"

        return config

    def write_tfvars(self, config: dict[str, Any], filename: str) -> str:
        """Write configuration to a tfvars file.

        Args:
            config: Configuration dictionary
            filename: Output filename

        Returns:
            Generated tfvars content
        """
        lines = []

        for key, value in sorted(config.items()):
            if isinstance(value, str):
                lines.append(f'{key} = "{value}"')
            elif isinstance(value, bool):
                lines.append(f"{key} = {str(value).lower()}")
            elif isinstance(value, (int, float)):
                lines.append(f"{key} = {value}")
            elif isinstance(value, list):
                formatted = json.dumps(value, indent=2)
                lines.append(f"{key} = {formatted}")
            elif isinstance(value, dict):
                formatted = self._format_map(value)
                lines.append(f"{key} = {formatted}")

        return "\n".join(lines)

    def _format_map(self, data: dict) -> str:
        """Format a dictionary for HCL.

        Args:
            data: Dictionary to format

        Returns:
            HCL-formatted map
        """
        if not data:
            return "{}"

        lines = ["{"]
        for key, value in sorted(data.items()):
            if isinstance(value, str):
                lines.append(f'  {key} = "{value}"')
            else:
                lines.append(f"  {key} = {json.dumps(value)}")
        lines.append("}")

        return "\n".join(lines)

    def generate_backend_config(self, environment: str) -> str:
        """Generate backend configuration for an environment.

        Args:
            environment: Target environment

        Returns:
            Backend configuration HCL
        """
        return f"""# Backend configuration for {environment}
terraform {{
  backend "gcs" {{
    bucket = "${{var.state_bucket}}"
    prefix = "terraform/state/{environment}"
  }}
}}
"""

    def generate_remote_state_data(self, dependencies: list[str]) -> str:
        """Generate remote state data sources.

        Args:
            dependencies: List of dependent state names

        Returns:
            Remote state configuration HCL
        """
        hcl = "# Remote state data sources\n\n"

        for dep in dependencies:
            hcl += f"""data "terraform_remote_state" "{dep}" {{
  backend = "gcs"
  config = {{
    bucket = var.state_bucket
    prefix = "terraform/state/{dep}"
  }}
}}

"""

        return hcl
