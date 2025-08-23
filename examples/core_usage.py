#!/usr/bin/env python3
"""
Genesis Core Usage Examples

Demonstrates basic usage patterns for all Genesis Core components.
This example shows how to use error handling, logging, retry logic,
health checks, and context management in a simple application.

Run this example:
    python examples/core_usage.py
"""

import asyncio
import random
import time

# Import Genesis Core components
from core import (AGGRESSIVE_POLICY, CircuitBreaker, Context, DiskHealthCheck,
                  GenesisError, HealthStatus, HTTPHealthCheck,
                  MemoryHealthCheck, RequestContext, TraceContext, UserContext,
                  configure_core, context_span, get_context,
                  get_health_registry, get_logger, handle_error, retry)


def example_basic_setup():
    """Example 1: Basic Genesis Core setup"""
    print("=== Example 1: Basic Setup ===")

    # Configure all core components at once
    configure_core(
        service_name="example-service",
        environment="development",
        version="1.0.0",
        log_level="INFO",
    )

    # Get a logger (automatically configured)
    logger = get_logger(__name__)
    logger.info("Genesis Core configured and ready!")

    print("✅ Core components configured")


def example_structured_logging():
    """Example 2: Structured logging with context"""
    print("\n=== Example 2: Structured Logging ===")

    logger = get_logger("example.logging")

    # Basic structured logging
    logger.info("Processing user request", user_id="12345", action="create_order")

    # Performance timing
    with logger.timer("database_operation", operation_type="SELECT"):
        # Simulate database operation
        time.sleep(0.1)

    # Error logging with context
    try:
        raise ValueError("Something went wrong!")
    except Exception as e:
        logger.error("Operation failed", error=e, user_id="12345")

    print("✅ Structured logging examples completed")


def example_error_handling():
    """Example 3: Structured error handling"""
    print("\n=== Example 3: Error Handling ===")

    logger = get_logger("example.errors")

    def risky_operation():
        """Simulate a risky operation that might fail"""
        if random.random() < 0.5:
            raise ConnectionError("Network connection failed")
        elif random.random() < 0.7:
            raise ValueError("Invalid input data")
        else:
            return "Success!"

    try:
        result = risky_operation()
        logger.info("Operation succeeded", result=result)
    except Exception as e:
        # Convert to Genesis error with automatic categorization
        genesis_error = handle_error(e)

        logger.error(
            "Operation failed with Genesis error",
            error_code=genesis_error.code,
            error_category=genesis_error.category.value,
            correlation_id=genesis_error.context.correlation_id,
        )

        # Print error details
        print(f"Genesis Error: {genesis_error.code}")
        print(f"Category: {genesis_error.category.value}")
        print(f"Message: {genesis_error.message}")
        print(f"Recoverable: {genesis_error.recoverable}")

    print("✅ Error handling examples completed")


def example_retry_logic():
    """Example 4: Retry logic with different strategies"""
    print("\n=== Example 4: Retry Logic ===")

    logger = get_logger("example.retry")

    # Example: Unreliable function
    def unreliable_function():
        """Function that fails 70% of the time"""
        if random.random() < 0.7:
            raise ConnectionError("Temporary connection failure")
        return "Operation successful!"

    # Method 1: Simple retry decorator
    @retry(max_attempts=3, backoff="exponential")
    def reliable_operation():
        return unreliable_function()

    try:
        result = reliable_operation()
        logger.info("Retry operation succeeded", result=result)
    except Exception as e:
        logger.error("Retry operation failed after all attempts", error=e)

    # Method 2: Using pre-configured policies
    @retry(policy=AGGRESSIVE_POLICY)
    def critical_operation():
        return unreliable_function()

    try:
        result = critical_operation()
        logger.info("Critical operation succeeded", result=result)
    except Exception as e:
        logger.error("Critical operation failed", error=e)

    print("✅ Retry logic examples completed")


def example_circuit_breaker():
    """Example 5: Circuit breaker pattern"""
    print("\n=== Example 5: Circuit Breaker ===")

    logger = get_logger("example.circuit_breaker")

    # Create circuit breaker
    circuit_breaker = CircuitBreaker(
        name="external_service",
        failure_threshold=3,
        timeout=5.0,  # Short timeout for demo
        half_open_max_calls=2,
    )

    def failing_service():
        """Service that always fails for demo"""
        raise ConnectionError("Service unavailable")

    # Wrap function with circuit breaker
    @circuit_breaker.decorator
    def external_service_call():
        return failing_service()

    # Try calling the service multiple times to trigger circuit breaker
    for i in range(7):
        try:
            result = external_service_call()
            logger.info(f"Call {i + 1} succeeded", result=result)
        except Exception as e:
            logger.warning(f"Call {i + 1} failed", error=str(e)[:50])

    # Check circuit breaker status
    status = circuit_breaker.get_status()
    print(f"Circuit breaker state: {status['state']}")
    print(f"Total requests: {status['metrics']['total_requests']}")
    print(f"Failed requests: {status['metrics']['failed_requests']}")

    print("✅ Circuit breaker examples completed")


async def example_health_checks():
    """Example 6: Health monitoring"""
    print("\n=== Example 6: Health Monitoring ===")

    logger = get_logger("example.health")

    # Get global health registry
    registry = get_health_registry()

    # Add basic system health checks
    registry.add_check(DiskHealthCheck("disk_space", path="/", warning_threshold=80.0))
    registry.add_check(MemoryHealthCheck("memory_usage", warning_threshold=80.0))

    # Add a custom HTTP health check (this will fail since it's a fake URL)
    registry.add_check(
        HTTPHealthCheck(
            name="external_api",
            url="https://httpbin.org/status/200",  # This should work
            timeout=5.0,
        )
    )

    # Run health checks
    health_report = await registry.check_health()

    logger.info(
        "Health check completed",
        overall_status=health_report.status.value,
        total_checks=len(health_report.checks),
        summary=health_report.summary,
    )

    # Print individual check results
    for check in health_report.checks:
        status_icon = "✅" if check.status == HealthStatus.HEALTHY else "❌"
        print(f"{status_icon} {check.name}: {check.status.value} - {check.message}")

    print("✅ Health monitoring examples completed")


def example_context_management():
    """Example 7: Context management and propagation"""
    print("\n=== Example 7: Context Management ===")

    logger = get_logger("example.context")

    # Create application context
    app_context = Context.new_context(
        service="example-service", environment="development", version="1.0.0"
    )

    # Create request context
    request = RequestContext.new_request()
    request.method = "POST"
    request.path = "/api/users"
    request.remote_addr = "192.168.1.100"

    # Create user context
    user = UserContext(
        user_id="user123",
        username="john_doe",
        email="john@example.com",
        roles=["user", "admin"],
    )

    # Create trace context
    trace = TraceContext.new_trace()

    # Build complete context
    complete_context = (
        app_context.with_request(request).with_user(user).with_trace(trace)
    )

    # Use context span for scoped execution
    with context_span(complete_context):
        current = get_context()
        if current:
            logger.info(
                "Processing request with full context",
                correlation_id=current.correlation_id,
                user_id=current.user.user_id if current.user else None,
                trace_id=current.trace.trace_id if current.trace else None,
                request_method=current.request.method if current.request else None,
            )

            # Simulate nested operation with new span
            new_span_trace = current.trace.new_span() if current.trace else None
            if new_span_trace:
                nested_context = current.with_trace(new_span_trace)
                with context_span(nested_context):
                    logger.info(
                        "Nested operation with child span",
                        parent_span=trace.span_id,
                        current_span=new_span_trace.span_id,
                    )

    print("✅ Context management examples completed")


async def example_integrated_patterns():
    """Example 8: Integrated patterns using multiple components"""
    print("\n=== Example 8: Integrated Patterns ===")

    logger = get_logger("example.integrated")

    # Set up application context
    app_context = Context.new_context(
        service="integrated-example", environment="development", version="1.0.0"
    )

    request = RequestContext.new_request()
    request.method = "POST"
    request.path = "/api/process"

    context_with_request = app_context.with_request(request)

    # Circuit breaker for external service
    external_cb = CircuitBreaker("payment_service", failure_threshold=2)

    @retry(max_attempts=3, backoff="exponential")
    @external_cb.decorator
    async def process_payment(amount: float):
        """Simulate payment processing with retry and circuit breaker"""
        # Simulate occasional failures
        if random.random() < 0.3:
            raise ConnectionError("Payment service temporarily unavailable")

        # Simulate processing time
        await asyncio.sleep(0.1)
        return {"transaction_id": f"txn_{random.randint(1000, 9999)}", "amount": amount}

    # Process with context
    with context_span(context_with_request):
        try:
            # Log start of processing
            logger.info("Starting payment processing", amount=100.0)

            # Process with retry and circuit breaker
            result = await process_payment(100.0)

            # Log success
            logger.info(
                "Payment processed successfully",
                transaction_id=result["transaction_id"],
                amount=result["amount"],
            )

        except GenesisError as e:
            # Handle Genesis errors specifically
            logger.error(
                "Genesis error during payment processing",
                error_code=e.code,
                error_category=e.category.value,
                correlation_id=e.context.correlation_id,
            )
        except Exception as e:
            # Handle other errors
            genesis_error = handle_error(e)
            logger.error(
                "Unexpected error during payment processing", error=genesis_error
            )

    print("✅ Integrated patterns examples completed")


async def main():
    """Main function to run all examples"""
    print("🚀 Genesis Core Usage Examples")
    print("=" * 50)

    # Run examples in sequence
    example_basic_setup()
    example_structured_logging()
    example_error_handling()
    example_retry_logic()
    example_circuit_breaker()

    # Async examples
    await example_health_checks()
    example_context_management()
    await example_integrated_patterns()

    print("\n" + "=" * 50)
    print("🎉 All examples completed successfully!")
    print("\nKey takeaways:")
    print("- Use configure_core() for easy setup")
    print("- Structured logging provides rich context")
    print("- Error handling with automatic categorization")
    print("- Retry logic and circuit breakers for resilience")
    print("- Health checks for monitoring")
    print("- Context management for tracing and correlation")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
