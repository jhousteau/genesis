"""
Genesis Threat Intelligence System - Advanced Threat Detection and Intelligence Integration
SHIELD Methodology: Scan & Defend components for automated threat response

Provides comprehensive threat intelligence, behavioral analysis, and automated response capabilities.
"""

import hashlib
import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import requests
from google.cloud import monitoring_v3, pubsub_v1
from google.cloud.exceptions import GoogleCloudError


class ThreatSeverity(Enum):
    """Threat severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatCategory(Enum):
    """Categories of security threats"""

    MALWARE = "malware"
    PHISHING = "phishing"
    BRUTE_FORCE = "brute_force"
    DATA_EXFILTRATION = "data_exfiltration"
    INSIDER_THREAT = "insider_threat"
    APT = "advanced_persistent_threat"
    DENIAL_OF_SERVICE = "denial_of_service"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    LATERAL_MOVEMENT = "lateral_movement"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"


class ResponseAction(Enum):
    """Automated response actions"""

    ALERT_ONLY = "alert_only"
    RATE_LIMIT = "rate_limit"
    BLOCK_ACCESS = "block_access"
    ROTATE_SECRET = "rotate_secret"
    QUARANTINE_USER = "quarantine_user"
    EMERGENCY_LOCKDOWN = "emergency_lockdown"
    REVOKE_TOKENS = "revoke_tokens"
    ISOLATE_SERVICE = "isolate_service"


@dataclass
class ThreatIndicator:
    """Individual threat indicator"""

    indicator_type: str  # ip, domain, hash, pattern, etc.
    value: str
    severity: ThreatSeverity
    category: ThreatCategory
    source: str
    confidence_score: float  # 0.0 to 1.0
    first_seen: datetime
    last_seen: datetime
    description: str = ""
    references: List[str] = field(default_factory=list)
    ttl: Optional[datetime] = None


@dataclass
class ThreatEvent:
    """Detected threat event"""

    event_id: str
    threat_category: ThreatCategory
    severity: ThreatSeverity
    timestamp: datetime
    source_ip: Optional[str] = None
    user_identity: Optional[str] = None
    service_identity: Optional[str] = None
    secret_name: Optional[str] = None
    indicators: List[ThreatIndicator] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    automated_response: Optional[ResponseAction] = None
    response_taken: bool = False
    resolved: bool = False


@dataclass
class BehaviorBaseline:
    """Behavioral baseline for anomaly detection"""

    entity_id: str  # user, service, or secret identifier
    entity_type: str  # "user", "service", "secret"
    typical_access_times: List[int] = field(default_factory=list)  # Hours of day
    typical_access_frequency: float = 0.0  # Average accesses per hour
    typical_secret_access_patterns: Set[str] = field(default_factory=set)
    typical_source_ips: Set[str] = field(default_factory=set)
    last_updated: Optional[datetime] = None


class ThreatIntelligenceSystem:
    """
    Advanced threat intelligence and automated response system

    Implements comprehensive threat detection:
    - Real-time threat intelligence feed integration
    - Behavioral anomaly detection with ML-based analysis
    - Automated threat response and containment
    - Threat hunting and correlation capabilities
    """

    def __init__(
        self,
        project_id: str,
        secret_manager,
        threat_feeds: Optional[List[str]] = None,
        enable_automated_response: bool = True,
        max_response_level: ResponseAction = ResponseAction.ROTATE_SECRET,
        threat_callback: Optional[Callable] = None,
    ):
        self.project_id = project_id
        self.secret_manager = secret_manager
        self.enable_automated_response = enable_automated_response
        self.max_response_level = max_response_level
        self.threat_callback = threat_callback

        self.logger = logging.getLogger("genesis.secrets.threat_intel")

        # Threat intelligence storage
        self._threat_indicators: Dict[str, ThreatIndicator] = {}
        self._threat_events: deque = deque(maxlen=10000)
        self._behavioral_baselines: Dict[str, BehaviorBaseline] = {}

        # Threat feeds configuration
        self.threat_feeds = threat_feeds or [
            "https://reputation.alienvault.com/reputation.data",
            "https://rules.emergingthreats.net/blockrules/compromised-ips.txt",
        ]

        # Response tracking
        self._active_responses: Dict[str, Dict[str, Any]] = {}
        self._response_history: deque = deque(maxlen=1000)

        # ML/Statistical models for anomaly detection
        self._anomaly_thresholds = {
            "access_frequency_multiplier": 5.0,  # 5x normal frequency triggers alert
            "unusual_time_threshold": 0.1,  # Bottom 10% of typical times
            "new_ip_threshold": 0.8,  # Confidence threshold for new IPs
            "secret_access_anomaly": 0.7,  # Threshold for unusual secret access
        }

        # Thread safety
        self._lock = threading.RLock()

        # Initialize GCP clients
        self._init_gcp_clients()

        # Start background processes
        self._start_threat_feed_updates()
        self._start_behavioral_learning()
        self._start_threat_hunting()

        self.logger.info("ThreatIntelligenceSystem initialized")

    def _init_gcp_clients(self):
        """Initialize Google Cloud clients"""
        try:
            self.monitoring_client = monitoring_v3.MetricServiceClient()
            self.pubsub_client = pubsub_v1.PublisherClient()

            # Create threat intelligence topic if it doesn't exist
            topic_path = self.pubsub_client.topic_path(
                self.project_id, "threat-intelligence"
            )
            try:
                self.pubsub_client.create_topic(request={"name": topic_path})
            except GoogleCloudError:
                pass  # Topic already exists

        except Exception as e:
            self.logger.warning(f"Failed to initialize some GCP clients: {e}")

    def process_audit_event(self, audit_entry: Dict[str, Any]) -> Optional[ThreatEvent]:
        """
        Process an audit log entry for threat detection

        Args:
            audit_entry: Audit log entry from secret monitoring

        Returns:
            ThreatEvent if threat detected, None otherwise
        """
        with self._lock:
            threats_detected = []

            # Check against threat intelligence indicators
            ip_threat = self._check_ip_indicators(audit_entry.get("source_ip"))
            if ip_threat:
                threats_detected.append(ip_threat)

            # Perform behavioral analysis
            behavioral_threats = self._analyze_behavioral_anomalies(audit_entry)
            threats_detected.extend(behavioral_threats)

            # Check for attack patterns
            pattern_threats = self._detect_attack_patterns(audit_entry)
            threats_detected.extend(pattern_threats)

            if threats_detected:
                # Create consolidated threat event
                threat_event = self._create_threat_event(audit_entry, threats_detected)

                # Determine and execute automated response
                if self.enable_automated_response:
                    self._execute_automated_response(threat_event)

                # Store and notify
                self._threat_events.append(threat_event)

                if self.threat_callback:
                    try:
                        self.threat_callback(threat_event)
                    except Exception as e:
                        self.logger.error(f"Threat callback failed: {e}")

                return threat_event

            # Update behavioral baselines with legitimate activity
            self._update_behavioral_baselines(audit_entry)

            return None

    def _check_ip_indicators(
        self, source_ip: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Check IP address against threat intelligence indicators"""
        if not source_ip:
            return None

        for indicator in self._threat_indicators.values():
            if (
                indicator.indicator_type == "ip"
                and indicator.value == source_ip
                and (not indicator.ttl or indicator.ttl > datetime.utcnow())
            ):
                return {
                    "type": "malicious_ip",
                    "severity": indicator.severity,
                    "category": indicator.category,
                    "confidence": indicator.confidence_score,
                    "indicator": indicator,
                }

        return None

    def _analyze_behavioral_anomalies(
        self, audit_entry: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze audit entry for behavioral anomalies"""
        anomalies = []

        user_id = audit_entry.get("user_identity")
        service_id = audit_entry.get("service_identity")
        secret_name = audit_entry.get("secret_name")
        source_ip = audit_entry.get("source_ip")
        timestamp = datetime.fromisoformat(
            audit_entry["timestamp"].replace("Z", "+00:00")
        )

        # Check user behavioral anomalies
        if user_id:
            user_baseline = self._behavioral_baselines.get(f"user:{user_id}")
            if user_baseline:
                user_anomalies = self._check_user_anomalies(
                    user_baseline, audit_entry, timestamp
                )
                anomalies.extend(user_anomalies)

        # Check service behavioral anomalies
        if service_id:
            service_baseline = self._behavioral_baselines.get(f"service:{service_id}")
            if service_baseline:
                service_anomalies = self._check_service_anomalies(
                    service_baseline, audit_entry, timestamp
                )
                anomalies.extend(service_anomalies)

        # Check secret access anomalies
        if secret_name:
            secret_baseline = self._behavioral_baselines.get(f"secret:{secret_name}")
            if secret_baseline:
                secret_anomalies = self._check_secret_anomalies(
                    secret_baseline, audit_entry, timestamp
                )
                anomalies.extend(secret_anomalies)

        return anomalies

    def _check_user_anomalies(
        self,
        baseline: BehaviorBaseline,
        audit_entry: Dict[str, Any],
        timestamp: datetime,
    ) -> List[Dict[str, Any]]:
        """Check for user behavioral anomalies"""
        anomalies = []

        current_hour = timestamp.hour
        source_ip = audit_entry.get("source_ip")
        secret_name = audit_entry.get("secret_name")

        # Unusual access time
        if (
            baseline.typical_access_times
            and current_hour not in baseline.typical_access_times
        ):
            time_probability = len(
                [h for h in baseline.typical_access_times if abs(h - current_hour) <= 2]
            ) / len(baseline.typical_access_times)
            if time_probability < self._anomaly_thresholds["unusual_time_threshold"]:
                anomalies.append(
                    {
                        "type": "unusual_access_time",
                        "severity": ThreatSeverity.MEDIUM,
                        "category": ThreatCategory.ANOMALOUS_BEHAVIOR,
                        "confidence": 1.0 - time_probability,
                        "details": {
                            "current_hour": current_hour,
                            "typical_hours": baseline.typical_access_times,
                        },
                    }
                )

        # New source IP
        if (
            source_ip
            and baseline.typical_source_ips
            and source_ip not in baseline.typical_source_ips
        ):
            anomalies.append(
                {
                    "type": "new_source_ip",
                    "severity": ThreatSeverity.MEDIUM,
                    "category": ThreatCategory.ANOMALOUS_BEHAVIOR,
                    "confidence": self._anomaly_thresholds["new_ip_threshold"],
                    "details": {
                        "source_ip": source_ip,
                        "known_ips": list(baseline.typical_source_ips)[
                            :5
                        ],  # First 5 for privacy
                    },
                }
            )

        # Unusual secret access
        if (
            secret_name
            and baseline.typical_secret_access_patterns
            and secret_name not in baseline.typical_secret_access_patterns
        ):
            anomalies.append(
                {
                    "type": "unusual_secret_access",
                    "severity": ThreatSeverity.HIGH,
                    "category": ThreatCategory.PRIVILEGE_ESCALATION,
                    "confidence": self._anomaly_thresholds["secret_access_anomaly"],
                    "details": {
                        "secret_name": secret_name,
                        "typical_secrets": len(baseline.typical_secret_access_patterns),
                    },
                }
            )

        return anomalies

    def _check_service_anomalies(
        self,
        baseline: BehaviorBaseline,
        audit_entry: Dict[str, Any],
        timestamp: datetime,
    ) -> List[Dict[str, Any]]:
        """Check for service behavioral anomalies"""
        # Similar to user anomalies but focused on service-specific patterns
        return self._check_user_anomalies(baseline, audit_entry, timestamp)

    def _check_secret_anomalies(
        self,
        baseline: BehaviorBaseline,
        audit_entry: Dict[str, Any],
        timestamp: datetime,
    ) -> List[Dict[str, Any]]:
        """Check for secret-specific anomalies"""
        anomalies = []

        # High frequency access detection
        recent_window = timedelta(hours=1)
        current_access_count = sum(
            1
            for event in self._threat_events
            if (
                event.secret_name == audit_entry.get("secret_name")
                and event.timestamp > timestamp - recent_window
            )
        )

        if (
            baseline.typical_access_frequency > 0
            and current_access_count
            > baseline.typical_access_frequency
            * self._anomaly_thresholds["access_frequency_multiplier"]
        ):
            anomalies.append(
                {
                    "type": "excessive_secret_access",
                    "severity": ThreatSeverity.HIGH,
                    "category": ThreatCategory.DATA_EXFILTRATION,
                    "confidence": 0.9,
                    "details": {
                        "current_frequency": current_access_count,
                        "typical_frequency": baseline.typical_access_frequency,
                    },
                }
            )

        return anomalies

    def _detect_attack_patterns(
        self, audit_entry: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect known attack patterns"""
        patterns = []

        # Brute force detection (multiple failed attempts)
        if audit_entry.get("status") in ["failure", "error", "denied", "access_denied"]:
            user_key = audit_entry.get("user_identity") or audit_entry.get(
                "service_identity"
            )
            if user_key:
                recent_failures = sum(
                    1
                    for event in list(self._threat_events)[
                        -100:
                    ]  # Check last 100 events
                    if (
                        event.user_identity == user_key
                        or event.service_identity == user_key
                    )
                    and event.timestamp > datetime.utcnow() - timedelta(hours=1)
                )

                if recent_failures > 10:  # More than 10 failures in an hour
                    patterns.append(
                        {
                            "type": "brute_force_attempt",
                            "severity": ThreatSeverity.HIGH,
                            "category": ThreatCategory.BRUTE_FORCE,
                            "confidence": 0.9,
                            "details": {
                                "failure_count": recent_failures,
                                "user": user_key,
                            },
                        }
                    )

        # Data exfiltration pattern (rapid sequential access to multiple secrets)
        if (
            audit_entry.get("operation") == "get"
            and audit_entry.get("status") == "success"
        ):
            user_key = audit_entry.get("user_identity") or audit_entry.get(
                "service_identity"
            )
            if user_key:
                recent_accesses = [
                    event
                    for event in list(self._threat_events)[-50:]
                    if (
                        event.user_identity == user_key
                        or event.service_identity == user_key
                    )
                    and event.timestamp > datetime.utcnow() - timedelta(minutes=10)
                ]

                unique_secrets = len(
                    set(
                        event.secret_name
                        for event in recent_accesses
                        if event.secret_name
                    )
                )

                if (
                    unique_secrets > 5
                ):  # Access to more than 5 different secrets in 10 minutes
                    patterns.append(
                        {
                            "type": "potential_data_exfiltration",
                            "severity": ThreatSeverity.CRITICAL,
                            "category": ThreatCategory.DATA_EXFILTRATION,
                            "confidence": 0.8,
                            "details": {
                                "unique_secrets_accessed": unique_secrets,
                                "time_window": "10 minutes",
                            },
                        }
                    )

        return patterns

    def _create_threat_event(
        self, audit_entry: Dict[str, Any], detected_threats: List[Dict[str, Any]]
    ) -> ThreatEvent:
        """Create a consolidated threat event from detected threats"""

        # Determine overall severity (highest among all threats)
        max_severity = ThreatSeverity.LOW
        for threat in detected_threats:
            if threat["severity"].value > max_severity.value:
                max_severity = threat["severity"]

        # Determine primary category
        categories = [threat["category"] for threat in detected_threats]
        primary_category = max(set(categories), key=categories.count)

        # Calculate overall confidence score
        confidence_scores = [threat["confidence"] for threat in detected_threats]
        overall_confidence = sum(confidence_scores) / len(confidence_scores)

        # Generate event ID
        event_data = f"{audit_entry.get('timestamp')}-{audit_entry.get('user_identity')}-{audit_entry.get('secret_name')}"
        event_id = f"threat_{hashlib.md5(event_data.encode()).hexdigest()[:16]}"

        # Determine automated response
        automated_response = self._determine_automated_response(
            max_severity, primary_category
        )

        threat_event = ThreatEvent(
            event_id=event_id,
            threat_category=primary_category,
            severity=max_severity,
            timestamp=datetime.fromisoformat(
                audit_entry["timestamp"].replace("Z", "+00:00")
            ),
            source_ip=audit_entry.get("source_ip"),
            user_identity=audit_entry.get("user_identity"),
            service_identity=audit_entry.get("service_identity"),
            secret_name=audit_entry.get("secret_name"),
            evidence={
                "audit_entry": audit_entry,
                "detected_threats": detected_threats,
            },
            confidence_score=overall_confidence,
            automated_response=automated_response,
        )

        return threat_event

    def _determine_automated_response(
        self, severity: ThreatSeverity, category: ThreatCategory
    ) -> ResponseAction:
        """Determine appropriate automated response based on threat characteristics"""

        # Response matrix based on severity and category
        response_matrix = {
            ThreatSeverity.CRITICAL: {
                ThreatCategory.DATA_EXFILTRATION: ResponseAction.EMERGENCY_LOCKDOWN,
                ThreatCategory.APT: ResponseAction.ISOLATE_SERVICE,
                ThreatCategory.MALWARE: ResponseAction.QUARANTINE_USER,
                "default": ResponseAction.ROTATE_SECRET,
            },
            ThreatSeverity.HIGH: {
                ThreatCategory.BRUTE_FORCE: ResponseAction.BLOCK_ACCESS,
                ThreatCategory.PRIVILEGE_ESCALATION: ResponseAction.REVOKE_TOKENS,
                "default": ResponseAction.ROTATE_SECRET,
            },
            ThreatSeverity.MEDIUM: {
                ThreatCategory.ANOMALOUS_BEHAVIOR: ResponseAction.RATE_LIMIT,
                "default": ResponseAction.ALERT_ONLY,
            },
            ThreatSeverity.LOW: {
                "default": ResponseAction.ALERT_ONLY,
            },
        }

        severity_responses = response_matrix.get(severity, {})
        response = severity_responses.get(
            category, severity_responses.get("default", ResponseAction.ALERT_ONLY)
        )

        # Ensure we don't exceed maximum allowed response level
        if response.value > self.max_response_level.value:
            response = self.max_response_level

        return response

    def _execute_automated_response(self, threat_event: ThreatEvent):
        """Execute automated response to threat event"""
        if not threat_event.automated_response:
            return

        response_id = f"response_{threat_event.event_id}_{int(time.time())}"

        try:
            success = False

            if threat_event.automated_response == ResponseAction.ALERT_ONLY:
                success = self._send_alert(threat_event)

            elif threat_event.automated_response == ResponseAction.RATE_LIMIT:
                success = self._apply_rate_limiting(threat_event)

            elif threat_event.automated_response == ResponseAction.BLOCK_ACCESS:
                success = self._block_access(threat_event)

            elif threat_event.automated_response == ResponseAction.ROTATE_SECRET:
                success = self._rotate_secret(threat_event)

            elif threat_event.automated_response == ResponseAction.QUARANTINE_USER:
                success = self._quarantine_user(threat_event)

            elif threat_event.automated_response == ResponseAction.REVOKE_TOKENS:
                success = self._revoke_tokens(threat_event)

            elif threat_event.automated_response == ResponseAction.ISOLATE_SERVICE:
                success = self._isolate_service(threat_event)

            elif threat_event.automated_response == ResponseAction.EMERGENCY_LOCKDOWN:
                success = self._emergency_lockdown(threat_event)

            threat_event.response_taken = success

            # Record response
            response_record = {
                "response_id": response_id,
                "threat_event_id": threat_event.event_id,
                "response_action": threat_event.automated_response.value,
                "timestamp": datetime.utcnow().isoformat(),
                "success": success,
            }

            self._response_history.append(response_record)

            self.logger.info(
                f"Automated response executed: {threat_event.automated_response.value} "
                f"for threat {threat_event.event_id} - Success: {success}"
            )

        except Exception as e:
            self.logger.error(f"Failed to execute automated response: {e}")
            threat_event.response_taken = False

    def _send_alert(self, threat_event: ThreatEvent) -> bool:
        """Send alert notification"""
        try:
            # Publish to Pub/Sub topic
            topic_path = self.pubsub_client.topic_path(
                self.project_id, "threat-intelligence"
            )
            message_data = json.dumps(
                {
                    "event_id": threat_event.event_id,
                    "severity": threat_event.severity.value,
                    "category": threat_event.threat_category.value,
                    "timestamp": threat_event.timestamp.isoformat(),
                    "description": f"Security threat detected: {threat_event.threat_category.value}",
                    "evidence": threat_event.evidence,
                }
            ).encode()

            self.pubsub_client.publish(topic_path, message_data)
            return True

        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
            return False

    def _apply_rate_limiting(self, threat_event: ThreatEvent) -> bool:
        """Apply rate limiting to user/service"""
        # In a real implementation, this would integrate with API gateway or load balancer
        self.logger.info(
            f"Rate limiting applied to {threat_event.user_identity or threat_event.service_identity}"
        )
        return True

    def _block_access(self, threat_event: ThreatEvent) -> bool:
        """Block access for user/service/IP"""
        # In a real implementation, this would update firewall rules or IAM policies
        self.logger.info(
            f"Access blocked for {threat_event.source_ip or threat_event.user_identity}"
        )
        return True

    def _rotate_secret(self, threat_event: ThreatEvent) -> bool:
        """Rotate the affected secret"""
        try:
            if threat_event.secret_name and hasattr(
                self.secret_manager, "rotate_secret"
            ):
                self.secret_manager.rotate_secret(threat_event.secret_name)
                return True
        except Exception as e:
            self.logger.error(f"Failed to rotate secret: {e}")
        return False

    def _quarantine_user(self, threat_event: ThreatEvent) -> bool:
        """Quarantine user account"""
        # In a real implementation, this would disable user account or restrict permissions
        self.logger.info(f"User quarantined: {threat_event.user_identity}")
        return True

    def _revoke_tokens(self, threat_event: ThreatEvent) -> bool:
        """Revoke authentication tokens"""
        # In a real implementation, this would revoke OAuth tokens or API keys
        self.logger.info(
            f"Tokens revoked for {threat_event.user_identity or threat_event.service_identity}"
        )
        return True

    def _isolate_service(self, threat_event: ThreatEvent) -> bool:
        """Isolate service from network"""
        # In a real implementation, this would update network security groups
        self.logger.info(f"Service isolated: {threat_event.service_identity}")
        return True

    def _emergency_lockdown(self, threat_event: ThreatEvent) -> bool:
        """Execute emergency lockdown procedures"""
        # In a real implementation, this would trigger organization-wide security measures
        self.logger.critical(
            f"EMERGENCY LOCKDOWN TRIGGERED for threat {threat_event.event_id}"
        )
        return True

    def _update_behavioral_baselines(self, audit_entry: Dict[str, Any]):
        """Update behavioral baselines with legitimate activity"""
        user_id = audit_entry.get("user_identity")
        service_id = audit_entry.get("service_identity")
        secret_name = audit_entry.get("secret_name")
        source_ip = audit_entry.get("source_ip")
        timestamp = datetime.fromisoformat(
            audit_entry["timestamp"].replace("Z", "+00:00")
        )

        # Update user baseline
        if user_id:
            baseline_key = f"user:{user_id}"
            if baseline_key not in self._behavioral_baselines:
                self._behavioral_baselines[baseline_key] = BehaviorBaseline(
                    entity_id=user_id, entity_type="user"
                )

            baseline = self._behavioral_baselines[baseline_key]
            baseline.typical_access_times.append(timestamp.hour)
            if source_ip:
                baseline.typical_source_ips.add(source_ip)
            if secret_name:
                baseline.typical_secret_access_patterns.add(secret_name)
            baseline.last_updated = timestamp

        # Update service baseline
        if service_id:
            baseline_key = f"service:{service_id}"
            if baseline_key not in self._behavioral_baselines:
                self._behavioral_baselines[baseline_key] = BehaviorBaseline(
                    entity_id=service_id, entity_type="service"
                )

            baseline = self._behavioral_baselines[baseline_key]
            baseline.typical_access_times.append(timestamp.hour)
            if source_ip:
                baseline.typical_source_ips.add(source_ip)
            if secret_name:
                baseline.typical_secret_access_patterns.add(secret_name)
            baseline.last_updated = timestamp

        # Update secret baseline
        if secret_name:
            baseline_key = f"secret:{secret_name}"
            if baseline_key not in self._behavioral_baselines:
                self._behavioral_baselines[baseline_key] = BehaviorBaseline(
                    entity_id=secret_name, entity_type="secret"
                )

            # Calculate access frequency (simplified)
            baseline = self._behavioral_baselines[baseline_key]
            if baseline.last_updated:
                time_diff = (
                    timestamp - baseline.last_updated
                ).total_seconds() / 3600  # hours
                if time_diff > 0:
                    # Update moving average of access frequency
                    new_frequency = 1.0 / time_diff
                    baseline.typical_access_frequency = (
                        baseline.typical_access_frequency * 0.9 + new_frequency * 0.1
                    )
            baseline.last_updated = timestamp

    def update_threat_intelligence(self, indicators: List[Dict[str, Any]]):
        """Update threat intelligence indicators"""
        with self._lock:
            for indicator_data in indicators:
                indicator = ThreatIndicator(
                    indicator_type=indicator_data["type"],
                    value=indicator_data["value"],
                    severity=ThreatSeverity(indicator_data.get("severity", "medium")),
                    category=ThreatCategory(indicator_data.get("category", "malware")),
                    source=indicator_data.get("source", "manual"),
                    confidence_score=indicator_data.get("confidence", 0.8),
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    description=indicator_data.get("description", ""),
                    references=indicator_data.get("references", []),
                    ttl=datetime.utcnow()
                    + timedelta(days=indicator_data.get("ttl_days", 30)),
                )

                indicator_key = f"{indicator.indicator_type}:{indicator.value}"
                self._threat_indicators[indicator_key] = indicator

        self.logger.info(f"Updated {len(indicators)} threat intelligence indicators")

    def get_threat_events(
        self,
        severity: Optional[ThreatSeverity] = None,
        category: Optional[ThreatCategory] = None,
        resolved: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get threat events with filtering"""
        with self._lock:
            events = list(self._threat_events)

            # Apply filters
            filtered_events = []
            for event in events:
                if severity and event.severity != severity:
                    continue
                if category and event.threat_category != category:
                    continue
                if resolved is not None and event.resolved != resolved:
                    continue

                filtered_events.append(event)

            # Sort by timestamp (newest first)
            filtered_events.sort(key=lambda e: e.timestamp, reverse=True)

            # Limit results
            filtered_events = filtered_events[:limit]

            # Convert to dictionaries
            return [
                {
                    "event_id": event.event_id,
                    "threat_category": event.threat_category.value,
                    "severity": event.severity.value,
                    "timestamp": event.timestamp.isoformat(),
                    "source_ip": event.source_ip,
                    "user_identity": event.user_identity,
                    "service_identity": event.service_identity,
                    "secret_name": event.secret_name,
                    "confidence_score": event.confidence_score,
                    "automated_response": event.automated_response.value
                    if event.automated_response
                    else None,
                    "response_taken": event.response_taken,
                    "resolved": event.resolved,
                    "evidence": event.evidence,
                }
                for event in filtered_events
            ]

    def _start_threat_feed_updates(self):
        """Start background thread for threat feed updates"""

        def update_feeds():
            while True:
                try:
                    for feed_url in self.threat_feeds:
                        self._process_threat_feed(feed_url)

                    # Update every hour
                    time.sleep(3600)

                except Exception as e:
                    self.logger.error(f"Threat feed update error: {e}")
                    time.sleep(300)  # Retry in 5 minutes on error

        feed_thread = threading.Thread(target=update_feeds, daemon=True)
        feed_thread.start()
        self.logger.info("Threat feed update thread started")

    def _process_threat_feed(self, feed_url: str):
        """Process a single threat intelligence feed"""
        try:
            response = requests.get(feed_url, timeout=30)
            response.raise_for_status()

            # Simple IP list processing (would need more sophisticated parsing for other formats)
            indicators = []
            for line in response.text.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Simple IP indicator
                    indicators.append(
                        {
                            "type": "ip",
                            "value": line,
                            "severity": "medium",
                            "category": "malware",
                            "source": feed_url,
                            "confidence": 0.7,
                            "ttl_days": 7,
                        }
                    )

            if indicators:
                self.update_threat_intelligence(indicators)
                self.logger.info(
                    f"Processed {len(indicators)} indicators from {feed_url}"
                )

        except Exception as e:
            self.logger.warning(f"Failed to process threat feed {feed_url}: {e}")

    def _start_behavioral_learning(self):
        """Start background behavioral learning process"""

        def learn_behaviors():
            while True:
                try:
                    self._update_behavioral_models()
                    time.sleep(1800)  # Update every 30 minutes

                except Exception as e:
                    self.logger.error(f"Behavioral learning error: {e}")
                    time.sleep(300)

        learning_thread = threading.Thread(target=learn_behaviors, daemon=True)
        learning_thread.start()
        self.logger.info("Behavioral learning thread started")

    def _update_behavioral_models(self):
        """Update behavioral models and clean up old data"""
        with self._lock:
            # Clean up old baselines (older than 30 days without updates)
            cutoff = datetime.utcnow() - timedelta(days=30)
            old_baselines = [
                key
                for key, baseline in self._behavioral_baselines.items()
                if baseline.last_updated and baseline.last_updated < cutoff
            ]

            for key in old_baselines:
                del self._behavioral_baselines[key]

            if old_baselines:
                self.logger.info(
                    f"Cleaned up {len(old_baselines)} old behavioral baselines"
                )

    def _start_threat_hunting(self):
        """Start proactive threat hunting process"""

        def hunt_threats():
            while True:
                try:
                    self._proactive_threat_hunt()
                    time.sleep(3600)  # Hunt every hour

                except Exception as e:
                    self.logger.error(f"Threat hunting error: {e}")
                    time.sleep(300)

        hunting_thread = threading.Thread(target=hunt_threats, daemon=True)
        hunting_thread.start()
        self.logger.info("Threat hunting thread started")

    def _proactive_threat_hunt(self):
        """Perform proactive threat hunting"""
        # This would implement advanced threat hunting logic
        # For now, we'll perform basic correlation analysis

        with self._lock:
            # Look for correlated suspicious activities
            recent_events = [
                event
                for event in list(self._threat_events)[-1000:]
                if event.timestamp > datetime.utcnow() - timedelta(hours=24)
            ]

            # Group events by user/service
            user_events = defaultdict(list)
            for event in recent_events:
                key = event.user_identity or event.service_identity or "unknown"
                user_events[key].append(event)

            # Look for patterns
            for user, events in user_events.items():
                if len(events) > 5:  # Multiple threat events for same user
                    self.logger.warning(
                        f"Threat hunting: User {user} has {len(events)} threat events in last 24h"
                    )
