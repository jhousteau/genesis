"""
Security Automation Orchestrator - SHIELD Methodology Implementation
Comprehensive GCP-native security automation platform integrating all security components
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .chronicle_threat_hunting import ChroniclethreatHunting
from .cloud_armor_automation import AttackPattern, CloudArmorAutomation
from .gcp_security_center import GCPSecurityCenter, ThreatSeverity
from .incident_response_automation import IncidentResponseAutomation
from .jit_iam_automation import JITIAMAutomation


class SecurityAutomationLevel(Enum):
    """Security automation levels"""

    MONITORING = "MONITORING"  # Monitor and alert only
    REACTIVE = "REACTIVE"  # React to detected threats
    PROACTIVE = "PROACTIVE"  # Proactive threat hunting and prevention
    AUTONOMOUS = "AUTONOMOUS"  # Fully autonomous security operations


class SecurityEventType(Enum):
    """Security event types"""

    THREAT_DETECTED = "THREAT_DETECTED"
    INCIDENT_TRIGGERED = "INCIDENT_TRIGGERED"
    RESPONSE_EXECUTED = "RESPONSE_EXECUTED"
    COMPLIANCE_VIOLATION = "COMPLIANCE_VIOLATION"
    ACCESS_REQUESTED = "ACCESS_REQUESTED"
    VULNERABILITY_FOUND = "VULNERABILITY_FOUND"


@dataclass
class SecurityMetrics:
    """Comprehensive security metrics"""

    timestamp: datetime
    threats_detected: int = 0
    threats_blocked: int = 0
    incidents_responded: int = 0
    access_requests_processed: int = 0
    compliance_score: float = 0.0
    mean_time_to_detection: float = 0.0
    mean_time_to_response: float = 0.0
    false_positive_rate: float = 0.0
    security_coverage: float = 0.0
    automation_effectiveness: float = 0.0


@dataclass
class SecurityEvent:
    """Security event representation"""

    event_id: str
    event_type: SecurityEventType
    severity: ThreatSeverity
    timestamp: datetime
    source_component: str
    details: Dict[str, Any] = field(default_factory=dict)
    affected_resources: List[str] = field(default_factory=list)
    response_actions: List[str] = field(default_factory=list)
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class SecurityAutomationOrchestrator:
    """
    Comprehensive Security Automation Orchestrator

    SHIELD Methodology Implementation:
    S - Scan: Continuous threat detection across all security components
    H - Harden: Automated security control deployment and policy enforcement
    I - Isolate: Coordinated resource isolation and network segmentation
    E - Encrypt: End-to-end encryption and credential management
    L - Log: Unified security logging and audit trail management
    D - Defend: Comprehensive automated threat response and recovery
    """

    def __init__(
        self,
        project_id: str,
        organization_id: str,
        automation_level: SecurityAutomationLevel = SecurityAutomationLevel.REACTIVE,
        chronicle_customer_id: Optional[str] = None,
        enable_all_components: bool = True,
    ):
        self.project_id = project_id
        self.organization_id = organization_id
        self.automation_level = automation_level
        self.chronicle_customer_id = chronicle_customer_id
        self.enable_all_components = enable_all_components

        self.logger = self._setup_logging()

        # Initialize security components
        self.security_center: Optional[GCPSecurityCenter] = None
        self.cloud_armor: Optional[CloudArmorAutomation] = None
        self.incident_response: Optional[IncidentResponseAutomation] = None
        self.jit_iam: Optional[JITIAMAutomation] = None
        self.threat_hunting: Optional[ChroniclethreatHunting] = None

        # Initialize components based on configuration
        self._initialize_security_components()

        # Security event tracking
        self.security_events: Dict[str, SecurityEvent] = {}
        self.security_metrics: Dict[datetime, SecurityMetrics] = {}

        # Event handlers registry
        self.event_handlers: Dict[SecurityEventType, List[Callable]] = {
            event_type: [] for event_type in SecurityEventType
        }
        self._register_default_event_handlers()

        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.metrics_task: Optional[asyncio.Task] = None

        # Start orchestration
        self._start_orchestration()

        self.logger.info(
            f"Security Automation Orchestrator initialized - Level: {automation_level.value}"
        )

    def _setup_logging(self) -> logging.Logger:
        """Setup orchestrator logging"""
        logger = logging.getLogger(f"genesis.security.orchestrator.{self.project_id}")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [SECURITY_ORCHESTRATOR] %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def _initialize_security_components(self):
        """Initialize all security automation components"""
        try:
            if self.enable_all_components:
                # Security Command Center
                self.security_center = GCPSecurityCenter(
                    organization_id=self.organization_id,
                    project_id=self.project_id,
                    enable_auto_response=(
                        self.automation_level != SecurityAutomationLevel.MONITORING
                    ),
                )

                # Cloud Armor
                self.cloud_armor = CloudArmorAutomation(
                    project_id=self.project_id,
                    enable_adaptive_protection=True,
                    enable_auto_scaling=(
                        self.automation_level
                        in [
                            SecurityAutomationLevel.PROACTIVE,
                            SecurityAutomationLevel.AUTONOMOUS,
                        ]
                    ),
                )

                # Incident Response
                self.incident_response = IncidentResponseAutomation(
                    project_id=self.project_id,
                    organization_id=self.organization_id,
                    enable_auto_rollback=(
                        self.automation_level == SecurityAutomationLevel.AUTONOMOUS
                    ),
                )

                # Just-in-Time IAM
                self.jit_iam = JITIAMAutomation(
                    project_id=self.project_id,
                    organization_id=self.organization_id,
                    enable_emergency_access=True,
                    auto_cleanup_expired=True,
                )

                # Chronicle Threat Hunting (if customer ID provided)
                if self.chronicle_customer_id:
                    self.threat_hunting = ChroniclethreatHunting(
                        customer_id=self.chronicle_customer_id,
                        project_id=self.project_id,
                        enable_real_time_hunting=(
                            self.automation_level
                            in [
                                SecurityAutomationLevel.PROACTIVE,
                                SecurityAutomationLevel.AUTONOMOUS,
                            ]
                        ),
                    )

                self.logger.info("All security components initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize security components: {e}")
            raise

    def _register_default_event_handlers(self):
        """Register default event handlers"""
        # Threat detection handlers
        self.event_handlers[SecurityEventType.THREAT_DETECTED].extend(
            [
                self._handle_threat_detection,
                self._escalate_high_severity_threats,
            ]
        )

        # Incident response handlers
        self.event_handlers[SecurityEventType.INCIDENT_TRIGGERED].extend(
            [
                self._handle_incident_escalation,
                self._coordinate_response_actions,
            ]
        )

        # Access request handlers
        self.event_handlers[SecurityEventType.ACCESS_REQUESTED].extend(
            [
                self._handle_access_request_event,
            ]
        )

        # Compliance handlers
        self.event_handlers[SecurityEventType.COMPLIANCE_VIOLATION].extend(
            [
                self._handle_compliance_violation,
            ]
        )

    def _start_orchestration(self):
        """Start orchestration background tasks"""
        if self.automation_level != SecurityAutomationLevel.MONITORING:
            # Start continuous monitoring
            self.monitoring_task = asyncio.create_task(
                self._continuous_monitoring_loop()
            )

        # Start metrics collection
        self.metrics_task = asyncio.create_task(self._metrics_collection_loop())

        self.logger.info("Security orchestration started")

    # SHIELD Method: SCAN - Comprehensive Threat Detection
    async def execute_comprehensive_scan(
        self,
        scan_scope: Optional[List[str]] = None,
        time_window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Execute comprehensive security scan across all components

        Args:
            scan_scope: Optional list of resources to focus on
            time_window_hours: Time window for historical analysis

        Returns:
            Comprehensive scan results
        """
        self.logger.info("Executing comprehensive security scan")

        scan_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "scan_scope": scan_scope or ["all"],
            "time_window_hours": time_window_hours,
            "component_results": {},
            "consolidated_threats": [],
            "risk_assessment": {},
            "recommended_actions": [],
        }

        try:
            # Security Command Center scan
            if self.security_center:
                scc_findings = await self.security_center.scan_security_findings(
                    limit=1000
                )
                scan_results["component_results"]["security_center"] = {
                    "findings_count": len(scc_findings),
                    "critical_findings": len(
                        [
                            f
                            for f in scc_findings
                            if f.severity == ThreatSeverity.CRITICAL
                        ]
                    ),
                    "findings": scc_findings[:10],  # Top 10 findings
                }

            # Cloud Armor traffic analysis
            if self.cloud_armor:
                traffic_analysis = await self.cloud_armor.scan_traffic_patterns(
                    time_window_hours=time_window_hours
                )
                scan_results["component_results"]["cloud_armor"] = traffic_analysis

            # Chronicle threat hunting
            if self.threat_hunting:
                # Execute behavioral hunts
                hunt_results = []
                for query_id in list(self.threat_hunting.hunting_queries.keys())[
                    :3
                ]:  # Top 3 queries
                    try:
                        result = await self.threat_hunting.execute_behavioral_hunt(
                            query_id, time_window_hours
                        )
                        hunt_results.append(result)
                    except Exception as e:
                        self.logger.warning(f"Hunt query {query_id} failed: {e}")

                scan_results["component_results"]["threat_hunting"] = {
                    "hunts_executed": len(hunt_results),
                    "threats_detected": len(
                        [r for r in hunt_results if r.matched_events]
                    ),
                    "high_confidence_threats": len(
                        [r for r in hunt_results if r.confidence > 0.7]
                    ),
                }

            # JIT IAM access analysis
            if self.jit_iam:
                access_analysis = await self.jit_iam.analyze_access_patterns(
                    time_window_hours=time_window_hours
                )
                scan_results["component_results"]["jit_iam"] = access_analysis

            # Consolidate threats from all sources
            scan_results["consolidated_threats"] = await self._consolidate_scan_threats(
                scan_results["component_results"]
            )

            # Perform risk assessment
            scan_results["risk_assessment"] = self._assess_consolidated_risk(
                scan_results["consolidated_threats"]
            )

            # Generate recommended actions
            scan_results["recommended_actions"] = self._generate_scan_recommendations(
                scan_results
            )

            self.logger.info(
                f"Comprehensive scan completed: {len(scan_results['consolidated_threats'])} threats found"
            )

            return scan_results

        except Exception as e:
            self.logger.error(f"Comprehensive scan failed: {e}")
            raise

    async def _consolidate_scan_threats(
        self, component_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Consolidate threats from all security components"""
        consolidated_threats = []

        # Process Security Command Center findings
        if "security_center" in component_results:
            scc_data = component_results["security_center"]
            for finding in scc_data.get("findings", []):
                consolidated_threats.append(
                    {
                        "source": "Security Command Center",
                        "threat_type": finding.category,
                        "severity": finding.severity.value,
                        "description": finding.description,
                        "resource": finding.resource_name,
                        "timestamp": (
                            finding.create_time.isoformat()
                            if finding.create_time
                            else None
                        ),
                    }
                )

        # Process Cloud Armor threats
        if "cloud_armor" in component_results:
            armor_data = component_results["cloud_armor"]
            for anomaly in armor_data.get("anomalies", []):
                consolidated_threats.append(
                    {
                        "source": "Cloud Armor",
                        "threat_type": anomaly["type"],
                        "severity": anomaly.get("severity", "MEDIUM"),
                        "description": f"Traffic anomaly: {anomaly['type']}",
                        "resource": "network",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

        # Process threat hunting results
        if "threat_hunting" in component_results and self.threat_hunting:
            for hunt_result in self.threat_hunting.hunt_results.values():
                if hunt_result.matched_events:
                    consolidated_threats.append(
                        {
                            "source": "Chronicle Threat Hunting",
                            "threat_type": hunt_result.query_name,
                            "severity": hunt_result.severity.value,
                            "description": f"Behavioral pattern detected: {len(hunt_result.matched_events)} events",
                            "resource": ",".join(list(hunt_result.affected_assets)[:3]),
                            "timestamp": hunt_result.detection_time.isoformat(),
                        }
                    )

        return consolidated_threats

    def _assess_consolidated_risk(
        self, threats: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess overall risk from consolidated threats"""
        if not threats:
            return {"overall_risk": "LOW", "risk_score": 0.0, "risk_factors": []}

        # Count threats by severity
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for threat in threats:
            severity = threat.get("severity", "MEDIUM")
            if severity in severity_counts:
                severity_counts[severity] += 1

        # Calculate risk score
        risk_score = (
            severity_counts["CRITICAL"] * 1.0
            + severity_counts["HIGH"] * 0.7
            + severity_counts["MEDIUM"] * 0.4
            + severity_counts["LOW"] * 0.1
        ) / max(len(threats), 1)

        # Determine overall risk level
        if risk_score > 0.8 or severity_counts["CRITICAL"] > 0:
            overall_risk = "CRITICAL"
        elif risk_score > 0.6 or severity_counts["HIGH"] > 2:
            overall_risk = "HIGH"
        elif risk_score > 0.3 or severity_counts["MEDIUM"] > 5:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"

        # Identify risk factors
        risk_factors = []
        if severity_counts["CRITICAL"] > 0:
            risk_factors.append(
                f"{severity_counts['CRITICAL']} critical threats detected"
            )
        if severity_counts["HIGH"] > 3:
            risk_factors.append(
                f"High volume of high-severity threats ({severity_counts['HIGH']})"
            )

        return {
            "overall_risk": overall_risk,
            "risk_score": risk_score,
            "severity_breakdown": severity_counts,
            "risk_factors": risk_factors,
        }

    def _generate_scan_recommendations(self, scan_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on scan results"""
        recommendations = []

        risk_assessment = scan_results["risk_assessment"]
        overall_risk = risk_assessment.get("overall_risk", "LOW")

        # Risk-based recommendations
        if overall_risk == "CRITICAL":
            recommendations.extend(
                [
                    "IMMEDIATE ACTION REQUIRED: Critical threats detected",
                    "Activate incident response team",
                    "Consider emergency access restrictions",
                ]
            )
        elif overall_risk == "HIGH":
            recommendations.extend(
                [
                    "Elevated threat level - increase monitoring",
                    "Review and validate security controls",
                    "Consider additional access restrictions",
                ]
            )

        # Component-specific recommendations
        for component, results in scan_results["component_results"].items():
            if component == "cloud_armor" and results.get("anomalies"):
                recommendations.append(
                    "Review Cloud Armor rules and consider adaptive protection"
                )
            elif (
                component == "security_center"
                and results.get("critical_findings", 0) > 0
            ):
                recommendations.append(
                    "Address critical Security Command Center findings immediately"
                )
            elif component == "jit_iam" and results.get("anomalies"):
                recommendations.append(
                    "Review JIT access patterns for unusual activity"
                )

        # General recommendations
        recommendations.extend(
            [
                "Update threat intelligence feeds",
                "Review security monitoring coverage",
                "Validate backup and recovery procedures",
            ]
        )

        return recommendations

    # SHIELD Method: DEFEND - Coordinated Threat Response
    async def execute_coordinated_response(
        self,
        threat_event: SecurityEvent,
        override_automation_level: Optional[SecurityAutomationLevel] = None,
    ) -> Dict[str, Any]:
        """
        Execute coordinated threat response across all components

        Args:
            threat_event: Security event requiring response
            override_automation_level: Override default automation level

        Returns:
            Response execution results
        """
        automation_level = override_automation_level or self.automation_level

        self.logger.warning(
            f"Executing coordinated response for event: {threat_event.event_id}"
        )

        response_results = {
            "event_id": threat_event.event_id,
            "response_timestamp": datetime.utcnow().isoformat(),
            "automation_level": automation_level.value,
            "component_responses": {},
            "overall_success": True,
            "actions_taken": [],
            "failed_actions": [],
        }

        try:
            # Determine response strategy based on threat severity and automation level
            response_strategy = self._determine_response_strategy(
                threat_event, automation_level
            )

            # Execute Security Command Center response
            if self.security_center and "security_center" in response_strategy:
                try:
                    # Create custom finding for orchestrated response
                    finding_name = await self.security_center.create_custom_finding(
                        source_id="orchestrator",
                        category="COORDINATED_RESPONSE",
                        description=f"Orchestrated response for event: {threat_event.event_id}",
                        resource_name=(
                            threat_event.affected_resources[0]
                            if threat_event.affected_resources
                            else "unknown"
                        ),
                        severity=threat_event.severity,
                        properties=threat_event.details,
                    )

                    response_results["component_responses"]["security_center"] = {
                        "success": True,
                        "finding_created": finding_name,
                    }
                    response_results["actions_taken"].append(
                        "Created Security Command Center finding"
                    )

                except Exception as e:
                    response_results["component_responses"]["security_center"] = {
                        "success": False,
                        "error": str(e),
                    }
                    response_results["failed_actions"].append(
                        f"Security Command Center response failed: {e}"
                    )

            # Execute Cloud Armor response
            if self.cloud_armor and "cloud_armor" in response_strategy:
                try:
                    # Determine attack pattern and respond
                    attack_pattern = self._map_threat_to_attack_pattern(threat_event)
                    if attack_pattern:
                        attack_response = (
                            await self.cloud_armor.respond_to_application_attack(
                                attack_pattern=attack_pattern,
                                attack_signature=threat_event.details.get(
                                    "signature", "unknown"
                                ),
                                source_ips=threat_event.details.get("source_ips", []),
                            )
                        )

                        response_results["component_responses"][
                            "cloud_armor"
                        ] = attack_response
                        response_results["actions_taken"].extend(
                            attack_response.get("actions_taken", [])
                        )

                except Exception as e:
                    response_results["component_responses"]["cloud_armor"] = {
                        "success": False,
                        "error": str(e),
                    }
                    response_results["failed_actions"].append(
                        f"Cloud Armor response failed: {e}"
                    )

            # Execute incident response automation
            if self.incident_response and "incident_response" in response_strategy:
                try:
                    execution_id = (
                        await self.incident_response.evaluate_incident_for_response(
                            incident_id=threat_event.event_id,
                            category=threat_event.details.get("category", "UNKNOWN"),
                            severity=threat_event.severity,
                            resource_name=(
                                threat_event.affected_resources[0]
                                if threat_event.affected_resources
                                else "unknown"
                            ),
                            additional_context=threat_event.details,
                        )
                    )

                    if execution_id:
                        response_results["component_responses"]["incident_response"] = {
                            "success": True,
                            "execution_id": execution_id,
                        }
                        response_results["actions_taken"].append(
                            f"Initiated incident response: {execution_id}"
                        )
                    else:
                        response_results["component_responses"]["incident_response"] = {
                            "success": False,
                            "reason": "No matching workflow found",
                        }

                except Exception as e:
                    response_results["component_responses"]["incident_response"] = {
                        "success": False,
                        "error": str(e),
                    }
                    response_results["failed_actions"].append(
                        f"Incident response failed: {e}"
                    )

            # Execute JIT IAM restrictions if needed
            if self.jit_iam and "jit_iam" in response_strategy:
                try:
                    # For high-severity threats, revoke suspicious access
                    if threat_event.severity in [
                        ThreatSeverity.HIGH,
                        ThreatSeverity.CRITICAL,
                    ]:
                        # Identify potentially compromised accounts
                        affected_users = threat_event.details.get("affected_users", [])
                        if affected_users:
                            revoked_count = 0
                            for user in affected_users:
                                revoked = await self.jit_iam.revoke_access(
                                    requester=user
                                )
                                if revoked:
                                    revoked_count += 1

                            response_results["component_responses"]["jit_iam"] = {
                                "success": True,
                                "access_revoked": revoked_count,
                                "affected_users": affected_users,
                            }
                            response_results["actions_taken"].append(
                                f"Revoked JIT access for {revoked_count} users"
                            )

                except Exception as e:
                    response_results["component_responses"]["jit_iam"] = {
                        "success": False,
                        "error": str(e),
                    }
                    response_results["failed_actions"].append(
                        f"JIT IAM response failed: {e}"
                    )

            # Execute threat hunting investigation
            if self.threat_hunting and "threat_hunting" in response_strategy:
                try:
                    # Extract IOCs from threat event and hunt for them
                    iocs = threat_event.details.get("iocs", [])
                    if iocs:
                        hunt_results = await self.threat_hunting.scan_iocs(
                            ioc_values=iocs,
                            time_window_hours=24,
                        )

                        response_results["component_responses"]["threat_hunting"] = {
                            "success": True,
                            "hunts_executed": len(hunt_results),
                            "additional_threats": len(
                                [r for r in hunt_results if r.matched_events]
                            ),
                        }
                        response_results["actions_taken"].append(
                            f"Executed threat hunting for {len(iocs)} IOCs"
                        )

                except Exception as e:
                    response_results["component_responses"]["threat_hunting"] = {
                        "success": False,
                        "error": str(e),
                    }
                    response_results["failed_actions"].append(
                        f"Threat hunting response failed: {e}"
                    )

            # Check overall success
            response_results["overall_success"] = (
                len(response_results["failed_actions"]) == 0
            )

            # Update threat event
            threat_event.response_actions = response_results["actions_taken"]
            if response_results["overall_success"]:
                threat_event.resolved = True
                threat_event.resolution_time = datetime.utcnow()

            self.logger.info(
                f"Coordinated response completed for {threat_event.event_id}: "
                f"success={response_results['overall_success']}, "
                f"actions={len(response_results['actions_taken'])}"
            )

            return response_results

        except Exception as e:
            self.logger.error(
                f"Coordinated response failed for {threat_event.event_id}: {e}"
            )
            response_results["overall_success"] = False
            response_results["failed_actions"].append(
                f"Orchestration failure: {str(e)}"
            )
            return response_results

    def _determine_response_strategy(
        self,
        threat_event: SecurityEvent,
        automation_level: SecurityAutomationLevel,
    ) -> List[str]:
        """Determine which components should participate in response"""
        strategy = []

        # Always include Security Command Center for tracking
        strategy.append("security_center")

        # Automation level-based inclusion
        if automation_level in [
            SecurityAutomationLevel.REACTIVE,
            SecurityAutomationLevel.PROACTIVE,
            SecurityAutomationLevel.AUTONOMOUS,
        ]:
            # Include incident response for medium+ severity
            if threat_event.severity in [
                ThreatSeverity.MEDIUM,
                ThreatSeverity.HIGH,
                ThreatSeverity.CRITICAL,
            ]:
                strategy.append("incident_response")

            # Include Cloud Armor for network-related threats
            if "network" in threat_event.details.get("category", "").lower():
                strategy.append("cloud_armor")

            # Include JIT IAM for access-related threats
            if (
                "access" in threat_event.details.get("category", "").lower()
                or "authentication" in threat_event.details.get("category", "").lower()
            ):
                strategy.append("jit_iam")

        # Proactive and autonomous levels include threat hunting
        if automation_level in [
            SecurityAutomationLevel.PROACTIVE,
            SecurityAutomationLevel.AUTONOMOUS,
        ]:
            strategy.append("threat_hunting")

        return strategy

    def _map_threat_to_attack_pattern(
        self, threat_event: SecurityEvent
    ) -> Optional[AttackPattern]:
        """Map threat event to Cloud Armor attack pattern"""
        category = threat_event.details.get("category", "").upper()

        mapping = {
            "SQL_INJECTION": AttackPattern.SQL_INJECTION,
            "XSS": AttackPattern.XSS,
            "CROSS_SITE_SCRIPTING": AttackPattern.XSS,
            "LFI": AttackPattern.LFI,
            "RFI": AttackPattern.RFI,
            "RCE": AttackPattern.RCE,
            "DDOS": AttackPattern.PROTOCOL_ATTACK,
            "SCANNER": AttackPattern.SCANNER_DETECTION,
        }

        return mapping.get(category)

    # Background Monitoring and Event Processing
    async def _continuous_monitoring_loop(self):
        """Continuous security monitoring loop"""
        self.logger.info("Starting continuous security monitoring")

        while True:
            try:
                # Check for new findings from Security Command Center
                if self.security_center:
                    findings = await self.security_center.scan_security_findings(
                        limit=100
                    )

                    for finding in findings:
                        if finding.severity in [
                            ThreatSeverity.HIGH,
                            ThreatSeverity.CRITICAL,
                        ]:
                            await self._process_security_event(
                                SecurityEvent(
                                    event_id=f"scc-{int(time.time())}-{hash(finding.name) % 10000}",
                                    event_type=SecurityEventType.THREAT_DETECTED,
                                    severity=finding.severity,
                                    timestamp=datetime.utcnow(),
                                    source_component="Security Command Center",
                                    details={
                                        "category": finding.category,
                                        "description": finding.description,
                                        "source_properties": finding.source_properties,
                                    },
                                    affected_resources=[finding.resource_name],
                                )
                            )

                # Check for high-severity threat hunting results
                if self.threat_hunting:
                    for hunt_result in self.threat_hunting.hunt_results.values():
                        if (
                            hunt_result.severity
                            in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL]
                            and hunt_result.matched_events
                        ):
                            await self._process_security_event(
                                SecurityEvent(
                                    event_id=f"hunt-{hunt_result.hunt_id}",
                                    event_type=SecurityEventType.THREAT_DETECTED,
                                    severity=hunt_result.severity,
                                    timestamp=hunt_result.detection_time,
                                    source_component="Chronicle Threat Hunting",
                                    details={
                                        "category": "BEHAVIORAL_DETECTION",
                                        "query_name": hunt_result.query_name,
                                        "confidence": hunt_result.confidence,
                                        "iocs": [
                                            ind.ioc_value
                                            for ind in hunt_result.threat_indicators
                                        ],
                                    },
                                    affected_resources=list(
                                        hunt_result.affected_assets
                                    ),
                                )
                            )

                # Sleep for 5 minutes before next monitoring cycle
                await asyncio.sleep(300)

            except Exception as e:
                self.logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(60)

    async def _process_security_event(self, event: SecurityEvent):
        """Process security event through registered handlers"""
        self.logger.info(
            f"Processing security event: {event.event_id} - {event.event_type.value}"
        )

        # Store event
        self.security_events[event.event_id] = event

        # Execute registered handlers
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                self.logger.error(f"Event handler failed for {event.event_id}: {e}")

    # Event Handlers
    async def _handle_threat_detection(self, event: SecurityEvent):
        """Handle threat detection event"""
        if self.automation_level in [
            SecurityAutomationLevel.REACTIVE,
            SecurityAutomationLevel.PROACTIVE,
            SecurityAutomationLevel.AUTONOMOUS,
        ]:
            # Trigger coordinated response for high-severity threats
            if event.severity in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL]:
                await self.execute_coordinated_response(event)

    async def _escalate_high_severity_threats(self, event: SecurityEvent):
        """Escalate high-severity threats"""
        if event.severity == ThreatSeverity.CRITICAL:
            self.logger.critical(
                f"CRITICAL THREAT DETECTED: {event.event_id} from {event.source_component}"
            )
            # In production, this would trigger additional alerting

    async def _handle_incident_escalation(self, event: SecurityEvent):
        """Handle incident escalation"""
        self.logger.warning(f"Incident escalated: {event.event_id}")

    async def _coordinate_response_actions(self, event: SecurityEvent):
        """Coordinate response actions across components"""
        # This is handled by execute_coordinated_response
        pass

    async def _handle_access_request_event(self, event: SecurityEvent):
        """Handle access request events"""
        if event.severity in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL]:
            # For high-severity access events, increase scrutiny
            self.logger.warning(f"High-risk access event: {event.event_id}")

    async def _handle_compliance_violation(self, event: SecurityEvent):
        """Handle compliance violations"""
        self.logger.warning(f"Compliance violation detected: {event.event_id}")

    # Metrics Collection
    async def _metrics_collection_loop(self):
        """Collect and store security metrics"""
        while True:
            try:
                await asyncio.sleep(3600)  # Collect metrics every hour

                metrics = SecurityMetrics(timestamp=datetime.utcnow())

                # Calculate metrics from recent events
                recent_events = [
                    event
                    for event in self.security_events.values()
                    if event.timestamp >= datetime.utcnow() - timedelta(hours=1)
                ]

                metrics.threats_detected = len(
                    [
                        e
                        for e in recent_events
                        if e.event_type == SecurityEventType.THREAT_DETECTED
                    ]
                )

                metrics.threats_blocked = len([e for e in recent_events if e.resolved])

                metrics.incidents_responded = len(
                    [e for e in recent_events if e.response_actions]
                )

                # Calculate response times
                resolved_events = [
                    e for e in recent_events if e.resolved and e.resolution_time
                ]
                if resolved_events:
                    response_times = [
                        (e.resolution_time - e.timestamp).total_seconds()
                        for e in resolved_events
                    ]
                    metrics.mean_time_to_response = sum(response_times) / len(
                        response_times
                    )

                # Store metrics
                self.security_metrics[metrics.timestamp] = metrics

                # Keep only last 24 hours of metrics
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                self.security_metrics = {
                    timestamp: metric
                    for timestamp, metric in self.security_metrics.items()
                    if timestamp >= cutoff_time
                }

            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")

    # Public API Methods
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status"""
        recent_events = [
            event
            for event in self.security_events.values()
            if event.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ]

        return {
            "automation_level": self.automation_level.value,
            "component_status": {
                "security_center": self.security_center is not None,
                "cloud_armor": self.cloud_armor is not None,
                "incident_response": self.incident_response is not None,
                "jit_iam": self.jit_iam is not None,
                "threat_hunting": self.threat_hunting is not None,
            },
            "recent_activity": {
                "total_events": len(recent_events),
                "threats_detected": len(
                    [
                        e
                        for e in recent_events
                        if e.event_type == SecurityEventType.THREAT_DETECTED
                    ]
                ),
                "incidents_triggered": len(
                    [
                        e
                        for e in recent_events
                        if e.event_type == SecurityEventType.INCIDENT_TRIGGERED
                    ]
                ),
                "resolved_events": len([e for e in recent_events if e.resolved]),
            },
            "severity_breakdown": {
                "critical": len(
                    [e for e in recent_events if e.severity == ThreatSeverity.CRITICAL]
                ),
                "high": len(
                    [e for e in recent_events if e.severity == ThreatSeverity.HIGH]
                ),
                "medium": len(
                    [e for e in recent_events if e.severity == ThreatSeverity.MEDIUM]
                ),
                "low": len(
                    [e for e in recent_events if e.severity == ThreatSeverity.LOW]
                ),
            },
        }

    def get_security_metrics_summary(self) -> Dict[str, Any]:
        """Get security metrics summary"""
        if not self.security_metrics:
            return {"message": "No metrics available yet"}

        latest_metrics = max(self.security_metrics.values(), key=lambda m: m.timestamp)

        return {
            "latest_timestamp": latest_metrics.timestamp.isoformat(),
            "threats_detected_last_hour": latest_metrics.threats_detected,
            "threats_blocked_last_hour": latest_metrics.threats_blocked,
            "incidents_responded_last_hour": latest_metrics.incidents_responded,
            "mean_time_to_response_seconds": latest_metrics.mean_time_to_response,
            "automation_effectiveness": latest_metrics.automation_effectiveness,
        }

    def register_event_handler(self, event_type: SecurityEventType, handler: Callable):
        """Register custom event handler"""
        self.event_handlers[event_type].append(handler)
        self.logger.info(f"Registered event handler for: {event_type.value}")

    async def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        self.logger.info("Shutting down Security Automation Orchestrator")

        # Cancel background tasks
        if self.monitoring_task:
            self.monitoring_task.cancel()

        if self.metrics_task:
            self.metrics_task.cancel()

        # Shutdown threat hunting if enabled
        if self.threat_hunting and self.threat_hunting.real_time_task:
            self.threat_hunting.real_time_task.cancel()


# Factory function for easy instantiation
def create_security_automation_orchestrator(
    project_id: str, organization_id: str, **kwargs
) -> SecurityAutomationOrchestrator:
    """Create Security Automation Orchestrator instance"""
    return SecurityAutomationOrchestrator(
        project_id=project_id, organization_id=organization_id, **kwargs
    )
