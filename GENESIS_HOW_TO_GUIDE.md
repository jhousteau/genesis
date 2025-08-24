# Genesis Universal Platform - Complete How-To Guide

Genesis is a comprehensive, production-ready infrastructure platform for Google Cloud Platform with intelligent automation, comprehensive monitoring, and built-in security best practices.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Core Concepts](#core-concepts)
3. [CLI Commands Reference](#cli-commands-reference)
4. [Environment Management](#environment-management)
5. [Infrastructure Operations](#infrastructure-operations)
6. [VM Management](#vm-management)
7. [Container Orchestration](#container-orchestration)
8. [Agent Operations](#agent-operations)
9. [Intelligence Systems](#intelligence-systems)
10. [Security & Governance](#security--governance)
11. [Monitoring & Observability](#monitoring--observability)
12. [Development Workflows](#development-workflows)
13. [Troubleshooting](#troubleshooting)
14. [Best Practices](#best-practices)

## Getting Started

### Prerequisites

Before using Genesis, ensure you have:

- **Google Cloud account** with billing enabled
- **Google Cloud SDK** (`gcloud`) installed and authenticated
- **Terraform** >= 1.5
- **Python** >= 3.11 with Poetry
- **Git** >= 2.28
- **direnv** (for automatic environment loading)
- Active GCP project with appropriate IAM permissions (Project Editor or Owner)

### Initial Setup

1. **Clone and Setup Genesis**
   ```bash
   # Clone the repository
   git clone https://github.com/jhousteau/genesis.git
   cd genesis

   # Allow direnv to load environment
   direnv allow

   # Run the bootstrap script
   ./scripts/bootstrap.sh
   ```

2. **Configure Your Environment**
   ```bash
   # Set your GCP project
   export PROJECT_ID=your-gcp-project-id
   export ENVIRONMENT=dev

   # The environment is automatically configured via .envrc
   # Switch environments with:
   ENVIRONMENT=staging direnv allow
   ENVIRONMENT=prod direnv allow
   ```

3. **Install Git Protections**
   ```bash
   # Install pre-commit hooks (automatic branch protection)
   pre-commit install

   # Verify protection is active
   git commit -m "test" # Should fail on main branch
   ```

## Core Concepts

### Genesis Architecture

Genesis provides these key components:

- **CLI Interface**: Comprehensive `g` command for all operations
- **Intelligence Systems**: solve, autofix, optimization, and prediction capabilities
- **Multi-Environment Isolation**: GCP project separation with automated credential management
- **Container Orchestration**: GKE-based platform with agent-cage and claude-talk integration
- **VM Management**: Automated agent pools with autoscaling and health monitoring
- **Infrastructure as Code**: Comprehensive Terraform modules with validation

### Project Structure

```
genesis/
├── cli/                  # Genesis CLI commands
├── core/                 # Production-ready libraries
├── intelligence/         # Smart-commit and SOLVE framework
│   ├── solve/           # AI-driven problem resolution
│   ├── autofix/         # Automated code repair
│   └── smart-commit/    # Quality gates and commit validation
├── modules/             # Terraform infrastructure modules
├── templates/           # Project templates
├── monitoring/          # Observability stack
├── config/              # Environment configurations
├── governance/          # Compliance and policies
├── isolation/           # Environment isolation
└── scripts/             # Automation scripts
```

## CLI Commands Reference

### Genesis CLI (`g`) Commands

The Genesis CLI provides unified access to all platform operations:

#### VM Management
```bash
# Create agent VM pool
g vm create-pool --type backend-developer --size 3

# Scale existing pool
g vm scale-pool pool-name --min 1 --max 10

# Health check
g vm health-check --pool pool-name

# List all pools
g vm list-pools

# Lifecycle management
g vm start-pool pool-name
g vm stop-pool pool-name
g vm delete-pool pool-name
```

#### Container Orchestration
```bash
# Create GKE cluster
g container create-cluster cluster-name --autopilot

# Deploy services
g container deploy --service agent-cage --environment dev
g container deploy --service claude-talk --environment prod

# Scale deployments
g container scale --deployment claude-talk --replicas 5

# View logs
g container logs --service agent-cage --follow

# Cluster management
g container list-clusters
g container delete-cluster cluster-name
```

#### Infrastructure Management
```bash
# Initialize infrastructure
g infra init

# Plan changes
g infra plan --module vm-management --environment dev

# Apply infrastructure
g infra apply --module container-orchestration --environment prod

# View status
g infra status --all

# Validate configuration
g infra validate

# Cost analysis
g cost analyze
g cost estimate --environment prod
```

#### Agent Operations
```bash
# Start agents
g agent start --type backend-developer --count 2
g agent start --type frontend-developer --count 1

# Check agent status
g agent status --all
g agent status --type backend-developer

# Migrate agents
g agent migrate --from legacy --to agent-cage

# Stop agents
g agent stop --type backend-developer
```

## Environment Management

Genesis supports isolated environments with proper separation:

### Environment Configuration

```bash
# Set environment variables
export PROJECT_ID=your-gcp-project
export ENVIRONMENT=dev|staging|prod

# Environment-specific infrastructure
g infra apply --module vm-management --environment dev
g infra apply --module container-orchestration --environment prod
```

### Environment Files

Configuration files are located in:
- `config/environments/dev.env` - Development settings
- `config/environments/staging.env` - Staging settings
- `config/environments/prod.env` - Production settings
- `config/project.env` - Global project configuration

### GCP Project Isolation

Each environment uses separate GCP projects:
```bash
# Development
export PROJECT_ID=my-project-dev
export ENVIRONMENT=dev

# Production (requires confirmation)
export PROJECT_ID=my-project-prod
export ENVIRONMENT=prod
export CONFIRM_PROD=I_UNDERSTAND
```

## Infrastructure Operations

### Terraform Module Management

Genesis uses modular Terraform architecture:

```bash
# Available modules
g infra list-modules

# Plan specific module
g infra plan --module vm-management --environment dev
g infra plan --module container-orchestration --environment staging
g infra plan --module networking --environment prod

# Apply with validation
g infra apply --module vm-management --environment dev
```

### Infrastructure Modules

Key infrastructure modules:
- **bootstrap**: Project initialization and backend setup
- **compute**: GKE clusters, Cloud Run, VMs
- **networking**: VPC, subnets, firewall rules
- **security**: IAM, secrets management, policies
- **monitoring**: Observability stack setup
- **container-orchestration**: GKE and agent container deployment
- **vm-management**: Agent VM pools and lifecycle management

### State Management

```bash
# Initialize backend
g infra init

# Import existing resources
g infra import --resource-type vm --resource-id instance-id

# Show state
g infra show

# Refresh state
g infra refresh
```

## VM Management

### Agent VM Pools

Create and manage pools of VMs for different agent types:

```bash
# Create pools for different agent types
g vm create-pool --type backend-developer --size 2
g vm create-pool --type frontend-developer --size 1
g vm create-pool --type qa-automation --size 1
g vm create-pool --type devops --size 1

# Scale pools based on demand
g vm scale-pool backend-developer --min 2 --max 8
g vm scale-pool frontend-developer --min 1 --max 4
```

### VM Lifecycle Management

```bash
# Start/stop pools
g vm start-pool backend-developer
g vm stop-pool frontend-developer

# Health monitoring
g vm health-check --pool backend-developer
g vm health-check --all

# Maintenance operations
g vm update-pool --pool backend-developer --size 4
g vm restart-pool --pool qa-automation
```

### VM Configuration

VM pools support various configurations:
- **Agent Types**: backend-developer, frontend-developer, qa-automation, devops, sre, security
- **Sizing**: Configurable instance types and autoscaling parameters
- **Health Checks**: Automated health monitoring and self-healing
- **Cost Optimization**: Preemptible instances and automatic scaling

## Container Orchestration

### GKE Cluster Management

```bash
# Create clusters
g container create-cluster genesis-dev-cluster --autopilot
g container create-cluster genesis-prod-cluster --standard --nodes 3

# Cluster operations
g container list-clusters
g container describe-cluster genesis-dev-cluster
g container delete-cluster genesis-dev-cluster
```

### Service Deployment

```bash
# Deploy core services
g container deploy --service agent-cage --environment dev
g container deploy --service claude-talk --environment prod
g container deploy --service mcp-server --environment staging

# Service management
g container list-services
g container describe-service agent-cage
g container scale --deployment claude-talk --replicas 5
```

### Container Monitoring

```bash
# View logs
g container logs --service agent-cage --follow
g container logs --deployment claude-talk --since 1h

# Service status
g container status --service agent-cage
g container status --all

# Resource usage
g container resources --deployment claude-talk
```

## Agent Operations

### Agent Types and Coordination

Genesis supports multiple specialized agent types:

- **backend-developer-agent**: API development, database design, microservices
- **frontend-developer-agent**: UI/UX implementation, client-side development
- **qa-automation-agent**: Test automation, quality assurance
- **devops-agent**: Deployment automation, CI/CD pipelines
- **sre-agent**: Incident response, performance optimization
- **security-agent**: Security assessment, vulnerability scanning

### Agent Management

```bash
# Start agents by type
g agent start --type backend-developer --count 2
g agent start --type frontend-developer --count 1
g agent start --type qa-automation --count 1

# Multi-agent coordination
g agent coordinate --task "implement user authentication" --agents backend-developer,frontend-developer,security

# Agent migration
g agent migrate --from legacy --to agent-cage --type backend-developer
```

### Agent Health and Monitoring

```bash
# Check agent health
g agent status --all
g agent health-check --type backend-developer

# Agent logs
g agent logs --type backend-developer --follow
g agent logs --agent-id agent-123 --tail 100
```

## Intelligence Systems

### SOLVE Framework

The SOLVE system provides AI-driven problem resolution:

```bash
# Use solve for complex problems
solve "implement user authentication with OAuth2"
solve "optimize database performance for user queries"
solve "set up monitoring for microservices"

# SOLVE with specific parameters
solve "deploy microservice to production" --environment prod --validate
```

### Auto-Fix System

Automated code repair and optimization:

```bash
# Fix specific files
autofix src/api/auth.py
autofix frontend/src/components/

# Auto-fix with validation
autofix --validate --backup src/
```

### Smart Commit System

Quality gates and automated validation:

```bash
# Use smart commit for all changes
./smart-commit.sh

# Smart commit with specific options
./smart-commit.sh --validate-tests --security-scan
```

## Security & Governance

### Security Features

Genesis includes comprehensive security:

- **Git Branch Protection**: Pre-commit hooks prevent direct commits to main
- **GCP Environment Isolation**: Isolated configurations per environment
- **Secret Management**: Automated secret rotation and access control
- **Security Scanning**: Automated vulnerability and compliance scanning
- **IAM Controls**: Principle of least privilege implementation

### Compliance Management

```bash
# Run compliance scans
g security scan --comprehensive
g compliance validate --framework iso27001
g compliance validate --framework soc2

# Generate compliance reports
g compliance report --framework gdpr --output pdf
```

### Secret Management

```bash
# Secret operations
g secret create --name api-key --environment dev
g secret rotate --name api-key --environment prod
g secret list --environment staging

# Secret access patterns
g secret access-pattern --name database-url --read-only
```

## Monitoring & Observability

### Monitoring Stack

Genesis includes comprehensive monitoring:

- **Metrics**: Prometheus-compatible metrics with Grafana dashboards
- **Logging**: Centralized logging with Cloud Logging
- **Tracing**: Distributed tracing with OpenTelemetry
- **Alerting**: PagerDuty and Slack integrations

### Monitoring Commands

```bash
# View system metrics
g monitor metrics --service agent-cage
g monitor metrics --infrastructure

# Check logs
g monitor logs --service claude-talk --follow
g monitor logs --level error --since 1h

# Alerting status
g monitor alerts --active
g monitor alerts --configure --service agent-cage
```

### Dashboard Management

```bash
# Create dashboards
g monitor dashboard --create --service agent-cage
g monitor dashboard --template infrastructure

# View dashboards
g monitor dashboard --list
g monitor dashboard --open --name agent-performance
```

## Development Workflows

### Feature Development Workflow

1. **Plan the Implementation**
   ```bash
   # Use SOLVE for planning
   solve "implement user dashboard with real-time metrics"
   ```

2. **Set Up Infrastructure**
   ```bash
   # Plan and apply infrastructure
   g infra plan --module vm-management --environment dev
   g infra apply --module vm-management --environment dev
   ```

3. **Create Agent Resources**
   ```bash
   # Create VM pools for development
   g vm create-pool --type backend-developer --size 2
   g vm create-pool --type frontend-developer --size 1
   ```

4. **Deploy Container Services**
   ```bash
   # Deploy development services
   g container deploy --service agent-cage --environment dev
   ```

5. **Start Development Agents**
   ```bash
   # Start coordinated agents
   g agent start --type backend-developer --count 2
   g agent start --type frontend-developer --count 1
   ```

6. **Quality Gates and Commit**
   ```bash
   # Use smart commit for validation
   ./smart-commit.sh
   ```

### Testing Workflow

```bash
# Run comprehensive test suite
pytest tests/ --cov=. --cov-report=html

# Infrastructure validation
g infra validate --all-modules
g cost estimate --environment prod

# Security and compliance
g security scan --comprehensive
g compliance validate --framework iso27001

# Quality gates
./smart-commit.sh
pre-commit run --all-files
```

### Deployment Workflow

```bash
# Production deployment
export ENVIRONMENT=prod
export CONFIRM_PROD=I_UNDERSTAND

# Plan production changes
g infra plan --module container-orchestration --environment prod

# Apply with validation
g infra apply --module container-orchestration --environment prod

# Verify deployment
g container status --all --environment prod
g agent status --all --environment prod
```

## Troubleshooting

### Common Issues and Solutions

#### Infrastructure Issues
```bash
# Check system health
g vm health-check --pool backend-developer
g container logs --service agent-cage --follow

# Infrastructure diagnostics
g infra status --all
g cost analyze

# Fix with intelligence systems
solve "debug infrastructure deployment issues"
autofix terraform/modules/vm-management/
```

#### Agent Issues
```bash
# Agent diagnostics
g agent status --all
g agent logs --type backend-developer --tail 100

# Agent health checks
g agent health-check --type backend-developer
g vm health-check --pool backend-developer
```

#### Container Issues
```bash
# Container diagnostics
g container status --all
g container logs --service claude-talk --follow

# Resource issues
g container resources --deployment agent-cage
g monitor metrics --service claude-talk
```

### Emergency Procedures

If something goes wrong:

1. **System Issues**: Use `g vm health-check` and `g container logs` for diagnostics
2. **Infrastructure Problems**: Run `g infra status --all` and check cost analysis
3. **Code Quality Issues**: Use `autofix` and `./smart-commit.sh` for quality gates
4. **Container Issues**: Check `g container` commands for cluster and deployment status
5. **Intelligence Systems**: Validate solve system and autofix capabilities

### Debug Mode

```bash
# Enable verbose logging
export GENESIS_DEBUG=true
g --verbose vm create-pool --type backend-developer --size 2

# Dry run mode
g --dry-run infra apply --module vm-management --environment prod
```

## Best Practices

### Development Best Practices

1. **Always use smart-commit**: `./smart-commit.sh` for all changes
2. **Environment isolation**: Separate dev/staging/prod environments
3. **Infrastructure as code**: All resources via Terraform modules
4. **Agent coordination**: Use multi-agent development workflows
5. **Quality gates**: Automated validation and testing

### Infrastructure Best Practices

1. **Plan before apply**: Always run `g infra plan` before `g infra apply`
2. **Use appropriate sizing**: Right-size VM pools and container resources
3. **Monitor costs**: Regular `g cost analyze` checks
4. **Security first**: Regular security scans and compliance validation
5. **Backup and recovery**: Ensure proper state backup and disaster recovery

### Agent Management Best Practices

1. **Right-size agent pools**: Match pool size to workload demands
2. **Use health checks**: Regular `g agent health-check` and `g vm health-check`
3. **Monitor performance**: Track agent performance and resource usage
4. **Coordinate workflows**: Use multi-agent coordination for complex tasks
5. **Keep agents updated**: Regular agent updates and migrations

### Security Best Practices

1. **Principle of least privilege**: Minimal required permissions
2. **Regular security scans**: Automated vulnerability scanning
3. **Secret rotation**: Automated secret management and rotation
4. **Compliance monitoring**: Regular compliance validation
5. **Audit logging**: Comprehensive audit trails

### Cost Optimization Best Practices

1. **Use preemptible instances**: For non-critical workloads
2. **Auto-scaling**: Configure appropriate scaling parameters
3. **Resource monitoring**: Regular resource usage analysis
4. **Cost budgets**: Set up budget alerts and controls
5. **Regular cleanup**: Remove unused resources

## Advanced Usage

### Custom Agent Types

```bash
# Create custom agent pools
g vm create-pool --type custom-ml-agent --size 1 --spec ml-optimized

# Deploy custom agent containers
g container deploy --service custom-agent --environment dev --spec custom-config.yaml
```

### Multi-Project Deployment

```bash
# Deploy across multiple projects
g infra apply --multi-project --projects dev,staging,prod
g vm create-pool --multi-environment --pool-config multi-env.yaml
```

### Advanced Monitoring

```bash
# Custom metrics and alerting
g monitor custom-metric --name response_time --service api
g monitor alert-rule --metric response_time --threshold 500ms

# Advanced tracing
g monitor trace --service agent-cage --operation /api/v1/agents
```

### Integration with External Systems

```bash
# External CI/CD integration
g integration setup --type github-actions --project my-project
g integration setup --type gitlab-ci --project my-project

# External monitoring integration
g monitor integration --type datadog --api-key $DATADOG_API_KEY
```

## Getting Help

### Resources

- **Command Help**: Run `g --help` or `g <command> --help` for specific commands
- **Documentation**: Check `/docs` directory for comprehensive guides
- **Component READMEs**: Each component has detailed README files
- **Troubleshooting Guides**: Located in `/docs/04-guides/troubleshooting/`

### Support

For support:
1. Check the [documentation](docs/)
2. Search [existing issues](https://github.com/jhousteau/genesis/issues)
3. Create a new issue if needed
4. Review component-specific README files

### Key Commands Quick Reference

```bash
# Essential commands
g --help                    # Show all commands
g vm create-pool           # Create agent VM pool
g container deploy         # Deploy container service
g infra apply             # Apply infrastructure
g agent start             # Start agents
./smart-commit.sh         # Quality gates and commit
solve "<problem>"         # AI-driven problem solving
autofix <file>            # Automated code repair
```

---

**Genesis: Universal Infrastructure Platform - Write features, not plumbing.**

*Version: 0.2.1 (Alpha)*
*Last Updated: August 24, 2025*
