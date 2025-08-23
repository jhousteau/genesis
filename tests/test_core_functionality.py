#!/usr/bin/env python3
"""
Comprehensive core functionality tests for Universal Project Platform
Tests core modules and basic functionality with VERIFY methodology
"""

import os
import sys
from pathlib import Path

import pytest


@pytest.mark.unit
class TestCoreModules:
    """Test core module functionality"""

    def test_project_root_exists(self, project_root):
        """Test that project root is correctly identified"""
        assert project_root.exists()
        assert project_root.is_dir()
        assert project_root.name == "genesis"

    def test_bin_directory_exists(self, project_root):
        """Test that bin directory exists"""
        bin_dir = project_root / "bin"
        assert bin_dir.exists()
        assert bin_dir.is_dir()

    def test_bootstrap_script_exists(self, project_root):
        """Test that bootstrap script exists"""
        bootstrap_script = project_root / "bin" / "bootstrap"
        assert bootstrap_script.exists()
        assert bootstrap_script.is_file()

    def test_lib_python_directory_exists(self, project_root):
        """Test that lib/python directory exists"""
        lib_python = project_root / "lib" / "python"
        assert lib_python.exists()
        assert lib_python.is_dir()

    def test_setup_project_directory_exists(self, project_root):
        """Test that setup-project directory exists"""
        setup_project = project_root / "setup-project"
        assert setup_project.exists()
        assert setup_project.is_dir()


@pytest.mark.unit
class TestTestInfrastructure:
    """Test the testing infrastructure itself"""

    def test_temp_directory_fixture(self, temp_dir):
        """Test that temp directory fixture works"""
        assert temp_dir.exists()
        assert temp_dir.is_dir()

        # Test we can create files in it
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        assert test_file.exists()
        assert test_file.read_text() == "test content"

    def test_mock_registry_fixture(self, mock_registry):
        """Test that mock registry fixture works"""
        assert "global" in mock_registry
        assert "projects" in mock_registry
        assert "test-project" in mock_registry["projects"]

        project = mock_registry["projects"]["test-project"]
        assert project["type"] == "api"
        assert project["language"] == "python"
        assert project["cloud_provider"] == "gcp"

    def test_sample_project_structure(self, sample_project_structure):
        """Test that sample project structure fixture works"""
        assert sample_project_structure.exists()
        assert sample_project_structure.is_dir()

        # Check basic files
        assert (sample_project_structure / "README.md").exists()
        assert (sample_project_structure / "package.json").exists()
        assert (sample_project_structure / ".project-config.yaml").exists()
        assert (sample_project_structure / ".git").exists()

        # Check scripts
        scripts_dir = sample_project_structure / "scripts"
        assert scripts_dir.exists()
        assert (scripts_dir / "smart-commit.sh").exists()
        assert (scripts_dir / "deploy.sh").exists()
        assert (scripts_dir / "validate-compliance.sh").exists()


@pytest.mark.unit
class TestMockingInfrastructure:
    """Test the mocking infrastructure"""

    def test_mock_subprocess(self, mock_subprocess):
        """Test that subprocess mocking works"""
        import subprocess

        result = subprocess.run(["echo", "test"])
        assert result.returncode == 0
        assert result.stdout == "success"
        mock_subprocess.assert_called_once()

    def test_gcp_mock_services(self, gcp_mock_services):
        """Test that GCP services mocking works"""
        assert "storage" in gcp_mock_services
        assert "secrets" in gcp_mock_services
        assert "firestore" in gcp_mock_services
        assert "compute" in gcp_mock_services

        # Test storage client
        storage_client = gcp_mock_services["storage"]
        buckets = storage_client.list_buckets()
        assert buckets == []

    def test_gcp_helper(self, gcp_helper):
        """Test GCP helper utilities"""
        bucket = gcp_helper.create_mock_bucket("test-bucket")
        assert bucket.name == "test-bucket"
        assert bucket.exists() is True

        secret = gcp_helper.create_mock_secret("test-secret", "test-value")
        assert "test-secret" in secret.name


@pytest.mark.integration
class TestPathManagement:
    """Test Python path management for tests"""

    def test_python_path_includes_project_dirs(self):
        """Test that Python path includes necessary project directories"""
        project_root = Path(__file__).parent.parent

        expected_paths = [
            str(project_root),
            str(project_root / "lib" / "python"),
            str(project_root / "bin"),
            str(project_root / "setup-project"),
        ]

        for expected_path in expected_paths:
            # Check if path is in sys.path or a parent is
            path_found = any(
                expected_path in path
                or Path(path).resolve() == Path(expected_path).resolve()
                for path in sys.path
            )
            assert path_found, f"Expected path not found in sys.path: {expected_path}"

    def test_environment_variables_set(self):
        """Test that test environment variables are set"""
        assert os.getenv("TESTING") == "true"
        assert os.getenv("LOG_LEVEL") == "DEBUG"
        assert os.getenv("GOOGLE_CLOUD_PROJECT") == "test-project"


@pytest.mark.unit
class TestBasicFileOperations:
    """Test basic file operations that tests will need"""

    def test_create_yaml_file(self, temp_dir):
        """Test creating and reading YAML files"""
        import yaml

        test_data = {
            "version": "1.0.0",
            "type": "test",
            "config": {"enabled": True, "timeout": 30},
        }

        yaml_file = temp_dir / "test.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(test_data, f)

        assert yaml_file.exists()

        with open(yaml_file, "r") as f:
            loaded_data = yaml.safe_load(f)

        assert loaded_data == test_data

    def test_create_json_file(self, temp_dir):
        """Test creating and reading JSON files"""
        import json

        test_data = {
            "name": "test-project",
            "version": "1.0.0",
            "dependencies": ["fastapi", "uvicorn"],
        }

        json_file = temp_dir / "test.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f, indent=2)

        assert json_file.exists()

        with open(json_file, "r") as f:
            loaded_data = json.load(f)

        assert loaded_data == test_data


@pytest.mark.performance
class TestPerformanceUtilities:
    """Test performance testing utilities"""

    def test_performance_timer(self, performance_timer):
        """Test performance timer functionality"""
        import time

        performance_timer.start()
        time.sleep(0.1)  # Sleep for 100ms
        performance_timer.stop()

        elapsed = performance_timer.elapsed
        assert 0.05 < elapsed < 0.2  # Should be around 0.1 seconds, with some tolerance


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
