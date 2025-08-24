"""
Progress Indicator - Efficient Progress Visualization
Provides real-time progress feedback with minimal performance impact.
"""

import sys
import time
import threading
from typing import Optional, Any, Callable
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class ProgressIndicator:
    """
    Efficient progress indicator following REACT methodology.

    R - Responsive: Adapts to terminal width and capabilities
    E - Efficient: Minimal CPU usage and smooth updates
    A - Accessible: Screen reader compatible with text updates
    C - Connected: Integrates with Genesis operations
    T - Tested: Reliable progress tracking across operations
    """

    def __init__(self, terminal_adapter=None, color_scheme=None):
        self.terminal_adapter = terminal_adapter
        self.color_scheme = color_scheme
        self._current_progress = 0.0
        self._message = ""
        self._active = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._update_interval = 0.1  # 100ms updates for smooth animation

    def start(self, message: str = "Processing...") -> None:
        """Start progress indicator."""
        if self._active:
            return

        self._active = True
        self._message = message
        self._current_progress = 0.0
        self._stop_event.clear()

        if sys.stdout.isatty():
            self._thread = threading.Thread(target=self._update_loop, daemon=True)
            self._thread.start()
        else:
            # Non-TTY fallback - just print the message
            print(f"{message}")

    def update(self, progress: float, message: Optional[str] = None) -> None:
        """Update progress percentage and optional message."""
        self._current_progress = max(0.0, min(100.0, progress))
        if message:
            self._message = message

    def stop(self, final_message: Optional[str] = None) -> None:
        """Stop progress indicator."""
        if not self._active:
            return

        self._active = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        # Clear the progress line and show final message
        if sys.stdout.isatty() and self.terminal_adapter:
            sys.stdout.write("\r" + " " * self.terminal_adapter.width + "\r")

        if final_message:
            print(final_message)

    def _update_loop(self) -> None:
        """Main update loop for progress animation."""
        spinner_chars = (
            ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]
            if self._supports_unicode()
            else ["|", "/", "-", "\\"]
        )
        spinner_idx = 0

        while not self._stop_event.wait(self._update_interval):
            if not self._active:
                break

            try:
                self._render_progress(spinner_chars[spinner_idx % len(spinner_chars)])
                spinner_idx += 1
            except Exception as e:
                logger.debug(f"Progress render error: {e}")
                break

    def _render_progress(self, spinner_char: str) -> None:
        """Render current progress state."""
        if not self.terminal_adapter:
            return

        width = self.terminal_adapter.width
        message = self._message
        progress = self._current_progress

        # Create progress bar
        bar_width = max(20, min(40, width // 3))
        filled = int(progress * bar_width / 100)

        if self.color_scheme and self.color_scheme.supports_color:
            # Colored progress bar
            bar_filled = self.color_scheme.colorize("█" * filled, "primary")
            bar_empty = self.color_scheme.colorize("░" * (bar_width - filled), "muted")
            progress_bar = f"[{bar_filled}{bar_empty}]"

            # Colored spinner and message
            spinner = self.color_scheme.colorize(spinner_char, "accent")
            formatted_message = self.color_scheme.colorize(message, "info")
        else:
            # Plain progress bar
            progress_bar = f"[{'=' * filled}{'-' * (bar_width - filled)}]"
            spinner = spinner_char
            formatted_message = message

        # Format complete line
        progress_text = f"{spinner} {formatted_message} {progress_bar} {progress:.1f}%"

        # Truncate to fit terminal width
        if (
            len(
                self.color_scheme.strip_colors(progress_text)
                if self.color_scheme
                else progress_text
            )
            > width
        ):
            available_width = (
                width - len(progress_bar) - 20
            )  # Reserve space for bar and percentage
            truncated_message = message[: max(10, available_width)] + "..."
            if self.color_scheme and self.color_scheme.supports_color:
                truncated_message = self.color_scheme.colorize(
                    truncated_message, "info"
                )
            progress_text = (
                f"{spinner} {truncated_message} {progress_bar} {progress:.1f}%"
            )

        # Write to terminal
        sys.stdout.write(f"\r{progress_text}")
        sys.stdout.flush()

    def _supports_unicode(self) -> bool:
        """Check if terminal supports unicode characters."""
        if self.terminal_adapter:
            return self.terminal_adapter.supports_unicode
        try:
            sys.stdout.write("\u2713")
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False

    @contextmanager
    def context(
        self, message: str = "Processing...", final_message: Optional[str] = None
    ):
        """Context manager for automatic progress management."""
        try:
            self.start(message)
            yield self
        finally:
            self.stop(final_message)


class TaskProgress:
    """Enhanced task progress with step tracking."""

    def __init__(self, total_steps: int, terminal_adapter=None, color_scheme=None):
        self.total_steps = total_steps
        self.current_step = 0
        self.progress_indicator = ProgressIndicator(terminal_adapter, color_scheme)
        self.step_messages = []

    def start(self, message: str = "Starting tasks...") -> None:
        """Start task progress tracking."""
        self.progress_indicator.start(message)

    def next_step(self, message: str) -> None:
        """Move to next step with message."""
        self.current_step += 1
        progress = (self.current_step / self.total_steps) * 100
        step_message = f"Step {self.current_step}/{self.total_steps}: {message}"
        self.step_messages.append(step_message)
        self.progress_indicator.update(progress, step_message)

    def complete(self, final_message: Optional[str] = None) -> None:
        """Complete task progress."""
        if not final_message:
            final_message = f"Completed {self.total_steps} steps successfully"
        self.progress_indicator.stop(final_message)

    @contextmanager
    def context(self, message: str = "Executing tasks..."):
        """Context manager for task progress."""
        try:
            self.start(message)
            yield self
        finally:
            self.complete()


class LongRunningOperation:
    """Progress tracking for long-running operations."""

    def __init__(self, operation_name: str, terminal_adapter=None, color_scheme=None):
        self.operation_name = operation_name
        self.progress_indicator = ProgressIndicator(terminal_adapter, color_scheme)
        self.start_time = None

    def start(self) -> None:
        """Start long-running operation."""
        self.start_time = time.time()
        self.progress_indicator.start(f"{self.operation_name}...")

    def update_status(self, status: str, progress: Optional[float] = None) -> None:
        """Update operation status."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        message = f"{self.operation_name} - {status} ({elapsed:.1f}s)"

        if progress is not None:
            self.progress_indicator.update(progress, message)
        else:
            # Just update message for indeterminate progress
            self.progress_indicator._message = message

    def complete(
        self, success: bool = True, final_message: Optional[str] = None
    ) -> None:
        """Complete long-running operation."""
        elapsed = time.time() - self.start_time if self.start_time else 0

        if not final_message:
            status = "completed" if success else "failed"
            final_message = f"{self.operation_name} {status} in {elapsed:.1f}s"

        self.progress_indicator.stop(final_message)

    @contextmanager
    def context(self):
        """Context manager for long-running operation."""
        try:
            self.start()
            yield self
        finally:
            self.complete()


class BatchProgress:
    """Progress tracking for batch operations."""

    def __init__(
        self,
        batch_name: str,
        total_items: int,
        terminal_adapter=None,
        color_scheme=None,
    ):
        self.batch_name = batch_name
        self.total_items = total_items
        self.processed_items = 0
        self.failed_items = 0
        self.progress_indicator = ProgressIndicator(terminal_adapter, color_scheme)

    def start(self) -> None:
        """Start batch processing."""
        message = f"{self.batch_name} (0/{self.total_items})"
        self.progress_indicator.start(message)

    def item_processed(self, item_name: str, success: bool = True) -> None:
        """Mark item as processed."""
        self.processed_items += 1
        if not success:
            self.failed_items += 1

        progress = (self.processed_items / self.total_items) * 100
        status = f"({self.processed_items}/{self.total_items})"
        if self.failed_items > 0:
            status += f" - {self.failed_items} failed"

        message = f"{self.batch_name} {status} - {item_name}"
        self.progress_indicator.update(progress, message)

    def complete(self, final_message: Optional[str] = None) -> None:
        """Complete batch processing."""
        if not final_message:
            if self.failed_items > 0:
                final_message = f"{self.batch_name} completed: {self.processed_items - self.failed_items} succeeded, {self.failed_items} failed"
            else:
                final_message = f"{self.batch_name} completed successfully: {self.processed_items} items processed"

        self.progress_indicator.stop(final_message)

    @contextmanager
    def context(self):
        """Context manager for batch progress."""
        try:
            self.start()
            yield self
        finally:
            self.complete()
