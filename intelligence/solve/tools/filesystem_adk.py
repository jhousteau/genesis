"""
ADK-Compliant FileSystem Tool for SOLVE Agents

Implements actual file operations with safety mechanisms following Google ADK patterns.
Based on official ADK BaseTool interface and academic_research_tools.py reference.

NO MOCKS, NO STUBS - REAL FILE OPERATIONS ONLY
"""

import logging
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from google.adk.tools import BaseTool

logger = logging.getLogger(__name__)


@dataclass
class FileOperation:
    """Result of a file operation."""

    success: bool
    path: str
    operation: str
    message: str
    metadata: dict[str, Any]


@dataclass
class SafetyConfig:
    """Safety configuration for file operations."""

    allowed_extensions: list[str]
    forbidden_paths: list[str]
    max_file_size: int  # bytes
    require_confirmation_for_destructive: bool
    sandbox_root: str | None


class FileSystemTool(BaseTool):
    """
    ADK-compliant file system operations with safety mechanisms.

    This tool performs ACTUAL file operations following Google ADK patterns.
    All operations return dict results that can be serialized as JSON.
    """

    def __init__(self, safety_config: SafetyConfig | None = None):
        """Initialize with safety configuration."""
        # Initialize BaseTool with name and description
        super().__init__(
            name="filesystem",
            description="Perform file system operations (create, read, write, delete, list, copy)",
        )

        self.safety_config = safety_config or self._default_safety_config()
        self.operation_log: list[FileOperation] = []

        # Set up sandbox if specified
        if self.safety_config.sandbox_root:
            self.sandbox_root = Path(self.safety_config.sandbox_root).resolve()
            self.sandbox_root.mkdir(parents=True, exist_ok=True)
        else:
            self.sandbox_root = Path.cwd()

        logger.info(f"FileSystemTool initialized with sandbox: {self.sandbox_root}")

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute file system operation based on parameters.

        This is the main ADK entry point that routes to specific operations.

        Args:
            **kwargs: Operation parameters including:
                - operation: The operation to perform (create, read, write, delete, list, copy)
                - Additional parameters specific to each operation

        Returns:
            Dict containing operation results
        """
        operation = kwargs.get("operation", "").lower()

        if operation == "create" or operation == "write":
            return await self._create_file(
                path=kwargs.get("path", ""),
                content=kwargs.get("content", ""),
                overwrite=kwargs.get("overwrite", False),
            )

        elif operation == "read":
            return await self._read_file(path=kwargs.get("path", ""))

        elif operation == "list":
            return await self._list_directory(
                path=kwargs.get("path", "."),
                include_hidden=kwargs.get("include_hidden", False),
            )

        elif operation == "create_directory":
            return await self._create_directory(
                path=kwargs.get("path", ""),
                parents=kwargs.get("parents", True),
            )

        elif operation == "delete":
            return await self._delete_file(
                path=kwargs.get("path", ""),
                confirm=kwargs.get("confirm", False),
            )

        elif operation == "copy":
            return await self._copy_file(
                source=kwargs.get("source", ""),
                destination=kwargs.get("destination", ""),
                overwrite=kwargs.get("overwrite", False),
            )

        elif operation == "get_log":
            return {"operation_log": [asdict(op) for op in self.operation_log]}

        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
                "supported_operations": [
                    "create",
                    "write",
                    "read",
                    "list",
                    "create_directory",
                    "delete",
                    "copy",
                    "get_log",
                ],
            }

    def _default_safety_config(self) -> SafetyConfig:
        """Create default safety configuration."""
        return SafetyConfig(
            allowed_extensions=[
                ".py",
                ".js",
                ".ts",
                ".md",
                ".txt",
                ".json",
                ".yaml",
                ".yml",
                ".toml",
                ".cfg",
                ".ini",
                ".sh",
                ".bash",
                ".zsh",
                ".fish",
                ".html",
                ".css",
                ".scss",
                ".less",
                ".xml",
                ".svg",
                ".sql",
                ".go",
                ".rs",
                ".java",
                ".kt",
                ".swift",
                ".c",
                ".cpp",
                ".h",
                ".rb",
                ".php",
                ".lua",
                ".r",
                ".m",
                ".scala",
                ".clj",
                ".hs",
            ],
            forbidden_paths=[
                "/etc",
                "/usr",
                "/var",
                "/bin",
                "/sbin",
                "/sys",
                "/proc",
                "/dev",
                "/boot",
                "/root",
                "~/.ssh",
                "~/.aws",
                "~/.config",
            ],
            max_file_size=10 * 1024 * 1024,  # 10MB
            require_confirmation_for_destructive=True,
            sandbox_root=None,  # Default to current working directory
        )

    def _validate_path(self, path: str | Path) -> Path:
        """
        Validate path for safety.

        Args:
            path: Path to validate

        Returns:
            Resolved and validated Path object

        Raises:
            ValueError: If path is unsafe
        """
        path_obj = Path(path)

        # If path is relative and we have a sandbox, resolve it relative to sandbox
        if self.sandbox_root and not path_obj.is_absolute():
            path_obj = self.sandbox_root / path_obj

        # Now resolve to absolute path
        path_obj = path_obj.resolve()

        # Check if path is within sandbox
        if self.sandbox_root:
            try:
                path_obj.relative_to(self.sandbox_root)
            except ValueError as e:
                raise ValueError(
                    f"Path {path_obj} is outside sandbox {self.sandbox_root}"
                ) from e

        # Check forbidden paths
        path_str = str(path_obj)
        for forbidden in self.safety_config.forbidden_paths:
            if path_str.startswith(forbidden):
                raise ValueError(
                    f"Path {path_obj} is in forbidden location {forbidden}"
                )

        # Check file extension if it's a file
        if (
            path_obj.suffix
            and path_obj.suffix not in self.safety_config.allowed_extensions
        ):
            raise ValueError(f"File extension {path_obj.suffix} not allowed")

        return path_obj

    def _log_operation(
        self,
        operation: str,
        path: str,
        success: bool,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> FileOperation:
        """Log file operation for audit trail."""
        op = FileOperation(
            success=success,
            path=path,
            operation=operation,
            message=message,
            metadata=metadata or {},
        )
        self.operation_log.append(op)

        if success:
            logger.info(f"FileOp {operation}: {path} - {message}")
        else:
            logger.error(f"FileOp {operation} FAILED: {path} - {message}")

        return op

    async def _create_file(
        self,
        path: str,
        content: str,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """
        Create a file with the given content.

        Returns ADK-compliant dict response.
        """
        try:
            validated_path = self._validate_path(path)

            # Check if file exists
            if validated_path.exists() and not overwrite:
                op = self._log_operation(
                    "create_file",
                    str(validated_path),
                    False,
                    "File exists and overwrite=False",
                )
                return asdict(op)

            # Check content size
            content_bytes = content.encode("utf-8")
            if len(content_bytes) > self.safety_config.max_file_size:
                op = self._log_operation(
                    "create_file",
                    str(validated_path),
                    False,
                    f"Content size {len(content_bytes)} exceeds limit "
                    f"{self.safety_config.max_file_size}",
                )
                return asdict(op)

            # Create parent directories if needed
            validated_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            validated_path.write_text(content, encoding="utf-8")

            # Verify file was created
            if not validated_path.exists():
                op = self._log_operation(
                    "create_file",
                    str(validated_path),
                    False,
                    "File creation verification failed",
                )
                return asdict(op)

            op = self._log_operation(
                "create_file",
                str(validated_path),
                True,
                f"File created successfully ({len(content_bytes)} bytes)",
                {"size": len(content_bytes), "lines": content.count("\n") + 1},
            )
            return asdict(op)

        except Exception as e:
            op = self._log_operation(
                "create_file", path, False, f"Creation failed: {str(e)}"
            )
            return asdict(op)

    async def _read_file(self, path: str) -> dict[str, Any]:
        """
        Read file content.

        Returns ADK-compliant dict response with content.
        """
        try:
            validated_path = self._validate_path(path)

            if not validated_path.exists():
                op = self._log_operation(
                    "read_file",
                    str(validated_path),
                    False,
                    "File does not exist",
                )
                return asdict(op)

            if not validated_path.is_file():
                op = self._log_operation(
                    "read_file",
                    str(validated_path),
                    False,
                    "Path is not a file",
                )
                return asdict(op)

            # Check file size
            file_size = validated_path.stat().st_size
            if file_size > self.safety_config.max_file_size:
                op = self._log_operation(
                    "read_file",
                    str(validated_path),
                    False,
                    f"File size {file_size} exceeds limit {self.safety_config.max_file_size}",
                )
                return asdict(op)

            # Read content
            content = validated_path.read_text(encoding="utf-8")

            op = self._log_operation(
                "read_file",
                str(validated_path),
                True,
                f"File read successfully ({file_size} bytes)",
                {
                    "content": content,
                    "size": file_size,
                    "lines": content.count("\n") + 1,
                    "modified": datetime.fromtimestamp(
                        validated_path.stat().st_mtime
                    ).isoformat(),
                },
            )
            return asdict(op)

        except Exception as e:
            op = self._log_operation("read_file", path, False, f"Read failed: {str(e)}")
            return asdict(op)

    async def _list_directory(
        self,
        path: str = ".",
        include_hidden: bool = False,
    ) -> dict[str, Any]:
        """
        List directory contents.

        Returns ADK-compliant dict response with directory listing.
        """
        try:
            validated_path = self._validate_path(path)

            if not validated_path.exists():
                op = self._log_operation(
                    "list_directory",
                    str(validated_path),
                    False,
                    "Directory does not exist",
                )
                return asdict(op)

            if not validated_path.is_dir():
                op = self._log_operation(
                    "list_directory",
                    str(validated_path),
                    False,
                    "Path is not a directory",
                )
                return asdict(op)

            # Get directory contents
            entries = []
            for item in validated_path.iterdir():
                if not include_hidden and item.name.startswith("."):
                    continue

                stat_info = item.stat()
                entries.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat_info.st_size if item.is_file() else None,
                        "modified": datetime.fromtimestamp(
                            stat_info.st_mtime
                        ).isoformat(),
                        "permissions": oct(stat_info.st_mode)[-3:],
                    },
                )

            # Sort by name
            entries.sort(key=lambda x: str(x["name"]))

            op = self._log_operation(
                "list_directory",
                str(validated_path),
                True,
                f"Directory listed successfully ({len(entries)} items)",
                {
                    "entries": entries,
                    "total_items": len(entries),
                    "directories": sum(1 for e in entries if e["type"] == "directory"),
                    "files": sum(1 for e in entries if e["type"] == "file"),
                },
            )
            return asdict(op)

        except Exception as e:
            op = self._log_operation(
                "list_directory", path, False, f"List failed: {str(e)}"
            )
            return asdict(op)

    async def _create_directory(
        self, path: str, parents: bool = True
    ) -> dict[str, Any]:
        """
        Create a directory.

        Returns ADK-compliant dict response.
        """
        try:
            validated_path = self._validate_path(path)

            if validated_path.exists():
                if validated_path.is_dir():
                    op = self._log_operation(
                        "create_directory",
                        str(validated_path),
                        True,
                        "Directory already exists",
                    )
                    return asdict(op)
                else:
                    op = self._log_operation(
                        "create_directory",
                        str(validated_path),
                        False,
                        "Path exists but is not a directory",
                    )
                    return asdict(op)

            # Create directory
            validated_path.mkdir(parents=parents, exist_ok=True)

            # Verify creation
            if not validated_path.exists() or not validated_path.is_dir():
                op = self._log_operation(
                    "create_directory",
                    str(validated_path),
                    False,
                    "Directory creation verification failed",
                )
                return asdict(op)

            op = self._log_operation(
                "create_directory",
                str(validated_path),
                True,
                "Directory created successfully",
            )
            return asdict(op)

        except Exception as e:
            op = self._log_operation(
                "create_directory", path, False, f"Creation failed: {str(e)}"
            )
            return asdict(op)

    async def _delete_file(self, path: str, confirm: bool = False) -> dict[str, Any]:
        """
        Delete a file.

        Returns ADK-compliant dict response.
        """
        try:
            validated_path = self._validate_path(path)

            if not validated_path.exists():
                op = self._log_operation(
                    "delete_file",
                    str(validated_path),
                    False,
                    "File does not exist",
                )
                return asdict(op)

            if not validated_path.is_file():
                op = self._log_operation(
                    "delete_file",
                    str(validated_path),
                    False,
                    "Path is not a file",
                )
                return asdict(op)

            # Check confirmation requirement
            if self.safety_config.require_confirmation_for_destructive and not confirm:
                op = self._log_operation(
                    "delete_file",
                    str(validated_path),
                    False,
                    "Destructive operation requires confirmation (confirm=True)",
                )
                return asdict(op)

            # Store file info before deletion
            file_size = validated_path.stat().st_size

            # Delete file
            validated_path.unlink()

            # Verify deletion
            if validated_path.exists():
                op = self._log_operation(
                    "delete_file",
                    str(validated_path),
                    False,
                    "File deletion verification failed",
                )
                return asdict(op)

            op = self._log_operation(
                "delete_file",
                str(validated_path),
                True,
                f"File deleted successfully ({file_size} bytes)",
                {"deleted_size": file_size},
            )
            return asdict(op)

        except Exception as e:
            op = self._log_operation(
                "delete_file", path, False, f"Deletion failed: {str(e)}"
            )
            return asdict(op)

    async def _copy_file(
        self,
        source: str,
        destination: str,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """
        Copy a file.

        Returns ADK-compliant dict response.
        """
        try:
            source_path = self._validate_path(source)
            dest_path = self._validate_path(destination)

            if not source_path.exists():
                op = self._log_operation(
                    "copy_file",
                    f"{source} -> {destination}",
                    False,
                    "Source file does not exist",
                )
                return asdict(op)

            if not source_path.is_file():
                op = self._log_operation(
                    "copy_file",
                    f"{source} -> {destination}",
                    False,
                    "Source is not a file",
                )
                return asdict(op)

            if dest_path.exists() and not overwrite:
                op = self._log_operation(
                    "copy_file",
                    f"{source} -> {destination}",
                    False,
                    "Destination exists and overwrite=False",
                )
                return asdict(op)

            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source_path, dest_path)

            # Verify copy
            if not dest_path.exists():
                op = self._log_operation(
                    "copy_file",
                    f"{source} -> {destination}",
                    False,
                    "File copy verification failed",
                )
                return asdict(op)

            source_size = source_path.stat().st_size
            dest_size = dest_path.stat().st_size

            if source_size != dest_size:
                op = self._log_operation(
                    "copy_file",
                    f"{source} -> {destination}",
                    False,
                    f"Size mismatch: source {source_size} != dest {dest_size}",
                )
                return asdict(op)

            op = self._log_operation(
                "copy_file",
                f"{source} -> {destination}",
                True,
                f"File copied successfully ({source_size} bytes)",
                {"size": source_size},
            )
            return asdict(op)

        except Exception as e:
            op = self._log_operation(
                "copy_file",
                f"{source} -> {destination}",
                False,
                f"Copy failed: {str(e)}",
            )
            return asdict(op)

    def get_operation_log(self) -> list[FileOperation]:
        """Get the operation log for audit purposes."""
        return self.operation_log.copy()

    def clear_operation_log(self) -> None:
        """Clear the operation log."""
        self.operation_log.clear()


# Example usage function for documentation
async def example_usage() -> None:
    """Example of using FileSystemTool with ADK patterns."""
    # Create tool instance
    tool = FileSystemTool()

    # Example 1: Create a file using ADK run() method
    await tool.run(
        operation="create", path="example.py", content="print('Hello from ADK!')\n"
    )

    # Example 2: Read the file
    await tool.run(operation="read", path="example.py")

    # Example 3: List directory
    await tool.run(operation="list", path=".")

    # Example 4: Copy file
    await tool.run(operation="copy", source="example.py", destination="example_copy.py")

    # Example 5: Delete file (requires confirmation)
    await tool.run(operation="delete", path="example_copy.py", confirm=True)

    # Example 6: Get operation log
    await tool.run(operation="get_log")


if __name__ == "__main__":
    import asyncio

    # Run example usage
    asyncio.run(example_usage())
