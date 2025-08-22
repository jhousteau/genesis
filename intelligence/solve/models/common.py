"""Common data models."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class Goal(str, Enum):
    """Goal types."""

    ANALYZE = "analyze"
    IMPLEMENT = "implement"
    REVIEW = "review"


class TaskStatus(str, Enum):
    """Task status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentTask:
    """Task for an agent to execute."""

    task_id: str
    goal: Goal
    description: str
    status: TaskStatus = TaskStatus.PENDING
    metadata: Optional[dict[str, Any]] = None


@dataclass
class Result:
    """Result from task execution."""

    success: bool
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    artifacts: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
