"""
Log Correlation and Tracing System
Correlates logs across services using trace IDs and request context.
"""

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    from google.cloud import logging as gcp_logging
    from google.cloud import trace

    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

try:
    import elasticsearch
    from elasticsearch import Elasticsearch

    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False


@dataclass
class LogEntry:
    """Represents a log entry with correlation information."""

    timestamp: datetime
    level: str
    message: str
    service_name: str
    trace_id: str
    span_id: str
    correlation_id: str
    user_id: str = ""
    session_id: str = ""
    request_id: str = ""
    parent_span_id: str = ""
    labels: Dict[str, Any] = field(default_factory=dict)
    raw_log: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceContext:
    """Trace context information for log correlation."""

    trace_id: str
    correlation_id: str
    service_chain: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    user_id: str = ""
    session_id: str = ""
    request_path: str = ""
    error_count: int = 0
    total_duration_ms: float = 0.0


class LogCorrelator:
    """Correlates logs across services using trace and correlation IDs."""

    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self.trace_contexts: Dict[str, TraceContext] = {}
        self.log_entries: List[LogEntry] = []

        # Initialize clients
        if GCP_AVAILABLE and project_id:
            self.gcp_logging_client = gcp_logging.Client(project=project_id)
            self.trace_client = trace.TraceServiceV2Client()

        # Initialize Elasticsearch if available
        self.elasticsearch_client = None
        if ELASTICSEARCH_AVAILABLE:
            try:
                self.elasticsearch_client = Elasticsearch(
                    [{"host": "localhost", "port": 9200}]
                )
            except Exception:
                pass

    def parse_log_entry(self, log_data: Dict[str, Any]) -> Optional[LogEntry]:
        """Parse a log entry and extract correlation information."""
        try:
            # Extract timestamp
            timestamp = log_data.get("timestamp", "")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now()

            # Extract basic fields
            level = log_data.get("level", "INFO")
            message = log_data.get("message", "")
            service_name = log_data.get("service", {}).get("name", "unknown")

            # Extract correlation IDs from various sources
            request_info = log_data.get("request", {})
            trace_id = (
                request_info.get("trace_id")
                or log_data.get("traceId")
                or log_data.get("trace_id")
                or self._extract_trace_id_from_message(message)
                or ""
            )

            span_id = (
                request_info.get("span_id")
                or log_data.get("spanId")
                or log_data.get("span_id")
                or ""
            )

            correlation_id = (
                request_info.get("correlation_id")
                or log_data.get("correlationId")
                or log_data.get("correlation_id")
                or log_data.get("requestId")
                or ""
            )

            # Extract user context
            user_info = log_data.get("user", {})
            user_id = (
                user_info.get("user_id")
                or log_data.get("userId")
                or log_data.get("user_id")
                or ""
            )

            session_id = (
                user_info.get("session_id")
                or log_data.get("sessionId")
                or log_data.get("session_id")
                or ""
            )

            request_id = (
                request_info.get("request_id")
                or log_data.get("requestId")
                or log_data.get("request_id")
                or ""
            )

            parent_span_id = (
                request_info.get("parent_span_id")
                or log_data.get("parentSpanId")
                or log_data.get("parent_span_id")
                or ""
            )

            # Extract labels
            labels = log_data.get("labels", {})
            if "kubernetes" in log_data:
                k8s_labels = log_data["kubernetes"].get("labels", {})
                labels.update(k8s_labels)

            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                service_name=service_name,
                trace_id=trace_id,
                span_id=span_id,
                correlation_id=correlation_id,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                parent_span_id=parent_span_id,
                labels=labels,
                raw_log=log_data,
            )

        except Exception as e:
            logging.error(f"Failed to parse log entry: {e}")
            return None

    def _extract_trace_id_from_message(self, message: str) -> str:
        """Extract trace ID from log message using regex patterns."""
        # Common trace ID patterns
        patterns = [
            r'trace[_-]?id[":\\s]*([a-f0-9]{32})',
            r'traceId[":\\s]*([a-f0-9]{32})',
            r'trace[":\\s]*([a-f0-9]{32})',
            r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
            r"([a-f0-9]{32})",
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)

        return ""

    def correlate_logs(
        self, log_entries: List[Dict[str, Any]]
    ) -> Dict[str, List[LogEntry]]:
        """Correlate logs by trace ID and correlation ID."""
        correlated_logs = defaultdict(list)

        for log_data in log_entries:
            log_entry = self.parse_log_entry(log_data)
            if not log_entry:
                continue

            self.log_entries.append(log_entry)

            # Use trace_id as primary correlation key
            correlation_key = log_entry.trace_id or log_entry.correlation_id
            if correlation_key:
                correlated_logs[correlation_key].append(log_entry)
                self._update_trace_context(log_entry)

        return dict(correlated_logs)

    def _update_trace_context(self, log_entry: LogEntry):
        """Update trace context with information from log entry."""
        trace_key = log_entry.trace_id or log_entry.correlation_id
        if not trace_key:
            return

        if trace_key not in self.trace_contexts:
            self.trace_contexts[trace_key] = TraceContext(
                trace_id=log_entry.trace_id,
                correlation_id=log_entry.correlation_id,
                start_time=log_entry.timestamp,
                user_id=log_entry.user_id,
                session_id=log_entry.session_id,
            )

        context = self.trace_contexts[trace_key]

        # Update service chain
        if log_entry.service_name not in context.service_chain:
            context.service_chain.append(log_entry.service_name)

        # Update timing
        if log_entry.timestamp < context.start_time:
            context.start_time = log_entry.timestamp

        if not context.end_time or log_entry.timestamp > context.end_time:
            context.end_time = log_entry.timestamp

        # Count errors
        if log_entry.level in ["ERROR", "CRITICAL", "FATAL"]:
            context.error_count += 1

        # Extract request path from first log entry
        if not context.request_path and "http_path" in log_entry.labels:
            context.request_path = log_entry.labels["http_path"]

    def get_trace_timeline(
        self, trace_id: str, time_window_minutes: int = 30
    ) -> List[LogEntry]:
        """Get chronologically ordered logs for a trace."""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_window_minutes)

        trace_logs = [
            entry
            for entry in self.log_entries
            if (entry.trace_id == trace_id or entry.correlation_id == trace_id)
            and start_time <= entry.timestamp <= end_time
        ]

        return sorted(trace_logs, key=lambda x: x.timestamp)

    def find_error_chains(
        self, time_window_minutes: int = 30
    ) -> Dict[str, List[LogEntry]]:
        """Find chains of errors across services."""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_window_minutes)

        error_chains = {}

        for trace_id, context in self.trace_contexts.items():
            if context.error_count > 0 and context.start_time >= start_time:
                error_logs = [
                    entry
                    for entry in self.log_entries
                    if (entry.trace_id == trace_id or entry.correlation_id == trace_id)
                    and entry.level in ["ERROR", "CRITICAL", "FATAL"]
                ]

                if error_logs:
                    error_chains[trace_id] = sorted(
                        error_logs, key=lambda x: x.timestamp
                    )

        return error_chains

    def analyze_service_dependencies(
        self, time_window_hours: int = 24
    ) -> Dict[str, List[str]]:
        """Analyze service dependencies based on trace flows."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_window_hours)

        dependencies = defaultdict(set)

        for context in self.trace_contexts.values():
            if context.start_time >= start_time and len(context.service_chain) > 1:
                for i in range(len(context.service_chain) - 1):
                    caller = context.service_chain[i]
                    callee = context.service_chain[i + 1]
                    dependencies[caller].add(callee)

        return {k: list(v) for k, v in dependencies.items()}

    def get_request_flow_summary(self, trace_id: str) -> Dict[str, Any]:
        """Get a summary of the request flow for a trace."""
        if trace_id not in self.trace_contexts:
            return {}

        context = self.trace_contexts[trace_id]
        trace_logs = self.get_trace_timeline(trace_id, 60)  # 1 hour window

        # Calculate total duration
        if context.end_time and context.start_time:
            total_duration = (
                context.end_time - context.start_time
            ).total_seconds() * 1000
        else:
            total_duration = 0

        # Service timing breakdown
        service_timings = defaultdict(list)
        for log in trace_logs:
            if "duration_ms" in log.labels:
                try:
                    duration = float(log.labels["duration_ms"])
                    service_timings[log.service_name].append(duration)
                except (ValueError, TypeError):
                    pass

        service_stats = {}
        for service, durations in service_timings.items():
            service_stats[service] = {
                "count": len(durations),
                "total_ms": sum(durations),
                "avg_ms": sum(durations) / len(durations),
                "max_ms": max(durations),
                "min_ms": min(durations),
            }

        return {
            "trace_id": trace_id,
            "correlation_id": context.correlation_id,
            "user_id": context.user_id,
            "session_id": context.session_id,
            "request_path": context.request_path,
            "start_time": context.start_time.isoformat(),
            "end_time": context.end_time.isoformat() if context.end_time else None,
            "total_duration_ms": total_duration,
            "service_chain": context.service_chain,
            "error_count": context.error_count,
            "log_count": len(trace_logs),
            "service_stats": service_stats,
            "status": "error" if context.error_count > 0 else "success",
        }

    def search_correlated_logs(
        self, query: str, time_window_hours: int = 24, include_context: bool = True
    ) -> List[Dict[str, Any]]:
        """Search for logs and include correlated context."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_window_hours)

        # Simple text search in messages
        matching_logs = [
            entry
            for entry in self.log_entries
            if query.lower() in entry.message.lower()
            and start_time <= entry.timestamp <= end_time
        ]

        results = []
        for log_entry in matching_logs:
            result = {
                "log": {
                    "timestamp": log_entry.timestamp.isoformat(),
                    "level": log_entry.level,
                    "message": log_entry.message,
                    "service": log_entry.service_name,
                    "trace_id": log_entry.trace_id,
                    "correlation_id": log_entry.correlation_id,
                    "user_id": log_entry.user_id,
                    "labels": log_entry.labels,
                }
            }

            # Add correlated context if requested
            if include_context:
                trace_key = log_entry.trace_id or log_entry.correlation_id
                if trace_key:
                    context = self.get_request_flow_summary(trace_key)
                    result["context"] = context

                    # Add related logs
                    related_logs = self.get_trace_timeline(trace_key, 30)
                    result["related_logs"] = [
                        {
                            "timestamp": log.timestamp.isoformat(),
                            "level": log.level,
                            "message": log.message,
                            "service": log.service_name,
                        }
                        for log in related_logs
                        if log != log_entry
                    ][:10]  # Limit to 10 related logs

            results.append(result)

        return results

    def export_trace_data(self, trace_id: str, format: str = "json") -> str:
        """Export trace data in specified format."""
        trace_data = self.get_request_flow_summary(trace_id)
        trace_logs = self.get_trace_timeline(trace_id, 60)

        export_data = {
            "trace_summary": trace_data,
            "logs": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "level": log.level,
                    "message": log.message,
                    "service": log.service_name,
                    "span_id": log.span_id,
                    "parent_span_id": log.parent_span_id,
                    "labels": log.labels,
                }
                for log in trace_logs
            ],
        }

        if format == "json":
            return json.dumps(export_data, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Convenience functions
def create_log_correlator(project_id: str = None) -> LogCorrelator:
    """Create a log correlator with default configuration."""
    return LogCorrelator(project_id)


def correlate_request_logs(
    log_data: List[Dict[str, Any]], project_id: str = None
) -> Dict[str, Any]:
    """Convenience function to correlate a batch of logs."""
    correlator = LogCorrelator(project_id)
    correlated = correlator.correlate_logs(log_data)

    # Generate summary
    summary = {
        "total_logs": len(log_data),
        "correlated_traces": len(correlated),
        "traces": [],
    }

    for trace_id, logs in correlated.items():
        trace_summary = correlator.get_request_flow_summary(trace_id)
        summary["traces"].append(trace_summary)

    return summary


def find_error_root_cause(
    error_trace_id: str, log_data: List[Dict[str, Any]], project_id: str = None
) -> Dict[str, Any]:
    """Find the root cause of an error by analyzing the trace."""
    correlator = LogCorrelator(project_id)
    correlator.correlate_logs(log_data)

    trace_logs = correlator.get_trace_timeline(error_trace_id, 60)
    error_logs = [
        log for log in trace_logs if log.level in ["ERROR", "CRITICAL", "FATAL"]
    ]

    if not error_logs:
        return {"error": "No error logs found for trace"}

    # Find the first error (likely root cause)
    root_error = min(error_logs, key=lambda x: x.timestamp)

    # Get context around the root error
    error_time = root_error.timestamp
    context_start = error_time - timedelta(minutes=5)
    context_end = error_time + timedelta(minutes=1)

    context_logs = [
        log for log in trace_logs if context_start <= log.timestamp <= context_end
    ]

    return {
        "root_error": {
            "timestamp": root_error.timestamp.isoformat(),
            "service": root_error.service_name,
            "message": root_error.message,
            "level": root_error.level,
            "span_id": root_error.span_id,
        },
        "context_logs": [
            {
                "timestamp": log.timestamp.isoformat(),
                "service": log.service_name,
                "level": log.level,
                "message": log.message,
            }
            for log in sorted(context_logs, key=lambda x: x.timestamp)
        ],
        "trace_summary": correlator.get_request_flow_summary(error_trace_id),
    }
