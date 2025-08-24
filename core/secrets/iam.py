"""
Genesis Secret Management - IAM Integration
SHIELD Methodology: Isolate component for IAM-based secret access controls

Provides comprehensive IAM integration for secure secret access patterns.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from google.cloud import iam_v1, resourcemanager_v3
from google.cloud.exceptions import GoogleCloudError

from .exceptions import SecretAccessDeniedError, SecretConfigurationError, SecretError


class IAMRole(Enum):
    """IAM roles for secret access"""

    SECRET_VIEWER = "roles/secretmanager.viewer"
    SECRET_ACCESSOR = "roles/secretmanager.secretAccessor"
    SECRET_VERSION_ADDER = "roles/secretmanager.secretVersionAdder"
    SECRET_VERSION_MANAGER = "roles/secretmanager.secretVersionManager"
    SECRET_ADMIN = "roles/secretmanager.admin"


class AccessScope(Enum):
    """Access scope for secrets"""

    PROJECT = "project"
    SECRET = "secret"
    VERSION = "version"


@dataclass
class IAMBinding:
    """IAM binding configuration"""

    role: IAMRole
    members: List[str]
    condition: Optional[Dict[str, Any]] = None
    scope: AccessScope = AccessScope.SECRET


@dataclass
class AccessRequest:
    """Request for secret access"""

    secret_name: str
    user_identity: str
    service_account: Optional[str] = None
    requested_at: datetime = field(default_factory=datetime.utcnow)
    justification: Optional[str] = None
    temporary: bool = False
    duration_hours: int = 24


class IAMSecretAccessManager:
    """
    IAM-based secret access management with fine-grained controls

    Implements SHIELD I (Isolate) methodology for secret access:
    - Role-based access control (RBAC)
    - Service account impersonation
    - Temporary access grants
    - Access audit trails
    - Just-in-time (JIT) access
    """

    def __init__(self, project_id: str, enable_jit_access: bool = True):
        self.project_id = project_id
        self.enable_jit_access = enable_jit_access
        self.logger = logging.getLogger("genesis.secrets.iam")

        # Initialize GCP clients
        try:
            self.iam_client = iam_v1.IAMPolicyClient()
            self.resource_client = resourcemanager_v3.ProjectsClient()
        except Exception as e:
            raise SecretConfigurationError(f"Failed to initialize IAM clients: {e}")

        # Access tracking
        self._access_grants: Dict[str, AccessRequest] = {}
        self._temporary_grants: Dict[str, datetime] = {}  # grant_id -> expires_at
        self._lock = threading.RLock()

        # Default IAM policies
        self._default_policies = self._load_default_policies()

        self.logger.info(
            f"IAMSecretAccessManager initialized for project: {project_id}"
        )

    def _load_default_policies(self) -> Dict[str, List[IAMBinding]]:
        """Load default IAM policies for different environments"""
        return {
            "production": [
                IAMBinding(
                    role=IAMRole.SECRET_ACCESSOR,
                    members=[
                        "serviceAccount:prod-service@{project}.iam.gserviceaccount.com".format(
                            project=self.project_id
                        )
                    ],
                    scope=AccessScope.SECRET,
                ),
            ],
            "staging": [
                IAMBinding(
                    role=IAMRole.SECRET_ACCESSOR,
                    members=[
                        "serviceAccount:staging-service@{project}.iam.gserviceaccount.com".format(
                            project=self.project_id
                        ),
                        "group:staging-developers@example.com",
                    ],
                    scope=AccessScope.SECRET,
                ),
            ],
            "development": [
                IAMBinding(
                    role=IAMRole.SECRET_VERSION_MANAGER,
                    members=[
                        "group:developers@example.com",
                        "serviceAccount:dev-service@{project}.iam.gserviceaccount.com".format(
                            project=self.project_id
                        ),
                    ],
                    scope=AccessScope.SECRET,
                ),
            ],
        }

    def create_secret_iam_policy(
        self,
        secret_name: str,
        bindings: List[IAMBinding],
        environment: str = "development",
    ) -> bool:
        """
        Create IAM policy for a secret with specified bindings

        Args:
            secret_name: Name of the secret
            bindings: List of IAM bindings to apply
            environment: Environment context for policy application

        Returns:
            True if policy was created successfully
        """
        with self._lock:
            self.logger.info(f"Creating IAM policy for secret: {secret_name}")

            try:
                # Get current policy
                resource_name = f"projects/{self.project_id}/secrets/{secret_name}"

                # Build new policy
                policy = iam_v1.Policy()

                for binding in bindings:
                    iam_binding = iam_v1.Binding(
                        role=binding.role.value,
                        members=binding.members,
                    )

                    # Add conditional access if specified
                    if binding.condition:
                        condition = iam_v1.Expr(
                            title=binding.condition.get("title", "Access condition"),
                            description=binding.condition.get("description", ""),
                            expression=binding.condition.get("expression", ""),
                        )
                        iam_binding.condition = condition

                    policy.bindings.append(iam_binding)

                # Apply policy
                request = iam_v1.SetIamPolicyRequest(
                    resource=resource_name,
                    policy=policy,
                )

                result_policy = self.iam_client.set_iam_policy(request=request)

                self.logger.info(
                    f"IAM policy created for secret {secret_name} with {len(bindings)} bindings"
                )

                return True

            except GoogleCloudError as e:
                error_msg = f"Failed to create IAM policy for secret {secret_name}: {e}"
                self.logger.error(error_msg)
                raise SecretError(error_msg)

    def check_secret_access(
        self,
        secret_name: str,
        user_identity: str,
        required_permission: str = "secretmanager.versions.access",
    ) -> bool:
        """
        Check if user has access to a secret

        Args:
            secret_name: Name of the secret
            user_identity: User or service account identity
            required_permission: Required permission for access

        Returns:
            True if access is allowed
        """
        try:
            resource_name = f"projects/{self.project_id}/secrets/{secret_name}"

            # Test IAM permissions
            request = iam_v1.TestIamPermissionsRequest(
                resource=resource_name,
                permissions=[required_permission],
            )

            response = self.iam_client.test_iam_permissions(request=request)

            has_permission = required_permission in response.permissions

            self.logger.info(
                f"Access check for {user_identity} on secret {secret_name}: {'ALLOWED' if has_permission else 'DENIED'}"
            )

            return has_permission

        except GoogleCloudError as e:
            self.logger.error(f"Failed to check secret access: {e}")
            return False

    def request_temporary_access(
        self,
        access_request: AccessRequest,
        approver_identity: Optional[str] = None,
    ) -> str:
        """
        Request temporary access to a secret (JIT access)

        Args:
            access_request: Details of the access request
            approver_identity: Identity of the approver (if required)

        Returns:
            Grant ID for the temporary access
        """
        if not self.enable_jit_access:
            raise SecretError("Just-in-time access is disabled")

        with self._lock:
            grant_id = f"grant_{access_request.secret_name}_{int(datetime.utcnow().timestamp())}"

            self.logger.info(
                f"Processing temporary access request: {grant_id} for secret {access_request.secret_name}"
            )

            try:
                # Validate request
                if not self._validate_access_request(access_request):
                    raise SecretAccessDeniedError(
                        access_request.secret_name, "Access request validation failed"
                    )

                # Create temporary IAM binding
                expires_at = access_request.requested_at + timedelta(
                    hours=access_request.duration_hours
                )

                # Build time-limited condition
                condition = {
                    "title": f"Temporary access for {access_request.user_identity}",
                    "description": f"Access expires at {expires_at.isoformat()}",
                    "expression": f"request.time < timestamp('{expires_at.isoformat()}Z')",
                }

                # Create temporary binding
                temp_binding = IAMBinding(
                    role=IAMRole.SECRET_ACCESSOR,
                    members=[access_request.user_identity],
                    condition=condition,
                )

                # Apply temporary policy
                success = self.create_secret_iam_policy(
                    access_request.secret_name,
                    [temp_binding],
                )

                if success:
                    # Track the grant
                    self._access_grants[grant_id] = access_request
                    self._temporary_grants[grant_id] = expires_at

                    self.logger.info(
                        f"Temporary access granted: {grant_id} expires at {expires_at}"
                    )

                    return grant_id
                else:
                    raise SecretError("Failed to apply temporary access policy")

            except Exception as e:
                error_msg = f"Failed to grant temporary access: {e}"
                self.logger.error(error_msg)
                raise SecretError(error_msg)

    def revoke_temporary_access(self, grant_id: str) -> bool:
        """
        Revoke temporary access grant

        Args:
            grant_id: ID of the grant to revoke

        Returns:
            True if access was revoked successfully
        """
        with self._lock:
            if grant_id not in self._access_grants:
                self.logger.warning(f"Grant ID {grant_id} not found")
                return False

            access_request = self._access_grants[grant_id]

            self.logger.info(
                f"Revoking temporary access: {grant_id} for secret {access_request.secret_name}"
            )

            try:
                # Remove the temporary binding by getting current policy and filtering out the temporary one
                resource_name = (
                    f"projects/{self.project_id}/secrets/{access_request.secret_name}"
                )

                # Get current policy
                request = iam_v1.GetIamPolicyRequest(resource=resource_name)
                current_policy = self.iam_client.get_iam_policy(request=request)

                # Filter out the temporary binding
                filtered_bindings = []
                for binding in current_policy.bindings:
                    # Skip bindings that match our temporary grant
                    if (
                        binding.condition
                        and f"Temporary access for {access_request.user_identity}"
                        in binding.condition.title
                    ):
                        continue
                    filtered_bindings.append(binding)

                # Update policy
                current_policy.bindings[:] = filtered_bindings

                set_request = iam_v1.SetIamPolicyRequest(
                    resource=resource_name,
                    policy=current_policy,
                )

                self.iam_client.set_iam_policy(request=set_request)

                # Clean up tracking
                del self._access_grants[grant_id]
                if grant_id in self._temporary_grants:
                    del self._temporary_grants[grant_id]

                self.logger.info(f"Temporary access revoked: {grant_id}")
                return True

            except GoogleCloudError as e:
                error_msg = f"Failed to revoke temporary access {grant_id}: {e}"
                self.logger.error(error_msg)
                raise SecretError(error_msg)

    def cleanup_expired_grants(self) -> int:
        """
        Clean up expired temporary access grants

        Returns:
            Number of grants cleaned up
        """
        with self._lock:
            now = datetime.utcnow()
            expired_grants = [
                grant_id
                for grant_id, expires_at in self._temporary_grants.items()
                if now > expires_at
            ]

            cleaned_up = 0
            for grant_id in expired_grants:
                try:
                    if self.revoke_temporary_access(grant_id):
                        cleaned_up += 1
                except Exception as e:
                    self.logger.error(
                        f"Failed to cleanup expired grant {grant_id}: {e}"
                    )

            if cleaned_up > 0:
                self.logger.info(f"Cleaned up {cleaned_up} expired access grants")

            return cleaned_up

    def get_secret_iam_policy(self, secret_name: str) -> Dict[str, Any]:
        """
        Get current IAM policy for a secret

        Args:
            secret_name: Name of the secret

        Returns:
            Dictionary representation of the IAM policy
        """
        try:
            resource_name = f"projects/{self.project_id}/secrets/{secret_name}"
            request = iam_v1.GetIamPolicyRequest(resource=resource_name)
            policy = self.iam_client.get_iam_policy(request=request)

            # Convert to dictionary
            policy_dict = {
                "bindings": [],
                "etag": policy.etag,
                "version": policy.version,
            }

            for binding in policy.bindings:
                binding_dict = {
                    "role": binding.role,
                    "members": list(binding.members),
                }

                if binding.condition:
                    binding_dict["condition"] = {
                        "title": binding.condition.title,
                        "description": binding.condition.description,
                        "expression": binding.condition.expression,
                    }

                policy_dict["bindings"].append(binding_dict)

            return policy_dict

        except GoogleCloudError as e:
            error_msg = f"Failed to get IAM policy for secret {secret_name}: {e}"
            self.logger.error(error_msg)
            raise SecretError(error_msg)

    def audit_secret_access(
        self,
        secret_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Audit secret access using Cloud Logging

        Args:
            secret_name: Filter by specific secret (optional)
            start_time: Start time for audit period
            end_time: End time for audit period

        Returns:
            List of audit log entries
        """
        # This would integrate with Cloud Logging to retrieve audit logs
        # For now, return the tracked access grants
        with self._lock:
            audit_entries = []

            for grant_id, access_request in self._access_grants.items():
                # Apply filters
                if secret_name and access_request.secret_name != secret_name:
                    continue

                if start_time and access_request.requested_at < start_time:
                    continue

                if end_time and access_request.requested_at > end_time:
                    continue

                entry = {
                    "grant_id": grant_id,
                    "secret_name": access_request.secret_name,
                    "user_identity": access_request.user_identity,
                    "service_account": access_request.service_account,
                    "requested_at": access_request.requested_at.isoformat(),
                    "justification": access_request.justification,
                    "temporary": access_request.temporary,
                    "duration_hours": access_request.duration_hours,
                    "expires_at": (
                        self._temporary_grants.get(grant_id, "").isoformat()
                        if isinstance(self._temporary_grants.get(grant_id), datetime)
                        else None
                    ),
                }

                audit_entries.append(entry)

            return audit_entries

    def _validate_access_request(self, access_request: AccessRequest) -> bool:
        """Validate access request parameters"""
        if not access_request.secret_name:
            return False

        if not access_request.user_identity:
            return False

        if (
            access_request.duration_hours <= 0 or access_request.duration_hours > 168
        ):  # Max 1 week
            return False

        return True

    def get_access_summary(self) -> Dict[str, Any]:
        """Get summary of current access grants and policies"""
        with self._lock:
            now = datetime.utcnow()

            active_grants = len(
                [g for g, expires in self._temporary_grants.items() if now < expires]
            )

            expired_grants = len(
                [g for g, expires in self._temporary_grants.items() if now >= expires]
            )

            return {
                "project_id": self.project_id,
                "jit_access_enabled": self.enable_jit_access,
                "total_grants": len(self._access_grants),
                "active_grants": active_grants,
                "expired_grants": expired_grants,
                "summary_generated_at": now.isoformat(),
            }
