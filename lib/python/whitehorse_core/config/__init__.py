"""
Configuration Module

Pydantic-based configuration management with environment variable support,
validation, and GCP Secret Manager integration.
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

try:
    from pydantic import BaseSettings, Field, validator
    from pydantic.env_settings import SettingsSourceCallable

    HAS_PYDANTIC = True
except ImportError:
    try:
        from pydantic import Field, validator
        from pydantic_settings import BaseSettings

        HAS_PYDANTIC = True
    except ImportError:
        # Fallback implementations when Pydantic is not available
        HAS_PYDANTIC = False

        def Field(default=None, description="", **kwargs):
            """Fallback Field function"""
            return default

        def validator(*args, **kwargs):
            """Fallback validator decorator"""
            def decorator(func):
                return func
            return decorator

        class BaseSettings:
            """Fallback BaseSettings class"""
            pass

try:
    from google.cloud import secretmanager

    HAS_GCP_SECRETS = True
except ImportError:
    HAS_GCP_SECRETS = False

from ..logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound="BaseConfig")


class ConfigError(Exception):
    """Configuration related errors."""

    pass


class BaseConfig(BaseSettings if HAS_PYDANTIC else object):
    """
    Base configuration class with environment variable and secret support.
    """

    # Environment settings
    environment: str = Field(default="dev", description="Deployment environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # GCP settings
    gcp_project: Optional[str] = Field(default=None, description="GCP Project ID")
    gcp_region: str = Field(default="us-central1", description="GCP Region")

    # Service settings
    service_name: str = Field(default="whitehorse-service", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")

    # Health check settings
    health_check_port: int = Field(default=8080, description="Health check port")
    health_check_path: str = Field(default="/health", description="Health check path")

    if HAS_PYDANTIC:

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = False

        @validator("log_level")
        def validate_log_level(cls, v):
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if v.upper() not in valid_levels:
                raise ValueError(f"log_level must be one of: {valid_levels}")
            return v.upper()

        @validator("environment")
        def validate_environment(cls, v):
            valid_envs = ["dev", "test", "staging", "prod"]
            if v.lower() not in valid_envs:
                raise ValueError(f"environment must be one of: {valid_envs}")
            return v.lower()


class DatabaseConfig(BaseConfig):
    """Database configuration."""

    # Database connection
    db_host: str = Field(..., description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(..., description="Database name")
    db_user: str = Field(..., description="Database user")
    db_password: str = Field(..., description="Database password")
    db_ssl_mode: str = Field(default="prefer", description="SSL mode")

    # Connection pool settings
    db_pool_size: int = Field(default=10, description="Connection pool size")
    db_max_overflow: int = Field(default=20, description="Max pool overflow")
    db_pool_timeout: int = Field(default=30, description="Pool timeout seconds")

    @property
    def database_url(self) -> str:
        """Get database connection URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?sslmode={self.db_ssl_mode}"


class RedisConfig(BaseConfig):
    """Redis configuration."""

    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_ssl: bool = Field(default=False, description="Use SSL for Redis")

    # Connection pool settings
    redis_max_connections: int = Field(default=10, description="Max Redis connections")
    redis_socket_timeout: int = Field(default=5, description="Socket timeout seconds")

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        scheme = "rediss" if self.redis_ssl else "redis"
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"{scheme}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


class APIConfig(BaseConfig):
    """API configuration."""

    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")
    api_timeout: int = Field(default=30, description="API timeout seconds")

    # CORS settings
    cors_origins: str = Field(default="*", description="CORS allowed origins")
    cors_methods: str = Field(default="*", description="CORS allowed methods")
    cors_headers: str = Field(default="*", description="CORS allowed headers")

    # Security
    api_key: Optional[str] = Field(
        default=None, description="API key for authentication"
    )
    jwt_secret: Optional[str] = Field(default=None, description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiry: int = Field(default=3600, description="JWT expiry seconds")


class SecretManager:
    """
    GCP Secret Manager integration for configuration values.
    """

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.environ.get("GCP_PROJECT")
        self.client = None

        if HAS_GCP_SECRETS and self.project_id:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
                logger.info(
                    "Initialized GCP Secret Manager client", project=self.project_id
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Secret Manager: {e}")

    def get_secret(self, secret_name: str, version: str = "latest") -> Optional[str]:
        """
        Retrieve a secret from GCP Secret Manager.

        Args:
            secret_name: Name of the secret
            version: Version of the secret (default: latest)

        Returns:
            Secret value or None if not found
        """
        if not self.client or not self.project_id:
            logger.warning("Secret Manager not available", secret=secret_name)
            return None

        try:
            name = (
                f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            )
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            logger.info("Retrieved secret from Secret Manager", secret=secret_name)
            return secret_value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            return None


class Config:
    """
    Main configuration manager with multiple sources and validation.
    """

    def __init__(self, config_class: Type[T] = BaseConfig, **kwargs) -> None:
        self.config_class = config_class
        self.secret_manager = SecretManager(kwargs.get("gcp_project"))
        self._config_cache: Dict[Type, Any] = {}

    def load(self, **overrides) -> T:
        """
        Load configuration with multiple sources in priority order:
        1. Keyword arguments
        2. Environment variables
        3. GCP Secret Manager
        4. Configuration files
        5. Default values
        """
        if self.config_class in self._config_cache:
            return self._config_cache[self.config_class]

        # Load from various sources
        config_data = {}

        # Load from files
        config_data.update(self._load_from_files())

        # Load from Secret Manager
        config_data.update(self._load_from_secrets())

        # Environment variables and overrides are handled by Pydantic
        try:
            if HAS_PYDANTIC:
                config = self.config_class(**{**config_data, **overrides})
            else:
                # Fallback for when Pydantic is not available
                config = self._create_simple_config(config_data, overrides)

            self._config_cache[self.config_class] = config
            logger.info(
                "Configuration loaded successfully",
                config_class=self.config_class.__name__,
            )
            return config

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigError(f"Configuration validation failed: {e}")

    def _load_from_files(self) -> Dict[str, Any]:
        """Load configuration from JSON/YAML files."""
        config_data = {}

        # Check for config files in standard locations
        config_files = [
            Path("config.json"),
            Path("config.yaml"),
            Path("config.yml"),
            Path(".config/config.json"),
            Path("configs/config.json"),
        ]

        for config_file in config_files:
            if config_file.exists():
                try:
                    if config_file.suffix == ".json":
                        with open(config_file) as f:
                            file_config = json.load(f)
                    elif config_file.suffix in [".yaml", ".yml"]:
                        try:
                            import yaml

                            with open(config_file) as f:
                                file_config = yaml.safe_load(f)
                        except ImportError:
                            logger.warning("PyYAML not available, skipping YAML config")
                            continue
                    else:
                        continue

                    config_data.update(file_config)
                    logger.info(f"Loaded configuration from {config_file}")
                    break  # Use first found config file
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_file}: {e}")

        return config_data

    def _load_from_secrets(self) -> Dict[str, Any]:
        """Load sensitive configuration from GCP Secret Manager."""
        config_data = {}

        if not self.secret_manager.client:
            return config_data

        # Common secret names to check
        secret_mappings = {
            "db-password": "db_password",
            "api-key": "api_key",
            "jwt-secret": "jwt_secret",
            "redis-password": "redis_password",
        }

        for secret_name, config_key in secret_mappings.items():
            secret_value = self.secret_manager.get_secret(secret_name)
            if secret_value:
                config_data[config_key] = secret_value

        return config_data

    def _create_simple_config(self, config_data: Dict, overrides: Dict) -> Any:
        """Create simple config object when Pydantic is not available."""

        class SimpleConfig:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        all_data = {**config_data, **overrides}
        return SimpleConfig(**all_data)

    def reload(self) -> T:
        """Reload configuration from sources."""
        self._config_cache.clear()
        return self.load()


# Global config instance
_global_config = Config()


def get_config(config_class: Type[T] = BaseConfig, **overrides) -> T:
    """
    Get configuration instance.

    Args:
        config_class: Configuration class to use
        **overrides: Override values

    Returns:
        Configuration instance
    """
    if config_class != BaseConfig:
        # Create new instance for custom config classes
        config_manager = Config(config_class)
        return config_manager.load(**overrides)

    return _global_config.load(**overrides)


def reload_config():
    """Reload global configuration."""
    _global_config.reload()
