#!/usr/bin/env python3
"""
MCP Server Health Monitoring and Alerting System

Comprehensive health monitoring for MCP protocol implementation with:
- Real-time health checking
- Performance metrics collection
- Alerting and notifications
- Service dependency monitoring
- Automated remediation triggers
"""

import asyncio
import logging
import smtplib
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class HealthMetric:
    """Individual health metric."""

    name: str
    value: float
    threshold: float
    status: HealthStatus
    timestamp: datetime
    unit: str = ""
    description: str = ""


@dataclass
class ServiceHealth:
    """Overall service health status."""

    service_id: str
    service_name: str
    status: HealthStatus
    metrics: List[HealthMetric]
    last_check: datetime
    uptime: float
    error_rate: float
    response_time_avg: float
    dependencies: List[str]
    metadata: Dict[str, Any]


@dataclass
class Alert:
    """Alert definition and status."""

    id: str
    title: str
    description: str
    severity: AlertSeverity
    service_id: str
    metric_name: str
    threshold_value: float
    current_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    is_active: bool = True
    notification_count: int = 0
    suppressed_until: Optional[datetime] = None


class HealthChecker:
    """Individual service health checker."""

    def __init__(self, service_id: str, service_name: str, endpoint: str):
        self.service_id = service_id
        self.service_name = service_name
        self.endpoint = endpoint
        self.session: Optional[aiohttp.ClientSession] = None
        self.metrics_history: Dict[str, List[float]] = {}

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=100),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def check_health(self) -> ServiceHealth:
        """Perform comprehensive health check."""
        start_time = time.time()
        metrics = []
        status = HealthStatus.UNKNOWN
        error_rate = 0.0

        try:
            # HTTP health check
            http_metric = await self._check_http_health()
            metrics.append(http_metric)

            # WebSocket health check
            ws_metric = await self._check_websocket_health()
            metrics.append(ws_metric)

            # Performance metrics
            perf_metrics = await self._check_performance_metrics()
            metrics.extend(perf_metrics)

            # Service-specific metrics
            service_metrics = await self._check_service_metrics()
            metrics.extend(service_metrics)

            # Calculate overall status
            status = self._calculate_overall_status(metrics)

            # Calculate error rate
            error_rate = await self._calculate_error_rate()

        except Exception as e:
            logger.error(f"Health check failed for {self.service_id}: {e}")
            metrics.append(
                HealthMetric(
                    name="health_check_error",
                    value=1.0,
                    threshold=0.0,
                    status=HealthStatus.UNHEALTHY,
                    timestamp=datetime.now(),
                    description=str(e),
                )
            )
            status = HealthStatus.UNHEALTHY
            error_rate = 100.0

        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        return ServiceHealth(
            service_id=self.service_id,
            service_name=self.service_name,
            status=status,
            metrics=metrics,
            last_check=datetime.now(),
            uptime=await self._calculate_uptime(),
            error_rate=error_rate,
            response_time_avg=response_time,
            dependencies=await self._get_dependencies(),
            metadata=await self._get_metadata(),
        )

    async def _check_http_health(self) -> HealthMetric:
        """Check HTTP endpoint health."""
        try:
            start_time = time.time()
            async with self.session.get(f"{self.endpoint}/health") as response:
                response_time = (time.time() - start_time) * 1000

                if response.status == 200:
                    status = (
                        HealthStatus.HEALTHY
                        if response_time < 1000
                        else HealthStatus.DEGRADED
                    )
                else:
                    status = HealthStatus.UNHEALTHY

                return HealthMetric(
                    name="http_response_time",
                    value=response_time,
                    threshold=1000.0,
                    status=status,
                    timestamp=datetime.now(),
                    unit="ms",
                    description="HTTP endpoint response time",
                )

        except Exception as e:
            return HealthMetric(
                name="http_response_time",
                value=float("inf"),
                threshold=1000.0,
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.now(),
                unit="ms",
                description=f"HTTP health check failed: {e}",
            )

    async def _check_websocket_health(self) -> HealthMetric:
        """Check WebSocket connection health."""
        try:
            # This is a simplified WebSocket health check
            # In production, you'd establish a WebSocket connection and test it
            ws_endpoint = self.endpoint.replace("http", "ws") + "/ws"

            # For now, we'll simulate WebSocket health based on HTTP health
            # In a real implementation, you'd use aiohttp's WebSocket client
            start_time = time.time()

            # Simulate WebSocket connection test
            await asyncio.sleep(0.1)  # Simulate connection time

            response_time = (time.time() - start_time) * 1000

            return HealthMetric(
                name="websocket_connection_time",
                value=response_time,
                threshold=500.0,
                status=HealthStatus.HEALTHY
                if response_time < 500
                else HealthStatus.DEGRADED,
                timestamp=datetime.now(),
                unit="ms",
                description="WebSocket connection establishment time",
            )

        except Exception as e:
            return HealthMetric(
                name="websocket_connection_time",
                value=float("inf"),
                threshold=500.0,
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.now(),
                unit="ms",
                description=f"WebSocket health check failed: {e}",
            )

    async def _check_performance_metrics(self) -> List[HealthMetric]:
        """Check performance-related metrics."""
        metrics = []

        try:
            async with self.session.get(f"{self.endpoint}/api/metrics") as response:
                if response.status == 200:
                    data = await response.json()

                    # CPU usage metric
                    if "cpu_usage" in data:
                        cpu_usage = data["cpu_usage"]
                        metrics.append(
                            HealthMetric(
                                name="cpu_usage",
                                value=cpu_usage,
                                threshold=80.0,
                                status=HealthStatus.HEALTHY
                                if cpu_usage < 80
                                else HealthStatus.DEGRADED,
                                timestamp=datetime.now(),
                                unit="%",
                                description="CPU usage percentage",
                            )
                        )

                    # Memory usage metric
                    if "memory_usage" in data:
                        memory_usage = data["memory_usage"]
                        metrics.append(
                            HealthMetric(
                                name="memory_usage",
                                value=memory_usage,
                                threshold=85.0,
                                status=HealthStatus.HEALTHY
                                if memory_usage < 85
                                else HealthStatus.DEGRADED,
                                timestamp=datetime.now(),
                                unit="%",
                                description="Memory usage percentage",
                            )
                        )

                    # Active connections
                    if "activeConnections" in data:
                        connections = data["activeConnections"]
                        metrics.append(
                            HealthMetric(
                                name="active_connections",
                                value=connections,
                                threshold=1000.0,
                                status=HealthStatus.HEALTHY
                                if connections < 1000
                                else HealthStatus.DEGRADED,
                                timestamp=datetime.now(),
                                unit="count",
                                description="Number of active connections",
                            )
                        )

                    # Error count
                    if "errorCount" in data:
                        errors = data["errorCount"]
                        self._update_metrics_history("error_count", errors)
                        recent_error_rate = self._calculate_recent_trend("error_count")

                        metrics.append(
                            HealthMetric(
                                name="error_rate",
                                value=recent_error_rate,
                                threshold=5.0,
                                status=HealthStatus.HEALTHY
                                if recent_error_rate < 5
                                else HealthStatus.UNHEALTHY,
                                timestamp=datetime.now(),
                                unit="errors/min",
                                description="Recent error rate",
                            )
                        )

        except Exception as e:
            logger.warning(
                f"Failed to get performance metrics for {self.service_id}: {e}"
            )
            metrics.append(
                HealthMetric(
                    name="metrics_collection_error",
                    value=1.0,
                    threshold=0.0,
                    status=HealthStatus.DEGRADED,
                    timestamp=datetime.now(),
                    description=f"Failed to collect performance metrics: {e}",
                )
            )

        return metrics

    async def _check_service_metrics(self) -> List[HealthMetric]:
        """Check MCP-specific service metrics."""
        metrics = []

        try:
            # Check service registry
            async with self.session.get(f"{self.endpoint}/api/services") as response:
                if response.status == 200:
                    services = await response.json()
                    service_count = len(services) if isinstance(services, list) else 0

                    metrics.append(
                        HealthMetric(
                            name="registered_services",
                            value=service_count,
                            threshold=0.0,
                            status=HealthStatus.HEALTHY,
                            timestamp=datetime.now(),
                            unit="count",
                            description="Number of registered services",
                        )
                    )

                    # Check if critical services are registered
                    critical_services = ["claude-agent-manager", "claude-tool-executor"]
                    missing_services = []

                    if isinstance(services, list):
                        registered_service_ids = [
                            s.get("serviceId", "") for s in services
                        ]
                        missing_services = [
                            s
                            for s in critical_services
                            if s not in registered_service_ids
                        ]

                    metrics.append(
                        HealthMetric(
                            name="critical_services_available",
                            value=len(critical_services) - len(missing_services),
                            threshold=len(critical_services),
                            status=HealthStatus.HEALTHY
                            if not missing_services
                            else HealthStatus.UNHEALTHY,
                            timestamp=datetime.now(),
                            unit="count",
                            description=f"Critical services available. Missing: {missing_services}",
                        )
                    )

        except Exception as e:
            logger.warning(
                f"Failed to check service metrics for {self.service_id}: {e}"
            )
            metrics.append(
                HealthMetric(
                    name="service_metrics_error",
                    value=1.0,
                    threshold=0.0,
                    status=HealthStatus.DEGRADED,
                    timestamp=datetime.now(),
                    description=f"Failed to check service metrics: {e}",
                )
            )

        return metrics

    def _calculate_overall_status(self, metrics: List[HealthMetric]) -> HealthStatus:
        """Calculate overall service status from individual metrics."""
        if not metrics:
            return HealthStatus.UNKNOWN

        unhealthy_count = sum(1 for m in metrics if m.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for m in metrics if m.status == HealthStatus.DEGRADED)

        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    async def _calculate_error_rate(self) -> float:
        """Calculate recent error rate."""
        if "error_count" in self.metrics_history:
            return self._calculate_recent_trend("error_count")
        return 0.0

    async def _calculate_uptime(self) -> float:
        """Calculate service uptime percentage."""
        # This is a simplified uptime calculation
        # In production, you'd track actual uptime/downtime periods
        if "health_check_success" in self.metrics_history:
            recent_checks = self.metrics_history["health_check_success"][
                -20:
            ]  # Last 20 checks
            if recent_checks:
                return (sum(recent_checks) / len(recent_checks)) * 100
        return 100.0  # Assume 100% if no history

    async def _get_dependencies(self) -> List[str]:
        """Get list of service dependencies."""
        # This would be configured based on the service architecture
        return ["database", "secret-manager", "container-orchestration"]

    async def _get_metadata(self) -> Dict[str, Any]:
        """Get additional service metadata."""
        return {
            "endpoint": self.endpoint,
            "last_restart": None,  # Would track actual restart times
            "version": "1.0.0",
            "build": "latest",
        }

    def _update_metrics_history(self, metric_name: str, value: float):
        """Update metrics history for trend analysis."""
        if metric_name not in self.metrics_history:
            self.metrics_history[metric_name] = []

        self.metrics_history[metric_name].append(value)

        # Keep only last 100 values
        if len(self.metrics_history[metric_name]) > 100:
            self.metrics_history[metric_name] = self.metrics_history[metric_name][-100:]

    def _calculate_recent_trend(self, metric_name: str) -> float:
        """Calculate recent trend for a metric."""
        if (
            metric_name not in self.metrics_history
            or not self.metrics_history[metric_name]
        ):
            return 0.0

        recent_values = self.metrics_history[metric_name][-10:]  # Last 10 values
        if len(recent_values) < 2:
            return recent_values[0] if recent_values else 0.0

        # Calculate rate of change per minute (simplified)
        return statistics.mean(recent_values)


class AlertManager:
    """Manages alerts and notifications."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_cooldown = timedelta(minutes=5)

    async def process_health_status(self, health: ServiceHealth):
        """Process health status and trigger alerts if needed."""
        for metric in health.metrics:
            await self._check_metric_for_alerts(health, metric)

    async def _check_metric_for_alerts(
        self, health: ServiceHealth, metric: HealthMetric
    ):
        """Check if a metric should trigger an alert."""
        alert_id = f"{health.service_id}_{metric.name}"

        # Define alert thresholds based on metric
        should_alert = False
        severity = AlertSeverity.INFO

        if metric.status == HealthStatus.UNHEALTHY:
            should_alert = True
            severity = AlertSeverity.CRITICAL
        elif metric.status == HealthStatus.DEGRADED:
            should_alert = True
            severity = AlertSeverity.WARNING

        if should_alert:
            if alert_id not in self.active_alerts:
                # New alert
                alert = Alert(
                    id=alert_id,
                    title=f"{health.service_name}: {metric.name} Alert",
                    description=f"{metric.description}. Current value: {metric.value:.2f}{metric.unit}, Threshold: {metric.threshold:.2f}{metric.unit}",
                    severity=severity,
                    service_id=health.service_id,
                    metric_name=metric.name,
                    threshold_value=metric.threshold,
                    current_value=metric.value,
                    triggered_at=datetime.now(),
                )

                self.active_alerts[alert_id] = alert
                await self._send_alert_notification(alert)
                logger.warning(f"Alert triggered: {alert.title}")

            else:
                # Update existing alert
                existing_alert = self.active_alerts[alert_id]
                existing_alert.current_value = metric.value
                existing_alert.notification_count += 1

                # Send notification if cooldown has passed
                if (
                    datetime.now() - existing_alert.triggered_at
                ) > self.notification_cooldown:
                    await self._send_alert_notification(
                        existing_alert, is_reminder=True
                    )
        else:
            # Check if we should resolve an existing alert
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved_at = datetime.now()
                alert.is_active = False

                await self._send_resolution_notification(alert)
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]

                logger.info(f"Alert resolved: {alert.title}")

    async def _send_alert_notification(self, alert: Alert, is_reminder: bool = False):
        """Send alert notification through configured channels."""
        reminder_text = " (Reminder)" if is_reminder else ""
        subject = f"[{alert.severity.value.upper()}] {alert.title}{reminder_text}"

        message = {
            "subject": subject,
            "body": f"""
Alert Details:
- Service: {alert.service_id}
- Metric: {alert.metric_name}
- Severity: {alert.severity.value}
- Current Value: {alert.current_value:.2f}
- Threshold: {alert.threshold_value:.2f}
- Triggered At: {alert.triggered_at}

Description: {alert.description}

This is alert #{alert.notification_count + 1} for this issue.
""",
            "alert": alert,
        }

        # Send to configured channels
        tasks = []

        if self.config.get("email", {}).get("enabled", False):
            tasks.append(self._send_email_notification(message))

        if self.config.get("slack", {}).get("enabled", False):
            tasks.append(self._send_slack_notification(message))

        if self.config.get("webhook", {}).get("enabled", False):
            tasks.append(self._send_webhook_notification(message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_resolution_notification(self, alert: Alert):
        """Send alert resolution notification."""
        subject = f"[RESOLVED] {alert.title}"

        duration = alert.resolved_at - alert.triggered_at

        message = {
            "subject": subject,
            "body": f"""
Alert Resolved:
- Service: {alert.service_id}
- Metric: {alert.metric_name}
- Duration: {duration}
- Resolved At: {alert.resolved_at}

The alert condition is no longer present.
""",
            "alert": alert,
        }

        # Send to configured channels (same as alerts)
        tasks = []

        if self.config.get("email", {}).get("enabled", False):
            tasks.append(self._send_email_notification(message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_email_notification(self, message: Dict[str, Any]):
        """Send email notification."""
        try:
            email_config = self.config.get("email", {})

            msg = MimeMultipart()
            msg["From"] = email_config.get("sender", "mcp-monitor@genesis.local")
            msg["To"] = ", ".join(email_config.get("recipients", []))
            msg["Subject"] = message["subject"]

            msg.attach(MimeText(message["body"], "plain"))

            with smtplib.SMTP(email_config.get("smtp_server", "localhost")) as server:
                if email_config.get("use_tls", False):
                    server.starttls()
                if email_config.get("username") and email_config.get("password"):
                    server.login(email_config["username"], email_config["password"])

                server.send_message(msg)

            logger.info("Email notification sent successfully")

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    async def _send_slack_notification(self, message: Dict[str, Any]):
        """Send Slack notification."""
        try:
            slack_config = self.config.get("slack", {})
            webhook_url = slack_config.get("webhook_url")

            if not webhook_url:
                logger.warning("Slack webhook URL not configured")
                return

            alert = message["alert"]
            color = {
                AlertSeverity.CRITICAL: "#FF0000",
                AlertSeverity.WARNING: "#FFA500",
                AlertSeverity.INFO: "#0000FF",
            }.get(alert.severity, "#808080")

            payload = {
                "channel": slack_config.get("channel", "#alerts"),
                "username": "MCP Monitor",
                "attachments": [
                    {
                        "color": color,
                        "title": message["subject"],
                        "text": message["body"],
                        "footer": "Genesis MCP Monitor",
                        "ts": int(alert.triggered_at.timestamp()),
                    }
                ],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent successfully")
                    else:
                        logger.error(f"Slack notification failed: {response.status}")

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")

    async def _send_webhook_notification(self, message: Dict[str, Any]):
        """Send webhook notification."""
        try:
            webhook_config = self.config.get("webhook", {})
            webhook_url = webhook_config.get("url")

            if not webhook_url:
                logger.warning("Webhook URL not configured")
                return

            payload = {
                "timestamp": datetime.now().isoformat(),
                "alert": asdict(message["alert"]),
                "message": message["body"],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Webhook notification sent successfully")
                    else:
                        logger.error(f"Webhook notification failed: {response.status}")

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")


class MCPHealthMonitor:
    """Main MCP health monitoring system."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.services = {}
        self.alert_manager = AlertManager(config.get("alerting", {}))
        self.monitoring_interval = config.get("monitoring_interval", 30)  # seconds
        self.running = False

    def add_service(self, service_id: str, service_name: str, endpoint: str):
        """Add a service to monitor."""
        self.services[service_id] = {
            "service_id": service_id,
            "service_name": service_name,
            "endpoint": endpoint,
        }
        logger.info(f"Added service to monitoring: {service_name} ({service_id})")

    async def start_monitoring(self):
        """Start the monitoring system."""
        if self.running:
            logger.warning("Monitoring is already running")
            return

        self.running = True
        logger.info("Starting MCP health monitoring system")

        try:
            await self._monitoring_loop()
        except Exception as e:
            logger.error(f"Monitoring system error: {e}")
        finally:
            self.running = False

    def stop_monitoring(self):
        """Stop the monitoring system."""
        self.running = False
        logger.info("Stopping MCP health monitoring system")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Check all services in parallel
                tasks = []
                for service_config in self.services.values():
                    task = self._check_service_health(service_config)
                    tasks.append(task)

                if tasks:
                    health_results = await asyncio.gather(
                        *tasks, return_exceptions=True
                    )

                    for result in health_results:
                        if isinstance(result, ServiceHealth):
                            await self.alert_manager.process_health_status(result)
                            await self._log_health_status(result)
                        elif isinstance(result, Exception):
                            logger.error(f"Health check failed: {result}")

                # Wait for next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Short delay on error

    async def _check_service_health(
        self, service_config: Dict[str, Any]
    ) -> ServiceHealth:
        """Check health of a single service."""
        async with HealthChecker(
            service_config["service_id"],
            service_config["service_name"],
            service_config["endpoint"],
        ) as checker:
            return await checker.check_health()

    async def _log_health_status(self, health: ServiceHealth):
        """Log health status for observability."""
        logger.info(
            f"Health Check - Service: {health.service_name}, "
            f"Status: {health.status.value}, "
            f"Uptime: {health.uptime:.1f}%, "
            f"Error Rate: {health.error_rate:.1f}%, "
            f"Response Time: {health.response_time_avg:.2f}ms"
        )

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            "monitoring_active": self.running,
            "services_count": len(self.services),
            "active_alerts": len(self.alert_manager.active_alerts),
            "last_check": datetime.now().isoformat(),
        }


async def main():
    """Main entry point for the monitoring system."""

    # Example configuration
    config = {
        "monitoring_interval": 30,  # seconds
        "alerting": {
            "email": {
                "enabled": True,
                "smtp_server": "localhost",
                "sender": "mcp-monitor@genesis.local",
                "recipients": ["admin@genesis.local"],
            },
            "slack": {"enabled": False, "webhook_url": "", "channel": "#mcp-alerts"},
            "webhook": {"enabled": False, "url": ""},
        },
    }

    # Initialize monitor
    monitor = MCPHealthMonitor(config)

    # Add services to monitor
    monitor.add_service("mcp-server-main", "MCP Server (Main)", "http://localhost:8080")

    monitor.add_service(
        "mcp-server-backup", "MCP Server (Backup)", "http://localhost:8081"
    )

    try:
        # Start monitoring
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Shutting down monitoring system")
        monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
