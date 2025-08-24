"""
ADK Compatibility Layer for SOLVE

This module provides compatibility between SOLVE's tool patterns and Google ADK.
It allows SOLVE tools to work with both the legacy adapter and real ADK patterns.

Key Features:
1. Bridge SOLVE tools to ADK BaseTool interface
2. Convert between ToolContext patterns
3. Provide adapter classes for existing SOLVE tools
4. Enable gradual migration to pure ADK patterns
"""

import logging
from typing import Any, Protocol

from google.adk.tools import BaseTool as ADKBaseTool
from google.adk.tools.tool_context import ToolContext as ADKToolContext

# Import SOLVE adapter for compatibility
from solve.adk_adapter import BaseTool as SOLVEBaseTool
from solve.adk_adapter import ToolContext as SOLVEToolContext

logger = logging.getLogger(__name__)


class SOLVEToolProtocol(Protocol):
    """Protocol for SOLVE tools to enable type checking"""

    async def run(self, context: SOLVEToolContext, **kwargs: Any) -> dict[str, Any]:
        """Run method expected by SOLVE tools"""
        ...

    @property
    def name(self) -> str:
        """Tool name property"""
        ...

    @property
    def description(self) -> str:
        """Tool description property"""
        ...


class SOLVEToADKAdapter(ADKBaseTool):
    """
    Adapter that wraps SOLVE tools to work with real ADK patterns.

    This allows existing SOLVE tools to be used in real ADK agents
    without modification.
    """

    def __init__(self, solve_tool: SOLVEToolProtocol):
        """
        Initialize adapter with a SOLVE tool.

        Args:
            solve_tool: Any object implementing SOLVEToolProtocol
        """
        super().__init__(name=solve_tool.name, description=solve_tool.description)
        self.solve_tool = solve_tool

    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ADKToolContext,
    ) -> dict[str, Any]:
        """
        Execute SOLVE tool using ADK interface.

        Converts ADK context to SOLVE context and delegates to SOLVE tool.
        """
        try:
            # Convert ADK context to SOLVE context
            solve_context = self._convert_adk_to_solve_context(tool_context, args)

            # Execute SOLVE tool
            result = await self.solve_tool.run(solve_context, **args)

            # Ensure result is JSON-serializable and return
            return result if isinstance(result, dict) else {"result": result}

        except Exception as e:
            logger.error(f"Error executing SOLVE tool {self.solve_tool.name}: {e}")
            return {"success": False, "error": str(e), "tool": self.solve_tool.name}

    def _convert_adk_to_solve_context(
        self,
        adk_context: ADKToolContext,
        args: dict[str, Any],
    ) -> SOLVEToolContext:
        """Convert ADK ToolContext to SOLVE ToolContext"""
        # Extract session info from ADK context
        session_id = getattr(adk_context._invocation_context.session, "id", "unknown")
        agent_name = getattr(adk_context._invocation_context, "agent_name", "unknown")

        return SOLVEToolContext(
            session_id=session_id,
            agent_name=agent_name,
            tool_name=self.solve_tool.name,
            state={},  # Use empty dict since state conversion is complex
            history=[],  # ADK doesn't expose history directly
            metadata={"adk_context": True, "args": args},
        )


class ADKToSOLVEAdapter(SOLVEBaseTool):
    """
    Adapter that wraps ADK tools to work with SOLVE patterns.

    This allows new ADK tools to be used in existing SOLVE systems
    that expect the SOLVE adapter interface.
    """

    def __init__(self, adk_tool: ADKBaseTool):
        """
        Initialize adapter with an ADK tool.

        Args:
            adk_tool: Real ADK BaseTool instance
        """
        super().__init__()
        self.adk_tool = adk_tool
        # Override name and description from ADK tool
        self.name = adk_tool.name
        self.description = adk_tool.description

    async def run(self, context: SOLVEToolContext, **kwargs: Any) -> dict[str, Any]:
        """
        Execute ADK tool using SOLVE interface.

        Converts SOLVE context to ADK context and delegates to ADK tool.
        """
        try:
            # Create minimal ADK context for testing
            # Note: In real usage, this would come from actual ADK session
            adk_context = self._create_mock_adk_context(context)

            # Execute ADK tool
            result = await self.adk_tool.run_async(
                args=kwargs, tool_context=adk_context
            )

            # Ensure result is dict[str, Any]
            if not isinstance(result, dict):
                return {"result": result}

            return result

        except Exception as e:
            logger.error(f"Error executing ADK tool {self.adk_tool.name}: {e}")
            return {"success": False, "error": str(e), "tool": self.adk_tool.name}

    def _create_mock_adk_context(
        self, solve_context: SOLVEToolContext
    ) -> ADKToolContext:
        """
        Create an ADK context from SOLVE context.

        This creates a real ADK context with proper session and invocation context.
        """
        # Create proper ADK session and invocation context
        # This should integrate with actual ADK session management
        raise NotImplementedError(
            "ADK context creation requires real ADK session integration. "
            "This functionality needs to be implemented with proper ADK SDK initialization.",
        )


def wrap_solve_tool_for_adk(solve_tool: SOLVEToolProtocol) -> ADKBaseTool:
    """
    Convenience function to wrap a SOLVE tool for ADK usage.

    Args:
        solve_tool: SOLVE tool to wrap

    Returns:
        ADK-compatible tool wrapper
    """
    return SOLVEToADKAdapter(solve_tool)


def wrap_adk_tool_for_solve(adk_tool: ADKBaseTool) -> SOLVEBaseTool:
    """
    Convenience function to wrap an ADK tool for SOLVE usage.

    Args:
        adk_tool: ADK tool to wrap

    Returns:
        SOLVE-compatible tool wrapper
    """
    return ADKToSOLVEAdapter(adk_tool)


class ExtendedToolRegistry:
    """
    Extended tool registry wrapper that provides SOLVE compatibility methods.

    This class wraps a ToolRegistry and adds the needed methods with proper typing.
    """

    def __init__(self, base_registry: Any = None) -> None:
        """Initialize with base registry"""
        from solve.tools.adk_registry import ToolRegistry

        self._registry = base_registry if base_registry is not None else ToolRegistry()

    def register(self, tool_class: type[ADKBaseTool], **kwargs: Any) -> None:
        """Register an ADK tool class"""
        self._registry.register(tool_class, **kwargs)

    def register_solve_tool(self, solve_tool: SOLVEToolProtocol, **kwargs: Any) -> None:
        """Register a SOLVE tool by wrapping it for ADK"""

        # Create an adapter class dynamically
        class WrappedSOLVETool(SOLVEToADKAdapter):
            def __init__(self) -> None:
                super().__init__(solve_tool)

        self._registry.register(WrappedSOLVETool, **kwargs)

    def register_mixed_tool(self, tool: Any, **kwargs: Any) -> None:
        """Register any tool type by detecting its interface"""
        if hasattr(tool, "run_async") and isinstance(tool, ADKBaseTool):
            # It's an ADK tool - register the class
            self._registry.register(tool.__class__, **kwargs)
        elif hasattr(tool, "run") and hasattr(tool, "name"):
            # It's a SOLVE tool - wrap it
            class WrappedTool(SOLVEToADKAdapter):
                def __init__(self) -> None:
                    super().__init__(tool)

            self._registry.register(WrappedTool, **kwargs)
        else:
            raise ValueError(f"Unknown tool type: {type(tool)}")

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the wrapped registry"""
        return getattr(self._registry, name)


def create_tool_registry_adapter() -> ExtendedToolRegistry:
    """
    Create a tool registry that works with both SOLVE and ADK tools.

    Returns a registry that can handle mixed tool types during migration.
    """
    return ExtendedToolRegistry()


# Export compatibility functions
__all__ = [
    "SOLVEToADKAdapter",
    "ADKToSOLVEAdapter",
    "wrap_solve_tool_for_adk",
    "wrap_adk_tool_for_solve",
    "create_tool_registry_adapter",
    "ExtendedToolRegistry",
    "SOLVEToolProtocol",
]
