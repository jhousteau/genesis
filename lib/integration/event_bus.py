#!/usr/bin/env python3
"""
Event Bus - Pub/Sub Messaging System
Provides asynchronous, decoupled communication between components
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event priority levels"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    SYSTEM = 4  # Highest priority for system events


class EventType(Enum):
    """Standard event types"""

    # Lifecycle events
    COMPONENT_STARTED = "component.started"
    COMPONENT_STOPPED = "component.stopped"
    COMPONENT_ERROR = "component.error"
    COMPONENT_HEALTH = "component.health"

    # Configuration events
    CONFIG_CHANGED = "config.changed"
    CONFIG_RELOADED = "config.reloaded"

    # Deployment events
    DEPLOY_STARTED = "deploy.started"
    DEPLOY_COMPLETED = "deploy.completed"
    DEPLOY_FAILED = "deploy.failed"
    ROLLBACK_INITIATED = "rollback.initiated"

    # Monitoring events
    METRIC_THRESHOLD = "metric.threshold"
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"

    # Intelligence events
    ANOMALY_DETECTED = "anomaly.detected"
    OPTIMIZATION_SUGGESTED = "optimization.suggested"
    AUTO_FIX_APPLIED = "auto_fix.applied"

    # Security events
    SECURITY_VIOLATION = "security.violation"
    ACCESS_DENIED = "access.denied"
    CREDENTIAL_ROTATED = "credential.rotated"

    # Custom events
    CUSTOM = "custom"


@dataclass
class Event:
    """Represents an event in the system"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: Union[EventType, str] = EventType.CUSTOM
    source: str = "unknown"
    target: Optional[str] = None  # None means broadcast
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: EventPriority = EventPriority.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl: Optional[int] = None  # Time to live in seconds

    def is_expired(self) -> bool:
        """Check if event has expired"""
        if not self.ttl:
            return False

        event_time = datetime.fromisoformat(self.timestamp)
        return datetime.now() - event_time > timedelta(seconds=self.ttl)

    def to_json(self) -> str:
        """Convert event to JSON string"""
        data = asdict(self)
        if isinstance(data["type"], EventType):
            data["type"] = data["type"].value
        if isinstance(data["priority"], EventPriority):
            data["priority"] = data["priority"].value
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Create event from JSON string"""
        data = json.loads(json_str)

        # Convert string types back to enums
        if "type" in data:
            try:
                data["type"] = EventType(data["type"])
            except ValueError:
                data["type"] = EventType.CUSTOM

        if "priority" in data:
            try:
                data["priority"] = EventPriority(data["priority"])
            except (ValueError, TypeError):
                data["priority"] = EventPriority.NORMAL

        return cls(**data)


@dataclass
class Subscription:
    """Represents a subscription to events"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subscriber_id: str = "unknown"
    pattern: str = "*"  # Event pattern to match (supports wildcards)
    callback: Optional[Callable] = None
    async_callback: Optional[Callable] = None
    filter_func: Optional[Callable] = None
    priority_threshold: EventPriority = EventPriority.LOW
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    active: bool = True

    def matches(self, event: Event) -> bool:
        """Check if event matches subscription criteria"""
        if not self.active:
            return False

        # Check priority threshold
        if event.priority.value < self.priority_threshold.value:
            return False

        # Check pattern matching
        if not self._pattern_matches(event):
            return False

        # Apply custom filter if provided
        if self.filter_func:
            try:
                return self.filter_func(event)
            except Exception as e:
                logger.error(f"Filter function error: {e}")
                return False

        return True

    def _pattern_matches(self, event: Event) -> bool:
        """Check if event matches pattern"""
        if self.pattern == "*":
            return True

        event_type = (
            event.type.value if isinstance(event.type, EventType) else str(event.type)
        )

        # Simple wildcard matching
        if self.pattern.endswith("*"):
            prefix = self.pattern[:-1]
            return event_type.startswith(prefix)
        elif self.pattern.startswith("*"):
            suffix = self.pattern[1:]
            return event_type.endswith(suffix)
        else:
            return event_type == self.pattern


class EventBus:
    """
    Central event bus for pub/sub messaging
    Supports both sync and async handlers
    """

    def __init__(self, max_queue_size: int = 10000, enable_persistence: bool = False):
        """Initialize the event bus"""
        self.subscriptions: Dict[str, Subscription] = {}
        self.subscription_lock = threading.RLock()

        # Event queues by priority
        self.event_queues: Dict[EventPriority, deque] = {
            priority: deque(maxlen=max_queue_size // 5) for priority in EventPriority
        }
        self.queue_lock = threading.RLock()

        # Event history
        self.event_history: deque = deque(maxlen=1000)
        self.enable_persistence = enable_persistence

        # Statistics
        self.stats = {
            "events_published": 0,
            "events_delivered": 0,
            "events_dropped": 0,
            "events_failed": 0,
            "subscriptions_created": 0,
            "subscriptions_removed": 0,
        }

        # Dead letter queue for failed events
        self.dead_letter_queue: deque = deque(maxlen=1000)

        # Start event processing
        self.processing = True
        self.event_loop = None
        self._start_event_processing()

    def _start_event_processing(self):
        """Start background event processing"""

        def process_events():
            """Synchronous event processing"""
            while self.processing:
                try:
                    event = self._get_next_event()
                    if event:
                        self._process_event(event)
                    else:
                        time.sleep(0.01)  # Short sleep if no events
                except Exception as e:
                    logger.error(f"Event processing error: {e}")

        # Start sync processing thread
        thread = threading.Thread(target=process_events, daemon=True)
        thread.start()

        # Start async processing if event loop available
        try:
            self.event_loop = asyncio.new_event_loop()

            async def async_process_events():
                while self.processing:
                    try:
                        await asyncio.sleep(0.01)
                        # Process async callbacks
                    except Exception as e:
                        logger.error(f"Async event processing error: {e}")

            asyncio.set_event_loop(self.event_loop)
            asyncio.ensure_future(async_process_events(), loop=self.event_loop)

            def run_loop():
                self.event_loop.run_forever()

            thread = threading.Thread(target=run_loop, daemon=True)
            thread.start()
        except Exception as e:
            logger.warning(f"Could not start async event processing: {e}")

    def publish(
        self,
        event_type: Union[EventType, str],
        data: Dict[str, Any],
        source: str = "unknown",
        target: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """
        Publish an event to the bus
        Returns the event ID
        """
        # Create event
        event = Event(
            type=event_type,
            source=source,
            target=target,
            data=data,
            priority=priority,
            correlation_id=correlation_id,
            ttl=ttl,
        )

        # Add to appropriate queue
        with self.queue_lock:
            self.event_queues[priority].append(event)
            self.stats["events_published"] += 1

        # Add to history
        self.event_history.append(event)

        # Persist if enabled
        if self.enable_persistence:
            self._persist_event(event)

        logger.debug(f"Published event: {event.id} type={event_type} from={source}")

        return event.id

    def subscribe(
        self,
        pattern: str = "*",
        callback: Optional[Callable] = None,
        async_callback: Optional[Callable] = None,
        subscriber_id: str = "unknown",
        filter_func: Optional[Callable] = None,
        priority_threshold: EventPriority = EventPriority.LOW,
    ) -> str:
        """
        Subscribe to events matching pattern
        Returns subscription ID
        """
        if not callback and not async_callback:
            raise ValueError("Either callback or async_callback must be provided")

        subscription = Subscription(
            subscriber_id=subscriber_id,
            pattern=pattern,
            callback=callback,
            async_callback=async_callback,
            filter_func=filter_func,
            priority_threshold=priority_threshold,
        )

        with self.subscription_lock:
            self.subscriptions[subscription.id] = subscription
            self.stats["subscriptions_created"] += 1

        logger.info(
            f"Created subscription: {subscription.id} for {subscriber_id} pattern={pattern}"
        )

        return subscription.id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        with self.subscription_lock:
            if subscription_id in self.subscriptions:
                del self.subscriptions[subscription_id]
                self.stats["subscriptions_removed"] += 1
                logger.info(f"Removed subscription: {subscription_id}")
                return True
        return False

    def _get_next_event(self) -> Optional[Event]:
        """Get next event to process (priority-based)"""
        with self.queue_lock:
            # Process in priority order
            for priority in reversed(list(EventPriority)):
                queue = self.event_queues[priority]
                if queue:
                    return queue.popleft()
        return None

    def _process_event(self, event: Event):
        """Process a single event"""
        # Skip expired events
        if event.is_expired():
            self.stats["events_dropped"] += 1
            return

        # Find matching subscriptions
        matching_subs = []
        with self.subscription_lock:
            for sub in self.subscriptions.values():
                if sub.matches(event):
                    matching_subs.append(sub)

        # Deliver to subscribers
        for sub in matching_subs:
            try:
                if event.target and sub.subscriber_id != event.target:
                    continue  # Skip if targeted to different subscriber

                if sub.callback:
                    # Synchronous callback
                    sub.callback(event)
                    self.stats["events_delivered"] += 1

                if sub.async_callback and self.event_loop:
                    # Asynchronous callback
                    asyncio.run_coroutine_threadsafe(
                        sub.async_callback(event), self.event_loop
                    )
                    self.stats["events_delivered"] += 1

            except Exception as e:
                logger.error(f"Error delivering event to {sub.subscriber_id}: {e}")
                self.stats["events_failed"] += 1

                # Add to dead letter queue
                self.dead_letter_queue.append(
                    {
                        "event": event,
                        "subscription": sub.id,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    def request_reply(
        self,
        event_type: Union[EventType, str],
        data: Dict[str, Any],
        source: str,
        target: str,
        timeout: float = 5.0,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> Optional[Event]:
        """
        Send event and wait for reply (synchronous RPC-style)
        """
        correlation_id = str(uuid.uuid4())
        reply_event = None
        reply_received = threading.Event()

        def reply_handler(event: Event):
            nonlocal reply_event
            if event.correlation_id == correlation_id:
                reply_event = event
                reply_received.set()

        # Subscribe to replies
        sub_id = self.subscribe(
            pattern="reply.*",
            callback=reply_handler,
            subscriber_id=source,
            filter_func=lambda e: e.correlation_id == correlation_id,
        )

        try:
            # Publish request
            self.publish(
                event_type=event_type,
                data=data,
                source=source,
                target=target,
                priority=priority,
                correlation_id=correlation_id,
            )

            # Wait for reply
            if reply_received.wait(timeout):
                return reply_event
            else:
                logger.warning(f"Request timeout: {event_type} to {target}")
                return None

        finally:
            # Cleanup subscription
            self.unsubscribe(sub_id)

    def reply(self, original_event: Event, data: Dict[str, Any], source: str):
        """Reply to an event"""
        self.publish(
            event_type=f"reply.{original_event.type}",
            data=data,
            source=source,
            target=original_event.source,
            correlation_id=original_event.correlation_id or original_event.id,
            priority=original_event.priority,
        )

    def broadcast(
        self,
        event_type: Union[EventType, str],
        data: Dict[str, Any],
        source: str = "system",
        priority: EventPriority = EventPriority.NORMAL,
    ):
        """Broadcast event to all subscribers"""
        self.publish(
            event_type=event_type,
            data=data,
            source=source,
            target=None,  # Broadcast
            priority=priority,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self.queue_lock:
            queue_sizes = {
                priority.name: len(queue)
                for priority, queue in self.event_queues.items()
            }

        with self.subscription_lock:
            subscription_count = len(self.subscriptions)
            subscribers = defaultdict(int)
            for sub in self.subscriptions.values():
                subscribers[sub.subscriber_id] += 1

        return {
            "timestamp": datetime.now().isoformat(),
            "statistics": self.stats.copy(),
            "queue_sizes": queue_sizes,
            "total_subscriptions": subscription_count,
            "subscribers": dict(subscribers),
            "event_history_size": len(self.event_history),
            "dead_letter_queue_size": len(self.dead_letter_queue),
        }

    def get_event_history(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[Event]:
        """Get recent event history"""
        history = list(self.event_history)

        # Filter if needed
        if event_type:
            history = [e for e in history if str(e.type) == event_type]
        if source:
            history = [e for e in history if e.source == source]

        # Return most recent events
        return history[-limit:]

    def get_dead_letters(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get failed events from dead letter queue"""
        return list(self.dead_letter_queue)[-limit:]

    def clear_dead_letters(self):
        """Clear the dead letter queue"""
        self.dead_letter_queue.clear()

    def _persist_event(self, event: Event):
        """Persist event to storage (if enabled)"""
        try:
            # This could write to file, database, etc.
            # For now, just log it
            logger.debug(f"Persisting event: {event.id}")
        except Exception as e:
            logger.error(f"Failed to persist event: {e}")

    def shutdown(self):
        """Shutdown the event bus"""
        self.processing = False

        if self.event_loop:
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)

        logger.info("Event bus shutdown complete")


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish_event(**kwargs) -> str:
    """Convenience function to publish an event"""
    return get_event_bus().publish(**kwargs)


def subscribe_to_events(**kwargs) -> str:
    """Convenience function to subscribe to events"""
    return get_event_bus().subscribe(**kwargs)


def broadcast_event(**kwargs):
    """Convenience function to broadcast an event"""
    get_event_bus().broadcast(**kwargs)
