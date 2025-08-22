"""
KnowledgeLoader - Simple file-based knowledge system leveraging existing frameworks

Following best practices from docs/best-practices/:
- 10-leverage-existing-frameworks.md: Use markdown library, don't reinvent parsing
- 14-gemini-cli-integration-patterns.md: Follow tool patterns for structured interface
- 1-anthropic-prompt-engineering-guide.md: Use structured XML-like data representation
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDocument:
    """Structured representation of a knowledge document"""

    title: str
    content: str
    sections: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    file_path: Path | None = None
    keywords: list[str] = field(default_factory=list)


class KnowledgeLoader:
    """
    Simple file-based knowledge loader following Gemini CLI patterns

    Leverages existing frameworks instead of reinventing:
    - Uses pathlib for file operations
    - Simple regex for markdown parsing (can upgrade to markdown lib later)
    - Follows tool interface pattern from Gemini CLI
    """

    def __init__(self, knowledge_path: str = "docs/best-practices/"):
        self.knowledge_path = Path(knowledge_path)
        self.cache: dict[str, KnowledgeDocument] = {}

        if not self.knowledge_path.exists():
            logger.warning(f"Knowledge path {self.knowledge_path} does not exist")

    def load_document(self, filename: str) -> KnowledgeDocument | None:
        """Load and parse a single document - leveraging existing file operations"""
        if filename in self.cache:
            return self.cache[filename]

        file_path = self.knowledge_path / filename
        if not file_path.exists():
            logger.warning(f"Document {filename} not found at {file_path}")
            return None

        try:
            content = file_path.read_text(encoding="utf-8")

            doc = KnowledgeDocument(
                title=self._extract_title(content),
                content=content,
                sections=self._extract_sections(content),
                metadata=self._extract_metadata(content),
                file_path=file_path,
                keywords=self._extract_keywords(content),
            )

            self.cache[filename] = doc
            logger.debug(f"Loaded document: {filename}")
            return doc

        except Exception as e:
            logger.error(f"Error loading document {filename}: {e}")
            return None

    def load_all_documents(self) -> dict[str, KnowledgeDocument]:
        """Load all markdown documents from knowledge path"""
        documents = {}

        for md_file in self.knowledge_path.glob("*.md"):
            doc = self.load_document(md_file.name)
            if doc:
                documents[md_file.name] = doc

        logger.info(f"Loaded {len(documents)} knowledge documents")
        return documents

    def search_for_guidance(
        self,
        query: str,
        agent_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for relevant guidance - following Gemini CLI tool pattern

        Args:
            query: Search query (keywords, concepts, problems)
            agent_type: Optional agent type to filter guidance

        Returns:
            List of guidance items with relevance scoring
        """
        # Handle empty query
        if not query or not query.strip():
            return []

        results = []
        query_lower = query.lower()

        # Load all documents if not cached
        if not self.cache:
            self.load_all_documents()

        for filename, doc in self.cache.items():
            # Skip if document failed to load
            if not doc:
                continue

            relevance_score = self._calculate_relevance(doc, query_lower)

            if relevance_score > 0:
                results.append(
                    {
                        "document": doc.title,
                        "filename": filename,
                        "relevance_score": relevance_score,
                        "relevant_sections": self._find_relevant_sections(
                            doc, query_lower
                        ),
                        "guidance_type": self._classify_guidance(doc, query_lower),
                        "file_path": str(doc.file_path),
                        "keywords": doc.keywords,
                    },
                )

        # Sort by relevance score (highest first)
        def sort_key(x: dict[str, Any]) -> float:
            score = x["relevance_score"]
            return float(score) if isinstance(score, int | float) else 0.0

        results.sort(key=sort_key, reverse=True)

        return results

    def get_agent_guidelines(self, agent_type: str) -> list[dict[str, Any]]:
        """Get specific guidelines for an agent type"""
        agent_queries = {
            "structure": ["project structure", "scaffolding", "directory organization"],
            "interface": ["API design", "contracts", "type hints", "interfaces"],
            "logic": ["implementation", "business logic", "algorithms"],
            "quality": ["testing", "validation", "code quality", "reviews"],
            "test": ["testing patterns", "test coverage", "test frameworks"],
        }

        # Handle unknown agent types by returning empty list
        if agent_type.lower() not in agent_queries:
            return []

        queries = agent_queries.get(agent_type.lower(), [])
        all_results = []

        for query in queries:
            results = self.search_for_guidance(query, agent_type)
            all_results.extend(results)

        # Deduplicate and sort
        seen = set()
        unique_results = []
        for result in all_results:
            key = (result["filename"], result["document"])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)

        return unique_results

    def _extract_title(self, content: str) -> str:
        """Extract title from markdown content"""
        # Look for first # heading
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "Untitled"

    def _extract_sections(self, content: str) -> dict[str, str]:
        """Extract sections from markdown content"""
        sections = {}

        # Find all headings and their content
        heading_pattern = r"^(#{1,6})\s+(.+)$"
        lines = content.split("\n")

        current_section = None
        current_content: list[str] = []

        for line in lines:
            heading_match = re.match(heading_pattern, line)
            if heading_match:
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()

                # Start new section
                current_section = heading_match.group(2).strip()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _extract_metadata(self, content: str) -> dict[str, Any]:
        """Extract metadata from document"""
        metadata: dict[str, Any] = {}

        # Look for common patterns
        if "Executive Summary" in content:
            metadata["has_executive_summary"] = True

        if "Best Practices" in content:
            metadata["has_best_practices"] = True

        if "Framework" in content or "Architecture" in content:
            metadata["has_architecture"] = True

        # Count code examples
        code_blocks = len(re.findall(r"```", content))
        metadata["code_examples_count"] = code_blocks // 2

        return metadata

    def _extract_keywords(self, content: str) -> list[str]:
        """Extract keywords from content"""
        # Simple keyword extraction - can be enhanced with NLP later
        keywords = []

        # Look for common technical terms
        tech_terms = [
            "agent",
            "framework",
            "architecture",
            "pattern",
            "tool",
            "adk",
            "gemini",
            "claude",
            "react",
            "mcp",
            "constitutional",
            "prompt",
            "evaluation",
            "testing",
            "validation",
        ]

        content_lower = content.lower()
        for term in tech_terms:
            if term in content_lower:
                keywords.append(term)

        return keywords

    def _calculate_relevance(self, doc: KnowledgeDocument, query: str) -> float:
        """Calculate relevance score for a document given a query"""
        score = 0.0

        # Title match (highest weight)
        if query in doc.title.lower():
            score += 3.0

        # Content match (medium weight)
        content_lower = doc.content.lower()
        query_words = query.split()

        for word in query_words:
            if word in content_lower:
                # Count occurrences
                occurrences = content_lower.count(word)
                score += min(occurrences * 0.1, 1.0)  # Cap at 1.0 per word

        # Section title match (high weight)
        for section_title in doc.sections:
            if query in section_title.lower():
                score += 2.0

        # Keyword match (medium weight)
        for keyword in doc.keywords:
            if keyword in query:
                score += 1.5

        return score

    def _find_relevant_sections(self, doc: KnowledgeDocument, query: str) -> list[str]:
        """Find sections that are relevant to the query"""
        relevant_sections = []

        for section_title, section_content in doc.sections.items():
            # Check if query appears in section title or content
            if query in section_title.lower() or query in section_content.lower():
                relevant_sections.append(section_title)

        return relevant_sections

    def _classify_guidance(self, doc: KnowledgeDocument, query: str) -> str:
        """Classify the type of guidance this document provides"""
        title_lower = doc.title.lower()

        if "framework" in title_lower or "architecture" in title_lower:
            return "architecture"
        elif "prompt" in title_lower or "engineering" in title_lower:
            return "prompt_engineering"
        elif "evaluation" in title_lower or "testing" in title_lower:
            return "evaluation"
        elif "best practices" in title_lower:
            return "best_practices"
        elif "integration" in title_lower or "patterns" in title_lower:
            return "integration"
        else:
            return "general"

    def get_document_summary(self, filename: str) -> str | None:
        """Get a brief summary of a document"""
        doc = self.load_document(filename)
        if not doc:
            return None

        # Look for executive summary
        if "Executive Summary" in doc.sections:
            return doc.sections["Executive Summary"]

        # Look for overview
        if "Overview" in doc.sections:
            return doc.sections["Overview"]

        # Fall back to first paragraph
        paragraphs = doc.content.split("\n\n")
        for paragraph in paragraphs:
            if paragraph.strip() and not paragraph.startswith("#"):
                return paragraph.strip()

        return "No summary available"

    def list_available_documents(self) -> list[dict[str, Any]]:
        """List all available documents with basic info"""
        if not self.cache:
            self.load_all_documents()

        documents = []
        for filename, doc in self.cache.items():
            if doc:
                documents.append(
                    {
                        "filename": filename,
                        "title": doc.title,
                        "keywords": doc.keywords,
                        "sections": list(doc.sections.keys()),
                        "metadata": doc.metadata,
                    },
                )

        return documents

    def get_constitutional_principles(self) -> dict[str, Any]:
        """Get constitutional principles for agent guidance."""
        doc = self.load_document("12-agentic-transformation-principles.md")
        if not doc:
            return {}

        # Extract the seven core principles
        principles: dict[str, dict[str, Any]] = {}

        # Look for principle sections
        for section_title, section_content in doc.sections.items():
            if "Agent Autonomy" in section_title:
                principles["agent_autonomy"] = {
                    "title": section_title,
                    "content": section_content,
                    "anti_patterns": self._extract_anti_patterns(section_content),
                    "implementation_notes": self._extract_implementation_notes(
                        section_content
                    ),
                }
            elif "Goals Over Process" in section_title:
                principles["goals_over_process"] = {
                    "title": section_title,
                    "content": section_content,
                    "metrics": self._extract_metrics(section_content),
                    "implementation_notes": self._extract_implementation_notes(
                        section_content
                    ),
                }
            elif "Intelligence Over Compliance" in section_title:
                principles["intelligence_over_compliance"] = {
                    "title": section_title,
                    "content": section_content,
                    "constitutional_approach": self._extract_constitutional_approach(
                        section_content,
                    ),
                    "implementation_notes": self._extract_implementation_notes(
                        section_content
                    ),
                }
            elif "Collaboration Through Communication" in section_title:
                principles["collaboration_through_communication"] = {
                    "title": section_title,
                    "content": section_content,
                    "patterns": self._extract_patterns(section_content),
                    "implementation_notes": self._extract_implementation_notes(
                        section_content
                    ),
                }
            elif "Emergent Workflows" in section_title:
                principles["emergent_workflows"] = {
                    "title": section_title,
                    "content": section_content,
                    "vs_prescribed_info": self._extract_vs_prescribed(section_content),
                    "implementation_notes": self._extract_implementation_notes(
                        section_content
                    ),
                }
            elif "Continuous Learning" in section_title:
                principles["continuous_learning"] = {
                    "title": section_title,
                    "content": section_content,
                    "learning_components": self._extract_learning_components(
                        section_content
                    ),
                    "implementation_notes": self._extract_implementation_notes(
                        section_content
                    ),
                }
            elif "Tools as Capabilities" in section_title:
                principles["tools_as_capabilities"] = {
                    "title": section_title,
                    "content": section_content,
                    "philosophy": self._extract_philosophy(section_content),
                    "implementation_notes": self._extract_implementation_notes(
                        section_content
                    ),
                }

        return principles

    def get_safety_principles(self) -> dict[str, Any]:
        """Get safety principles for agent operation."""
        doc = self.load_document("AGENT_SAFETY_PRINCIPLES.md")
        if not doc:
            return {}

        safety_principles: dict[str, dict[str, Any]] = {}

        # Extract core principles
        if "Core Principles" in doc.sections:
            content = doc.sections["Core Principles"]
            safety_principles["core_principles"] = {
                "content": content,
                "principles": self._extract_numbered_list(content),
            }

        # Extract technical safeguards
        if "Technical Safeguards" in doc.sections:
            content = doc.sections["Technical Safeguards"]
            safety_principles["technical_safeguards"] = {
                "content": content,
                "react_protections": self._extract_react_protections(content),
                "oversight_checkpoints": self._extract_oversight_checkpoints(content),
            }

        # Extract safety mechanisms
        if "Safety Mechanisms" in doc.sections:
            content = doc.sections["Safety Mechanisms"]
            safety_principles["safety_mechanisms"] = {
                "content": content,
                "iterative_safeguards": self._extract_iterative_safeguards(content),
                "quality_assurance": self._extract_quality_assurance(content),
            }

        return safety_principles

    def get_unified_architecture_guidance(self) -> dict[str, Any]:
        """Get unified agentic architecture guidance."""
        doc = self.load_document("11-unified-agentic-architecture.md")
        if not doc:
            return {}

        architecture_guidance: dict[str, dict[str, Any]] = {}

        # Extract architectural principles
        if "Architectural Principles" in doc.sections:
            content = doc.sections["Architectural Principles"]
            architecture_guidance["architectural_principles"] = {
                "content": content,
                "principles": self._extract_numbered_list(content),
            }

        # Extract core components
        if "Core Architecture Components" in doc.sections:
            content = doc.sections["Core Architecture Components"]
            architecture_guidance["core_components"] = {
                "content": content,
                "agent_hierarchy_info": self._extract_agent_hierarchy(content),
                "tool_architecture_info": self._extract_tool_architecture(content),
            }

        # Extract constitutional principles
        if "Constitutional Principles for SOLVE Agents" in doc.sections:
            content = doc.sections["Constitutional Principles for SOLVE Agents"]
            architecture_guidance["constitutional_principles"] = {
                "content": content,
                "constitution_info": self._extract_constitution(content),
            }

        return architecture_guidance

    def _extract_anti_patterns(self, content: str) -> list[str]:
        """Extract anti-patterns from content."""
        anti_patterns = []
        lines = content.split("\n")
        in_anti_patterns = False

        for line in lines:
            if "Anti-Patterns" in line:
                in_anti_patterns = True
                continue
            elif in_anti_patterns and line.startswith("- "):
                anti_patterns.append(line[2:].strip())
            elif in_anti_patterns and line.startswith("**"):
                break

        return anti_patterns

    def _extract_metrics(self, content: str) -> list[str]:
        """Extract metrics from content."""
        metrics = []
        lines = content.split("\n")

        for line in lines:
            if line.startswith("- ❌") or line.startswith("- ✅"):
                metrics.append(line[2:].strip())

        return metrics

    def _extract_implementation_notes(self, content: str) -> list[str]:
        """Extract implementation notes from content."""
        notes = []
        lines = content.split("\n")
        in_implementation = False

        for line in lines:
            if "Implementation" in line and ":" in line:
                in_implementation = True
                continue
            elif in_implementation and line.startswith("```"):
                # Skip code blocks for now
                continue
            elif in_implementation and line.strip() and not line.startswith("#"):
                notes.append(line.strip())

        return notes

    def _extract_constitutional_approach(self, content: str) -> str:
        """Extract constitutional approach from content."""
        lines = content.split("\n")
        in_constitutional = False
        approach_lines = []

        for line in lines:
            if "Constitutional AI Approach" in line:
                in_constitutional = True
                continue
            elif in_constitutional and line.startswith("```"):
                in_constitutional = False
                break
            elif in_constitutional and line.strip():
                approach_lines.append(line.strip())

        return "\n".join(approach_lines)

    def _extract_patterns(self, content: str) -> list[str]:
        """Extract patterns from content."""
        patterns = []
        lines = content.split("\n")

        for line in lines:
            if line.startswith("- **") and "**:" in line:
                pattern = line[3:].split("**:")[0].strip()
                patterns.append(pattern)

        return patterns

    def _extract_vs_prescribed(self, content: str) -> dict[str, list[str]]:
        """Extract emergent vs prescribed comparison."""
        vs_comparison = {}
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if "# ❌ Prescribed workflow" in line:
                vs_comparison["prescribed"] = lines[i + 1 : i + 4]
            elif "# ✅ Emergent workflow" in line:
                vs_comparison["emergent"] = lines[i + 1 : i + 4]

        return vs_comparison

    def _extract_learning_components(self, content: str) -> list[str]:
        """Extract learning components from content."""
        components = []
        lines = content.split("\n")

        for line in lines:
            if line.startswith("- ") and any(
                word in line.lower()
                for word in ["capture", "share", "improve", "question"]
            ):
                components.append(line[2:].strip())

        return components

    def _extract_philosophy(self, content: str) -> list[str]:
        """Extract tool philosophy from content."""
        philosophy = []
        lines = content.split("\n")

        for line in lines:
            if line.startswith("- ") and any(
                word in line.lower()
                for word in ["enable", "available", "composable", "discoverable"]
            ):
                philosophy.append(line[2:].strip())

        return philosophy

    def _extract_numbered_list(self, content: str) -> list[str]:
        """Extract numbered list items from content."""
        items = []
        lines = content.split("\n")

        for line in lines:
            if re.match(r"^\d+\.", line.strip()):
                items.append(line.strip())

        return items

    def _extract_react_protections(self, content: str) -> list[str]:
        """Extract ReAct loop protections."""
        protections = []
        lines = content.split("\n")
        in_react = False

        for line in lines:
            if "ReAct Loop Protections" in line:
                in_react = True
                continue
            elif in_react and line.startswith("- **"):
                protection = line[3:].split("**:")[0].strip()
                protections.append(protection)
            elif in_react and line.startswith("####"):
                break

        return protections

    def _extract_oversight_checkpoints(self, content: str) -> list[str]:
        """Extract human oversight checkpoints."""
        checkpoints = []
        lines = content.split("\n")
        in_oversight = False

        for line in lines:
            if "Human Oversight Checkpoints" in line:
                in_oversight = True
                continue
            elif in_oversight and line.startswith("- **"):
                checkpoint = line[3:].split("**:")[0].strip()
                checkpoints.append(checkpoint)
            elif in_oversight and line.startswith("###"):
                break

        return checkpoints

    def _extract_iterative_safeguards(self, content: str) -> list[str]:
        """Extract iterative safeguards."""
        safeguards = []
        lines = content.split("\n")

        for line in lines:
            if "max_iterations" in line or "timeout" in line or "stuck" in line:
                safeguards.append(line.strip())

        return safeguards

    def _extract_quality_assurance(self, content: str) -> list[str]:
        """Extract quality assurance items."""
        qa_items = []
        lines = content.split("\n")

        for line in lines:
            if "validate_tests" in line or "validate_code_quality" in line:
                qa_items.append(line.strip())

        return qa_items

    def _extract_agent_hierarchy(self, content: str) -> dict[str, Any]:
        """Extract agent hierarchy information."""
        hierarchy = {}
        lines = content.split("\n")

        for line in lines:
            if "solve_agent = Agent" in line:
                hierarchy["root_agent"] = "solve_coordinator"
            elif "sub_agents" in line:
                hierarchy["sub_agents"] = (
                    "StructureArchitect,InterfaceDesigner,ImplementationExpert,"
                    "QualityGuardian,LearningCatalyst"
                )

        return hierarchy

    def _extract_tool_architecture(self, content: str) -> dict[str, Any]:
        """Extract tool architecture information."""
        tools = {}
        lines = content.split("\n")

        for line in lines:
            if "StructureAnalyzer" in line:
                tools["structure"] = "StructureAnalyzer"
            elif "InterfaceExtractor" in line:
                tools["interface"] = "InterfaceExtractor"
            elif "CodeGenerator" in line:
                tools["code"] = "CodeGenerator"
            elif "TestGenerator" in line:
                tools["test"] = "TestGenerator"
            elif "LessonCapture" in line:
                tools["lesson"] = "LessonCapture"

        return tools

    def _extract_constitution(self, content: str) -> dict[str, Any]:
        """Extract constitutional principles."""
        constitution = {}
        lines = content.split("\n")

        current_section = None
        current_items: list[str] = []

        for line in lines:
            if line.startswith("Core Principles:"):
                current_section = "core_principles"
                current_items = []
            elif line.startswith("Quality Objectives:"):
                if current_section:
                    constitution[current_section] = current_items
                current_section = "quality_objectives"
                current_items = []
            elif line.startswith("Behavioral Guidelines:"):
                if current_section:
                    constitution[current_section] = current_items
                current_section = "behavioral_guidelines"
                current_items = []
            elif (
                line.startswith("1. ")
                or line.startswith("2. ")
                or line.startswith("3. ")
            ):
                current_items.append(line.strip())
            elif line.startswith("- "):
                current_items.append(line[2:].strip())

        if current_section:
            constitution[current_section] = current_items

        return constitution
