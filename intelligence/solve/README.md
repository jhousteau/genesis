# SOLVE Package - Core Implementation

This directory contains the core implementation of the SOLVE methodology framework.

## Package Structure

### Core Components

#### Lesson Capture System (Issue #80)
- `lesson_capture_system.py` - Main lesson capture and processing engine (812 lines)
- `template_evolution.py` - Template evolution based on lessons (573 lines)
- `constitutional_lesson_ai.py` - AI validation with safety principles (574 lines)
- `cli_lesson_handlers.py` - CLI commands for lesson management (712 lines)
- `gcp_lesson_integration.py` - Cloud storage integration (621 lines)
- `improvement_metrics.py` - Analytics and reporting (583 lines)

#### Agent System
- `agents/` - Specialized AI agents for each SOLVE phase
  - `master_planner.py` - ADR to graph transformation (Issue #76)
  - `contract_validation.py` - Tick-and-tie validation (Issue #77)
  - `parallel_execution.py` - Concurrent agent orchestration (Issue #78)
- `agent_coordinator.py` - Multi-agent orchestration system
- `agent_constitution.py` - Constitutional AI principles

#### Tool Implementations (Issue #73)
- `tools/` - Development tool integrations
  - `terraform_tool.py` - Infrastructure as code operations
  - `gcp_tool.py` - Google Cloud Platform deployments
  - `graph_tool.py` - Neo4j database operations
  - `git_tool.py` - Version control operations

#### Infrastructure Generation (Issue #79)
- `terraform/` - Terraform generation from graphs
  - `generator.py` - Main generation engine
  - `mapper.py` - Graph to Terraform mapping
  - `validator.py` - Infrastructure validation

### Supporting Components

#### CLI Interface
- `cli.py` - Main command-line interface
- `cli_lesson_handlers.py` - Lesson-specific CLI commands
- `cli_build_plans.py` - Build plan management

#### Quality & Debugging
- `auto_debugger.py` - Automated debugging system
- `governance.py` - Quality governance engine
- `validators.py` - Phase validation rules

#### Utilities
- `models.py` - Core data models
- `prompts/` - AI prompt templates
- `utils/` - Utility functions

## Key Features

### 1. Lesson Capture and Evolution
The system learns from every execution:
```python
from solve.lesson_capture_system import LessonCaptureSystem

system = LessonCaptureSystem()
lesson = await system.capture_from_autofix(result)
```

### 2. Graph-Driven Development
Neo4j powers the architecture:
```python
from solve.agents.master_planner import MasterPlannerAgent

planner = MasterPlannerAgent()
graph_id = await planner.parse_adr_to_graph(adr_content)
```

### 3. Parallel Agent Execution
Concurrent development across graph nodes:
```python
from solve.parallel_execution import ParallelExecutionEngine

engine = ParallelExecutionEngine()
results = await engine.execute_all_nodes(graph_id)
```

## Testing

### Unit Tests
```bash
pytest tests/unit/
```

### Integration Tests
```bash
pytest tests/integration/
```

### Functional Validation
```bash
python tmp/validate_issue_80_comprehensive.py
```

## Development Guidelines

### Adding New Features
1. Follow existing patterns in the codebase
2. Add comprehensive tests for new functionality
3. Update documentation and CLI help text
4. Ensure Constitutional AI principles are maintained

### Code Quality Standards
- Type hints required for all functions
- Docstrings following Google style
- 80% minimum test coverage
- No mock implementations - real functionality only

## Dependencies

### Core Requirements
- Python 3.10+
- Google ADK (Agent Development Kit)
- Neo4j Python driver
- Click (CLI framework)

### Optional Dependencies
- google-cloud-* (for GCP integration)
- python-terraform (for infrastructure)
- Constitutional AI validators

## Configuration

### Environment Variables
```bash
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# GCP Configuration
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# SOLVE Configuration
SOLVE_LESSONS_PATH=.solve/lessons
SOLVE_TEMPLATES_PATH=templates/archetypes
```

### Configuration Files
- `.solve/config.yaml` - Main configuration
- `.solve/lessons/` - Lesson storage
- `templates/` - Template library

## CLI Usage

### Lesson Management
```bash
# Capture lessons
solve lessons capture --issue "..." --resolution "..."

# Search lessons
solve lessons search --query "database"

# View analytics
solve lessons analytics --period 30_days
```

### Template Evolution
```bash
# Evolve templates
solve templates evolve --min-priority medium

# List templates
solve templates list

# Show template details
solve templates show cloud-run
```

### Graph Operations
```bash
# Initialize graph
solve graph init

# Visualize architecture
solve graph visualize --graph-id ADR-001

# Generate Terraform
solve graph generate-terraform --graph-id ADR-001
```

## Architecture Decisions

### Why Graph-Driven?
- Single source of truth for system architecture
- Enables parallel agent execution
- Supports complex dependency management
- Facilitates infrastructure generation

### Why Lesson Capture?
- Continuous improvement without manual intervention
- Prevents repeated mistakes
- Builds organizational knowledge
- Measures improvement over time

### Why Constitutional AI?
- Ensures safe autonomous operation
- Prevents harmful code generation
- Maintains quality standards
- Provides explainable decisions

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

See [LICENSE](../../LICENSE) for details.
