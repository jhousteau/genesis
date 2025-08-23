# Genesis Terraform Modules

Production-ready Terraform modules for Google Cloud Platform infrastructure. These modules provide opinionated, secure, and scalable infrastructure patterns following cloud-native best practices.

## 🏗️ Available Modules

### Core Infrastructure

#### Bootstrap Module (`bootstrap/`)

Initial project setup and foundational infrastructure.

**Resources:**

- GCP project configuration
- Essential API enablement
- Service account creation
- Initial IAM bindings

#### State Backend Module (`state-backend/`)

Terraform state management infrastructure.

**Resources:**

- Cloud Storage bucket for state files
- State file encryption and versioning
- Access controls and locking

### Compute Modules

#### Compute Module (`compute/`)

Comprehensive compute infrastructure including serverless and container orchestration.

**Resources:**

- Google Kubernetes Engine (GKE) clusters
- Cloud Run services
- Compute Engine instances
- Load balancers and ingress

#### Networking Module (`networking/`)

VPC and network security infrastructure.

**Resources:**

- VPC networks and subnets
- Firewall rules and security policies
- Cloud NAT and routers
- Private service connections

### Data Modules

#### Data Module (`data/`)

Storage and database infrastructure.

**Resources:**

- Cloud Storage buckets
- Cloud SQL databases
- Firestore databases
- BigQuery datasets

### Security Modules

#### Service Accounts Module (`service-accounts/`)

Service account management and IAM configuration.

**Resources:**

- Service account creation
- IAM role bindings
- Key management and rotation
- Cross-project permissions

#### Workload Identity Module (`workload-identity/`)

Secure CI/CD authentication without service account keys.

**Resources:**

- Workload Identity pool and providers
- GitHub Actions integration
- GitLab CI integration
- Azure DevOps integration

#### Security Module (`security/`)

Comprehensive security infrastructure.

**Resources:**

- Secret Manager configuration
- Security scanning setup
- Compliance monitoring
- Audit logging

### Project Management

#### Multi-Project Module (`multi-project/`)

Enterprise-scale multi-project management.

**Resources:**

- Project factory patterns
- Organization policies
- Shared VPC configuration
- Centralized logging and monitoring

## 🚀 Usage Patterns

### Single Project Deployment

```hcl
# environments/dev/main.tf
module "bootstrap" {
  source = "../../modules/bootstrap"

  project_id = var.project_id
  environment = "dev"
}

module "networking" {
  source = "../../modules/networking"

  project_id = var.project_id
  environment = "dev"

  depends_on = [module.bootstrap]
}

module "compute" {
  source = "../../modules/compute"

  project_id = var.project_id
  environment = "dev"
  network_name = module.networking.network_name

  depends_on = [module.networking]
}
```

### Multi-Environment Setup

```hcl
# environments/prod/main.tf
module "prod_infrastructure" {
  source = "../../modules/multi-project"

  environments = {
    dev = {
      project_id = "my-project-dev"
      region = "us-central1"
    }
    staging = {
      project_id = "my-project-staging"
      region = "us-central1"
    }
    prod = {
      project_id = "my-project-prod"
      region = "us-central1"
    }
  }
}
```

### Workload Identity for CI/CD

```hcl
module "workload_identity" {
  source = "../../modules/workload-identity"

  project_id = var.project_id

  github_repos = [
    "organization/repository"
  ]

  service_accounts = {
    "ci-cd" = {
      roles = [
        "roles/run.admin",
        "roles/storage.admin"
      ]
    }
  }
}
```

## 🔧 Module Standards

### Naming Conventions

- **Resources**: Use descriptive names with environment prefixes
- **Variables**: Clear, documented with validation rules
- **Outputs**: Comprehensive with descriptions

### Security Practices

- **Least Privilege**: Minimal required permissions
- **Encryption**: All data encrypted at rest and in transit
- **Network Security**: Private endpoints and firewall rules
- **Audit Logging**: Comprehensive logging and monitoring

### Operational Features

- **Health Checks**: Built-in monitoring and alerting
- **Backup & Recovery**: Automated backup strategies
- **Disaster Recovery**: Multi-region failover capabilities
- **Cost Optimization**: Resource quotas and cost controls

## 📚 Documentation

Each module includes comprehensive documentation:

- `README.md` - Usage examples and configuration
- `variables.tf` - Input variable definitions
- `outputs.tf` - Output value definitions
- `versions.tf` - Provider requirements
- `examples/` - Complete usage examples

## 🧪 Testing

### Module Validation

```bash
# Validate all modules
for module in modules/*/; do
  echo "Validating $module"
  cd "$module"
  terraform init
  terraform validate
  cd -
done
```

### Integration Testing

```bash
# Test module integration
cd examples/complete-deployment
terraform init
terraform plan
terraform apply -auto-approve
terraform destroy -auto-approve
```

## 🔗 Integration

### With Genesis Core

Modules automatically integrate with Genesis Core for:

- Structured logging and monitoring
- Health checks and observability
- Error handling and retry logic

### With Intelligence System

Modules support:

- Infrastructure as code generation from SOLVE graphs
- Template evolution based on usage patterns
- Automated compliance validation

## 🛠️ Development

### Adding New Modules

1. Create module directory with standard structure:

   ```
   modules/new-module/
   ├── README.md
   ├── main.tf
   ├── variables.tf
   ├── outputs.tf
   ├── versions.tf
   └── examples/
   ```

2. Follow naming and security conventions
3. Add comprehensive tests and documentation
4. Update this index README

### Module Guidelines

- **Single Responsibility**: Each module has one clear purpose
- **Composability**: Modules work together seamlessly
- **Flexibility**: Support multiple use cases through variables
- **Security**: Security-first design and implementation

## 📊 Module Matrix

| Module | Use Case | Complexity | Dependencies |
|--------|----------|------------|--------------|
| bootstrap | Project setup | Low | None |
| state-backend | State management | Low | None |
| networking | VPC infrastructure | Medium | bootstrap |
| compute | Application hosting | High | networking |
| data | Storage & databases | Medium | networking |
| security | Security controls | High | bootstrap |
| service-accounts | IAM management | Medium | bootstrap |
| workload-identity | CI/CD auth | High | service-accounts |
| multi-project | Enterprise setup | Very High | All others |

## 🎯 Roadmap

- **v1.1**: Advanced monitoring integration
- **v1.2**: Multi-cloud support (AWS, Azure)
- **v1.3**: Serverless-first architectures
- **v1.4**: AI/ML infrastructure modules

---

**Terraform Modules** - Infrastructure as code, done right.
