"""
Genesis Bootstrap Command

Project initialization functionality extracted from bootstrap shell script.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import click

from ..core.errors import (
    InfrastructureError,
    ResourceError,
    ValidationError,
    handle_error,
)
from ..core.logger import get_logger

logger = get_logger(__name__)


def find_genesis_root() -> Path | None:
    """Find Genesis project root by looking for CLAUDE.md."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return None


def get_template_path(project_type: str) -> Path | None:
    """Get path to project template."""
    genesis_root = find_genesis_root()
    if not genesis_root:
        return None

    template_path = genesis_root / "templates" / project_type
    return template_path if template_path.exists() else None


def validate_project_name(name: str) -> None:
    """Validate project name meets requirements."""
    if not name:
        raise ValidationError("Project name cannot be empty", field="name")

    if not name.replace("-", "").replace("_", "").isalnum():
        raise ValidationError(
            "Project name must contain only letters, numbers, hyphens, and underscores",
            field="name",
        )

    if name.startswith("-") or name.startswith("_"):
        raise ValidationError(
            "Project name cannot start with hyphen or underscore", field="name"
        )


def create_project_directory(project_path: Path) -> None:
    """Create project directory structure."""
    if project_path.exists():
        raise ResourceError(
            f"Directory {project_path} already exists", resource_type="directory"
        )

    try:
        project_path.mkdir(parents=True, exist_ok=False)
        logger.info(f"Created project directory: {project_path}")
    except OSError as e:
        raise InfrastructureError(
            f"Failed to create directory {project_path}: {e}"
        ) from e


def process_template_file(
    template_file: Path, target_file: Path, substitutions: dict[str, str]
) -> None:
    """Process a template file with substitutions."""
    try:
        # Read template content
        content = template_file.read_text()

        # Apply substitutions
        for placeholder, value in substitutions.items():
            content = content.replace(placeholder, value)

        # Ensure target directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Write processed content
        target_file.write_text(content)
        logger.debug(f"Processed template: {template_file} -> {target_file}")

    except Exception as e:
        raise InfrastructureError(
            f"Failed to process template {template_file}: {e}"
        ) from e


def copy_template_structure(
    template_path: Path, project_path: Path, project_name: str
) -> None:
    """Copy and process template structure."""
    from genesis.core.constants import get_git_author_info, get_python_version

    logger.info(f"Processing template from {template_path}")

    # Get dynamic values - fail fast if not available
    try:
        get_python_version()
        author_name, author_email = get_git_author_info()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise click.ClickException(f"Bootstrap failed: {e}") from e

    # Create substitution map supporting multiple template formats
    # Create Python-safe module name (replace hyphens with underscores)
    module_name = project_name.replace("-", "_")
    substitutions = {
        # Double underscore format (for filenames/directories)
        "__project_name__": project_name,
        "__PROJECT_NAME__": project_name.upper().replace("-", "_"),
        "__project-name__": project_name,
        "__module_name__": module_name,
        # Mustache format (for content)
        "{{project_name}}": project_name,
        "{{PROJECT_NAME}}": project_name.upper().replace("-", "_"),
        "{{project-name}}": project_name,
        "{{module_name}}": module_name,
        "{{project_description}}": f"A {project_name} project created with Genesis",
        "{{python_version}}": get_python_version(),
        "{{author_name}}": author_name,
        "{{author_email}}": author_email,
        "{{project_type}}": "Genesis Project",
        "{{genesis_version}}": "0.1.0-alpha",
    }

    # Process all template files
    for template_file in template_path.rglob("*.template"):
        # Calculate relative path from template root
        relative_path = template_file.relative_to(template_path)

        # Remove .template extension and apply name substitutions to path
        target_relative_path_str = str(relative_path)[:-9]  # Remove .template
        for placeholder, value in substitutions.items():
            target_relative_path_str = target_relative_path_str.replace(
                placeholder, value
            )

        target_file = project_path / target_relative_path_str
        process_template_file(template_file, target_file, substitutions)

    # Copy non-template files (like README.md in templates)
    for non_template_file in template_path.rglob("*"):
        if (
            non_template_file.is_file()
            and not non_template_file.name.endswith(".template")
            and non_template_file.name != "template.json"
        ):
            relative_path = non_template_file.relative_to(template_path)
            target_file = project_path / relative_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(non_template_file, target_file)
            logger.debug(f"Copied file: {non_template_file} -> {target_file}")


def initialize_git_repo(project_path: Path, skip_git: bool) -> None:
    """Initialize Git repository in project."""
    if skip_git:
        logger.info("Skipping Git initialization (--skip-git)")
        return

    try:
        # Check if git is available
        subprocess.run(["git", "--version"], check=True, capture_output=True)

        # Initialize repository
        subprocess.run(
            ["git", "init"], cwd=project_path, check=True, capture_output=True
        )

        # Create initial commit
        subprocess.run(
            ["git", "add", "."], cwd=project_path, check=True, capture_output=True
        )

        subprocess.run(
            ["git", "commit", "-m", "Initial commit from Genesis bootstrap"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )

        logger.info("Initialized Git repository with initial commit")

    except subprocess.CalledProcessError as e:
        logger.warning(f"Git initialization failed: {e}")
    except FileNotFoundError:
        logger.warning("Git not found - skipping repository initialization")


def bootstrap_project(
    name: str,
    project_type: str,
    target_path: str | None = None,
    skip_git: bool = False,
) -> Path:
    """Bootstrap a new project with Genesis patterns."""

    # Validate inputs
    validate_project_name(name)

    # Determine project path
    if target_path:
        project_path = Path(target_path) / name
    else:
        project_path = Path.cwd() / name

    project_path = project_path.resolve()

    # Get template path
    template_path = get_template_path(project_type)
    if not template_path:
        raise ResourceError(
            f"Template '{project_type}' not found or Genesis not detected",
            resource_type="template",
        )

    logger.info(f"Bootstrapping {project_type} project '{name}' at {project_path}")

    try:
        # Create project directory
        create_project_directory(project_path)

        # Copy and process template
        copy_template_structure(template_path, project_path, name)

        # Initialize Git repository
        initialize_git_repo(project_path, skip_git)

        logger.info(f"✅ Project '{name}' created successfully at {project_path}")
        return project_path

    except Exception as e:
        # Clean up on failure
        if project_path.exists():
            try:
                shutil.rmtree(project_path)
                logger.debug(f"Cleaned up failed project directory: {project_path}")
            except Exception:
                pass  # Best effort cleanup
        handled_error = handle_error(e)
        raise InfrastructureError(f"Bootstrap failed: {handled_error.message}") from e


# CLI command integration
def bootstrap_command(
    name: str, project_type: str, target_path: str | None, skip_git: bool
) -> None:
    """Bootstrap command implementation for CLI integration."""
    try:
        project_path = bootstrap_project(name, project_type, target_path, skip_git)
        click.echo(f"✅ Project '{name}' created at {project_path}")
        click.echo(f"📁 Type: {project_type}")
        click.echo("🚀 Ready to start development!")

    except Exception as e:
        handled_error = handle_error(e)
        click.echo(f"❌ Bootstrap failed: {handled_error.message}", err=True)
        logger.error("Bootstrap error", extra=handled_error.to_dict())
        sys.exit(1)
