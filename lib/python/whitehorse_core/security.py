"""
Security Manager Module

Provides comprehensive security management including authentication,
authorization, secret management, and security scanning integration.
"""

import base64
import hashlib
import hmac
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

try:
    import jwt
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

try:
    from google.cloud import iam, secretmanager
    from google.oauth2 import service_account

    HAS_GCP_SECURITY = True
except ImportError:
    HAS_GCP_SECURITY = False

from .config import get_config
from .errors import AuthorizationError, ExternalServiceError, ValidationError
from .logging import get_logger

logger = get_logger(__name__)


class SecurityLevel(Enum):
    """Security level classifications."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class Permission(Enum):
    """Permission types."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    DELETE = "delete"


class TokenType(Enum):
    """Token types."""

    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SERVICE = "service"


@dataclass
class User:
    """User information."""

    id: str
    email: str
    name: str
    roles: List[str] = field(default_factory=list)
    permissions: List[Permission] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Role:
    """Role definition."""

    name: str
    description: str
    permissions: List[Permission]
    parent_roles: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SecurityToken:
    """Security token information."""

    token: str
    token_type: TokenType
    user_id: str
    expires_at: datetime
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAuditEvent:
    """Security audit event."""

    id: str
    event_type: str
    user_id: Optional[str]
    resource: Optional[str]
    action: str
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


class SecurityManager:
    """
    Central security manager for authentication, authorization, and security operations.
    Integrates with GCP IAM and Secret Manager.
    """

    def __init__(self):
        """Initialize security manager."""
        self.config = get_config()
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.active_tokens: Dict[str, SecurityToken] = {}
        self.audit_events: List[SecurityAuditEvent] = []
        self.security_lock = threading.Lock()

        # Initialize security components
        self.secret_manager_client = None
        self.iam_client = None
        self.encryption_key = None

        self._initialize_gcp_security()
        self._initialize_encryption()
        self._setup_default_roles()

    def _initialize_gcp_security(self) -> None:
        """Initialize GCP security clients."""
        if not HAS_GCP_SECURITY:
            logger.warning("GCP security libraries not available")
            return

        try:
            project_id = getattr(self.config, "gcp_project", None) or os.environ.get(
                "GCP_PROJECT"
            )
            if project_id:
                self.secret_manager_client = secretmanager.SecretManagerServiceClient()
                self.iam_client = iam.IAMCredentialsClient()
                self.project_id = project_id
                logger.info("GCP security clients initialized", project=project_id)
            else:
                logger.warning("GCP project not configured, skipping GCP security")
        except Exception as e:
            logger.error(f"Failed to initialize GCP security: {e}")

    def _initialize_encryption(self) -> None:
        """Initialize encryption capabilities."""
        if not HAS_CRYPTO:
            logger.warning("Cryptography libraries not available")
            return

        try:
            # Try to load encryption key from environment or generate one
            key_env = os.environ.get("WHITEHORSE_ENCRYPTION_KEY")
            if key_env:
                self.encryption_key = base64.urlsafe_b64decode(key_env)
            else:
                # Generate a new key (in production, this should be managed securely)
                self.encryption_key = Fernet.generate_key()
                logger.warning(
                    "Generated new encryption key - ensure this is stored securely"
                )

            logger.info("Encryption initialized")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")

    def _setup_default_roles(self) -> None:
        """Setup default roles and permissions."""
        default_roles = [
            Role(
                name="admin",
                description="Full system administrator",
                permissions=[
                    Permission.READ,
                    Permission.WRITE,
                    Permission.EXECUTE,
                    Permission.ADMIN,
                    Permission.DELETE,
                ],
            ),
            Role(
                name="developer",
                description="Developer with deployment permissions",
                permissions=[Permission.READ, Permission.WRITE, Permission.EXECUTE],
            ),
            Role(
                name="viewer",
                description="Read-only access",
                permissions=[Permission.READ],
            ),
            Role(
                name="operator",
                description="Operations with execute permissions",
                permissions=[Permission.READ, Permission.EXECUTE],
            ),
        ]

        for role in default_roles:
            self.roles[role.name] = role

    def create_user(
        self,
        user_id: str,
        email: str,
        name: str,
        roles: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> User:
        """
        Create a new user.

        Args:
            user_id: Unique user identifier
            email: User email address
            name: User display name
            roles: List of role names
            metadata: Additional user metadata

        Returns:
            Created User instance
        """
        if user_id in self.users:
            raise ValidationError(f"User {user_id} already exists")

        # Validate roles
        roles = roles or []
        for role_name in roles:
            if role_name not in self.roles:
                raise ValidationError(f"Unknown role: {role_name}")

        # Calculate effective permissions
        permissions = self._calculate_user_permissions(roles)

        user = User(
            id=user_id,
            email=email,
            name=name,
            roles=roles,
            permissions=permissions,
            metadata=metadata or {},
        )

        with self.security_lock:
            self.users[user_id] = user

        self._audit_event(
            event_type="user_created",
            user_id=user_id,
            action="create_user",
            details={"email": email, "roles": roles},
        )

        logger.info(f"User created: {user_id}", email=email, roles=roles)
        return user

    def _calculate_user_permissions(self, role_names: List[str]) -> List[Permission]:
        """Calculate effective permissions for user based on roles."""
        permissions = set()

        for role_name in role_names:
            if role_name in self.roles:
                role = self.roles[role_name]
                permissions.update(role.permissions)

                # Add inherited permissions from parent roles
                for parent_role in role.parent_roles:
                    if parent_role in self.roles:
                        permissions.update(self.roles[parent_role].permissions)

        return list(permissions)

    def authenticate_user(
        self, user_id: str, credential: str, credential_type: str = "password"
    ) -> Optional[User]:
        """
        Authenticate a user.

        Args:
            user_id: User identifier
            credential: Authentication credential
            credential_type: Type of credential (password, token, etc.)

        Returns:
            User instance if authenticated, None otherwise
        """
        user = self.users.get(user_id)
        if not user or not user.active:
            self._audit_event(
                event_type="authentication_failed",
                user_id=user_id,
                action="authenticate",
                success=False,
                details={"reason": "user_not_found_or_inactive"},
            )
            return None

        # In a real implementation, this would verify the credential
        # For now, we'll assume authentication is successful if user exists
        authenticated = True  # Placeholder

        if authenticated:
            user.last_login = datetime.utcnow()
            self._audit_event(
                event_type="authentication_success",
                user_id=user_id,
                action="authenticate",
                success=True,
            )
            logger.info(f"User authenticated: {user_id}")
            return user
        else:
            self._audit_event(
                event_type="authentication_failed",
                user_id=user_id,
                action="authenticate",
                success=False,
                details={"reason": "invalid_credential"},
            )
            logger.warning(f"Authentication failed for user: {user_id}")
            return None

    def create_token(
        self,
        user_id: str,
        token_type: TokenType = TokenType.ACCESS,
        expires_in_seconds: int = 3600,
        scopes: Optional[List[str]] = None,
    ) -> SecurityToken:
        """
        Create a security token for a user.

        Args:
            user_id: User identifier
            token_type: Type of token
            expires_in_seconds: Token expiration time
            scopes: Token scopes

        Returns:
            SecurityToken instance
        """
        if user_id not in self.users:
            raise ValidationError(f"User {user_id} not found")

        if not HAS_CRYPTO:
            raise ExternalServiceError("JWT library not available")

        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)

        # Create JWT payload
        payload = {
            "user_id": user_id,
            "token_type": token_type.value,
            "exp": expires_at.timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "scopes": scopes or [],
        }

        # Get JWT secret from config or use default
        jwt_secret = getattr(
            self.config, "jwt_secret", "default_secret_change_in_production"
        )
        jwt_algorithm = getattr(self.config, "jwt_algorithm", "HS256")

        # Create token
        token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)

        security_token = SecurityToken(
            token=token,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
            scopes=scopes or [],
        )

        with self.security_lock:
            self.active_tokens[token] = security_token

        self._audit_event(
            event_type="token_created",
            user_id=user_id,
            action="create_token",
            details={
                "token_type": token_type.value,
                "expires_at": expires_at.isoformat(),
            },
        )

        logger.info(f"Token created for user {user_id}", token_type=token_type.value)
        return security_token

    def validate_token(self, token: str) -> Optional[SecurityToken]:
        """
        Validate a security token.

        Args:
            token: Token string

        Returns:
            SecurityToken if valid, None otherwise
        """
        if not HAS_CRYPTO:
            logger.error("JWT library not available")
            return None

        try:
            jwt_secret = getattr(
                self.config, "jwt_secret", "default_secret_change_in_production"
            )
            jwt_algorithm = getattr(self.config, "jwt_algorithm", "HS256")

            # Decode and verify token
            payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])

            # Check if token is in active tokens
            if token in self.active_tokens:
                security_token = self.active_tokens[token]

                # Check expiration
                if security_token.expires_at > datetime.utcnow():
                    return security_token
                else:
                    # Remove expired token
                    with self.security_lock:
                        del self.active_tokens[token]

                    self._audit_event(
                        event_type="token_expired",
                        user_id=payload.get("user_id"),
                        action="validate_token",
                        success=False,
                        details={"reason": "token_expired"},
                    )

            return None

        except jwt.ExpiredSignatureError:
            self._audit_event(
                event_type="token_validation_failed",
                action="validate_token",
                success=False,
                details={"reason": "expired_signature"},
            )
            return None
        except jwt.InvalidTokenError as e:
            self._audit_event(
                event_type="token_validation_failed",
                action="validate_token",
                success=False,
                details={"reason": "invalid_token", "error": str(e)},
            )
            return None

    def check_permission(
        self, user_id: str, permission: Permission, resource: Optional[str] = None
    ) -> bool:
        """
        Check if user has specific permission.

        Args:
            user_id: User identifier
            permission: Required permission
            resource: Optional resource identifier

        Returns:
            True if user has permission, False otherwise
        """
        user = self.users.get(user_id)
        if not user or not user.active:
            self._audit_event(
                event_type="authorization_failed",
                user_id=user_id,
                resource=resource,
                action="check_permission",
                success=False,
                details={
                    "permission": permission.value,
                    "reason": "user_not_found_or_inactive",
                },
            )
            return False

        has_permission = permission in user.permissions

        self._audit_event(
            event_type="authorization_check",
            user_id=user_id,
            resource=resource,
            action="check_permission",
            success=has_permission,
            details={"permission": permission.value},
        )

        return has_permission

    def require_permission(
        self, user_id: str, permission: Permission, resource: Optional[str] = None
    ) -> None:
        """
        Require user to have specific permission, raise exception if not.

        Args:
            user_id: User identifier
            permission: Required permission
            resource: Optional resource identifier

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        if not self.check_permission(user_id, permission, resource):
            raise AuthorizationError(
                f"User {user_id} does not have {permission.value} permission"
            )

    def encrypt_data(self, data: Union[str, bytes]) -> str:
        """
        Encrypt sensitive data.

        Args:
            data: Data to encrypt

        Returns:
            Base64 encoded encrypted data
        """
        if not HAS_CRYPTO or not self.encryption_key:
            raise ExternalServiceError("Encryption not available")

        try:
            fernet = Fernet(self.encryption_key)

            if isinstance(data, str):
                data = data.encode("utf-8")

            encrypted_data = fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted_data).decode("utf-8")

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ExternalServiceError(f"Encryption failed: {e}")

    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data.

        Args:
            encrypted_data: Base64 encoded encrypted data

        Returns:
            Decrypted data as string
        """
        if not HAS_CRYPTO or not self.encryption_key:
            raise ExternalServiceError("Decryption not available")

        try:
            fernet = Fernet(self.encryption_key)

            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode("utf-8"))
            decrypted_data = fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode("utf-8")

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ExternalServiceError(f"Decryption failed: {e}")

    def store_secret(
        self, name: str, value: str, labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Store a secret in GCP Secret Manager.

        Args:
            name: Secret name
            value: Secret value
            labels: Optional labels

        Returns:
            True if stored successfully
        """
        if not self.secret_manager_client:
            logger.error("Secret Manager client not available")
            return False

        try:
            parent = f"projects/{self.project_id}"

            # Create the secret
            secret = {"labels": labels or {}}
            secret_request = {"parent": parent, "secret_id": name, "secret": secret}

            try:
                secret_response = self.secret_manager_client.create_secret(
                    request=secret_request
                )
                logger.info(f"Secret created: {name}")
            except Exception:
                # Secret might already exist
                secret_response = self.secret_manager_client.get_secret(
                    request={"name": f"{parent}/secrets/{name}"}
                )

            # Add secret version
            version_request = {
                "parent": secret_response.name,
                "payload": {"data": value.encode("utf-8")},
            }

            self.secret_manager_client.add_secret_version(request=version_request)

            self._audit_event(
                event_type="secret_stored",
                action="store_secret",
                details={"secret_name": name},
            )

            logger.info(f"Secret stored: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to store secret {name}: {e}")
            return False

    def get_secret(self, name: str, version: str = "latest") -> Optional[str]:
        """
        Retrieve a secret from GCP Secret Manager.

        Args:
            name: Secret name
            version: Secret version

        Returns:
            Secret value or None if not found
        """
        if not self.secret_manager_client:
            logger.error("Secret Manager client not available")
            return None

        try:
            secret_name = (
                f"projects/{self.project_id}/secrets/{name}/versions/{version}"
            )
            response = self.secret_manager_client.access_secret_version(
                request={"name": secret_name}
            )

            secret_value = response.payload.data.decode("utf-8")

            self._audit_event(
                event_type="secret_accessed",
                action="get_secret",
                details={"secret_name": name, "version": version},
            )

            logger.info(f"Secret retrieved: {name}")
            return secret_value

        except Exception as e:
            logger.error(f"Failed to retrieve secret {name}: {e}")
            return None

    def hash_password(
        self, password: str, salt: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Hash a password with salt.

        Args:
            password: Password to hash
            salt: Optional salt (generated if not provided)

        Returns:
            Dictionary with hash and salt
        """
        if salt is None:
            salt = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")

        # Use PBKDF2 for password hashing

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,  # 100k iterations
        )

        hash_b64 = base64.urlsafe_b64encode(password_hash).decode("utf-8")

        return {"hash": hash_b64, "salt": salt}

    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """
        Verify a password against stored hash.

        Args:
            password: Password to verify
            stored_hash: Stored password hash
            salt: Salt used for hashing

        Returns:
            True if password is correct
        """
        hash_result = self.hash_password(password, salt)
        return hmac.compare_digest(hash_result["hash"], stored_hash)

    def _audit_event(
        self,
        event_type: str,
        action: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Record security audit event."""
        import uuid

        event = SecurityAuditEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            action=action,
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            details=details or {},
        )

        with self.security_lock:
            self.audit_events.append(event)
            # Keep only last 1000 events in memory
            if len(self.audit_events) > 1000:
                self.audit_events.pop(0)

        # Log audit event
        logger.info(
            f"Security audit: {event_type}",
            event_id=event.id,
            user_id=user_id,
            action=action,
            success=success,
            details=details,
        )

    def get_audit_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[SecurityAuditEvent]:
        """
        Get security audit events with optional filtering.

        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of events to return

        Returns:
            List of audit events
        """
        events = self.audit_events.copy()

        # Apply filters
        if user_id:
            events = [e for e in events if e.user_id == user_id]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if start_time:
            events = [e for e in events if e.timestamp >= start_time]

        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        # Sort by timestamp descending and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def revoke_token(self, token: str) -> bool:
        """
        Revoke a security token.

        Args:
            token: Token to revoke

        Returns:
            True if revoked successfully
        """
        with self.security_lock:
            if token in self.active_tokens:
                security_token = self.active_tokens[token]
                del self.active_tokens[token]

                self._audit_event(
                    event_type="token_revoked",
                    user_id=security_token.user_id,
                    action="revoke_token",
                    details={"token_type": security_token.token_type.value},
                )

                logger.info(f"Token revoked for user {security_token.user_id}")
                return True

        return False

    def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from active tokens.

        Returns:
            Number of tokens removed
        """
        now = datetime.utcnow()
        expired_tokens = []

        with self.security_lock:
            for token, security_token in self.active_tokens.items():
                if security_token.expires_at <= now:
                    expired_tokens.append(token)

            for token in expired_tokens:
                del self.active_tokens[token]

        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")

        return len(expired_tokens)

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on security manager.

        Returns:
            Health check results
        """
        try:
            health = {
                "status": "healthy",
                "crypto_available": HAS_CRYPTO,
                "gcp_security_available": HAS_GCP_SECURITY,
                "secret_manager_client": self.secret_manager_client is not None,
                "iam_client": self.iam_client is not None,
                "encryption_key": self.encryption_key is not None,
                "total_users": len(self.users),
                "total_roles": len(self.roles),
                "active_tokens": len(self.active_tokens),
                "audit_events": len(self.audit_events),
            }

            # Check for expired tokens
            expired_count = self.cleanup_expired_tokens()
            health["expired_tokens_cleaned"] = expired_count

            # Check recent authentication failures
            recent_failures = [
                e
                for e in self.audit_events[-50:]  # Last 50 events
                if e.event_type == "authentication_failed"
                and (datetime.utcnow() - e.timestamp).total_seconds()
                < 3600  # Last hour
            ]

            if len(recent_failures) > 10:  # More than 10 failures in last hour
                health["status"] = "degraded"
                health["recent_auth_failures"] = len(recent_failures)

            return health

        except Exception as e:
            logger.error(f"Security manager health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "crypto_available": HAS_CRYPTO,
                "gcp_security_available": HAS_GCP_SECURITY,
            }
