/**
 * Logging Module
 * 
 * Provides structured logging with GCP Cloud Logging integration,
 * correlation IDs, and consistent formatting across all projects.
 */

import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';
import { AsyncLocalStorage } from 'async_hooks';

export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
  FATAL = 'fatal'
}

export interface LogContext {
  correlationId?: string;
  traceId?: string;
  spanId?: string;
  userId?: string;
  requestId?: string;
  operationId?: string;
  [key: string]: any;
}

export interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  service: string;
  context?: LogContext;
  metadata?: Record<string, any>;
  error?: {
    name: string;
    message: string;
    stack?: string;
  };
}

// AsyncLocalStorage for correlation context
const correlationStorage = new AsyncLocalStorage<LogContext>();

/**
 * Custom Winston formatter for structured logging
 */
const structuredFormatter = winston.format.combine(
  winston.format.timestamp(),
  winston.format.errors({ stack: true }),
  winston.format.json(),
  winston.format.printf((info) => {
    const context = correlationStorage.getStore() || {};
    
    const logEntry: LogEntry = {
      level: info.level as LogLevel,
      message: info.message,
      timestamp: info.timestamp,
      service: info.service || 'whitehorse-service',
      context: { ...context, ...info.context },
      metadata: info.metadata
    };

    if (info.error || info.stack) {
      logEntry.error = {
        name: info.error?.name || 'Error',
        message: info.error?.message || info.message,
        stack: info.stack || info.error?.stack
      };
    }

    return JSON.stringify(logEntry);
  })
);

/**
 * Logger class with correlation ID support and structured logging
 */
export class Logger {
  private winston: winston.Logger;
  private serviceName: string;

  constructor(serviceName: string = 'whitehorse-service', options?: winston.LoggerOptions) {
    this.serviceName = serviceName;
    
    const defaultOptions: winston.LoggerOptions = {
      level: process.env.LOG_LEVEL || 'info',
      format: structuredFormatter,
      defaultMeta: { service: serviceName },
      transports: [
        new winston.transports.Console({
          format: winston.format.combine(
            winston.format.colorize(),
            winston.format.simple()
          )
        })
      ],
      ...options
    };

    this.winston = winston.createLogger(defaultOptions);
  }

  /**
   * Add GCP Cloud Logging transport
   */
  addGcpLogging(projectId?: string): void {
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { LoggingWinston } = require('@google-cloud/logging-winston');
      
      const gcpTransport = new LoggingWinston({
        projectId,
        keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS,
        logName: this.serviceName,
        resource: {
          type: 'generic_node',
          labels: {
            location: process.env.GCP_REGION || 'us-central1',
            namespace: this.serviceName,
            node_id: process.env.HOSTNAME || 'default'
          }
        }
      });

      this.winston.add(gcpTransport);
      this.info('GCP Cloud Logging enabled');
    } catch (error) {
      this.warn('Failed to initialize GCP Cloud Logging', { error: error.message });
    }
  }

  /**
   * Add file transport
   */
  addFileLogging(filename: string, options?: winston.transports.FileTransportOptions): void {
    const fileTransport = new winston.transports.File({
      filename,
      format: structuredFormatter,
      ...options
    });

    this.winston.add(fileTransport);
    this.info('File logging enabled', { filename });
  }

  debug(message: string, metadata?: Record<string, any>): void {
    this.winston.debug(message, { metadata });
  }

  info(message: string, metadata?: Record<string, any>): void {
    this.winston.info(message, { metadata });
  }

  warn(message: string, metadata?: Record<string, any>): void {
    this.winston.warn(message, { metadata });
  }

  error(message: string, error?: Error, metadata?: Record<string, any>): void {
    this.winston.error(message, { error, metadata });
  }

  fatal(message: string, error?: Error, metadata?: Record<string, any>): void {
    this.winston.error(message, { error, metadata, fatal: true });
  }

  /**
   * Create a child logger with additional context
   */
  child(context: LogContext): Logger {
    const childLogger = new Logger(this.serviceName, {
      level: this.winston.level,
      format: this.winston.format,
      transports: this.winston.transports,
      defaultMeta: { ...this.winston.defaultMeta, context }
    });

    return childLogger;
  }

  /**
   * Execute function with correlation ID context
   */
  withCorrelationId<T>(correlationId: string, fn: () => T): T;
  withCorrelationId<T>(correlationId: string, fn: () => Promise<T>): Promise<T>;
  withCorrelationId<T>(correlationId: string, fn: () => T | Promise<T>): T | Promise<T> {
    const context: LogContext = { correlationId };
    return correlationStorage.run(context, fn);
  }

  /**
   * Execute function with full context
   */
  withContext<T>(context: LogContext, fn: () => T): T;
  withContext<T>(context: LogContext, fn: () => Promise<T>): Promise<T>;
  withContext<T>(context: LogContext, fn: () => T | Promise<T>): T | Promise<T> {
    return correlationStorage.run(context, fn);
  }

  /**
   * Get current correlation ID
   */
  getCorrelationId(): string | undefined {
    return correlationStorage.getStore()?.correlationId;
  }

  /**
   * Get current context
   */
  getContext(): LogContext | undefined {
    return correlationStorage.getStore();
  }

  /**
   * Performance timing decorator
   */
  timing<T extends (...args: any[]) => any>(
    operation: string,
    fn: T
  ): T {
    return ((...args: any[]) => {
      const start = Date.now();
      const operationId = uuidv4();
      
      this.info(`Starting ${operation}`, { operationId, operation });
      
      try {
        const result = fn(...args);
        
        if (result instanceof Promise) {
          return result
            .then((value) => {
              const duration = Date.now() - start;
              this.info(`Completed ${operation}`, {
                operationId,
                operation,
                duration,
                success: true
              });
              return value;
            })
            .catch((error) => {
              const duration = Date.now() - start;
              this.error(`Failed ${operation}`, error, {
                operationId,
                operation,
                duration,
                success: false
              });
              throw error;
            });
        } else {
          const duration = Date.now() - start;
          this.info(`Completed ${operation}`, {
            operationId,
            operation,
            duration,
            success: true
          });
          return result;
        }
      } catch (error) {
        const duration = Date.now() - start;
        this.error(`Failed ${operation}`, error, {
          operationId,
          operation,
          duration,
          success: false
        });
        throw error;
      }
    }) as T;
  }

  /**
   * Set log level
   */
  setLevel(level: LogLevel): void {
    this.winston.level = level;
  }

  /**
   * Get current log level
   */
  getLevel(): string {
    return this.winston.level;
  }

  /**
   * Flush all transports
   */
  async flush(): Promise<void> {
    return new Promise((resolve) => {
      this.winston.end(() => resolve());
    });
  }
}

// Global logger instance
let globalLogger: Logger;

/**
 * Create or get a logger instance
 */
export function createLogger(serviceName?: string, options?: winston.LoggerOptions): Logger {
  if (!globalLogger || serviceName) {
    globalLogger = new Logger(serviceName || 'whitehorse-service', options);
  }
  return globalLogger;
}

/**
 * Get the global logger instance
 */
export function getLogger(): Logger {
  if (!globalLogger) {
    globalLogger = createLogger();
  }
  return globalLogger;
}

/**
 * Setup logging with common configuration
 */
export function setupLogging(options: {
  serviceName?: string;
  level?: LogLevel;
  enableGcp?: boolean;
  gcpProjectId?: string;
  enableFile?: boolean;
  filename?: string;
  enableConsole?: boolean;
}): Logger {
  const logger = createLogger(options.serviceName, {
    level: options.level || LogLevel.INFO,
    transports: []
  });

  // Add console transport
  if (options.enableConsole !== false) {
    logger['winston'].add(new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.timestamp(),
        winston.format.printf(({ timestamp, level, message, service, metadata }) => {
          const meta = metadata ? ` ${JSON.stringify(metadata)}` : '';
          return `${timestamp} [${service}] ${level}: ${message}${meta}`;
        })
      )
    }));
  }

  // Add file transport
  if (options.enableFile && options.filename) {
    logger.addFileLogging(options.filename);
  }

  // Add GCP transport
  if (options.enableGcp) {
    logger.addGcpLogging(options.gcpProjectId);
  }

  return logger;
}

/**
 * Middleware function for Express.js to add correlation ID
 */
export function correlationMiddleware() {
  return (req: any, res: any, next: any) => {
    const correlationId = req.headers['x-correlation-id'] || uuidv4();
    const context: LogContext = {
      correlationId,
      requestId: req.id || uuidv4(),
      userId: req.user?.id
    };

    res.setHeader('x-correlation-id', correlationId);
    
    correlationStorage.run(context, () => {
      next();
    });
  };
}

/**
 * Performance timing function
 */
export function time<T>(
  operation: string,
  fn: () => T,
  logger?: Logger
): T {
  const log = logger || getLogger();
  return log.timing(operation, fn)();
}

/**
 * Async performance timing function
 */
export async function timeAsync<T>(
  operation: string,
  fn: () => Promise<T>,
  logger?: Logger
): Promise<T> {
  const log = logger || getLogger();
  return log.timing(operation, fn)();
}

export default Logger;