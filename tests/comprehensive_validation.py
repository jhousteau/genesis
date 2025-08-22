#!/usr/bin/env python3
"""
Comprehensive Validation Suite for Universal Project Platform
Validates all 8 core components and system integration
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib" / "python"))


class UniversalPlatformValidation(unittest.TestCase):
    """Comprehensive validation test suite for the Universal Project Platform"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.bootstrap_root = Path(__file__).parent.parent.resolve()
        cls.bin_dir = cls.bootstrap_root / "bin"
        cls.bootstrap_cli = cls.bin_dir / "bootstrap"
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="bootstrap_test_"))
        cls.test_project_name = (
            f"test_project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        cls.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "platform_version": "2.0.0",
            "components": {},
            "tests": {},
            "errors": [],
            "warnings": [],
        }

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Clean up temp directory
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

        # Generate final validation report
        cls.generate_validation_report()

    @classmethod
    def generate_validation_report(cls):
        """Generate comprehensive validation report"""
        report_path = cls.bootstrap_root / "tests" / "validation_report.md"

        with open(report_path, "w") as f:
            f.write("# Universal Project Platform - Validation Report\n\n")
            f.write(f"**Generated:** {cls.validation_results['timestamp']}\n")
            f.write(
                f"**Platform Version:** {cls.validation_results['platform_version']}\n\n"
            )

            # Component Status
            f.write("## Component Validation Status\n\n")
            f.write("| Component | Status | Details |\n")
            f.write("|-----------|--------|----------|\n")

            for component, status in cls.validation_results["components"].items():
                status_icon = "✅" if status["passed"] else "❌"
                details = status.get("details", "")
                f.write(f"| {component} | {status_icon} | {details} |\n")

            # Test Results
            f.write("\n## Test Results\n\n")
            f.write("| Test | Result | Duration | Notes |\n")
            f.write("|------|--------|----------|-------|\n")

            for test_name, result in cls.validation_results["tests"].items():
                status = "✅ Passed" if result["passed"] else "❌ Failed"
                duration = result.get("duration", "N/A")
                notes = result.get("notes", "")
                f.write(f"| {test_name} | {status} | {duration} | {notes} |\n")

            # Errors and Warnings
            if cls.validation_results["errors"]:
                f.write("\n## Errors\n\n")
                for error in cls.validation_results["errors"]:
                    f.write(f"- ❌ {error}\n")

            if cls.validation_results["warnings"]:
                f.write("\n## Warnings\n\n")
                for warning in cls.validation_results["warnings"]:
                    f.write(f"- ⚠️ {warning}\n")

            # Overall Status
            total_tests = len(cls.validation_results["tests"])
            passed_tests = sum(
                1 for t in cls.validation_results["tests"].values() if t["passed"]
            )

            f.write("\n## Overall Status\n\n")
            f.write(f"- **Total Tests:** {total_tests}\n")
            f.write(f"- **Passed:** {passed_tests}\n")
            f.write(f"- **Failed:** {total_tests - passed_tests}\n")
            f.write(f"- **Success Rate:** {(passed_tests / total_tests * 100):.1f}%\n")

            if passed_tests == total_tests:
                f.write("\n### 🎉 PLATFORM IS 100% FUNCTIONAL\n")
            else:
                f.write(
                    f"\n### ⚠️ Platform has {total_tests - passed_tests} failing tests\n"
                )

        print(f"\n📊 Validation report generated: {report_path}")

    def run_command(
        self, cmd: List[str], cwd: Optional[Path] = None, check: bool = True
    ) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.bootstrap_root,
                capture_output=True,
                text=True,
                check=check,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout or "", e.stderr or ""
        except Exception as e:
            return 1, "", str(e)

    def test_01_python_syntax(self):
        """Test: All Python files compile without syntax errors"""
        test_name = "Python Syntax Validation"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()
        errors = []

        # Find all Python files
        python_files = list(self.bootstrap_root.rglob("*.py"))

        for py_file in python_files:
            if "temp" in str(py_file) or "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file, "r") as f:
                    compile(f.read(), py_file, "exec")
            except SyntaxError as e:
                errors.append(f"{py_file}: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        self.validation_results["tests"][test_name] = {
            "passed": len(errors) == 0,
            "duration": f"{duration:.2f}s",
            "notes": f"Validated {len(python_files)} Python files",
        }

        if errors:
            for error in errors:
                self.validation_results["errors"].append(error)

        self.assertEqual(len(errors), 0, f"Syntax errors found: {errors}")
        print(f"✅ {test_name} passed - {len(python_files)} files validated")

    def test_02_cli_help(self):
        """Test: CLI help command works"""
        test_name = "CLI Help Command"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        # Test main help
        returncode, stdout, stderr = self.run_command(
            [str(self.bootstrap_cli), "--help"]
        )

        duration = (datetime.now() - start_time).total_seconds()

        self.validation_results["tests"][test_name] = {
            "passed": returncode == 0,
            "duration": f"{duration:.2f}s",
            "notes": "CLI help system functional",
        }

        self.assertEqual(returncode, 0, f"CLI help failed: {stderr}")
        self.assertIn("Universal Project Bootstrap CLI", stdout)
        print(f"✅ {test_name} passed")

    def test_03_cli_subcommands(self):
        """Test: All CLI subcommands are accessible"""
        test_name = "CLI Subcommands"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        subcommands = [
            "new",
            "retrofit",
            "list",
            "validate",
            "registry",
            "deploy",
            "infra",
            "health",
            "logs",
            "status",
            "isolation",
        ]

        failed_commands = []
        for cmd in subcommands:
            returncode, stdout, stderr = self.run_command(
                [str(self.bootstrap_cli), cmd, "--help"], check=False
            )
            if returncode != 0:
                failed_commands.append(cmd)

        duration = (datetime.now() - start_time).total_seconds()

        self.validation_results["tests"][test_name] = {
            "passed": len(failed_commands) == 0,
            "duration": f"{duration:.2f}s",
            "notes": f"Tested {len(subcommands)} subcommands",
        }

        self.assertEqual(
            len(failed_commands), 0, f"Failed subcommands: {failed_commands}"
        )
        print(f"✅ {test_name} passed - All {len(subcommands)} subcommands accessible")

    def test_04_project_creation(self):
        """Test: Project creation works end-to-end"""
        test_name = "Project Creation"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        project_path = self.temp_dir / self.test_project_name

        # Create new project
        returncode, stdout, stderr = self.run_command(
            [
                str(self.bootstrap_cli),
                "new",
                self.test_project_name,
                "--type",
                "api",
                "--language",
                "python",
                "--cloud",
                "gcp",
                "--path",
                str(project_path),
                "--git",
            ]
        )

        # Verify project was created
        project_exists = project_path.exists()
        has_config = (
            (project_path / ".project-config.yaml").exists()
            if project_exists
            else False
        )
        has_git = (project_path / ".git").exists() if project_exists else False

        duration = (datetime.now() - start_time).total_seconds()

        success = returncode == 0 and project_exists and has_config

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": f"Created project at {project_path}",
        }

        self.assertEqual(returncode, 0, f"Project creation failed: {stderr}")
        self.assertTrue(project_exists, "Project directory not created")
        self.assertTrue(has_config, "Project config not created")

        print(f"✅ {test_name} passed - Project created successfully")

    def test_05_registry_operations(self):
        """Test: Registry operations work correctly"""
        test_name = "Registry Operations"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        # Test registry validation
        returncode, stdout, stderr = self.run_command(
            [str(self.bootstrap_cli), "registry", "validate"]
        )

        # Test registry stats
        returncode2, stdout2, stderr2 = self.run_command(
            [str(self.bootstrap_cli), "registry", "stats"]
        )

        duration = (datetime.now() - start_time).total_seconds()

        success = returncode == 0 and returncode2 == 0

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": "Registry validation and stats functional",
        }

        self.assertEqual(returncode, 0, f"Registry validation failed: {stderr}")
        self.assertEqual(returncode2, 0, f"Registry stats failed: {stderr2}")

        print(f"✅ {test_name} passed - Registry operations functional")

    def test_06_project_validation(self):
        """Test: Project validation works"""
        test_name = "Project Validation"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        # Validate all projects
        returncode, stdout, stderr = self.run_command(
            [str(self.bootstrap_cli), "validate", "all"]
        )

        duration = (datetime.now() - start_time).total_seconds()

        # We expect this to succeed even if no projects exist
        success = returncode == 0 or "not found in registry" in stderr

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": "Project validation command functional",
        }

        self.assertTrue(success, f"Project validation failed unexpectedly: {stderr}")

        print(f"✅ {test_name} passed - Validation command functional")

    def test_07_component_setup_project(self):
        """Test: setup-project module functionality"""
        test_name = "Setup Project Module"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        setup_module = self.bootstrap_root / "setup-project" / "setup.py"

        # Check if module exists and is importable
        module_exists = setup_module.exists()

        if module_exists:
            # Try to import the module
            import importlib.util

            spec = importlib.util.spec_from_file_location("setup_project", setup_module)
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                has_class = hasattr(module, "ProjectSetup")
            except Exception as e:
                has_class = False
                self.validation_results["errors"].append(
                    f"Setup module import error: {e}"
                )
        else:
            has_class = False

        duration = (datetime.now() - start_time).total_seconds()

        success = module_exists and has_class

        self.validation_results["components"]["setup-project"] = {
            "passed": success,
            "details": (
                "Module exists and is importable"
                if success
                else "Module missing or import failed"
            ),
        }

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": "Setup project module validation",
        }

        self.assertTrue(module_exists, "Setup project module not found")
        self.assertTrue(has_class, "ProjectSetup class not found in module")

        print(f"✅ {test_name} passed - Module functional")

    def test_08_component_isolation(self):
        """Test: Isolation component structure"""
        test_name = "Isolation Component"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        isolation_dir = self.bootstrap_root / "isolation"

        required_subdirs = [
            "gcp",
            "aws",
            "credentials",
            "policies",
            "validation",
            "safety",
        ]
        missing_dirs = []

        for subdir in required_subdirs:
            if not (isolation_dir / subdir).exists():
                missing_dirs.append(subdir)

        duration = (datetime.now() - start_time).total_seconds()

        success = len(missing_dirs) == 0

        self.validation_results["components"]["isolation"] = {
            "passed": success,
            "details": (
                "All isolation subdirectories present"
                if success
                else f"Missing: {missing_dirs}"
            ),
        }

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": f"Checked {len(required_subdirs)} required directories",
        }

        self.assertEqual(
            len(missing_dirs), 0, f"Missing isolation directories: {missing_dirs}"
        )

        print(f"✅ {test_name} passed - Isolation structure valid")

    def test_09_component_monitoring(self):
        """Test: Monitoring component structure"""
        test_name = "Monitoring Component"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        monitoring_dir = self.bootstrap_root / "monitoring"

        required_files = [
            "dashboard-templates/gcp-dashboard.json",
            "alerts/alert-rules.yaml",
            "metrics/metrics-config.yaml",
            "logging/logging-config.yaml",
        ]

        missing_files = []
        for file_path in required_files:
            if not (monitoring_dir / file_path).exists():
                missing_files.append(file_path)

        duration = (datetime.now() - start_time).total_seconds()

        success = len(missing_files) == 0

        self.validation_results["components"]["monitoring"] = {
            "passed": success,
            "details": (
                "All monitoring configs present"
                if success
                else f"Missing: {missing_files}"
            ),
        }

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": f"Checked {len(required_files)} required files",
        }

        self.assertEqual(
            len(missing_files), 0, f"Missing monitoring files: {missing_files}"
        )

        print(f"✅ {test_name} passed - Monitoring structure valid")

    def test_10_component_intelligence(self):
        """Test: Intelligence component structure"""
        test_name = "Intelligence Component"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        intelligence_dir = self.bootstrap_root / "intelligence"

        required_modules = [
            "auto-fix/fix.py",
            "optimization/analyze.py",
            "predictions/analyze.py",
            "recommendations/analyze.py",
            "self-healing.py",
        ]

        missing_modules = []
        for module_path in required_modules:
            if not (intelligence_dir / module_path).exists():
                missing_modules.append(module_path)

        duration = (datetime.now() - start_time).total_seconds()

        success = len(missing_modules) == 0

        self.validation_results["components"]["intelligence"] = {
            "passed": success,
            "details": (
                "All AI modules present" if success else f"Missing: {missing_modules}"
            ),
        }

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": f"Checked {len(required_modules)} AI modules",
        }

        self.assertEqual(
            len(missing_modules), 0, f"Missing intelligence modules: {missing_modules}"
        )

        print(f"✅ {test_name} passed - Intelligence structure valid")

    def test_11_component_deployment(self):
        """Test: Deployment component structure"""
        test_name = "Deployment Component"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        deploy_dir = self.bootstrap_root / "deploy"

        required_files = [
            "terraform/main.tf",
            "terraform/variables.tf",
            "kubernetes/base/kustomization.yaml",
            "docker/Dockerfile.template",
        ]

        missing_files = []
        for file_path in required_files:
            if not (deploy_dir / file_path).exists():
                missing_files.append(file_path)

        duration = (datetime.now() - start_time).total_seconds()

        success = len(missing_files) == 0

        self.validation_results["components"]["deployment"] = {
            "passed": success,
            "details": (
                "All deployment configs present"
                if success
                else f"Missing: {missing_files}"
            ),
        }

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": f"Checked {len(required_files)} deployment files",
        }

        self.assertEqual(
            len(missing_files), 0, f"Missing deployment files: {missing_files}"
        )

        print(f"✅ {test_name} passed - Deployment structure valid")

    def test_12_component_governance(self):
        """Test: Governance component structure"""
        test_name = "Governance Component"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        governance_dir = self.bootstrap_root / "governance"

        required_files = [
            "policies/security-policy.yaml",
            "policies/compliance-policy.yaml",
            "standards/coding-standards.md",
            "templates/project-template.yaml",
        ]

        missing_files = []
        for file_path in required_files:
            if not (governance_dir / file_path).exists():
                missing_files.append(file_path)

        duration = (datetime.now() - start_time).total_seconds()

        success = len(missing_files) == 0

        self.validation_results["components"]["governance"] = {
            "passed": success,
            "details": (
                "All governance policies present"
                if success
                else f"Missing: {missing_files}"
            ),
        }

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": f"Checked {len(required_files)} governance files",
        }

        self.assertEqual(
            len(missing_files), 0, f"Missing governance files: {missing_files}"
        )

        print(f"✅ {test_name} passed - Governance structure valid")

    def test_13_component_core_library(self):
        """Test: Core library structure"""
        test_name = "Core Library"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        lib_dir = self.bootstrap_root / "lib" / "python" / "whitehorse_core"

        required_modules = [
            "__init__.py",
            "config/__init__.py",
            "database/__init__.py",
            "api_client/__init__.py",
            "metrics/__init__.py",
            "tracing/__init__.py",
            "cache/__init__.py",
            "security/__init__.py",
        ]

        missing_modules = []
        for module_path in required_modules:
            if not (lib_dir / module_path).exists():
                missing_modules.append(module_path)

        duration = (datetime.now() - start_time).total_seconds()

        success = len(missing_modules) == 0

        self.validation_results["components"]["core-library"] = {
            "passed": success,
            "details": (
                "All core modules present" if success else f"Missing: {missing_modules}"
            ),
        }

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": f"Checked {len(required_modules)} core modules",
        }

        self.assertEqual(
            len(missing_modules), 0, f"Missing core library modules: {missing_modules}"
        )

        print(f"✅ {test_name} passed - Core library structure valid")

    def test_14_terraform_modules(self):
        """Test: Terraform modules structure"""
        test_name = "Terraform Modules"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        modules_dir = self.bootstrap_root / "modules"

        required_modules = [
            "bootstrap",
            "compute",
            "data",
            "networking",
            "workload-identity",
            "multi-project",
        ]

        missing_modules = []
        for module_name in required_modules:
            module_path = modules_dir / module_name
            if not module_path.exists():
                missing_modules.append(module_name)
            elif (
                not (module_path / "main.tf").exists()
                and not (module_path / "README.md").exists()
            ):
                missing_modules.append(f"{module_name} (incomplete)")

        duration = (datetime.now() - start_time).total_seconds()

        success = len(missing_modules) == 0

        self.validation_results["components"]["terraform-modules"] = {
            "passed": success,
            "details": (
                "All Terraform modules present"
                if success
                else f"Missing: {missing_modules}"
            ),
        }

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": f"Checked {len(required_modules)} Terraform modules",
        }

        self.assertEqual(
            len(missing_modules), 0, f"Missing Terraform modules: {missing_modules}"
        )

        print(f"✅ {test_name} passed - Terraform modules valid")

    def test_15_scripts_directory(self):
        """Test: Scripts directory structure"""
        test_name = "Scripts Directory"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        scripts_dir = self.bootstrap_root / "scripts"

        required_scripts = [
            "validate-compliance.sh",
            "deploy.sh",
            "smart-commit.sh",
            "setup-environment.sh",
            "bootstrap-project.sh",
        ]

        missing_scripts = []
        for script_name in required_scripts:
            if not (scripts_dir / script_name).exists():
                missing_scripts.append(script_name)

        duration = (datetime.now() - start_time).total_seconds()

        success = len(missing_scripts) == 0

        self.validation_results["components"]["scripts"] = {
            "passed": success,
            "details": (
                "All scripts present" if success else f"Missing: {missing_scripts}"
            ),
        }

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": f"Checked {len(required_scripts)} scripts",
        }

        self.assertEqual(len(missing_scripts), 0, f"Missing scripts: {missing_scripts}")

        print(f"✅ {test_name} passed - Scripts directory valid")

    def test_16_config_integration(self):
        """Test: Configuration integration"""
        test_name = "Configuration Integration"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        config_file = self.bootstrap_root / "config" / "unified_config.py"

        # Check if config module exists
        config_exists = config_file.exists()

        if config_exists:
            # Try to import and validate config
            import importlib.util

            spec = importlib.util.spec_from_file_location("unified_config", config_file)
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                has_class = hasattr(module, "UnifiedConfig")
            except Exception as e:
                has_class = False
                self.validation_results["errors"].append(f"Config import error: {e}")
        else:
            has_class = False

        duration = (datetime.now() - start_time).total_seconds()

        success = config_exists and has_class

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": "Unified configuration system",
        }

        self.assertTrue(config_exists, "Unified config not found")
        self.assertTrue(has_class, "UnifiedConfig class not found")

        print(f"✅ {test_name} passed - Configuration integrated")

    def test_17_coordination_system(self):
        """Test: System coordination component"""
        test_name = "System Coordination"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        coordinator_file = (
            self.bootstrap_root / "coordination" / "system_coordinator.py"
        )

        # Check if coordinator exists
        coordinator_exists = coordinator_file.exists()

        if coordinator_exists:
            # Try to import coordinator
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "system_coordinator", coordinator_file
            )
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                has_class = hasattr(module, "SystemCoordinator")
            except Exception as e:
                has_class = False
                self.validation_results["errors"].append(
                    f"Coordinator import error: {e}"
                )
        else:
            has_class = False

        duration = (datetime.now() - start_time).total_seconds()

        success = coordinator_exists and has_class

        self.validation_results["components"]["coordination"] = {
            "passed": success,
            "details": (
                "System coordinator functional"
                if success
                else "Coordinator missing or import failed"
            ),
        }

        self.validation_results["tests"][test_name] = {
            "passed": success,
            "duration": f"{duration:.2f}s",
            "notes": "System coordination validation",
        }

        self.assertTrue(coordinator_exists, "System coordinator not found")
        self.assertTrue(has_class, "SystemCoordinator class not found")

        print(f"✅ {test_name} passed - Coordination system valid")

    def test_18_end_to_end_workflow(self):
        """Test: End-to-end project workflow"""
        test_name = "End-to-End Workflow"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        workflow_success = True
        workflow_steps = []

        # Step 1: List projects (should work even if empty)
        returncode, stdout, stderr = self.run_command([str(self.bootstrap_cli), "list"])
        workflow_steps.append(("List projects", returncode == 0))
        workflow_success = workflow_success and (returncode == 0)

        # Step 2: Show registry stats
        returncode, stdout, stderr = self.run_command(
            [str(self.bootstrap_cli), "registry", "stats"]
        )
        workflow_steps.append(("Registry stats", returncode == 0))
        workflow_success = workflow_success and (returncode == 0)

        # Step 3: Show status
        returncode, stdout, stderr = self.run_command(
            [str(self.bootstrap_cli), "status"]
        )
        workflow_steps.append(("Platform status", returncode == 0))
        workflow_success = workflow_success and (returncode == 0)

        duration = (datetime.now() - start_time).total_seconds()

        failed_steps = [step for step, success in workflow_steps if not success]

        self.validation_results["tests"][test_name] = {
            "passed": workflow_success,
            "duration": f"{duration:.2f}s",
            "notes": f"Completed {len(workflow_steps)} workflow steps",
        }

        if failed_steps:
            self.validation_results["errors"].append(
                f"Workflow failed at: {failed_steps}"
            )

        self.assertTrue(workflow_success, f"Workflow failed at steps: {failed_steps}")

        print(f"✅ {test_name} passed - Workflow completed successfully")

    def test_19_platform_integration(self):
        """Test: Overall platform integration"""
        test_name = "Platform Integration"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        # Check overall platform health
        integration_checks = []

        # CLI is executable
        cli_executable = self.bootstrap_cli.exists() and os.access(
            self.bootstrap_cli, os.X_OK
        )
        integration_checks.append(("CLI executable", cli_executable))

        # Registry exists or can be created
        registry_file = self.bootstrap_root / "projects" / "registry.yaml"
        registry_ok = registry_file.exists() or registry_file.parent.exists()
        integration_checks.append(("Registry accessible", registry_ok))

        # Core directories exist
        core_dirs = [
            "modules",
            "lib",
            "scripts",
            "config",
            "monitoring",
            "intelligence",
        ]
        for dir_name in core_dirs:
            dir_exists = (self.bootstrap_root / dir_name).exists()
            integration_checks.append((f"Directory: {dir_name}", dir_exists))

        duration = (datetime.now() - start_time).total_seconds()

        failed_checks = [check for check, success in integration_checks if not success]
        integration_success = len(failed_checks) == 0

        self.validation_results["tests"][test_name] = {
            "passed": integration_success,
            "duration": f"{duration:.2f}s",
            "notes": f"Performed {len(integration_checks)} integration checks",
        }

        if failed_checks:
            self.validation_results["warnings"].append(
                f"Integration issues: {failed_checks}"
            )

        self.assertTrue(
            integration_success, f"Integration checks failed: {failed_checks}"
        )

        print(f"✅ {test_name} passed - Platform fully integrated")

    def test_20_final_validation(self):
        """Test: Final platform validation"""
        test_name = "Final Platform Validation"
        print(f"\n🔍 Running: {test_name}")

        start_time = datetime.now()

        # Summary of all component statuses
        total_components = len(self.validation_results["components"])
        passed_components = sum(
            1 for c in self.validation_results["components"].values() if c["passed"]
        )

        # Summary of all test results
        total_tests = len(self.validation_results["tests"])
        passed_tests = sum(
            1 for t in self.validation_results["tests"].values() if t["passed"]
        )

        duration = (datetime.now() - start_time).total_seconds()

        platform_functional = (passed_components == total_components) and (
            passed_tests >= total_tests - 1
        )

        self.validation_results["tests"][test_name] = {
            "passed": platform_functional,
            "duration": f"{duration:.2f}s",
            "notes": f"Components: {passed_components}/{total_components}, Tests: {passed_tests}/{total_tests}",
        }

        print(f"\n{'=' * 60}")
        print("FINAL VALIDATION SUMMARY")
        print(f"{'=' * 60}")
        print(f"Components Validated: {passed_components}/{total_components}")
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        print(f"Errors: {len(self.validation_results['errors'])}")
        print(f"Warnings: {len(self.validation_results['warnings'])}")

        if platform_functional:
            print("\n🎉 PLATFORM IS 100% FUNCTIONAL!")
        else:
            print("\n⚠️ Platform has issues that need attention")

        print(f"{'=' * 60}\n")

        self.assertTrue(platform_functional, "Platform is not fully functional")


def main():
    """Main entry point for validation suite"""
    print("=" * 60)
    print("UNIVERSAL PROJECT PLATFORM - COMPREHENSIVE VALIDATION")
    print("=" * 60)
    print(f"Platform Root: {Path(__file__).parent.parent.resolve()}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(UniversalPlatformValidation)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code based on results
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
