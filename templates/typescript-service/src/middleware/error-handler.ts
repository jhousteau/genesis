/**
 * Genesis Error Handler Middleware
 *
 * Comprehensive error handling with structured logging,
 * security considerations, and Genesis error patterns.
 */

import { FastifyRequest, FastifyReply, FastifyError } from 'fastify';
import { Logger } from '../utils/logger';
import { GenesisError, isGenesisError, ErrorFactory } from '../types/errors';

const logger = Logger.getInstance('error-handler');

/**
 * Global error handler for Fastify
 */
export function errorHandler(
  error: FastifyError,
  request: FastifyRequest,
  reply: FastifyReply
): void {
  const requestId = request.id;
  const method = request.method;
  const url = request.url;

  // Convert to Genesis error if needed
  let genesisError: GenesisError;

  if (isGenesisError(error)) {
    genesisError = error;
  } else if (error.statusCode) {
    genesisError = ErrorFactory.fromHttpStatus(
      error.statusCode,
      error.message,
      undefined,
      { requestId, method, url }
    );
  } else {
    genesisError = ErrorFactory.fromException(error, { requestId, method, url });
  }

  // Log error with appropriate level
  const logLevel = genesisError.statusCode >= 500 ? 'error' : 'warn';

  logger[logLevel]('Request error handled', {
    requestId,
    method,
    url,
    error: genesisError.toJSON(),
    userAgent: request.headers['user-agent'],
    ip: request.ip
  });

  // Send error response
  const responseBody = genesisError.toApiResponse();

  // Add additional context in development
  if (process.env.NODE_ENV === 'development') {
    responseBody.error.stack = genesisError.stack;
  }

  reply
    .status(genesisError.statusCode)
    .send(responseBody);
}
