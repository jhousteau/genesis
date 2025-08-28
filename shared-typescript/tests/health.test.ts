import { HealthCheck, HealthStatus, HealthChecks } from '../src/health';

describe('Health Checks', () => {
  describe('HealthCheck', () => {
    let healthCheck: HealthCheck;

    beforeEach(() => {
      healthCheck = new HealthCheck();
    });

    it('should add and run health checks', async () => {
      healthCheck.addCheck('test', () => ({
        name: 'test',
        status: HealthStatus.HEALTHY,
        message: 'All good',
      }));

      const result = await healthCheck.runCheck('test');

      expect(result.name).toBe('test');
      expect(result.status).toBe(HealthStatus.HEALTHY);
      expect(result.message).toBe('All good');
      expect(result.durationMs).toBeDefined();
    });

    it('should handle missing checks', async () => {
      const result = await healthCheck.runCheck('missing');

      expect(result.status).toBe(HealthStatus.UNHEALTHY);
      expect(result.message).toContain('not found');
    });

    it('should handle check failures', async () => {
      healthCheck.addCheck('failing', () => {
        throw new Error('Check failed');
      });

      const result = await healthCheck.runCheck('failing');

      expect(result.status).toBe(HealthStatus.UNHEALTHY);
      expect(result.message).toContain('Check failed');
    });

    it('should calculate overall status correctly', async () => {
      healthCheck.addCheck('healthy', () => ({
        name: 'healthy',
        status: HealthStatus.HEALTHY,
      }));

      healthCheck.addCheck('unhealthy', () => ({
        name: 'unhealthy',
        status: HealthStatus.UNHEALTHY,
      }));

      const overallStatus = await healthCheck.getOverallStatus();
      expect(overallStatus).toBe(HealthStatus.UNHEALTHY);
    });

    it('should generate summary correctly', async () => {
      healthCheck.addCheck('healthy', () => ({
        name: 'healthy',
        status: HealthStatus.HEALTHY,
      }));

      healthCheck.addCheck('degraded', () => ({
        name: 'degraded',
        status: HealthStatus.DEGRADED,
      }));

      const summary = await healthCheck.getSummary();

      expect(summary.overallStatus).toBe(HealthStatus.DEGRADED);
      expect(summary.checks).toHaveLength(2);
      expect(summary.summary.totalChecks).toBe(2);
      expect(summary.summary.healthy).toBe(1);
      expect(summary.summary.degraded).toBe(1);
    });
  });

  describe('HealthChecks utilities', () => {
    it('should create ping check', () => {
      const result = HealthChecks.ping();

      expect(result.name).toBe('ping');
      expect(result.status).toBe(HealthStatus.HEALTHY);
    });

    it('should check memory usage', () => {
      const result = HealthChecks.memory(1024);

      expect(result.name).toBe('memory');
      expect(result.status).toBeDefined();
      expect(result.metadata?.heapUsedMB).toBeDefined();
    });
  });
});
