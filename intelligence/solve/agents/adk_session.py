"""
ADK Session Management for SOLVE Agents

This module implements proper ADK session management following official patterns
from adk-python/src/google/adk/sessions/ and adk-samples/session_state_agent/.

Features:
- Proper session lifecycle management
- Session persistence and state management
- Multi-user session support
- Session context for tool state
- Agent coordination session sharing
- Full ADK compliance with InMemorySessionService

Reference:
- adk-python/src/google/adk/sessions/
- adk-samples/session_state_agent/
- adk-samples/hello_world/main.py
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

# Use centralized ADK imports with proper fallbacks
from solve_core.adk_imports import Agent, Content, EventActions
from solve_core.adk_imports import EventClass as Event
from solve_core.adk_imports import (GetSessionConfig, InMemoryRunner,
                                    InMemorySessionService,
                                    ListSessionsResponse, Part, RunConfig,
                                    Session, is_adk_available)

# Handle google.genai import for Content/Part types
try:
    from google.genai import types
except ImportError:
    # Create fallback types namespace
    class types:  # type: ignore
        Content = Content
        Part = Part


logger = logging.getLogger(__name__)


class SessionManager:
    """
    Session manager for SOLVE agents following ADK patterns.

    Manages session lifecycle, persistence, and state for multiple agents
    and users within the SOLVE methodology framework.
    """

    def __init__(self, app_name: str = "solve-methodology"):
        """
        Initialize session manager with ADK session service.

        Args:
            app_name: Name of the SOLVE application
        """
        self.app_name = app_name
        self.session_service = InMemorySessionService()
        self._active_sessions: dict[str, Session] = {}
        self._runners: dict[str, InMemoryRunner] = {}

        logger.info(f"SessionManager initialized for app: {app_name}")

    async def create_session(
        self,
        user_id: str,
        session_id: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> Session:
        """
        Create a new session following ADK patterns.

        Args:
            user_id: Unique identifier for the user
            session_id: Optional session ID (generated if not provided)
            initial_state: Optional initial session state

        Returns:
            Created session instance
        """
        # Follow ADK pattern from hello_world/main.py
        session = await self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
            state=initial_state or {},
        )

        # Cache session for quick access
        self._active_sessions[session.id] = session

        logger.info(f"Created session {session.id} for user {user_id}")
        return session

    async def get_session(
        self,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        """
        Retrieve existing session with optional configuration.

        Args:
            user_id: User identifier
            session_id: Session identifier
            config: Optional configuration for session retrieval

        Returns:
            Session instance or None if not found
        """
        # Follow ADK pattern from session_state_agent
        session = await self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
            config=config,
        )

        if session:
            # Update cache
            self._active_sessions[session.id] = session
            logger.debug(f"Retrieved session {session_id} for user {user_id}")
        else:
            logger.warning(f"Session {session_id} not found for user {user_id}")

        return session

    async def list_user_sessions(self, user_id: str) -> ListSessionsResponse:
        """
        List all sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of user sessions
        """
        # Follow ADK pattern from base_session_service
        response = await self.session_service.list_sessions(
            app_name=self.app_name, user_id=user_id
        )

        logger.debug(f"Listed {len(response.sessions)} sessions for user {user_id}")
        return response

    async def delete_session(self, user_id: str, session_id: str) -> None:
        """
        Delete a session and clean up resources.

        Args:
            user_id: User identifier
            session_id: Session identifier
        """
        # Follow ADK pattern from base_session_service
        await self.session_service.delete_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
        )

        # Clean up caches
        self._active_sessions.pop(session_id, None)
        if session_id in self._runners:
            self._runners.pop(session_id)

        logger.info(f"Deleted session {session_id} for user {user_id}")

    async def update_session_state(
        self,
        session: Session,
        state_updates: dict[str, Any],
    ) -> Session:
        """
        Update session state with new values using ADK event system.

        Args:
            session: Session to update
            state_updates: State changes to apply

        Returns:
            Updated session
        """
        # Follow ADK state management patterns using events
        # Create event with state_delta to properly persist state
        if is_adk_available():
            # Use real ADK event creation
            event = Event(
                invocation_id=str(uuid.uuid4()),
                author="session_manager",
                content=types.Content(
                    role="assistant",
                    parts=[types.Part.from_text(text="Session state updated")],
                ),
                timestamp=datetime.now().timestamp(),
                actions=EventActions(state_delta=state_updates),
            )
        else:
            # Use fallback event creation
            event = Event(
                content="Session state updated",
                artifacts=state_updates,
            )

        # Use the session service to append the event, which will update state
        await self.session_service.append_event(session, event)

        # Update cache
        self._active_sessions[session.id] = session

        logger.debug(
            f"Updated session {session.id} state with {len(state_updates)} changes"
        )
        return session

    def create_runner_for_agent(self, agent: Agent, session: Session) -> InMemoryRunner:
        """
        Create an ADK runner for an agent with session support.

        Args:
            agent: ADK agent instance
            session: Session for the runner

        Returns:
            Configured InMemoryRunner
        """
        # Follow ADK pattern from hello_world/main.py
        try:
            # Try with minimal constructor first (most common pattern)
            runner = InMemoryRunner(agent=agent)
        except TypeError:
            # Fallback for version with app_name
            try:
                runner = InMemoryRunner(agent=agent, app_name=self.app_name)
            except TypeError:
                # Final fallback - try with session_service if supported
                runner = InMemoryRunner(
                    agent=agent,
                    app_name=self.app_name,
                )  # Remove unsupported session_service parameter

        # Cache runner for reuse
        self._runners[session.id] = runner

        logger.debug(f"Created runner for agent {agent.name} with session {session.id}")
        return runner

    async def run_agent_with_session(
        self,
        agent: Agent,
        user_id: str,
        session_id: str,
        message: str,
        run_config: RunConfig | None = None,
    ) -> list[Any]:
        """
        Run an agent with proper session management.

        Args:
            agent: ADK agent to run
            user_id: User identifier
            session_id: Session identifier
            message: User message
            run_config: Optional run configuration

        Returns:
            List of events from agent execution
        """
        # Get or create runner
        if session_id not in self._runners:
            session = await self.get_session(user_id, session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found for user {user_id}")
            self.create_runner_for_agent(agent, session)

        runner = self._runners[session_id]

        # Follow ADK pattern from hello_world/main.py
        content = types.Content(role="user", parts=[types.Part.from_text(text=message)])

        events = []
        # Handle optional run_config
        if run_config is not None:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
                run_config=run_config,
            ):
                events.append(event)
        else:
            # Use default run config if none provided
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                events.append(event)

        logger.info(f"Agent {agent.name} processed message in session {session_id}")
        return events

    async def get_session_tool_state(
        self,
        user_id: str,
        session_id: str,
        tool_name: str,
    ) -> dict[str, Any] | None:
        """
        Get tool-specific state from session.

        Args:
            user_id: User identifier
            session_id: Session identifier
            tool_name: Name of the tool

        Returns:
            Tool state dictionary or None
        """
        session = await self.get_session(user_id, session_id)
        if not session:
            return None

        tool_state_key = f"tool:{tool_name}"
        return session.state.get(tool_state_key)

    async def set_session_tool_state(
        self,
        user_id: str,
        session_id: str,
        tool_name: str,
        tool_state: dict[str, Any],
    ) -> None:
        """
        Set tool-specific state in session.

        Args:
            user_id: User identifier
            session_id: Session identifier
            tool_name: Name of the tool
            tool_state: Tool state to store
        """
        session = await self.get_session(user_id, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found for user {user_id}")

        tool_state_key = f"tool:{tool_name}"
        await self.update_session_state(session, {tool_state_key: tool_state})

    async def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up expired sessions.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            Number of sessions cleaned up
        """
        current_time = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600

        cleanup_count = 0
        sessions_to_remove = []

        for session_id, session in self._active_sessions.items():
            if (current_time - session.last_update_time) > max_age_seconds:
                sessions_to_remove.append((session.user_id, session_id))

        for user_id, session_id in sessions_to_remove:
            await self.delete_session(user_id, session_id)
            cleanup_count += 1

        logger.info(f"Cleaned up {cleanup_count} expired sessions")
        return cleanup_count

    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self._active_sessions)

    def get_session_stats(self) -> dict[str, Any]:
        """
        Get session statistics.

        Returns:
            Dictionary with session statistics
        """
        return {
            "active_sessions": len(self._active_sessions),
            "active_runners": len(self._runners),
            "app_name": self.app_name,
            "session_service_type": type(self.session_service).__name__,
        }


class MultiAgentSessionCoordinator:
    """
    Coordinates sessions across multiple SOLVE agents.

    Manages agent delegation, shared state, and multi-agent workflows
    within the SOLVE methodology framework.
    """

    def __init__(self, session_manager: SessionManager):
        """
        Initialize multi-agent session coordinator.

        Args:
            session_manager: Session manager instance
        """
        self.session_manager = session_manager
        self._agent_sessions: dict[
            str, dict[str, str]
        ] = {}  # agent_name -> {user_id: session_id}

        logger.info("MultiAgentSessionCoordinator initialized")

    async def create_agent_session(
        self,
        agent_name: str,
        user_id: str,
        parent_session_id: str | None = None,
        shared_state: dict[str, Any] | None = None,
    ) -> Session:
        """
        Create a session for a specific agent.

        Args:
            agent_name: Name of the agent
            user_id: User identifier
            parent_session_id: Optional parent session for inheritance
            shared_state: Optional shared state from parent

        Returns:
            Created session for the agent
        """
        # Create initial state with agent context
        initial_state = {
            "agent_name": agent_name,
            "parent_session_id": parent_session_id,
            "created_at": datetime.now().isoformat(),
        }

        if shared_state:
            initial_state.update(shared_state)

        # Create session
        session = await self.session_manager.create_session(
            user_id=user_id,
            initial_state=initial_state,
        )

        # Track agent session
        if agent_name not in self._agent_sessions:
            self._agent_sessions[agent_name] = {}
        self._agent_sessions[agent_name][user_id] = session.id

        logger.info(f"Created session {session.id} for agent {agent_name}")
        return session

    async def get_agent_session(self, agent_name: str, user_id: str) -> Session | None:
        """
        Get existing session for an agent.

        Args:
            agent_name: Name of the agent
            user_id: User identifier

        Returns:
            Session instance or None
        """
        if agent_name not in self._agent_sessions:
            return None

        session_id = self._agent_sessions[agent_name].get(user_id)
        if not session_id:
            return None

        return await self.session_manager.get_session(user_id, session_id)

    async def share_state_between_agents(
        self,
        from_agent: str,
        to_agent: str,
        user_id: str,
        state_keys: list[str],
    ) -> bool:
        """
        Share state between agent sessions.

        Args:
            from_agent: Source agent name
            to_agent: Target agent name
            user_id: User identifier
            state_keys: Keys to share

        Returns:
            True if successful, False otherwise
        """
        # Get source session
        source_session = await self.get_agent_session(from_agent, user_id)
        if not source_session:
            logger.warning(f"No session found for source agent {from_agent}")
            return False

        # Get or create target session
        target_session = await self.get_agent_session(to_agent, user_id)
        if not target_session:
            target_session = await self.create_agent_session(to_agent, user_id)

        # Share specified state
        shared_state = {}
        for key in state_keys:
            if key in source_session.state:
                shared_state[f"shared:{key}"] = source_session.state[key]

        if shared_state:
            await self.session_manager.update_session_state(
                target_session, shared_state
            )
            logger.info(
                f"Shared {len(shared_state)} state keys from {from_agent} to {to_agent}"
            )
            return True

        return False

    async def cleanup_agent_sessions(self, agent_name: str) -> int:
        """
        Clean up all sessions for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Number of sessions cleaned up
        """
        if agent_name not in self._agent_sessions:
            return 0

        cleanup_count = 0
        for user_id, session_id in self._agent_sessions[agent_name].items():
            await self.session_manager.delete_session(user_id, session_id)
            cleanup_count += 1

        # Clear tracking
        self._agent_sessions.pop(agent_name, None)

        logger.info(f"Cleaned up {cleanup_count} sessions for agent {agent_name}")
        return cleanup_count

    def get_coordination_stats(self) -> dict[str, Any]:
        """
        Get coordination statistics.

        Returns:
            Dictionary with coordination statistics
        """
        agent_counts = {}
        for agent_name, sessions in self._agent_sessions.items():
            agent_counts[agent_name] = len(sessions)

        return {
            "tracked_agents": len(self._agent_sessions),
            "total_agent_sessions": sum(
                len(sessions) for sessions in self._agent_sessions.values()
            ),
            "agent_session_counts": agent_counts,
        }


# Example usage patterns following ADK best practices
async def example_usage() -> None:
    """
    Example usage of ADK session management for SOLVE agents.

    This demonstrates proper session lifecycle management following
    patterns from adk-samples/hello_world/main.py.
    """
    # Initialize session manager
    session_manager = SessionManager(app_name="solve-methodology")

    # Create user session
    user_id = "developer-123"
    session = await session_manager.create_session(
        user_id=user_id,
        initial_state={"project": "my-project", "phase": "scaffold"},
    )

    # Create a simple agent (would be replaced with actual SOLVE agents)
    from google.adk.agents import Agent

    agent = Agent(
        name="structure_agent",
        description="SOLVE structure agent",
        model="gemini-2.0-flash-exp",
        instruction="You are a SOLVE structure agent. Help create project structure.",
    )

    # Run agent with session
    await session_manager.run_agent_with_session(
        agent=agent,
        user_id=user_id,
        session_id=session.id,
        message="Create a new Python project structure",
    )

    # Update session state
    await session_manager.update_session_state(
        session,
        {"last_action": "structure_created", "files_created": 5},
    )

    # Store tool state
    await session_manager.set_session_tool_state(
        user_id=user_id,
        session_id=session.id,
        tool_name="filesystem",
        tool_state={
            "current_dir": "/project",
            "files": ["main.py", "requirements.txt"],
        },
    )

    # Multi-agent coordination
    coordinator = MultiAgentSessionCoordinator(session_manager)

    # Create agent-specific session
    await coordinator.create_agent_session(
        agent_name="structure_agent",
        user_id=user_id,
        parent_session_id=session.id,
        shared_state={"project": "my-project"},
    )

    # Get statistics
    session_manager.get_session_stats()
    coordinator.get_coordination_stats()

    # Cleanup
    await session_manager.cleanup_expired_sessions(max_age_hours=24)


if __name__ == "__main__":
    # Run example (for testing purposes)
    asyncio.run(example_usage())
