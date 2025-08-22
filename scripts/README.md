# Genesis Scripts

This directory contains utility scripts for managing the Genesis platform infrastructure and development environment.

## 🔒 Security Scripts

### `bootstrap_gcloud.sh`
Sets up isolated GCloud configurations for the repository to prevent cross-project contamination.

**Usage:**
```bash
./scripts/bootstrap_gcloud.sh
```

**Features:**
- Creates isolated config directory at `~/.gcloud/genesis-${ENVIRONMENT}`
- Copies authentication from main gcloud config
- Sets project, region, and zone for the environment
- Validates project access
- Creates initialization markers

### `setup-gcp-isolation-universal.sh`
Universal GCP isolation setup script that creates agent-ready isolated environments for any project.

**Usage:**
```bash
# Basic setup for genesis project
./scripts/setup-gcp-isolation-universal.sh --project genesis --region us-east1

# Full setup with custom environment
./scripts/setup-gcp-isolation-universal.sh \
  --project genesis \
  --env staging \
  --region us-east1 \
  --service-account deploy-staging@genesis-staging.iam.gserviceaccount.com
```

**Features:**
- Creates isolated gcloud configurations per project/environment
- Automatic service account creation and IAM setup
- Production safety guards and confirmation prompts
- Agent-ready template generation
- Manual environment configuration via .envrc
- CI/CD workflow templates

### `gcloud_guard.sh`
Provides protection against wrong-project operations and enforces safety policies.

**Usage:**
```bash
# Create an alias
alias gcloud='./scripts/gcloud_guard.sh'

# Use as normal
gcloud compute instances list
```

**Features:**
- Validates isolation is active
- Blocks cross-project operations
- Production safety checks
- Comprehensive audit logging
- Rate limiting for resource-intensive operations

## 🚀 Deployment Scripts

### `bootstrap.sh`
Main initialization script for setting up the Genesis platform.

**Usage:**
```bash
./scripts/bootstrap.sh
```

**Features:**
- Enables required GCP APIs
- Creates Terraform backend storage
- Sets up Workload Identity Federation
- Initializes Terraform
- Generates environment templates

### `deploy.sh`
Deployment orchestration script for various environments.

**Usage:**
```bash
./scripts/deploy.sh [environment] [options]

# Examples:
./scripts/deploy.sh dev
./scripts/deploy.sh staging --plan-only
./scripts/deploy.sh prod --auto-approve
```

### `smart-commit.sh`
Intelligent commit system with quality gates and validation.

**Usage:**
```bash
./scripts/smart-commit.sh
```

**Features:**
- Pre-commit validation
- Conventional commit format
- Quality checks
- Secret scanning
- Automated testing

## 🧹 Maintenance Scripts

### `cleanup.sh`
Safely removes resources and cleans up environments.

**Usage:**
```bash
./scripts/cleanup.sh [environment]

# With backup
./scripts/cleanup.sh dev --backup
```

### `validate-project.sh`
Validates project configuration and setup.

**Usage:**
```bash
./scripts/validate-project.sh
```

**Checks:**
- Environment configuration
- API enablement
- IAM permissions
- Network connectivity
- Resource quotas

### `generate-terraform-vars.sh`
Generates Terraform variable files from templates.

**Usage:**
```bash
./scripts/generate-terraform-vars.sh [environment]
```

## 📊 Monitoring Scripts

### `check-progress.sh`
Monitors deployment progress and resource status.

**Usage:**
```bash
./scripts/check-progress.sh
```

### `validate-config.sh`
Validates configuration files for correctness.

**Usage:**
```bash
./scripts/validate-config.sh
```

## 🔧 Development Scripts

### `setup-dev.sh`
Sets up local development environment.

**Usage:**
```bash
./scripts/setup-dev.sh
```

**Actions:**
- Installs dependencies
- Configures pre-commit hooks
- Sets up Python virtual environment
- Configures IDE settings

## 🚨 Important Notes

### Environment Variables
Most scripts respect these environment variables:
- `ENVIRONMENT`: Target environment (dev/test/staging/prod)
- `PROJECT_ID`: GCP project ID
- `REGION`: Default region
- `CONFIRM_PROD`: Required for production operations

### Safety Features
- Production operations require explicit confirmation
- Destructive operations are logged
- Backup options available for cleanup scripts
- Dry-run modes for testing

### Prerequisites
- Google Cloud SDK installed
- Terraform >= 1.5
- Appropriate IAM permissions
- Active GCP project

## 📚 Script Conventions

All scripts follow these conventions:
- Bash strict mode (`set -euo pipefail`)
- Colored output for clarity
- Comprehensive error handling
- Help text with `-h` or `--help`
- Dry-run support with `--dry-run`
- Verbose mode with `-v` or `--verbose`

## 🔗 Related Documentation

- [GCP Isolation Guide](../docs/04-guides/gcp-isolation.md)
- [Deployment Guide](../docs/04-guides/deployment/)
- [Operations Runbooks](../docs/05-operations/runbooks/)