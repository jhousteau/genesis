"""
Cache Module

Unified caching abstraction supporting Redis, Memcached, and in-memory caching
with TTL, serialization, and distributed cache invalidation.
"""

import functools
import hashlib
import json
import pickle
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    import pymemcache
    from pymemcache.client.base import Client as MemcacheClient

    HAS_MEMCACHED = True
except ImportError:
    HAS_MEMCACHED = False

from ..config import RedisConfig
from ..logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class SerializationFormat(Enum):
    """Serialization formats for cache values."""

    PICKLE = "pickle"
    JSON = "json"
    STRING = "string"


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
        }


class Cache(ABC):
    """Abstract cache interface."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries."""
        pass

    @abstractmethod
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        pass


class InMemoryCache(Cache):
    """In-memory cache implementation with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats()

        logger.info(f"Initialized in-memory cache with max_size={max_size}")

    def _is_expired(self, key: str) -> bool:
        """Check if key is expired."""
        if key not in self._ttl:
            return False
        return time.time() > self._ttl[key]

    def _evict_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [key for key, ttl in self._ttl.items() if current_time > ttl]

        for key in expired_keys:
            self._remove_key(key)
            self._stats.evictions += 1

    def _evict_lru(self) -> None:
        """Remove least recently used entry."""
        if not self._access_times:
            return

        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        self._remove_key(lru_key)
        self._stats.evictions += 1

    def _remove_key(self, key: str) -> None:
        """Remove key from all internal structures."""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
        self._access_times.pop(key, None)

    def _ensure_capacity(self) -> None:
        """Ensure cache doesn't exceed max size."""
        self._evict_expired()

        while len(self._cache) >= self.max_size:
            self._evict_lru()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            if self._is_expired(key):
                self._remove_key(key)
                self._stats.misses += 1
                self._stats.evictions += 1
                return None

            self._access_times[key] = time.time()
            self._stats.hits += 1
            return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        with self._lock:
            self._ensure_capacity()

            self._cache[key] = value
            self._access_times[key] = time.time()

            # Set TTL
            effective_ttl = ttl if ttl is not None else self.default_ttl
            if effective_ttl is not None:
                self._ttl[key] = time.time() + effective_ttl
            elif key in self._ttl:
                # Remove TTL if not setting one
                del self._ttl[key]

            self._stats.sets += 1
            return True

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self._lock:
            if key in self._cache:
                self._remove_key(key)
                self._stats.deletes += 1
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        with self._lock:
            if key not in self._cache:
                return False

            if self._is_expired(key):
                self._remove_key(key)
                self._stats.evictions += 1
                return False

            return True

    def clear(self) -> bool:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
            self._ttl.clear()
            self._access_times.clear()
            return True

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    def get_size(self) -> int:
        """Get current cache size."""
        with self._lock:
            self._evict_expired()
            return len(self._cache)


class RedisCache(Cache):
    """Redis cache implementation."""

    def __init__(
        self,
        config: Optional[RedisConfig] = None,
        redis_client: Optional[redis.Redis] = None,
        serialization: SerializationFormat = SerializationFormat.PICKLE,
        key_prefix: str = "whitehorse:",
    ):
        if not HAS_REDIS:
            raise ImportError("Redis library not available")

        self.serialization = serialization
        self.key_prefix = key_prefix
        self._stats = CacheStats()

        if redis_client:
            self.client = redis_client
        elif config:
            self.client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                password=config.redis_password,
                db=config.redis_db,
                ssl=config.redis_ssl,
                max_connections=config.redis_max_connections,
                socket_timeout=config.redis_socket_timeout,
                decode_responses=False,  # We handle serialization ourselves
            )
        else:
            # Default Redis connection
            self.client = redis.Redis(decode_responses=False)

        try:
            self.client.ping()
            logger.info("Initialized Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.key_prefix}{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if self.serialization == SerializationFormat.PICKLE:
            return pickle.dumps(value)
        elif self.serialization == SerializationFormat.JSON:
            return json.dumps(value).encode("utf-8")
        elif self.serialization == SerializationFormat.STRING:
            if isinstance(value, str):
                return value.encode("utf-8")
            else:
                return str(value).encode("utf-8")
        else:
            raise ValueError(f"Unsupported serialization format: {self.serialization}")

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        if self.serialization == SerializationFormat.PICKLE:
            return pickle.loads(data)
        elif self.serialization == SerializationFormat.JSON:
            return json.loads(data.decode("utf-8"))
        elif self.serialization == SerializationFormat.STRING:
            return data.decode("utf-8")
        else:
            raise ValueError(f"Unsupported serialization format: {self.serialization}")

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            cache_key = self._make_key(key)
            data = self.client.get(cache_key)

            if data is None:
                self._stats.misses += 1
                return None

            value = self._deserialize(data)
            self._stats.hits += 1
            return value

        except Exception as e:
            logger.error(f"Redis get failed for key {key}: {e}")
            self._stats.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        try:
            cache_key = self._make_key(key)
            data = self._serialize(value)

            if ttl is not None:
                result = self.client.setex(cache_key, ttl, data)
            else:
                result = self.client.set(cache_key, data)

            if result:
                self._stats.sets += 1
                return True
            return False

        except Exception as e:
            logger.error(f"Redis set failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        try:
            cache_key = self._make_key(key)
            result = self.client.delete(cache_key)

            if result > 0:
                self._stats.deletes += 1
                return True
            return False

        except Exception as e:
            logger.error(f"Redis delete failed for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            cache_key = self._make_key(key)
            return self.client.exists(cache_key) > 0
        except Exception as e:
            logger.error(f"Redis exists failed for key {key}: {e}")
            return False

    def clear(self) -> bool:
        """Clear all cache entries with our prefix."""
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Redis clear failed: {e}")
            return False

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    def increment(
        self, key: str, amount: int = 1, ttl: Optional[int] = None
    ) -> Optional[int]:
        """Increment numeric value in cache."""
        try:
            cache_key = self._make_key(key)
            result = self.client.incr(cache_key, amount)

            if ttl is not None:
                self.client.expire(cache_key, ttl)

            return result
        except Exception as e:
            logger.error(f"Redis increment failed for key {key}: {e}")
            return None

    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        try:
            cache_key = self._make_key(key)
            return self.client.expire(cache_key, ttl)
        except Exception as e:
            logger.error(f"Redis expire failed for key {key}: {e}")
            return False


class MemcachedCache(Cache):
    """Memcached cache implementation."""

    def __init__(
        self,
        servers: List[str] = None,
        serialization: SerializationFormat = SerializationFormat.PICKLE,
    ):
        if not HAS_MEMCACHED:
            raise ImportError("Memcached library not available")

        self.serialization = serialization
        self._stats = CacheStats()

        servers = servers or ["localhost:11211"]
        self.client = MemcacheClient(
            servers[0]
        )  # pymemcache doesn't support multiple servers directly

        try:
            # Test connection
            self.client.stats()
            logger.info(f"Initialized Memcached cache: {servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Memcached: {e}")
            raise

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if self.serialization == SerializationFormat.PICKLE:
            return pickle.dumps(value)
        elif self.serialization == SerializationFormat.JSON:
            return json.dumps(value).encode("utf-8")
        elif self.serialization == SerializationFormat.STRING:
            return str(value).encode("utf-8")

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        if self.serialization == SerializationFormat.PICKLE:
            return pickle.loads(data)
        elif self.serialization == SerializationFormat.JSON:
            return json.loads(data.decode("utf-8"))
        elif self.serialization == SerializationFormat.STRING:
            return data.decode("utf-8")

    def get(self, key: str) -> Optional[Any]:
        """Get value from Memcached."""
        try:
            data = self.client.get(key)

            if data is None:
                self._stats.misses += 1
                return None

            value = self._deserialize(data)
            self._stats.hits += 1
            return value

        except Exception as e:
            logger.error(f"Memcached get failed for key {key}: {e}")
            self._stats.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Memcached."""
        try:
            data = self._serialize(value)
            result = self.client.set(key, data, expire=ttl or 0)

            if result:
                self._stats.sets += 1
                return True
            return False

        except Exception as e:
            logger.error(f"Memcached set failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from Memcached."""
        try:
            result = self.client.delete(key)

            if result:
                self._stats.deletes += 1
                return True
            return False

        except Exception as e:
            logger.error(f"Memcached delete failed for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in Memcached."""
        return self.get(key) is not None

    def clear(self) -> bool:
        """Clear all Memcached entries."""
        try:
            self.client.flush_all()
            return True
        except Exception as e:
            logger.error(f"Memcached clear failed: {e}")
            return False

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats


class CacheManager:
    """
    High-level cache management with fallback support.
    """

    def __init__(self, primary_cache: Cache, fallback_cache: Optional[Cache] = None):
        self.primary_cache = primary_cache
        self.fallback_cache = fallback_cache
        self._lock = threading.Lock()

        logger.info(
            f"Initialized cache manager with primary: {primary_cache.__class__.__name__}"
            + (
                f", fallback: {fallback_cache.__class__.__name__}"
                if fallback_cache
                else ""
            )
        )

    def get(self, key: str) -> Optional[Any]:
        """Get value with fallback support."""
        # Try primary cache first
        try:
            value = self.primary_cache.get(key)
            if value is not None:
                return value
        except Exception as e:
            logger.warning(f"Primary cache get failed for {key}: {e}")

        # Try fallback cache
        if self.fallback_cache:
            try:
                value = self.fallback_cache.get(key)
                if value is not None:
                    # Restore to primary cache
                    try:
                        self.primary_cache.set(key, value)
                    except Exception:
                        pass  # Ignore restoration failures
                    return value
            except Exception as e:
                logger.warning(f"Fallback cache get failed for {key}: {e}")

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in both caches."""
        primary_success = False
        fallback_success = False

        # Set in primary cache
        try:
            primary_success = self.primary_cache.set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Primary cache set failed for {key}: {e}")

        # Set in fallback cache
        if self.fallback_cache:
            try:
                fallback_success = self.fallback_cache.set(key, value, ttl)
            except Exception as e:
                logger.warning(f"Fallback cache set failed for {key}: {e}")

        return primary_success or fallback_success

    def delete(self, key: str) -> bool:
        """Delete from both caches."""
        primary_success = False
        fallback_success = False

        try:
            primary_success = self.primary_cache.delete(key)
        except Exception as e:
            logger.warning(f"Primary cache delete failed for {key}: {e}")

        if self.fallback_cache:
            try:
                fallback_success = self.fallback_cache.delete(key)
            except Exception as e:
                logger.warning(f"Fallback cache delete failed for {key}: {e}")

        return primary_success or fallback_success

    def exists(self, key: str) -> bool:
        """Check existence in either cache."""
        try:
            if self.primary_cache.exists(key):
                return True
        except Exception as e:
            logger.warning(f"Primary cache exists failed for {key}: {e}")

        if self.fallback_cache:
            try:
                return self.fallback_cache.exists(key)
            except Exception as e:
                logger.warning(f"Fallback cache exists failed for {key}: {e}")

        return False

    def clear(self) -> bool:
        """Clear both caches."""
        primary_success = False
        fallback_success = False

        try:
            primary_success = self.primary_cache.clear()
        except Exception as e:
            logger.warning(f"Primary cache clear failed: {e}")

        if self.fallback_cache:
            try:
                fallback_success = self.fallback_cache.clear()
            except Exception as e:
                logger.warning(f"Fallback cache clear failed: {e}")

        return primary_success or fallback_success

    def get_stats(self) -> Dict[str, CacheStats]:
        """Get statistics from both caches."""
        stats = {}

        try:
            stats["primary"] = self.primary_cache.get_stats()
        except Exception as e:
            logger.warning(f"Failed to get primary cache stats: {e}")

        if self.fallback_cache:
            try:
                stats["fallback"] = self.fallback_cache.get_stats()
            except Exception as e:
                logger.warning(f"Failed to get fallback cache stats: {e}")

        return stats


# Decorators for caching


def cached(
    cache: Optional[Cache] = None,
    ttl: Optional[int] = None,
    key_func: Optional[Callable] = None,
):
    """Decorator to cache function results."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache instance
            cache_instance = cache or get_cache()

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                args_str = ",".join(str(arg) for arg in args)
                kwargs_str = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_content = (
                    f"{func.__module__}.{func.__name__}({args_str},{kwargs_str})"
                )
                cache_key = hashlib.md5(key_content.encode()).hexdigest()

            # Try to get from cache
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}", cache_key=cache_key)
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {func.__name__}", cache_key=cache_key)

            return result

        return wrapper

    return decorator


def cache_invalidate(cache: Optional[Cache] = None, pattern: str = "*"):
    """Decorator to invalidate cache after function execution."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Invalidate cache
            cache_instance = cache or get_cache()
            if hasattr(cache_instance, "delete_pattern"):
                cache_instance.delete_pattern(pattern)
            else:
                # Fallback: clear entire cache
                cache_instance.clear()

            logger.debug(f"Invalidated cache after {func.__name__}", pattern=pattern)
            return result

        return wrapper

    return decorator


# Factory functions


def create_cache(cache_type: str, **kwargs) -> Cache:
    """
    Factory function to create cache instance.

    Args:
        cache_type: Type of cache ('memory', 'redis', 'memcached')
        **kwargs: Cache-specific configuration

    Returns:
        Cache instance
    """
    cache_type = cache_type.lower()

    if cache_type == "memory":
        return InMemoryCache(**kwargs)
    elif cache_type == "redis":
        return RedisCache(**kwargs)
    elif cache_type == "memcached":
        return MemcachedCache(**kwargs)
    else:
        raise ValueError(f"Unsupported cache type: {cache_type}")


# Global cache instance
_global_cache = None


def get_cache() -> Cache:
    """Get global cache instance."""
    global _global_cache
    if _global_cache is None:
        # Try Redis first, fallback to memory
        try:
            if HAS_REDIS:
                _global_cache = RedisCache()
            else:
                _global_cache = InMemoryCache()
        except Exception:
            _global_cache = InMemoryCache()

    return _global_cache


def set_cache(cache: Cache) -> None:
    """Set global cache instance."""
    global _global_cache
    _global_cache = cache
