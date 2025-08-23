"""
Google Chronicle Integration for Advanced Threat Hunting
SHIELD Methodology implementation for comprehensive threat detection and analysis
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import requests
from google.auth import default
from google.auth.transport.requests import Request

from .gcp_security_center import ThreatSeverity


class ThreatHuntingScope(Enum):
    """Threat hunting scope levels"""

    TARGETED = "TARGETED"  # Specific IOCs or entities
    BEHAVIORAL = "BEHAVIORAL"  # Behavioral pattern analysis
    COMPREHENSIVE = "COMPREHENSIVE"  # Full environment sweep
    REAL_TIME = "REAL_TIME"  # Continuous monitoring


class IOCType(Enum):
    """Indicator of Compromise types"""

    DOMAIN = "DOMAIN"
    IP_ADDRESS = "IP_ADDRESS"
    FILE_HASH = "FILE_HASH"
    EMAIL = "EMAIL"
    URL = "URL"
    PROCESS = "PROCESS"
    REGISTRY_KEY = "REGISTRY_KEY"
    USER_AGENT = "USER_AGENT"


class ThreatCategory(Enum):
    """Threat categories"""

    MALWARE = "MALWARE"
    PHISHING = "PHISHING"
    C2_COMMUNICATION = "C2_COMMUNICATION"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    LATERAL_MOVEMENT = "LATERAL_MOVEMENT"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    PERSISTENCE = "PERSISTENCE"
    RECONNAISSANCE = "RECONNAISSANCE"


@dataclass
class ThreatIndicator:
    """Threat indicator definition"""

    ioc_value: str
    ioc_type: IOCType
    threat_category: ThreatCategory
    severity: ThreatSeverity
    confidence_score: float
    source: str
    description: str
    created_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    related_campaigns: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreatHuntResult:
    """Threat hunting result"""

    hunt_id: str
    query_name: str
    detection_time: datetime
    matched_events: List[Dict[str, Any]] = field(default_factory=list)
    threat_indicators: List[ThreatIndicator] = field(default_factory=list)
    severity: ThreatSeverity = ThreatSeverity.MEDIUM
    confidence: float = 0.0
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    affected_assets: Set[str] = field(default_factory=set)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class HuntingQuery:
    """Chronicle hunting query definition"""

    query_id: str
    name: str
    description: str
    yara_l_query: str
    scope: ThreatHuntingScope
    threat_categories: List[ThreatCategory] = field(default_factory=list)
    schedule_interval_hours: Optional[int] = None
    enabled: bool = True
    created_by: str = "system"
    last_run: Optional[datetime] = None


class ChronicleAPI:
    """Chronicle API client wrapper"""

    def __init__(self, customer_id: str, region: str = "us"):
        self.customer_id = customer_id
        self.region = region
        self.base_url = f"https://{region}-chronicle.googleapis.com"
        self.credentials, self.project_id = default()

        # Refresh credentials
        self.credentials.refresh(Request())

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.credentials.token}",
                "Content-Type": "application/json",
            }
        )

    async def search_iocs(
        self,
        ioc_values: List[str],
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """Search for IOCs in Chronicle data"""
        endpoint = f"{self.base_url}/v1/ioc/listiocdetails"

        request_data = {
            "artifact_value": ioc_values,
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z",
        }

        response = self.session.post(endpoint, json=request_data)
        response.raise_for_status()

        return response.json()

    async def execute_hunt_query(
        self,
        yara_l_query: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """Execute YARA-L hunting query"""
        endpoint = f"{self.base_url}/v1/tools/yaral/search"

        request_data = {
            "rule": yara_l_query,
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z",
        }

        response = self.session.post(endpoint, json=request_data)
        response.raise_for_status()

        return response.json()

    async def get_asset_details(self, asset_name: str) -> Dict[str, Any]:
        """Get detailed asset information"""
        endpoint = f"{self.base_url}/v1/asset/listassets"

        request_data = {
            "asset_name": asset_name,
        }

        response = self.session.post(endpoint, json=request_data)
        response.raise_for_status()

        return response.json()

    async def search_timeline(
        self,
        hostname: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """Search asset timeline"""
        endpoint = f"{self.base_url}/v1/asset/listassettimeline"

        request_data = {
            "asset_name": hostname,
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z",
        }

        response = self.session.post(endpoint, json=request_data)
        response.raise_for_status()

        return response.json()


class ChroniclethreatHunting:
    """
    Chronicle-based threat hunting and analysis platform

    SHIELD Implementation:
    S - Scan: Continuous IOC scanning and behavioral analysis
    H - Harden: Automated threat detection rule creation and tuning
    I - Isolate: Asset-based threat isolation and timeline analysis
    E - Encrypt: Secure threat intelligence sharing and storage
    L - Log: Comprehensive threat hunting audit and timeline logging
    D - Defend: Automated threat response and intelligence enrichment
    """

    def __init__(
        self,
        customer_id: str,
        region: str = "us",
        project_id: Optional[str] = None,
        enable_real_time_hunting: bool = True,
        threat_intel_feeds: Optional[List[str]] = None,
    ):
        self.customer_id = customer_id
        self.region = region
        self.project_id = project_id
        self.enable_real_time_hunting = enable_real_time_hunting
        self.threat_intel_feeds = threat_intel_feeds or []

        self.logger = self._setup_logging()

        # Initialize Chronicle API client
        self.chronicle = ChronicleAPI(customer_id, region)

        # Threat hunting state
        self.hunting_queries: Dict[str, HuntingQuery] = {}
        self.threat_indicators: Dict[str, ThreatIndicator] = {}
        self.hunt_results: Dict[str, ThreatHuntResult] = {}

        # Real-time hunting task
        self.real_time_task: Optional[asyncio.Task] = None

        # Initialize default hunting queries
        self._initialize_default_queries()

        # Start real-time hunting if enabled
        if enable_real_time_hunting:
            self.real_time_task = asyncio.create_task(self._real_time_hunting_loop())

        self.logger.info(
            f"Chronicle Threat Hunting initialized for customer: {customer_id}"
        )

    def _setup_logging(self) -> logging.Logger:
        """Setup security-focused logging"""
        logger = logging.getLogger(f"genesis.security.chronicle.{self.customer_id}")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [CHRONICLE] %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def _initialize_default_queries(self):
        """Initialize default threat hunting queries"""

        # Malware detection query
        malware_query = HuntingQuery(
            query_id="malware_detection",
            name="Malware Activity Detection",
            description="Detect malware execution and suspicious file activity",
            yara_l_query="""
            rule malware_execution {
                meta:
                    description = "Detect potential malware execution"
                    severity = "HIGH"
                
                events:
                    $process = $detection.metadata.event_type = "PROCESS_LAUNCH"
                    $file = $detection.metadata.event_type = "FILE_CREATION"
                
                condition:
                    $process and (
                        $process.principal.process.command_line contains "powershell" and
                        $process.principal.process.command_line contains "-encodedcommand"
                    ) or (
                        $file and $file.target.file.full_path matches /.*\.(exe|scr|bat|cmd|pif)$/ and
                        $file.target.file.md5 in %malware_hashes
                    )
            }
            """,
            scope=ThreatHuntingScope.BEHAVIORAL,
            threat_categories=[ThreatCategory.MALWARE],
            schedule_interval_hours=1,
        )
        self.hunting_queries[malware_query.query_id] = malware_query

        # Data exfiltration detection
        exfiltration_query = HuntingQuery(
            query_id="data_exfiltration",
            name="Data Exfiltration Detection",
            description="Detect unusual data transfer patterns",
            yara_l_query="""
            rule data_exfiltration {
                meta:
                    description = "Detect potential data exfiltration"
                    severity = "CRITICAL"
                
                events:
                    $network = $detection.metadata.event_type = "NETWORK_CONNECTION"
                    $file = $detection.metadata.event_type = "FILE_READ"
                
                condition:
                    $network and $file and (
                        $network.target.ip != /^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)/ and
                        $file.target.file.size > 10000000  // > 10MB
                    )
                
                outcome:
                    $network and $file within 5m
            }
            """,
            scope=ThreatHuntingScope.BEHAVIORAL,
            threat_categories=[ThreatCategory.DATA_EXFILTRATION],
            schedule_interval_hours=2,
        )
        self.hunting_queries[exfiltration_query.query_id] = exfiltration_query

        # C2 communication detection
        c2_query = HuntingQuery(
            query_id="c2_communication",
            name="C2 Communication Detection",
            description="Detect command and control communication patterns",
            yara_l_query="""
            rule c2_communication {
                meta:
                    description = "Detect C2 communication patterns"
                    severity = "HIGH"
                
                events:
                    $dns = $detection.metadata.event_type = "NETWORK_DNS"
                    $http = $detection.metadata.event_type = "NETWORK_HTTP"
                
                condition:
                    ($dns and $dns.network.dns.questions.name matches /[a-z]{10,}\.(tk|ml|ga|cf)$/) or
                    ($http and (
                        $http.network.http.user_agent contains "Mozilla/4.0" or
                        $http.network.http.response_code = 404 and
                        $http.target.url contains "/api/"
                    ))
            }
            """,
            scope=ThreatHuntingScope.BEHAVIORAL,
            threat_categories=[ThreatCategory.C2_COMMUNICATION],
            schedule_interval_hours=1,
        )
        self.hunting_queries[c2_query.query_id] = c2_query

        # Lateral movement detection
        lateral_movement_query = HuntingQuery(
            query_id="lateral_movement",
            name="Lateral Movement Detection",
            description="Detect lateral movement techniques",
            yara_l_query="""
            rule lateral_movement {
                meta:
                    description = "Detect lateral movement activities"
                    severity = "HIGH"
                
                events:
                    $auth = $detection.metadata.event_type = "USER_LOGIN"
                    $network = $detection.metadata.event_type = "NETWORK_CONNECTION"
                
                condition:
                    $auth and $network and (
                        $auth.security_result.action = "ALLOW" and
                        $auth.principal.user.user_display_name != /^(admin|administrator|root)$/ and
                        $network.target.port in [445, 139, 135, 3389]
                    )
                
                outcome:
                    $auth and $network within 10m
            }
            """,
            scope=ThreatHuntingScope.BEHAVIORAL,
            threat_categories=[ThreatCategory.LATERAL_MOVEMENT],
            schedule_interval_hours=2,
        )
        self.hunting_queries[lateral_movement_query.query_id] = lateral_movement_query

        self.logger.info(
            f"Initialized {len(self.hunting_queries)} default hunting queries"
        )

    # SHIELD Method: SCAN - Threat Indicator Scanning
    async def scan_iocs(
        self,
        ioc_values: List[str],
        time_window_hours: int = 24,
        ioc_type: Optional[IOCType] = None,
    ) -> List[ThreatHuntResult]:
        """
        Scan for specific Indicators of Compromise

        Args:
            ioc_values: List of IOC values to search for
            time_window_hours: Time window for search
            ioc_type: Type of IOCs being searched

        Returns:
            List of threat hunting results
        """
        self.logger.info(f"Scanning for {len(ioc_values)} IOCs in Chronicle")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)

        hunt_results = []

        try:
            # Search for IOCs in Chronicle
            search_response = await self.chronicle.search_iocs(
                ioc_values, start_time, end_time
            )

            # Process search results
            if "artifacts" in search_response:
                for artifact in search_response["artifacts"]:
                    hunt_id = f"ioc-scan-{int(time.time())}-{hash(artifact.get('artifact_value', '')) % 10000}"

                    result = ThreatHuntResult(
                        hunt_id=hunt_id,
                        query_name="IOC Scanning",
                        detection_time=datetime.utcnow(),
                    )

                    # Extract matched events
                    if "events" in artifact:
                        result.matched_events = artifact["events"]

                        # Calculate severity based on event count and types
                        result.severity = self._calculate_ioc_severity(artifact)
                        result.confidence = min(len(artifact["events"]) * 0.2, 1.0)

                        # Extract affected assets
                        for event in artifact["events"]:
                            if (
                                "principal" in event
                                and "hostname" in event["principal"]
                            ):
                                result.affected_assets.add(
                                    event["principal"]["hostname"]
                                )
                            if "target" in event and "hostname" in event["target"]:
                                result.affected_assets.add(event["target"]["hostname"])

                    # Create threat indicator
                    if artifact.get("artifact_value"):
                        threat_indicator = ThreatIndicator(
                            ioc_value=artifact["artifact_value"],
                            ioc_type=ioc_type
                            or self._detect_ioc_type(artifact["artifact_value"]),
                            threat_category=ThreatCategory.MALWARE,  # Default category
                            severity=result.severity,
                            confidence_score=result.confidence,
                            source="Chronicle IOC Scan",
                            description=f"IOC detected in Chronicle data: {artifact['artifact_value']}",
                            created_at=datetime.utcnow(),
                            last_seen=datetime.utcnow(),
                        )

                        result.threat_indicators.append(threat_indicator)
                        self.threat_indicators[
                            threat_indicator.ioc_value
                        ] = threat_indicator

                    # Generate recommendations
                    result.recommendations = self._generate_ioc_recommendations(
                        artifact
                    )

                    hunt_results.append(result)
                    self.hunt_results[hunt_id] = result

            self.logger.info(
                f"IOC scan completed: {len(hunt_results)} threats detected"
            )

            return hunt_results

        except Exception as e:
            self.logger.error(f"IOC scanning failed: {e}")
            raise

    def _calculate_ioc_severity(self, artifact: Dict[str, Any]) -> ThreatSeverity:
        """Calculate severity based on IOC artifact data"""
        event_count = len(artifact.get("events", []))

        # Base severity on event count and types
        if event_count > 10:
            return ThreatSeverity.CRITICAL
        elif event_count > 5:
            return ThreatSeverity.HIGH
        elif event_count > 1:
            return ThreatSeverity.MEDIUM
        else:
            return ThreatSeverity.LOW

    def _detect_ioc_type(self, ioc_value: str) -> IOCType:
        """Auto-detect IOC type from value"""
        if (
            "." in ioc_value
            and not ioc_value.replace(".", "").replace(":", "").isdigit()
        ):
            return IOCType.DOMAIN
        elif ioc_value.replace(".", "").replace(":", "").isdigit():
            return IOCType.IP_ADDRESS
        elif len(ioc_value) in [32, 40, 64, 128]:  # Common hash lengths
            return IOCType.FILE_HASH
        elif "@" in ioc_value:
            return IOCType.EMAIL
        elif ioc_value.startswith(("http://", "https://")):
            return IOCType.URL
        else:
            return IOCType.PROCESS

    def _generate_ioc_recommendations(self, artifact: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on IOC findings"""
        recommendations = []

        event_count = len(artifact.get("events", []))

        if event_count > 5:
            recommendations.append(
                "High IOC activity detected - initiate incident response"
            )
            recommendations.append("Isolate affected systems immediately")

        recommendations.append("Block IOC at network perimeter")
        recommendations.append("Scan all systems for additional indicators")
        recommendations.append("Review logs for related suspicious activity")

        return recommendations

    # SHIELD Method: HARDEN - Behavioral Threat Hunting
    async def execute_behavioral_hunt(
        self,
        query_id: str,
        time_window_hours: int = 24,
        custom_parameters: Optional[Dict[str, Any]] = None,
    ) -> ThreatHuntResult:
        """
        Execute behavioral threat hunting query

        Args:
            query_id: Hunting query identifier
            time_window_hours: Time window for hunt
            custom_parameters: Custom query parameters

        Returns:
            Threat hunting result
        """
        if query_id not in self.hunting_queries:
            raise ValueError(f"Hunting query not found: {query_id}")

        query = self.hunting_queries[query_id]

        self.logger.info(f"Executing behavioral hunt: {query.name}")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)

        hunt_id = f"behavioral-{query_id}-{int(time.time())}"

        try:
            # Execute YARA-L query in Chronicle
            hunt_response = await self.chronicle.execute_hunt_query(
                query.yara_l_query, start_time, end_time
            )

            # Process hunt results
            result = ThreatHuntResult(
                hunt_id=hunt_id,
                query_name=query.name,
                detection_time=datetime.utcnow(),
            )

            if "events" in hunt_response:
                result.matched_events = hunt_response["events"]

                # Analyze matched events
                result.severity = self._analyze_behavioral_severity(
                    hunt_response["events"], query.threat_categories
                )
                result.confidence = self._calculate_behavioral_confidence(hunt_response)

                # Extract timeline and affected assets
                result.timeline = self._build_event_timeline(hunt_response["events"])

                for event in hunt_response["events"]:
                    if "principal" in event and "hostname" in event["principal"]:
                        result.affected_assets.add(event["principal"]["hostname"])
                    if "target" in event and "hostname" in event["target"]:
                        result.affected_assets.add(event["target"]["hostname"])

                # Generate threat indicators from behavioral patterns
                behavioral_indicators = self._extract_behavioral_indicators(
                    hunt_response["events"], query.threat_categories
                )
                result.threat_indicators.extend(behavioral_indicators)

                # Store new indicators
                for indicator in behavioral_indicators:
                    self.threat_indicators[indicator.ioc_value] = indicator

                # Generate recommendations
                result.recommendations = self._generate_behavioral_recommendations(
                    result, query
                )

            # Update query last run time
            query.last_run = datetime.utcnow()

            # Store result
            self.hunt_results[hunt_id] = result

            self.logger.info(
                f"Behavioral hunt completed: {query.name} - "
                f"{len(result.matched_events)} events, "
                f"severity: {result.severity.value}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Behavioral hunt failed {query.name}: {e}")
            raise

    def _analyze_behavioral_severity(
        self,
        events: List[Dict[str, Any]],
        threat_categories: List[ThreatCategory],
    ) -> ThreatSeverity:
        """Analyze severity of behavioral detection"""
        event_count = len(events)

        # High-risk categories
        high_risk_categories = [
            ThreatCategory.MALWARE,
            ThreatCategory.DATA_EXFILTRATION,
            ThreatCategory.C2_COMMUNICATION,
        ]

        # Check for high-risk categories
        has_high_risk = any(cat in high_risk_categories for cat in threat_categories)

        if has_high_risk and event_count > 10:
            return ThreatSeverity.CRITICAL
        elif has_high_risk or event_count > 5:
            return ThreatSeverity.HIGH
        elif event_count > 2:
            return ThreatSeverity.MEDIUM
        else:
            return ThreatSeverity.LOW

    def _calculate_behavioral_confidence(self, hunt_response: Dict[str, Any]) -> float:
        """Calculate confidence score for behavioral detection"""
        events = hunt_response.get("events", [])

        if not events:
            return 0.0

        # Factors that increase confidence
        confidence_factors = []

        # Multiple affected assets
        unique_assets = set()
        for event in events:
            if "principal" in event and "hostname" in event["principal"]:
                unique_assets.add(event["principal"]["hostname"])

        if len(unique_assets) > 1:
            confidence_factors.append(0.3)

        # Time span of activity
        timestamps = []
        for event in events:
            if "metadata" in event and "event_timestamp" in event["metadata"]:
                timestamps.append(event["metadata"]["event_timestamp"])

        if len(set(timestamps)) > len(timestamps) * 0.5:  # Distributed over time
            confidence_factors.append(0.2)

        # Event diversity
        event_types = set()
        for event in events:
            if "metadata" in event and "event_type" in event["metadata"]:
                event_types.add(event["metadata"]["event_type"])

        if len(event_types) > 2:
            confidence_factors.append(0.3)

        # Base confidence on event count
        base_confidence = min(len(events) * 0.1, 0.5)

        return min(base_confidence + sum(confidence_factors), 1.0)

    def _build_event_timeline(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build chronological timeline from events"""
        timeline = []

        for event in events:
            timeline_entry = {
                "timestamp": event.get("metadata", {}).get("event_timestamp", ""),
                "event_type": event.get("metadata", {}).get("event_type", "UNKNOWN"),
                "principal": event.get("principal", {}).get("hostname", "unknown"),
                "target": event.get("target", {}).get("hostname", "unknown"),
                "description": self._generate_event_description(event),
            }
            timeline.append(timeline_entry)

        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])

        return timeline

    def _generate_event_description(self, event: Dict[str, Any]) -> str:
        """Generate human-readable event description"""
        event_type = event.get("metadata", {}).get("event_type", "UNKNOWN")

        if event_type == "PROCESS_LAUNCH":
            process = event.get("target", {}).get("process", {})
            return f"Process launched: {process.get('file', {}).get('full_path', 'unknown')}"
        elif event_type == "NETWORK_CONNECTION":
            target = event.get("target", {})
            return f"Network connection to {target.get('hostname', 'unknown')}:{target.get('port', 'unknown')}"
        elif event_type == "FILE_CREATION":
            file_info = event.get("target", {}).get("file", {})
            return f"File created: {file_info.get('full_path', 'unknown')}"
        else:
            return f"Event: {event_type}"

    def _extract_behavioral_indicators(
        self,
        events: List[Dict[str, Any]],
        threat_categories: List[ThreatCategory],
    ) -> List[ThreatIndicator]:
        """Extract threat indicators from behavioral patterns"""
        indicators = []

        # Extract common IOCs from events
        domains = set()
        ip_addresses = set()
        file_hashes = set()

        for event in events:
            # Extract domains from DNS events
            if event.get("metadata", {}).get("event_type") == "NETWORK_DNS":
                dns_name = (
                    event.get("network", {})
                    .get("dns", {})
                    .get("questions", {})
                    .get("name")
                )
                if dns_name:
                    domains.add(dns_name)

            # Extract IPs from network events
            if "network" in event:
                target_ip = event.get("target", {}).get("ip")
                if target_ip:
                    ip_addresses.add(target_ip)

            # Extract file hashes
            if "target" in event and "file" in event["target"]:
                file_hash = event["target"]["file"].get("md5") or event["target"][
                    "file"
                ].get("sha256")
                if file_hash:
                    file_hashes.add(file_hash)

        # Create indicators from extracted IOCs
        for domain in domains:
            indicator = ThreatIndicator(
                ioc_value=domain,
                ioc_type=IOCType.DOMAIN,
                threat_category=threat_categories[0]
                if threat_categories
                else ThreatCategory.RECONNAISSANCE,
                severity=ThreatSeverity.MEDIUM,
                confidence_score=0.7,
                source="Chronicle Behavioral Hunt",
                description=f"Domain observed in behavioral pattern: {domain}",
                created_at=datetime.utcnow(),
                last_seen=datetime.utcnow(),
            )
            indicators.append(indicator)

        for ip in ip_addresses:
            indicator = ThreatIndicator(
                ioc_value=ip,
                ioc_type=IOCType.IP_ADDRESS,
                threat_category=threat_categories[0]
                if threat_categories
                else ThreatCategory.C2_COMMUNICATION,
                severity=ThreatSeverity.MEDIUM,
                confidence_score=0.6,
                source="Chronicle Behavioral Hunt",
                description=f"IP address observed in behavioral pattern: {ip}",
                created_at=datetime.utcnow(),
                last_seen=datetime.utcnow(),
            )
            indicators.append(indicator)

        for file_hash in file_hashes:
            indicator = ThreatIndicator(
                ioc_value=file_hash,
                ioc_type=IOCType.FILE_HASH,
                threat_category=ThreatCategory.MALWARE,
                severity=ThreatSeverity.HIGH,
                confidence_score=0.8,
                source="Chronicle Behavioral Hunt",
                description=f"File hash observed in behavioral pattern: {file_hash}",
                created_at=datetime.utcnow(),
                last_seen=datetime.utcnow(),
            )
            indicators.append(indicator)

        return indicators

    def _generate_behavioral_recommendations(
        self,
        result: ThreatHuntResult,
        query: HuntingQuery,
    ) -> List[str]:
        """Generate recommendations based on behavioral hunt results"""
        recommendations = []

        if result.severity == ThreatSeverity.CRITICAL:
            recommendations.append("CRITICAL: Initiate immediate incident response")
            recommendations.append("Isolate affected assets from network")
            recommendations.append("Collect forensic images of affected systems")

        if result.severity in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL]:
            recommendations.append("Block identified IOCs at security controls")
            recommendations.append("Hunt for additional indicators across environment")

        if result.affected_assets:
            recommendations.append(
                f"Review detailed logs for {len(result.affected_assets)} affected assets"
            )

        # Category-specific recommendations
        for category in query.threat_categories:
            if category == ThreatCategory.DATA_EXFILTRATION:
                recommendations.append("Review data access logs and DLP alerts")
                recommendations.append("Verify backup integrity and availability")
            elif category == ThreatCategory.MALWARE:
                recommendations.append("Run full antivirus scans on affected systems")
                recommendations.append("Check for persistence mechanisms")
            elif category == ThreatCategory.C2_COMMUNICATION:
                recommendations.append("Block C2 domains/IPs at DNS and proxy")
                recommendations.append("Monitor for additional C2 channels")

        recommendations.append("Update threat hunting queries based on findings")

        return recommendations

    # SHIELD Method: ISOLATE - Asset Timeline Analysis
    async def analyze_asset_timeline(
        self,
        hostname: str,
        time_window_hours: int = 24,
        include_related_assets: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze detailed timeline for specific asset

        Args:
            hostname: Target hostname for analysis
            time_window_hours: Time window for analysis
            include_related_assets: Include related asset analysis

        Returns:
            Asset timeline analysis results
        """
        self.logger.info(f"Analyzing asset timeline for: {hostname}")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)

        try:
            # Get asset timeline from Chronicle
            timeline_response = await self.chronicle.search_timeline(
                hostname, start_time, end_time
            )

            # Get asset details
            asset_details = await self.chronicle.get_asset_details(hostname)

            analysis = {
                "hostname": hostname,
                "analysis_time": datetime.utcnow().isoformat(),
                "time_window_hours": time_window_hours,
                "asset_details": asset_details,
                "timeline_events": [],
                "risk_score": 0.0,
                "threat_indicators": [],
                "anomalies": [],
                "recommendations": [],
                "related_assets": [],
            }

            # Process timeline events
            if "timeline" in timeline_response:
                analysis["timeline_events"] = timeline_response["timeline"]

                # Analyze for anomalies and threats
                analysis["anomalies"] = self._detect_timeline_anomalies(
                    timeline_response["timeline"]
                )

                # Calculate risk score
                analysis["risk_score"] = self._calculate_asset_risk_score(
                    timeline_response["timeline"], analysis["anomalies"]
                )

                # Extract threat indicators
                analysis["threat_indicators"] = self._extract_timeline_indicators(
                    timeline_response["timeline"]
                )

            # Analyze related assets if requested
            if include_related_assets:
                analysis["related_assets"] = await self._analyze_related_assets(
                    hostname, timeline_response.get("timeline", [])
                )

            # Generate recommendations
            analysis["recommendations"] = self._generate_timeline_recommendations(
                analysis
            )

            self.logger.info(
                f"Asset timeline analysis completed for {hostname}: "
                f"risk_score={analysis['risk_score']:.2f}, "
                f"{len(analysis['anomalies'])} anomalies detected"
            )

            return analysis

        except Exception as e:
            self.logger.error(f"Asset timeline analysis failed for {hostname}: {e}")
            raise

    def _detect_timeline_anomalies(
        self, timeline_events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in asset timeline"""
        anomalies = []

        if not timeline_events:
            return anomalies

        # Analyze event patterns
        event_type_counts = {}
        hourly_activity = {}

        for event in timeline_events:
            event_type = event.get("metadata", {}).get("event_type", "UNKNOWN")
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

            # Parse timestamp hour
            timestamp = event.get("metadata", {}).get("event_timestamp", "")
            if timestamp:
                try:
                    event_time = datetime.fromisoformat(
                        timestamp.replace("Z", "+00:00")
                    )
                    hour = event_time.hour
                    hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
                except:
                    pass

        # Detect anomalous event volumes
        for event_type, count in event_type_counts.items():
            if count > 100:  # High volume threshold
                anomalies.append(
                    {
                        "type": "high_event_volume",
                        "event_type": event_type,
                        "count": count,
                        "severity": "HIGH" if count > 500 else "MEDIUM",
                        "description": f"High volume of {event_type} events: {count}",
                    }
                )

        # Detect off-hours activity
        off_hours = [h for h in hourly_activity.keys() if h < 6 or h > 22]
        if off_hours:
            total_off_hours = sum(hourly_activity[h] for h in off_hours)
            if total_off_hours > len(timeline_events) * 0.3:  # > 30% off-hours
                anomalies.append(
                    {
                        "type": "off_hours_activity",
                        "count": total_off_hours,
                        "percentage": total_off_hours / len(timeline_events) * 100,
                        "severity": "MEDIUM",
                        "description": f"Significant off-hours activity: {total_off_hours} events",
                    }
                )

        return anomalies

    def _calculate_asset_risk_score(
        self,
        timeline_events: List[Dict[str, Any]],
        anomalies: List[Dict[str, Any]],
    ) -> float:
        """Calculate risk score for asset based on timeline and anomalies"""
        base_score = 0.0

        # Base score from event volume
        event_count = len(timeline_events)
        if event_count > 1000:
            base_score += 0.3
        elif event_count > 500:
            base_score += 0.2
        elif event_count > 100:
            base_score += 0.1

        # Add score for anomalies
        high_severity_anomalies = len(
            [a for a in anomalies if a.get("severity") == "HIGH"]
        )
        medium_severity_anomalies = len(
            [a for a in anomalies if a.get("severity") == "MEDIUM"]
        )

        base_score += high_severity_anomalies * 0.3 + medium_severity_anomalies * 0.2

        # Check for high-risk event types
        high_risk_events = ["PROCESS_LAUNCH", "NETWORK_CONNECTION", "FILE_DELETION"]
        for event in timeline_events:
            event_type = event.get("metadata", {}).get("event_type")
            if event_type in high_risk_events:
                base_score += 0.01  # Small increment per high-risk event

        return min(base_score, 1.0)  # Cap at 1.0

    def _extract_timeline_indicators(
        self, timeline_events: List[Dict[str, Any]]
    ) -> List[ThreatIndicator]:
        """Extract threat indicators from timeline events"""
        indicators = []

        # Track unique indicators to avoid duplicates
        seen_indicators = set()

        for event in timeline_events:
            # Extract network indicators
            if "network" in event:
                # DNS queries
                if event.get("metadata", {}).get("event_type") == "NETWORK_DNS":
                    dns_name = (
                        event.get("network", {})
                        .get("dns", {})
                        .get("questions", {})
                        .get("name")
                    )
                    if dns_name and dns_name not in seen_indicators:
                        indicators.append(
                            ThreatIndicator(
                                ioc_value=dns_name,
                                ioc_type=IOCType.DOMAIN,
                                threat_category=ThreatCategory.RECONNAISSANCE,
                                severity=ThreatSeverity.LOW,
                                confidence_score=0.3,
                                source="Asset Timeline Analysis",
                                description=f"Domain queried by asset: {dns_name}",
                                created_at=datetime.utcnow(),
                                last_seen=datetime.utcnow(),
                            )
                        )
                        seen_indicators.add(dns_name)

                # Network connections
                target_ip = event.get("target", {}).get("ip")
                if target_ip and target_ip not in seen_indicators:
                    indicators.append(
                        ThreatIndicator(
                            ioc_value=target_ip,
                            ioc_type=IOCType.IP_ADDRESS,
                            threat_category=ThreatCategory.C2_COMMUNICATION,
                            severity=ThreatSeverity.LOW,
                            confidence_score=0.2,
                            source="Asset Timeline Analysis",
                            description=f"IP contacted by asset: {target_ip}",
                            created_at=datetime.utcnow(),
                            last_seen=datetime.utcnow(),
                        )
                    )
                    seen_indicators.add(target_ip)

        return indicators

    async def _analyze_related_assets(
        self,
        primary_hostname: str,
        timeline_events: List[Dict[str, Any]],
    ) -> List[str]:
        """Analyze assets related to primary asset"""
        related_assets = set()

        # Extract related assets from timeline events
        for event in timeline_events:
            # Assets that communicated with primary asset
            if "principal" in event and "hostname" in event["principal"]:
                hostname = event["principal"]["hostname"]
                if hostname != primary_hostname:
                    related_assets.add(hostname)

            if "target" in event and "hostname" in event["target"]:
                hostname = event["target"]["hostname"]
                if hostname != primary_hostname:
                    related_assets.add(hostname)

        return list(related_assets)[:10]  # Limit to top 10

    def _generate_timeline_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on timeline analysis"""
        recommendations = []

        risk_score = analysis["risk_score"]
        anomalies = analysis["anomalies"]

        if risk_score > 0.7:
            recommendations.append(
                "HIGH RISK: Prioritize detailed investigation of this asset"
            )
            recommendations.append("Consider isolating asset pending investigation")
        elif risk_score > 0.4:
            recommendations.append("MEDIUM RISK: Enhanced monitoring recommended")

        if anomalies:
            high_severity = len([a for a in anomalies if a.get("severity") == "HIGH"])
            if high_severity > 0:
                recommendations.append(
                    f"Address {high_severity} high-severity anomalies immediately"
                )

        if analysis.get("related_assets"):
            recommendations.append("Investigate related assets for lateral movement")

        recommendations.extend(
            [
                "Review antivirus and EDR alerts for this asset",
                "Verify asset compliance with security baselines",
                "Consider additional monitoring for suspicious processes",
            ]
        )

        return recommendations

    # SHIELD Method: DEFEND - Real-time Threat Hunting
    async def _real_time_hunting_loop(self):
        """Background task for continuous threat hunting"""
        self.logger.info("Starting real-time threat hunting loop")

        while True:
            try:
                # Execute scheduled hunting queries
                for query_id, query in self.hunting_queries.items():
                    if not query.enabled or not query.schedule_interval_hours:
                        continue

                    # Check if query should run
                    if (
                        query.last_run is None
                        or datetime.utcnow() - query.last_run
                        >= timedelta(hours=query.schedule_interval_hours)
                    ):
                        try:
                            result = await self.execute_behavioral_hunt(
                                query_id, 1
                            )  # 1 hour window

                            # Alert on high-severity findings
                            if result.severity in [
                                ThreatSeverity.HIGH,
                                ThreatSeverity.CRITICAL,
                            ]:
                                await self._alert_high_severity_finding(result)

                        except Exception as e:
                            self.logger.error(
                                f"Real-time hunt failed for {query_id}: {e}"
                            )

                # Sleep for 5 minutes before next cycle
                await asyncio.sleep(300)

            except Exception as e:
                self.logger.error(f"Error in real-time hunting loop: {e}")
                await asyncio.sleep(300)

    async def _alert_high_severity_finding(self, result: ThreatHuntResult):
        """Alert on high-severity threat hunting findings"""
        self.logger.critical(
            f"HIGH SEVERITY THREAT DETECTED: {result.query_name} - "
            f"{result.severity.value} - {len(result.matched_events)} events"
        )

        # In production, this would integrate with alerting systems
        # such as PagerDuty, Slack, email, etc.

    # Management and Query Methods
    def add_hunting_query(self, query: HuntingQuery):
        """Add custom hunting query"""
        self.hunting_queries[query.query_id] = query
        self.logger.info(f"Added hunting query: {query.name}")

    def get_threat_intelligence_summary(self) -> Dict[str, Any]:
        """Get threat intelligence summary"""
        return {
            "total_indicators": len(self.threat_indicators),
            "indicator_types": {
                ioc_type.value: len(
                    [
                        ind
                        for ind in self.threat_indicators.values()
                        if ind.ioc_type == ioc_type
                    ]
                )
                for ioc_type in IOCType
            },
            "threat_categories": {
                category.value: len(
                    [
                        ind
                        for ind in self.threat_indicators.values()
                        if ind.threat_category == category
                    ]
                )
                for category in ThreatCategory
            },
            "severity_breakdown": {
                severity.value: len(
                    [
                        ind
                        for ind in self.threat_indicators.values()
                        if ind.severity == severity
                    ]
                )
                for severity in ThreatSeverity
            },
        }

    def get_hunting_metrics(self) -> Dict[str, Any]:
        """Get threat hunting metrics"""
        return {
            "total_queries": len(self.hunting_queries),
            "enabled_queries": len(
                [q for q in self.hunting_queries.values() if q.enabled]
            ),
            "total_hunts": len(self.hunt_results),
            "high_severity_results": len(
                [
                    r
                    for r in self.hunt_results.values()
                    if r.severity in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL]
                ]
            ),
            "avg_confidence": sum(r.confidence for r in self.hunt_results.values())
            / len(self.hunt_results)
            if self.hunt_results
            else 0.0,
        }

    def export_threat_indicators(self, format: str = "json") -> str:
        """Export threat indicators in specified format"""
        indicators_data = [
            {
                "ioc_value": ind.ioc_value,
                "ioc_type": ind.ioc_type.value,
                "threat_category": ind.threat_category.value,
                "severity": ind.severity.value,
                "confidence_score": ind.confidence_score,
                "source": ind.source,
                "description": ind.description,
                "created_at": ind.created_at.isoformat() if ind.created_at else None,
                "last_seen": ind.last_seen.isoformat() if ind.last_seen else None,
            }
            for ind in self.threat_indicators.values()
        ]

        if format.lower() == "json":
            return json.dumps(indicators_data, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Factory function for easy instantiation
def create_chronicle_threat_hunting(
    customer_id: str, **kwargs
) -> ChroniclethreatHunting:
    """Create Chronicle Threat Hunting instance"""
    return ChroniclethreatHunting(customer_id=customer_id, **kwargs)
