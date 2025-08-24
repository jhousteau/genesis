# Claude AI Assistant Instructions for Genesis

## Project Context
- **Name**: Genesis - Universal Project Platform
- **Type**: Infrastructure Platform and Development Framework
- **Architecture**: Cloud-native, serverless-first with GCP focus
- **Languages**: Python (Poetry), Node.js/TypeScript, Go, Bash, Terraform
- **Specialization**: Intelligent automation, multi-environment isolation, comprehensive testing
- **Key Components**: CLI tooling, Intelligence systems (solve/autofix), Container orchestration, VM management

## Project Standards
This project follows the Genesis Universal Project Platform standards:

### Development Workflow
- **Smart Commits**: Always use `./smart-commit.sh` or intelligence/smart-commit system
- **Testing**: All code changes require comprehensive testing (pytest, integration tests)
- **Quality Gates**: Pre-commit hooks, linting, and automated validation
- **CLI Operations**: Use `g` command for VM, container, infrastructure, and agent management
- **Intelligence Systems**: Leverage solve, autofix, and optimization systems

### GCP Integration
- **Isolation**: Each project has its own GCP project and gcloud config
- **Authentication**: Use service account impersonation (no local keys)
- **Deployment**: Multi-environment deployment patterns
- **Monitoring**: Built-in Cloud Operations integration

### Security Requirements
- No hardcoded secrets (use Secret Manager)
- All temp files go in `temp/` directory
- Regular security scanning and compliance validation
- Follow principle of least privilege across all agents

## Genesis Platform Architecture

Genesis provides a comprehensive infrastructure platform with integrated tooling:

### Core Platform Components
- **CLI Interface**: Comprehensive `g` command for all operations (VM, container, infrastructure, agent)
- **Intelligence Systems**: solve, autofix, optimization, and prediction capabilities
- **Multi-Environment Isolation**: GCP project separation with automated credential management
- **Container Orchestration**: GKE-based platform with agent-cage and claude-talk integration
- **VM Management**: Automated agent pools with autoscaling and health monitoring

### Infrastructure Management
- **Terraform Modules**: Comprehensive infrastructure as code with validation
- **Cost Control**: Advanced cost optimization and budget enforcement
- **Security Controls**: Comprehensive governance and compliance automation
- **Monitoring**: Cloud Operations integration with custom dashboards

### Development Workflow Integration
- **Quality Gates**: Smart-commit system with automated validation
- **Testing Framework**: Comprehensive pytest-based testing with coverage
- **CI/CD Pipelines**: Multi-platform deployment automation
- **Secret Management**: Automated secret rotation and access control

### How to Use Genesis Platform

#### CLI Operations
Use the Genesis CLI for all infrastructure operations:
```bash
# VM Management
g vm create-pool --type backend-developer --size 3
g vm health-check --pool backend-pool

# Container Operations
g container deploy --service agent-cage --environment dev
g container logs --service claude-talk --follow

# Infrastructure Management
g infra plan --module vm-management --environment dev
g infra apply --module container-orchestration --environment prod
```

#### Intelligence System Integration
Leverage AI-driven development tools:
```bash
# Problem solving and code generation
solve "implement user authentication with OAuth2"

# Automated code repair
autofix src/api/auth.py

# Quality gates and commit orchestration
./smart-commit.sh
```

### Genesis Platform Best Practices

#### When Planning Complex Features:
1. Use **intelligence systems** for problem analysis and solution design
2. Plan **infrastructure** with Terraform modules and cost analysis
3. Implement with **comprehensive testing** and quality gates
4. Deploy through **container orchestration** with health monitoring
5. Monitor with **observability stack** and automated alerting

#### When Debugging Issues:
1. Use **CLI diagnostics** for system health and log analysis
2. Leverage **intelligence systems** for automated problem resolution
3. Check **infrastructure status** and cost analysis
4. Review **container health** and scaling metrics
5. Validate **security controls** and compliance status

#### When Implementing New Systems:
1. **Design infrastructure** with Terraform modules and validation
2. **Provision resources** through automated deployment pipelines
3. **Implement components** with testing and quality gates
4. **Deploy services** through container orchestration
5. **Monitor operations** with comprehensive observability
6. **Maintain compliance** with automated governance controls

### Proactive Platform Usage

#### For Complex Tasks:
"This is a complex multi-service implementation - I'll use the solve system to break this down and plan the implementation"

#### For Infrastructure Decisions:
"This system design needs infrastructure planning - I'll use the Genesis CLI to plan and validate the Terraform modules"

#### For Quality Concerns:
"This code needs quality validation - I'll use the autofix system and smart-commit for comprehensive quality gates"

## AI Assistant Guidelines

### Always Do
1. **Use Genesis CLI**: Use `g` command for infrastructure, VM, container, and agent operations
2. **Follow Smart Commit**: Use `./smart-commit.sh` for all changes with quality gates
3. **Run Tests**: Use `pytest` for Python components, ensure comprehensive test coverage
4. **Check Project Health**: Run validation scripts before making changes
5. **Use Intelligence Systems**: Leverage solve/autofix systems for complex problem resolution

### Genesis CLI Command Guidelines
- **VM Operations**: `g vm` - Create pools, scale, health checks, lifecycle management
- **Container Management**: `g container` - GKE clusters, deployments, services, logs
- **Infrastructure**: `g infra` - Terraform operations, cost analysis, validation
- **Agent Operations**: `g agent` - Start/stop agents, migration, cage/claude-talk management
- **Intelligence Systems**: Direct CLI access to solve, autofix, optimization tools
- **Quality Gates**: Use `./smart-commit.sh` for all commits with automated validation

### Never Do
1. **Don't bypass quality gates**: Always use smart-commit and proper workflows
2. **Don't hardcode values**: Use environment variables and Secret Manager
3. **Don't skip tests**: All changes must have corresponding tests
4. **Don't bypass isolation**: Respect GCP project boundaries and environment separation
5. **Don't ignore CLI patterns**: Use established `g` command patterns for operations

### Intelligence System Integration
Genesis includes sophisticated intelligence systems:
- **Smart-commit**: Interactive commit system with quality gates (`./smart-commit.sh`)
- **Solve system**: AI-driven problem resolution and build planning (`intelligence/solve/`)
- **Auto-fix**: Intelligent code repair and optimization (`intelligence/autofix/`)
- **CLI Integration**: Comprehensive command interface for all operations (`cli/`)
- **Container Orchestration**: GKE cluster and deployment management
- **VM Management**: Agent VM pools and lifecycle management

### Common Workflows

#### Feature Development:
```bash
# 1. Plan infrastructure
g infra plan --module <module> --environment <env>

# 2. Create/update components
# Use intelligence systems for complex implementations
solve <problem-description>

# 3. Test implementation
pytest tests/
g vm health-check --pool <pool>

# 4. Quality gates
./smart-commit.sh

# 5. Deploy
g container deploy --service <service> --environment <env>
g infra apply --module <module>
```

#### Troubleshooting:
```bash
# 1. Check system health
g vm health-check --pool <pool>
g container logs --service <service> --follow

# 2. Infrastructure diagnostics
g infra status --all
g cost analyze

# 3. Use intelligence systems
solve "debug <issue-description>"
autofix <file-path>

# 4. Test and commit fixes
pytest tests/
./smart-commit.sh
```

### Emergency Procedures
If something goes wrong:

1. **System Issues**: Use `g vm health-check` and `g container logs` for diagnostics
2. **Infrastructure Problems**: Run `g infra status --all` and check cost analysis
3. **Code Quality Issues**: Use `autofix` and `./smart-commit.sh` for quality gates
4. **Container Issues**: Check `g container` commands for cluster and deployment status
5. **Intelligence Systems**: Validate solve system and autofix capabilities

### Genesis-Specific Integration Points
- **Genesis CLI (`g`)**: Comprehensive project and infrastructure management
- **Intelligence Layer**: solve, autofix, optimization, and prediction systems
- **Multi-environment**: Dev, staging, production isolation with GCP project separation
- **Monitoring**: Cloud Operations integration with custom dashboards and alerting
- **Container Platform**: GKE-based orchestration with agent-cage and claude-talk support
- **VM Management**: Automated agent VM pools with autoscaling and health monitoring

## Key Directory Structure

- **`/cli/`**: Genesis CLI implementation with comprehensive command structure
- **`/intelligence/`**: AI-driven systems (solve, autofix, smart-commit, optimization)
- **`/core/`**: Platform core components (context, health, lifecycle, security, secrets)
- **`/modules/`**: Terraform modules for infrastructure provisioning
- **`/templates/`**: Project templates and scaffolding
- **`/monitoring/`**: Comprehensive observability and alerting systems
- **`/tests/`**: Comprehensive test suite with integration and e2e testing
- **`/governance/`**: Compliance, cost control, and policy management
- **`/isolation/`**: Multi-cloud isolation and credential management
- **`./smart-commit.sh`**: Interactive commit system with quality gates

## Testing and Quality Assurance

### Testing Framework
- **Unit Testing**: pytest-based testing framework with comprehensive coverage
- **Integration Testing**: Cross-component testing with real GCP services
- **End-to-End Testing**: Complete workflow validation with automated scenarios
- **Performance Testing**: Load testing and cost optimization validation
- **Security Testing**: Comprehensive security scanning and compliance validation

### Quality Gates
- **Smart Commit System**: Interactive commit process with automated quality validation
- **Pre-commit Hooks**: Automated linting, formatting, and security scanning
- **CI/CD Pipeline**: Automated testing, building, and deployment validation
- **Infrastructure Validation**: Terraform plan validation and cost analysis
- **Container Health Checks**: Automated health monitoring and rollback capabilities

### Key Commands for Quality Assurance
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
./smart-commit.sh  # Interactive commit with quality validation
pre-commit run --all-files  # Run all quality checks
```

This Genesis-specific configuration provides a comprehensive platform for infrastructure management, intelligent automation, and quality-assured development workflows while maintaining security, compliance, and operational excellence.
