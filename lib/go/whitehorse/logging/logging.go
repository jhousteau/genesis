// Package logging provides structured logging with GCP Cloud Logging integration,
// correlation IDs, and consistent formatting across all services.
package logging

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"runtime"
	"strings"
	"time"

	"cloud.google.com/go/logging"
	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
)

// Level represents the logging level
type Level int

const (
	// TraceLevel for very detailed logging
	TraceLevel Level = iota
	// DebugLevel for debug information
	DebugLevel
	// InfoLevel for general information
	InfoLevel
	// WarnLevel for warnings
	WarnLevel
	// ErrorLevel for errors
	ErrorLevel
	// FatalLevel for fatal errors
	FatalLevel
)

// String returns the string representation of the level
func (l Level) String() string {
	switch l {
	case TraceLevel:
		return "trace"
	case DebugLevel:
		return "debug"
	case InfoLevel:
		return "info"
	case WarnLevel:
		return "warn"
	case ErrorLevel:
		return "error"
	case FatalLevel:
		return "fatal"
	default:
		return "unknown"
	}
}

// Options configures the logger
type Options struct {
	Level         string
	ServiceName   string
	Environment   string
	GCPProject    string
	Format        string // "json" or "text"
	EnableGCP     bool
	EnableConsole bool
	Output        io.Writer
}

// Logger provides structured logging capabilities
type Logger struct {
	logger      *logrus.Logger
	gcpLogger   *logging.Logger
	serviceName string
	environment string
	gcpProject  string
}

// correlationIDKey is the context key for correlation ID
type correlationIDKey struct{}

// New creates a new logger instance
func New(opts *Options) (*Logger, error) {
	if opts == nil {
		opts = &Options{
			Level:         "info",
			ServiceName:   "whitehorse-service",
			Environment:   "development",
			Format:        "json",
			EnableConsole: true,
		}
	}

	// Create logrus logger
	logrusLogger := logrus.New()

	// Set level
	level, err := logrus.ParseLevel(opts.Level)
	if err != nil {
		level = logrus.InfoLevel
	}
	logrusLogger.SetLevel(level)

	// Set output
	if opts.Output != nil {
		logrusLogger.SetOutput(opts.Output)
	} else if opts.EnableConsole {
		logrusLogger.SetOutput(os.Stdout)
	}

	// Set formatter
	if opts.Format == "json" {
		logrusLogger.SetFormatter(&StructuredFormatter{
			ServiceName: opts.ServiceName,
			Environment: opts.Environment,
		})
	} else {
		logrusLogger.SetFormatter(&logrus.TextFormatter{
			FullTimestamp: true,
			TimestampFormat: time.RFC3339,
		})
	}

	logger := &Logger{
		logger:      logrusLogger,
		serviceName: opts.ServiceName,
		environment: opts.Environment,
		gcpProject:  opts.GCPProject,
	}

	// Initialize GCP logging if enabled
	if opts.EnableGCP && opts.GCPProject != "" {
		if err := logger.initGCPLogging(); err != nil {
			logrusLogger.Warnf("Failed to initialize GCP logging: %v", err)
		}
	}

	return logger, nil
}

// initGCPLogging initializes GCP Cloud Logging
func (l *Logger) initGCPLogging() error {
	ctx := context.Background()
	client, err := logging.NewClient(ctx, l.gcpProject)
	if err != nil {
		return fmt.Errorf("failed to create GCP logging client: %w", err)
	}

	l.gcpLogger = client.Logger(l.serviceName)
	return nil
}

// StructuredFormatter formats logs as structured JSON
type StructuredFormatter struct {
	ServiceName string
	Environment string
}

// Format implements the logrus.Formatter interface
func (f *StructuredFormatter) Format(entry *logrus.Entry) ([]byte, error) {
	data := make(map[string]interface{})

	// Standard fields
	data["timestamp"] = entry.Time.UTC().Format(time.RFC3339Nano)
	data["level"] = entry.Level.String()
	data["message"] = entry.Message
	data["service"] = f.ServiceName
	data["environment"] = f.Environment

	// Add caller information
	if entry.HasCaller() {
		data["caller"] = fmt.Sprintf("%s:%d", entry.Caller.File, entry.Caller.Line)
		data["function"] = entry.Caller.Function
	}

	// Add custom fields
	for key, value := range entry.Data {
		data[key] = value
	}

	// Marshal to JSON
	serialized, err := json.Marshal(data)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal log entry: %w", err)
	}

	return append(serialized, '\n'), nil
}

// WithField adds a field to the logger
func (l *Logger) WithField(key string, value interface{}) *Logger {
	return &Logger{
		logger:      l.logger.WithField(key, value).Logger,
		gcpLogger:   l.gcpLogger,
		serviceName: l.serviceName,
		environment: l.environment,
		gcpProject:  l.gcpProject,
	}
}

// WithFields adds multiple fields to the logger
func (l *Logger) WithFields(fields map[string]interface{}) *Logger {
	return &Logger{
		logger:      l.logger.WithFields(fields).Logger,
		gcpLogger:   l.gcpLogger,
		serviceName: l.serviceName,
		environment: l.environment,
		gcpProject:  l.gcpProject,
	}
}

// WithError adds an error field to the logger
func (l *Logger) WithError(err error) *Logger {
	return l.WithField("error", err.Error())
}

// WithContext creates a logger with context information
func (l *Logger) WithContext(ctx context.Context) *Logger {
	fields := make(map[string]interface{})

	// Add correlation ID if present
	if correlationID := GetCorrelationID(ctx); correlationID != "" {
		fields["correlation_id"] = correlationID
	}

	return l.WithFields(fields)
}

// WithCorrelationID creates a logger with a correlation ID
func (l *Logger) WithCorrelationID(correlationID string) *Logger {
	return l.WithField("correlation_id", correlationID)
}

// Debug logs at debug level
func (l *Logger) Debug(args ...interface{}) {
	l.log(DebugLevel, fmt.Sprint(args...))
}

// Debugf logs at debug level with formatting
func (l *Logger) Debugf(format string, args ...interface{}) {
	l.log(DebugLevel, fmt.Sprintf(format, args...))
}

// Info logs at info level
func (l *Logger) Info(args ...interface{}) {
	l.log(InfoLevel, fmt.Sprint(args...))
}

// Infof logs at info level with formatting
func (l *Logger) Infof(format string, args ...interface{}) {
	l.log(InfoLevel, fmt.Sprintf(format, args...))
}

// Warn logs at warn level
func (l *Logger) Warn(args ...interface{}) {
	l.log(WarnLevel, fmt.Sprint(args...))
}

// Warnf logs at warn level with formatting
func (l *Logger) Warnf(format string, args ...interface{}) {
	l.log(WarnLevel, fmt.Sprintf(format, args...))
}

// Error logs at error level
func (l *Logger) Error(args ...interface{}) {
	l.log(ErrorLevel, fmt.Sprint(args...))
}

// Errorf logs at error level with formatting
func (l *Logger) Errorf(format string, args ...interface{}) {
	l.log(ErrorLevel, fmt.Sprintf(format, args...))
}

// Fatal logs at fatal level and exits
func (l *Logger) Fatal(args ...interface{}) {
	l.log(FatalLevel, fmt.Sprint(args...))
	os.Exit(1)
}

// Fatalf logs at fatal level with formatting and exits
func (l *Logger) Fatalf(format string, args ...interface{}) {
	l.log(FatalLevel, fmt.Sprintf(format, args...))
	os.Exit(1)
}

// log is the internal logging method
func (l *Logger) log(level Level, message string) {
	// Log to logrus
	switch level {
	case DebugLevel:
		l.logger.Debug(message)
	case InfoLevel:
		l.logger.Info(message)
	case WarnLevel:
		l.logger.Warn(message)
	case ErrorLevel:
		l.logger.Error(message)
	case FatalLevel:
		l.logger.Fatal(message)
	}

	// Log to GCP if available
	if l.gcpLogger != nil {
		l.logToGCP(level, message)
	}
}

// logToGCP sends log entry to GCP Cloud Logging
func (l *Logger) logToGCP(level Level, message string) {
	var severity logging.Severity

	switch level {
	case DebugLevel:
		severity = logging.Debug
	case InfoLevel:
		severity = logging.Info
	case WarnLevel:
		severity = logging.Warning
	case ErrorLevel:
		severity = logging.Error
	case FatalLevel:
		severity = logging.Critical
	default:
		severity = logging.Info
	}

	entry := logging.Entry{
		Timestamp: time.Now(),
		Severity:  severity,
		Payload:   message,
	}

	l.gcpLogger.Log(entry)
}

// SetLevel sets the logging level
func (l *Logger) SetLevel(level string) {
	logrusLevel, err := logrus.ParseLevel(level)
	if err != nil {
		l.logger.Warnf("Invalid log level %s, keeping current level", level)
		return
	}
	l.logger.SetLevel(logrusLevel)
}

// GetLevel returns the current logging level
func (l *Logger) GetLevel() string {
	return l.logger.GetLevel().String()
}

// Performance logging
type PerformanceLogger struct {
	logger    *Logger
	operation string
	startTime time.Time
	fields    map[string]interface{}
}

// StartOperation begins performance logging for an operation
func (l *Logger) StartOperation(operation string) *PerformanceLogger {
	return &PerformanceLogger{
		logger:    l,
		operation: operation,
		startTime: time.Now(),
		fields:    make(map[string]interface{}),
	}
}

// WithField adds a field to the performance logger
func (p *PerformanceLogger) WithField(key string, value interface{}) *PerformanceLogger {
	p.fields[key] = value
	return p
}

// Success logs successful completion of the operation
func (p *PerformanceLogger) Success() {
	duration := time.Since(p.startTime)
	fields := make(map[string]interface{})
	for k, v := range p.fields {
		fields[k] = v
	}
	fields["operation"] = p.operation
	fields["duration_ms"] = duration.Milliseconds()
	fields["success"] = true

	p.logger.WithFields(fields).Infof("Operation completed: %s", p.operation)
}

// Error logs failed completion of the operation
func (p *PerformanceLogger) Error(err error) {
	duration := time.Since(p.startTime)
	fields := make(map[string]interface{})
	for k, v := range p.fields {
		fields[k] = v
	}
	fields["operation"] = p.operation
	fields["duration_ms"] = duration.Milliseconds()
	fields["success"] = false
	fields["error"] = err.Error()

	p.logger.WithFields(fields).Errorf("Operation failed: %s", p.operation)
}

// Correlation ID utilities

// GenerateCorrelationID generates a new correlation ID
func GenerateCorrelationID() string {
	return uuid.New().String()
}

// WithCorrelationID adds correlation ID to context
func WithCorrelationID(ctx context.Context, correlationID string) context.Context {
	return context.WithValue(ctx, correlationIDKey{}, correlationID)
}

// GetCorrelationID retrieves correlation ID from context
func GetCorrelationID(ctx context.Context) string {
	if ctx == nil {
		return ""
	}
	if correlationID, ok := ctx.Value(correlationIDKey{}).(string); ok {
		return correlationID
	}
	return ""
}

// GetOrGenerateCorrelationID gets existing correlation ID or generates a new one
func GetOrGenerateCorrelationID(ctx context.Context) (context.Context, string) {
	correlationID := GetCorrelationID(ctx)
	if correlationID == "" {
		correlationID = GenerateCorrelationID()
		ctx = WithCorrelationID(ctx, correlationID)
	}
	return ctx, correlationID
}

// Helper functions for structured logging

// LogHTTPRequest logs an HTTP request
func (l *Logger) LogHTTPRequest(method, path, userAgent, remoteAddr string, statusCode int, duration time.Duration) {
	l.WithFields(map[string]interface{}{
		"method":      method,
		"path":        path,
		"user_agent":  userAgent,
		"remote_addr": remoteAddr,
		"status_code": statusCode,
		"duration_ms": duration.Milliseconds(),
	}).Info("HTTP request")
}

// LogDatabaseQuery logs a database query
func (l *Logger) LogDatabaseQuery(query string, duration time.Duration, err error) {
	fields := map[string]interface{}{
		"query":       maskSensitiveData(query),
		"duration_ms": duration.Milliseconds(),
	}

	if err != nil {
		fields["error"] = err.Error()
		l.WithFields(fields).Error("Database query failed")
	} else {
		l.WithFields(fields).Debug("Database query executed")
	}
}

// LogExternalCall logs an external service call
func (l *Logger) LogExternalCall(service, endpoint string, duration time.Duration, statusCode int, err error) {
	fields := map[string]interface{}{
		"service":     service,
		"endpoint":    endpoint,
		"duration_ms": duration.Milliseconds(),
		"status_code": statusCode,
	}

	if err != nil {
		fields["error"] = err.Error()
		l.WithFields(fields).Error("External service call failed")
	} else {
		l.WithFields(fields).Info("External service call completed")
	}
}

// Security logging

// LogSecurityEvent logs a security-related event
func (l *Logger) LogSecurityEvent(eventType, userID, ipAddress string, details map[string]interface{}) {
	fields := map[string]interface{}{
		"event_type":  eventType,
		"user_id":     userID,
		"ip_address":  ipAddress,
		"timestamp":   time.Now().UTC(),
	}

	for k, v := range details {
		fields[k] = v
	}

	l.WithFields(fields).Warn("Security event")
}

// LogAuthEvent logs an authentication event
func (l *Logger) LogAuthEvent(action, userID, ipAddress string, success bool, details map[string]interface{}) {
	fields := map[string]interface{}{
		"action":     action,
		"user_id":    userID,
		"ip_address": ipAddress,
		"success":    success,
		"timestamp":  time.Now().UTC(),
	}

	for k, v := range details {
		fields[k] = v
	}

	if success {
		l.WithFields(fields).Info("Authentication event")
	} else {
		l.WithFields(fields).Warn("Authentication failed")
	}
}

// Utility functions

// maskSensitiveData masks sensitive information in strings
func maskSensitiveData(data string) string {
	// Simple masking for common sensitive patterns
	patterns := []string{"password", "token", "secret", "key"}
	
	for _, pattern := range patterns {
		if strings.Contains(strings.ToLower(data), pattern) {
			// This is a simple implementation - in production, use more sophisticated masking
			return "[MASKED]"
		}
	}
	
	return data
}

// getCaller returns information about the calling function
func getCaller() (string, string, int) {
	pc, file, line, ok := runtime.Caller(3) // Skip 3 frames to get the actual caller
	if !ok {
		return "unknown", "unknown", 0
	}

	function := runtime.FuncForPC(pc).Name()
	
	// Extract just the filename
	if idx := strings.LastIndex(file, "/"); idx >= 0 {
		file = file[idx+1:]
	}

	return function, file, line
}

// Flush ensures all log entries are written
func (l *Logger) Flush() {
	if l.gcpLogger != nil {
		l.gcpLogger.Flush()
	}
}

// Close closes the logger and releases resources
func (l *Logger) Close() error {
	l.Flush()
	return nil
}