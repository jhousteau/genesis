/**
 * Lightweight configuration management with YAML and environment variables
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { ResourceError, ValidationError, handleError } from './errors';

export interface ConfigLoader {
  loadFile(filePath: string): Record<string, any>;
  loadEnv(config: Record<string, any>): Record<string, any>;
  load(filePath?: string, defaults?: Record<string, any>): Record<string, any>;
  get(key: string, defaultValue?: any): any;
}

export class GenesisConfigLoader implements ConfigLoader {
  private config: Record<string, any> = {};

  constructor(private envPrefix: string = '') {
    this.envPrefix = envPrefix.toUpperCase();
  }

  loadFile(filePath: string): Record<string, any> {
    if (!fs.existsSync(filePath)) {
      return {};
    }

    try {
      const fileContent = fs.readFileSync(filePath, 'utf8');
      const content = yaml.load(fileContent);
      
      if (content === null || content === undefined) {
        return {};
      }
      
      if (typeof content !== 'object' || Array.isArray(content)) {
        throw new ValidationError(
          `Configuration file must contain a YAML dictionary, got ${typeof content}`
        );
      }

      return content as Record<string, any>;
    } catch (error: any) {
      if (error instanceof ValidationError) {
        throw error;
      }
      
      if (error.name === 'YAMLException') {
        throw new ValidationError(`Invalid YAML in configuration file ${filePath}: ${error.message}`);
      }

      const handledError = handleError(error);
      throw new ResourceError(
        `Failed to load configuration file ${filePath}: ${handledError.message}`,
        'config_file'
      );
    }
  }

  loadEnv(config: Record<string, any>): Record<string, any> {
    const result = { ...config };

    for (const [key, value] of Object.entries(process.env)) {
      if (key.startsWith(this.envPrefix)) {
        // Remove prefix and convert to lowercase
        const configKey = key.slice(this.envPrefix.length).toLowerCase();

        // Convert common string values to appropriate types
        if (value === 'true' || value === 'false') {
          result[configKey] = value === 'true';
        } else if (value && /^\\d+$/.test(value)) {
          result[configKey] = parseInt(value, 10);
        } else if (value && /^\\d*\\.\\d+$/.test(value)) {
          result[configKey] = parseFloat(value);
        } else {
          result[configKey] = value;
        }
      }
    }

    return result;
  }

  load(filePath?: string, defaults?: Record<string, any>): Record<string, any> {
    let config = defaults || {};

    // Load from file if provided
    if (filePath) {
      const fileConfig = this.loadFile(filePath);
      config = { ...config, ...fileConfig };
    }

    // Apply environment overrides
    config = this.loadEnv(config);

    this.config = config;
    return config;
  }

  get(key: string, defaultValue: any = undefined): any {
    // Support dot notation for nested keys
    const keys = key.split('.');
    let current = this.config;

    for (const k of keys) {
      if (current && typeof current === 'object' && k in current) {
        current = current[k];
      } else {
        return defaultValue;
      }
    }

    return current;
  }

  // Dictionary-style access
  getItem(key: string): any {
    return this.config[key];
  }

  // Check if key exists
  has(key: string): boolean {
    return key in this.config;
  }

  // Get all config as readonly
  getAll(): Readonly<Record<string, any>> {
    return { ...this.config };
  }

  // Update config at runtime (useful for testing)
  set(key: string, value: any): void {
    const keys = key.split('.');
    let current = this.config;

    for (let i = 0; i < keys.length - 1; i++) {
      const k = keys[i];
      if (!(k in current) || typeof current[k] !== 'object') {
        current[k] = {};
      }
      current = current[k];
    }

    current[keys[keys.length - 1]] = value;
  }
}

/**
 * Simple function interface for loading configuration
 */
export function loadConfig(
  filePath?: string,
  envPrefix: string = '',
  defaults?: Record<string, any>
): Record<string, any> {
  const loader = new GenesisConfigLoader(envPrefix);
  return loader.load(filePath, defaults);
}

/**
 * Create a config loader instance
 */
export function createConfigLoader(envPrefix: string = ''): ConfigLoader {
  return new GenesisConfigLoader(envPrefix);
}

/**
 * Type-safe configuration class with schema validation
 */
export abstract class TypedConfig<T = Record<string, any>> {
  protected config: T;

  constructor(
    filePath?: string,
    envPrefix: string = '',
    defaults?: Partial<T>
  ) {
    const loader = new GenesisConfigLoader(envPrefix);
    const rawConfig = loader.load(filePath, defaults as Record<string, any>);
    this.config = this.validate(rawConfig);
  }

  /**
   * Validate and transform raw config into typed config
   * Override this method to provide type-safe validation
   */
  protected abstract validate(rawConfig: Record<string, any>): T;

  /**
   * Get configuration value by key
   */
  get<K extends keyof T>(key: K): T[K] {
    return this.config[key];
  }

  /**
   * Get all configuration
   */
  getAll(): Readonly<T> {
    return { ...this.config };
  }
}

/**
 * Predefined configuration patterns
 */
export const ConfigPresets = {
  /**
   * Standard application configuration
   */
  application: (envPrefix: string = 'APP') => ({
    name: 'app',
    version: '1.0.0',
    environment: 'development',
    port: 3000,
    logLevel: 'info',
    database: {
      host: 'localhost',
      port: 5432,
      name: 'app_db',
    },
  }),

  /**
   * Service configuration
   */
  service: (envPrefix: string = 'SERVICE') => ({
    name: 'service',
    version: '1.0.0',
    environment: 'development',
    port: 8080,
    logLevel: 'info',
    health: {
      enabled: true,
      endpoint: '/health',
    },
    metrics: {
      enabled: true,
      endpoint: '/metrics',
    },
  }),

  /**
   * Database configuration
   */
  database: (envPrefix: string = 'DB') => ({
    host: 'localhost',
    port: 5432,
    name: 'postgres',
    username: 'postgres',
    password: 'postgres',
    ssl: false,
    poolSize: 10,
    timeout: 30000,
  }),
} as const;