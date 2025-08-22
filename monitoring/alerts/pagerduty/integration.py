"""
PagerDuty Integration for Critical Alert Management
Provides comprehensive incident management and escalation procedures.
"""

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Requests library not available, PagerDuty integration will be limited")

try:
    from pdpyras import APISession, EventsAPISession

    PDPYRAS_AVAILABLE = True
except ImportError:
    PDPYRAS_AVAILABLE = False
    print("PagerDuty library not available, using direct API calls")


class Severity(Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IncidentStatus(Enum):
    """PagerDuty incident status."""

    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class AlertContext:
    """Context information for alerts."""

    service_name: str
    environment: str
    region: str = "us-central1"
    project_id: str = "unknown"
    team: str = "platform"
    runbook_url: str = ""
    dashboard_url: str = ""
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Definition of an alert rule."""

    name: str
    description: str
    severity: Severity
    query: str
    threshold: float
    duration: str = "5m"
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    def to_prometheus_rule(self) -> Dict[str, Any]:
        """Convert to Prometheus alert rule format."""
        return {
            "alert": self.name,
            "expr": self.query,
            "for": self.duration,
            "labels": {"severity": self.severity.value, **self.labels},
            "annotations": {"description": self.description, **self.annotations},
        }


class PagerDutyIntegration:
    """PagerDuty integration for incident management."""

    def __init__(
        self,
        api_token: str = None,
        integration_key: str = None,
        service_id: str = None,
        escalation_policy_id: str = None,
        default_urgency: str = "high",
    ):
        self.api_token = api_token or os.getenv("PAGERDUTY_API_TOKEN")
        self.integration_key = integration_key or os.getenv("PAGERDUTY_INTEGRATION_KEY")
        self.service_id = service_id or os.getenv("PAGERDUTY_SERVICE_ID")
        self.escalation_policy_id = escalation_policy_id or os.getenv(
            "PAGERDUTY_ESCALATION_POLICY_ID"
        )
        self.default_urgency = default_urgency

        self.session = None
        self.events_session = None

        if PDPYRAS_AVAILABLE and self.api_token:
            self.session = APISession(self.api_token)

        if PDPYRAS_AVAILABLE and self.integration_key:
            self.events_session = EventsAPISession(self.integration_key)

    def create_incident(
        self,
        title: str,
        description: str,
        severity: Severity,
        context: AlertContext,
        dedup_key: str = None,
        urgency: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new PagerDuty incident."""
        if not self.events_session and not REQUESTS_AVAILABLE:
            logging.error("Neither PagerDuty library nor requests available")
            return None

        # Determine urgency based on severity
        if urgency is None:
            urgency = (
                "high" if severity in [Severity.CRITICAL, Severity.ERROR] else "low"
            )

        # Build event payload
        payload = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "dedup_key": dedup_key or f"{context.service_name}-{int(time.time())}",
            "payload": {
                "summary": title,
                "source": f"{context.service_name} ({context.environment})",
                "severity": severity.value,
                "component": context.service_name,
                "group": context.team,
                "class": "monitoring",
                "custom_details": {
                    "description": description,
                    "environment": context.environment,
                    "region": context.region,
                    "project_id": context.project_id,
                    "runbook_url": context.runbook_url,
                    "dashboard_url": context.dashboard_url,
                    **context.additional_context,
                },
            },
            "client": "Universal Platform Monitoring",
            "client_url": context.dashboard_url
            or "https://monitoring.universal-platform.com",
        }

        try:
            if self.events_session:
                # Use PagerDuty library
                response = self.events_session.trigger(**payload)
                logging.info(f"PagerDuty incident created: {response}")
                return response
            elif REQUESTS_AVAILABLE:
                # Use direct API call
                response = requests.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()
                logging.info(f"PagerDuty incident created: {result}")
                return result

        except Exception as e:
            logging.error(f"Failed to create PagerDuty incident: {e}")
            return None

    def resolve_incident(self, dedup_key: str, resolution_note: str = "") -> bool:
        """Resolve a PagerDuty incident."""
        payload = {
            "routing_key": self.integration_key,
            "event_action": "resolve",
            "dedup_key": dedup_key,
        }

        if resolution_note:
            payload["payload"] = {
                "summary": resolution_note,
                "source": "Universal Platform Monitoring",
            }

        try:
            if self.events_session:
                response = self.events_session.resolve(dedup_key)
                logging.info(f"PagerDuty incident resolved: {response}")
                return True
            elif REQUESTS_AVAILABLE:
                response = requests.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                response.raise_for_status()
                logging.info("PagerDuty incident resolved successfully")
                return True

        except Exception as e:
            logging.error(f"Failed to resolve PagerDuty incident: {e}")
            return False

        return False

    def acknowledge_incident(self, dedup_key: str, ack_note: str = "") -> bool:
        """Acknowledge a PagerDuty incident."""
        payload = {
            "routing_key": self.integration_key,
            "event_action": "acknowledge",
            "dedup_key": dedup_key,
        }

        if ack_note:
            payload["payload"] = {
                "summary": ack_note,
                "source": "Universal Platform Monitoring",
            }

        try:
            if self.events_session:
                response = self.events_session.acknowledge(dedup_key)
                logging.info(f"PagerDuty incident acknowledged: {response}")
                return True
            elif REQUESTS_AVAILABLE:
                response = requests.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                response.raise_for_status()
                logging.info("PagerDuty incident acknowledged successfully")
                return True

        except Exception as e:
            logging.error(f"Failed to acknowledge PagerDuty incident: {e}")
            return False

        return False

    def get_incidents(
        self,
        status: List[IncidentStatus] = None,
        service_ids: List[str] = None,
        since: datetime = None,
        until: datetime = None,
    ) -> List[Dict[str, Any]]:
        """Get incidents from PagerDuty."""
        if not self.session:
            logging.error("PagerDuty API session not available")
            return []

        params = {}

        if status:
            params["statuses[]"] = [s.value for s in status]

        if service_ids:
            params["service_ids[]"] = service_ids
        elif self.service_id:
            params["service_ids[]"] = [self.service_id]

        if since:
            params["since"] = since.isoformat()

        if until:
            params["until"] = until.isoformat()

        try:
            incidents = list(self.session.list_all("incidents", params=params))
            logging.info(f"Retrieved {len(incidents)} incidents from PagerDuty")
            return incidents

        except Exception as e:
            logging.error(f"Failed to get PagerDuty incidents: {e}")
            return []

    def create_service(
        self, name: str, description: str = "", escalation_policy_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new PagerDuty service."""
        if not self.session:
            logging.error("PagerDuty API session not available")
            return None

        escalation_policy_id = escalation_policy_id or self.escalation_policy_id
        if not escalation_policy_id:
            logging.error("Escalation policy ID required to create service")
            return None

        service_data = {
            "name": name,
            "description": description,
            "escalation_policy": {
                "id": escalation_policy_id,
                "type": "escalation_policy",
            },
            "alert_creation": "create_alerts_and_incidents",
        }

        try:
            service = self.session.post("services", json={"service": service_data})
            logging.info(f"Created PagerDuty service: {service['id']}")
            return service

        except Exception as e:
            logging.error(f"Failed to create PagerDuty service: {e}")
            return None

    def create_integration(
        self,
        service_id: str,
        integration_type: str = "generic_events_api_inbound_integration",
        name: str = "Universal Platform Integration",
    ) -> Optional[Dict[str, Any]]:
        """Create a new integration for a service."""
        if not self.session:
            logging.error("PagerDuty API session not available")
            return None

        integration_data = {
            "type": integration_type,
            "name": name,
            "service": {"id": service_id, "type": "service"},
        }

        try:
            integration = self.session.post(
                f"services/{service_id}/integrations",
                json={"integration": integration_data},
            )
            logging.info(f"Created PagerDuty integration: {integration['id']}")
            return integration

        except Exception as e:
            logging.error(f"Failed to create PagerDuty integration: {e}")
            return None


class AlertRuleManager:
    """Manager for alert rules and conditions."""

    def __init__(self, rules_file: str = "alert_rules.yaml"):
        self.rules_file = rules_file
        self.rules: List[AlertRule] = []
        self.load_rules()

    def load_rules(self):
        """Load alert rules from configuration file."""
        if not os.path.exists(self.rules_file):
            logging.warning(f"Alert rules file not found: {self.rules_file}")
            self._create_default_rules()
            return

        try:
            import yaml

            with open(self.rules_file, "r") as f:
                rules_config = yaml.safe_load(f)

            self.rules = []
            for rule_config in rules_config.get("rules", []):
                rule = AlertRule(
                    name=rule_config["name"],
                    description=rule_config["description"],
                    severity=Severity(rule_config["severity"]),
                    query=rule_config["query"],
                    threshold=rule_config["threshold"],
                    duration=rule_config.get("duration", "5m"),
                    labels=rule_config.get("labels", {}),
                    annotations=rule_config.get("annotations", {}),
                    enabled=rule_config.get("enabled", True),
                )
                self.rules.append(rule)

            logging.info(f"Loaded {len(self.rules)} alert rules")

        except Exception as e:
            logging.error(f"Failed to load alert rules: {e}")
            self._create_default_rules()

    def _create_default_rules(self):
        """Create default alert rules."""
        self.rules = [
            AlertRule(
                name="HighErrorRate",
                description="High error rate detected",
                severity=Severity.CRITICAL,
                query='rate(http_requests_total{code=~"5.."}[5m]) > 0.1',
                threshold=0.1,
                labels={"team": "platform"},
                annotations={
                    "runbook_url": "https://runbooks.universal-platform.com/high-error-rate",
                    "dashboard_url": "https://monitoring.universal-platform.com/errors",
                },
            ),
            AlertRule(
                name="HighLatency",
                description="High response latency detected",
                severity=Severity.WARNING,
                query="histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0",
                threshold=1.0,
                labels={"team": "platform"},
                annotations={
                    "runbook_url": "https://runbooks.universal-platform.com/high-latency",
                    "dashboard_url": "https://monitoring.universal-platform.com/latency",
                },
            ),
            AlertRule(
                name="ServiceDown",
                description="Service is not responding",
                severity=Severity.CRITICAL,
                query="up == 0",
                threshold=0,
                duration="1m",
                labels={"team": "platform"},
                annotations={
                    "runbook_url": "https://runbooks.universal-platform.com/service-down",
                    "dashboard_url": "https://monitoring.universal-platform.com/uptime",
                },
            ),
        ]

    def get_prometheus_rules(self) -> Dict[str, Any]:
        """Get rules in Prometheus format."""
        return {
            "groups": [
                {
                    "name": "universal_platform_alerts",
                    "rules": [
                        rule.to_prometheus_rule() for rule in self.rules if rule.enabled
                    ],
                }
            ]
        }

    def add_rule(self, rule: AlertRule):
        """Add a new alert rule."""
        self.rules.append(rule)
        self.save_rules()

    def remove_rule(self, name: str) -> bool:
        """Remove an alert rule by name."""
        initial_count = len(self.rules)
        self.rules = [rule for rule in self.rules if rule.name != name]
        if len(self.rules) < initial_count:
            self.save_rules()
            return True
        return False

    def save_rules(self):
        """Save alert rules to configuration file."""
        try:
            import yaml

            rules_config = {
                "rules": [
                    {
                        "name": rule.name,
                        "description": rule.description,
                        "severity": rule.severity.value,
                        "query": rule.query,
                        "threshold": rule.threshold,
                        "duration": rule.duration,
                        "labels": rule.labels,
                        "annotations": rule.annotations,
                        "enabled": rule.enabled,
                    }
                    for rule in self.rules
                ]
            }

            with open(self.rules_file, "w") as f:
                yaml.dump(rules_config, f, default_flow_style=False, indent=2)

            logging.info(f"Saved {len(self.rules)} alert rules to {self.rules_file}")

        except Exception as e:
            logging.error(f"Failed to save alert rules: {e}")


# Global instances
_global_pagerduty = None
_global_rule_manager = None


def get_pagerduty() -> PagerDutyIntegration:
    """Get the global PagerDuty integration instance."""
    global _global_pagerduty
    if _global_pagerduty is None:
        _global_pagerduty = PagerDutyIntegration()
    return _global_pagerduty


def get_rule_manager() -> AlertRuleManager:
    """Get the global alert rule manager instance."""
    global _global_rule_manager
    if _global_rule_manager is None:
        _global_rule_manager = AlertRuleManager()
    return _global_rule_manager


# Convenience functions
def create_critical_alert(
    title: str, description: str, context: AlertContext, dedup_key: str = None
):
    """Create a critical alert that goes to PagerDuty."""
    pd = get_pagerduty()
    return pd.create_incident(title, description, Severity.CRITICAL, context, dedup_key)


def resolve_alert(dedup_key: str, resolution_note: str = ""):
    """Resolve an alert."""
    pd = get_pagerduty()
    return pd.resolve_incident(dedup_key, resolution_note)
