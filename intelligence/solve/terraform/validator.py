"""Terraform validation and testing utilities."""

import json
import subprocess
from pathlib import Path
from typing import Optional


class TerraformValidator:
    """Validates generated Terraform configurations."""

    def __init__(self, terraform_path: str = "terraform"):
        """Initialize the validator.

        Args:
            terraform_path: Path to terraform binary
        """
        self.terraform_path = terraform_path

    def validate_project(self, project_path: Path) -> tuple[bool, list[str]]:
        """Validate a complete Terraform project.

        Args:
            project_path: Path to the Terraform project

        Returns:
            Tuple of (success, errors)
        """
        errors = []

        # Check if terraform is available
        if not self._check_terraform_installed():
            errors.append("Terraform is not installed or not in PATH")
            return False, errors

        # Run terraform fmt check
        fmt_ok, fmt_errors = self.check_formatting(project_path)
        if not fmt_ok:
            errors.extend(fmt_errors)

        # Run terraform init
        init_ok, init_errors = self.terraform_init(project_path)
        if not init_ok:
            errors.extend(init_errors)
            return False, errors  # Can't validate without init

        # Run terraform validate
        validate_ok, validate_errors = self.terraform_validate(project_path)
        if not validate_ok:
            errors.extend(validate_errors)

        return len(errors) == 0, errors

    def check_formatting(self, project_path: Path) -> tuple[bool, list[str]]:
        """Check Terraform formatting.

        Args:
            project_path: Path to the project

        Returns:
            Tuple of (success, errors)
        """
        try:
            result = subprocess.run(
                [self.terraform_path, "fmt", "-check", "-diff"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return False, [f"Formatting issues: {result.stdout}"]

            return True, []

        except subprocess.TimeoutExpired:
            return False, ["Terraform fmt check timed out"]
        except Exception as e:
            return False, [f"Error checking formatting: {str(e)}"]

    def terraform_init(self, project_path: Path) -> tuple[bool, list[str]]:
        """Initialize Terraform project.

        Args:
            project_path: Path to the project

        Returns:
            Tuple of (success, errors)
        """
        try:
            result = subprocess.run(
                [self.terraform_path, "init", "-backend=false"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return False, [f"Terraform init failed: {result.stderr}"]

            return True, []

        except subprocess.TimeoutExpired:
            return False, ["Terraform init timed out"]
        except Exception as e:
            return False, [f"Error initializing Terraform: {str(e)}"]

    def terraform_validate(self, project_path: Path) -> tuple[bool, list[str]]:
        """Validate Terraform configuration.

        Args:
            project_path: Path to the project

        Returns:
            Tuple of (success, errors)
        """
        try:
            result = subprocess.run(
                [self.terraform_path, "validate", "-json"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return True, []

            # Parse JSON output for errors
            try:
                validation_result = json.loads(result.stdout)
                errors = []

                if "diagnostics" in validation_result:
                    for diag in validation_result["diagnostics"]:
                        severity = diag.get("severity", "error")
                        summary = diag.get("summary", "Unknown error")
                        detail = diag.get("detail", "")

                        error_msg = f"{severity}: {summary}"
                        if detail:
                            error_msg += f" - {detail}"

                        errors.append(error_msg)

                return False, errors

            except json.JSONDecodeError:
                return False, [
                    f"Terraform validate failed: {result.stderr or result.stdout}"
                ]

        except subprocess.TimeoutExpired:
            return False, ["Terraform validate timed out"]
        except Exception as e:
            return False, [f"Error validating Terraform: {str(e)}"]

    def terraform_plan(
        self,
        project_path: Path,
        var_file: Optional[str] = None,
    ) -> tuple[bool, dict]:
        """Run terraform plan and analyze results.

        Args:
            project_path: Path to the project
            var_file: Optional tfvars file

        Returns:
            Tuple of (success, plan_summary)
        """
        try:
            cmd = [self.terraform_path, "plan", "-json", "-input=false"]
            if var_file:
                cmd.extend(["-var-file", var_file])

            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Parse JSON lines output
            plan_summary = {
                "resources_to_add": 0,
                "resources_to_change": 0,
                "resources_to_destroy": 0,
                "errors": [],
            }

            for line in result.stdout.splitlines():
                try:
                    event = json.loads(line)

                    if event.get("type") == "planned_change":
                        change = event.get("change", {})
                        actions = change.get("actions", [])

                        if "create" in actions:
                            plan_summary["resources_to_add"] += 1
                        elif "update" in actions:
                            plan_summary["resources_to_change"] += 1
                        elif "delete" in actions:
                            plan_summary["resources_to_destroy"] += 1

                    elif event.get("type") == "diagnostic":
                        if event.get("diagnostic", {}).get("severity") == "error":
                            plan_summary["errors"].append(
                                event["diagnostic"].get("summary", "Unknown error"),
                            )

                except json.JSONDecodeError:
                    continue

            success = len(plan_summary["errors"]) == 0
            return success, plan_summary

        except subprocess.TimeoutExpired:
            return False, {"errors": ["Terraform plan timed out"]}
        except Exception as e:
            return False, {"errors": [f"Error running terraform plan: {str(e)}"]}

    def _check_terraform_installed(self) -> bool:
        """Check if Terraform is installed.

        Returns:
            True if Terraform is available
        """
        try:
            result = subprocess.run(
                [self.terraform_path, "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            FileNotFoundError,
        ):
            return False

    def validate_resource_naming(self, project_path: Path) -> list[str]:
        """Validate resource naming conventions.

        Args:
            project_path: Path to the project

        Returns:
            List of naming issues
        """
        issues = []

        # Check all .tf files
        for tf_file in project_path.rglob("*.tf"):
            content = tf_file.read_text()

            # Check for resource naming patterns
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if line.strip().startswith("resource "):
                    parts = line.split('"')
                    if len(parts) >= 4:
                        resource_name = parts[3]

                        # Check naming conventions
                        if (
                            not resource_name.replace("_", "")
                            .replace("-", "")
                            .isalnum()
                        ):
                            issues.append(
                                f"{tf_file}:{i} - Invalid resource name: {resource_name}"
                            )

                        if resource_name.startswith("_") or resource_name.endswith("_"):
                            issues.append(
                                f"{tf_file}:{i} - Resource name should not start/end with "
                                f"underscore: {resource_name}",
                            )

        return issues

    def check_security_issues(self, project_path: Path) -> list[str]:
        """Check for common security issues.

        Args:
            project_path: Path to the project

        Returns:
            List of security issues
        """
        issues = []

        # Security patterns to check
        security_patterns = [
            ("password", "Hardcoded password found"),
            ("secret", "Hardcoded secret found"),
            ("api_key", "Hardcoded API key found"),
            ("0.0.0.0/0", "Overly permissive network access"),
            ("allUsers", "Public access configured"),
            ("allAuthenticatedUsers", "Broad authenticated access"),
        ]

        for tf_file in project_path.rglob("*.tf"):
            content = tf_file.read_text().lower()

            for pattern, message in security_patterns:
                if pattern.lower() in content:
                    # Check if it's not a variable reference
                    lines = tf_file.read_text().splitlines()
                    for i, line in enumerate(lines, 1):
                        if pattern.lower() in line.lower() and "var." not in line:
                            issues.append(f"{tf_file}:{i} - {message}")

        return issues
