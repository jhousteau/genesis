/**
 * Genesis Graceful Shutdown Utilities
 *
 * Handles graceful shutdown of services with proper cleanup,
 * connection draining, and resource management.
 */

import { FastifyInstance } from 'fastify';
import { Logger } from './logger';

const logger = Logger.getInstance('shutdown');

export interface ShutdownHandler {
  name: string;
  handler: () => Promise<void>;
  timeout?: number;
}

class ShutdownManager {
  private handlers: ShutdownHandler[] = [];
  private isShuttingDown = false;
  private shutdownTimeout = 30000; // 30 seconds default

  /**
   * Register a shutdown handler
   */
  public register(handler: ShutdownHandler): void {
    this.handlers.push(handler);
    logger.debug('Shutdown handler registered', { name: handler.name });
  }

  /**
   * Execute graceful shutdown
   */
  public async shutdown(signal: string): Promise<void> {
    if (this.isShuttingDown) {
      logger.warn('Shutdown already in progress, ignoring signal', { signal });
      return;
    }

    this.isShuttingDown = true;
    logger.info('Starting graceful shutdown', { signal });

    const shutdownPromises = this.handlers.map(async (handler) => {
      const timeout = handler.timeout || 5000;

      try {
        logger.debug('Executing shutdown handler', { name: handler.name });

        await Promise.race([
          handler.handler(),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error(`Timeout after ${timeout}ms`)), timeout)
          )
        ]);

        logger.debug('Shutdown handler completed', { name: handler.name });
      } catch (error) {
        logger.error('Shutdown handler failed', {
          name: handler.name,
          error: error.message
        });
      }
    });

    try {
      await Promise.race([
        Promise.all(shutdownPromises),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Shutdown timeout')), this.shutdownTimeout)
        )
      ]);

      logger.info('Graceful shutdown completed');
    } catch (error) {
      logger.error('Shutdown process timed out or failed', { error: error.message });
    }

    process.exit(0);
  }

  /**
   * Set shutdown timeout
   */
  public setShutdownTimeout(timeout: number): void {
    this.shutdownTimeout = timeout;
  }
}

const shutdownManager = new ShutdownManager();

/**
 * Setup graceful shutdown for Fastify server
 */
export function gracefulShutdown(server: FastifyInstance, appLogger?: Logger): void {
  const log = appLogger || logger;

  // Register server shutdown
  shutdownManager.register({
    name: 'fastify-server',
    handler: async () => {
      log.info('Closing Fastify server');
      await server.close();
      log.info('Fastify server closed');
    },
    timeout: 10000
  });

  // Setup signal handlers
  const signals: NodeJS.Signals[] = ['SIGTERM', 'SIGINT'];

  signals.forEach(signal => {
    process.on(signal, async () => {
      log.info(`Received ${signal}, initiating graceful shutdown`);
      await shutdownManager.shutdown(signal);
    });
  });

  // Handle uncaught exceptions
  process.on('uncaughtException', (error) => {
    log.error('Uncaught exception, shutting down', {
      error: error.message,
      stack: error.stack
    });
    shutdownManager.shutdown('uncaughtException');
  });

  // Handle unhandled rejections
  process.on('unhandledRejection', (reason, promise) => {
    log.error('Unhandled promise rejection, shutting down', {
      reason: reason?.toString(),
      promise: promise.toString()
    });
    shutdownManager.shutdown('unhandledRejection');
  });

  log.info('Graceful shutdown handlers registered');
}

/**
 * Register custom shutdown handler
 */
export function registerShutdownHandler(handler: ShutdownHandler): void {
  shutdownManager.register(handler);
}

/**
 * Set global shutdown timeout
 */
export function setShutdownTimeout(timeout: number): void {
  shutdownManager.setShutdownTimeout(timeout);
}
