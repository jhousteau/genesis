"""
Prompt loader for error-specific LLM prompts.

Loads and caches prompts from the prompts directory.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptLoader:
    """Loads error-specific prompts from markdown files."""

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize the prompt loader.

        Args:
            prompts_dir: Directory containing prompt files. Defaults to ./prompts
        """
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent / "prompts"

        self.prompts_dir = prompts_dir
        self._cache: dict[str, str] = {}
        self._load_all_prompts()

    def _load_all_prompts(self) -> None:
        """Load all prompts from the prompts directory."""
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            return

        for prompt_file in self.prompts_dir.glob("*.md"):
            error_code = prompt_file.stem
            try:
                content = prompt_file.read_text()
                self._cache[error_code] = content
                logger.debug(f"Loaded prompt for {error_code}")
            except Exception as e:
                logger.error(f"Failed to load prompt for {error_code}: {e}")

    def get_prompt(self, error_code: str) -> str | None:
        """Get the prompt content for a specific error code.

        Args:
            error_code: The error code (e.g., "E722", "no-untyped-def")

        Returns:
            The prompt content or None if not found
        """
        return self._cache.get(error_code)

    def has_prompt(self, error_code: str) -> bool:
        """Check if a prompt exists for the error code."""
        return error_code in self._cache

    def get_instructions(self, error_code: str) -> str:
        """Extract just the fix instructions from a prompt.

        Args:
            error_code: The error code

        Returns:
            The fix instructions section or a generic message
        """
        prompt = self.get_prompt(error_code)
        if not prompt:
            return f"Fix {error_code} error according to best practices"

        # Extract the Fix Instructions section
        lines = prompt.split("\n")
        in_instructions = False
        instructions = []

        for line in lines:
            if line.strip() == "## Fix Instructions":
                in_instructions = True
                continue
            elif line.startswith("## ") and in_instructions:
                break
            elif in_instructions and line.strip():
                instructions.append(line)

        return "\n".join(instructions) if instructions else f"Fix {error_code} error"

    def get_examples(self, error_code: str) -> list[str]:
        """Extract examples from a prompt.

        Args:
            error_code: The error code

        Returns:
            List of example outputs
        """
        prompt = self.get_prompt(error_code)
        if not prompt:
            return []

        examples = []
        lines = prompt.split("\n")
        in_output = False

        for _i, line in enumerate(lines):
            if line.strip() == "Output:" or line.strip() == "### Output":
                in_output = True
                continue
            elif in_output:
                if line.startswith("```"):
                    in_output = False
                elif (
                    line.strip()
                    and not line.startswith("#")
                    and ":" in line
                    and line.strip()[0].isdigit()
                ):
                    examples.append(line.strip())
                    in_output = False

        return examples

    def reload(self) -> None:
        """Reload all prompts from disk."""
        self._cache.clear()
        self._load_all_prompts()
        logger.info(f"Reloaded {len(self._cache)} prompts")
