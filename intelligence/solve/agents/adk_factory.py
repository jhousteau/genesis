"""
ADK Agent Factory System

Creates properly configured ADK agents following official patterns from:
- adk-samples/python/agents/academic-research/
- adk-samples/python/agents/multi-agent/
- adk-python/src/google/adk/agents/

This factory system provides:
1. Factory functions for each agent type
2. Integration with tool registry
3. Configuration management (dev/prod)
4. Agent discovery and listing
5. Team creation utilities
6. Constitutional AI integration
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from solve.constitutional_ai import ConstitutionalAI
from solve.prompts.constitutional_template import AgentRole
from solve.tools.adk_registry import ToolCategory, get_registry

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent as Agent
else:
    Agent = "Agent"

# ADK imports - handled dynamically to avoid import-time dependencies
logger = logging.getLogger(__name__)

# Tool name mappings - maps expected names to actual registry names
TOOL_NAME_MAPPING = {
    "filesystem": "filesystem",  # Direct mapping
    "git": "safegit",  # Use safe git wrapper
    "directory_analyzer": "codeanalysisadk",  # Map to code analysis
    "code_analyzer": "codeanalysisadk",
    "documentation_generator": "codeanalysisadk",  # Use code analysis for now
    "schema_validator": "codeanalysisadk",  # Use code analysis for validation
    "code_generator": "filesystem",  # Use filesystem for code generation
    "refactoring_tool": "codeanalysisadk",  # Use code analysis for refactoring
    "dependency_manager": "codeanalysisadk",  # Use code analysis for dependencies
    "test_runner": "codeanalysisadk",  # Use code analysis for test discovery
    "coverage_analyzer": "codeanalysisadk",  # Use code analysis for coverage
    "test_generator": "filesystem",  # Use filesystem for test generation
    "linter": "codeanalysisadk",  # Use code analysis for linting
    "security_scanner": "codeanalysisadk",  # Use code analysis for security
    "autofix": "filesystem",  # Use filesystem for fixes
}


class SafetyLevel(Enum):
    """Safety levels for agent operation"""

    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


class ModelType(Enum):
    """Supported model types"""

    GEMINI_2_0_FLASH = "gemini-2.0-flash-exp"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    CLAUDE_3_5_SONNET = "claude-3.5-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"


@dataclass
class AgentConfig:
    """Configuration for agent creation"""

    name: str
    model: ModelType = ModelType.GEMINI_2_0_FLASH
    safety_level: SafetyLevel = SafetyLevel.MODERATE
    tool_categories: list[ToolCategory] | None = None
    tool_names: list[str] | None = None
    custom_tools: list[Any] | None = None
    max_iterations: int = 10
    timeout_seconds: int = 300
    enable_monitoring: bool = True
    working_directory: Path | None = None
    constitutional_ai: bool = True
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 8192

    def __post_init__(self) -> None:
        if self.tool_categories is None:
            self.tool_categories = []
        if self.tool_names is None:
            self.tool_names = []
        if self.custom_tools is None:
            self.custom_tools = []


class AgentFactory:
    """
    Factory for creating ADK agents with proper configuration.

    Follows patterns from adk-samples/python/agents/academic-research/
    and multi-agent examples.
    """

    def __init__(self, working_directory: Path | None = None):
        """Initialize the agent factory"""
        self.working_directory = working_directory or Path.cwd()
        self.tool_registry = get_registry()
        self.constitutional_ai = ConstitutionalAI()
        self.created_agents: dict[str, Agent] = {}

        # Initialize lesson capture system for loading lessons
        from solve.lessons import LessonCapture

        self.lesson_capture = LessonCapture()

        logger.info(
            f"Initialized AgentFactory with working directory: {self.working_directory}"
        )

    def create_structure_agent(self, config: AgentConfig | None = None) -> "Agent":
        """
        Create a structure agent for scaffolding and project setup.

        Args:
            config: Optional configuration override

        Returns:
            Configured ADK Agent instance
        """
        if config is None:
            config = AgentConfig(
                name="structure_agent",
                tool_categories=[ToolCategory.FILESYSTEM, ToolCategory.GIT],
                tool_names=[
                    "filesystem",
                    "git",
                    "directory_analyzer",
                ],  # Will be mapped to actual names
            )

        # Get tools for structure operations
        tools = self._get_tools_for_config(config)

        # Build system instruction with Constitutional AI
        system_instruction = self._build_system_instruction(
            role=AgentRole.STRUCTURE,
            config=config,
            tools=tools,
            specific_instructions="""
            You are a Structure Agent specialized in project scaffolding and setup.

            Your primary responsibilities:
            - Create well-organized project directory structures
            - Set up configuration files and development environments
            - Initialize version control and documentation
            - Follow industry best practices for project organization

            Always ensure:
            - Directory structures are logical and maintainable
            - Configuration files are properly formatted
            - Documentation is created for project structure
            - Git repository is initialized with proper ignore files
            """,
        )

        agent = self._create_adk_agent(
            name=config.name,
            model=config.model.value,
            description="Agent for creating project structure and scaffolding",
            system_instruction=system_instruction,
            tools=tools,
            config=config,
        )

        self.created_agents[config.name] = agent
        logger.info(f"Created structure agent: {config.name}")
        return agent

    def create_interface_agent(self, config: AgentConfig | None = None) -> "Agent":
        """
        Create an interface agent for API design and contracts.

        Args:
            config: Optional configuration override

        Returns:
            Configured ADK Agent instance
        """
        if config is None:
            config = AgentConfig(
                name="interface_agent",
                tool_categories=[ToolCategory.ANALYSIS, ToolCategory.DOCUMENTATION],
                tool_names=[
                    "code_analyzer",
                    "documentation_generator",
                    "schema_validator",
                ],  # Will be mapped
            )

        tools = self._get_tools_for_config(config)

        system_instruction = self._build_system_instruction(
            role=AgentRole.INTERFACE,
            config=config,
            tools=tools,
            specific_instructions="""
            You are an Interface Agent specialized in API design and system contracts.

            Your primary responsibilities:
            - Design clear, consistent APIs and interfaces
            - Create comprehensive documentation for interfaces
            - Validate interface contracts and schemas
            - Ensure proper separation of concerns

            Always ensure:
            - APIs are well-documented and consistent
            - Interface contracts are validated
            - Documentation includes examples and usage patterns
            - Interfaces follow industry standards and best practices
            """,
        )

        agent = self._create_adk_agent(
            name=config.name,
            model=config.model.value,
            description="Agent for designing interfaces and API contracts",
            system_instruction=system_instruction,
            tools=tools,
            config=config,
        )

        self.created_agents[config.name] = agent
        logger.info(f"Created interface agent: {config.name}")
        return agent

    def create_logic_agent(self, config: AgentConfig | None = None) -> "Agent":
        """
        Create a logic agent for business logic implementation.

        Args:
            config: Optional configuration override

        Returns:
            Configured ADK Agent instance
        """
        if config is None:
            config = AgentConfig(
                name="logic_agent",
                tool_categories=[ToolCategory.FILESYSTEM, ToolCategory.TESTING],
                tool_names=[
                    "code_generator",
                    "refactoring_tool",
                    "dependency_manager",
                ],  # Will be mapped
            )

        tools = self._get_tools_for_config(config)

        system_instruction = self._build_system_instruction(
            role=AgentRole.LOGIC,
            config=config,
            tools=tools,
            specific_instructions="""
            You are a Logic Agent specialized in business logic implementation.

            Your primary responsibilities:
            - Implement core business logic and algorithms
            - Write clean, maintainable, and efficient code
            - Follow established patterns and architectural guidelines
            - Ensure proper error handling and edge case coverage

            Always ensure:
            - Code is well-structured and follows best practices
            - Business logic is separated from infrastructure concerns
            - Error handling is comprehensive and informative
            - Implementation matches interface specifications
            """,
        )

        agent = self._create_adk_agent(
            name=config.name,
            model=config.model.value,
            description="Agent for implementing business logic and core functionality",
            system_instruction=system_instruction,
            tools=tools,
            config=config,
        )

        self.created_agents[config.name] = agent
        logger.info(f"Created logic agent: {config.name}")
        return agent

    def create_testing_agent(self, config: AgentConfig | None = None) -> "Agent":
        """
        Create a testing agent for test creation and validation.

        Args:
            config: Optional configuration override

        Returns:
            Configured ADK Agent instance
        """
        if config is None:
            config = AgentConfig(
                name="testing_agent",
                tool_categories=[ToolCategory.TESTING, ToolCategory.ANALYSIS],
                tool_names=[
                    "test_runner",
                    "coverage_analyzer",
                    "test_generator",
                ],  # Will be mapped
            )

        tools = self._get_tools_for_config(config)

        system_instruction = self._build_system_instruction(
            role=AgentRole.TESTING,
            config=config,
            tools=tools,
            specific_instructions="""
            You are a Testing Agent specialized in test creation and validation.

            Your primary responsibilities:
            - Create comprehensive test suites for all functionality
            - Run tests and analyze coverage reports
            - Identify and fix test failures
            - Ensure testing best practices are followed

            Always ensure:
            - Tests cover all critical functionality and edge cases
            - Test code is clean, maintainable, and well-documented
            - Coverage reports meet quality standards
            - Tests are reliable and don't produce false positives
            """,
        )

        agent = self._create_adk_agent(
            name=config.name,
            model=config.model.value,
            description="Agent for creating and running tests",
            system_instruction=system_instruction,
            tools=tools,
            config=config,
        )

        self.created_agents[config.name] = agent
        logger.info(f"Created testing agent: {config.name}")
        return agent

    def create_quality_agent(self, config: AgentConfig | None = None) -> "Agent":
        """
        Create a quality agent for code review and improvement.

        Args:
            config: Optional configuration override

        Returns:
            Configured ADK Agent instance
        """
        if config is None:
            config = AgentConfig(
                name="quality_agent",
                tool_categories=[ToolCategory.ANALYSIS, ToolCategory.MONITORING],
                tool_names=[
                    "code_analyzer",
                    "linter",
                    "security_scanner",
                    "autofix",
                ],  # Will be mapped
            )

        tools = self._get_tools_for_config(config)

        system_instruction = self._build_system_instruction(
            role=AgentRole.QUALITY,
            config=config,
            tools=tools,
            specific_instructions="""
            You are a Quality Agent specialized in code review and improvement.

            Your primary responsibilities:
            - Review code for quality, security, and maintainability
            - Apply automated fixes and improvements
            - Ensure coding standards and best practices are followed
            - Monitor system health and performance

            Always ensure:
            - Code meets established quality standards
            - Security vulnerabilities are identified and fixed
            - Performance issues are addressed
            - Documentation is accurate and up-to-date
            """,
        )

        agent = self._create_adk_agent(
            name=config.name,
            model=config.model.value,
            description="Agent for code quality and review",
            system_instruction=system_instruction,
            tools=tools,
            config=config,
        )

        self.created_agents[config.name] = agent
        logger.info(f"Created quality agent: {config.name}")
        return agent

    def create_contract_validation_agent(
        self, config: AgentConfig | None = None
    ) -> "Agent":
        """
        Create a contract validation agent for graph database validation.

        Args:
            config: Optional configuration override

        Returns:
            Configured ADK Agent instance
        """
        if config is None:
            config = AgentConfig(
                name="contract_validation_agent",
                tool_categories=[ToolCategory.ANALYSIS, ToolCategory.GRAPH],
                tool_names=[
                    "graph_operations",
                    "gcp_operations",
                    "terraform_operations",
                ],
                model=ModelType.GEMINI_2_0_FLASH,
                safety_level=SafetyLevel.STRICT,  # Use strict safety for validation
            )

        # Get tools for contract validation
        tools = self._get_tools_for_config(config)

        # Build system instruction with Constitutional AI for validation
        system_instruction = self._build_system_instruction(
            role=AgentRole.ANALYSIS,
            config=config,
            tools=tools,
            specific_instructions="""
            You are a Contract Validation Agent specialized in graph database validation.

            Your core responsibility is performing "tick-and-tie" validation across the
            entire graph database to ensure system integrity, contract completeness, and
            dependency satisfaction.

            Core Capabilities:
            - Validate ADR-System-GCP relationship integrity
            - Detect and report circular dependencies
            - Verify communication contract completeness
            - Validate SLA requirements for realism and measurability
            - Check archetype template consistency
            - Ensure all critical dependencies are satisfied
            - Validate protocol compatibility between node types

            Constitutional AI Principles:
            - Ensure all contracts are completely specified
            - Validate dependencies are satisfied and non-circular
            - Verify SLA requirements are realistic and measurable
            - Check communication protocols are consistent
            - Ensure archetype templates match node specifications
            - Validate security and compliance requirements
            - Preserve system integrity through rigorous validation

            Always provide detailed validation reports with specific issues,
            fix suggestions, and severity classifications.
            """,
        )

        # Create the agent
        agent = self._create_agent_instance(
            config=config,
            system_instruction=system_instruction,
            tools=tools,
        )

        # Register and return
        self.created_agents[config.name] = agent
        logger.info(f"✅ Created contract validation agent: {config.name}")

        return agent

    def create_solve_team(
        self,
        team_config: dict[str, AgentConfig] | None = None,
    ) -> dict[str, "Agent"]:
        """
        Create a complete SOLVE team with all agent types.

        Args:
            team_config: Optional per-agent configuration overrides

        Returns:
            Dictionary of agent_name -> Agent instances
        """
        if team_config is None:
            team_config = {}

        team = {}

        # Create each agent type
        agent_creators = {
            "structure": self.create_structure_agent,
            "interface": self.create_interface_agent,
            "logic": self.create_logic_agent,
            "testing": self.create_testing_agent,
            "quality": self.create_quality_agent,
            "contract_validation": self.create_contract_validation_agent,
        }

        for agent_type, creator in agent_creators.items():
            config = team_config.get(agent_type)
            try:
                agent = creator(config)
                team[agent_type] = agent
            except Exception as e:
                logger.error(f"Failed to create {agent_type} agent: {e}")
                raise

        logger.info(f"Created SOLVE team with {len(team)} agents")
        return team

    def discover_agents(self) -> list[dict[str, Any]]:
        """
        Discover all available agent types and their capabilities.

        Returns:
            List of agent metadata dictionaries
        """
        agents = []

        # Define agent types with their metadata
        agent_types: dict[str, dict[str, Any]] = {
            "structure": {
                "name": "Structure Agent",
                "role": AgentRole.STRUCTURE,
                "description": "Creates project scaffolding and directory structures",
                "capabilities": [
                    "Directory creation",
                    "File scaffolding",
                    "Git initialization",
                    "Configuration setup",
                ],
                "primary_tools": [ToolCategory.FILESYSTEM, ToolCategory.GIT],
            },
            "interface": {
                "name": "Interface Agent",
                "role": AgentRole.INTERFACE,
                "description": "Designs APIs and system contracts",
                "capabilities": [
                    "API design",
                    "Interface documentation",
                    "Schema validation",
                    "Contract definition",
                ],
                "primary_tools": [ToolCategory.ANALYSIS, ToolCategory.DOCUMENTATION],
            },
            "logic": {
                "name": "Logic Agent",
                "role": AgentRole.LOGIC,
                "description": "Implements business logic and core functionality",
                "capabilities": [
                    "Code implementation",
                    "Algorithm development",
                    "Business logic",
                    "Error handling",
                ],
                "primary_tools": [ToolCategory.FILESYSTEM, ToolCategory.TESTING],
            },
            "testing": {
                "name": "Testing Agent",
                "role": AgentRole.TESTING,
                "description": "Creates and runs comprehensive tests",
                "capabilities": [
                    "Test creation",
                    "Coverage analysis",
                    "Test execution",
                    "Quality validation",
                ],
                "primary_tools": [ToolCategory.TESTING, ToolCategory.ANALYSIS],
            },
            "quality": {
                "name": "Quality Agent",
                "role": AgentRole.QUALITY,
                "description": "Ensures code quality and security",
                "capabilities": [
                    "Code review",
                    "Security scanning",
                    "Performance analysis",
                    "Automated fixes",
                ],
                "primary_tools": [ToolCategory.ANALYSIS, ToolCategory.MONITORING],
            },
            "contract_validation": {
                "name": "Contract Validation Agent",
                "role": AgentRole.ANALYSIS,
                "description": "Performs tick-and-tie validation across graph database contracts",
                "capabilities": [
                    "ADR-System-GCP relationship validation",
                    "Dependency graph cycle detection",
                    "Communication contract verification",
                    "SLA requirement validation",
                    "Archetype template consistency checking",
                    "System completeness validation",
                    "Critical path dependency analysis",
                ],
                "primary_tools": [ToolCategory.ANALYSIS, ToolCategory.GRAPH],
            },
        }

        for agent_id, metadata in agent_types.items():
            agents.append(
                {
                    "id": agent_id,
                    "name": metadata["name"],
                    "role": metadata["role"].value,
                    "description": metadata["description"],
                    "capabilities": metadata["capabilities"],
                    "primary_tools": [cat.value for cat in metadata["primary_tools"]],
                    "available_tools": self.tool_registry.list_tools(
                        category=(
                            metadata["primary_tools"][0]
                            if metadata["primary_tools"]
                            else None
                        ),
                    ),
                    "factory_method": f"create_{agent_id}_agent",
                },
            )

        return agents

    def get_agent_by_name(self, name: str) -> Optional["Agent"]:
        """Get a previously created agent by name"""
        return self.created_agents.get(name)

    def list_created_agents(self) -> list[str]:
        """List names of all created agents"""
        return list(self.created_agents.keys())

    def _get_tools_for_config(self, config: AgentConfig) -> list[Any]:
        """Get tools based on configuration"""
        tools = []

        # Add tools by category
        if config.tool_categories:
            for category in config.tool_categories:
                category_tools = self.tool_registry.get_tools_by_category(category)
                tools.extend(category_tools)

        # Add specific tools by name
        if config.tool_names:
            for requested_name in config.tool_names:
                # Map the requested name to actual registry name
                actual_name = TOOL_NAME_MAPPING.get(requested_name, requested_name)
                tool = self.tool_registry.get_tool(actual_name)
                if tool:
                    tools.append(tool)
                    if requested_name != actual_name:
                        logger.debug(
                            f"Mapped tool '{requested_name}' to '{actual_name}'"
                        )
                else:
                    logger.warning(
                        f"Tool '{requested_name}' (mapped to '{actual_name}') "
                        f"not found in registry",
                    )

        # Add custom tools
        if config.custom_tools:
            tools.extend(config.custom_tools)

        # Remove duplicates while preserving order
        unique_tools = []
        seen = set()
        for tool in tools:
            tool_id = id(tool)
            if tool_id not in seen:
                seen.add(tool_id)
                unique_tools.append(tool)

        return unique_tools

    def _load_relevant_lessons(
        self, role: AgentRole, phase: str | None = None
    ) -> list[Any]:
        """Load relevant lessons for the agent based on role and phase.

        Args:
            role: Agent role
            phase: Current phase if provided

        Returns:
            List of relevant lessons
        """
        try:
            import asyncio

            # Map agent role to phase for lesson filtering
            role_to_phase_map = {
                AgentRole.STRUCTURE: "S",  # Scaffold phase
                AgentRole.INTERFACE: "O",  # Outline phase
                AgentRole.LOGIC: "L",  # Logic phase
                AgentRole.TESTING: "V",  # Verify phase
                AgentRole.QUALITY: "E",  # Enhance phase
            }

            # Determine phase from role if not provided
            if phase is None:
                phase = role_to_phase_map.get(role)

            # Load lessons from the last 30 days
            lessons = asyncio.run(
                self.lesson_capture.load_historical_lessons(phase=phase, days_back=30),
            )

            # Limit to top 10 most recent lessons
            lessons = lessons[:10]

            logger.info(
                f"Loaded {len(lessons)} relevant lessons for {role.value} agent"
            )
            return lessons

        except Exception as e:
            logger.warning(f"Failed to load lessons: {e}")
            return []

    def _build_system_instruction(
        self,
        role: AgentRole,
        config: AgentConfig,
        tools: list[Any],
        specific_instructions: str,
    ) -> str:
        """Build system instruction with Constitutional AI and lesson context"""

        # Load relevant lessons for this agent
        lessons = self._load_relevant_lessons(role)

        # Format lessons for inclusion in prompt
        lessons_text = ""
        if lessons:
            lessons_text = "\n\nPREVIOUS LESSONS LEARNED:\n"
            for i, lesson in enumerate(lessons[:5], 1):  # Include top 5 lessons
                lessons_text += f"""
{i}. Issue: {lesson.issue}
   Resolution: {lesson.resolution}
   Prevention: {lesson.prevention}
   Phase: {lesson.phase}
"""

        if config.constitutional_ai:
            # Add lessons as constitutional constraints
            if lessons:
                self.constitutional_ai.add_lesson_constraints(lessons)
            # Use Constitutional AI for enhanced safety
            base_instruction = self.constitutional_ai.build_system_instruction(
                role=role,
                tools=tools,
                safety_level=config.safety_level.value,
                working_directory=config.working_directory or self.working_directory,
            )
        else:
            # Basic instruction without Constitutional AI
            base_instruction = f"""
            You are a {role.value} in the SOLVE methodology.

            Available tools: {[getattr(tool, "name", tool.__class__.__name__) for tool in tools]}
            Working directory: {config.working_directory or self.working_directory}
            """

        # Combine with specific instructions and lessons
        full_instruction = f"""
        {base_instruction}

        {specific_instructions}
        {lessons_text}

        Operation Guidelines:
        - Always use available tools to accomplish tasks
        - Work within the specified working directory
        - Follow safety guidelines for all operations
        - Provide clear, actionable results
        - Validate your work before completion
        - Learn from previous lessons to avoid past mistakes
        """

        return full_instruction

    def _create_adk_agent(
        self,
        name: str,
        model: str,
        description: str,
        system_instruction: str,
        tools: list[Any],
        config: AgentConfig,
    ) -> "Agent":
        """Create an ADK agent instance"""
        try:
            from google.adk.agents import LlmAgent
            from google.genai import types

            # Build safety settings based on config
            safety_settings = self._build_safety_settings(config.safety_level)

            # Create generate content config
            generate_config = types.GenerateContentConfig(
                temperature=config.temperature,
                top_p=config.top_p,
                max_output_tokens=config.max_tokens,
                safety_settings=safety_settings,
            )

            # Convert tools to ADK format
            adk_tools = self._convert_tools_to_adk_format(tools)

            # Create ADK agent
            agent = LlmAgent(
                name=name,
                model=model,
                description=description,
                instruction=system_instruction,
                tools=adk_tools,
                generate_content_config=generate_config,
            )

            # Add monitoring if enabled
            if config.enable_monitoring:
                agent = self._add_monitoring_to_agent(agent, config)

            return agent

        except ImportError as e:
            logger.error(f"ADK import failed: {e}")
            raise RuntimeError(f"Google ADK not available: {e}") from e
        except Exception as e:
            logger.error(f"Agent creation failed: {e}")
            raise RuntimeError(f"Agent creation failed: {e}") from e

    def _build_safety_settings(self, safety_level: SafetyLevel) -> list[Any]:
        """Build safety settings based on safety level"""
        from google.genai import types

        # Define safety thresholds based on level
        if safety_level == SafetyLevel.STRICT:
            threshold = types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
        elif safety_level == SafetyLevel.MODERATE:
            threshold = types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
        else:  # PERMISSIVE
            threshold = types.HarmBlockThreshold.BLOCK_ONLY_HIGH

        return [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=threshold,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=threshold,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=threshold,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=threshold,
            ),
        ]

    def _convert_tools_to_adk_format(self, tools: list[Any]) -> list[Any]:
        """Convert tools to ADK format"""
        adk_tools = []

        for tool in tools:
            try:
                # Tools should already be ADK compatible from registry
                # This is a placeholder for any conversion logic needed
                adk_tools.append(tool)
            except Exception as e:
                logger.warning(f"Failed to convert tool {tool}: {e}")

        return adk_tools

    def _add_monitoring_to_agent(self, agent: "Agent", config: AgentConfig) -> "Agent":
        """Add monitoring capabilities to agent"""
        # This is a placeholder for monitoring integration
        # In a real implementation, this would wrap the agent with monitoring
        logger.debug(f"Monitoring enabled for agent: {agent.name}")
        return agent


# Convenience functions for common operations
def create_structure_agent(config: AgentConfig | None = None) -> "Agent":
    """Create a structure agent with default configuration"""
    factory = AgentFactory()
    return factory.create_structure_agent(config)


def create_interface_agent(config: AgentConfig | None = None) -> "Agent":
    """Create an interface agent with default configuration"""
    factory = AgentFactory()
    return factory.create_interface_agent(config)


def create_logic_agent(config: AgentConfig | None = None) -> "Agent":
    """Create a logic agent with default configuration"""
    factory = AgentFactory()
    return factory.create_logic_agent(config)


def create_testing_agent(config: AgentConfig | None = None) -> "Agent":
    """Create a testing agent with default configuration"""
    factory = AgentFactory()
    return factory.create_testing_agent(config)


def create_quality_agent(config: AgentConfig | None = None) -> "Agent":
    """Create a quality agent with default configuration"""
    factory = AgentFactory()
    return factory.create_quality_agent(config)


def create_contract_validation_agent(config: AgentConfig | None = None) -> "Agent":
    """Create a contract validation agent with default configuration"""
    factory = AgentFactory()
    return factory.create_contract_validation_agent(config)


def create_solve_team(
    team_config: dict[str, AgentConfig] | None = None,
) -> dict[str, "Agent"]:
    """Create a complete SOLVE team with all agent types"""
    factory = AgentFactory()
    return factory.create_solve_team(team_config)


def discover_available_agents() -> list[dict[str, Any]]:
    """Discover all available agent types and capabilities"""
    factory = AgentFactory()
    return factory.discover_agents()


# Example usage and testing
if __name__ == "__main__":
    # Example of creating agents with different configurations

    # Create a structure agent with custom configuration
    structure_config = AgentConfig(
        name="my_structure_agent",
        model=ModelType.GEMINI_2_0_FLASH,
        safety_level=SafetyLevel.MODERATE,
        tool_categories=[ToolCategory.FILESYSTEM, ToolCategory.GIT],
        temperature=0.5,
        max_tokens=4096,
    )

    structure_agent = create_structure_agent(structure_config)

    # Create a complete SOLVE team
    team = create_solve_team()

    # Discover available agents
    available = discover_available_agents()
    for _agent_info in available:
        pass
