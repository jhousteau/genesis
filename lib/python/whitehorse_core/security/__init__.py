"""
Security Module

Comprehensive security utilities including secrets management, encryption,
authentication, authorization, and GCP integration.
"""

import base64
import hashlib
import hmac
import os
import secrets
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import jwt

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

try:
    from google.auth import default as gcp_default
    from google.auth.transport.requests import Request
    from google.cloud import secretmanager

    HAS_GCP_AUTH = True
except ImportError:
    HAS_GCP_AUTH = False

from ..errors import (AuthenticationError, AuthorizationError,
                      ConfigurationError)
from ..logging import get_logger

logger = get_logger(__name__)


class Permission(Enum):
    """Standard permission types."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"


@dataclass
class User:
    """User representation."""

    id: str
    email: str
    name: str
    roles: List[str]
    permissions: List[str]
    metadata: Optional[Dict[str, Any]] = None

    def has_permission(self, permission: Union[str, Permission]) -> bool:
        """Check if user has specific permission."""
        perm_str = (
            permission.value if isinstance(permission, Permission) else permission
        )
        return perm_str in self.permissions or "admin" in self.permissions

    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles


@dataclass
class Token:
    """Authentication token."""

    value: str
    user_id: str
    expires_at: float
    token_type: str = "bearer"
    scopes: Optional[List[str]] = None

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return time.time() > self.expires_at

    @property
    def expires_in(self) -> float:
        """Get seconds until expiration."""
        return max(0, self.expires_at - time.time())


class SecretStore(ABC):
    """Abstract base class for secret storage."""

    @abstractmethod
    def get_secret(self, name: str) -> Optional[str]:
        """Retrieve a secret by name."""
        pass

    @abstractmethod
    def set_secret(self, name: str, value: str) -> bool:
        """Store a secret."""
        pass

    @abstractmethod
    def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        pass

    @abstractmethod
    def list_secrets(self) -> List[str]:
        """List all secret names."""
        pass


class GCPSecretStore(SecretStore):
    """GCP Secret Manager implementation."""

    def __init__(self, project_id: Optional[str] = None):
        if not HAS_GCP_AUTH:
            raise ConfigurationError("GCP libraries not available")

        self.project_id = project_id or os.environ.get("GCP_PROJECT")
        if not self.project_id:
            raise ConfigurationError("GCP project ID not provided")

        try:
            self.client = secretmanager.SecretManagerServiceClient()
            logger.info("Initialized GCP Secret Manager", project=self.project_id)
        except Exception as e:
            logger.error(f"Failed to initialize GCP Secret Manager: {e}")
            raise ConfigurationError(f"GCP Secret Manager initialization failed: {e}")

    def get_secret(self, name: str, version: str = "latest") -> Optional[str]:
        """Retrieve secret from GCP Secret Manager."""
        try:
            secret_path = (
                f"projects/{self.project_id}/secrets/{name}/versions/{version}"
            )
            response = self.client.access_secret_version(request={"name": secret_path})
            secret_value = response.payload.data.decode("UTF-8")
            logger.debug("Retrieved secret from GCP Secret Manager", secret=name)
            return secret_value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {name}: {e}")
            return None

    def set_secret(self, name: str, value: str) -> bool:
        """Store secret in GCP Secret Manager."""
        try:
            parent = f"projects/{self.project_id}"

            # Create secret if it doesn't exist
            try:
                secret = self.client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": name,
                        "secret": {"replication": {"automatic": {}}},
                    }
                )
                logger.info(f"Created new secret {name}")
            except Exception:
                # Secret already exists
                secret = f"{parent}/secrets/{name}"

            # Add secret version
            self.client.add_secret_version(
                request={"parent": secret, "payload": {"data": value.encode("UTF-8")}}
            )

            logger.info("Stored secret in GCP Secret Manager", secret=name)
            return True
        except Exception as e:
            logger.error(f"Failed to store secret {name}: {e}")
            return False

    def delete_secret(self, name: str) -> bool:
        """Delete secret from GCP Secret Manager."""
        try:
            secret_path = f"projects/{self.project_id}/secrets/{name}"
            self.client.delete_secret(request={"name": secret_path})
            logger.info("Deleted secret from GCP Secret Manager", secret=name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            return False

    def list_secrets(self) -> List[str]:
        """List all secrets in GCP Secret Manager."""
        try:
            parent = f"projects/{self.project_id}"
            secrets = self.client.list_secrets(request={"parent": parent})
            secret_names = [secret.name.split("/")[-1] for secret in secrets]
            logger.debug(
                "Listed secrets from GCP Secret Manager", count=len(secret_names)
            )
            return secret_names
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []


class FileSecretStore(SecretStore):
    """File-based secret storage (for development)."""

    def __init__(self, secrets_dir: str = ".secrets"):
        self.secrets_dir = Path(secrets_dir)
        self.secrets_dir.mkdir(exist_ok=True, mode=0o700)
        logger.info(f"Initialized file secret store: {self.secrets_dir}")

    def get_secret(self, name: str) -> Optional[str]:
        """Retrieve secret from file."""
        try:
            secret_file = self.secrets_dir / f"{name}.secret"
            if secret_file.exists():
                return secret_file.read_text().strip()
            return None
        except Exception as e:
            logger.error(f"Failed to read secret {name}: {e}")
            return None

    def set_secret(self, name: str, value: str) -> bool:
        """Store secret to file."""
        try:
            secret_file = self.secrets_dir / f"{name}.secret"
            secret_file.write_text(value)
            secret_file.chmod(0o600)
            logger.debug("Stored secret to file", secret=name)
            return True
        except Exception as e:
            logger.error(f"Failed to store secret {name}: {e}")
            return False

    def delete_secret(self, name: str) -> bool:
        """Delete secret file."""
        try:
            secret_file = self.secrets_dir / f"{name}.secret"
            if secret_file.exists():
                secret_file.unlink()
                logger.debug("Deleted secret file", secret=name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            return False

    def list_secrets(self) -> List[str]:
        """List all secret files."""
        try:
            return [f.stem for f in self.secrets_dir.glob("*.secret")]
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []


class MemorySecretStore(SecretStore):
    """In-memory secret storage (for testing)."""

    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._lock = threading.Lock()

    def get_secret(self, name: str) -> Optional[str]:
        """Retrieve secret from memory."""
        with self._lock:
            return self._secrets.get(name)

    def set_secret(self, name: str, value: str) -> bool:
        """Store secret in memory."""
        with self._lock:
            self._secrets[name] = value
            return True

    def delete_secret(self, name: str) -> bool:
        """Delete secret from memory."""
        with self._lock:
            if name in self._secrets:
                del self._secrets[name]
            return True

    def list_secrets(self) -> List[str]:
        """List all secrets in memory."""
        with self._lock:
            return list(self._secrets.keys())


class Encryption:
    """Encryption utilities using Fernet symmetric encryption."""

    def __init__(self, key: Optional[bytes] = None):
        if not HAS_CRYPTOGRAPHY:
            raise ConfigurationError("Cryptography library not available")

        if key is None:
            key = Fernet.generate_key()

        self.fernet = Fernet(key)
        self.key = key

    @classmethod
    def from_password(cls, password: str, salt: Optional[bytes] = None) -> "Encryption":
        """Create encryption instance from password."""
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return cls(key)

    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """Encrypt data."""
        if isinstance(data, str):
            data = data.encode()
        return self.fernet.encrypt(data)

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data."""
        return self.fernet.decrypt(encrypted_data)

    def encrypt_string(self, text: str) -> str:
        """Encrypt string and return base64 encoded result."""
        encrypted = self.encrypt(text)
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt base64 encoded string."""
        encrypted_data = base64.urlsafe_b64decode(encrypted_text.encode())
        decrypted = self.decrypt(encrypted_data)
        return decrypted.decode()


class APIKeyManager:
    """API key generation and validation."""

    def __init__(self, secret_store: SecretStore):
        self.secret_store = secret_store

    def generate_api_key(self, user_id: str, expires_in: int = 86400) -> str:
        """Generate API key for user."""
        # Generate random key
        key_bytes = secrets.token_bytes(32)
        api_key = base64.urlsafe_b64encode(key_bytes).decode().rstrip("=")

        # Store key with metadata
        key_data = {
            "user_id": user_id,
            "created_at": time.time(),
            "expires_at": time.time() + expires_in,
            "active": True,
        }

        self.secret_store.set_secret(f"api_key_{api_key[:8]}", str(key_data))
        logger.info("Generated API key", user_id=user_id, key_prefix=api_key[:8])
        return api_key

    def validate_api_key(self, api_key: str) -> Optional[str]:
        """Validate API key and return user ID."""
        try:
            key_prefix = api_key[:8]
            key_data_str = self.secret_store.get_secret(f"api_key_{key_prefix}")

            if not key_data_str:
                return None

            key_data = eval(key_data_str)  # In production, use proper JSON

            # Check if key is active and not expired
            if not key_data.get("active"):
                return None

            if time.time() > key_data.get("expires_at", 0):
                return None

            return key_data.get("user_id")
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return None

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke API key."""
        try:
            key_prefix = api_key[:8]
            return self.secret_store.delete_secret(f"api_key_{key_prefix}")
        except Exception as e:
            logger.error(f"Failed to revoke API key: {e}")
            return False


class JWTManager:
    """JWT token management."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(
        self,
        user_id: str,
        expires_in: int = 3600,
        scopes: Optional[List[str]] = None,
        **claims,
    ) -> Token:
        """Create JWT token."""
        now = time.time()
        expires_at = now + expires_in

        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expires_at,
            "scopes": scopes or [],
            **claims,
        }

        token_value = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return Token(
            value=token_value, user_id=user_id, expires_at=expires_at, scopes=scopes
        )

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    def refresh_token(self, token: str, expires_in: int = 3600) -> Optional[Token]:
        """Refresh JWT token."""
        payload = self.validate_token(token)
        if not payload:
            return None

        return self.create_token(
            user_id=payload["sub"],
            expires_in=expires_in,
            scopes=payload.get("scopes", []),
        )


class RoleBasedAccessControl:
    """Role-based access control system."""

    def __init__(self):
        self.roles: Dict[str, List[str]] = {}
        self.user_roles: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def define_role(self, role: str, permissions: List[str]) -> None:
        """Define a role with permissions."""
        with self._lock:
            self.roles[role] = permissions
            logger.info(f"Defined role: {role} with {len(permissions)} permissions")

    def assign_role(self, user_id: str, role: str) -> None:
        """Assign role to user."""
        with self._lock:
            if user_id not in self.user_roles:
                self.user_roles[user_id] = []
            if role not in self.user_roles[user_id]:
                self.user_roles[user_id].append(role)
                logger.info(f"Assigned role {role} to user {user_id}")

    def revoke_role(self, user_id: str, role: str) -> None:
        """Revoke role from user."""
        with self._lock:
            if user_id in self.user_roles and role in self.user_roles[user_id]:
                self.user_roles[user_id].remove(role)
                logger.info(f"Revoked role {role} from user {user_id}")

    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for user based on roles."""
        with self._lock:
            user_roles = self.user_roles.get(user_id, [])
            permissions = set()

            for role in user_roles:
                role_permissions = self.roles.get(role, [])
                permissions.update(role_permissions)

            return list(permissions)

    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission."""
        user_permissions = self.get_user_permissions(user_id)
        return permission in user_permissions or "admin" in user_permissions


class SecurityManager:
    """Central security management."""

    def __init__(
        self,
        secret_store: Optional[SecretStore] = None,
        jwt_secret: Optional[str] = None,
    ):
        # Initialize secret store
        if secret_store is None:
            try:
                self.secret_store = GCPSecretStore()
            except (ConfigurationError, Exception):
                logger.warning("GCP Secret Manager not available, using file store")
                self.secret_store = FileSecretStore()
        else:
            self.secret_store = secret_store

        # Initialize JWT manager
        if jwt_secret is None:
            jwt_secret = self.secret_store.get_secret("jwt_secret")
            if jwt_secret is None:
                jwt_secret = secrets.token_urlsafe(32)
                self.secret_store.set_secret("jwt_secret", jwt_secret)
                logger.info("Generated new JWT secret")

        self.jwt_manager = JWTManager(jwt_secret)
        self.api_key_manager = APIKeyManager(self.secret_store)
        self.rbac = RoleBasedAccessControl()

        # Setup default roles
        self._setup_default_roles()

    def _setup_default_roles(self):
        """Setup default RBAC roles."""
        self.rbac.define_role("admin", ["read", "write", "delete", "admin", "execute"])
        self.rbac.define_role("editor", ["read", "write"])
        self.rbac.define_role("viewer", ["read"])

    def authenticate_jwt(self, token: str) -> Optional[User]:
        """Authenticate user via JWT token."""
        payload = self.jwt_manager.validate_token(token)
        if not payload:
            raise AuthenticationError("Invalid or expired token")

        user_id = payload["sub"]
        permissions = self.rbac.get_user_permissions(user_id)
        roles = self.rbac.user_roles.get(user_id, [])

        return User(
            id=user_id,
            email=payload.get("email", ""),
            name=payload.get("name", ""),
            roles=roles,
            permissions=permissions,
            metadata=payload,
        )

    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate user via API key."""
        user_id = self.api_key_manager.validate_api_key(api_key)
        if not user_id:
            raise AuthenticationError("Invalid API key")

        permissions = self.rbac.get_user_permissions(user_id)
        roles = self.rbac.user_roles.get(user_id, [])

        return User(
            id=user_id,
            email="",  # Would need to fetch from user store
            name="",
            roles=roles,
            permissions=permissions,
        )

    def authorize(
        self, user: User, permission: str, resource: Optional[str] = None
    ) -> bool:
        """Authorize user action."""
        if user.has_permission("admin"):
            return True

        if not user.has_permission(permission):
            raise AuthorizationError(f"Permission denied: {permission}")

        # Resource-specific authorization logic would go here
        return True

    def hash_password(self, password: str) -> str:
        """Hash password securely."""
        salt = secrets.token_hex(16)
        pwdhash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100000
        )
        return f"{salt}${pwdhash.hex()}"

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            salt, pwdhash = hashed.split("$")
            computed_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), 100000
            )
            return hmac.compare_digest(pwdhash, computed_hash.hex())
        except Exception:
            return False


# Global security manager instance
_security_manager = None


def get_security_manager() -> SecurityManager:
    """Get global security manager instance."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager
