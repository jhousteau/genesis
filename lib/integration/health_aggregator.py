#!/usr/bin/env python3
"""
Health Aggregator - System Health Monitoring
Aggregates health status from all components and provides system-wide health view
"""

import logging
import os
import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

    @classmethod
    def from_score(cls, score: float) -> "HealthStatus":
        """Convert health score to status"""
        if score >= 0.9:
            return cls.HEALTHY
        elif score >= 0.5:
            return cls.DEGRADED
        elif score > 0:
            return cls.UNHEALTHY
        else:
            return cls.UNKNOWN


class CheckType(Enum):
    """Types of health checks"""

    LIVENESS = "liveness"  # Is the component alive?
    READINESS = "readiness"  # Is the component ready to serve?
    STARTUP = "startup"  # Has the component started successfully?
    CUSTOM = "custom"  # Custom health check


@dataclass
class HealthCheck:
    """Represents a health check"""

    name: str
    component: str
    check_type: CheckType
    endpoint: Optional[str] = None
    command: Optional[str] = None
    function: Optional[Callable] = None
    interval: int = 30  # seconds
    timeout: int = 5  # seconds
    retries: int = 3
    critical: bool = False  # If true, failure affects overall system health
    enabled: bool = True

    def __hash__(self):
        return hash(f"{self.component}:{self.name}")


@dataclass
class HealthMetric:
    """Health metric data point"""

    timestamp: str
    value: float
    unit: str = "percent"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentHealth:
    """Health status of a component"""

    component: str
    status: HealthStatus
    score: float  # 0.0 to 1.0
    checks: Dict[str, bool]  # Check name -> pass/fail
    metrics: Dict[str, float]
    last_check: str
    consecutive_failures: int = 0
    error_message: Optional[str] = None
    dependencies_healthy: bool = True

    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def is_critical_failure(self) -> bool:
        return self.status == HealthStatus.UNHEALTHY and self.consecutive_failures > 3


@dataclass
class SystemHealth:
    """Overall system health"""

    status: HealthStatus
    score: float
    component_health: Dict[str, ComponentHealth]
    timestamp: str
    healthy_components: int
    total_components: int
    critical_issues: List[str]
    warnings: List[str]

    def get_summary(self) -> str:
        """Get health summary string"""
        return (
            f"System Health: {self.status.value} "
            f"({self.healthy_components}/{self.total_components} healthy) "
            f"Score: {self.score:.2%}"
        )


class HealthAggregator:
    """
    Aggregates health information from all system components
    Provides unified health monitoring and alerting
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize health aggregator"""
        self.config = config or self._get_default_config()
        self.health_checks: Set[HealthCheck] = set()
        self.component_health: Dict[str, ComponentHealth] = {}
        self.health_history: Dict[str, deque] = {}  # Component -> history
        self.health_lock = threading.RLock()

        # Monitoring state
        self.monitoring_active = False
        self.check_threads: Dict[str, threading.Thread] = {}

        # Alerting
        self.alert_handlers: List[Callable] = []
        self.alert_thresholds: Dict[str, float] = {}

        # Metrics
        self.metrics_buffer: Dict[str, deque] = {}
        self.metrics_aggregation_window = 300  # 5 minutes

        # Initialize default health checks
        self._initialize_default_checks()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "health": {
                "enabled": True,
                "default_interval": 30,
                "default_timeout": 5,
                "history_size": 100,
                "alert_on_degraded": True,
                "alert_on_unhealthy": True,
                "aggregation_strategy": "weighted",  # 'weighted', 'minimum', 'average'
                "component_weights": {
                    "cli": 0.5,
                    "registry": 1.0,
                    "monitoring": 0.8,
                    "intelligence": 0.6,
                    "deployment": 1.0,
                    "infrastructure": 1.0,
                    "isolation": 0.9,
                    "governance": 0.7,
                },
            }
        }

    def _initialize_default_checks(self):
        """Initialize default health checks for known components"""
        base_path = "/Users/jameshousteau/source_code/bootstrapper"

        # CLI health check
        self.add_check(
            HealthCheck(
                name="cli_exists",
                component="cli",
                check_type=CheckType.LIVENESS,
                function=lambda: os.path.exists(f"{base_path}/bin/bootstrap"),
                critical=False,
            )
        )

        # Registry health check
        self.add_check(
            HealthCheck(
                name="registry_available",
                component="registry",
                check_type=CheckType.READINESS,
                function=self._check_registry_health,
                critical=True,
            )
        )

        # Monitoring health check
        self.add_check(
            HealthCheck(
                name="monitoring_config",
                component="monitoring",
                check_type=CheckType.READINESS,
                function=lambda: os.path.exists(f"{base_path}/monitoring/configs"),
                critical=False,
            )
        )

        # Intelligence health check
        self.add_check(
            HealthCheck(
                name="intelligence_scripts",
                component="intelligence",
                check_type=CheckType.READINESS,
                function=lambda: all(
                    os.path.exists(f"{base_path}/intelligence/{script}")
                    for script in ["auto-fix/fix.py", "optimization/analyze.py"]
                ),
                critical=False,
            )
        )

        # Deployment health check
        self.add_check(
            HealthCheck(
                name="deployment_orchestrator",
                component="deployment",
                check_type=CheckType.READINESS,
                function=lambda: os.path.exists(
                    f"{base_path}/deploy/deploy-orchestrator.sh"
                ),
                critical=True,
            )
        )

        # Infrastructure health check
        self.add_check(
            HealthCheck(
                name="terraform_modules",
                component="infrastructure",
                check_type=CheckType.READINESS,
                function=lambda: os.path.exists(f"{base_path}/modules"),
                critical=True,
            )
        )

        # Isolation health check
        self.add_check(
            HealthCheck(
                name="isolation_validator",
                component="isolation",
                check_type=CheckType.READINESS,
                function=lambda: os.path.exists(
                    f"{base_path}/isolation/validation/isolation_validator.sh"
                ),
                critical=True,
            )
        )

        # Governance health check
        self.add_check(
            HealthCheck(
                name="governance_config",
                component="governance",
                check_type=CheckType.READINESS,
                function=lambda: os.path.exists(
                    f"{base_path}/governance/governance-config.yaml"
                ),
                critical=False,
            )
        )

    def _check_registry_health(self) -> bool:
        """Check if component registry is healthy"""
        try:
            from .component_registry import get_registry

            registry = get_registry()
            status = registry.get_status()
            return status.get("total_components", 0) > 0
        except Exception:
            return False

    def add_check(self, check: HealthCheck):
        """Add a health check"""
        self.health_checks.add(check)

        # Initialize component health if needed
        if check.component not in self.component_health:
            self.component_health[check.component] = ComponentHealth(
                component=check.component,
                status=HealthStatus.UNKNOWN,
                score=0.0,
                checks={},
                metrics={},
                last_check=datetime.now().isoformat(),
            )

        # Initialize history if needed
        if check.component not in self.health_history:
            history_size = self.config.get("health", {}).get("history_size", 100)
            self.health_history[check.component] = deque(maxlen=history_size)

        logger.info(f"Added health check: {check.name} for {check.component}")

    def remove_check(self, name: str, component: str) -> bool:
        """Remove a health check"""
        check_to_remove = None
        for check in self.health_checks:
            if check.name == name and check.component == component:
                check_to_remove = check
                break

        if check_to_remove:
            self.health_checks.remove(check_to_remove)
            logger.info(f"Removed health check: {name} for {component}")
            return True
        return False

    def start_monitoring(self):
        """Start health monitoring"""
        if self.monitoring_active:
            logger.warning("Health monitoring is already active")
            return

        self.monitoring_active = True
        logger.info("Starting health monitoring")

        # Start check threads for each component
        for component in set(check.component for check in self.health_checks):
            thread = threading.Thread(
                target=self._monitor_component, args=(component,), daemon=True
            )
            self.check_threads[component] = thread
            thread.start()

    def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False

        # Wait for threads to complete
        for thread in self.check_threads.values():
            thread.join(timeout=5)

        self.check_threads.clear()
        logger.info("Stopped health monitoring")

    def _monitor_component(self, component: str):
        """Monitor health of a specific component"""
        while self.monitoring_active:
            try:
                # Get checks for this component
                component_checks = [
                    check
                    for check in self.health_checks
                    if check.component == component and check.enabled
                ]

                if component_checks:
                    # Find minimum interval
                    min_interval = min(check.interval for check in component_checks)

                    # Perform checks
                    self._perform_component_checks(component, component_checks)

                    # Sleep until next check
                    time.sleep(min_interval)
                else:
                    time.sleep(30)  # Default interval if no checks

            except Exception as e:
                logger.error(f"Error monitoring {component}: {e}")
                time.sleep(30)

    def _perform_component_checks(self, component: str, checks: List[HealthCheck]):
        """Perform health checks for a component"""
        check_results = {}
        metrics = {}

        for check in checks:
            try:
                result = self._execute_check(check)
                check_results[check.name] = result

                # Track success rate metric
                metric_name = f"{check.name}_success_rate"
                if metric_name not in self.metrics_buffer:
                    self.metrics_buffer[metric_name] = deque(maxlen=100)
                self.metrics_buffer[metric_name].append(1.0 if result else 0.0)
                metrics[metric_name] = statistics.mean(self.metrics_buffer[metric_name])

            except Exception as e:
                logger.error(f"Check {check.name} failed: {e}")
                check_results[check.name] = False

        # Calculate component health score
        score = self._calculate_component_score(check_results, checks)
        status = HealthStatus.from_score(score)

        # Update component health
        with self.health_lock:
            health = self.component_health[component]
            old_status = health.status

            health.status = status
            health.score = score
            health.checks = check_results
            health.metrics = metrics
            health.last_check = datetime.now().isoformat()

            # Track consecutive failures
            if status == HealthStatus.UNHEALTHY:
                health.consecutive_failures += 1
            else:
                health.consecutive_failures = 0

            # Add to history
            self.health_history[component].append(
                {"timestamp": health.last_check, "status": status.value, "score": score}
            )

            # Check for status change
            if old_status != status:
                self._handle_status_change(component, old_status, status)

    def _execute_check(self, check: HealthCheck) -> bool:
        """Execute a single health check"""
        for attempt in range(check.retries):
            try:
                if check.function:
                    # Execute function check
                    result = check.function()
                    return bool(result)

                elif check.endpoint:
                    # HTTP endpoint check
                    return self._check_http_endpoint(check.endpoint, check.timeout)

                elif check.command:
                    # Command execution check
                    return self._check_command(check.command, check.timeout)

                else:
                    logger.warning(f"No check method defined for {check.name}")
                    return False

            except Exception:
                if attempt == check.retries - 1:
                    raise
                time.sleep(1)  # Brief pause between retries

        return False

    def _check_http_endpoint(self, endpoint: str, timeout: int) -> bool:
        """Check HTTP endpoint health"""
        import requests

        try:
            response = requests.get(endpoint, timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False

    def _check_command(self, command: str, timeout: int) -> bool:
        """Check command execution"""
        import subprocess

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, timeout=timeout
            )
            return result.returncode == 0
        except Exception:
            return False

    def _calculate_component_score(
        self, results: Dict[str, bool], checks: List[HealthCheck]
    ) -> float:
        """Calculate health score for a component"""
        if not results:
            return 0.0

        # Weight critical checks more heavily
        total_weight = 0
        weighted_sum = 0

        for check in checks:
            weight = 2.0 if check.critical else 1.0
            total_weight += weight
            if results.get(check.name, False):
                weighted_sum += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _handle_status_change(
        self, component: str, old_status: HealthStatus, new_status: HealthStatus
    ):
        """Handle component status change"""
        logger.info(
            f"Component {component} status changed: {old_status.value} -> {new_status.value}"
        )

        # Trigger alerts if configured
        if new_status == HealthStatus.UNHEALTHY:
            self._trigger_alert(
                level="critical",
                component=component,
                message=f"Component {component} is unhealthy",
            )
        elif new_status == HealthStatus.DEGRADED:
            if self.config.get("health", {}).get("alert_on_degraded", True):
                self._trigger_alert(
                    level="warning",
                    component=component,
                    message=f"Component {component} is degraded",
                )
        elif (
            old_status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]
            and new_status == HealthStatus.HEALTHY
        ):
            self._trigger_alert(
                level="info",
                component=component,
                message=f"Component {component} recovered to healthy",
            )

    def _trigger_alert(self, level: str, component: str, message: str):
        """Trigger health alert"""
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "component": component,
            "message": message,
        }

        for handler in self.alert_handlers:
            try:
                handler(alert_data)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def add_alert_handler(self, handler: Callable):
        """Add alert handler"""
        self.alert_handlers.append(handler)

    def remove_alert_handler(self, handler: Callable):
        """Remove alert handler"""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)

    def get_component_health(self, component: str) -> Optional[ComponentHealth]:
        """Get health status for a specific component"""
        with self.health_lock:
            return self.component_health.get(component)

    def get_system_health(self) -> SystemHealth:
        """Get overall system health"""
        with self.health_lock:
            # Calculate overall health score
            strategy = self.config.get("health", {}).get(
                "aggregation_strategy", "weighted"
            )
            weights = self.config.get("health", {}).get("component_weights", {})

            if strategy == "weighted":
                total_weight = 0
                weighted_sum = 0
                for component, health in self.component_health.items():
                    weight = weights.get(component, 1.0)
                    total_weight += weight
                    weighted_sum += health.score * weight
                overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0

            elif strategy == "minimum":
                scores = [h.score for h in self.component_health.values()]
                overall_score = min(scores) if scores else 0.0

            else:  # average
                scores = [h.score for h in self.component_health.values()]
                overall_score = statistics.mean(scores) if scores else 0.0

            # Determine overall status
            overall_status = HealthStatus.from_score(overall_score)

            # Count healthy components
            healthy_count = sum(
                1
                for h in self.component_health.values()
                if h.status == HealthStatus.HEALTHY
            )

            # Identify critical issues and warnings
            critical_issues = []
            warnings = []

            for component, health in self.component_health.items():
                if health.status == HealthStatus.UNHEALTHY:
                    critical_issues.append(
                        f"{component}: {health.error_message or 'unhealthy'}"
                    )
                elif health.status == HealthStatus.DEGRADED:
                    warnings.append(f"{component}: degraded performance")

            return SystemHealth(
                status=overall_status,
                score=overall_score,
                component_health=dict(self.component_health),
                timestamp=datetime.now().isoformat(),
                healthy_components=healthy_count,
                total_components=len(self.component_health),
                critical_issues=critical_issues,
                warnings=warnings,
            )

    def get_health_history(
        self, component: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get health history for a component"""
        with self.health_lock:
            if component in self.health_history:
                history = list(self.health_history[component])
                return history[-limit:]
        return []

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get health metrics"""
        system_health = self.get_system_health()

        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "status": system_health.status.value,
                "score": system_health.score,
                "healthy_components": system_health.healthy_components,
                "total_components": system_health.total_components,
            },
            "components": {
                component: {
                    "status": health.status.value,
                    "score": health.score,
                    "consecutive_failures": health.consecutive_failures,
                    "metrics": health.metrics,
                }
                for component, health in self.component_health.items()
            },
            "checks": {
                "total": len(self.health_checks),
                "enabled": len([c for c in self.health_checks if c.enabled]),
                "critical": len([c for c in self.health_checks if c.critical]),
            },
        }

    def export_health_report(self) -> str:
        """Export detailed health report"""
        system_health = self.get_system_health()

        report = []
        report.append("=" * 60)
        report.append("SYSTEM HEALTH REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        report.append(system_health.get_summary())
        report.append("")

        if system_health.critical_issues:
            report.append("CRITICAL ISSUES:")
            for issue in system_health.critical_issues:
                report.append(f"  - {issue}")
            report.append("")

        if system_health.warnings:
            report.append("WARNINGS:")
            for warning in system_health.warnings:
                report.append(f"  - {warning}")
            report.append("")

        report.append("COMPONENT DETAILS:")
        report.append("-" * 40)

        for component, health in sorted(system_health.component_health.items()):
            report.append(f"\n{component.upper()}:")
            report.append(f"  Status: {health.status.value}")
            report.append(f"  Score: {health.score:.2%}")
            report.append(f"  Last Check: {health.last_check}")

            if health.checks:
                report.append("  Checks:")
                for check_name, passed in health.checks.items():
                    status = "✓" if passed else "✗"
                    report.append(f"    {status} {check_name}")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


# Global health aggregator instance
_health_aggregator: Optional[HealthAggregator] = None


def get_health_aggregator() -> HealthAggregator:
    """Get or create the global health aggregator instance"""
    global _health_aggregator
    if _health_aggregator is None:
        _health_aggregator = HealthAggregator()
    return _health_aggregator


def get_system_health() -> SystemHealth:
    """Convenience function to get system health"""
    return get_health_aggregator().get_system_health()


def add_health_check(check: HealthCheck):
    """Convenience function to add health check"""
    get_health_aggregator().add_check(check)
