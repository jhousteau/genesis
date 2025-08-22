"""
Configuration management system for SOLVE framework.

This module provides centralized configuration management with:
- Environment variable loading with validation
- Type conversion and default values
- Secure secret management
- Development vs production profiles
- Configuration validation and error handling
"""

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from jsonschema import ValidationError, validate

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


class LogLevel(Enum):
    """Supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Supported log formats."""

    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"


class Environment(Enum):
    """Supported environments."""

    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"


class RollbackStrategy(Enum):
    """Rollback strategies for autofix."""

    ALWAYS = "always"
    ON_SYNTAX_ERROR = "on_syntax_error"
    NEVER = "never"


@dataclass
class APIConfig:
    """API configuration for external services."""

    # Anthropic API keys
    sdk_key: str | None = None
    api_key: str | None = None

    # Google ADK configuration
    adk_project_id: str | None = None
    adk_location: str | None = None
    adk_credentials_path: str | None = None

    # LLM settings
    llm_model: str = "gemini-2.0-flash-exp"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 4096
    llm_timeout: int = 300
    llm_max_retries: int = 3
    llm_batch_size: int = 10

    def validate(self) -> None:
        """Validate API configuration."""
        # Google ADK is required for agents
        if not self.adk_project_id:
            raise ConfigurationError(
                "Google ADK configuration is required for SOLVE agents:\n"
                "  - Set SOLVE_ADK_PROJECT_ID to your Google Cloud project ID\n"
                "  - Optionally set SOLVE_ADK_CREDENTIALS_PATH to your service account JSON file\n"
                "    (if not using Application Default Credentials via "
                "'gcloud auth application-default login')\n"
                "  - Set SOLVE_ADK_LOCATION to your preferred region (default: us-central1)\n\n"
                "Note: Anthropic API keys (SOLVE_SDK_KEY/SOLVE_API_KEY) are optional "
                "and only needed for autofix/debugger features.",
            )

        # Anthropic keys are optional (only needed for autofix/auto-debugger)
        # No validation needed - autofix will check these separately

        if self.llm_temperature < 0.0 or self.llm_temperature > 2.0:
            raise ConfigurationError(
                f"LLM temperature must be between 0.0 and 2.0, got {self.llm_temperature}",
            )

        if self.llm_max_tokens < 1 or self.llm_max_tokens > 8192:
            raise ConfigurationError(
                f"LLM max tokens must be between 1 and 8192, got {self.llm_max_tokens}",
            )


@dataclass
class AutofixConfig:
    """Autofix system configuration."""

    # Stage 1: Automated fixes
    enable_auto_fixers: bool = True
    max_iterations: int = 5
    max_stuck_iterations: int = 5

    # Ruff settings
    enable_ruff_unsafe_fixes: bool = True
    ruff_timeout: int = 60

    # Stage 2: Validation
    enable_validation: bool = True
    enable_mypy: bool = True
    enable_bandit: bool = True
    enable_pytest: bool = True
    pytest_timeout: int = 300

    # Stage 3: LLM fixes
    enable_llm_fixes: bool = True
    llm_max_retries: int = 3

    # Safety settings
    enable_backups: bool = True
    backup_retention_days: int = 7
    rollback_strategy: RollbackStrategy = RollbackStrategy.ON_SYNTAX_ERROR

    # Interactive mode
    interactive_mode: bool | None = None  # Auto-detect

    def validate(self) -> None:
        """Validate autofix configuration."""
        if self.max_iterations < 1 or self.max_iterations > 20:
            raise ConfigurationError(
                f"Max iterations must be between 1 and 20, got {self.max_iterations}",
            )

        if self.backup_retention_days < 1 or self.backup_retention_days > 365:
            raise ConfigurationError(
                f"Backup retention days must be between 1 and 365, "
                f"got {self.backup_retention_days}",
            )


@dataclass
class DebuggingConfig:
    """Auto-debugger configuration."""

    enable_auto_debugger: bool = True
    max_debug_iterations: int = 10
    enable_verbose_output: bool = False
    keep_partial_fixes: bool = True

    def validate(self) -> None:
        """Validate debugging configuration."""
        if self.max_debug_iterations < 1 or self.max_debug_iterations > 50:
            raise ConfigurationError(
                f"Max debug iterations must be between 1 and 50, got {self.max_debug_iterations}",
            )


@dataclass
class MetricsConfig:
    """Metrics and monitoring configuration."""

    enable_metrics: bool = True
    metrics_retention_days: int = 30
    enable_telemetry: bool = True
    metrics_export_format: str = "json"

    def validate(self) -> None:
        """Validate metrics configuration."""
        if self.metrics_retention_days < 1 or self.metrics_retention_days > 365:
            raise ConfigurationError(
                f"Metrics retention days must be between 1 and 365, "
                f"got {self.metrics_retention_days}",
            )


@dataclass
class PerformanceConfig:
    """Performance and resource configuration."""

    enable_parallel_processing: bool = True
    max_workers: int = 4
    max_file_size_mb: int = 10
    file_encoding: str = "utf-8"

    def validate(self) -> None:
        """Validate performance configuration."""
        if self.max_workers < 1 or self.max_workers > 32:
            raise ConfigurationError(
                f"Max workers must be between 1 and 32, got {self.max_workers}",
            )

        if self.max_file_size_mb < 1 or self.max_file_size_mb > 100:
            raise ConfigurationError(
                f"Max file size must be between 1 and 100 MB, got {self.max_file_size_mb}",
            )


@dataclass
class PathConfig:
    """Path configuration for directories and files."""

    project_root: Path | None = None
    template_dir: Path | None = None
    backup_dir: Path | None = None
    metrics_dir: Path | None = None
    cache_dir: Path | None = None

    def __post_init__(self) -> None:
        """Auto-detect paths if not provided."""
        if self.project_root is None:
            self.project_root = Path.cwd()

        if self.template_dir is None:
            self.template_dir = self.project_root / "templates"

        if self.backup_dir is None:
            self.backup_dir = self.project_root / ".solve" / "backups"

        if self.metrics_dir is None:
            self.metrics_dir = self.project_root / ".solve" / "metrics"

        if self.cache_dir is None:
            self.cache_dir = self.project_root / ".solve" / "cache"


@dataclass
class LoggingConfig:
    """Logging configuration."""

    log_level: LogLevel = LogLevel.INFO
    log_format: LogFormat = LogFormat.SIMPLE
    enable_file_logging: bool = True
    log_file_path: Path | None = None
    log_max_size_mb: int = 10
    log_backup_count: int = 5

    def __post_init__(self) -> None:
        """Set default log file path if not provided."""
        if self.log_file_path is None:
            self.log_file_path = Path.cwd() / ".solve" / "solve.log"

    def validate(self) -> None:
        """Validate logging configuration."""
        if self.log_max_size_mb < 1 or self.log_max_size_mb > 100:
            raise ConfigurationError(
                f"Log max size must be between 1 and 100 MB, got {self.log_max_size_mb}",
            )


@dataclass
class FeatureFlags:
    """Feature flags for experimental features."""

    agent_mode: bool = False
    parallel_validation: bool = False
    experimental_fixes: bool = False
    enhanced_metrics: bool = False

    def validate(self) -> None:
        """Validate feature flags."""
        # All feature flags are boolean, no validation needed
        pass


@dataclass
class SOLVEConfig:
    """Main SOLVE configuration containing all sub-configurations."""

    # Environment
    environment: Environment = Environment.DEVELOPMENT
    dry_run: bool = False

    # Sub-configurations
    api: APIConfig | None = None
    autofix: AutofixConfig | None = None
    debugging: DebuggingConfig | None = None
    metrics: MetricsConfig | None = None
    performance: PerformanceConfig | None = None
    paths: PathConfig | None = None
    logging: LoggingConfig | None = None
    features: FeatureFlags | None = None

    def __post_init__(self) -> None:
        """Initialize sub-configurations if not provided."""
        if self.api is None:
            self.api = APIConfig()
        if self.autofix is None:
            self.autofix = AutofixConfig()
        if self.debugging is None:
            self.debugging = DebuggingConfig()
        if self.metrics is None:
            self.metrics = MetricsConfig()
        if self.performance is None:
            self.performance = PerformanceConfig()
        if self.paths is None:
            self.paths = PathConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.features is None:
            self.features = FeatureFlags()

    def validate(self) -> None:
        """Validate all configuration sections."""
        try:
            if self.api:
                self.api.validate()
            if self.autofix:
                self.autofix.validate()
            if self.debugging:
                self.debugging.validate()
            if self.metrics:
                self.metrics.validate()
            if self.performance:
                self.performance.validate()
            if self.logging:
                self.logging.validate()
            if self.features:
                self.features.validate()
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}") from e


class ConfigurationManager:
    """Manages configuration loading, validation, and access."""

    def __init__(
        self,
        env_file: str | None = None,
        env_override: Environment | None = None,
        schema_path: str | None = None,
    ):
        """
        Initialize configuration manager.

        Args:
            env_file: Path to .env file (defaults to .env)
            env_override: Override environment detection
            schema_path: Path to JSON schema file (defaults to config.schema.json)
        """
        self.env_file = env_file or ".env"
        self.env_override = env_override
        self.schema_path = schema_path or Path(Path.cwd(), "config.schema.json")
        self._config: SOLVEConfig | None = None
        self._schema: dict[str, Any] | None = None
        self._load_environment()
        self._load_schema()

    def _load_environment(self) -> None:
        """Load environment variables from .env file."""
        if Path(self.env_file).exists():
            logger.info(f"Loading environment from {self.env_file}")
            load_dotenv(self.env_file, override=False)
        else:
            logger.info(
                f"No .env file found at {self.env_file}, using environment variables only"
            )

    def _get_env_value(
        self, key: str, default: Any = None, type_converter: Any = str
    ) -> Any:
        """
        Get environment variable with type conversion.

        Args:
            key: Environment variable name
            default: Default value if not found
            type_converter: Function to convert string to desired type

        Returns:
            Converted value or default
        """
        value = os.environ.get(key)
        if value is None:
            return default

        try:
            if type_converter is bool:
                return value.lower() in ("true", "1", "yes", "on", "enabled")
            elif type_converter == Path:
                return Path(value)
            elif issubclass(type_converter, Enum):
                return type_converter(value.upper())
            else:
                return type_converter(value)
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Invalid value '{value}' for {key}, using default {default}: {e}"
            )
            return default

    def _load_schema(self) -> None:
        """Load JSON schema from file."""
        try:
            with open(self.schema_path) as f:
                self._schema = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema from {self.schema_path}: {e}")
            raise ConfigurationError(f"Failed to load schema: {e}") from e

    def _load_json_config(self, env: str) -> dict[str, Any]:
        """Load and merge JSON configuration files."""
        base_path = Path(Path.cwd(), "config.base.json")
        env_path = Path(Path.cwd(), f"config.{env}.json")

        try:
            # Load base config
            with open(base_path) as f:
                config = json.load(f)

            # Load environment config
            with open(env_path) as f:
                env_config = json.load(f)

            # Merge configs
            def deep_merge(
                base: dict[str, Any], update: dict[str, Any]
            ) -> dict[str, Any]:
                for key, value in update.items():
                    if (
                        key in base
                        and isinstance(base[key], dict)
                        and isinstance(value, dict)
                    ):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value
                return base

            config = deep_merge(config, env_config)

            # Validate against schema
            if self._schema:
                try:
                    validate(instance=config, schema=self._schema)
                except ValidationError as e:
                    raise ConfigurationError(
                        f"Configuration validation failed: {e.message}"
                    ) from e

            return config

        except FileNotFoundError as e:
            raise ConfigurationError(
                f"Configuration file not found: {e.filename}"
            ) from e
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}") from e

    def load_config(self) -> SOLVEConfig:
        """Load configuration from environment variables."""
        if self._config is not None:
            return self._config

        # Determine environment
        env_name = self.env_override or self._get_env_value("SOLVE_ENVIRONMENT", "dev")
        environment = Environment(env_name) if isinstance(env_name, str) else env_name

        # Load JSON config
        self._load_json_config(environment.value)

        # Load API configuration
        api_config = APIConfig(
            sdk_key=self._get_env_value("SOLVE_SDK_KEY"),
            api_key=self._get_env_value("SOLVE_API_KEY"),
            adk_project_id=self._get_env_value("SOLVE_ADK_PROJECT_ID"),
            adk_location=self._get_env_value("SOLVE_ADK_LOCATION", "us-central1"),
            adk_credentials_path=self._get_env_value("SOLVE_ADK_CREDENTIALS_PATH"),
            llm_model=self._get_env_value("SOLVE_LLM_MODEL", "gemini-2.0-flash-exp"),
            llm_temperature=self._get_env_value("SOLVE_LLM_TEMPERATURE", 0.2, float),
            llm_max_tokens=self._get_env_value("SOLVE_LLM_MAX_TOKENS", 4096, int),
            llm_timeout=self._get_env_value("SOLVE_LLM_TIMEOUT", 300, int),
            llm_max_retries=self._get_env_value("SOLVE_LLM_MAX_RETRIES", 3, int),
            llm_batch_size=self._get_env_value("SOLVE_LLM_BATCH_SIZE", 10, int),
        )

        # Load autofix configuration
        autofix_config = AutofixConfig(
            enable_auto_fixers=self._get_env_value(
                "SOLVE_ENABLE_AUTO_FIXERS", True, bool
            ),
            max_iterations=self._get_env_value("SOLVE_AUTOFIX_MAX_ITERATIONS", 5, int),
            max_stuck_iterations=self._get_env_value("SOLVE_AUTOFIX_MAX_STUCK", 5, int),
            enable_ruff_unsafe_fixes=self._get_env_value(
                "SOLVE_RUFF_UNSAFE_FIXES", True, bool
            ),
            ruff_timeout=self._get_env_value("SOLVE_RUFF_TIMEOUT", 60, int),
            enable_validation=self._get_env_value(
                "SOLVE_ENABLE_VALIDATION", True, bool
            ),
            enable_mypy=self._get_env_value("SOLVE_ENABLE_MYPY", True, bool),
            enable_bandit=self._get_env_value("SOLVE_ENABLE_BANDIT", True, bool),
            enable_pytest=self._get_env_value("SOLVE_ENABLE_PYTEST", True, bool),
            pytest_timeout=self._get_env_value("SOLVE_PYTEST_TIMEOUT", 300, int),
            enable_llm_fixes=self._get_env_value("SOLVE_ENABLE_LLM_FIXES", True, bool),
            llm_max_retries=self._get_env_value("SOLVE_LLM_MAX_RETRIES", 3, int),
            enable_backups=self._get_env_value("SOLVE_ENABLE_BACKUPS", True, bool),
            backup_retention_days=self._get_env_value(
                "SOLVE_BACKUP_RETENTION_DAYS", 7, int
            ),
            rollback_strategy=self._get_env_value(
                "SOLVE_ROLLBACK_STRATEGY",
                RollbackStrategy.ON_SYNTAX_ERROR,
                RollbackStrategy,
            ),
            interactive_mode=self._get_env_value("SOLVE_INTERACTIVE_MODE", None, bool),
        )

        # Load debugging configuration
        debugging_config = DebuggingConfig(
            enable_auto_debugger=self._get_env_value(
                "SOLVE_ENABLE_AUTO_DEBUGGER", True, bool
            ),
            max_debug_iterations=self._get_env_value(
                "SOLVE_AUTO_DEBUG_MAX_ITERATIONS", 10, int
            ),
            enable_verbose_output=self._get_env_value(
                "SOLVE_DEBUG_VERBOSE", False, bool
            ),
            keep_partial_fixes=self._get_env_value(
                "SOLVE_KEEP_PARTIAL_FIXES", True, bool
            ),
        )

        # Load metrics configuration
        metrics_config = MetricsConfig(
            enable_metrics=self._get_env_value("SOLVE_ENABLE_METRICS", True, bool),
            metrics_retention_days=self._get_env_value(
                "SOLVE_METRICS_RETENTION_DAYS", 30, int
            ),
            enable_telemetry=self._get_env_value("SOLVE_ENABLE_TELEMETRY", True, bool),
            metrics_export_format=self._get_env_value(
                "SOLVE_METRICS_EXPORT_FORMAT", "json"
            ),
        )

        # Load performance configuration
        performance_config = PerformanceConfig(
            enable_parallel_processing=self._get_env_value(
                "SOLVE_ENABLE_PARALLEL", True, bool
            ),
            max_workers=self._get_env_value("SOLVE_MAX_WORKERS", 4, int),
            max_file_size_mb=self._get_env_value("SOLVE_MAX_FILE_SIZE_MB", 10, int),
            file_encoding=self._get_env_value("SOLVE_FILE_ENCODING", "utf-8"),
        )

        # Load path configuration
        paths_config = PathConfig(
            project_root=self._get_env_value("SOLVE_PROJECT_ROOT", None, Path),
            template_dir=self._get_env_value("SOLVE_TEMPLATE_DIR", None, Path),
            backup_dir=self._get_env_value("SOLVE_BACKUP_DIR", None, Path),
            metrics_dir=self._get_env_value("SOLVE_METRICS_DIR", None, Path),
            cache_dir=self._get_env_value("SOLVE_CACHE_DIR", None, Path),
        )

        # Load logging configuration
        logging_config = LoggingConfig(
            log_level=self._get_env_value("SOLVE_LOG_LEVEL", LogLevel.INFO, LogLevel),
            log_format=self._get_env_value(
                "SOLVE_LOG_FORMAT", LogFormat.SIMPLE, LogFormat
            ),
            enable_file_logging=self._get_env_value(
                "SOLVE_ENABLE_FILE_LOGGING", True, bool
            ),
            log_file_path=self._get_env_value("SOLVE_LOG_FILE_PATH", None, Path),
            log_max_size_mb=self._get_env_value("SOLVE_LOG_MAX_SIZE_MB", 10, int),
            log_backup_count=self._get_env_value("SOLVE_LOG_BACKUP_COUNT", 5, int),
        )

        # Load feature flags
        features_config = FeatureFlags(
            agent_mode=self._get_env_value("SOLVE_AGENT_MODE", False, bool),
            parallel_validation=self._get_env_value(
                "SOLVE_PARALLEL_VALIDATION", False, bool
            ),
            experimental_fixes=self._get_env_value(
                "SOLVE_EXPERIMENTAL_FIXES", False, bool
            ),
            enhanced_metrics=self._get_env_value("SOLVE_ENHANCED_METRICS", False, bool),
        )

        # Create main configuration
        self._config = SOLVEConfig(
            environment=environment,
            dry_run=self._get_env_value("SOLVE_DRY_RUN", False, bool),
            api=api_config,
            autofix=autofix_config,
            debugging=debugging_config,
            metrics=metrics_config,
            performance=performance_config,
            paths=paths_config,
            logging=logging_config,
            features=features_config,
        )

        # Validate configuration
        self._config.validate()

        logger.info(
            f"Configuration loaded successfully for {environment.value} environment"
        )
        return self._config

    def get_config(self) -> SOLVEConfig:
        """Get the loaded configuration."""
        if self._config is None:
            return self.load_config()
        return self._config

    def reload_config(self) -> SOLVEConfig:
        """Reload configuration from environment."""
        self._config = None
        self._load_environment()
        return self.load_config()

    def get_secrets_status(self) -> dict[str, bool]:
        """Get status of configured secrets."""
        config = self.get_config()
        if config.api:
            return {
                "sdk_key": config.api.sdk_key is not None,
                "api_key": config.api.api_key is not None,
                "adk_project_id": config.api.adk_project_id is not None,
                "adk_credentials": config.api.adk_credentials_path is not None,
            }
        return {
            "sdk_key": False,
            "api_key": False,
            "adk_project_id": False,
            "adk_credentials": False,
        }

    def validate_required_secrets(self, required_secrets: list[str]) -> None:
        """
        Validate that required secrets are configured.

        Args:
            required_secrets: List of required secret names

        Raises:
            ConfigurationError: If required secrets are missing
        """
        status = self.get_secrets_status()
        missing = [
            secret for secret in required_secrets if not status.get(secret, False)
        ]

        if missing:
            raise ConfigurationError(
                f"Missing required secrets: {', '.join(missing)}. "
                f"Please configure them in your .env file or environment variables.",
            )


# Global configuration manager instance
_config_manager: ConfigurationManager | None = None


def get_config_manager(
    env_file: str | None = None,
    env_override: Environment | None = None,
    schema_path: str | None = None,
) -> ConfigurationManager:
    """Get or create global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(env_file, env_override, schema_path)
    return _config_manager


def get_config() -> SOLVEConfig:
    """Get the current configuration."""
    return get_config_manager().get_config()


def reload_config() -> SOLVEConfig:
    """Reload configuration from environment."""
    return get_config_manager().reload_config()


def validate_secrets(required_secrets: list[str]) -> None:
    """Validate that required secrets are configured."""
    get_config_manager().validate_required_secrets(required_secrets)


# Convenience functions for common configuration access
def get_api_key() -> str | None:
    """Get Anthropic API key if available (SDK key preferred, fallback to API key).

    Returns None if no Anthropic keys are configured (they're optional for autofix only).
    """
    config = get_config()
    if config.api:
        return config.api.sdk_key or config.api.api_key
    return None


def get_llm_config() -> dict[str, Any]:
    """Get LLM configuration as dictionary."""
    config = get_config()
    if config.api:
        return {
            "model": config.api.llm_model,
            "temperature": config.api.llm_temperature,
            "max_tokens": config.api.llm_max_tokens,
            "timeout": config.api.llm_timeout,
            "max_retries": config.api.llm_max_retries,
        }
    return {
        "model": "claude-3-5-haiku-20241022",
        "temperature": 0.2,
        "max_tokens": 4096,
        "timeout": 300,
        "max_retries": 3,
    }


def is_dry_run() -> bool:
    """Check if dry run mode is enabled."""
    return get_config().dry_run


def is_interactive() -> bool:
    """Check if interactive mode is enabled."""
    config = get_config()
    if config.autofix and config.autofix.interactive_mode is not None:
        return config.autofix.interactive_mode

    # Auto-detect: interactive if TTY and not in CI
    import sys

    return sys.stdin.isatty() and not os.environ.get("CI", False)


def get_environment() -> Environment:
    """Get current environment."""
    return get_config().environment


def is_development() -> bool:
    """Check if running in development environment."""
    return get_environment() == Environment.DEVELOPMENT


def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment() == Environment.PRODUCTION


def get_adk_config() -> dict[str, Any]:
    """Get Google ADK configuration.

    Returns:
        Dictionary with ADK configuration settings

    Raises:
        ConfigurationError: If ADK is not properly configured
    """
    config = get_config()
    if not config.api or not config.api.adk_project_id:
        raise ConfigurationError("Google ADK not configured. Set SOLVE_ADK_PROJECT_ID")

    return {
        "project_id": config.api.adk_project_id,
        "location": config.api.adk_location or "us-central1",
        "credentials_path": config.api.adk_credentials_path,
    }


def get_adk_project_id() -> str:
    """Get Google Cloud project ID for ADK.

    Returns:
        Google Cloud project ID

    Raises:
        ConfigurationError: If project ID is not configured
    """
    adk_config = get_adk_config()
    project_id = adk_config["project_id"]
    if not isinstance(project_id, str):
        raise ConfigurationError("ADK project ID must be a string")
    return project_id


def has_anthropic_keys() -> bool:
    """Check if Anthropic API keys are configured.

    Returns:
        True if either SDK key or API key is configured
    """
    config = get_config()
    if config.api:
        return bool(config.api.sdk_key or config.api.api_key)
    return False


def has_adk_config() -> bool:
    """Check if Google ADK is configured.

    Returns:
        True if ADK project ID is configured
    """
    config = get_config()
    if config.api:
        return bool(config.api.adk_project_id)
    return False
