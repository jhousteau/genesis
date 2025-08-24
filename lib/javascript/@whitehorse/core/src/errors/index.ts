/**
 * Error Handling Module
 *
 * Comprehensive error handling with recovery mechanisms, structured error logging,
 * and integration with monitoring systems.
 */

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export enum ErrorCategory {
  VALIDATION = 'validation',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  NETWORK = 'network',
  DATABASE = 'database',
  EXTERNAL_SERVICE = 'external_service',
  CONFIGURATION = 'configuration',
  BUSINESS_LOGIC = 'business_logic',
  SYSTEM = 'system',
  UNKNOWN = 'unknown'
}

export interface ErrorContext {
  errorId: string;
  timestamp: number;
  severity: ErrorSeverity;
  category: ErrorCategory;
  service: string;
  operation?: string;
  userId?: string;
  correlationId?: string;
  requestId?: string;
  additionalData?: Record<string, any>;
}

/**
 * Base error class for all Whitehorse-related errors
 */
export class WhitehorseError extends Error {
  public readonly errorCode: string;
  public readonly severity: ErrorSeverity;
  public readonly category: ErrorCategory;
  public readonly context?: ErrorContext;
  public readonly cause?: Error;
  public readonly recoverable: boolean;
  public readonly userMessage: string;
  public readonly additionalData: Record<string, any>;
  public readonly timestamp: number;

  constructor(
    message: string,
    options: {
      errorCode?: string;
      severity?: ErrorSeverity;
      category?: ErrorCategory;
      context?: ErrorContext;
      cause?: Error;
      recoverable?: boolean;
      userMessage?: string;
      additionalData?: Record<string, any>;
    } = {}
  ) {
    super(message);

    this.name = this.constructor.name;
    this.errorCode = options.errorCode || this.constructor.name;
    this.severity = options.severity || ErrorSeverity.MEDIUM;
    this.category = options.category || ErrorCategory.UNKNOWN;
    this.context = options.context;
    this.cause = options.cause;
    this.recoverable = options.recoverable || false;
    this.userMessage = options.userMessage || message;
    this.additionalData = options.additionalData || {};
    this.timestamp = Date.now();

    // Ensure proper prototype chain
    Object.setPrototypeOf(this, new.target.prototype);

    // Capture stack trace
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }

  /**
   * Convert error to dictionary for logging and monitoring
   */
  toObject(): Record<string, any> {
    return {
      errorCode: this.errorCode,
      message: this.message,
      userMessage: this.userMessage,
      severity: this.severity,
      category: this.category,
      recoverable: this.recoverable,
      timestamp: this.timestamp,
      context: this.context,
      cause: this.cause?.message,
      additionalData: this.additionalData,
      stack: this.stack
    };
  }

  /**
   * Convert to JSON
   */
  toJSON(): Record<string, any> {
    return this.toObject();
  }
}

/**
 * Data validation errors
 */
export class ValidationError extends WhitehorseError {
  public readonly field?: string;

  constructor(message: string, field?: string, additionalData?: Record<string, any>) {
    super(message, {
      severity: ErrorSeverity.LOW,
      category: ErrorCategory.VALIDATION,
      additionalData: { field, ...additionalData }
    });
    this.field = field;
  }
}

/**
 * Authentication failures
 */
export class AuthenticationError extends WhitehorseError {
  constructor(message: string = 'Authentication failed', additionalData?: Record<string, any>) {
    super(message, {
      severity: ErrorSeverity.HIGH,
      category: ErrorCategory.AUTHENTICATION,
      additionalData
    });
  }
}

/**
 * Authorization failures
 */
export class AuthorizationError extends WhitehorseError {
  constructor(message: string = 'Access denied', additionalData?: Record<string, any>) {
    super(message, {
      severity: ErrorSeverity.HIGH,
      category: ErrorCategory.AUTHORIZATION,
      additionalData
    });
  }
}

/**
 * Network-related errors
 */
export class NetworkError extends WhitehorseError {
  public readonly url?: string;
  public readonly statusCode?: number;

  constructor(
    message: string,
    options: {
      url?: string;
      statusCode?: number;
      additionalData?: Record<string, any>;
    } = {}
  ) {
    super(message, {
      severity: ErrorSeverity.MEDIUM,
      category: ErrorCategory.NETWORK,
      recoverable: true,
      additionalData: options.additionalData
    });
    this.url = options.url;
    this.statusCode = options.statusCode;
  }
}

/**
 * Database-related errors
 */
export class DatabaseError extends WhitehorseError {
  public readonly query?: string;
  public readonly constraint?: string;

  constructor(
    message: string,
    options: {
      query?: string;
      constraint?: string;
      additionalData?: Record<string, any>;
    } = {}
  ) {
    super(message, {
      severity: ErrorSeverity.HIGH,
      category: ErrorCategory.DATABASE,
      additionalData: options.additionalData
    });
    this.query = options.query;
    this.constraint = options.constraint;
  }
}

/**
 * External service integration errors
 */
export class ExternalServiceError extends WhitehorseError {
  public readonly service?: string;
  public readonly endpoint?: string;

  constructor(
    message: string,
    options: {
      service?: string;
      endpoint?: string;
      additionalData?: Record<string, any>;
    } = {}
  ) {
    super(message, {
      severity: ErrorSeverity.MEDIUM,
      category: ErrorCategory.EXTERNAL_SERVICE,
      recoverable: true,
      additionalData: options.additionalData
    });
    this.service = options.service;
    this.endpoint = options.endpoint;
  }
}

/**
 * Configuration-related errors
 */
export class ConfigurationError extends WhitehorseError {
  public readonly configKey?: string;

  constructor(
    message: string,
    configKey?: string,
    additionalData?: Record<string, any>
  ) {
    super(message, {
      severity: ErrorSeverity.HIGH,
      category: ErrorCategory.CONFIGURATION,
      additionalData: { configKey, ...additionalData }
    });
    this.configKey = configKey;
  }
}

/**
 * Business logic violation errors
 */
export class BusinessLogicError extends WhitehorseError {
  constructor(message: string, additionalData?: Record<string, any>) {
    super(message, {
      severity: ErrorSeverity.MEDIUM,
      category: ErrorCategory.BUSINESS_LOGIC,
      additionalData
    });
  }
}

/**
 * System-level errors
 */
export class SystemError extends WhitehorseError {
  constructor(message: string, additionalData?: Record<string, any>) {
    super(message, {
      severity: ErrorSeverity.CRITICAL,
      category: ErrorCategory.SYSTEM,
      additionalData
    });
  }
}

/**
 * Retry policy configuration
 */
export interface RetryPolicy {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  exponentialBase: number;
  jitter: boolean;
  retryCondition?: (error: Error) => boolean;
}

/**
 * Default retry policy
 */
export const DEFAULT_RETRY_POLICY: RetryPolicy = {
  maxAttempts: 3,
  baseDelay: 1000,
  maxDelay: 60000,
  exponentialBase: 2,
  jitter: true,
  retryCondition: (error) => {
    if (error instanceof WhitehorseError) {
      return error.recoverable && [
        NetworkError,
        ExternalServiceError,
        SystemError
      ].some(ErrorClass => error instanceof ErrorClass);
    }
    return false;
  }
};

/**
 * Calculate delay for retry attempt
 */
export function calculateRetryDelay(attempt: number, policy: RetryPolicy): number {
  let delay = policy.baseDelay * Math.pow(policy.exponentialBase, attempt - 1);
  delay = Math.min(delay, policy.maxDelay);

  if (policy.jitter) {
    delay *= (0.5 + Math.random() * 0.5); // 50-100% of calculated delay
  }

  return delay;
}

/**
 * Circuit breaker implementation
 */
export class CircuitBreaker {
  private failureCount = 0;
  private lastFailureTime?: number;
  private state: 'closed' | 'open' | 'half-open' = 'closed';

  constructor(
    private options: {
      failureThreshold: number;
      recoveryTimeout: number;
      expectedError?: new (...args: any[]) => Error;
    }
  ) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      if (this.shouldAttemptReset()) {
        this.state = 'half-open';
      } else {
        throw new SystemError('Circuit breaker is open', {
          circuitBreakerState: this.state,
          failureCount: this.failureCount
        });
      }
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private shouldAttemptReset(): boolean {
    return (
      this.lastFailureTime !== undefined &&
      Date.now() - this.lastFailureTime >= this.options.recoveryTimeout
    );
  }

  private onSuccess(): void {
    this.failureCount = 0;
    this.state = 'closed';
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.failureCount >= this.options.failureThreshold) {
      this.state = 'open';
    }
  }

  getState(): string {
    return this.state;
  }

  getFailureCount(): number {
    return this.failureCount;
  }
}

/**
 * Error handler class
 */
export class ErrorHandler {
  private errorCount = 0;
  private errorHistory: Array<Record<string, any>> = [];
  private maxHistorySize = 100;

  constructor(private serviceName: string = 'whitehorse-service') {}

  /**
   * Handle error with logging and monitoring
   */
  handleError(
    error: Error,
    context?: ErrorContext,
    notify: boolean = true
  ): void {
    this.errorCount++;

    let errorInfo: Record<string, any>;

    if (error instanceof WhitehorseError) {
      errorInfo = error.toObject();
    } else {
      errorInfo = {
        errorCode: error.constructor.name,
        message: error.message,
        severity: ErrorSeverity.MEDIUM,
        category: ErrorCategory.UNKNOWN,
        timestamp: Date.now(),
        stack: error.stack
      };
    }

    if (context) {
      errorInfo.context = context;
    }

    // Add to history
    this.errorHistory.push(errorInfo);
    if (this.errorHistory.length > this.maxHistorySize) {
      this.errorHistory.shift();
    }

    // Log error (would integrate with actual logging system)
    console.error('Error handled:', errorInfo);

    // Send notifications for high-severity errors
    if (notify && [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL].includes(errorInfo.severity)) {
      this.sendNotification(errorInfo);
    }
  }

  private sendNotification(errorInfo: Record<string, any>): void {
    // Placeholder for notification integration (Slack, PagerDuty, etc.)
    console.warn('CRITICAL ERROR NOTIFICATION:', {
      service: this.serviceName,
      error: errorInfo.errorCode,
      message: errorInfo.message,
      severity: errorInfo.severity
    });
  }

  /**
   * Get error statistics
   */
  getErrorStats(): Record<string, any> {
    const recentErrors = this.errorHistory.filter(
      error => Date.now() - error.timestamp < 3600000 // Last hour
    );

    const severityCounts: Record<string, number> = {};
    const categoryCounts: Record<string, number> = {};

    for (const error of recentErrors) {
      const severity = error.severity || 'unknown';
      const category = error.category || 'unknown';

      severityCounts[severity] = (severityCounts[severity] || 0) + 1;
      categoryCounts[category] = (categoryCounts[category] || 0) + 1;
    }

    return {
      totalErrors: this.errorCount,
      recentErrors: recentErrors.length,
      severityDistribution: severityCounts,
      categoryDistribution: categoryCounts,
      errorRate: recentErrors.length / 60 // errors per minute
    };
  }

  /**
   * Clear error history
   */
  clearHistory(): void {
    this.errorHistory = [];
    this.errorCount = 0;
  }
}

// Global error handler
let globalErrorHandler: ErrorHandler;

/**
 * Get global error handler
 */
export function getErrorHandler(): ErrorHandler {
  if (!globalErrorHandler) {
    globalErrorHandler = new ErrorHandler();
  }
  return globalErrorHandler;
}

/**
 * Setup global error handling
 */
export function setupErrorHandling(serviceName?: string): void {
  globalErrorHandler = new ErrorHandler(serviceName);

  // Handle uncaught exceptions
  process.on('uncaughtException', (error) => {
    globalErrorHandler.handleError(
      new SystemError('Uncaught exception', { originalError: error.message }),
      undefined,
      true
    );
    process.exit(1);
  });

  // Handle unhandled promise rejections
  process.on('unhandledRejection', (reason, promise) => {
    globalErrorHandler.handleError(
      new SystemError('Unhandled promise rejection', {
        reason: reason instanceof Error ? reason.message : String(reason),
        promise: promise.toString()
      }),
      undefined,
      true
    );
  });
}

export default WhitehorseError;
