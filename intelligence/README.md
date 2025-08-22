# Genesis Intelligence System

The Genesis Intelligence System provides AI-driven automation, problem-solving, and quality assurance capabilities. This system is built on the SOLVE methodology and includes sophisticated multi-agent coordination.

## 🧠 Components

### Smart Commit System (`smart-commit/`)
Intelligent commit validation and quality gates that prevent issues before they reach the repository.

**Key Features:**
- Multi-stage validation pipeline
- Quality gate enforcement
- Automatic code formatting
- Security scanning integration
- Context-aware commit messages

### SOLVE Framework (`solve/`)
Core implementation of the SOLVE methodology for problem-solving and orchestration.

**Key Features:**
- Graph-driven development using Neo4j
- Constitutional AI with safety principles
- Lesson capture and template evolution
- Multi-agent coordination system
- Infrastructure generation from architecture

### Autofix System (`autofix/`)
Automated issue detection, categorization, and resolution system.

**Key Features:**
- Three-stage fix pipeline (format → validate → AI fix)
- LLM-powered code correction
- Backup and rollback capabilities
- Metrics and validation tracking

## 🚀 Quick Start

### Initialize Intelligence System
```python
from intelligence import configure_intelligence
from intelligence.solve import get_orchestrator

# Configure the intelligence layer
configure_intelligence(
    neo4j_uri="bolt://localhost:7687",
    project_id="my-gcp-project"
)

# Get the SOLVE orchestrator
orchestrator = get_orchestrator()
```

### Smart Commit Usage
```bash
# Use smart commit for all changes
./scripts/smart-commit.sh "feat: add user authentication"

# Or through the intelligence layer
python -m intelligence.smart_commit
```

### SOLVE Operations
```bash
# Initialize graph database
solve graph init

# Parse ADR to graph
solve graph parse-adr --file architecture.md

# Execute development plan
solve execute --graph-id ADR-001
```

## 🏗️ Architecture

The Intelligence System follows a layered architecture:

```
┌─────────────────────────────────────┐
│           CLI Interface             │
├─────────────────────────────────────┤
│         SOLVE Orchestrator          │
├─────────────────────────────────────┤
│    Smart Commit  │    Autofix       │
├─────────────────────────────────────┤
│        Constitutional AI            │
├─────────────────────────────────────┤
│    Neo4j Graph   │   Lesson Store   │
└─────────────────────────────────────┘
```

## 📚 Documentation

- [Smart Commit Guide](smart-commit/README.md) - Intelligent commit validation
- [SOLVE Framework](solve/README.md) - Core orchestration system
- [Autofix System](autofix/) - Automated issue resolution
- [Agent Coordination](solve/agents/) - Multi-agent development

## 🔧 Configuration

### Environment Variables
```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# GCP Integration
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Intelligence Settings
INTELLIGENCE_LOG_LEVEL=INFO
SOLVE_WORKSPACE=.solve/
```

### Configuration Files
- `.solve/config.yaml` - Main configuration
- `.solve/lessons/` - Lesson storage directory
- `templates/` - Template library

## 🧪 Testing

```bash
# Run intelligence system tests
pytest intelligence/

# Run specific component tests
pytest intelligence/smart-commit/tests/
pytest intelligence/solve/tests/
pytest intelligence/autofix/tests/

# Validation tests
python intelligence/solve/tests/validate_comprehensive.py
```

## 🤝 Integration

### With Genesis Core
```python
from core import configure_core
from intelligence import configure_intelligence

# Configure both systems
configure_core("my-service", "production")
configure_intelligence(project_id="my-gcp-project")
```

### With CLI
```bash
# All genesis commands use intelligence automatically
g commit "feat: new feature"  # Uses smart-commit
g solve "Create user API"     # Uses SOLVE orchestrator
g fix                         # Uses autofix system
```

## 🔗 Related

- [Genesis Core](../core/) - Production-ready plumbing
- [Monitoring System](../monitoring/) - Observability stack
- [Documentation](../docs/) - Comprehensive guides

---

**Intelligence System** - Making development smarter, not harder.
