#!/usr/bin/env python3

"""
System Coordinator for Universal Project Platform
Unified coordination system for all bootstrapper components and agent outputs
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml

# Add the lib directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "python"))


class ComponentStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class CoordinationLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Component:
    """Represents a system component"""

    name: str
    path: str
    type: str  # 'intelligence', 'deployment', 'governance', etc.
    status: ComponentStatus
    last_health_check: str
    health_score: float  # 0.0 to 1.0
    capabilities: List[str]
    dependencies: List[str]
    configuration: Dict[str, Any]
    metrics: Dict[str, Any]


@dataclass
class CoordinationTask:
    """Represents a coordination task"""

    id: str
    name: str
    type: str
    level: CoordinationLevel
    components: List[str]
    dependencies: List[str]
    parameters: Dict[str, Any]
    status: str  # 'pending', 'running', 'completed', 'failed'
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class AgentOutput:
    """Represents output from an agent"""

    agent_id: str
    agent_name: str
    component: str
    output_type: str  # 'configuration', 'code', 'documentation', 'test'
    timestamp: str
    content: Dict[str, Any]
    dependencies: List[str]
    conflicts: List[str]
    integration_requirements: List[str]


class SystemCoordinator:
    """Main system coordinator that manages all bootstrapper components"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or self._find_config_path()
        self.config = self._load_configuration()
        self.logger = self._setup_logging()

        # Component management
        self.components: Dict[str, Component] = {}
        self.component_lock = threading.RLock()

        # Task management
        self.tasks: Dict[str, CoordinationTask] = {}
        self.task_queue = asyncio.Queue()
        self.task_lock = threading.RLock()

        # Agent output management
        self.agent_outputs: List[AgentOutput] = []
        self.integration_conflicts: List[Dict[str, Any]] = []

        # Coordination state
        self.coordination_active = False
        self.coordination_loop_task = None
        self.health_monitor_task = None

        # Initialize components
        self._discover_components()

    def _find_config_path(self) -> str:
        """Find the configuration file"""
        possible_paths = [
            "/Users/jameshousteau/source_code/bootstrapper/coordination/config.yaml",
            "/Users/jameshousteau/source_code/bootstrapper/config/system_coordination.yaml",
            os.path.join(os.path.dirname(__file__), "config.yaml"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # Create default config if none found
        return self._create_default_config()

    def _create_default_config(self) -> str:
        """Create default configuration"""
        config_dir = os.path.join(os.path.dirname(__file__))
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.yaml")

        default_config = {
            "system_coordination": {
                "enabled": True,
                "coordination_interval": 30,
                "health_check_interval": 60,
                "max_concurrent_tasks": 5,
                "task_timeout": 300,
                "auto_resolve_conflicts": True,
                "notification_enabled": True,
            },
            "components": {
                "intelligence": {
                    "path": "/Users/jameshousteau/source_code/bootstrapper/intelligence",
                    "capabilities": [
                        "analysis",
                        "auto-fix",
                        "optimization",
                        "predictions",
                        "recommendations",
                    ],
                    "dependencies": [],
                    "health_endpoint": None,
                    "priority": "high",
                },
                "deployment": {
                    "path": "/Users/jameshousteau/source_code/bootstrapper/deploy",
                    "capabilities": [
                        "orchestration",
                        "strategies",
                        "rollback",
                        "validation",
                    ],
                    "dependencies": ["intelligence"],
                    "health_endpoint": None,
                    "priority": "critical",
                },
                "governance": {
                    "path": "/Users/jameshousteau/source_code/bootstrapper/governance",
                    "capabilities": [
                        "compliance",
                        "policies",
                        "auditing",
                        "cost-control",
                    ],
                    "dependencies": [],
                    "health_endpoint": None,
                    "priority": "high",
                },
                "isolation": {
                    "path": "/Users/jameshousteau/source_code/bootstrapper/isolation",
                    "capabilities": [
                        "gcp-isolation",
                        "credentials",
                        "policies",
                        "validation",
                    ],
                    "dependencies": ["governance"],
                    "health_endpoint": None,
                    "priority": "critical",
                },
                "monitoring": {
                    "path": "/Users/jameshousteau/source_code/bootstrapper/monitoring",
                    "capabilities": ["metrics", "logging", "alerting", "dashboards"],
                    "dependencies": [],
                    "health_endpoint": None,
                    "priority": "high",
                },
                "setup-project": {
                    "path": "/Users/jameshousteau/source_code/bootstrapper/setup-project",
                    "capabilities": ["project-creation", "templates", "validation"],
                    "dependencies": ["governance", "isolation"],
                    "health_endpoint": None,
                    "priority": "medium",
                },
            },
            "agents": {
                "agent_1_genesis": {
                    "name": "Project Genesis",
                    "components": ["setup-project"],
                    "output_types": ["configuration", "templates", "scripts"],
                },
                "agent_2_plumbing": {
                    "name": "Plumbing Layer",
                    "components": ["lib"],
                    "output_types": ["code", "libraries", "utilities"],
                },
                "agent_3_infrastructure": {
                    "name": "Infrastructure Layer",
                    "components": ["modules"],
                    "output_types": ["terraform", "configuration"],
                },
                "agent_4_deployment": {
                    "name": "Deployment Layer",
                    "components": ["deploy"],
                    "output_types": ["pipelines", "strategies", "scripts"],
                },
                "agent_5_isolation": {
                    "name": "Isolation Layer",
                    "components": ["isolation"],
                    "output_types": ["policies", "scripts", "configurations"],
                },
                "agent_6_monitoring": {
                    "name": "Monitoring Layer",
                    "components": ["monitoring"],
                    "output_types": ["configs", "dashboards", "alerts"],
                },
                "agent_7_governance": {
                    "name": "Governance Layer",
                    "components": ["governance"],
                    "output_types": ["policies", "compliance", "auditing"],
                },
                "agent_8_integration": {
                    "name": "Integration Coordinator",
                    "components": ["intelligence", "coordination"],
                    "output_types": ["integration", "tests", "documentation"],
                },
            },
            "integration_rules": {
                "conflict_resolution": {
                    "strategy": "priority_based",  # 'manual', 'priority_based', 'consensus'
                    "timeout": 300,
                },
                "dependency_management": {
                    "auto_resolve": True,
                    "circular_dependency_action": "error",
                },
                "quality_gates": {
                    "enabled": True,
                    "required_checks": ["syntax", "dependencies", "conflicts"],
                },
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)

        return config_path

    def _load_configuration(self) -> Dict[str, Any]:
        """Load system configuration"""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return {}

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the system coordinator"""
        logger = logging.getLogger("system_coordinator")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _discover_components(self):
        """Discover and register system components"""
        component_configs = self.config.get("components", {})

        for component_name, component_config in component_configs.items():
            component = Component(
                name=component_name,
                path=component_config.get("path", ""),
                type=component_name,
                status=ComponentStatus.OFFLINE,
                last_health_check=datetime.now().isoformat(),
                health_score=0.0,
                capabilities=component_config.get("capabilities", []),
                dependencies=component_config.get("dependencies", []),
                configuration=component_config,
                metrics={},
            )

            # Check initial health
            if os.path.exists(component.path):
                component.status = ComponentStatus.ONLINE
                component.health_score = 1.0

            self.components[component_name] = component

        self.logger.info(f"Discovered {len(self.components)} components")

    async def start_coordination(self):
        """Start the coordination system"""
        if self.coordination_active:
            self.logger.warning("Coordination is already active")
            return

        self.coordination_active = True
        self.logger.info("Starting system coordination")

        # Start coordination loop
        self.coordination_loop_task = asyncio.create_task(self._coordination_loop())

        # Start health monitoring
        self.health_monitor_task = asyncio.create_task(self._health_monitor_loop())

        # Process existing agent outputs
        await self._process_pending_integrations()

    async def stop_coordination(self):
        """Stop the coordination system"""
        self.coordination_active = False

        if self.coordination_loop_task:
            self.coordination_loop_task.cancel()
            try:
                await self.coordination_loop_task
            except asyncio.CancelledError:
                pass

        if self.health_monitor_task:
            self.health_monitor_task.cancel()
            try:
                await self.health_monitor_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Stopped system coordination")

    async def _coordination_loop(self):
        """Main coordination loop"""
        interval = self.config.get("system_coordination", {}).get(
            "coordination_interval", 30
        )

        while self.coordination_active:
            try:
                await self._coordinate_components()
                await self._process_task_queue()
                await self._resolve_conflicts()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in coordination loop: {e}")
                await asyncio.sleep(interval)

    async def _health_monitor_loop(self):
        """Health monitoring loop"""
        interval = self.config.get("system_coordination", {}).get(
            "health_check_interval", 60
        )

        while self.coordination_active:
            try:
                await self._check_component_health()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(interval)

    async def _coordinate_components(self):
        """Coordinate between components"""
        with self.component_lock:
            # Check for component dependencies
            for component_name, component in self.components.items():
                if component.status == ComponentStatus.ONLINE:
                    await self._check_component_dependencies(component)
                    await self._update_component_metrics(component)

    async def _check_component_dependencies(self, component: Component):
        """Check if component dependencies are satisfied"""
        for dep_name in component.dependencies:
            if dep_name in self.components:
                dep_component = self.components[dep_name]
                if dep_component.status != ComponentStatus.ONLINE:
                    self.logger.warning(
                        f"Component {component.name} depends on {dep_name} which is {dep_component.status.value}"
                    )
                    # Could trigger dependency resolution here

    async def _update_component_metrics(self, component: Component):
        """Update component metrics"""
        # This would collect real metrics from each component
        # For now, we'll update basic health metrics
        component.last_health_check = datetime.now().isoformat()

        # Simulate metric collection
        if component.status == ComponentStatus.ONLINE:
            component.metrics.update(
                {
                    "uptime": time.time(),
                    "cpu_usage": 0.1,  # Would be real metrics
                    "memory_usage": 0.2,
                    "disk_usage": 0.3,
                    "last_activity": datetime.now().isoformat(),
                }
            )

    async def _check_component_health(self):
        """Check health of all components"""
        for component_name, component in self.components.items():
            try:
                health_score = await self._calculate_component_health(component)
                component.health_score = health_score

                # Update status based on health score
                if health_score >= 0.9:
                    component.status = ComponentStatus.ONLINE
                elif health_score >= 0.5:
                    component.status = ComponentStatus.DEGRADED
                else:
                    component.status = ComponentStatus.OFFLINE

            except Exception as e:
                self.logger.error(f"Health check failed for {component_name}: {e}")
                component.status = ComponentStatus.ERROR
                component.health_score = 0.0

    async def _calculate_component_health(self, component: Component) -> float:
        """Calculate health score for a component"""
        health_factors = []

        # Check if component path exists
        if os.path.exists(component.path):
            health_factors.append(1.0)
        else:
            health_factors.append(0.0)

        # Check component-specific health indicators
        if component.type == "intelligence":
            # Check if intelligence scripts exist
            required_scripts = [
                "auto-fix/fix.py",
                "optimization/analyze.py",
                "predictions/analyze.py",
                "recommendations/analyze.py",
            ]
            script_health = sum(
                1.0 if os.path.exists(os.path.join(component.path, script)) else 0.0
                for script in required_scripts
            ) / len(required_scripts)
            health_factors.append(script_health)

        elif component.type == "deployment":
            # Check deployment orchestrator
            orchestrator_path = os.path.join(component.path, "deploy-orchestrator.sh")
            health_factors.append(1.0 if os.path.exists(orchestrator_path) else 0.0)

        elif component.type == "governance":
            # Check governance config
            config_path = os.path.join(component.path, "governance-config.yaml")
            health_factors.append(1.0 if os.path.exists(config_path) else 0.0)

        # Add more component-specific checks as needed

        return sum(health_factors) / len(health_factors) if health_factors else 0.0

    async def _process_task_queue(self):
        """Process coordination tasks from the queue"""
        try:
            while not self.task_queue.empty():
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                await self._execute_coordination_task(task)
        except asyncio.TimeoutError:
            pass  # No tasks in queue

    async def _execute_coordination_task(self, task: CoordinationTask):
        """Execute a coordination task"""
        with self.task_lock:
            task.status = "running"
            task.started_at = datetime.now().isoformat()

        try:
            self.logger.info(f"Executing coordination task: {task.name}")

            # Execute task based on type
            if task.type == "health_check":
                result = await self._execute_health_check_task(task)
            elif task.type == "integration":
                result = await self._execute_integration_task(task)
            elif task.type == "conflict_resolution":
                result = await self._execute_conflict_resolution_task(task)
            elif task.type == "deployment_coordination":
                result = await self._execute_deployment_coordination_task(task)
            else:
                result = {"error": f"Unknown task type: {task.type}"}

            with self.task_lock:
                task.status = "completed"
                task.completed_at = datetime.now().isoformat()
                task.result = result

            self.logger.info(f"Task {task.name} completed successfully")

        except Exception as e:
            with self.task_lock:
                task.status = "failed"
                task.completed_at = datetime.now().isoformat()
                task.error = str(e)

            self.logger.error(f"Task {task.name} failed: {e}")

    async def _execute_health_check_task(
        self, task: CoordinationTask
    ) -> Dict[str, Any]:
        """Execute health check coordination task"""
        components_to_check = task.components or list(self.components.keys())
        results = {}

        for component_name in components_to_check:
            if component_name in self.components:
                component = self.components[component_name]
                health_score = await self._calculate_component_health(component)
                results[component_name] = {
                    "status": component.status.value,
                    "health_score": health_score,
                    "last_check": component.last_health_check,
                }

        return results

    async def _execute_integration_task(self, task: CoordinationTask) -> Dict[str, Any]:
        """Execute integration coordination task"""
        # Process agent outputs and resolve conflicts
        integration_results = {
            "processed_outputs": 0,
            "resolved_conflicts": 0,
            "new_conflicts": 0,
            "integration_status": "success",
        }

        # Process any pending agent outputs
        pending_outputs = [
            output
            for output in self.agent_outputs
            if not hasattr(output, "processed") or not output.processed
        ]

        for output in pending_outputs:
            try:
                await self._process_agent_output(output)
                integration_results["processed_outputs"] += 1
                output.processed = True
            except Exception as e:
                self.logger.error(f"Failed to process agent output: {e}")
                integration_results["integration_status"] = "partial_failure"

        return integration_results

    async def _execute_conflict_resolution_task(
        self, task: CoordinationTask
    ) -> Dict[str, Any]:
        """Execute conflict resolution task"""
        resolution_results = {
            "conflicts_found": len(self.integration_conflicts),
            "conflicts_resolved": 0,
            "conflicts_remaining": 0,
            "resolution_strategy": self.config.get("integration_rules", {})
            .get("conflict_resolution", {})
            .get("strategy", "manual"),
        }

        strategy = resolution_results["resolution_strategy"]

        for conflict in self.integration_conflicts.copy():
            try:
                if strategy == "priority_based":
                    resolved = await self._resolve_conflict_by_priority(conflict)
                elif strategy == "consensus":
                    resolved = await self._resolve_conflict_by_consensus(conflict)
                else:
                    resolved = False  # Manual resolution required

                if resolved:
                    self.integration_conflicts.remove(conflict)
                    resolution_results["conflicts_resolved"] += 1

            except Exception as e:
                self.logger.error(f"Failed to resolve conflict: {e}")

        resolution_results["conflicts_remaining"] = len(self.integration_conflicts)

        return resolution_results

    async def _execute_deployment_coordination_task(
        self, task: CoordinationTask
    ) -> Dict[str, Any]:
        """Execute deployment coordination task"""
        # Coordinate deployment across components
        deployment_results = {
            "components_coordinated": 0,
            "deployment_status": "success",
            "coordination_level": task.level.value,
        }

        # This would coordinate actual deployment activities
        # For now, return mock results
        deployment_results["components_coordinated"] = len(task.components)

        return deployment_results

    async def _resolve_conflicts(self):
        """Resolve integration conflicts"""
        if not self.integration_conflicts:
            return

        auto_resolve = (
            self.config.get("integration_rules", {})
            .get("conflict_resolution", {})
            .get("auto_resolve", True)
        )

        if auto_resolve:
            # Create conflict resolution task
            task = CoordinationTask(
                id=f"conflict_resolution_{int(time.time())}",
                name="Automatic Conflict Resolution",
                type="conflict_resolution",
                level=CoordinationLevel.HIGH,
                components=list(self.components.keys()),
                dependencies=[],
                parameters={},
                status="pending",
                created_at=datetime.now().isoformat(),
            )

            await self.task_queue.put(task)

    async def _resolve_conflict_by_priority(self, conflict: Dict[str, Any]) -> bool:
        """Resolve conflict using priority-based strategy"""
        # Get component priorities from configuration
        component_priorities = {}
        for comp_name, comp_config in self.config.get("components", {}).items():
            priority_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            component_priorities[comp_name] = priority_map.get(
                comp_config.get("priority", "medium"), 2
            )

        # Find highest priority component in conflict
        conflicting_components = conflict.get("components", [])
        if not conflicting_components:
            return False

        highest_priority_component = max(
            conflicting_components, key=lambda comp: component_priorities.get(comp, 0)
        )

        # Apply resolution based on highest priority component
        conflict["resolution"] = {
            "strategy": "priority_based",
            "winner": highest_priority_component,
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(
            f"Resolved conflict using priority: {highest_priority_component} wins"
        )
        return True

    async def _resolve_conflict_by_consensus(self, conflict: Dict[str, Any]) -> bool:
        """Resolve conflict using consensus strategy"""
        # This would implement a consensus mechanism
        # For now, return False (manual resolution required)
        return False

    async def _process_pending_integrations(self):
        """Process any pending agent output integrations"""
        if self.agent_outputs:
            task = CoordinationTask(
                id=f"integration_{int(time.time())}",
                name="Process Pending Integrations",
                type="integration",
                level=CoordinationLevel.MEDIUM,
                components=list(self.components.keys()),
                dependencies=[],
                parameters={},
                status="pending",
                created_at=datetime.now().isoformat(),
            )

            await self.task_queue.put(task)

    async def _process_agent_output(self, output: AgentOutput):
        """Process output from an agent"""
        self.logger.info(f"Processing output from {output.agent_name}")

        # Check for conflicts with existing outputs
        conflicts = self._detect_conflicts(output)

        if conflicts:
            conflict_record = {
                "id": f"conflict_{int(time.time())}",
                "timestamp": datetime.now().isoformat(),
                "type": "agent_output_conflict",
                "components": [output.component]
                + [c.get("component", "") for c in conflicts],
                "details": {
                    "new_output": asdict(output),
                    "conflicting_outputs": conflicts,
                },
                "severity": "medium",
                "auto_resolvable": True,
            }

            self.integration_conflicts.append(conflict_record)
            self.logger.warning(
                f"Conflict detected for output from {output.agent_name}"
            )

        # Validate dependencies
        await self._validate_output_dependencies(output)

        # Apply integration requirements
        await self._apply_integration_requirements(output)

    def _detect_conflicts(self, new_output: AgentOutput) -> List[Dict[str, Any]]:
        """Detect conflicts with existing agent outputs"""
        conflicts = []

        for existing_output in self.agent_outputs:
            if (
                existing_output.component == new_output.component
                and existing_output.output_type == new_output.output_type
                and existing_output.agent_id != new_output.agent_id
            ):
                # Check for content conflicts
                if self._outputs_conflict(existing_output, new_output):
                    conflicts.append(
                        {
                            "agent_id": existing_output.agent_id,
                            "agent_name": existing_output.agent_name,
                            "component": existing_output.component,
                            "output_type": existing_output.output_type,
                            "conflict_type": "content_overlap",
                        }
                    )

        return conflicts

    def _outputs_conflict(self, output1: AgentOutput, output2: AgentOutput) -> bool:
        """Check if two outputs conflict"""
        # This would implement sophisticated conflict detection
        # For now, simple heuristic: same component + same output type = potential conflict
        return (
            output1.component == output2.component
            and output1.output_type == output2.output_type
        )

    async def _validate_output_dependencies(self, output: AgentOutput):
        """Validate that output dependencies are satisfied"""
        for dependency in output.dependencies:
            if dependency not in self.components:
                self.logger.warning(
                    f"Output from {output.agent_name} depends on unknown component: {dependency}"
                )
            elif self.components[dependency].status != ComponentStatus.ONLINE:
                self.logger.warning(
                    f"Output from {output.agent_name} depends on offline component: {dependency}"
                )

    async def _apply_integration_requirements(self, output: AgentOutput):
        """Apply integration requirements for the output"""
        for requirement in output.integration_requirements:
            # Process integration requirements
            # This could trigger specific integration tasks
            self.logger.debug(f"Processing integration requirement: {requirement}")

    def register_agent_output(self, output: AgentOutput):
        """Register output from an agent"""
        self.agent_outputs.append(output)
        self.logger.info(
            f"Registered output from {output.agent_name} for component {output.component}"
        )

        # Trigger integration processing if coordination is active
        if self.coordination_active:
            asyncio.create_task(self._process_agent_output(output))

    def create_coordination_task(self, task: CoordinationTask):
        """Create a new coordination task"""
        with self.task_lock:
            self.tasks[task.id] = task

        # Add to queue for processing
        if self.coordination_active:
            asyncio.create_task(self.task_queue.put(task))

        self.logger.info(f"Created coordination task: {task.name}")

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        with self.component_lock:
            component_status = {}
            for name, component in self.components.items():
                component_status[name] = {
                    "status": component.status.value,
                    "health_score": component.health_score,
                    "last_health_check": component.last_health_check,
                    "capabilities": component.capabilities,
                    "metrics": component.metrics,
                }

        with self.task_lock:
            task_status = {
                "total_tasks": len(self.tasks),
                "pending_tasks": len(
                    [t for t in self.tasks.values() if t.status == "pending"]
                ),
                "running_tasks": len(
                    [t for t in self.tasks.values() if t.status == "running"]
                ),
                "completed_tasks": len(
                    [t for t in self.tasks.values() if t.status == "completed"]
                ),
                "failed_tasks": len(
                    [t for t in self.tasks.values() if t.status == "failed"]
                ),
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "coordination_active": self.coordination_active,
            "components": component_status,
            "tasks": task_status,
            "agent_outputs": len(self.agent_outputs),
            "integration_conflicts": len(self.integration_conflicts),
            "overall_health": self._calculate_overall_health(),
        }

    def _calculate_overall_health(self) -> float:
        """Calculate overall system health"""
        if not self.components:
            return 0.0

        total_health = sum(
            component.health_score for component in self.components.values()
        )
        return total_health / len(self.components)

    def get_integration_report(self) -> Dict[str, Any]:
        """Generate integration report"""
        agent_summary = {}
        for output in self.agent_outputs:
            agent_id = output.agent_id
            if agent_id not in agent_summary:
                agent_summary[agent_id] = {
                    "agent_name": output.agent_name,
                    "output_count": 0,
                    "components": set(),
                    "output_types": set(),
                }

            agent_summary[agent_id]["output_count"] += 1
            agent_summary[agent_id]["components"].add(output.component)
            agent_summary[agent_id]["output_types"].add(output.output_type)

        # Convert sets to lists for JSON serialization
        for agent_data in agent_summary.values():
            agent_data["components"] = list(agent_data["components"])
            agent_data["output_types"] = list(agent_data["output_types"])

        return {
            "timestamp": datetime.now().isoformat(),
            "agent_outputs": len(self.agent_outputs),
            "unique_agents": len(agent_summary),
            "integration_conflicts": len(self.integration_conflicts),
            "agent_summary": agent_summary,
            "conflict_summary": [
                {
                    "id": conflict.get("id"),
                    "type": conflict.get("type"),
                    "components": conflict.get("components", []),
                    "severity": conflict.get("severity"),
                    "auto_resolvable": conflict.get("auto_resolvable"),
                }
                for conflict in self.integration_conflicts
            ],
        }


# Utility functions for agent integration
def create_agent_output(
    agent_id: str,
    agent_name: str,
    component: str,
    output_type: str,
    content: Dict[str, Any],
    dependencies: List[str] = None,
    conflicts: List[str] = None,
    integration_requirements: List[str] = None,
) -> AgentOutput:
    """Helper function to create agent output"""
    return AgentOutput(
        agent_id=agent_id,
        agent_name=agent_name,
        component=component,
        output_type=output_type,
        timestamp=datetime.now().isoformat(),
        content=content,
        dependencies=dependencies or [],
        conflicts=conflicts or [],
        integration_requirements=integration_requirements or [],
    )


async def main():
    """Main entry point for the system coordinator"""
    import argparse

    parser = argparse.ArgumentParser(description="System Coordinator for Bootstrapper")
    parser.add_argument(
        "command",
        choices=["start", "status", "report", "stop"],
        help="Command to execute",
    )
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")

    args = parser.parse_args()

    coordinator = SystemCoordinator(args.config)

    if args.command == "start":
        print("Starting system coordination...")
        await coordinator.start_coordination()

        if args.daemon:
            # Run as daemon
            try:
                while coordinator.coordination_active:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping coordination...")
                await coordinator.stop_coordination()
        else:
            # Run for a short time and then stop
            await asyncio.sleep(10)
            await coordinator.stop_coordination()

    elif args.command == "status":
        status = coordinator.get_system_status()
        print(json.dumps(status, indent=2))

    elif args.command == "report":
        report = coordinator.get_integration_report()
        print(json.dumps(report, indent=2))

    elif args.command == "stop":
        await coordinator.stop_coordination()
        print("Coordination stopped")


if __name__ == "__main__":
    asyncio.run(main())
