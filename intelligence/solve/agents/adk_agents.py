"""
Simple ADK Agent Definitions for SOLVE Methodology

Creates ADK-compliant agents following official patterns from:
- adk-python/contributing/samples/hello_world/agent.py
- adk-samples/python/agents/academic-research/agent.py
- adk-samples/python/agents/customer-service/agent.py

Each agent is a simple Agent instance with Constitutional AI principles embedded
in their instructions and access to real ADK tools.

NO CLASSES - Only direct function-style Agent definitions following hello_world pattern.
"""

import logging
from typing import Any

from solve.prompts.constitutional_template import (AgentRole, PromptContext,
                                                   build_adk_instruction)

# Set up logging for this module
logger = logging.getLogger(__name__)


def _get_tools_for_agent(agent_role: AgentRole) -> list[Any]:
    """Get ADK-compliant tools for specific agent role"""
    tools = []

    try:
        # Import ADK tools directly to ensure compatibility
        from solve.tools.code_analysis_adk import CodeAnalysisADKTool
        from solve.tools.filesystem_adk import FileSystemTool
        from solve.tools.git_operations_adk import (GitAddTool, GitCommitTool,
                                                    GitStatusTool)

        # Base tools that all agents need
        filesystem_tool = FileSystemTool()

        if agent_role == AgentRole.STRUCTURE:
            tools.extend(
                [
                    filesystem_tool,
                    GitStatusTool(),
                    GitAddTool(),
                    GitCommitTool(),
                ],
            )

        elif (
            agent_role == AgentRole.INTERFACE
            or agent_role == AgentRole.LOGIC
            or agent_role == AgentRole.TESTING
            or agent_role == AgentRole.QUALITY
        ):
            tools.extend(
                [
                    filesystem_tool,
                    CodeAnalysisADKTool(),
                ],
            )

    except ImportError:
        # Fallback to basic tool set if ADK tools not available
        tools = []

    return tools


def _build_constitutional_instruction(agent_role: AgentRole, description: str) -> str:
    """Build constitutional AI instruction for agent"""
    context = PromptContext(
        agent_role=agent_role,
        task_description=description,
        agent_id=f"{agent_role.value}_agent",
        model_name="gemini-2.0-flash",
    )

    return build_adk_instruction(context)


# Import ADK Agent here to avoid import-time dependencies
def _create_adk_agent(name: str, description: str, role: AgentRole) -> Any:
    """Create ADK Agent instance with error handling"""
    try:
        from google.adk import Agent

        # Get tools for this agent role
        tools = _get_tools_for_agent(role)

        # Build constitutional instruction
        instruction = _build_constitutional_instruction(role, description)

        # Create agent following hello_world pattern
        agent = Agent(
            model="gemini-2.0-flash",
            name=name,
            description=description,
            instruction=instruction,
            tools=tools,
        )

        return agent

    except ImportError:
        # Fallback for development without ADK
        return None
    except Exception:
        return None


# ==================== AGENT DEFINITIONS ====================

# Structure Agent - Creates project structures and scaffolding
structure_agent = _create_adk_agent(
    name="structure_agent",
    description="Creates project structures and scaffolding following SOLVE methodology",
    role=AgentRole.STRUCTURE,
)

# Interface Agent - Designs APIs and interfaces
interface_agent = _create_adk_agent(
    name="interface_agent",
    description="Designs clean, well-documented APIs and interfaces",
    role=AgentRole.INTERFACE,
)

# Logic Agent - Implements business logic
logic_agent = _create_adk_agent(
    name="logic_agent",
    description="Implements robust, tested business logic",
    role=AgentRole.LOGIC,
)

# Testing Agent - Creates and runs tests
testing_agent = _create_adk_agent(
    name="testing_agent",
    description="Creates comprehensive test suites and validation",
    role=AgentRole.TESTING,
)

# Quality Agent - Ensures code quality and security
quality_agent = _create_adk_agent(
    name="quality_agent",
    description="Ensures code quality, security, and best practices",
    role=AgentRole.QUALITY,
)


# ==================== AGENT REGISTRY ====================

# Registry of all available agents
SOLVE_AGENTS = {
    "structure": structure_agent,
    "interface": interface_agent,
    "logic": logic_agent,
    "testing": testing_agent,
    "quality": quality_agent,
}

# Filter out None values (agents that failed to create)
SOLVE_AGENTS = {k: v for k, v in SOLVE_AGENTS.items() if v is not None}


def get_agent(agent_name: str) -> Any:
    """Get agent by name"""
    return SOLVE_AGENTS.get(agent_name)


def list_agents() -> list[str]:
    """List all available agent names"""
    return list(SOLVE_AGENTS.keys())


def get_all_agents() -> dict[str, Any]:
    """Get all agents as dictionary"""
    return SOLVE_AGENTS.copy()


# ==================== EXAMPLE USAGE ====================


async def example_usage() -> None:
    """Example of how to use the ADK agents"""

    # List available agents
    for name in list_agents():
        agent = get_agent(name)
        if agent:
            pass

    # Example: Use structure agent
    if structure_agent:
        try:
            from google.adk.runners import InMemoryRunner
            from google.genai import types

            # Create runner
            runner = InMemoryRunner(
                agent=structure_agent, app_name="solve_structure_example"
            )

            # Create session
            session = await runner.session_service.create_session(
                app_name="solve_structure_example",
                user_id="example_user",
            )

            # Create message
            message = types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=(
                            "Create a Python package structure for a web API "
                            "called 'inventory-service'"
                        ),
                    ),
                ],
            )

            # Run agent
            events = []
            async for event in runner.run_async(
                user_id="example_user",
                session_id=session.id,
                new_message=message,
            ):
                events.append(event)

        except Exception as e:
            logger.error(
                "Failed to run structure agent example: %s", str(e), exc_info=True
            )


# ==================== CONSTITUTIONAL AI INTEGRATION ====================


def get_agent_capabilities(agent_name: str) -> dict[str, Any]:
    """Get agent capabilities and constraints"""
    agent = get_agent(agent_name)
    if not agent:
        return {"error": f"Agent '{agent_name}' not found"}

    role_capabilities = {
        "structure": {
            "primary_focus": "Project structure and scaffolding",
            "capabilities": [
                "Create directory hierarchies",
                "Set up configuration files",
                "Initialize version control",
                "Establish project conventions",
            ],
            "constitutional_principles": [
                "Create clean, organized structures",
                "Follow established conventions",
                "Ensure proper file permissions",
                "Validate structure integrity",
            ],
        },
        "interface": {
            "primary_focus": "API design and interface contracts",
            "capabilities": [
                "Define public APIs",
                "Create type definitions",
                "Design data models",
                "Document interfaces",
            ],
            "constitutional_principles": [
                "Design clear, consistent interfaces",
                "Prioritize usability and safety",
                "Ensure backward compatibility",
                "Provide comprehensive documentation",
            ],
        },
        "logic": {
            "primary_focus": "Business logic implementation",
            "capabilities": [
                "Implement core algorithms",
                "Handle error conditions",
                "Integrate with interfaces",
                "Write maintainable code",
            ],
            "constitutional_principles": [
                "Write robust, tested code",
                "Handle edge cases gracefully",
                "Maintain code quality",
                "Preserve existing functionality",
            ],
        },
        "testing": {
            "primary_focus": "Test creation and validation",
            "capabilities": [
                "Write unit tests",
                "Create integration tests",
                "Develop test data",
                "Validate system behavior",
                "Analyze code for testability",
            ],
            "constitutional_principles": [
                "Ensure comprehensive coverage",
                "Test edge cases thoroughly",
                "Validate quality metrics",
                "Maintain test reliability",
            ],
        },
        "quality": {
            "primary_focus": "Code quality and security",
            "capabilities": [
                "Perform code reviews",
                "Check security vulnerabilities",
                "Ensure coding standards",
                "Optimize performance",
            ],
            "constitutional_principles": [
                "Never compromise on quality",
                "Prioritize security always",
                "Maintain consistent standards",
                "Optimize for maintainability",
            ],
        },
    }

    return {
        "agent_name": agent_name,
        "agent_description": agent.description,
        "model": agent.model,
        **role_capabilities.get(agent_name, {}),
    }


def validate_agent_usage(agent_name: str, task_description: str) -> dict[str, Any]:
    """Validate if agent usage aligns with constitutional AI principles"""
    agent = get_agent(agent_name)
    if not agent:
        return {"valid": False, "reason": f"Agent '{agent_name}' not found"}

    # Get capabilities
    capabilities = get_agent_capabilities(agent_name)

    # Simple validation based on task description
    task_lower = task_description.lower()

    # Check if task aligns with agent's focus
    focus_keywords = {
        "structure": ["structure", "scaffold", "setup", "organize", "create directory"],
        "interface": ["interface", "api", "contract", "design", "schema"],
        "logic": ["implement", "logic", "algorithm", "business", "function"],
        "testing": ["test", "verify", "validate", "check", "coverage"],
        "quality": ["quality", "review", "lint", "security", "optimize"],
    }

    agent_keywords = focus_keywords.get(agent_name, [])
    has_relevant_keywords = any(keyword in task_lower for keyword in agent_keywords)

    if not has_relevant_keywords:
        return {
            "valid": False,
            "reason": f"Task doesn't align with {agent_name} agent's focus areas",
            "suggestions": [
                "Consider using a different agent for this task",
                (
                    f"Reframe task to align with {agent_name} capabilities: "
                    f"{capabilities.get('primary_focus', 'N/A')}"
                ),
            ],
        }

    return {
        "valid": True,
        "reason": f"Task aligns with {agent_name} agent capabilities",
        "constitutional_check": "Task respects agent autonomy and role boundaries",
    }


# ==================== INTEGRATION HELPERS ====================


def create_agent_session(agent_name: str, app_name: str | None = None) -> Any:
    """Create a session for an agent"""
    agent = get_agent(agent_name)
    if not agent:
        raise ValueError(f"Agent '{agent_name}' not found")

    try:
        from google.adk.runners import InMemoryRunner

        app_name = app_name or f"solve_{agent_name}"

        runner = InMemoryRunner(agent=agent, app_name=app_name)

        return runner

    except ImportError as err:
        raise RuntimeError("ADK not available - cannot create session") from err


async def run_agent_task(
    agent_name: str, task: str, user_id: str = "solve_user"
) -> dict[str, Any]:
    """Run a task with the specified agent"""
    agent = get_agent(agent_name)
    if not agent:
        raise ValueError(f"Agent '{agent_name}' not found")

    # Validate task
    validation = validate_agent_usage(agent_name, task)
    if not validation["valid"]:
        raise ValueError(f"Task validation failed: {validation['reason']}")

    try:
        from google.genai import types

        # Create runner
        runner = create_agent_session(agent_name)

        # Create session
        session = await runner.session_service.create_session(
            app_name=f"solve_{agent_name}",
            user_id=user_id,
        )

        # Create message
        message = types.Content(role="user", parts=[types.Part.from_text(text=task)])

        # Run agent
        events = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=message,
        ):
            events.append(event)

        return {
            "success": True,
            "agent": agent_name,
            "task": task,
            "events": events,
            "session_id": session.id,
        }

    except Exception as e:
        return {"success": False, "agent": agent_name, "task": task, "error": str(e)}


# ==================== MAIN EXECUTION ====================

if __name__ == "__main__":
    import asyncio

    # Show available agents
    for name in list_agents():
        agent = get_agent(name)
        if agent:
            pass

    # Show capabilities
    for name in list_agents():
        capabilities = get_agent_capabilities(name)

    # Run example if agents are available
    if SOLVE_AGENTS:
        asyncio.run(example_usage())
    else:
        pass
