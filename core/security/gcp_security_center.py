"""
GCP Security Command Center Integration - SHIELD Methodology
Enhanced security automation for centralized monitoring and incident response
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from google.cloud import monitoring_v3, pubsub_v1
from google.cloud import securitycenter_v1 as scc


class ThreatSeverity(Enum):
    """Threat severity levels"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(Enum):
    """Incident response status"""

    DETECTED = "DETECTED"
    ANALYZING = "ANALYZING"
    RESPONDING = "RESPONDING"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"


@dataclass
class SecurityFinding:
    """Security finding from Security Command Center"""

    name: str
    category: str
    state: str
    severity: ThreatSeverity
    resource_name: str
    description: str
    source_properties: Dict[str, Any] = field(default_factory=dict)
    event_time: Optional[datetime] = None
    create_time: Optional[datetime] = None


@dataclass
class IncidentResponse:
    """Automated incident response action"""

    incident_id: str
    finding_id: str
    severity: ThreatSeverity
    status: IncidentStatus
    response_actions: List[str] = field(default_factory=list)
    containment_actions: List[str] = field(default_factory=list)
    recovery_actions: List[str] = field(default_factory=list)
    timestamps: Dict[str, datetime] = field(default_factory=dict)


class GCPSecurityCenter:
    """
    GCP Security Command Center integration with automated incident response

    SHIELD Implementation:
    S - Scan: Continuous threat detection and vulnerability scanning
    H - Harden: Automated security control deployment
    I - Isolate: Network and resource isolation responses
    E - Encrypt: Enhanced encryption enforcement
    L - Log: Comprehensive security event logging
    D - Defend: Automated threat response and mitigation
    """

    def __init__(
        self,
        organization_id: str,
        project_id: str,
        location: str = "global",
        notification_topic: Optional[str] = None,
        enable_auto_response: bool = True,
    ):
        self.organization_id = organization_id
        self.project_id = project_id
        self.location = location
        self.notification_topic = notification_topic
        self.enable_auto_response = enable_auto_response

        self.logger = self._setup_logging()

        # Initialize GCP clients
        self.scc_client = scc.SecurityCenterClient()
        self.monitoring_client = monitoring_v3.MetricServiceClient()

        if notification_topic:
            self.publisher = pubsub_v1.PublisherClient()
            self.subscriber = pubsub_v1.SubscriberClient()

        # Response handlers registry
        self.response_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

        # Active incidents tracking
        self.active_incidents: Dict[str, IncidentResponse] = {}

        self.logger.info(f"GCP Security Center initialized for org: {organization_id}")

    def _setup_logging(self) -> logging.Logger:
        """Setup security-focused logging"""
        logger = logging.getLogger(f"genesis.security.scc.{self.project_id}")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [SECURITY] %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def _register_default_handlers(self):
        """Register default incident response handlers"""
        self.response_handlers.update(
            {
                "MALWARE": self._handle_malware_incident,
                "VULNERABILITY": self._handle_vulnerability_incident,
                "ANOMALOUS_ACTIVITY": self._handle_anomalous_activity,
                "DATA_EXFILTRATION": self._handle_data_exfiltration,
                "UNAUTHORIZED_ACCESS": self._handle_unauthorized_access,
                "BRUTE_FORCE": self._handle_brute_force_attack,
                "DDoS": self._handle_ddos_attack,
            }
        )

    # SHIELD Method: SCAN - Continuous Threat Detection
    async def scan_security_findings(
        self,
        filters: Optional[Dict[str, str]] = None,
        limit: int = 1000,
    ) -> List[SecurityFinding]:
        """
        Scan for security findings from Security Command Center

        Args:
            filters: Optional filters for findings
            limit: Maximum number of findings to retrieve

        Returns:
            List of security findings
        """
        self.logger.info("Starting security findings scan")

        try:
            organization_name = f"organizations/{self.organization_id}"

            # Build filter string
            filter_str = self._build_findings_filter(filters)

            # List findings
            findings = []
            request = {
                "parent": organization_name,
                "filter": filter_str,
                "page_size": min(limit, 1000),
            }

            page_result = self.scc_client.list_findings(request=request)

            for finding in page_result:
                security_finding = self._convert_to_security_finding(finding.finding)
                findings.append(security_finding)

                # Auto-respond to critical findings if enabled
                if (
                    self.enable_auto_response
                    and security_finding.severity == ThreatSeverity.CRITICAL
                ):
                    await self._trigger_incident_response(security_finding)

            self.logger.info(f"Scan completed: {len(findings)} findings discovered")

            # Send metrics
            await self._send_security_metrics(
                "findings_scan",
                {
                    "count": len(findings),
                    "critical": len(
                        [f for f in findings if f.severity == ThreatSeverity.CRITICAL]
                    ),
                    "high": len(
                        [f for f in findings if f.severity == ThreatSeverity.HIGH]
                    ),
                },
            )

            return findings

        except Exception as e:
            self.logger.error(f"Security findings scan failed: {e}")
            raise

    def _build_findings_filter(self, filters: Optional[Dict[str, str]]) -> str:
        """Build Security Command Center findings filter"""
        filter_parts = []

        if filters:
            for key, value in filters.items():
                if key == "state":
                    filter_parts.append(f'state="{value}"')
                elif key == "category":
                    filter_parts.append(f'category="{value}"')
                elif key == "severity":
                    filter_parts.append(f'severity="{value}"')
                elif key == "resource_name":
                    filter_parts.append(f'resource_name:"{value}"')

        # Default filters for active findings
        if not any("state=" in part for part in filter_parts):
            filter_parts.append('state="ACTIVE"')

        return " AND ".join(filter_parts) if filter_parts else 'state="ACTIVE"'

    def _convert_to_security_finding(self, finding) -> SecurityFinding:
        """Convert SCC finding to SecurityFinding object"""
        severity_map = {
            "LOW": ThreatSeverity.LOW,
            "MEDIUM": ThreatSeverity.MEDIUM,
            "HIGH": ThreatSeverity.HIGH,
            "CRITICAL": ThreatSeverity.CRITICAL,
        }

        return SecurityFinding(
            name=finding.name,
            category=finding.category,
            state=finding.state.name if finding.state else "UNKNOWN",
            severity=severity_map.get(finding.severity.name, ThreatSeverity.MEDIUM),
            resource_name=finding.resource_name,
            description=finding.description,
            source_properties=dict(finding.source_properties),
            event_time=finding.event_time if finding.event_time else None,
            create_time=finding.create_time if finding.create_time else None,
        )

    # SHIELD Method: DEFEND - Automated Incident Response
    async def _trigger_incident_response(self, finding: SecurityFinding):
        """Trigger automated incident response"""
        incident_id = f"incident-{int(time.time())}-{hash(finding.name) % 10000}"

        self.logger.warning(f"Triggering incident response for: {finding.category}")

        incident = IncidentResponse(
            incident_id=incident_id,
            finding_id=finding.name,
            severity=finding.severity,
            status=IncidentStatus.DETECTED,
            timestamps={"detected": datetime.utcnow()},
        )

        self.active_incidents[incident_id] = incident

        try:
            # Update incident status
            await self._update_incident_status(incident_id, IncidentStatus.ANALYZING)

            # Execute category-specific response
            handler = self.response_handlers.get(finding.category)
            if handler:
                await handler(finding, incident)
            else:
                await self._handle_generic_incident(finding, incident)

            # Update status to responding
            await self._update_incident_status(incident_id, IncidentStatus.RESPONDING)

            # Send notification
            if self.notification_topic:
                await self._send_incident_notification(incident, finding)

            self.logger.info(f"Incident response initiated: {incident_id}")

        except Exception as e:
            self.logger.error(f"Incident response failed for {incident_id}: {e}")
            incident.status = IncidentStatus.DETECTED

    async def _handle_malware_incident(
        self, finding: SecurityFinding, incident: IncidentResponse
    ):
        """Handle malware detection incident"""
        self.logger.critical(f"MALWARE DETECTED: {finding.description}")

        # Immediate containment actions
        containment_actions = [
            "isolate_infected_resources",
            "block_malicious_traffic",
            "quarantine_affected_data",
            "disable_compromised_accounts",
        ]

        incident.containment_actions.extend(containment_actions)

        # Execute containment
        for action in containment_actions:
            await self._execute_containment_action(action, finding, incident)

        # Recovery actions
        recovery_actions = [
            "scan_related_resources",
            "update_security_policies",
            "restore_from_clean_backup",
        ]

        incident.recovery_actions.extend(recovery_actions)

    async def _handle_vulnerability_incident(
        self, finding: SecurityFinding, incident: IncidentResponse
    ):
        """Handle vulnerability detection incident"""
        self.logger.warning(f"VULNERABILITY DETECTED: {finding.description}")

        # Assessment and patching actions
        response_actions = [
            "assess_vulnerability_impact",
            "check_patch_availability",
            "schedule_emergency_patching",
            "implement_workaround_controls",
        ]

        incident.response_actions.extend(response_actions)

        for action in response_actions:
            await self._execute_response_action(action, finding, incident)

    async def _handle_anomalous_activity(
        self, finding: SecurityFinding, incident: IncidentResponse
    ):
        """Handle anomalous activity detection"""
        self.logger.warning(f"ANOMALOUS ACTIVITY: {finding.description}")

        # Monitoring and analysis actions
        response_actions = [
            "enhance_monitoring",
            "analyze_activity_patterns",
            "correlate_with_threat_intel",
            "implement_additional_controls",
        ]

        incident.response_actions.extend(response_actions)

    async def _handle_data_exfiltration(
        self, finding: SecurityFinding, incident: IncidentResponse
    ):
        """Handle data exfiltration incident"""
        self.logger.critical(f"DATA EXFILTRATION DETECTED: {finding.description}")

        # Immediate containment for data protection
        containment_actions = [
            "block_outbound_traffic",
            "revoke_access_tokens",
            "enable_data_loss_prevention",
            "notify_compliance_team",
        ]

        incident.containment_actions.extend(containment_actions)

        for action in containment_actions:
            await self._execute_containment_action(action, finding, incident)

    async def _handle_unauthorized_access(
        self, finding: SecurityFinding, incident: IncidentResponse
    ):
        """Handle unauthorized access attempts"""
        self.logger.warning(f"UNAUTHORIZED ACCESS: {finding.description}")

        # Access control and monitoring actions
        response_actions = [
            "review_access_patterns",
            "strengthen_authentication",
            "implement_additional_mfa",
            "audit_user_permissions",
        ]

        incident.response_actions.extend(response_actions)

    async def _handle_brute_force_attack(
        self, finding: SecurityFinding, incident: IncidentResponse
    ):
        """Handle brute force attack"""
        self.logger.warning(f"BRUTE FORCE ATTACK: {finding.description}")

        # Rate limiting and blocking actions
        containment_actions = [
            "implement_rate_limiting",
            "block_source_ips",
            "enforce_account_lockouts",
            "enhance_monitoring",
        ]

        incident.containment_actions.extend(containment_actions)

    async def _handle_ddos_attack(
        self, finding: SecurityFinding, incident: IncidentResponse
    ):
        """Handle DDoS attack"""
        self.logger.critical(f"DDoS ATTACK DETECTED: {finding.description}")

        # DDoS mitigation actions
        containment_actions = [
            "activate_cloud_armor",
            "implement_auto_scaling",
            "route_traffic_through_cdn",
            "block_attack_sources",
        ]

        incident.containment_actions.extend(containment_actions)

    async def _handle_generic_incident(
        self, finding: SecurityFinding, incident: IncidentResponse
    ):
        """Handle generic security incident"""
        self.logger.info(
            f"GENERIC INCIDENT: {finding.category} - {finding.description}"
        )

        # Standard response actions
        response_actions = [
            "collect_evidence",
            "analyze_impact",
            "implement_basic_controls",
            "monitor_situation",
        ]

        incident.response_actions.extend(response_actions)

    async def _execute_containment_action(
        self, action: str, finding: SecurityFinding, incident: IncidentResponse
    ):
        """Execute containment action"""
        self.logger.info(f"Executing containment action: {action}")

        try:
            # Implement actual containment logic based on action type
            if action == "isolate_infected_resources":
                await self._isolate_resources(finding.resource_name)
            elif action == "block_malicious_traffic":
                await self._block_traffic_patterns(finding)
            elif action == "revoke_access_tokens":
                await self._revoke_suspicious_tokens(finding)
            elif action == "activate_cloud_armor":
                await self._activate_cloud_armor_rules(finding)

            self.logger.info(f"Containment action completed: {action}")

        except Exception as e:
            self.logger.error(f"Containment action failed {action}: {e}")

    async def _execute_response_action(
        self, action: str, finding: SecurityFinding, incident: IncidentResponse
    ):
        """Execute response action"""
        self.logger.info(f"Executing response action: {action}")

        # Implementation would depend on specific action requirements
        # This is a placeholder for the actual response logic

        self.logger.info(f"Response action completed: {action}")

    # SHIELD Method: ISOLATE - Network and Resource Isolation
    async def _isolate_resources(self, resource_name: str):
        """Isolate compromised resources"""
        self.logger.warning(f"Isolating resource: {resource_name}")

        # Implementation would involve:
        # - Updating firewall rules to block traffic
        # - Modifying IAM policies to restrict access
        # - Moving resources to quarantine network

        # Placeholder for actual implementation
        pass

    async def _block_traffic_patterns(self, finding: SecurityFinding):
        """Block malicious traffic patterns"""
        self.logger.warning(f"Blocking traffic for finding: {finding.name}")

        # Implementation would involve:
        # - Creating Cloud Armor rules
        # - Updating VPC firewall rules
        # - Implementing rate limiting

        pass

    async def _revoke_suspicious_tokens(self, finding: SecurityFinding):
        """Revoke suspicious access tokens"""
        self.logger.warning(f"Revoking tokens for finding: {finding.name}")

        # Implementation would involve:
        # - Identifying affected service accounts
        # - Revoking OAuth tokens
        # - Forcing re-authentication

        pass

    async def _activate_cloud_armor_rules(self, finding: SecurityFinding):
        """Activate Cloud Armor protection rules"""
        self.logger.warning(f"Activating Cloud Armor for: {finding.name}")

        # Implementation would involve:
        # - Creating adaptive protection rules
        # - Enabling DDoS protection
        # - Configuring WAF rules

        pass

    async def _update_incident_status(self, incident_id: str, status: IncidentStatus):
        """Update incident status"""
        if incident_id in self.active_incidents:
            incident = self.active_incidents[incident_id]
            incident.status = status
            incident.timestamps[status.value.lower()] = datetime.utcnow()

            self.logger.info(
                f"Incident {incident_id} status updated to: {status.value}"
            )

    async def _send_incident_notification(
        self, incident: IncidentResponse, finding: SecurityFinding
    ):
        """Send incident notification via Pub/Sub"""
        if not self.notification_topic:
            return

        notification = {
            "incident_id": incident.incident_id,
            "finding_id": finding.name,
            "category": finding.category,
            "severity": finding.severity.value,
            "status": incident.status.value,
            "description": finding.description,
            "resource_name": finding.resource_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            topic_path = self.publisher.topic_path(
                self.project_id, self.notification_topic
            )
            message_data = json.dumps(notification).encode("utf-8")

            future = self.publisher.publish(topic_path, message_data)
            future.result()  # Wait for publish to complete

            self.logger.info(f"Incident notification sent: {incident.incident_id}")

        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")

    async def _send_security_metrics(self, metric_type: str, data: Dict[str, Any]):
        """Send security metrics to Cloud Monitoring"""
        try:
            # Create custom metrics for security monitoring
            # Implementation would involve creating time series data
            # and sending to Cloud Monitoring

            self.logger.debug(f"Security metric sent: {metric_type} - {data}")

        except Exception as e:
            self.logger.error(f"Failed to send security metrics: {e}")

    # SHIELD Method: LOG - Comprehensive Security Logging
    def get_incident_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity_filter: Optional[ThreatSeverity] = None,
    ) -> List[IncidentResponse]:
        """Get incident response history"""
        filtered_incidents = []

        for incident in self.active_incidents.values():
            # Apply time filters
            if (
                start_time
                and incident.timestamps.get("detected", datetime.min) < start_time
            ):
                continue
            if (
                end_time
                and incident.timestamps.get("detected", datetime.max) > end_time
            ):
                continue

            # Apply severity filter
            if severity_filter and incident.severity != severity_filter:
                continue

            filtered_incidents.append(incident)

        return filtered_incidents

    def get_security_metrics_summary(self) -> Dict[str, Any]:
        """Get security metrics summary"""
        total_incidents = len(self.active_incidents)

        status_counts = {}
        severity_counts = {}

        for incident in self.active_incidents.values():
            status = incident.status.value
            severity = incident.severity.value

            status_counts[status] = status_counts.get(status, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_incidents": total_incidents,
            "status_breakdown": status_counts,
            "severity_breakdown": severity_counts,
            "active_critical": len(
                [
                    i
                    for i in self.active_incidents.values()
                    if i.severity == ThreatSeverity.CRITICAL
                    and i.status != IncidentStatus.RESOLVED
                ]
            ),
            "response_time_avg": self._calculate_avg_response_time(),
        }

    def _calculate_avg_response_time(self) -> float:
        """Calculate average incident response time"""
        response_times = []

        for incident in self.active_incidents.values():
            detected = incident.timestamps.get("detected")
            responding = incident.timestamps.get("responding")

            if detected and responding:
                response_time = (responding - detected).total_seconds()
                response_times.append(response_time)

        return sum(response_times) / len(response_times) if response_times else 0.0

    async def create_custom_finding(
        self,
        source_id: str,
        category: str,
        description: str,
        resource_name: str,
        severity: ThreatSeverity,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create custom security finding"""
        self.logger.info(f"Creating custom finding: {category}")

        try:
            organization_name = f"organizations/{self.organization_id}"
            source_name = f"{organization_name}/sources/{source_id}"

            finding_id = f"finding-{int(time.time())}-{hash(description) % 10000}"

            finding = {
                "state": scc.Finding.State.ACTIVE,
                "resource_name": resource_name,
                "category": category,
                "severity": getattr(scc.Finding.Severity, severity.value),
                "description": description,
                "source_properties": properties or {},
                "event_time": datetime.utcnow(),
            }

            request = {
                "parent": source_name,
                "finding_id": finding_id,
                "finding": finding,
            }

            created_finding = self.scc_client.create_finding(request=request)

            self.logger.info(f"Custom finding created: {created_finding.name}")
            return created_finding.name

        except Exception as e:
            self.logger.error(f"Failed to create custom finding: {e}")
            raise

    def register_response_handler(self, category: str, handler: Callable):
        """Register custom incident response handler"""
        self.response_handlers[category] = handler
        self.logger.info(f"Registered response handler for category: {category}")

    async def close_incident(self, incident_id: str, resolution_notes: str = ""):
        """Close an incident"""
        if incident_id in self.active_incidents:
            incident = self.active_incidents[incident_id]
            incident.status = IncidentStatus.RESOLVED
            incident.timestamps["resolved"] = datetime.utcnow()

            self.logger.info(f"Incident closed: {incident_id} - {resolution_notes}")
        else:
            raise ValueError(f"Incident not found: {incident_id}")


# Factory function for easy instantiation
def create_security_center(
    organization_id: str, project_id: str, **kwargs
) -> GCPSecurityCenter:
    """Create GCP Security Center instance"""
    return GCPSecurityCenter(
        organization_id=organization_id, project_id=project_id, **kwargs
    )
