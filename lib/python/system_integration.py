#!/usr/bin/env python3
"""
System Integration Module
Connects all 8 components of the Universal Project Platform
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml
from whitehorse_core.intelligence import IntelligenceCoordinator

# Import all components
from whitehorse_core.registry import ProjectRegistry

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ComponentStatus:
    """Status of a system component"""

    name: str
    enabled: bool
    healthy: bool
    version: str = "1.0.0"
    last_check: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)


class SystemIntegrator:
    """Manages integration between all platform components"""

    COMPONENTS = [
        "setup_project",  # 1. Project setup and initialization
        "isolation",  # 2. Environment isolation
        "infrastructure",  # 3. Infrastructure as Code (Terraform)
        "governance",  # 4. Governance and compliance
        "deployment",  # 5. Deployment pipelines
        "monitoring",  # 6. Monitoring and observability
        "intelligence",  # 7. AI/ML intelligence layer
        "cli",  # 8. Command-line interface
    ]

    def __init__(self, bootstrap_root: str = None):
        """Initialize system integrator"""
        self.bootstrap_root = (
            Path(bootstrap_root)
            if bootstrap_root
            else Path(__file__).parent.parent.parent
        )
        self.registry = ProjectRegistry()
        self.intelligence = IntelligenceCoordinator(self.registry)
        self.component_status = {}
        self._initialize_components()

    def _initialize_components(self):
        """Initialize all components"""
        for component in self.COMPONENTS:
            self.component_status[component] = self._check_component(component)

    def _check_component(self, component: str) -> ComponentStatus:
        """Check if a component is available and healthy"""
        status = ComponentStatus(name=component, enabled=False, healthy=False)

        try:
            if component == "setup_project":
                # Check setup-project module
                setup_path = self.bootstrap_root / "setup-project" / "setup.py"
                if setup_path.exists():
                    status.enabled = True
                    status.healthy = True

            elif component == "isolation":
                # Check isolation layer
                isolation_path = self.bootstrap_root / "isolation"
                if isolation_path.exists():
                    status.enabled = True
                    # Check key scripts
                    validator = isolation_path / "validation" / "isolation_validator.sh"
                    status.healthy = validator.exists()

            elif component == "infrastructure":
                # Check terraform modules
                modules_path = self.bootstrap_root / "modules"
                if modules_path.exists():
                    status.enabled = True
                    # Check for key modules
                    bootstrap_module = modules_path / "bootstrap"
                    status.healthy = bootstrap_module.exists()

            elif component == "governance":
                # Check governance configurations
                governance_path = self.bootstrap_root / "governance"
                if governance_path.exists():
                    status.enabled = True
                    status.healthy = True

            elif component == "deployment":
                # Check deployment scripts
                deploy_path = self.bootstrap_root / "deploy"
                scripts_path = self.bootstrap_root / "scripts"
                if deploy_path.exists() or scripts_path.exists():
                    status.enabled = True
                    status.healthy = True

            elif component == "monitoring":
                # Check monitoring modules
                monitoring_path = self.bootstrap_root / "monitoring"
                if monitoring_path.exists():
                    status.enabled = True
                    # Check for key monitoring components
                    metrics_path = monitoring_path / "metrics"
                    logging_path = monitoring_path / "logging"
                    status.healthy = metrics_path.exists() and logging_path.exists()

            elif component == "intelligence":
                # Check intelligence layer
                try:
                    from whitehorse_core.intelligence import IntelligenceCoordinator

                    status.enabled = True
                    status.healthy = True
                except ImportError:
                    status.enabled = False
                    status.errors.append("Intelligence module not available")

            elif component == "cli":
                # Check CLI
                cli_path = self.bootstrap_root / "bin" / "bootstrap"
                if cli_path.exists():
                    status.enabled = True
                    status.healthy = True

        except Exception as e:
            status.errors.append(str(e))
            logger.error(f"Error checking component {component}: {e}")

        return status

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        total_components = len(self.COMPONENTS)
        enabled_components = sum(1 for s in self.component_status.values() if s.enabled)
        healthy_components = sum(1 for s in self.component_status.values() if s.healthy)

        return {
            "total_components": total_components,
            "enabled_components": enabled_components,
            "healthy_components": healthy_components,
            "health_percentage": (healthy_components / total_components) * 100,
            "components": {
                name: {
                    "enabled": status.enabled,
                    "healthy": status.healthy,
                    "version": status.version,
                    "errors": status.errors,
                }
                for name, status in self.component_status.items()
            },
            "timestamp": datetime.now().isoformat(),
        }

    def integrate_project(self, project_name: str, project_path: str = None) -> bool:
        """Integrate a project with all platform components"""
        logger.info(f"Integrating project: {project_name}")

        if not project_path:
            project_path = self.bootstrap_root.parent / project_name

        project_path = Path(project_path)

        # Register project
        self.registry.register_project(project_name, str(project_path))

        # Apply each component
        results = {}

        # 1. Setup project structure
        if self.component_status["setup_project"].enabled:
            results["setup_project"] = self._apply_setup(project_name, project_path)

        # 2. Configure isolation
        if self.component_status["isolation"].enabled:
            results["isolation"] = self._apply_isolation(project_name, project_path)

        # 3. Setup infrastructure
        if self.component_status["infrastructure"].enabled:
            results["infrastructure"] = self._apply_infrastructure(
                project_name, project_path
            )

        # 4. Apply governance
        if self.component_status["governance"].enabled:
            results["governance"] = self._apply_governance(project_name, project_path)

        # 5. Configure deployment
        if self.component_status["deployment"].enabled:
            results["deployment"] = self._configure_deployment(
                project_name, project_path
            )

        # 6. Setup monitoring
        if self.component_status["monitoring"].enabled:
            results["monitoring"] = self._setup_monitoring(project_name, project_path)

        # 7. Enable intelligence
        if self.component_status["intelligence"].enabled:
            results["intelligence"] = self._enable_intelligence(
                project_name, project_path
            )

        # Save integration results
        self._save_integration_results(project_name, project_path, results)

        # Check if integration was successful
        success = all(r.get("success", False) for r in results.values() if r)

        if success:
            logger.info(f"✅ Successfully integrated project: {project_name}")
        else:
            logger.warning(f"⚠️  Partial integration for project: {project_name}")

        return success

    def _apply_setup(self, project_name: str, project_path: Path) -> Dict[str, Any]:
        """Apply project setup"""
        try:
            # Create project structure if needed
            essential_dirs = ["scripts", "tests", "docs", "deploy"]
            for dir_name in essential_dirs:
                dir_path = project_path / dir_name
                dir_path.mkdir(exist_ok=True)

            # Create project config if missing
            config_file = project_path / ".project-config.yaml"
            if not config_file.exists():
                config = {
                    "project_name": project_name,
                    "created_at": datetime.now().isoformat(),
                    "platform_version": "2.0.0",
                    "components": list(self.COMPONENTS),
                }
                with open(config_file, "w") as f:
                    yaml.dump(config, f)

            return {"success": True}

        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return {"success": False, "error": str(e)}

    def _apply_isolation(self, project_name: str, project_path: Path) -> Dict[str, Any]:
        """Apply isolation configuration"""
        try:
            # Create isolation config
            isolation_config = project_path / ".isolation"
            isolation_config.mkdir(exist_ok=True)

            # Copy isolation templates
            templates_dir = self.bootstrap_root / "isolation" / "gcp" / "templates"
            if templates_dir.exists():
                envrc_template = templates_dir / "envrc.template"
                if envrc_template.exists():
                    target = isolation_config / ".envrc"
                    if not target.exists():
                        import shutil

                        shutil.copy2(envrc_template, target)

            return {"success": True}

        except Exception as e:
            logger.error(f"Isolation setup failed: {e}")
            return {"success": False, "error": str(e)}

    def _apply_infrastructure(
        self, project_name: str, project_path: Path
    ) -> Dict[str, Any]:
        """Setup infrastructure configuration"""
        try:
            # Create terraform directory
            terraform_dir = project_path / "terraform"
            terraform_dir.mkdir(exist_ok=True)

            # Create basic terraform configuration
            main_tf = terraform_dir / "main.tf"
            if not main_tf.exists():
                with open(main_tf, "w") as f:
                    f.write(
                        f"""# Terraform configuration for {project_name}

terraform {{
  required_version = ">= 1.0"

  backend "gcs" {{
    bucket = "{project_name}-terraform-state"
    prefix = "terraform/state"
  }}
}}

provider "google" {{
  project = var.project_id
  region  = var.region
}}

variable "project_id" {{
  description = "GCP Project ID"
  type        = string
}}

variable "region" {{
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}}
"""
                    )

            return {"success": True}

        except Exception as e:
            logger.error(f"Infrastructure setup failed: {e}")
            return {"success": False, "error": str(e)}

    def _apply_governance(
        self, project_name: str, project_path: Path
    ) -> Dict[str, Any]:
        """Apply governance policies"""
        try:
            # Create governance config
            governance_file = project_path / ".governance.yaml"
            if not governance_file.exists():
                governance_config = {
                    "version": "1.0.0",
                    "policies": {
                        "security": {
                            "require_encryption": True,
                            "require_mfa": True,
                            "max_privilege_duration": "8h",
                        },
                        "compliance": {
                            "standards": ["SOC2", "GDPR"],
                            "audit_logging": True,
                        },
                        "cost": {"budget_alerts": True, "max_monthly_spend": 10000},
                    },
                }
                with open(governance_file, "w") as f:
                    yaml.dump(governance_config, f)

            return {"success": True}

        except Exception as e:
            logger.error(f"Governance setup failed: {e}")
            return {"success": False, "error": str(e)}

    def _configure_deployment(
        self, project_name: str, project_path: Path
    ) -> Dict[str, Any]:
        """Configure deployment pipeline"""
        try:
            # Create deployment configuration
            deploy_dir = project_path / "deploy"
            deploy_dir.mkdir(exist_ok=True)

            # Create deployment config
            deploy_config = deploy_dir / "config.yaml"
            if not deploy_config.exists():
                config = {
                    "environments": {
                        "dev": {"auto_deploy": True, "approval_required": False},
                        "stage": {"auto_deploy": False, "approval_required": True},
                        "prod": {
                            "auto_deploy": False,
                            "approval_required": True,
                            "rollback_enabled": True,
                        },
                    }
                }
                with open(deploy_config, "w") as f:
                    yaml.dump(config, f)

            return {"success": True}

        except Exception as e:
            logger.error(f"Deployment configuration failed: {e}")
            return {"success": False, "error": str(e)}

    def _setup_monitoring(
        self, project_name: str, project_path: Path
    ) -> Dict[str, Any]:
        """Setup monitoring configuration"""
        try:
            # Create monitoring config
            monitoring_file = project_path / ".monitoring.yaml"
            if not monitoring_file.exists():
                monitoring_config = {
                    "metrics": {
                        "enabled": True,
                        "collection_interval": "60s",
                        "retention_days": 30,
                    },
                    "logging": {"enabled": True, "level": "INFO", "structured": True},
                    "tracing": {"enabled": True, "sampling_rate": 0.1},
                    "alerting": {"enabled": True, "channels": ["email", "slack"]},
                }
                with open(monitoring_file, "w") as f:
                    yaml.dump(monitoring_config, f)

            return {"success": True}

        except Exception as e:
            logger.error(f"Monitoring setup failed: {e}")
            return {"success": False, "error": str(e)}

    def _enable_intelligence(
        self, project_name: str, project_path: Path
    ) -> Dict[str, Any]:
        """Enable intelligence features"""
        try:
            # Enable intelligence for the project
            self.intelligence.enable_intelligence_features(
                project_name,
                [
                    "auto_fix_enabled",
                    "optimization_enabled",
                    "predictions_enabled",
                    "recommendations_enabled",
                ],
            )

            # Create intelligence config
            intelligence_file = project_path / ".intelligence.yaml"
            if not intelligence_file.exists():
                intelligence_config = {
                    "enabled": True,
                    "features": {
                        "auto_fix": True,
                        "optimization": True,
                        "predictions": True,
                        "recommendations": True,
                    },
                    "scan_interval": "daily",
                    "auto_apply_fixes": False,
                }
                with open(intelligence_file, "w") as f:
                    yaml.dump(intelligence_config, f)

            return {"success": True}

        except Exception as e:
            logger.error(f"Intelligence setup failed: {e}")
            return {"success": False, "error": str(e)}

    def _save_integration_results(
        self, project_name: str, project_path: Path, results: Dict[str, Any]
    ):
        """Save integration results"""
        try:
            integration_file = project_path / ".integration-status.json"
            integration_data = {
                "project_name": project_name,
                "integration_date": datetime.now().isoformat(),
                "components": results,
                "platform_version": "2.0.0",
            }

            with open(integration_file, "w") as f:
                json.dump(integration_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save integration results: {e}")

    def verify_integration(
        self, project_name: str, project_path: str = None
    ) -> Dict[str, Any]:
        """Verify that a project is properly integrated"""
        if not project_path:
            project_info = self.registry.get_project(project_name)
            if not project_info:
                return {"error": f"Project {project_name} not found in registry"}
            project_path = project_info.get("path")

        project_path = Path(project_path)

        verification_results = {}

        # Check each component
        for component in self.COMPONENTS:
            if self.component_status[component].enabled:
                verification_results[component] = self._verify_component(
                    component, project_path
                )

        # Calculate overall health
        total_checks = len(verification_results)
        passed_checks = sum(
            1 for r in verification_results.values() if r.get("verified", False)
        )

        return {
            "project_name": project_name,
            "project_path": str(project_path),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "health_percentage": (
                (passed_checks / total_checks * 100) if total_checks > 0 else 0
            ),
            "components": verification_results,
            "fully_integrated": passed_checks == total_checks,
        }

    def _verify_component(self, component: str, project_path: Path) -> Dict[str, Any]:
        """Verify a specific component integration"""
        try:
            if component == "setup_project":
                # Check for essential directories and files
                essential = [".project-config.yaml", "scripts", "tests", "docs"]
                missing = [e for e in essential if not (project_path / e).exists()]
                return {"verified": len(missing) == 0, "missing": missing}

            elif component == "isolation":
                isolation_dir = project_path / ".isolation"
                return {"verified": isolation_dir.exists()}

            elif component == "infrastructure":
                terraform_dir = project_path / "terraform"
                return {"verified": terraform_dir.exists()}

            elif component == "governance":
                governance_file = project_path / ".governance.yaml"
                return {"verified": governance_file.exists()}

            elif component == "deployment":
                deploy_dir = project_path / "deploy"
                return {"verified": deploy_dir.exists()}

            elif component == "monitoring":
                monitoring_file = project_path / ".monitoring.yaml"
                return {"verified": monitoring_file.exists()}

            elif component == "intelligence":
                intelligence_file = project_path / ".intelligence.yaml"
                return {"verified": intelligence_file.exists()}

            elif component == "cli":
                # CLI is global, just check if project is in registry
                project_info = self.registry.get_project(project_path.name)
                return {"verified": project_info is not None}

        except Exception as e:
            return {"verified": False, "error": str(e)}

        return {"verified": False}


# Convenience functions
def get_system_integrator() -> SystemIntegrator:
    """Get the system integrator instance"""
    return SystemIntegrator()


def integrate_project(project_name: str, project_path: str = None) -> bool:
    """Integrate a project with all platform components"""
    integrator = get_system_integrator()
    return integrator.integrate_project(project_name, project_path)


def verify_project_integration(
    project_name: str, project_path: str = None
) -> Dict[str, Any]:
    """Verify project integration"""
    integrator = get_system_integrator()
    return integrator.verify_integration(project_name, project_path)


def get_platform_status() -> Dict[str, Any]:
    """Get overall platform status"""
    integrator = get_system_integrator()
    return integrator.get_system_status()
