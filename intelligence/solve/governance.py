"""
Governance Loader for SOLVE Phases

This module loads and parses governance files in both XML and YAML frontmatter formats,
providing structured configuration for phase execution.
"""

import asyncio
import logging

try:
    import defusedxml.ElementTree as ET
except ImportError:
    import warnings
    import xml.etree.ElementTree as ET

    warnings.warn(
        "defusedxml not available. Using standard XML parser. "
        "Install defusedxml for enhanced security: pip install defusedxml",
        UserWarning,
        stacklevel=2,
    )
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from solve.exceptions import ConfigurationError, GovernanceLoadError
from solve.models import ADRConfig, GovernanceConfig, PhaseConfig

logger = logging.getLogger(__name__)


class GovernanceLoader:
    """Loads and parses governance files in both XML and YAML frontmatter formats.

    Handles both ADR governance files and phase-specific governance files,
    providing a unified interface for configuration loading.

    Supports both legacy .mdc XML format and new YAML frontmatter + Markdown format.
    """

    def __init__(self) -> None:
        """Initialize the governance loader."""
        self._cache: dict[str, ADRConfig | PhaseConfig | GovernanceConfig] = {}

    def _is_yaml_frontmatter(self, content: str) -> bool:
        """Check if content uses YAML frontmatter format."""
        return content.strip().startswith("---\n")

    def _parse_yaml_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse YAML frontmatter and return metadata dict and markdown content."""
        if not self._is_yaml_frontmatter(content):
            raise ValueError("Content is not YAML frontmatter format")

        # Split frontmatter and content
        parts = content.split("---\n", 2)
        if len(parts) < 3:
            raise ValueError("Invalid YAML frontmatter format")

        yaml_content = parts[1]
        markdown_content = parts[2].strip()

        # Parse YAML metadata
        metadata = yaml.safe_load(yaml_content)
        if not isinstance(metadata, dict):
            raise ValueError("YAML frontmatter must be a dictionary")

        return metadata, markdown_content

    async def _parse_yaml_adr(self, content: str, path: Path) -> ADRConfig:
        """Parse YAML frontmatter ADR format."""
        try:
            metadata, markdown_content = self._parse_yaml_frontmatter(content)

            # Build ADR config from YAML metadata
            config = ADRConfig(
                number=str(metadata.get("number", "")).strip(),
                title=str(metadata.get("title", "")).strip(),
                status=str(metadata.get("status", "draft")).strip(),
            )

            if not config.number:
                raise ValueError("Missing required field: number")
            if not config.title:
                raise ValueError("Missing required field: title")

            # Extract requirements
            if "requirements" in metadata:
                requirements = metadata["requirements"]
                if isinstance(requirements, list):
                    for req in requirements:
                        if isinstance(req, str) and req.strip():
                            config.requirements.append(req.strip())

            # Extract constraints
            if "constraints" in metadata:
                constraints = metadata["constraints"]
                if isinstance(constraints, list):
                    for constraint in constraints:
                        if isinstance(constraint, str) and constraint.strip():
                            # Add constraints as special requirements
                            config.requirements.append(
                                f"Constraint: {constraint.strip()}"
                            )

            # Extract phase outcomes
            if "phase_outcomes" in metadata:
                phase_outcomes = metadata["phase_outcomes"]
                if isinstance(phase_outcomes, dict):
                    for phase_name, outcomes in phase_outcomes.items():
                        if isinstance(outcomes, list):
                            phase_config = PhaseConfig(
                                name=phase_name,
                                description=f"{phase_name} phase outcomes",
                            )
                            phase_config.key_considerations = [
                                str(outcome) for outcome in outcomes if outcome
                            ]
                            config.phase_outcomes[phase_name] = phase_config

            # Extract approved resources
            if "approved_resources" in metadata:
                resources = metadata["approved_resources"]
                if isinstance(resources, dict) and "components" in resources:
                    components = resources["components"]
                    if isinstance(components, list):
                        for component in components:
                            if isinstance(component, str) and component.strip():
                                component_text = component.strip()
                                # Extract file path from component text (before " - ")
                                if " - " in component_text:
                                    file_path = component_text.split(" - ")[0].strip()
                                    # Add component file path as a requirement
                                    config.requirements.append(
                                        f"Create component: {file_path}"
                                    )
                                    logger.debug(
                                        f"Added component requirement: {file_path}"
                                    )

            logger.info(f"Successfully parsed YAML ADR-{config.number}: {config.title}")
            return config

        except Exception as e:
            raise GovernanceLoadError(
                f"Failed to parse YAML frontmatter ADR: {e}",
                file_path=str(path),
            ) from e

    async def _parse_xml_adr(self, content: str, path: Path) -> ADRConfig:
        """Parse legacy XML ADR format."""
        try:
            # Parse XML
            # Using defusedxml when available for secure XML parsing
            root = ET.fromstring(
                content
            )  # noqa: S314 - Using defusedxml or warning issued
            if root.tag != "adr_governance":
                raise GovernanceLoadError(
                    f"Invalid ADR file format: root element should be "
                    f"'adr_governance', got '{root.tag}'",
                    file_path=str(path),
                )

            # Extract metadata
            metadata = root.find("metadata")
            if metadata is None:
                raise GovernanceLoadError(
                    "ADR file missing required 'metadata' section",
                    file_path=str(path),
                )

            # Build ADR config
            config = ADRConfig(
                number=self._get_text(metadata, "number", required=True),
                title=self._get_text(metadata, "title", required=True),
                status=self._get_text(metadata, "status", default="draft"),
            )

            # Extract requirements from root level (primary location)
            requirements_elem = root.find("requirements")
            if requirements_elem:
                for req in requirements_elem.findall("requirement"):
                    if req.text:
                        config.requirements.append(req.text.strip())
            else:
                # Fallback: try to find requirements in decision section
                decision = root.find("decision")
                if decision:
                    requirements_elem = decision.find("requirements")
                    if requirements_elem:
                        for req in requirements_elem.findall("requirement"):
                            if req.text:
                                config.requirements.append(req.text.strip())

            # Extract approved resources
            resources = root.find("approved_resources")
            if resources:
                # Extract traditional resource elements
                for resource in resources.findall("resource"):
                    resource_dict = {
                        "url": resource.get("url", ""),
                        "priority": resource.get("priority", "medium"),
                        "description": self._get_text(
                            resource, "description", default=""
                        ),
                        "usage": self._get_text(resource, "usage", default=""),
                    }
                    config.approved_resources.append(resource_dict)

                # Extract component file paths and add them as requirements
                components = resources.findall(".//component")
                for component in components:
                    if component.text:
                        component_text = component.text.strip()
                        # Extract file path from component text (before " - ")
                        if " - " in component_text:
                            file_path = component_text.split(" - ")[0].strip()
                            # Add component file path as a requirement
                            config.requirements.append(f"Create component: {file_path}")
                            logger.debug(f"Added component requirement: {file_path}")

            # Extract phase outcomes
            phase_outcomes = root.find("phase_outcomes")
            if phase_outcomes:
                for phase in ["scaffold", "outline", "logic", "verify", "enhance"]:
                    phase_elem = phase_outcomes.find(phase)
                    if phase_elem:
                        phase_config = PhaseConfig(
                            name=phase,
                            description=f"{phase} phase",
                            outcome=self._get_text(phase_elem, "outcome"),
                            uses_web_resources=self._get_bool(
                                phase_elem, "uses_web_resources"
                            ),
                        )

                        # Extract key considerations
                        key_elem = phase_elem.find("key_considerations")
                        if key_elem:
                            for consideration in key_elem.findall("consideration"):
                                if consideration.text:
                                    phase_config.key_considerations.append(
                                        consideration.text.strip(),
                                    )

                        config.phase_outcomes[phase] = phase_config

            # Validate ADR structure before caching
            validation_errors = self._validate_adr_structure(config, root)
            if validation_errors:
                logger.warning(
                    f"ADR validation warnings for {path}: {validation_errors}"
                )
                # Don't fail - just warn about potential issues

            logger.info(f"Successfully parsed XML ADR-{config.number}: {config.title}")
            return config

        except ET.ParseError as e:
            raise GovernanceLoadError(
                f"Failed to parse ADR XML: {e}",
                file_path=str(path),
                parse_error=str(e),
            ) from e

    async def load_adr(self, path: Path) -> ADRConfig:
        """Load and parse an ADR governance file.

        Args:
            path: Path to the ADR file (*.mdc or *.md)

        Returns:
            Parsed ADR configuration

        Raises:
            GovernanceLoadError: If file cannot be loaded or parsed
        """
        logger.info(f"Loading ADR from {path}")

        # Check cache first
        cache_key = f"adr:{path}"
        if cache_key in self._cache:
            logger.debug(f"Using cached ADR config for {path}")
            return self._cache[cache_key]  # type: ignore[return-value]

        try:
            # Read file content
            if not path.exists():
                raise GovernanceLoadError(
                    f"ADR file not found: {path}", file_path=str(path)
                )

            content = await asyncio.to_thread(path.read_text, encoding="utf-8")

            # Determine format and parse accordingly
            if self._is_yaml_frontmatter(content):
                config = await self._parse_yaml_adr(content, path)
            else:
                config = await self._parse_xml_adr(content, path)

            # Cache the result
            self._cache[cache_key] = config
            logger.info(
                f"Successfully loaded ADR-{config.number}: {config.title} with "
                f"{len(config.requirements)} requirements",
            )

            return config

        except Exception as e:
            if isinstance(e, GovernanceLoadError):
                raise
            raise GovernanceLoadError(
                f"Failed to load ADR file: {e}", file_path=str(path)
            ) from e

    async def load_phase_governance(self, path: Path, phase: str) -> PhaseConfig:
        """Load phase-specific governance configuration.

        Args:
            path: Path to search for phase governance files
            phase: Phase identifier (S, O, L, V, E)

        Returns:
            Phase configuration object

        Raises:
            ConfigurationError: If phase is invalid
        """
        logger.info(f"Loading {phase} phase governance from {path}")

        cache_key = f"phase:{path}:{phase}"
        if cache_key in self._cache:
            logger.debug(f"Using cached phase config for {phase}")
            return self._cache[cache_key]  # type: ignore[return-value]

        # Map phase letters to full names
        phase_names = {
            "S": "scaffold",
            "O": "outline",
            "L": "logic",
            "V": "verify",
            "E": "enhance",
        }

        phase_name = phase_names.get(phase.upper())
        if not phase_name:
            raise ConfigurationError(
                f"Invalid phase: {phase}",
                config_key="phase",
                expected_type="One of: S, O, L, V, E",
            )

        # Look for phase governance files
        governance_file = path / f"{phase_name}-governance.mdc"
        if governance_file.exists():
            try:
                content = await asyncio.to_thread(
                    governance_file.read_text, encoding="utf-8"
                )
                # Using defusedxml when available for secure XML parsing
                root = ET.fromstring(
                    content
                )  # noqa: S314 - Using defusedxml or warning issued

                # Create phase config from governance file
                config = PhaseConfig(
                    name=phase_name,
                    description=self._get_text(
                        root, "description", default=f"{phase_name} phase"
                    ),
                )

                # Extract requirements and other details
                requirements = root.find("requirements")
                if requirements:
                    for req in requirements.findall("requirement"):
                        if req.text:
                            config.key_considerations.append(req.text.strip())

                logger.info(
                    f"Loaded {phase_name} governance with "
                    f"{len(config.key_considerations)} considerations",
                )
                return config

            except Exception as e:
                logger.warning(f"Failed to load phase governance: {e}")

        # Return default config if no governance file found
        logger.debug(f"No governance file found for {phase_name}, using defaults")
        return PhaseConfig(
            name=phase_name, description=f"Default {phase_name} phase configuration"
        )

    async def merge_configs(
        self,
        configs: list[ADRConfig | PhaseConfig | GovernanceConfig],
    ) -> GovernanceConfig:
        """Merge multiple configuration objects into a unified config.

        Args:
            configs: List of configuration objects to merge

        Returns:
            Unified governance configuration
        """
        logger.debug(f"Merging {len(configs)} configuration objects")

        merged = GovernanceConfig(phase="merged")

        for config in configs:
            if isinstance(config, ADRConfig):
                # Merge ADR configuration
                merged.requirements.extend(config.requirements)
                merged.approved_resources.extend(config.approved_resources)

                # Add phase outcomes as constraints
                for phase_name, phase_config in config.phase_outcomes.items():
                    if phase_config.outcome:
                        merged.constraints.append(
                            f"{phase_name} phase outcome: {phase_config.outcome}",
                        )

            elif isinstance(config, PhaseConfig):
                # Merge phase configuration - add key_considerations as requirements
                merged.requirements.extend(config.key_considerations)

            elif isinstance(config, GovernanceConfig):
                # Merge governance configuration
                merged.requirements.extend(config.requirements)
                merged.constraints.extend(config.constraints)
                merged.approved_resources.extend(config.approved_resources)

                # Merge performance targets
                merged.performance_targets.update(config.performance_targets)

        # Remove duplicates while preserving order
        merged.requirements = list(dict.fromkeys(merged.requirements))
        merged.constraints = list(dict.fromkeys(merged.constraints))

        logger.info(
            f"Merged config has {len(merged.requirements)} requirements, "
            f"{len(merged.constraints)} constraints",
        )
        return merged

    def _get_text(
        self,
        parent: ET.Element,
        tag: str,
        default: str = "",
        required: bool = False,
    ) -> str:
        """Extract text content from XML element.

        Args:
            parent: Parent XML element
            tag: Tag name to find
            default: Default value if element not found
            required: Whether this field is required

        Returns:
            Text content or default value

        Raises:
            GovernanceLoadError: If required field is missing
        """
        element = parent.find(tag)
        if element is not None and element.text:
            return element.text.strip()

        if required:
            raise GovernanceLoadError(f"Required field '{tag}' is missing or empty")

        return default

    def _get_bool(self, parent: ET.Element, tag: str, default: bool = False) -> bool:
        """Extract boolean value from XML element.

        Args:
            parent: Parent XML element
            tag: Tag name to find
            default: Default value if element not found

        Returns:
            Boolean value or default
        """
        text = self._get_text(parent, tag, default=str(default))
        return text.lower() in ("true", "1", "yes", "on")

    def _validate_adr_structure(self, config: ADRConfig, root: ET.Element) -> list[str]:
        """Validate ADR structure and return any issues found.

        Args:
            config: ADR configuration to validate
            root: XML root element

        Returns:
            List of validation warnings
        """
        warnings = []

        # Check for empty requirements
        if not config.requirements:
            warnings.append("No requirements found in ADR")

        # Check for missing essential sections
        if root.find("context") is None:
            warnings.append("Missing context section")

        if root.find("decision") is None:
            warnings.append("Missing decision section")

        return warnings


class GovernanceEngine(GovernanceLoader):
    """Engine for applying governance rules during phase execution.

    This is an enhanced version of GovernanceLoader with additional
    methods for rule enforcement and validation.
    """

    def __init__(self, project_path: Path | None = None):
        """Initialize the governance engine.

        Args:
            project_path: Optional project path for context
        """
        super().__init__()
        self.project_path = project_path or Path.cwd()

    async def get_phase_rules(self, phase: str) -> dict[str, Any]:
        """Get rules for a specific phase.

        Args:
            phase: Phase identifier (S, O, L, V, E)

        Returns:
            Dictionary of rules for the phase
        """
        try:
            # Load phase configuration
            phase_config = await self.load_phase_governance(self.project_path, phase)

            # Convert to rules format
            rules = {
                "phase": phase,
                "name": phase_config.name,
                "description": phase_config.description,
                "considerations": phase_config.key_considerations,
                "outcome": phase_config.outcome,
                "uses_web_resources": phase_config.uses_web_resources,
            }

            return rules

        except Exception as e:
            logger.warning(f"Failed to load phase rules: {e}")
            return {
                "phase": phase,
                "name": phase.lower(),
                "description": f"Default rules for phase {phase}",
                "considerations": [],
                "outcome": None,
                "uses_web_resources": False,
            }

    def validate_requirements(self, requirements: list[str]) -> tuple[bool, list[str]]:
        """Validate a list of requirements.

        Args:
            requirements: List of requirements to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        for req in requirements:
            if not req or not req.strip():
                issues.append("Empty requirement found")
            elif len(req) < 10:
                issues.append(f"Requirement too short: '{req}'")
            elif not any(
                word in req.lower()
                for word in [
                    "must",
                    "shall",
                    "should",
                    "will",
                    "create",
                    "implement",
                    "add",
                    "ensure",
                ]
            ):
                issues.append(f"Requirement lacks action verb: '{req}'")

        return len(issues) == 0, issues
