"""
ADK Tool Registry System

Implements a proper ADK tool registry following official patterns from:
- adk-python/src/google/adk/tools/toolbox.py
- adk-samples/python/agents/academic-research/tool_registry.py

This registry provides:
1. Tool discovery and registration
2. Categorization and metadata management
3. Dynamic tool loading
4. Integration with ADK's toolbox patterns
5. Tool introspection capabilities
"""

import importlib
import inspect
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Union

from google.adk.tools import BaseTool

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Standard tool categories for organization"""

    FILESYSTEM = "filesystem"
    GIT = "git"
    ANALYSIS = "analysis"
    TESTING = "testing"
    MONITORING = "monitoring"
    DOCUMENTATION = "documentation"
    COMMUNICATION = "communication"
    UTILITY = "utility"
    CUSTOM = "custom"
    # New categories for Issue #73
    INFRASTRUCTURE = "infrastructure"
    CLOUD = "cloud"
    DATABASE = "database"
    GRAPH = "graph"


@dataclass
class ToolMetadata:
    """Complete metadata for a registered tool"""

    name: str
    category: ToolCategory
    description: str
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    parameters_schema: dict[str, Any] = field(default_factory=dict)

    # ADK-specific metadata
    supports_async: bool = True
    supports_batch: bool = False
    supports_streaming: bool = False
    max_concurrency: int = 1
    timeout_seconds: int | None = None

    # Usage statistics
    usage_count: int = 0
    last_used: str | None = None
    avg_execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for serialization"""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "capabilities": self.capabilities,
            "required_permissions": self.required_permissions,
            "examples": self.examples,
            "parameters_schema": self.parameters_schema,
            "supports_async": self.supports_async,
            "supports_batch": self.supports_batch,
            "supports_streaming": self.supports_streaming,
            "max_concurrency": self.max_concurrency,
            "timeout_seconds": self.timeout_seconds,
            "usage_count": self.usage_count,
            "last_used": self.last_used,
            "avg_execution_time_ms": self.avg_execution_time_ms,
        }


@dataclass
class ToolRegistration:
    """Internal registration record for a tool"""

    tool_class: type[BaseTool]
    metadata: ToolMetadata
    instance: BaseTool | None = None
    is_singleton: bool = True

    def get_instance(self) -> BaseTool:
        """Get or create tool instance"""
        if self.is_singleton and self.instance:
            return self.instance

        instance = self.tool_class(name="", description="")
        if self.is_singleton:
            self.instance = instance
        return instance


class ToolRegistry:
    """
    Central registry for ADK tools with auto-discovery and management.

    Follows ADK patterns from toolbox.py and academic-research examples.
    """

    def __init__(self) -> None:
        """Initialize the tool registry"""
        self._tools: dict[str, ToolRegistration] = {}
        self._categories: dict[ToolCategory, set[str]] = {
            category: set() for category in ToolCategory
        }
        self._tags: dict[str, set[str]] = {}
        self._aliases: dict[str, str] = {}

        # Auto-discovery configuration
        self._discovery_paths: list[Path] = []
        self._discovered_modules: set[str] = set()

        logger.info("Initialized ADK Tool Registry")

    def register(
        self,
        tool_class: type[BaseTool],
        metadata: ToolMetadata | None = None,
        name: str | None = None,
        category: ToolCategory | None = None,
        replace: bool = False,
    ) -> None:
        """
        Register a tool with the registry.

        Args:
            tool_class: The tool class to register (must inherit from BaseTool)
            metadata: Optional complete metadata (auto-generated if not provided)
            name: Optional name override (uses class name if not provided)
            category: Optional category override
            replace: Whether to replace existing registration
        """
        if not issubclass(tool_class, BaseTool):
            raise ValueError(f"{tool_class} must inherit from BaseTool")

        # Determine tool name (for ADK tools, try to get from instance first)
        if name:
            tool_name = name
        else:
            # For ADK tools, try to get name from instance
            try:
                temp_instance = tool_class(name="", description="")
                if hasattr(temp_instance, "name") and temp_instance.name:
                    tool_name = temp_instance.name
                else:
                    tool_name = tool_class.__name__.lower().replace("tool", "")
            except Exception:
                # Fallback to class name if instantiation fails
                tool_name = tool_class.__name__.lower().replace("tool", "")

        # Check for existing registration
        if tool_name in self._tools and not replace:
            raise ValueError(f"Tool '{tool_name}' already registered")

        # Create or validate metadata
        if metadata:
            if metadata.name != tool_name:
                logger.warning(
                    f"Metadata name '{metadata.name}' differs from registration name '{tool_name}'",
                )
                metadata.name = tool_name
        else:
            # Auto-generate metadata from class
            metadata = self._generate_metadata(tool_class, tool_name, category)

        # Create registration
        registration = ToolRegistration(tool_class=tool_class, metadata=metadata)

        # Register the tool
        self._tools[tool_name] = registration
        self._categories[metadata.category].add(tool_name)

        # Update tag index
        for tag in metadata.tags:
            if tag not in self._tags:
                self._tags[tag] = set()
            self._tags[tag].add(tool_name)

        logger.info(
            f"Registered tool '{tool_name}' in category '{metadata.category.value}'"
        )

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool from the registry.

        Args:
            name: Tool name to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if name not in self._tools:
            return False

        registration = self._tools[name]
        metadata = registration.metadata

        # Remove from all indexes
        del self._tools[name]
        self._categories[metadata.category].discard(name)

        for tag in metadata.tags:
            if tag in self._tags:
                self._tags[tag].discard(name)
                if not self._tags[tag]:
                    del self._tags[tag]

        # Remove aliases
        aliases_to_remove = [
            alias for alias, target in self._aliases.items() if target == name
        ]
        for alias in aliases_to_remove:
            del self._aliases[alias]

        logger.info(f"Unregistered tool '{name}'")
        return True

    def add_alias(self, alias: str, tool_name: str) -> None:
        """Add an alias for a tool name"""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        if alias in self._aliases:
            raise ValueError(f"Alias '{alias}' already exists")

        self._aliases[alias] = tool_name
        logger.debug(f"Added alias '{alias}' for tool '{tool_name}'")

    def get_tool(self, name: str) -> BaseTool | None:
        """
        Get a tool instance by name.

        Args:
            name: Tool name or alias

        Returns:
            Tool instance or None if not found
        """
        # Resolve alias if necessary
        tool_name = self._aliases.get(name, name)

        registration = self._tools.get(tool_name)
        if not registration:
            return None

        return registration.get_instance()

    def get_tools_by_category(self, category: ToolCategory) -> list[BaseTool]:
        """Get all tools in a specific category"""
        tools = []
        for tool_name in self._categories.get(category, set()):
            tool = self.get_tool(tool_name)
            if tool:
                tools.append(tool)
        return tools

    def get_tools_by_tag(self, tag: str) -> list[BaseTool]:
        """Get all tools with a specific tag"""
        tools = []
        for tool_name in self._tags.get(tag, set()):
            tool = self.get_tool(tool_name)
            if tool:
                tools.append(tool)
        return tools

    def get_tools_by_capability(self, capability: str) -> list[BaseTool]:
        """Get all tools with a specific capability"""
        tools = []
        for name, registration in self._tools.items():
            if capability in registration.metadata.capabilities:
                tool = self.get_tool(name)
                if tool:
                    tools.append(tool)
        return tools

    def get_metadata(self, name: str) -> ToolMetadata | None:
        """Get metadata for a tool"""
        tool_name = self._aliases.get(name, name)
        registration = self._tools.get(tool_name)
        return registration.metadata if registration else None

    def list_tools(
        self,
        category: ToolCategory | None = None,
        tag: str | None = None,
        capability: str | None = None,
    ) -> list[str]:
        """
        List tool names with optional filtering.

        Args:
            category: Filter by category
            tag: Filter by tag
            capability: Filter by capability

        Returns:
            List of tool names matching filters
        """
        tools = set(self._tools.keys())

        if category:
            tools &= self._categories.get(category, set())

        if tag:
            tools &= self._tags.get(tag, set())

        if capability:
            capability_tools = set()
            for name in tools:
                registration = self._tools.get(name)
                if registration and capability in registration.metadata.capabilities:
                    capability_tools.add(name)
            tools &= capability_tools

        return sorted(tools)

    def get_toolbox(
        self,
        categories: list[ToolCategory] | None = None,
        tags: list[str] | None = None,
        capabilities: list[str] | None = None,
    ) -> list[BaseTool]:
        """
        Get a toolbox (list of tool instances) based on criteria.

        This follows ADK's toolbox pattern for agent creation.

        Args:
            categories: Tool categories to include
            tags: Tags to filter by (ANY match)
            capabilities: Required capabilities (ALL match)

        Returns:
            List of tool instances
        """
        tool_names = set()

        # Start with all tools if no filters
        if not categories and not tags and not capabilities:
            tool_names = set(self._tools.keys())
        else:
            # Apply category filter
            if categories:
                for category in categories:
                    tool_names.update(self._categories.get(category, set()))
            else:
                tool_names = set(self._tools.keys())

            # Apply tag filter (OR logic)
            if tags:
                tag_tools = set()
                for tag in tags:
                    tag_tools.update(self._tags.get(tag, set()))
                tool_names &= tag_tools

            # Apply capability filter (AND logic)
            if capabilities:
                for capability in capabilities:
                    capability_tools = set()
                    for name in tool_names:
                        registration = self._tools.get(name)
                        if (
                            registration
                            and capability in registration.metadata.capabilities
                        ):
                            capability_tools.add(name)
                    tool_names &= capability_tools

        # Create tool instances
        tools = []
        for name in sorted(tool_names):
            tool = self.get_tool(name)
            if tool:
                tools.append(tool)

        return tools

    def discover_tools(self, path: Union[str, Path], recursive: bool = True) -> int:
        """
        Auto-discover tools in a directory.

        Args:
            path: Directory path to search
            recursive: Whether to search subdirectories

        Returns:
            Number of tools discovered and registered
        """
        path = Path(path)
        if not path.exists() or not path.is_dir():
            logger.warning(
                f"Discovery path '{path}' does not exist or is not a directory"
            )
            return 0

        discovered = 0

        # Find Python files
        pattern = "**/*.py" if recursive else "*.py"
        for py_file in path.glob(pattern):
            if py_file.name.startswith("_") or py_file.name == "adk_registry.py":
                continue

            # Convert to module path
            try:
                # For solve.tools modules
                if "solve/tools" in str(py_file):
                    module_path = f"solve.tools.{py_file.stem}"
                else:
                    relative_path = py_file.relative_to(path.parent)
                    module_path = str(relative_path).replace("/", ".").rstrip(".py")

                if module_path in self._discovered_modules:
                    continue

                # Import module
                module = importlib.import_module(module_path)
                self._discovered_modules.add(module_path)

                # Find tool classes
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseTool)
                        and obj is not BaseTool
                        and obj.__module__ == module.__name__  # Only from this module
                    ):
                        # Skip SafetyWrapper as it requires wrapped_tool parameter
                        if name == "SafetyWrapper":
                            logger.debug(
                                "Skipping SafetyWrapper - requires wrapped_tool parameter"
                            )
                            continue

                        try:
                            self.register(obj)
                            discovered += 1
                            logger.debug(f"Discovered tool '{name}' in {module_path}")
                        except ValueError as e:
                            logger.debug(f"Could not register {name}: {e}")

            except Exception as e:
                logger.debug(f"Could not import {py_file.stem}: {e}")

        if discovered > 0:
            logger.info(f"Discovered {discovered} tools in {path}")
        return discovered

    def get_help(self, name: str) -> str:
        """
        Get detailed help for a tool.

        Args:
            name: Tool name or alias

        Returns:
            Formatted help text
        """
        metadata = self.get_metadata(name)
        if not metadata:
            return f"Tool '{name}' not found"

        help_text = [
            f"Tool: {metadata.name}",
            f"Category: {metadata.category.value}",
            f"Version: {metadata.version}",
            "",
            f"Description: {metadata.description}",
            "",
        ]

        if metadata.author:
            help_text.append(f"Author: {metadata.author}")

        if metadata.tags:
            help_text.append(f"Tags: {', '.join(metadata.tags)}")

        if metadata.capabilities:
            help_text.append("Capabilities:")
            for cap in metadata.capabilities:
                help_text.append(f"  - {cap}")
            help_text.append("")

        if metadata.required_permissions:
            help_text.append("Required Permissions:")
            for perm in metadata.required_permissions:
                help_text.append(f"  - {perm}")
            help_text.append("")

        if metadata.parameters_schema:
            help_text.append("Parameters:")
            # Format schema (simplified for now)
            for param, details in metadata.parameters_schema.items():
                help_text.append(f"  - {param}: {details}")
            help_text.append("")

        if metadata.examples:
            help_text.append("Examples:")
            for i, example in enumerate(metadata.examples, 1):
                help_text.append(f"  Example {i}:")
                help_text.append(f"    {example}")
            help_text.append("")

        help_text.extend(
            [
                "Capabilities:",
                f"  - Async: {metadata.supports_async}",
                f"  - Batch: {metadata.supports_batch}",
                f"  - Streaming: {metadata.supports_streaming}",
                f"  - Max Concurrency: {metadata.max_concurrency}",
            ],
        )

        if metadata.timeout_seconds:
            help_text.append(f"  - Timeout: {metadata.timeout_seconds}s")

        if metadata.usage_count > 0:
            help_text.extend(
                [
                    "",
                    "Usage Statistics:",
                    f"  - Usage Count: {metadata.usage_count}",
                    f"  - Avg Execution Time: {metadata.avg_execution_time_ms:.2f}ms",
                ],
            )
            if metadata.last_used:
                help_text.append(f"  - Last Used: {metadata.last_used}")

        return "\n".join(help_text)

    def export_catalog(self) -> dict[str, Any]:
        """Export complete tool catalog as JSON-serializable dict"""
        catalog: dict[str, Any] = {
            "tools": {},
            "categories": {},
            "tags": {},
            "aliases": self._aliases.copy(),
        }

        # Export tool metadata
        for tool_name, registration in self._tools.items():
            catalog["tools"][tool_name] = registration.metadata.to_dict()

        # Export category mappings
        for category in ToolCategory:
            catalog["categories"][category.value] = list(
                self._categories.get(category, set())
            )

        # Export tag mappings
        for tag_name, tag_tools in self._tags.items():
            catalog["tags"][tag_name] = list(tag_tools)

        return catalog

    def _generate_metadata(
        self,
        tool_class: type[BaseTool],
        name: str,
        category: ToolCategory | None = None,
    ) -> ToolMetadata:
        """Generate metadata from tool class introspection"""
        # Extract description from docstring
        description = inspect.getdoc(tool_class) or f"Tool: {name}"
        description = description.split("\n")[0]  # First line only

        # Determine category from class name or attributes
        if category is None:
            category = self._infer_category(tool_class, name)

        # Extract capabilities from method names
        capabilities = []
        for method_name in dir(tool_class):
            if not method_name.startswith("_") and method_name not in [
                "run",
                "validate_params",
            ]:
                capabilities.append(method_name)

        # Check for async support (ADK tools use run_async)
        run_method = getattr(tool_class, "run", None) or getattr(
            tool_class, "run_async", None
        )
        supports_async = inspect.iscoroutinefunction(run_method)

        # Generate basic tags
        tags = [category.value, name]
        if "file" in name.lower():
            tags.append("filesystem")
        if "git" in name.lower():
            tags.append("version-control")
        if "test" in name.lower():
            tags.append("testing")
        if "analyze" in name.lower() or "analysis" in name.lower():
            tags.append("analysis")

        return ToolMetadata(
            name=name,
            category=category,
            description=description,
            tags=tags,
            capabilities=capabilities,
            supports_async=supports_async,
        )

    def _infer_category(self, tool_class: type[BaseTool], name: str) -> ToolCategory:
        """Infer tool category from class and name"""
        name_lower = name.lower()

        # Check for analysis first (before test)
        if "analyze" in name_lower or "analysis" in name_lower:
            return ToolCategory.ANALYSIS
        elif "terraform" in name_lower or "infrastructure" in name_lower:
            return ToolCategory.INFRASTRUCTURE
        elif "gcp" in name_lower or "cloud" in name_lower:
            return ToolCategory.CLOUD
        elif "graph" in name_lower or "database" in name_lower or "neo4j" in name_lower:
            return ToolCategory.DATABASE
        elif "file" in name_lower or "directory" in name_lower:
            return ToolCategory.FILESYSTEM
        elif "git" in name_lower:
            return ToolCategory.GIT
        elif "test" in name_lower:
            return ToolCategory.TESTING
        elif "monitor" in name_lower:
            return ToolCategory.MONITORING
        elif "doc" in name_lower:
            return ToolCategory.DOCUMENTATION
        else:
            return ToolCategory.UTILITY


# Global registry instance
_global_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()

        # Auto-discover tools in the tools directory
        tools_dir = Path(__file__).parent
        _global_registry.discover_tools(tools_dir, recursive=False)

    return _global_registry


def register_tool(tool_class: type[BaseTool], **kwargs: Any) -> None:
    """Convenience function to register a tool with the global registry"""
    get_registry().register(tool_class, **kwargs)


def get_tool(name: str) -> BaseTool | None:
    """Convenience function to get a tool from the global registry"""
    return get_registry().get_tool(name)


def get_toolbox(**kwargs: Any) -> list[BaseTool]:
    """Convenience function to get a toolbox from the global registry"""
    return get_registry().get_toolbox(**kwargs)
