"""Lightweight retry decorator with exponential backoff."""

import asyncio
import functools
import random
import time
from typing import Any, Callable, Optional, Type, Union
from dataclasses import dataclass


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    exceptions: tuple[Type[Exception], ...] = (Exception,)


def retry(config: Optional[RetryConfig] = None) -> Callable:
    """Retry decorator with exponential backoff.
    
    Args:
        config: RetryConfig instance. Defaults to basic configuration.
        
    Usage:
        @retry()
        def unreliable_function():
            # May fail, will be retried
            pass
            
        @retry(RetryConfig(max_attempts=5, initial_delay=0.5))
        async def async_function():
            # Async functions supported
            pass
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            return _async_retry_wrapper(func, config)
        else:
            return _sync_retry_wrapper(func, config)
    
    return decorator


def _sync_retry_wrapper(func: Callable, config: RetryConfig) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                return func(*args, **kwargs)
            except config.exceptions as e:
                last_exception = e
                if attempt == config.max_attempts - 1:
                    break
                
                delay = min(
                    config.initial_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
                if config.jitter:
                    delay *= random.uniform(0.5, 1.5)
                
                time.sleep(delay)
        
        raise last_exception
    
    return wrapper


def _async_retry_wrapper(func: Callable, config: RetryConfig) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except config.exceptions as e:
                last_exception = e
                if attempt == config.max_attempts - 1:
                    break
                
                delay = min(
                    config.initial_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
                if config.jitter:
                    delay *= random.uniform(0.5, 1.5)
                
                await asyncio.sleep(delay)
        
        raise last_exception
    
    return wrapper