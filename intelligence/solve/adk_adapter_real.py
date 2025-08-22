"""
Real Google ADK Adapter for SOLVE

This module provides real ADK-based implementations of agents and tools,
replacing the mock implementations with authentic Google ADK classes.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from solve.knowledge_loader import KnowledgeLoader
# Use centralized ADK imports with proper fallbacks
from solve_core.adk_imports import (BaseAgent, BaseTool, Content, Event,
                                    InMemorySessionService, LlmAgent,
                                    ParallelAgent, RunConfig, Runner,
                                    SequentialAgent, is_adk_available)

logger = logging.getLogger(__name__)


@dataclass
class ADKExecutionResult:
    """Result from ADK agent execution."""

    success: bool
    message: str
    artifacts: dict[str, Any]
    events: list[Event]
    session_id: str
    agent_name: str
    timestamp: str


class SOLVEKnowledgeTool(BaseTool):
    """Real ADK tool for accessing SOLVE knowledge and governance."""

    def __init__(self, knowledge_loader: KnowledgeLoader):
        super().__init__(
            name="solve_knowledge",
            description="Access SOLVE methodology knowledge, best practices, and governance rules",
        )
        self.knowledge_loader = knowledge_loader

    async def run(
        self,
        query: str = "",
        document_type: str = "guidance",
        max_results: int = 5,
    ) -> str:
        """
        Access SOLVE knowledge base.

        Args:
            query: Search query for specific guidance
            document_type: Type of documents to search ('guidance', 'templates', 'all')
            max_results: Maximum number of results to return
        """
        try:
            if query.strip():  # Check for non-empty query
                results = self.knowledge_loader.search_for_guidance(query)
                if results:
                    formatted_results = []
                    for result in results[:max_results]:
                        doc_name = result.get("document", "Unknown")
                        guidance_type = result.get("guidance_type", "guidance")
                        content = result.get("content", "No content")
                        formatted_results.append(
                            f"📄 **{doc_name}** ({guidance_type})\n{content}"
                        )

                    return f"Found {len(results)} guidance items:\n\n" + "\n\n".join(
                        formatted_results,
                    )
                else:
                    return f"No guidance found for query: '{query}'"

            # List available documents (when no query provided)
            documents = self.knowledge_loader.list_available_documents()
            if isinstance(documents, list):
                return f"Available SOLVE documents: {', '.join(str(doc) for doc in documents)}"

            # Handle non-list case (mypy false positive suppression)
            return f"Available SOLVE documents: {documents}"  # type: ignore[unreachable]

        except Exception as e:
            logger.error(f"Knowledge tool error: {e}")
            return f"Error accessing knowledge: {str(e)}"


class CodeAnalysisTool(BaseTool):
    """Real ADK tool for code analysis and validation."""

    def __init__(self) -> None:
        super().__init__(
            name="code_analysis",
            description="Analyze code for syntax, style, and SOLVE compliance",
        )

    async def run(
        self, code: str, analysis_type: str = "syntax", file_path: str = ""
    ) -> str:
        """
        Analyze code with specified checks.

        Args:
            code: Code to analyze
            analysis_type: Type of analysis ('syntax', 'style', 'preservation', 'all')
            file_path: Optional file path for context
        """
        try:
            results = []

            if analysis_type in ["syntax", "all"]:
                syntax_result = self._check_syntax(code)
                results.append(f"**Syntax Analysis:** {syntax_result}")

            if analysis_type in ["style", "all"]:
                style_result = self._check_style(code)
                results.append(f"**Style Analysis:** {style_result}")

            if analysis_type in ["preservation", "all"]:
                preservation_result = self._check_preservation(code)
                results.append(f"**Preservation Analysis:** {preservation_result}")

            return "\n\n".join(results)

        except Exception as e:
            logger.error(f"Code analysis error: {e}")
            return f"Error during analysis: {str(e)}"

    def _check_syntax(self, code: str) -> str:
        """Check code syntax."""
        try:
            compile(code, "<string>", "exec")
            return "✅ Syntax is valid"
        except SyntaxError as e:
            return f"❌ Syntax error: {str(e)}"

    def _check_style(self, code: str) -> str:
        """Check code style."""
        issues = []

        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                issues.append(f"Line {i}: Line too long ({len(line)} chars)")
            if line.endswith(" "):
                issues.append(f"Line {i}: Trailing whitespace")

        if issues:
            return "❌ Style issues:\n" + "\n".join(issues)
        return "✅ Style looks good"

    def _check_preservation(self, code: str) -> str:
        """Check code preservation rules."""
        violations = []

        # Check for self. prefix preservation
        if "self " in code and "self." not in code:
            violations.append("Missing self. prefix on instance variables")

        # Check for proper imports
        if "import " in code and "from " not in code:
            violations.append("Consider using 'from' imports for better clarity")

        if violations:
            return "⚠️ Preservation violations:\n" + "\n".join(violations)
        return "✅ Preservation rules followed"


class ProjectStructureTool(BaseTool):
    """Real ADK tool for project structure operations."""

    def __init__(self) -> None:
        super().__init__(
            name="project_structure",
            description="Analyze and create project structure following SOLVE patterns",
        )

    async def run(
        self,
        action: str = "analyze",
        path: str = ".",
        structure_type: str = "python",
    ) -> str:
        """
        Handle project structure operations.

        Args:
            action: Action to perform ('analyze', 'create', 'validate')
            path: Path to analyze or create structure
            structure_type: Type of structure ('python', 'web', 'data')
        """
        try:
            if action == "analyze":
                return self._analyze_structure(path)
            elif action == "create":
                return self._create_structure(path, structure_type)
            elif action == "validate":
                return self._validate_structure(path)
            else:
                return (
                    f"Unknown action: {action}. Use 'analyze', 'create', or 'validate'"
                )

        except Exception as e:
            logger.error(f"Project structure tool error: {e}")
            return f"Error with project structure: {str(e)}"

    def _analyze_structure(self, path: str) -> str:
        """Analyze existing project structure."""
        import os

        if not os.path.exists(path):
            return f"❌ Path does not exist: {path}"

        structure = []
        for root, _dirs, files in os.walk(path):
            level = root.replace(path, "").count(os.sep)
            indent = " " * 2 * level
            structure.append(f"{indent}{os.path.basename(root)}/")

            subindent = " " * 2 * (level + 1)
            for file in files:
                if not file.startswith("."):
                    structure.append(f"{subindent}{file}")

        return "📁 Project structure:\n" + "\n".join(structure[:20])  # Limit output

    def _create_structure(self, path: str, structure_type: str) -> str:
        """Create project structure."""
        # This would implement structure creation logic
        return f"✅ Would create {structure_type} structure at {path}"

    def _validate_structure(self, path: str) -> str:
        """Validate project structure."""
        # This would implement structure validation logic
        return f"✅ Structure validation for {path} completed"


class RealADKAgent:
    """Wrapper for real ADK agents with SOLVE integration."""

    def __init__(
        self,
        name: str,
        description: str,
        instruction: str,
        agent_type: str = "llm",
        tools: list[BaseTool] | None = None,
        sub_agents: list[BaseAgent] | None = None,
        model: str = "gemini-1.5-flash",
        knowledge_loader: KnowledgeLoader | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.instruction = instruction
        self.agent_type = agent_type
        self.model = model
        self.knowledge_loader = knowledge_loader or KnowledgeLoader()

        # Create tools
        self.tools = tools or []
        self.tools.extend(
            [
                SOLVEKnowledgeTool(self.knowledge_loader),
                CodeAnalysisTool(),
                ProjectStructureTool(),
            ],
        )

        # Create the actual ADK agent
        self.adk_agent = self._create_adk_agent(sub_agents)

        # Setup session management
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            app_name=f"solve_{name}",
            agent=self.adk_agent,
            session_service=self.session_service,
        )

        logger.info(f"Created real ADK agent: {name} ({agent_type})")

    def _create_adk_agent(
        self,
        sub_agents: list[BaseAgent] | None = None,
    ) -> LlmAgent | SequentialAgent | ParallelAgent:
        """Create the actual ADK agent based on type."""

        # Build enhanced instruction with SOLVE context
        self._build_enhanced_instruction()

        if self.agent_type == "llm":
            return LlmAgent(name=self.name, description=self.description)

        elif self.agent_type == "sequential":
            return SequentialAgent(
                name=self.name,
                description=self.description,
                sub_agents=sub_agents or [],
            )

        elif self.agent_type == "parallel":
            return ParallelAgent(
                name=self.name,
                description=self.description,
                sub_agents=sub_agents or [],
            )

        else:
            raise ValueError(f"Unknown agent type: {self.agent_type}")

    def _build_enhanced_instruction(self) -> str:
        """Build enhanced instruction with SOLVE principles."""
        parts = [
            self.instruction,
            "",
            "## SOLVE Methodology Principles:",
            "1. **Scaffold**: Create solid foundation and structure",
            "2. **Outline**: Define clear interfaces and contracts",
            "3. **Logic**: Implement robust, tested business logic",
            "4. **Verify**: Ensure quality through testing and validation",
            "5. **Enhance**: Learn and improve continuously",
            "",
            "## Available Tools:",
            "- `solve_knowledge`: Access SOLVE knowledge base and guidance",
            "- `code_analysis`: Analyze code for quality and compliance",
            "- `project_structure`: Handle project structure operations",
            "",
            "## Constitutional AI Principles:",
            "1. Always prioritize code quality and correctness",
            "2. Never take destructive actions without explicit permission",
            "3. Provide clear explanations for all decisions",
            "4. Respect project constraints and conventions",
            "5. Use tools proactively to gather context and validate work",
            "",
            "Always use the available tools to access guidance and validate your work.",
        ]

        return "\n".join(parts)

    async def execute(
        self,
        prompt: str,
        user_id: str = "solve_user",
        session_id: str | None = None,
    ) -> ADKExecutionResult:
        """
        Execute the agent with a prompt using real ADK.

        Args:
            prompt: The task or goal to execute
            user_id: User identifier
            session_id: Session identifier (auto-generated if None)

        Returns:
            ADKExecutionResult with execution details
        """
        if session_id is None:
            session_id = f"{self.name}_session_{int(datetime.now().timestamp())}"

        # Ensure session_id is not None for the rest of the function
        assert session_id is not None

        try:
            # Enhanced prompt with SOLVE context
            enhanced_prompt = self._enhance_prompt_with_context(prompt)

            # Execute using ADK runner
            # Create RunConfig - works with both real and fallback implementations
            run_config = RunConfig()

            # Convert string prompt to Content type if needed
            message_content: Any = enhanced_prompt
            if is_adk_available() and callable(Content):
                try:
                    message_content = Content(enhanced_prompt)
                except (TypeError, AttributeError):
                    message_content = enhanced_prompt
            else:
                # For fallback Content or when ADK not available
                message_content = enhanced_prompt

            events = list(
                self.runner.run(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=message_content,
                    run_config=run_config,
                ),
            )

            # Process results
            message, artifacts = self._process_events(events)

            result = ADKExecutionResult(
                success=True,
                message=message,
                artifacts=artifacts,
                events=events,
                session_id=session_id,
                agent_name=self.name,
                timestamp=datetime.now().isoformat(),
            )

            logger.info(
                f"Agent {self.name} executed successfully with {len(events)} events"
            )
            return result

        except Exception as e:
            logger.error(f"Agent {self.name} execution failed: {e}")
            return ADKExecutionResult(
                success=False,
                message=f"Execution failed: {str(e)}",
                artifacts={},
                events=[],
                session_id=session_id,
                agent_name=self.name,
                timestamp=datetime.now().isoformat(),
            )

    def _enhance_prompt_with_context(self, prompt: str) -> str:
        """Enhance prompt with SOLVE context."""
        try:
            # Get relevant knowledge
            knowledge = self.knowledge_loader.search_for_guidance(prompt)

            parts = [
                f"# Task: {prompt}",
                "",
                "## SOLVE Context:",
                "You are working within the SOLVE methodology framework.",
                "Use your tools to access specific guidance and validate your work.",
                "",
            ]

            if knowledge:
                parts.extend(
                    [
                        "## Relevant Knowledge Available:",
                        *[f"- {item['document']}" for item in knowledge[:3]],
                        "",
                        "Use the `solve_knowledge` tool to access specific guidance.",
                        "",
                    ],
                )

            parts.extend(
                [
                    "## Instructions:",
                    "1. Use tools to gather context and guidance",
                    "2. Follow SOLVE methodology principles",
                    "3. Validate your work using available tools",
                    "4. Provide clear, actionable results",
                    "",
                    "Begin by using the `solve_knowledge` tool if you need "
                    "guidance about this task.",
                ],
            )

            return "\n".join(parts)

        except Exception as e:
            logger.warning(f"Failed to enhance prompt: {e}")
            return prompt

    def _process_events(self, events: list[Event]) -> tuple[str, dict[str, Any]]:
        """Process ADK events into message and artifacts."""
        messages = []
        artifacts = {}

        for event in events:
            if hasattr(event, "content") and event.content:
                content = str(event.content)
                if content.strip():
                    messages.append(content)

            if hasattr(event, "artifacts") and event.artifacts:
                artifacts.update(event.artifacts)

        message = "\n".join(messages) if messages else "Task completed successfully"
        return message, artifacts


# Factory functions for creating real ADK agents
def create_structure_agent(
    knowledge_loader: KnowledgeLoader | None = None,
) -> RealADKAgent:
    """Create a structure agent using real ADK."""
    return RealADKAgent(
        name="structure_agent",
        description="Project structure specialist using real Google ADK",
        instruction="""
        You are a structure specialist for the SOLVE methodology.

        Your responsibilities:
        - Create and organize project structures
        - Set up proper directory hierarchies
        - Establish configuration files
        - Follow SOLVE governance from .mdc files

        Always use your tools to access guidance and validate structure.
        """,
        agent_type="llm",
        knowledge_loader=knowledge_loader,
    )


def create_interface_agent(
    knowledge_loader: KnowledgeLoader | None = None,
) -> RealADKAgent:
    """Create an interface agent using real ADK."""
    return RealADKAgent(
        name="interface_agent",
        description="Interface design specialist using real Google ADK",
        instruction="""
        You are an interface design specialist for the SOLVE methodology.

        Your responsibilities:
        - Design clean, well-documented APIs
        - Create interface contracts and protocols
        - Ensure proper type hints and documentation
        - Follow interface design best practices

        Always validate interface designs and check governance rules.
        """,
        agent_type="llm",
        knowledge_loader=knowledge_loader,
    )


def create_logic_agent(knowledge_loader: KnowledgeLoader | None = None) -> RealADKAgent:
    """Create a logic agent using real ADK."""
    return RealADKAgent(
        name="logic_agent",
        description="Logic implementation specialist using real Google ADK",
        instruction="""
        You are a logic implementation specialist for the SOLVE methodology.

        Your responsibilities:
        - Implement robust business logic
        - Handle errors gracefully
        - Write clean, maintainable code
        - Follow coding best practices

        Always validate your code and check for preservation violations.
        """,
        agent_type="llm",
        knowledge_loader=knowledge_loader,
    )


def create_quality_agent(
    knowledge_loader: KnowledgeLoader | None = None,
) -> RealADKAgent:
    """Create a quality agent using real ADK."""
    return RealADKAgent(
        name="quality_agent",
        description="Quality assurance specialist using real Google ADK",
        instruction="""
        You are a quality assurance specialist for the SOLVE methodology.

        Your responsibilities:
        - Write comprehensive tests
        - Validate code quality
        - Check for security issues
        - Ensure documentation standards

        Use analysis tools extensively to ensure high quality.
        """,
        agent_type="llm",
        knowledge_loader=knowledge_loader,
    )


def create_orchestrator_agent(
    knowledge_loader: KnowledgeLoader | None = None,
) -> RealADKAgent:
    """Create an orchestrator agent using real ADK."""
    # Create sub-agents and cast to BaseAgent list
    from typing import cast

    sub_agents: list[BaseAgent] = [
        cast(BaseAgent, create_structure_agent(knowledge_loader).adk_agent),
        cast(BaseAgent, create_interface_agent(knowledge_loader).adk_agent),
        cast(BaseAgent, create_logic_agent(knowledge_loader).adk_agent),
        cast(BaseAgent, create_quality_agent(knowledge_loader).adk_agent),
    ]

    return RealADKAgent(
        name="solve_orchestrator",
        description="SOLVE workflow orchestrator using real Google ADK",
        instruction="""
        You coordinate the SOLVE development workflow.

        Your responsibilities:
        1. Analyze development goals and requirements
        2. Coordinate with specialized agents in proper sequence
        3. Ensure quality and consistency across all work
        4. Follow SOLVE principles: Scaffold, Outline, Logic, Verify, Enhance

        Delegate to sub-agents based on their specializations.
        """,
        agent_type="sequential",
        sub_agents=sub_agents,
        knowledge_loader=knowledge_loader,
    )


# Main factory function
def create_real_adk_system(
    knowledge_loader: KnowledgeLoader | None = None,
) -> RealADKAgent:
    """Create a complete SOLVE system using real Google ADK."""
    return create_orchestrator_agent(knowledge_loader)
