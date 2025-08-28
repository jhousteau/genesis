"""
Genesis Context Management

Thread-safe context management for distributed applications with
correlation IDs, request tracking, and context propagation.
"""

from .manager import (
    RequestContext,
    TraceContext,
    ContextManager,
    get_context,
    set_context,
    clear_context,
    context_span,
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
    generate_request_id,
)

__all__ = [
    "RequestContext",
    "TraceContext",
    "ContextManager",
    "get_context",
    "set_context",
    "clear_context",
    "context_span",
    "get_correlation_id",
    "set_correlation_id",
    "generate_correlation_id",
    "generate_request_id",
]
