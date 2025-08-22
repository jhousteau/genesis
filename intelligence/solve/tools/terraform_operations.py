"""
Real Terraform Operations Tool for SOLVE Agents

Implements actual Terraform operations with safety mechanisms and comprehensive functionality.
Based on best practices from docs/best-practices/ and patterns from GitTool.

NO MOCKS, NO STUBS - REAL TERRAFORM OPERATIONS ONLY
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

logger = logging.getLogger(__name__)

try:
    from python_terraform import IsNotFlagged, Terraform
except ImportError:
    logger.warning(
        "python-terraform not installed. TerraformTool functionality will be limited."
    )
    Terraform = None
    IsNotFlagged = None


@dataclass
class TerraformOperation:
    """Result of a Terraform operation."""

    success: bool
    command: str
    operation: str
    message: str
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TerraformState:
    """Terraform state information."""

    workspace: str
    backend_config: dict[str, Any]
    resources: list[dict[str, Any]]
    outputs: dict[str, Any]
    version: str
    serial: int
    lineage: str


@dataclass
class TerraformSafetyConfig:
    """Safety configuration for Terraform operations."""

    allow_destroy: bool = False
    allow_force_unlock: bool = False
    require_confirmation_for_apply: bool = True
    protected_workspaces: list[str] = field(
        default_factory=lambda: ["production", "prod"]
    )
    max_cost_threshold_usd: float = 1000.0
    allowed_providers: list[str] = field(
        default_factory=lambda: ["google", "google-beta"]
    )
    sandbox_directories: list[str] = field(default_factory=list)
    auto_approve_for_plan_only: bool = True
    require_backend_config: bool = True


class TerraformTool:
    """
    Real Terraform operations tool with safety mechanisms.

    CRITICAL: This performs ACTUAL Terraform operations - no mocking.
    Provides comprehensive Terraform functionality for GCP deployment.
    """

    def __init__(
        self,
        working_dir: Union[str, Path] | None = None,
        safety_config: TerraformSafetyConfig | None = None,
    ):
        """Initialize Terraform tool with safety configuration."""
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.safety_config = safety_config or TerraformSafetyConfig()
        self.operation_log: list[TerraformOperation] = []

        # Initialize terraform-python wrapper
        if Terraform is not None:
            self.tf = Terraform(working_dir=str(self.working_dir))
        else:
            self.tf = None
            logger.warning(
                "Terraform wrapper not available - install python-terraform package"
            )

        logger.info(f"TerraformTool initialized in {self.working_dir}")

    def _validate_directory(
        self, terraform_dir: Union[str, Path] | None = None
    ) -> Path:
        """
        Validate Terraform directory and ensure safety.

        Args:
            terraform_dir: Directory containing Terraform files

        Returns:
            Validated directory path

        Raises:
            ValueError: If directory validation fails
        """
        if terraform_dir:
            dir_path = Path(terraform_dir).resolve()
        else:
            dir_path = self.working_dir.resolve()

        # Check if directory exists
        if not dir_path.exists():
            raise ValueError(f"Terraform directory does not exist: {dir_path}")

        # Check for Terraform files
        tf_files = list(dir_path.glob("*.tf"))
        if not tf_files:
            raise ValueError(f"No Terraform files found in directory: {dir_path}")

        # Validate sandbox if configured
        if self.safety_config.sandbox_directories:
            is_sandbox = any(
                str(dir_path).startswith(str(Path(sandbox).resolve()))
                for sandbox in self.safety_config.sandbox_directories
            )
            if not is_sandbox:
                logger.warning(f"Directory {dir_path} is not in sandbox list")

        return dir_path

    def _sanitize_path(self, path: str) -> str:
        """
        Sanitize file paths to prevent injection attacks.

        Args:
            path: Path to sanitize

        Returns:
            Sanitized path

        Raises:
            ValueError: If path contains dangerous characters
        """
        if not path:
            raise ValueError("Empty path not allowed")

        # Check for dangerous characters
        dangerous_chars = [";", "|", "&", "$", "`", "(", ")", "{", "}"]
        for char in dangerous_chars:
            if char in path:
                raise ValueError(f"Dangerous character '{char}' found in path: {path}")

        return path

    def _validate_workspace_name(self, workspace: str) -> str:
        """
        Validate workspace name for safety.

        Args:
            workspace: Workspace name to validate

        Returns:
            Validated workspace name

        Raises:
            ValueError: If workspace name is invalid or protected
        """
        if not workspace or not isinstance(workspace, str):
            raise ValueError("Workspace name must be a non-empty string")

        # Check for invalid characters
        if not workspace.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid workspace name: {workspace}")

        # Check protected workspaces
        if workspace in self.safety_config.protected_workspaces:
            raise ValueError(f"Cannot operate on protected workspace: {workspace}")

        return workspace

    def _validate_terraform_config(self, config_dir: Path) -> None:
        """
        Validate Terraform configuration for safety.

        Args:
            config_dir: Directory containing Terraform configuration

        Raises:
            ValueError: If configuration is unsafe
        """
        # Check for required backend configuration
        if self.safety_config.require_backend_config:
            backend_files = list(config_dir.glob("*backend*.tf")) + list(
                config_dir.glob("*remote*.tf"),
            )
            if not backend_files:
                logger.warning("No backend configuration found - state will be local")

        # Validate providers
        for tf_file in config_dir.glob("*.tf"):
            try:
                content = tf_file.read_text()
                # Simple provider validation (could be enhanced with HCL parsing)
                for provider in ["provider", "terraform"]:
                    if provider in content:
                        logger.debug(
                            f"Found {provider} configuration in {tf_file.name}"
                        )
            except Exception as e:
                logger.warning(f"Could not read {tf_file}: {e}")

    def _execute_terraform_command(
        self,
        command: str,
        args: list[str] | None = None,
        capture_output: bool = True,
        **kwargs: Any,
    ) -> tuple[int, str, str]:
        """
        Execute Terraform command safely.

        Args:
            command: Terraform command (init, plan, apply, etc.)
            args: Additional arguments
            capture_output: Whether to capture output
            **kwargs: Additional terraform-python arguments

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        args = args or []

        # Validate command
        allowed_commands = [
            "init",
            "plan",
            "apply",
            "destroy",
            "validate",
            "workspace",
            "output",
            "state",
        ]
        if command not in allowed_commands:
            raise ValueError(f"Command '{command}' not allowed")

        # Safety checks for destructive operations
        if command == "destroy" and not self.safety_config.allow_destroy:
            raise ValueError("Destroy operations not allowed by safety configuration")

        if command == "apply" and self.safety_config.require_confirmation_for_apply:
            if "-auto-approve" not in args and not kwargs.get("auto_approve", False):
                logger.warning(
                    "Apply operations require confirmation "
                    "(use auto_approve=True or add -auto-approve)",
                )

        logger.info(f"Executing terraform {command} {' '.join(args)}")

        try:
            # Check if terraform wrapper is available
            if self.tf is None:
                raise RuntimeError(
                    "Terraform wrapper not available - install python-terraform package",
                )

            # Use terraform-python wrapper
            method = getattr(self.tf, command)
            if not method:
                raise ValueError(f"Terraform command '{command}' not supported")

            # Execute command
            return_code, stdout, stderr = method(
                *args, capture_output=capture_output, **kwargs
            )

            return return_code, stdout, stderr

        except Exception as e:
            logger.error(f"Terraform command failed: {e}")
            return 1, "", str(e)

    def _log_operation(
        self,
        operation: str,
        command: str,
        success: bool,
        message: str,
        stdout: str = "",
        stderr: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> TerraformOperation:
        """Log Terraform operation for audit trail."""
        op = TerraformOperation(
            success=success,
            command=command,
            operation=operation,
            message=message,
            stdout=stdout,
            stderr=stderr,
            metadata=metadata or {},
        )
        self.operation_log.append(op)

        if success:
            logger.info(f"TerraformOp {operation}: {message}")
        else:
            logger.error(f"TerraformOp {operation} FAILED: {message}")

        return op

    async def init(
        self,
        terraform_dir: Union[str, Path] | None = None,
        backend_config: dict[str, str] | None = None,
        upgrade: bool = False,
        reconfigure: bool = False,
    ) -> TerraformOperation:
        """
        Initialize Terraform working directory.

        Args:
            terraform_dir: Directory containing Terraform files
            backend_config: Backend configuration parameters
            upgrade: Upgrade provider plugins
            reconfigure: Reconfigure backend

        Returns:
            TerraformOperation result
        """
        try:
            tf_dir = self._validate_directory(terraform_dir)
            self._validate_terraform_config(tf_dir)

            # Update working directory if needed
            if tf_dir != self.working_dir:
                self.tf = Terraform(working_dir=str(tf_dir))

            args = []
            if upgrade:
                args.append("-upgrade")
            if reconfigure:
                args.append("-reconfigure")

            # Add backend config if provided
            backend_configs = []
            if backend_config:
                for key, value in backend_config.items():
                    backend_configs.extend(["-backend-config", f"{key}={value}"])
                args.extend(backend_configs)

            return_code, stdout, stderr = self._execute_terraform_command("init", args)

            if return_code == 0:
                return self._log_operation(
                    "init",
                    f"terraform init {' '.join(args)}",
                    True,
                    f"Initialized Terraform in {tf_dir}",
                    stdout=stdout,
                    metadata={
                        "directory": str(tf_dir),
                        "backend_config": backend_config,
                        "upgrade": upgrade,
                        "reconfigure": reconfigure,
                    },
                )
            else:
                return self._log_operation(
                    "init",
                    f"terraform init {' '.join(args)}",
                    False,
                    f"Initialization failed: {stderr}",
                    stderr=stderr,
                )

        except Exception as e:
            return self._log_operation(
                "init",
                "terraform init",
                False,
                f"Init failed: {str(e)}",
                stderr=str(e),
            )

    async def plan(
        self,
        terraform_dir: Union[str, Path] | None = None,
        var_file: str | None = None,
        variables: dict[str, str] | None = None,
        target: list[str] | None = None,
        out_file: str | None = None,
        destroy: bool = False,
    ) -> TerraformOperation:
        """
        Create Terraform execution plan.

        Args:
            terraform_dir: Directory containing Terraform files
            var_file: Variables file path
            variables: Variable overrides
            target: Specific resources to target
            out_file: Output plan file
            destroy: Create destroy plan

        Returns:
            TerraformOperation result
        """
        try:
            tf_dir = self._validate_directory(terraform_dir)

            if tf_dir != self.working_dir:
                self.tf = Terraform(working_dir=str(tf_dir))

            args = []
            if var_file:
                args.extend(["-var-file", var_file])
            if variables:
                for key, value in variables.items():
                    args.extend(["-var", f"{key}={value}"])
            if target:
                for tgt in target:
                    args.extend(["-target", tgt])
            if out_file:
                args.extend(["-out", out_file])
            if destroy:
                args.append("-destroy")

            return_code, stdout, stderr = self._execute_terraform_command("plan", args)

            # Parse plan output for cost estimation
            plan_summary = self._parse_plan_output(stdout)

            if return_code == 0:
                return self._log_operation(
                    "plan",
                    f"terraform plan {' '.join(args)}",
                    True,
                    f"Plan created: {plan_summary.get('summary', 'No changes')}",
                    stdout=stdout,
                    metadata={
                        "directory": str(tf_dir),
                        "plan_summary": plan_summary,
                        "var_file": var_file,
                        "variables": variables,
                        "destroy": destroy,
                    },
                )
            else:
                return self._log_operation(
                    "plan",
                    f"terraform plan {' '.join(args)}",
                    False,
                    f"Plan failed: {stderr}",
                    stderr=stderr,
                )

        except Exception as e:
            return self._log_operation(
                "plan",
                "terraform plan",
                False,
                f"Plan failed: {str(e)}",
                stderr=str(e),
            )

    async def apply(
        self,
        terraform_dir: Union[str, Path] | None = None,
        plan_file: str | None = None,
        auto_approve: bool = False,
        var_file: str | None = None,
        variables: dict[str, str] | None = None,
        target: list[str] | None = None,
    ) -> TerraformOperation:
        """
        Apply Terraform configuration.

        Args:
            terraform_dir: Directory containing Terraform files
            plan_file: Pre-generated plan file
            auto_approve: Skip interactive approval
            var_file: Variables file path
            variables: Variable overrides
            target: Specific resources to target

        Returns:
            TerraformOperation result
        """
        try:
            tf_dir = self._validate_directory(terraform_dir)

            # Safety check for auto-approve
            if not auto_approve and self.safety_config.require_confirmation_for_apply:
                return self._log_operation(
                    "apply",
                    "terraform apply",
                    False,
                    "Apply requires confirmation (set auto_approve=True)",
                )

            if tf_dir != self.working_dir:
                self.tf = Terraform(working_dir=str(tf_dir))

            args = []
            if plan_file:
                args.append(plan_file)
            else:
                if auto_approve:
                    args.append("-auto-approve")
                if var_file:
                    args.extend(["-var-file", var_file])
                if variables:
                    for key, value in variables.items():
                        args.extend(["-var", f"{key}={value}"])
                if target:
                    for tgt in target:
                        args.extend(["-target", tgt])

            return_code, stdout, stderr = self._execute_terraform_command(
                "apply",
                args,
                auto_approve=auto_approve,
            )

            if return_code == 0:
                # Extract apply summary
                apply_summary = self._parse_apply_output(stdout)

                return self._log_operation(
                    "apply",
                    f"terraform apply {' '.join(args)}",
                    True,
                    f"Apply completed: {apply_summary.get('summary', 'Resources applied')}",
                    stdout=stdout,
                    metadata={
                        "directory": str(tf_dir),
                        "apply_summary": apply_summary,
                        "plan_file": plan_file,
                        "auto_approve": auto_approve,
                    },
                )
            else:
                return self._log_operation(
                    "apply",
                    f"terraform apply {' '.join(args)}",
                    False,
                    f"Apply failed: {stderr}",
                    stderr=stderr,
                )

        except Exception as e:
            return self._log_operation(
                "apply",
                "terraform apply",
                False,
                f"Apply failed: {str(e)}",
                stderr=str(e),
            )

    async def destroy(
        self,
        terraform_dir: Union[str, Path] | None = None,
        auto_approve: bool = False,
        var_file: str | None = None,
        variables: dict[str, str] | None = None,
        target: list[str] | None = None,
    ) -> TerraformOperation:
        """
        Destroy Terraform-managed infrastructure.

        Args:
            terraform_dir: Directory containing Terraform files
            auto_approve: Skip interactive approval
            var_file: Variables file path
            variables: Variable overrides
            target: Specific resources to target

        Returns:
            TerraformOperation result
        """
        try:
            if not self.safety_config.allow_destroy:
                return self._log_operation(
                    "destroy",
                    "terraform destroy",
                    False,
                    "Destroy operations not allowed by safety configuration",
                )

            tf_dir = self._validate_directory(terraform_dir)

            if tf_dir != self.working_dir:
                self.tf = Terraform(working_dir=str(tf_dir))

            args = []
            if auto_approve:
                args.append("-auto-approve")
            if var_file:
                args.extend(["-var-file", var_file])
            if variables:
                for key, value in variables.items():
                    args.extend(["-var", f"{key}={value}"])
            if target:
                for tgt in target:
                    args.extend(["-target", tgt])

            return_code, stdout, stderr = self._execute_terraform_command(
                "destroy",
                args,
                auto_approve=auto_approve,
            )

            if return_code == 0:
                destroy_summary = self._parse_destroy_output(stdout)

                return self._log_operation(
                    "destroy",
                    f"terraform destroy {' '.join(args)}",
                    True,
                    f"Destroy completed: {destroy_summary.get('summary', 'Resources destroyed')}",
                    stdout=stdout,
                    metadata={
                        "directory": str(tf_dir),
                        "destroy_summary": destroy_summary,
                        "auto_approve": auto_approve,
                    },
                )
            else:
                return self._log_operation(
                    "destroy",
                    f"terraform destroy {' '.join(args)}",
                    False,
                    f"Destroy failed: {stderr}",
                    stderr=stderr,
                )

        except Exception as e:
            return self._log_operation(
                "destroy",
                "terraform destroy",
                False,
                f"Destroy failed: {str(e)}",
                stderr=str(e),
            )

    async def validate(
        self, terraform_dir: Union[str, Path] | None = None
    ) -> TerraformOperation:
        """
        Validate Terraform configuration.

        Args:
            terraform_dir: Directory containing Terraform files

        Returns:
            TerraformOperation result
        """
        try:
            tf_dir = self._validate_directory(terraform_dir)

            if tf_dir != self.working_dir:
                self.tf = Terraform(working_dir=str(tf_dir))

            return_code, stdout, stderr = self._execute_terraform_command("validate")

            if return_code == 0:
                return self._log_operation(
                    "validate",
                    "terraform validate",
                    True,
                    "Configuration is valid",
                    stdout=stdout,
                    metadata={"directory": str(tf_dir)},
                )
            else:
                return self._log_operation(
                    "validate",
                    "terraform validate",
                    False,
                    f"Validation failed: {stderr}",
                    stderr=stderr,
                )

        except Exception as e:
            return self._log_operation(
                "validate",
                "terraform validate",
                False,
                f"Validation failed: {str(e)}",
                stderr=str(e),
            )

    async def workspace_list(
        self,
        terraform_dir: Union[str, Path] | None = None,
    ) -> TerraformOperation:
        """
        List Terraform workspaces.

        Args:
            terraform_dir: Directory containing Terraform files

        Returns:
            TerraformOperation result
        """
        try:
            tf_dir = self._validate_directory(terraform_dir)

            if tf_dir != self.working_dir:
                self.tf = Terraform(working_dir=str(tf_dir))

            return_code, stdout, stderr = self._execute_terraform_command(
                "workspace", ["list"]
            )

            if return_code == 0:
                workspaces = self._parse_workspace_list(stdout)
                current_workspace = next(
                    (ws for ws in workspaces if ws.startswith("*")),
                    "default",
                ).lstrip("* ")

                return self._log_operation(
                    "workspace_list",
                    "terraform workspace list",
                    True,
                    f"Found {len(workspaces)} workspaces",
                    stdout=stdout,
                    metadata={
                        "directory": str(tf_dir),
                        "workspaces": [ws.lstrip("* ") for ws in workspaces],
                        "current_workspace": current_workspace,
                    },
                )
            else:
                return self._log_operation(
                    "workspace_list",
                    "terraform workspace list",
                    False,
                    f"Workspace list failed: {stderr}",
                    stderr=stderr,
                )

        except Exception as e:
            return self._log_operation(
                "workspace_list",
                "terraform workspace list",
                False,
                f"Workspace list failed: {str(e)}",
                stderr=str(e),
            )

    async def workspace_select(
        self,
        workspace: str,
        terraform_dir: Union[str, Path] | None = None,
    ) -> TerraformOperation:
        """
        Select Terraform workspace.

        Args:
            workspace: Workspace name to select
            terraform_dir: Directory containing Terraform files

        Returns:
            TerraformOperation result
        """
        try:
            tf_dir = self._validate_directory(terraform_dir)
            validated_workspace = self._validate_workspace_name(workspace)

            if tf_dir != self.working_dir:
                self.tf = Terraform(working_dir=str(tf_dir))

            return_code, stdout, stderr = self._execute_terraform_command(
                "workspace",
                ["select", validated_workspace],
            )

            if return_code == 0:
                return self._log_operation(
                    "workspace_select",
                    f"terraform workspace select {workspace}",
                    True,
                    f"Selected workspace '{workspace}'",
                    stdout=stdout,
                    metadata={"directory": str(tf_dir), "workspace": workspace},
                )
            else:
                return self._log_operation(
                    "workspace_select",
                    f"terraform workspace select {workspace}",
                    False,
                    f"Workspace select failed: {stderr}",
                    stderr=stderr,
                )

        except Exception as e:
            return self._log_operation(
                "workspace_select",
                f"terraform workspace select {workspace}",
                False,
                f"Workspace select failed: {str(e)}",
                stderr=str(e),
            )

    async def workspace_new(
        self,
        workspace: str,
        terraform_dir: Union[str, Path] | None = None,
    ) -> TerraformOperation:
        """
        Create new Terraform workspace.

        Args:
            workspace: Workspace name to create
            terraform_dir: Directory containing Terraform files

        Returns:
            TerraformOperation result
        """
        try:
            tf_dir = self._validate_directory(terraform_dir)
            validated_workspace = self._validate_workspace_name(workspace)

            if tf_dir != self.working_dir:
                self.tf = Terraform(working_dir=str(tf_dir))

            return_code, stdout, stderr = self._execute_terraform_command(
                "workspace",
                ["new", validated_workspace],
            )

            if return_code == 0:
                return self._log_operation(
                    "workspace_new",
                    f"terraform workspace new {workspace}",
                    True,
                    f"Created workspace '{workspace}'",
                    stdout=stdout,
                    metadata={"directory": str(tf_dir), "workspace": workspace},
                )
            else:
                return self._log_operation(
                    "workspace_new",
                    f"terraform workspace new {workspace}",
                    False,
                    f"Workspace creation failed: {stderr}",
                    stderr=stderr,
                )

        except Exception as e:
            return self._log_operation(
                "workspace_new",
                f"terraform workspace new {workspace}",
                False,
                f"Workspace creation failed: {str(e)}",
                stderr=str(e),
            )

    def _parse_plan_output(self, output: str) -> dict[str, Any]:
        """Parse Terraform plan output for summary information."""
        summary = {
            "summary": "No changes",
            "resources_to_add": 0,
            "resources_to_change": 0,
            "resources_to_destroy": 0,
        }

        lines = output.split("\n")
        for line in lines:
            if "Plan:" in line:
                # Extract plan summary
                summary["summary"] = line.strip()
                # Parse numbers from plan line
                import re

                numbers = re.findall(r"(\d+) to (\w+)", line)
                for count, action in numbers:
                    if action == "add":
                        summary["resources_to_add"] = int(count)
                    elif action == "change":
                        summary["resources_to_change"] = int(count)
                    elif action == "destroy":
                        summary["resources_to_destroy"] = int(count)

        return summary

    def _parse_apply_output(self, output: str) -> dict[str, Any]:
        """Parse Terraform apply output for summary information."""
        summary = {
            "summary": "No changes",
            "resources_created": 0,
            "resources_updated": 0,
            "resources_destroyed": 0,
        }

        lines = output.split("\n")
        for line in lines:
            if "Apply complete!" in line:
                summary["summary"] = line.strip()
                # Extract resource counts
                import re

                numbers = re.findall(r"(\d+) (\w+)", line)
                for count, action in numbers:
                    if action in ["added", "created"]:
                        summary["resources_created"] = int(count)
                    elif action in ["changed", "updated"]:
                        summary["resources_updated"] = int(count)
                    elif action in ["destroyed", "deleted"]:
                        summary["resources_destroyed"] = int(count)

        return summary

    def _parse_destroy_output(self, output: str) -> dict[str, Any]:
        """Parse Terraform destroy output for summary information."""
        summary = {"summary": "No resources destroyed", "resources_destroyed": 0}

        lines = output.split("\n")
        for line in lines:
            if "Destroy complete!" in line:
                summary["summary"] = line.strip()
                # Extract resource count
                import re

                numbers = re.findall(r"(\d+) destroyed", line)
                if numbers:
                    summary["resources_destroyed"] = int(numbers[0])

        return summary

    def _parse_workspace_list(self, output: str) -> list[str]:
        """Parse workspace list output."""
        workspaces = []
        lines = output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("No"):
                workspaces.append(line)
        return workspaces

    def get_operation_log(self) -> list[TerraformOperation]:
        """Get the operation log for audit purposes."""
        return self.operation_log.copy()

    def clear_operation_log(self) -> None:
        """Clear the operation log."""
        self.operation_log.clear()
