"""
Genesis Constants and Configuration

Single source of truth for all configurable values.
No hardcoded defaults - fail fast when configuration is missing.
"""

import os


def get_required_env(key: str) -> str:
    """
    Get required environment variable - fail fast if missing.

    Args:
        key: Environment variable name

    Returns:
        Environment variable value

    Raises:
        ValueError: If environment variable is not set
    """
    value = os.environ.get(key)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


def get_service_name() -> str:
    """
    Get current service name - fail fast if not configured.

    Returns:
        Service name

    Raises:
        ValueError: If service name cannot be determined
    """
    # Try environment variable first
    service_name = os.environ.get("SERVICE")
    if service_name:
        return service_name

    # Try to detect from git remote or directory name
    import subprocess
    from pathlib import Path

    try:
        # Try git remote origin
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path.cwd(),
        )
        if result.stdout.strip():
            # Extract repo name from git URL
            url = result.stdout.strip()
            if url.endswith(".git"):
                url = url[:-4]
            service_name = url.split("/")[-1]
            if service_name:
                return service_name
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Last resort: use current directory name
    service_name = Path.cwd().name
    if service_name and service_name != "." and service_name != "/":
        return service_name

    raise ValueError(
        "Cannot determine service name. Set SERVICE environment variable "
        "or ensure you're in a properly named project directory with git remote."
    )


def get_environment() -> str:
    """
    Get current environment - fail fast if not configured.

    Returns:
        Environment name

    Raises:
        ValueError: If environment cannot be determined
    """
    # Try common environment variables
    env_vars = ["ENV", "ENVIRONMENT", "ENV", "NODE_ENV"]

    for var in env_vars:
        value = os.environ.get(var)
        if value:
            return value

    raise ValueError("Cannot determine environment. Set one of: " + ", ".join(env_vars))


class AILimits:
    """AI safety limits - configurable but with sensible bounds."""

    @staticmethod
    def get_max_worktree_files() -> int:
        """Get maximum files per worktree for AI safety."""
        value_str = os.environ.get("AI_MAX_FILES")
        if not value_str:
            raise ValueError("AI_MAX_FILES environment variable is required")
        try:
            value = int(value_str)
            if value <= 0 or value > 100:
                raise ValueError("AI_MAX_FILES must be between 1-100")
            return value
        except ValueError as e:
            raise ValueError(f"Invalid AI_MAX_FILES '{value_str}': {e}") from e

    @staticmethod
    def get_max_project_files() -> int:
        """Get maximum files per project for AI safety."""
        value_str = os.environ.get("MAX_PROJECT_FILES")
        if not value_str:
            raise ValueError("MAX_PROJECT_FILES environment variable is required")
        try:
            value = int(value_str)
            if value <= 0 or value > 1000:
                raise ValueError("MAX_PROJECT_FILES must be between 1-1000")
            return value
        except ValueError as e:
            raise ValueError(f"Invalid MAX_PROJECT_FILES '{value_str}': {e}") from e

    @staticmethod
    def get_max_component_files() -> int:
        """Get maximum files per component for AI safety."""
        value_str = os.environ.get("AI_MAX_FILES")
        if not value_str:
            raise ValueError("AI_MAX_FILES environment variable is required")
        try:
            value = int(value_str)
            if value <= 0 or value > 100:
                raise ValueError("AI_MAX_FILES must be between 1-100")
            return value
        except ValueError as e:
            raise ValueError(f"Invalid AI_MAX_FILES '{value_str}': {e}") from e


class RetryDefaults:
    """Retry configuration - no defaults, must be explicitly set."""

    @staticmethod
    def get_max_attempts() -> int:
        """Get retry max attempts."""
        return int(get_required_env("RETRY_MAX_ATTEMPTS"))

    @staticmethod
    def get_initial_delay() -> float:
        """Get retry initial delay."""
        return float(get_required_env("RETRY_INITIAL_DELAY"))

    @staticmethod
    def get_max_delay() -> float:
        """Get retry max delay."""
        return float(get_required_env("RETRY_MAX_DELAY"))

    @staticmethod
    def get_exponential_base() -> float:
        """Get retry exponential base."""
        return float(get_required_env("RETRY_EXPONENTIAL_BASE"))


class CircuitBreakerDefaults:
    """Circuit breaker configuration - no defaults, must be explicitly set."""

    @staticmethod
    def get_failure_threshold() -> int:
        """Get circuit breaker failure threshold."""
        return int(get_required_env("CB_FAILURE_THRESHOLD"))

    @staticmethod
    def get_timeout() -> float:
        """Get circuit breaker timeout."""
        return float(get_required_env("CB_TIMEOUT"))

    @staticmethod
    def get_half_open_max_calls() -> int:
        """Get circuit breaker half-open max calls."""
        return int(get_required_env("CB_HALF_OPEN_MAX_CALLS"))

    @staticmethod
    def get_success_threshold() -> int:
        """Get circuit breaker success threshold."""
        return int(get_required_env("CB_SUCCESS_THRESHOLD"))

    @staticmethod
    def get_sliding_window_size() -> int:
        """Get circuit breaker sliding window size."""
        return int(get_required_env("CB_SLIDING_WINDOW_SIZE"))


class LoggerConfig:
    """Logger configuration with environment-specific behavior."""

    @staticmethod
    def get_level() -> str:
        """Get log level based on environment."""
        env = os.environ.get("LOG_LEVEL")
        if env:
            return env

        # Environment-specific defaults only if no explicit config
        try:
            environment = get_environment()
            if environment in ["production", "prod"]:
                return "WARNING"
            elif environment in ["development", "dev", "local"]:
                return "DEBUG"
            elif environment in ["staging", "test"]:
                return "INFO"
        except ValueError:
            pass

        # Default to INFO for CLI usage when environment isn't configured
        return "INFO"

    @staticmethod
    def should_format_json() -> bool:
        """Whether to format logs as JSON."""
        value = os.environ.get("LOG_JSON")
        if not value:
            # Default based on environment if available
            try:
                environment = get_environment()
                return environment in ["production", "prod", "staging"]
            except ValueError:
                return False  # Default to human-readable for CLI

        value = value.lower()
        if value in ["true", "1", "yes"]:
            return True
        elif value in ["false", "0", "no"]:
            return False

        # Default based on environment
        try:
            environment = get_environment()
            return environment in ["production", "prod", "staging"]
        except ValueError:
            return False  # Default to human-readable for CLI

    @staticmethod
    def should_include_timestamp() -> bool:
        """Whether to include timestamp in logs."""
        value = os.environ.get("LOG_TIMESTAMP")
        if not value:
            return True  # Default to including timestamps

        value = value.lower()
        if value in ["true", "1", "yes"]:
            return True
        elif value in ["false", "0", "no"]:
            return False
        return True  # Always include timestamps by default

    @staticmethod
    def should_include_caller() -> bool:
        """Whether to include caller info in logs."""
        value = os.environ.get("LOG_CALLER")
        if not value:
            return False  # Default to not including caller for CLI simplicity
        value = value.lower()
        if value in ["true", "1", "yes"]:
            return True
        elif value in ["false", "0", "no"]:
            return False

        # Default based on environment
        try:
            environment = get_environment()
            return environment in ["development", "dev", "local"]
        except ValueError:
            return False  # Safe default


# Common directory exclusions for AI safety
SKIP_DIRECTORIES = frozenset(
    [
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        "site-packages",
        ".git",
        "dist",
        "build",
        "__pycache__",
        ".pytest_cache",
        "coverage",
        ".coverage",
        "old-bloated-code-read-only",
    ]
)


def get_genesis_components() -> dict[str, str]:
    """
    Get Genesis components from environment configuration.

    Returns:
        Dictionary mapping component names to descriptions

    Raises:
        ValueError: If no components are configured
    """
    # Try environment variable first (JSON format)
    components_json = os.environ.get("COMPONENTS")
    if components_json:
        import json

        try:
            return json.loads(components_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid COMPONENTS JSON: {e}") from e

    # Try individual environment variables
    component_vars = {
        f"COMPONENT_{name.upper().replace('-', '_')}": name
        for name in [
            "bootstrap",
            "smart-commit",
            "worktree-tools",
            "genesis",
            "testing",
        ]
    }

    configured_components = {}
    for env_var, component_name in component_vars.items():
        description = os.environ.get(env_var)
        if description:
            configured_components[component_name] = description

    if configured_components:
        return configured_components

    raise ValueError(
        "No Genesis components configured. Set COMPONENTS (JSON) or "
        "individual COMPONENT_* environment variables"
    )


def get_component_scripts() -> dict[str, str]:
    """
    Get component script paths from environment configuration.

    Returns:
        Dictionary mapping component names to script paths

    Raises:
        ValueError: If no component scripts are configured
    """
    # Try environment variable first (JSON format)
    scripts_json = os.environ.get("COMPONENT_SCRIPTS")
    if scripts_json:
        import json

        try:
            return json.loads(scripts_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid COMPONENT_SCRIPTS JSON: {e}") from e

    # Try individual environment variables
    script_vars = {
        "WORKTREE_SCRIPT": "worktree-tools",
        "SMART_COMMIT_SCRIPT": "smart-commit",
    }

    configured_scripts = {}
    for env_var, component_name in script_vars.items():
        script_path = os.environ.get(env_var)
        if script_path:
            configured_scripts[component_name] = script_path

    if not configured_scripts:
        raise ValueError(
            "No component scripts configured. Set COMPONENT_SCRIPTS (JSON) or "
            "individual *_SCRIPT environment variables"
        )

    return configured_scripts


def get_python_version() -> str:
    """
    Get current Python version for template generation.

    Returns:
        Python version string (e.g., "3.11")
    """
    import sys

    return f"{sys.version_info.major}.{sys.version_info.minor}"


def get_git_author_info() -> tuple[str, str]:
    """
    Get git author information.

    Returns:
        Tuple of (name, email)

    Raises:
        ValueError: If git config is not set up
    """
    import subprocess

    try:
        name_result = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, check=True
        )

        email_result = subprocess.run(
            ["git", "config", "user.email"], capture_output=True, text=True, check=True
        )

        name = name_result.stdout.strip()
        email = email_result.stdout.strip()

        if not name or not email:
            raise ValueError("Git name or email is empty")

        return name, email

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise ValueError(
            "Git author information not configured. "
            "Run: git config user.name 'Your Name' && git config user.email 'you@example.com'"
        ) from e
