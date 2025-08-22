# Claude AI Assistant Instructions for Genesis

## Project Context
- **Name**: Genesis - Universal Project Platform
- **Type**: Infrastructure Platform and Development Framework
- **Architecture**: Cloud-native, serverless-first with GCP focus
- **Languages**: Python (Poetry), Node.js/TypeScript, Go, Bash, Terraform
- **Specialization**: Multi-agent coordination and intelligent automation

## Project Standards
This project follows the Genesis Universal Project Platform standards:

### Development Workflow
- **Smart Commits**: Always use `./scripts/smart-commit.sh` or intelligence layer
- **Testing**: All code changes require comprehensive testing
- **Quality Gates**: Pre-commit hooks, linting, and automated validation
- **Agent Coordination**: Leverage specialized agents for complex workflows

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

## Agent Delegation Framework

Genesis uses a sophisticated multi-agent architecture with clear hierarchy and delegation patterns:

### Executive Level Agents
- **project-manager-agent**: Overall coordination and resource allocation
- **architect-agent**: System design and architectural decisions
- **tech-lead-agent**: Development standards and code quality

### Implementation Level Agents
- **platform-engineer-agent**: Infrastructure implementation
- **backend-developer-agent**: Server-side development
- **frontend-developer-agent**: Client-side development
- **data-engineer-agent**: Data pipelines and analytics
- **integration-agent**: System integration and APIs

### Quality & Operations Level Agents
- **qa-automation-agent**: Quality assurance and testing
- **sre-agent**: Site reliability and incident response
- **security-agent**: Security assessment and compliance
- **devops-agent**: Deployment and CI/CD automation

### How to Use Agents

#### Direct Invocation
Use explicit delegation for specific tasks:
```
"Use the architect-agent to design the microservices architecture"
"Delegate to backend-developer-agent for API implementation"
"Have the security-agent review this for vulnerabilities"
```

#### Automatic Delegation
Agents will auto-select based on task triggers. All agent descriptions include "MUST BE USED when..." patterns for automatic matching.

#### Sequential Coordination
For complex projects, use coordination patterns:
```
User Request → project-manager-agent → architect-agent → implementation agents → quality agents
```

#### Parallel Processing
For independent workstreams:
```
project-manager-agent coordinates:
├── backend-developer-agent (API development)
├── frontend-developer-agent (UI development)  
├── platform-engineer-agent (infrastructure)
└── security-agent (security validation)
```

### Agent Collaboration Best Practices

#### When Planning Complex Features:
1. Start with **project-manager-agent** for breakdown and coordination
2. Engage **architect-agent** for system design decisions
3. Use specialized implementation agents for development
4. Coordinate with **qa-automation-agent** for testing strategy
5. Have **devops-agent** handle deployment automation

#### When Debugging or Issues:
1. Use **sre-agent** for incident response and system debugging
2. Engage **security-agent** for security-related issues
3. Use **tech-lead-agent** for code quality problems
4. Escalate to **project-manager-agent** for coordination needs

#### When Implementing New Systems:
1. **architect-agent** designs the system architecture
2. **platform-engineer-agent** provisions infrastructure
3. Development agents implement their respective components
4. **integration-agent** handles service communication
5. **security-agent** validates security measures
6. **qa-automation-agent** ensures comprehensive testing

### Proactive Agent Usage

#### For Complex Tasks:
"This is a complex multi-service implementation - I'll use the project-manager-agent to coordinate this properly"

#### For Architecture Decisions:
"This system design needs architectural review - I'll engage the architect-agent for SOLID-CLOUD principles"

#### For Quality Concerns:
"This code needs quality validation - I'll use the tech-lead-agent for MENTOR methodology guidance"

## AI Assistant Guidelines

### Always Do
1. **Use Agent Delegation**: For complex tasks, delegate to appropriate specialized agents
2. **Follow Smart Commit**: Use `./scripts/smart-commit.sh` for all changes
3. **Respect Agent Hierarchy**: Follow delegation chains and authority structures
4. **Check Project Health**: Run validation before making changes
5. **Coordinate Multi-Agent Work**: Use project-manager-agent for complex coordination

### Agent Selection Guidelines
- **Planning & Coordination**: project-manager-agent
- **System Design**: architect-agent  
- **Code Quality**: tech-lead-agent
- **Infrastructure**: platform-engineer-agent
- **Backend Development**: backend-developer-agent
- **Frontend Development**: frontend-developer-agent
- **Data Processing**: data-engineer-agent
- **Service Integration**: integration-agent
- **Quality Assurance**: qa-automation-agent
- **Incident Response**: sre-agent
- **Security**: security-agent
- **Deployment**: devops-agent

### Never Do
1. **Don't bypass quality gates**: Always use smart-commit and proper workflows
2. **Don't skip agent delegation**: Use specialized agents for their expertise areas
3. **Don't break agent hierarchy**: Respect reporting structures and authority
4. **Don't hardcode values**: Use environment variables and Secret Manager
5. **Don't ignore agent recommendations**: Trust specialized agent expertise

### Intelligence System Integration
Genesis includes sophisticated intelligence systems:
- **Smart-commit**: Automated quality gates and commit orchestration
- **Solve system**: AI-driven problem resolution and code generation
- **Auto-fix**: Intelligent code repair and optimization
- **Agent coordination**: Multi-agent workflow orchestration

### Common Agent Workflows

#### Feature Development:
```bash
# 1. Plan with project management
"Use the project-manager-agent to break down this feature into tasks"

# 2. Design architecture
"Delegate to architect-agent for system design"

# 3. Implement components
"Use backend-developer-agent for API implementation"
"Use frontend-developer-agent for UI implementation"

# 4. Ensure quality
"Have qa-automation-agent create comprehensive tests"

# 5. Deploy
"Use devops-agent for deployment automation"
```

#### Troubleshooting:
```bash
# 1. Incident response
"Use sre-agent to investigate this production issue"

# 2. Security assessment (if needed)
"Have security-agent check for security implications"

# 3. Code quality review
"Use tech-lead-agent to review code quality issues"

# 4. Coordinate resolution
"Use project-manager-agent to coordinate the fix across teams"
```

### Emergency Procedures
If something goes wrong:

1. **System Issues**: Use sre-agent for incident response
2. **Security Concerns**: Engage security-agent immediately  
3. **Code Quality Problems**: Use tech-lead-agent for resolution
4. **Project Coordination**: Escalate to project-manager-agent
5. **Check Intelligence Systems**: Validate smart-commit and solve systems

### Genesis-Specific Integration Points
- **Bootstrap CLI**: Project setup and management
- **Intelligence Layer**: AI-driven analysis and optimization
- **Multi-environment**: Dev, staging, production isolation
- **Monitoring**: Comprehensive observability stack
- **Agent Registry**: Dynamic agent discovery and coordination

## Agent Methodologies Reference

- **RAPID** (Project Manager): Requirements, Allocation, Planning, Implementation, Delivery
- **SOLID-CLOUD** (Architect): Single responsibility, Open/closed, Liskov substitution, Interface segregation, Dependency inversion + Cloud-native, Lifecycle, Observability, User-centric, Data architecture
- **MENTOR** (Tech Lead): Measure, Evaluate, Nurture, Transform, Optimize, Review
- **PIPES** (Platform Engineer): Provision, Integration, Protection, Evolution, Standardization
- **CRAFT** (Backend Developer): Create, Refactor, Authenticate, Function, Test
- **REACT** (Frontend Developer): Responsive, Efficient, Accessible, Connected, Tested
- **STREAM** (Data Engineer): Source, Transform, Route, Enrich, Analyze, Monitor
- **CONNECT** (Integration): Compose, Orchestrate, Negotiate, Network, Error-handle, Test
- **VERIFY** (QA Automation): Validate, Execute, Report, Integrate, Fix, Yield
- **SPIDER** (SRE): Symptom identification, Problem isolation, Investigation, Diagnosis, Execution, Review
- **SHIELD** (Security): Scan, Harden, Isolate, Encrypt, Log, Defend
- **DEPLOY** (DevOps): Design, Environments, Pipelines, Launch, Orchestrate, Yield

This Genesis-specific configuration leverages the full power of the multi-agent architecture while maintaining the platform's standards for quality, security, and operational excellence.