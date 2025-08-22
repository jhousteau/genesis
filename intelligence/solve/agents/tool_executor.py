"""
Tool Execution Layer for Real Agent Integration

Enables agents to execute real file operations and other tools.
NO MOCKS - Real tool execution with safety validation.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from solve.tools.filesystem import FileSystemTool

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executes tools for agents with real operations and safety validation.

    Parses agent responses to identify tool calls and executes them safely.
    """

    def __init__(self, tools: dict[str, Any]):
        """Initialize tool executor with available tools."""
        self.tools = tools
        self.execution_history: list[dict[str, Any]] = []

    async def execute_tool_calls_from_response(
        self,
        response_input: str | list[Any],
    ) -> dict[str, Any]:
        """
        Parse agent response and execute any tool calls found.

        Args:
            response_input: Agent's response text (str) or ADK events (list)

        Returns:
            Dict with execution results and artifacts
        """
        # Handle both string responses and ADK events
        if isinstance(response_input, str):
            tool_calls = self._parse_tool_calls(response_input)
        else:
            # Handle ADK events directly
            tool_calls = self._parse_tool_calls_from_events(response_input)
            # Also extract text for traditional parsing
            text_content = self._extract_text_from_events(response_input)
            if text_content:
                tool_calls.extend(self._parse_tool_calls(text_content))

        if not tool_calls:
            return {
                "tool_calls_found": 0,
                "executions": [],
                "artifacts": {},
                "success": True,
            }

        logger.info(f"🔧 Found {len(tool_calls)} tool calls in response")

        execution_results = []
        artifacts = {}
        overall_success = True

        for i, call in enumerate(tool_calls, 1):
            logger.info(
                f"⚙️ Executing tool call {i}: {call['tool']} -> {call['operation']}"
            )

            try:
                result = await self._execute_single_tool_call(call)
                execution_results.append(result)

                # Collect artifacts
                if result.get("artifacts"):
                    artifacts.update(result["artifacts"])

                # Track overall success
                if not result.get("success", False):
                    overall_success = False

            except Exception as e:
                logger.error(f"❌ Tool call {i} failed: {e}")
                execution_results.append(
                    {
                        "tool": call["tool"],
                        "operation": call["operation"],
                        "success": False,
                        "error": str(e),
                        "parameters": call.get("parameters", {}),
                    },
                )
                overall_success = False

        # Record execution history
        response_preview = (
            str(response_input)[:200]
            if isinstance(response_input, str)
            else f"ADK events: {len(response_input)} events"
        )
        self.execution_history.append(
            {
                "response_text": response_preview,
                "tool_calls": len(tool_calls),
                "executions": execution_results,
                "overall_success": overall_success,
            },
        )

        return {
            "tool_calls_found": len(tool_calls),
            "executions": execution_results,
            "artifacts": artifacts,
            "success": overall_success,
        }

    def _parse_tool_calls(self, response_text: str) -> list[dict[str, Any]]:
        """
        Parse tool calls from agent response text.

        Looks for patterns like:
        - CREATE_FILE: path/to/file.py with content: "code here"
        - READ_FILE: path/to/file.py
        - LIST_DIRECTORY: path/to/dir
        """
        tool_calls = []

        # Pattern 1: CREATE_FILE operations
        create_patterns = [
            r'CREATE_FILE:\s*([^\s]+)\s+with\s+content:\s*["\']([^"\']*)["\']',
            r'create_file\(([^,]+),\s*["\']([^"\']*)["\']',
            r"create\s+file\s+([^\s]+):\s*```(?:python|js|ts|html|css|json)?\s*\n(.*?)\n```",
        ]

        for pattern in create_patterns:
            matches = re.finditer(pattern, response_text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                tool_calls.append(
                    {
                        "tool": "filesystem",
                        "operation": "create_file",
                        "parameters": {
                            "path": match.group(1).strip(),
                            "content": match.group(2).strip(),
                        },
                    },
                )

        # Pattern 2: READ_FILE operations
        read_patterns = [
            r"READ_FILE:\s*([^\s]+)",
            r"read_file\(([^)]+)\)",
            r"read\s+(?:file\s+)?([^\s]+\.(?:py|js|ts|md|txt|json|yaml|yml))",
        ]

        for pattern in read_patterns:
            matches = re.finditer(pattern, response_text, re.IGNORECASE)
            for match in matches:
                tool_calls.append(
                    {
                        "tool": "filesystem",
                        "operation": "read_file",
                        "parameters": {"path": match.group(1).strip()},
                    },
                )

        # Pattern 3: LIST_DIRECTORY operations
        list_patterns = [
            r"LIST_DIRECTORY:\s*([^\s]+)",
            r"list_directory\(([^)]+)\)",
            r"list\s+(?:directory\s+)?([^\s]+)",
        ]

        for pattern in list_patterns:
            matches = re.finditer(pattern, response_text, re.IGNORECASE)
            for match in matches:
                tool_calls.append(
                    {
                        "tool": "filesystem",
                        "operation": "list_directory",
                        "parameters": {"path": match.group(1).strip()},
                    },
                )

        # Pattern 4: COPY_FILE operations
        copy_patterns = [
            r"COPY_FILE:\s*([^\s]+)\s+to\s+([^\s]+)",
            r"copy_file\(([^,]+),\s*([^)]+)\)",
            r"copy\s+([^\s]+)\s+to\s+([^\s]+)",
        ]

        for pattern in copy_patterns:
            matches = re.finditer(pattern, response_text, re.IGNORECASE)
            for match in matches:
                tool_calls.append(
                    {
                        "tool": "filesystem",
                        "operation": "copy_file",
                        "parameters": {
                            "source_path": match.group(1).strip(),
                            "dest_path": match.group(2).strip(),
                        },
                    },
                )

        # Remove duplicates while preserving order
        seen = set()
        unique_calls = []
        for call in tool_calls:
            call_signature = f"{call['tool']}:{call['operation']}:{call['parameters']}"
            if call_signature not in seen:
                seen.add(call_signature)
                unique_calls.append(call)

        return unique_calls

    def _parse_tool_calls_from_events(self, events: list[Any]) -> list[dict[str, Any]]:
        """
        Parse tool calls directly from ADK events.

        Args:
            events: List of ADK events

        Returns:
            List of tool call dictionaries
        """
        tool_calls = []

        try:
            for event in events:
                # Extract text content using ADK event structure
                text_content = self._extract_text_from_event(event)
                if text_content:
                    # Parse traditional tool calls from event text
                    event_tool_calls = self._parse_tool_calls(text_content)
                    tool_calls.extend(event_tool_calls)

        except Exception as e:
            logger.error(f"Failed to parse tool calls from ADK events: {e}")

        return tool_calls

    def _extract_text_from_events(self, events: list[Any]) -> str:
        """
        Extract text content from multiple ADK events.

        Args:
            events: List of ADK events

        Returns:
            Combined text content
        """
        text_parts = []

        for event in events:
            text_content = self._extract_text_from_event(event)
            if text_content:
                text_parts.append(text_content)

        return "\n".join(text_parts)

    def _extract_text_from_event(self, event: Any) -> str | None:
        """
        Extract text content from a single ADK event.

        Based on hello_world sample: event.content.parts[0].text

        Args:
            event: Single ADK event

        Returns:
            Text content or None
        """
        try:
            # Primary ADK pattern from hello_world sample
            if hasattr(event, "content") and event.content:
                if hasattr(event.content, "parts") and event.content.parts:
                    if len(event.content.parts) > 0:
                        part = event.content.parts[0]
                        if hasattr(part, "text") and part.text:
                            return str(part.text)

            # Fallback patterns for different event structures
            if hasattr(event, "content") and event.content:
                # Direct string content
                if isinstance(event.content, str):
                    return event.content
                # Content as string representation
                content_str = str(event.content)
                if content_str and content_str != "None":
                    return content_str

            # Additional fallback patterns
            if hasattr(event, "message") and event.message:
                return str(event.message)
            if hasattr(event, "text") and event.text:
                return str(event.text)

        except Exception as e:
            logger.debug(f"Failed to extract text from event: {e}")

        return None

    async def _execute_single_tool_call(self, call: dict[str, Any]) -> dict[str, Any]:
        """Execute a single tool call safely."""
        tool_name = call["tool"]
        operation = call["operation"]
        parameters = call.get("parameters", {})

        if tool_name not in self.tools:
            return {
                "tool": tool_name,
                "operation": operation,
                "success": False,
                "error": f"Tool '{tool_name}' not available",
                "parameters": parameters,
            }

        tool = self.tools[tool_name]

        try:
            # Execute filesystem operations
            if tool_name == "filesystem" and isinstance(tool, FileSystemTool):
                return await self._execute_filesystem_operation(
                    tool, operation, parameters
                )
            else:
                return {
                    "tool": tool_name,
                    "operation": operation,
                    "success": False,
                    "error": f"Unknown tool type: {type(tool)}",
                    "parameters": parameters,
                }

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {
                "tool": tool_name,
                "operation": operation,
                "success": False,
                "error": str(e),
                "parameters": parameters,
            }

    async def _execute_filesystem_operation(
        self,
        tool: FileSystemTool,
        operation: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute filesystem tool operations."""

        try:
            # Handle relative paths by making them relative to the sandbox
            if operation in ["create_file", "read_file", "delete_file"]:
                path = parameters["path"]
                # If path is relative and doesn't start with sandbox, make it relative to sandbox
                if not path.startswith("/") and tool.safety_config.sandbox_root:
                    path = str(Path(tool.safety_config.sandbox_root) / path)
                    parameters = {**parameters, "path": path}
            elif operation in ["copy_file", "move_file"]:
                source_path = parameters["source_path"]
                dest_path = parameters["dest_path"]
                if not source_path.startswith("/") and tool.safety_config.sandbox_root:
                    source_path = str(
                        Path(tool.safety_config.sandbox_root) / source_path
                    )
                if not dest_path.startswith("/") and tool.safety_config.sandbox_root:
                    dest_path = str(Path(tool.safety_config.sandbox_root) / dest_path)
                parameters = {
                    **parameters,
                    "source_path": source_path,
                    "dest_path": dest_path,
                }

            if operation == "create_file":
                result = await tool.create_file(
                    path=parameters["path"],
                    content=parameters["content"],
                    overwrite=parameters.get("overwrite", False),
                )
            elif operation == "read_file":
                result = await tool.read_file(parameters["path"])
            elif operation == "list_directory":
                result = await tool.list_directory(parameters["path"])
            elif operation == "copy_file":
                result = await tool.copy_file(
                    source=parameters["source_path"],
                    destination=parameters["dest_path"],
                )
            elif operation == "delete_file":
                result = await tool.delete_file(parameters["path"])
            elif operation == "create_directory":
                result = await tool.create_directory(parameters["path"])
            # Note: move_file not implemented in FileSystemTool yet
            # elif operation == "move_file":
            #     result = await tool.move_file(
            #         source=parameters["source_path"], destination=parameters["dest_path"]
            #     )
            else:
                return {
                    "tool": "filesystem",
                    "operation": operation,
                    "success": False,
                    "error": f"Unknown filesystem operation: {operation}",
                    "parameters": parameters,
                }

            # Convert FileOperation to dict for JSON serialization
            # Content is stored in metadata for FileOperation
            content = result.metadata.get("content", "")

            return {
                "tool": "filesystem",
                "operation": operation,
                "success": result.success,
                "message": result.message,
                "path": result.path,
                "content_preview": (
                    content[:100] + "..." if len(content) > 100 else content
                ),
                "artifacts": {
                    f"file_{operation}": {
                        "path": result.path,
                        "success": result.success,
                        "operation_type": operation,
                        "size": len(content) if content else 0,
                        "metadata": result.metadata,
                    },
                },
                "parameters": parameters,
            }

        except Exception as e:
            logger.error(f"Filesystem operation failed: {e}")
            return {
                "tool": "filesystem",
                "operation": operation,
                "success": False,
                "error": str(e),
                "parameters": parameters,
            }

    def get_execution_summary(self) -> dict[str, Any]:
        """Get summary of all tool executions."""
        total_executions = len(self.execution_history)
        successful_executions = sum(
            1
            for exec_record in self.execution_history
            if exec_record["overall_success"]
        )

        tool_usage = {}
        for record in self.execution_history:
            for execution in record["executions"]:
                tool = execution["tool"]
                operation = execution["operation"]
                key = f"{tool}:{operation}"
                if key not in tool_usage:
                    tool_usage[key] = {"count": 0, "successes": 0}
                tool_usage[key]["count"] += 1
                if execution["success"]:
                    tool_usage[key]["successes"] += 1

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": (
                successful_executions / total_executions if total_executions > 0 else 0
            ),
            "tool_usage": tool_usage,
            "available_tools": list(self.tools.keys()),
        }


# Test function for tool executor
async def test_tool_executor() -> bool:
    """Test the tool executor with real operations."""
    # Import filesystem tool
    from solve.tools.filesystem import FileSystemTool, SafetyConfig

    # Create filesystem tool
    safety_config = SafetyConfig(
        allowed_extensions=[".py", ".txt", ".md"],
        forbidden_paths=["/etc", "/usr"],
        max_file_size=1024 * 1024,  # 1MB
        require_confirmation_for_destructive=False,
        sandbox_root="/Users/jameshousteau/source_code/solve/tmp",
    )

    filesystem_tool = FileSystemTool(safety_config)

    # Create executor
    executor = ToolExecutor({"filesystem": filesystem_tool})

    # Test parsing and execution
    test_response = """
    I need to create a test file to demonstrate the tool integration.

    CREATE_FILE: test_integration.py with content: "print('Tool integration working!')"

    Then I should READ_FILE: test_integration.py to verify it was created.

    Also, let me LIST_DIRECTORY: /Users/jameshousteau/source_code/solve/tmp to see what
    files are available.
    """

    try:
        result = await executor.execute_tool_calls_from_response(test_response)

        # Show execution summary
        summary = executor.get_execution_summary()
        _ = summary  # Use the value

        return bool(result["success"])

    except Exception:
        logger.exception("Tool executor test exception")
        return False


if __name__ == "__main__":
    asyncio.run(test_tool_executor())
