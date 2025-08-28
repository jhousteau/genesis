"""
Tests for hardcoded value detection scripts.

These tests ensure our regex patterns correctly identify problematic hardcoded values
and variable defaults in both Python and TypeScript code.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestHardcodedDetection:
    """Test hardcoded value detection scripts."""

    @pytest.fixture
    def scripts_dir(self) -> Path:
        """Get path to scripts directory."""
        return Path(__file__).parent.parent / "scripts"

    @pytest.fixture
    def hardcoded_script(self, scripts_dir: Path) -> Path:
        """Get path to hardcoded values detection script."""
        script_path = scripts_dir / "find-hardcoded-values.sh"
        assert script_path.exists(), f"Script not found: {script_path}"
        return script_path

    @pytest.fixture
    def variable_defaults_script(self, scripts_dir: Path) -> Path:
        """Get path to variable defaults detection script."""
        script_path = scripts_dir / "check-variable-defaults.sh"
        assert script_path.exists(), f"Script not found: {script_path}"
        return script_path

    def create_test_files(self, files: list[tuple[str, str]]) -> Path:
        """Create temporary test files and return the directory path."""
        temp_dir = Path(tempfile.mkdtemp())

        for filename, content in files:
            file_path = temp_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        return temp_dir

    def run_script(self, script_path: Path, test_dir: Path) -> tuple[int, str, str]:
        """Run detection script on test directory."""
        env = os.environ.copy()
        env["PWD"] = str(test_dir)

        result = subprocess.run(
            [str(script_path)], cwd=test_dir, capture_output=True, text=True, env=env
        )

        return result.returncode, result.stdout, result.stderr

    def test_python_function_defaults_detected(self, hardcoded_script: Path):
        """Test detection of Python function parameter defaults."""
        test_files = [
            (
                "bad_defaults.py",
                """
def bad_function(name="hardcoded", port=8080, timeout=30):
    pass

def another_bad(url="https://api.example.com"):
    pass
            """,
            ),
            (
                "good_defaults.py",
                """
def good_function(name=None, enabled=True, items=None):
    pass

def another_good(count=0, debug=False):
    pass
            """,
            ),
        ]

        test_dir = self.create_test_files(test_files)
        returncode, stdout, stderr = self.run_script(hardcoded_script, test_dir)

        # Should detect issues (non-zero return code)
        assert returncode != 0
        assert "bad_defaults.py" in stdout
        assert "Found issues" in stdout

    def test_environment_variable_fallbacks_detected(self, hardcoded_script: Path):
        """Test detection of environment variable fallbacks."""
        test_files = [
            (
                "bad_env.py",
                """
import os

# Bad - has fallback defaults
database_url = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/app")
service_name = os.environ.get("SERVICE_NAME", "my-service")
port = int(os.environ.get("PORT", "8080"))
            """,
            ),
            (
                "good_env.py",
                """
import os

# Good - no fallback defaults
database_url = os.environ.get("DATABASE_URL")
service_name = os.environ.get("SERVICE_NAME")
if not service_name:
    raise ValueError("SERVICE_NAME required")
            """,
            ),
        ]

        test_dir = self.create_test_files(test_files)
        returncode, stdout, stderr = self.run_script(hardcoded_script, test_dir)

        # Should detect issues
        assert returncode != 0
        assert "bad_env.py" in stdout

    def test_hardcoded_urls_detected(self, hardcoded_script: Path):
        """Test detection of hardcoded URLs and hostnames."""
        test_files = [
            (
                "bad_urls.py",
                """
API_BASE = "https://api.example.com"
DATABASE_HOST = "localhost"
REDIS_URL = "redis://127.0.0.1:6379"
            """,
            )
        ]

        test_dir = self.create_test_files(test_files)
        returncode, stdout, stderr = self.run_script(hardcoded_script, test_dir)

        # Should detect issues
        assert returncode != 0
        assert "bad_urls.py" in stdout

    def test_typescript_function_defaults_detected(
        self, variable_defaults_script: Path
    ):
        """Test detection of TypeScript function parameter defaults."""
        test_files = [
            (
                "bad_defaults.ts",
                """
function badFunction(name = "hardcoded", port = 8080) {
    return name + port;
}

const arrowBad = (url = "https://api.example.com") => {
    return fetch(url);
};

// Interface with defaults
interface Config {
    apiUrl?: string = "https://default.api.com";
    timeout?: number = 5000;
}
            """,
            ),
            (
                "good_defaults.ts",
                """
function goodFunction(name?: string, port = 0) {
    return name + port;
}

const arrowGood = (url?: string) => {
    return url || process.env.API_URL;
};
            """,
            ),
        ]

        test_dir = self.create_test_files(test_files)
        returncode, stdout, stderr = self.run_script(variable_defaults_script, test_dir)

        # Should detect issues
        assert returncode != 0
        assert "bad_defaults.ts" in stdout

    def test_python_variable_assignments_detected(self, variable_defaults_script: Path):
        """Test detection of Python variable assignments with hardcoded values."""
        test_files = [
            (
                "bad_variables.py",
                """
# Bad - hardcoded strings and URLs
API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
SERVICE_NAME = "my-hardcoded-service"
DEFAULT_TIMEOUT = 30

class Config:
    api_base: str = "https://api.example.com"
    max_retries: int = 5
            """,
            ),
            (
                "good_variables.py",
                """
# Good - no hardcoded values
import os

API_KEY = os.environ.get("API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")
SERVICE_NAME = os.environ.get("SERVICE_NAME")

class Config:
    api_base: str
    max_retries: int

    def __init__(self):
        self.api_base = os.environ.get("API_BASE")
        self.max_retries = int(os.environ.get("MAX_RETRIES", "3"))
            """,
            ),
        ]

        test_dir = self.create_test_files(test_files)
        returncode, stdout, stderr = self.run_script(variable_defaults_script, test_dir)

        # Should detect issues
        assert returncode != 0
        assert "bad_variables.py" in stdout

    def test_typescript_object_properties_detected(
        self, variable_defaults_script: Path
    ):
        """Test detection of TypeScript object properties with hardcoded defaults."""
        test_files = [
            (
                "bad_objects.ts",
                """
const config = {
    apiUrl: "https://api.hardcoded.com",
    timeout: 5000,
    retries: 3,
    environment: "production"
};

class ApiClient {
    private baseUrl: string = "https://api.example.com";
    private timeout: number = 30000;

    constructor() {
        // Bad defaults
    }
}
            """,
            ),
            (
                "good_objects.ts",
                """
const config = {
    apiUrl: process.env.API_URL,
    timeout: parseInt(process.env.TIMEOUT || "0"),
    retries: parseInt(process.env.RETRIES || "1"),
    environment: process.env.NODE_ENV
};

class ApiClient {
    private baseUrl: string;
    private timeout: number;

    constructor(baseUrl: string, timeout: number) {
        this.baseUrl = baseUrl;
        this.timeout = timeout;
    }
}
            """,
            ),
        ]

        test_dir = self.create_test_files(test_files)
        returncode, stdout, stderr = self.run_script(variable_defaults_script, test_dir)

        # Should detect issues
        assert returncode != 0
        assert "bad_objects.ts" in stdout

    def test_cross_language_patterns_detected(self, variable_defaults_script: Path):
        """Test detection of cross-language patterns (URLs, ports, etc.)."""
        test_files = [
            (
                "cross_lang.py",
                """
LOCALHOST_URL = "http://localhost:3000"
DB_HOST = "127.0.0.1"
API_PORT = ":8080"
            """,
            ),
            (
                "cross_lang.ts",
                """
const LOCALHOST_URL = "http://localhost:3000";
const DB_HOST = "127.0.0.1";
const API_PORT = ":8080";
            """,
            ),
        ]

        test_dir = self.create_test_files(test_files)
        returncode, stdout, stderr = self.run_script(variable_defaults_script, test_dir)

        # Should detect issues in both files
        assert returncode != 0
        assert "cross_lang.py" in stdout
        assert "cross_lang.ts" in stdout

    def test_acceptable_values_ignored(self, variable_defaults_script: Path):
        """Test that truly safe values are not flagged by our stricter patterns."""
        test_files = [
            (
                "acceptable.py",
                """
# These patterns should not be detected by our focused patterns
import os
value = 42  # Not a function parameter default
result = calculate(x * 1024)  # Math constant, not configuration
            """,
            ),
            (
                "acceptable.ts",
                """
// These patterns should not be detected
const MATH_CONSTANT = 1024;
const result = memory / 1024 / 1024;  // Math operation
            """,
            ),
        ]

        test_dir = self.create_test_files(test_files)
        returncode, stdout, stderr = self.run_script(variable_defaults_script, test_dir)

        # Should NOT detect issues (return code 0)
        assert returncode == 0
        assert "No variable default issues found" in stdout

    def test_database_connection_strings_detected(self, variable_defaults_script: Path):
        """Test detection of database connection strings with credentials."""
        test_files = [
            (
                "db_strings.py",
                """
# Bad - connection strings with credentials
DATABASE_URL = "postgresql://user:password@localhost:5432/mydb"
REDIS_URL = "redis://user:pass@127.0.0.1:6379/0"
MONGO_URL = "mongodb://admin:secret@mongo:27017/app"
            """,
            )
        ]

        test_dir = self.create_test_files(test_files)
        returncode, stdout, stderr = self.run_script(variable_defaults_script, test_dir)

        # Should detect issues
        assert returncode != 0
        assert "Database connection strings with credentials" in stdout

    def test_environment_variable_fallbacks_detected(
        self, variable_defaults_script: Path
    ):
        """Test detection of dangerous environment variable fallback patterns."""
        test_files = [
            (
                "env_fallbacks.py",
                """
# Bad - environment variable fallbacks with hardcoded defaults
database_url = os.environ.get("DATABASE_URL", "postgresql://localhost/app")
api_key = os.environ.get("API_KEY", "hardcoded-fallback")
            """,
            ),
            (
                "env_fallbacks.ts",
                """
// Bad - environment variable fallbacks
const dbUrl = process.env["DATABASE_URL"] || "postgresql://localhost/app";
const port = process.env["PORT"] || "8080";
            """,
            ),
        ]

        test_dir = self.create_test_files(test_files)
        returncode, stdout, stderr = self.run_script(variable_defaults_script, test_dir)

        # Should detect issues
        assert returncode != 0
        assert "Environment variable fallbacks" in stdout

    def test_clean_codebase_passes(
        self, hardcoded_script: Path, variable_defaults_script: Path
    ):
        """Test that clean code without hardcoded values passes both scripts."""
        test_files = [
            (
                "clean.py",
                '''
import os

def configure_service(name: str, port: int, timeout: Optional[int] = None):
    """Configure service with required parameters."""
    if not name:
        raise ValueError("Service name is required")
    return {"name": name, "port": port, "timeout": timeout}

# Good configuration loading
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

SERVICE_NAME = get_service_name()  # From constants module
            ''',
            ),
            (
                "clean.ts",
                """
interface ServiceConfig {
    name: string;
    port: number;
    timeout?: number;
}

function configureService(config: ServiceConfig): ServiceConfig {
    if (!config.name) {
        throw new Error("Service name is required");
    }
    return config;
}

// Good configuration loading
const DATABASE_URL = process.env.DATABASE_URL;
if (!DATABASE_URL) {
    throw new Error("DATABASE_URL environment variable is required");
}
            """,
            ),
        ]

        test_dir = self.create_test_files(test_files)

        # Both scripts should pass
        returncode1, stdout1, stderr1 = self.run_script(hardcoded_script, test_dir)
        returncode2, stdout2, stderr2 = self.run_script(
            variable_defaults_script, test_dir
        )

        assert returncode1 == 0 or "No hardcoded values found" in stdout1
        assert returncode2 == 0, f"Variable defaults script failed: {stdout2}"
        assert "No variable default issues found" in stdout2
