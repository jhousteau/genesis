/**
 * Genesis Retry Utilities
 *
 * Retry mechanisms with exponential backoff, circuit breaker patterns,
 * and comprehensive error handling following Genesis patterns.
 */

import { Logger } from './logger';

export interface RetryOptions {
  retries: number;
  delay: number;
  maxDelay?: number;
  backoff?: 'linear' | 'exponential';
  jitter?: boolean;
  condition?: (error: Error) => boolean;
}

const logger = Logger.getInstance('retry');

/**
 * Retry decorator for methods
 */
export function retry(options: RetryOptions) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      return retryOperation(() => originalMethod.apply(this, args), options);
    };

    return descriptor;
  };
}

/**
 * Retry an async operation
 */
export async function retryOperation<T>(
  operation: () => Promise<T>,
  options: RetryOptions
): Promise<T> {
  const { retries, delay, maxDelay = 30000, backoff = 'exponential', jitter = true, condition } = options;

  let lastError: Error;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const result = await operation();

      if (attempt > 0) {
        logger.info('Operation succeeded after retry', {
          attempt,
          totalAttempts: attempt + 1
        });
      }

      return result;

    } catch (error) {
      lastError = error;

      // Check if we should retry this error
      if (condition && !condition(error)) {
        logger.debug('Retry condition not met', {
          error: error.message,
          attempt
        });
        throw error;
      }

      // If this was the last attempt, throw the error
      if (attempt === retries) {
        logger.error('Operation failed after all retries', {
          error: error.message,
          totalAttempts: attempt + 1,
          maxRetries: retries
        });
        throw error;
      }

      // Calculate delay for next attempt
      const nextDelay = calculateDelay(delay, attempt, backoff, maxDelay, jitter);

      logger.warn('Operation failed, retrying', {
        error: error.message,
        attempt: attempt + 1,
        nextDelay,
        retriesLeft: retries - attempt
      });

      // Wait before next attempt
      await sleep(nextDelay);
    }
  }

  throw lastError!;
}

/**
 * Calculate delay with backoff and jitter
 */
function calculateDelay(
  baseDelay: number,
  attempt: number,
  backoff: 'linear' | 'exponential',
  maxDelay: number,
  jitter: boolean
): number {
  let delay: number;

  if (backoff === 'exponential') {
    delay = baseDelay * Math.pow(2, attempt);
  } else {
    delay = baseDelay * (attempt + 1);
  }

  // Apply max delay cap
  delay = Math.min(delay, maxDelay);

  // Apply jitter to avoid thundering herd
  if (jitter) {
    delay = delay * (0.5 + Math.random() * 0.5);
  }

  return Math.floor(delay);
}

/**
 * Sleep utility
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Circuit Breaker Pattern
 */
export class CircuitBreaker {
  private failureCount = 0;
  private lastFailureTime = 0;
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';
  private logger: Logger;

  constructor(
    private failureThreshold: number = 5,
    private recoveryTimeout: number = 60000,
    private monitoringPeriod: number = 60000
  ) {
    this.logger = Logger.getInstance('circuit-breaker');
  }

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailureTime >= this.recoveryTimeout) {
        this.state = 'HALF_OPEN';
        this.logger.info('Circuit breaker half-open, attempting recovery');
      } else {
        const error = new Error('Circuit breaker is OPEN');
        this.logger.warn('Circuit breaker blocked operation', {
          state: this.state,
          failureCount: this.failureCount
        });
        throw error;
      }
    }

    try {
      const result = await operation();

      if (this.state === 'HALF_OPEN') {
        this.reset();
        this.logger.info('Circuit breaker recovered, state reset to CLOSED');
      }

      return result;

    } catch (error) {
      this.recordFailure();
      throw error;
    }
  }

  private recordFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    this.logger.warn('Circuit breaker recorded failure', {
      failureCount: this.failureCount,
      threshold: this.failureThreshold
    });

    if (this.failureCount >= this.failureThreshold) {
      this.state = 'OPEN';
      this.logger.error('Circuit breaker opened due to failures', {
        failureCount: this.failureCount,
        threshold: this.failureThreshold
      });
    }
  }

  private reset(): void {
    this.failureCount = 0;
    this.lastFailureTime = 0;
    this.state = 'CLOSED';
  }

  public getState(): string {
    return this.state;
  }

  public getFailureCount(): number {
    return this.failureCount;
  }
}

/**
 * Timeout wrapper
 */
export async function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  timeoutMessage?: string
): Promise<T> {
  const timeout = new Promise<never>((_, reject) => {
    setTimeout(() => {
      reject(new Error(timeoutMessage || `Operation timed out after ${timeoutMs}ms`));
    }, timeoutMs);
  });

  return Promise.race([promise, timeout]);
}

/**
 * Retry conditions
 */
export const retryConditions = {
  // Retry on network errors
  networkErrors: (error: Error): boolean => {
    const networkErrorCodes = ['ECONNRESET', 'ECONNREFUSED', 'ETIMEDOUT', 'ENOTFOUND'];
    return networkErrorCodes.some(code => error.message.includes(code));
  },

  // Retry on HTTP 5xx errors
  serverErrors: (error: any): boolean => {
    return error.status >= 500 && error.status < 600;
  },

  // Retry on transient errors
  transientErrors: (error: Error): boolean => {
    const transientMessages = [
      'ECONNRESET',
      'ETIMEDOUT',
      'Service Unavailable',
      'Internal Server Error',
      'Bad Gateway',
      'Gateway Timeout'
    ];
    return transientMessages.some(msg => error.message.includes(msg));
  },

  // Never retry on auth errors
  notAuthErrors: (error: any): boolean => {
    return !(error.status === 401 || error.status === 403);
  },

  // Combine multiple conditions
  and: (...conditions: Array<(error: Error) => boolean>) => {
    return (error: Error): boolean => {
      return conditions.every(condition => condition(error));
    };
  },

  or: (...conditions: Array<(error: Error) => boolean>) => {
    return (error: Error): boolean => {
      return conditions.some(condition => condition(error));
    };
  }
};

/**
 * Common retry configurations
 */
export const retryConfigs = {
  // Quick retry for transient issues
  quick: {
    retries: 3,
    delay: 100,
    backoff: 'exponential' as const,
    condition: retryConditions.transientErrors
  },

  // Standard retry for most operations
  standard: {
    retries: 5,
    delay: 1000,
    backoff: 'exponential' as const,
    maxDelay: 10000,
    condition: retryConditions.and(
      retryConditions.transientErrors,
      retryConditions.notAuthErrors
    )
  },

  // Slow retry for expensive operations
  slow: {
    retries: 3,
    delay: 5000,
    backoff: 'exponential' as const,
    maxDelay: 30000,
    condition: retryConditions.networkErrors
  },

  // Network-specific retry
  network: {
    retries: 7,
    delay: 500,
    backoff: 'exponential' as const,
    maxDelay: 15000,
    jitter: true,
    condition: retryConditions.or(
      retryConditions.networkErrors,
      retryConditions.serverErrors
    )
  }
};
