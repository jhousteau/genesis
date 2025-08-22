#!/usr/bin/env python3

"""
Auto-Fix System for Universal Project Platform
Version: 1.0.0

This module provides automated detection and fixing of common project issues.
"""

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Add the lib directory to the path for common utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib", "python"))


@dataclass
class Issue:
    """Represents a detected project issue"""

    id: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    title: str
    description: str
    auto_fixable: bool
    fix_command: Optional[str] = None
    manual_steps: Optional[List[str]] = None


class AutoFixEngine:
    """Main auto-fix engine for detecting and fixing project issues"""

    def __init__(self, project_name: str, project_path: str = None):
        self.project_name = project_name
        self.project_path = project_path or self._find_project_path(project_name)
        self.logger = self._setup_logging()
        self.issues: List[Issue] = []

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the auto-fix engine"""
        logger = logging.getLogger(f"autofix.{self.project_name}")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _find_project_path(self, project_name: str) -> str:
        """Find the project path from the registry"""
        # For now, assume projects are in the parent directory
        # In production, this would query the project registry
        possible_paths = [
            os.path.join(os.path.expanduser("~/source_code"), project_name),
            os.path.join(os.getcwd(), project_name),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        raise FileNotFoundError(f"Project '{project_name}' not found")

    def analyze(self) -> List[Issue]:
        """Analyze the project for common issues"""
        self.logger.info(f"Analyzing project: {self.project_name}")
        self.issues = []

        # Run all detectors
        self._detect_missing_files()
        self._detect_dependency_issues()
        self._detect_security_issues()
        self._detect_configuration_issues()
        self._detect_infrastructure_issues()
        self._detect_documentation_issues()

        self.logger.info(f"Found {len(self.issues)} issues")
        return self.issues

    def _detect_missing_files(self):
        """Detect missing essential files"""
        essential_files = {
            "README.md": "Project documentation",
            ".gitignore": "Git ignore file",
            "requirements.txt": "Python dependencies (if Python project)",
            "package.json": "Node.js dependencies (if Node.js project)",
            "Dockerfile": "Container configuration",
            ".env.example": "Environment variables template",
        }

        for file, description in essential_files.items():
            file_path = os.path.join(self.project_path, file)
            if not os.path.exists(file_path):
                # Determine if this file is actually needed
                if self._should_have_file(file):
                    self.issues.append(
                        Issue(
                            id=f"missing_{file.replace('.', '_')}",
                            severity="medium",
                            title=f"Missing {file}",
                            description=f"{description} is missing",
                            auto_fixable=True,
                            fix_command=f"touch {file_path}",
                        )
                    )

    def _should_have_file(self, filename: str) -> bool:
        """Determine if a project should have a specific file"""
        if filename == "requirements.txt":
            # Check if it's a Python project
            return any(
                os.path.exists(os.path.join(self.project_path, f))
                for f in ["*.py", "setup.py", "pyproject.toml"]
            )
        elif filename == "package.json":
            # Check if it's a Node.js project
            return any(
                os.path.exists(os.path.join(self.project_path, f))
                for f in ["*.js", "*.ts", "src/"]
            )

        # These files should exist for all projects
        return filename in ["README.md", ".gitignore", ".env.example"]

    def _detect_dependency_issues(self):
        """Detect dependency-related issues"""
        # Check for outdated dependencies
        if os.path.exists(os.path.join(self.project_path, "requirements.txt")):
            self._check_python_dependencies()

        if os.path.exists(os.path.join(self.project_path, "package.json")):
            self._check_node_dependencies()

    def _check_python_dependencies(self):
        """Check Python dependencies for issues"""
        req_file = os.path.join(self.project_path, "requirements.txt")

        try:
            with open(req_file, "r") as f:
                content = f.read()

            # Check for unpinned dependencies
            lines = content.strip().split("\n")
            unpinned = [
                line for line in lines if line and "==" not in line and ">=" not in line
            ]

            if unpinned:
                self.issues.append(
                    Issue(
                        id="unpinned_python_deps",
                        severity="medium",
                        title="Unpinned Python dependencies",
                        description=f"Dependencies without version pins: {', '.join(unpinned)}",
                        auto_fixable=False,
                        manual_steps=[
                            "Run 'pip freeze > requirements.txt' to pin current versions",
                            "Or manually specify version ranges for each dependency",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze requirements.txt: {e}")

    def _check_node_dependencies(self):
        """Check Node.js dependencies for issues"""
        package_file = os.path.join(self.project_path, "package.json")

        try:
            with open(package_file, "r") as f:
                package_data = json.load(f)

            # Check for missing package-lock.json
            lock_file = os.path.join(self.project_path, "package-lock.json")
            if not os.path.exists(lock_file):
                self.issues.append(
                    Issue(
                        id="missing_package_lock",
                        severity="high",
                        title="Missing package-lock.json",
                        description="Package lock file missing - dependencies not pinned",
                        auto_fixable=True,
                        fix_command="cd {} && npm install".format(self.project_path),
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze package.json: {e}")

    def _detect_security_issues(self):
        """Detect security-related issues"""
        # Check for hardcoded secrets
        self._check_for_secrets()

        # Check for insecure configurations
        self._check_security_configs()

    def _check_for_secrets(self):
        """Check for potential hardcoded secrets"""
        secret_patterns = ["password=", "secret=", "api_key=", "token=", "private_key"]

        # Scan common files for secrets
        files_to_scan = []
        for root, dirs, files in os.walk(self.project_path):
            # Skip .git and node_modules directories
            dirs[:] = [
                d for d in dirs if d not in [".git", "node_modules", "__pycache__"]
            ]

            for file in files:
                if file.endswith(
                    (".py", ".js", ".ts", ".yaml", ".yml", ".json", ".sh")
                ):
                    files_to_scan.append(os.path.join(root, file))

        for file_path in files_to_scan:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                for pattern in secret_patterns:
                    if pattern in content.lower():
                        self.issues.append(
                            Issue(
                                id=f"potential_secret_{os.path.basename(file_path)}",
                                severity="high",
                                title=f"Potential secret in {os.path.basename(file_path)}",
                                description=f"Found pattern '{pattern}' which may contain secrets",
                                auto_fixable=False,
                                manual_steps=[
                                    "Review the file for hardcoded secrets",
                                    "Move secrets to environment variables",
                                    "Add the file to .gitignore if it contains secrets",
                                ],
                            )
                        )
                        break  # Only report once per file

            except Exception as e:
                self.logger.warning(f"Could not scan {file_path}: {e}")

    def _check_security_configs(self):
        """Check for insecure configuration settings"""
        # Check Dockerfile for security issues
        dockerfile = os.path.join(self.project_path, "Dockerfile")
        if os.path.exists(dockerfile):
            self._check_dockerfile_security(dockerfile)

    def _check_dockerfile_security(self, dockerfile_path: str):
        """Check Dockerfile for security issues"""
        try:
            with open(dockerfile_path, "r") as f:
                content = f.read()

            # Check for running as root
            if "USER root" in content or "USER 0" in content:
                self.issues.append(
                    Issue(
                        id="dockerfile_root_user",
                        severity="high",
                        title="Dockerfile runs as root",
                        description="Container configured to run as root user",
                        auto_fixable=False,
                        manual_steps=[
                            "Add a non-root user to the Dockerfile",
                            "Use USER directive to switch to non-root user",
                            "Example: USER 1000:1000",
                        ],
                    )
                )

            # Check for COPY without specific ownership
            if "COPY ." in content and "--chown=" not in content:
                self.issues.append(
                    Issue(
                        id="dockerfile_copy_ownership",
                        severity="medium",
                        title="Dockerfile COPY without ownership",
                        description="COPY instructions should specify ownership",
                        auto_fixable=False,
                        manual_steps=[
                            "Add --chown flag to COPY instructions",
                            "Example: COPY --chown=1000:1000 . /app",
                        ],
                    )
                )

        except Exception as e:
            self.logger.warning(f"Could not analyze Dockerfile: {e}")

    def _detect_configuration_issues(self):
        """Detect configuration-related issues"""
        # Check for environment configuration
        self._check_environment_config()

    def _check_environment_config(self):
        """Check environment configuration"""
        env_example = os.path.join(self.project_path, ".env.example")
        env_file = os.path.join(self.project_path, ".env")

        if os.path.exists(env_file) and not os.path.exists(env_example):
            self.issues.append(
                Issue(
                    id="missing_env_example",
                    severity="medium",
                    title="Missing .env.example",
                    description=".env file exists but no .env.example template",
                    auto_fixable=True,
                    fix_command=f"cp {env_file} {env_example} && sed -i 's/=.*/=/' {env_example}",
                )
            )

    def _detect_infrastructure_issues(self):
        """Detect infrastructure-related issues"""
        # Check Terraform configurations
        self._check_terraform_config()

    def _check_terraform_config(self):
        """Check Terraform configuration for issues"""
        tf_files = []
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(".tf"):
                    tf_files.append(os.path.join(root, file))

        if not tf_files:
            return

        # Check for state backend configuration
        has_backend = False
        for tf_file in tf_files:
            try:
                with open(tf_file, "r") as f:
                    content = f.read()
                    if "backend" in content:
                        has_backend = True
                        break
            except Exception as e:
                self.logger.warning(f"Could not read {tf_file}: {e}")

        if not has_backend:
            self.issues.append(
                Issue(
                    id="terraform_no_backend",
                    severity="high",
                    title="Terraform backend not configured",
                    description="No remote state backend configured for Terraform",
                    auto_fixable=False,
                    manual_steps=[
                        "Configure a remote backend (e.g., GCS, S3)",
                        "Add backend configuration to terraform block",
                        "Run 'terraform init' to initialize backend",
                    ],
                )
            )

    def _detect_documentation_issues(self):
        """Detect documentation-related issues"""
        readme_path = os.path.join(self.project_path, "README.md")

        if os.path.exists(readme_path):
            try:
                with open(readme_path, "r") as f:
                    content = f.read()

                # Check if README is too short
                if len(content.strip()) < 100:
                    self.issues.append(
                        Issue(
                            id="readme_too_short",
                            severity="low",
                            title="README.md is too short",
                            description="README should contain project description and setup instructions",
                            auto_fixable=False,
                            manual_steps=[
                                "Add project description",
                                "Add installation instructions",
                                "Add usage examples",
                                "Add contributing guidelines",
                            ],
                        )
                    )

                # Check for missing sections
                required_sections = ["installation", "usage", "description"]
                missing_sections = []

                for section in required_sections:
                    if section.lower() not in content.lower():
                        missing_sections.append(section)

                if missing_sections:
                    self.issues.append(
                        Issue(
                            id="readme_missing_sections",
                            severity="low",
                            title="README missing sections",
                            description=f"Missing sections: {', '.join(missing_sections)}",
                            auto_fixable=False,
                            manual_steps=[
                                f"Add {section} section" for section in missing_sections
                            ],
                        )
                    )

            except Exception as e:
                self.logger.warning(f"Could not analyze README.md: {e}")

    def fix_auto_fixable_issues(self) -> Dict[str, Any]:
        """Automatically fix all auto-fixable issues"""
        results = {"fixed": [], "failed": [], "total_auto_fixable": 0}

        auto_fixable_issues = [issue for issue in self.issues if issue.auto_fixable]
        results["total_auto_fixable"] = len(auto_fixable_issues)

        self.logger.info(
            f"Attempting to fix {len(auto_fixable_issues)} auto-fixable issues"
        )

        for issue in auto_fixable_issues:
            try:
                if issue.fix_command:
                    self.logger.info(f"Fixing: {issue.title}")
                    result = subprocess.run(
                        issue.fix_command,
                        shell=True,
                        cwd=self.project_path,
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode == 0:
                        results["fixed"].append(
                            {
                                "id": issue.id,
                                "title": issue.title,
                                "command": issue.fix_command,
                            }
                        )
                        self.logger.info(f"Fixed: {issue.title}")
                    else:
                        results["failed"].append(
                            {
                                "id": issue.id,
                                "title": issue.title,
                                "error": result.stderr or result.stdout,
                            }
                        )
                        self.logger.error(
                            f"Failed to fix {issue.title}: {result.stderr}"
                        )

            except Exception as e:
                results["failed"].append(
                    {"id": issue.id, "title": issue.title, "error": str(e)}
                )
                self.logger.error(f"Failed to fix {issue.title}: {e}")

        return results

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report of all issues"""
        issues_by_severity = {"critical": [], "high": [], "medium": [], "low": []}

        for issue in self.issues:
            issues_by_severity[issue.severity].append(
                {
                    "id": issue.id,
                    "title": issue.title,
                    "description": issue.description,
                    "auto_fixable": issue.auto_fixable,
                    "fix_command": issue.fix_command,
                    "manual_steps": issue.manual_steps,
                }
            )

        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "total_issues": len(self.issues),
            "auto_fixable_count": len([i for i in self.issues if i.auto_fixable]),
            "issues_by_severity": issues_by_severity,
            "timestamp": str(subprocess.check_output(["date"], text=True).strip()),
        }


def main():
    """Main entry point for the auto-fix CLI"""
    if len(sys.argv) != 2:
        print("Usage: python fix.py <project_name>")
        sys.exit(1)

    project_name = sys.argv[1]

    try:
        # Initialize the auto-fix engine
        engine = AutoFixEngine(project_name)

        # Analyze the project
        issues = engine.analyze()

        # Generate and display report
        report = engine.generate_report()

        print(f"\n=== Auto-Fix Report for {project_name} ===")
        print(f"Total issues found: {report['total_issues']}")
        print(f"Auto-fixable issues: {report['auto_fixable_count']}")

        # Display issues by severity
        for severity in ["critical", "high", "medium", "low"]:
            severity_issues = report["issues_by_severity"][severity]
            if severity_issues:
                print(f"\n{severity.upper()} ({len(severity_issues)} issues):")
                for issue in severity_issues:
                    status = "[AUTO-FIXABLE]" if issue["auto_fixable"] else "[MANUAL]"
                    print(f"  {status} {issue['title']}")
                    print(f"    {issue['description']}")
                    if issue["auto_fixable"] and issue["fix_command"]:
                        print(f"    Fix: {issue['fix_command']}")
                    elif issue["manual_steps"]:
                        print("    Manual steps:")
                        for step in issue["manual_steps"]:
                            print(f"      - {step}")
                    print()

        # Ask user if they want to auto-fix issues
        auto_fixable_count = report["auto_fixable_count"]
        if auto_fixable_count > 0:
            response = input(
                f"\nWould you like to automatically fix {auto_fixable_count} auto-fixable issues? (y/n): "
            )
            if response.lower() in ["y", "yes"]:
                print("\nFixing auto-fixable issues...")
                fix_results = engine.fix_auto_fixable_issues()

                print("\nFix Results:")
                print(f"  Successfully fixed: {len(fix_results['fixed'])}")
                print(f"  Failed to fix: {len(fix_results['failed'])}")

                if fix_results["fixed"]:
                    print("\n  Fixed issues:")
                    for fixed in fix_results["fixed"]:
                        print(f"    ✓ {fixed['title']}")

                if fix_results["failed"]:
                    print("\n  Failed to fix:")
                    for failed in fix_results["failed"]:
                        print(f"    ✗ {failed['title']}: {failed['error']}")

        # Save report to file
        report_file = os.path.join(
            engine.project_path, ".bootstrap-autofix-report.json"
        )
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
