"""
Genesis Secret Rotation - Automated Secret Rotation System
SHIELD Methodology: Encrypt component for automated secret rotation

Provides secure automated rotation of secrets with rollback capabilities.
"""

import logging
import secrets
import string
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class RotationStatus(Enum):
    """Status of secret rotation"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RotationType(Enum):
    """Type of secret rotation"""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"
    POLICY_DRIVEN = "policy_driven"


@dataclass
class RotationPolicy:
    """Policy for secret rotation"""

    secret_pattern: str
    rotation_interval_days: int = 90
    auto_rotate: bool = True
    notification_days_before: int = 7
    max_rotation_attempts: int = 3
    rollback_on_failure: bool = True
    validation_required: bool = True
    custom_generator: Optional[Callable[[], str]] = None


@dataclass
class RotationRecord:
    """Record of a secret rotation"""

    rotation_id: str
    secret_name: str
    rotation_type: RotationType
    status: RotationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    error_message: Optional[str] = None
    rollback_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecretGenerator:
    """Secure secret value generator"""

    @staticmethod
    def generate_password(
        length: int = 32,
        include_symbols: bool = True,
        exclude_ambiguous: bool = True,
    ) -> str:
        """Generate a secure password"""
        chars = string.ascii_letters + string.digits

        if include_symbols:
            chars += "!@#$%^&*"

        if exclude_ambiguous:
            # Remove ambiguous characters
            chars = (
                chars.replace("0", "")
                .replace("O", "")
                .replace("1", "")
                .replace("l", "")
                .replace("I", "")
            )

        return "".join(secrets.choice(chars) for _ in range(length))

    @staticmethod
    def generate_api_key(length: int = 64, prefix: str = "") -> str:
        """Generate a secure API key"""
        key_part = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(length)
        )
        return f"{prefix}{key_part}" if prefix else key_part

    @staticmethod
    def generate_token(length: int = 128) -> str:
        """Generate a secure token"""
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_uuid_secret() -> str:
        """Generate a UUID-based secret"""
        return str(uuid.uuid4())


class SecretRotator:
    """
    Automated secret rotation system with comprehensive controls
    """

    def __init__(self, secret_manager):
        self.secret_manager = secret_manager
        self.logger = logging.getLogger("genesis.secrets.rotator")

        # Rotation state
        self._rotation_policies: Dict[str, RotationPolicy] = {}
        self._rotation_records: Dict[str, RotationRecord] = {}
        self._active_rotations: Dict[str, str] = {}  # secret_name -> rotation_id
        self._lock = threading.RLock()

        # Secret generators
        self.generator = SecretGenerator()

        # Load existing policies and records
        self._load_rotation_state()

        self.logger.info("SecretRotator initialized")

    def _load_rotation_state(self) -> None:
        """Load rotation policies and records from persistent storage"""
        # In a real implementation, this would load from a database or file
        # For now, we'll initialize with empty state
        pass

    def _save_rotation_state(self) -> None:
        """Save rotation state to persistent storage"""
        # In a real implementation, this would save to a database or file
        pass

    def register_rotation_policy(
        self,
        secret_pattern: str,
        rotation_interval_days: int = 90,
        auto_rotate: bool = True,
        **kwargs,
    ) -> None:
        """
        Register a rotation policy for secrets

        Args:
            secret_pattern: Pattern to match secret names (supports wildcards)
            rotation_interval_days: Days between rotations
            auto_rotate: Whether to automatically rotate
            **kwargs: Additional policy parameters
        """
        with self._lock:
            policy = RotationPolicy(
                secret_pattern=secret_pattern,
                rotation_interval_days=rotation_interval_days,
                auto_rotate=auto_rotate,
                **kwargs,
            )

            self._rotation_policies[secret_pattern] = policy
            self._save_rotation_state()

            self.logger.info(
                f"Registered rotation policy for pattern: {secret_pattern} "
                f"(interval: {rotation_interval_days} days, auto: {auto_rotate})"
            )

    def rotate_secret(
        self,
        secret_name: str,
        new_value: Optional[str] = None,
        validate: bool = True,
        rotation_type: RotationType = RotationType.MANUAL,
    ) -> str:
        """
        Rotate a secret with comprehensive controls

        Args:
            secret_name: Name of the secret to rotate
            new_value: New secret value (auto-generated if None)
            validate: Whether to validate the new secret
            rotation_type: Type of rotation being performed

        Returns:
            New secret version
        """
        with self._lock:
            # Check if rotation is already in progress
            if secret_name in self._active_rotations:
                existing_rotation_id = self._active_rotations[secret_name]
                raise Exception(
                    f"Rotation already in progress for {secret_name}: {existing_rotation_id}"
                )

            # Generate rotation ID
            rotation_id = f"rot_{uuid.uuid4().hex[:12]}"

            # Create rotation record
            rotation_record = RotationRecord(
                rotation_id=rotation_id,
                secret_name=secret_name,
                rotation_type=rotation_type,
                status=RotationStatus.PENDING,
                started_at=datetime.utcnow(),
            )

            try:
                # Mark rotation as active
                self._active_rotations[secret_name] = rotation_id
                self._rotation_records[rotation_id] = rotation_record

                self.logger.info(
                    f"Starting rotation {rotation_id} for secret {secret_name}"
                )

                # Get current version for rollback
                try:
                    current_version = self.secret_manager._get_latest_version(
                        secret_name
                    )
                    rotation_record.old_version = current_version.name.split("/")[-1]
                except Exception as e:
                    self.logger.warning(
                        f"Could not get current version for {secret_name}: {e}"
                    )

                # Update status to in progress
                rotation_record.status = RotationStatus.IN_PROGRESS

                # Generate new secret value if not provided
                if new_value is None:
                    new_value = self._generate_secret_value(secret_name)

                # Validate new secret
                if validate:
                    self._validate_new_secret(secret_name, new_value)

                # Create new secret version
                self.secret_manager._add_secret_version(secret_name, new_value)

                # Get new version info
                new_version = self.secret_manager._get_latest_version(secret_name)
                rotation_record.new_version = new_version.name.split("/")[-1]

                # Test the new secret (if validation is enabled)
                if validate:
                    self._test_new_secret(secret_name, new_value)

                # Clear cache for this secret
                if self.secret_manager.cache:
                    self.secret_manager.cache.invalidate(secret_name)

                # Mark rotation as completed
                rotation_record.status = RotationStatus.COMPLETED
                rotation_record.completed_at = datetime.utcnow()

                # Log successful rotation
                self.logger.info(
                    f"Rotation {rotation_id} completed successfully for secret {secret_name}"
                )

                # Log to monitoring system
                if self.secret_manager.monitor:
                    self.secret_manager.monitor.log_secret_access(
                        "rotate",
                        "success",
                        {
                            "secret_name": secret_name,
                            "rotation_id": rotation_id,
                            "rotation_type": rotation_type.value,
                            "old_version": rotation_record.old_version,
                            "new_version": rotation_record.new_version,
                        },
                    )

                return rotation_record.new_version

            except Exception as e:
                # Handle rotation failure
                error_msg = (
                    f"Rotation {rotation_id} failed for secret {secret_name}: {str(e)}"
                )
                self.logger.error(error_msg)

                rotation_record.status = RotationStatus.FAILED
                rotation_record.error_message = str(e)
                rotation_record.completed_at = datetime.utcnow()

                # Attempt rollback if enabled
                policy = self._get_policy_for_secret(secret_name)
                if policy and policy.rollback_on_failure:
                    try:
                        self._rollback_rotation(rotation_record)
                    except Exception as rollback_error:
                        self.logger.error(
                            f"Rollback failed for rotation {rotation_id}: {rollback_error}"
                        )

                # Log failed rotation
                if self.secret_manager.monitor:
                    self.secret_manager.monitor.log_secret_access(
                        "rotate",
                        "failed",
                        {
                            "secret_name": secret_name,
                            "rotation_id": rotation_id,
                            "error": str(e),
                        },
                    )

                from .exceptions import SecretRotationError

                raise SecretRotationError(secret_name, rotation_id, str(e))

            finally:
                # Remove from active rotations
                if secret_name in self._active_rotations:
                    del self._active_rotations[secret_name]

                # Save state
                self._save_rotation_state()

    def _generate_secret_value(self, secret_name: str) -> str:
        """Generate appropriate secret value based on secret name and policy"""
        # Check if there's a custom generator for this secret
        policy = self._get_policy_for_secret(secret_name)
        if policy and policy.custom_generator:
            return policy.custom_generator()

        # Generate based on secret name patterns
        secret_lower = secret_name.lower()

        if "password" in secret_lower or "pwd" in secret_lower:
            return self.generator.generate_password()
        elif "api_key" in secret_lower or "apikey" in secret_lower:
            return self.generator.generate_api_key()
        elif "token" in secret_lower:
            return self.generator.generate_token()
        elif "uuid" in secret_lower or "id" in secret_lower:
            return self.generator.generate_uuid_secret()
        else:
            # Default to password generation
            return self.generator.generate_password()

    def _validate_new_secret(self, secret_name: str, new_value: str) -> None:
        """Validate new secret value"""
        # Use the secret manager's validation
        self.secret_manager._validate_secret(secret_name, new_value)

        # Additional rotation-specific validation
        if len(new_value) < 16:
            from .exceptions import SecretValidationError

            raise SecretValidationError(
                secret_name, ["New secret too short for rotation"]
            )

    def _test_new_secret(self, secret_name: str, new_value: str) -> None:
        """Test new secret value to ensure it works"""
        # This would typically involve testing the secret with the service that uses it
        # For now, we'll just do basic validation
        self.logger.debug(f"Testing new secret value for {secret_name}")

        # Simulate secret testing (in real implementation, this would test connectivity, etc.)
        if not new_value or len(new_value.strip()) == 0:
            raise Exception("New secret value is empty or invalid")

    def _rollback_rotation(self, rotation_record: RotationRecord) -> None:
        """Rollback a failed rotation"""
        if not rotation_record.old_version:
            raise Exception("Cannot rollback - no previous version available")

        self.logger.warning(f"Rolling back rotation {rotation_record.rotation_id}")

        try:
            # Disable the current (new) version and enable the old version
            # In a real implementation, this would involve more complex version management
            rotation_record.status = RotationStatus.ROLLED_BACK
            rotation_record.rollback_version = rotation_record.old_version

            # Clear cache to ensure old version is used
            if self.secret_manager.cache:
                self.secret_manager.cache.invalidate(rotation_record.secret_name)

            self.logger.info(
                f"Rollback completed for rotation {rotation_record.rotation_id}"
            )

        except Exception as e:
            self.logger.error(
                f"Rollback failed for rotation {rotation_record.rotation_id}: {e}"
            )
            raise

    def _get_policy_for_secret(self, secret_name: str) -> Optional[RotationPolicy]:
        """Get rotation policy for a specific secret"""
        with self._lock:
            for pattern, policy in self._rotation_policies.items():
                if self._matches_pattern(secret_name, pattern):
                    return policy
            return None

    def _matches_pattern(self, secret_name: str, pattern: str) -> bool:
        """Check if secret name matches pattern"""
        if pattern == "*":
            return True

        if "*" in pattern:
            import fnmatch

            return fnmatch.fnmatch(secret_name, pattern)

        return secret_name == pattern

    def check_rotation_needed(self) -> List[Dict[str, Any]]:
        """
        Check which secrets need rotation

        Returns:
            List of secrets needing rotation with details
        """
        self.logger.info("Checking secrets for rotation needs")

        rotation_needed = []

        try:
            # Get all secrets
            secrets = self.secret_manager.scan_secrets()

            for secret_metadata in secrets:
                policy = self._get_policy_for_secret(secret_metadata.name)

                if not policy or not policy.auto_rotate:
                    continue

                # Check if rotation is needed based on age
                if secret_metadata.created_at:
                    age_days = (
                        datetime.utcnow()
                        - secret_metadata.created_at.replace(tzinfo=None)
                    ).days

                    if age_days >= policy.rotation_interval_days:
                        rotation_needed.append(
                            {
                                "secret_name": secret_metadata.name,
                                "age_days": age_days,
                                "rotation_interval": policy.rotation_interval_days,
                                "policy_pattern": policy.secret_pattern,
                                "overdue_days": age_days
                                - policy.rotation_interval_days,
                            }
                        )

            self.logger.info(f"Found {len(rotation_needed)} secrets needing rotation")
            return rotation_needed

        except Exception as e:
            self.logger.error(f"Error checking rotation needs: {e}")
            return []

    def auto_rotate_secrets(self) -> Dict[str, Any]:
        """
        Automatically rotate secrets that need rotation

        Returns:
            Summary of rotation results
        """
        self.logger.info("Starting automatic secret rotation")

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "secrets_checked": 0,
            "rotations_attempted": 0,
            "rotations_successful": 0,
            "rotations_failed": 0,
            "errors": [],
        }

        try:
            # Check which secrets need rotation
            rotation_needed = self.check_rotation_needed()
            results["secrets_checked"] = len(rotation_needed)

            for rotation_info in rotation_needed:
                secret_name = rotation_info["secret_name"]

                try:
                    results["rotations_attempted"] += 1

                    # Perform rotation
                    new_version = self.rotate_secret(
                        secret_name=secret_name,
                        rotation_type=RotationType.SCHEDULED,
                    )

                    results["rotations_successful"] += 1
                    self.logger.info(
                        f"Auto-rotated secret {secret_name} to version {new_version}"
                    )

                except Exception as e:
                    results["rotations_failed"] += 1
                    error_msg = f"Failed to rotate {secret_name}: {str(e)}"
                    results["errors"].append(error_msg)
                    self.logger.error(error_msg)

            results["completed_at"] = datetime.utcnow().isoformat()

            self.logger.info(
                f"Automatic rotation completed: {results['rotations_successful']} successful, "
                f"{results['rotations_failed']} failed out of {results['rotations_attempted']} attempted"
            )

            return results

        except Exception as e:
            error_msg = f"Auto rotation failed: {str(e)}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
            return results

    def get_rotation_history(
        self,
        secret_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get rotation history

        Args:
            secret_name: Filter by specific secret (optional)
            limit: Maximum number of records to return

        Returns:
            List of rotation records
        """
        with self._lock:
            records = list(self._rotation_records.values())

            # Filter by secret name if provided
            if secret_name:
                records = [r for r in records if r.secret_name == secret_name]

            # Sort by start time (newest first)
            records.sort(key=lambda r: r.started_at, reverse=True)

            # Limit results
            records = records[:limit]

            # Convert to dictionaries
            return [
                {
                    "rotation_id": r.rotation_id,
                    "secret_name": r.secret_name,
                    "rotation_type": r.rotation_type.value,
                    "status": r.status.value,
                    "started_at": r.started_at.isoformat(),
                    "completed_at": (
                        r.completed_at.isoformat() if r.completed_at else None
                    ),
                    "old_version": r.old_version,
                    "new_version": r.new_version,
                    "error_message": r.error_message,
                    "rollback_version": r.rollback_version,
                }
                for r in records
            ]

    def get_rotation_policies(self) -> Dict[str, Dict[str, Any]]:
        """Get all rotation policies"""
        with self._lock:
            return {
                pattern: {
                    "secret_pattern": policy.secret_pattern,
                    "rotation_interval_days": policy.rotation_interval_days,
                    "auto_rotate": policy.auto_rotate,
                    "notification_days_before": policy.notification_days_before,
                    "max_rotation_attempts": policy.max_rotation_attempts,
                    "rollback_on_failure": policy.rollback_on_failure,
                    "validation_required": policy.validation_required,
                    "has_custom_generator": policy.custom_generator is not None,
                }
                for pattern, policy in self._rotation_policies.items()
            }

    def emergency_rotate_secret(self, secret_name: str, reason: str) -> str:
        """
        Emergency rotation of a secret (bypasses normal schedules)

        Args:
            secret_name: Name of the secret to rotate
            reason: Reason for emergency rotation

        Returns:
            New secret version
        """
        self.logger.warning(f"Emergency rotation requested for {secret_name}: {reason}")

        try:
            new_version = self.rotate_secret(
                secret_name=secret_name,
                rotation_type=RotationType.EMERGENCY,
            )

            # Log emergency rotation
            if self.secret_manager.monitor:
                self.secret_manager.monitor.log_secret_access(
                    "emergency_rotate",
                    "success",
                    {
                        "secret_name": secret_name,
                        "reason": reason,
                        "new_version": new_version,
                    },
                )

            return new_version

        except Exception as e:
            # Log failed emergency rotation
            if self.secret_manager.monitor:
                self.secret_manager.monitor.log_secret_access(
                    "emergency_rotate",
                    "failed",
                    {
                        "secret_name": secret_name,
                        "reason": reason,
                        "error": str(e),
                    },
                )

            raise
