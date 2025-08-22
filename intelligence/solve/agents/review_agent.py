"""Review agent for SOLVE tasks."""

from solve_core.config import BaseConfig

from .base import Agent


class ReviewAgent(Agent):
    """Agent responsible for reviewing solutions."""

    def __init__(self, config: BaseConfig | None = None):
        super().__init__(config)

    def plan(self, task_description: str) -> str:
        """Plan review process."""
        return f"Review plan for: {task_description}"

    def execute(self, plan: str) -> None:
        """Execute review process."""
        raise NotImplementedError(
            "Review agent execution requires ADK integration for "
            "code analysis and feedback generation.",
        )

    def validate(self, result: str) -> bool:
        """Validate review results."""
        raise NotImplementedError(
            "Review validation requires checking for completeness and actionability of feedback.",
        )
