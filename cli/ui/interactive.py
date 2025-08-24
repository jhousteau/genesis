"""
Interactive Prompt - Connected User Interaction
Provides interactive prompts and user guidance with accessibility features.
"""

import sys
from typing import Any, List, Optional, Dict, Callable, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PromptChoice:
    """Structure for interactive prompt choices."""

    value: Any
    display: str
    description: Optional[str] = None
    disabled: bool = False


@dataclass
class ValidationResult:
    """Result of input validation."""

    valid: bool
    message: Optional[str] = None
    suggestion: Optional[str] = None


class InteractivePrompt:
    """
    Interactive prompt system following REACT methodology.

    R - Responsive: Prompts adapt to terminal capabilities and user preferences
    E - Efficient: Fast input processing with intelligent defaults
    A - Accessible: Screen reader compatible with clear guidance
    C - Connected: Integrates with Genesis configuration and context
    T - Tested: Reliable input validation and error handling
    """

    def __init__(self, terminal_adapter=None, color_scheme=None):
        self.terminal_adapter = terminal_adapter
        self.color_scheme = color_scheme
        self._input_history: List[str] = []

    def confirm(self, message: str, default: bool = True) -> bool:
        """Get yes/no confirmation from user."""
        default_text = "Y/n" if default else "y/N"

        if self.color_scheme:
            formatted_message = self.color_scheme.colorize(message, "info")
            prompt = f"{formatted_message} [{default_text}]: "
        else:
            prompt = f"{message} [{default_text}]: "

        while True:
            try:
                response = input(prompt).strip().lower()

                if not response:
                    return default

                if response in ["y", "yes", "true", "1"]:
                    return True
                elif response in ["n", "no", "false", "0"]:
                    return False
                else:
                    if self.color_scheme:
                        error_msg = self.color_scheme.format_error(
                            "Please enter 'y' or 'n'"
                        )
                        print(error_msg)
                    else:
                        print("Please enter 'y' or 'n'")
                    continue

            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                return False
            except EOFError:
                return default

    def text_input(
        self,
        message: str,
        default: Optional[str] = None,
        validator: Optional[Callable[[str], ValidationResult]] = None,
        password: bool = False,
    ) -> Optional[str]:
        """Get text input from user with validation."""

        if default:
            if self.color_scheme:
                formatted_message = self.color_scheme.colorize(message, "info")
                default_display = self.color_scheme.colorize(f"[{default}]", "muted")
                prompt = f"{formatted_message} {default_display}: "
            else:
                prompt = f"{message} [{default}]: "
        else:
            if self.color_scheme:
                formatted_message = self.color_scheme.colorize(message, "info")
                prompt = f"{formatted_message}: "
            else:
                prompt = f"{message}: "

        while True:
            try:
                if password:
                    import getpass

                    response = getpass.getpass(prompt)
                else:
                    response = input(prompt)

                # Use default if no input provided
                if not response.strip() and default is not None:
                    response = default

                # Validate input
                if validator:
                    validation = validator(response)
                    if not validation.valid:
                        if self.color_scheme:
                            error_msg = self.color_scheme.format_error(
                                validation.message or "Invalid input"
                            )
                            print(error_msg)
                        else:
                            print(f"Error: {validation.message or 'Invalid input'}")

                        if validation.suggestion:
                            if self.color_scheme:
                                suggestion = self.color_scheme.colorize(
                                    f"Suggestion: {validation.suggestion}", "info"
                                )
                                print(suggestion)
                            else:
                                print(f"Suggestion: {validation.suggestion}")
                        continue

                # Store in history (except passwords)
                if not password and response.strip():
                    self._input_history.append(response.strip())

                return response

            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                return None
            except EOFError:
                return default

    def choice(
        self, message: str, choices: List[PromptChoice], default: Optional[Any] = None
    ) -> Optional[Any]:
        """Get choice selection from user."""

        if not choices:
            if self.color_scheme:
                error_msg = self.color_scheme.format_error("No choices available")
                print(error_msg)
            else:
                print("Error: No choices available")
            return None

        # Display choices
        if self.color_scheme:
            formatted_message = self.color_scheme.colorize(message, "info", "bold")
            print(formatted_message)
        else:
            print(message)
        print()

        choice_map = {}
        default_index = None

        for i, choice in enumerate(choices, 1):
            if choice.disabled:
                if self.color_scheme:
                    choice_text = self.color_scheme.colorize(
                        f"  {i}. {choice.display} (disabled)", "muted"
                    )
                    print(choice_text)
                else:
                    print(f"  {i}. {choice.display} (disabled)")
            else:
                choice_map[str(i)] = choice.value

                if choice.value == default:
                    default_index = i
                    if self.color_scheme:
                        choice_text = self.color_scheme.colorize(
                            f"  {i}. {choice.display} (default)", "primary", "bold"
                        )
                        print(choice_text)
                    else:
                        print(f"  {i}. {choice.display} (default)")
                else:
                    if self.color_scheme:
                        choice_text = self.color_scheme.colorize(
                            f"  {i}. {choice.display}", "highlight"
                        )
                        print(choice_text)
                    else:
                        print(f"  {i}. {choice.display}")

                # Show description if available
                if choice.description:
                    if self.color_scheme:
                        desc_text = self.color_scheme.colorize(
                            f"     {choice.description}", "muted"
                        )
                        print(desc_text)
                    else:
                        print(f"     {choice.description}")

        print()

        # Get user selection
        if default_index:
            prompt = f"Enter choice [1-{len(choices)}] (default: {default_index}): "
        else:
            prompt = f"Enter choice [1-{len(choices)}]: "

        while True:
            try:
                response = input(prompt).strip()

                if not response and default_index:
                    return default

                if response in choice_map:
                    return choice_map[response]
                else:
                    if self.color_scheme:
                        error_msg = self.color_scheme.format_error(
                            f"Please enter a number between 1 and {len(choices)}"
                        )
                        print(error_msg)
                    else:
                        print(f"Please enter a number between 1 and {len(choices)}")

            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                return None
            except EOFError:
                return default

    def multi_choice(
        self,
        message: str,
        choices: List[PromptChoice],
        min_choices: int = 0,
        max_choices: Optional[int] = None,
    ) -> Optional[List[Any]]:
        """Get multiple choice selections from user."""

        if not choices:
            if self.color_scheme:
                error_msg = self.color_scheme.format_error("No choices available")
                print(error_msg)
            else:
                print("Error: No choices available")
            return None

        # Display choices
        if self.color_scheme:
            formatted_message = self.color_scheme.colorize(message, "info", "bold")
            print(formatted_message)
        else:
            print(message)

        print("(Enter numbers separated by commas, e.g., '1,3,5')")
        print()

        choice_map = {}

        for i, choice in enumerate(choices, 1):
            if choice.disabled:
                if self.color_scheme:
                    choice_text = self.color_scheme.colorize(
                        f"  {i}. {choice.display} (disabled)", "muted"
                    )
                    print(choice_text)
                else:
                    print(f"  {i}. {choice.display} (disabled)")
            else:
                choice_map[str(i)] = choice.value

                if self.color_scheme:
                    choice_text = self.color_scheme.colorize(
                        f"  {i}. {choice.display}", "highlight"
                    )
                    print(choice_text)
                else:
                    print(f"  {i}. {choice.display}")

                if choice.description:
                    if self.color_scheme:
                        desc_text = self.color_scheme.colorize(
                            f"     {choice.description}", "muted"
                        )
                        print(desc_text)
                    else:
                        print(f"     {choice.description}")

        print()
        prompt = f"Enter choices [1-{len(choices)}]: "

        while True:
            try:
                response = input(prompt).strip()

                if not response:
                    if min_choices == 0:
                        return []
                    else:
                        if self.color_scheme:
                            error_msg = self.color_scheme.format_error(
                                f"Please select at least {min_choices} choice(s)"
                            )
                            print(error_msg)
                        else:
                            print(f"Please select at least {min_choices} choice(s)")
                        continue

                # Parse selections
                selections = []
                try:
                    selected_indices = [s.strip() for s in response.split(",")]

                    for index in selected_indices:
                        if index in choice_map:
                            selections.append(choice_map[index])
                        else:
                            raise ValueError(f"Invalid choice: {index}")

                    # Validate selection count
                    if len(selections) < min_choices:
                        if self.color_scheme:
                            error_msg = self.color_scheme.format_error(
                                f"Please select at least {min_choices} choice(s)"
                            )
                            print(error_msg)
                        else:
                            print(f"Please select at least {min_choices} choice(s)")
                        continue

                    if max_choices and len(selections) > max_choices:
                        if self.color_scheme:
                            error_msg = self.color_scheme.format_error(
                                f"Please select at most {max_choices} choice(s)"
                            )
                            print(error_msg)
                        else:
                            print(f"Please select at most {max_choices} choice(s)")
                        continue

                    return selections

                except ValueError as e:
                    if self.color_scheme:
                        error_msg = self.color_scheme.format_error(str(e))
                        print(error_msg)
                    else:
                        print(f"Error: {e}")

            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                return None
            except EOFError:
                return []

    def progress_confirmation(
        self,
        operation_name: str,
        details: Dict[str, Any],
        warnings: Optional[List[str]] = None,
    ) -> bool:
        """Get confirmation for potentially destructive operations."""

        if self.color_scheme:
            title = self.color_scheme.colorize(
                f"CONFIRM {operation_name.upper()}", "warning", "bold"
            )
            print(title)
        else:
            print(f"CONFIRM {operation_name.upper()}")

        print("=" * len(f"CONFIRM {operation_name.upper()}"))
        print()

        # Show operation details
        if self.color_scheme:
            details_title = self.color_scheme.colorize(
                "Operation Details:", "info", "bold"
            )
            print(details_title)
        else:
            print("Operation Details:")

        for key, value in details.items():
            if self.color_scheme:
                formatted_line = self.color_scheme.format_key_value(key, str(value))
                print(f"  {formatted_line}")
            else:
                print(f"  {key}: {value}")

        print()

        # Show warnings if any
        if warnings:
            if self.color_scheme:
                warning_title = self.color_scheme.colorize(
                    "WARNINGS:", "warning", "bold"
                )
                print(warning_title)
            else:
                print("WARNINGS:")

            for warning in warnings:
                if self.color_scheme:
                    warning_text = self.color_scheme.format_warning(warning)
                    print(f"  • {warning_text}")
                else:
                    print(f"  • WARNING: {warning}")
            print()

        # Get confirmation
        return self.confirm("Do you want to proceed?", default=False)

    def guided_setup(
        self, setup_name: str, steps: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Guide user through multi-step setup process."""

        if self.color_scheme:
            title = self.color_scheme.colorize(f"{setup_name} Setup", "primary", "bold")
            print(title)
        else:
            print(f"{setup_name} Setup")

        print("=" * len(f"{setup_name} Setup"))
        print()

        results = {}

        for i, step in enumerate(steps, 1):
            if self.color_scheme:
                step_title = self.color_scheme.colorize(
                    f"Step {i}/{len(steps)}: {step['title']}", "primary", "bold"
                )
                print(step_title)
            else:
                print(f"Step {i}/{len(steps)}: {step['title']}")

            if "description" in step:
                if self.color_scheme:
                    description = self.color_scheme.colorize(
                        step["description"], "info"
                    )
                    print(description)
                else:
                    print(step["description"])

            print()

            # Handle different step types
            step_type = step.get("type", "text")
            step_key = step["key"]

            if step_type == "confirm":
                result = self.confirm(step["message"], step.get("default", True))
            elif step_type == "choice":
                choices = [
                    PromptChoice(
                        value=c["value"],
                        display=c["display"],
                        description=c.get("description"),
                    )
                    for c in step["choices"]
                ]
                result = self.choice(step["message"], choices, step.get("default"))
            elif step_type == "text":
                result = self.text_input(
                    step["message"], step.get("default"), step.get("validator")
                )
            else:
                if self.color_scheme:
                    error_msg = self.color_scheme.format_error(
                        f"Unknown step type: {step_type}"
                    )
                    print(error_msg)
                else:
                    print(f"Error: Unknown step type: {step_type}")
                return None

            if result is None:
                if self.color_scheme:
                    cancelled_msg = self.color_scheme.colorize(
                        "Setup cancelled by user", "warning"
                    )
                    print(cancelled_msg)
                else:
                    print("Setup cancelled by user")
                return None

            results[step_key] = result
            print()

        # Summary
        if self.color_scheme:
            summary_title = self.color_scheme.colorize(
                "Setup Summary:", "success", "bold"
            )
            print(summary_title)
        else:
            print("Setup Summary:")

        for key, value in results.items():
            if self.color_scheme:
                formatted_line = self.color_scheme.format_key_value(key, str(value))
                print(f"  {formatted_line}")
            else:
                print(f"  {key}: {value}")

        print()

        if self.confirm("Confirm setup configuration?", default=True):
            return results
        else:
            return None

    def get_input_history(self) -> List[str]:
        """Get input history (excluding passwords)."""
        return self._input_history.copy()

    def clear_input_history(self) -> None:
        """Clear input history."""
        self._input_history.clear()
