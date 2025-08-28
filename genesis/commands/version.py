"""Genesis Version Management Commands"""

import json
import tomllib
from pathlib import Path
from typing import Optional

import click

from genesis.core.version import (
    bump_version,
    get_project_version,
    sync_version_to_files,
)


@click.group()
def version():
    """Version management utilities."""
    pass


@version.command("show")
@click.option("--project", "-p", help="Project path (default: current directory)")
def show_version(project: Optional[str]):
    """Show current project version."""
    project_path = Path(project) if project else Path.cwd()

    try:
        current_version = get_project_version(project_path)
        click.echo(f"Current version: {current_version}")
    except FileNotFoundError:
        click.echo("❌ No pyproject.toml found", err=True)
        exit(1)
    except KeyError:
        click.echo("❌ No version found in pyproject.toml", err=True)
        exit(1)


@version.command("sync")
@click.option("--project", "-p", help="Project path (default: current directory)")
@click.option("--dry-run", is_flag=True, help="Show what would be synced")
def sync_version(project: Optional[str], dry_run: bool):
    """Synchronize version across all project files."""
    project_path = Path(project) if project else Path.cwd()

    try:
        current_version = get_project_version(project_path)
        click.echo(f"Syncing version: {current_version}")

        if dry_run:
            click.echo("Files that would be updated:")
            # Check package.json
            package_json = project_path / "package.json"
            if package_json.exists():
                click.echo(f"  - {package_json}")

            # Check __init__.py files
            for init_file in project_path.rglob("__init__.py"):
                content = init_file.read_text()
                if "__version__" in content:
                    click.echo(f"  - {init_file}")
        else:
            results = sync_version_to_files(project_path, current_version)

            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            if success_count > 0:
                click.echo(f"✅ Synced version to {success_count}/{total_count} files:")
                for file_path, success in results.items():
                    status = "✅" if success else "❌"
                    click.echo(f"  {status} {file_path}")
            else:
                click.echo("📝 No files needed version sync")

    except FileNotFoundError:
        click.echo("❌ No pyproject.toml found", err=True)
        exit(1)
    except KeyError:
        click.echo("❌ No version found in pyproject.toml", err=True)
        exit(1)


@version.command("bump")
@click.argument(
    "bump_type", type=click.Choice(["major", "minor", "patch", "alpha", "beta", "rc"])
)
@click.option("--project", "-p", help="Project path (default: current directory)")
@click.option(
    "--sync", is_flag=True, help="Auto-sync to other files (default: enabled)"
)
@click.option("--dry-run", is_flag=True, help="Show what version would be bumped to")
def bump_version_cmd(bump_type: str, project: Optional[str], sync: bool, dry_run: bool):
    """Bump version and optionally sync to other files."""
    project_path = Path(project) if project else Path.cwd()
    pyproject_path = project_path / "pyproject.toml"

    try:
        current_version = get_project_version(project_path)
        new_version = bump_version(current_version, bump_type)

        click.echo(f"Version bump: {current_version} → {new_version}")

        if dry_run:
            click.echo("This is a dry run - no changes would be made")
            if sync:
                click.echo("Would also sync to other project files")
            return

        # Update pyproject.toml
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Update the version in the data structure
        if "tool" in data and "poetry" in data["tool"]:
            data["tool"]["poetry"]["version"] = new_version
        elif "project" in data:
            data["project"]["version"] = new_version
        else:
            data["version"] = new_version

        # Write back to pyproject.toml
        import tomli_w

        with open(pyproject_path, "wb") as f:
            tomli_w.dump(data, f)

        click.echo(f"✅ Updated {pyproject_path}")

        # Sync to other files by default (explicit behavior)
        if sync:
            results = sync_version_to_files(project_path, new_version)
            success_count = sum(1 for success in results.values() if success)
            if success_count > 0:
                click.echo(f"✅ Synced to {success_count} additional files")

        click.echo(f"🎉 Version bumped to {new_version}")

    except FileNotFoundError:
        click.echo("❌ No pyproject.toml found", err=True)
        exit(1)
    except KeyError:
        click.echo("❌ No version found in pyproject.toml", err=True)
        exit(1)
    except ModuleNotFoundError:
        click.echo(
            "❌ tomli-w required for version bumping. Install with: pip install tomli-w",
            err=True,
        )
        exit(1)
    except Exception as e:
        click.echo(f"❌ Error bumping version: {e}", err=True)
        exit(1)


@version.command("check")
@click.option("--project", "-p", help="Project path (default: current directory)")
def check_version_consistency(project: Optional[str]):
    """Check version consistency across project files."""
    project_path = Path(project) if project else Path.cwd()

    try:
        main_version = get_project_version(project_path)
        click.echo(f"Main version (pyproject.toml): {main_version}")

        inconsistencies = []

        # Check package.json
        package_json = project_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                package_version = data.get("version", "")
                if package_version != main_version:
                    inconsistencies.append(f"package.json: {package_version}")
                else:
                    click.echo(f"✅ package.json: {package_version}")
            except Exception as e:
                inconsistencies.append(f"package.json: error reading ({e})")

        # Check __init__.py files (exclude virtual environments and external packages)
        for init_file in project_path.rglob("__init__.py"):
            # Skip virtual environments and external packages
            relative_path = init_file.relative_to(project_path)
            path_parts = relative_path.parts

            # Skip common virtual environment and package directories
            skip_dirs = {
                ".venv",
                "venv",
                "env",
                ".env",
                "node_modules",
                "site-packages",
                ".git",
            }
            if any(part in skip_dirs for part in path_parts):
                continue

            try:
                content = init_file.read_text()
                if "__version__" in content:
                    import re

                    version_match = re.search(
                        r'__version__\s*=\s*["\']([^"\']*)["\']', content
                    )
                    if version_match:
                        file_version = version_match.group(1)
                        if file_version != main_version:
                            inconsistencies.append(f"{relative_path}: {file_version}")
                        else:
                            click.echo(f"✅ {relative_path}: {file_version}")
            except Exception:
                pass

        if inconsistencies:
            click.echo("\n❌ Version inconsistencies found:")
            for inconsistency in inconsistencies:
                click.echo(f"  - {inconsistency}")
            click.echo("\nRun 'genesis version sync' to fix inconsistencies")
            exit(1)
        else:
            click.echo("\n🎉 All versions are consistent!")

    except FileNotFoundError:
        click.echo("❌ No pyproject.toml found", err=True)
        exit(1)
    except KeyError:
        click.echo("❌ No version found in pyproject.toml", err=True)
        exit(1)
