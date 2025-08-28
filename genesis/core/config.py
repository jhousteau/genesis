"""Lightweight configuration management with YAML and environment variables."""

import os
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from .errors import ResourceError, ValidationError, handle_error


class ConfigLoader:
    """Simple configuration loader supporting YAML files and env var overrides."""

    def __init__(self, env_prefix: str = ""):
        """Initialize config loader.

        Args:
            env_prefix: Prefix for environment variables (e.g., "APP_")
        """
        self.env_prefix = env_prefix.upper()
        self._config: dict[str, Any] = {}

    def load_file(self, file_path: Union[str, Path]) -> dict[str, Any]:
        """Load configuration from YAML file."""
        path = Path(file_path)
        if not path.exists():
            return {}

        try:
            with open(path) as f:
                content = yaml.safe_load(f) or {}
                if not isinstance(content, dict):
                    raise ValidationError(
                        f"Configuration file must contain a YAML dictionary, got {type(content).__name__}"
                    )
                return content
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML in configuration file {path}: {e}")
        except Exception as e:
            handled_error = handle_error(e)
            raise ResourceError(
                f"Failed to load configuration file {path}: {handled_error.message}",
                resource_type="config_file",
            )

    def load_env(self, config: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides to config."""
        result = config.copy()

        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(self.env_prefix) :].lower()

                # Convert common string values to appropriate types
                if value.lower() in ("true", "false"):
                    result[config_key] = value.lower() == "true"
                elif value.isdigit():
                    result[config_key] = int(value)
                else:
                    try:
                        # Try float conversion
                        result[config_key] = float(value)
                    except ValueError:
                        result[config_key] = value

        return result

    def load(
        self,
        file_path: Optional[Union[str, Path]] = None,
        defaults: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Load configuration with precedence: defaults < file < environment.

        Args:
            file_path: Path to YAML config file
            defaults: Default configuration values

        Returns:
            Merged configuration dictionary
        """
        config = defaults or {}

        # Load from file if provided
        if file_path:
            file_config = self.load_file(file_path)
            config.update(file_config)

        # Apply environment overrides
        config = self.load_env(config)

        self._config = config
        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self._config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access to config values."""
        return self._config[key]


def load_config(
    file_path: Optional[Union[str, Path]] = None,
    env_prefix: str = "",
    defaults: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Simple function interface for loading configuration.

    Args:
        file_path: Path to YAML config file
        env_prefix: Prefix for environment variables
        defaults: Default configuration values

    Usage:
        config = load_config("config.yml", env_prefix="APP_")
        database_url = config.get("database_url", "sqlite:///default.db")
    """
    loader = ConfigLoader(env_prefix)
    return loader.load(file_path, defaults)
