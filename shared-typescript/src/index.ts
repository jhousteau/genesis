/**
 * @genesis/typescript - TypeScript shared utilities
 *
 * Core functionality including configuration, health checks, logging, retry logic,
 * error handling, and context management.
 */

// Config utilities
export {
  ConfigLoader,
  GenesisConfigLoader,
  TypedConfig,
  ConfigPresets,
  loadConfig,
  createConfigLoader,
} from './config';

// Context management
export {
  TraceContext,
  RequestContext,
  ContextManager,
  getContext,
  setContext,
  clearContext,
  contextSpan,
  contextSpanSync,
  getCorrelationId,
  setCorrelationId,
  getRequestId,
  getTraceId,
  getUserId,
  getMetadata,
  generateCorrelationId,
  generateRequestId,
  generateTraceId,
  generateSpanId,
  createRequestContext,
  createTraceContext,
  enrichContext,
  contextToDict,
  getLoggerContext,
  createContextMiddleware,
} from './context';

// Error handling
export {
  ErrorSeverity,
  ErrorCategory,
  ErrorContext,
  GenesisErrorOptions,
  GenesisError,
  InfrastructureError,
  NetworkError,
  ValidationError,
  AuthenticationError,
  AuthorizationError,
  TimeoutError,
  RateLimitError,
  ExternalServiceError,
  ResourceError,
  ErrorHandler,
  createErrorContext,
  getErrorHandler,
  handleError,
} from './errors';

// Health checks
export {
  HealthStatus,
  CheckResult,
  HealthSummary,
  HealthCheckFunction,
  HealthCheck,
  HealthChecks,
} from './health';

// Logging
export {
  LogLevel,
  LogConfig,
  LogEntry,
  Logger,
  getLogger,
  createChildLogger,
  LoggerPresets,
} from './logger';

// Retry and circuit breaker
export {
  RetryConfig,
  CircuitBreakerState,
  CircuitBreakerMetrics,
  CircuitBreakerConfig,
  CircuitBreakerError,
  CircuitBreaker,
  retry,
  retryFunction,
  circuitBreaker,
  resilientCall,
  resilientExternalService,
  resilientDatabase,
} from './retry';
