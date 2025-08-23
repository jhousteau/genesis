/**
 * Genesis Route Registration
 *
 * Central route registration following Genesis patterns
 * with proper error handling and middleware integration.
 */

import { FastifyInstance } from 'fastify';
import { Logger } from '../utils/logger';

// Import route handlers
import { healthRoutes } from './health';
import { apiRoutes } from './api';

const logger = Logger.getInstance('routes');

/**
 * Register all application routes
 */
export async function registerRoutes(server: FastifyInstance): Promise<void> {
  try {
    logger.info('Registering application routes');

    // Health and monitoring routes
    await server.register(healthRoutes, { prefix: '/health' });

    // API routes
    await server.register(apiRoutes, { prefix: '/api/v1' });

    logger.info('All routes registered successfully');

  } catch (error) {
    logger.error('Failed to register routes', { error: error.message });
    throw error;
  }
}
