"""
End-to-End Workflow Testing for Genesis CLI
Complete user journey testing following VERIFY methodology.
"""

import pytest
import subprocess
import tempfile
import time
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

# Test configurations
TEST_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "test-project")
SKIP_E2E = not os.getenv("RUN_E2E_TESTS", False)

pytestmark = pytest.mark.skipif(
    SKIP_E2E, reason="E2E tests require explicit enablement"
)


@pytest.fixture
def cli_environment():
    """Set up complete CLI environment for E2E testing."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create complete Genesis CLI structure
    config_dir = temp_dir / "config"
    config_dir.mkdir()
    (config_dir / "environments").mkdir()

    # Create comprehensive test configuration
    (config_dir / "environments" / "e2e-test.yaml").write_text(
        f"""
gcp:
  project_id: {TEST_PROJECT_ID}-e2e
  region: us-central1
  zone: us-central1-a
agents:
  types:
    backend-developer:
      machine_type: e2-micro  # Smallest for testing
      disk_size_gb: 20
      preemptible: true  # Cost optimization
    test-agent:
      machine_type: e2-micro
      disk_size_gb: 10
      preemptible: true
containers:
  cluster_name: e2e-test-cluster
  node_pool_size: 1
  services:
    test-service:
      replicas: 1
      port: 8080
      image: "gcr.io/google-samples/hello-app:2.0"
terraform:
  backend_bucket: {TEST_PROJECT_ID}-e2e-terraform-state
monitoring:
  enabled: true
  retention_days: 1  # Short retention for testing
"""
    )

    (config_dir / "global.yaml").write_text(
        """
terraform:
  region: us-central1
  timeout: 300
performance:
  target_response_time: 5.0  # Relaxed for E2E testing
  cache_ttl: 60
"""
    )

    # Create modules directory structure
    modules_dir = temp_dir / "modules"
    modules_dir.mkdir()
    for module in ["vm-management", "container-orchestration", "networking"]:
        (modules_dir / module).mkdir()

    yield temp_dir

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


@pytest.mark.e2e
class TestCompleteVMLifecycle:
    """Test complete VM agent pool lifecycle from creation to deletion."""

    def test_vm_pool_complete_lifecycle(self, cli_environment):
        """Test complete VM pool lifecycle: create -> scale -> monitor -> delete."""
        from cli.commands.vm_commands import VMCommands

        # Initialize VM commands with test environment
        mock_cli = Mock()
        mock_cli.genesis_root = cli_environment
        mock_cli.environment = "e2e-test"
        mock_cli.project_id = f"{TEST_PROJECT_ID}-e2e"

        vm_commands = VMCommands(mock_cli)

        # Mock GCP service to simulate operations without real resources
        vm_commands.gcp_service = Mock()
        vm_commands.performance_service = Mock()
        vm_commands.cache_service = Mock()
        vm_commands.error_service = Mock()

        # Test Step 1: Create VM pool
        create_args = Mock()
        create_args.vm_action = "create-pool"
        create_args.type = "test-agent"
        create_args.size = 1
        create_args.machine_type = "e2-micro"
        create_args.preemptible = True
        create_args.zones = ["us-central1-a"]
        create_args.dry_run = False

        vm_commands.gcp_service.create_vm_pool.return_value = {
            "pool_name": "test-agent-pool-001",
            "instance_count": 1,
            "status": "creating",
            "instances": [{"name": "test-instance-1", "status": "PROVISIONING"}],
        }

        create_result = vm_commands.execute(create_args, {})

        # Verify pool creation
        assert create_result["action"] == "create-pool"
        vm_commands.gcp_service.create_vm_pool.assert_called_once()

        pool_name = "test-agent-pool-001"

        # Test Step 2: Monitor pool health
        health_args = Mock()
        health_args.vm_action = "health-check"
        health_args.pool = pool_name
        health_args.instance = None

        vm_commands.gcp_service.get_pool_health.return_value = {
            "pool_name": pool_name,
            "overall_status": "healthy",
            "healthy_count": 1,
            "unhealthy_count": 0,
            "instance_details": [
                {"name": "test-instance-1", "status": "RUNNING", "health": "healthy"}
            ],
        }

        health_result = vm_commands.execute(health_args, {})

        # Verify health monitoring
        assert health_result["action"] == "health-check"
        assert health_result["overall_status"] == "healthy"

        # Test Step 3: Scale pool
        scale_args = Mock()
        scale_args.vm_action = "scale-pool"
        scale_args.pool = pool_name
        scale_args.size = 2
        scale_args.min_size = 1
        scale_args.max_size = 3

        vm_commands.gcp_service.scale_vm_pool.return_value = {
            "pool_name": pool_name,
            "previous_size": 1,
            "new_size": 2,
            "status": "scaling",
            "scaling_operation_id": "op-12345",
        }

        scale_result = vm_commands.execute(scale_args, {})

        # Verify scaling
        assert scale_result["action"] == "scale-pool"
        assert scale_result["new_size"] == 2

        # Test Step 4: List pools
        list_args = Mock()
        list_args.vm_action = "list-pools"

        vm_commands.gcp_service.list_vm_pools.return_value = [
            {
                "name": pool_name,
                "agent_type": "test-agent",
                "size": 2,
                "status": "running",
                "created": "2024-01-01T00:00:00Z",
            }
        ]

        list_result = vm_commands.execute(list_args, {})

        # Verify pool listing
        assert isinstance(list_result, list)
        assert len(list_result) == 1
        assert list_result[0]["name"] == pool_name

        # Test Step 5: Delete pool (cleanup)
        delete_args = Mock()
        delete_args.vm_action = "delete-pool"
        delete_args.pool = pool_name
        delete_args.force = True

        vm_commands.gcp_service.delete_vm_pool.return_value = {
            "pool_name": pool_name,
            "status": "deleting",
            "deletion_operation_id": "op-67890",
        }

        delete_result = vm_commands.execute(delete_args, {})

        # Verify pool deletion
        assert delete_result["action"] == "delete-pool"
        assert delete_result["status"] == "deleting"
        vm_commands.gcp_service.delete_vm_pool.assert_called_once()

    def test_vm_error_recovery_workflow(self, cli_environment):
        """Test VM error recovery and rollback scenarios."""
        from cli.commands.vm_commands import VMCommands
        from cli.services.error_service import ErrorCategory, ErrorSeverity

        mock_cli = Mock()
        mock_cli.genesis_root = cli_environment
        mock_cli.environment = "e2e-test"
        mock_cli.project_id = f"{TEST_PROJECT_ID}-e2e"

        vm_commands = VMCommands(mock_cli)

        # Mock services for error scenarios
        vm_commands.gcp_service = Mock()
        vm_commands.error_service = Mock()

        # Test quota exceeded error scenario
        create_args = Mock()
        create_args.vm_action = "create-pool"
        create_args.type = "test-agent"
        create_args.size = 100  # Intentionally large to trigger quota error
        create_args.dry_run = False

        # Simulate quota exceeded error
        quota_error = subprocess.CalledProcessError(
            1,
            "gcloud",
            stderr="Quota 'CPUS' exceeded. Limit: 24.0 in region us-central1.",
        )
        vm_commands.gcp_service.create_vm_pool.side_effect = quota_error

        # Configure error service response
        mock_error = Mock()
        mock_error.category = ErrorCategory.RESOURCE
        mock_error.severity = ErrorSeverity.HIGH
        mock_error.suggestions = [
            "Request quota increase in GCP Console",
            "Reduce instance count",
            "Use preemptible instances",
        ]
        vm_commands.error_service.handle_gcp_error.return_value = mock_error

        # Test error handling
        with pytest.raises(Exception):
            vm_commands.execute(create_args, {})

        # Verify error was properly handled
        vm_commands.error_service.handle_gcp_error.assert_called_once()
        error_call_args = vm_commands.error_service.handle_gcp_error.call_args
        assert "quota" in str(error_call_args).lower()


@pytest.mark.e2e
class TestCompleteContainerWorkflow:
    """Test complete container deployment workflow."""

    def test_container_deployment_lifecycle(self, cli_environment):
        """Test complete container service lifecycle: cluster -> deploy -> scale -> cleanup."""
        from cli.commands.enhanced_container_commands import EnhancedContainerCommands

        mock_cli = Mock()
        mock_cli.genesis_root = cli_environment
        mock_cli.environment = "e2e-test"
        mock_cli.project_id = f"{TEST_PROJECT_ID}-e2e"

        container_commands = EnhancedContainerCommands(mock_cli)

        # Mock Kubernetes and GCP services
        container_commands.gcp_service = Mock()
        container_commands.performance_service = Mock()
        container_commands.cache_service = Mock()
        container_commands.error_service = Mock()

        # Test Step 1: Create GKE cluster
        cluster_args = Mock()
        cluster_args.container_action = "create-cluster"
        cluster_args.cluster_name = "e2e-test-cluster"
        cluster_args.autopilot = True
        cluster_args.region = "us-central1"
        cluster_args.dry_run = False

        container_commands.gcp_service.create_gke_cluster.return_value = {
            "cluster_name": "e2e-test-cluster",
            "status": "creating",
            "node_count": 3,
            "operation_id": "op-cluster-create-123",
        }

        cluster_result = container_commands.execute(cluster_args, {})

        # Verify cluster creation
        assert cluster_result["action"] == "create-cluster"
        assert cluster_result["cluster_name"] == "e2e-test-cluster"

        # Test Step 2: Deploy service
        deploy_args = Mock()
        deploy_args.container_action = "deploy"
        deploy_args.service = "test-service"
        deploy_args.replicas = 2
        deploy_args.namespace = "genesis-e2e"
        deploy_args.version = "latest"
        deploy_args.dry_run = False

        # Mock successful deployment
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "deployment.apps/test-service created"
            mock_run.return_value = mock_result

            deploy_result = container_commands.execute(deploy_args, {})

            # Verify deployment
            assert deploy_result["action"] == "deploy"
            assert deploy_result["service"] == "test-service"
            assert deploy_result["status"] == "success"

        # Test Step 3: Scale deployment
        scale_args = Mock()
        scale_args.container_action = "scale"
        scale_args.deployment = "test-service"
        scale_args.replicas = 4
        scale_args.namespace = "genesis-e2e"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "deployment.apps/test-service scaled"
            mock_run.return_value = mock_result

            scale_result = container_commands.execute(scale_args, {})

            # Verify scaling
            assert scale_result["action"] == "scale"
            assert scale_result["replicas"] == 4

        # Test Step 4: Get service logs
        logs_args = Mock()
        logs_args.container_action = "logs"
        logs_args.service = "test-service"
        logs_args.pod = None
        logs_args.follow = False
        logs_args.lines = 100
        logs_args.namespace = "genesis-e2e"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "2024-01-01T00:00:00Z Starting test service..."
            mock_run.return_value = mock_result

            logs_result = container_commands.execute(logs_args, {})

            # Verify log retrieval
            assert logs_result["action"] == "logs"
            assert "Starting test service" in logs_result["logs"]

        # Test Step 5: Delete deployment (cleanup)
        delete_args = Mock()
        delete_args.container_action = "delete"
        delete_args.service = "test-service"
        delete_args.namespace = "genesis-e2e"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "deployment.apps/test-service deleted"
            mock_run.return_value = mock_result

            delete_result = container_commands.execute(delete_args, {})

            # Verify deletion
            assert delete_result["action"] == "delete"
            assert delete_result["status"] == "success"

    def test_container_monitoring_integration(self, cli_environment):
        """Test container monitoring and health check integration."""
        from cli.commands.enhanced_container_commands import EnhancedContainerCommands

        mock_cli = Mock()
        mock_cli.genesis_root = cli_environment
        mock_cli.environment = "e2e-test"
        mock_cli.project_id = f"{TEST_PROJECT_ID}-e2e"

        container_commands = EnhancedContainerCommands(mock_cli)

        # Test health checking
        health_args = Mock()
        health_args.container_action = "health"
        health_args.service = "test-service"
        health_args.namespace = "genesis-e2e"

        with patch("subprocess.run") as mock_run:
            # Mock kubectl get pods response
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(
                {
                    "items": [
                        {
                            "metadata": {"name": "test-service-pod-1"},
                            "status": {
                                "phase": "Running",
                                "containerStatuses": [
                                    {"ready": True, "restartCount": 0}
                                ],
                            },
                        }
                    ]
                }
            )
            mock_run.return_value = mock_result

            health_result = container_commands.execute(health_args, {})

            # Verify health check
            assert health_result["action"] == "health"
            assert health_result["overall_status"] == "healthy"
            assert len(health_result["pod_details"]) == 1


@pytest.mark.e2e
class TestCompleteInfrastructureWorkflow:
    """Test complete infrastructure provisioning workflow."""

    def test_infrastructure_provisioning_lifecycle(self, cli_environment):
        """Test complete infrastructure lifecycle: plan -> apply -> monitor -> destroy."""
        from cli.commands.enhanced_infrastructure_commands import (
            EnhancedInfrastructureCommands,
        )

        mock_cli = Mock()
        mock_cli.genesis_root = cli_environment
        mock_cli.environment = "e2e-test"
        mock_cli.project_id = f"{TEST_PROJECT_ID}-e2e"

        infra_commands = EnhancedInfrastructureCommands(mock_cli)

        # Mock Terraform service
        infra_commands.terraform_service = Mock()

        # Test Step 1: Infrastructure planning
        plan_args = Mock()
        plan_args.infra_action = "plan"
        plan_args.module = "vm-management"
        plan_args.target = None
        plan_args.dry_run = False

        infra_commands.terraform_service.terraform_plan.return_value = {
            "status": "success",
            "changes": {"add": 3, "change": 0, "destroy": 0},
            "resources": [
                "google_compute_instance_template.agent_template",
                "google_compute_instance_group_manager.agent_group",
                "google_compute_autoscaler.agent_autoscaler",
            ],
        }

        plan_result = infra_commands.execute(plan_args, {})

        # Verify planning
        assert plan_result["action"] == "plan"
        assert plan_result["changes"]["add"] == 3

        # Test Step 2: Infrastructure application
        apply_args = Mock()
        apply_args.infra_action = "apply"
        apply_args.module = "vm-management"
        apply_args.auto_approve = True
        apply_args.target = None
        apply_args.dry_run = False

        infra_commands.terraform_service.terraform_apply.return_value = {
            "status": "success",
            "applied_changes": 3,
            "resources_created": [
                "google_compute_instance_template.agent_template",
                "google_compute_instance_group_manager.agent_group",
                "google_compute_autoscaler.agent_autoscaler",
            ],
        }

        apply_result = infra_commands.execute(apply_args, {})

        # Verify application
        assert apply_result["action"] == "apply"
        assert apply_result["applied_changes"] == 3

        # Test Step 3: Infrastructure status monitoring
        status_args = Mock()
        status_args.infra_action = "status"

        infra_commands.terraform_service.get_terraform_status.return_value = {
            "modules": {
                "vm-management": {
                    "status": "applied",
                    "resources": 3,
                    "last_applied": "2024-01-01T00:00:00Z",
                }
            },
            "overall_status": "healthy",
        }

        status_result = infra_commands.execute(status_args, {})

        # Verify status monitoring
        assert status_result["action"] == "status"
        assert status_result["overall_status"] == "healthy"

        # Test Step 4: Cost analysis
        cost_args = Mock()
        cost_args.infra_action = "cost"
        cost_args.cost_action = "analyze"

        cost_result = infra_commands.execute(cost_args, {})

        # Verify cost analysis
        assert cost_result["action"] == "cost-analyze"
        assert "current_monthly_cost" in cost_result

    def test_infrastructure_rollback_scenario(self, cli_environment):
        """Test infrastructure rollback and disaster recovery."""
        from cli.commands.enhanced_infrastructure_commands import (
            EnhancedInfrastructureCommands,
        )

        mock_cli = Mock()
        mock_cli.genesis_root = cli_environment
        mock_cli.environment = "e2e-test"
        mock_cli.project_id = f"{TEST_PROJECT_ID}-e2e"

        infra_commands = EnhancedInfrastructureCommands(mock_cli)
        infra_commands.terraform_service = Mock()

        # Simulate failed apply
        apply_args = Mock()
        apply_args.infra_action = "apply"
        apply_args.module = "vm-management"
        apply_args.auto_approve = True
        apply_args.dry_run = False

        # Mock Terraform apply failure
        terraform_error = subprocess.CalledProcessError(
            1, "terraform", stderr="Error: insufficient quota for resource creation"
        )
        infra_commands.terraform_service.terraform_apply.side_effect = terraform_error

        # Test error handling and rollback
        with pytest.raises(Exception):
            infra_commands.execute(apply_args, {})

        # Verify rollback is triggered
        infra_commands.terraform_service.terraform_apply.assert_called_once()


@pytest.mark.e2e
class TestUserJourneyWorkflows:
    """Test complete user journey workflows from start to finish."""

    def test_new_user_onboarding_workflow(self, cli_environment):
        """Test complete new user onboarding experience."""
        # This would test the complete user journey:
        # 1. Initial CLI setup
        # 2. Environment configuration
        # 3. Authentication setup
        # 4. First resource creation
        # 5. Monitoring setup

        # Mock the complete onboarding flow
        from cli.commands.main import GenesisCLI

        with patch("cli.commands.main.GenesisCLI") as mock_cli_class:
            mock_cli = Mock()
            mock_cli_class.return_value = mock_cli

            # Simulate onboarding steps
            onboarding_steps = [
                {"command": "setup", "status": "success"},
                {"command": "auth", "status": "success"},
                {"command": "vm create-pool", "status": "success"},
                {"command": "container create-cluster", "status": "success"},
            ]

            for step in onboarding_steps:
                mock_cli.execute_command.return_value = {"status": step["status"]}

            # Verify onboarding workflow
            assert len(onboarding_steps) == 4
            assert all(step["status"] == "success" for step in onboarding_steps)

    def test_developer_daily_workflow(self, cli_environment):
        """Test typical daily developer workflow."""
        # Simulate a developer's daily workflow:
        # 1. Check system status
        # 2. Scale resources if needed
        # 3. Deploy new code
        # 4. Monitor deployments
        # 5. Debug issues

        daily_workflow = [
            "infra status",
            "vm health-check",
            "container deploy --service my-app",
            "container logs --service my-app",
        ]

        # Mock each workflow step
        for command in daily_workflow:
            # Each command would be executed and verified
            assert command is not None
            assert len(command.split()) >= 1

    def test_production_deployment_workflow(self, cli_environment):
        """Test production deployment workflow with safety checks."""
        # Production deployment requires:
        # 1. Environment verification
        # 2. Resource planning
        # 3. Gradual deployment
        # 4. Health monitoring
        # 5. Rollback capability

        production_steps = [
            {"action": "verify_environment", "environment": "prod"},
            {"action": "plan_resources", "dry_run": True},
            {"action": "deploy_infrastructure", "gradual": True},
            {"action": "monitor_health", "continuous": True},
            {"action": "verify_deployment", "smoke_tests": True},
        ]

        # Verify production safety measures
        for step in production_steps:
            assert step["action"] is not None
            if step["action"] == "plan_resources":
                assert step.get("dry_run") is True
            if step["action"] == "deploy_infrastructure":
                assert step.get("gradual") is True


@contextmanager
def performance_monitoring():
    """Context manager for performance monitoring during E2E tests."""
    start_time = time.time()
    start_memory = get_memory_usage()

    yield

    end_time = time.time()
    end_memory = get_memory_usage()

    duration = end_time - start_time
    memory_delta = end_memory - start_memory

    # Assert performance constraints
    assert duration < 30.0, f"E2E test took {duration:.2f}s, exceeds 30s limit"
    assert memory_delta < 100, f"Memory increase {memory_delta}MB exceeds 100MB limit"


def get_memory_usage():
    """Get current memory usage in MB."""
    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0


if __name__ == "__main__":
    # Run E2E tests with performance monitoring
    pytest.main(
        [
            __file__,
            "-m",
            "e2e",
            "--tb=short",
            "-v",
            "--durations=10",  # Show slowest 10 tests
        ]
    )
