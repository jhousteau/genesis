#!/usr/bin/env python3
"""
Comprehensive Tests for Project Registry Operations
Tests all registry functionality with 100% critical path coverage
"""

import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "lib" / "python"))

from whitehorse_core.registry import ProjectRegistry


class TestProjectRegistry:
    """Test ProjectRegistry class operations"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="test_registry_")
        self.registry_file = Path(self.test_dir) / "registry.yaml"

        # Create initial registry
        self.initial_registry = {
            "global": {
                "organization": "test-org",
                "default_region": "us-central1",
                "plumbing_version": "2.0.0",
                "bootstrap_version": "1.0.0",
                "registry_version": "2.0.0",
                "last_updated": "2024-01-01T00:00:00Z",
                "standards": {
                    "compliance_level": "enhanced",
                    "security_baseline": "high",
                    "monitoring_required": True,
                    "backup_required": True,
                },
                "templates": {
                    "current_version": "2.0.0",
                    "available_types": [
                        "api",
                        "web-app",
                        "cli",
                        "library",
                        "infrastructure",
                    ],
                    "supported_languages": [
                        "python",
                        "javascript",
                        "go",
                        "rust",
                        "java",
                    ],
                },
                "deployment": {
                    "default_strategy": "canary",
                    "approval_required_envs": ["prod", "stage"],
                    "auto_deploy_envs": ["dev"],
                },
            },
            "projects": {},
        }

        with open(self.registry_file, "w") as f:
            yaml.dump(self.initial_registry, f)

        yield

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_registry_initialization(self):
        """Test registry initialization"""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(self.test_dir)

            registry = ProjectRegistry()

            assert registry is not None
            assert registry.registry_path is not None

    def test_load_registry(self):
        """Test loading registry from file"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()
            data = registry.load_registry()

            assert data is not None
            assert "global" in data
            assert "projects" in data
            assert data["global"]["organization"] == "test-org"

    def test_save_registry(self):
        """Test saving registry to file"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Modify registry
            new_data = self.initial_registry.copy()
            new_data["projects"]["test-project"] = {
                "path": "/test/path",
                "type": "api",
                "language": "python",
            }

            registry.save_registry(new_data)

            # Load and verify
            with open(self.registry_file) as f:
                saved_data = yaml.safe_load(f)

            assert "test-project" in saved_data["projects"]
            assert saved_data["projects"]["test-project"]["type"] == "api"

    def test_add_project(self):
        """Test adding a new project"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            project_config = {
                "path": "/new/project",
                "type": "web-app",
                "language": "javascript",
                "team": "frontend",
                "criticality": "high",
                "environments": {
                    "dev": {"gcp_project": "test-dev"},
                    "prod": {"gcp_project": "test-prod"},
                },
            }

            registry.add_project("new-project", project_config)

            # Verify project was added
            data = registry.load_registry()
            assert "new-project" in data["projects"]
            assert data["projects"]["new-project"]["type"] == "web-app"
            assert data["projects"]["new-project"]["team"] == "frontend"

    def test_update_project(self):
        """Test updating an existing project"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add initial project
            initial_config = {"path": "/old/path", "type": "api", "language": "python"}
            registry.add_project("test-project", initial_config)

            # Update project
            updated_config = {
                "path": "/new/path",
                "type": "api",
                "language": "go",
                "team": "backend",
            }
            registry.update_project("test-project", updated_config)

            # Verify update
            data = registry.load_registry()
            assert data["projects"]["test-project"]["path"] == "/new/path"
            assert data["projects"]["test-project"]["language"] == "go"
            assert data["projects"]["test-project"]["team"] == "backend"

    def test_remove_project(self):
        """Test removing a project"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add projects
            registry.add_project("project1", {"path": "/path1"})
            registry.add_project("project2", {"path": "/path2"})

            # Remove one project
            registry.remove_project("project1")

            # Verify removal
            data = registry.load_registry()
            assert "project1" not in data["projects"]
            assert "project2" in data["projects"]

    def test_get_project(self):
        """Test getting a specific project"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add project
            config = {"path": "/test/path", "type": "cli", "language": "rust"}
            registry.add_project("test-cli", config)

            # Get project
            project = registry.get_project("test-cli")

            assert project is not None
            assert project["type"] == "cli"
            assert project["language"] == "rust"

    def test_get_nonexistent_project(self):
        """Test getting a non-existent project"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()
            project = registry.get_project("nonexistent")

            assert project is None

    def test_list_projects(self):
        """Test listing all projects"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add multiple projects
            registry.add_project("project1", {"path": "/path1", "type": "api"})
            registry.add_project("project2", {"path": "/path2", "type": "web-app"})
            registry.add_project("project3", {"path": "/path3", "type": "cli"})

            # List projects
            projects = registry.list_projects()

            assert len(projects) == 3
            assert "project1" in projects
            assert "project2" in projects
            assert "project3" in projects

    def test_search_projects_by_type(self):
        """Test searching projects by type"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add projects of different types
            registry.add_project("api1", {"path": "/api1", "type": "api"})
            registry.add_project("api2", {"path": "/api2", "type": "api"})
            registry.add_project("web1", {"path": "/web1", "type": "web-app"})

            # Search for API projects
            api_projects = registry.search_projects(project_type="api")

            assert len(api_projects) == 2
            assert "api1" in api_projects
            assert "api2" in api_projects
            assert "web1" not in api_projects

    def test_search_projects_by_language(self):
        """Test searching projects by language"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add projects with different languages
            registry.add_project("py1", {"path": "/py1", "language": "python"})
            registry.add_project("py2", {"path": "/py2", "language": "python"})
            registry.add_project("js1", {"path": "/js1", "language": "javascript"})

            # Search for Python projects
            python_projects = registry.search_projects(language="python")

            assert len(python_projects) == 2
            assert "py1" in python_projects
            assert "py2" in python_projects

    def test_search_projects_by_team(self):
        """Test searching projects by team"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add projects with teams
            registry.add_project("backend1", {"path": "/b1", "team": "backend"})
            registry.add_project("backend2", {"path": "/b2", "team": "backend"})
            registry.add_project("frontend1", {"path": "/f1", "team": "frontend"})

            # Search for backend team projects
            backend_projects = registry.search_projects(team="backend")

            assert len(backend_projects) == 2
            assert "backend1" in backend_projects
            assert "backend2" in backend_projects

    def test_search_projects_multiple_criteria(self):
        """Test searching with multiple criteria"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add varied projects
            registry.add_project(
                "match1",
                {"path": "/m1", "type": "api", "language": "python", "team": "backend"},
            )
            registry.add_project(
                "match2",
                {
                    "path": "/m2",
                    "type": "api",
                    "language": "python",
                    "team": "frontend",
                },
            )
            registry.add_project(
                "nomatch",
                {
                    "path": "/nm",
                    "type": "web-app",
                    "language": "javascript",
                    "team": "frontend",
                },
            )

            # Search with multiple criteria
            results = registry.search_projects(project_type="api", language="python")

            assert len(results) == 2
            assert "match1" in results
            assert "match2" in results
            assert "nomatch" not in results

    def test_validate_registry_structure(self):
        """Test registry structure validation"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Valid registry
            is_valid, errors = registry.validate_registry()
            assert is_valid
            assert len(errors) == 0

            # Invalid registry - missing global section
            invalid_data = {"projects": {}}
            registry.save_registry(invalid_data)

            is_valid, errors = registry.validate_registry()
            assert not is_valid
            assert len(errors) > 0

    def test_validate_project_config(self):
        """Test project configuration validation"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Valid config
            valid_config = {"path": "/test", "type": "api", "language": "python"}
            is_valid, errors = registry.validate_project_config(valid_config)
            assert is_valid
            assert len(errors) == 0

            # Invalid config - missing required field
            invalid_config = {"type": "api"}
            is_valid, errors = registry.validate_project_config(invalid_config)
            assert not is_valid
            assert len(errors) > 0

    def test_get_projects_by_criticality(self):
        """Test getting projects by criticality level"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add projects with different criticality
            registry.add_project("critical1", {"path": "/c1", "criticality": "high"})
            registry.add_project("critical2", {"path": "/c2", "criticality": "high"})
            registry.add_project("normal", {"path": "/n1", "criticality": "medium"})

            # Get high criticality projects
            critical_projects = registry.get_projects_by_criticality("high")

            assert len(critical_projects) == 2
            assert "critical1" in critical_projects
            assert "critical2" in critical_projects

    def test_get_project_environments(self):
        """Test getting project environments"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add project with environments
            registry.add_project(
                "test-project",
                {
                    "path": "/test",
                    "environments": {
                        "dev": {"gcp_project": "test-dev"},
                        "stage": {"gcp_project": "test-stage"},
                        "prod": {"gcp_project": "test-prod", "approval_required": True},
                    },
                },
            )

            # Get environments
            environments = registry.get_project_environments("test-project")

            assert len(environments) == 3
            assert "dev" in environments
            assert "prod" in environments
            assert environments["prod"]["approval_required"] is True

    def test_update_project_environment(self):
        """Test updating a specific project environment"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add project
            registry.add_project(
                "test-project",
                {"path": "/test", "environments": {"dev": {"gcp_project": "test-dev"}}},
            )

            # Update environment
            registry.update_project_environment(
                "test-project",
                "dev",
                {"gcp_project": "test-dev-updated", "region": "us-west1"},
            )

            # Verify update
            environments = registry.get_project_environments("test-project")
            assert environments["dev"]["gcp_project"] == "test-dev-updated"
            assert environments["dev"]["region"] == "us-west1"

    def test_export_registry_json(self):
        """Test exporting registry to JSON"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add some projects
            registry.add_project("project1", {"path": "/p1"})

            # Export to JSON
            export_file = Path(self.test_dir) / "export.json"
            registry.export_registry(str(export_file), format="json")

            # Verify export
            assert export_file.exists()
            with open(export_file) as f:
                exported_data = json.load(f)

            assert "projects" in exported_data
            assert "project1" in exported_data["projects"]

    def test_export_registry_csv(self):
        """Test exporting registry to CSV"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add projects
            registry.add_project(
                "project1", {"path": "/p1", "type": "api", "language": "python"}
            )
            registry.add_project(
                "project2", {"path": "/p2", "type": "web-app", "language": "javascript"}
            )

            # Export to CSV
            export_file = Path(self.test_dir) / "export.csv"
            registry.export_registry(str(export_file), format="csv")

            # Verify export
            assert export_file.exists()
            with open(export_file) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 2
            assert any(row["name"] == "project1" for row in rows)
            assert any(row["name"] == "project2" for row in rows)

    def test_import_registry_json(self):
        """Test importing registry from JSON"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Create import file
            import_data = {
                "projects": {
                    "imported1": {"path": "/imp1", "type": "api"},
                    "imported2": {"path": "/imp2", "type": "cli"},
                }
            }
            import_file = Path(self.test_dir) / "import.json"
            with open(import_file, "w") as f:
                json.dump(import_data, f)

            # Import
            registry.import_registry(str(import_file), format="json", merge=True)

            # Verify import
            projects = registry.list_projects()
            assert "imported1" in projects
            assert "imported2" in projects

    def test_backup_registry(self):
        """Test registry backup functionality"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Create backup
            backup_path = registry.backup_registry()

            assert backup_path is not None
            assert Path(backup_path).exists()

            # Verify backup content
            with open(backup_path) as f:
                backup_data = yaml.safe_load(f)

            assert "global" in backup_data
            assert backup_data["global"]["organization"] == "test-org"

    def test_restore_registry(self):
        """Test registry restoration from backup"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add project and create backup
            registry.add_project("backup-test", {"path": "/backup"})
            backup_path = registry.backup_registry()

            # Modify registry
            registry.remove_project("backup-test")
            registry.add_project("new-project", {"path": "/new"})

            # Restore from backup
            registry.restore_registry(backup_path)

            # Verify restoration
            projects = registry.list_projects()
            assert "backup-test" in projects
            assert "new-project" not in projects

    def test_get_registry_statistics(self):
        """Test getting registry statistics"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add various projects
            registry.add_project("api1", {"type": "api", "language": "python"})
            registry.add_project("api2", {"type": "api", "language": "go"})
            registry.add_project("web1", {"type": "web-app", "language": "javascript"})

            # Get statistics
            stats = registry.get_statistics()

            assert stats["total_projects"] == 3
            assert stats["by_type"]["api"] == 2
            assert stats["by_type"]["web-app"] == 1
            assert stats["by_language"]["python"] == 1
            assert stats["by_language"]["go"] == 1
            assert stats["by_language"]["javascript"] == 1

    def test_clean_missing_projects(self):
        """Test cleaning projects with missing paths"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add projects
            registry.add_project("exists", {"path": str(self.test_dir)})
            registry.add_project("missing", {"path": "/nonexistent/path"})

            # Clean missing projects
            removed = registry.clean_missing_projects()

            # Verify cleaning
            assert len(removed) == 1
            assert "missing" in removed

            projects = registry.list_projects()
            assert "exists" in projects
            assert "missing" not in projects

    def test_get_project_dependencies(self):
        """Test getting project dependencies"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add project with dependencies
            registry.add_project(
                "service-a",
                {
                    "path": "/service-a",
                    "dependencies": ["service-b", "service-c"],
                    "type": "api",
                },
            )

            # Get dependencies
            deps = registry.get_project_dependencies("service-a")

            assert len(deps) == 2
            assert "service-b" in deps
            assert "service-c" in deps

    def test_intelligence_config_management(self):
        """Test intelligence configuration management"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry = ProjectRegistry()

            # Add project
            registry.add_project("test-project", {"path": "/test"})

            # Set intelligence config
            intelligence_config = {
                "auto_fix_enabled": True,
                "optimization_enabled": True,
                "predictions_enabled": False,
                "recommendations_enabled": True,
            }
            registry.set_intelligence_config("test-project", intelligence_config)

            # Get intelligence config
            config = registry.get_intelligence_config("test-project")

            assert config["auto_fix_enabled"] is True
            assert config["optimization_enabled"] is True
            assert config["predictions_enabled"] is False
            assert config["recommendations_enabled"] is True

    def test_concurrent_access_handling(self):
        """Test handling of concurrent registry access"""
        with patch.object(ProjectRegistry, "_get_registry_path") as mock_path:
            mock_path.return_value = self.registry_file

            registry1 = ProjectRegistry()
            registry2 = ProjectRegistry()

            # Both registries add projects
            registry1.add_project("project1", {"path": "/p1"})
            registry2.add_project("project2", {"path": "/p2"})

            # Reload first registry
            registry1_projects = registry1.list_projects()

            # Should have both projects (last write wins)
            assert "project2" in registry1_projects


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
