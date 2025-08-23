"""
Just-in-Time (JIT) IAM Access Automation
SHIELD Methodology implementation for automated temporary privilege management
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from google.cloud import iam_v1, pubsub_v1, resourcemanager_v1, secretmanager


class AccessRequestStatus(Enum):
    """Access request status"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class AccessJustification(Enum):
    """Access justification reasons"""

    INCIDENT_RESPONSE = "INCIDENT_RESPONSE"
    EMERGENCY_MAINTENANCE = "EMERGENCY_MAINTENANCE"
    SECURITY_INVESTIGATION = "SECURITY_INVESTIGATION"
    COMPLIANCE_AUDIT = "COMPLIANCE_AUDIT"
    BUSINESS_CRITICAL = "BUSINESS_CRITICAL"
    DEVELOPMENT_TESTING = "DEVELOPMENT_TESTING"


class ElevationLevel(Enum):
    """Privilege elevation levels"""

    READ_ONLY = "READ_ONLY"
    LIMITED_WRITE = "LIMITED_WRITE"
    ELEVATED_ACCESS = "ELEVATED_ACCESS"
    ADMIN_ACCESS = "ADMIN_ACCESS"
    EMERGENCY_ACCESS = "EMERGENCY_ACCESS"


@dataclass
class AccessRequest:
    """JIT access request"""

    request_id: str
    requester: str
    target_resource: str
    requested_roles: List[str]
    justification: AccessJustification
    elevation_level: ElevationLevel
    duration_hours: int
    business_reason: str
    status: AccessRequestStatus = AccessRequestStatus.PENDING
    created_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    approver: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ActiveAccess:
    """Active JIT access tracking"""

    access_id: str
    request_id: str
    principal: str
    resource: str
    roles: List[str]
    granted_at: datetime
    expires_at: datetime
    original_bindings: Dict[str, Any] = field(default_factory=dict)
    conditions_applied: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessPolicy:
    """JIT access policy"""

    policy_id: str
    resource_pattern: str
    allowed_roles: List[str]
    max_duration_hours: int
    auto_approval_conditions: Dict[str, Any] = field(default_factory=dict)
    required_approvers: List[str] = field(default_factory=list)
    elevation_restrictions: Dict[ElevationLevel, Dict[str, Any]] = field(
        default_factory=dict
    )
    emergency_break_glass: bool = False


class JITIAMAutomation:
    """
    Just-in-Time IAM Access Automation

    SHIELD Implementation:
    S - Scan: Continuous monitoring of access patterns and privilege usage
    H - Harden: Automated privilege escalation with time-bound controls
    I - Isolate: Conditional access based on context and risk assessment
    E - Encrypt: Secure approval workflows and audit trail encryption
    L - Log: Comprehensive logging of all privilege changes and access events
    D - Defend: Automated revocation and emergency break-glass procedures
    """

    def __init__(
        self,
        project_id: str,
        organization_id: Optional[str] = None,
        approval_topic: Optional[str] = None,
        enable_emergency_access: bool = True,
        auto_cleanup_expired: bool = True,
    ):
        self.project_id = project_id
        self.organization_id = organization_id
        self.approval_topic = approval_topic
        self.enable_emergency_access = enable_emergency_access
        self.auto_cleanup_expired = auto_cleanup_expired

        self.logger = self._setup_logging()

        # Initialize GCP clients
        self.iam_client = iam_v1.IAMClient()
        self.resource_client = resourcemanager_v1.ProjectsClient()
        self.secret_client = secretmanager.SecretManagerServiceClient()

        if approval_topic:
            self.publisher = pubsub_v1.PublisherClient()
            self.subscriber = pubsub_v1.SubscriberClient()

        # Access management state
        self.access_requests: Dict[str, AccessRequest] = {}
        self.active_access: Dict[str, ActiveAccess] = {}
        self.access_policies: Dict[str, AccessPolicy] = {}

        # Approval workflows
        self.approval_handlers: Dict[str, Callable] = {}
        self._register_default_approval_handlers()

        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None

        # Start background processes
        if auto_cleanup_expired:
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_access())

        self.logger.info(f"JIT IAM Automation initialized for project: {project_id}")

    def _setup_logging(self) -> logging.Logger:
        """Setup security-focused logging"""
        logger = logging.getLogger(f"genesis.security.jit.{self.project_id}")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [JIT_IAM] %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def _register_default_approval_handlers(self):
        """Register default approval handlers"""
        self.approval_handlers.update(
            {
                AccessJustification.INCIDENT_RESPONSE.value: self._auto_approve_incident_response,
                AccessJustification.EMERGENCY_MAINTENANCE.value: self._review_emergency_maintenance,
                AccessJustification.SECURITY_INVESTIGATION.value: self._auto_approve_security_investigation,
                AccessJustification.COMPLIANCE_AUDIT.value: self._review_compliance_audit,
                AccessJustification.BUSINESS_CRITICAL.value: self._review_business_critical,
                AccessJustification.DEVELOPMENT_TESTING.value: self._review_development_testing,
            }
        )

    # SHIELD Method: SCAN - Access Pattern Analysis
    async def analyze_access_patterns(
        self,
        time_window_hours: int = 24,
        user_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze JIT access patterns for anomalies and optimization

        Args:
            time_window_hours: Time window for analysis
            user_filter: Filter by specific user

        Returns:
            Access pattern analysis results
        """
        self.logger.info(f"Analyzing access patterns (last {time_window_hours}h)")

        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)

        # Filter recent requests
        recent_requests = [
            req
            for req in self.access_requests.values()
            if req.created_at
            and req.created_at >= cutoff_time
            and (not user_filter or req.requester == user_filter)
        ]

        analysis = {
            "time_window_hours": time_window_hours,
            "total_requests": len(recent_requests),
            "approval_metrics": {},
            "access_patterns": {},
            "anomalies": [],
            "recommendations": [],
            "user_activity": {},
            "resource_access": {},
        }

        # Analyze approval metrics
        status_counts = {}
        justification_counts = {}

        for request in recent_requests:
            status = request.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

            justification = request.justification.value
            justification_counts[justification] = (
                justification_counts.get(justification, 0) + 1
            )

            # Track user activity
            user = request.requester
            if user not in analysis["user_activity"]:
                analysis["user_activity"][user] = {
                    "total_requests": 0,
                    "approved": 0,
                    "denied": 0,
                    "resources_accessed": set(),
                }

            analysis["user_activity"][user]["total_requests"] += 1
            if request.status == AccessRequestStatus.APPROVED:
                analysis["user_activity"][user]["approved"] += 1
            elif request.status == AccessRequestStatus.DENIED:
                analysis["user_activity"][user]["denied"] += 1

            analysis["user_activity"][user]["resources_accessed"].add(
                request.target_resource
            )

            # Track resource access
            resource = request.target_resource
            analysis["resource_access"][resource] = (
                analysis["resource_access"].get(resource, 0) + 1
            )

        analysis["approval_metrics"] = {
            "status_breakdown": status_counts,
            "justification_breakdown": justification_counts,
            "approval_rate": (
                status_counts.get("APPROVED", 0) / len(recent_requests) * 100
                if recent_requests
                else 0
            ),
        }

        # Convert sets to lists for JSON serialization
        for user_data in analysis["user_activity"].values():
            user_data["resources_accessed"] = list(user_data["resources_accessed"])

        # Detect anomalies
        await self._detect_access_anomalies(analysis, recent_requests)

        # Generate recommendations
        await self._generate_access_recommendations(analysis)

        self.logger.info(
            f"Access pattern analysis completed: {len(recent_requests)} requests analyzed"
        )

        return analysis

    async def _detect_access_anomalies(
        self,
        analysis: Dict[str, Any],
        requests: List[AccessRequest],
    ):
        """Detect access pattern anomalies"""
        anomalies = []

        # Detect unusual access patterns
        for user, data in analysis["user_activity"].items():
            if data["total_requests"] > 10:  # High volume user
                anomalies.append(
                    {
                        "type": "high_request_volume",
                        "user": user,
                        "count": data["total_requests"],
                        "severity": "MEDIUM",
                        "description": f"User {user} made {data['total_requests']} requests",
                    }
                )

            if len(data["resources_accessed"]) > 5:  # Accessing many resources
                anomalies.append(
                    {
                        "type": "broad_resource_access",
                        "user": user,
                        "resource_count": len(data["resources_accessed"]),
                        "severity": "MEDIUM",
                        "description": f"User {user} accessed {len(data['resources_accessed'])} different resources",
                    }
                )

        # Detect unusual time patterns
        request_hours = [req.created_at.hour for req in requests if req.created_at]
        off_hours_requests = len([h for h in request_hours if h < 6 or h > 22])

        if off_hours_requests > len(requests) * 0.3:  # More than 30% off-hours
            anomalies.append(
                {
                    "type": "off_hours_access_pattern",
                    "count": off_hours_requests,
                    "percentage": off_hours_requests / len(requests) * 100,
                    "severity": "HIGH",
                    "description": f"High percentage of off-hours access requests ({off_hours_requests})",
                }
            )

        analysis["anomalies"] = anomalies

    async def _generate_access_recommendations(self, analysis: Dict[str, Any]):
        """Generate access optimization recommendations"""
        recommendations = []

        approval_rate = analysis["approval_metrics"]["approval_rate"]

        if approval_rate < 70:
            recommendations.append(
                "Low approval rate detected - review access policies and training"
            )
        elif approval_rate > 95:
            recommendations.append(
                "Very high approval rate - consider streamlining approval processes"
            )

        if analysis["anomalies"]:
            high_severity_anomalies = [
                a for a in analysis["anomalies"] if a["severity"] == "HIGH"
            ]
            if high_severity_anomalies:
                recommendations.append(
                    f"Address {len(high_severity_anomalies)} high-severity access anomalies"
                )

        # Resource-specific recommendations
        most_accessed = max(
            analysis["resource_access"].items(), key=lambda x: x[1], default=("", 0)
        )

        if most_accessed[1] > len(analysis["user_activity"]) * 0.5:
            recommendations.append(
                f"Consider permanent access policies for highly accessed resource: {most_accessed[0]}"
            )

        analysis["recommendations"] = recommendations

    # SHIELD Method: HARDEN - Access Request Processing
    async def request_access(
        self,
        requester: str,
        target_resource: str,
        requested_roles: List[str],
        justification: AccessJustification,
        duration_hours: int,
        business_reason: str,
        elevation_level: ElevationLevel = ElevationLevel.READ_ONLY,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Request JIT access with automated approval workflow

        Args:
            requester: User requesting access
            target_resource: Target resource for access
            requested_roles: List of IAM roles requested
            justification: Business justification
            duration_hours: Access duration in hours
            business_reason: Detailed business reason
            elevation_level: Level of privilege elevation
            conditions: Additional access conditions

        Returns:
            Request ID
        """
        request_id = f"jit-{int(time.time())}-{hash(requester) % 10000}"

        self.logger.info(f"Processing access request: {request_id} from {requester}")

        # Validate request
        await self._validate_access_request(
            requester, target_resource, requested_roles, duration_hours, elevation_level
        )

        # Create access request
        request = AccessRequest(
            request_id=request_id,
            requester=requester,
            target_resource=target_resource,
            requested_roles=requested_roles,
            justification=justification,
            elevation_level=elevation_level,
            duration_hours=duration_hours,
            business_reason=business_reason,
            created_at=datetime.utcnow(),
            conditions=conditions or {},
        )

        # Add to audit trail
        request.audit_trail.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "REQUEST_CREATED",
                "actor": requester,
                "details": {
                    "resource": target_resource,
                    "roles": requested_roles,
                    "duration_hours": duration_hours,
                    "justification": justification.value,
                },
            }
        )

        self.access_requests[request_id] = request

        # Process approval workflow
        await self._process_approval_workflow(request)

        self.logger.info(f"Access request processed: {request_id}")

        return request_id

    async def _validate_access_request(
        self,
        requester: str,
        target_resource: str,
        requested_roles: List[str],
        duration_hours: int,
        elevation_level: ElevationLevel,
    ):
        """Validate access request parameters"""

        # Check if requester has permission to request access
        # Implementation would verify the requester's identity and base permissions

        # Validate duration
        max_duration = self._get_max_duration_for_elevation(elevation_level)
        if duration_hours > max_duration:
            raise ValueError(
                f"Requested duration {duration_hours}h exceeds maximum {max_duration}h for {elevation_level.value}"
            )

        # Validate roles against resource policies
        applicable_policy = self._find_applicable_policy(target_resource)
        if applicable_policy:
            invalid_roles = set(requested_roles) - set(applicable_policy.allowed_roles)
            if invalid_roles:
                raise ValueError(f"Invalid roles for resource: {invalid_roles}")

        self.logger.debug(
            f"Access request validation passed for requester: {requester}"
        )

    def _get_max_duration_for_elevation(self, elevation_level: ElevationLevel) -> int:
        """Get maximum duration for elevation level"""
        duration_limits = {
            ElevationLevel.READ_ONLY: 24,
            ElevationLevel.LIMITED_WRITE: 8,
            ElevationLevel.ELEVATED_ACCESS: 4,
            ElevationLevel.ADMIN_ACCESS: 2,
            ElevationLevel.EMERGENCY_ACCESS: 1,
        }
        return duration_limits.get(elevation_level, 1)

    def _find_applicable_policy(self, resource: str) -> Optional[AccessPolicy]:
        """Find applicable access policy for resource"""
        for policy in self.access_policies.values():
            if resource.startswith(policy.resource_pattern.rstrip("*")):
                return policy
        return None

    async def _process_approval_workflow(self, request: AccessRequest):
        """Process approval workflow for access request"""
        self.logger.info(f"Processing approval workflow for: {request.request_id}")

        # Check for auto-approval conditions
        handler = self.approval_handlers.get(request.justification.value)
        if handler:
            try:
                approved = await handler(request)
                if approved:
                    await self._approve_access_request(
                        request.request_id, "SYSTEM_AUTO_APPROVAL"
                    )
                    return
            except Exception as e:
                self.logger.error(f"Auto-approval handler failed: {e}")

        # Check policy-based auto-approval
        applicable_policy = self._find_applicable_policy(request.target_resource)
        if applicable_policy and self._meets_auto_approval_conditions(
            request, applicable_policy
        ):
            await self._approve_access_request(
                request.request_id, "POLICY_AUTO_APPROVAL"
            )
            return

        # Send for manual approval
        await self._send_for_manual_approval(request)

    async def _auto_approve_incident_response(self, request: AccessRequest) -> bool:
        """Auto-approve incident response requests"""
        # Auto-approve if:
        # - Duration <= 4 hours
        # - Elevation level <= ELEVATED_ACCESS
        # - During business hours or marked as emergency

        if request.duration_hours <= 4 and request.elevation_level.value in [
            ElevationLevel.READ_ONLY.value,
            ElevationLevel.LIMITED_WRITE.value,
            ElevationLevel.ELEVATED_ACCESS.value,
        ]:
            self.logger.info(
                f"Auto-approving incident response request: {request.request_id}"
            )
            return True

        return False

    async def _auto_approve_security_investigation(
        self, request: AccessRequest
    ) -> bool:
        """Auto-approve security investigation requests"""
        # Auto-approve read-only security investigation requests
        if (
            request.elevation_level == ElevationLevel.READ_ONLY
            and request.duration_hours <= 8
        ):
            self.logger.info(
                f"Auto-approving security investigation request: {request.request_id}"
            )
            return True

        return False

    async def _review_emergency_maintenance(self, request: AccessRequest) -> bool:
        """Review emergency maintenance requests"""
        # Emergency maintenance requires manual approval unless it's truly critical
        self.logger.info(
            f"Emergency maintenance request requires review: {request.request_id}"
        )
        return False

    async def _review_compliance_audit(self, request: AccessRequest) -> bool:
        """Review compliance audit requests"""
        # Compliance audits are typically read-only and can be auto-approved
        if request.elevation_level == ElevationLevel.READ_ONLY:
            return True
        return False

    async def _review_business_critical(self, request: AccessRequest) -> bool:
        """Review business critical requests"""
        return False  # Always require manual approval

    async def _review_development_testing(self, request: AccessRequest) -> bool:
        """Review development testing requests"""
        # Auto-approve development testing in non-production resources
        if (
            "dev" in request.target_resource.lower()
            or "test" in request.target_resource.lower()
        ):
            return True
        return False

    def _meets_auto_approval_conditions(
        self,
        request: AccessRequest,
        policy: AccessPolicy,
    ) -> bool:
        """Check if request meets policy auto-approval conditions"""
        auto_conditions = policy.auto_approval_conditions

        if not auto_conditions:
            return False

        # Check duration limit
        if request.duration_hours > auto_conditions.get("max_duration_hours", 0):
            return False

        # Check elevation level
        allowed_elevations = auto_conditions.get("allowed_elevation_levels", [])
        if request.elevation_level.value not in allowed_elevations:
            return False

        # Check time restrictions
        current_hour = datetime.utcnow().hour
        business_hours = auto_conditions.get("business_hours_only", False)
        if business_hours and (current_hour < 8 or current_hour > 18):
            return False

        return True

    async def _send_for_manual_approval(self, request: AccessRequest):
        """Send request for manual approval"""
        self.logger.info(f"Sending request for manual approval: {request.request_id}")

        if not self.approval_topic:
            self.logger.warning(
                "No approval topic configured - request will remain pending"
            )
            return

        # Send approval notification
        approval_message = {
            "request_id": request.request_id,
            "requester": request.requester,
            "target_resource": request.target_resource,
            "requested_roles": request.requested_roles,
            "justification": request.justification.value,
            "duration_hours": request.duration_hours,
            "business_reason": request.business_reason,
            "elevation_level": request.elevation_level.value,
            "created_at": request.created_at.isoformat(),
        }

        try:
            topic_path = self.publisher.topic_path(self.project_id, self.approval_topic)
            message_data = json.dumps(approval_message).encode("utf-8")

            future = self.publisher.publish(topic_path, message_data)
            future.result()

            self.logger.info(f"Approval notification sent for: {request.request_id}")

        except Exception as e:
            self.logger.error(f"Failed to send approval notification: {e}")

    # SHIELD Method: ISOLATE - Conditional Access Controls
    async def approve_access_request(
        self,
        request_id: str,
        approver: str,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Approve access request and grant JIT access

        Args:
            request_id: Access request ID
            approver: Approver identity
            conditions: Additional access conditions

        Returns:
            True if successfully approved and granted
        """
        return await self._approve_access_request(request_id, approver, conditions)

    async def _approve_access_request(
        self,
        request_id: str,
        approver: str,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Internal approve access request method"""
        if request_id not in self.access_requests:
            raise ValueError(f"Access request not found: {request_id}")

        request = self.access_requests[request_id]

        if request.status != AccessRequestStatus.PENDING:
            raise ValueError(
                f"Request {request_id} is not in pending status: {request.status}"
            )

        self.logger.info(f"Approving access request: {request_id} by {approver}")

        # Update request status
        request.status = AccessRequestStatus.APPROVED
        request.approved_at = datetime.utcnow()
        request.expires_at = datetime.utcnow() + timedelta(hours=request.duration_hours)
        request.approver = approver

        if conditions:
            request.conditions.update(conditions)

        # Add to audit trail
        request.audit_trail.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "REQUEST_APPROVED",
                "actor": approver,
                "details": {
                    "conditions": conditions or {},
                },
            }
        )

        # Grant JIT access
        success = await self._grant_jit_access(request)

        if success:
            request.status = AccessRequestStatus.ACTIVE
            self.logger.info(f"JIT access granted for request: {request_id}")
        else:
            request.status = AccessRequestStatus.DENIED  # Grant failed
            self.logger.error(f"Failed to grant JIT access for request: {request_id}")

        return success

    async def _grant_jit_access(self, request: AccessRequest) -> bool:
        """Grant JIT access by modifying IAM policies"""
        access_id = f"jit-access-{request.request_id}"

        try:
            # Get current IAM policy for resource
            current_policy = await self._get_current_iam_policy(request.target_resource)

            # Store original bindings for rollback
            original_bindings = json.loads(json.dumps(current_policy, default=str))

            # Add temporary IAM bindings with conditions
            updated_policy = await self._add_conditional_iam_bindings(
                current_policy, request
            )

            # Apply updated policy
            await self._set_iam_policy(request.target_resource, updated_policy)

            # Track active access
            active_access = ActiveAccess(
                access_id=access_id,
                request_id=request.request_id,
                principal=f"user:{request.requester}",
                resource=request.target_resource,
                roles=request.requested_roles,
                granted_at=datetime.utcnow(),
                expires_at=request.expires_at,
                original_bindings=original_bindings,
                conditions_applied=request.conditions,
            )

            self.active_access[access_id] = active_access

            self.logger.info(f"JIT access granted: {access_id}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to grant JIT access: {e}")
            return False

    async def _get_current_iam_policy(self, resource: str) -> Dict[str, Any]:
        """Get current IAM policy for resource"""
        # Implementation would use appropriate GCP IAM client
        # to retrieve the current policy for the resource

        # Placeholder implementation
        return {
            "bindings": [],
            "version": 1,
        }

    async def _add_conditional_iam_bindings(
        self,
        policy: Dict[str, Any],
        request: AccessRequest,
    ) -> Dict[str, Any]:
        """Add conditional IAM bindings to policy"""

        # Create time-based condition
        condition_expression = (
            f'request.time < timestamp("{request.expires_at.isoformat()}Z")'
        )

        # Add additional conditions
        if "source_ips" in request.conditions:
            ip_condition = " || ".join(
                [f'origin.ip == "{ip}"' for ip in request.conditions["source_ips"]]
            )
            condition_expression += f" && ({ip_condition})"

        if "time_window" in request.conditions:
            time_window = request.conditions["time_window"]
            time_condition = f'request.time.getHours() >= {time_window["start"]} && request.time.getHours() <= {time_window["end"]}'
            condition_expression += f" && ({time_condition})"

        # Add bindings for each requested role
        for role in request.requested_roles:
            binding = {
                "role": role,
                "members": [f"user:{request.requester}"],
                "condition": {
                    "title": f"JIT Access - {request.request_id}",
                    "description": f"Temporary access until {request.expires_at.isoformat()}",
                    "expression": condition_expression,
                },
            }

            policy["bindings"].append(binding)

        return policy

    async def _set_iam_policy(self, resource: str, policy: Dict[str, Any]):
        """Set IAM policy for resource"""
        # Implementation would use appropriate GCP IAM client
        # to set the IAM policy for the resource

        self.logger.debug(f"Setting IAM policy for resource: {resource}")

    # SHIELD Method: DEFEND - Access Revocation and Cleanup
    async def revoke_access(
        self,
        access_id: Optional[str] = None,
        request_id: Optional[str] = None,
        requester: Optional[str] = None,
    ) -> bool:
        """
        Revoke JIT access

        Args:
            access_id: Specific access ID to revoke
            request_id: Request ID to revoke
            requester: Revoke all access for requester

        Returns:
            True if successfully revoked
        """
        revoked_count = 0

        # Find access records to revoke
        access_to_revoke = []

        if access_id:
            if access_id in self.active_access:
                access_to_revoke.append(self.active_access[access_id])
        elif request_id:
            access_to_revoke.extend(
                [
                    access
                    for access in self.active_access.values()
                    if access.request_id == request_id
                ]
            )
        elif requester:
            access_to_revoke.extend(
                [
                    access
                    for access in self.active_access.values()
                    if access.principal == f"user:{requester}"
                ]
            )

        # Revoke each access
        for access in access_to_revoke:
            try:
                await self._revoke_individual_access(access)
                revoked_count += 1
            except Exception as e:
                self.logger.error(f"Failed to revoke access {access.access_id}: {e}")

        self.logger.info(f"Revoked {revoked_count} JIT access grants")

        return revoked_count > 0

    async def _revoke_individual_access(self, access: ActiveAccess):
        """Revoke individual JIT access"""
        self.logger.info(f"Revoking JIT access: {access.access_id}")

        try:
            # Restore original IAM policy
            await self._set_iam_policy(access.resource, access.original_bindings)

            # Remove from active access tracking
            if access.access_id in self.active_access:
                del self.active_access[access.access_id]

            # Update request status
            if access.request_id in self.access_requests:
                request = self.access_requests[access.request_id]
                request.status = AccessRequestStatus.REVOKED

                # Add to audit trail
                request.audit_trail.append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "action": "ACCESS_REVOKED",
                        "actor": "SYSTEM",
                        "details": {
                            "access_id": access.access_id,
                            "reason": "Manual revocation",
                        },
                    }
                )

            self.logger.info(f"JIT access revoked: {access.access_id}")

        except Exception as e:
            self.logger.error(f"Failed to revoke JIT access {access.access_id}: {e}")
            raise

    async def _cleanup_expired_access(self):
        """Background task to cleanup expired access"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                current_time = datetime.utcnow()
                expired_access = [
                    access
                    for access in self.active_access.values()
                    if access.expires_at <= current_time
                ]

                for access in expired_access:
                    try:
                        await self._revoke_individual_access(access)

                        # Update request status to expired
                        if access.request_id in self.access_requests:
                            request = self.access_requests[access.request_id]
                            request.status = AccessRequestStatus.EXPIRED

                            request.audit_trail.append(
                                {
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "action": "ACCESS_EXPIRED",
                                    "actor": "SYSTEM",
                                    "details": {
                                        "access_id": access.access_id,
                                    },
                                }
                            )

                    except Exception as e:
                        self.logger.error(
                            f"Failed to cleanup expired access {access.access_id}: {e}"
                        )

                if expired_access:
                    self.logger.info(
                        f"Cleaned up {len(expired_access)} expired JIT access grants"
                    )

            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)

    # Management and Query Methods
    def get_active_access_summary(self) -> Dict[str, Any]:
        """Get summary of active JIT access"""
        active_count = len(self.active_access)

        # Group by resource
        resource_counts = {}
        user_counts = {}

        for access in self.active_access.values():
            resource = access.resource
            user = access.principal.replace("user:", "")

            resource_counts[resource] = resource_counts.get(resource, 0) + 1
            user_counts[user] = user_counts.get(user, 0) + 1

        return {
            "total_active_access": active_count,
            "resource_breakdown": resource_counts,
            "user_breakdown": user_counts,
            "expiring_soon": len(
                [
                    access
                    for access in self.active_access.values()
                    if access.expires_at <= datetime.utcnow() + timedelta(hours=1)
                ]
            ),
        }

    def get_request_metrics(self) -> Dict[str, Any]:
        """Get access request metrics"""
        total_requests = len(self.access_requests)

        status_counts = {}
        justification_counts = {}

        for request in self.access_requests.values():
            status = request.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

            justification = request.justification.value
            justification_counts[justification] = (
                justification_counts.get(justification, 0) + 1
            )

        return {
            "total_requests": total_requests,
            "status_breakdown": status_counts,
            "justification_breakdown": justification_counts,
            "approval_rate": (
                status_counts.get("APPROVED", 0) / total_requests * 100
                if total_requests > 0
                else 0
            ),
        }

    def add_access_policy(self, policy: AccessPolicy):
        """Add JIT access policy"""
        self.access_policies[policy.policy_id] = policy
        self.logger.info(f"Added JIT access policy: {policy.policy_id}")

    def register_approval_handler(self, justification: str, handler: Callable):
        """Register custom approval handler"""
        self.approval_handlers[justification] = handler
        self.logger.info(f"Registered approval handler for: {justification}")

    async def deny_access_request(
        self,
        request_id: str,
        denier: str,
        reason: str,
    ) -> bool:
        """Deny access request"""
        if request_id not in self.access_requests:
            raise ValueError(f"Access request not found: {request_id}")

        request = self.access_requests[request_id]

        if request.status != AccessRequestStatus.PENDING:
            raise ValueError(f"Request {request_id} is not in pending status")

        request.status = AccessRequestStatus.DENIED

        # Add to audit trail
        request.audit_trail.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "REQUEST_DENIED",
                "actor": denier,
                "details": {
                    "reason": reason,
                },
            }
        )

        self.logger.info(f"Access request denied: {request_id} by {denier}")

        return True


# Factory function for easy instantiation
def create_jit_iam_automation(project_id: str, **kwargs) -> JITIAMAutomation:
    """Create JIT IAM Automation instance"""
    return JITIAMAutomation(project_id=project_id, **kwargs)
