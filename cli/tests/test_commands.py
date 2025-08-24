"""
Command Tests
Unit and integration tests for Genesis CLI commands following CRAFT methodology.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace

from cli.commands.vm_commands import VMCommands
from cli.commands.enhanced_container_commands import EnhancedContainerCommands
from cli.commands.enhanced_infrastructure_commands import EnhancedInfrastructureCommands


class TestVMCommands:
    """Test VM management commands following CRAFT principles."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Mock CLI object
        self.mock_cli = Mock()
        self.mock_cli.genesis_root = self.temp_dir
        self.mock_cli.environment = "test"
        self.mock_cli.project_id = "test-project"

        # Create config directory
        config_dir = self.temp_dir / "config"
        config_dir.mkdir()
        (config_dir / "environments").mkdir()
        (config_dir / "environments" / "test.yaml").write_text(
            """
gcp:
  project_id: test-project
  region: us-central1
agents:
  types:
    backend-developer:
      machine_type: e2-standard-2
"""
        )
        (config_dir / "global.yaml").write_text("terraform:\n  region: us-central1")

        self.vm_commands = VMCommands(self.mock_cli)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_execute_invalid_action(self):
        """Test handling of invalid VM actions."""
        args = Namespace(vm_action="invalid_action", environment="test")
        config = {}

        with pytest.raises(Exception) as exc_info:
            self.vm_commands.execute(args, config)

        assert "Unknown VM action" in str(exc_info.value) or "INVALID_VM_ACTION" in str(
            exc_info.value
        )

    @patch("cli.services.gcp_service.subprocess.run")
    def test_create_pool_dry_run(self, mock_run):
        """Test VM pool creation in dry-run mode."""
        args = Namespace(
            vm_action="create-pool",
            type="backend-developer",
            size=2,
            machine_type=None,
            preemptible=False,
            zones=None,
            environment="test",
            project_id="test-project",
            dry_run=True,
        )
        config = {}

        result = self.vm_commands.execute(args, config)

        assert result["action"] == "create-pool"
        assert result["agent_type"] == "backend-developer"
        assert result["size"] == 2
        assert result["status"] == "dry-run"

    def test_create_pool_invalid_agent_type(self):
        """Test VM pool creation with invalid agent type."""
        args = Namespace(
            vm_action="create-pool",
            type="invalid-agent",
            size=1,
            environment="test",
            project_id="test-project",
        )
        config = {}

        with pytest.raises(Exception) as exc_info:
            self.vm_commands.execute(args, config)

        assert "Unknown agent type" in str(
            exc_info.value
        ) or "INVALID_AGENT_TYPE" in str(exc_info.value)

    @patch("cli.services.gcp_service.subprocess.run")
    def test_list_pools_success(self, mock_run):
        """Test successful VM pool listing."""
        # Mock gcloud response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"  # Empty list
        mock_run.return_value = mock_result

        args = Namespace(
            vm_action="list-pools", environment="test", project_id="test-project"
        )
        config = {}

        result = self.vm_commands.execute(args, config)

        assert isinstance(result, list)

    def test_health_check_no_resources(self):
        """Test health check with no specified resources."""
        args = Namespace(
            vm_action="health-check",
            environment="test",
            project_id="test-project",
            pool=None,
            instance=None,
        )
        config = {}

        result = self.vm_commands.execute(args, config)

        assert result["action"] == "health-check"
        assert "timestamp" in result
        assert "overall_status" in result

    def test_generate_pool_config(self):
        """Test pool configuration generation."""
        args = Namespace(
            type="backend-developer",
            size=3,
            machine_type=None,
            preemptible=None,
            zones=None,
        )

        config = self.vm_commands._generate_pool_config(args)

        assert config["agent_type"] == "backend-developer"
        assert config["pool_size"] == 3
        assert config["machine_type"] == "e2-standard-2"  # From agent config
        assert config["enable_autoscaling"] is True
        assert "labels" in config
        assert "startup_script" in config

    def test_performance_metrics(self):
        """Test performance metrics retrieval."""
        metrics = self.vm_commands.get_performance_metrics()

        assert "vm_operations" in metrics
        assert "cache_stats" in metrics
        assert "error_summary" in metrics


class TestContainerCommands:
    """Test container orchestration commands following CRAFT principles."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Mock CLI object
        self.mock_cli = Mock()
        self.mock_cli.genesis_root = self.temp_dir
        self.mock_cli.environment = "test"
        self.mock_cli.project_id = "test-project"

        # Create config and manifests directories
        config_dir = self.temp_dir / "config"
        config_dir.mkdir()
        (config_dir / "environments").mkdir()
        (config_dir / "environments" / "test.yaml").write_text(
            """
gcp:
  project_id: test-project
  region: us-central1
containers:
  cluster_name: test-cluster
  services:
    agent-cage:
      replicas: 2
      port: 8080
"""
        )
        (config_dir / "global.yaml").write_text("terraform:\n  region: us-central1")

        # Create modules directory structure
        modules_dir = self.temp_dir / "modules" / "container-orchestration"
        modules_dir.mkdir(parents=True)
        (modules_dir / "manifests").mkdir()
        (modules_dir / "templates").mkdir()

        self.container_commands = EnhancedContainerCommands(self.mock_cli)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_execute_invalid_action(self):
        """Test handling of invalid container actions."""
        args = Namespace(container_action="invalid_action", environment="test")
        config = {}

        with pytest.raises(Exception) as exc_info:
            self.container_commands.execute(args, config)

        assert "Unknown container action" in str(
            exc_info.value
        ) or "INVALID_CONTAINER_ACTION" in str(exc_info.value)

    def test_create_cluster_dry_run(self):
        """Test cluster creation in dry-run mode."""
        args = Namespace(
            container_action="create-cluster",
            cluster_name="test-cluster",
            autopilot=True,
            region=None,
            environment="test",
            project_id="test-project",
            dry_run=True,
        )
        config = {}

        result = self.container_commands.execute(args, config)

        assert result["action"] == "create-cluster"
        assert result["cluster_name"] == "test-cluster"
        assert result["status"] == "dry-run"

    @patch("cli.services.gcp_service.subprocess.run")
    def test_list_clusters_success(self, mock_run):
        """Test successful cluster listing."""
        # Mock gcloud response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"  # Empty list
        mock_run.return_value = mock_result

        args = Namespace(
            container_action="list-clusters",
            environment="test",
            project_id="test-project",
        )
        config = {}

        result = self.container_commands.execute(args, config)

        assert isinstance(result, list)

    def test_deploy_service_invalid_service(self):
        """Test service deployment with invalid service name."""
        args = Namespace(
            container_action="deploy",
            service="invalid-service",
            environment="test",
            project_id="test-project",
        )
        config = {}

        with pytest.raises(Exception) as exc_info:
            self.container_commands.execute(args, config)

        assert "Unsupported service" in str(
            exc_info.value
        ) or "UNSUPPORTED_SERVICE" in str(exc_info.value)

    def test_deploy_service_dry_run(self):
        """Test service deployment in dry-run mode."""
        args = Namespace(
            container_action="deploy",
            service="agent-cage",
            replicas=None,
            namespace=None,
            version=None,
            environment="test",
            project_id="test-project",
            dry_run=True,
        )
        config = {}

        result = self.container_commands.execute(args, config)

        assert result["action"] == "deploy"
        assert result["service"] == "agent-cage"
        assert result["status"] == "dry-run"

    @patch("cli.services.enhanced_container_commands.subprocess.run")
    def test_get_logs_success(self, mock_run):
        """Test successful log retrieval."""
        # Mock kubectl response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test log output"
        mock_run.return_value = mock_result

        args = Namespace(
            container_action="logs",
            service="agent-cage",
            pod=None,
            follow=False,
            lines=None,
            namespace=None,
            environment="test",
            project_id="test-project",
        )
        config = {}

        result = self.container_commands.execute(args, config)

        assert result["action"] == "logs"
        assert result["service"] == "agent-cage"
        assert result["logs"] == "test log output"
        assert result["status"] == "success"

    def test_generate_cluster_config(self):
        """Test cluster configuration generation."""
        args = Namespace(cluster_name="test-cluster", autopilot=True, region=None)

        config = self.container_commands._generate_cluster_config(args)

        assert config["cluster_name"] == "test-cluster"
        assert config["autopilot"] is True
        assert config["region"] == "us-central1"  # From config
        assert "labels" in config

    def test_generate_deployment_config(self):
        """Test deployment configuration generation."""
        args = Namespace(
            service="agent-cage", replicas=None, namespace=None, version=None
        )

        config = self.container_commands._generate_deployment_config(args)

        assert config["service_name"] == "agent-cage"
        assert config["replicas"] == 2  # From container config
        assert config["namespace"] == "genesis"  # Default
        assert "labels" in config
        assert "resources" in config
        assert "health_check" in config

    def test_generate_kubernetes_manifest(self):
        """Test Kubernetes manifest generation."""
        config = {
            "service_name": "agent-cage",
            "namespace": "test",
            "replicas": 2,
            "image": "test-image:latest",
            "port": 8080,
            "labels": {"app": "agent-cage"},
            "resources": {"requests": {"memory": "256Mi", "cpu": "100m"}},
            "health_check": {
                "path": "/health",
                "port": 8080,
                "initial_delay": 30,
                "period": 10,
            },
        }

        manifest = self.container_commands._generate_kubernetes_manifest(
            "agent-cage", config
        )

        assert "apiVersion: apps/v1" in manifest
        assert "kind: Deployment" in manifest
        assert "kind: Service" in manifest
        assert "agent-cage" in manifest
        assert "test-image:latest" in manifest


class TestInfrastructureCommands:
    """Test infrastructure management commands following CRAFT principles."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Mock CLI object
        self.mock_cli = Mock()
        self.mock_cli.genesis_root = self.temp_dir
        self.mock_cli.environment = "test"
        self.mock_cli.project_id = "test-project"

        # Create config and terraform directories
        config_dir = self.temp_dir / "config"
        config_dir.mkdir()
        (config_dir / "environments").mkdir()
        (config_dir / "environments" / "test.yaml").write_text(
            """
gcp:
  project_id: test-project
  region: us-central1
terraform:
  backend_bucket: test-terraform-state
"""
        )
        (config_dir / "global.yaml").write_text("terraform:\n  region: us-central1")

        # Create environments directory
        env_dir = self.temp_dir / "environments" / "test"
        env_dir.mkdir(parents=True)

        # Create modules directory
        modules_dir = self.temp_dir / "modules"
        modules_dir.mkdir()
        for module in [
            "vm-management",
            "container-orchestration",
            "networking",
            "security",
        ]:
            (modules_dir / module).mkdir()

        self.infra_commands = EnhancedInfrastructureCommands(self.mock_cli)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_execute_invalid_action(self):
        """Test handling of invalid infrastructure actions."""
        args = Namespace(infra_action="invalid_action", environment="test")
        config = {}

        with pytest.raises(Exception) as exc_info:
            self.infra_commands.execute(args, config)

        assert "Unknown infrastructure action" in str(
            exc_info.value
        ) or "INVALID_INFRA_ACTION" in str(exc_info.value)

    def test_terraform_plan_dry_run(self):
        """Test Terraform plan in dry-run mode."""
        args = Namespace(
            infra_action="plan",
            module="vm-management",
            target=None,
            environment="test",
            project_id="test-project",
            dry_run=True,
        )
        config = {}

        result = self.infra_commands.execute(args, config)

        assert result["action"] == "plan"
        assert result["module"] == "vm-management"
        assert result["status"] == "dry-run"

    def test_terraform_apply_dry_run(self):
        """Test Terraform apply in dry-run mode."""
        args = Namespace(
            infra_action="apply",
            module="vm-management",
            auto_approve=False,
            target=None,
            environment="test",
            project_id="test-project",
            dry_run=True,
        )
        config = {}

        result = self.infra_commands.execute(args, config)

        assert result["action"] == "apply"
        assert result["module"] == "vm-management"
        assert result["auto_approve"] is False
        assert result["status"] == "dry-run"

    def test_terraform_destroy_dry_run(self):
        """Test Terraform destroy in dry-run mode."""
        args = Namespace(
            infra_action="destroy",
            module="vm-management",
            auto_approve=False,
            target=None,
            environment="test",
            project_id="test-project",
            dry_run=True,
        )
        config = {}

        result = self.infra_commands.execute(args, config)

        assert result["action"] == "destroy"
        assert result["module"] == "vm-management"
        assert result["status"] == "dry-run"

    def test_infrastructure_status(self):
        """Test infrastructure status check."""
        args = Namespace(
            infra_action="status", environment="test", project_id="test-project"
        )
        config = {}

        result = self.infra_commands.execute(args, config)

        assert result["action"] == "status"
        assert "timestamp" in result
        assert "environment" in result
        assert "project_id" in result
        assert "overall_status" in result

    def test_cost_operations_estimate(self):
        """Test cost estimation."""
        args = Namespace(
            infra_action="cost",
            cost_action="estimate",
            environment="test",
            project_id="test-project",
        )
        config = {}

        result = self.infra_commands.execute(args, config)

        assert result["action"] == "cost-estimate"
        assert "estimated_monthly_cost" in result
        assert "breakdown" in result
        assert result["status"] == "completed"

    def test_cost_operations_analyze(self):
        """Test cost analysis."""
        args = Namespace(
            infra_action="cost",
            cost_action="analyze",
            environment="test",
            project_id="test-project",
        )
        config = {}

        result = self.infra_commands.execute(args, config)

        assert result["action"] == "cost-analyze"
        assert "current_monthly_cost" in result
        assert "top_resources" in result
        assert result["status"] == "completed"

    def test_cost_operations_optimize(self):
        """Test cost optimization."""
        args = Namespace(
            infra_action="cost",
            cost_action="optimize",
            environment="test",
            project_id="test-project",
        )
        config = {}

        result = self.infra_commands.execute(args, config)

        assert result["action"] == "cost-optimize"
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0
        assert "potential_savings" in result
        assert result["status"] == "completed"

    def test_cost_operations_invalid_action(self):
        """Test invalid cost action."""
        args = Namespace(
            infra_action="cost",
            cost_action="invalid",
            environment="test",
            project_id="test-project",
        )
        config = {}

        with pytest.raises(Exception) as exc_info:
            self.infra_commands.execute(args, config)

        assert "Unknown cost action" in str(
            exc_info.value
        ) or "INVALID_COST_ACTION" in str(exc_info.value)

    def test_cost_operations_missing_action(self):
        """Test missing cost action."""
        args = Namespace(
            infra_action="cost", environment="test", project_id="test-project"
        )
        # Don't set cost_action

        config = {}

        with pytest.raises(Exception) as exc_info:
            self.infra_commands.execute(args, config)

        assert "Cost action is required" in str(
            exc_info.value
        ) or "MISSING_COST_ACTION" in str(exc_info.value)

    def test_performance_metrics(self):
        """Test performance metrics retrieval."""
        metrics = self.infra_commands.get_performance_metrics()

        assert "infra_operations" in metrics
        assert "cache_stats" in metrics
        assert "error_summary" in metrics
        assert "terraform_cache" in metrics


class TestCommandIntegration:
    """Integration tests for command interactions."""

    def test_cross_command_data_flow(self):
        """Test data flow between different command types."""
        # This would test scenarios where VM commands affect container commands, etc.
        # For now, we'll test basic interaction patterns

        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Mock CLI object
            mock_cli = Mock()
            mock_cli.genesis_root = temp_dir
            mock_cli.environment = "test"
            mock_cli.project_id = "test-project"

            # Create minimal config structure
            config_dir = temp_dir / "config"
            config_dir.mkdir()
            (config_dir / "environments").mkdir()
            (config_dir / "environments" / "test.yaml").write_text(
                """
gcp:
  project_id: test-project
  region: us-central1
agents:
  types:
    backend-developer:
      machine_type: e2-standard-2
"""
            )
            (config_dir / "global.yaml").write_text("terraform:\n  region: us-central1")

            # Initialize commands
            vm_commands = VMCommands(mock_cli)

            # Test that services are properly initialized and can interact
            assert vm_commands.config_service is not None
            assert vm_commands.performance_service is not None
            assert vm_commands.cache_service is not None

            # Test configuration is properly loaded
            agent_config = vm_commands.agent_config
            assert "backend-developer" in agent_config["types"]

        finally:
            import shutil

            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
