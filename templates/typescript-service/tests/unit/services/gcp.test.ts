/**
 * GCP Services Unit Tests
 *
 * Comprehensive unit tests for GCP integration services
 * following Genesis testing patterns and CRAFT methodology.
 */

import { GCPSecretManager, GCPPubSub, GCPFirestore, GCPStorage, GCPServices } from '../../../src/services/gcp';
import { ExternalServiceError } from '../../../src/types/errors';

// Mock GCP clients
jest.mock('@google-cloud/secret-manager');
jest.mock('@google-cloud/pubsub');
jest.mock('@google-cloud/firestore');
jest.mock('@google-cloud/storage');

describe('GCPSecretManager', () => {
  let secretManager: GCPSecretManager;
  let mockClient: any;

  beforeEach(() => {
    // Clear mocks
    jest.clearAllMocks();

    // Mock Secret Manager client
    const { SecretManagerServiceClient } = require('@google-cloud/secret-manager');
    mockClient = {
      accessSecretVersion: jest.fn(),
      createSecret: jest.fn(),
      addSecretVersion: jest.fn(),
      listSecrets: jest.fn()
    };
    SecretManagerServiceClient.mockImplementation(() => mockClient);

    secretManager = new GCPSecretManager({ projectId: 'test-project' });
  });

  describe('getSecret', () => {
    it('should retrieve secret successfully', async () => {
      const mockSecretData = 'secret-value';
      mockClient.accessSecretVersion.mockResolvedValue([{
        payload: { data: Buffer.from(mockSecretData) }
      }]);

      const result = await secretManager.getSecret('test-secret');

      expect(result).toBe(mockSecretData);
      expect(mockClient.accessSecretVersion).toHaveBeenCalledWith({
        name: 'projects/test-project/secrets/test-secret/versions/latest'
      });
    });

    it('should handle secret not found', async () => {
      mockClient.accessSecretVersion.mockResolvedValue([{
        payload: null
      }]);

      await expect(secretManager.getSecret('missing-secret'))
        .rejects
        .toThrow('Secret missing-secret has no data');
    });

    it('should handle API errors', async () => {
      const error = new Error('API Error');
      mockClient.accessSecretVersion.mockRejectedValue(error);

      await expect(secretManager.getSecret('test-secret'))
        .rejects
        .toBeInstanceOf(ExternalServiceError);
    });

    it('should retry on failure', async () => {
      mockClient.accessSecretVersion
        .mockRejectedValueOnce(new Error('Temporary error'))
        .mockResolvedValue([{
          payload: { data: Buffer.from('secret-value') }
        }]);

      const result = await secretManager.getSecret('test-secret');

      expect(result).toBe('secret-value');
      expect(mockClient.accessSecretVersion).toHaveBeenCalledTimes(2);
    });
  });

  describe('setSecret', () => {
    it('should create and set secret successfully', async () => {
      mockClient.createSecret.mockResolvedValue({});
      mockClient.addSecretVersion.mockResolvedValue({});

      await secretManager.setSecret('new-secret', 'secret-value');

      expect(mockClient.createSecret).toHaveBeenCalledWith({
        parent: 'projects/test-project',
        secretId: 'new-secret',
        secret: {
          replication: { automatic: {} }
        }
      });

      expect(mockClient.addSecretVersion).toHaveBeenCalledWith({
        parent: 'projects/test-project/secrets/new-secret',
        payload: {
          data: Buffer.from('secret-value', 'utf8')
        }
      });
    });

    it('should handle existing secret', async () => {
      const existsError = new Error('Secret already exists');
      existsError.message = 'already exists';
      mockClient.createSecret.mockRejectedValue(existsError);
      mockClient.addSecretVersion.mockResolvedValue({});

      await secretManager.setSecret('existing-secret', 'secret-value');

      expect(mockClient.addSecretVersion).toHaveBeenCalled();
    });
  });

  describe('listSecrets', () => {
    it('should list secrets successfully', async () => {
      const mockSecrets = [
        { name: 'projects/test-project/secrets/secret-1' },
        { name: 'projects/test-project/secrets/secret-2' }
      ];
      mockClient.listSecrets.mockResolvedValue([mockSecrets]);

      const result = await secretManager.listSecrets();

      expect(result).toEqual(['secret-1', 'secret-2']);
      expect(mockClient.listSecrets).toHaveBeenCalledWith({
        parent: 'projects/test-project'
      });
    });
  });
});

describe('GCPPubSub', () => {
  let pubsub: GCPPubSub;
  let mockClient: any;
  let mockTopic: any;

  beforeEach(() => {
    jest.clearAllMocks();

    mockTopic = {
      publishMessage: jest.fn(),
      exists: jest.fn(),
      create: jest.fn(),
      subscription: jest.fn(),
      createSubscription: jest.fn()
    };

    const { PubSub } = require('@google-cloud/pubsub');
    mockClient = {
      topic: jest.fn().mockReturnValue(mockTopic),
      getTopics: jest.fn()
    };
    PubSub.mockImplementation(() => mockClient);

    pubsub = new GCPPubSub({ projectId: 'test-project' });
  });

  describe('publishMessage', () => {
    it('should publish message successfully', async () => {
      const messageId = 'message-123';
      mockTopic.publishMessage.mockResolvedValue(messageId);

      const result = await pubsub.publishMessage('test-topic', { data: 'test' });

      expect(result).toBe(messageId);
      expect(mockClient.topic).toHaveBeenCalledWith('test-topic');
      expect(mockTopic.publishMessage).toHaveBeenCalledWith({
        data: Buffer.from('{"data":"test"}', 'utf8'),
        attributes: expect.objectContaining({
          publishedAt: expect.any(String),
          source: expect.any(String)
        })
      });
    });

    it('should handle string messages', async () => {
      const messageId = 'message-123';
      mockTopic.publishMessage.mockResolvedValue(messageId);

      const result = await pubsub.publishMessage('test-topic', 'test message');

      expect(result).toBe(messageId);
      expect(mockTopic.publishMessage).toHaveBeenCalledWith({
        data: Buffer.from('test message', 'utf8'),
        attributes: expect.any(Object)
      });
    });

    it('should handle publish errors', async () => {
      const error = new Error('Publish failed');
      mockTopic.publishMessage.mockRejectedValue(error);

      await expect(pubsub.publishMessage('test-topic', { data: 'test' }))
        .rejects
        .toBeInstanceOf(ExternalServiceError);
    });
  });

  describe('createTopic', () => {
    it('should create topic if not exists', async () => {
      mockTopic.exists.mockResolvedValue([false]);
      mockTopic.create.mockResolvedValue({});

      await pubsub.createTopic('new-topic');

      expect(mockTopic.exists).toHaveBeenCalled();
      expect(mockTopic.create).toHaveBeenCalled();
    });

    it('should skip creation if topic exists', async () => {
      mockTopic.exists.mockResolvedValue([true]);

      await pubsub.createTopic('existing-topic');

      expect(mockTopic.exists).toHaveBeenCalled();
      expect(mockTopic.create).not.toHaveBeenCalled();
    });
  });
});

describe('GCPFirestore', () => {
  let firestore: GCPFirestore;
  let mockClient: any;
  let mockCollection: any;
  let mockDoc: any;

  beforeEach(() => {
    jest.clearAllMocks();

    mockDoc = {
      get: jest.fn(),
      set: jest.fn(),
      id: 'doc-123',
      createTime: new Date(),
      updateTime: new Date(),
      exists: true,
      data: jest.fn().mockReturnValue({ field: 'value' })
    };

    mockCollection = {
      doc: jest.fn().mockReturnValue(mockDoc),
      where: jest.fn().mockReturnThis(),
      orderBy: jest.fn().mockReturnThis(),
      limit: jest.fn().mockReturnThis(),
      get: jest.fn()
    };

    const { Firestore } = require('@google-cloud/firestore');
    mockClient = {
      collection: jest.fn().mockReturnValue(mockCollection),
      listCollections: jest.fn()
    };
    Firestore.mockImplementation(() => mockClient);

    firestore = new GCPFirestore({ projectId: 'test-project' });
  });

  describe('getDocument', () => {
    it('should get document successfully', async () => {
      mockDoc.get.mockResolvedValue(mockDoc);

      const result = await firestore.getDocument('users', 'user-123');

      expect(result).toEqual({
        id: 'doc-123',
        field: 'value',
        _metadata: {
          createTime: expect.any(Date),
          updateTime: expect.any(Date)
        }
      });
      expect(mockCollection.doc).toHaveBeenCalledWith('user-123');
    });

    it('should handle document not found', async () => {
      mockDoc.exists = false;
      mockDoc.get.mockResolvedValue(mockDoc);

      const result = await firestore.getDocument('users', 'missing-user');

      expect(result).toBeNull();
    });

    it('should handle Firestore errors', async () => {
      const error = new Error('Firestore error');
      mockDoc.get.mockRejectedValue(error);

      await expect(firestore.getDocument('users', 'user-123'))
        .rejects
        .toBeInstanceOf(ExternalServiceError);
    });
  });

  describe('setDocument', () => {
    it('should set document successfully', async () => {
      mockDoc.set.mockResolvedValue({});

      await firestore.setDocument('users', 'user-123', { name: 'Test User' });

      expect(mockDoc.set).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Test User',
          updatedAt: expect.any(Date),
          createdAt: expect.any(Date)
        }),
        { merge: false }
      );
    });

    it('should merge document when specified', async () => {
      mockDoc.set.mockResolvedValue({});

      await firestore.setDocument('users', 'user-123', { name: 'Test User' }, true);

      expect(mockDoc.set).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Test User',
          updatedAt: expect.any(Date)
        }),
        { merge: true }
      );
    });
  });

  describe('queryCollection', () => {
    it('should query collection successfully', async () => {
      const mockSnapshot = {
        docs: [mockDoc]
      };
      mockCollection.get.mockResolvedValue(mockSnapshot);

      const result = await firestore.queryCollection('users', [
        { field: 'active', operator: '==', value: true }
      ]);

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({
        id: 'doc-123',
        field: 'value',
        _metadata: {
          createTime: expect.any(Date),
          updateTime: expect.any(Date)
        }
      });
      expect(mockCollection.where).toHaveBeenCalledWith('active', '==', true);
    });
  });
});

describe('GCPStorage', () => {
  let storage: GCPStorage;
  let mockClient: any;
  let mockBucket: any;
  let mockFile: any;

  beforeEach(() => {
    jest.clearAllMocks();

    const mockStream = {
      on: jest.fn(),
      end: jest.fn()
    };

    // Chain on() calls
    mockStream.on.mockImplementation((event, callback) => {
      if (event === 'finish') {
        setTimeout(callback, 0);
      }
      return mockStream;
    });

    mockFile = {
      createWriteStream: jest.fn().mockReturnValue(mockStream),
      download: jest.fn(),
      getSignedUrl: jest.fn()
    };

    mockBucket = {
      file: jest.fn().mockReturnValue(mockFile)
    };

    const { Storage } = require('@google-cloud/storage');
    mockClient = {
      bucket: jest.fn().mockReturnValue(mockBucket),
      getBuckets: jest.fn()
    };
    Storage.mockImplementation(() => mockClient);

    storage = new GCPStorage({ projectId: 'test-project' });
  });

  describe('uploadFile', () => {
    it('should upload file successfully', async () => {
      const fileContent = Buffer.from('test content');

      const result = await storage.uploadFile('test-bucket', 'test-file.txt', fileContent);

      expect(result).toBe('gs://test-bucket/test-file.txt');
      expect(mockBucket.file).toHaveBeenCalledWith('test-file.txt');
      expect(mockFile.createWriteStream).toHaveBeenCalledWith({
        metadata: expect.any(Object),
        public: false
      });
    });

    it('should handle upload errors', async () => {
      const mockStream = {
        on: jest.fn().mockImplementation((event, callback) => {
          if (event === 'error') {
            setTimeout(() => callback(new Error('Upload failed')), 0);
          }
          return mockStream;
        }),
        end: jest.fn()
      };

      mockFile.createWriteStream.mockReturnValue(mockStream);

      await expect(storage.uploadFile('test-bucket', 'test-file.txt', 'content'))
        .rejects
        .toBeInstanceOf(ExternalServiceError);
    });
  });

  describe('downloadFile', () => {
    it('should download file successfully', async () => {
      const fileBuffer = Buffer.from('file content');
      mockFile.download.mockResolvedValue([fileBuffer]);

      const result = await storage.downloadFile('test-bucket', 'test-file.txt');

      expect(result).toBe(fileBuffer);
      expect(mockFile.download).toHaveBeenCalled();
    });

    it('should handle download errors', async () => {
      const error = new Error('Download failed');
      mockFile.download.mockRejectedValue(error);

      await expect(storage.downloadFile('test-bucket', 'test-file.txt'))
        .rejects
        .toBeInstanceOf(ExternalServiceError);
    });
  });

  describe('getSignedUrl', () => {
    it('should generate signed URL successfully', async () => {
      const signedUrl = 'https://storage.googleapis.com/test-bucket/test-file.txt?signature=...';
      mockFile.getSignedUrl.mockResolvedValue([signedUrl]);

      const result = await storage.getSignedUrl('test-bucket', 'test-file.txt');

      expect(result).toBe(signedUrl);
      expect(mockFile.getSignedUrl).toHaveBeenCalledWith({
        action: 'read',
        expires: expect.any(Date)
      });
    });
  });
});

describe('GCPServices', () => {
  let gcpServices: GCPServices;

  beforeEach(() => {
    jest.clearAllMocks();
    gcpServices = GCPServices.getInstance({ projectId: 'test-project' });
  });

  describe('healthCheck', () => {
    it('should perform health check for all services', async () => {
      // Mock all service health checks to succeed
      gcpServices.secrets.listSecrets = jest.fn().mockResolvedValue(['secret1']);
      gcpServices.firestore.client.listCollections = jest.fn().mockResolvedValue([]);
      gcpServices.pubsub.client.getTopics = jest.fn().mockResolvedValue([]);
      gcpServices.storage.client.getBuckets = jest.fn().mockResolvedValue([]);

      const result = await gcpServices.healthCheck();

      expect(result).toEqual({
        secretManager: true,
        firestore: true,
        pubsub: true,
        storage: true
      });
    });

    it('should handle service failures in health check', async () => {
      // Mock some services to fail
      gcpServices.secrets.listSecrets = jest.fn().mockRejectedValue(new Error('Service unavailable'));
      gcpServices.firestore.client.listCollections = jest.fn().mockResolvedValue([]);
      gcpServices.pubsub.client.getTopics = jest.fn().mockRejectedValue(new Error('PubSub error'));
      gcpServices.storage.client.getBuckets = jest.fn().mockResolvedValue([]);

      const result = await gcpServices.healthCheck();

      expect(result).toEqual({
        secretManager: false,
        firestore: true,
        pubsub: false,
        storage: true
      });
    });
  });

  describe('singleton pattern', () => {
    it('should return the same instance', () => {
      const instance1 = GCPServices.getInstance();
      const instance2 = GCPServices.getInstance();

      expect(instance1).toBe(instance2);
    });
  });
});
