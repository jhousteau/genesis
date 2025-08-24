"""
Terminal Adapter - Responsive Design Implementation
Provides adaptive CLI interface for different terminal environments.
"""

import os
import shutil
import sys
from typing import Optional, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TerminalAdapter:
    """
    Responsive terminal adapter following REACT methodology.

    R - Responsive: Adapts to terminal width and capabilities
    E - Efficient: Minimal terminal queries and caching
    A - Accessible: Screen reader and alternative terminal support
    C - Connected: Integrates with Genesis configuration
    T - Tested: Comprehensive terminal compatibility testing
    """

    def __init__(self):
        self._width_cache: Optional[int] = None
        self._height_cache: Optional[int] = None
        self._color_support: Optional[bool] = None
        self._unicode_support: Optional[bool] = None
        self._capabilities: Optional[Dict[str, bool]] = None

    @property
    def width(self) -> int:
        """Get terminal width with responsive caching."""
        if self._width_cache is None:
            try:
                # Try to get terminal size
                size = shutil.get_terminal_size()
                self._width_cache = size.columns
            except OSError:
                # Fallback for non-terminal environments
                self._width_cache = 80
        return self._width_cache

    @property
    def height(self) -> int:
        """Get terminal height with responsive caching."""
        if self._height_cache is None:
            try:
                size = shutil.get_terminal_size()
                self._height_cache = size.lines
            except OSError:
                self._height_cache = 24
        return self._height_cache

    @property
    def supports_color(self) -> bool:
        """Check if terminal supports color output."""
        if self._color_support is None:
            # Check various indicators of color support
            self._color_support = (
                sys.stdout.isatty()
                and os.getenv("TERM") != "dumb"
                and (
                    "color" in os.getenv("TERM", "").lower()
                    or os.getenv("COLORTERM") is not None
                    or os.getenv("FORCE_COLOR") is not None
                )
            )
        return self._color_support

    @property
    def supports_unicode(self) -> bool:
        """Check if terminal supports unicode characters."""
        if self._unicode_support is None:
            try:
                # Test unicode output
                sys.stdout.write("\u2713")
                sys.stdout.flush()
                self._unicode_support = True
            except UnicodeEncodeError:
                self._unicode_support = False
            except Exception:
                self._unicode_support = False
        return self._unicode_support

    def get_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive terminal capabilities."""
        if self._capabilities is None:
            self._capabilities = {
                "width": self.width,
                "height": self.height,
                "color_support": self.supports_color,
                "unicode_support": self.supports_unicode,
                "is_tty": sys.stdout.isatty(),
                "term_type": os.getenv("TERM", "unknown"),
                "color_term": os.getenv("COLORTERM"),
                "ssh_session": "SSH_CONNECTION" in os.environ,
                "mobile_terminal": self.width < 80 or "MOBILE" in os.environ,
                "accessibility_mode": os.getenv("ACCESSIBILITY_MODE") == "true",
            }

            # Determine layout mode based on width
            if self.width >= 120:
                self._capabilities["layout_mode"] = "wide"
            elif self.width >= 80:
                self._capabilities["layout_mode"] = "standard"
            else:
                self._capabilities["layout_mode"] = "narrow"

        return self._capabilities

    def clear_screen(self) -> None:
        """Clear terminal screen if supported."""
        if sys.stdout.isatty():
            if os.name == "nt":  # Windows
                os.system("cls")
            else:  # Unix/Linux/macOS
                os.system("clear")

    def move_cursor(self, row: int, col: int) -> None:
        """Move cursor to specific position if supported."""
        if sys.stdout.isatty() and self.supports_color:
            sys.stdout.write(f"\033[{row};{col}H")
            sys.stdout.flush()

    def hide_cursor(self) -> None:
        """Hide terminal cursor if supported."""
        if sys.stdout.isatty() and self.supports_color:
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

    def show_cursor(self) -> None:
        """Show terminal cursor if supported."""
        if sys.stdout.isatty() and self.supports_color:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    def get_responsive_columns(self, min_cols: int = 2, max_cols: int = 5) -> int:
        """Calculate optimal number of columns for responsive layout."""
        width = self.width

        if width < 60:
            return 1
        elif width < 100:
            return min(2, max_cols)
        elif width < 140:
            return min(3, max_cols)
        elif width < 180:
            return min(4, max_cols)
        else:
            return min(max_cols, max_cols)

    def wrap_text(self, text: str, max_width: Optional[int] = None) -> str:
        """Wrap text to fit terminal width."""
        if max_width is None:
            max_width = max(40, self.width - 4)  # Leave margin

        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)

            # If adding this word would exceed the line length
            if current_length + word_length + len(current_line) > max_width:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    current_length = word_length
                else:
                    # Word is longer than max width, break it
                    lines.append(word[:max_width])
                    current_line = []
                    current_length = 0
            else:
                current_line.append(word)
                current_length += word_length

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)

    def truncate_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Truncate text to fit terminal width with ellipsis."""
        if max_length is None:
            max_length = self.width - 4

        if len(text) <= max_length:
            return text

        ellipsis = "..." if self.supports_unicode else "..."
        return text[: max_length - len(ellipsis)] + ellipsis

    def format_table_responsive(self, data: list, headers: list) -> str:
        """Format table data responsively based on terminal width."""
        capabilities = self.get_capabilities()

        if not data:
            return "No data to display"

        # Calculate column widths
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(header)
            for row in data:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            col_widths.append(max_width)

        # Adjust for narrow terminals
        if capabilities["layout_mode"] == "narrow":
            # Vertical layout for narrow terminals
            result = []
            for row in data:
                result.append("---")
                for i, (header, value) in enumerate(zip(headers, row)):
                    result.append(f"{header}: {value}")
            return "\n".join(result)

        # Horizontal table layout
        total_width = sum(col_widths) + len(headers) * 3 - 1

        if total_width > self.width:
            # Truncate columns to fit
            available_width = self.width - len(headers) * 3 + 1
            scale_factor = available_width / sum(col_widths)
            col_widths = [max(8, int(w * scale_factor)) for w in col_widths]

        # Format table
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

        result = [separator]

        # Header row
        header_row = "|"
        for i, (header, width) in enumerate(zip(headers, col_widths)):
            truncated_header = header[:width]
            header_row += f" {truncated_header.ljust(width)} |"
        result.append(header_row)
        result.append(separator)

        # Data rows
        for row in data:
            data_row = "|"
            for i, (value, width) in enumerate(zip(row, col_widths)):
                truncated_value = str(value)[:width]
                data_row += f" {truncated_value.ljust(width)} |"
            result.append(data_row)

        result.append(separator)
        return "\n".join(result)

    def invalidate_cache(self) -> None:
        """Invalidate cached terminal properties (for terminal resize)."""
        self._width_cache = None
        self._height_cache = None
        self._capabilities = None

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for terminal resize."""
        import signal

        def handle_resize(signum, frame):
            self.invalidate_cache()
            logger.debug("Terminal resized, cache invalidated")

        try:
            signal.signal(signal.SIGWINCH, handle_resize)
        except AttributeError:
            # SIGWINCH not available on Windows
            pass
