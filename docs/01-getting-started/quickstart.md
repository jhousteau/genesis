---
title: Genesis Quick Start Guide
category: getting-started
status: current
version: 2.0.0
updated: 2025-08-24
---

# Genesis Quick Start

Get started with Genesis Universal Infrastructure Platform in minutes.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and authenticated
- Python 3.10+
- Git installed

## Step 1: Clone and Setup

```bash
# Clone Genesis repository
git clone https://github.com/jhousteau/genesis.git
cd genesis

# Run bootstrap script
./scripts/bootstrap.sh
```

## Step 2: Configure Environment

```bash
# Set your GCP project
export PROJECT_ID=your-gcp-project-id
export ENVIRONMENT=dev

# Initialize Terraform backend
g infra init
```

## Step 3: Deploy Infrastructure

```bash
# Plan infrastructure changes
g infra plan --module vm-management --environment dev

# Apply infrastructure
g infra apply --module vm-management --environment dev
```

## Step 4: Manage Agents

```bash
# Create agent VM pool
g vm create-pool --type backend-developer --size 2

# Start agents
g agent start --type backend-developer --count 2
```

## Step 5: Container Orchestration

```bash
# Create GKE cluster
g container create-cluster genesis-cluster --autopilot

# Deploy agent-cage service
g container deploy --service agent-cage --environment dev
```

## What Genesis Provides

✅ **VM Management** - Agent pools with autoscaling
✅ **Container Orchestration** - GKE clusters and deployments
✅ **Infrastructure Automation** - Terraform modules and state management
✅ **Agent Operations** - Multi-agent coordination and migration
✅ **Smart Commit** - Quality gates and automated validation

## Common Commands

```bash
# VM Management
g vm create-pool --type backend-developer --size 3
g vm scale-pool pool-name --min 1 --max 10
g vm health-check --pool pool-name
g vm list-pools

# Container Orchestration
g container create-cluster cluster-name --autopilot
g container deploy --service agent-cage --environment dev
g container scale --deployment claude-talk --replicas 5
g container logs --service agent-cage --follow

# Infrastructure
g infra plan --module vm-management --environment dev
g infra apply --module container-orchestration --environment prod
g infra status --all

# Agent Operations
g agent start --type backend-developer --count 2
g agent status --all
g agent migrate --from legacy --to agent-cage

# Smart Commit (use project's smart-commit)
./smart-commit.sh  # Quality gates and validation
```

## Genesis Structure

```
genesis/
├── cli/               # Genesis CLI commands
├── core/              # Production-ready libraries
├── intelligence/      # Smart-commit and SOLVE framework
├── modules/           # Terraform infrastructure modules
├── templates/         # Project templates
├── monitoring/        # Observability stack
├── config/            # Environment configurations
└── scripts/           # Automation scripts
```

## Environment Management

```bash
# Set environment
export ENVIRONMENT=dev|staging|prod
export PROJECT_ID=your-gcp-project

# Environment-specific infrastructure
g infra apply --module vm-management --environment dev
g infra apply --module container-orchestration --environment prod

# Check environment status
g infra status --all
```

## Monitoring

```bash
# View container logs
g container logs --service agent-cage --follow

# Check VM health
g vm health-check --pool backend-pool

# Agent status
g agent status --all

# Infrastructure status
g infra status --all
```

## Next Steps

### Learn More
- [GCP Isolation Setup](../04-guides/gcp-isolation-setup.md) - Environment isolation
- [VM Management](../04-guides/vm-management-deployment.md) - Agent VM deployment
- [Architecture Overview](../00-overview/GRAND_DESIGN.md) - Complete platform vision

### Core Components
- [Genesis Core](../../core/README.md) - Production libraries
- [Smart Commit](../../intelligence/smart-commit/README.md) - Quality gates
- [SOLVE Framework](../../intelligence/solve/README.md) - AI orchestration

### Get Help
- Run `g --help` for command reference
- Check project documentation in `/docs`
- Review component README files

## Key Principles

1. **Use smart-commit** - `./smart-commit.sh` for all changes
2. **Environment isolation** - Separate dev/staging/prod
3. **Infrastructure as code** - All resources via Terraform
4. **Agent coordination** - Multi-agent development workflows
5. **Quality gates** - Automated validation and testing

---

**Genesis: Write features, not plumbing.**
