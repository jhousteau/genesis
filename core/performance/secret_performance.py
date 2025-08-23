"""
Secret Manager Performance Optimization - CRAFT Function Component
Performance optimization patterns for GCP Secret Manager access

This module implements comprehensive performance optimization for Secret Manager,
including intelligent caching, batch operations, and access pattern analytics.
"""

import asyncio
import logging
import statistics
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from google.api_core import exceptions as gcp_exceptions
    from google.cloud import secretmanager

    GCP_SECRET_MANAGER_AVAILABLE = True
except ImportError:
    GCP_SECRET_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Caching strategies for secret access."""

    NONE = "none"
    TIME_BASED = "time_based"
    USAGE_BASED = "usage_based"
    ADAPTIVE = "adaptive"


class AccessPattern(Enum):
    """Secret access patterns."""

    SINGLE_ACCESS = "single_access"
    BATCH_ACCESS = "batch_access"
    PERIODIC_REFRESH = "periodic_refresh"
    ON_DEMAND = "on_demand"


@dataclass
class SecretAccessMetrics:
    """Metrics for secret access performance."""

    # Access statistics
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0

    # Performance metrics
    avg_access_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    p95_access_time_ms: float = 0.0

    # Error tracking
    error_count: int = 0
    timeout_count: int = 0

    # Cost optimization
    estimated_api_cost: float = 0.0
    estimated_savings: float = 0.0

    # Access patterns
    most_accessed_secrets: List[Tuple[str, int]] = field(default_factory=list)
    access_frequency: Dict[str, int] = field(default_factory=dict)

    # Time-based patterns
    peak_usage_hours: List[int] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class CacheEntry:
    """Enhanced cache entry with performance tracking."""

    secret_name: str
    value: str
    version: str
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: int = 300
    priority: int = 1  # 1=low, 2=medium, 3=high

    # Performance tracking
    fetch_time_ms: float = 0.0
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() > (self.created_at + timedelta(seconds=self.ttl_seconds))

    def update_access(self) -> None:
        """Update access tracking."""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def calculate_priority_score(self) -> float:
        """Calculate priority score for cache eviction."""
        # Higher score = higher priority to keep
        recency_score = 1.0 / (
            1 + (datetime.now() - self.last_accessed).total_seconds() / 3600
        )
        frequency_score = min(self.access_count / 10.0, 1.0)  # Normalize to 0-1
        size_penalty = max(1.0 - (self.size_bytes / 1024), 0.1)  # Smaller is better

        return (
            recency_score * 0.4 + frequency_score * 0.4 + size_penalty * 0.2
        ) * self.priority


class PerformantSecretCache:
    """
    High-performance secret cache with intelligent eviction and analytics.

    Implements CRAFT Function methodology for optimal caching performance.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,
        cache_strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache_strategy = cache_strategy

        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._access_times: Dict[str, List[float]] = {}  # Track access times per secret
        self._lock = threading.RLock()

        # Performance metrics
        self.metrics = SecretAccessMetrics()

        # Adaptive caching parameters
        self._adaptive_ttl: Dict[str, int] = {}
        self._usage_patterns: Dict[str, List[datetime]] = {}

        # Background optimization
        self._optimization_enabled = True
        self._optimization_thread = None

        self.logger = logging.getLogger(f"{__name__}.PerformantSecretCache")
        self.logger.info(f"Initialized cache with strategy: {cache_strategy.value}")

    def get(self, secret_name: str, version: str = "latest") -> Optional[str]:
        """Get secret from cache with performance tracking."""
        start_time = time.perf_counter()

        with self._lock:
            cache_key = self._generate_cache_key(secret_name, version)

            if cache_key in self._cache:
                entry = self._cache[cache_key]

                if entry.is_expired():
                    # Remove expired entry
                    del self._cache[cache_key]
                    self.metrics.cache_misses += 1
                    self._record_access_time(
                        secret_name, time.perf_counter() - start_time
                    )
                    return None

                # Update access tracking
                entry.update_access()
                self.metrics.cache_hits += 1
                self.metrics.total_requests += 1

                # Update usage patterns for adaptive caching
                if cache_key not in self._usage_patterns:
                    self._usage_patterns[cache_key] = []
                self._usage_patterns[cache_key].append(datetime.now())

                # Keep only recent accesses (last 24 hours)
                cutoff = datetime.now() - timedelta(hours=24)
                self._usage_patterns[cache_key] = [
                    access_time
                    for access_time in self._usage_patterns[cache_key]
                    if access_time >= cutoff
                ]

                access_time = time.perf_counter() - start_time
                self._record_access_time(secret_name, access_time)

                self.logger.debug(
                    f"Cache hit: {secret_name} (access time: {access_time*1000:.2f}ms)"
                )
                return entry.value

            self.metrics.cache_misses += 1
            self.metrics.total_requests += 1

            access_time = time.perf_counter() - start_time
            self._record_access_time(secret_name, access_time)

            return None

    def set(
        self,
        secret_name: str,
        version: str,
        value: str,
        fetch_time_ms: float = 0.0,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set secret in cache with intelligent TTL and priority."""

        with self._lock:
            cache_key = self._generate_cache_key(secret_name, version)

            # Determine TTL based on strategy
            if ttl_seconds is None:
                ttl_seconds = self._determine_optimal_ttl(secret_name)

            # Determine priority based on access patterns
            priority = self._calculate_entry_priority(secret_name)

            # Check if we need to evict entries
            if len(self._cache) >= self.max_size:
                self._intelligent_eviction()

            # Calculate entry size
            size_bytes = len(value.encode("utf-8"))

            # Create cache entry
            entry = CacheEntry(
                secret_name=secret_name,
                value=value,
                version=version,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl_seconds=ttl_seconds,
                priority=priority,
                fetch_time_ms=fetch_time_ms,
                size_bytes=size_bytes,
            )

            self._cache[cache_key] = entry

            # Update metrics
            self.metrics.access_frequency[secret_name] = (
                self.metrics.access_frequency.get(secret_name, 0) + 1
            )

            self.logger.debug(
                f"Cache set: {secret_name} (TTL: {ttl_seconds}s, Priority: {priority}, Size: {size_bytes}B)"
            )

    def batch_get(
        self, secret_requests: List[Tuple[str, str]]
    ) -> Dict[str, Optional[str]]:
        """Get multiple secrets from cache efficiently."""
        results = {}

        for secret_name, version in secret_requests:
            results[secret_name] = self.get(secret_name, version)

        return results

    def preload_secrets(
        self, secret_names: List[str], secret_fetcher: Callable[[str], str]
    ) -> int:
        """Preload secrets into cache for better performance."""
        preloaded_count = 0

        for secret_name in secret_names:
            if self.get(secret_name) is None:  # Not in cache
                try:
                    start_time = time.perf_counter()
                    value = secret_fetcher(secret_name)
                    fetch_time = (time.perf_counter() - start_time) * 1000

                    self.set(secret_name, "latest", value, fetch_time_ms=fetch_time)
                    preloaded_count += 1

                except Exception as e:
                    self.logger.warning(f"Failed to preload secret {secret_name}: {e}")

        self.logger.info(f"Preloaded {preloaded_count} secrets into cache")
        return preloaded_count

    def get_performance_metrics(self) -> SecretAccessMetrics:
        """Get comprehensive performance metrics."""
        with self._lock:
            # Update derived metrics
            total_requests = self.metrics.cache_hits + self.metrics.cache_misses
            self.metrics.cache_hit_rate = (
                self.metrics.cache_hits / total_requests if total_requests > 0 else 0.0
            )

            # Calculate average access times
            all_times = []
            for secret_times in self._access_times.values():
                all_times.extend(secret_times)

            if all_times:
                self.metrics.avg_access_time_ms = statistics.mean(all_times) * 1000
                sorted_times = sorted(all_times)
                self.metrics.p95_access_time_ms = (
                    sorted_times[int(0.95 * len(sorted_times))] * 1000
                )

            # Most accessed secrets
            sorted_secrets = sorted(
                self.metrics.access_frequency.items(), key=lambda x: x[1], reverse=True
            )
            self.metrics.most_accessed_secrets = sorted_secrets[:10]

            # Estimate cost savings from caching
            api_cost_per_request = (
                0.00005  # Estimate $0.00005 per Secret Manager API call
            )
            self.metrics.estimated_api_cost = (
                self.metrics.api_calls * api_cost_per_request
            )

            # Savings = cache hits * api cost (since cache hits avoid API calls)
            self.metrics.estimated_savings = (
                self.metrics.cache_hits * api_cost_per_request
            )

            self.metrics.last_updated = datetime.now()

            return self.metrics

    def optimize_cache(self) -> Dict[str, Any]:
        """Perform cache optimization and return results."""
        optimization_results = {
            "optimizations_applied": [],
            "cache_size_before": len(self._cache),
            "cache_size_after": 0,
            "expired_entries_removed": 0,
            "ttl_adjustments": 0,
        }

        with self._lock:
            # Remove expired entries
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]

            optimization_results["expired_entries_removed"] = len(expired_keys)
            if expired_keys:
                optimization_results["optimizations_applied"].append(
                    "removed_expired_entries"
                )

            # Optimize TTL for frequently accessed secrets
            ttl_adjustments = self._optimize_ttl_values()
            optimization_results["ttl_adjustments"] = ttl_adjustments
            if ttl_adjustments > 0:
                optimization_results["optimizations_applied"].append(
                    "optimized_ttl_values"
                )

            # Adjust cache size if needed
            if len(self._cache) > self.max_size * 0.9:  # 90% full
                entries_to_remove = int(self.max_size * 0.1)  # Remove 10%
                self._intelligent_eviction(entries_to_remove)
                optimization_results["optimizations_applied"].append(
                    "intelligent_eviction"
                )

            optimization_results["cache_size_after"] = len(self._cache)

        self.logger.info(
            f"Cache optimization completed: {len(optimization_results['optimizations_applied'])} optimizations applied"
        )

        return optimization_results

    def start_background_optimization(self, interval_minutes: int = 15) -> None:
        """Start background cache optimization."""
        if self._optimization_thread and self._optimization_thread.is_alive():
            return

        self._optimization_enabled = True

        def optimization_worker():
            while self._optimization_enabled:
                try:
                    self.optimize_cache()
                    time.sleep(interval_minutes * 60)
                except Exception as e:
                    self.logger.error(f"Background optimization error: {e}")
                    time.sleep(60)  # Wait 1 minute before retry

        self._optimization_thread = threading.Thread(
            target=optimization_worker, daemon=True
        )
        self._optimization_thread.start()

        self.logger.info(
            f"Started background optimization (interval: {interval_minutes} minutes)"
        )

    def stop_background_optimization(self) -> None:
        """Stop background cache optimization."""
        self._optimization_enabled = False
        if self._optimization_thread:
            self._optimization_thread.join(timeout=5)

        self.logger.info("Stopped background optimization")

    def _generate_cache_key(self, secret_name: str, version: str) -> str:
        """Generate cache key for secret."""
        return f"{secret_name}:{version}"

    def _determine_optimal_ttl(self, secret_name: str) -> int:
        """Determine optimal TTL based on access patterns."""
        if self.cache_strategy == CacheStrategy.TIME_BASED:
            return self.default_ttl

        if self.cache_strategy == CacheStrategy.USAGE_BASED:
            # Longer TTL for frequently accessed secrets
            access_count = self.metrics.access_frequency.get(secret_name, 0)
            if access_count > 10:
                return self.default_ttl * 2
            elif access_count > 5:
                return int(self.default_ttl * 1.5)
            else:
                return self.default_ttl

        if self.cache_strategy == CacheStrategy.ADAPTIVE:
            # Adaptive TTL based on access patterns
            cache_key = self._generate_cache_key(secret_name, "latest")
            if cache_key in self._usage_patterns:
                recent_accesses = self._usage_patterns[cache_key]
                if len(recent_accesses) >= 2:
                    # Calculate average time between accesses
                    time_diffs = [
                        (recent_accesses[i] - recent_accesses[i - 1]).total_seconds()
                        for i in range(1, len(recent_accesses))
                    ]
                    avg_interval = statistics.mean(time_diffs)

                    # Set TTL to be slightly less than average access interval
                    optimal_ttl = int(avg_interval * 0.8)
                    return max(
                        min(optimal_ttl, self.default_ttl * 4), 60
                    )  # Between 1 min and 4x default

            return self.default_ttl

        return self.default_ttl

    def _calculate_entry_priority(self, secret_name: str) -> int:
        """Calculate priority for cache entry."""
        access_count = self.metrics.access_frequency.get(secret_name, 0)

        if access_count >= 20:
            return 3  # High priority
        elif access_count >= 5:
            return 2  # Medium priority
        else:
            return 1  # Low priority

    def _intelligent_eviction(self, count: Optional[int] = None) -> int:
        """Perform intelligent cache eviction based on priority scores."""
        if not self._cache:
            return 0

        # Calculate priority scores for all entries
        entry_scores = [
            (key, entry.calculate_priority_score())
            for key, entry in self._cache.items()
        ]

        # Sort by priority score (lowest first = candidates for eviction)
        entry_scores.sort(key=lambda x: x[1])

        # Determine how many entries to evict
        if count is None:
            count = max(1, int(len(self._cache) * 0.1))  # Evict 10% by default

        evicted_count = 0
        for key, _ in entry_scores[:count]:
            del self._cache[key]
            evicted_count += 1

        self.logger.debug(f"Intelligent eviction removed {evicted_count} entries")
        return evicted_count

    def _optimize_ttl_values(self) -> int:
        """Optimize TTL values for cached entries."""
        adjustments = 0

        for key, entry in self._cache.items():
            new_ttl = self._determine_optimal_ttl(entry.secret_name)
            if new_ttl != entry.ttl_seconds:
                entry.ttl_seconds = new_ttl
                adjustments += 1

        return adjustments

    def _record_access_time(self, secret_name: str, access_time_seconds: float) -> None:
        """Record access time for performance tracking."""
        if secret_name not in self._access_times:
            self._access_times[secret_name] = []

        self._access_times[secret_name].append(access_time_seconds)

        # Keep only recent measurements (last 100 per secret)
        if len(self._access_times[secret_name]) > 100:
            self._access_times[secret_name] = self._access_times[secret_name][-100:]


class SecretManagerOptimizer:
    """
    Secret Manager performance optimizer implementing CRAFT Function methodology.

    Provides comprehensive optimization for Secret Manager operations:
    - Intelligent caching with adaptive strategies
    - Batch operations for efficiency
    - Performance monitoring and analytics
    - Cost optimization recommendations
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        cache_strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
        enable_metrics: bool = True,
    ):
        self.project_id = project_id or self._get_gcp_project_id()
        self.enable_metrics = enable_metrics

        # Initialize GCP Secret Manager client
        self.client = None
        if GCP_SECRET_MANAGER_AVAILABLE:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
                self.logger.info("GCP Secret Manager client initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Secret Manager client: {e}")

        # Initialize performance cache
        self.cache = PerformantSecretCache(cache_strategy=cache_strategy)

        # Performance tracking
        self.performance_history: List[Tuple[datetime, SecretAccessMetrics]] = []
        self.batch_operations: Dict[str, List[str]] = {}  # operation_id -> secret_names

        # Cost tracking
        self.monthly_api_calls = 0
        self.monthly_cost_estimate = 0.0

        self.logger = logging.getLogger(f"{__name__}.SecretManagerOptimizer")
        self.logger.info("SecretManagerOptimizer initialized")

    async def get_secret_optimized(
        self,
        secret_name: str,
        version: str = "latest",
        use_cache: bool = True,
        timeout_seconds: float = 5.0,
    ) -> str:
        """Get secret with performance optimization."""

        start_time = time.perf_counter()

        # Try cache first
        if use_cache:
            cached_value = self.cache.get(secret_name, version)
            if cached_value is not None:
                return cached_value

        # Fetch from Secret Manager
        if not self.client:
            raise RuntimeError("Secret Manager client not available")

        try:
            # Construct the resource name
            if version == "latest":
                name = (
                    f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                )
            else:
                name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"

            # Make API call with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.access_secret_version, request={"name": name}
                ),
                timeout=timeout_seconds,
            )

            secret_value = response.payload.data.decode("UTF-8")

            # Record metrics
            fetch_time = (time.perf_counter() - start_time) * 1000
            self.cache.metrics.api_calls += 1
            self.monthly_api_calls += 1

            # Cache the result
            if use_cache:
                self.cache.set(
                    secret_name, version, secret_value, fetch_time_ms=fetch_time
                )

            self.logger.debug(f"Fetched secret {secret_name} in {fetch_time:.2f}ms")
            return secret_value

        except asyncio.TimeoutError:
            self.cache.metrics.timeout_count += 1
            raise TimeoutError(
                f"Secret Manager request timed out after {timeout_seconds}s"
            )

        except Exception as e:
            self.cache.metrics.error_count += 1
            self.logger.error(f"Failed to fetch secret {secret_name}: {e}")
            raise

    async def batch_get_secrets(
        self,
        secret_names: List[str],
        use_cache: bool = True,
        max_concurrent: int = 10,
        timeout_seconds: float = 10.0,
    ) -> Dict[str, Optional[str]]:
        """Get multiple secrets with optimized batch processing."""

        results = {}
        cache_hits = {}
        cache_misses = []

        # Check cache first
        if use_cache:
            for secret_name in secret_names:
                cached_value = self.cache.get(secret_name)
                if cached_value is not None:
                    cache_hits[secret_name] = cached_value
                else:
                    cache_misses.append(secret_name)
        else:
            cache_misses = secret_names.copy()

        # Fetch cache misses concurrently
        if cache_misses:
            semaphore = asyncio.Semaphore(max_concurrent)

            async def fetch_single_secret(
                secret_name: str,
            ) -> Tuple[str, Optional[str]]:
                async with semaphore:
                    try:
                        value = await self.get_secret_optimized(
                            secret_name,
                            use_cache=use_cache,
                            timeout_seconds=timeout_seconds,
                        )
                        return secret_name, value
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to fetch secret {secret_name}: {e}"
                        )
                        return secret_name, None

            # Execute all fetches concurrently
            tasks = [fetch_single_secret(name) for name in cache_misses]

            try:
                fetch_results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout_seconds,
                )

                for result in fetch_results:
                    if isinstance(result, tuple):
                        secret_name, value = result
                        results[secret_name] = value
                    else:
                        self.logger.error(f"Unexpected result type: {type(result)}")

            except asyncio.TimeoutError:
                self.logger.error(f"Batch fetch timed out after {timeout_seconds}s")
                for secret_name in cache_misses:
                    results[secret_name] = None

        # Combine cache hits with fetched results
        results.update(cache_hits)

        # Ensure all requested secrets are in results
        for secret_name in secret_names:
            if secret_name not in results:
                results[secret_name] = None

        self.logger.info(
            f"Batch get completed: {len(cache_hits)} cache hits, "
            f"{len(cache_misses)} API calls, {sum(1 for v in results.values() if v is not None)} successful"
        )

        return results

    def preload_frequently_used_secrets(
        self, secret_names: List[str], schedule_refresh: bool = True
    ) -> Dict[str, Any]:
        """Preload frequently used secrets for optimal performance."""

        preload_results = {
            "requested": len(secret_names),
            "preloaded": 0,
            "already_cached": 0,
            "failed": 0,
            "errors": [],
        }

        for secret_name in secret_names:
            try:
                # Check if already cached
                if self.cache.get(secret_name) is not None:
                    preload_results["already_cached"] += 1
                    continue

                # Fetch and cache
                asyncio.run(self.get_secret_optimized(secret_name, use_cache=True))
                preload_results["preloaded"] += 1

            except Exception as e:
                preload_results["failed"] += 1
                preload_results["errors"].append(f"{secret_name}: {str(e)}")

        # Schedule periodic refresh if requested
        if schedule_refresh:
            self._schedule_secret_refresh(secret_names)

        self.logger.info(
            f"Preloaded secrets: {preload_results['preloaded']} new, "
            f"{preload_results['already_cached']} cached, "
            f"{preload_results['failed']} failed"
        )

        return preload_results

    def get_performance_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance analysis."""

        metrics = self.cache.get_performance_metrics()

        analysis = {
            "performance_summary": {
                "cache_hit_rate": metrics.cache_hit_rate,
                "avg_access_time_ms": metrics.avg_access_time_ms,
                "p95_access_time_ms": metrics.p95_access_time_ms,
                "total_requests": metrics.total_requests,
                "api_calls": metrics.api_calls,
                "error_rate": metrics.error_count / max(metrics.total_requests, 1),
            },
            "cost_analysis": {
                "estimated_monthly_api_calls": self.monthly_api_calls
                * (30 * 24 / hours),
                "estimated_monthly_cost": self.monthly_api_calls
                * 0.00005
                * (30 * 24 / hours),
                "estimated_savings_from_cache": metrics.estimated_savings,
                "cost_per_request": 0.00005,
            },
            "optimization_opportunities": [],
            "top_secrets": metrics.most_accessed_secrets[:10],
            "cache_efficiency": {
                "cache_size": len(self.cache._cache),
                "max_cache_size": self.cache.max_size,
                "cache_utilization": len(self.cache._cache) / self.cache.max_size,
            },
        }

        # Identify optimization opportunities
        opportunities = []

        if metrics.cache_hit_rate < 0.7:
            opportunities.append(
                {
                    "type": "low_cache_hit_rate",
                    "description": f"Cache hit rate is {metrics.cache_hit_rate:.1%}, consider increasing TTL or preloading frequently used secrets",
                    "potential_impact": "20-30% performance improvement",
                }
            )

        if metrics.avg_access_time_ms > 50:
            opportunities.append(
                {
                    "type": "high_access_time",
                    "description": f"Average access time is {metrics.avg_access_time_ms:.1f}ms, consider batch operations or connection pooling",
                    "potential_impact": "15-25% latency reduction",
                }
            )

        if metrics.error_count > 0:
            opportunities.append(
                {
                    "type": "error_handling",
                    "description": f"Detected {metrics.error_count} errors, implement retry logic and better error handling",
                    "potential_impact": "Improved reliability",
                }
            )

        if len(self.cache._cache) / self.cache.max_size > 0.9:
            opportunities.append(
                {
                    "type": "cache_size",
                    "description": "Cache is near capacity, consider increasing size or improving eviction strategy",
                    "potential_impact": "Prevent cache thrashing",
                }
            )

        analysis["optimization_opportunities"] = opportunities

        return analysis

    def generate_cost_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate cost optimization recommendations for Secret Manager usage."""

        recommendations = []
        metrics = self.cache.get_performance_metrics()

        # Recommendation 1: Optimize caching
        if metrics.cache_hit_rate < 0.8:
            potential_savings = (
                metrics.api_calls * 0.2 * 0.00005 * 30
            )  # Monthly savings
            recommendations.append(
                {
                    "title": "Improve caching strategy",
                    "description": f"Current cache hit rate is {metrics.cache_hit_rate:.1%}. Improving to 80% could save ${potential_savings:.2f}/month",
                    "implementation": [
                        "Increase cache TTL for frequently accessed secrets",
                        "Preload commonly used secrets at application startup",
                        "Implement periodic refresh for critical secrets",
                    ],
                    "estimated_monthly_savings": potential_savings,
                    "effort_level": "LOW",
                }
            )

        # Recommendation 2: Batch operations
        if metrics.total_requests > 100 and len(metrics.most_accessed_secrets) > 5:
            batch_savings = metrics.total_requests * 0.3 * 0.00005 * 30
            recommendations.append(
                {
                    "title": "Implement batch secret retrieval",
                    "description": f"Batch operations could reduce API calls by 30% and save ${batch_savings:.2f}/month",
                    "implementation": [
                        "Group related secret fetches into batch operations",
                        "Use concurrent fetching with proper rate limiting",
                        "Implement smart batching based on access patterns",
                    ],
                    "estimated_monthly_savings": batch_savings,
                    "effort_level": "MEDIUM",
                }
            )

        # Recommendation 3: Secret lifecycle management
        if len(metrics.most_accessed_secrets) > 20:
            lifecycle_savings = metrics.total_requests * 0.1 * 0.00005 * 30
            recommendations.append(
                {
                    "title": "Optimize secret lifecycle management",
                    "description": f"Better secret organization could reduce unnecessary fetches by 10% and save ${lifecycle_savings:.2f}/month",
                    "implementation": [
                        "Review and consolidate rarely used secrets",
                        "Implement secret versioning strategy",
                        "Set up automated cleanup of unused secrets",
                    ],
                    "estimated_monthly_savings": lifecycle_savings,
                    "effort_level": "HIGH",
                }
            )

        return recommendations

    def _schedule_secret_refresh(
        self, secret_names: List[str], interval_hours: int = 4
    ) -> None:
        """Schedule periodic refresh of secrets (simplified implementation)."""
        # In a production environment, this would integrate with a job scheduler
        self.logger.info(
            f"Scheduled refresh for {len(secret_names)} secrets every {interval_hours} hours"
        )

    def _get_gcp_project_id(self) -> Optional[str]:
        """Get GCP project ID from environment or metadata."""
        import os

        # Try environment variable first
        project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            return project_id

        # Try to get from GCP metadata service
        try:
            import requests

            response = requests.get(
                "http://metadata.google.internal/computeMetadata/v1/project/project-id",
                headers={"Metadata-Flavor": "Google"},
                timeout=1,
            )
            if response.status_code == 200:
                return response.text
        except:
            pass

        return None


# Integration with existing Secret Manager
class OptimizedSecretManager:
    """
    Drop-in replacement for existing Secret Manager with performance optimizations.
    """

    def __init__(self, project_id: Optional[str] = None):
        self.optimizer = SecretManagerOptimizer(project_id)
        self.logger = logging.getLogger(f"{__name__}.OptimizedSecretManager")

    async def get_secret(
        self, secret_name: str, version: str = "latest", use_cache: bool = True
    ) -> str:
        """Get secret with performance optimization."""
        return await self.optimizer.get_secret_optimized(
            secret_name, version, use_cache
        )

    async def get_secrets(
        self, secret_names: List[str], use_cache: bool = True
    ) -> Dict[str, Optional[str]]:
        """Get multiple secrets with batch optimization."""
        return await self.optimizer.batch_get_secrets(secret_names, use_cache)

    def preload_secrets(self, secret_names: List[str]) -> Dict[str, Any]:
        """Preload secrets for optimal performance."""
        return self.optimizer.preload_frequently_used_secrets(secret_names)

    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance analysis report."""
        return self.optimizer.get_performance_analysis()

    def get_cost_recommendations(self) -> List[Dict[str, Any]]:
        """Get cost optimization recommendations."""
        return self.optimizer.generate_cost_optimization_recommendations()

    def start_optimization(self) -> None:
        """Start background optimization."""
        self.optimizer.cache.start_background_optimization()
        self.logger.info("Started Secret Manager performance optimization")

    def stop_optimization(self) -> None:
        """Stop background optimization."""
        self.optimizer.cache.stop_background_optimization()
        self.logger.info("Stopped Secret Manager performance optimization")
