/**
 * Lightweight structured logging utility
 */

import { getContext, getLoggerContext as getContextLoggerData } from './context';

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
  FATAL = 'FATAL',
}

export interface LogConfig {
  level?: LogLevel;
  formatJson?: boolean;
  includeTimestamp?: boolean;
  includeCaller?: boolean;
  extraFields?: Record<string, any>;
}

export interface LogEntry {
  message: string;
  level: LogLevel;
  timestamp?: string;
  caller?: string;
  [key: string]: any;
}

export interface Logger {
  debug(message: string, extra?: Record<string, any>): void;
  info(message: string, extra?: Record<string, any>): void;
  warn(message: string, extra?: Record<string, any>): void;
  error(message: string, extra?: Record<string, any>): void;
  fatal(message: string, extra?: Record<string, any>): void;
}

class GenesisLogger implements Logger {
  constructor(
    private name: string,
    private config: Required<LogConfig>
  ) {}

  private shouldLog(level: LogLevel): boolean {
    const levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARN, LogLevel.ERROR, LogLevel.FATAL];
    const currentLevelIndex = levels.indexOf(this.config.level);
    const messageLevelIndex = levels.indexOf(level);
    return messageLevelIndex >= currentLevelIndex;
  }

  private formatMessage(level: LogLevel, message: string, extra?: Record<string, any>): string {
    const logData: LogEntry = {
      message,
      level,
    };

    if (this.config.includeTimestamp) {
      logData.timestamp = new Date().toISOString();
    }

    if (this.config.includeCaller) {
      // In TypeScript/Node.js, we can capture the stack trace
      const stack = new Error().stack;
      if (stack) {
        const callerLine = stack.split('\n')[3]; // Adjust index as needed
        if (callerLine) {
          const match = callerLine.match(/at .* \\((.*):(\\d+):(\\d+)\\)/);
          if (match) {
            const [, filename, line] = match;
            logData.caller = `${filename.split('/').pop()}:${line}`;
          }
        }
      }
    }

    // Include context information automatically
    const context = getContext();
    if (context) {
      const loggerContext = getContextLoggerData(context);
      Object.assign(logData, loggerContext);
    }

    // Add extra data
    if (extra) {
      Object.assign(logData, extra);
    }

    // Add configured extra fields
    Object.assign(logData, this.config.extraFields);

    if (this.config.formatJson) {
      return JSON.stringify(logData);
    } else {
      const timestamp = logData.timestamp || new Date().toISOString();
      return `${timestamp} - ${this.name} - ${level} - ${message}`;
    }
  }

  private log(level: LogLevel, message: string, extra?: Record<string, any>): void {
    if (!this.shouldLog(level)) {
      return;
    }

    const formattedMessage = this.formatMessage(level, message, extra);
    
    // Route to appropriate console method
    switch (level) {
      case LogLevel.DEBUG:
        console.debug(formattedMessage);
        break;
      case LogLevel.INFO:
        console.info(formattedMessage);
        break;
      case LogLevel.WARN:
        console.warn(formattedMessage);
        break;
      case LogLevel.ERROR:
      case LogLevel.FATAL:
        console.error(formattedMessage);
        break;
      default:
        console.log(formattedMessage);
    }
  }

  debug(message: string, extra?: Record<string, any>): void {
    this.log(LogLevel.DEBUG, message, extra);
  }

  info(message: string, extra?: Record<string, any>): void {
    this.log(LogLevel.INFO, message, extra);
  }

  warn(message: string, extra?: Record<string, any>): void {
    this.log(LogLevel.WARN, message, extra);
  }

  error(message: string, extra?: Record<string, any>): void {
    this.log(LogLevel.ERROR, message, extra);
  }

  fatal(message: string, extra?: Record<string, any>): void {
    this.log(LogLevel.FATAL, message, extra);
  }
}

/**
 * Get configured logger instance
 */
export function getLogger(
  name: string,
  config: LogConfig = {}
): Logger {
  const defaultConfig: Required<LogConfig> = {
    level: LogLevel.INFO,
    formatJson: true,
    includeTimestamp: true,
    includeCaller: false,
    extraFields: {},
    ...config,
  };

  return new GenesisLogger(name, defaultConfig);
}

/**
 * Create a child logger with additional context
 */
export function createChildLogger(
  parent: Logger,
  name: string,
  extraFields: Record<string, any> = {}
): Logger {
  return getLogger(name, { extraFields });
}

/**
 * Predefined logger configurations
 */
export const LoggerPresets = {
  development: (): LogConfig => ({
    level: LogLevel.DEBUG,
    formatJson: false,
    includeTimestamp: true,
    includeCaller: true,
  }),

  production: (): LogConfig => ({
    level: LogLevel.INFO,
    formatJson: true,
    includeTimestamp: true,
    includeCaller: false,
  }),

  testing: (): LogConfig => ({
    level: LogLevel.WARN,
    formatJson: false,
    includeTimestamp: false,
    includeCaller: false,
  }),
} as const;