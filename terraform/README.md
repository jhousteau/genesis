# Genesis Terraform Modules

Simple, focused Terraform modules for GCP project setup. **No over-engineering.**

## Philosophy

Based on the [OLD_CODE_ANALYSIS.md](../OLD_CODE_ANALYSIS.md), we learned that Terraform modules can become massively over-engineered. Genesis modules follow these principles:

- **Simple**: ~100 lines max per module
- **Focused**: One clear purpose per module  
- **Actually Used**: Only features that projects regularly need
- **Generic**: Works for any project type

## Available Modules

### Core Modules

| Module | Purpose | Lines | Use When |
|--------|---------|--------|----------|
| `bootstrap` | Create GCP project with APIs | ~80 | Setting up any new project |
| `state-backend` | Terraform state GCS bucket | ~60 | Need remote state storage |
| `service-accounts` | Create service accounts + IAM | ~50 | Need service accounts |
| `project-setup` | Complete project initialization | ~40 | Want everything in one go |

### What We DON'T Include

- ❌ 6 deployment strategies (old code had this)
- ❌ Multi-region disaster recovery 
- ❌ Complex CMEK encryption setups
- ❌ Advanced monitoring/alerting
- ❌ VPC Service Controls
- ❌ Organization policies
- ❌ Cost anomaly detection

**Why not?** Most projects never use these. Add them later if actually needed.

## Quick Start

### Basic Project Setup

```hcl
module "project" {
  source = "path/to/genesis/terraform/modules/project-setup"
  
  project_id      = "my-awesome-project"
  billing_account = "XXXXXX-YYYYYY-ZZZZZZ"
}
```

That's it! You get:
- GCP project with essential APIs
- Terraform state bucket 
- Service account for Terraform
- Basic budget alert

### Just State Backend

```hcl
module "state" {
  source = "path/to/genesis/terraform/modules/state-backend"
  
  project_id = "existing-project-id"
}
```

## Examples

- [`basic-project/`](examples/basic-project/) - Simple project setup
- [`advanced-project/`](examples/advanced-project/) - With service accounts & GitHub Actions

## Module Details

### bootstrap

Creates a GCP project with essential APIs enabled.

**What it does:**
- Creates project under org/folder
- Enables APIs: `cloudresourcemanager`, `iam`, `storage`
- Optional: Additional APIs, service account, budget

**What it doesn't do:**
- Complex organization policies
- Advanced audit logging  
- Multi-region setup

### state-backend

Creates GCS bucket for Terraform state.

**What it does:**
- Creates bucket with versioning
- Sets up lifecycle rules (keeps 5 versions)
- Optional: Service account, workload identity

**What it doesn't do:**
- Cross-region replication
- CMEK encryption (can add KMS key if needed)
- Advanced monitoring

### service-accounts

Creates service accounts with IAM roles.

**What it does:**
- Creates service accounts
- Assigns project roles
- Optional: Keys, impersonation

**What it doesn't do:**
- Organization-level roles
- Complex conditional IAM
- Multiple projects

### project-setup

Combines bootstrap + state-backend + service-accounts.

**What it does:**
- Everything above in one module
- Handles dependencies correctly

**What it doesn't do:**
- Advanced networking
- Custom organization setup

## Lessons from Old Code

The previous Genesis had **1000+ line Terraform modules** with features like:

- Multi-region state replication (45 resources)
- Advanced security scanning (17 security policies)  
- Cost anomaly detection (automated budgets)
- Disaster recovery automation (cross-region backups)
- CMEK keys for 8 different services
- VPC service controls & perimeters

**Reality check:** 99% of projects never used any of this.

## Genesis Terraform Principles

### 1. Start Simple
- Basic module: ~50-100 lines
- Add complexity only when needed
- Most projects need: project + APIs + state bucket

### 2. One Module, One Job
- `bootstrap`: Create project
- `state-backend`: Handle Terraform state
- `service-accounts`: Manage service accounts
- `project-setup`: Do all three

### 3. Actually Generic
- No hardcoded project names
- Works for any project type
- Environment-agnostic defaults

### 4. Easy to Understand
- Clear variable names
- Minimal locals
- Obvious outputs

## Migration from Old Modules

If you have existing projects using the old complex modules:

1. **Don't migrate existing projects** - if it works, leave it
2. **Use Genesis modules for new projects**
3. **Gradually adopt** - start with `state-backend` only

## Contributing

When adding new modules:

1. Keep it under 100 lines
2. Ask: "Do 80% of projects need this?"
3. If no, don't add it
4. Add example usage
5. Test with real project

## Success Metrics

- ✅ New project setup: < 5 minutes
- ✅ Module complexity: < 100 lines each
- ✅ Features used: > 80% utilization  
- ✅ AI-safe: Complete module in one session

---

*"5,000 lines of excellent code > 250,000 lines of mediocre code"* - OLD_CODE_ANALYSIS.md