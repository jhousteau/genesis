"""
Feature flag system for SOLVE framework.

This module provides feature flags for controlling the rollout of new functionality,
allowing gradual migration from existing implementations to new ones.
"""

import logging
import os

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Central registry for feature flags in SOLVE."""

    # Environment variable prefix for all SOLVE feature flags
    ENV_PREFIX = "SOLVE_"

    # Individual feature flag names
    AGENT_MODE = "AGENT_MODE"

    @classmethod
    def is_enabled(cls, flag_name: str, default: bool = False) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag_name: Name of the feature flag (without prefix)
            default: Default value if environment variable is not set

        Returns:
            True if the feature is enabled, False otherwise
        """
        # Try to use the new configuration system first
        try:
            from solve.config import get_config

            config = get_config()
            if config.features and flag_name == cls.AGENT_MODE:
                return bool(config.features.agent_mode)
                # Add more feature flags as needed
        except ImportError:
            pass  # Fall back to environment variables

        env_var = f"{cls.ENV_PREFIX}{flag_name}"
        value = os.environ.get(env_var, "").lower()

        if not value:
            return default

        # Handle various truthy values
        if value in ("true", "1", "yes", "on", "enabled"):
            logger.debug(f"Feature flag {flag_name} is ENABLED")
            return True
        elif value in ("false", "0", "no", "off", "disabled"):
            logger.debug(f"Feature flag {flag_name} is DISABLED")
            return False
        else:
            logger.warning(
                f"Invalid value '{value}' for feature flag {env_var}. Using default: {default}",
            )
            return default


def is_agent_mode_enabled() -> bool:
    """
    Check if agent mode is enabled.

    Agent mode replaces the traditional phase-based orchestration with
    a goal-driven agent coordination system.

    Enable by setting: SOLVE_AGENT_MODE=true

    Returns:
        True if agent mode is enabled, False otherwise
    """
    return FeatureFlags.is_enabled(FeatureFlags.AGENT_MODE, default=False)


def get_active_features() -> dict[str, bool]:
    """
    Get a dictionary of all feature flags and their current states.

    Returns:
        Dictionary mapping feature names to their enabled/disabled status
    """
    try:
        from solve.config import get_config

        config = get_config()
        if config.features:
            return {
                "agent_mode": config.features.agent_mode,
                "parallel_validation": config.features.parallel_validation,
                "experimental_fixes": config.features.experimental_fixes,
                "enhanced_metrics": config.features.enhanced_metrics,
            }
    except ImportError:
        pass  # Fall back to environment variables
    return {
        "agent_mode": is_agent_mode_enabled(),
        # Add more feature flags here as they are created
    }


def get_feature_flag(flag_name: str, default: bool = False) -> bool:
    """
    Get the value of a feature flag.

    Args:
        flag_name: Name of the feature flag (can include or exclude ENV_PREFIX)
        default: Default value if flag is not set

    Returns:
        Boolean value of the feature flag
    """
    # Remove prefix if already included
    if flag_name.startswith(FeatureFlags.ENV_PREFIX):
        flag_name = flag_name[len(FeatureFlags.ENV_PREFIX) :]

    return FeatureFlags.is_enabled(flag_name, default)


def log_feature_status() -> None:
    """Log the status of all feature flags for debugging."""
    features = get_active_features()
    logger.info("Feature flag status:")
    for feature, enabled in features.items():
        status = "ENABLED" if enabled else "DISABLED"
        logger.info(f"  - {feature}: {status}")
