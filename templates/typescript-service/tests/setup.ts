/**
 * Genesis Test Setup
 *
 * Global test configuration and utilities for comprehensive testing
 * following Genesis patterns and CRAFT methodology.
 */

import 'dotenv/config';
import { Logger } from '../src/utils/logger';

// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.GENESIS_ENVIRONMENT = 'test';
process.env.LOG_LEVEL = 'error';
process.env.GENESIS_TEST_MODE = 'true';

// Mock GCP services for testing
jest.mock('@google-cloud/secret-manager');
jest.mock('@google-cloud/logging');
jest.mock('@google-cloud/pubsub');
jest.mock('@google-cloud/firestore');
jest.mock('@google-cloud/storage');
jest.mock('@google-cloud/monitoring');

// Global test timeout
jest.setTimeout(30000);

// Global test utilities
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeValidUUID(): R;
      toBeValidEmail(): R;
      toBeValidDate(): R;
      toHaveValidationError(field: string): R;
      toHaveStatusCode(code: number): R;
    }
  }

  var testUtils: {
    mockUser: (overrides?: any) => any;
    mockRequest: (overrides?: any) => any;
    mockResponse: () => any;
    createTestServer: () => Promise<any>;
    generateTestData: (type: string, overrides?: any) => any;
  };
}

// Test utilities
global.testUtils = {
  // Mock user for testing
  mockUser: (overrides = {}) => ({
    id: 'test-user-123',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    createdAt: new Date(),
    updatedAt: new Date(),
    ...overrides
  }),

  // Mock HTTP request
  mockRequest: (overrides = {}) => ({
    method: 'GET',
    url: '/test',
    headers: {
      'content-type': 'application/json',
      'user-agent': 'test-agent',
      ...overrides.headers
    },
    body: {},
    query: {},
    params: {},
    user: null,
    ...overrides
  }),

  // Mock HTTP response
  mockResponse: () => {
    const res: any = {};
    res.status = jest.fn().mockReturnValue(res);
    res.json = jest.fn().mockReturnValue(res);
    res.send = jest.fn().mockReturnValue(res);
    res.header = jest.fn().mockReturnValue(res);
    res.cookie = jest.fn().mockReturnValue(res);
    res.redirect = jest.fn().mockReturnValue(res);
    return res;
  },

  // Create test server instance
  createTestServer: async () => {
    const { createServer } = await import('../src/server');
    return createServer();
  },

  // Generate test data
  generateTestData: (type: string, overrides = {}) => {
    const generators: Record<string, () => any> = {
      user: () => global.testUtils.mockUser(overrides),

      product: () => ({
        id: 'test-product-123',
        name: 'Test Product',
        description: 'A test product',
        price: 99.99,
        category: 'test',
        inStock: true,
        createdAt: new Date(),
        ...overrides
      }),

      order: () => ({
        id: 'test-order-123',
        userId: 'test-user-123',
        status: 'pending',
        items: [
          {
            productId: 'test-product-123',
            quantity: 1,
            price: 99.99
          }
        ],
        total: 99.99,
        createdAt: new Date(),
        ...overrides
      }),

      error: () => ({
        code: 'TEST_ERROR',
        message: 'Test error message',
        statusCode: 400,
        ...overrides
      })
    };

    const generator = generators[type];
    if (!generator) {
      throw new Error(`Unknown test data type: ${type}`);
    }

    return generator();
  }
};

// Global test hooks
beforeAll(async () => {
  // Initialize test logger
  const logger = Logger.getInstance('test');
  logger.info('Starting test suite', {
    environment: process.env.NODE_ENV,
    timestamp: new Date().toISOString()
  });
});

afterAll(async () => {
  // Cleanup
  const logger = Logger.getInstance('test');
  logger.info('Test suite completed', {
    timestamp: new Date().toISOString()
  });

  // Close logger
  await logger.close();
});

beforeEach(() => {
  // Clear all mocks before each test
  jest.clearAllMocks();

  // Reset environment variables
  process.env.GENESIS_REQUEST_ID = undefined;
  process.env.GENESIS_USER_ID = undefined;
});

afterEach(() => {
  // Cleanup after each test
  jest.restoreAllMocks();
});

// Console error handling
const originalError = console.error;
console.error = (...args: any[]) => {
  // Suppress expected errors in tests
  const message = args[0]?.toString() || '';
  const suppressedPatterns = [
    'Warning: React.createFactory',
    'Warning: componentWillMount',
    'Warning: componentWillReceiveProps'
  ];

  if (!suppressedPatterns.some(pattern => message.includes(pattern))) {
    originalError(...args);
  }
};

// Unhandled promise rejection handling
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // Don't exit in tests
});

// Uncaught exception handling
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  // Don't exit in tests
});

export {}; // Make this a module
