"""
Monitoring Automation Orchestrator for Universal Platform
Coordinates service discovery, configuration management, and monitoring automation.
"""

import asyncio
import json
import logging
import os
import signal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml

from .config_manager import ConfigurationManager

# Import local modules
from .service_discovery import DiscoveredService, ServiceDiscovery


class AutomationStatus(Enum):
    """Status of automation components."""

    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


@dataclass
class AutomationMetrics:
    """Metrics for monitoring automation."""

    discovery_cycles: int = 0
    config_updates: int = 0
    successful_updates: int = 0
    failed_updates: int = 0
    services_discovered: int = 0
    last_discovery: Optional[datetime] = None
    last_config_update: Optional[datetime] = None
    uptime_start: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "discovery_cycles": self.discovery_cycles,
            "config_updates": self.config_updates,
            "successful_updates": self.successful_updates,
            "failed_updates": self.failed_updates,
            "services_discovered": self.services_discovered,
            "last_discovery": (
                self.last_discovery.isoformat() if self.last_discovery else None
            ),
            "last_config_update": (
                self.last_config_update.isoformat() if self.last_config_update else None
            ),
            "uptime_seconds": (datetime.now() - self.uptime_start).total_seconds(),
        }


class MonitoringOrchestrator:
    """Orchestrates monitoring automation components."""

    def __init__(self, config_file: str = "orchestrator-config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
        self.status = AutomationStatus.STOPPED
        self.metrics = AutomationMetrics()

        # Initialize components
        self.service_discovery = ServiceDiscovery(
            self.config.get("service_discovery", {}).get(
                "config_file", "discovery-config.yaml"
            )
        )
        self.config_manager = ConfigurationManager(
            self.config.get("config_manager", {}).get(
                "config_file", "config-manager.yaml"
            )
        )

        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # State tracking
        self._running = False
        self._tasks = []
        self._last_services = []

        # Signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _load_config(self) -> Dict[str, Any]:
        """Load orchestrator configuration."""
        default_config = {
            "log_level": "INFO",
            "discovery_interval": 60,
            "config_update_interval": 300,
            "health_check_interval": 30,
            "max_workers": 4,
            "service_discovery": {
                "config_file": "discovery-config.yaml",
                "enabled": True,
            },
            "config_manager": {
                "config_file": "config-manager.yaml",
                "enabled": True,
                "auto_update": True,
            },
            "automation_features": {
                "auto_scaling_alerts": True,
                "slo_monitoring": True,
                "cost_optimization": True,
                "security_monitoring": True,
                "performance_tuning": True,
            },
            "thresholds": {
                "service_change_threshold": 0.1,
                "config_update_timeout": 120,
                "health_check_timeout": 30,
            },
            "notification": {
                "webhooks": [],
                "slack_channels": [],
                "email_recipients": [],
            },
            "persistence": {
                "state_file": "/var/lib/monitoring/orchestrator-state.json",
                "metrics_file": "/var/lib/monitoring/orchestrator-metrics.json",
            },
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._deep_update(default_config, user_config)
            except Exception as e:
                print(f"Failed to load config: {e}")

        return default_config

    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> Dict:
        """Recursively update nested dictionaries."""
        for key, value in update_dict.items():
            if (
                isinstance(value, dict)
                and key in base_dict
                and isinstance(base_dict[key], dict)
            ):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
        return base_dict

    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.config.get("log_level", "INFO")),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("/var/log/monitoring-orchestrator.log"),
            ],
        )

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()

    async def start(self):
        """Start the monitoring orchestrator."""
        if self._running:
            self.logger.warning("Orchestrator already running")
            return

        self.logger.info("Starting monitoring orchestrator...")
        self.status = AutomationStatus.STARTING
        self._running = True

        try:
            # Load persisted state
            self._load_state()

            # Start background tasks
            self._tasks = [
                asyncio.create_task(self._discovery_loop()),
                asyncio.create_task(self._config_management_loop()),
                asyncio.create_task(self._health_check_loop()),
                asyncio.create_task(self._automation_features_loop()),
                asyncio.create_task(self._metrics_persistence_loop()),
            ]

            self.status = AutomationStatus.RUNNING
            self.logger.info("Monitoring orchestrator started successfully")

            # Wait for all tasks to complete
            await asyncio.gather(*self._tasks, return_exceptions=True)

        except Exception as e:
            self.logger.error(f"Orchestrator startup failed: {e}")
            self.status = AutomationStatus.ERROR
            raise

    def stop(self):
        """Stop the monitoring orchestrator."""
        if not self._running:
            return

        self.logger.info("Stopping monitoring orchestrator...")
        self.status = AutomationStatus.STOPPING
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Save state
        self._save_state()

        self.status = AutomationStatus.STOPPED
        self.logger.info("Monitoring orchestrator stopped")

    async def _discovery_loop(self):
        """Main service discovery loop."""
        interval = self.config.get("discovery_interval", 60)

        while self._running:
            try:
                self.logger.debug("Starting service discovery cycle")

                # Discover services
                services = self.service_discovery.discover_services()

                # Update metrics
                self.metrics.discovery_cycles += 1
                self.metrics.services_discovered = len(services)
                self.metrics.last_discovery = datetime.now()

                # Check for significant changes
                if self._services_changed(services):
                    self.logger.info(
                        f"Service changes detected, discovered {len(services)} services"
                    )
                    await self._handle_service_changes(services)

                self._last_services = services

                # Generate Prometheus targets
                targets = self.service_discovery.generate_prometheus_targets(services)
                self.service_discovery._write_prometheus_targets(targets)

                self.logger.debug(
                    f"Discovery cycle completed, found {len(services)} services"
                )

            except Exception as e:
                self.logger.error(f"Discovery loop error: {e}")

            await asyncio.sleep(interval)

    async def _config_management_loop(self):
        """Configuration management loop."""
        interval = self.config.get("config_update_interval", 300)

        while self._running:
            try:
                if self.config["config_manager"].get("auto_update", True):
                    self.logger.debug("Starting configuration update cycle")

                    # Update all configurations
                    self.config_manager.update_all_configurations()

                    # Update metrics
                    self.metrics.config_updates += 1
                    self.metrics.last_config_update = datetime.now()

                    # Check update status
                    status = self.config_manager.get_update_status()
                    self.metrics.successful_updates += status["successful_updates"]
                    self.metrics.failed_updates += status["failed_updates"]

                    self.logger.debug("Configuration update cycle completed")

            except Exception as e:
                self.logger.error(f"Config management loop error: {e}")
                self.metrics.failed_updates += 1

            await asyncio.sleep(interval)

    async def _health_check_loop(self):
        """Health monitoring loop for orchestrator components."""
        interval = self.config.get("health_check_interval", 30)

        while self._running:
            try:
                health_status = await self._perform_health_checks()

                if not health_status["overall_healthy"]:
                    self.logger.warning("Health check failures detected")
                    await self._handle_health_issues(health_status)

            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")

            await asyncio.sleep(interval)

    async def _automation_features_loop(self):
        """Execute automation features like auto-scaling, SLO monitoring, etc."""
        interval = 120  # Run every 2 minutes

        while self._running:
            try:
                features = self.config.get("automation_features", {})

                if features.get("auto_scaling_alerts", False):
                    await self._check_auto_scaling_needs()

                if features.get("slo_monitoring", False):
                    await self._monitor_slos()

                if features.get("cost_optimization", False):
                    await self._analyze_cost_optimization()

                if features.get("security_monitoring", False):
                    await self._monitor_security_events()

                if features.get("performance_tuning", False):
                    await self._analyze_performance_optimization()

            except Exception as e:
                self.logger.error(f"Automation features loop error: {e}")

            await asyncio.sleep(interval)

    async def _metrics_persistence_loop(self):
        """Persist metrics and state periodically."""
        interval = 60  # Save every minute

        while self._running:
            try:
                self._save_metrics()

            except Exception as e:
                self.logger.error(f"Metrics persistence error: {e}")

            await asyncio.sleep(interval)

    def _services_changed(self, current_services: List[DiscoveredService]) -> bool:
        """Check if services have changed significantly."""
        if not self._last_services:
            return True

        threshold = self.config["thresholds"].get("service_change_threshold", 0.1)

        # Compare service counts
        current_count = len(current_services)
        last_count = len(self._last_services)

        if abs(current_count - last_count) / max(last_count, 1) > threshold:
            return True

        # Compare service names
        current_names = {s.name for s in current_services}
        last_names = {s.name for s in self._last_services}

        if current_names != last_names:
            return True

        return False

    async def _handle_service_changes(self, services: List[DiscoveredService]):
        """Handle significant service changes."""
        self.logger.info("Handling service changes...")

        # Trigger immediate config update
        if self.config["config_manager"].get("enabled", True):
            try:
                self.config_manager.update_all_configurations()
                self.logger.info("Configuration updated due to service changes")
            except Exception as e:
                self.logger.error(f"Failed to update configuration: {e}")

        # Send notifications
        await self._send_service_change_notifications(services)

    async def _perform_health_checks(self) -> Dict[str, Any]:
        """Perform health checks on monitoring components."""
        health_status = {"overall_healthy": True, "components": {}}

        # Check service discovery health
        try:
            # Test if service discovery can load services
            services = self.service_discovery.discover_services()
            health_status["components"]["service_discovery"] = {
                "healthy": True,
                "services_count": len(services),
            }
        except Exception as e:
            health_status["components"]["service_discovery"] = {
                "healthy": False,
                "error": str(e),
            }
            health_status["overall_healthy"] = False

        # Check configuration manager health
        try:
            status = self.config_manager.get_update_status()
            failed_updates = status["failed_updates"]
            health_status["components"]["config_manager"] = {
                "healthy": failed_updates == 0,
                "failed_updates": failed_updates,
            }
            if failed_updates > 0:
                health_status["overall_healthy"] = False
        except Exception as e:
            health_status["components"]["config_manager"] = {
                "healthy": False,
                "error": str(e),
            }
            health_status["overall_healthy"] = False

        return health_status

    async def _handle_health_issues(self, health_status: Dict[str, Any]):
        """Handle health check failures."""
        self.logger.warning("Handling health issues...")

        for component, status in health_status["components"].items():
            if not status.get("healthy", False):
                self.logger.error(f"Component {component} is unhealthy: {status}")

                # Attempt recovery actions
                if component == "service_discovery":
                    # Restart discovery
                    self.logger.info("Attempting to restart service discovery")
                    # Implementation would restart the discovery component

                elif component == "config_manager":
                    # Reset config manager state
                    self.logger.info("Attempting to reset configuration manager")
                    # Implementation would reset config manager

    async def _check_auto_scaling_needs(self):
        """Check if any services need auto-scaling alerts."""
        # This would analyze metrics to determine scaling needs
        self.logger.debug("Checking auto-scaling needs")

    async def _monitor_slos(self):
        """Monitor SLO compliance and error budgets."""
        # This would check SLO metrics and alert on violations
        self.logger.debug("Monitoring SLOs")

    async def _analyze_cost_optimization(self):
        """Analyze cost optimization opportunities."""
        # This would analyze resource usage and costs
        self.logger.debug("Analyzing cost optimization")

    async def _monitor_security_events(self):
        """Monitor security events and anomalies."""
        # This would check security metrics and logs
        self.logger.debug("Monitoring security events")

    async def _analyze_performance_optimization(self):
        """Analyze performance optimization opportunities."""
        # This would analyze performance metrics
        self.logger.debug("Analyzing performance optimization")

    async def _send_service_change_notifications(
        self, services: List[DiscoveredService]
    ):
        """Send notifications about service changes."""
        notification_config = self.config.get("notification", {})

        message = f"Service discovery detected changes: {len(services)} services currently discovered"

        # Send to webhooks
        for webhook_url in notification_config.get("webhooks", []):
            try:
                # Implementation would send webhook notification
                self.logger.debug(f"Sending webhook notification to {webhook_url}")
            except Exception as e:
                self.logger.error(f"Failed to send webhook notification: {e}")

    def _save_state(self):
        """Save orchestrator state to file."""
        state_file = self.config["persistence"].get("state_file")
        if not state_file:
            return

        try:
            state = {
                "status": self.status.value,
                "last_services": [s.to_dict() for s in self._last_services],
                "saved_at": datetime.now().isoformat(),
            }

            os.makedirs(os.path.dirname(state_file), exist_ok=True)

            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def _load_state(self):
        """Load orchestrator state from file."""
        state_file = self.config["persistence"].get("state_file")
        if not state_file or not os.path.exists(state_file):
            return

        try:
            with open(state_file, "r") as f:
                state = json.load(f)

            # Restore last services
            self._last_services = [
                DiscoveredService(**s) for s in state.get("last_services", [])
            ]

            self.logger.info("Loaded orchestrator state from file")

        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")

    def _save_metrics(self):
        """Save metrics to file."""
        metrics_file = self.config["persistence"].get("metrics_file")
        if not metrics_file:
            return

        try:
            os.makedirs(os.path.dirname(metrics_file), exist_ok=True)

            with open(metrics_file, "w") as f:
                json.dump(self.metrics.to_dict(), f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status and metrics."""
        return {
            "status": self.status.value,
            "running": self._running,
            "metrics": self.metrics.to_dict(),
            "config": {
                "discovery_interval": self.config.get("discovery_interval"),
                "config_update_interval": self.config.get("config_update_interval"),
                "enabled_features": self.config.get("automation_features", {}),
            },
            "services_count": len(self._last_services),
        }


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Universal Platform Monitoring Orchestrator"
    )
    parser.add_argument(
        "--config", default="orchestrator-config.yaml", help="Configuration file path"
    )
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument(
        "--status", action="store_true", help="Show orchestrator status"
    )

    args = parser.parse_args()

    orchestrator = MonitoringOrchestrator(args.config)

    if args.status:
        status = orchestrator.get_status()
        print(json.dumps(status, indent=2))
    elif args.daemon:
        # Run as daemon
        try:
            asyncio.run(orchestrator.start())
        except KeyboardInterrupt:
            orchestrator.stop()
    else:
        print("Use --daemon to start or --status to check status")
        parser.print_help()
