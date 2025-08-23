/**
 * Genesis Fastify Server Implementation
 *
 * Following Genesis CRAFT methodology for robust server implementation
 */

import Fastify, { FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';

import { Config } from './config';
import { Logger } from './utils/logger';
import { registerRoutes } from './routes';
import { errorHandler } from './middleware/error-handler';
import { authMiddleware } from './middleware/auth';
import { metricsMiddleware } from './middleware/metrics';
import { GenesisError } from './types/errors';

const logger = Logger.getInstance('server');

export async function createServer(): Promise<FastifyInstance> {
  const config = Config.getInstance();

  // Create Fastify instance with custom logger
  const server = Fastify({
    logger: {
      level: config.logLevel,
      serializers: {
        req: (req) => ({
          method: req.method,
          url: req.url,
          headers: {
            host: req.headers.host,
            'user-agent': req.headers['user-agent'],
            'x-request-id': req.headers['x-request-id']
          }
        }),
        res: (res) => ({
          statusCode: res.statusCode,
          headers: {
            'content-type': res.headers['content-type'],
            'content-length': res.headers['content-length']
          }
        })
      }
    },
    genReqId: () => {
      return require('uuid').v4();
    },
    trustProxy: true,
    disableRequestLogging: false
  });

  // Register security plugins
  await server.register(cors, {
    origin: config.cors.origins,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-ID'],
    credentials: true
  });

  await server.register(helmet, {
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        scriptSrc: ["'self'"],
        imgSrc: ["'self'", "data:", "https:"]
      }
    },
    hsts: {
      maxAge: 31536000,
      includeSubDomains: true,
      preload: true
    }
  });

  // Register rate limiting
  await server.register(rateLimit, {
    max: config.rateLimiting.max,
    timeWindow: config.rateLimiting.timeWindow,
    allowList: ['127.0.0.1'],
    redis: config.redis.enabled ? {
      host: config.redis.host,
      port: config.redis.port,
      password: config.redis.password
    } : undefined
  });

  // Register Swagger documentation
  if (config.environment !== 'production') {
    await server.register(swagger, {
      swagger: {
        info: {
          title: '{{PROJECT_NAME}} API',
          description: 'Genesis TypeScript Service API Documentation',
          version: '1.0.0'
        },
        externalDocs: {
          url: 'https://swagger.io',
          description: 'Find more info here'
        },
        host: `localhost:${config.port}`,
        schemes: ['http', 'https'],
        consumes: ['application/json'],
        produces: ['application/json'],
        tags: [
          { name: 'health', description: 'Health check endpoints' },
          { name: 'auth', description: 'Authentication endpoints' },
          { name: 'api', description: 'Main API endpoints' }
        ]
      }
    });

    await server.register(swaggerUi, {
      routePrefix: '/docs',
      uiConfig: {
        docExpansion: 'full',
        deepLinking: false
      },
      uiHooks: {
        onRequest: function (request, reply, next) { next(); },
        preHandler: function (request, reply, next) { next(); }
      },
      staticCSP: true,
      transformStaticCSP: (header) => header
    });
  }

  // Register global middleware
  server.addHook('onRequest', metricsMiddleware);
  server.addHook('preHandler', authMiddleware);

  // Register error handler
  server.setErrorHandler(errorHandler);

  // Register routes
  await registerRoutes(server);

  // Add health check endpoint
  server.get('/health', {
    schema: {
      tags: ['health'],
      summary: 'Health check endpoint',
      description: 'Returns the health status of the service',
      response: {
        200: {
          type: 'object',
          properties: {
            status: { type: 'string' },
            timestamp: { type: 'string' },
            uptime: { type: 'number' },
            version: { type: 'string' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const startTime = Date.now();

    try {
      const health = await import('./services/health');
      const healthStatus = await health.HealthChecker.getInstance().checkHealth();

      return reply.send({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        version: process.env.npm_package_version || '1.0.0',
        checks: healthStatus
      });
    } catch (error) {
      logger.error('Health check failed', { error: error.message });
      return reply.status(503).send({
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        error: error.message
      });
    } finally {
      const duration = Date.now() - startTime;
      logger.debug('Health check completed', { duration });
    }
  });

  // Add readiness endpoint
  server.get('/ready', {
    schema: {
      tags: ['health'],
      summary: 'Readiness check endpoint',
      description: 'Returns whether the service is ready to accept requests',
      response: {
        200: {
          type: 'object',
          properties: {
            ready: { type: 'boolean' },
            timestamp: { type: 'string' }
          }
        }
      }
    }
  }, async (request, reply) => {
    try {
      const health = await import('./services/health');
      const isReady = await health.HealthChecker.getInstance().isReady();

      if (isReady) {
        return reply.send({
          ready: true,
          timestamp: new Date().toISOString()
        });
      } else {
        return reply.status(503).send({
          ready: false,
          timestamp: new Date().toISOString()
        });
      }
    } catch (error) {
      logger.error('Readiness check failed', { error: error.message });
      return reply.status(503).send({
        ready: false,
        timestamp: new Date().toISOString(),
        error: error.message
      });
    }
  });

  // Add metrics endpoint (for Prometheus scraping)
  server.get('/metrics', async (request, reply) => {
    try {
      const metrics = await import('./services/metrics');
      const metricsData = await metrics.MetricsCollector.getInstance().getPrometheusMetrics();

      return reply
        .header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
        .send(metricsData);
    } catch (error) {
      logger.error('Metrics endpoint failed', { error: error.message });
      throw new GenesisError('Metrics unavailable', 503);
    }
  });

  logger.info('Fastify server configured successfully');

  return server;
}
