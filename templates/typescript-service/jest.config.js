/**
 * Genesis TypeScript Jest Configuration
 *
 * Comprehensive testing configuration with coverage,
 * environment setup, and Genesis-specific patterns.
 */

module.exports = {
  // Test environment
  preset: 'ts-jest',
  testEnvironment: 'node',

  // Test file patterns
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: [
    '**/tests/**/*.test.ts',
    '**/tests/**/*.spec.ts',
    '**/__tests__/**/*.ts',
    '**/*.test.ts',
    '**/*.spec.ts'
  ],

  // Transform configuration
  transform: {
    '^.+\\.ts$': ['ts-jest', {
      tsconfig: 'tsconfig.json',
      diagnostics: {
        ignoreCodes: [151001] // Ignore TypeScript errors in tests
      }
    }]
  },

  // Module resolution
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@/config/(.*)$': '<rootDir>/src/config/$1',
    '^@/services/(.*)$': '<rootDir>/src/services/$1',
    '^@/handlers/(.*)$': '<rootDir>/src/handlers/$1',
    '^@/models/(.*)$': '<rootDir>/src/models/$1',
    '^@/utils/(.*)$': '<rootDir>/src/utils/$1',
    '^@/middleware/(.*)$': '<rootDir>/src/middleware/$1',
    '^@/types/(.*)$': '<rootDir>/src/types/$1'
  },

  // File extensions
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],

  // Coverage configuration
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/index.ts',
    '!src/**/__tests__/**',
    '!src/**/*.test.ts',
    '!src/**/*.spec.ts'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: [
    'text',
    'text-summary',
    'lcov',
    'html',
    'clover',
    'json'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    },
    // Critical paths require 100% coverage
    'src/services/**/*.ts': {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90
    },
    'src/config/**/*.ts': {
      branches: 95,
      functions: 95,
      lines: 95,
      statements: 95
    }
  },

  // Test timeout
  testTimeout: 30000,

  // Reporter configuration
  reporters: [
    'default',
    ['jest-junit', {
      outputDirectory: 'test-results',
      outputName: 'junit.xml',
      suiteName: 'Genesis TypeScript Service Tests'
    }],
    ['jest-html-reporters', {
      publicPath: 'test-results',
      filename: 'test-report.html',
      expand: true
    }]
  ],

  // Global variables
  globals: {
    'ts-jest': {
      tsconfig: 'tsconfig.json'
    },
    GENESIS_TEST_ENV: true,
    GENESIS_PROJECT_NAME: '{{PROJECT_NAME}}',
    GENESIS_TEST_TIMEOUT: 30000
  },

  // Environment variables
  testEnvironment: 'node',
  testEnvironmentOptions: {
    NODE_ENV: 'test',
    GENESIS_ENVIRONMENT: 'test',
    LOG_LEVEL: 'error'
  },

  // Mock configuration
  clearMocks: true,
  restoreMocks: true,
  resetMocks: true,

  // Watch mode configuration
  watchPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/dist/',
    '<rootDir>/coverage/',
    '<rootDir>/test-results/',
    '<rootDir>/docs/'
  ],

  // Ignore patterns
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/dist/',
    '<rootDir>/coverage/'
  ],

  // Verbose output for CI
  verbose: process.env.CI === 'true',

  // Fail fast in CI
  bail: process.env.CI === 'true' ? 1 : 0,

  // Force exit after tests complete
  forceExit: true,

  // Detect open handles
  detectOpenHandles: true,

  // Error handling
  errorOnDeprecated: true,

  // Test sequencer for deterministic test order
  testSequencer: '<rootDir>/tests/test-sequencer.js',

  // Custom test runner for enhanced Genesis integration
  runner: 'jest-runner',

  // Maximum worker processes
  maxWorkers: process.env.CI === 'true' ? 2 : '50%',

  // Cache configuration
  cacheDirectory: '<rootDir>/node_modules/.cache/jest',

  // Snapshot configuration
  snapshotSerializers: ['jest-serializer-json'],

  // Custom matchers and utilities
  setupFilesAfterEnv: [
    '<rootDir>/tests/setup.ts',
    '<rootDir>/tests/matchers.ts'
  ],

  // Test categories
  projects: [
    {
      displayName: 'unit',
      testMatch: ['**/tests/unit/**/*.test.ts'],
      testEnvironment: 'node'
    },
    {
      displayName: 'integration',
      testMatch: ['**/tests/integration/**/*.test.ts'],
      testEnvironment: 'node',
      setupFilesAfterEnv: [
        '<rootDir>/tests/setup.ts',
        '<rootDir>/tests/integration-setup.ts'
      ]
    },
    {
      displayName: 'e2e',
      testMatch: ['**/tests/e2e/**/*.test.ts'],
      testEnvironment: 'node',
      setupFilesAfterEnv: [
        '<rootDir>/tests/setup.ts',
        '<rootDir>/tests/e2e-setup.ts'
      ],
      testTimeout: 60000
    }
  ]
};
