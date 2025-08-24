"""
Genesis Performance Monitoring System
CRAFT Methodology Implementation for Automated Performance Monitoring

This module provides comprehensive performance monitoring, profiling, and
optimization capabilities for the Genesis platform with GCP-native integrations.

Components:
- Automated performance profiling and benchmarking
- Continuous performance regression detection
- GCP Cloud Monitoring integration with alerting
- Performance optimization with GCP-specific recommendations
- Cost optimization monitoring and analysis
- Secret Manager performance optimization patterns
"""

from .benchmarks import (
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkRunner,
    PerformanceBenchmarks,
)
from .cost_optimizer import CostOptimizationMonitor, CostRecommendation
from .monitor import PerformanceAlert, PerformanceIncident, PerformanceMonitor
from .optimizer import OptimizationRecommendation, PerformanceOptimizer
from .profiler import PerformanceProfiler, ProfilerConfig
from .regression import PerformanceBaseline, RegressionDetector, RegressionResult
from .secret_performance import OptimizedSecretManager, SecretManagerOptimizer

__all__ = [
    "PerformanceProfiler",
    "ProfilerConfig",
    "PerformanceBenchmarks",
    "BenchmarkRunner",
    "BenchmarkConfig",
    "BenchmarkResult",
    "RegressionDetector",
    "PerformanceBaseline",
    "RegressionResult",
    "PerformanceMonitor",
    "PerformanceAlert",
    "PerformanceIncident",
    "PerformanceOptimizer",
    "OptimizationRecommendation",
    "CostOptimizationMonitor",
    "CostRecommendation",
    "SecretManagerOptimizer",
    "OptimizedSecretManager",
]

# Version and metadata
__version__ = "1.0.0"
__author__ = "Genesis Backend Developer Agent"
__description__ = "Automated Performance Monitoring and Optimization System"
