/**
 * Genesis TypeScript Service - Main Entry Point
 *
 * This service follows Genesis patterns for cloud-native TypeScript applications
 * with comprehensive GCP integration, monitoring, and security features.
 */

import 'dotenv/config';
import { createServer } from './server';
import { Config } from './config';
import { Logger } from './utils/logger';
import { HealthChecker } from './services/health';
import { MetricsCollector } from './services/metrics';
import { gracefulShutdown } from './utils/shutdown';

const logger = Logger.getInstance('main');

async function main(): Promise<void> {
  try {
    logger.info('Starting Genesis TypeScript Service');

    // Load and validate configuration
    const config = Config.getInstance();
    logger.info('Configuration loaded', {
      environment: config.environment,
      port: config.port,
      projectId: config.gcp.projectId
    });

    // Initialize health checker
    const healthChecker = HealthChecker.getInstance();
    await healthChecker.initialize();

    // Initialize metrics collector
    const metrics = MetricsCollector.getInstance();
    await metrics.initialize();

    // Create and start server
    const server = await createServer();

    const address = await server.listen({
      host: '0.0.0.0',
      port: config.port
    });

    logger.info(`Server listening at ${address}`);

    // Setup graceful shutdown
    gracefulShutdown(server, logger);

    // Log successful startup
    metrics.recordStartup();
    logger.info('Genesis TypeScript Service started successfully');

  } catch (error) {
    logger.error('Failed to start service', { error: error.message, stack: error.stack });
    process.exit(1);
  }
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled promise rejection', {
    reason: reason?.toString(),
    promise: promise.toString()
  });
  process.exit(1);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception', {
    error: error.message,
    stack: error.stack
  });
  process.exit(1);
});

// Start the application
main().catch((error) => {
  console.error('Fatal error during startup:', error);
  process.exit(1);
});
