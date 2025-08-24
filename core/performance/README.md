# Genesis Performance Monitoring System

A comprehensive GCP-native performance monitoring and optimization system implementing the CRAFT methodology for optimal backend performance.

## Overview

The Genesis Performance Monitoring System provides end-to-end performance monitoring, analysis, and optimization for GCP-based applications. It integrates seamlessly with GCP Cloud Operations, Secret Manager, and other GCP services to deliver intelligent performance insights and automated optimizations.

## Architecture

```
Genesis Performance System
├── Profiler          - CRAFT Create: Real-time performance profiling
├── Benchmarks        - CRAFT Create: Automated performance benchmarking
├── Regression        - CRAFT Refactor: Performance regression detection
├── Monitor           - CRAFT Authenticate: GCP Cloud Monitoring integration
├── Optimizer         - CRAFT Function: Performance optimization engine
├── Cost Optimizer    - CRAFT Function: Cost optimization monitoring
└── Secret Performance - CRAFT Function: Secret Manager optimization
```

## Key Features

### 🚀 Performance Profiling
- **Real-time Profiling**: CPU, memory, and I/O monitoring
- **Context-aware Metrics**: Function-level performance tracking
- **Automated Issue Detection**: Performance threshold monitoring
- **Resource Optimization**: Intelligent resource usage analysis

### 📊 Performance Benchmarking
- **Automated Benchmarking**: Continuous performance validation
- **GCP Integration**: Cloud Monitoring metrics publishing
- **Statistical Analysis**: Comprehensive performance analytics
- **Baseline Management**: Performance baseline creation and tracking

### 🔍 Regression Detection
- **Statistical Analysis**: Advanced regression detection algorithms
- **Baseline Comparison**: Historical performance comparison
- **Confidence Scoring**: AI-driven confidence assessments
- **Actionable Recommendations**: Automated optimization suggestions

### 📈 GCP Cloud Monitoring
- **Native Integration**: Deep GCP Cloud Operations integration
- **Real-time Alerting**: Intelligent performance alerting
- **Custom Dashboards**: Automated dashboard generation
- **Incident Management**: Comprehensive incident tracking

### ⚡ Performance Optimization
- **Service-specific Analysis**: GCP service optimization recommendations
- **Implementation Guidance**: Step-by-step optimization instructions
- **ROI Calculation**: Investment return analysis
- **Risk Assessment**: Implementation risk evaluation

### 💰 Cost Optimization
- **Cost Analysis**: Comprehensive GCP cost monitoring
- **Savings Identification**: Automated cost-saving opportunities
- **Budget Management**: Intelligent budget alerting
- **Resource Right-sizing**: Optimal resource allocation recommendations

### 🔐 Secret Manager Optimization
- **Intelligent Caching**: Adaptive caching strategies
- **Batch Operations**: Optimized secret retrieval
- **Access Pattern Analysis**: Usage pattern optimization
- **Cost Reduction**: Secret Manager cost optimization

## Quick Start

### Basic Usage

```python
import asyncio
from core.performance import (
    PerformanceProfiler, PerformanceBenchmarks,
    PerformanceMonitor, PerformanceOptimizer,
    CostOptimizationMonitor, OptimizedSecretManager
)

async def main():
    # Initialize components
    profiler = PerformanceProfiler()
    benchmarks = PerformanceBenchmarks()
    monitor = PerformanceMonitor(gcp_project_id="your-project")
    optimizer = PerformanceOptimizer()
    cost_monitor = CostOptimizationMonitor()
    secret_manager = OptimizedSecretManager()

    # Profile application performance
    profile_id = profiler.start_profiling()

    # Your application code here
    with profiler.profile_context("database_operation"):
        result = await your_database_operation()

    # Get performance results
    report = profiler.stop_profiling(profile_id)
    print(f"Performance: {report.avg_cpu_percent:.1f}% CPU, {report.avg_duration_ms:.2f}ms avg")

asyncio.run(main())
```

### Advanced Configuration

```python
from core.performance import (
    ProfilerConfig, BenchmarkConfig,
    OptimizationRecommendation, CacheStrategy
)

# Configure profiler
profiler_config = ProfilerConfig(
    enable_cpu_profiling=True,
    enable_memory_profiling=True,
    sampling_interval=0.1,
    cpu_threshold_percent=80.0,
    memory_threshold_percent=85.0,
    response_time_threshold_ms=500.0
)

profiler = PerformanceProfiler(profiler_config)

# Configure benchmarks
benchmark_config = BenchmarkConfig(
    benchmark_name="api_endpoint",
    target_function=your_api_function,
    measurement_iterations=50,
    target_avg_ms=200.0,
    target_p95_ms=300.0,
    gcp_project_id="your-project",
    enable_cloud_monitoring=True
)

benchmarks = PerformanceBenchmarks()
benchmarks.register_benchmark(benchmark_config)

# Configure optimized Secret Manager
secret_manager = OptimizedSecretManager(
    project_id="your-project"
)
secret_manager.start_optimization()  # Enable background optimization
```

## GCP Integration

### Cloud Monitoring Setup

The system automatically integrates with GCP Cloud Monitoring:

```python
# Monitor creates custom metrics
monitor = PerformanceMonitor(
    gcp_project_id="your-project",
    metric_prefix="myapp.performance"
)

# Record custom metrics
monitor.record_performance_metric(
    "response_time",
    150.0,  # ms
    labels={
        "service": "api",
        "endpoint": "/users",
        "environment": "production"
    }
)

# Create alerts
alert = monitor.create_response_time_alert(
    service_name="api",
    threshold_ms=500,
    environment="production"
)
```

### Cost Optimization Integration

```python
# Analyze costs across GCP services
cost_monitor = CostOptimizationMonitor(
    project_id="your-project"
)

# Monthly cost analysis
analysis = await cost_monitor.analyze_monthly_costs()
print(f"Total cost: ${analysis.total_cost:.2f}")
print(f"Potential savings: ${analysis.total_potential_savings:.2f}")

# Create budget alerts
alerts = cost_monitor.create_budget_alert(
    service_name="Cloud Run",
    monthly_budget=500.0,
    threshold_percentages=[50, 80, 100]
)
```

### Secret Manager Optimization

```python
# Use optimized Secret Manager
secret_manager = OptimizedSecretManager("your-project")

# Batch secret retrieval with caching
secrets = await secret_manager.get_secrets([
    "database-password",
    "api-key",
    "encryption-key"
])

# Performance analysis
report = secret_manager.get_performance_report()
print(f"Cache hit rate: {report['performance_summary']['cache_hit_rate']:.1%}")

# Cost recommendations
recommendations = secret_manager.get_cost_recommendations()
for rec in recommendations:
    print(f"- {rec['title']}: ${rec['estimated_monthly_savings']:.2f}/month")
```

## Performance Optimization Workflow

### 1. Profile and Benchmark

```python
# Start comprehensive profiling
profiler = PerformanceProfiler()
benchmarks = PerformanceBenchmarks()

# Profile critical operations
with profiler.profile_context("critical_operation"):
    result = await critical_operation()

# Benchmark against targets
benchmark_result = await benchmarks.run_benchmark("critical_operation")
if not benchmark_result.meets_targets:
    print(f"Performance issue: {benchmark_result.performance_grade}")
```

### 2. Detect Regressions

```python
# Create performance baseline
regression_detector = RegressionDetector()
baseline = regression_detector.create_baseline(
    operation_name="critical_operation",
    duration_samples=duration_measurements
)

# Check for regressions
regression_result = regression_detector.detect_regression(
    operation_name="critical_operation",
    current_samples=new_measurements
)

if regression_result.has_regression:
    print(f"Regression detected: {regression_result.regression_severity}")
    print(f"Recommendations: {regression_result.recommendations}")
```

### 3. Generate Optimizations

```python
# Analyze performance and generate recommendations
optimizer = PerformanceOptimizer()
recommendations = await optimizer.analyze_service_performance(
    service_name="my-service",
    service_type="cloud_run",
    metrics=performance_metrics
)

# Create optimization plan
plan = optimizer.generate_optimization_plan(
    max_recommendations=10,
    max_total_effort_hours=40,
    prioritize_quick_wins=True
)

print(f"Optimization plan: {len(plan['selected_recommendations'])} recommendations")
print(f"Estimated effort: {plan['summary']['total_implementation_hours']} hours")
```

### 4. Monitor and Alert

```python
# Set up comprehensive monitoring
monitor = PerformanceMonitor(gcp_project_id="your-project")

# Create service-specific alerts
response_alert = monitor.create_response_time_alert(
    service_name="my-service",
    threshold_ms=500,
    environment="production"
)

error_alert = monitor.create_error_rate_alert(
    service_name="my-service",
    threshold_percent=2.0,
    environment="production"
)

# Check for incidents
incidents = monitor.check_performance_thresholds()
for incident in incidents:
    print(f"Incident: {incident.alert_name} - {incident.current_value}")
```

## Integration Examples

### Django Integration

```python
from django.middleware.base import BaseMiddleware
from core.performance import PerformanceProfiler

class PerformanceMiddleware(BaseMiddleware):
    def __init__(self, get_response):
        self.get_response = get_response
        self.profiler = PerformanceProfiler()

    def __call__(self, request):
        with self.profiler.profile_context(f"{request.method}_{request.path}"):
            response = self.get_response(request)
        return response
```

### FastAPI Integration

```python
from fastapi import FastAPI, Request
from core.performance import PerformanceProfiler
import time

app = FastAPI()
profiler = PerformanceProfiler()

@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    start_time = time.time()

    with profiler.profile_context(f"{request.method}_{request.url.path}"):
        response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### Cloud Function Integration

```python
import functions_framework
from core.performance import PerformanceProfiler, OptimizedSecretManager

profiler = PerformanceProfiler()
secret_manager = OptimizedSecretManager()

@functions_framework.http
def my_function(request):
    with profiler.profile_context("cloud_function_execution"):
        # Your function logic
        api_key = await secret_manager.get_secret("api-key")
        result = process_request(request, api_key)
        return result
```

## Configuration

### Environment Variables

```bash
# GCP Configuration
export GCP_PROJECT_ID="your-gcp-project"
export GOOGLE_CLOUD_PROJECT="your-gcp-project"

# Performance Configuration
export PERFORMANCE_PROFILING_ENABLED=true
export PERFORMANCE_SAMPLING_INTERVAL=0.1
export PERFORMANCE_CACHE_SIZE=1000

# Cost Monitoring
export COST_MONITORING_ENABLED=true
export MONTHLY_BUDGET_ALERTS=true

# Secret Manager Optimization
export SECRET_CACHE_STRATEGY=adaptive
export SECRET_CACHE_TTL=300
```

### Configuration Files

```yaml
# performance_config.yaml
profiler:
  enable_cpu_profiling: true
  enable_memory_profiling: true
  sampling_interval: 0.1
  cpu_threshold_percent: 80.0
  memory_threshold_percent: 85.0

benchmarks:
  default_iterations: 50
  confidence_level: 0.95
  enable_cloud_monitoring: true

monitoring:
  gcp_project_id: "your-project"
  metric_prefix: "myapp.performance"
  enable_alerting: true

cost_optimization:
  enable_analysis: true
  monthly_budget_alerts: true
  savings_threshold: 100.0

secret_manager:
  cache_strategy: "adaptive"
  cache_size: 1000
  background_optimization: true
```

## Best Practices

### 1. Performance Profiling
- Use context managers for operation-specific profiling
- Set appropriate thresholds based on SLAs
- Enable background optimization for production
- Monitor resource usage trends

### 2. Benchmarking
- Set realistic performance targets
- Run benchmarks in consistent environments
- Use statistical analysis for reliable results
- Integrate with CI/CD pipelines

### 3. Cost Optimization
- Regular monthly cost analysis
- Set up budget alerts at multiple thresholds
- Implement recommended optimizations gradually
- Track ROI of optimization efforts

### 4. Secret Management
- Use batch operations for multiple secrets
- Enable intelligent caching
- Monitor access patterns
- Implement periodic refresh for critical secrets

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```python
   # Reduce profiling history size
   profiler_config = ProfilerConfig(
       max_profile_history=50,  # Reduce from default 100
       retention_days=7         # Reduce retention period
   )
   ```

2. **GCP Permissions**
   ```bash
   # Required IAM permissions
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
       --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
       --role="roles/monitoring.metricWriter"

   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
       --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
       --role="roles/secretmanager.secretAccessor"
   ```

3. **Performance Impact**
   ```python
   # Use sampling for production
   profiler_config = ProfilerConfig(
       sampling_interval=1.0,    # Reduce sampling frequency
       enable_persistent_storage=False  # Disable for high-throughput apps
   )
   ```

## API Reference

### Core Classes

- **PerformanceProfiler**: Real-time performance profiling
- **PerformanceBenchmarks**: Automated benchmarking system
- **RegressionDetector**: Performance regression detection
- **PerformanceMonitor**: GCP monitoring integration
- **PerformanceOptimizer**: Optimization recommendation engine
- **CostOptimizationMonitor**: Cost monitoring and optimization
- **OptimizedSecretManager**: High-performance Secret Manager client

### Key Methods

```python
# Profiling
profiler.start_profiling(profile_id) -> str
profiler.stop_profiling(profile_id) -> ProfileReport
profiler.profile_context(operation_name) -> ContextManager

# Benchmarking
benchmarks.run_benchmark(name) -> BenchmarkResult
benchmarks.run_benchmark_suite() -> Dict[str, BenchmarkResult]

# Monitoring
monitor.record_performance_metric(name, value, labels)
monitor.create_response_time_alert(service, threshold) -> PerformanceAlert
monitor.check_performance_thresholds() -> List[PerformanceIncident]

# Optimization
optimizer.analyze_service_performance(service, type, metrics) -> List[OptimizationRecommendation]
optimizer.generate_optimization_plan(max_recs, effort) -> Dict

# Cost Optimization
cost_monitor.analyze_monthly_costs() -> CostAnalysis
cost_monitor.create_budget_alert(service, budget) -> List[CostAlert]

# Secret Manager
secret_manager.get_secret(name) -> str
secret_manager.get_secrets(names) -> Dict[str, str]
secret_manager.get_performance_report() -> Dict
```

## Contributing

1. Follow the CRAFT methodology for all implementations
2. Include comprehensive tests with >80% coverage
3. Add GCP integration examples
4. Update documentation for new features
5. Ensure backward compatibility

## License

Copyright © 2024 Genesis Platform. All rights reserved.

---

For more information, see the [Genesis Documentation](../../../docs/) or contact the development team.
