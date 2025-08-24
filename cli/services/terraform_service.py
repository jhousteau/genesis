"""
Terraform Service
Infrastructure as Code management service following CRAFT methodology.
"""

import json
import subprocess
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import tempfile
import logging

from .auth_service import AuthService
from .cache_service import CacheService
from .error_service import ErrorService, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


@dataclass
class TerraformPlan:
    """Terraform plan result."""

    actions: Dict[str, int]  # add, change, destroy counts
    resources: List[Dict[str, Any]]
    has_changes: bool
    plan_file: Optional[str] = None


@dataclass
class TerraformState:
    """Terraform state information."""

    resources: List[Dict[str, Any]]
    outputs: Dict[str, Any]
    serial: int
    terraform_version: str


class TerraformService:
    """
    Terraform infrastructure management service implementing CRAFT principles.

    Create: Robust Terraform workflow management
    Refactor: Optimized for infrastructure best practices
    Authenticate: Secure state and credential management
    Function: Reliable infrastructure operations
    Test: Comprehensive validation and testing
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

        self.terraform_config = config_service.get_terraform_config()
        self.project_id = self.terraform_config.get("project_id")
        self.environment = self.terraform_config.get("environment")

        # Terraform paths
        self.genesis_root = config_service.genesis_root
        self.modules_dir = self.genesis_root / "modules"
        self.environments_dir = self.genesis_root / "environments"

    def init(
        self, module_path: str, backend_config: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Initialize Terraform in a module directory."""
        try:
            module_dir = self._resolve_module_path(module_path)

            # Ensure we have valid credentials
            self.auth_service.authenticate_gcp(self.project_id)

            cmd = ["terraform", "init"]

            # Add backend configuration
            if backend_config or self.terraform_config.get("backend"):
                backend_config = backend_config or self._generate_backend_config()
                for key, value in backend_config.items():
                    cmd.extend([f"-backend-config={key}={value}"])

            # Add plugin directory if configured
            if self.terraform_config.get("plugin_cache_dir"):
                os.environ["TF_PLUGIN_CACHE_DIR"] = self.terraform_config[
                    "plugin_cache_dir"
                ]

            result = self._execute_terraform_command(cmd, module_dir)

            if result["success"]:
                # Cache initialization status
                self.cache_service.set(
                    f"terraform_init:{module_path}",
                    {"initialized": True, "timestamp": datetime.now().isoformat()},
                    ttl=3600,
                    tags=["terraform", "init"],
                )

            return result

        except Exception as e:
            error = self.error_service.handle_exception(
                e, {"operation": "terraform_init", "module_path": module_path}
            )
            return {"success": False, "error": error, "data": None}

    def plan(
        self,
        module_path: str,
        var_file: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        target: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create Terraform execution plan."""
        try:
            module_dir = self._resolve_module_path(module_path)

            # Ensure module is initialized
            if not self._is_module_initialized(module_path):
                init_result = self.init(module_path)
                if not init_result["success"]:
                    return init_result

            # Ensure we have valid credentials
            self.auth_service.authenticate_gcp(self.project_id)

            # Create plan file
            plan_file = tempfile.mktemp(suffix=".tfplan")

            cmd = ["terraform", "plan", f"-out={plan_file}", "-detailed-exitcode"]

            # Add variable file
            if var_file:
                cmd.extend([f"-var-file={var_file}"])
            elif self._get_default_var_file(module_path):
                cmd.extend([f"-var-file={self._get_default_var_file(module_path)}"])

            # Add individual variables
            if variables:
                for key, value in variables.items():
                    cmd.extend([f"-var={key}={value}"])

            # Add default variables
            default_vars = self._generate_default_variables()
            for key, value in default_vars.items():
                cmd.extend([f"-var={key}={value}"])

            # Add target if specified
            if target:
                cmd.extend([f"-target={target}"])

            result = self._execute_terraform_command(cmd, module_dir)

            # Parse plan output
            if result["success"]:
                plan_data = self._parse_plan_file(plan_file)
                plan_data["plan_file"] = plan_file
                result["data"] = plan_data

                # Cache plan results
                self.cache_service.set(
                    f"terraform_plan:{module_path}",
                    result["data"],
                    ttl=1800,  # 30 minutes
                    tags=["terraform", "plan"],
                )

            return result

        except Exception as e:
            error = self.error_service.handle_exception(
                e,
                {
                    "operation": "terraform_plan",
                    "module_path": module_path,
                    "target": target,
                },
            )
            return {"success": False, "error": error, "data": None}

    def apply(
        self,
        module_path: str,
        plan_file: Optional[str] = None,
        auto_approve: bool = False,
        var_file: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Apply Terraform configuration changes."""
        try:
            module_dir = self._resolve_module_path(module_path)

            # Ensure we have valid credentials
            self.auth_service.authenticate_gcp(self.project_id)

            cmd = ["terraform", "apply"]

            if plan_file and os.path.exists(plan_file):
                # Apply from plan file
                cmd.append(plan_file)
            else:
                # Apply with variables
                if auto_approve:
                    cmd.append("-auto-approve")

                # Add variable file
                if var_file:
                    cmd.extend([f"-var-file={var_file}"])
                elif self._get_default_var_file(module_path):
                    cmd.extend([f"-var-file={self._get_default_var_file(module_path)}"])

                # Add individual variables
                if variables:
                    for key, value in variables.items():
                        cmd.extend([f"-var={key}={value}"])

                # Add default variables
                default_vars = self._generate_default_variables()
                for key, value in default_vars.items():
                    cmd.extend([f"-var={key}={value}"])

            result = self._execute_terraform_command(
                cmd, module_dir, timeout=1800
            )  # 30 minutes

            if result["success"]:
                # Invalidate cached plans
                self.cache_service.delete_by_tags(["terraform", "plan"])

                # Cache apply status
                self.cache_service.set(
                    f"terraform_apply:{module_path}",
                    {"applied": True, "timestamp": datetime.now().isoformat()},
                    ttl=3600,
                    tags=["terraform", "apply"],
                )

            return result

        except Exception as e:
            error = self.error_service.handle_exception(
                e,
                {
                    "operation": "terraform_apply",
                    "module_path": module_path,
                    "auto_approve": auto_approve,
                },
            )
            return {"success": False, "error": error, "data": None}

    def destroy(
        self,
        module_path: str,
        auto_approve: bool = False,
        var_file: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        target: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Destroy Terraform-managed infrastructure."""
        try:
            module_dir = self._resolve_module_path(module_path)

            # Ensure we have valid credentials
            self.auth_service.authenticate_gcp(self.project_id)

            cmd = ["terraform", "destroy"]

            if auto_approve:
                cmd.append("-auto-approve")

            # Add variable file
            if var_file:
                cmd.extend([f"-var-file={var_file}"])
            elif self._get_default_var_file(module_path):
                cmd.extend([f"-var-file={self._get_default_var_file(module_path)}"])

            # Add individual variables
            if variables:
                for key, value in variables.items():
                    cmd.extend([f"-var={key}={value}"])

            # Add default variables
            default_vars = self._generate_default_variables()
            for key, value in default_vars.items():
                cmd.extend([f"-var={key}={value}"])

            # Add target if specified
            if target:
                cmd.extend([f"-target={target}"])

            result = self._execute_terraform_command(
                cmd, module_dir, timeout=1800
            )  # 30 minutes

            if result["success"]:
                # Clear all related cache entries
                self.cache_service.delete_by_tags([f"terraform"])

            return result

        except Exception as e:
            error = self.error_service.handle_exception(
                e,
                {
                    "operation": "terraform_destroy",
                    "module_path": module_path,
                    "target": target,
                },
            )
            return {"success": False, "error": error, "data": None}

    def validate(self, module_path: str) -> Dict[str, Any]:
        """Validate Terraform configuration."""
        try:
            module_dir = self._resolve_module_path(module_path)

            # Ensure module is initialized
            if not self._is_module_initialized(module_path):
                init_result = self.init(module_path)
                if not init_result["success"]:
                    return init_result

            cmd = ["terraform", "validate", "-json"]

            result = self._execute_terraform_command(cmd, module_dir)

            if result["success"] and result.get("stdout"):
                try:
                    validation_result = json.loads(result["stdout"])
                    result["data"] = validation_result
                except json.JSONDecodeError:
                    pass

            return result

        except Exception as e:
            error = self.error_service.handle_exception(
                e, {"operation": "terraform_validate", "module_path": module_path}
            )
            return {"success": False, "error": error, "data": None}

    def show_state(
        self, module_path: str, address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Show Terraform state information."""
        try:
            module_dir = self._resolve_module_path(module_path)

            cmd = ["terraform", "show", "-json"]

            if address:
                cmd.append(address)

            result = self._execute_terraform_command(cmd, module_dir)

            if result["success"] and result.get("stdout"):
                try:
                    state_data = json.loads(result["stdout"])
                    result["data"] = self._parse_state_data(state_data)
                except json.JSONDecodeError:
                    pass

            return result

        except Exception as e:
            error = self.error_service.handle_exception(
                e,
                {
                    "operation": "terraform_show",
                    "module_path": module_path,
                    "address": address,
                },
            )
            return {"success": False, "error": error, "data": None}

    def get_outputs(self, module_path: str) -> Dict[str, Any]:
        """Get Terraform output values."""
        try:
            module_dir = self._resolve_module_path(module_path)

            cmd = ["terraform", "output", "-json"]

            result = self._execute_terraform_command(cmd, module_dir)

            if result["success"] and result.get("stdout"):
                try:
                    outputs = json.loads(result["stdout"])
                    result["data"] = outputs
                except json.JSONDecodeError:
                    pass

            return result

        except Exception as e:
            error = self.error_service.handle_exception(
                e, {"operation": "terraform_output", "module_path": module_path}
            )
            return {"success": False, "error": error, "data": None}

    def _resolve_module_path(self, module_path: str) -> Path:
        """Resolve module path to absolute path."""
        if module_path.startswith("/"):
            return Path(module_path)

        # Check if it's a known module
        if (self.modules_dir / module_path).exists():
            return self.modules_dir / module_path

        # Check if it's an environment
        if (self.environments_dir / module_path).exists():
            return self.environments_dir / module_path

        # Default to modules directory
        return self.modules_dir / module_path

    def _is_module_initialized(self, module_path: str) -> bool:
        """Check if Terraform module is initialized."""
        cached_status = self.cache_service.get(f"terraform_init:{module_path}")
        if cached_status:
            return True

        module_dir = self._resolve_module_path(module_path)
        terraform_dir = module_dir / ".terraform"
        return terraform_dir.exists() and terraform_dir.is_dir()

    def _get_default_var_file(self, module_path: str) -> Optional[str]:
        """Get default variable file for module."""
        module_dir = self._resolve_module_path(module_path)

        # Check for environment-specific var file
        env_var_file = module_dir / f"terraform.{self.environment}.tfvars"
        if env_var_file.exists():
            return str(env_var_file)

        # Check for default var file
        default_var_file = module_dir / "terraform.tfvars"
        if default_var_file.exists():
            return str(default_var_file)

        return None

    def _generate_backend_config(self) -> Dict[str, str]:
        """Generate backend configuration."""
        return {
            "bucket": self.terraform_config.get("backend_bucket"),
            "prefix": f"{self.terraform_config.get('state_prefix')}/terraform.tfstate",
        }

    def _generate_default_variables(self) -> Dict[str, str]:
        """Generate default Terraform variables."""
        return {
            "project_id": self.project_id,
            "environment": self.environment,
            "region": self.terraform_config.get("region", "us-central1"),
            "zone": self.terraform_config.get("zone", "us-central1-a"),
        }

    def _execute_terraform_command(
        self, cmd: List[str], cwd: Path, timeout: int = 300
    ) -> Dict[str, Any]:
        """Execute Terraform command with proper environment."""
        try:
            # Set up environment
            env = os.environ.copy()
            env["GOOGLE_APPLICATION_CREDENTIALS"] = ""  # Use gcloud auth

            # Add Terraform-specific environment variables
            if self.terraform_config.get("plugin_cache_dir"):
                env["TF_PLUGIN_CACHE_DIR"] = self.terraform_config["plugin_cache_dir"]

            env["TF_IN_AUTOMATION"] = "1"
            env["TF_LOG"] = self.terraform_config.get("log_level", "WARN")

            # Execute command
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env
            )

            success = result.returncode == 0 or (
                "terraform plan" in " ".join(cmd) and result.returncode == 2
            )

            return {
                "success": success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Terraform command timed out after {timeout} seconds",
                "command": " ".join(cmd),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "command": " ".join(cmd)}

    def _parse_plan_file(self, plan_file: str) -> TerraformPlan:
        """Parse Terraform plan file."""
        try:
            # Use terraform show to get JSON output of plan
            cmd = ["terraform", "show", "-json", plan_file]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return TerraformPlan(
                    actions={"add": 0, "change": 0, "destroy": 0},
                    resources=[],
                    has_changes=False,
                    plan_file=plan_file,
                )

            plan_data = json.loads(result.stdout)
            resource_changes = plan_data.get("resource_changes", [])

            actions = {"add": 0, "change": 0, "destroy": 0}
            for change in resource_changes:
                change_actions = change.get("change", {}).get("actions", [])
                if "create" in change_actions:
                    actions["add"] += 1
                elif "update" in change_actions:
                    actions["change"] += 1
                elif "delete" in change_actions:
                    actions["destroy"] += 1

            has_changes = any(count > 0 for count in actions.values())

            return TerraformPlan(
                actions=actions,
                resources=resource_changes,
                has_changes=has_changes,
                plan_file=plan_file,
            )

        except Exception as e:
            logger.error(f"Failed to parse plan file: {e}")
            return TerraformPlan(
                actions={"add": 0, "change": 0, "destroy": 0},
                resources=[],
                has_changes=False,
                plan_file=plan_file,
            )

    def _parse_state_data(self, state_data: Dict[str, Any]) -> TerraformState:
        """Parse Terraform state data."""
        values = state_data.get("values", {})

        return TerraformState(
            resources=values.get("root_module", {}).get("resources", []),
            outputs=values.get("outputs", {}),
            serial=state_data.get("serial", 0),
            terraform_version=state_data.get("terraform_version", "unknown"),
        )
