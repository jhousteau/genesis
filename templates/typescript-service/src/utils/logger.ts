/**
 * Genesis Logger Implementation
 *
 * Structured logging with GCP Cloud Logging integration,
 * following Genesis observability patterns.
 */

import winston, { Logger as WinstonLogger } from 'winston';
import { LoggingWinston } from '@google-cloud/logging-winston';
import { Config } from '../config';

export enum LogLevel {
  ERROR = 'error',
  WARN = 'warn',
  INFO = 'info',
  DEBUG = 'debug'
}

export interface LogMetadata {
  requestId?: string;
  userId?: string;
  correlationId?: string;
  operation?: string;
  duration?: number;
  statusCode?: number;
  error?: any;
  [key: string]: any;
}

export interface LogEntry {
  level: LogLevel;
  message: string;
  metadata?: LogMetadata;
  timestamp: Date;
  service: string;
  version: string;
  environment: string;
}

/**
 * Genesis Logger Class
 *
 * Provides structured logging with automatic GCP integration
 */
export class Logger {
  private static instances: Map<string, Logger> = new Map();
  private winston: WinstonLogger;
  private context: string;
  private config: Config;

  private constructor(context: string) {
    this.context = context;
    this.config = Config.getInstance();
    this.winston = this.createWinstonLogger();
  }

  /**
   * Get logger instance for a specific context
   */
  public static getInstance(context: string = 'app'): Logger {
    if (!Logger.instances.has(context)) {
      Logger.instances.set(context, new Logger(context));
    }
    return Logger.instances.get(context)!;
  }

  /**
   * Create Winston logger with appropriate transports
   */
  private createWinstonLogger(): WinstonLogger {
    const transports: winston.transport[] = [];

    // Console transport for local development
    if (this.config.environment === 'development') {
      transports.push(
        new winston.transports.Console({
          format: winston.format.combine(
            winston.format.colorize(),
            winston.format.timestamp(),
            winston.format.printf(({ level, message, timestamp, ...meta }) => {
              const metaStr = Object.keys(meta).length ? JSON.stringify(meta, null, 2) : '';
              return `${timestamp} [${this.context}] ${level}: ${message} ${metaStr}`;
            })
          )
        })
      );
    } else {
      // Production console transport (structured JSON)
      transports.push(
        new winston.transports.Console({
          format: winston.format.combine(
            winston.format.timestamp(),
            winston.format.json()
          )
        })
      );

      // GCP Cloud Logging transport for production
      if (this.config.gcp.projectId) {
        try {
          const cloudLogging = new LoggingWinston({
            projectId: this.config.gcp.projectId,
            keyFilename: this.config.gcp.keyFilename,
            logName: `${this.config.serviceName}-${this.config.environment}`,
            resource: {
              type: 'cloud_run_revision',
              labels: {
                service_name: this.config.serviceName,
                revision_name: process.env.K_REVISION || 'local',
                location: this.config.gcp.region
              }
            },
            labels: {
              service: this.config.serviceName,
              version: this.config.version,
              environment: this.config.environment
            }
          });

          transports.push(cloudLogging);
        } catch (error) {
          console.warn('Failed to initialize GCP logging transport:', error.message);
        }
      }
    }

    return winston.createLogger({
      level: this.config.logLevel,
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.metadata({
          fillExcept: ['message', 'level', 'timestamp']
        })
      ),
      defaultMeta: {
        service: this.config.serviceName,
        version: this.config.version,
        environment: this.config.environment,
        context: this.context
      },
      transports,
      // Handle uncaught exceptions and rejections
      exceptionHandlers: transports,
      rejectionHandlers: transports
    });
  }

  /**
   * Log error message
   */
  public error(message: string, metadata?: LogMetadata): void {
    this.winston.error(message, this.enrichMetadata(metadata));
  }

  /**
   * Log warning message
   */
  public warn(message: string, metadata?: LogMetadata): void {
    this.winston.warn(message, this.enrichMetadata(metadata));
  }

  /**
   * Log info message
   */
  public info(message: string, metadata?: LogMetadata): void {
    this.winston.info(message, this.enrichMetadata(metadata));
  }

  /**
   * Log debug message
   */
  public debug(message: string, metadata?: LogMetadata): void {
    this.winston.debug(message, this.enrichMetadata(metadata));
  }

  /**
   * Log HTTP request
   */
  public logRequest(
    method: string,
    url: string,
    statusCode: number,
    duration: number,
    metadata?: LogMetadata
  ): void {
    const level = statusCode >= 500 ? LogLevel.ERROR :
                 statusCode >= 400 ? LogLevel.WARN : LogLevel.INFO;

    const message = `${method} ${url} ${statusCode} - ${duration}ms`;

    this[level](message, {
      ...metadata,
      httpMethod: method,
      httpUrl: url,
      httpStatusCode: statusCode,
      httpDuration: duration,
      type: 'http_request'
    });
  }

  /**
   * Log database operation
   */
  public logDatabase(
    operation: string,
    table: string,
    duration: number,
    metadata?: LogMetadata
  ): void {
    this.info(`Database ${operation} on ${table} - ${duration}ms`, {
      ...metadata,
      dbOperation: operation,
      dbTable: table,
      dbDuration: duration,
      type: 'database_operation'
    });
  }

  /**
   * Log external service call
   */
  public logExternalService(
    service: string,
    operation: string,
    statusCode: number,
    duration: number,
    metadata?: LogMetadata
  ): void {
    const level = statusCode >= 500 ? LogLevel.ERROR :
                 statusCode >= 400 ? LogLevel.WARN : LogLevel.INFO;

    const message = `External service ${service}.${operation} ${statusCode} - ${duration}ms`;

    this[level](message, {
      ...metadata,
      externalService: service,
      externalOperation: operation,
      externalStatusCode: statusCode,
      externalDuration: duration,
      type: 'external_service_call'
    });
  }

  /**
   * Log business event
   */
  public logBusinessEvent(
    event: string,
    entityType: string,
    entityId: string,
    metadata?: LogMetadata
  ): void {
    this.info(`Business event: ${event}`, {
      ...metadata,
      businessEvent: event,
      entityType,
      entityId,
      type: 'business_event'
    });
  }

  /**
   * Log security event
   */
  public logSecurityEvent(
    event: string,
    severity: 'low' | 'medium' | 'high' | 'critical',
    metadata?: LogMetadata
  ): void {
    const level = severity === 'critical' || severity === 'high' ? LogLevel.ERROR : LogLevel.WARN;

    this[level](`Security event: ${event}`, {
      ...metadata,
      securityEvent: event,
      securitySeverity: severity,
      type: 'security_event'
    });
  }

  /**
   * Log performance metric
   */
  public logPerformance(
    operation: string,
    duration: number,
    metadata?: LogMetadata
  ): void {
    const level = duration > 5000 ? LogLevel.WARN : LogLevel.DEBUG;

    this[level](`Performance: ${operation} - ${duration}ms`, {
      ...metadata,
      performanceOperation: operation,
      performanceDuration: duration,
      type: 'performance_metric'
    });
  }

  /**
   * Create child logger with additional context
   */
  public child(additionalContext: Record<string, any>): Logger {
    const childLogger = new Logger(this.context);
    childLogger.winston = this.winston.child(additionalContext);
    return childLogger;
  }

  /**
   * Set correlation ID for request tracking
   */
  public withCorrelation(correlationId: string): Logger {
    return this.child({ correlationId });
  }

  /**
   * Set user context
   */
  public withUser(userId: string, username?: string): Logger {
    return this.child({ userId, username });
  }

  /**
   * Enrich metadata with common fields
   */
  private enrichMetadata(metadata?: LogMetadata): LogMetadata {
    return {
      ...metadata,
      timestamp: new Date(),
      context: this.context,
      pid: process.pid,
      hostname: require('os').hostname()
    };
  }

  /**
   * Get underlying Winston instance
   */
  public getWinstonLogger(): WinstonLogger {
    return this.winston;
  }

  /**
   * Close logger and clean up resources
   */
  public close(): Promise<void> {
    return new Promise((resolve) => {
      this.winston.end(() => resolve());
    });
  }
}

/**
 * Request Logger Middleware Helper
 */
export function createRequestLogger(context: string = 'http') {
  const logger = Logger.getInstance(context);

  return {
    logRequest: (
      requestId: string,
      method: string,
      url: string,
      userAgent?: string,
      ip?: string
    ) => {
      logger.info(`${method} ${url} - Started`, {
        requestId,
        httpMethod: method,
        httpUrl: url,
        userAgent,
        clientIp: ip,
        type: 'http_request_start'
      });
    },

    logResponse: (
      requestId: string,
      method: string,
      url: string,
      statusCode: number,
      duration: number,
      userId?: string
    ) => {
      logger.logRequest(method, url, statusCode, duration, {
        requestId,
        userId,
        type: 'http_request_complete'
      });
    },

    logError: (
      requestId: string,
      error: any,
      method?: string,
      url?: string
    ) => {
      logger.error('Request error', {
        requestId,
        error: error.message,
        stack: error.stack,
        httpMethod: method,
        httpUrl: url,
        type: 'http_request_error'
      });
    }
  };
}

// Export singleton instance for common usage
export const logger = Logger.getInstance('app');
