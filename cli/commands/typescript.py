"""
Genesis TypeScript CLI Commands

Command-line interface for TypeScript project operations,
integrated with Genesis universal project platform.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click

from ..utils.logger import get_logger
from ..utils.templates import TemplateRenderer
from ..utils.validators import validate_gcp_project_id, validate_project_name

logger = get_logger(__name__)


@click.group(name="typescript")
def typescript_cli():
    """TypeScript project management commands"""
    pass


@typescript_cli.command()
@click.option("--name", "-n", required=True, help="Project name")
@click.option("--description", "-d", default="", help="Project description")
@click.option("--gcp-project", help="GCP project ID (without environment suffix)")
@click.option("--region", default="us-central1", help="GCP region")
@click.option(
    "--template",
    default="service",
    type=click.Choice(["service", "api", "worker", "function"]),
    help="Project template type",
)
@click.option("--with-database", is_flag=True, help="Include database configuration")
@click.option("--with-auth", is_flag=True, help="Include authentication setup")
@click.option("--with-monitoring", is_flag=True, help="Include monitoring setup")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.pass_context
def new(
    ctx: click.Context,
    name: str,
    description: str,
    gcp_project: Optional[str],
    region: str,
    template: str,
    with_database: bool,
    with_auth: bool,
    with_monitoring: bool,
    interactive: bool,
):
    """Create a new TypeScript project with Genesis patterns"""

    try:
        logger.info(f"Creating new TypeScript {template}: {name}")

        # Interactive mode
        if interactive:
            name = click.prompt("Project name", default=name)
            description = click.prompt("Project description", default=description)
            gcp_project = click.prompt(
                "GCP project ID (base)", default=gcp_project or ""
            )
            region = click.prompt("GCP region", default=region)
            template = click.prompt(
                "Template type",
                type=click.Choice(["service", "api", "worker", "function"]),
                default=template,
            )
            with_database = click.confirm(
                "Include database support?", default=with_database
            )
            with_auth = click.confirm("Include authentication?", default=with_auth)
            with_monitoring = click.confirm(
                "Include monitoring?", default=with_monitoring
            )

        # Validate inputs
        if not validate_project_name(name):
            raise click.ClickException(f"Invalid project name: {name}")

        if gcp_project and not validate_gcp_project_id(gcp_project):
            raise click.ClickException(f"Invalid GCP project ID: {gcp_project}")

        # Create project directory
        project_dir = Path.cwd() / name
        if project_dir.exists():
            if not click.confirm(f"Directory {name} already exists. Overwrite?"):
                return
            shutil.rmtree(project_dir)

        project_dir.mkdir(parents=True, exist_ok=True)

        # Get template data
        template_data = {
            "PROJECT_NAME": name,
            "PROJECT_DESCRIPTION": description,
            "GCP_PROJECT": gcp_project or f"genesis-{name}",
            "GCP_REGION": region,
            "TEMPLATE_TYPE": template,
            "WITH_DATABASE": with_database,
            "WITH_AUTH": with_auth,
            "WITH_MONITORING": with_monitoring,
            "REPOSITORY_URL": f"https://github.com/organization/{name}",
            "DIRECTORY_PATH": f"services/{name}",
            "TIMESTAMP": click.DateTime().process_value(
                ctx, None, ctx.obj.get("timestamp")
            ),
        }

        # Render templates
        template_renderer = TemplateRenderer()
        genesis_root = Path(__file__).parent.parent.parent
        template_source = genesis_root / "templates" / "typescript-service"

        click.echo(f"📁 Creating project structure in {project_dir}")
        template_renderer.render_directory(
            template_source,
            project_dir,
            template_data,
            exclude_patterns=[
                "**/__pycache__/**",
                "**/.pytest_cache/**",
                "**/node_modules/**",
                "**/dist/**",
                "**/coverage/**",
            ],
        )

        # Initialize git repository
        click.echo("📦 Initializing git repository")
        _init_git_repo(project_dir, name)

        # Install dependencies
        click.echo("📚 Installing dependencies")
        _install_dependencies(project_dir)

        # Setup GCP integration if project ID provided
        if gcp_project:
            click.echo("☁️  Setting up GCP integration")
            _setup_gcp_integration(project_dir, gcp_project, region, template_data)

        # Generate additional files based on options
        if with_database:
            _setup_database_config(project_dir, template_data)

        if with_auth:
            _setup_auth_config(project_dir, template_data)

        if with_monitoring:
            _setup_monitoring_config(project_dir, template_data)

        # Create initial documentation
        _create_documentation(project_dir, template_data)

        # Success message
        click.echo("\n" + "=" * 50)
        click.echo(f"✅ TypeScript {template} '{name}' created successfully!")
        click.echo(f"📁 Location: {project_dir.absolute()}")
        click.echo("\n📋 Next steps:")
        click.echo(f"   cd {name}")
        click.echo("   npm install")
        click.echo("   npm run dev")

        if gcp_project:
            click.echo("\n☁️  GCP Setup:")
            click.echo(f"   gcloud config set project {gcp_project}-dev")
            click.echo("   npm run deploy:dev")

        click.echo(f"\n📖 Documentation: {project_dir / 'README.md'}")

        logger.info(f"Successfully created TypeScript project: {name}")

    except Exception as e:
        logger.error(f"Failed to create TypeScript project: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@typescript_cli.command()
@click.option("--env", default="development", help="Environment to build for")
@click.option("--clean", is_flag=True, help="Clean before building")
@click.option("--watch", is_flag=True, help="Watch mode")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def build(env: str, clean: bool, watch: bool, verbose: bool):
    """Build TypeScript project"""

    try:
        click.echo(f"🔨 Building TypeScript project for {env}")

        # Check if we're in a TypeScript project
        if not _is_typescript_project():
            raise click.ClickException("Not in a TypeScript project directory")

        # Use Python build tools if available
        poetry_cmd = _find_poetry_command()
        if poetry_cmd:
            click.echo("🐍 Using Genesis Python build tools")
            cmd = [poetry_cmd, "run", "genesis-ts-build", "build", "--env", env]
            if clean:
                cmd.append("--clean")
            if watch:
                cmd.append("--watch")
            if verbose:
                cmd.append("--verbose")
        else:
            # Fallback to npm
            click.echo("📦 Using npm build")
            if clean:
                _run_command(["npm", "run", "clean"])

            if watch:
                cmd = ["npm", "run", "build:watch"]
            else:
                cmd = ["npm", "run", "build"]

        _run_command(cmd, verbose=verbose)
        click.echo("✅ Build completed successfully")

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Build failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Build error: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@typescript_cli.command()
@click.option(
    "--type",
    "test_type",
    default="all",
    type=click.Choice(["unit", "integration", "e2e", "all"]),
    help="Type of tests to run",
)
@click.option("--coverage", is_flag=True, help="Generate coverage report")
@click.option("--watch", is_flag=True, help="Watch mode")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def test(test_type: str, coverage: bool, watch: bool, verbose: bool):
    """Run TypeScript tests"""

    try:
        click.echo(f"🧪 Running {test_type} tests")

        if not _is_typescript_project():
            raise click.ClickException("Not in a TypeScript project directory")

        # Use Python test tools if available
        poetry_cmd = _find_poetry_command()
        if poetry_cmd:
            click.echo("🐍 Using Genesis Python test runner")
            cmd = [poetry_cmd, "run", "genesis-ts-test", "test", "--type", test_type]
            if coverage:
                cmd.append("--coverage")
            if watch:
                cmd.append("--watch")
            if verbose:
                cmd.append("--verbose")
        else:
            # Fallback to Jest
            cmd = ["npm", "run"]
            if test_type == "all":
                cmd.append("test")
            else:
                cmd.append(f"test:{test_type}")

            if coverage:
                cmd.append("--coverage")
            if watch:
                cmd.append("--watch")

        _run_command(cmd, verbose=verbose)
        click.echo("✅ Tests completed successfully")

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Tests failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test error: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@typescript_cli.command()
@click.option("--env", default="development", help="Environment to deploy to")
@click.option("--project", help="GCP project ID (overrides config)")
@click.option("--region", help="GCP region (overrides config)")
@click.option("--service", help="Cloud Run service name (overrides config)")
@click.option("--dry-run", is_flag=True, help="Show deployment plan without executing")
@click.option("--build-only", is_flag=True, help="Build only, skip deployment")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def deploy(
    env: str,
    project: Optional[str],
    region: Optional[str],
    service: Optional[str],
    dry_run: bool,
    build_only: bool,
    verbose: bool,
):
    """Deploy TypeScript service to GCP"""

    try:
        click.echo(f"🚀 Deploying to {env} environment")

        if not _is_typescript_project():
            raise click.ClickException("Not in a TypeScript project directory")

        # Use Python deployment tools if available
        poetry_cmd = _find_poetry_command()
        if poetry_cmd:
            click.echo("🐍 Using Genesis Python deployment tools")
            cmd = [poetry_cmd, "run", "genesis-ts-deploy", "deploy", "--env", env]
            if project:
                cmd.extend(["--project", project])
            if region:
                cmd.extend(["--region", region])
            if service:
                cmd.extend(["--service", service])
            if dry_run:
                cmd.append("--dry-run")
            if build_only:
                cmd.append("--build-only")
            if verbose:
                cmd.append("--verbose")
        else:
            # Fallback to gcloud
            click.echo("☁️  Using gcloud deployment")
            if not build_only:
                # Build first
                _run_command(["npm", "run", "build"], verbose=verbose)

            if not dry_run and not build_only:
                service_name = service or Path.cwd().name
                cmd = [
                    "gcloud",
                    "run",
                    "deploy",
                    service_name,
                    "--source",
                    ".",
                    "--platform",
                    "managed",
                    "--region",
                    region or "us-central1",
                    "--allow-unauthenticated",
                ]

                if project:
                    cmd.extend(["--project", project])

        if not dry_run:
            _run_command(cmd, verbose=verbose)
            click.echo("✅ Deployment completed successfully")
        else:
            click.echo("🔍 Dry run completed - no deployment executed")

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Deployment failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@typescript_cli.command()
def doctor():
    """Check TypeScript development environment"""

    click.echo("🩺 Genesis TypeScript Environment Doctor")
    click.echo("=" * 50)

    issues = []

    # Check Node.js
    if _check_command("node"):
        version = _get_command_version("node")
        major_version = int(version.split(".")[0].replace("v", ""))
        if major_version >= 18:
            click.echo(f"✅ Node.js: {version}")
        else:
            click.echo(f"⚠️  Node.js: {version} (upgrade to >= 18 recommended)")
            issues.append("Node.js version should be >= 18")
    else:
        click.echo("❌ Node.js: Not found")
        issues.append("Node.js not installed")

    # Check package managers
    npm_found = _check_command("npm")
    yarn_found = _check_command("yarn")
    pnpm_found = _check_command("pnpm")

    if npm_found:
        version = _get_command_version("npm")
        click.echo(f"✅ npm: {version}")

    if yarn_found:
        version = _get_command_version("yarn")
        click.echo(f"✅ yarn: {version}")

    if pnpm_found:
        version = _get_command_version("pnpm")
        click.echo(f"✅ pnpm: {version}")

    if not (npm_found or yarn_found or pnpm_found):
        click.echo("❌ Package manager: Not found")
        issues.append("No package manager found")

    # Check TypeScript
    if _check_command("tsc"):
        version = _get_command_version("tsc")
        click.echo(f"✅ TypeScript: {version}")
    else:
        click.echo("⚠️  TypeScript: Not found globally (project-local is fine)")

    # Check Docker
    if _check_command("docker"):
        version = _get_command_version("docker")
        click.echo(f"✅ Docker: {version}")
    else:
        click.echo("⚠️  Docker: Not found (needed for containerization)")

    # Check gcloud
    if _check_command("gcloud"):
        click.echo("✅ Google Cloud CLI: Installed")
    else:
        click.echo("⚠️  Google Cloud CLI: Not found (needed for GCP deployment)")

    # Check Poetry (for enhanced Genesis features)
    if _check_command("poetry"):
        version = _get_command_version("poetry")
        click.echo(f"✅ Poetry: {version} (Enhanced Genesis features available)")
    else:
        click.echo("⚠️  Poetry: Not found (enhanced Genesis features disabled)")

    # Check current directory
    if _is_typescript_project():
        click.echo("✅ Current directory: TypeScript project detected")

        # Check project structure
        required_files = ["package.json", "tsconfig.json"]
        for file in required_files:
            if Path(file).exists():
                click.echo(f"✅ {file}: Found")
            else:
                click.echo(f"❌ {file}: Missing")
                issues.append(f"Missing {file}")
    else:
        click.echo("ℹ️  Current directory: Not a TypeScript project")

    # Summary
    click.echo("\n" + "=" * 50)
    if issues:
        click.echo(f"❌ Found {len(issues)} issue(s):")
        for issue in issues:
            click.echo(f"  • {issue}")

        click.echo("\n💡 Recommendations:")
        click.echo("  • Install missing tools")
        click.echo("  • Run 'genesis typescript new' to create a new project")
        click.echo("  • Check the Genesis documentation for setup guides")
    else:
        click.echo("✅ All checks passed! Your TypeScript environment is ready.")


# Helper functions


def _is_typescript_project() -> bool:
    """Check if current directory is a TypeScript project"""
    return (Path.cwd() / "package.json").exists() and (
        Path.cwd() / "tsconfig.json"
    ).exists()


def _find_poetry_command() -> Optional[str]:
    """Find Poetry command for enhanced Genesis features"""
    if _check_command("poetry") and Path("pyproject.toml").exists():
        return "poetry"
    return None


def _check_command(command: str) -> bool:
    """Check if command exists"""
    try:
        subprocess.run([command, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _get_command_version(command: str) -> str:
    """Get command version"""
    try:
        result = subprocess.run(
            [command, "--version"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip().split("\n")[0]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Unknown"


def _run_command(cmd: List[str], verbose: bool = False) -> None:
    """Run command with proper error handling"""
    if verbose:
        click.echo(f"Running: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        raise click.ClickException(f"Command failed: {' '.join(cmd)}")


def _init_git_repo(project_dir: Path, name: str) -> None:
    """Initialize git repository"""
    try:
        subprocess.run(
            ["git", "init"], cwd=project_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "add", "."], cwd=project_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Initial commit for {name}"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        logger.warning("Failed to initialize git repository")


def _install_dependencies(project_dir: Path) -> None:
    """Install project dependencies"""
    try:
        # Install npm dependencies
        subprocess.run(["npm", "install"], cwd=project_dir, check=True)

        # Install Python dependencies if pyproject.toml exists
        if (project_dir / "pyproject.toml").exists():
            if _check_command("poetry"):
                subprocess.run(["poetry", "install"], cwd=project_dir, check=True)
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to install some dependencies: {e}")


def _setup_gcp_integration(
    project_dir: Path, gcp_project: str, region: str, template_data: Dict
) -> None:
    """Setup GCP integration files"""
    # Create environment-specific configs
    environments = ["development", "staging", "production"]
    for env in environments:
        env_suffix = (
            "-dev" if env == "development" else f"-{env}" if env != "production" else ""
        )
        env_config = {
            "project_id": f"{gcp_project}{env_suffix}",
            "region": region,
            "environment": env,
        }

        env_file = project_dir / f".env.{env}"
        with open(env_file, "w") as f:
            f.write(f"NODE_ENV={env}\n")
            f.write(f"GOOGLE_CLOUD_PROJECT={env_config['project_id']}\n")
            f.write(f"GOOGLE_CLOUD_REGION={env_config['region']}\n")
            f.write(f"GENESIS_ENVIRONMENT={env}\n")


def _setup_database_config(project_dir: Path, template_data: Dict) -> None:
    """Setup database configuration"""
    db_config = {
        "host": "localhost",
        "port": 5432,
        "database": template_data["PROJECT_NAME"],
        "ssl": True,
    }

    # Add to environment files
    for env_file in project_dir.glob(".env.*"):
        with open(env_file, "a") as f:
            f.write("\n# Database Configuration\n")
            f.write(f"DB_HOST={db_config['host']}\n")
            f.write(f"DB_PORT={db_config['port']}\n")
            f.write(f"DB_NAME={db_config['database']}\n")
            f.write(f"DB_SSL={str(db_config['ssl']).lower()}\n")


def _setup_auth_config(project_dir: Path, template_data: Dict) -> None:
    """Setup authentication configuration"""
    # Add auth environment variables
    for env_file in project_dir.glob(".env.*"):
        with open(env_file, "a") as f:
            f.write("\n# Authentication Configuration\n")
            f.write("JWT_SECRET=your-secret-key-here\n")
            f.write("JWT_EXPIRES_IN=24h\n")
            f.write("AUTH_ENABLED=true\n")


def _setup_monitoring_config(project_dir: Path, template_data: Dict) -> None:
    """Setup monitoring configuration"""
    # Add monitoring environment variables
    for env_file in project_dir.glob(".env.*"):
        with open(env_file, "a") as f:
            f.write("\n# Monitoring Configuration\n")
            f.write("ENABLE_METRICS=true\n")
            f.write("ENABLE_TRACING=true\n")
            f.write("METRICS_PORT=9090\n")


def _create_documentation(project_dir: Path, template_data: Dict) -> None:
    """Create initial project documentation"""
    readme_content = f"""# {template_data['PROJECT_NAME']}

{template_data['PROJECT_DESCRIPTION']}

## Genesis TypeScript Service

This project is built using the Genesis Universal Project Platform with TypeScript support.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm test

# Build for production
npm run build

# Deploy to GCP
npm run deploy
```

## Features

- ✅ TypeScript with strict configuration
- ✅ Fastify web framework
- ✅ GCP integration (Secret Manager, Pub/Sub, Firestore, Storage)
- ✅ Comprehensive testing with Jest
- ✅ Docker containerization
- ✅ CI/CD with GitHub Actions
- ✅ Monitoring and observability
- ✅ Security best practices

## Development

### Requirements

- Node.js >= 18
- npm >= 8
- Docker (for containerization)
- Google Cloud CLI (for deployment)

### Commands

```bash
npm run build       # Build TypeScript
npm run build:watch # Build with watch mode
npm run test        # Run all tests
npm run test:unit   # Run unit tests
npm run test:integration # Run integration tests
npm run test:e2e    # Run end-to-end tests
npm run lint        # Lint code
npm run format      # Format code
npm run dev         # Development server
```

### Genesis Commands

If Poetry is installed, enhanced Genesis commands are available:

```bash
poetry run genesis-ts-build build --env production
poetry run genesis-ts-test test --type all --coverage
poetry run genesis-ts-deploy deploy --env staging
```

## Architecture

This service follows Genesis CRAFT methodology:

- **C - Create**: Clean, modular architecture
- **R - Refactor**: Continuous improvement patterns
- **A - Authenticate**: Secure authentication and authorization
- **F - Function**: High-performance, scalable operations
- **T - Test**: Comprehensive testing at all levels

## GCP Integration

### Services Used

- **Secret Manager**: Configuration and secrets
- **Cloud Run**: Serverless deployment
- **Firestore**: NoSQL database
- **Pub/Sub**: Messaging and events
- **Cloud Storage**: File storage
- **Cloud Monitoring**: Observability

### Deployment

```bash
# Development
gcloud config set project {template_data['GCP_PROJECT']}-dev
npm run deploy:dev

# Staging
gcloud config set project {template_data['GCP_PROJECT']}-staging
npm run deploy:staging

# Production
gcloud config set project {template_data['GCP_PROJECT']}
npm run deploy:prod
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run the full test suite
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
"""

    with open(project_dir / "README.md", "w") as f:
        f.write(readme_content)


# Register the CLI group
if __name__ == "__main__":
    typescript_cli()
