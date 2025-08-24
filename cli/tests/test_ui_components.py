"""
User Interface Components Testing
Comprehensive testing for CLI UI following REACT methodology validation.
"""

import pytest
import sys
import os
from io import StringIO
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the parent directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.ui.terminal import TerminalAdapter
from cli.ui.colors import ColorScheme, ColorLevel
from cli.ui.progress import ProgressIndicator, TaskProgress, LongRunningOperation
from cli.ui.formatter import OutputFormatter
from cli.ui.help import HelpSystem
from cli.ui.interactive import InteractivePrompt, PromptChoice, ValidationResult


class TestTerminalAdapter:
    """Test terminal adaptation and responsive design."""

    def test_initialization(self):
        """Test terminal adapter initialization."""
        adapter = TerminalAdapter()
        assert adapter._width_cache is None
        assert adapter._height_cache is None
        assert adapter._color_support is None
        assert adapter._unicode_support is None

    def test_width_detection(self):
        """Test terminal width detection."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value = MagicMock(columns=120, lines=30)
            adapter = TerminalAdapter()
            assert adapter.width == 120

    def test_width_fallback(self):
        """Test terminal width fallback when detection fails."""
        with patch("shutil.get_terminal_size", side_effect=OSError):
            adapter = TerminalAdapter()
            assert adapter.width == 80  # Default fallback

    def test_color_support_detection(self):
        """Test color support detection."""
        with patch("sys.stdout.isatty", return_value=True):
            with patch.dict("os.environ", {"TERM": "xterm-256color"}):
                adapter = TerminalAdapter()
                assert adapter.supports_color is True

    def test_no_color_environment(self):
        """Test NO_COLOR environment variable handling."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}):
            adapter = TerminalAdapter()
            assert adapter.supports_color is False

    def test_unicode_support_detection(self):
        """Test unicode support detection."""
        adapter = TerminalAdapter()

        with patch("sys.stdout.write") as mock_write:
            with patch("sys.stdout.flush"):
                mock_write.return_value = None  # No exception
                result = adapter.supports_unicode
                # Should attempt to write unicode character
                mock_write.assert_called()

    def test_capabilities_comprehensive(self):
        """Test comprehensive capability detection."""
        with patch("shutil.get_terminal_size") as mock_size:
            with patch("sys.stdout.isatty", return_value=True):
                with patch.dict("os.environ", {"TERM": "xterm-256color"}):
                    mock_size.return_value = MagicMock(columns=100, lines=30)
                    adapter = TerminalAdapter()

                    capabilities = adapter.get_capabilities()

                    assert capabilities["width"] == 100
                    assert capabilities["height"] == 30
                    assert capabilities["is_tty"] is True
                    assert capabilities["layout_mode"] == "standard"
                    assert "term_type" in capabilities

    def test_responsive_columns_calculation(self):
        """Test responsive column calculation."""
        adapter = TerminalAdapter()

        with patch.object(adapter, "width", 50):
            assert adapter.get_responsive_columns() == 1

        with patch.object(adapter, "width", 100):
            assert adapter.get_responsive_columns() == 2

        with patch.object(adapter, "width", 150):
            assert adapter.get_responsive_columns() == 3

    def test_text_wrapping(self):
        """Test text wrapping functionality."""
        adapter = TerminalAdapter()

        long_text = (
            "This is a very long line that should be wrapped at the specified width"
        )
        wrapped = adapter.wrap_text(long_text, max_width=20)

        lines = wrapped.split("\n")
        for line in lines:
            assert len(line) <= 20

    def test_text_truncation(self):
        """Test text truncation with ellipsis."""
        adapter = TerminalAdapter()

        long_text = "This is a very long text that should be truncated"
        truncated = adapter.truncate_text(long_text, max_length=20)

        assert len(truncated) <= 20
        assert truncated.endswith("...") or truncated.endswith("...")

    def test_cache_invalidation(self):
        """Test cache invalidation on terminal resize."""
        adapter = TerminalAdapter()

        # Populate cache
        _ = adapter.width
        _ = adapter.height

        # Invalidate cache
        adapter.invalidate_cache()

        assert adapter._width_cache is None
        assert adapter._height_cache is None


class TestColorScheme:
    """Test color scheme and accessibility features."""

    def test_initialization(self):
        """Test color scheme initialization."""
        scheme = ColorScheme()
        assert scheme._color_level is None
        assert scheme._supports_color is None

    def test_color_level_detection_truecolor(self):
        """Test truecolor detection."""
        with patch.dict("os.environ", {"COLORTERM": "truecolor"}):
            scheme = ColorScheme()
            assert scheme.detect_color_level() == ColorLevel.TRUECOLOR

    def test_color_level_detection_256color(self):
        """Test 256 color detection."""
        with patch.dict("os.environ", {"TERM": "xterm-256color"}):
            scheme = ColorScheme()
            assert scheme.detect_color_level() == ColorLevel.EXTENDED

    def test_no_color_detection(self):
        """Test NO_COLOR environment variable."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}):
            scheme = ColorScheme()
            assert scheme.detect_color_level() == ColorLevel.NONE

    def test_semantic_colors_with_support(self):
        """Test semantic color mapping with color support."""
        with patch("sys.stdout.isatty", return_value=True):
            with patch.dict("os.environ", {"TERM": "xterm-color"}):
                scheme = ColorScheme()
                colors = scheme.get_semantic_colors()

                assert "primary" in colors
                assert "error" in colors
                assert "success" in colors
                assert colors["primary"]  # Should not be empty

    def test_semantic_colors_without_support(self):
        """Test semantic color mapping without color support."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}):
            scheme = ColorScheme()
            colors = scheme.get_semantic_colors()

            assert "primary" in colors
            assert colors["primary"] == ""  # Should be empty

    def test_colorize_with_support(self):
        """Test text colorization with color support."""
        with patch("sys.stdout.isatty", return_value=True):
            with patch.dict("os.environ", {"TERM": "xterm-color"}):
                scheme = ColorScheme()

                colored_text = scheme.colorize("test", "primary")
                assert colored_text != "test"  # Should have color codes
                assert colored_text.endswith(scheme.RESET)

    def test_colorize_without_support(self):
        """Test text colorization without color support."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}):
            scheme = ColorScheme()

            colored_text = scheme.colorize("test", "primary")
            assert colored_text == "test"  # Should be unchanged

    def test_progress_bar_creation(self):
        """Test progress bar creation."""
        with patch("sys.stdout.isatty", return_value=True):
            with patch.dict("os.environ", {"TERM": "xterm-color"}):
                scheme = ColorScheme()

                progress_bar = scheme.create_progress_bar(50.0, width=20)
                assert "50.0%" in progress_bar
                assert len(progress_bar) > 20  # Should include percentage

    def test_strip_colors(self):
        """Test color stripping functionality."""
        scheme = ColorScheme()

        colored_text = f"{scheme.BASIC_COLORS['red']}test{scheme.RESET}"
        plain_text = scheme.strip_colors(colored_text)

        assert plain_text == "test"

    def test_accessibility_info(self):
        """Test accessibility information."""
        scheme = ColorScheme()
        info = scheme.get_accessibility_info()

        assert "color_support" in info
        assert "high_contrast" in info
        assert "colorblind_friendly" in info
        assert info["high_contrast"] == "true"
        assert info["colorblind_friendly"] == "true"


class TestProgressIndicator:
    """Test progress indication and real-time feedback."""

    def test_initialization(self):
        """Test progress indicator initialization."""
        progress = ProgressIndicator()
        assert progress._current_progress == 0.0
        assert progress._message == ""
        assert progress._active is False

    def test_start_stop_cycle(self):
        """Test start/stop cycle."""
        progress = ProgressIndicator()

        progress.start("Testing...")
        assert progress._active is True
        assert progress._message == "Testing..."

        progress.stop("Complete")
        assert progress._active is False

    def test_progress_update(self):
        """Test progress updates."""
        progress = ProgressIndicator()

        progress.start("Testing...")
        progress.update(50.0, "Half done")

        assert progress._current_progress == 50.0
        assert progress._message == "Half done"

        progress.stop()

    def test_unicode_support_detection(self):
        """Test unicode support detection for spinner."""
        terminal_adapter = MagicMock()
        terminal_adapter.supports_unicode = True

        progress = ProgressIndicator(terminal_adapter=terminal_adapter)
        assert progress._supports_unicode() is True

    def test_context_manager(self):
        """Test progress indicator context manager."""
        progress = ProgressIndicator()

        with progress.context("Testing context"):
            assert progress._active is True

        assert progress._active is False


class TestTaskProgress:
    """Test task-based progress tracking."""

    def test_initialization(self):
        """Test task progress initialization."""
        task_progress = TaskProgress(5)
        assert task_progress.total_steps == 5
        assert task_progress.current_step == 0

    def test_step_progression(self):
        """Test step progression."""
        task_progress = TaskProgress(3)
        task_progress.start("Starting tasks")

        task_progress.next_step("Step 1")
        assert task_progress.current_step == 1

        task_progress.next_step("Step 2")
        assert task_progress.current_step == 2

        task_progress.complete()

    def test_context_manager(self):
        """Test task progress context manager."""
        task_progress = TaskProgress(2)

        with task_progress.context("Testing"):
            task_progress.next_step("Step 1")
            task_progress.next_step("Step 2")


class TestOutputFormatter:
    """Test output formatting and visualization."""

    def test_initialization(self):
        """Test output formatter initialization."""
        formatter = OutputFormatter()
        assert formatter.terminal_adapter is None
        assert formatter.color_scheme is None

    def test_json_formatting(self):
        """Test JSON output formatting."""
        formatter = OutputFormatter()

        data = {"key": "value", "number": 123}
        formatted = formatter.format_json(data)

        assert "key" in formatted
        assert "value" in formatted
        assert "123" in formatted

    def test_yaml_formatting(self):
        """Test YAML output formatting."""
        formatter = OutputFormatter()

        data = {"key": "value", "list": [1, 2, 3]}
        formatted = formatter.format_yaml(data)

        assert "key: value" in formatted

    def test_table_formatting_with_dicts(self):
        """Test table formatting with dictionary data."""
        formatter = OutputFormatter()

        data = [{"name": "item1", "value": 100}, {"name": "item2", "value": 200}]

        formatted = formatter.format_table(data)
        assert "name" in formatted
        assert "value" in formatted
        assert "item1" in formatted

    def test_list_formatting(self):
        """Test list output formatting."""
        formatter = OutputFormatter()

        data = ["item1", "item2", "item3"]
        formatted = formatter.format_list(data)

        assert "• item1" in formatted
        assert "• item2" in formatted

    def test_tree_formatting(self):
        """Test tree structure formatting."""
        formatter = OutputFormatter()

        data = {"root": {"branch1": "leaf1", "branch2": {"subbranch": "leaf2"}}}

        formatted = formatter.format_tree(data)
        assert "root" in formatted
        assert "branch1" in formatted

    def test_status_formatting(self):
        """Test status message formatting."""
        color_scheme = ColorScheme()
        formatter = OutputFormatter(color_scheme=color_scheme)

        status_msg = formatter.format_status("running", "Operation in progress")
        assert "RUNNING" in status_msg.upper()
        assert "Operation in progress" in status_msg

    def test_error_details_formatting(self):
        """Test error details formatting."""
        formatter = OutputFormatter()

        error_msg = formatter.format_error_details(
            "Something went wrong",
            suggestions=["Try this", "Or that"],
            context={"command": "test"},
        )

        assert "Something went wrong" in error_msg
        assert "Try this" in error_msg
        assert "command" in error_msg


class TestHelpSystem:
    """Test interactive help system."""

    def test_initialization(self):
        """Test help system initialization."""
        help_system = HelpSystem()
        assert isinstance(help_system._help_database, dict)
        assert "vm" in help_system._help_database
        assert "container" in help_system._help_database

    def test_main_help(self):
        """Test main help generation."""
        help_system = HelpSystem()
        main_help = help_system.get_main_help()

        assert "Genesis Universal Infrastructure Platform" in main_help
        assert "vm" in main_help
        assert "container" in main_help
        assert "infra" in main_help

    def test_topic_help(self):
        """Test specific topic help."""
        help_system = HelpSystem()
        vm_help = help_system.get_topic_help("vm")

        assert "VM Management" in vm_help
        assert "create-pool" in vm_help

    def test_command_suggestions(self):
        """Test command suggestions."""
        help_system = HelpSystem()

        suggestions = help_system.suggest_commands("v")
        assert any("vm" in s for s in suggestions)

        suggestions = help_system.suggest_commands("con")
        assert any("container" in s for s in suggestions)

    def test_contextual_help(self):
        """Test contextual help based on errors."""
        help_system = HelpSystem()

        contextual = help_system.get_contextual_help("permission denied")
        assert (
            "authentication" in contextual.lower() or "permission" in contextual.lower()
        )


class TestInteractivePrompt:
    """Test interactive prompts and user interaction."""

    def test_initialization(self):
        """Test interactive prompt initialization."""
        prompt = InteractivePrompt()
        assert prompt.terminal_adapter is None
        assert prompt.color_scheme is None

    @patch("builtins.input", return_value="y")
    def test_confirm_yes(self, mock_input):
        """Test confirmation prompt with yes response."""
        prompt = InteractivePrompt()
        result = prompt.confirm("Continue?")
        assert result is True

    @patch("builtins.input", return_value="n")
    def test_confirm_no(self, mock_input):
        """Test confirmation prompt with no response."""
        prompt = InteractivePrompt()
        result = prompt.confirm("Continue?")
        assert result is False

    @patch("builtins.input", return_value="")
    def test_confirm_default(self, mock_input):
        """Test confirmation prompt with default value."""
        prompt = InteractivePrompt()
        result = prompt.confirm("Continue?", default=True)
        assert result is True

    @patch("builtins.input", return_value="test input")
    def test_text_input(self, mock_input):
        """Test text input prompt."""
        prompt = InteractivePrompt()
        result = prompt.text_input("Enter text:")
        assert result == "test input"

    @patch("builtins.input", return_value="")
    def test_text_input_default(self, mock_input):
        """Test text input with default value."""
        prompt = InteractivePrompt()
        result = prompt.text_input("Enter text:", default="default value")
        assert result == "default value"

    @patch("builtins.input", return_value="1")
    def test_choice_selection(self, mock_input):
        """Test choice selection."""
        prompt = InteractivePrompt()
        choices = [
            PromptChoice("option1", "Option 1"),
            PromptChoice("option2", "Option 2"),
        ]

        with patch("builtins.print"):  # Mock print to avoid output during tests
            result = prompt.choice("Choose:", choices)
            assert result == "option1"

    def test_validation_result(self):
        """Test validation result structure."""
        valid_result = ValidationResult(True, "Valid input")
        assert valid_result.valid is True
        assert valid_result.message == "Valid input"

        invalid_result = ValidationResult(False, "Invalid input", "Try this")
        assert invalid_result.valid is False
        assert invalid_result.suggestion == "Try this"


@pytest.mark.integration
class TestUIIntegration:
    """Integration tests for UI components working together."""

    def test_complete_ui_workflow(self):
        """Test complete UI workflow with all components."""
        # Initialize all components
        terminal_adapter = TerminalAdapter()
        color_scheme = ColorScheme()
        output_formatter = OutputFormatter(terminal_adapter, color_scheme)
        help_system = HelpSystem(terminal_adapter, color_scheme)

        # Test that components work together
        assert output_formatter.terminal_adapter == terminal_adapter
        assert output_formatter.color_scheme == color_scheme
        assert help_system.terminal_adapter == terminal_adapter

        # Test output formatting with color
        data = {"status": "success", "message": "All systems operational"}
        formatted = output_formatter.format_output(data, "json")

        # Should produce valid JSON
        import json

        parsed = json.loads(
            formatted.replace("\033[0m", "")
            .replace("\033[94m", "")
            .replace("\033[92m", "")
        )
        assert parsed["status"] == "success"

    def test_responsive_behavior(self):
        """Test responsive behavior across different terminal sizes."""
        terminal_adapter = TerminalAdapter()
        color_scheme = ColorScheme()
        output_formatter = OutputFormatter(terminal_adapter, color_scheme)

        # Test with narrow terminal
        with patch.object(terminal_adapter, "width", 40):
            capabilities = terminal_adapter.get_capabilities()
            assert capabilities["layout_mode"] == "narrow"

            # Test table formatting adapts
            data = [{"name": "very long name", "value": "very long value"}]
            formatted = output_formatter.format_table(data)
            # Should adapt to narrow layout (specific format may vary)
            assert formatted is not None

    def test_accessibility_compliance(self):
        """Test accessibility features across components."""
        color_scheme = ColorScheme()

        # Test that accessibility info is available
        accessibility = color_scheme.get_accessibility_info()
        assert accessibility["high_contrast"] == "true"
        assert accessibility["colorblind_friendly"] == "true"
        assert accessibility["screen_reader_compatible"] == "true"

        # Test that colors can be stripped for screen readers
        colored_text = color_scheme.colorize("Important message", "error", "bold")
        plain_text = color_scheme.strip_colors(colored_text)
        assert plain_text == "Important message"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
