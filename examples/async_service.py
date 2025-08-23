#!/usr/bin/env python3
"""
Genesis Async Service Example

Demonstrates advanced async patterns using Genesis Core components.
This example shows how to build a high-performance async service with:

- Async task processing with queues
- Concurrent worker patterns
- Async health checks and monitoring
- Graceful shutdown handling
- Background task management
- Stream processing patterns

Usage:
    python examples/async_service.py
"""

import asyncio
import random
import signal
from asyncio import Queue
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

# Genesis Core imports
from core import (AGGRESSIVE_POLICY, CircuitBreaker, Context, HealthCheck,
                  HealthStatus, HTTPHealthCheck, TraceContext, configure_core,
                  context_span, get_health_registry, get_logger, handle_error,
                  retry_async)


@dataclass
class Task:
    """Async task representation"""

    id: str
    type: str
    payload: Dict[str, Any]
    priority: int = 1
    max_retries: int = 3
    current_retry: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    context: Optional[Context] = None


@dataclass
class TaskResult:
    """Task execution result"""

    task_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    retry_count: int = 0


class TaskProcessor:
    """Async task processor with retry logic and circuit breakers"""

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"task_processor.{name}")
        self.circuit_breaker = CircuitBreaker(f"processor_{name}", failure_threshold=5)

    @retry_async(policy=AGGRESSIVE_POLICY)
    @circuit_breaker.decorator
    async def process_task(self, task: Task) -> TaskResult:
        """Process a single task with retry and circuit breaker protection"""
        start_time = asyncio.get_event_loop().time()

        try:
            # Set task context if available
            if task.context:
                with context_span(task.context):
                    result = await self._execute_task_logic(task)
            else:
                result = await self._execute_task_logic(task)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            self.logger.info(
                "Task processed successfully",
                task_id=task.id,
                task_type=task.type,
                duration_ms=duration_ms,
                retry_count=task.current_retry,
            )

            return TaskResult(
                task_id=task.id,
                success=True,
                result=result,
                duration_ms=duration_ms,
                retry_count=task.current_retry,
            )

        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            genesis_error = handle_error(e)

            self.logger.error(
                "Task processing failed",
                task_id=task.id,
                task_type=task.type,
                error=genesis_error,
                duration_ms=duration_ms,
                retry_count=task.current_retry,
            )

            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(genesis_error),
                duration_ms=duration_ms,
                retry_count=task.current_retry,
            )

    async def _execute_task_logic(self, task: Task) -> Any:
        """Execute the actual task logic"""
        # Simulate different task types
        if task.type == "data_processing":
            return await self._process_data(task.payload)
        elif task.type == "api_call":
            return await self._make_api_call(task.payload)
        elif task.type == "computation":
            return await self._perform_computation(task.payload)
        else:
            raise ValueError(f"Unknown task type: {task.type}")

    async def _process_data(self, payload: Dict) -> Dict:
        """Simulate data processing"""
        await asyncio.sleep(random.uniform(0.1, 0.5))

        # Simulate occasional failures
        if random.random() < 0.1:
            raise ConnectionError("Data source unavailable")

        return {
            "processed_records": payload.get("records", 0) * 2,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _make_api_call(self, payload: Dict) -> Dict:
        """Simulate external API call"""
        await asyncio.sleep(random.uniform(0.2, 0.8))

        # Simulate network failures
        if random.random() < 0.15:
            raise ConnectionError("API endpoint unreachable")

        return {
            "api_response": f"Response for {payload.get('endpoint', 'unknown')}",
            "status": "success",
        }

    async def _perform_computation(self, payload: Dict) -> Dict:
        """Simulate CPU-intensive computation"""
        await asyncio.sleep(random.uniform(0.3, 1.0))

        # Simulate computation errors
        if random.random() < 0.05:
            raise ValueError("Invalid computation parameters")

        return {"result": payload.get("input", 0) ** 2, "computation_type": "square"}


class AsyncTaskQueue:
    """High-performance async task queue with priority support"""

    def __init__(self, max_size: int = 1000):
        self.queue: Queue[Task] = Queue(maxsize=max_size)
        self.priority_queues: Dict[int, Queue[Task]] = {}
        self.processed_count = 0
        self.failed_count = 0
        self.logger = get_logger(__name__ + ".TaskQueue")

    async def enqueue(self, task: Task) -> None:
        """Add task to queue with priority handling"""
        try:
            # Use priority queue if specified
            if task.priority > 1:
                if task.priority not in self.priority_queues:
                    self.priority_queues[task.priority] = Queue()
                await self.priority_queues[task.priority].put(task)
            else:
                await self.queue.put(task)

            self.logger.debug("Task enqueued", task_id=task.id, priority=task.priority)

        except asyncio.QueueFull:
            self.logger.error("Task queue full, dropping task", task_id=task.id)
            raise

    async def dequeue(self) -> Optional[Task]:
        """Get next task from queue, respecting priority"""
        # Check priority queues first (higher priority first)
        for priority in sorted(self.priority_queues.keys(), reverse=True):
            priority_queue = self.priority_queues[priority]
            try:
                task = priority_queue.get_nowait()
                self.logger.debug(
                    "Dequeued priority task", task_id=task.id, priority=priority
                )
                return task
            except asyncio.QueueEmpty:
                continue

        # Check regular queue
        try:
            task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            self.logger.debug("Dequeued regular task", task_id=task.id)
            return task
        except asyncio.TimeoutError:
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        total_priority_items = sum(q.qsize() for q in self.priority_queues.values())

        return {
            "regular_queue_size": self.queue.qsize(),
            "priority_queue_size": total_priority_items,
            "total_queue_size": self.queue.qsize() + total_priority_items,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.failed_count)
                if (self.processed_count + self.failed_count) > 0
                else 0
            ),
        }


class AsyncWorker:
    """Async worker that processes tasks from the queue"""

    def __init__(
        self, worker_id: str, task_queue: AsyncTaskQueue, processor: TaskProcessor
    ):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.processor = processor
        self.logger = get_logger(f"worker.{worker_id}")
        self.running = False
        self.current_task: Optional[Task] = None

    async def start(self) -> None:
        """Start the worker"""
        self.running = True
        self.logger.info("Worker started")

        while self.running:
            try:
                # Get next task
                task = await self.task_queue.dequeue()
                if not task:
                    continue

                self.current_task = task

                # Process task
                result = await self.processor.process_task(task)

                # Update statistics
                if result.success:
                    self.task_queue.processed_count += 1
                else:
                    self.task_queue.failed_count += 1

                self.current_task = None

            except Exception as e:
                genesis_error = handle_error(e)
                self.logger.error("Worker error", error=genesis_error)

                if self.current_task:
                    self.task_queue.failed_count += 1
                    self.current_task = None

                # Brief pause before retrying
                await asyncio.sleep(1.0)

    async def stop(self) -> None:
        """Stop the worker gracefully"""
        self.running = False
        self.logger.info("Worker stopping")

    def get_status(self) -> Dict[str, Any]:
        """Get worker status"""
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "current_task": self.current_task.id if self.current_task else None,
            "processor_circuit_breaker": self.processor.circuit_breaker.get_status(),
        }


class QueueHealthCheck(HealthCheck):
    """Custom health check for task queue"""

    def __init__(self, name: str, task_queue: AsyncTaskQueue):
        super().__init__(name)
        self.task_queue = task_queue

    async def check_health(self):
        """Check queue health"""
        stats = self.task_queue.get_stats()

        # Check queue size
        if stats["total_queue_size"] > 900:  # Near capacity
            return self._create_result(
                HealthStatus.DEGRADED,
                f"Queue nearly full: {stats['total_queue_size']}/1000",
                **stats,
            )

        # Check success rate
        if stats["success_rate"] < 0.8 and stats["processed_count"] > 10:
            return self._create_result(
                HealthStatus.DEGRADED,
                f"Low success rate: {stats['success_rate']:.2%}",
                **stats,
            )

        return self._create_result(
            HealthStatus.HEALTHY,
            f"Queue healthy: {stats['total_queue_size']} items",
            **stats,
        )


class AsyncService:
    """Main async service coordinating all components"""

    def __init__(self, num_workers: int = 5):
        self.num_workers = num_workers
        self.logger = get_logger(__name__ + ".AsyncService")
        self.task_queue = AsyncTaskQueue()
        self.workers: List[AsyncWorker] = []
        self.processors: List[TaskProcessor] = []
        self.health_registry = None
        self.running = False
        self.background_tasks: Set[asyncio.Task] = set()

    async def setup(self) -> None:
        """Setup service components"""
        self.logger.info("Setting up async service")

        # Configure Genesis Core
        configure_core(
            service_name="async-task-service",
            environment="production",
            version="1.0.0",
            log_level="INFO",
        )

        # Setup health monitoring
        self.health_registry = get_health_registry()

        # Add queue health check
        self.health_registry.add_check(QueueHealthCheck("task_queue", self.task_queue))

        # Add external dependency health check
        self.health_registry.add_check(
            HTTPHealthCheck(
                "external_api", "https://httpbin.org/status/200", timeout=5.0
            )
        )

        # Create processors and workers
        for i in range(self.num_workers):
            processor = TaskProcessor(f"processor_{i}")
            worker = AsyncWorker(f"worker_{i}", self.task_queue, processor)

            self.processors.append(processor)
            self.workers.append(worker)

        self.logger.info("Service setup completed", num_workers=self.num_workers)

    async def start(self) -> None:
        """Start the service"""
        self.running = True
        self.logger.info("Starting async service")

        # Start workers
        worker_tasks = [asyncio.create_task(worker.start()) for worker in self.workers]

        # Start background monitoring
        monitor_task = asyncio.create_task(self._health_monitor())
        stats_task = asyncio.create_task(self._stats_reporter())

        # Store background tasks
        self.background_tasks.update(worker_tasks)
        self.background_tasks.add(monitor_task)
        self.background_tasks.add(stats_task)

        # Wait for all tasks
        try:
            await asyncio.gather(*self.background_tasks)
        except asyncio.CancelledError:
            self.logger.info("Service tasks cancelled")

    async def stop(self) -> None:
        """Stop the service gracefully"""
        self.running = False
        self.logger.info("Stopping async service")

        # Stop workers
        for worker in self.workers:
            await worker.stop()

        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.background_tasks, return_exceptions=True)

        self.logger.info("Service stopped")

    async def submit_task(
        self, task_type: str, payload: Dict, priority: int = 1
    ) -> str:
        """Submit a task for processing"""
        # Create context for the task
        context = Context.new_context(
            service="async-task-service", environment="production", version="1.0.0"
        )

        # Add trace context
        trace = TraceContext.new_trace()
        context_with_trace = context.with_trace(trace)

        # Create task
        task = Task(
            id=str(uuid4()),
            type=task_type,
            payload=payload,
            priority=priority,
            context=context_with_trace,
        )

        await self.task_queue.enqueue(task)

        self.logger.info(
            "Task submitted", task_id=task.id, task_type=task_type, priority=priority
        )
        return task.id

    async def _health_monitor(self) -> None:
        """Background health monitoring"""
        while self.running:
            try:
                health_report = await self.health_registry.check_health()

                if health_report.status != HealthStatus.HEALTHY:
                    self.logger.warning(
                        "Service health degraded",
                        status=health_report.status.value,
                        failed_checks=[
                            check.name
                            for check in health_report.checks
                            if check.status != HealthStatus.HEALTHY
                        ],
                    )

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                genesis_error = handle_error(e)
                self.logger.error("Health monitoring failed", error=genesis_error)
                await asyncio.sleep(30)

    async def _stats_reporter(self) -> None:
        """Background statistics reporting"""
        while self.running:
            try:
                # Get queue stats
                queue_stats = self.task_queue.get_stats()

                # Get worker stats
                worker_stats = [worker.get_status() for worker in self.workers]
                active_workers = sum(1 for w in worker_stats if w["running"])

                self.logger.info(
                    "Service statistics",
                    queue_size=queue_stats["total_queue_size"],
                    processed_count=queue_stats["processed_count"],
                    failed_count=queue_stats["failed_count"],
                    success_rate=f"{queue_stats['success_rate']:.2%}",
                    active_workers=active_workers,
                    total_workers=len(self.workers),
                )

                await asyncio.sleep(60)  # Report every minute

            except Exception as e:
                genesis_error = handle_error(e)
                self.logger.error("Stats reporting failed", error=genesis_error)
                await asyncio.sleep(60)

    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status"""
        return {
            "service": "async-task-service",
            "running": self.running,
            "queue_stats": self.task_queue.get_stats(),
            "worker_stats": [worker.get_status() for worker in self.workers],
            "processor_circuit_breakers": [
                processor.circuit_breaker.get_status() for processor in self.processors
            ],
        }


# Global service instance
service: Optional[AsyncService] = None


async def task_generator():
    """Generate random tasks for demonstration"""
    global service

    task_types = ["data_processing", "api_call", "computation"]

    for i in range(50):  # Generate 50 tasks
        task_type = random.choice(task_types)
        priority = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]

        payload = {
            "batch_id": i,
            "records": random.randint(100, 1000),
            "endpoint": f"/api/endpoint_{i}",
            "input": random.randint(1, 100),
        }

        task_id = await service.submit_task(task_type, payload, priority)
        print(
            f"📋 Submitted task {i+1}/50: {task_id} ({task_type}, priority={priority})"
        )

        # Random delay between task submissions
        await asyncio.sleep(random.uniform(0.1, 0.5))


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    if service:
        asyncio.create_task(service.stop())


async def main():
    """Main function"""
    global service

    print("🚀 Starting Genesis Async Service Example")
    print("=" * 50)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and setup service
    service = AsyncService(num_workers=3)
    await service.setup()

    # Start task generation in background
    task_gen = asyncio.create_task(task_generator())

    # Start service monitoring
    status_task = asyncio.create_task(status_monitor())

    try:
        # Start service and wait
        service_task = asyncio.create_task(service.start())

        # Wait for task generation to complete
        await task_gen

        print("\n📊 All tasks submitted, monitoring service...")
        print("📈 Press Ctrl+C to stop the service")

        # Continue running service and monitoring
        await asyncio.gather(service_task, status_task)

    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
    except Exception as e:
        genesis_error = handle_error(e)
        print(f"❌ Service error: {genesis_error.message}")
    finally:
        if service:
            await service.stop()
        print("✅ Service stopped gracefully")


async def status_monitor():
    """Monitor service status periodically"""
    global service

    while service and service.running:
        try:
            await asyncio.sleep(10)  # Update every 10 seconds

            status = service.get_service_status()
            queue_stats = status["queue_stats"]
            active_workers = sum(1 for w in status["worker_stats"] if w["running"])

            print(
                f"\n📊 Status: Queue={queue_stats['total_queue_size']}, "
                f"Processed={queue_stats['processed_count']}, "
                f"Failed={queue_stats['failed_count']}, "
                f"Workers={active_workers}/{len(status['worker_stats'])}, "
                f"Success Rate={queue_stats['success_rate']:.2%}"
            )

        except Exception as e:
            print(f"❌ Status monitoring error: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    # Run the async service
    asyncio.run(main())
