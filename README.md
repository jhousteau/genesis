# Genesis - Universal Cloud Platform

A comprehensive, production-ready infrastructure platform for Google Cloud Platform with intelligent automation, comprehensive monitoring, and built-in security best practices.

## 🚀 Features

### Core Capabilities
- **Multi-Environment Support**: Isolated configurations for dev, test, staging, and production
- **Intelligent Automation**: SOLVE integration for smart problem-solving and orchestration
- **Security First**: Git branch protection, GCP environment isolation, and comprehensive security scanning
- **Infrastructure as Code**: Complete Terraform modules for GCP resources
- **Comprehensive Monitoring**: Integrated logging, metrics, tracing, and alerting
- **CI/CD Integration**: GitHub Actions, GitLab CI, and Cloud Build support

### Recent Additions
- **Git Branch Protection**: Pre-commit and pre-push hooks to prevent direct commits to main
- **GCloud Environment Isolation**: Per-repository isolated configurations preventing cross-contamination
- **Smart Commit System**: Intelligent commit validation and quality gates
- **Workload Identity Federation**: Secure CI/CD without service account keys

## 📋 Prerequisites

- **Google Cloud SDK** (`gcloud`) installed and configured
- **Terraform** >= 1.5
- **Python** >= 3.11 (for intelligent automation features)
- **Poetry** (for Python dependency management)
- **direnv** (for automatic environment loading)
- **Git** >= 2.28
- Active GCP account with billing enabled
- Appropriate IAM permissions (Project Editor or Owner)

## 🚀 Quick Start

### 1. Initial Setup

```bash
# Clone the repository
git clone https://github.com/jhousteau/genesis.git
cd genesis

# Allow direnv to load environment
direnv allow

# Run the bootstrap script
./scripts/bootstrap.sh
```

The bootstrap will:
- Set up isolated GCP configurations
- Enable required APIs
- Create Terraform backend storage
- Configure security protections
- Initialize development environment

### 2. Environment Configuration

```bash
# The environment is automatically configured via .envrc
# Default is 'dev', switch environments with:
ENVIRONMENT=staging direnv allow
ENVIRONMENT=prod direnv allow
```

### 3. Install Git Protections

```bash
# Install pre-commit hooks (automatic branch protection)
pre-commit install

# Verify protection is active
git commit -m "test" # Should fail on main branch
```

## 🏗️ Project Structure

```
genesis/
├── .envrc                    # Automatic environment configuration
├── .pre-commit-config.yaml   # Git hooks and validations
├── config/
│   ├── project.env          # Central project configuration
│   └── environments/        # Environment-specific settings
│       ├── dev.env
│       ├── test.env
│       ├── staging.env
│       └── prod.env
├── scripts/
│   ├── bootstrap_gcloud.sh  # GCP isolation setup
│   ├── gcloud_guard.sh      # Protection against wrong-project operations
│   └── bootstrap.sh         # Main initialization script
├── modules/                 # Terraform modules
│   ├── bootstrap/          # Project bootstrapping
│   ├── compute/            # GKE, Cloud Run, VMs
│   ├── networking/         # VPC, subnets, firewall
│   ├── data/              # Storage, databases
│   ├── security/          # IAM, secrets, policies
│   └── workload-identity/ # WIF configuration
├── environments/           # Environment-specific Terraform
│   ├── dev/
│   ├── test/
│   ├── staging/
│   └── prod/
├── intelligence/          # Intelligent automation
│   ├── solve/            # Problem-solving orchestrator
│   ├── autofix/          # Automated issue resolution
│   └── smart-commit/     # Intelligent commit system
├── monitoring/           # Observability stack
│   ├── alerts/          # Alert rules and routing
│   ├── dashboards/      # Grafana and GCP dashboards
│   └── logging/         # Centralized logging
├── docs/                # Comprehensive documentation
│   ├── 00-overview/
│   ├── 01-getting-started/
│   ├── 04-guides/
│   │   ├── git-branch-protection.md
│   │   └── gcp-isolation.md
│   └── 05-operations/
└── tests/              # Testing suite

```

## 🔒 Security Features

### Git Branch Protection
- **Pre-commit hooks** prevent direct commits to main/master
- **Pre-push hooks** block direct pushes to protected branches
- **Quality gates** ensure code standards before commits
- See [Git Branch Protection Guide](docs/04-guides/git-branch-protection.md)

### GCP Environment Isolation
- **Isolated configurations** per environment and repository
- **Automatic environment detection** and configuration
- **Production safeguards** with confirmation requirements
- **Audit logging** of all GCP operations
- See [GCP Isolation Guide](docs/04-guides/gcp-isolation.md)

### Security Scanning
- **Secret detection** with gitleaks
- **Terraform security** validation
- **Dependency scanning** for vulnerabilities
- **Compliance checks** for SOC2, ISO27001, GDPR

## 🚀 Deployment

### Development Environment
```bash
cd environments/dev
terraform init
terraform plan
terraform apply
```

### Production Deployment
```bash
# Production requires explicit confirmation
ENVIRONMENT=prod direnv allow
export CONFIRM_PROD=I_UNDERSTAND

cd environments/prod
terraform plan -out=tfplan
terraform apply tfplan
```

## 📊 Monitoring & Observability

- **Metrics**: Prometheus-compatible metrics with Grafana dashboards
- **Logging**: Centralized logging with Cloud Logging
- **Tracing**: Distributed tracing with OpenTelemetry
- **Alerting**: PagerDuty and Slack integrations
- **SLO Monitoring**: Service level objectives tracking

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test suites
pytest tests/unit
pytest tests/integration
pytest tests/e2e

# Run pre-commit checks
pre-commit run --all-files
```

## 📚 Documentation

- [Architecture Overview](docs/00-overview/ARCHITECTURE_PLAN.md)
- [Getting Started Guide](docs/01-getting-started/quickstart.md)
- [Git Branch Protection](docs/04-guides/git-branch-protection.md)
- [GCP Environment Isolation](docs/04-guides/gcp-isolation.md)
- [API Reference](docs/03-api-reference/)
- [Operations Runbooks](docs/05-operations/runbooks/)

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (using smart-commit)
4. Push to your branch
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
poetry install

# Install pre-commit hooks
pre-commit install

# Run tests before committing
make test
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built on proven patterns from agent-cage architecture
- Incorporates best practices from Google Cloud Platform
- Uses Keep a Changelog format for version tracking

## 🔗 Links

- [Project Repository](https://github.com/jhousteau/genesis)
- [Issue Tracker](https://github.com/jhousteau/genesis/issues)
- [Documentation](docs/)
- [Changelog](CHANGELOG.md)
- [Release Notes](RELEASE_NOTES.md)

## 📞 Support

For support, please:
1. Check the [documentation](docs/)
2. Search [existing issues](https://github.com/jhousteau/genesis/issues)
3. Create a new issue if needed

---

**Current Version**: 0.2.1 (Alpha)
**Last Updated**: August 22, 2025
