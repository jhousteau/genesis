import { retryFunction, CircuitBreaker, CircuitBreakerState } from '../src/retry';

describe('Retry Functions', () => {
  describe('retryFunction', () => {
    it('should succeed on first attempt', async () => {
      const fn = jest.fn().mockResolvedValue('success');
      const result = await retryFunction(fn);
      
      expect(result).toBe('success');
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should retry on failure', async () => {
      const fn = jest.fn()
        .mockRejectedValueOnce(new Error('fail 1'))
        .mockRejectedValueOnce(new Error('fail 2'))
        .mockResolvedValueOnce('success');
      
      const result = await retryFunction(fn, { maxAttempts: 3, initialDelay: 1 });
      
      expect(result).toBe('success');
      expect(fn).toHaveBeenCalledTimes(3);
    });

    it('should fail after max attempts', async () => {
      const fn = jest.fn().mockRejectedValue(new Error('always fails'));
      
      await expect(retryFunction(fn, { maxAttempts: 2, initialDelay: 1 }))
        .rejects.toThrow('always fails');
      expect(fn).toHaveBeenCalledTimes(2);
    });
  });

  describe('CircuitBreaker', () => {
    it('should start in CLOSED state', () => {
      const cb = CircuitBreaker.create();
      expect(cb.getState()).toBe(CircuitBreakerState.CLOSED);
    });

    it('should record successful calls', async () => {
      const cb = CircuitBreaker.create();
      const fn = jest.fn().mockResolvedValue('success');
      
      const result = await cb.execute(fn);
      
      expect(result).toBe('success');
      const metrics = cb.getMetrics();
      expect(metrics.totalRequests).toBe(1);
      expect(metrics.successfulRequests).toBe(1);
      expect(metrics.successRate).toBe(100);
    });

    it('should open circuit after failure threshold', async () => {
      const cb = CircuitBreaker.create({ failureThreshold: 2 });
      const fn = jest.fn().mockRejectedValue(new Error('fail'));
      
      // First failure
      await expect(cb.execute(fn)).rejects.toThrow('fail');
      expect(cb.getState()).toBe(CircuitBreakerState.CLOSED);
      
      // Second failure - should open circuit
      await expect(cb.execute(fn)).rejects.toThrow('fail');
      expect(cb.getState()).toBe(CircuitBreakerState.OPEN);
      
      // Third call should fail fast without calling function
      await expect(cb.execute(fn)).rejects.toThrow('Circuit breaker');
      expect(fn).toHaveBeenCalledTimes(2); // Function not called on third attempt
    });
  });
});