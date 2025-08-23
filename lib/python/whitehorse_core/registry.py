"""
Project Registry Integration Module
Provides interface to the project registry system
"""

import logging
import os
from typing import Any, Dict, List

import yaml


class ProjectRegistry:
    """Central interface to the project registry"""

    def __init__(self, registry_path: str = None):
        self.registry_path = registry_path or self._find_registry_path()
        self.logger = logging.getLogger(f"{__name__}.ProjectRegistry")
        self._cache = None

    def _find_registry_path(self) -> str:
        """Find the registry file"""
        possible_paths = [
            os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "projects", "registry.yaml"
            ),
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "projects",
                "registry-enhanced.yaml",
            ),
            os.path.expanduser("~/.bootstrap/registry.yaml"),
            "/etc/bootstrap/registry.yaml",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)

        raise FileNotFoundError("Project registry not found")

    def load_registry(self) -> Dict[str, Any]:
        """Load the complete registry"""
        if self._cache is None:
            try:
                with open(self.registry_path, "r") as f:
                    self._cache = yaml.safe_load(f)
            except Exception as e:
                self.logger.error(f"Failed to load registry: {e}")
                raise
        return self._cache

    def get_project(self, project_name: str) -> Dict[str, Any]:
        """Get configuration for a specific project"""
        registry = self.load_registry()
        projects = registry.get("projects", {})

        if project_name not in projects:
            raise ValueError(f"Project '{project_name}' not found in registry")

        return projects[project_name]

    def list_projects(self) -> List[str]:
        """List all projects in the registry"""
        registry = self.load_registry()
        return list(registry.get("projects", {}).keys())

    def get_projects_by_type(self, project_type: str) -> List[str]:
        """Get projects of a specific type"""
        registry = self.load_registry()
        projects = registry.get("projects", {})

        return [
            name
            for name, config in projects.items()
            if config.get("type") == project_type
        ]

    def get_projects_by_language(self, language: str) -> List[str]:
        """Get projects using a specific language"""
        registry = self.load_registry()
        projects = registry.get("projects", {})

        return [
            name
            for name, config in projects.items()
            if config.get("language") == language
        ]

    def get_environment_config(
        self, project_name: str, environment: str
    ) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        project = self.get_project(project_name)
        environments = project.get("environments", {})

        if environment not in environments:
            raise ValueError(
                f"Environment '{environment}' not found for project '{project_name}'"
            )

        return environments[environment]

    def get_global_config(self) -> Dict[str, Any]:
        """Get global configuration"""
        registry = self.load_registry()
        return registry.get("global", {})

    def get_template_config(self, template_name: str) -> Dict[str, Any]:
        """Get template configuration"""
        registry = self.load_registry()
        templates = registry.get("templates", {})

        if template_name not in templates:
            raise ValueError(f"Template '{template_name}' not found")

        return templates[template_name]

    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """Get list of projects pending migration"""
        registry = self.load_registry()
        projects = registry.get("projects", {})

        return [
            {"name": name, **config}
            for name, config in projects.items()
            if config.get("migration_status") == "pending"
        ]

    def update_project(self, project_name: str, updates: Dict[str, Any]):
        """Update project configuration"""
        registry = self.load_registry()

        if project_name not in registry.get("projects", {}):
            raise ValueError(f"Project '{project_name}' not found")

        # Update the project
        registry["projects"][project_name].update(updates)

        # Add audit log entry
        audit_entry = {
            "timestamp": "2024-08-20T00:00:00Z",  # In real implementation, use actual timestamp
            "action": "project_updated",
            "user": "system",
            "project": project_name,
            "details": f"Updated fields: {list(updates.keys())}",
        }

        if "audit_log" not in registry:
            registry["audit_log"] = []
        registry["audit_log"].append(audit_entry)

        # Save registry
        self._save_registry(registry)

        # Clear cache
        self._cache = None

    def add_project(self, project_name: str, config: Dict[str, Any]):
        """Add a new project to the registry"""
        registry = self.load_registry()

        if project_name in registry.get("projects", {}):
            raise ValueError(f"Project '{project_name}' already exists")

        # Add the project
        if "projects" not in registry:
            registry["projects"] = {}
        registry["projects"][project_name] = config

        # Add audit log entry
        audit_entry = {
            "timestamp": "2024-08-20T00:00:00Z",  # In real implementation, use actual timestamp
            "action": "project_added",
            "user": "system",
            "project": project_name,
            "details": f"Added new project of type {config.get('type', 'unknown')}",
        }

        if "audit_log" not in registry:
            registry["audit_log"] = []
        registry["audit_log"].append(audit_entry)

        # Update metrics
        self._update_metrics(registry)

        # Save registry
        self._save_registry(registry)

        # Clear cache
        self._cache = None

    def register_project(self, project_name: str, project_path: str):
        """Register a new project - alias for add_project with minimal config"""
        # Check if project already exists, if so update it instead
        registry = self.load_registry()
        if project_name in registry.get("projects", {}):
            # Project exists, update the path
            updates = {"path": project_path}
            self.update_project(project_name, updates)
            return
        
        # Create basic config from project path
        config = {
            "path": project_path,
            "type": "api",  # Default type
            "language": "auto",  # Auto-detect
            "cloud_provider": "gcp",
            "team": "unknown",
            "criticality": "medium",
            "environments": {
                "dev": {
                    "gcp_project": f"{project_name}-dev",
                    "gcloud_home": f"~/.gcloud/{project_name}-dev"
                },
                "test": {
                    "gcp_project": f"{project_name}-test", 
                    "gcloud_home": f"~/.gcloud/{project_name}-test"
                },
                "prod": {
                    "gcp_project": f"{project_name}-prod",
                    "gcloud_home": f"~/.gcloud/{project_name}-prod",
                    "approval_required": True
                }
            },
            "intelligence": {
                "auto_fix_enabled": True,
                "optimization_enabled": True,
                "predictions_enabled": True,
                "recommendations_enabled": True
            }
        }
        
        return self.add_project(project_name, config)

    def _update_metrics(self, registry: Dict[str, Any]):
        """Update platform metrics"""
        projects = registry.get("projects", {})

        metrics = {
            "total_projects": len(projects),
            "active_projects": len(
                [p for p in projects.values() if not p.get("archived", False)]
            ),
            "projects_by_type": {},
            "projects_by_language": {},
            "pending_migrations": len(
                [p for p in projects.values() if p.get("migration_status") == "pending"]
            ),
        }

        # Count by type and language
        for project in projects.values():
            project_type = project.get("type", "unknown")
            language = project.get("language", "unknown")

            metrics["projects_by_type"][project_type] = (
                metrics["projects_by_type"].get(project_type, 0) + 1
            )
            metrics["projects_by_language"][language] = (
                metrics["projects_by_language"].get(language, 0) + 1
            )

        registry["platform_metrics"] = metrics

    def _save_registry(self, registry: Dict[str, Any]):
        """Save registry to file"""
        try:
            with open(self.registry_path, "w") as f:
                yaml.dump(registry, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")
            raise

    def validate_project_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate project configuration"""
        errors = []

        required_fields = ["type", "language", "team", "criticality"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Validate environment configurations
        environments = config.get("environments", {})
        for env_name, env_config in environments.items():
            if "gcp_project" not in env_config:
                errors.append(f"Missing gcp_project for environment {env_name}")

        return errors

    def get_deployment_targets(self, project_name: str) -> List[str]:
        """Get list of deployment targets for a project"""
        project = self.get_project(project_name)
        return list(project.get("environments", {}).keys())

    def get_intelligence_config(self, project_name: str) -> Dict[str, Any]:
        """Get intelligence layer configuration for a project"""
        project = self.get_project(project_name)
        return project.get(
            "intelligence",
            {
                "auto_fix_enabled": False,
                "optimization_enabled": False,
                "predictions_enabled": False,
                "recommendations_enabled": False,
            },
        )

    def get_monitoring_config(self, project_name: str) -> Dict[str, Any]:
        """Get monitoring configuration for a project"""
        project = self.get_project(project_name)
        return project.get("monitoring", {"enabled": False})

    def get_security_config(self, project_name: str) -> Dict[str, Any]:
        """Get security configuration for a project"""
        project = self.get_project(project_name)
        return project.get(
            "security",
            {
                "vulnerability_scanning": False,
                "secret_scanning": False,
                "compliance_checks": [],
            },
        )
