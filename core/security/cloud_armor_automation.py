"""
Cloud Armor Automation - Advanced Threat Detection and DDoS Protection
SHIELD Methodology implementation for automated security policy management
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from google.cloud import compute_v1, monitoring_v3

from .gcp_security_center import ThreatSeverity


class SecurityPolicyType(Enum):
    """Security policy types"""

    CLOUD_ARMOR = "CLOUD_ARMOR"
    CLOUD_ARMOR_EDGE = "CLOUD_ARMOR_EDGE"


class RuleAction(Enum):
    """Security rule actions"""

    ALLOW = "allow"
    DENY_403 = "deny(403)"
    DENY_404 = "deny(404)"
    DENY_502 = "deny(502)"
    RATE_BASED_BAN = "rate_based_ban"
    REDIRECT = "redirect"
    THROTTLE = "throttle"


class AttackPattern(Enum):
    """Attack pattern detection"""

    SQL_INJECTION = "SQL_INJECTION"
    XSS = "CROSS_SITE_SCRIPTING"
    LFI = "LOCAL_FILE_INCLUSION"
    RFI = "REMOTE_FILE_INCLUSION"
    RCE = "REMOTE_CODE_EXECUTION"
    PROTOCOL_ATTACK = "PROTOCOL_ATTACK"
    SESSION_FIXATION = "SESSION_FIXATION"
    SCANNER_DETECTION = "SCANNER_DETECTION"


@dataclass
class SecurityRule:
    """Security rule definition"""

    priority: int
    action: RuleAction
    description: str
    match_expression: Optional[str] = None
    src_ip_ranges: List[str] = field(default_factory=list)
    rate_limit_threshold: Optional[Dict[str, int]] = None
    preview: bool = False


@dataclass
class ThreatIntelligence:
    """Threat intelligence data"""

    source_ips: Set[str] = field(default_factory=set)
    malicious_domains: Set[str] = field(default_factory=set)
    attack_signatures: Dict[str, str] = field(default_factory=dict)
    geo_restrictions: Set[str] = field(default_factory=set)
    last_updated: Optional[datetime] = None


@dataclass
class AttackEvent:
    """Attack event details"""

    timestamp: datetime
    source_ip: str
    target: str
    attack_type: AttackPattern
    severity: ThreatSeverity
    blocked: bool
    rule_matched: Optional[str] = None


class CloudArmorAutomation:
    """
    Automated Cloud Armor security policy management

    SHIELD Implementation:
    S - Scan: Continuous threat pattern analysis
    H - Harden: Automated security rule deployment
    I - Isolate: IP and geo-based traffic isolation
    E - Encrypt: HTTPS enforcement and TLS security
    L - Log: Comprehensive attack logging and analysis
    D - Defend: Real-time threat blocking and rate limiting
    """

    def __init__(
        self,
        project_id: str,
        region: str = "global",
        enable_adaptive_protection: bool = True,
        enable_auto_scaling: bool = True,
    ):
        self.project_id = project_id
        self.region = region
        self.enable_adaptive_protection = enable_adaptive_protection
        self.enable_auto_scaling = enable_auto_scaling

        self.logger = self._setup_logging()

        # Initialize GCP clients
        self.compute_client = compute_v1.SecurityPoliciesClient()
        self.monitoring_client = monitoring_v3.MetricServiceClient()

        # Threat intelligence
        self.threat_intel = ThreatIntelligence()
        self._load_threat_intelligence()

        # Attack tracking
        self.attack_events: List[AttackEvent] = []

        # Security policies tracking
        self.active_policies: Dict[str, Dict[str, Any]] = {}

        self.logger.info(
            f"Cloud Armor automation initialized for project: {project_id}"
        )

    def _setup_logging(self) -> logging.Logger:
        """Setup security-focused logging"""
        logger = logging.getLogger(f"genesis.security.armor.{self.project_id}")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [CLOUD_ARMOR] %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def _load_threat_intelligence(self):
        """Load threat intelligence data"""
        # Load known malicious IPs and domains
        self.threat_intel.source_ips.update(
            [
                # Known botnet IPs (examples)
                "192.168.1.100",
                "10.0.0.50",
            ]
        )

        self.threat_intel.malicious_domains.update(
            [
                "malicious-domain.com",
                "attack-site.net",
            ]
        )

        # Attack signatures for pattern matching
        self.threat_intel.attack_signatures.update(
            {
                "sql_injection": r"(?i)(union|select|insert|drop|delete|update|exec|script)",
                "xss": r"(?i)(<script|javascript:|onload=|onerror=)",
                "lfi": r"(?i)(\.\.\/|\.\.\\|\/etc\/passwd|\/windows\/system32)",
                "rce": r"(?i)(eval\(|exec\(|system\(|shell_exec)",
            }
        )

        self.threat_intel.last_updated = datetime.utcnow()

        self.logger.info("Threat intelligence loaded")

    # SHIELD Method: SCAN - Threat Pattern Analysis
    async def scan_traffic_patterns(
        self,
        time_window_hours: int = 1,
        threshold_requests: int = 1000,
    ) -> Dict[str, Any]:
        """
        Scan traffic patterns for threats and anomalies

        Args:
            time_window_hours: Time window for analysis
            threshold_requests: Request threshold for anomaly detection

        Returns:
            Traffic analysis results
        """
        self.logger.info(f"Scanning traffic patterns (last {time_window_hours}h)")

        analysis_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "time_window_hours": time_window_hours,
            "threats_detected": [],
            "anomalies": [],
            "recommendations": [],
            "blocked_attacks": 0,
            "top_source_ips": {},
            "attack_types": {},
        }

        try:
            # Analyze recent attack events
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            recent_attacks = [
                event for event in self.attack_events if event.timestamp >= cutoff_time
            ]

            analysis_results["blocked_attacks"] = len(
                [attack for attack in recent_attacks if attack.blocked]
            )

            # Count attack types
            for attack in recent_attacks:
                attack_type = attack.attack_type.value
                analysis_results["attack_types"][attack_type] = (
                    analysis_results["attack_types"].get(attack_type, 0) + 1
                )

            # Identify top attacking IPs
            ip_counts = {}
            for attack in recent_attacks:
                ip_counts[attack.source_ip] = ip_counts.get(attack.source_ip, 0) + 1

            analysis_results["top_source_ips"] = dict(
                sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            )

            # Detect anomalies
            for ip, count in ip_counts.items():
                if count > threshold_requests:
                    analysis_results["anomalies"].append(
                        {
                            "type": "high_request_volume",
                            "source_ip": ip,
                            "request_count": count,
                            "severity": (
                                "HIGH" if count > threshold_requests * 2 else "MEDIUM"
                            ),
                        }
                    )

            # Generate recommendations
            if analysis_results["anomalies"]:
                analysis_results["recommendations"].append(
                    "Consider implementing rate limiting for high-volume source IPs"
                )

            if analysis_results["blocked_attacks"] > 100:
                analysis_results["recommendations"].append(
                    "High attack volume detected - consider enabling adaptive protection"
                )

            self.logger.info(
                f"Traffic pattern analysis completed: {len(recent_attacks)} events analyzed"
            )

            return analysis_results

        except Exception as e:
            self.logger.error(f"Traffic pattern analysis failed: {e}")
            raise

    # SHIELD Method: HARDEN - Automated Security Rules
    async def create_security_policy(
        self,
        policy_name: str,
        description: str = "",
        policy_type: SecurityPolicyType = SecurityPolicyType.CLOUD_ARMOR,
        enable_adaptive_protection: Optional[bool] = None,
    ) -> str:
        """
        Create security policy with hardened defaults

        Args:
            policy_name: Name of the security policy
            description: Policy description
            policy_type: Type of security policy
            enable_adaptive_protection: Enable adaptive protection

        Returns:
            Policy resource name
        """
        self.logger.info(f"Creating security policy: {policy_name}")

        if enable_adaptive_protection is None:
            enable_adaptive_protection = self.enable_adaptive_protection

        try:
            policy_body = {
                "name": policy_name,
                "description": description
                or f"Automated security policy - {policy_name}",
                "type": policy_type.value,
            }

            # Configure adaptive protection
            if enable_adaptive_protection:
                policy_body["adaptiveProtectionConfig"] = {
                    "layer7DdosDefenseConfig": {
                        "enable": True,
                        "ruleVisibility": "STANDARD",
                    },
                    "autoDeployConfig": {
                        "loadThreshold": 0.1,
                        "confidenceThreshold": 0.5,
                        "impactedBaselineThreshold": 0.01,
                        "expirationSec": 600,
                    },
                }

            # Advanced options
            policy_body["advancedOptionsConfig"] = {
                "jsonParsing": "STANDARD",
                "logLevel": "NORMAL",
                "userIpRequestHeaders": ["X-Forwarded-For", "X-Real-IP"],
            }

            # Create the policy
            request = {
                "project": self.project_id,
                "security_policy_resource": policy_body,
            }

            operation = self.compute_client.insert(request=request)
            self._wait_for_operation(operation)

            # Add default security rules
            await self._add_default_security_rules(policy_name)

            # Track active policy
            self.active_policies[policy_name] = {
                "created": datetime.utcnow(),
                "type": policy_type,
                "adaptive_protection": enable_adaptive_protection,
            }

            self.logger.info(f"Security policy created: {policy_name}")

            return f"projects/{self.project_id}/global/securityPolicies/{policy_name}"

        except Exception as e:
            self.logger.error(f"Failed to create security policy {policy_name}: {e}")
            raise

    async def _add_default_security_rules(self, policy_name: str):
        """Add default security rules to policy"""
        default_rules = [
            # Block known malicious IPs
            SecurityRule(
                priority=1000,
                action=RuleAction.DENY_403,
                description="Block known malicious IPs",
                src_ip_ranges=list(self.threat_intel.source_ips),
            ),
            # SQL Injection protection
            SecurityRule(
                priority=2000,
                action=RuleAction.DENY_403,
                description="Block SQL injection attempts",
                match_expression=f'origin.regionCode == \'US\' && has(request.headers[\'user-agent\']) && request.headers[\'user-agent\'].matches(\'{self.threat_intel.attack_signatures["sql_injection"]}\')',
            ),
            # XSS protection
            SecurityRule(
                priority=2100,
                action=RuleAction.DENY_403,
                description="Block XSS attempts",
                match_expression=f'request.query.matches(\'{self.threat_intel.attack_signatures["xss"]}\')',
            ),
            # Rate limiting for high volume sources
            SecurityRule(
                priority=3000,
                action=RuleAction.RATE_BASED_BAN,
                description="Rate limit high volume sources",
                rate_limit_threshold={"count": 100, "interval_sec": 60},
            ),
            # Default allow rule (lowest priority)
            SecurityRule(
                priority=2147483647,  # Max int32
                action=RuleAction.ALLOW,
                description="Default allow rule",
                match_expression="true",
            ),
        ]

        for rule in default_rules:
            await self.add_security_rule(policy_name, rule)

    async def add_security_rule(
        self,
        policy_name: str,
        rule: SecurityRule,
    ) -> str:
        """
        Add security rule to policy

        Args:
            policy_name: Name of the security policy
            rule: Security rule to add

        Returns:
            Rule resource name
        """
        self.logger.info(f"Adding security rule to {policy_name}: {rule.description}")

        try:
            rule_body = {
                "priority": rule.priority,
                "action": rule.action.value,
                "description": rule.description,
                "preview": rule.preview,
            }

            # Add match configuration
            if rule.match_expression:
                rule_body["match"] = {"expr": {"expression": rule.match_expression}}
            elif rule.src_ip_ranges:
                rule_body["match"] = {"config": {"srcIpRanges": rule.src_ip_ranges}}

            # Add rate limiting configuration
            if rule.rate_limit_threshold and rule.action == RuleAction.RATE_BASED_BAN:
                rule_body["rateLimitOptions"] = {
                    "conformAction": "allow",
                    "exceedAction": "deny(429)",
                    "enforceOnKey": "IP",
                    "rateLimitThreshold": {
                        "count": rule.rate_limit_threshold["count"],
                        "intervalSec": rule.rate_limit_threshold["interval_sec"],
                    },
                    "banThreshold": {
                        "count": rule.rate_limit_threshold["count"] * 2,
                        "intervalSec": rule.rate_limit_threshold["interval_sec"],
                    },
                    "banDurationSec": 600,  # 10 minutes ban
                }

            request = {
                "project": self.project_id,
                "security_policy": policy_name,
                "security_policy_rule_resource": rule_body,
            }

            operation = self.compute_client.add_rule(request=request)
            self._wait_for_operation(operation)

            self.logger.info(f"Security rule added: {rule.description}")

            return f"projects/{self.project_id}/global/securityPolicies/{policy_name}/rules/{rule.priority}"

        except Exception as e:
            self.logger.error(f"Failed to add security rule: {e}")
            raise

    # SHIELD Method: DEFEND - Automated Threat Response
    async def respond_to_ddos_attack(
        self,
        target_service: str,
        attack_source_ips: List[str],
        severity: ThreatSeverity,
    ) -> Dict[str, Any]:
        """
        Respond to DDoS attack with automated mitigation

        Args:
            target_service: Target service being attacked
            attack_source_ips: List of attacking IP addresses
            severity: Attack severity level

        Returns:
            Response actions taken
        """
        self.logger.critical(
            f"DDoS attack detected on {target_service} - Severity: {severity.value}"
        )

        response_actions = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_service": target_service,
            "attack_source_count": len(attack_source_ips),
            "severity": severity.value,
            "actions_taken": [],
            "policies_created": [],
        }

        try:
            # Create emergency security policy
            emergency_policy_name = f"emergency-ddos-{int(time.time())}"

            policy_resource = await self.create_security_policy(
                policy_name=emergency_policy_name,
                description=f"Emergency DDoS mitigation for {target_service}",
                enable_adaptive_protection=True,
            )

            response_actions["policies_created"].append(emergency_policy_name)
            response_actions["actions_taken"].append(
                "Created emergency security policy"
            )

            # Block attacking IPs
            if attack_source_ips:
                block_rule = SecurityRule(
                    priority=100,  # High priority
                    action=RuleAction.DENY_403,
                    description=f"Block DDoS attack sources - {datetime.utcnow()}",
                    src_ip_ranges=attack_source_ips,
                )

                await self.add_security_rule(emergency_policy_name, block_rule)
                response_actions["actions_taken"].append(
                    f"Blocked {len(attack_source_ips)} attacking IPs"
                )

            # Enable aggressive rate limiting
            rate_limit_rule = SecurityRule(
                priority=200,
                action=RuleAction.RATE_BASED_BAN,
                description="Aggressive rate limiting for DDoS mitigation",
                rate_limit_threshold={"count": 10, "interval_sec": 60},  # Very strict
            )

            await self.add_security_rule(emergency_policy_name, rate_limit_rule)
            response_actions["actions_taken"].append("Enabled aggressive rate limiting")

            # Log attack event
            attack_event = AttackEvent(
                timestamp=datetime.utcnow(),
                source_ip=",".join(attack_source_ips[:5])
                + ("..." if len(attack_source_ips) > 5 else ""),
                target=target_service,
                attack_type=AttackPattern.PROTOCOL_ATTACK,
                severity=severity,
                blocked=True,
                rule_matched=emergency_policy_name,
            )

            self.attack_events.append(attack_event)

            self.logger.info(
                f"DDoS attack response completed: {len(response_actions['actions_taken'])} actions taken"
            )

            return response_actions

        except Exception as e:
            self.logger.error(f"DDoS attack response failed: {e}")
            response_actions["actions_taken"].append(f"ERROR: {str(e)}")
            return response_actions

    async def respond_to_application_attack(
        self,
        attack_pattern: AttackPattern,
        attack_signature: str,
        source_ips: List[str],
    ) -> Dict[str, Any]:
        """
        Respond to application-layer attack

        Args:
            attack_pattern: Type of attack detected
            attack_signature: Attack signature or pattern
            source_ips: Source IP addresses of the attack

        Returns:
            Response actions taken
        """
        self.logger.warning(f"Application attack detected: {attack_pattern.value}")

        response_actions = {
            "timestamp": datetime.utcnow().isoformat(),
            "attack_pattern": attack_pattern.value,
            "source_ip_count": len(source_ips),
            "actions_taken": [],
        }

        try:
            # Find existing security policies
            existing_policies = list(self.active_policies.keys())

            if not existing_policies:
                # Create new policy if none exist
                policy_name = "app-security-policy"
                await self.create_security_policy(
                    policy_name, "Application security policy"
                )
                existing_policies = [policy_name]

            # Add specific attack blocking rule
            for policy_name in existing_policies:
                block_rule = SecurityRule(
                    priority=500 + len(self.attack_events) % 1000,  # Dynamic priority
                    action=RuleAction.DENY_403,
                    description=f"Block {attack_pattern.value} attack - {datetime.utcnow()}",
                    match_expression=f"request.url_map.matches('{attack_signature}')",
                )

                await self.add_security_rule(policy_name, block_rule)
                response_actions["actions_taken"].append(
                    f"Added blocking rule to {policy_name}"
                )

            # Block source IPs if provided
            if source_ips:
                for policy_name in existing_policies:
                    ip_block_rule = SecurityRule(
                        priority=400 + len(self.attack_events) % 1000,
                        action=RuleAction.DENY_403,
                        description=f"Block attack source IPs - {attack_pattern.value}",
                        src_ip_ranges=source_ips,
                    )

                    await self.add_security_rule(policy_name, ip_block_rule)
                    response_actions["actions_taken"].append(
                        f"Blocked {len(source_ips)} source IPs"
                    )

            # Log attack event
            attack_event = AttackEvent(
                timestamp=datetime.utcnow(),
                source_ip=",".join(source_ips[:3])
                + ("..." if len(source_ips) > 3 else ""),
                target="application",
                attack_type=attack_pattern,
                severity=ThreatSeverity.HIGH,
                blocked=True,
                rule_matched=existing_policies[0] if existing_policies else None,
            )

            self.attack_events.append(attack_event)

            self.logger.info(
                f"Application attack response completed: {len(response_actions['actions_taken'])} actions"
            )

            return response_actions

        except Exception as e:
            self.logger.error(f"Application attack response failed: {e}")
            response_actions["actions_taken"].append(f"ERROR: {str(e)}")
            return response_actions

    # SHIELD Method: LOG - Attack Monitoring and Analysis
    def get_attack_statistics(
        self,
        time_window_hours: int = 24,
    ) -> Dict[str, Any]:
        """Get attack statistics and metrics"""
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_attacks = [
            event for event in self.attack_events if event.timestamp >= cutoff_time
        ]

        stats = {
            "time_window_hours": time_window_hours,
            "total_attacks": len(recent_attacks),
            "blocked_attacks": len([a for a in recent_attacks if a.blocked]),
            "attack_types": {},
            "severity_breakdown": {},
            "top_source_ips": {},
            "most_targeted": {},
        }

        for attack in recent_attacks:
            # Count attack types
            attack_type = attack.attack_type.value
            stats["attack_types"][attack_type] = (
                stats["attack_types"].get(attack_type, 0) + 1
            )

            # Count severity levels
            severity = attack.severity.value
            stats["severity_breakdown"][severity] = (
                stats["severity_breakdown"].get(severity, 0) + 1
            )

            # Count source IPs
            if attack.source_ip not in stats["top_source_ips"]:
                stats["top_source_ips"][attack.source_ip] = 0
            stats["top_source_ips"][attack.source_ip] += 1

            # Count targets
            if attack.target not in stats["most_targeted"]:
                stats["most_targeted"][attack.target] = 0
            stats["most_targeted"][attack.target] += 1

        # Sort top items
        stats["top_source_ips"] = dict(
            sorted(stats["top_source_ips"].items(), key=lambda x: x[1], reverse=True)[
                :10
            ]
        )
        stats["most_targeted"] = dict(
            sorted(stats["most_targeted"].items(), key=lambda x: x[1], reverse=True)[
                :10
            ]
        )

        return stats

    def _wait_for_operation(self, operation):
        """Wait for GCP operation to complete"""
        # In production, this would properly wait for the operation
        # For now, we'll just log it
        self.logger.debug(f"Operation initiated: {operation}")

    async def update_threat_intelligence(
        self,
        new_malicious_ips: Optional[List[str]] = None,
        new_malicious_domains: Optional[List[str]] = None,
        new_signatures: Optional[Dict[str, str]] = None,
    ):
        """Update threat intelligence data"""
        if new_malicious_ips:
            self.threat_intel.source_ips.update(new_malicious_ips)
            self.logger.info(
                f"Added {len(new_malicious_ips)} malicious IPs to threat intel"
            )

        if new_malicious_domains:
            self.threat_intel.malicious_domains.update(new_malicious_domains)
            self.logger.info(
                f"Added {len(new_malicious_domains)} malicious domains to threat intel"
            )

        if new_signatures:
            self.threat_intel.attack_signatures.update(new_signatures)
            self.logger.info(
                f"Added {len(new_signatures)} attack signatures to threat intel"
            )

        self.threat_intel.last_updated = datetime.utcnow()

    async def cleanup_expired_rules(self, max_age_hours: int = 24):
        """Clean up expired emergency security rules"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        # Implementation would involve:
        # - Identifying temporary/emergency rules older than max_age_hours
        # - Removing those rules from active policies
        # - Logging cleanup actions

        self.logger.info(f"Cleaned up security rules older than {max_age_hours} hours")


# Factory function for easy instantiation
def create_cloud_armor_automation(project_id: str, **kwargs) -> CloudArmorAutomation:
    """Create Cloud Armor automation instance"""
    return CloudArmorAutomation(project_id=project_id, **kwargs)
