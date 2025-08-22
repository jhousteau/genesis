---
title: Genesis Quick Start Guide
category: getting-started
status: approved
version: 1.0.0
updated: 2024-08-21
---

# Genesis Quick Start - 5 Minutes to Production

Get your first Genesis project deployed to GCP in under 5 minutes.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed
- Node.js 18+ or Python 3.10+
- Git installed

## Step 1: Install Genesis CLI

```bash
# Option 1: Install globally
curl -sSL https://genesis.dev/install | bash

# Option 2: Clone and install locally
git clone https://github.com/jhousteau/genesis.git
cd genesis
./scripts/bootstrap.sh
```

## Step 2: Initialize Genesis

```bash
# Set up your GCP project
g init

# This will:
# - Configure GCP project settings
# - Set up service accounts
# - Create Terraform state bucket
# - Configure Workload Identity Federation
```

## Step 3: Create Your First Project

```bash
# Create a new project from template
g new my-api --template=cloud-run

# Or migrate an existing project
g migrate ./my-existing-project
```

## Step 4: Local Development

```bash
# Start local development server
cd my-api
g dev

# Your service is now running at http://localhost:8080
# Changes auto-reload with hot module replacement
```

## Step 5: Deploy to GCP

```bash
# Run smart-commit (formats, validates, fixes)
g commit -m "Initial deployment"

# Deploy to development environment
g deploy dev

# Your service is now live at:
# https://my-api-dev-xxxxx.run.app
```

## What Just Happened?

Genesis automatically:

✅ **Created production-ready infrastructure**
- Error handling and retry logic
- Structured logging to Cloud Logging
- Health checks and monitoring
- Security scanning and compliance

✅ **Set up GCP resources**
- Cloud Run service with auto-scaling
- Service accounts with least privilege
- Cloud Build pipeline
- Monitoring dashboards

✅ **Configured development tools**
- Local development environment
- Hot reload for rapid iteration
- Integrated debugging
- Test framework

## Common Commands

```bash
# Development
g dev              # Start local development
g test             # Run tests
g lint             # Run linters
g debug            # Start debugger

# Deployment
g deploy [env]     # Deploy to environment
g rollback [env]   # Rollback deployment
g status [env]     # Check deployment status

# Project Management
g new [name]       # Create new project
g migrate [path]   # Migrate existing project
g list             # List all projects

# Smart Commit (never use git commit directly)
g commit           # Smart commit with quality gates
g fix              # Run autofix pipeline
```

## Project Structure

```
my-api/
├── .genesis/          # Genesis configuration
│   ├── config.yaml    # Project settings
│   └── hooks/         # Git hooks
├── src/               # Your application code
│   ├── main.py        # Entry point
│   └── handlers/      # Request handlers
├── terraform/         # Infrastructure as code
│   ├── main.tf        # Generated Terraform
│   └── variables.tf   # Environment variables
├── tests/             # Test suite
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
├── Dockerfile         # Container definition
├── cloudbuild.yaml    # CI/CD pipeline
└── genesis.yaml       # Genesis project config
```

## Environment Management

```bash
# Deploy to different environments
g deploy dev       # Development
g deploy staging   # Staging
g deploy prod      # Production

# Environment-specific configuration
g config set --env=prod MIN_INSTANCES=3
g config set --env=dev DEBUG=true
```

## Monitoring Your Application

```bash
# View logs
g logs --tail

# Check metrics
g metrics

# View traces
g traces

# Open monitoring dashboard
g dashboard
```

## Next Steps

### Learn More
- [Installation Guide](./installation.md) - Detailed setup instructions
- [First Project Tutorial](./first-project.md) - Build a complete application
- [Architecture Overview](../02-architecture/foundation.md) - Understand Genesis internals

### Explore Features
- [Smart Commit Workflow](../04-guides/deployment/smart-commit.md)
- [Multi-Agent Development](../04-guides/deployment/multi-agent.md)
- [Monitoring Setup](../04-guides/monitoring/setup.md)

### Get Help
- Run `g help` for command reference
- Check [Troubleshooting Guide](../04-guides/troubleshooting/common-issues.md)
- Join our [Discord Community](https://discord.genesis.dev)

## Tips for Success

1. **Always use `g commit`** - Never use `git commit` directly
2. **Start with templates** - Use `g new --list-templates` to see options
3. **Test locally first** - Use `g dev` before deploying
4. **Monitor deployments** - Use `g status` to track progress
5. **Use environments** - Keep dev, staging, and prod separate

---

**Ready to build?** You now have a production-ready application with 80% less code to maintain!