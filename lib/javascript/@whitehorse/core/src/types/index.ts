/**
 * Type definitions for the Whitehorse Core Library
 */

export interface BaseConfig {
  environment: string;
  debug: boolean;
  logLevel: string;
  gcpProject?: string;
  gcpRegion: string;
  serviceName: string;
  serviceVersion: string;
  healthCheckPort: number;
  healthCheckPath: string;
}

export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
  poolSize: number;
  timeout: number;
}

export interface RedisConfig {
  host: string;
  port: number;
  password?: string;
  database: number;
  maxConnections: number;
  timeout: number;
}

export interface ApiConfig {
  host: string;
  port: number;
  timeout: number;
  retryAttempts: number;
  corsOrigins: string[];
  rateLimitPerSecond: number;
}

export interface CloudProvider {
  type: 'gcp' | 'aws' | 'azure' | 'multi';
  project?: string;
  region: string;
  credentials?: Record<string, any>;
}

export interface ServiceEndpoint {
  name: string;
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  timeout?: number;
  retryAttempts?: number;
}

export interface SecurityPolicy {
  requireAuthentication: boolean;
  requireEncryption: boolean;
  allowedOrigins: string[];
  tokenExpiration: number;
  maxLoginAttempts: number;
  passwordPolicy: {
    minLength: number;
    requireUppercase: boolean;
    requireLowercase: boolean;
    requireNumbers: boolean;
    requireSpecialChars: boolean;
  };
}

export interface MonitoringConfig {
  enabled: boolean;
  metricsPort: number;
  enablePrometheus: boolean;
  enableGcp: boolean;
  alertingRules: AlertRule[];
  retentionDays: number;
}

export interface AlertRule {
  name: string;
  condition: string;
  threshold: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  channels: string[];
}

export interface LoggingConfig {
  level: 'debug' | 'info' | 'warn' | 'error';
  format: 'json' | 'text';
  destination: 'console' | 'file' | 'gcp' | 'all';
  enableStructured: boolean;
  enableCorrelationId: boolean;
  enablePerformanceLogging: boolean;
}

export interface ProjectMetadata {
  id: string;
  name: string;
  description: string;
  owner: string;
  team: string;
  environment: string;
  criticality: 'low' | 'medium' | 'high' | 'critical';
  tags: Record<string, string>;
  created: string;
  updated: string;
}

export interface ServiceMetadata {
  name: string;
  version: string;
  type: 'api' | 'worker' | 'cron' | 'web' | 'cli';
  language: string;
  framework?: string;
  port?: number;
  healthEndpoint?: string;
  dependencies: string[];
  resources: {
    cpu: string;
    memory: string;
    storage?: string;
  };
}

export interface DeploymentTarget {
  name: string;
  environment: string;
  cloudProvider: CloudProvider;
  cluster?: string;
  namespace?: string;
  replicas?: number;
  autoScaling?: {
    enabled: boolean;
    minReplicas: number;
    maxReplicas: number;
    targetCpu: number;
    targetMemory: number;
  };
}

export interface EnvironmentConfig {
  name: string;
  type: 'development' | 'testing' | 'staging' | 'production';
  cloudProvider: CloudProvider;
  database: DatabaseConfig;
  redis?: RedisConfig;
  api: ApiConfig;
  security: SecurityPolicy;
  monitoring: MonitoringConfig;
  logging: LoggingConfig;
  secrets: Record<string, string>;
  features: Record<string, boolean>;
}

export interface HealthCheckResult {
  name: string;
  status: 'healthy' | 'unhealthy' | 'degraded' | 'unknown';
  timestamp: string;
  duration: number;
  details?: Record<string, any>;
  error?: string;
}

export interface SystemHealth {
  overall: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  version: string;
  uptime: number;
  checks: HealthCheckResult[];
  resources: {
    cpu: number;
    memory: number;
    disk: number;
    connections: number;
  };
}

export interface MetricPoint {
  name: string;
  value: number;
  timestamp: string;
  labels: Record<string, string>;
  unit?: string;
}

export interface TraceSpan {
  id: string;
  traceId: string;
  parentId?: string;
  operationName: string;
  startTime: string;
  endTime?: string;
  duration?: number;
  status: 'ok' | 'error' | 'timeout';
  tags: Record<string, any>;
  logs: Array<{
    timestamp: string;
    level: string;
    message: string;
    fields?: Record<string, any>;
  }>;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  userId?: string;
  action: string;
  resource: string;
  outcome: 'success' | 'failure';
  details: Record<string, any>;
  ipAddress?: string;
  userAgent?: string;
}

export interface CacheEntry<T = any> {
  key: string;
  value: T;
  ttl: number;
  created: string;
  accessed: string;
  hits: number;
}

export interface QueueJob<T = any> {
  id: string;
  type: string;
  payload: T;
  priority: number;
  attempts: number;
  maxAttempts: number;
  delay?: number;
  created: string;
  scheduled?: string;
  started?: string;
  completed?: string;
  failed?: string;
  error?: string;
}

export interface StorageObject {
  name: string;
  bucket: string;
  size: number;
  contentType: string;
  etag: string;
  created: string;
  updated: string;
  metadata: Record<string, string>;
}

export interface ApiRequest {
  method: string;
  url: string;
  headers: Record<string, string>;
  query?: Record<string, any>;
  body?: any;
  timeout?: number;
  retries?: number;
}

export interface ApiResponse<T = any> {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: T;
  duration: number;
  request: ApiRequest;
}

export interface PaginationOptions {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  filters?: Record<string, any>;
}

export interface PaginatedResponse<T = any> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

export interface RetryOptions {
  attempts: number;
  delay: number;
  backoff?: 'fixed' | 'exponential' | 'linear';
  maxDelay?: number;
  jitter?: boolean;
  retryCondition?: (error: Error) => boolean;
}

export interface CircuitBreakerOptions {
  threshold: number;
  timeout: number;
  monitoringPeriod: number;
  fallback?: () => any;
}

export interface ValidationRule {
  field: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object' | 'date' | 'email' | 'url';
  required?: boolean;
  min?: number;
  max?: number;
  pattern?: string;
  enum?: any[];
  custom?: (value: any) => boolean | string;
}

export interface ValidationResult {
  valid: boolean;
  errors: Array<{
    field: string;
    message: string;
    value?: any;
  }>;
}

export interface EventEmitter {
  on(event: string, listener: (...args: any[]) => void): void;
  off(event: string, listener: (...args: any[]) => void): void;
  emit(event: string, ...args: any[]): void;
  once(event: string, listener: (...args: any[]) => void): void;
  removeAllListeners(event?: string): void;
}

export interface AsyncOperation<T = any> {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  result?: T;
  error?: Error;
  progress?: number;
  started: string;
  completed?: string;
}

export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'fatal';

export type Environment = 'development' | 'testing' | 'staging' | 'production';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD' | 'OPTIONS';

export type MetricType = 'counter' | 'gauge' | 'histogram' | 'summary';

export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical';

export type DeploymentStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled';

export type DeploymentStrategy = 'rolling' | 'blue-green' | 'canary' | 'recreate';

export type StorageProvider = 'gcs' | 's3' | 'azure' | 'local';

export type QueueProvider = 'redis' | 'gcp-pubsub' | 'aws-sqs' | 'memory';

export type CacheProvider = 'redis' | 'memcached' | 'memory';

export type DatabaseProvider = 'postgresql' | 'mysql' | 'mongodb' | 'firestore';