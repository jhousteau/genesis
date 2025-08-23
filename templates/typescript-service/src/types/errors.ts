/**
 * Genesis Error Types and Classes
 *
 * Comprehensive error handling following Genesis patterns
 * with proper HTTP status codes and structured logging.
 */

export enum ErrorCode {
  // Authentication & Authorization
  AUTHENTICATION_FAILED = 'AUTHENTICATION_FAILED',
  AUTHORIZATION_FAILED = 'AUTHORIZATION_FAILED',
  TOKEN_INVALID = 'TOKEN_INVALID',
  TOKEN_EXPIRED = 'TOKEN_EXPIRED',

  // Validation
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  INVALID_INPUT = 'INVALID_INPUT',
  MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD',

  // Business Logic
  BUSINESS_RULE_VIOLATION = 'BUSINESS_RULE_VIOLATION',
  RESOURCE_NOT_FOUND = 'RESOURCE_NOT_FOUND',
  RESOURCE_ALREADY_EXISTS = 'RESOURCE_ALREADY_EXISTS',
  OPERATION_NOT_ALLOWED = 'OPERATION_NOT_ALLOWED',

  // External Services
  EXTERNAL_SERVICE_ERROR = 'EXTERNAL_SERVICE_ERROR',
  DATABASE_ERROR = 'DATABASE_ERROR',
  CACHE_ERROR = 'CACHE_ERROR',
  QUEUE_ERROR = 'QUEUE_ERROR',

  // System
  INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  REQUEST_TIMEOUT = 'REQUEST_TIMEOUT',

  // Configuration
  CONFIGURATION_ERROR = 'CONFIGURATION_ERROR',
  ENVIRONMENT_ERROR = 'ENVIRONMENT_ERROR'
}

export interface ErrorDetails {
  field?: string;
  value?: any;
  constraint?: string;
  resource?: string;
  operation?: string;
}

export interface ErrorContext {
  requestId?: string;
  userId?: string;
  correlationId?: string;
  timestamp?: Date;
  metadata?: Record<string, any>;
}

/**
 * Base Genesis Error Class
 */
export class GenesisError extends Error {
  public readonly code: ErrorCode;
  public readonly statusCode: number;
  public readonly details?: ErrorDetails;
  public readonly context?: ErrorContext;
  public readonly isOperational: boolean;

  constructor(
    message: string,
    statusCode: number = 500,
    code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
    details?: ErrorDetails,
    context?: ErrorContext,
    isOperational: boolean = true
  ) {
    super(message);

    this.name = this.constructor.name;
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
    this.context = {
      ...context,
      timestamp: context?.timestamp || new Date()
    };
    this.isOperational = isOperational;

    // Capture stack trace
    Error.captureStackTrace(this, this.constructor);
  }

  /**
   * Convert error to JSON for logging and API responses
   */
  public toJSON() {
    return {
      name: this.name,
      message: this.message,
      code: this.code,
      statusCode: this.statusCode,
      details: this.details,
      context: this.context,
      isOperational: this.isOperational,
      stack: this.stack
    };
  }

  /**
   * Get safe error response for API clients (excluding sensitive data)
   */
  public toApiResponse() {
    return {
      error: {
        message: this.message,
        code: this.code,
        details: this.details,
        timestamp: this.context?.timestamp?.toISOString()
      }
    };
  }
}

/**
 * Authentication Error
 */
export class AuthenticationError extends GenesisError {
  constructor(
    message: string = 'Authentication failed',
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(message, 401, ErrorCode.AUTHENTICATION_FAILED, details, context);
  }
}

/**
 * Authorization Error
 */
export class AuthorizationError extends GenesisError {
  constructor(
    message: string = 'Authorization failed',
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(message, 403, ErrorCode.AUTHORIZATION_FAILED, details, context);
  }
}

/**
 * Validation Error
 */
export class ValidationError extends GenesisError {
  constructor(
    message: string = 'Validation failed',
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(message, 400, ErrorCode.VALIDATION_ERROR, details, context);
  }
}

/**
 * Not Found Error
 */
export class NotFoundError extends GenesisError {
  constructor(
    resource: string = 'Resource',
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(`${resource} not found`, 404, ErrorCode.RESOURCE_NOT_FOUND, details, context);
  }
}

/**
 * Conflict Error
 */
export class ConflictError extends GenesisError {
  constructor(
    message: string = 'Resource already exists',
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(message, 409, ErrorCode.RESOURCE_ALREADY_EXISTS, details, context);
  }
}

/**
 * Business Logic Error
 */
export class BusinessError extends GenesisError {
  constructor(
    message: string,
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(message, 422, ErrorCode.BUSINESS_RULE_VIOLATION, details, context);
  }
}

/**
 * External Service Error
 */
export class ExternalServiceError extends GenesisError {
  public readonly serviceName: string;

  constructor(
    serviceName: string,
    message: string = 'External service error',
    statusCode: number = 502,
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(message, statusCode, ErrorCode.EXTERNAL_SERVICE_ERROR, details, context);
    this.serviceName = serviceName;
  }

  public toJSON() {
    return {
      ...super.toJSON(),
      serviceName: this.serviceName
    };
  }
}

/**
 * Database Error
 */
export class DatabaseError extends GenesisError {
  public readonly operation?: string;
  public readonly table?: string;

  constructor(
    message: string = 'Database operation failed',
    operation?: string,
    table?: string,
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(message, 500, ErrorCode.DATABASE_ERROR, details, context);
    this.operation = operation;
    this.table = table;
  }

  public toJSON() {
    return {
      ...super.toJSON(),
      operation: this.operation,
      table: this.table
    };
  }
}

/**
 * Rate Limit Error
 */
export class RateLimitError extends GenesisError {
  public readonly retryAfter?: number;

  constructor(
    message: string = 'Rate limit exceeded',
    retryAfter?: number,
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(message, 429, ErrorCode.RATE_LIMIT_EXCEEDED, details, context);
    this.retryAfter = retryAfter;
  }

  public toJSON() {
    return {
      ...super.toJSON(),
      retryAfter: this.retryAfter
    };
  }
}

/**
 * Configuration Error
 */
export class ConfigurationError extends GenesisError {
  constructor(
    message: string = 'Configuration error',
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(message, 500, ErrorCode.CONFIGURATION_ERROR, details, context, false);
  }
}

/**
 * Timeout Error
 */
export class TimeoutError extends GenesisError {
  public readonly timeoutMs: number;

  constructor(
    operation: string,
    timeoutMs: number,
    details?: ErrorDetails,
    context?: ErrorContext
  ) {
    super(`Operation '${operation}' timed out after ${timeoutMs}ms`,
          408,
          ErrorCode.REQUEST_TIMEOUT,
          details,
          context);
    this.timeoutMs = timeoutMs;
  }

  public toJSON() {
    return {
      ...super.toJSON(),
      timeoutMs: this.timeoutMs
    };
  }
}

/**
 * Error Factory for creating errors from different sources
 */
export class ErrorFactory {
  /**
   * Create error from HTTP status code
   */
  static fromHttpStatus(
    statusCode: number,
    message?: string,
    details?: ErrorDetails,
    context?: ErrorContext
  ): GenesisError {
    switch (statusCode) {
      case 400:
        return new ValidationError(message || 'Bad request', details, context);
      case 401:
        return new AuthenticationError(message || 'Unauthorized', details, context);
      case 403:
        return new AuthorizationError(message || 'Forbidden', details, context);
      case 404:
        return new NotFoundError(message || 'Not found', details, context);
      case 409:
        return new ConflictError(message || 'Conflict', details, context);
      case 422:
        return new BusinessError(message || 'Unprocessable entity', details, context);
      case 429:
        return new RateLimitError(message || 'Too many requests', undefined, details, context);
      case 500:
        return new GenesisError(message || 'Internal server error', 500, ErrorCode.INTERNAL_SERVER_ERROR, details, context);
      case 502:
        return new ExternalServiceError('unknown', message || 'Bad gateway', 502, details, context);
      case 503:
        return new GenesisError(message || 'Service unavailable', 503, ErrorCode.SERVICE_UNAVAILABLE, details, context);
      case 504:
        return new TimeoutError('request', 30000, details, context);
      default:
        return new GenesisError(message || 'Unknown error', statusCode, ErrorCode.INTERNAL_SERVER_ERROR, details, context);
    }
  }

  /**
   * Create error from exception
   */
  static fromException(
    error: any,
    context?: ErrorContext
  ): GenesisError {
    if (error instanceof GenesisError) {
      return error;
    }

    if (error.name === 'ValidationError') {
      return new ValidationError(error.message, undefined, context);
    }

    if (error.name === 'MongoError' || error.name === 'SequelizeError') {
      return new DatabaseError(error.message, undefined, undefined, undefined, context);
    }

    if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
      return new ExternalServiceError('database', error.message, 503, undefined, context);
    }

    if (error.code === 'ETIMEDOUT') {
      return new TimeoutError('operation', 30000, undefined, context);
    }

    // Default to internal server error
    return new GenesisError(
      error.message || 'Unknown error',
      500,
      ErrorCode.INTERNAL_SERVER_ERROR,
      undefined,
      context,
      false // Unknown errors are not operational
    );
  }
}

/**
 * Type guards
 */
export function isGenesisError(error: any): error is GenesisError {
  return error instanceof GenesisError;
}

export function isOperationalError(error: any): boolean {
  return isGenesisError(error) && error.isOperational;
}
