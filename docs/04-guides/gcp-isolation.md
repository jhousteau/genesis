# GCP Environment Isolation Guide

## Overview

Genesis implements comprehensive GCP environment isolation to prevent cross-project contamination and ensure each environment (dev, test, staging, prod) operates in complete isolation. This system is based on the proven isolation patterns from agent-cage.

## Key Features

### 1. Per-Repository Isolation
- Each repository gets its own `CLOUDSDK_CONFIG` directory
- Prevents credential and configuration bleeding between projects
- Isolated gcloud configurations at `~/.gcloud/genesis-${ENVIRONMENT}`

### 2. Environment Segregation
- Separate configurations for dev, test, staging, and production
- Environment-specific PROJECT_IDs and settings
- Automatic environment detection and configuration loading

### 3. Production Safety
- Automatic warnings for production environments
- Destructive operation blocking (requires `CONFIRM_PROD=I_UNDERSTAND`)
- Audit logging of all gcloud operations
- Cross-project operation detection and prevention

### 4. Automatic Activation
- Uses `direnv` for automatic environment loading
- Triggers bootstrap on first entry to project
- Shows current context on directory entry

## Setup Instructions

### Prerequisites

1. **Install direnv** (if not already installed):
   ```bash
   # macOS
   brew install direnv
   
   # Add to your shell profile (.zshrc or .bash_profile)
   eval "$(direnv hook zsh)"  # or bash
   ```

2. **Install Google Cloud SDK**:
   ```bash
   # Download from https://cloud.google.com/sdk/docs/install
   ```

### Initial Setup

1. **Allow direnv in the project**:
   ```bash
   cd /path/to/genesis
   direnv allow
   ```

2. **The bootstrap will run automatically** on first entry, or manually run:
   ```bash
   ./scripts/bootstrap_gcloud.sh
   ```

3. **Verify isolation**:
   ```bash
   echo $CLOUDSDK_CONFIG
   # Should show: /Users/yourname/.gcloud/whai-genesis-dev
   
   gcloud config list
   # Should show isolated configuration
   ```

## Usage

### Switching Environments

```bash
# Switch to production
ENVIRONMENT=prod direnv allow

# Switch to staging
ENVIRONMENT=staging direnv allow

# Back to development (default)
ENVIRONMENT=dev direnv allow
```

### Environment Variables Set

When you enter the Genesis directory, these variables are automatically set:

- `ENVIRONMENT` - Current environment (dev/test/staging/prod)
- `PROJECT_ID` - GCP project ID for current environment
- `REGION` - Default GCP region
- `ZONE` - Default GCP zone
- `CLOUDSDK_CONFIG` - Isolated gcloud config directory
- `TF_VAR_*` - Terraform variables
- `DOCKER_REGISTRY` - Container registry URL
- Various feature flags and settings

### Using the GCloud Guard

The `gcloud_guard.sh` script provides additional protection:

```bash
# Create an alias to use the guard
alias gcloud='./scripts/gcloud_guard.sh'

# Now all gcloud commands go through the guard
gcloud compute instances list
```

Guard features:
- Validates isolation is active
- Checks for cross-project operations
- Blocks destructive production operations
- Logs all operations for audit

## Configuration Files

### Project Configuration
- **Location**: `config/project.env`
- **Purpose**: Central configuration for project settings
- **Contains**: Project name, service definitions, naming patterns

### Environment Configurations
- **Location**: `config/environments/*.env`
- **Files**:
  - `dev.env` - Development settings
  - `test.env` - Test environment settings
  - `staging.env` - Staging/pre-production settings
  - `prod.env` - Production settings (with extra safeguards)

### Customizing for Your GCP Projects

Edit `config/project.env` and update the PROJECT_ID variables:

```bash
# Your actual GCP project IDs
PROJECT_ID_DEV="your-project-dev"
PROJECT_ID_TEST="your-project-test"
PROJECT_ID_STAGING="your-project-staging"
PROJECT_ID_PROD="your-project-prod"
```

## Production Safeguards

### Blocking Destructive Operations

In production, destructive operations are blocked by default:

```bash
# This will be blocked in production
gcloud compute instances delete my-instance

# To override (use with extreme caution):
export CONFIRM_PROD=I_UNDERSTAND
gcloud compute instances delete my-instance
```

### Production Warnings

When entering production environment:
```
⚠️  WARNING: Production environment detected: prod (whai-genesis-prod)
Set CONFIRM_PROD=I_UNDERSTAND to enable production operations
```

### Audit Logging

All gcloud operations are logged to:
```
~/.gcloud/genesis-${ENVIRONMENT}/logs/audit.log
```

## Troubleshooting

### Issue: "CLOUDSDK_CONFIG not set"
**Solution**: Run `direnv allow` in the project directory

### Issue: "No active authentication"
**Solution**: 
```bash
gcloud auth login
# or for service account:
gcloud auth activate-service-account --key-file=key.json
```

### Issue: "Cannot access project"
**Solution**: Ensure you have permissions for the project:
```bash
gcloud projects get-iam-policy PROJECT_ID
```

### Issue: Cross-contamination detected
**Solution**: Re-run bootstrap to reset isolation:
```bash
./scripts/bootstrap_gcloud.sh
```

## Best Practices

1. **Always use direnv** - Don't manually set CLOUDSDK_CONFIG
2. **Check environment before operations** - Verify with `echo $ENVIRONMENT`
3. **Use service accounts in production** - Set DEPLOY_SA in .envrc
4. **Review audit logs regularly** - Check for unexpected operations
5. **Test in staging first** - Always validate changes in staging
6. **Keep configurations in sync** - Update all environment files together

## Security Considerations

1. **Never commit credentials** - Add `.secrets/` to .gitignore
2. **Use service account impersonation** - Better than key files
3. **Enable audit logging** - Required for compliance
4. **Rotate credentials regularly** - Especially for production
5. **Limit production access** - Use least privilege principle

## Integration with CI/CD

For CI/CD pipelines, set environment variables:

```yaml
# GitHub Actions example
env:
  ENVIRONMENT: ${{ github.ref == 'refs/heads/main' && 'prod' || 'dev' }}
  CLOUDSDK_CONFIG: /home/runner/.gcloud/genesis-${{ env.ENVIRONMENT }}
  PROJECT_ID: ${{ secrets[format('PROJECT_ID_{0}', env.ENVIRONMENT)] }}
```

## Advanced Features

### Custom Service Account Per Environment

Edit `.envrc` and uncomment:
```bash
export DEPLOY_SA="genesis-deploy-${ENVIRONMENT}@${PROJECT_ID}.iam.gserviceaccount.com"
export GCLOUD_IMPERSONATE_SA="${DEPLOY_SA}"
```

### Application Default Credentials

For applications that need ADC:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/.secrets/genesis-${ENVIRONMENT}-adc.json"
```

### Multi-Region Setup

Configure in environment files:
```bash
MULTI_REGIONS=("us-central1" "us-east1" "europe-west1")
BACKUP_REGION="us-east1"
```

## Monitoring and Alerts

The isolation system integrates with monitoring:

1. **Audit log analysis** - Parse logs for anomalies
2. **Cross-project detection** - Alert on contamination attempts
3. **Production operation tracking** - Monitor destructive operations
4. **Cost tracking per environment** - Isolated billing analysis

## Related Documentation

- [Git Branch Protection](./git-branch-protection.md)
- [Project Setup Guide](../01-getting-started/quickstart.md)
- [Security Best Practices](../06-reference/security.md)
- [Terraform Integration](./deployment/terraform.md)