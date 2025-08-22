"""Base tool classes for SOLVE tools."""

from typing import Any


class BaseTool:
    """Base class for all SOLVE tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def run(self, **kwargs: Any) -> Any:
        """Run the tool with given arguments."""
        raise NotImplementedError(
            "Tool execution must be implemented by concrete tool classes. "
            "Each tool should define its specific functionality.",
        )
