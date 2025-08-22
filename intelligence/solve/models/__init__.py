"""
Core data models for the SOLVE package.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from .common import AgentTask, Goal, Result, TaskStatus

__all__ = [
    "AgentConfig",
    "ToolConfig",
    "PhaseConfig",
    "SolveConfig",
    "AgentTask",
    "Goal",
    "Result",
    "TaskStatus",
    "Lesson",
    "ADRConfig",
]


@dataclass
class AgentConfig:
    """Configuration for a SOLVE agent."""

    name: str
    type: str
    settings: dict[str, Any]


@dataclass
class ToolConfig:
    """Configuration for a SOLVE tool."""

    name: str
    type: str
    settings: dict[str, Any]


@dataclass
class PhaseConfig:
    """Configuration for a SOLVE phase."""

    name: str
    type: str
    settings: dict[str, Any]
    agents: list[AgentConfig]
    tools: list[ToolConfig]


@dataclass
class SolveConfig:
    """Complete SOLVE configuration."""

    version: str
    phases: list[PhaseConfig]
    global_settings: dict[str, Any]


@dataclass
class Lesson:
    """Represents a lesson learned during SOLVE execution."""

    lesson_id: str
    phase: str
    issue: str
    resolution: str
    prevention: str
    adr_number: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert lesson to dictionary for storage."""
        return {
            "lesson_id": self.lesson_id,
            "phase": self.phase,
            "issue": self.issue,
            "resolution": self.resolution,
            "prevention": self.prevention,
            "adr_number": self.adr_number,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lesson":
        """Create lesson from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class ADRConfig:
    """Configuration for Architecture Decision Records."""

    number: str
    title: str
    status: str
    requirements: list[str] = field(default_factory=list)
    phase_outcomes: Dict[str, list[str]] = field(default_factory=dict)
