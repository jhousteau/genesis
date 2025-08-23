/**
 * Genesis API Routes
 *
 * Main API endpoints following Genesis CRAFT methodology
 * with comprehensive validation and error handling.
 */

import { FastifyInstance } from 'fastify';
import { Logger } from '../utils/logger';

const logger = Logger.getInstance('api-routes');

export async function apiRoutes(server: FastifyInstance): Promise<void> {

  // Example API endpoint
  server.get('/status', {
    schema: {
      tags: ['api'],
      summary: 'Get API status',
      response: {
        200: {
          type: 'object',
          properties: {
            service: { type: 'string' },
            version: { type: 'string' },
            environment: { type: 'string' },
            timestamp: { type: 'string' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const { Config } = await import('../config');
    const config = Config.getInstance();

    return reply.send({
      service: config.serviceName,
      version: config.version,
      environment: config.environment,
      timestamp: new Date().toISOString()
    });
  });

  // Example authenticated endpoint
  server.get('/protected', {
    schema: {
      tags: ['api'],
      summary: 'Protected endpoint example',
      security: [{ bearerAuth: [] }],
      response: {
        200: {
          type: 'object',
          properties: {
            message: { type: 'string' },
            user: { type: 'object' }
          }
        }
      }
    }
  }, async (request, reply) => {
    // This would use the auth middleware
    return reply.send({
      message: 'This is a protected endpoint',
      user: (request as any).user || null
    });
  });

  logger.info('API routes registered');
}
