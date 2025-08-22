# Whitehorse Go Library

High-performance Go library for the Universal Project Platform. Provides comprehensive utilities for building cloud-native applications with deep GCP integration and enterprise-grade features.

## Features

- **Structured Logging**: High-performance logging with logrus and GCP Cloud Logging integration
- **Error Handling**: Comprehensive error handling with stack traces and categorization
- **Configuration**: Viper-based configuration with environment variables and GCP Secret Manager
- **HTTP Utilities**: HTTP client and server helpers with middleware support
- **Metrics**: Prometheus metrics integration with custom collectors
- **Storage**: GCS and database abstractions with connection pooling
- **Observability**: Built-in tracing, health checking, and monitoring
- **Type Safety**: Full type safety with comprehensive interfaces
- **Performance**: Optimized for high-throughput applications

## Installation

```bash
go get github.com/whitehorse/bootstrapper/lib/go/whitehorse
```

## Quick Start

```go
package main

import (
    "context"
    "log"
    
    "github.com/whitehorse/bootstrapper/lib/go/whitehorse"
)

func main() {
    // Create Whitehorse client
    client, err := whitehorse.NewClient(&whitehorse.Options{
        ServiceName:    "my-service",
        ServiceVersion: "1.0.0",
        Environment:    "production",
        GCPProject:     "my-gcp-project",
        LogLevel:       "info",
        EnableMetrics:  true,
        EnableTracing:  true,
    })
    if err != nil {
        log.Fatal(err)
    }

    // Start the client
    ctx := context.Background()
    if err := client.Start(ctx); err != nil {
        log.Fatal(err)
    }
    defer client.Stop(ctx)

    // Get logger
    logger := client.Logger()
    logger.Info("Service started successfully")

    // Use metrics
    metrics := client.Metrics()
    metrics.IncrementCounter("requests_total", 1, map[string]string{
        "method": "GET",
        "status": "200",
    })

    // Your application logic here
    if err := runApplication(client); err != nil {
        logger.WithError(err).Error("Application failed")
    }
}

func runApplication(client *whitehorse.Client) error {
    logger := client.Logger()
    
    // Performance logging
    perfLogger := logger.StartOperation("process_request")
    defer func() {
        if err := recover(); err != nil {
            perfLogger.Error(fmt.Errorf("panic: %v", err))
        } else {
            perfLogger.Success()
        }
    }()

    // Your business logic
    logger.Info("Processing request", "user_id", "123")
    
    return nil
}
```

## Configuration

### Environment Variables

```bash
# Service identification
SERVICE_NAME=my-service
SERVICE_VERSION=1.0.0
ENVIRONMENT=production

# GCP configuration
GCP_PROJECT=my-gcp-project
GCP_REGION=us-central1

# Logging
LOG_LEVEL=info
LOG_FORMAT=json

# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=myapp
DATABASE_USER=myuser
DATABASE_PASSWORD=mypassword
DATABASE_SSL_MODE=prefer

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Metrics
METRICS_PORT=8080
ENABLE_PROMETHEUS=true

# Security
JWT_SECRET=your-jwt-secret
```

### Configuration Files

The library supports multiple configuration formats using Viper:

**config.yaml**
```yaml
service:
  name: my-service
  version: 1.0.0
  environment: production

gcp:
  project: my-gcp-project
  region: us-central1

database:
  host: localhost
  port: 5432
  name: myapp
  user: myuser
  password: mypassword
  ssl_mode: prefer

redis:
  host: localhost
  port: 6379

metrics:
  port: 8080
  enable_prometheus: true
```

**config.json**
```json
{
  "service": {
    "name": "my-service",
    "version": "1.0.0",
    "environment": "production"
  },
  "gcp": {
    "project": "my-gcp-project",
    "region": "us-central1"
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "myapp"
  }
}
```

## API Reference

### Client

```go
import "github.com/whitehorse/bootstrapper/lib/go/whitehorse"

// Create client with options
client, err := whitehorse.NewClient(&whitehorse.Options{
    ServiceName:    "my-service",
    ServiceVersion: "1.0.0",
    Environment:    "production",
    GCPProject:     "my-gcp-project",
    GCPRegion:      "us-central1",
    LogLevel:       "info",
    EnableMetrics:  true,
    EnableTracing:  true,
    ConfigFile:     "config.yaml",
})

// Start and stop
ctx := context.Background()
err = client.Start(ctx)
defer client.Stop(ctx)

// Health check
health, err := client.Health(ctx)
fmt.Printf("Service health: %s\n", health.Overall)

// Access components
logger := client.Logger()
metrics := client.Metrics()
config := client.Config()
```

### Logging

```go
import "github.com/whitehorse/bootstrapper/lib/go/whitehorse/logging"

// Create logger
logger, err := logging.New(&logging.Options{
    Level:         "info",
    ServiceName:   "my-service",
    Environment:   "production",
    GCPProject:    "my-gcp-project",
    Format:        "json",
    EnableGCP:     true,
    EnableConsole: true,
})

// Basic logging
logger.Info("Application started")
logger.Error("Database connection failed")
logger.WithField("user_id", "123").Info("User logged in")

// Structured logging
logger.WithFields(map[string]interface{}{
    "user_id":    "123",
    "ip_address": "192.168.1.1",
    "action":     "login",
}).Info("User authentication successful")

// Error logging
err := errors.New("something went wrong")
logger.WithError(err).Error("Operation failed")

// Performance logging
perfLogger := logger.StartOperation("database_query")
// ... perform operation ...
perfLogger.Success() // or perfLogger.Error(err)

// Context logging
ctx = logging.WithCorrelationID(ctx, "abc-123")
logger.WithContext(ctx).Info("Processing request")

// Security logging
logger.LogSecurityEvent("login_attempt", "user123", "192.168.1.1", map[string]interface{}{
    "success": true,
    "method":  "oauth",
})

// HTTP request logging
logger.LogHTTPRequest("GET", "/api/users", "MyApp/1.0", "192.168.1.1", 200, time.Millisecond*150)

// Database query logging
logger.LogDatabaseQuery("SELECT * FROM users WHERE id = ?", time.Millisecond*50, nil)

// External service logging
logger.LogExternalCall("user-service", "GET /users/123", time.Millisecond*200, 200, nil)
```

### Error Handling

```go
import "github.com/whitehorse/bootstrapper/lib/go/whitehorse/errors"

// Create errors
err := errors.New("Invalid input", errors.ErrValidationFailed,
    errors.WithSeverity(errors.SeverityLow),
    errors.WithCategory(errors.CategoryValidation),
    errors.WithRecoverable(true),
)

// Wrap existing errors
if err := someOperation(); err != nil {
    return errors.Wrap(err, "Operation failed", errors.ErrInternalError,
        errors.WithSeverity(errors.SeverityCritical),
    )
}

// Predefined error constructors
err = errors.NewValidationError("Email is required", "email")
err = errors.NewNotFoundError("User")
err = errors.NewUnauthorizedError("Invalid token")
err = errors.NewInternalError("Database connection failed")

// Error handling
if errors.IsRetryable(err) {
    // Retry the operation
}

severity := errors.GetSeverity(err)
category := errors.GetCategory(err)
userMsg := errors.GetUserMessage(err)

// Convert to map for logging
errMap := err.(*errors.WhitehorseError).ToMap()
logger.WithFields(errMap).Error("Operation failed")

// Multi-error handling
multiErr := errors.NewMultiError()
multiErr.Add(errors.NewValidationError("Name required", "name"))
multiErr.Add(errors.NewValidationError("Email required", "email"))

if multiErr.HasErrors() {
    return multiErr.ToError()
}
```

### Configuration

```go
import "github.com/whitehorse/bootstrapper/lib/go/whitehorse/config"

// Create configuration
cfg, err := config.New(&config.Options{
    ServiceName:    "my-service",
    ServiceVersion: "1.0.0",
    Environment:    "production",
    ConfigFile:     "config.yaml",
    GCPProject:     "my-gcp-project",
})

// Access configuration values
serviceName := cfg.ServiceName()
environment := cfg.Environment()
dbHost := cfg.GetString("database.host")
dbPort := cfg.GetInt("database.port")

// Default values
apiTimeout := cfg.GetDuration("api.timeout", 30*time.Second)
maxRetries := cfg.GetInt("api.max_retries", 3)

// Environment checks
if cfg.IsDevelopment() {
    // Development-specific logic
}

if cfg.IsProduction() {
    // Production-specific logic
}

// Watch for configuration changes
cfg.WatchConfig()
cfg.OnConfigChange(func(e fsnotify.Event) {
    logger.Info("Config file changed:", e.Name)
})
```

### HTTP Client

```go
import "github.com/whitehorse/bootstrapper/lib/go/whitehorse/http"

// Create HTTP client
client := http.NewClient(&http.Options{
    BaseURL: "https://api.example.com",
    Timeout: 30 * time.Second,
    Retry: &http.RetryOptions{
        MaxAttempts: 3,
        BackoffType: http.ExponentialBackoff,
        MinDelay:    time.Second,
        MaxDelay:    30 * time.Second,
    },
})

// Make requests
response, err := client.Get(ctx, "/users", &http.RequestOptions{
    Headers: map[string]string{
        "Authorization": "Bearer " + token,
    },
    Query: map[string]string{
        "page":  "1",
        "limit": "10",
    },
})

// POST request
user := User{Name: "John", Email: "john@example.com"}
response, err = client.Post(ctx, "/users", &http.RequestOptions{
    Body: user,
})

// Custom request
req := &http.Request{
    Method: "PUT",
    URL:    "/users/123",
    Body:   updatedUser,
    Headers: map[string]string{
        "Content-Type": "application/json",
    },
}
response, err = client.Do(ctx, req)
```

### Metrics

```go
import "github.com/whitehorse/bootstrapper/lib/go/whitehorse/metrics"

// Create metrics collector
collector, err := metrics.New(&metrics.Options{
    ServiceName: "my-service",
    Environment: "production",
    GCPProject:  "my-gcp-project",
    Port:        8080, // Prometheus metrics port
})

// Start metrics server
ctx := context.Background()
err = collector.Start(ctx)
defer collector.Stop(ctx)

// Counter metrics
collector.IncrementCounter("requests_total", 1, map[string]string{
    "method": "GET",
    "status": "200",
    "endpoint": "/api/users",
})

// Gauge metrics
collector.SetGauge("active_connections", 42)
collector.SetGauge("memory_usage_bytes", float64(runtime.MemStats{}.Alloc))

// Histogram metrics
collector.RecordDuration("request_duration", 150*time.Millisecond, map[string]string{
    "endpoint": "/api/users",
    "method":   "GET",
})

// Custom metrics
collector.RecordValue("business_metric", 100.5, map[string]string{
    "type": "revenue",
    "currency": "USD",
})

// Timing wrapper
duration, err := collector.TimeOperation("database_query", func() error {
    return db.Query("SELECT * FROM users")
})
```

### Storage

```go
import "github.com/whitehorse/bootstrapper/lib/go/whitehorse/storage"

// GCS storage
gcsClient, err := storage.NewGCSClient(&storage.GCSOptions{
    BucketName: "my-bucket",
    ProjectID:  "my-gcp-project",
})

// Upload object
err = gcsClient.Upload(ctx, "path/to/file.txt", bytes.NewReader(data))

// Download object
data, err := gcsClient.Download(ctx, "path/to/file.txt")

// List objects
objects, err := gcsClient.List(ctx, "path/to/directory/")

// Database storage
db, err := storage.NewDatabase(&storage.DatabaseOptions{
    Driver:   "postgres",
    Host:     "localhost",
    Port:     5432,
    Database: "myapp",
    Username: "user",
    Password: "password",
    SSLMode:  "prefer",
    PoolSize: 10,
})

// Connection management
conn, err := db.GetConnection(ctx)
defer conn.Close()

// Transaction support
err = db.WithTransaction(ctx, func(tx *sql.Tx) error {
    // Your transactional operations
    return nil
})
```

## Middleware

### HTTP Middleware

```go
import (
    "github.com/go-chi/chi/v5"
    "github.com/whitehorse/bootstrapper/lib/go/whitehorse"
)

func main() {
    client, _ := whitehorse.NewClient(opts)
    middleware := client.NewMiddleware()
    
    r := chi.NewRouter()
    
    // Correlation ID middleware
    r.Use(middleware.WithCorrelationID(func(ctx context.Context) error {
        // Request processing
        return nil
    }))
    
    // Metrics middleware
    r.Use(middleware.WithMetrics("http_request", func(ctx context.Context) error {
        // Request processing
        return nil
    }))
    
    // Logging middleware
    r.Use(middleware.WithLogging("http_request", func(ctx context.Context) error {
        // Request processing
        return nil
    }))
    
    r.Get("/api/users", handleUsers)
}

func handleUsers(w http.ResponseWriter, r *http.Request) {
    client := whitehorse.MustFromContext(r.Context())
    logger := client.Logger().WithContext(r.Context())
    
    logger.Info("Handling user request")
    
    // Your handler logic
}
```

### Custom Middleware

```go
func LoggingMiddleware(logger *logging.Logger) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            start := time.Now()
            
            // Add correlation ID
            ctx, correlationID := logging.GetOrGenerateCorrelationID(r.Context())
            r = r.WithContext(ctx)
            
            // Wrap response writer to capture status
            ww := &responseWriter{ResponseWriter: w, status: 200}
            
            next.ServeHTTP(ww, r)
            
            duration := time.Since(start)
            logger.WithCorrelationID(correlationID).LogHTTPRequest(
                r.Method, r.URL.Path, r.UserAgent(), r.RemoteAddr,
                ww.status, duration,
            )
        })
    }
}

type responseWriter struct {
    http.ResponseWriter
    status int
}

func (rw *responseWriter) WriteHeader(code int) {
    rw.status = code
    rw.ResponseWriter.WriteHeader(code)
}
```

## Advanced Usage

### Graceful Shutdown

```go
func main() {
    client, err := whitehorse.NewClient(opts)
    if err != nil {
        log.Fatal(err)
    }
    
    ctx := context.Background()
    if err := client.Start(ctx); err != nil {
        log.Fatal(err)
    }
    
    // Setup graceful shutdown
    graceful := client.NewGraceful()
    
    // Handle shutdown signals
    c := make(chan os.Signal, 1)
    signal.Notify(c, os.Interrupt, syscall.SIGTERM)
    
    go func() {
        <-c
        graceful.Shutdown()
    }()
    
    // Wait for shutdown
    shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    if err := graceful.Wait(shutdownCtx); err != nil {
        log.Printf("Graceful shutdown failed: %v", err)
    }
}
```

### Circuit Breaker

```go
import "github.com/whitehorse/bootstrapper/lib/go/whitehorse/errors"

// Create circuit breaker
breaker := &errors.CircuitBreaker{
    FailureThreshold: 5,
    RecoveryTimeout:  60 * time.Second,
    ExpectedError:    &errors.WhitehorseError{},
}

// Execute with circuit breaker
result, err := breaker.Execute(func() (interface{}, error) {
    return externalAPICall()
})

if err != nil {
    logger.WithError(err).Error("Circuit breaker open")
}
```

### Performance Monitoring

```go
func MonitoredFunction(client *whitehorse.Client) error {
    logger := client.Logger()
    metrics := client.Metrics()
    
    // Start performance monitoring
    perfLogger := logger.StartOperation("process_data")
    timer := time.Now()
    
    defer func() {
        duration := time.Since(timer)
        
        // Record metrics
        metrics.RecordDuration("operation_duration", duration, map[string]string{
            "operation": "process_data",
        })
        
        // Log performance
        if err := recover(); err != nil {
            perfLogger.Error(fmt.Errorf("panic: %v", err))
        } else {
            perfLogger.Success()
        }
    }()
    
    // Your operation logic
    time.Sleep(100 * time.Millisecond)
    
    return nil
}
```

## Testing

### Unit Tests

```go
func TestWhitehorseClient(t *testing.T) {
    opts := &whitehorse.Options{
        ServiceName: "test-service",
        LogLevel:    "debug",
    }
    
    client, err := whitehorse.NewClient(opts)
    require.NoError(t, err)
    require.NotNil(t, client)
    
    ctx := context.Background()
    err = client.Start(ctx)
    require.NoError(t, err)
    defer client.Stop(ctx)
    
    // Test health check
    health, err := client.Health(ctx)
    require.NoError(t, err)
    assert.Equal(t, "healthy", health.Overall)
}

func TestLogging(t *testing.T) {
    var buf bytes.Buffer
    
    logger, err := logging.New(&logging.Options{
        Level:  "debug",
        Format: "json",
        Output: &buf,
    })
    require.NoError(t, err)
    
    logger.Info("test message")
    
    var logEntry map[string]interface{}
    err = json.Unmarshal(buf.Bytes(), &logEntry)
    require.NoError(t, err)
    
    assert.Equal(t, "test message", logEntry["message"])
    assert.Equal(t, "info", logEntry["level"])
}
```

### Integration Tests

```go
func TestGCPIntegration(t *testing.T) {
    if testing.Short() {
        t.Skip("Skipping integration test")
    }
    
    opts := &whitehorse.Options{
        ServiceName: "integration-test",
        GCPProject:  os.Getenv("GCP_PROJECT"),
        EnableGCP:   true,
    }
    
    client, err := whitehorse.NewClient(opts)
    require.NoError(t, err)
    
    ctx := context.Background()
    err = client.Start(ctx)
    require.NoError(t, err)
    defer client.Stop(ctx)
    
    // Test GCP logging
    logger := client.Logger()
    logger.Info("Integration test log message")
    
    // Allow time for log to be sent
    time.Sleep(2 * time.Second)
}
```

## Performance Benchmarks

```go
func BenchmarkLogging(b *testing.B) {
    logger, _ := logging.New(&logging.Options{
        Level:  "info",
        Format: "json",
        Output: io.Discard,
    })
    
    b.ResetTimer()
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            logger.Info("benchmark message")
        }
    })
}

func BenchmarkMetrics(b *testing.B) {
    collector, _ := metrics.New(&metrics.Options{
        ServiceName: "benchmark",
    })
    
    b.ResetTimer()
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            collector.IncrementCounter("test_counter", 1, nil)
        }
    })
}
```

## Best Practices

1. **Use context.Context** for all operations
2. **Implement proper error handling** with structured errors
3. **Include correlation IDs** for request tracing
4. **Monitor performance** of critical operations
5. **Use structured logging** with consistent field names
6. **Implement graceful shutdown** for long-running services
7. **Follow Go conventions** for package and function naming
8. **Use interfaces** for better testability
9. **Implement circuit breakers** for external service calls
10. **Monitor resource usage** and optimize accordingly

## Examples

See the `examples/` directory for complete examples:

- **HTTP API Server**: REST API with full middleware stack
- **Worker Service**: Background job processing with metrics
- **CLI Application**: Command-line tool with rich logging
- **Microservice**: Complete microservice with all features

## Contributing

1. Follow Go conventions and best practices
2. Add comprehensive tests for new functionality
3. Update documentation for API changes
4. Use consistent error handling patterns
5. Ensure thread safety for concurrent operations

## License

MIT License - see LICENSE file for details.