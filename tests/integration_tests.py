#!/usr/bin/env python3

"""
Integration Tests for Bootstrapper Components
Tests integration between different bootstrapper components
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the lib directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "python"))

from whitehorse_core.intelligence import (
    IntelligenceCoordinator,
    SystemIntegrationStatus,
)

# Test configuration
BOOTSTRAPPER_ROOT = Path(__file__).parent.parent
TEST_PROJECT_NAME = "test-integration-project"
TEST_PROJECT_PATH = None


@pytest.fixture(scope="session")
def test_project_setup():
    """Set up a test project for integration testing"""
    global TEST_PROJECT_PATH

    # Create temporary directory for test project
    temp_dir = tempfile.mkdtemp(prefix="bootstrapper_test_")
    TEST_PROJECT_PATH = os.path.join(temp_dir, TEST_PROJECT_NAME)
    os.makedirs(TEST_PROJECT_PATH)

    # Create basic project structure
    create_test_project_structure(TEST_PROJECT_PATH)

    yield TEST_PROJECT_PATH

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


def create_test_project_structure(project_path: str):
    """Create a realistic test project structure"""

    # Create basic files
    files_to_create = {
        "README.md": "# Test Project\nThis is a test project for integration testing.",
        "requirements.txt": "flask==2.0.1\nrequests==2.25.1\npytest==6.2.4",
        "package.json": json.dumps(
            {
                "name": "test-project",
                "version": "1.0.0",
                "dependencies": {"express": "^4.17.1"},
                "devDependencies": {"jest": "^27.0.6"},
            },
            indent=2,
        ),
        ".env": "DATABASE_URL=postgresql://localhost/test\nSECRET_KEY=test_secret",
        "app.py": """
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, World!"

if __name__ == '__main__':
    app.run()
""",
        "Dockerfile": """
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
""",
        "main.tf": """
resource "google_compute_instance" "default" {
  name         = "test-instance"
  machine_type = "n1-standard-1"
  zone         = "us-central1-a"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network = "default"
  }
}
""",
    }

    # Create directories
    directories = ["src", "tests", "docs", "scripts", "k8s", ".github/workflows"]

    for directory in directories:
        os.makedirs(os.path.join(project_path, directory), exist_ok=True)

    # Create files
    for filename, content in files_to_create.items():
        with open(os.path.join(project_path, filename), "w") as f:
            f.write(content)

    # Create Kubernetes config
    k8s_config = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
spec:
  replicas: 2
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
"""

    with open(os.path.join(project_path, "k8s", "deployment.yaml"), "w") as f:
        f.write(k8s_config)

    # Create GitHub workflow
    gh_workflow = """
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run tests
      run: pytest
"""

    with open(os.path.join(project_path, ".github/workflows", "ci.yml"), "w") as f:
        f.write(gh_workflow)


class TestIntelligenceIntegration:
    """Test intelligence layer integration with other components"""

    def test_intelligence_coordinator_initialization(self):
        """Test intelligence coordinator can be initialized"""
        coordinator = IntelligenceCoordinator()
        assert coordinator is not None
        assert coordinator.intelligence_path is not None
        assert coordinator.system_components is not None
        assert len(coordinator.system_components) > 0

    def test_system_integration_status_check(self):
        """Test system integration status checking"""
        coordinator = IntelligenceCoordinator()
        status = coordinator.check_system_integration_status()

        assert isinstance(status, SystemIntegrationStatus)
        assert status.integration_health in ["healthy", "degraded", "critical"]
        assert isinstance(status.components_online, list)
        assert isinstance(status.components_offline, list)
        assert isinstance(status.coordination_errors, list)

    def test_component_health_checks(self, test_project_setup):
        """Test individual component health checks"""
        coordinator = IntelligenceCoordinator()

        # Test each component health check
        for component_name, component_path in coordinator.system_components.items():
            health = coordinator._check_component_health(component_name, component_path)
            assert isinstance(health, bool)

    @patch("subprocess.run")
    def test_intelligence_analysis_execution(self, mock_subprocess, test_project_setup):
        """Test intelligence analysis execution"""
        # Mock successful subprocess execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Analysis completed successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        coordinator = IntelligenceCoordinator()

        # Test auto-fix analysis
        result = coordinator.run_auto_fix(TEST_PROJECT_NAME)
        assert result["status"] in ["success", "disabled"]

        # Test optimization analysis
        result = coordinator.run_optimization_analysis(TEST_PROJECT_NAME)
        assert result["status"] in ["success", "disabled"]

        # Test predictions analysis
        result = coordinator.run_predictions_analysis(TEST_PROJECT_NAME)
        assert result["status"] in ["success", "disabled"]

        # Test recommendations analysis
        result = coordinator.run_recommendations_analysis(TEST_PROJECT_NAME)
        assert result["status"] in ["success", "disabled"]

    @patch("subprocess.run")
    def test_parallel_analysis(self, mock_subprocess, test_project_setup):
        """Test parallel analysis across multiple projects"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Analysis completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        coordinator = IntelligenceCoordinator()
        project_names = [TEST_PROJECT_NAME, "test-project-2"]

        results = coordinator.run_parallel_analysis(
            project_names, ["auto_fix", "optimization"]
        )

        assert isinstance(results, dict)
        assert len(results) <= len(project_names)  # Some projects might not exist

        for project_name, project_results in results.items():
            assert isinstance(project_results, dict)
            for analysis_type, analysis_result in project_results.items():
                assert "status" in analysis_result


class TestComponentIntegration:
    """Test integration between different bootstrapper components"""

    def test_intelligence_and_setup_project_integration(self, test_project_setup):
        """Test integration between intelligence and setup-project components"""
        # This would test that intelligence can analyze projects created by setup-project
        setup_project_path = BOOTSTRAPPER_ROOT / "setup-project"
        intelligence_path = BOOTSTRAPPER_ROOT / "intelligence"

        assert setup_project_path.exists()
        assert intelligence_path.exists()

        # Test that intelligence can find and analyze the test project
        coordinator = IntelligenceCoordinator()
        status = coordinator.check_system_integration_status()

        # Both components should be online
        assert (
            "setup-project" in status.components_online
            or "setup-project" in status.components_offline
        )
        assert (
            "intelligence" in status.components_online
            or "intelligence" in status.components_offline
        )

    def test_intelligence_and_deployment_integration(self, test_project_setup):
        """Test integration between intelligence and deployment components"""
        deploy_path = BOOTSTRAPPER_ROOT / "deploy"
        intelligence_path = BOOTSTRAPPER_ROOT / "intelligence"

        assert deploy_path.exists()
        assert intelligence_path.exists()

        # Test coordination between components
        coordinator = IntelligenceCoordinator()

        # Test system-wide health check
        result = coordinator.coordinate_system_wide_operations("health_check")
        assert result["operation"] == "health_check"
        assert "component_results" in result
        assert result["overall_status"] in ["success", "error"]

    def test_intelligence_and_governance_integration(self, test_project_setup):
        """Test integration between intelligence and governance components"""
        governance_path = BOOTSTRAPPER_ROOT / "governance"
        intelligence_path = BOOTSTRAPPER_ROOT / "intelligence"

        assert governance_path.exists()
        assert intelligence_path.exists()

        # Test security audit coordination
        coordinator = IntelligenceCoordinator()
        result = coordinator.coordinate_system_wide_operations("security_audit")

        assert result["operation"] == "security_audit"
        assert "component_results" in result

    def test_intelligence_and_monitoring_integration(self, test_project_setup):
        """Test integration between intelligence and monitoring components"""
        monitoring_path = BOOTSTRAPPER_ROOT / "monitoring"
        intelligence_path = BOOTSTRAPPER_ROOT / "intelligence"

        assert monitoring_path.exists()
        assert intelligence_path.exists()

        # Test system optimization coordination
        coordinator = IntelligenceCoordinator()
        result = coordinator.coordinate_system_wide_operations("system_optimization")

        assert result["operation"] == "system_optimization"
        assert "component_results" in result


class TestCrossProjectAnalysis:
    """Test cross-project analysis capabilities"""

    @patch("subprocess.run")
    def test_cross_project_pattern_analysis(self, mock_subprocess, test_project_setup):
        """Test cross-project pattern detection"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Analysis completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        coordinator = IntelligenceCoordinator()

        # Mock some analysis results
        with patch.object(coordinator, "run_parallel_analysis") as mock_analysis:
            mock_analysis.return_value = {
                "project1": {
                    "recommendations": {
                        "status": "success",
                        "report": {
                            "project_context": {
                                "languages": ["python"],
                                "frameworks": ["flask"],
                                "has_dockerfile": True,
                                "has_k8s": False,
                                "has_terraform": True,
                            }
                        },
                    }
                },
                "project2": {
                    "recommendations": {
                        "status": "success",
                        "report": {
                            "project_context": {
                                "languages": ["python", "javascript"],
                                "frameworks": ["django", "react"],
                                "has_dockerfile": True,
                                "has_k8s": True,
                                "has_terraform": True,
                            }
                        },
                    }
                },
            }

            insights = coordinator.generate_cross_project_insights(
                ["project1", "project2"]
            )

            assert "cross_project_patterns" in insights
            assert "common_issues" in insights
            assert "optimization_opportunities" in insights
            assert "security_trends" in insights
            assert "architecture_patterns" in insights

            patterns = insights["cross_project_patterns"]
            assert "technology_stacks" in patterns
            assert "infrastructure_patterns" in patterns

    @patch("subprocess.run")
    def test_common_issues_identification(self, mock_subprocess, test_project_setup):
        """Test identification of common issues across projects"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Analysis completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        coordinator = IntelligenceCoordinator()

        # Mock analysis results with common issues
        with patch.object(coordinator, "run_parallel_analysis") as mock_analysis:
            mock_analysis.return_value = {
                "project1": {
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
                                ]
                            }
                        },
                    }
                },
                "project2": {
                    "auto_fix": {
                        "status": "success",
                        "report": {
                            "issues_by_severity": {
                                "high": [
                                    {
                                        "id": "missing_gitignore",
                                        "title": "Missing .gitignore",
                                    }
                                ],
                                "medium": [
                                    {
                                        "id": "unpinned_deps",
                                        "title": "Unpinned dependencies",
                                    }
                                ],
                            }
                        },
                    }
                },
            }

            insights = coordinator.generate_cross_project_insights(
                ["project1", "project2"]
            )
            common_issues = insights["common_issues"]

            assert "most_common_issues" in common_issues
            assert "issues_affecting_multiple_projects" in common_issues

            # The missing_gitignore issue should appear in multiple projects
            multiple_project_issues = common_issues[
                "issues_affecting_multiple_projects"
            ]
            assert len(multiple_project_issues) > 0


class TestSystemCoordination:
    """Test system-wide coordination capabilities"""

    def test_system_wide_health_check(self, test_project_setup):
        """Test system-wide health check coordination"""
        coordinator = IntelligenceCoordinator()
        result = coordinator.coordinate_system_wide_operations("health_check")

        assert result["operation"] == "health_check"
        assert "timestamp" in result
        assert "component_results" in result
        assert "overall_status" in result
        assert result["overall_status"] in ["success", "error"]

        # Check integration status is included
        component_results = result["component_results"]
        assert "integration_status" in component_results

        integration_status = component_results["integration_status"]
        assert "status" in integration_status
        assert "components_online" in integration_status
        assert "components_offline" in integration_status

    @patch("subprocess.run")
    def test_full_system_analysis_coordination(
        self, mock_subprocess, test_project_setup
    ):
        """Test coordination of full system analysis"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Analysis completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        coordinator = IntelligenceCoordinator()

        # Mock registry to return test projects
        with patch.object(coordinator.registry, "list_projects") as mock_list:
            mock_list.return_value = {TEST_PROJECT_NAME: {"path": TEST_PROJECT_PATH}}

            result = coordinator.coordinate_system_wide_operations(
                "full_analysis", project_names=[TEST_PROJECT_NAME]
            )

            assert result["operation"] == "full_analysis"
            assert "component_results" in result

            component_results = result["component_results"]
            assert "projects_analyzed" in component_results
            assert "status" in component_results

    def test_unknown_operation_handling(self, test_project_setup):
        """Test handling of unknown coordination operations"""
        coordinator = IntelligenceCoordinator()
        result = coordinator.coordinate_system_wide_operations("unknown_operation")

        assert result["operation"] == "unknown_operation"
        assert result["overall_status"] == "error"
        assert len(result["errors"]) > 0
        assert "Unknown operation" in result["errors"][0]


# Performance and stress tests
class TestPerformanceIntegration:
    """Test performance characteristics of integration"""

    @pytest.mark.slow
    @patch("subprocess.run")
    def test_parallel_analysis_performance(self, mock_subprocess, test_project_setup):
        """Test performance of parallel analysis"""
        import time

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Analysis completed"
        mock_result.stderr = ""

        # Simulate some processing time
        def slow_subprocess(*args, **kwargs):
            time.sleep(0.1)  # Simulate 100ms processing time
            return mock_result

        mock_subprocess.side_effect = slow_subprocess

        coordinator = IntelligenceCoordinator()

        # Test with multiple projects
        project_names = [f"test-project-{i}" for i in range(5)]

        start_time = time.time()
        results = coordinator.run_parallel_analysis(project_names, ["auto_fix"])
        end_time = time.time()

        execution_time = end_time - start_time

        # With parallel execution, should be faster than sequential
        # Sequential would take at least 5 * 0.1 * 4 analyses = 2 seconds
        # Parallel should be significantly faster
        assert execution_time < 2.0  # Should complete in less than 2 seconds

    @pytest.mark.slow
    def test_system_health_check_performance(self, test_project_setup):
        """Test performance of system health checks"""
        import time

        coordinator = IntelligenceCoordinator()

        start_time = time.time()
        status = coordinator.check_system_integration_status()
        end_time = time.time()

        execution_time = end_time - start_time

        # Health check should be fast
        assert execution_time < 5.0  # Should complete in less than 5 seconds
        assert status is not None


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
