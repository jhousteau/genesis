# Bootstrap CLI - Universal Project Platform (Genesis Layer)

The unified command-line interface for the Universal Project Platform, providing a complete Genesis Layer implementation for project management, deployment, and operations across the entire platform.

## Installation

Add the `bin` directory to your PATH:

```bash
export PATH="/Users/jameshousteau/source_code/bootstrapper/bin:$PATH"
```

Or run directly:

```bash
python /Users/jameshousteau/source_code/bootstrapper/bin/bootstrap
```

## Quick Start

```bash
# Create a new project
bootstrap new my-api --type api --language python --team platform

# List all managed projects
bootstrap list

# Retrofit an existing project
bootstrap retrofit /path/to/existing/project

# Validate project compliance
bootstrap validate my-api

# Deploy a project
bootstrap deploy my-api dev
```

## Commands

### Project Management

- `bootstrap new <name>` - Create a new project with standard structure
- `bootstrap retrofit <path>` - Update existing project to standards
- `bootstrap list` - List all managed projects
- `bootstrap validate <project>` - Check project compliance

### Registry Management

- `bootstrap registry show` - Display project registry
- `bootstrap registry validate` - Validate registry integrity
- `bootstrap registry update` - Auto-discover and register projects

### Deployment & Infrastructure

- `bootstrap deploy <project> [env]` - Deploy project to environment
- `bootstrap infra <action> <project>` - Infrastructure operations

## Project Types

- **api** - REST API services
- **web-app** - Web applications  
- **cli** - Command-line tools
- **library** - Shared libraries
- **infrastructure** - Terraform/IaC projects

## Features

### 🏗️ Standard Project Structure
Every project gets:
- Consistent directory layout (`src/`, `tests/`, `docs/`, `scripts/`)
- Essential files (README, CHANGELOG, CONTRIBUTING, SECURITY)
- Universal Makefile with standard targets
- Pre-commit hooks and quality gates

### 🔒 GCP Isolation
- Per-project gcloud configurations
- Service account impersonation
- Environment-specific isolation
- Production safeguards

### 📋 Project Registry
- Single source of truth for all projects
- Auto-discovery of existing projects
- Environment and team tracking
- Compliance monitoring

### ✅ Quality Enforcement
- Automated compliance validation
- Smart commit system with quality gates
- Security scanning
- Documentation requirements

### 🚀 Deployment Pipeline
- Standard deployment scripts
- Environment-specific configurations
- Health checks and rollback capabilities
- Approval workflows for production

## Project Registry

The registry is stored at `projects/registry.yaml` and contains:

```yaml
global:
  organization: whitehorse
  default_region: us-central1
  plumbing_version: 2.0.0

projects:
  my-api:
    path: /path/to/project
    type: api
    language: python
    team: platform
    criticality: high
    environments:
      dev:
        gcp_project: my-api-dev
        gcloud_home: ~/.gcloud/my-api-dev
      prod:
        gcp_project: my-api-prod
        approval_required: true
```

## Integration

The CLI integrates the following components:

- **setup-project** - Project initialization and templates
- **Terraform modules** - Infrastructure provisioning
- **GCP isolation** - Security and safety
- **Compliance validation** - Quality enforcement
- **Registry system** - Project tracking

## Examples

### Create New API Project

```bash
bootstrap new payment-service \
  --type api \
  --language python \
  --team payments \
  --criticality high \
  --git
```

### Retrofit Existing Project

```bash
bootstrap retrofit /path/to/legacy-project --type api
```

### Deploy to Staging

```bash
bootstrap deploy payment-service staging
```

### Validate All Projects

```bash
bootstrap validate all
```

## Architecture

The CLI serves as the unified interface to the Universal Project Platform:

```
bootstrapper/
├── bin/bootstrap           # This CLI
├── setup-project/          # Project templates and generators  
├── modules/               # Terraform infrastructure modules
├── lib/                   # Shared libraries (plumbing)
├── isolation/             # GCP isolation templates
├── monitoring/            # Observability configs
├── governance/            # Compliance and policies
└── projects/              # Project registry
```

## Contributing

This CLI is the foundation of the Universal Project Platform. Changes should be coordinated with the overall architecture defined in `GRAND_DESIGN.md`.