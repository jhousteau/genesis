"""
Configuration Service
Centralized configuration management following SOLID principles.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Configuration management service following SOLID-CLOUD principles.

    Single Responsibility: Manages all configuration loading and access
    Open/Closed: Extensible for new configuration sources
    Liskov Substitution: Consistent interface across config types
    Interface Segregation: Focused configuration interface
    Dependency Inversion: Abstracts configuration sources
    """

    def __init__(self, genesis_root: Path):
        self.genesis_root = genesis_root
        self.config_path = genesis_root / "config"
        self._config_cache: Dict[str, Any] = {}
        self._environment = os.getenv("ENVIRONMENT", "dev")
        self._project_id = os.getenv("PROJECT_ID")

    @property
    def environment(self) -> str:
        """Get current environment."""
        return self._environment

    @property
    def project_id(self) -> Optional[str]:
        """Get current project ID."""
        return self._project_id

    def load_environment_config(
        self, environment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Load environment-specific configuration."""
        env = environment or self._environment
        cache_key = f"env_{env}"

        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        config_file = self.config_path / f"environments/{env}.yaml"

        if not config_file.exists():
            logger.warning(f"Environment config not found: {config_file}")
            return {}

        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f) or {}
                self._config_cache[cache_key] = config
                return config
        except Exception as e:
            logger.error(f"Failed to load environment config: {e}")
            return {}

    def load_global_config(self) -> Dict[str, Any]:
        """Load global configuration."""
        cache_key = "global"

        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        config_file = self.config_path / "global.yaml"

        if not config_file.exists():
            logger.warning(f"Global config not found: {config_file}")
            return {}

        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f) or {}
                self._config_cache[cache_key] = config
                return config
        except Exception as e:
            logger.error(f"Failed to load global config: {e}")
            return {}

    def get_terraform_config(self) -> Dict[str, Any]:
        """Get Terraform-specific configuration."""
        global_config = self.load_global_config()
        env_config = self.load_environment_config()

        terraform_config = {
            **global_config.get("terraform", {}),
            **env_config.get("terraform", {}),
        }

        # Add environment-specific overrides
        terraform_config.update(
            {
                "environment": self._environment,
                "project_id": self._project_id,
                "backend_bucket": f"{self._project_id}-terraform-state",
                "state_prefix": f"genesis/{self._environment}",
            }
        )

        return terraform_config

    def get_gcp_config(self) -> Dict[str, Any]:
        """Get GCP-specific configuration."""
        global_config = self.load_global_config()
        env_config = self.load_environment_config()

        gcp_config = {**global_config.get("gcp", {}), **env_config.get("gcp", {})}

        # Add default GCP settings
        gcp_config.update(
            {
                "project_id": self._project_id,
                "region": gcp_config.get("region", "us-central1"),
                "zone": gcp_config.get("zone", "us-central1-a"),
                "labels": {
                    "genesis-managed": "true",
                    "environment": self._environment,
                    **gcp_config.get("labels", {}),
                },
            }
        )

        return gcp_config

    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent-specific configuration."""
        global_config = self.load_global_config()
        env_config = self.load_environment_config()

        agent_config = {
            **global_config.get("agents", {}),
            **env_config.get("agents", {}),
        }

        # Add default agent settings
        agent_types = agent_config.get(
            "types",
            {
                "backend-developer": {
                    "machine_type": "e2-standard-2",
                    "disk_size_gb": 50,
                    "preemptible": True,
                    "image_family": "ubuntu-2004-lts",
                },
                "frontend-developer": {
                    "machine_type": "e2-standard-2",
                    "disk_size_gb": 30,
                    "preemptible": True,
                    "image_family": "ubuntu-2004-lts",
                },
                "platform-engineer": {
                    "machine_type": "e2-standard-4",
                    "disk_size_gb": 100,
                    "preemptible": False,
                    "image_family": "ubuntu-2004-lts",
                },
                "data-engineer": {
                    "machine_type": "e2-standard-4",
                    "disk_size_gb": 100,
                    "preemptible": True,
                    "image_family": "ubuntu-2004-lts",
                },
                "qa-automation": {
                    "machine_type": "e2-standard-2",
                    "disk_size_gb": 50,
                    "preemptible": True,
                    "image_family": "ubuntu-2004-lts",
                },
                "sre": {
                    "machine_type": "e2-standard-2",
                    "disk_size_gb": 50,
                    "preemptible": False,
                    "image_family": "ubuntu-2004-lts",
                },
            },
        )

        agent_config["types"] = {**agent_types, **agent_config.get("types", {})}

        return agent_config

    def get_container_config(self) -> Dict[str, Any]:
        """Get container orchestration configuration."""
        global_config = self.load_global_config()
        env_config = self.load_environment_config()

        container_config = {
            **global_config.get("containers", {}),
            **env_config.get("containers", {}),
        }

        # Add default container settings
        default_config = {
            "cluster_name": f"genesis-{self._environment}",
            "autopilot": True,
            "region": "us-central1",
            "namespace": "genesis",
            "services": {
                "agent-cage": {
                    "replicas": 3,
                    "port": 8080,
                    "image": f"gcr.io/{self._project_id}/agent-cage:latest",
                },
                "claude-talk": {
                    "replicas": 2,
                    "port": 8090,
                    "image": f"gcr.io/{self._project_id}/claude-talk:latest",
                },
            },
        }

        return {**default_config, **container_config}

    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance optimization configuration."""
        global_config = self.load_global_config()
        env_config = self.load_environment_config()

        perf_config = {
            **global_config.get("performance", {}),
            **env_config.get("performance", {}),
        }

        # Add default performance settings
        default_perf = {
            "response_timeout": 120,  # 2 minutes
            "target_response_time": 2.0,  # 2 seconds
            "cache": {"ttl": 300, "max_entries": 1000},  # 5 minutes
            "concurrency": {"max_workers": 10, "thread_pool_size": 20},
            "monitoring": {"enabled": True, "sample_rate": 0.1},
        }

        return {**default_perf, **perf_config}

    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration."""
        global_config = self.load_global_config()
        env_config = self.load_environment_config()

        security_config = {
            **global_config.get("security", {}),
            **env_config.get("security", {}),
        }

        # Add default security settings
        default_security = {
            "service_account": f"genesis-cli@{self._project_id}.iam.gserviceaccount.com",
            "scopes": [
                "https://www.googleapis.com/auth/cloud-platform",
                "https://www.googleapis.com/auth/compute",
            ],
            "audit_logging": True,
            "encryption": {"at_rest": True, "in_transit": True},
        }

        return {**default_security, **security_config}

    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration from all sources."""
        global_config = self.load_global_config()
        env_config = self.load_environment_config()

        merged_config = {
            **global_config,
            **env_config,
            "terraform": self.get_terraform_config(),
            "gcp": self.get_gcp_config(),
            "agents": self.get_agent_config(),
            "containers": self.get_container_config(),
            "performance": self.get_performance_config(),
            "security": self.get_security_config(),
            "environment": self._environment,
            "project_id": self._project_id,
        }

        return merged_config

    def invalidate_cache(self, cache_key: Optional[str] = None) -> None:
        """Invalidate configuration cache."""
        if cache_key:
            self._config_cache.pop(cache_key, None)
        else:
            self._config_cache.clear()

    def update_environment(self, environment: str) -> None:
        """Update current environment and invalidate cache."""
        self._environment = environment
        self.invalidate_cache()

    def update_project_id(self, project_id: str) -> None:
        """Update current project ID and invalidate cache."""
        self._project_id = project_id
        self.invalidate_cache()
