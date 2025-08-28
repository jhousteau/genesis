/**
 * Lightweight health check system
 */

import { handleError } from './errors';

export enum HealthStatus {
  HEALTHY = 'healthy',
  UNHEALTHY = 'unhealthy',
  DEGRADED = 'degraded',
}

export interface CheckResult {
  name: string;
  status: HealthStatus;
  message?: string;
  durationMs?: number;
  timestamp?: Date;
  metadata?: Record<string, any>;
}

export interface HealthSummary {
  overallStatus: HealthStatus;
  timestamp: string;
  checks: Array<{
    name: string;
    status: HealthStatus;
    message?: string;
    durationMs?: number;
    metadata?: Record<string, any>;
  }>;
  summary: {
    totalChecks: number;
    healthy: number;
    unhealthy: number;
    degraded: number;
  };
}

export type HealthCheckFunction = () => Promise<CheckResult> | CheckResult;

/**
 * Simple health check coordinator
 */
export class HealthCheck {
  private checks: Map<string, HealthCheckFunction> = new Map();

  /**
   * Add a health check function
   */
  addCheck(name: string, checkFunc: HealthCheckFunction): void {
    this.checks.set(name, checkFunc);
  }

  /**
   * Remove a health check by name
   */
  removeCheck(name: string): void {
    this.checks.delete(name);
  }

  /**
   * Run a single health check by name
   */
  async runCheck(name: string): Promise<CheckResult> {
    const checkFunc = this.checks.get(name);
    if (!checkFunc) {
      return {
        name,
        status: HealthStatus.UNHEALTHY,
        message: `Check '${name}' not found`,
        timestamp: new Date(),
        durationMs: 0,
      };
    }

    const startTime = performance.now();
    try {
      const result = await checkFunc();
      const endTime = performance.now();

      return {
        ...result,
        name,
        timestamp: result.timestamp || new Date(),
        durationMs: result.durationMs || (endTime - startTime),
      };
    } catch (error) {
      const endTime = performance.now();
      const handledError = handleError(error as Error);

      return {
        name,
        status: HealthStatus.UNHEALTHY,
        message: `Check failed: ${handledError.message}`,
        timestamp: new Date(),
        durationMs: endTime - startTime,
        metadata: {
          errorCode: handledError.code,
          errorCategory: handledError.category,
        },
      };
    }
  }

  /**
   * Run all registered health checks
   */
  async runAllChecks(): Promise<CheckResult[]> {
    const checkNames = Array.from(this.checks.keys());
    const results = await Promise.all(
      checkNames.map(name => this.runCheck(name))
    );
    return results;
  }

  /**
   * Get overall health status based on all checks
   */
  async getOverallStatus(): Promise<HealthStatus> {
    if (this.checks.size === 0) {
      return HealthStatus.HEALTHY;
    }

    const results = await this.runAllChecks();

    // If any check is unhealthy, overall is unhealthy
    if (results.some(r => r.status === HealthStatus.UNHEALTHY)) {
      return HealthStatus.UNHEALTHY;
    }

    // If any check is degraded, overall is degraded
    if (results.some(r => r.status === HealthStatus.DEGRADED)) {
      return HealthStatus.DEGRADED;
    }

    return HealthStatus.HEALTHY;
  }

  /**
   * Get health check summary
   */
  async getSummary(): Promise<HealthSummary> {
    const results = await this.runAllChecks();
    const overallStatus = await this.getOverallStatus();

    return {
      overallStatus,
      timestamp: new Date().toISOString(),
      checks: results.map(r => ({
        name: r.name,
        status: r.status,
        message: r.message,
        durationMs: r.durationMs,
        metadata: r.metadata,
      })),
      summary: {
        totalChecks: results.length,
        healthy: results.filter(r => r.status === HealthStatus.HEALTHY).length,
        unhealthy: results.filter(r => r.status === HealthStatus.UNHEALTHY).length,
        degraded: results.filter(r => r.status === HealthStatus.DEGRADED).length,
      },
    };
  }

  /**
   * Get list of registered check names
   */
  getCheckNames(): string[] {
    return Array.from(this.checks.keys());
  }
}

/**
 * Common health check implementations
 */
export const HealthChecks = {
  /**
   * Simple ping check that always returns healthy
   */
  ping: (): CheckResult => ({
    name: 'ping',
    status: HealthStatus.HEALTHY,
    message: 'Service is responding',
  }),

  /**
   * Memory usage check
   */
  memory: (maxMemoryMB: number): CheckResult => {
    const memUsage = process.memoryUsage();
    const heapUsedMB = Math.round(memUsage.heapUsed / 1024 / 1024);

    if (heapUsedMB > maxMemoryMB) {
      return {
        name: 'memory',
        status: HealthStatus.UNHEALTHY,
        message: `High memory usage: ${heapUsedMB}MB (max: ${maxMemoryMB}MB)`,
        metadata: { heapUsedMB, maxMemoryMB },
      };
    }

    if (heapUsedMB > maxMemoryMB * 0.8) {
      return {
        name: 'memory',
        status: HealthStatus.DEGRADED,
        message: `Memory usage approaching limit: ${heapUsedMB}MB (max: ${maxMemoryMB}MB)`,
        metadata: { heapUsedMB, maxMemoryMB },
      };
    }

    return {
      name: 'memory',
      status: HealthStatus.HEALTHY,
      message: `Memory usage normal: ${heapUsedMB}MB (max: ${maxMemoryMB}MB)`,
      metadata: { heapUsedMB, maxMemoryMB },
    };
  },

  /**
   * Disk space check (Node.js specific)
   */
  diskSpace: async (path: string, minFreeGB: number): Promise<CheckResult> => {
    try {
      const fs = await import('fs');
      const { promisify } = await import('util');
      const statvfs = promisify(fs.statSync);

      // Note: This is a simplified check - in production you'd want to use a proper disk space library
      return {
        name: 'disk_space',
        status: HealthStatus.HEALTHY,
        message: 'Disk space check not fully implemented in this basic version',
        metadata: { path, minFreeGB },
      };
    } catch (error) {
      return {
        name: 'disk_space',
        status: HealthStatus.UNHEALTHY,
        message: `Disk space check failed: ${(error as Error).message}`,
        metadata: { path, minFreeGB },
      };
    }
  },

  /**
   * HTTP endpoint check
   */
  httpEndpoint: async (
    url: string,
    timeoutMs: number,
    expectedStatus: number
  ): Promise<CheckResult> => {
    const startTime = performance.now();

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      const response = await fetch(url, {
        signal: controller.signal,
        method: 'GET',
      });

      clearTimeout(timeoutId);
      const endTime = performance.now();
      const durationMs = endTime - startTime;

      if (response.status === expectedStatus) {
        return {
          name: 'http_endpoint',
          status: HealthStatus.HEALTHY,
          message: `Endpoint responding: ${response.status}`,
          durationMs,
          metadata: { url, status: response.status, expectedStatus },
        };
      } else {
        return {
          name: 'http_endpoint',
          status: HealthStatus.UNHEALTHY,
          message: `Unexpected status: ${response.status} (expected: ${expectedStatus})`,
          durationMs,
          metadata: { url, status: response.status, expectedStatus },
        };
      }
    } catch (error) {
      const endTime = performance.now();
      const durationMs = endTime - startTime;

      return {
        name: 'http_endpoint',
        status: HealthStatus.UNHEALTHY,
        message: `Endpoint check failed: ${(error as Error).message}`,
        durationMs,
        metadata: { url, expectedStatus },
      };
    }
  },

  /**
   * Database connection check (generic)
   */
  database: async (
    connectionTest: () => Promise<boolean>,
    name: string
  ): Promise<CheckResult> => {
    try {
      const isConnected = await connectionTest();

      return {
        name,
        status: isConnected ? HealthStatus.HEALTHY : HealthStatus.UNHEALTHY,
        message: isConnected ? 'Database connection successful' : 'Database connection failed',
      };
    } catch (error) {
      return {
        name,
        status: HealthStatus.UNHEALTHY,
        message: `Database check failed: ${(error as Error).message}`,
      };
    }
  },
} as const;
