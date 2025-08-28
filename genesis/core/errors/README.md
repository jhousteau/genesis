# Error Framework

Structured error handling with context management and correlation tracking.

## Quick Start

```python
from genesis.core.errors import handle_error, ErrorCategory

try:
    risky_operation()
except Exception as e:
    handle_error(e, ErrorCategory.NETWORK, {"operation": "api_call"})
```

## Error Categories

- `INFRASTRUCTURE` - Infrastructure and deployment failures
- `NETWORK` - Network connectivity and timeout issues  
- `VALIDATION` - Input validation and data format errors
- `AUTHENTICATION` - Authentication and authorization failures
- `DATABASE` - Database connection and query errors
- `EXTERNAL_SERVICE` - Third-party service integration failures
- `FILE_SYSTEM` - File I/O and permission errors
- `CONFIGURATION` - Configuration and environment errors
- `BUSINESS_LOGIC` - Application logic and workflow errors
- `RESOURCE` - Resource exhaustion and limits
- `SECURITY` - Security violations and access control
- `CONCURRENCY` - Threading and async operation errors
- `INTEGRATION` - System integration and communication errors
- `UNKNOWN` - Uncategorized errors

## Features

- Automatic context enrichment
- Correlation ID tracking for request tracing
- Thread-safe error handling
- Integration with logging system
- Error categorization for monitoring