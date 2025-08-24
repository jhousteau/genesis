/**
 * Configuration Module
 *
 * Provides configuration management with environment variable support,
 * validation, and GCP Secret Manager integration.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'yaml';
import Joi from 'joi';
import { config } from 'dotenv';
import { BaseConfig, EnvironmentConfig } from '../types';
import { Logger, getLogger } from '../logging';

export interface ConfigOptions {
  configFile?: string;
  secretsEnabled?: boolean;
  gcpProjectId?: string;
  environment?: string;
  validateSchema?: boolean;
}

/**
 * Configuration Manager class
 */
export class ConfigManager {
  private logger: Logger;
  private config: Record<string, any> = {};
  private secretManager?: any;
  private options: ConfigOptions;

  constructor(options: ConfigOptions = {}) {
    this.logger = getLogger();
    this.options = {
      validateSchema: true,
      secretsEnabled: false,
      ...options
    };

    // Load .env file
    config();

    this.initializeSecretManager();
  }

  /**
   * Initialize GCP Secret Manager if available
   */
  private async initializeSecretManager(): Promise<void> {
    if (!this.options.secretsEnabled) {
      return;
    }

    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { SecretManagerServiceClient } = require('@google-cloud/secret-manager');

      this.secretManager = new SecretManagerServiceClient({
        projectId: this.options.gcpProjectId || process.env.GCP_PROJECT
      });

      this.logger.info('Secret Manager initialized', {
        projectId: this.options.gcpProjectId || process.env.GCP_PROJECT
      });
    } catch (error) {
      this.logger.warn('Failed to initialize Secret Manager', {
        error: error.message,
        secretsEnabled: this.options.secretsEnabled
      });
    }
  }

  /**
   * Load configuration from multiple sources
   */
  async load(): Promise<Record<string, any>> {
    try {
      // Load from files
      await this.loadFromFiles();

      // Load from environment variables
      this.loadFromEnvironment();

      // Load from secrets manager
      await this.loadFromSecrets();

      // Validate configuration if schema is provided
      if (this.options.validateSchema) {
        this.validateConfiguration();
      }

      this.logger.info('Configuration loaded successfully', {
        sources: this.getConfigSources(),
        environment: this.config.environment || 'unknown'
      });

      return this.config;
    } catch (error) {
      this.logger.error('Failed to load configuration', error);
      throw error;
    }
  }

  /**
   * Load configuration from files
   */
  private async loadFromFiles(): Promise<void> {
    const configPaths = [
      this.options.configFile,
      'config.json',
      'config.yaml',
      'config.yml',
      path.join('config', 'default.json'),
      path.join('config', 'default.yaml'),
      path.join('.config', 'config.json'),
      path.join('.config', 'config.yaml')
    ].filter(Boolean);

    for (const configPath of configPaths) {
      if (fs.existsSync(configPath!)) {
        try {
          const content = fs.readFileSync(configPath!, 'utf-8');
          let fileConfig: Record<string, any>;

          if (configPath!.endsWith('.json')) {
            fileConfig = JSON.parse(content);
          } else if (configPath!.endsWith('.yaml') || configPath!.endsWith('.yml')) {
            fileConfig = yaml.parse(content);
          } else {
            continue;
          }

          this.config = { ...this.config, ...fileConfig };
          this.logger.debug('Loaded configuration from file', { file: configPath });
          break; // Use first found config file
        } catch (error) {
          this.logger.warn('Failed to load config file', {
            file: configPath,
            error: error.message
          });
        }
      }
    }
  }

  /**
   * Load configuration from environment variables
   */
  private loadFromEnvironment(): void {
    const envMapping: Record<string, string> = {
      // Base configuration
      ENVIRONMENT: 'environment',
      NODE_ENV: 'environment',
      DEBUG: 'debug',
      LOG_LEVEL: 'logLevel',
      SERVICE_NAME: 'serviceName',
      SERVICE_VERSION: 'serviceVersion',

      // GCP configuration
      GCP_PROJECT: 'gcpProject',
      GCP_REGION: 'gcpRegion',

      // Server configuration
      PORT: 'port',
      HOST: 'host',

      // Database configuration
      DATABASE_HOST: 'database.host',
      DATABASE_PORT: 'database.port',
      DATABASE_NAME: 'database.name',
      DATABASE_USER: 'database.username',
      DATABASE_PASSWORD: 'database.password',
      DATABASE_SSL: 'database.ssl',

      // Redis configuration
      REDIS_HOST: 'redis.host',
      REDIS_PORT: 'redis.port',
      REDIS_PASSWORD: 'redis.password',
      REDIS_DATABASE: 'redis.database',

      // Security configuration
      JWT_SECRET: 'security.jwtSecret',
      JWT_EXPIRATION: 'security.jwtExpiration',
      ENCRYPTION_KEY: 'security.encryptionKey'
    };

    for (const [envVar, configPath] of Object.entries(envMapping)) {
      const value = process.env[envVar];
      if (value !== undefined) {
        this.setNestedValue(this.config, configPath, this.parseValue(value));
      }
    }
  }

  /**
   * Load sensitive configuration from GCP Secret Manager
   */
  private async loadFromSecrets(): Promise<void> {
    if (!this.secretManager) {
      return;
    }

    const secretMappings: Record<string, string> = {
      'database-password': 'database.password',
      'jwt-secret': 'security.jwtSecret',
      'encryption-key': 'security.encryptionKey',
      'redis-password': 'redis.password',
      'api-key': 'api.key'
    };

    for (const [secretName, configPath] of Object.entries(secretMappings)) {
      try {
        const secretValue = await this.getSecret(secretName);
        if (secretValue) {
          this.setNestedValue(this.config, configPath, secretValue);
          this.logger.debug('Loaded secret from Secret Manager', { secret: secretName });
        }
      } catch (error) {
        this.logger.warn('Failed to load secret', {
          secret: secretName,
          error: error.message
        });
      }
    }
  }

  /**
   * Get secret from GCP Secret Manager
   */
  private async getSecret(name: string, version: string = 'latest'): Promise<string | null> {
    if (!this.secretManager) {
      return null;
    }

    try {
      const projectId = this.options.gcpProjectId || process.env.GCP_PROJECT;
      const secretName = `projects/${projectId}/secrets/${name}/versions/${version}`;

      const [response] = await this.secretManager.accessSecretVersion({
        name: secretName
      });

      return response.payload.data.toString();
    } catch (error) {
      this.logger.debug('Secret not found or inaccessible', {
        secret: name,
        error: error.message
      });
      return null;
    }
  }

  /**
   * Parse string value to appropriate type
   */
  private parseValue(value: string): any {
    // Boolean values
    if (value.toLowerCase() === 'true') return true;
    if (value.toLowerCase() === 'false') return false;

    // Numbers
    if (/^\d+$/.test(value)) return parseInt(value, 10);
    if (/^\d*\.\d+$/.test(value)) return parseFloat(value);

    // Arrays (comma-separated)
    if (value.includes(',')) {
      return value.split(',').map(v => v.trim());
    }

    return value;
  }

  /**
   * Set nested object value using dot notation
   */
  private setNestedValue(obj: Record<string, any>, path: string, value: any): void {
    const keys = path.split('.');
    let current = obj;

    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i];
      if (!(key in current) || typeof current[key] !== 'object') {
        current[key] = {};
      }
      current = current[key];
    }

    current[keys[keys.length - 1]] = value;
  }

  /**
   * Get nested object value using dot notation
   */
  private getNestedValue(obj: Record<string, any>, path: string): any {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  /**
   * Validate configuration against schema
   */
  private validateConfiguration(): void {
    const baseSchema = Joi.object({
      environment: Joi.string().valid('development', 'testing', 'staging', 'production').default('development'),
      debug: Joi.boolean().default(false),
      logLevel: Joi.string().valid('debug', 'info', 'warn', 'error', 'fatal').default('info'),
      serviceName: Joi.string().default('whitehorse-service'),
      serviceVersion: Joi.string().default('1.0.0'),
      gcpProject: Joi.string().optional(),
      gcpRegion: Joi.string().default('us-central1'),

      // Server configuration
      port: Joi.number().port().default(3000),
      host: Joi.string().default('0.0.0.0'),

      // Database configuration
      database: Joi.object({
        host: Joi.string().required(),
        port: Joi.number().port().default(5432),
        name: Joi.string().required(),
        username: Joi.string().required(),
        password: Joi.string().required(),
        ssl: Joi.boolean().default(false)
      }).optional(),

      // Redis configuration
      redis: Joi.object({
        host: Joi.string().default('localhost'),
        port: Joi.number().port().default(6379),
        password: Joi.string().optional(),
        database: Joi.number().default(0)
      }).optional(),

      // Security configuration
      security: Joi.object({
        jwtSecret: Joi.string().required(),
        jwtExpiration: Joi.string().default('1h'),
        encryptionKey: Joi.string().optional()
      }).optional()
    }).unknown(true);

    const { error, value } = baseSchema.validate(this.config);

    if (error) {
      throw new Error(`Configuration validation failed: ${error.message}`);
    }

    this.config = value;
  }

  /**
   * Get configuration value
   */
  get<T = any>(path: string, defaultValue?: T): T {
    const value = this.getNestedValue(this.config, path);
    return value !== undefined ? value : defaultValue;
  }

  /**
   * Set configuration value
   */
  set(path: string, value: any): void {
    this.setNestedValue(this.config, path, value);
  }

  /**
   * Check if configuration key exists
   */
  has(path: string): boolean {
    return this.getNestedValue(this.config, path) !== undefined;
  }

  /**
   * Get all configuration
   */
  getAll(): Record<string, any> {
    return { ...this.config };
  }

  /**
   * Get configuration sources that were loaded
   */
  private getConfigSources(): string[] {
    const sources = ['environment'];

    if (this.options.configFile || fs.existsSync('config.json') || fs.existsSync('config.yaml')) {
      sources.push('file');
    }

    if (this.secretManager) {
      sources.push('secrets');
    }

    return sources;
  }

  /**
   * Get database configuration
   */
  getDatabaseConfig(): any {
    return this.get('database');
  }

  /**
   * Get Redis configuration
   */
  getRedisConfig(): any {
    return this.get('redis');
  }

  /**
   * Get security configuration
   */
  getSecurityConfig(): any {
    return this.get('security');
  }

  /**
   * Check if running in development mode
   */
  isDevelopment(): boolean {
    return this.get('environment') === 'development';
  }

  /**
   * Check if running in production mode
   */
  isProduction(): boolean {
    return this.get('environment') === 'production';
  }

  /**
   * Check if debug mode is enabled
   */
  isDebug(): boolean {
    return this.get('debug', false);
  }
}

// Global configuration manager
let globalConfig: ConfigManager;

/**
 * Load configuration with options
 */
export async function loadConfig(options?: ConfigOptions): Promise<Record<string, any>> {
  globalConfig = new ConfigManager(options);
  return await globalConfig.load();
}

/**
 * Get global configuration manager
 */
export function getConfig(): ConfigManager {
  if (!globalConfig) {
    globalConfig = new ConfigManager();
  }
  return globalConfig;
}

/**
 * Configuration decorator for dependency injection
 */
export function Config(path?: string) {
  return function (target: any, propertyKey: string) {
    const configPath = path || propertyKey;

    Object.defineProperty(target, propertyKey, {
      get() {
        return getConfig().get(configPath);
      },
      enumerable: true,
      configurable: true
    });
  };
}

/**
 * Environment-aware configuration class
 */
export class EnvironmentAwareConfig {
  private config: ConfigManager;

  constructor(config?: ConfigManager) {
    this.config = config || getConfig();
  }

  /**
   * Get environment-specific configuration
   */
  getForEnvironment<T = any>(baseKey: string, environment?: string): T {
    const env = environment || this.config.get('environment', 'development');
    const envKey = `${baseKey}.${env}`;

    // Try environment-specific first, fall back to base
    return this.config.get(envKey) || this.config.get(baseKey);
  }

  /**
   * Get feature flag value
   */
  getFeatureFlag(flag: string, defaultValue: boolean = false): boolean {
    return this.config.get(`features.${flag}`, defaultValue);
  }

  /**
   * Get rate limiting configuration
   */
  getRateLimitConfig(endpoint?: string): any {
    if (endpoint) {
      return this.config.get(`rateLimit.endpoints.${endpoint}`) ||
             this.config.get('rateLimit.default');
    }
    return this.config.get('rateLimit.default');
  }
}

export default ConfigManager;
