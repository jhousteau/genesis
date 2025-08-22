"""Base agent interface."""

from abc import ABC, abstractmethod
from typing import Optional

from solve_core.config import BaseConfig
from solve_core.logging import get_logger

logger = get_logger(__name__)


class Agent(ABC):
    """Base agent class."""

    def __init__(self, config: Optional[BaseConfig] = None):
        self.config = config or BaseConfig()

    @abstractmethod
    def plan(self, task_description: str) -> str:
        """Plan task execution."""
        ...

    @abstractmethod
    def execute(self, plan: str) -> None:
        """Execute a plan."""
        ...

    @abstractmethod
    def validate(self, result: str) -> bool:
        """Validate execution result."""
        ...
