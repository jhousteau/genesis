#!/usr/bin/env python3

"""
End-to-End Tests for Bootstrapper
Tests complete workflows from project creation to deployment
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Add the lib directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "python"))

from whitehorse_core.intelligence import IntelligenceCoordinator

# Test configuration
BOOTSTRAPPER_ROOT = Path(__file__).parent.parent
E2E_TEST_PROJECT_NAME = "e2e-test-project"
E2E_TEST_PROJECT_PATH = None


@pytest.fixture(scope="module")
def e2e_test_environment():
    """Set up end-to-end test environment"""
    global E2E_TEST_PROJECT_PATH

    # Create temporary directory for E2E testing
    temp_dir = tempfile.mkdtemp(prefix="bootstrapper_e2e_")
    E2E_TEST_PROJECT_PATH = os.path.join(temp_dir, E2E_TEST_PROJECT_NAME)

    yield {
        "temp_dir": temp_dir,
        "project_path": E2E_TEST_PROJECT_PATH,
        "project_name": E2E_TEST_PROJECT_NAME,
    }

    # Cleanup
    import shutil

    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        logging.warning(f"Failed to cleanup E2E test directory: {e}")


def run_command(
    command: List[str], cwd: str = None, timeout: int = 60
) -> Dict[str, Any]:
    """Run a command and return result"""
    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(command),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "command": " ".join(command),
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "command": " ".join(command),
        }


class TestCompleteWorkflow:
    """Test complete workflows from project creation to analysis"""

    def test_project_creation_to_intelligence_analysis_workflow(
        self, e2e_test_environment
    ):
        """Test complete workflow: Create project -> Analyze with intelligence"""
        env = e2e_test_environment

        # Step 1: Create project structure (simulating setup-project)
        self._create_realistic_project(env["project_path"])

        # Step 2: Initialize intelligence coordinator
        coordinator = IntelligenceCoordinator()

        # Step 3: Check system integration status
        integration_status = coordinator.check_system_integration_status()
        assert integration_status.integration_health in [
            "healthy",
            "degraded",
            "critical",
        ]

        # Step 4: Run intelligence analysis (mocked for E2E)
        with patch("subprocess.run") as mock_subprocess:
            # Mock successful analysis
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(
                {
                    "project_name": env["project_name"],
                    "total_issues": 5,
                    "auto_fixable_count": 3,
                }
            )
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Run full analysis
            result = coordinator.run_full_analysis(env["project_name"])
            assert result["project_name"] == env["project_name"]
            assert "analyses" in result

    def test_multi_project_coordination_workflow(self, e2e_test_environment):
        """Test workflow with multiple projects and cross-project analysis"""
        env = e2e_test_environment

        # Create multiple test projects
        project_names = []
        for i in range(3):
            project_name = f"multi-test-project-{i}"
            project_path = os.path.join(env["temp_dir"], project_name)
            self._create_realistic_project(project_path)
            project_names.append(project_name)

        coordinator = IntelligenceCoordinator()

        # Test parallel analysis across projects
        with patch("subprocess.run") as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Analysis completed"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Run parallel analysis
            results = coordinator.run_parallel_analysis(
                project_names, ["auto_fix", "recommendations"]
            )

            assert isinstance(results, dict)
            assert len(results) <= len(project_names)

            # Test cross-project insights generation
            with patch.object(coordinator, "run_parallel_analysis") as mock_analysis:
                mock_analysis.return_value = self._create_mock_analysis_results(
                    project_names
                )

                insights = coordinator.generate_cross_project_insights(project_names)

                assert "cross_project_patterns" in insights
                assert "common_issues" in insights
                assert "optimization_opportunities" in insights
                assert "projects_analyzed" in insights
                assert insights["projects_analyzed"] == project_names

    def test_system_wide_operations_workflow(self, e2e_test_environment):
        """Test system-wide coordination operations"""
        env = e2e_test_environment

        coordinator = IntelligenceCoordinator()

        # Test 1: System health check
        health_result = coordinator.coordinate_system_wide_operations("health_check")

        assert health_result["operation"] == "health_check"
        assert "component_results" in health_result
        assert "overall_status" in health_result
        assert health_result["overall_status"] in ["success", "error"]

        # Test 2: Full analysis coordination (mocked)
        with patch("subprocess.run") as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Analysis completed"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            with patch.object(coordinator.registry, "list_projects") as mock_list:
                mock_list.return_value = {
                    env["project_name"]: {"path": env["project_path"]}
                }

                analysis_result = coordinator.coordinate_system_wide_operations(
                    "full_analysis"
                )

                assert analysis_result["operation"] == "full_analysis"
                assert "component_results" in analysis_result

        # Test 3: Security audit coordination
        security_result = coordinator.coordinate_system_wide_operations(
            "security_audit"
        )

        assert security_result["operation"] == "security_audit"
        assert "component_results" in security_result

        # Test 4: System optimization coordination
        optimization_result = coordinator.coordinate_system_wide_operations(
            "system_optimization"
        )

        assert optimization_result["operation"] == "system_optimization"
        assert "component_results" in optimization_result

    def test_error_handling_and_recovery_workflow(self, e2e_test_environment):
        """Test error handling and recovery in workflows"""
        env = e2e_test_environment

        coordinator = IntelligenceCoordinator()

        # Test handling of invalid project
        with patch("subprocess.run") as mock_subprocess:
            # Mock subprocess failure
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Project not found"
            mock_subprocess.return_value = mock_result

            result = coordinator.run_auto_fix("non-existent-project")

            assert result["status"] in ["error", "disabled"]

        # Test handling of timeout
        with patch("subprocess.run") as mock_subprocess:
            # Mock subprocess timeout
            mock_subprocess.side_effect = subprocess.TimeoutExpired("test", 5)

            result = coordinator.run_optimization_analysis(env["project_name"])

            assert result["status"] == "timeout"

        # Test unknown operation handling
        result = coordinator.coordinate_system_wide_operations("invalid_operation")

        assert result["overall_status"] == "error"
        assert len(result["errors"]) > 0

    def _create_realistic_project(self, project_path: str):
        """Create a realistic project structure for testing"""
        os.makedirs(project_path, exist_ok=True)

        # Create project files
        files = {
            "README.md": """# Test Project
This is a test project for end-to-end testing.

## Setup
1. Install dependencies
2. Run the application

## Development
- Use pytest for testing
- Follow PEP 8 style guide
""",
            "requirements.txt": """flask==2.1.0
requests==2.27.1
pytest==7.0.1
black==22.3.0
flake8==4.0.1
""",
            "app.py": """
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({"message": "Hello, World!"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
""",
            "Dockerfile": """FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "app.py"]
""",
            "docker-compose.yml": """version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: testdb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
""",
            ".env.example": """FLASK_ENV=development
DATABASE_URL=postgresql://user:password@localhost/testdb
SECRET_KEY=your-secret-key-here
""",
            ".gitignore": """__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/
""",
            "main.tf": """terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

resource "google_compute_instance" "app_server" {
  name         = "test-app-server"
  machine_type = "e2-micro"
  zone         = "${var.region}-a"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 20
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker
  EOF

  tags = ["http-server", "https-server"]
}

output "instance_ip" {
  value = google_compute_instance.app_server.network_interface[0].access_config[0].nat_ip
}
""",
            "pytest.ini": """[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
""",
            "pyproject.toml": '''[tool.black]
line-length = 88
target-version = ['py39']
include = '\\.pyi?$'
extend-exclude = """
/(
  migrations
  | .venv
  | venv
)/
"""

[tool.flake8]
max-line-length = 88
extend-ignore = E203, W503
''',
        }

        # Create directories
        directories = ["tests", "src", "docs", "scripts", "k8s", ".github/workflows"]

        for directory in directories:
            os.makedirs(os.path.join(project_path, directory), exist_ok=True)

        # Write files
        for filename, content in files.items():
            with open(os.path.join(project_path, filename), "w") as f:
                f.write(content)

        # Create test files
        test_files = {
            "tests/test_app.py": """
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_hello(client):
    rv = client.get('/')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['message'] == 'Hello, World!'

def test_health(client):
    rv = client.get('/health')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['status'] == 'healthy'
""",
            "tests/__init__.py": "",
            "k8s/deployment.yaml": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
  labels:
    app: test-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: test-app
  template:
    metadata:
      labels:
        app: test-app
    spec:
      containers:
      - name: test-app
        image: test-app:latest
        ports:
        - containerPort: 5000
        env:
        - name: FLASK_ENV
          value: "production"
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: test-app-service
spec:
  selector:
    app: test-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
  type: LoadBalancer
""",
            ".github/workflows/ci.yml": """name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python 3.9
      uses: actions/setup-python@v3
      with:
        python-version: 3.9
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run linting
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Run tests
      run: |
        pytest tests/ -v --tb=short
    
    - name: Build Docker image
      run: |
        docker build -t test-app:latest .
    
    - name: Test Docker image
      run: |
        docker run -d -p 5000:5000 --name test-container test-app:latest
        sleep 10
        curl -f http://localhost:5000/health || exit 1
        docker stop test-container
        docker rm test-container
""",
        }

        for filename, content in test_files.items():
            file_path = os.path.join(project_path, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)

    def _create_mock_analysis_results(
        self, project_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Create mock analysis results for testing"""
        results = {}

        for i, project_name in enumerate(project_names):
            results[project_name] = {
                "auto_fix": {
                    "status": "success",
                    "report": {
                        "issues_by_severity": {
                            "high": [
                                {
                                    "id": "missing_gitignore",
                                    "title": "Missing .gitignore",
                                },
                                {
                                    "id": "dockerfile_root_user",
                                    "title": "Docker runs as root",
                                },
                            ],
                            "medium": [
                                {
                                    "id": "unpinned_deps",
                                    "title": "Unpinned dependencies",
                                }
                            ],
                        }
                    },
                },
                "recommendations": {
                    "status": "success",
                    "report": {
                        "project_context": {
                            "languages": ["python"],
                            "frameworks": ["flask"],
                            "has_dockerfile": True,
                            "has_k8s": i % 2 == 0,  # Alternate between projects
                            "has_terraform": True,
                            "has_ci_cd": True,
                            "project_size": "medium",
                        },
                        "recommendations_by_category": {
                            "security": [
                                {
                                    "id": "implement_secrets_management",
                                    "priority": "critical",
                                    "title": "Implement proper secrets management",
                                }
                            ],
                            "performance": [
                                {
                                    "id": "implement_caching",
                                    "priority": "medium",
                                    "title": "Implement caching strategy",
                                }
                            ],
                        },
                        "implementation_roadmap": {
                            "phase_1_immediate": [
                                {
                                    "id": "implement_secrets_management",
                                    "category": "security",
                                }
                            ],
                            "phase_2_short_term": [
                                {"id": "implement_caching", "category": "performance"}
                            ],
                            "phase_3_long_term": [],
                        },
                    },
                },
                "optimization": {
                    "status": "success",
                    "report": {
                        "recommendations_by_category": {
                            "cost": [
                                {
                                    "title": "Optimize instance size",
                                    "savings_estimate": "$100-200/month",
                                    "priority": "high",
                                }
                            ],
                            "performance": [
                                {
                                    "title": "Implement container optimization",
                                    "performance_impact": "Faster startup times",
                                    "priority": "medium",
                                }
                            ],
                        }
                    },
                },
                "predictions": {
                    "status": "success",
                    "report": {
                        "predictions_by_type": {
                            "failure": [
                                {
                                    "title": "CI/CD pipeline failure risk",
                                    "timeframe": "Next 30 days",
                                    "confidence": 0.7,
                                }
                            ]
                        }
                    },
                },
            }

        return results


class TestPerformanceE2E:
    """End-to-end performance tests"""

    @pytest.mark.slow
    def test_large_scale_analysis_performance(self, e2e_test_environment):
        """Test performance with large number of projects"""
        env = e2e_test_environment

        # Create multiple projects
        project_count = 10
        project_names = []

        for i in range(project_count):
            project_name = f"perf-test-project-{i}"
            project_path = os.path.join(env["temp_dir"], project_name)
            self._create_simple_project(project_path)
            project_names.append(project_name)

        coordinator = IntelligenceCoordinator()

        with patch("subprocess.run") as mock_subprocess:
            # Mock fast analysis
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Analysis completed"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            start_time = time.time()
            results = coordinator.run_parallel_analysis(project_names, ["auto_fix"])
            end_time = time.time()

            execution_time = end_time - start_time

            # Should handle 10 projects efficiently
            assert execution_time < 30.0  # Should complete in less than 30 seconds
            assert len(results) <= project_count

    def _create_simple_project(self, project_path: str):
        """Create a simple project for performance testing"""
        os.makedirs(project_path, exist_ok=True)

        files = {
            "README.md": "# Simple Test Project",
            "requirements.txt": "flask==2.1.0",
            "app.py": """
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, World!"
""",
        }

        for filename, content in files.items():
            with open(os.path.join(project_path, filename), "w") as f:
                f.write(content)


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""

    def test_new_developer_onboarding_scenario(self, e2e_test_environment):
        """Test scenario: New developer onboarding with intelligence analysis"""
        env = e2e_test_environment

        # Scenario: New developer clones project and runs bootstrapper analysis

        # Step 1: Create "existing" project
        self._create_realistic_project(env["project_path"])

        # Step 2: New developer runs system health check
        coordinator = IntelligenceCoordinator()
        health_status = coordinator.check_system_integration_status()

        # Should detect system components
        assert len(health_status.components_online) > 0
        assert health_status.integration_health in ["healthy", "degraded", "critical"]

        # Step 3: Run comprehensive analysis
        with patch("subprocess.run") as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(
                {
                    "project_name": env["project_name"],
                    "total_issues": 3,
                    "auto_fixable_count": 2,
                }
            )
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Run full analysis to understand project state
            result = coordinator.run_full_analysis(env["project_name"])

            assert result["project_name"] == env["project_name"]
            assert "analyses" in result

            # Should provide actionable insights for new developer
            assert result["overall_status"] in [
                "success",
                "partial_failure",
                "disabled",
                "mixed",
            ]

    def test_team_lead_cross_project_analysis_scenario(self, e2e_test_environment):
        """Test scenario: Team lead analyzing multiple projects for patterns"""
        env = e2e_test_environment

        # Scenario: Team lead wants to understand patterns across team's projects

        # Create multiple projects representing team's work
        team_projects = []
        for i, project_type in enumerate(["web-service", "data-pipeline", "ml-model"]):
            project_name = f"team-{project_type}-{i}"
            project_path = os.path.join(env["temp_dir"], project_name)
            self._create_project_by_type(project_path, project_type)
            team_projects.append(project_name)

        coordinator = IntelligenceCoordinator()

        with patch("subprocess.run") as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Analysis completed"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Mock diverse analysis results
            with patch.object(coordinator, "run_parallel_analysis") as mock_analysis:
                mock_analysis.return_value = self._create_team_analysis_results(
                    team_projects
                )

                # Generate cross-project insights
                insights = coordinator.generate_cross_project_insights(team_projects)

                # Team lead should get valuable insights
                assert "cross_project_patterns" in insights
                assert "common_issues" in insights
                assert "security_trends" in insights

                patterns = insights["cross_project_patterns"]
                assert "technology_stacks" in patterns
                assert "infrastructure_patterns" in patterns

                # Should identify common technologies used by team
                tech_stacks = patterns["technology_stacks"]
                assert len(tech_stacks) > 0  # Team uses various technologies

    def test_devops_engineer_system_optimization_scenario(self, e2e_test_environment):
        """Test scenario: DevOps engineer optimizing system-wide operations"""
        env = e2e_test_environment

        # Scenario: DevOps engineer wants to optimize infrastructure across projects

        coordinator = IntelligenceCoordinator()

        # Step 1: Check overall system health
        health_result = coordinator.coordinate_system_wide_operations("health_check")

        assert health_result["operation"] == "health_check"
        assert "component_results" in health_result

        # Step 2: Run system-wide optimization analysis
        optimization_result = coordinator.coordinate_system_wide_operations(
            "system_optimization"
        )

        assert optimization_result["operation"] == "system_optimization"
        assert "component_results" in optimization_result

        # Step 3: Security audit across all components
        security_result = coordinator.coordinate_system_wide_operations(
            "security_audit"
        )

        assert security_result["operation"] == "security_audit"
        assert "component_results" in security_result

        # DevOps engineer should get comprehensive system insights
        all_results = [health_result, optimization_result, security_result]
        for result in all_results:
            assert result["overall_status"] in ["success", "error"]
            assert "timestamp" in result

    def _create_project_by_type(self, project_path: str, project_type: str):
        """Create project structure based on type"""
        os.makedirs(project_path, exist_ok=True)

        base_files = {
            "README.md": f"# {project_type.title()} Project",
            ".gitignore": "__pycache__/\n*.pyc\n.env\n",
        }

        if project_type == "web-service":
            base_files.update(
                {
                    "requirements.txt": "flask==2.1.0\ngunicorn==20.1.0",
                    "app.py": "from flask import Flask\napp = Flask(__name__)",
                    "Dockerfile": "FROM python:3.9-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt",
                }
            )
        elif project_type == "data-pipeline":
            base_files.update(
                {
                    "requirements.txt": "pandas==1.4.0\napache-airflow==2.3.0",
                    "pipeline.py": "import pandas as pd\n# Data pipeline code",
                    "docker-compose.yml": 'version: "3.8"\nservices:\n  airflow:\n    image: apache/airflow:2.3.0',
                }
            )
        elif project_type == "ml-model":
            base_files.update(
                {
                    "requirements.txt": "scikit-learn==1.1.0\ntensorflow==2.9.0",
                    "model.py": "import sklearn\n# ML model code",
                    "Dockerfile": "FROM tensorflow/tensorflow:2.9.0\nWORKDIR /app",
                }
            )

        for filename, content in base_files.items():
            with open(os.path.join(project_path, filename), "w") as f:
                f.write(content)

    def _create_team_analysis_results(
        self, project_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Create mock analysis results for team scenario"""
        results = {}

        project_configs = [
            {
                "languages": ["python"],
                "frameworks": ["flask"],
                "has_dockerfile": True,
                "has_k8s": False,
                "has_terraform": False,
            },
            {
                "languages": ["python"],
                "frameworks": ["pandas", "airflow"],
                "has_dockerfile": True,
                "has_k8s": True,
                "has_terraform": True,
            },
            {
                "languages": ["python"],
                "frameworks": ["tensorflow", "scikit-learn"],
                "has_dockerfile": True,
                "has_k8s": True,
                "has_terraform": False,
            },
        ]

        for i, project_name in enumerate(project_names):
            config = project_configs[i % len(project_configs)]

            results[project_name] = {
                "recommendations": {
                    "status": "success",
                    "report": {"project_context": config},
                },
                "auto_fix": {
                    "status": "success",
                    "report": {
                        "issues_by_severity": {
                            "medium": [
                                {
                                    "id": "missing_env_example",
                                    "title": "Missing .env.example",
                                }
                            ]
                        }
                    },
                },
            }

        return results


if __name__ == "__main__":
    # Run end-to-end tests with verbose output
    pytest.main([__file__, "-v", "--tb=long", "-s"])
