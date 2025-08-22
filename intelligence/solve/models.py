"""
Data Models for SOLVE SDK Integration

This module defines the data structures used throughout the SDK integration,
providing type safety and clear interfaces.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Enums for type safety


class LessonType(Enum):
    """Type of lesson learned during SOLVE execution."""

    IMPROVEMENT = "improvement"
    WARNING = "warning"
    SUCCESS = "success"


# Agent-Friendly Data Structures (New)


class TaskStatus(Enum):
    """Status of an agent task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Goal:
    """Represents a high-level goal for agent execution.

    This structure provides clear context and constraints for agents
    to understand what they need to achieve.
    """

    description: str
    context: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate goal data."""
        if not self.description:
            raise ValueError("Goal description cannot be empty")

        if not self.success_criteria:
            logger.warning("Goal defined without explicit success criteria")

        logger.info(f"Created goal: {self.description[:50]}...")


@dataclass
class Result:
    """Represents the result of an agent task execution.

    Provides structured feedback about task completion including
    any artifacts produced and metadata about the execution.
    """

    success: bool
    message: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    fixes_applied: int = 0  # Number of fixes applied during workflow execution

    def __post_init__(self) -> None:
        """Log result summary."""
        logger.info(
            f"Result: success={self.success}, "
            f"artifacts={len(self.artifacts)}, "
            f"message={self.message[:50]}...",
        )

    def add_artifact(self, name: str, value: Any) -> None:
        """Add an artifact to the result."""
        self.artifacts[name] = value
        logger.debug(f"Added artifact '{name}' to result")

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the result."""
        self.metadata[key] = value
        logger.debug(f"Added metadata '{key}' to result")


@dataclass
class AgentTask:
    """Represents a task assigned to an agent.

    Combines a goal with agent assignment and tracking information
    to manage autonomous task execution.
    """

    goal: Goal
    assigned_agent: str
    status: TaskStatus = field(default_factory=lambda: TaskStatus.PENDING)
    results: Result | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate task data."""
        if not self.assigned_agent:
            raise ValueError("Task must be assigned to an agent")

        logger.info(
            f"Created task for {self.assigned_agent}: {self.goal.description[:50]}..."
        )

    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()
        logger.info(f"Started task for {self.assigned_agent}")

    def complete(self, result: Result) -> None:
        """Mark task as completed with result."""
        self.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
        self.results = result
        self.completed_at = datetime.now()
        logger.info(
            f"Completed task for {self.assigned_agent}: status={self.status.value}"
        )

    def block(self, reason: str) -> None:
        """Mark task as blocked."""
        self.status = TaskStatus.BLOCKED
        if not self.results:
            self.results = Result(success=False, message=f"Task blocked: {reason}")
        logger.warning(f"Task blocked for {self.assigned_agent}: {reason}")

    @property
    def execution_time(self) -> float | None:
        """Calculate execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# Legacy Data Structures (with deprecation warnings)


@dataclass
class ExecutionResult:
    """Result of a SOLVE phase execution.

    Tracks the outcome of phase execution including files affected,
    validation status, and any lessons learned during execution.

    .. deprecated::
        Consider using the new Result class for agent-friendly interfaces.
        ExecutionResult will be maintained for backward compatibility.
    """

    success: bool
    phase: str
    files_created: list[Path] = field(default_factory=list)
    files_modified: list[Path] = field(default_factory=list)
    validation_result: ValidationResult | None = None
    lessons_learned: list[Lesson] = field(default_factory=list)
    error_message: str | None = None
    execution_time_seconds: float | None = None

    def __post_init__(self) -> None:
        """Validate execution result data."""
        # Issue deprecation warning for new usage
        warnings.warn(
            "ExecutionResult is deprecated. Consider using Result class for new implementations.",
            DeprecationWarning,
            stacklevel=2,
        )

        if self.phase not in ["S", "O", "L", "V", "E"]:
            logger.warning(f"Invalid phase '{self.phase}' in ExecutionResult")

        # Log execution summary
        logger.info(
            f"ExecutionResult for phase {self.phase}: "
            f"success={self.success}, "
            f"files_created={len(self.files_created)}, "
            f"files_modified={len(self.files_modified)}",
        )

    def to_result(self) -> Result:
        """Convert ExecutionResult to new Result format.

        This method helps with migration to the new agent-friendly
        Result data structure.
        """
        artifacts: dict[str, Any] = {
            "phase": self.phase,
            "files_created": [str(p) for p in self.files_created],
            "files_modified": [str(p) for p in self.files_modified],
        }

        if self.validation_result:
            artifacts["validation"] = {
                "passed": self.validation_result.passed,
                "errors": self.validation_result.errors,
                "warnings": self.validation_result.warnings,
            }

        if self.lessons_learned:
            artifacts["lessons"] = [lesson.to_dict() for lesson in self.lessons_learned]

        metadata: dict[str, Any] = {}
        if self.execution_time_seconds is not None:
            metadata["execution_time_seconds"] = self.execution_time_seconds

        message = (
            self.error_message
            if self.error_message
            else f"Phase {self.phase} execution completed"
        )

        return Result(
            success=self.success,
            message=message,
            artifacts=artifacts,
            metadata=metadata,
        )


@dataclass
class ValidationResult:
    """Result of phase validation checks.

    Contains detailed information about validation outcomes including
    specific errors and warnings found during validation.
    """

    passed: bool = True  # Default to True, will be overridden by is_valid if provided
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_files: list[Path] = field(default_factory=list)
    validation_time_seconds: float | None = None
    # Additional fields for test compatibility
    phase: str | None = None
    is_valid: bool | None = None  # Alias for passed
    issues: list[Any] = field(default_factory=list)  # For ValidationIssue objects

    def __post_init__(self) -> None:
        """Log validation summary."""
        # Sync is_valid with passed if provided
        if self.is_valid is not None:
            self.passed = self.is_valid
        elif self.passed is not None:
            self.is_valid = self.passed

        logger.info(
            f"ValidationResult: passed={self.passed}, "
            f"errors={len(self.errors)}, warnings={len(self.warnings)}, "
            f"files_checked={len(self.checked_files)}",
        )

        # Log specific errors if validation failed
        if not self.passed and self.errors:
            for error in self.errors[:5]:  # Log first 5 errors
                logger.error(f"Validation error: {error}")
            if len(self.errors) > 5:
                logger.error(f"...and {len(self.errors) - 5} more errors")

    def add_error(self, error: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.passed = False
        logger.debug(f"Added validation error: {error}")

    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(warning)
        logger.debug(f"Added validation warning: {warning}")


@dataclass
class Lesson:
    """Represents a lesson learned during SOLVE execution.

    Captures issues encountered, their resolutions, and preventive
    measures for future development.
    """

    lesson_id: str
    phase: str
    issue: str
    resolution: str
    prevention: str
    timestamp: datetime = field(default_factory=datetime.now)
    adr_number: str | None = None

    def __post_init__(self) -> None:
        """Validate lesson data."""
        # Ensure all required fields have meaningful content
        if not all(
            [self.lesson_id, self.phase, self.issue, self.resolution, self.prevention]
        ):
            logger.warning(f"Lesson {self.lesson_id} has empty required fields")

        # Validate phase
        if self.phase not in ["S", "O", "L", "V", "E", "general"]:
            logger.warning(f"Invalid phase '{self.phase}' in Lesson {self.lesson_id}")

        logger.info(f"Created lesson {self.lesson_id} for phase {self.phase}")

    def to_dict(self) -> dict[str, Any]:
        """Convert lesson to dictionary for serialization."""
        return {
            "lesson_id": self.lesson_id,
            "phase": self.phase,
            "issue": self.issue,
            "resolution": self.resolution,
            "prevention": self.prevention,
            "timestamp": self.timestamp.isoformat(),
            "adr_number": self.adr_number,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lesson:
        """Create lesson from dictionary."""
        # Handle timestamp conversion
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


# Additional data models for configuration


@dataclass
class GovernanceConfig:
    """Configuration loaded from governance files."""

    phase: str
    requirements: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    approved_resources: list[dict[str, Any]] = field(default_factory=list)
    performance_targets: dict[str, Any] = field(default_factory=dict)
    interfaces: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Log governance config summary."""
        logger.debug(
            f"GovernanceConfig for phase {self.phase}: "
            f"{len(self.requirements)} requirements, "
            f"{len(self.constraints)} constraints",
        )


@dataclass
class ADRConfig:
    """Configuration loaded from ADR files."""

    number: str
    title: str
    status: str
    requirements: list[str] = field(default_factory=list)
    approved_resources: list[dict[str, Any]] = field(default_factory=list)
    phase_outcomes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate ADR configuration."""
        if not self.number or not self.title:
            logger.error("ADR missing required number or title")
        logger.info(f"Loaded ADR-{self.number}: {self.title}")


@dataclass
class PhaseConfig:
    """Configuration for a specific SOLVE phase."""

    name: str
    description: str
    uses_web_resources: bool = False
    outcome: str | None = None
    key_considerations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Log phase config."""
        logger.debug(
            f"PhaseConfig for {self.name}: web_resources={self.uses_web_resources}"
        )


# Constitutional AI Data Structures


@dataclass
class ConstitutionalContext:
    """Context for constitutional AI decision-making."""

    agent_id: str
    agent_type: str
    goal: str | None = None
    constraints: list[str] = field(default_factory=list)
    reasoning: str | None = None
    prior_decisions: list[str] = field(default_factory=list)
    safety_requirements: list[str] = field(default_factory=list)
    collaboration_context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate constitutional context."""
        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty")
        if not self.agent_type:
            raise ValueError("Agent type cannot be empty")

        logger.debug(f"Constitutional context for {self.agent_id} ({self.agent_type})")


@dataclass
class ConstitutionalGuidance:
    """Guidance provided by constitutional AI system."""

    agent_type: str
    situation: str
    core_mission: str
    relevant_principles: list[str] = field(default_factory=list)
    applicable_guidelines: list[str] = field(default_factory=list)
    safety_considerations: list[str] = field(default_factory=list)
    collaboration_advice: list[str] = field(default_factory=list)
    decision_criteria: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """Validate constitutional guidance."""
        if not self.core_mission:
            raise ValueError("Core mission cannot be empty")

        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

        logger.debug(
            f"Constitutional guidance for {self.agent_type}: "
            f"{len(self.relevant_principles)} principles",
        )


@dataclass
class AgentDecisionRequest:
    """Request for agent decision validation."""

    agent_id: str
    agent_type: str
    proposed_decision: str
    context: ConstitutionalContext
    urgency: str = "normal"  # "low", "normal", "high", "critical"
    requires_approval: bool = False

    def __post_init__(self) -> None:
        """Validate decision request."""
        if not self.proposed_decision:
            raise ValueError("Proposed decision cannot be empty")

        if self.urgency not in ["low", "normal", "high", "critical"]:
            raise ValueError(f"Invalid urgency level: {self.urgency}")

        logger.info(
            f"Decision request from {self.agent_id}: {self.proposed_decision[:50]}..."
        )


@dataclass
class AgentDecisionResponse:
    """Response to agent decision validation."""

    approved: bool
    confidence: float
    reasoning: str
    applied_principles: list[str] = field(default_factory=list)
    safety_warnings: list[str] = field(default_factory=list)
    improvement_suggestions: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate decision response."""
        if not self.reasoning:
            raise ValueError("Reasoning cannot be empty")

        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

        logger.debug(
            f"Decision response: approved={self.approved}, confidence={self.confidence}"
        )


@dataclass
class ConstitutionalLearning:
    """Learning captured from constitutional AI interactions."""

    agent_type: str
    situation_pattern: str
    effective_principles: list[str]
    outcomes: dict[str, Any]
    improvements: list[str]
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate constitutional learning."""
        if not self.situation_pattern:
            raise ValueError("Situation pattern cannot be empty")

        if not self.effective_principles:
            logger.warning("No effective principles identified in learning")

        logger.info(
            f"Constitutional learning for {self.agent_type}: {self.situation_pattern}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert learning to dictionary for storage."""
        return {
            "agent_type": self.agent_type,
            "situation_pattern": self.situation_pattern,
            "effective_principles": self.effective_principles,
            "outcomes": self.outcomes,
            "improvements": self.improvements,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConstitutionalLearning:
        """Create learning from dictionary."""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class AgentInteraction:
    """Record of agent-to-agent interaction."""

    from_agent: str
    to_agent: str
    interaction_type: str  # "request", "response", "collaboration", "escalation"
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    constitutional_guidance_applied: bool = False

    def __post_init__(self) -> None:
        """Validate agent interaction."""
        if not self.from_agent or not self.to_agent:
            raise ValueError("From and to agents cannot be empty")

        if self.interaction_type not in [
            "request",
            "response",
            "collaboration",
            "escalation",
        ]:
            raise ValueError(f"Invalid interaction type: {self.interaction_type}")

        logger.debug(
            f"Agent interaction: {self.from_agent} -> {self.to_agent} ({self.interaction_type})",
        )


@dataclass
class SystemState:
    """Current state of the SOLVE system for constitutional AI."""

    active_agents: list[str]
    current_goals: list[Goal]
    recent_decisions: list[AgentDecisionRequest]
    performance_metrics: dict[str, Any] = field(default_factory=dict)
    safety_status: str = "normal"  # "normal", "warning", "critical"
    learning_insights: list[ConstitutionalLearning] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate system state."""
        if self.safety_status not in ["normal", "warning", "critical"]:
            raise ValueError(f"Invalid safety status: {self.safety_status}")

        logger.info(
            f"System state: {len(self.active_agents)} agents, {len(self.current_goals)} goals",
        )

    def add_decision(self, decision: AgentDecisionRequest) -> None:
        """Add a decision to recent decisions."""
        self.recent_decisions.append(decision)

        # Keep only recent decisions (last 100)
        if len(self.recent_decisions) > 100:
            self.recent_decisions = self.recent_decisions[-50:]

        logger.debug(
            f"Added decision to system state: {len(self.recent_decisions)} total"
        )

    def update_safety_status(self, new_status: str, reason: str | None = None) -> None:
        """Update system safety status."""
        if new_status not in ["normal", "warning", "critical"]:
            raise ValueError(f"Invalid safety status: {new_status}")

        old_status = self.safety_status
        self.safety_status = new_status

        if reason:
            logger.info(
                f"Safety status changed: {old_status} -> {new_status} ({reason})"
            )
        else:
            logger.info(f"Safety status changed: {old_status} -> {new_status}")

    def add_learning(self, learning: ConstitutionalLearning) -> None:
        """Add learning insight to system state."""
        self.learning_insights.append(learning)

        # Keep only recent learning (last 200)
        if len(self.learning_insights) > 200:
            self.learning_insights = self.learning_insights[-100:]

        logger.debug(f"Added learning insight: {len(self.learning_insights)} total")


@dataclass
class ConstitutionalMetrics:
    """Metrics for constitutional AI system performance."""

    total_decisions: int = 0
    approved_decisions: int = 0
    rejected_decisions: int = 0
    safety_warnings: int = 0
    critical_violations: int = 0
    learning_insights_captured: int = 0
    average_confidence: float = 0.0
    most_used_principles: list[str] = field(default_factory=list)
    agent_performance: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize metrics."""
        logger.debug("Constitutional metrics initialized")

    @property
    def approval_rate(self) -> float:
        """Calculate approval rate."""
        if self.total_decisions == 0:
            return 0.0
        return self.approved_decisions / self.total_decisions

    @property
    def safety_incident_rate(self) -> float:
        """Calculate safety incident rate."""
        if self.total_decisions == 0:
            return 0.0
        return (self.safety_warnings + self.critical_violations) / self.total_decisions

    def update_decision_metrics(
        self,
        approved: bool,
        confidence: float,
        had_warnings: bool = False,
        had_critical: bool = False,
    ) -> None:
        """Update decision-related metrics."""
        self.total_decisions += 1

        if approved:
            self.approved_decisions += 1
        else:
            self.rejected_decisions += 1

        if had_warnings:
            self.safety_warnings += 1

        if had_critical:
            self.critical_violations += 1

        # Update rolling average confidence
        if self.total_decisions == 1:
            self.average_confidence = confidence
        else:
            self.average_confidence = (
                self.average_confidence * (self.total_decisions - 1) + confidence
            ) / self.total_decisions

        logger.debug(
            f"Updated decision metrics: {self.total_decisions} total, "
            f"{self.approval_rate:.2f} approval rate",
        )

    def update_agent_performance(
        self, agent_id: str, performance_data: dict[str, Any]
    ) -> None:
        """Update agent-specific performance metrics."""
        if agent_id not in self.agent_performance:
            self.agent_performance[agent_id] = {}

        self.agent_performance[agent_id].update(performance_data)
        logger.debug(f"Updated performance for {agent_id}")

    def get_summary(self) -> dict[str, Any]:
        """Get summary of constitutional AI metrics."""
        return {
            "total_decisions": self.total_decisions,
            "approval_rate": self.approval_rate,
            "safety_incident_rate": self.safety_incident_rate,
            "average_confidence": self.average_confidence,
            "learning_insights": self.learning_insights_captured,
            "most_used_principles": self.most_used_principles[:5],  # Top 5
            "agent_count": len(self.agent_performance),
        }
