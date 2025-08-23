/**
 * Genesis Metrics Service
 *
 * Prometheus-compatible metrics collection with GCP integration
 * following Genesis observability patterns.
 */

import { Logger } from '../utils/logger';
import { Config } from '../config';

interface Metric {
  name: string;
  type: 'counter' | 'gauge' | 'histogram';
  help: string;
  labels?: Record<string, string>;
  value: number;
  timestamp: Date;
}

export class MetricsCollector {
  private static instance: MetricsCollector;
  private metrics = new Map<string, Metric>();
  private logger: Logger;

  private constructor() {
    this.logger = Logger.getInstance('metrics');
    this.initializeDefaultMetrics();
  }

  public static getInstance(): MetricsCollector {
    if (!MetricsCollector.instance) {
      MetricsCollector.instance = new MetricsCollector();
    }
    return MetricsCollector.instance;
  }

  /**
   * Initialize metrics collector
   */
  public async initialize(): Promise<void> {
    this.logger.info('Metrics collector initialized');
  }

  /**
   * Record a request
   */
  public recordRequest(method: string, path: string): void {
    const key = `http_requests_total:${method}:${this.normalizePath(path)}`;
    this.incrementCounter(key, 'http_requests_total', 'Total HTTP requests', {
      method,
      path: this.normalizePath(path)
    });
  }

  /**
   * Record a response
   */
  public recordResponse(method: string, path: string, statusCode: number, duration: number): void {
    // Response counter
    const responseKey = `http_responses_total:${method}:${this.normalizePath(path)}:${statusCode}`;
    this.incrementCounter(responseKey, 'http_responses_total', 'Total HTTP responses', {
      method,
      path: this.normalizePath(path),
      status_code: statusCode.toString()
    });

    // Response duration histogram
    const durationKey = `http_request_duration_ms:${method}:${this.normalizePath(path)}`;
    this.observeHistogram(durationKey, 'http_request_duration_ms', 'HTTP request duration in milliseconds', duration, {
      method,
      path: this.normalizePath(path)
    });
  }

  /**
   * Record startup event
   */
  public recordStartup(): void {
    this.incrementCounter('app_starts_total', 'app_starts_total', 'Total application starts');
  }

  /**
   * Record custom metric
   */
  public recordCustomMetric(name: string, value: number, labels?: Record<string, string>): void {
    const key = labels ? `${name}:${Object.values(labels).join(':')}` : name;
    this.setGauge(key, name, 'Custom metric', value, labels);
  }

  /**
   * Get Prometheus-formatted metrics
   */
  public async getPrometheusMetrics(): Promise<string> {
    const lines: string[] = [];
    const metricGroups = new Map<string, Metric[]>();

    // Group metrics by name
    for (const metric of this.metrics.values()) {
      if (!metricGroups.has(metric.name)) {
        metricGroups.set(metric.name, []);
      }
      metricGroups.get(metric.name)!.push(metric);
    }

    // Format each metric group
    for (const [name, metrics] of metricGroups) {
      const firstMetric = metrics[0];

      // Add help and type
      lines.push(`# HELP ${name} ${firstMetric.help}`);
      lines.push(`# TYPE ${name} ${firstMetric.type}`);

      // Add metric values
      for (const metric of metrics) {
        const labelStr = metric.labels ?
          '{' + Object.entries(metric.labels).map(([k, v]) => `${k}="${v}"`).join(',') + '}' :
          '';
        lines.push(`${name}${labelStr} ${metric.value}`);
      }

      lines.push(''); // Empty line between metrics
    }

    return lines.join('\n');
  }

  /**
   * Get all metrics as JSON
   */
  public getMetricsAsJSON(): Record<string, any> {
    const result: Record<string, any> = {};

    for (const [key, metric] of this.metrics) {
      result[key] = {
        value: metric.value,
        labels: metric.labels,
        timestamp: metric.timestamp
      };
    }

    return result;
  }

  // Private methods

  private incrementCounter(key: string, name: string, help: string, labels?: Record<string, string>): void {
    const existing = this.metrics.get(key);
    const value = existing ? existing.value + 1 : 1;

    this.metrics.set(key, {
      name,
      type: 'counter',
      help,
      labels,
      value,
      timestamp: new Date()
    });
  }

  private setGauge(key: string, name: string, help: string, value: number, labels?: Record<string, string>): void {
    this.metrics.set(key, {
      name,
      type: 'gauge',
      help,
      labels,
      value,
      timestamp: new Date()
    });
  }

  private observeHistogram(key: string, name: string, help: string, value: number, labels?: Record<string, string>): void {
    // Simplified histogram - in production you'd want proper bucket handling
    this.metrics.set(key, {
      name,
      type: 'histogram',
      help,
      labels,
      value,
      timestamp: new Date()
    });
  }

  private normalizePath(path: string): string {
    // Replace dynamic path segments with placeholders
    return path
      .replace(/\/\d+/g, '/{id}')
      .replace(/\/[a-f0-9-]{36}/g, '/{uuid}')
      .replace(/\/[a-f0-9]{24}/g, '/{objectId}');
  }

  private initializeDefaultMetrics(): void {
    const config = Config.getInstance();

    // Application info
    this.setGauge('app_info', 'app_info', 'Application information', 1, {
      service: config.serviceName,
      version: config.version,
      environment: config.environment
    });

    // Node.js version
    this.setGauge('nodejs_version_info', 'nodejs_version_info', 'Node.js version', 1, {
      version: process.version
    });

    // Start time
    this.setGauge('process_start_time_seconds', 'process_start_time_seconds', 'Process start time in seconds',
      Date.now() / 1000);

    // Setup periodic system metrics
    setInterval(() => {
      this.collectSystemMetrics();
    }, 10000); // Every 10 seconds
  }

  private collectSystemMetrics(): void {
    // Memory usage
    const memUsage = process.memoryUsage();
    this.setGauge('process_resident_memory_bytes', 'process_resident_memory_bytes',
      'Resident memory usage in bytes', memUsage.rss);
    this.setGauge('process_heap_bytes', 'process_heap_bytes',
      'Process heap size in bytes', memUsage.heapUsed);
    this.setGauge('process_heap_total_bytes', 'process_heap_total_bytes',
      'Total heap size in bytes', memUsage.heapTotal);

    // CPU usage (simplified)
    const cpuUsage = process.cpuUsage();
    this.setGauge('process_cpu_user_seconds_total', 'process_cpu_user_seconds_total',
      'Total user CPU time spent in seconds', cpuUsage.user / 1000000);
    this.setGauge('process_cpu_system_seconds_total', 'process_cpu_system_seconds_total',
      'Total system CPU time spent in seconds', cpuUsage.system / 1000000);

    // Event loop lag
    const start = process.hrtime.bigint();
    setImmediate(() => {
      const lag = Number(process.hrtime.bigint() - start) / 1000000;
      this.setGauge('nodejs_eventloop_lag_milliseconds', 'nodejs_eventloop_lag_milliseconds',
        'Event loop lag in milliseconds', lag);
    });

    // Active handles and requests
    (process as any)._getActiveHandles &&
      this.setGauge('nodejs_active_handles_total', 'nodejs_active_handles_total',
        'Number of active handles', (process as any)._getActiveHandles().length);

    (process as any)._getActiveRequests &&
      this.setGauge('nodejs_active_requests_total', 'nodejs_active_requests_total',
        'Number of active requests', (process as any)._getActiveRequests().length);
  }
}
