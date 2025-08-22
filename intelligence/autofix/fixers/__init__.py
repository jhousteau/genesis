"""Code fixers for the autofix package."""


class BaseFixer:
    """Base class for all code fixers."""

    def fix(self, content: str) -> str:
        """Fix the given content."""
        raise NotImplementedError


class EndOfFileFixer(BaseFixer):
    """Ensures files end with a newline."""

    def fix(self, content: str) -> str:
        if not content.endswith("\n"):
            return content + "\n"
        return content


class TrailingWhitespaceFixer(BaseFixer):
    """Removes trailing whitespace from lines."""

    def fix(self, content: str) -> str:
        return "\n".join(line.rstrip() for line in content.splitlines()) + "\n"


class RuffAutoFixer(BaseFixer):
    """Applies ruff auto-fixes."""

    def fix(self, content: str) -> str:
        """Apply ruff auto-fixes to content."""
        import subprocess
        import tempfile
        from pathlib import Path

        # Write content to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            # Run ruff --fix on the file
            subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                [
                    "ruff",
                    "check",
                    "--fix",
                    "--select",
                    "I,F401,F841",
                    "--quiet",
                    str(temp_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            # Read the fixed content
            fixed_content = temp_path.read_text()
            return fixed_content

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            # If ruff fails or is not available, return original content
            return content
        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()


class RuffFormatter(BaseFixer):
    """Formats code using ruff."""

    def fix(self, content: str) -> str:
        """Format content using ruff."""
        import subprocess
        import tempfile
        from pathlib import Path

        # Write content to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            # Run ruff format on the file
            subprocess.run(  # noqa: S603  # Subprocess secured: shell=False, validated inputs
                ["ruff", "format", "--quiet", str(temp_path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            # Read the formatted content
            formatted_content = temp_path.read_text()
            return formatted_content

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            # If ruff fails or is not available, return original content
            return content
        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()
