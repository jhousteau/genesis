#!/usr/bin/env python3
"""Genesis CLI - Main command-line interface for Genesis toolkit."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click

from .core.errors import handle_error

# Version info
__version__ = "2.0.0-dev"

# Genesis root detection
def find_genesis_root() -> Optional[Path]:
    """Find Genesis project root by looking for CLAUDE.md."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return None

def get_component_path(component: str) -> Optional[Path]:
    """Get path to a Genesis component."""
    genesis_root = find_genesis_root()
    if not genesis_root:
        return None
    
    component_path = genesis_root / component
    return component_path if component_path.exists() else None

@click.group()
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx):
    """Genesis - Development toolkit for lean, AI-safe projects."""
    ctx.ensure_object(dict)
    ctx.obj['genesis_root'] = find_genesis_root()

@cli.command()
@click.argument('name')
@click.option('--type', 'project_type', default='python-api',
              type=click.Choice(['python-api', 'typescript-service', 'cli-tool']),
              help='Project template type')
@click.option('--path', 'target_path', default=None,
              help='Directory to create project in')
@click.option('--skip-git', is_flag=True,
              help='Skip Git initialization')
@click.pass_context
def bootstrap(ctx, name: str, project_type: str, target_path: Optional[str], skip_git: bool):
    """Create new project with Genesis patterns and tooling."""
    from genesis.commands.bootstrap import bootstrap_command
    bootstrap_command(name, project_type, target_path, skip_git)

@cli.command()
@click.argument('name')
@click.argument('focus_path')
@click.option('--max-files', default=30, type=int,
              help='Maximum files in worktree')
@click.option('--verify', is_flag=True,
              help='Verify safety after creation')
@click.pass_context
def worktree(ctx, name: str, focus_path: str, max_files: int, verify: bool):
    """Create AI-safe sparse worktree with file limits."""
    genesis_root = ctx.obj.get('genesis_root')
    if not genesis_root:
        click.echo("❌ Not in a Genesis project. Run from Genesis directory.", err=True)
        sys.exit(1)
    
    worktree_script = genesis_root / "worktree-tools" / "src" / "create-sparse-worktree.sh"
    if not worktree_script.exists():
        click.echo("❌ Worktree script not found. Genesis may be incomplete.", err=True)
        sys.exit(1)
    
    # Build command arguments
    cmd = [str(worktree_script), name, focus_path, "--max-files", str(max_files)]
    if verify:
        cmd.append("--verify")
    
    try:
        result = subprocess.run(cmd, check=True)
        click.echo(f"✅ Sparse worktree '{name}' created successfully!")
    except Exception as e:
        handled_error = handle_error(e)
        click.echo(f"❌ Worktree creation failed: {handled_error.message}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--message', '-m', help='Commit message')
@click.pass_context  
def commit(ctx, message: Optional[str]):
    """Smart commit with quality gates and pre-commit hooks."""
    genesis_root = ctx.obj.get('genesis_root')
    if not genesis_root:
        click.echo("❌ Not in a Genesis project. Run from Genesis directory.", err=True)
        sys.exit(1)
    
    smart_commit_script = genesis_root / "smart-commit" / "src" / "smart-commit.sh"
    if not smart_commit_script.exists():
        click.echo("❌ Smart-commit script not found. Genesis may be incomplete.", err=True)
        sys.exit(1)
    
    # Build command arguments
    cmd = [str(smart_commit_script)]
    if message:
        # Note: smart-commit.sh handles interactive commit message entry
        # We'll need to set an environment variable or pass it differently
        os.environ['GENESIS_COMMIT_MESSAGE'] = message
    
    try:
        result = subprocess.run(cmd, check=True)
        click.echo("✅ Smart commit completed!")
    except Exception as e:
        handled_error = handle_error(e)
        click.echo(f"❌ Smart commit failed: {handled_error.message}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--worktrees', is_flag=True, help='Clean old worktrees only')
@click.option('--artifacts', is_flag=True, help='Clean build artifacts only')
@click.option('--all', 'clean_all', is_flag=True, help='Clean everything')
@click.pass_context
def clean(ctx, worktrees: bool, artifacts: bool, clean_all: bool):
    """Clean workspace: remove old worktrees and build artifacts."""
    genesis_root = ctx.obj.get('genesis_root')
    if not genesis_root:
        click.echo("❌ Not in a Genesis project. Run from Genesis directory.", err=True)
        sys.exit(1)
    
    # Default to cleaning everything if no specific flags
    if not any([worktrees, artifacts, clean_all]):
        clean_all = True
    
    cleaned_items = []
    
    # Clean old worktrees
    if worktrees or clean_all:
        worktrees_dir = genesis_root.parent / "worktrees"
        if worktrees_dir.exists():
            try:
                shutil.rmtree(worktrees_dir)
                cleaned_items.append("worktrees directory")
                click.echo("✅ Cleaned old worktrees")
            except Exception as e:
                handled_error = handle_error(e)
                click.echo(f"⚠️  Could not clean worktrees: {handled_error.message}", err=True)
    
    # Clean build artifacts
    if artifacts or clean_all:
        artifact_patterns = [
            "dist/", "build/", "*.egg-info/", "__pycache__/", 
            ".pytest_cache/", ".coverage", "coverage/", 
            "node_modules/", ".venv/", "venv/"
        ]
        
        for pattern in artifact_patterns:
            # Use find to locate and remove artifacts
            try:
                if pattern.endswith('/'):
                    # Directory patterns
                    result = subprocess.run(
                        ["find", str(genesis_root), "-type", "d", "-name", pattern.rstrip('/'), 
                         "-not", "-path", "*/old-bloated-code-read-only/*"],
                        capture_output=True, text=True
                    )
                    if result.stdout.strip():
                        for dir_path in result.stdout.strip().split('\n'):
                            if dir_path and Path(dir_path).exists():
                                shutil.rmtree(dir_path)
                                cleaned_items.append(f"artifact: {Path(dir_path).name}")
                else:
                    # File patterns  
                    result = subprocess.run(
                        ["find", str(genesis_root), "-name", pattern,
                         "-not", "-path", "*/old-bloated-code-read-only/*"],
                        capture_output=True, text=True
                    )
                    if result.stdout.strip():
                        for file_path in result.stdout.strip().split('\n'):
                            if file_path and Path(file_path).exists():
                                Path(file_path).unlink()
                                cleaned_items.append(f"artifact: {Path(file_path).name}")
            except (subprocess.CalledProcessError, OSError) as e:
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
    genesis_root = ctx.obj.get('genesis_root')
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
            click.echo(f"⚠️  Could not update shared-python: {handled_error.message}", err=True)
    
    # Check for updates to Genesis components
    components = ["bootstrap", "smart-commit", "worktree-tools"]
    for component in components:
        component_path = genesis_root / component
        if component_path.exists():
            click.echo(f"✅ {component} component available")
        else:
            click.echo(f"⚠️  {component} component missing")
    
    click.echo("✅ Sync complete!")

@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed status')
@click.pass_context
def status(ctx, verbose: bool):
    """Check Genesis project health and component status."""
    genesis_root = ctx.obj.get('genesis_root')
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
        "genesis-cli": "Main CLI interface"
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
            ["find", str(genesis_root), "-type", "f", "-not", "-path", "*/old-bloated-code-read-only/*", 
             "-not", "-path", "*/.git/*", "-not", "-path", "*/node_modules/*"],
            capture_output=True, text=True, check=True
        )
        file_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        
        if file_count <= 100:
            click.echo(f"✅ File count: {file_count} (AI-safe: ≤100)")
        else:
            click.echo(f"⚠️  File count: {file_count} (Target: ≤100 for AI safety)")
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

if __name__ == '__main__':
    cli()