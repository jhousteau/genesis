#!/usr/bin/env python3
"""
Genesis Microservice Template

Complete example showing how to build a production-ready microservice
using all Genesis Core components. This template includes:

- FastAPI web framework integration
- Request/response middleware with context
- Health check endpoints
- Error handling and structured logging
- Retry logic for external dependencies
- Circuit breakers for resilience
- Graceful shutdown handling

Usage:
    pip install fastapi uvicorn httpx
    python examples/microservice_template.py

Then visit:
    http://localhost:8000/docs - API documentation
    http://localhost:8000/health/liveness - Liveness probe
    http://localhost:8000/health/readiness - Readiness probe
"""

import asyncio
import signal
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Genesis Core imports
from core import (NETWORK_POLICY, CircuitBreaker, Context, ErrorCategory,
                  GenesisError, HealthStatus, HTTPHealthCheck, RequestContext,
                  TraceContext, UserContext, configure_core, context_span,
                  get_context, get_logger, get_service_health_registry,
                  handle_error, retry)
from core.health import KubernetesProbeHandler


# Pydantic models for API
class UserCreateRequest(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    created_at: str


class ErrorResponse(BaseModel):
    error: str
    code: str
    correlation_id: str
    details: Optional[Dict] = None


# Global components
health_registry = None
external_api_cb = None
database_cb = None
logger = None


async def setup_service():
    """Initialize service components"""
    global health_registry, external_api_cb, database_cb, logger

    # Configure Genesis Core
    configure_core(
        service_name="user-microservice",
        environment="production",
        version="1.2.0",
        log_level="INFO",
    )

    # Get configured logger
    logger = get_logger(__name__)

    # Setup health monitoring
    health_registry = get_service_health_registry()

    # Add application-specific health checks
    health_registry.add_check(
        HTTPHealthCheck(
            name="external_user_api",
            url="https://jsonplaceholder.typicode.com/users/1",
            timeout=5.0,
        )
    )

    # Setup circuit breakers
    external_api_cb = CircuitBreaker(
        name="external_api", failure_threshold=5, timeout=60.0, half_open_max_calls=3
    )

    database_cb = CircuitBreaker(
        name="database", failure_threshold=3, timeout=30.0, half_open_max_calls=2
    )

    logger.info("Service components initialized")


async def cleanup_service():
    """Cleanup service components"""
    global logger
    if logger:
        logger.info("Service shutting down gracefully")


# Lifespan manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await setup_service()
    yield
    # Shutdown
    await cleanup_service()


# Create FastAPI app
app = FastAPI(
    title="User Microservice",
    description="Example microservice built with Genesis Core components",
    version="1.2.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request context middleware
@app.middleware("http")
async def context_middleware(request: Request, call_next):
    """Add Genesis context to all requests"""

    # Extract headers for tracing
    correlation_id = request.headers.get("X-Correlation-ID")
    trace_id = request.headers.get("X-Trace-ID")
    user_id = request.headers.get("X-User-ID")

    # Create request context
    req_context = RequestContext(
        request_id=str(uuid.uuid4()),
        method=request.method,
        path=str(request.url.path),
        remote_addr=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        headers=dict(request.headers),
    )

    # Create base context
    app_context = Context.new_context(
        service="user-microservice",
        environment="production",
        version="1.2.0",
        correlation_id=correlation_id,
    )

    # Add request context
    context_with_request = app_context.with_request(req_context)

    # Add user context if user ID provided
    if user_id:
        user_context = UserContext(user_id=user_id)
        context_with_request = context_with_request.with_user(user_context)

    # Add trace context if trace ID provided
    if trace_id:
        trace_context = TraceContext(
            trace_id=trace_id, span_id=str(uuid.uuid4()).replace("-", "")[:16]
        )
        context_with_request = context_with_request.with_trace(trace_context)

    # Execute request within context
    try:
        with context_span(context_with_request):
            response = await call_next(request)

            # Add correlation ID to response headers
            current_context = get_context()
            if current_context:
                response.headers["X-Correlation-ID"] = current_context.correlation_id
                if current_context.trace:
                    response.headers["X-Trace-ID"] = current_context.trace.trace_id

            return response

    except Exception as e:
        # Handle unexpected errors
        genesis_error = handle_error(e)
        logger.error("Unhandled error in request processing", error=genesis_error)

        # Return structured error response
        return Response(
            content=ErrorResponse(
                error=genesis_error.message,
                code=genesis_error.code,
                correlation_id=genesis_error.context.correlation_id,
                details=genesis_error.details,
            ).model_dump_json(),
            status_code=500,
            media_type="application/json",
        )


# External service simulation
@retry(policy=NETWORK_POLICY)
@external_api_cb.decorator
async def fetch_external_user_data(user_id: str) -> Dict:
    """Fetch user data from external service with retry and circuit breaker"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://jsonplaceholder.typicode.com/users/{user_id}"
        )
        response.raise_for_status()
        return response.json()


# Database simulation
@retry(max_attempts=3, backoff="linear")
@database_cb.decorator
async def save_user_to_database(user_data: Dict) -> str:
    """Save user to database with retry and circuit breaker"""
    # Simulate database operation
    await asyncio.sleep(0.1)

    # Simulate occasional database errors
    import random

    if random.random() < 0.1:
        raise ConnectionError("Database connection timeout")

    # Return mock user ID
    return str(uuid.uuid4())


# API Routes
@app.get("/")
async def root():
    """Root endpoint"""
    current_context = get_context()
    logger.info("Root endpoint accessed")

    return {
        "service": "user-microservice",
        "version": "1.2.0",
        "status": "healthy",
        "correlation_id": current_context.correlation_id if current_context else None,
    }


@app.post("/users", response_model=UserResponse)
async def create_user(user: UserCreateRequest):
    """Create a new user"""
    current_context = get_context()
    logger.info("Creating new user", username=user.username, email=user.email)

    try:
        # Fetch additional data from external service (demonstration)
        external_data = await fetch_external_user_data("1")  # Mock external call

        # Save user to database
        user_id = await save_user_to_database(
            {
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "external_ref": external_data.get("id"),
            }
        )

        # Create response
        response = UserResponse(
            id=user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            created_at="2024-01-01T00:00:00Z",  # Mock timestamp
        )

        logger.info(
            "User created successfully", user_id=user_id, username=user.username
        )
        return response

    except GenesisError as e:
        logger.error(
            "Genesis error during user creation",
            error_code=e.code,
            error_category=e.category.value,
        )
        raise HTTPException(
            status_code=503 if e.category == ErrorCategory.EXTERNAL_SERVICE else 500,
            detail=ErrorResponse(
                error=e.message,
                code=e.code,
                correlation_id=e.context.correlation_id,
                details=e.details,
            ).model_dump(),
        )
    except Exception as e:
        genesis_error = handle_error(e)
        logger.error("Unexpected error during user creation", error=genesis_error)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=genesis_error.message,
                code=genesis_error.code,
                correlation_id=genesis_error.context.correlation_id,
            ).model_dump(),
        )


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID"""
    logger.info("Fetching user", user_id=user_id)

    try:
        # Simulate user fetch (in real app, this would query database)
        await asyncio.sleep(0.05)  # Simulate DB query time

        # Mock user data
        user_data = UserResponse(
            id=user_id,
            username=f"user_{user_id}",
            email=f"user_{user_id}@example.com",
            full_name=f"User {user_id}",
            created_at="2024-01-01T00:00:00Z",
        )

        logger.info("User fetched successfully", user_id=user_id)
        return user_data

    except Exception as e:
        genesis_error = handle_error(e)
        logger.error("Error fetching user", error=genesis_error, user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")


@app.get("/users", response_model=List[UserResponse])
async def list_users(limit: int = 10, offset: int = 0):
    """List users with pagination"""
    logger.info("Listing users", limit=limit, offset=offset)

    # Mock user list
    users = []
    for i in range(offset, offset + limit):
        users.append(
            UserResponse(
                id=str(uuid.uuid4()),
                username=f"user_{i}",
                email=f"user_{i}@example.com",
                full_name=f"User {i}",
                created_at="2024-01-01T00:00:00Z",
            )
        )

    logger.info("Users listed successfully", count=len(users))
    return users


# Health Check Endpoints
@app.get("/health/liveness")
async def liveness_probe():
    """Kubernetes liveness probe"""
    probe_handler = KubernetesProbeHandler(health_registry)
    result = await probe_handler.liveness_probe()

    if result["status"] == "ok":
        return result
    else:
        raise HTTPException(status_code=503, detail=result)


@app.get("/health/readiness")
async def readiness_probe():
    """Kubernetes readiness probe"""
    probe_handler = KubernetesProbeHandler(health_registry)
    result = await probe_handler.readiness_probe()

    if result["status"] == "ok":
        return result
    else:
        raise HTTPException(status_code=503, detail=result)


@app.get("/health/startup")
async def startup_probe():
    """Kubernetes startup probe"""
    probe_handler = KubernetesProbeHandler(health_registry)
    result = await probe_handler.startup_probe()

    if result["status"] == "ok":
        return result
    else:
        raise HTTPException(status_code=503, detail=result)


@app.get("/health")
async def detailed_health():
    """Detailed health status for monitoring"""
    health_report = await health_registry.check_health()

    # Convert to API response format
    response = {
        "status": health_report.status.value,
        "timestamp": health_report.timestamp.isoformat(),
        "service": "user-microservice",
        "version": "1.2.0",
        "checks": [check.to_dict() for check in health_report.checks],
        "summary": health_report.summary,
    }

    status_code = 200
    if health_report.status == HealthStatus.UNHEALTHY:
        status_code = 503
    elif health_report.status == HealthStatus.DEGRADED:
        status_code = 200  # Still accepting traffic but with warnings

    return Response(
        content=response, status_code=status_code, media_type="application/json"
    )


# Debug endpoints (only in development)
@app.get("/debug/context")
async def debug_context():
    """Debug endpoint to show current context"""
    current_context = get_context()
    if current_context:
        return current_context.to_dict()
    else:
        return {"error": "No context available"}


@app.get("/debug/circuit-breakers")
async def debug_circuit_breakers():
    """Debug endpoint to show circuit breaker status"""
    return {
        "external_api": external_api_cb.get_status() if external_api_cb else None,
        "database": database_cb.get_status() if database_cb else None,
    }


# Graceful shutdown handler
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    if logger:
        logger.info("Received shutdown signal", signal=signum)
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main function to run the microservice"""
    print("🚀 Starting User Microservice with Genesis Core")
    print("🔗 API Documentation: http://localhost:8000/docs")
    print("❤️  Health Check: http://localhost:8000/health")
    print("🛑 Graceful shutdown: Ctrl+C")

    # Run the service
    uvicorn.run(
        "microservice_template:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_config=None,  # Let Genesis handle logging
        access_log=False,  # Disable uvicorn access logs (we handle this in middleware)
    )


if __name__ == "__main__":
    main()
