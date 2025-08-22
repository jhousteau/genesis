# GCP Bootstrap Deployer - Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Environment Configuration](#environment-configuration)
4. [Deployment Process](#deployment-process)
5. [CI/CD Setup](#cicd-setup)
6. [Validation & Testing](#validation--testing)
7. [Production Deployment](#production-deployment)
8. [Rollback Procedures](#rollback-procedures)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

## Prerequisites

### Required Tools

| Tool | Version | Installation |
|------|---------|--------------|
| gcloud CLI | Latest | `curl https://sdk.cloud.google.com \| bash` |
| Terraform | >= 1.5 | `brew install terraform` or [Download](https://terraform.io) |
| jq | >= 1.6 | `brew install jq` or `apt-get install jq` |
| git | >= 2.0 | `brew install git` or `apt-get install git` |

### GCP Requirements

- [ ] GCP Account with billing enabled
- [ ] Organization or standalone project
- [ ] Project Creator role (or Owner for standalone)
- [ ] Billing Account User role

### Local Environment Setup

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Initialize gcloud
gcloud init

# Install Terraform
brew install terraform  # macOS
# OR
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Verify installations
gcloud version
terraform version
jq --version
```

## Initial Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/gcp-bootstrap-deployer.git
cd gcp-bootstrap-deployer
```

### Step 2: Run Bootstrap Script

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run bootstrap
./scripts/bootstrap.sh
```

The bootstrap script will guide you through:
1. Project selection/creation
2. API enablement
3. Terraform backend setup
4. Workload Identity Federation configuration
5. Initial environment setup

### Step 3: Verify Setup

```bash
# Run validation script
./scripts/validate-config.sh

# Check validation report
cat validation-report-*.md
```

## Environment Configuration

### Directory Structure

```
environments/
├── dev.tfvars          # Development environment
├── staging.tfvars      # Staging environment
├── prod.tfvars         # Production environment
└── common.tfvars       # Shared configuration
```

### Configuration Variables

#### Base Configuration (common.tfvars)

```hcl
# Project Configuration
organization_id = "123456789"
billing_account = "XXXXXX-XXXXXX-XXXXXX"

# Network Configuration
network_cidr_range = "10.0.0.0/8"
enable_private_google_access = true

# Security Configuration
enable_vpc_flow_logs = true
enable_cloud_armor = true
enable_binary_authorization = false

# Monitoring
enable_monitoring = true
notification_email = "team@example.com"
```

#### Environment-Specific (dev.tfvars)

```hcl
# Environment Settings
environment = "dev"
project_id  = "my-project-dev"
region      = "us-central1"
zones       = ["us-central1-a", "us-central1-b"]

# Resource Sizing
machine_type = "n2-standard-2"
node_count   = 2
disk_size_gb = 100

# Network
subnet_cidr = "10.0.0.0/16"

# Labels
labels = {
  environment = "dev"
  team        = "platform"
  cost_center = "engineering"
  managed_by  = "terraform"
}

# Features
enable_deletion_protection = false
enable_auto_backup = false
```

### Secrets Configuration

```bash
# Create secret in Secret Manager
echo -n "your-secret-value" | gcloud secrets create api-key \
    --data-file=- \
    --replication-policy="automatic"

# Reference in Terraform
data "google_secret_manager_secret_version" "api_key" {
  secret = "api-key"
}
```

## Deployment Process

### Local Deployment

#### 1. Initialize Terraform

```bash
# Initialize with backend configuration
terraform init \
  -backend-config="bucket=terraform-state-${PROJECT_ID}" \
  -backend-config="prefix=bootstrap"
```

#### 2. Select Workspace

```bash
# List available workspaces
terraform workspace list

# Create/select workspace
terraform workspace new dev
# OR
terraform workspace select dev
```

#### 3. Plan Changes

```bash
# Validate configuration
terraform validate

# Generate plan
terraform plan \
  -var-file="environments/common.tfvars" \
  -var-file="environments/dev.tfvars" \
  -out=tfplan

# Review plan
terraform show tfplan
```

#### 4. Apply Changes

```bash
# Apply with approval
terraform apply tfplan

# OR apply directly with auto-approve (use with caution)
terraform apply \
  -var-file="environments/common.tfvars" \
  -var-file="environments/dev.tfvars" \
  -auto-approve
```

#### 5. Verify Deployment

```bash
# Check outputs
terraform output

# Verify resources in GCP
gcloud compute instances list
gcloud container clusters list
gcloud sql instances list
```

### Deployment Order

For initial deployment, follow this sequence:

1. **Foundation**
   ```bash
   terraform apply -target=module.bootstrap
   ```

2. **Network**
   ```bash
   terraform apply -target=module.network
   ```

3. **Security**
   ```bash
   terraform apply -target=module.security
   ```

4. **Compute**
   ```bash
   terraform apply -target=module.compute
   ```

5. **Full Deployment**
   ```bash
   terraform apply
   ```

## CI/CD Setup

### GitHub Actions Setup

#### 1. Configure Secrets

Navigate to Settings > Secrets and add:

```yaml
GCP_PROJECT_ID: your-project-id
WIF_PROVIDER: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL/providers/PROVIDER
WIF_SERVICE_ACCOUNT: github-actions-sa@PROJECT_ID.iam.gserviceaccount.com
SLACK_WEBHOOK: https://hooks.slack.com/services/XXX
```

#### 2. Enable Workflows

```bash
# Copy workflow examples
cp -r examples/github-actions/.github/workflows .github/

# Commit and push
git add .github/workflows/
git commit -m "Add GitHub Actions workflows"
git push origin main
```

#### 3. Test Workflow

```bash
# Create a feature branch
git checkout -b feature/test-deployment

# Make a change
echo "# Test" >> README.md

# Push and create PR
git add README.md
git commit -m "Test deployment workflow"
git push origin feature/test-deployment
```

### GitLab CI Setup

#### 1. Configure Variables

In GitLab, go to Settings > CI/CD > Variables:

```yaml
GCP_PROJECT_ID: your-project-id
WIF_PROVIDER_GITLAB: projects/NUMBER/locations/global/workloadIdentityPools/POOL/providers/PROVIDER
WIF_SERVICE_ACCOUNT_GITLAB: gitlab-ci-sa@PROJECT_ID.iam.gserviceaccount.com
```

#### 2. Add Pipeline Configuration

```bash
# Copy GitLab CI configuration
cp examples/gitlab-ci/.gitlab-ci.yml .

# Commit and push
git add .gitlab-ci.yml
git commit -m "Add GitLab CI pipeline"
git push origin main
```

## Validation & Testing

### Pre-Deployment Validation

```bash
# Run all validation checks
./scripts/validate-config.sh

# Run specific checks
terraform fmt -check -recursive
terraform validate
tfsec .
checkov -d .
```

### Integration Testing

```bash
# Test network connectivity
gcloud compute ssh test-instance --command="curl -I https://www.google.com"

# Test service account permissions
gcloud auth activate-service-account --key-file=key.json
gcloud projects get-iam-policy PROJECT_ID

# Test API access
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  https://compute.googleapis.com/compute/v1/projects/PROJECT_ID/zones
```

### Load Testing

```bash
# Install testing tools
go install github.com/rakyll/hey@latest

# Run load test
hey -n 1000 -c 50 https://your-app.example.com
```

## Production Deployment

### Pre-Production Checklist

- [ ] All tests passing in staging
- [ ] Security scan completed
- [ ] Change approval obtained
- [ ] Rollback plan documented
- [ ] Monitoring alerts configured
- [ ] Team notified of deployment window

### Production Deployment Steps

#### 1. Create Release Tag

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

#### 2. Deploy via CI/CD

For GitHub Actions:
1. Go to Actions tab
2. Select "Terraform Apply" workflow
3. Click "Run workflow"
4. Select "prod" environment
5. Type "apply" to confirm
6. Monitor deployment

#### 3. Manual Production Deployment

```bash
# Switch to production workspace
terraform workspace select prod

# Plan with production variables
terraform plan \
  -var-file="environments/common.tfvars" \
  -var-file="environments/prod.tfvars" \
  -out=prod.tfplan

# Apply after review and approval
terraform apply prod.tfplan
```

#### 4. Post-Deployment Verification

```bash
# Smoke tests
curl -f https://prod.example.com/health || exit 1

# Check metrics
gcloud monitoring dashboards list
gcloud monitoring metrics-descriptors list

# Verify logs
gcloud logging read "resource.type=gce_instance" --limit=10
```

### Blue-Green Deployment

```bash
# Deploy to green environment
terraform workspace select prod-green
terraform apply -var-file="environments/prod.tfvars"

# Test green environment
./scripts/smoke-test.sh https://green.example.com

# Switch traffic to green
gcloud compute url-maps set-default-service \
  --default-service=prod-green-backend \
  load-balancer

# Verify and clean up blue
terraform workspace select prod-blue
terraform destroy -var-file="environments/prod.tfvars"
```

## Rollback Procedures

### Immediate Rollback

```bash
# Revert to previous state
terraform workspace select prod
cd .terraform
cp terraform.tfstate.backup terraform.tfstate
terraform apply -refresh=false

# OR using state management
terraform state pull > current.tfstate
terraform state push terraform.tfstate.backup
```

### Git-Based Rollback

```bash
# Find previous working commit
git log --oneline

# Revert to previous version
git revert HEAD
git push origin main

# OR reset to specific commit
git reset --hard COMMIT_HASH
git push --force origin main
```

### Database Rollback

```bash
# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --restore-instance=INSTANCE_NAME

# Verify restoration
gcloud sql operations list --instance=INSTANCE_NAME
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Terraform State Lock

```bash
# Error: Error acquiring the state lock

# Solution: Force unlock
terraform force-unlock LOCK_ID

# Find lock ID in error message or:
gsutil cat gs://terraform-state-PROJECT/PREFIX/default.tflock
```

#### 2. API Not Enabled

```bash
# Error: googleapi: Error 403: Service not enabled

# Solution: Enable the API
gcloud services enable SERVICE_NAME.googleapis.com

# List all required APIs
gcloud services list --available | grep -E "(compute|storage|iam)"
```

#### 3. Permission Denied

```bash
# Error: Error 403: Required permission missing

# Solution: Grant required role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:USER_EMAIL" \
  --role="roles/ROLE_NAME"
```

#### 4. Resource Quota Exceeded

```bash
# Check quotas
gcloud compute project-info describe --project=PROJECT_ID

# Request increase
gcloud compute project-info update \
  --project=PROJECT_ID \
  --add-quotas=CPUS=100
```

#### 5. Network Connectivity Issues

```bash
# Test connectivity
gcloud compute ssh INSTANCE_NAME --command="ping -c 4 8.8.8.8"

# Check firewall rules
gcloud compute firewall-rules list

# Verify routes
gcloud compute routes list
```

### Debug Mode

```bash
# Enable debug logging
export TF_LOG=DEBUG
export TF_LOG_PATH=terraform-debug.log

# Run terraform with debug
terraform plan -var-file="environments/dev.tfvars"

# Check debug log
tail -f terraform-debug.log
```

## Maintenance

### Regular Maintenance Tasks

#### Daily
- Monitor alerts and dashboards
- Check CI/CD pipeline status
- Review security notifications

#### Weekly
- Update dependencies
- Run security scans
- Review cost reports

#### Monthly
- Rotate secrets
- Update documentation
- Performance optimization
- Disaster recovery test

#### Quarterly
- Security audit
- Access review
- Capacity planning
- Architecture review

### Terraform Maintenance

```bash
# Update providers
terraform init -upgrade

# Check for deprecated resources
terraform plan -var-file="environments/dev.tfvars" 2>&1 | grep -i deprecated

# Clean up state
terraform state list
terraform state rm RESOURCE_NAME  # Remove orphaned resources
```

### Backup Procedures

```bash
# Backup Terraform state
gsutil cp -r gs://terraform-state-PROJECT/* ./backups/state/

# Backup configurations
tar -czf configs-$(date +%Y%m%d).tar.gz environments/ modules/

# Backup to Cloud Storage
gsutil cp configs-*.tar.gz gs://backup-bucket/configs/
```

### Monitoring Setup

```bash
# Create uptime check
gcloud monitoring uptime-checks create https \
  --display-name="Production Health Check" \
  --resource-type="URL" \
  --hostname="prod.example.com" \
  --path="/health"

# Create alert policy
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High CPU Usage" \
  --condition="rate(compute.googleapis.com/instance/cpu/utilization) > 0.8"
```

## Best Practices

### Version Control
- Tag all production releases
- Use semantic versioning
- Maintain changelog
- Document breaking changes

### Security
- Never commit secrets
- Use least privilege IAM
- Enable audit logging
- Regular security scanning

### Cost Optimization
- Use committed use discounts
- Enable auto-scaling
- Set up budget alerts
- Regular resource cleanup

### Documentation
- Keep README updated
- Document all changes
- Maintain runbooks
- Update architecture diagrams

## Support

### Getting Help

1. Check documentation in `/docs`
2. Review closed issues on GitHub
3. Contact team on Slack: #infrastructure
4. Email: infrastructure@example.com

### Reporting Issues

Include in bug reports:
- Environment (dev/staging/prod)
- Error messages
- Terraform version
- Steps to reproduce
- Expected vs actual behavior

## Conclusion

This deployment guide provides comprehensive instructions for deploying and managing GCP infrastructure using the Bootstrap Deployer. Follow the procedures carefully and always test in lower environments before production deployment.