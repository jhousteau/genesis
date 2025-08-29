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
def find_genesis_root() -> Path | None:
    """Find Genesis project root by looking for CLAUDE.md."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return None


def get_git_root() -> Path | None:
    """Find Git repository root."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    return None


def get_component_path(component: str) -> Path | None:
    """Get path to a Genesis component (works in dev and installed package)."""
    # First try development directory
    genesis_root = find_genesis_root()
    if genesis_root:
        component_path = genesis_root / component
        if component_path.exists():
            return component_path

    # Then try installed package
    try:
        import genesis

        package_root = Path(genesis.__file__).parent.parent
        component_path = package_root / component
        if component_path.exists():
            return component_path
    except (ImportError, AttributeError):
        pass

    return None


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx):
    """Genesis - Development toolkit for lean, AI-safe projects.

    Genesis provides automated code quality, formatting, and project management
    tools designed for AI-assisted development workflows.
    """
    ctx.ensure_object(dict)
    ctx.obj["genesis_root"] = find_genesis_root()


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
@click.pass_context
def bootstrap(
    ctx, name: str, project_type: str, target_path: str | None, skip_git: bool
):
    """Create new project with Genesis patterns and tooling."""
    from genesis.commands.bootstrap import bootstrap_command

    bootstrap_command(name, project_type, target_path, skip_git)


@cli.command()
@click.argument("name")
@click.argument("focus_path")
@click.option(
    "--max-files",
    type=int,
    help="Maximum files in worktree (default from MAX_WORKTREE_FILES)",
)
@click.option("--verify", is_flag=True, help="Verify safety after creation")
@click.pass_context
def worktree(ctx, name: str, focus_path: str, max_files: int | None, verify: bool):
    """Create AI-safe sparse worktree with file limits."""
    from genesis.core.constants import AILimits

    # Find worktree-tools component
    worktree_path = get_component_path("worktree-tools")
    if not worktree_path:
        click.echo(
            "❌ Worktree-tools component not found. Genesis may not be properly installed.",
            err=True,
        )
        sys.exit(1)

    worktree_script = worktree_path / "src" / "create-sparse-worktree.sh"
    if not worktree_script.exists():
        click.echo(f"❌ Worktree script not found at {worktree_script}", err=True)
        sys.exit(1)

    # Use configured limit if not provided
    if max_files is None:
        try:
            max_files = AILimits.get_max_worktree_files()
        except ValueError as e:
            click.echo(f"❌ Configuration error: {e}", err=True)
            sys.exit(1)

    # Build command arguments
    cmd = [str(worktree_script), name, focus_path, "--max-files", str(max_files)]
    if verify:
        cmd.append("--verify")

    try:
        subprocess.run(cmd, check=True)
        click.echo(f"✅ Sparse worktree '{name}' created successfully!")
    except Exception as e:
        handled_error = handle_error(e)
        click.echo(f"❌ Worktree creation failed: {handled_error.message}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--dry-run", is_flag=True, help="Show what would be fixed without making changes"
)
@click.option(
    "--stages",
    help="Comma-separated list of stages to run (basic,formatter,linter,validation)",
)
@click.option(
    "--max-iterations",
    type=int,
    help="Maximum convergent fixing iterations (default: 3)",
)
@click.pass_context
def autofix(ctx, dry_run: bool, stages: str | None, max_iterations: int | None):
    """Run autofix (formatting, linting) without committing changes."""
    try:
        from genesis.core.autofix import AutoFixer
        from genesis.core.errors import handle_error
    except ImportError as e:
        click.echo(f"❌ AutoFixer not available: {e}", err=True)
        sys.exit(1)

    # Set required environment variables for AutoFixer if not already set
    env_vars = {
        "AUTOFIX_MAX_ITERATIONS": str(max_iterations) if max_iterations else "3",
        "AUTOFIX_MAX_RUNS": "5",
        "AI_MAX_FILES": "30",
        "AI_SAFETY_MODE": "enforced",
        "LOG_LEVEL": "info",
    }

    for var, default_value in env_vars.items():
        if var not in os.environ:
            os.environ[var] = default_value

    try:
        fixer = AutoFixer(max_iterations=max_iterations or 3)

        if stages:
            # Run specific stages only
            stage_list = [s.strip() for s in stages.split(",")]
            result = fixer.run_stage_only(stage_list, dry_run=dry_run)
        else:
            # Run all stages
            result = fixer.run(dry_run=dry_run)

        if result.success:
            if dry_run:
                click.echo("✅ AutoFixer dry-run completed! (no changes made)")
            else:
                click.echo("✅ AutoFixer completed successfully!")
                click.echo(
                    f"📊 Executed {len(result.stage_results)} stages with {result.total_runs} total runs"
                )
        else:
            click.echo(
                f"❌ AutoFixer failed: {result.error or 'Unknown error'}", err=True
            )
            sys.exit(1)

    except Exception as e:
        handled_error = handle_error(e)
        click.echo(f"❌ AutoFixer failed: {handled_error.message}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--message", "-m", help="Commit message")
@click.pass_context
def commit(ctx, message: str | None):
    """Smart commit with quality gates and pre-commit hooks."""
    # Check if we're in a git repository
    if not Path.cwd().joinpath(".git").exists():
        click.echo(
            "❌ Not in a git repository. Initialize git first with: git init", err=True
        )
        sys.exit(1)

    # Find smart-commit script from component path
    smart_commit_path = get_component_path("smart-commit")
    if not smart_commit_path:
        click.echo(
            "❌ Smart-commit component not found. Genesis may not be properly installed.",
            err=True,
        )
        sys.exit(1)

    smart_commit_script = smart_commit_path / "src" / "smart-commit.sh"
    if not smart_commit_script.exists():
        click.echo(
            f"❌ Smart-commit script not found at {smart_commit_script}", err=True
        )
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
@click.pass_context
def clean(ctx, worktrees: bool, artifacts: bool, clean_all: bool):
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
@click.pass_context
def sync(ctx):
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
@click.pass_context
def status(ctx, verbose: bool):
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
