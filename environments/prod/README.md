# Production Environment

This configuration deploys a production-grade environment in GCP with high availability, security, and disaster recovery capabilities.

## Architecture Overview

The production environment implements:

- **High Availability**: Multi-region deployment with automatic failover
- **Security**: KMS encryption, private networking, least privilege IAM
- **Scalability**: Auto-scaling services with global load balancing
- **Reliability**: Automated backups, monitoring, and alerting
- **Compliance**: Audit logging, data residency, encryption at rest

## Key Features

### Multi-Region Architecture

- **Primary Region**: Main production workloads
- **DR Region**: Disaster recovery standby resources
- **Global Routing**: Traffic management across regions
- **Data Replication**: Cross-region backup and synchronization

### Security Hardening

- **KMS Encryption**: All data encrypted at rest
- **Private Networking**: No public IPs, Cloud NAT for egress
- **Secret Management**: Centralized secrets with rotation
- **Audit Logging**: Complete audit trail for compliance

### Production Services

- **Compute**: Managed instance groups with auto-healing
- **Kubernetes**: GKE with node auto-scaling and upgrades
- **Serverless**: Cloud Run and Functions for event processing
- **Databases**: Cloud SQL with HA, Firestore multi-region
- **Storage**: Multi-tier storage with lifecycle management

## Prerequisites

1. Bootstrap environment completed
2. Production project quota approved
3. SSL certificates provisioned
4. Domain DNS configured
5. Monitoring channels set up

## Deployment Guide

### 1. Pre-Deployment Checklist

- [ ] Review and approve production quotas
- [ ] Verify billing alerts configured
- [ ] Confirm DR requirements
- [ ] Document recovery procedures
- [ ] Set up monitoring dashboards

### 2. Configure Backend

```bash
cp backend.tf.example backend.tf
# Update with your state bucket from bootstrap
```

### 3. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Update with production values
```

### 4. Initialize and Plan

```bash
terraform init
terraform plan -out=prod.tfplan
```

### 5. Deploy Production

```bash
# Deploy with approval
terraform apply prod.tfplan

# Verify deployment
terraform output
```

## Network Architecture

### Primary Region Network

```
VPC: main-prod (10.10.0.0/16)
├── main-subnet (10.10.0.0/24)
│   ├── Compute instances
│   └── Internal load balancers
├── serverless-subnet (10.10.1.0/24)
│   ├── Cloud Run services
│   └── VPC connectors
├── gke-pods (10.11.0.0/16)
│   └── Kubernetes pods
└── gke-services (10.12.0.0/16)
    └── Kubernetes services
```

### DR Region Network

```
VPC: main-prod (10.20.0.0/16)
├── main-subnet (10.20.0.0/24)
├── serverless-subnet (10.20.1.0/24)
├── gke-pods (10.21.0.0/16)
└── gke-services (10.22.0.0/16)
```

## Security Configuration

### Encryption

All data encrypted using Cloud KMS:
- **Storage**: Customer-managed encryption keys (CMEK)
- **Databases**: Encrypted at rest and in transit
- **Secrets**: Secret Manager with automatic rotation

### Network Security

- **Firewall Rules**: Restrictive ingress, managed egress
- **Cloud Armor**: DDoS protection and WAF rules
- **Private Google Access**: Internal routing to Google APIs
- **VPC Service Controls**: Data exfiltration prevention

### IAM Best Practices

```bash
# Service account per workload
compute-prod@         # Compute Engine instances
gke-prod@            # GKE node pools
cloud-run-prod@      # Cloud Run services
cloud-functions-prod@ # Cloud Functions

# Minimal permissions per account
roles/logging.logWriter
roles/monitoring.metricWriter
roles/cloudtrace.agent
# Additional specific roles as needed
```

## Database Configuration

### Cloud SQL (PostgreSQL)

- **High Availability**: Regional configuration with standby
- **Backups**: Daily automated backups with PITR
- **Maintenance**: Scheduled windows with minimal impact
- **Monitoring**: Query insights and performance metrics

### Firestore

- **Mode**: Native mode for real-time sync
- **Location**: Multi-region (nam5) for US
- **Backups**: Daily exports to Cloud Storage
- **Security**: Fine-grained access rules

## Storage Strategy

### Data Lifecycle

```
Active Data (0-30 days)    → STANDARD
Warm Data (30-90 days)     → NEARLINE
Cold Data (90-365 days)    → COLDLINE
Archive (365+ days)        → ARCHIVE
```

### Backup Policy

- **Frequency**: Daily incremental, weekly full
- **Retention**: 90 days standard, 7 years for compliance
- **Testing**: Monthly restore verification
- **Location**: Cross-region replication

## Monitoring and Alerting

### Key Metrics

```yaml
# SLI/SLO Configuration
availability:
  target: 99.95%
  measurement: uptime checks

latency:
  p50: < 100ms
  p99: < 1000ms

error_rate:
  target: < 0.1%
  window: 5 minutes
```

### Alert Policies

1. **Critical**: Immediate page
   - Service down
   - Data loss risk
   - Security breach

2. **Warning**: Email notification
   - Performance degradation
   - Capacity threshold
   - Budget alerts

3. **Info**: Dashboard only
   - Scheduled maintenance
   - Non-critical errors

## Disaster Recovery

### RTO/RPO Targets

- **RTO** (Recovery Time Objective): 1 hour
- **RPO** (Recovery Point Objective): 15 minutes

### DR Procedures

1. **Detection**: Automated monitoring alerts
2. **Assessment**: Determine impact and scope
3. **Activation**: Failover to DR region
4. **Validation**: Verify service restoration
5. **Communication**: Update stakeholders

### Failover Process

```bash
# Manual failover to DR region
./scripts/failover-to-dr.sh

# Automated failover (if configured)
# Triggered by health check failures
```

## Deployment Patterns

### Blue-Green Deployment

```bash
# Deploy to green environment
gcloud run deploy app-green --image=IMAGE

# Switch traffic
gcloud run services update-traffic app \
  --to-revisions=app-green=100

# Rollback if needed
gcloud run services update-traffic app \
  --to-revisions=app-blue=100
```

### Canary Deployment

```bash
# Deploy canary (10% traffic)
gcloud run deploy app-canary --image=NEW_IMAGE
gcloud run services update-traffic app \
  --to-revisions=app-canary=10,app-stable=90

# Gradual rollout
for percent in 25 50 75 100; do
  gcloud run services update-traffic app \
    --to-revisions=app-canary=$percent
  sleep 300  # Monitor for 5 minutes
done
```

## Cost Management

### Optimization Strategies

1. **Committed Use Discounts**: 1-3 year commitments
2. **Sustained Use Discounts**: Automatic for consistent usage
3. **Preemptible Instances**: For batch processing
4. **Resource Scheduling**: Auto-shutdown non-critical resources
5. **Storage Tiering**: Automatic lifecycle transitions

### Budget Controls

```bash
# Monthly budget: $1000
# Alerts at: 50%, 80%, 90%, 100%

# View current spend
gcloud billing accounts list
gcloud alpha billing budgets list

# Cost breakdown by service
bq query --use_legacy_sql=false '
  SELECT service.description,
         SUM(cost) as total_cost
  FROM `billing_dataset.gcp_billing_export_v1`
  WHERE DATE(_PARTITIONTIME) = CURRENT_DATE()
  GROUP BY service.description
  ORDER BY total_cost DESC'
```

## Maintenance Windows

### Scheduled Maintenance

- **Database**: Sunday 2:00-4:00 AM UTC
- **GKE**: Rolling updates, no downtime
- **Infrastructure**: Quarterly, announced 2 weeks prior

### Update Procedures

```bash
# GKE node pool upgrade
gcloud container clusters upgrade CLUSTER \
  --node-pool=POOL --cluster-version=VERSION

# Cloud SQL maintenance
gcloud sql instances patch INSTANCE \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=2
```

## Compliance and Auditing

### Audit Logging

All admin and data access logged:
- Who: User/service account identity
- What: Resource and action
- When: Timestamp with timezone
- Where: Source IP and location

### Compliance Controls

- **Data Residency**: Configurable per region
- **Encryption**: FIPS 140-2 Level 1
- **Access Controls**: MFA, conditional access
- **Audit Trail**: Immutable logs in Cloud Logging

## Performance Tuning

### Application Optimization

```yaml
# Cloud Run configuration
resources:
  limits:
    cpu: "2"
    memory: "2Gi"

scaling:
  minInstances: 2
  maxInstances: 100

concurrency:
  containerConcurrency: 80
```

### Database Optimization

```sql
-- Enable query insights
ALTER DATABASE mydb SET cloudsql.enable_pgaudit = 'on';

-- Create indexes for common queries
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_created_at ON orders(created_at DESC);

-- Analyze query performance
SELECT * FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

## Troubleshooting

### Common Issues

1. **High Latency**
   - Check network routes
   - Review Cloud CDN hit ratio
   - Analyze database queries

2. **Service Unavailable**
   - Verify health checks
   - Check quotas and limits
   - Review error logs

3. **Cost Overruns**
   - Identify unused resources
   - Review auto-scaling settings
   - Check for data egress

### Debug Commands

```bash
# Check service status
gcloud run services describe SERVICE

# View recent errors
gcloud logging read "severity>=ERROR" --limit=50

# Network connectivity test
gcloud compute network-connectivity-tests create TEST \
  --source-instance=INSTANCE \
  --destination-ip=IP

# Database connections
gcloud sql operations list --instance=INSTANCE
```

## Support and Escalation

### Support Tiers

1. **L1**: Application team (business hours)
2. **L2**: Platform team (24/7 on-call)
3. **L3**: Google Cloud Support (Premium)

### Escalation Matrix

| Severity | Response Time | Escalation |
|----------|--------------|------------|
| Critical | 15 minutes | Immediate |
| High | 1 hour | After 2 hours |
| Medium | 4 hours | Next business day |
| Low | 1 business day | As needed |

## Next Steps

1. Configure SSL certificates and domains
2. Set up CI/CD pipelines
3. Implement monitoring dashboards
4. Document runbooks
5. Conduct DR drills
6. Schedule security review
