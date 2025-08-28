# Terraform Examples

Practical examples of using Genesis Terraform modules.

## Examples

### basic-project/
Simple project setup - perfect for getting started.

**Creates:**
- GCP project with common APIs
- Terraform state bucket
- Budget alert ($100/month)

**Time:** ~2 minutes

### advanced-project/
Production-ready setup with service accounts and GitHub Actions.

**Creates:**
- Everything from basic-project
- Additional service accounts for app/CI-CD
- Workload Identity for GitHub Actions
- More APIs (monitoring, logging, Cloud Run)

**Time:** ~3 minutes

## How to Use

1. Copy example directory: `cp -r basic-project my-project`
2. Edit variables: `cp terraform.tfvars.example terraform.tfvars`
3. Initialize: `terraform init`
4. Plan: `terraform plan`
5. Apply: `terraform apply`

## Why These Examples?

Based on analyzing the old bloated code, we found most projects need:

- **90%** need: project + state bucket
- **60%** need: service accounts
- **40%** need: GitHub Actions integration
- **10%** need: complex multi-region setups

These examples cover the 90% and 60% use cases. The 10% can add complexity later if actually needed.
