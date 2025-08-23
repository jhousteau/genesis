"""
Genesis Security Module - SHIELD Methodology Implementation
Comprehensive GCP-native security automation platform

SHIELD Components:
- S (Scan): GCP Security Command Center + Chronicle Threat Hunting
- H (Harden): Cloud Armor + Just-in-Time IAM + Security Policies  
- I (Isolate): VPC Security + Network Segmentation + Resource Isolation
- E (Encrypt): Secret Manager + KMS + End-to-End Encryption
- L (Log): Comprehensive Security Logging + Audit Trails
- D (Defend): Automated Incident Response + Threat Mitigation
"""

# Import existing secret manager components
from ..secrets.manager import SecretManager, SecretMetadata, get_secret_manager
from .chronicle_threat_hunting import (ChronicleAPI, ChroniclethreatHunting,
                                       HuntingQuery, IOCType, ThreatCategory,
                                       ThreatHuntingScope, ThreatHuntResult,
                                       ThreatIndicator,
                                       create_chronicle_threat_hunting)
from .cloud_armor_automation import (AttackEvent, AttackPattern,
                                     CloudArmorAutomation, RuleAction,
                                     SecurityPolicyType, SecurityRule,
                                     ThreatIntelligence,
                                     create_cloud_armor_automation)
from .gcp_security_center import (GCPSecurityCenter, IncidentResponse,
                                  IncidentStatus, SecurityFinding,
                                  ThreatSeverity, create_security_center)
from .incident_response_automation import (ContainmentLevel,
                                           IncidentResponseAutomation,
                                           IsolatedResource, NetworkAction,
                                           ResponseAction, ResponseExecution,
                                           ResponseWorkflow,
                                           create_incident_response_automation)
from .jit_iam_automation import (AccessJustification, AccessPolicy,
                                 AccessRequest, AccessRequestStatus,
                                 ActiveAccess, ElevationLevel,
                                 JITIAMAutomation, create_jit_iam_automation)
from .security_automation_orchestrator import (
    SecurityAutomationLevel, SecurityAutomationOrchestrator, SecurityEvent,
    SecurityEventType, SecurityMetrics,
    create_security_automation_orchestrator)

__all__ = [
    # GCP Security Command Center
    "GCPSecurityCenter",
    "SecurityFinding",
    "ThreatSeverity",
    "IncidentResponse",
    "IncidentStatus",
    "create_security_center",
    # Cloud Armor Automation
    "CloudArmorAutomation",
    "SecurityPolicyType",
    "RuleAction",
    "AttackPattern",
    "SecurityRule",
    "ThreatIntelligence",
    "AttackEvent",
    "create_cloud_armor_automation",
    # Incident Response Automation
    "IncidentResponseAutomation",
    "ResponseAction",
    "ContainmentLevel",
    "NetworkAction",
    "ResponseWorkflow",
    "ResponseExecution",
    "IsolatedResource",
    "create_incident_response_automation",
    # Just-in-Time IAM
    "JITIAMAutomation",
    "AccessRequestStatus",
    "AccessJustification",
    "ElevationLevel",
    "AccessRequest",
    "ActiveAccess",
    "AccessPolicy",
    "create_jit_iam_automation",
    # Chronicle Threat Hunting
    "ChroniclethreatHunting",
    "ThreatHuntingScope",
    "IOCType",
    "ThreatCategory",
    "ThreatIndicator",
    "ThreatHuntResult",
    "HuntingQuery",
    "ChronicleAPI",
    "create_chronicle_threat_hunting",
    # Security Orchestrator
    "SecurityAutomationOrchestrator",
    "SecurityAutomationLevel",
    "SecurityEventType",
    "SecurityMetrics",
    "SecurityEvent",
    "create_security_automation_orchestrator",
    # Secret Manager (existing)
    "SecretManager",
    "SecretMetadata",
    "get_secret_manager",
]


# Version and metadata
__version__ = "1.0.0"
__author__ = "Genesis Security Team"
__description__ = "Comprehensive GCP-native security automation platform implementing SHIELD methodology"


def get_shield_score(security_metrics: SecurityMetrics) -> dict:
    """
    Calculate SHIELD methodology score based on security metrics

    Args:
        security_metrics: Security metrics instance

    Returns:
        Dict containing SHIELD component scores and overall score
    """
    shield_scores = {
        "scan": min(
            (
                security_metrics.threats_detected
                / max(
                    security_metrics.threats_detected
                    + security_metrics.threats_blocked,
                    1,
                )
            )
            * 10,
            10,
        ),
        "harden": min(security_metrics.security_coverage * 10, 10),
        "isolate": min((1 - security_metrics.false_positive_rate) * 10, 10),
        "encrypt": 10.0,  # Assume full encryption implementation
        "log": min(security_metrics.security_coverage * 10, 10),
        "defend": min(security_metrics.automation_effectiveness * 10, 10),
    }

    overall_score = sum(shield_scores.values()) / len(shield_scores)

    return {
        "shield_scores": shield_scores,
        "overall_score": overall_score,
        "grade": _get_security_grade(overall_score),
        "recommendations": _get_shield_recommendations(shield_scores),
    }


def _get_security_grade(score: float) -> str:
    """Get security grade based on SHIELD score"""
    if score >= 9.5:
        return "A+"
    elif score >= 9.0:
        return "A"
    elif score >= 8.5:
        return "A-"
    elif score >= 8.0:
        return "B+"
    elif score >= 7.5:
        return "B"
    elif score >= 7.0:
        return "B-"
    elif score >= 6.5:
        return "C+"
    elif score >= 6.0:
        return "C"
    elif score >= 5.5:
        return "C-"
    else:
        return "D"


def _get_shield_recommendations(shield_scores: dict) -> list:
    """Get SHIELD improvement recommendations"""
    recommendations = []

    for component, score in shield_scores.items():
        if score < 8.0:
            if component == "scan":
                recommendations.append(
                    f"Improve threat detection capabilities (current: {score:.1f}/10)"
                )
            elif component == "harden":
                recommendations.append(
                    f"Enhance security hardening measures (current: {score:.1f}/10)"
                )
            elif component == "isolate":
                recommendations.append(
                    f"Strengthen network isolation and segmentation (current: {score:.1f}/10)"
                )
            elif component == "encrypt":
                recommendations.append(
                    f"Implement comprehensive encryption (current: {score:.1f}/10)"
                )
            elif component == "log":
                recommendations.append(
                    f"Enhance security logging and monitoring (current: {score:.1f}/10)"
                )
            elif component == "defend":
                recommendations.append(
                    f"Improve automated threat response (current: {score:.1f}/10)"
                )

    return recommendations


# Convenience factory function for full security stack
def create_comprehensive_security_platform(
    project_id: str,
    organization_id: str,
    chronicle_customer_id: str = None,
    automation_level: SecurityAutomationLevel = SecurityAutomationLevel.REACTIVE,
    enable_all_components: bool = True,
) -> SecurityAutomationOrchestrator:
    """
    Create comprehensive security platform with all SHIELD components

    Args:
        project_id: GCP project ID
        organization_id: GCP organization ID
        chronicle_customer_id: Chronicle customer ID (optional)
        automation_level: Level of automation
        enable_all_components: Enable all security components

    Returns:
        Fully configured SecurityAutomationOrchestrator
    """
    return SecurityAutomationOrchestrator(
        project_id=project_id,
        organization_id=organization_id,
        chronicle_customer_id=chronicle_customer_id,
        automation_level=automation_level,
        enable_all_components=enable_all_components,
    )


# Configuration helper
def get_shield_configuration(
    automation_level: SecurityAutomationLevel = SecurityAutomationLevel.REACTIVE,
) -> dict:
    """
    Get recommended SHIELD configuration based on automation level

    Args:
        automation_level: Desired automation level

    Returns:
        Configuration dictionary for SHIELD components
    """
    base_config = {
        "security_center": {
            "enable_auto_response": automation_level
            != SecurityAutomationLevel.MONITORING,
            "notification_topic": "security-alerts",
        },
        "cloud_armor": {
            "enable_adaptive_protection": True,
            "enable_auto_scaling": automation_level
            in [SecurityAutomationLevel.PROACTIVE, SecurityAutomationLevel.AUTONOMOUS],
        },
        "incident_response": {
            "enable_auto_rollback": automation_level
            == SecurityAutomationLevel.AUTONOMOUS,
            "max_concurrent_responses": 5,
        },
        "jit_iam": {
            "enable_emergency_access": True,
            "auto_cleanup_expired": True,
        },
        "threat_hunting": {
            "enable_real_time_hunting": automation_level
            in [SecurityAutomationLevel.PROACTIVE, SecurityAutomationLevel.AUTONOMOUS],
            "threat_intel_feeds": [],
        },
    }

    # Adjust configuration based on automation level
    if automation_level == SecurityAutomationLevel.MONITORING:
        # Monitoring only - disable most automated responses
        base_config["incident_response"]["enable_auto_rollback"] = False
        base_config["cloud_armor"]["enable_auto_scaling"] = False

    elif automation_level == SecurityAutomationLevel.AUTONOMOUS:
        # Fully autonomous - enable all automation features
        base_config["incident_response"]["max_concurrent_responses"] = 10
        base_config["cloud_armor"]["enable_auto_scaling"] = True

    return base_config
