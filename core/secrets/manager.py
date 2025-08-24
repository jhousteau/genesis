"""
Genesis Secret Manager - Core Secret Management System
SHIELD Methodology: Scan, Harden, Isolate, Encrypt, Log, Defend

Comprehensive secret management for both claude-talk and agent-cage migrations.
"""

import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.cloud import secretmanager
from google.cloud.exceptions import NotFound, PermissionDenied

from .access_patterns import SecretAccessPattern, SecretCache
from .exceptions import (
    SecretAccessDeniedError,
    SecretConfigurationError,
    SecretError,
    SecretNotFoundError,
    SecretValidationError,
)
from .monitoring import SecretMonitor
from .rotation import SecretRotator


@dataclass
class SecretMetadata:
    """Metadata for secret management"""

    name: str
    project_id: str
    version: str = "latest"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    rotation_policy: Optional[Dict[str, Any]] = None
    access_policy: Optional[Dict[str, Any]] = None
    tags: Dict[str, str] = field(default_factory=dict)
    environment: str = "development"
    service: Optional[str] = None
    expires_at: Optional[datetime] = None


class SecretManager:
    """
    Genesis Secret Manager implementing SHIELD methodology

    S - Scan: Comprehensive secret discovery and validation
    H - Harden: Secure secret access patterns and encryption
    I - Isolate: Environment and service-based secret isolation
    E - Encrypt: End-to-end encryption for secrets
    L - Log: Complete audit logging for secret operations
    D - Defend: Real-time monitoring and threat detection
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        environment: str = "development",
        enable_caching: bool = True,
        enable_rotation: bool = True,
        enable_monitoring: bool = True,
    ):
        self.project_id = project_id or os.getenv("PROJECT_ID")
        if not self.project_id:
            raise SecretConfigurationError("PROJECT_ID must be set")

        self.environment = environment
        self.logger = self._setup_logging()

        # Initialize GCP Secret Manager client
        try:
            self.client = secretmanager.SecretManagerServiceClient()
        except Exception as e:
            raise SecretConfigurationError(
                f"Failed to initialize Secret Manager client: {e}"
            )

        # Initialize components
        self.cache = SecretCache() if enable_caching else None
        self.rotator = SecretRotator(self) if enable_rotation else None
        self.monitor = SecretMonitor(self) if enable_monitoring else None
        self.access_pattern = SecretAccessPattern(self)

        # Thread safety
        self._lock = threading.RLock()

        # Secret validation rules
        self.validation_rules = self._load_validation_rules()

        self.logger.info(f"SecretManager initialized for project: {self.project_id}")

    def _setup_logging(self) -> logging.Logger:
        """Set up security-focused logging"""
        logger = logging.getLogger(f"genesis.secrets.{self.project_id}")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [SECRET_AUDIT] %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load secret validation rules"""
        return {
            "min_length": 8,
            "require_complexity": True,
            "forbidden_patterns": [
                "password123",
                "admin",
                "secret",
                "key123",
            ],
            "required_entropy": 50.0,
        }

    # SHIELD Method: SCAN - Secret Discovery and Validation
    def scan_secrets(
        self, filters: Optional[Dict[str, str]] = None
    ) -> List[SecretMetadata]:
        """
        Scan and discover all secrets with optional filtering

        Args:
            filters: Optional filters for secret discovery

        Returns:
            List of discovered secrets with metadata
        """
        self.logger.info("Starting secret discovery scan")

        try:
            parent = f"projects/{self.project_id}"
            secrets = []

            for secret in self.client.list_secrets(request={"parent": parent}):
                # Extract secret name from full path
                secret_name = secret.name.split("/")[-1]

                # Get latest version info
                try:
                    latest_version = self._get_latest_version(secret_name)
                    version_info = self.client.get_secret_version(
                        name=latest_version.name
                    )

                    metadata = SecretMetadata(
                        name=secret_name,
                        project_id=self.project_id,
                        version=latest_version.name.split("/")[-1],
                        created_at=secret.create_time,
                        updated_at=version_info.create_time,
                        environment=self.environment,
                        tags=dict(secret.labels) if secret.labels else {},
                    )

                    # Apply filters
                    if self._matches_filters(metadata, filters):
                        secrets.append(metadata)

                except Exception as e:
                    self.logger.warning(
                        f"Could not get version info for secret {secret_name}: {e}"
                    )
                    continue

            self.logger.info(
                f"Secret scan completed: {len(secrets)} secrets discovered"
            )

            if self.monitor:
                self.monitor.log_secret_access(
                    "scan", "success", {"count": len(secrets)}
                )

            return secrets

        except Exception as e:
            error_msg = f"Secret scan failed: {e}"
            self.logger.error(error_msg)

            if self.monitor:
                self.monitor.log_secret_access("scan", "failure", {"error": str(e)})

            raise SecretError(error_msg)

    def _matches_filters(
        self, metadata: SecretMetadata, filters: Optional[Dict[str, str]]
    ) -> bool:
        """Check if secret metadata matches filters"""
        if not filters:
            return True

        for key, value in filters.items():
            if key == "environment" and metadata.environment != value:
                return False
            elif key == "service" and metadata.service != value:
                return False
            elif key in metadata.tags and metadata.tags[key] != value:
                return False

        return True

    # SHIELD Method: HARDEN - Secure Secret Access
    def get_secret(
        self,
        secret_name: str,
        version: str = "latest",
        validate: bool = True,
        use_cache: bool = True,
    ) -> str:
        """
        Securely retrieve a secret value

        Args:
            secret_name: Name of the secret
            version: Secret version (default: "latest")
            validate: Whether to validate the secret
            use_cache: Whether to use cached values

        Returns:
            Decrypted secret value
        """
        with self._lock:
            self.logger.info(f"Retrieving secret: {secret_name}")

            # Check cache first (if enabled)
            if use_cache and self.cache:
                cached_value = self.cache.get(secret_name, version)
                if cached_value:
                    self.logger.debug(f"Secret {secret_name} retrieved from cache")

                    if self.monitor:
                        self.monitor.log_secret_access(
                            "get",
                            "success",
                            {
                                "secret_name": secret_name,
                                "version": version,
                                "source": "cache",
                            },
                        )

                    return cached_value

            try:
                # Construct the resource name
                if version == "latest":
                    name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                else:
                    name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"

                # Access the secret version
                response = self.client.access_secret_version(request={"name": name})
                secret_value = response.payload.data.decode("UTF-8")

                # Validate secret if requested
                if validate:
                    self._validate_secret(secret_name, secret_value)

                # Cache the secret (if enabled)
                if use_cache and self.cache:
                    self.cache.set(secret_name, version, secret_value)

                self.logger.info(f"Secret {secret_name} retrieved successfully")

                if self.monitor:
                    self.monitor.log_secret_access(
                        "get",
                        "success",
                        {
                            "secret_name": secret_name,
                            "version": version,
                            "source": "secret_manager",
                        },
                    )

                return secret_value

            except NotFound:
                error_msg = f"Secret {secret_name} not found"
                self.logger.error(error_msg)

                if self.monitor:
                    self.monitor.log_secret_access(
                        "get",
                        "not_found",
                        {
                            "secret_name": secret_name,
                            "version": version,
                        },
                    )

                raise SecretNotFoundError(secret_name, self.project_id)

            except PermissionDenied:
                error_msg = f"Access denied to secret {secret_name}"
                self.logger.error(error_msg)

                if self.monitor:
                    self.monitor.log_secret_access(
                        "get",
                        "access_denied",
                        {
                            "secret_name": secret_name,
                            "version": version,
                        },
                    )

                raise SecretAccessDeniedError(secret_name)

            except Exception as e:
                error_msg = f"Failed to retrieve secret {secret_name}: {e}"
                self.logger.error(error_msg)

                if self.monitor:
                    self.monitor.log_secret_access(
                        "get",
                        "error",
                        {
                            "secret_name": secret_name,
                            "version": version,
                            "error": str(e),
                        },
                    )

                raise SecretError(error_msg)

    # SHIELD Method: ISOLATE - Environment and Service Isolation
    def create_secret(
        self,
        secret_name: str,
        secret_value: str,
        labels: Optional[Dict[str, str]] = None,
        replication_policy: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> bool:
        """
        Create a new secret with isolation controls

        Args:
            secret_name: Name of the secret
            secret_value: Secret value to store
            labels: Labels for categorization and isolation
            replication_policy: Secret replication policy
            validate: Whether to validate the secret before creating

        Returns:
            True if secret was created successfully
        """
        with self._lock:
            self.logger.info(f"Creating secret: {secret_name}")

            # Validate secret before creation
            if validate:
                self._validate_secret(secret_name, secret_value)

            # Add isolation labels
            isolation_labels = self._get_isolation_labels(labels)

            try:
                # Create the parent secret
                parent = f"projects/{self.project_id}"
                secret_id = secret_name

                secret = {
                    "replication": replication_policy or {"automatic": {}},
                    "labels": isolation_labels,
                }

                # Create the secret
                response = self.client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": secret,
                    }
                )

                # Add the secret version
                self._add_secret_version(secret_name, secret_value)

                self.logger.info(f"Secret {secret_name} created successfully")

                if self.monitor:
                    self.monitor.log_secret_access(
                        "create",
                        "success",
                        {
                            "secret_name": secret_name,
                            "labels": isolation_labels,
                        },
                    )

                return True

            except Exception as e:
                error_msg = f"Failed to create secret {secret_name}: {e}"
                self.logger.error(error_msg)

                if self.monitor:
                    self.monitor.log_secret_access(
                        "create",
                        "error",
                        {
                            "secret_name": secret_name,
                            "error": str(e),
                        },
                    )

                raise SecretError(error_msg)

    def _get_isolation_labels(self, labels: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Get labels with isolation controls"""
        isolation_labels = {
            "environment": self.environment,
            "project": self.project_id,
            "managed_by": "genesis_secret_manager",
            "created_at": datetime.utcnow().isoformat(),
        }

        if labels:
            isolation_labels.update(labels)

        return isolation_labels

    def _add_secret_version(self, secret_name: str, secret_value: str) -> None:
        """Add a version to an existing secret"""
        parent = f"projects/{self.project_id}/secrets/{secret_name}"
        payload = {"data": secret_value.encode("UTF-8")}

        self.client.add_secret_version(request={"parent": parent, "payload": payload})

    # SHIELD Method: ENCRYPT - End-to-end Encryption
    def rotate_secret(
        self,
        secret_name: str,
        new_value: Optional[str] = None,
        validate: bool = True,
    ) -> str:
        """
        Rotate a secret with encryption

        Args:
            secret_name: Name of the secret to rotate
            new_value: New secret value (auto-generated if None)
            validate: Whether to validate the new secret

        Returns:
            New secret version
        """
        if not self.rotator:
            raise SecretError("Secret rotation is disabled")

        return self.rotator.rotate_secret(secret_name, new_value, validate)

    # SHIELD Method: LOG - Comprehensive Audit Logging
    def get_secret_audit_log(
        self,
        secret_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get audit log for secret operations

        Args:
            secret_name: Filter by specific secret (optional)
            start_time: Start time for log filtering
            end_time: End time for log filtering

        Returns:
            List of audit log entries
        """
        if not self.monitor:
            raise SecretError("Secret monitoring is disabled")

        return self.monitor.get_audit_log(secret_name, start_time, end_time)

    # SHIELD Method: DEFEND - Real-time Monitoring
    def validate_secret_health(self) -> Dict[str, Any]:
        """
        Validate overall secret health and security posture

        Returns:
            Secret health report
        """
        self.logger.info("Starting secret health validation")

        health_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "project_id": self.project_id,
            "environment": self.environment,
            "secrets_discovered": 0,
            "secrets_validated": 0,
            "validation_failures": [],
            "security_issues": [],
            "recommendations": [],
        }

        try:
            # Discover all secrets
            secrets = self.scan_secrets()
            health_report["secrets_discovered"] = len(secrets)

            # Validate each secret
            for secret_metadata in secrets:
                try:
                    secret_value = self.get_secret(secret_metadata.name, validate=True)
                    health_report["secrets_validated"] += 1

                    # Check for security issues
                    issues = self._check_secret_security_issues(
                        secret_metadata.name, secret_value, secret_metadata
                    )

                    if issues:
                        health_report["security_issues"].extend(issues)

                except Exception as e:
                    health_report["validation_failures"].append(
                        {
                            "secret_name": secret_metadata.name,
                            "error": str(e),
                        }
                    )

            # Generate recommendations
            health_report["recommendations"] = self._generate_security_recommendations(
                health_report
            )

            self.logger.info(
                f"Secret health validation completed: {health_report['secrets_validated']}/{health_report['secrets_discovered']} secrets validated"
            )

            return health_report

        except Exception as e:
            error_msg = f"Secret health validation failed: {e}"
            self.logger.error(error_msg)
            raise SecretError(error_msg)

    def _check_secret_security_issues(
        self, secret_name: str, secret_value: str, metadata: SecretMetadata
    ) -> List[Dict[str, Any]]:
        """Check for security issues in a secret"""
        issues = []

        # Check age of secret
        if metadata.created_at:
            age_days = (
                datetime.utcnow() - metadata.created_at.replace(tzinfo=None)
            ).days
            if age_days > 90:  # Older than 90 days
                issues.append(
                    {
                        "type": "stale_secret",
                        "secret_name": secret_name,
                        "message": f"Secret is {age_days} days old and may need rotation",
                        "severity": "medium",
                    }
                )

        # Check for weak secrets
        if len(secret_value) < 12:
            issues.append(
                {
                    "type": "weak_secret",
                    "secret_name": secret_name,
                    "message": "Secret is too short and may be vulnerable",
                    "severity": "high",
                }
            )

        # Check for forbidden patterns
        for pattern in self.validation_rules["forbidden_patterns"]:
            if pattern.lower() in secret_value.lower():
                issues.append(
                    {
                        "type": "forbidden_pattern",
                        "secret_name": secret_name,
                        "message": f"Secret contains forbidden pattern: {pattern}",
                        "severity": "critical",
                    }
                )

        return issues

    def _generate_security_recommendations(
        self, health_report: Dict[str, Any]
    ) -> List[str]:
        """Generate security recommendations based on health report"""
        recommendations = []

        if health_report["security_issues"]:
            critical_issues = [
                issue
                for issue in health_report["security_issues"]
                if issue["severity"] == "critical"
            ]
            high_issues = [
                issue
                for issue in health_report["security_issues"]
                if issue["severity"] == "high"
            ]

            if critical_issues:
                recommendations.append(
                    f"URGENT: Address {len(critical_issues)} critical security issues immediately"
                )

            if high_issues:
                recommendations.append(
                    f"HIGH PRIORITY: Address {len(high_issues)} high-severity security issues"
                )

        if health_report["validation_failures"]:
            recommendations.append(
                f"Fix {len(health_report['validation_failures'])} secret validation failures"
            )

        # Additional recommendations
        if health_report["secrets_discovered"] > 50:
            recommendations.append(
                "Consider secret consolidation to reduce attack surface"
            )

        recommendations.append(
            "Enable automated secret rotation for all production secrets"
        )
        recommendations.append("Implement regular secret security audits")

        return recommendations

    def _validate_secret(self, secret_name: str, secret_value: str) -> None:
        """Validate secret against security rules"""
        if len(secret_value) < self.validation_rules["min_length"]:
            raise SecretValidationError(
                secret_name,
                [
                    f"Secret too short (minimum {self.validation_rules['min_length']} characters)"
                ],
            )

        for pattern in self.validation_rules["forbidden_patterns"]:
            if pattern.lower() in secret_value.lower():
                raise SecretValidationError(
                    secret_name, [f"Secret contains forbidden pattern: {pattern}"]
                )

    def _get_latest_version(self, secret_name: str):
        """Get the latest version of a secret"""
        name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
        return self.client.get_secret_version(request={"name": name})

    def delete_secret(self, secret_name: str, force: bool = False) -> bool:
        """
        Delete a secret (with safety checks)

        Args:
            secret_name: Name of the secret to delete
            force: Force deletion without confirmation

        Returns:
            True if secret was deleted successfully
        """
        with self._lock:
            if not force and self.environment == "production":
                raise SecretError("Cannot delete production secrets without force=True")

            self.logger.warning(f"Deleting secret: {secret_name}")

            try:
                name = f"projects/{self.project_id}/secrets/{secret_name}"
                self.client.delete_secret(request={"name": name})

                # Clear from cache
                if self.cache:
                    self.cache.invalidate(secret_name)

                self.logger.warning(f"Secret {secret_name} deleted successfully")

                if self.monitor:
                    self.monitor.log_secret_access(
                        "delete",
                        "success",
                        {
                            "secret_name": secret_name,
                            "force": force,
                        },
                    )

                return True

            except NotFound:
                raise SecretNotFoundError(secret_name, self.project_id)
            except Exception as e:
                error_msg = f"Failed to delete secret {secret_name}: {e}"
                self.logger.error(error_msg)

                if self.monitor:
                    self.monitor.log_secret_access(
                        "delete",
                        "error",
                        {
                            "secret_name": secret_name,
                            "error": str(e),
                        },
                    )

                raise SecretError(error_msg)


# Global secret manager instance
_secret_manager: Optional[SecretManager] = None
_manager_lock = threading.Lock()


def get_secret_manager(
    project_id: Optional[str] = None, environment: Optional[str] = None, **kwargs
) -> SecretManager:
    """
    Get or create the global secret manager instance

    Args:
        project_id: GCP project ID
        environment: Environment name
        **kwargs: Additional SecretManager initialization arguments

    Returns:
        SecretManager instance
    """
    global _secret_manager

    with _manager_lock:
        if _secret_manager is None:
            env = environment or os.getenv("ENVIRONMENT", "development")
            _secret_manager = SecretManager(
                project_id=project_id, environment=env, **kwargs
            )

        return _secret_manager


def reset_secret_manager() -> None:
    """Reset the global secret manager instance (for testing)"""
    global _secret_manager

    with _manager_lock:
        _secret_manager = None
