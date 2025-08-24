"""Runners for executing autofix operations."""

from .fixers import (
    BaseFixer,
    EndOfFileFixer,
    RuffAutoFixer,
    RuffFormatter,
    TrailingWhitespaceFixer,
)


class AutofixRunner:
    """Runner for executing a sequence of code fixes."""

    def __init__(self, max_iterations: int = 5):
        """Initialize the autofix runner.

        Args:
            max_iterations: Maximum number of fix iterations
        """
        self.max_iterations = max_iterations
        self.fixers: list[BaseFixer] = [
            EndOfFileFixer(),
            TrailingWhitespaceFixer(),
            RuffAutoFixer(),
            RuffFormatter(),
        ]

    def run(self, content: str) -> str:
        """Run all fixers on the content.

        Args:
            content: Code content to fix

        Returns:
            Fixed code content
        """
        for _ in range(self.max_iterations):
            orig_content = content
            for fixer in self.fixers:
                content = fixer.fix(content)
            if content == orig_content:
                break
        return content
