// Package errors provides comprehensive error handling with structured error information,
// error categories, and integration with monitoring systems.
package errors

import (
	"encoding/json"
	"fmt"
	"runtime"
	"strings"
	"time"
)

// ErrorCode represents a specific error code
type ErrorCode string

// Common error codes
const (
	ErrInvalidInput      ErrorCode = "INVALID_INPUT"
	ErrNotFound          ErrorCode = "NOT_FOUND"
	ErrUnauthorized      ErrorCode = "UNAUTHORIZED"
	ErrForbidden         ErrorCode = "FORBIDDEN"
	ErrInternalError     ErrorCode = "INTERNAL_ERROR"
	ErrExternalService   ErrorCode = "EXTERNAL_SERVICE"
	ErrTimeout           ErrorCode = "TIMEOUT"
	ErrRateLimited       ErrorCode = "RATE_LIMITED"
	ErrValidationFailed  ErrorCode = "VALIDATION_FAILED"
	ErrConfigurationError ErrorCode = "CONFIGURATION_ERROR"
	ErrDatabaseError     ErrorCode = "DATABASE_ERROR"
	ErrNetworkError      ErrorCode = "NETWORK_ERROR"
	ErrInvalidOperation  ErrorCode = "INVALID_OPERATION"
)

// Severity represents the severity level of an error
type Severity int

const (
	SeverityLow Severity = iota
	SeverityMedium
	SeverityHigh
	SeverityCritical
)

// String returns the string representation of severity
func (s Severity) String() string {
	switch s {
	case SeverityLow:
		return "low"
	case SeverityMedium:
		return "medium"
	case SeverityHigh:
		return "high"
	case SeverityCritical:
		return "critical"
	default:
		return "unknown"
	}
}

// Category represents the category of an error
type Category int

const (
	CategoryValidation Category = iota
	CategoryAuthentication
	CategoryAuthorization
	CategoryNetwork
	CategoryDatabase
	CategoryExternalService
	CategoryConfiguration
	CategoryBusinessLogic
	CategorySystem
	CategoryUnknown
)

// String returns the string representation of category
func (c Category) String() string {
	switch c {
	case CategoryValidation:
		return "validation"
	case CategoryAuthentication:
		return "authentication"
	case CategoryAuthorization:
		return "authorization"
	case CategoryNetwork:
		return "network"
	case CategoryDatabase:
		return "database"
	case CategoryExternalService:
		return "external_service"
	case CategoryConfiguration:
		return "configuration"
	case CategoryBusinessLogic:
		return "business_logic"
	case CategorySystem:
		return "system"
	default:
		return "unknown"
	}
}

// StackFrame represents a single frame in the stack trace
type StackFrame struct {
	Function string `json:"function"`
	File     string `json:"file"`
	Line     int    `json:"line"`
}

// WhitehorseError is the base error type for all Whitehorse errors
type WhitehorseError struct {
	Code         ErrorCode              `json:"code"`
	Message      string                 `json:"message"`
	UserMessage  string                 `json:"user_message,omitempty"`
	Severity     Severity               `json:"severity"`
	Category     Category               `json:"category"`
	Timestamp    time.Time              `json:"timestamp"`
	Recoverable  bool                   `json:"recoverable"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
	Cause        error                  `json:"cause,omitempty"`
	StackTrace   []StackFrame           `json:"stack_trace,omitempty"`
	CorrelationID string                `json:"correlation_id,omitempty"`
}

// Error implements the error interface
func (e *WhitehorseError) Error() string {
	return fmt.Sprintf("[%s] %s", e.Code, e.Message)
}

// Unwrap implements the unwrap interface for error wrapping
func (e *WhitehorseError) Unwrap() error {
	return e.Cause
}

// Is implements the Is interface for error comparison
func (e *WhitehorseError) Is(target error) bool {
	if other, ok := target.(*WhitehorseError); ok {
		return e.Code == other.Code
	}
	return false
}

// MarshalJSON implements the json.Marshaler interface
func (e *WhitehorseError) MarshalJSON() ([]byte, error) {
	type Alias WhitehorseError
	return json.Marshal(&struct {
		*Alias
		Severity string `json:"severity"`
		Category string `json:"category"`
		Cause    string `json:"cause,omitempty"`
	}{
		Alias:    (*Alias)(e),
		Severity: e.Severity.String(),
		Category: e.Category.String(),
		Cause:    fmt.Sprintf("%v", e.Cause),
	})
}

// ToMap converts the error to a map for logging/monitoring
func (e *WhitehorseError) ToMap() map[string]interface{} {
	result := map[string]interface{}{
		"error_code":     string(e.Code),
		"message":        e.Message,
		"severity":       e.Severity.String(),
		"category":       e.Category.String(),
		"timestamp":      e.Timestamp,
		"recoverable":    e.Recoverable,
	}

	if e.UserMessage != "" {
		result["user_message"] = e.UserMessage
	}

	if e.CorrelationID != "" {
		result["correlation_id"] = e.CorrelationID
	}

	if e.Cause != nil {
		result["cause"] = e.Cause.Error()
	}

	if e.Metadata != nil {
		result["metadata"] = e.Metadata
	}

	if len(e.StackTrace) > 0 {
		result["stack_trace"] = e.StackTrace
	}

	return result
}

// WithMetadata adds metadata to the error
func (e *WhitehorseError) WithMetadata(key string, value interface{}) *WhitehorseError {
	if e.Metadata == nil {
		e.Metadata = make(map[string]interface{})
	}
	e.Metadata[key] = value
	return e
}

// WithCorrelationID adds a correlation ID to the error
func (e *WhitehorseError) WithCorrelationID(correlationID string) *WhitehorseError {
	e.CorrelationID = correlationID
	return e
}

// WithUserMessage sets a user-friendly message
func (e *WhitehorseError) WithUserMessage(message string) *WhitehorseError {
	e.UserMessage = message
	return e
}

// New creates a new WhitehorseError
func New(message string, code ErrorCode, options ...Option) *WhitehorseError {
	err := &WhitehorseError{
		Code:        code,
		Message:     message,
		Severity:    SeverityMedium,
		Category:    CategoryUnknown,
		Timestamp:   time.Now().UTC(),
		Recoverable: false,
		StackTrace:  captureStackTrace(),
	}

	for _, option := range options {
		option(err)
	}

	return err
}

// Wrap wraps an existing error with additional context
func Wrap(err error, message string, code ErrorCode, options ...Option) *WhitehorseError {
	if err == nil {
		return nil
	}

	whErr := &WhitehorseError{
		Code:        code,
		Message:     message,
		Cause:       err,
		Severity:    SeverityMedium,
		Category:    CategoryUnknown,
		Timestamp:   time.Now().UTC(),
		Recoverable: false,
		StackTrace:  captureStackTrace(),
	}

	// If wrapping another WhitehorseError, inherit some properties
	if existingErr, ok := err.(*WhitehorseError); ok {
		whErr.Severity = existingErr.Severity
		whErr.Category = existingErr.Category
		whErr.Recoverable = existingErr.Recoverable
		if existingErr.CorrelationID != "" {
			whErr.CorrelationID = existingErr.CorrelationID
		}
	}

	for _, option := range options {
		option(whErr)
	}

	return whErr
}

// Option represents a configuration option for errors
type Option func(*WhitehorseError)

// WithSeverity sets the error severity
func WithSeverity(severity Severity) Option {
	return func(e *WhitehorseError) {
		e.Severity = severity
	}
}

// WithCategory sets the error category
func WithCategory(category Category) Option {
	return func(e *WhitehorseError) {
		e.Category = category
	}
}

// WithRecoverable sets whether the error is recoverable
func WithRecoverable(recoverable bool) Option {
	return func(e *WhitehorseError) {
		e.Recoverable = recoverable
	}
}

// WithUserMsg sets a user-friendly message
func WithUserMsg(message string) Option {
	return func(e *WhitehorseError) {
		e.UserMessage = message
	}
}

// WithMetadata adds metadata to the error
func WithMetadata(metadata map[string]interface{}) Option {
	return func(e *WhitehorseError) {
		if e.Metadata == nil {
			e.Metadata = make(map[string]interface{})
		}
		for k, v := range metadata {
			e.Metadata[k] = v
		}
	}
}

// WithCorrelationID adds a correlation ID
func WithCorrelationID(correlationID string) Option {
	return func(e *WhitehorseError) {
		e.CorrelationID = correlationID
	}
}

// captureStackTrace captures the current stack trace
func captureStackTrace() []StackFrame {
	var frames []StackFrame

	// Skip the first few frames (captureStackTrace, New/Wrap, etc.)
	for i := 2; i < 10; i++ {
		pc, file, line, ok := runtime.Caller(i)
		if !ok {
			break
		}

		function := runtime.FuncForPC(pc).Name()

		// Stop at main or test functions
		if strings.Contains(function, "main.") || strings.Contains(function, "testing.") {
			break
		}

		// Extract just the filename
		if idx := strings.LastIndex(file, "/"); idx >= 0 {
			file = file[idx+1:]
		}

		frames = append(frames, StackFrame{
			Function: function,
			File:     file,
			Line:     line,
		})
	}

	return frames
}

// Predefined error constructors

// NewValidationError creates a validation error
func NewValidationError(message string, field string) *WhitehorseError {
	return New(message, ErrValidationFailed,
		WithCategory(CategoryValidation),
		WithSeverity(SeverityLow),
		WithRecoverable(true),
		WithMetadata(map[string]interface{}{"field": field}),
	)
}

// NewNotFoundError creates a not found error
func NewNotFoundError(resource string) *WhitehorseError {
	return New(fmt.Sprintf("%s not found", resource), ErrNotFound,
		WithCategory(CategoryBusinessLogic),
		WithSeverity(SeverityMedium),
		WithRecoverable(false),
		WithMetadata(map[string]interface{}{"resource": resource}),
		WithUserMsg(fmt.Sprintf("The requested %s could not be found", resource)),
	)
}

// NewUnauthorizedError creates an unauthorized error
func NewUnauthorizedError(message string) *WhitehorseError {
	return New(message, ErrUnauthorized,
		WithCategory(CategoryAuthentication),
		WithSeverity(SeverityHigh),
		WithRecoverable(false),
		WithUserMsg("Authentication required"),
	)
}

// NewForbiddenError creates a forbidden error
func NewForbiddenError(message string) *WhitehorseError {
	return New(message, ErrForbidden,
		WithCategory(CategoryAuthorization),
		WithSeverity(SeverityHigh),
		WithRecoverable(false),
		WithUserMsg("Access denied"),
	)
}

// NewInternalError creates an internal error
func NewInternalError(message string) *WhitehorseError {
	return New(message, ErrInternalError,
		WithCategory(CategorySystem),
		WithSeverity(SeverityCritical),
		WithRecoverable(false),
		WithUserMsg("An internal error occurred"),
	)
}

// NewExternalServiceError creates an external service error
func NewExternalServiceError(service string, message string) *WhitehorseError {
	return New(message, ErrExternalService,
		WithCategory(CategoryExternalService),
		WithSeverity(SeverityMedium),
		WithRecoverable(true),
		WithMetadata(map[string]interface{}{"service": service}),
		WithUserMsg("External service temporarily unavailable"),
	)
}

// NewTimeoutError creates a timeout error
func NewTimeoutError(operation string, timeout time.Duration) *WhitehorseError {
	return New(fmt.Sprintf("Operation %s timed out after %v", operation, timeout), ErrTimeout,
		WithCategory(CategorySystem),
		WithSeverity(SeverityMedium),
		WithRecoverable(true),
		WithMetadata(map[string]interface{}{
			"operation": operation,
			"timeout":   timeout.String(),
		}),
		WithUserMsg("Operation timed out, please try again"),
	)
}

// NewDatabaseError creates a database error
func NewDatabaseError(operation string, err error) *WhitehorseError {
	return Wrap(err, fmt.Sprintf("Database operation failed: %s", operation), ErrDatabaseError,
		WithCategory(CategoryDatabase),
		WithSeverity(SeverityHigh),
		WithRecoverable(false),
		WithMetadata(map[string]interface{}{"operation": operation}),
		WithUserMsg("Database operation failed"),
	)
}

// NewNetworkError creates a network error
func NewNetworkError(endpoint string, err error) *WhitehorseError {
	return Wrap(err, fmt.Sprintf("Network error connecting to %s", endpoint), ErrNetworkError,
		WithCategory(CategoryNetwork),
		WithSeverity(SeverityMedium),
		WithRecoverable(true),
		WithMetadata(map[string]interface{}{"endpoint": endpoint}),
		WithUserMsg("Network connectivity issue"),
	)
}

// NewConfigurationError creates a configuration error
func NewConfigurationError(key string, message string) *WhitehorseError {
	return New(message, ErrConfigurationError,
		WithCategory(CategoryConfiguration),
		WithSeverity(SeverityHigh),
		WithRecoverable(false),
		WithMetadata(map[string]interface{}{"config_key": key}),
		WithUserMsg("Configuration error"),
	)
}

// Error handling utilities

// IsRetryable checks if an error is retryable
func IsRetryable(err error) bool {
	if whErr, ok := err.(*WhitehorseError); ok {
		return whErr.Recoverable && (whErr.Category == CategoryNetwork ||
			whErr.Category == CategoryExternalService ||
			whErr.Code == ErrTimeout ||
			whErr.Code == ErrRateLimited)
	}
	return false
}

// GetErrorCode extracts the error code from an error
func GetErrorCode(err error) ErrorCode {
	if whErr, ok := err.(*WhitehorseError); ok {
		return whErr.Code
	}
	return ErrInternalError
}

// GetSeverity extracts the severity from an error
func GetSeverity(err error) Severity {
	if whErr, ok := err.(*WhitehorseError); ok {
		return whErr.Severity
	}
	return SeverityMedium
}

// GetCategory extracts the category from an error
func GetCategory(err error) Category {
	if whErr, ok := err.(*WhitehorseError); ok {
		return whErr.Category
	}
	return CategoryUnknown
}

// GetUserMessage extracts a user-friendly message from an error
func GetUserMessage(err error) string {
	if whErr, ok := err.(*WhitehorseError); ok && whErr.UserMessage != "" {
		return whErr.UserMessage
	}
	return "An error occurred"
}

// Multi-error support

// MultiError represents multiple errors
type MultiError struct {
	Errors []error
}

// Error implements the error interface
func (m *MultiError) Error() string {
	if len(m.Errors) == 0 {
		return "no errors"
	}
	if len(m.Errors) == 1 {
		return m.Errors[0].Error()
	}

	var messages []string
	for _, err := range m.Errors {
		messages = append(messages, err.Error())
	}
	return fmt.Sprintf("multiple errors: %s", strings.Join(messages, "; "))
}

// Add adds an error to the multi-error
func (m *MultiError) Add(err error) {
	if err != nil {
		m.Errors = append(m.Errors, err)
	}
}

// HasErrors returns true if there are any errors
func (m *MultiError) HasErrors() bool {
	return len(m.Errors) > 0
}

// ToError returns the multi-error as an error, or nil if no errors
func (m *MultiError) ToError() error {
	if !m.HasErrors() {
		return nil
	}
	return m
}

// NewMultiError creates a new multi-error
func NewMultiError() *MultiError {
	return &MultiError{}
}
