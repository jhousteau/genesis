"""
Cache Service
Multi-level caching service for performance optimization following CRAFT methodology.
"""

import json
import time
import threading
from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    value: Any
    created_at: datetime
    ttl_seconds: int
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds <= 0:
            return False  # No expiration

        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)

    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class CacheService:
    """
    Multi-level caching service implementing CRAFT performance optimization.

    Create: Robust caching architecture
    Refactor: Optimized for performance
    Authenticate: Secure cache isolation
    Function: Reliable cache operations
    Test: Comprehensive cache validation
    """

    def __init__(self, config_service):
        self.config_service = config_service
        self.perf_config = config_service.get_performance_config()

        # L1 Cache - In-memory (fastest)
        self._l1_cache: Dict[str, CacheEntry] = {}
        self._l1_lock = threading.RLock()

        # Cache configuration
        self.default_ttl = self.perf_config.get("cache", {}).get("ttl", 300)
        self.max_entries = self.perf_config.get("cache", {}).get("max_entries", 1000)

        # Statistics
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "evictions": 0}

        # Start background cleanup
        self._cleanup_thread = threading.Thread(
            target=self._background_cleanup, daemon=True
        )
        self._cleanup_thread.start()

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with L1 lookup."""
        cache_key = self._normalize_key(key)

        with self._l1_lock:
            entry = self._l1_cache.get(cache_key)

            if entry is None:
                self._stats["misses"] += 1
                return default

            if entry.is_expired():
                del self._l1_cache[cache_key]
                self._stats["misses"] += 1
                return default

            entry.touch()
            self._stats["hits"] += 1
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Set value in cache with optional TTL and tags."""
        cache_key = self._normalize_key(key)
        ttl = ttl if ttl is not None else self.default_ttl
        tags = tags or []

        with self._l1_lock:
            # Ensure we don't exceed max entries
            if len(self._l1_cache) >= self.max_entries:
                self._evict_lru()

            entry = CacheEntry(
                key=cache_key,
                value=value,
                created_at=datetime.now(),
                ttl_seconds=ttl,
                tags=tags,
            )

            self._l1_cache[cache_key] = entry
            self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        cache_key = self._normalize_key(key)

        with self._l1_lock:
            if cache_key in self._l1_cache:
                del self._l1_cache[cache_key]
                self._stats["deletes"] += 1
                return True
            return False

    def delete_by_tags(self, tags: List[str]) -> int:
        """Delete all entries with specified tags."""
        deleted_count = 0

        with self._l1_lock:
            keys_to_delete = []

            for key, entry in self._l1_cache.items():
                if any(tag in entry.tags for tag in tags):
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self._l1_cache[key]
                deleted_count += 1
                self._stats["deletes"] += 1

        return deleted_count

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        cache_key = self._normalize_key(key)

        with self._l1_lock:
            entry = self._l1_cache.get(cache_key)
            return entry is not None and not entry.is_expired()

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._l1_lock:
            cleared_count = len(self._l1_cache)
            self._l1_cache.clear()
            self._stats["deletes"] += cleared_count

    def get_or_set(
        self,
        key: str,
        factory_func,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Any:
        """Get value from cache or set it using factory function."""
        cached_value = self.get(key)

        if cached_value is not None:
            return cached_value

        # Generate value and cache it
        value = factory_func()
        self.set(key, value, ttl, tags)
        return value

    def increment(self, key: str, delta: int = 1, ttl: Optional[int] = None) -> int:
        """Increment a numeric value in cache."""
        cache_key = self._normalize_key(key)

        with self._l1_lock:
            entry = self._l1_cache.get(cache_key)

            if entry is None or entry.is_expired():
                new_value = delta
            else:
                try:
                    new_value = int(entry.value) + delta
                except (ValueError, TypeError):
                    new_value = delta

            self.set(key, new_value, ttl)
            return new_value

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._l1_lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                (self._stats["hits"] / total_requests) if total_requests > 0 else 0
            )

            return {
                **self._stats,
                "hit_rate": hit_rate,
                "total_entries": len(self._l1_cache),
                "memory_usage": self._estimate_memory_usage(),
            }

    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all cache keys, optionally filtered by pattern."""
        with self._l1_lock:
            keys = list(self._l1_cache.keys())

            if pattern:
                import fnmatch

                keys = [key for key in keys if fnmatch.fnmatch(key, pattern)]

            return keys

    def get_entries_info(self) -> List[Dict[str, Any]]:
        """Get information about all cache entries."""
        with self._l1_lock:
            entries_info = []

            for entry in self._l1_cache.values():
                entries_info.append(
                    {
                        "key": entry.key,
                        "created_at": entry.created_at.isoformat(),
                        "ttl_seconds": entry.ttl_seconds,
                        "access_count": entry.access_count,
                        "last_accessed": (
                            entry.last_accessed.isoformat()
                            if entry.last_accessed
                            else None
                        ),
                        "tags": entry.tags,
                        "is_expired": entry.is_expired(),
                        "size_estimate": len(str(entry.value)) if entry.value else 0,
                    }
                )

            return entries_info

    def _normalize_key(self, key: str) -> str:
        """Normalize cache key to ensure consistency."""
        # Add namespace prefix to avoid conflicts
        project_id = self.config_service.project_id or "default"
        environment = self.config_service.environment

        normalized = f"genesis:{project_id}:{environment}:{key}"

        # Hash very long keys to avoid memory issues
        if len(normalized) > 250:
            hash_obj = hashlib.sha256(normalized.encode())
            normalized = f"genesis:hash:{hash_obj.hexdigest()}"

        return normalized

    def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        if not self._l1_cache:
            return

        # Sort by last accessed time (oldest first)
        entries_by_age = sorted(
            self._l1_cache.items(), key=lambda x: x[1].last_accessed or x[1].created_at
        )

        # Remove oldest 10% of entries
        evict_count = max(1, len(entries_by_age) // 10)

        for i in range(evict_count):
            key, _ = entries_by_age[i]
            del self._l1_cache[key]
            self._stats["evictions"] += 1

    def _background_cleanup(self) -> None:
        """Background thread to clean up expired entries."""
        while True:
            try:
                time.sleep(60)  # Run every minute

                with self._l1_lock:
                    expired_keys = []

                    for key, entry in self._l1_cache.items():
                        if entry.is_expired():
                            expired_keys.append(key)

                    for key in expired_keys:
                        del self._l1_cache[key]
                        self._stats["evictions"] += 1

                if expired_keys:
                    logger.debug(
                        f"Cleaned up {len(expired_keys)} expired cache entries"
                    )

            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of cache in bytes."""
        total_size = 0

        for entry in self._l1_cache.values():
            # Rough estimate of entry size
            total_size += len(str(entry.key)) * 2  # Unicode chars
            total_size += len(str(entry.value)) * 2
            total_size += 200  # Overhead for entry metadata

        return total_size

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear()
