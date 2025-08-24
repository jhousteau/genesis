# Genesis Templates

Project templates and scaffolding for Genesis Universal Infrastructure Platform.

## Overview

Genesis templates provide production-ready project scaffolding with:
- Pre-configured infrastructure as code
- Best practices implementation
- Security and compliance built-in
- Monitoring and observability
- CI/CD pipeline integration

## Available Templates

### Cloud Run Service (`cloud-run/`)
Serverless HTTP service template for APIs and web applications.

**Features:**
- Cloud Run service with autoscaling
- Cloud SQL database integration
- Identity and Access Management
- Cloud Build CI/CD pipeline
- Monitoring and logging setup

**Use Cases:**
- REST APIs
- Web applications
- Microservices
- Background services

### Cloud Function (`cloud-function/`)
Event-driven serverless function template.

**Features:**
- HTTP or event-triggered functions
- Pub/Sub integration
- Secret Manager integration
- Monitoring and error reporting
- Automated deployment

**Use Cases:**
- Event processing
- API endpoints
- Data transformation
- Integration hooks

### TypeScript Service (`typescript-service/`)
Production-ready TypeScript service with full Genesis integration.

**Features:**
- Express.js framework setup
- TypeScript configuration
- Docker containerization
- GCP service integration
- Jest testing framework
- ESLint and Prettier

**Use Cases:**
- Node.js APIs
- Backend services
- Real-time applications
- GraphQL APIs

### Static Site (`static-site/`)
Static website hosting template with CDN and SSL.

**Features:**
- Cloud Storage hosting
- Cloud CDN integration
- SSL certificate provisioning
- Custom domain support
- Build pipeline integration

**Use Cases:**
- Documentation sites
- Landing pages
- Single-page applications
- Static blogs

### Base Template (`base/`)
Minimal template with core Genesis infrastructure.

**Features:**
- Basic project structure
- Environment configuration
- Security baseline
- Monitoring foundation
- CI/CD skeleton

**Use Cases:**
- Custom project types
- Template customization base
- Learning and experimentation

## Template Structure

Each template follows the Genesis standard structure:

```
template-name/
├── Dockerfile              # Container definition
├── package.json            # Node.js dependencies (if applicable)
├── pyproject.toml          # Python dependencies (if applicable)
├── src/                    # Application source code
│   ├── index.ts|py        # Main entry point
│   ├── config/            # Configuration
│   ├── middleware/        # Request middleware
│   ├── routes/            # API routes
│   ├── services/          # Business logic
│   └── utils/             # Utilities
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── setup.ts|py        # Test configuration
├── scripts/                # Build and deployment scripts
│   └── deploy-to-gcp.sh   # GCP deployment
├── terraform/              # Infrastructure as code
│   ├── main.tf            # Infrastructure definition
│   ├── variables.tf       # Configuration variables
│   └── outputs.tf         # Infrastructure outputs
├── .github/workflows/      # GitHub Actions CI/CD
├── cloudbuild.yaml         # Cloud Build configuration
├── jest.config.js          # Test configuration
└── README.md              # Project documentation
```

## Using Templates

### Create New Project
```bash
# Clone specific template
git clone https://github.com/jhousteau/genesis.git
cd genesis/templates/cloud-run/

# Customize configuration
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your project settings

# Initialize infrastructure
terraform init
terraform plan
terraform apply
```

### Template Customization
```bash
# Copy template for customization
cp -r templates/cloud-run my-custom-service
cd my-custom-service

# Customize application code
# Edit src/ directory with your business logic

# Update infrastructure
# Modify terraform/ directory for your requirements

# Deploy
terraform apply
```

### Integration with Genesis CLI
```bash
# List available templates
g templates list

# Create project from template
g new my-project --template cloud-run

# Deploy project
g deploy --project my-project --environment dev
```

## Template Development

### Creating New Templates
1. Copy base template: `cp -r templates/base templates/my-template`
2. Implement application logic in `src/`
3. Configure infrastructure in `terraform/`
4. Add tests in `tests/`
5. Update documentation
6. Test deployment end-to-end

### Template Standards
- **Security First** - All templates include security best practices
- **Monitoring Ready** - Built-in observability and alerting
- **Environment Isolation** - Support for dev/staging/prod
- **CI/CD Integration** - GitHub Actions and Cloud Build
- **Documentation** - Comprehensive README and inline documentation

### Template Validation
```bash
# Validate template structure
./scripts/validate-template.sh template-name

# Test template deployment
./scripts/test-template.sh template-name

# Security scan template
bandit -r templates/template-name/src/
```

## Template Features

### Built-in Security
- Service account with minimal permissions
- Secret Manager integration
- HTTPS enforcement
- Identity and Access Management
- Security scanning integration

### Monitoring and Observability
- Cloud Logging integration
- Cloud Monitoring metrics
- Error Reporting
- Cloud Trace for distributed tracing
- Health check endpoints

### Performance Optimization
- Caching strategies
- Connection pooling
- Resource optimization
- Autoscaling configuration
- CDN integration where applicable

### Development Experience
- Local development setup
- Hot reload for development
- Debugging configuration
- Test framework integration
- Code quality tools

## Integration Points

### Genesis Core Integration
Templates automatically include:
- Error handling from `core/errors/`
- Retry logic from `core/retry/`
- Health checks from `core/health/`
- Context management from `core/context/`

### Intelligence Integration
- Smart commit system integration
- SOLVE framework integration
- Auto-fix system integration
- Quality gates integration

### Governance Integration
- Policy compliance validation
- Security scanning integration
- Cost optimization
- Audit logging

## Maintenance

### Template Updates
Templates are regularly updated with:
- Security patches
- Performance improvements
- New Genesis features
- Best practice updates

### Version Management
Templates follow semantic versioning:
- **Major** - Breaking changes
- **Minor** - New features, backward compatible
- **Patch** - Bug fixes and security updates

## See Also

- [Getting Started Guide](../docs/01-getting-started/quickstart.md) - Using templates
- [CLI Commands](../cli/README.md) - Template management commands
- [Infrastructure Modules](../modules/README.md) - Terraform modules used by templates
- [Core Libraries](../core/README.md) - Shared libraries included in templates

---

**Genesis Templates** - Production-ready project scaffolding with best practices built-in.
