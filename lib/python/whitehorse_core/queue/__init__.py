"""
Queue Module

Message queue abstraction supporting Google Cloud Pub/Sub, Cloud Tasks,
Redis queues, and in-memory queues for reliable message processing.
"""

import json
import pickle
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import Enum
from queue import Empty, Full
from queue import Queue as ThreadQueue
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from google.cloud import pubsub_v1, tasks_v2

    HAS_GCP_PUBSUB = True
except ImportError:
    HAS_GCP_PUBSUB = False

try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

from ..errors import SystemError
from ..logging import get_logger

logger = get_logger(__name__)


class MessageStatus(Enum):
    """Message processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


@dataclass
class Message:
    """Queue message representation."""

    id: str
    data: Any
    attributes: Dict[str, str]
    publish_time: float
    delivery_attempt: int = 1
    status: MessageStatus = MessageStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "data": self.data,
            "attributes": self.attributes,
            "publish_time": self.publish_time,
            "delivery_attempt": self.delivery_attempt,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            data=data["data"],
            attributes=data["attributes"],
            publish_time=data["publish_time"],
            delivery_attempt=data.get("delivery_attempt", 1),
            status=MessageStatus(data.get("status", "pending")),
        )


@dataclass
class QueueStats:
    """Queue statistics."""

    messages_published: int = 0
    messages_consumed: int = 0
    messages_acked: int = 0
    messages_nacked: int = 0
    messages_failed: int = 0
    current_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MessageHandler:
    """Base message handler interface."""

    def handle(self, message: Message) -> bool:
        """
        Handle a message.

        Returns:
            True if message was processed successfully, False otherwise
        """
        raise NotImplementedError

    def on_error(self, message: Message, error: Exception) -> None:
        """Called when message processing fails."""
        logger.error(f"Message processing failed: {error}", message_id=message.id)


class Queue(ABC):
    """Abstract queue interface."""

    @abstractmethod
    def publish(self, data: Any, attributes: Optional[Dict[str, str]] = None) -> str:
        """Publish a message to the queue."""
        pass

    @abstractmethod
    def consume(self, handler: MessageHandler, max_messages: int = 1) -> List[Message]:
        """Consume messages from the queue."""
        pass

    @abstractmethod
    def ack(self, message_id: str) -> bool:
        """Acknowledge message processing."""
        pass

    @abstractmethod
    def nack(self, message_id: str) -> bool:
        """Negative acknowledge (reject) message."""
        pass

    @abstractmethod
    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        pass

    @abstractmethod
    def purge(self) -> bool:
        """Purge all messages from queue."""
        pass


class InMemoryQueue(Queue):
    """In-memory queue implementation."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queue = ThreadQueue(maxsize=max_size)
        self._pending_acks: Dict[str, Message] = {}
        self._stats = QueueStats()
        self._lock = threading.Lock()

        logger.info(f"Initialized in-memory queue with max_size={max_size}")

    def publish(self, data: Any, attributes: Optional[Dict[str, str]] = None) -> str:
        """Publish message to in-memory queue."""
        message = Message(
            id=str(uuid.uuid4()),
            data=data,
            attributes=attributes or {},
            publish_time=time.time(),
        )

        try:
            self._queue.put(message, block=False)
            with self._lock:
                self._stats.messages_published += 1
                self._stats.current_size += 1

            logger.debug("Published message to in-memory queue", message_id=message.id)
            return message.id

        except Full:
            logger.error("In-memory queue is full")
            raise SystemError("Queue is full")

    def consume(self, handler: MessageHandler, max_messages: int = 1) -> List[Message]:
        """Consume messages from in-memory queue."""
        messages = []

        for _ in range(max_messages):
            try:
                message = self._queue.get(block=False)
                message.status = MessageStatus.PROCESSING

                # Store for acknowledgment
                with self._lock:
                    self._pending_acks[message.id] = message
                    self._stats.messages_consumed += 1
                    self._stats.current_size -= 1

                # Process message
                try:
                    success = handler.handle(message)
                    if success:
                        self.ack(message.id)
                    else:
                        self.nack(message.id)
                except Exception as e:
                    handler.on_error(message, e)
                    self.nack(message.id)

                messages.append(message)

            except Empty:
                break

        return messages

    def ack(self, message_id: str) -> bool:
        """Acknowledge message processing."""
        with self._lock:
            if message_id in self._pending_acks:
                message = self._pending_acks.pop(message_id)
                message.status = MessageStatus.COMPLETED
                self._stats.messages_acked += 1
                logger.debug("Acknowledged message", message_id=message_id)
                return True
            return False

    def nack(self, message_id: str) -> bool:
        """Negative acknowledge message."""
        with self._lock:
            if message_id in self._pending_acks:
                message = self._pending_acks.pop(message_id)
                message.status = MessageStatus.FAILED
                message.delivery_attempt += 1

                # Re-queue for retry (simple strategy)
                if message.delivery_attempt <= 3:
                    try:
                        message.status = MessageStatus.RETRYING
                        self._queue.put(message, block=False)
                        self._stats.current_size += 1
                    except Full:
                        message.status = MessageStatus.DEAD_LETTER
                        self._stats.messages_failed += 1
                else:
                    message.status = MessageStatus.DEAD_LETTER
                    self._stats.messages_failed += 1

                self._stats.messages_nacked += 1
                logger.debug("Negative acknowledged message", message_id=message_id)
                return True
            return False

    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        with self._lock:
            stats = self._stats
            stats.current_size = self._queue.qsize()
            return stats

    def purge(self) -> bool:
        """Purge all messages."""
        with self._lock:
            # Clear the queue
            while not self._queue.empty():
                try:
                    self._queue.get(block=False)
                except Empty:
                    break

            # Clear pending acks
            self._pending_acks.clear()

            # Reset stats
            self._stats.current_size = 0

            logger.info("Purged in-memory queue")
            return True


class RedisQueue(Queue):
    """Redis-based queue implementation."""

    def __init__(
        self,
        queue_name: str,
        redis_client: Optional[redis.Redis] = None,
        redis_url: Optional[str] = None,
    ):
        if not HAS_REDIS:
            raise ImportError("Redis library not available")

        self.queue_name = queue_name
        self.pending_key = f"{queue_name}:pending"
        self.processing_key = f"{queue_name}:processing"
        self.stats_key = f"{queue_name}:stats"

        if redis_client:
            self.client = redis_client
        elif redis_url:
            self.client = redis.from_url(redis_url)
        else:
            self.client = redis.Redis(decode_responses=False)

        try:
            self.client.ping()
            logger.info(f"Initialized Redis queue: {queue_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _serialize_message(self, message: Message) -> bytes:
        """Serialize message for storage."""
        return pickle.dumps(message)

    def _deserialize_message(self, data: bytes) -> Message:
        """Deserialize message from storage."""
        return pickle.loads(data)

    def publish(self, data: Any, attributes: Optional[Dict[str, str]] = None) -> str:
        """Publish message to Redis queue."""
        message = Message(
            id=str(uuid.uuid4()),
            data=data,
            attributes=attributes or {},
            publish_time=time.time(),
        )

        try:
            serialized = self._serialize_message(message)
            self.client.lpush(self.pending_key, serialized)
            self.client.hincrby(self.stats_key, "messages_published", 1)

            logger.debug("Published message to Redis queue", message_id=message.id)
            return message.id

        except Exception as e:
            logger.error(f"Failed to publish message to Redis queue: {e}")
            raise SystemError(f"Failed to publish message: {e}")

    def consume(self, handler: MessageHandler, max_messages: int = 1) -> List[Message]:
        """Consume messages from Redis queue."""
        messages = []

        for _ in range(max_messages):
            try:
                # Move message from pending to processing
                serialized = self.client.brpoplpush(
                    self.pending_key, self.processing_key, timeout=1
                )

                if not serialized:
                    break

                message = self._deserialize_message(serialized)
                message.status = MessageStatus.PROCESSING

                self.client.hincrby(self.stats_key, "messages_consumed", 1)

                # Process message
                try:
                    success = handler.handle(message)
                    if success:
                        self.ack(message.id)
                    else:
                        self.nack(message.id)
                except Exception as e:
                    handler.on_error(message, e)
                    self.nack(message.id)

                messages.append(message)

            except Exception as e:
                logger.error(f"Failed to consume message from Redis queue: {e}")
                break

        return messages

    def ack(self, message_id: str) -> bool:
        """Acknowledge message processing."""
        try:
            # Remove from processing queue
            # Note: This is simplified - in production, you'd want to find and remove the specific message
            self.client.hincrby(self.stats_key, "messages_acked", 1)
            logger.debug("Acknowledged message", message_id=message_id)
            return True
        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            return False

    def nack(self, message_id: str) -> bool:
        """Negative acknowledge message."""
        try:
            # Move back to pending for retry (simplified)
            self.client.hincrby(self.stats_key, "messages_nacked", 1)
            logger.debug("Negative acknowledged message", message_id=message_id)
            return True
        except Exception as e:
            logger.error(f"Failed to nack message {message_id}: {e}")
            return False

    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        try:
            stats_data = self.client.hgetall(self.stats_key)

            return QueueStats(
                messages_published=int(stats_data.get(b"messages_published", 0)),
                messages_consumed=int(stats_data.get(b"messages_consumed", 0)),
                messages_acked=int(stats_data.get(b"messages_acked", 0)),
                messages_nacked=int(stats_data.get(b"messages_nacked", 0)),
                messages_failed=int(stats_data.get(b"messages_failed", 0)),
                current_size=self.client.llen(self.pending_key),
            )
        except Exception as e:
            logger.error(f"Failed to get Redis queue stats: {e}")
            return QueueStats()

    def purge(self) -> bool:
        """Purge all messages."""
        try:
            self.client.delete(self.pending_key, self.processing_key)
            logger.info(f"Purged Redis queue: {self.queue_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to purge Redis queue: {e}")
            return False


class PubSubQueue(Queue):
    """Google Cloud Pub/Sub queue implementation."""

    def __init__(self, project_id: str, topic_name: str, subscription_name: str):
        if not HAS_GCP_PUBSUB:
            raise ImportError("Google Cloud Pub/Sub library not available")

        self.project_id = project_id
        self.topic_name = topic_name
        self.subscription_name = subscription_name

        # Initialize clients
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()

        # Create topic and subscription paths
        self.topic_path = self.publisher.topic_path(project_id, topic_name)
        self.subscription_path = self.subscriber.subscription_path(
            project_id, subscription_name
        )

        # Ensure topic and subscription exist
        self._ensure_resources()

        self._stats = QueueStats()

        logger.info(f"Initialized Pub/Sub queue: {topic_name}/{subscription_name}")

    def _ensure_resources(self):
        """Ensure topic and subscription exist."""
        try:
            # Create topic if it doesn't exist
            try:
                self.publisher.create_topic(request={"name": self.topic_path})
                logger.info(f"Created Pub/Sub topic: {self.topic_name}")
            except Exception:
                # Topic probably already exists
                pass

            # Create subscription if it doesn't exist
            try:
                self.subscriber.create_subscription(
                    request={"name": self.subscription_path, "topic": self.topic_path}
                )
                logger.info(f"Created Pub/Sub subscription: {self.subscription_name}")
            except Exception:
                # Subscription probably already exists
                pass

        except Exception as e:
            logger.error(f"Failed to ensure Pub/Sub resources: {e}")
            raise

    def publish(self, data: Any, attributes: Optional[Dict[str, str]] = None) -> str:
        """Publish message to Pub/Sub."""
        try:
            # Serialize data
            if isinstance(data, (dict, list)):
                message_data = json.dumps(data).encode("utf-8")
            elif isinstance(data, str):
                message_data = data.encode("utf-8")
            else:
                message_data = str(data).encode("utf-8")

            # Add message ID to attributes
            message_id = str(uuid.uuid4())
            message_attributes = attributes or {}
            message_attributes["message_id"] = message_id
            message_attributes["publish_time"] = str(time.time())

            # Publish message
            future = self.publisher.publish(
                self.topic_path, message_data, **message_attributes
            )

            # Wait for publish to complete
            future.result()

            self._stats.messages_published += 1
            logger.debug("Published message to Pub/Sub", message_id=message_id)
            return message_id

        except Exception as e:
            logger.error(f"Failed to publish message to Pub/Sub: {e}")
            raise SystemError(f"Failed to publish message: {e}")

    def consume(self, handler: MessageHandler, max_messages: int = 1) -> List[Message]:
        """Consume messages from Pub/Sub."""
        messages = []

        try:
            # Pull messages
            response = self.subscriber.pull(
                request={
                    "subscription": self.subscription_path,
                    "max_messages": max_messages,
                }
            )

            for received_message in response.received_messages:
                pubsub_message = received_message.message

                # Create our message object
                message = Message(
                    id=pubsub_message.attributes.get("message_id", str(uuid.uuid4())),
                    data=pubsub_message.data.decode("utf-8"),
                    attributes=dict(pubsub_message.attributes),
                    publish_time=float(
                        pubsub_message.attributes.get("publish_time", time.time())
                    ),
                )

                self._stats.messages_consumed += 1

                # Process message
                try:
                    success = handler.handle(message)
                    if success:
                        # Acknowledge message
                        self.subscriber.acknowledge(
                            request={
                                "subscription": self.subscription_path,
                                "ack_ids": [received_message.ack_id],
                            }
                        )
                        self._stats.messages_acked += 1
                    else:
                        # Don't acknowledge - message will be redelivered
                        self._stats.messages_nacked += 1
                except Exception as e:
                    handler.on_error(message, e)
                    self._stats.messages_failed += 1

                messages.append(message)

        except Exception as e:
            logger.error(f"Failed to consume messages from Pub/Sub: {e}")

        return messages

    def ack(self, message_id: str) -> bool:
        """Acknowledge message (handled in consume method)."""
        return True

    def nack(self, message_id: str) -> bool:
        """Negative acknowledge message (handled in consume method)."""
        return True

    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        return self._stats

    def purge(self) -> bool:
        """Purge all messages (not supported by Pub/Sub)."""
        logger.warning("Purge not supported for Pub/Sub queues")
        return False


class QueueManager:
    """
    High-level queue management with worker pools.
    """

    def __init__(self, queue: Queue):
        self.queue = queue
        self.workers: List[threading.Thread] = []
        self.running = False
        self._lock = threading.Lock()

        logger.info(f"Initialized queue manager with {queue.__class__.__name__}")

    def start_worker(self, handler: MessageHandler, max_messages: int = 1) -> None:
        """Start a worker thread to process messages."""

        def worker_loop():
            while self.running:
                try:
                    messages = self.queue.consume(handler, max_messages)
                    if not messages:
                        time.sleep(1)  # No messages, wait a bit
                except Exception as e:
                    logger.error(f"Worker error: {e}")
                    time.sleep(5)  # Error occurred, wait longer

        with self._lock:
            if not self.running:
                self.running = True

            worker = threading.Thread(target=worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)

            logger.info(f"Started worker thread (total: {len(self.workers)})")

    def stop_workers(self) -> None:
        """Stop all worker threads."""
        with self._lock:
            self.running = False

            for worker in self.workers:
                worker.join(timeout=5)

            self.workers.clear()
            logger.info("Stopped all worker threads")

    def publish_batch(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Publish multiple messages."""
        message_ids = []

        for msg in messages:
            data = msg.get("data")
            attributes = msg.get("attributes")

            try:
                message_id = self.queue.publish(data, attributes)
                message_ids.append(message_id)
            except Exception as e:
                logger.error(f"Failed to publish batch message: {e}")

        logger.info(f"Published batch of {len(message_ids)} messages")
        return message_ids


# Factory functions


def create_queue(queue_type: str, **kwargs) -> Queue:
    """
    Factory function to create queue instance.

    Args:
        queue_type: Type of queue ('memory', 'redis', 'pubsub')
        **kwargs: Queue-specific configuration

    Returns:
        Queue instance
    """
    queue_type = queue_type.lower()

    if queue_type == "memory":
        return InMemoryQueue(**kwargs)
    elif queue_type == "redis":
        return RedisQueue(**kwargs)
    elif queue_type == "pubsub":
        return PubSubQueue(**kwargs)
    else:
        raise ValueError(f"Unsupported queue type: {queue_type}")


# Global queue instance
_global_queue = None


def get_queue() -> Queue:
    """Get global queue instance."""
    global _global_queue
    if _global_queue is None:
        _global_queue = InMemoryQueue()
    return _global_queue


def set_queue(queue: Queue) -> None:
    """Set global queue instance."""
    global _global_queue
    _global_queue = queue
