/**
 * Genesis Error Handling - Simplified and Enhanced
 *
 * Provides structured error handling with:
 * - 14 error categories for proper classification
 * - Correlation ID tracking for request tracing
 * - Context preservation across operations
 * - Automatic error enrichment
 */

export enum ErrorSeverity {
  DEBUG = 'debug',
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

export enum ErrorCategory {
  INFRASTRUCTURE = 'infrastructure',
  APPLICATION = 'application',
  NETWORK = 'network',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  VALIDATION = 'validation',
  CONFIGURATION = 'configuration',
  EXTERNAL_SERVICE = 'external_service',
  RESOURCE = 'resource',
  RESOURCE_EXHAUSTED = 'resource_exhausted',
  TIMEOUT = 'timeout',
  RATE_LIMIT = 'rate_limit',
  UNAVAILABLE = 'unavailable',
  UNKNOWN = 'unknown',
}

export interface ErrorContext {
  correlationId: string;
  timestamp: Date;
  service: string;
  environment: string;
  userId?: string;
  requestId?: string;
  traceId?: string;
  spanId?: string;
  metadata?: Record<string, any>;
}

export interface GenesisErrorOptions {
  message: string;
  code?: string;
  category?: ErrorCategory;
  severity?: ErrorSeverity;
  context?: ErrorContext;
  cause?: Error;
  details?: Record<string, any>;
  retryAfter?: number;
  recoverable?: boolean;
}

export function createErrorContext(
  service?: string,
  environment?: string
): ErrorContext {
  return {
    correlationId: crypto.randomUUID(),
    timestamp: new Date(),
    service: service || process.env.SERVICE || 'genesis',
    environment: environment || process.env.ENV || 'development',
  };
}

/**
 * Base exception class for all Genesis errors
 */
export class GenesisError extends Error {
  public readonly code: string;
  public readonly category: ErrorCategory;
  public readonly severity: ErrorSeverity;
  public readonly context: ErrorContext;
  public readonly cause?: Error;
  public readonly details: Record<string, any>;
  public readonly retryAfter?: number;
  public readonly recoverable: boolean;
  public readonly stackTrace: string[];

  constructor(options: GenesisErrorOptions) {
    super(options.message);
    this.name = 'GenesisError';

    this.code = options.code || 'GENESIS_ERROR';
    this.category = options.category || ErrorCategory.UNKNOWN;
    this.severity = options.severity || ErrorSeverity.ERROR;
    this.context = options.context || this.createDefaultContext();
    this.cause = options.cause;
    this.details = options.details || {};
    this.retryAfter = options.retryAfter;
    this.recoverable = options.recoverable !== false;
    this.stackTrace = this.captureStackTrace();

    // Maintain prototype chain
    Object.setPrototypeOf(this, GenesisError.prototype);
  }

  private createDefaultContext(): ErrorContext {
    return createErrorContext(
      process.env.SERVICE || 'genesis',
      process.env.ENV || 'development'
    );
  }

  private captureStackTrace(): string[] {
    const stack = this.stack || '';
    return stack.split('\n').slice(1); // Remove first line (error message)
  }

  toJSON(): Record<string, any> {
    const errorData: Record<string, any> = {
      error: {
        message: this.message,
        code: this.code,
        category: this.category,
        severity: this.severity,
        recoverable: this.recoverable,
        timestamp: new Date().toISOString(),
      },
      context: {
        correlationId: this.context.correlationId,
        timestamp: this.context.timestamp.toISOString(),
        service: this.context.service,
        environment: this.context.environment,
        userId: this.context.userId,
        requestId: this.context.requestId,
        traceId: this.context.traceId,
        spanId: this.context.spanId,
        metadata: this.context.metadata || {},
      },
      details: this.details,
    };

    if (this.retryAfter) {
      errorData.error.retryAfter = this.retryAfter;
    }

    if (this.cause) {
      errorData.cause = {
        type: this.cause.constructor.name,
        message: this.cause.message,
      };
    }

    // Include stack trace for errors and critical issues
    if (this.severity === ErrorSeverity.ERROR || this.severity === ErrorSeverity.CRITICAL) {
      errorData.error.stackTrace = this.stackTrace.slice(-10); // Last 10 frames
    }

    return errorData;
  }

  toString(): string {
    return JSON.stringify(this.toJSON(), null, 2);
  }
}

/**
 * Infrastructure and platform-related errors
 */
export class InfrastructureError extends GenesisError {
  constructor(message: string, options: Partial<GenesisErrorOptions> = {}) {
    super({
      message,
      code: 'INFRASTRUCTURE_ERROR',
      category: ErrorCategory.INFRASTRUCTURE,
      ...options,
    });
    this.name = 'InfrastructureError';
    Object.setPrototypeOf(this, InfrastructureError.prototype);
  }
}

/**
 * Network connectivity and communication errors
 */
export class NetworkError extends GenesisError {
  constructor(message: string, endpoint?: string, options: Partial<GenesisErrorOptions> = {}) {
    const details = { ...options.details };
    if (endpoint) {
      details.endpoint = endpoint;
    }

    super({
      message,
      code: 'NETWORK_ERROR',
      category: ErrorCategory.NETWORK,
      details,
      ...options,
    });
    this.name = 'NetworkError';
    Object.setPrototypeOf(this, NetworkError.prototype);
  }
}

/**
 * Data validation and format errors
 */
export class ValidationError extends GenesisError {
  constructor(message: string, field?: string, options: Partial<GenesisErrorOptions> = {}) {
    const details = { ...options.details };
    if (field) {
      details.field = field;
    }

    super({
      message,
      code: 'VALIDATION_ERROR',
      category: ErrorCategory.VALIDATION,
      severity: ErrorSeverity.WARNING,
      details,
      ...options,
    });
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

/**
 * Authentication failures
 */
export class AuthenticationError extends GenesisError {
  constructor(message: string, options: Partial<GenesisErrorOptions> = {}) {
    super({
      message,
      code: 'AUTHENTICATION_ERROR',
      category: ErrorCategory.AUTHENTICATION,
      recoverable: false,
      ...options,
    });
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

/**
 * Authorization and permission errors
 */
export class AuthorizationError extends GenesisError {
  constructor(message: string, resource?: string, options: Partial<GenesisErrorOptions> = {}) {
    const details = { ...options.details };
    if (resource) {
      details.resource = resource;
    }

    super({
      message,
      code: 'AUTHORIZATION_ERROR',
      category: ErrorCategory.AUTHORIZATION,
      recoverable: false,
      details,
      ...options,
    });
    this.name = 'AuthorizationError';
    Object.setPrototypeOf(this, AuthorizationError.prototype);
  }
}

/**
 * Timeout and deadline exceeded errors
 */
export class TimeoutError extends GenesisError {
  constructor(message: string, timeoutDuration?: number, options: Partial<GenesisErrorOptions> = {}) {
    const details = { ...options.details };
    if (timeoutDuration) {
      details.timeoutDuration = timeoutDuration;
    }

    super({
      message,
      code: 'TIMEOUT_ERROR',
      category: ErrorCategory.TIMEOUT,
      details,
      ...options,
    });
    this.name = 'TimeoutError';
    Object.setPrototypeOf(this, TimeoutError.prototype);
  }
}

/**
 * Rate limiting and throttling errors
 */
export class RateLimitError extends GenesisError {
  constructor(message: string, retryAfter?: number, options: Partial<GenesisErrorOptions> = {}) {
    super({
      message,
      code: 'RATE_LIMIT_ERROR',
      category: ErrorCategory.RATE_LIMIT,
      retryAfter,
      ...options,
    });
    this.name = 'RateLimitError';
    Object.setPrototypeOf(this, RateLimitError.prototype);
  }
}

/**
 * External service and API errors
 */
export class ExternalServiceError extends GenesisError {
  constructor(message: string, serviceName?: string, options: Partial<GenesisErrorOptions> = {}) {
    const details = { ...options.details };
    if (serviceName) {
      details.serviceName = serviceName;
    }

    super({
      message,
      code: 'EXTERNAL_SERVICE_ERROR',
      category: ErrorCategory.EXTERNAL_SERVICE,
      details,
      ...options,
    });
    this.name = 'ExternalServiceError';
    Object.setPrototypeOf(this, ExternalServiceError.prototype);
  }
}

/**
 * Resource not found or access errors
 */
export class ResourceError extends GenesisError {
  constructor(message: string, resourceType?: string, options: Partial<GenesisErrorOptions> = {}) {
    const details = { ...options.details };
    if (resourceType) {
      details.resourceType = resourceType;
    }

    super({
      message,
      code: 'RESOURCE_ERROR',
      category: ErrorCategory.RESOURCE,
      details,
      ...options,
    });
    this.name = 'ResourceError';
    Object.setPrototypeOf(this, ResourceError.prototype);
  }
}

/**
 * Central error handler for processing and converting exceptions
 */
export class ErrorHandler {
  private handlers: Array<(error: GenesisError) => void> = [];

  constructor(
    private serviceName: string = 'genesis',
    private environment: string = 'development'
  ) {}

  handle(error: Error, context?: ErrorContext): GenesisError {
    // If already a GenesisError, enrich with context if provided
    if (error instanceof GenesisError) {
      if (context) {
        (error as any).context = context;
      }
      return error;
    }

    // Convert standard exceptions to GenesisError
    const genesisError = this.convertToGenesisError(error, context);

    // Process through registered handlers
    for (const handler of this.handlers) {
      try {
        handler(genesisError);
      } catch {
        // Don't let handler errors break error handling
      }
    }

    return genesisError;
  }

  private convertToGenesisError(error: Error, context?: ErrorContext): GenesisError {
    // Create context if not provided
    if (!context) {
      context = createErrorContext(this.serviceName, this.environment);
    }

    // Map standard errors to Genesis error types
    if (error instanceof TypeError || error instanceof RangeError || error instanceof ReferenceError) {
      return new ValidationError(error.message, undefined, { context, cause: error });
    }

    return new GenesisError({ message: error.message, context, cause: error });
  }

  addHandler(handler: (error: GenesisError) => void): void {
    this.handlers.push(handler);
  }
}

// Global error handler instance
let globalErrorHandler: ErrorHandler | undefined;

export function getErrorHandler(): ErrorHandler {
  if (!globalErrorHandler) {
    globalErrorHandler = new ErrorHandler(
      process.env.SERVICE || 'genesis',
      process.env.ENV || 'development'
    );
  }
  return globalErrorHandler;
}

/**
 * Convenience function to handle errors with the global handler
 */
export function handleError(error: Error, context?: ErrorContext): GenesisError {
  return getErrorHandler().handle(error, context);
}
