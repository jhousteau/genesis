// Package whitehorse provides a comprehensive Go library for the Universal Project Platform
// with focus on GCP integration, observability, and enterprise-grade features.
package whitehorse

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/whitehorse/bootstrapper/lib/go/whitehorse/config"
	"github.com/whitehorse/bootstrapper/lib/go/whitehorse/errors"
	"github.com/whitehorse/bootstrapper/lib/go/whitehorse/logging"
	"github.com/whitehorse/bootstrapper/lib/go/whitehorse/metrics"
)

// Version represents the library version
const Version = "1.0.0"

// Client represents the main Whitehorse client
type Client struct {
	config  *config.Config
	logger  *logging.Logger
	metrics *metrics.Collector
	mu      sync.RWMutex
	started bool
}

// Options configures the Whitehorse client
type Options struct {
	ServiceName    string
	ServiceVersion string
	Environment    string
	GCPProject     string
	GCPRegion      string
	LogLevel       string
	EnableMetrics  bool
	EnableTracing  bool
	ConfigFile     string
}

// DefaultOptions returns default configuration options
func DefaultOptions() *Options {
	return &Options{
		ServiceName:    "whitehorse-service",
		ServiceVersion: "1.0.0",
		Environment:    "development",
		GCPRegion:      "us-central1",
		LogLevel:       "info",
		EnableMetrics:  true,
		EnableTracing:  true,
	}
}

// NewClient creates a new Whitehorse client
func NewClient(opts *Options) (*Client, error) {
	if opts == nil {
		opts = DefaultOptions()
	}

	// Initialize configuration
	cfg, err := config.New(&config.Options{
		ServiceName:    opts.ServiceName,
		ServiceVersion: opts.ServiceVersion,
		Environment:    opts.Environment,
		GCPProject:     opts.GCPProject,
		GCPRegion:      opts.GCPRegion,
		ConfigFile:     opts.ConfigFile,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to initialize config: %w", err)
	}

	// Initialize logger
	logger, err := logging.New(&logging.Options{
		Level:       opts.LogLevel,
		ServiceName: opts.ServiceName,
		Environment: opts.Environment,
		GCPProject:  opts.GCPProject,
		Format:      "json",
	})
	if err != nil {
		return nil, fmt.Errorf("failed to initialize logger: %w", err)
	}

	// Initialize metrics collector
	var metricsCollector *metrics.Collector
	if opts.EnableMetrics {
		metricsCollector, err = metrics.New(&metrics.Options{
			ServiceName: opts.ServiceName,
			Environment: opts.Environment,
			GCPProject:  opts.GCPProject,
		})
		if err != nil {
			logger.Warn("Failed to initialize metrics collector", "error", err)
		}
	}

	client := &Client{
		config:  cfg,
		logger:  logger,
		metrics: metricsCollector,
	}

	logger.Info("Whitehorse client initialized",
		"version", Version,
		"service", opts.ServiceName,
		"environment", opts.Environment,
	)

	return client, nil
}

// Start initializes and starts all client components
func (c *Client) Start(ctx context.Context) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.started {
		return errors.New("client already started", errors.ErrInvalidOperation)
	}

	c.logger.Info("Starting Whitehorse client")

	// Start metrics collector
	if c.metrics != nil {
		if err := c.metrics.Start(ctx); err != nil {
			c.logger.Error("Failed to start metrics collector", "error", err)
			return fmt.Errorf("failed to start metrics: %w", err)
		}
	}

	c.started = true
	c.logger.Info("Whitehorse client started successfully")

	return nil
}

// Stop gracefully shuts down the client
func (c *Client) Stop(ctx context.Context) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if !c.started {
		return nil
	}

	c.logger.Info("Stopping Whitehorse client")

	// Stop metrics collector
	if c.metrics != nil {
		if err := c.metrics.Stop(ctx); err != nil {
			c.logger.Error("Error stopping metrics collector", "error", err)
		}
	}

	c.started = false
	c.logger.Info("Whitehorse client stopped")

	return nil
}

// Config returns the configuration instance
func (c *Client) Config() *config.Config {
	return c.config
}

// Logger returns the logger instance
func (c *Client) Logger() *logging.Logger {
	return c.logger
}

// Metrics returns the metrics collector instance
func (c *Client) Metrics() *metrics.Collector {
	return c.metrics
}

// Health returns the health status of the client
func (c *Client) Health(ctx context.Context) (*HealthStatus, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	status := &HealthStatus{
		Service:   c.config.ServiceName(),
		Version:   Version,
		Timestamp: time.Now().UTC(),
		Started:   c.started,
		Checks:    make(map[string]CheckResult),
	}

	// Check configuration
	if c.config != nil {
		status.Checks["config"] = CheckResult{
			Status:  "healthy",
			Message: "Configuration loaded successfully",
		}
	} else {
		status.Checks["config"] = CheckResult{
			Status:  "unhealthy",
			Message: "Configuration not available",
		}
		status.Overall = "unhealthy"
	}

	// Check logger
	if c.logger != nil {
		status.Checks["logger"] = CheckResult{
			Status:  "healthy",
			Message: "Logger initialized",
		}
	} else {
		status.Checks["logger"] = CheckResult{
			Status:  "unhealthy",
			Message: "Logger not available",
		}
		status.Overall = "unhealthy"
	}

	// Check metrics collector
	if c.metrics != nil {
		if err := c.metrics.Health(ctx); err != nil {
			status.Checks["metrics"] = CheckResult{
				Status:  "unhealthy",
				Message: fmt.Sprintf("Metrics collector error: %v", err),
			}
			if status.Overall != "unhealthy" {
				status.Overall = "degraded"
			}
		} else {
			status.Checks["metrics"] = CheckResult{
				Status:  "healthy",
				Message: "Metrics collector operational",
			}
		}
	} else {
		status.Checks["metrics"] = CheckResult{
			Status:  "disabled",
			Message: "Metrics collector not enabled",
		}
	}

	// Determine overall status
	if status.Overall == "" {
		status.Overall = "healthy"
	}

	return status, nil
}

// HealthStatus represents the overall health of the client
type HealthStatus struct {
	Service   string                 `json:"service"`
	Version   string                 `json:"version"`
	Timestamp time.Time              `json:"timestamp"`
	Started   bool                   `json:"started"`
	Overall   string                 `json:"overall"`
	Checks    map[string]CheckResult `json:"checks"`
}

// CheckResult represents the result of a health check
type CheckResult struct {
	Status  string `json:"status"`
	Message string `json:"message"`
}

// WithContext creates a new context with the Whitehorse client
func (c *Client) WithContext(ctx context.Context) context.Context {
	return context.WithValue(ctx, clientKey{}, c)
}

// FromContext retrieves the Whitehorse client from context
func FromContext(ctx context.Context) (*Client, bool) {
	client, ok := ctx.Value(clientKey{}).(*Client)
	return client, ok
}

// clientKey is used as a key for storing the client in context
type clientKey struct{}

// MustFromContext retrieves the Whitehorse client from context or panics
func MustFromContext(ctx context.Context) *Client {
	client, ok := FromContext(ctx)
	if !ok {
		panic("whitehorse client not found in context")
	}
	return client
}

// Middleware provides common middleware functionality
type Middleware struct {
	client *Client
}

// NewMiddleware creates a new middleware instance
func (c *Client) NewMiddleware() *Middleware {
	return &Middleware{client: c}
}

// WithCorrelationID adds correlation ID to the context and logs
func (m *Middleware) WithCorrelationID(next func(context.Context) error) func(context.Context) error {
	return func(ctx context.Context) error {
		correlationID := logging.GetCorrelationID(ctx)
		if correlationID == "" {
			correlationID = logging.GenerateCorrelationID()
			ctx = logging.WithCorrelationID(ctx, correlationID)
		}

		m.client.logger.WithCorrelationID(correlationID).Info("Processing request")
		return next(ctx)
	}
}

// WithMetrics adds metrics collection to the operation
func (m *Middleware) WithMetrics(operation string, next func(context.Context) error) func(context.Context) error {
	return func(ctx context.Context) error {
		if m.client.metrics == nil {
			return next(ctx)
		}

		start := time.Now()
		err := next(ctx)
		duration := time.Since(start)

		labels := map[string]string{
			"operation": operation,
			"status":    "success",
		}

		if err != nil {
			labels["status"] = "error"
		}

		m.client.metrics.RecordDuration("operation_duration", duration, labels)
		m.client.metrics.IncrementCounter("operations_total", 1, labels)

		return err
	}
}

// WithLogging adds structured logging to the operation
func (m *Middleware) WithLogging(operation string, next func(context.Context) error) func(context.Context) error {
	return func(ctx context.Context) error {
		logger := m.client.logger.WithContext(ctx)
		
		logger.Info("Operation started", "operation", operation)
		start := time.Now()
		
		err := next(ctx)
		duration := time.Since(start)
		
		if err != nil {
			logger.Error("Operation failed",
				"operation", operation,
				"duration", duration,
				"error", err,
			)
		} else {
			logger.Info("Operation completed",
				"operation", operation,
				"duration", duration,
			)
		}
		
		return err
	}
}

// Graceful provides graceful shutdown functionality
type Graceful struct {
	client   *Client
	shutdown chan struct{}
	done     chan struct{}
}

// NewGraceful creates a new graceful shutdown handler
func (c *Client) NewGraceful() *Graceful {
	return &Graceful{
		client:   c,
		shutdown: make(chan struct{}),
		done:     make(chan struct{}),
	}
}

// Shutdown initiates graceful shutdown
func (g *Graceful) Shutdown() {
	close(g.shutdown)
}

// Wait waits for graceful shutdown to complete
func (g *Graceful) Wait(ctx context.Context) error {
	select {
	case <-g.done:
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

// Run runs the graceful shutdown handler
func (g *Graceful) Run(ctx context.Context) {
	defer close(g.done)
	
	select {
	case <-g.shutdown:
		g.client.logger.Info("Graceful shutdown initiated")
		
		// Create shutdown context with timeout
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		
		if err := g.client.Stop(shutdownCtx); err != nil {
			g.client.logger.Error("Error during graceful shutdown", "error", err)
		}
		
	case <-ctx.Done():
		g.client.logger.Info("Context cancelled, stopping graceful handler")
	}
}