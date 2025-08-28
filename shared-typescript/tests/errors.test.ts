import { GenesisError, ValidationError, NetworkError, handleError, ErrorCategory, ErrorSeverity } from '../src/errors';

describe('Error Handling', () => {
  describe('GenesisError', () => {
    it('should create error with default values', () => {
      const error = new GenesisError({ message: 'Test error' });

      expect(error.message).toBe('Test error');
      expect(error.code).toBe('GENESIS_ERROR');
      expect(error.category).toBe(ErrorCategory.UNKNOWN);
      expect(error.severity).toBe(ErrorSeverity.ERROR);
      expect(error.recoverable).toBe(true);
      expect(error.context).toBeDefined();
      expect(error.context.correlationId).toBeDefined();
    });

    it('should serialize to JSON correctly', () => {
      const error = new GenesisError({
        message: 'Test error',
        code: 'TEST_ERROR',
        details: { field: 'name' },
      });

      const json = error.toJSON();

      expect(json.error.message).toBe('Test error');
      expect(json.error.code).toBe('TEST_ERROR');
      expect(json.details.field).toBe('name');
      expect(json.context.correlationId).toBeDefined();
    });
  });

  describe('Specific Error Types', () => {
    it('should create ValidationError', () => {
      const error = new ValidationError('Invalid email', 'email');

      expect(error).toBeInstanceOf(GenesisError);
      expect(error.category).toBe(ErrorCategory.VALIDATION);
      expect(error.severity).toBe(ErrorSeverity.WARNING);
      expect(error.details.field).toBe('email');
    });

    it('should create NetworkError', () => {
      const error = new NetworkError('Connection failed', 'https://api.example.com');

      expect(error).toBeInstanceOf(GenesisError);
      expect(error.category).toBe(ErrorCategory.NETWORK);
      expect(error.details.endpoint).toBe('https://api.example.com');
    });
  });

  describe('handleError', () => {
    it('should return GenesisError as-is', () => {
      const originalError = new ValidationError('Test validation error');
      const handledError = handleError(originalError);

      expect(handledError).toBe(originalError);
    });

    it('should convert standard Error to GenesisError', () => {
      const originalError = new TypeError('Invalid type');
      const handledError = handleError(originalError);

      expect(handledError).toBeInstanceOf(ValidationError);
      expect(handledError.message).toBe('Invalid type');
      expect(handledError.cause).toBe(originalError);
    });

    it('should convert unknown error to base GenesisError', () => {
      const originalError = new Error('Unknown error');
      const handledError = handleError(originalError);

      expect(handledError).toBeInstanceOf(GenesisError);
      expect(handledError.message).toBe('Unknown error');
      expect(handledError.cause).toBe(originalError);
    });
  });
});
