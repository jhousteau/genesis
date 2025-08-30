#!/usr/bin/env python3
"""Genesis CLI - Main command-line interface for Genesis toolkit."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import click

# Import version from package
from genesis import __version__
from genesis.commands.version import version

from .core.errors import handle_error


# Genesis root detection
def get_git_root() -> Path | None:
    """Find Git repository root."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    return None


@click.group()
@click.version_option(version=__version__)
def cli():
    """Genesis - Development toolkit for lean, AI-safe projects."""
    pass


@cli.command()
@click.argument("name")
@click.option(
    "--type",
    "project_type",
    required=True,
    type=click.Choice(["python-api", "typescript-service", "cli-tool"]),
    help="Project template type (required)",
)
@click.option(
    "--path", "target_path", default=None, help="Directory to create project in"
)
@click.option("--skip-git", is_flag=True, help="Skip Git initialization")
def bootstrap(name: str, project_type: str, target_path: str | None, skip_git: bool):
    """Create new project with Genesis patterns and tooling."""
    from genesis.commands.bootstrap import bootstrap_command

    bootstrap_command(name, project_type, target_path, skip_git)


# Worktree functionality removed - use direct script calls instead
# Direct usage: /path/to/genesis/worktree-tools/src/create-sparse-worktree.sh <name> <focus_path> --max-files <n> --verify


@cli.command()
@click.option("--message", "-m", help="Commit message")
def commit(message: str | None):
    """Smart commit with quality gates and pre-commit hooks."""
    # Check if we're in a git repository
    if not Path.cwd().joinpath(".git").exists():
        click.echo(
            "❌ Not in a git repository. Initialize git first with: git init", err=True
        )
        sys.exit(1)

    # Try to find smart-commit script relative to CLI file
    cli_path = Path(__file__)
    smart_commit_script = (
        cli_path.parent.parent / "smart-commit" / "src" / "smart-commit.sh"
    )

    if not smart_commit_script.exists():
        click.echo(
            "❌ Smart-commit script not found. Use direct call instead:", err=True
        )
        click.echo("   /path/to/genesis/smart-commit/src/smart-commit.sh", err=True)
        sys.exit(1)

    # Set required environment variables for AutoFixer if not already set
    env_vars = {
        "AUTOFIX_MAX_ITERATIONS": "3",
        "AUTOFIX_MAX_RUNS": "5",
        "AI_MAX_FILES": "30",
        "AI_SAFETY_MODE": "enforced",
        "LOG_LEVEL": "info",
    }

    for var, default_value in env_vars.items():
        if var not in os.environ:
            os.environ[var] = default_value

    # Build command arguments
    cmd = [str(smart_commit_script)]
    if message:
        os.environ["COMMIT_MESSAGE"] = message

    try:
        subprocess.run(cmd, check=True)
        click.echo("✅ Smart commit completed!")
    except Exception as e:
        handled_error = handle_error(e)
        click.echo(f"❌ Smart commit failed: {handled_error.message}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--worktrees", is_flag=True, help="Clean old worktrees only")
@click.option("--artifacts", is_flag=True, help="Clean build artifacts only")
@click.option("--all", "clean_all", is_flag=True, help="Clean everything")
def clean(worktrees: bool, artifacts: bool, clean_all: bool):
    """Clean workspace: remove old worktrees and build artifacts."""
    # Get the current repo root instead of genesis_root
    repo_root = get_git_root()
    if not repo_root:
        raise click.ClickException("Not in a Git repository")

    # Default to cleaning everything if no specific flags
    if not any([worktrees, artifacts, clean_all]):
        clean_all = True

    cleaned_items = []

    # Clean old worktrees
    if worktrees or clean_all:
        worktrees_dir = repo_root.parent / "worktrees"
        if worktrees_dir.exists():
            try:
                shutil.rmtree(worktrees_dir)
                cleaned_items.append("worktrees directory")
                click.echo("✅ Cleaned old worktrees")
            except Exception as e:
                handled_error = handle_error(e)
                click.echo(
                    f"⚠️  Could not clean worktrees: {handled_error.message}", err=True
                )

    # Clean build artifacts
    if artifacts or clean_all:
        artifact_patterns = [
            "dist/",
            "build/",
            "*.egg-info/",
            "__pycache__/",
            ".pytest_cache/",
            ".coverage",
            "coverage/",
            "node_modules/",
            ".venv/",
            "venv/",
        ]

        for pattern in artifact_patterns:
            # Use find to locate and remove artifacts
            try:
                if pattern.endswith("/"):
                    # Directory patterns
                    result = subprocess.run(
                        [
                            "find",
                            str(repo_root),
                            "-type",
                            "d",
                            "-name",
                            pattern.rstrip("/"),
                            "-not",
                            "-path",
                            "*/old-bloated-code-read-only/*",
                        ],
                        capture_output=True,
                        text=True,
                    )
                    if result.stdout.strip():
                        for dir_path in result.stdout.strip().split("\n"):
                            if dir_path and Path(dir_path).exists():
                                shutil.rmtree(dir_path)
                                cleaned_items.append(f"artifact: {Path(dir_path).name}")
                else:
                    # File patterns
                    result = subprocess.run(
                        [
                            "find",
                            str(repo_root),
                            "-name",
                            pattern,
                            "-not",
                            "-path",
                            "*/old-bloated-code-read-only/*",
                        ],
                        capture_output=True,
                        text=True,
                    )
                    if result.stdout.strip():
                        for file_path in result.stdout.strip().split("\n"):
                            if file_path and Path(file_path).exists():
                                Path(file_path).unlink()
                                cleaned_items.append(
                                    f"artifact: {Path(file_path).name}"
                                )
            except (subprocess.CalledProcessError, OSError):
                # Continue with other patterns if one fails
                pass

        if any("artifact:" in item for item in cleaned_items):
            click.echo("✅ Cleaned build artifacts")

    if cleaned_items:
        click.echo(f"🧹 Cleaned: {', '.join(cleaned_items)}")
        click.echo("✅ Workspace cleanup complete!")
    else:
        click.echo("✨ Workspace is already clean!")


@cli.command()
def sync():
    """Update shared components and dependencies."""
    genesis_root = ctx.obj.get("genesis_root")
    if not genesis_root:
        click.echo("❌ Not in a Genesis project. Run from Genesis directory.", err=True)
        sys.exit(1)

    click.echo("🔄 Syncing shared components...")

    # Update shared-python if it exists
    shared_python = genesis_root / "shared-python"
    if shared_python.exists():
        try:
            os.chdir(shared_python)
            subprocess.run(["poetry", "install"], check=True, capture_output=True)
            click.echo("✅ Updated shared-python dependencies")
        except Exception as e:
            handled_error = handle_error(e)
            click.echo(
                f"⚠️  Could not update shared-python: {handled_error.message}", err=True
            )

    # Check for updates to Genesis components
    components = ["bootstrap", "smart-commit", "worktree-tools"]
    for component in components:
        component_path = genesis_root / component
        if component_path.exists():
            click.echo(f"✅ {component} component available")
        else:
            click.echo(f"⚠️  {component} component missing")

    click.echo("✅ Sync complete!")


cli.add_command(version)


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed status")
def status(verbose: bool):
    """Check Genesis project health and component status."""
    genesis_root = ctx.obj.get("genesis_root")
    if not genesis_root:
        click.echo("❌ Not in a Genesis project")
        sys.exit(1)

    click.echo(f"📍 Genesis root: {genesis_root}")

    # Check core components
    components = {
        "bootstrap": "Project initialization system",
        "smart-commit": "Quality gates before commits",
        "worktree-tools": "AI-safe sparse worktree creation",
        "shared-python": "Common Python utilities",
        "genesis-cli": "Main CLI interface",
    }

    all_healthy = True
    for component, description in components.items():
        component_path = genesis_root / component
        if component_path.exists():
            if verbose:
                click.echo(f"✅ {component}: {description}")
            else:
                click.echo(f"✅ {component}")
        else:
            click.echo(f"❌ {component}: Missing")
            all_healthy = False

    # Check file count for AI safety
    try:
        result = subprocess.run(
            [
                "find",
                str(genesis_root),
                "-type",
                "f",
                "-not",
                "-path",
                "*/old-bloated-code-read-only/*",
                "-not",
                "-path",
                "*/.git/*",
                "-not",
                "-path",
                "*/node_modules/*",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        file_count = (
            len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        )

        try:
            from genesis.core.constants import AILimits

            max_files = AILimits.get_max_project_files()

            if file_count <= max_files:
                click.echo(f"✅ File count: {file_count} (AI-safe: ≤{max_files})")
            else:
                click.echo(
                    f"⚠️  File count: {file_count} (Target: ≤{max_files} for AI safety)"
                )
                all_healthy = False
        except ValueError as e:
            click.echo(f"⚠️  Could not check file limits: {e}")
            all_healthy = False
    except Exception as e:
        handled_error = handle_error(e)
        click.echo(f"⚠️  Could not check file count: {handled_error.message}")
        all_healthy = False

    # Overall health
    if all_healthy:
        click.echo("🎉 Genesis project is healthy!")
    else:
        click.echo("⚠️  Genesis project has issues")
        sys.exit(1)


if __name__ == "__main__":
    cli()
