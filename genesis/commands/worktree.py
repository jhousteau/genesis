"""Genesis worktree command implementation."""

import os
import subprocess
import sys
from pathlib import Path

import click

from ..core.errors import handle_error


def get_component_path(component_name: str) -> Path | None:
    """Find Genesis component path."""
    # Try relative to CLI file first (for development)
    cli_path = Path(__file__)
    component_path = cli_path.parent.parent.parent / component_name
    if component_path.exists():
        return component_path

    # Try current directory (if we're in Genesis project)
    current_path = Path.cwd() / component_name
    if current_path.exists():
        return current_path

    return None


@click.group()
def worktree():
    """Manage AI-safe sparse worktrees for focused development."""
    pass


@worktree.command()
@click.argument("name")
@click.argument("focus_path")
@click.option(
    "--max-files",
    type=int,
    help="Maximum number of files (defaults to AI_MAX_FILES env var or 30)",
)
@click.option("--verify", is_flag=True, help="Verify safety after creation")
def create(name: str, focus_path: str, max_files: int | None, verify: bool):
    """Create a new sparse worktree focused on a specific path.

    NAME: Worktree name (e.g., fix-auth, update-tests)
    FOCUS_PATH: Path to focus on (file or directory)
    """
    # Check if we're in a git repository
    try:
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, check=True
        )
    except subprocess.CalledProcessError:
        click.echo("❌ Not in a git repository", err=True)
        sys.exit(1)

    # Find worktree-tools script
    worktree_tools_path = get_component_path("worktree-tools")
    if not worktree_tools_path:
        click.echo("❌ Worktree-tools component not found", err=True)
        sys.exit(1)

    script_path = worktree_tools_path / "src" / "create-sparse-worktree.sh"
    if not script_path.exists():
        click.echo(f"❌ Worktree script not found at {script_path}", err=True)
        sys.exit(1)

    # Set environment variables
    env = os.environ.copy()
    if max_files:
        env["AI_MAX_FILES"] = str(max_files)
    elif "AI_MAX_FILES" not in env:
        env["AI_MAX_FILES"] = "30"

    # Build command
    cmd = [str(script_path), name, focus_path]
    if max_files:
        cmd.extend(["--max-files", str(max_files)])
    if verify:
        cmd.append("--verify")

    try:
        subprocess.run(cmd, env=env, check=True, cwd=os.getcwd())
        click.echo(f"✅ Sparse worktree '{name}' created successfully!")
    except subprocess.CalledProcessError as e:
        handled_error = handle_error(e)
        click.echo(f"❌ Failed to create worktree: {handled_error.message}", err=True)
        sys.exit(1)


@worktree.command()
@click.option("--all", is_flag=True, help="List all worktrees (not just Genesis ones)")
def list(all: bool):
    """List existing worktrees."""
    try:
        # Get worktree list
        result = subprocess.run(
            ["git", "worktree", "list"], capture_output=True, text=True, check=True
        )

        if not result.stdout.strip():
            click.echo("No worktrees found")
            return

        click.echo("Existing worktrees:")
        lines = result.stdout.strip().split("\n")

        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                path = parts[0]
                branch = parts[1] if len(parts) > 1 else "unknown"

                # Skip main repo entry unless --all specified
                if not all and "[" not in line:
                    continue

                # Check if it's a Genesis sparse worktree
                manifest_path = Path(path) / ".ai-safety-manifest"
                if manifest_path.exists():
                    click.echo(f"  🛡️  {Path(path).name} -> {branch} (AI-safe)")
                elif all:
                    click.echo(f"  📁 {Path(path).name} -> {branch}")

    except subprocess.CalledProcessError as e:
        handled_error = handle_error(e)
        click.echo(f"❌ Failed to list worktrees: {handled_error.message}", err=True)
        sys.exit(1)


@worktree.command()
@click.argument("name")
@click.option(
    "--force", is_flag=True, help="Force removal even with uncommitted changes"
)
def remove(name: str, force: bool):
    """Remove a worktree by name."""
    # Find worktree path
    worktree_path = Path(f"worktrees/{name}")

    if not worktree_path.exists():
        click.echo(f"❌ Worktree '{name}' not found at {worktree_path}", err=True)
        sys.exit(1)

    try:
        cmd = ["git", "worktree", "remove", str(worktree_path)]
        if force:
            cmd.append("--force")

        subprocess.run(cmd, check=True)
        click.echo(f"✅ Removed worktree '{name}'")

    except subprocess.CalledProcessError as e:
        handled_error = handle_error(e)
        click.echo(f"❌ Failed to remove worktree: {handled_error.message}", err=True)
        sys.exit(1)


@worktree.command()
@click.argument("name")
def info(name: str):
    """Show information about a specific worktree."""
    worktree_path = Path(f"worktrees/{name}")

    if not worktree_path.exists():
        click.echo(f"❌ Worktree '{name}' not found", err=True)
        sys.exit(1)

    # Read AI safety manifest if it exists
    manifest_path = worktree_path / ".ai-safety-manifest"
    if manifest_path.exists():
        click.echo(f"🛡️  AI-Safe Worktree: {name}")
        click.echo("─" * 40)

        try:
            with open(manifest_path) as f:
                content = f.read()
                # Extract key info from manifest
                lines = content.split("\n")
                for line in lines:
                    if (
                        line.startswith("Focus:")
                        or line.startswith("Files:")
                        or line.startswith("Branch:")
                        or line.startswith("Created:")
                    ):
                        click.echo(f"  {line}")
        except Exception:
            click.echo("  Error reading manifest")
    else:
        click.echo(f"📁 Standard Worktree: {name}")

    # Show git status
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=worktree_path,
        )

        if result.stdout.strip():
            click.echo("\n  Modified files:")
            for line in result.stdout.strip().split("\n"):
                click.echo(f"    {line}")
        else:
            click.echo("\n  ✅ No uncommitted changes")

    except subprocess.CalledProcessError:
        click.echo("\n  ⚠️  Could not check git status")
