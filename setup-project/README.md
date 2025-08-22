# Setup-Project: Universal Project Initialization Tool

A comprehensive project setup tool that creates consistent, production-ready project structures with proper GCP isolation, CI/CD pipelines, monitoring, and compliance validation.

## Features

- **Universal project structure** - Works for any language or framework
- **GCP per-repository isolation** - Each project gets its own isolated gcloud configuration
- **Consistent plumbing** - Same deployment process, monitoring, and tooling across all projects
- **Smart commits** - Enforced quality gates before commits
- **Compliance validation** - Automated checks for standards and best practices
- **Documentation templates** - Consistent README, CHANGELOG, and other docs
- **Pre-commit hooks** - Code quality enforcement
- **Multi-environment support** - dev, test, stage, prod with proper safeguards

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize a new API project
python setup.py init --name=my-api --type=api --language=python

# Validate project compliance
python setup.py validate

# Upgrade existing project
python setup.py upgrade
```

## Project Types

- **api** - REST API services
- **web-app** - Web applications
- **cli** - Command-line tools
- **library** - Shared libraries
- **infrastructure** - Terraform/IaC projects

## What Gets Created

Every project gets:

### Core Structure
```
project/
├── src/                    # Source code
├── tests/                  # Test files
├── docs/                   # Documentation
├── scripts/               # Utility scripts
├── temp/                  # Temporary files (gitignored)
├── config/                # Configuration
├── .github/workflows/     # CI/CD pipelines
└── infrastructure/        # Terraform modules
```

### Essential Files
- `README.md` - Comprehensive documentation template
- `CHANGELOG.md` - Version history
- `CONTRIBUTING.md` - Contribution guidelines
- `SECURITY.md` - Security policies
- `CLAUDE.md` - AI agent instructions
- `Makefile` - Universal commands
- `.project-config.yaml` - Project metadata

### Scripts
- `bootstrap_gcloud.sh` - GCP isolation setup
- `gcloud_guard.sh` - Prevents wrong-project operations
- `validate-compliance.sh` - Standards enforcement
- `smart-commit.sh` - Quality-gated commits
- `deploy.sh` - Universal deployment
- `cleanup.sh` - Garbage removal

### Standard Commands

Every project gets the same Makefile targets:

```bash
make setup          # Initial setup
make dev           # Start local development
make test          # Run all tests
make lint          # Run linters
make build         # Build artifacts
make deploy        # Deploy to environment
make validate      # Check compliance
make commit        # Smart commit
make clean         # Clean garbage
```

## GCP Isolation

Each repository gets its own isolated gcloud configuration:

```bash
# Each repo uses its own config directory
export CLOUDSDK_CONFIG="$HOME/.gcloud/project-env"

# Service account impersonation (no local keys)
export GCLOUD_IMPERSONATE_SA="deploy@project.iam.gserviceaccount.com"

# Production safety
export CONFIRM_PROD="I_UNDERSTAND"  # Required for prod operations
```

## Compliance Validation

The compliance script checks for:

- Required files and documentation
- Forbidden/garbage files
- Hardcoded secrets
- Proper temp directory usage
- Documentation freshness
- TODO/FIXME count limits
- File permissions
- Large files
- And more...

## Deployment Pipeline

Consistent deployment across all environments:

```bash
# Development (auto-approve)
make deploy-dev

# Staging (manual approval)
make deploy-stage

# Production (multiple approvals + checks)
CONFIRM_PROD=I_UNDERSTAND make deploy-prod
```

Features:
- Pre-deployment validation
- Health checks
- Automatic rollback
- Deployment tracking
- Canary deployments
- Notifications

## Adding to Existing Projects

```bash
# Apply specific components
python setup.py apply --components=gcp-isolation,smart-commit

# Upgrade to latest standards
python setup.py upgrade
```

## Customization

Edit templates in `templates/` directory:
- `plumbing/` - Core infrastructure
- `gcp/` - GCP-specific configs
- `documentation/` - Doc templates
- `compliance/` - Validation rules
- `ci-cd/` - Pipeline definitions

## Requirements

- Python 3.8+
- Git
- Docker (optional)
- gcloud CLI (for GCP projects)
- direnv (recommended)

## Contributing

This tool enforces standards - changes should be discussed before implementation to maintain consistency across all projects.

## License

MIT