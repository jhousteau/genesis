#!/usr/bin/env python3
"""
Configuration Manager - Unified Configuration Management System
Manages configuration for all platform components with hot-reload and validation
"""

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import yaml
from jsonschema import ValidationError, validate
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class ConfigFormat(Enum):
    """Supported configuration formats"""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    ENV = "env"
    INI = "ini"


class ConfigScope(Enum):
    """Configuration scopes"""

    GLOBAL = "global"  # Platform-wide configuration
    COMPONENT = "component"  # Component-specific configuration
    PROJECT = "project"  # Project-specific configuration
    ENVIRONMENT = "environment"  # Environment-specific (dev, staging, prod)
    USER = "user"  # User-specific configuration


@dataclass
class ConfigSource:
    """Represents a configuration source"""

    path: str
    format: ConfigFormat
    scope: ConfigScope
    priority: int = 0  # Higher priority overrides lower
    watch: bool = False  # Enable file watching for changes
    schema_path: Optional[str] = None
    description: str = ""

    def load(self) -> Dict[str, Any]:
        """Load configuration from source"""
        if not os.path.exists(self.path):
            return {}

        with open(self.path, "r") as f:
            if self.format == ConfigFormat.JSON:
                return json.load(f)
            elif self.format == ConfigFormat.YAML:
                return yaml.safe_load(f) or {}
            elif self.format == ConfigFormat.ENV:
                return self._load_env_file(f)
            elif self.format == ConfigFormat.INI:
                return self._load_ini_file(f)
            elif self.format == ConfigFormat.TOML:
                try:
                    import toml

                    return toml.load(f)
                except ImportError:
                    logger.error("toml library not installed")
                    return {}
        return {}

    def _load_env_file(self, file) -> Dict[str, Any]:
        """Load .env file format"""
        config = {}
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
        return config

    def _load_ini_file(self, file) -> Dict[str, Any]:
        """Load INI file format"""
        import configparser

        parser = configparser.ConfigParser()
        parser.read_file(file)

        config = {}
        for section in parser.sections():
            config[section] = dict(parser[section])
        return config

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate configuration against schema if provided"""
        if not self.schema_path or not os.path.exists(self.schema_path):
            return True

        try:
            with open(self.schema_path, "r") as f:
                schema = json.load(f)
            validate(instance=data, schema=schema)
            return True
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return True  # Pass if schema cannot be loaded


@dataclass
class ConfigValue:
    """Represents a configuration value with metadata"""

    key: str
    value: Any
    scope: ConfigScope
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    encrypted: bool = False
    sensitive: bool = False

    def get_decrypted(self) -> Any:
        """Get decrypted value if encrypted"""
        if not self.encrypted:
            return self.value

        # Implement decryption logic here
        # For now, return as-is
        return self.value


class ConfigWatcher(FileSystemEventHandler):
    """Watches configuration files for changes"""

    def __init__(self, config_manager: "ConfigManager"):
        self.config_manager = config_manager
        self.debounce_timers = {}

    def on_modified(self, event):
        if event.is_directory:
            return

        # Debounce rapid changes
        if event.src_path in self.debounce_timers:
            self.debounce_timers[event.src_path].cancel()

        timer = threading.Timer(
            0.5,  # Wait 500ms before reloading
            self._reload_config,
            args=[event.src_path],
        )
        self.debounce_timers[event.src_path] = timer
        timer.start()

    def _reload_config(self, path: str):
        """Reload configuration from changed file"""
        logger.info(f"Configuration file changed: {path}")
        self.config_manager.reload_source(path)


class ConfigManager:
    """
    Unified configuration management for all platform components
    Features:
    - Multiple configuration sources with priority
    - Hot-reload on configuration changes
    - Schema validation
    - Environment variable substitution
    - Encrypted values support
    - Configuration inheritance and overrides
    """

    def __init__(self, base_path: Optional[str] = None):
        """Initialize configuration manager"""
        self.base_path = base_path or "/Users/jameshousteau/source_code/bootstrapper"
        self.sources: Dict[str, ConfigSource] = {}
        self.config_cache: Dict[str, ConfigValue] = {}
        self.config_lock = threading.RLock()
        self.listeners: Dict[str, List[Callable]] = {}

        # File watching
        self.observer = Observer()
        self.watcher = ConfigWatcher(self)
        self.watched_paths: Set[str] = set()

        # Configuration defaults
        self.defaults: Dict[str, Any] = {}

        # Initialize default sources
        self._initialize_default_sources()

        # Load all configurations
        self.reload_all()

        # Start file watching
        self.observer.start()

    def _initialize_default_sources(self):
        """Initialize default configuration sources"""
        # Global configuration
        self.add_source(
            ConfigSource(
                path=os.path.join(self.base_path, "config", "global.yaml"),
                format=ConfigFormat.YAML,
                scope=ConfigScope.GLOBAL,
                priority=0,
                watch=True,
                description="Global platform configuration",
            )
        )

        # Environment configurations
        for env in ["development", "staging", "production"]:
            env_path = os.path.join(
                self.base_path, "config", "environments", f"{env}.yaml"
            )
            if os.path.exists(env_path):
                self.add_source(
                    ConfigSource(
                        path=env_path,
                        format=ConfigFormat.YAML,
                        scope=ConfigScope.ENVIRONMENT,
                        priority=10,
                        watch=True,
                        description=f"{env.capitalize()} environment configuration",
                    )
                )

        # Component configurations
        components_dir = os.path.join(self.base_path, "config", "components")
        if os.path.exists(components_dir):
            for config_file in Path(components_dir).glob("*.yaml"):
                self.add_source(
                    ConfigSource(
                        path=str(config_file),
                        format=ConfigFormat.YAML,
                        scope=ConfigScope.COMPONENT,
                        priority=5,
                        watch=True,
                        description=f"Component configuration: {config_file.stem}",
                    )
                )

        # User configuration (highest priority)
        user_config = os.path.expanduser("~/.bootstrapper/config.yaml")
        if os.path.exists(user_config):
            self.add_source(
                ConfigSource(
                    path=user_config,
                    format=ConfigFormat.YAML,
                    scope=ConfigScope.USER,
                    priority=100,
                    watch=True,
                    description="User-specific configuration",
                )
            )

    def add_source(self, source: ConfigSource) -> str:
        """Add a configuration source"""
        source_id = hashlib.md5(source.path.encode()).hexdigest()[:8]

        with self.config_lock:
            self.sources[source_id] = source

            # Setup file watching if requested
            if source.watch and os.path.exists(source.path):
                self._setup_watching(source.path)

        # Load configuration from source
        self._load_source(source)

        logger.info(f"Added configuration source: {source.path}")
        return source_id

    def remove_source(self, source_id: str) -> bool:
        """Remove a configuration source"""
        with self.config_lock:
            if source_id not in self.sources:
                return False

            source = self.sources[source_id]

            # Stop watching if needed
            if source.path in self.watched_paths:
                self.watched_paths.remove(source.path)

            # Remove cached values from this source
            keys_to_remove = [
                key
                for key, value in self.config_cache.items()
                if value.source == source_id
            ]
            for key in keys_to_remove:
                del self.config_cache[key]

            del self.sources[source_id]

        logger.info(f"Removed configuration source: {source_id}")
        return True

    def _setup_watching(self, path: str):
        """Setup file watching for a path"""
        if path in self.watched_paths:
            return

        directory = os.path.dirname(path)
        if os.path.exists(directory):
            try:
                self.observer.schedule(self.watcher, directory, recursive=False)
                self.watched_paths.add(path)
            except Exception as e:
                # Directory might already be watched, which is fine
                logger.debug(f"File watching setup warning for {directory}: {e}")
                self.watched_paths.add(path)

    def _load_source(self, source: ConfigSource):
        """Load configuration from a source"""
        try:
            data = source.load()

            # Validate if schema provided
            if source.schema_path and not source.validate(data):
                logger.error(f"Configuration validation failed for {source.path}")
                return

            # Process and cache configuration values
            self._process_config_data(data, source)

        except Exception as e:
            logger.error(f"Failed to load configuration from {source.path}: {e}")

    def _process_config_data(
        self, data: Dict[str, Any], source: ConfigSource, prefix: str = ""
    ):
        """Process and cache configuration data"""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            # Handle nested dictionaries
            if isinstance(value, dict) and not self._is_leaf_value(value):
                self._process_config_data(value, source, full_key)
            else:
                # Perform variable substitution
                if isinstance(value, str):
                    value = self._substitute_variables(value)

                # Create config value
                config_value = ConfigValue(
                    key=full_key,
                    value=value,
                    scope=source.scope,
                    source=hashlib.md5(source.path.encode()).hexdigest()[:8],
                    sensitive=self._is_sensitive(full_key),
                )

                # Cache based on priority
                with self.config_lock:
                    if full_key not in self.config_cache:
                        self.config_cache[full_key] = config_value
                    else:
                        # Override if higher priority
                        existing_source = self.sources.get(
                            self.config_cache[full_key].source
                        )
                        if (
                            existing_source
                            and source.priority > existing_source.priority
                        ):
                            old_value = self.config_cache[full_key].value
                            self.config_cache[full_key] = config_value

                            # Notify listeners of change
                            if old_value != value:
                                self._notify_change(full_key, old_value, value)

    def _is_leaf_value(self, value: Dict) -> bool:
        """Check if dictionary is a leaf value (not nested config)"""
        # Consider it a leaf if it has special keys
        special_keys = {"$ref", "$encrypt", "$env", "$file"}
        return any(key in value for key in special_keys)

    def _is_sensitive(self, key: str) -> bool:
        """Check if configuration key contains sensitive data"""
        sensitive_patterns = [
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "api_key",
            "private",
            "cert",
            "ssl",
        ]
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in sensitive_patterns)

    def _substitute_variables(self, value: str) -> str:
        """Substitute environment variables and references"""
        import re

        # Environment variable substitution ${ENV_VAR}
        env_pattern = re.compile(r"\$\{([^}]+)\}")

        def env_replace(match):
            env_var = match.group(1)
            # Support default values ${VAR:-default}
            if ":-" in env_var:
                var_name, default = env_var.split(":-", 1)
                return os.environ.get(var_name, default)
            return os.environ.get(env_var, match.group(0))

        value = env_pattern.sub(env_replace, value)

        # Configuration reference substitution {{config.key}}
        ref_pattern = re.compile(r"\{\{([^}]+)\}\}")

        def ref_replace(match):
            ref_key = match.group(1)
            ref_value = self.get(ref_key)
            return str(ref_value) if ref_value is not None else match.group(0)

        value = ref_pattern.sub(ref_replace, value)

        return value

    def get(
        self, key: str, default: Any = None, scope: Optional[ConfigScope] = None
    ) -> Any:
        """Get configuration value"""
        with self.config_lock:
            # Direct lookup
            if key in self.config_cache:
                config_value = self.config_cache[key]
                if scope is None or config_value.scope == scope:
                    return config_value.get_decrypted()

            # Try with wildcards (e.g., "component.*")
            for cached_key, config_value in self.config_cache.items():
                if self._key_matches(key, cached_key):
                    if scope is None or config_value.scope == scope:
                        return config_value.get_decrypted()

        # Check defaults
        if key in self.defaults:
            return self.defaults[key]

        return default

    def set(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.GLOBAL,
        persist: bool = False,
    ):
        """Set configuration value"""
        config_value = ConfigValue(
            key=key,
            value=value,
            scope=scope,
            source="runtime",
            sensitive=self._is_sensitive(key),
        )

        with self.config_lock:
            old_value = self.config_cache.get(key)
            self.config_cache[key] = config_value

        # Notify listeners
        if old_value and old_value.value != value:
            self._notify_change(key, old_value.value, value)

        # Persist if requested
        if persist:
            self._persist_value(key, value, scope)

    def _persist_value(self, key: str, value: Any, scope: ConfigScope):
        """Persist configuration value to appropriate source"""
        # Find appropriate source for scope
        target_source = None
        for source in self.sources.values():
            if source.scope == scope:
                target_source = source
                break

        if not target_source:
            logger.warning(f"No source found for scope {scope}")
            return

        try:
            # Load existing data
            data = target_source.load() if os.path.exists(target_source.path) else {}

            # Set nested value
            keys = key.split(".")
            current = data
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value

            # Save back
            os.makedirs(os.path.dirname(target_source.path), exist_ok=True)
            with open(target_source.path, "w") as f:
                if target_source.format == ConfigFormat.JSON:
                    json.dump(data, f, indent=2)
                elif target_source.format == ConfigFormat.YAML:
                    yaml.dump(data, f, default_flow_style=False)

            logger.info(f"Persisted {key} to {target_source.path}")

        except Exception as e:
            logger.error(f"Failed to persist configuration: {e}")

    def get_all(
        self, prefix: str = "", scope: Optional[ConfigScope] = None
    ) -> Dict[str, Any]:
        """Get all configuration values with optional prefix filter"""
        result = {}

        with self.config_lock:
            for key, config_value in self.config_cache.items():
                if prefix and not key.startswith(prefix):
                    continue
                if scope and config_value.scope != scope:
                    continue

                # Build nested dictionary
                keys = key.split(".")
                current = result
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                current[keys[-1]] = config_value.get_decrypted()

        return result

    def reload_all(self):
        """Reload all configuration sources"""
        with self.config_lock:
            self.config_cache.clear()

            # Load sources in priority order
            sorted_sources = sorted(self.sources.values(), key=lambda s: s.priority)

            for source in sorted_sources:
                self._load_source(source)

        logger.info("Reloaded all configuration sources")
        self._notify_change("*", None, None)

    def reload_source(self, path: str):
        """Reload configuration from a specific source"""
        source_to_reload = None
        for source in self.sources.values():
            if source.path == path:
                source_to_reload = source
                break

        if source_to_reload:
            # Remove old values from this source
            source_id = hashlib.md5(path.encode()).hexdigest()[:8]
            with self.config_lock:
                keys_to_remove = [
                    key
                    for key, value in self.config_cache.items()
                    if value.source == source_id
                ]
                for key in keys_to_remove:
                    del self.config_cache[key]

            # Reload
            self._load_source(source_to_reload)
            logger.info(f"Reloaded configuration from {path}")
            self._notify_change(f"source:{path}", None, None)

    def add_listener(self, pattern: str, callback: Callable):
        """Add configuration change listener"""
        if pattern not in self.listeners:
            self.listeners[pattern] = []
        self.listeners[pattern].append(callback)

    def remove_listener(self, pattern: str, callback: Callable):
        """Remove configuration change listener"""
        if pattern in self.listeners:
            self.listeners[pattern].remove(callback)

    def _notify_change(self, key: str, old_value: Any, new_value: Any):
        """Notify listeners of configuration change"""
        for pattern, callbacks in self.listeners.items():
            if self._key_matches(pattern, key) or pattern == "*":
                for callback in callbacks:
                    try:
                        callback(key, old_value, new_value)
                    except Exception as e:
                        logger.error(f"Listener error: {e}")

    def _key_matches(self, pattern: str, key: str) -> bool:
        """Check if key matches pattern"""
        if pattern == "*":
            return True
        if pattern == key:
            return True
        if pattern.endswith("*"):
            return key.startswith(pattern[:-1])
        return False

    def export(self, format: ConfigFormat = ConfigFormat.YAML) -> str:
        """Export current configuration"""
        data = self.get_all()

        if format == ConfigFormat.JSON:
            return json.dumps(data, indent=2)
        elif format == ConfigFormat.YAML:
            return yaml.dump(data, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def validate_all(self) -> Dict[str, List[str]]:
        """Validate all configuration sources"""
        errors = {}

        for source_id, source in self.sources.items():
            if source.schema_path:
                try:
                    data = source.load()
                    if not source.validate(data):
                        errors[source.path] = ["Validation failed"]
                except Exception as e:
                    errors[source.path] = [str(e)]

        return errors

    def get_metadata(self) -> Dict[str, Any]:
        """Get configuration metadata"""
        return {
            "timestamp": datetime.now().isoformat(),
            "sources": [
                {
                    "path": source.path,
                    "format": source.format.value,
                    "scope": source.scope.value,
                    "priority": source.priority,
                    "watch": source.watch,
                    "exists": os.path.exists(source.path),
                }
                for source in self.sources.values()
            ],
            "total_keys": len(self.config_cache),
            "scopes": list(set(v.scope.value for v in self.config_cache.values())),
            "watched_paths": list(self.watched_paths),
        }

    def shutdown(self):
        """Shutdown configuration manager"""
        self.observer.stop()
        self.observer.join()
        logger.info("Configuration manager shutdown complete")


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config(key: str, default: Any = None) -> Any:
    """Convenience function to get configuration value"""
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any, persist: bool = False):
    """Convenience function to set configuration value"""
    get_config_manager().set(key, value, persist=persist)
