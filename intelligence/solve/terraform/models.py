"""Data models for Terraform generation."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class TerraformResource:
    """Represents a single Terraform resource."""

    resource_type: str
    resource_name: str
    properties: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)

    def to_hcl(self) -> str:
        """Convert to HCL format."""
        hcl = f'resource "{self.resource_type}" "{self.resource_name}" {{\n'

        # Add properties
        for key, value in self.properties.items():
            hcl += f"  {key} = {self._format_value(value)}\n"

        # Add dependencies
        if self.depends_on:
            deps = ", ".join([f'"{dep}"' for dep in self.depends_on])
            hcl += f"  depends_on = [{deps}]\n"

        hcl += "}\n"
        return hcl

    def _format_value(self, value: Any) -> str:
        """Format a value for HCL."""
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            items = [self._format_value(v) for v in value]
            return f"[{', '.join(items)}]"
        elif isinstance(value, dict):
            return self._format_dict(value)
        else:
            return f'"{str(value)}"'

    def _format_dict(self, d: dict[str, Any], indent: int = 4) -> str:
        """Format a dictionary for HCL."""
        if not d:
            return "{}"

        lines = ["{"]
        for key, value in d.items():
            formatted_value = self._format_value(value)
            lines.append(f"{' ' * indent}{key} = {formatted_value}")
        lines.append(f"{' ' * (indent - 2)}}}")
        return "\n".join(lines)


@dataclass
class TerraformModule:
    """Represents a Terraform module."""

    name: str
    source: Optional[str] = None
    version: Optional[str] = None
    variables: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    resources: list[TerraformResource] = field(default_factory=list)

    def to_hcl(self) -> str:
        """Convert module to HCL format."""
        hcl = ""

        # Module declaration if it's a referenced module
        if self.source:
            hcl += f'module "{self.name}" {{\n'
            hcl += f'  source = "{self.source}"\n'
            if self.version:
                hcl += f'  version = "{self.version}"\n'
            for key, value in self.variables.items():
                hcl += f"  {key} = {self._format_value(value)}\n"
            hcl += "}\n\n"

        # Resources
        for resource in self.resources:
            hcl += resource.to_hcl() + "\n"

        return hcl

    def _format_value(self, value: Any) -> str:
        """Format a value for HCL."""
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            items = [self._format_value(v) for v in value]
            return f"[{', '.join(items)}]"
        else:
            return f'"{str(value)}"'


@dataclass
class TerraformProject:
    """Represents a complete Terraform project."""

    name: str
    main: str = ""
    variables: str = ""
    outputs: str = ""
    backend: str = ""
    versions: str = ""
    modules: dict[str, TerraformModule] = field(default_factory=dict)
    environments: dict[str, dict[str, Any]] = field(default_factory=dict)

    def write_to_filesystem(self, base_path: Path) -> None:
        """Write the project to the filesystem."""
        base_path = Path(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # Write main files
        if self.main:
            (base_path / "main.tf").write_text(self.main)

        if self.variables:
            (base_path / "variables.tf").write_text(self.variables)

        if self.outputs:
            (base_path / "outputs.tf").write_text(self.outputs)

        if self.backend:
            (base_path / "backend.tf").write_text(self.backend)

        if self.versions:
            (base_path / "versions.tf").write_text(self.versions)

        # Write modules
        if self.modules:
            modules_path = base_path / "modules"
            modules_path.mkdir(exist_ok=True)

            for module_name, module in self.modules.items():
                module_path = modules_path / module_name
                module_path.mkdir(exist_ok=True)

                # Write module files
                (module_path / "main.tf").write_text(module.to_hcl())

                if module.variables:
                    var_hcl = self._generate_variables_hcl(module.variables)
                    (module_path / "variables.tf").write_text(var_hcl)

                if module.outputs:
                    out_hcl = self._generate_outputs_hcl(module.outputs)
                    (module_path / "outputs.tf").write_text(out_hcl)

        # Write environment configs
        if self.environments:
            env_path = base_path / "environments"
            env_path.mkdir(exist_ok=True)

            for env_name, env_config in self.environments.items():
                tfvars_content = self._generate_tfvars(env_config)
                (env_path / f"{env_name}.tfvars").write_text(tfvars_content)

    def _generate_variables_hcl(self, variables: dict[str, Any]) -> str:
        """Generate variables.tf content."""
        hcl = ""
        for var_name, var_config in variables.items():
            hcl += f'variable "{var_name}" {{\n'
            if isinstance(var_config, dict):
                if "description" in var_config:
                    hcl += f'  description = "{var_config["description"]}"\n'
                if "type" in var_config:
                    hcl += f"  type        = {var_config['type']}\n"
                if "default" in var_config:
                    hcl += (
                        f"  default     = {self._format_value(var_config['default'])}\n"
                    )
            hcl += "}\n\n"
        return hcl

    def _generate_outputs_hcl(self, outputs: dict[str, Any]) -> str:
        """Generate outputs.tf content."""
        hcl = ""
        for out_name, out_config in outputs.items():
            hcl += f'output "{out_name}" {{\n'
            if isinstance(out_config, dict):
                if "description" in out_config:
                    hcl += f'  description = "{out_config["description"]}"\n'
                if "value" in out_config:
                    hcl += f"  value       = {out_config['value']}\n"
            else:
                hcl += f"  value = {out_config}\n"
            hcl += "}\n\n"
        return hcl

    def _generate_tfvars(self, config: dict[str, Any]) -> str:
        """Generate tfvars file content."""
        lines = []
        for key, value in config.items():
            if isinstance(value, str):
                lines.append(f'{key} = "{value}"')
            elif isinstance(value, (int, float, bool)):
                lines.append(f"{key} = {str(value).lower()}")
            elif isinstance(value, list):
                lines.append(f"{key} = {json.dumps(value)}")
            elif isinstance(value, dict):
                lines.append(f"{key} = {json.dumps(value, indent=2)}")
        return "\n".join(lines)

    def _format_value(self, value: Any) -> str:
        """Format a value for HCL."""
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            items = [self._format_value(v) for v in value]
            return f"[{', '.join(items)}]"
        else:
            return json.dumps(value)
