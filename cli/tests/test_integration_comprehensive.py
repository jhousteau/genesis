"""
Comprehensive Integration Tests for Genesis CLI
Real integration testing with external services following VERIFY methodology.
"""

import pytest
import os
import time
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import json
import yaml

# Skip integration tests if not in integration environment
SKIP_INTEGRATION = not os.getenv("RUN_INTEGRATION_TESTS", False)
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "test-project")
GCP_SERVICE_ACCOUNT = os.getenv("GCP_SERVICE_ACCOUNT")

pytestmark = pytest.mark.skipif(
    SKIP_INTEGRATION, reason="Integration tests require environment setup"
)


@pytest.mark.integration
class TestGCPServiceIntegration:
    """Integration testing with real GCP services."""

    def setup_method(self):
        """Set up GCP integration testing environment."""
        self.project_id = GCP_PROJECT_ID
        self.service_account = GCP_SERVICE_ACCOUNT

        # Verify GCP authentication is available
        try:
            result = subprocess.run(
                ["gcloud", "auth", "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True,
            )
            auth_accounts = json.loads(result.stdout)
            assert len(auth_accounts) > 0, "No GCP authentication available"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("GCP CLI not available or not authenticated")

    def test_gcp_authentication_integration(self):
        """Test real GCP authentication flow."""
        from cli.services.gcp_service import GCPService
        from cli.services.auth_service import AuthService
        from cli.services.config_service import ConfigService
        from cli.services.cache_service import CacheService
        from cli.services.error_service import ErrorService

        # Initialize services
        config_service = Mock()
        config_service.project_id = self.project_id
        config_service.get_security_config.return_value = {
            "service_account": self.service_account,
            "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
        }

        auth_service = AuthService(config_service)
        cache_service = CacheService(config_service)
        error_service = ErrorService(config_service)

        gcp_service = GCPService(
            config_service, auth_service, cache_service, error_service
        )

        # Test authentication
        credentials = gcp_service.authenticate_gcp(self.project_id)

        # Verify authentication succeeded
        assert credentials is not None
        assert credentials.project_id == self.project_id
        assert credentials.token is not None
        assert len(credentials.token) > 10  # Valid token should be substantial

    def test_gcp_compute_integration(self):
        """Test integration with GCP Compute Engine API."""
        from cli.services.gcp_service import GCPService

        # Mock services for integration test
        config_service = Mock()
        config_service.project_id = self.project_id
        auth_service = Mock()
        cache_service = Mock()
        error_service = Mock()

        gcp_service = GCPService(
            config_service, auth_service, cache_service, error_service
        )

        # Test listing zones (read-only operation)
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "compute",
                    "zones",
                    "list",
                    f"--project={self.project_id}",
                    "--format=json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            zones = json.loads(result.stdout)
            assert len(zones) > 0, "No zones found in project"

            # Verify zone data structure
            first_zone = zones[0]
            assert "name" in first_zone
            assert "region" in first_zone
            assert "status" in first_zone

        except subprocess.CalledProcessError as e:
            pytest.fail(f"GCP Compute integration failed: {e.stderr}")

    @pytest.mark.slow
    def test_vm_lifecycle_integration(self):
        """Test complete VM lifecycle with real GCP resources."""
        # This is a more comprehensive test that would create and delete real resources
        # Disabled by default to avoid costs and resource creation
        pytest.skip("VM lifecycle test disabled to avoid resource creation")

        # Implementation would include:
        # 1. Create test VM instance
        # 2. Verify instance is running
        # 3. Test health checks
        # 4. Clean up instance

        """
        from cli.commands.vm_commands import VMCommands

        vm_commands = VMCommands(mock_cli)

        # Create test instance
        create_result = vm_commands.create_pool(
            agent_type="test-agent",
            pool_size=1,
            machine_type="e2-micro"  # Smallest instance for testing
        )

        assert create_result["status"] == "success"
        instance_name = create_result["instance_name"]

        try:
            # Wait for instance to be ready
            time.sleep(30)

            # Test health check
            health_result = vm_commands.health_check(instance=instance_name)
            assert health_result["status"] in ["healthy", "starting"]

        finally:
            # Cleanup
            vm_commands.delete_pool(pool_name=instance_name)
        """


@pytest.mark.integration
class TestTerraformIntegration:
    """Integration testing with Terraform operations."""

    def setup_method(self):
        """Set up Terraform integration testing environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.terraform_dir = self.temp_dir / "terraform"
        self.terraform_dir.mkdir()

        # Verify Terraform is available
        try:
            subprocess.run(["terraform", "version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Terraform not available")

    def teardown_method(self):
        """Clean up Terraform test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_terraform_initialization_integration(self):
        """Test Terraform initialization with real backend."""
        from cli.services.terraform_service import TerraformService

        # Create minimal Terraform configuration
        tf_config = """
terraform {
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

output "project_info" {
  value = {
    project_id = var.project_id
    region     = var.region
  }
}
"""

        (self.terraform_dir / "main.tf").write_text(tf_config)

        # Initialize Terraform service
        config_service = Mock()
        config_service.project_id = GCP_PROJECT_ID
        config_service.get_terraform_config.return_value = {
            "working_directory": str(self.terraform_dir),
            "backend_bucket": "test-terraform-state",
        }

        terraform_service = TerraformService(config_service)

        # Test initialization
        init_result = terraform_service.terraform_init(str(self.terraform_dir))

        # Verify initialization succeeded
        assert init_result["status"] == "success"
        assert (self.terraform_dir / ".terraform").exists()

    def test_terraform_plan_integration(self):
        """Test Terraform plan generation with real configuration."""
        from cli.services.terraform_service import TerraformService

        # Create test configuration (resource-free for safety)
        tf_config = """
variable "test_var" {
  description = "Test variable"
  type        = string
  default     = "test-value"
}

output "test_output" {
  value = var.test_var
}
"""

        (self.terraform_dir / "main.tf").write_text(tf_config)

        # Initialize Terraform
        subprocess.run(["terraform", "init"], cwd=self.terraform_dir, check=True)

        # Test plan generation
        config_service = Mock()
        terraform_service = TerraformService(config_service)

        plan_result = terraform_service.terraform_plan(
            working_directory=str(self.terraform_dir), var_file=None, targets=[]
        )

        # Verify plan generation succeeded
        assert plan_result["status"] == "success"
        assert "changes" in plan_result

        # Should show no changes for this simple configuration
        assert plan_result["changes"]["add"] == 0
        assert plan_result["changes"]["change"] == 0
        assert plan_result["changes"]["destroy"] == 0


@pytest.mark.integration
class TestKubernetesIntegration:
    """Integration testing with Kubernetes operations."""

    def setup_method(self):
        """Set up Kubernetes integration testing environment."""
        # Check if kubectl is available
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                pytest.skip("No Kubernetes cluster available")
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            pytest.skip("kubectl not available or cluster not accessible")

    def test_kubernetes_cluster_connectivity(self):
        """Test connection to Kubernetes cluster."""
        # Get cluster information
        result = subprocess.run(
            ["kubectl", "cluster-info", "--output=json"], capture_output=True, text=True
        )

        if result.returncode == 0:
            cluster_info = json.loads(result.stdout)
            assert "cluster" in cluster_info or len(result.stdout) > 0
        else:
            pytest.skip("Kubernetes cluster not accessible")

    def test_kubernetes_namespace_operations(self):
        """Test Kubernetes namespace operations."""
        from cli.commands.enhanced_container_commands import EnhancedContainerCommands

        # Create test namespace
        test_namespace = f"genesis-test-{int(time.time())}"

        try:
            # Create namespace
            subprocess.run(
                ["kubectl", "create", "namespace", test_namespace], check=True
            )

            # Verify namespace exists
            result = subprocess.run(
                ["kubectl", "get", "namespace", test_namespace, "-o", "json"],
                capture_output=True,
                text=True,
                check=True,
            )

            namespace_info = json.loads(result.stdout)
            assert namespace_info["metadata"]["name"] == test_namespace
            assert namespace_info["status"]["phase"] == "Active"

        finally:
            # Cleanup namespace
            try:
                subprocess.run(
                    ["kubectl", "delete", "namespace", test_namespace, "--timeout=60s"],
                    check=True,
                )
            except subprocess.CalledProcessError:
                pass  # Ignore cleanup errors

    @pytest.mark.slow
    def test_container_deployment_integration(self):
        """Test container deployment integration with Kubernetes."""
        # Skip actual deployment to avoid resource creation
        pytest.skip("Container deployment test disabled to avoid resource creation")

        # Implementation would include:
        # 1. Deploy test application
        # 2. Verify deployment status
        # 3. Test service accessibility
        # 4. Clean up resources


@pytest.mark.integration
class TestMultiEnvironmentIntegration:
    """Integration testing across multiple environments."""

    def setup_method(self):
        """Set up multi-environment testing."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir()
        (self.config_dir / "environments").mkdir()

        # Create environment configurations
        self._create_environment_configs()

    def _create_environment_configs(self):
        """Create test environment configurations."""
        environments = {
            "dev": {
                "gcp": {"project_id": f"{GCP_PROJECT_ID}-dev", "region": "us-central1"},
                "terraform": {"backend_bucket": "terraform-state-dev"},
            },
            "staging": {
                "gcp": {
                    "project_id": f"{GCP_PROJECT_ID}-staging",
                    "region": "us-east1",
                },
                "terraform": {"backend_bucket": "terraform-state-staging"},
            },
            "prod": {
                "gcp": {"project_id": f"{GCP_PROJECT_ID}-prod", "region": "us-west1"},
                "terraform": {"backend_bucket": "terraform-state-prod"},
            },
        }

        for env_name, config in environments.items():
            env_file = self.config_dir / "environments" / f"{env_name}.yaml"
            env_file.write_text(yaml.dump(config))

    def teardown_method(self):
        """Clean up multi-environment test."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_environment_switching_integration(self):
        """Test switching between different environments."""
        from cli.services.config_service import ConfigService

        config_service = ConfigService(self.temp_dir)

        # Test switching to dev environment
        config_service.update_environment("dev")
        dev_config = config_service.load_environment_config("dev")

        assert dev_config["gcp"]["project_id"] == f"{GCP_PROJECT_ID}-dev"
        assert dev_config["gcp"]["region"] == "us-central1"

        # Test switching to production environment
        config_service.update_environment("prod")
        prod_config = config_service.load_environment_config("prod")

        assert prod_config["gcp"]["project_id"] == f"{GCP_PROJECT_ID}-prod"
        assert prod_config["gcp"]["region"] == "us-west1"

    def test_cross_environment_isolation(self):
        """Test that environments are properly isolated."""
        from cli.services.config_service import ConfigService
        from cli.services.cache_service import CacheService

        config_service = ConfigService(self.temp_dir)

        # Test dev environment cache isolation
        config_service.update_environment("dev")
        dev_cache_service = CacheService(config_service)
        dev_cache_service.set("test_key", "dev_value")

        # Switch to staging environment
        config_service.update_environment("staging")
        staging_cache_service = CacheService(config_service)

        # Verify cache isolation
        staging_value = staging_cache_service.get("test_key", "default")
        assert (
            staging_value == "default"
        ), "Cache not properly isolated between environments"

        # Set staging value
        staging_cache_service.set("test_key", "staging_value")

        # Switch back to dev
        config_service.update_environment("dev")
        dev_cache_service_new = CacheService(config_service)

        # Verify dev value is still isolated
        dev_value = dev_cache_service_new.get("test_key", "default")
        assert dev_value == "dev_value", "Environment isolation broken"


@pytest.mark.integration
class TestEndToEndWorkflows:
    """End-to-end integration testing of complete workflows."""

    def setup_method(self):
        """Set up end-to-end testing environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_id = GCP_PROJECT_ID

        # Create complete CLI structure
        self._setup_complete_cli_environment()

    def _setup_complete_cli_environment(self):
        """Set up complete CLI environment for E2E testing."""
        config_dir = self.temp_dir / "config"
        config_dir.mkdir()
        (config_dir / "environments").mkdir()

        # Create comprehensive configuration
        (config_dir / "environments" / "test.yaml").write_text(
            f"""
gcp:
  project_id: {self.project_id}
  region: us-central1
  zone: us-central1-a
agents:
  types:
    backend-developer:
      machine_type: e2-standard-2
      disk_size_gb: 50
containers:
  cluster_name: test-cluster
  services:
    agent-cage:
      replicas: 2
      port: 8080
terraform:
  backend_bucket: test-terraform-state
"""
        )

    def teardown_method(self):
        """Clean up end-to-end test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_complete_infrastructure_workflow(self):
        """Test complete infrastructure provisioning workflow."""
        # This test demonstrates the complete flow but doesn't create real resources
        from cli.commands.enhanced_infrastructure_commands import (
            EnhancedInfrastructureCommands,
        )

        # Mock CLI for testing
        mock_cli = Mock()
        mock_cli.genesis_root = self.temp_dir
        mock_cli.environment = "test"
        mock_cli.project_id = self.project_id

        infra_commands = EnhancedInfrastructureCommands(mock_cli)

        # Mock the underlying services to avoid real resource creation
        infra_commands.terraform_service = Mock()
        infra_commands.terraform_service.terraform_plan.return_value = {
            "status": "success",
            "changes": {"add": 5, "change": 0, "destroy": 0},
        }

        # Test workflow steps
        workflows = [
            ("plan", {"module": "vm-management"}),
            ("plan", {"module": "container-orchestration"}),
            ("plan", {"module": "networking"}),
        ]

        results = []
        for action, params in workflows:
            args = Mock()
            args.infra_action = action
            args.module = params.get("module")
            args.dry_run = True

            result = infra_commands.execute(args, {})
            results.append(result)

        # Verify workflow execution
        assert len(results) == 3
        for result in results:
            assert result is not None

    def test_monitoring_and_alerting_integration(self):
        """Test monitoring and alerting system integration."""
        # Test that monitoring systems can be integrated
        from cli.services.performance_service import PerformanceService

        config_service = Mock()
        config_service.get_performance_config.return_value = {
            "target_response_time": 2.0,
            "monitoring": {"enabled": True},
        }

        performance_service = PerformanceService(config_service)

        # Simulate operations with monitoring
        operations = ["vm_create", "container_deploy", "infra_apply"]

        for operation in operations:
            with performance_service.time_operation(operation):
                time.sleep(0.1)  # Simulate work

        # Get performance summary
        summary = performance_service.get_performance_summary()

        # Verify monitoring data collection
        assert summary["total_operations"] == len(operations)
        assert summary["avg_response_time"] > 0
        assert "operations" in summary


if __name__ == "__main__":
    # Run integration tests with specific markers
    pytest.main([__file__, "-m", "integration", "--tb=short", "-v"])
