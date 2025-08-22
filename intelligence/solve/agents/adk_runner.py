"""
ADK Runner Patterns Implementation

This module implements proper ADK runner patterns for agent execution, following
the official Google ADK examples and best practices.

Reference Materials:
- adk-python/contributing/samples/hello_world/main.py - Runner usage patterns
- adk-python/src/google/adk/runners.py - InMemoryRunner implementation
- docs/PHASE3-ADK-COMPLIANCE-PLAN.md - Runner requirements

Key Features:
- Proper session management using ADK patterns
- Event processing following hello_world example
- Async execution with proper error handling
- Integration with monitoring system
- Support for single and multi-turn conversations
- Clean async/await patterns
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any

# Use centralized ADK imports with proper fallbacks
from solve_core.adk_imports import Content
from solve_core.adk_imports import EventClass as Event
from solve_core.adk_imports import (InMemoryRunner, Part, RunConfig, Session,
                                    is_adk_available)

# Handle google.genai import for Content/Part types
try:
    from google.genai import types
except ImportError:
    # Create fallback types namespace
    class types:  # type: ignore
        Content = Content
        Part = Part


# Use centralized ADK availability check
ADK_AVAILABLE = is_adk_available()

# Local imports
from solve.adk_monitoring import (  # noqa: E402  # Must import after ADK availability check
    ADKMonitoringSystem, get_monitoring_system)
from solve.models import (  # noqa: E402  # Must import after ADK availability check
    AgentTask, Result, TaskStatus)

logger = logging.getLogger(__name__)


class SOLVERunner:
    """
    SOLVE runner wrapping InMemoryRunner with proper ADK patterns.

    This class implements the runner patterns from hello_world/main.py,
    providing session management, event processing, and monitoring integration.
    """

    def __init__(
        self,
        agent: Any,
        app_name: str = "solve_app",
        user_id: str = "solve_user",
        monitoring_enabled: bool = True,
    ):
        """
        Initialize SOLVE runner following ADK patterns.

        Args:
            agent: ADK agent instance
            app_name: Application name for session management
            user_id: User ID for session management
            monitoring_enabled: Whether to enable monitoring integration
        """
        self.agent = agent
        self.app_name = app_name
        self.user_id = user_id
        self.monitoring_enabled = monitoring_enabled

        # Initialize InMemoryRunner following hello_world pattern
        if ADK_AVAILABLE:
            self.runner = InMemoryRunner(
                agent=agent,
                app_name=app_name,
            )
        else:
            logger.warning("ADK not available - using fallback runner")
            self.runner = InMemoryRunner(agent=agent, app_name=app_name)

        # Session management
        self.current_session: Session | None = None
        self.active_sessions: dict[str, Session] = {}

        # Monitoring integration
        self.monitoring_system: ADKMonitoringSystem | None
        if monitoring_enabled:
            self.monitoring_system = get_monitoring_system()
        else:
            self.monitoring_system = None

        logger.info(f"🚀 SOLVERunner initialized with app_name: {app_name}")

    async def create_session(self, session_id: str | None = None) -> Session:
        """
        Create a new session using ADK patterns.

        Args:
            session_id: Optional session ID, generates one if not provided

        Returns:
            Created session instance
        """
        if not ADK_AVAILABLE:
            # Fallback session creation
            session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
            session = Session(
                id=session_id, user_id=self.user_id, app_name=self.app_name
            )
            self.active_sessions[session_id] = session
            return session

        try:
            # Create session using ADK runner pattern from hello_world
            session = await self.runner.session_service.create_session(
                app_name=self.app_name,
                user_id=self.user_id,
            )

            # Store session for reuse
            self.active_sessions[session.id] = session
            self.current_session = session

            logger.info(f"📋 Created session: {session.id}")
            return session

        except Exception as e:
            logger.error(f"❌ Session creation failed: {e}")
            raise RuntimeError(f"Failed to create session: {e}") from e

    async def get_session(self, session_id: str) -> Session | None:
        """
        Get existing session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session instance or None if not found
        """
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        if not ADK_AVAILABLE:
            return None

        try:
            # Get session using ADK pattern
            session = await self.runner.session_service.get_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=session_id,
            )

            if session:
                self.active_sessions[session_id] = session

            return session

        except Exception as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None

    async def run_agent(
        self,
        message: str,
        session_id: str | None = None,
        run_config: RunConfig | None = None,
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Run agent with message using ADK patterns.

        Args:
            message: Message to send to agent
            session_id: Session ID, creates new if not provided
            run_config: ADK run configuration
            agent_name: Agent name for monitoring

        Returns:
            Dictionary containing response and metadata
        """
        start_time = time.time()

        # Get or create session
        if session_id:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found, creating new one")
                session = await self.create_session()
        else:
            session = await self.create_session()

        # Set up run config with defaults
        if run_config is None:
            run_config = RunConfig()

        # Start monitoring if enabled
        if self.monitoring_enabled and self.monitoring_system:
            await self.monitoring_system.start_agent_monitoring(
                agent_name or "unknown", session.id
            )

        try:
            # Execute using ADK runner pattern from hello_world
            response_text, events = await self._execute_with_runner(
                message, session, run_config
            )

            # Process events to extract results
            success, metadata = await self._process_events(events)

            # Calculate execution time
            execution_time = time.time() - start_time

            # End monitoring if enabled
            if self.monitoring_enabled and self.monitoring_system:
                await self.monitoring_system.end_agent_monitoring(
                    session_id=session.id,
                    agent_name=agent_name or "unknown",
                    success=success,
                    goal_achieved=success,
                    iterations=1,
                    tokens_used=metadata.get("tokens_used", 0),
                    estimated_cost=metadata.get("estimated_cost", 0.0),
                    tools_used=metadata.get("tools_used", []),
                )

            return {
                "success": success,
                "response": response_text,
                "session_id": session.id,
                "execution_time": execution_time,
                "events_count": len(events),
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"❌ Agent execution failed: {e}")

            # End monitoring with error if enabled
            if self.monitoring_enabled and self.monitoring_system:
                await self.monitoring_system.end_agent_monitoring(
                    session_id=session.id,
                    agent_name=agent_name or "unknown",
                    success=False,
                    goal_achieved=False,
                    iterations=1,
                    tokens_used=0,
                    estimated_cost=0.0,
                    tools_used=[],
                    error_message=str(e),
                )

            return {
                "success": False,
                "response": f"Execution failed: {str(e)}",
                "session_id": session.id,
                "execution_time": time.time() - start_time,
                "events_count": 0,
                "metadata": {"error": str(e)},
            }

    async def _execute_with_runner(
        self,
        message: str,
        session: Session,
        run_config: RunConfig,
    ) -> tuple[str, list[Event]]:
        """
        Execute message using ADK runner following hello_world pattern.

        Args:
            message: Message to execute
            session: Session to use
            run_config: Run configuration

        Returns:
            Tuple of (response_text, events)
        """
        if not ADK_AVAILABLE:
            # Fallback execution
            return f"Fallback response to: {message}", []

        # Create content following hello_world pattern
        content = types.Content(role="user", parts=[types.Part.from_text(text=message)])

        logger.debug(f"📤 Sending message: {message[:100]}...")

        # Execute using async generator pattern from hello_world
        events = []
        async for event in self.runner.run_async(
            user_id=self.user_id,
            session_id=session.id,
            new_message=content,
            run_config=run_config,
        ):
            events.append(event)

            # Log event processing similar to hello_world
            if hasattr(event, "content") and event.content:
                if hasattr(event.content, "parts") and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            logger.debug(
                                f"📥 {getattr(event, 'author', 'agent')}: {part.text[:100]}...",
                            )

        # Extract response text from events
        response_text = self._extract_response_text(events)

        return response_text, events

    def _extract_response_text(self, events: list[Event]) -> str:
        """
        Extract response text from events following hello_world pattern.

        Args:
            events: List of events from ADK runner

        Returns:
            Combined response text
        """
        responses = []

        for event in events:
            if hasattr(event, "content") and event.content:
                if hasattr(event.content, "parts") and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            responses.append(part.text.strip())

        return "\n".join(responses) if responses else "No response received"

    async def _process_events(self, events: list[Event]) -> tuple[bool, dict[str, Any]]:
        """
        Process events to extract success status and metadata.

        Args:
            events: List of events to process

        Returns:
            Tuple of (success, metadata)
        """
        metadata = {
            "events_processed": len(events),
            "tokens_used": 0,
            "estimated_cost": 0.0,
            "tools_used": [],
            "processing_time": time.time(),
        }

        # Determine success based on event content
        success = len(events) > 0

        # Extract metadata from events
        for event in events:
            # Check for error indicators
            if hasattr(event, "content") and event.content:
                if hasattr(event.content, "parts") and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            text = part.text.lower()
                            if any(
                                error_word in text
                                for error_word in ["error", "failed", "exception"]
                            ):
                                success = False

            # Extract tool usage if available
            if hasattr(event, "tool_calls") and event.tool_calls:
                for tool_call in event.tool_calls:
                    if hasattr(tool_call, "name"):
                        tools_used = metadata.get("tools_used", [])
                        if isinstance(tools_used, list):
                            tools_used.append(tool_call.name)
                            metadata["tools_used"] = tools_used

        return success, metadata

    async def run_multi_turn_conversation(
        self,
        messages: list[str],
        session_id: str | None = None,
        agent_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Run multi-turn conversation using same session.

        Args:
            messages: List of messages to send
            session_id: Session ID to use
            agent_name: Agent name for monitoring

        Returns:
            List of responses for each message
        """
        # Create or get session
        if session_id:
            session = await self.get_session(session_id)
            if not session:
                session = await self.create_session()
        else:
            session = await self.create_session()

        responses = []

        for i, message in enumerate(messages):
            logger.info(
                f"📝 Multi-turn message {i + 1}/{len(messages)}: {message[:50]}..."
            )

            response = await self.run_agent(
                message=message,
                session_id=session.id,
                agent_name=agent_name,
            )

            responses.append(response)

            # If a message failed, we might want to continue or stop
            if not response["success"]:
                logger.warning(f"Message {i + 1} failed: {response['response']}")

        return responses

    async def execute_agent_task(
        self, task: AgentTask, session_id: str | None = None
    ) -> Result:
        """
        Execute AgentTask using ADK runner patterns.

        Args:
            task: Agent task to execute
            session_id: Optional session ID

        Returns:
            Result object with execution details
        """
        start_time = datetime.now()

        # Update task status
        task.status = TaskStatus.IN_PROGRESS

        # Execute using runner
        response = await self.run_agent(
            message=task.goal.description,
            session_id=session_id,
            agent_name=task.assigned_agent,
        )

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        # Create result
        result = Result(
            success=response["success"],
            message=response["response"],
            artifacts={
                "session_id": response["session_id"],
                "execution_time": execution_time,
                "events_count": response["events_count"],
                "adk_runner": "real",
                **response["metadata"],
            },
            metadata={
                "task_id": getattr(task, "id", "unknown"),
                "agent_name": task.assigned_agent,
                "runner_type": "SOLVERunner",
                "adk_integration": "real",
            },
        )

        # Update task status
        task.status = TaskStatus.COMPLETED if response["success"] else TaskStatus.FAILED

        return result

    async def get_session_state(self, session_id: str) -> dict[str, Any]:
        """
        Get session state following ADK patterns.

        Args:
            session_id: Session ID to query

        Returns:
            Session state dictionary
        """
        session = await self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        return {
            "session_id": session.id,
            "user_id": getattr(session, "user_id", self.user_id),
            "app_name": getattr(session, "app_name", self.app_name),
            "events_count": len(getattr(session, "events", [])),
            "state": getattr(session, "state", {}),
            "created_at": getattr(session, "created_at", None),
        }

    async def close(self) -> None:
        """
        Clean up runner resources.
        """
        try:
            # Close ADK runner if available
            if hasattr(self.runner, "close"):
                close_method = self.runner.close
                if callable(close_method):
                    await close_method()  # type: ignore[no-untyped-call]

            # Clear sessions
            self.active_sessions.clear()
            self.current_session = None

            logger.info("🔒 SOLVERunner closed successfully")

        except Exception as e:
            logger.error(f"❌ Error closing runner: {e}")

    def get_runner_stats(self) -> dict[str, Any]:
        """
        Get runner statistics.

        Returns:
            Dictionary containing runner statistics
        """
        return {
            "app_name": self.app_name,
            "user_id": self.user_id,
            "active_sessions": len(self.active_sessions),
            "current_session": (
                self.current_session.id if self.current_session else None
            ),
            "monitoring_enabled": self.monitoring_enabled,
            "adk_available": ADK_AVAILABLE,
            "runner_type": "SOLVERunner",
        }


# Utility functions for common ADK runner operations


async def create_runner_for_agent(
    agent: Any,
    app_name: str = "solve",
    user_id: str = "solve_user",
) -> SOLVERunner:
    """
    Create a SOLVERunner for an agent.

    Args:
        agent: ADK agent instance
        app_name: Application name
        user_id: User ID

    Returns:
        Configured SOLVERunner instance
    """
    return SOLVERunner(
        agent=agent, app_name=app_name, user_id=user_id, monitoring_enabled=True
    )


async def execute_single_message(
    agent: Any,
    message: str,
    app_name: str = "solve_single",
) -> dict[str, Any]:
    """
    Execute a single message with an agent (convenience function).

    Args:
        agent: ADK agent instance
        message: Message to execute
        app_name: Application name

    Returns:
        Execution result
    """
    runner = await create_runner_for_agent(agent, app_name)

    try:
        result = await runner.run_agent(message)
        return result
    finally:
        close_method = runner.close
        if callable(close_method):
            await close_method()


async def execute_conversation(
    agent: Any,
    messages: list[str],
    app_name: str = "solve_conversation",
) -> list[dict[str, Any]]:
    """
    Execute a multi-turn conversation with an agent.

    Args:
        agent: ADK agent instance
        messages: List of messages
        app_name: Application name

    Returns:
        List of execution results
    """
    runner = await create_runner_for_agent(agent, app_name)

    try:
        results = await runner.run_multi_turn_conversation(messages)
        return results
    finally:
        close_method = runner.close
        if callable(close_method):
            await close_method()


# Example usage following hello_world pattern
async def example_usage() -> None:
    """
    Example usage of SOLVERunner following hello_world patterns.
    """
    try:
        # This would be replaced with actual ADK agent
        from solve.agents.base_agent import RealADKAgent
        from solve.prompts.constitutional_template import AgentRole

        # Create agent
        agent = RealADKAgent(
            name="example_agent",
            role=AgentRole.STRUCTURE,
            description="Example agent for runner testing",
            capabilities=["Create files", "Structure projects"],
        )

        # Create runner
        runner = SOLVERunner(
            agent=agent.adk_agent, app_name="example_app", user_id="example_user"
        )

        # Create session
        session = await runner.create_session()

        # Run single message
        await runner.run_agent(
            message="Create a simple Python project structure",
            session_id=session.id,
        )

        # Run follow-up message in same session
        await runner.run_agent(
            message="Add a README.md file to the project", session_id=session.id
        )

        # Get session state
        await runner.get_session_state(session.id)

        # Get runner stats
        runner.get_runner_stats()

        # Close runner
        close_method = runner.close
        if callable(close_method):
            await close_method()

    except Exception as e:
        logger.error(f"Example usage failed: {e}")


if __name__ == "__main__":
    # Run example usage
    example_func = example_usage
    if callable(example_func):
        asyncio.run(example_func())
