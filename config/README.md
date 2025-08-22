# Genesis Configuration

This directory contains all configuration files for the Genesis platform, providing centralized management of project settings, environment variables, and deployment configurations.

## 📁 Directory Structure

```
config/
├── project.env           # Central project configuration
├── environments/         # Environment-specific settings
│   ├── dev.env          # Development environment
│   ├── test.env         # Test environment
│   ├── staging.env      # Staging environment
│   └── prod.env         # Production environment
├── global.yaml          # Global configuration (if present)
└── unified_config.py    # Configuration loader utilities
```

## 🔧 Configuration Files

### `project.env`

Central configuration file defining project-wide settings and constants.

**Key Sections:**
- **Core Project Identity**: Project name, description, repository details
- **Infrastructure Naming**: Patterns for all GCP resources
- **Service Definitions**: Lists of core, intelligence, and infrastructure services
- **Environment Definitions**: Environment names and PROJECT_IDs
- **Infrastructure Defaults**: Default values for all infrastructure settings
- **Utility Functions**: Helper functions for pattern expansion

**Usage:**
```bash
# Source in scripts
source config/project.env

# Use variables
echo $PROJECT_NAME
echo $DEFAULT_REGION

# Use functions
get_project_id "dev"
get_tf_state_bucket "staging"
```

### Environment Files (`environments/*.env`)

Environment-specific configurations that override or extend project defaults.

**Common Variables:**
- `ENVIRONMENT`: Environment identifier (dev/test/staging/prod)
- `PROJECT_ID`: GCP project ID for this environment
- `REGION`: Primary region
- `ZONE`: Primary zone
- Resource configurations (compute, storage, networking)
- Security settings
- Monitoring configurations
- Cost management settings

## 🌍 Environment Configuration

### Development (`dev.env`)
- **Purpose**: Local development and experimentation
- **Characteristics**:
  - Preemptible instances for cost savings
  - Public IPs enabled for easier access
  - Minimal backups and retention
  - Debug mode enabled
  - Auto-shutdown after 4 hours

### Test (`test.env`)
- **Purpose**: Automated testing and CI/CD
- **Characteristics**:
  - Ephemeral resources
  - Test data generation enabled
  - Full monitoring for test analysis
  - Auto-cleanup policies
  - Integration with CI/CD pipelines

### Staging (`staging.env`)
- **Purpose**: Pre-production validation
- **Characteristics**:
  - Production-like configuration
  - High availability enabled
  - Full backup and recovery
  - Performance testing enabled
  - Manual deployment approval

### Production (`prod.env`)
- **Purpose**: Live production environment
- **Characteristics**:
  - No preemptible instances
  - Private IPs only
  - Full redundancy and HA
  - Comprehensive monitoring
  - Strict change controls
  - Deletion protection enabled

## 🔒 Security Configuration

### Production Safeguards
Production configurations include additional safety measures:
```bash
# Required for production operations
export CONFIRM_PROD=I_UNDERSTAND

# Deletion protection
ENABLE_DELETION_PROTECTION=true

# Resource locks
ENABLE_RESOURCE_LOCKS=true
```

### Sensitive Variables
Never commit sensitive values. Use placeholders:
```bash
# Use environment variables
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL_PROD}"

# Or Secret Manager references
DB_PASSWORD="sm://genesis-prod/db-password"
```

## 📝 Configuration Patterns

### Resource Naming
All resources follow consistent naming patterns:
```bash
# Pattern definition
VM_NAME_PATTERN="${APP_NAME}-vm-{service}-{environment}"

# Expansion
expand_full_pattern "$VM_NAME_PATTERN" "dev" "api"
# Result: genesis-vm-api-dev
```

### Project ID Mapping
```bash
PROJECT_ID_DEV="your-project-dev"
PROJECT_ID_TEST="your-project-test"
PROJECT_ID_STAGING="your-project-staging"
PROJECT_ID_PROD="your-project-prod"
```

## 🚀 Usage

### In Scripts
```bash
#!/usr/bin/env bash
source config/project.env
source config/environments/${ENVIRONMENT}.env

echo "Deploying to ${PROJECT_ID} in ${REGION}"
```

### With Terraform
```bash
# Variables are automatically exported as TF_VAR_*
export TF_VAR_project_id="${PROJECT_ID}"
export TF_VAR_region="${REGION}"
export TF_VAR_environment="${ENVIRONMENT}"
```

### With direnv
The `.envrc` file automatically loads configurations:
```bash
cd /path/to/genesis
# Configurations loaded automatically
echo $PROJECT_ID
```

## 🔄 Configuration Precedence

1. Command-line arguments (highest priority)
2. Environment variables
3. Environment-specific config files
4. Project-wide config file
5. Built-in defaults (lowest priority)

## ✅ Validation

Configurations are validated automatically:
```bash
# Manual validation
source config/project.env
validate_config

# Check specific environment
ENVIRONMENT=prod source config/environments/prod.env
```

## 📚 Best Practices

1. **Never commit secrets** - Use environment variables or Secret Manager
2. **Use consistent naming** - Follow established patterns
3. **Document changes** - Update this README when adding new variables
4. **Test configurations** - Validate before deployment
5. **Keep DRY** - Define once in project.env, override only when needed
6. **Version control** - Track all configuration changes

## 🔗 Related Documentation

- [Environment Setup Guide](../docs/01-getting-started/quickstart.md)
- [GCP Isolation Guide](../docs/04-guides/gcp-isolation.md)
- [Deployment Guide](../docs/04-guides/deployment/)

## 🆘 Troubleshooting

### Variable Not Found
```bash
# Check if variable is defined
grep -r "VARIABLE_NAME" config/

# Verify sourcing order
source config/project.env
source config/environments/${ENVIRONMENT}.env
```

### Wrong Project ID
```bash
# Verify environment
echo $ENVIRONMENT

# Check PROJECT_ID mapping
get_project_id "$ENVIRONMENT"
```

### Configuration Not Loading
```bash
# With direnv
direnv allow

# Manual sourcing
source .envrc
```