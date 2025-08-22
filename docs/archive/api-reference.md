# Bootstrapper API Reference

## Overview

The Bootstrapper platform provides comprehensive APIs for project management, system coordination, and intelligent automation. All APIs follow RESTful principles and support JSON for data exchange.

## Base URLs

- **Production**: `https://api.bootstrapper.dev`
- **Staging**: `https://staging-api.bootstrapper.dev`
- **Development**: `http://localhost:8000`

## Authentication

### OAuth2 / OpenID Connect
```http
POST /auth/login
Content-Type: application/json

{
  "provider": "google|github|okta",
  "redirect_uri": "https://your-app.com/callback"
}
```

### API Key Authentication
```http
GET /api/v1/projects
Authorization: Bearer your-api-key
```

### Service Account Authentication
```http
GET /api/v1/system/health
Authorization: Bearer service-account-token
```

## Core APIs

### 1. Intelligence Layer APIs

#### Auto-Fix System

##### Analyze Project Issues
```http
POST /api/v1/intelligence/auto-fix/analyze
Content-Type: application/json

{
  "project_name": "my-project",
  "project_path": "/path/to/project",
  "analysis_options": {
    "check_dependencies": true,
    "check_security": true,
    "check_configuration": true,
    "check_infrastructure": true
  }
}
```

**Response:**
```json
{
  "project_name": "my-project",
  "total_issues": 5,
  "auto_fixable_count": 3,
  "issues_by_severity": {
    "critical": [
      {
        "id": "security_vulnerability",
        "title": "Security vulnerability detected",
        "description": "Outdated dependencies with known vulnerabilities",
        "auto_fixable": true,
        "fix_command": "npm audit fix"
      }
    ],
    "high": [
      {
        "id": "missing_dockerfile",
        "title": "Missing Dockerfile",
        "description": "No containerization configuration found",
        "auto_fixable": true,
        "fix_command": "touch Dockerfile"
      }
    ],
    "medium": [
      {
        "id": "unpinned_dependencies",
        "title": "Unpinned dependencies",
        "description": "Some dependencies lack version pinning",
        "auto_fixable": false,
        "manual_steps": ["Review requirements.txt", "Pin dependency versions"]
      }
    ]
  },
  "analysis_timestamp": "2024-08-20T10:30:00Z"
}
```

##### Execute Auto-Fix
```http
POST /api/v1/intelligence/auto-fix/execute
Content-Type: application/json

{
  "project_name": "my-project",
  "issue_ids": ["security_vulnerability", "missing_dockerfile"],
  "confirm_execution": true
}
```

**Response:**
```json
{
  "execution_id": "fix-exec-123",
  "status": "completed",
  "results": {
    "fixed": [
      {
        "issue_id": "security_vulnerability",
        "status": "success",
        "execution_time": 45.2
      }
    ],
    "failed": [],
    "skipped": []
  },
  "total_execution_time": 47.8
}
```

#### Optimization Engine

##### Run Optimization Analysis
```http
POST /api/v1/intelligence/optimization/analyze
Content-Type: application/json

{
  "project_name": "my-project",
  "optimization_types": ["cost", "performance", "resource"],
  "include_estimates": true
}
```

**Response:**
```json
{
  "project_name": "my-project",
  "analysis_timestamp": "2024-08-20T10:30:00Z",
  "total_recommendations": 8,
  "recommendations_by_category": {
    "cost": [
      {
        "id": "instance_rightsizing",
        "title": "Optimize instance sizes",
        "description": "Current instances are oversized for workload",
        "priority": "high",
        "savings_estimate": "$500-1000/month",
        "implementation_steps": [
          "Monitor current CPU and memory utilization",
          "Test with smaller instance types",
          "Implement auto-scaling"
        ]
      }
    ],
    "performance": [
      {
        "id": "enable_caching",
        "title": "Implement caching layer",
        "description": "Add Redis caching for API responses",
        "priority": "medium",
        "performance_impact": "50% faster response times",
        "implementation_steps": [
          "Set up Redis cluster",
          "Implement cache-aside pattern",
          "Monitor cache hit rates"
        ]
      }
    ]
  },
  "summary": {
    "potential_monthly_savings": "$750-1500",
    "performance_improvements": 3,
    "implementation_effort": "medium"
  }
}
```

#### Prediction System

##### Get Failure Predictions
```http
GET /api/v1/intelligence/predictions/{project_name}
```

**Response:**
```json
{
  "project_name": "my-project",
  "analysis_timestamp": "2024-08-20T10:30:00Z",
  "total_predictions": 4,
  "predictions_by_type": {
    "failure": [
      {
        "id": "deployment_failure_risk",
        "title": "High deployment failure risk",
        "description": "CI/CD pipeline lacks proper error handling",
        "confidence": 0.85,
        "timeframe": "Next 30 days",
        "likelihood": "high",
        "preventive_actions": [
          "Add timeout configurations",
          "Implement retry logic",
          "Set up proper error handling"
        ]
      }
    ],
    "capacity": [
      {
        "id": "storage_capacity_limit",
        "title": "Storage capacity will be exceeded",
        "description": "Current growth rate will exceed storage in 3 months",
        "confidence": 0.92,
        "timeframe": "Next 90 days",
        "likelihood": "high",
        "preventive_actions": [
          "Implement automatic storage expansion",
          "Set up storage monitoring",
          "Plan data archiving strategy"
        ]
      }
    ]
  },
  "high_confidence_predictions": 2
}
```

#### Recommendation Engine

##### Get Best Practice Recommendations
```http
POST /api/v1/intelligence/recommendations/analyze
Content-Type: application/json

{
  "project_name": "my-project",
  "categories": ["security", "performance", "maintainability"],
  "include_implementation_guide": true
}
```

**Response:**
```json
{
  "project_name": "my-project",
  "project_context": {
    "languages": ["python", "javascript"],
    "frameworks": ["django", "react"],
    "has_dockerfile": true,
    "has_k8s": false,
    "has_terraform": true,
    "project_size": "medium"
  },
  "total_recommendations": 12,
  "recommendations_by_category": {
    "security": [
      {
        "id": "implement_oauth2",
        "priority": "critical",
        "title": "Implement OAuth2 authentication",
        "description": "Replace basic auth with OAuth2/OIDC",
        "rationale": "OAuth2 provides better security and user experience",
        "benefits": [
          "Industry-standard authentication security",
          "Single sign-on capabilities",
          "Reduced password management burden"
        ],
        "implementation_guide": [
          "Choose OAuth2 provider (Auth0, Google, etc.)",
          "Implement OAuth2 flow in application",
          "Set up proper token validation",
          "Add session management"
        ],
        "effort_estimate": "medium",
        "risk_level": "low"
      }
    ]
  },
  "implementation_roadmap": {
    "phase_1_immediate": [
      {
        "id": "implement_oauth2",
        "category": "security",
        "effort": "medium"
      }
    ],
    "phase_2_short_term": [],
    "phase_3_long_term": []
  }
}
```

#### Self-Healing System

##### Start Monitoring
```http
POST /api/v1/intelligence/self-healing/monitor/start
Content-Type: application/json

{
  "project_name": "my-project",
  "monitoring_interval": 60,
  "auto_heal_enabled": true,
  "notification_webhook": "https://your-app.com/webhooks/healing"
}
```

##### Get Health Report
```http
GET /api/v1/intelligence/self-healing/health/{project_name}
```

**Response:**
```json
{
  "project_name": "my-project",
  "timestamp": "2024-08-20T10:30:00Z",
  "monitoring_active": true,
  "auto_heal_enabled": true,
  "system_health": {
    "disk_space": {
      "status": "healthy",
      "usage_percent": 45
    },
    "memory_usage": {
      "status": "healthy",
      "usage_percent": 62
    },
    "service_status": {
      "status": "issues_found",
      "issues": [
        {
          "service": "postgresql",
          "status": "inactive"
        }
      ]
    }
  },
  "recent_healing_actions": [
    {
      "action_id": "restart_postgresql",
      "timestamp": "2024-08-20T09:45:00Z",
      "success": true,
      "execution_time": 15.3
    }
  ],
  "recommendations": [
    "PostgreSQL service was automatically restarted",
    "Consider monitoring database performance"
  ]
}
```

##### Execute Healing Action
```http
POST /api/v1/intelligence/self-healing/heal
Content-Type: application/json

{
  "project_name": "my-project",
  "action_id": "fix_disk_space",
  "force_execution": false,
  "context": {
    "filesystem": "/var/lib/docker"
  }
}
```

### 2. System Coordination APIs

#### System Status

##### Get Overall System Status
```http
GET /api/v1/system/status
```

**Response:**
```json
{
  "timestamp": "2024-08-20T10:30:00Z",
  "coordination_active": true,
  "overall_health": 0.94,
  "components": {
    "intelligence": {
      "status": "online",
      "health_score": 0.98,
      "last_health_check": "2024-08-20T10:29:45Z",
      "capabilities": ["analysis", "auto-fix", "optimization", "predictions"],
      "metrics": {
        "uptime": 86400,
        "cpu_usage": 0.15,
        "memory_usage": 0.32
      }
    },
    "deployment": {
      "status": "online",
      "health_score": 0.92,
      "capabilities": ["orchestration", "strategies", "rollback"]
    }
  },
  "tasks": {
    "total_tasks": 15,
    "pending_tasks": 2,
    "running_tasks": 1,
    "completed_tasks": 12,
    "failed_tasks": 0
  },
  "integration_conflicts": 0
}
```

##### Get Integration Report
```http
GET /api/v1/system/integration/report
```

**Response:**
```json
{
  "timestamp": "2024-08-20T10:30:00Z",
  "agent_outputs": 23,
  "unique_agents": 8,
  "integration_conflicts": 1,
  "agent_summary": {
    "agent_1_genesis": {
      "agent_name": "Project Genesis",
      "output_count": 3,
      "components": ["setup-project"],
      "output_types": ["configuration", "templates"]
    },
    "agent_8_integration": {
      "agent_name": "Integration Coordinator",
      "output_count": 8,
      "components": ["intelligence", "coordination"],
      "output_types": ["integration", "tests", "documentation"]
    }
  },
  "conflict_summary": [
    {
      "id": "conflict_123",
      "type": "configuration_overlap",
      "components": ["deployment", "governance"],
      "severity": "medium",
      "auto_resolvable": true
    }
  ]
}
```

#### Task Management

##### Create Coordination Task
```http
POST /api/v1/system/tasks
Content-Type: application/json

{
  "name": "System Health Check",
  "type": "health_check",
  "level": "medium",
  "components": ["intelligence", "deployment", "governance"],
  "parameters": {
    "deep_check": true,
    "include_metrics": true
  }
}
```

**Response:**
```json
{
  "task_id": "task-456",
  "status": "pending",
  "created_at": "2024-08-20T10:30:00Z",
  "estimated_completion": "2024-08-20T10:32:00Z"
}
```

##### Get Task Status
```http
GET /api/v1/system/tasks/{task_id}
```

**Response:**
```json
{
  "id": "task-456",
  "name": "System Health Check",
  "type": "health_check",
  "status": "completed",
  "created_at": "2024-08-20T10:30:00Z",
  "started_at": "2024-08-20T10:30:15Z",
  "completed_at": "2024-08-20T10:31:42Z",
  "result": {
    "intelligence": {
      "status": "online",
      "health_score": 0.98
    },
    "deployment": {
      "status": "online",
      "health_score": 0.92
    }
  }
}
```

#### Agent Output Management

##### Register Agent Output
```http
POST /api/v1/system/agent-outputs
Content-Type: application/json

{
  "agent_id": "agent_8_integration",
  "agent_name": "Integration Coordinator",
  "component": "intelligence",
  "output_type": "configuration",
  "content": {
    "config_version": "1.0",
    "settings": {
      "auto_heal_enabled": true,
      "monitoring_interval": 60
    }
  },
  "dependencies": ["monitoring"],
  "integration_requirements": ["validate_config", "merge_settings"]
}
```

**Response:**
```json
{
  "output_id": "output-789",
  "status": "registered",
  "integration_status": "pending",
  "conflicts_detected": 0,
  "timestamp": "2024-08-20T10:30:00Z"
}
```

### 3. Project Management APIs

#### Project Lifecycle

##### Create Project
```http
POST /api/v1/projects
Content-Type: application/json

{
  "name": "my-new-project",
  "type": "web-service",
  "template": "python-flask",
  "configuration": {
    "language": "python",
    "framework": "flask",
    "database": "postgresql",
    "deployment_target": "gcp"
  },
  "governance": {
    "compliance_level": "soc2",
    "cost_budget": 1000,
    "team": "backend-team"
  }
}
```

**Response:**
```json
{
  "project_id": "proj-123",
  "name": "my-new-project",
  "status": "created",
  "repository_url": "https://github.com/org/my-new-project",
  "infrastructure": {
    "gcp_project": "my-org-my-new-project-dev",
    "terraform_state": "gs://my-org-terraform-state/my-new-project/"
  },
  "next_steps": [
    "Clone repository",
    "Run initial deployment",
    "Configure monitoring"
  ]
}
```

##### Get Project Details
```http
GET /api/v1/projects/{project_id}
```

##### Update Project Configuration
```http
PUT /api/v1/projects/{project_id}/config
Content-Type: application/json

{
  "configuration": {
    "auto_scaling": true,
    "max_instances": 10,
    "monitoring_enabled": true
  }
}
```

##### Delete Project
```http
DELETE /api/v1/projects/{project_id}
?confirm=true&cleanup_infrastructure=true
```

#### Project Analysis

##### Run Full Analysis
```http
POST /api/v1/projects/{project_id}/analyze
Content-Type: application/json

{
  "analysis_types": ["auto_fix", "optimization", "predictions", "recommendations"],
  "deep_analysis": true,
  "include_cross_project_insights": true
}
```

**Response:**
```json
{
  "analysis_id": "analysis-456",
  "status": "completed",
  "results": {
    "auto_fix": {
      "total_issues": 3,
      "auto_fixable": 2,
      "critical_issues": 0
    },
    "optimization": {
      "cost_savings_potential": "$200-400/month",
      "performance_improvements": 2,
      "resource_optimizations": 1
    },
    "predictions": {
      "high_risk_predictions": 1,
      "capacity_warnings": 0
    },
    "recommendations": {
      "critical_recommendations": 1,
      "immediate_actions": 2
    }
  },
  "cross_project_insights": {
    "similar_projects": ["project-a", "project-b"],
    "common_patterns": ["python-flask", "postgresql"],
    "shared_optimizations": 3
  }
}
```

### 4. Cross-Project APIs

##### Get Cross-Project Insights
```http
POST /api/v1/analytics/cross-project-insights
Content-Type: application/json

{
  "project_names": ["project-a", "project-b", "project-c"],
  "analysis_types": ["patterns", "issues", "optimizations"],
  "time_range": {
    "start": "2024-07-01T00:00:00Z",
    "end": "2024-08-20T23:59:59Z"
  }
}
```

**Response:**
```json
{
  "analysis_timestamp": "2024-08-20T10:30:00Z",
  "projects_analyzed": ["project-a", "project-b", "project-c"],
  "cross_project_patterns": {
    "technology_stacks": {
      "python": 3,
      "javascript": 2,
      "go": 1
    },
    "infrastructure_patterns": {
      "docker": 3,
      "kubernetes": 2,
      "terraform": 3
    }
  },
  "common_issues": {
    "missing_gitignore": {
      "count": 2,
      "severity": "medium",
      "projects": ["project-a", "project-c"]
    }
  },
  "optimization_opportunities": {
    "total_cost_savings": "$1500-3000/month",
    "performance_improvements": 8,
    "security_enhancements": 4
  }
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid project configuration",
    "details": {
      "field": "configuration.database",
      "reason": "Unsupported database type"
    },
    "request_id": "req-123",
    "timestamp": "2024-08-20T10:30:00Z"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `AUTHENTICATION_REQUIRED` | 401 | Authentication required |
| `INSUFFICIENT_PERMISSIONS` | 403 | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Rate Limiting

### Rate Limits
- **General API**: 1000 requests/hour per API key
- **Analysis APIs**: 100 requests/hour per project
- **System APIs**: 500 requests/hour per service account

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1692532800
```

## Webhooks

### Webhook Events

#### Project Events
- `project.created`
- `project.updated`
- `project.deleted`
- `project.analysis.completed`

#### System Events
- `system.health.degraded`
- `system.health.recovered`
- `component.offline`
- `component.online`

#### Intelligence Events
- `auto_fix.completed`
- `prediction.high_risk`
- `recommendation.critical`
- `healing.action.executed`

### Webhook Payload
```json
{
  "event": "project.analysis.completed",
  "timestamp": "2024-08-20T10:30:00Z",
  "data": {
    "project_id": "proj-123",
    "analysis_id": "analysis-456",
    "results_summary": {
      "total_issues": 3,
      "critical_issues": 0,
      "recommendations": 5
    }
  },
  "metadata": {
    "webhook_id": "webhook-789",
    "delivery_attempt": 1
  }
}
```

## SDKs and Libraries

### Python SDK
```python
from bootstrapper_sdk import BootstrapperClient

client = BootstrapperClient(api_key="your-api-key")

# Run analysis
analysis = client.intelligence.auto_fix.analyze("my-project")
print(f"Found {analysis.total_issues} issues")

# Execute auto-fix
result = client.intelligence.auto_fix.execute("my-project", issue_ids=["security_vulnerability"])
```

### JavaScript SDK
```javascript
import { BootstrapperClient } from '@bootstrapper/sdk';

const client = new BootstrapperClient({ apiKey: 'your-api-key' });

// Get system status
const status = await client.system.getStatus();
console.log(`System health: ${status.overall_health}`);

// Create project
const project = await client.projects.create({
  name: 'my-new-project',
  type: 'web-service'
});
```

### CLI Tool
```bash
# Install CLI
npm install -g @bootstrapper/cli

# Configure authentication
bootstrapper auth login

# Create project
bootstrapper projects create my-project --type web-service

# Run analysis
bootstrapper analyze my-project --include-all

# Get system status
bootstrapper system status
```

---

*This API reference is maintained by Agent 8 (Integration Coordinator) and reflects the current API design. For the latest updates and examples, see the interactive API documentation at https://docs.bootstrapper.dev*