#!/usr/bin/env python3
"""
Component Registry - Service Discovery and Registration
Manages registration, discovery, and lifecycle of all platform components
"""

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """Types of components in the system"""

    CLI = "cli"
    REGISTRY = "registry"
    MONITORING = "monitoring"
    INTELLIGENCE = "intelligence"
    DEPLOYMENT = "deployment"
    INFRASTRUCTURE = "infrastructure"
    ISOLATION = "isolation"
    GOVERNANCE = "governance"
    SETUP = "setup"
    LIBRARY = "library"
    CUSTOM = "custom"


class ComponentState(Enum):
    """Component lifecycle states"""

    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class ComponentMetadata:
    """Metadata for a registered component"""

    name: str
    type: ComponentType
    version: str
    description: str
    author: str = "bootstrapper"
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ComponentEndpoint:
    """Component communication endpoint"""

    protocol: str  # http, grpc, unix, pipe
    host: str
    port: Optional[int] = None
    path: Optional[str] = None
    auth_required: bool = False

    def to_url(self) -> str:
        """Convert endpoint to URL string"""
        if self.protocol in ["http", "https"]:
            url = f"{self.protocol}://{self.host}"
            if self.port:
                url += f":{self.port}"
            if self.path:
                url += self.path
            return url
        elif self.protocol == "unix":
            return f"unix://{self.path}"
        elif self.protocol == "pipe":
            return f"pipe://{self.host}"
        return f"{self.protocol}://{self.host}"


@dataclass
class ComponentCapability:
    """Describes a capability provided by a component"""

    name: str
    description: str
    version: str
    methods: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)


@dataclass
class RegisteredComponent:
    """A fully registered component"""

    id: str
    metadata: ComponentMetadata
    state: ComponentState
    endpoint: Optional[ComponentEndpoint]
    capabilities: List[ComponentCapability]
    dependencies: List[str]
    health_check_url: Optional[str] = None
    config_path: Optional[str] = None
    log_path: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: str = field(default_factory=lambda: datetime.now().isoformat())
    registration_time: str = field(default_factory=lambda: datetime.now().isoformat())

    def is_healthy(self) -> bool:
        """Check if component is healthy based on heartbeat"""
        if self.state not in [ComponentState.READY, ComponentState.RUNNING]:
            return False

        # Check heartbeat (consider unhealthy if no heartbeat for 5 minutes)
        last_heartbeat = datetime.fromisoformat(self.last_heartbeat)
        if datetime.now() - last_heartbeat > timedelta(minutes=5):
            return False

        return True


class ComponentRegistry:
    """
    Central registry for all platform components
    Provides service discovery, health monitoring, and dependency management
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the component registry"""
        self.config_path = config_path or self._get_default_config_path()
        self.components: Dict[str, RegisteredComponent] = {}
        self.component_lock = threading.RLock()
        self.listeners: Dict[str, List[Callable]] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}

        # Load configuration
        self.config = self._load_config()

        # Start background tasks
        self._start_health_monitor()
        self._start_persistence()

        # Register self
        self._register_self()

    def _get_default_config_path(self) -> str:
        """Get default configuration path"""
        return "/Users/jameshousteau/source_code/bootstrapper/lib/integration/registry.yaml"

    def _load_config(self) -> Dict[str, Any]:
        """Load registry configuration"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}

        # Default configuration
        return {
            "registry": {
                "persistence_enabled": True,
                "persistence_interval": 60,
                "health_check_interval": 30,
                "heartbeat_timeout": 300,
                "auto_discovery": True,
                "discovery_paths": [
                    "/Users/jameshousteau/source_code/bootstrapper/bin",
                    "/Users/jameshousteau/source_code/bootstrapper/lib",
                    "/Users/jameshousteau/source_code/bootstrapper/monitoring",
                    "/Users/jameshousteau/source_code/bootstrapper/intelligence",
                    "/Users/jameshousteau/source_code/bootstrapper/deploy",
                    "/Users/jameshousteau/source_code/bootstrapper/isolation",
                    "/Users/jameshousteau/source_code/bootstrapper/governance",
                    "/Users/jameshousteau/source_code/bootstrapper/setup-project",
                ],
            }
        }

    def _register_self(self):
        """Register the registry component itself"""
        self.register(
            name="component-registry",
            component_type=ComponentType.REGISTRY,
            version="1.0.0",
            description="Central component registry and service discovery",
            capabilities=[
                ComponentCapability(
                    name="service_discovery",
                    description="Discover and locate components",
                    version="1.0.0",
                    methods=["discover", "locate", "query"],
                    provides=["component_list", "component_details", "health_status"],
                ),
                ComponentCapability(
                    name="registration",
                    description="Register and manage components",
                    version="1.0.0",
                    methods=["register", "unregister", "update"],
                    provides=["registration_status", "component_id"],
                ),
            ],
        )

    def _start_health_monitor(self):
        """Start background health monitoring thread"""

        def monitor():
            interval = self.config.get("registry", {}).get("health_check_interval", 30)
            while True:
                try:
                    self._check_all_health()
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")
                    time.sleep(interval)

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def _start_persistence(self):
        """Start background persistence thread"""

        def persist():
            interval = self.config.get("registry", {}).get("persistence_interval", 60)
            while True:
                try:
                    self._persist_registry()
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Persistence error: {e}")
                    time.sleep(interval)

        if self.config.get("registry", {}).get("persistence_enabled", True):
            thread = threading.Thread(target=persist, daemon=True)
            thread.start()

    def _check_all_health(self):
        """Check health of all registered components"""
        with self.component_lock:
            for component_id, component in list(self.components.items()):
                if not component.is_healthy():
                    # Update component state
                    old_state = component.state
                    component.state = ComponentState.DEGRADED

                    # Notify listeners
                    self._notify_listeners(
                        "health_change",
                        {
                            "component_id": component_id,
                            "old_state": old_state,
                            "new_state": ComponentState.DEGRADED,
                            "reason": "health_check_failed",
                        },
                    )

    def _persist_registry(self):
        """Persist registry state to disk"""
        persistence_file = Path(self.config_path).parent / "registry_state.json"

        with self.component_lock:
            state = {
                "timestamp": datetime.now().isoformat(),
                "components": {
                    comp_id: {
                        "metadata": {
                            "name": comp.metadata.name,
                            "type": comp.metadata.type.value,
                            "version": comp.metadata.version,
                            "description": comp.metadata.description,
                            "author": comp.metadata.author,
                            "tags": comp.metadata.tags,
                            "created_at": comp.metadata.created_at,
                            "updated_at": comp.metadata.updated_at,
                        },
                        "state": comp.state.value,
                        "endpoint": asdict(comp.endpoint) if comp.endpoint else None,
                        "capabilities": [asdict(cap) for cap in comp.capabilities],
                        "dependencies": comp.dependencies,
                        "metrics": comp.metrics,
                        "last_heartbeat": comp.last_heartbeat,
                        "registration_time": comp.registration_time,
                    }
                    for comp_id, comp in self.components.items()
                },
                "dependency_graph": {
                    k: list(v) for k, v in self.dependency_graph.items()
                },
            }

        try:
            with open(persistence_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist registry state: {e}")

    def register(
        self,
        name: str,
        component_type: ComponentType,
        version: str,
        description: str,
        endpoint: Optional[ComponentEndpoint] = None,
        capabilities: List[ComponentCapability] = None,
        dependencies: List[str] = None,
        health_check_url: Optional[str] = None,
        config_path: Optional[str] = None,
        log_path: Optional[str] = None,
        tags: List[str] = None,
    ) -> str:
        """
        Register a new component
        Returns the unique component ID
        """
        # Generate unique ID
        component_id = self._generate_component_id(name, component_type, version)

        # Create metadata
        metadata = ComponentMetadata(
            name=name,
            type=component_type,
            version=version,
            description=description,
            tags=tags or [],
        )

        # Create registered component
        component = RegisteredComponent(
            id=component_id,
            metadata=metadata,
            state=ComponentState.INITIALIZING,
            endpoint=endpoint,
            capabilities=capabilities or [],
            dependencies=dependencies or [],
            health_check_url=health_check_url,
            config_path=config_path,
            log_path=log_path,
        )

        with self.component_lock:
            # Check if already registered
            if component_id in self.components:
                # Update existing registration
                self.components[component_id] = component
                logger.info(f"Updated registration for component: {component_id}")
            else:
                # New registration
                self.components[component_id] = component
                logger.info(f"Registered new component: {component_id}")

            # Update dependency graph
            self.dependency_graph[component_id] = set(dependencies or [])

            # Mark as ready
            component.state = ComponentState.READY

        # Notify listeners
        self._notify_listeners(
            "component_registered",
            {"component_id": component_id, "component": component},
        )

        return component_id

    def unregister(self, component_id: str) -> bool:
        """Unregister a component"""
        with self.component_lock:
            if component_id not in self.components:
                return False

            component = self.components[component_id]
            component.state = ComponentState.STOPPING

            # Remove from registry
            del self.components[component_id]

            # Remove from dependency graph
            if component_id in self.dependency_graph:
                del self.dependency_graph[component_id]

            # Remove from other components' dependencies
            for deps in self.dependency_graph.values():
                deps.discard(component_id)

        # Notify listeners
        self._notify_listeners("component_unregistered", {"component_id": component_id})

        logger.info(f"Unregistered component: {component_id}")
        return True

    def update_state(self, component_id: str, new_state: ComponentState) -> bool:
        """Update component state"""
        with self.component_lock:
            if component_id not in self.components:
                return False

            component = self.components[component_id]
            old_state = component.state
            component.state = new_state
            component.updated_at = datetime.now().isoformat()

        # Notify listeners
        self._notify_listeners(
            "state_change",
            {
                "component_id": component_id,
                "old_state": old_state,
                "new_state": new_state,
            },
        )

        return True

    def heartbeat(
        self, component_id: str, metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update component heartbeat"""
        with self.component_lock:
            if component_id not in self.components:
                return False

            component = self.components[component_id]
            component.last_heartbeat = datetime.now().isoformat()

            if metrics:
                component.metrics.update(metrics)

        return True

    def discover(
        self,
        component_type: Optional[ComponentType] = None,
        tags: Optional[List[str]] = None,
        state: Optional[ComponentState] = None,
        healthy_only: bool = False,
    ) -> List[RegisteredComponent]:
        """
        Discover components based on criteria
        """
        with self.component_lock:
            results = []

            for component in self.components.values():
                # Filter by type
                if component_type and component.metadata.type != component_type:
                    continue

                # Filter by tags
                if tags and not any(tag in component.metadata.tags for tag in tags):
                    continue

                # Filter by state
                if state and component.state != state:
                    continue

                # Filter by health
                if healthy_only and not component.is_healthy():
                    continue

                results.append(component)

        return results

    def locate(self, component_id: str) -> Optional[RegisteredComponent]:
        """Locate a specific component by ID"""
        with self.component_lock:
            return self.components.get(component_id)

    def get_dependencies(self, component_id: str, recursive: bool = False) -> Set[str]:
        """Get component dependencies"""
        if component_id not in self.dependency_graph:
            return set()

        dependencies = self.dependency_graph[component_id].copy()

        if recursive:
            # Recursively get all dependencies
            to_process = list(dependencies)
            processed = set()

            while to_process:
                dep_id = to_process.pop(0)
                if dep_id in processed:
                    continue

                processed.add(dep_id)

                if dep_id in self.dependency_graph:
                    sub_deps = self.dependency_graph[dep_id]
                    dependencies.update(sub_deps)
                    to_process.extend(sub_deps)

        return dependencies

    def get_dependents(self, component_id: str) -> Set[str]:
        """Get components that depend on this component"""
        dependents = set()

        for comp_id, deps in self.dependency_graph.items():
            if component_id in deps:
                dependents.add(comp_id)

        return dependents

    def check_circular_dependencies(self) -> List[List[str]]:
        """Check for circular dependencies"""
        cycles = []

        def visit(node: str, path: List[str], visited: Set[str]):
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            path.append(node)

            if node in self.dependency_graph:
                for dep in self.dependency_graph[node]:
                    visit(dep, path.copy(), visited.copy())

        for component_id in self.dependency_graph:
            visit(component_id, [], set())

        return cycles

    def add_listener(self, event_type: str, callback: Callable):
        """Add event listener"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)

    def remove_listener(self, event_type: str, callback: Callable):
        """Remove event listener"""
        if event_type in self.listeners:
            self.listeners[event_type].remove(callback)

    def _notify_listeners(self, event_type: str, data: Dict[str, Any]):
        """Notify all listeners of an event"""
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Listener error for {event_type}: {e}")

    def _generate_component_id(
        self, name: str, component_type: ComponentType, version: str
    ) -> str:
        """Generate unique component ID"""
        # Create a deterministic ID based on name, type, and version
        id_string = f"{name}:{component_type.value}:{version}"
        return hashlib.md5(id_string.encode()).hexdigest()[:12]

    def get_status(self) -> Dict[str, Any]:
        """Get registry status"""
        with self.component_lock:
            total = len(self.components)
            by_state = {}
            by_type = {}

            for component in self.components.values():
                # Count by state
                state_name = component.state.value
                by_state[state_name] = by_state.get(state_name, 0) + 1

                # Count by type
                type_name = component.metadata.type.value
                by_type[type_name] = by_type.get(type_name, 0) + 1

            # Check for circular dependencies
            cycles = self.check_circular_dependencies()

            return {
                "timestamp": datetime.now().isoformat(),
                "total_components": total,
                "components_by_state": by_state,
                "components_by_type": by_type,
                "healthy_components": len(
                    [c for c in self.components.values() if c.is_healthy()]
                ),
                "circular_dependencies": len(cycles) > 0,
                "circular_dependency_chains": cycles,
            }

    def export_graph(self) -> Dict[str, Any]:
        """Export component dependency graph"""
        nodes = []
        edges = []

        with self.component_lock:
            for component_id, component in self.components.items():
                nodes.append(
                    {
                        "id": component_id,
                        "name": component.metadata.name,
                        "type": component.metadata.type.value,
                        "state": component.state.value,
                        "healthy": component.is_healthy(),
                    }
                )

                for dep_id in self.dependency_graph.get(component_id, []):
                    edges.append({"from": component_id, "to": dep_id})

        return {"nodes": nodes, "edges": edges, "timestamp": datetime.now().isoformat()}


# Global registry instance
_registry: Optional[ComponentRegistry] = None


def get_registry() -> ComponentRegistry:
    """Get or create the global registry instance"""
    global _registry
    if _registry is None:
        _registry = ComponentRegistry()
    return _registry


def register_component(**kwargs) -> str:
    """Convenience function to register a component"""
    return get_registry().register(**kwargs)


def discover_components(**kwargs) -> List[RegisteredComponent]:
    """Convenience function to discover components"""
    return get_registry().discover(**kwargs)


def locate_component(component_id: str) -> Optional[RegisteredComponent]:
    """Convenience function to locate a component"""
    return get_registry().locate(component_id)
