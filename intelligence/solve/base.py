"""Base SOLVE types."""

from enum import Enum
from pathlib import Path
from typing import Any, Optional


class TaskType(str, Enum):
    """Types of tasks."""

    ANALYSIS = "analysis"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"


class Task:
    """Task to be executed."""

    def __init__(
        self,
        task_id: str,
        task_type: TaskType,
        description: str,
        files: Optional[list[Path]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.description = description
        self.files = files or []
        self.metadata = metadata or {}
