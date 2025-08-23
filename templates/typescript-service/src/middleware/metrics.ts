/**
 * Genesis Metrics Middleware
 *
 * Request metrics collection with Prometheus integration
 * following Genesis observability patterns.
 */

import { FastifyRequest, FastifyReply } from 'fastify';
import { Logger } from '../utils/logger';
import { MetricsCollector } from '../services/metrics';

const logger = Logger.getInstance('metrics-middleware');

/**
 * Metrics collection middleware
 */
export async function metricsMiddleware(
  request: FastifyRequest,
  reply: FastifyReply
): Promise<void> {
  const startTime = Date.now();
  const metrics = MetricsCollector.getInstance();

  // Increment request counter
  metrics.recordRequest(request.method, request.url);

  // Set up response time tracking
  reply.addHook('onSend', async (request, reply, payload) => {
    const duration = Date.now() - startTime;
    const statusCode = reply.statusCode;

    // Record response metrics
    metrics.recordResponse(
      request.method,
      request.url,
      statusCode,
      duration
    );

    // Log request details
    logger.logRequest(
      request.method,
      request.url,
      statusCode,
      duration,
      {
        requestId: request.id,
        userAgent: request.headers['user-agent'],
        contentLength: payload ? Buffer.byteLength(payload) : 0
      }
    );

    return payload;
  });
}
