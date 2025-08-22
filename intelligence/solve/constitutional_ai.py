"""
Constitutional AI System for SOLVE

This module implements a Constitutional AI system based on the 7 core principles
documented in docs/best-practices/12-agentic-transformation-principles.md:

1. Agent Autonomy is Sacred
2. Goals Over Process
3. Intelligence Over Compliance
4. Collaboration Through Communication
5. Emergent Workflows Over Predefined Phases
6. Continuous Learning Over Static Procedures
7. Tools as Capabilities, Not Enforcers

The system provides principle-based decision validation, safety constraints,
and explanation capabilities for agent behavior.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .knowledge_loader import KnowledgeLoader
from .models import Result

logger = logging.getLogger(__name__)


class ConstitutionalPrinciple(Enum):
    """Core constitutional principles for agent behavior."""

    AGENT_AUTONOMY = "agent_autonomy"
    GOALS_OVER_PROCESS = "goals_over_process"
    INTELLIGENCE_OVER_COMPLIANCE = "intelligence_over_compliance"
    COLLABORATION_THROUGH_COMMUNICATION = "collaboration_through_communication"
    EMERGENT_WORKFLOWS = "emergent_workflows"
    CONTINUOUS_LEARNING = "continuous_learning"
    TOOLS_AS_CAPABILITIES = "tools_as_capabilities"


@dataclass
class ConstitutionalDecision:
    """Represents a decision made by an agent with constitutional reasoning."""

    agent_id: str
    decision: str
    reasoning: str
    principles_applied: list[ConstitutionalPrinciple]
    context: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    safety_constraints: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate constitutional decision."""
        if not self.decision:
            raise ValueError("Decision cannot be empty")

        if not self.reasoning:
            raise ValueError("Reasoning cannot be empty")

        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

        logger.debug(
            f"Constitutional decision by {self.agent_id}: {self.decision[:50]}..."
        )


@dataclass
class ConstitutionalConstraint:
    """Represents a safety constraint derived from constitutional principles."""

    name: str
    description: str
    principle: ConstitutionalPrinciple
    severity: str  # "warning", "error", "critical"
    check_function: str  # Name of the validation function

    def __post_init__(self) -> None:
        """Validate constraint."""
        if self.severity not in ["warning", "error", "critical"]:
            raise ValueError(f"Invalid severity: {self.severity}")


@dataclass
class ConstitutionalViolation:
    """Represents a violation of constitutional principles."""

    constraint: ConstitutionalConstraint
    violation_description: str
    suggested_remedy: str
    context: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


class ConstitutionalAI:
    """
    Constitutional AI system for SOLVE agents.

    This class implements principle-based decision validation, safety constraints,
    and explanation capabilities based on the 7 core constitutional principles.
    """

    def __init__(self, knowledge_loader: KnowledgeLoader | None = None):
        """Initialize Constitutional AI system."""
        self.knowledge_loader = knowledge_loader or KnowledgeLoader()
        self.principles = self._load_core_principles()
        self.constraints = self._load_safety_constraints()
        self.decision_history: list[ConstitutionalDecision] = []
        self.violation_history: list[ConstitutionalViolation] = []

        logger.info("Constitutional AI system initialized")

    def _load_core_principles(self) -> dict[ConstitutionalPrinciple, dict[str, Any]]:
        """Load core constitutional principles from knowledge base."""
        principles = {}

        # Load the agentic transformation principles document
        try:
            doc = self.knowledge_loader.load_document(
                "12-agentic-transformation-principles.md"
            )
        except (FileNotFoundError, AttributeError):
            doc = None

        if doc:
            # Extract principle definitions from the document
            principles[ConstitutionalPrinciple.AGENT_AUTONOMY] = {
                "title": "Agent Autonomy is Sacred",
                "description": (
                    "Agents must have the freedom to make intelligent decisions "
                    "based on context and goals"
                ),
                "guidelines": [
                    "Agents choose optimal approaches, not follow prescribed steps",
                    "Decision-making happens at the agent level, not orchestrator level",
                    "Trust in agent intelligence over process compliance",
                    "Enable exploration and experimentation",
                ],
                "anti_patterns": [
                    "Micromanaging agent actions",
                    "Prescriptive step-by-step procedures",
                    "Validation gates that block progress",
                    "Must follow rules that remove judgment",
                ],
            }

            principles[ConstitutionalPrinciple.GOALS_OVER_PROCESS] = {
                "title": "Goals Over Process",
                "description": "Success is measured by outcomes achieved, not steps followed",
                "guidelines": [
                    "Define clear goals and success criteria",
                    "Let agents determine the path",
                    "Measure value delivered, not compliance",
                    "Celebrate creative solutions",
                ],
                "metrics": [
                    "Problem resolution rate",
                    "Code quality achieved",
                    "User satisfaction",
                    "Time to value",
                ],
            }

            principles[ConstitutionalPrinciple.INTELLIGENCE_OVER_COMPLIANCE] = {
                "title": "Intelligence Over Compliance",
                "description": "Trust agents to understand nuance and make thoughtful trade-offs",
                "guidelines": [
                    "Agents interpret principles, not follow rules",
                    "Context drives decisions, not governance",
                    "Explanation over enforcement",
                    "Learning from exceptions",
                ],
            }

            principles[ConstitutionalPrinciple.COLLABORATION_THROUGH_COMMUNICATION] = {
                "title": "Collaboration Through Communication",
                "description": "Agents interact through clear communication, not governance files",
                "patterns": [
                    "Goal articulation",
                    "Context sharing",
                    "Expertise-based delegation",
                    "Peer review",
                ],
            }

            principles[ConstitutionalPrinciple.EMERGENT_WORKFLOWS] = {
                "title": "Emergent Workflows Over Predefined Phases",
                "description": "Allow optimal workflows to emerge based on problem characteristics",
                "guidelines": [
                    "No forced sequential phases",
                    "Natural iteration between concerns",
                    "Concurrent work where beneficial",
                    "Adaptive approaches",
                ],
            }

            principles[ConstitutionalPrinciple.CONTINUOUS_LEARNING] = {
                "title": "Continuous Learning Over Static Procedures",
                "description": "Systems must learn and improve from every interaction",
                "components": [
                    "Capture insights from outcomes",
                    "Share knowledge across agents",
                    "Improve approaches over time",
                    "Question existing patterns",
                ],
            }

            principles[ConstitutionalPrinciple.TOOLS_AS_CAPABILITIES] = {
                "title": "Tools as Capabilities, Not Enforcers",
                "description": (
                    "Tools provide capabilities that agents use intelligently, "
                    "not rules they must follow"
                ),
                "philosophy": [
                    "Tools enable, not restrict",
                    "Available when needed, not phase-locked",
                    "Composable for complex tasks",
                    "Discoverable and extensible",
                ],
            }

        logger.info(f"Loaded {len(principles)} constitutional principles")
        return principles

    def _load_safety_constraints(self) -> list[ConstitutionalConstraint]:
        """Load safety constraints from knowledge base."""
        constraints = []

        # Load agent safety principles
        try:
            safety_doc = self.knowledge_loader.load_document(
                "AGENT_SAFETY_PRINCIPLES.md"
            )
        except (FileNotFoundError, AttributeError):
            safety_doc = None

        if safety_doc:
            # Core safety constraints
            constraints.extend(
                [
                    ConstitutionalConstraint(
                        name="quality_first",
                        description="Agents must prioritize code quality and correctness",
                        principle=ConstitutionalPrinciple.INTELLIGENCE_OVER_COMPLIANCE,
                        severity="error",
                        check_function="validate_code_quality",
                    ),
                    ConstitutionalConstraint(
                        name="no_destructive_actions",
                        description="No destructive actions without explicit permission",
                        principle=ConstitutionalPrinciple.AGENT_AUTONOMY,
                        severity="critical",
                        check_function="validate_destructive_actions",
                    ),
                    ConstitutionalConstraint(
                        name="transparent_reasoning",
                        description=(
                            "All agent decisions must be explainable through reasoning traces"
                        ),
                        principle=ConstitutionalPrinciple.INTELLIGENCE_OVER_COMPLIANCE,
                        severity="warning",
                        check_function="validate_reasoning_transparency",
                    ),
                    ConstitutionalConstraint(
                        name="respect_boundaries",
                        description="Agents must respect project constraints and user preferences",
                        principle=ConstitutionalPrinciple.COLLABORATION_THROUGH_COMMUNICATION,
                        severity="error",
                        check_function="validate_boundary_respect",
                    ),
                    ConstitutionalConstraint(
                        name="learning_focus",
                        description=(
                            "Prioritize learning and improvement over repetitive compliance"
                        ),
                        principle=ConstitutionalPrinciple.CONTINUOUS_LEARNING,
                        severity="warning",
                        check_function="validate_learning_focus",
                    ),
                    ConstitutionalConstraint(
                        name="goal_alignment",
                        description=(
                            "All actions must align with declared goals and success criteria"
                        ),
                        principle=ConstitutionalPrinciple.GOALS_OVER_PROCESS,
                        severity="error",
                        check_function="validate_goal_alignment",
                    ),
                    ConstitutionalConstraint(
                        name="collaborative_spirit",
                        description="Promote collaboration and knowledge sharing",
                        principle=ConstitutionalPrinciple.COLLABORATION_THROUGH_COMMUNICATION,
                        severity="warning",
                        check_function="validate_collaboration",
                    ),
                ],
            )

        logger.info(f"Loaded {len(constraints)} safety constraints")
        return constraints

    def validate_decision(
        self, agent_id: str, decision: str, context: dict[str, Any]
    ) -> Result:
        """
        Validate an agent decision against constitutional principles.

        Args:
            agent_id: ID of the agent making the decision
            decision: The decision being made
            context: Context information for the decision

        Returns:
            Result indicating validation outcome with detailed feedback
        """
        violations = []

        # Check each constraint
        for constraint in self.constraints:
            violation = self._check_constraint(constraint, decision, context)
            if violation:
                violations.append(violation)

        # Record violations for tracking
        if violations:
            for violation in violations:
                # Update violation context with agent_id for tracking
                violation.context["agent_id"] = agent_id
                self.violation_history.append(violation)

        # Determine overall result
        critical_violations = [
            v for v in violations if v.constraint.severity == "critical"
        ]
        error_violations = [v for v in violations if v.constraint.severity == "error"]

        # Identify applied principles
        applied_principles = self._identify_applied_principles(decision, context)

        # Record decision for tracking (even if it has violations)
        reasoning = context.get("reasoning", "No reasoning provided")
        if not reasoning.strip():
            reasoning = "No reasoning provided"

        constitutional_decision = ConstitutionalDecision(
            agent_id=agent_id,
            decision=decision,
            reasoning=reasoning,
            principles_applied=applied_principles,
            context=context,
            confidence=(
                1.0 if not violations else max(0.1, 1.0 - (len(violations) * 0.2))
            ),
        )
        self.record_decision(constitutional_decision)

        if critical_violations:
            return Result(
                success=False,
                message=f"Critical constitutional violations: {len(critical_violations)}",
                artifacts={
                    "violations": [self._violation_to_dict(v) for v in violations]
                },
                metadata={"agent_id": agent_id, "validation_type": "constitutional"},
            )

        if error_violations:
            return Result(
                success=False,
                message=f"Constitutional errors: {len(error_violations)}",
                artifacts={
                    "violations": [self._violation_to_dict(v) for v in violations]
                },
                metadata={"agent_id": agent_id, "validation_type": "constitutional"},
            )

        # Success case
        return Result(
            success=True,
            message="Decision aligns with constitutional principles",
            artifacts={"applied_principles": [p.value for p in applied_principles]},
            metadata={"agent_id": agent_id, "validation_type": "constitutional"},
        )

    def _check_constraint(
        self,
        constraint: ConstitutionalConstraint,
        decision: str,
        context: dict[str, Any],
    ) -> ConstitutionalViolation | None:
        """Check a specific constitutional constraint."""
        # Route to appropriate validation function
        if constraint.check_function == "validate_code_quality":
            return self._validate_code_quality(constraint, decision, context)
        elif constraint.check_function == "validate_destructive_actions":
            return self._validate_destructive_actions(constraint, decision, context)
        elif constraint.check_function == "validate_reasoning_transparency":
            return self._validate_reasoning_transparency(constraint, decision, context)
        elif constraint.check_function == "validate_boundary_respect":
            return self._validate_boundary_respect(constraint, decision, context)
        elif constraint.check_function == "validate_learning_focus":
            return self._validate_learning_focus(constraint, decision, context)
        elif constraint.check_function == "validate_goal_alignment":
            return self._validate_goal_alignment(constraint, decision, context)
        elif constraint.check_function == "validate_collaboration":
            return self._validate_collaboration(constraint, decision, context)
        elif constraint.check_function == "validate_lesson_adherence":
            return self._validate_lesson_adherence(constraint, decision, context)

        return None

    def _validate_code_quality(
        self,
        constraint: ConstitutionalConstraint,
        decision: str,
        context: dict[str, Any],
    ) -> ConstitutionalViolation | None:
        """Validate code quality constraint."""
        # Check for quality-related keywords in decision
        quality_keywords = [
            "test",
            "review",
            "validate",
            "quality",
            "security",
            "performance",
        ]
        decision_lower = decision.lower()

        # If decision involves code changes but doesn't mention quality
        if any(
            keyword in decision_lower
            for keyword in ["implement", "code", "write", "change"]
        ) and not any(keyword in decision_lower for keyword in quality_keywords):
            return ConstitutionalViolation(
                constraint=constraint,
                violation_description="Code-related decision lacks quality considerations",
                suggested_remedy="Include quality validation, testing, or review steps",
                context=context,
            )

        return None

    def _validate_destructive_actions(
        self,
        constraint: ConstitutionalConstraint,
        decision: str,
        context: dict[str, Any],
    ) -> ConstitutionalViolation | None:
        """Validate destructive actions constraint."""
        destructive_keywords = [
            "delete",
            "remove",
            "drop",
            "truncate",
            "destroy",
            "overwrite",
        ]
        decision_lower = decision.lower()

        if any(keyword in decision_lower for keyword in destructive_keywords):
            # Check if explicit permission is mentioned
            permission_keywords = ["approved", "confirmed", "permission", "authorized"]
            if not any(keyword in decision_lower for keyword in permission_keywords):
                return ConstitutionalViolation(
                    constraint=constraint,
                    violation_description="Destructive action without explicit permission",
                    suggested_remedy=(
                        "Obtain explicit permission before proceeding with destructive actions"
                    ),
                    context=context,
                )

        return None

    def _validate_reasoning_transparency(
        self,
        constraint: ConstitutionalConstraint,
        decision: str,
        context: dict[str, Any],
    ) -> ConstitutionalViolation | None:
        """Validate reasoning transparency constraint."""
        # Check if reasoning is provided in context
        if "reasoning" not in context or not context["reasoning"]:
            return ConstitutionalViolation(
                constraint=constraint,
                violation_description="Decision lacks transparent reasoning",
                suggested_remedy="Provide clear reasoning for the decision",
                context=context,
            )

        return None

    def _validate_boundary_respect(
        self,
        constraint: ConstitutionalConstraint,
        decision: str,
        context: dict[str, Any],
    ) -> ConstitutionalViolation | None:
        """Validate boundary respect constraint."""
        # Check if decision respects stated constraints
        if "constraints" in context and context["constraints"]:
            for constraint_text in context["constraints"]:
                # Simple check - could be enhanced with NLP
                if (
                    "must not" in constraint_text.lower()
                    or "forbidden" in constraint_text.lower()
                ):
                    # Check if decision violates constraints (simplified)
                    # In a real implementation, this would be more sophisticated
                    pass

        return None

    def _validate_learning_focus(
        self,
        constraint: ConstitutionalConstraint,
        decision: str,
        context: dict[str, Any],
    ) -> ConstitutionalViolation | None:
        """Validate learning focus constraint."""
        # Check if decision includes learning opportunities
        learning_keywords = ["learn", "improve", "adapt", "insight", "lesson"]
        decision_lower = decision.lower()

        if (
            not any(keyword in decision_lower for keyword in learning_keywords)
            and len(decision) > 100
        ):  # Only flag if this is a complex decision that should include learning
            return ConstitutionalViolation(
                constraint=constraint,
                violation_description="Complex decision lacks learning component",
                suggested_remedy="Consider what can be learned from this decision",
                context=context,
            )

        return None

    def _validate_goal_alignment(
        self,
        constraint: ConstitutionalConstraint,
        decision: str,
        context: dict[str, Any],
    ) -> ConstitutionalViolation | None:
        """Validate goal alignment constraint."""
        # Check if decision aligns with stated goals
        if "goal" in context and context["goal"]:
            goal_description = context["goal"]
            # Simple alignment check - could be enhanced with semantic analysis
            # For now, just check if the decision mentions goal-related terms
            if len(decision) > 50 and goal_description.lower() not in decision.lower():
                return ConstitutionalViolation(
                    constraint=constraint,
                    violation_description="Decision does not clearly align with stated goal",
                    suggested_remedy="Explicitly connect decision to the stated goal",
                    context=context,
                )

        return None

    def _validate_collaboration(
        self,
        constraint: ConstitutionalConstraint,
        decision: str,
        context: dict[str, Any],
    ) -> ConstitutionalViolation | None:
        """Validate collaboration constraint."""
        # Check if decision promotes collaboration
        collaboration_keywords = [
            "collaborate",
            "share",
            "communicate",
            "coordinate",
            "team",
        ]
        decision_lower = decision.lower()

        # If decision affects multiple agents or stakeholders
        if any(
            keyword in decision_lower
            for keyword in ["agent", "team", "stakeholder", "user"]
        ) and not any(keyword in decision_lower for keyword in collaboration_keywords):
            return ConstitutionalViolation(
                constraint=constraint,
                violation_description=(
                    "Multi-stakeholder decision lacks collaboration considerations"
                ),
                suggested_remedy="Include collaboration or communication steps",
                context=context,
            )

        return None

    def _identify_applied_principles(
        self,
        decision: str,
        context: dict[str, Any],
    ) -> list[ConstitutionalPrinciple]:
        """Identify which constitutional principles are applied in a decision."""
        applied_principles = []
        decision_lower = decision.lower()

        # Agent autonomy
        if any(
            keyword in decision_lower
            for keyword in ["choose", "decide", "determine", "select"]
        ):
            applied_principles.append(ConstitutionalPrinciple.AGENT_AUTONOMY)

        # Goals over process
        if any(
            keyword in decision_lower
            for keyword in ["goal", "outcome", "achieve", "result"]
        ):
            applied_principles.append(ConstitutionalPrinciple.GOALS_OVER_PROCESS)

        # Intelligence over compliance
        if any(
            keyword in decision_lower
            for keyword in ["analyze", "understand", "interpret", "reason"]
        ):
            applied_principles.append(
                ConstitutionalPrinciple.INTELLIGENCE_OVER_COMPLIANCE
            )

        # Collaboration
        if any(
            keyword in decision_lower
            for keyword in ["collaborate", "communicate", "coordinate"]
        ):
            applied_principles.append(
                ConstitutionalPrinciple.COLLABORATION_THROUGH_COMMUNICATION
            )

        # Emergent workflows
        if any(
            keyword in decision_lower
            for keyword in ["adapt", "flexible", "dynamic", "emergent"]
        ):
            applied_principles.append(ConstitutionalPrinciple.EMERGENT_WORKFLOWS)

        # Continuous learning
        if any(
            keyword in decision_lower
            for keyword in ["learn", "improve", "adapt", "evolve"]
        ):
            applied_principles.append(ConstitutionalPrinciple.CONTINUOUS_LEARNING)

        # Tools as capabilities
        if any(
            keyword in decision_lower
            for keyword in ["tool", "capability", "use", "leverage"]
        ):
            applied_principles.append(ConstitutionalPrinciple.TOOLS_AS_CAPABILITIES)

        return applied_principles

    def _violation_to_dict(self, violation: ConstitutionalViolation) -> dict[str, Any]:
        """Convert violation to dictionary for serialization."""
        return {
            "constraint_name": violation.constraint.name,
            "severity": violation.constraint.severity,
            "principle": violation.constraint.principle.value,
            "description": violation.violation_description,
            "remedy": violation.suggested_remedy,
            "timestamp": violation.timestamp.isoformat(),
        }

    def record_decision(self, decision: ConstitutionalDecision) -> None:
        """Record a constitutional decision for learning purposes."""
        self.decision_history.append(decision)
        logger.info(f"Recorded constitutional decision by {decision.agent_id}")

        # Limit history size
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-500:]

    def get_principle_guidance(
        self, principle: ConstitutionalPrinciple
    ) -> dict[str, Any]:
        """Get guidance for a specific constitutional principle."""
        return self.principles.get(principle, {})

    def get_agent_constitution(self, agent_type: str) -> dict[str, Any]:
        """Get constitutional guidance for a specific agent type."""
        # Load agent-specific guidance from knowledge base
        guidelines = self.knowledge_loader.get_agent_guidelines(agent_type)

        # Combine with constitutional principles
        constitution = {
            "agent_type": agent_type,
            "core_principles": self.principles,
            "safety_constraints": [
                {"name": c.name, "description": c.description, "severity": c.severity}
                for c in self.constraints
            ],
            "specific_guidelines": guidelines,
        }

        return constitution

    def explain_decision(self, decision: ConstitutionalDecision) -> str:
        """Generate a human-readable explanation of a constitutional decision."""
        explanation = f"""
Constitutional Decision by {decision.agent_id}

Decision: {decision.decision}

Reasoning: {decision.reasoning}

Applied Principles:
"""

        for principle in decision.principles_applied:
            principle_info = self.principles.get(principle, {})
            explanation += f"- {principle_info.get('title', principle.value)}\n"

        if decision.safety_constraints:
            explanation += "\nSafety Constraints Considered:\n"
            for constraint in decision.safety_constraints:
                explanation += f"- {constraint}\n"

        explanation += f"\nConfidence: {decision.confidence:.2f}"

        return explanation

    def get_decision_history(
        self, agent_id: str | None = None
    ) -> list[ConstitutionalDecision]:
        """Get decision history, optionally filtered by agent."""
        if agent_id:
            return [d for d in self.decision_history if d.agent_id == agent_id]
        return self.decision_history.copy()

    def get_violation_history(self) -> list[ConstitutionalViolation]:
        """Get violation history for analysis."""
        return self.violation_history.copy()

    def analyze_agent_performance(self, agent_id: str) -> dict[str, Any]:
        """Analyze an agent's constitutional performance."""
        agent_decisions = self.get_decision_history(agent_id)
        agent_violations = [
            v for v in self.violation_history if v.context.get("agent_id") == agent_id
        ]

        total_decisions = len(agent_decisions)

        if not agent_decisions:
            return {
                "agent_id": agent_id,
                "total_decisions": 0,
                "violations": len(agent_violations),
                "average_confidence": 0.0,
                "principle_usage": {},
                "most_used_principle": None,
                "violation_rate": 0.0,
            }

        # Calculate metrics
        principle_usage: dict[str, int] = {}

        for decision in agent_decisions:
            for principle in decision.principles_applied:
                principle_usage[principle.value] = (
                    principle_usage.get(principle.value, 0) + 1
                )

        avg_confidence = sum(d.confidence for d in agent_decisions) / total_decisions

        return {
            "agent_id": agent_id,
            "total_decisions": total_decisions,
            "violations": len(agent_violations),
            "average_confidence": avg_confidence,
            "principle_usage": principle_usage,
            "most_used_principle": (
                max(principle_usage.items(), key=lambda x: x[1])[0]
                if principle_usage
                else None
            ),
            "violation_rate": (
                len(agent_violations) / total_decisions if total_decisions > 0 else 0
            ),
        }

    def build_system_instruction(
        self,
        role: Any,
        tools: list[Any],
        safety_level: str = "moderate",
        working_directory: Any = None,
    ) -> str:
        """
        Build a system instruction incorporating Constitutional AI principles.

        Args:
            role: Agent role (from prompts.constitutional_template)
            tools: List of available tools
            safety_level: Safety level (strict, moderate, permissive)
            working_directory: Working directory for the agent

        Returns:
            System instruction string with Constitutional AI principles
        """
        # Get role-specific principles
        role_principles = []
        if hasattr(role, "value"):
            role_value = role.value
            if role_value == "structure":
                role_principles = [
                    ConstitutionalPrinciple.AGENT_AUTONOMY,
                    ConstitutionalPrinciple.GOALS_OVER_PROCESS,
                    ConstitutionalPrinciple.TOOLS_AS_CAPABILITIES,
                ]
            elif role_value == "interface":
                role_principles = [
                    ConstitutionalPrinciple.INTELLIGENCE_OVER_COMPLIANCE,
                    ConstitutionalPrinciple.COLLABORATION_THROUGH_COMMUNICATION,
                ]
            elif role_value == "logic":
                role_principles = [
                    ConstitutionalPrinciple.GOALS_OVER_PROCESS,
                    ConstitutionalPrinciple.CONTINUOUS_LEARNING,
                ]
            elif role_value == "testing" or role_value == "quality":
                role_principles = [
                    ConstitutionalPrinciple.INTELLIGENCE_OVER_COMPLIANCE,
                    ConstitutionalPrinciple.CONTINUOUS_LEARNING,
                ]

        # Build instruction components
        tool_names = [getattr(tool, "name", tool.__class__.__name__) for tool in tools]

        # Constitutional principles section
        principles_text = ""
        for principle in role_principles:
            if principle in self.principles:
                principle_info = self.principles[principle]
                principles_text += f"""
{principle_info["title"]}:
{principle_info["description"]}
"""

        # Safety constraints section
        safety_text = ""
        if safety_level == "strict":
            safety_text = """
STRICT SAFETY MODE:
- Block all potentially harmful operations
- Require explicit confirmation for destructive actions
- Prioritize safety over efficiency
"""
        elif safety_level == "moderate":
            safety_text = """
MODERATE SAFETY MODE:
- Balance safety with functionality
- Use reasonable safety measures
- Allow standard operations with safeguards
"""
        else:  # permissive
            safety_text = """
PERMISSIVE SAFETY MODE:
- Minimal safety restrictions
- Trust agent judgment
- Allow advanced operations with awareness
"""

        # Build complete instruction
        instruction = f"""
You are a {role.value if hasattr(role, "value") else str(role)} agent operating under
Constitutional AI principles.

CONSTITUTIONAL PRINCIPLES:
{principles_text}

AVAILABLE TOOLS:
{", ".join(tool_names)}

WORKING DIRECTORY:
{working_directory or "Current directory"}

SAFETY LEVEL:
{safety_text}

CORE DIRECTIVES:
- Act autonomously to achieve goals
- Use tools intelligently and creatively
- Prioritize results over rigid processes
- Collaborate through clear communication
- Learn and adapt continuously
- Maintain transparency in reasoning
- Respect user boundaries and preferences

OPERATIONAL GUIDELINES:
- Explain your reasoning for complex decisions
- Use available tools to accomplish tasks effectively
- Prioritize goal achievement over process compliance
- Maintain high standards of quality and safety
- Adapt approaches based on context and feedback
- Communicate clearly about capabilities and limitations

Remember: Your primary duty is to achieve the user's goals effectively while
following constitutional principles.
"""

        return instruction.strip()

    def add_lesson_constraints(self, lessons: list[Any]) -> None:
        """Add lessons as additional safety constraints.

        Args:
            lessons: List of Lesson objects from the lesson capture system
        """
        logger.info(f"Adding {len(lessons)} lessons as constitutional constraints")

        # Convert lessons to constraints
        for lesson in lessons:
            # Create constraint name from lesson ID
            constraint_name = f"lesson_{lesson.lesson_id.replace('-', '_')}"

            # Determine severity based on lesson content
            severity = "warning"  # Default severity
            if (
                "critical" in lesson.issue.lower()
                or "security" in lesson.issue.lower()
                or "breaking" in lesson.issue.lower()
                or "failure" in lesson.issue.lower()
            ):
                severity = "error"

            # Create constraint from lesson
            constraint = ConstitutionalConstraint(
                name=constraint_name,
                description=f"Lesson learned: {lesson.issue[:100]}...",
                principle=ConstitutionalPrinciple.CONTINUOUS_LEARNING,
                severity=severity,
                check_function="validate_lesson_adherence",
            )

            # Add to constraints if not already present
            if not any(c.name == constraint_name for c in self.constraints):
                self.constraints.append(constraint)

                # Store lesson details for validation
                if not hasattr(self, "lesson_constraints"):
                    self.lesson_constraints = {}
                self.lesson_constraints[constraint_name] = {
                    "lesson": lesson,
                    "prevention": lesson.prevention,
                    "phase": lesson.phase,
                }

        logger.info(f"Total constraints after adding lessons: {len(self.constraints)}")

    def _validate_lesson_adherence(
        self,
        constraint: ConstitutionalConstraint,
        decision: str,
        context: dict[str, Any],
    ) -> ConstitutionalViolation | None:
        """Validate that decisions adhere to lessons learned."""
        if not hasattr(self, "lesson_constraints"):
            return None

        lesson_info = self.lesson_constraints.get(constraint.name)
        if not lesson_info:
            return None

        lesson = lesson_info["lesson"]
        prevention = lesson_info["prevention"]

        # Check if decision might repeat past mistakes
        decision_lower = decision.lower()
        issue_keywords = lesson.issue.lower().split()

        # Look for patterns that might indicate repeating the mistake
        violation_indicators = []
        for keyword in issue_keywords:
            if len(keyword) > 4 and keyword in decision_lower:
                violation_indicators.append(keyword)

        # If we have multiple indicators, check if prevention is mentioned
        if len(violation_indicators) >= 2:
            prevention_keywords = prevention.lower().split()
            prevention_mentioned = any(
                keyword in decision_lower
                for keyword in prevention_keywords
                if len(keyword) > 5
            )

            if not prevention_mentioned:
                return ConstitutionalViolation(
                    constraint=constraint,
                    violation_description=f"Decision may repeat past mistake: {lesson.issue[:100]}",
                    suggested_remedy=f"Apply prevention strategy: {prevention[:200]}",
                    context={"lesson_id": lesson.lesson_id, "phase": lesson.phase},
                )

        return None
