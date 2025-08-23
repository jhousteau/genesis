#!/usr/bin/env python3
"""
Universal Project Setup Tool
Creates consistent project structure and plumbing across all technologies
"""

import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import yaml


class ProjectSetup:
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.template_dir = Path(__file__).parent / "templates"
        self.script_dir = Path(__file__).parent / "scripts"
        self.config_dir = Path(__file__).parent / "config"

    def detect_project_type(self) -> Dict[str, str]:
        """Detect existing project characteristics"""
        detected = {
            "language": "unknown",
            "framework": "unknown",
            "has_git": False,
            "has_terraform": False,
            "has_docker": False,
        }

        # Check for language indicators
        if (self.project_path / "package.json").exists():
            detected["language"] = "javascript"
        elif (self.project_path / "pyproject.toml").exists():
            detected["language"] = "python"
        elif (self.project_path / "go.mod").exists():
            detected["language"] = "go"
        elif (self.project_path / "Cargo.toml").exists():
            detected["language"] = "rust"

        # Check for infrastructure
        detected["has_git"] = (self.project_path / ".git").exists()
        detected["has_terraform"] = any(self.project_path.glob("*.tf"))
        detected["has_docker"] = (self.project_path / "Dockerfile").exists()

        return detected

    def init_project(self, project_name: str, project_type: str, **options):
        """Initialize a new project with all standard components"""
        print(f"🚀 Initializing project: {project_name}")
        print(f"   Type: {project_type}")
        print(f"   Path: {self.project_path}")

        # Create project manifest
        manifest = {
            "version": "1.0",
            "created_by": "setup-project v1.0",
            "created_at": datetime.now().isoformat(),
            "project": {
                "name": project_name,
                "type": project_type,
                "language": options.get("language", "auto-detect"),
                "cloud_provider": options.get("cloud_provider", "gcp"),
            },
            "components": [],
            "environments": {
                "dev": {"project_id": f"{project_name}-dev"},
                "test": {"project_id": f"{project_name}-test"},
                "stage": {"project_id": f"{project_name}-stage"},
                "prod": {"project_id": f"{project_name}-prod"},
            },
        }

        # Apply components based on project type
        components = self.get_components_for_type(project_type)
        for component in components:
            self.apply_component(component, manifest, **options)
            manifest["components"].append(component)

        # Save manifest
        with open(self.project_path / ".project-config.yaml", "w") as f:
            yaml.dump(manifest, f, default_flow_style=False)

        print("✅ Project initialization complete!")
        self.run_validation()

    def get_components_for_type(self, project_type: str) -> List[str]:
        """Get list of components for project type"""
        base_components = [
            "core",
            "documentation",
            "gcp-isolation",
            "compliance",
            "ci-cd",
            "pre-commit",
            "smart-commit",
        ]

        type_specific = {
            "api": ["monitoring", "health-checks", "api-docs"],
            "web-app": ["frontend-build", "cdn", "monitoring"],
            "cli": ["distribution", "updates"],
            "library": ["packaging", "versioning"],
            "infrastructure": ["terraform", "state-management"],
        }

        return base_components + type_specific.get(project_type, [])

    def apply_component(self, component: str, manifest: Dict, **options):
        """Apply a specific component to the project"""
        print(f"   📦 Applying component: {component}")

        component_handlers = {
            "core": self.apply_core,
            "documentation": self.apply_documentation,
            "gcp-isolation": self.apply_gcp_isolation,
            "compliance": self.apply_compliance,
            "ci-cd": self.apply_ci_cd,
            "pre-commit": self.apply_pre_commit,
            "smart-commit": self.apply_smart_commit,
            "monitoring": self.apply_monitoring,
        }

        handler = component_handlers.get(component)
        if handler:
            handler(manifest, **options)

    def apply_core(self, manifest: Dict, **options):
        """Apply core project structure"""
        # Create standard directories
        dirs = [
            "src",
            "tests",
            "docs",
            "scripts",
            "temp",
            "config",
            ".github/workflows",
        ]
        for dir_name in dirs:
            (self.project_path / dir_name).mkdir(parents=True, exist_ok=True)

        # Copy core templates
        self.copy_template("plumbing/Makefile", "Makefile", manifest)
        self.copy_template("plumbing/.editorconfig", ".editorconfig", manifest)
        self.copy_template("plumbing/.gitignore.template", ".gitignore", manifest)
        self.copy_template("plumbing/.envrc", ".envrc", manifest)

    def apply_documentation(self, manifest: Dict, **options):
        """Apply documentation templates"""
        self.copy_template("documentation/README.md", "README.md", manifest)
        self.copy_template("documentation/CHANGELOG.md", "CHANGELOG.md", manifest)
        self.copy_template("documentation/CONTRIBUTING.md", "CONTRIBUTING.md", manifest)
        self.copy_template("documentation/SECURITY.md", "SECURITY.md", manifest)
        self.copy_template("documentation/CLAUDE.md", "CLAUDE.md", manifest)

        # Create docs structure
        docs_structure = [
            "docs/ARCHITECTURE.md",
            "docs/API.md",
            "docs/DEPLOYMENT.md",
            "docs/DEVELOPMENT.md",
            "docs/TROUBLESHOOTING.md",
            "docs/decisions/ADR-001-project-setup.md",
            "docs/runbooks/incident-response.md",
            "docs/runbooks/rollback.md",
            "docs/runbooks/debugging.md",
        ]

        for doc_path in docs_structure:
            self.copy_template(f"documentation/{doc_path}", doc_path, manifest)

    def apply_gcp_isolation(self, manifest: Dict, **options):
        """Apply GCP isolation configuration"""
        project_name = manifest["project"]["name"]

        # Copy GCP scripts
        self.copy_template(
            "gcp/bootstrap_gcloud.sh", "scripts/bootstrap_gcloud.sh", manifest
        )
        self.copy_template("gcp/gcloud_guard.sh", "scripts/gcloud_guard.sh", manifest)

        # Make scripts executable
        for script in ["bootstrap_gcloud.sh", "gcloud_guard.sh"]:
            script_path = self.project_path / "scripts" / script
            if script_path.exists():
                script_path.chmod(0o755)

        # Update .envrc with GCP settings
        envrc_content = self.render_template("gcp/.envrc", manifest)
        with open(self.project_path / ".envrc", "a") as f:
            f.write("\n" + envrc_content)

    def apply_compliance(self, manifest: Dict, **options):
        """Apply compliance validation"""
        self.copy_template(
            "compliance/validate-compliance.sh",
            "scripts/validate-compliance.sh",
            manifest,
        )
        self.copy_template("compliance/cleanup.sh", "scripts/cleanup.sh", manifest)
        self.copy_template(
            "compliance/.project-hygiene.yaml", ".project-hygiene.yaml", manifest
        )

        # Make scripts executable
        for script in ["validate-compliance.sh", "cleanup.sh"]:
            script_path = self.project_path / "scripts" / script
            if script_path.exists():
                script_path.chmod(0o755)

    def apply_ci_cd(self, manifest: Dict, **options):
        """Apply CI/CD pipelines"""
        self.copy_template(
            "ci-cd/github/compliance.yml", ".github/workflows/compliance.yml", manifest
        )
        self.copy_template(
            "ci-cd/github/deploy.yml", ".github/workflows/deploy.yml", manifest
        )
        self.copy_template(
            "ci-cd/github/pr-validation.yml",
            ".github/workflows/pr-validation.yml",
            manifest,
        )

    def apply_pre_commit(self, manifest: Dict, **options):
        """Apply pre-commit hooks"""
        self.copy_template(
            "compliance/.pre-commit-config.yaml", ".pre-commit-config.yaml", manifest
        )

    def apply_smart_commit(self, manifest: Dict, **options):
        """Apply smart commit system"""
        self.copy_template(
            "plumbing/smart-commit.sh", "scripts/smart-commit.sh", manifest
        )
        script_path = self.project_path / "scripts" / "smart-commit.sh"
        if script_path.exists():
            script_path.chmod(0o755)

    def apply_monitoring(self, manifest: Dict, **options):
        """Apply monitoring configuration"""
        self.copy_template(
            "plumbing/monitoring.yaml", "config/monitoring.yaml", manifest
        )
        self.copy_template("plumbing/alerts.yaml", "config/alerts.yaml", manifest)

    def copy_template(self, template_path: str, dest_path: str, manifest: Dict):
        """Copy and render a template file"""
        src = self.template_dir / template_path
        dest = self.project_path / dest_path

        if not src.exists():
            # Create placeholder if template doesn't exist yet
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(
                f"# Generated by setup-project\n# Template placeholder for {template_path}\n# This will be populated when the template is available\n"
            )
            return

        dest.parent.mkdir(parents=True, exist_ok=True)

        # Read and render template
        content = self.render_template(template_path, manifest)
        dest.write_text(content)

    def render_template(self, template_path: str, manifest: Dict) -> str:
        """Render a template with variables"""
        src = self.template_dir / template_path

        if not src.exists():
            return f"# Template not found: {template_path}\n# This placeholder will be replaced when the template becomes available\n"

        content = src.read_text()

        # Replace variables
        replacements = {
            "${PROJECT_NAME}": manifest["project"]["name"],
            "${PROJECT_TYPE}": manifest["project"]["type"],
            "${CREATED_AT}": manifest["created_at"],
            "${PROJECT_ID}": manifest["project"]["name"],
        }

        for key, value in replacements.items():
            content = content.replace(key, value)

        return content

    def run_validation(self):
        """Run compliance validation"""
        validation_script = self.project_path / "scripts" / "validate-compliance.sh"
        if validation_script.exists():
            print("\n🔍 Running compliance validation...")
            result = subprocess.run(
                [str(validation_script)], capture_output=True, text=True
            )
            print(result.stdout)
            if result.returncode != 0:
                print("⚠️  Some validation checks failed. Please review and fix.")

    def upgrade(self):
        """Upgrade existing project to latest standards"""
        print("📈 Upgrading project to latest standards...")

        # Load existing manifest
        manifest_path = self.project_path / ".project-config.yaml"
        if not manifest_path.exists():
            print("❌ No project manifest found. Run 'init' first.")
            return

        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        # Check for missing components
        current_components = manifest.get("components", [])
        recommended = self.get_components_for_type(manifest["project"]["type"])

        missing = set(recommended) - set(current_components)
        if missing:
            print(f"📦 Adding missing components: {', '.join(missing)}")
            for component in missing:
                self.apply_component(component, manifest)
                manifest["components"].append(component)

        # Update manifest
        manifest["last_upgraded"] = datetime.now().isoformat()
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f, default_flow_style=False)

        print("✅ Upgrade complete!")
        self.run_validation()


def main():
    parser = argparse.ArgumentParser(description="Universal Project Setup Tool")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize new project")
    init_parser.add_argument("--name", required=True, help="Project name")
    init_parser.add_argument(
        "--type",
        choices=["api", "web-app", "cli", "library", "infrastructure"],
        default="api",
        help="Project type",
    )
    init_parser.add_argument(
        "--language",
        choices=["python", "javascript", "go", "auto"],
        default="auto",
        help="Primary language",
    )
    init_parser.add_argument(
        "--cloud",
        choices=["gcp", "aws", "azure", "local"],
        default="gcp",
        help="Cloud provider",
    )

    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply specific components")
    apply_parser.add_argument(
        "--components", required=True, help="Comma-separated list of components"
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate project compliance"
    )

    # Upgrade command
    upgrade_parser = subparsers.add_parser(
        "upgrade", help="Upgrade to latest standards"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    setup = ProjectSetup()

    if args.command == "init":
        setup.init_project(
            project_name=args.name,
            project_type=args.type,
            language=args.language,
            cloud_provider=args.cloud,
        )
    elif args.command == "apply":
        # Load manifest
        manifest_path = Path(".project-config.yaml")
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
        else:
            manifest = {"project": {"name": "unknown"}, "components": []}

        components = args.components.split(",")
        for component in components:
            setup.apply_component(component.strip(), manifest)

        # Save updated manifest
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f, default_flow_style=False)

    elif args.command == "validate":
        setup.run_validation()

    elif args.command == "upgrade":
        setup.upgrade()


if __name__ == "__main__":
    main()
