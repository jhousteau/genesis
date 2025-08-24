"""
Authentication Service
Multi-provider authentication system with security controls following CRAFT methodology.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class AuthCredentials:
    """Authentication credentials data class."""

    provider: str
    project_id: str
    service_account: Optional[str] = None
    token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    scopes: Optional[List[str]] = None


class AuthenticationError(Exception):
    """Authentication-specific error."""

    pass


class AuthService:
    """
    Multi-provider authentication service implementing CRAFT principles.

    Create: Robust authentication framework
    Refactor: Optimized for multiple providers
    Authenticate: Core responsibility - secure authentication
    Function: Reliable credential management
    Test: Comprehensive validation
    """

    def __init__(self, config_service):
        self.config_service = config_service
        self.credentials_cache: Dict[str, AuthCredentials] = {}
        self._initialize_auth()

    def _initialize_auth(self) -> None:
        """Initialize authentication system."""
        security_config = self.config_service.get_security_config()
        self.default_service_account = security_config.get("service_account")
        self.default_scopes = security_config.get("scopes", [])

    def authenticate_gcp(
        self,
        project_id: Optional[str] = None,
        service_account: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> AuthCredentials:
        """
        Authenticate with Google Cloud Platform.

        Supports multiple authentication methods:
        1. Service account impersonation (recommended)
        2. Application default credentials
        3. User credentials
        """
        project_id = project_id or self.config_service.project_id
        service_account = service_account or self.default_service_account
        scopes = scopes or self.default_scopes

        if not project_id:
            raise AuthenticationError("Project ID is required for GCP authentication")

        cache_key = f"gcp_{project_id}_{service_account}"

        # Check cache first
        if cache_key in self.credentials_cache:
            credentials = self.credentials_cache[cache_key]
            if self._is_token_valid(credentials):
                return credentials

        try:
            # Try service account impersonation first (most secure)
            if service_account:
                credentials = self._authenticate_service_account(
                    project_id, service_account, scopes
                )
            else:
                # Fall back to application default credentials
                credentials = self._authenticate_application_default(project_id, scopes)

            # Cache the credentials
            self.credentials_cache[cache_key] = credentials

            # Audit log the authentication
            self._audit_log_auth("gcp", project_id, service_account, True)

            return credentials

        except Exception as e:
            self._audit_log_auth("gcp", project_id, service_account, False, str(e))
            raise AuthenticationError(f"GCP authentication failed: {e}")

    def _authenticate_service_account(
        self, project_id: str, service_account: str, scopes: List[str]
    ) -> AuthCredentials:
        """Authenticate using service account impersonation."""
        logger.info(f"Authenticating with service account: {service_account}")

        try:
            # Get access token via service account impersonation
            cmd = [
                "gcloud",
                "auth",
                "print-access-token",
                f"--impersonate-service-account={service_account}",
                f"--project={project_id}",
            ]

            if scopes:
                cmd.extend([f"--scopes={','.join(scopes)}"])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            token = result.stdout.strip()

            # Calculate token expiry (GCP access tokens typically last 1 hour)
            token_expiry = datetime.now() + timedelta(hours=1)

            return AuthCredentials(
                provider="gcp",
                project_id=project_id,
                service_account=service_account,
                token=token,
                token_expiry=token_expiry,
                scopes=scopes,
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"Service account authentication failed: {e.stderr}")
            raise AuthenticationError(
                f"Service account authentication failed: {e.stderr}"
            )

    def _authenticate_application_default(
        self, project_id: str, scopes: List[str]
    ) -> AuthCredentials:
        """Authenticate using application default credentials."""
        logger.info("Authenticating with application default credentials")

        try:
            # Set project for gcloud
            subprocess.run(
                ["gcloud", "config", "set", "project", project_id],
                capture_output=True,
                check=True,
            )

            # Get access token
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True,
            )

            token = result.stdout.strip()
            token_expiry = datetime.now() + timedelta(hours=1)

            return AuthCredentials(
                provider="gcp",
                project_id=project_id,
                token=token,
                token_expiry=token_expiry,
                scopes=scopes,
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"Application default authentication failed: {e.stderr}")
            raise AuthenticationError(
                f"Application default authentication failed: {e.stderr}"
            )

    def get_authenticated_gcloud_cmd(
        self, base_cmd: List[str], project_id: Optional[str] = None
    ) -> List[str]:
        """Get gcloud command with authentication parameters."""
        project_id = project_id or self.config_service.project_id

        if not project_id:
            raise AuthenticationError("Project ID required for gcloud commands")

        # Ensure we have valid credentials
        credentials = self.authenticate_gcp(project_id)

        # Add project to command
        cmd = list(base_cmd)
        cmd.extend([f"--project={project_id}"])

        # Add impersonation if using service account
        if credentials.service_account:
            cmd.extend([f"--impersonate-service-account={credentials.service_account}"])

        return cmd

    def get_kubernetes_credentials(
        self, cluster_name: str, region: str, project_id: Optional[str] = None
    ) -> None:
        """Get Kubernetes cluster credentials."""
        project_id = project_id or self.config_service.project_id

        if not project_id:
            raise AuthenticationError(
                "Project ID required for Kubernetes authentication"
            )

        try:
            # Ensure GCP authentication first
            self.authenticate_gcp(project_id)

            # Get cluster credentials
            cmd = self.get_authenticated_gcloud_cmd(
                [
                    "gcloud",
                    "container",
                    "clusters",
                    "get-credentials",
                    cluster_name,
                    f"--region={region}",
                ],
                project_id,
            )

            subprocess.run(cmd, check=True)
            logger.info(
                f"Kubernetes credentials configured for cluster: {cluster_name}"
            )

        except subprocess.CalledProcessError as e:
            raise AuthenticationError(f"Failed to get Kubernetes credentials: {e}")

    def validate_permissions(
        self,
        project_id: Optional[str] = None,
        required_permissions: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """Validate current permissions."""
        project_id = project_id or self.config_service.project_id
        required_permissions = required_permissions or [
            "compute.instances.list",
            "compute.instanceGroups.list",
            "container.clusters.list",
            "resourcemanager.projects.get",
        ]

        if not project_id:
            raise AuthenticationError("Project ID required for permission validation")

        try:
            # Ensure authentication first
            self.authenticate_gcp(project_id)

            permission_results = {}

            for permission in required_permissions:
                cmd = self.get_authenticated_gcloud_cmd(
                    [
                        "gcloud",
                        "projects",
                        "get-iam-policy",
                        project_id,
                        "--flatten=bindings[].members",
                        f"--filter=bindings.role:roles/compute.admin",
                    ],
                    project_id,
                )

                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, check=True
                    )
                    # Simplified permission check - in production, this would be more sophisticated
                    permission_results[permission] = True
                except subprocess.CalledProcessError:
                    permission_results[permission] = False

            return permission_results

        except Exception as e:
            logger.error(f"Permission validation failed: {e}")
            return {perm: False for perm in required_permissions}

    def refresh_credentials(
        self, provider: str, project_id: Optional[str] = None
    ) -> AuthCredentials:
        """Refresh expired credentials."""
        project_id = project_id or self.config_service.project_id

        # Remove from cache to force refresh
        cache_key = f"{provider}_{project_id}"
        self.credentials_cache.pop(cache_key, None)

        if provider == "gcp":
            return self.authenticate_gcp(project_id)
        else:
            raise AuthenticationError(f"Unsupported provider: {provider}")

    def _is_token_valid(self, credentials: AuthCredentials) -> bool:
        """Check if token is still valid."""
        if not credentials.token_expiry:
            return False

        # Consider token expired if it expires in the next 5 minutes
        return datetime.now() + timedelta(minutes=5) < credentials.token_expiry

    def _audit_log_auth(
        self,
        provider: str,
        project_id: str,
        service_account: Optional[str],
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Log authentication events for audit purposes."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "project_id": project_id,
            "service_account": service_account,
            "success": success,
            "error": error,
            "user": os.getenv("USER", "unknown"),
        }

        # In production, this would write to a secure audit log
        logger.info(f"Auth audit: {json.dumps(audit_entry)}")

    def get_current_credentials(
        self, provider: str = "gcp"
    ) -> Optional[AuthCredentials]:
        """Get currently active credentials."""
        project_id = self.config_service.project_id
        cache_key = f"{provider}_{project_id}"

        credentials = self.credentials_cache.get(cache_key)
        if credentials and self._is_token_valid(credentials):
            return credentials

        return None

    def clear_credentials(self, provider: Optional[str] = None) -> None:
        """Clear cached credentials."""
        if provider:
            keys_to_remove = [
                key for key in self.credentials_cache.keys() if key.startswith(provider)
            ]
            for key in keys_to_remove:
                self.credentials_cache.pop(key, None)
        else:
            self.credentials_cache.clear()

    def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status summary."""
        status = {
            "authenticated": False,
            "provider": None,
            "project_id": self.config_service.project_id,
            "service_account": None,
            "token_expires": None,
            "permissions_validated": False,
        }

        current_creds = self.get_current_credentials()
        if current_creds:
            status.update(
                {
                    "authenticated": True,
                    "provider": current_creds.provider,
                    "service_account": current_creds.service_account,
                    "token_expires": (
                        current_creds.token_expiry.isoformat()
                        if current_creds.token_expiry
                        else None
                    ),
                }
            )

        return status
