#!/usr/bin/env python3

"""
Unified Configuration Management for Bootstrapper
Centralized configuration system for all components and environments
"""

import copy
import json
import logging
import os
import re
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class ConfigSource:
    """Represents a configuration source"""

    name: str
    type: str  # 'file', 'env', 'cli', 'api', 'default'
    path: Optional[str] = None
    priority: int = 0  # Higher number = higher priority
    data: Dict[str, Any] = field(default_factory=dict)
    last_modified: Optional[str] = None


@dataclass
class ConfigValidationRule:
    """Configuration validation rule"""

    path: str  # Dot notation path like 'database.host'
    rule_type: str  # 'required', 'type', 'range', 'regex', 'custom'
    parameters: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


class ConfigurationManager:
    """Unified configuration management system"""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or self._find_base_path()
        self.config_sources: List[ConfigSource] = []
        self.merged_config: Dict[str, Any] = {}
        self.validation_rules: List[ConfigValidationRule] = []
        self.environment = os.getenv("BOOTSTRAPPER_ENV", "development")
        self.logger = self._setup_logging()
        self.config_lock = threading.RLock()
        self.watchers = []  # Config change watchers

        # Initialize configuration
        self._load_default_config()
        self._load_validation_rules()
        self._discover_config_sources()
        self._merge_configurations()

    def _find_base_path(self) -> str:
        """Find the base path for configuration files"""
        possible_paths = [
            "/Users/jameshousteau/source_code/bootstrapper",
            os.path.dirname(os.path.dirname(__file__)),
            os.getcwd(),
        ]

        for path in possible_paths:
            config_dir = os.path.join(path, "config")
            if os.path.exists(config_dir):
                return path

        # Create config directory if none found
        base_path = os.path.dirname(os.path.dirname(__file__))
        os.makedirs(os.path.join(base_path, "config"), exist_ok=True)
        return base_path

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for configuration management"""
        logger = logging.getLogger("unified_config")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _load_default_config(self):
        """Load default configuration values"""
        default_config = {
            "system": {
                "name": "bootstrapper",
                "version": "1.0.0",
                "environment": self.environment,
                "debug": False,
                "log_level": "INFO",
            },
            "intelligence": {
                "enabled": True,
                "auto_fix": {
                    "enabled": True,
                    "auto_execute": False,
                    "max_retries": 3,
                    "timeout": 300,
                },
                "optimization": {
                    "enabled": True,
                    "analysis_interval": 3600,
                    "cost_threshold": 100,
                },
                "predictions": {
                    "enabled": True,
                    "confidence_threshold": 0.7,
                    "forecast_horizon": 30,
                },
                "recommendations": {
                    "enabled": True,
                    "priority_filter": "medium",
                    "max_recommendations": 20,
                },
                "self_healing": {
                    "enabled": True,
                    "monitoring_interval": 60,
                    "auto_heal_enabled": True,
                    "max_healing_attempts": 3,
                },
            },
            "coordination": {
                "enabled": True,
                "coordination_interval": 30,
                "health_check_interval": 60,
                "max_concurrent_tasks": 5,
                "task_timeout": 300,
                "auto_resolve_conflicts": True,
            },
            "deployment": {
                "default_strategy": "rolling",
                "timeout": 1800,
                "rollback_enabled": True,
                "validation_enabled": True,
                "pre_deploy_checks": True,
            },
            "governance": {
                "compliance_enabled": True,
                "policy_enforcement": "strict",
                "audit_logging": True,
                "cost_monitoring": True,
            },
            "isolation": {
                "gcp_isolation": True,
                "credential_rotation": True,
                "policy_validation": True,
            },
            "monitoring": {
                "metrics_enabled": True,
                "logging_enabled": True,
                "tracing_enabled": True,
                "alerting_enabled": True,
                "retention_days": 30,
            },
            "security": {
                "authentication_required": True,
                "authorization_enabled": True,
                "encryption_at_rest": True,
                "encryption_in_transit": True,
                "vulnerability_scanning": True,
            },
            "performance": {
                "caching_enabled": True,
                "compression_enabled": True,
                "async_processing": True,
                "connection_pooling": True,
            },
            "integrations": {
                "github_enabled": False,
                "gitlab_enabled": False,
                "slack_enabled": False,
                "pagerduty_enabled": False,
            },
        }

        source = ConfigSource(
            name="default",
            type="default",
            priority=0,
            data=default_config,
            last_modified=datetime.now().isoformat(),
        )

        self.config_sources.append(source)

    def _load_validation_rules(self):
        """Load configuration validation rules"""
        rules = [
            # System validation
            ConfigValidationRule(
                path="system.name",
                rule_type="required",
                error_message="System name is required",
            ),
            ConfigValidationRule(
                path="system.environment",
                rule_type="regex",
                parameters={"pattern": r"^(development|staging|production)$"},
                error_message="Environment must be development, staging, or production",
            ),
            # Intelligence validation
            ConfigValidationRule(
                path="intelligence.auto_fix.timeout",
                rule_type="range",
                parameters={"min": 60, "max": 3600},
                error_message="Auto-fix timeout must be between 60 and 3600 seconds",
            ),
            ConfigValidationRule(
                path="intelligence.predictions.confidence_threshold",
                rule_type="range",
                parameters={"min": 0.0, "max": 1.0},
                error_message="Confidence threshold must be between 0.0 and 1.0",
            ),
            # Coordination validation
            ConfigValidationRule(
                path="coordination.max_concurrent_tasks",
                rule_type="range",
                parameters={"min": 1, "max": 20},
                error_message="Max concurrent tasks must be between 1 and 20",
            ),
            # Security validation
            ConfigValidationRule(
                path="security.authentication_required",
                rule_type="type",
                parameters={"expected_type": bool},
                error_message="Authentication required must be a boolean",
            ),
            # Performance validation
            ConfigValidationRule(
                path="monitoring.retention_days",
                rule_type="range",
                parameters={"min": 1, "max": 365},
                error_message="Retention days must be between 1 and 365",
            ),
        ]

        self.validation_rules.extend(rules)

    def _discover_config_sources(self):
        """Discover all configuration sources"""
        config_dir = os.path.join(self.base_path, "config")

        # 1. Global configuration file
        global_config_path = os.path.join(config_dir, "global.yaml")
        if os.path.exists(global_config_path):
            self._load_file_config(global_config_path, "global", priority=10)

        # 2. Component-specific configuration files
        components_dir = os.path.join(config_dir, "components")
        if os.path.exists(components_dir):
            for component_file in os.listdir(components_dir):
                if component_file.endswith((".yaml", ".yml", ".json")):
                    component_path = os.path.join(components_dir, component_file)
                    component_name = os.path.splitext(component_file)[0]
                    self._load_file_config(
                        component_path, f"component_{component_name}", priority=20
                    )

        # 3. Environment-specific configuration
        env_config_path = os.path.join(
            config_dir, "environments", f"{self.environment}.yaml"
        )
        if os.path.exists(env_config_path):
            self._load_file_config(
                env_config_path, f"environment_{self.environment}", priority=30
            )

        # 4. Environment variables
        self._load_environment_variables(priority=40)

        # 5. Command line arguments (if available)
        self._load_cli_arguments(priority=50)

        self.logger.info(f"Discovered {len(self.config_sources)} configuration sources")

    def _load_file_config(self, file_path: str, source_name: str, priority: int):
        """Load configuration from a file"""
        try:
            with open(file_path, "r") as f:
                if file_path.endswith(".json"):
                    data = json.load(f)
                else:  # YAML
                    data = yaml.safe_load(f)

            source = ConfigSource(
                name=source_name,
                type="file",
                path=file_path,
                priority=priority,
                data=data or {},
                last_modified=datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).isoformat(),
            )

            self.config_sources.append(source)
            self.logger.debug(f"Loaded configuration from {file_path}")

        except Exception as e:
            self.logger.error(f"Failed to load configuration from {file_path}: {e}")

    def _load_environment_variables(self, priority: int):
        """Load configuration from environment variables"""
        env_config = {}

        # Look for environment variables with BOOTSTRAPPER_ prefix
        for key, value in os.environ.items():
            if key.startswith("BOOTSTRAPPER_"):
                # Convert BOOTSTRAPPER_INTELLIGENCE_AUTO_FIX_ENABLED to intelligence.auto_fix.enabled
                config_key = (
                    key[13:].lower().replace("_", ".")
                )  # Remove BOOTSTRAPPER_ prefix

                # Try to parse value as appropriate type
                parsed_value = self._parse_env_value(value)
                self._set_nested_value(env_config, config_key, parsed_value)

        if env_config:
            source = ConfigSource(
                name="environment",
                type="env",
                priority=priority,
                data=env_config,
                last_modified=datetime.now().isoformat(),
            )

            self.config_sources.append(source)
            self.logger.debug(f"Loaded {len(env_config)} environment variables")

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type"""
        # Try boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Try JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass

        # Return as string
        return value

    def _set_nested_value(self, config: Dict[str, Any], key_path: str, value: Any):
        """Set a nested value in configuration using dot notation"""
        keys = key_path.split(".")
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _load_cli_arguments(self, priority: int):
        """Load configuration from command line arguments"""
        # This would parse sys.argv for configuration overrides
        # For now, we'll skip this implementation
        pass

    def _merge_configurations(self):
        """Merge all configuration sources based on priority"""
        with self.config_lock:
            # Sort sources by priority (higher priority overrides lower)
            sorted_sources = sorted(self.config_sources, key=lambda s: s.priority)

            merged = {}
            for source in sorted_sources:
                merged = self._deep_merge(merged, source.data)

            self.merged_config = merged
            self.logger.info("Configuration merged successfully")

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = copy.deepcopy(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)

        return result

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        try:
            keys = key_path.split(".")
            current = self.merged_config

            for key in keys:
                current = current[key]

            return current

        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any, source_name: str = "runtime"):
        """Set configuration value using dot notation"""
        with self.config_lock:
            # Find or create runtime source
            runtime_source = None
            for source in self.config_sources:
                if source.name == source_name:
                    runtime_source = source
                    break

            if not runtime_source:
                runtime_source = ConfigSource(
                    name=source_name,
                    type="runtime",
                    priority=60,  # High priority for runtime changes
                    data={},
                    last_modified=datetime.now().isoformat(),
                )
                self.config_sources.append(runtime_source)

            # Set the value in the runtime source
            self._set_nested_value(runtime_source.data, key_path, value)
            runtime_source.last_modified = datetime.now().isoformat()

            # Re-merge configurations
            self._merge_configurations()

            # Notify watchers
            self._notify_watchers(key_path, value)

    def validate(self) -> List[str]:
        """Validate current configuration against rules"""
        errors = []

        for rule in self.validation_rules:
            try:
                value = self.get(rule.path)
                error = self._validate_value(value, rule)
                if error:
                    errors.append(f"{rule.path}: {error}")
            except Exception as e:
                errors.append(f"{rule.path}: Validation error - {e}")

        return errors

    def _validate_value(self, value: Any, rule: ConfigValidationRule) -> Optional[str]:
        """Validate a single value against a rule"""
        if rule.rule_type == "required":
            if value is None:
                return rule.error_message or f"Required value missing for {rule.path}"

        elif rule.rule_type == "type":
            expected_type = rule.parameters.get("expected_type")
            if expected_type and not isinstance(value, expected_type):
                return (
                    rule.error_message
                    or f"Expected {expected_type.__name__}, got {type(value).__name__}"
                )

        elif rule.rule_type == "range":
            if value is not None:
                min_val = rule.parameters.get("min")
                max_val = rule.parameters.get("max")

                if min_val is not None and value < min_val:
                    return (
                        rule.error_message
                        or f"Value {value} is below minimum {min_val}"
                    )

                if max_val is not None and value > max_val:
                    return (
                        rule.error_message
                        or f"Value {value} is above maximum {max_val}"
                    )

        elif rule.rule_type == "regex":
            if value is not None:
                pattern = rule.parameters.get("pattern")
                if pattern and not re.match(pattern, str(value)):
                    return (
                        rule.error_message or f"Value does not match pattern {pattern}"
                    )

        elif rule.rule_type == "custom":
            validator_func = rule.parameters.get("validator")
            if validator_func and callable(validator_func):
                try:
                    if not validator_func(value):
                        return rule.error_message or "Custom validation failed"
                except Exception as e:
                    return f"Custom validation error: {e}"

        return None

    def add_watcher(self, key_path: str, callback: callable):
        """Add a configuration change watcher"""
        self.watchers.append({"key_path": key_path, "callback": callback})

    def _notify_watchers(self, changed_key: str, new_value: Any):
        """Notify watchers of configuration changes"""
        for watcher in self.watchers:
            if changed_key.startswith(watcher["key_path"]):
                try:
                    watcher["callback"](changed_key, new_value)
                except Exception as e:
                    self.logger.error(f"Watcher callback error: {e}")

    def reload(self):
        """Reload configuration from all sources"""
        self.logger.info("Reloading configuration")

        with self.config_lock:
            # Clear existing sources except defaults
            self.config_sources = [
                s for s in self.config_sources if s.type == "default"
            ]

            # Rediscover and reload
            self._discover_config_sources()
            self._merge_configurations()

        self.logger.info("Configuration reloaded successfully")

    def export_config(
        self, format: str = "yaml", include_source_info: bool = False
    ) -> str:
        """Export current configuration"""
        if include_source_info:
            export_data = {
                "merged_config": self.merged_config,
                "sources": [
                    {
                        "name": s.name,
                        "type": s.type,
                        "priority": s.priority,
                        "path": s.path,
                        "last_modified": s.last_modified,
                    }
                    for s in sorted(self.config_sources, key=lambda x: x.priority)
                ],
            }
        else:
            export_data = self.merged_config

        if format.lower() == "json":
            return json.dumps(export_data, indent=2)
        else:  # YAML
            return yaml.dump(export_data, default_flow_style=False)

    def get_component_config(self, component_name: str) -> Dict[str, Any]:
        """Get configuration for a specific component"""
        return self.get(component_name, {})

    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        return {
            "environment": self.environment,
            "debug": self.get("system.debug", False),
            "log_level": self.get("system.log_level", "INFO"),
        }

    def is_feature_enabled(self, feature_path: str) -> bool:
        """Check if a feature is enabled"""
        return self.get(f"{feature_path}.enabled", False)

    def get_security_config(self) -> Dict[str, Any]:
        """Get security-related configuration"""
        return self.get("security", {})

    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance-related configuration"""
        return self.get("performance", {})

    def get_integration_config(self, integration_name: str) -> Dict[str, Any]:
        """Get configuration for a specific integration"""
        return self.get(f"integrations.{integration_name}", {})

    def create_environment_override(self, environment: str, overrides: Dict[str, Any]):
        """Create environment-specific configuration overrides"""
        env_dir = os.path.join(self.base_path, "config", "environments")
        os.makedirs(env_dir, exist_ok=True)

        env_file = os.path.join(env_dir, f"{environment}.yaml")

        # Load existing environment config if it exists
        existing_config = {}
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                existing_config = yaml.safe_load(f) or {}

        # Merge with new overrides
        merged_env_config = self._deep_merge(existing_config, overrides)

        # Write back to file
        with open(env_file, "w") as f:
            yaml.dump(merged_env_config, f, default_flow_style=False)

        self.logger.info(f"Created environment override for {environment}")

        # Reload if this is the current environment
        if environment == self.environment:
            self.reload()

    def create_component_config(self, component_name: str, config: Dict[str, Any]):
        """Create component-specific configuration"""
        components_dir = os.path.join(self.base_path, "config", "components")
        os.makedirs(components_dir, exist_ok=True)

        component_file = os.path.join(components_dir, f"{component_name}.yaml")

        with open(component_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        self.logger.info(f"Created component configuration for {component_name}")
        self.reload()


# Global configuration manager instance
_config_manager = None


def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def get_config(key_path: str, default: Any = None) -> Any:
    """Get configuration value (convenience function)"""
    return get_config_manager().get(key_path, default)


def set_config(key_path: str, value: Any, source_name: str = "runtime"):
    """Set configuration value (convenience function)"""
    get_config_manager().set(key_path, value, source_name)


def is_feature_enabled(feature_path: str) -> bool:
    """Check if a feature is enabled (convenience function)"""
    return get_config_manager().is_feature_enabled(feature_path)


def main():
    """Main entry point for configuration management CLI"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Bootstrapper Configuration Management"
    )
    parser.add_argument(
        "command",
        choices=["show", "validate", "export", "set", "reload"],
        help="Command to execute",
    )
    parser.add_argument("--key", help="Configuration key (dot notation)")
    parser.add_argument("--value", help="Value to set")
    parser.add_argument(
        "--format", choices=["yaml", "json"], default="yaml", help="Output format"
    )
    parser.add_argument(
        "--include-sources",
        action="store_true",
        help="Include source information in export",
    )

    args = parser.parse_args()

    config_manager = ConfigurationManager()

    if args.command == "show":
        if args.key:
            value = config_manager.get(args.key)
            if args.format == "json":
                print(json.dumps(value, indent=2))
            else:
                print(yaml.dump(value, default_flow_style=False))
        else:
            print(config_manager.export_config(args.format, args.include_sources))

    elif args.command == "validate":
        errors = config_manager.validate()
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("Configuration validation passed")

    elif args.command == "export":
        print(config_manager.export_config(args.format, args.include_sources))

    elif args.command == "set":
        if not args.key or args.value is None:
            print("Error: --key and --value are required for set command")
            sys.exit(1)

        # Parse value
        value = config_manager._parse_env_value(args.value)
        config_manager.set(args.key, value)
        print(f"Set {args.key} = {value}")

    elif args.command == "reload":
        config_manager.reload()
        print("Configuration reloaded")


if __name__ == "__main__":
    main()
