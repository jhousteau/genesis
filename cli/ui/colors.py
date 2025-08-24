"""
Color Scheme - Accessible Color Management
Provides consistent, accessible color scheme with fallbacks.
"""

import os
from enum import Enum
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ColorLevel(Enum):
    """Color capability levels."""

    NONE = 0
    BASIC = 8
    EXTENDED = 256
    TRUECOLOR = 16777216


class ColorScheme:
    """
    Accessible color scheme following REACT methodology.

    R - Responsive: Adapts to terminal color capabilities
    E - Efficient: Minimal color detection overhead
    A - Accessible: High contrast, color-blind friendly palette
    C - Connected: Consistent with Genesis brand colors
    T - Tested: Comprehensive color compatibility testing
    """

    # ANSI Color Codes
    RESET = "\033[0m"

    # Basic 8 colors (compatible with most terminals)
    BASIC_COLORS = {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "bright_black": "\033[90m",
        "bright_red": "\033[91m",
        "bright_green": "\033[92m",
        "bright_yellow": "\033[93m",
        "bright_blue": "\033[94m",
        "bright_magenta": "\033[95m",
        "bright_cyan": "\033[96m",
        "bright_white": "\033[97m",
    }

    # Background colors
    BASIC_BG_COLORS = {
        "bg_black": "\033[40m",
        "bg_red": "\033[41m",
        "bg_green": "\033[42m",
        "bg_yellow": "\033[43m",
        "bg_blue": "\033[44m",
        "bg_magenta": "\033[45m",
        "bg_cyan": "\033[46m",
        "bg_white": "\033[47m",
    }

    # Text styles
    STYLES = {
        "bold": "\033[1m",
        "dim": "\033[2m",
        "italic": "\033[3m",
        "underline": "\033[4m",
        "blink": "\033[5m",
        "reverse": "\033[7m",
        "strikethrough": "\033[9m",
    }

    def __init__(self):
        self._color_level: Optional[ColorLevel] = None
        self._supports_color: Optional[bool] = None
        self._theme = "default"

    def detect_color_level(self) -> ColorLevel:
        """Detect terminal color capability level."""
        if self._color_level is not None:
            return self._color_level

        # Check environment variables
        colorterm = os.getenv("COLORTERM", "").lower()
        term = os.getenv("TERM", "").lower()

        if colorterm in ["truecolor", "24bit"]:
            self._color_level = ColorLevel.TRUECOLOR
        elif "256color" in term or "256" in colorterm:
            self._color_level = ColorLevel.EXTENDED
        elif any(color in term for color in ["color", "ansi"]):
            self._color_level = ColorLevel.BASIC
        elif os.getenv("NO_COLOR") or os.getenv("TERM") == "dumb":
            self._color_level = ColorLevel.NONE
        else:
            # Default to basic color support
            self._color_level = ColorLevel.BASIC

        logger.debug(f"Detected color level: {self._color_level}")
        return self._color_level

    @property
    def supports_color(self) -> bool:
        """Check if terminal supports any color output."""
        if self._supports_color is None:
            import sys

            self._supports_color = (
                sys.stdout.isatty()
                and self.detect_color_level() != ColorLevel.NONE
                and os.getenv("NO_COLOR") is None
            )
        return self._supports_color

    def get_semantic_colors(self) -> Dict[str, str]:
        """Get semantic color mapping for Genesis CLI."""
        if not self.supports_color:
            return {
                key: ""
                for key in [
                    "primary",
                    "secondary",
                    "success",
                    "warning",
                    "error",
                    "info",
                    "muted",
                    "highlight",
                    "accent",
                ]
            }

        # High contrast, accessible color scheme
        return {
            "primary": self.BASIC_COLORS["bright_blue"],  # Genesis primary
            "secondary": self.BASIC_COLORS["cyan"],  # Secondary actions
            "success": self.BASIC_COLORS["bright_green"],  # Success messages
            "warning": self.BASIC_COLORS["bright_yellow"],  # Warnings
            "error": self.BASIC_COLORS["bright_red"],  # Errors
            "info": self.BASIC_COLORS["bright_cyan"],  # Information
            "muted": self.BASIC_COLORS["bright_black"],  # Muted text
            "highlight": self.BASIC_COLORS["bright_white"],  # Important text
            "accent": self.BASIC_COLORS["bright_magenta"],  # Accent elements
        }

    def get_status_colors(self) -> Dict[str, str]:
        """Get status-specific color mapping."""
        if not self.supports_color:
            return {
                key: ""
                for key in ["running", "completed", "failed", "pending", "cancelled"]
            }

        return {
            "running": self.BASIC_COLORS["bright_blue"],
            "completed": self.BASIC_COLORS["bright_green"],
            "failed": self.BASIC_COLORS["bright_red"],
            "pending": self.BASIC_COLORS["bright_yellow"],
            "cancelled": self.BASIC_COLORS["bright_black"],
        }

    def colorize(self, text: str, color: str, style: Optional[str] = None) -> str:
        """Apply color and style to text with reset."""
        if not self.supports_color:
            return text

        semantic_colors = self.get_semantic_colors()
        color_code = semantic_colors.get(color, self.BASIC_COLORS.get(color, ""))
        style_code = self.STYLES.get(style, "") if style else ""

        if color_code or style_code:
            return f"{style_code}{color_code}{text}{self.RESET}"
        return text

    def format_status(self, status: str, text: str) -> str:
        """Format status text with appropriate colors."""
        status_colors = self.get_status_colors()
        color_code = status_colors.get(status.lower(), "")

        if not self.supports_color or not color_code:
            return f"[{status.upper()}] {text}"

        return f"{color_code}[{status.upper()}]{self.RESET} {text}"

    def format_command(self, command: str) -> str:
        """Format command text with highlighting."""
        return self.colorize(command, "primary", "bold")

    def format_path(self, path: str) -> str:
        """Format file path with highlighting."""
        return self.colorize(path, "accent")

    def format_value(self, value: str) -> str:
        """Format value with highlighting."""
        return self.colorize(value, "highlight")

    def format_error(self, error: str) -> str:
        """Format error message with appropriate styling."""
        return self.colorize(f"ERROR: {error}", "error", "bold")

    def format_warning(self, warning: str) -> str:
        """Format warning message with appropriate styling."""
        return self.colorize(f"WARNING: {warning}", "warning", "bold")

    def format_info(self, info: str) -> str:
        """Format info message with appropriate styling."""
        return self.colorize(f"INFO: {info}", "info")

    def format_success(self, success: str) -> str:
        """Format success message with appropriate styling."""
        return self.colorize(f"SUCCESS: {success}", "success", "bold")

    def create_progress_bar(self, percentage: float, width: int = 40) -> str:
        """Create a colored progress bar."""
        if not self.supports_color:
            filled = int(percentage * width / 100)
            return f"[{'=' * filled}{'-' * (width - filled)}] {percentage:.1f}%"

        filled = int(percentage * width / 100)
        bar_filled = "█" * filled
        bar_empty = "░" * (width - filled)

        # Color based on progress
        if percentage < 30:
            color = "error"
        elif percentage < 70:
            color = "warning"
        else:
            color = "success"

        colored_bar = self.colorize(bar_filled, color) + self.colorize(
            bar_empty, "muted"
        )
        return f"[{colored_bar}] {percentage:.1f}%"

    def format_table_headers(self, headers: list) -> list:
        """Format table headers with consistent styling."""
        return [self.colorize(header, "primary", "bold") for header in headers]

    def format_help_section(self, title: str, content: str) -> str:
        """Format help section with consistent styling."""
        formatted_title = self.colorize(title, "primary", "bold")
        return f"{formatted_title}\n{content}"

    def format_key_value(self, key: str, value: str, separator: str = ": ") -> str:
        """Format key-value pairs with consistent styling."""
        formatted_key = self.colorize(key, "info", "bold")
        formatted_value = self.colorize(value, "highlight")
        return f"{formatted_key}{separator}{formatted_value}"

    def strip_colors(self, text: str) -> str:
        """Remove all color codes from text."""
        import re

        # Remove ANSI escape sequences
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    def get_accessibility_info(self) -> Dict[str, str]:
        """Get accessibility information for the current color scheme."""
        return {
            "color_support": str(self.supports_color),
            "color_level": self.detect_color_level().name,
            "high_contrast": "true",  # Our scheme is high contrast by design
            "colorblind_friendly": "true",  # Uses distinct brightness levels
            "screen_reader_compatible": "true",  # Can be stripped to plain text
        }
