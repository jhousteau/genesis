# Genesis Projects Registry

Centralized registry and management for all projects using the Genesis Universal Infrastructure Platform.

## Overview

The projects registry provides centralized tracking and management of:
- Project metadata and configuration
- Environment mappings and isolation
- Resource allocation and usage
- Compliance and governance status
- Integration with other Genesis components

## Structure

```
projects/
├── registry.yaml           # Main project registry
├── registry-enhanced.yaml  # Extended project metadata
└── registry.yaml.backup   # Registry backup (if exists)
```

## Project Registry

The registry tracks all projects using Genesis infrastructure:

### Registry Format
```yaml
# registry.yaml
projects:
  project-name:
    name: "Human Readable Name"
    type: "web-application|microservice|data-pipeline|ml-pipeline"
    environments:
      - dev
      - staging
      - prod
    gcp_projects:
      dev: "project-dev-123"
      staging: "project-staging-456"
      prod: "project-prod-789"
    status: "active|maintenance|deprecated"
    team: "team-name"
    repositories:
      - "https://github.com/org/project-name"
    compliance_requirements:
      - "soc2"
      - "gdpr"
    resources:
      compute: ["cloud-run", "gke"]
      storage: ["cloud-sql", "firestore"]
      networking: ["load-balancer", "vpc"]
```

### Enhanced Registry
The enhanced registry provides additional metadata:
- Resource usage tracking
- Cost allocation
- Performance metrics
- Security compliance status
- Integration dependencies

## Project Management

### Registration
Register a new project:
```bash
# Add project to registry
# Edit projects/registry.yaml to add new project entry

# Validate registry
python scripts/validate-registry.py

# Apply project configuration
g infra plan --project project-name --environment dev
g infra apply --project project-name --environment dev
```

### Environment Management
Each project supports multiple isolated environments:
- **Development** - Feature development and testing
- **Staging** - Pre-production validation
- **Production** - Live production environment

### Resource Allocation
Track resource usage per project:
- Compute resources (VMs, containers, serverless)
- Storage resources (databases, object storage, file systems)
- Network resources (load balancers, VPCs, CDN)
- Security resources (secrets, certificates, IAM)

## Integration

### CLI Integration
The registry integrates with Genesis CLI:
```bash
# List all projects
g projects list

# Show project details
g projects show project-name

# Validate project configuration
g projects validate project-name

# Update project status
g projects update project-name --status maintenance
```

### Infrastructure Integration
Projects are automatically integrated with:
- **Terraform Modules** - Infrastructure provisioning based on project type
- **Environment Isolation** - Separate GCP projects per environment
- **Security Policies** - Compliance requirements enforcement
- **Monitoring** - Automatic monitoring setup based on project type

### Compliance Integration
Registry enforces compliance requirements:
- **SOC2** - Security and availability controls
- **GDPR** - Data privacy and protection
- **HIPAA** - Healthcare data protection (if applicable)
- **PCI-DSS** - Payment card data security (if applicable)

## Project Types

### Web Application
Standard web application with frontend and backend:
- Cloud Run for application hosting
- Cloud SQL for data persistence
- Cloud CDN for static assets
- Identity and Access Management

### Microservice
Individual microservice in a larger system:
- GKE for container orchestration
- Service mesh for inter-service communication
- Cloud SQL or Firestore for data
- API Gateway for external access

### Data Pipeline
Data processing and analytics pipeline:
- Dataflow for stream/batch processing
- BigQuery for data warehousing
- Cloud Storage for data lake
- Pub/Sub for messaging

### ML Pipeline
Machine learning training and inference pipeline:
- Vertex AI for ML operations
- Cloud Storage for model artifacts
- Cloud Functions for inference endpoints
- BigQuery ML for in-database ML

## Monitoring and Reporting

### Project Health
Track project health across all registered projects:
- Infrastructure status
- Application performance
- Security compliance
- Cost efficiency

### Usage Analytics
Generate reports on:
- Resource utilization across projects
- Cost allocation and trending
- Performance metrics
- Compliance status

### Lifecycle Management
Track project lifecycle:
- **Active** - Under active development
- **Maintenance** - Stable, minimal changes
- **Deprecated** - Planned for removal
- **Archived** - No longer in use

## Configuration

### Registry Validation
Ensure registry consistency:
```python
# scripts/validate-registry.py validates:
# - Project name uniqueness
# - GCP project ID format
# - Environment consistency
# - Compliance requirement validity
# - Repository URL accessibility
```

### Automatic Updates
Registry is automatically updated by:
- CI/CD pipelines when projects are deployed
- Infrastructure provisioning when resources change
- Monitoring when status changes
- Compliance scans when requirements change

## Migration

### Adding Existing Projects
To register an existing project:
1. Add entry to `registry.yaml`
2. Run validation: `python scripts/validate-registry.py`
3. Configure environment isolation
4. Apply infrastructure: `g infra apply --project project-name`
5. Enable monitoring and compliance

### Project Retirement
To retire a project:
1. Update status to "deprecated"
2. Plan resource cleanup
3. Export/backup necessary data
4. Remove infrastructure: `g infra destroy --project project-name`
5. Archive project entry

## See Also

- [Getting Started](../docs/01-getting-started/quickstart.md) - New project setup
- [Infrastructure Modules](../modules/README.md) - Project infrastructure components
- [Governance](../governance/README.md) - Compliance and policy management
- [Isolation](../isolation/README.md) - Environment isolation setup
- [CLI Commands](../cli/README.md) - Project management commands

---

**Genesis Projects Registry** - Centralized project lifecycle management.
