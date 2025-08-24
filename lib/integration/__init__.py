#!/usr/bin/env python3
"""
Integration Package - Complete System Integration
Provides unified interfaces and orchestration for all platform components
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# Import all integration components
from .component_registry import (
    ComponentRegistry,
    ComponentState,
    ComponentType,
    discover_components,
    get_registry,
    locate_component,
    register_component,
)
from .config_manager import (
    ConfigFormat,
    ConfigManager,
    ConfigScope,
    get_config,
    get_config_manager,
    set_config,
)
from .event_bus import (
    Event,
    EventBus,
    EventPriority,
    EventType,
    broadcast_event,
    get_event_bus,
    publish_event,
    subscribe_to_events,
)
from .health_aggregator import (
    CheckType,
    HealthAggregator,
    HealthCheck,
    HealthStatus,
    add_health_check,
    get_health_aggregator,
    get_system_health,
)

logger = logging.getLogger(__name__)


class SystemIntegrator:
    """
    Main system integrator that orchestrates all integration components
    Provides the unified API for system integration
    """

    def __init__(self):
        """Initialize the system integrator"""
        self.registry = get_registry()
        self.event_bus = get_event_bus()
        self.config_manager = get_config_manager()
        self.health_aggregator = get_health_aggregator()

        self.initialized = False
        self._setup_integration()

    def _setup_integration(self):
        """Setup integration between components"""
        logger.info("Setting up system integration...")

        # Setup event listeners for integration
        self._setup_event_integration()

        # Setup configuration monitoring
        self._setup_config_integration()

        # Setup health monitoring integration
        self._setup_health_integration()

        # Register integration points
        self._register_integration_points()

        self.initialized = True
        logger.info("System integration setup complete")

    def _setup_event_integration(self):
        """Setup event-based integration"""
        # Listen for component registration events
        self.event_bus.subscribe(
            pattern="component.*",
            callback=self._handle_component_event,
            subscriber_id="system_integrator",
        )

        # Listen for configuration changes
        self.event_bus.subscribe(
            pattern="config.*",
            callback=self._handle_config_event,
            subscriber_id="system_integrator",
        )

        # Listen for health events
        self.event_bus.subscribe(
            pattern="health.*",
            callback=self._handle_health_event,
            subscriber_id="system_integrator",
        )

    def _setup_config_integration(self):
        """Setup configuration integration"""
        # Listen for configuration changes and propagate
        self.config_manager.add_listener("*", self._handle_config_change)

    def _setup_health_integration(self):
        """Setup health monitoring integration"""
        # Add alert handler for health events
        self.health_aggregator.add_alert_handler(self._handle_health_alert)

    def _register_integration_points(self):
        """Register integration points with all components"""
        # Register the integrator itself
        register_component(
            name="system_integrator",
            component_type=ComponentType.CUSTOM,
            version="1.0.0",
            description="Main system integrator",
            capabilities=[],
        )

        # Register other integration components
        register_component(
            name="event_bus",
            component_type=ComponentType.CUSTOM,
            version="1.0.0",
            description="Inter-component event bus",
            capabilities=[],
        )

        register_component(
            name="config_manager",
            component_type=ComponentType.CUSTOM,
            version="1.0.0",
            description="Unified configuration manager",
            capabilities=[],
        )

        register_component(
            name="health_aggregator",
            component_type=ComponentType.CUSTOM,
            version="1.0.0",
            description="System health aggregator",
            capabilities=[],
        )

    def _handle_component_event(self, event: Event):
        """Handle component-related events"""
        logger.debug(f"Component event: {event.type} from {event.source}")

        if event.type == EventType.COMPONENT_STARTED:
            # Component started - update health monitoring
            component_name = event.data.get("component")
            if component_name:
                self._add_component_health_checks(component_name)

        elif event.type == EventType.COMPONENT_STOPPED:
            # Component stopped - mark as unhealthy
            component_name = event.data.get("component")
            if component_name:
                health = self.health_aggregator.get_component_health(component_name)
                if health:
                    health.status = HealthStatus.UNHEALTHY

    def _handle_config_event(self, event: Event):
        """Handle configuration-related events"""
        logger.debug(f"Config event: {event.type} from {event.source}")

        if event.type == EventType.CONFIG_CHANGED:
            # Configuration changed - reload affected components
            self._reload_affected_components(event.data)

    def _handle_health_event(self, event: Event):
        """Handle health-related events"""
        logger.debug(f"Health event: {event.type} from {event.source}")

        # Health events are already handled by the health aggregator
        # This is for any additional integration logic

    def _handle_config_change(self, key: str, old_value: Any, new_value: Any):
        """Handle configuration changes"""
        # Publish config change event
        self.event_bus.publish(
            event_type=EventType.CONFIG_CHANGED,
            data={"key": key, "old_value": old_value, "new_value": new_value},
            source="config_manager",
        )

    def _handle_health_alert(self, alert_data: Dict[str, Any]):
        """Handle health alerts"""
        # Publish health alert event
        self.event_bus.publish(
            event_type=EventType.ALERT_TRIGGERED,
            data=alert_data,
            source="health_aggregator",
            priority=EventPriority.HIGH,
        )

    def _add_component_health_checks(self, component_name: str):
        """Add health checks for a component"""
        # This would add appropriate health checks based on component type
        # For now, add a basic liveness check
        self.health_aggregator.add_check(
            HealthCheck(
                name=f"{component_name}_registered",
                component=component_name,
                check_type=CheckType.LIVENESS,
                function=lambda: self.registry.locate(component_name) is not None,
            )
        )

    def _reload_affected_components(self, config_data: Dict[str, Any]):
        """Reload components affected by configuration changes"""
        # This would determine which components need to be reloaded
        # and trigger appropriate reload events
        pass

    def integrate_new_component(
        self,
        name: str,
        component_type: ComponentType,
        capabilities: List[str] = None,
        dependencies: List[str] = None,
        config: Dict[str, Any] = None,
    ) -> str:
        """
        Integrate a new component into the system
        Returns the component ID
        """
        logger.info(f"Integrating new component: {name}")

        # Register component
        component_id = register_component(
            name=name,
            component_type=component_type,
            version="1.0.0",
            description=f"Integrated component: {name}",
            capabilities=capabilities or [],
            dependencies=dependencies or [],
        )

        # Add configuration if provided
        if config:
            for key, value in config.items():
                config_key = f"components.{name}.{key}"
                self.config_manager.set(config_key, value)

        # Add basic health checks
        self._add_component_health_checks(name)

        # Publish integration event
        self.event_bus.publish(
            event_type=EventType.COMPONENT_STARTED,
            data={
                "component": name,
                "component_id": component_id,
                "type": component_type.value,
            },
            source="system_integrator",
        )

        logger.info(f"Component {name} integrated successfully with ID: {component_id}")
        return component_id

    def get_integration_status(self) -> Dict[str, Any]:
        """Get overall integration status"""
        # Get status from all components
        registry_status = self.registry.get_status()
        event_bus_stats = self.event_bus.get_stats()
        config_metadata = self.config_manager.get_metadata()
        health_metrics = self.health_aggregator.get_health_metrics()
        system_health = self.health_aggregator.get_system_health()

        return {
            "timestamp": datetime.now().isoformat(),
            "initialized": self.initialized,
            "overall_health": system_health.status.value,
            "health_score": system_health.score,
            "registry": {
                "total_components": registry_status["total_components"],
                "healthy_components": registry_status.get("healthy_components", 0),
                "components_by_type": registry_status["components_by_type"],
            },
            "event_bus": {
                "events_published": event_bus_stats["statistics"]["events_published"],
                "events_delivered": event_bus_stats["statistics"]["events_delivered"],
                "total_subscriptions": event_bus_stats["total_subscriptions"],
            },
            "configuration": {
                "total_sources": len(config_metadata["sources"]),
                "total_keys": config_metadata["total_keys"],
                "scopes": config_metadata["scopes"],
            },
            "health_monitoring": {
                "total_checks": health_metrics["checks"]["total"],
                "enabled_checks": health_metrics["checks"]["enabled"],
                "critical_checks": health_metrics["checks"]["critical"],
            },
        }

    def start_monitoring(self):
        """Start all monitoring services"""
        logger.info("Starting integrated monitoring services...")

        # Start health monitoring
        self.health_aggregator.start_monitoring()

        # Publish system start event
        self.event_bus.broadcast(
            event_type=EventType.COMPONENT_STARTED,
            data={"component": "system", "services": "all"},
            source="system_integrator",
        )

        logger.info("All monitoring services started")

    def stop_monitoring(self):
        """Stop all monitoring services"""
        logger.info("Stopping integrated monitoring services...")

        # Stop health monitoring
        self.health_aggregator.stop_monitoring()

        # Publish system stop event
        self.event_bus.broadcast(
            event_type=EventType.COMPONENT_STOPPED,
            data={"component": "system", "services": "all"},
            source="system_integrator",
        )

        logger.info("All monitoring services stopped")

    def shutdown(self):
        """Shutdown the entire integration system"""
        logger.info("Shutting down system integration...")

        # Stop monitoring
        self.stop_monitoring()

        # Shutdown components
        self.health_aggregator.stop_monitoring()
        self.event_bus.shutdown()
        self.config_manager.shutdown()

        logger.info("System integration shutdown complete")


# Global system integrator instance
_system_integrator: Optional[SystemIntegrator] = None


def get_system_integrator() -> SystemIntegrator:
    """Get or create the global system integrator instance"""
    global _system_integrator
    if _system_integrator is None:
        _system_integrator = SystemIntegrator()
    return _system_integrator


def integrate_component(**kwargs) -> str:
    """Convenience function to integrate a new component"""
    return get_system_integrator().integrate_new_component(**kwargs)


def get_integration_status() -> Dict[str, Any]:
    """Convenience function to get integration status"""
    return get_system_integrator().get_integration_status()


def start_system_monitoring():
    """Convenience function to start system monitoring"""
    get_system_integrator().start_monitoring()


def stop_system_monitoring():
    """Convenience function to stop system monitoring"""
    get_system_integrator().stop_monitoring()


# Initialize the system integrator when the module is imported
def initialize():
    """Initialize the integration system"""
    get_system_integrator()


# Export all public interfaces
__all__ = [
    # Main integrator
    "SystemIntegrator",
    "get_system_integrator",
    "integrate_component",
    "get_integration_status",
    "start_system_monitoring",
    "stop_system_monitoring",
    "initialize",
    # Component registry
    "ComponentRegistry",
    "ComponentType",
    "ComponentState",
    "get_registry",
    "register_component",
    "discover_components",
    "locate_component",
    # Event bus
    "EventBus",
    "Event",
    "EventType",
    "EventPriority",
    "get_event_bus",
    "publish_event",
    "subscribe_to_events",
    "broadcast_event",
    # Configuration manager
    "ConfigManager",
    "ConfigScope",
    "ConfigFormat",
    "get_config_manager",
    "get_config",
    "set_config",
    # Health aggregator
    "HealthAggregator",
    "HealthStatus",
    "HealthCheck",
    "CheckType",
    "get_health_aggregator",
    "get_system_health",
    "add_health_check",
]
