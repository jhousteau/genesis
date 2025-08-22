"""
Genesis Context Management

Provides context management for distributed applications with:
- Request context tracking
- Correlation ID management
- User session management
- Trace and span context
- Thread-safe context storage
- Context propagation patterns
"""

from .context import (
    Context,
    ContextManager,
    RequestContext,
    TraceContext,
    UserContext,
    clear_context,
    context_span,
    current_context,
    get_context,
    set_context,
)

__all__ = [
    # Core context classes
    "Context",
    "RequestContext",
    "UserContext",
    "TraceContext",
    # Context management
    "ContextManager",
    # Convenience functions
    "get_context",
    "set_context",
    "clear_context",
    "context_span",
    "current_context",
]
