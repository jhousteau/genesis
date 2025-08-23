"""
Genesis Secret Access Patterns - Secure Secret Access Implementation
SHIELD Methodology: Harden component for secure secret access patterns

Provides caching, access patterns, and security controls for secret retrieval.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class AccessLevel(Enum):
    """Secret access levels"""

    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"
    TOP_SECRET = "top_secret"


@dataclass
class CacheEntry:
    """Cache entry for secrets"""

    value: str
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: int = 300  # 5 minutes default

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.utcnow() > (
            self.created_at + timedelta(seconds=self.ttl_seconds)
        )

    def update_access(self) -> None:
        """Update access tracking"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


class SecretCache:
    """
    Secure cache for secrets with TTL and access controls
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self.logger = logging.getLogger("genesis.secrets.cache")

        # Cache statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _generate_key(self, secret_name: str, version: str = "latest") -> str:
        """Generate cache key"""
        return f"{secret_name}:{version}"

    def get(self, secret_name: str, version: str = "latest") -> Optional[str]:
        """
        Get secret from cache

        Args:
            secret_name: Name of the secret
            version: Secret version

        Returns:
            Cached secret value or None if not found/expired
        """
        with self._lock:
            key = self._generate_key(secret_name, version)

            if key in self._cache:
                entry = self._cache[key]

                if entry.is_expired():
                    # Remove expired entry
                    del self._cache[key]
                    self.misses += 1
                    self.logger.debug(f"Cache miss (expired): {secret_name}")
                    return None

                # Update access tracking
                entry.update_access()
                self.hits += 1
                self.logger.debug(f"Cache hit: {secret_name}")
                return entry.value

            self.misses += 1
            self.logger.debug(f"Cache miss: {secret_name}")
            return None

    def set(
        self,
        secret_name: str,
        version: str,
        value: str,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Set secret in cache

        Args:
            secret_name: Name of the secret
            version: Secret version
            value: Secret value
            ttl_seconds: Time to live in seconds
        """
        with self._lock:
            # Check cache size and evict if necessary
            if len(self._cache) >= self.max_size:
                self._evict_oldest()

            key = self._generate_key(secret_name, version)
            ttl = ttl_seconds or self.default_ttl

            entry = CacheEntry(
                value=value,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                ttl_seconds=ttl,
            )

            self._cache[key] = entry
            self.logger.debug(f"Cache set: {secret_name} (TTL: {ttl}s)")

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry"""
        if not self._cache:
            return

        # Find oldest entry by creation time
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        self.evictions += 1
        self.logger.debug(f"Evicted oldest cache entry: {oldest_key}")

    def invalidate(self, secret_name: str, version: str = "latest") -> bool:
        """
        Invalidate cached secret

        Args:
            secret_name: Name of the secret
            version: Secret version (default: "latest")

        Returns:
            True if entry was found and removed
        """
        with self._lock:
            key = self._generate_key(secret_name, version)

            if key in self._cache:
                del self._cache[key]
                self.logger.debug(f"Cache invalidated: {secret_name}")
                return True

            return False

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
            self.logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests) if total_requests > 0 else 0.0

            return {
                "cache_size": len(self._cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": hit_rate,
                "total_requests": total_requests,
            }

    def cleanup_expired(self) -> int:
        """Clean up expired cache entries"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                self.logger.debug(
                    f"Cleaned up {len(expired_keys)} expired cache entries"
                )

            return len(expired_keys)


class SecretAccessPattern:
    """
    Secure access patterns for secret retrieval with controls and validation
    """

    def __init__(self, secret_manager):
        self.secret_manager = secret_manager
        self.logger = logging.getLogger("genesis.secrets.access")
        self._access_controls: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register_access_control(
        self,
        secret_pattern: str,
        access_level: AccessLevel,
        allowed_services: Optional[List[str]] = None,
        allowed_environments: Optional[List[str]] = None,
        validator: Optional[Callable[[str], bool]] = None,
    ) -> None:
        """
        Register access control for secret patterns

        Args:
            secret_pattern: Secret name pattern (supports wildcards)
            access_level: Access level required
            allowed_services: List of allowed services (None = all)
            allowed_environments: List of allowed environments (None = all)
            validator: Custom validation function
        """
        with self._lock:
            self._access_controls[secret_pattern] = {
                "access_level": access_level,
                "allowed_services": allowed_services,
                "allowed_environments": allowed_environments,
                "validator": validator,
            }

            self.logger.info(f"Registered access control for pattern: {secret_pattern}")

    def secure_get_secret(
        self,
        secret_name: str,
        requesting_service: Optional[str] = None,
        environment: Optional[str] = None,
        use_cache: bool = True,
        **kwargs,
    ) -> str:
        """
        Securely get secret with access controls

        Args:
            secret_name: Name of the secret
            requesting_service: Service requesting the secret
            environment: Environment context
            use_cache: Whether to use cache
            **kwargs: Additional arguments passed to secret manager

        Returns:
            Secret value if access is allowed

        Raises:
            SecretAccessDeniedError: If access is denied
        """
        # Check access controls
        if not self._check_access_allowed(secret_name, requesting_service, environment):
            from .exceptions import SecretAccessDeniedError

            raise SecretAccessDeniedError(
                secret_name, "Access denied by access control policy"
            )

        # Log access attempt
        self.logger.info(
            f"Authorized secret access: {secret_name} by {requesting_service or 'unknown'}"
        )

        # Get secret through manager
        return self.secret_manager.get_secret(
            secret_name=secret_name, use_cache=use_cache, **kwargs
        )

    def _check_access_allowed(
        self,
        secret_name: str,
        requesting_service: Optional[str],
        environment: Optional[str],
    ) -> bool:
        """Check if access is allowed based on registered controls"""
        with self._lock:
            for pattern, controls in self._access_controls.items():
                if self._matches_pattern(secret_name, pattern):
                    # Check service restrictions
                    allowed_services = controls.get("allowed_services")
                    if allowed_services and requesting_service not in allowed_services:
                        self.logger.warning(
                            f"Service {requesting_service} not allowed for secret {secret_name}"
                        )
                        return False

                    # Check environment restrictions
                    allowed_environments = controls.get("allowed_environments")
                    if allowed_environments and environment not in allowed_environments:
                        self.logger.warning(
                            f"Environment {environment} not allowed for secret {secret_name}"
                        )
                        return False

                    # Run custom validator
                    validator = controls.get("validator")
                    if validator and not validator(secret_name):
                        self.logger.warning(
                            f"Custom validation failed for secret {secret_name}"
                        )
                        return False

                    # Access allowed
                    return True

            # No specific controls found, use default policy
            return True

    def _matches_pattern(self, secret_name: str, pattern: str) -> bool:
        """Check if secret name matches pattern (supports basic wildcards)"""
        if pattern == "*":
            return True

        if "*" in pattern:
            # Simple wildcard matching
            import fnmatch

            return fnmatch.fnmatch(secret_name, pattern)

        return secret_name == pattern

    def batch_get_secrets(
        self,
        secret_names: List[str],
        requesting_service: Optional[str] = None,
        environment: Optional[str] = None,
        use_cache: bool = True,
        fail_on_error: bool = False,
    ) -> Dict[str, Optional[str]]:
        """
        Get multiple secrets in batch with access controls

        Args:
            secret_names: List of secret names
            requesting_service: Service requesting the secrets
            environment: Environment context
            use_cache: Whether to use cache
            fail_on_error: Whether to fail if any secret cannot be accessed

        Returns:
            Dictionary mapping secret names to values (None for failed access)
        """
        results = {}
        errors = []

        for secret_name in secret_names:
            try:
                value = self.secure_get_secret(
                    secret_name=secret_name,
                    requesting_service=requesting_service,
                    environment=environment,
                    use_cache=use_cache,
                )
                results[secret_name] = value

            except Exception as e:
                results[secret_name] = None
                errors.append(f"{secret_name}: {str(e)}")

                if fail_on_error:
                    from .exceptions import SecretError

                    raise SecretError(
                        f"Batch secret retrieval failed: {'; '.join(errors)}"
                    )

        if errors:
            self.logger.warning(f"Batch retrieval had errors: {'; '.join(errors)}")

        return results

    def get_secret_with_fallback(
        self,
        primary_secret: str,
        fallback_secrets: List[str],
        requesting_service: Optional[str] = None,
        environment: Optional[str] = None,
        use_cache: bool = True,
    ) -> Optional[str]:
        """
        Get secret with fallback options

        Args:
            primary_secret: Primary secret name
            fallback_secrets: List of fallback secret names
            requesting_service: Service requesting the secret
            environment: Environment context
            use_cache: Whether to use cache

        Returns:
            Secret value from primary or first available fallback
        """
        # Try primary secret first
        try:
            return self.secure_get_secret(
                secret_name=primary_secret,
                requesting_service=requesting_service,
                environment=environment,
                use_cache=use_cache,
            )
        except Exception as e:
            self.logger.warning(f"Primary secret {primary_secret} failed: {e}")

        # Try fallback secrets
        for fallback in fallback_secrets:
            try:
                value = self.secure_get_secret(
                    secret_name=fallback,
                    requesting_service=requesting_service,
                    environment=environment,
                    use_cache=use_cache,
                )

                self.logger.info(f"Used fallback secret: {fallback}")
                return value

            except Exception as e:
                self.logger.warning(f"Fallback secret {fallback} failed: {e}")
                continue

        # All secrets failed
        self.logger.error(f"All secrets failed: {primary_secret}, {fallback_secrets}")
        return None

    def create_secret_group(
        self,
        group_name: str,
        secret_names: List[str],
        access_level: AccessLevel = AccessLevel.INTERNAL,
    ) -> None:
        """
        Create a logical group of secrets with shared access controls

        Args:
            group_name: Name of the secret group
            secret_names: List of secret names in the group
            access_level: Access level for the entire group
        """
        # Register access control for each secret in the group
        for secret_name in secret_names:
            self.register_access_control(
                secret_pattern=secret_name,
                access_level=access_level,
            )

        self.logger.info(
            f"Created secret group: {group_name} with {len(secret_names)} secrets"
        )

    def get_access_control_summary(self) -> Dict[str, Any]:
        """Get summary of access controls"""
        with self._lock:
            summary = {
                "total_patterns": len(self._access_controls),
                "patterns": [],
            }

            for pattern, controls in self._access_controls.items():
                pattern_info = {
                    "pattern": pattern,
                    "access_level": controls["access_level"].value,
                    "allowed_services": controls.get("allowed_services"),
                    "allowed_environments": controls.get("allowed_environments"),
                    "has_validator": controls.get("validator") is not None,
                }
                summary["patterns"].append(pattern_info)

            return summary
