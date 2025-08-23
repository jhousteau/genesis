/**
 * Genesis Authentication Middleware
 *
 * JWT-based authentication with Firebase Auth integration
 * following Genesis security patterns.
 */

import { FastifyRequest, FastifyReply } from 'fastify';
import jwt from 'jsonwebtoken';
import { Config } from '../config';
import { Logger } from '../utils/logger';
import { AuthenticationError, AuthorizationError } from '../types/errors';

const logger = Logger.getInstance('auth-middleware');

declare module 'fastify' {
  interface FastifyRequest {
    user?: {
      id: string;
      email: string;
      role: string;
      permissions: string[];
    };
  }
}

/**
 * Authentication middleware
 */
export async function authMiddleware(
  request: FastifyRequest,
  reply: FastifyReply
): Promise<void> {
  const config = Config.getInstance();

  // Skip auth for certain routes
  const skipAuthRoutes = [
    '/health',
    '/metrics',
    '/docs',
    '/ready'
  ];

  if (skipAuthRoutes.some(route => request.url.startsWith(route))) {
    return;
  }

  // Skip auth for OPTIONS requests
  if (request.method === 'OPTIONS') {
    return;
  }

  try {
    const authHeader = request.headers.authorization;

    if (!authHeader) {
      throw new AuthenticationError('Authorization header required');
    }

    const parts = authHeader.split(' ');
    if (parts.length !== 2 || parts[0] !== 'Bearer') {
      throw new AuthenticationError('Invalid authorization header format');
    }

    const token = parts[1];

    // Verify JWT token
    const decoded = jwt.verify(token, config.jwt.secret) as any;

    // Extract user information
    request.user = {
      id: decoded.sub || decoded.user_id,
      email: decoded.email,
      role: decoded.role || 'user',
      permissions: decoded.permissions || []
    };

    logger.debug('User authenticated', {
      userId: request.user.id,
      email: request.user.email,
      role: request.user.role,
      requestId: request.id
    });

  } catch (error) {
    logger.warn('Authentication failed', {
      error: error.message,
      url: request.url,
      method: request.method,
      requestId: request.id
    });

    if (error.name === 'JsonWebTokenError') {
      throw new AuthenticationError('Invalid token');
    } else if (error.name === 'TokenExpiredError') {
      throw new AuthenticationError('Token expired');
    } else if (error instanceof AuthenticationError) {
      throw error;
    } else {
      throw new AuthenticationError('Authentication failed');
    }
  }
}

/**
 * Authorization middleware factory
 */
export function requireRole(requiredRole: string) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    if (!request.user) {
      throw new AuthenticationError('Authentication required');
    }

    if (request.user.role !== requiredRole && request.user.role !== 'admin') {
      logger.warn('Authorization failed', {
        userId: request.user.id,
        userRole: request.user.role,
        requiredRole,
        url: request.url,
        requestId: request.id
      });

      throw new AuthorizationError(`Role '${requiredRole}' required`);
    }

    logger.debug('Authorization successful', {
      userId: request.user.id,
      userRole: request.user.role,
      requiredRole,
      requestId: request.id
    });
  };
}

/**
 * Permission-based authorization
 */
export function requirePermission(permission: string) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    if (!request.user) {
      throw new AuthenticationError('Authentication required');
    }

    if (!request.user.permissions.includes(permission) && request.user.role !== 'admin') {
      logger.warn('Permission denied', {
        userId: request.user.id,
        userPermissions: request.user.permissions,
        requiredPermission: permission,
        url: request.url,
        requestId: request.id
      });

      throw new AuthorizationError(`Permission '${permission}' required`);
    }

    logger.debug('Permission granted', {
      userId: request.user.id,
      permission,
      requestId: request.id
    });
  };
}
