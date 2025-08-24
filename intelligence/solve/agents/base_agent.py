"""
Real Agent Base Class with ADK Integration

Replaces mock implementations with actual ADK-powered agents.
NO MOCKS, NO STUBS - REAL ADK EXECUTION ONLY

Based on:
- docs/best-practices/1-anthropic-prompt-engineering-guide.md (Constitutional AI)
- docs/best-practices/7-adk-based-autofix-architecture.md (ADK patterns)
- docs/best-practices/12-agentic-transformation-principles.md (Agent autonomy)
"""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from solve.agents.tool_executor import ToolExecutor
from solve.models import AgentTask, Goal, Result, TaskStatus
from solve.prompts.constitutional_template import (
    AgentRole,
    PromptContext,
    build_complete_prompt,
)
from solve.tools.filesystem import FileSystemTool, SafetyConfig

# ADK imports are done inside methods to avoid import-time dependencies

logger = logging.getLogger(__name__)


class RealADKAgent:
    """
    Base class for real ADK-powered agents.

    CRITICAL: This class performs ACTUAL LLM execution via Google ADK.
    No mock responses, no simulated behavior.
    """

    def __init__(
        self,
        name: str,
        role: AgentRole,
        description: str,
        capabilities: list[str],
        tools: list[Any] | None = None,
        working_directory: str | Path | None = None,
    ) -> None:
        """Initialize real ADK agent."""
        self.name = name
        self.role = role
        self.description = description
        self.capabilities = capabilities
        self.execution_count = 0
        self.working_directory = Path(working_directory or Path.cwd())
        self.app_name = f"solve_{self.name}"

        # Initialize real ADK components
        self._initialize_adk_components()

        # Initialize tools with real implementations
        self._initialize_tools(tools)

        # Initialize tool executor for real operations
        self.tool_executor = ToolExecutor(self.tools)

        logger.info(f"🤖 Initialized real ADK agent: {name} ({role.value})")

    def _initialize_adk_components(self) -> None:
        """Initialize Google ADK components for real LLM execution."""
        try:
            from google.adk import Agent
            from google.adk.runners import InMemoryRunner
            from google.genai import types

            # Build constitutional AI instruction using prompt template
            instruction = self._build_constitutional_instruction()

            # Create ADK agent with constitutional instructions following official pattern
            self.adk_agent = Agent(
                model="gemini-2.0-flash",
                name=self.name,
                description=self.description,
                instruction=instruction,
                tools=self._get_adk_tools(),
                generate_content_config=types.GenerateContentConfig(
                    safety_settings=[
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        ),
                    ],
                ),
            )

            # Initialize runner and app_name for session management
            self.app_name = f"solve_{self.name}"
            self.runner = InMemoryRunner(
                agent=self.adk_agent,
                app_name=self.app_name,
            )

            logger.info(
                f"✅ ADK Agent initialized for {self.name} with model gemini-2.0-flash"
            )

        except ImportError as e:
            logger.error(f"❌ ADK import failed: {e}")
            raise RuntimeError(f"Google ADK not available: {e}") from e
        except Exception as e:
            logger.error(f"❌ ADK initialization failed: {e}")
            raise RuntimeError(f"ADK setup failed: {e}") from e

    def _initialize_tools(self, additional_tools: list[Any] | None = None) -> None:
        """Initialize real tools for agent use."""
        # Create file system tool with sandbox safety
        safety_config = SafetyConfig(
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
                ".html",
                ".css",
                ".sql",
            ],
            forbidden_paths=["/etc", "/usr", "/var", "/bin", "/sbin", "/sys"],
            max_file_size=10 * 1024 * 1024,  # 10MB
            require_confirmation_for_destructive=True,
            sandbox_root=str(self.working_directory),
        )

        self.filesystem_tool = FileSystemTool(safety_config)

        # Initialize tool registry
        self.tools = {"filesystem": self.filesystem_tool}

        # Add additional tools if provided
        if additional_tools:
            for tool in additional_tools:
                tool_name = getattr(tool, "name", tool.__class__.__name__.lower())
                self.tools[tool_name] = tool

        logger.info(f"🔧 Initialized {len(self.tools)} tools for {self.name}")

    def _build_constitutional_instruction(self) -> str:
        """Build Constitutional AI instruction for ADK agent."""
        try:
            # Build system prompt using constitutional template
            system_prompt = build_complete_prompt(
                PromptContext(
                    agent_role=self.role,
                    task_description="Agent system initialization",
                    tools_available=(
                        list(self.tools.keys()) if hasattr(self, "tools") else []
                    ),
                ),
            )[0]

            # Convert system prompt to instruction format for ADK
            instruction = f"""
            {system_prompt}

            CRITICAL OPERATION GUIDELINES:
            - You are a real {self.role.value} agent in the SOLVE methodology
            - Use available tools to accomplish tasks effectively
            - Follow Constitutional AI principles in all decisions
            - Provide concrete, actionable results
            - Maintain code quality and preserve existing functionality
            - Always validate your work using available tools
            """

            return instruction
        except Exception as e:
            logger.warning(f"Failed to build constitutional instruction: {e}")
            return f"""
            You are {self.name}, a {self.role.value} agent in the SOLVE methodology.

            Your primary capabilities include:
            {chr(10).join(f"- {cap}" for cap in self.capabilities)}

            Follow Constitutional AI principles:
            - Be helpful and provide actionable solutions
            - Never harm systems or data
            - Be honest about capabilities and limitations
            - Preserve existing code quality and functionality
            - Work collaboratively with other agents and users
            """

    def _get_adk_tools(self) -> list[Any]:
        """Get ADK-compatible tools for the agent."""
        # For now, return empty list as ADK tool integration needs to be implemented
        # In the future, this should convert our tools to ADK tool format
        return []

    def _build_system_prompt(self) -> str:
        """Build Constitutional AI system prompt for this agent."""
        try:
            prompt_tuple = build_complete_prompt(
                PromptContext(
                    agent_role=self.role,
                    task_description="Agent system initialization",
                    tools_available=(
                        list(self.tools.keys()) if hasattr(self, "tools") else []
                    ),
                ),
            )
            system_prompt: str = prompt_tuple[0]
            return system_prompt
        except Exception as e:
            logger.warning(f"Failed to build system prompt: {e}")
            return f"You are {self.name}, a {self.role.value} agent in the SOLVE methodology."

    async def can_handle(self, goal: Goal) -> float:
        """
        Evaluate confidence in handling a goal.

        Args:
            goal: Goal to evaluate

        Returns:
            Confidence score (0.0 to 1.0)
        """
        try:
            # Use real LLM to evaluate confidence
            confidence_prompt = self._build_confidence_prompt(goal)

            f"confidence_{uuid.uuid4().hex[:8]}"

            # Create session for confidence evaluation
            session = await self.runner.session_service.create_session(
                app_name=self.app_name,
                user_id="confidence_evaluator",
            )

            # Execute confidence evaluation via ADK using correct pattern
            from google.genai import types

            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=confidence_prompt)],
            )

            events = []
            async for event in self.runner.run_async(
                user_id="confidence_evaluator",
                session_id=session.id,
                new_message=content,
            ):
                events.append(event)

            # Extract confidence from events
            confidence = self._extract_confidence_from_events(events)

            logger.info(
                f"🎯 {self.name} confidence for '{goal.description[:50]}...': {confidence}"
            )
            return confidence

        except Exception as e:
            logger.error(f"❌ Confidence evaluation failed for {self.name}: {e}")
            # Return role-based default confidence
            return self._get_default_confidence(goal)

    def _build_confidence_prompt(self, goal: Goal) -> str:
        """Build prompt for confidence evaluation."""
        return f"""<confidence_evaluation>
<goal>{goal.description}</goal>
<agent_role>{self.role.value}</agent_role>
<agent_capabilities>
{chr(10).join(f"- {cap}" for cap in self.capabilities)}
</agent_capabilities>

Rate your confidence in successfully achieving this goal on a scale of 0.0 to 1.0.

Consider:
- How well the goal aligns with your role and capabilities
- Whether you have the necessary tools and knowledge
- The complexity and scope of the work required

Respond with ONLY a decimal number between 0.0 and 1.0, nothing else.
</confidence_evaluation>"""

    def _extract_confidence_from_events(self, events: list[Any]) -> float:
        """Extract confidence score from ADK events."""
        try:
            # Process events to find confidence score using hello_world pattern
            for event in events:
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts") and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                content = part.text.strip()
                                try:
                                    confidence = float(content)
                                    if 0.0 <= confidence <= 1.0:
                                        return confidence
                                except ValueError:
                                    continue

            # If no valid score found, return default
            logger.warning(f"No valid confidence score found in {len(events)} events")
            return 0.5

        except Exception as e:
            logger.error(f"Confidence extraction failed: {e}")
            return 0.5

    def _get_default_confidence(self, goal: Goal) -> float:
        """Get default confidence based on role and goal."""
        # Simple keyword matching for fallback
        goal_lower = goal.description.lower()

        role_keywords = {
            AgentRole.STRUCTURE: [
                "structure",
                "scaffold",
                "setup",
                "organize",
                "create",
                "directory",
            ],
            AgentRole.INTERFACE: [
                "interface",
                "api",
                "contract",
                "design",
                "endpoint",
                "schema",
            ],
            AgentRole.LOGIC: [
                "implement",
                "logic",
                "function",
                "algorithm",
                "business",
                "core",
            ],
            AgentRole.TESTING: [
                "test",
                "verify",
                "validate",
                "check",
                "quality",
                "coverage",
            ],
            AgentRole.QUALITY: [
                "quality",
                "review",
                "lint",
                "format",
                "security",
                "optimize",
            ],
        }

        keywords = role_keywords.get(self.role, [])
        matches = sum(1 for keyword in keywords if keyword in goal_lower)

        # Base confidence + keyword bonus
        base_confidence = 0.3
        keyword_bonus = min(0.6, matches * 0.2)

        return base_confidence + keyword_bonus

    async def execute(self, task: AgentTask) -> Result:
        """
        Execute a task using real ADK integration.

        Args:
            task: Task to execute

        Returns:
            Result with actual outcomes (NO MOCKS)
        """
        self.execution_count += 1
        start_time = datetime.now()

        logger.info(f"🚀 {self.name} executing task: {task.goal.description}")

        try:
            # Update task status
            task.status = TaskStatus.IN_PROGRESS

            # Build execution prompt with full context
            execution_prompt = self._build_execution_prompt(task)

            # Create unique session for this execution
            user_id = f"solve_user_{self.name}"
            session = await self.runner.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
            )

            # Execute via ADK using correct pattern
            logger.info(f"🤖 Executing via ADK with session: {session.id}")
            from google.genai import types

            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=execution_prompt)],
            )

            events = []
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content,
            ):
                events.append(event)

            logger.info(f"📥 Received {len(events)} events from ADK")

            # Process events to extract results
            success, response_text, artifacts = await self._process_execution_events(
                events, task
            )

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Create result
            result = Result(
                success=success,
                message=response_text or f"Task completed by {self.name}",
                artifacts=artifacts,
                metadata={
                    "agent": self.name,
                    "role": self.role.value,
                    "execution_time": execution_time,
                    "events_received": len(events),
                    "session_id": session.id,
                    "execution_count": self.execution_count,
                    "adk_integration": "real",  # Mark as real execution
                },
            )

            # Update task status
            task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED

            logger.info(f"✅ {self.name} completed task in {execution_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"❌ {self.name} execution failed: {e}", exc_info=True)

            # Update task status
            task.status = TaskStatus.FAILED

            return Result(
                success=False,
                message=f"Execution failed: {str(e)}",
                artifacts={},
                metadata={
                    "agent": self.name,
                    "role": self.role.value,
                    "error": str(e),
                    "execution_count": self.execution_count,
                    "adk_integration": "real",
                },
            )

    def _build_execution_prompt(self, task: AgentTask) -> str:
        """Build comprehensive execution prompt."""
        context = PromptContext(
            agent_role=self.role,
            task_description=task.goal.description,
            project_context=str(task.goal.context) if task.goal.context else None,
            tools_available=list(self.tools.keys()),
            constraints=task.goal.success_criteria,
        )

        system_prompt, user_prompt = build_complete_prompt(context)

        # Combine for execution (ADK handles system/user separation)
        return f"{system_prompt}\n\n{user_prompt}"

    async def _process_execution_events(
        self,
        events: list[Any],
        task: AgentTask,
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        Process ADK events to extract execution results.

        Returns:
            tuple: (success, response_text, artifacts)
        """
        if not events:
            logger.warning(f"No events received from ADK for {self.name}")
            return False, "No response from ADK", {}

        responses = []
        artifacts = {}

        try:
            # Extract text from events using hello_world pattern
            for event in events:
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts") and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                responses.append(part.text.strip())

            # Combine responses
            response_text = "\n".join(responses) if responses else "Task completed"

            # Execute any tool calls found in the response
            tool_execution_result = (
                await self.tool_executor.execute_tool_calls_from_response(
                    response_text,
                )
            )

            # Parse artifacts from response (if agent provided them)
            artifacts = await self._extract_artifacts_from_response(response_text, task)

            # Merge tool execution artifacts
            if tool_execution_result.get("artifacts"):
                artifacts.update(tool_execution_result["artifacts"])

            # Add tool execution summary to artifacts
            artifacts["tool_execution"] = {
                "tool_calls_found": tool_execution_result["tool_calls_found"],
                "executions": tool_execution_result["executions"],
                "tool_success": tool_execution_result["success"],
            }

            # Determine success based on response content, artifacts, and tool execution
            success = (
                len(responses) > 0
                and not any(
                    error_word in response_text.lower()
                    for error_word in ["error", "failed", "cannot", "unable"]
                )
                and tool_execution_result.get(
                    "success", True
                )  # Tool execution must also succeed
            )

            return success, response_text, artifacts

        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            return False, f"Failed to process events: {str(e)}", {}

    async def _extract_artifacts_from_response(
        self,
        response_text: str,
        task: AgentTask,
    ) -> dict[str, Any]:
        """Extract artifacts from agent response."""
        artifacts = {
            "response_text": response_text,
            "task_description": task.goal.description,
            "agent_role": self.role.value,
            "execution_timestamp": datetime.now().isoformat(),
        }

        # Role-specific artifact extraction
        if self.role == AgentRole.STRUCTURE:
            artifacts.update(await self._extract_structure_artifacts(response_text))
        elif self.role == AgentRole.INTERFACE:
            artifacts.update(await self._extract_interface_artifacts(response_text))
        elif self.role == AgentRole.LOGIC:
            artifacts.update(await self._extract_logic_artifacts(response_text))
        elif self.role == AgentRole.TESTING:
            artifacts.update(await self._extract_testing_artifacts(response_text))
        elif self.role == AgentRole.QUALITY:
            artifacts.update(await self._extract_quality_artifacts(response_text))

        return artifacts

    # Abstract methods for role-specific artifact extraction
    async def _extract_structure_artifacts(self, response: str) -> dict[str, Any]:
        """Extract structure-specific artifacts."""
        return {"structure_response": response}

    async def _extract_interface_artifacts(self, response: str) -> dict[str, Any]:
        """Extract interface-specific artifacts."""
        return {"interface_response": response}

    async def _extract_logic_artifacts(self, response: str) -> dict[str, Any]:
        """Extract logic-specific artifacts."""
        return {"logic_response": response}

    async def _extract_testing_artifacts(self, response: str) -> dict[str, Any]:
        """Extract testing-specific artifacts."""
        return {"testing_response": response}

    async def _extract_quality_artifacts(self, response: str) -> dict[str, Any]:
        """Extract quality-specific artifacts."""
        return {"quality_response": response}

    def get_execution_stats(self) -> dict[str, Any]:
        """Get agent execution statistics."""
        return {
            "name": self.name,
            "role": self.role.value,
            "execution_count": self.execution_count,
            "tools_available": list(self.tools.keys()),
            "working_directory": str(self.working_directory),
            "adk_integration": "real",
        }


# Test function to verify real ADK integration
async def test_real_adk_agent() -> bool:
    """Test the real ADK agent implementation."""
    try:
        # Create a test agent
        agent = RealADKAgent(
            name="test_structure_agent",
            role=AgentRole.STRUCTURE,
            description="Test agent for structure creation",
            capabilities=[
                "Create project directories",
                "Set up configuration files",
                "Initialize development environment",
            ],
        )

        # Test confidence evaluation
        test_goal = Goal(
            description="Create a Python package structure for a web API",
            success_criteria=["Directories created", "Files structured properly"],
        )

        confidence = await agent.can_handle(test_goal)
        _ = confidence  # Use the value

        # Test execution
        test_task = AgentTask(
            goal=test_goal, assigned_agent=agent.name, status=TaskStatus.PENDING
        )

        result = await agent.execute(test_task)

        # Show execution stats
        stats = agent.get_execution_stats()
        _ = stats  # Use the value

        return bool(result.success)

    except Exception:
        logger.exception("Agent test exception")
        return False


if __name__ == "__main__":
    asyncio.run(test_real_adk_agent())
