"""
Output Formatter - Efficient Data Visualization
Provides structured output formatting with responsive design.
"""

import json
import yaml
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OutputFormatter:
    """
    Efficient output formatter following REACT methodology.

    R - Responsive: Formats adapt to terminal width and capabilities
    E - Efficient: Minimal processing overhead with caching
    A - Accessible: Clear structure with screen reader compatibility
    C - Connected: Consistent with Genesis design patterns
    T - Tested: Reliable formatting across all data types
    """

    def __init__(self, terminal_adapter=None, color_scheme=None):
        self.terminal_adapter = terminal_adapter
        self.color_scheme = color_scheme
        self._format_cache: Dict[str, Any] = {}

    def format_output(self, data: Any, format_type: str = "text") -> str:
        """Format data according to specified output format."""
        if format_type == "json":
            return self.format_json(data)
        elif format_type == "yaml":
            return self.format_yaml(data)
        elif format_type == "table":
            return self.format_table(data)
        elif format_type == "list":
            return self.format_list(data)
        elif format_type == "tree":
            return self.format_tree(data)
        else:  # text format (default)
            return self.format_text(data)

    def format_json(self, data: Any) -> str:
        """Format data as JSON with proper indentation."""
        try:
            formatted = json.dumps(data, indent=2, default=self._json_serializer)

            if self.color_scheme and self.color_scheme.supports_color:
                # Add syntax highlighting for JSON
                return self._highlight_json(formatted)
            return formatted
        except Exception as e:
            logger.error(f"JSON formatting error: {e}")
            return str(data)

    def format_yaml(self, data: Any) -> str:
        """Format data as YAML with proper structure."""
        try:
            formatted = yaml.dump(
                data, default_flow_style=False, allow_unicode=True, sort_keys=False
            )

            if self.color_scheme and self.color_scheme.supports_color:
                return self._highlight_yaml(formatted)
            return formatted
        except Exception as e:
            logger.error(f"YAML formatting error: {e}")
            return str(data)

    def format_table(self, data: Any, headers: Optional[List[str]] = None) -> str:
        """Format data as responsive table."""
        if not isinstance(data, list) or not data:
            return "No data to display"

        # Handle different data structures
        if isinstance(data[0], dict):
            if not headers:
                headers = list(data[0].keys())
            rows = [[item.get(header, "") for header in headers] for item in data]
        elif isinstance(data[0], (list, tuple)):
            rows = data
        else:
            # Convert scalar values to single-column table
            headers = headers or ["Value"]
            rows = [[item] for item in data]

        if not headers:
            headers = [f"Column {i+1}" for i in range(len(rows[0]) if rows else 0)]

        # Use terminal adapter for responsive table formatting
        if self.terminal_adapter:
            return self.terminal_adapter.format_table_responsive(rows, headers)

        # Fallback formatting
        return self._format_simple_table(rows, headers)

    def format_list(self, data: Any, indent: int = 0) -> str:
        """Format data as structured list."""
        if not data:
            return "No items to display"

        result = []
        indent_str = "  " * indent

        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    result.append(f"{indent_str}• {self._format_dict_item(item)}")
                else:
                    result.append(f"{indent_str}• {item}")
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    result.append(f"{indent_str}{self._format_key(key)}:")
                    result.append(self.format_list(value, indent + 1))
                else:
                    result.append(
                        f"{indent_str}{self._format_key(key)}: {self._format_value(value)}"
                    )
        else:
            result.append(f"{indent_str}• {data}")

        return "\n".join(result)

    def format_tree(
        self, data: Dict[str, Any], prefix: str = "", is_last: bool = True
    ) -> str:
        """Format data as tree structure."""
        if not isinstance(data, dict):
            return str(data)

        result = []
        items = list(data.items())

        for i, (key, value) in enumerate(items):
            is_last_item = i == len(items) - 1

            # Tree symbols
            if self.terminal_adapter and self.terminal_adapter.supports_unicode:
                connector = "└── " if is_last_item else "├── "
                extension = "    " if is_last_item else "│   "
            else:
                connector = "+-- " if is_last_item else "+-- "
                extension = "    " if is_last_item else "|   "

            formatted_key = self._format_key(key)

            if isinstance(value, dict) and value:
                result.append(f"{prefix}{connector}{formatted_key}")
                result.append(self.format_tree(value, prefix + extension, is_last_item))
            elif isinstance(value, list) and value:
                result.append(
                    f"{prefix}{connector}{formatted_key} ({len(value)} items)"
                )
                for j, item in enumerate(value):
                    item_is_last = j == len(value) - 1
                    if isinstance(item, dict):
                        result.append(f"{prefix}{extension}[{j}]")
                        result.append(
                            self.format_tree(
                                item,
                                prefix
                                + extension
                                + ("    " if item_is_last else "│   "),
                                item_is_last,
                            )
                        )
                    else:
                        result.append(
                            f"{prefix}{extension}[{j}] {self._format_value(item)}"
                        )
            else:
                result.append(
                    f"{prefix}{connector}{formatted_key}: {self._format_value(value)}"
                )

        return "\n".join(filter(None, result))

    def format_text(self, data: Any) -> str:
        """Format data as human-readable text."""
        if isinstance(data, dict):
            return self._format_dict_text(data)
        elif isinstance(data, list):
            return self._format_list_text(data)
        else:
            return str(data)

    def format_status(
        self, status: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format status message with consistent styling."""
        if self.color_scheme:
            formatted_status = self.color_scheme.format_status(status, message)
        else:
            formatted_status = f"[{status.upper()}] {message}"

        if details:
            details_text = self.format_list(details, indent=1)
            return f"{formatted_status}\n{details_text}"

        return formatted_status

    def format_command_help(
        self,
        command: str,
        description: str,
        usage: str,
        examples: Optional[List[str]] = None,
    ) -> str:
        """Format command help with consistent styling."""
        result = []

        # Command header
        if self.color_scheme:
            result.append(self.color_scheme.format_help_section("COMMAND", command))
            result.append("")
            result.append(
                self.color_scheme.format_help_section("DESCRIPTION", description)
            )
            result.append("")
            result.append(self.color_scheme.format_help_section("USAGE", usage))
        else:
            result.append(f"COMMAND\n{command}")
            result.append(f"\nDESCRIPTION\n{description}")
            result.append(f"\nUSAGE\n{usage}")

        if examples:
            result.append("")
            if self.color_scheme:
                result.append(self.color_scheme.format_help_section("EXAMPLES", ""))
            else:
                result.append("EXAMPLES")

            for i, example in enumerate(examples, 1):
                if self.color_scheme:
                    result.append(f"  {i}. {self.color_scheme.format_command(example)}")
                else:
                    result.append(f"  {i}. {example}")

        return "\n".join(result)

    def format_error_details(
        self,
        error: str,
        suggestions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format error message with helpful details."""
        result = []

        if self.color_scheme:
            result.append(self.color_scheme.format_error(error))
        else:
            result.append(f"ERROR: {error}")

        if suggestions:
            result.append("")
            if self.color_scheme:
                result.append(self.color_scheme.format_help_section("SUGGESTIONS", ""))
            else:
                result.append("SUGGESTIONS:")

            for suggestion in suggestions:
                result.append(f"  • {suggestion}")

        if context:
            result.append("")
            if self.color_scheme:
                result.append(self.color_scheme.format_help_section("CONTEXT", ""))
            else:
                result.append("CONTEXT:")
            result.append(self.format_list(context, indent=1))

        return "\n".join(result)

    def format_summary(
        self,
        title: str,
        data: Dict[str, Any],
        highlight_keys: Optional[List[str]] = None,
    ) -> str:
        """Format summary information with highlighting."""
        result = []

        if self.color_scheme:
            result.append(self.color_scheme.format_help_section(title.upper(), ""))
        else:
            result.append(f"{title.upper()}")
        result.append("")

        highlight_keys = highlight_keys or []

        for key, value in data.items():
            if self.color_scheme:
                if key in highlight_keys:
                    formatted_line = self.color_scheme.format_key_value(key, str(value))
                    formatted_line = self.color_scheme.colorize(
                        formatted_line, "success", "bold"
                    )
                else:
                    formatted_line = self.color_scheme.format_key_value(key, str(value))
            else:
                formatted_line = f"{key}: {value}"

            result.append(f"  {formatted_line}")

        return "\n".join(result)

    def _format_simple_table(self, rows: List[List[str]], headers: List[str]) -> str:
        """Simple table formatting fallback."""
        if not rows:
            return "No data"

        all_rows = [headers] + rows

        # Calculate column widths
        col_widths = []
        for col_idx in range(len(headers)):
            max_width = 0
            for row in all_rows:
                if col_idx < len(row):
                    max_width = max(max_width, len(str(row[col_idx])))
            col_widths.append(max_width)

        # Format table
        result = []
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

        result.append(separator)

        # Header row
        header_row = "|"
        for i, (header, width) in enumerate(zip(headers, col_widths)):
            header_row += f" {header.ljust(width)} |"
        result.append(header_row)
        result.append(separator)

        # Data rows
        for row in rows:
            data_row = "|"
            for i, width in enumerate(col_widths):
                value = str(row[i]) if i < len(row) else ""
                data_row += f" {value.ljust(width)} |"
            result.append(data_row)

        result.append(separator)
        return "\n".join(result)

    def _format_dict_text(self, data: Dict[str, Any]) -> str:
        """Format dictionary as readable text."""
        result = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                result.append(f"{self._format_key(key)}:")
                result.append(self._indent_text(str(value), 2))
            else:
                result.append(f"{self._format_key(key)}: {self._format_value(value)}")
        return "\n".join(result)

    def _format_list_text(self, data: List[Any]) -> str:
        """Format list as readable text."""
        if not data:
            return "Empty list"

        result = []
        for i, item in enumerate(data):
            if isinstance(item, dict):
                result.append(f"{i + 1}. {self._format_dict_item(item)}")
            else:
                result.append(f"{i + 1}. {item}")
        return "\n".join(result)

    def _format_dict_item(self, item: Dict[str, Any]) -> str:
        """Format dictionary item for list display."""
        if "name" in item:
            return f"{item['name']} ({', '.join(f'{k}: {v}' for k, v in item.items() if k != 'name')})"
        elif "id" in item:
            return f"ID: {item['id']} ({', '.join(f'{k}: {v}' for k, v in item.items() if k != 'id')})"
        else:
            return ", ".join(f"{k}: {v}" for k, v in item.items())

    def _format_key(self, key: str) -> str:
        """Format dictionary key with styling."""
        if self.color_scheme:
            return self.color_scheme.colorize(key, "info", "bold")
        return key

    def _format_value(self, value: Any) -> str:
        """Format value with appropriate styling."""
        if isinstance(value, bool):
            color = "success" if value else "error"
        elif isinstance(value, (int, float)):
            color = "highlight"
        elif isinstance(value, datetime):
            value = value.isoformat()
            color = "muted"
        else:
            color = "highlight"

        if self.color_scheme:
            return self.color_scheme.colorize(str(value), color)
        return str(value)

    def _indent_text(self, text: str, spaces: int) -> str:
        """Indent text by specified number of spaces."""
        indent = " " * spaces
        return "\n".join(indent + line for line in text.split("\n"))

    def _highlight_json(self, json_text: str) -> str:
        """Add syntax highlighting to JSON."""
        # Simple JSON highlighting - could be enhanced
        import re

        # Highlight strings (values)
        json_text = re.sub(
            r'"([^"]*)"(\s*:)',
            lambda m: self.color_scheme.colorize(f'"{m.group(1)}"', "info", "bold")
            + m.group(2),
            json_text,
        )

        # Highlight values
        def highlight_value(m):
            quoted_value = '"' + m.group(1) + '"'
            return f': {self.color_scheme.colorize(quoted_value, "highlight")}'

        json_text = re.sub(r':\s*"([^"]*)"', highlight_value, json_text)

        return json_text

    def _highlight_yaml(self, yaml_text: str) -> str:
        """Add syntax highlighting to YAML."""
        lines = yaml_text.split("\n")
        highlighted_lines = []

        for line in lines:
            if ":" in line and not line.strip().startswith("#"):
                key, value = line.split(":", 1)
                key_highlighted = self.color_scheme.colorize(key, "info", "bold")
                if value.strip():
                    value_highlighted = self.color_scheme.colorize(value, "highlight")
                    highlighted_lines.append(f"{key_highlighted}:{value_highlighted}")
                else:
                    highlighted_lines.append(f"{key_highlighted}:")
            else:
                highlighted_lines.append(line)

        return "\n".join(highlighted_lines)

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for complex objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return str(obj)
