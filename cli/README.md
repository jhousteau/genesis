# Genesis CLI

Universal Infrastructure Platform Command Interface implementing PIPES methodology for comprehensive infrastructure management.

## Overview

The Genesis CLI (`g`) provides a unified interface for managing:
- **VM Management** - Agent pools, autoscaling, lifecycle management
- **Container Orchestration** - GKE clusters, deployments, services
- **Infrastructure Automation** - Terraform modules, monitoring, security
- **Agent Operations** - Multi-agent coordination and migration

## Installation

The CLI is automatically available after Genesis setup:

```bash
# From project root
cd genesis
export PATH="$PATH:$(pwd)/cli/bin"

# Verify installation
g --help
```

## Commands

### VM Management
```bash
g vm create-pool --type backend-developer --size 3
g vm scale-pool pool-name --min 1 --max 10
g vm health-check --pool pool-name
g vm list-pools
```

### Container Orchestration
```bash
g container create-cluster cluster-name --autopilot
g container deploy --service agent-cage --environment dev
g container scale --deployment claude-talk --replicas 5
g container logs --service agent-cage --follow
```

### Infrastructure Management
```bash
g infra plan --module vm-management --environment dev
g infra apply --module container-orchestration --environment prod
g infra status --all
g infra validate
```

### Agent Operations
```bash
g agent start --type backend-developer --count 2
g agent status --all
g agent migrate --from legacy --to agent-cage
```

## Configuration

The CLI uses environment-specific configuration:

```bash
export PROJECT_ID=your-gcp-project
export ENVIRONMENT=dev|staging|prod
```

Configuration files are located in:
- `config/environments/` - Environment-specific settings
- `config/project.env` - Global project configuration

## Architecture

```
cli/
├── commands/           # Command implementations
│   ├── main.py        # Main CLI entry point
│   ├── vm_commands.py # VM management
│   ├── container_commands.py # Container orchestration
│   ├── infrastructure_commands.py # Infrastructure automation
│   └── agent_commands.py # Agent operations
├── utils/             # Shared utilities
│   └── error_formatting.py # Error handling
└── bin/               # Executable scripts
```

## Implementation Details

### Command Categories
- **vm** - VM pool management and agent infrastructure
- **container** - GKE cluster and container deployment management
- **infra** - Terraform infrastructure automation
- **agent** - Multi-agent coordination and operations

### Global Options
- `--environment, -e` - Target environment (dev, staging, prod)
- `--project-id, -p` - GCP project ID
- `--verbose, -v` - Enable verbose logging
- `--dry-run` - Show planned actions without execution
- `--output, -o` - Output format (json, yaml, table, text)

### Error Handling
Comprehensive error handling with user-friendly messages and suggested fixes.

### Integration
- **Terraform** - Direct integration for infrastructure management
- **GCP APIs** - Native GCP service integration
- **Kubernetes** - kubectl wrapper for container operations
- **Agent Systems** - Direct integration with agent-cage and claude-talk

## Examples

### Complete Workflow
```bash
# Initialize infrastructure
g infra init
g infra plan --module vm-management --environment dev
g infra apply --module vm-management --environment dev

# Create agent pools
g vm create-pool --type backend-developer --size 2
g vm create-pool --type frontend-developer --size 1

# Deploy container services
g container create-cluster genesis-dev-cluster --autopilot
g container deploy --service agent-cage --environment dev

# Start agents
g agent start --type backend-developer --count 2
g agent start --type frontend-developer --count 1
```

### Environment Management
```bash
# Development
export ENVIRONMENT=dev
g infra apply --module vm-management --environment dev

# Production (with safeguards)
export ENVIRONMENT=prod
g infra plan --module vm-management --environment prod
g infra apply --module vm-management --environment prod
```

## See Also

- [Getting Started Guide](../docs/01-getting-started/quickstart.md) - Quick setup instructions
- [VM Management Guide](../docs/04-guides/vm-management-deployment.md) - Detailed VM operations
- [Infrastructure Modules](../modules/README.md) - Terraform module documentation
- [Agent Coordination](../coordination/README.md) - Multi-agent system architecture

---

**Genesis CLI** - Universal infrastructure management made simple.
