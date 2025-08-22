"""
ADK Adapter - Implements ADK patterns using available libraries

This module provides ADK-compatible interfaces using libraries we can install immediately,
following the architecture patterns documented in
docs/best-practices/7-adk-based-autofix-architecture.md

This is a transitional implementation that can be upgraded to real ADK when available.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from solve.knowledge_loader import KnowledgeLoader

logger = logging.getLogger(__name__)


@dataclass
class ToolContext:
    """Context provided to tools during execution"""

    session_id: str
    agent_name: str
    tool_name: str
    state: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """Add an event to the execution history"""
        event = {
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
        }
        self.history.append(event)


class BaseTool(ABC):
    """Base class for all tools - follows ADK tool pattern"""

    def __init__(self) -> None:
        self.name = self.__class__.__name__.lower().replace("tool", "")
        self.description = self.__doc__ or f"Tool for {self.name}"

    @abstractmethod
    async def run(self, context: ToolContext, **kwargs: Any) -> dict[str, Any]:
        """Execute the tool with given context and parameters"""
        pass

    def validate_params(self, **kwargs: Any) -> str | None:
        """Validate parameters - return error message or None if valid"""
        return None


class Agent(ABC):
    """Base Agent class following ADK patterns"""

    def __init__(
        self,
        name: str,
        description: str,
        instruction: str,
        tools: list[BaseTool | str] | None = None,
        sub_agents: list["Agent"] | None = None,
        model: str = "claude-3-haiku-20240307",
        knowledge_loader: KnowledgeLoader | None = None,
    ):
        self.name = name
        self.description = description
        self.instruction = instruction
        self.model = model
        self.tools = tools or []
        self.sub_agents = sub_agents or []
        self.knowledge_loader = knowledge_loader or KnowledgeLoader()

        # ADK-compatible state
        self.session_state: dict[str, Any] = {}
        self.execution_history: list[dict[str, Any]] = []

        logger.info(f"Initialized agent: {self.name}")

    async def run(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Main execution method - follows ADK agent execution pattern

        Args:
            prompt: The task or goal to execute
            context: Additional context for execution

        Returns:
            Dict containing execution results
        """
        session_id = f"{self.name}_{datetime.now().timestamp()}"
        context = context or {}

        # Log execution start
        execution_start = {
            "session_id": session_id,
            "agent": self.name,
            "prompt": prompt,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }
        self.execution_history.append(execution_start)

        try:
            # Get relevant knowledge
            relevant_knowledge = await self._get_relevant_knowledge(prompt)

            # Execute with full context
            result = await self._execute_with_context(
                prompt=prompt,
                context=context,
                knowledge=relevant_knowledge,
                session_id=session_id,
            )

            # Log execution completion
            execution_end = {
                "session_id": session_id,
                "agent": self.name,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
            self.execution_history.append(execution_end)

            return result

        except Exception as e:
            logger.error(f"Agent {self.name} execution failed: {e}")
            error_result = {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            }
            self.execution_history.append(error_result)
            return error_result

    async def _get_relevant_knowledge(self, prompt: str) -> list[dict[str, Any]]:
        """Get relevant knowledge for the prompt"""
        try:
            # Search knowledge base for relevant guidance
            guidance = self.knowledge_loader.search_for_guidance(prompt)

            # Also get agent-specific guidelines
            agent_guidance = self.knowledge_loader.get_agent_guidelines(self.name)

            return guidance + agent_guidance

        except Exception as e:
            logger.warning(f"Failed to load knowledge for {self.name}: {e}")
            return []

    @abstractmethod
    async def _execute_with_context(
        self,
        prompt: str,
        context: dict[str, Any],
        knowledge: list[dict[str, Any]],
        session_id: str,
    ) -> dict[str, Any]:
        """Execute the agent's core logic with full context"""
        pass

    async def use_tool(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Use a tool - follows ADK tool usage pattern"""
        tool_context = ToolContext(
            session_id=f"{self.name}_{datetime.now().timestamp()}",
            agent_name=self.name,
            tool_name=tool_name,
            state=self.session_state,
        )

        # Find the tool
        tool = None
        for t in self.tools:
            if isinstance(t, BaseTool) and t.name == tool_name:
                tool = t
                break
            elif isinstance(t, str) and t == tool_name:
                # Tool reference - would need tool registry in full implementation
                logger.warning(f"Tool reference {tool_name} not resolved")
                return {"error": f"Tool {tool_name} not found"}

        if not tool:
            return {"error": f"Tool {tool_name} not found"}

        # Validate parameters
        validation_error = tool.validate_params(**kwargs)
        if validation_error:
            return {"error": validation_error}

        # Execute tool
        try:
            result = await tool.run(tool_context, **kwargs)

            # Update session state
            self.session_state.update(tool_context.state)

            return result

        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return {"error": str(e)}

    async def delegate_to_sub_agent(
        self,
        sub_agent_name: str,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Delegate to a sub-agent - follows ADK delegation pattern"""
        sub_agent = None
        for agent in self.sub_agents:
            if agent.name == sub_agent_name:
                sub_agent = agent
                break

        if not sub_agent:
            return {"error": f"Sub-agent {sub_agent_name} not found"}

        # Delegate execution
        return await sub_agent.run(prompt, context)


class LlmAgent(Agent):
    """LLM-powered agent - follows ADK LlmAgent pattern"""

    async def _execute_with_context(
        self,
        prompt: str,
        context: dict[str, Any],
        knowledge: list[dict[str, Any]],
        session_id: str,
    ) -> dict[str, Any]:
        """Execute using LLM with constitutional AI principles"""

        # Build comprehensive system prompt
        system_prompt = self._build_system_prompt(knowledge)

        # Build user prompt with context
        user_prompt = self._build_user_prompt(prompt, context)

        # Execute LLM call (would use actual LLM client in full implementation)
        result = await self._execute_llm_call(system_prompt, user_prompt)

        return {
            "success": True,
            "result": result,
            "session_id": session_id,
            "model": self.model,
            "knowledge_used": len(knowledge),
        }

    def _build_system_prompt(self, knowledge: list[dict[str, Any]]) -> str:
        """Build system prompt with constitutional AI principles"""
        prompt_parts = [
            f"You are {self.name}: {self.description}",
            "",
            "## Your Role and Capabilities:",
            self.instruction,
            "",
            "## Constitutional AI Principles:",
            "1. Always prioritize code quality and correctness",
            "2. Never take destructive actions without explicit permission",
            "3. Provide clear explanations for all decisions",
            "4. Respect project constraints and conventions",
            "5. Learn from feedback and improve continuously",
            "",
            "## Available Tools:",
        ]

        for tool in self.tools:
            if isinstance(tool, BaseTool):
                prompt_parts.append(f"- {tool.name}: {tool.description}")
            elif isinstance(tool, str):
                prompt_parts.append(f"- {tool}: Available tool")

        if self.sub_agents:
            prompt_parts.extend(
                [
                    "",
                    "## Sub-Agents You Can Delegate To:",
                ],
            )
            for agent in self.sub_agents:
                prompt_parts.append(f"- {agent.name}: {agent.description}")

        if knowledge:
            prompt_parts.extend(
                [
                    "",
                    "## Relevant Knowledge and Best Practices:",
                ],
            )
            for item in knowledge[:3]:  # Limit to top 3 most relevant
                prompt_parts.append(
                    f"- {item['document']}: {item.get('guidance_type', 'guidance')}",
                )

        return "\n".join(prompt_parts)

    def _build_user_prompt(self, prompt: str, context: dict[str, Any]) -> str:
        """Build user prompt with context"""
        prompt_parts = [
            f"## Task: {prompt}",
            "",
        ]

        if context:
            prompt_parts.extend(
                [
                    "## Context:",
                    str(context),
                    "",
                ],
            )

        prompt_parts.extend(
            [
                "## Instructions:",
                "1. Think step-by-step about the task",
                "2. Use available tools when needed",
                "3. Delegate to sub-agents for specialized tasks",
                "4. Follow constitutional AI principles",
                "5. Provide clear, actionable results",
                "",
                "Execute the task now:",
            ],
        )

        return "\n".join(prompt_parts)

    async def _execute_llm_call(self, system_prompt: str, user_prompt: str) -> str:
        """Execute LLM call with actual ADK integration"""
        # This requires ADK LLM client integration
        # Should use ADK's LLMClient or similar for actual execution
        raise NotImplementedError(
            "LLM execution requires ADK LLM client integration. "
            "Implement using ADK's LLMClient or equivalent service."
        )


class SequentialAgent(Agent):
    """Sequential agent coordination - follows ADK SequentialAgent pattern"""

    async def _execute_with_context(
        self,
        prompt: str,
        context: dict[str, Any],
        knowledge: list[dict[str, Any]],
        session_id: str,
    ) -> dict[str, Any]:
        """Execute sub-agents in sequence"""
        results = []
        current_context = context.copy()

        for agent in self.sub_agents:
            logger.info(f"Executing sub-agent: {agent.name}")

            # Execute sub-agent
            result = await agent.run(prompt, current_context)
            results.append(result)

            # Update context with result
            current_context[f"{agent.name}_result"] = result

            # Stop if any agent fails
            if not result.get("success", True):
                logger.error(f"Sub-agent {agent.name} failed, stopping sequence")
                break

        return {
            "success": all(r.get("success", True) for r in results),
            "results": results,
            "session_id": session_id,
            "agents_executed": len(results),
        }


class ParallelAgent(Agent):
    """Parallel agent coordination - follows ADK ParallelAgent pattern"""

    async def _execute_with_context(
        self,
        prompt: str,
        context: dict[str, Any],
        knowledge: list[dict[str, Any]],
        session_id: str,
    ) -> dict[str, Any]:
        """Execute sub-agents in parallel"""

        # Create tasks for all sub-agents
        tasks = []
        for agent in self.sub_agents:
            task = asyncio.create_task(agent.run(prompt, context))
            tasks.append((agent.name, task))

        # Wait for all to complete
        results = []
        for agent_name, task in tasks:
            try:
                result = await task
                results.append(result)
                logger.info(f"Sub-agent {agent_name} completed")
            except Exception as e:
                logger.error(f"Sub-agent {agent_name} failed: {e}")
                results.append({"success": False, "error": str(e)})

        return {
            "success": all(r.get("success", True) for r in results),
            "results": results,
            "session_id": session_id,
            "agents_executed": len(results),
        }


# Example SOLVE-specific tools following ADK patterns
class SOLVEGovernanceTool(BaseTool):
    """Tool for accessing SOLVE governance and best practices"""

    def __init__(self) -> None:
        super().__init__()
        self.description = "Access SOLVE governance rules and best practices"
        self.knowledge_loader = KnowledgeLoader()

    async def run(self, context: ToolContext, **kwargs: Any) -> dict[str, Any]:
        """Get governance guidance for a query or file"""
        query = kwargs.get("query", "")
        kwargs.get("file_path", "")

        try:
            if query:
                guidance = self.knowledge_loader.search_for_guidance(query)
            else:
                guidance = self.knowledge_loader.list_available_documents()

            return {
                "success": True,
                "guidance": guidance,
                "source": "SOLVE knowledge base",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


class ValidatorTool(BaseTool):
    """Tool for validating code and preserving structure"""

    def __init__(self) -> None:
        super().__init__()
        self.description = "Validate code and check preservation rules"

    async def run(self, context: ToolContext, **kwargs: Any) -> dict[str, Any]:
        """Validate code with specified checks"""
        code = kwargs.get("code", "")
        check_type = kwargs.get("check_type", "syntax")

        try:
            if check_type == "syntax":
                # Simple syntax validation
                try:
                    compile(code, "<string>", "exec")
                    return {"success": True, "valid": True, "check_type": check_type}
                except SyntaxError as e:
                    return {
                        "success": True,
                        "valid": False,
                        "error": str(e),
                        "check_type": check_type,
                    }

            elif check_type == "preservation":
                # Check for preservation violations
                violations = []
                if "self." not in code and "self " in code:
                    violations.append("Missing self. prefix on instance variables")

                return {
                    "success": True,
                    "violations": violations,
                    "preserved": len(violations) == 0,
                    "check_type": check_type,
                }

            else:
                return {"success": False, "error": f"Unknown check type: {check_type}"}

        except Exception as e:
            return {"success": False, "error": str(e)}


# Factory function to create ADK-style agent systems
def create_solve_agent_system(knowledge_loader: KnowledgeLoader | None = None) -> Agent:
    """Create a complete SOLVE agent system following ADK patterns"""

    knowledge_loader = knowledge_loader or KnowledgeLoader()

    # Create specialized agents
    structure_agent = LlmAgent(
        name="structure_agent",
        description="Creates and organizes project structure",
        instruction=(
            "You specialize in creating clean, organized project structures "
            "following best practices."
        ),
        tools=[SOLVEGovernanceTool(), ValidatorTool()],
        knowledge_loader=knowledge_loader,
    )

    interface_agent = LlmAgent(
        name="interface_agent",
        description="Designs APIs and interfaces",
        instruction="You specialize in designing clean, well-documented APIs and interfaces.",
        tools=[SOLVEGovernanceTool(), ValidatorTool()],
        knowledge_loader=knowledge_loader,
    )

    logic_agent = LlmAgent(
        name="logic_agent",
        description="Implements business logic",
        instruction="You specialize in implementing robust, tested business logic.",
        tools=[SOLVEGovernanceTool(), ValidatorTool()],
        knowledge_loader=knowledge_loader,
    )

    quality_agent = LlmAgent(
        name="quality_agent",
        description="Ensures code quality and testing",
        instruction="You specialize in code quality, testing, and validation.",
        tools=[SOLVEGovernanceTool(), ValidatorTool()],
        knowledge_loader=knowledge_loader,
    )

    # Create main orchestrator
    solve_orchestrator = SequentialAgent(
        name="solve_orchestrator",
        description="Coordinates SOLVE development workflow",
        instruction="""
        You coordinate the SOLVE development workflow using specialized agents.

        Your role:
        1. Analyze development goals and break them into tasks
        2. Delegate to appropriate specialist agents
        3. Ensure quality and consistency across all work
        4. Learn from outcomes to improve future coordination

        Always follow SOLVE principles: Structure, Outline, Logic, Verify, Enhance
        """,
        tools=[SOLVEGovernanceTool(), ValidatorTool()],
        sub_agents=[structure_agent, interface_agent, logic_agent, quality_agent],
        knowledge_loader=knowledge_loader,
    )

    return solve_orchestrator
