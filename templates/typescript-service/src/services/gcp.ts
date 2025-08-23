/**
 * Genesis GCP Integration Service
 *
 * Comprehensive GCP services integration following CRAFT methodology
 * with authentication, authorization, and error handling.
 */

import { SecretManagerServiceClient } from '@google-cloud/secret-manager';
import { Logging } from '@google-cloud/logging';
import { PubSub } from '@google-cloud/pubsub';
import { Firestore } from '@google-cloud/firestore';
import { Storage } from '@google-cloud/storage';
import { Monitoring } from '@google-cloud/monitoring';

import { Config } from '../config';
import { Logger } from '../utils/logger';
import { GenesisError, ExternalServiceError } from '../types/errors';
import { retry } from '../utils/retry';

export interface GCPServiceOptions {
  projectId?: string;
  keyFilename?: string;
  credentials?: object;
}

/**
 * GCP Secret Manager Integration
 */
export class GCPSecretManager {
  private client: SecretManagerServiceClient;
  private logger: Logger;
  private projectId: string;

  constructor(options: GCPServiceOptions = {}) {
    this.logger = Logger.getInstance('gcp-secrets');
    this.projectId = options.projectId || Config.getInstance().gcp.projectId;

    this.client = new SecretManagerServiceClient({
      projectId: this.projectId,
      keyFilename: options.keyFilename,
      credentials: options.credentials
    });
  }

  /**
   * Get secret value by name
   */
  @retry({ retries: 3, delay: 1000 })
  public async getSecret(secretName: string, version: string = 'latest'): Promise<string> {
    const startTime = Date.now();

    try {
      this.logger.debug('Retrieving secret', { secretName, version });

      const name = `projects/${this.projectId}/secrets/${secretName}/versions/${version}`;
      const [secretVersion] = await this.client.accessSecretVersion({ name });

      if (!secretVersion.payload?.data) {
        throw new GenesisError(`Secret ${secretName} has no data`, 404);
      }

      const secretValue = secretVersion.payload.data.toString();
      const duration = Date.now() - startTime;

      this.logger.info('Secret retrieved successfully', {
        secretName,
        version,
        duration
      });

      return secretValue;

    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('Failed to retrieve secret', {
        secretName,
        version,
        error: error.message,
        duration
      });

      throw new ExternalServiceError(
        'SecretManager',
        `Failed to retrieve secret ${secretName}: ${error.message}`,
        500
      );
    }
  }

  /**
   * Create or update secret
   */
  public async setSecret(secretName: string, value: string): Promise<void> {
    const startTime = Date.now();

    try {
      this.logger.debug('Setting secret', { secretName });

      const parent = `projects/${this.projectId}`;

      // Try to create secret first
      try {
        await this.client.createSecret({
          parent,
          secretId: secretName,
          secret: {
            replication: {
              automatic: {}
            }
          }
        });

        this.logger.info('Secret created', { secretName });
      } catch (error) {
        // Secret might already exist, that's okay
        if (!error.message.includes('already exists')) {
          throw error;
        }
      }

      // Add version with the value
      const secretPath = `${parent}/secrets/${secretName}`;
      await this.client.addSecretVersion({
        parent: secretPath,
        payload: {
          data: Buffer.from(value, 'utf8')
        }
      });

      const duration = Date.now() - startTime;
      this.logger.info('Secret version added', { secretName, duration });

    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('Failed to set secret', {
        secretName,
        error: error.message,
        duration
      });

      throw new ExternalServiceError(
        'SecretManager',
        `Failed to set secret ${secretName}: ${error.message}`,
        500
      );
    }
  }

  /**
   * List all secrets
   */
  public async listSecrets(): Promise<string[]> {
    try {
      const parent = `projects/${this.projectId}`;
      const [secrets] = await this.client.listSecrets({ parent });

      return secrets.map(secret => {
        const parts = secret.name!.split('/');
        return parts[parts.length - 1];
      });

    } catch (error) {
      this.logger.error('Failed to list secrets', { error: error.message });
      throw new ExternalServiceError(
        'SecretManager',
        `Failed to list secrets: ${error.message}`,
        500
      );
    }
  }
}

/**
 * GCP Pub/Sub Integration
 */
export class GCPPubSub {
  private client: PubSub;
  private logger: Logger;
  private projectId: string;

  constructor(options: GCPServiceOptions = {}) {
    this.logger = Logger.getInstance('gcp-pubsub');
    this.projectId = options.projectId || Config.getInstance().gcp.projectId;

    this.client = new PubSub({
      projectId: this.projectId,
      keyFilename: options.keyFilename,
      credentials: options.credentials
    });
  }

  /**
   * Publish message to topic
   */
  @retry({ retries: 3, delay: 1000 })
  public async publishMessage(
    topicName: string,
    message: object | string,
    attributes?: Record<string, string>
  ): Promise<string> {
    const startTime = Date.now();

    try {
      this.logger.debug('Publishing message', { topicName, attributes });

      const topic = this.client.topic(topicName);
      const messageData = typeof message === 'string' ? message : JSON.stringify(message);

      const messageId = await topic.publishMessage({
        data: Buffer.from(messageData, 'utf8'),
        attributes: {
          ...attributes,
          publishedAt: new Date().toISOString(),
          source: Config.getInstance().serviceName
        }
      });

      const duration = Date.now() - startTime;
      this.logger.info('Message published', {
        topicName,
        messageId,
        duration,
        messageSize: messageData.length
      });

      return messageId;

    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('Failed to publish message', {
        topicName,
        error: error.message,
        duration
      });

      throw new ExternalServiceError(
        'PubSub',
        `Failed to publish to ${topicName}: ${error.message}`,
        500
      );
    }
  }

  /**
   * Create topic if it doesn't exist
   */
  public async createTopic(topicName: string): Promise<void> {
    try {
      this.logger.debug('Creating topic', { topicName });

      const topic = this.client.topic(topicName);
      const [exists] = await topic.exists();

      if (!exists) {
        await topic.create();
        this.logger.info('Topic created', { topicName });
      } else {
        this.logger.debug('Topic already exists', { topicName });
      }

    } catch (error) {
      this.logger.error('Failed to create topic', {
        topicName,
        error: error.message
      });

      throw new ExternalServiceError(
        'PubSub',
        `Failed to create topic ${topicName}: ${error.message}`,
        500
      );
    }
  }

  /**
   * Create subscription
   */
  public async createSubscription(
    topicName: string,
    subscriptionName: string,
    options: any = {}
  ): Promise<void> {
    try {
      this.logger.debug('Creating subscription', { topicName, subscriptionName });

      const topic = this.client.topic(topicName);
      const subscription = topic.subscription(subscriptionName);
      const [exists] = await subscription.exists();

      if (!exists) {
        await topic.createSubscription(subscriptionName, {
          ackDeadlineSeconds: 60,
          messageRetentionDuration: '7d',
          ...options
        });

        this.logger.info('Subscription created', { topicName, subscriptionName });
      } else {
        this.logger.debug('Subscription already exists', { topicName, subscriptionName });
      }

    } catch (error) {
      this.logger.error('Failed to create subscription', {
        topicName,
        subscriptionName,
        error: error.message
      });

      throw new ExternalServiceError(
        'PubSub',
        `Failed to create subscription ${subscriptionName}: ${error.message}`,
        500
      );
    }
  }
}

/**
 * GCP Firestore Integration
 */
export class GCPFirestore {
  private client: Firestore;
  private logger: Logger;

  constructor(options: GCPServiceOptions = {}) {
    this.logger = Logger.getInstance('gcp-firestore');

    this.client = new Firestore({
      projectId: options.projectId || Config.getInstance().gcp.projectId,
      keyFilename: options.keyFilename,
      credentials: options.credentials
    });
  }

  /**
   * Get document by path
   */
  @retry({ retries: 3, delay: 1000 })
  public async getDocument(collection: string, documentId: string): Promise<any> {
    const startTime = Date.now();

    try {
      this.logger.debug('Getting document', { collection, documentId });

      const docRef = this.client.collection(collection).doc(documentId);
      const doc = await docRef.get();

      const duration = Date.now() - startTime;

      if (!doc.exists) {
        this.logger.warn('Document not found', { collection, documentId, duration });
        return null;
      }

      const data = doc.data();
      this.logger.info('Document retrieved', {
        collection,
        documentId,
        duration,
        hasData: !!data
      });

      return {
        id: doc.id,
        ...data,
        _metadata: {
          createTime: doc.createTime,
          updateTime: doc.updateTime
        }
      };

    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('Failed to get document', {
        collection,
        documentId,
        error: error.message,
        duration
      });

      throw new ExternalServiceError(
        'Firestore',
        `Failed to get document ${collection}/${documentId}: ${error.message}`,
        500
      );
    }
  }

  /**
   * Create or update document
   */
  public async setDocument(
    collection: string,
    documentId: string,
    data: any,
    merge: boolean = false
  ): Promise<void> {
    const startTime = Date.now();

    try {
      this.logger.debug('Setting document', { collection, documentId, merge });

      const docRef = this.client.collection(collection).doc(documentId);

      const enrichedData = {
        ...data,
        updatedAt: new Date(),
        ...(merge ? {} : { createdAt: new Date() })
      };

      await docRef.set(enrichedData, { merge });

      const duration = Date.now() - startTime;
      this.logger.info('Document set', {
        collection,
        documentId,
        merge,
        duration
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('Failed to set document', {
        collection,
        documentId,
        error: error.message,
        duration
      });

      throw new ExternalServiceError(
        'Firestore',
        `Failed to set document ${collection}/${documentId}: ${error.message}`,
        500
      );
    }
  }

  /**
   * Query collection with filters
   */
  public async queryCollection(
    collection: string,
    filters: Array<{ field: string; operator: FirebaseFirestore.WhereFilterOp; value: any }> = [],
    orderBy?: { field: string; direction?: 'asc' | 'desc' },
    limit?: number
  ): Promise<any[]> {
    const startTime = Date.now();

    try {
      this.logger.debug('Querying collection', { collection, filters, orderBy, limit });

      let query: FirebaseFirestore.Query = this.client.collection(collection);

      // Apply filters
      for (const filter of filters) {
        query = query.where(filter.field, filter.operator, filter.value);
      }

      // Apply ordering
      if (orderBy) {
        query = query.orderBy(orderBy.field, orderBy.direction || 'asc');
      }

      // Apply limit
      if (limit) {
        query = query.limit(limit);
      }

      const snapshot = await query.get();
      const results = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data(),
        _metadata: {
          createTime: doc.createTime,
          updateTime: doc.updateTime
        }
      }));

      const duration = Date.now() - startTime;
      this.logger.info('Collection queried', {
        collection,
        resultCount: results.length,
        duration
      });

      return results;

    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('Failed to query collection', {
        collection,
        error: error.message,
        duration
      });

      throw new ExternalServiceError(
        'Firestore',
        `Failed to query collection ${collection}: ${error.message}`,
        500
      );
    }
  }
}

/**
 * GCP Cloud Storage Integration
 */
export class GCPStorage {
  private client: Storage;
  private logger: Logger;

  constructor(options: GCPServiceOptions = {}) {
    this.logger = Logger.getInstance('gcp-storage');

    this.client = new Storage({
      projectId: options.projectId || Config.getInstance().gcp.projectId,
      keyFilename: options.keyFilename,
      credentials: options.credentials
    });
  }

  /**
   * Upload file to bucket
   */
  @retry({ retries: 3, delay: 2000 })
  public async uploadFile(
    bucketName: string,
    fileName: string,
    fileContent: Buffer | string,
    options: any = {}
  ): Promise<string> {
    const startTime = Date.now();

    try {
      this.logger.debug('Uploading file', { bucketName, fileName });

      const bucket = this.client.bucket(bucketName);
      const file = bucket.file(fileName);

      const stream = file.createWriteStream({
        metadata: {
          contentType: options.contentType || 'application/octet-stream',
          metadata: {
            uploadedAt: new Date().toISOString(),
            service: Config.getInstance().serviceName
          }
        },
        public: options.public || false
      });

      await new Promise((resolve, reject) => {
        stream.on('error', reject);
        stream.on('finish', resolve);

        if (Buffer.isBuffer(fileContent)) {
          stream.end(fileContent);
        } else {
          stream.end(fileContent);
        }
      });

      const duration = Date.now() - startTime;
      const fileSize = Buffer.isBuffer(fileContent) ? fileContent.length : fileContent.length;

      this.logger.info('File uploaded', {
        bucketName,
        fileName,
        duration,
        fileSize
      });

      return `gs://${bucketName}/${fileName}`;

    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('Failed to upload file', {
        bucketName,
        fileName,
        error: error.message,
        duration
      });

      throw new ExternalServiceError(
        'CloudStorage',
        `Failed to upload file ${fileName}: ${error.message}`,
        500
      );
    }
  }

  /**
   * Download file from bucket
   */
  public async downloadFile(bucketName: string, fileName: string): Promise<Buffer> {
    const startTime = Date.now();

    try {
      this.logger.debug('Downloading file', { bucketName, fileName });

      const bucket = this.client.bucket(bucketName);
      const file = bucket.file(fileName);

      const [buffer] = await file.download();

      const duration = Date.now() - startTime;
      this.logger.info('File downloaded', {
        bucketName,
        fileName,
        duration,
        fileSize: buffer.length
      });

      return buffer;

    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('Failed to download file', {
        bucketName,
        fileName,
        error: error.message,
        duration
      });

      throw new ExternalServiceError(
        'CloudStorage',
        `Failed to download file ${fileName}: ${error.message}`,
        500
      );
    }
  }

  /**
   * Generate signed URL for file access
   */
  public async getSignedUrl(
    bucketName: string,
    fileName: string,
    action: 'read' | 'write' = 'read',
    expires: Date = new Date(Date.now() + 3600000) // 1 hour default
  ): Promise<string> {
    try {
      const bucket = this.client.bucket(bucketName);
      const file = bucket.file(fileName);

      const [url] = await file.getSignedUrl({
        action,
        expires
      });

      this.logger.info('Signed URL generated', {
        bucketName,
        fileName,
        action,
        expires: expires.toISOString()
      });

      return url;

    } catch (error) {
      this.logger.error('Failed to generate signed URL', {
        bucketName,
        fileName,
        error: error.message
      });

      throw new ExternalServiceError(
        'CloudStorage',
        `Failed to generate signed URL for ${fileName}: ${error.message}`,
        500
      );
    }
  }
}

/**
 * Unified GCP Services Manager
 */
export class GCPServices {
  public readonly secrets: GCPSecretManager;
  public readonly pubsub: GCPPubSub;
  public readonly firestore: GCPFirestore;
  public readonly storage: GCPStorage;

  private static instance: GCPServices;
  private logger: Logger;

  private constructor(options: GCPServiceOptions = {}) {
    this.logger = Logger.getInstance('gcp-services');

    this.secrets = new GCPSecretManager(options);
    this.pubsub = new GCPPubSub(options);
    this.firestore = new GCPFirestore(options);
    this.storage = new GCPStorage(options);

    this.logger.info('GCP Services initialized', {
      projectId: options.projectId || Config.getInstance().gcp.projectId
    });
  }

  public static getInstance(options: GCPServiceOptions = {}): GCPServices {
    if (!GCPServices.instance) {
      GCPServices.instance = new GCPServices(options);
    }
    return GCPServices.instance;
  }

  /**
   * Health check for all GCP services
   */
  public async healthCheck(): Promise<Record<string, boolean>> {
    const checks: Record<string, boolean> = {};

    // Check Secret Manager
    try {
      await this.secrets.listSecrets();
      checks.secretManager = true;
    } catch (error) {
      this.logger.warn('Secret Manager health check failed', { error: error.message });
      checks.secretManager = false;
    }

    // Check Firestore
    try {
      await this.firestore.client.listCollections();
      checks.firestore = true;
    } catch (error) {
      this.logger.warn('Firestore health check failed', { error: error.message });
      checks.firestore = false;
    }

    // Check Pub/Sub
    try {
      await this.pubsub.client.getTopics();
      checks.pubsub = true;
    } catch (error) {
      this.logger.warn('Pub/Sub health check failed', { error: error.message });
      checks.pubsub = false;
    }

    // Check Storage
    try {
      await this.storage.client.getBuckets();
      checks.storage = true;
    } catch (error) {
      this.logger.warn('Cloud Storage health check failed', { error: error.message });
      checks.storage = false;
    }

    this.logger.info('GCP services health check completed', { checks });
    return checks;
  }
}

// Export singleton instance
export const gcpServices = GCPServices.getInstance();
