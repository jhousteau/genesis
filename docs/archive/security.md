# GCP Bootstrap Deployer - Security Guide

## Security Overview

This document outlines the security controls, best practices, and procedures implemented in the GCP Bootstrap Deployer. The framework follows a defense-in-depth approach with multiple layers of security controls to protect infrastructure, data, and operations.

## Security Principles

### Zero Trust Architecture
- Never trust, always verify
- Assume breach mentality
- Least privilege access
- Continuous validation

### Security by Design
- Security integrated from the start
- Automated security controls
- Immutable infrastructure
- Encrypted by default

## Authentication & Authorization

### Workload Identity Federation (WIF)

#### Configuration
```bash
# Create workload identity pool
gcloud iam workload-identity-pools create github-pool \
    --location="global" \
    --display-name="GitHub Actions Pool"

# Create OIDC provider
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --workload-identity-pool="github-pool" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub"
```

#### Security Benefits
- No long-lived credentials
- Token lifetime: 1 hour (configurable)
- Attribute-based access control
- Audit trail for all access

### Service Account Management

#### Best Practices
1. **Unique Service Accounts**: One SA per service/application
2. **Minimal Permissions**: Grant only required roles
3. **No Default SA**: Avoid using default compute service account
4. **Regular Audits**: Review permissions quarterly

#### Example Service Account Setup
```hcl
resource "google_service_account" "app_sa" {
  account_id   = "app-service-account"
  display_name = "Application Service Account"
  description  = "Service account for application workloads"
}

resource "google_project_iam_member" "app_sa_roles" {
  for_each = toset([
    "roles/storage.objectViewer",
    "roles/secretmanager.secretAccessor"
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}
```

### IAM Best Practices

#### Role Assignment Matrix

| Role | Use Case | Risk Level | Approval Required |
|------|----------|------------|-------------------|
| Owner | Break-glass only | Critical | CTO/CISO |
| Editor | Infrastructure team | High | Manager |
| Viewer | Developers | Low | Team Lead |
| Custom | Specific permissions | Variable | Security Team |

#### Conditional IAM Policies

```hcl
resource "google_project_iam_binding" "conditional_admin" {
  project = var.project_id
  role    = "roles/compute.admin"

  members = ["user:admin@example.com"]

  condition {
    title       = "Business hours only"
    description = "Admin access during business hours"
    expression  = "request.time.getHours('America/New_York') >= 9 && request.time.getHours('America/New_York') <= 17"
  }
}
```

## Network Security

### VPC Security Controls

#### Firewall Rules

```hcl
# Deny all ingress by default
resource "google_compute_firewall" "deny_all_ingress" {
  name    = "deny-all-ingress"
  network = google_compute_network.vpc.name
  
  priority = 65534
  
  deny {
    protocol = "all"
  }
  
  source_ranges = ["0.0.0.0/0"]
}

# Allow specific traffic
resource "google_compute_firewall" "allow_https" {
  name    = "allow-https"
  network = google_compute_network.vpc.name
  
  priority = 1000
  
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
  
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["https-server"]
}
```

#### Private Google Access

Enable private access to Google APIs:
```hcl
resource "google_compute_subnetwork" "private" {
  name                     = "private-subnet"
  network                  = google_compute_network.vpc.id
  ip_cidr_range           = "10.0.0.0/24"
  private_ip_google_access = true
}
```

### VPC Service Controls

#### Perimeter Configuration

```hcl
resource "google_access_context_manager_service_perimeter" "secure_perimeter" {
  parent = "accessPolicies/${var.access_policy}"
  name   = "accessPolicies/${var.access_policy}/servicePerimeters/secure_perimeter"
  title  = "Secure Perimeter"

  status {
    restricted_services = [
      "storage.googleapis.com",
      "bigquery.googleapis.com",
      "secretmanager.googleapis.com"
    ]

    resources = [
      "projects/${var.project_number}"
    ]

    ingress_policies {
      ingress_from {
        identity_type = "ANY_IDENTITY"
        sources {
          resource = "projects/${var.trusted_project}"
        }
      }
    }
  }
}
```

## Data Security

### Encryption

#### Encryption at Rest

All data encrypted by default using Google-managed encryption keys (GMEK):
- Cloud Storage: AES-256
- Cloud SQL: AES-256
- Secret Manager: AES-256

#### Customer-Managed Encryption Keys (CMEK)

```hcl
resource "google_kms_key_ring" "keyring" {
  name     = "bootstrap-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "key" {
  name            = "bootstrap-key"
  key_ring        = google_kms_key_ring.keyring.id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

# Use CMEK for storage bucket
resource "google_storage_bucket" "secure_bucket" {
  name     = "secure-bucket-${var.project_id}"
  location = var.region

  encryption {
    default_kms_key_name = google_kms_crypto_key.key.id
  }
}
```

### Secret Management

#### Secret Manager Configuration

```hcl
resource "google_secret_manager_secret" "api_key" {
  secret_id = "api-key"

  replication {
    automatic = true
  }

  topics {
    name = google_pubsub_topic.secret_rotation.id
  }
}

resource "google_secret_manager_secret_version" "api_key_version" {
  secret = google_secret_manager_secret.api_key.id
  secret_data = var.api_key

  lifecycle {
    ignore_changes = [secret_data]
  }
}
```

#### Secret Rotation Policy

```yaml
Rotation Schedule:
  - API Keys: 30 days
  - Database Passwords: 60 days
  - Service Account Keys: Never (use WIF)
  - Encryption Keys: 90 days
```

### Data Loss Prevention (DLP)

#### DLP Inspection Template

```hcl
resource "google_data_loss_prevention_inspect_template" "sensitive_data" {
  parent       = "projects/${var.project_id}"
  display_name = "Sensitive Data Template"

  inspect_config {
    info_types {
      name = "CREDIT_CARD_NUMBER"
    }
    info_types {
      name = "US_SOCIAL_SECURITY_NUMBER"
    }
    info_types {
      name = "EMAIL_ADDRESS"
    }
    
    min_likelihood = "LIKELY"
  }
}
```

## Security Scanning

### Infrastructure Scanning

#### TFSec Configuration

`.tfsec/config.yml`:
```yaml
severity_overrides:
  - rule_id: google-compute-no-public-ingress
    severity: CRITICAL
  - rule_id: google-storage-no-public-access
    severity: HIGH

custom_checks:
  - name: Ensure all buckets have versioning
    resource_type: google_storage_bucket
    path: versioning[0].enabled
    required: true
```

#### Checkov Policy

`.checkov.yml`:
```yaml
framework: terraform
quiet: true
skip-check:
  - CKV_GCP_62  # Skip logging check for dev
external-checks-dir:
  - ./custom-checks
output: sarif
```

### Secret Scanning

#### Pre-commit Hooks

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        
  - repo: https://github.com/zricethezav/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

### Vulnerability Management

#### Container Scanning

```hcl
resource "google_container_analysis_note" "vulnerability_note" {
  name = "projects/${var.project_id}/notes/prod-vulnerability"

  attestation_authority {
    hint {
      human_readable_name = "Production Vulnerability Attestation"
    }
  }
}

resource "google_binary_authorization_policy" "policy" {
  admission_whitelist_patterns {
    name_pattern = "gcr.io/${var.project_id}/*"
  }

  default_admission_rule {
    evaluation_mode  = "REQUIRE_ATTESTATION"
    enforcement_mode = "ENFORCED"
    
    require_attestations_by = [
      google_container_analysis_note.vulnerability_note.name
    ]
  }
}
```

## Compliance & Auditing

### Audit Logging

#### Log Configuration

```hcl
resource "google_project_iam_audit_config" "project" {
  project = var.project_id
  service = "allServices"

  audit_log_config {
    log_type = "ADMIN_READ"
  }
  
  audit_log_config {
    log_type = "DATA_READ"
    exempted_members = []
  }
  
  audit_log_config {
    log_type = "DATA_WRITE"
    exempted_members = []
  }
}
```

#### Log Retention

```yaml
Log Types:
  Admin Activity: 400 days
  Data Access: 30 days
  System Events: 30 days
  VPC Flow Logs: 7 days
```

### Compliance Monitoring

#### Security Command Center

```hcl
resource "google_scc_source" "custom_findings" {
  display_name = "Custom Security Findings"
  organization = var.org_id
  description  = "Custom security findings from automated scans"
}

resource "google_scc_notification_config" "scc_notification" {
  config_id    = "security-notification"
  organization = var.org_id
  description  = "Security findings notification"
  
  pubsub_topic = google_pubsub_topic.security_alerts.id

  streaming_config {
    filter = "category=\"VULNERABILITY\" AND state=\"ACTIVE\""
  }
}
```

### Access Reviews

#### Quarterly Review Process

1. **Export IAM Policies**
```bash
gcloud projects get-iam-policy PROJECT_ID --format=json > iam-audit.json
```

2. **Review Service Accounts**
```bash
gcloud iam service-accounts list --format="table(email,disabled)"
```

3. **Check API Keys**
```bash
gcloud services api-keys list --format="table(name,createTime,restrictions)"
```

4. **Audit Firewall Rules**
```bash
gcloud compute firewall-rules list --format="table(name,sourceRanges,allowed)"
```

## Incident Response

### Incident Response Plan

#### Severity Levels

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| P1 | Data breach | 15 minutes | CISO, Legal |
| P2 | Service compromise | 30 minutes | Security Team |
| P3 | Policy violation | 2 hours | Team Lead |
| P4 | Minor issue | 24 hours | On-call |

#### Response Procedures

1. **Detection & Analysis**
   - Alert triggered
   - Initial assessment
   - Severity classification
   - Team notification

2. **Containment**
   - Isolate affected resources
   - Preserve evidence
   - Temporary fixes

3. **Eradication**
   - Remove threat
   - Patch vulnerabilities
   - Update configurations

4. **Recovery**
   - Restore services
   - Verify functionality
   - Monitor for recurrence

5. **Post-Incident**
   - Root cause analysis
   - Documentation
   - Process improvements
   - Training updates

### Break-Glass Procedures

#### Emergency Access

```bash
# Create emergency admin binding
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="user:emergency@example.com" \
    --role="roles/owner" \
    --condition="expression=request.time < timestamp('2024-01-01T00:00:00Z'),title=Emergency Access"
```

#### Audit Requirements
- All break-glass access logged
- Notification to security team
- Access review within 24 hours
- Automatic revocation after time limit

## Security Checklist

### Pre-Deployment

- [ ] Security scanning passed
- [ ] No secrets in code
- [ ] IAM roles reviewed
- [ ] Network rules validated
- [ ] Encryption enabled
- [ ] Logging configured

### Post-Deployment

- [ ] Security monitoring active
- [ ] Alerts configured
- [ ] Backup verified
- [ ] Documentation updated
- [ ] Team trained
- [ ] Compliance validated

## Security Tools

### Recommended Tools

| Tool | Purpose | Integration |
|------|---------|-------------|
| TFSec | Terraform security scanning | CI/CD |
| Checkov | Policy as code | CI/CD |
| GitLeaks | Secret detection | Pre-commit |
| OWASP ZAP | Web app security | Testing |
| Cloud Security Scanner | Vulnerability scanning | GCP |
| Forseti | Security governance | GCP |

### Security Automation

```yaml
Automated Security Tasks:
  - Daily vulnerability scans
  - Weekly compliance reports
  - Monthly access reviews
  - Quarterly security assessments
  - Annual penetration testing
```

## Security Training

### Required Training

1. **All Team Members**
   - Security awareness
   - Phishing prevention
   - Password management
   - Incident reporting

2. **Developers**
   - Secure coding practices
   - OWASP Top 10
   - Secret management
   - Security testing

3. **Operations**
   - Infrastructure security
   - Incident response
   - Compliance requirements
   - Security tools

## Security Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| Security Team | security@example.com | Primary |
| CISO | ciso@example.com | P1 incidents |
| On-call | oncall@example.com | 24/7 |
| Legal | legal@example.com | Breaches |

## Conclusion

Security is a continuous process, not a destination. This guide provides the foundation for secure GCP infrastructure management. Regular reviews, updates, and training ensure the security posture remains strong against evolving threats.