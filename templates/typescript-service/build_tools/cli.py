"""
Genesis TypeScript Build CLI

Command-line interface for TypeScript service build operations,
integrating npm/yarn with Genesis deployment patterns.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click

from .builder import TypeScriptBuilder
from .config import BuildConfig
from .deployer import GCPDeployer
from .tester import TestRunner


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.pass_context
def main(ctx: click.Context, verbose: bool, config: Optional[str]) -> None:
    """Genesis TypeScript Build Tools CLI"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    # Load configuration
    if config:
        config_path = Path(config)
    else:
        config_path = Path.cwd() / "build-config.yaml"
        if not config_path.exists():
            config_path = Path.cwd() / "build-config.json"

    if config_path.exists():
        ctx.obj["config"] = BuildConfig.load(config_path)
    else:
        ctx.obj["config"] = BuildConfig.default()


@main.command()
@click.option("--env", default="development", help="Environment to build for")
@click.option("--clean", is_flag=True, help="Clean build artifacts first")
@click.option("--watch", is_flag=True, help="Watch for changes and rebuild")
@click.pass_context
def build(ctx: click.Context, env: str, clean: bool, watch: bool) -> None:
    """Build TypeScript service"""
    config = ctx.obj["config"]
    builder = TypeScriptBuilder(config, verbose=ctx.obj["verbose"])

    try:
        if clean:
            click.echo("🧹 Cleaning build artifacts...")
            builder.clean()

        click.echo(f"🔨 Building for environment: {env}")

        if watch:
            click.echo("👀 Watching for changes...")
            builder.build_watch(env)
        else:
            success = builder.build(env)
            if success:
                click.echo("✅ Build completed successfully")
            else:
                click.echo("❌ Build failed")
                sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Build error: {e}")
        if ctx.obj["verbose"]:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    "--type",
    "test_type",
    default="all",
    type=click.Choice(["unit", "integration", "e2e", "all"]),
    help="Type of tests to run",
)
@click.option("--coverage", is_flag=True, help="Generate coverage report")
@click.option("--watch", is_flag=True, help="Watch for changes and re-run tests")
@click.option("--parallel", is_flag=True, help="Run tests in parallel")
@click.pass_context
def test(
    ctx: click.Context, test_type: str, coverage: bool, watch: bool, parallel: bool
) -> None:
    """Run TypeScript tests"""
    config = ctx.obj["config"]
    runner = TestRunner(config, verbose=ctx.obj["verbose"])

    try:
        click.echo(f"🧪 Running {test_type} tests...")

        if watch:
            click.echo("👀 Watching for changes...")
            runner.test_watch(test_type, coverage=coverage)
        else:
            success = runner.run_tests(
                test_type=test_type, coverage=coverage, parallel=parallel
            )

            if success:
                click.echo("✅ All tests passed")
            else:
                click.echo("❌ Some tests failed")
                sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Test error: {e}")
        if ctx.obj["verbose"]:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option("--env", default="development", help="Environment to deploy to")
@click.option("--project", help="GCP project ID (overrides config)")
@click.option("--region", help="GCP region (overrides config)")
@click.option("--service", help="Cloud Run service name (overrides config)")
@click.option("--dry-run", is_flag=True, help="Show what would be deployed")
@click.option("--build-only", is_flag=True, help="Only build, do not deploy")
@click.pass_context
def deploy(
    ctx: click.Context,
    env: str,
    project: Optional[str],
    region: Optional[str],
    service: Optional[str],
    dry_run: bool,
    build_only: bool,
) -> None:
    """Deploy TypeScript service to GCP"""
    config = ctx.obj["config"]
    deployer = GCPDeployer(config, verbose=ctx.obj["verbose"])

    # Override config with CLI options
    deploy_config = {
        "environment": env,
        "project_id": project or config.get_env_config(env).get("project_id"),
        "region": region or config.get_env_config(env).get("region"),
        "service_name": service or config.get_env_config(env).get("service_name"),
    }

    try:
        click.echo(f"🚀 Deploying to {env} environment...")

        if dry_run:
            click.echo("🔍 Dry run - showing deployment plan:")
            plan = deployer.plan_deployment(deploy_config)
            click.echo(json.dumps(plan, indent=2))
            return

        # Build first
        builder = TypeScriptBuilder(config, verbose=ctx.obj["verbose"])
        click.echo("🔨 Building service...")
        if not builder.build(env):
            click.echo("❌ Build failed")
            sys.exit(1)

        if build_only:
            click.echo("✅ Build completed (skipping deployment)")
            return

        # Deploy
        success = deployer.deploy(deploy_config)

        if success:
            click.echo("✅ Deployment completed successfully")
            # Show deployment info
            info = deployer.get_deployment_info(deploy_config)
            if info:
                click.echo(f"🌐 Service URL: {info.get('url')}")
                click.echo(f"📊 Revision: {info.get('revision')}")
        else:
            click.echo("❌ Deployment failed")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Deployment error: {e}")
        if ctx.obj["verbose"]:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option("--env", default="development", help="Environment to check")
@click.pass_context
def status(ctx: click.Context, env: str) -> None:
    """Check deployment status"""
    config = ctx.obj["config"]
    deployer = GCPDeployer(config, verbose=ctx.obj["verbose"])

    try:
        deploy_config = {"environment": env, **config.get_env_config(env)}

        info = deployer.get_deployment_info(deploy_config)

        if info:
            click.echo(f"📊 Status for {env} environment:")
            click.echo(f"  Service: {info.get('service_name')}")
            click.echo(f"  URL: {info.get('url')}")
            click.echo(f"  Revision: {info.get('revision')}")
            click.echo(f"  Status: {info.get('status')}")
            click.echo(f"  Traffic: {info.get('traffic', '100%')}")
            click.echo(f"  Last Deploy: {info.get('last_deploy')}")
        else:
            click.echo(f"❌ No deployment found for {env} environment")

    except Exception as e:
        click.echo(f"❌ Status check error: {e}")
        if ctx.obj["verbose"]:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option("--env", default="development", help="Environment to get logs from")
@click.option("--lines", default=100, help="Number of lines to retrieve")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--filter", help="Filter logs by string")
@click.pass_context
def logs(
    ctx: click.Context, env: str, lines: int, follow: bool, filter: Optional[str]
) -> None:
    """View deployment logs"""
    config = ctx.obj["config"]
    deployer = GCPDeployer(config, verbose=ctx.obj["verbose"])

    try:
        deploy_config = {"environment": env, **config.get_env_config(env)}

        click.echo(f"📋 Logs for {env} environment:")
        deployer.stream_logs(deploy_config, lines=lines, follow=follow, filter=filter)

    except KeyboardInterrupt:
        click.echo("\n👋 Log streaming stopped")
    except Exception as e:
        click.echo(f"❌ Log error: {e}")
        if ctx.obj["verbose"]:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize TypeScript service configuration"""
    try:
        # Check if already initialized
        if (Path.cwd() / "build-config.yaml").exists():
            if not click.confirm("Configuration already exists. Overwrite?"):
                return

        click.echo("🚀 Initializing Genesis TypeScript service...")

        # Get project details
        project_name = click.prompt("Project name", type=str)
        project_description = click.prompt("Project description", type=str, default="")

        # GCP configuration
        gcp_project = click.prompt("GCP Project ID", type=str)
        gcp_region = click.prompt("GCP Region", type=str, default="us-central1")

        # Generate configuration
        config_data = {
            "project": {
                "name": project_name,
                "description": project_description,
                "version": "1.0.0",
            },
            "environments": {
                "development": {
                    "project_id": f"{gcp_project}-dev",
                    "region": gcp_region,
                    "service_name": f"{project_name}-dev",
                },
                "staging": {
                    "project_id": f"{gcp_project}-staging",
                    "region": gcp_region,
                    "service_name": f"{project_name}-staging",
                },
                "production": {
                    "project_id": gcp_project,
                    "region": gcp_region,
                    "service_name": project_name,
                },
            },
            "build": {
                "node_version": "18",
                "npm_registry": "https://registry.npmjs.org/",
                "build_command": "npm run build",
                "test_command": "npm test",
                "docker": {"base_image": "node:18-alpine", "port": 8080},
            },
        }

        # Write configuration
        import yaml

        with open("build-config.yaml", "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        click.echo("✅ Configuration created: build-config.yaml")
        click.echo("📝 Edit the configuration file to customize your setup")
        click.echo("🏃 Run 'genesis-ts-build build' to build your service")

    except Exception as e:
        click.echo(f"❌ Initialization error: {e}")
        if ctx.obj["verbose"]:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Check system requirements and configuration"""
    click.echo("🩺 Genesis TypeScript Build Doctor")
    click.echo("=" * 40)

    issues = []

    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            click.echo(f"✅ Node.js: {version}")

            # Check version is >= 18
            major_version = int(version.split(".")[0].replace("v", ""))
            if major_version < 18:
                issues.append("Node.js version should be >= 18")
        else:
            issues.append("Node.js not found")
            click.echo("❌ Node.js: Not found")
    except Exception:
        issues.append("Node.js not found")
        click.echo("❌ Node.js: Not found")

    # Check npm/yarn
    for pkg_manager in ["npm", "yarn"]:
        try:
            result = subprocess.run(
                [pkg_manager, "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                click.echo(f"✅ {pkg_manager}: {result.stdout.strip()}")
                break
        except Exception:
            continue
    else:
        issues.append("No package manager (npm/yarn) found")
        click.echo("❌ Package manager: Not found")

    # Check Docker
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            click.echo(f"✅ Docker: {result.stdout.strip()}")
        else:
            issues.append("Docker not found")
            click.echo("❌ Docker: Not found")
    except Exception:
        issues.append("Docker not found")
        click.echo("❌ Docker: Not found")

    # Check gcloud
    try:
        result = subprocess.run(["gcloud", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            click.echo("✅ Google Cloud CLI: Installed")
        else:
            issues.append("Google Cloud CLI not found")
            click.echo("❌ Google Cloud CLI: Not found")
    except Exception:
        issues.append("Google Cloud CLI not found")
        click.echo("❌ Google Cloud CLI: Not found")

    # Check configuration
    config_files = [
        "build-config.yaml",
        "build-config.json",
        "package.json",
        "tsconfig.json",
    ]
    found_configs = []

    for config_file in config_files:
        if Path(config_file).exists():
            found_configs.append(config_file)
            click.echo(f"✅ Configuration: {config_file}")

    if not found_configs:
        issues.append("No configuration files found")
        click.echo("❌ Configuration: Not found")

    # Summary
    click.echo("\n" + "=" * 40)
    if issues:
        click.echo(f"❌ Found {len(issues)} issue(s):")
        for issue in issues:
            click.echo(f"  - {issue}")
        click.echo("\n💡 Run 'genesis-ts-build init' to create initial configuration")
    else:
        click.echo("✅ All checks passed! You're ready to build.")


if __name__ == "__main__":
    main()
