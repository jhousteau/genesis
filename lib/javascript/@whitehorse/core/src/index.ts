/**
 * @whitehorse/core - Industrial-strength core library for the Universal Project Platform
 *
 * This library provides comprehensive utilities for building cloud-native applications
 * with focus on GCP integration, observability, and enterprise-grade features.
 */

// Core modules
export { Logger, createLogger, LogLevel } from './logging';
export { Config, ConfigManager, loadConfig } from './config';
export { Registry, ProjectRegistry, ProjectInfo, ServiceInfo } from './registry';
export { ApiClient, HttpClient, RequestOptions, ApiResponse } from './api-client';
export { HealthChecker, HealthCheck, HealthStatus } from './health';
export { SecurityManager, TokenManager, User, Role } from './security';

// Storage and caching
export { StorageClient, GCSStorage, LocalStorage } from './storage';
export { CacheManager, RedisCache, MemoryCache } from './cache';
export { DatabaseClient, ConnectionPool } from './database';

// Monitoring and observability
export { MetricsCollector, Metric, MetricType } from './metrics';
export { TracingClient, Span, TraceContext } from './tracing';
export { QueueManager, Queue, QueueMessage } from './queue';

// Utilities
export { retry, timeout, delay, CircuitBreaker } from './utils/async';
export { validateSchema, ValidationError } from './utils/validation';
export { encrypt, decrypt, generateHash } from './utils/crypto';
export { parseDate, formatDate, isValidDate } from './utils/date';
export { deepMerge, pick, omit, isEmpty } from './utils/object';

// Error handling
export {
  WhitehorseError,
  ValidationError as CoreValidationError,
  AuthenticationError,
  AuthorizationError,
  NetworkError,
  DatabaseError,
  ExternalServiceError,
  ConfigurationError,
  BusinessLogicError,
  SystemError
} from './errors';

// Types
export * from './types';

// MCP Protocol Support
export * from './mcp';

// Version
export const VERSION = '1.0.0';
