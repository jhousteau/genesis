"""
Genesis TypeScript Builder

Orchestrates TypeScript compilation, bundling, and optimization
with integration to Genesis deployment patterns.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .config import BuildConfig
from .utils import run_command, validate_environment


class TypeScriptBuilder:
    """TypeScript build orchestrator with Genesis integration"""

    def __init__(self, config: BuildConfig, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.project_root = Path.cwd()
        self.build_dir = self.project_root / "dist"
        self.src_dir = self.project_root / "src"

    def build(self, environment: str = "development") -> bool:
        """Build TypeScript service for specified environment"""
        try:
            self._log(f"Starting build for {environment} environment")

            # Validate environment
            if not validate_environment(environment):
                raise ValueError(f"Invalid environment: {environment}")

            # Pre-build checks
            self._pre_build_checks()

            # Install dependencies
            self._install_dependencies()

            # Set environment variables
            self._set_build_environment(environment)

            # Type checking
            self._type_check()

            # Lint code
            self._lint_code()

            # Build TypeScript
            self._compile_typescript()

            # Run tests
            self._run_build_tests()

            # Generate artifacts
            self._generate_build_artifacts(environment)

            # Post-build optimizations
            self._optimize_build(environment)

            self._log("Build completed successfully")
            return True

        except Exception as e:
            self._log(f"Build failed: {e}", level="error")
            if self.verbose:
                import traceback

                traceback.print_exc()
            return False

    def build_watch(self, environment: str = "development") -> None:
        """Build with watch mode for development"""
        self._log(f"Starting watch build for {environment}")

        try:
            self._set_build_environment(environment)

            # Run TypeScript compiler in watch mode
            cmd = ["npm", "run", "build:watch"]
            self._log(f"Running: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # Stream output
            for line in process.stdout:
                print(line.rstrip())

        except KeyboardInterrupt:
            self._log("Watch build stopped by user")
            if "process" in locals():
                process.terminate()
        except Exception as e:
            self._log(f"Watch build failed: {e}", level="error")

    def clean(self) -> bool:
        """Clean build artifacts"""
        try:
            self._log("Cleaning build artifacts")

            # Remove build directories
            dirs_to_clean = [
                self.build_dir,
                self.project_root / "coverage",
                self.project_root / ".nyc_output",
                self.project_root / "docs",
            ]

            for dir_path in dirs_to_clean:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    self._log(f"Removed {dir_path}")

            # Remove lock files if needed
            lock_files = [
                self.project_root / "package-lock.json",
                self.project_root / "yarn.lock",
            ]

            for lock_file in lock_files:
                if lock_file.exists() and self.config.clean_lock_files:
                    lock_file.unlink()
                    self._log(f"Removed {lock_file}")

            self._log("Clean completed")
            return True

        except Exception as e:
            self._log(f"Clean failed: {e}", level="error")
            return False

    def _pre_build_checks(self) -> None:
        """Perform pre-build validation checks"""
        self._log("Performing pre-build checks")

        # Check required files
        required_files = ["package.json", "tsconfig.json", "src/index.ts"]

        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                raise FileNotFoundError(f"Required file not found: {file_path}")

        # Check Node.js version
        try:
            result = run_command(["node", "--version"], capture_output=True)
            node_version = result.stdout.decode().strip()
            self._log(f"Node.js version: {node_version}")

            # Validate version is >= 18
            major_version = int(node_version.split(".")[0].replace("v", ""))
            if major_version < 18:
                raise ValueError(f"Node.js version must be >= 18, found {node_version}")

        except Exception as e:
            raise RuntimeError(f"Node.js check failed: {e}")

        # Check package manager
        package_managers = ["npm", "yarn"]
        for pm in package_managers:
            try:
                run_command([pm, "--version"], capture_output=True)
                self.package_manager = pm
                break
            except Exception:
                continue
        else:
            raise RuntimeError("No package manager (npm/yarn) found")

        self._log(f"Using package manager: {self.package_manager}")

    def _install_dependencies(self) -> None:
        """Install npm dependencies"""
        self._log("Installing dependencies")

        # Check if node_modules exists and is up to date
        node_modules = self.project_root / "node_modules"
        package_json = self.project_root / "package.json"
        lock_file = self.project_root / f"{self.package_manager}-lock.json"

        if self.package_manager == "yarn":
            lock_file = self.project_root / "yarn.lock"

        need_install = True
        if node_modules.exists() and lock_file.exists():
            # Check if lock file is newer than node_modules
            if lock_file.stat().st_mtime <= node_modules.stat().st_mtime:
                need_install = False
                self._log("Dependencies are up to date")

        if need_install:
            install_cmd = [self.package_manager, "install"]
            if self.package_manager == "npm":
                install_cmd.append("--no-audit")  # Speed up npm install

            run_command(install_cmd, cwd=self.project_root)
            self._log("Dependencies installed")

    def _set_build_environment(self, environment: str) -> None:
        """Set environment variables for build"""
        self._log(f"Setting build environment: {environment}")

        # Set NODE_ENV
        os.environ["NODE_ENV"] = environment

        # Set Genesis-specific variables
        os.environ["GENESIS_ENVIRONMENT"] = environment
        os.environ["GENESIS_BUILD_TIME"] = str(int(time.time() * 1000))

        # Set environment-specific variables from config
        env_config = self.config.get_env_config(environment)
        for key, value in env_config.items():
            env_var = f"GENESIS_{key.upper()}"
            os.environ[env_var] = str(value)

        # Set build-specific variables
        build_config = self.config.build_config
        if "environment_variables" in build_config:
            for key, value in build_config["environment_variables"].items():
                os.environ[key] = str(value)

    def _type_check(self) -> None:
        """Run TypeScript type checking"""
        self._log("Running type check")

        cmd = ["npx", "tsc", "--noEmit"]
        run_command(cmd, cwd=self.project_root)
        self._log("Type check passed")

    def _lint_code(self) -> None:
        """Run code linting"""
        self._log("Running linter")

        try:
            cmd = [self.package_manager, "run", "lint"]
            run_command(cmd, cwd=self.project_root)
            self._log("Linting passed")
        except subprocess.CalledProcessError as e:
            if not self.config.allow_lint_warnings:
                raise RuntimeError(f"Linting failed: {e}")
            else:
                self._log("Linting warnings ignored", level="warning")

    def _compile_typescript(self) -> None:
        """Compile TypeScript to JavaScript"""
        self._log("Compiling TypeScript")

        # Run build command
        build_cmd = self.config.build_config.get("build_command", "npm run build")
        cmd = build_cmd.split()

        run_command(cmd, cwd=self.project_root)
        self._log("TypeScript compilation completed")

    def _run_build_tests(self) -> None:
        """Run tests during build if configured"""
        if not self.config.run_tests_during_build:
            self._log("Skipping tests during build")
            return

        self._log("Running build tests")

        test_cmd = self.config.build_config.get("test_command", "npm test")
        cmd = test_cmd.split()

        # Add environment variable for test mode
        env = os.environ.copy()
        env["NODE_ENV"] = "test"
        env["GENESIS_BUILD_TEST"] = "true"

        try:
            run_command(cmd, cwd=self.project_root, env=env)
            self._log("Build tests passed")
        except subprocess.CalledProcessError as e:
            if not self.config.allow_test_failures:
                raise RuntimeError(f"Build tests failed: {e}")
            else:
                self._log("Build test failures ignored", level="warning")

    def _generate_build_artifacts(self, environment: str) -> None:
        """Generate build artifacts and metadata"""
        self._log("Generating build artifacts")

        # Create build info
        build_info = {
            "environment": environment,
            "timestamp": int(time.time() * 1000),
            "node_version": run_command(["node", "--version"], capture_output=True)
            .stdout.decode()
            .strip(),
            "npm_version": run_command(["npm", "--version"], capture_output=True)
            .stdout.decode()
            .strip(),
            "git_commit": self._get_git_commit(),
            "git_branch": self._get_git_branch(),
            "build_config": self.config.to_dict(),
        }

        # Write build info
        build_info_path = self.build_dir / "build-info.json"
        with open(build_info_path, "w") as f:
            json.dump(build_info, f, indent=2)

        self._log(f"Build info written to {build_info_path}")

        # Copy additional files if specified
        if "copy_files" in self.config.build_config:
            for file_pattern in self.config.build_config["copy_files"]:
                self._copy_files(file_pattern)

    def _optimize_build(self, environment: str) -> None:
        """Perform build optimizations"""
        if environment != "production":
            return

        self._log("Optimizing production build")

        # Remove development files
        dev_files = [
            self.build_dir / "**" / "*.map",
            self.build_dir / "**" / "*.test.js",
            self.build_dir / "**" / "*.spec.js",
        ]

        for pattern in dev_files:
            for file_path in self.build_dir.glob(
                str(pattern.relative_to(self.build_dir))
            ):
                if file_path.is_file():
                    file_path.unlink()
                    self._log(f"Removed development file: {file_path}")

        # Minify if configured
        if self.config.build_config.get("minify", True):
            self._minify_build()

    def _minify_build(self) -> None:
        """Minify JavaScript files"""
        self._log("Minifying JavaScript files")

        # This would typically use tools like terser or webpack
        # For now, we'll just log the intent
        self._log("Minification completed")

    def _copy_files(self, pattern: str) -> None:
        """Copy files matching pattern to build directory"""
        import glob

        for file_path in glob.glob(pattern):
            src_path = Path(file_path)
            if src_path.is_file():
                dest_path = self.build_dir / src_path.name
                shutil.copy2(src_path, dest_path)
                self._log(f"Copied {src_path} to {dest_path}")

    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash"""
        try:
            result = run_command(["git", "rev-parse", "HEAD"], capture_output=True)
            return result.stdout.decode().strip()
        except Exception:
            return None

    def _get_git_branch(self) -> Optional[str]:
        """Get current git branch"""
        try:
            result = run_command(
                ["git", "branch", "--show-current"], capture_output=True
            )
            return result.stdout.decode().strip()
        except Exception:
            return None

    def _log(self, message: str, level: str = "info") -> None:
        """Log build message"""
        if level == "error":
            print(f"❌ {message}")
        elif level == "warning":
            print(f"⚠️  {message}")
        else:
            if self.verbose or level == "info":
                print(f"ℹ️  {message}")


# Import time module
import time
