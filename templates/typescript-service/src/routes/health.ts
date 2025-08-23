/**
 * Genesis Health Routes
 *
 * Health check and monitoring endpoints
 * following Genesis observability patterns.
 */

import { FastifyInstance } from 'fastify';
import { HealthChecker } from '../services/health';

export async function healthRoutes(server: FastifyInstance): Promise<void> {
  const healthChecker = HealthChecker.getInstance();

  // Basic health check
  server.get('/', {
    schema: {
      tags: ['health'],
      summary: 'Basic health check',
      response: {
        200: {
          type: 'object',
          properties: {
            status: { type: 'string' },
            timestamp: { type: 'string' }
          }
        }
      }
    }
  }, async (request, reply) => {
    return reply.send({
      status: 'healthy',
      timestamp: new Date().toISOString()
    });
  });

  // Detailed health check
  server.get('/detailed', {
    schema: {
      tags: ['health'],
      summary: 'Detailed health check',
      response: {
        200: {
          type: 'object',
          properties: {
            status: { type: 'string' },
            timestamp: { type: 'string' },
            uptime: { type: 'number' },
            checks: { type: 'object' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const checks = await healthChecker.checkHealth();

    return reply.send({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      checks
    });
  });
}
