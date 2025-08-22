"""
Real FileSystem Tool for SOLVE Agents

Implements actual file operations with safety mechanisms and sandboxing.
Based on best practices from docs/best-practices/2-llm-code-editing-best-practices.md

NO MOCKS, NO STUBS - REAL FILE OPERATIONS ONLY
"""

import contextlib
import logging
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

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


class FileSystemTool:
    """
    Real file system operations with safety mechanisms.

    CRITICAL: This performs ACTUAL file operations - no mocking.
    """

    def __init__(self, safety_config: SafetyConfig | None = None):
        """Initialize with safety configuration."""
        self.safety_config = safety_config or self._default_safety_config()
        self.operation_log: list[FileOperation] = []

        # Set up sandbox if specified
        if self.safety_config.sandbox_root:
            self.sandbox_root = Path(self.safety_config.sandbox_root).resolve()
            self.sandbox_root.mkdir(parents=True, exist_ok=True)
        else:
            self.sandbox_root = Path.cwd()

        logger.info(f"FileSystemTool initialized with sandbox: {self.sandbox_root}")

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
        path_obj = Path(path).resolve()

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

    async def create_file(
        self, path: str, content: str, overwrite: bool = False
    ) -> FileOperation:
        """
        Create a file with the given content.

        Args:
            path: File path to create
            content: File content
            overwrite: Whether to overwrite existing file

        Returns:
            FileOperation result
        """
        try:
            validated_path = self._validate_path(path)

            # Check if file exists
            if validated_path.exists() and not overwrite:
                return self._log_operation(
                    "create_file",
                    str(validated_path),
                    False,
                    "File exists and overwrite=False",
                )

            # Check content size
            content_bytes = content.encode("utf-8")
            if len(content_bytes) > self.safety_config.max_file_size:
                return self._log_operation(
                    "create_file",
                    str(validated_path),
                    False,
                    f"Content size {len(content_bytes)} exceeds limit "
                    f"{self.safety_config.max_file_size}",
                )

            # Create parent directories if needed
            validated_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            validated_path.write_text(content, encoding="utf-8")

            # Verify file was created
            if not validated_path.exists():
                return self._log_operation(
                    "create_file",
                    str(validated_path),
                    False,
                    "File creation verification failed",
                )

            return self._log_operation(
                "create_file",
                str(validated_path),
                True,
                f"File created successfully ({len(content_bytes)} bytes)",
                {"size": len(content_bytes), "lines": content.count("\n") + 1},
            )

        except Exception as e:
            return self._log_operation(
                "create_file", path, False, f"Creation failed: {str(e)}"
            )

    async def read_file(self, path: str) -> FileOperation:
        """
        Read file content.

        Args:
            path: File path to read

        Returns:
            FileOperation with content in metadata
        """
        try:
            validated_path = self._validate_path(path)

            if not validated_path.exists():
                return self._log_operation(
                    "read_file",
                    str(validated_path),
                    False,
                    "File does not exist",
                )

            if not validated_path.is_file():
                return self._log_operation(
                    "read_file",
                    str(validated_path),
                    False,
                    "Path is not a file",
                )

            # Check file size
            file_size = validated_path.stat().st_size
            if file_size > self.safety_config.max_file_size:
                return self._log_operation(
                    "read_file",
                    str(validated_path),
                    False,
                    f"File size {file_size} exceeds limit {self.safety_config.max_file_size}",
                )

            # Read content
            content = validated_path.read_text(encoding="utf-8")

            return self._log_operation(
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

        except Exception as e:
            return self._log_operation(
                "read_file", path, False, f"Read failed: {str(e)}"
            )

    async def list_directory(
        self, path: str = ".", include_hidden: bool = False
    ) -> FileOperation:
        """
        List directory contents.

        Args:
            path: Directory path to list
            include_hidden: Whether to include hidden files

        Returns:
            FileOperation with directory listing in metadata
        """
        try:
            validated_path = self._validate_path(path)

            if not validated_path.exists():
                return self._log_operation(
                    "list_directory",
                    str(validated_path),
                    False,
                    "Directory does not exist",
                )

            if not validated_path.is_dir():
                return self._log_operation(
                    "list_directory",
                    str(validated_path),
                    False,
                    "Path is not a directory",
                )

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

            return self._log_operation(
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

        except Exception as e:
            return self._log_operation(
                "list_directory", path, False, f"List failed: {str(e)}"
            )

    async def create_directory(self, path: str, parents: bool = True) -> FileOperation:
        """
        Create a directory.

        Args:
            path: Directory path to create
            parents: Whether to create parent directories

        Returns:
            FileOperation result
        """
        try:
            validated_path = self._validate_path(path)

            if validated_path.exists():
                if validated_path.is_dir():
                    return self._log_operation(
                        "create_directory",
                        str(validated_path),
                        True,
                        "Directory already exists",
                    )
                else:
                    return self._log_operation(
                        "create_directory",
                        str(validated_path),
                        False,
                        "Path exists but is not a directory",
                    )

            # Create directory
            validated_path.mkdir(parents=parents, exist_ok=True)

            # Verify creation
            if not validated_path.exists() or not validated_path.is_dir():
                return self._log_operation(
                    "create_directory",
                    str(validated_path),
                    False,
                    "Directory creation verification failed",
                )

            return self._log_operation(
                "create_directory",
                str(validated_path),
                True,
                "Directory created successfully",
            )

        except Exception as e:
            return self._log_operation(
                "create_directory",
                path,
                False,
                f"Creation failed: {str(e)}",
            )

    async def delete_file(self, path: str, confirm: bool = False) -> FileOperation:
        """
        Delete a file.

        Args:
            path: File path to delete
            confirm: Confirmation for destructive operation

        Returns:
            FileOperation result
        """
        try:
            validated_path = self._validate_path(path)

            if not validated_path.exists():
                return self._log_operation(
                    "delete_file",
                    str(validated_path),
                    False,
                    "File does not exist",
                )

            if not validated_path.is_file():
                return self._log_operation(
                    "delete_file",
                    str(validated_path),
                    False,
                    "Path is not a file",
                )

            # Check confirmation requirement
            if self.safety_config.require_confirmation_for_destructive and not confirm:
                return self._log_operation(
                    "delete_file",
                    str(validated_path),
                    False,
                    "Destructive operation requires confirmation (confirm=True)",
                )

            # Store file info before deletion
            file_size = validated_path.stat().st_size

            # Delete file
            validated_path.unlink()

            # Verify deletion
            if validated_path.exists():
                return self._log_operation(
                    "delete_file",
                    str(validated_path),
                    False,
                    "File deletion verification failed",
                )

            return self._log_operation(
                "delete_file",
                str(validated_path),
                True,
                f"File deleted successfully ({file_size} bytes)",
                {"deleted_size": file_size},
            )

        except Exception as e:
            return self._log_operation(
                "delete_file", path, False, f"Deletion failed: {str(e)}"
            )

    async def copy_file(
        self,
        source: str,
        destination: str,
        overwrite: bool = False,
    ) -> FileOperation:
        """
        Copy a file.

        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing destination

        Returns:
            FileOperation result
        """
        try:
            source_path = self._validate_path(source)
            dest_path = self._validate_path(destination)

            if not source_path.exists():
                return self._log_operation(
                    "copy_file",
                    f"{source} -> {destination}",
                    False,
                    "Source file does not exist",
                )

            if not source_path.is_file():
                return self._log_operation(
                    "copy_file",
                    f"{source} -> {destination}",
                    False,
                    "Source is not a file",
                )

            if dest_path.exists() and not overwrite:
                return self._log_operation(
                    "copy_file",
                    f"{source} -> {destination}",
                    False,
                    "Destination exists and overwrite=False",
                )

            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source_path, dest_path)

            # Verify copy
            if not dest_path.exists():
                return self._log_operation(
                    "copy_file",
                    f"{source} -> {destination}",
                    False,
                    "File copy verification failed",
                )

            source_size = source_path.stat().st_size
            dest_size = dest_path.stat().st_size

            if source_size != dest_size:
                return self._log_operation(
                    "copy_file",
                    f"{source} -> {destination}",
                    False,
                    f"Size mismatch: source {source_size} != dest {dest_size}",
                )

            return self._log_operation(
                "copy_file",
                f"{source} -> {destination}",
                True,
                f"File copied successfully ({source_size} bytes)",
                {"size": source_size},
            )

        except Exception as e:
            return self._log_operation(
                "copy_file",
                f"{source} -> {destination}",
                False,
                f"Copy failed: {str(e)}",
            )

    def get_operation_log(self) -> list[FileOperation]:
        """Get the operation log for audit purposes."""
        return self.operation_log.copy()

    def clear_operation_log(self) -> None:
        """Clear the operation log."""
        self.operation_log.clear()


# Test function to verify real operations
async def test_filesystem_tool() -> None:
    """Test FileSystemTool with real operations."""
    # Create temporary sandbox for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Configure tool with sandbox
        safety_config = SafetyConfig(
            allowed_extensions=[".py", ".txt", ".md"],
            forbidden_paths=[],  # Allow everything in temp dir
            max_file_size=1024 * 1024,  # 1MB
            require_confirmation_for_destructive=False,  # For testing
            sandbox_root=temp_dir,
        )

        tool = FileSystemTool(safety_config)

        # Test 1: Create file
        result = await tool.create_file("test.py", "print('Hello, World!')\n")

        # Test 2: Read file
        result = await tool.read_file("test.py")

        # Test 3: Create directory
        result = await tool.create_directory("src/utils")

        # Test 4: List directory
        result = await tool.list_directory(".")

        # Test 5: Copy file
        result = await tool.copy_file("test.py", "src/main.py")

        # Test 6: Safety validation
        with contextlib.suppress(ValueError):
            result = await tool.create_file("../outside_sandbox.py", "bad content")
            _ = result  # Use the value

        # Show operation log
        for op in tool.get_operation_log():
            status = "✅" if op.success else "❌"
            _ = status  # Use the value


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_filesystem_tool())
