"""
Genesis Secret Monitoring - Comprehensive Security Monitoring and Audit Logging
SHIELD Methodology: Log & Defend components for secret security monitoring

Provides comprehensive audit logging, threat detection, and security monitoring.
"""

import hashlib
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional


class AlertLevel(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ThreatType(Enum):
    """Types of security threats"""

    EXCESSIVE_ACCESS = "excessive_access"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    FAILED_ACCESS = "failed_access"
    ROTATION_FAILURE = "rotation_failure"
    POLICY_VIOLATION = "policy_violation"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"


@dataclass
class AuditLogEntry:
    """Single audit log entry"""

    timestamp: datetime
    operation: str
    status: str
    secret_name: Optional[str] = None
    user_identity: Optional[str] = None
    service_identity: Optional[str] = None
    source_ip: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    risk_score: float = 0.0


@dataclass
class SecurityAlert:
    """Security alert for threats and anomalies"""

    alert_id: str
    threat_type: ThreatType
    alert_level: AlertLevel
    timestamp: datetime
    secret_name: Optional[str] = None
    description: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommended_actions: List[str] = field(default_factory=list)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class SecretMonitor:
    """
    Comprehensive security monitoring for secret operations

    Implements SHIELD L (Log) and D (Defend) components:
    - Complete audit logging for all secret operations
    - Real-time threat detection and alerting
    - Behavioral analysis and anomaly detection
    - Security metrics and reporting
    """

    def __init__(
        self,
        secret_manager,
        alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.secret_manager = secret_manager
        self.alert_callback = alert_callback
        self.logger = logging.getLogger("genesis.secrets.monitor")

        # Audit log storage (in-memory for demo, should use persistent storage)
        self._audit_logs: Deque[Dict[str, Any]] = deque(maxlen=10000)
        self._security_alerts: Dict[str, SecurityAlert] = {}

        # Access tracking for anomaly detection
        self._access_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self._failed_access_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self._user_access_patterns: Dict[str, Dict[str, List[datetime]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Configuration
        self.max_access_rate = 100  # Max accesses per minute per secret
        self.max_failed_attempts = 10  # Max failed attempts per hour per user
        self.anomaly_detection_window = timedelta(hours=1)

        # Thread safety
        self._lock = threading.RLock()

        # Start background monitoring
        self._start_background_monitoring()

        self.logger.info("SecretMonitor initialized")

    def log_secret_access(
        self,
        operation: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
        secret_name: Optional[str] = None,
        user_identity: Optional[str] = None,
        service_identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Log a secret access operation with comprehensive audit details

        Args:
            operation: Type of operation (get, create, rotate, delete, etc.)
            status: Operation status (success, failure, denied, etc.)
            metadata: Additional metadata about the operation
            secret_name: Name of the secret being accessed
            user_identity: Identity of the user/service
            service_identity: Identity of the requesting service
            source_ip: Source IP address
            session_id: Session identifier
        """
        with self._lock:
            # Create audit log entry
            audit_entry = AuditLogEntry(
                timestamp=datetime.utcnow(),
                operation=operation,
                status=status,
                secret_name=secret_name,
                user_identity=user_identity,
                service_identity=service_identity,
                source_ip=source_ip,
                metadata=metadata or {},
                session_id=session_id,
                risk_score=self._calculate_risk_score(operation, status, metadata),
            )

            # Add to audit log
            self._audit_logs.append(audit_entry)

            # Update access patterns for anomaly detection
            self._update_access_patterns(audit_entry)

            # Check for immediate threats
            self._analyze_for_threats(audit_entry)

            # Log to system logger
            self.logger.info(
                f"SECRET_AUDIT: {operation}:{status} secret={secret_name} "
                f"user={user_identity} service={service_identity} "
                f"risk_score={audit_entry.risk_score:.2f}"
            )

    def _calculate_risk_score(
        self, operation: str, status: str, metadata: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate risk score for an operation"""
        base_score = 0.0

        # Base risk by operation type
        operation_risks = {
            "get": 0.1,
            "create": 0.3,
            "update": 0.4,
            "rotate": 0.2,
            "delete": 0.8,
            "emergency_rotate": 0.6,
            "scan": 0.2,
        }
        base_score += operation_risks.get(operation, 0.5)

        # Increase risk for failures
        if status in ["failure", "error", "denied", "not_found", "access_denied"]:
            base_score += 0.5

        # Increase risk based on metadata
        if metadata:
            if metadata.get("source") == "external":
                base_score += 0.3
            if metadata.get("emergency", False):
                base_score += 0.4
            if metadata.get("force", False):
                base_score += 0.3

        return min(base_score, 1.0)

    def _update_access_patterns(self, audit_entry: AuditLogEntry) -> None:
        """Update access patterns for anomaly detection"""
        now = audit_entry.timestamp

        # Track secret access patterns
        if audit_entry.secret_name:
            self._access_patterns[audit_entry.secret_name].append(now)
            # Keep only recent access times
            cutoff = now - self.anomaly_detection_window
            self._access_patterns[audit_entry.secret_name] = [
                t for t in self._access_patterns[audit_entry.secret_name] if t > cutoff
            ]

        # Track failed access patterns
        if audit_entry.status in ["failure", "error", "denied", "access_denied"]:
            key = audit_entry.user_identity or audit_entry.service_identity or "unknown"
            self._failed_access_patterns[key].append(now)
            # Keep only recent failed access times
            cutoff = now - self.anomaly_detection_window
            self._failed_access_patterns[key] = [
                t for t in self._failed_access_patterns[key] if t > cutoff
            ]

        # Track user-specific access patterns
        if audit_entry.user_identity and audit_entry.secret_name:
            self._user_access_patterns[audit_entry.user_identity][
                audit_entry.secret_name
            ].append(now)

    def _analyze_for_threats(self, audit_entry: AuditLogEntry) -> None:
        """Analyze audit entry for immediate security threats"""
        threats: List[Dict[str, Any]] = []

        # Check for excessive access rate
        if audit_entry.secret_name:
            recent_accesses = len(self._access_patterns[audit_entry.secret_name])
            if recent_accesses > self.max_access_rate:
                threats.append(
                    {
                        "type": ThreatType.EXCESSIVE_ACCESS,
                        "level": AlertLevel.WARNING,
                        "description": f"Excessive access to secret {audit_entry.secret_name}: {recent_accesses} accesses in last hour",
                        "evidence": {
                            "access_count": recent_accesses,
                            "window": "1 hour",
                        },
                    }
                )

        # Check for excessive failed attempts
        user_key = (
            audit_entry.user_identity or audit_entry.service_identity or "unknown"
        )
        if user_key != "unknown":
            recent_failures = len(self._failed_access_patterns[user_key])
            if recent_failures > self.max_failed_attempts:
                threats.append(
                    {
                        "type": ThreatType.FAILED_ACCESS,
                        "level": AlertLevel.ERROR,
                        "description": f"Excessive failed access attempts by {user_key}: {recent_failures} failures in last hour",
                        "evidence": {
                            "failure_count": recent_failures,
                            "user": user_key,
                        },
                    }
                )

        # Check for high-risk operations
        if audit_entry.risk_score > 0.7:
            threats.append(
                {
                    "type": ThreatType.SUSPICIOUS_PATTERN,
                    "level": (
                        AlertLevel.WARNING
                        if audit_entry.risk_score < 0.9
                        else AlertLevel.CRITICAL
                    ),
                    "description": f"High-risk operation detected: {audit_entry.operation} with risk score {audit_entry.risk_score:.2f}",
                    "evidence": {
                        "risk_score": audit_entry.risk_score,
                        "operation": audit_entry.operation,
                    },
                }
            )

        # Create alerts for detected threats
        for threat in threats:
            self._create_security_alert(
                threat_type=threat["type"],
                alert_level=threat["level"],
                secret_name=audit_entry.secret_name,
                description=threat["description"],
                evidence=threat["evidence"],
            )

    def _create_security_alert(
        self,
        threat_type: ThreatType,
        alert_level: AlertLevel,
        secret_name: Optional[str] = None,
        description: str = "",
        evidence: Optional[Dict[str, Any]] = None,
    ) -> SecurityAlert:
        """Create and store a security alert"""
        alert_id = f"alert_{int(time.time())}_{hashlib.md5(description.encode()).hexdigest()[:8]}"

        alert = SecurityAlert(
            alert_id=alert_id,
            threat_type=threat_type,
            alert_level=alert_level,
            timestamp=datetime.utcnow(),
            secret_name=secret_name,
            description=description,
            evidence=evidence or {},
            recommended_actions=self._get_recommended_actions(threat_type, evidence),
        )

        self._security_alerts[alert_id] = alert

        # Log alert
        self.logger.warning(
            f"SECURITY_ALERT: {threat_type.value} - {alert_level.value} - {description}"
        )

        # Call alert callback if configured
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")

        return alert

    def _get_recommended_actions(
        self, threat_type: ThreatType, evidence: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Get recommended actions for a threat type"""
        actions = {
            ThreatType.EXCESSIVE_ACCESS: [
                "Review access patterns for the secret",
                "Consider implementing rate limiting",
                "Verify legitimate business need for high access frequency",
            ],
            ThreatType.UNAUTHORIZED_ACCESS: [
                "Review IAM permissions for the user/service",
                "Audit recent access patterns",
                "Consider rotating the secret if compromised",
            ],
            ThreatType.FAILED_ACCESS: [
                "Investigate the source of failed attempts",
                "Consider temporary access restriction",
                "Review authentication mechanisms",
            ],
            ThreatType.ROTATION_FAILURE: [
                "Investigate rotation failure cause",
                "Verify secret rotation policies",
                "Consider manual intervention",
            ],
            ThreatType.SUSPICIOUS_PATTERN: [
                "Investigate the suspicious activity",
                "Review recent changes to access patterns",
                "Consider increasing monitoring for this secret",
            ],
        }

        return actions.get(threat_type, ["Investigate the security incident"])

    def get_audit_log(
        self,
        secret_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        operation: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Get audit log entries with filtering

        Args:
            secret_name: Filter by specific secret
            start_time: Start time for filtering
            end_time: End time for filtering
            operation: Filter by operation type
            status: Filter by operation status
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        with self._lock:
            entries = list(self._audit_logs)

            # Apply filters
            filtered_entries = []
            for entry in entries:
                # Time range filter
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue

                # Secret name filter
                if secret_name and entry.secret_name != secret_name:
                    continue

                # Operation filter
                if operation and entry.operation != operation:
                    continue

                # Status filter
                if status and entry.status != status:
                    continue

                filtered_entries.append(entry)

            # Sort by timestamp (newest first)
            filtered_entries.sort(key=lambda e: e.timestamp, reverse=True)

            # Limit results
            filtered_entries = filtered_entries[:limit]

            # Convert to dictionaries
            return [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "operation": entry.operation,
                    "status": entry.status,
                    "secret_name": entry.secret_name,
                    "user_identity": entry.user_identity,
                    "service_identity": entry.service_identity,
                    "source_ip": entry.source_ip,
                    "metadata": entry.metadata,
                    "session_id": entry.session_id,
                    "risk_score": entry.risk_score,
                }
                for entry in filtered_entries
            ]

    def get_security_alerts(
        self,
        threat_type: Optional[ThreatType] = None,
        alert_level: Optional[AlertLevel] = None,
        resolved: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get security alerts with filtering

        Args:
            threat_type: Filter by threat type
            alert_level: Filter by alert level
            resolved: Filter by resolution status
            limit: Maximum number of alerts to return

        Returns:
            List of security alerts
        """
        with self._lock:
            alerts = list(self._security_alerts.values())

            # Apply filters
            filtered_alerts = []
            for alert in alerts:
                if threat_type and alert.threat_type != threat_type:
                    continue
                if alert_level and alert.alert_level != alert_level:
                    continue
                if resolved is not None and alert.resolved != resolved:
                    continue

                filtered_alerts.append(alert)

            # Sort by timestamp (newest first)
            filtered_alerts.sort(key=lambda a: a.timestamp, reverse=True)

            # Limit results
            filtered_alerts = filtered_alerts[:limit]

            # Convert to dictionaries
            return [
                {
                    "alert_id": alert.alert_id,
                    "threat_type": alert.threat_type.value,
                    "alert_level": alert.alert_level.value,
                    "timestamp": alert.timestamp.isoformat(),
                    "secret_name": alert.secret_name,
                    "description": alert.description,
                    "evidence": alert.evidence,
                    "recommended_actions": alert.recommended_actions,
                    "resolved": alert.resolved,
                    "resolved_at": (
                        alert.resolved_at.isoformat() if alert.resolved_at else None
                    ),
                }
                for alert in filtered_alerts
            ]

    def resolve_alert(self, alert_id: str, resolution_notes: str = "") -> bool:
        """
        Resolve a security alert

        Args:
            alert_id: ID of the alert to resolve
            resolution_notes: Notes about the resolution

        Returns:
            True if alert was resolved successfully
        """
        with self._lock:
            if alert_id not in self._security_alerts:
                return False

            alert = self._security_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()

            if resolution_notes:
                alert.evidence["resolution_notes"] = resolution_notes

            self.logger.info(f"Security alert resolved: {alert_id}")
            return True

    def get_security_metrics(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive security metrics

        Args:
            start_time: Start time for metrics calculation
            end_time: End time for metrics calculation

        Returns:
            Dictionary of security metrics
        """
        with self._lock:
            # Default to last 24 hours if no time range specified
            if not start_time:
                start_time = datetime.utcnow() - timedelta(days=1)
            if not end_time:
                end_time = datetime.utcnow()

            # Filter audit logs by time range
            relevant_logs = [
                entry
                for entry in self._audit_logs
                if start_time <= entry.timestamp <= end_time
            ]

            # Calculate metrics
            metrics: Dict[str, Any] = {
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                },
                "total_operations": len(relevant_logs),
                "operations_by_type": defaultdict(int),
                "operations_by_status": defaultdict(int),
                "unique_secrets_accessed": set(),  # type: ignore[misc]
                "unique_users": set(),  # type: ignore[misc]
                "unique_services": set(),  # type: ignore[misc]
                "risk_distribution": {
                    "low": 0,
                    "medium": 0,
                    "high": 0,
                },
                "security_alerts": {
                    "total": len(
                        [
                            a
                            for a in self._security_alerts.values()
                            if start_time <= a.timestamp <= end_time
                        ]
                    ),
                    "by_level": defaultdict(int),
                    "by_type": defaultdict(int),
                    "resolved": 0,
                    "unresolved": 0,
                },
            }

            # Process audit logs
            for entry in relevant_logs:
                metrics["operations_by_type"][entry.operation] += 1
                metrics["operations_by_status"][entry.status] += 1

                if entry.secret_name:
                    metrics["unique_secrets_accessed"].add(entry.secret_name)
                if entry.user_identity:
                    metrics["unique_users"].add(entry.user_identity)
                if entry.service_identity:
                    metrics["unique_services"].add(entry.service_identity)

                # Risk distribution
                if entry.risk_score < 0.3:
                    metrics["risk_distribution"]["low"] += 1
                elif entry.risk_score < 0.7:
                    metrics["risk_distribution"]["medium"] += 1
                else:
                    metrics["risk_distribution"]["high"] += 1

            # Process security alerts
            relevant_alerts = [
                alert
                for alert in self._security_alerts.values()
                if start_time <= alert.timestamp <= end_time
            ]

            for alert in relevant_alerts:
                metrics["security_alerts"]["by_level"][alert.alert_level.value] += 1
                metrics["security_alerts"]["by_type"][alert.threat_type.value] += 1

                if alert.resolved:
                    metrics["security_alerts"]["resolved"] += 1
                else:
                    metrics["security_alerts"]["unresolved"] += 1

            # Convert sets to counts
            metrics["unique_secrets_accessed"] = len(metrics["unique_secrets_accessed"])
            metrics["unique_users"] = len(metrics["unique_users"])
            metrics["unique_services"] = len(metrics["unique_services"])

            # Convert defaultdicts to regular dicts
            metrics["operations_by_type"] = dict(metrics["operations_by_type"])
            metrics["operations_by_status"] = dict(metrics["operations_by_status"])
            metrics["security_alerts"]["by_level"] = dict(
                metrics["security_alerts"]["by_level"]
            )
            metrics["security_alerts"]["by_type"] = dict(
                metrics["security_alerts"]["by_type"]
            )

            return metrics

    def _start_background_monitoring(self) -> None:
        """Start background monitoring tasks"""

        def background_monitor():
            while True:
                try:
                    # Clean up old access patterns
                    self._cleanup_old_patterns()

                    # Perform periodic anomaly detection
                    self._detect_anomalies()

                    # Sleep for a minute before next check
                    time.sleep(60)

                except Exception as e:
                    self.logger.error(f"Background monitoring error: {e}")
                    time.sleep(60)

        # Start background thread
        monitor_thread = threading.Thread(target=background_monitor, daemon=True)
        monitor_thread.start()

        self.logger.info("Background monitoring started")

    def _cleanup_old_patterns(self) -> None:
        """Clean up old access patterns to prevent memory leaks"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        with self._lock:
            # Clean up access patterns
            for secret_name in list(self._access_patterns.keys()):
                self._access_patterns[secret_name] = [
                    t for t in self._access_patterns[secret_name] if t > cutoff_time
                ]
                if not self._access_patterns[secret_name]:
                    del self._access_patterns[secret_name]

            # Clean up failed access patterns
            for user in list(self._failed_access_patterns.keys()):
                self._failed_access_patterns[user] = [
                    t for t in self._failed_access_patterns[user] if t > cutoff_time
                ]
                if not self._failed_access_patterns[user]:
                    del self._failed_access_patterns[user]

    def _detect_anomalies(self) -> None:
        """Detect behavioral anomalies in secret access patterns"""
        # This would implement more sophisticated anomaly detection
        # For now, we'll keep it simple
        pass
