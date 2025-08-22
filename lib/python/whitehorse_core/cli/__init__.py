"""
CLI Framework Module

Provides comprehensive CLI framework with typer/click integration,
configuration management, and interactive features.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import click
    import typer
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, Prompt
    from rich.table import Table

    HAS_CLI_DEPS = True
except ImportError:
    HAS_CLI_DEPS = False

from ..config import get_config
from ..errors import ValidationError, WhitehorseError
from ..logging import get_logger, setup_logging
from ..registry import ProjectRegistry

logger = get_logger(__name__)

# Initialize Rich console
console = Console() if HAS_CLI_DEPS else None


def init_cli():
    """Initialize CLI with required dependencies check."""
    if not HAS_CLI_DEPS:
        print(
            "CLI dependencies not available. Install with: pip install 'whitehorse-core[dev]'"
        )
        sys.exit(1)


# Main CLI application
app = (
    typer.Typer(
        name="whitehorse",
        help="Whitehorse Platform CLI - Universal Project Platform",
        add_completion=False,
    )
    if HAS_CLI_DEPS
    else None
)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--config-file", help="Configuration file path")
@click.option("--log-level", default="INFO", help="Log level")
@click.pass_context
def cli(ctx, debug, config_file, log_level):
    """Whitehorse Platform CLI - Universal Project Platform"""
    if not HAS_CLI_DEPS:
        init_cli()

    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["config_file"] = config_file

    # Setup logging
    setup_logging(
        service_name="whitehorse-cli",
        level=log_level.upper(),
        console_output=True,
        enable_gcp=False,  # Disable GCP logging for CLI
    )

    if debug:
        logger.info("Debug mode enabled")


@cli.group()
def project():
    """Project management commands."""
    pass


@project.command()
@click.argument("project_name")
@click.option("--type", "project_type", required=True, help="Project type")
@click.option("--language", required=True, help="Programming language")
@click.option("--team", required=True, help="Team name")
@click.option("--criticality", default="medium", help="Project criticality")
def create(project_name, project_type, language, team, criticality):
    """Create a new project."""
    init_cli()

    try:
        registry = ProjectRegistry()

        project_config = {
            "type": project_type,
            "language": language,
            "team": team,
            "criticality": criticality,
            "created_by": "cli",
            "environments": {
                "dev": {"gcp_project": f"{project_name}-dev", "region": "us-central1"},
                "staging": {
                    "gcp_project": f"{project_name}-staging",
                    "region": "us-central1",
                },
                "prod": {
                    "gcp_project": f"{project_name}-prod",
                    "region": "us-central1",
                },
            },
        }

        # Validate configuration
        errors = registry.validate_project_config(project_config)
        if errors:
            console.print("[red]Validation errors:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            sys.exit(1)

        registry.add_project(project_name, project_config)

        console.print(f"[green]✓[/green] Project '{project_name}' created successfully")

    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@project.command()
def list():
    """List all projects."""
    init_cli()

    try:
        registry = ProjectRegistry()
        projects = registry.list_projects()

        if not projects:
            console.print("No projects found.")
            return

        table = Table(title="Projects")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Language", style="green")
        table.add_column("Team", style="yellow")
        table.add_column("Criticality", style="red")

        for project_name in projects:
            try:
                project = registry.get_project(project_name)
                table.add_row(
                    project_name,
                    project.get("type", "N/A"),
                    project.get("language", "N/A"),
                    project.get("team", "N/A"),
                    project.get("criticality", "N/A"),
                )
            except Exception as e:
                logger.warning(f"Failed to load project {project_name}: {e}")

        console.print(table)

    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@project.command()
@click.argument("project_name")
def show(project_name):
    """Show detailed project information."""
    init_cli()

    try:
        registry = ProjectRegistry()
        project = registry.get_project(project_name)

        # Create panels for different sections
        basic_info = Table.grid(padding=1)
        basic_info.add_column(style="cyan", no_wrap=True)
        basic_info.add_column()

        basic_info.add_row("Type:", project.get("type", "N/A"))
        basic_info.add_row("Language:", project.get("language", "N/A"))
        basic_info.add_row("Team:", project.get("team", "N/A"))
        basic_info.add_row("Criticality:", project.get("criticality", "N/A"))

        console.print(
            Panel(basic_info, title=f"Project: {project_name}", border_style="blue")
        )

        # Environments
        environments = project.get("environments", {})
        if environments:
            env_table = Table(title="Environments")
            env_table.add_column("Environment", style="cyan")
            env_table.add_column("GCP Project", style="green")
            env_table.add_column("Region", style="yellow")

            for env_name, env_config in environments.items():
                env_table.add_row(
                    env_name,
                    env_config.get("gcp_project", "N/A"),
                    env_config.get("region", "N/A"),
                )

            console.print(env_table)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to show project: {e}")
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@cli.group()
def config():
    """Configuration management commands."""
    pass


@config.command()
def show():
    """Show current configuration."""
    init_cli()

    try:
        config = get_config()

        config_table = Table(title="Configuration")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="green")

        config_dict = config.__dict__ if hasattr(config, "__dict__") else {}

        for key, value in config_dict.items():
            if not key.startswith("_"):
                # Hide sensitive values
                if (
                    "password" in key.lower()
                    or "secret" in key.lower()
                    or "key" in key.lower()
                ):
                    value = "***"
                config_table.add_row(key, str(value))

        console.print(config_table)

    except Exception as e:
        logger.error(f"Failed to show config: {e}")
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@cli.group()
def registry():
    """Registry management commands."""
    pass


@registry.command()
def validate():
    """Validate project registry."""
    init_cli()

    try:
        registry = ProjectRegistry()
        projects = registry.list_projects()

        total_errors = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Validating projects...", total=len(projects))

            for project_name in projects:
                progress.update(task, description=f"Validating {project_name}...")

                try:
                    project = registry.get_project(project_name)
                    errors = registry.validate_project_config(project)

                    if errors:
                        console.print(f"[red]✗[/red] {project_name}:")
                        for error in errors:
                            console.print(f"    {error}")
                        total_errors += len(errors)
                    else:
                        console.print(f"[green]✓[/green] {project_name}")

                except Exception as e:
                    console.print(f"[red]✗[/red] {project_name}: {str(e)}")
                    total_errors += 1

                progress.update(task, advance=1)

        if total_errors == 0:
            console.print("\n[green]✓[/green] All projects are valid")
        else:
            console.print(f"\n[red]Found {total_errors} validation error(s)[/red]")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Failed to validate registry: {e}")
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@registry.command()
@click.option("--output", help="Output file path")
def export(output):
    """Export project registry."""
    init_cli()

    try:
        registry = ProjectRegistry()

        if output:
            data = registry.export_registry(output)
            console.print(f"[green]✓[/green] Registry exported to {output}")
        else:
            data = registry.export_registry()
            console.print_json(data=data)

    except Exception as e:
        logger.error(f"Failed to export registry: {e}")
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@cli.group()
def health():
    """Health check commands."""
    pass


@health.command()
def check():
    """Perform comprehensive health check."""
    init_cli()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running health checks...", total=3)

            # Check registry
            progress.update(task, description="Checking registry...")
            registry = ProjectRegistry()
            registry_health = registry.health_check()
            progress.update(task, advance=1)

            # Check configuration
            progress.update(task, description="Checking configuration...")
            try:
                config = get_config()
                config_health = {
                    "status": "healthy",
                    "message": "Configuration loaded successfully",
                }
            except Exception as e:
                config_health = {"status": "unhealthy", "error": str(e)}
            progress.update(task, advance=1)

            # Check logging
            progress.update(task, description="Checking logging...")
            try:
                logger.info("Health check test log")
                logging_health = {"status": "healthy", "message": "Logging working"}
            except Exception as e:
                logging_health = {"status": "unhealthy", "error": str(e)}
            progress.update(task, advance=1)

        # Display results
        health_table = Table(title="Health Check Results")
        health_table.add_column("Component", style="cyan")
        health_table.add_column("Status", style="bold")
        health_table.add_column("Details", style="white")

        components = [
            ("Registry", registry_health),
            ("Configuration", config_health),
            ("Logging", logging_health),
        ]

        all_healthy = True

        for name, health in components:
            status = health.get("status", "unknown")
            if status == "healthy":
                status_style = "[green]✓ Healthy[/green]"
            else:
                status_style = "[red]✗ Unhealthy[/red]"
                all_healthy = False

            details = health.get("message", health.get("error", ""))
            health_table.add_row(name, status_style, details)

        console.print(health_table)

        if not all_healthy:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


@cli.command()
def version():
    """Show version information."""
    from .. import __version__

    console.print(f"Whitehorse Core Library v{__version__}")


def main():
    """Main CLI entry point."""
    if HAS_CLI_DEPS:
        cli()
    else:
        init_cli()


if __name__ == "__main__":
    main()
