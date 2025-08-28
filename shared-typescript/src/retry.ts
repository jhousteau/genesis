/**
 * Retry and Circuit Breaker - Resilience patterns for distributed systems.
 *
 * This module provides:
 * 1. **Retry decorator**: Exponential backoff with jitter for transient failures
 * 2. **Circuit Breaker**: Fail-fast pattern to prevent cascading failures
 * 3. **Integration**: Combined retry + circuit breaker for maximum resilience
 */

import { GenesisError, ErrorCategory } from './errors';

// Type definitions
export interface RetryConfig {
  maxAttempts?: number;
  initialDelay?: number;
  maxDelay?: number;
  exponentialBase?: number;
  jitter?: boolean;
  exceptions?: (new (...args: any[]) => Error)[];
}

export enum CircuitBreakerState {
  CLOSED = 'closed',
  OPEN = 'open',
  HALF_OPEN = 'half_open',
}

export interface CircuitBreakerMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  openStateCount: number;
  halfOpenStateCount: number;
  lastFailureTime?: number;
  lastSuccessTime?: number;
  stateTransitions: number;
  successRate: number;
  failureRate: number;
}

export interface CircuitBreakerConfig {
  failureThreshold?: number;
  timeout?: number;
  halfOpenMaxCalls?: number;
  successThreshold?: number;
  slidingWindowSize?: number;
  name?: string;
}

export class CircuitBreakerError extends GenesisError {
  public readonly circuitName: string;

  constructor(message: string, circuitName: string = 'unknown') {
    super({
      message,
      code: 'CIRCUIT_BREAKER_OPEN',
      category: ErrorCategory.UNAVAILABLE,
      details: {
        circuitName,
        circuitState: 'open',
        errorType: 'circuit_breaker_open',
      },
    });
    this.circuitName = circuitName;
  }
}

/**
 * Sleep utility for async delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Add jitter to delay values
 */
function addJitter(delay: number, jitter: boolean): number {
  if (!jitter) return delay;
  return delay * (0.5 + Math.random());
}

/**
 * Retry decorator for functions and methods
 */
export function retry(config: Required<RetryConfig>) {
  const {
    maxAttempts,
    initialDelay,
    maxDelay,
    exponentialBase,
    jitter,
    exceptions,
  } = config;

  return function <T extends (...args: any[]) => any>(
    target: any,
    propertyName: string,
    descriptor: TypedPropertyDescriptor<T>
  ): TypedPropertyDescriptor<T> {
    const method = descriptor.value!;

    descriptor.value = (async function (this: any, ...args: any[]) {
      let lastException: Error | null = null;

      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
          const result = method.apply(this, args);
          // Handle both sync and async functions
          return result instanceof Promise ? await result : result;
        } catch (error) {
          lastException = error as Error;

          // Check if this exception type should be retried
          const shouldRetry = exceptions.some(ExceptionType =>
            error instanceof ExceptionType
          );

          if (!shouldRetry || attempt === maxAttempts - 1) {
            break;
          }

          const delay = Math.min(
            initialDelay * Math.pow(exponentialBase, attempt),
            maxDelay
          );
          const finalDelay = addJitter(delay, jitter);

          await sleep(finalDelay);
        }
      }

      throw lastException;
    } as any) as T;

    return descriptor;
  };
}

/**
 * Standalone retry function for non-decorator usage
 */
export async function retryFunction<T>(
  fn: () => Promise<T> | T,
  config: Required<RetryConfig>
): Promise<T> {
  const {
    maxAttempts,
    initialDelay,
    maxDelay,
    exponentialBase,
    jitter,
    exceptions,
  } = config;

  let lastException: Error | null = null;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const result = fn();
      return result instanceof Promise ? await result : result;
    } catch (error) {
      lastException = error as Error;

      const shouldRetry = exceptions.some(ExceptionType =>
        error instanceof ExceptionType
      );

      if (!shouldRetry || attempt === maxAttempts - 1) {
        break;
      }

      const delay = Math.min(
        initialDelay * Math.pow(exponentialBase, attempt),
        maxDelay
      );
      const finalDelay = addJitter(delay, jitter);

      await sleep(finalDelay);
    }
  }

  throw lastException;
}

/**
 * Circuit Breaker implementation
 */
export class CircuitBreaker {
  private state: CircuitBreakerState = CircuitBreakerState.CLOSED;
  private lastFailureTime?: number;
  private halfOpenCalls = 0;
  private halfOpenSuccesses = 0;
  private callResults: boolean[] = [];
  private metrics: CircuitBreakerMetrics;

  constructor(private config: Required<CircuitBreakerConfig>) {
    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      openStateCount: 0,
      halfOpenStateCount: 0,
      stateTransitions: 0,
      successRate: 0,
      failureRate: 0,
    };
  }

  static create(config: Required<CircuitBreakerConfig>): CircuitBreaker {
    return new CircuitBreaker(config);
  }

  getState(): CircuitBreakerState {
    return this.state;
  }

  getMetrics(): CircuitBreakerMetrics {
    this.updateMetrics();
    return { ...this.metrics };
  }

  private updateMetrics(): void {
    if (this.metrics.totalRequests > 0) {
      this.metrics.successRate = (this.metrics.successfulRequests / this.metrics.totalRequests) * 100;
      this.metrics.failureRate = (this.metrics.failedRequests / this.metrics.totalRequests) * 100;
    }
  }

  private shouldAttemptReset(): boolean {
    if (this.state !== CircuitBreakerState.OPEN) return false;
    if (!this.lastFailureTime) return false;
    return Date.now() - this.lastFailureTime >= this.config.timeout;
  }

  private transitionToState(newState: CircuitBreakerState): void {
    if (newState === this.state) return;

    this.state = newState;
    this.metrics.stateTransitions++;

    if (newState === CircuitBreakerState.HALF_OPEN) {
      this.halfOpenCalls = 0;
      this.halfOpenSuccesses = 0;
      this.metrics.halfOpenStateCount++;
    } else if (newState === CircuitBreakerState.OPEN) {
      this.metrics.openStateCount++;
    }
  }

  private recordSuccess(): void {
    const currentTime = Date.now();

    this.callResults.push(true);
    if (this.callResults.length > this.config.slidingWindowSize) {
      this.callResults.shift();
    }

    this.metrics.totalRequests++;
    this.metrics.successfulRequests++;
    this.metrics.lastSuccessTime = currentTime;

    if (this.state === CircuitBreakerState.HALF_OPEN) {
      this.halfOpenSuccesses++;
      if (this.halfOpenSuccesses >= this.config.successThreshold) {
        this.transitionToState(CircuitBreakerState.CLOSED);
      }
    }
  }

  private recordFailure(): void {
    const currentTime = Date.now();

    this.callResults.push(false);
    if (this.callResults.length > this.config.slidingWindowSize) {
      this.callResults.shift();
    }

    this.metrics.totalRequests++;
    this.metrics.failedRequests++;
    this.metrics.lastFailureTime = currentTime;
    this.lastFailureTime = currentTime;

    if (this.state === CircuitBreakerState.CLOSED) {
      const recentFailures = this.callResults.filter(result => !result).length;
      if (this.config.failureThreshold > 0 && recentFailures >= this.config.failureThreshold) {
        this.transitionToState(CircuitBreakerState.OPEN);
      }
    } else if (this.state === CircuitBreakerState.HALF_OPEN) {
      this.transitionToState(CircuitBreakerState.OPEN);
    }
  }

  private canExecute(): boolean {
    if (this.state === CircuitBreakerState.CLOSED) {
      return true;
    } else if (this.state === CircuitBreakerState.OPEN) {
      if (this.shouldAttemptReset()) {
        this.transitionToState(CircuitBreakerState.HALF_OPEN);
        this.halfOpenCalls = 1;
        return true;
      }
      return false;
    } else if (this.state === CircuitBreakerState.HALF_OPEN) {
      if (this.halfOpenCalls < this.config.halfOpenMaxCalls) {
        this.halfOpenCalls++;
        return true;
      }
      return false;
    }
    return false;
  }

  async execute<T>(fn: () => Promise<T> | T): Promise<T> {
    if (!this.canExecute()) {
      throw new CircuitBreakerError(
        `Circuit breaker '${this.config.name}' is open. Failure rate: ${this.metrics.failureRate.toFixed(1)}%`,
        this.config.name
      );
    }

    try {
      const result = fn();
      const finalResult = result instanceof Promise ? await result : result;
      this.recordSuccess();
      return finalResult;
    } catch (error) {
      this.recordFailure();
      throw error;
    }
  }

  reset(): void {
    this.transitionToState(CircuitBreakerState.CLOSED);
    this.callResults = [];
    this.halfOpenCalls = 0;
    this.halfOpenSuccesses = 0;
  }

  getStatus(): any {
    this.updateMetrics();
    return {
      name: this.config.name,
      state: this.state,
      failureThreshold: this.config.failureThreshold,
      timeout: this.config.timeout,
      metrics: {
        totalRequests: this.metrics.totalRequests,
        successfulRequests: this.metrics.successfulRequests,
        failedRequests: this.metrics.failedRequests,
        successRate: Math.round(this.metrics.successRate * 100) / 100,
        failureRate: Math.round(this.metrics.failureRate * 100) / 100,
        lastFailureTime: this.metrics.lastFailureTime,
        lastSuccessTime: this.metrics.lastSuccessTime,
        stateTransitions: this.metrics.stateTransitions,
      },
      config: {
        halfOpenMaxCalls: this.config.halfOpenMaxCalls,
        successThreshold: this.config.successThreshold,
        slidingWindowSize: this.config.slidingWindowSize,
      },
    };
  }
}

/**
 * Circuit breaker decorator
 */
export function circuitBreaker(config: Required<CircuitBreakerConfig>) {
  const cb = CircuitBreaker.create(config);

  return function <T extends (...args: any[]) => any>(
    target: any,
    propertyName: string,
    descriptor: TypedPropertyDescriptor<T>
  ): TypedPropertyDescriptor<T> {
    const method = descriptor.value!;

    descriptor.value = (async function (this: any, ...args: any[]) {
      return cb.execute(() => {
        const result = method.apply(this, args);
        return result instanceof Promise ? result : Promise.resolve(result);
      });
    } as any) as T;

    return descriptor;
  };
}

/**
 * Combined retry and circuit breaker for resilient calls
 */
export function resilientCall(
  retryConfig: Required<RetryConfig>,
  circuitConfig: Required<CircuitBreakerConfig>
) {
  const cb = CircuitBreaker.create(circuitConfig);

  return function <T extends (...args: any[]) => any>(
    target: any,
    propertyName: string,
    descriptor: TypedPropertyDescriptor<T>
  ): TypedPropertyDescriptor<T> {
    const method = descriptor.value!;

    descriptor.value = (async function (this: any, ...args: any[]) {
      return cb.execute(async () => {
        return retryFunction(() => {
          const result = method.apply(this, args);
          return result instanceof Promise ? result : Promise.resolve(result);
        }, retryConfig);
      });
    } as any) as T;

    return descriptor;
  };
}

/**
 * Pre-configured resilient decorator for external service calls
 */
export function resilientExternalService(
  maxAttempts: number,
  failureThreshold: number,
  timeout: number,
  name: string,
  initialDelay: number,
  maxDelay: number,
  exponentialBase: number,
  jitter: boolean,
  halfOpenMaxCalls: number,
  successThreshold: number,
  slidingWindowSize: number
) {
  return resilientCall(
    {
      maxAttempts,
      initialDelay,
      maxDelay,
      exponentialBase,
      jitter,
      exceptions: [Error],
    },
    {
      failureThreshold,
      timeout,
      halfOpenMaxCalls,
      successThreshold,
      slidingWindowSize,
      name,
    }
  );
}

/**
 * Pre-configured resilient decorator for database calls
 */
export function resilientDatabase(
  maxAttempts: number,
  failureThreshold: number,
  timeout: number,
  name: string,
  initialDelay: number,
  maxDelay: number,
  exponentialBase: number,
  jitter: boolean,
  halfOpenMaxCalls: number,
  successThreshold: number,
  slidingWindowSize: number
) {
  return resilientCall(
    {
      maxAttempts,
      initialDelay,
      maxDelay,
      exponentialBase,
      jitter,
      exceptions: [Error],
    },
    {
      failureThreshold,
      timeout,
      halfOpenMaxCalls,
      successThreshold,
      slidingWindowSize,
      name,
    }
  );
}
