# Development Environment

This configuration deploys a development environment in GCP with all necessary resources for application development and testing.

## Architecture

The development environment includes:

- **Networking**: Custom VPC with subnets for different workload types
- **Compute**: Service accounts for various GCP services
- **Storage**: Cloud Storage buckets for data and temporary files
- **Database**: Firestore for NoSQL data storage
- **Messaging**: Pub/Sub topics for event-driven architecture
- **Container Registry**: Artifact Registry for Docker images
- **Security**: Minimal IAM permissions following least privilege

## Prerequisites

1. Bootstrap environment deployed
2. Terraform state bucket created
3. Service account with necessary permissions
4. Terraform >= 1.5

## Setup Instructions

### 1. Configure Backend

Copy and update the backend configuration:

```bash
cp backend.tf.example backend.tf
# Edit backend.tf with your state bucket name from bootstrap
```

### 2. Configure Variables

Copy and customize the variables:

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 3. Initialize Terraform

```bash
terraform init
```

### 4. Plan and Apply

Review the changes:

```bash
terraform plan
```

Apply the configuration:

```bash
terraform apply
```

## Network Architecture

### VPC Design

- **Main Subnet** (`10.0.0.0/24`): General compute workloads
- **Serverless Subnet** (`10.0.1.0/24`): Cloud Run, Cloud Functions
- **GKE Pods** (`10.1.0.0/16`): Kubernetes pod IPs
- **GKE Services** (`10.2.0.0/16`): Kubernetes service IPs

### Connectivity

- **Cloud NAT**: Outbound internet access for private resources
- **Private Google Access**: Access to Google APIs without external IPs
- **Firewall Rules**: Internal communication and health checks

## Service Accounts

| Service Account | Purpose | Default Roles |
|----------------|---------|---------------|
| `compute-dev` | Compute Engine VMs | logging, monitoring |
| `gke-dev` | GKE node pools | logging, monitoring, artifact registry |
| `cloud-run-dev` | Cloud Run services | logging, monitoring, secrets |
| `cloud-functions-dev` | Cloud Functions | logging, monitoring, pub/sub |

## Storage Resources

### Cloud Storage Buckets

1. **Data Bucket**: Persistent data storage with versioning
   - 30-day lifecycle for old versions
   - Uniform bucket-level access

2. **Temp Bucket**: Temporary file storage
   - 7-day auto-deletion
   - Force destroy enabled

### Firestore Database

- Type: Native mode
- Location: Multi-region (nam5)
- Use cases: User data, application state, real-time sync

## Pub/Sub Topics

1. **events-dev**: Main event bus
   - 1-day message retention
   - For application events

2. **deadletter-dev**: Failed message handling
   - 7-day message retention
   - For debugging and recovery

## Container Registry

- **Artifact Registry**: Docker image storage
- Format: Docker
- Location: Same as project region
- Access: Via service account authentication

## Budget Alerts

Default monthly budget: $100 USD

Alert thresholds:
- 50% ($50)
- 80% ($80)
- 100% ($100)

## Deploying Applications

### Cloud Run

```bash
# Build and push image
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/containers-dev/my-app:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/containers-dev/my-app:latest

# Deploy to Cloud Run
gcloud run deploy my-app \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/containers-dev/my-app:latest \
  --service-account=cloud-run-dev@${PROJECT_ID}.iam.gserviceaccount.com \
  --vpc-connector=projects/${PROJECT_ID}/locations/${REGION}/connectors/serverless-connector
```

### Cloud Functions

```bash
gcloud functions deploy my-function \
  --runtime=nodejs18 \
  --trigger-topic=events-dev \
  --service-account=cloud-functions-dev@${PROJECT_ID}.iam.gserviceaccount.com \
  --vpc-connector=projects/${PROJECT_ID}/locations/${REGION}/connectors/serverless-connector
```

### GKE Cluster (Optional)

```bash
gcloud container clusters create dev-cluster \
  --network=main-dev \
  --subnetwork=main-dev-main-${REGION} \
  --cluster-secondary-range-name=pods \
  --services-secondary-range-name=services \
  --service-account=gke-dev@${PROJECT_ID}.iam.gserviceaccount.com
```

## Development Workflow

### Local Development

1. Authenticate with service account:
```bash
gcloud auth activate-service-account --key-file=key.json
gcloud config set project ${PROJECT_ID}
```

2. Set up application default credentials:
```bash
gcloud auth application-default login
```

### CI/CD Integration

For GitHub Actions with Workload Identity:

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v1
  with:
    workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
    service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

- name: Deploy to Development
  run: |
    terraform init
    terraform apply -auto-approve
```

## Testing

### Integration Testing

Use the development environment for:
- API testing
- Load testing (with limits)
- Feature branch deployments
- A/B testing

### Resource Limits

Consider implementing quotas:
- Compute Engine: Limited instance types
- Cloud Run: Concurrency limits
- Storage: Lifecycle policies

## Monitoring

### Metrics to Track

- API latency (p50, p95, p99)
- Error rates
- Resource utilization
- Cost trends

### Logging

All services configured with:
- Structured logging
- Log aggregation in Cloud Logging
- 30-day retention (default)

## Security Considerations

### Best Practices

1. **Least Privilege**: Service accounts have minimal required permissions
2. **Network Isolation**: Private IPs with Cloud NAT for egress
3. **Secrets Management**: Use Secret Manager for sensitive data
4. **Audit Logging**: Cloud Audit Logs enabled

### Security Checklist

- [ ] Review IAM permissions
- [ ] Enable VPC Flow Logs
- [ ] Configure Secret Manager
- [ ] Set up Cloud Armor (if needed)
- [ ] Enable Binary Authorization (for GKE)

## Cost Optimization

### Tips for Development

1. **Auto-shutdown**: Schedule compute resources
2. **Preemptible VMs**: Use for non-critical workloads
3. **Storage Lifecycle**: Auto-delete old data
4. **Right-sizing**: Monitor and adjust resource allocation

### Cost Monitoring

```bash
# View current month costs
gcloud billing accounts list
gcloud alpha billing accounts budgets list --billing-account=BILLING_ACCOUNT_ID
```

## Cleanup

To destroy the development environment:

```bash
terraform destroy
```

**Warning**: This will delete all resources including data. Ensure backups are taken if needed.

## Troubleshooting

### Common Issues

1. **API Not Enabled**: Wait for API propagation or manually enable
2. **Permission Denied**: Check service account roles
3. **Network Issues**: Verify firewall rules and routes
4. **Quota Exceeded**: Request quota increase or optimize usage

### Debug Commands

```bash
# Check project configuration
gcloud config list

# View service account permissions
gcloud projects get-iam-policy ${PROJECT_ID}

# Test network connectivity
gcloud compute ssh INSTANCE_NAME --command="curl -I https://www.google.com"

# View logs
gcloud logging read "resource.type=cloud_function"
```

## Next Steps

After setting up development:

1. Deploy application components
2. Set up monitoring dashboards
3. Configure CI/CD pipelines
4. Implement automated testing
5. Prepare for production deployment