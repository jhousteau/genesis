/**
 * Genesis Context Management - Simplified
 *
 * Thread-safe context management for distributed applications using AsyncLocalStorage.
 * Provides correlation ID tracking, request context, and distributed tracing support.
 */

import { AsyncLocalStorage } from 'async_hooks';
import { randomUUID } from 'crypto';

export interface TraceContext {
  traceId: string;
  spanId: string;
  parentSpanId?: string;
  baggage?: Record<string, string>;
}

export interface RequestContext {
  correlationId: string;
  requestId: string;
  timestamp: Date;
  userId?: string;
  traceContext?: TraceContext;
  service: string;
  environment: string;
  metadata: Record<string, any>;
}

// AsyncLocalStorage for context management
const contextStorage = new AsyncLocalStorage<RequestContext>();

export class ContextManager {
  constructor(
    private serviceName: string = 'genesis',
    private environment: string = 'development'
  ) {}

  getCurrentContext(): RequestContext | undefined {
    return contextStorage.getStore();
  }

  setCurrentContext(context: RequestContext): void {
    // Note: AsyncLocalStorage doesn't have a direct set method
    // This would typically be used within a run() call
    throw new Error('Use contextScope() to set context in AsyncLocalStorage');
  }

  clearCurrentContext(): void {
    // AsyncLocalStorage automatically clears context when exiting scope
    // This method is kept for API compatibility
  }

  createContext(options: {
    correlationId?: string;
    requestId?: string;
    userId?: string;
    traceContext?: TraceContext;
    metadata?: Record<string, any>;
  } = {}): RequestContext {
    return {
      correlationId: options.correlationId || generateCorrelationId(),
      requestId: options.requestId || generateRequestId(),
      timestamp: new Date(),
      userId: options.userId,
      traceContext: options.traceContext,
      service: this.serviceName,
      environment: this.environment,
      metadata: options.metadata || {},
    };
  }

  async contextScope<T>(
    context: RequestContext,
    fn: () => Promise<T>
  ): Promise<T> {
    return contextStorage.run(context, fn);
  }

  contextScopeSync<T>(context: RequestContext, fn: () => T): T {
    return contextStorage.run(context, fn);
  }
}

// Global context manager instance
let globalContextManager: ContextManager | undefined;

function getContextManager(): ContextManager {
  if (!globalContextManager) {
    globalContextManager = new ContextManager(
      process.env.GENESIS_SERVICE || 'genesis',
      process.env.GENESIS_ENV || 'development'
    );
  }
  return globalContextManager;
}

// Convenience functions for direct context access
export function getContext(): RequestContext | undefined {
  return getContextManager().getCurrentContext();
}

export function setContext(context: RequestContext): void {
  getContextManager().setCurrentContext(context);
}

export function clearContext(): void {
  getContextManager().clearCurrentContext();
}

export async function contextSpan<T>(
  context: RequestContext,
  fn: () => Promise<T>
): Promise<T> {
  return getContextManager().contextScope(context, fn);
}

export function contextSpanSync<T>(
  context: RequestContext,
  fn: () => T
): T {
  return getContextManager().contextScopeSync(context, fn);
}

// Individual context variable accessors
export function getCorrelationId(): string | undefined {
  const context = getContext();
  return context?.correlationId;
}

export function setCorrelationId(correlationId: string): void {
  const context = getContext();
  if (context) {
    context.correlationId = correlationId;
  }
}

export function getRequestId(): string | undefined {
  const context = getContext();
  return context?.requestId;
}

export function getTraceId(): string | undefined {
  const context = getContext();
  return context?.traceContext?.traceId;
}

export function getUserId(): string | undefined {
  const context = getContext();
  return context?.userId;
}

export function getMetadata(): Record<string, any> {
  const context = getContext();
  return context?.metadata || {};
}

// ID generation functions
export function generateCorrelationId(): string {
  return randomUUID();
}

export function generateRequestId(): string {
  return `req_${randomUUID().replace(/-/g, '').slice(0, 12)}`;
}

export function generateTraceId(): string {
  return randomUUID().replace(/-/g, '');
}

export function generateSpanId(): string {
  return randomUUID().replace(/-/g, '').slice(0, 16);
}

// Helper functions for creating contexts
export function createRequestContext(options: {
  userId?: string;
  metadata?: Record<string, any>;
  service?: string;
  environment?: string;
} = {}): RequestContext {
  return {
    correlationId: generateCorrelationId(),
    requestId: generateRequestId(),
    timestamp: new Date(),
    userId: options.userId,
    service: options.service || process.env.GENESIS_SERVICE || 'genesis',
    environment: options.environment || process.env.GENESIS_ENV || 'development',
    metadata: options.metadata || {},
  };
}

export function createTraceContext(options: {
  traceId?: string;
  parentSpanId?: string;
  baggage?: Record<string, string>;
} = {}): TraceContext {
  return {
    traceId: options.traceId || generateTraceId(),
    spanId: generateSpanId(),
    parentSpanId: options.parentSpanId,
    baggage: options.baggage || {},
  };
}

// Context utilities
export function enrichContext(
  context: RequestContext,
  updates: Partial<RequestContext>
): RequestContext {
  return {
    ...context,
    ...updates,
    metadata: { ...context.metadata, ...updates.metadata },
  };
}

export function contextToDict(context: RequestContext): Record<string, any> {
  const result: Record<string, any> = {
    correlationId: context.correlationId,
    requestId: context.requestId,
    timestamp: context.timestamp.toISOString(),
    service: context.service,
    environment: context.environment,
    userId: context.userId,
    metadata: context.metadata,
  };

  if (context.traceContext) {
    result.trace = {
      traceId: context.traceContext.traceId,
      spanId: context.traceContext.spanId,
      parentSpanId: context.traceContext.parentSpanId,
      baggage: context.traceContext.baggage,
    };
  }

  return result;
}

export function getLoggerContext(context?: RequestContext): Record<string, any> {
  const ctx = context || getContext();
  if (!ctx) {
    return {};
  }

  const loggerContext: Record<string, any> = {
    correlationId: ctx.correlationId,
    requestId: ctx.requestId,
  };

  if (ctx.userId) {
    loggerContext.userId = ctx.userId;
  }

  if (ctx.traceContext) {
    loggerContext.traceId = ctx.traceContext.traceId;
    loggerContext.spanId = ctx.traceContext.spanId;
    if (ctx.traceContext.parentSpanId) {
      loggerContext.parentSpanId = ctx.traceContext.parentSpanId;
    }
  }

  return loggerContext;
}

// Helper function to add getLoggerContext method to RequestContext objects
export function addLoggerContextMethod(context: RequestContext): RequestContext & { getLoggerContext(): Record<string, any> } {
  const extended = context as RequestContext & { getLoggerContext(): Record<string, any> };
  extended.getLoggerContext = () => getLoggerContext(context);
  return extended;
}

// Middleware helper for Express-like frameworks
export function createContextMiddleware(options: {
  generateCorrelationId?: boolean;
  extractUserId?: (req: any) => string | undefined;
  extractTraceHeaders?: (req: any) => TraceContext | undefined;
} = {}) {
  const { 
    generateCorrelationId: shouldGenerateId = true,
    extractUserId,
    extractTraceHeaders 
  } = options;

  return (req: any, res: any, next: any) => {
    const correlationId = shouldGenerateId 
      ? generateCorrelationId() 
      : req.headers['x-correlation-id'] || generateCorrelationId();
    
    const userId = extractUserId ? extractUserId(req) : undefined;
    const traceContext = extractTraceHeaders ? extractTraceHeaders(req) : undefined;

    const context = createRequestContext({
      userId,
      metadata: {
        method: req.method,
        url: req.url,
        userAgent: req.headers['user-agent'],
      },
    });

    context.correlationId = correlationId;
    if (traceContext) {
      context.traceContext = traceContext;
    }

    // Add correlation ID to response headers
    res.setHeader('X-Correlation-ID', correlationId);

    // Run the rest of the request in this context
    contextSpanSync(context, () => next());
  };
}