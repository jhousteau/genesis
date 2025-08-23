/**
 * Genesis Configuration Management
 *
 * Centralized configuration with environment-specific settings,
 * secret management, and validation following Genesis patterns.
 */

import Joi from 'joi';
import { SecretManagerServiceClient } from '@google-cloud/secret-manager';

export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
  connectionTimeout: number;
  maxConnections: number;
}

export interface RedisConfig {
  enabled: boolean;
  host: string;
  port: number;
  password?: string;
  db: number;
  keyPrefix: string;
}

export interface GCPConfig {
  projectId: string;
  region: string;
  serviceAccountEmail: string;
  keyFilename?: string;
}

export interface CORSConfig {
  origins: string[];
  credentials: boolean;
}

export interface RateLimitingConfig {
  max: number;
  timeWindow: number;
}

export interface JWTConfig {
  secret: string;
  expiresIn: string;
  algorithm: string;
}

export interface ServiceConfig {
  port: number;
  environment: string;
  logLevel: string;
  serviceName: string;
  version: string;
  gcp: GCPConfig;
  database: DatabaseConfig;
  redis: RedisConfig;
  cors: CORSConfig;
  rateLimiting: RateLimitingConfig;
  jwt: JWTConfig;
}

// Configuration schema validation
const configSchema = Joi.object<ServiceConfig>({
  port: Joi.number().port().default(8080),
  environment: Joi.string().valid('development', 'staging', 'production').required(),
  logLevel: Joi.string().valid('debug', 'info', 'warn', 'error').default('info'),
  serviceName: Joi.string().required(),
  version: Joi.string().default('1.0.0'),

  gcp: Joi.object({
    projectId: Joi.string().required(),
    region: Joi.string().default('us-central1'),
    serviceAccountEmail: Joi.string().email(),
    keyFilename: Joi.string().optional()
  }).required(),

  database: Joi.object({
    host: Joi.string().required(),
    port: Joi.number().port().default(5432),
    database: Joi.string().required(),
    username: Joi.string().required(),
    password: Joi.string().required(),
    ssl: Joi.boolean().default(true),
    connectionTimeout: Joi.number().default(10000),
    maxConnections: Joi.number().default(20)
  }).required(),

  redis: Joi.object({
    enabled: Joi.boolean().default(false),
    host: Joi.string().when('enabled', { is: true, then: Joi.required() }),
    port: Joi.number().port().default(6379),
    password: Joi.string().optional(),
    db: Joi.number().default(0),
    keyPrefix: Joi.string().default('genesis:')
  }),

  cors: Joi.object({
    origins: Joi.array().items(Joi.string()).default(['http://localhost:3000']),
    credentials: Joi.boolean().default(true)
  }),

  rateLimiting: Joi.object({
    max: Joi.number().default(100),
    timeWindow: Joi.number().default(60000) // 1 minute
  }),

  jwt: Joi.object({
    secret: Joi.string().min(32).required(),
    expiresIn: Joi.string().default('24h'),
    algorithm: Joi.string().default('HS256')
  }).required()
});

export class Config {
  private static instance: Config;
  private config: ServiceConfig;
  private secretManager: SecretManagerServiceClient;

  private constructor() {
    this.secretManager = new SecretManagerServiceClient();
  }

  public static getInstance(): Config {
    if (!Config.instance) {
      Config.instance = new Config();
    }
    return Config.instance;
  }

  public async initialize(): Promise<void> {
    await this.loadConfiguration();
  }

  private async loadConfiguration(): Promise<void> {
    const rawConfig = {
      port: parseInt(process.env.PORT || '8080'),
      environment: process.env.NODE_ENV || 'development',
      logLevel: process.env.LOG_LEVEL || 'info',
      serviceName: process.env.SERVICE_NAME || '{{PROJECT_NAME}}',
      version: process.env.npm_package_version || '1.0.0',

      gcp: {
        projectId: process.env.GOOGLE_CLOUD_PROJECT || process.env.GCP_PROJECT_ID || '',
        region: process.env.GOOGLE_CLOUD_REGION || process.env.GCP_REGION || 'us-central1',
        serviceAccountEmail: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL || '',
        keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS
      },

      database: {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || '{{PROJECT_NAME}}',
        username: process.env.DB_USERNAME || 'postgres',
        password: await this.getSecret('DB_PASSWORD') || process.env.DB_PASSWORD || '',
        ssl: process.env.DB_SSL === 'true',
        connectionTimeout: parseInt(process.env.DB_CONNECTION_TIMEOUT || '10000'),
        maxConnections: parseInt(process.env.DB_MAX_CONNECTIONS || '20')
      },

      redis: {
        enabled: process.env.REDIS_ENABLED === 'true',
        host: process.env.REDIS_HOST || 'localhost',
        port: parseInt(process.env.REDIS_PORT || '6379'),
        password: await this.getSecret('REDIS_PASSWORD') || process.env.REDIS_PASSWORD,
        db: parseInt(process.env.REDIS_DB || '0'),
        keyPrefix: process.env.REDIS_KEY_PREFIX || 'genesis:'
      },

      cors: {
        origins: process.env.CORS_ORIGINS?.split(',') || ['http://localhost:3000'],
        credentials: process.env.CORS_CREDENTIALS !== 'false'
      },

      rateLimiting: {
        max: parseInt(process.env.RATE_LIMIT_MAX || '100'),
        timeWindow: parseInt(process.env.RATE_LIMIT_WINDOW || '60000')
      },

      jwt: {
        secret: await this.getSecret('JWT_SECRET') || process.env.JWT_SECRET || this.generateSecretKey(),
        expiresIn: process.env.JWT_EXPIRES_IN || '24h',
        algorithm: process.env.JWT_ALGORITHM || 'HS256'
      }
    };

    // Validate configuration
    const { error, value } = configSchema.validate(rawConfig, {
      allowUnknown: false,
      stripUnknown: true
    });

    if (error) {
      throw new Error(`Configuration validation failed: ${error.message}`);
    }

    this.config = value;

    // Log configuration (excluding sensitive data)
    const sanitizedConfig = this.sanitizeConfig(this.config);
    console.log('Configuration loaded:', JSON.stringify(sanitizedConfig, null, 2));
  }

  private async getSecret(secretName: string): Promise<string | undefined> {
    try {
      if (!this.config?.gcp?.projectId && !process.env.GOOGLE_CLOUD_PROJECT) {
        return undefined;
      }

      const projectId = this.config?.gcp?.projectId || process.env.GOOGLE_CLOUD_PROJECT;
      const name = `projects/${projectId}/secrets/${secretName}/versions/latest`;

      const [version] = await this.secretManager.accessSecretVersion({ name });
      return version.payload?.data?.toString();
    } catch (error) {
      console.warn(`Failed to retrieve secret ${secretName}:`, error.message);
      return undefined;
    }
  }

  private generateSecretKey(): string {
    const crypto = require('crypto');
    return crypto.randomBytes(32).toString('hex');
  }

  private sanitizeConfig(config: ServiceConfig): Partial<ServiceConfig> {
    return {
      ...config,
      database: {
        ...config.database,
        password: '[REDACTED]'
      },
      redis: {
        ...config.redis,
        password: '[REDACTED]'
      },
      jwt: {
        ...config.jwt,
        secret: '[REDACTED]'
      }
    };
  }

  // Getters for configuration values
  public get port(): number { return this.config.port; }
  public get environment(): string { return this.config.environment; }
  public get logLevel(): string { return this.config.logLevel; }
  public get serviceName(): string { return this.config.serviceName; }
  public get version(): string { return this.config.version; }
  public get gcp(): GCPConfig { return this.config.gcp; }
  public get database(): DatabaseConfig { return this.config.database; }
  public get redis(): RedisConfig { return this.config.redis; }
  public get cors(): CORSConfig { return this.config.cors; }
  public get rateLimiting(): RateLimitingConfig { return this.config.rateLimiting; }
  public get jwt(): JWTConfig { return this.config.jwt; }

  public getFullConfig(): ServiceConfig {
    return { ...this.config };
  }
}
