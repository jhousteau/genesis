"""
Specialist Worker Agents for SOLVE Methodology

These agents perform specific, focused tasks within each SOLVE phase.
They report to phase executors and have their work validated by phase validators.

Based on:
- docs/SOLVE_MULTI_AGENT_ARCHITECTURE.md (Layer 3 specialists)
- docs/best-practices/4-adk-agent-patterns.md (Focused agents)
- docs/best-practices/6-tool-architecture.md (Tool integration)
"""

import logging
from typing import Any

from solve.agents.base_agent import RealADKAgent
from solve.models import AgentTask, Goal, Result, TaskStatus
from solve.prompts.constitutional_template import AgentRole
from solve.tools.git_operations import GitTool

logger = logging.getLogger(__name__)


class BaseSpecialistWorker(RealADKAgent):
    """Base class for specialist workers with narrow focus."""

    def __init__(self, specialty: str, **kwargs: Any) -> None:
        """Initialize specialist worker."""
        self.specialty = specialty
        # Specialists have focused capabilities
        kwargs["capabilities"] = [f"Specialized in {specialty}"] + kwargs.get(
            "capabilities", []
        )
        super().__init__(**kwargs)

    async def execute_specialist_task(self, task: dict[str, Any]) -> Result:
        """
        Execute a specific specialist task.

        Args:
            task: Task details from executor

        Returns:
            Execution result
        """
        # Create focused goal for this specialist task
        specialist_goal = Goal(
            description=task.get("description", f"Execute {self.specialty} task"),
            context={
                "task_details": task,
                "specialty": self.specialty,
                "agent_type": "specialist",
            },
            constraints=task.get("constraints", []),
            success_criteria=task.get("success_criteria", []),
        )

        # Execute via base agent
        agent_task = AgentTask(
            goal=specialist_goal,
            assigned_agent=self.name,
            status=TaskStatus.PENDING,
        )

        return await self.execute(agent_task)


# =============================================================================
# SCAFFOLD PHASE SPECIALISTS
# =============================================================================


class DirectoryCreator(BaseSpecialistWorker):
    """Creates directory structures for projects."""

    def __init__(self) -> None:
        super().__init__(
            specialty="directory creation",
            name="directory_creator",
            role=AgentRole.STRUCTURE,
            description="Specialist in creating project directory structures",
            capabilities=[
                "Create nested directory hierarchies",
                "Set appropriate permissions",
                "Follow project conventions",
                "Create placeholder files",
            ],
        )

    async def create_structure(self, structure_spec: dict[str, Any]) -> Result:
        """Create directory structure based on specification."""
        return await self.execute_specialist_task(
            {
                "description": "Create project directory structure",
                "structure_spec": structure_spec,
                "constraints": [
                    "Follow Python package conventions",
                    "Create __init__.py files where needed",
                    "Use appropriate directory names",
                ],
                "success_criteria": [
                    "All directories created",
                    "Proper permissions set",
                    "Structure matches specification",
                ],
            },
        )


class ConfigGenerator(BaseSpecialistWorker):
    """Generates configuration files for projects."""

    def __init__(self) -> None:
        super().__init__(
            specialty="configuration generation",
            name="config_generator",
            role=AgentRole.STRUCTURE,
            description="Specialist in generating project configuration files",
            capabilities=[
                "Create pyproject.toml files",
                "Generate .gitignore files",
                "Create environment configs",
                "Set up tool configurations",
            ],
        )

    async def generate_configs(self, project_info: dict[str, Any]) -> Result:
        """Generate configuration files for the project."""
        return await self.execute_specialist_task(
            {
                "description": "Generate project configuration files",
                "project_info": project_info,
                "constraints": [
                    "Use modern Python packaging standards",
                    "Include essential development tools",
                    "Follow best practices",
                ],
                "success_criteria": [
                    "pyproject.toml created",
                    ".gitignore configured",
                    "Tool configs generated",
                ],
            },
        )


class GitInitializer(BaseSpecialistWorker):
    """Initializes Git repositories and sets up version control."""

    def __init__(self) -> None:
        super().__init__(
            specialty="Git initialization",
            name="git_initializer",
            role=AgentRole.STRUCTURE,
            description="Specialist in Git repository setup",
            capabilities=[
                "Initialize Git repositories",
                "Configure Git settings",
                "Create initial commit",
                "Set up branch protection",
            ],
            tools=[GitTool()],
        )

    async def initialize_repo(self, repo_config: dict[str, Any]) -> Result:
        """Initialize Git repository with configuration."""
        return await self.execute_specialist_task(
            {
                "description": "Initialize Git repository",
                "repo_config": repo_config,
                "constraints": [
                    "Use conventional commit format",
                    "Set up main branch as default",
                    "Configure useful Git aliases",
                ],
                "success_criteria": [
                    "Git repository initialized",
                    "Initial commit created",
                    "Git configured properly",
                ],
            },
        )


# =============================================================================
# OUTLINE PHASE SPECIALISTS
# =============================================================================


class ApiDesigner(BaseSpecialistWorker):
    """Designs API interfaces and endpoints."""

    def __init__(self) -> None:
        super().__init__(
            specialty="API design",
            name="api_designer",
            role=AgentRole.INTERFACE,
            description="Specialist in API interface design",
            capabilities=[
                "Design RESTful APIs",
                "Create endpoint specifications",
                "Define request/response formats",
                "Document API contracts",
            ],
        )

    async def design_api(self, api_requirements: dict[str, Any]) -> Result:
        """Design API based on requirements."""
        return await self.execute_specialist_task(
            {
                "description": "Design API interfaces",
                "api_requirements": api_requirements,
                "constraints": [
                    "Follow REST principles",
                    "Use consistent naming",
                    "Include error handling",
                ],
                "success_criteria": [
                    "Endpoints defined",
                    "Request/response formats specified",
                    "Error cases documented",
                ],
            },
        )


class SchemaCreator(BaseSpecialistWorker):
    """Creates data schemas and models."""

    def __init__(self) -> None:
        super().__init__(
            specialty="schema creation",
            name="schema_creator",
            role=AgentRole.INTERFACE,
            description="Specialist in data schema design",
            capabilities=[
                "Create Pydantic models",
                "Design database schemas",
                "Define validation rules",
                "Generate TypeScript types",
            ],
        )

    async def create_schemas(self, data_requirements: dict[str, Any]) -> Result:
        """Create data schemas based on requirements."""
        return await self.execute_specialist_task(
            {
                "description": "Create data schemas and models",
                "data_requirements": data_requirements,
                "constraints": [
                    "Use type hints throughout",
                    "Include validation rules",
                    "Make schemas serializable",
                ],
                "success_criteria": [
                    "All models defined",
                    "Validation rules included",
                    "Documentation complete",
                ],
            },
        )


class ContractWriter(BaseSpecialistWorker):
    """Writes interface contracts and documentation."""

    def __init__(self) -> None:
        super().__init__(
            specialty="contract documentation",
            name="contract_writer",
            role=AgentRole.INTERFACE,
            description="Specialist in interface contract documentation",
            capabilities=[
                "Write interface contracts",
                "Document preconditions/postconditions",
                "Create usage examples",
                "Define SLAs",
            ],
        )

    async def write_contracts(self, interface_specs: dict[str, Any]) -> Result:
        """Write contracts for interfaces."""
        return await self.execute_specialist_task(
            {
                "description": "Document interface contracts",
                "interface_specs": interface_specs,
                "constraints": [
                    "Be precise and unambiguous",
                    "Include all edge cases",
                    "Provide clear examples",
                ],
                "success_criteria": [
                    "Contracts documented",
                    "Examples provided",
                    "Edge cases covered",
                ],
            },
        )


# =============================================================================
# LOGIC PHASE SPECIALISTS
# =============================================================================


class CodeImplementer(BaseSpecialistWorker):
    """Implements business logic and core functionality."""

    def __init__(self) -> None:
        super().__init__(
            specialty="code implementation",
            name="code_implementer",
            role=AgentRole.LOGIC,
            description="Specialist in implementing business logic",
            capabilities=[
                "Write Python functions",
                "Implement algorithms",
                "Create classes and modules",
                "Follow SOLID principles",
            ],
        )

    async def implement_logic(self, implementation_spec: dict[str, Any]) -> Result:
        """Implement business logic based on specification."""
        return await self.execute_specialist_task(
            {
                "description": "Implement business logic",
                "implementation_spec": implementation_spec,
                "constraints": [
                    "Follow existing code style",
                    "Write clean, readable code",
                    "Include error handling",
                ],
                "success_criteria": [
                    "Functions implemented",
                    "Logic works correctly",
                    "Code is maintainable",
                ],
            },
        )


class TestScaffolder(BaseSpecialistWorker):
    """Creates test structure alongside implementation."""

    def __init__(self) -> None:
        super().__init__(
            specialty="test scaffolding",
            name="test_scaffolder",
            role=AgentRole.TESTING,
            description="Specialist in creating test structures",
            capabilities=[
                "Create pytest test files",
                "Set up test fixtures",
                "Generate test cases",
                "Configure test coverage",
            ],
        )

    async def scaffold_tests(self, code_structure: dict[str, Any]) -> Result:
        """Create test structure for implemented code."""
        return await self.execute_specialist_task(
            {
                "description": "Create test scaffolding",
                "code_structure": code_structure,
                "constraints": [
                    "Mirror source code structure",
                    "Use pytest conventions",
                    "Include edge case tests",
                ],
                "success_criteria": [
                    "Test files created",
                    "Fixtures defined",
                    "Basic tests scaffolded",
                ],
            },
        )


class ErrorHandler(BaseSpecialistWorker):
    """Implements error handling and recovery logic."""

    def __init__(self) -> None:
        super().__init__(
            specialty="error handling",
            name="error_handler",
            role=AgentRole.LOGIC,
            description="Specialist in error handling implementation",
            capabilities=[
                "Design error hierarchies",
                "Implement exception handling",
                "Create recovery strategies",
                "Add logging and monitoring",
            ],
        )

    async def implement_error_handling(self, error_spec: dict[str, Any]) -> Result:
        """Implement error handling based on specification."""
        return await self.execute_specialist_task(
            {
                "description": "Implement error handling",
                "error_spec": error_spec,
                "constraints": [
                    "Use specific exception types",
                    "Include helpful error messages",
                    "Enable graceful degradation",
                ],
                "success_criteria": [
                    "Error classes defined",
                    "Exception handling added",
                    "Recovery logic implemented",
                ],
            },
        )


# =============================================================================
# VERIFY PHASE SPECIALISTS
# =============================================================================


class RequirementAuditor(BaseSpecialistWorker):
    """Audits implementation against requirements."""

    def __init__(self) -> None:
        super().__init__(
            specialty="requirement auditing",
            name="requirement_auditor",
            role=AgentRole.TESTING,
            description="Specialist in requirement compliance auditing",
            capabilities=[
                "Check ADR compliance",
                "Verify requirement coverage",
                "Identify missing features",
                "Create audit reports",
            ],
        )

    async def audit_requirements(self, audit_spec: dict[str, Any]) -> Result:
        """Audit implementation against requirements."""
        return await self.execute_specialist_task(
            {
                "description": "Audit requirement compliance",
                "audit_spec": audit_spec,
                "constraints": [
                    "Be thorough and systematic",
                    "Document all findings",
                    "Prioritize critical issues",
                ],
                "success_criteria": [
                    "All requirements checked",
                    "Compliance documented",
                    "Issues identified",
                ],
            },
        )


class TestRunner(BaseSpecialistWorker):
    """Executes test suites and reports results."""

    def __init__(self) -> None:
        super().__init__(
            specialty="test execution",
            name="test_runner",
            role=AgentRole.TESTING,
            description="Specialist in running test suites",
            capabilities=[
                "Execute pytest suites",
                "Run integration tests",
                "Generate test reports",
                "Identify flaky tests",
            ],
        )

    async def run_tests(self, test_config: dict[str, Any]) -> Result:
        """Run test suite based on configuration."""
        return await self.execute_specialist_task(
            {
                "description": "Execute test suite",
                "test_config": test_config,
                "constraints": [
                    "Run all relevant tests",
                    "Capture detailed output",
                    "Report failures clearly",
                ],
                "success_criteria": [
                    "Tests executed",
                    "Results reported",
                    "Coverage measured",
                ],
            },
        )


class CoverageAnalyzer(BaseSpecialistWorker):
    """Analyzes test coverage and identifies gaps."""

    def __init__(self) -> None:
        super().__init__(
            specialty="coverage analysis",
            name="coverage_analyzer",
            role=AgentRole.TESTING,
            description="Specialist in test coverage analysis",
            capabilities=[
                "Measure code coverage",
                "Identify uncovered code",
                "Suggest additional tests",
                "Generate coverage reports",
            ],
        )

    async def analyze_coverage(self, coverage_data: dict[str, Any]) -> Result:
        """Analyze test coverage data."""
        return await self.execute_specialist_task(
            {
                "description": "Analyze test coverage",
                "coverage_data": coverage_data,
                "constraints": [
                    "Focus on critical paths",
                    "Identify coverage gaps",
                    "Suggest improvements",
                ],
                "success_criteria": [
                    "Coverage analyzed",
                    "Gaps identified",
                    "Recommendations made",
                ],
            },
        )


# =============================================================================
# ENHANCE PHASE SPECIALISTS
# =============================================================================


class LessonExtractor(BaseSpecialistWorker):
    """Extracts lessons learned from development process."""

    def __init__(self) -> None:
        super().__init__(
            specialty="lesson extraction",
            name="lesson_extractor",
            role=AgentRole.QUALITY,
            description="Specialist in extracting lessons learned",
            capabilities=[
                "Identify key learnings",
                "Document best practices",
                "Capture pain points",
                "Create knowledge artifacts",
            ],
        )

    async def extract_lessons(self, development_history: dict[str, Any]) -> Result:
        """Extract lessons from development history."""
        return await self.execute_specialist_task(
            {
                "description": "Extract lessons learned",
                "development_history": development_history,
                "constraints": [
                    "Focus on actionable insights",
                    "Be specific and concrete",
                    "Include both successes and failures",
                ],
                "success_criteria": [
                    "Lessons identified",
                    "Insights documented",
                    "Recommendations made",
                ],
            },
        )


class PatternRecognizer(BaseSpecialistWorker):
    """Recognizes patterns in code and development process."""

    def __init__(self) -> None:
        super().__init__(
            specialty="pattern recognition",
            name="pattern_recognizer",
            role=AgentRole.QUALITY,
            description="Specialist in recognizing development patterns",
            capabilities=[
                "Identify recurring issues",
                "Spot design patterns",
                "Find antipatterns",
                "Suggest pattern applications",
            ],
        )

    async def recognize_patterns(self, codebase_analysis: dict[str, Any]) -> Result:
        """Recognize patterns in codebase and process."""
        return await self.execute_specialist_task(
            {
                "description": "Recognize development patterns",
                "codebase_analysis": codebase_analysis,
                "constraints": [
                    "Focus on significant patterns",
                    "Consider both code and process",
                    "Provide actionable insights",
                ],
                "success_criteria": [
                    "Patterns identified",
                    "Antipatterns found",
                    "Improvements suggested",
                ],
            },
        )


class ImprovementSuggester(BaseSpecialistWorker):
    """Suggests improvements based on analysis."""

    def __init__(self) -> None:
        super().__init__(
            specialty="improvement suggestions",
            name="improvement_suggester",
            role=AgentRole.QUALITY,
            description="Specialist in suggesting improvements",
            capabilities=[
                "Propose optimizations",
                "Suggest refactorings",
                "Recommend tool adoption",
                "Create improvement roadmap",
            ],
        )

    async def suggest_improvements(self, analysis_results: dict[str, Any]) -> Result:
        """Suggest improvements based on analysis."""
        return await self.execute_specialist_task(
            {
                "description": "Suggest improvements",
                "analysis_results": analysis_results,
                "constraints": [
                    "Prioritize high-impact changes",
                    "Consider implementation effort",
                    "Maintain backward compatibility",
                ],
                "success_criteria": [
                    "Improvements identified",
                    "Roadmap created",
                    "ROI estimated",
                ],
            },
        )


# =============================================================================
# SPECIALIST REGISTRY
# =============================================================================


def get_specialist_registry() -> dict[str, Any]:
    """Get registry of all specialist workers."""
    return {
        # Scaffold specialists
        "DirectoryCreator": DirectoryCreator,
        "ConfigGenerator": ConfigGenerator,
        "GitInitializer": GitInitializer,
        # Outline specialists
        "ApiDesigner": ApiDesigner,
        "SchemaCreator": SchemaCreator,
        "ContractWriter": ContractWriter,
        # Logic specialists
        "CodeImplementer": CodeImplementer,
        "TestScaffolder": TestScaffolder,
        "ErrorHandler": ErrorHandler,
        # Verify specialists
        "RequirementAuditor": RequirementAuditor,
        "TestRunner": TestRunner,
        "CoverageAnalyzer": CoverageAnalyzer,
        # Enhance specialists
        "LessonExtractor": LessonExtractor,
        "PatternRecognizer": PatternRecognizer,
        "ImprovementSuggester": ImprovementSuggester,
    }


def create_specialist(specialist_name: str) -> BaseSpecialistWorker:
    """
    Create a specialist worker by name.

    Args:
        specialist_name: Name of the specialist

    Returns:
        Specialist worker instance

    Raises:
        ValueError: If specialist is unknown
    """
    registry = get_specialist_registry()
    specialist_class = registry.get(specialist_name)

    if not specialist_class:
        raise ValueError(f"Unknown specialist: {specialist_name}")

    return specialist_class()  # type: ignore[no-any-return]


# Export all specialist classes
__all__ = [
    "BaseSpecialistWorker",
    # Scaffold
    "DirectoryCreator",
    "ConfigGenerator",
    "GitInitializer",
    # Outline
    "ApiDesigner",
    "SchemaCreator",
    "ContractWriter",
    # Logic
    "CodeImplementer",
    "TestScaffolder",
    "ErrorHandler",
    # Verify
    "RequirementAuditor",
    "TestRunner",
    "CoverageAnalyzer",
    # Enhance
    "LessonExtractor",
    "PatternRecognizer",
    "ImprovementSuggester",
    # Functions
    "get_specialist_registry",
    "create_specialist",
]
